"""Small, byte-based declaration coordinates shared by current adapters."""

from __future__ import annotations

import hashlib


def nearby_comment(node, source: bytes) -> str:
    """Small syntactic search hint from a directly preceding ordinary comment."""
    prior = node.prev_named_sibling
    if prior is None or prior.type not in {"comment", "line_comment", "block_comment"}:
        return ""
    gap = source[prior.end_byte:node.start_byte]
    if gap.strip() or gap.count(b"\n") > 1:
        return ""
    comment = source[prior.start_byte:prior.end_byte].decode("utf-8", "replace")
    lines = [line.strip(" /*\t\r\n") for line in comment.splitlines()]
    return " ".join(line for line in lines if line)


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
    counts: dict[tuple[str, str, str | None], int] = {}
    for entry in entries:
        if entry["declaration_kind"] in {"lambda", "closure"} or entry.get("anonymous"):
            continue
        key = (entry["declaration_kind"], entry["qualified_name"],
               entry.get("identity_signature"))
        counts[key] = counts.get(key, 0) + 1
    ordinals: dict[tuple[str, str, str | None], int] = {}
    for entry in entries:
        if entry["declaration_kind"] in {"lambda", "closure"} or entry.get("anonymous"):
            continue
        key = (entry["declaration_kind"], entry["qualified_name"],
               entry.get("identity_signature"))
        entry["identity_ambiguous"] = counts[key] > 1
        ordinal = ordinals.get(key, 0)
        discriminator = f"({key[2]})" if key[2] is not None else ""
        entry["declaration_id"] = f"{key[0]}:{key[1]}{discriminator}#{ordinal}"
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
