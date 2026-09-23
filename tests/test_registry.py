"""Closed provider-neutral registry identity authority tests."""
from __future__ import annotations

import copy
import unittest

from repository_intelligence.errors import ValidationError
from repository_intelligence.registry import RegistryIdentityCatalog, SourceMatrixAuthority


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


class SourceMatrixAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            {
                "source_id": "source-a",
                "repository": "example/repo",
                "revision": "a" * 40,
                "language": "Rust",
                "source_state_mode": "immutable_committed",
                "configuration_id": "config-a",
            },
            {
                "source_id": "source-b",
                "repository": "example/repo",
                "revision": "b" * 40,
                "language": "TypeScript",
                "source_state_mode": "immutable_committed",
                "configuration_id": "config-b",
            },
        ]

    def test_exact_authored_geometry_and_caller_mutation(self):
        authority = SourceMatrixAuthority(self.sources, ["controller", "reviewer"], ["navigate", "scope"])
        fragment = authority.as_dict()
        self.assertEqual(len(fragment["matrix"]), 8)
        self.assertEqual({cell["disposition"] for cell in fragment["matrix"]}, {"not_executed"})
        authority.validate(fragment)
        self.sources[0]["revision"] = "c" * 40
        authority.validate(fragment)
        fragment["matrix"][0]["source_id"] = "source-b"
        with self.assertRaises(ValidationError):
            authority.validate(fragment)

    def test_source_drift_and_self_rebuilt_matrix_fail(self):
        authority = SourceMatrixAuthority(self.sources, ["controller"], ["navigate"])
        fragment = authority.as_dict()
        fragment["source_pins"][0]["revision"] = "c" * 40
        fragment["matrix"][0]["revision"] = "c" * 40
        with self.assertRaises(ValidationError):
            authority.validate(fragment)
        for mutation in (
            lambda data: data["matrix"].reverse(),
            lambda data: data["matrix"].append(data["matrix"][0]),
            lambda data: data["matrix"][0].update(disposition="qualified"),
            lambda data: data["source_pins"][0].update(extra="accepted"),
        ):
            changed = authority.as_dict()
            mutation(changed)
            with self.assertRaises(ValidationError):
                authority.validate(changed)

    def test_invalid_sources_roles_and_operations_fail(self):
        for sources in (
            [],
            self.sources + [self.sources[0]],
            [{**self.sources[0], "revision": "latest"}],
            [{**self.sources[0], "revision": "A" * 40}],
            [{**self.sources[0], "repository": "example/../other"}],
        ):
            with self.subTest(sources=sources), self.assertRaises(ValidationError):
                SourceMatrixAuthority(sources, ["controller"], ["navigate"])
        for roles, operations in (([], ["navigate"]), (["controller", "controller"], ["navigate"]), (["controller"], ["latest"])):
            with self.assertRaises(ValidationError):
                SourceMatrixAuthority(self.sources, roles, operations)


if __name__ == "__main__":
    unittest.main()
