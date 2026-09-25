"""Review declaration-node fields in downloaded pinned grammar node-types.json files.

Usage: python scripts/check_grammar_nodes.py PYTHON_NODE_TYPES RUST_NODE_TYPES
This is a maintainer upgrade check, not a runtime dependency or registry.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


# Field names and requiredness used by the current adapters, from the pinned
# tree-sitter-python 0.25.0 and tree-sitter-rust 0.24.2 generated node types.
EXPECTED = {
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
        "trait_item": {"body": True, "name": True},
        "foreign_mod_item": {"body": False},
        "call_expression": {"function": True},
    },
}


def check(language: str, nodes: list[dict]) -> list[str]:
    indexed = {node["type"]: node for node in nodes if node.get("named")}
    errors = []
    for kind, required_fields in EXPECTED[language].items():
        node = indexed.get(kind)
        if node is None:
            errors.append(f"{language}: missing named node {kind}")
            continue
        fields = node.get("fields", {})
        for field, required in required_fields.items():
            actual = fields.get(field)
            if actual is None:
                errors.append(f"{language}: {kind} missing field {field}")
            elif actual.get("required") is not required:
                errors.append(f"{language}: {kind}.{field} requiredness changed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("python_node_types", type=Path)
    parser.add_argument("rust_node_types", type=Path)
    args = parser.parse_args()
    errors = []
    for language, path in (("python", args.python_node_types),
                           ("rust", args.rust_node_types)):
        errors.extend(check(language, json.loads(path.read_text(encoding="utf-8"))))
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Pinned declaration nodes and fields match the adapter assumptions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
