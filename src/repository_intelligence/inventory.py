"""Query-independent source inventory and planning-to-candidate structural delta.

The caller supplies stable materializations; a working-tree walk is not atomic.
Neither an inventory digest nor a comparable delta attests to a Git checkout.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .locator import PARSERS, index_file
from .source import SCHEMA_VERSION, git_object_format
from .structural import probe


INVENTORY_SCHEMA_VERSION = 1
MAPPING_CONTRACT = "python-rust-source-callables-v1"
EXCLUDED_DIRECTORIES = {"target", "__pycache__", "venv"}


def _digest(scope: dict, files: list[dict]) -> str:
    material = {"scope": scope,
                "files": [{"path": item["path"],
                           "raw_sha256": (item["source_identity"] or {}).get("raw_sha256"),
                           "byte_count": (item["source_identity"] or {}).get("byte_count")}
                          for item in files]}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def inventory_tree(root: Path, *, stable: bool = False,
                   logical_root: str = ".") -> dict:
    """Inventory supported in-scope files; `stable` is a caller assertion."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Inventory root must be a real directory")
    if not logical_root or logical_root.startswith("/") or ".." in Path(logical_root).parts:
        raise ValueError("Logical root must be a nonempty relative identifier")
    root = root.resolve()
    parser_contract = {suffix: probe(suffix, b"")["parser"] for suffix in sorted(PARSERS)}
    object_format = git_object_format(root)
    files: list[dict] = []
    exclusions: list[dict] = []
    failures: list[dict] = []
    other_files = 0
    seen_physical: set[tuple[int, int]] = set()

    def walk_error(error: OSError) -> None:
        failures.append({"path": error.filename or ".", "error": type(error).__name__})

    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False,
                                                    onerror=walk_error):
        parent = Path(current)
        kept = []
        for name in sorted(directories):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            reason = ("excluded_directory" if name.startswith(".") or name in EXCLUDED_DIRECTORIES
                      else "symlink_directory" if path.is_symlink()
                      else "nested_repository" if (path / ".git").exists() else None)
            if reason is None:
                kept.append(name)
            else:
                exclusions.append({"path": relative, "reason": reason})
        directories[:] = kept
        for name in sorted(filenames):
            path = parent / name
            suffix = path.suffix.lower()
            if suffix not in PARSERS:
                other_files += 1
                continue
            relative = path.relative_to(root).as_posix()
            if name.startswith(".") or path.is_symlink():
                exclusions.append({"path": relative,
                                   "reason": "symlink_file" if path.is_symlink() else "hidden_file"})
                continue
            try:
                if not path.resolve().is_relative_to(root):
                    exclusions.append({"path": relative, "reason": "outside_root"})
                    continue
                stat = path.stat()
                physical = stat.st_dev, stat.st_ino
                if stat.st_ino and physical in seen_physical:
                    exclusions.append({"path": relative, "reason": "duplicate_physical_file"})
                    failures.append({"path": relative, "error": "DuplicatePhysicalFile"})
                    continue
                if stat.st_ino:
                    seen_physical.add(physical)
                indexed = index_file(path, root=root, object_format=object_format)
            except (OSError, ValueError) as error:
                failures.append({"path": relative, "error": type(error).__name__})
                continue
            files.append({"path": relative, "language": "python" if suffix == ".py" else "rust",
                          "source_identity": indexed.get("source_identity"),
                          "parser": indexed.get("parser"),
                          "mapping_status": indexed["mapping_status"],
                          "adapter_coverage": indexed.get("adapter_coverage"),
                          "structural": indexed.get("structural"),
                          "declarations": indexed["functions"]})
            failures.extend({"path": relative, **failure} for failure in indexed["failures"])
            if indexed["mapping_status"] != "navigation_only":
                failures.append({"path": relative, "error": "IncompleteMapping"})
    files.sort(key=lambda item: item["path"])
    exclusions.sort(key=lambda item: (item["path"], item["reason"]))
    failures.sort(key=lambda item: (item["path"], item["error"]))
    scope = {"logical_root": logical_root, "extensions": sorted(PARSERS),
             "exclusion_rules": ["hidden_names", "target", "__pycache__", "venv",
                                 "symlinks", "nested_repositories", "duplicate_physical_files"],
             "excluded_paths": exclusions, "configuration": None}
    return {"inventory_schema_version": INVENTORY_SCHEMA_VERSION,
            "navigation_schema_version": SCHEMA_VERSION,
            "mapping_contract": MAPPING_CONTRACT, "parser_contract": parser_contract,
            "root": str(root), "scope": scope,
            "materialization": "caller_asserted_stable" if stable else "working_tree_non_atomic",
            "status": "complete" if stable and not failures else "incomplete",
            "incomplete_reasons": (["working_tree_non_atomic"] if not stable else [])
                                  + (["file_or_scan_failure"] if failures else []),
            "files": files, "failures": failures,
            "other_file_types_skipped": other_files,
            "inventory_digest": _digest(scope, files)}


def _declarations(inventory: dict) -> dict[tuple[str, str], dict]:
    found = {}
    for file in inventory["files"]:
        for entry in file["declarations"]:
            key = file["path"], entry["declaration_id"]
            if key in found:
                raise ValueError("Duplicate declaration identity in inventory")
            found[key] = entry
    return found


def _changes(planning: dict, candidate: dict, key: str) -> dict:
    before = {item[key]: item for item in planning}
    after = {item[key]: item for item in candidate}
    result = {status: [] for status in ("added", "removed", "modified", "unchanged")}
    for identity in sorted(before.keys() | after.keys()):
        prior, current = before.get(identity), after.get(identity)
        if prior is None:
            status = "added"
        elif current is None:
            status = "removed"
        elif prior["source_identity"]["raw_sha256"] == current["source_identity"]["raw_sha256"]:
            status = "unchanged"
        else:
            status = "modified"
        result[status].append({"path": identity, "planning": prior, "candidate": current})
    return result


def _summary(inventory: dict) -> dict:
    return {"root": inventory.get("root"), "status": inventory.get("status"),
            "materialization": inventory.get("materialization"),
            "incomplete_reasons": inventory.get("incomplete_reasons"),
            "digest": inventory.get("inventory_digest"), "scope": inventory.get("scope"),
            "failures": inventory.get("failures"),
            "files": [{"path": file["path"], "source_identity": file["source_identity"],
                       "mapping_status": file["mapping_status"],
                       "adapter_coverage": file["adapter_coverage"]}
                      for file in inventory.get("files", [])]}


def compare_inventories(planning: dict, candidate: dict) -> dict:
    """Return factual deltas only for compatible, caller-stable complete scans."""
    contract_fields = ("inventory_schema_version", "navigation_schema_version",
                       "mapping_contract", "parser_contract", "scope")
    mismatches = [field for field in contract_fields
                  if planning.get(field) is None or candidate.get(field) is None
                  or planning[field] != candidate[field]]
    basic = {"planning": _summary(planning), "candidate": _summary(candidate)}
    for label, inventory in (("planning", planning), ("candidate", candidate)):
        files = inventory.get("files", [])
        paths = [file.get("path") for file in files]
        if len(paths) != len(set(paths)):
            mismatches.append(f"{label}_duplicate_file_path")
        if inventory.get("status") == "complete" and (inventory.get("failures") or
                                                     inventory.get("materialization") !=
                                                     "caller_asserted_stable"):
            mismatches.append(f"{label}_false_complete_status")
    if mismatches:
        return {**basic, "status": "incompatible", "mismatches": mismatches,
                "file_changes": None, "declaration_changes": None}
    if planning.get("status") != "complete" or candidate.get("status") != "complete":
        return {**basic, "status": "incomplete", "mismatches": [],
                "file_changes": None, "declaration_changes": None}
    file_changes = _changes(planning["files"], candidate["files"], "path")
    before = _declarations(planning)
    after = _declarations(candidate)
    declaration_changes = {status: [] for status in ("added", "removed", "modified", "unchanged")}
    for identity in sorted(before.keys() | after.keys()):
        prior, current = before.get(identity), after.get(identity)
        if prior is None:
            status = "added"
        elif current is None:
            status = "removed"
        elif prior["declaration_sha256"] == current["declaration_sha256"]:
            status = "unchanged"
        else:
            status = "modified"
        declaration_changes[status].append({"path": identity[0], "declaration_id": identity[1],
                                            "planning": prior, "candidate": current})
    return {**basic, "status": "comparable_candidate_delta", "mismatches": [],
            "file_changes": file_changes, "declaration_changes": declaration_changes,
            "meaning": "factual structural candidates; no edit authority or checkout attestation"}
