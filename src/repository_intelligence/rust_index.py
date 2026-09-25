"""On-demand, source-bound Rust function locator (not a semantic call graph)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from .declarations import assign_named_ids, declaration

from .search import (compact as _compact, display_entry, format_compact,
                     format_tree_compact, query, rank, tokens as _tokens,
                     validate_query)


def _children(node: dict, kind: str) -> list[dict]:
    return [child for child in node.get("children", []) if child["kind"] == kind]


def _slice(source: bytes, node: dict) -> str:
    return source[node["start"][0] : node["end"][0]].decode("utf-8", "replace")


def _display_column(source: bytes, offset: int) -> int:
    """One-based character column for navigation, not declaration identity."""
    line_start = max(source.rfind(b"\n", 0, offset), source.rfind(b"\r", 0, offset)) + 1
    return len(source[line_start:offset].decode("utf-8", "replace")) + 1


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
                "column": _display_column(source, names[0]["start"][0]),
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
            "parse_error_count": error_count(tree), "functions": functions,
            "relationship_kind": "lexical call candidates only; not resolved call graph"}


def _authority_records(directory: Path) -> dict[str, list[dict]]:
    """Read existing authored anchors; they remain claims to confirm in source."""
    if not directory.is_dir():
        raise ValueError("Authority directory must be an existing directory")
    records: dict[str, list[dict]] = {}
    for document in sorted(directory.glob("*.md")):
        heading = ""
        fields: dict[str, str] = {}

        def finish() -> None:
            for token in re.findall(r"`([^`]+)`", fields.get("Anchors", "")):
                anchor = re.fullmatch(r"(.+?\.rs)(?:::(.*))?", token)
                if anchor is None:
                    continue
                symbols = anchor.group(2) or ""
                names = [part.strip() for part in symbols.strip("{}").split(",") if part.strip()]
                records.setdefault(anchor.group(1), []).append({
                    "authority": f"{document} ({heading})",
                    "contract": fields.get("Contract", ""),
                    "origin": fields.get("Origin / mutation", ""),
                    "must_not": fields.get("Must not", ""),
                    "symbols": names,
                })

        for line in [*document.read_text().splitlines(), "### END"]:
            if line.startswith("### "):
                finish()
                heading = line[4:].strip()
                fields = {}
            elif heading and ": " in line:
                key, value = line.split(": ", 1)
                if key in {"Contract", "Origin / mutation", "Must not", "Anchors"}:
                    fields[key] = value
    return records


def _guidance_for(entry: dict, root: Path, records: dict[str, list[dict]]) -> list[dict]:
    path = Path(entry["path"]).resolve().relative_to(root.resolve()).as_posix()
    qualified = entry["qualified_name"]
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", qualified))
    matched = []
    for record in records.get(path, []):
        symbols = record["symbols"]
        if not symbols:
            rank = 0
        elif any(qualified.endswith(symbol) for symbol in symbols if "::" in symbol):
            rank = 2
        elif any(symbol in identifiers for symbol in symbols if "::" not in symbol):
            rank = 1
        else:
            continue
        matched.append((rank, record))
    matched.sort(key=lambda item: (-item[0], item[1]["authority"]))
    return [{key: value for key, value in record.items() if key != "symbols"}
            for _, record in matched]


def query_tree(root: Path, terms: str, limit: int = 8, *, analyzer: str = "rust-analyzer",
               authority_dir: Path | None = None) -> dict:
    """Legacy Rust-only navigation; not the shared locator's v1 result contract."""
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
                               "parse_error_count": index["parse_error_count"]})
    candidates = rank(candidates, words)
    selected = [display_entry(entry, words) for entry in candidates[:limit]]
    if authority_dir is not None:
        records = _authority_records(authority_dir)
        for entry in selected:
            guidance = _guidance_for(entry, root, records)
            entry["guidance_candidate_count"] = len(guidance)
            entry["guidance_candidates"] = guidance[:2]
    return {"result_kind": "legacy_rust_query", "root": str(root), "query": terms,
            "scanned_files": scanned,
            "parse_error_count": parse_errors, "failures": failures,
            "total_matches": len(candidates), "matches": selected}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--authority-dir", type=Path,
                        help="optional authored Markdown anchor directory for candidate guidance")
    parser.add_argument("--json", action="store_true", help="emit structured JSON instead of compact text")
    args = parser.parse_args()
    if args.source.is_dir():
        result = query_tree(args.source, args.query, args.limit, authority_dir=args.authority_dir)
        print(json.dumps(result, indent=2) if args.json else format_tree_compact(result))
    else:
        result = query(index_file(args.source), args.query, args.limit)
        print(json.dumps(result, indent=2) if args.json else format_compact(result))


if __name__ == "__main__":
    main()
