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
from unittest import mock

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
                      'environment': {}, 'source_files': {'task.py': {'mode': '100644', 'sha256': hashlib.sha256(
                          b'new independently expected bytes\n').hexdigest()}}}
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

    def repeat_checks(self, count):
        expected, observed, rehearsal = (copy.deepcopy(rows[0]) for rows in (
            self.contract['checks'], self.packet['checks'], self.packet['rehearsals']))
        for document, field, template in ((self.contract, 'checks', expected),
                (self.packet, 'checks', observed), (self.packet, 'rehearsals', rehearsal)):
            document[field] = [{**copy.deepcopy(template), 'id': f'check-{i}'}
                               for i in range(count)]

    def test_committed_sources_are_read_once_per_validation(self):
        sources = copy.deepcopy(self.contract['checks'][0]['invocation']['source_files'])
        for i in range(31):
            path, data = f'source-{i}.py', f'fixture {i}\n'.encode()
            (self.root / path).write_bytes(data)
            sources[path] = {'mode': '100644', 'sha256': hashlib.sha256(data).hexdigest()}
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'source fixture')
        candidate = self.git('rev-parse', 'HEAD').strip()
        self.contract['identity']['candidate'] = candidate
        self.packet['identity']['candidate'] = candidate
        self.packet['checks'][0]['candidate'] = candidate
        self.contract['allowed_paths'] = sorted(sources)
        self.contract['inventory'] = [{'path': path, 'disposition': 'edit', 'purpose': 'fixture'}
                                     for path in sorted(sources)]
        for record in self.contract['checks'] + self.packet['checks'] + self.packet['rehearsals']:
            record['invocation']['source_files'] = copy.deepcopy(sources)
        self.repeat_checks(12)
        with mock.patch.object(gate, 'git', wraps=gate.git) as calls:
            self.assertEqual(self.check(), sorted(sources))
            source_calls = [call for call in calls.call_args_list
                            if call.args[1] in ('ls-tree', 'show')]
            self.assertEqual(len(source_calls), 64)
            self.assertEqual(self.check(), sorted(sources))
            source_calls = [call for call in calls.call_args_list
                            if call.args[1] in ('ls-tree', 'show')]
            self.assertEqual(len(source_calls), 128)  # No cross-call memo.
        for field, wrong in (('sha256', '0' * 64), ('mode', '100755')):
            expected = copy.deepcopy(self.contract)
            packet = copy.deepcopy(self.packet)
            expected['checks'][-1]['invocation']['source_files']['task.py'][field] = wrong
            packet['checks'][-1]['invocation'] = copy.deepcopy(expected['checks'][-1]['invocation'])
            with self.subTest(field=field), self.assertRaises(gate.Blocked):
                gate.validate(expected, packet, self.root, self.records)

    def test_source_cache_keys_include_exact_commit_and_repository(self):
        invocation = self.contract['checks'][0]['invocation']
        candidate = self.contract['identity']['candidate']
        base = self.contract['identity']['base']
        cache = {}
        gate._validate_invocation(invocation, self.root, candidate, cache)
        with self.assertRaisesRegex(gate.Blocked, 'source mismatch'):
            gate._validate_invocation(invocation, self.root, base, cache)
        other = Path(self.temp.name) / 'other'
        subprocess.run(['git', 'clone', '-q', str(self.root), str(other)],
                       check=True, env=self.env)
        with mock.patch.object(gate, 'git', wraps=gate.git) as calls:
            gate._validate_invocation(invocation, other, candidate, cache)
            self.assertEqual(calls.call_count, 2)
        # A later invocation observes changed expectations, never cached decisions.
        changed = copy.deepcopy(invocation)
        changed['source_files']['task.py']['mode'] = '100755'
        with self.assertRaisesRegex(gate.Blocked, 'mode mismatch'):
            gate.validate_invocation(changed, self.root, candidate)

    def test_shared_source_maps_roundtrip_and_cli(self):
        import sys
        self.repeat_checks(30)
        contract, packet = map(gate.compact_source_maps, (self.contract, self.packet))
        self.assertEqual(len(contract['source_maps']), 1)
        self.assertEqual(len(packet['source_maps']), 1)
        self.assertEqual(gate.expand_source_maps(contract), self.contract)
        self.assertEqual(gate.expand_source_maps(packet), self.packet)
        self.assertEqual(gate.validate(contract, packet, self.root, self.records), ['task.py'])
        for name, value in (('contract', contract), ('packet', packet)):
            (self.records / f'{name}.json').write_text(json.dumps(value))
        result = subprocess.run([sys.executable, str(SCRIPT), '--repository', str(self.root),
            '--contract', str(self.records / 'contract.json'),
            '--packet', str(self.records / 'packet.json')], capture_output=True,
            text=True, env=self.env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cli_named_root_ignores_inherited_routing_and_supports_linked_worktree(self):
        import sys
        for name, value in (('contract', self.contract), ('packet', self.packet)):
            (self.records / f'{name}.json').write_text(json.dumps(value))
        candidate = self.contract['identity']['candidate']
        base = self.contract['identity']['base']
        wrong = Path(self.temp.name) / 'wrong'
        linked = Path(self.temp.name) / 'linked'
        subprocess.run(['git', 'clone', '-q', str(self.root), str(wrong)],
                       check=True, env=self.env)
        subprocess.run(['git', '-C', str(wrong), 'checkout', '-q', base],
                       check=True, env=self.env)
        self.git('worktree', 'add', '--detach', '-q', str(linked), candidate)
        inherited = dict(self.env, GIT_DIR=str(self.root / '.git'),
                         GIT_WORK_TREE=str(self.root), GIT_INDEX_FILE=str(self.root / '.git/index'))
        # Independently establish which actual commits each named worktree holds.
        self.assertEqual(subprocess.check_output(['git', '-C', str(wrong), 'rev-parse', 'HEAD'],
                                                env=self.env).decode().strip(), base)
        self.assertEqual(subprocess.check_output(['git', '-C', str(linked), 'rev-parse', 'HEAD'],
                                                env=self.env).decode().strip(), candidate)
        foreign = dict(self.env, GIT_DIR=str(wrong / '.git'), GIT_WORK_TREE=str(wrong))
        nested = self.root / 'nested'
        nested.mkdir()
        for root, environment, expected in ((self.root, self.env, 'checked'),
                (wrong, self.env, 'blocked'), (wrong, inherited, 'blocked'),
                (self.root, inherited, 'checked'), (self.root, foreign, 'checked'),
                (linked, inherited, 'checked'),
                (nested, inherited, 'blocked')):
            result = subprocess.run([sys.executable, str(SCRIPT), '--repository', str(root),
                '--contract', str(self.records / 'contract.json'),
                '--packet', str(self.records / 'packet.json')], capture_output=True,
                text=True, env=environment, timeout=30)
            observed = json.loads(result.stdout)
            with self.subTest(root=root, inherited=environment is inherited):
                self.assertEqual(observed['disposition'], expected, result.stdout + result.stderr)
                self.assertEqual(result.returncode, 0 if expected == 'checked' else 2)
                if expected == 'checked':
                    self.assertEqual(observed['changed_paths'], ['task.py'])
                    self.assertEqual(observed['schema_version'], 1)

    def test_shared_maps_fit_budget_without_merging_evidence_roles(self):
        self.repeat_checks(30)
        sources = {'directory-' + 'x' * 150 + f'/file-{i}.py':
                   {'mode': '100644', 'sha256': hashlib.sha256(str(i).encode()).hexdigest()}
                   for i in range(256)}
        for record in self.packet['checks'] + self.packet['rehearsals']:
            record['invocation']['source_files'] = copy.deepcopy(sources)
        before = json.dumps(self.packet).encode()
        compact = gate.compact_source_maps(self.packet)
        after = json.dumps(compact).encode()
        self.assertGreater(len(before), 2_000_000)
        self.assertLess(len(after), 150_000)
        self.assertEqual(gate.expand_source_maps(compact), self.packet)
        self.assertEqual(len(compact['checks']), 30)
        self.assertEqual(len(compact['rehearsals']), 30)
        compact['metadata'] = {'source_files_ref': 'ordinary consumer metadata'}
        self.assertEqual(gate.expand_source_maps(compact)['metadata'], compact['metadata'])

    def test_shared_map_faults_and_expansion_budget(self):
        compact = gate.compact_source_maps(self.packet)
        key = next(iter(compact['source_maps']))
        for fault in ('missing', 'tamper', 'unused', 'both', 'version'):
            value = copy.deepcopy(compact)
            if fault == 'missing': value['source_maps'].clear()
            elif fault == 'tamper': value['source_maps'][key]['task.py']['mode'] = '100755'
            elif fault == 'unused':
                sources = {'extra': {'mode': '100644', 'sha256': '0' * 64}}
                value['source_maps'][gate.source_map_digest(sources)] = sources
            elif fault == 'both': value['checks'][0]['invocation']['source_files'] = {}
            else: value['schema_version'] = True
            with self.subTest(fault=fault), self.assertRaises(gate.Blocked):
                gate.expand_source_maps(value)
        with mock.patch.object(gate, 'MAX_EXPANDED_SOURCE_BYTES', 1), self.assertRaises(gate.Blocked):
            gate.expand_source_maps(compact)
        # Sharing hashes does not permit a final invocation to replace rehearsal settings.
        compact['rehearsals'][0]['invocation']['environment'] = {'changed': 'yes'}
        with self.assertRaisesRegex(gate.Blocked, 'rehearsal mismatch'):
            gate.validate(self.contract, compact, self.root, self.records)

    def test_committed_candidate_final_identity_is_always_required(self):
        self.contract['checks'][0]['rehearsal_required'] = False
        self.packet['rehearsals'] = []
        self.assertEqual(self.check(), ['task.py'])
        original = copy.deepcopy(self.packet['checks'][0]['invocation'])
        for field in ('argv', 'interpreter', 'isolation', 'config', 'environment', 'source_files'):
            with self.subTest(field=field):
                self.packet['checks'][0]['invocation'] = copy.deepcopy(original)
                self.packet['checks'][0]['invocation'][field] = 'wrong'
                with self.assertRaises(gate.Blocked):
                    self.check()
        self.packet['checks'][0].pop('invocation')
        with self.assertRaises(gate.Blocked):
            self.check()
        self.packet['checks'][0]['invocation'] = original
        self.contract['checks'][0]['invocation']['source_files']['task.py']['sha256'] = '0' * 64
        with self.assertRaisesRegex(gate.Blocked, 'source mismatch'):
            self.check()

    def test_green_packet_requires_real_mandatory_node_execution(self):
        # Execute a real fixture selector. Both runs exit zero; one omits the node.
        import sys
        selector = self.records / 'selector.py'
        selector.write_text('import json,sys,unittest\n'
            'class Suite(unittest.TestCase):\n def test_required(self): self.assertTrue(True)\n def test_other(self): self.assertTrue(True)\n'
            'suite=unittest.defaultTestLoader.loadTestsFromName("Suite.test_required" if sys.argv[1]=="select" else "Suite.test_other", sys.modules["__main__"])\n'
            'ids=[test.id() for test in suite]\nexecuted=[]\n'
            'class Recording(unittest.TextTestResult):\n def startTest(self,test): executed.append(test.id()); super().startTest(test)\n'
            'result=unittest.TextTestRunner(resultclass=Recording).run(suite)\n'
            'print(json.dumps({"collected":"__main__.Suite.test_required" in ids,"executed":"__main__.Suite.test_required" in executed,"outcome":"passed" if result.wasSuccessful() else "failed","ids":ids,"executed_ids":executed}))\n')
        selecting_gate = hashlib.sha256(selector.read_bytes()).hexdigest()
        self.contract['checks'][0]['mandatory_observations'] = [
            {'id': '__main__.Suite.test_required', 'stage': 'incumbent', 'gate_identity': selecting_gate}]
        for mode in ('omit', 'select'):
            run = subprocess.run([sys.executable, str(selector), mode], check=True, capture_output=True)
            observation = json.loads(run.stdout)
            self.packet['checks'][0]['observations'] = [
                {'id': '__main__.Suite.test_required', 'stage': 'incumbent', 'gate_identity': selecting_gate,
                 **observation}]
            log = run.stdout + run.stderr
            (self.records / 'run.log').write_bytes(log)
            digest = hashlib.sha256(log).hexdigest()
            self.packet['checks'][0]['log_sha256'] = digest
            self.packet['rehearsals'][0]['log_sha256'] = digest
            if mode == 'omit':
                with self.assertRaisesRegex(gate.Blocked, 'not executed'):
                    self.check()
            else:
                self.assertEqual(self.check(), ['task.py'])
                self.packet['checks'][0]['observations'][0]['stage'] = 'installed'
                with self.assertRaisesRegex(gate.Blocked, 'stage mismatch'):
                    self.check()

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
        observed['validator_evidence'] = {'id': 'focused', 'candidate': recovery,
            'exit_code': 0, **proof}
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
        self.contract['checks'][0]['invocation']['source_files']['task.py']['sha256'] = '0' * 64
        with self.assertRaisesRegex(gate.Blocked, 'source mismatch'):
            self.check()

    def test_rehearsal_mode_identity(self):
        self.contract['checks'][0]['invocation']['source_files']['task.py']['mode'] = '100755'
        with self.assertRaisesRegex(gate.Blocked, 'mode mismatch'):
            self.check()

    def test_identical_bytes_after_executable_or_symlink_transition(self):
        source = self.root / 'task.py'
        source.chmod(0o755)
        self.git('add', 'task.py')
        self.git('update-index', '--chmod=+x', 'task.py')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'executable source')
        invocation = self.contract['checks'][0]['invocation']
        invocation['source_files']['task.py']['mode'] = '100755'
        gate.validate_invocation(invocation, self.root, self.git('rev-parse', 'HEAD').strip())
        source.chmod(0o644)
        self.git('add', 'task.py')
        self.git('update-index', '--chmod=-x', 'task.py')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'mode only change')
        with self.assertRaisesRegex(gate.Blocked, 'mode mismatch'):
            gate.validate_invocation(invocation, self.root, self.git('rev-parse', 'HEAD').strip())
        raw = source.read_text()
        source.unlink()
        source.symlink_to(raw)
        self.git('add', 'task.py')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-qm', 'symlink with same stored bytes')
        invocation['source_files']['task.py']['mode'] = '100644'
        with self.assertRaisesRegex(gate.Blocked, 'mode mismatch'):
            gate.validate_invocation(invocation, self.root, self.git('rev-parse', 'HEAD').strip())

    def test_cwd_escape_and_missing_directory(self):
        for cwd in ('missing', 'outside'):
            with self.subTest(cwd=cwd):
                if cwd == 'outside':
                    (self.root / cwd).symlink_to(self.records, target_is_directory=True)
                invocation = self.contract['checks'][0]['invocation']
                invocation['cwd'] = cwd
                with self.assertRaisesRegex(gate.Blocked, 'cwd missing or escapes'):
                    gate.validate_invocation(invocation, self.root, self.contract['identity']['candidate'])

    def test_extra_rehearsal_rejected(self):
        extra = copy.deepcopy(self.packet['rehearsals'][0])
        extra['id'] = 'stale'
        self.packet['rehearsals'].append(extra)
        with self.assertRaisesRegex(gate.Blocked, 'rehearsal IDs'):
            self.check()

    def test_history_validator_evidence_binding(self):
        self.closeout_fixture()
        self.packet['closeout']['validator_evidence']['log_sha256'] = '0' * 64
        with self.assertRaisesRegex(gate.Blocked, 'validator evidence'):
            self.check()

    def test_dirty_and_wrong_head(self):
        (self.root / 'cache').write_text('generated')
        with self.assertRaisesRegex(gate.Blocked, 'dirty checkout'):
            self.check()
        (self.root / 'cache').unlink()
        self.git('checkout', '--detach', '-q', self.contract['identity']['planning'])
        with self.assertRaisesRegex(gate.Blocked, 'head differs'):
            self.check()

    def test_successful_command_that_changes_source_is_ineligible(self):
        self.assertEqual(self.check(), ['task.py'])
        candidate = self.packet['checks'][0]['candidate']
        result = subprocess.run([os.sys.executable, '-c',
            'from pathlib import Path; Path("task.py").write_text("changed during check\\n")'],
            cwd=self.root, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), candidate)
        with self.assertRaisesRegex(gate.Blocked, 'dirty checkout'):
            self.check()

    def test_duplicate_json_and_unsupported_schema(self):
        path = self.records / 'bad.json'
        path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(gate.Blocked, 'duplicate JSON'):
            gate.load(path)
        path.write_text('{"schema_version":3}')
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

    def test_deep_compact_metadata_returns_structured_block(self):
        contract = self.records / 'contract.json'
        packet = self.records / 'packet.json'
        contract.write_text(json.dumps(self.contract))
        cmd = [os.sys.executable, str(SCRIPT), '--repository', str(self.root),
               '--contract', str(contract), '--packet', str(packet)]
        # Traversal capacity varies across Python versions (3.14 inlines
        # comprehensions). A processable record may pass, exhaustion must block.
        metadata = '[' * 600 + '0' + ']' * 600
        for value, disposition in [(self.packet, 'checked'),
                                    (gate.compact_source_maps(self.packet), 'blocked')]:
            raw = json.dumps(value)
            packet.write_text(raw[:-1] + ',"extra_metadata":' + metadata + '}')
            result = subprocess.run(cmd, capture_output=True, text=True)
            actual = json.loads(result.stdout)['disposition']
            self.assertIn(actual, ['checked'] if disposition == 'checked' else
                          ['checked', 'blocked'])
            self.assertEqual(result.returncode, 0 if actual == 'checked' else 2)
            self.assertEqual(result.stderr, '')
        with mock.patch.object(gate, 'expand_source_maps', side_effect=RecursionError):
            with self.assertRaisesRegex(gate.Blocked, 'record nesting'):
                gate.load(packet)
        # Parser exhaustion itself must also produce a controlled block.
        packet.write_text('{"schema_version":2,"extra":' + '[' * 2000 +
                          '0' + ']' * 2000 + '}')
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['disposition'], 'blocked')
        self.assertEqual(result.stderr, '')

    def test_reuse_retains_origin_and_separate_current_authorization(self):
        execution = copy.deepcopy(self.packet['checks'][0])
        execution['inputs'] = {key: 'a' * 64 for key in gate.REUSE_INPUTS}
        origin = execution['candidate']
        (self.root / 'lifecycle.md').write_text('closeout only\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'lifecycle')
        current = self.git('rev-parse', 'HEAD').strip()
        digest = hashlib.sha256(json.dumps(execution, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        authorization = {'candidate': current, 'execution_sha256': digest,
                         'policy_version': 'fixture-v1', 'claim': 'focused',
                         'trusted': True, 'fresh': True, 'inputs': copy.deepcopy(execution['inputs'])}
        policy = {'adopted': True, 'version': 'fixture-v1', 'allowed_claims': ['focused']}
        before = copy.deepcopy(execution)
        result = gate.validate_reuse(execution, authorization, policy, self.root, self.records, current)
        self.assertEqual(result['execution_candidate'], origin)
        self.assertEqual(result['authorization_candidate'], current)
        self.assertEqual(execution, before)
        for field, value in [('execution_sha256', '0' * 64), ('policy_version', 'other'),
                             ('trusted', False), ('fresh', False), ('candidate', '0' * 40)]:
            with self.subTest(field=field), self.assertRaises((gate.Blocked, subprocess.CalledProcessError)):
                gate.validate_reuse(execution, {**authorization, field: value}, policy, self.root, self.records, current)
        with self.assertRaises(gate.Blocked):
            gate.validate_reuse({**execution, 'candidate': current}, authorization, policy, self.root, self.records, current)
        with self.assertRaises(gate.Blocked):
            gate.validate_reuse(execution, authorization, {**policy, 'adopted': False}, self.root, self.records, current)
        for field in ('code', 'dependencies', 'environment', 'configuration',
                      'selector', 'selecting_gate', 'toolchain', 'isolation', 'timeout_policy'):
            with self.subTest(changed_input=field), self.assertRaises(gate.Blocked):
                gate.validate_reuse(execution, {**authorization, 'inputs': {
                    **authorization['inputs'], field: 'b' * 64}},
                    policy, self.root, self.records, current)
        self.assertEqual(execution, before)

    def test_reuse_rejects_malformed_claim_allowlists(self):
        execution = copy.deepcopy(self.packet['checks'][0])
        execution['inputs'] = {key: 'a' * 64 for key in gate.REUSE_INPUTS}
        candidate = execution['candidate']
        authorization = {'candidate': candidate, 'execution_sha256': hashlib.sha256(
            json.dumps(execution, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest(),
            'policy_version': 'v1', 'claim': 'unit', 'trusted': True, 'fresh': True,
            'inputs': execution['inputs']}
        policy = {'adopted': True, 'version': 'v1', 'allowed_claims': ['unit']}
        gate.validate_reuse(execution, authorization, policy, self.root, self.records, candidate)
        cases = [('unit', 'not-unit'), ('', ['']), (7, [7]),
                 ('unit', ['unit', 'unit']), ('unit', []), ('unit', {'unit': True}),
                 ('unit', ['not-unit']), (None, [None])]
        for claim, allowed in cases:
            with self.subTest(claim=claim, allowed=allowed), self.assertRaises(gate.Blocked):
                gate.validate_reuse(execution, {**authorization, 'claim': claim},
                    {**policy, 'allowed_claims': allowed}, self.root, self.records, candidate)

    def test_json_scalar_aliases_reject_in_preflight_and_closeout_cli(self):
        import sys
        self.closeout_fixture()
        for document in (self.contract, self.packet):
            document['closeout']['metadata']['issue'] = 1
            document['closeout']['metadata']['accepted'] = True
        self.contract['closeout']['required_metadata'].append('accepted')
        original = copy.deepcopy(self.packet)
        contract_path, packet_path = self.records / 'contract.json', self.records / 'packet.json'
        contract_path.write_text(json.dumps(self.contract))
        def invoke():
            packet_path.write_text(json.dumps(self.packet))
            result = subprocess.run([sys.executable, str(SCRIPT), '--repository', str(self.root),
                '--contract', str(contract_path), '--packet', str(packet_path)],
                capture_output=True, text=True, timeout=30, env=self.env)
            return result.returncode, json.loads(result.stdout)
        self.assertEqual(invoke()[0], 0)
        self.assertEqual(self.check(), ['task.py'])
        cases = [(('identity', 'revision'), True), (('identity', 'revision'), 1.0),
                 (('closeout', 'metadata', 'issue'), True),
                 (('closeout', 'metadata', 'issue'), 1.0),
                 (('closeout', 'metadata', 'accepted'), 1),
                 (('closeout', 'validator_evidence', 'exit_code'), False),
                 (('closeout', 'validator_evidence', 'exit_code'), 0.0),
                 (('identity', 'revision'), 2)]
        for path, substitute in cases:
            with self.subTest(path=path, substitute=substitute):
                self.packet = copy.deepcopy(original)
                parent = self.packet
                for field in path[:-1]:
                    parent = parent[field]
                parent[path[-1]] = substitute
                code, result = invoke()
                self.assertEqual(code, 2, result)
                self.assertEqual(result['disposition'], 'blocked')
                with self.assertRaises(gate.Blocked):
                    self.check()
        self.packet = original
        self.assertEqual(invoke()[0], 0)
