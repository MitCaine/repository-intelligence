"""Provider-neutral authenticated security observation records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hmac
from pathlib import PurePosixPath
import re
from typing import Any, Optional

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

_WRITABLE_ROOT_NAMESPACES = frozenset({"working-tree", "scratch", "cache", "logs", "temp"})
_BROAD_ROOT_TOKENS = frozenset({
    "all", "any", "current", "discover", "discovered", "discovery", "everything",
    "files", "head", "home", "host", "latest", "later", "root", "whatever", "workspace",
})


def _concrete_writable_roots(value: Any, *, nonempty: bool) -> tuple[str, ...]:
    if type(value) not in {tuple, list} or (nonempty and not value):
        raise ValidationError("writable roots must be a finite concrete sequence")
    roots: list[str] = []
    for index, raw in enumerate(value):
        path = _require_text(raw, f"writable roots[{index}]")
        parsed = PurePosixPath(path)
        parts = parsed.parts
        if (
            path in {".", ".."}
            or path.startswith(("/", "~"))
            or path.endswith("/")
            or parsed.as_posix() != path
            or any(part in {"", ".", ".."} for part in parsed.parts)
            or any(marker in path for marker in ("*", "?", "[", "]", "\\", ":", "$", "%"))
            or any(ord(char) < 32 or ord(char) == 127 for char in path)
            or len(parts) < 2
            or parts[0] not in _WRITABLE_ROOT_NAMESPACES
            or any(set(re.split(r"[^a-z0-9]+", part.lower())) & _BROAD_ROOT_TOKENS for part in parts)
        ):
            raise ValidationError("writable root must be normalized, concrete and anchor-relative")
        if any(path == other or path.startswith(other + "/") or other.startswith(path + "/") for other in roots):
            raise ValidationError("writable roots cannot duplicate or overlap")
        roots.append(path)
    return tuple(roots)


@dataclass(frozen=True)
class WritableRootsPolicy:
    """Exact finite writable roots within one independently identified sandbox anchor."""

    policy_id: str
    binding: AuthenticatedBinding
    anchor_id: str
    roots: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.policy_id, "writable roots policy_id", identifier=True)
        _require_authenticated_binding(self.binding, "writable roots policy binding")
        _require_text(self.anchor_id, "writable roots anchor_id", identifier=True)
        object.__setattr__(self, "roots", _concrete_writable_roots(self.roots, nonempty=True))


@dataclass(frozen=True)
class WritableRootsObservation:
    """Harness-retained observed root set, never a candidate-supplied claim."""

    observation_id: str
    binding: AuthenticatedBinding
    anchor_id: str
    roots: tuple[str, ...]
    _authority: Optional[_Authority] = field(default=None, repr=False, compare=False)
    _issuer: Any = field(default=None, repr=False, compare=False)
    _signature: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_text(self.observation_id, "writable roots observation_id", identifier=True)
        _require_authenticated_binding(self.binding, "writable roots observation binding")
        _require_text(self.anchor_id, "writable roots observation anchor_id", identifier=True)
        object.__setattr__(self, "roots", _concrete_writable_roots(self.roots, nonempty=False))

    def is_authenticated(self) -> bool:
        if (
            self._authority is None
            or self.binding._authority is not self._authority
            or self._issuer is None
            or getattr(self._issuer, "_authority", None) is not self._authority
            or getattr(self._issuer, "_writable_roots_issued", {}).get(self.observation_id) is not self
        ):
            return False
        expected = _sign(self._authority, {
            "observation_id": self.observation_id,
            "binding": self.binding.as_dict(),
            "anchor_id": self.anchor_id,
            "roots": list(self.roots),
        })
        return hmac.compare_digest(self._signature, expected)


@dataclass(frozen=True)
class WritableRootsEvaluation:
    status: str
    reasons: tuple[str, ...]
    observation_id: str

    def __post_init__(self) -> None:
        if self.status not in {"pass", "fail"} or (self.status == "pass") != (not self.reasons):
            raise ValidationError("writable roots evaluation status is inconsistent")
        if any(reason not in {"missing:roots", "conflict:roots"} for reason in self.reasons):
            raise ValidationError("writable roots evaluation reason is unsupported")
        _require_text(self.observation_id, "writable roots evaluation observation_id", identifier=True)


def evaluate_writable_roots(
    policy: WritableRootsPolicy,
    observation: WritableRootsObservation,
    expected_binding: AuthenticatedBinding,
) -> WritableRootsEvaluation:
    """Require exact independently issued roots; categorical security is insufficient."""

    if type(policy) is not WritableRootsPolicy:
        raise ValidationError("writable roots policy has the wrong type")
    if type(observation) is not WritableRootsObservation or not observation.is_authenticated():
        raise ValidationError("writable roots observation lacks independent issuer provenance")
    expected = _require_authenticated_binding(expected_binding, "writable roots expected binding")
    if (
        policy.binding._authority is not expected._authority
        or observation.binding._authority is not expected._authority
        or _binding_tuple(policy.binding) != _binding_tuple(expected)
        or _binding_tuple(observation.binding) != _binding_tuple(expected)
    ):
        raise ValidationError("writable roots source binding mismatch")
    if policy.anchor_id != observation.anchor_id:
        raise ValidationError("writable roots sandbox anchor mismatch")
    reasons = () if set(policy.roots) == set(observation.roots) else (("missing:roots",) if not observation.roots else ("conflict:roots",))
    return WritableRootsEvaluation("pass" if not reasons else "fail", reasons, observation.observation_id)


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
class AttemptCleanupObservation:
    """One issuer-retained cleanup observation for an exact terminal attempt."""

    observation_id: str
    attempt_id: str
    binding: AuthenticatedBinding
    observed_at: int
    disposition: str
    _authority: Optional[_Authority] = field(default=None, repr=False, compare=False)
    _issuer: Any = field(default=None, repr=False, compare=False)
    _signature: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_text(self.observation_id, "cleanup observation_id", identifier=True)
        _require_text(self.attempt_id, "cleanup attempt_id", identifier=True)
        _require_authenticated_binding(self.binding, "cleanup binding")
        if type(self.observed_at) is not int or self.observed_at < 0:
            raise ValidationError("cleanup observed_at must be a nonnegative exact integer")
        if self.disposition not in {"clean", "residue", "unknown"}:
            raise ValidationError("cleanup disposition is unsupported")

    def is_authenticated(self) -> bool:
        if (
            self._authority is None
            or self.binding._authority is not self._authority
            or self._issuer is None
            or getattr(self._issuer, "_authority", None) is not self._authority
            or getattr(self._issuer, "_cleanup_issued", {}).get(self.observation_id) is not self
        ):
            return False
        expected = _sign(self._authority, {
            "observation_id": self.observation_id,
            "attempt_id": self.attempt_id,
            "binding": self.binding.as_dict(),
            "observed_at": self.observed_at,
            "disposition": self.disposition,
        })
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
