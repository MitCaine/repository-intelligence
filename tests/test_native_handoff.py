"""Explicit native handoffs preserve source bytes and distinct coverage."""

import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repository_intelligence.locator import index_file
from repository_intelligence.python_index import index_source as python_native
from repository_intelligence.rust_index import index_source as rust_native


class NativeHandoffTests(unittest.TestCase):
    def test_new_python_syntax_can_use_native_without_erasing_incomplete_result(self):
        source = b"def target[T = int](value: T): return value\n"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.py"
            path.write_bytes(source)
            structural = index_file(path)
            self.assertEqual(structural["mapping_status"], "incomplete")
            self.assertGreater(structural["structural"]["diagnostic_count"], 0)
            if sys.version_info < (3, 13):
                # The native runtime's syntax support is a real prerequisite.
                with self.assertRaises(SyntaxError):
                    python_native(path, source)
                return
            native = python_native(path, source)
        self.assertEqual([entry["name"] for entry in native["functions"]], ["target"])
        self.assertEqual(native["functions"][0]["byte_range"],
                         {"start": 0, "end": len(source) - 1})
        self.assertEqual(native["functions"][0]["declaration_sha256"],
                         hashlib.sha256(source[:-1]).hexdigest())
        self.assertEqual(native["raw_sha256"], structural["raw_sha256"])
        self.assertEqual(structural["mapping_status"], "incomplete")
        self.assertNotIn("adapter_coverage", native)

    def test_python_native_uses_supplied_bytes_after_the_file_changes(self):
        source = b"def original(): return 1\n"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.py"
            path.write_bytes(source)
            structural = index_file(path)
            path.write_bytes(b"def replacement(): return 2\n")
            with patch.object(Path, "read_bytes", side_effect=AssertionError("Unexpected reread")):
                native = python_native(path, source)
            self.assertEqual([entry["name"] for entry in native["functions"]], ["original"])
            self.assertEqual(native["raw_sha256"], structural["raw_sha256"])
            current = index_file(path)
            self.assertNotEqual(native["raw_sha256"], current["raw_sha256"])

    @unittest.skipUnless(shutil.which("rust-analyzer"), "rust-analyzer required for native syntax")
    def test_rust_native_does_not_replace_tree_sitter_closure_coverage(self):
        source = b"fn target() { let callback = || 1; callback(); }\n"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.rs"
            path.write_bytes(source)
            structural = index_file(path)
            path.write_bytes(b"fn replacement() {}\n")
            with patch.object(Path, "read_bytes", side_effect=AssertionError("Unexpected reread")):
                native = rust_native(path, source)
        self.assertEqual(structural["mapping_status"], "navigation_only")
        self.assertEqual([entry["declaration_kind"] for entry in structural["functions"]],
                         ["function", "closure"])
        self.assertEqual([entry["name"] for entry in native["functions"]], ["target"])
        self.assertEqual(native["parse_error_count"], 0)
        self.assertEqual(native["raw_sha256"], structural["raw_sha256"])
        self.assertEqual(native["functions"][0]["byte_range"],
                         {"start": 0, "end": len(source) - 1})
        self.assertNotIn("adapter_coverage", native)


if __name__ == "__main__":
    unittest.main()
