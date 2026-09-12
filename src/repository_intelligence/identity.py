"""Source/materialization/configuration/generation identity records.

This module owns the identity representation and process-local signing
operation without depending on any project runtime module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import re
from typing import Any, Optional


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


def _validate_binding_text(value: Any, name: str) -> str:
    """Accept a nonblank binding dimension constrained to an identifier."""

    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{name} is not a valid identifier")
    return value


def _canonical_binding_json(value: Any) -> str:
    """Serialize the four binding dimensions deterministically."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@dataclass(frozen=True)
class IdentityBinding:
    """Untrusted source/materialization/configuration/generation identity."""

    source_id: str
    materialization_id: str
    configuration_id: str
    generation_id: str

    def __post_init__(self) -> None:
        _validate_binding_text(self.source_id, "source_id")
        _validate_binding_text(self.materialization_id, "materialization_id")
        _validate_binding_text(self.configuration_id, "configuration_id")
        _validate_binding_text(self.generation_id, "generation_id")

    def as_dict(self) -> dict[str, str]:
        """Return a fresh, non-authoritative serialized view of the binding."""

        return {
            "source_id": self.source_id,
            "materialization_id": self.materialization_id,
            "configuration_id": self.configuration_id,
            "generation_id": self.generation_id,
        }


@dataclass(frozen=True)
class AuthenticatedBinding(IdentityBinding):
    """Harness-authenticated identity accepted for exact evidence joins."""

    _authority: Optional[Any] = field(default=None, repr=False, compare=False)
    _signature: str = field(default="", repr=False, compare=False)

    def is_authenticated(self) -> bool:
        """Return whether the private issuer signature still validates."""

        if self._authority is None or type(self._signature) is not str:
            return False
        expected = hmac.new(
            self._authority.secret,
            _canonical_binding_json(self.as_dict()).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(self._signature, expected)


def _new_binding(authority: Any, **values: str) -> AuthenticatedBinding:
    """Issue one signed binding from a harness authority."""

    binding = AuthenticatedBinding(
        values["source_id"],
        values["materialization_id"],
        values["configuration_id"],
        values["generation_id"],
        _authority=authority,
    )
    object.__setattr__(
        binding,
        "_signature",
        hmac.new(
            authority.secret,
            _canonical_binding_json(binding.as_dict()).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest(),
    )
    return binding
