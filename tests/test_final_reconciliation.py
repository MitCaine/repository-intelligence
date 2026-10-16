"""Selected public generation/RETURN/intake, real native subprocess and retained files."""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import test_worker_execution as fixtures
from repository_intelligence.obligation_reconciliation import bind_native_mapping, derive, reconcile
from repository_intelligence.worker_execution import load_record, verify_reference


RUNNER = r'''
import hashlib,json,os,pathlib,subprocess,sys,time
p=pathlib.Path(sys.argv[1]); candidate=sys.argv[2]
request=p/'CHECK_REQUEST.json'; request_sha=hashlib.sha256(request.read_bytes()).hexdigest()
inventory=json.loads(request.read_bytes())['accepted_obligations']; fault=os.environ.get('FIXTURE_FAULT','')
def ref(path): return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
log=p/'consumer.log'; log.write_text('Actual fixture run at '+candidate+'\n')
rows=[]
for entry in inventory['entries']:
 row={'id':entry['id'],'definition_sha256':entry['definition_sha256'],'mandatory':entry['due_now']}
 if not entry['due_now']:
  row.update(status='pending',next_owner=entry['owner'])
 elif entry['kind']!='proof':
  row.update(status='passed',basis='Accepted edit and actual native proof retained',evidence=[ref(log)])
 else:
  started=time.monotonic()
  command=[sys.executable,'-c','assert 2+2==4; print("native sum proof")']
  observed=subprocess.run(command,capture_output=True)
  stdout=p/(entry['id']+'.stdout'); stdout.write_bytes(observed.stdout)
  native={'case':entry['native_id'],'status':observed.returncode,'candidate':candidate,
          'attempt':p.name,'request_sha256':request_sha,'duration':time.monotonic()-started,
          'artifacts':{'stdout':ref(stdout)},'argv':command}
  if fault=='substitution': native['case']='unrelated.same-label-proof'
  if fault=='candidate': native['candidate']='0'*40
  if fault=='request': native['request_sha256']='0'*64
  if fault in ('missing-value','measurement'): del native['duration']
  if fault=='unknown-value': native['duration']='unknown'
  native_path=p/(entry['id']+'.json'); native_path.write_text(json.dumps(native))
  row.update(status='passed',native={'record':ref(native_path)})
  if fault=='mapping-override': row['native']['fields']={'status':['duration']}
  if fault=='teardown': stdout.unlink()
  if fault=='defer-due': row.update(status='pending',next_owner=entry['owner'],mandatory=False)
 rows.append(row)
if fault=='omit': rows=[row for row in rows if row['id']!='P1']
if fault=='rename': next(row for row in rows if row['id']=='P1')['id']='easier-P1'
if fault=='duplicate': rows.append(dict(rows[0]))
if fault=='future-owner': rows[-1]['next_owner']='wrong-owner'
facts={'request_digests':{'raw_file_sha256':request_sha},'source_stable':True,'terminal_complete':True,
       'inventory_sha256':inventory['inventory_sha256'],'outcomes':rows}
if fault=='inventory': facts['inventory_sha256']='0'*64
if fault=='definition': rows[0]['definition_sha256']='0'*64
r={'commit':candidate,'repository':str(pathlib.Path.cwd()),'attempt':p.name,'eligible':True,
   'request_sha256':request_sha,'refs':[ref(log)],'facts':facts}
detail=p/'runner-detail.log'; detail.write_text('Extra retained native runner detail\n')
r['refs'].append(ref(detail))
(p/'consumer.json').write_text(json.dumps(r))
'''


class FinalReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkerExecutionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.b = self.fixture
        self.request = self.b.request
        common = dict(outcome='A5', due='implementor', owner='implementor', routes=['normal'])
        self.entries = [dict(common, id='A5', kind='outcome'), dict(common, id='S1', kind='step'),
                        dict(common, id='P1', kind='proof', native_id='original.sum-proof', success=0,
                             artifacts=['stdout'], measurements=['seconds']),
                        dict(common, id='capture', kind='step', due='capture', owner='controller'),
                        dict(common, id='installed', kind='proof', due='installed', owner='controller',
                             native_id='installed-proof', success=0, artifacts=[], measurements=[])]
        self.capsule()
        self.b.runner.write_text('#!/bin/sh\nset -e\npython3 - "$1" "$2" <<\'PYCODE\'\n'+RUNNER+'\nPYCODE\n')
        self.request['runner'] = self.b.op(self.b.runner, '{attempt}', '{candidate}')
        self.request['conformance'] = ['facts']
        self.owner_inventory()

    def owner_inventory(self):
        mapping = {'fields':{key:[key] for key in ('case','status','candidate','attempt','request_sha256')},
                   'artifacts':{'stdout':['artifacts','stdout']},'measurements':{'seconds':['duration']}}
        path = self.b.root/'owner-inventory.json'
        inputs = [dict(path=str(value),sha256=self.b.sha(value))
                  for value in (self.b.input,self.b.runner,self.b.capture,self.b.edit)]
        path.write_text(json.dumps({'required':inputs,'native_proof':{'original.sum-proof':mapping}}))
        self.request['input_inventory'] = dict(path=str(path),sha256=self.b.sha(path),keys=['required'])
        self.request['inputs'] = [dict(path=str(path),sha256=self.b.sha(path)),*inputs]
        self.request['proof_mapping'] = ['native_proof']

    def capsule(self):
        body = dict(phases=['implementor','capture','qualification','review','installed','closeout'],
                    routes=['normal'], entries=self.entries)
        self.b.input.write_text('# Task\n## Objective\nOriginal case\n## Source and scope\nS1: edit source.txt\n'
                                '## Acceptance\n- [ ] A5: original sum behavior\n## Checks\n```ri-obligations\n'+
                                json.dumps(body)+'\n```\n## Prerequisites\nNone\n## Handoff and closeout\nController owns later phases\n')
        self.request['inputs'] = [dict(path=str(self.b.input), sha256=self.b.sha(self.b.input))]
        self.request['accepted_capsule'] = dict(self.request['inputs'][0], phase='implementor', route='normal')
        if 'input_inventory' in self.request:
            self.owner_inventory()

    def run_case(self, fault=''):
        self.request['environment']['FIXTURE_FAULT'] = fault
        self.assertEqual(self.b.cli('prepare')[0], 0)
        return self.b.cli('run')

    def test_generated_inventory_success_and_same_intake_future_pending(self):
        request = dict(self.request)
        del request['inputs']
        for name in ('edit','capture','runner'):
            request[name]={'argv':self.request[name]['argv']}
        self.b.request = request
        code, generated = self.b.cli('generate')
        self.assertEqual(code, 0, generated)
        self.assertEqual(generated['required_outcomes'],
                         {'A5':True,'S1':True,'P1':True,'capture':False,'installed':False})
        self.b.request = generated
        self.assertEqual(self.b.cli('prepare')[0], 0)
        code, result = self.b.cli('run')
        self.assertEqual(code, 0, result)
        self.assertTrue(result['completeness']['ready'])
        pending = [row for row in result['completeness']['entries'] if row['status']=='pending']
        self.assertEqual(pending, [dict(id='capture',status='pending',next_owner='controller'),
                                   dict(id='installed',status='pending',next_owner='controller')])
        returned = (self.b.evidence/'attempt-1'/'RETURN.json').read_bytes()
        code, consumed = self.b.cli('intake')
        self.assertEqual(code, 0, consumed)
        self.assertEqual(consumed['completeness'], result['completeness'])
        self.assertEqual((self.b.evidence/'attempt-1'/'RETURN.json').read_bytes(), returned)
        self.assertGreaterEqual(next(row for row in result['completeness']['entries']
                                     if row['id']=='P1')['measurements']['seconds'], 0)

    def test_missing_prescribed_proof_is_not_hidden_by_passing_outcome(self):
        code, result = self.run_case('omit')
        self.assertEqual(code, 1)
        self.assertTrue(any('coverage mismatch' in error for error in result['completeness']['errors']))
        self.assertEqual(result['operations'][-1]['exit_code'], 0)

    def test_renamed_proof_cannot_discharge_original_identity(self):
        code, result = self.run_case('rename')
        self.assertEqual(code, 1)
        self.assertFalse(result['completeness']['ready'])

    def test_same_label_unrelated_native_case_cannot_discharge_original(self):
        code, result = self.run_case('substitution')
        self.assertEqual(code, 1)
        self.assertIn('P1: Prescribed native case substituted', result['completeness']['errors'])

    def test_required_post_teardown_artifact_missing(self):
        code, result = self.run_case('teardown')
        self.assertEqual(code, 1)
        self.assertFalse(result['review_ready'])

    def test_required_measurement_binding_missing(self):
        code, result = self.run_case('measurement')
        self.assertEqual(code, 1)
        self.assertIn('P1: Required measurement unavailable: seconds', result['completeness']['errors'])

    def test_required_native_measurement_value_missing(self):
        code, result = self.run_case('missing-value')
        self.assertEqual(code, 1)
        self.assertFalse(result['completeness']['ready'])

    def test_unknown_native_measurement_is_not_a_required_measurement(self):
        code, result = self.run_case('unknown-value')
        self.assertEqual(code, 1)
        self.assertIn('P1: Required measurement unavailable: seconds', result['completeness']['errors'])

    def test_worker_cannot_override_authoritative_native_status_mapping(self):
        code, result = self.run_case('mapping-override')
        self.assertEqual(code, 1)
        self.assertIn('P1: Native proof binding unavailable', result['completeness']['errors'])

    def test_duplicate_id_cannot_satisfy_accounting(self):
        code, result = self.run_case('duplicate')
        self.assertEqual(code, 1)
        self.assertIn('Missing or duplicate original identity', result['completeness']['errors'])

    def test_stale_native_candidate_binding(self):
        code, result = self.run_case('candidate')
        self.assertEqual(code, 1)
        self.assertIn('P1: Stale native candidate', result['completeness']['errors'])

    def test_stale_native_request_binding(self):
        code, result = self.run_case('request')
        self.assertEqual(code, 1)
        self.assertIn('P1: Stale native request_sha256', result['completeness']['errors'])

    def test_stale_inventory_binding(self):
        code, result = self.run_case('inventory')
        self.assertEqual(code, 1)
        self.assertIn('Accepted inventory binding mismatch', result['completeness']['errors'])

    def test_criterion_definition_substitution(self):
        code, result = self.run_case('definition')
        self.assertEqual(code, 1)
        self.assertIn('A5: Original definition binding mismatch', result['completeness']['errors'])

    def test_due_proof_cannot_be_reclassified_future(self):
        code, result = self.run_case('defer-due')
        self.assertEqual(code, 1)
        self.assertFalse(result['completeness']['ready'])

    def test_future_pending_retains_accepted_owner(self):
        code, result = self.run_case('future-owner')
        self.assertEqual(code, 1)
        self.assertIn('installed: Future obligation lost accepted next owner', result['completeness']['errors'])

    def test_intake_rechecks_artifacts_without_overwriting_original_return(self):
        code, result = self.run_case()
        self.assertEqual(code, 0, result)
        attempt = self.b.evidence/'attempt-1'
        returned = (attempt/'RETURN.json').read_bytes()
        (attempt/'P1.stdout').unlink()
        code, result = self.b.cli('intake')
        self.assertEqual(code, 1)
        self.assertEqual((attempt/'RETURN.json').read_bytes(), returned)

    def test_intake_rejects_changed_native_evidence(self):
        self.assertEqual(self.run_case()[0], 0)
        (self.b.evidence/'attempt-1'/'P1.json').write_text('{}')
        self.assertEqual(self.b.cli('intake')[0], 1)

    def test_intake_rejects_changed_selected_candidate(self):
        self.assertEqual(self.run_case()[0], 0)
        self.b.git(self.b.workspace, 'reset', '--hard', self.request['base'])
        self.assertEqual(self.b.cli('intake')[0], 1)

    def test_duplicate_accepted_case_refused_before_edit(self):
        self.entries.append(dict(self.entries[2]))
        self.capsule()
        self.assertEqual(self.b.cli('prepare')[0], 1)
        self.assertEqual((self.b.workspace/'source.txt').read_text(), 'before\n')

    def test_changed_accepted_source_refuses_before_edit(self):
        self.assertEqual(self.b.cli('prepare')[0], 0)
        self.b.input.write_text(self.b.input.read_text()+'changed original A5\n')
        self.assertEqual(self.b.cli('run')[0], 1)
        self.assertEqual((self.b.workspace/'source.txt').read_text(), 'before\n')

    def test_handwritten_competing_required_set_refused(self):
        self.request['required_outcomes']={'A5':True}
        self.assertEqual(self.b.cli('prepare')[0], 1)

    def test_null_selection_cannot_disable_required_reconciliation(self):
        self.request['accepted_capsule']=None
        self.assertEqual(self.b.cli('prepare')[0],1)
        self.assertEqual(self.b.cli('intake')[0],1)

    def test_intake_requires_selected_binding(self):
        del self.request['accepted_capsule']
        code,result=self.b.cli('intake')
        self.assertEqual(code,1)
        self.assertIn('selected accepted-capsule',result['error'])

    def test_due_native_mapping_omission_caught_before_edit(self):
        path = Path(self.request['input_inventory']['path'])
        owner = json.loads(path.read_text())
        owner['native_proof']['original.sum-proof']['measurements']={}
        path.write_text(json.dumps(owner))
        self.request['input_inventory']['sha256']=self.b.sha(path)
        self.request['inputs'][0]['sha256']=self.b.sha(path)
        self.assertEqual(self.b.cli('prepare')[0], 1)
        self.assertEqual((self.b.workspace/'source.txt').read_text(), 'before\n')

    def test_return_operation_omission_not_accepted_by_intake(self):
        self.assertEqual(self.run_case()[0], 0)
        path=self.b.evidence/'attempt-1'/'RETURN.json'
        result=json.loads(path.read_text()); result['operations']=[]
        path.write_text(json.dumps(result))
        self.assertEqual(self.b.cli('intake')[0], 1)

    def test_dropped_return_reference_cannot_hide_missing_native_log(self):
        self.assertEqual(self.run_case()[0],0)
        attempt=self.b.evidence/'attempt-1'
        returned=attempt/'RETURN.json'; result=json.loads(returned.read_text())
        detail=attempt/'runner-detail.log'
        result['references']=[ref for ref in result['references'] if ref['path']!=str(detail)]
        returned.write_text(json.dumps(result)); detail.unlink()
        code,consumed=self.b.cli('intake')
        self.assertEqual(code,1,consumed)

    def test_empty_or_tampered_terminal_reference_view_is_not_consumed(self):
        self.assertEqual(self.run_case()[0],0)
        attempt=self.b.evidence/'attempt-1'
        returned=attempt/'RETURN.json'; original=returned.read_bytes()
        detail=attempt/'runner-detail.log'; detail_bytes=detail.read_bytes()
        for fault in ('empty','drop','tamper'):
            with self.subTest(fault=fault):
                result=json.loads(original)
                detail.write_bytes(detail_bytes)
                if fault=='empty':
                    result['references']=[]
                else:
                    result['references']=[ref for ref in result['references'] if ref['path']!=str(detail)]
                    if fault=='tamper':
                        detail.write_bytes(b'changed native runner detail')
                returned.write_text(json.dumps(result))
                self.assertEqual(self.b.cli('intake')[0],1)

    def test_native_pre_capture_handoff_does_not_force_a_worker_commit(self):
        head = self.b.git(self.b.workspace, 'rev-parse', 'HEAD')
        source = self.b.workspace/'source.txt'
        source.write_text('after\n')
        snapshot = hashlib.sha256(source.read_bytes()).hexdigest()
        inventory = derive(self.b.input.read_bytes(), self.request['accepted_capsule'])
        owner = self.request['input_inventory']
        mapping = load_record(dict(path=owner['path'],sha256=owner['sha256']))['native_proof']
        inventory = bind_native_mapping(inventory,mapping,dict(path=owner['path'],sha256=owner['sha256'],keys=['native_proof']))
        attempt=self.b.evidence/'native-pre-capture'; attempt.mkdir()
        check=attempt/'CHECK_REQUEST.json'; check.write_text(json.dumps({'accepted_obligations':inventory}))
        result = subprocess.run([str(self.b.runner),str(attempt),snapshot], cwd=self.b.workspace,
                                env=self.request['environment'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        facts=json.loads((attempt/'consumer.json').read_bytes())['facts']
        assessment=reconcile(inventory,facts,dict(candidate=snapshot,attempt=attempt.name,
                             request_sha256=hashlib.sha256(check.read_bytes()).hexdigest()),
                             load_record=load_record,verify_reference=verify_reference)
        self.assertTrue(assessment['ready'],assessment)
        self.assertEqual(next(row for row in assessment['entries'] if row['id']=='capture'),
                         dict(id='capture',status='pending',next_owner='controller'))
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),snapshot)
        self.assertEqual(self.b.git(self.b.workspace,'rev-parse','HEAD'),head)
        self.assertFalse((attempt/'LAUNCHED').exists())
