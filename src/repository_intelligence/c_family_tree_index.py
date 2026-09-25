"""C/C++ raw-source callable navigation; preprocessing is not expanded."""

from __future__ import annotations

from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage, syntax_token_key
from .source import utf8_display_column


def _text(source: bytes, node) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _name(node, source: bytes) -> str | None:
    if node is None:
        return None
    if node.type == "qualified_identifier":
        scope = node.child_by_field_name("scope")
        terminal = node.child_by_field_name("name")
        if terminal is not None and terminal.type == "operator_cast":
            return ((_text(source, scope).replace("::", ".") + ".") if scope else "") + \
                (_name(terminal, source) or "")
    if node.type == "operator_cast":
        target = node.child_by_field_name("type")
        return "operator " + _text(source, target) if target is not None else None
    next_node = node.child_by_field_name("declarator")
    if next_node is not None:
        return _name(next_node, source)
    if node.type in {"identifier", "field_identifier", "qualified_identifier",
                     "destructor_name", "operator_name", "type_identifier"}:
        return _text(source, node).replace("::", ".")
    return None


def _parameter_identity(parameter, source: bytes) -> str:
    """Keep C/C++ declarator shape but omit the parameter's local name."""
    declarator = parameter.child_by_field_name("declarator")
    leaf = declarator
    while leaf is not None and leaf.child_by_field_name("declarator") is not None:
        leaf = leaf.child_by_field_name("declarator")
    local_name = leaf if leaf is not None and leaf.type in {"identifier", "field_identifier"} else None
    default = parameter.child_by_field_name("default_value")
    return syntax_token_key(parameter, source,
                            omit=tuple(node for node in (local_name, default) if node is not None))


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


def _prototype(node) -> bool:
    parent = node.parent
    while parent is not None:
        if parent.type == "function_definition":
            return False
        if parent.type in {"declaration", "field_declaration"}:
            return True
        if parent.type in {"translation_unit", "declaration_list", "field_declaration_list"}:
            return False
        parent = parent.parent
    return False


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Account for recognized definitions and disclose unexpanded directives."""
    if len(source) > 4_000_000:
        raise ValueError("C/C++ source exceeds the 4 MB per-file limit")
    source.decode("utf-8")
    functions = []
    bodyless = []
    unhandled = []
    promised = 0
    unhandled_count = 0
    preprocess = {"conditional_count": 0, "macro_definition_count": 0,
                  "macro_invocation_count": 0, "include_count": 0,
                  "other_directive_count": 0,
                  "mode": "unexpanded_raw_source", "effective_program_claim": False}
    pending = [(tree, ())]
    while pending:
        node, owners = pending.pop()
        if node.type in {"macro_type_specifier", "preproc_call"}:
            preprocess["macro_invocation_count"] += 1
        elif (node.type == "expression_statement" and node.parent is not None
              and node.parent.type in {"translation_unit", "declaration_list", "preproc_if",
                                       "preproc_ifdef", "preproc_else", "preproc_elif"}
              and any(child.type == "call_expression" for child in node.named_children)):
            preprocess["macro_invocation_count"] += 1
        elif node.type.startswith("preproc_") and node.type not in {"preproc_arg", "preproc_params"}:
            if node.type in {"preproc_if", "preproc_ifdef", "preproc_elif", "preproc_else"}:
                preprocess["conditional_count"] += 1
            elif node.type in {"preproc_def", "preproc_function_def"}:
                preprocess["macro_definition_count"] += 1
            elif node.type == "preproc_include":
                preprocess["include_count"] += 1
            else:
                preprocess["other_directive_count"] += 1
        if node.type in {"namespace_definition", "class_specifier", "struct_specifier",
                         "union_specifier"}:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                owners = (*owners, (node.type, _text(source, name_node)))
        if node.type == "function_declarator" and _prototype(node):
            # A pointer-to-function variable is not a function prototype.
            name_node = node.child_by_field_name("declarator")
            if name_node is not None and name_node.type in {"identifier", "field_identifier",
                                                              "qualified_identifier",
                                                              "operator_name", "destructor_name",
                                                              "type_identifier"}:
                bodyless.append({"syntax_kind": "function_declarator",
                                 "byte_range": {"start": node.start_byte, "end": node.end_byte}})
        elif node.type in {"function_definition", "lambda_expression"}:
            body = node.child_by_field_name("body")
            if node.type == "function_definition" and body is None:
                body = next((child for child in node.named_children
                             if child.type == "try_statement"), None)
                if body is None and any(child.type in {"default_method_clause",
                                                       "delete_method_clause"}
                                        for child in node.named_children):
                    bodyless.append({"syntax_kind": node.type,
                                     "byte_range": {"start": node.start_byte,
                                                    "end": node.end_byte}})
                    continue
            promised += 1
            declarator = node.child_by_field_name("declarator")
            anonymous = node.type == "lambda_expression"
            name = f"<lambda@{node.start_byte}>" if anonymous else _name(declarator, source)
            if body is None or body.start_byte == body.end_byte or name is None:
                unhandled_count += 1
                if len(unhandled) < 50:
                    unhandled.append({"syntax_kind": node.type,
                                      "byte_range": {"start": node.start_byte,
                                                     "end": node.end_byte}})
            else:
                start = node.start_byte
                friend = False
                wrapper = node.parent
                while wrapper is not None and wrapper.type in {
                        "template_declaration", "friend_declaration"}:
                    start = wrapper.start_byte
                    friend |= wrapper.type == "friend_declaration"
                    wrapper = wrapper.parent
                visible_owners = (tuple(part for part in owners
                                        if part[0] == "namespace_definition") if friend else owners)
                qualified = ".".join((*[part[1] for part in visible_owners], name))
                terminal = declarator
                while terminal is not None and terminal.type not in {
                        "qualified_identifier", "operator_name", "operator_cast",
                        "destructor_name", "identifier", "field_identifier"}:
                    terminal = terminal.child_by_field_name("declarator")
                terminal_scope = (terminal.child_by_field_name("scope")
                                  if terminal is not None and terminal.type == "qualified_identifier"
                                  else None)
                if terminal is not None and terminal.type == "qualified_identifier":
                    terminal = terminal.child_by_field_name("name")
                constructor_owner = (_text(source, terminal_scope).split("::")[-1]
                                     if terminal_scope is not None else
                                     next((part[1] for part in reversed(owners)
                                           if part[0] in {"class_specifier", "struct_specifier"}), None))
                kind = ("lambda" if anonymous else
                        "conversion" if terminal is not None and terminal.type == "operator_cast" else
                        "operator" if terminal is not None and terminal.type == "operator_name" else
                        "destructor" if terminal is not None and terminal.type == "destructor_name" else
                        "constructor" if node.child_by_field_name("type") is None
                        and terminal is not None and terminal.type in {"identifier", "field_identifier"}
                        and constructor_owner == _text(source, terminal) else
                        "friend_function" if friend else "function")
                parameter_node = declarator
                while parameter_node is not None and parameter_node.type != "function_declarator":
                    parameter_node = parameter_node.child_by_field_name("declarator")
                parameters = (parameter_node.child_by_field_name("parameters")
                              if parameter_node is not None else None)
                identity_signature = None
                if parameters is not None and not anonymous:
                    identity_signature = ",".join(
                        _parameter_identity(parameter, source)
                        for parameter in parameters.named_children)
                    qualifiers = "".join(_text(source, child) for child in parameter_node.named_children
                                         if child.type in {"type_qualifier", "ref_qualifier"})
                    if qualifiers:
                        identity_signature += "|" + qualifiers
                functions.append({
                    "name": name, "qualified_name": qualified,
                    "line": node.start_point.row + 1,
                    "column": utf8_display_column(source, node.start_byte),
                    "end_line": node.end_point.row + (node.end_point.column != 0),
                    "signature": source[node.start_byte:body.start_byte].decode("utf-8"),
                    "docs": "", "lexical_call_candidates": _calls(body, source),
                    "syntax_kind": node.type, "anonymous": anonymous,
                    "identity_signature": identity_signature,
                    **declaration(source, kind, qualified, start, node.end_byte),
                })
                owners = (*owners, ("callable", name))
        pending.extend((child, owners) for child in reversed(node.named_children))
    assign_named_ids(functions)
    coverage = finalize_coverage(functions, promised, unhandled_count, len(bodyless))
    return {"path": str(path), "function_count": len(functions),
            "parse_error_count": unhandled_count, "unhandled_declarations": unhandled,
            "bodyless_declarations": bodyless, "adapter_coverage": coverage,
            "preprocessing": preprocess, "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}
