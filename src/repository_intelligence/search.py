"""Language-neutral ranking and bounded presentation of source symbols."""

from __future__ import annotations

import re
from pathlib import Path


def compact(value: str, limit: int) -> str:
    value = " ".join(value.split())
    return value[: limit - 1] + "…" if len(value) > limit else value


def tokens(value: str) -> list[str]:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    return re.findall(r"[a-z0-9]+", value.lower())


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


def query(index: dict, terms: str, limit: int = 8) -> dict:
    words = validate_query(terms, limit)
    ranked = rank(index["functions"], words)
    return {key: value for key, value in index.items() if key != "functions"} | {
        "query": terms, "matches": ranked[:limit], "total_matches": len(ranked)}


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
    return "\n".join(lines)


def format_tree_compact(result: dict) -> str:
    lines = [f"{result['root']} scanned={result['scanned_files']} "
             f"parse_errors={result['parse_error_count']} failures={len(result['failures'])}",
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
    if result["failures"] or result["parse_error_count"]:
        lines.append("INCOMPLETE: some source could not be parsed; no absence claim is valid")
    return "\n".join(lines)
