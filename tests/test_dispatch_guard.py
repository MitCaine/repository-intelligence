"""Synthetic adapter transitions, not live host wake or delivery proof."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from repository_intelligence.dispatch_guard import DispatchError, decide


class DispatchGuardTests(unittest.TestCase):
    def setUp(self):
        self.expected = dict(assignment='task-533', attempt='correction-06', operation='resume', worker='original-worker')
        self.observed = dict(self.expected, state='active', accepted=True, evidence='existing/native-followup-and-state-record')

    def test_planned_handoff_cannot_enter_running_or_wait(self):
        # A dispatcher transition must be selected from the decision, not from
        # existence of a correction document (the reported old assumption).
        for state in ('planned', 'delivered', 'unknown'):
            observation = dict(self.observed, state=state)
            result = decide(self.expected, observation)
            self.assertEqual(result['action'], 'reconcile')
            self.assertFalse(result['may_wait'])
            self.assertFalse(result['may_mark_running'])
            self.assertFalse(result['may_dispatch'])
        self.assertFalse(decide(self.expected, None)['may_wait'])

    def test_accepted_launch_and_resumption_controls(self):
        result = decide(self.expected, self.observed)
        self.assertEqual(result['action'], 'wait')
        self.assertTrue(result['may_mark_running'])
        expected = dict(assignment='new-task', attempt='new-attempt', operation='launch')
        observed = dict(expected, worker='new-worker', accepted=True, state='accepted', evidence='native/spawn-result')
        result = decide(expected, observed)
        self.assertTrue(result['may_wait'])
        self.assertFalse(result['may_mark_running'])

    def test_mismatched_and_stale_acceptance_refused(self):
        for key, value in [('assignment', 'other'), ('attempt', 'correction-05'), ('operation', 'launch'), ('worker', 'other')]:
            with self.subTest(key=key), self.assertRaises(DispatchError):
                decide(self.expected, dict(self.observed, **{key: value}))
        for change in [dict(accepted=False), dict(evidence=''), dict(worker='')]:
            with self.assertRaises(DispatchError):
                decide(self.expected, dict(self.observed, **change))

    def test_lost_reply_reconciliation_never_launches_duplicate(self):
        self.assertEqual(decide(self.expected, None)['action'], 'reconcile')
        active = decide(self.expected, self.observed)
        self.assertEqual(active['worker'], 'original-worker')
        self.assertEqual(active['action'], 'wait')
        terminal = decide(self.expected, dict(self.observed, state='terminal'))
        self.assertEqual(terminal['action'], 'consume')
        self.assertFalse(terminal['may_wait'])
        for state in ('absent', 'rejected'):
            result = decide(self.expected, dict(self.observed, state=state, accepted=False))
            self.assertEqual(result['action'], 'controller_decision')
            self.assertFalse(result['may_dispatch'])

    def test_synthetic_dispatcher_checks_before_running_and_wait(self):
        def transition(observation, wait):
            # Consumer-owned transition fixture; no actual host or checkpoint.
            decision = decide(self.expected, observation)
            record = {'phase': 'handoff_ready'}
            if decision['may_mark_running']:
                record['phase'] = 'running'
            if decision['may_wait']:
                wait(decision['worker'])
            return record
        calls = []
        record = transition(dict(self.observed, state='planned'), calls.append)
        self.assertEqual(record['phase'], 'handoff_ready')
        self.assertEqual(calls, [])
        record = transition(self.observed, calls.append)
        self.assertEqual(record['phase'], 'running')
        self.assertEqual(calls, ['original-worker'])
        # Distinguishing negative: the reported old assumption (handoff exists
        # implies running/wait) fails the SAME independently expected boundary.
        def assert_unlaunched(record, waits):
            self.assertNotEqual(record['phase'], 'running')
            self.assertEqual(waits, [])
        assert_unlaunched({'phase': 'handoff_ready'}, [])
        with self.assertRaises(AssertionError):
            assert_unlaunched({'phase': 'running'}, ['original-worker'])

    def test_public_cli_refuses_stale_input_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as raw:
            request = Path(raw)/'request.json'
            request.write_text(json.dumps(dict(expected=self.expected, observed=self.observed)))
            before = request.read_bytes()
            command = [sys.executable, '-m', 'repository_intelligence.dispatch_guard', '--request', str(request)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['may_wait'])
            self.assertEqual(request.read_bytes(), before)
            self.assertEqual(list(Path(raw).iterdir()), [request])
            request.write_text(json.dumps(dict(expected=self.expected, observed=dict(self.observed, attempt='old'))))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)['may_wait'])


if __name__ == '__main__':
    unittest.main()
