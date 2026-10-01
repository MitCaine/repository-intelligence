"""Durable maintenance review obligations; no hosted approval is inferred here."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
import tomllib


def target_bytes(root: Path, kind: str, target: str) -> bytes:
    if kind == 'grammar':
        project = tomllib.loads((root / 'pyproject.toml').read_text())
        requirements = project['build-system']['requires'] + project['project']['dependencies']
        import re
        pins = [value for value in requirements
                if re.sub(r'[-_.]+', '-', value.split('==')[0]).lower() == target]
        if not pins:
            return b'absent'
        return json.dumps(sorted(pins)).encode()
    if kind == 'actions':
        directory = root / '.github' / 'workflows'
        files = sorted([*directory.glob('*.yml'), *directory.glob('*.yaml')])
        return json.dumps({path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in files}, sort_keys=True).encode()
    raise ValueError('Unsupported maintenance obligation')


def identity(root: Path, commit: str, kind: str, target: str) -> str:
    changes = subprocess.run(['git', 'diff', '--binary', 'HEAD', '--',
                              'src', 'scripts', 'tests', 'pyproject.toml'], cwd=root,
                             capture_output=True, check=True, timeout=20).stdout
    return hashlib.sha256(commit.encode() + b'\0' + changes + b'\0' +
                          target_bytes(root, kind, target)).hexdigest()


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    record = json.loads(path.read_text())
    if (not isinstance(record, dict) or set(record) != {'schema_version', 'pending'}
            or type(record.get('schema_version')) is not int or record['schema_version'] != 1
            or not isinstance(record.get('pending'), dict)):
        raise ValueError('Invalid pending maintenance review state')
    pending = record['pending']
    for key, item in pending.items():
        if (not isinstance(item, dict) or set(item) != {'kind', 'target', 'reason', 'source_commit', 'sha256'}
                or not all(isinstance(v, str) and v for v in item.values())
                or key != item['kind'] + ':' + item['target']):
            raise ValueError('Invalid pending maintenance obligation')
    return pending


def refresh(root: Path, commit: str, pending: dict) -> dict:
    # A newer pin/source supersedes the subject, never the unresolved review itself.
    return {key: {**item, 'source_commit': commit,
                  'sha256': identity(root, commit, item['kind'], item['target'])}
            for key, item in pending.items()}


def add(root: Path, commit: str, pending: dict, kind: str, target: str, reason: str) -> None:
    pending[kind + ':' + target] = {'kind': kind, 'target': target, 'reason': reason,
        'source_commit': commit, 'sha256': identity(root, commit, kind, target)}


def resolve(pending: dict, resolutions: list[str]) -> None:
    for resolution in resolutions:
        key, separator, digest = resolution.rpartition('=')
        if not separator or key not in pending or pending[key]['sha256'] != digest:
            raise ValueError('Review resolution does not match a current obligation identity')
        del pending[key]
