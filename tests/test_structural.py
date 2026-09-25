"""Tree-sitter feasibility fixtures, without a completeness claim."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file
from repository_intelligence.structural import probe


class StructuralTests(unittest.TestCase):
    def test_cross_language_expected_callable_slices_and_owners(self):
        cases = [
            (".py", b"class C:\n    def run(self): return 1\n", "C.run", b"def run(self): return 1"),
            (".rs", b"mod m { fn run() {} }\n", "m::run", b"fn run() {}"),
            (".js", b"class C { run(){} }\n", "C.run", b"run(){}"),
            (".ts", b"namespace N { export function run(){} }\n", "N.run", b"function run(){}"),
            (".java", b"class C { void run(){} }\n", "C.run", b"void run(){}"),
            (".go", b"package m\nfunc run() {}\n", "m.run", b"func run() {}"),
            (".cs", b"namespace N; class C { void Run(){} }\n", "N.C.Run", b"void Run(){}"),
            (".cpp", b"struct C { int run(){return 1;} };\n", "C.run", b"int run(){return 1;}"),
        ]
        with tempfile.TemporaryDirectory() as raw:
            for number, (suffix, source, expected_name, expected_slice) in enumerate(cases):
                with self.subTest(suffix=suffix):
                    path = Path(raw) / f"case{number}{suffix}"
                    path.write_bytes(source)
                    result = index_file(path)
                    self.assertEqual(result["mapping_status"], "navigation_only")
                    self.assertEqual([entry["qualified_name"] for entry in result["functions"]],
                                     [expected_name])
                    span = result["functions"][0]["byte_range"]
                    self.assertEqual(source[span["start"]:span["end"]], expected_slice)
                    self.assertEqual(result["structural"]["declaration_count"], 1)
                    self.assertEqual(result["structural"]["declarations"][0]["byte_range"], span)
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
            self.assertEqual(syntax["parser"]["adapter_version"], 5)
            self.assertEqual(syntax["coverage"], "adapter_owned_callable_accounting")
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
            self.assertEqual(result["function_count"], 3)
            span = syntax["declarations"][0]["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]].splitlines()[0], b"#[inline]")

    def test_rust_only_attached_doc_comments_enter_declaration_hash(self):
        cases = [
            (b"// unrelated\nfn f() {}\n", b"fn f() {}"),
            (b"/* unrelated */\nfn f() {}\n", b"fn f() {}"),
            (b"//// ordinary\nfn f() {}\n", b"fn f() {}"),
            (b"//! module docs\nfn f() {}\n", b"fn f() {}"),
            (b"/*! module docs */\nfn f() {}\n", b"fn f() {}"),
            (b"/// function docs\nfn f() {}\n", b"/// function docs\nfn f() {}"),
            (b"/** function docs */\nfn f() {}\n", b"/** function docs */\nfn f() {}"),
            (b"/// separated docs\n\nfn f() {}\n", b"/// separated docs\n\nfn f() {}"),
            (b"#[allow(dead_code)]\n\n// ordinary\nfn f() {}\n",
             b"#[allow(dead_code)]\n\n// ordinary\nfn f() {}"),
            (b"#[inline]\n#[allow(dead_code)]\n\n/// documented\nfn f() {}\n",
             b"#[inline]\n#[allow(dead_code)]\n\n/// documented\nfn f() {}"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                entry = probe(".rs", source)["declarations"][0]
                span = entry["byte_range"]
                self.assertEqual(source[span["start"]:span["end"]], expected)
                self.assertEqual(entry["declaration_sha256"],
                                 hashlib.sha256(expected).hexdigest())

    def test_rust_attribute_edit_changes_declaration_hash_across_gap(self):
        before = b"#[allow(dead_code)]\n\n// explanation\nfn f() {}\n"
        after = before.replace(b"allow", b"deny")
        previous = probe(".rs", before)["declarations"][0]
        current = probe(".rs", after)["declarations"][0]
        self.assertEqual(before[previous["byte_range"]["start"]:
                                previous["byte_range"]["end"]], before[:-1])
        self.assertNotEqual(previous["declaration_sha256"], current["declaration_sha256"])

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
