"""Selected parser features do not change legacy helper dependency requirements."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest

BLOCK = '''
import importlib.abc, sys
class NoParsers(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'tree_sitter' or fullname.startswith('tree_sitter_'):
            raise ModuleNotFoundError('fixture parser unavailable: ' + fullname, name=fullname)
sys.meta_path.insert(0, NoParsers())
'''


class WorkerParserBoundaryTests(unittest.TestCase):
    def child(self, text, *, missing=None):
        block = BLOCK if missing is None else BLOCK.replace(
            "fullname == 'tree_sitter' or fullname.startswith('tree_sitter_')",
            f"fullname == {missing!r}")
        return subprocess.run([sys.executable, '-c', block + text],
                              text=True, capture_output=True, env=os.environ.copy())

    def test_legacy_helper_cli_help_does_not_import_parsers(self):
        result = self.child('''
from repository_intelligence import worker_execution
raise SystemExit(worker_execution.main(['--help']))
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--mode', result.stdout)

    def test_legacy_helper_and_cleanup_use_work_without_parsers(self):
        result = self.child('''
import tempfile
from pathlib import Path
from repository_intelligence.worker_execution import identity, accepted_inventory
from repository_intelligence import output_cleanup, dispatch_guard
assert accepted_inventory({}) is None
with tempfile.TemporaryDirectory() as directory:
    p=Path(directory)/'owned';p.write_bytes(b'legacy')
    assert identity(p)['sha256']=='c49fea7425fa7f8699897a97c159c6690267d9003bb78c53fafa8fc15c325d84'
assert not any(n=='tree_sitter' or n.startswith('tree_sitter_') for n in __import__('sys').modules)
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_prepared_execution_finishes_without_parsers(self):
        tests = str(Path(__file__).resolve().parent)
        result = self.child(f'''
sys.path.insert(0, {tests!r})
from test_worker_execution import WorkerExecutionTests
from repository_intelligence.worker_execution import execute
fixture = WorkerExecutionTests()
fixture.setUp()
try:
    execute(fixture.request, fixture.evidence, 'prepare')
    result = execute(fixture.request, fixture.evidence, 'run')
    assert result['review_ready'], result
finally:
    fixture.doCleanups()
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_selected_derivation_reports_missing_dependency_without_fallback(self):
        source = b'## Checks\n```ri-obligations\n{}\n```\n'
        binding = {'path': 'task.md', 'sha256': hashlib.sha256(source).hexdigest(),
                   'phase': 'implementation', 'route': 'normal'}
        for missing in (None, 'tree_sitter_markdown'):
            with self.subTest(missing=missing):
                result = self.child(f'''
from repository_intelligence.obligation_reconciliation import derive
try:
    derive({source!r}, {binding!r})
except ValueError as error:
    assert 'parser dependencies' in str(error), str(error)
    assert 'pyproject.toml' in str(error), str(error)
    print(str(error))
else:
    raise AssertionError('missing parser must not use a fallback')
''', missing=missing)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('parser dependencies', result.stdout)
