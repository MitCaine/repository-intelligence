"""Small shared maintenance commands; only prepare downloads or installs packages."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WHEELS = ROOT / '.ri-cache' / 'wheels'


def load_pins(project_path: Path = ROOT / 'pyproject.toml') -> dict[str, dict[str, str]]:
    """Read the repository's deliberately small, exact-pin requirement format."""
    project = tomllib.loads(project_path.read_text(encoding='utf-8'))
    pins = {}
    for group, requirements in (
            ('build', project['build-system']['requires']),
            ('runtime', project['project']['dependencies'])):
        selected = {}
        for requirement in requirements:
            match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)',
                                 requirement)
            if match is None:
                raise ValueError(f'{group}: use one exact NAME==VERSION pin: {requirement!r}')
            name = re.sub(r'[-_.]+', '-', match[1]).lower()
            if name in selected:
                raise ValueError(f'{group}: duplicate dependency {name}')
            selected[name] = match[2]
        pins[group] = selected
    conflicts = [name for name in pins['build'].keys() & pins['runtime'].keys()
                 if pins['build'][name] != pins['runtime'][name]]
    if conflicts:
        raise ValueError(f'Build/runtime pins disagree: {", ".join(sorted(conflicts))}')
    return pins


def requirements(pins: dict[str, dict[str, str]]) -> list[str]:
    return [f'{name}=={version}' for name, version in
            {**pins['build'], **pins['runtime']}.items()]


def native_status(tool: str) -> dict:
    path = shutil.which(tool)
    if path is None:
        return {'status': 'missing', 'path': None, 'version': None}
    try:
        result = subprocess.run([path, '--version'], cwd=ROOT, capture_output=True,
                                text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'status': 'unavailable', 'path': path, 'version': None,
                'error': type(error).__name__}
    return {'status': 'available' if result.returncode == 0 else 'unavailable',
            'path': path, 'version': result.stdout.strip() if result.returncode == 0 else None,
            **({'error': result.stderr.strip() or f'exit {result.returncode}'}
               if result.returncode else {})}


def status(pins: dict[str, dict[str, str]]) -> dict:
    packages = []
    for group, selected in pins.items():
        for name, expected in selected.items():
            try:
                actual = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                actual = None
            packages.append({'group': group, 'name': name, 'pinned': expected,
                             'installed': actual, 'matches': actual == expected})
    return {'python': platform.python_version(), 'executable': sys.executable,
            'platform': f'{platform.system()} {platform.release()} {platform.machine()}',
            'packages': packages,
            'native_tools': {name: native_status(name)
                             for name in ('rustc', 'cargo', 'rust-analyzer')}}


def offline_environment() -> dict[str, str]:
    """Offline pip must not inherit remote links, requirements, or config files."""
    return {key: value for key, value in os.environ.items() if not key.startswith('PIP_')} | {
        'PIP_CONFIG_FILE': os.devnull, 'PIP_NO_INDEX': '1',
        'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_CACHE_DIR': '1'}


def prepare(pins: dict[str, dict[str, str]], wheelhouse: Path, *, offline: bool) -> int:
    """Install declared pins into the invoking virtual environment; reuse old wheels."""
    if sys.prefix == sys.base_prefix:
        raise ValueError('prepare installs packages: run it with a virtual-environment Python')
    wheelhouse = wheelhouse.resolve()
    wheelhouse.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    if not offline:
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--only-binary=:all:',
                        '--dest', str(wheelhouse), *requirements(pins)],
                       cwd=ROOT, env=environment, check=True, timeout=600)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-index',
                    '--find-links', str(wheelhouse), *requirements(pins)],
                   cwd=ROOT, env=offline_environment(), check=True, timeout=600)
    return 0


def verify(pins: dict[str, dict[str, str]], wheelhouse: Path, *, require_native: bool) -> int:
    """Use the prepared environment/wheels without downloading or installing in it."""
    report = status(pins)
    print(json.dumps(report, indent=2), flush=True)
    mismatches = [item['name'] for item in report['packages'] if not item['matches']]
    if mismatches:
        raise ValueError('Installed pins differ; run prepare first: ' + ', '.join(mismatches))
    if require_native:
        missing = [name for name, item in report['native_tools'].items()
                   if item['status'] != 'available']
        if missing:
            raise ValueError('Required native tools are unavailable: ' + ', '.join(missing))
    wheelhouse = wheelhouse.resolve()
    if not wheelhouse.is_dir() or not any(wheelhouse.glob('*.whl')):
        raise ValueError('A prepared wheelhouse is required; run prepare first')
    environment = {**offline_environment(), 'PYTHONPATH': str(ROOT / 'src'),
                   'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1',
                   'PIP_DISABLE_PIP_VERSION_CHECK': '1',
                   'RI_REQUIRE_STANDALONE': '1', 'RI_WHEELHOUSE': str(wheelhouse)}
    return subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                          cwd=ROOT, env=environment, timeout=900).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status', help='read installed pins and optional native tool versions')
    setup = commands.add_parser('prepare', help='download pinned wheels and install into this venv')
    setup.add_argument('--wheelhouse', type=Path, default=DEFAULT_WHEELS)
    setup.add_argument('--offline', action='store_true', help='install only from existing wheels')
    check = commands.add_parser('verify', help='run full source and offline installed-consumer tests')
    check.add_argument('--wheelhouse', type=Path, default=DEFAULT_WHEELS)
    check.add_argument('--require-native', action='store_true', help='require functional Rust tools')
    args = parser.parse_args(argv)
    try:
        pins = load_pins()
        if args.command == 'status':
            print(json.dumps(status(pins), indent=2))
            return 0
        if args.command == 'prepare':
            return prepare(pins, args.wheelhouse, offline=args.offline)
        return verify(pins, args.wheelhouse, require_native=args.require_native)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Maintenance failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
