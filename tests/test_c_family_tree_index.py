"""C/C++ raw-source definitions, prototypes and preprocessing limits."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import index_file


class CFamilyTests(unittest.TestCase):
    def test_cpp_variadic_overloads_are_not_ambiguous(self):
        source = b"int F(int x) {return 1;} int F(int x, ...) {return 2;}"
        entries = self._index(".cpp", source)["functions"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(len({entry["identity_signature"] for entry in entries}), 2)
        self.assertFalse(any(entry["identity_ambiguous"] for entry in entries))
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "f.cpp").write_bytes(source)
            (right / "f.cpp").write_bytes(b"// unrelated\n" + source)
            changes = compare_inventories(inventory_tree(left, stable=True),
                                          inventory_tree(right, stable=True))["declaration_changes"]
            self.assertEqual(tuple(len(changes[key]) for key in
                                   ("added", "removed", "modified", "unchanged")),
                             (0, 0, 0, 2))

    def test_parenthesized_c_declarator_is_mapped(self):
        source = b"int (F)(int x) {return x;}"
        result = self._index(".c", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual([entry["name"] for entry in result["functions"]], ["F"])

    def test_function_pointer_declarators_and_callback_rename(self):
        source = (b"int (*Factory(void))(int) { return 0; }\n"
                  b"void Use(int (*callback)(int)) {}\n")
        result = self._index(".c", source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual({entry["name"] for entry in result["functions"]},
                         {"Factory", "Use"})
        renamed = self._index(".c", source.replace(b"callback", b"handler"))
        use = next(entry for entry in result["functions"] if entry["name"] == "Use")
        use_renamed = next(entry for entry in renamed["functions"] if entry["name"] == "Use")
        self.assertEqual(use["declaration_id"], use_renamed["declaration_id"])

    def test_deleted_member_does_not_hide_default_argument_lambda(self):
        source = b"struct C { void f(int x = [](){return 1;}()) = delete; };"
        result = self._index(".cpp", source)
        self.assertEqual(result["function_count"], 1)
        self.assertEqual(result["functions"][0]["declaration_kind"], "lambda")
        entry = result["functions"][0]
        self.assertEqual(source[entry["byte_range"]["start"]:entry["byte_range"]["end"]],
                         b"[](){return 1;}")

    def test_reference_return_and_parameter_name_are_mapped(self):
        before = self._index(".cpp", b"int &get(int &x) {return x;}")
        after = self._index(".cpp", b"int &get(int &renamed) {return renamed;}")
        self.assertEqual(before["function_count"], 1)
        self.assertEqual(before["functions"][0]["name"], "get")
        self.assertEqual(before["functions"][0]["declaration_id"],
                         after["functions"][0]["declaration_id"])

    def test_parameter_comment_does_not_change_identity(self):
        plain = self._index(".cpp", b"int add(int a, int b) {return a+b;}")
        commented = self._index(".cpp", b"int add(int a, /* note */ int b) {return a+b;}")
        self.assertEqual(plain["functions"][0]["declaration_id"],
                         commented["functions"][0]["declaration_id"])

    def test_constructor_try_body_and_intentionally_bodyless_members(self):
        source = (b"struct C { C(); C(const C&) = delete; C(C&&) = default; };\n"
                  b"C::C() try {} catch(...) {}\n")
        indexed = self._index(".cpp", source)
        self.assertEqual(indexed["mapping_status"], "navigation_only")
        self.assertEqual(indexed["adapter_coverage"]["unhandled_node_count"], 0)
        self.assertGreaterEqual(indexed["adapter_coverage"]["bodyless_excluded_count"], 2)
        self.assertEqual([(entry["qualified_name"], entry["declaration_kind"])
                          for entry in indexed["functions"]], [("C.C", "constructor")])
        entry = indexed["functions"][0]
        self.assertEqual(source[entry["byte_range"]["start"]:entry["byte_range"]["end"]],
                         b"C::C() try {} catch(...) {}")

    def test_pure_virtual_declaration_is_explicitly_bodyless(self):
        result = self._index(".cpp", b"struct I { virtual int f() = 0; };\n")
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["function_count"], 0)
        self.assertGreaterEqual(result["adapter_coverage"]["bodyless_excluded_count"], 1)

    def test_qualified_conversion_uses_terminal_declarator(self):
        source = b"struct C { operator int(); }; C::operator int() { return 1; }\n"
        entries = self._index(".cpp", source)["functions"]
        self.assertEqual([(entry["qualified_name"], entry["declaration_kind"])
                          for entry in entries], [("C.operator int", "conversion")])

    def test_type_token_boundaries_do_not_create_false_ambiguity(self):
        source = (b"using unsignedint = double;\n"
                  b"int choose(unsigned int x) { return 1; }\n"
                  b"int choose(unsignedint x) { return 2; }\n")
        entries = self._index(".cpp", source)["functions"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(len({entry["declaration_id"] for entry in entries}), 2)
        self.assertFalse(any(entry["identity_ambiguous"] for entry in entries))
        after = (b"// unrelated\nusing unsignedint = double;\n"
                 b"int choose(unsignedint renamed) { return 2; }\n"
                 b"int choose(unsigned /* trivia */ int other) { return 1; }\n")
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "f.cpp").write_bytes(source)
            (right / "f.cpp").write_bytes(after)
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual(len(delta["declaration_changes"]["added"]), 0)
            self.assertEqual(len(delta["declaration_changes"]["removed"]), 0)
            self.assertEqual(len(delta["declaration_changes"]["modified"]), 2)

    def test_template_friend_range_includes_constraint(self):
        prefix = b"struct C {\n"
        suffix = b"\n};\n"
        hashes = []
        for bound in (b"1", b"2"):
            declaration = (b"template<class T> requires(sizeof(T)>" + bound + b")\n"
                           b"friend int choose(C, T) { return 1; }")
            source = prefix + declaration + suffix
            indexed = self._index(".cpp", source)
            self.assertEqual(indexed["mapping_status"], "navigation_only")
            self.assertEqual(indexed["function_count"], 1)
            entry = indexed["functions"][0]
            span = entry["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]], declaration)
            hashes.append(entry["declaration_sha256"])
        self.assertNotEqual(hashes[0], hashes[1])

    def test_member_qualifiers_distinguish_overloads(self):
        before = b"struct C { int f() & {return 1;} int f() const & {return 2;} };\n"
        indexed = self._index(".cpp", before)
        self.assertEqual({before[e["byte_range"]["start"]:e["byte_range"]["end"]]
                          for e in indexed["functions"]},
                         {b"int f() & {return 1;}", b"int f() const & {return 2;}"})
        self.assertFalse(any(e.get("identity_ambiguous") for e in indexed["functions"]))
        after = (b"// unrelated\nstruct C { int f() const & {return 2;} "
                 b"int f() & {return 1;} };\n")
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.cpp").write_bytes(before)
            (right / "C.cpp").write_bytes(after)
            changes = compare_inventories(inventory_tree(left, stable=True),
                                          inventory_tree(right, stable=True))["declaration_changes"]
            self.assertEqual(tuple(len(changes[k]) for k in
                                   ("added", "removed", "modified", "unchanged")),
                             (0, 0, 0, 2))

    def test_out_of_class_special_members_use_terminal_declarator_kind(self):
        source = (b"struct C { C(); ~C(); C operator+(const C&) const; };\n"
                  b"C::C(){}\n"
                  b"C::~C(){}\n"
                  b"C C::operator+(const C& other) const {return *this;}\n")
        indexed = self._index(".cpp", source)
        self.assertEqual({(e["qualified_name"], e["declaration_kind"],
                           source[e["byte_range"]["start"]:e["byte_range"]["end"]])
                          for e in indexed["functions"]},
                         {("C.C", "constructor", b"C::C(){}"),
                          ("C.~C", "destructor", b"C::~C(){}"),
                          ("C.operator+", "operator",
                           b"C C::operator+(const C& other) const {return *this;}")})
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.cpp").write_bytes(source)
            (right / "C.cpp").write_bytes(b"// unrelated\n" + source)
            changes = compare_inventories(inventory_tree(left, stable=True),
                                          inventory_tree(right, stable=True))["declaration_changes"]
            self.assertEqual(tuple(len(changes[k]) for k in
                                   ("added", "removed", "modified", "unchanged")),
                             (0, 0, 0, 3))
    def test_spaced_operator_is_not_conversion(self):
        result = self._index(".cpp", b"struct C { C operator +(const C&) { return *this; } };\n")
        self.assertEqual([(item["qualified_name"], item["declaration_kind"])
                          for item in result["functions"]], [("C.operator +", "operator")])

    def test_pointer_reference_overloads_survive_insert_and_reorder(self):
        before = b"struct C { int f(int* p){return 1;} int f(int& r){return 2;} };\n"
        after = (b"struct C { int f(double d){return 3;} int f(int& r){return 2;} "
                 b"int f(int* p){return 1;} };\n")
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir(); right.mkdir()
            (left / "C.cpp").write_bytes(before)
            (right / "C.cpp").write_bytes(after)
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            changes = delta["declaration_changes"]
            self.assertEqual(tuple(len(changes[key]) for key in
                                   ("added", "removed", "modified", "unchanged")),
                             (1, 0, 0, 2))
            self.assertEqual({item["planning"]["signature"] for item in changes["unchanged"]},
                             {item["candidate"]["signature"] for item in changes["unchanged"]})
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
