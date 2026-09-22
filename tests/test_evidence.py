"""Direct tests for generic authenticated evidence contracts."""
from __future__ import annotations
from dataclasses import replace
import unittest
from repository_intelligence import evidence
from repository_intelligence.errors import ValidationError
from repository_intelligence.harness import Harness
from repository_intelligence.identity import IdentityBinding

class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.harness=Harness("evidence-test")
        self.binding=self.harness.bind("source-a","material-a","config-a","generation-a")
        self.other=self.harness.bind("source-b","material-b","config-b","generation-b")
        self.foreign=Harness("foreign-issuer").bind("source-a","material-a","config-a","generation-a")
    def record(self,**overrides):
        values={"result":[],"result_kind":"set","outcome":"success","support":"supported","completeness":"complete","termination":"normal_terminal","binding":self.binding,"query":"missing-symbol","operation":"search","coverage_universe_id":"coverage-a","view_id":"view-a","ordering":"canonical","evidence_session_id":"session-a","lineage_id":"lineage-a","has_more":False}
        values.update(overrides); return self.harness.record_evidence(**values)
    def test_attestation_requires_independent_authenticated_observation(self):
        raw={"members":["definition-a"]}; claim=evidence.ProviderClaim(dict(raw),IdentityBinding(*self.binding.as_dict().values())); observation=self.harness.observe_result(dict(raw),self.binding)
        attestation=evidence.attest_provider_result(claim,observation,self.binding)
        self.assertIs(evidence.validate_attestation(attestation,claim,observation,self.binding),attestation)
        same_raw=evidence.ProviderClaim(raw,self.binding)
        with self.assertRaisesRegex(ValidationError,"reuse the same raw result object"):
            evidence.attest_provider_result(same_raw,self.harness.observe_result(raw,self.binding),self.binding)
    def test_evidence_join_and_complete_absence_fail_closed(self):
        record=self.record(); self.assertIs(evidence.validate_evidence(record,self.binding),record); self.assertIs(evidence.require_complete_absence_evidence(record,self.binding),record); self.assertTrue(evidence.validate_evidence_for_absence(record,self.binding))
        for invalid in (self.record(completeness="partial",partial=True),self.record(termination="truncated",truncated=True),self.record(result=["present"])):
            with self.subTest(invalid=invalid),self.assertRaises(ValidationError):evidence.require_complete_absence_evidence(invalid,self.binding)
        with self.assertRaisesRegex(ValidationError,"binding does not match"):evidence.validate_evidence(record,self.other)
    def test_continuation_requires_every_lineage_dimension(self):
        page=self.record(result=["first"],completeness="partial",termination="continuation_available",has_more=True,continuation_cursor="cursor-a"); token=self.harness.mint_continuation(page)
        values={"expected_binding":self.binding,"evidence_session_id":"session-a","query":"missing-symbol","operation":"search","coverage_universe_id":"coverage-a","view_id":"view-a","ordering":"canonical","lineage_id":"lineage-a"}
        self.assertTrue(evidence.validate_continuation(token,**values))
        for field in ("evidence_session_id","query","operation","coverage_universe_id","view_id","ordering","lineage_id"):
            with self.subTest(field=field),self.assertRaises(ValidationError):evidence.validate_continuation(token,**{**values,field:"changed"})
        with self.assertRaisesRegex(ValidationError,"wrong source/configuration generation"):
            evidence.validate_continuation(token,**{**values,"expected_binding":self.other})
        with self.assertRaisesRegex(ValidationError,"different issuers"):
            evidence.validate_continuation(token,**{**values,"expected_binding":self.foreign})
        with self.assertRaisesRegex(ValidationError,"unauthenticated or mutated"):
            evidence.validate_continuation(replace(token,binding=self.other),**values)
        with self.assertRaises(ValidationError):evidence.validate_continuation(replace(token,query="changed"),**values)
if __name__=="__main__":unittest.main()
