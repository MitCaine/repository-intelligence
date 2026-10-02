"""Lossless transport, independent source expectations and hostile reference faults."""
from copy import deepcopy
from pathlib import Path
import tempfile
import contextlib
import io
import json
import unittest
from unittest import mock

from repository_intelligence.inventory import inventory_tree, compare_inventories
from repository_intelligence import review_bundle as rb


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.p, self.c = root/'p', root/'c'
        self.p.mkdir(); self.c.mkdir()
        before = ''.join(f'def test_{i}(value):\n    return value + {i}\n\n' for i in range(60))
        after = before.replace('return value + 5\n', 'return value - 5\n')
        (self.p/'tests.py').write_text(before)
        (self.c/'tests.py').write_text(after)
        self.planning = inventory_tree(self.p, stable=True)
        self.candidate = inventory_tree(self.c, stable=True)
        self.bundle = rb.build_review_bundle(self.planning, self.candidate)

    def test_lossless_and_smaller(self):
        decoded = rb.validate_review_bundle(self.bundle)
        self.assertEqual(decoded, {'planning': self.planning, 'candidate': self.candidate,
                                   'comparison': compare_inventories(self.planning, self.candidate)})
        self.assertLess(len(rb.canonical(self.bundle)), len(rb.canonical(decoded)))
        selected = rb.read_document_path(self.bundle, 'candidate', ['files',0,'declarations',5])
        self.assertEqual(selected['name'], 'test_5')
        self.assertEqual((self.c/'tests.py').read_bytes()[slice(selected['byte_range']['start'], selected['byte_range']['end'])].strip(),
                         b'def test_5(value):\n    return value - 5')

    def test_canonical_hash_preserves_unicode_numbers_and_array_order(self):
        self.assertEqual(rb.digest({'b': 2, 'a': 'Résumé'}), rb.digest({'a': 'Résumé', 'b': 2}))
        self.assertNotEqual(rb.digest(['a', 'b']), rb.digest(['b', 'a']))
        self.assertNotEqual(rb.digest({'value': 1}), rb.digest({'value': 1.0}))
        self.assertNotEqual(rb.digest({'value': 'é'}), rb.digest({'value': 'e\u0301'}))
        with self.assertRaises(ValueError):
            rb.canonical({'value': float('nan')})

    def test_large_indivisible_file_retained_bundle_survives_scratch_removal(self):
        source = ''.join(f'def unit_{i}(value):\n    """' + 'context ' * 40 +
                         f'"""\n    return value + {i}\n\n' for i in range(320))
        self.assertGreater(len(source.encode()), 100_000)
        (self.p / 'tests.py').write_text(source)
        (self.c / 'tests.py').write_text(source.replace('return value + 5\n', 'return value - 5\n'))
        planning = inventory_tree(self.p, stable=True)
        candidate = inventory_tree(self.c, stable=True)
        bundle = rb.build_review_bundle(planning, candidate)
        path = Path(self.temp.name) / 'retained.json'
        path.write_bytes(rb.canonical(bundle))
        import shutil
        shutil.rmtree(self.p); shutil.rmtree(self.c)
        restored = rb.validate_review_bundle(json.loads(path.read_bytes()))
        self.assertEqual(restored['planning'], planning)
        self.assertEqual(restored['candidate'], candidate)
        self.assertEqual([v['candidate']['name'] for v in restored['comparison']['declaration_changes']['modified']],
                         ['unit_5'])
        self.assertLess(len(path.read_bytes()), len(rb.canonical(restored)))
        # This retains structural facts. Raw source and consumer receipts need their own route.

    def test_deterministic(self):
        self.assertEqual(rb.canonical(self.bundle), rb.canonical(rb.build_review_bundle(self.planning, self.candidate)))

    def test_reference_prefixes_in_both_orders_and_typed_siblings(self):
        for first, second in (([], ['a']), (['a'], []), (['a'], ['a']),
                              (['a'], ['a', 0]), (['a', 0], ['a'])):
            with self.subTest(first=first, second=second):
                paths = rb._ReferencePaths()
                paths.add(first)
                with self.assertRaisesRegex(ValueError, 'overlapping'):
                    paths.add(second)
        paths = rb._ReferencePaths()
        for path in (['a', 0], ['a', '0'], ['ab'], ['a', 1]):
            paths.add(path)

    def test_reference_lookup_work_scales_with_components(self):
        for count in (1000, 4000):
            visits = []
            class CountingNodes(dict):
                def setdefault(self, key, default):
                    visits.append(key)
                    return super().setdefault(key, CountingNodes())
            paths = rb._ReferencePaths()
            paths.root = CountingNodes()
            for i in range(count):
                paths.add(['files', i, 'metadata'])
            self.assertEqual(len(visits), 3 * count)

    def test_index_bounds_complete_unsupported_inventory(self):
        for i in range(1000):
            for root in (self.p, self.c):
                (root / f'unsupported-{i}.h').write_text('unmapped')
        planning = inventory_tree(self.p, stable=True)
        candidate = inventory_tree(self.c, stable=True)
        bundle = rb.build_review_bundle(planning, candidate)
        index = rb.review_index(bundle, limit=1)
        self.assertEqual(index['review_index_version'], 2)
        self.assertLess(len(rb.canonical(index)), 20_000)
        for side in ('planning', 'candidate'):
            view = index['delta'][side]['observed_unsupported_paths']
            self.assertEqual(view['count'], 1000)
            self.assertEqual(len(view['sample']), 1)
            self.assertTrue(view['truncated'])
            rows = rb.read_document_path(bundle, view['document'], view['path'])
            self.assertEqual(len(rows), 1000)
            self.assertEqual(index['delta'][side]['retained_inventory_sha256'],
                             rb.digest(rb.read_document_path(bundle, side, [])))
        (self.c / 'unsupported-0.h').unlink()
        (self.c / 'new.h').write_text('unmapped')
        changed = inventory_tree(self.c, stable=True)
        self.assertEqual(candidate['inventory_digest'], changed['inventory_digest'])
        changed_index = rb.review_index(rb.build_review_bundle(planning, changed), limit=1)
        self.assertNotEqual(index['delta']['candidate']['retained_inventory_sha256'],
                            changed_index['delta']['candidate']['retained_inventory_sha256'])
        # Source contents at an unchanged unsupported path are outside this inventory.
        (self.c / 'new.h').write_text('different unmapped content')
        self.assertEqual(changed, inventory_tree(self.c, stable=True))
        altered = deepcopy(bundle)
        rows_key = rb.digest(candidate['observed_unsupported_paths'])
        altered['records'][rows_key]['value'][0]['reason'] = 'tampered'
        with self.assertRaises(ValueError):
            rb.validate_review_bundle(altered)

    def test_repeated_arrays_are_factored_and_selectable(self):
        planning = deepcopy(self.planning)
        candidate = deepcopy(self.candidate)
        rows = [{'path': f'unsupported-{i}-é.h', 'reason': 'no_language_adapter_selected'}
                for i in range(1000)]
        for inventory in (planning, candidate):
            inventory['observed_unsupported_paths'] = deepcopy(rows)
        bundle = rb.build_review_bundle(planning, candidate)
        key = rb.digest(rows)
        self.assertIn(key, bundle['records'])
        self.assertIsInstance(bundle['records'][key]['value'], list)
        decoded = rb.validate_review_bundle(bundle)
        self.assertEqual(decoded['planning'], planning)
        self.assertEqual(decoded['candidate'], candidate)
        self.assertEqual(rb.read_record(bundle, key), rows)
        selected = rb.read_record(bundle, key)
        selected[0]['reason'] = 'changed by caller'
        self.assertEqual(rb.read_record(bundle, key), rows)
        self.assertEqual(rb.read_document_path(bundle, 'candidate',
            ['observed_unsupported_paths', 5]), rows[5])
        self.assertLess(len(rb.canonical(bundle)), len(rb.canonical(decoded)) * .6)
        self.assertEqual(rb.canonical(bundle), rb.canonical(rb.build_review_bundle(planning, candidate)))
        for fault in ('missing', 'tamper'):
            altered = deepcopy(bundle)
            if fault == 'missing': del altered['records'][key]
            else: altered['records'][key]['value'][0]['path'] = 'different.h'
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                rb.validate_review_bundle(altered)

    def test_all_accepted_record_types_have_selective_reads(self):
        for value in ([], ['value'], 'text', None, False, 0):
            planning = deepcopy(self.planning)
            planning['selected_record'] = value
            documents = {'planning': planning, 'candidate': self.candidate,
                'comparison': compare_inventories(planning, self.candidate)}
            key = rb.digest(value)
            bundle = {'review_bundle_schema_version': 1,
                'records': {key: {'value': value, 'references': []}},
                'documents': {name: {'value': deepcopy(document), 'references': [],
                    'sha256': rb.digest(document)} for name, document in documents.items()}}
            bundle['documents']['planning']['value']['selected_record'] = None
            bundle['documents']['planning']['references'] = [
                {'path': ['selected_record'], 'record': key}]
            with self.subTest(value=value):
                self.assertEqual(rb.canonical(rb.read_record(bundle, key)), rb.canonical(value))

    def test_index_bounds_failure_and_mismatch_metadata(self):
        candidate = deepcopy(self.candidate)
        candidate['status'] = 'incomplete'
        candidate['failures'] = [{'path': f'p{i}', 'error': 'fixture'} for i in range(1000)]
        candidate['incomplete_reasons'] = ['file_or_scan_failure']
        index = rb.review_index(rb.build_review_bundle(self.planning, candidate), limit=1)
        self.assertEqual(index['delta']['status'], 'incomplete')
        self.assertEqual(index['delta']['candidate']['failures']['count'], 1000)
        self.assertEqual(len(index['delta']['candidate']['failures']['sample']), 1)
        incompatible = deepcopy(self.candidate)
        incompatible['files'] = incompatible['files'] * 1000
        index = rb.review_index(rb.build_review_bundle(self.planning, incompatible), limit=1)
        self.assertEqual(index['delta']['status'], 'incompatible')
        self.assertTrue(index['delta']['mismatches']['truncated'])

    def test_missing_extra_and_tampered_record(self):
        for fault in ('missing','extra','tamper'):
            value = deepcopy(self.bundle)
            key = next(iter(value['records']))
            if fault == 'missing': del value['records'][key]
            elif fault == 'extra': value['records']['0'*64] = deepcopy(value['records'][key])
            else: value['records'][key]['value'] = {'tampered': True}
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                rb.validate_review_bundle(value)

    def test_cycle_and_duplicate_paths(self):
        value = deepcopy(self.bundle)
        key = next(iter(value['records']))
        value['records'][key] = {'value':None,'references':[{'path':[],'record':key}]}
        with self.assertRaises(ValueError): rb.validate_review_bundle(value)
        value = deepcopy(self.bundle)
        entry = next(e for e in value['documents'].values() if e['references'])
        entry['references'].append(deepcopy(entry['references'][0]))
        with self.assertRaises(ValueError): rb.validate_review_bundle(value)

    def test_incomplete_status_retained(self):
        incomplete = deepcopy(self.candidate)
        incomplete['status'] = 'incomplete'
        incomplete['incomplete_reasons'] = ['fixture failure']
        result = rb.validate_review_bundle(rb.build_review_bundle(self.planning, incomplete))
        self.assertEqual(result['candidate']['status'], 'incomplete')
        self.assertNotEqual(result['comparison']['status'], 'comparable_candidate_delta')

    def test_limits_and_unknown_selection(self):
        with mock.patch.object(rb,'MAX_BYTES',10), self.assertRaises(ValueError):
            rb.validate_review_bundle(self.bundle)
        with mock.patch.object(rb,'MAX_DECODED_BYTES',10), self.assertRaises(ValueError):
            rb.validate_review_bundle(self.bundle)
        with self.assertRaises(ValueError): rb.read_document_path(self.bundle,'candidate',['missing'])
        with self.assertRaises(ValueError): rb.read_record(self.bundle,'0'*64)

    def test_record_selection(self):
        key = next(iter(self.bundle['records']))
        self.assertEqual(rb.digest(rb.read_record(self.bundle,key)), key)
        index = rb.review_index(self.bundle)
        self.assertEqual(index['delta']['status'],'comparable_candidate_delta')
        self.assertEqual(index['bundle_sha256'],rb.digest(self.bundle))

    def test_cli_roundtrip_and_bounded_index(self):
        from repository_intelligence.inventory import main as inventory_main
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(inventory_main(['compare', str(self.p), str(self.c),
                '--assert-stable-materialization', '--review-bundle-json']), 0)
        path = Path(self.temp.name)/'bundle.json'
        path.write_text(output.getvalue())
        for command in ('verify', 'index', 'read'):
            output = io.StringIO()
            args = [command, str(path)]
            if command == 'read': args += ['--document', 'candidate', '--path', '["files",0,"declarations",5,"name"]']
            with contextlib.redirect_stdout(output): self.assertEqual(rb.main(args), 0)
            result = json.loads(output.getvalue())
            if command == 'read': self.assertEqual(result, 'test_5')
        changed = deepcopy(self.candidate)
        changed['inventory_schema_version'] = -1
        decoded = rb.validate_review_bundle(rb.build_review_bundle(self.planning, changed))
        self.assertEqual(decoded['comparison']['status'], 'incompatible')
        index = rb.review_index(self.bundle, limit=1)
        self.assertNotIn('file_metadata', index['delta'])
        self.assertNotIn('record_ids', index)
        for groups in (index['delta']['file_changes'], index['delta']['declaration_changes']):
            for entry in groups.values(): self.assertLessEqual(len(entry['sample']), 1)

    def test_bundle_cli_constructs_and_independently_compares_only_twice(self):
        from repository_intelligence import inventory
        for variant, exit_code in (('complete', 0), ('incomplete', 2), ('incompatible', 3)):
            candidate = deepcopy(self.candidate)
            if variant == 'incomplete': candidate['status'] = 'incomplete'
            if variant == 'incompatible': candidate['inventory_schema_version'] = -1
            with self.subTest(variant=variant), \
                 mock.patch.object(inventory, 'inventory_tree', side_effect=[self.planning, candidate]), \
                 mock.patch.object(inventory, 'compare_inventories', wraps=inventory.compare_inventories) as extra, \
                 mock.patch.object(rb, 'compare_inventories', wraps=rb.compare_inventories) as required:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(inventory.main(['compare', str(self.p), str(self.c),
                        '--assert-stable-materialization', '--review-bundle-json']), exit_code)
                self.assertEqual(extra.call_count, 0)
                self.assertEqual(required.call_count, 2)
                bundle = json.loads(output.getvalue())
            self.assertEqual(rb.validate_review_bundle(bundle)['candidate'], candidate)

    def test_recomputed_comparison_uses_exact_json_types(self):
        documents = rb.validate_review_bundle(self.bundle)
        plain = {'review_bundle_schema_version': 1, 'records': {}, 'documents': {
            name: {'value': value, 'references': [], 'sha256': rb.digest(value)}
            for name, value in documents.items()}}
        self.assertEqual(rb.validate_review_bundle(plain), documents)
        def scalars(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield from scalars(child, (*path, key))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from scalars(child, (*path, index))
            elif type(value) is int:
                yield path, value
        selected = {}
        for path, original in scalars(documents['comparison']):
            category = original if original in (0, 1) else 'other_integer'
            selected.setdefault(category, (path, original))
        self.assertIn(0, selected)
        for path, original in selected.values():
            for substitute in ([float(original), bool(original)] if original in (0, 1) else [float(original)]):
                with self.subTest(path=path, substitute=substitute):
                    altered = deepcopy(plain)
                    envelope = altered['documents']['comparison']
                    parent = envelope['value']
                    for segment in path[:-1]:
                        parent = parent[segment]
                    parent[path[-1]] = substitute
                    envelope['sha256'] = rb.digest(envelope['value'])
                    with self.assertRaisesRegex(ValueError, 'comparison does not match'):
                        rb.validate_review_bundle(altered)
                    # Actual CLI paths must reject rather than expose the substituted value.
                    bundle_path = Path(self.temp.name) / 'altered.json'
                    bundle_path.write_bytes(rb.canonical(altered))
                    for command in ('verify', 'read'):
                        arguments = [command, str(bundle_path)]
                        if command == 'read':
                            arguments += ['--document', 'comparison']
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output), self.assertRaises(ValueError):
                            rb.main(arguments)
                        self.assertEqual(output.getvalue(), '')

    def test_expanded_depth_is_bounded_even_with_shallow_reference_envelope(self):
        def specimen(depth):
            tail = 'leaf'
            for _ in range(depth - 60):
                tail = {'child': tail}
            placeholder = None
            for _ in range(60):
                placeholder = {'child': placeholder}
            planning = deepcopy(self.planning)
            planning['depth_probe'] = placeholder
            expanded = deepcopy(self.planning)
            full = 'leaf'
            for _ in range(depth):
                full = {'child': full}
            expanded['depth_probe'] = full
            documents = {'planning': expanded, 'candidate': self.candidate,
                         'comparison': compare_inventories(expanded, self.candidate)}
            bundle = {'review_bundle_schema_version': 1, 'records': {
                rb.digest(tail): {'value': tail, 'references': []}}, 'documents': {
                name: {'value': deepcopy(value), 'references': [], 'sha256': rb.digest(value)}
                for name, value in documents.items()}}
            bundle['documents']['planning']['value'] = planning
            bundle['documents']['planning']['references'] = [{
                'path': ['depth_probe'] + ['child'] * 60, 'record': rb.digest(tail)}]
            return bundle, expanded
        valid, expanded = specimen(79)  # Root property adds one level: decoded depth 80.
        self.assertEqual(rb.validate_review_bundle(valid)['planning'], expanded)
        invalid, expanded = specimen(120)
        rb._check_depth(invalid)  # Wire representation is within its separate bound.
        with self.assertRaisesRegex(ValueError, 'nesting exceeds'):
            rb.validate_review_bundle(invalid)
        with self.assertRaisesRegex(ValueError, 'nesting exceeds'):
            rb.build_review_bundle(expanded, self.candidate)
