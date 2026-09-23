"""Controller-side, non-authorizing joins across source and attempt planes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .acquisition import GitSourceObservation, GitSourceObserver
from .attempts import AttemptLedger, AttemptRecord
from .authority import _binding_tuple
from .errors import ValidationError
from .qualification import ExecutionEvidence, QualificationAuthority
from .validation import _require_text


@dataclass(frozen=True)
class LineageAssessment:
    """Identity consistency only; never acquisition or execution readiness."""

    status: str
    reasons: tuple[str, ...]
    source_id: str
    attempt_id: str
    execution_authorized: bool = False
    scoring_authorized: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"consistent", "pending", "invalid"}:
            raise ValidationError("lineage status is unsupported")
        if (self.status == "consistent") != (not self.reasons):
            raise ValidationError("lineage status and reasons are inconsistent")
        if self.execution_authorized is not False or self.scoring_authorized is not False:
            raise ValidationError("lineage assessment cannot authorize execution or scoring")
        _require_text(self.source_id, "lineage source_id", identifier=True)
        _require_text(self.attempt_id, "lineage attempt_id", identifier=True)


def assess_lineage(
    source_observer: GitSourceObserver,
    source_observation: GitSourceObservation,
    ledger: AttemptLedger,
    record: AttemptRecord,
    execution_evidence: Sequence[ExecutionEvidence],
    qualification_authority: QualificationAuthority,
) -> LineageAssessment:
    """Revalidate real Git and join one current attempt to its exact results."""

    if type(source_observer) is not GitSourceObserver:
        raise ValidationError("lineage requires an independent Git source observer")
    source = source_observer.require(source_observation)
    if type(ledger) is not AttemptLedger or type(record) is not AttemptRecord:
        raise ValidationError("lineage requires an exact retained attempt")
    with ledger._lock:
        if ledger._records.get(record.attempt_id) is not record:
            raise ValidationError("lineage attempt is not the ledger-retained snapshot")
    if type(qualification_authority) is not QualificationAuthority:
        raise ValidationError("lineage requires authored qualification authority")
    task = record.access_planes.task_source
    planes = record.access_planes
    reasons: list[str] = []
    if (
        task.source_id != source["source_id"]
        or task.configuration_id != source["configuration_id"]
        or task.materialization_id != source["tree_sha"]
        or task.generation_id != source["revision"]
    ):
        reasons.append("source_materialization_mismatch")
    if (
        len({_binding_tuple(planes.task_source), _binding_tuple(planes.provider_source), _binding_tuple(planes.retrieval_source)}) != 3
        or planes.edit_scope.source_binding._authority is not task._authority
        or _binding_tuple(planes.edit_scope.source_binding) != _binding_tuple(task)
    ):
        reasons.append("access_planes_collapsed")
    evidence = tuple(execution_evidence)
    if not evidence and not record.evidence_refs and record.status in {"scheduled", "started"}:
        return LineageAssessment("invalid" if reasons else "pending", tuple(reasons) or ("execution_pending",), source["source_id"], record.attempt_id)
    refs = record.evidence_refs
    if not refs or len(refs) != len(set(refs)):
        reasons.append("retained_result_refs_incomplete")
    if not evidence or any(type(item) is not ExecutionEvidence for item in evidence):
        reasons.append("execution_evidence_missing")
    else:
        ids = tuple(item.evidence_id for item in evidence)
        if len(ids) != len(set(ids)) or set(ids) != set(refs):
            reasons.append("execution_result_identity_mismatch")
        if any(
            not item.is_authenticated()
            or item.attempt_id != record.attempt_id
            or item.source_binding._authority is not task._authority
            or _binding_tuple(item.source_binding) != _binding_tuple(task)
            or item.status != "passed"
            or item.observed is not True
            or item.complete is not True
            or item.terminal is not True
            for item in evidence
        ):
            reasons.append("execution_attempt_or_source_mismatch")
    if not qualification_authority.obligations or qualification_authority.assess(evidence, task).disposition != "qualified":
        reasons.append("qualification_not_satisfied")
    return LineageAssessment("consistent" if not reasons else "invalid", tuple(reasons), source["source_id"], record.attempt_id)
