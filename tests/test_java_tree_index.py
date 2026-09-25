"""Java source-level callable and bodyless coverage fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import index_file


class JavaTreeIndexTests(unittest.TestCase):
    def _index(self, source: bytes) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "Fixture.java"
            path.write_bytes(source)
            return index_file(path)

    def _exact(self, result: dict, source: bytes) -> None:
        functions = result["functions"]
        self.assertEqual(len({item["declaration_id"] for item in functions}), len(functions))
        self.assertEqual(result["adapter_coverage"]["promised_node_count"], len(functions))
        self.assertEqual(result["structural"]["declaration_count"], len(functions))
        for item in functions:
            span = item["byte_range"]
            self.assertEqual(item["declaration_sha256"], hashlib.sha256(
                source[span["start"]:span["end"]]).hexdigest())

    def test_methods_constructors_lambdas_and_owners(self):
        source = (b"@A public class C<T> {\n"
                  b" C() {} C(int x) {}\n"
                  b" @A public <U> U f(U u) { class Local { void run(){} } return u; }\n"
                  b" int f(int x) { return x; }\n"
                  b" Runnable r = x -> x;\n"
                  b" Object a = new Object() { void owned(){} };\n"
                  b"}\n"
                  b"record R(int x) { R { } }\n"
                  b"enum E { A { void run(){} }; }\n")
        result = self._index(source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        names = {item["qualified_name"] for item in result["functions"]}
        self.assertIn("C.f.Local.run", names)
        self.assertEqual(len([item for item in result["functions"]
                              if item["qualified_name"] == "C.f"]), 2)
        generic = next(item for item in result["functions"]
                       if item["qualified_name"] == "C.f" and "<U>" in item["signature"])
        self.assertTrue(source[generic["byte_range"]["start"]:].startswith(b"@A public"))
        self.assertIn("R.R", names)
        self.assertIn("E.A.run", names)
        self.assertIn("C.<anonymous-class@", " ".join(names))
        self.assertEqual(len([item for item in result["functions"]
                              if item["declaration_kind"] == "constructor"]), 3)
        self._exact(result, source)

    def test_bodyless_and_initializer_delta(self):
        source = (b"interface I { void run(); }\n"
                  b"abstract class A { abstract void run(); static { go(); } { work(); } }\n"
                  b"@interface Tag { String value(); }\n")
        result = self._index(source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["function_count"], 0)
        self.assertEqual(result["adapter_coverage"]["bodyless_excluded_count"], 3)
        self._exact(result, source)
        with tempfile.TemporaryDirectory() as raw:
            planning, candidate = Path(raw) / "planning", Path(raw) / "candidate"
            planning.mkdir()
            candidate.mkdir()
            (planning / "A.java").write_bytes(source)
            (candidate / "A.java").write_bytes(source.replace(b"go();", b"changed();"))
            delta = compare_inventories(inventory_tree(planning, stable=True),
                                        inventory_tree(candidate, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual(len(delta["file_changes"]["modified"]), 1)
            self.assertEqual(delta["declaration_changes"]["modified"], [])

    def test_syntax_error_is_incomplete(self):
        result = self._index(b"class C { void good(){} void bad( }\n")
        self.assertEqual(result["mapping_status"], "incomplete")
        self.assertGreater(result["structural"]["error_count"] +
                           result["structural"]["missing_count"], 0)


if __name__ == "__main__":
    unittest.main()
