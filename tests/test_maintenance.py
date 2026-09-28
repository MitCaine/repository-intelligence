"""The maintenance interface keeps observation, preparation, and verification distinct."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'maintain.py'
SPEC = importlib.util.spec_from_file_location('ri_maintenance', SCRIPT)
maintenance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(maintenance)
PINS = {'build': {'builder': '2.0'}, 'runtime': {'parser': '3.0'}}


def prepared_report(*, native='available'):
    return {'packages': [{'name': 'builder', 'matches': True},
                         {'name': 'parser', 'matches': True}],
            'native_tools': {name: {'status': native}
                             for name in ('rustc', 'cargo', 'rust-analyzer')}}


class MaintenanceTests(unittest.TestCase):
    def test_manifest_is_the_only_pin_list_and_accepts_a_new_build_dependency(self):
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / 'pyproject.toml'
            project.write_text('[build-system]\nrequires = ["Builder==2.0", "Extra_Tool==1.1"]\n'
                               '[project]\ndependencies = ["Parser==3.0"]\n')
            self.assertEqual(maintenance.load_pins(project),
                             {'build': {'builder': '2.0', 'extra-tool': '1.1'},
                              'runtime': {'parser': '3.0'}})
            project.write_text('[build-system]\nrequires = ["builder>=2.0"]\n'
                               '[project]\ndependencies = []\n')
            with self.assertRaisesRegex(ValueError, 'exact'):
                maintenance.load_pins(project)

    def test_conflicting_or_duplicate_normalized_names_fail_clearly(self):
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / 'pyproject.toml'
            for build, runtime, message in (
                    ('["Some_Tool==1", "some-tool==1"]', '[]', 'duplicate'),
                    ('["Some_Tool==1"]', '["some-tool==2"]', 'disagree')):
                with self.subTest(build=build):
                    project.write_text(f'[build-system]\nrequires = {build}\n'
                                       f'[project]\ndependencies = {runtime}\n')
                    with self.assertRaisesRegex(ValueError, message):
                        maintenance.load_pins(project)

    def test_status_works_without_packages_and_never_installs_or_downloads(self):
        missing = maintenance.importlib.metadata.PackageNotFoundError
        with mock.patch.object(maintenance.importlib.metadata, 'version', side_effect=missing), \
                mock.patch.object(maintenance.shutil, 'which', return_value=None), \
                mock.patch.object(maintenance.subprocess, 'run') as run:
            report = maintenance.status(PINS)
        self.assertEqual([item['installed'] for item in report['packages']], [None, None])
        self.assertFalse(any(item['matches'] for item in report['packages']))
        self.assertEqual(report['native_tools']['rust-analyzer']['status'], 'missing')
        run.assert_not_called()

    def test_native_proxy_on_path_is_not_a_working_provider(self):
        with mock.patch.object(maintenance.shutil, 'which', return_value='/fake/rust-analyzer'), \
                mock.patch.object(maintenance.subprocess, 'run', return_value=
                                  subprocess.CompletedProcess([], 1, '', 'component missing')) as run:
            report = maintenance.native_status('rust-analyzer')
        self.assertEqual(report['status'], 'unavailable')
        self.assertEqual(report['error'], 'component missing')
        self.assertEqual(run.call_args.kwargs['cwd'], SCRIPT.parent.parent)

    def test_offline_prepare_installs_exact_pins_without_downloading(self):
        with tempfile.TemporaryDirectory() as raw, \
                mock.patch.object(maintenance.sys, 'prefix', '/fixture-venv'), \
                mock.patch.object(maintenance.sys, 'base_prefix', '/fixture-base'), \
                mock.patch.object(maintenance.subprocess, 'run') as run:
            maintenance.prepare(PINS, Path(raw), offline=True)
        self.assertEqual(run.call_count, 1)
        command = run.call_args.args[0]
        self.assertIn('install', command)
        self.assertIn('--no-index', command)
        self.assertIn('builder==2.0', command)
        self.assertIn('parser==3.0', command)
        self.assertEqual(run.call_args.kwargs['env']['PIP_CONFIG_FILE'], os.devnull)

    def test_offline_pip_ignores_inherited_remote_requirements_and_links(self):
        inherited = {name: 'https://example.invalid/unrequested' for name in
                     ('PIP_REQUIREMENT', 'PIP_CONSTRAINT', 'PIP_FIND_LINKS', 'PIP_INDEX_URL')}
        with mock.patch.dict(maintenance.os.environ, inherited):
            environment = maintenance.offline_environment()
        for name in inherited:
            self.assertNotIn(name, environment)
        self.assertEqual(environment['PIP_CONFIG_FILE'], os.devnull)
        self.assertEqual(environment['PIP_NO_INDEX'], '1')

    def test_online_prepare_downloads_before_offline_install(self):
        with tempfile.TemporaryDirectory() as raw, \
                mock.patch.object(maintenance.sys, 'prefix', '/fixture-venv'), \
                mock.patch.object(maintenance.sys, 'base_prefix', '/fixture-base'), \
                mock.patch.object(maintenance.subprocess, 'run') as run:
            maintenance.prepare(PINS, Path(raw), offline=False)
        self.assertEqual(run.call_count, 2)
        self.assertIn('download', run.call_args_list[0].args[0])
        self.assertIn('--only-binary=:all:', run.call_args_list[0].args[0])
        self.assertIn('install', run.call_args_list[1].args[0])
        self.assertIn('--no-index', run.call_args_list[1].args[0])

    def test_prepare_does_not_mutate_a_global_python_environment(self):
        with mock.patch.object(maintenance.sys, 'prefix', '/base'), \
                mock.patch.object(maintenance.sys, 'base_prefix', '/base'), \
                mock.patch.object(maintenance.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'virtual-environment'):
                maintenance.prepare(PINS, Path('/unused'), offline=True)
        run.assert_not_called()

    def test_verify_preserves_test_failure_and_forces_offline_package_check(self):
        with tempfile.TemporaryDirectory() as raw, \
                mock.patch.object(maintenance, 'status', return_value=prepared_report()), \
                mock.patch.object(maintenance.subprocess, 'run', return_value=
                                  subprocess.CompletedProcess([], 7)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            wheelhouse = Path(raw)
            (wheelhouse / 'placeholder.whl').touch()
            self.assertEqual(maintenance.verify(PINS, wheelhouse, require_native=True), 7)
            environment = run.call_args.kwargs['env']
            self.assertEqual(environment['PIP_NO_INDEX'], '1')
            self.assertEqual(environment['PIP_CONFIG_FILE'], os.devnull)
            self.assertEqual(environment['RI_REQUIRE_STANDALONE'], '1')
            self.assertEqual(environment['RI_WHEELHOUSE'], str(wheelhouse.resolve()))
            self.assertEqual(run.call_args.kwargs['cwd'], SCRIPT.parent.parent)
            self.assertIn('unittest', run.call_args.args[0])
        self.assertEqual(run.call_count, 1)

    def test_verify_stops_before_tests_when_pins_or_native_tools_are_wrong(self):
        wrong_pin = prepared_report()
        wrong_pin['packages'][0]['matches'] = False
        for report, native, message in ((wrong_pin, False, 'pins differ'),
                                        (prepared_report(native='unavailable'), True, 'native tools')):
            with self.subTest(message=message), \
                    mock.patch.object(maintenance, 'status', return_value=report), \
                    mock.patch.object(maintenance.subprocess, 'run') as run, \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, message):
                    maintenance.verify(PINS, Path('/unused'), require_native=native)
                run.assert_not_called()

    def test_status_command_works_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as raw:
            result = subprocess.run([sys.executable, str(SCRIPT), 'status'], cwd=raw,
                                    capture_output=True, text=True, timeout=40, check=True)
        report = json.loads(result.stdout)
        self.assertIn('tree-sitter', {item['name'] for item in report['packages']})
        self.assertEqual(set(report['native_tools']), {'rustc', 'cargo', 'rust-analyzer'})

    def test_bundle_rejects_dirty_checkout_before_verification_or_output(self):
        with tempfile.TemporaryDirectory() as raw, \
                mock.patch.object(maintenance.sys, 'prefix', '/fixture-venv'), \
                mock.patch.object(maintenance.sys, 'base_prefix', '/fixture-base'), \
                mock.patch.object(maintenance.subprocess, 'run', side_effect=[
                    subprocess.CompletedProcess([], 0, 'abc123\n', ''),
                    subprocess.CompletedProcess([], 0, ' M source.py\n', '')]), \
                mock.patch.object(maintenance, 'verify') as verify:
            output = Path(raw) / 'bundle'
            with self.assertRaisesRegex(ValueError, 'clean checkout'):
                maintenance.bundle(PINS, Path(raw), output, require_native=True)
            verify.assert_not_called()
            self.assertFalse(output.exists())

    def test_archive_source_uses_head_bytes_and_omits_ignored_files(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / 'repo'
            repo.mkdir()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            (repo / '.gitignore').write_text('ignored/\n', encoding='utf-8')
            (repo / 'source.txt').write_text('committed', encoding='utf-8')
            subprocess.run(['git', 'add', '.gitignore', 'source.txt'], cwd=repo, check=True)
            subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                            'commit', '-qm', 'fixture'], cwd=repo, check=True)
            revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, check=True,
                                      capture_output=True, text=True).stdout.strip()
            (repo / 'source.txt').write_text('live edit', encoding='utf-8')
            (repo / 'ignored').mkdir()
            (repo / 'ignored' / 'payload').write_text('ignored', encoding='utf-8')
            source = Path(raw) / 'source'
            source.mkdir()
            with mock.patch.object(maintenance, 'ROOT', repo):
                maintenance.archive_source(revision, source)
            self.assertEqual((source / 'source.txt').read_text(encoding='utf-8'), 'committed')
            self.assertFalse((source / 'ignored').exists())


if __name__ == '__main__':
    unittest.main()
