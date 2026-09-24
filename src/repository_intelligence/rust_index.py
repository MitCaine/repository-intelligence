"""On-demand, source-bound Rust function locator (not a semantic call graph)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def _children(node: dict, kind: str) -> list[dict]:
    return [child for child in node.get("children", []) if child["kind"] == kind]


def _slice(source: bytes, node: dict) -> str:
    return source[node["start"][0] : node["end"][0]].decode("utf-8", "replace")


def _compact(value: str, limit: int) -> str:
    value = " ".join(value.split())
    return value[: limit - 1] + "…" if len(value) > limit else value


def _tokens(value: str) -> list[str]:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    return re.findall(r"[a-z0-9]+", value.lower())


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
                        calls.add(_compact(_slice(source, paths[0]), 80))
                for descendant in child.get("children", []):
                    if descendant.get("type") == "Node":
                        visit_call(descendant)

            if body:
                visit_call(body[0])
            output.append({
                "name": name,
                "qualified_name": "::".join((*owners, name)),
                "line": names[0]["start"][1] + 1,
                "end_line": node["end"][1] + (node["end"][2] != 0),
                "signature": _compact(source[signature_start:signature_end].decode("utf-8", "replace"), 180),
                "docs": _compact(" ".join(docs), 220),
                "lexical_call_candidates": sorted(calls)[:12],
            })
    for child in node.get("children", []):
        if child.get("type") == "Node":
            _walk(child, source, owners, output)


def index_file(path: Path, *, analyzer: str = "rust-analyzer") -> dict:
    source = path.read_bytes()
    if len(source) > 4_000_000:
        raise ValueError("Rust source exceeds the 4 MB pilot limit")
    parsed = subprocess.run([analyzer, "parse", "--json"], input=source, capture_output=True,
                            timeout=30, check=True)
    tree = json.loads(parsed.stdout)
    functions: list[dict] = []
    _walk(tree, source, (), functions)
    def error_count(node: dict) -> int:
        return (node["kind"] == "ERROR") + sum(error_count(child) for child in node.get("children", [])
                                                if child.get("type") == "Node")

    blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    return {"path": str(path), "raw_sha256": hashlib.sha256(source).hexdigest(),
            "git_blob_sha1": blob, "function_count": len(functions),
            "parse_error_count": error_count(tree), "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}


def query(index: dict, terms: str, limit: int = 8) -> dict:
    words = _tokens(terms)
    if not words or not 1 <= limit <= 20:
        raise ValueError("Provide query terms and a limit from 1 to 20")

    ranked = sorted((entry for entry in index["functions"] if _score(entry, words) > 0),
                    key=lambda entry: ("::tests::" in entry["qualified_name"],
                                       -_score(entry, words), entry["line"]))
    return {key: index[key] for key in ("path", "raw_sha256", "git_blob_sha1", "function_count", "parse_error_count", "relationship_kind")} | {
        "query": terms, "matches": ranked[:limit], "total_matches": len(ranked)}


def _score(entry: dict, words: list[str]) -> int:
    name = set(_tokens(entry["name"]))
    qualified = set(_tokens(entry["qualified_name"]))
    docs = set(_tokens(entry["docs"]))
    calls = set(word for call in entry["lexical_call_candidates"]
                for word in _tokens(call.rsplit("::", 1)[-1]))
    per_word = [8 * (word in name) + 3 * (word in qualified) + (word in docs)
                + (word in calls) for word in words]
    return sum(per_word) + 20 * max(0, sum(value > 0 for value in per_word) - 1)


def query_tree(root: Path, terms: str, limit: int = 8, *, analyzer: str = "rust-analyzer") -> dict:
    """Query current Rust files without a second maintained function map."""
    words = _tokens(terms)
    if not words or not 1 <= limit <= 20:
        raise ValueError("Provide query terms and a limit from 1 to 20")
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
            if _score(entry, words) > 0:
                candidates.append({**entry, "path": str(path), "raw_sha256": index["raw_sha256"],
                                   "git_blob_sha1": index["git_blob_sha1"],
                                   "parse_error_count": index["parse_error_count"]})
    candidates.sort(key=lambda entry: ("::tests::" in entry["qualified_name"],
                                       -_score(entry, words), entry["path"], entry["line"]))
    return {"root": str(root), "query": terms, "scanned_files": scanned,
            "parse_error_count": parse_errors, "failures": failures,
            "total_matches": len(candidates), "matches": candidates[:limit]}


def format_tree_compact(result: dict) -> str:
    lines = [f"{result['root']} scanned={result['scanned_files']} "
             f"parse_errors={result['parse_error_count']} failures={len(result['failures'])}",
             f"query={result['query']!r} matches={result['total_matches']} "
             f"shown={len(result['matches'])}; calls are lexical candidates, not a call graph"]
    for entry in result["matches"]:
        lines.append(f"{entry['path']}:{entry['line']}-{entry['end_line']} "
                     f"{entry['qualified_name']} sha256={entry['raw_sha256']}")
    if result["failures"]:
        lines.append("INCOMPLETE: some files could not be indexed; no absence claim is valid")
    return "\n".join(lines)


def format_compact(result: dict) -> str:
    """Render a bounded navigation packet; JSON remains available for machines."""
    lines = [
        f"{result['path']} sha256={result['raw_sha256']} "
        f"functions={result['function_count']} parse_errors={result['parse_error_count']}",
        f"query={result['query']!r} matches={result['total_matches']} "
        f"shown={len(result['matches'])}; calls are lexical candidates, not a call graph",
    ]
    terms = set(_tokens(result["query"]))
    for entry in result["matches"]:
        line = f"L{entry['line']}-{entry['end_line']} {entry['qualified_name']}"
        if entry["docs"]:
            line += f" | doc: {_compact(entry['docs'], 120)}"
        relevant_calls = [call for call in entry["lexical_call_candidates"]
                          if terms & set(_tokens(call.rsplit("::", 1)[-1]))]
        if relevant_calls:
            line += f" | calls?: {', '.join(relevant_calls[:2])}"
        lines.append(line)
    return "\n".join(lines)


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
