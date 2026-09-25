"""Tree-sitter feasibility fixtures, without a completeness claim."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file
from repository_intelligence.structural import probe


class StructuralTests(unittest.TestCase):
    def test_python_async_nested_method_decorator_and_lambda(self):
        source = (b"@cache\nasync def outer(x):\n"
                  b"    class C:\n"
                  b"        def method(self): return lambda y: y + x\n"
                  b"    def inner(): return x\n")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.py"
            path.write_bytes(source)
            result = index_file(path)
            syntax = result["structural"]
            self.assertEqual(result["mapping_status"], "navigation_only")
            self.assertEqual(syntax["parser"]["runtime_version"], "0.25.0")
            self.assertEqual(syntax["parser"]["grammar_version"], "0.25.0")
            self.assertEqual(syntax["parser"]["adapter_version"], 1)
            self.assertEqual(syntax["coverage"], "partial_navigation_evidence")
            self.assertEqual(syntax["error_count"], 0)
            self.assertEqual(syntax["missing_count"], 0)
            self.assertEqual([(entry["kind"], entry["name"])
                              for entry in syntax["declarations"]],
                             [("function", "outer"), ("function", "method"),
                              ("lambda", None), ("function", "inner")])
            self.assertEqual(len(syntax["declarations"]), result["function_count"])
            span = syntax["declarations"][0]["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]].splitlines()[0], b"@cache")

    def test_rust_generics_methods_attributes_and_closure(self):
        source = (b"#[inline]\n/// doc\nfn outer<T>(x: T) { let c = |y| y; }\n"
                  b"struct S; impl S { fn method(&self) {} }\n")
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.rs"
            path.write_bytes(source)
            result = index_file(path)
            syntax = result["structural"]
            self.assertEqual(result["mapping_status"], "navigation_only")
            self.assertEqual(syntax["parser"]["grammar_version"], "0.24.2")
            self.assertEqual([(entry["kind"], entry["name"])
                              for entry in syntax["declarations"]],
                             [("function", "outer"), ("closure", None),
                              ("function", "method")])
            self.assertEqual(result["function_count"], 2)
            span = syntax["declarations"][0]["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]].splitlines()[0], b"#[inline]")

    def test_declared_latin1_positions_still_bind_raw_bytes(self):
        source = b'# coding: latin-1\nx = "\x85"\ndef target(): return "caf\xe9"\n'
        syntax = probe(".py", source)
        self.assertEqual(syntax["source_encoding"], "iso-8859-1")
        self.assertEqual(syntax["coordinate_space"], "raw_bytes")
        entry = syntax["declarations"][0]
        span = entry["byte_range"]
        self.assertEqual(source[span["start"]:span["end"]],
                         b'def target(): return "caf\xe9"')
        self.assertEqual(entry["declaration_sha256"],
                         hashlib.sha256(source[span["start"]:span["end"]]).hexdigest())

    def test_error_and_missing_nodes_are_reported_as_incomplete(self):
        python_source = b"def broken(:\n"
        python_syntax = probe(".py", python_source)
        self.assertGreater(python_syntax["missing_count"], 0)
        self.assertIn("MISSING", {item["kind"] for item in python_syntax["diagnostics"]})
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "broken.py"
            path.write_bytes(python_source)
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertGreater(result["structural"]["missing_count"], 0)

        rust_source = b"fn broken( {\n"
        rust_syntax = probe(".rs", rust_source)
        self.assertGreater(rust_syntax["error_count"], 0)
        self.assertIn("ERROR", {item["kind"] for item in rust_syntax["diagnostics"]})
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "broken.rs"
            path.write_bytes(rust_source)
            result = index_file(path)
            self.assertEqual(result["mapping_status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
