"""Direct tests for generic security observations and evaluation."""
from __future__ import annotations
import unittest
from repository_intelligence import security
from repository_intelligence.errors import ValidationError
from repository_intelligence.harness import Harness

EXPECTED={"network":"blocked","credentials":"absent","writable_roots":"scoped","process_limits":"bounded","resource_limits":"bounded","checkout":"read-only","host_config":"separate","cleanup":"complete"}

class SecurityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness("security-test"); self.binding=self.h.bind("source-a","material-a","config-a","generation-a"); self.policy=security.SecurityPolicy("neutral-policy",EXPECTED,binding=self.binding)
    def test_closed_vocabulary_and_authenticated_observation(self):
        record=self.h.observe_security(self.binding,EXPECTED,candidate_claims={"cleanup":"residue"})
        self.assertIsInstance(record,security.SecurityObservation); self.assertTrue(record.is_authenticated()); self.assertEqual(set(record.observed),set(security.REQUIRED_SECURITY_OBSERVATIONS)); self.assertEqual(record.observed["cleanup"],"complete")
        self.assertEqual(security.evaluate_security(self.policy,record,self.binding).status,"pass")
        with self.assertRaises(ValidationError):self.h.observe_security(self.binding,{**EXPECTED,"provider_secret":"present"})
    def test_policy_evaluation_is_bound_and_fail_closed(self):
        passed=security.evaluate_security(self.policy,self.h.observe_security(self.binding,EXPECTED),self.binding); self.assertEqual((passed.status,passed.reasons),("pass",()))
        observed=dict(EXPECTED); observed.pop("writable_roots"); observed["cleanup"]="residue"
        failed=security.evaluate_security(self.policy,self.h.observe_security(self.binding,observed),self.binding); self.assertEqual((failed.status,failed.reasons),("fail",("missing:writable_roots","conflict:cleanup")))
        other=self.h.bind("source-b","material-b","config-b","generation-b")
        with self.assertRaisesRegex(ValidationError,"observation binding mismatch"):security.evaluate_security(self.policy,self.h.observe_security(self.binding,EXPECTED),other)
        with self.assertRaisesRegex(ValidationError,"policy binding mismatch"):security.evaluate_security(self.policy,self.h.observe_security(other,EXPECTED),other)
        foreign=Harness("foreign").bind("source-a","material-a","config-a","generation-a")
        with self.assertRaisesRegex(ValidationError,"different issuers"):security.evaluate_security(self.policy,self.h.observe_security(self.binding,EXPECTED),foreign)
    def test_evaluation_record_shape_is_typed(self):
        result=security.SecurityEvaluation("fail",("conflict:cleanup",),"observation-a"); self.assertEqual((result.status,result.reasons,result.observation_id),("fail",("conflict:cleanup",),"observation-a"))
if __name__=="__main__":unittest.main()
