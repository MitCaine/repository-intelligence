"""Finite immutable executable scope authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath
import re
from typing import Any

from .authority import _binding_tuple, _require_authenticated_binding
from .errors import ValidationError
from .identity import AuthenticatedBinding
from .validation import _canonical_digest, _deep_freeze, _json_value, _require_exact_keys, _require_mapping, _require_sequence, _require_text


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MUTABLE_SELECTOR_TOKENS = {
    "all",
    "any",
    "current",
    "discover",
    "discovered",
    "discovery",
    "head",
    "latest",
    "later",
    "whatever",
}


def _concrete_relative_path(value: Any, name: str) -> str:
    path = _require_text(value, name)
    if (
        path in {".", ".."}
        or path.startswith("/")
        or path.endswith("/")
        or "\\" in path
        or ":" in path
        or any(marker in path for marker in ("*", "?", "[", "]"))
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    ):
        raise ValidationError(f"{name} must be a concrete normalized POSIX-relative path")
    parsed = PurePosixPath(path)
    if parsed.as_posix() != path or any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValidationError(f"{name} must be a concrete normalized POSIX-relative path")
    return path


def _concrete_identifier(value: Any, name: str) -> str:
    identifier = _require_text(value, name, identifier=True)
    tokens = set(re.split(r"[^a-z0-9]+", identifier.lower()))
    if tokens & _MUTABLE_SELECTOR_TOKENS:
        raise ValidationError(f"{name} must identify a concrete immutable selection")
    return identifier


def _finite_preconditions(value: Any) -> Mapping[str, Any]:
    preconditions = _require_mapping(value, "preconditions")
    allowed = {"branch", "required_paths", "path_sha256", "package_manager"}
    _require_exact_keys(preconditions, allowed, set(), "preconditions")
    accepted: dict[str, Any] = {}
    if "branch" in preconditions:
        accepted["branch"] = _concrete_identifier(preconditions["branch"], "preconditions.branch")
    if "package_manager" in preconditions:
        accepted["package_manager"] = _concrete_identifier(
            preconditions["package_manager"], "preconditions.package_manager"
        )
    if "required_paths" in preconditions:
        raw_paths = _require_sequence(preconditions["required_paths"], "preconditions.required_paths")
        if not raw_paths:
            raise ValidationError("preconditions.required_paths must be finite and nonempty")
        paths = tuple(
            _concrete_relative_path(path, f"preconditions.required_paths[{index}]")
            for index, path in enumerate(raw_paths)
        )
        if len(set(paths)) != len(paths):
            raise ValidationError("preconditions.required_paths cannot contain duplicates")
        accepted["required_paths"] = paths
    if "path_sha256" in preconditions:
        raw_digests = _require_mapping(preconditions["path_sha256"], "preconditions.path_sha256")
        if not raw_digests:
            raise ValidationError("preconditions.path_sha256 must be finite and nonempty")
        digests: dict[str, str] = {}
        for raw_path, raw_digest in raw_digests.items():
            path = _concrete_relative_path(raw_path, "preconditions.path_sha256 path")
            digest = _require_text(raw_digest, f"preconditions.path_sha256[{path}]")
            if not _SHA256.fullmatch(digest):
                raise ValidationError("preconditions.path_sha256 values must be lowercase SHA-256 digests")
            digests[path] = digest
        accepted["path_sha256"] = digests
    return _deep_freeze(accepted)


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
        seen_paths: set[str] = set()
        for index, operation in enumerate(self.operations):
            record = _require_mapping(operation, f"operations[{index}]")
            _require_exact_keys(
                record,
                {"operation", "path"},
                {"operation", "path"},
                f"operations[{index}]",
            )
            op = _require_text(record["operation"], f"operations[{index}].operation", identifier=True)
            path = _concrete_relative_path(record["path"], f"operations[{index}].path")
            if op not in {"modify", "create", "delete", "rename"}:
                raise ValidationError("ScopeGrant operation kind is unsupported")
            if path in seen_paths:
                raise ValidationError("ScopeGrant operation paths cannot contain duplicates")
            seen_paths.add(path)
            frozen_operations.append(_deep_freeze({"operation": op, "path": path}))
        frozen_preconditions = _finite_preconditions(self.preconditions)
        destinations = tuple(self.destinations)
        if destinations != ("working-tree",):
            raise ValidationError("destinations must be exactly the singleton working-tree boundary")
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
        declared = _require_authenticated_binding(request["source_binding"], "declared scope binding")
        if (
            _binding_tuple(declared) != _binding_tuple(expected)
            or declared._authority is not expected._authority
        ):
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
