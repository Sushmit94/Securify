"""Loads and preprocesses vulnerability datasets for Layer 2 fine-tuning.

Supports the real datasets named in the README (Devign, Big-Vul, SARD/Juliet,
CVEfixes) when they've been downloaded into data/raw/<language>/, and also
provides `generate_synthetic_sample()` — a small, clearly-labeled synthetic
dataset used to smoke-test the training/evaluation pipeline end-to-end
without requiring a multi-GB download or GPU time. Real experiments should
use `load_dataset()` against actual downloaded data, not the synthetic set.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

RAW_DATA_ROOT = Path(__file__).resolve().parent / "raw"
PROCESSED_DATA_ROOT = Path(__file__).resolve().parent / "processed"

# Columns expected by ml_model/train.py and ml_model/evaluate.py.
CSV_COLUMNS = ["code", "label", "language"]

# A handful of hand-written vulnerable/safe function pairs per language, used
# purely to exercise the training pipeline (tokenize -> fine-tune -> eval ->
# save checkpoint) without a real dataset. Not suitable for a real classifier.
_SYNTHETIC_PAIRS: dict[str, list[tuple[str, int]]] = {
    "python": [
        ("def get_user(uid):\n    cur.execute(\"SELECT * FROM users WHERE id=\" + uid)\n    return cur.fetchone()", 1),
        ("def get_user(uid):\n    cur.execute(\"SELECT * FROM users WHERE id=%s\", (uid,))\n    return cur.fetchone()", 0),
        ("def run(cmd):\n    os.system(cmd)", 1),
        ("def run(cmd):\n    subprocess.run(cmd, shell=False)", 0),
        ("def load(data):\n    return pickle.loads(data)", 1),
        ("def load(data):\n    return json.loads(data)", 0),
        ("def hash_pw(pw):\n    return hashlib.md5(pw.encode()).hexdigest()", 1),
        ("def hash_pw(pw):\n    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt())", 0),
    ],
    "java": [
        ("Statement s = c.createStatement();\ns.executeQuery(\"SELECT * FROM t WHERE id=\" + id);", 1),
        ("PreparedStatement s = c.prepareStatement(\"SELECT * FROM t WHERE id=?\");\ns.setString(1, id);", 0),
        ("Runtime.getRuntime().exec(\"sh -c \" + userInput);", 1),
        ("ProcessBuilder pb = new ProcessBuilder(\"ls\", \"-l\");\npb.start();", 0),
        ("ObjectInputStream ois = new ObjectInputStream(in);\nObject o = ois.readObject();", 1),
        ("ObjectMapper mapper = new ObjectMapper();\nMyType o = mapper.readValue(in, MyType.class);", 0),
    ],
    "cpp": [
        ("void copy(char* dst, char* src) {\n    strcpy(dst, src);\n}", 1),
        ("void copy(char* dst, size_t n, const char* src) {\n    strncpy(dst, src, n);\n}", 0),
        ("void log(char* fmt) {\n    printf(fmt);\n}", 1),
        ("void log(const char* msg) {\n    printf(\"%s\", msg);\n}", 0),
        ("char buf[8];\ngets(buf);", 1),
        ("char buf[8];\nfgets(buf, sizeof(buf), stdin);", 0),
    ],
}


def generate_synthetic_sample(language: str, repeat: int = 20, seed: int = 42) -> Path:
    """Writes a synthetic labeled dataset to data/processed/<language>.csv and returns its path."""
    if language not in _SYNTHETIC_PAIRS:
        raise ValueError(f"No synthetic samples defined for '{language}'.")

    rng = random.Random(seed)
    rows = list(_SYNTHETIC_PAIRS[language]) * repeat
    rng.shuffle(rows)

    PROCESSED_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DATA_ROOT / f"{language}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for code, label in rows:
            writer.writerow([code, label, language])
    return out_path


def load_dataset(language: str) -> list[dict]:
    """Loads a processed CSV dataset for a language into a list of {code, label, language} dicts."""
    path = PROCESSED_DATA_ROOT / f"{language}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"No processed dataset at {path}. Run generate_synthetic_sample('{language}') for a "
            f"smoke-test dataset, or preprocess a real dataset (Devign/Big-Vul/SARD) into this path."
        )
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{"code": row["code"], "label": int(row["label"]), "language": row["language"]} for row in reader]


def train_test_split(rows: list[dict], test_ratio: float = 0.2, seed: int = 42) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    shuffled = rows[:]
    rng.shuffle(shuffled)
    split_idx = max(1, int(len(shuffled) * (1 - test_ratio)))
    return shuffled[:split_idx], shuffled[split_idx:]
