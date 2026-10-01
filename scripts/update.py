"""One start-of-work command for pinned packages, tools, and editor setup."""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import uuid
from urllib.error import URLError

if sys.version_info < (3, 12):
    for executable_name in ('python3.14', 'python3.13', 'python3.12'):
        executable = shutil.which(executable_name)
        if executable:
            version = subprocess.run([executable, '-c',
                                      'import sys; print(*sys.version_info[:2], sep=".")'],
                                     capture_output=True, text=True, timeout=10)
            if version.returncode == 0 and version.stdout.strip() in ('3.12', '3.13', '3.14'):
                os.execv(executable, [executable, __file__, *sys.argv[1:]])
    raise SystemExit('Install Python 3.12, 3.13, or 3.14 before running updates')

from update_modules import actions, editor, native, python_packages, review_obligations


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / '.venv'
CACHE = ROOT / '.ri-cache'
SELECTION = CACHE / 'selected-python.json'
JOURNAL = CACHE / 'update-recovery.json'
RESULT = CACHE / 'update-result.json'
REJECTIONS = CACHE / 'rejected-updates.json'
GRAMMAR_NAMES = {'tree-sitter', 'tree-sitter-python', 'tree-sitter-rust',
                 'tree-sitter-javascript', 'tree-sitter-typescript', 'tree-sitter-java',
                 'tree-sitter-go', 'tree-sitter-c-sharp', 'tree-sitter-c', 'tree-sitter-cpp',
                 'tree-sitter-markdown'}


def run(*args: str, env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(args, cwd=ROOT, env=env, check=True)
    except subprocess.CalledProcessError as error:
        if error.returncode == 75 and len(args) > 1 and Path(args[1]) == ROOT / 'scripts' / 'maintain.py':
            raise subprocess.TimeoutExpired(args, None) from error
        raise


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def source_commit() -> str:
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                            capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if not re.fullmatch(r'[0-9a-f]{40,64}', commit):
        raise ValueError('RI source commit is unavailable')
    return commit


def write_result(run_id: str, commit: str, disposition: str, **details: object) -> dict:
    result = {'schema_version': 1, 'run_id': run_id, 'source_commit': commit,
              'disposition': disposition, **details}
    atomic_write(RESULT, (json.dumps(result, indent=2) + '\n').encode())
    return result


def write_failed_result(run_id: str, commit: str | None, reason: str) -> None:
    if commit is None:
        return
    try:
        write_result(run_id, commit, 'failed', failure_reason=reason[:500])
    except OSError as error:
        print(f'Could not write failed update result: {error}', file=sys.stderr)


def selected_bytes() -> bytes | None:
    return SELECTION.read_bytes() if SELECTION.exists() else None


def selected_path() -> Path:
    if SELECTION.exists():
        path = Path(json.loads(SELECTION.read_text(encoding='utf-8'))['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Selected project Python path is invalid')
        selected = ROOT / path
        if not selected.is_file():
            raise ValueError('Selected project Python is unavailable')
        return selected
    return VENV / 'bin' / 'python'


def select_python(python: Path) -> None:
    atomic_write(SELECTION, (json.dumps({'path': str(python.relative_to(ROOT))}) + '\n').encode())


def workflow_paths() -> list[Path]:
    directory = ROOT / '.github' / 'workflows'
    return sorted({path for pattern in ('*.yml', '*.yaml') for path in directory.glob(pattern)})


def begin_recovery() -> None:
    if JOURNAL.exists():
        raise ValueError('An update recovery record already exists')
    paths = [ROOT / 'pyproject.toml', SELECTION, pending_path(), *workflow_paths()]
    snapshot = {str(path.relative_to(ROOT)): (base64.b64encode(path.read_bytes()).decode()
                                              if path.exists() else None)
                for path in paths}
    atomic_write(JOURNAL, (json.dumps({'files': snapshot}, indent=2) + '\n').encode())


def recover() -> bool:
    """Restore tracked pins/Actions and selection; candidates never touch the old venv."""
    if not JOURNAL.exists():
        return False
    record = json.loads(JOURNAL.read_text(encoding='utf-8'))
    for relative, encoded in record['files'].items():
        path = ROOT / relative
        if encoded is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, base64.b64decode(encoded, validate=True))
    JOURNAL.unlink()
    return True


@contextmanager
def update_lock():
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / 'update.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Another updater run is active') from error
        yield


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
    current = selected_path()
    if migrate and current.exists():
        result = subprocess.run([str(current), '-c',
                                 'import sys; print(*sys.version_info[:2], sep=".")'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip() == f'{selected[0]}.{selected[1]}':
            return current, False
        candidate = CACHE / 'venvs' / f'python{selected[0]}.{selected[1]}'
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


def new_candidate(python: Path) -> Path:
    directory = CACHE / 'venvs' / ('update-' + uuid.uuid4().hex)
    directory.parent.mkdir(parents=True, exist_ok=True)
    run(str(python), '-m', 'venv', str(directory))
    return directory / 'bin' / 'python'


def verified_candidate(python: Path, *, offline: bool = False) -> None:
    run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'prepare',
        *(['--offline'] if offline else []))
    run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify')


def rejection_context(manifest: bytes, python: Path) -> str:
    version = subprocess.run([str(python), '-c',
                              'import platform; print(platform.python_version())'],
                             capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                              capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    diff = subprocess.run(['git', 'diff', '--binary', 'HEAD', '--', 'src', 'scripts', 'tests'],
                          cwd=ROOT, capture_output=True, check=True, timeout=20).stdout
    identity = (revision + '\n' + version + '\n' + platform.platform()).encode() + manifest + diff
    return hashlib.sha256(identity).hexdigest()


def update_packages(python: Path, manifest: Path, proposals: list[tuple[str, str, str]],
                    rejected_versions: dict, *, commit: str | None = None) -> tuple[Path, list[str], list[str]]:
    review = []
    changed = []
    for name, old, new in proposals:
        context = rejection_context(manifest.read_bytes(), python)
        if rejected_versions.get(name) == {'version': new, 'context': context}:
            review.append(f'{name} {new}: previously rejected in this qualification context')
            continue
        print(f'Trying {name}: {old} -> {new}', flush=True)
        begin_recovery()
        stage = 'prepare'
        try:
            python_packages.set_pin(manifest, name, old, new)
            candidate = new_candidate(python)
            run(str(candidate), str(ROOT / 'scripts' / 'maintain.py'), 'prepare')
            stage = 'verify'
            run(str(candidate), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
            stage = 'promote'
            select_python(candidate)
            if name in GRAMMAR_NAMES:
                retain_reviews(commit or source_commit(), [name], [])
            JOURNAL.unlink()
            python = candidate
            changed.append(name)
        except BaseException as error:
            recover()
            if isinstance(error, KeyboardInterrupt):
                raise
            if isinstance(error, (OSError, subprocess.SubprocessError)) and stage == 'prepare':
                review.append(f'{name} {new}: preparation unavailable; retry next run: {error}')
                continue
            if stage == 'promote':
                raise
            if stage == 'prepare':
                raise
            if isinstance(error, (OSError, subprocess.TimeoutExpired)):
                review.append(f'{name} {new}: verification unavailable; retry next run: {error}')
                continue
            rejected_versions[name] = {'version': new, 'context': context}
            atomic_write(REJECTIONS, (json.dumps(rejected_versions, indent=2) + '\n').encode())
            review.append(f'{name} {new}: candidate verification failed: {error}')
    return python, review, changed


def pending_path() -> Path:
    return CACHE / 'pending-reviews.json'


def save_pending(pending: dict) -> None:
    atomic_write(pending_path(), (json.dumps({'schema_version': 1, 'pending': pending},
                                           indent=2) + '\n').encode())


def retain_reviews(commit: str, changed: list[str], action_changes: list[str]) -> dict:
    pending = review_obligations.refresh(ROOT, commit, review_obligations.load(pending_path()))
    for name in changed:
        if name in GRAMMAR_NAMES:
            review_obligations.add(ROOT, commit, pending, 'grammar', name,
                                   'upstream grammar and node review')
    if action_changes:
        review_obligations.add(ROOT, commit, pending, 'actions', 'workflows',
                               'hosted Verify for changed GitHub Actions')
    save_pending(pending)
    return pending


def readiness_result(python: Path, changed: list[str], action_changes: list[str],
                     editor_ready: bool, review: list[str]) -> dict:
    outstanding = []
    if any(name in GRAMMAR_NAMES for name in changed):
        outstanding.append('upstream grammar and node review')
    if action_changes:
        outstanding.append('hosted Verify for changed GitHub Actions')
    return {'selected_python': str(python), 'local_verify_passed': True,
            'package_changes': changed, 'action_changes': action_changes,
            'outstanding_qualification': outstanding,
            'editor_configured': editor_ready, 'rejected_or_retryable': review}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='also update rustup stable tools')
    parser.add_argument('--offline', action='store_true', help='reuse existing pinned wheels')
    parser.add_argument('--migrate-python', action='store_true',
                        help='qualify a newer Python in a separate environment before selecting it')
    parser.add_argument('--skip-actions', action='store_true', help='leave CI action pins unchanged')
    parser.add_argument('--resolve-review', action='append', default=[], metavar='ID=SHA256',
                        help='acknowledge completed external review for a printed current identity')
    parser.add_argument('--run-id', help='caller-selected unique run ID for the structured result')
    args = parser.parse_args()
    if args.run_id is not None and (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', args.run_id)
                                    or args.run_id in {'.', '..'}):
        parser.error('--run-id must be 1-128 safe ASCII characters')
    if args.offline and args.native:
        parser.error('--offline cannot update native tools; use verify --require-native')
    run_id = args.run_id or uuid.uuid4().hex
    commit = None
    try:
        with update_lock():
            # Upgrade old success-only state before clearing the per-invocation result.
            try:
                commit = source_commit()
                previous = (json.loads(RESULT.read_text())
                            if RESULT.exists() and not pending_path().exists() else {})
                if not isinstance(previous, dict):
                    raise ValueError('Invalid previous updater result')
            finally:
                RESULT.unlink(missing_ok=True)
            recovered = recover()
            if recovered:
                print('Restored an interrupted update; verifying the selected environment', flush=True)
            pending = retain_reviews(commit, previous.get('package_changes', [])
                                     if not pending_path().exists() else [],
                                     previous.get('action_changes', [])
                                     if not pending_path().exists() else [])
            review_obligations.resolve(pending, args.resolve_review)
            save_pending(pending)
            manifest = ROOT / 'pyproject.toml'
            python, migrating = ensure_python(migrate=args.migrate_python)
            try:
                if migrating:
                    raise ValueError('qualify migration candidate')
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify')
            except (OSError, ValueError, subprocess.SubprocessError):
                # An unprepared or interrupted selected environment is never called ready.
                candidate = python if migrating else new_candidate(python)
                verified_candidate(candidate, offline=args.offline)
                begin_recovery()
                try:
                    select_python(candidate)
                    JOURNAL.unlink()
                except BaseException:
                    recover()
                    raise
                python = candidate
            rejected_versions = json.loads(REJECTIONS.read_text(encoding='utf-8')) if REJECTIONS.exists() else {}
            proposals = [] if args.offline else python_packages.proposals(manifest)
            python, review, changed = update_packages(python, manifest, proposals,
                                                      rejected_versions, commit=commit)
            if args.native:
                native.update()
                run(str(python), str(ROOT / 'scripts' / 'maintain.py'), 'verify', '--require-native',
                    env={**os.environ, 'RUSTUP_TOOLCHAIN': 'stable'})
            action_changes = []
            if not args.offline and not args.skip_actions:
                begin_recovery()
                try:
                    action_changes = actions.update(ROOT / '.github' / 'workflows')
                    retain_reviews(commit, [], action_changes)
                    JOURNAL.unlink()
                except BaseException:
                    recover()
                    raise
            editor_ready = True
            try:
                editor.configure(ROOT, python)
            except (OSError, ValueError) as error:
                editor_ready = False
                print(f'Editor setting unchanged: {error}', file=sys.stderr)
            readiness = readiness_result(python, changed, action_changes, editor_ready, review)
            pending = retain_reviews(commit, changed, action_changes)
            readiness['pending_reviews'] = pending
            readiness['outstanding_qualification'] = sorted({item['reason'] for item in pending.values()})
            disposition = ('review_required' if review or readiness['outstanding_qualification']
                           else 'completed')
            result = write_result(run_id, commit, disposition, **readiness)
            if review:
                print('Updates requiring review:\n' + '\n'.join(review), file=sys.stderr)
            print(json.dumps(result, indent=2))
            return 0
    except KeyboardInterrupt:
        write_failed_result(run_id, commit, 'interrupted')
        print('Update interrupted; selected environment remains at last qualified state',
              file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, URLError) as error:
        write_failed_result(run_id, commit, str(error))
        print(f'Update failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
