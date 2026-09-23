"""Direct tests for generic security observations and evaluation."""
from __future__ import annotations
import unittest
from dataclasses import replace
import copy
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
        with self.assertRaises(ValidationError):security.SecurityEvaluation("pass",("conflict:cleanup",),"observation-a")
        with self.assertRaises(ValidationError):security.SecurityEvaluation("accepted",(),"observation-a")
    def test_policy_and_observation_values_use_closed_typed_vocabularies(self):
        for value in ("/","host-root","whatever-is-discovered-later","all-files"):
            with self.subTest(kind="policy",value=value),self.assertRaises(ValidationError):
                security.SecurityPolicy("unsafe",{**EXPECTED,"writable_roots":value},binding=self.binding)
            with self.subTest(kind="observation",value=value),self.assertRaises(ValidationError):
                self.h.observe_security(self.binding,{**EXPECTED,"writable_roots":value})
        unsafe=self.h.observe_security(self.binding,{**EXPECTED,"writable_roots":"unbounded"})
        self.assertEqual(security.evaluate_security(self.policy,unsafe,self.binding).status,"fail")

    def test_concrete_writable_roots_match_independent_issuer_observation(self):
        roots=("working-tree/candidate", "scratch/attempt")
        policy=security.WritableRootsPolicy("roots-a",self.binding,"sandbox-a",roots)
        observation=self.h.observe_writable_roots(self.binding,"sandbox-a",tuple(reversed(roots)),candidate_claims={"roots":["/"]})
        self.assertTrue(observation.is_authenticated())
        self.assertEqual(policy.roots,roots)
        self.assertEqual(security.evaluate_writable_roots(policy,observation,self.binding).status,"pass")
        self.assertEqual(security.evaluate_writable_roots(policy,self.h.observe_writable_roots(self.binding,"sandbox-a",()),self.binding).reasons,("missing:roots",))
        self.assertEqual(security.evaluate_writable_roots(policy,self.h.observe_writable_roots(self.binding,"sandbox-a",("working-tree/candidate", "scratch/attempt", "extra/root")),self.binding).reasons,("conflict:roots",))

    def test_concrete_writable_roots_reject_broad_overlap_and_false_provenance(self):
        roots=("working-tree/candidate", "scratch/attempt")
        policy=security.WritableRootsPolicy("roots-a",self.binding,"sandbox-a",roots)
        for invalid in ((),(".",),("/",),("~/data",),("$HOME",),("a/../b",),("a//b",),("a/*",),("a\\b",),("a", "a/b"),("a", "a")):
            with self.subTest(invalid=invalid),self.assertRaises(ValidationError):
                security.WritableRootsPolicy("invalid",self.binding,"sandbox-a",invalid)
        valid=self.h.observe_writable_roots(self.binding,"sandbox-a",roots)
        with self.assertRaises(ValidationError):
            security.evaluate_writable_roots(self.policy,valid,self.binding)
        for forged in (copy.copy(valid),replace(valid,anchor_id="sandbox-b"),replace(valid,roots=("extra/root",)),security.WritableRootsObservation("direct",self.binding,"sandbox-a",roots)):
            with self.subTest(forged=forged),self.assertRaises(ValidationError):
                security.evaluate_writable_roots(policy,forged,self.binding)
        other=self.h.bind("other","other-material","other-config","other-generation")
        with self.assertRaises(ValidationError):
            security.evaluate_writable_roots(policy,self.h.observe_writable_roots(other,"sandbox-a",roots),self.binding)
        with self.assertRaises(ValidationError):
            security.evaluate_writable_roots(policy,self.h.observe_writable_roots(self.binding,"sandbox-b",roots),self.binding)
        foreign_harness=Harness("foreign-roots")
        foreign_binding=foreign_harness.bind("source-a","material-a","config-a","generation-a")
        with self.assertRaises(ValidationError):
            security.evaluate_writable_roots(policy,foreign_harness.observe_writable_roots(foreign_binding,"sandbox-a",roots),self.binding)
if __name__=="__main__":unittest.main()
