"""Parses the LLM's raw text response into the framework's common finding shape.

Tolerant of the LLM wrapping JSON in a markdown code fence or adding stray
whitespace/prose despite instructions. Malformed responses degrade to an
empty finding list with a logged warning rather than crashing the pipeline.
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)
_SEVERITY_ALLOWED = {"low", "medium", "high", "critical"}


def parse_response(raw_text: str, file_path: str) -> list[dict]:
    payload = _extract_json(raw_text)
    if payload is None:
        logger.warning("Could not parse LLM response as JSON for %s; treating as no findings.", file_path)
        return []

    findings = []
    for item in payload.get("findings", []):
        try:
            findings.append(_to_finding(item, file_path))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed LLM finding for %s: %s", file_path, exc)
    return findings


def _extract_json(raw_text: str) -> dict | None:
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = _JSON_FENCE.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    # Last resort: grab the largest {...} span in the text.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    return None


def _to_finding(item: dict, file_path: str) -> dict:
    severity = str(item.get("severity", "medium")).lower()
    if severity not in _SEVERITY_ALLOWED:
        severity = "medium"

    confidence = float(item.get("confidence", 0.6))
    confidence = max(0.0, min(1.0, confidence))

    status = str(item.get("status", "new")).lower()

    return {
        "line": int(item.get("line", 0) or 0),
        "end_line": int(item.get("end_line", item.get("line", 0)) or 0),
        "type": item.get("type", "Unknown"),
        "cwe": item.get("cwe"),
        "severity": severity,
        "confidence": confidence,
        "source": "llm_reasoning",
        "rule_id": item.get("upstream_rule_id"),
        "function_name": None,
        "explanation": item.get("explanation", ""),
        "suggested_fix": item.get("suggested_fix"),
        "file": file_path,
        "llm_status": status,  # confirmed | rejected | new -- consumed by the aggregator
    }
