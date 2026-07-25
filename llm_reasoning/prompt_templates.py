"""Builds the structured prompt sent to the LLM reasoning layer (Layer 3).

The LLM is given the code, Layer 1 (static analysis) findings, and Layer 2
(ML classifier) score when available, and is asked to: confirm or reject each
prior-layer finding, surface anything the other layers missed, explain each
finding in plain English, and suggest a fix. It is instructed to respond with
strict JSON so response_parser.py can parse it reliably.
"""
from __future__ import annotations

import json

SYSTEM_PROMPT = """You are a senior application security engineer performing a code review.
You will be given a source file (or function), plus findings from two upstream detection layers:
1. A static analyzer (deterministic, pattern-based - can false-positive on context it can't see)
2. An ML classifier (a learned probability that the code is vulnerable - can be wrong, and is only
   available for some languages)

Your job:
- For each upstream finding, decide CONFIRM or REJECT based on actual code context (e.g. reject a
  "SQL injection" flag if the input is provably not attacker-controlled).
- Identify any additional real vulnerabilities the upstream layers missed.
- For every confirmed/new finding, give a precise line number, a plain-English explanation of *why*
  it's a vulnerability, and a concrete, minimal suggested fix.
- Do not invent findings that aren't actually present in the code. If nothing is wrong, say so.
- Assign your own confidence (0-1) reflecting how certain you are, independent of the upstream layers.

Respond with ONLY valid JSON matching this schema, no prose outside the JSON:
{
  "findings": [
    {
      "line": <int>,
      "end_line": <int>,
      "type": "<short vulnerability class, e.g. 'SQL Injection'>",
      "cwe": "<CWE-XXX or null>",
      "severity": "<low|medium|high|critical>",
      "confidence": <float 0-1>,
      "status": "<confirmed|rejected|new>",
      "upstream_rule_id": "<rule_id being confirmed/rejected, or null if new>",
      "explanation": "<plain-English reason this is/isn't a real vulnerability>",
      "suggested_fix": "<concrete remediation>"
    }
  ]
}"""


def build_prompt(
    code: str,
    language: str,
    file_path: str,
    static_findings: list[dict] | None = None,
    ml_score: float | None = None,
    function_name: str | None = None,
) -> str:
    static_findings = static_findings or []

    static_summary = (
        json.dumps(
            [
                {
                    "rule_id": f.get("rule_id"),
                    "line": f.get("line"),
                    "type": f.get("type"),
                    "cwe": f.get("cwe"),
                    "severity": f.get("severity"),
                    "message": f.get("explanation"),
                }
                for f in static_findings
            ],
            indent=2,
        )
        if static_findings
        else "(none - no static analysis findings for this file/language)"
    )

    ml_summary = (
        f"{ml_score:.3f} probability of being vulnerable (0=safe, 1=vulnerable)"
        if ml_score is not None
        else "(not available - no trained ML classifier for this language)"
    )

    location = f"{file_path}" + (f" (function: {function_name})" if function_name else "")

    return f"""File: {location}
Language: {language}

--- Static analysis (Layer 1) findings ---
{static_summary}

--- ML classifier (Layer 2) score ---
{ml_summary}

--- Source code ---
```{language}
{code}
```

Review the code above. Confirm/reject each static analysis finding, surface anything missed, and
respond with the JSON schema described in your instructions."""
