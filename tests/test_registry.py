"""Closed provider-neutral registry identity authority tests."""
from __future__ import annotations

import copy
import unittest

from repository_intelligence.errors import ValidationError
from repository_intelligence.registry import RegistryIdentityCatalog


class RegistryIdentityCatalogTests(unittest.TestCase):
    def setUp(self):
        self.declarations = [
            {"identity_id": "source-a", "kind": "source", "value": "repo/project@abc123"},
            {"identity_id": "policy-a", "kind": "policy", "value": "bounded-policy-v1"},
            {"identity_id": "candidate-a", "kind": "candidate", "value": "candidate-one"},
        ]

    def test_exact_reference_and_immutable_declarations(self):
        catalog = RegistryIdentityCatalog(self.declarations)
        reference = {"identity_id": "policy-a", "expected_kind": "policy", "value": "bounded-policy-v1"}
        self.assertEqual(catalog.require_reference(reference)["identity_id"], "policy-a")
        self.declarations[1]["value"] = "latest"
        self.assertEqual(catalog.require_reference(reference)["value"], "bounded-policy-v1")
        serialized = catalog.as_dict()
        serialized[1]["value"] = "latest"
        self.assertEqual(catalog.require_reference(reference)["value"], "bounded-policy-v1")

    def test_duplicate_alias_unknown_and_conflict_fail(self):
        for declarations in (
            [],
            self.declarations + [self.declarations[0]],
            self.declarations + [{"identity_id": "source-b", "kind": "source", "value": "repo/project@abc123"}],
            self.declarations + [{"identity_id": "policy-a", "kind": "candidate", "value": "other"}],
            [{"identity_id": "source-a", "kind": "source", "value": "repo/project@abc123", "extra": "x"}],
        ):
            with self.subTest(declarations=declarations), self.assertRaises(ValidationError):
                RegistryIdentityCatalog(declarations)
        catalog = RegistryIdentityCatalog(self.declarations)
        for reference in (
            {"identity_id": "missing", "expected_kind": "policy", "value": "bounded-policy-v1"},
            {"identity_id": "policy-a", "expected_kind": "candidate", "value": "bounded-policy-v1"},
            {"identity_id": "policy-a", "expected_kind": "policy", "value": "latest"},
            {"identity_id": "policy-a", "expected_kind": "policy", "value": "bounded-policy-v1", "extra": "x"},
        ):
            with self.subTest(reference=reference), self.assertRaises(ValidationError):
                catalog.require_reference(reference)

    def test_mutable_or_open_ended_values_fail(self):
        for value in (
            "latest", "origin/HEAD", "current-branch", "discover-all",
            "whatever-is-discovered-later/x", "issue/296/latest",
            "comment/last", "repo/*", "repo/../host", "repo/\x00host",
        ):
            declarations = copy.deepcopy(self.declarations)
            declarations[1]["value"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                RegistryIdentityCatalog(declarations)


if __name__ == "__main__":
    unittest.main()
