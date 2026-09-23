"""Sealed process-local authority for independently replayed conformance cases."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import hmac
import secrets
from types import MappingProxyType
from typing import Any

from .errors import ValidationError
from .validation import (
    _canonical_json,
    _require_exact_keys,
    _require_mapping,
    _require_sequence,
    _require_text,
)


class AuthenticatedConformanceRun:
    """Immutable result minted by exactly one sealed conformance runner."""

    __slots__ = ("_owner", "_cases", "_nonce", "_signature", "_sealed")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ValidationError("conformance runs can only be minted by a sealed runner")

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("authenticated conformance run is immutable")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("authenticated conformance run is immutable")

    @property
    def cases(self) -> tuple[Mapping[str, Any], ...]:
        return self._cases

    def __copy__(self) -> "AuthenticatedConformanceRun":
        raise ValidationError("authenticated conformance runs cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> "AuthenticatedConformanceRun":
        raise ValidationError("authenticated conformance runs cannot be copied")


class ConformanceRunner:
    """Seal one evaluator object and exact ordered case contract.

    The evaluator is captured at construction rather than looked up by name on
    each run. A later replacement of a compatibility module attribute cannot
    redirect this runner to receipt-supplied records.
    """

    __slots__ = ("_expected", "_evaluator", "_secret", "_issued", "_sealed")

    def __init__(
        self,
        expected_cases: Mapping[str, Any],
        evaluator: Callable[[], Any],
    ) -> None:
        expected = _require_mapping(expected_cases, "conformance expected_cases")
        if not expected:
            raise ValidationError("conformance expected_cases must be nonempty")
        if not callable(evaluator):
            raise ValidationError("conformance evaluator must be callable")
        normalized: dict[str, tuple[str, ...]] = {}
        for case_id, raw_checks in expected.items():
            identifier = _require_text(case_id, "conformance case_id", identifier=True)
            checks = tuple(_require_sequence(raw_checks, f"conformance checks {identifier}"))
            if not checks:
                raise ValidationError("conformance expected checks must be nonempty")
            checked = tuple(
                _require_text(check, f"conformance check {identifier}", identifier=True)
                for check in checks
            )
            if len(set(checked)) != len(checked):
                raise ValidationError("conformance expected checks must be unique")
            normalized[identifier] = checked
        object.__setattr__(self, "_expected", MappingProxyType(normalized))
        object.__setattr__(self, "_evaluator", evaluator)
        object.__setattr__(self, "_secret", secrets.token_bytes(32))
        object.__setattr__(self, "_issued", {})
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("conformance runner authority is sealed")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("conformance runner authority is sealed")

    def _normalize(self, value: Any) -> tuple[Mapping[str, Any], ...]:
        records = tuple(_require_sequence(value, "conformance evaluator result"))
        if len(records) != len(self._expected):
            raise ValidationError("conformance evaluator returned an incomplete case set")
        normalized = []
        for index, raw_record in enumerate(records):
            record = _require_mapping(raw_record, f"conformance cases[{index}]")
            _require_exact_keys(
                record,
                {"case_id", "disposition", "checks"},
                {"case_id", "disposition", "checks"},
                f"conformance cases[{index}]",
            )
            case_id = _require_text(
                record["case_id"], f"conformance cases[{index}].case_id", identifier=True
            )
            disposition = _require_text(
                record["disposition"], f"conformance cases[{index}].disposition", identifier=True
            )
            checks = tuple(
                _require_text(
                    check,
                    f"conformance cases[{index}].checks",
                    identifier=True,
                )
                for check in _require_sequence(
                    record["checks"], f"conformance cases[{index}].checks"
                )
            )
            normalized.append(
                MappingProxyType(
                    {
                        "case_id": case_id,
                        "disposition": disposition,
                        "checks": checks,
                    }
                )
            )
        if tuple(record["case_id"] for record in normalized) != tuple(self._expected):
            raise ValidationError("conformance cases are missing, duplicated, or reordered")
        for record in normalized:
            if record["disposition"] != "pass":
                raise ValidationError(f"conformance case {record['case_id']} did not pass")
            if record["checks"] != self._expected[record["case_id"]]:
                raise ValidationError(f"conformance checks changed for {record['case_id']}")
        return tuple(normalized)

    @staticmethod
    def _payload(cases: tuple[Mapping[str, Any], ...]) -> list[dict[str, Any]]:
        return [
            {
                "case_id": record["case_id"],
                "disposition": record["disposition"],
                "checks": list(record["checks"]),
            }
            for record in cases
        ]

    def _signature(self, cases: tuple[Mapping[str, Any], ...], nonce: str) -> str:
        return hmac.new(
            self._secret,
            _canonical_json({"nonce": nonce, "cases": self._payload(cases)}).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def run(self) -> AuthenticatedConformanceRun:
        cases = self._normalize(self._evaluator())
        nonce = secrets.token_hex(32)
        result = object.__new__(AuthenticatedConformanceRun)
        object.__setattr__(result, "_owner", self)
        object.__setattr__(result, "_cases", cases)
        object.__setattr__(result, "_nonce", nonce)
        object.__setattr__(result, "_signature", self._signature(cases, nonce))
        object.__setattr__(result, "_sealed", True)
        self._issued[nonce] = result
        return result

    def require(
        self, value: AuthenticatedConformanceRun
    ) -> tuple[Mapping[str, Any], ...]:
        if type(value) is not AuthenticatedConformanceRun or getattr(value, "_owner", None) is not self:
            raise ValidationError("conformance run is not authenticated by this runner")
        nonce = getattr(value, "_nonce", None)
        cases = getattr(value, "_cases", None)
        signature = getattr(value, "_signature", None)
        if (
            type(nonce) is not str
            or self._issued.get(nonce) is not value
            or type(cases) is not tuple
            or type(signature) is not str
        ):
            raise ValidationError("conformance run is not authenticated by this runner")
        try:
            expected_signature = self._signature(cases, nonce)
        except (KeyError, TypeError, ValidationError):
            raise ValidationError("conformance run is not authenticated by this runner") from None
        if not hmac.compare_digest(signature, expected_signature):
            raise ValidationError("conformance run is not authenticated by this runner")
        return value.cases
