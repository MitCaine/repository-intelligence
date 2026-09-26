"""On-demand, source-bound Rust function locator (not a semantic call graph)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from .declarations import assign_named_ids, declaration
from .source import utf8_display_column

from .search import (compact as _compact, display_entry, format_compact,
                     format_tree_compact, query, rank, tokens as _tokens,
                     validate_query)


# The native CLI serializes syntax nodes but omits parser diagnostics.
# ERROR nodes are evidence of some errors, never an exhaustive error count.
_NATIVE_DIAGNOSTICS = {"diagnostic_coverage": "error_nodes_only",
                       "parse_error_count_kind": "error_node_lower_bound"}


def _children(node: dict, kind: str) -> list[dict]:
    return [child for child in node.get("children", []) if child["kind"] == kind]


def _slice(source: bytes, node: dict) -> str:
    return source[node["start"][0] : node["end"][0]].decode("utf-8", "replace")


def _walk(node: dict, source: bytes, owners: tuple[str, ...], output: list[dict]) -> None:
    kind = node["kind"]
    if kind == "MODULE":
        names = _children(node, "NAME")
        if names:
            owners += (_slice(source, names[0]),)
    elif kind == "IMPL":
        items = _children(node, "ASSOC_ITEM_LIST")
        if items:
            header = source[node["start"][0] : items[0]["start"][0]].decode("utf-8", "replace")
            owners += (_compact(header, 100),)
    elif kind in ("TRAIT", "ENUM", "STRUCT"):
        names = _children(node, "NAME")
        if names:
            owners += (_slice(source, names[0]),)
    if kind == "FN":
        names = _children(node, "NAME")
        if names:
            name = _slice(source, names[0])
            body = _children(node, "BLOCK_EXPR")
            signature_end = body[0]["start"][0] if body else node["end"][0]
            fn_kw = _children(node, "FN_KW")
            signature_start = fn_kw[0]["start"][0] if fn_kw else node["start"][0]
            docs = [_slice(source, child).lstrip("/! *") for child in _children(node, "COMMENT")
                    if _slice(source, child).startswith(("///", "/**"))]
            calls: set[str] = set()

            def visit_call(child: dict) -> None:
                if child["kind"] == "METHOD_CALL_EXPR":
                    for reference in _children(child, "NAME_REF"):
                        calls.add(_slice(source, reference))
                elif child["kind"] == "CALL_EXPR":
                    paths = _children(child, "PATH_EXPR")
                    if paths:
                        calls.add(_slice(source, paths[0]))
                for descendant in child.get("children", []):
                    if descendant.get("type") == "Node":
                        visit_call(descendant)

            if body:
                visit_call(body[0])
            output.append({
                "name": name,
                "qualified_name": "::".join((*owners, name)),
                "line": names[0]["start"][1] + 1,
                "column": utf8_display_column(source, names[0]["start"][0],
                                              cr_is_newline=False),
                "end_line": node["end"][1] + (node["end"][2] != 0),
                "signature": source[signature_start:signature_end].decode("utf-8", "replace"),
                "docs": " ".join(docs),
                "lexical_call_candidates": sorted(calls),
                **declaration(source, "function", "::".join((*owners, name)),
                              node["start"][0], node["end"][0]),
            })
    for child in node.get("children", []):
        if child.get("type") == "Node":
            _walk(child, source, owners, output)


def index_file(path: Path, *, analyzer: str = "rust-analyzer") -> dict:
    return index_source(path, path.read_bytes(), analyzer=analyzer)


def index_source(path: Path, source: bytes, *, analyzer: str = "rust-analyzer") -> dict:
    """Parse the same bytes the caller identified; never reopen the file."""
    if len(source) > 4_000_000:
        raise ValueError("Rust source exceeds the 4 MB pilot limit")
    parsed = subprocess.run([analyzer, "parse", "--json"], input=source, capture_output=True,
                            timeout=30, check=True)
    tree = json.loads(parsed.stdout)
    functions: list[dict] = []
    _walk(tree, source, (), functions)
    assign_named_ids(functions)
    def error_count(node: dict) -> int:
        return (node["kind"] == "ERROR") + sum(error_count(child) for child in node.get("children", [])
                                                if child.get("type") == "Node")

    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    return {"path": str(path), "raw_sha256": hashlib.sha256(source).hexdigest(),
            "git_blob_sha1": blob, "function_count": len(functions),
            "parse_error_count": error_count(tree), **_NATIVE_DIAGNOSTICS, "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}


def query_tree(root: Path, terms: str, limit: int = 8, *,
               analyzer: str = "rust-analyzer") -> dict:
    """Legacy Rust-only navigation; not the shared locator's v2 result contract."""
    words = validate_query(terms, limit)
    if not root.is_dir():
        raise ValueError("Rust query root must be an existing directory")
    candidates = []
    failures = []
    scanned = 0
    parse_errors = 0
    for path in sorted(root.rglob("*.rs")):
        if any(part.startswith(".") or part == "target" for part in path.relative_to(root).parts):
            continue
        try:
            index = index_file(path, analyzer=analyzer)
        except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as error:
            failures.append({"path": str(path), "error": type(error).__name__})
            continue
        scanned += 1
        parse_errors += index["parse_error_count"]
        for entry in index["functions"]:
            candidates.append({**entry, "path": str(path), "raw_sha256": index["raw_sha256"],
                               "git_blob_sha1": index["git_blob_sha1"],
                               "parse_error_count": index["parse_error_count"],
                               **_NATIVE_DIAGNOSTICS})
    candidates = rank(candidates, words)
    selected = [display_entry(entry, words) for entry in candidates[:limit]]
    return {"result_kind": "legacy_rust_query", "root": str(root), "query": terms,
            "scanned_files": scanned,
            "parse_error_count": parse_errors, **_NATIVE_DIAGNOSTICS, "failures": failures,
            "total_matches": len(candidates), "matches": selected}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="emit structured JSON instead of compact text")
    args = parser.parse_args()
    if args.source.is_dir():
        result = query_tree(args.source, args.query, args.limit)
        print(json.dumps(result, indent=2) if args.json else format_tree_compact(result))
    else:
        result = query(index_file(args.source), args.query, args.limit)
        print(json.dumps(result, indent=2) if args.json else format_compact(result))


if __name__ == "__main__":
    main()
