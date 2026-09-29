"""Consumer-facing encoding, coverage and diagnostic parity regressions."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import compare_inventories, inventory_tree
from repository_intelligence.locator import index_file, query_path
from repository_intelligence.structural import GRAMMARS, MAX_DIAGNOSTIC_DETAILS, scan


class ScanIntegrityTests(unittest.TestCase):
    def test_invalid_utf8_is_incomplete_in_every_non_python_adapter(self):
        fixtures = {
            ".rs": b"fn target() {}", ".js": b"function target() {}",
            ".ts": b"function target() {}", ".tsx": b"const target = () => <div/>;",
            ".java": b"class C { void target() {} }",
            ".go": b"package p\nfunc target() {}",
            ".cs": b"class C { void Target() {} }",
            ".c": b"void target(void) {}", ".cpp": b"void target() {}",
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for suffix, valid in fixtures.items():
                with self.subTest(suffix=suffix):
                    source = b"// invalid \xff\n" + valid + b"\n"
                    path = root / ("bad" + suffix)
                    path.write_bytes(source)
                    result = index_file(path)
                    self.assertEqual(result["mapping_status"], "incomplete")
                    self.assertEqual(result["functions"], [])
                    self.assertEqual(result["source_identity"]["raw_sha256"],
                                     hashlib.sha256(source).hexdigest())
                    self.assertEqual(result["failures"][0]["error"], "UnicodeDecodeError")
            inventory = inventory_tree(root, stable=True)
            self.assertEqual(inventory["status"], "incomplete")
            self.assertEqual(query_path(root, "target")["mapping_status"], "incomplete")
            self.assertIsNone(compare_inventories(inventory, inventory)["file_changes"])

    def test_valid_non_ascii_rust_retains_exact_source(self):
        source = "/// café\nfn target() { let message = \"日本語\"; }\n".encode()
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "valid.rs"
            path.write_bytes(source)
            result = index_file(path)
        self.assertEqual(result["mapping_status"], "navigation_only")
        self.assertEqual(result["functions"][0]["docs"], "café")
        self.assertEqual(result["functions"][0]["declaration_sha256"],
                         hashlib.sha256(source.rstrip(b"\n")).hexdigest())

    def test_excluded_planning_paths_do_not_become_proven_additions(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            left, right = root / "left", root / "right"
            left.mkdir()
            right.mkdir()
            (left / "src").symlink_to(right, target_is_directory=True)
            (right / "src").mkdir()
            (right / "src/run.py").write_text("def run(): pass\n")
            planning = inventory_tree(left, stable=True)
            candidate = inventory_tree(right, stable=True)
            delta = compare_inventories(planning, candidate)
            self.assertEqual(delta["status"], "incompatible")
            self.assertIn("planning_coverage_missing:src/run.py", delta["mismatches"])
            self.assertIsNone(delta["file_changes"])
            reverse = compare_inventories(candidate, planning)
            self.assertIn("coverage_lost:src/run.py", reverse["mismatches"])

    def test_excluded_planning_file_does_not_become_proven_addition(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            left, right = root / "left", root / "right"
            left.mkdir()
            right.mkdir()
            (left / "run.py").symlink_to(root / "unavailable.py")
            (right / "run.py").write_text("def run(): pass\n")
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "incompatible")
            self.assertIn("planning_coverage_missing:run.py", delta["mismatches"])

    def test_exclusion_prefix_does_not_shadow_sibling_name(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            left, right = root / "left", root / "right"
            left.mkdir()
            right.mkdir()
            (left / "src").symlink_to(right, target_is_directory=True)
            (right / "src_extra").mkdir()
            (right / "src_extra/run.py").write_text("def run(): pass\n")
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
            self.assertEqual(delta["status"], "comparable_candidate_delta")
            self.assertEqual([item["path"] for item in delta["file_changes"]["added"]],
                             ["src_extra/run.py"])

    def test_mixed_language_delta_has_independently_expected_changes(self):
        sources = {
            "sample.py": b"def target(): return 1\n",
            "sample.rs": b"fn target() -> i32 { 1 }\n",
            "sample.js": b"function target() { return 1; }\n",
            "sample.ts": b"function target(): number { return 1; }\n",
            "sample.tsx": b"const target = () => <div>{1}</div>;\n",
            "sample.java": b"class C { int target() { return 1; } }\n",
            "sample.go": b"package p\nfunc target() int { return 1 }\n",
            "sample.cs": b"class C { int target() { return 1; } }\n",
            "sample.c": b"int target(void) { return 1; }\n",
            "sample.cpp": b"int target() { return 1; }\n",
        }
        with tempfile.TemporaryDirectory() as raw:
            left, right = Path(raw) / "left", Path(raw) / "right"
            left.mkdir()
            right.mkdir()
            for name, source in sources.items():
                (left / name).write_bytes(source)
                (right / name).write_bytes(source.replace(b"1", b"2"))
            for root in (left, right):
                (root / "unchanged.py").write_text("def same(): pass\n")
                (root / "unsupported.swift").write_text("func outside() {}\n")
            (left / "constants.py").write_text("VALUE = 1\n")
            (right / "constants.py").write_text("VALUE = 2\n")
            (left / "deleted.py").write_text("def removed(): pass\n")
            (right / "added.py").write_text("def added(): pass\n")
            delta = compare_inventories(inventory_tree(left, stable=True),
                                        inventory_tree(right, stable=True))
        self.assertEqual(delta["status"], "comparable_candidate_delta")
        files = delta["file_changes"]
        self.assertEqual([item["path"] for item in files["added"]], ["added.py"])
        self.assertEqual([item["path"] for item in files["removed"]], ["deleted.py"])
        self.assertEqual([item["path"] for item in files["unchanged"]], ["unchanged.py"])
        self.assertEqual({item["path"] for item in files["modified"]},
                         {*sources, "constants.py"})
        declarations = delta["declaration_changes"]
        self.assertEqual({item["path"] for item in declarations["modified"]}, set(sources))
        self.assertEqual(len(declarations["modified"]), len(sources))
        self.assertEqual([item["candidate"]["name"] for item in declarations["added"]], ["added"])
        self.assertEqual([item["planning"]["name"] for item in declarations["removed"]], ["removed"])
        self.assertEqual([item["candidate"]["name"] for item in declarations["unchanged"]], ["same"])
        for item in declarations["modified"]:
            self.assertEqual(item["planning"]["name"], "target")
            self.assertEqual(item["candidate"]["name"], "target")
        self.assertEqual(delta["planning"]["observed_unsupported_paths"],
                         [{"path": "unsupported.swift", "reason": "no_language_adapter_selected"}])

    def test_diagnostics_match_exhaustive_walk_for_every_pinned_grammar(self):
        fixtures = {
            ".py": b"def good(): pass\ndef broken(:\n  return (\n",
            ".rs": b"fn good() {}\nfn broken() { let x = ; }\n",
            ".js": b"function good() {}\nfunction broken( { return ;\n",
            ".ts": b"function good() {}\nfunction broken(x: ) { return ( ; }\n",
            ".tsx": b"const good = () => <div/>;\nconst broken = () => <div>;\n",
            ".java": b"class C { void good() {} void broken( { return ; } }",
            ".go": b"package p\nfunc good() {}\nfunc broken( { x := }",
            ".cs": b"class C { void Good() {} void Broken( { return ; } }",
            ".c": b"void good(void) {}\nvoid broken(void) { return 1 }",
            ".cpp": b"void good() {}\nvoid broken() { return 1 }",
            ".md": b"# Good\n\n```\nunterminated fence\n",
        }
        aliases = {".jsx": ".js", ".mjs": ".js", ".cjs": ".js",
                   ".mts": ".ts", ".cts": ".ts", ".cc": ".cpp",
                   ".cxx": ".cpp", ".hh": ".cpp", ".hpp": ".cpp", ".hxx": ".cpp"}
        for suffix in GRAMMARS:
            with self.subTest(suffix=suffix):
                syntax, tree, _, _ = scan(suffix, fixtures[aliases.get(suffix, suffix)])
                expected = []
                pending = [tree]
                while pending:
                    node = pending.pop()
                    if node.type == "ERROR" or node.is_missing:
                        expected.append({"kind": "MISSING" if node.is_missing else "ERROR",
                                         "node_type": node.type,
                                         "byte_range": {"start": node.start_byte,
                                                        "end": node.end_byte}})
                    pending.extend(reversed(node.children))
                if suffix != ".md":  # Markdown accepts an unclosed fence as content.
                    self.assertGreater(len(expected), 0)
                self.assertEqual(syntax["diagnostics"], expected[:MAX_DIAGNOSTIC_DETAILS])
                self.assertEqual(syntax["error_count"],
                                 sum(item["kind"] == "ERROR" for item in expected))
                self.assertEqual(syntax["missing_count"],
                                 sum(item["kind"] == "MISSING" for item in expected))
                self.assertEqual(syntax["diagnostic_count"], len(expected))

    def test_diagnostic_truncation_keeps_full_missing_count(self):
        source = b"int f() { return 1 }\n" * (MAX_DIAGNOSTIC_DETAILS + 7)
        syntax, _, _, _ = scan(".c", source)
        self.assertEqual(syntax["missing_count"], MAX_DIAGNOSTIC_DETAILS + 7)
        self.assertEqual(syntax["error_count"], 0)
        self.assertEqual(len(syntax["diagnostics"]), MAX_DIAGNOSTIC_DETAILS)
        self.assertTrue(syntax["details_truncated"])


if __name__ == "__main__":
    unittest.main()
