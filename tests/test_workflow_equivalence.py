"""Bounded equivalence/stage examples; these do not authenticate consumer receipts."""
import copy
import importlib.util
from pathlib import Path
import unittest

script = Path(__file__).resolve().parents[1] / 'docs/skill-templates/capsule-preflight/scripts/evidence_preflight.py'
spec = importlib.util.spec_from_file_location('workflow_checks', script)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class WorkflowEquivalenceTests(unittest.TestCase):
    def test_each_affected_input_invalidates_reuse_unknown_inputs_are_not_cacheable(self):
        inputs = {key: 'a' * 64 for key in checks.REUSE_INPUTS}
        self.assertTrue(checks.equivalent_inputs(inputs, copy.deepcopy(inputs)))
        for key in inputs:
            changed = {**inputs, key: 'b' * 64}
            self.assertFalse(checks.equivalent_inputs(inputs, changed))
            unknown = {**inputs, key: None}
            self.assertFalse(checks.equivalent_inputs(inputs, unknown))
        self.assertFalse(checks.equivalent_inputs({}, {}))

    def test_terminal_carries_only_unchanged_authenticated_exported_judgment(self):
        inputs = {key: 'a' * 64 for key in checks.REUSE_INPUTS}
        prior = {'verdict': 'PASS', 'receipt_sha256': 'b' * 64,
                 'requirements_sha256': 'c' * 64, 'inputs': inputs,
                 'evidence_sha256': 'e' * 64, 'policy_version': 'adopted-v1'}
        self.assertTrue(checks.carry_review(prior, inputs, 'c' * 64, evidence_sha256='e' * 64, policy_version='adopted-v1'))
        self.assertFalse(checks.carry_review(prior, {**inputs, 'code': 'd' * 64}, 'c' * 64, evidence_sha256='e' * 64, policy_version='adopted-v1'))
        self.assertFalse(checks.carry_review(prior, inputs, 'd' * 64, evidence_sha256='e' * 64, policy_version='adopted-v1'))
        for field in ('receipt_sha256', 'inputs', 'verdict', 'evidence_sha256', 'policy_version'):
            missing = dict(prior); missing.pop(field)
            self.assertFalse(checks.carry_review(missing, inputs, 'c' * 64, evidence_sha256='e' * 64, policy_version='adopted-v1'))

    def test_future_events_do_not_create_candidate_approval_cycle(self):
        obligations = [{'id': 'implementation', 'deadline_stage': 'candidate', 'satisfied_by': 'external', 'status': 'passed'},
                       {'id': 'live-control', 'deadline_stage': 'installed', 'satisfied_by': 'external', 'status': 'pending'},
                       {'id': 'branch-cleanup', 'deadline_stage': 'terminal', 'satisfied_by': 'external', 'status': 'pending'}]
        self.assertEqual(checks.validate_obligation_stage(obligations, 'candidate'),
                         ['branch-cleanup', 'live-control'])
        with self.assertRaises(checks.Blocked):
            checks.validate_obligation_stage(obligations, 'installed')
        obligations[1]['status'] = 'passed'
        self.assertEqual(checks.validate_obligation_stage(obligations, 'installed'), ['branch-cleanup'])
        with self.assertRaises(checks.Blocked):
            checks.validate_obligation_stage(obligations, 'terminal')
        obligations[2]['status'] = 'passed'
        self.assertEqual(checks.validate_obligation_stage(obligations, 'terminal'), [])

    def test_review_intake_distinguishes_external_from_review_discharge(self):
        obligation = {'id': 'standards', 'deadline_stage': 'candidate',
                      'satisfied_by': 'review', 'status': 'pending'}
        self.assertEqual(checks.validate_obligation_stage([obligation], 'candidate', phase='intake'), ['standards'])
        with self.assertRaises(checks.Blocked):
            checks.validate_obligation_stage([obligation], 'candidate')
        with self.assertRaises(checks.Blocked):
            checks.validate_obligation_stage([{**obligation, 'satisfied_by': 'external'}], 'candidate', phase='intake')
        with self.assertRaises(checks.Blocked):
            checks.validate_obligation_stage([{**obligation, 'supersedes': 'standards'}], 'candidate', phase='intake')
        with self.assertRaises(checks.Blocked):
            checks.validate_obligation_stage([{**obligation, 'status': 'failed'}], 'candidate', phase='intake')

    def test_terminal_cannot_inherit_changed_evidence_or_policy(self):
        inputs = {key: 'a' * 64 for key in checks.REUSE_INPUTS}
        prior = {'verdict': 'PASS', 'receipt_sha256': 'b' * 64,
                 'requirements_sha256': 'c' * 64, 'inputs': inputs,
                 'evidence_sha256': 'e' * 64, 'policy_version': 'adopted-v1'}
        self.assertFalse(checks.carry_review(prior, inputs, 'c' * 64,
            evidence_sha256='f' * 64, policy_version='adopted-v1'))
        self.assertFalse(checks.carry_review(prior, inputs, 'c' * 64,
            evidence_sha256='e' * 64, policy_version='adopted-v2'))
