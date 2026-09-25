"""Exact-byte fallback and public comparison-boundary regressions."""

import copy
import tempfile
import unittest
from pathlib import Path

from repository_intelligence.inventory import _digest, compare_inventories, inventory_tree
from repository_intelligence.python_index import index_source as ast_index_source


class EvidenceBoundaryTests(unittest.TestCase):
    def test_ast_fallback_stateful_encoding_includes_changed_value(self):
        entries = []
        for value in (b"123", b"456"):
            source = b"# coding: iso2022_jp\ndef f(): return \x1b(B" + value + b"\n"
            result = ast_index_source(Path("f.py"), source)
            entry = result["functions"][0]
            span = entry["byte_range"]
            self.assertEqual(source[span["start"]:span["end"]],
                             b"def f(): return \x1b(B" + value)
            entries.append(entry)
        self.assertNotEqual(entries[0]["declaration_sha256"],
                            entries[1]["declaration_sha256"])

    def _pair(self, *, changed=False):
        raw = tempfile.TemporaryDirectory()
        self.addCleanup(raw.cleanup)
        left, right = Path(raw.name) / "left", Path(raw.name) / "right"
        left.mkdir(); right.mkdir()
        source = b"def one(): return 1\ndef two(): return 2\n"
        (left / "x.py").write_bytes(source)
        (right / "x.py").write_bytes(source.replace(b"return 2", b"return 3")
                                     if changed else source)
        return inventory_tree(left, stable=True), inventory_tree(right, stable=True)

    def test_changed_candidate_rejects_duplicate_declaration_range(self):
        planning, candidate = self._pair(changed=True)
        records = candidate["files"][0]["declarations"]
        records[1]["byte_range"] = copy.deepcopy(records[0]["byte_range"])
        records[1]["declaration_sha256"] = records[0]["declaration_sha256"]
        self.assertEqual(compare_inventories(planning, candidate)["status"], "incompatible")

    def test_complete_packet_rejects_nonhex_file_hash(self):
        planning, candidate = self._pair()
        candidate["files"][0]["source_identity"]["raw_sha256"] = "z" * 64
        candidate["inventory_digest"] = _digest(candidate["scope"], candidate["files"])
        self.assertEqual(compare_inventories(planning, candidate)["status"], "incompatible")

    def test_equal_file_hash_with_different_size_is_incompatible(self):
        planning, candidate = self._pair()
        candidate["files"][0]["source_identity"]["byte_count"] += 1
        candidate["inventory_digest"] = _digest(candidate["scope"], candidate["files"])
        self.assertEqual(compare_inventories(planning, candidate)["status"], "incompatible")

    def test_missing_optional_module_bindings_does_not_crash(self):
        planning, candidate = self._pair()
        candidate["files"][0].pop("module_bindings")
        self.assertEqual(compare_inventories(planning, candidate)["status"], "incompatible")


if __name__ == "__main__":
    unittest.main()
