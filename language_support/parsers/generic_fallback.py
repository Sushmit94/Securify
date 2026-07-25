"""Fallback for Tier 3 languages with no dedicated parser.

Treats the whole file as a single code unit. This is sufficient for the LLM
reasoning layer, which is the only layer that runs for these languages
anyway (see language_registry.DEFAULT_FALLBACK).
"""
from __future__ import annotations

from language_support.parsers import CodeUnit


def extract_functions(code: str, file_path: str | None = None) -> list[CodeUnit]:
    if not code.strip():
        return []
    lines = code.splitlines()
    return [CodeUnit(name="<file>", start_line=1, end_line=len(lines) or 1, code=code)]
