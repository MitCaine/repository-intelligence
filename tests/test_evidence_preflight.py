"""Consumer-template checks against independently created Git source and logs."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'docs/skill-templates/capsule-preflight/scripts/evidence_preflight.py'
spec = importlib.util.spec_from_file_location('evidence_preflight', SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class EvidencePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.records = Path(self.temp.name) / 'records'
        self.records.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        self.git('init', '-q')
        (self.root / 'task.py').write_text('old\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'base')
        b = self.git('rev-parse', 'HEAD').strip()
        (self.root / 'task.py').write_text('new independently expected bytes\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'candidate')
        c = self.git('rev-parse', 'HEAD').strip()
        invocation = {'argv': ['python', '-m', 'pytest', 'tests'], 'cwd': '.',
                      'config': {'collection': 'tests'}, 'interpreter': '/fixed/python',
                      'profiles': ['repository'], 'isolation': 'protected-v1',
                      'environment': {}, 'source_files': {'task.py': hashlib.sha256(
                          b'new independently expected bytes\n').hexdigest()}}
        self.contract = {'schema_version': 1,
                         'identity': {'task_id': 'fixture', 'revision': 1,
                                      'base': b, 'planning': b, 'candidate': c},
                         'allowed_paths': ['task.py'],
                         'inventory': [{'path': 'task.py', 'disposition': 'edit',
                                        'purpose': 'requested behavior'}],
                         'checks': [{'id': 'focused', 'profile': 'repository',
                                     'allowed_skip_ids': ['test_native'],
                                     'probe_required': True, 'rehearsal_required': True,
                                     'invocation': invocation}]}
        log = b'fixture result: one skip because unavailable capability\n'
        (self.records / 'run.log').write_bytes(log)
        proof = {'log_path': 'run.log', 'log_sha256': hashlib.sha256(log).hexdigest()}
        self.packet = {'schema_version': 1, 'identity': copy.deepcopy(self.contract['identity']),
                       'checks': [{'id': 'focused', 'candidate': c, 'profile': 'repository',
                                   'exit_code': 0, 'skip_count': 1,
                                   'skips': [{'id': 'test_native', 'reason': 'unavailable'}],
                                   'capability_probe': {'available': False, 'detail': 'not installed'},
                                   'invocation': copy.deepcopy(invocation), **proof}],
                       'rehearsals': [{'id': 'focused', 'exit_code': 0,
                                      'invocation': copy.deepcopy(invocation), **proof}]}

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args],
                                       env=self.env, stderr=subprocess.PIPE).decode()

    def check(self):
        return gate.validate(self.contract, self.packet, self.root, self.records)

    def test_complete_packet(self):
        self.assertEqual(self.check(), ['task.py'])

    def closeout_fixture(self):
        installed = self.contract['identity']['base']
        recovery = self.contract['identity']['candidate']
        self.git('checkout', '--detach', '-q', installed)
        (self.root / 'probe.txt').write_text('negative probe\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'negative probe')
        negative = self.git('rev-parse', 'HEAD').strip()
        self.git('checkout', '--detach', '-q', recovery)
        proof = {'log_path': 'run.log', 'log_sha256': hashlib.sha256(
            (self.records / 'run.log').read_bytes()).hexdigest()}
        expected = {'history_check_id': 'focused', 'required_metadata': ['repository', 'issue'],
                    'metadata': {'repository': 'fixture', 'issue': 245},
                    'installed_base': installed, 'recovery_commit': recovery,
                    'capsule_path': 'task.py', 'capsule_sha256': hashlib.sha256(
                        b'new independently expected bytes\n').hexdigest(),
                    'workflow_identity': 'installed-workflow-digest',
                    'selected_test_id': 'test_controller',
                    'probes': {'negative': {'candidate': negative, 'check_id': 'check-negative'},
                               'positive': {'candidate': recovery, 'check_id': 'check-positive'}}}
        observed = {key: copy.deepcopy(expected[key]) for key in
                    ('metadata', 'installed_base', 'recovery_commit', 'capsule_sha256')}
        observed.update(proof)
        observed['probes'] = []
        for name, candidate, outcome, code, failures in [
                ('negative', negative, 'failed', 1, ['test_controller']),
                ('positive', recovery, 'passed', 0, [])]:
            observed['probes'].append({'id': name, 'candidate': candidate,
                'check_id': 'check-' + name, 'installed_base': installed,
                'workflow_identity': expected['workflow_identity'],
                'selected_test_id': 'test_controller', 'selected_test_outcome': outcome,
                'failed_test_ids': failures, 'qualification_candidate': candidate,
                'qualification_outcome': outcome, 'exit_code': code, **proof})
        self.contract['closeout'] = expected
        self.packet['closeout'] = observed

    def test_complete_closeout_pair(self):
        self.closeout_fixture()
        self.assertEqual(self.check(), ['task.py'])

    def test_closeout_missing_metadata_or_validator(self):
        self.closeout_fixture()
        del self.packet['closeout']['metadata']['repository']
        with self.assertRaisesRegex(gate.Blocked, 'metadata'):
            self.check()
        self.packet['closeout']['metadata']['repository'] = 'fixture'
        self.contract['closeout']['history_check_id'] = 'absent'
        with self.assertRaisesRegex(gate.Blocked, 'validator'):
            self.check()

    def test_closeout_wrong_test_is_not_negative_proof(self):
        self.closeout_fixture()
        negative = self.packet['closeout']['probes'][0]
        negative['failed_test_ids'] = ['unrelated_test']
        with self.assertRaisesRegex(gate.Blocked, 'unexpected failing'):
            self.check()
        negative['failed_test_ids'] = ['test_controller']
        negative['selected_test_outcome'] = 'skipped'
        with self.assertRaisesRegex(gate.Blocked, 'selected test'):
            self.check()

    def test_closeout_identity_drift(self):
        self.closeout_fixture()
        original = copy.deepcopy(self.packet['closeout'])
        for field, value in [('installed_base', '0' * 40),
                             ('capsule_sha256', '0' * 64), ('recovery_commit', '0' * 40)]:
            with self.subTest(field=field):
                self.packet['closeout'] = copy.deepcopy(original)
                self.packet['closeout'][field] = value
                with self.assertRaises(gate.Blocked):
                    self.check()
        for field in ('workflow_identity', 'qualification_candidate', 'check_id', 'candidate'):
            with self.subTest(field=field):
                self.packet['closeout'] = copy.deepcopy(original)
                self.packet['closeout']['probes'][0][field] = '0' * 40
                with self.assertRaises(gate.Blocked):
                    self.check()

    def test_closeout_missing_probe_and_failed_validator(self):
        self.closeout_fixture()
        original = copy.deepcopy(self.packet['closeout']['probes'])
        self.packet['closeout']['probes'] = original[:1]
        with self.assertRaisesRegex(gate.Blocked, 'probe pair'):
            self.check()
        self.packet['closeout']['probes'] = original
        self.packet['checks'][0]['exit_code'] = 1
        with self.assertRaisesRegex(gate.Blocked, 'exit status'):
            self.check()

    def test_identity_and_profile_fail_closed(self):
        for key, value in [('candidate', '0' * 40), ('profile', 'ios-native')]:
            with self.subTest(key=key):
                original = self.packet['checks'][0][key]
                self.packet['checks'][0][key] = value
                with self.assertRaisesRegex(gate.Blocked, 'mismatch'):
                    self.check()
                self.packet['checks'][0][key] = original

    def test_omitted_skip_and_probe(self):
        self.packet['checks'][0]['skips'] = []
        with self.assertRaisesRegex(gate.Blocked, 'skip detail'):
            self.check()
        self.packet['checks'][0]['skip_count'] = 0
        self.packet['checks'][0].pop('capability_probe')
        with self.assertRaisesRegex(gate.Blocked, 'probe result'):
            self.check()

    def test_missing_and_duplicate_check(self):
        original = self.packet['checks']
        self.packet['checks'] = []
        with self.assertRaisesRegex(gate.Blocked, 'check IDs'):
            self.check()
        self.packet['checks'] = original * 2
        with self.assertRaisesRegex(gate.Blocked, 'duplicate'):
            self.check()

    def test_unauthorized_skip(self):
        self.contract['checks'][0]['allowed_skip_ids'] = []
        with self.assertRaisesRegex(gate.Blocked, 'unauthorized skipped'):
            self.check()

    def test_allowed_path_still_needs_edit_inventory(self):
        self.contract['inventory'][0]['disposition'] = 'inspect'
        with self.assertRaisesRegex(gate.Blocked, 'edit inventory'):
            self.check()

    def test_retained_log_tampering(self):
        (self.records / 'run.log').write_text('changed')
        with self.assertRaisesRegex(gate.Blocked, 'digest mismatch'):
            self.check()

    def test_rehearsal_environment_drift(self):
        for field in ('cwd', 'config', 'interpreter', 'isolation', 'source_files'):
            with self.subTest(field=field):
                original = self.packet['rehearsals'][0]['invocation'][field]
                self.packet['rehearsals'][0]['invocation'][field] = 'different'
                with self.assertRaisesRegex(gate.Blocked, 'rehearsal mismatch'):
                    self.check()
                self.packet['rehearsals'][0]['invocation'][field] = original

    def test_frozen_invocation_drift(self):
        self.packet['checks'][0]['invocation']['argv'].append('--changed')
        with self.assertRaisesRegex(gate.Blocked, 'frozen invocation drift'):
            self.check()

    def test_source_hash_checked_against_git(self):
        self.contract['checks'][0]['invocation']['source_files']['task.py'] = '0' * 64
        with self.assertRaisesRegex(gate.Blocked, 'source mismatch'):
            self.check()

    def test_dirty_and_wrong_head(self):
        (self.root / 'cache').write_text('generated')
        with self.assertRaisesRegex(gate.Blocked, 'dirty checkout'):
            self.check()
        (self.root / 'cache').unlink()
        self.git('checkout', '--detach', '-q', self.contract['identity']['planning'])
        with self.assertRaisesRegex(gate.Blocked, 'head differs'):
            self.check()

    def test_duplicate_json_and_unsupported_schema(self):
        path = self.records / 'bad.json'
        path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(gate.Blocked, 'duplicate JSON'):
            gate.load(path)
        path.write_text('{"schema_version":2}')
        with self.assertRaisesRegex(gate.Blocked, 'unsupported schema'):
            gate.load(path)

    def test_symlink_log_rejected(self):
        (self.records / 'linked.log').symlink_to(self.records / 'run.log')
        self.packet['checks'][0]['log_path'] = 'linked.log'
        with self.assertRaisesRegex(gate.Blocked, 'not regular'):
            self.check()

    def test_cli_blocked_and_checked_results(self):
        contract = self.records / 'contract.json'
        packet = self.records / 'packet.json'
        contract.write_text(json.dumps(self.contract))
        packet.write_text(json.dumps(self.packet))
        cmd = [os.sys.executable, str(SCRIPT), '--repository', str(self.root),
               '--contract', str(contract), '--packet', str(packet)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)['disposition'], 'checked')
        packet.write_text('{')
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['disposition'], 'blocked')
