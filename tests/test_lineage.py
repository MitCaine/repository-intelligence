"""Exact real-Git to attempt/execution/qualification identity joins."""
from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import subprocess
import tempfile
import unittest

from repository_intelligence.acquisition import GitSourceObserver
from repository_intelligence.attempts import AccessPlanes, AttemptEligibility, AttemptLedger
from repository_intelligence.errors import ValidationError
from repository_intelligence.harness import Harness
from repository_intelligence.lineage import assess_lineage
from repository_intelligence.qualification import AuthoredEvidencePredicate, QualificationAuthority, QualificationObligation
from repository_intelligence.scope import ScopeGrant


class LineageTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/"source"
        self.root.mkdir()
        self.git("init","-q")
        (self.root/"source.txt").write_text("source\n",encoding="utf-8")
        self.git("add","source.txt")
        self.git("-c","user.name=Lineage Test","-c","user.email=lineage@example.invalid","commit","-qm","initial")
        revision=self.git("rev-parse","HEAD").stdout.strip()
        tree=self.git("rev-parse","HEAD^{tree}").stdout.strip()
        self.pin={"source_id":"source-a","repository":"example/source","revision":revision,"language":"Rust","source_state_mode":"immutable_committed","configuration_id":"config-a"}
        self.observer=GitSourceObserver(self.pin,self.root)
        self.observation=self.observer.observe()
        self.harness=Harness("lineage-harness")
        self.task=self.harness.bind("source-a",tree,"config-a",revision)
        provider=self.harness.bind("provider-source","provider-material","config-a","provider-generation")
        retrieval=self.harness.bind("retrieval-source","retrieval-material","config-a","retrieval-generation")
        scope=ScopeGrant.accept({"grant_id":"grant-a","source_binding":self.task,"configuration_id":"config-a","registry_id":"registry-a","resolution_id":"resolution-a","operations":[{"operation":"modify","path":"src/example.py"}],"preconditions":{},"destinations":["working-tree"]},self.task)
        self.planes=AccessPlanes(self.task,provider,retrieval,scope)
        self.ledger=AttemptLedger()
        self.scheduled=self.ledger.allocate(benchmark_id="benchmark-a",condition_id="condition-a",corpus_id="corpus-a",case_id="case-a",task_id="task-a",access_planes=self.planes,eligibility=AttemptEligibility("cold",True,True),configuration_id="config-a",schedule_block_id="block-a",scheduled_at=10)
        predicate=AuthoredEvidencePredicate("predicate-a",self.task,"command-a","test-a","artifact-a")
        self.authority=QualificationAuthority((QualificationObligation("obligation-a",predicate),))

    def git(self,*args):
        return subprocess.run(("git","-C",str(self.root),*args),check=True,capture_output=True,text=True)

    def finished(self):
        self.ledger.start(self.scheduled.attempt_id,observed_at=11)
        return self.ledger.finish(self.scheduled.attempt_id,status="completed",termination="normal",observed_at=12,disposition="terminal",evidence_refs=("execution-a",))

    def evidence(self,**overrides):
        values=dict(evidence_id="execution-a",binding=self.task,command_id="command-a",test_id="test-a",artifact_id="artifact-a",status="passed",observed=True,complete=True,terminal=True,evidence_session_id="session-a",exit_code=0,attempt_id=self.scheduled.attempt_id)
        values.update(overrides)
        return self.harness.observe_execution(**values)

    def assess(self,record,evidence,authority=None):
        return assess_lineage(self.observer,self.observation,self.ledger,record,evidence,authority or self.authority)

    def test_revalidates_git_and_distinct_planes_without_claiming_readiness(self):
        pending=self.assess(self.scheduled,())
        self.assertEqual((pending.status,pending.reasons,pending.execution_authorized,pending.scoring_authorized),("pending",("execution_pending",),False,False))
        record=self.finished()
        evidence=self.evidence()
        complete=self.assess(record,(evidence,))
        self.assertEqual((complete.status,complete.reasons,complete.execution_authorized,complete.scoring_authorized),("consistent",(),False,False))
        (self.root/"untracked.txt").write_text("changed",encoding="utf-8")
        with self.assertRaises(ValidationError):
            self.assess(record,(evidence,))

    def test_rejects_forged_stale_cross_attempt_and_unqualified_evidence(self):
        record=self.finished()
        evidence=self.evidence()
        for items in ((),(evidence,evidence),(copy.copy(evidence),),(self.evidence(attempt_id="other-attempt"),),(self.evidence(binding=self.planes.provider_source),),(self.evidence(evidence_id="extra"),)):
            with self.subTest(items=items):
                self.assertEqual(self.assess(record,items).status,"invalid")
        with self.assertRaises(ValidationError):
            self.assess(replace(record,scheduled_at=9),(evidence,))
        with self.assertRaises(ValidationError):
            assess_lineage(GitSourceObserver(self.pin,self.root),self.observation,self.ledger,record,(evidence,),self.authority)
        with self.assertRaises(ValidationError):
            assess_lineage(self.observer,self.observation.as_dict(),self.ledger,record,(evidence,),self.authority)
        wrong=AuthoredEvidencePredicate("wrong",self.task,"other-command","test-a","artifact-a")
        self.assertEqual(self.assess(record,(evidence,),QualificationAuthority((QualificationObligation("wrong",wrong),))).status,"invalid")

    def test_wrong_git_tree_or_configuration_cannot_join_harness_binding(self):
        record=self.finished()
        evidence=self.evidence()
        self.assertEqual(self.assess(record,(evidence,)).status,"consistent")
        mismatched=self.harness.bind("source-a","0"*40,"config-a",self.pin["revision"])
        planes=AccessPlanes(mismatched,self.planes.provider_source,self.planes.retrieval_source,ScopeGrant.accept({"grant_id":"wrong-grant","source_binding":mismatched,"configuration_id":"config-a","registry_id":"registry-a","resolution_id":"resolution-a","operations":[{"operation":"modify","path":"src/example.py"}],"preconditions":{},"destinations":["working-tree"]},mismatched))
        wrong_ledger=AttemptLedger()
        wrong_record=wrong_ledger.allocate(benchmark_id="benchmark-a",condition_id="condition-a",corpus_id="corpus-a",case_id="case-a",task_id="task-a",access_planes=planes,eligibility=AttemptEligibility("cold",True,True),configuration_id="config-a",schedule_block_id="block-a",scheduled_at=10)
        decision=assess_lineage(self.observer,self.observation,wrong_ledger,wrong_record,(),self.authority)
        self.assertEqual((decision.status,decision.reasons),("invalid",("source_materialization_mismatch",)))


if __name__=="__main__": unittest.main()
