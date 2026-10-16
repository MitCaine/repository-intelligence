"""Optional task-output lifecycle at the consumer worker/closeout seam.

Consumers supply authenticated owner definitions, live use/retention observations
and an authorized disposal callback. No inventory discovery, permission grant,
process supervision, Git cleanup, or general-purpose recursive deleter lives here.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

from .worker_execution import absolute, identity


class CleanupError(ValueError):
    pass


def _path(value: str) -> Path:
    if not isinstance(value, str) or value != os.path.normpath(value):
        raise CleanupError('Expected normalized absolute path')
    return absolute(value)


def _node(path: Path) -> list[int]:
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        raise CleanupError('Expected owned directory')
    return [info.st_dev, info.st_ino]


def _definition(binding: dict) -> dict:
    if not isinstance(binding, dict) or set(binding) != {'path', 'sha256'}:
        raise CleanupError('Expected authoritative owner-definition binding')
    observed = identity(_path(binding['path']))
    if observed != binding:
        raise CleanupError('Owner definition changed')
    return observed


def create_output(path: str, *, task: str, attempt: str, definition: dict) -> dict:
    """Replace the owner's exclusive mkdir and append this receipt to its record.

    Call only from the authoritative output definition's actual creation path.
    A pre-existing directory cannot be adopted. A lost receipt leaves an unknown
    item to preserve, not ownership inferred from its name or temporary location.
    """
    if os.name != 'posix':
        raise CleanupError('Local output identity is unsupported on this platform')
    if not all(isinstance(value, str) and value.strip() for value in (task, attempt)):
        raise CleanupError('Task and attempt required')
    binding = _definition(definition)
    target = _path(path)
    parent = _node(target.parent)
    target.mkdir(exist_ok=False)
    return dict(schema_version=1, task=task, attempt=attempt, path=str(target),
                node=_node(target), parent_node=parent, definition=binding)


def _size(path: Path) -> int:
    """Measure logical regular-file bytes without following links or special files."""
    total = 0
    device = path.stat(follow_symlinks=False).st_dev
    def failed(error):
        raise error
    for root, directories, files in os.walk(path, followlinks=False, onerror=failed):
        for name in directories + files:
            item = Path(root) / name
            info = item.stat(follow_symlinks=False)
            if info.st_dev != device:
                raise CleanupError('Nested filesystem needs consumer disposition: ' + str(item))
            if stat.S_ISDIR(info.st_mode):
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise CleanupError('Linked or special output needs consumer disposition: ' + str(item))
            total += info.st_size
    return total


def assess_output(receipt: dict, observation: dict, *, protected: list[str], retained: list[dict]) -> dict:
    """Read-only dry-run of one mapped item, never authentication of owner claims.

    The consumer reconciles live assignments/processes, complete source/evidence
    coverage and all protected paths under its existing exclusive closeout route.
    It must reobserve immediately before execution. Unknown facts retain this item.
    """
    result = dict(path=receipt.get('path') if isinstance(receipt, dict) else None,
                  status='retained', reason='', bytes=None)
    try:
        if os.name != 'posix':
            raise CleanupError('Local output identity is unsupported on this platform')
        required = {'schema_version', 'task', 'attempt', 'path', 'node', 'parent_node', 'definition'}
        if (not isinstance(receipt, dict) or set(receipt) != required
                or type(receipt['schema_version']) is not int or receipt['schema_version'] != 1
                or not all(isinstance(receipt[key], str) and receipt[key].strip() for key in ('task', 'attempt'))
                or not all(isinstance(receipt[key], list) and len(receipt[key]) == 2
                           and all(type(value) is int and value >= 0 for value in receipt[key])
                           for key in ('node', 'parent_node'))):
            raise CleanupError('Unknown creation receipt')
        if not isinstance(observation, dict) or any(
                observation.get(key) != receipt[key] for key in ('task', 'attempt')):
            raise CleanupError('Current ownership observation does not match creation')
        _definition(receipt['definition'])
        path = _path(receipt['path'])
        if _node(path.parent) != receipt['parent_node']:
            raise CleanupError('Output parent identity changed')
        if observation.get('state') not in ('completed', 'superseded_terminal'):
            raise CleanupError('Attempt is active, paused or not verified terminal')
        for fact in ('exclusive', 'quiescent', 'regenerable', 'source_preserved', 'references_relocated'):
            if observation.get(fact) is not True:
                raise CleanupError('Unestablished prerequisite: ' + fact)
        if not isinstance(protected, list) or not protected:
            raise CleanupError('Consumer protected-path observation required')
        if not isinstance(retained, list) or not retained:
            raise CleanupError('Authenticated readable retention bindings required')
        protected_paths = [_path(value) for value in protected]
        protected_paths += [_path(binding['path']) for binding in retained]
        protected_paths += [_path(receipt['definition']['path'])]
        for other in protected_paths:
            if path == other or path in other.parents or other in path.parents:
                raise CleanupError('Output overlaps a protected source/evidence/runtime/shared path')
        for binding in retained:
            _definition(binding)  # Same regular-file/raw-hash contract, not another evidence schema.
        if not path.exists():
            return dict(result, status='absent', reason='Owned path already absent; no new reclaimed-byte claim', bytes=0)
        if _node(path) != receipt['node']:
            raise CleanupError('Output identity changed')
        return dict(result, status='eligible', reason='Mapped prerequisites established', bytes=_size(path))
    except (ValueError, OSError, KeyError, TypeError) as error:
        return dict(result, reason=str(error))


def dispose_output(receipt: dict, observation: dict, *, protected: list[str], retained: list[dict],
                   authorized: bool, dispose) -> dict:
    """Recheck then invoke the selected consumer adapter once for an eligible item.

    The adapter owns safe deletion/quarantine mechanics. It returns {'kind':
    'deleted'} or {'kind': 'quarantined', 'path': absolute_path}. Caller records the
    result in existing closeout evidence. Logical bytes are not measured disk
    reclamation; in particular, quarantine reclaims zero bytes.
    """
    plan = assess_output(receipt, observation, protected=protected, retained=retained)
    result = dict(plan, removed_bytes=0, reclaimed_bytes=None)
    if plan['status'] != 'eligible':
        return result
    if authorized is not True:
        return dict(result, status='retained', reason='Disposal authority missing')
    try:
        response = dispose(Path(receipt['path']))
        if os.path.lexists(receipt['path']):
            raise CleanupError('Adapter left the original path; reconcile partial disposal')
        if response == {'kind': 'deleted'}:
            return dict(result, status='deleted', removed_bytes=plan['bytes'],
                        reason='Adapter reports deletion; physical disk reclamation unmeasured')
        if isinstance(response, dict) and set(response) == {'kind', 'path'} and response['kind'] == 'quarantined':
            quarantine = _path(response['path'])
            if _node(quarantine) != receipt['node'] or _size(quarantine) != plan['bytes']:
                raise CleanupError('Quarantine identity/size mismatch')
            return dict(result, status='quarantined', quarantine=str(quarantine), reclaimed_bytes=0,
                        reason='Recoverable disposal; retained bytes remain on disk')
        raise CleanupError('Unknown adapter result; reconcile actual state')
    except Exception as error:
        return dict(result, status='incomplete', removed_bytes=None, reason=str(error))
