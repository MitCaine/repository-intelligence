import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from repository_intelligence import adoption


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source'
        self.destination = self.root / 'destination'
        for repository in (self.source, self.destination):
            repository.mkdir()
            self.git(repository, 'init', '-q')
            self.git(repository, 'config', 'user.email', 'test@example.invalid')
            self.git(repository, 'config', 'user.name', 'Test')
        (self.source / 'source.txt').write_bytes(b'hello old\n')
        self.git(self.source, 'add', '.')
        self.git(self.source, 'commit', '-qm', 'source')
        (self.destination / 'existing.txt').write_bytes(b'existing\n')
        self.git(self.destination, 'add', '.')
        self.git(self.destination, 'commit', '-qm', 'destination')
        self.request = dict(source_repository=str(self.source), revision=self.git(self.source, 'rev-parse', 'HEAD').strip(), destination_repository=str(self.destination), resources=[dict(source='source.txt', destination='adopted.txt', expected_destination_sha256=None, replacements=[dict(old='old', new='new', expected_count=1)])])

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args]).decode()

    def cli(self, mode):
        request_path = self.root / 'request.json'
        request_path.write_text(json.dumps(self.request))
        result = subprocess.run([sys.executable, '-m', 'repository_intelligence.adoption', '--request', str(request_path), '--mode', mode], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_public_cli_exact_revision_transform_repeat(self):
        (self.source / 'source.txt').write_bytes(b'changed worktree')
        self.assertEqual(self.cli('preview')[1]['resources'][0]['source_sha256'], hashlib.sha256(b'hello old\n').hexdigest())
        self.assertFalse((self.destination / 'adopted.txt').exists())
        self.assertEqual(self.cli('verify')[0], 1)
        self.assertEqual(self.cli('apply')[0], 0)
        self.assertEqual((self.destination / 'adopted.txt').read_bytes(), b'hello new\n')
        self.assertEqual(self.cli('apply')[1]['status'], 'unchanged')
        self.assertEqual(self.cli('verify')[0], 0)
        (self.destination / 'adopted.txt').write_bytes(b'drift')
        self.assertEqual(self.cli('apply')[0], 1)
        self.assertEqual((self.destination / 'adopted.txt').read_bytes(), b'drift')

    def test_dirty_staged_hidden_and_bad_revision(self):
        existing = self.destination / 'existing.txt'
        existing.write_text('dirty')
        self.assertEqual(self.cli('apply')[0], 1)
        self.git(self.destination, 'add', '.')
        self.assertEqual(self.cli('apply')[0], 1)
        self.git(self.destination, 'reset', '--hard', '-q')
        self.git(self.destination, 'update-index', '--assume-unchanged', 'existing.txt')
        self.assertEqual(self.cli('apply')[0], 1)
        self.git(self.destination, 'update-index', '--no-assume-unchanged', 'existing.txt')
        self.git(self.destination, 'update-index', '--skip-worktree', 'existing.txt')
        self.assertEqual(self.cli('apply')[0], 1)
        self.request['revision'] = self.request['revision'][:12]
        self.assertEqual(self.cli('preview')[0], 1)

    def test_paths_symlinks_and_inventory_precheck(self):
        for path in ('../escape', '/absolute', '.git/config', 'nested/../escape'):
            self.request['resources'][0]['destination'] = path
            self.assertEqual(self.cli('apply')[0], 1)
        (self.destination / 'link').symlink_to(self.root, target_is_directory=True)
        self.request['resources'][0]['destination'] = 'link/file'
        self.assertEqual(self.cli('apply')[0], 1)
        (self.destination / 'link').unlink()
        self.request['resources'][0]['destination'] = 'adopted.txt'
        self.request['resources'].append(dict(source='missing', destination='second.txt', expected_destination_sha256=None))
        self.assertEqual(self.cli('apply')[0], 1)
        self.assertFalse((self.destination / 'adopted.txt').exists())

    def test_replacement_count_and_duplicate(self):
        self.request['resources'][0]['replacements'][0]['expected_count'] = 2
        self.assertEqual(self.cli('apply')[0], 1)
        self.request['resources'][0]['replacements'][0]['expected_count'] = 1
        self.request['resources'].append(self.request['resources'][0].copy())
        self.assertEqual(self.cli('apply')[0], 1)

    def test_failure_rolls_back_and_reports_failed_rollback(self):
        self.request['resources'].append(dict(source='source.txt', destination='nested/second.txt', expected_destination_sha256=None))
        original = adoption._atomic
        calls = []
        def fail_second(path, data, mode):
            calls.append(path)
            if len(calls) == 2:
                raise OSError('injected write failure')
            return original(path, data, mode)
        with patch.object(adoption, '_atomic', fail_second):
            report = adoption.adopt(self.request, 'apply')
        self.assertEqual(report['status'], 'rolled_back')
        self.assertFalse((self.destination / 'adopted.txt').exists())
        self.assertFalse((self.destination / 'nested').exists())

    def test_existing_identity_and_mode(self):
        resource = self.request['resources'][0]
        resource['destination'] = 'existing.txt'
        resource['expected_destination_sha256'] = hashlib.sha256(b'existing\n').hexdigest()
        os.chmod(self.destination / 'existing.txt', 0o755)
        self.git(self.destination, 'add', '.')
        self.git(self.destination, 'commit', '-qm', 'mode')
        self.assertEqual(self.cli('apply')[0], 0)
        self.assertEqual((self.destination / 'existing.txt').stat().st_mode & 0o777, 0o755)
        self.assertEqual(self.cli('apply')[1]['status'], 'unchanged')

    def test_public_cli_native_metadata_alias_is_readonly(self):
        config = self.destination / '.git' / 'config'
        before = config.read_bytes()
        alias = self.destination / '.GIT'
        if not alias.exists() or not alias.samefile(self.destination / '.git'):
            self.skipTest('Temporary filesystem does not alias .GIT to .git')
        resource = self.request['resources'][0]
        resource['destination'] = '.GIT/config'
        resource['expected_destination_sha256'] = hashlib.sha256(before).hexdigest()
        for mode in ('preview', 'verify', 'apply'):
            code, report = self.cli(mode)
            self.assertEqual(code, 1)
            self.assertEqual(report['status'], 'error')
            self.assertIn('Git metadata', report['error'])
            self.assertEqual(config.read_bytes(), before)
        resource['destination'] = 'ordinary.GIT/config.txt'
        resource['expected_destination_sha256'] = None
        self.assertEqual(self.cli('apply')[0], 0)
        self.assertEqual((self.destination / 'ordinary.GIT/config.txt').read_bytes(), b'hello new\n')
        self.assertEqual(config.read_bytes(), before)

    def test_public_cli_absent_case_aliases_and_ancestor_overlap(self):
        if sys.platform != 'darwin' or os.pathconf(self.destination, 11):
            self.skipTest('Actual case-insensitive Darwin filesystem required')
        first = self.request['resources'][0]
        for left, right in [('A.txt', 'a.txt'), ('Dir/A.txt', 'dir/a.txt'), ('Dir', 'dir/file.txt')]:
            first['destination'] = left
            self.request['resources'] = [first, dict(source='source.txt', destination=right, expected_destination_sha256=None)]
            for mode in ('preview', 'verify', 'apply'):
                code, report = self.cli(mode)
                self.assertEqual(code, 1, report)
                self.assertIn('alias or overlap', report['error'])
                self.assertFalse((self.destination / left).exists())
                self.assertFalse((self.destination / right).exists())

    def test_public_cli_existing_noop_alias_preserves_bytes(self):
        upper = self.destination / 'A.txt'
        upper.write_bytes(b'hello new\n')
        self.git(self.destination, 'add', '.')
        self.git(self.destination, 'commit', '-qm', 'existing alias')
        lower = self.destination / 'a.txt'
        if not lower.exists() or not upper.samefile(lower):
            self.skipTest('Actual filesystem case alias required')
        first = self.request['resources'][0]
        first.update(destination='A.txt', expected_destination_sha256=hashlib.sha256(upper.read_bytes()).hexdigest())
        self.request['resources'].append(dict(source='source.txt', destination='a.txt', expected_destination_sha256=first['expected_destination_sha256']))
        before = upper.read_bytes()
        for mode in ('preview', 'verify', 'apply'):
            self.assertEqual(self.cli(mode)[0], 1)
            self.assertEqual(upper.read_bytes(), before)

    def test_public_cli_existing_ancestor_alias_refuses_before_write(self):
        folder = self.destination / 'Dir'
        folder.mkdir()
        (folder / 'keep').write_bytes(b'preserved')
        self.git(self.destination, 'add', '.')
        self.git(self.destination, 'commit', '-qm', 'existing directory')
        if not (self.destination / 'dir').exists() or not folder.samefile(self.destination / 'dir'):
            self.skipTest('Actual filesystem directory alias required')
        self.request['resources'][0]['destination'] = 'Dir/A.txt'
        self.request['resources'].append(dict(source='source.txt', destination='dir/a.txt', expected_destination_sha256=None))
        self.assertEqual(self.cli('apply')[0], 1)
        self.assertEqual((folder / 'keep').read_bytes(), b'preserved')
        self.assertFalse((folder / 'A.txt').exists())

    def test_public_cli_nested_repository_and_submodule_refusal(self):
        self.git(self.destination, '-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', str(self.source), 'sub')
        self.git(self.destination, 'commit', '-qam', 'submodule')
        pointer = self.destination / 'sub/.git'
        before = pointer.read_bytes()
        metadata = (self.destination / '.git/config').read_bytes()
        for location in ('sub/new.txt', 'sub/.GIT'):
            self.request['resources'] = [self.request['resources'][0], dict(source='source.txt', destination=location, expected_destination_sha256=None)]
            for mode in ('preview', 'verify', 'apply'):
                code, report = self.cli(mode)
                self.assertEqual(code, 1, report)
                self.assertIn('Nested repository', report['error'])
                self.assertEqual(pointer.read_bytes(), before)
                self.assertEqual((self.destination / '.git/config').read_bytes(), metadata)
                self.assertFalse((self.destination / 'adopted.txt').exists())
                self.assertEqual(self.git(self.destination / 'sub', 'rev-parse', 'HEAD').strip(), self.request['revision'])
        nested = self.destination / 'nested'
        nested.mkdir()
        self.git(nested, 'init', '-q')
        self.request['resources'] = [dict(source='source.txt', destination='nested/new.txt', expected_destination_sha256=None)]
        self.assertEqual(self.cli('apply')[0], 1)
        self.assertFalse((nested / 'new.txt').exists())

    def test_public_cli_actual_case_sensitive_distinct_paths(self):
        upper, lower = self.destination / 'A.txt', self.destination / 'a.txt'
        upper.write_bytes(b'upper')
        lower.write_bytes(b'lower')
        if upper.samefile(lower):
            self.skipTest('Actual case-sensitive filesystem required')
        self.git(self.destination, 'add', '.')
        self.git(self.destination, 'commit', '-qm', 'distinct names')
        self.request['resources'] = [dict(source='source.txt', destination=name, expected_destination_sha256=hashlib.sha256((self.destination / name).read_bytes()).hexdigest()) for name in ('A.txt', 'a.txt')]
        self.assertEqual(self.cli('apply')[0], 0)
        self.assertEqual(upper.read_bytes(), b'hello old\n')
        self.assertEqual(lower.read_bytes(), b'hello old\n')
        self.assertEqual(self.cli('verify')[0], 0)

    def test_public_cli_hardlinked_destinations_refuse_before_write(self):
        first = self.destination / 'first.txt'
        first.write_bytes(b'preserved')
        (self.destination / 'nested').mkdir()
        os.link(first, self.destination / 'nested/other.txt')
        self.git(self.destination, 'add', '.')
        self.git(self.destination, 'commit', '-qm', 'hardlinked names')
        self.request['resources'] = [dict(source='source.txt', destination=name, expected_destination_sha256=hashlib.sha256(b'preserved').hexdigest()) for name in ('first.txt', 'nested/other.txt')]
        self.assertEqual(self.cli('apply')[0], 1)
        self.assertEqual(first.read_bytes(), b'preserved')
        self.assertEqual((self.destination / 'nested/other.txt').read_bytes(), b'preserved')

    def test_public_cli_absent_unicode_alias_is_explicitly_unsupported(self):
        self.request['resources'][0]['destination'] = '\u00e9.txt'
        self.request['resources'].append(dict(source='source.txt', destination='e\u0301.txt', expected_destination_sha256=None))
        code, report = self.cli('apply')
        self.assertEqual(code, 1)
        self.assertIn('Unsupported absent Unicode', report['error'])
        self.assertFalse((self.destination / '\u00e9.txt').exists())

    def test_unknown_host_absent_case_policy_is_not_assumed(self):
        with patch.object(adoption.sys, 'platform', 'unknown'):
            with self.assertRaisesRegex(adoption.AdoptionError, 'Unsupported absent'):
                adoption._same_component(self.destination, 'A.txt', 'a.txt')
            self.assertFalse(adoption._same_component(self.destination, 'one.txt', 'two.txt'))

    def test_portable_absent_case_sensitive_policy_control(self):
        with patch.object(adoption.sys, 'platform', 'darwin'), patch.object(adoption.os, 'pathconf', return_value=1) as query:
            self.assertFalse(adoption._same_component(self.destination, 'A.txt', 'a.txt'))
            query.assert_called_once_with(self.destination, 11)
        with patch.object(adoption.sys, 'platform', 'darwin'), patch.object(adoption.os, 'pathconf', return_value=0):
            self.assertTrue(adoption._same_component(self.destination, 'A.txt', 'a.txt'))
