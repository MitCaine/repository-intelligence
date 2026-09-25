"""Small, byte-based declaration coordinates shared by current adapters."""

from __future__ import annotations

import hashlib


def declaration(source: bytes, kind: str, qualified_name: str,
                start: int, end: int) -> dict:
    """Describe one source unit; offsets are half-open in the supplied raw bytes."""
    if not 0 <= start < end <= len(source):
        raise ValueError("Declaration range is outside the supplied source bytes")
    return {"declaration_kind": kind,
            "declaration_id": f"{kind}:{qualified_name}@{start}",
            "byte_range": {"start": start, "end": end},
            "declaration_sha256": hashlib.sha256(source[start:end]).hexdigest()}


def assign_named_ids(entries: list[dict]) -> None:
    """Distinguish duplicate names without tying named identity to byte position."""
    ordinals: dict[tuple[str, str], int] = {}
    for entry in entries:
        if entry["declaration_kind"] in {"lambda", "closure"}:
            continue
        key = (entry["declaration_kind"], entry["qualified_name"])
        ordinal = ordinals.get(key, 0)
        entry["declaration_id"] = f"{key[0]}:{key[1]}#{ordinal}"
        ordinals[key] = ordinal + 1


def finalize_coverage(entries: list[dict], promised: int, unhandled: int,
                      bodyless_excluded: int) -> dict:
    """Check one-to-one source mapping and report the adapter's bounded promise."""
    if promised != len(entries) + unhandled:
        raise ValueError("Promised callable count is not accounted for")
    ranges = {(item["declaration_kind"], item["byte_range"]["start"],
               item["byte_range"]["end"]) for item in entries}
    if len(ranges) != len(entries):
        raise ValueError("Callable source range mapped more than once")
    return {"promised_node_count": promised, "mapped_node_count": len(entries),
            "unhandled_node_count": unhandled,
            "bodyless_excluded_count": bodyless_excluded}
