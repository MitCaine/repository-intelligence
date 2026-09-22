"""Strict provider-neutral receipt parsing primitives."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import ReceiptVerificationError, ValidationError
from .validation import _require_exact_bool, _require_mapping, _require_text


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
