"""Review adapter assumptions in local upstream Tree-sitter node-types files.

Print exact pinned download URLs with --sources, then pass LANGUAGE=PATH pairs.
Use --require-all to require every parser variant, including TypeScript and TSX.
The original two positional Python/Rust file arguments remain supported.
This maintainer tool never downloads files or changes installed dependencies.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
# Distribution versions come only from pyproject.toml. These upstream repository
# paths were checked at the pinned release tags; review them when packaging moves.
SOURCES = {
    **{language: (f"tree-sitter-{language}", "src/node-types.json")
       for language in ("python", "rust", "javascript", "java", "go", "c-sharp", "c", "cpp")},
    "typescript": ("tree-sitter-typescript", "typescript/src/node-types.json"),
    "tsx": ("tree-sitter-typescript", "tsx/src/node-types.json"),
    "markdown": ("tree-sitter-markdown", "tree-sitter-markdown/src/node-types.json"),
}

# Field presence and requiredness used by adapters. Empty maps check a named node
# exists when the adapter walks its unnamed fields/children. These are selected
# assumptions, not a complete grammar snapshot or a classifier coverage proof.
_JS = {
    "function_declaration": {"body": True, "name": True, "parameters": True},
    "generator_function_declaration": {"body": True, "name": True, "parameters": True},
    "function_expression": {"body": True, "name": False, "parameters": True},
    "generator_function": {"body": True, "name": False, "parameters": True},
    "arrow_function": {"body": True, "parameter": False, "parameters": False},
    "method_definition": {"body": True, "name": True, "parameters": True},
    "class_declaration": {"body": True, "name": True},
    "class": {"body": True, "name": False},
    "variable_declarator": {"name": True, "value": False},
    "pair": {"key": True, "value": True},
    "assignment_expression": {"left": True, "right": True},
    "member_expression": {"object": True, "property": True},
    "call_expression": {"function": True},
    "new_expression": {"constructor": True},
    "import_statement": {"source": True},
    "export_statement": {"source": False},
}
_TS = {
    **_JS,
    "import_statement": {"source": False},
    "function_signature": {"name": True, "parameters": True},
    "method_signature": {"name": True, "parameters": True},
    "abstract_method_signature": {"name": True, "parameters": True},
    "call_signature": {"parameters": True},
    "construct_signature": {"parameters": True},
    "abstract_class_declaration": {"name": True},
    "public_field_definition": {"name": True, "value": False},
    "internal_module": {"body": False, "name": True},
    "module": {"body": False, "name": True},
}
_C = {
    "function_definition": {"body": True, "declarator": True},
    "function_declarator": {"declarator": True, "parameters": True},
    "pointer_declarator": {"declarator": True},
    "parenthesized_declarator": {},
    "attributed_declarator": {},
    "parameter_declaration": {"declarator": False, "type": True},
    "call_expression": {"function": True},
}
EXPECTED = {
    "markdown": {
        "section": {}, "atx_heading": {"heading_content": False},
        "setext_heading": {"heading_content": True},
        "list_item": {}, "task_list_marker_checked": {},
        "task_list_marker_unchecked": {},
        "minus_metadata": {}, "plus_metadata": {},
    },
    "python": {
        "function_definition": {"body": True, "name": True, "parameters": True},
        "lambda": {"body": True, "parameters": False},
        "decorated_definition": {"definition": True},
        "class_definition": {"body": True, "name": True},
        "call": {"function": True},
    },
    "rust": {
        "function_item": {"body": True, "name": True, "parameters": True},
        "closure_expression": {"body": True, "parameters": True},
        "function_signature_item": {"name": True, "parameters": True},
        "mod_item": {"body": False, "name": True},
        "trait_item": {"body": True, "name": True},
        "impl_item": {"body": False},
        "foreign_mod_item": {"body": False},
        "call_expression": {"function": True},
        "field_expression": {"field": True},
    },
    "javascript": {**_JS, "field_definition": {"property": True, "value": False}},
    "typescript": _TS,
    "tsx": _TS,
    "java": {
        "method_declaration": {"body": False, "name": True, "parameters": True},
        "constructor_declaration": {"body": True, "name": True, "parameters": True},
        "compact_constructor_declaration": {"body": True, "name": True},
        "lambda_expression": {"body": True, "parameters": True},
        "class_declaration": {"name": True},
        "interface_declaration": {"name": True},
        "record_declaration": {"name": True},
        "enum_declaration": {"name": True},
        "annotation_type_declaration": {"name": True},
        "enum_constant": {"body": False, "name": True},
        "object_creation_expression": {"type": True},
        "annotation_type_element_declaration": {"name": True},
        "formal_parameter": {"name": True, "type": True},
        "spread_parameter": {},
        "method_invocation": {"name": True},
    },
    "go": {
        "function_declaration": {"body": False, "name": True, "parameters": True},
        "method_declaration": {"body": False, "name": True, "parameters": True, "receiver": True},
        "func_literal": {"body": True, "parameters": True},
        "method_elem": {"name": True, "parameters": True},
        "type_spec": {"name": True, "type": True},
        "parameter_declaration": {"type": True},
        "call_expression": {"function": True},
    },
    "c-sharp": {
        "method_declaration": {"body": False, "name": True, "parameters": True},
        "constructor_declaration": {"body": False, "name": True, "parameters": True},
        "destructor_declaration": {"body": False, "name": True, "parameters": True},
        "operator_declaration": {"body": False, "operator": True, "parameters": True},
        "conversion_operator_declaration": {"body": False, "type": True, "parameters": True},
        "local_function_statement": {"body": False, "name": True, "parameters": True},
        "lambda_expression": {"body": True, "parameters": True},
        "anonymous_method_expression": {"parameters": False},
        "accessor_declaration": {"body": False, "name": True},
        "namespace_declaration": {"name": True},
        "file_scoped_namespace_declaration": {"name": True},
        "class_declaration": {"name": True},
        "struct_declaration": {"name": True},
        "interface_declaration": {"name": True},
        "record_declaration": {"name": True},
        "property_declaration": {"name": True, "value": False},
        "indexer_declaration": {"parameters": True, "value": False},
        "event_declaration": {"name": True},
        "parameter": {"name": True, "type": False},
        "parameter_list": {"type": False},
        "invocation_expression": {"function": True},
        "type_parameter_list": {},
        "explicit_interface_specifier": {},
    },
    "c": _C,
    "cpp": {
        **_C,
        "function_definition": {"body": False, "declarator": True, "type": False},
        "lambda_expression": {"body": True, "declarator": False},
        "operator_cast": {"declarator": True, "type": True},
        "qualified_identifier": {"name": True, "scope": False},
        "template_function": {"arguments": True, "name": True},
        "abstract_function_declarator": {"parameters": True},
        "reference_declarator": {},
        "namespace_definition": {"name": False},
        "class_specifier": {"name": False},
        "struct_specifier": {"name": False},
        "union_specifier": {"name": False},
        "optional_parameter_declaration": {"declarator": False, "default_value": True},
        "variadic_parameter_declaration": {"declarator": True},
    },
}


def source_urls(project: Path = ROOT / "pyproject.toml") -> dict[str, str]:
    with project.open("rb") as handle:
        dependencies = tomllib.load(handle)["project"]["dependencies"]
    pins = {}
    for dependency in dependencies:
        match = re.fullmatch(r"([a-z0-9-]+)==([a-zA-Z0-9.+-]+)", dependency)
        if match:
            pins[match[1]] = match[2]
    urls = {}
    for language, (distribution, relative) in SOURCES.items():
        if distribution not in pins:
            raise ValueError(f"{distribution} needs an exact pin in {project}")
        owner = "tree-sitter-grammars" if language == "markdown" else "tree-sitter"
        urls[language] = (f"https://raw.githubusercontent.com/{owner}/{distribution}/"
                          f"v{pins[distribution]}/{relative}")
    return urls


def check(language: str, nodes: object) -> list[str]:
    if not isinstance(nodes, list) or any(not isinstance(node, dict) for node in nodes):
        return [f"{language}: expected a node-types JSON array of objects"]
    indexed = {node.get("type"): node for node in nodes
               if node.get("named") is True and isinstance(node.get("type"), str)}
    errors = []
    for kind, required_fields in EXPECTED[language].items():
        node = indexed.get(kind)
        if node is None:
            errors.append(f"{language}: missing named node {kind}")
            continue
        fields = node.get("fields", {})
        if not isinstance(fields, dict):
            errors.append(f"{language}: {kind} fields must be an object")
            continue
        for field, required in required_fields.items():
            actual = fields.get(field)
            if not isinstance(actual, dict):
                errors.append(f"{language}: {kind} missing field {field}")
            elif actual.get("required") is not required:
                errors.append(f"{language}: {kind}.{field} requiredness changed")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", metavar="LANGUAGE=PATH")
    parser.add_argument("--sources", action="store_true", help="print current pinned upstream URLs")
    parser.add_argument("--require-all", action="store_true", help="reject missing parser variants")
    args = parser.parse_args(argv)
    if args.sources:
        if args.inputs or args.require_all:
            parser.error("--sources cannot be combined with files or --require-all")
        for language, url in source_urls().items():
            print(f"{language}={url}")
        return 0
    if len(args.inputs) == 2 and all("=" not in value for value in args.inputs):
        paths = dict(zip(("python", "rust"), map(Path, args.inputs)))
    else:
        paths = {}
        for value in args.inputs:
            language, separator, filename = value.partition("=")
            if not separator or language not in EXPECTED or not filename:
                parser.error(f"expected LANGUAGE=PATH; languages: {', '.join(EXPECTED)}")
            if language in paths:
                parser.error(f"duplicate language: {language}")
            paths[language] = Path(filename)
    if not paths:
        parser.error("supply local node-types files or use --sources")
    if args.require_all and (missing := EXPECTED.keys() - paths.keys()):
        parser.error(f"missing parser variants: {', '.join(sorted(missing))}")
    errors = []
    for language, path in paths.items():
        try:
            nodes = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            errors.append(f"{language}: cannot read {path}: {error}")
        else:
            errors.extend(check(language, nodes))
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"Checked node/field assumptions: {', '.join(paths)}")
    print("Review field types, new syntax, and adapter fixtures separately; this is not a coverage proof.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
