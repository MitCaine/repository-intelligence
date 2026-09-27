"""The updater keeps exact pins and unrelated settings intact."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_modules import actions, editor, python_packages  # noqa: E402


class UpdateTests(unittest.TestCase):
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
            with self.assertRaisesRegex(ValueError, 'Expected one current pin'):
                python_packages.set_pin(path, 'wheel', '1.0', '1.2')

    def test_known_crashing_runtime_is_not_proposed_on_a_fresh_checkout(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'pyproject.toml'
            path.write_text('"tree-sitter==0.25.1"\n', encoding='utf-8')
            with mock.patch.object(python_packages, 'latest', return_value='0.26.0'):
                self.assertEqual(python_packages.proposals(path), [])

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
