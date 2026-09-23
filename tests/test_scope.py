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
        self.request={"grant_id":"grant-a","source_binding":self.binding,"configuration_id":"config-a","registry_id":"registry-a","resolution_id":"resolution-a","operations":[{"operation":"modify","path":"src/example.ts"}],"preconditions":{"branch":"capsule","required_paths":["src/example.ts"],"path_sha256":{"src/example.ts":"a"*64},"package_manager":"npm"},"destinations":["working-tree"]}
    def test_grant_is_finite_immutable_and_digest_bound(self):
        grant=ScopeGrant.accept(self.request,self.binding); digest=grant.digest
        self.request["preconditions"]["required_paths"].append("src/other.ts"); self.request["destinations"].append("outside")
        self.assertEqual(grant.digest,digest); self.assertEqual(grant.preconditions["required_paths"],("src/example.ts",))
        with self.assertRaises(TypeError): grant.preconditions["branch"]={}
        with self.assertRaisesRegex(ValidationError,"digest does not match"): ScopeGrant(**{**grant.__dict__,"_digest":"0"*64})
    def test_wildcards_unknown_operations_and_identity_mismatch_fail_closed(self):
        for operation in ({"operation":"modify","path":"src/*.ts"},{"operation":"read","path":"src/a.ts"},{"operation":"modify","path":"/etc/passwd"},{"operation":"modify","path":"."},{"operation":"modify","path":"../outside"},{"operation":"modify","path":"C:/host"},{"operation":"modify","path":"src\\outside"},{"operation":"modify","path":"src//a.ts"},{"operation":"modify","path":"src/\x00x"},{"operation":"modify","path":"src/a.ts","metadata":{"later":"all-files"}}):
            with self.subTest(operation=operation),self.assertRaises(ValidationError): ScopeGrant.accept({**self.request,"operations":[operation]},self.binding)
        with self.assertRaises(ValidationError):ScopeGrant.accept({**self.request,"operations":[self.request["operations"][0],self.request["operations"][0]]},self.binding)
        for preconditions in ({"branch":"latest"},{"branch":"origin/HEAD"},{"branch":"current-branch"},{"branch":"latest-release"},{"branch":"discover-all"},{"branch":"whatever-is-discovered-later/x"},{"unknown":"all-files"},{"required_paths":["src/*.ts"]},{"required_paths":["src/x","src/x"]},{"path_sha256":{"../x":"a"*64}},{"path_sha256":{"src/x":"A"*64}}):
            with self.subTest(preconditions=preconditions),self.assertRaises(ValidationError):ScopeGrant.accept({**self.request,"preconditions":preconditions},self.binding)
        for destinations in ([],["outside"],["working-tree","working-tree"],["working-tree","outside"]):
            with self.subTest(destinations=destinations),self.assertRaises(ValidationError):ScopeGrant.accept({**self.request,"destinations":destinations},self.binding)
        other=_new_binding(_Authority("other"),source_id="source-b",materialization_id="material-b",configuration_id="config-b",generation_id="generation-b")
        with self.assertRaisesRegex(ValidationError,"source binding mismatch"): ScopeGrant.accept(self.request,other)
        foreign_same=_new_binding(_Authority("foreign-same"),source_id="source-a",materialization_id="material-a",configuration_id="config-a",generation_id="generation-a")
        with self.assertRaisesRegex(ValidationError,"source binding mismatch"): ScopeGrant.accept({**self.request,"source_binding":foreign_same},self.binding)

if __name__=="__main__": unittest.main()
