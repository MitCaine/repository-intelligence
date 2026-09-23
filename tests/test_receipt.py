"""Direct tests for strict generic receipt parsing and verification."""
from __future__ import annotations
import copy
from pathlib import Path
import tempfile,unittest
from repository_intelligence import errors,receipt

class ReceiptTests(unittest.TestCase):
    def contract(self):
        paths={"spec":"docs/neutral-contract.json"}; cases={"case-alpha":["check-one"],"case-beta":["check-two","check-three"]}; authority={"claims_are_external":True}; stage={"execution_performed":False}
        bindings={"spec":receipt.AcceptedArtifactBinding(path="docs/neutral-contract.json",accepted_commit="1"*40,git_blob_sha="2"*40,sha256="a"*64)}
        expected=receipt.ReceiptExpectations(receipt_kind="neutral-receipt",receipt_schema_version=3,harness_id="neutral-harness",harness_version="v2",input_paths=paths,cases=cases,authority_boundaries=authority,stage_boundary=stage,input_bindings=bindings)
        value={"receipt_kind":"neutral-receipt","receipt_schema_version":3,"harness":{"id":"neutral-harness","version":"v2"},"inputs":{"spec":bindings["spec"].as_dict()},"cases":[{"case_id":"case-alpha","disposition":"pass","checks":["check-one"]},{"case_id":"case-beta","disposition":"pass","checks":["check-two","check-three"]}],"summary":{"case_count":2,"passed_count":2,"failed_count":0,"overall_disposition":"pass"},"authority_boundaries":{"claims_are_external":True},"stage_boundary":{"execution_performed":False}}
        return expected,value,(paths,cases,authority,stage,bindings)
    def test_valid_closed_object_and_invalid_json_io(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); valid=root/"valid.json"; valid.write_text('{"ok":true,"name":"value"}'); self.assertEqual(dict(receipt._load_receipt(valid)),{"ok":True,"name":"value"})
            for index,text in enumerate(('{"a":1,"a":2}','{"a":NaN}','not-json')):
                path=root/f"bad-{index}.json"; path.write_text(text)
                with self.assertRaises(errors.ReceiptVerificationError):receipt._load_receipt(path)
            with self.assertRaises(errors.ReceiptVerificationError):receipt._load_receipt(root/"missing.json")
    def test_explicit_file_hashing_preserves_bytes_and_io_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"authority.bin"; path.write_bytes(b"abc"); self.assertEqual(receipt._sha256_file(path),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            with self.assertRaises(errors.PilotError):receipt._sha256_file(Path(directory)/"missing")
    def test_receipt_scalars_are_exactly_typed(self):
        self.assertEqual(receipt._receipt_text("value","field"),"value"); self.assertIs(receipt._receipt_bool(True,"flag"),True)
        for value in ("",1,True):
            with self.assertRaises(errors.ReceiptVerificationError):receipt._receipt_text(value,"field")
        for value in (1,"true",None):
            with self.assertRaises(errors.ReceiptVerificationError):receipt._receipt_bool(value,"flag")
    def test_neutral_receipt_validates_and_rejects_authority_drift(self):
        expected,value,_=self.contract(); self.assertIsNone(receipt.validate_receipt(value,expected))
        for path,replacement in ((["harness","id"],"chosen"),(["inputs","spec","path"],"other"),(["cases",0,"checks"],["other"]),(["summary","passed_count"],0),(["authority_boundaries","claims_are_external"],False)):
            changed=copy.deepcopy(value); target=changed
            for key in path[:-1]:target=target[key]
            target[path[-1]]=replacement
            with self.assertRaises((errors.ReceiptVerificationError,errors.ValidationError)):receipt.validate_receipt(changed,expected)
    def test_expectations_defensively_freeze_nested_caller_state(self):
        expected,value,(paths,cases,authority,stage,bindings)=self.contract(); paths["spec"]="mutated"; cases["case-alpha"].append("mutated"); authority["claims_are_external"]=False; stage["execution_performed"]=True; bindings["spec"]=receipt.AcceptedArtifactBinding(path="other",accepted_commit="3"*40,git_blob_sha="4"*40,sha256="b"*64)
        self.assertIsNone(receipt.validate_receipt(value,expected))
        with self.assertRaises(TypeError):expected.input_paths["spec"]="other"
    def test_closed_shape_order_digest_and_boolean_fail_closed(self):
        expected,value,_=self.contract(); variants=[]
        for mutate in (lambda x:x.update(unexpected=True),lambda x:x.pop("summary"),lambda x:x["cases"].reverse(),lambda x:x["inputs"]["spec"].update(path="docs/latest"),lambda x:x["inputs"]["spec"].update(accepted_commit="3"*40),lambda x:x["inputs"]["spec"].update(git_blob_sha="4"*40),lambda x:x["inputs"]["spec"].update(sha256="A"*64),lambda x:x["inputs"]["spec"].update(sha256="abc"),lambda x:x["inputs"]["spec"].update(extra="authority"),lambda x:x["authority_boundaries"].update(claims_are_external=1),lambda x:x["stage_boundary"].update(execution_performed="false")):
            changed=copy.deepcopy(value); mutate(changed); variants.append(changed)
        for variant in variants:
            with self.assertRaises((errors.ReceiptVerificationError,errors.ValidationError)):receipt.validate_receipt(variant,expected)
    def test_accepted_binding_rejects_mutable_or_malformed_authority(self):
        for values in (
            {"path":"docs/latest","accepted_commit":"latest","git_blob_sha":"2"*40,"sha256":"a"*64},
            {"path":"../outside","accepted_commit":"1"*40,"git_blob_sha":"2"*40,"sha256":"a"*64},
            {"path":"docs/spec","accepted_commit":"A"*40,"git_blob_sha":"2"*40,"sha256":"a"*64},
            {"path":"docs/spec","accepted_commit":"1"*40,"git_blob_sha":"2"*39,"sha256":"a"*64},
        ):
            with self.subTest(values=values),self.assertRaises(errors.ValidationError):
                receipt.AcceptedArtifactBinding(**values)
if __name__=="__main__":unittest.main()
