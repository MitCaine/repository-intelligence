"""Pinned Java source-level callable navigation; no semantic resolution."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage
from .source import utf8_display_column


CALLABLES = {"method_declaration", "constructor_declaration",
             "compact_constructor_declaration", "lambda_expression"}
OWNERS = {"class_declaration", "interface_declaration", "record_declaration",
          "enum_declaration", "annotation_type_declaration"}


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _calls(body, source: bytes) -> list[str]:
    calls = set()
    pending = [body]
    while pending:
        node = pending.pop()
        if node.type == "method_invocation":
            name = node.child_by_field_name("name")
            if name is not None:
                calls.add(_text(source, name))
        elif node.type == "object_creation_expression":
            target = node.child_by_field_name("type")
            if target is not None:
                calls.add(_text(source, target))
        pending.extend(node.named_children)
    return sorted(calls)


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Account for grammar-recognized executable Java callables exactly once."""
    if len(source) > 4_000_000:
        raise ValueError("Java source exceeds the 4 MB per-file limit")
    source.decode("utf-8")
    functions = []
    unhandled = []
    bodyless = []
    promised = 0
    unhandled_count = 0
    pending = [(tree, ())]
    while pending:
        node, owners = pending.pop()
        if node.type in OWNERS:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                owners = (*owners, _text(source, name_node))
        elif node.type == "enum_constant" and node.child_by_field_name("body") is not None:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                owners = (*owners, _text(source, name_node))
        elif node.type == "object_creation_expression" and any(
                child.type == "class_body" for child in node.named_children):
            owners = (*owners, f"<anonymous-class@{node.start_byte}>")
        if node.type == "annotation_type_element_declaration":
            bodyless.append({"syntax_kind": node.type,
                             "byte_range": {"start": node.start_byte, "end": node.end_byte}})
        elif node.type in CALLABLES:
            body = node.child_by_field_name("body")
            if body is None:
                bodyless.append({"syntax_kind": node.type,
                                 "byte_range": {"start": node.start_byte,
                                                "end": node.end_byte}})
            else:
                promised += 1
                name_node = node.child_by_field_name("name")
                is_lambda = node.type == "lambda_expression"
                if body.start_byte == body.end_byte or (not is_lambda and name_node is None):
                    unhandled_count += 1
                    if len(unhandled) < 50:
                        unhandled.append({"syntax_kind": node.type,
                                          "byte_range": {"start": node.start_byte,
                                                         "end": node.end_byte}})
                else:
                    name = (_text(source, name_node) if name_node is not None
                            else f"<lambda@{node.start_byte}>")
                    parameters = node.child_by_field_name("parameters")
                    identity_signature = None
                    if parameters is not None and not is_lambda:
                        identity_signature = ",".join(
                            _text(source, parameter.child_by_field_name("type"))
                            if parameter.child_by_field_name("type") is not None
                            else _text(source, parameter)
                            for parameter in parameters.named_children)
                    qualified = ".".join((*owners, name))
                    kind = ("lambda" if is_lambda else
                            "constructor" if node.type.endswith("constructor_declaration") else
                            "method")
                    functions.append({
                        "name": name, "qualified_name": qualified,
                        "line": node.start_point.row + 1,
                        "column": utf8_display_column(source, node.start_byte),
                        "end_line": node.end_point.row + (node.end_point.column != 0),
                        "signature": source[node.start_byte:body.start_byte].decode("utf-8"),
                        "docs": "", "lexical_call_candidates": _calls(body, source),
                        "syntax_kind": node.type, "anonymous": is_lambda,
                        "identity_signature": identity_signature,
                        **declaration(source, kind, qualified, node.start_byte, node.end_byte),
                    })
                    owners = (*owners, name)
        pending.extend((child, owners) for child in reversed(node.named_children))
    assign_named_ids(functions)
    coverage = finalize_coverage(functions, promised, unhandled_count, len(bodyless))
    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    return {"path": str(path), "raw_sha256": hashlib.sha256(source).hexdigest(),
            "git_blob_sha1": blob, "function_count": len(functions),
            "parse_error_count": unhandled_count, "unhandled_declarations": unhandled,
            "bodyless_declarations": bodyless, "adapter_coverage": coverage,
            "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
