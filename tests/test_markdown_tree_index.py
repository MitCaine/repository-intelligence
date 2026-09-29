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
