"""Focused tests for the disposable, source-derived Rust locator."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.rust_index import index_file, query


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
            source_path.write_bytes(self.SOURCE + b"\n")
            self.assertNotEqual(indexed["raw_sha256"], index_file(source_path)["raw_sha256"])

    def test_query_rejects_unbounded_output(self):
        with self.assertRaises(ValueError):
            query({"functions": []}, "pot", 21)
        with self.assertRaises(ValueError):
            query({"functions": []}, "", 1)


if __name__ == "__main__":
    unittest.main()
