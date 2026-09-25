"""Language-neutral ranking and bounded presentation of source symbols."""

from __future__ import annotations

import re
from pathlib import Path


def compact(value: str, limit: int) -> str:
    value = " ".join(value.split())
    return value[: limit - 1] + "…" if len(value) > limit else value


def tokens(value: str) -> list[str]:
    separated: list[str] = []
    for position, character in enumerate(value):
        if position and character.isupper():
            prior = value[position - 1]
            following = value[position + 1] if position + 1 < len(value) else ""
            if prior.islower() or prior.isdigit() or (prior.isupper() and following.islower()):
                separated.append(" ")
        separated.append(character)
    return re.findall(r"[^\W_]+", "".join(separated).casefold(), flags=re.UNICODE)


def validate_query(terms: str, limit: int) -> list[str]:
    words = tokens(terms)
    if not words or not 1 <= limit <= 20:
        raise ValueError("Provide query terms and a limit from 1 to 20")
    return words


def score(entry: dict, words: list[str]) -> int:
    name = set(tokens(entry["name"]))
    qualified = set(tokens(entry["qualified_name"]))
    docs = set(tokens(entry["docs"]))
    calls = set(word for call in entry["lexical_call_candidates"] for word in tokens(call))
    per_word = [8 * (word in name) + 3 * (word in qualified) + (word in docs)
                + (word in calls) for word in words]
    return sum(per_word) + 20 * max(0, sum(value > 0 for value in per_word) - 1)


def is_test_entry(entry: dict) -> bool:
    return ("tests" in Path(entry.get("path", "")).parts
            or "tests" in re.split(r"::|\.", entry["qualified_name"])[:-1])


def rank(entries: list[dict], words: list[str]) -> list[dict]:
    return sorted((entry for entry in entries if score(entry, words) > 0),
                  key=lambda entry: (is_test_entry(entry), -score(entry, words),
                                     entry.get("path", ""), entry["line"]))


def display_entry(entry: dict, words: list[str]) -> dict:
    """Bound a selected packet only after full extracted text has been ranked."""
    calls = entry["lexical_call_candidates"]
    wanted = set(words)
    exact = [call for call in calls if wanted <= set(tokens(call))]
    exact_set = set(exact)
    partial = [call for call in calls if call not in exact_set
               and wanted & set(tokens(call))]
    shown_set = exact_set | set(partial)
    remaining = [call for call in calls if call not in shown_set]
    return {**entry,
            "signature": compact(entry["signature"], 180),
            "docs": compact(entry["docs"], 220),
            "lexical_call_candidates": [compact(call, 80)
                                        for call in (exact + partial + remaining)[:12]]}


def query(index: dict, terms: str, limit: int = 8) -> dict:
    words = validate_query(terms, limit)
    ranked = rank(index["functions"], words)
    return {key: value for key, value in index.items() if key != "functions"} | {
        "query": terms, "matches": [display_entry(entry, words) for entry in ranked[:limit]],
        "total_matches": len(ranked)}


def format_compact(result: dict) -> str:
    """Render a bounded navigation packet; JSON remains available for machines."""
    lines = [
        f"{result['path']} sha256={result['raw_sha256']} "
        f"functions={result['function_count']} parse_errors={result['parse_error_count']}",
        f"query={result['query']!r} matches={result['total_matches']} "
        f"shown={len(result['matches'])}; calls are lexical candidates, not a call graph",
    ]
    terms = set(tokens(result["query"]))
    for entry in result["matches"]:
        line = f"L{entry['line']}-{entry['end_line']} {entry['qualified_name']}"
        if entry["docs"]:
            line += f" | doc: {compact(entry['docs'], 120)}"
        relevant_calls = [call for call in entry["lexical_call_candidates"]
                          if terms & set(tokens(call))]
        if relevant_calls:
            line += f" | calls?: {', '.join(relevant_calls[:2])}"
        lines.append(line)
    if result.get("mapping_status") == "unsupported":
        lines.append("UNSUPPORTED: bytes identified; no structural interpretation")
    elif result.get("mapping_status") == "incomplete":
        lines.append("INCOMPLETE: source could not be fully parsed; no absence claim is valid")
    return "\n".join(lines)


def format_tree_compact(result: dict) -> str:
    scope = result.get("scan_scope", {})
    exclusions = scope.get("excluded_paths", [])
    lines = [f"{result['root']} scanned={result['scanned_files']} "
             f"parse_errors={result['parse_error_count']} failures={len(result['failures'])} "
             f"excluded={len(exclusions)} status={result.get('mapping_status', 'unknown')}",
             f"query={result['query']!r} matches={result['total_matches']} "
             f"shown={len(result['matches'])}; calls are lexical candidates, not a call graph"]
    for entry in result["matches"]:
        lines.append(f"{entry['path']}:{entry['line']}-{entry['end_line']} "
                     f"{entry['qualified_name']} sha256={entry['raw_sha256']}")
        if entry.get("guidance_candidates"):
            shown = entry["guidance_candidates"]
            extra = entry["guidance_candidate_count"] - len(shown)
            lines.append("  guidance?: " + ", ".join(
                record["authority"] for record in shown)
                + (f" (+{extra} more)" if extra else ""))
    if result.get("mapping_status") == "incomplete" or result["failures"] or result["parse_error_count"]:
        lines.append("INCOMPLETE: some source could not be parsed; no absence claim is valid")
    if exclusions:
        lines.append("EXCLUDED: " + ", ".join(
            f"{item['path']} ({item['reason']})" for item in exclusions[:3])
            + (f" (+{len(exclusions) - 3} more; use --json)" if len(exclusions) > 3 else ""))
    return "\n".join(lines)
