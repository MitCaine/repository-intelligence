"""Optional local linkage of explicit worker operations to consumer evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import signal
import tempfile
import time
import subprocess
import sys

from .adapter_conformance import assess, request_digests
from .adoption import AdoptionError, _git, _root

SCHEMA_VERSION = 1
MAX_BYTES = 1_000_000
MAX_IDENTITY_BYTES = 1_000_000_000


class ExecutionError(ValueError):
    pass


def read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ExecutionError('Expected bounded regular file: ' + str(path))
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ExecutionError('File exceeds byte limit')
    return data


def identity(path: Path) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_IDENTITY_BYTES:
            raise ExecutionError('Identity needs a regular file within the byte limit')
        digest = hashlib.sha256()
        count = 0
        while chunk := os.read(fd, 65536):
            count += len(chunk)
            if count > MAX_IDENTITY_BYTES:
                raise ExecutionError('Identity exceeds byte limit')
            digest.update(chunk)
        after = os.fstat(fd)
        current = path.stat(follow_symlinks=False)
        def observed(value):
            return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                    value.st_mtime_ns, value.st_ctime_ns)
        if observed(before) != observed(after) or observed(after) != observed(current) or count != before.st_size:
            raise ExecutionError('File changed while hashing')
        return dict(path=str(path), sha256=digest.hexdigest())
    finally:
        os.close(fd)


def absolute(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ExecutionError('Expected absolute non-symlink path')
    return path


def save(path: Path, value: dict) -> None:
    fd, name = tempfile.mkstemp(prefix=path.name + '.tmp-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def owned_run(argv, cwd, environment, stdout, stderr, timeout):
    if os.name != 'posix':
        raise ExecutionError('Local process ownership is unsupported on this platform')
    process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stdout,
                               stderr=stderr, start_new_session=True)
    interrupted = None
    try:
        code = process.wait(timeout=timeout)
    except BaseException as error:
        interrupted = error
        code = None
    # Normal immediate-child exit does not establish descendant completion.
    survivors = False
    try:
        os.killpg(process.pid, 0)
        survivors = True
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=2)
    outlived_parent = survivors
    deadline = time.monotonic() + 2
    while survivors and time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            survivors = False
            break
        time.sleep(0.02)
    if interrupted is not None or outlived_parent:
        return dict(exit_code=code, status='incomplete', outputs_final=not survivors,
                    error=str(interrupted) if interrupted else 'Descendant outlived immediate child; operation incomplete')
    return dict(exit_code=code, status='passed' if code == 0 else 'failed', outputs_final=True)


def frozen(root: Path, commit: str) -> None:
    if _git(root, 'rev-parse', 'HEAD').decode().strip() != commit:
        raise ExecutionError('Workspace HEAD mismatch')
    if any(item and (item[:1].islower() or item[:1] == b'S') for item in _git(root, 'ls-files', '-v', '-z').split(b'\x00')):
        raise ExecutionError('Hidden index flags are unsupported')
    if _git(root, 'status', '--porcelain', '--untracked-files=all').strip():
        raise ExecutionError('Candidate is not a clean frozen source')


def workspace_binding(root: Path) -> dict:
    gitdir = _git(root, 'rev-parse', '--absolute-git-dir').decode().strip()
    common = _git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()
    config = identity(Path(common) / 'config')
    return dict(git_config=config, root=str(root), root_inode=[root.stat().st_dev, root.stat().st_ino],
                git_directory=gitdir, git_inode=[Path(gitdir).stat().st_dev, Path(gitdir).stat().st_ino])


def selected_inputs(request: dict) -> list:
    supplied = request['inputs']
    if not isinstance(supplied, list) or not supplied or len(supplied) > 128:
        raise ExecutionError('Assignment/instruction inputs must be a bounded nonempty list')
    observed = []
    for item in supplied:
        actual = identity(absolute(item['path']))
        if actual['sha256'] != item['sha256']:
            raise ExecutionError('Selected input mismatch: ' + item['path'])
        observed.append(actual)
    return observed


def native_string(value: str) -> None:
    try:
        os.fsencode(value)
    except UnicodeError as error:
        raise ExecutionError('Command input is not representable on this platform') from error


def operation_inputs(request: dict) -> list:
    results = []
    for name in ('edit', 'capture', 'runner'):
        operation = request.get(name)
        if operation is None and name == 'edit':
            continue
        if not isinstance(operation, dict) or set(operation) != {'argv', 'executable_sha256'}:
            raise ExecutionError('Operations need argv and executable_sha256')
        argv = operation['argv']
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and '\x00' not in x for x in argv):
            raise ExecutionError('Invalid operation argv')
        for value in argv:
            native_string(value)
        actual = identity(absolute(argv[0]))
        if actual['sha256'] != operation['executable_sha256']:
            raise ExecutionError('Operation executable mismatch')
        results.append(dict(operation=name, **actual))
    return results


def field(value: dict, path: list) -> object:
    if not isinstance(path, list) or not path or not all(isinstance(p, str) for p in path):
        raise ExecutionError('Binding paths need a nonempty list of object keys')
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise ExecutionError('Missing consumer result field: ' + key)
        value = value[key]
    return value


def helper_outputs():
    return {'', '.', '..', 'RETURN.json', 'PREPARED.json', 'LAUNCHED', 'CHECK_REQUEST.json',
            *(name + '.' + channel for name in ('edit', 'capture', 'runner') for channel in ('stdout', 'stderr'))}


def prepare(request: dict, evidence: Path, *, initial: bool = True) -> dict:
    required = {'assignment', 'attempt', 'workspace', 'protected_repository', 'base', 'inputs',
                'allowed_changes', 'capture_authority', 'environment', 'capture', 'runner',
                'runner_result', 'result_bindings', 'require_new_candidate', 'check_request'}
    if not isinstance(request, dict) or not required <= set(request) or set(request) - required - {'edit', 'timeout_seconds', 'route', 'conformance', 'integration_base'}:
        raise ExecutionError('Invalid explicit execution binding fields')
    route = request.get('route', 'subprocess')
    if route not in ('subprocess', 'interactive') or (route == 'interactive' and request.get('edit') is not None):
        raise ExecutionError('Interactive route uses worker edits, not an edit launcher')
    if not isinstance(request['assignment'], str) or not request['assignment'].strip():
        raise ExecutionError('Assignment identity required')
    if type(request['require_new_candidate']) is not bool:
        raise ExecutionError('Consumer must select new-candidate requirement explicitly')
    timeout = request.get('timeout_seconds', 300)
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        raise ExecutionError('Timeout must be between 1 and 3600 seconds')
    if not isinstance(request['runner_result'], str) or Path(request['runner_result']).name != request['runner_result'] or request['runner_result'] in helper_outputs() or request['runner_result'].startswith(tuple(name + '.tmp' for name in helper_outputs())):
        raise ExecutionError('Runner result must name a distinct direct attempt file')
    if not isinstance(request['result_bindings'], dict) or set(request['result_bindings']) != {'candidate', 'workspace', 'attempt', 'ready', 'references', 'request_sha256'}:
        raise ExecutionError('Explicit consumer result bindings required')
    for binding in request['result_bindings'].values():
        if not isinstance(binding, list) or not binding or len(binding) > 32 or not all(isinstance(k, str) and k for k in binding):
            raise ExecutionError('Every result binding needs a bounded nonempty object-key path')
    if 'conformance' in request and (not isinstance(request['conformance'], list) or not request['conformance'] or not all(isinstance(k, str) and k for k in request['conformance'])):
        raise ExecutionError('Conformance binding needs a nonempty object-key path')
    if not isinstance(request['check_request'], dict) or not request['check_request']:
        raise ExecutionError('Explicit consumer check request template required')
    if not isinstance(request['attempt'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', request['attempt']):
        raise ExecutionError('Invalid attempt identity')
    root = _root(str(absolute(request['workspace'])))
    base = request['base']
    if not isinstance(base, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', base):
        raise ExecutionError('Full base commit required')
    if initial or route == 'subprocess':
        frozen(root, base)
    else:
        _git(root, 'merge-base', '--is-ancestor', base, 'HEAD')
    integration_base = request.get('integration_base', base)
    if not isinstance(integration_base, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', integration_base):
        raise ExecutionError('Full integration base required')
    _git(root, 'merge-base', '--is-ancestor', integration_base, base)
    protected = _root(str(absolute(request['protected_repository'])))
    if root == protected or root in protected.parents or protected in root.parents:
        raise ExecutionError('Prepared workspace must be separate from protected repository')
    paths = request['allowed_changes']
    if not isinstance(paths, list) or not paths or len(paths) > 128:
        raise ExecutionError('Explicit bounded allowed changes required')
    for path in paths:
        if not isinstance(path, str) or Path(path).is_absolute() or any(x in ('', '.', '..', '.git') for x in path.split('/')):
            raise ExecutionError('Unsafe allowed change path')
    if not isinstance(request['capture_authority'], str) or not request['capture_authority'].strip():
        raise ExecutionError('Explicit consumer capture authority reference required')
    if not isinstance(request['environment'], dict) or not all(isinstance(k, str) and k and '=' not in k and '\x00' not in k and isinstance(v, str) and '\x00' not in v for k, v in request['environment'].items()):
        raise ExecutionError('Explicit child environment required')
    for key, value in request['environment'].items():
        native_string(key)
        native_string(value)
    return dict(schema_version=SCHEMA_VERSION, assignment=request['assignment'], attempt=request['attempt'],
                base=base, workspace=workspace_binding(root), selected_inputs=selected_inputs(request),
                operations=operation_inputs(request), capture_authority=request['capture_authority'],
                request_sha256=hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
                environment_sha256=hashlib.sha256(json.dumps(request['environment'], sort_keys=True).encode()).hexdigest())


def execute(request: dict, evidence: Path, mode: str) -> dict:
    if mode not in ('prepare', 'run'):
        raise ExecutionError('Unsupported execution mode')
    evidence = absolute(str(evidence))
    if not evidence.is_dir():
        raise ExecutionError('Evidence parent must already exist')
    attempt = evidence / request['attempt']
    prepared = prepare(request, evidence, initial=mode == 'prepare')
    if mode == 'prepare':
        attempt.mkdir(exist_ok=False)
        save(attempt / 'PREPARED.json', prepared)
        return prepared
    retained = json.loads(read(attempt / 'PREPARED.json'))
    if prepared != retained:
        raise ExecutionError('Prepared assignment/workspace binding mismatch')
    # Exclusive launch marker prevents repeat execution after failure or a lost reply.
    with (attempt / 'LAUNCHED').open('x') as stream:
        stream.write('Existing terminal/partial evidence must be reconciled, not relaunched.\n')
    report = dict(schema_version=SCHEMA_VERSION, assignment=request['assignment'], attempt=request['attempt'],
                  base=request['base'], prepared=identity(attempt / 'PREPARED.json'), status='incomplete',
                  operations=[], review_ready=False,
                  limits='Mechanical linkage only; no filesystem isolation, semantic acceptance, or authority authentication.')
    result_path = attempt / 'RETURN.json'
    save(result_path, report)
    root = Path(request['workspace'])
    initial_binding = retained['workspace']
    def check_workspace(expected_head: str, clean: bool = False):
        if any(item and (item[:1].islower() or item[:1] == b'S') for item in _git(root, 'ls-files', '-v', '-z').split(b'\x00')):
            raise ExecutionError('Hidden index flags are unsupported before operations')
        if workspace_binding(_root(str(root))) != initial_binding:
            raise ExecutionError('Workspace identity substituted')
        if _git(root, 'rev-parse', 'HEAD').decode().strip() != expected_head:
            raise ExecutionError('Workspace HEAD changed before operation')
        if selected_inputs(request) != retained['selected_inputs'] or operation_inputs(request) != retained['operations']:
            raise ExecutionError('Bound inputs changed before operation')
        if clean:
            frozen(root, expected_head)
    def invoke(name: str, candidate: str):
        check_workspace(candidate, clean=name == 'runner')
        substitutions = {'{workspace}': str(root), '{attempt}': str(attempt), '{candidate}': candidate, '{check_request}': str(attempt / 'CHECK_REQUEST.json')}
        argv = [substitutions.get(x, x) for x in request[name]['argv']]
        row = dict(operation=name, status='incomplete', exit_code=None)
        report['operations'].append(row)
        save(result_path, report)
        # Only invocation output is retained here; consumer runner owns gate logs.
        try:
            with (attempt / (name + '.stdout')).open('xb') as stdout, (attempt / (name + '.stderr')).open('xb') as stderr:
                row.update(owned_run(argv, root, request['environment'], stdout, stderr, request.get('timeout_seconds', 300)))
        except (OSError, subprocess.SubprocessError) as error:
            row.update(status='incomplete', outputs_final=False, error=str(error))
        for channel in ('stdout', 'stderr'):
            path = attempt / (name + '.' + channel)
            if path.exists():
                row[channel] = identity(path) if row.get('outputs_final') else dict(path=str(path), status='not-final')
        save(result_path, report)
        if row['status'] != 'passed' and name != 'runner':
            raise ExecutionError(name + ' operation failed or incomplete')
        return row['status'] == 'passed'
    try:
        capture_parent = request['base']
        if request.get('route', 'subprocess') == 'interactive':
            capture_parent = _git(root, 'rev-parse', 'HEAD').decode().strip()
            check_workspace(capture_parent)
            _git(root, 'merge-base', '--is-ancestor', request['base'], capture_parent)
            changed = _git(root, 'diff', '--no-renames', '--name-only', '-z', request['base'], capture_parent).split(b'\x00')
            changed += _git(root, 'diff', '--cached', '--no-renames', '--name-only', '-z', capture_parent).split(b'\x00')
            changed += _git(root, 'diff', '--no-renames', '--name-only', '-z').split(b'\x00')
            changed += _git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\x00')
            if {path.decode() for path in changed if path} - set(request['allowed_changes']):
                raise ExecutionError('Interactive edits exceed original authorized paths')
            report['post_edit_head'] = capture_parent
            report['post_edit_paths'] = sorted({path.decode() for path in changed if path})
            save(result_path, report)
        if request.get('edit'):
            invoke('edit', request['base'])
        check_workspace(capture_parent)
        invoke('capture', capture_parent)
        candidate = _git(root, 'rev-parse', 'HEAD').decode().strip()
        frozen(root, candidate)
        if request['require_new_candidate'] and candidate == request['base']:
            raise ExecutionError('Required frozen candidate was not captured')
        _git(root, 'merge-base', '--is-ancestor', request['base'], candidate)
        changed = _git(root, 'diff', '--no-renames', '--name-only', '-z', request['base'], candidate).decode().strip('\x00').split('\x00')
        changed = [path for path in changed if path]
        if set(changed) - set(request['allowed_changes']):
            raise ExecutionError('Capture contains unauthorized changed paths')
        integration_base = request.get('integration_base', request['base'])
        full_paths = _git(root, 'diff', '--no-renames', '--name-only', '-z', integration_base, candidate).decode().strip('\x00').split('\x00')
        report.update(candidate=candidate, changed_paths=changed, integration_base=integration_base,
                      integration_changed_paths=[path for path in full_paths if path], recovery_base=request['base'])
        bindings = request['result_bindings']
        runner_file = attempt / request['runner_result']
        if Path(request['runner_result']).name != request['runner_result'] or runner_file.exists():
            raise ExecutionError('Runner result needs an absent direct attempt filename')
        def bind(value):
            if isinstance(value, str):
                return {'{candidate}': candidate, '{workspace}': str(root), '{attempt}': request['attempt']}.get(value, value)
            if isinstance(value, list):
                return [bind(item) for item in value]
            if isinstance(value, dict):
                return {key: bind(item) for key, item in value.items()}
            return value
        save(attempt / 'CHECK_REQUEST.json', bind(request['check_request']))
        report['check_request'] = identity(attempt / 'CHECK_REQUEST.json')
        runner_passed = invoke('runner', candidate)
        check_workspace(candidate, clean=True)
        if report['operations'][-1].get('outputs_final') is not True:
            report['runner_result'] = dict(path=str(runner_file), status='not-final')
            raise ExecutionError('Runner activity is unresolved; output is not final')
        report['runner_result'] = identity(runner_file)
        result = json.loads(read(runner_file))
        if field(result, bindings['request_sha256']) != report['check_request']['sha256'] or identity(attempt / 'CHECK_REQUEST.json') != report['check_request']:
            raise ExecutionError('Consumer check request binding mismatch')
        if field(result, bindings['candidate']) != candidate or field(result, bindings['workspace']) != str(root):
            raise ExecutionError('Runner source binding mismatch')
        if field(result, bindings['attempt']) != request['attempt']:
            raise ExecutionError('Runner attempt mismatch')
        references = field(result, bindings['references'])
        if not isinstance(references, list) or not references or len(references) > 128:
            raise ExecutionError('Bounded nonempty evidence references required')
        verified = []
        for item in references:
            actual = identity(absolute(item['path']))
            if actual['sha256'] != item['sha256']:
                raise ExecutionError('Stale evidence reference')
            verified.append(actual)
        report['references'] = verified
        if 'conformance' in request:
            report['conformance'] = assess(field(result, request['conformance']), request_digests(read(attempt / 'CHECK_REQUEST.json')))
            if not report['conformance']['ready']:
                raise ExecutionError('Consumer mapped facts fail adapter conformance')
        if not runner_passed or field(result, bindings['ready']) is not True:
            raise ExecutionError('Consumer runner reports failed/incomplete/ineligible evidence')
        report.update(status='complete', review_ready=True)
    except (ExecutionError, AdoptionError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report.update(status='blocked', error=str(error))
    finally:
        save(result_path, report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--mode', choices=('prepare', 'run'), required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(read(args.request))
        result = execute(request, args.evidence, args.mode)
        print(json.dumps(result, sort_keys=True))
        return 0 if args.mode == 'prepare' or result['review_ready'] else 1
    except (ExecutionError, AdoptionError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps(dict(schema_version=SCHEMA_VERSION, status='blocked', error=str(error))))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
