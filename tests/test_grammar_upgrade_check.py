"""The optional maintainer check recognizes declaration-node field drift."""

import runpy
import unittest
from pathlib import Path


CHECK = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                            "scripts" / "check_grammar_nodes.py"))


class GrammarUpgradeCheckTests(unittest.TestCase):
    def test_pinned_shapes_pass_and_field_drift_fails(self):
        for language, expected in CHECK["EXPECTED"].items():
            nodes = [{"type": kind, "named": True,
                      "fields": {field: {"required": required}
                                 for field, required in fields.items()}}
                     for kind, fields in expected.items()]
            with self.subTest(language=language):
                self.assertEqual(CHECK["check"](language, nodes), [])
                nodes[0]["fields"].pop(next(iter(nodes[0]["fields"])))
                self.assertTrue(CHECK["check"](language, nodes))


if __name__ == "__main__":
    unittest.main()
