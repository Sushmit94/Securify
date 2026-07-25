"""Extracts function-like units from JavaScript/TypeScript source.

Uses `esprima` (pure-Python JS parser) when available, since it needs no
Node.js toolchain to run inside the Python backend. Falls back to a regex
heuristic if esprima is not installed or fails to parse (e.g. TSX/newer
syntax it doesn't support) so the rest of the pipeline still gets *something*
to analyze rather than nothing.
"""
from __future__ import annotations

import re

from language_support.parsers import CodeUnit

_FUNC_HEURISTIC = re.compile(
    r"^[ \t]*(?:export\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)?\s*\(",
    re.MULTILINE,
)
_ARROW_HEURISTIC = re.compile(
    r"^[ \t]*(?:export\s+)?const\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
    re.MULTILINE,
)


def extract_functions(code: str, file_path: str | None = None) -> list[CodeUnit]:
    units = _extract_with_esprima(code)
    if units:
        return units
    return _extract_with_regex(code)


def _extract_with_esprima(code: str) -> list[CodeUnit]:
    try:
        import esprima  # type: ignore
    except ImportError:
        return []

    try:
        tree = esprima.parseScript(code, options={"loc": True, "tolerant": True})
    except Exception:
        try:
            tree = esprima.parseModule(code, options={"loc": True, "tolerant": True})
        except Exception:
            return []

    lines = code.splitlines()
    units: list[CodeUnit] = []

    def walk(node, name_hint: str | None = None) -> None:
        if node is None or not hasattr(node, "type"):
            return
        node_type = getattr(node, "type", None)
        if node_type in ("FunctionDeclaration", "FunctionExpression", "ArrowFunctionExpression"):
            loc = getattr(node, "loc", None)
            if loc is not None:
                start, end = loc.start.line, loc.end.line
                name = getattr(node, "id", None)
                fname = (name.name if name else None) or name_hint or "<anonymous>"
                units.append(
                    CodeUnit(
                        name=fname,
                        start_line=start,
                        end_line=end,
                        code="\n".join(lines[start - 1 : end]),
                    )
                )
        for attr in vars(node):
            if attr in ("type", "loc", "range"):
                continue
            value = getattr(node, attr)
            hint = value.name if attr == "id" and hasattr(value, "name") else (
                node.id.name if node_type == "VariableDeclarator" and hasattr(node, "id") and hasattr(node.id, "name") else None
            )
            if isinstance(value, list):
                for item in value:
                    walk(item, hint)
            elif hasattr(value, "type"):
                walk(value, hint)

    walk(tree)
    return units


def _extract_with_regex(code: str) -> list[CodeUnit]:
    lines = code.splitlines()
    units: list[CodeUnit] = []
    for pattern in (_FUNC_HEURISTIC, _ARROW_HEURISTIC):
        for match in pattern.finditer(code):
            start_line = code.count("\n", 0, match.start()) + 1
            end_line = _find_block_end(lines, start_line)
            units.append(
                CodeUnit(
                    name=match.group("name") or "<anonymous>",
                    start_line=start_line,
                    end_line=end_line,
                    code="\n".join(lines[start_line - 1 : end_line]),
                )
            )
    if not units and code.strip():
        units.append(CodeUnit(name="<module>", start_line=1, end_line=len(lines) or 1, code=code))
    return units


def _find_block_end(lines: list[str], start_line: int) -> int:
    """Balances braces starting from `start_line` to approximate a function body's end."""
    depth = 0
    started = False
    for idx in range(start_line - 1, len(lines)):
        depth += lines[idx].count("{") - lines[idx].count("}")
        if "{" in lines[idx]:
            started = True
        if started and depth <= 0:
            return idx + 1
    return min(start_line + 40, len(lines))
