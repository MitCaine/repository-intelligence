"""One start-of-work command for pinned packages, tools, and editor setup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.error import URLError

from update_modules import actions, editor, native, python_packages


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / '.venv'
PYTHON = VENV / 'bin' / 'python'


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def ensure_python() -> None:
    candidates = []
    for name in ('python3.12', 'python3.13', 'python3.14'):
        path = shutil.which(name)
        if path:
            result = subprocess.run([path, '-c',
                                     'import sys; print(*sys.version_info[:2], sep=".")'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and re.fullmatch(r'3\.\d+', result.stdout.strip()):
                major, minor = map(int, result.stdout.strip().split('.'))
                if (major, minor) >= (3, 12):
                    candidates.append(((major, minor), path))
    executable = max(candidates)[1] if candidates else None
    if executable is None:
        raise RuntimeError('Install Python 3.12, 3.13, or 3.14 before running updates')
    selected = max(candidates)[0]
    if PYTHON.exists():
        result = subprocess.run([str(PYTHON), '-c',
                                 'import sys; print(*sys.version_info[:2], sep=".")'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip() == f'{selected[0]}.{selected[1]}':
            return
        print(f'Rebuilding .venv with Python {selected[0]}.{selected[1]}', flush=True)
        run(executable, '-m', 'venv', '--clear', str(VENV))
    else:
        run(executable, '-m', 'venv', str(VENV))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='also update rustup stable tools')
    parser.add_argument('--offline', action='store_true', help='reuse existing pinned wheels')
    parser.add_argument('--skip-actions', action='store_true', help='leave CI action pins unchanged')
    args = parser.parse_args()
    manifest = ROOT / 'pyproject.toml'
    rejected_path = ROOT / '.ri-cache' / 'rejected-updates.json'
    rejected_versions = json.loads(rejected_path.read_text(encoding='utf-8')) if rejected_path.exists() else {}
    before = manifest.read_bytes()
    workflow_dir = ROOT / '.github' / 'workflows'
    workflows_before = {path: path.read_bytes() for path in workflow_dir.glob('*.yml')}
    try:
        ensure_python()
        changes = [] if args.offline else [proposal for proposal in python_packages.proposals(manifest)
                                          if rejected_versions.get(proposal[0]) != proposal[2]]
        rejected = []
        # Seed the wheelhouse with known-good versions before trying candidates.
        run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'prepare',
            *(['--offline'] if args.offline else []))
        run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
        for name, old, new in changes:
            print(f'Trying {name}: {old} -> {new}', flush=True)
            python_packages.set_pin(manifest, name, old, new)
            try:
                run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'prepare')
                run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
            except (OSError, subprocess.CalledProcessError) as error:
                python_packages.set_pin(manifest, name, new, old)
                run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'prepare', '--offline')
                run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
                rejected_versions[name] = new
                rejected_path.parent.mkdir(exist_ok=True)
                rejected_path.write_text(json.dumps(rejected_versions, indent=2) + '\n',
                                         encoding='utf-8')
                rejected.append(f'{name} {new}: {error}')
                print(f'Rejected {name} {new}; previous pin restored', flush=True)
        if args.native:
            native.update()
            run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'verify', '--require-native')
        if not args.offline and not args.skip_actions:
            print('\n'.join(actions.update(workflow_dir)) or 'GitHub Actions are current', flush=True)
        editor.configure(ROOT)
        if rejected:
            print('Updates requiring review:\n' + '\n'.join(rejected), file=sys.stderr)
        print('Ready: use .venv/bin/python in Codex; VS Code points to the same environment')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, URLError) as error:
        if manifest.read_bytes() != before:
            manifest.write_bytes(before)
            print('Restored pyproject.toml after an unsuccessful update', file=sys.stderr)
            try:
                run(str(PYTHON), str(ROOT / 'scripts' / 'maintain.py'), 'prepare', '--offline')
            except (OSError, subprocess.CalledProcessError) as restore_error:
                print(f'Could not restore installed pins: {restore_error}', file=sys.stderr)
        for path, content in workflows_before.items():
            if path.read_bytes() != content:
                path.write_bytes(content)
        print(f'Update failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
