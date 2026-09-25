"""Query-independent source inventory and planning-to-candidate structural delta.

The caller supplies stable materializations; a working-tree walk is not atomic.
Neither an inventory digest nor a comparable delta attests to a Git checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .locator import PARSERS, SUFFIX_LANGUAGE, index_file, walk_supported_paths
from .source import SCHEMA_VERSION, git_object_format
from .structural import probe


INVENTORY_SCHEMA_VERSION = 6
MAPPING_CONTRACT = "python-rust-javascript-typescript-java-go-csharp-c-cpp-source-callables-v1"


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
    paths, exclusions, failures, other_files = walk_supported_paths(root)
    # Navigation merely reports hardlink exclusions; a complete inventory
    # cannot omit a second in-scope relative source path.
    failures.extend({"path": item["path"], "error": "DuplicatePhysicalFile"}
                    for item in exclusions if item["reason"] == "duplicate_physical_file")
    for path in paths:
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        try:
            indexed = index_file(path, root=root, object_format=object_format)
        except (OSError, ValueError) as error:
            failures.append({"path": relative, "error": type(error).__name__})
            continue
        files.append({"path": relative, "language": SUFFIX_LANGUAGE[suffix],
                      "source_identity": indexed.get("source_identity"),
                      "parser": indexed.get("parser"),
                      "mapping_status": indexed["mapping_status"],
                      "adapter_coverage": indexed.get("adapter_coverage"),
                      "structural": indexed.get("structural"),
                      "module_bindings": indexed.get("module_bindings"),
                      "preprocessing": indexed.get("preprocessing"),
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
            "inventory_schema_version": inventory.get("inventory_schema_version"),
            "navigation_schema_version": inventory.get("navigation_schema_version"),
            "mapping_contract": inventory.get("mapping_contract"),
            "parser_contract": inventory.get("parser_contract"),
            "materialization": inventory.get("materialization"),
            "incomplete_reasons": inventory.get("incomplete_reasons"),
            "digest": inventory.get("inventory_digest"), "scope": inventory.get("scope"),
            "failures": inventory.get("failures"),
            "files": [{"path": file.get("path"), "source_identity": file.get("source_identity"),
                       "mapping_status": file.get("mapping_status"),
                       "adapter_coverage": file.get("adapter_coverage")}
                      for file in inventory.get("files", [])]}


def _complete_packet_errors(inventory: dict) -> list[str]:
    """Do not trust a top-level complete flag over contradictory file evidence."""
    if inventory.get("status") != "complete":
        return []
    errors = []
    if (inventory.get("materialization") != "caller_asserted_stable"
            or inventory.get("failures") or inventory.get("incomplete_reasons")):
        errors.append("false_complete_status")
    try:
        if inventory.get("inventory_digest") != _digest(inventory["scope"], inventory["files"]):
            errors.append("inventory_digest_mismatch")
    except (KeyError, TypeError, ValueError):
        errors.append("invalid_inventory_digest_input")
    parser_contract = inventory.get("parser_contract") or {}
    for file in inventory.get("files", []):
        path = file.get("path")
        suffix = Path(path).suffix.lower() if isinstance(path, str) else None
        identity = file.get("source_identity")
        parser = file.get("parser")
        structural = file.get("structural")
        coverage = file.get("adapter_coverage")
        declarations = file.get("declarations")
        expected = parser_contract.get(suffix)
        if (suffix not in PARSERS or file.get("language") != SUFFIX_LANGUAGE.get(suffix) or
                not isinstance(identity, dict) or identity.get("relative_path") != path or
                not isinstance(identity.get("raw_sha256"), str) or
                len(identity["raw_sha256"]) != 64 or
                not isinstance(identity.get("byte_count"), int) or identity["byte_count"] < 0 or
                not isinstance(parser, dict) or not isinstance(expected, dict) or
                any(parser.get(key) != value for key, value in (expected or {}).items()) or
                not isinstance(structural, dict) or structural.get("parser") != expected or
                not isinstance(coverage, dict) or not isinstance(declarations, list) or
                file.get("mapping_status") != "navigation_only"):
            errors.append(f"invalid_file_packet:{path}")
            continue
        if (structural.get("error_count") != 0 or structural.get("missing_count") != 0 or
                structural.get("diagnostic_count") != 0 or
                coverage.get("unhandled_node_count") != 0 or
                coverage.get("promised_node_count") != coverage.get("mapped_node_count") or
                coverage.get("mapped_node_count") != len(declarations) or
                structural.get("declaration_count") != coverage.get("promised_node_count")):
            errors.append(f"incomplete_file_packet:{path}")
        ids = [item.get("declaration_id") for item in declarations if isinstance(item, dict)]
        if (len(ids) != len(declarations) or not all(isinstance(item, str) for item in ids)
                or len(ids) != len(set(ids))):
            errors.append(f"duplicate_or_missing_declaration_id:{path}")
    return errors


def _unchanged_file_evidence_matches(prior: dict, current: dict) -> bool:
    """Identical bytes under one parser contract must yield identical mapping."""
    return (prior["adapter_coverage"] == current["adapter_coverage"]
            and prior["structural"] == current["structural"]
            and prior["module_bindings"] == current["module_bindings"]
            and prior["preprocessing"] == current["preprocessing"]
            and sorted(prior["declarations"], key=lambda item: item["declaration_id"])
            == sorted(current["declarations"], key=lambda item: item["declaration_id"]))


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
        if any(not isinstance(path, str) for path in paths) or len(paths) != len(set(paths)):
            mismatches.append(f"{label}_duplicate_file_path")
        mismatches.extend(f"{label}_{error}" for error in _complete_packet_errors(inventory))
    if mismatches:
        return {**basic, "status": "incompatible", "mismatches": mismatches,
                "file_changes": None, "declaration_changes": None}
    if planning.get("status") != "complete" or candidate.get("status") != "complete":
        return {**basic, "status": "incomplete", "mismatches": [],
                "file_changes": None, "declaration_changes": None}
    planning_files = {file["path"]: file for file in planning["files"]}
    candidate_files = {file["path"]: file for file in candidate["files"]}
    for path in sorted(planning_files.keys() & candidate_files.keys()):
        prior, current = planning_files[path], candidate_files[path]
        if (prior["source_identity"]["raw_sha256"] ==
                current["source_identity"]["raw_sha256"] and
                not _unchanged_file_evidence_matches(prior, current)):
            mismatches.append(f"unchanged_file_evidence:{path}")
    if mismatches:
        return {**basic, "status": "incompatible", "mismatches": mismatches,
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


def format_inventory_compact(inventory: dict, *, limit: int = 8) -> str:
    """Bound display only; the inventory and its digest still cover all files."""
    files = inventory["files"]
    declarations = sum(len(file["declarations"]) for file in files)
    scope = inventory["scope"]
    lines = [f"inventory {inventory['status']} files={len(files)} declarations={declarations} "
             f"digest={inventory['inventory_digest']}",
             f"schema={inventory['inventory_schema_version']} contract={inventory['mapping_contract']} "
             f"logical_root={scope['logical_root']} materialization={inventory['materialization']}",
             f"excluded={len(scope['excluded_paths'])} failures={len(inventory['failures'])} "
             f"other_types={inventory['other_file_types_skipped']}"]
    lines.extend(f"  {file['path']} {file['mapping_status']} "
                 f"sha256={file['source_identity']['raw_sha256'] if file['source_identity'] else 'unread'} "
                 f"declarations={len(file['declarations'])}" for file in files[:limit])
    if len(files) > limit:
        lines.append(f"  ... {len(files) - limit} more files; use --json")
    return "\n".join(lines)


def format_delta_compact(delta: dict, *, limit: int = 8) -> str:
    """Bound display of file and declaration changes without changing counts."""
    lines = [f"comparison {delta['status']}",
             f"schema={delta['planning']['inventory_schema_version']} "
             f"navigation_schema={delta['planning']['navigation_schema_version']} "
             f"contract={delta['planning']['mapping_contract']}",
             f"planning={delta['planning']['root']} status={delta['planning']['status']} "
             f"digest={delta['planning']['digest']}",
             f"candidate={delta['candidate']['root']} status={delta['candidate']['status']} "
             f"digest={delta['candidate']['digest']}",
             f"logical_root={delta['planning']['scope']['logical_root']} "
             f"extensions={','.join(delta['planning']['scope']['extensions'])} "
             f"excluded={len(delta['planning']['scope']['excluded_paths'])} "
             f"mismatches={len(delta['mismatches'])}"]
    if delta["mismatches"]:
        lines.extend(f"  mismatch: {reason}" for reason in delta["mismatches"][:limit])
        if len(delta["mismatches"]) > limit:
            lines.append(f"  ... {len(delta['mismatches']) - limit} more mismatches; use --json")
    for side in ("planning", "candidate"):
        summary = delta[side]
        if summary["incomplete_reasons"] or summary["failures"]:
            lines.append(f"{side} incomplete_reasons={summary['incomplete_reasons']} "
                         f"failures={len(summary['failures'])}")
    if delta["file_changes"] is None:
        lines.append("No structural delta emitted; use --json for full evidence")
        return "\n".join(lines)
    for label, changes in (("files", delta["file_changes"]),
                           ("declarations", delta["declaration_changes"])):
        counts = " ".join(f"{kind}={len(changes[kind])}"
                          for kind in ("added", "removed", "modified", "unchanged"))
        lines.append(f"{label}: {counts}")
        selected = [(kind, item) for kind in ("added", "removed", "modified")
                    for item in changes[kind]]
        lines.extend(f"  {kind}: {item['path']}"
                     + (f" {item['declaration_id']}" if label == "declarations" else "")
                     for kind, item in selected[:limit])
        if len(selected) > limit:
            lines.append(f"  ... {len(selected) - limit} more {label} changes; use --json")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    scan = subcommands.add_parser("scan", help="inventory one source root")
    scan.add_argument("root", type=Path)
    compare = subcommands.add_parser("compare", help="compare planning and candidate roots")
    compare.add_argument("planning", type=Path)
    compare.add_argument("candidate", type=Path)
    for command in (scan, compare):
        command.add_argument("--logical-root", default=".")
        command.add_argument("--assert-stable-materialization", action="store_true",
                             help="caller asserts supplied source roots remain stable for this scan")
        command.add_argument("--json", action="store_true", help="print full unbounded evidence")
        command.add_argument("--limit", type=int, default=8,
                             help="maximum displayed file/change lines per category (1-20)")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 20:
        parser.error("--limit must be from 1 to 20")
    if args.assert_stable_materialization:
        print("WARNING: stability is asserted by the caller; RI does not attest source snapshots",
              file=sys.stderr)
    if args.command == "scan":
        result = inventory_tree(args.root, stable=args.assert_stable_materialization,
                                logical_root=args.logical_root)
        output = json.dumps(result, indent=2) if args.json else format_inventory_compact(
            result, limit=args.limit)
        status = result["status"]
    else:
        planning = inventory_tree(args.planning, stable=args.assert_stable_materialization,
                                  logical_root=args.logical_root)
        candidate = inventory_tree(args.candidate, stable=args.assert_stable_materialization,
                                   logical_root=args.logical_root)
        result = compare_inventories(planning, candidate)
        output = json.dumps(result, indent=2) if args.json else format_delta_compact(
            result, limit=args.limit)
        status = result["status"]
    print(output)
    return 0 if status in {"complete", "comparable_candidate_delta"} else 3 if status == "incompatible" else 2


if __name__ == "__main__":
    raise SystemExit(main())
