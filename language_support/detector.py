"""Detects the programming language of an input file.

Strategy: fast extension lookup first (covers the overwhelming majority of
real files); falls back to `pygments` content-based lexer guessing only for
ambiguous or extensionless files. Pygments is lightweight, actively
maintained, and has no heavy ML dependency chain (unlike `guesslang`, which
pulls in an outdated, unmaintained TensorFlow pin).
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

# Pygments lexer aliases don't always match our internal language names
# (e.g. pygments says "c++" / "cpp", "shell" / "bash", "yaml" varies by
# version). Normalize the common ones here so downstream routing
# (language_registry.py) sees the same names it would from EXTENSION_MAP.
_PYGMENTS_ALIAS_MAP: dict[str, str] = {
    "python3": "python",
    "py3": "python",
    "js": "javascript",
    "node.js": "javascript",
    "typescript": "typescript",
    "c++": "cpp",
    "cplusplus": "cpp",
    "shell": "bash",
    "shell-session": "bash",
    "console": "bash",
    "c#": "csharp",
    "yml": "yaml",
}


class LanguageDetector:
    """Detects language for a single file, with an optional pygments fallback."""

    def __init__(self, use_content_fallback: bool = True) -> None:
        self.use_content_fallback = use_content_fallback

    def detect_file(self, file_path: str | os.PathLike) -> str | None:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        if not self.use_content_fallback:
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

        if not self.use_content_fallback:
            return None
        return self._detect_by_content_string(code)

    def _detect_by_content(self, path: Path) -> str | None:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return self._detect_by_content_string(text)

    def _detect_by_content_string(self, text: str) -> str | None:
        if not text.strip():
            return None
        try:
            from pygments.lexers import guess_lexer
            from pygments.util import ClassNotFound
        except ImportError:
            return None

        try:
            lexer = guess_lexer(text)
        except ClassNotFound:
            return None

        if not lexer.aliases:
            return None

        alias = lexer.aliases[0].lower()
        return _PYGMENTS_ALIAS_MAP.get(alias, alias)


def detect_directory(root: str | os.PathLike, use_content_fallback: bool = True) -> dict[str, str]:
    """Detects languages for every file under `root`. Returns {relative_path: language}."""
    detector = LanguageDetector(use_content_fallback=use_content_fallback)
    root_path = Path(root)
    results: dict[str, str] = {}
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        language = detector.detect_file(file_path)
        if language:
            results[str(file_path.relative_to(root_path))] = language
    return results