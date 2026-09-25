"""The bounded source-level callable promises of the two Tree-sitter adapters."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.declarations import finalize_coverage
from repository_intelligence.locator import index_file


class CallableCoverageTests(unittest.TestCase):
    def test_shared_finalizer_rejects_missing_or_duplicate_mapping(self):
        entry = {"declaration_kind": "function", "byte_range": {"start": 0, "end": 4}}
        with self.assertRaisesRegex(ValueError, "not accounted"):
            finalize_coverage([entry], promised=2, unhandled=0, bodyless_excluded=0)
        with self.assertRaisesRegex(ValueError, "mapped more than once"):
            finalize_coverage([entry, entry], promised=2, unhandled=0,
                              bodyless_excluded=0)

    def _index(self, filename: str, source: bytes) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / filename
            path.write_bytes(source)
            return index_file(path)

    def _assert_exact_unique_ranges(self, result: dict, source: bytes) -> None:
        ranges = set()
        for entry in result["functions"]:
            span = entry["byte_range"]
            pair = span["start"], span["end"]
            self.assertNotIn(pair, ranges)
            ranges.add(pair)
            self.assertGreater(pair[1], pair[0])
            self.assertEqual(entry["declaration_sha256"],
                             hashlib.sha256(source[pair[0]:pair[1]]).hexdigest())
        coverage = result["adapter_coverage"]
        self.assertEqual(coverage["promised_node_count"],
                         coverage["mapped_node_count"] + coverage["unhandled_node_count"])
        self.assertEqual(coverage["mapped_node_count"], len(ranges))

    def test_python_named_nested_decorated_methods_and_lambdas(self):
        source = ("# coding: latin-1\n"
                  "@dec\nasync def work():\n"
                  "    \"\"\"café\"\"\"\n"
                  "    class C:\n        def method(self): return (lambda x: x)\n"
                  "    def local(): return 1\n"
                  "    first = lambda x: x\n    second = lambda x: x\n").encode("latin-1")
        result = self._index("forms.py", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["adapter_coverage"], {
            "promised_node_count": 6, "mapped_node_count": 6,
            "unhandled_node_count": 0, "bodyless_excluded_count": 0})
        names = [entry["qualified_name"] for entry in result["functions"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("work.C.method", names)
        self.assertIn("work.local", names)
        self._assert_exact_unique_ranges(result, source)
        work = result["functions"][0]
        self.assertTrue(source[work["byte_range"]["start"]:].startswith(b"@dec"))

    def test_rust_named_nested_trait_impl_generic_closures_and_bodyless_policy(self):
        source = (b"extern \"C\" { fn foreign(); }\n"
                  b"trait T { fn required(&self); fn default(&self) {} }\n"
                  b"impl T for Game { #[inline] fn default(&self) { let x = || 1; let y = || 2; } }\n"
                  b"fn outer<T>() { fn inner() {} inner(); }\n")
        result = self._index("forms.rs", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["adapter_coverage"], {
            "promised_node_count": 6, "mapped_node_count": 6,
            "unhandled_node_count": 0, "bodyless_excluded_count": 2})
        self._assert_exact_unique_ranges(result, source)
        names = [entry["qualified_name"] for entry in result["functions"]]
        self.assertIn("T::default", names)
        self.assertIn("outer::inner", names)
        self.assertNotIn("T::required", names)
        self.assertEqual(len(names), len(set(names)))

    def test_repeated_named_declarations_are_distinct_without_duplicate_mapping(self):
        for filename, source in [
            ("repeated.py", b"def same(): return 1\ndef same(): return 2\n"),
            ("repeated.rs", b"fn same() {}\nfn same() {}\n"),
        ]:
            with self.subTest(filename=filename):
                result = self._index(filename, source)
                self.assertEqual(result["mapping_status"], "navigation_only")
                self.assertEqual(result["adapter_coverage"]["promised_node_count"], 2)
                self.assertEqual(len({entry["declaration_id"]
                                      for entry in result["functions"]}), 2)
                self._assert_exact_unique_ranges(result, source)

    def test_bodyless_outside_rust_declaration_context_and_empty_python_body_incomplete(self):
        rust = self._index("invalid.rs", b"fn orphan();\n")
        self.assertEqual(rust["mapping_status"], "incomplete")
        self.assertEqual(rust["adapter_coverage"]["unhandled_node_count"], 1)
        self.assertEqual(rust["unhandled_declarations"][0]["syntax_kind"],
                         "function_signature_item")
        python = self._index("invalid.py", b"def empty():\n")
        self.assertEqual(python["mapping_status"], "incomplete")
        self.assertEqual(python["adapter_coverage"]["unhandled_node_count"], 1)

    def test_error_and_missing_never_claim_complete(self):
        for filename, source, kind in [
            ("broken.py", b"def good(): return 1\ndef (): pass\n", "ERROR"),
            ("missing.py", b"def good(): return 1\ndef broken(:\n", "MISSING"),
            ("broken.rs", b"fn good() {}\nfn broken( {\n", "ERROR"),
            ("missing.rs", b"fn good() {}\nfn broken()\n", "MISSING"),
        ]:
            with self.subTest(filename=filename):
                result = self._index(filename, source)
                self.assertEqual(result["mapping_status"], "incomplete")
                self.assertIn(kind, {item["kind"] for item in result["structural"]["diagnostics"]})
                self._assert_exact_unique_ranges(result, source)


if __name__ == "__main__":
    unittest.main()
