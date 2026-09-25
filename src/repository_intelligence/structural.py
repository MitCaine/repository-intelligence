"""Pinned Tree-sitter syntax evidence alongside the existing navigation adapters.

This is a small language seam, not a completeness inventory. The source of truth
for returned byte spans is always the raw input, even when Python is transcoded
to UTF-8 for Tree-sitter.
"""

from __future__ import annotations

import hashlib
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


ADAPTER_VERSION = 1
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

JS_CALLABLES = {"function_declaration", "generator_function_declaration",
                "function_expression", "generator_function", "arrow_function",
                "method_definition"}


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


def _rust_start(node, source: bytes) -> int:
    attachments = rust_attachments(node, source)
    return attachments[0].start_byte if attachments else node.start_byte


def scan(suffix: str, source: bytes) -> tuple[dict, Node, bytes, _RawOffsets | None]:
    """Return evidence, syntax tree, and decoded input for a language adapter."""
    grammar_name, distribution, provider = GRAMMARS[suffix]
    language = Language(provider.language() if suffix in {".py", ".rs"} else provider())
    parse_bytes, encoding, offsets = (python_input(source) if suffix == ".py"
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
        elif suffix in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"} \
                and node.type in JS_CALLABLES:
            selected = node
            name_node = node.child_by_field_name("name")
        elif suffix == ".java" and node.type in {"method_declaration", "constructor_declaration",
                                                  "compact_constructor_declaration",
                                                  "lambda_expression"} \
                and node.child_by_field_name("body") is not None:
            selected = node
            name_node = node.child_by_field_name("name")
        elif suffix == ".go" and node.type in {"function_declaration", "method_declaration",
                                                "func_literal"}:
            selected = node
            name_node = node.child_by_field_name("name")
        elif suffix == ".cs" and node.type in {"method_declaration", "constructor_declaration",
                                                "destructor_declaration", "operator_declaration",
                                                "conversion_operator_declaration",
                                                "local_function_statement", "lambda_expression",
                                                "anonymous_method_expression",
                                                "accessor_declaration", "property_declaration",
                                                "indexer_declaration"} \
                and (node.child_by_field_name("body") is not None or
                     (node.type == "anonymous_method_expression" and any(
                         child.type == "block" for child in node.named_children)) or
                     (node.type in {"property_declaration", "indexer_declaration"} and
                      node.child_by_field_name("value") is not None and
                      node.child_by_field_name("value").type == "arrow_expression_clause")):
            selected = node
            name_node = node.child_by_field_name("name")
        elif suffix in {".c", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"} \
                and node.type in {"function_definition", "lambda_expression"}:
            selected = node
            name_node = None
        if selected is not None:
            declaration_count += 1
            if len(declarations) < MAX_DECLARATION_DETAILS:
                kind = ("lambda" if selected.type in {"lambda", "lambda_expression", "func_literal",
                                                       "anonymous_method_expression"}
                        else "closure" if selected.type == "closure_expression"
                        else "arrow" if selected.type == "arrow_function" else "function")
                start_node = (node.parent if suffix in {".c", ".cc", ".cpp", ".cxx",
                                                        ".hpp", ".hh", ".hxx"}
                              and node.parent is not None
                              and node.parent.type in {"template_declaration", "friend_declaration"}
                              else node)
                start = raw(_rust_start(node, source) if suffix == ".rs"
                            and kind == "function" else start_node.start_byte)
                end = raw(node.end_byte)
                name = (parse_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
                        if name_node is not None else None)
                declarations.append({"kind": kind, "name": name,
                                     "byte_range": {"start": start, "end": end},
                                     "declaration_sha256": hashlib.sha256(source[start:end]).hexdigest()})
        pending.extend(reversed(node.children))
    result = {"parser": {"name": "tree-sitter", "runtime_version": version("tree-sitter"),
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
    return result, root, parse_bytes, offsets


def probe(suffix: str, source: bytes) -> dict:
    """Return partial structural evidence without exposing parser objects."""
    return scan(suffix, source)[0]
