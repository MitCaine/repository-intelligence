"""Direct tests for generic attempt lifecycle authority."""
from __future__ import annotations
import unittest
from repository_intelligence import attempts
from repository_intelligence.errors import DuplicateAttemptError,ValidationError
from repository_intelligence.harness import Harness

class AttemptLifecycleTests(unittest.TestCase):
    def setUp(self):
        binding=Harness("attempt-test").bind("source-a","material-a","config-a","generation-a")
        self.values=dict(benchmark_id="benchmark-a",condition_id="condition-a",corpus_id="corpus-a",case_id="case-a",task_id="task-a",source_binding=binding,configuration_id="config-a",schedule_block_id="block-a")
    def test_duplicate_allocation_rejected_without_history_mutation(self):
        ledger=attempts.AttemptLedger(); first=ledger.allocate(**self.values)
        with self.assertRaisesRegex(DuplicateAttemptError,"rejected atomically"):ledger.allocate(**self.values)
        self.assertEqual(ledger.records,(first,)); self.assertEqual(ledger.history,(first,))
    def test_linked_rerun_retains_original_terminal_evidence(self):
        ledger=attempts.AttemptLedger(); original=ledger.allocate(**self.values)
        with self.assertRaisesRegex(ValidationError,"terminal attempt"):ledger.rerun(original.attempt_id)
        terminal=ledger.finish(ledger.start(original.attempt_id).attempt_id,status="crashed",disposition="retained failure",evidence_refs=("evidence-a",)); rerun=ledger.rerun(terminal.attempt_id)
        self.assertEqual(rerun.retry_of,terminal.attempt_id); self.assertEqual(ledger.records[0],terminal); self.assertEqual(ledger.records[0].evidence_refs,("evidence-a",))
        with self.assertRaisesRegex(ValidationError,"cannot be rewritten"):ledger.finish(terminal.attempt_id,status="completed",disposition="rewrite")
        self.assertEqual([record.status for record in ledger.history],["scheduled","started","crashed","scheduled"])
    def test_configuration_must_match_authenticated_binding(self):
        with self.assertRaisesRegex(ValidationError,"configuration_id must equal"):attempts.AttemptLedger().allocate(**{**self.values,"configuration_id":"config-b"})
if __name__=="__main__":unittest.main()
