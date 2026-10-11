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

    def test_malformed_bytes_are_diagnostic_and_command_status_is_unchanged(self):
        for descriptor, code in ((1, 0), (2, 7)):
            with self.subTest(descriptor=descriptor, code=code), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                executable = root / 'codex'
                executable.write_text(f'#!{Path(sys.executable).resolve()}\nimport os,sys\n'
                                      f'os.write({descriptor}, b"\\xff"); sys.exit({code})\n')
                executable.chmod(0o755)
                queue.save_json(root / 'status.json', {'outcome': 'success'})
                before = (root / 'status.json').read_bytes()
                with mock.patch.dict(os.environ, {'PATH': raw}):
                    delivery = queue.notify(self.config(root))
                self.assertEqual(delivery['state'], 'accepted_by_cli' if code == 0 else 'rejected_by_cli')
                self.assertIn('\\xff', (root / 'queue.log').read_text())
                self.assertEqual((root / 'status.json').read_bytes(), before)

    def test_malformed_capability_diagnostics_do_not_crash_discovery(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            executable = root / 'codex'
            executable.write_text(f'#!{Path(sys.executable).resolve()}\n'
                                  'import os\nos.write(1, b"--thread --message\\xff")\n')
            executable.chmod(0o755)
            real_popen = subprocess.Popen
            def launch_process(command, **kwargs):
                if command[0] == 'codex':
                    return real_popen(command, **kwargs)
                return mock.Mock(pid=123)
            with mock.patch.dict(os.environ, {'PATH': raw}), \
                    mock.patch.object(queue.subprocess, 'Popen', side_effect=launch_process):
                queue.launch(['--thread', THREAD, '--cwd', raw, '--job-dir', str(root / 'job'),
                              '--label', 'Gate', '--follow-up', 'Inspect', '--', 'example'])
            self.assertTrue((root / 'job' / 'config.json').is_file())

    def test_concurrent_recovery_sends_only_one_notification(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue.save_json(root / 'status.json', {'outcome': 'success'})
            def recover():
                try:
                    return queue.notify(self.config(root), recovery=True)['state']
                except ValueError:
                    return 'already accepted'
            with mock.patch.object(queue.subprocess, 'run',
                                   return_value=subprocess.CompletedProcess([], 0, 'ok')) as run:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda _: recover(), range(2)))
            self.assertCountEqual(results, ['accepted_by_cli', 'already accepted'])
            self.assertEqual(run.call_count, 1)
            self.assertEqual(json.loads((root / 'delivery.json').read_text())['attempts'], 1)

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

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups required')
    def test_watcher_cancellation_stops_owned_descendant_and_records_interruption(self):
        import signal
        for signum in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=signum), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                child = root / 'child.py'
                child.write_text('import signal,time\nfrom pathlib import Path\n'
                    'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                    'while True:\n Path("heartbeat").write_text(str(time.time_ns()))\n time.sleep(.02)\n')
                config = self.config(root)
                config['timeout_seconds'] = 30
                config['command'] = [sys.executable, '-c',
                    'import subprocess,sys,time,signal\nfrom pathlib import Path\n'
                    'child=subprocess.Popen([sys.executable,"child.py"])\n'
                    'def stop(signum,frame):\n child.kill(); child.wait(); Path("cleanup_active").touch()\n'
                    ' while not Path("release_cleanup").exists(): time.sleep(.01)\n'
                    ' sys.exit(0)\n'
                    'signal.signal(signal.SIGTERM,stop)\nPath("ready").touch()\ntime.sleep(60)']
                config_path = root / 'config.json'
                config_path.write_text(json.dumps(config))
                # Actual helper watch entry point, with only delivery replaced to prevent messages.
                launcher = ('import importlib.util,json,sys; '
                    f's=importlib.util.spec_from_file_location("queue",{str(SCRIPT)!r}); '
                    'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                    'm.TERM_GRACE_SECONDS=7; m.notify=lambda config: None; '
                    'm.watch(json.load(open(sys.argv[1])))')
                watcher = subprocess.Popen([sys.executable, '-c', launcher, str(config_path)],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                try:
                    deadline = time.monotonic() + 5
                    while not ((root / 'heartbeat').exists() and (root / 'ready').exists()) and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertTrue((root / 'heartbeat').exists())
                    self.assertTrue((root / 'ready').exists())
                    watcher.send_signal(signum)
                    # Prove cleanup is active rather than race an elapsed delay.
                    deadline = time.monotonic() + 5
                    while not (root / 'cleanup_active').exists() and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertTrue((root / 'cleanup_active').exists())
                    self.assertIsNone(watcher.poll())
                    watcher.send_signal(signum)
                    (root / 'release_cleanup').touch()
                    _, error = watcher.communicate(timeout=5)
                    self.assertEqual(watcher.returncode, 0, error.decode())
                    status = json.loads((root / 'status.json').read_text())
                    self.assertEqual(status['outcome'], 'interrupted')
                    self.assertTrue(status['cancel_requested'])
                    self.assertTrue(status['cleanup_confirmed'], status)
                    before = (root / 'heartbeat').read_bytes()
                    time.sleep(.12)
                    self.assertEqual((root / 'heartbeat').read_bytes(), before)
                finally:
                    (root / 'release_cleanup').touch()
                    if watcher.poll() is None:
                        watcher.kill(); watcher.communicate()

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

    def test_unavailable_group_observation_never_proves_absence(self):
        process = mock.Mock(pid=123)
        with mock.patch.object(queue, 'group_exists', side_effect=PermissionError('unavailable')):
            absent, error = queue.wait_group_absence(process, 0)
        self.assertFalse(absent)
        self.assertIsInstance(error, PermissionError)
        process.poll.assert_called_once()
        with mock.patch.object(queue, 'group_exists', side_effect=[PermissionError('transient'), False]), \
                mock.patch.object(queue.time, 'sleep'):
            absent, error = queue.wait_group_absence(process, 1)
        self.assertTrue(absent)
        self.assertIsNone(error)

    def test_finished_job_cannot_be_rerun_or_overwritten(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue.save_json(root / 'status.json', {'outcome': 'success', 'exit_code': 0})
            before = (root / 'status.json').read_bytes()
            with mock.patch.object(queue.subprocess, 'Popen') as popen:
                with self.assertRaisesRegex(ValueError, 'already retained'):
                    queue.watch(self.config(root))
                popen.assert_not_called()
            self.assertEqual((root / 'status.json').read_bytes(), before)

    def test_cancellation_during_cleanup_preserves_known_success(self):
        import signal
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            def absent(group):
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                return False
            with mock.patch.object(queue.subprocess, 'Popen', return_value=mock.Mock(pid=123, wait=mock.Mock(return_value=0))), \
                    mock.patch.object(queue, 'group_exists', side_effect=absent), \
                    mock.patch.object(queue, 'notify'):
                queue.watch(self.config(root))
            status = json.loads((root / 'status.json').read_text())
            self.assertEqual(status['outcome'], 'success')
            self.assertEqual(status['exit_code'], 0)
            self.assertTrue(status['cancel_requested'])
            self.assertTrue(status['cleanup_confirmed'])

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
            (root / 'queue.log').write_text('legacy rejection diagnostic')
            legacy = (root / 'delivery.json').read_bytes()
            with mock.patch.object(queue.subprocess, 'Popen') as popen, \
                    mock.patch.object(queue.subprocess, 'run', return_value=
                                      subprocess.CompletedProcess([], 0, 'queued')) as run:
                result = queue.notify(config, recovery=True)
            self.assertEqual(result['state'], 'accepted_by_cli')
            self.assertEqual(result['attempts'], 2)
            self.assertEqual((root / 'delivery-attempts/000001/legacy.json').read_bytes(), legacy)
            self.assertEqual((root / 'delivery-attempts/000001/queue.log').read_text(), 'legacy rejection diagnostic')
            popen.assert_not_called()
            self.assertEqual(run.call_count, 1)
            with self.assertRaisesRegex(ValueError, 'do not resend'):
                queue.notify(config, recovery=True)

    def test_public_redelivery_retains_rejected_then_accepted_and_refuses_resend(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.config(root)
            queue.save_json(root / 'config.json', config)
            queue.save_json(root / 'status.json', {'outcome': 'success'})
            (root / 'output.log').write_bytes(b'original command output')
            originals = {name: (root / name).read_bytes() for name in ('status.json', 'output.log')}
            executable = root / 'codex'
            executable.write_text(f'#!{Path(sys.executable).resolve()}\n'
                'from pathlib import Path\nimport sys\n'
                f'p=Path({str(root / "sends")!r})\n'
                'n=int(p.read_text())+1 if p.exists() else 1\np.write_text(str(n))\n'
                'print("rejection-original" if n == 1 else "accepted-original")\n'
                'sys.exit(7 if n == 1 else 0)\n')
            executable.chmod(0o755)
            command = [sys.executable, str(SCRIPT), '--redeliver', str(root / 'config.json')]
            env = dict(os.environ, PATH=raw)
            first = subprocess.run(command, env=env, capture_output=True)
            self.assertEqual(first.returncode, 0)
            first_files = {p.name: p.read_bytes() for p in (root / 'delivery-attempts/000001').iterdir()}
            second = subprocess.run(command, env=env, capture_output=True)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(json.loads((root / 'delivery-attempts/000001/result.json').read_text())['exit_code'], 7)
            self.assertIn(b'rejection-original', first_files['queue.log'])
            self.assertIn('accepted-original', (root / 'delivery-attempts/000002/queue.log').read_text())
            third = subprocess.run(command, env=env, capture_output=True)
            self.assertNotEqual(third.returncode, 0)
            self.assertEqual((root / 'sends').read_text(), '2')
            for name, original in first_files.items():
                self.assertEqual((root / 'delivery-attempts/000001' / name).read_bytes(), original)
            for name, original in originals.items():
                self.assertEqual((root / name).read_bytes(), original)
            self.assertFalse((root / 'watcher.log').exists())

    def test_public_concurrent_redelivery_sends_once(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue.save_json(root / 'config.json', self.config(root))
            queue.save_json(root / 'status.json', {'outcome': 'success'})
            (root / 'output.log').write_bytes(b'unchanged')
            originals = {name: (root / name).read_bytes() for name in ('status.json', 'output.log')}
            executable = root / 'codex'
            executable.write_text(f'#!{Path(sys.executable).resolve()}\nimport time\nfrom pathlib import Path\n'
                f'p=Path({str(root / "sends")!r})\n'
                'p.write_text(p.read_text()+"send\\n" if p.exists() else "send\\n")\n'
                'time.sleep(.3)\nprint("accepted")\n')
            executable.chmod(0o755)
            command = [sys.executable, str(SCRIPT), '--redeliver', str(root / 'config.json')]
            processes = [subprocess.Popen(command, env=dict(os.environ, PATH=raw),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            for process in processes:
                process.communicate(timeout=10)
            self.assertCountEqual([p.returncode for p in processes], [0, 1])
            self.assertEqual((root / 'sends').read_text(), 'send\n')
            self.assertEqual(len(list((root / 'delivery-attempts').iterdir())), 1)
            for name, original in originals.items():
                self.assertEqual((root / name).read_bytes(), original)
            self.assertFalse((root / 'watcher.log').exists())

    def test_interrupted_attempt_remains_immutable_during_authorized_retry(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue.save_json(root / 'status.json', {'outcome': 'success'})
            with mock.patch.object(queue.subprocess, 'run', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    queue.notify(self.config(root))
            original = (root / 'delivery-attempts/000001/attempting.json').read_bytes()
            self.assertFalse((root / 'delivery-attempts/000001/result.json').exists())
            with mock.patch.object(queue.subprocess, 'run', side_effect=subprocess.TimeoutExpired('codex', 30)):
                delivery = queue.notify(self.config(root), recovery=True)
            self.assertEqual(delivery['state'], 'uncertain')
            uncertain = (root / 'delivery-attempts/000002/result.json').read_bytes()
            with mock.patch.object(queue.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok')):
                queue.notify(self.config(root), recovery=True)
            self.assertEqual((root / 'delivery-attempts/000001/attempting.json').read_bytes(), original)
            self.assertEqual((root / 'delivery-attempts/000002/result.json').read_bytes(), uncertain)

    def test_first_success_inspection_error_enters_bounded_cleanup(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = self.config(root)
            config['command'] = [sys.executable, '-c', 'pass']
            with mock.patch.object(queue, 'group_exists', side_effect=[PermissionError('transient'), False]) as inspect, \
                    mock.patch.object(queue, 'terminate_group', wraps=queue.terminate_group) as cleanup, \
                    mock.patch.object(queue, 'notify'):
                queue.watch(config)
            status = json.loads((root / 'status.json').read_text())
            self.assertEqual((status['outcome'], status['exit_code']), ('success', 0))
            self.assertTrue(status['cleanup_confirmed'])
            self.assertIsNone(status['cleanup_error'])
            self.assertGreaterEqual(inspect.call_count, 2)
            cleanup.assert_called_once()

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups required')
    def test_transient_first_success_inspection_still_stops_real_descendant(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'child.py').write_text('import signal,time\nfrom pathlib import Path\n'
                'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                'until=time.monotonic()+8\n'
                'while time.monotonic()<until:\n Path("heartbeat").write_text(str(time.time_ns()))\n time.sleep(.02)\n')
            config = self.config(root)
            config['command'] = [sys.executable, '-c',
                'import subprocess,sys,time; subprocess.Popen([sys.executable,"child.py"]); time.sleep(.4)']
            actual = queue.group_exists
            observed = []
            def first_error(group):
                observed.append(group)
                if len(observed) == 1:
                    raise PermissionError('transient first inspection')
                return actual(group)
            with mock.patch.object(queue, 'group_exists', side_effect=first_error), \
                    mock.patch.object(queue, 'terminate_group', wraps=queue.terminate_group) as cleanup, \
                    mock.patch.object(queue, 'TERM_GRACE_SECONDS', .2), \
                    mock.patch.object(queue, 'CLEANUP_WAIT_SECONDS', .5), \
                    mock.patch.object(queue, 'notify'):
                queue.watch(config)
            status = json.loads((root / 'status.json').read_text())
            self.assertEqual((status['outcome'], status['exit_code']), ('success', 0))
            cleanup.assert_called_once()
            self.assertGreaterEqual(len(observed), 2)
            heartbeat = (root / 'heartbeat').read_bytes()
            time.sleep(.15)
            self.assertEqual((root / 'heartbeat').read_bytes(), heartbeat)
            # A zombie-only group may remain visible: never convert that into absence.
            if not status['cleanup_confirmed']:
                self.assertIn('cleanup unresolved', status['detail'])


if __name__ == '__main__':
    unittest.main()
