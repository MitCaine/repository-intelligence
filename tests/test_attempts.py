"""Direct tests for generic attempt lifecycle authority."""
from __future__ import annotations
from dataclasses import replace
import copy
import subprocess
import sys
import unittest
from repository_intelligence import attempts
from repository_intelligence.attempts import AccessPlanes,AttemptEligibility
from repository_intelligence.errors import DuplicateAttemptError,ValidationError
from repository_intelligence.harness import Harness
from repository_intelligence.qualification import AuthoredEvidencePredicate, QualificationAuthority, QualificationObligation
from repository_intelligence.scope import ScopeGrant
from repository_intelligence.security import AttemptCleanupObservation, CacheResetObservation

class AttemptLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.harness=Harness("attempt-planes")
        self.task=self.harness.bind("task-source","task-material","config-a","task-generation")
        self.provider=self.harness.bind("provider-source","provider-material","config-a","provider-generation")
        self.retrieval=self.harness.bind("retrieval-source","retrieval-material","config-a","retrieval-generation")
        self.scope=ScopeGrant.accept({"grant_id":"edit-grant","source_binding":self.task,"configuration_id":"config-a","registry_id":"registry-a","resolution_id":"resolution-a","operations":[{"operation":"modify","path":"src/example.py"}],"preconditions":{"branch":"candidate"},"destinations":["working-tree"]},self.task)
        self.planes=AccessPlanes(self.task,self.provider,self.retrieval,self.scope)
        self.eligibility=AttemptEligibility("cold",True,True)
        self.values=dict(benchmark_id="benchmark-a",condition_id="condition-a",corpus_id="corpus-a",case_id="case-a",task_id="task-a",access_planes=self.planes,eligibility=self.eligibility,configuration_id="config-a",schedule_block_id="block-a",scheduled_at=10)
    def test_access_planes_reject_collapsed_sources_and_bind_finite_edit_grant(self):
        planes=AccessPlanes(self.task,self.provider,self.retrieval,self.scope)
        self.assertIs(planes.edit_scope,self.scope)
        with self.assertRaisesRegex(ValidationError,"distinct"):
            AccessPlanes(self.task,self.task,self.retrieval,self.scope)
        foreign=Harness("foreign-issuer").bind("task-source","task-material","config-a","task-generation")
        foreign_scope=ScopeGrant.accept({"grant_id":"foreign-edit","source_binding":foreign,"configuration_id":"config-a","registry_id":"registry-a","resolution_id":"resolution-a","operations":[{"operation":"modify","path":"src/example.py"}],"preconditions":{},"destinations":["working-tree"]},foreign)
        with self.assertRaisesRegex(ValidationError,"issuer"):
            AccessPlanes(self.task,self.provider,self.retrieval,foreign_scope)
    def test_scoring_eligibility_requires_verified_cache_state(self):
        self.assertTrue(AttemptEligibility("cold",True,True).scoring_eligible)
        for values in (("unknown",False,True),("warm",False,True),("invalid",True,False)):
            with self.subTest(values=values),self.assertRaises(ValidationError):
                AttemptEligibility(*values)
    def test_duplicate_allocation_rejected_without_history_mutation(self):
        ledger=attempts.AttemptLedger(); first=ledger.allocate(**self.values)
        with self.assertRaisesRegex(DuplicateAttemptError,"rejected atomically"):ledger.allocate(**self.values)
        self.assertEqual(ledger.records,(first,)); self.assertEqual(ledger.history,(first,))
    def test_linked_rerun_retains_original_terminal_evidence(self):
        ledger=attempts.AttemptLedger(); original=ledger.allocate(**self.values)
        with self.assertRaisesRegex(ValidationError,"terminal attempt"):ledger.rerun(original.attempt_id)
        terminal=ledger.finish(ledger.start(original.attempt_id,observed_at=11).attempt_id,status="crashed",termination="crashed",observed_at=12,disposition="retained failure",evidence_refs=("evidence-a",)); rerun=ledger.rerun(terminal.attempt_id,scheduled_at=13)
        self.assertEqual(rerun.retry_of,terminal.attempt_id); self.assertEqual(ledger.records[0],terminal); self.assertEqual(ledger.records[0].evidence_refs,("evidence-a",))
        with self.assertRaisesRegex(ValidationError,"cannot be rewritten"):ledger.finish(terminal.attempt_id,status="completed",termination="normal",observed_at=14,disposition="rewrite")
        self.assertEqual([record.status for record in ledger.history],["scheduled","started","crashed","scheduled"])
    def test_configuration_must_match_authenticated_binding(self):
        with self.assertRaisesRegex(ValidationError,"configuration_id must equal"):attempts.AttemptLedger().allocate(**{**self.values,"configuration_id":"config-b"})
    def test_lifecycle_rejects_time_and_terminal_inconsistency(self):
        ledger=attempts.AttemptLedger(); record=ledger.allocate(**self.values)
        with self.assertRaisesRegex(ValidationError,"after scheduled"):ledger.start(record.attempt_id,observed_at=10)
        started=ledger.start(record.attempt_id,observed_at=11)
        with self.assertRaisesRegex(ValidationError,"integer"):
            replace(started,started_at=10.5)
        with self.assertRaisesRegex(ValidationError,"terminal status and termination"):
            ledger.finish(started.attempt_id,status="completed",termination="crashed",observed_at=12,disposition="impossible")
    def test_retry_budget_applies_to_complete_root_lineage(self):
        ledger=attempts.AttemptLedger(retry_budget=1); root=ledger.allocate(**self.values)
        ledger.start(root.attempt_id,observed_at=11); ledger.finish(root.attempt_id,status="crashed",termination="crashed",observed_at=12,disposition="failure")
        retry=ledger.rerun(root.attempt_id,scheduled_at=13)
        with self.assertRaisesRegex(ValidationError,"root retry budget"):
            ledger.rerun(root.attempt_id,scheduled_at=14)
        ledger.start(retry.attempt_id,observed_at=14); ledger.finish(retry.attempt_id,status="crashed",termination="crashed",observed_at=15,disposition="failure")
        with self.assertRaisesRegex(ValidationError,"root retry budget"):
            ledger.rerun(retry.attempt_id,scheduled_at=16)
    def test_abrupt_exit_does_not_persist_allocation_into_fresh_process(self):
        allocate = (
            "import os; from repository_intelligence.attempts import AttemptLedger; "
            "from repository_intelligence.harness import Harness; "
            "b=Harness('restart-proof').bind('source','material','config','generation'); "
            "from repository_intelligence.scope import ScopeGrant; from repository_intelligence.attempts import AccessPlanes,AttemptEligibility; "
            "p=Harness('restart-proof').bind('provider','provider-material','config','provider-generation'); "
            "v=Harness('restart-proof').bind('retrieval','retrieval-material','config','retrieval-generation'); "
            "s=ScopeGrant.accept({'grant_id':'grant','source_binding':b,'configuration_id':'config','registry_id':'registry','resolution_id':'resolution','operations':[{'operation':'modify','path':'src/x.py'}],'preconditions':{},'destinations':['working-tree']},b); "
            "r=AttemptLedger().allocate(benchmark_id='benchmark',condition_id='condition',"
            "corpus_id='corpus',case_id='case',task_id='task',access_planes=AccessPlanes(b,p,v,s),eligibility=AttemptEligibility('cold',True,True),"
            "configuration_id='config',schedule_block_id='block',scheduled_at=1); "
            "os.write(1,r.attempt_id.encode())"
        )
        interrupted=subprocess.run(
            [sys.executable,"-c",allocate+"; os._exit(17)"],
            check=False,capture_output=True,text=True,
        )
        restarted=subprocess.run(
            [sys.executable,"-c",allocate],
            check=True,capture_output=True,text=True,
        )
        self.assertEqual(interrupted.returncode,17)
        self.assertEqual(interrupted.stdout,"attempt-0001")
        self.assertEqual(restarted.stdout,"attempt-0001")

    def test_cleanup_observation_is_exact_post_terminal_history(self):
        ledger = attempts.AttemptLedger()
        scheduled = ledger.allocate(**self.values)
        started = ledger.start(scheduled.attempt_id, observed_at=11)
        finished = ledger.finish(started.attempt_id, status="crashed", termination="crashed", observed_at=12, disposition="failure", evidence_refs=("failure-a",))
        self.assertEqual((finished.cleanup_observation_id, finished.cleanup_disposition), (None, "unobserved"))
        observation = self.harness.observe_attempt_cleanup(finished.attempt_id, self.task, observed_at=13, disposition="residue", candidate_claims={"cleanup": "clean"})
        self.assertTrue(observation.is_authenticated())
        cleaned = ledger.record_cleanup(finished.attempt_id, observation)
        self.assertEqual((cleaned.cleanup_observation_id, cleaned.cleanup_observed_at, cleaned.cleanup_disposition), (observation.observation_id, 13, "residue"))
        self.assertEqual(cleaned.evidence_refs, ("failure-a",))
        self.assertIs(ledger.history[-2], finished)
        self.assertEqual(ledger.history[-2].cleanup_disposition, "unobserved")
        retry = ledger.rerun(finished.attempt_id, scheduled_at=14)
        self.assertEqual(retry.cleanup_disposition, "unobserved")
        self.assertEqual(ledger.records[0], cleaned)

    def test_cleanup_identity_time_forgery_and_replay_fail_atomically(self):
        ledger = attempts.AttemptLedger()
        scheduled = ledger.allocate(**self.values)
        early_harness = Harness("early-cleanup")
        early_binding = early_harness.bind("task-source", "task-material", "config-a", "task-generation")
        early = early_harness.observe_attempt_cleanup(scheduled.attempt_id, early_binding, observed_at=13, disposition="clean")
        before = ledger.history
        with self.assertRaises(ValidationError):
            ledger.record_cleanup(scheduled.attempt_id, early)
        self.assertEqual(ledger.history, before)
        ledger.start(scheduled.attempt_id, observed_at=11)
        finished = ledger.finish(scheduled.attempt_id, status="completed", termination="normal", observed_at=12, disposition="terminal")
        valid = self.harness.observe_attempt_cleanup(finished.attempt_id, self.task, observed_at=13, disposition="clean")
        with self.assertRaises(ValidationError):
            self.harness.observe_attempt_cleanup(finished.attempt_id, self.task, observed_at=14, disposition="clean")
        wrong_source = replace(valid, binding=self.provider)
        wrong_attempt = replace(valid, attempt_id="another-attempt")
        same_time = replace(valid, observed_at=12)
        foreign_harness = Harness("foreign-cleanup")
        foreign_binding = foreign_harness.bind("task-source", "task-material", "config-a", "task-generation")
        foreign = foreign_harness.observe_attempt_cleanup(finished.attempt_id, foreign_binding, observed_at=13, disposition="clean")
        direct = AttemptCleanupObservation("direct", finished.attempt_id, self.task, 13, "clean")
        rejected = (wrong_source, wrong_attempt, same_time, foreign, direct, copy.copy(valid), {"disposition": "clean"})
        before = ledger.history
        for observation in rejected:
            with self.subTest(observation=observation), self.assertRaises(ValidationError):
                ledger.record_cleanup(finished.attempt_id, observation)
            self.assertEqual(ledger.history, before)
        with self.assertRaises(ValidationError):
            replace(finished, cleanup_observation_id="fake", cleanup_observed_at=12, cleanup_disposition="clean")
        with self.assertRaises(ValidationError):
            replace(finished, cleanup_observation_id="fake", cleanup_observed_at=13, cleanup_disposition="clean", last_observed_at=13)
        with self.assertRaises(ValidationError):
            replace(scheduled, cleanup_observation_id="fake", cleanup_observed_at=13, cleanup_disposition="clean")
        accepted = ledger.record_cleanup(finished.attempt_id, valid)
        with self.assertRaises(ValidationError):
            ledger.record_cleanup(finished.attempt_id, valid)
        self.assertEqual(ledger.records[0], accepted)

    def test_cache_reset_scoring_requires_independent_complete_exact_evidence(self):
        ledger=attempts.AttemptLedger()
        scheduled=ledger.allocate(**self.values)
        cache=self.harness.observe_cache_reset(scheduled.attempt_id,self.task,observed_at=11,cache_state="cold",reset_disposition="complete",candidate_claims={"cache_state":"warm"})
        self.assertTrue(cache.is_authenticated())
        with self.assertRaises(ValidationError):
            self.harness.observe_cache_reset(scheduled.attempt_id,self.task,observed_at=11,cache_state="cold",reset_disposition="complete")
        ledger.start(scheduled.attempt_id,observed_at=12)
        finished=ledger.finish(scheduled.attempt_id,status="completed",termination="normal",observed_at=13,disposition="terminal",evidence_refs=("execution-a",))
        cleanup=self.harness.observe_attempt_cleanup(finished.attempt_id,self.task,observed_at=14,disposition="clean")
        record=ledger.record_cleanup(finished.attempt_id,cleanup)
        evidence=self.harness.observe_execution(evidence_id="execution-a",binding=self.task,command_id="command-a",test_id="test-a",artifact_id="artifact-a",status="passed",observed=True,complete=True,terminal=True,evidence_session_id="session-a",exit_code=0)
        predicate=AuthoredEvidencePredicate("predicate-a",self.task,"command-a","test-a","artifact-a")
        authority=QualificationAuthority((QualificationObligation("obligation-a",predicate),))
        score=lambda r,c,e,a=authority: attempts.assess_scoring(ledger,r,c,e,a)
        self.assertEqual(score(record,cache,(evidence,)).disposition,"eligible")
        with self.assertRaises(ValidationError):
            score(replace(record,eligibility=AttemptEligibility("cold",False,False)),cache,(evidence,))
        self.assertEqual(score(record,None,(evidence,)).reasons,("cache_unverified",))
        self.assertEqual(score(record,cache,()).disposition,"ineligible")
        self.assertEqual(score(record,cache,(evidence,evidence)).disposition,"ineligible")
        self.assertEqual(score(record,cache,(replace(evidence,evidence_id="extra"),)).disposition,"ineligible")
        with self.assertRaises(ValidationError):
            score(replace(record,evidence_refs=()),cache,(evidence,))
        self.assertIn("execution_not_complete_passing",score(record,cache,(replace(evidence,complete=False),)).reasons)
        self.assertEqual(score(record,copy.copy(cache),(evidence,)).reasons,("cache_unverified",))
        with self.assertRaises(ValidationError):
            score(replace(record,started_at=11),cache,(evidence,))
        with self.assertRaises(ValidationError):
            score(replace(record,scheduled_at=9),cache,(evidence,))
        self.assertIs(ledger.records[0],record)
        self.assertIn("execution_not_complete_passing",score(record,cache,(self.harness.observe_execution(evidence_id="execution-a",binding=self.task,command_id="command-a",test_id="test-a",artifact_id="artifact-a",status="passed",observed=True,complete=False,terminal=True,evidence_session_id="session-a",exit_code=0),)).reasons)
        self.assertIn("qualification_not_satisfied",score(record,cache,(evidence,),QualificationAuthority(())).reasons)
        mismatched_predicate=AuthoredEvidencePredicate("wrong",self.task,"command-other","test-a","artifact-a")
        self.assertIn("qualification_not_satisfied",score(record,cache,(evidence,),QualificationAuthority((QualificationObligation("wrong",mismatched_predicate),))).reasons)
        unclean=ledger.rerun(record.attempt_id,scheduled_at=15)
        self.assertEqual(score(unclean,cache,(evidence,)).disposition,"ineligible")
        mistimed_cache=self.harness.observe_cache_reset(unclean.attempt_id,self.task,observed_at=15,cache_state="cold",reset_disposition="complete")
        ledger.start(unclean.attempt_id,observed_at=17)
        mistimed_finished=ledger.finish(unclean.attempt_id,status="completed",termination="normal",observed_at=18,disposition="terminal",evidence_refs=("execution-a",))
        mistimed_cleanup=self.harness.observe_attempt_cleanup(unclean.attempt_id,self.task,observed_at=19,disposition="clean")
        mistimed_record=ledger.record_cleanup(mistimed_finished.attempt_id,mistimed_cleanup)
        self.assertIn("cache_reset_wrong_boundary",score(mistimed_record,mistimed_cache,(evidence,)).reasons)
        with self.assertRaises(ValidationError):
            score(replace(mistimed_record,scheduled_at=14),mistimed_cache,(evidence,))
        with self.assertRaises(ValidationError):
            self.harness.observe_cache_reset("another-attempt",self.task,observed_at=11,cache_state="impossible",reset_disposition="complete")
        direct=CacheResetObservation("direct",record.attempt_id,self.task,11,"cold","complete")
        self.assertIn("cache_unverified",score(record,direct,(evidence,)).reasons)
        stale=self.harness.observe_cache_reset("another-attempt",self.provider,observed_at=11,cache_state="unknown",reset_disposition="incomplete")
        stale_reasons=score(record,stale,(evidence,)).reasons
        self.assertIn("cache_identity_mismatch",stale_reasons)
        self.assertIn("cache_reset_incomplete",stale_reasons)
        self.assertIn("cache_state_mismatch",stale_reasons)
if __name__=="__main__":unittest.main()
