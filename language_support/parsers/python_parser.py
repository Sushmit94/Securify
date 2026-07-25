"""Extracts function/method definitions from Python source using the stdlib `ast` module."""
from __future__ import annotations

import ast

from language_support.parsers import CodeUnit


def extract_functions(code: str, file_path: str | None = None) -> list[CodeUnit]:
    try:
        tree = ast.parse(code, filename=file_path or "<string>")
    except SyntaxError:
        return []

    lines = code.splitlines()
    units: list[CodeUnit] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            end_line = getattr(node, "end_lineno", node.lineno)
            qualified_name = ".".join([*self.class_stack, node.name])
            snippet = "\n".join(lines[node.lineno - 1 : end_line])
            units.append(
                CodeUnit(
                    name=qualified_name,
                    start_line=node.lineno,
                    end_line=end_line,
                    code=snippet,
                )
            )
            self.generic_visit(node)

        visit_FunctionDef = _visit_func
        visit_AsyncFunctionDef = _visit_func

    Visitor().visit(tree)

    if not units and code.strip():
        units.append(CodeUnit(name="<module>", start_line=1, end_line=len(lines) or 1, code=code))

    return units
