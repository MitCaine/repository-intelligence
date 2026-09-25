"""Pinned Tree-sitter syntax evidence alongside the existing navigation adapters.

This is a two-language seam, not a completeness inventory. The source of truth
for returned byte spans is always the raw input, even when Python is transcoded
to UTF-8 for Tree-sitter.
"""

from __future__ import annotations

import hashlib
import io
import tokenize
from bisect import bisect_right
from importlib.metadata import version

from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_rust

from .python_index import _physical_lines


ADAPTER_VERSION = 1
MAX_DECLARATION_DETAILS = 100
MAX_DIAGNOSTIC_DETAILS = 50
GRAMMARS = {
    ".py": ("Python", "tree-sitter-python", tree_sitter_python),
    ".rs": ("Rust", "tree-sitter-rust", tree_sitter_rust),
}


class _RawOffsets:
    def __init__(self, source: bytes, decoded: str, encoding: str) -> None:
        self.source = source
        self.encoding = encoding
        self.codec = "utf-8" if encoding == "utf-8-sig" else encoding
        self.utf8 = decoded.encode("utf-8")
        self.utf8_starts = [0]
        self.raw_starts = [0]
        for line in _physical_lines(self.utf8):
            self.utf8_starts.append(self.utf8_starts[-1] + len(line))
        for line in _physical_lines(source):
            self.raw_starts.append(self.raw_starts[-1] + len(line))
        if len(self.utf8_starts) != len(self.raw_starts):
            raise ValueError("Transcoded Python line structure differs from raw source")

    def raw(self, offset: int) -> int:
        line = min(bisect_right(self.utf8_starts, offset) - 1,
                   len(self.raw_starts) - 2)
        prefix = self.utf8[self.utf8_starts[line]:offset].decode("utf-8")
        bom = 3 if line == 0 and self.encoding == "utf-8-sig" else 0
        return self.raw_starts[line] + bom + len(prefix.encode(self.codec))


def _python_input(source: bytes) -> tuple[bytes, str, _RawOffsets | None]:
    encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
    decoded = source.decode(encoding)
    utf8 = decoded.encode("utf-8")
    return utf8, encoding, (_RawOffsets(source, decoded, encoding)
                            if utf8 != source else None)


def _rust_start(node, source: bytes) -> int:
    """Include adjacent Rust attributes/doc comments in the source envelope."""
    start = node.start_byte
    prior = node.prev_named_sibling
    while prior is not None and prior.type in {
            "attribute_item", "inner_attribute_item", "line_comment", "block_comment"}:
        if source[prior.end_byte:start].strip():
            break
        start = prior.start_byte
        prior = prior.prev_named_sibling
    return start


def probe(suffix: str, source: bytes) -> dict:
    """Return partial structural evidence; no exhaustive coverage is asserted."""
    grammar_name, distribution, module = GRAMMARS[suffix]
    language = Language(module.language())
    parse_bytes, encoding, offsets = (_python_input(source) if suffix == ".py"
                                      else (source, "utf-8", None))
    root = Parser(language).parse(parse_bytes).root_node

    def raw(offset: int) -> int:
        return offsets.raw(offset) if offsets is not None else offset

    declarations = []
    diagnostics = []
    declaration_count = 0
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
        selected = None
        name_node = None
        if suffix == ".py":
            if node.type == "decorated_definition":
                selected = next((child for child in node.named_children
                                 if child.type == "function_definition"), None)
                if selected is not None:
                    name_node = selected.child_by_field_name("name")
            elif node.type == "function_definition" and node.parent.type != "decorated_definition":
                selected = node
                name_node = node.child_by_field_name("name")
            elif node.type == "lambda" and node.is_named:
                selected = node
        elif node.type in {"function_item", "closure_expression"}:
            selected = node
            if node.type == "function_item":
                name_node = node.child_by_field_name("name")
        if selected is not None:
            declaration_count += 1
            if len(declarations) < MAX_DECLARATION_DETAILS:
                kind = ("lambda" if suffix == ".py" and selected.type == "lambda"
                        else "closure" if selected.type == "closure_expression" else "function")
                start = raw(_rust_start(node, source) if suffix == ".rs"
                            and kind == "function" else node.start_byte)
                end = raw(node.end_byte)
                name = (parse_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                        if name_node is not None else None)
                declarations.append({"kind": kind, "name": name,
                                     "byte_range": {"start": start, "end": end},
                                     "declaration_sha256": hashlib.sha256(source[start:end]).hexdigest()})
        pending.extend(reversed(node.children))
    return {"parser": {"name": "tree-sitter", "runtime_version": version("tree-sitter"),
                       "grammar": grammar_name, "grammar_version": version(distribution),
                       "grammar_abi_version": language.abi_version,
                       "adapter_version": ADAPTER_VERSION},
            "source_encoding": encoding, "coordinate_space": "raw_bytes",
            "error_count": error_count, "missing_count": missing_count,
            "diagnostic_count": error_count + missing_count,
            "declaration_count": declaration_count,
            "diagnostics": diagnostics, "declarations": declarations,
            "details_truncated": (declaration_count > len(declarations)
                                  or error_count + missing_count > len(diagnostics)),
            "coverage": "partial_navigation_evidence"}
