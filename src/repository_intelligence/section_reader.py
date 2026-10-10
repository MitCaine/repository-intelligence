"""Read explicitly selected Markdown sections from one local Git commit.

This source reader supplies byte evidence only, without resolving links or
interpreting the authority of any document. Ranges are half-open raw bytes.
Only document headings are targets; headings in lists and quotes are separate
scopes. max_output_bytes limits emitted text, excluding JSON metadata overhead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from .markdown_tree_index import HEADINGS, _heading_name
from .structural import ScanSetup, scan

SCHEMA_VERSION = 1
MAX_SOURCE_BYTES = 4_000_000
MAX_REQUEST_BYTES = 1_000_000
DEFAULT_OUTPUT_BYTES = 256_000
MAX_OUTPUT_BYTES = 4_000_000


def _git(repository: Path, *args: str) -> bytes:
    # Ambient Git settings must not redirect the explicit source repository.
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_")}
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repository), *args],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False,
        env=environment)
    if result.returncode:
        raise ValueError("Git source unavailable for the requested repository, revision or path")
    return result.stdout


def _path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise ValueError("path must be a canonical repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("path must be a canonical repository-relative POSIX path")
    return value


def _blob(repository: Path, revision: str, path: str) -> tuple[bytes, str]:
    # Literal pathspecs prevent wildcard and pathspec-magic interpretation.
    entries = _git(repository, "ls-tree", "-z", revision, "--", ":(literal)" + path).split(b"\0")
    matches = []
    for entry in entries:
        if entry:
            meta, name = entry.split(b"\t", 1)
            if name == path.encode("utf-8"):
                matches.append(meta.split())
    if len(matches) != 1 or matches[0][0] not in {b"100644", b"100755"} or matches[0][1] != b"blob":
        raise ValueError("requested path is missing or is not a regular committed file")
    object_id = matches[0][2].decode("ascii")
    size = int(_git(repository, "cat-file", "-s", object_id))
    if size > MAX_SOURCE_BYTES:
        raise ValueError("Markdown source exceeds the 4 MB per-document limit")
    source = _git(repository, "cat-file", "blob", object_id)
    if len(source) != size:
        raise ValueError("committed source byte count changed during acquisition")
    return source, object_id


def _sections(source: bytes, setup: ScanSetup) -> list[dict]:
    source.decode("utf-8")
    syntax, tree, _, _ = scan(".md", source, setup=setup)
    if syntax["diagnostic_count"]:
        raise ValueError("Markdown parse contains incomplete or unsupported syntax")
    headings = []

    def visit(node) -> None:
        for child in node.named_children:
            if child.type in HEADINGS:
                marker = next((item for item in child.named_children
                               if item.type.endswith("marker") or "underline" in item.type), None)
                level = (len(source[marker.start_byte:marker.end_byte].strip())
                         if child.type == "atx_heading" and marker else
                         1 if marker and marker.type == "setext_h1_underline" else 2)
                headings.append({"heading": _heading_name(child, source),
                                 "level": level, "start": child.start_byte})
            elif child.type == "section":
                visit(child)
    visit(tree)
    headings.sort(key=lambda entry: entry["start"])
    for index, entry in enumerate(headings):
        entry["end"] = next((other["start"] for other in headings[index + 1:]
                             if other["level"] <= entry["level"]), len(source))
    return headings


def read_sections(request: dict) -> dict:
    """Return a packet; invalid requests and unavailable selections are incomplete."""
    result = {"schema_version": SCHEMA_VERSION, "status": "incomplete",
              "repository": request.get("repository") if isinstance(request, dict) else None,
              "revision": request.get("revision") if isinstance(request, dict) else None,
              "documents": [], "errors": [], "emitted_bytes": 0,
              "output_limit_kind": "emitted_raw_utf8_text_bytes",
              "source_scope": "committed_objects_only; worktree changes are not observed"}
    try:
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        repository_value = request.get("repository")
        if not isinstance(repository_value, str) or not repository_value:
            raise ValueError("repository must be an explicit local directory")
        repository = Path(repository_value).resolve(strict=True)
        if not repository.is_dir():
            raise ValueError("repository must be a local directory")
        bare = _git(repository, "rev-parse", "--is-bare-repository").strip() == b"true"
        root_command = "--absolute-git-dir" if bare else "--show-toplevel"
        source_root = Path(os.fsdecode(_git(repository, "rev-parse", root_command)).rstrip("\r\n")).resolve(strict=True)
        if source_root != repository:
            raise ValueError("repository must identify the exact Git repository root")
        result["repository"] = str(source_root)
        revision = request.get("revision")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", revision):
            raise ValueError("revision must be a full 40- or 64-character commit object ID")
        revision = revision.lower()
        result["revision"] = revision
        object_format = _git(repository, "rev-parse", "--show-object-format=storage").decode().strip()
        if object_format not in {"sha1", "sha256"} or len(revision) != {"sha1": 40, "sha256": 64}[object_format]:
            raise ValueError("revision length does not match the repository object format")
        if _git(repository, "cat-file", "-t", revision).strip() != b"commit":
            raise ValueError("revision must identify a commit object")
        selections = request.get("selections")
        if not isinstance(selections, list) or not 1 <= len(selections) <= 64:
            raise ValueError("selections must contain between 1 and 64 documents")
        limit = request.get("max_output_bytes", DEFAULT_OUTPUT_BYTES)
        if type(limit) is not int or not 0 <= limit <= MAX_OUTPUT_BYTES:
            raise ValueError("max_output_bytes must be an integer between 0 and 4000000")
        result["max_output_bytes"] = limit
        grouped = {}
        for selection in selections:
            if not isinstance(selection, dict):
                raise ValueError("each selection must be an object")
            path = _path(selection.get("path"))
            headings = selection.get("headings")
            if not isinstance(headings, list) or not 1 <= len(headings) <= 256 or any(
                    not isinstance(heading, str) or not heading for heading in headings):
                raise ValueError("headings must contain between 1 and 256 nonempty exact heading strings")
            if "sha256" in selection and "expected_sha256" in selection and selection["sha256"] != selection["expected_sha256"]:
                raise ValueError("conflicting expected source identities")
            expected = selection.get("expected_sha256", selection.get("sha256"))
            if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected)):
                raise ValueError("expected sha256 must be a 64-character hexadecimal digest")
            document = grouped.setdefault(path, {"headings": [], "expected": set()})
            document["headings"].extend(heading for heading in headings if heading not in document["headings"])
            if expected is not None:
                document["expected"].add(expected.lower())
        setup = ScanSetup()
        incomplete = False
        for path, selection in grouped.items():
            document = {"path": path, "status": "incomplete", "identity": None,
                        "selection_coverage": [{"heading": heading, "status": "incomplete",
                                                "reason": "source_unavailable"}
                                               for heading in selection["headings"]],
                        "expected_sha256": sorted(selection["expected"]),
                        "ranges": [], "errors": []}
            result["documents"].append(document)
            try:
                source, object_id = _blob(repository, revision, path)
                digest = hashlib.sha256(source).hexdigest()
                document["identity"] = {"relative_path": path, "raw_sha256": digest,
                                        "byte_count": len(source),
                                        "git_blob": {"algorithm": object_format, "object_id": object_id,
                                                     "meaning": "blob read from requested commit"}}
                if selection["expected"] and selection["expected"] != {digest}:
                    raise ValueError("expected sha256 does not match committed source identity")
                sections = _sections(source, setup)
                selected = []
                for coverage in document["selection_coverage"]:
                    heading = coverage["heading"]
                    matches = [entry for entry in sections if entry["heading"] == heading]
                    coverage.pop("reason", None)
                    if len(matches) != 1:
                        coverage["reason"] = "missing_heading" if not matches else "ambiguous_heading"
                        continue
                    entry = matches[0]
                    coverage["requested_byte_range"] = {"start": entry["start"], "end": entry["end"]}
                    selected.append((entry["start"], entry["end"]))
                merged = []
                for start, end in sorted(set(selected)):
                    if merged and start <= merged[-1][1]:
                        merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
                    else:
                        merged.append((start, end))
                for start, end in merged:
                    budget = limit - result["emitted_bytes"]
                    text = source[start:min(end, start + budget)].decode("utf-8", "ignore")
                    emitted_end = start + len(text.encode("utf-8"))
                    document["ranges"].append({"byte_range": {"start": start, "end": emitted_end},
                                               "requested_byte_range": {"start": start, "end": end},
                                               "text": text, "complete": emitted_end == end})
                    result["emitted_bytes"] += emitted_end - start
                for coverage in document["selection_coverage"]:
                    if "requested_byte_range" not in coverage:
                        continue
                    bounds = coverage["requested_byte_range"]
                    if any(item["byte_range"]["start"] <= bounds["start"] and
                           item["byte_range"]["end"] >= bounds["end"] for item in document["ranges"]):
                        coverage["status"] = "complete"
                    else:
                        coverage["reason"] = "output_limit"
                document["status"] = ("complete" if all(item["status"] == "complete" for item in
                                                       document["selection_coverage"]) else "incomplete")
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                document["errors"].append(str(error))
            incomplete |= document["status"] != "complete"
        result["status"] = "incomplete" if incomplete else "complete"
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        result["errors"].append(str(error))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        with args.request.open("rb") as stream:
            raw = stream.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("request exceeds the 1 MB limit")
        result = read_sections(json.loads(raw))
    except (ValueError, OSError) as error:
        result = {"schema_version": SCHEMA_VERSION, "status": "incomplete", "errors": [str(error)]}
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
