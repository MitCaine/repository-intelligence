"""Strict provider-neutral receipt parsing primitives."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .errors import PilotError, ReceiptVerificationError, ValidationError
from .validation import (
    _deep_freeze,
    _require_exact_bool,
    _require_exact_keys,
    _require_mapping,
    _require_sequence,
    _require_text,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256_file(path: Path) -> str:
    """Hash exact file bytes for protocol/schema identity binding."""

    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PilotError(f"cannot read required authority file {path}: {exc}") from exc
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ReceiptExpectations:
    """Independently supplied, recursively immutable receipt expectations."""

    receipt_kind: str
    receipt_schema_version: int | str
    harness_id: str
    harness_version: str
    input_paths: Mapping[str, str]
    cases: Mapping[str, tuple[str, ...]]
    authority_boundaries: Mapping[str, bool]
    stage_boundary: Mapping[str, bool]

    def __post_init__(self) -> None:
        for name in ("receipt_kind", "harness_id", "harness_version"):
            _require_text(getattr(self, name), name, identifier=True)
        if type(self.receipt_schema_version) is int:
            if self.receipt_schema_version < 1:
                raise ValidationError("receipt_schema_version must be positive")
        else:
            _require_text(self.receipt_schema_version, "receipt_schema_version", identifier=True)
        paths = _require_mapping(self.input_paths, "receipt input_paths")
        cases = _require_mapping(self.cases, "receipt cases")
        boundaries = _require_mapping(self.authority_boundaries, "receipt authority_boundaries")
        stage = _require_mapping(self.stage_boundary, "receipt stage_boundary")
        if not paths or not cases:
            raise ValidationError("receipt expectations require inputs and cases")
        for name, path in paths.items():
            _require_text(name, "receipt input name", identifier=True)
            _require_text(path, f"receipt input path {name}")
        normalized_cases: dict[str, tuple[str, ...]] = {}
        for case_id, checks in cases.items():
            _require_text(case_id, "receipt case identity", identifier=True)
            values = tuple(_require_sequence(checks, f"receipt checks {case_id}"))
            if not values:
                raise ValidationError(f"receipt checks {case_id} must be nonempty")
            for check in values:
                _require_text(check, f"receipt check {case_id}", identifier=True)
            normalized_cases[case_id] = values
        for collection_name, values in (
            ("authority_boundaries", boundaries),
            ("stage_boundary", stage),
        ):
            for name, expected in values.items():
                _require_text(name, f"{collection_name} name", identifier=True)
                _require_exact_bool(expected, f"{collection_name}.{name}")
        object.__setattr__(self, "input_paths", _deep_freeze(dict(paths)))
        object.__setattr__(self, "cases", _deep_freeze(normalized_cases))
        object.__setattr__(self, "authority_boundaries", _deep_freeze(dict(boundaries)))
        object.__setattr__(self, "stage_boundary", _deep_freeze(dict(stage)))


def validate_receipt(receipt: Mapping[str, Any], expectations: ReceiptExpectations) -> None:
    """Validate an untrusted receipt against independent closed expectations."""

    if not isinstance(expectations, ReceiptExpectations):
        raise ReceiptVerificationError("receipt expectations have the wrong type")
    try:
        _require_exact_keys(
            receipt,
            {"receipt_kind", "receipt_schema_version", "harness", "inputs", "cases", "summary", "authority_boundaries", "stage_boundary"},
            {"receipt_kind", "receipt_schema_version", "harness", "inputs", "cases", "summary", "authority_boundaries", "stage_boundary"},
            "receipt",
        )
    except ValidationError as exc:
        raise ReceiptVerificationError(str(exc)) from exc
    if receipt["receipt_kind"] != expectations.receipt_kind:
        raise ReceiptVerificationError("receipt kind mismatch")
    if receipt["receipt_schema_version"] != expectations.receipt_schema_version:
        raise ReceiptVerificationError("receipt schema version mismatch")

    harness = _require_mapping(receipt["harness"], "receipt.harness")
    _require_exact_keys(harness, {"id", "version"}, {"id", "version"}, "receipt.harness")
    if _receipt_text(harness["id"], "harness.id", identifier=True) != expectations.harness_id:
        raise ReceiptVerificationError("harness identity mismatch")
    if _receipt_text(harness["version"], "harness.version", identifier=True) != expectations.harness_version:
        raise ReceiptVerificationError("harness version mismatch")

    inputs = _require_mapping(receipt["inputs"], "receipt.inputs")
    _require_exact_keys(inputs, expectations.input_paths, expectations.input_paths, "receipt.inputs")
    for name, expected_path in expectations.input_paths.items():
        item = _require_mapping(inputs[name], f"receipt.inputs.{name}")
        _require_exact_keys(item, {"path", "sha256"}, {"path", "sha256"}, f"inputs.{name}")
        if _receipt_text(item["path"], f"inputs.{name}.path") != expected_path:
            raise ReceiptVerificationError(f"{name} authority path mismatch")
        digest = _receipt_text(item["sha256"], f"inputs.{name}.sha256")
        if not _SHA256_RE.fullmatch(digest):
            raise ReceiptVerificationError(f"{name} digest is not a lowercase SHA-256")

    cases = _require_sequence(receipt["cases"], "receipt.cases")
    if len(cases) != len(expectations.cases):
        raise ReceiptVerificationError("receipt conformance case count mismatch")
    seen: list[str] = []
    for index, case_value in enumerate(cases):
        case = _require_mapping(case_value, f"receipt.cases[{index}]")
        _require_exact_keys(case, {"case_id", "disposition", "checks"}, {"case_id", "disposition", "checks"}, f"receipt.cases[{index}]")
        case_id = _receipt_text(case["case_id"], f"case[{index}].case_id", identifier=True)
        if case_id in seen:
            raise ReceiptVerificationError("receipt case identities must be unique")
        seen.append(case_id)
        if case_id not in expectations.cases:
            raise ReceiptVerificationError(f"unknown conformance case {case_id}")
        if case["disposition"] != "pass":
            raise ReceiptVerificationError(f"conformance case {case_id} is not passing")
        checks = _require_sequence(case["checks"], f"case[{index}].checks")
        if len(checks) == 0 or any(type(check) is not str or not check.strip() for check in checks):
            raise ReceiptVerificationError(f"case {case_id} has invalid checks")
        if tuple(checks) != expectations.cases[case_id]:
            raise ReceiptVerificationError(f"conformance checks for {case_id} were tampered")
    if tuple(seen) != tuple(expectations.cases):
        raise ReceiptVerificationError("receipt conformance cases are missing or reordered")

    summary = _require_mapping(receipt["summary"], "receipt.summary")
    _require_exact_keys(summary, {"case_count", "passed_count", "failed_count", "overall_disposition"}, {"case_count", "passed_count", "failed_count", "overall_disposition"}, "receipt.summary")
    counts = {"case_count": len(cases), "passed_count": sum(case["disposition"] == "pass" for case in cases), "failed_count": sum(case["disposition"] != "pass" for case in cases)}
    for name, expected in counts.items():
        value = summary[name]
        if type(value) is not int or value != expected:
            raise ReceiptVerificationError(f"receipt summary {name} was not recomputed correctly")
    expected_overall = "pass" if counts["failed_count"] == 0 else "fail"
    if summary["overall_disposition"] != expected_overall:
        raise ReceiptVerificationError("receipt overall disposition is inconsistent")

    for field, expected_values in (("authority_boundaries", expectations.authority_boundaries), ("stage_boundary", expectations.stage_boundary)):
        values = _require_mapping(receipt[field], field)
        _require_exact_keys(values, expected_values, expected_values, field)
        for name, expected in expected_values.items():
            if _receipt_bool(values[name], f"{field}.{name}") is not expected:
                label = "authority boundary" if field == "authority_boundaries" else "stage boundary"
                raise ReceiptVerificationError(f"{label} {name} was tampered")


def _reject_json_constant(value: str) -> None:
    """Reject NaN and Infinity while parsing a closed receipt."""

    raise ReceiptVerificationError(f"receipt contains non-JSON constant {value}")

def _no_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Parse JSON objects without silently accepting duplicate authority fields."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReceiptVerificationError(f"receipt contains duplicate field {key}")
        result[key] = value
    return result

def _load_receipt(path: Path) -> Mapping[str, Any]:
    """Load a closed JSON object with strict duplicate/constant handling."""

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicate_object_pairs,
            parse_constant=_reject_json_constant,
        )
    except ReceiptVerificationError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptVerificationError(f"cannot parse receipt {path}: {exc}") from exc
    return _require_mapping(value, "receipt")

def _receipt_text(value: Any, name: str, *, identifier: bool = False) -> str:
    """Receipt-specific strict text validator that maps failures to receipt errors."""

    try:
        return _require_text(value, name, identifier=identifier)
    except ValidationError as exc:
        raise ReceiptVerificationError(str(exc)) from exc

def _receipt_bool(value: Any, name: str) -> bool:
    """Receipt-specific strict boolean validator."""

    try:
        return _require_exact_bool(value, name)
    except ValidationError as exc:
        raise ReceiptVerificationError(str(exc)) from exc
