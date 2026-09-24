"""Focused tests for the disposable, source-derived Rust locator."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.rust_index import _tokens, format_compact, index_file, query


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


if __name__ == "__main__":
    unittest.main()
