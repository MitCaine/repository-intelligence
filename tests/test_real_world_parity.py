"""Compare useful navigation fields on RI's own nontrivial Python modules."""

import hashlib
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file
from repository_intelligence.python_index import index_source as ast_index_source
from repository_intelligence.search import query, score, tokens


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
                    current_terms = {term for call in actual["lexical_call_candidates"]
                                     for term in tokens(call)}
                    reference_terms = {term for call in expected["lexical_call_candidates"]
                                       for term in tokens(call)}
                    self.assertEqual(current_terms, reference_terms,
                                     f"{path.name}: {expected['qualified_name']}: call search terms")
                    self.assertEqual(actual["lexical_call_candidates"],
                                     expected["lexical_call_candidates"],
                                     f"{path.name}: {expected['qualified_name']}: call presentation")

    def test_call_escape_terms_preserve_navigation_discoverability(self):
        path = ROOT / "source.py"
        source = path.read_bytes()
        current = index_file(path)
        reference = ast_index_source(path, source)
        selected = "identify_bytes"
        current_entry = next(entry for entry in current["functions"] if entry["name"] == selected)
        reference_entry = next(entry for entry in reference["functions"] if entry["name"] == selected)
        for words in (tokens("x00"), tokens("hashlib new")):
            with self.subTest(words=words):
                self.assertEqual(score(current_entry, words), score(reference_entry, words))
        self.assertEqual([entry["name"] for entry in query(current, "x00")["matches"]],
                         [entry["name"] for entry in query(reference, "x00")["matches"]])


if __name__ == "__main__":
    unittest.main()
