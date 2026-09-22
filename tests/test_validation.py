"""Direct tests for generic primitive validation behavior."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
import unittest

from repository_intelligence.errors import ValidationError
from repository_intelligence import validation


class PrimitiveValidationTests(unittest.TestCase):
    def test_boolean_validation_rejects_python_truthiness(self):
        self.assertIs(validation._require_exact_bool(True, "flag"), True)
        for invalid in (1, "true", [], None):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValidationError, "flag must be a boolean"):
                    validation._require_exact_bool(invalid, "flag")

    def test_text_and_optional_text_preserve_identifier_rules(self):
        self.assertEqual(validation._require_text("source:a", "source", identifier=True), "source:a")
        self.assertIsNone(validation._optional_text(None, "note"))
        self.assertEqual(validation._optional_text("note", "note"), "note")
        with self.assertRaisesRegex(ValidationError, "source is not a valid identifier"):
            validation._require_text("bad value", "source", identifier=True)
        with self.assertRaisesRegex(ValidationError, "note must be nonblank text"):
            validation._optional_text("", "note")

    def test_mapping_sequence_and_exact_keys_are_closed(self):
        value = {"required": 1}
        self.assertIs(validation._require_mapping(value, "record"), value)
        self.assertEqual(validation._require_sequence((1, 2), "items"), (1, 2))
        validation._require_exact_keys(value, {"required"}, {"required"}, "record")
        with self.assertRaisesRegex(ValidationError, "record keys must be text"):
            validation._require_mapping({1: "bad"}, "record")
        with self.assertRaisesRegex(ValidationError, "items must be a list or tuple"):
            validation._require_sequence("not-a-sequence", "items")
        with self.assertRaisesRegex(ValidationError, "record has unknown fields: extra"):
            validation._require_exact_keys({"required": 1, "extra": 2}, {"required"}, {"required"}, "record")
        with self.assertRaisesRegex(ValidationError, "record is missing fields: required"):
            validation._require_exact_keys({}, {"required"}, {"required"}, "record")

    def test_json_normalization_is_fresh_sorted_and_finite(self):
        source = {"z": (1, {"a": True}), "a": None}
        normalized = validation._json_value(source, "payload")
        self.assertEqual(normalized, {"a": None, "z": [1, {"a": True}]})
        self.assertIsNot(normalized, source)
        for invalid in (float("nan"), float("inf"), {1: "bad"}, {"x": object()}):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                validation._json_value(invalid, "payload")

    def test_deep_freeze_recursively_owns_immutable_data(self):
        source = {"items": [{"value": 1}]}
        frozen = validation._deep_freeze(source)
        source["items"][0]["value"] = 2
        self.assertIsInstance(frozen, MappingProxyType)
        self.assertEqual(frozen["items"][0]["value"], 1)
        with self.assertRaises(TypeError):
            frozen["new"] = "forbidden"

    def test_canonical_json_and_digest_are_exact(self):
        value = {"z": [2, 1], "a": True}
        expected = '{"a":true,"z":[2,1]}'
        self.assertEqual(validation._canonical_json(value), expected)
        self.assertEqual(validation._canonical_digest(value), hashlib.sha256(expected.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    unittest.main()
