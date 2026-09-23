"""Provider-neutral authenticated security observation records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hmac
from typing import Optional

from .authority import _Authority, _binding_tuple, _require_authenticated_binding, _sign
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

_SAFE_SECURITY_DISPOSITIONS = {
    "network": frozenset({"denied", "blocked"}),
    "credentials": frozenset({"dropped", "absent"}),
    "writable_roots": frozenset({"bounded", "scoped"}),
    "process_limits": frozenset({"enforced", "bounded"}),
    "resource_limits": frozenset({"enforced", "bounded"}),
    "checkout": frozenset({"unchanged", "read-only"}),
    "host_config": frozenset({"isolated", "separate"}),
    "cleanup": frozenset({"clean", "complete"}),
}
_UNSAFE_SECURITY_DISPOSITIONS = {
    "network": frozenset({"allowed"}),
    "credentials": frozenset({"present"}),
    "writable_roots": frozenset({"unbounded"}),
    "process_limits": frozenset({"unenforced"}),
    "resource_limits": frozenset({"unenforced"}),
    "checkout": frozenset({"modified"}),
    "host_config": frozenset({"shared"}),
    "cleanup": frozenset({"residue"}),
}


@dataclass(frozen=True)
class SecurityPolicy:
    """Declared security requirements, separate from observed sandbox state."""

    policy_id: str
    expected: Mapping[str, str]
    required: tuple[str, ...] = REQUIRED_SECURITY_OBSERVATIONS
    binding: Optional[AuthenticatedBinding] = None

    def __post_init__(self) -> None:
        _require_text(self.policy_id, "policy_id", identifier=True)
        expected = _require_mapping(self.expected, "security policy expected")
        if set(expected) != set(REQUIRED_SECURITY_OBSERVATIONS):
            raise ValidationError("security policy fields must match the closed observation set")
        required = tuple(self.required)
        if required != REQUIRED_SECURITY_OBSERVATIONS:
            raise ValidationError("security policy must retain all required observations")
        object.__setattr__(self, "required", REQUIRED_SECURITY_OBSERVATIONS)
        for name in REQUIRED_SECURITY_OBSERVATIONS:
            if name not in expected:
                raise ValidationError(f"security policy omits {name}")
            value = _require_text(expected[name], f"security policy {name}", identifier=True)
            if value not in _SAFE_SECURITY_DISPOSITIONS[name]:
                raise ValidationError(f"security policy {name} disposition is unsafe or unknown")
        object.__setattr__(self, "expected", _deep_freeze(_json_value(expected, "security expected")))
        if self.binding is not None:
            _require_authenticated_binding(self.binding, "security policy binding")


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
            disposition = _require_text(value, f"security observed {key}", identifier=True)
            allowed = _SAFE_SECURITY_DISPOSITIONS[key] | _UNSAFE_SECURITY_DISPOSITIONS[key]
            if disposition not in allowed:
                raise ValidationError(f"security observed {key} disposition is unknown")
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

    def __post_init__(self) -> None:
        if self.status not in {"pass", "fail"}:
            raise ValidationError("security evaluation status is unsupported")
        _require_text(self.observation_id, "security evaluation observation_id", identifier=True)
        if not isinstance(self.reasons, tuple):
            raise ValidationError("security evaluation reasons must be an immutable tuple")
        for reason in self.reasons:
            if type(reason) is not str or ":" not in reason:
                raise ValidationError("security evaluation reason is malformed")
            kind, name = reason.split(":", 1)
            if kind not in {"missing", "conflict"} or name not in REQUIRED_SECURITY_OBSERVATIONS:
                raise ValidationError("security evaluation reason is unsupported")
        if (self.status == "pass") != (not self.reasons):
            raise ValidationError("security evaluation status and reasons are inconsistent")


def evaluate_security(
    policy: SecurityPolicy,
    observation: SecurityObservation,
    expected_binding: AuthenticatedBinding,
) -> SecurityEvaluation:
    """Evaluate observed state; candidate claims are not consulted or accepted."""

    if not isinstance(policy, SecurityPolicy):
        raise ValidationError("security policy has the wrong type")
    if not isinstance(observation, SecurityObservation) or not observation.is_authenticated():
        raise ValidationError("security observation lacks independent harness provenance")
    _require_authenticated_binding(expected_binding, "expected_binding")
    if observation.binding._authority is not expected_binding._authority:
        raise ValidationError("security observation and expected binding have different issuers")
    if _binding_tuple(observation.binding) != _binding_tuple(expected_binding):
        raise ValidationError("security observation binding mismatch")
    if policy.binding is not None:
        if policy.binding._authority is not expected_binding._authority or _binding_tuple(
            policy.binding
        ) != _binding_tuple(expected_binding):
            raise ValidationError("security policy binding mismatch")
    reasons: list[str] = []
    for name in REQUIRED_SECURITY_OBSERVATIONS:
        if name not in observation.observed:
            reasons.append(f"missing:{name}")
        elif observation.observed[name] != policy.expected[name]:
            reasons.append(f"conflict:{name}")
    return SecurityEvaluation(
        status="pass" if not reasons else "fail",
        reasons=tuple(reasons),
        observation_id=observation.observation_id,
    )
