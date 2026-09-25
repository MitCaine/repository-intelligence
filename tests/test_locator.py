"""Tests for the shared locator across distinct languages and projects."""

import hashlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file, query_path
from repository_intelligence.search import format_tree_compact, tokens
from repository_intelligence.source import SCHEMA_VERSION, identify_bytes


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
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertEqual(result["scan_scope"]["extensions"], [".py", ".rs"])
            self.assertEqual(result["scan_scope"]["source_kind"], "working_tree_non_atomic")
            self.assertIn("raw_sha256", result["failures"][0]["source_identity"])
            self.assertIn("INCOMPLETE", format_tree_compact(result))
            self.assertEqual(result["total_matches"], result["scanned_files"])
            self.assertIn("git_blob_sha1", result["matches"][0])

    def test_directory_scope_reports_duplicate_symlink_and_nested_repo(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "a.py"
            source.write_text("def calculate_total():\n    return 1\n")
            os.link(source, root / "z.py")
            (root / "link.py").symlink_to(source)
            nested = root / "nested"
            nested.mkdir()
            (nested / ".git").mkdir()
            (nested / "other.py").write_text("def calculate_total(): return 2\n")
            result = query_path(root, "calculate total")
            self.assertEqual(result["scanned_files"], 1)
            self.assertEqual(result["total_matches"], 1)
            excluded = {item["path"]: item["reason"]
                        for item in result["scan_scope"]["excluded_paths"]}
            self.assertEqual(excluded["link.py"], "symlink_file")
            self.assertEqual(excluded["nested"], "nested_repository")
            self.assertEqual(excluded["z.py"], "duplicate_physical_file")

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
            source = b"class Unknown {}"
            path.write_bytes(source)
            result = query_path(path, "unknown")
            self.assertEqual(result["schema_version"], SCHEMA_VERSION)
            self.assertEqual(result["mapping_status"], "unsupported")
            self.assertEqual(result["source_identity"]["relative_path"], "unknown.java")
            self.assertEqual(result["source_identity"]["raw_sha256"],
                             hashlib.sha256(source).hexdigest())
            self.assertEqual(result["matches"], [])
            with self.assertRaisesRegex(ValueError, "existing file or directory"):
                query_path(Path(raw) / "missing", "unknown")
            with self.assertRaisesRegex(ValueError, "No supported"):
                query_path(Path(raw), "unknown")

    def test_failed_or_oversized_source_remains_identified_and_incomplete(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            broken = root / "broken.py"
            broken.write_bytes(b"def broken(:\n")
            result = query_path(broken, "broken")
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertEqual(result["failures"][0]["error"], "SyntaxError")
            self.assertEqual(result["source_identity"]["raw_sha256"],
                             hashlib.sha256(broken.read_bytes()).hexdigest())

            large = root / "large.py"
            large.write_bytes(b"x" * 4_000_001)
            limited = query_path(large, "large")
            self.assertEqual(limited["mapping_status"], "incomplete")
            self.assertEqual(limited["failures"][0]["error"], "SourceLimitExceeded")
            self.assertEqual(limited["source_identity"]["byte_count"], 4_000_001)

    def test_tagged_git_blob_identity_is_a_computed_byte_identity(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "sample.xyz"
            source = b"hello\n"
            identity = identify_bytes(path, source, root=Path(raw), object_format="sha256")
            expected = hashlib.sha256(b"blob 6\0hello\n").hexdigest()
            self.assertEqual(identity["git_blob"]["algorithm"], "sha256")
            self.assertEqual(identity["git_blob"]["object_id"], expected)
            self.assertIn("not checkout attestation", identity["git_blob"]["meaning"])
            with self.assertRaises(ValueError):
                identify_bytes(Path(raw).parent / "outside.xyz", source,
                               root=Path(raw), object_format="sha256")


if __name__ == "__main__":
    unittest.main()
