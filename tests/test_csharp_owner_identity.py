"""Distinct C# source owners must survive unrelated edits and reordering."""

import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree


class CSharpOwnerIdentityTests(unittest.TestCase):
    def test_interface_accessors_and_generic_type_owners_remain_distinct(self):
        fixtures = {
            'property': (
                b'interface I { int P { get; } } interface J { int P { get; } } ',
                b'class C : I, J { int I.P { get { return 1; } } '
                b'int J.P { get { return 2; } } }',
                [b'get { return 1; }', b'get { return 2; }'],
            ),
            'arrow_property': (
                b'interface I { int P { get; } } interface J { int P { get; } } ',
                b'class C : I, J { int I.P => 1; int J.P => 2; }',
                [b'int I.P => 1;', b'int J.P => 2;'],
            ),
            'indexer': (
                b'interface I { int this[int x] { get; } } '
                b'interface J { int this[int x] { get; } } ',
                b'class C : I, J { int I.this[int x] { get { return 1; } } '
                b'int J.this[int x] { get { return 2; } } }',
                [b'get { return 1; }', b'get { return 2; }'],
            ),
            'event': (
                b'interface I { event System.Action E; } '
                b'interface J { event System.Action E; } ',
                b'class C : I, J { event System.Action I.E { add {} remove {} } '
                b'event System.Action J.E { add {} remove {} } }',
                [b'add {}', b'remove {}', b'add {}', b'remove {}'],
            ),
            'get_set_helpers': (
                b'',
                b'class C { int P { get { int Local(){return 1;} return Local(); } '
                b'set { int Local(){return 2;} _ = Local(); } } }',
                [b'get { int Local(){return 1;} return Local(); }',
                 b'int Local(){return 1;}',
                 b'set { int Local(){return 2;} _ = Local(); }',
                 b'int Local(){return 2;}'],
            ),
            'operator_helpers': (
                b'',
                b'class C { public static C operator +(C a,C b) { C Local()=>a; return Local(); } '
                b'public static C operator -(C a,C b) { C Local()=>b; return Local(); } }',
                [b'public static C operator +(C a,C b) { C Local()=>a; return Local(); }',
                 b'C Local()=>a;',
                 b'public static C operator -(C a,C b) { C Local()=>b; return Local(); }',
                 b'C Local()=>b;'],
            ),
            'generic_class': (
                b'',
                b'class C { int F() {return 1;} } class C<T> {int F() {return 2;} } '
                b'class C<T,U> {int F() {return 3;} }',
                [b'int F() {return 1;}', b'int F() {return 2;}', b'int F() {return 3;}'],
            ),
            'nested_helpers': (
                b'interface I { int P { get; } } interface J { int P { get; } } ',
                b'class C : I, J { int I.P { get { int Local() => 1; return Local(); } } '
                b'int J.P { get { int Local() => 2; return Local(); } } }',
                [b'get { int Local() => 1; return Local(); }',
                 b'int Local() => 1;',
                 b'get { int Local() => 2; return Local(); }',
                 b'int Local() => 2;'],
            ),
        }
        for label, (prefix, body, slices) in fixtures.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                left, right = Path(raw) / 'left', Path(raw) / 'right'
                left.mkdir()
                right.mkdir()
                source = prefix + body
                (left / 'C.cs').write_bytes(source)
                (right / 'C.cs').write_bytes(b'// unrelated\n' + source)
                before, after = inventory_tree(left, stable=True), inventory_tree(right, stable=True)
                self.assertEqual(before['status'], 'complete')
                entries = before['files'][0]['declarations']
                self.assertEqual([source[e['byte_range']['start']:e['byte_range']['end']]
                                  for e in entries], slices)
                self.assertFalse(any(e.get('identity_ambiguous') for e in entries))
                delta = compare_inventories(before, after)
                self.assertEqual(delta['status'], 'comparable_candidate_delta')
                self.assertEqual(tuple(len(delta['declaration_changes'][k])
                                       for k in ('added', 'removed', 'modified', 'unchanged')),
                                 (0, 0, 0, len(slices)))

    def test_generic_owner_parameter_names_and_trivia_are_not_identity(self):
        left = b'class C<T, U> { int F() {return 1;} }'
        right = b'class C<Value, /* note */ Other> { int F() {return 1;} }'
        with tempfile.TemporaryDirectory() as raw:
            before, after = Path(raw) / 'left', Path(raw) / 'right'
            before.mkdir()
            after.mkdir()
            (before / 'C.cs').write_bytes(left)
            (after / 'C.cs').write_bytes(right)
            delta = compare_inventories(inventory_tree(before, stable=True),
                                        inventory_tree(after, stable=True))
            self.assertEqual(delta['status'], 'comparable_candidate_delta')
            self.assertEqual(tuple(len(delta['declaration_changes'][k])
                                   for k in ('added', 'removed', 'modified', 'unchanged')),
                             (0, 0, 0, 1))


if __name__ == '__main__':
    unittest.main()
