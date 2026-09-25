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
            self.assertEqual(award["column"], 12)
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

    def test_rust_declaration_range_includes_attached_attribute(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "attr.rs"
            source = b"#[inline]\n/// Comment.\nfn example() { work(); }\n"
            path.write_bytes(source)
            entry = index_file(path)["functions"][0]
            span = entry["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]], source.rstrip(b"\n"))
            self.assertEqual(entry["declaration_sha256"],
                             hashlib.sha256(source[span["start"]:span["end"]]).hexdigest())

    def test_ranking_sees_rust_docs_and_calls_beyond_packet_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "search.rs"
            calls = " ".join(f"call_{number:02d}();" for number in range(20))
            path.write_text(f"/// {'filler ' * 60}late_document_term\n"
                            f"fn find_target() {{ {calls} }}\n")
            indexed = index_file(path)
            by_doc = query(indexed, "late document term")
            by_call = query(indexed, "call 19")
            self.assertEqual(by_doc["matches"][0]["name"], "find_target")
            self.assertEqual(by_call["matches"][0]["name"], "find_target")
            self.assertLessEqual(len(by_doc["matches"][0]["docs"]), 220)
            self.assertIn("call_19", by_call["matches"][0]["lexical_call_candidates"])

    def test_ranking_uses_relevance_without_project_specific_test_demotion(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "clock.rs"
            source_path.write_text(
                "fn resume_clock() {}\n"
                "mod tests {\n"
                "    /// Pause and resume the clock.\n"
                "    fn resume_clock() {}\n"
                "}\n")
            matches = query(index_file(source_path), "pause resume clock", 2)["matches"]
            self.assertEqual(matches[0]["qualified_name"], "tests::resume_clock")
            self.assertEqual(matches[1]["qualified_name"], "resume_clock")
            tree_matches = query_tree(Path(directory), "pause resume clock", 2)["matches"]
            self.assertEqual([item["qualified_name"] for item in tree_matches],
                             ["tests::resume_clock", "resume_clock"])

    def test_tree_query_is_source_bound_and_reports_incomplete_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "game.rs").write_bytes(self.SOURCE)
            (root / "target").mkdir()
            (root / "target" / "ignored.rs").write_text("fn award_pot() {}")
            (root / "tests").mkdir()
            (root / "tests" / "game_contract.rs").write_text("fn award_pot() {}")
            result = query_tree(root, "award pot", 2)
            self.assertEqual(result["result_kind"], "legacy_rust_query")
            self.assertEqual(result["scanned_files"], 2)
            self.assertEqual(result["total_matches"], 2)
            self.assertEqual(result["matches"][0]["path"], str(root / "src" / "game.rs"))
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
