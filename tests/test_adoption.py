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
