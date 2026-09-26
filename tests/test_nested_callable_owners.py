"""Nested callable identities retain the source discriminator of their owner."""

import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree


class NestedCallableOwnerTests(unittest.TestCase):
    def _assert_owner_deltas(self, filename, source, expected, modified):
        with tempfile.TemporaryDirectory() as raw:
            planning, candidate = Path(raw) / "planning", Path(raw) / "candidate"
            planning.mkdir()
            candidate.mkdir()
            (planning / filename).write_bytes(source)
            baseline = inventory_tree(planning, stable=True)
            self.assertEqual(baseline["status"], "complete")
            entries = baseline["files"][0]["declarations"]
            self.assertEqual([(entry["declaration_kind"], entry["qualified_name"],
                               source[entry["byte_range"]["start"]:entry["byte_range"]["end"]])
                              for entry in entries], expected)
            self.assertFalse(any(entry.get("identity_ambiguous") for entry in entries))
            for label, changed, counts in (
                    ("comment", b"// unrelated\n" + source, (0, 0, 0, len(expected))),
                    ("body", source.replace(b"return 11;", b"return 99;"),
                     (0, 0, 2, len(expected) - 2))):
                with self.subTest(edit=label):
                    (candidate / filename).write_bytes(changed)
                    delta = compare_inventories(baseline, inventory_tree(candidate, stable=True))
                    self.assertEqual(delta["status"], "comparable_candidate_delta")
                    changes = delta["declaration_changes"]
                    self.assertEqual(tuple(len(changes[key]) for key in
                                           ("added", "removed", "modified", "unchanged")), counts)
                    if label == "body":
                        self.assertEqual({(item["candidate"]["declaration_kind"],
                                           item["candidate"]["qualified_name"])
                                          for item in changes["modified"]}, modified)

    def test_js_and_ts_getter_setter_helpers_have_distinct_owners(self):
        getter = b"get value() { function helper(){return 11;} return helper(); }"
        setter = b"set value(x) { function helper(){return 22;} helper(); }"
        for suffix in (".js", ".ts"):
            for container in ("class", "object"):
                for static in ((False, True) if container == "class" else (False,)):
                    with self.subTest(suffix=suffix, container=container, static=static):
                        prefix = b"static " if static else b""
                        source = ((b"class C { " + prefix + getter + b" " + prefix + setter + b" }")
                                  if container == "class" else
                                  b"const C = { " + getter + b", " + setter + b" };" )
                        expected = [
                            ("getter", "C.value", prefix + getter),
                            ("function", "C.value.helper", b"function helper(){return 11;}"),
                            ("setter", "C.value", prefix + setter),
                            ("function", "C.value.helper", b"function helper(){return 22;}"),
                        ]
                        self._assert_owner_deltas("C" + suffix, source, expected,
                                                  {("getter", "C.value"),
                                                   ("function", "C.value.helper")})

    def test_cpp_local_class_methods_inherit_overload_qualifiers_and_templates(self):
        first_body = b"{ struct Local { int run(){return 11;} }; return 1; }"
        second_body = b"{ struct Local { int run(){return 22;} }; return 2; }"
        for label, first, second, opening, closing, outer, nested in (
                ("parameters", b"int F(int x) ", b"int F(double x) ", b"", b"", "F", "F.Local.run"),
                ("const", b"int F() ", b"int F() const ", b"struct C { ", b" };", "C.F", "C.F.Local.run"),
                ("specializations", b"template<> int F<1>() ", b"template<> int F<2>() ",
                 b"template<int N> int F();\n", b"", "F", "F.Local.run")):
            with self.subTest(label=label):
                source = opening + first + first_body + b" " + second + second_body + closing
                expected = [
                    ("function", outer, first + first_body),
                    ("function", nested, b"int run(){return 11;}"),
                    ("function", outer, second + second_body),
                    ("function", nested, b"int run(){return 22;}"),
                ]
                self._assert_owner_deltas("C.cpp", source, expected,
                                          {("function", outer), ("function", nested)})


if __name__ == "__main__":
    unittest.main()
