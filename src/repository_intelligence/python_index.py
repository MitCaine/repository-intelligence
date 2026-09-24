"""Source-bound Python function locator using the standard-library parser."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from .search import compact


def index_file(path: Path) -> dict:
    source = path.read_bytes()
    if len(source) > 4_000_000:
        raise ValueError("Python source exceeds the 4 MB per-file limit")
    tree = ast.parse(source, filename=str(path))
    text = source.decode("utf-8", "replace")
    lines = text.splitlines(keepends=True)
    functions: list[dict] = []

    class Collector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.owners: tuple[str, ...] = ()

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self._visit_owner(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function(node)

        def _visit_owner(self, node: ast.ClassDef) -> None:
            prior = self.owners
            self.owners += (node.name,)
            self.generic_visit(node)
            self.owners = prior

        def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            first_body_line = node.body[0].lineno if node.body else node.end_lineno
            header = "".join(lines[node.lineno - 1:first_body_line - 1])
            if not header.strip() and node.lineno <= len(lines):
                header = lines[node.lineno - 1].split(":", 1)[0] + ":"
            calls = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    name = ast.unparse(child.func)
                    calls.add(compact(name, 80))
            functions.append({
                "name": node.name,
                "qualified_name": ".".join((*self.owners, node.name)),
                "line": node.lineno,
                "end_line": node.end_lineno,
                "signature": compact(header, 180),
                "docs": compact(ast.get_docstring(node) or "", 220),
                "lexical_call_candidates": sorted(calls)[:12],
            })
            prior = self.owners
            self.owners += (node.name,)
            self.generic_visit(node)
            self.owners = prior

    Collector().visit(tree)
    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    return {"path": str(path), "raw_sha256": hashlib.sha256(source).hexdigest(),
            "git_blob_sha1": blob, "function_count": len(functions),
            "parse_error_count": 0, "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
