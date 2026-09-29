"""Markdown sections, front matter, and checklist items from the block grammar."""

from __future__ import annotations

from pathlib import Path

from .declarations import assign_named_ids, declaration, finalize_coverage
from .source import utf8_display_column


HEADINGS = {"atx_heading", "setext_heading"}
METADATA = {"minus_metadata", "plus_metadata"}
TASK_MARKERS = {"task_list_marker_checked", "task_list_marker_unchecked"}


def _end_line(source: bytes, end: int) -> int:
    return source.count(b"\n", 0, end) + (end > 0 and source[end - 1:end] != b"\n")


def _heading_name(heading, source: bytes) -> str:
    content = heading.child_by_field_name("heading_content")
    if content is None:
        content = next((child for child in heading.named_children
                        if child.type == "paragraph"), None)
    return source[content.start_byte:content.end_byte].decode("utf-8").strip() if content else ""


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Map grammar-recognized document units without interpreting capsule policy."""
    if len(source) > 4_000_000:
        raise ValueError("Markdown source exceeds the 4 MB per-file limit")
    source.decode("utf-8")
    entries = []
    unhandled = []
    promised = 0
    task_counts: dict[tuple[str, ...], int] = {}

    def emit(node, kind: str, name: str, qualified: str, start: int, end: int,
             docs: str, **extra) -> None:
        entries.append({"name": name, "qualified_name": qualified,
                        "line": node.start_point.row + 1,
                        "column": utf8_display_column(source, start),
                        "end_line": _end_line(source, end),
                        "signature": name, "docs": docs,
                        "lexical_call_candidates": [], "syntax_kind": node.type,
                        **extra, **declaration(source, kind, qualified, start, end)})

    def visit(node, owners: tuple[str, ...]) -> None:
        nonlocal promised
        if node.type in METADATA:
            promised += 1
            emit(node, "metadata", "front matter", "front matter",
                 node.start_byte, node.end_byte,
                 source[node.start_byte:node.end_byte].decode("utf-8"))
        elif node.type == "section":
            heading = next((child for child in node.named_children
                            if child.type in HEADINGS), None)
            if heading is not None:
                promised += 1
                name = _heading_name(heading, source)
                if not name or node.start_byte >= node.end_byte:
                    if len(unhandled) < 50:
                        unhandled.append({"syntax_kind": heading.type,
                                          "byte_range": {"start": node.start_byte,
                                                         "end": node.end_byte}})
                else:
                    owners = (*owners, name)
                    next_section = next((child for child in node.named_children
                                         if child.type == "section"), None)
                    end = next_section.start_byte if next_section else node.end_byte
                    qualified = " / ".join(owners)
                    emit(node, "section", name, qualified, node.start_byte, end,
                         source[heading.end_byte:end].decode("utf-8"))
        elif node.type == "list_item":
            marker = next((child for child in node.named_children
                           if child.type in TASK_MARKERS), None)
            if marker is not None:
                promised += 1
                paragraph = next((child for child in node.named_children
                                  if child.type == "paragraph"), None)
                name = (source[paragraph.start_byte:paragraph.end_byte]
                        .decode("utf-8").strip() if paragraph else "")
                if not name:
                    if len(unhandled) < 50:
                        unhandled.append({"syntax_kind": node.type,
                                          "byte_range": {"start": node.start_byte,
                                                         "end": node.end_byte}})
                else:
                    task_counts[owners] = task_counts.get(owners, 0) + 1
                    qualified = " / ".join((*owners, f"checklist[{task_counts[owners]}]"))
                    nested = next((child for child in node.named_children
                                   if child.type == "list"), None)
                    end = nested.start_byte if nested else node.end_byte
                    emit(node, "checklist_item", name, qualified,
                         node.start_byte, end, source[node.start_byte:end].decode("utf-8"),
                         task_state=("checked" if marker.type == "task_list_marker_checked"
                                     else "unchecked"))
        for child in node.named_children:
            visit(child, owners)

    visit(tree, ())
    assign_named_ids(entries)
    coverage = finalize_coverage(entries, promised, promised - len(entries), 0)
    return {"path": str(path), "function_count": len(entries),
            "parse_error_count": promised - len(entries),
            "unhandled_declarations": unhandled, "bodyless_declarations": [],
            "adapter_coverage": coverage, "functions": entries,
            "relationship_kind": "Markdown document units; no call graph"}
