"""Tests for the shared locator across distinct languages and projects."""

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file, query_path
from repository_intelligence.search import format_tree_compact, tokens


class LocatorTests(unittest.TestCase):
    def test_unicode_identifier_is_searchable_by_name_parts(self):
        self.assertEqual(tokens("caféRésumé"), ["café", "résumé"])
        self.assertEqual(tokens("ΔοκιμήΚώδικα"), ["δοκιμή", "κώδικα"])
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "names.py"
            path.write_text("def caféRésumé():\n    return 1\n"
                            "def ΔοκιμήΚώδικα():\n    return 2\n")
            self.assertEqual(query_path(path, "café résumé")["matches"][0]["name"],
                             "caféRésumé")
            self.assertEqual(query_path(path, "δοκιμή κώδικα")["matches"][0]["name"],
                             "ΔοκιμήΚώδικα")

    def test_python_file_symbols_and_source_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "orders.py"
            source = ("class Orders:\n"
                      "    def calculate_total(self, price):\n"
                      "        \"\"\"Calculate the final order total.\"\"\"\n"
                      "        return self.apply_tax(price)\n")
            path.write_text(source)
            result = query_path(path, "final order total")
            self.assertEqual(result["raw_sha256"], hashlib.sha256(source.encode()).hexdigest())
            self.assertEqual(result["matches"][0]["qualified_name"], "Orders.calculate_total")
            self.assertEqual(result["matches"][0]["line"], 2)
            self.assertEqual(result["matches"][0]["end_line"], 4)
            self.assertIn("self.apply_tax", result["matches"][0]["lexical_call_candidates"])

    def test_mixed_tree_and_failures(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "orders.py").write_text("def calculate_total(price):\n    return price\n")
            (root / "bad.py").write_text("def broken(:\n")
            (root / "ignored.txt").write_text("calculate_total")
            (root / ".venv").mkdir()
            (root / ".venv" / "hidden.py").write_text("def calculate_total(): pass\n")
            if shutil.which("rust-analyzer"):
                (root / "lib.rs").write_text("fn calculate_total(value: i32) -> i32 { value }\n")
            result = query_path(root, "calculate total")
            self.assertEqual(result["scanned_files"], 1 + bool(shutil.which("rust-analyzer")))
            self.assertEqual(len(result["failures"]), 1)
            self.assertEqual(result["failures"][0]["error"], "SyntaxError")
            self.assertIn("INCOMPLETE", format_tree_compact(result))
            self.assertEqual(result["total_matches"], result["scanned_files"])
            self.assertIn("git_blob_sha1", result["matches"][0])

    def test_ranking_preserves_terms_beyond_display_limits(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "search.py"
            calls = "\n".join(f"    call_{number:02d}()" for number in range(20))
            path.write_text("def find_target():\n"
                            f"    \"\"\"{'filler ' * 60}late_document_term\"\"\"\n"
                            f"{calls}\n")
            by_doc = query_path(path, "late document term")
            by_call = query_path(path, "call 19")
            self.assertEqual(by_doc["matches"][0]["name"], "find_target")
            self.assertEqual(by_call["matches"][0]["name"], "find_target")
            self.assertLessEqual(len(by_doc["matches"][0]["docs"]), 220)
            self.assertLessEqual(len(by_call["matches"][0]["lexical_call_candidates"]), 12)
            self.assertIn("call_19", by_call["matches"][0]["lexical_call_candidates"])

    def test_python_signatures_preserve_legal_inline_multiline_and_encoding(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "signatures.py"
            source = ("# coding: latin-1\n"
                      "def inline(value: int) -> int: return value\n"
                      "def wrapped(\n"
                      "    value: dict[str, int],\n"
                      ") -> int: return len(value)\n"
                      "def labelled(name: str = 'café') -> str: return name\n").encode("latin-1")
            path.write_bytes(source)
            indexed = index_file(path)
            signatures = {name: query_path(path, name)["matches"][0]["signature"]
                          for name in ("inline", "wrapped", "labelled")}
            self.assertEqual(signatures["inline"], "def inline(value: int) -> int:")
            self.assertEqual(signatures["wrapped"],
                             "def wrapped( value: dict[str, int], ) -> int:")
            self.assertEqual(signatures["labelled"],
                             "def labelled(name: str = 'café') -> str:")
            self.assertEqual(indexed["raw_sha256"], hashlib.sha256(source).hexdigest())

    def test_unsupported_file_is_explicit(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "unknown.java"
            path.write_text("class Unknown {}")
            with self.assertRaisesRegex(ValueError, "Unsupported source type"):
                index_file(path)
            with self.assertRaisesRegex(ValueError, "existing file or directory"):
                query_path(Path(raw) / "missing", "unknown")
            with self.assertRaisesRegex(ValueError, "No supported"):
                query_path(Path(raw), "unknown")


if __name__ == "__main__":
    unittest.main()
