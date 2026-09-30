"""Exercise the portable queue template without contacting a Codex session."""

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / 'docs/skill-templates/capsule-queue/scripts/run_and_queue.py'
SPEC = importlib.util.spec_from_file_location('ri_queue_template', SCRIPT)
queue = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(queue)
THREAD = '01234567-89ab-cdef-0123-456789abcdef'


class QueueHelperTests(unittest.TestCase):
    def config(self, root):
        return {'job_dir': str(root), 'cwd': str(root), 'thread': THREAD,
                'label': 'Gate', 'follow_up': 'Inspect evidence',
                'timeout_seconds': 3, 'command': ['example-command']}

    def test_deadline_rejects_nan_and_infinity_before_starting_job(self):
        for value in ('nan', 'inf', '-inf', '0'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as raw, \
                    mock.patch.object(queue.subprocess, 'run') as run, \
                    mock.patch.object(queue.subprocess, 'Popen') as popen:
                args = ['--thread', THREAD, '--cwd', raw, '--job-dir', str(Path(raw) / 'job'),
                        '--label', 'Gate', '--follow-up', 'Check', f'--timeout-seconds={value}',
                        '--', 'example-command']
                with self.assertRaises(SystemExit):
                    queue.launch(args)
                run.assert_not_called()
                popen.assert_not_called()

    def test_default_deadline_is_finite_and_capability_check_is_bounded(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            helper = subprocess.CompletedProcess([], 0, '--thread --message', '')
            process = mock.Mock(pid=123)
            with mock.patch.object(queue.subprocess, 'run', return_value=helper) as run, \
                    mock.patch.object(queue.subprocess, 'Popen', return_value=process):
                queue.launch(['--thread', THREAD, '--cwd', raw,
                              '--job-dir', str(root / 'job'), '--label', 'Gate',
                              '--follow-up', 'Check', '--', 'example-command'])
            config = json.loads((root / 'job' / 'config.json').read_text())
            self.assertEqual(config['timeout_seconds'], queue.DEFAULT_TIMEOUT_SECONDS)
            self.assertEqual(run.call_args.kwargs['timeout'], 10)

    def test_signal_termination_and_failed_delivery_are_separate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            process = mock.Mock(pid=123, wait=mock.Mock(return_value=-15))
            rejected = subprocess.CompletedProcess([], 7, 'not delivered')
            with mock.patch.object(queue.subprocess, 'Popen', return_value=process), \
                    mock.patch.object(queue, 'terminate_group', return_value=(-15, True)), \
                    mock.patch.object(queue.subprocess, 'run', return_value=rejected) as run:
                queue.watch(self.config(root))
            status = json.loads((root / 'status.json').read_text())
            delivery = json.loads((root / 'delivery.json').read_text())
            self.assertEqual(status['outcome'], 'signal_terminated')
            self.assertEqual(status['exit_code'], -15)
            self.assertEqual(delivery['state'], 'rejected_by_cli')
            self.assertEqual(run.call_count, 1)

    def test_timeout_is_distinct_from_signal_termination(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            process = mock.Mock(pid=123)
            process.wait.side_effect = [subprocess.TimeoutExpired('example-command', 3), -15]
            with mock.patch.object(queue.subprocess, 'Popen', return_value=process), \
                    mock.patch.object(queue, 'terminate_group', return_value=(-15, True)) as cleanup, \
                    mock.patch.object(queue, 'notify'):
                queue.watch(self.config(root))
            status = json.loads((root / 'status.json').read_text())
            self.assertEqual(status['outcome'], 'timeout')
            self.assertEqual(status['exit_code'], -15)
            cleanup.assert_called_once_with(process)
            self.assertTrue(status['cleanup_confirmed'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups required')
    def test_timeout_stops_term_ignoring_descendant_writer(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            child = root / 'child.py'
            child.write_text('import signal,time\nfrom pathlib import Path\n'
                             'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                             'while True:\n Path("heartbeat").write_text(str(time.time_ns()))\n time.sleep(.02)\n')
            config = self.config(root)
            config['command'] = [sys.executable, '-c',
                'import subprocess,sys,time; subprocess.Popen([sys.executable,"child.py"]); time.sleep(60)']
            config['timeout_seconds'] = 0.8
            with mock.patch.object(queue, 'notify'), \
                    mock.patch.object(queue, 'TERM_GRACE_SECONDS', 0.2):
                queue.watch(config)
            status = json.loads((root / 'status.json').read_text())
            self.assertEqual(status['outcome'], 'timeout')
            self.assertEqual(status['exit_code'], -15)
            before = (root / 'heartbeat').read_text()
            time.sleep(0.15)
            self.assertEqual((root / 'heartbeat').read_text(), before)

    def test_unresolved_cleanup_is_not_claimed_terminated(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            process = mock.Mock(pid=123)
            process.wait.side_effect = subprocess.TimeoutExpired('command', 3)
            with mock.patch.object(queue.subprocess, 'Popen', return_value=process), \
                    mock.patch.object(queue, 'terminate_group', return_value=(-15, False)), \
                    mock.patch.object(queue, 'notify'):
                queue.watch(self.config(root))
            status = json.loads((root / 'status.json').read_text())
            self.assertFalse(status['cleanup_confirmed'])
            self.assertIn('cleanup unresolved', status['detail'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups required')
    def test_abnormal_leader_exit_stops_descendant(self):
        for ending, outcome, code in [('sys.exit(7)', 'failure', 7),
                ('sys.exit(0)', 'success', 0),
                ('os.kill(os.getpid(),15)', 'signal_terminated', -15)]:
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                (root / 'child.py').write_text('import signal,time\nfrom pathlib import Path\n'
                    'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                    'while True:\n Path("heartbeat").write_text(str(time.time_ns()))\n time.sleep(.02)\n')
                config = self.config(root)
                config['command'] = [sys.executable, '-c',
                    'import os,sys,subprocess,time; subprocess.Popen([sys.executable,"child.py"]); time.sleep(.5); ' + ending]
                with mock.patch.object(queue, 'notify'), \
                        mock.patch.object(queue, 'TERM_GRACE_SECONDS', 0.2):
                    queue.watch(config)
                status = json.loads((root / 'status.json').read_text())
                self.assertEqual((status['outcome'], status['exit_code']), (outcome, code))
                before = (root / 'heartbeat').read_text()
                time.sleep(.1)
                self.assertEqual((root / 'heartbeat').read_text(), before)

    def test_cleanup_error_preserves_known_command_outcome(self):
        for code, outcome in [(7, 'failure'), (-15, 'signal_terminated'), (0, 'success')]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                process = mock.Mock(pid=123, wait=mock.Mock(return_value=code))
                with mock.patch.object(queue.subprocess, 'Popen', return_value=process), \
                        mock.patch.object(queue, 'group_exists', return_value=True), \
                        mock.patch.object(queue, 'terminate_group', side_effect=OSError('cleanup fault')), \
                        mock.patch.object(queue, 'notify'):
                    queue.watch(self.config(root))
                status = json.loads((root / 'status.json').read_text())
                self.assertEqual((status['outcome'], status['exit_code']), (outcome, code))
                self.assertFalse(status['cleanup_confirmed'])
                self.assertIn('cleanup fault', status['cleanup_error'])

    def test_redelivery_reuses_terminal_result_without_rerunning_job(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.config(root)
            queue.save_json(root / 'status.json', {'outcome': 'success'})
            queue.save_json(root / 'delivery.json', {'state': 'rejected_by_cli', 'attempts': 1})
            with mock.patch.object(queue.subprocess, 'Popen') as popen, \
                    mock.patch.object(queue.subprocess, 'run', return_value=
                                      subprocess.CompletedProcess([], 0, 'queued')) as run:
                result = queue.notify(config, recovery=True)
            self.assertEqual(result['state'], 'accepted_by_cli')
            self.assertEqual(result['attempts'], 2)
            popen.assert_not_called()
            self.assertEqual(run.call_count, 1)
            with self.assertRaisesRegex(ValueError, 'do not resend'):
                queue.notify(config, recovery=True)


if __name__ == '__main__':
    unittest.main()
