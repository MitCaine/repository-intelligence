"""Direct tests for generic oracle leakage isolation."""
from __future__ import annotations
import unittest
from repository_intelligence import oracle, validation
from repository_intelligence.errors import ValidationError

class OracleIsolationTests(unittest.TestCase):
    def test_typed_equality_rejects_bool_number_collisions(self):
        self.assertFalse(validation._typed_equal(False,0)); self.assertFalse(validation._typed_equal(1,True)); self.assertFalse(validation._typed_equal(1,1.0)); self.assertTrue(validation._typed_equal({"x":[False,1]},{"x":[False,1]}))
    def test_detector_is_redacted_recursive_and_monotonic(self):
        detector=oracle.OracleLeakDetector(({"answer":[0,"yes"]},["needle",1])); leaked=detector.scan("attempt-a",{"nested":{"answer":[0,"yes"]},"text":'["needle",1]'})
        self.assertEqual(leaked.status,"leaked"); self.assertTrue(leaked.invalidated); self.assertGreater(leaked.finding_count,0); self.assertNotIn("needle",repr(leaked.findings))
        later=detector.scan("attempt-a",{"ordinary":"clean"}); self.assertEqual(later.status,"leaked"); self.assertEqual(later.scan_count,2); self.assertEqual(later.finding_count,leaked.finding_count)
    def test_unobserved_disposition_and_empty_protection_fail_closed(self):
        with self.assertRaisesRegex(ValidationError,"at least one"):oracle.OracleLeakDetector(())
        detector=oracle.OracleLeakDetector(("secret",))
        with self.assertRaisesRegex(ValidationError,"has not been observed"):detector.disposition("attempt-a")
if __name__=="__main__":unittest.main()
