"""Cross-representation evidence and syntax-identity interaction regressions."""

import copy
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree


class FollowupConsistencyTests(unittest.TestCase):
    def _pair(self, filename: str, before: bytes, after: bytes):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        left, right = Path(temporary.name) / "left", Path(temporary.name) / "right"
        left.mkdir(); right.mkdir()
        (left / filename).write_bytes(before)
        (right / filename).write_bytes(after)
        return inventory_tree(left, stable=True), inventory_tree(right, stable=True)

    def _unchanged_after_comment(self, filename: str, source: bytes, count: int):
        planning, candidate = self._pair(filename, source, b"// unrelated\n" + source)
        before = planning["files"][0]["declarations"]
        after = candidate["files"][0]["declarations"]
        self.assertEqual(len(before), count)
        self.assertEqual(len(after), count)
        self.assertFalse(any(item.get("identity_ambiguous") for item in before + after))
        delta = compare_inventories(planning, candidate)
        self.assertEqual(delta["status"], "comparable_candidate_delta")
        changes = delta["declaration_changes"]
        self.assertEqual(tuple(len(changes[key]) for key in
                               ("added", "removed", "modified", "unchanged")),
                         (0, 0, 0, count))

    def test_structural_hash_disagreement_is_incompatible(self):
        planning, candidate = self._pair(
            "file.py", b"def one(): return 1\ndef two(): return 2\n",
            b"def one(): return 1\ndef two(): return 3\n")
        self.assertEqual(len(compare_inventories(planning, candidate)
                             ["declaration_changes"]["modified"]), 1)
        stale = copy.deepcopy(candidate)
        prior = next(item for item in planning["files"][0]["declarations"]
                     if item["name"] == "two")
        record = next(item for item in stale["files"][0]["declarations"]
                      if item["name"] == "two")
        record["declaration_sha256"] = prior["declaration_sha256"]
        self.assertEqual(compare_inventories(planning, stale)["status"], "incompatible")

    def test_bounded_structural_projection_remains_comparable(self):
        source = b"".join(f"def f{index}(): return {index}\n".encode()
                          for index in range(101))
        planning, candidate = self._pair("many.py", source, source)
        file = candidate["files"][0]
        self.assertEqual(len(file["declarations"]), 101)
        self.assertEqual(len(file["structural"]["declarations"]), 100)
        self.assertTrue(file["structural"]["details_truncated"])
        self.assertEqual(compare_inventories(planning, candidate)["status"],
                         "comparable_candidate_delta")

    def test_static_callable_fields_keep_identity_in_js_and_ts(self):
        source = b"class C { run = () => 1; static run = () => 2; }\n"
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix):
                self._unchanged_after_comment("fields" + suffix, source, 2)

    def test_nested_helpers_inherit_static_owner_identity(self):
        source = (b"class C { run() { function helper() { return 1; } return helper(); } "
                  b"static run() { function helper() { return 2; } return helper(); } }\n")
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix):
                self._unchanged_after_comment("nested" + suffix, source, 4)

    def test_cpp_conversion_qualifiers_are_distinct(self):
        source = (b"struct C { operator int() {return 1;} "
                  b"operator int() const {return 2;} };\n")
        self._unchanged_after_comment("conversions.cpp", source, 2)

    def test_cpp_specialization_arguments_are_distinct(self):
        source = (b"template<int N> int choose();\n"
                  b"template<> int choose<1>() {return 1;}\n"
                  b"template<> int choose<2>() {return 2;}\n")
        self._unchanged_after_comment("specializations.cpp", source, 2)


if __name__ == "__main__":
    unittest.main()
