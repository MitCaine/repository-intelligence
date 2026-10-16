"""Read-only decisions over consumer-authenticated native dispatch observations.

This module does not launch workers, authenticate a host, or persist job state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


class DispatchError(ValueError):
    pass


def _identity(value: dict, label: str) -> None:
    if not isinstance(value, dict) or not all(
        isinstance(value.get(key), str) and value[key].strip()
        for key in ('assignment', 'attempt', 'operation')
    ) or value['operation'] not in ('launch', 'resume'):
        raise DispatchError(label + ' needs assignment, unique attempt and launch/resume operation')


def decide(expected: dict, observed: dict | None) -> dict:
    """Do not equate a planned handoff or unknown delivery with an active job.

    The consumer maps existing native records and owns authenticity/freshness of
    the observation, including its binding to this specific dispatch attempt.
    """
    _identity(expected, 'Selection')
    if expected['operation'] == 'resume' and not (
        isinstance(expected.get('worker'), str) and expected['worker'].strip()
    ):
        raise DispatchError('Resumption selection needs the existing worker identity')
    result = dict(assignment=expected['assignment'], attempt=expected['attempt'],
                  operation=expected['operation'], action='reconcile', may_wait=False,
                  may_mark_running=False, may_dispatch=False)
    if observed is None:
        return dict(result, reason='No accepted launch or authoritative observation; reconcile before acting')
    _identity(observed, 'Observation')
    if any(observed[key] != expected[key] for key in ('assignment', 'attempt', 'operation')):
        raise DispatchError('Stale or mismatched dispatch observation')
    if 'worker' in expected and observed.get('worker') != expected['worker']:
        raise DispatchError('Worker identity mismatch')
    state = observed.get('state')
    if state not in ('planned', 'delivered', 'unknown', 'accepted', 'active', 'terminal', 'absent', 'rejected'):
        raise DispatchError('Unknown native state mapping')
    if state in ('planned', 'delivered', 'unknown'):
        return dict(result, reason='Handoff/delivery does not establish current job acceptance or completion')
    evidence = observed.get('evidence')
    if not isinstance(evidence, str) or not evidence.strip():
        raise DispatchError('Consequential observation needs an existing authoritative evidence reference')
    if state in ('absent', 'rejected'):
        return dict(result, action='controller_decision', evidence=evidence,
                    reason='Reconciled absence/rejection; dispatch or retry still requires the selected recovery authority')
    if observed.get('accepted') is not True or not (
        isinstance(observed.get('worker'), str) and observed['worker'].strip()
    ):
        raise DispatchError('Accepted launch/resumption identity required before wait or terminal consumption')
    return dict(result, action='consume' if state == 'terminal' else 'wait',
                worker=observed['worker'], evidence=evidence,
                may_wait=state in ('accepted', 'active'), may_mark_running=state == 'active',
                reason='Use existing terminal evidence' if state == 'terminal' else 'Use supported completion wait for this accepted job')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.request.is_symlink() or not args.request.is_file() or args.request.stat().st_size > 1_000_000:
            raise DispatchError('Expected bounded regular request file')
        request = json.loads(args.request.read_bytes())
        if not isinstance(request, dict) or set(request) != {'expected', 'observed'}:
            raise DispatchError('Request needs only expected and observed projections')
        print(json.dumps(decide(request['expected'], request['observed']), sort_keys=True))
        return 0
    except (DispatchError, OSError, ValueError, TypeError) as error:
        print(json.dumps(dict(action='refused', may_wait=False, may_mark_running=False,
                              may_dispatch=False, reason=str(error))))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
