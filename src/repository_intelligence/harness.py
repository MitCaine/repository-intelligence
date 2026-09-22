"""Generic authenticated record issuance and composition."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any, Optional

from .authority import _Authority, _require_authenticated_binding, _sign
from .errors import ValidationError
from .evidence import (
    ContinuationToken,
    EvidenceRecord,
    HarnessObservation,
    ProviderAttestation,
    ProviderClaim,
    _require_valid_evidence,
    attest_provider_result,
    validate_evidence,
)
from .identity import AuthenticatedBinding, IdentityBinding, _new_binding
from .qualification import ExecutionEvidence
from .security import SecurityObservation
from .validation import _json_value, _require_mapping, _require_text


class Harness:
    """Issue and validate authenticated records within one bounded authority."""

    def __init__(self, harness_id: str) -> None:
        self.harness_id = _require_text(harness_id, "harness_id", identifier=True)
        self._authority = _Authority(self.harness_id)
        self._observation_count = 0
        self._evidence_count = 0
        self._security_count = 0

    def authenticated_binding(
        self,
        source_id: str,
        materialization_id: str,
        configuration_id: str,
        generation_id: str,
    ) -> AuthenticatedBinding:
        """Authenticate all four material source identity dimensions."""

        return _new_binding(
            self._authority,
            source_id=source_id,
            materialization_id=materialization_id,
            configuration_id=configuration_id,
            generation_id=generation_id,
        )

    bind = authenticated_binding

    def observe_result(
        self,
        result: Any,
        binding: IdentityBinding,
    ) -> HarnessObservation:
        """Observe a result through a generated distinct path and provenance."""

        if not isinstance(binding, IdentityBinding):
            raise ValidationError("observation binding must be an IdentityBinding")
        _json_value(result, "observed result")
        self._observation_count += 1
        observation_id = f"observation-{self._observation_count:04d}"
        provenance = f"harness-controlled-observation/{self.harness_id}/{observation_id}"
        observation = HarnessObservation(
            result=result,
            binding=binding,
            observation_id=observation_id,
            provenance=provenance,
            _authority=self._authority,
        )
        object.__setattr__(
            observation,
            "_signature",
            _sign(
                self._authority,
                {
                    "observation_id": observation.observation_id,
                    "provenance": observation.provenance,
                    "binding": observation.binding.as_dict(),
                    "result": observation.result,
                },
            ),
        )
        return observation

    def attest(
        self,
        claim: ProviderClaim,
        observation: HarnessObservation,
        expected_binding: AuthenticatedBinding,
    ) -> ProviderAttestation:
        """Derive an accepted attestation only from this harness's observation."""

        if observation._authority is not self._authority:
            raise ValidationError("observation was not issued by this harness")
        return attest_provider_result(claim, observation, expected_binding)

    def record_evidence(
        self,
        *,
        result: Any,
        result_kind: str,
        outcome: str,
        support: str,
        completeness: str,
        termination: str,
        binding: AuthenticatedBinding,
        query: str,
        operation: str,
        coverage_universe_id: str,
        view_id: str,
        ordering: str,
        evidence_session_id: str,
        lineage_id: str,
        has_more: bool,
        continuation_cursor: Optional[str] = None,
        partial: bool = False,
        truncated: bool = False,
        stale: bool = False,
        available: bool = True,
        top_level_binding: Optional[AuthenticatedBinding] = None,
        embedded_binding: Optional[AuthenticatedBinding] = None,
    ) -> EvidenceRecord:
        """Issue one signed evidence record with duplicated binding fields."""

        expected = _require_authenticated_binding(binding, "evidence binding")
        if expected._authority is not self._authority:
            raise ValidationError("evidence binding was not issued by this harness")
        _json_value(result, "evidence result")
        self._evidence_count += 1
        evidence = EvidenceRecord(
            evidence_id=f"evidence-{self._evidence_count:04d}",
            result=result,
            result_kind=result_kind,
            outcome=outcome,
            support=support,
            completeness=completeness,
            termination=termination,
            binding=expected,
            query=query,
            operation=operation,
            coverage_universe_id=coverage_universe_id,
            view_id=view_id,
            ordering=ordering,
            evidence_session_id=evidence_session_id,
            lineage_id=lineage_id,
            has_more=has_more,
            continuation_cursor=continuation_cursor,
            partial=partial,
            truncated=truncated,
            stale=stale,
            available=available,
            top_level_binding=top_level_binding,
            embedded_binding=embedded_binding,
            _authority=self._authority,
        )
        object.__setattr__(evidence, "_signature", _sign(self._authority, evidence._signed_payload()))
        return evidence

    def mint_continuation(self, evidence: EvidenceRecord) -> ContinuationToken:
        """Mint continuation only from nonterminal evidence with a cursor."""

        record = _require_valid_evidence(evidence)
        if record._authority is not self._authority:
            raise ValidationError("evidence was not issued by this harness")
        # Authentication covers the record bytes; this semantic join also
        # prevents a signed-but-cross-bound page from minting portable state.
        validate_evidence(record, record.binding)
        if record.has_more is not True or record.continuation_cursor is None:
            raise ValidationError("terminal evidence cannot mint a continuation token")
        if record.termination != "continuation_available":
            raise ValidationError("continuation requires continuation_available termination")
        if record.completeness == "complete":
            raise ValidationError("complete evidence cannot advertise more pages")
        token_id = "continuation-" + hashlib.sha256(
            f"{record.evidence_id}|{record.continuation_cursor}|{record.lineage_id}".encode()
        ).hexdigest()[:20]
        token = ContinuationToken(
            token_id=token_id,
            evidence_session_id=record.evidence_session_id,
            query=record.query,
            operation=record.operation,
            coverage_universe_id=record.coverage_universe_id,
            view_id=record.view_id,
            ordering=record.ordering,
            lineage_id=record.lineage_id,
            cursor=record.continuation_cursor,
            binding=record.binding,
            has_more=True,
            _authority=self._authority,
        )
        object.__setattr__(
            token,
            "_signature",
            _sign(
                self._authority,
                {
                    "token_id": token.token_id,
                    "evidence_session_id": token.evidence_session_id,
                    "query": token.query,
                    "operation": token.operation,
                    "coverage_universe_id": token.coverage_universe_id,
                    "view_id": token.view_id,
                    "ordering": token.ordering,
                    "lineage_id": token.lineage_id,
                    "cursor": token.cursor,
                    "binding": token.binding.as_dict(),
                    "has_more": True,
                },
            ),
        )
        return token

    def observe_security(
        self,
        binding: AuthenticatedBinding,
        observed: Mapping[str, str],
        *,
        candidate_claims: Optional[Mapping[str, Any]] = None,
    ) -> SecurityObservation:
        """Record independent security state; candidate claims are intentionally ignored."""

        expected = _require_authenticated_binding(binding, "security binding")
        if expected._authority is not self._authority:
            raise ValidationError("security binding was not issued by this harness")
        if candidate_claims is not None:
            _require_mapping(candidate_claims, "candidate_claims")
        self._security_count += 1
        observation = SecurityObservation(
            observation_id=f"security-observation-{self._security_count:04d}",
            context_id=f"security-context-{self._security_count:04d}",
            binding=expected,
            observed=observed,
            _authority=self._authority,
        )
        object.__setattr__(
            observation,
            "_signature",
            _sign(
                self._authority,
                {
                    "observation_id": observation.observation_id,
                    "context_id": observation.context_id,
                    "binding": observation.binding.as_dict(),
                    "observed": observation.observed,
                },
            ),
        )
        return observation

    def observe_execution(
        self,
        *,
        evidence_id: str,
        binding: AuthenticatedBinding,
        command_id: str,
        test_id: str,
        artifact_id: str,
        status: str,
        observed: bool,
        complete: bool,
        terminal: bool,
        evidence_session_id: str,
        exit_code: Optional[int] = None,
    ) -> ExecutionEvidence:
        """Issue exact/bounded execution evidence through the harness path."""

        expected = _require_authenticated_binding(binding, "execution binding")
        if expected._authority is not self._authority:
            raise ValidationError("execution binding was not issued by this harness")
        record = ExecutionEvidence(
            evidence_id=evidence_id,
            source_binding=expected,
            command_id=command_id,
            test_id=test_id,
            artifact_id=artifact_id,
            status=status,
            observed=observed,
            complete=complete,
            terminal=terminal,
            evidence_session_id=evidence_session_id,
            exit_code=exit_code,
            _authority=self._authority,
        )
        object.__setattr__(
            record,
            "_signature",
            _sign(
                self._authority,
                {
                    "evidence_id": record.evidence_id,
                    "source_binding": record.source_binding.as_dict(),
                    "command_id": record.command_id,
                    "test_id": record.test_id,
                    "artifact_id": record.artifact_id,
                    "status": record.status,
                    "observed": record.observed,
                    "complete": record.complete,
                    "terminal": record.terminal,
                    "evidence_session_id": record.evidence_session_id,
                    "exit_code": record.exit_code,
                },
            ),
        )
        return record
