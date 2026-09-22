"""Primitive validation and canonicalization for repository-intelligence records.

This internal module owns JSON-shaped input normalization without depending on
identity, evidence, provider, or host-policy modules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Iterable, Optional

from .errors import ValidationError


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


def _require_exact_bool(value: Any, name: str) -> bool:
    """Accept only a JSON boolean; reject truthy strings, integers, and containers."""

    if type(value) is not bool:
        raise ValidationError(f"{name} must be a boolean")
    return value


def _require_text(value: Any, name: str, *, identifier: bool = False) -> str:
    """Accept a nonblank text value, optionally constrained to an identifier."""

    if type(value) is not str or not value.strip():
        raise ValidationError(f"{name} must be nonblank text")
    if identifier and not _ID_RE.fullmatch(value):
        raise ValidationError(f"{name} is not a valid identifier")
    return value


def _optional_text(value: Any, name: str) -> Optional[str]:
    """Validate a nullable text field without applying Python truthiness."""

    if value is None:
        return None
    return _require_text(value, name)


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    """Require a mapping with string keys."""

    if not isinstance(value, Mapping):
        raise ValidationError(f"{name} must be a mapping")
    for key in value:
        if type(key) is not str:
            raise ValidationError(f"{name} keys must be text")
    return value


def _require_sequence(value: Any, name: str) -> Sequence[Any]:
    """Require a list/tuple-like sequence, excluding strings and bytes."""

    if not isinstance(value, (list, tuple)):
        raise ValidationError(f"{name} must be a list or tuple")
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    allowed: Iterable[str],
    required: Iterable[str],
    name: str,
) -> None:
    """Reject unknown fields and report missing closed-contract fields."""

    allowed_set = set(allowed)
    required_set = set(required)
    unknown = sorted(set(value) - allowed_set)
    missing = sorted(required_set - set(value))
    if unknown:
        raise ValidationError(f"{name} has unknown fields: {', '.join(unknown)}")
    if missing:
        raise ValidationError(f"{name} is missing fields: {', '.join(missing)}")


def _json_value(value: Any, name: str = "value") -> Any:
    """Convert supported JSON-shaped input to a fresh, finite JSON value."""

    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValidationError(f"{name} cannot contain a non-finite float")
        return value
    if isinstance(value, Mapping):
        result = {}
        for key in sorted(value):
            if type(key) is not str:
                raise ValidationError(f"{name} mapping keys must be text")
            result[key] = _json_value(value[key], f"{name}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{name}[{index}]") for index, item in enumerate(value)]
    raise ValidationError(f"{name} contains unsupported value type {type(value).__name__}")


def _deep_freeze(value: Any) -> Any:
    """Defensively copy JSON-shaped data into recursively immutable containers."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _canonical_json(value: Any) -> str:
    """Serialize a supported value deterministically without permitting NaN."""

    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _canonical_digest(value: Any) -> str:
    """Return a stable SHA-256 digest for a supported structured value."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
