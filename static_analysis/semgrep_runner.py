"""Runs Semgrep against a file and normalizes results into the framework's common finding shape.

Common finding shape (a plain dict, shared across all three detection layers
and consumed by aggregator.merge_findings):

    {
        "line": int,
        "end_line": int,
        "type": str,             # human-readable vulnerability class, e.g. "SQL Injection"
        "cwe": str | None,       # e.g. "CWE-89"
        "severity": str,         # "low" | "medium" | "high" | "critical"
        "confidence": float,     # 0-1, this layer's own confidence
        "source": "static_analysis",
        "rule_id": str,
        "function_name": str | None,
        "explanation": str,
        "suggested_fix": str | None,
        "file": str,
    }

Requires the `semgrep` CLI/package to be installed. If it isn't, `run()`
returns an empty list with a warning rather than raising, so the rest of the
pipeline (ML + LLM layers) can still run for languages semgrep doesn't need
to cover.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from language_support.language_registry import get_language_config

logger = logging.getLogger(__name__)

_SEVERITY_MAP = {"INFO": "low", "WARNING": "medium", "ERROR": "high"}


def is_available() -> bool:
    return shutil.which("semgrep") is not None


def run(file_path: str, language: str | None = None, timeout: int = 60) -> list[dict]:
    if not is_available():
        logger.warning("semgrep is not installed; skipping static analysis layer for %s", file_path)
        return []

    config = get_language_config(language)
    semgrep_config = config.semgrep_ruleset if config.semgrep_ruleset and Path(config.semgrep_ruleset).exists() else None
    config_arg = semgrep_config or config.semgrep_registry_config or "auto"

    cmd = ["semgrep", "--json", "--quiet", "--config", config_arg, file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("semgrep failed for %s: %s", file_path, exc)
        return []

    if not result.stdout:
        return []

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("semgrep produced non-JSON output for %s", file_path)
        return []

    return [_to_finding(r, file_path) for r in payload.get("results", [])]


def _to_finding(raw: dict, file_path: str) -> dict:
    extra = raw.get("extra", {})
    metadata = extra.get("metadata", {})
    cwe = metadata.get("cwe")
    if isinstance(cwe, list):
        cwe = cwe[0] if cwe else None

    start = raw.get("start", {})
    end = raw.get("end", {})

    return {
        "line": start.get("line", 0),
        "end_line": end.get("line", start.get("line", 0)),
        "type": metadata.get("vulnerability_class", [extra.get("message", "Unknown")])[0]
        if isinstance(metadata.get("vulnerability_class"), list)
        else extra.get("message", "Unknown"),
        "cwe": cwe,
        "severity": _SEVERITY_MAP.get(extra.get("severity", "WARNING"), "medium"),
        "confidence": 0.7,
        "source": "static_analysis",
        "rule_id": raw.get("check_id", "unknown"),
        "function_name": None,
        "explanation": extra.get("message", ""),
        "suggested_fix": extra.get("fix"),
        "file": file_path,
    }
