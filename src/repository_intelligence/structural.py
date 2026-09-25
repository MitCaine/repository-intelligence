"""Pinned Tree-sitter syntax evidence alongside the existing navigation adapters.

This is a small language seam, not a completeness inventory. The source of truth
for returned byte spans is always the raw input, even when Python is transcoded
to UTF-8 for Tree-sitter.
"""

from __future__ import annotations

import io
import tokenize
from bisect import bisect_right
from importlib.metadata import version

from tree_sitter import Language, Node, Parser
import tree_sitter_python
import tree_sitter_rust
import tree_sitter_javascript
import tree_sitter_typescript
import tree_sitter_java
import tree_sitter_go
import tree_sitter_c_sharp
import tree_sitter_c
import tree_sitter_cpp

from .source import physical_lines


ADAPTER_VERSION = 2
MAX_DECLARATION_DETAILS = 100
MAX_DIAGNOSTIC_DETAILS = 50
GRAMMARS = {
    ".py": ("Python", "tree-sitter-python", tree_sitter_python),
    ".rs": ("Rust", "tree-sitter-rust", tree_sitter_rust),
    ".js": ("JavaScript", "tree-sitter-javascript", tree_sitter_javascript.language),
    ".jsx": ("JavaScript", "tree-sitter-javascript", tree_sitter_javascript.language),
    ".mjs": ("JavaScript", "tree-sitter-javascript", tree_sitter_javascript.language),
    ".cjs": ("JavaScript", "tree-sitter-javascript", tree_sitter_javascript.language),
    ".ts": ("TypeScript", "tree-sitter-typescript", tree_sitter_typescript.language_typescript),
    ".mts": ("TypeScript", "tree-sitter-typescript", tree_sitter_typescript.language_typescript),
    ".cts": ("TypeScript", "tree-sitter-typescript", tree_sitter_typescript.language_typescript),
    ".tsx": ("TSX", "tree-sitter-typescript", tree_sitter_typescript.language_tsx),
    ".java": ("Java", "tree-sitter-java", tree_sitter_java.language),
    ".go": ("Go", "tree-sitter-go", tree_sitter_go.language),
    ".cs": ("CSharp", "tree-sitter-c-sharp", tree_sitter_c_sharp.language),
    ".c": ("C", "tree-sitter-c", tree_sitter_c.language),
    ".cc": ("C++", "tree-sitter-cpp", tree_sitter_cpp.language),
    ".cpp": ("C++", "tree-sitter-cpp", tree_sitter_cpp.language),
    ".cxx": ("C++", "tree-sitter-cpp", tree_sitter_cpp.language),
    ".hpp": ("C++", "tree-sitter-cpp", tree_sitter_cpp.language),
    ".hh": ("C++", "tree-sitter-cpp", tree_sitter_cpp.language),
    ".hxx": ("C++", "tree-sitter-cpp", tree_sitter_cpp.language),
}



class _RawOffsets:
    def __init__(self, source: bytes, decoded: str, encoding: str) -> None:
        self.source = source
        self.encoding = encoding
        self.codec = "utf-8" if encoding == "utf-8-sig" else encoding
        self.utf8 = decoded.encode("utf-8")
        self.utf8_starts = [0]
        self.raw_starts = [0]
        for line in physical_lines(self.utf8):
            self.utf8_starts.append(self.utf8_starts[-1] + len(line))
        for line in physical_lines(source):
            self.raw_starts.append(self.raw_starts[-1] + len(line))
        if len(self.utf8_starts) != len(self.raw_starts):
            raise ValueError("Transcoded Python line structure differs from raw source")

    def raw(self, offset: int) -> int:
        line = min(bisect_right(self.utf8_starts, offset) - 1,
                   len(self.raw_starts) - 2)
        prefix = self.utf8[self.utf8_starts[line]:offset].decode("utf-8")
        bom = 3 if line == 0 and self.encoding == "utf-8-sig" else 0
        return self.raw_starts[line] + bom + len(prefix.encode(self.codec))


def python_input(source: bytes) -> tuple[bytes, str, _RawOffsets | None]:
    """Tree-sitter UTF-8 input and an optional map back to encoded source bytes."""
    encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
    decoded = source.decode(encoding)
    utf8 = decoded.encode("utf-8")
    return utf8, encoding, (_RawOffsets(source, decoded, encoding)
                            if utf8 != source else None)


def rust_attachments(node, source: bytes) -> list:
    """Return Rust outer attributes/docs, including intervening trivia."""
    start = node.start_byte
    prior = node.prev_named_sibling
    attached_nodes = []
    while prior is not None:
        snippet = source[prior.start_byte:prior.end_byte]
        attached = (prior.type == "attribute_item"
                    or (prior.type == "line_comment"
                        and snippet.startswith(b"///") and not snippet.startswith(b"////"))
                    or (prior.type == "block_comment"
                        and snippet.startswith(b"/**") and not snippet.startswith(b"/***")))
        if not attached and prior.type not in {"line_comment", "block_comment"}:
            break
        if attached:
            start = prior.start_byte
            attached_nodes.append(prior)
        prior = prior.prev_named_sibling
    return list(reversed(attached_nodes))


class ScanSetup:
    """Reuse immutable grammar metadata and parsers only within one scan call."""

    def __init__(self) -> None:
        self._grammars: dict[str, tuple[Parser, Language, dict]] = {}
        self._versions: dict[str, str] = {}

    def _version(self, distribution: str) -> str:
        if distribution not in self._versions:
            self._versions[distribution] = version(distribution)
        return self._versions[distribution]

    def get(self, suffix: str) -> tuple[Parser, dict]:
        grammar_name, distribution, provider = GRAMMARS[suffix]
        if grammar_name not in self._grammars:
            language = Language(provider.language() if suffix in {".py", ".rs"} else provider())
            info = {"name": "tree-sitter", "runtime_version": self._version("tree-sitter"),
                    "grammar": grammar_name, "grammar_version": self._version(distribution),
                    "grammar_abi_version": language.abi_version,
                    "adapter_version": ADAPTER_VERSION}
            self._grammars[grammar_name] = Parser(language), language, info
        parser, _, info = self._grammars[grammar_name]
        return parser, dict(info)


def scan(suffix: str, source: bytes, *, setup: ScanSetup | None = None) -> tuple[dict, Node, bytes, _RawOffsets | None]:
    """Return evidence, syntax tree, and decoded input for a language adapter."""
    parser, parser_info = (setup or ScanSetup()).get(suffix)
    parse_bytes, encoding, offsets = (python_input(source) if suffix == ".py"
                                      else (source, "utf-8", None))
    root = parser.parse(parse_bytes).root_node

    def raw(offset: int) -> int:
        return offsets.raw(offset) if offsets is not None else offset

    diagnostics = []
    error_count = 0
    missing_count = 0

    pending = [root]
    while pending:
        node = pending.pop()
        if node.type == "ERROR" or node.is_missing:
            if node.is_missing:
                missing_count += 1
            else:
                error_count += 1
            if len(diagnostics) < MAX_DIAGNOSTIC_DETAILS:
                diagnostics.append({"kind": "MISSING" if node.is_missing else "ERROR",
                                    "node_type": node.type,
                                    "byte_range": {"start": raw(node.start_byte),
                                                   "end": raw(node.end_byte)}})
        pending.extend(reversed(node.children))
    result = {"parser": parser_info,
            "source_encoding": encoding, "coordinate_space": "raw_bytes",
            "error_count": error_count, "missing_count": missing_count,
            "diagnostic_count": error_count + missing_count,
            "declaration_count": None,
            "diagnostics": diagnostics, "declarations": [],
            "details_truncated": error_count + missing_count > len(diagnostics),
            "coverage": "syntax_diagnostics_only"}
    return result, root, parse_bytes, offsets


def with_mapping(syntax: dict, indexed: dict) -> dict:
    """Present adapter-owned callable accounting beside independent syntax errors."""
    coverage = indexed["adapter_coverage"]
    promised = coverage["promised_node_count"]
    entries = indexed["functions"]
    declarations = [
        {"kind": entry["declaration_kind"] if entry["declaration_kind"] in
          {"lambda", "closure", "arrow"} else "function",
         "name": (None if entry.get("anonymous") or entry["declaration_kind"] in
                  {"lambda", "closure", "arrow"} else entry["name"]),
         "byte_range": entry["byte_range"],
         "declaration_sha256": entry["declaration_sha256"]}
        for entry in entries[:MAX_DECLARATION_DETAILS]]
    return {**syntax, "declaration_count": promised, "declarations": declarations,
            "details_truncated": (syntax["details_truncated"] or
                                  len(entries) > len(declarations)),
            "coverage": "adapter_owned_callable_accounting"}


def probe(suffix: str, source: bytes, *, setup: ScanSetup | None = None) -> dict:
    """Return syntax evidence and adapter-owned callable presentation."""
    from pathlib import Path
    from .locator import PARSERS
    syntax, tree, parse_bytes, offsets = scan(suffix, source, setup=setup)
    adapter = PARSERS[suffix]
    indexed = (adapter(Path("probe" + suffix), source, tree=tree,
                       parse_bytes=parse_bytes, offsets=offsets) if suffix == ".py"
               else adapter(Path("probe" + suffix), source, tree=tree))
    return with_mapping(syntax, indexed)
