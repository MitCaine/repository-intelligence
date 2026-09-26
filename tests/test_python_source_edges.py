"""Independent Python newline, raw-byte and native-name handoff oracles."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence import structural
from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.python_index import index_source as native_index_source
from repository_intelligence.python_tree_index import index_source as tree_index_source
from repository_intelligence.scan import index_file


class PythonSourceEdgeTests(unittest.TestCase):
    def index_both(self, source):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.py"
            path.write_bytes(source)
            structural = index_file(path)
            native = native_index_source(path, source)
        self.assertEqual(structural["mapping_status"], "navigation_only")
        self.assertEqual(structural["raw_sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(native["raw_sha256"], hashlib.sha256(source).hexdigest())
        return structural["functions"], native["functions"]

    def assert_entry(self, source, entry, *, name, qualified, line, end_line, text):
        self.assertEqual(entry["name"], name)
        self.assertEqual(entry["qualified_name"], qualified)
        self.assertEqual(entry["line"], line)
        self.assertEqual(entry["end_line"], end_line)
        start = source.index(text)
        self.assertEqual(entry["byte_range"], {"start": start, "end": start + len(text)})
        self.assertEqual(entry["declaration_sha256"], hashlib.sha256(text).hexdigest())

    def test_comment_and_decorator_with_every_python_line_ending(self):
        for newline in (b"\n", b"\r\n", b"\r"):
            with self.subTest(newline=newline):
                body = newline.join((b"@cache", b"def target(", b"    value=3,",
                                     b"): ", b"    return value"))
                source = b"# preamble" + newline + body + newline
                for entries in self.index_both(source):
                    self.assertEqual(len(entries), 1)
                    self.assert_entry(source, entries[0], name="target", qualified="target",
                                      line=3, end_line=6, text=body)
                    self.assertEqual(entries[0]["signature"],
                                     newline.join((b"def target(", b"    value=3,", b"):"))
                                     .decode())

    def test_mixed_newlines_preserve_bom_and_raw_byte_spans(self):
        text = b"@cache\rdef target():\r\n    return 'caf\xc3\xa9'"
        source = b"\xef\xbb\xbf# preamble\n" + text + b"\r"
        for entries in self.index_both(source):
            self.assertEqual(len(entries), 1)
            self.assert_entry(source, entries[0], name="target", qualified="target",
                              line=3, end_line=4, text=text)

    def test_declared_encoding_with_mixed_newlines_and_unicode(self):
        text = b"@cache\r\ndef target():\r    return 'caf\xe9'"
        source = b"# coding: latin-1\n# preamble\r" + text + b"\n"
        for entries in self.index_both(source):
            self.assertEqual(len(entries), 1)
            self.assert_entry(source, entries[0], name="target", qualified="target",
                              line=4, end_line=5, text=text)

    def test_direct_adapter_keeps_existing_declared_encoding_interface(self):
        source = b"# coding: latin-1\ndef target(value='caf\xe9'): return value\n"
        _, tree, parse_bytes, offsets = structural.scan(".py", source)
        result = tree_index_source(Path("source.py"), source, tree=tree,
                                   parse_bytes=parse_bytes, offsets=offsets)
        self.assertEqual(result["functions"][0]["signature"], "def target(value='café'):")

    def test_second_line_encoding_cookie_with_cr_only_lines(self):
        text = b"def target(): return 'caf\xe9'"
        source = b"# preamble\r# coding: latin-1\r" + text + b"\r"
        for entries in self.index_both(source):
            self.assertEqual(len(entries), 1)
            self.assert_entry(source, entries[0], name="target", qualified="target",
                              line=3, end_line=3, text=text)

    def test_trailing_comment_is_a_documented_provider_envelope_difference(self):
        source = b"def target():\n    return 3  # trailing explanation\n"
        structural, native = self.index_both(source)
        self.assert_entry(source, structural[0], name="target", qualified="target",
                          line=1, end_line=2,
                          text=b"def target():\n    return 3  # trailing explanation")
        self.assert_entry(source, native[0], name="target", qualified="target",
                          line=1, end_line=2, text=b"def target():\n    return 3")

    def test_stateful_encoding_newlines_keep_trailing_return_bytes(self):
        text = b"def target():\r\n    return \x1b(B123"
        source = b"# coding: iso2022_jp\n" + text + b"\r"
        for entries in self.index_both(source):
            self.assert_entry(source, entries[0], name="target", qualified="target",
                              line=2, end_line=3, text=text)

    def test_universal_newlines_inside_docstrings_match_python(self):
        text = b'def target():\r    """First.\r\n\r    Last."""\r    return 3'
        source = text + b"\r"
        for entries in self.index_both(source):
            self.assert_entry(source, entries[0], name="target", qualified="target",
                              line=1, end_line=5, text=text)
            self.assertEqual(entries[0]["docs"], "First.\n\nLast.")

    def test_nfkc_function_async_and_class_names_match_python_identifiers(self):
        source = ("def K(): return 1\n"
                  "class Ｃ:\n"
                  "    async def ｘ(self):\n"
                  "        def a\u0301(): return 2\n"
                  "        return a\u0301()\n").encode()
        expected = [
            ("K", "K", 1, 1, "def K(): return 1"),
            ("x", "C.x", 3, 5,
             "async def ｘ(self):\n        def a\u0301(): return 2\n        return a\u0301()"),
            ("á", "C.x.á", 4, 4, "def a\u0301(): return 2"),
        ]
        for entries in self.index_both(source):
            self.assertEqual(len(entries), len(expected))
            for entry, (name, qualified, line, end_line, text) in zip(entries, expected):
                self.assert_entry(source, entry, name=name, qualified=qualified,
                                  line=line, end_line=end_line, text=text.encode())
        self.assertEqual(self.index_both(source)[1][0]["signature"], "def K():")

    def test_cr_only_body_change_reaches_inventory_delta(self):
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "planning", Path(raw) / "candidate"
            left.mkdir()
            right.mkdir()
            (left / "source.py").write_bytes(b"# preamble\rdef target(): return 1\r")
            (right / "source.py").write_bytes(b"# preamble\rdef target(): return 2\r")
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
        self.assertEqual(delta["status"], "comparable_candidate_delta")
        self.assertEqual([item["path"] for item in delta["file_changes"]["modified"]],
                         ["source.py"])
        self.assertEqual([item["declaration_id"]
                          for item in delta["declaration_changes"]["modified"]],
                         ["function:target#0"])
        self.assertEqual(delta["declaration_changes"]["added"], [])
        self.assertEqual(delta["declaration_changes"]["removed"], [])

    def test_nfkc_aliases_are_ambiguous_named_declarations(self):
        source = "def K(): return 1\ndef K(): return 2\n".encode()
        for entries in self.index_both(source):
            self.assertEqual([entry["qualified_name"] for entry in entries], ["K", "K"])
            self.assertTrue(all(entry["identity_ambiguous"] for entry in entries))
            self.assertEqual([entry["declaration_id"] for entry in entries],
                             ["function:K#0", "function:K#1"])


if __name__ == "__main__":
    unittest.main()
