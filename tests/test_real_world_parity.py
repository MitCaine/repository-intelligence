"""Compare useful navigation fields on RI's own nontrivial Python modules."""

import hashlib
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file
from repository_intelligence.python_index import index_source as ast_index_source


ROOT = Path(__file__).resolve().parents[1] / "src" / "repository_intelligence"


class RealWorldParityTests(unittest.TestCase):
    def test_ri_python_modules_preserve_ast_navigation_fields(self):
        for path in sorted(ROOT.glob("*.py")):
            with self.subTest(module=path.name):
                source = path.read_bytes()
                current = index_file(path)
                reference = ast_index_source(path, source)
                self.assertEqual(current["mapping_status"], "navigation_only")
                self.assertEqual(current["function_count"], reference["function_count"])
                self.assertEqual(current["adapter_coverage"]["mapped_node_count"],
                                 reference["function_count"])
                for actual, expected in zip(current["functions"], reference["functions"]):
                    for field in ("name", "qualified_name", "line", "column",
                                  "end_line", "signature", "docs", "byte_range",
                                  "declaration_sha256"):
                        self.assertEqual(actual[field], expected[field],
                                         f"{path.name}: {expected['qualified_name']}: {field}")
                    span = actual["byte_range"]
                    self.assertEqual(actual["declaration_sha256"], hashlib.sha256(
                        source[span["start"]:span["end"]]).hexdigest())


if __name__ == "__main__":
    unittest.main()
