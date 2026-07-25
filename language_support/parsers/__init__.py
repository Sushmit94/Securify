"""Language-specific parsers.

Every parser module exposes a single function:

    extract_functions(code: str, file_path: str | None = None) -> list[CodeUnit]

where CodeUnit is a dict: {"name", "start_line", "end_line", "code"}.
This is the unit the ML classifier (Layer 2) scores and the unit the LLM
reasoning layer (Layer 3) is given as context, per file.
"""
from __future__ import annotations

from typing import TypedDict


class CodeUnit(TypedDict):
    name: str
    start_line: int
    end_line: int
    code: str
