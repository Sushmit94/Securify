"""Runs the fine-tuned Layer 2 classifier on a single code unit (function).

Used by backend/services/pipeline.py. Models are loaded once per language and
cached in-process (fine-tuned transformer models are too expensive to reload
per request). If no checkpoint exists for a language, `score()` returns None
so the pipeline can skip Layer 2 for that language without raising — the
framework never claims ML-based confidence for a language it wasn't trained
on, per the README's language support strategy.
"""
from __future__ import annotations

import logging

from ml_model.model_config import get_model_config, has_trained_checkpoint

logger = logging.getLogger(__name__)

_MODEL_CACHE: dict[str, tuple] = {}


def is_available(language: str) -> bool:
    return has_trained_checkpoint(language)


def score(language: str, code: str) -> float | None:
    """Returns a vulnerability probability in [0, 1], or None if no checkpoint exists for this language."""
    if not is_available(language):
        return None

    try:
        model, tokenizer, config = _get_or_load_model(language)
    except ImportError:
        logger.warning("torch/transformers not installed; skipping ML classifier layer for %s", language)
        return None

    import torch

    encoding = tokenizer(code, truncation=True, padding="max_length", max_length=config.max_length, return_tensors="pt")
    with torch.no_grad():
        logits = model(**encoding).logits
        probs = torch.softmax(logits, dim=-1)
        vulnerable_prob = probs[0, 1].item()  # index 1 = "vulnerable", see model_config.LABEL_NAMES
    return vulnerable_prob


def _get_or_load_model(language: str):
    if language in _MODEL_CACHE:
        return _MODEL_CACHE[language]

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    config = get_model_config(language)
    tokenizer = AutoTokenizer.from_pretrained(str(config.checkpoint_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(config.checkpoint_dir))
    model.eval()

    _MODEL_CACHE[language] = (model, tokenizer, config)
    return _MODEL_CACHE[language]
