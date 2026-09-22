"""Direct tests for the generic Harness issuance surface."""
from __future__ import annotations
import inspect
import unittest
from repository_intelligence import harness
from repository_intelligence.evidence import ProviderClaim
from repository_intelligence.identity import IdentityBinding

SECURITY={"network":"blocked","credentials":"absent","writable_roots":"scoped","process_limits":"bounded","resource_limits":"bounded","checkout":"read-only","host_config":"separate","cleanup":"complete"}
class HarnessTests(unittest.TestCase):
    def setUp(self):self.h=harness.Harness("harness-test"); self.binding=self.h.bind("source-a","material-a","config-a","generation-a")
    def test_harness_identity_is_required(self):self.assertIs(inspect.signature(harness.Harness).parameters["harness_id"].default,inspect.Parameter.empty); self.assertTrue(self.binding.is_authenticated())
    def test_claim_observation_attestation_issuance(self):
        claim=ProviderClaim({"members":["a"]},IdentityBinding("source-a","material-a","config-a","generation-a"),"provider"); observation=self.h.observe_result({"members":["a"]},self.binding); attestation=self.h.attest(claim,observation,self.binding)
        self.assertTrue(observation.is_authenticated()); self.assertTrue(attestation.is_valid(claim,observation,self.binding))
    def test_evidence_and_continuation_issuance(self):
        record=self.h.record_evidence(result=["a"],result_kind="set",outcome="success",support="supported",completeness="partial",termination="continuation_available",binding=self.binding,query="q",operation="search",coverage_universe_id="coverage-a",view_id="view-a",ordering="canonical",evidence_session_id="session-a",lineage_id="lineage-a",has_more=True,continuation_cursor="cursor-a",partial=True)
        self.assertTrue(record.is_authenticated()); self.assertTrue(self.h.mint_continuation(record).is_valid())
    def test_security_and_execution_issuance(self):
        observed=self.h.observe_security(self.binding,SECURITY,candidate_claims={"cleanup":"residue"}); execution=self.h.observe_execution(evidence_id="execution-a",binding=self.binding,command_id="command-a",test_id="test-a",artifact_id="artifact-a",status="passed",observed=True,complete=True,terminal=True,evidence_session_id="session-a",exit_code=0)
        self.assertTrue(observed.is_authenticated()); self.assertTrue(execution.is_authenticated())
if __name__=="__main__":unittest.main()
