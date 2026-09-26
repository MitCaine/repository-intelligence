"""Ordinary Python navigation from the pinned Tree-sitter grammar."""

from __future__ import annotations

import ast
import inspect
import unicodedata
from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage
from .source import python_source_encoding, utf8_display_column


def _text(parse_bytes: bytes, node) -> str:
    return parse_bytes[node.start_byte:node.end_byte].decode("utf-8")


def _calls(node, parse_bytes: bytes) -> list[str]:
    candidates = set()
    pending = [node]
    while pending:
        current = pending.pop()
        if current.type == "call":
            function = current.child_by_field_name("function")
            if function is not None:
                expression = _text(parse_bytes, function)
                try:
                    # Match the legacy AST candidate spelling; Tree-sitter still
                    # owns declaration discovery and all source coordinates.
                    candidate = ast.unparse(ast.parse(f"({expression})", mode="eval").body)
                except (SyntaxError, RecursionError):
                    candidate = expression
                candidates.add(candidate)
        pending.extend(current.named_children)
    return sorted(candidates)


def _docs(body, parse_bytes: bytes) -> str:
    if body is None or not body.named_children:
        return ""
    first = body.named_children[0]
    if first.type != "expression_statement":
        return ""
    try:
        value = ast.literal_eval(_text(parse_bytes, first))
    except (SyntaxError, ValueError):
        return ""
    return inspect.cleandoc(value) if isinstance(value, str) else ""


def index_source(path: Path, source: bytes, *, tree, parse_bytes: bytes, offsets,
                 encoding: str | None = None) -> dict:
    """Extract Python callables from an already parsed Tree-sitter syntax tree."""
    if len(source) > 4_000_000:
        raise ValueError("Python source exceeds the 4 MB per-file limit")

    def raw(offset: int) -> int:
        return offsets.raw(offset) if offsets is not None else offset

    if encoding is None:
        encoding = python_source_encoding(source)

    functions = []
    unhandled = []
    unhandled_count = 0
    promised_count = 0

    def emit(node, owners: tuple[str, ...], *, start: int | None = None) -> str | None:
        nonlocal promised_count, unhandled_count
        promised_count += 1
        is_lambda = node.type == "lambda"
        name_node = node.child_by_field_name("name") if not is_lambda else None
        body = node.child_by_field_name("body")
        if body is None or body.start_byte == body.end_byte or (not is_lambda and name_node is None):
            unhandled_count += 1
            if len(unhandled) < 50:
                unhandled.append({"syntax_kind": node.type,
                                  "byte_range": {"start": raw(node.start_byte),
                                                 "end": raw(node.end_byte)}})
            return None
        begin = raw(node.start_byte if start is None else start)
        end = raw(node.end_byte)
        kind = "lambda" if is_lambda else "function"
        name = (f"<lambda@{begin}>" if is_lambda else
                unicodedata.normalize("NFKC", _text(parse_bytes, name_node)))
        qualified = ".".join((*owners, name))
        colon = next((child for child in node.children if child.type == ":"), None)
        if not is_lambda and colon is None:
            unhandled_count += 1
            if len(unhandled) < 50:
                unhandled.append({"syntax_kind": node.type,
                                  "byte_range": {"start": begin, "end": end}})
            return None
        signature = ("lambda" if is_lambda else
                     source[raw(node.start_byte):raw(colon.end_byte)].decode(encoding))
        functions.append({
            "name": name, "qualified_name": qualified,
            "line": node.start_point.row + 1,
            "column": utf8_display_column(parse_bytes, node.start_byte),
            "end_line": node.end_point.row + (node.end_point.column != 0),
            "signature": signature,
            "docs": "" if is_lambda else _docs(body, parse_bytes),
            "lexical_call_candidates": _calls(node, parse_bytes),
            **declaration(source, kind, qualified, begin, end),
        })
        return name

    pending = [(tree, ())]
    while pending:
        node, owners = pending.pop()
        if node.type == "decorated_definition":
            definition = next((child for child in node.named_children
                               if child.type == "function_definition"), None)
            name = emit(definition, owners, start=node.start_byte) if definition else None
            for child in reversed(node.named_children):
                child_owners = (*owners, name) if child == definition and name else owners
                pending.append((child, child_owners))
            continue
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                owners = (*owners, unicodedata.normalize("NFKC", _text(parse_bytes, name_node)))
        elif node.type == "function_definition":
            if node.parent.type != "decorated_definition":
                name = emit(node, owners)
                if name is not None:
                    owners = (*owners, name)
        elif node.type == "lambda" and node.is_named:
            name = emit(node, owners)
            if name is not None:
                owners = (*owners, name)
        pending.extend((child, owners) for child in reversed(node.named_children))
    assign_named_ids(functions)
    coverage = finalize_coverage(functions, promised_count, unhandled_count, 0)
    return {"path": str(path), "function_count": len(functions),
            "parse_error_count": unhandled_count, "unhandled_declarations": unhandled,
            "adapter_coverage": coverage,
            "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
