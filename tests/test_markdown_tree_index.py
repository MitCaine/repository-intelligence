"""Independent Markdown source slices and planning-to-candidate deltas."""

import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import query_path
from repository_intelligence.scan import index_file


class MarkdownTests(unittest.TestCase):
    def test_capsule_sections_front_matter_and_checklist_have_exact_slices(self):
        source = (b"---\nid: N-1\n---\n# Capsule\nIntro\n\n## Acceptance\n"
                  b"- [ ] Implement reader\n- [x] Keep source identity\n\n"
                  b"```md\n# Fake heading\n- [ ] fake task\n```\n\n"
                  b"### Proof\nRun tests\n")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "capsule.md"
            path.write_bytes(source)
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "navigation_only")
            self.assertEqual([(item["declaration_kind"], item["name"])
                              for item in result["functions"]],
                             [("metadata", "front matter"), ("section", "Capsule"),
                              ("section", "Acceptance"),
                              ("checklist_item", "Implement reader"),
                              ("checklist_item", "Keep source identity"),
                              ("section", "Proof")])
            expected = [b"---\nid: N-1\n---\n", b"# Capsule\nIntro\n\n",
                        b"## Acceptance\n- [ ] Implement reader\n"
                        b"- [x] Keep source identity\n\n"
                        b"```md\n# Fake heading\n- [ ] fake task\n```\n\n",
                        b"- [ ] Implement reader\n", b"- [x] Keep source identity\n\n",
                        b"### Proof\nRun tests\n"]
            self.assertEqual([source[item["byte_range"]["start"]:
                                     item["byte_range"]["end"]]
                              for item in result["functions"]], expected)
            self.assertEqual([item.get("task_state") for item in result["functions"]],
                             [None, None, None, "unchecked", "checked", None])
            self.assertEqual([item["end_line"] for item in result["functions"]],
                             [3, 6, 15, 8, 10, 17])
            self.assertEqual([item["name"] for item in
                              query_path(path, "source identity")["matches"]][:2],
                             ["Keep source identity", "Acceptance"])

    def test_setext_unicode_and_crlf_preserve_raw_coordinates(self):
        source = "Résumé\r\n======\r\n- [ ] Vérifier l’identité\r\n".encode()
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "notes.md"
            path.write_bytes(source)
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "navigation_only")
            self.assertEqual([entry["name"] for entry in result["functions"]],
                             ["Résumé", "Vérifier l’identité"])
            self.assertEqual(source[result["functions"][1]["byte_range"]["start"]:],
                             b"- [ ] V\xc3\xa9rifier l\xe2\x80\x99identit\xc3\xa9\r\n")

    def test_every_heading_preamble_quotes_and_newline_ranges(self):
        text = 'Preamble\n\nOne\n===\nBody\n\nTwo\n---\nTail\n# Three\n> Quoted\n> ======\n> End\n'
        for newline in ('\n', '\r\n', '\r'):
            with self.subTest(newline=repr(newline)), tempfile.TemporaryDirectory() as raw:
                source = text.replace('\n', newline).encode()
                path = Path(raw) / 'notes.md'
                path.write_bytes(source)
                result = index_file(path)
                units = result['functions']
                self.assertEqual([unit['name'] for unit in units], ['One', 'Two', 'Three', 'Quoted'])
                expected = ['One\n===\nBody\n\n', 'Two\n---\nTail\n',
                            '# Three\n> Quoted\n> ======\n> End\n',
                            'Quoted\n> ======\n> End\n']
                self.assertEqual([source[u['byte_range']['start']:u['byte_range']['end']] for u in units],
                                 [value.replace('\n', newline).encode() for value in expected])
                self.assertEqual([(u['line'], u['end_line']) for u in units],
                                 [(3, 6), (7, 9), (10, 13), (11, 13)])
                inventory = inventory_tree(Path(raw), stable=True)
                self.assertEqual(inventory['status'], 'complete')
                self.assertEqual([u['name'] for u in inventory['files'][0]['declarations']],
                                 ['One', 'Two', 'Three', 'Quoted'])

    def test_repeated_setext_inventory_delta(self):
        with tempfile.TemporaryDirectory() as raw:
            before, after = Path(raw) / 'before', Path(raw) / 'after'
            before.mkdir(); after.mkdir()
            (before / 'a.md').write_text('One\n===\nFirst\n\nTwo\n===\nSecond\n')
            (after / 'a.md').write_text('One\n===\nFirst\n\nTwo\n===\nChanged\n')
            delta = compare_inventories(inventory_tree(before, stable=True), inventory_tree(after, stable=True))
            self.assertEqual([v['candidate']['name'] for v in delta['declaration_changes']['modified']], ['Two'])
            self.assertEqual([v['candidate']['name'] for v in delta['declaration_changes']['unchanged']], ['One'])

    def test_mixed_heading_paths_and_unambiguous_delta(self):
        import itertools
        kinds = {'a1': 1, 'a2': 2, 'a3': 3, 's1': 1, 's2': 2}
        import random
        sequences = list(itertools.product(kinds, repeat=2))
        for seed in (1977, 2309, 8031):
            generator = random.Random(seed)
            sequences.extend(tuple(generator.choice(list(kinds)) for _ in range(8)) for _ in range(15))
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'mixed.md'
            for pair in sequences:
                blocks, expected, stack = [], [], []
                for i, kind in enumerate(pair):
                    name, level = f'H{i}', kinds[kind]
                    while stack and stack[-1][0] >= level:
                        stack.pop()
                    stack.append((level, name))
                    expected.append(' / '.join(title for _, title in stack))
                    heading = (f'{"#" * level} {name}\n' if kind[0] == 'a' else
                               name + '\n' + ('===' if level == 1 else '---') + '\n')
                    blocks.append(heading + f'Body{i}\n\n')
                for newline in ('\n', '\r\n', '\r'):
                    with self.subTest(pair=pair, newline=repr(newline)):
                        source = ''.join(blocks).replace('\n', newline).encode()
                        path.write_bytes(source)
                        units = index_file(path)['functions']
                        self.assertEqual([u['qualified_name'] for u in units], expected)
                        self.assertEqual([source[u['byte_range']['start']:u['byte_range']['end']] for u in units],
                                         [b.replace('\n', newline).encode() for b in blocks])
            before, after = Path(raw) / 'p', Path(raw) / 'c'
            before.mkdir(); after.mkdir()
            source = 'A\n===\n\n## Details\nfirst\n\nB\n===\n\n## Details\nsecond\n'
            (before / 'a.md').write_text(source)
            (after / 'a.md').write_text(source.replace('second', 'changed'))
            units = index_file(before / 'a.md')['functions']
            self.assertEqual([u['qualified_name'] for u in units], ['A', 'A / Details', 'B', 'B / Details'])
            self.assertTrue(all(not u['identity_ambiguous'] for u in units))
            delta = compare_inventories(inventory_tree(before, stable=True), inventory_tree(after, stable=True))
            self.assertEqual([v['candidate']['qualified_name'] for v in delta['declaration_changes']['modified']], ['B / Details'])
            self.assertEqual(delta['declaration_changes']['added'], [])
            self.assertEqual(delta['declaration_changes']['removed'], [])

    def test_quote_heading_stack_does_not_escape_to_document(self):
        source = b'Parent\n===\n\n> Quote\n> =====\n> ## Inner\n> body\n\n## Outside\nbody\n'
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'quote.md'
            path.write_bytes(source)
            self.assertEqual([u['qualified_name'] for u in index_file(path)['functions']],
                             ['Parent', 'Parent / Quote', 'Parent / Quote / Inner', 'Parent / Outside'])

    def test_markdown_candidate_delta_and_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as raw:
            planning = Path(raw) / "planning"
            candidate = Path(raw) / "candidate"
            planning.mkdir()
            candidate.mkdir()
            (planning / "task.md").write_text("# Task\n## Acceptance\n- [ ] Verify\n")
            (candidate / "task.md").write_text("# Task\n## Acceptance\n- [x] Verify\n- [ ] Ship\n")
            before = inventory_tree(planning, stable=True)
            after = inventory_tree(candidate, stable=True)
            self.assertEqual(before["status"], "complete")
            self.assertEqual(after["status"], "complete")
            delta = compare_inventories(before, after)
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            changes = delta["declaration_changes"]
            self.assertEqual([item["candidate"]["name"] for item in changes["added"]],
                             ["Ship"])
            self.assertEqual({item["candidate"]["name"] for item in changes["modified"]},
                             {"Acceptance", "Verify"})
            self.assertEqual([item["candidate"]["name"] for item in changes["unchanged"]],
                             ["Task"])
            (candidate / "task.md").write_bytes(b"# Good\n\xff\n")
            invalid = inventory_tree(candidate, stable=True)
            self.assertEqual(invalid["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
