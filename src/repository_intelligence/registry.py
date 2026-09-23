"""Finite provider-neutral identity declarations and references for registries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from types import MappingProxyType
from typing import Any

from .errors import ValidationError
from .validation import _require_exact_keys, _require_mapping, _require_sequence, _require_text


_CONCRETE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@#-]*\Z")
_UNRESOLVED_TOKENS = frozenset({
    "all", "any", "comment", "current", "discover", "discovered",
    "discovery", "head", "issue", "last", "latest", "later", "next",
    "unknown", "whatever",
})


def _concrete(value: Any, name: str) -> str:
    text = _require_text(value, name)
    if (
        not _CONCRETE_RE.fullmatch(text)
        or set(re.split(r"[^a-z0-9]+", text.lower())) & _UNRESOLVED_TOKENS
        or ".." in text
        or "//" in text
    ):
        raise ValidationError(f"{name} must be a concrete closed identifier")
    return text


class RegistryIdentityCatalog:
    """Immutable, independently authored role/value bindings for one registry."""

    __slots__ = ("_declarations", "_by_id", "_sealed")

    def __init__(self, declarations: Sequence[Mapping[str, Any]]) -> None:
        raw = _require_sequence(declarations, "registry identity declarations")
        if not raw:
            raise ValidationError("registry identity declarations must be nonempty")
        accepted = []
        by_id: dict[str, Mapping[str, str]] = {}
        values: set[tuple[str, str]] = set()
        for index, item in enumerate(raw):
            record = _require_mapping(item, f"registry declaration[{index}]")
            _require_exact_keys(
                record,
                {"identity_id", "kind", "value"},
                {"identity_id", "kind", "value"},
                f"registry declaration[{index}]",
            )
            identity_id = _concrete(record["identity_id"], "identity_id")
            kind = _concrete(record["kind"], "identity kind")
            value = _concrete(record["value"], "identity value")
            if identity_id in by_id or (kind, value) in values:
                raise ValidationError("registry identity declarations contain duplicate authority")
            frozen = MappingProxyType(
                {"identity_id": identity_id, "kind": kind, "value": value}
            )
            accepted.append(frozen)
            by_id[identity_id] = frozen
            values.add((kind, value))
        object.__setattr__(self, "_declarations", tuple(accepted))
        object.__setattr__(self, "_by_id", MappingProxyType(by_id))
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("registry identity catalog is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("registry identity catalog is immutable")

    def require_reference(self, value: Mapping[str, Any]) -> Mapping[str, str]:
        reference = _require_mapping(value, "registry identity reference")
        _require_exact_keys(
            reference,
            {"identity_id", "expected_kind", "value"},
            {"identity_id", "expected_kind", "value"},
            "registry identity reference",
        )
        identity_id = _concrete(reference["identity_id"], "reference.identity_id")
        kind = _concrete(reference["expected_kind"], "reference.expected_kind")
        declared_value = _concrete(reference["value"], "reference.value")
        declared = self._by_id.get(identity_id)
        if declared is None or declared["kind"] != kind or declared["value"] != declared_value:
            raise ValidationError("registry identity reference does not match authored declaration")
        return declared

    def as_dict(self) -> list[dict[str, str]]:
        """Return a detached non-authoritative serialization."""
        return [dict(item) for item in self._declarations]
