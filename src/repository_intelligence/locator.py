"""Locate current functions in supported source files without a saved index."""

from __future__ import annotations

import argparse
from functools import lru_cache
import json
import os
import platform
import subprocess
from pathlib import Path

from . import python_index, rust_index
from .search import (display_entry, format_compact, format_tree_compact, query, rank,
                     validate_query)
from .source import SCHEMA_VERSION, git_object_format, identify_bytes


PARSERS = {".py": python_index.index_source, ".rs": rust_index.index_source}
MAX_PARSE_BYTES = 4_000_000
PARSE_FAILURES = (OSError, ValueError, SyntaxError, UnicodeError,
                  subprocess.SubprocessError, json.JSONDecodeError)
_AUTO_FORMAT = object()


@lru_cache(maxsize=1)
def _rust_analyzer_version() -> str | None:
    try:
        result = subprocess.run(["rust-analyzer", "--version"], capture_output=True,
                                text=True, check=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def index_file(path: Path, *, root: Path | None = None,
               object_format: str | None | object = _AUTO_FORMAT) -> dict:
    """Identify one file's bytes, then attempt structural navigation if supported."""
    root = root or path.parent
    excluded_reason = ("symlink_file" if path.is_symlink() else
                       "outside_root" if not path.resolve().is_relative_to(root.resolve())
                       else None)
    if excluded_reason is not None:
        return {"schema_version": SCHEMA_VERSION, "path": str(path),
                "source_identity": None, "raw_sha256": None, "function_count": 0,
                "parse_error_count": 0, "functions": [], "parser": None,
                "relationship_kind": "lexical call candidates only; not resolved call graph",
                "mapping_status": "excluded", "excluded_reason": excluded_reason,
                "failures": []}
    if object_format is _AUTO_FORMAT:
        object_format = git_object_format(root)
    try:
        source = path.read_bytes()
    except OSError as error:
        return {"schema_version": SCHEMA_VERSION, "path": str(path),
                "source_identity": None, "raw_sha256": None, "function_count": 0,
                "parse_error_count": 0, "functions": [], "parser": None,
                "relationship_kind": "lexical call candidates only; not resolved call graph",
                "mapping_status": "incomplete",
                "failures": [{"error": type(error).__name__}]}
    identity = identify_bytes(path, source, root=root, object_format=object_format)
    basic = {"schema_version": SCHEMA_VERSION, "path": str(path),
             "source_identity": identity, "raw_sha256": identity["raw_sha256"],
             "function_count": 0, "parse_error_count": 0, "functions": [],
             "relationship_kind": "lexical call candidates only; not resolved call graph",
             "failures": []}
    parser = PARSERS.get(path.suffix.lower())
    if parser is None:
        return {**basic, "mapping_status": "unsupported", "parser": None}
    parser_name = "python.ast" if path.suffix.lower() == ".py" else "rust-analyzer"
    parser_info = {"name": parser_name,
                   "version": (platform.python_version() if parser_name == "python.ast"
                               else _rust_analyzer_version()),
                   "adapter_version": 2,
                   "runtime": ("CPython" if parser_name == "python.ast" else None),
                   "runtime_version": (platform.python_version()
                                       if parser_name == "python.ast" else None),
                   "grammar": ("Python" if parser_name == "python.ast" else "Rust"),
                   "grammar_version": (platform.python_version()
                                       if parser_name == "python.ast" else None)}
    if len(source) > MAX_PARSE_BYTES:
        return {**basic, "mapping_status": "incomplete", "parser": parser_info,
                "failures": [{"error": "SourceLimitExceeded", "limit_bytes": MAX_PARSE_BYTES}]}
    try:
        indexed = parser(path, source)
    except PARSE_FAILURES as error:
        return {**basic, "mapping_status": "incomplete", "parser": parser_info,
                "failures": [{"error": type(error).__name__}]}
    return {**indexed, "schema_version": SCHEMA_VERSION, "source_identity": identity,
            "parser": parser_info,
            "mapping_status": "incomplete" if indexed["parse_error_count"] else "navigation_only",
            "failures": []}


def query_path(source: Path, terms: str, limit: int = 8, *, root: Path | None = None) -> dict:
    words = validate_query(terms, limit)
    if source.is_file():
        return query(index_file(source, root=root), terms, limit)
    if not source.is_dir():
        raise ValueError("Source must be an existing file or directory")
    if root is not None:
        raise ValueError("Explicit root applies only to a direct file query")
    candidates: list[dict] = []
    failures: list[dict] = []
    excluded_paths: list[dict] = []
    scanned = 0
    parse_errors = 0
    supported = 0
    out_of_scope = 0
    object_format = git_object_format(source)
    seen_files: set[tuple[int, int]] = set()

    def walk_error(error: OSError) -> None:
        failures.append({"path": error.filename or str(source), "error": type(error).__name__})

    for current, directories, filenames in os.walk(source, topdown=True, followlinks=False,
                                                    onerror=walk_error):
        parent = Path(current)
        retained = []
        for name in sorted(directories):
            directory = parent / name
            relative = directory.relative_to(source).as_posix()
            if name.startswith(".") or name in {"target", "__pycache__", "venv"}:
                reason = "excluded_directory"
            elif directory.is_symlink():
                reason = "symlink_directory"
            elif (directory / ".git").exists():
                reason = "nested_repository"
            else:
                retained.append(name)
                continue
            excluded_paths.append({"path": relative, "reason": reason})
        directories[:] = retained
        for name in sorted(filenames):
            path = parent / name
            if path.suffix.lower() not in PARSERS:
                out_of_scope += 1
                continue
            relative = path.relative_to(source).as_posix()
            if name.startswith(".") or path.is_symlink():
                excluded_paths.append({"path": relative,
                                       "reason": "symlink_file" if path.is_symlink() else "hidden_file"})
                continue
            try:
                resolved = path.resolve()
                if not resolved.is_relative_to(source.resolve()):
                    excluded_paths.append({"path": relative, "reason": "outside_root"})
                    continue
                stat = path.stat()
                physical = (stat.st_dev, stat.st_ino)
                if stat.st_ino and physical in seen_files:
                    excluded_paths.append({"path": relative, "reason": "duplicate_physical_file"})
                    continue
                if stat.st_ino:
                    seen_files.add(physical)
                supported += 1
                indexed = index_file(path, root=source, object_format=object_format)
            except (OSError, ValueError) as error:
                failures.append({"path": str(path), "error": type(error).__name__})
                continue
            if indexed["failures"]:
                failures.extend({"path": str(path), "source_identity": indexed["source_identity"],
                                 **failure} for failure in indexed["failures"])
                continue
            scanned += 1
            parse_errors += indexed["parse_error_count"]
            candidates.extend({**entry, "path": str(path),
                               "raw_sha256": indexed["raw_sha256"],
                               "git_blob_sha1": indexed["git_blob_sha1"],
                               "source_identity": indexed["source_identity"],
                               "parse_error_count": indexed["parse_error_count"]}
                              for entry in indexed["functions"])
    if supported == 0:
        raise ValueError("No supported .py or .rs files found in directory")
    ranked = rank(candidates, words)
    return {"schema_version": SCHEMA_VERSION, "root": str(source), "query": terms,
            "scan_scope": {"root": str(source.resolve()),
                           "extensions": sorted(PARSERS),
                           "source_kind": "working_tree_non_atomic",
                           "excluded_paths": excluded_paths,
                           "other_file_types_skipped": out_of_scope},
            "mapping_status": "incomplete" if failures or parse_errors else "navigation_only",
            "scanned_files": scanned,
            "parse_error_count": parse_errors, "failures": failures,
            "total_matches": len(ranked),
            "matches": [display_entry(entry, words) for entry in ranked[:limit]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--root", type=Path, help="allowed root for a direct file query")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = query_path(args.source, args.query, args.limit, root=args.root)
    print(json.dumps(result, indent=2) if args.json else
          (format_tree_compact(result) if args.source.is_dir() else format_compact(result)))


if __name__ == "__main__":
    main()
