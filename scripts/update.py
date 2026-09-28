"""One start-of-work command for pinned packages, tools, and editor setup."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.error import URLError

from update_modules import actions, editor, native, python_packages


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / '.venv'
SELECTION = ROOT / '.ri-cache' / 'selected-python.json'


def run(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def ensure_python(*, migrate: bool) -> tuple[Path, bool]:
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
    if not candidates:
        raise RuntimeError('Install Python 3.12, 3.13, or 3.14 before running updates')
    selected, executable = max(candidates)
    current = VENV / 'bin' / 'python'
    if SELECTION.exists():
        path = Path(json.loads(SELECTION.read_text(encoding='utf-8'))['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Selected project Python path is invalid')
        current = ROOT / path
        if not current.is_file():
            raise ValueError('Selected project Python is unavailable')
    if migrate and current.exists():
        result = subprocess.run([str(current), '-c',
                                 'import sys; print(*sys.version_info[:2], sep=".")'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip() == f'{selected[0]}.{selected[1]}':
            return current, False
        candidate = ROOT / '.ri-cache' / 'venvs' / f'python{selected[0]}.{selected[1]}'
        python = candidate / 'bin' / 'python'
        if candidate.exists() and not python.exists():
            raise ValueError(f'Incomplete candidate environment: {candidate}')
        if python.exists():
            result = subprocess.run([str(python), '-c',
                                     'import sys; print(*sys.version_info[:2], sep=".")'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode != 0 or result.stdout.strip() != f'{selected[0]}.{selected[1]}':
                raise ValueError(f'Candidate environment uses the wrong Python: {candidate}')
        if not candidate.exists():
            candidate.parent.mkdir(parents=True, exist_ok=True)
            run(executable, '-m', 'venv', str(candidate))
        return python, True
    if current.exists():
        return current, False
    if SELECTION.exists():
        raise ValueError('Selected project Python is unavailable')
    run(executable, '-m', 'venv', str(VENV))
    return current, False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='also update rustup stable tools')
    parser.add_argument('--offline', action='store_true', help='reuse existing pinned wheels')
    parser.add_argument('--migrate-python', action='store_true',
                        help='qualify a newer Python in a separate environment before selecting it')
    parser.add_argument('--skip-actions', action='store_true', help='leave CI action pins unchanged')
    args = parser.parse_args()
    if args.offline and args.native:
        parser.error('--offline cannot update native tools; use verify --require-native')
    manifest = ROOT / 'pyproject.toml'
    rejected_path = ROOT / '.ri-cache' / 'rejected-updates.json'
    rejected_versions = json.loads(rejected_path.read_text(encoding='utf-8')) if rejected_path.exists() else {}
    before = manifest.read_bytes()
    workflow_dir = ROOT / '.github' / 'workflows'
    workflows_before = {path: path.read_bytes() for pattern in ('*.yml', '*.yaml')
                        for path in workflow_dir.glob(pattern)}
    python = None
    try:
        python, migrating = ensure_python(migrate=args.migrate_python)
        changes = [] if args.offline else [proposal for proposal in python_packages.proposals(manifest)
                                          if rejected_versions.get(proposal[0]) != proposal[2]]
        rejected = []
        # Seed the wheelhouse with known-good versions before trying candidates.
        run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'prepare',
            *(['--offline'] if args.offline else []))
        run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
        for name, old, new in changes:
            print(f'Trying {name}: {old} -> {new}', flush=True)
            python_packages.set_pin(manifest, name, old, new)
            try:
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'prepare')
            except (OSError, subprocess.SubprocessError) as error:
                python_packages.set_pin(manifest, name, new, old)
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'prepare', '--offline')
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
                rejected.append(f'{name} {new}: preparation unavailable, retry next run: {error}')
                continue
            try:
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
            except (OSError, subprocess.SubprocessError) as error:
                python_packages.set_pin(manifest, name, new, old)
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'prepare', '--offline')
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
                rejected_versions[name] = new
                rejected_path.parent.mkdir(exist_ok=True)
                rejected_path.write_text(json.dumps(rejected_versions, indent=2) + '\n',
                                         encoding='utf-8')
                rejected.append(f'{name} {new}: {error}')
                print(f'Rejected {name} {new}; previous pin restored', flush=True)
        if args.native:
            native.update()
            run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify', '--require-native',
                env={**os.environ, 'RUSTUP_TOOLCHAIN': 'stable'})
        if not args.offline and not args.skip_actions:
            print('\n'.join(actions.update(workflow_dir)) or 'GitHub Actions are current', flush=True)
        if migrating:
            SELECTION.parent.mkdir(exist_ok=True)
            SELECTION.write_text(json.dumps({'path': str(python.relative_to(ROOT))}) + '\n',
                                 encoding='utf-8')
        editor_ready = True
        try:
            editor.configure(ROOT, python)
        except (OSError, ValueError) as error:
            editor_ready = False
            print(f'Editor setting unchanged: {error}', file=sys.stderr)
        if rejected:
            print('Updates requiring review:\n' + '\n'.join(rejected), file=sys.stderr)
        print(f'Ready: use {python} in Codex'
              + (' and VS Code' if editor_ready else '; select it manually in VS Code'))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, URLError) as error:
        if manifest.read_bytes() != before:
            manifest.write_bytes(before)
            print('Restored pyproject.toml after an unsuccessful update', file=sys.stderr)
            try:
                if python is not None:
                    run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'prepare', '--offline')
            except (OSError, subprocess.SubprocessError) as restore_error:
                print(f'Could not restore installed pins: {restore_error}', file=sys.stderr)
        for path, content in workflows_before.items():
            if path.read_bytes() != content:
                path.write_bytes(content)
        print(f'Update failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
