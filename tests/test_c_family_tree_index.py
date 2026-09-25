"""C/C++ raw-source definitions, prototypes and preprocessing limits."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import index_file


class CFamilyTests(unittest.TestCase):
    def _index(self, suffix: str, source: bytes, *, language=None) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / f"fixture{suffix}"
            path.write_bytes(source)
            return index_file(path, language=language)

    def _exact(self, result: dict, source: bytes) -> None:
        functions = result["functions"]
        self.assertEqual(result["adapter_coverage"]["promised_node_count"], len(functions))
        self.assertEqual(result["structural"]["declaration_count"], len(functions))
        self.assertEqual(len({item["declaration_id"] for item in functions}), len(functions))
        for item in functions:
            span = item["byte_range"]
            self.assertEqual(item["declaration_sha256"], hashlib.sha256(
                source[span["start"]:span["end"]]).hexdigest())

    def test_c_definitions_prototypes_and_preprocessing(self):
        source = (b"int f(int x){return x;} int g(int);\n"
                  b"#if FEATURE\nint h(){return 1;}\n#endif\n"
                  b"#define MAKE(x) int x(){return 2;}\n"
                  b"MAKE(foo);\n")
        result = self._index(".c", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual({item["name"] for item in result["functions"]}, {"f", "h"})
        self.assertGreaterEqual(result["adapter_coverage"]["bodyless_excluded_count"], 1)
        self.assertGreater(result["preprocessing"]["conditional_count"], 0)
        self.assertEqual(result["preprocessing"]["macro_definition_count"], 1)
        self.assertGreaterEqual(result["preprocessing"]["macro_invocation_count"], 1)
        self.assertFalse(result["preprocessing"]["effective_program_claim"])
        self._exact(result, source)

    def test_cpp_templates_ownership_friends_operators_and_lambda(self):
        source = (b"namespace N {\n"
                  b"template<class T> T f(T x){return x;}\n"
                  b"class C { public: C(){} ~C(){} operator int(){return 1;}\n"
                  b" C operator+(const C& other){return *this;}\n"
                  b" friend int friend_fn(C c){return 1;} };\n"
                  b"class Outer { class Inner { template<class T> T member(T x){return x;} }; };\n"
                  b"auto l=[](int x){return x;};\n"
                  b"extern \"C\" { int exported(){return 1;} }\n"
                  b"int C::outside(){return 1;}\n"
                  b"}\n")
        result = self._index(".cpp", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        by_name = {item["qualified_name"]: item for item in result["functions"]}
        self.assertIn("N.f", by_name)
        self.assertIn("N.C.C", by_name)
        self.assertIn("N.C.~C", by_name)
        self.assertIn("N.friend_fn", by_name)
        self.assertIn("N.exported", by_name)
        self.assertIn("N.C.outside", by_name)
        self.assertIn("N.C.operator int", by_name)
        self.assertIn("N.C.operator+", by_name)
        self.assertIn("N.Outer.Inner.member", by_name)
        self.assertTrue(source[by_name["N.f"]["byte_range"]["start"]:].startswith(b"template"))
        self.assertEqual(len([item for item in result["functions"] if item["anonymous"]]), 1)
        self._exact(result, source)

    def test_header_override_and_directory_policy(self):
        source = b"inline int f(){return 1;}\n"
        self.assertEqual(self._index(".h", source)["mapping_status"], "unsupported")
        self.assertEqual(self._index(".h", source, language="c")["function_count"], 1)
        self.assertEqual(self._index(".h", source, language="cpp")["function_count"], 1)
        self.assertEqual(self._index(".hpp", source)["function_count"], 1)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "x.h").write_bytes(source)
            (root / "x.cpp").write_bytes(source)
            scan = inventory_tree(root, stable=True)
            self.assertEqual(scan["status"], "complete")
            self.assertEqual([item["path"] for item in scan["files"]], ["x.cpp"])

    def test_function_pointer_variable_is_not_a_prototype(self):
        source = b"int f(int); int (*fp)(int); int (*factory(void))(int);\n"
        result = self._index(".c", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["adapter_coverage"]["bodyless_excluded_count"], 2)
        self.assertEqual(result["function_count"], 0)

    def test_syntax_error_and_raw_delta(self):
        broken = self._index(".cpp", b"int okay(){} int broken(\n")
        self.assertEqual(broken["mapping_status"], "incomplete")
        with tempfile.TemporaryDirectory() as raw:
            before, after = Path(raw) / "before", Path(raw) / "after"
            before.mkdir()
            after.mkdir()
            (before / "x.c").write_text("#if A\nint f(){return 1;}\n#endif\n")
            (after / "x.c").write_text("#if B\nint f(){return 1;}\n#endif\n")
            delta = compare_inventories(inventory_tree(before, stable=True),
                                        inventory_tree(after, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual(len(delta["file_changes"]["modified"]), 1)


if __name__ == "__main__":
    unittest.main()
