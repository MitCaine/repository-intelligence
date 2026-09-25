"""C# callable, accessor, bodyless and exact-byte fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file


class CSharpTreeIndexTests(unittest.TestCase):
    def _index(self, source: bytes) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "Fixture.cs"
            path.write_bytes(source)
            return index_file(path)

    def _exact(self, result: dict, source: bytes) -> None:
        functions = result["functions"]
        self.assertEqual(result["adapter_coverage"]["promised_node_count"], len(functions))
        self.assertEqual(result["structural"]["declaration_count"], len(functions))
        self.assertEqual(len({item["declaration_id"] for item in functions}), len(functions))
        for item in functions:
            span = item["byte_range"]
            self.assertEqual(item["declaration_sha256"], hashlib.sha256(
                source[span["start"]:span["end"]]).hexdigest())

    def test_methods_constructors_operators_local_and_anonymous(self):
        source = (b"namespace N { [A] public class C {\n"
                  b" public C(){} static C(){} ~C(){}\n"
                  b" [A] public int F(int x){ int L()=>x; return L(); }\n"
                  b" public int F()=>1;\n"
                  b" public static C operator +(C a,C b)=>a;\n"
                  b" public static explicit operator int(C a)=>1;\n"
                  b" Action a = x=>x; Action b = delegate(){};\n"
                  b" } record R(int X) { public int F()=>X; } }\n")
        result = self._index(source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        functions = result["functions"]
        names = [item["qualified_name"] for item in functions]
        self.assertEqual(names.count("N.C.F"), 2)
        self.assertIn("N.C.F.L", names)
        self.assertIn("N.R.F", names)
        self.assertEqual(len([item for item in functions
                              if item["declaration_kind"] in {"constructor", "static_constructor"}]), 2)
        self.assertIn("static_constructor", {item["declaration_kind"] for item in functions})
        self.assertIn("destructor", {item["declaration_kind"] for item in functions})
        self.assertEqual(len([item for item in functions if item["anonymous"]]), 2)
        self.assertIn("operator", {item["declaration_kind"] for item in functions})
        self.assertIn("conversion", {item["declaration_kind"] for item in functions})
        decorated = next(item for item in functions
                         if item["qualified_name"] == "N.C.F" and "int x" in item["signature"])
        self.assertTrue(source[decorated["byte_range"]["start"]:].startswith(b"[A] public"))
        self._exact(result, source)

    def test_executable_and_bodyless_accessors(self):
        source = (b"interface I { void M(); int P { get; } }\n"
                  b"abstract class A { public abstract void M(); }\n"
                  b"class C { int P { get {return 1;} set {} }\n"
                  b" int this[int i] { get => i; set {} }\n"
                  b" event Action E { add {} remove {} }\n"
                  b" int Q => 1; int this[string s] => 2;\n"
                  b" int Auto { get; set; } = 1; }\n")
        result = self._index(source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        names = {item["qualified_name"] for item in result["functions"]}
        self.assertTrue({"C.P.get", "C.P.set", "C.this[].get", "C.this[].set",
                         "C.E.add", "C.E.remove", "C.Q.get"}.issubset(names))
        self.assertNotIn("C.Auto.get", names)
        self.assertEqual(result["adapter_coverage"]["bodyless_excluded_count"], 5)
        self._exact(result, source)

    def test_parse_error_is_incomplete(self):
        result = self._index(b"class C { void Good(){} void Bad( }\n")
        self.assertEqual(result["mapping_status"], "incomplete")
        self.assertGreater(result["structural"]["error_count"] +
                           result["structural"]["missing_count"], 0)


if __name__ == "__main__":
    unittest.main()
