"""Pinned C# source-level callable navigation, including executable accessors."""

from __future__ import annotations

from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage, syntax_token_key
from .source import utf8_display_column


CALLABLES = {"method_declaration", "constructor_declaration", "destructor_declaration",
             "operator_declaration", "conversion_operator_declaration",
             "local_function_statement", "lambda_expression",
             "anonymous_method_expression", "accessor_declaration"}
OWNERS = {"namespace_declaration", "file_scoped_namespace_declaration",
          "class_declaration", "struct_declaration", "interface_declaration",
          "record_declaration"}


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _body(node):
    body = node.child_by_field_name("body")
    if body is None and node.type == "anonymous_method_expression":
        body = next((child for child in node.named_children if child.type == "block"), None)
    if body is None and node.type in {"property_declaration", "indexer_declaration"}:
        value = node.child_by_field_name("value")
        body = value if value is not None and value.type == "arrow_expression_clause" else None
    return body


def _owner(node, source: bytes) -> str | None:
    if node.type in OWNERS:
        name = node.child_by_field_name("name")
        return _text(source, name) if name is not None else None
    if node.type in {"property_declaration", "event_declaration"}:
        name = node.child_by_field_name("name")
        return _text(source, name) if name is not None else None
    if node.type == "indexer_declaration":
        parameters = node.child_by_field_name("parameters")
        types = ",".join(_text(source, parameter.child_by_field_name("type"))
                         if parameter.child_by_field_name("type") is not None
                         else _text(source, parameter)
                         for parameter in parameters.named_children) if parameters else ""
        return f"this[{types}]"
    return None


def _parameter_identity(parameter, source: bytes) -> str:
    name = parameter.child_by_field_name("name")
    default = parameter.child_by_field_name("default_value")
    return syntax_token_key(parameter, source,
                            omit=tuple(node for node in (name, default) if node is not None))


def _calls(body, source: bytes) -> list[str]:
    calls = set()
    pending = [body]
    while pending:
        node = pending.pop()
        if node.type == "invocation_expression":
            target = node.child_by_field_name("function")
            if target is not None:
                calls.add(_text(source, target))
        pending.extend(node.named_children)
    return sorted(calls)


def _name_kind(node, source: bytes) -> tuple[str, str, bool]:
    kind = node.type
    name_node = node.child_by_field_name("name")
    if kind in {"lambda_expression", "anonymous_method_expression"}:
        return f"<anonymous@{node.start_byte}>", "lambda", True
    if kind == "accessor_declaration":
        return (_text(source, name_node) if name_node is not None else "<accessor>"), "accessor", False
    if kind in {"property_declaration", "indexer_declaration"}:
        return "get", "getter", False
    if kind == "operator_declaration":
        symbol = node.child_by_field_name("operator")
        return f"operator {_text(source, symbol) if symbol is not None else '?'}", "operator", False
    if kind == "conversion_operator_declaration":
        target = node.child_by_field_name("type")
        label = next((child.type for child in node.children
                      if child.type in {"explicit", "implicit"}), None)
        if label is None:
            raise ValueError("Conversion operator has no explicit/implicit keyword")
        return f"{label} operator {_text(source, target) if target is not None else '?'}", "conversion", False
    name = _text(source, name_node) if name_node is not None else "<unnamed>"
    if kind == "constructor_declaration":
        prefix = source[node.start_byte:name_node.start_byte] if name_node is not None else b""
        return name, "static_constructor" if b"static" in prefix.split() else "constructor", False
    if kind == "destructor_declaration":
        return f"~{name}", "destructor", False
    return name, "local_function" if kind == "local_function_statement" else "method", False


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Map contracted executable C# syntax once and expose bodyless members."""
    if len(source) > 4_000_000:
        raise ValueError("C# source exceeds the 4 MB per-file limit")
    source.decode("utf-8")
    functions = []
    bodyless = []
    unhandled = []
    promised = 0
    unhandled_count = 0
    pending = [(tree, (), ())]
    file_namespace = next((node for node in tree.named_children
                           if node.type == "file_scoped_namespace_declaration"), None)
    file_namespace_name = (_owner(file_namespace, source)
                           if file_namespace is not None else None)
    while pending:
        node, owners, owner_identities = pending.pop()
        if node.parent == tree and node is not file_namespace and file_namespace_name is not None:
            owners = (file_namespace_name,)
        owner = _owner(node, source)
        if owner is not None:
            owners = (*owners, owner)
        value = node.child_by_field_name("value")
        is_expression_property = (node.type in {"property_declaration", "indexer_declaration"}
                                  and value is not None and value.type == "arrow_expression_clause")
        if node.type in CALLABLES or is_expression_property:
            body = _body(node)
            if body is None and node.type in {"method_declaration", "accessor_declaration"}:
                bodyless.append({"syntax_kind": node.type,
                                 "owner": ".".join(owners) or None,
                                 "byte_range": {"start": node.start_byte, "end": node.end_byte}})
            else:
                promised += 1
                name_node = node.child_by_field_name("name")
                requires_name = node.type in {"method_declaration", "constructor_declaration",
                                              "destructor_declaration", "local_function_statement"}
                if body is None or body.start_byte == body.end_byte or (requires_name and name_node is None):
                    unhandled_count += 1
                    if len(unhandled) < 50:
                        unhandled.append({"syntax_kind": node.type,
                                          "byte_range": {"start": node.start_byte,
                                                         "end": node.end_byte}})
                else:
                    name, kind, anonymous = _name_kind(node, source)
                    qualified = ".".join((*owners, name))
                    parameters = node.child_by_field_name("parameters")
                    identity_signature = None
                    if parameters is not None and not anonymous:
                        identity_signature = ",".join(_parameter_identity(parameter, source)
                                                      for parameter in parameters.named_children)
                        type_parameters = next((child for child in node.named_children
                                                if child.type == "type_parameter_list"), None)
                        if type_parameters is not None:
                            identity_signature = (f"arity={len(type_parameters.named_children)}|"
                                                  + identity_signature)
                    own_signature = identity_signature
                    if owner_identities:
                        identity_signature = "/".join(owner_identities) + ":" + (own_signature or "")
                    functions.append({
                        "name": name, "qualified_name": qualified,
                        "line": node.start_point.row + 1,
                        "column": utf8_display_column(source, node.start_byte),
                        "end_line": node.end_point.row + (node.end_point.column != 0),
                        "signature": source[node.start_byte:body.start_byte].decode("utf-8"),
                        "docs": "", "lexical_call_candidates": _calls(body, source),
                        "syntax_kind": node.type, "anonymous": anonymous,
                        "identity_signature": identity_signature,
                        **declaration(source, kind, qualified, node.start_byte, node.end_byte),
                    })
                    if node.type in {"method_declaration", "constructor_declaration",
                                     "local_function_statement"}:
                        owners = (*owners, name)
                        owner_identities = (*owner_identities,
                                            f"{name}({own_signature or ''})")
        pending.extend((child, owners, owner_identities)
                       for child in reversed(node.named_children))
    assign_named_ids(functions)
    coverage = finalize_coverage(functions, promised, unhandled_count, len(bodyless))
    return {"path": str(path), "function_count": len(functions),
            "parse_error_count": unhandled_count, "unhandled_declarations": unhandled,
            "bodyless_declarations": bodyless, "adapter_coverage": coverage,
            "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
