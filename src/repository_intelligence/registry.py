"""Finite provider-neutral identity declarations and references for registries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from types import MappingProxyType
from typing import Any

from .errors import ValidationError
from .validation import _require_exact_keys, _require_mapping, _require_sequence, _require_text, _typed_equal


_CONCRETE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@#-]*\Z")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
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


_SOURCE_FIELDS = (
    "source_id", "repository", "revision", "language",
    "source_state_mode", "configuration_id",
)
_CELL_FIELDS = (*_SOURCE_FIELDS, "role_id", "operation_id", "disposition")


class SourceMatrixAuthority:
    """Immutable authored source tuples and complete planned matrix geometry."""

    __slots__ = ("_sources", "_roles", "_operations", "_cells", "_sealed")

    def __init__(
        self,
        source_pins: Sequence[Mapping[str, Any]],
        role_ids: Sequence[str],
        operation_ids: Sequence[str],
    ) -> None:
        pins = _require_sequence(source_pins, "source pins")
        if not pins:
            raise ValidationError("source pins must be nonempty")
        sources = []
        source_ids: set[str] = set()
        source_values: set[tuple[str, ...]] = set()
        for index, raw in enumerate(pins):
            source = _require_mapping(raw, f"source pin[{index}]")
            _require_exact_keys(source, _SOURCE_FIELDS, _SOURCE_FIELDS, f"source pin[{index}]")
            normalized = {
                key: _concrete(source[key], f"source pin[{index}].{key}")
                for key in _SOURCE_FIELDS
            }
            if not _COMMIT_RE.fullmatch(normalized["revision"]):
                raise ValidationError("source revision must be an exact lowercase commit SHA")
            source_id = normalized["source_id"]
            value = tuple(normalized[key] for key in (
                "repository", "revision", "language", "source_state_mode", "configuration_id"
            ))
            if source_id in source_ids or value in source_values:
                raise ValidationError("source pins contain duplicate or aliased authority")
            source_ids.add(source_id)
            source_values.add(value)
            sources.append(MappingProxyType(normalized))
        roles = self._identifiers(role_ids, "role_ids")
        operations = self._identifiers(operation_ids, "operation_ids")
        if len(sources) * len(roles) * len(operations) > 10000:
            raise ValidationError("source matrix authority exceeds finite cell limit")
        cells = tuple(
            MappingProxyType({
                **source,
                "role_id": role,
                "operation_id": operation,
                "disposition": "not_executed",
            })
            for source in sources
            for role in roles
            for operation in operations
        )
        object.__setattr__(self, "_sources", tuple(sources))
        object.__setattr__(self, "_roles", roles)
        object.__setattr__(self, "_operations", operations)
        object.__setattr__(self, "_cells", cells)
        object.__setattr__(self, "_sealed", True)

    @staticmethod
    def _identifiers(values: Sequence[str], name: str) -> tuple[str, ...]:
        raw = _require_sequence(values, name)
        identifiers = tuple(_concrete(value, name) for value in raw)
        if not identifiers or len(set(identifiers)) != len(identifiers):
            raise ValidationError(f"{name} must be finite, nonempty and unique")
        return identifiers

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("source matrix authority is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("source matrix authority is immutable")

    def as_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "source_pins": [dict(source) for source in self._sources],
            "matrix": [dict(cell) for cell in self._cells],
        }

    def validate(self, value: Mapping[str, Any]) -> None:
        fragment = _require_mapping(value, "source matrix fragment")
        _require_exact_keys(
            fragment, {"source_pins", "matrix"}, {"source_pins", "matrix"},
            "source matrix fragment",
        )
        pins = _require_sequence(fragment["source_pins"], "source matrix pins")
        cells = _require_sequence(fragment["matrix"], "source matrix cells")
        if len(pins) != len(self._sources) or len(cells) != len(self._cells):
            raise ValidationError("source matrix is incomplete or expanded")
        for index, (raw, expected) in enumerate(zip(pins, self._sources)):
            pin = _require_mapping(raw, f"source matrix pin[{index}]")
            _require_exact_keys(pin, _SOURCE_FIELDS, _SOURCE_FIELDS, f"source matrix pin[{index}]")
            if not _typed_equal(pin, expected):
                raise ValidationError("source matrix pin differs from authored source")
        for index, (raw, expected) in enumerate(zip(cells, self._cells)):
            cell = _require_mapping(raw, f"source matrix cell[{index}]")
            _require_exact_keys(cell, _CELL_FIELDS, _CELL_FIELDS, f"source matrix cell[{index}]")
            if not _typed_equal(cell, expected):
                raise ValidationError("source matrix cell differs from authored source or geometry")
