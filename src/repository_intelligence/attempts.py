"""Attempt allocation, lifecycle, immutable history, and linked rerun contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import threading
from typing import Any, Optional, Sequence

from .authority import _binding_tuple, _require_authenticated_binding
from .errors import DuplicateAttemptError, ValidationError
from .identity import AuthenticatedBinding
from .validation import _require_text


@dataclass(frozen=True)
class AttemptRecord:
    """Immutable snapshot of one durable pre-execution attempt allocation."""

    attempt_id: str
    benchmark_id: str
    condition_id: str
    corpus_id: str
    case_id: str
    task_id: str
    source_binding: AuthenticatedBinding
    configuration_id: str
    schedule_block_id: str
    status: str
    disposition: str
    retry_of: Optional[str] = None
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
        _require_authenticated_binding(self.source_binding, "source_binding")
        if self.configuration_id != self.source_binding.configuration_id:
            raise ValidationError("attempt configuration does not match source binding")
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
        if self.retry_of is not None:
            _require_text(self.retry_of, "retry_of", identifier=True)
        if type(self.allocation_sequence) is not int or self.allocation_sequence < 1:
            raise ValidationError("allocation_sequence must be a positive integer")
        if not isinstance(self.evidence_refs, tuple) or any(
            type(item) is not str or not item.strip() for item in self.evidence_refs
        ):
            raise ValidationError("evidence_refs must be an immutable tuple of text")


class AttemptLedger:
    """Thread-safe, append-retaining allocator for scheduled and rerun attempts.

    Validation and duplicate checks complete before the counter and record are
    changed.  A rerun receives a new identity linked by ``retry_of``; it never
    rewrites the original snapshot or evidence references.
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

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, AttemptRecord] = {}
        self._history: list[AttemptRecord] = []
        self._allocation_keys: set[tuple[str, ...]] = set()
        self._next_sequence = 1

    @staticmethod
    def _key(
        benchmark_id: str,
        condition_id: str,
        corpus_id: str,
        case_id: str,
        task_id: str,
        source_binding: AuthenticatedBinding,
        configuration_id: str,
        schedule_block_id: str,
    ) -> tuple[str, ...]:
        return (
            benchmark_id,
            condition_id,
            corpus_id,
            case_id,
            task_id,
            *(_binding_tuple(source_binding)),
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
        source_binding: AuthenticatedBinding,
        configuration_id: str,
        schedule_block_id: str,
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
        binding = _require_authenticated_binding(source_binding, "source_binding")
        if configuration_id != binding.configuration_id:
            raise ValidationError("configuration_id must equal source binding configuration_id")
        if retry_of is not None:
            _require_text(retry_of, "retry_of", identifier=True)

        key = self._key(
            benchmark_id,
            condition_id,
            corpus_id,
            case_id,
            task_id,
            binding,
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
                    original.source_binding,
                    original.configuration_id,
                    original.schedule_block_id,
                ) != key:
                    raise ValidationError("retry identity does not match original bindings")
            sequence = self._next_sequence
            attempt_id = f"attempt-{sequence:04d}"
            record = AttemptRecord(
                attempt_id=attempt_id,
                benchmark_id=benchmark_id,
                condition_id=condition_id,
                corpus_id=corpus_id,
                case_id=case_id,
                task_id=task_id,
                source_binding=binding,
                configuration_id=configuration_id,
                schedule_block_id=schedule_block_id,
                status="scheduled",
                disposition="scheduled_before_execution",
                retry_of=retry_of,
                allocation_sequence=sequence,
            )
            self._next_sequence += 1
            self._records[attempt_id] = record
            self._history.append(record)
            self._allocation_keys.add(key)
            return record

    def start(self, attempt_id: str) -> AttemptRecord:
        """Mark a scheduled allocation started without changing its identity."""

        with self._lock:
            record = self._records.get(attempt_id)
            if record is None:
                raise ValidationError("unknown attempt_id")
            if record.status != "scheduled":
                raise ValidationError("only scheduled attempts can start")
            updated = replace(record, status="started", disposition="execution_started")
            self._records[attempt_id] = updated
            self._history.append(updated)
            return updated

    def finish(
        self,
        attempt_id: str,
        *,
        status: str,
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
            updated = replace(
                record,
                status=status,
                disposition=disposition,
                evidence_refs=refs,
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
                "source_binding": original.source_binding,
                "configuration_id": original.configuration_id,
                "schedule_block_id": original.schedule_block_id,
            }
        defaults.update(kwargs)
        defaults["retry_of"] = original_attempt_id
        return self.allocate(**defaults)
