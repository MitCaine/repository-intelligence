"""Explicit direct-file language selection does not invent adapter coverage."""

import tempfile
import unittest
from pathlib import Path

from repository_intelligence.locator import index_file, query_path


class LanguageSelectionTests(unittest.TestCase):
    def test_ambiguous_extension_requires_explicit_supported_language(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "snippet.h"
            path.write_bytes(b"fn example() {}\n")
            unknown = index_file(path)
            self.assertEqual(unknown["mapping_status"], "unsupported")
            self.assertIsNone(unknown["parser"])
            self.assertNotIn("adapter_coverage", unknown)
            chosen = index_file(path, language="rust")
            self.assertEqual(chosen["mapping_status"], "navigation_only")
            self.assertEqual(chosen["parser"]["grammar"], "Rust")
            self.assertEqual(chosen["functions"][0]["name"], "example")
            self.assertEqual(query_path(path, "example", language="rust")["matches"][0]["name"],
                             "example")
            python_path = Path(raw) / "python.snippet"
            python_path.write_bytes(b"def example(): return 1\n")
            python = index_file(python_path, language="python")
            self.assertEqual(python["mapping_status"], "navigation_only")
            self.assertEqual(python["parser"]["grammar"], "Python")

    def test_known_extension_conflict_and_unknown_language_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "snippet.py"
            path.write_bytes(b"def example(): pass\n")
            conflict = index_file(path, language="rust")
            self.assertEqual(conflict["mapping_status"], "unsupported")
            self.assertEqual(conflict["unsupported_reason"], "language_extension_mismatch")
            self.assertNotIn("adapter_coverage", conflict)
            with self.assertRaisesRegex(ValueError, "Unsupported language"):
                index_file(path, language="swift")
            with self.assertRaisesRegex(ValueError, "direct file"):
                query_path(Path(raw), "example", language="python")


if __name__ == "__main__":
    unittest.main()
