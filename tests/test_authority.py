"""Direct tests for generic process-local authority."""
from __future__ import annotations
import unittest
from repository_intelligence import authority
from repository_intelligence.errors import ValidationError
from repository_intelligence.identity import AuthenticatedBinding, IdentityBinding, _new_binding

VALUES = {"source_id":"source:one","materialization_id":"materialization:one","configuration_id":"configuration:one","generation_id":"generation:one"}

class AuthorityTests(unittest.TestCase):
    def test_authorities_hold_distinct_ephemeral_32_byte_secrets(self):
        first=authority._Authority("harness"); second=authority._Authority("harness")
        self.assertEqual((first.harness_id,len(first.secret),len(second.secret)),("harness",32,32)); self.assertNotEqual(first.secret,second.secret)
    def test_binding_tuple_preserves_material_dimension_order(self):
        binding=IdentityBinding(**VALUES)
        self.assertEqual(authority._binding_tuple(binding),("source:one","materialization:one","configuration:one","generation:one"))
    def test_authenticated_binding_requires_valid_issuer_signature(self):
        issuer=authority._Authority("harness"); binding=_new_binding(issuer,**VALUES)
        self.assertIs(authority._require_authenticated_binding(binding,"binding"),binding)
        for invalid in (IdentityBinding(**VALUES),AuthenticatedBinding(**VALUES),VALUES):
            with self.subTest(invalid=type(invalid).__name__),self.assertRaisesRegex(ValidationError,"binding must be a harness-authenticated binding"):
                authority._require_authenticated_binding(invalid,"binding")
    def test_signing_is_deterministic_per_authority_and_separates_authorities(self):
        first=authority._Authority("harness"); second=authority._Authority("harness"); value={"z":[2,1],"a":True}
        signature=authority._sign(first,value)
        self.assertEqual(signature,authority._sign(first,{"a":True,"z":[2,1]})); self.assertNotEqual(signature,authority._sign(second,value)); self.assertRegex(signature,r"^[0-9a-f]{64}$")

if __name__=="__main__": unittest.main()
