"""Mixed-language scan policy and observed-coverage regressions."""

import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import query_path


class ScanScopeTests(unittest.TestCase):
    def test_mixed_typescript_and_selected_header(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "one.mts").write_text("export function moduleThing() { return 1; }\n")
            (root / "two.cts").write_text("export function commonThing() { return 2; }\n")
            (root / "chosen.h").write_text("inline int headerThing(){return 3;}\n")
            (root / "unknown.h").write_text("inline int unknownThing(){return 4;}\n")
            choices = {"chosen.h": "cpp"}
            found = query_path(root, "thing", language_choices=choices)
            self.assertEqual(found["scanned_files"], 3)
            self.assertEqual({item["path"] for item in found["scan_scope"]["unsupported_paths"]},
                             {"unknown.h"})
            scan = inventory_tree(root, stable=True, language_choices=choices)
            self.assertEqual(scan["status"], "complete")
            self.assertEqual([item["path"] for item in scan["files"]],
                             ["chosen.h", "one.mts", "two.cts"])
            self.assertEqual(scan["observed_unsupported_paths"][0]["path"], "unknown.h")

    def test_observed_exclusions_do_not_change_policy_or_digest(self):
        with tempfile.TemporaryDirectory() as raw:
            left, right = (Path(raw) / name for name in ("left", "right"))
            left.mkdir()
            right.mkdir()
            for root in (left, right):
                (root / "same.rs").write_text("fn same() {}\n")
            (left / "target").mkdir()
            (left / "target" / "generated.rs").write_text("fn generated() {}\n")
            planning = inventory_tree(left, stable=True)
            candidate = inventory_tree(right, stable=True)
            self.assertNotEqual(planning["observed_exclusions"], candidate["observed_exclusions"])
            self.assertEqual(planning["inventory_digest"], candidate["inventory_digest"])
            self.assertEqual(compare_inventories(planning, candidate)["status"],
                             "comparable_candidate_delta")

    def test_policy_drift_and_coverage_loss_are_visible(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "source.py").write_text("def source(): pass\n")
            baseline = inventory_tree(root, stable=True)
            changed_policy = inventory_tree(root, stable=True, excluded_directories=("generated",))
            self.assertIn("scope", compare_inventories(baseline, changed_policy)["mismatches"])
            (root / "source.py").unlink()
            (root / "source.py").symlink_to(root / "replacement.py")
            (root / "replacement.py").write_text("def replacement(): pass\n")
            lost = inventory_tree(root, stable=True)
            self.assertIn("coverage_lost:source.py", compare_inventories(baseline, lost)["mismatches"])

    def test_excluded_parent_directory_cannot_hide_prior_source(self):
        with tempfile.TemporaryDirectory() as raw:
            left, right = (Path(raw) / name for name in ("left", "right"))
            for root in (left, right):
                (root / "src").mkdir(parents=True)
                (root / "src" / "source.py").write_text("def source(): pass\n")
            planning = inventory_tree(left, stable=True)
            (right / "src" / "source.py").unlink()
            (right / "src").rmdir()
            (right / "replacement").mkdir()
            (right / "src").symlink_to(right / "replacement", target_is_directory=True)
            candidate = inventory_tree(right, stable=True)
            self.assertIn("coverage_lost:src/source.py",
                          compare_inventories(planning, candidate)["mismatches"])

    def test_caller_generated_directory_and_unsupported_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "vendor").mkdir()
            (root / "vendor" / "do_not_index.py").write_text("def skipped(): pass\n")
            (root / "current.py").write_text("def current(): pass\n")
            (root / "other.h").write_text("int other(void);\n")
            result = inventory_tree(root, stable=True, excluded_directories=("vendor",))
            self.assertEqual(result["status"], "complete")
            self.assertEqual([file["path"] for file in result["files"]], ["current.py"])
            self.assertIn({"path": "vendor", "reason": "caller_excluded_directory"},
                          result["observed_exclusions"])
            self.assertEqual(result["observed_unsupported_paths"][0]["path"], "other.h")

    def test_only_ambiguous_source_still_returns_a_scope_packet(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "unknown.h").write_text("int unknown(void);\n")
            result = query_path(root, "unknown")
            self.assertEqual(result["mapping_status"], "unsupported")
            self.assertEqual(result["scanned_files"], 0)
            self.assertEqual(result["scan_scope"]["unsupported_paths"][0]["path"],
                             "unknown.h")


if __name__ == "__main__":
    unittest.main()
