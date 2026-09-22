"""Finite immutable executable scope authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .authority import _binding_tuple, _require_authenticated_binding
from .errors import ValidationError
from .identity import AuthenticatedBinding, IdentityBinding
from .validation import _canonical_digest, _deep_freeze, _json_value, _require_exact_keys, _require_mapping, _require_sequence, _require_text


@dataclass(frozen=True)
class ScopeGrant:
    """Finite immutable D authority compiled from an authored concrete set.

    ``operations`` and ``preconditions`` are recursively frozen defensive
    copies.  A caller can mutate its original request or machine suggestions
    after acceptance without widening this grant.
    """

    grant_id: str
    source_binding: AuthenticatedBinding
    configuration_id: str
    registry_id: str
    resolution_id: str
    operations: tuple[Mapping[str, Any], ...]
    preconditions: Mapping[str, Any]
    destinations: tuple[str, ...]
    _digest: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("grant_id", "configuration_id", "registry_id", "resolution_id"):
            _require_text(getattr(self, name), name, identifier=True)
        _require_authenticated_binding(self.source_binding, "scope source_binding")
        if self.configuration_id != self.source_binding.configuration_id:
            raise ValidationError("scope configuration does not match source binding")
        if not isinstance(self.operations, tuple) or len(self.operations) == 0:
            raise ValidationError("ScopeGrant operations must be a finite nonempty tuple")
        frozen_operations = []
        for index, operation in enumerate(self.operations):
            record = _require_mapping(operation, f"operations[{index}]")
            if "operation" not in record or "path" not in record:
                raise ValidationError("each ScopeGrant operation needs operation and path")
            op = _require_text(record["operation"], f"operations[{index}].operation", identifier=True)
            path = _require_text(record["path"], f"operations[{index}].path")
            if op not in {"modify", "create", "delete", "rename"}:
                raise ValidationError("ScopeGrant operation kind is unsupported")
            if any(marker in path for marker in ("*", "?", "[", "]")):
                raise ValidationError("ScopeGrant path cannot be a live wildcard")
            frozen_operations.append(_deep_freeze(_json_value(record, f"operations[{index}]")))
        frozen_preconditions = _deep_freeze(_json_value(self.preconditions, "preconditions"))
        if not isinstance(frozen_preconditions, Mapping):
            raise ValidationError("preconditions must remain a mapping")
        destinations = tuple(self.destinations)
        if any(type(value) is not str or not value.strip() for value in destinations):
            raise ValidationError("destinations must be immutable nonblank text")
        object.__setattr__(self, "operations", tuple(frozen_operations))
        object.__setattr__(self, "preconditions", frozen_preconditions)
        object.__setattr__(self, "destinations", destinations)
        calculated_digest = _canonical_digest(self.as_dict())
        if self._digest and self._digest != calculated_digest:
            raise ValidationError("scope digest does not match immutable grant contents")
        object.__setattr__(self, "_digest", calculated_digest)

    @classmethod
    def accept(cls, raw: Mapping[str, Any], binding: AuthenticatedBinding) -> "ScopeGrant":
        """Defensively canonicalize one finite, authored grant request."""

        request = _require_mapping(raw, "scope grant")
        _require_exact_keys(
            request,
            {
                "grant_id",
                "source_binding",
                "configuration_id",
                "registry_id",
                "resolution_id",
                "operations",
                "preconditions",
                "destinations",
            },
            {
                "grant_id",
                "source_binding",
                "configuration_id",
                "registry_id",
                "resolution_id",
                "operations",
                "preconditions",
                "destinations",
            },
            "scope grant",
        )
        expected = _require_authenticated_binding(binding, "expected scope binding")
        declared = request["source_binding"]
        if not isinstance(declared, IdentityBinding) or _binding_tuple(declared) != _binding_tuple(expected):
            raise ValidationError("scope grant source binding mismatch")
        operations = _require_sequence(request["operations"], "scope operations")
        destinations = _require_sequence(request["destinations"], "scope destinations")
        return cls(
            grant_id=_require_text(request["grant_id"], "grant_id", identifier=True),
            source_binding=expected,
            configuration_id=_require_text(
                request["configuration_id"], "configuration_id", identifier=True
            ),
            registry_id=_require_text(request["registry_id"], "registry_id", identifier=True),
            resolution_id=_require_text(request["resolution_id"], "resolution_id", identifier=True),
            operations=tuple(operations),
            preconditions=_require_mapping(request["preconditions"], "preconditions"),
            destinations=tuple(destinations),
        )

    @property
    def digest(self) -> str:
        """Return the digest of the immutable accepted grant."""

        return self._digest

    def as_dict(self) -> dict[str, Any]:
        """Return a fresh non-authoritative serialization of the finite grant."""

        return {
            "grant_id": self.grant_id,
            "source_binding": self.source_binding.as_dict(),
            "configuration_id": self.configuration_id,
            "registry_id": self.registry_id,
            "resolution_id": self.resolution_id,
            "operations": list(self.operations),
            "preconditions": self.preconditions,
            "destinations": list(self.destinations),
        }
