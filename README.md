# AI-Based Framework for Automated Source Code Vulnerability Detection

A hybrid, multi-layer system that detects security vulnerabilities in source code by combining **static analysis**, a **fine-tuned machine learning classifier**, and **LLM-based reasoning**.

---

## Table of Contents

1. [Overview](#overview)
2. [Motivation](#motivation)
3. [System Design](#system-design)
4. [Architecture Layers Explained](#architecture-layers-explained)
5. [Language Support Strategy](#language-support-strategy)
6. [Tech Stack](#tech-stack)
7. [Folder Structure](#folder-structure)
8. [Datasets](#datasets)
9. [Setup & Installation](#setup--installation)
10. [Usage](#usage)
11. [Model Training (Fine-Tuning)](#model-training-fine-tuning)
12. [Evaluation Metrics](#evaluation-metrics)
13. [API Reference](#api-reference)
14. [Project Timeline](#project-timeline)
15. [Limitations & Future Work](#limitations--future-work)
16. [References](#references)

---

## Overview

This project builds a framework that takes source code as input (a single file, multiple files, or a full GitHub repository) and produces a structured vulnerability report identifying:

- **What** the vulnerability is (e.g., SQL injection, XSS, buffer overflow, hardcoded credentials, insecure deserialization)
- **Where** it is located (file, line number, function)
- **How confident** the system is in the finding
- **Why** it's a vulnerability (plain-English explanation)
- **How to fix it** (suggested remediation)

Unlike a purely rule-based static analyzer or a purely LLM-based tool, this framework combines three independent detection layers and reconciles their outputs, aiming for **higher precision and richer explanations than any single approach alone.**

---

## Motivation

Existing approaches typically fall into one of two camps:

- **Static analyzers** (Semgrep, Bandit, SonarQube) are fast and deterministic but rule-based — they miss novel or context-dependent vulnerabilities and often produce false positives.
- **Pure LLM-based tools** are flexible and can reason about context, but are non-deterministic, can hallucinate, and are expensive to run on large codebases without any prior filtering.

This project combines both, plus a supervised ML classifier trained on labeled vulnerability data, so that:
- Static analysis provides fast, deterministic first-pass detection.
- The ML classifier adds a learned, data-driven signal for languages where labeled datasets exist.
- The LLM reasoning layer explains findings, suggests fixes, filters false positives, and extends coverage to languages without a trained classifier.

---

## System Design

```
                    ┌─────────────────────────┐
                    │   Code Input (any lang)  │
                    │  file / repo / snippet   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Language Detector       │
                    │  (extension + guesslang) │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Language-specific       │
                    │  Parser / Router         │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌─────────▼─────────┐   ┌─────────▼─────────┐
│ Layer 1:        │    │ Layer 2:          │   │ Layer 3:           │
│ Static Analysis │    │ ML Classifier     │   │ LLM Reasoning      │
│ Semgrep ruleset │    │ (runs only if a   │   │ (works regardless  │
│ per language    │    │ trained model     │   │ of language)       │
│ (30+ languages) │    │ exists for lang)  │   │                    │
└───────┬────────┘    └─────────┬─────────┘   └─────────┬─────────┘
        │             (skipped for unsupported langs)     │
        └───────────────────────┼────────────────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Aggregator / Scorer     │
                    │  merges findings, dedupes│
                    │  weights confidence based│
                    │  on which layers ran     │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Report Generator        │
                    │  (JSON, HTML, PDF)       │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Web Dashboard (React)   │
                    │  upload, view, export    │
                    └─────────────────────────┘
```

### Data flow, step by step

1. **Input** — user uploads a file, pastes a snippet, or provides a repo URL.
2. **Language Detector** — identifies the language of each file via extension, falling back to a lightweight classifier (`guesslang`) for ambiguous or extensionless files.
3. **Parser/Router** — parses the code into an AST (where a parser exists for that language) and extracts functions/code units for analysis; routes the code to the appropriate rulesets and models.
4. **Layer 1 (Static Analysis)** — Semgrep (and Bandit for Python specifically) scans against a language-specific ruleset and returns deterministic pattern-based findings.
5. **Layer 2 (ML Classifier)** — for languages with a trained model (initially Python, Java, C/C++), each function is tokenized and passed through a fine-tuned CodeBERT/GraphCodeBERT model, which outputs a vulnerability probability score. Skipped for unsupported languages.
6. **Layer 3 (LLM Reasoning)** — the code, along with Layer 1 and Layer 2 findings, is sent to an LLM via API with a structured prompt. The LLM confirms/rejects findings, explains them, and suggests fixes. This layer works for any language.
7. **Aggregator** — merges and deduplicates findings across layers, assigns a final confidence score (weighted differently depending on which layers actually ran for that language), and ranks results by severity.
8. **Report Generator** — produces a structured JSON report plus a human-readable HTML/PDF version.
9. **Dashboard** — a React frontend for uploading code, browsing findings, and exporting reports.

---

## Architecture Layers Explained

### Layer 1 — Static Analysis
- **Tools:** Semgrep (primary, 30+ language support), Bandit (Python-specific, deeper AST-based checks)
- **Output:** deterministic findings with rule ID, file, line, severity, CWE reference
- **Role:** fast first pass, catches well-known vulnerability patterns

### Layer 2 — ML Classifier (fine-tuned)
- **Base model:** CodeBERT or GraphCodeBERT (HuggingFace, ~125M parameters)
- **Fine-tuned on:** Devign, Big-Vul, and/or SARD/Juliet Test Suite (labeled vulnerable/safe function pairs)
- **Output:** a vulnerability probability score (0–1) per function
- **Role:** learned, data-driven signal that can catch patterns static rules miss; only available for languages with sufficient labeled training data
- **Note:** this is the only layer that involves actual model training (fine-tuning); Layers 1 and 3 use existing tools/models as-is

### Layer 3 — LLM Reasoning
- **Model:** an existing large language model accessed via API (e.g., Claude or GPT-4) — not trained or fine-tuned
- **Input:** the code snippet + Layer 1 findings + Layer 2 score (when available)
- **Output:** structured JSON containing confirmed/rejected findings, plain-English explanations, and suggested fixes
- **Role:** contextual reasoning, false-positive filtering, and coverage for any language regardless of ML/static tool support

### Aggregator
- Deduplicates overlapping findings from different layers referring to the same line/function
- Weights confidence based on **which layers actually contributed** — e.g., a finding confirmed by all three layers is weighted higher than one from static analysis alone
- Produces a final ranked list of vulnerabilities per file

---

## Language Support Strategy

Since Layer 2 realistically cannot be trained for every language (limited labeled datasets exist beyond a handful of languages), coverage is intentionally tiered:

| Tier | Languages | Layers Active |
|---|---|---|
| Tier 1 (deep coverage) | Python, Java, C/C++ | Static Analysis + ML Classifier + LLM Reasoning |
| Tier 2 (broad coverage) | JavaScript/TypeScript, Go, PHP, Ruby, C#, Kotlin, Rust, and other Semgrep-supported languages | Static Analysis + LLM Reasoning |
| Tier 3 (fallback) | Any other language | LLM Reasoning only (no static ruleset or trained model) |

This tiered approach is documented transparently in the report output — the framework never claims ML-based confidence for a language it wasn't trained on.

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Static analysis | Semgrep, Bandit | Rule-based vulnerability detection |
| ML framework | PyTorch, HuggingFace Transformers | Fine-tuning CodeBERT/GraphCodeBERT |
| Dataset handling | Pandas, HuggingFace Datasets | Loading/preprocessing Devign, Big-Vul |
| LLM integration | Claude API / OpenAI API | Reasoning, explanation, fix suggestions |
| Backend | Python, FastAPI | Orchestration, REST API |
| Language detection | File extension mapping + `guesslang` | Routing code to correct pipeline |
| Code parsing | `ast` (Python), `esprima`/`@babel/parser` (JS), `javalang` (Java), `pycparser`/`clang` bindings (C/C++) | Extracting functions for analysis |
| Frontend | React, Tailwind CSS | Dashboard UI |
| Database | PostgreSQL | Scan history, findings storage |
| Report generation | WeasyPrint / ReportLab | PDF export |
| Experiment tracking | Weights & Biases (optional) | Logging fine-tuning runs |
| Containerization | Docker, Docker Compose | Reproducible deployment |
| Testing | Pytest | Unit and integration tests |

---

## Folder Structure

```
vuln-detection-framework/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
│
├── data/
│   ├── raw/
│   │   ├── python/
│   │   ├── java/
│   │   └── cpp/
│   ├── processed/
│   └── dataset_loader.py
│
├── language_support/
│   ├── detector.py               # detects language of input file
│   ├── language_registry.py      # maps language -> {ruleset, ml_model?, parser}
│   └── parsers/
│       ├── python_parser.py
│       ├── js_parser.py
│       ├── java_parser.py
│       ├── cpp_parser.py
│       └── generic_fallback.py
│
├── ml_model/
│   ├── train.py                  # fine-tuning script
│   ├── evaluate.py                # precision/recall/F1 on test set
│   ├── model_config.py
│   ├── inference.py
│   └── checkpoints/
│       ├── python_model/
│       ├── java_model/
│       └── cpp_model/
│
├── static_analysis/
│   ├── semgrep_runner.py
│   ├── bandit_runner.py
│   └── rulesets/
│       ├── python.yml
│       ├── javascript.yml
│       ├── java.yml
│       ├── cpp.yml
│       └── go.yml
│
├── llm_reasoning/
│   ├── prompt_templates.py
│   ├── llm_client.py
│   └── response_parser.py
│
├── aggregator/
│   ├── merge_findings.py
│   └── scorer.py
│
├── backend/
│   ├── main.py
│   ├── routes/
│   │   ├── scan.py
│   │   └── report.py
│   ├── models/
│   └── services/
│       └── pipeline.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.jsx
│   └── package.json
│
├── reports/
│   └── generator.py
│
├── tests/
│   ├── test_static_analysis.py
│   ├── test_ml_model.py
│   ├── test_llm_reasoning.py
│   └── test_pipeline.py
│
└── docs/
    ├── system_design.md
    ├── language_coverage.md
    ├── dataset_notes.md
    └── evaluation_results.md
```

---

## Datasets

| Dataset | Language(s) | Description |
|---|---|---|
| **Devign** | C/C++ | Function-level vulnerable/non-vulnerable labels from real open-source projects |
| **Big-Vul** | C/C++ | Large-scale vulnerability dataset with CVE mappings |
| **SARD / Juliet Test Suite** | C/C++, Java | Synthetic test cases covering many CWE categories |
| **CVEfixes** | Multiple | Real-world CVE fix commits mapped to vulnerable/patched code pairs |

These are used to fine-tune the Layer 2 ML classifier for the Tier 1 languages.

---

## Setup & Installation

```bash
# Clone the repository
git clone <repo-url>
cd vuln-detection-framework

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # .\venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Set up environment variables
cp .env.example .env
# Add your LLM API key and database URL to .env

# Run with Docker Compose (recommended)
docker-compose up --build
```

---

## Usage

```bash
# Run a scan on a single file
python backend/services/pipeline.py --input path/to/file.py

# Run a scan on a full repository
python backend/services/pipeline.py --repo https://github.com/user/repo

# Start the API server
uvicorn backend.main:app --reload

# Start the frontend dashboard
cd frontend && npm start
```

Example JSON output:

```json
{
  "file": "app/routes/login.py",
  "language": "python",
  "findings": [
    {
      "line": 42,
      "type": "SQL Injection",
      "cwe": "CWE-89",
      "confidence": 0.93,
      "sources": ["static_analysis", "ml_classifier", "llm_reasoning"],
      "explanation": "User input is concatenated directly into a SQL query without parameterization.",
      "suggested_fix": "Use parameterized queries via the database driver's placeholder syntax."
    }
  ]
}
```

---

## Model Training (Fine-Tuning)

Only Layer 2 involves actual training. High-level steps:

1. Download and preprocess Devign/Big-Vul/SARD datasets (`data/dataset_loader.py`)
2. Tokenize functions using the CodeBERT tokenizer
3. Fine-tune CodeBERT for binary classification (vulnerable / not vulnerable) using `ml_model/train.py`
4. Track experiments (loss, accuracy, F1) with Weights & Biases
5. Evaluate on a held-out test set (`ml_model/evaluate.py`)
6. Save checkpoints per language under `ml_model/checkpoints/`

Repeat separately for each Tier 1 language (Python, Java, C/C++), since each requires its own fine-tuned checkpoint.

---

## Evaluation Metrics

The framework is evaluated using:

- **Precision, Recall, F1-score** — per language, per vulnerability category
- **False positive rate** — before vs. after LLM reasoning layer filters static analysis output
- **Layer contribution analysis** — how many true positives each layer uniquely catches
- **Latency** — average scan time per file/repo size

Results are logged in `docs/evaluation_results.md`.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/scan/file` | POST | Upload a single file for scanning |
| `/scan/repo` | POST | Submit a GitHub repo URL for scanning |
| `/report/{scan_id}` | GET | Retrieve findings for a completed scan |
| `/report/{scan_id}/pdf` | GET | Download PDF report |
| `/history` | GET | List past scans |

---

## Project Timeline

| Phase | Weeks | Deliverable |
|---|---|---|
| Literature review + dataset selection | 1–2 | Finalized dataset choice, repo skeleton |
| Static analysis layer | 3–4 | Working Semgrep/Bandit integration |
| ML classifier fine-tuning | 5–8 | Trained CodeBERT checkpoints (Tier 1 languages) |
| LLM reasoning layer | 9–10 | Prompt design, structured output parsing |
| Aggregator + scoring | 11–12 | Merged, weighted findings pipeline |
| Backend + frontend | 13–14 | Working API and dashboard |
| Evaluation + writeup | 15+ | Metrics, final report, documentation |

---

## Limitations & Future Work

- ML classifier coverage is limited to languages with sufficient labeled data; expanding to more languages requires new labeled datasets or transfer learning approaches.
- LLM reasoning layer depends on an external API — introduces cost and latency considerations at scale.
- Current design analyzes function-level context; whole-program/cross-file data-flow vulnerabilities (e.g., taint tracking across files) are a possible future extension.
- Future work could explore fine-tuning a single multilingual classifier (e.g., using UniXcoder or CodeT5+) to reduce the need for per-language checkpoints.

---

## References

- Zhou et al., "Devign: Effective Vulnerability Identification by Learning Comprehensive Program Semantics via Graph Neural Networks"
- Fan et al., "A C/C++ Code Vulnerability Dataset with Code Changes and CVE Summaries" (Big-Vul)
- Feng et al., "CodeBERT: A Pre-Trained Model for Programming and Natural Languages"
- Guo et al., "GraphCodeBERT: Pre-training Code Representations with Data Flow"
- Semgrep documentation: https://semgrep.dev/docs/
- NIST SARD / Juliet Test Suite: https://samate.nist.gov/SARD/
