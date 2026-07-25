"""Runs Bandit (Python-specific, deeper AST-based checks) and normalizes results.

Bandit only applies to Python. Runs alongside semgrep_runner for Tier 1
Python files to add a second, independent deterministic signal. See
semgrep_runner for the common finding shape.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

_SEVERITY_MAP = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high"}

_CWE_BY_TEST = {
    "B301": "CWE-502", "B302": "CWE-502", "B303": "CWE-327", "B304": "CWE-327",
    "B305": "CWE-327", "B306": "CWE-377", "B307": "CWE-78", "B308": "CWE-79",
    "B310": "CWE-22", "B311": "CWE-330", "B324": "CWE-327", "B501": "CWE-295",
    "B502": "CWE-295", "B506": "CWE-20", "B601": "CWE-78", "B602": "CWE-78",
    "B603": "CWE-78", "B604": "CWE-78", "B605": "CWE-78", "B606": "CWE-78",
    "B607": "CWE-78", "B608": "CWE-89", "B609": "CWE-78",
}


def is_available() -> bool:
    return shutil.which("bandit") is not None


def run(file_path: str, timeout: int = 60) -> list[dict]:
    if not is_available():
        logger.warning("bandit is not installed; skipping Python-specific static checks for %s", file_path)
        return []

    cmd = ["bandit", "-f", "json", "-q", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("bandit failed for %s: %s", file_path, exc)
        return []

    if not result.stdout:
        return []

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("bandit produced non-JSON output for %s", file_path)
        return []

    return [_to_finding(r, file_path) for r in payload.get("results", [])]


def _to_finding(raw: dict, file_path: str) -> dict:
    test_id = raw.get("test_id", "")
    return {
        "line": raw.get("line_number", 0),
        "end_line": raw.get("line_number", 0),
        "type": raw.get("test_name", "Unknown"),
        "cwe": _CWE_BY_TEST.get(test_id, f"CWE-{raw['issue_cwe']['id']}" if raw.get("issue_cwe") else None),
        "severity": _SEVERITY_MAP.get(raw.get("issue_severity", "MEDIUM"), "medium"),
        "confidence": {"LOW": 0.5, "MEDIUM": 0.7, "HIGH": 0.85}.get(raw.get("issue_confidence", "MEDIUM"), 0.7),
        "source": "static_analysis",
        "rule_id": test_id,
        "function_name": None,
        "explanation": raw.get("issue_text", ""),
        "suggested_fix": None,
        "file": file_path,
    }
