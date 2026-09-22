"""Provider-neutral authenticated security observation records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hmac
from typing import Optional

from .authority import _Authority, _require_authenticated_binding, _sign
from .errors import ValidationError
from .identity import AuthenticatedBinding
from .validation import _deep_freeze, _json_value, _require_mapping, _require_text


REQUIRED_SECURITY_OBSERVATIONS = (
    "network",
    "credentials",
    "writable_roots",
    "process_limits",
    "resource_limits",
    "checkout",
    "host_config",
    "cleanup",
)


@dataclass(frozen=True)
class SecurityObservation:
    """Harness-issued observation of required security and cleanup variables."""

    observation_id: str
    context_id: str
    binding: AuthenticatedBinding
    observed: Mapping[str, str]
    _authority: Optional[_Authority] = field(default=None, repr=False, compare=False)
    _signature: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_text(self.observation_id, "security observation_id", identifier=True)
        _require_text(self.context_id, "security context_id", identifier=True)
        _require_authenticated_binding(self.binding, "security observation binding")
        observed = _require_mapping(self.observed, "security observed")
        for key, value in observed.items():
            if key not in REQUIRED_SECURITY_OBSERVATIONS:
                raise ValidationError(f"unknown security observation {key}")
            _require_text(value, f"security observed {key}", identifier=True)
        object.__setattr__(self, "observed", _deep_freeze(_json_value(observed, "security observed")))

    def is_authenticated(self) -> bool:
        """Return whether the observation is bound to its harness context."""

        if self._authority is None or self.binding._authority is not self._authority:
            return False
        expected = _sign(
            self._authority,
            {
                "observation_id": self.observation_id,
                "context_id": self.context_id,
                "binding": self.binding.as_dict(),
                "observed": self.observed,
            },
        )
        return hmac.compare_digest(self._signature, expected)


@dataclass(frozen=True)
class SecurityEvaluation:
    """Derived security gate result and redacted reasons."""

    status: str
    reasons: tuple[str, ...]
    observation_id: str
