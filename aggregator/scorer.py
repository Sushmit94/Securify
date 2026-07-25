"""Computes a final weighted confidence score for a finding based on which
detection layers actually contributed to it.

The LLM reasoning layer is weighted highest since it has full contextual
understanding of the code (it can see why a static pattern match is or isn't
actually exploitable); the ML classifier is weighted lowest since it's a
single probability score with no explanation. Weights are renormalized over
only the layers that actually ran for a given finding/language, so a
Tier 2 language (no ML classifier) isn't penalized for a layer that was never
available to it.
"""
from __future__ import annotations

LAYER_WEIGHTS = {
    "static_analysis": 0.30,
    "ml_classifier": 0.25,
    "llm_reasoning": 0.45,
}

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_RANK_TO_SEVERITY = {v: k for k, v in SEVERITY_RANK.items()}

# A finding confirmed by more independent layers is inherently more trustworthy,
# on top of whatever the individual layer confidences say.
_AGREEMENT_BONUS = {1: 0.0, 2: 0.08, 3: 0.15}


def compute_confidence(layer_confidences: dict[str, float]) -> float:
    """layer_confidences: {"static_analysis": 0.7, "llm_reasoning": 0.85, ...} -> final score in [0, 1]."""
    if not layer_confidences:
        return 0.0

    active_weights = {layer: LAYER_WEIGHTS.get(layer, 0.2) for layer in layer_confidences}
    total_weight = sum(active_weights.values())
    if total_weight == 0:
        return round(sum(layer_confidences.values()) / len(layer_confidences), 3)

    weighted_sum = sum(layer_confidences[layer] * active_weights[layer] for layer in layer_confidences)
    base_score = weighted_sum / total_weight

    bonus = _AGREEMENT_BONUS.get(min(len(layer_confidences), 3), 0.15)
    return round(min(1.0, base_score + bonus), 3)


def resolve_severity(severities: list[str]) -> str:
    """A vulnerability is as severe as its most severe assessment across layers."""
    if not severities:
        return "medium"
    best_rank = max(SEVERITY_RANK.get(s, 1) for s in severities)
    return _RANK_TO_SEVERITY[best_rank]


def rank_findings(findings: list[dict]) -> list[dict]:
    return sorted(
        findings,
        key=lambda f: (SEVERITY_RANK.get(f.get("severity", "medium"), 1), f.get("confidence", 0.0)),
        reverse=True,
    )
