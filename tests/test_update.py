"""The updater keeps exact pins and unrelated settings intact."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import io


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update as updater  # noqa: E402
from update_modules import actions, editor, python_packages  # noqa: E402


class UpdateTests(unittest.TestCase):
    def test_readiness_classifies_grammar_upgrade(self):
        result = updater.readiness_result(Path('candidate/bin/python'),
                                          ['tree-sitter-python'], [], True, [])
        self.assertTrue(result['local_verify_passed'])
        self.assertEqual(result['outstanding_qualification'],
                         ['upstream grammar and node review'])

    def test_readiness_classifies_action_update(self):
        result = updater.readiness_result(Path('candidate/bin/python'), [],
                                          ['actions/checkout: v1 -> v2'], True, [])
        self.assertTrue(result['local_verify_passed'])
        self.assertEqual(result['outstanding_qualification'],
                         ['hosted Verify for changed GitHub Actions'])

    def test_readiness_classifies_clean_local_run(self):
        result = updater.readiness_result(Path('.venv/bin/python'), [], [], True, [])
        self.assertEqual(result['outstanding_qualification'], [])
        self.assertTrue(result['local_verify_passed'])
        self.assertEqual(result['package_changes'], [])
        self.assertEqual(result['action_changes'], [])

    def test_package_proposals_change_only_the_selected_exact_pin(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'pyproject.toml'
            path.write_text('[build-system]\nrequires = ["wheel==1.0"]\n'
                            '[project]\ndependencies = ["tree-sitter==2.0"]\n',
                            encoding='utf-8')
            with mock.patch.object(python_packages, 'latest',
                                   side_effect=lambda name: {'wheel': '1.1',
                                                             'tree-sitter': '2.0'}[name]):
                self.assertEqual(python_packages.proposals(path), [('wheel', '1.0', '1.1')])
            python_packages.set_pin(path, 'wheel', '1.0', '1.1')
            self.assertIn('"tree-sitter==2.0"', path.read_text(encoding='utf-8'))
            with self.assertRaisesRegex(ValueError, 'Expected a current pin'):
                python_packages.set_pin(path, 'wheel', '1.0', '1.2')

    def test_known_crashing_runtime_is_not_proposed_on_a_fresh_checkout(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'pyproject.toml'
            path.write_text('[build-system]\nrequires = []\n[project]\n'
                            'dependencies = ["tree-sitter==0.25.1"]\n', encoding='utf-8')
            with mock.patch.object(python_packages, 'latest', return_value='0.26.0'):
                self.assertEqual(python_packages.proposals(path), [])

    def test_lower_release_is_not_an_update(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'pyproject.toml'
            path.write_text('[build-system]\nrequires = ["builder==3.0"]\n'
                            '[project]\ndependencies = []\n', encoding='utf-8')
            with mock.patch.object(python_packages, 'latest', return_value='2.0'):
                self.assertEqual(python_packages.proposals(path), [])

    def test_prerelease_response_is_not_called_stable(self):
        payload = b'{"info":{"version":"2.0rc1"},"urls":'
        payload += b'[{"packagetype":"bdist_wheel","yanked":false}]}'
        with mock.patch.object(python_packages, 'urlopen') as open_url:
            open_url.return_value.__enter__.return_value = io.BytesIO(payload)
            with self.assertRaisesRegex(ValueError, 'non-stable'):
                python_packages.latest('builder')

    def test_manifest_parser_ignores_comments_and_edits_both_pin_groups(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'pyproject.toml'
            path.write_text('[build-system]\nrequires = [\'Tree_Sitter==0.25.1\']\n'
                            '[project]\ndependencies = ["tree-sitter==0.25.1"]\n'
                            '# "fake==1.0"\n', encoding='utf-8')
            with mock.patch.object(python_packages, 'latest', return_value='0.26.0'):
                self.assertEqual(python_packages.proposals(path), [])
            python_packages.set_pin(path, 'tree-sitter', '0.25.1', '0.25.2')
            self.assertIn("'Tree_Sitter==0.25.2'", path.read_text(encoding='utf-8'))
            self.assertIn('"tree-sitter==0.25.2"', path.read_text(encoding='utf-8'))
            self.assertIn('# "fake==1.0"', path.read_text(encoding='utf-8'))

    def test_migration_uses_separate_candidate_without_clearing_current(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            current = root / '.venv' / 'bin' / 'python'
            current.parent.mkdir(parents=True)
            current.touch()

            def version(command, **_kwargs):
                return subprocess.CompletedProcess(command, 0, '3.13\n' if str(current) == command[0]
                                                   else '3.14\n', '')

            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'VENV', root / '.venv'), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'SELECTION', root / '.ri-cache' / 'selected-python.json'), \
                    mock.patch.object(updater.shutil, 'which', side_effect=lambda name: name), \
                    mock.patch.object(updater.subprocess, 'run', side_effect=version), \
                    mock.patch.object(updater, 'run') as run:
                candidate, migrating = updater.ensure_python(migrate=True)
            self.assertTrue(migrating)
            self.assertEqual(candidate, root / '.ri-cache' / 'venvs' / 'python3.14' / 'bin' / 'python')
            self.assertTrue(current.exists())
            self.assertNotIn('--clear', run.call_args.args)

    def test_failed_candidate_does_not_change_selected_interpreter(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'pyproject.toml').write_text('original', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)
            selection = root / '.ri-cache' / 'selected-python.json'
            selection.parent.mkdir()
            selection.write_text('{"path":".venv/bin/python"}\n', encoding='utf-8')
            candidate = root / '.ri-cache' / 'venvs' / 'python3.14' / 'bin' / 'python'
            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'RESULT', root / '.ri-cache' / 'update-result.json'), \
                    mock.patch.object(updater, 'REJECTIONS', root / '.ri-cache' / 'rejected-updates.json'), \
                    mock.patch.object(updater, 'SELECTION', selection), \
                    mock.patch.object(updater, 'ensure_python', return_value=(candidate, True)), \
                    mock.patch.object(updater, 'run', side_effect=subprocess.CalledProcessError(1, 'prepare')), \
                    mock.patch.object(sys, 'argv', ['update.py', '--offline', '--migrate-python']):
                self.assertEqual(updater.main(), 1)
            self.assertEqual(selection.read_text(encoding='utf-8'),
                             '{"path":".venv/bin/python"}\n')

    def test_native_timeout_does_not_erase_qualified_package_candidate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / 'pyproject.toml'
            manifest.write_text('"wheel==1"', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)

            def change_pin(path, _name, old, new):
                path.write_text(path.read_text(encoding='utf-8').replace(f'=={old}', f'=={new}'),
                                encoding='utf-8')

            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'RESULT', root / '.ri-cache' / 'update-result.json'), \
                    mock.patch.object(updater, 'REJECTIONS', root / '.ri-cache' / 'rejected-updates.json'), \
                    mock.patch.object(updater, 'SELECTION', root / '.ri-cache' / 'selected-python.json'), \
                    mock.patch.object(updater, 'ensure_python', return_value=(root / '.venv/bin/python', False)), \
                    mock.patch.object(updater, 'new_candidate', return_value=root / 'candidate/bin/python'), \
                    mock.patch.object(updater, 'rejection_context', return_value='context'), \
                    mock.patch.object(updater.python_packages, 'proposals', return_value=[('wheel', '1', '2')]), \
                    mock.patch.object(updater.python_packages, 'set_pin', side_effect=change_pin), \
                    mock.patch.object(updater, 'run'), \
                    mock.patch.object(updater.native, 'update',
                                      side_effect=subprocess.TimeoutExpired('rustup', 1)), \
                    mock.patch.object(sys, 'argv', ['update.py', '--native']):
                self.assertEqual(updater.main(), 1)
            self.assertEqual(manifest.read_text(encoding='utf-8'), '"wheel==2"')
            self.assertEqual(json.loads((root / '.ri-cache' / 'selected-python.json').read_text())['path'],
                             'candidate/bin/python')
            self.assertFalse((root / '.ri-cache' / 'update-result.json').exists())

    def test_transient_preparation_failure_does_not_cache_rejection(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / 'pyproject.toml'
            manifest.write_text('"wheel==1"', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)

            def change_pin(path, _name, old, new):
                path.write_text(path.read_text(encoding='utf-8').replace(f'=={old}', f'=={new}'),
                                encoding='utf-8')

            calls = []
            def run(*args, **_kwargs):
                calls.append(args)
                if args[-1] == 'prepare':
                    raise subprocess.TimeoutExpired('pip download', 1)

            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'RESULT', root / '.ri-cache' / 'update-result.json'), \
                    mock.patch.object(updater, 'REJECTIONS', root / '.ri-cache' / 'rejected-updates.json'), \
                    mock.patch.object(updater, 'SELECTION', root / '.ri-cache' / 'selected-python.json'), \
                    mock.patch.object(updater, 'ensure_python', return_value=(root / '.venv/bin/python', False)), \
                    mock.patch.object(updater, 'new_candidate', return_value=root / 'candidate/bin/python'), \
                    mock.patch.object(updater, 'rejection_context', return_value='context'), \
                    mock.patch.object(updater.python_packages, 'proposals', return_value=[('wheel', '1', '2')]), \
                    mock.patch.object(updater.python_packages, 'set_pin', side_effect=change_pin), \
                    mock.patch.object(updater, 'run', side_effect=run), \
                    mock.patch.object(sys, 'argv', ['update.py', '--skip-actions']):
                self.assertEqual(updater.main(), 0)
            self.assertEqual(manifest.read_text(encoding='utf-8'), '"wheel==1"')
            self.assertFalse((root / '.ri-cache' / 'rejected-updates.json').exists())

    def test_interrupted_verification_restores_pin_without_selecting_candidate(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / 'pyproject.toml'
            manifest.write_text('"wheel==1"', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)
            selection = root / '.ri-cache' / 'selected-python.json'
            selection.parent.mkdir()
            selection.write_text('{"path":".venv/bin/python"}\n', encoding='utf-8')

            def change_pin(path, _name, old, new):
                path.write_text(path.read_text().replace(f'=={old}', f'=={new}'))

            def run(*args, **_kwargs):
                if args[-1] == 'verify':
                    raise KeyboardInterrupt()

            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'SELECTION', selection), \
                    mock.patch.object(updater, 'new_candidate', return_value=root / 'candidate/bin/python'), \
                    mock.patch.object(updater, 'rejection_context', return_value='context'), \
                    mock.patch.object(updater.python_packages, 'set_pin', side_effect=change_pin), \
                    mock.patch.object(updater, 'run', side_effect=run):
                with self.assertRaises(KeyboardInterrupt):
                    updater.update_packages(root / '.venv/bin/python', manifest,
                                            [('wheel', '1', '2')], {})
            self.assertEqual(manifest.read_text(), '"wheel==1"')
            self.assertEqual(selection.read_text(), '{"path":".venv/bin/python"}\n')
            self.assertFalse((root / '.ri-cache' / 'update-recovery.json').exists())

    def test_next_launch_restores_an_abruptly_interrupted_manifest_and_selection(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / 'pyproject.toml'
            manifest.write_text('old pin', encoding='utf-8')
            workflow = root / '.github' / 'workflows' / 'verify.yml'
            workflow.parent.mkdir(parents=True)
            workflow.write_text('old action', encoding='utf-8')
            selection = root / '.ri-cache' / 'selected-python.json'
            selection.parent.mkdir()
            selection.write_text('{"path":"old/bin/python"}\n', encoding='utf-8')
            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'SELECTION', selection):
                updater.begin_recovery()
                manifest.write_text('candidate pin', encoding='utf-8')
                workflow.write_text('candidate action', encoding='utf-8')
                selection.write_text('{"path":"candidate/bin/python"}\n', encoding='utf-8')
                self.assertTrue(updater.recover())
                self.assertFalse(updater.recover())
            self.assertEqual(manifest.read_text(), 'old pin')
            self.assertEqual(workflow.read_text(), 'old action')
            self.assertEqual(selection.read_text(), '{"path":"old/bin/python"}\n')

    def test_promotion_interruption_restores_old_selection(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / 'pyproject.toml'
            manifest.write_text('"wheel==1"', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)
            selection = root / '.ri-cache' / 'selected-python.json'
            selection.parent.mkdir()
            selection.write_text('{"path":".venv/bin/python"}\n', encoding='utf-8')

            def change_pin(path, _name, old, new):
                path.write_text(path.read_text().replace(f'=={old}', f'=={new}'))

            def interrupted_select(candidate):
                updater.atomic_write(selection, (json.dumps({'path': str(candidate.relative_to(root))}) + '\n').encode())
                raise KeyboardInterrupt()

            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'SELECTION', selection), \
                    mock.patch.object(updater, 'new_candidate', return_value=root / 'candidate/bin/python'), \
                    mock.patch.object(updater, 'rejection_context', return_value='context'), \
                    mock.patch.object(updater.python_packages, 'set_pin', side_effect=change_pin), \
                    mock.patch.object(updater, 'run'), \
                    mock.patch.object(updater, 'select_python', side_effect=interrupted_select):
                with self.assertRaises(KeyboardInterrupt):
                    updater.update_packages(root / '.venv/bin/python', manifest,
                                            [('wheel', '1', '2')], {})
            self.assertEqual(manifest.read_text(), '"wheel==1"')
            self.assertEqual(selection.read_text(), '{"path":".venv/bin/python"}\n')

    def test_verified_candidate_promotes_without_installing_into_old_python(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / 'pyproject.toml'
            manifest.write_text('"wheel==1"', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)
            current = root / '.venv/bin/python'
            candidate = root / 'candidate/bin/python'

            def change_pin(path, _name, old, new):
                path.write_text(path.read_text().replace(f'=={old}', f'=={new}'))

            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'SELECTION', root / '.ri-cache' / 'selected-python.json'), \
                    mock.patch.object(updater, 'new_candidate', return_value=candidate), \
                    mock.patch.object(updater, 'rejection_context', return_value='context'), \
                    mock.patch.object(updater.python_packages, 'set_pin', side_effect=change_pin), \
                    mock.patch.object(updater, 'run') as run:
                selected, review, changed = updater.update_packages(current, manifest,
                                            [('wheel', '1', '2')], {})
            self.assertEqual((selected, review, changed), (candidate, [], ['wheel']))
            self.assertEqual(manifest.read_text(), '"wheel==2"')
            self.assertEqual(json.loads((root / '.ri-cache' / 'selected-python.json').read_text())['path'],
                             'candidate/bin/python')
            self.assertTrue(all(call.args[0] == str(candidate) for call in run.call_args_list))

    def test_rejection_cache_is_bound_to_qualification_context(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest = root / 'pyproject.toml'
            manifest.write_text('"wheel==1"', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)
            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'SELECTION', root / '.ri-cache' / 'selected-python.json'), \
                    mock.patch.object(updater, 'rejection_context', return_value='new-context'), \
                    mock.patch.object(updater.python_packages, 'set_pin'), \
                    mock.patch.object(updater, 'new_candidate', side_effect=RuntimeError('retried')):
                with self.assertRaisesRegex(RuntimeError, 'retried'):
                    updater.update_packages(root / '.venv/bin/python', manifest,
                                            [('wheel', '1', '2')],
                                            {'wheel': {'version': '2', 'context': 'old-context'}})

    def test_concurrent_updater_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with mock.patch.object(updater, 'CACHE', root / '.ri-cache'):
                with updater.update_lock():
                    with self.assertRaisesRegex(ValueError, 'Another updater'):
                        with updater.update_lock():
                            pass

    def test_jsonc_editor_settings_do_not_undo_verified_packages(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'pyproject.toml').write_text('manifest', encoding='utf-8')
            (root / '.github' / 'workflows').mkdir(parents=True)
            settings = root / '.vscode' / 'settings.json'
            settings.parent.mkdir()
            settings.write_text('{\n  // user setting\n  "editor.tabSize": 4,\n}\n',
                                encoding='utf-8')
            with mock.patch.object(updater, 'ROOT', root), \
                    mock.patch.object(updater, 'CACHE', root / '.ri-cache'), \
                    mock.patch.object(updater, 'JOURNAL', root / '.ri-cache' / 'update-recovery.json'), \
                    mock.patch.object(updater, 'RESULT', root / '.ri-cache' / 'update-result.json'), \
                    mock.patch.object(updater, 'REJECTIONS', root / '.ri-cache' / 'rejected-updates.json'), \
                    mock.patch.object(updater, 'SELECTION', root / '.ri-cache' / 'selected-python.json'), \
                    mock.patch.object(updater, 'ensure_python', return_value=(root / '.venv/bin/python', False)), \
                    mock.patch.object(updater, 'run'), \
                    mock.patch.object(sys, 'argv', ['update.py', '--offline']):
                self.assertEqual(updater.main(), 0)
            self.assertIn('// user setting', settings.read_text(encoding='utf-8'))

    def test_editor_preserves_other_workspace_settings(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            settings = root / '.vscode' / 'settings.json'
            settings.parent.mkdir()
            settings.write_text('{"editor.tabSize": 4}', encoding='utf-8')
            editor.configure(root)
            self.assertEqual(json.loads(settings.read_text(encoding='utf-8')),
                             {'editor.tabSize': 4,
                              'python.defaultInterpreterPath': '${workspaceFolder}/.venv/bin/python'})

    def test_action_update_keeps_sha_and_release_comment_together(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'verify.yml'
            path.write_text('steps:\n  - uses: actions/checkout@' + 'a' * 40 + ' # v1\n'
                            '  - uses: ./local\n', encoding='utf-8')
            with mock.patch.object(actions, 'release', return_value=('v2', 'b' * 40)):
                self.assertEqual(actions.update(Path(raw)), ['actions/checkout: v1 -> v2'])
            self.assertIn('actions/checkout@' + 'b' * 40 + ' # v2',
                          path.read_text(encoding='utf-8'))
            self.assertIn('uses: ./local', path.read_text(encoding='utf-8'))

    def test_actions_find_named_steps_and_yaml_files(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'verify.yaml'
            path.write_text('steps:\n  - name: Checkout\n    uses: actions/checkout@'
                            + 'a' * 40 + ' # v1\n', encoding='utf-8')
            with mock.patch.object(actions, 'release', return_value=('v2', 'b' * 40)):
                self.assertEqual(actions.update(Path(raw)), ['actions/checkout: v1 -> v2'])
            self.assertIn('uses: actions/checkout@' + 'b' * 40, path.read_text(encoding='utf-8'))
