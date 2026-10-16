"""Derive accepted proof identities and reconcile consumer-native evidence.

The accepted task owns the entries; preparation/review owns completeness and
semantic adequacy. This module neither invents scenarios nor executes checks.
"""
from __future__ import annotations

import hashlib
import json
import math

from .section_reader import _sections
from .structural import ScanSetup, scan


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def _names(value, label: str, *, nonempty=True):
    if (not isinstance(value, list) or (nonempty and not value)
            or not all(isinstance(item, str) and item.strip() for item in value)
            or len(set(value)) != len(value)):
        raise ValueError(label + ' needs unique explicit names')
    return value


def derive(source: bytes, binding: dict) -> dict:
    """One ri-obligations fence inside Checks, never an independent inventory file."""
    if not isinstance(binding, dict) or set(binding) != {'path', 'sha256', 'phase', 'route'}:
        raise ValueError('Accepted capsule needs path, sha256, phase and route')
    if hashlib.sha256(source).hexdigest() != binding['sha256']:
        raise ValueError('Accepted capsule identity mismatch')
    setup = ScanSetup()
    sections = [item for item in _sections(source, setup) if item['level'] == 2 and item['heading'] == 'Checks']
    if len(sections) != 1:
        raise ValueError('Accepted capsule needs one Checks section')
    section = sections[0]
    _, tree, _, _ = scan('.md', source, setup=setup)
    blocks = []
    def visit(node):
        if node.type == 'fenced_code_block' and section['start'] <= node.start_byte < section['end']:
            info = next((child for child in node.named_children if child.type == 'info_string'), None)
            content = next((child for child in node.named_children if child.type == 'code_fence_content'), None)
            if info and source[info.start_byte:info.end_byte].strip() == b'ri-obligations' and content:
                blocks.append(source[content.start_byte:content.end_byte])
        # Do not mistake a quoted/listed example or a nested fence for task entries.
        elif node.type in ('document', 'section'):
            for child in node.named_children:
                visit(child)
    visit(tree)
    if len(blocks) != 1:
        raise ValueError('Checks needs one authoritative ri-obligations block')
    value = json.loads(blocks[0], object_pairs_hook=unique_object)
    if not isinstance(value, dict) or set(value) != {'phases', 'routes', 'entries'}:
        raise ValueError('Accepted entries need phases, routes and entries')
    phases, routes = _names(value['phases'], 'Phases'), _names(value['routes'], 'Routes')
    if binding['phase'] not in phases or binding['route'] not in routes:
        raise ValueError('Selected phase/route is not accepted')
    entries = value['entries']
    if not isinstance(entries, list) or not 1 <= len(entries) <= 128:
        raise ValueError('Accepted entries must be nonempty and bounded')
    ids = set()
    for entry in entries:
        common = {'id', 'kind', 'outcome', 'due', 'owner', 'routes'}
        proof = {'native_id', 'success', 'artifacts', 'measurements'}
        if not isinstance(entry, dict) or entry.get('kind') not in ('outcome', 'step', 'proof'):
            raise ValueError('Unknown accepted entry kind')
        if set(entry) != common | (proof if entry['kind'] == 'proof' else set()):
            raise ValueError('Unknown or missing accepted entry fields')
        if not all(isinstance(entry[key], str) and entry[key].strip() for key in common - {'routes'}):
            raise ValueError('Accepted identities and owner must be explicit')
        if entry['id'] in ids or entry['due'] not in phases or not set(_names(entry['routes'], 'Entry routes')) <= set(routes):
            raise ValueError('Duplicate identity or unaccepted phase/route')
        ids.add(entry['id'])
        if entry['kind'] == 'proof':
            _names(entry['artifacts'], 'Artifacts', nonempty=False)
            _names(entry['measurements'], 'Measurements', nonempty=False)
            if not isinstance(entry['native_id'], str) or not entry['native_id']:
                raise ValueError('Prescribed native case identity required')
            if type(entry['success']) not in (str, int, float, bool) or (type(entry['success']) is float and not math.isfinite(entry['success'])):
                raise ValueError('Native success must be a finite scalar')
    outcomes = {entry['id']: entry for entry in entries if entry['kind'] == 'outcome'}
    for entry in entries:
        parent = outcomes.get(entry['outcome'])
        if parent is None or (entry['kind'] == 'outcome' and entry['outcome'] != entry['id']) or not set(entry['routes']) <= set(parent['routes']):
            raise ValueError('Entry lost its original outcome/route identity')
    selected = []
    excluded = []
    for entry in entries:
        if binding['route'] not in entry['routes']:
            excluded.append(entry['id'])
            continue
        selected.append(dict(entry, due_now=phases.index(entry['due']) <= phases.index(binding['phase']),
                             definition_sha256=_digest(dict(source_sha256=binding['sha256'], entry=entry))))
    if not selected:
        raise ValueError('Selected route has no accepted obligations')
    result = dict(source=dict(path=binding['path'], sha256=binding['sha256']),
                  phase=binding['phase'], route=binding['route'], entries=selected, excluded=excluded)
    result['required_outcomes'] = {entry['id']: entry['due_now'] for entry in selected}
    result['inventory_sha256'] = _digest(result)
    return result


def bind_native_mapping(inventory: dict, mapping: dict, source: dict) -> dict:
    """Bind native selectors exported by the same consumer runner owner, not worker aliases."""
    if not isinstance(mapping, dict):
        raise ValueError('Authoritative native mapping unavailable')
    for entry in inventory['entries']:
        if entry['kind'] == 'proof' and entry['due_now'] and entry['native_id'] not in mapping:
            raise ValueError('Due native case mapping omitted: ' + entry['native_id'])
    for case, definition in mapping.items():
        if (not isinstance(case, str) or not case or not isinstance(definition, dict)
                or set(definition) != {'fields', 'artifacts', 'measurements'}
                or not isinstance(definition['fields'], dict)
                or set(definition['fields']) != {'case', 'status', 'candidate', 'attempt', 'request_sha256'}
                or not isinstance(definition['artifacts'], dict) or not isinstance(definition['measurements'], dict)):
            raise ValueError('Authoritative native case mapping invalid')
        for category in definition.values():
            for keys in category.values():
                if (not isinstance(keys, list) or not 1 <= len(keys) <= 32
                        or not all((isinstance(key, str) and key) or (type(key) is int and key >= 0) for key in keys)):
                    raise ValueError('Native mapping needs bounded literal key paths')
    for entry in inventory['entries']:
        if entry['kind'] == 'proof' and entry['due_now']:
            definition = mapping[entry['native_id']]
            if (not set(entry['artifacts']) <= set(definition['artifacts'])
                    or not set(entry['measurements']) <= set(definition['measurements'])):
                raise ValueError('Due native artifacts/measurements missing from owning mapping')
    result = dict(inventory, native_mapping=mapping, mapping_source=source)
    result['inventory_sha256'] = _digest({key: value for key, value in result.items() if key != 'inventory_sha256'})
    return result


def _get(value, keys):
    if not isinstance(keys, list) or not 1 <= len(keys) <= 32:
        raise ValueError('Native field needs an explicit bounded key path')
    for key in keys:
        if isinstance(value, dict) and isinstance(key, str):
            value = value[key]
        elif isinstance(value, list) and type(key) is int and key >= 0:
            value = value[key]
        else:
            raise ValueError('Native field path unavailable')
    return value


def reconcile(inventory: dict, facts: dict, expected: dict, *, load_record, verify_reference) -> dict:
    """Reuse original identities and actual native values; do not judge assertion quality."""
    errors, accounted = [], []
    if not isinstance(facts, dict) or facts.get('inventory_sha256') != inventory['inventory_sha256']:
        return dict(ready=False, errors=['Accepted inventory binding mismatch'], entries=[])
    rows = facts.get('outcomes')
    if not isinstance(rows, list):
        return dict(ready=False, errors=['Outcome rows unavailable'], entries=[])
    mapped = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] in mapped:
            errors.append('Missing or duplicate original identity')
        else:
            mapped[row['id']] = row
    if set(mapped) != set(inventory['required_outcomes']):
        errors.append('Original outcome/step/proof identity coverage mismatch')
    for entry in inventory['entries']:
        label = entry['id']
        try:
            row = mapped.get(label)
            if not isinstance(row, dict) or row.get('definition_sha256') != entry['definition_sha256']:
                raise ValueError('Original definition binding mismatch')
            if row.get('status') == 'pending' and not entry['due_now']:
                if row.get('next_owner') != entry['owner']:
                    raise ValueError('Future obligation lost accepted next owner')
                accounted.append(dict(id=label, status='pending', next_owner=entry['owner']))
                continue
            if row.get('status') != 'passed':
                raise ValueError('Due or claimed-complete obligation did not pass')
            if entry['kind'] != 'proof':
                refs = row.get('evidence')
                if not isinstance(refs, list) or not 1 <= len(refs) <= 128 or not isinstance(row.get('basis'), str) or not row['basis'].strip():
                    raise ValueError('Completed step/outcome needs retained evidence and concise basis')
                accounted.append(dict(id=label, status='passed', evidence=[verify_reference(ref) for ref in refs]))
                continue
            native = row.get('native')
            if not isinstance(native, dict) or set(native) != {'record'}:
                raise ValueError('Native proof binding unavailable')
            record = load_record(native['record'])
            mapping = inventory.get('native_mapping', {}).get(entry['native_id'])
            if not isinstance(mapping, dict):
                raise ValueError('Native result identity mappings unavailable')
            fields = mapping['fields']
            for key in ('candidate', 'attempt', 'request_sha256'):
                if _get(record, fields[key]) != expected[key]:
                    raise ValueError('Stale native ' + key)
            if _get(record, fields['case']) != entry['native_id']:
                raise ValueError('Prescribed native case substituted')
            status = _get(record, fields['status'])
            if type(status) is not type(entry['success']) or status != entry['success']:
                raise ValueError('Native case did not pass')
            artifacts, measurements = {}, {}
            if not set(entry['artifacts']) <= set(mapping['artifacts']):
                raise ValueError('Required artifact coverage mismatch')
            if not set(entry['measurements']) <= set(mapping['measurements']):
                raise ValueError('Required measurement coverage mismatch')
            for name in entry['artifacts']:
                artifacts[name] = verify_reference(_get(record, mapping['artifacts'][name]))
            for name in entry['measurements']:
                try:
                    value = _get(record, mapping['measurements'][name])
                except (KeyError, IndexError, ValueError, TypeError) as error:
                    raise ValueError('Required measurement unavailable: ' + name) from error
                if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
                    raise ValueError('Required measurement unavailable: ' + name)
                measurements[name] = value
            accounted.append(dict(id=label, status='passed', native=verify_reference(native['record']),
                                  artifacts=artifacts, measurements=measurements))
        except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
            errors.append(label + ': ' + str(error))
    return dict(ready=not errors, errors=errors, inventory_sha256=inventory['inventory_sha256'],
                source=inventory['source'], phase=inventory['phase'], route=inventory['route'], entries=accounted)
