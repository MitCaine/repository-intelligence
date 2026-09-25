"""Source-bound JavaScript, JSX, TypeScript and TSX callable navigation."""

from __future__ import annotations

from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage, nearby_comment
from .source import utf8_display_column


CALLABLES = {"function_declaration", "generator_function_declaration",
             "function_expression", "generator_function", "arrow_function",
             "method_definition"}
BODYLESS = {"function_signature", "method_signature", "abstract_method_signature",
            "call_signature", "construct_signature"}


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _name_from_assignment(node, source: bytes) -> str | None:
    parent = node.parent
    if parent is None or parent.type not in {"variable_declarator", "pair", "public_field_definition",
                                            "assignment_expression"}:
        return None
    field = "right" if parent.type == "assignment_expression" else "value"
    if parent.child_by_field_name(field) != node:
        return None
    target = (parent.child_by_field_name("name") or parent.child_by_field_name("key")
              or parent.child_by_field_name("left"))
    return _text(source, target) if target is not None else None


def _export_kind(node, source: bytes) -> str | None:
    ancestor = node.parent
    while ancestor is not None and ancestor.type != "program":
        if ancestor.type in CALLABLES | {"class_body", "class_declaration", "class",
                                           "abstract_class_declaration", "call_expression",
                                           "new_expression", "arguments", "object", "pair",
                                           "array", "member_expression", "subscript_expression"}:
            return None  # This callable is contained in, rather than directly bound by, the export.
        if ancestor.type == "assignment_expression":
            target = ancestor.child_by_field_name("left")
            if target is not None and _is_commonjs_target(target, source):
                return "commonjs"
        if ancestor.type == "export_statement":
            return "default" if any(child.type == "default" for child in ancestor.children) else "named"
        ancestor = ancestor.parent
    return None


def _is_commonjs_target(target, source: bytes) -> bool:
    parts = []
    current = target
    while current.type == "member_expression":
        member = current.child_by_field_name("property")
        if member is None:
            return False
        parts.append(_text(source, member))
        current = current.child_by_field_name("object")
        if current is None:
            return False
    if current.type != "identifier":
        return False
    parts.append(_text(source, current))
    parts.reverse()
    return parts[:2] == ["module", "exports"] or (len(parts) > 1 and parts[0] == "exports")


def _calls(node, source: bytes) -> list[str]:
    calls = set()
    pending = [node]
    while pending:
        current = pending.pop()
        if current.type in {"call_expression", "new_expression"}:
            target = current.child_by_field_name("function") or current.child_by_field_name("constructor")
            if target is not None:
                calls.add(_text(source, target))
        pending.extend(current.named_children)
    return sorted(calls)


def _module_bindings(tree, source: bytes) -> dict:
    imports = []
    exports = []
    pending = [tree]
    while pending:
        node = pending.pop()
        if node.type == "import_statement":
            target = node.child_by_field_name("source")
            imports.append({"source": _text(source, target) if target is not None else None,
                            "byte_range": {"start": node.start_byte, "end": node.end_byte}})
        elif node.type == "export_statement":
            target = node.child_by_field_name("source")
            owner = []
            ancestor = node.parent
            while ancestor is not None:
                if ancestor.type in {"internal_module", "module"}:
                    name = ancestor.child_by_field_name("name")
                    if name is not None:
                        owner.append(_text(source, name))
                ancestor = ancestor.parent
            exports.append({"kind": "default" if any(child.type == "default" for child in node.children)
                            else "named",
                            "source": _text(source, target) if target is not None else None,
                            "owner": ".".join(reversed(owner)) or None,
                            "byte_range": {"start": node.start_byte, "end": node.end_byte}})
        elif node.type == "expression_statement":
            assignment = next((child for child in node.named_children
                               if child.type == "assignment_expression"), None)
            target = assignment.child_by_field_name("left") if assignment is not None else None
            if target is not None and _is_commonjs_target(target, source):
                exports.append({"kind": "commonjs",
                                "source": None, "owner": None,
                                "byte_range": {"start": node.start_byte, "end": node.end_byte}})
        pending.extend(reversed(node.named_children))
    imports.sort(key=lambda entry: entry["byte_range"]["start"])
    exports.sort(key=lambda entry: entry["byte_range"]["start"])
    return {"imports": imports, "exports": exports,
            "meaning": "syntactic module bindings only; not resolved imports or exports"}


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Map every recognized body-bearing callable or disclose unhandled syntax."""
    if len(source) > 4_000_000:
        raise ValueError("JavaScript/TypeScript source exceeds the 4 MB per-file limit")
    source.decode("utf-8")  # Do not claim exact text navigation for invalid UTF-8.
    functions = []
    unhandled = []
    bodyless = []
    promised_count = 0
    unhandled_count = 0
    pending = [(tree, ())]
    while pending:
        node, owners = pending.pop()
        if node.type in {"class_declaration", "class", "abstract_class_declaration",
                         "interface_declaration", "internal_module", "module"}:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                owners = (*owners, _text(source, name_node))
        elif node.type in {"variable_declarator", "pair", "public_field_definition"}:
            value = node.child_by_field_name("value")
            if value is not None and value.type not in CALLABLES:
                name_node = node.child_by_field_name("name") or node.child_by_field_name("key")
                if name_node is not None:
                    owners = (*owners, _text(source, name_node))
        if node.type in BODYLESS:
            bodyless.append({"syntax_kind": node.type,
                             "byte_range": {"start": node.start_byte, "end": node.end_byte}})
        elif node.type in CALLABLES:
            promised_count += 1
            body = node.child_by_field_name("body")
            name_node = node.child_by_field_name("name")
            if body is None or body.start_byte == body.end_byte:
                unhandled_count += 1
                if len(unhandled) < 50:
                    unhandled.append({"syntax_kind": node.type,
                                      "byte_range": {"start": node.start_byte,
                                                     "end": node.end_byte}})
            else:
                inferred = _name_from_assignment(node, source)
                export_kind = _export_kind(node, source)
                anonymous = name_node is None and inferred is None
                name = (_text(source, name_node) if name_node is not None else inferred
                        or f"<{'default' if export_kind == 'default' else 'anonymous'}@{node.start_byte}>")
                aliases = [inferred] if inferred is not None and inferred != name else []
                qualified = ".".join((*owners, name))
                method_tokens = tuple(child.type for child in node.children
                                      if name_node is not None and child.end_byte <= name_node.start_byte)
                kind = ("arrow" if node.type == "arrow_function" else
                        "constructor" if node.type == "method_definition" and name == "constructor"
                        and node.parent is not None and node.parent.type == "class_body"
                        and "static" not in method_tokens else
                        "getter" if "get" in method_tokens else
                        "setter" if "set" in method_tokens else
                        "method" if node.type == "method_definition" else "function")
                functions.append({
                    "name": name, "qualified_name": qualified,
                    "binding_aliases": aliases,
                    "line": node.start_point.row + 1,
                    "column": utf8_display_column(source, node.start_byte),
                    "end_line": node.end_point.row + (node.end_point.column != 0),
                    "signature": source[node.start_byte:body.start_byte].decode("utf-8"),
                    "docs": nearby_comment(node, source), "lexical_call_candidates": _calls(node, source),
                    "syntax_kind": node.type, "export_kind": export_kind,
                    "anonymous": anonymous,
                    **declaration(source, kind, qualified, node.start_byte, node.end_byte),
                })
                if node.type in CALLABLES:
                    owners = (*owners, name)
        pending.extend((child, owners) for child in reversed(node.named_children))
    assign_named_ids(functions)
    coverage = finalize_coverage(functions, promised_count, unhandled_count, len(bodyless))
    return {"path": str(path), "function_count": len(functions),
            "parse_error_count": unhandled_count, "unhandled_declarations": unhandled,
            "bodyless_declarations": bodyless, "adapter_coverage": coverage,
            "functions": functions, "module_bindings": _module_bindings(tree, source),
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
