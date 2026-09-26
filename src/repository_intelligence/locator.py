"""Locate current functions in supported source files without a saved index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import structural
from .scan import (LANGUAGE_SUFFIX, MAX_PARSE_BYTES, PARSERS, SUFFIX_LANGUAGE,
                   index_file, parse_language_choices, walk_supported_paths)
from .search import display_entry, format_compact, format_tree_compact, query, rank, validate_query
from .source import SCHEMA_VERSION, git_object_format


def query_path(source: Path, terms: str, limit: int = 8, *, root: Path | None = None,
               language: str | None = None, language_choices: dict[str, str] | None = None,
               excluded_directories: tuple[str, ...] = ()) -> dict:
    words = validate_query(terms, limit)
    if source.is_symlink():
        return query(index_file(source, root=root, language=language), terms, limit)
    if source.is_file() or (source.exists() and not source.is_dir()):
        return query(index_file(source, root=root, language=language), terms, limit)
    if not source.is_dir():
        raise ValueError("Source must be an existing file or directory")
    if root is not None:
        raise ValueError("Explicit root applies only to a direct file query")
    if language is not None:
        raise ValueError("Explicit language applies only to a direct file query; use language_choices for a directory")
    candidates: list[dict] = []
    files: dict[str, dict] = {}
    paths, excluded_paths, failures, out_of_scope, unsupported = walk_supported_paths(
        source, language_choices=language_choices, excluded_directories=excluded_directories)
    scanned = 0
    parse_errors = 0
    structural_errors = 0
    incomplete_files = 0
    object_format = git_object_format(source)
    scan_setup = structural.ScanSetup()
    for path in paths:
        try:
            choice = (language_choices or {}).get(path.relative_to(source).as_posix())
            indexed = index_file(path, root=source, object_format=object_format,
                                 language=choice, scan_setup=scan_setup)
        except (OSError, ValueError) as error:
            failures.append({"path": str(path), "error": type(error).__name__})
            continue
        files[str(path)] = {key: indexed.get(key) for key in
                            ("source_identity", "parser", "structural", "preprocessing", "module_bindings",
                             "adapter_coverage", "mapping_status", "parse_error_count")}
        if indexed["failures"]:
            failures.extend({"path": str(path), "source_identity": indexed["source_identity"],
                             **failure} for failure in indexed["failures"])
            continue
        if indexed["mapping_status"] == "excluded":
            failures.append({"path": str(path), "error": "SourceBecameExcluded",
                             "reason": indexed["excluded_reason"]})
            continue
        scanned += 1
        incomplete_files += indexed["mapping_status"] == "incomplete"
        parse_errors += indexed["parse_error_count"]
        structural_errors += (indexed["structural"]["error_count"]
                              + indexed["structural"]["missing_count"])
        candidates.extend({**entry, "path": str(path),
                           "raw_sha256": indexed["raw_sha256"],
                           "git_blob_sha1": indexed["git_blob_sha1"],
                           "source_identity": indexed["source_identity"],
                           "parse_error_count": indexed["parse_error_count"]}
                          for entry in indexed["functions"])
    if not paths and not unsupported and not failures and not excluded_paths:
        raise ValueError("No supported source files found in directory")
    ranked = rank(candidates, words)
    return {"schema_version": SCHEMA_VERSION, "root": str(source), "query": terms,
            "scan_scope": {"root": str(source.resolve()),
                           "extensions": sorted(PARSERS),
                           "source_kind": "working_tree_non_atomic",
                           "excluded_paths": excluded_paths,
                           "unsupported_paths": unsupported,
                           "other_file_types_skipped": out_of_scope},
            "mapping_status": ("incomplete" if failures or parse_errors or structural_errors
                               or incomplete_files
                               else "unsupported" if not paths and unsupported
                               else "excluded" if not paths else "navigation_only"),
            "scanned_files": scanned,
            "files": files,
            "parse_error_count": parse_errors, "structural_error_count": structural_errors,
            "failures": failures,
            "total_matches": len(ranked),
            "matches": [display_entry(entry, words) for entry in ranked[:limit]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--root", type=Path, help="allowed root for a direct file query")
    parser.add_argument("--language", choices=sorted(LANGUAGE_SUFFIX),
                        help="explicit parser for a direct file with an ambiguous extension")
    parser.add_argument("--header-language", action="append", default=[], metavar="PATH=c|cpp",
                        help="select a relative .h path for directory navigation")
    parser.add_argument("--exclude-directory", action="append", default=[], metavar="NAME")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = query_path(args.source, args.query, args.limit, root=args.root,
                        language=args.language,
                        language_choices=parse_language_choices(args.header_language),
                        excluded_directories=tuple(args.exclude_directory))
    print(json.dumps(result, indent=2) if args.json else
          (format_tree_compact(result) if "scan_scope" in result else format_compact(result)))


if __name__ == "__main__":
    main()
