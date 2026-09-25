"""C# callable, accessor, bodyless and exact-byte fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file
from repository_intelligence.inventory import compare_inventories, inventory_tree


class CSharpTreeIndexTests(unittest.TestCase):
    def test_attribute_text_does_not_make_constructor_static(self):
        source = (b'class C { [System.Obsolete(" static ")] public C() {} '
                  b'[System.Obsolete("instance")] static C() {} }')
        entries = [entry for entry in self._index(source)["functions"]
                   if entry["name"] == "C"]
        self.assertEqual([entry["declaration_kind"] for entry in entries],
                         ["constructor", "static_constructor"])

    def test_generic_arity_ignores_comment(self):
        plain = self._index(b"class C { void F<T, U>() {} }")
        commented = self._index(b"class C { void F<T, /* note */ U>() {} }")
        self.assertEqual(plain["functions"][0]["declaration_id"],
                         commented["functions"][0]["declaration_id"])

    def test_parameter_comment_does_not_change_identity(self):
        plain = self._index(b"class C { int Add(int a, int b) {return a+b;} }")
        commented = self._index(b"class C { int Add(int a, /* note */ int b) {return a+b;} }")
        self.assertEqual(plain["functions"][0]["declaration_id"],
                         commented["functions"][0]["declaration_id"])

    def test_conversion_keyword_not_attribute_text_controls_identity(self):
        source = (b"class C { [Obsolete(\"explicit\")] "
                  b"public static implicit operator int(C x) => 1; }")
        entry = self._index(source)["functions"][0]
        self.assertEqual(entry["name"], "implicit operator int")
        self.assertEqual(entry["declaration_kind"], "conversion")

    def test_modifier_and_type_token_boundaries_do_not_collide(self):
        source = (b"class refint {} class C {"
                  b" int F(ref int x) { return 1; }"
                  b" int F(refint x) { return 2; } }")
        entries = [entry for entry in self._index(source)["functions"] if entry["name"] == "F"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(len({entry["declaration_id"] for entry in entries}), 2)
        self.assertFalse(any(entry["identity_ambiguous"] for entry in entries))

    def test_file_scoped_namespace_owns_members(self):
        result = self._index(b"namespace Example; class C { void Run(){} }\n")
        self.assertEqual({item["qualified_name"] for item in result["functions"]},
                         {"Example.C.Run"})

    def test_valid_value_reference_overloads_survive_insert_and_reorder(self):
        before = b"class C { int F(int x){return 1;} int F(ref int y){return 2;} }\n"
        after = (b"class C { int F(double d){return 3;} "
                 b"int F(ref int y){return 2;} int F(int x){return 1;} }\n")
        indexed = self._index(before)
        self.assertEqual({before[e["byte_range"]["start"]:e["byte_range"]["end"]]
                          for e in indexed["functions"]},
                         {b"int F(int x){return 1;}", b"int F(ref int y){return 2;}"})
        self.assertFalse(any(e.get("identity_ambiguous") for e in indexed["functions"]))
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.cs").write_bytes(before)
            (right / "C.cs").write_bytes(after)
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            changes = delta["declaration_changes"]
            self.assertEqual(tuple(len(changes[key]) for key in
                                   ("added", "removed", "modified", "unchanged")),
                             (1, 0, 0, 2))

    def test_generic_arity_and_indexer_parameter_owners(self):
        before = (b"class C { int F<T>(){return 1;} int F<T,U>(){return 2;} "
                  b"int this[int i] { get { return i; } } "
                  b"int this[string s] { get { return 2; } } }\n")
        indexed = self._index(before)
        entries = indexed["functions"]
        self.assertFalse(any(e.get("identity_ambiguous") for e in entries
                             if e["qualified_name"] == "C.F"))
        expected = {
            ("C.F", b"int F<T>(){return 1;}"),
            ("C.F", b"int F<T,U>(){return 2;}"),
            ("C.this[int].get", b"get { return i; }"),
            ("C.this[string].get", b"get { return 2; }"),
        }
        self.assertEqual({(e["qualified_name"], before[e["byte_range"]["start"]:
                                                    e["byte_range"]["end"]]) for e in entries},
                         expected)
        self.assertEqual(len({e["declaration_id"] for e in entries}), 4)
        self.assertFalse(any(e.get("identity_ambiguous") for e in entries))
        after = (b"// unrelated\nclass C { int F<T,U>(){return 2;} "
                 b"int this[string s] { get { return 2; } } "
                 b"int F<T>(){return 1;} int this[int i] { get { return i; } } }\n")
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.cs").write_bytes(before)
            (right / "C.cs").write_bytes(after)
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            changes = delta["declaration_changes"]
            self.assertEqual(tuple(len(changes[k]) for k in
                                   ("added", "removed", "modified", "unchanged")),
                             (0, 0, 0, 4))

    def test_nested_local_identity_in_generic_overloads(self):
        source = (b"class C { int F<T>() { int Local(){return 1;} return Local(); } "
                  b"int F<T,U>() { int Local(){return 2;} return Local(); } }\n")
        entries = self._index(source)["functions"]
        locals_ = [entry for entry in entries if entry["qualified_name"] == "C.F.Local"]
        self.assertEqual(len(locals_), 2)
        self.assertEqual({source[e["byte_range"]["start"]:e["byte_range"]["end"]]
                          for e in locals_},
                         {b"int Local(){return 1;}", b"int Local(){return 2;}"})
        self.assertFalse(any(e.get("identity_ambiguous") for e in locals_))
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
        self.assertTrue({"C.P.get", "C.P.set", "C.this[int].get", "C.this[int].set",
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
