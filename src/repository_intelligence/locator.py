"""Locate current functions in supported source files without a saved index."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from . import python_index, rust_index
from .search import (display_entry, format_compact, format_tree_compact, query, rank,
                     validate_query)


PARSERS = {".py": python_index.index_file, ".rs": rust_index.index_file}


def index_file(path: Path) -> dict:
    parser = PARSERS.get(path.suffix.lower())
    if parser is None:
        raise ValueError(f"Unsupported source type: {path.suffix or '<none>'}")
    return parser(path)


def query_path(source: Path, terms: str, limit: int = 8) -> dict:
    words = validate_query(terms, limit)
    if source.is_file():
        return query(index_file(source), terms, limit)
    if not source.is_dir():
        raise ValueError("Source must be an existing file or directory")
    candidates: list[dict] = []
    failures: list[dict] = []
    scanned = 0
    parse_errors = 0
    supported = 0
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in PARSERS:
            continue
        relative = path.relative_to(source)
        if any(part.startswith(".") or part in {"target", "__pycache__", ".venv", "venv"}
               for part in relative.parts):
            continue
        supported += 1
        try:
            indexed = index_file(path)
        except (OSError, ValueError, SyntaxError, UnicodeError,
                subprocess.SubprocessError, json.JSONDecodeError) as error:
            failures.append({"path": str(path), "error": type(error).__name__})
            continue
        scanned += 1
        parse_errors += indexed["parse_error_count"]
        candidates.extend({**entry, "path": str(path),
                           "raw_sha256": indexed["raw_sha256"],
                           "git_blob_sha1": indexed["git_blob_sha1"],
                           "parse_error_count": indexed["parse_error_count"]}
                          for entry in indexed["functions"])
    if supported == 0:
        raise ValueError("No supported .py or .rs files found in directory")
    ranked = rank(candidates, words)
    return {"root": str(source), "query": terms, "scanned_files": scanned,
            "parse_error_count": parse_errors, "failures": failures,
            "total_matches": len(ranked),
            "matches": [display_entry(entry, words) for entry in ranked[:limit]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = query_path(args.source, args.query, args.limit)
    print(json.dumps(result, indent=2) if args.json else
          (format_tree_compact(result) if args.source.is_dir() else format_compact(result)))


if __name__ == "__main__":
    main()
