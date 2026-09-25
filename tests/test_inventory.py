"""Query-independent structural inventory and fail-closed candidate deltas."""

import copy
import os
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import MAX_PARSE_BYTES, query_path


class InventoryTests(unittest.TestCase):
    def test_files_and_declarations_change_independently_of_queries_or_absolute_roots(self):
        with tempfile.TemporaryDirectory() as raw:
            planning, candidate = (Path(raw) / name for name in ("planning", "candidate"))
            planning.mkdir()
            candidate.mkdir()
            (planning / "main.py").write_text(
                "def stay(): return 1\ndef change(): return 1\ndef removed(): return 3\n")
            (candidate / "main.py").write_text(
                "def stay(): return 1\ndef change(): return 2\ndef added(): return 4\n")
            (planning / "empty.rs").write_text("// before\n")
            (candidate / "empty.rs").write_text("// after\n")
            (planning / "gone.py").write_text("def gone(): pass\n")
            (candidate / "new.rs").write_text("fn fresh() {}\n")
            p = inventory_tree(planning, stable=True)
            c = inventory_tree(candidate, stable=True)
            self.assertEqual(p["status"], "complete")
            self.assertEqual(c["status"], "complete")
            self.assertNotEqual(p["root"], c["root"])
            self.assertEqual([file["path"] for file in p["files"]],
                             ["empty.rs", "gone.py", "main.py"])
            self.assertEqual(next(file for file in p["files"] if file["path"] == "empty.rs")
                             ["declarations"], [])
            before = p["inventory_digest"]
            query_path(planning, "stay")
            query_path(planning, "removed")
            self.assertEqual(inventory_tree(planning, stable=True)["inventory_digest"], before)
            delta = compare_inventories(p, c)
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            files = delta["file_changes"]
            self.assertEqual([item["path"] for item in files["added"]], ["new.rs"])
            self.assertEqual([item["path"] for item in files["removed"]], ["gone.py"])
            self.assertEqual([item["path"] for item in files["modified"]],
                             ["empty.rs", "main.py"])
            declarations = delta["declaration_changes"]
            self.assertEqual(len(declarations["added"]), 2)
            self.assertEqual(len(declarations["removed"]), 2)
            self.assertEqual(len(declarations["modified"]), 1)
            self.assertEqual(len(declarations["unchanged"]), 1)
            self.assertIn("change", declarations["modified"][0]["declaration_id"])

    def test_identical_bytes_have_same_digest_across_checkout_roots(self):
        with tempfile.TemporaryDirectory() as raw:
            left, right = (Path(raw) / name for name in ("left", "right"))
            left.mkdir()
            right.mkdir()
            for root in (left, right):
                (root / "same.py").write_text("def same(): return 1\n")
            p, c = inventory_tree(left, stable=True), inventory_tree(right, stable=True)
            self.assertEqual(p["inventory_digest"], c["inventory_digest"])
            self.assertEqual(len(compare_inventories(p, c)["file_changes"]["unchanged"]), 1)

    def test_non_atomic_errors_and_exclusions_do_not_silently_qualify(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "valid.py").write_text("def valid(): return 1\n")
            (root / "broken.py").write_text("def broken(:\n")
            (root / "oversized.rs").write_bytes(b" " * (MAX_PARSE_BYTES + 1))
            (root / ".hidden").mkdir()
            (root / ".hidden" / "ignored.py").write_text("def hidden(): pass\n")
            (root / "nested").mkdir()
            (root / "nested" / ".git").mkdir()
            (root / "nested" / "ignored.rs").write_text("fn hidden() {}\n")
            os.symlink(root / "valid.py", root / "linked.py")
            snapshot = inventory_tree(root, stable=True)
            self.assertEqual(snapshot["status"], "incomplete")
            self.assertTrue(snapshot["failures"])
            self.assertIn("symlink_file", {item["reason"] for item in snapshot["observed_exclusions"]})
            self.assertIn("nested_repository", {item["reason"] for item in snapshot["observed_exclusions"]})
            blocked = compare_inventories(snapshot, snapshot)
            self.assertIsNone(blocked["declaration_changes"])
            self.assertEqual(len(blocked["planning"]["files"]), 3)
            self.assertTrue(blocked["planning"]["observed_exclusions"])
            live = inventory_tree(root)
            self.assertIn("working_tree_non_atomic", live["incomplete_reasons"])

    def test_hardlink_duplicate_and_contract_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            original = root / "a.py"
            original.write_text("def a(): pass\n")
            complete = inventory_tree(root, stable=True)
            changed = copy.deepcopy(complete)
            changed["parser_contract"][".py"]["grammar_version"] = "future"
            incompatible = compare_inventories(complete, changed)
            self.assertEqual(incompatible["status"], "incompatible")
            self.assertIn("parser_contract", incompatible["mismatches"])
            self.assertIsNone(incompatible["declaration_changes"])
            repeated = copy.deepcopy(complete)
            repeated["files"].append(copy.deepcopy(repeated["files"][0]))
            self.assertIn("candidate_duplicate_file_path",
                          compare_inventories(complete, repeated)["mismatches"])
            os.link(original, root / "b.py")
            duplicate = inventory_tree(root, stable=True)
            self.assertEqual(duplicate["status"], "complete")
            self.assertEqual([item["path"] for item in duplicate["files"]], ["a.py", "b.py"])

    def test_forged_complete_flag_cannot_override_file_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "one.py").write_text("def one(): return 1\n")
            valid = inventory_tree(root, stable=True)
            mutations = {
                "mapping": lambda packet: packet["files"][0].__setitem__("mapping_status", "incomplete"),
                "error": lambda packet: packet["files"][0]["structural"].__setitem__("error_count", 1),
                "missing": lambda packet: packet["files"][0]["structural"].__setitem__("missing_count", 1),
                "unhandled": lambda packet: packet["files"][0]["adapter_coverage"].__setitem__(
                    "unhandled_node_count", 1),
                "parser": lambda packet: packet["files"][0]["parser"].__setitem__(
                    "grammar_version", "future"),
                "identity": lambda packet: packet["files"][0].__setitem__("source_identity", None),
                "digest": lambda packet: packet.__setitem__("inventory_digest", "wrong"),
            }
            for label, mutate in mutations.items():
                with self.subTest(mutation=label):
                    forged = copy.deepcopy(valid)
                    mutate(forged)
                    self.assertEqual(forged["status"], "complete")
                    delta = compare_inventories(valid, forged)
                    self.assertEqual(delta["status"], "incompatible")
                    self.assertIsNone(delta["file_changes"])
                    self.assertIsNone(delta["declaration_changes"])

    def test_identical_file_bytes_cannot_have_changed_declaration_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "one.py").write_text("def one(): return 1\n")
            valid = inventory_tree(root, stable=True)
            changed = copy.deepcopy(valid)
            changed["files"][0]["declarations"][0]["declaration_sha256"] = "0" * 64
            self.assertEqual(valid["inventory_digest"], changed["inventory_digest"])
            delta = compare_inventories(valid, changed)
            self.assertEqual(delta["status"], "incompatible")
            self.assertIn("unchanged_file_evidence:one.py", delta["mismatches"])
            self.assertIsNone(delta["file_changes"])
            self.assertIsNone(delta["declaration_changes"])

    def test_anonymous_movement_is_reported_as_add_and_remove(self):
        with tempfile.TemporaryDirectory() as raw:
            left, right = (Path(raw) / name for name in ("left", "right"))
            left.mkdir()
            right.mkdir()
            (left / "f.py").write_text("f = lambda x: x + 1\n")
            (right / "f.py").write_text("# inserted\nf = lambda x: x + 1\n")
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual(len(delta["declaration_changes"]["added"]), 1)
            self.assertEqual(len(delta["declaration_changes"]["removed"]), 1)
            self.assertEqual(delta["declaration_changes"]["modified"], [])

    def test_file_move_is_add_and_remove_without_guessing_rename(self):
        with tempfile.TemporaryDirectory() as raw:
            left, right = (Path(raw) / name for name in ("left", "right"))
            left.mkdir()
            right.mkdir()
            (left / "before.rs").write_text("fn same() {}\n")
            (right / "after.rs").write_text("fn same() {}\n")
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual([item["path"] for item in delta["file_changes"]["added"]],
                             ["after.rs"])
            self.assertEqual([item["path"] for item in delta["file_changes"]["removed"]],
                             ["before.rs"])
            self.assertEqual(len(delta["declaration_changes"]["added"]), 1)
            self.assertEqual(len(delta["declaration_changes"]["removed"]), 1)


if __name__ == "__main__":
    unittest.main()
