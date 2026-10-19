"""Approved prose and original source through real generate/prepare/run/intake."""
import copy
import json
from pathlib import Path
import unittest

import test_final_reconciliation as fixtures
from repository_intelligence.obligation_reconciliation import derive_engineering


class EngineeringSelectionTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.FinalReconciliationTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.b = self.case.b
        self.request = self.case.request
        self.original = self.b.root / 'original.md'
        self.original.write_text('# Original requirements\n## A5\nReturn the original sum and retain native output.\n')
        self.b.input.write_text('# Engineering decision\n## A5\nChange source.txt through its existing owner.\n'
                                'Keep sum semantics; exercise native sum and retained stdout.\n')
        self.report = self.b.root / 'planning-review.md'
        self.report.write_text('PASS: independently compared A5, source.txt and the expected native sum.\n')
        self.approval = self.b.root / 'planning-approval.json'
        self.selection = dict(phases=['implementor', 'capture', 'qualification', 'review', 'installed', 'closeout'],
                              routes=['normal'], entries=self.case.entries,
                              anchors={'A5': dict(section='A5', original=dict(self.ref(self.original), section='A5'))})
        self.b.runner.write_text(self.b.runner.read_text().replace("  if fault=='request':", "  if fault=='attempt': native['attempt']='old-attempt'\n  if fault=='request':"))
        self.request['runner'] = self.b.op(self.b.runner, '{attempt}', '{candidate}')
        self.request.pop('accepted_capsule')
        self.request['accepted_engineering'] = dict(self.ref(self.b.input), phase='implementor', route='normal',
                                                   selection=['engineering'], approval=self.ref(self.report))
        self.refresh(approve=True)

    def ref(self, path):
        return dict(path=str(path), sha256=self.b.sha(path))

    def refresh(self, *, approve=False):
        binding = {key: self.request['accepted_engineering'][key] for key in ('path', 'sha256', 'phase', 'route')}
        if approve:
            projected = derive_engineering(self.b.input.read_bytes(), binding, self.selection,
                                           load_source=lambda ref: Path(ref['path']).read_bytes())
            self.approval.write_text(json.dumps(dict(decision='approved', specification=self.ref(self.b.input),
                selection_sha256=projected['selection_sha256'], reviewer='fresh-planning-reviewer',
                reviewer_report=self.ref(self.report))))
        self.request['accepted_engineering']['approval'] = self.ref(self.approval)
        self.case.owner_inventory()
        path = Path(self.request['input_inventory']['path'])
        owner = json.loads(path.read_text())
        owner['engineering'] = self.selection
        owner['required'] += [self.ref(p) for p in (self.original, self.report, self.approval)]
        path.write_text(json.dumps(owner))
        self.request['input_inventory']['sha256'] = self.b.sha(path)
        self.request['inputs'] = [self.ref(path), *owner['required']]

    def test_plain_prose_generated_request_return_and_readonly_intake(self):
        self.assertNotIn('ri-obligations', self.b.input.read_text())
        request = copy.deepcopy(self.request)
        request.pop('inputs')
        for name in ('edit', 'capture', 'runner'):
            request[name] = {'argv': request[name]['argv']}
        self.b.request = request
        code, generated = self.b.cli('generate')
        self.assertEqual(code, 0, generated)
        self.b.request = generated
        self.assertEqual(generated['required_outcomes'],
                         {'A5': True, 'S1': True, 'P1': True, 'capture': False, 'installed': False})
        self.assertEqual(self.b.cli('prepare')[0], 0)
        code, result = self.b.cli('run')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['accepted_inventory']['format'], 'engineering-selection-v1')
        self.assertEqual(result['completeness']['entries'][2]['id'], 'P1')
        self.assertGreaterEqual(result['completeness']['entries'][2]['measurements']['seconds'], 0)
        returned = self.b.evidence / 'attempt-1' / 'RETURN.json'
        before = returned.read_bytes()
        code, consumed = self.b.cli('intake')
        self.assertEqual(code, 0, consumed)
        self.assertEqual(consumed['completeness'], result['completeness'])
        self.assertEqual(returned.read_bytes(), before)

    def test_changed_specification_after_review_is_not_new_approval(self):
        self.b.input.write_text(self.b.input.read_text() + 'Changed design after planning review.\n')
        self.request['accepted_engineering'].update(self.ref(self.b.input))
        self.refresh()
        code, result = self.b.cli('prepare')
        self.assertEqual(code, 1, result)
        self.assertIn('planning review', result['error'])
        self.assertEqual((self.b.workspace / 'source.txt').read_text(), 'before\n')

    def test_changed_selection_or_original_binding_needs_new_review(self):
        self.selection['entries'][0]['owner'] = 'different-owner'
        self.refresh()
        code, result = self.b.cli('prepare')
        self.assertEqual(code, 1, result)
        self.assertIn('planning review', result['error'])

    def test_missing_or_wrong_original_section_is_rejected(self):
        self.selection['anchors']['A5']['original']['section'] = 'not-original-A5'
        self.refresh()
        code, result = self.b.cli('prepare')
        self.assertEqual(code, 1, result)
        self.assertIn('unambiguous section', result['error'])

    def test_original_requirement_omission_is_rejected(self):
        self.selection['anchors'] = {}
        self.refresh()
        code, result = self.b.cli('prepare')
        self.assertEqual(code, 1, result)
        self.assertIn('anchor coverage', result['error'])

    def test_rejected_plan_or_missing_report_cannot_dispatch(self):
        approval = json.loads(self.approval.read_text())
        approval['decision'] = 'rejected'
        self.approval.write_text(json.dumps(approval))
        self.refresh()
        self.assertEqual(self.b.cli('prepare')[0], 1)
        self.assertFalse((self.b.evidence / 'attempt-1' / 'LAUNCHED').exists())
        approval['decision'] = 'approved'
        approval['reviewer_report']['sha256'] = '0' * 64
        self.approval.write_text(json.dumps(approval))
        self.refresh()
        self.assertEqual(self.b.cli('prepare')[0], 1)

    def test_plan_changed_between_prepare_and_run_does_not_edit(self):
        self.assertEqual(self.b.cli('prepare')[0], 0)
        self.report.write_text('Changed review after acceptance.\n')
        self.assertEqual(self.b.cli('run')[0], 1)
        self.assertEqual((self.b.workspace / 'source.txt').read_text(), 'before\n')

    def test_original_report_and_approval_must_be_in_owning_inputs(self):
        path = Path(self.request['input_inventory']['path'])
        owner = json.loads(path.read_text())
        owner['required'] = [ref for ref in owner['required'] if ref['path'] != str(self.original)]
        path.write_text(json.dumps(owner))
        self.request['input_inventory']['sha256'] = self.b.sha(path)
        self.request['inputs'] = [self.ref(path), *owner['required']]
        code, result = self.b.cli('prepare')
        self.assertEqual(code, 1, result)
        self.assertIn('missing from selected', result['error'])

    def test_ambiguous_or_fenced_specification_section_is_not_a_requirement(self):
        for text in ('# Plan\n```md\n## A5\nexample only\n```\n', '## A5\none\n## A5\ntwo\n'):
            with self.subTest(text=text):
                self.b.input.write_text(text)
                self.request['accepted_engineering'].update(self.ref(self.b.input))
                self.refresh()
                self.assertEqual(self.b.cli('prepare')[0], 1)

    def test_ambiguous_representation_and_null_selection_do_not_disable_gate(self):
        self.request['accepted_capsule'] = None
        self.assertEqual(self.b.cli('prepare')[0], 1)
        self.request.pop('accepted_capsule')
        self.request['accepted_engineering'] = None
        self.assertEqual(self.b.cli('prepare')[0], 1)

    def test_stale_candidate_attempt_request_and_missing_proof_remain_not_ready(self):
        for fault in ('candidate', 'attempt', 'request', 'omit', 'teardown'):
            with self.subTest(fault=fault):
                case = EngineeringSelectionTests()
                case.setUp()
                try:
                    code, result = case.case.run_case(fault)
                    self.assertEqual(code, 1, result)
                    self.assertFalse(result['review_ready'])
                    self.assertFalse(result['completeness']['ready'])
                    if fault in ('candidate', 'attempt', 'request'):
                        self.assertTrue(any('Stale native ' in error for error in result['completeness']['errors']))
                finally:
                    case.doCleanups()

    def test_intake_rejects_changed_approval_without_rewriting_terminal(self):
        self.assertEqual(self.case.run_case()[0], 0)
        returned = self.b.evidence / 'attempt-1' / 'RETURN.json'
        before = returned.read_bytes()
        self.approval.write_text('{}')
        self.assertEqual(self.b.cli('intake')[0], 1)
        self.assertEqual(returned.read_bytes(), before)
