"""Small ranking contract and scan-cost regressions."""

import unittest
from unittest.mock import patch

from repository_intelligence import search


class SearchTests(unittest.TestCase):
    def test_rank_scores_each_entry_once_without_changing_order(self):
        def entry(name, line):
            return {"name": name, "qualified_name": name, "docs": "",
                    "lexical_call_candidates": [], "path": "file.py", "line": line}

        entries = [entry("not_related", 1), entry("target", 3), entry("target", 2)]
        with patch.object(search, "score", wraps=search.score) as scored:
            result = search.rank(entries, ["target"])
        self.assertEqual([item["line"] for item in result], [2, 3])
        self.assertEqual(scored.call_count, len(entries))


if __name__ == "__main__":
    unittest.main()
