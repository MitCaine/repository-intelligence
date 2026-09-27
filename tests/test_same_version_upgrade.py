"""An existing consumer must replace RI code when the wheel version stays fixed."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run(*args: object, environment: dict[str, str]) -> str:
    result = subprocess.run([str(arg) for arg in args], env=environment,
                            check=True, capture_output=True, text=True, timeout=180)
    return result.stdout


class SameVersionUpgradeTests(unittest.TestCase):
    def test_force_reinstall_replaces_existing_ri_wheel(self):
        wheelhouse = os.environ.get('RI_WHEELHOUSE')
        if not wheelhouse or not Path(wheelhouse).is_dir():
            if os.environ.get('RI_REQUIRE_STANDALONE') == '1':
                self.fail('RI_WHEELHOUSE is required for the upgrade check')
            self.skipTest('RI_WHEELHOUSE is unavailable')
        environment = {key: value for key, value in os.environ.items()
                       if key != 'PYTHONPATH' and not key.startswith('PIP_')}
        environment.update(PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX='1',
                           PIP_NO_CACHE_DIR='1', PIP_DISABLE_PIP_VERSION_CHECK='1',
                           PYTHONDONTWRITEBYTECODE='1')
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(prefix='ri-same-version-') as raw:
            temp = Path(raw)
            build = temp / 'build'
            consumer = temp / 'consumer'
            run(sys.executable, '-m', 'venv', build, environment=environment)
            run(sys.executable, '-m', 'venv', consumer, environment=environment)
            relative_python = Path('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            build_python = build / relative_python
            consumer_python = consumer / relative_python
            run(build_python, '-m', 'pip', 'install', '--no-index', '--find-links', wheelhouse,
                *project['build-system']['requires'], environment=environment)
            wheels = []
            for label in ('old', 'new'):
                source = temp / label
                (source / 'src').mkdir(parents=True)
                shutil.copy2(ROOT / 'pyproject.toml', source / 'pyproject.toml')
                package = source / 'src' / 'repository_intelligence'
                shutil.copytree(ROOT / 'src' / 'repository_intelligence', package)
                if label == 'old':
                    with (package / '__init__.py').open('a', encoding='utf-8') as file:
                        file.write('\n_upgrade_probe = "old"\n')
                output = temp / f'{label}-wheels'
                run(build_python, '-m', 'pip', 'wheel', '--no-index', '--no-build-isolation',
                    '--no-deps', '--wheel-dir', output, source, environment=environment)
                built = list(output.glob('repository_intelligence-*.whl'))
                self.assertEqual(len(built), 1)
                wheels.append(built[0])
            run(consumer_python, '-m', 'pip', 'install', '--no-index', '--find-links',
                wheelhouse, wheels[0], environment=environment)
            self.assertEqual(run(consumer_python, '-c',
                                 'import repository_intelligence as ri; print(ri._upgrade_probe)',
                                 environment=environment).strip(), 'old')
            run(consumer_python, '-m', 'pip', 'install', '--force-reinstall', '--no-index',
                '--find-links', wheelhouse, wheels[1], environment=environment)
            self.assertEqual(run(consumer_python, '-c',
                                 'import repository_intelligence as ri; '
                                 'print(hasattr(ri, "_upgrade_probe"))',
                                 environment=environment).strip(), 'False')
            run(consumer_python, '-m', 'pip', 'check', environment=environment)
