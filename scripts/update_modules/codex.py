"""Side-by-side Codex CLI updates for future attempts; no model inference."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time
import uuid


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, indent=2) + '\n')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def installation_digest(prefix):
    """Bind launcher, native optional package and installed dependencies together."""
    digest = hashlib.sha256()
    for path in sorted(prefix.rglob('*')):
        if path.is_dir() and not path.is_symlink():
            continue
        relative = path.relative_to(prefix).as_posix()
        if path.is_symlink():
            path.resolve(strict=True).relative_to(prefix.resolve())
            value = {'path': relative, 'link': os.readlink(path)}
        else:
            file_digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1_048_576), b''):
                    file_digest.update(chunk)
            value = {'path': relative, 'sha256': file_digest.hexdigest(),
                     'mode': path.stat().st_mode & 0o777}
        digest.update(json.dumps(value, sort_keys=True).encode())
        digest.update(b'\n')
    return digest.hexdigest()


def catalog(executable, timeout=30):
    """Read model/list through this executable, without creating a thread/turn."""
    process = subprocess.Popen([str(executable), 'app-server'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    deadline, buffer, received = time.monotonic() + timeout, b'', 0
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    def send(value):
        process.stdin.write((json.dumps(value) + '\n').encode())
        process.stdin.flush()

    def response(identity):
        nonlocal buffer, received
        while True:
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError('Invalid Codex response')
                if value.get('id') == identity:
                    if 'error' in value:
                        raise ValueError('Codex catalog request failed')
                    if not isinstance(value.get('result'), dict):
                        raise ValueError('Invalid Codex response result')
                    return value['result']
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError('Codex catalog timed out')
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                raise ValueError('Codex catalog process ended before response')
            received += len(chunk)
            if received > 2_000_000:
                raise ValueError('Codex catalog exceeds budget')
            buffer += chunk

    try:
        send({'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'ri_maintenance', 'version': '1'}}})
        response(1)
        send({'method': 'initialized', 'params': {}})
        models, cursor, seen, identity = [], None, set(), 2
        while True:
            send({'id': identity, 'method': 'model/list',
                  'params': {'limit': 100, 'includeHidden': True, 'cursor': cursor}})
            result = response(identity)
            if not isinstance(result.get('data'), list):
                raise ValueError('Invalid Codex catalog data')
            for item in result['data']:
                if not isinstance(item, dict) or not isinstance(item.get('supportedReasoningEfforts'), list):
                    raise ValueError('Invalid Codex catalog entry')
                model = item.get('model')
                efforts = [v.get('reasoningEffort') if isinstance(v, dict) else None
                           for v in item['supportedReasoningEfforts']]
                if not isinstance(model, str) or not all(isinstance(v, str) for v in efforts):
                    raise ValueError('Invalid Codex catalog')
                models.append({'model': model, 'efforts': efforts})
            cursor = result.get('nextCursor')
            if not cursor:
                return models
            if not isinstance(cursor, str) or cursor in seen:
                raise ValueError('Invalid Codex catalog pagination')
            seen.add(cursor)
            identity += 1
    finally:
        selector.close()
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        process.stdin.close()
        process.stdout.close()


def validate_pairs(models, pairs):
    available = {item['model']: item['efforts'] for item in models}
    for pair in pairs:
        model, separator, effort = pair.partition(':')
        if not separator or effort not in available.get(model, []):
            raise ValueError(f'Requested Codex model/effort unsupported: {pair}')


def update(cache: Path, pairs=()):
    """Select a freshly checked CLI for new attempts; old directories stay intact."""
    npm = shutil.which('npm')
    if not npm:
        raise ValueError('Codex update requires npm and Node.js')
    directory = cache / 'codex'
    directory.mkdir(parents=True, exist_ok=True)
    npm_cache = directory / 'npm-cache'
    version = json.loads(subprocess.check_output(
        [npm, '--cache', str(npm_cache), 'view', '@openai/codex', 'version', '--json'],
        timeout=60))
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Codex registry returned a non-stable version')
    selection = directory / 'selected.json'
    previous = json.loads(selection.read_text()) if selection.exists() else None
    if previous and previous['version'] == version:
        executable = Path(previous['executable'])
        if (hashlib.sha256(executable.read_bytes()).hexdigest() != previous['sha256'] or
                installation_digest(Path(previous['prefix'])) != previous['installation_sha256']):
            raise ValueError('Selected Codex executable changed; preserve and investigate')
        candidate = previous
    else:
        # A new directory prevents update-in-place mutation of existing attempts.
        prefix = directory / (version + '-' + uuid.uuid4().hex)
        prefix.mkdir()
        subprocess.run([npm, '--cache', str(npm_cache), 'install', '--prefix', str(prefix),
                        '--no-audit', '--no-fund', '--ignore-scripts',
                        '@openai/codex@' + version], check=True, timeout=300)
        executable = (prefix / 'node_modules' / '.bin' / 'codex').resolve(strict=True)
        observed = subprocess.check_output([str(executable), '--version'], timeout=15,
                                          text=True).strip()
        if observed != 'codex-cli ' + version:
            raise ValueError('Installed Codex version does not match registry selection')
        candidate = {'version': version, 'executable': str(executable), 'prefix': str(prefix),
                     'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                     'installation_sha256': installation_digest(prefix)}
    before = candidate['installation_sha256']
    models = catalog(executable)
    validate_pairs(models, pairs)
    if installation_digest(Path(candidate['prefix'])) != before:
        raise ValueError('Codex installation changed during catalog check')
    receipt = {**candidate, 'schema_version': 1, 'catalog': models,
               'requested_pairs': list(pairs), 'inference_access_verified': False,
               'consumer_route_qualified': False}
    atomic_json(selection, receipt)
    print(f'Codex CLI for future attempts: {executable}')
    return receipt
