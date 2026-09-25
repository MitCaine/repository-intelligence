"""Java source-level callable and bodyless coverage fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import index_file, query_path


class JavaTreeIndexTests(unittest.TestCase):
    def test_varargs_local_name_is_not_declaration_identity(self):
        before = b"class C { void f(String... args) {} }"
        after = b"class C { void f(String... values) {} }"
        left = self._index(before)["functions"][0]
        right = self._index(after)["functions"][0]
        self.assertEqual(left["declaration_id"], right["declaration_id"])
        self.assertNotEqual(left["declaration_sha256"], right["declaration_sha256"])

    def test_local_class_members_in_overloads_have_distinct_owner_identity(self):
        source = (b"class C {"
                  b" void f(int x) { class Local { void g() {} } }"
                  b" void f(String x) { class Local { void g() {} } }"
                  b" }")
        entries = [entry for entry in self._index(source)["functions"] if entry["name"] == "g"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(len({entry["declaration_id"] for entry in entries}), 2)
        self.assertFalse(any(entry["identity_ambiguous"] for entry in entries))

    def test_array_declarator_dimensions_distinguish_overloads(self):
        before = b"class C { int f(int x){return 1;} int f(int x[]){return 2;} }\n"
        indexed = self._index(before)
        self.assertEqual({before[e["byte_range"]["start"]:e["byte_range"]["end"]]
                          for e in indexed["functions"]},
                         {b"int f(int x){return 1;}", b"int f(int x[]){return 2;}"})
        self.assertFalse(any(e.get("identity_ambiguous") for e in indexed["functions"]))
        after = (b"// unrelated\nclass C { int f(int x[]){return 2;} "
                 b"int f(int x){return 1;} }\n")
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.java").write_bytes(before)
            (right / "C.java").write_bytes(after)
            changes = compare_inventories(inventory_tree(left, stable=True),
                                          inventory_tree(right, stable=True))["declaration_changes"]
            self.assertEqual(tuple(len(changes[k]) for k in
                                   ("added", "removed", "modified", "unchanged")),
                             (0, 0, 0, 2))
    def test_nearby_javadoc_terms_find_opaque_method_name(self):
        source = b"class C { /** Reconcile overdue invoices. */\n void run(){} }\n"
        result = self._index(source)
        self.assertIn("overdue invoices", result["functions"][0]["docs"])
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "Fixture.java"
            path.write_bytes(source)
            self.assertEqual(query_path(path, "overdue invoices")["matches"][0]["name"], "run")
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

    def test_overload_identity_survives_insert_remove_reorder_and_signature_edit(self):
        base = b"class C { int f(int x){return 1;} int f(String x){return 2;} }\n"
        variants = [
            (b"class C { int f(boolean x){return 0;} int f(int x){return 1;} int f(String x){return 2;} }\n",
             (1, 0, 0, 2)),
            (b"class C { int f(String x){return 2;} int f(int x){return 1;} }\n",
             (0, 0, 0, 2)),
            (b"class C { int f(String x){return 2;} }\n", (0, 1, 0, 1)),
            (b"class C { int f(long x){return 1;} int f(String x){return 2;} }\n",
             (1, 1, 0, 1)),
        ]
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.java").write_bytes(base)
            for candidate, expected in variants:
                (right / "C.java").write_bytes(candidate)
                delta = compare_inventories(inventory_tree(left, stable=True),
                                            inventory_tree(right, stable=True))
                self.assertEqual(delta["status"], "comparable_candidate_delta")
                changes = delta["declaration_changes"]
                self.assertEqual(tuple(len(changes[k]) for k in
                                       ("added", "removed", "modified", "unchanged")), expected)
                for item in changes["unchanged"]:
                    self.assertEqual(item["planning"]["signature"], item["candidate"]["signature"])

    def test_identical_syntactic_signatures_are_explicitly_ambiguous(self):
        source = b"class C { int f(int x){return 1;} int f(int y){return 2;} }\n"
        entries = [item for item in self._index(source)["functions"]
                   if item["qualified_name"] == "C.f"]
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(item["identity_ambiguous"] for item in entries))
        changed = b"class C { int f(int y){return 2;} int f(int x){return 1;} }\n"
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.java").write_bytes(source)
            (right / "C.java").write_bytes(changed)
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            changes = delta["declaration_changes"]
            self.assertEqual((len(changes["added"]), len(changes["removed"]),
                              len(changes["modified"]), len(changes["unchanged"])),
                             (2, 2, 0, 0))


if __name__ == "__main__":
    unittest.main()
