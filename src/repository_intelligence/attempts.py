"""Attempt allocation, lifecycle, immutable history, and linked rerun contracts."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import threading
from typing import Any, Optional, Sequence

from .authority import _binding_tuple, _require_authenticated_binding
from .errors import DuplicateAttemptError, ValidationError
from .identity import AuthenticatedBinding
from .qualification import ExecutionEvidence, QualificationAuthority
from .scope import ScopeGrant
from .security import AttemptCleanupObservation, CacheResetObservation
from .validation import _require_text


@dataclass(frozen=True)
class AccessPlanes:
    """Explicit source, visibility, and edit-authority planes for one attempt."""

    task_source: AuthenticatedBinding
    provider_source: AuthenticatedBinding
    retrieval_source: AuthenticatedBinding
    edit_scope: ScopeGrant

    def __post_init__(self) -> None:
        bindings = (
            _require_authenticated_binding(self.task_source, "task_source"),
            _require_authenticated_binding(self.provider_source, "provider_source"),
            _require_authenticated_binding(self.retrieval_source, "retrieval_source"),
        )
        if len({_binding_tuple(binding) for binding in bindings}) != len(bindings):
            raise ValidationError("task, provider, and retrieval sources must be distinct")
        if not isinstance(self.edit_scope, ScopeGrant):
            raise ValidationError("edit_scope must be an immutable ScopeGrant")
        if _binding_tuple(self.edit_scope.source_binding) != _binding_tuple(self.task_source):
            raise ValidationError("edit_scope must bind the authenticated task source")
        if self.edit_scope.source_binding._authority is not self.task_source._authority:
            raise ValidationError("edit_scope and task source must share an authenticated issuer")
        if self.edit_scope.configuration_id != self.task_source.configuration_id:
            raise ValidationError("edit_scope configuration must match task source")


@dataclass(frozen=True)
class AttemptEligibility:
    """Legacy descriptive cache flag; never authoritative for G2 scoring."""

    cache_state: str
    cache_state_verified: bool
    scoring_eligible: bool

    def __post_init__(self) -> None:
        if self.cache_state not in {"cold", "warm", "unknown"}:
            raise ValidationError("cache_state is unsupported")
        if type(self.cache_state_verified) is not bool or type(self.scoring_eligible) is not bool:
            raise ValidationError("cache verification and scoring eligibility must be exact booleans")
        if self.scoring_eligible and (
            not self.cache_state_verified or self.cache_state not in {"cold", "warm"}
        ):
            raise ValidationError("scoring eligibility requires verified cache/reset state")


@dataclass(frozen=True)
class ScoringDecision:
    """Derived G2 eligibility, not a score or measurement."""

    disposition: str
    reasons: tuple[str, ...]
    attempt_id: str
    cache_observation_id: Optional[str]

    def __post_init__(self) -> None:
        if self.disposition not in {"eligible", "ineligible"} or (self.disposition == "eligible") != (not self.reasons):
            raise ValidationError("scoring disposition and reasons are inconsistent")
        _require_text(self.attempt_id, "scoring attempt_id", identifier=True)


def assess_scoring(
    ledger: "AttemptLedger",
    record: "AttemptRecord",
    cache_observation: Optional[CacheResetObservation],
    execution_evidence: Sequence[ExecutionEvidence],
    qualification_authority: QualificationAuthority,
) -> ScoringDecision:
    """Gate scoring on exact independent reset, cleanup and authored evidence."""

    if type(ledger) is not AttemptLedger or type(record) is not AttemptRecord:
        raise ValidationError("scoring requires one immutable attempt record")
    with ledger._lock:
        if ledger._records.get(record.attempt_id) is not record:
            raise ValidationError("scoring attempt is not the ledger-retained snapshot")
    if type(qualification_authority) is not QualificationAuthority:
        raise ValidationError("scoring requires authored qualification authority")
    evidence = tuple(execution_evidence)
    binding = record.access_planes.task_source
    reasons: list[str] = []
    if record.status != "completed" or record.termination != "normal" or record.finished_at is None:
        reasons.append("attempt_not_completed")
    if record.cleanup_disposition != "clean" or record._cleanup_evidence is None or not record._cleanup_evidence.is_authenticated():
        reasons.append("cleanup_not_clean")
    cache_id = None
    if type(cache_observation) is not CacheResetObservation or not cache_observation.is_authenticated():
        reasons.append("cache_unverified")
    else:
        cache_id = cache_observation.observation_id
        if (
            cache_observation.attempt_id != record.attempt_id
            or cache_observation.binding._authority is not binding._authority
            or _binding_tuple(cache_observation.binding) != _binding_tuple(binding)
        ):
            reasons.append("cache_identity_mismatch")
        if record.started_at is None or not (record.scheduled_at < cache_observation.observed_at < record.started_at):
            reasons.append("cache_reset_wrong_boundary")
        if cache_observation.reset_disposition != "complete":
            reasons.append("cache_reset_incomplete")
        if cache_observation.cache_state not in {"cold", "warm"} or cache_observation.cache_state != record.eligibility.cache_state:
            reasons.append("cache_state_mismatch")
    refs = record.evidence_refs
    if not refs or len(set(refs)) != len(refs):
        reasons.append("execution_refs_incomplete")
    typed = all(type(item) is ExecutionEvidence for item in evidence)
    ids = tuple(item.evidence_id for item in evidence) if typed else ()
    if not typed or not evidence or len(set(ids)) != len(ids) or set(ids) != set(refs):
        reasons.append("execution_identity_mismatch")
    if any(
        not item.is_authenticated()
        or item.source_binding._authority is not binding._authority
        or _binding_tuple(item.source_binding) != _binding_tuple(binding)
        or item.status != "passed"
        or item.observed is not True
        or item.complete is not True
        or item.terminal is not True
        for item in evidence if type(item) is ExecutionEvidence
    ):
        reasons.append("execution_not_complete_passing")
    if not qualification_authority.obligations or qualification_authority.assess(evidence, binding).disposition != "qualified":
        reasons.append("qualification_not_satisfied")
    return ScoringDecision("eligible" if not reasons else "ineligible", tuple(reasons), record.attempt_id, cache_id)


@dataclass(frozen=True)
class AttemptRecord:
    """Immutable snapshot of one process-local pre-execution allocation."""

    attempt_id: str
    benchmark_id: str
    condition_id: str
    corpus_id: str
    case_id: str
    task_id: str
    access_planes: AccessPlanes
    eligibility: AttemptEligibility
    configuration_id: str
    schedule_block_id: str
    status: str
    disposition: str
    termination: str
    scheduled_at: int
    started_at: Optional[int] = None
    finished_at: Optional[int] = None
    last_observed_at: int = 0
    cleanup_observation_id: Optional[str] = None
    cleanup_observed_at: Optional[int] = None
    cleanup_disposition: str = "unobserved"
    _cleanup_evidence: Optional[AttemptCleanupObservation] = field(default=None, repr=False, compare=False)
    retry_of: Optional[str] = None
    retry_root_id: str = ""
    evidence_refs: tuple[str, ...] = ()
    allocation_sequence: int = 0

    def __post_init__(self) -> None:
        for name in (
            "attempt_id",
            "benchmark_id",
            "condition_id",
            "corpus_id",
            "case_id",
            "task_id",
            "configuration_id",
            "schedule_block_id",
        ):
            _require_text(getattr(self, name), name, identifier=True)
        if not isinstance(self.access_planes, AccessPlanes):
            raise ValidationError("attempt requires explicit AccessPlanes")
        if not isinstance(self.eligibility, AttemptEligibility):
            raise ValidationError("attempt requires explicit AttemptEligibility")
        if self.configuration_id != self.access_planes.task_source.configuration_id:
            raise ValidationError("attempt configuration does not match task source binding")
        if self.status not in {
            "scheduled",
            "started",
            "completed",
            "setup_failed",
            "crashed",
            "timed_out",
            "killed",
            "resource_exhausted",
            "invalid_manifest",
            "hard_gate_failed",
            "excluded",
            "cancelled",
            "substituted",
        }:
            raise ValidationError("attempt status is unsupported")
        _require_text(self.disposition, "disposition")
        _require_text(self.termination, "termination", identifier=True)
        if type(self.scheduled_at) is not int or self.scheduled_at < 0:
            raise ValidationError("scheduled_at must be a nonnegative integer")
        if type(self.last_observed_at) is not int or self.last_observed_at < self.scheduled_at:
            raise ValidationError("last_observed_at cannot precede scheduled_at")
        for name in ("started_at", "finished_at"):
            value = getattr(self, name)
            if value is not None and type(value) is not int:
                raise ValidationError(f"{name} must be an exact integer when present")
        if self.status == "scheduled":
            if self.termination != "not_started" or self.started_at is not None or self.finished_at is not None:
                raise ValidationError("scheduled attempt lifecycle is inconsistent")
        elif self.status == "started":
            if self.termination != "running" or self.started_at is None or self.finished_at is not None:
                raise ValidationError("started attempt lifecycle is inconsistent")
            if self.started_at <= self.scheduled_at or self.last_observed_at < self.started_at:
                raise ValidationError("started attempt time must follow scheduled time")
        else:
            expected_termination = self.status
            if self.status == "completed":
                expected_termination = "normal"
            if self.termination != expected_termination:
                raise ValidationError("terminal status and termination are inconsistent")
            if self.started_at is None or self.finished_at is None:
                raise ValidationError("terminal attempt requires start and finish observations")
            if not (self.scheduled_at < self.started_at < self.finished_at <= self.last_observed_at):
                raise ValidationError("terminal attempt time ordering is inconsistent")
        if self.cleanup_observation_id is None:
            if self.cleanup_observed_at is not None or self.cleanup_disposition != "unobserved" or self._cleanup_evidence is not None:
                raise ValidationError("cleanup fields require an authenticated observation identity")
        else:
            _require_text(self.cleanup_observation_id, "cleanup_observation_id", identifier=True)
            evidence = self._cleanup_evidence
            if (
                type(evidence) is not AttemptCleanupObservation
                or not evidence.is_authenticated()
                or evidence.observation_id != self.cleanup_observation_id
                or evidence.attempt_id != self.attempt_id
                or evidence.observed_at != self.cleanup_observed_at
                or evidence.disposition != self.cleanup_disposition
                or evidence.binding._authority is not self.access_planes.task_source._authority
                or _binding_tuple(evidence.binding) != _binding_tuple(self.access_planes.task_source)
            ):
                raise ValidationError("cleanup fields require exact authenticated observation")
            if self.status in {"scheduled", "started"} or self.finished_at is None:
                raise ValidationError("cleanup requires a terminal attempt")
            if (
                type(self.cleanup_observed_at) is not int
                or self.cleanup_observed_at <= self.finished_at
                or self.cleanup_observed_at > self.last_observed_at
            ):
                raise ValidationError("cleanup observation must follow terminal finish")
            if self.cleanup_disposition not in {"clean", "residue", "unknown"}:
                raise ValidationError("cleanup disposition is unsupported")
        if self.retry_of is not None:
            _require_text(self.retry_of, "retry_of", identifier=True)
        _require_text(self.retry_root_id, "retry_root_id", identifier=True)
        if type(self.allocation_sequence) is not int or self.allocation_sequence < 1:
            raise ValidationError("allocation_sequence must be a positive integer")
        if not isinstance(self.evidence_refs, tuple) or any(
            type(item) is not str or not item.strip() for item in self.evidence_refs
        ):
            raise ValidationError("evidence_refs must be an immutable tuple of text")


class AttemptLedger:
    """Thread-safe, process-local allocator for scheduled and rerun attempts.

    Validation and duplicate checks complete before the counter and record are
    changed.  A rerun receives a new identity linked by ``retry_of``; it never
    rewrites the original snapshot or evidence references. Records are retained
    only for this Python process; no restart or interruption durability is
    provided.
    """

    _TERMINAL = {
        "completed",
        "setup_failed",
        "crashed",
        "timed_out",
        "killed",
        "resource_exhausted",
        "invalid_manifest",
        "hard_gate_failed",
        "excluded",
        "cancelled",
        "substituted",
    }

    def __init__(self, *, retry_budget: int = 1) -> None:
        if type(retry_budget) is not int or retry_budget < 0:
            raise ValidationError("retry_budget must be a nonnegative integer")
        self._lock = threading.RLock()
        self._records: dict[str, AttemptRecord] = {}
        self._history: list[AttemptRecord] = []
        self._allocation_keys: set[tuple[str, ...]] = set()
        self._next_sequence = 1
        self._retry_budget = retry_budget
        self._root_retry_counts: dict[str, int] = {}

    @staticmethod
    def _key(
        benchmark_id: str,
        condition_id: str,
        corpus_id: str,
        case_id: str,
        task_id: str,
        access_planes: AccessPlanes,
        configuration_id: str,
        schedule_block_id: str,
    ) -> tuple[str, ...]:
        return (
            benchmark_id,
            condition_id,
            corpus_id,
            case_id,
            task_id,
            *(_binding_tuple(access_planes.task_source)),
            *(_binding_tuple(access_planes.provider_source)),
            *(_binding_tuple(access_planes.retrieval_source)),
            access_planes.edit_scope.digest,
            configuration_id,
            schedule_block_id,
        )

    @property
    def records(self) -> tuple[AttemptRecord, ...]:
        """Return current immutable snapshots in allocation order."""

        with self._lock:
            return tuple(self._records.values())

    @property
    def history(self) -> tuple[AttemptRecord, ...]:
        """Return all allocation/status snapshots retained for audit."""

        with self._lock:
            return tuple(self._history)

    def allocate(
        self,
        *,
        benchmark_id: str,
        condition_id: str,
        corpus_id: str,
        case_id: str,
        task_id: str,
        access_planes: AccessPlanes,
        eligibility: AttemptEligibility,
        configuration_id: str,
        schedule_block_id: str,
        scheduled_at: int,
        retry_of: Optional[str] = None,
    ) -> AttemptRecord:
        """Atomically allocate an identity before any execution can begin."""

        fields = {
            "benchmark_id": benchmark_id,
            "condition_id": condition_id,
            "corpus_id": corpus_id,
            "case_id": case_id,
            "task_id": task_id,
            "configuration_id": configuration_id,
            "schedule_block_id": schedule_block_id,
        }
        for name, value in fields.items():
            _require_text(value, name, identifier=True)
        if not isinstance(access_planes, AccessPlanes):
            raise ValidationError("access_planes must be explicit authenticated planes")
        if not isinstance(eligibility, AttemptEligibility):
            raise ValidationError("eligibility must be explicit cache/reset evidence")
        if configuration_id != access_planes.task_source.configuration_id:
            raise ValidationError("configuration_id must equal source binding configuration_id")
        if type(scheduled_at) is not int or scheduled_at < 0:
            raise ValidationError("scheduled_at must be a nonnegative integer")
        if retry_of is not None:
            _require_text(retry_of, "retry_of", identifier=True)

        key = self._key(
            benchmark_id,
            condition_id,
            corpus_id,
            case_id,
            task_id,
            access_planes,
            configuration_id,
            schedule_block_id,
        )
        with self._lock:
            if retry_of is None and key in self._allocation_keys:
                raise DuplicateAttemptError("duplicate attempt allocation rejected atomically")
            if retry_of is not None:
                original = self._records.get(retry_of)
                if original is None:
                    raise ValidationError("retry_of does not identify a retained attempt")
                if original.status not in self._TERMINAL:
                    raise ValidationError("only a terminal attempt may be rerun")
                if self._key(
                    original.benchmark_id,
                    original.condition_id,
                    original.corpus_id,
                    original.case_id,
                    original.task_id,
                    original.access_planes,
                    original.configuration_id,
                    original.schedule_block_id,
                ) != key:
                    raise ValidationError("retry identity does not match original bindings")
                root_id = original.retry_root_id
                if self._root_retry_counts.get(root_id, 0) >= self._retry_budget:
                    raise ValidationError("root retry budget is exhausted")
                if scheduled_at <= original.last_observed_at:
                    raise ValidationError("retry schedule must follow original observation")
            sequence = self._next_sequence
            attempt_id = f"attempt-{sequence:04d}"
            root_id = attempt_id if retry_of is None else self._records[retry_of].retry_root_id
            record = AttemptRecord(
                attempt_id=attempt_id,
                benchmark_id=benchmark_id,
                condition_id=condition_id,
                corpus_id=corpus_id,
                case_id=case_id,
                task_id=task_id,
                access_planes=access_planes,
                eligibility=eligibility,
                configuration_id=configuration_id,
                schedule_block_id=schedule_block_id,
                status="scheduled",
                disposition="scheduled_before_execution",
                termination="not_started",
                scheduled_at=scheduled_at,
                last_observed_at=scheduled_at,
                retry_of=retry_of,
                retry_root_id=root_id,
                allocation_sequence=sequence,
            )
            self._next_sequence += 1
            self._records[attempt_id] = record
            self._history.append(record)
            self._allocation_keys.add(key)
            if retry_of is None:
                self._root_retry_counts[root_id] = 0
            else:
                self._root_retry_counts[root_id] += 1
            return record

    def start(self, attempt_id: str, *, observed_at: int) -> AttemptRecord:
        """Mark a scheduled allocation started without changing its identity."""

        with self._lock:
            record = self._records.get(attempt_id)
            if record is None:
                raise ValidationError("unknown attempt_id")
            if record.status != "scheduled":
                raise ValidationError("only scheduled attempts can start")
            if type(observed_at) is not int or observed_at <= record.scheduled_at:
                raise ValidationError("start observation must be after scheduled time")
            updated = replace(
                record,
                status="started",
                disposition="execution_started",
                termination="running",
                started_at=observed_at,
                last_observed_at=observed_at,
            )
            self._records[attempt_id] = updated
            self._history.append(updated)
            return updated

    def finish(
        self,
        attempt_id: str,
        *,
        status: str,
        termination: str,
        observed_at: int,
        disposition: str,
        evidence_refs: Sequence[str] = (),
    ) -> AttemptRecord:
        """Retain one terminal outcome; refuse to rewrite an already-terminal run."""

        if status not in self._TERMINAL:
            raise ValidationError("finish status must be terminal")
        _require_text(disposition, "disposition")
        refs = tuple(evidence_refs)
        with self._lock:
            record = self._records.get(attempt_id)
            if record is None:
                raise ValidationError("unknown attempt_id")
            if record.status in self._TERMINAL:
                raise ValidationError("terminal attempt evidence cannot be rewritten")
            if record.status != "started":
                raise ValidationError("only started attempts can finish")
            if type(observed_at) is not int or observed_at <= record.last_observed_at:
                raise ValidationError("finish observation must follow start observation")
            updated = replace(
                record,
                status=status,
                termination=termination,
                finished_at=observed_at,
                last_observed_at=observed_at,
                disposition=disposition,
                evidence_refs=refs,
            )
            self._records[attempt_id] = updated
            self._history.append(updated)
            return updated

    def record_cleanup(
        self,
        attempt_id: str,
        observation: AttemptCleanupObservation,
    ) -> AttemptRecord:
        """Attach one independent post-terminal cleanup observation atomically."""

        if type(observation) is not AttemptCleanupObservation or not observation.is_authenticated():
            raise ValidationError("cleanup observation lacks independent issuer provenance")
        with self._lock:
            record = self._records.get(attempt_id)
            if record is None:
                raise ValidationError("unknown attempt_id")
            if record.status not in self._TERMINAL or record.finished_at is None:
                raise ValidationError("cleanup requires a terminal attempt")
            if record.cleanup_observation_id is not None:
                raise ValidationError("terminal cleanup observation cannot be rewritten")
            if observation.attempt_id != attempt_id:
                raise ValidationError("cleanup observation attempt identity mismatch")
            if (
                observation.binding._authority is not record.access_planes.task_source._authority
                or _binding_tuple(observation.binding) != _binding_tuple(record.access_planes.task_source)
            ):
                raise ValidationError("cleanup observation source identity mismatch")
            if observation.observed_at <= record.last_observed_at:
                raise ValidationError("cleanup observation must follow terminal finish")
            updated = replace(
                record,
                cleanup_observation_id=observation.observation_id,
                cleanup_observed_at=observation.observed_at,
                cleanup_disposition=observation.disposition,
                _cleanup_evidence=observation,
                last_observed_at=observation.observed_at,
            )
            self._records[attempt_id] = updated
            self._history.append(updated)
            return updated

    def rerun(self, original_attempt_id: str, **kwargs: Any) -> AttemptRecord:
        """Allocate a new linked attempt after a retained terminal attempt."""

        with self._lock:
            original = self._records.get(original_attempt_id)
            if original is None:
                raise ValidationError("unknown original attempt")
            if original.status not in self._TERMINAL:
                raise ValidationError("only a terminal attempt may be rerun")
            defaults = {
                "benchmark_id": original.benchmark_id,
                "condition_id": original.condition_id,
                "corpus_id": original.corpus_id,
                "case_id": original.case_id,
                "task_id": original.task_id,
                "access_planes": original.access_planes,
                "eligibility": original.eligibility,
                "configuration_id": original.configuration_id,
                "schedule_block_id": original.schedule_block_id,
            }
        defaults.update(kwargs)
        defaults["retry_of"] = original_attempt_id
        return self.allocate(**defaults)
