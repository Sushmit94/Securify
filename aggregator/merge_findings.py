"""Merges and deduplicates findings from all three detection layers into a
single ranked list per file.

Common finding shape produced by every layer (see static_analysis/semgrep_runner.py
for the authoritative definition): a dict with line/end_line/type/cwe/severity/
confidence/source/rule_id/function_name/explanation/suggested_fix/file.

Merge logic:
1. Start from Layer 1 (static analysis) findings.
2. Apply Layer 3 (LLM) verdicts: a "rejected" verdict drops the matching static
   finding (the LLM had full context and decided it wasn't real); a "confirmed"
   verdict merges onto the matching static finding, adding the LLM as a second
   contributing source; a "new" verdict (or an unmatched confirmed verdict)
   becomes its own finding.
3. Attach Layer 2 (ML classifier) scores to any finding whose line falls
   inside a scored function, when the score clears ML_POSITIVE_THRESHOLD --
   below that the ML layer isn't asserting anything about that specific line.
4. A final same-location safety-net pass merges any leftover duplicates that
   line up on (file, line, cwe/type) but weren't explicitly linked by the LLM.
5. Each finding's final confidence/severity is computed by aggregator.scorer
   from whichever layers actually contributed.
"""
from __future__ import annotations

from aggregator.scorer import compute_confidence, rank_findings, resolve_severity

ML_POSITIVE_THRESHOLD = 0.5
_LINE_PROXIMITY = 1  # lines within this distance are considered "the same location"


def merge(
    static_findings: list[dict],
    llm_findings: list[dict],
    ml_scores: list[dict] | None = None,
) -> list[dict]:
    working: list[dict] = [_seed(f) for f in static_findings]

    _apply_llm_verdicts(working, llm_findings)
    if ml_scores:
        _apply_ml_scores(working, ml_scores)
    working = _dedupe_same_location(working)

    for finding in working:
        finding["sources"] = sorted(finding["layer_confidences"].keys())
        finding["confidence"] = compute_confidence(finding["layer_confidences"])
        finding["severity"] = resolve_severity(finding["severities"])
        del finding["layer_confidences"]
        del finding["severities"]
        del finding["rejected"]

    return rank_findings(working)


def _seed(finding: dict) -> dict:
    seeded = dict(finding)
    seeded["layer_confidences"] = {finding["source"]: finding["confidence"]}
    seeded["severities"] = [finding["severity"]]
    seeded["rejected"] = False
    return seeded


def _same_location(a: dict, b_line: int, b_rule_id: str | None) -> bool:
    if b_rule_id and a.get("rule_id") == b_rule_id and abs(a["line"] - b_line) <= _LINE_PROXIMITY:
        return True
    return False


def _apply_llm_verdicts(working: list[dict], llm_findings: list[dict]) -> None:
    for llm_finding in llm_findings:
        status = llm_finding.get("llm_status", "new")
        rule_id = llm_finding.get("rule_id")
        line = llm_finding.get("line", 0)

        match = next((f for f in working if not f["rejected"] and _same_location(f, line, rule_id)), None)

        if status == "rejected":
            if match:
                match["rejected"] = True
            continue

        if status == "confirmed" and match:
            match["layer_confidences"]["llm_reasoning"] = llm_finding["confidence"]
            match["severities"].append(llm_finding["severity"])
            # The LLM's explanation/fix has full code context, so prefer it when present.
            if llm_finding.get("explanation"):
                match["explanation"] = llm_finding["explanation"]
            if llm_finding.get("suggested_fix"):
                match["suggested_fix"] = llm_finding["suggested_fix"]
            continue

        # "new" findings, or "confirmed" verdicts that didn't line up with any static finding
        # (the LLM may reference a static rule_id loosely) become standalone findings.
        new_finding = dict(llm_finding)
        new_finding["layer_confidences"] = {"llm_reasoning": llm_finding["confidence"]}
        new_finding["severities"] = [llm_finding["severity"]]
        new_finding["rejected"] = False
        working.append(new_finding)


def _apply_ml_scores(working: list[dict], ml_scores: list[dict]) -> None:
    for finding in working:
        if finding["rejected"]:
            continue
        for scored_fn in ml_scores:
            if scored_fn["score"] < ML_POSITIVE_THRESHOLD:
                continue
            if scored_fn["start_line"] <= finding["line"] <= scored_fn["end_line"]:
                finding["layer_confidences"]["ml_classifier"] = scored_fn["score"]
                finding["function_name"] = finding.get("function_name") or scored_fn.get("function_name")
                break


def _dedupe_same_location(working: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for finding in working:
        if finding["rejected"]:
            continue
        duplicate = next(
            (
                k
                for k in kept
                if k["file"] == finding["file"]
                and abs(k["line"] - finding["line"]) <= _LINE_PROXIMITY
                and (k.get("cwe") and k.get("cwe") == finding.get("cwe") or k.get("type") == finding.get("type"))
            ),
            None,
        )
        if duplicate is None:
            kept.append(finding)
            continue
        for layer, conf in finding["layer_confidences"].items():
            duplicate["layer_confidences"][layer] = max(duplicate["layer_confidences"].get(layer, 0), conf)
        duplicate["severities"].extend(finding["severities"])
    return kept
