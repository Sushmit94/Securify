"""Detects the programming language of an input file.

Strategy: fast extension lookup first (covers the overwhelming majority of
real files); falls back to `guesslang` content-based classification only for
ambiguous or extensionless files, since guesslang is slow and occasionally
wrong on short snippets.
"""
from __future__ import annotations

import os
from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".go": "go",
    ".php": "php",
    ".rb": "ruby",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rs": "rust",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".tf": "terraform",
}


class LanguageDetector:
    """Detects language for a single file, with an optional guesslang fallback."""

    def __init__(self, use_guesslang_fallback: bool = True) -> None:
        self.use_guesslang_fallback = use_guesslang_fallback
        self._guesser = None  # lazily constructed; guesslang is an optional, heavier dependency

    def detect_file(self, file_path: str | os.PathLike) -> str | None:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        if not self.use_guesslang_fallback:
            return None

        try:
            return self._detect_by_content(path)
        except (OSError, UnicodeDecodeError):
            return None

    def detect_snippet(self, code: str, hint_filename: str | None = None) -> str | None:
        """Detect the language of an in-memory code snippet (e.g. pasted code)."""
        if hint_filename:
            ext = Path(hint_filename).suffix.lower()
            if ext in EXTENSION_MAP:
                return EXTENSION_MAP[ext]

        if not self.use_guesslang_fallback:
            return None
        return self._detect_by_content_string(code)

    def _detect_by_content(self, path: Path) -> str | None:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return self._detect_by_content_string(text)

    def _detect_by_content_string(self, text: str) -> str | None:
        if not text.strip():
            return None
        if self._guesser is None:
            self._guesser = self._load_guesser()
        if self._guesser is None:
            return None
        try:
            return self._guesser.language_name(text).lower()
        except Exception:
            return None

    @staticmethod
    def _load_guesser():
        try:
            from guesslang import Guess  # type: ignore
        except ImportError:
            return None
        return Guess()


def detect_directory(root: str | os.PathLike, use_guesslang_fallback: bool = True) -> dict[str, str]:
    """Detects languages for every file under `root`. Returns {relative_path: language}."""
    detector = LanguageDetector(use_guesslang_fallback=use_guesslang_fallback)
    root_path = Path(root)
    results: dict[str, str] = {}
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        language = detector.detect_file(file_path)
        if language:
            results[str(file_path.relative_to(root_path))] = language
    return results
