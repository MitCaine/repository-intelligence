"""Lossless, content-addressed review transport; no acquisition or approval policy."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json

from .inventory import compare_inventories, compact_delta

SCHEMA_VERSION = 1
MAX_BYTES = 64_000_000
MAX_DECODED_BYTES = 128_000_000
MAX_DEPTH = 80
INDEX_VERSION = 2


class _ReferencePaths:
    """Reject component-prefix overlaps in work proportional to path length."""
    def __init__(self):
        self.root = {}
        self.end = object()

    def add(self, path):
        node = self.root
        for segment in path:
            if self.end in node:
                raise ValueError('duplicate or overlapping evidence paths')
            node = node.setdefault(segment, {})
        if node:
            raise ValueError('duplicate or overlapping evidence paths')
        node[self.end] = True


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def build_review_bundle(planning, candidate):
    """Factor repeated objects, retaining exact canonical JSON data and statuses."""
    documents = {'planning': planning, 'candidate': candidate,
                 'comparison': compare_inventories(planning, candidate)}
    if sum(len(canonical(v)) for v in documents.values()) > MAX_DECODED_BYTES:
        raise ValueError('decoded evidence exceeds budget')
    counts, originals = Counter(), {}

    def collect(value, depth=0):
        if depth > MAX_DEPTH:
            raise ValueError('evidence nesting exceeds budget')
        if isinstance(value, dict):
            raw = canonical(value)
            if len(raw) >= 256:
                key = hashlib.sha256(raw).hexdigest()
                counts[key] += 1
                originals[key] = value
            for child in value.values():
                collect(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                collect(child, depth + 1)

    for value in documents.values():
        collect(value)
    shared = {key for key, count in counts.items() if count > 1}

    def encode(value, own=None):
        references = []

        def walk(item, path):
            if isinstance(item, dict):
                key = digest(item)
                if key in shared and not (not path and key == own):
                    references.append({'path': path, 'record': key})
                    return None
                return {k: walk(v, path + [k]) for k, v in item.items()}
            if isinstance(item, list):
                return [walk(v, path + [i]) for i, v in enumerate(item)]
            return deepcopy(item)
        return {'value': walk(value, []), 'references': references}

    records = {key: encode(originals[key], key) for key in sorted(shared)}
    encoded = {name: {'sha256': digest(value), **encode(value)}
               for name, value in documents.items()}
    # Nested records referenced only inside an externalized parent remain reachable.
    bundle = {'review_bundle_schema_version': SCHEMA_VERSION, 'documents': encoded,
              'records': records}
    validate_review_bundle(bundle)
    _check_depth(bundle)
    if len(canonical(bundle)) > MAX_BYTES:
        raise ValueError('stored evidence exceeds budget')
    return bundle


def _check_depth(value, depth=0):
    if depth > MAX_DEPTH:
        raise ValueError('evidence nesting exceeds budget')
    if isinstance(value, dict):
        for child in value.values():
            _check_depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_depth(child, depth + 1)


def validate_review_bundle(bundle):
    """Authenticate every reference/hash and reconstruct all complete documents."""
    _check_depth(bundle)
    if len(canonical(bundle)) > MAX_BYTES:
        raise ValueError('stored evidence exceeds budget')
    if (not isinstance(bundle, dict) or set(bundle) != {'review_bundle_schema_version', 'documents', 'records'} or
            type(bundle['review_bundle_schema_version']) is not int or
            bundle['review_bundle_schema_version'] != SCHEMA_VERSION):
        raise ValueError('unsupported review bundle')
    records, documents = bundle['records'], bundle['documents']
    if not isinstance(records, dict) or not isinstance(documents, dict) or set(documents) != {
            'planning', 'candidate', 'comparison'}:
        raise ValueError('incomplete evidence documents')
    memo, active, used = {}, set(), set()
    decoded_bytes = 0

    def account(value):
        nonlocal decoded_bytes
        decoded_bytes += len(canonical(value))
        if decoded_bytes > MAX_DECODED_BYTES:
            raise ValueError('decoded evidence exceeds budget')

    def resolve(key, depth):
        if not isinstance(key, str) or key not in records:
            raise ValueError('missing evidence record')
        if key in active or depth > MAX_DEPTH:
            raise ValueError('cyclic or excessive evidence references')
        used.add(key)
        if key not in memo:
            active.add(key)
            value = decode(records[key], depth + 1)
            if digest(value) != key:
                raise ValueError('record digest mismatch')
            memo[key] = value
            active.remove(key)
        account(memo[key])
        return deepcopy(memo[key])

    def decode(entry, depth=0):
        if (not isinstance(entry, dict) or set(entry) not in ({'value', 'references'}, {'value', 'references', 'sha256'})
                or not isinstance(entry['references'], list)):
            raise ValueError('invalid encoded evidence')
        value, paths = deepcopy(entry['value']), _ReferencePaths()
        for reference in entry['references']:
            if not isinstance(reference, dict) or set(reference) != {'path', 'record'}:
                raise ValueError('invalid evidence reference')
            path = reference['path']
            if (not isinstance(path, list) or len(path) > MAX_DEPTH or
                    any(type(p) not in (str, int) or (type(p) is int and p < 0) for p in path)):
                raise ValueError('invalid evidence path')
            paths.add(path)
            parent = value
            try:
                for segment in path[:-1]:
                    if not ((isinstance(parent, dict) and type(segment) is str) or
                            (isinstance(parent, list) and type(segment) is int)):
                        raise ValueError('invalid evidence path type')
                    parent = parent[segment]
                if path:
                    segment = path[-1]
                    if not ((isinstance(parent, dict) and type(segment) is str) or
                            (isinstance(parent, list) and type(segment) is int)):
                        raise ValueError('invalid evidence path type')
                    if parent[segment] is not None:
                        raise ValueError('reference overwrites evidence')
                    parent[segment] = resolve(reference['record'], depth + 1)
                else:
                    if value is not None:
                        raise ValueError('reference overwrites document')
                    value = resolve(reference['record'], depth + 1)
            except (KeyError, IndexError, TypeError) as error:
                raise ValueError('invalid evidence path') from error
        _check_depth(value)  # References can expand a shallow envelope past the bound.
        return value

    result = {}
    for name, entry in documents.items():
        if not isinstance(entry, dict) or set(entry) != {'sha256', 'value', 'references'}:
            raise ValueError('invalid document envelope')
        value = decode(entry)
        if digest(value) != entry['sha256']:
            raise ValueError('document digest mismatch')
        account(value)
        result[name] = value
    if used != set(records):
        raise ValueError('unreferenced evidence records')
    if canonical(result['comparison']) != canonical(compare_inventories(result['planning'], result['candidate'])):
        raise ValueError('comparison does not match inventories')
    return result


def review_index(bundle, *, limit=20):
    """Small navigation view; not an omission of retained evidence or a verdict."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('index limit must be between 1 and 100')
    documents = validate_review_bundle(bundle)
    delta = compact_delta(documents['comparison'])
    def sample(rows, document, path):
        return {'count': len(rows), 'sample': rows[:limit],
                'truncated': len(rows) > limit,
                'document': document, 'path': path}

    # Full coverage belongs to the retained inventory, not repeated index lists.
    for side in ('planning', 'candidate'):
        inventory = documents[side]
        summary = delta[side]
        projected = {key: summary[key] for key in (
            'root', 'status', 'inventory_schema_version', 'navigation_schema_version',
            'mapping_contract', 'materialization', 'digest')}
        projected['retained_inventory_sha256'] = digest(inventory)
        for field in ('incomplete_reasons', 'failures', 'observed_exclusions',
                      'observed_unsupported_paths'):
            projected[field] = sample(inventory.get(field, []), side, [field])
        for field in ('scope', 'parser_contract'):
            projected[field] = {'document': side, 'path': [field]}
        delta[side] = projected
    delta['mismatches'] = sample(delta['mismatches'], 'comparison', ['mismatches'])
    for field in ('file_changes', 'declaration_changes'):
        if delta[field] is not None:
            delta[field] = {kind: {'count': len(rows), 'sample': rows[:limit],
                                  'truncated': len(rows) > limit}
                            for kind, rows in delta[field].items()}
    delta.pop('file_metadata', None)
    return {'review_bundle_schema_version': SCHEMA_VERSION,
            'review_index_version': INDEX_VERSION,
            'bundle_sha256': digest(bundle),
            'documents': {name: digest(value) for name, value in documents.items()},
            'record_count': len(bundle['records']), 'delta': delta}


def read_record(bundle, record_id):
    """Select one authenticated repeated record without model-driven reconstruction."""
    documents = validate_review_bundle(bundle)
    if record_id not in bundle['records']:
        raise ValueError('unknown evidence record')
    # Resolve from the complete authenticated documents using its canonical hash.
    def find(value):
        if isinstance(value, dict):
            if digest(value) == record_id:
                return value
            for child in value.values():
                result = find(child)
                if result is not None:
                    return result
        elif isinstance(value, list):
            for child in value:
                result = find(child)
                if result is not None:
                    return result
        return None
    for value in documents.values():
        result = find(value)
        if result is not None:
            return deepcopy(result)
    raise ValueError('unreachable evidence record')


def read_document_path(bundle, document, path):
    """Selective data access after whole-bundle mechanical verification."""
    documents = validate_review_bundle(bundle)
    if document not in documents:
        raise ValueError('unknown evidence document')
    value = documents[document]
    for segment in path:
        if not ((isinstance(value, dict) and type(segment) is str) or
                (isinstance(value, list) and type(segment) is int and segment >= 0)):
            raise ValueError('invalid selection path')
        try:
            value = value[segment]
        except (KeyError, IndexError) as error:
            raise ValueError('missing selection path') from error
    return deepcopy(value)


def main(argv=None):
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('verify', 'index', 'read'))
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--document', choices=('planning', 'candidate', 'comparison'))
    parser.add_argument('--path', default='[]', help='JSON array of object keys/list indices')
    args = parser.parse_args(argv)
    if args.bundle.stat().st_size > MAX_BYTES:
        raise ValueError('stored evidence exceeds budget')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate evidence JSON key')
            value[key] = item
        return value
    bundle = json.loads(args.bundle.read_text(encoding='utf-8'), object_pairs_hook=unique)
    if args.command == 'verify':
        documents = validate_review_bundle(bundle)
        result = {'verified': True, 'bundle_sha256': digest(bundle),
                  'status': documents['comparison']['status']}
    elif args.command == 'index':
        result = review_index(bundle)
    else:
        if args.document is None:
            parser.error('read requires --document')
        path = json.loads(args.path)
        if not isinstance(path, list):
            parser.error('--path must be a JSON array')
        result = read_document_path(bundle, args.document, path)
    print(canonical(result).decode('utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
