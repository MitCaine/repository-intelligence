"""Bounded, explicit adoption of regular blobs from a local immutable Git commit."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile

MAX_REQUEST_BYTES = 1_000_000
MAX_RESOURCE_BYTES = 8_000_000
MAX_TOTAL_BYTES = 32_000_000
MAX_RESOURCES = 128
SCHEMA_VERSION = 1


class AdoptionError(ValueError):
    pass


def _git(root: Path, *args: str) -> bytes:
    environment = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        environment.pop(key, None)
    environment['GIT_NO_REPLACE_OBJECTS'] = '1'
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30, env=environment)
    if result.returncode:
        raise AdoptionError('Git operation failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative(value: object) -> str:
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise AdoptionError('Invalid resource path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('', '.', '..', '.git') for part in value.split('/')):
        raise AdoptionError('Resource path must be relative and cannot traverse or address .git')
    return value


def _root(value: object) -> Path:
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise AdoptionError('Repository must be an explicit absolute path')
    supplied = Path(value)
    if any(parent.is_symlink() for parent in (supplied, *supplied.parents)):
        raise AdoptionError('Repository path contains a symlink')
    root = supplied.resolve(strict=True)
    if _git(root, 'rev-parse', '--show-toplevel').decode().strip() != str(root):
        raise AdoptionError('Repository must name the worktree root')
    return root


def _target(root: Path, relative: str) -> Path:
    target = root / relative
    cursor = root
    for part in relative.split('/'):
        cursor = cursor / part
        if cursor.is_symlink():
            raise AdoptionError('Destination contains a symlink: ' + relative)
        if cursor.exists() and cursor != target and not cursor.is_dir():
            raise AdoptionError('Destination ancestor is not a directory: ' + relative)
    if target.exists() and not target.is_file():
        raise AdoptionError('Destination is not a regular file: ' + relative)
    return target


def _read(path: Path) -> bytes | None:
    if not path.exists():
        return None
    if path.stat().st_size > MAX_RESOURCE_BYTES:
        raise AdoptionError('Destination exceeds resource limit')
    return path.read_bytes()


def _atomic(path: Path, data: bytes, mode: int) -> None:
    fd, temporary = tempfile.mkstemp(prefix='.ri-adoption-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def adopt(request: dict, mode: str) -> dict:
    if mode not in ('preview', 'verify', 'apply'):
        raise AdoptionError('Invalid mode')
    source = _root(request.get('source_repository'))
    destination = _root(request.get('destination_repository'))
    revision = request.get('revision')
    if not isinstance(revision, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', revision):
        raise AdoptionError('Revision must be a full lowercase commit object identity')
    resolved = _git(source, 'rev-parse', '--verify', revision + '^{commit}').decode().strip()
    if resolved != revision:
        raise AdoptionError('Revision does not identify the exact commit')
    resources = request.get('resources')
    if not isinstance(resources, list) or not 1 <= len(resources) <= MAX_RESOURCES:
        raise AdoptionError('Resources must be a bounded nonempty list')
    plan, reports, seen = [], [], set()
    total = 0
    for resource in resources:
        if not isinstance(resource, dict):
            raise AdoptionError('Invalid resource declaration')
        src = _relative(resource.get('source'))
        dst = _relative(resource.get('destination'))
        if dst in seen:
            raise AdoptionError('Duplicate destination: ' + dst)
        if any(dst.startswith(other + '/') or other.startswith(dst + '/') for other in seen):
            raise AdoptionError('Destinations overlap as file and ancestor: ' + dst)
        seen.add(dst)
        entry = _git(source, 'ls-tree', '-z', revision, '--', src).split(b'\x00')
        if len(entry) != 2 or not entry[0]:
            raise AdoptionError('Source must name exactly one regular commit blob: ' + src)
        metadata, name = entry[0].split(b'\t', 1)
        permissions, kind, blob = metadata.split()
        if name.decode() != src or kind != b'blob' or permissions not in (b'100644', b'100755'):
            raise AdoptionError('Source is not a regular commit blob: ' + src)
        size = int(_git(source, 'cat-file', '-s', blob.decode()))
        if size > MAX_RESOURCE_BYTES:
            raise AdoptionError('Source exceeds resource limit')
        raw = _git(source, 'cat-file', 'blob', blob.decode())
        output = raw
        replacements = resource.get('replacements', [])
        if not isinstance(replacements, list) or len(replacements) > 128:
            raise AdoptionError('Invalid replacements')
        for replacement in replacements:
            if not isinstance(replacement, dict):
                raise AdoptionError('Invalid replacement')
            old, new, count = (replacement.get(key) for key in ('old', 'new', 'expected_count'))
            if not isinstance(old, str) or not old or not isinstance(new, str) or type(count) is not int or count < 0:
                raise AdoptionError('Replacement needs nonempty old text, new text, and nonnegative exact count')
            before, after = old.encode('utf-8'), new.encode('utf-8')
            if output.count(before) != count:
                raise AdoptionError('Replacement count mismatch: ' + src)
            if len(output) + count * (len(after) - len(before)) > MAX_RESOURCE_BYTES:
                raise AdoptionError('Transformed resource exceeds limit')
            output = output.replace(before, after)
        total += len(raw) + len(output)
        if total > MAX_TOTAL_BYTES:
            raise AdoptionError('Inventory exceeds total byte limit')
        target = _target(destination, dst)
        current = _read(target)
        expected = resource.get('expected_destination_sha256')
        if expected is not None and (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
            raise AdoptionError('Invalid expected destination SHA256')
        if mode == 'apply' and 'expected_destination_sha256' not in resource:
            raise AdoptionError('Apply requires an explicit destination identity (null for absent)')
        matches = current == output
        conflict = not matches and (None if current is None else _hash(current)) != expected
        reports.append(dict(source=src, destination=dst, source_blob=blob.decode(), source_sha256=_hash(raw), source_bytes=len(raw), replacements=replacements, output_sha256=_hash(output), output_bytes=len(output), destination_sha256=None if current is None else _hash(current), conflict=conflict, status='unchanged' if matches else 'conflict' if conflict else 'different'))
        permissions_out = stat.S_IMODE(target.stat().st_mode) if current is not None else int(permissions, 8) & 0o777
        plan.append((target, current, output, permissions_out, dst))
    report = dict(schema_version=SCHEMA_VERSION, mode=mode, source_repository=str(source), revision=revision, destination_repository=str(destination), resources=reports, status='verified' if all(p[1] == p[2] for p in plan) else 'differences')
    if mode != 'apply':
        return report
    if any(item['conflict'] for item in reports):
        raise AdoptionError('Destination identity conflict; no files changed')
    if _git(destination, 'diff', '--cached', '--name-only', '-z'):
        raise AdoptionError('Destination has staged changes')
    flags = _git(destination, 'ls-files', '-v', '-z').split(b'\x00')
    if any(item and (item[:1].islower() or item[:1] == b'S') for item in flags):
        raise AdoptionError('Destination has hidden index flags')
    dirty = set(_git(destination, 'diff', '--name-only', '-z').decode().strip('\x00').split('\x00')) - {''}
    dirty.update(set(_git(destination, 'ls-files', '--others', '--exclude-standard', '-z').decode().strip('\x00').split('\x00')) - {''})
    allowed = {p[4] for p in plan if p[1] == p[2]}
    if dirty - allowed:
        raise AdoptionError('Destination has unrelated or drifting worktree changes')
    written, created_dirs = [], []
    try:
        for index, (target, old, output, permissions_out, dst) in enumerate(plan):
            # Recheck immediately before each write; no writes are planned until inventory validation finishes.
            if _read(_target(destination, dst)) != old:
                raise AdoptionError('Destination changed during application')
            if old == output:
                continue
            absent = []
            cursor = target.parent
            while not cursor.exists():
                absent.append(cursor)
                cursor = cursor.parent
            for directory in reversed(absent):
                directory.mkdir()
                created_dirs.append(directory)
            _atomic(target, output, permissions_out)
            written.append((target, old, permissions_out))
            reports[index]['status'] = 'applied'
    except Exception as error:
        failures = []
        for target, old, permissions_out in reversed(written):
            try:
                if old is None:
                    target.unlink()
                else:
                    _atomic(target, old, permissions_out)
            except Exception as rollback_error:
                failures.append(str(rollback_error))
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError as rollback_error:
                failures.append(str(rollback_error))
        for item in reports:
            if item['status'] == 'applied':
                item['status'] = 'rollback_uncertain' if failures else 'rolled_back'
        report.update(status='rollback_failed' if failures else 'rolled_back', error=str(error), rollback_errors=failures)
        return report
    report['status'] = 'applied' if written else 'unchanged'
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--mode', required=True, choices=('preview', 'verify', 'apply'))
    args = parser.parse_args(argv)
    try:
        path = Path(args.request)
        if path.stat().st_size > MAX_REQUEST_BYTES:
            raise AdoptionError('Request exceeds byte limit')
        data = path.read_bytes()
        if len(data) > MAX_REQUEST_BYTES:
            raise AdoptionError('Request exceeds byte limit')
        request = json.loads(data)
        if not isinstance(request, dict):
            raise AdoptionError('Request must be an object')
        report = adopt(request, args.mode)
        report['request_sha256'] = _hash(data)
        report['request_bytes'] = len(data)
        print(json.dumps(report, sort_keys=True))
        return 0 if report['status'] in ('verified', 'applied', 'unchanged') or args.mode == 'preview' else 1
    except (AdoptionError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps(dict(schema_version=SCHEMA_VERSION, status='error', mode=args.mode, error=str(error)), sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
