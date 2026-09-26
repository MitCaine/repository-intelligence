"""Focused tests for the disposable, source-derived Rust locator."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.rust_index import (
    _tokens, format_compact, format_tree_compact, index_file, query, query_tree,
)


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

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
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
            missing = query(indexed, "missing term")
            self.assertEqual(missing["matches"], [])
            self.assertEqual(missing["total_matches"], 0)
            compact = format_compact(query(indexed, "award record", 1))
            self.assertEqual(len(compact.splitlines()), 4)
            self.assertIn("PARTIAL DIAGNOSTICS", compact)
            self.assertIn(indexed["raw_sha256"], compact)
            self.assertIn("doc: Records a winning pot.", compact)
            self.assertIn("calls?: record_result", compact)
            self.assertIn("shown=1", compact)
            source_path.write_bytes(self.SOURCE + b"\n")
            self.assertNotEqual(indexed["raw_sha256"], index_file(source_path)["raw_sha256"])

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
    def test_native_error_node_count_is_not_syntax_validation(self):
        # The native CLI drops parser diagnostics from its JSON tree. Missing
        # delimiters and semicolons need not become ERROR nodes in that tree.
        invalid_sources = (b"fn target() {", b"fn target( {}",
                           b"fn target() { let x = 1 }")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.rs"
            for source in invalid_sources:
                with self.subTest(source=source):
                    path.write_bytes(source)
                    indexed = index_file(path)
                    self.assertEqual(indexed["parse_error_count"], 0)
                    self.assertEqual(indexed["diagnostic_coverage"], "error_nodes_only")
                    self.assertEqual(indexed["parse_error_count_kind"],
                                     "error_node_lower_bound")
                    self.assertEqual([item["name"] for item in indexed["functions"]],
                                     ["target"])
                    self.assertEqual(indexed["functions"][0]["byte_range"],
                                     {"start": 0, "end": len(source)})
                    self.assertIn("PARTIAL DIAGNOSTICS",
                                  format_compact(query(indexed, "target")))
                    tree = query_tree(Path(directory), "target")
                    self.assertEqual(tree["diagnostic_coverage"], "error_nodes_only")
                    self.assertEqual(tree["matches"][0]["parse_error_count_kind"],
                                     "error_node_lower_bound")
                    self.assertIn("PARTIAL DIAGNOSTICS", format_tree_compact(tree))

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
    def test_lone_cr_counts_as_whitespace_in_native_display_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.rs"
            path.write_bytes(b"fn target() {}\rfn caller() { target(); }\n")
            self.assertEqual([(entry["name"], entry["line"], entry["column"])
                              for entry in index_file(path)["functions"]],
                             [("target", 1, 4), ("caller", 1, 19)])

    def test_query_rejects_unbounded_output(self):
        self.assertEqual(_tokens("TournamentTableSettlement::award_pot"),
                         ["tournament", "table", "settlement", "award", "pot"])
        with self.assertRaises(ValueError):
            query({"functions": []}, "pot", 21)
        with self.assertRaises(ValueError):
            query({"functions": []}, "", 1)

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
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

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
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

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
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

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer not installed")
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
