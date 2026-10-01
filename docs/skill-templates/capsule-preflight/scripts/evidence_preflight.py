"""Read-only consumer adapter template; validates exported contract and evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess


class Blocked(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def load(path):
    require(stat.S_ISREG(path.lstat().st_mode), f'not a regular file: {path}')
    require(path.stat().st_size <= 2_000_000, f'record too large: {path}')
    value = json.loads(path.read_text(), object_pairs_hook=unique_object)
    require(isinstance(value, dict), f'expected object: {path}')
    require(type(value.get('schema_version')) is int and value['schema_version'] == 1,
            f'unsupported schema: {path}')
    return value


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args],
                                   stderr=subprocess.PIPE, timeout=30)


def relative_path(value):
    require(isinstance(value, str) and value and '\\' not in value,
            f'invalid relative path: {value!r}')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and str(path) == value,
            f'noncanonical relative path: {value!r}')
    return value


def nonempty_strings(values, label):
    require(isinstance(values, list) and values and
            all(isinstance(v, str) and v for v in values) and
            len(set(values)) == len(values), f'invalid {label}')
    return values


def indexed(records, label):
    require(isinstance(records, list), f'invalid {label}')
    result = {}
    for record in records:
        require(isinstance(record, dict) and isinstance(record.get('id'), str) and
                record['id'], f'invalid {label} ID')
        require(record['id'] not in result, f'duplicate {label} ID: {record["id"]}')
        result[record['id']] = record
    return result


def validate_invocation(invocation, root, candidate):
    require(isinstance(invocation, dict), 'missing invocation')
    require(isinstance(invocation.get('argv'), list) and invocation['argv'] and
            all(isinstance(v, str) and v for v in invocation['argv']), 'invalid invocation argv')
    require(set(invocation) == {'argv', 'cwd', 'config', 'interpreter', 'profiles',
                                'isolation', 'environment', 'source_files'},
            'incomplete or unsupported invocation fields')
    relative_path(invocation['cwd'])
    directory = root / invocation['cwd']
    require(directory.is_dir() and directory.resolve().is_relative_to(root.resolve()),
            'invocation cwd missing or escapes candidate')
    for field in ('interpreter', 'isolation'):
        require(isinstance(invocation[field], str) and invocation[field], f'missing {field}')
    nonempty_strings(invocation['profiles'], 'invocation profiles')
    for field in ('config', 'environment'):
        require(isinstance(invocation[field], dict) and
                all(isinstance(k, str) and isinstance(v, str)
                    for k, v in invocation[field].items()), f'invalid {field}')
    sources = invocation['source_files']
    require(isinstance(sources, dict) and sources, 'missing rehearsal source files')
    for path, identity in sources.items():
        relative_path(path)
        require(isinstance(identity, dict) and set(identity) == {'sha256', 'mode'},
                f'missing rehearsal mode/hash: {path}')
        entry = git(root, 'ls-tree', '-z', candidate, '--', path).split(b'\0')[0]
        require(entry and entry.split(b'\t', 1)[-1].decode() == path,
                f'missing exact rehearsal source: {path}')
        mode, kind, _ = entry.split(b'\t', 1)[0].decode().split()
        require(kind == 'blob' and mode == identity['mode'], f'rehearsal mode mismatch: {path}')
        actual = hashlib.sha256(git(root, 'show', f'{candidate}:{path}')).hexdigest()
        require(actual == identity['sha256'], f'rehearsal source mismatch: {path}')


def validate_log(record, packet_dir, name):
    log = packet_dir / relative_path(record.get('log_path'))
    require(log.resolve().is_relative_to(packet_dir.resolve()), f'{name}: log escapes packet directory')
    require(stat.S_ISREG(log.lstat().st_mode), f'{name}: log is not regular')
    require(log.stat().st_size <= 32_000_000, f'{name}: log too large')
    require(hashlib.sha256(log.read_bytes()).hexdigest() == record.get('log_sha256'),
            f'{name}: retained log digest mismatch')


def validate_observations(expected, observed, name):
    """Compare trusted mandatory nodes with actual runner-exported observations."""
    required = indexed(expected.get('mandatory_observations', []), f'{name} mandatory observations')
    actual = indexed(observed.get('observations', []), f'{name} observations')
    for identifier, item in required.items():
        record = actual.get(identifier, {})
        require(item.get('stage') in ('incumbent', 'proposed', 'installed') and
                isinstance(item.get('gate_identity'), str) and item['gate_identity'],
                f'{name}: missing selecting gate/stage')
        require(record.get('gate_identity') == item['gate_identity'] and
                record.get('stage') == item['stage'], f'{name}: observation gate/stage mismatch')
        require(record.get('collected') is True and record.get('executed') is True and
                record.get('outcome') == 'passed', f'{name}: mandatory observation not executed successfully: {identifier}')


REUSE_INPUTS = {'code', 'dependencies', 'selector', 'configuration', 'toolchain',
                'environment', 'isolation', 'timeout_policy'}


def equivalent_inputs(previous, current):
    """Eligibility only; caller must authenticate prior proof and authorize reuse."""
    def complete(value):
        return (isinstance(value, dict) and set(value) == REUSE_INPUTS and
                all(isinstance(digest, str) and len(digest) == 64 and
                    all(c in '0123456789abcdef' for c in digest) for digest in value.values()))
    return complete(previous) and complete(current) and previous == current


def carry_review(previous, current_inputs, requirements_sha256):
    """An authenticated exported receipt may support unchanged implementation judgment."""
    return (isinstance(previous, dict) and previous.get('verdict') == 'PASS' and
            isinstance(previous.get('receipt_sha256'), str) and
            len(previous['receipt_sha256']) == 64 and
            all(c in '0123456789abcdef' for c in previous['receipt_sha256']) and
            isinstance(requirements_sha256, str) and len(requirements_sha256) == 64 and
            all(c in '0123456789abcdef' for c in requirements_sha256) and
            previous.get('requirements_sha256') == requirements_sha256 and
            equivalent_inputs(previous.get('inputs'), current_inputs))


def validate_reuse(execution, authorization, policy, root, packet_dir, candidate):
    """Validate authenticated consumer exports without relabeling old execution.

    The consumer authenticates policy, freshness, trust and both records before
    calling. This is an eligibility check, never execution or acceptance.
    """
    require(isinstance(policy, dict) and policy.get('adopted') is True and
            isinstance(policy.get('version'), str) and policy['version'],
            'reuse requires an adopted versioned policy')
    require(isinstance(execution, dict) and isinstance(authorization, dict),
            'missing separate reuse records')
    origin = execution.get('candidate')
    current = authorization.get('candidate')
    require(current == candidate, 'reuse authorization names another current candidate')
    for value in (origin, current):
        require(isinstance(value, str) and len(value) in (40, 64) and
                all(c in '0123456789abcdef' for c in value) and
                git(root, 'rev-parse', f'{value}^{{commit}}').decode().strip() == value,
                'unresolved reuse candidate')
    require(execution.get('exit_code') == 0 and type(execution.get('exit_code')) is int,
            'original execution did not pass')
    validate_invocation(execution.get('invocation'), root, origin)
    validate_log(execution, packet_dir, 'original execution')
    digest = hashlib.sha256(json.dumps(execution, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    require(authorization.get('execution_sha256') == digest and
            authorization.get('policy_version') == policy['version'] and
            authorization.get('claim') in policy.get('allowed_claims', []) and
            authorization.get('trusted') is True and authorization.get('fresh') is True,
            'reuse authorization does not bind eligible original proof')
    require(equivalent_inputs(execution.get('inputs'), authorization.get('inputs')),
            'changed or unknown reuse inputs')
    return {'execution_candidate': origin, 'authorization_candidate': current,
            'execution_sha256': digest}


def validate_obligation_stage(obligations, stage, *, phase='complete'):
    """At intake allow review to satisfy its own obligations; never defer completion."""
    stages = ['candidate', 'installed', 'terminal']
    require(stage in stages and phase in ('intake', 'complete'), 'invalid obligation stage/phase')
    records = indexed(obligations, 'obligations')
    deferred = []
    for identifier, item in records.items():
        deadline = item.get('deadline_stage')
        route = item.get('satisfied_by')
        require(deadline in stages and route in ('external', 'review') and
                item.get('status') in ('passed', 'pending', 'failed'),
                f'{identifier}: missing obligation deadline/route/status')
        require(item.get('supersedes') != identifier, f'{identifier}: self-superseding obligation')
        due = stages.index(deadline) <= stages.index(stage)
        review_can_resolve = (phase == 'intake' and route == 'review' and
                              deadline == stage and item['status'] == 'pending')
        if due and not review_can_resolve:
            require(item['status'] == 'passed', f'{identifier}: unresolved applicable obligation')
        if item['status'] != 'passed':
            deferred.append(identifier)
    return sorted(deferred)


def validate_closeout(expected, observed, checks, root, packet_dir):
    """Check consumer-normalized history/probes; consumer authenticates exports."""
    require(isinstance(expected, dict) and isinstance(observed, dict), 'missing closeout record')
    validator = expected.get('history_check_id')
    require(isinstance(validator, str) and validator in checks, 'missing history validator check')
    record = checks[validator]
    require(observed.get('validator_evidence') == {
        'id': validator, 'candidate': record['candidate'], 'exit_code': record['exit_code'],
        'log_path': record['log_path'], 'log_sha256': record['log_sha256']},
        'history validator evidence mismatch')
    fields = nonempty_strings(expected.get('required_metadata'), 'required history metadata')
    metadata = observed.get('metadata')
    frozen = expected.get('metadata')
    require(isinstance(metadata, dict) and isinstance(frozen, dict) and
            all(key in metadata and metadata[key] not in (None, '', [], {}) for key in fields)
            and all(key in frozen for key in fields) and metadata == frozen,
            'history metadata missing or mismatched')
    validate_log(observed, packet_dir, 'history')
    recovery = expected.get('recovery_commit')
    installed = expected.get('installed_base')
    for label, sha in [('recovery', recovery), ('installed', installed)]:
        require(isinstance(sha, str) and len(sha) in (40, 64) and
                all(c in '0123456789abcdef' for c in sha) and
                git(root, 'rev-parse', f'{sha}^{{commit}}').decode().strip() == sha,
                f'invalid {label} source')
        require(observed.get(label + ('_commit' if label == 'recovery' else '_base')) == sha,
                f'{label} identity mismatch')
    capsule = relative_path(expected.get('capsule_path'))
    digest = hashlib.sha256(git(root, 'show', f'{recovery}:{capsule}')).hexdigest()
    require(expected.get('capsule_sha256') == digest and
            observed.get('capsule_sha256') == digest, 'recovery capsule hash mismatch')
    probes = indexed(observed.get('probes'), 'live probes')
    require(set(probes) == {'negative', 'positive'}, 'missing live probe pair')
    frozen_probes = expected.get('probes')
    require(isinstance(frozen_probes, dict) and set(frozen_probes) == set(probes),
            'missing trusted probe identities')
    candidates = []
    for name, outcome in [('negative', 'failed'), ('positive', 'passed')]:
        probe = probes[name]
        require(probe.get('installed_base') == installed and
                probe.get('workflow_identity') == expected.get('workflow_identity') and
                isinstance(expected.get('workflow_identity'), str) and expected['workflow_identity'],
                f'{name}: installed workflow mismatch')
        candidate = probe.get('candidate')
        binding = frozen_probes[name]
        require(isinstance(binding, dict) and candidate == binding.get('candidate') and
                isinstance(binding.get('check_id'), str) and binding['check_id'] and
                probe.get('check_id') == binding['check_id'], f'{name}: probe identity mismatch')
        require(isinstance(candidate, str) and len(candidate) in (40, 64) and
                all(c in '0123456789abcdef' for c in candidate), f'{name}: invalid candidate')
        git(root, 'merge-base', '--is-ancestor', installed, candidate)
        require(candidate != installed, f'{name}: missing probe candidate')
        candidates.append(candidate)
        selected = expected.get('selected_test_id')
        require(isinstance(selected, str) and selected and probe.get('selected_test_id') == selected
                and probe.get('selected_test_outcome') == outcome, f'{name}: selected test mismatch')
        require(probe.get('failed_test_ids') == ([selected] if name == 'negative' else []),
                f'{name}: unexpected failing tests')
        require(probe.get('qualification_candidate') == candidate and
                probe.get('qualification_outcome') == outcome, f'{name}: qualification mismatch')
        require(type(probe.get('exit_code')) is int and
                (probe['exit_code'] != 0 if name == 'negative' else probe['exit_code'] == 0),
                f'{name}: exit status mismatch')
        validate_log(probe, packet_dir, name)
    require(candidates[0] != candidates[1], 'live probes require separate candidates')


def validate(contract, packet, root, packet_dir):
    identity = contract.get('identity')
    require(isinstance(identity, dict) and set(identity) ==
            {'task_id', 'revision', 'base', 'planning', 'candidate'}, 'invalid contract identity')
    require(isinstance(identity['task_id'], str) and identity['task_id'] and
            type(identity['revision']) is int and identity['revision'] > 0, 'invalid task/revision')
    require(packet.get('identity') == identity, 'packet identity differs from trusted contract')
    for field in ('base', 'planning', 'candidate'):
        sha = identity[field]
        require(isinstance(sha, str) and len(sha) in (40, 64) and
                all(c in '0123456789abcdef' for c in sha), f'invalid {field} SHA')
        require(git(root, 'rev-parse', f'{sha}^{{commit}}').decode().strip() == sha,
                f'unresolved {field}')
    b, p, c = (identity[x] for x in ('base', 'planning', 'candidate'))
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == c, 'checkout head differs from C')
    require(not git(root, 'status', '--porcelain', '--untracked-files=all'), 'dirty checkout')
    git(root, 'merge-base', '--is-ancestor', b, p)
    git(root, 'merge-base', '--is-ancestor', p, c)
    allowed = set(nonempty_strings(contract.get('allowed_paths'), 'allowed paths'))
    for path in allowed:
        relative_path(path)
    inventory = contract.get('inventory')
    require(isinstance(inventory, list) and inventory, 'missing impact inventory')
    edits = set()
    seen = set()
    for row in inventory:
        require(isinstance(row, dict), 'invalid inventory row')
        path = relative_path(row.get('path'))
        require(path not in seen, f'duplicate inventory path: {path}')
        seen.add(path)
        require(row.get('disposition') in ('edit', 'inspect') and
                isinstance(row.get('purpose'), str) and row['purpose'].strip(),
                f'missing inventory purpose/disposition: {path}')
        if row['disposition'] == 'edit':
            edits.add(path)
    require(edits <= allowed, 'inventory edits exceed authorized paths')
    changed = set(filter(None, git(root, 'diff', '--name-only', '-z', '--no-renames',
                                  p, c).decode().split('\0')))
    require(changed <= allowed and changed <= edits,
            f'changed paths absent from authorized edit inventory: {sorted(changed - (allowed & edits))}')
    required = indexed(contract.get('checks'), 'required checks')
    require(required, 'empty required checks')
    observed = indexed(packet.get('checks'), 'observed checks')
    require(set(required) == set(observed), 'missing or unexpected check IDs')
    rehearsals = indexed(packet.get('rehearsals'), 'rehearsals')
    require(set(rehearsals) == {name for name, item in required.items()
                               if item.get('rehearsal_required') is True},
            'missing or unexpected rehearsal IDs')
    for name, expected in required.items():
        record = observed[name]
        require(record.get('candidate') == c and record.get('profile') == expected.get('profile')
                and isinstance(expected.get('profile'), str) and expected['profile'],
                f'{name}: candidate/profile mismatch')
        require(type(record.get('exit_code')) is int and record['exit_code'] == 0,
                f'{name}: unsuccessful or missing exit status')
        validate_log(record, packet_dir, name)
        validate_observations(expected, record, name)
        count = record.get('skip_count')
        skips = record.get('skips')
        require(type(count) is int and count >= 0 and isinstance(skips, list) and
                len(skips) == count, f'{name}: missing skip detail')
        indexed(skips, f'{name} skips')
        allowed_skips = expected.get('allowed_skip_ids')
        require(isinstance(allowed_skips, list) and
                all(isinstance(v, str) and v for v in allowed_skips) and
                len(set(allowed_skips)) == len(allowed_skips), f'{name}: invalid allowed skip IDs')
        require({s['id'] for s in skips} <= set(allowed_skips), f'{name}: unauthorized skipped tests')
        for skip in skips:
            require(isinstance(skip.get('reason'), str) and skip['reason'].strip(),
                    f'{name}: missing skip reason')
        probe_required = expected.get('probe_required')
        rehearsal_required = expected.get('rehearsal_required')
        require(type(probe_required) is bool and type(rehearsal_required) is bool,
                f'{name}: missing contract flags')
        if probe_required:
            probe = record.get('capability_probe')
            require(isinstance(probe, dict) and type(probe.get('available')) is bool and
                    isinstance(probe.get('detail'), str) and probe['detail'].strip(),
                    f'{name}: missing capability probe result')
        invocation = expected.get('invocation')
        validate_invocation(invocation, root, c)
        require(record.get('invocation') == invocation, f'{name}: frozen invocation drift')
        if rehearsal_required:
            rehearsal = rehearsals.get(name, {})
            require(type(rehearsal.get('exit_code')) is int and rehearsal['exit_code'] == 0 and
                    rehearsal.get('invocation') == invocation, f'{name}: rehearsal mismatch or failure')
            validate_log(rehearsal, packet_dir, f'{name} rehearsal')
    if 'closeout' in contract:
        validate_closeout(contract['closeout'], packet.get('closeout'), observed, root, packet_dir)
    else:
        require('closeout' not in packet, 'unexpected closeout without trusted expectations')
    return sorted(changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--packet', type=Path, required=True)
    args = parser.parse_args()
    try:
        changed = validate(load(args.contract), load(args.packet), args.repository,
                           args.packet.parent)
        result = {'schema_version': 1, 'disposition': 'checked', 'changed_paths': changed}
        code = 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {'schema_version': 1, 'disposition': 'blocked', 'reason': str(error)}
        code = 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
