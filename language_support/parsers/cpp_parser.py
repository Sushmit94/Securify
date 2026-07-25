"""Extracts function definitions from C/C++ source.

Full AST parsing of C/C++ requires a preprocessor pass and compile flags
(pycparser needs macro-expanded, `#include`-free input; clang bindings need
a working libclang install), which isn't reliable for arbitrary uploaded
snippets. Instead this uses a brace-balancing heuristic tuned for typical
function-definition syntax, which is what most lightweight C/C++ scanners
do in practice.
"""
from __future__ import annotations

import re

from language_support.parsers import CodeUnit

_FUNC_HEURISTIC = re.compile(
    r"^[ \t]*(?:[\w:<>,\*&\s]+?)\s+(?P<name>[A-Za-z_~]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?\{",
    re.MULTILINE,
)
_CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "return"}


def extract_functions(code: str, file_path: str | None = None) -> list[CodeUnit]:
    lines = code.splitlines()
    units: list[CodeUnit] = []
    for match in _FUNC_HEURISTIC.finditer(code):
        name = match.group("name")
        if name in _CONTROL_KEYWORDS:
            continue
        start_line = code.count("\n", 0, match.start()) + 1
        end_line = _find_block_end(lines, start_line)
        units.append(
            CodeUnit(name=name, start_line=start_line, end_line=end_line, code="\n".join(lines[start_line - 1 : end_line]))
        )
    if not units and code.strip():
        units.append(CodeUnit(name="<file>", start_line=1, end_line=len(lines) or 1, code=code))
    return units


def _find_block_end(lines: list[str], start_line: int) -> int:
    depth = 0
    started = False
    for idx in range(start_line - 1, len(lines)):
        depth += lines[idx].count("{") - lines[idx].count("}")
        if "{" in lines[idx]:
            started = True
        if started and depth <= 0:
            return idx + 1
    return min(start_line + 80, len(lines))
