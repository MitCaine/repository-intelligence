"""Directory navigation retains non-callable evidence and excluded-only scope."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repository_intelligence.locator import query_path
from repository_intelligence.search import format_tree_compact


class DirectoryEvidenceTests(unittest.TestCase):
    def test_module_bindings_survive_directory_query_without_callable_matches(self):
        source = b'import {value} from "./values.js";\nexport {value};\n'
        expected = {
            "imports": [{"source": '"./values.js"',
                         "byte_range": {"start": 0, "end": 34}}],
            "exports": [{"kind": "named", "source": None, "owner": None,
                         "byte_range": {"start": 35, "end": 50}}],
            "meaning": "syntactic module bindings only; not resolved imports or exports",
        }
        for suffix in (".js", ".ts"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                path = root / ("bindings" + suffix)
                path.write_bytes(source)
                result = query_path(root, "value")
                self.assertEqual(result["mapping_status"], "navigation_only")
                self.assertEqual(result["scanned_files"], 1)
                self.assertEqual(result["total_matches"], 0)
                self.assertEqual(result["matches"], [])
                self.assertEqual(result["files"][str(path)]["module_bindings"], expected)

    def test_excluded_only_source_returns_scope_instead_of_raising(self):
        for case, expected in (
                ("hidden", {"path": ".hidden.py", "reason": "hidden_file"}),
                ("caller", {"path": "generated", "reason": "caller_excluded_directory"}),
                ("symlink", {"path": "linked.py", "reason": "symlink_file"}),
                ("nested", {"path": "nested", "reason": "nested_repository"})):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                choices = {}
                if case == "hidden":
                    (root / ".hidden.py").write_text("def hidden(): pass\n")
                elif case == "caller":
                    (root / "generated").mkdir()
                    (root / "generated" / "source.py").write_text("def generated(): pass\n")
                    choices["excluded_directories"] = ("generated",)
                elif case == "symlink":
                    (root / "linked.py").symlink_to(root / "absent.py")
                else:
                    (root / "nested" / ".git").mkdir(parents=True)
                    (root / "nested" / "source.py").write_text("def nested(): pass\n")
                result = query_path(root, "source", **choices)
                self.assertEqual(result["mapping_status"], "excluded")
                self.assertEqual(result["scanned_files"], 0)
                self.assertEqual(result["files"], {})
                self.assertEqual(result["matches"], [])
                self.assertEqual(result["failures"], [])
                self.assertEqual(result["scan_scope"]["excluded_paths"], [expected])
                rendered = format_tree_compact(result)
                self.assertIn("status=excluded", rendered)
                self.assertIn(f"EXCLUDED: {expected['path']} ({expected['reason']})", rendered)

    def test_exclusions_do_not_override_incomplete_or_unsupported_scope(self):
        excluded = [{"path": "hidden", "reason": "caller_excluded_directory"}]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            failure = {"path": "unreadable", "error": "PermissionError"}
            with patch("repository_intelligence.locator.walk_supported_paths",
                       return_value=([], excluded, [failure], 0, [])):
                result = query_path(root, "source")
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertEqual(result["failures"], [failure])
            self.assertEqual(result["scan_scope"]["excluded_paths"], excluded)
            unsupported = [{"path": "unknown.h", "reason": "no_language_adapter_selected"}]
            with patch("repository_intelligence.locator.walk_supported_paths",
                       return_value=([], excluded, [], 1, unsupported)):
                result = query_path(root, "source")
            self.assertEqual(result["mapping_status"], "unsupported")
            self.assertEqual(result["scan_scope"]["unsupported_paths"], unsupported)
            self.assertEqual(result["scan_scope"]["excluded_paths"], excluded)

    def test_empty_directory_still_has_no_source(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "No supported source files"):
                query_path(Path(raw), "source")


if __name__ == "__main__":
    unittest.main()
