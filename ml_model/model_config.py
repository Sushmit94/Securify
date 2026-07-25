"""Configuration for fine-tuning and running the Layer 2 ML classifier.

One config per Tier 1 language (Python, Java, C/C++) since each gets its own
fine-tuned checkpoint, per the README's language support strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CHECKPOINTS_ROOT = Path(__file__).resolve().parent / "checkpoints"
PROCESSED_DATA_ROOT = Path(__file__).resolve().parent.parent / "data" / "processed"

BASE_MODEL = "microsoft/codebert-base"
NUM_LABELS = 2  # binary: vulnerable / not vulnerable
LABEL_NAMES = ["not_vulnerable", "vulnerable"]


@dataclass(frozen=True)
class ModelConfig:
    language: str
    base_model: str = BASE_MODEL
    max_length: int = 512
    num_labels: int = NUM_LABELS
    batch_size: int = 8
    learning_rate: float = 2e-5
    num_epochs: int = 4
    weight_decay: float = 0.01
    seed: int = 42

    @property
    def checkpoint_dir(self) -> Path:
        return CHECKPOINTS_ROOT / f"{self.language}_model"

    @property
    def processed_dataset_path(self) -> Path:
        return PROCESSED_DATA_ROOT / f"{self.language}.csv"


SUPPORTED_ML_LANGUAGES = ["python", "java", "cpp"]


def get_model_config(language: str, **overrides) -> ModelConfig:
    if language not in SUPPORTED_ML_LANGUAGES:
        raise ValueError(
            f"No ML classifier config for '{language}'. "
            f"Layer 2 is only trained for: {SUPPORTED_ML_LANGUAGES}."
        )
    return ModelConfig(language=language, **overrides)


def has_trained_checkpoint(language: str) -> bool:
    if language not in SUPPORTED_ML_LANGUAGES:
        return False
    checkpoint_dir = CHECKPOINTS_ROOT / f"{language}_model"
    if not checkpoint_dir.exists():
        return False
    return any(any(checkpoint_dir.glob(pattern)) for pattern in ("*.bin", "*.safetensors"))
