"""Authored qualification predicates and execution-evidence assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
import hmac
from typing import Any, Optional, Sequence

from .authority import _Authority, _binding_tuple, _require_authenticated_binding, _sign
from .errors import ValidationError
from .evidence import EvidenceRecord, _require_valid_evidence, validate_evidence
from .identity import AuthenticatedBinding
from .validation import _require_exact_bool, _require_sequence, _require_text


@dataclass(frozen=True)
class ExecutionEvidence:
    """Harness-issued observation of one exact/bounded execution.

    ``status`` is interpreted only with the bound command, test, artifact,
    source, configuration, and independent observation fields.  ``exit_code``
    is retained as one fact and never becomes qualification by itself.
    """

    evidence_id: str
    source_binding: AuthenticatedBinding
    command_id: str
    test_id: str
    artifact_id: str
    status: str
    observed: bool
    complete: bool
    terminal: bool
    evidence_session_id: str
    exit_code: Optional[int] = None
    attempt_id: Optional[str] = None
    _authority: Optional[_Authority] = field(default=None, repr=False, compare=False)
    _issuer: Any = field(default=None, repr=False, compare=False)
    _signature: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "evidence_id",
            "command_id",
            "test_id",
            "artifact_id",
            "evidence_session_id",
        ):
            _require_text(getattr(self, name), f"execution {name}", identifier=True)
        _require_authenticated_binding(self.source_binding, "execution source_binding")
        if self.status not in {
            "passed",
            "failed",
            "skipped",
            "quarantined",
            "filtered",
            "unrun",
            "partial",
            "indeterminate",
            "unavailable",
        }:
            raise ValidationError("execution status is unsupported")
        for name in ("observed", "complete", "terminal"):
            _require_exact_bool(getattr(self, name), f"execution {name}")
        if self.exit_code is not None and (type(self.exit_code) is not int or self.exit_code < 0):
            raise ValidationError("execution exit_code must be a nonnegative integer or null")
        if self.attempt_id is not None:
            _require_text(self.attempt_id, "execution attempt_id", identifier=True)

    def is_authenticated(self) -> bool:
        """Return whether the execution record has a valid harness signature."""

        if (
            self._authority is None
            or self.source_binding._authority is not self._authority
            or self._issuer is None
            or getattr(self._issuer, "_authority", None) is not self._authority
            or getattr(self._issuer, "_execution_issued", {}).get(id(self)) is not self
        ):
            return False
        expected = _sign(
            self._authority,
            {
                "evidence_id": self.evidence_id,
                "source_binding": self.source_binding.as_dict(),
                "command_id": self.command_id,
                "test_id": self.test_id,
                "artifact_id": self.artifact_id,
                "status": self.status,
                "observed": self.observed,
                "complete": self.complete,
                "terminal": self.terminal,
                "evidence_session_id": self.evidence_session_id,
                "exit_code": self.exit_code,
                "attempt_id": self.attempt_id,
            },
        )
        return hmac.compare_digest(self._signature, expected)


@dataclass(frozen=True)
class AuthoredEvidencePredicate:
    """Authored, immutable policy predicate for one required execution."""

    predicate_id: str
    expected_binding: AuthenticatedBinding
    command_id: str
    test_id: str
    artifact_id: str
    allowed_statuses: tuple[str, ...] = ("passed",)
    allowed_exit_codes: tuple[int, ...] = (0,)
    require_complete: bool = True

    def __post_init__(self) -> None:
        _require_text(self.predicate_id, "predicate_id", identifier=True)
        _require_authenticated_binding(self.expected_binding, "predicate expected_binding")
        for name in ("command_id", "test_id", "artifact_id"):
            _require_text(getattr(self, name), f"predicate {name}", identifier=True)
        if not isinstance(self.allowed_statuses, tuple) or not self.allowed_statuses:
            raise ValidationError("predicate allowed_statuses must be a nonempty tuple")
        for status in self.allowed_statuses:
            _require_text(status, "predicate allowed status", identifier=True)
        if (
            not isinstance(self.allowed_exit_codes, tuple)
            or not self.allowed_exit_codes
            or any(type(code) is not int or code < 0 for code in self.allowed_exit_codes)
            or len(self.allowed_exit_codes) != len(set(self.allowed_exit_codes))
        ):
            raise ValidationError("predicate allowed_exit_codes must be unique nonnegative integers")
        _require_exact_bool(self.require_complete, "predicate require_complete")

    def evaluate(
        self,
        evidence: Optional[ExecutionEvidence],
        expected_binding: AuthenticatedBinding,
    ) -> tuple[bool, str]:
        """Evaluate an execution record against every authored binding dimension."""

        if not isinstance(evidence, ExecutionEvidence):
            return False, "not_independent_execution_evidence"
        if not evidence.is_authenticated():
            return False, "unverified_execution_evidence"
        if evidence.source_binding._authority is not expected_binding._authority:
            return False, "different_source_authority"
        if _binding_tuple(evidence.source_binding) != _binding_tuple(expected_binding):
            return False, "wrong_source_binding"
        if self.expected_binding._authority is not expected_binding._authority or _binding_tuple(
            self.expected_binding
        ) != _binding_tuple(expected_binding):
            return False, "wrong_authored_binding"
        if evidence.command_id != self.command_id:
            return False, "wrong_command"
        if evidence.test_id != self.test_id:
            return False, "wrong_test"
        if evidence.artifact_id != self.artifact_id:
            return False, "wrong_artifact"
        if evidence.status not in self.allowed_statuses:
            return False, f"status_{evidence.status}"
        if evidence.exit_code not in self.allowed_exit_codes:
            return False, "exit_code_not_authored"
        if evidence.observed is not True:
            return False, "execution_not_observed"
        if evidence.terminal is not True:
            return False, "execution_not_terminal"
        if self.require_complete is True and evidence.complete is not True:
            return False, "execution_incomplete"
        return True, "authored_predicate_satisfied"


@dataclass(frozen=True)
class QualificationObligation:
    """Retained authored obligation; machine suggestions cannot replace it."""

    obligation_id: str
    predicate: AuthoredEvidencePredicate

    def __post_init__(self) -> None:
        _require_text(self.obligation_id, "obligation_id", identifier=True)
        if not isinstance(self.predicate, AuthoredEvidencePredicate):
            raise ValidationError("obligation predicate must be authored and typed")


@dataclass(frozen=True)
class QualificationAssessment:
    """One explicit interpretation of an authored predicate and available evidence."""

    obligation_id: str
    state: str
    reason: str
    predicate_evaluated: bool


@dataclass(frozen=True)
class QualificationDecision:
    """Derived disposition retaining every authored assessment."""

    disposition: str
    assessments: tuple[QualificationAssessment, ...]
    authored_obligations_retained: bool
    suggestions_ignored_for_authority: bool


class QualificationAuthority:
    """Apply immutable authored predicates to independent execution evidence."""

    def __init__(self, obligations: Sequence[QualificationObligation]) -> None:
        values = _require_sequence(obligations, "qualification obligations")
        normalized = tuple(values)
        if any(not isinstance(value, QualificationObligation) for value in normalized):
            raise ValidationError("qualification obligations must be typed authored records")
        ids = [value.obligation_id for value in normalized]
        if len(ids) != len(set(ids)):
            raise ValidationError("qualification obligation identities must be unique")
        self._obligations = normalized

    @property
    def obligations(self) -> tuple[QualificationObligation, ...]:
        """Return the retained immutable authored set."""

        return self._obligations

    def assess(
        self,
        evidence: Sequence[Any],
        expected_binding: AuthenticatedBinding,
        *,
        machine_suggestions: Sequence[Any] = (),
    ) -> QualificationDecision:
        """Evaluate every authored predicate; suggestions never satisfy one."""

        _require_authenticated_binding(expected_binding, "qualification expected_binding")
        observed = tuple(evidence)
        # The argument is deliberately read only for API clarity.  It cannot
        # alter the authored obligation set or be used as evidence.
        _require_sequence(machine_suggestions, "machine_suggestions")
        assessments: list[QualificationAssessment] = []
        for obligation in self._obligations:
            typed = [item for item in observed if isinstance(item, ExecutionEvidence)]
            claimed = [
                item
                for item in typed
                if item.command_id == obligation.predicate.command_id
                and item.test_id == obligation.predicate.test_id
                and item.artifact_id == obligation.predicate.artifact_id
            ]
            if not claimed:
                # Call the predicate explicitly even for absent evidence so
                # every authored obligation has a recorded evaluation.
                _, reason = obligation.predicate.evaluate(None, expected_binding)
                assessments.append(
                    QualificationAssessment(obligation.obligation_id, "not_run", reason, True)
                )
                continue
            evaluations = [
                obligation.predicate.evaluate(item, expected_binding) for item in claimed
            ]
            reasons = tuple(reason for _, reason in evaluations)
            authored_statuses = obligation.predicate.allowed_statuses
            blocking_statuses = (
                ("status_failed", "failed" not in authored_statuses, "failed"),
                ("status_indeterminate", "indeterminate" not in authored_statuses, "indeterminate"),
                ("status_unrun", "unrun" not in authored_statuses, "not_run"),
                ("status_skipped", "skipped" not in authored_statuses, "partial_or_skipped"),
                ("status_quarantined", "quarantined" not in authored_statuses, "partial_or_skipped"),
                ("status_filtered", "filtered" not in authored_statuses, "partial_or_skipped"),
                ("status_partial", "partial" not in authored_statuses, "partial_or_skipped"),
                ("status_unavailable", "unavailable" not in authored_statuses, "indeterminate"),
            )
            blocking = next(
                (state for reason, is_blocking, state in blocking_statuses if reason in reasons and is_blocking),
                None,
            )
            if all(result for result, _ in evaluations):
                assessments.append(
                    QualificationAssessment(
                        obligation.obligation_id,
                        "satisfied",
                        "authored_predicate_satisfied",
                        True,
                    )
                )
                continue
            if blocking is not None:
                state = blocking
            elif self._has_unpermitted_incomplete_evidence(obligation, reasons):
                state = "indeterminate"
            elif any(reason.startswith("status_failed") for reason in reasons):
                state = "failed"
            elif any(
                reason.startswith("status_")
                and reason.split("status_", 1)[1]
                in {"skipped", "quarantined", "filtered", "partial"}
                for reason in reasons
            ):
                state = "partial_or_skipped"
            elif any(
                reason
                in {
                    "different_source_authority",
                    "wrong_source_binding",
                    "wrong_authored_binding",
                    "unverified_execution_evidence",
                    "exit_code_not_authored",
                }
                for reason in reasons
            ):
                state = "invalid_or_stale_evidence"
            elif all(reason == "status_unrun" for reason in reasons):
                state = "not_run"
            else:
                state = "indeterminate"
            assessments.append(
                QualificationAssessment(
                    obligation.obligation_id,
                    state,
                    ";".join(reasons),
                    True,
                )
            )
        disposition = "qualified" if all(
            assessment.state == "satisfied" for assessment in assessments
        ) else "not_qualified"
        return QualificationDecision(
            disposition=disposition,
            assessments=tuple(assessments),
            authored_obligations_retained=True,
            suggestions_ignored_for_authority=True,
        )

    @staticmethod
    def _has_unpermitted_incomplete_evidence(
        obligation: QualificationObligation,
        reasons: Sequence[str],
    ) -> bool:
        """Keep incomplete observations from being hidden by a passing retry."""

        return (
            obligation.predicate.require_complete is True
            and "execution_incomplete" in reasons
        )
