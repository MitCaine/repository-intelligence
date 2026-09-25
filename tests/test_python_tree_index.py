"""Tree-sitter Python navigation parity and incomplete recovery fixtures."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file
from repository_intelligence.python_index import index_source as ast_index_source


class PythonTreeNavigationTests(unittest.TestCase):
    def test_async_decorated_nested_method_lambda_and_latin1_parity(self):
        source = ("# coding: latin-1\n"
                  "@cache\n"
                  "async def outer(value: int) -> int:\n"
                  "    \"\"\"Résumé docs.\"\"\"\n"
                  "    class C:\n"
                  "        def method(self): return self.apply(value)\n"
                  "    def inner(): return len(value)\n"
                  "    fn = lambda x: helper(x)\n"
                  "    return value\n").encode("latin-1")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.py"
            path.write_bytes(source)
            current = index_file(path)
            reference = ast_index_source(path, source)
            self.assertEqual(current["parser"]["name"], "tree-sitter")
            self.assertEqual(current["parser"]["grammar_version"], "0.25.0")
            self.assertEqual(current["mapping_status"], "navigation_only")
            self.assertEqual(current["function_count"], reference["function_count"])
            fields = ("name", "qualified_name", "line", "column", "end_line",
                      "signature", "docs", "lexical_call_candidates", "byte_range",
                      "declaration_sha256")
            for old, new in zip(reference["functions"], current["functions"]):
                with self.subTest(symbol=old["qualified_name"]):
                    for field in fields:
                        self.assertEqual(new[field], old[field], field)
                    span = new["byte_range"]
                    self.assertEqual(new["declaration_sha256"],
                                     hashlib.sha256(source[span["start"]:span["end"]]).hexdigest())

    def test_inline_multiline_signature_and_declared_encoding_parity(self):
        source = ("# coding: latin-1\n"
                  "def inline(value: int) -> int: return value\n"
                  "def wrapped(\n"
                  "    value: dict[str, int],\n"
                  ") -> int: return len(value)\n"
                  "def labelled(name: str = 'café') -> str: return name\n").encode("latin-1")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "signatures.py"
            path.write_bytes(source)
            current = index_file(path)
            reference = ast_index_source(path, source)
            self.assertEqual([entry["signature"] for entry in current["functions"]],
                             [entry["signature"] for entry in reference["functions"]])
            self.assertEqual([entry["byte_range"] for entry in current["functions"]],
                             [entry["byte_range"] for entry in reference["functions"]])

    def test_inline_header_comment_and_parenthesized_call_target_parity(self):
        source = b"def f(): # note\n    pass\ndef g(): return (f)()\n"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "comments_and_calls.py"
            path.write_bytes(source)
            current = index_file(path)
            reference = ast_index_source(path, source)
            self.assertEqual(current["mapping_status"], "navigation_only")
            for actual, expected in zip(current["functions"], reference["functions"]):
                with self.subTest(symbol=expected["name"]):
                    self.assertEqual(actual["signature"], expected["signature"])
                    self.assertEqual(actual["lexical_call_candidates"],
                                     expected["lexical_call_candidates"])

    def test_missing_syntax_and_unhandled_recovery_are_not_complete(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "broken.py"
            path.write_bytes(b"def broken(:\n")
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertGreater(result["structural"]["missing_count"], 0)
            self.assertEqual(result["source_identity"]["raw_sha256"],
                             hashlib.sha256(path.read_bytes()).hexdigest())

    def test_error_recovery_keeps_valid_navigation_partial(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "mixed.py"
            path.write_bytes(b"def valid(): return 1\ndef (): pass\n")
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertGreater(result["structural"]["error_count"], 0)
            self.assertEqual([entry["name"] for entry in result["functions"]],
                             ["valid"])


if __name__ == "__main__":
    unittest.main()
