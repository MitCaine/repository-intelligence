"""Locate current functions in supported source files without a saved index."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import c_family_tree_index, csharp_tree_index, go_tree_index, java_tree_index, js_tree_index, python_tree_index, rust_tree_index, structural
from .search import (display_entry, format_compact, format_tree_compact, query, rank,
                     validate_query)
from .source import SCHEMA_VERSION, git_object_format, identify_bytes


PARSERS = {".py": python_tree_index.index_source, ".rs": rust_tree_index.index_source,
           ".java": java_tree_index.index_source,
           ".go": go_tree_index.index_source,
           ".cs": csharp_tree_index.index_source,
           **{suffix: c_family_tree_index.index_source for suffix in
              (".c", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx")},
           **{suffix: js_tree_index.index_source for suffix in
              (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")}}
LANGUAGE_SUFFIX = {"python": ".py", "rust": ".rs", "javascript": ".js",
                   "typescript": ".ts", "tsx": ".tsx", "java": ".java", "go": ".go",
                   "csharp": ".cs", "c": ".c", "cpp": ".cpp"}
SUFFIX_LANGUAGE = {suffix: ("javascript" if suffix in {".js", ".jsx", ".mjs", ".cjs"}
                            else "typescript" if suffix == ".ts" else "tsx"
                            if suffix == ".tsx" else "python" if suffix == ".py"
                            else "java" if suffix == ".java" else "go" if suffix == ".go"
                            else "csharp" if suffix == ".cs" else "c" if suffix == ".c"
                            else "cpp" if suffix in {".cc", ".cpp", ".cxx", ".hpp", ".hh",
                                                     ".hxx"} else "rust")
                   for suffix in PARSERS}
MAX_PARSE_BYTES = 4_000_000
PARSE_FAILURES = (OSError, ValueError, SyntaxError, UnicodeError)
_AUTO_FORMAT = object()
EXCLUDED_DIRECTORIES = {"target", "__pycache__", "venv"}


def index_file(path: Path, *, root: Path | None = None,
               object_format: str | None | object = _AUTO_FORMAT,
               language: str | None = None) -> dict:
    """Identify one file's bytes, then attempt structural navigation if supported."""
    if language is not None and language not in LANGUAGE_SUFFIX:
        raise ValueError(f"Unsupported language: {language}")
    root = root or path.parent
    excluded_reason = ("symlink_path" if path.is_symlink() else
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
    extension = path.suffix.lower()
    if language is not None and extension in PARSERS \
            and SUFFIX_LANGUAGE[extension] != language:
        return {**basic, "mapping_status": "unsupported", "parser": None,
                "unsupported_reason": "language_extension_mismatch"}
    parser_suffix = LANGUAGE_SUFFIX[language] if language is not None else extension
    parser = PARSERS.get(parser_suffix)
    if parser is None:
        return {**basic, "mapping_status": "unsupported", "parser": None,
                "unsupported_reason": "no_language_adapter_selected"}
    if len(source) > MAX_PARSE_BYTES:
        return {**basic, "mapping_status": "incomplete", "parser": None,
                "failures": [{"error": "SourceLimitExceeded", "limit_bytes": MAX_PARSE_BYTES}]}
    try:
        syntax, tree, parse_bytes, offsets = structural.scan(parser_suffix, source)
    except (OSError, ValueError, UnicodeError, ImportError, SyntaxError, LookupError) as error:
        return {**basic, "mapping_status": "incomplete", "parser": None,
                "structural": None,
                "failures": [{"error": type(error).__name__, "stage": "tree_sitter"}]}
    parser_info = {**syntax["parser"], "version": syntax["parser"]["runtime_version"],
                   "runtime": "tree-sitter"}
    try:
        indexed = (parser(path, source, tree=tree, parse_bytes=parse_bytes,
                          offsets=offsets) if parser_suffix == ".py"
                   else parser(path, source, tree=tree))
    except PARSE_FAILURES as error:
        return {**basic, "mapping_status": "incomplete", "parser": parser_info,
                "structural": syntax,
                "failures": [{"error": type(error).__name__}]}
    return {**indexed, "schema_version": SCHEMA_VERSION, "source_identity": identity,
            "parser": parser_info, "structural": syntax,
            "mapping_status": ("incomplete" if indexed["parse_error_count"]
                               or syntax["error_count"] or syntax["missing_count"]
                               else "navigation_only"),
            "failures": []}


def walk_supported_paths(root: Path) -> tuple[list[Path], list[dict], list[dict], int]:
    """Share only traversal/exclusion facts; consumers choose failure policy."""
    paths: list[Path] = []
    exclusions: list[dict] = []
    failures: list[dict] = []
    other_files = 0
    seen_physical: set[tuple[int, int]] = set()
    resolved_root = root.resolve()

    def walk_error(error: OSError) -> None:
        failures.append({"path": error.filename or str(root), "error": type(error).__name__})

    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False,
                                                    onerror=walk_error):
        parent = Path(current)
        kept = []
        for name in sorted(directories):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            reason = ("excluded_directory" if name.startswith(".") or name in EXCLUDED_DIRECTORIES
                      else "symlink_directory" if path.is_symlink()
                      else "nested_repository" if (path / ".git").exists() else None)
            if reason is None:
                kept.append(name)
            else:
                exclusions.append({"path": relative, "reason": reason})
        directories[:] = kept
        for name in sorted(filenames):
            path = parent / name
            if path.suffix.lower() not in PARSERS:
                other_files += 1
                continue
            relative = path.relative_to(root).as_posix()
            if name.startswith(".") or path.is_symlink():
                exclusions.append({"path": relative,
                                   "reason": "symlink_file" if path.is_symlink() else "hidden_file"})
                continue
            try:
                if not path.resolve().is_relative_to(resolved_root):
                    exclusions.append({"path": relative, "reason": "outside_root"})
                    continue
                stat = path.stat()
                physical = stat.st_dev, stat.st_ino
                if stat.st_ino and physical in seen_physical:
                    exclusions.append({"path": relative, "reason": "duplicate_physical_file"})
                    continue
                if stat.st_ino:
                    seen_physical.add(physical)
                paths.append(path)
            except (OSError, ValueError) as error:
                failures.append({"path": relative, "error": type(error).__name__})
    return paths, exclusions, failures, other_files


def query_path(source: Path, terms: str, limit: int = 8, *, root: Path | None = None,
               language: str | None = None) -> dict:
    words = validate_query(terms, limit)
    if source.is_symlink():
        return query(index_file(source, root=root, language=language), terms, limit)
    if source.is_file():
        return query(index_file(source, root=root, language=language), terms, limit)
    if not source.is_dir():
        raise ValueError("Source must be an existing file or directory")
    if root is not None:
        raise ValueError("Explicit root applies only to a direct file query")
    if language is not None:
        raise ValueError("Explicit language applies only to a direct file query")
    candidates: list[dict] = []
    paths, excluded_paths, failures, out_of_scope = walk_supported_paths(source)
    scanned = 0
    parse_errors = 0
    structural_errors = 0
    object_format = git_object_format(source)
    for path in paths:
        try:
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
        structural_errors += (indexed["structural"]["error_count"]
                              + indexed["structural"]["missing_count"])
        candidates.extend({**entry, "path": str(path),
                           "raw_sha256": indexed["raw_sha256"],
                           "git_blob_sha1": indexed["git_blob_sha1"],
                           "source_identity": indexed["source_identity"],
                           "parse_error_count": indexed["parse_error_count"]}
                          for entry in indexed["functions"])
    if not paths:
        raise ValueError("No supported source files found in directory")
    ranked = rank(candidates, words)
    return {"schema_version": SCHEMA_VERSION, "root": str(source), "query": terms,
            "scan_scope": {"root": str(source.resolve()),
                           "extensions": sorted(PARSERS),
                           "source_kind": "working_tree_non_atomic",
                           "excluded_paths": excluded_paths,
                           "other_file_types_skipped": out_of_scope},
            "mapping_status": ("incomplete" if failures or parse_errors or structural_errors
                               else "navigation_only"),
            "scanned_files": scanned,
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = query_path(args.source, args.query, args.limit, root=args.root,
                        language=args.language)
    print(json.dumps(result, indent=2) if args.json else
          (format_tree_compact(result) if "scan_scope" in result else format_compact(result)))


if __name__ == "__main__":
    main()
