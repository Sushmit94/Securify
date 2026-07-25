"""Extracts method definitions from Java source using `javalang`, with a regex fallback."""
from __future__ import annotations

import re

from language_support.parsers import CodeUnit

_METHOD_HEURISTIC = re.compile(
    r"^[ \t]*(?:public|private|protected|static|final|synchronized|abstract|\s)+"
    r"[\w<>\[\],\s]+\s+(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{",
    re.MULTILINE,
)


def extract_functions(code: str, file_path: str | None = None) -> list[CodeUnit]:
    units = _extract_with_javalang(code)
    if units:
        return units
    return _extract_with_regex(code)


def _extract_with_javalang(code: str) -> list[CodeUnit]:
    try:
        import javalang  # type: ignore
    except ImportError:
        return []

    try:
        tree = javalang.parse.parse(code)
    except Exception:
        return []

    lines = code.splitlines()
    units: list[CodeUnit] = []
    for _, node in tree.filter(javalang.tree.MethodDeclaration):
        if node.position is None:
            continue
        start = node.position.line
        end = _find_block_end(lines, start)
        units.append(
            CodeUnit(name=node.name, start_line=start, end_line=end, code="\n".join(lines[start - 1 : end]))
        )
    return units


def _extract_with_regex(code: str) -> list[CodeUnit]:
    lines = code.splitlines()
    units: list[CodeUnit] = []
    for match in _METHOD_HEURISTIC.finditer(code):
        start_line = code.count("\n", 0, match.start()) + 1
        end_line = _find_block_end(lines, start_line)
        units.append(
            CodeUnit(
                name=match.group("name"),
                start_line=start_line,
                end_line=end_line,
                code="\n".join(lines[start_line - 1 : end_line]),
            )
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
    return min(start_line + 60, len(lines))
