"""Ordinary Rust navigation from the pinned Tree-sitter grammar."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage
from .source import utf8_display_column
from .structural import rust_attachments


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _owner(node, source: bytes) -> str | None:
    if node.type in {"mod_item", "trait_item"}:
        name = node.child_by_field_name("name")
        return _text(source, name) if name is not None else None
    if node.type == "impl_item":
        body = node.child_by_field_name("body")
        if body is not None:
            return " ".join(source[node.start_byte:body.start_byte]
                            .decode("utf-8", "replace").split())
    return None


def _calls(node, source: bytes) -> list[str]:
    candidates = set()
    pending = [node]
    while pending:
        current = pending.pop()
        if current.type == "call_expression":
            function = current.child_by_field_name("function")
            if function is not None:
                target = (function.child_by_field_name("field")
                          if function.type == "field_expression" else function)
                if target is not None:
                    candidates.add(_text(source, target))
        pending.extend(current.named_children)
    return sorted(candidates)


def _docs(attachments: list, source: bytes) -> str:
    parts = []
    for node in attachments:
        text = _text(source, node)
        if text.startswith("///"):
            parts.append(text[3:].strip())
        elif text.startswith("/**"):
            parts.append(text[3:-2].strip(" *\r\n"))
    return " ".join(parts)


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Extract useful Rust callables from the already parsed syntax tree."""
    if len(source) > 4_000_000:
        raise ValueError("Rust source exceeds the 4 MB per-file limit")
    functions = []
    unhandled = []
    unhandled_count = 0
    promised_count = 0
    bodyless_count = 0
    pending = [(tree, ())]
    while pending:
        node, owners = pending.pop()
        owner = _owner(node, source)
        if owner is not None:
            owners = (*owners, owner)
        if node.type in {"function_item", "closure_expression"}:
            promised_count += 1
            is_function = node.type == "function_item"
            name_node = node.child_by_field_name("name") if is_function else None
            body = node.child_by_field_name("body")
            if body is None or body.start_byte == body.end_byte or (is_function and name_node is None):
                unhandled_count += 1
                if len(unhandled) < 50:
                    unhandled.append({"syntax_kind": node.type,
                                      "byte_range": {"start": node.start_byte,
                                                     "end": node.end_byte}})
            else:
                attachments = rust_attachments(node, source) if is_function else []
                start = attachments[0].start_byte if attachments else node.start_byte
                kind = "function" if is_function else "closure"
                name = (_text(source, name_node) if name_node is not None
                        else f"<closure@{start}>")
                qualified = "::".join((*owners, name))
                position = name_node.start_byte if name_node is not None else node.start_byte
                functions.append({
                    "name": name, "qualified_name": qualified,
                    "line": (name_node or node).start_point.row + 1,
                    "column": utf8_display_column(source, position),
                    "end_line": node.end_point.row + (node.end_point.column != 0),
                    "signature": source[node.start_byte:body.start_byte].decode("utf-8", "replace"),
                    "docs": _docs(attachments, source),
                    "lexical_call_candidates": _calls(body, source),
                    **declaration(source, kind, qualified, start, node.end_byte),
                })
                owners = (*owners, name)
        elif node.type == "function_signature_item":
            container = node.parent.parent if node.parent is not None else None
            if container is not None and container.type in {"trait_item", "foreign_mod_item"}:
                bodyless_count += 1
            else:
                promised_count += 1
                unhandled_count += 1
                if len(unhandled) < 50:
                    unhandled.append({"syntax_kind": node.type,
                                      "byte_range": {"start": node.start_byte,
                                                     "end": node.end_byte}})
        pending.extend((child, owners) for child in reversed(node.named_children))
    assign_named_ids(functions)
    coverage = finalize_coverage(functions, promised_count, unhandled_count,
                                 bodyless_count)
    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    return {"path": str(path), "raw_sha256": hashlib.sha256(source).hexdigest(),
            "git_blob_sha1": blob, "function_count": len(functions),
            "parse_error_count": unhandled_count, "unhandled_declarations": unhandled,
            "adapter_coverage": coverage,
            "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
