"""Evaluates a fine-tuned checkpoint on a held-out test set.

    python ml_model/evaluate.py --language python --synthetic

Prints precision/recall/F1/accuracy and writes them to
ml_model/checkpoints/<language>_model/eval_results.json.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.dataset_loader import generate_synthetic_sample, load_dataset, train_test_split  # noqa: E402
from ml_model.model_config import SUPPORTED_ML_LANGUAGES, get_model_config, has_trained_checkpoint  # noqa: E402


def evaluate(language: str, dataset_path: Path | None = None, use_synthetic: bool = False) -> dict:
    if not has_trained_checkpoint(language):
        raise SystemExit(
            f"No trained checkpoint found for '{language}' at "
            f"ml_model/checkpoints/{language}_model/. Run ml_model/train.py first."
        )

    try:
        import numpy as np
        import torch
        from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(
            "Missing ML dependencies. Install them with `pip install -r requirements.txt`. "
            f"Original error: {exc}"
        )

    if use_synthetic:
        generate_synthetic_sample(language)

    config = get_model_config(language)

    if dataset_path is not None:
        with Path(dataset_path).open(encoding="utf-8") as f:
            rows = [{"code": r["code"], "label": int(r["label"])} for r in csv.DictReader(f)]
    else:
        rows = load_dataset(language)
    _, eval_rows = train_test_split(rows)

    tokenizer = AutoTokenizer.from_pretrained(str(config.checkpoint_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(config.checkpoint_dir))
    model.eval()

    encodings = tokenizer(
        [r["code"] for r in eval_rows], truncation=True, padding="max_length", max_length=config.max_length,
        return_tensors="pt",
    )
    labels = [r["label"] for r in eval_rows]

    with torch.no_grad():
        logits = model(**encodings).logits
        preds = torch.argmax(logits, dim=-1).numpy()

    metrics = {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision_score(labels, preds, zero_division=0),
        "recall": recall_score(labels, preds, zero_division=0),
        "f1": f1_score(labels, preds, zero_division=0),
        "n_test_examples": len(labels),
        "report": classification_report(labels, preds, target_names=["not_vulnerable", "vulnerable"], zero_division=0),
    }

    out_path = config.checkpoint_dir / "eval_results.json"
    out_path.write_text(json.dumps({k: v for k, v in metrics.items() if k != "report"}, indent=2))

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a fine-tuned Layer 2 checkpoint.")
    parser.add_argument("--language", required=True, choices=SUPPORTED_ML_LANGUAGES)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    metrics = evaluate(args.language, dataset_path=args.dataset, use_synthetic=args.synthetic)
    print(f"accuracy={metrics['accuracy']:.3f} precision={metrics['precision']:.3f} "
          f"recall={metrics['recall']:.3f} f1={metrics['f1']:.3f}")
    print(metrics["report"])


if __name__ == "__main__":
    main()
