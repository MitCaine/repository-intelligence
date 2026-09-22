"""Direct tests for generic identity binding behavior."""

from __future__ import annotations

from dataclasses import fields, replace
import unittest

from repository_intelligence.authority import _Authority
from repository_intelligence.errors import ValidationError
from repository_intelligence import identity


class IdentityPackageTests(unittest.TestCase):
    def issue(self):
        return identity._new_binding(
            _Authority("identity-test"), source_id="source-a", materialization_id="material-a",
            configuration_id="config-a", generation_id="generation-a",
        )

    def test_identity_has_exactly_four_material_dimensions(self):
        binding = identity.IdentityBinding("source-a", "material-a", "config-a", "generation-a")
        self.assertEqual([field.name for field in fields(identity.IdentityBinding)], ["source_id", "materialization_id", "configuration_id", "generation_id"])
        self.assertEqual(binding.as_dict(), {"source_id": "source-a", "materialization_id": "material-a", "configuration_id": "config-a", "generation_id": "generation-a"})

    def test_authority_issued_binding_authenticates(self):
        self.assertTrue(self.issue().is_authenticated())

    def test_matching_direct_construction_is_not_authenticated(self):
        issued = self.issue()
        caller = identity.AuthenticatedBinding(issued.source_id, issued.materialization_id, issued.configuration_id, issued.generation_id)
        self.assertEqual(caller.as_dict(), issued.as_dict())
        self.assertFalse(caller.is_authenticated())

    def test_tampered_signature_issuer_or_dimension_fails_authentication(self):
        issued = self.issue()
        self.assertFalse(replace(issued, _signature="0" * 64).is_authenticated())
        self.assertFalse(replace(issued, _authority=None).is_authenticated())
        self.assertFalse(replace(issued, source_id="source-tampered").is_authenticated())

    def test_invalid_dimensions_fail_closed(self):
        for invalid in ("", None, True, 1, "bad value"):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                identity.IdentityBinding(invalid, "material-a", "config-a", "generation-a")

    def test_valid_canonical_identity_bytes_are_unchanged(self):
        binding = identity.IdentityBinding("source-a", "material-a", "config-a", "generation-a")
        self.assertEqual(identity._canonical_binding_json(binding.as_dict()).encode("utf-8"), b'{"configuration_id":"config-a","generation_id":"generation-a","materialization_id":"material-a","source_id":"source-a"}')


if __name__ == "__main__":
    unittest.main()
