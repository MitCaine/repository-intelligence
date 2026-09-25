"""Tree-sitter Rust navigation and optional rust-analyzer parity fixtures."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file, query_path
from repository_intelligence.rust_index import index_source as analyzer_index_source


SOURCE = b"""mod table {
    struct Game;
    impl Game {
        /// Records a winning pot.
        fn award_pot(&self) { self.record_result(); }
        fn record_result(&self) {}
    }
}
"""


class RustTreeNavigationTests(unittest.TestCase):
    def test_shared_navigation_has_source_bound_fields_and_lexical_calls(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "game.rs"
            path.write_bytes(SOURCE)
            indexed = index_file(path)
            self.assertEqual(indexed["parser"]["name"], "tree-sitter")
            self.assertEqual(indexed["mapping_status"], "navigation_only")
            self.assertEqual(indexed["function_count"], 2)
            award = query_path(path, "award pot")["matches"][0]
            self.assertEqual(award["qualified_name"], "table::impl Game::award_pot")
            self.assertEqual(award["line"], 5)
            self.assertIn("winning pot", award["docs"])
            self.assertEqual(award["lexical_call_candidates"], ["record_result"])
            span = award["byte_range"]
            self.assertTrue(SOURCE[span["start"]:span["end"]].startswith(b"///"))
            self.assertEqual(award["declaration_sha256"],
                             hashlib.sha256(SOURCE[span["start"]:span["end"]]).hexdigest())

    def test_nested_trait_impl_generic_and_closure_are_navigable(self):
        source = (b"mod table {\n"
                  b"  trait Contract { fn required(&self); fn default(&self) {} }\n"
                  b"  struct Game;\n"
                  b"  impl Game { #[inline] fn apply<T>(&self, x: T) { let f = |y| y; helper(); } }\n"
                  b"  fn outer() { fn inner() {} inner(); }\n"
                  b"}\n")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "forms.rs"
            path.write_bytes(source)
            indexed = index_file(path)
            self.assertEqual(indexed["mapping_status"], "navigation_only")
            names = {entry["qualified_name"] for entry in indexed["functions"]}
            self.assertIn("table::Contract::default", names)
            self.assertIn("table::impl Game::apply", names)
            self.assertIn("table::outer::inner", names)
            self.assertTrue(any(entry["declaration_kind"] == "closure"
                                for entry in indexed["functions"]))
            self.assertNotIn("table::Contract::required", names)  # bodyless signature
            apply = next(entry for entry in indexed["functions"] if entry["name"] == "apply")
            self.assertIn("helper", apply["lexical_call_candidates"])
            span = apply["byte_range"]
            self.assertTrue(source[span["start"]:span["end"]].startswith(b"#[inline]"))

    def test_malformed_rust_is_incomplete_with_syntax_diagnostics(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "broken.rs"
            path.write_bytes(b"fn broken( {\n")
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertGreater(result["structural"]["diagnostic_count"], 0)

    def test_richer_rust_syntax_retains_exact_attribute_generic_and_closure_ranges(self):
        source = (b"mod api {\n"
                  b"  pub trait Store<T> { fn get(&self, id: T);\n"
                  b"    fn map<F>(&self, input: T, apply: F) -> T where F: Fn(T) -> T { apply(input) }\n"
                  b"  }\n"
                  b"  struct Cache<T>(T);\n"
                  b"  impl<T> Store<T> for Cache<T> {\n"
                  b"    /// Map through a cache.\n"
                  b"    #[inline]\n"
                  b"    fn map<F>(&self, input: T, apply: F) -> T where F: Fn(T) -> T {\n"
                  b"      let transform = move |value: T| apply(value);\n"
                  b"      transform(input)\n"
                  b"    }\n"
                  b"    fn get(&self, id: T) {}\n"
                  b"  }\n"
                  b"}\n")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "richer.rs"
            path.write_bytes(source)
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "navigation_only")
            self.assertEqual(result["adapter_coverage"]["bodyless_excluded_count"], 1)
            self.assertEqual(result["adapter_coverage"]["mapped_node_count"], 4)
            impl_map = next(item for item in result["functions"]
                            if item["qualified_name"].endswith("::map")
                            and "impl" in item["qualified_name"])
            span = impl_map["byte_range"]
            self.assertTrue(source[span["start"]:span["end"]].startswith(b"/// Map"))
            self.assertIn("Map through a cache", impl_map["docs"])
            self.assertIn("apply", impl_map["lexical_call_candidates"])
            self.assertEqual(impl_map["declaration_sha256"],
                             hashlib.sha256(source[span["start"]:span["end"]]).hexdigest())
            closure = next(item for item in result["functions"]
                           if item["declaration_kind"] == "closure")
            cspan = closure["byte_range"]
            self.assertEqual(source[cspan["start"]:cspan["end"]],
                             b"move |value: T| apply(value)")

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer unavailable")
    def test_named_navigation_parity_with_optional_rust_analyzer(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "game.rs"
            path.write_bytes(SOURCE)
            current = index_file(path)
            analyzer = analyzer_index_source(path, SOURCE)
            current_by_name = {entry["qualified_name"]: entry for entry in current["functions"]}
            analyzer_by_name = {entry["qualified_name"]: entry for entry in analyzer["functions"]}
            self.assertEqual(set(current_by_name), set(analyzer_by_name))
            for name in current_by_name:
                self.assertEqual(current_by_name[name]["line"], analyzer_by_name[name]["line"])
                self.assertEqual(current_by_name[name]["lexical_call_candidates"],
                                 analyzer_by_name[name]["lexical_call_candidates"])


if __name__ == "__main__":
    unittest.main()
