"""Markdown sections, front matter, and checklist items from the block grammar."""

from __future__ import annotations

from pathlib import Path
import re
from bisect import bisect_left, bisect_right

from .declarations import assign_named_ids, declaration, finalize_coverage
from .source import utf8_display_column


HEADINGS = {"atx_heading", "setext_heading"}
METADATA = {"minus_metadata", "plus_metadata"}
TASK_MARKERS = {"task_list_marker_checked", "task_list_marker_unchecked"}


def _heading_name(heading, source: bytes) -> str:
    content = heading.child_by_field_name("heading_content")
    if content is None:
        content = next((child for child in heading.named_children
                        if child.type == "paragraph"), None)
    if content is None:
        return ""
    inline = [child for child in content.named_children if child.type == "inline"]
    if inline:
        return " ".join(source[child.start_byte:child.end_byte].decode("utf-8").strip()
                        for child in inline)
    return source[content.start_byte:content.end_byte].decode("utf-8").strip()


def index_source(path: Path, source: bytes, *, tree) -> dict:
    """Map grammar-recognized document units without interpreting capsule policy."""
    if len(source) > 4_000_000:
        raise ValueError("Markdown source exceeds the 4 MB per-file limit")
    source.decode("utf-8")
    entries = []
    unhandled = []
    promised = 0
    line_ends = [match.end() for match in re.finditer(rb"\r\n|\r|\n", source)]
    task_counts: dict[tuple[str, ...], int] = {}

    def emit(node, kind: str, name: str, qualified: str, start: int, end: int,
             docs: str, **extra) -> None:
        entries.append({"name": name, "qualified_name": qualified,
                        "line": bisect_right(line_ends, start) + 1,
                        "column": utf8_display_column(source, start),
                        "end_line": bisect_left(line_ends, end) + (end > 0),
                        "signature": name, "docs": docs,
                        "lexical_call_candidates": [], "syntax_kind": node.type,
                        **extra, **declaration(source, kind, qualified, start, end)})

    def visit(node, owners: tuple[str, ...], levels=None) -> None:
        nonlocal promised
        if node.type in METADATA:
            promised += 1
            emit(node, "metadata", "front matter", "front matter",
                 node.start_byte, node.end_byte,
                 source[node.start_byte:node.end_byte].decode("utf-8"))
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
        # Some grammar containers hold several Setext headings rather than sections.
        # Walk every heading and retain only its direct section body before the next unit.
        siblings = node.named_children
        if levels is None:
            levels = []
        local_owners = (*owners, *(title for _, title in levels))
        for index, child in enumerate(siblings):
            if child.type in HEADINGS:
                promised += 1
                name = _heading_name(child, source)
                marker = next((item for item in child.named_children
                               if item.type.endswith("marker") or "underline" in item.type), None)
                level = (len(source[marker.start_byte:marker.end_byte].strip())
                         if child.type == "atx_heading" and marker else
                         1 if marker and marker.type == "setext_h1_underline" else 2)
                while levels and levels[-1][0] >= level:
                    levels.pop()
                levels.append((level, name))
                local_owners = (*owners, *(title for _, title in levels))
                boundary = next((item.start_byte for item in siblings[index + 1:]
                                 if item.type in HEADINGS or item.type == "section"), node.end_byte)
                if name:
                    emit(child, "section", name, " / ".join(local_owners),
                         child.start_byte, boundary,
                         source[child.end_byte:boundary].decode("utf-8"))
                else:
                    if len(unhandled) < 50:
                        unhandled.append({"syntax_kind": child.type,
                                      "byte_range": {"start": child.start_byte, "end": boundary}})
            else:
                if child.type == "section":
                    # Grammar sections are transparent: heading levels, not CST
                    # containers, determine mixed ATX/Setext ownership.
                    visit(child, owners, levels)
                    local_owners = (*owners, *(title for _, title in levels))
                else:
                    # Quotes/lists are separate scopes and cannot pop outer headings.
                    visit(child, local_owners)

    visit(tree, ())
    assign_named_ids(entries)
    coverage = finalize_coverage(entries, promised, promised - len(entries), 0)
    return {"path": str(path), "function_count": len(entries),
            "parse_error_count": promised - len(entries),
            "unhandled_declarations": unhandled, "bodyless_declarations": [],
            "adapter_coverage": coverage, "functions": entries,
            "relationship_kind": "Markdown document units; no call graph"}
