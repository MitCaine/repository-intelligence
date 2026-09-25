"""Shared source selection and byte-bound structural indexing for one scan."""

from __future__ import annotations

import os
from pathlib import Path

from . import structural
from .adapters import PARSERS
from .source import SCHEMA_VERSION, git_object_format, identify_bytes, legacy_git_blob_sha1


LANGUAGE_SUFFIX = {"python": ".py", "rust": ".rs", "javascript": ".js",
                   "typescript": ".ts", "tsx": ".tsx", "java": ".java", "go": ".go",
                   "csharp": ".cs", "c": ".c", "cpp": ".cpp"}
SUFFIX_LANGUAGE = {suffix: ("javascript" if suffix in {".js", ".jsx", ".mjs", ".cjs"}
                            else "typescript" if suffix in {".ts", ".mts", ".cts"} else "tsx"
                            if suffix == ".tsx" else "python" if suffix == ".py"
                            else "java" if suffix == ".java" else "go" if suffix == ".go"
                            else "csharp" if suffix == ".cs" else "c" if suffix == ".c"
                            else "cpp" if suffix in {".cc", ".cpp", ".cxx", ".hpp", ".hh",
                                                     ".hxx"} else "rust")
                   for suffix in PARSERS}
MAX_PARSE_BYTES = 4_000_000
PARSE_FAILURES = (OSError, ValueError, SyntaxError, UnicodeError)
_AUTO_FORMAT = object()
EXCLUDED_DIRECTORIES = {"target", "__pycache__", "venv", "node_modules"}
SOURCE_LIKE_SUFFIXES = {".h", ".m", ".mm", ".swift", ".kt", ".kts", ".rb",
                        ".php", ".scala", ".sc", ".vue", ".svelte", ".zig"}


def validate_scan_choices(language_choices: dict[str, str] | None,
                          excluded_directories: tuple[str, ...]) -> dict[str, str]:
    """Keep caller selection small: exact relative .h paths and directory names."""
    choices = language_choices or {}
    for path, language in choices.items():
        parts = Path(path).parts
        if (not path or Path(path).is_absolute() or ".." in parts or path != Path(path).as_posix()
                or Path(path).suffix.lower() != ".h" or language not in {"c", "cpp"}):
            raise ValueError("Language choices must map relative .h paths to c or cpp")
    for name in excluded_directories:
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Excluded directories must be simple directory names")
    return choices


def parse_language_choices(values: list[str]) -> dict[str, str]:
    """Parse repeatable PATH=c|cpp CLI choices without a config language."""
    choices = {}
    for value in values:
        path, separator, language = value.partition("=")
        if not separator or path in choices:
            raise ValueError("Expected unique PATH=c or PATH=cpp")
        choices[path] = language
    validate_scan_choices(choices, ())
    return choices


def index_file(path: Path, *, root: Path | None = None,
               object_format: str | None | object = _AUTO_FORMAT,
               language: str | None = None,
               scan_setup: structural.ScanSetup | None = None) -> dict:
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
        syntax, tree, parse_bytes, offsets = structural.scan(parser_suffix, source,
                                                              setup=scan_setup)
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
    syntax = structural.with_mapping(syntax, indexed)
    return {**indexed, "schema_version": SCHEMA_VERSION, "source_identity": identity,
            "raw_sha256": identity["raw_sha256"],
            "git_blob_sha1": legacy_git_blob_sha1(source),
            "parser": parser_info, "structural": syntax,
            "mapping_status": ("incomplete" if indexed["parse_error_count"]
                               or indexed["adapter_coverage"]["unhandled_node_count"]
                               or syntax["error_count"] or syntax["missing_count"]
                               else "navigation_only"),
            "failures": []}


def walk_supported_paths(root: Path, *, language_choices: dict[str, str] | None = None,
                         excluded_directories: tuple[str, ...] = ()) -> tuple[list[Path], list[dict], list[dict], int, list[dict]]:
    """Share only traversal/exclusion facts; consumers choose failure policy."""
    paths: list[Path] = []
    exclusions: list[dict] = []
    failures: list[dict] = []
    other_files = 0
    unsupported: list[dict] = []
    choices = validate_scan_choices(language_choices, excluded_directories)
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
            reason = ("caller_excluded_directory" if name in excluded_directories
                      else "excluded_directory" if name.startswith(".") or name in EXCLUDED_DIRECTORIES
                      else "symlink_directory" if path.is_symlink()
                      else "nested_repository" if (path / ".git").exists() else None)
            if reason is None:
                kept.append(name)
            else:
                exclusions.append({"path": relative, "reason": reason})
        directories[:] = kept
        for name in sorted(filenames):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if path.suffix.lower() not in PARSERS and relative not in choices:
                other_files += 1
                if path.suffix.lower() in SOURCE_LIKE_SUFFIXES:
                    unsupported.append({"path": relative, "reason": "no_language_adapter_selected"})
                continue
            if name.startswith(".") or path.is_symlink():
                exclusions.append({"path": relative,
                                   "reason": "symlink_file" if path.is_symlink() else "hidden_file"})
                continue
            try:
                if not path.resolve().is_relative_to(resolved_root):
                    exclusions.append({"path": relative, "reason": "outside_root"})
                    continue
                paths.append(path)
            except (OSError, ValueError) as error:
                failures.append({"path": relative, "error": type(error).__name__})
    return paths, exclusions, failures, other_files, unsupported
