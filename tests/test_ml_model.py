import pytest

from data import dataset_loader
from ml_model import inference
from ml_model.model_config import get_model_config, has_trained_checkpoint


def test_get_model_config_rejects_unsupported_language():
    with pytest.raises(ValueError):
        get_model_config("cobol")


def test_get_model_config_returns_expected_checkpoint_dir():
    config = get_model_config("python")
    assert config.checkpoint_dir.name == "python_model"
    assert config.base_model == "microsoft/codebert-base"


def test_has_trained_checkpoint_false_for_empty_dir():
    assert has_trained_checkpoint("python") is False


def test_has_trained_checkpoint_false_for_unsupported_language():
    assert has_trained_checkpoint("cobol") is False


def test_generate_synthetic_sample_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset_loader, "PROCESSED_DATA_ROOT", tmp_path)
    path = dataset_loader.generate_synthetic_sample("python", repeat=2)

    assert path.exists()
    rows = dataset_loader.load_dataset("python")
    assert len(rows) > 0
    assert set(rows[0].keys()) == {"code", "label", "language"}
    assert all(r["label"] in (0, 1) for r in rows)


def test_train_test_split_ratio():
    rows = [{"code": str(i), "label": i % 2} for i in range(10)]
    train_rows, test_rows = dataset_loader.train_test_split(rows, test_ratio=0.2)
    assert len(train_rows) == 8
    assert len(test_rows) == 2


def test_inference_score_none_without_checkpoint():
    # No checkpoint exists in this environment, so Layer 2 must degrade gracefully
    # rather than raising -- this is the "never claim ML confidence we don't have" contract.
    assert inference.is_available("python") is False
    assert inference.score("python", "def f(): pass") is None
