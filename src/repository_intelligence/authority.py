"""Process-local issuance and authenticated-binding support.

This internal module owns the ephemeral harness authority and the generic
operations that consume it without depending on evidence or session records.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from .errors import ValidationError
from .identity import AuthenticatedBinding, IdentityBinding
from .validation import _canonical_json


def _binding_tuple(binding: "IdentityBinding") -> tuple[str, str, str, str]:
    """Return all material identity dimensions in their comparison order."""

    return (
        binding.source_id,
        binding.materialization_id,
        binding.configuration_id,
        binding.generation_id,
    )


class _Authority:
    """Process-local issuer state for harness-issued records."""

    __slots__ = ("harness_id", "secret")

    def __init__(self, harness_id: str) -> None:
        self.harness_id = harness_id
        self.secret = secrets.token_bytes(32)


def _require_authenticated_binding(value: Any, name: str) -> AuthenticatedBinding:
    """Require a valid harness-issued binding rather than a matching mapping."""

    if not isinstance(value, AuthenticatedBinding) or not value.is_authenticated():
        raise ValidationError(f"{name} must be a harness-authenticated binding")
    return value


def _sign(authority: _Authority, value: Any) -> str:
    """Sign a structured record with process-local harness authority."""

    return hmac.new(
        authority.secret,
        _canonical_json(value).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
