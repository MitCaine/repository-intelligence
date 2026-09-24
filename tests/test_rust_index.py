"""Focused tests for the disposable, source-derived Rust locator."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.rust_index import (
    _tokens, format_compact, format_tree_compact, index_file, query, query_tree,
)


@unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
class RustIndexTests(unittest.TestCase):
    SOURCE = b"""mod table {
    struct Game;
    impl Game {
        /// Records a winning pot.
        fn award_pot(&self) { self.record_result(); }
        fn record_result(&self) {}
    }
}
"""

    def test_source_bound_locations_docs_and_lexical_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "sample.rs"
            source_path.write_bytes(self.SOURCE)
            indexed = index_file(source_path)
            self.assertEqual(indexed["function_count"], 2)
            self.assertEqual(indexed["raw_sha256"], hashlib.sha256(self.SOURCE).hexdigest())
            award = query(indexed, "award pot", 1)["matches"][0]
            self.assertEqual(award["line"], 5)
            self.assertEqual(award["qualified_name"], "table::impl Game::award_pot")
            self.assertIn("winning pot", award["docs"])
            self.assertIn("record_result", award["lexical_call_candidates"])
            self.assertNotIn("records", query(indexed, "missing term")["matches"])
            compact = format_compact(query(indexed, "award record", 1))
            self.assertEqual(len(compact.splitlines()), 3)
            self.assertIn(indexed["raw_sha256"], compact)
            self.assertIn("doc: Records a winning pot.", compact)
            self.assertIn("calls?: record_result", compact)
            self.assertIn("shown=1", compact)
            source_path.write_bytes(self.SOURCE + b"\n")
            self.assertNotEqual(indexed["raw_sha256"], index_file(source_path)["raw_sha256"])

    def test_query_rejects_unbounded_output(self):
        self.assertEqual(_tokens("TournamentTableSettlement::award_pot"),
                         ["tournament", "table", "settlement", "award", "pot"])
        with self.assertRaises(ValueError):
            query({"functions": []}, "pot", 21)
        with self.assertRaises(ValueError):
            query({"functions": []}, "", 1)

    def test_tree_query_is_source_bound_and_reports_incomplete_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "game.rs").write_bytes(self.SOURCE)
            (root / "target").mkdir()
            (root / "target" / "ignored.rs").write_text("fn award_pot() {}")
            result = query_tree(root, "award pot", 2)
            self.assertEqual(result["scanned_files"], 1)
            self.assertEqual(result["total_matches"], 1)
            self.assertEqual(result["matches"][0]["line"], 5)
            self.assertEqual(result["matches"][0]["raw_sha256"],
                             hashlib.sha256(self.SOURCE).hexdigest())
            self.assertIn("game.rs:5", format_tree_compact(result))
            (root / "src" / "missing.rs").symlink_to(root / "does-not-exist.rs")
            incomplete = query_tree(root, "award pot")
            self.assertEqual(len(incomplete["failures"]), 1)
            self.assertIn("INCOMPLETE", format_tree_compact(incomplete))
            with self.assertRaises(ValueError):
                query_tree(root / "missing", "award pot")


if __name__ == "__main__":
    unittest.main()
