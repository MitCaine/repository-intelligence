"""Direct tests for generic qualification evidence authority."""
from __future__ import annotations
import unittest
from repository_intelligence import qualification
from repository_intelligence.harness import Harness

class QualificationAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness("qualification-test"); self.binding=self.h.bind("source-a","material-a","config-a","generation-a")
        predicate=qualification.AuthoredEvidencePredicate("predicate-a",self.binding,"command-a","test-a","artifact-a")
        self.authority=qualification.QualificationAuthority([qualification.QualificationObligation("obligation-a",predicate)])
    def observed(self,status="passed",complete=True,exit_code=0,**overrides):
        values=dict(evidence_id="execution-a",binding=self.binding,command_id="command-a",test_id="test-a",artifact_id="artifact-a",status=status,observed=True,complete=complete,terminal=True,evidence_session_id="session-a",exit_code=exit_code); values.update(overrides)
        return self.h.observe_execution(**values)
    def test_authored_predicates_control_disposition_and_suggestions_do_not(self):
        suggestion={"status":"passed","exit_code":0}; absent=self.authority.assess([suggestion],self.binding,machine_suggestions=[suggestion])
        self.assertEqual((absent.disposition,absent.assessments[0].state),("not_qualified","not_run"))
        passed=self.authority.assess([self.observed()],self.binding,machine_suggestions=[{"status":"failed"}]); self.assertEqual((passed.disposition,passed.assessments[0].state),("qualified","satisfied"))
        failed=self.authority.assess([self.observed("failed",exit_code=1),self.observed()],self.binding); self.assertEqual((failed.disposition,failed.assessments[0].state),("not_qualified","failed"))
    def test_incomplete_execution_cannot_qualify(self):
        decision=self.authority.assess([self.observed(complete=False)],self.binding)
        self.assertEqual((decision.disposition,decision.assessments[0].state),("not_qualified","indeterminate"))
    def test_nonzero_pass_requires_exact_authored_exception(self):
        nonzero=self.observed(exit_code=7)
        self.assertEqual(self.authority.assess([nonzero],self.binding).disposition,"not_qualified")
        predicate=qualification.AuthoredEvidencePredicate("predicate-b",self.binding,"command-a","test-a","artifact-a",allowed_exit_codes=(7,))
        authority=qualification.QualificationAuthority([qualification.QualificationObligation("obligation-b",predicate)])
        self.assertEqual(authority.assess([nonzero],self.binding).disposition,"qualified")
    def test_valid_evidence_cannot_mask_same_identity_wrong_binding(self):
        other=self.h.bind("source-b","material-a","config-a","generation-a")
        wrong=self.observed(evidence_id="execution-wrong",binding=other)
        decision=self.authority.assess([self.observed(),wrong],self.binding)
        self.assertEqual((decision.disposition,decision.assessments[0].state),("not_qualified","invalid_or_stale_evidence"))
    def test_unrelated_observation_identity_does_not_poison_obligation(self):
        unrelated=self.observed(evidence_id="execution-other",command_id="command-other",status="failed",exit_code=1)
        self.assertEqual(self.authority.assess([self.observed(),unrelated],self.binding).disposition,"qualified")
if __name__=="__main__":unittest.main()
