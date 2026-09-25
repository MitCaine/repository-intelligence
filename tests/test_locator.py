"""Tests for the shared locator across distinct languages and projects."""

import hashlib
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from repository_intelligence.locator import index_file, main, query_path
from repository_intelligence.search import format_compact, format_tree_compact, tokens
from repository_intelligence.source import SCHEMA_VERSION, identify_bytes


class LocatorTests(unittest.TestCase):
    def test_common_identity_and_legacy_blob_field(self):
        source = b"fn process() {}\n"
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "sample.rs"
            path.write_bytes(source)
            indexed = index_file(path, object_format="sha256")
            self.assertEqual(indexed["raw_sha256"], hashlib.sha256(source).hexdigest())
            self.assertEqual(indexed["source_identity"]["raw_sha256"], indexed["raw_sha256"])
            self.assertEqual(indexed["source_identity"]["git_blob"]["algorithm"], "sha256")
            self.assertEqual(indexed["git_blob_sha1"], hashlib.sha1(
                f"blob {len(source)}\0".encode() + source).hexdigest())

    def test_cross_language_expected_slices_do_not_depend_on_probe_counts(self):
        cases = [
            (".js", b"// invoice close\nfunction process(){}\n", "process", b"function process(){}"),
            (".java", b"class C { /** invoice close */ void process(){} }\n",
             "C.process", b"void process(){}"),
            (".go", b"package main\nfunc process() {}\n", "main.process", b"func process() {}"),
        ]
        with tempfile.TemporaryDirectory() as raw:
            for position, (suffix, source, qualified, expected_slice) in enumerate(cases):
                path = Path(raw) / f"sample{position}{suffix}"
                path.write_bytes(source)
                result = index_file(path)
                self.assertEqual([entry["qualified_name"] for entry in result["functions"]],
                                 [qualified])
                span = result["functions"][0]["byte_range"]
                self.assertEqual(source[span["start"]:span["end"]], expected_slice)
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
            self.assertEqual(result["matches"][0]["column"], 5)
            self.assertEqual(result["matches"][0]["end_line"], 4)
            self.assertIn("self.apply_tax", result["matches"][0]["lexical_call_candidates"])

    def test_shared_rust_result_has_v2_source_and_declaration_contract(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "sample.rs"
            source = b"#[inline]\nfn calculate_total(value: i32) -> i32 { value }\n"
            path.write_bytes(source)
            result = query_path(path, "calculate total")
            self.assertEqual(result["schema_version"], 2)
            self.assertEqual(result["mapping_status"], "navigation_only")
            self.assertEqual(result["source_identity"]["raw_sha256"],
                             hashlib.sha256(source).hexdigest())
            self.assertEqual(result["parser"]["name"], "tree-sitter")
            self.assertEqual(result["parser"]["grammar_version"], "0.24.2")
            entry = result["matches"][0]
            span = entry["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]], source.rstrip(b"\n"))
            self.assertEqual(entry["declaration_sha256"],
                             hashlib.sha256(source[span["start"]:span["end"]]).hexdigest())
            self.assertNotIn("guidance_candidates", entry)

    def test_mixed_tree_and_failures(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "orders.py").write_text("def calculate_total(price):\n    return price\n")
            (root / "bad.py").write_text("def broken(:\n")
            (root / "ignored.txt").write_text("calculate_total")
            (root / ".venv").mkdir()
            (root / ".venv" / "hidden.py").write_text("def calculate_total(): pass\n")
            (root / "lib.rs").write_text("fn calculate_total(value: i32) -> i32 { value }\n")
            result = query_path(root, "calculate total")
            self.assertEqual(result["scanned_files"], 3)
            self.assertEqual(result["failures"], [])
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertGreater(result["structural_error_count"], 0)
            self.assertEqual(result["scan_scope"]["extensions"],
                             [".c", ".cc", ".cjs", ".cpp", ".cs", ".cts", ".cxx", ".go", ".hh", ".hpp", ".hxx", ".java", ".js", ".jsx", ".mjs", ".mts", ".py", ".rs", ".ts", ".tsx"])
            self.assertEqual(result["scan_scope"]["source_kind"], "working_tree_non_atomic")
            self.assertIn("INCOMPLETE", format_tree_compact(result))
            self.assertEqual(result["total_matches"], 2)
            self.assertIn("git_blob_sha1", result["matches"][0])

    def test_directory_file_metadata_matches_direct_result_and_raw_cpp_limit(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "work.cpp"
            path.write_bytes(b"#if FEATURE\nint process(){return 1;}\n#endif\n")
            direct = query_path(path, "process")
            directory = query_path(root, "process")
            self.assertEqual(directory["total_matches"], 1)
            self.assertEqual(directory["matches"][0]["path"], str(path))
            record = directory["files"][str(path)]
            for key in ("parser", "structural", "preprocessing", "source_identity",
                        "adapter_coverage", "mapping_status", "parse_error_count"):
                self.assertEqual(record[key], direct[key])
            self.assertIn("C/C++ RAW SOURCE", format_tree_compact(directory))

    def test_directory_retains_metadata_for_failed_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bad = root / "bad.js"
            bad.write_bytes(b"\xff")
            direct = query_path(bad, "process")
            directory = query_path(root, "process")
            record = directory["files"][str(bad)]
            self.assertEqual(record["source_identity"], direct["source_identity"])
            self.assertEqual(record["mapping_status"], "incomplete")
            self.assertEqual(record["parser"], direct["parser"])
            self.assertEqual(record["structural"], direct["structural"])
            self.assertEqual(directory["scanned_files"], 0)
            self.assertEqual(len(directory["failures"]), 1)

    def test_python_declaration_ranges_include_decorators_and_anonymous_lambda(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "ranges.py"
            source = ("# coding: latin-1\n"
                      "@cache\n"
                      "def café(value):\n"
                      "    fn = lambda x: x + value\n"
                      "    return fn(1)\n").encode("latin-1")
            path.write_bytes(source)
            indexed = index_file(path)
            named = next(item for item in indexed["functions"] if item["name"] == "café")
            anonymous = next(item for item in indexed["functions"]
                             if item["declaration_kind"] == "lambda")
            span = named["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]],
                             source[source.index(b"@cache"):].rstrip(b"\n"))
            self.assertEqual(named["declaration_sha256"],
                             hashlib.sha256(source[span["start"]:span["end"]]).hexdigest())
            self.assertEqual(anonymous["qualified_name"].split(".")[0], "café")
            lambda_span = anonymous["byte_range"]
            self.assertEqual(source[lambda_span["start"]:lambda_span["end"]],
                             b"lambda x: x + value")
            self.assertEqual(indexed["parser"]["adapter_version"], 1)
            self.assertEqual(indexed["mapping_status"], "navigation_only")

    def test_same_name_declarations_and_lambdas_have_distinct_byte_identities(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "duplicates.py"
            source = (b"def repeat(): return 1\n"
                      b"def repeat(): return 2\n"
                      b"one = lambda: 1\n"
                      b"two = lambda: 2\n")
            path.write_bytes(source)
            entries = index_file(path)["functions"]
            self.assertEqual(len(entries), 4)
            self.assertEqual(len({entry["declaration_id"] for entry in entries}), 4)
            self.assertEqual(len({entry["declaration_sha256"] for entry in entries}), 4)
            self.assertEqual([entry["declaration_kind"] for entry in entries],
                             ["function", "function", "lambda", "lambda"])
            named_ids = [entry["declaration_id"] for entry in entries[:2]]
            self.assertEqual(named_ids, ["function:repeat#0", "function:repeat#1"])
            path.write_bytes(b"unrelated = 0\n" + source)
            shifted = index_file(path)["functions"]
            self.assertEqual([entry["declaration_id"] for entry in shifted[:2]], named_ids)
            self.assertNotEqual(shifted[2]["declaration_id"], entries[2]["declaration_id"])

    def test_latin1_nel_in_prior_string_does_not_shift_byte_range(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "nel.py"
            source = b'# coding: latin-1\nx = "\x85"\ndef target(): return 1\n'
            path.write_bytes(source)
            indexed = index_file(path)
            entry = indexed["functions"][0]
            expected = b"def target(): return 1"
            span = entry["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]], expected)
            self.assertEqual(entry["declaration_sha256"], hashlib.sha256(expected).hexdigest())
            self.assertEqual(entry["signature"], "def target():")
            self.assertEqual(indexed["mapping_status"], "navigation_only")

    def test_utf8_bom_does_not_enter_declaration_range(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "bom.py"
            path.write_bytes(b"\xef\xbb\xbfdef sample(): return 1\n")
            entry = index_file(path)["functions"][0]
            self.assertEqual(entry["byte_range"]["start"], 3)

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
            self.assertEqual(result["scanned_files"], 2)
            self.assertEqual(result["total_matches"], 2)
            excluded = {item["path"]: item["reason"]
                        for item in result["scan_scope"]["excluded_paths"]}
            self.assertEqual(excluded["link.py"], "symlink_file")
            self.assertEqual(excluded["nested"], "nested_repository")
            self.assertNotIn("z.py", excluded)

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
            path = Path(raw) / "unknown.swift"
            source = b"class Unknown {}"
            path.write_bytes(source)
            result = query_path(path, "unknown")
            self.assertEqual(result["schema_version"], SCHEMA_VERSION)
            self.assertEqual(result["mapping_status"], "unsupported")
            self.assertEqual(result["source_identity"]["relative_path"], "unknown.swift")
            self.assertEqual(result["source_identity"]["raw_sha256"],
                             hashlib.sha256(source).hexdigest())
            self.assertEqual(result["matches"], [])
            with self.assertRaisesRegex(ValueError, "existing file or directory"):
                query_path(Path(raw) / "missing", "unknown")
            directory = query_path(Path(raw), "unknown")
            self.assertEqual(directory["mapping_status"], "unsupported")
            self.assertEqual(directory["scan_scope"]["unsupported_paths"][0]["path"],
                             "unknown.swift")

    def test_direct_files_outside_root_or_symlinked_are_excluded_without_reading(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "project"
            root.mkdir()
            outside = base / "outside.py"
            outside.write_text("def secret(): return 1\n")
            result = query_path(outside, "secret", root=root)
            self.assertEqual(result["schema_version"], 2)
            self.assertEqual(result["mapping_status"], "excluded")
            self.assertEqual(result["excluded_reason"], "outside_root")
            self.assertIsNone(result["source_identity"])
            self.assertIsNone(result["raw_sha256"])
            self.assertEqual(result["matches"], [])
            self.assertIn("EXCLUDED", format_compact(result))

            link = root / "linked.py"
            link.symlink_to(outside)
            linked = query_path(link, "secret", root=root)
            self.assertEqual(linked["mapping_status"], "excluded")
            self.assertEqual(linked["excluded_reason"], "symlink_path")
            self.assertIsNone(linked["source_identity"])

            dangling = root / "dangling.py"
            dangling.symlink_to(root / "missing.py")
            dangling_result = query_path(dangling, "secret", root=root)
            self.assertEqual(dangling_result["mapping_status"], "excluded")
            self.assertEqual(dangling_result["excluded_reason"], "symlink_path")
            self.assertIsNone(dangling_result["source_identity"])

            directory_link = base / "project-link"
            directory_link.symlink_to(root, target_is_directory=True)
            linked_directory = query_path(directory_link, "secret")
            self.assertEqual(linked_directory["mapping_status"], "excluded")
            self.assertEqual(linked_directory["excluded_reason"], "symlink_path")
            self.assertIsNone(linked_directory["source_identity"])
            self.assertNotIn("scanned_files", linked_directory)
            with patch("sys.argv", ["locator", str(directory_link), "--query", "secret"]):
                output = io.StringIO()
                with redirect_stdout(output):
                    main()
            self.assertIn("EXCLUDED: symlink_path", output.getvalue())
            with self.assertRaisesRegex(ValueError, "only to a direct file"):
                query_path(root, "secret", root=root)

    def test_failed_or_oversized_source_remains_identified_and_incomplete(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            broken = root / "broken.py"
            broken.write_bytes(b"def broken(:\n")
            result = query_path(broken, "broken")
            self.assertEqual(result["mapping_status"], "incomplete")
            self.assertGreater(result["structural"]["diagnostic_count"], 0)
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
