"""Presentation limits must not hide a real candidate edit in any grammar."""

import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compact_delta, compare_inventories, inventory_tree
from repository_intelligence.locator import query_path


class ProjectionBoundaryTests(unittest.TestCase):
    def test_change_beyond_structural_details_reaches_full_and_compact_delta(self):
        fixtures = {
            '.py': ('', '', 'def target_{i}(): return {value}\n'),
            '.rs': ('', '', 'fn target_{i}() -> i32 {{ {value} }}\n'),
            '.js': ('', '', 'function target_{i}() {{ return {value}; }}\n'),
            '.ts': ('', '', 'function target_{i}(): number {{ return {value}; }}\n'),
            '.tsx': ('', '', 'function target_{i}(): number {{ return {value}; }}\n'),
            '.java': ('class C {\n', '}\n', 'int target_{i}() {{ return {value}; }}\n'),
            '.go': ('package fixture\n', '', 'func target_{i}() int {{ return {value} }}\n'),
            '.cs': ('class C {\n', '}\n', 'int target_{i}() {{ return {value}; }}\n'),
            '.c': ('', '', 'int target_{i}(void) {{ return {value}; }}\n'),
            '.cpp': ('', '', 'int target_{i}() {{ return {value}; }}\n'),
        }
        for suffix, (opening, closing, template) in fixtures.items():
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as raw:
                planning, candidate = Path(raw) / 'planning', Path(raw) / 'candidate'
                planning.mkdir()
                candidate.mkdir()
                filename = 'source' + suffix
                before = (opening + ''.join(template.format(i=i, value=i)
                                            for i in range(102)) + closing).encode()
                expected = template.format(i=101, value=999).encode().rstrip(b'\n')
                after = before.replace(template.format(i=101, value=101).encode(),
                                       template.format(i=101, value=999).encode())
                (planning / filename).write_bytes(before)
                (candidate / filename).write_bytes(after)
                left = inventory_tree(planning, stable=True)
                right = inventory_tree(candidate, stable=True)
                self.assertEqual([entry['name'] for entry in right['files'][0]['declarations']],
                                 [f'target_{i}' for i in range(102)])
                self.assertEqual(len(right['files'][0]['structural']['declarations']), 100)
                self.assertTrue(right['files'][0]['structural']['details_truncated'])
                delta = compare_inventories(left, right)
                self.assertEqual(delta['status'], 'comparable_candidate_delta')
                changes = delta['declaration_changes']
                self.assertEqual(tuple(len(changes[k]) for k in
                                       ('added', 'removed', 'modified', 'unchanged')),
                                 (0, 0, 1, 101))
                modified = changes['modified'][0]['candidate']
                self.assertEqual(modified['name'], 'target_101')
                span = modified['byte_range']
                self.assertEqual(after[span['start']:span['end']], expected)
                compact = compact_delta(delta)
                self.assertEqual(compact['declaration_counts'],
                                 {'added': 0, 'removed': 0, 'modified': 1, 'unchanged': 101})
                self.assertEqual(compact['declaration_changes']['modified'][0]['declaration_id'],
                                 modified['declaration_id'])
                # A one-item navigation view still reports the full match count.
                query = query_path(candidate, 'target', limit=1)
                self.assertEqual(query['total_matches'], 102)
                self.assertEqual([entry['name'] for entry in query['matches']], ['target_0'])


if __name__ == '__main__':
    unittest.main()
