"""Orchestrates the full detection pipeline described in the README:

    Language Detector -> Parser/Router -> [Static Analysis | ML Classifier | LLM Reasoning] -> Aggregator

Usable both as a library (scan_file / scan_paths / scan_repo, called by the
FastAPI routes) and as a CLI:

    python backend/services/pipeline.py --input path/to/file.py
    python backend/services/pipeline.py --input path/to/directory
    python backend/services/pipeline.py --repo https://github.com/user/repo
"""
from __future__ import annotations

import argparse
import importlib
import logging
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from aggregator.merge_findings import merge  # noqa: E402
from language_support.detector import LanguageDetector  # noqa: E402
from language_support.language_registry import get_language_config  # noqa: E402
from language_support.parsers import generic_fallback  # noqa: E402
from llm_reasoning import llm_client, prompt_templates, response_parser  # noqa: E402
from ml_model import inference as ml_inference  # noqa: E402
from reports.generator import build_summary  # noqa: E402
from static_analysis import bandit_runner, semgrep_runner  # noqa: E402

logger = logging.getLogger(__name__)

# Files larger than this are skipped (binary/generated/vendored files aren't useful to scan
# and can be extremely slow to send through the LLM layer).
MAX_FILE_SIZE_BYTES = 500_000
# Cap how many functions per file get sent to the LLM, to bound cost/latency on large files.
MAX_LLM_UNITS_PER_FILE = 25

SKIP_DIR_NAMES = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "target"}


def scan_file(file_path: str, run_llm: bool = True) -> dict:
    """Runs all applicable layers on a single file and returns the merged per-file result."""
    path = Path(file_path)
    code = path.read_text(encoding="utf-8", errors="ignore")

    language = LanguageDetector().detect_file(path)
    config = get_language_config(language)
    layers_run: list[str] = []

    static_findings: list[dict] = []
    if semgrep_runner.is_available():
        static_findings.extend(semgrep_runner.run(str(path), language))
        layers_run.append("static_analysis")
    if language == "python" and bandit_runner.is_available():
        static_findings.extend(bandit_runner.run(str(path)))
        if "static_analysis" not in layers_run:
            layers_run.append("static_analysis")

    functions = _extract_functions(config.parser_module, code, str(path))

    ml_scores: list[dict] = []
    if language and ml_inference.is_available(language):
        for fn in functions:
            score = ml_inference.score(language, fn["code"])
            if score is not None:
                ml_scores.append(
                    {
                        "function_name": fn["name"],
                        "start_line": fn["start_line"],
                        "end_line": fn["end_line"],
                        "score": score,
                    }
                )
        if ml_scores:
            layers_run.append("ml_classifier")

    llm_findings: list[dict] = []
    if run_llm and llm_client.is_available():
        for fn in functions[:MAX_LLM_UNITS_PER_FILE]:
            fn_static = [f for f in static_findings if fn["start_line"] <= f["line"] <= fn["end_line"]]
            fn_ml_score = next(
                (s["score"] for s in ml_scores if s["start_line"] == fn["start_line"] and s["end_line"] == fn["end_line"]),
                None,
            )
            prompt = prompt_templates.build_prompt(
                code=fn["code"],
                language=language or "unknown",
                file_path=str(path),
                static_findings=fn_static,
                ml_score=fn_ml_score,
                function_name=fn["name"],
            )
            try:
                raw = llm_client.complete(prompt_templates.SYSTEM_PROMPT, prompt)
                llm_findings.extend(response_parser.parse_response(raw, str(path)))
            except RuntimeError as exc:
                logger.warning("LLM reasoning failed for %s (%s): %s", path, fn["name"], exc)
        if "llm_reasoning" not in layers_run:
            layers_run.append("llm_reasoning")

    findings = merge(static_findings, llm_findings, ml_scores)

    return {
        "file": str(path),
        "language": language,
        "tier": config.tier,
        "layers_run": layers_run,
        "findings": findings,
    }


def _extract_functions(parser_module_path: str | None, code: str, file_path: str) -> list[dict]:
    module = generic_fallback
    if parser_module_path:
        try:
            module = importlib.import_module(parser_module_path)
        except ImportError:
            logger.warning("Parser module %s unavailable; using generic fallback for %s", parser_module_path, file_path)
    try:
        return module.extract_functions(code, file_path)
    except Exception as exc:
        logger.warning("Parsing failed for %s: %s; using whole file as one unit", file_path, exc)
        return generic_fallback.extract_functions(code, file_path)


def scan_paths(paths: list[str], target_label: str, run_llm: bool = True) -> dict:
    """Scans a list of file paths and returns the full multi-file scan result."""
    files = [scan_file(p, run_llm=run_llm) for p in paths]
    return {
        "scan_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": target_label,
        "files": files,
        "summary": build_summary(files),
    }


def scan_directory(root: str, run_llm: bool = True, max_files: int = 500) -> dict:
    root_path = Path(root)
    if root_path.is_file():
        return scan_paths([str(root_path)], target_label=str(root_path), run_llm=run_llm)

    candidates = [
        p
        for p in root_path.rglob("*")
        if p.is_file()
        and not any(part in SKIP_DIR_NAMES for part in p.parts)
        and p.stat().st_size <= MAX_FILE_SIZE_BYTES
    ][:max_files]

    return scan_paths([str(p) for p in candidates], target_label=str(root_path), run_llm=run_llm)


def scan_repo(repo_url: str, run_llm: bool = True, max_files: int = 200) -> dict:
    """Shallow-clones a public git repo into a temp dir, scans it, then cleans up."""
    tmp_dir = tempfile.mkdtemp(prefix="securify_repo_")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, tmp_dir],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        result = scan_directory(tmp_dir, run_llm=run_llm, max_files=max_files)
        result["target"] = repo_url
        for file_entry in result["files"]:
            file_entry["file"] = str(Path(file_entry["file"]).relative_to(tmp_dir))
            for finding in file_entry["findings"]:
                finding["file"] = file_entry["file"]
        return result
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to clone {repo_url}: {exc.stderr}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Run the AI-based vulnerability detection pipeline.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", help="Path to a single file or a directory to scan.")
    group.add_argument("--repo", help="URL of a public git repository to clone and scan.")
    parser.add_argument("--no-llm", action="store_true", help="Skip the LLM reasoning layer (Layer 3).")
    parser.add_argument("--output", help="Write the JSON report to this path instead of stdout.")
    parser.add_argument("--save", action="store_true", help="Persist the scan to the local scan history database.")
    args = parser.parse_args()

    run_llm = not args.no_llm
    if args.input:
        result = scan_directory(args.input, run_llm=run_llm)
    else:
        result = scan_repo(args.repo, run_llm=run_llm)

    if args.save:
        from backend.models.db import save_scan

        save_scan(result)

    from reports.generator import to_json

    output_text = to_json(result)
    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
        print(f"Wrote report to {args.output}")
    else:
        print(output_text)

    summary = result["summary"]
    print(
        f"\nScanned {summary['files_scanned']} file(s), {summary['total_findings']} finding(s): "
        f"{summary['by_severity']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
