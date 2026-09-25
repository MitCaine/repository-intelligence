"""Go source-level callable, receiver and anonymous literal fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file


class GoTreeIndexTests(unittest.TestCase):
    def _index(self, source: bytes) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.go"
            path.write_bytes(source)
            return index_file(path)

    def test_package_generics_receivers_and_nested_literals(self):
        source = (b"package demo\n"
                  b"func init() {}\n"
                  b"func Identity[T any](x T) T { return x }\n"
                  b"type S struct{}\n"
                  b"func (s S) Read() {}\n"
                  b"func (s *S) Run() { f := func(x int) int { return x }; _ = func(){ _ = func(){} } }\n"
                  b"type I interface { Run(x int) error }\n")
        result = self._index(source)
        self.assertEqual(result["mapping_status"], "navigation_only")
        functions = result["functions"]
        self.assertEqual(result["adapter_coverage"]["bodyless_excluded_count"], 1)
        self.assertEqual(result["structural"]["declaration_count"], len(functions))
        self.assertEqual(result["adapter_coverage"]["promised_node_count"], len(functions))
        self.assertEqual(len({item["declaration_id"] for item in functions}), len(functions))
        self.assertEqual({item["qualified_name"] for item in functions if not item["anonymous"]},
                         {"demo.init", "demo.Identity", "demo.S.Read", "demo.*S.Run"})
        self.assertEqual(len([item for item in functions if item["anonymous"]]), 3)
        self.assertEqual(result["bodyless_declarations"][0]["owner"], "I")
        for item in functions:
            span = item["byte_range"]
            self.assertEqual(item["declaration_sha256"], hashlib.sha256(
                source[span["start"]:span["end"]]).hexdigest())

    def test_invalid_source_is_incomplete(self):
        result = self._index(b"package p\nfunc Good() {}\nfunc Bad(\n")
        self.assertEqual(result["mapping_status"], "incomplete")
        self.assertGreater(result["structural"]["error_count"] +
                           result["structural"]["missing_count"], 0)


if __name__ == "__main__":
    unittest.main()
