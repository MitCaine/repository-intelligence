"""Direct tests for generic attempt lifecycle authority."""
from __future__ import annotations
from dataclasses import replace
import subprocess
import sys
import unittest
from repository_intelligence import attempts
from repository_intelligence.attempts import AccessPlanes,AttemptEligibility
from repository_intelligence.errors import DuplicateAttemptError,ValidationError
from repository_intelligence.harness import Harness
from repository_intelligence.scope import ScopeGrant

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
if __name__=="__main__":unittest.main()
