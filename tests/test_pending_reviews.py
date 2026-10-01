"""Two actual updater invocations; release discovery and qualification are fixtures."""
from contextlib import ExitStack
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update
from update_modules import review_obligations


class PendingReviewTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        raw = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(raw)
        self.cache = self.root / '.ri-cache'
        self.manifest = self.root / 'pyproject.toml'
        self.manifest.write_text('[build-system]\nrequires=[]\n[project]\n'
                                 'dependencies=["tree-sitter==1"]\n')
        workflows = self.root / '.github/workflows'
        workflows.mkdir(parents=True)
        (workflows / 'verify.yml').write_text('uses: example@old\n')
        for args in (['init', '-q'], ['add', '.'],
                     ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '-qm', 'base']):
            subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True)

        for name, value in {'ROOT': self.root, 'CACHE': self.cache,
                'SELECTION': self.cache / 'selected-python.json',
                'JOURNAL': self.cache / 'update-recovery.json',
                'RESULT': self.cache / 'update-result.json',
                'REJECTIONS': self.cache / 'rejected-updates.json'}.items():
            self.stack.enter_context(mock.patch.object(update, name, value))
        self.stack.enter_context(mock.patch.object(update, 'source_commit', return_value='a' * 40))
        self.python = self.root / 'candidate/bin/python'
        self.stack.enter_context(mock.patch.object(update, 'ensure_python', return_value=(self.python, False)))
        self.stack.enter_context(mock.patch.object(update, 'new_candidate', return_value=self.python))
        self.stack.enter_context(mock.patch.object(update, 'rejection_context', return_value='fixture'))
        self.stack.enter_context(mock.patch.object(update, 'run'))
        self.stack.enter_context(mock.patch.object(update.editor, 'configure'))
        self.stack.enter_context(mock.patch.object(sys, 'stdout', io.StringIO()))
        self.stack.enter_context(mock.patch.object(sys, 'stderr', io.StringIO()))

    def invoke(self, *flags, proposals=(), action_changes=()):
        with mock.patch.object(sys, 'argv', ['update.py', *flags]), \
                mock.patch.object(update.python_packages, 'proposals', return_value=list(proposals)), \
                mock.patch.object(update.actions, 'update', return_value=list(action_changes)):
            code = update.main()
        return code, json.loads(update.RESULT.read_text())

    def test_two_runs_carry_over_and_resolve_obligations_independently(self):
        code, first = self.invoke(proposals=[('tree-sitter', '1', '2')], action_changes=['changed'])
        self.assertEqual(code, 0)
        self.assertEqual(first['disposition'], 'review_required')
        self.assertEqual(set(first['pending_reviews']), {'grammar:tree-sitter', 'actions:workflows'})
        code, second = self.invoke('--offline')
        self.assertEqual(second['package_changes'], [])
        self.assertEqual(second['disposition'], 'review_required')
        key = 'grammar:tree-sitter'
        code, third = self.invoke('--offline', '--resolve-review', key + '=' + second['pending_reviews'][key]['sha256'])
        self.assertEqual(set(third['pending_reviews']), {'actions:workflows'})
        key = 'actions:workflows'
        code, final = self.invoke('--offline', '--resolve-review', key + '=' + third['pending_reviews'][key]['sha256'])
        self.assertEqual(final['disposition'], 'completed')

    def test_supersession_requires_new_subject_resolution(self):
        _, first = self.invoke(proposals=[('tree-sitter', '1', '2')])
        _, second = self.invoke(proposals=[('tree-sitter', '2', '3')])
        key = 'grammar:tree-sitter'
        self.assertNotEqual(first['pending_reviews'][key]['sha256'], second['pending_reviews'][key]['sha256'])
        code, result = self.invoke('--offline', '--resolve-review', key + '=' + first['pending_reviews'][key]['sha256'])
        self.assertEqual(code, 1)
        self.assertEqual(result['disposition'], 'failed')
        self.assertIn(key, review_obligations.load(update.pending_path()))

    def test_dirty_and_staged_source_changes_invalidate_resolution(self):
        _, first = self.invoke(proposals=[('tree-sitter', '1', '2')])
        (self.root / 'src').mkdir()
        path = self.root / 'src' / 'fixture.py'
        path.write_text('value = 1\n')
        subprocess.run(['git', 'add', 'src/fixture.py'], cwd=self.root, check=True)
        _, second = self.invoke('--offline')
        key = 'grammar:tree-sitter'
        self.assertNotEqual(first['pending_reviews'][key]['sha256'], second['pending_reviews'][key]['sha256'])
        path.write_text('value = 2\n')
        _, third = self.invoke('--offline')
        self.assertNotEqual(second['pending_reviews'][key]['sha256'], third['pending_reviews'][key]['sha256'])

    def test_interruption_and_failure_preserve_pending_state(self):
        self.invoke(proposals=[('tree-sitter', '1', '2')])
        before = update.pending_path().read_bytes()
        for error, code in ((KeyboardInterrupt(), 130), (OSError('unavailable'), 1)):
            with mock.patch.object(update, 'ensure_python', side_effect=error):
                actual, result = self.invoke('--offline')
            self.assertEqual(actual, code)
            self.assertEqual(result['disposition'], 'failed')
            self.assertEqual(update.pending_path().read_bytes(), before)

    def test_clean_initial_run_and_legacy_result_import(self):
        _, initial = self.invoke('--offline')
        self.assertEqual(initial['disposition'], 'completed')
        update.pending_path().unlink()
        initial['package_changes'] = ['tree-sitter']
        initial['outstanding_qualification'] = ['upstream grammar and node review']
        update.RESULT.write_text(json.dumps(initial))
        _, imported = self.invoke('--offline')
        self.assertEqual(imported['disposition'], 'review_required')
        self.assertIn('grammar:tree-sitter', imported['pending_reviews'])
