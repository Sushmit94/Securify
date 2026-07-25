"""Fine-tunes CodeBERT for binary vulnerability classification.

    python ml_model/train.py --language python --synthetic
    python ml_model/train.py --language java --dataset data/processed/java.csv

This is the only layer in the framework that involves actual model training
(Layers 1 and 3 use existing tools/models as-is, per the README). Requires
torch + transformers (see requirements.txt); these are imported lazily so the
rest of the codebase can be used without them installed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.dataset_loader import generate_synthetic_sample, load_dataset, train_test_split  # noqa: E402
from ml_model.model_config import SUPPORTED_ML_LANGUAGES, get_model_config  # noqa: E402


def _import_ml_deps():
    try:
        import numpy as np
        import torch
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Missing ML dependencies. Install them with `pip install -r requirements.txt` "
            f"(torch + transformers + scikit-learn + numpy). Original error: {exc}"
        )
    return np, torch, (accuracy_score, f1_score, precision_score, recall_score), (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )


class _TorchTextDataset:
    """Thin wrapper so a list of tokenized encodings works with transformers' Trainer."""

    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        import torch

        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item


def train(language: str, dataset_path: Path | None = None, use_synthetic: bool = False, epochs: int | None = None) -> Path:
    if language not in SUPPORTED_ML_LANGUAGES:
        raise ValueError(f"Layer 2 only supports fine-tuning for: {SUPPORTED_ML_LANGUAGES}")

    if use_synthetic:
        generate_synthetic_sample(language)

    config = get_model_config(language, **({"num_epochs": epochs} if epochs else {}))

    if dataset_path is not None:
        import csv

        with Path(dataset_path).open(encoding="utf-8") as f:
            rows = [{"code": r["code"], "label": int(r["label"])} for r in csv.DictReader(f)]
    else:
        rows = load_dataset(language)
    train_rows, eval_rows = train_test_split(rows)

    np, torch, metric_fns, hf = _import_ml_deps()
    accuracy_score, f1_score, precision_score, recall_score = metric_fns
    AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments = hf

    tokenizer = AutoTokenizer.from_pretrained(config.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(config.base_model, num_labels=config.num_labels)

    def tokenize(rows: list[dict]):
        return tokenizer(
            [r["code"] for r in rows],
            truncation=True,
            padding="max_length",
            max_length=config.max_length,
        )

    train_dataset = _TorchTextDataset(tokenize(train_rows), [r["label"] for r in train_rows])
    eval_dataset = _TorchTextDataset(tokenize(eval_rows), [r["label"] for r in eval_rows])

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {
            "accuracy": accuracy_score(labels, preds),
            "precision": precision_score(labels, preds, zero_division=0),
            "recall": recall_score(labels, preds, zero_division=0),
            "f1": f1_score(labels, preds, zero_division=0),
        }

    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(config.checkpoint_dir),
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        seed=config.seed,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()

    trainer.save_model(str(config.checkpoint_dir))
    tokenizer.save_pretrained(str(config.checkpoint_dir))
    (config.checkpoint_dir / "training_metrics.json").write_text(json.dumps(metrics, indent=2))

    return config.checkpoint_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune the Layer 2 vulnerability classifier.")
    parser.add_argument("--language", required=True, choices=SUPPORTED_ML_LANGUAGES)
    parser.add_argument("--dataset", type=Path, default=None, help="Path to a preprocessed CSV dataset.")
    parser.add_argument("--synthetic", action="store_true", help="Generate a small synthetic sample dataset to smoke-test the pipeline.")
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()

    if not args.synthetic and args.dataset is None:
        parser.error("Provide --dataset <path> or pass --synthetic to smoke-test with a generated sample.")

    checkpoint_dir = train(args.language, dataset_path=args.dataset, use_synthetic=args.synthetic, epochs=args.epochs)
    print(f"Saved checkpoint to {checkpoint_dir}")


if __name__ == "__main__":
    main()
