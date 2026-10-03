"""Managed CLI selection preserves attempts and checks the actual catalog route."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update_modules import codex


class CodexUpdateTests(unittest.TestCase):
    def test_actual_catalog_handshake_pagination_and_no_turn(self):
        with tempfile.TemporaryDirectory() as raw:
            executable = Path(raw) / 'codex'
            executable.write_text('#!' + str(Path(sys.executable).resolve()) + '\n' + '''import json,sys
assert sys.argv[1:] == ['app-server']
assert json.loads(input())['method'] == 'initialize'
print(json.dumps({'id':1,'result':{}}),flush=True)
assert json.loads(input())['method'] == 'initialized'
for identity,cursor in [(2,None),(3,'page2')]:
 request=json.loads(input())
 assert request['method']=='model/list' and request['params']['cursor']==cursor
 print(json.dumps({'method':'account/updated','params':{}}),flush=True)
 print(json.dumps({'id':identity,'result':{'data':[{'model':'chosen','supportedReasoningEfforts':[{'reasoningEffort':'low'}]}],'nextCursor':'page2' if identity==2 else None}}),flush=True)
''')
            executable.chmod(0o755)
            models = codex.catalog(executable)
            self.assertEqual(models, [{'model': 'chosen', 'efforts': ['low']}] * 2)
            codex.validate_pairs(models, ['chosen:low'])
            with self.assertRaisesRegex(ValueError, 'unsupported'):
                codex.validate_pairs(models, ['chosen:max'])

    def test_catalog_deadline_reaps_process(self):
        with tempfile.TemporaryDirectory() as raw:
            executable = Path(raw) / 'codex'
            executable.write_text('#!' + str(Path(sys.executable).resolve()) + '\nimport time\ntime.sleep(30)\n')
            executable.chmod(0o755)
            with self.assertRaisesRegex(TimeoutError, 'timed out'):
                codex.catalog(executable, timeout=.1)

    def test_ended_catalog_preserves_request_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            executable = Path(raw) / 'codex'
            executable.write_text('#!' + str(Path(sys.executable).resolve()) + '\nraise SystemExit(1)\n')
            executable.chmod(0o755)
            with mock.patch.object(codex.os, 'killpg', side_effect=PermissionError) as kill:
                with self.assertRaisesRegex(ValueError, 'ended before response'):
                    codex.catalog(executable)
                kill.assert_not_called()

    def test_failed_new_selection_preserves_old_runtime_and_pointer(self):
        with tempfile.TemporaryDirectory() as raw:
            cache = Path(raw)
            version = ['1.0.0']
            installs = []

            def output(argv, **kwargs):
                return json.dumps(version[0]).encode() if 'view' in argv else 'codex-cli ' + version[0] + '\n'

            def install(argv, **kwargs):
                prefix = Path(argv[argv.index('--prefix') + 1])
                target = prefix / 'node_modules/.bin/codex'
                target.parent.mkdir(parents=True)
                target.write_text('launcher ' + version[0])
                (prefix / 'native').write_text('native ' + version[0])
                installs.append(prefix)
                return subprocess.CompletedProcess(argv, 0)

            with mock.patch.object(codex.shutil, 'which', return_value='/npm'), \
                 mock.patch.object(codex.subprocess, 'check_output', side_effect=output), \
                 mock.patch.object(codex.subprocess, 'run', side_effect=install), \
                 mock.patch.object(codex, 'catalog', return_value=[{'model':'chosen','efforts':['low']}]) as catalog:
                first = codex.update(cache, ['chosen:low'])
                selection = cache / 'codex/selected.json'
                original = selection.read_bytes()
                old_native = (installs[0] / 'native').read_bytes()
                codex.update(cache, ['chosen:low'])
                self.assertEqual(len(installs), 1)
                version[0] = '1.1.0'
                with self.assertRaisesRegex(ValueError, 'unsupported'):
                    codex.update(cache, ['chosen:max'])
                self.assertEqual(selection.read_bytes(), original)
                self.assertEqual((installs[0] / 'native').read_bytes(), old_native)
                second = codex.update(cache, ['chosen:low'])
                self.assertNotEqual(second['executable'], first['executable'])
                self.assertFalse(second['consumer_route_qualified'])
                self.assertFalse(second['inference_access_verified'])
                (Path(second['prefix']) / 'native').write_text('tampered native')
                calls = catalog.call_count
                with self.assertRaisesRegex(ValueError, 'changed'):
                    codex.update(cache, ['chosen:low'])
                self.assertEqual(catalog.call_count, calls)

    def test_installation_digest_includes_native_and_symlink_target(self):
        with tempfile.TemporaryDirectory() as raw:
            prefix = Path(raw) / 'runtime'; prefix.mkdir()
            native = prefix / 'native'; native.write_bytes(b'original')
            (prefix / 'entry').symlink_to(native)
            before = codex.installation_digest(prefix)
            native.write_bytes(b'changed')
            self.assertNotEqual(before, codex.installation_digest(prefix))
            (prefix / 'entry').unlink(); (prefix / 'entry').symlink_to(Path(raw) / 'outside')
            (Path(raw) / 'outside').write_bytes(b'external')
            with self.assertRaises(ValueError):
                codex.installation_digest(prefix)
