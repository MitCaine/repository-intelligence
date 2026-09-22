"""Direct tests for generic finite scope grants."""
from __future__ import annotations
import unittest
from repository_intelligence.authority import _Authority
from repository_intelligence.errors import ValidationError
from repository_intelligence.identity import _new_binding
from repository_intelligence.scope import ScopeGrant

class ScopeGrantTests(unittest.TestCase):
    def setUp(self):
        self.binding=_new_binding(_Authority("scope-test"),source_id="source-a",materialization_id="material-a",configuration_id="config-a",generation_id="generation-a")
        self.request={"grant_id":"grant-a","source_binding":self.binding,"configuration_id":"config-a","registry_id":"registry-a","resolution_id":"resolution-a","operations":[{"operation":"modify","path":"src/example.ts","metadata":{"markers":["before"]}}],"preconditions":{"branch":{"allowed":["capsule"]}},"destinations":["working-tree"]}
    def test_grant_is_finite_immutable_and_digest_bound(self):
        grant=ScopeGrant.accept(self.request,self.binding); digest=grant.digest
        self.request["operations"][0]["metadata"]["markers"].append("after"); self.request["preconditions"]["branch"]["allowed"].append("main"); self.request["destinations"].append("outside")
        self.assertEqual(grant.digest,digest); self.assertEqual(grant.operations[0]["metadata"]["markers"],("before",))
        with self.assertRaises(TypeError): grant.preconditions["branch"]={}
        with self.assertRaisesRegex(ValidationError,"digest does not match"): ScopeGrant(**{**grant.__dict__,"_digest":"0"*64})
    def test_wildcards_unknown_operations_and_identity_mismatch_fail_closed(self):
        for operation in ({"operation":"modify","path":"src/*.ts"},{"operation":"read","path":"src/a.ts"}):
            with self.subTest(operation=operation),self.assertRaises(ValidationError): ScopeGrant.accept({**self.request,"operations":[operation]},self.binding)
        other=_new_binding(_Authority("other"),source_id="source-b",materialization_id="material-b",configuration_id="config-b",generation_id="generation-b")
        with self.assertRaisesRegex(ValidationError,"source binding mismatch"): ScopeGrant.accept(self.request,other)

if __name__=="__main__": unittest.main()
