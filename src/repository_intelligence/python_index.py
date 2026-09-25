"""Source-bound Python function locator using the standard-library parser."""

from __future__ import annotations

import ast
import hashlib
import io
import tokenize
from pathlib import Path

from .declarations import declaration
from .declarations import assign_named_ids
from .source import physical_lines


def _signatures(source: bytes) -> dict[tuple[int, str], str]:
    """Locate Python headers with tokenizer coordinates, including inline bodies."""
    encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
    text = source.decode(encoding)
    lines = physical_lines(text)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    normalized = "".join(line.rstrip("\r\n") + "\n"
                         if line.endswith(("\r", "\n")) else line for line in lines)
    items = list(tokenize.generate_tokens(io.StringIO(normalized).readline))
    signatures: dict[tuple[int, str], str] = {}
    for position, token in enumerate(items[:-1]):
        if token.type != tokenize.NAME or token.string != "def":
            continue
        name = items[position + 1]
        if name.type != tokenize.NAME:
            continue
        first = token
        if position and items[position - 1].string == "async" \
                and items[position - 1].start[0] == token.start[0]:
            first = items[position - 1]
        depth = 0
        for part in items[position + 2:]:
            if part.type != tokenize.OP:
                continue
            if part.string in "([{":
                depth += 1
            elif part.string in ")]}":
                depth -= 1
            elif part.string == ":" and depth == 0:
                begin = starts[first.start[0] - 1] + first.start[1]
                end = starts[part.end[0] - 1] + part.end[1]
                signatures[(first.start[0], name.string)] = text[begin:end]
                break
    return signatures


def index_file(path: Path) -> dict:
    return index_source(path, path.read_bytes())


def index_source(path: Path, source: bytes) -> dict:
    """Parse the same bytes the caller identified; never reopen the file."""
    if len(source) > 4_000_000:
        raise ValueError("Python source exceeds the 4 MB per-file limit")
    tree = ast.parse(source, filename=str(path))
    signatures = _signatures(source)
    functions: list[dict] = []
    encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
    raw_lines = physical_lines(source)
    codec = "utf-8" if encoding == "utf-8-sig" else encoding
    text_lines = [line.decode(encoding if index == 0 else codec)
                  for index, line in enumerate(raw_lines)]
    starts = [0]
    for line in raw_lines:
        starts.append(starts[-1] + len(line))

    def offset(line: int, column: int) -> int:
        # AST columns count UTF-8 bytes even in a declared non-UTF-8 file.
        prefix = text_lines[line - 1].encode("utf-8")[:column].decode("utf-8")
        bom = 3 if line == 1 and encoding == "utf-8-sig" else 0
        return starts[line - 1] + bom + len(prefix.encode(codec))

    def display_column(line: int, column: int) -> int:
        """One-based Unicode character column, distinct from AST byte column."""
        return len(text_lines[line - 1].encode("utf-8")[:column].decode("utf-8")) + 1

    def position(node: ast.expr | ast.stmt) -> tuple[int, int]:
        return offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset)

    class Collector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.owners: tuple[str, ...] = ()

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self._visit_owner(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function(node)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            start, end = position(node)
            name = f"<lambda@{start}>"
            qualified = ".".join((*self.owners, name))
            calls = {ast.unparse(child.func) for child in ast.walk(node)
                     if isinstance(child, ast.Call)}
            functions.append({
                "name": name, "qualified_name": qualified,
                "line": node.lineno, "column": display_column(node.lineno, node.col_offset),
                "end_line": node.end_lineno,
                "signature": "lambda", "docs": "",
                "lexical_call_candidates": sorted(calls),
                **declaration(source, "lambda", qualified, start, end),
            })
            prior = self.owners
            self.owners += (name,)
            self.generic_visit(node)
            self.owners = prior

        def _visit_owner(self, node: ast.ClassDef) -> None:
            prior = self.owners
            self.owners += (node.name,)
            self.generic_visit(node)
            self.owners = prior

        def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            header = signatures.get((node.lineno, node.name))
            if header is None:
                raise ValueError(f"Could not locate function header at line {node.lineno}")
            calls = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    name = ast.unparse(child.func)
                    calls.add(name)
            start, end = position(node)
            if node.decorator_list:
                first = node.decorator_list[0]
                decorator_start, _ = position(first)
                line_start = starts[first.lineno - 1]
                prefix = source[line_start:decorator_start]
                marker = prefix.rfind(b"@")
                if marker < 0:
                    raise ValueError(f"Could not locate decorator at line {first.lineno}")
                start = line_start + marker
            qualified = ".".join((*self.owners, node.name))
            functions.append({
                "name": node.name,
                "qualified_name": qualified,
                "line": node.lineno,
                "column": display_column(node.lineno, node.col_offset),
                "end_line": node.end_lineno,
                "signature": header,
                "docs": ast.get_docstring(node) or "",
                "lexical_call_candidates": sorted(calls),
                **declaration(source, "function", qualified, start, end),
            })
            prior = self.owners
            self.owners += (node.name,)
            self.generic_visit(node)
            self.owners = prior

    Collector().visit(tree)
    assign_named_ids(functions)
    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    return {"path": str(path), "raw_sha256": hashlib.sha256(source).hexdigest(),
            "git_blob_sha1": blob, "function_count": len(functions),
            "parse_error_count": 0, "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
