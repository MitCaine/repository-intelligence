"""Pinned Go source-level functions, methods, literals and interface signatures."""

from __future__ import annotations

from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage
from .source import utf8_display_column


CALLABLES = {"function_declaration", "method_declaration", "func_literal"}


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _receiver(node, source: bytes) -> str | None:
    receiver = node.child_by_field_name("receiver")
    if receiver is None:
        return None
    parameter = next((child for child in receiver.named_children
                      if child.type == "parameter_declaration"), None)
    type_node = parameter.child_by_field_name("type") if parameter is not None else None
    return _text(source, type_node) if type_node is not None else _text(source, receiver)


def _calls(body, source: bytes) -> list[str]:
    calls = set()
    pending = [body]
    while pending:
        node = pending.pop()
        if node.type == "call_expression":
            target = node.child_by_field_name("function")
            if target is not None:
                calls.add(_text(source, target))
        pending.extend(node.named_children)
    return sorted(calls)


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Account for every grammar-recognized Go body-bearing callable."""
    if len(source) > 4_000_000:
        raise ValueError("Go source exceeds the 4 MB per-file limit")
    source.decode("utf-8")
    functions = []
    bodyless = []
    unhandled = []
    promised = 0
    unhandled_count = 0
    package = None
    pending = [(tree, ())]
    while pending:
        node, owners = pending.pop()
        if node.type == "package_clause":
            name = next(iter(node.named_children), None)
            package = _text(source, name) if name is not None else None
        elif node.type == "type_spec":
            name = node.child_by_field_name("name")
            type_node = node.child_by_field_name("type")
            if name is not None and type_node is not None and type_node.type == "interface_type":
                owners = (*owners, _text(source, name))
        if node.type == "method_elem":
            bodyless.append({"syntax_kind": node.type,
                             "owner": ".".join(owners) or None,
                             "byte_range": {"start": node.start_byte, "end": node.end_byte}})
        elif node.type in CALLABLES:
            body = node.child_by_field_name("body")
            name_node = node.child_by_field_name("name")
            anonymous = node.type == "func_literal"
            external = (node.type == "function_declaration" and body is None
                        and name_node is not None and not node.has_error)
            if external:
                bodyless.append({"syntax_kind": node.type,
                                 "owner": ".".join(owners) or None,
                                 "byte_range": {"start": node.start_byte,
                                                "end": node.end_byte}})
            else:
                promised += 1
            if external:
                pass
            elif body is None or body.start_byte == body.end_byte or (not anonymous and name_node is None):
                unhandled_count += 1
                if len(unhandled) < 50:
                    unhandled.append({"syntax_kind": node.type,
                                      "byte_range": {"start": node.start_byte,
                                                     "end": node.end_byte}})
            else:
                name = (_text(source, name_node) if name_node is not None
                        else f"<literal@{node.start_byte}>")
                receiver = _receiver(node, source) if node.type == "method_declaration" else None
                parts = ([package] if package else []) + list(owners)
                if receiver is not None:
                    parts.append(receiver)
                qualified = ".".join((*parts, name))
                kind = ("closure" if anonymous else "method" if receiver is not None
                        else "function")
                functions.append({
                    "name": name, "qualified_name": qualified,
                    "receiver": receiver, "anonymous": anonymous,
                    "line": node.start_point.row + 1,
                    "column": utf8_display_column(source, node.start_byte, cr_is_newline=False),
                    "end_line": node.end_point.row + (node.end_point.column != 0),
                    "signature": source[node.start_byte:body.start_byte].decode("utf-8"),
                    "docs": "", "lexical_call_candidates": _calls(body, source),
                    "syntax_kind": node.type,
                    **declaration(source, kind, qualified, node.start_byte, node.end_byte),
                })
                owners = (*owners, name)
        pending.extend((child, owners) for child in reversed(node.named_children))
    assign_named_ids(functions)
    coverage = finalize_coverage(functions, promised, unhandled_count, len(bodyless))
    return {"path": str(path), "function_count": len(functions),
            "parse_error_count": unhandled_count, "unhandled_declarations": unhandled,
            "bodyless_declarations": bodyless, "adapter_coverage": coverage,
            "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
