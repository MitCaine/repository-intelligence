"""Language-specific line terminators retain exact original source envelopes."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence import structural
from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.scan import index_file


class SourceLineEndingTests(unittest.TestCase):
    def test_cr_crlf_lf_and_mixed_endings_across_selected_grammars(self):
        families = {
            (".js", ".jsx", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".tsx"):
                (b"", b"function target() {", b"  return 1;", b"}", b"", 2, 4),
            (".java", ".cs"):
                (b"class C {", b"int target() {", b"  return 1;", b"}", b"}", 3, 5),
            (".c", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"):
                (b"", b"int target(void) {", b"  return 1;", b"}", b"", 2, 4),
        }
        endings = ((b"\n",), (b"\r\n",), (b"\r",), (b"\r", b"\r\n", b"\n"))
        setup = structural.ScanSetup()
        with tempfile.TemporaryDirectory() as raw:
            for suffixes, (owner, header, body, end, owner_end, first, last) in families.items():
                rows = [b"// preamble"] + ([owner] if owner else []) + [header, body, end]
                rows += [owner_end] if owner_end else []
                for suffix in suffixes:
                    path = Path(raw) / ("source" + suffix)
                    for sequence in endings:
                        with self.subTest(suffix=suffix, endings=sequence):
                            source = b"".join(row + sequence[i % len(sequence)]
                                              for i, row in enumerate(rows))
                            path.write_bytes(source)
                            result = index_file(path, object_format=None, scan_setup=setup)
                            self.assertEqual(result["mapping_status"], "navigation_only")
                            self.assertEqual(result["raw_sha256"], hashlib.sha256(source).hexdigest())
                            self.assertEqual([item["name"] for item in result["functions"]], ["target"])
                            entry = result["functions"][0]
                            start = source.index(header)
                            finish = source.index(body) + len(body) + len(sequence[first % len(sequence)]) + len(end)
                            self.assertEqual(entry["byte_range"], {"start": start, "end": finish})
                            self.assertEqual(entry["declaration_sha256"],
                                             hashlib.sha256(source[start:finish]).hexdigest())
                            self.assertEqual((entry["line"], entry["end_line"]), (first, last))
                            self.assertEqual(entry["column"], 1)

    def test_cr_comment_cannot_hide_java_or_cpp_declaration_delta(self):
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "planning", Path(raw) / "candidate"
            left.mkdir()
            right.mkdir()
            for root, value in ((left, b"1"), (right, b"2")):
                (root / "source.java").write_bytes(
                    b"// preamble\rclass C { int target() { return " + value + b"; } }\r")
                (root / "source.cpp").write_bytes(
                    b"// preamble\rint target() { return " + value + b"; }\r")
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
        self.assertEqual(delta["status"], "comparable_candidate_delta")
        self.assertEqual([item["path"] for item in delta["declaration_changes"]["modified"]],
                         ["source.cpp", "source.java"])
        self.assertEqual(delta["declaration_changes"]["added"], [])
        self.assertEqual(delta["declaration_changes"]["removed"], [])

    def test_rust_and_go_do_not_treat_lone_cr_as_a_line_comment_terminator(self):
        sources = {
            ".rs": b"// hidden\rfn hidden() {}\nfn target() {}\n",
            ".go": b"package example\n// hidden\rfunc hidden() {}\nfunc target() {}\n",
        }
        with tempfile.TemporaryDirectory() as raw:
            for suffix, source in sources.items():
                with self.subTest(suffix=suffix):
                    path = Path(raw) / ("source" + suffix)
                    path.write_bytes(source)
                    result = index_file(path, object_format=None)
                    self.assertEqual(result["mapping_status"], "navigation_only")
                    self.assertEqual([item["name"] for item in result["functions"]], ["target"])
                    _, _, parse_bytes, _ = structural.scan(suffix, source)
                    self.assertEqual(parse_bytes, source)

    def test_rust_and_go_columns_count_lone_cr_as_whitespace(self):
        sources = {
            ".rs": (b" \rfn target() {}\n", 1, 6),
            ".go": (b"package example\n \rfunc target() {}\n", 2, 3),
        }
        with tempfile.TemporaryDirectory() as raw:
            for suffix, (source, line, column) in sources.items():
                with self.subTest(suffix=suffix):
                    path = Path(raw) / ("source" + suffix)
                    path.write_bytes(source)
                    result = index_file(path, object_format=None)
                    self.assertEqual(result["mapping_status"], "navigation_only")
                    entry = result["functions"][0]
                    self.assertEqual((entry["name"], entry["line"], entry["column"]),
                                     ("target", line, column))

    def test_unicode_separators_in_literals_are_not_rewritten(self):
        source = 'const value = "\u2028\u2029";\rfunction target(){return value;}\r'.encode()
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.js"
            path.write_bytes(source)
            result = index_file(path, object_format=None)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["functions"][0]["line"], 2)
        _, _, parse_bytes, _ = structural.scan(".js", source)
        self.assertIn("\u2028\u2029".encode(), parse_bytes)
        self.assertEqual(len(parse_bytes), len(source))


if __name__ == "__main__":
    unittest.main()
