import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from repository_intelligence.adapter_conformance import assess, request_digests
from repository_intelligence.worker_execution import execute, identity, read, save, ExecutionError


class WorkerExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.workspace = self.root / 'workspace'
        self.protected = self.root / 'protected'
        for repo in (self.workspace, self.protected):
            repo.mkdir()
            self.git(repo, 'init', '-q')
            self.git(repo, 'config', 'user.email', 'fixture@example.invalid')
            self.git(repo, 'config', 'user.name', 'Fixture')
            (repo / 'source.txt').write_text('before\n')
            self.git(repo, 'add', '.')
            self.git(repo, 'commit', '-qm', 'base')
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.input = self.root / 'handoff.md'
        self.input.write_text('Accepted fixture: change source.txt; local commit authorized.\n')
        self.edit = self.script('edit', 'printf "after\\n" > source.txt\n')
        self.capture = self.script('capture', 'git add source.txt\ngit commit -qm candidate\n')
        self.runner = self.script('runner', '''python3 - "$1" "$2" <<'PYCODE'
import hashlib,json,pathlib,subprocess,sys
p=pathlib.Path(sys.argv[1]);log=p/'consumer.log';log.write_text('one checked outcome\\n')
r={'commit':sys.argv[2], 'repository':str(pathlib.Path.cwd()),'attempt':p.name,'eligible':True,'request_sha256':hashlib.sha256((p/'CHECK_REQUEST.json').read_bytes()).hexdigest(),
'refs':[{'path':str(log),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()}]}
(p/'consumer.json').write_text(json.dumps(r))
PYCODE
''')
        self.request = dict(assignment='fixture-1', attempt='attempt-1', workspace=str(self.workspace),
            protected_repository=str(self.protected), base=self.git(self.workspace, 'rev-parse', 'HEAD').strip(),
            inputs=[dict(path=str(self.input), sha256=self.sha(self.input))], allowed_changes=['source.txt'],
            capture_authority='handoff.md local fixture capture grant', environment=dict(PATH=os.environ['PATH'], HOME=str(self.root)),
            edit=self.op(self.edit), capture=self.op(self.capture), runner=self.op(self.runner, '{attempt}', '{candidate}'),
            runner_result='consumer.json', require_new_candidate=True, check_request=dict(repository='{workspace}',commit='{candidate}',attempt='{attempt}'),
            result_bindings=dict(candidate=['commit'],workspace=['repository'],attempt=['attempt'],ready=['eligible'],references=['refs'],request_sha256=['request_sha256']))

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True)

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def script(self, name, text):
        p=self.root/(name+'.sh');p.write_text('#!/bin/sh\nset -e\n'+text);p.chmod(0o755);return p

    def op(self, script, *args):
        return dict(argv=[str(script),*args],executable_sha256=self.sha(script))

    def cli(self, mode):
        p=self.root/'request.json';p.write_text(json.dumps(self.request))
        c=subprocess.run([sys.executable,'-m','repository_intelligence.worker_execution','--request',str(p),
            '--evidence',str(self.evidence),'--mode',mode],capture_output=True,text=True)
        return c.returncode,json.loads(c.stdout)

    def test_real_entrypoint_preparation_capture_runner_return_and_no_retry(self):
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,0,result)
        self.assertTrue(result['review_ready'])
        self.assertEqual([row['operation'] for row in result['operations']], ['edit', 'capture', 'runner'])
        for row in result['operations']:
            self.assertGreaterEqual(row['duration_seconds'], 0)
            self.assertTrue(math.isfinite(row['duration_seconds']))
        self.assertEqual(result['prepared']['sha256'], self.sha(self.evidence/'attempt-1'/'PREPARED.json'))
        self.assertEqual(result['changed_paths'],['source.txt'])
        self.assertNotEqual(result['candidate'],self.request['base'])
        self.assertEqual((self.protected/'source.txt').read_text(),'before\n')
        old=(self.evidence/'attempt-1'/'RETURN.json').read_bytes()
        self.assertEqual(self.cli('run')[0],1)
        self.assertEqual((self.evidence/'attempt-1'/'RETURN.json').read_bytes(),old)

    def test_substitution_and_authority_binding_refused_before_edit(self):
        self.assertEqual(self.cli('prepare')[0],0)
        self.request['capture_authority']='different grant'
        self.assertEqual(self.cli('run')[0],1)
        self.assertEqual((self.workspace/'source.txt').read_text(),'before\n')
        self.request['workspace']=str(self.protected)
        self.assertEqual(self.cli('run')[0],1)
        self.assertFalse((self.evidence/'attempt-1'/'LAUNCHED').exists())

    def test_missing_capture_and_plain_log_return_are_not_ready(self):
        for name, capture, runner in [('missing', 'true\n', None),('plain',None,'printf "PASS\\n"\n')]:
            with self.subTest(name=name):
                self.request['attempt']=name
                self.request['require_new_candidate']=name=='missing'
                self.request.pop('edit',None)
                self.request['capture']=self.op(self.script('capture-'+name,capture or 'true\n'))
                self.request['runner']=self.op(self.script('runner-'+name,runner or 'true\n'))
                self.assertEqual(self.cli('prepare')[0],0)
                code,result=self.cli('run');self.assertEqual(code,1,result);self.assertFalse(result['review_ready'])

    def test_stale_reference_and_failed_partial_launch_preserve_outputs(self):
        self.request['runner']=self.op(self.script('stale', '''python3 - "$1" "$2" <<'PYCODE'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);log=p/'log';log.write_text('changed')
(p/'consumer.json').write_text(json.dumps({'commit':sys.argv[2],'repository':str(pathlib.Path.cwd()),'attempt':p.name,'eligible':True,'request_sha256':hashlib.sha256((p/'CHECK_REQUEST.json').read_bytes()).hexdigest(),'refs':[{'path':str(log),'sha256':'0'*64}]}))
PYCODE
'''),'{attempt}','{candidate}')
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,1);self.assertIn('Stale evidence',result['error'])
        old=(self.evidence/'attempt-1'/'RETURN.json').read_bytes()
        self.request['attempt']='failed';self.request['base']=self.git(self.workspace,'rev-parse','HEAD').strip()
        self.request.pop('edit');self.request['require_new_candidate']=False
        self.request['capture']=self.op(self.script('failed','echo diagnostic\nexit 7\n'))
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,1)
        self.assertEqual(result['operations'][0]['exit_code'],7)
        self.assertFalse(result['review_ready'])
        self.assertEqual((self.evidence/'attempt-1'/'RETURN.json').read_bytes(),old)

    def test_failed_runner_retains_consumer_result_and_log_references(self):
        text=self.runner.read_text().replace("'eligible':True", "'eligible':False")+'exit 7\n'
        self.runner.write_text(text)
        self.request['runner']=self.op(self.runner,'{attempt}','{candidate}')
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,1)
        self.assertFalse(result['review_ready'])
        self.assertEqual(result['operations'][-1]['exit_code'],7)
        self.assertGreaterEqual(result['operations'][-1]['duration_seconds'], 0)
        self.assertEqual(result['runner_result']['sha256'],self.sha(self.evidence/'attempt-1'/'consumer.json'))
        self.assertEqual(result['references'][0]['sha256'],self.sha(self.evidence/'attempt-1'/'consumer.log'))

    def test_timeout_records_partial_invocation_output(self):
        self.request['timeout_seconds']=1
        self.request['capture']=self.op(self.script('timeout','echo partial\nexec sleep 2\n'))
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,1)
        row=result['operations'][-1]
        self.assertEqual(row['status'],'incomplete')
        self.assertGreaterEqual(row['duration_seconds'], 0.9)
        self.assertTrue(math.isfinite(row['duration_seconds']))
        self.assertIsNone(row['exit_code'])
        self.assertEqual(row['stdout']['sha256'],hashlib.sha256(b'partial\n').hexdigest())
        self.assertFalse(result['review_ready'])

    def test_large_regular_identities_and_changed_truncated_input_refusal(self):
        payload=b'large identity\n'*100000
        self.input.write_bytes(payload)
        self.request['inputs'][0]['sha256']=hashlib.sha256(payload).hexdigest()
        self.assertEqual(identity(self.input)['sha256'],hashlib.sha256(payload).hexdigest())
        with self.assertRaises(ExecutionError):read(self.input)
        self.assertEqual(self.cli('prepare')[0],0)
        self.input.write_bytes(payload[:-1])
        self.assertEqual(self.cli('run')[0],1)
        self.assertFalse((self.evidence/'attempt-1'/'LAUNCHED').exists())

    def test_malformed_bindings_refuse_before_attempt_or_operations(self):
        for binding in ([], [''], 'commit', [3], ['a']*33):
            self.request['result_bindings']['candidate']=binding
            code,result=self.cli('prepare');self.assertEqual(code,1,result)
            self.assertFalse((self.evidence/'attempt-1').exists())
            self.assertEqual((self.workspace/'source.txt').read_text(),'before\n')

    def test_interactive_edits_and_authorized_commit_preserve_original_base(self):
        self.request['route']='interactive';self.request.pop('edit')
        self.assertEqual(self.cli('prepare')[0],0)
        (self.workspace/'source.txt').write_text('interactive\n')
        self.git(self.workspace,'add','source.txt');self.git(self.workspace,'commit','-qm','worker commit')
        current=self.git(self.workspace,'rev-parse','HEAD').strip()
        self.request['capture']=self.op(self.script('capture-unchanged','true\n'))
        # Changing the selected capture after preparation is refused.
        self.assertEqual(self.cli('run')[0],1)
        self.request['capture']=self.op(self.capture)
        self.capture.write_text('#!/bin/sh\nset -e\ngit diff --quiet && git diff --cached --quiet\n')
        self.request['capture']=self.op(self.capture)
        self.assertEqual(self.cli('run')[0],1)
        self.assertEqual(self.git(self.workspace,'rev-parse','HEAD').strip(),current)

    def test_interactive_dirty_and_precommitted_valid_counterparts(self):
        for committed in (False,True):
            # Each case has its own prepared attempt/base and selected idempotent capture.
            self.request['attempt']='interactive-'+str(committed)
            self.request['base']=self.git(self.workspace,'rev-parse','HEAD').strip()
            self.request['route']='interactive';self.request.pop('edit',None)
            capture=self.script('capture-interactive', 'git add source.txt\nif ! git diff --cached --quiet; then git commit -qm captured; fi\n')
            self.request['capture']=self.op(capture)
            self.assertEqual(self.cli('prepare')[0],0)
            (self.workspace/'source.txt').write_text(str(committed)+'\n')
            if committed:
                self.git(self.workspace,'add','source.txt');self.git(self.workspace,'commit','-qm','authorized edit')
            code,result=self.cli('run');self.assertEqual(code,0,result)
            self.assertEqual(result['base'],self.request['base']);self.assertTrue(result['review_ready'])
            self.assertEqual(result['changed_paths'],['source.txt'])

    def test_interactive_out_of_scope_and_hidden_index_refusal(self):
        self.request['route']='interactive';self.request.pop('edit')
        self.assertEqual(self.cli('prepare')[0],0)
        (self.workspace/'outside.txt').write_text('not authorized')
        code,result=self.cli('run');self.assertEqual(code,1)
        self.assertIn('exceed original',result['error']);self.assertEqual(result['operations'],[])

    def test_large_runner_output_and_evidence_remain_eligible(self):
        self.runner.write_text(self.runner.read_text().replace("log.write_text('one checked outcome\\n')", "log.write_text('x'*1000001)")+"python3 -c 'import sys;sys.stdout.write(\"x\"*1000001)'\n")
        self.request['runner']=self.op(self.runner,'{attempt}','{candidate}')
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,0,result)
        expected=hashlib.sha256(b'x'*1000001).hexdigest()
        self.assertEqual(result['operations'][-1]['stdout']['sha256'],expected)
        self.assertEqual(result['references'][0]['sha256'],expected)

    def test_interactive_staged_mask_and_hidden_flags_refuse_before_capture(self):
        outside=self.workspace/'outside.txt';outside.write_text('original\n')
        self.git(self.workspace,'add','.');self.git(self.workspace,'commit','-qm','baseline outside')
        self.request['base']=self.git(self.workspace,'rev-parse','HEAD').strip()
        self.request['route']='interactive';self.request.pop('edit')
        self.assertEqual(self.cli('prepare')[0],0)
        outside.write_text('unauthorized\n');self.git(self.workspace,'add','outside.txt')
        outside.write_text('original\n');(self.workspace/'source.txt').write_text('authorized\n')
        code,result=self.cli('run');self.assertEqual(code,1)
        self.assertEqual(result['operations'],[])
        self.assertIn('exceed original',result['error'])
        self.git(self.workspace,'reset','--hard','-q')
        self.request['attempt']='hidden-index'
        self.assertEqual(self.cli('prepare')[0],0)
        self.git(self.workspace,'update-index','--assume-unchanged','source.txt')
        (self.workspace/'source.txt').write_text('hidden\n')
        code,result=self.cli('run');self.assertEqual(code,1)
        self.assertEqual(result['operations'],[])
        self.assertIn('Hidden index',result['error'])

    def test_reserved_outputs_and_invalid_environment_are_preparation_refusals(self):
        for name in ('capture.stdout','runner.stderr','CHECK_REQUEST.json','RETURN.json.tmp-old'):
            self.request['runner_result']=name
            self.assertEqual(self.cli('prepare')[0],1)
            self.assertFalse((self.evidence/'attempt-1').exists())
        self.request['runner_result']='consumer.json'
        for key,value in [('BAD=KEY','v'),('GOOD','bad\x00value'),('','v')]:
            self.request['environment']={key:value}
            self.assertEqual(self.cli('prepare')[0],1)
            self.assertFalse((self.evidence/'attempt-1').exists())
        self.assertEqual((self.workspace/'source.txt').read_text(),'before\n')

    def test_return_temporary_residue_does_not_prevent_valid_run(self):
        self.assertEqual(self.cli('prepare')[0],0)
        residue=self.evidence/'attempt-1'/'RETURN.tmp';residue.write_text('historical residue')
        self.assertEqual(self.cli('run')[0],0)
        self.assertEqual(residue.read_text(),'historical residue')

    def test_final_rename_authorizes_both_endpoints(self):
        self.request['allowed_changes']=['destination.txt']
        self.request['edit']=self.op(self.script('rename','git mv source.txt destination.txt\n'))
        self.request['capture']=self.op(self.script('rename-capture','git add .\ngit commit -qm rename\n'))
        self.assertEqual(self.cli('prepare')[0],0)
        code,r=self.cli('run');self.assertEqual(code,1)
        self.assertFalse(any(x['operation']=='runner' for x in r['operations']))
        self.git(self.workspace,'reset','--hard','-q',self.request['base'])
        self.request['attempt']='rename-positive';self.request['allowed_changes']=['source.txt','destination.txt']
        self.assertEqual(self.cli('prepare')[0],0)
        code,r=self.cli('run');self.assertEqual(code,0,r)
        self.assertEqual(set(r['changed_paths']),{'source.txt','destination.txt'})

    @unittest.skipUnless(os.name=='posix','Owned POSIX process groups required')
    def test_timeout_descendant_cannot_change_output_after_return(self):
        self.request['timeout_seconds']=1
        self.request['capture']=self.op(self.script('descendant', '(sleep 2; echo late) &\nwait\n'))
        self.assertEqual(self.cli('prepare')[0],0)
        code,r=self.cli('run');self.assertEqual(code,1)
        log=self.evidence/'attempt-1'/'capture.stdout';before=log.read_bytes();time.sleep(1.2)
        self.assertEqual(log.read_bytes(),before)
        self.assertNotIn(b'late',before)
        self.assertFalse(r['review_ready'])

    def test_correction_frame_keeps_full_integration_and_recovery_delta(self):
        original=self.request['base']
        (self.workspace/'prior.txt').write_text('prior')
        self.git(self.workspace,'add','.');self.git(self.workspace,'commit','-qm','C1')
        self.request['base']=self.git(self.workspace,'rev-parse','HEAD').strip()
        self.request['integration_base']=original
        self.assertEqual(self.cli('prepare')[0],0)
        code,r=self.cli('run');self.assertEqual(code,0,r)
        self.assertEqual(r['changed_paths'],['source.txt'])
        self.assertEqual(set(r['integration_changed_paths']),{'prior.txt','source.txt'})
        self.assertEqual(r['recovery_base'],self.request['base'])
        self.assertEqual(r['integration_base'],original)

    def test_conformance_refuses_stable_failed_or_incomplete_facts(self):
        hashes=request_digests(b'{"b":2, "a":1}\n')
        self.assertNotEqual(hashes['raw_file_sha256'],hashes['canonical_json_sha256'])
        facts=dict(request_digests=hashes,source_stable=True,terminal_complete=True,
                   outcomes=[dict(mandatory=True,status='passed'),dict(mandatory=False,status='failed')])
        self.assertTrue(assess(facts,hashes)['ready'])
        facts['outcomes'][0]['status']='failed';self.assertFalse(assess(facts,hashes)['ready'])
        facts['outcomes'][0]['status']='passed';facts['terminal_complete']=False
        self.assertFalse(assess(facts,hashes)['ready'])
        facts['terminal_complete']=True;facts['request_digests']={'unknown':'0'*64}
        self.assertFalse(assess(facts,hashes)['ready'])

    def test_selected_conformance_blocks_failed_mandatory_despite_exit_zero(self):
        original=self.runner.read_text()
        addition="""raw=(p/'CHECK_REQUEST.json').read_bytes()
r['facts']={'source_stable':True,'terminal_complete':True,
'outcomes':[{'mandatory':True,'status':'failed'}],
'request_digests':{'raw_file_sha256':hashlib.sha256(raw).hexdigest(),
'canonical_json_sha256':hashlib.sha256(json.dumps(json.loads(raw),sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()}}
"""
        self.runner.write_text(original.replace("(p/'consumer.json').write_text",addition+"(p/'consumer.json').write_text"))
        self.request['runner']=self.op(self.runner,'{attempt}','{candidate}')
        self.request['conformance']=['facts']
        self.request['required_outcomes']={'omitted': True}
        self.assertEqual(self.cli('prepare')[0],0)
        code,r=self.cli('run');self.assertEqual(code,1)
        self.assertEqual(r['operations'][-1]['exit_code'],0)
        self.assertFalse(r['review_ready']);self.assertFalse(r['conformance']['ready'])
        self.assertEqual(r['conformance']['outcomes'][0]['status'],'failed')

    def test_unrepresentable_native_inputs_refused_before_effects(self):
        for location in ('argv', 'key', 'value'):
            with self.subTest(location=location):
                if location == 'argv':
                    self.request['capture']['argv'].append('\ud800')
                else:
                    self.request['environment'] = {('\ud800' if location == 'key' else 'VALID'): '\ud800'}
                code, result = self.cli('prepare')
                self.assertEqual(code, 1, result)
                self.assertEqual((self.workspace/'source.txt').read_text(), 'before\n')
                self.assertFalse((self.evidence/'attempt-1').exists())
                self.request['capture']['argv'] = [str(self.capture)]
                self.request['environment'] = dict(PATH=os.environ['PATH'], HOME=str(self.root))

    def test_unknown_runner_cleanup_never_authenticates_outputs(self):
        from repository_intelligence import worker_execution
        execute(self.request, self.evidence, 'prepare')
        original = worker_execution.owned_run
        def uncertain(*args, **kwargs):
            result = original(*args, **kwargs)
            if args[0][0] == str(self.runner):
                raise PermissionError('injected cleanup uncertainty')
            return result
        with patch.object(worker_execution, 'owned_run', side_effect=uncertain):
            result = execute(self.request, self.evidence, 'run')
        self.assertFalse(result['review_ready'])
        self.assertEqual(result['runner_result']['status'], 'not-final')
        self.assertNotIn('sha256', result['runner_result'])
        self.assertNotIn('references', result)

    def test_public_runner_omission_and_future_obligation_control(self):
        original = self.runner.read_text()
        addition = """r['facts']={'source_stable':True,'terminal_complete':True,
'outcomes':[{'id':'check','mandatory':True,'status':'passed'},
{'id':'installed','mandatory':False,'status':'pending'}],
'request_digests':{'raw_file_sha256':r['request_sha256']}}
"""
        self.runner.write_text(original.replace("(p/'consumer.json').write_text", addition+"(p/'consumer.json').write_text"))
        self.request['runner'] = self.op(self.runner, '{attempt}', '{candidate}')
        self.request['conformance'] = ['facts']
        self.request['required_outcomes'] = {'check': True, 'installed': False, 'missing': True}
        self.assertEqual(self.cli('prepare')[0], 0)
        code, result = self.cli('run')
        self.assertEqual(code, 1)
        self.assertIn('Accepted obligation omitted: missing', result['conformance']['errors'])
        self.assertEqual(result['operations'][-1]['exit_code'], 0)
        self.git(self.workspace, 'reset', '--hard', self.request['base'])
        self.request['attempt'] = 'complete-obligations'
        del self.request['required_outcomes']['missing']
        self.assertEqual(self.cli('prepare')[0], 0)
        code, result = self.cli('run')
        self.assertEqual(code, 0, result)
        self.assertTrue(result['review_ready'])

    def test_accepted_obligation_coverage_and_due_stage(self):
        hashes = request_digests(b'{}')
        facts = dict(request_digests=hashes, source_stable=True, terminal_complete=True,
                     outcomes=[dict(id='check', mandatory=True, status='passed'),
                               dict(id='installed', mandatory=False, status='pending')])
        required = {'check': True, 'installed': False}
        self.assertTrue(assess(facts, hashes, required)['ready'])
        required['missing'] = True
        self.assertIn('Accepted obligation omitted: missing', assess(facts, hashes, required)['errors'])
        del required['missing']
        facts['outcomes'][0].update(mandatory=False, status='failed')
        self.assertFalse(assess(facts, hashes, required)['ready'])
        facts['outcomes'][0]['status'] = 'passed'
        required['installed'] = True
        self.assertFalse(assess(facts, hashes, required)['ready'])
        required['installed'] = False
        facts['outcomes'].append(dict(facts['outcomes'][0]))
        self.assertFalse(assess(facts, hashes, required)['ready'])

    def generation_request(self):
        package = self.root/'__init__.py'
        package.write_text('# validator-owned package input\n')
        inventory = self.root/'inventory.json'
        inventory.write_text(json.dumps({'required': [identity(path) for path in (self.input, self.runner, package)]}))
        request = dict(self.request)
        del request['inputs']
        request['input_inventory'] = dict(path=str(inventory), sha256=self.sha(inventory), keys=['required'])
        for name in ('edit', 'capture', 'runner'):
            request[name] = {'argv': self.request[name]['argv']}
        return request, package

    def test_generated_inventory_request_public_cli_and_manual_omission(self):
        request, package = self.generation_request()
        self.request = request
        code, generated = self.cli('generate')
        self.assertEqual(code, 0, generated)
        self.assertFalse((self.evidence/'attempt-1').exists())
        self.assertIn(identity(package), generated['inputs'])
        self.request = generated
        removed = self.request['inputs'].pop()
        self.assertEqual(self.cli('prepare')[0], 1)
        self.request['inputs'].append(removed)
        self.assertEqual(self.cli('prepare')[0], 0)
        self.assertEqual(self.cli('run')[0], 0)

    def test_generation_source_and_authority_barriers(self):
        request, package = self.generation_request()
        self.request = request
        self.request['capture_authority'] = ''
        self.assertEqual(self.cli('generate')[0], 1)
        self.request['capture_authority'] = 'accepted fixture grant'
        package.write_text('changed selected source')
        code, result = self.cli('generate')
        self.assertEqual(code, 1)
        self.assertIn('source mismatch', result['error'])
        self.assertEqual((self.workspace/'source.txt').read_text(), 'before\n')
        self.assertFalse((self.evidence/'attempt-1').exists())

    def test_pinned_helper_provisioning_survives_upstream_head_movement(self):
        from repository_intelligence.adoption import adopt
        source, destination = self.root/'helpers', self.root/'pinned'
        for root in (source, destination):
            root.mkdir()
            self.git(root, 'init', '-q')
            self.git(root, 'config', 'user.email', 'fixture@example.invalid')
            self.git(root, 'config', 'user.name', 'Fixture')
        (source/'helper.py').write_text('original selected helper\n')
        self.git(source, 'add', '.')
        self.git(source, 'commit', '-qm', 'selected')
        revision = self.git(source, 'rev-parse', 'HEAD').strip()
        provision = dict(source_repository=str(source), destination_repository=str(destination),
                         revision=revision, resources=[dict(source='helper.py', destination='helper.py',
                         expected_destination_sha256=None, replacements=[])])
        adopt(provision, 'apply')
        request, package = self.generation_request()
        inventory = Path(request['input_inventory']['path'])
        contents = json.loads(inventory.read_text())
        contents['required'].append(identity(destination/'helper.py'))
        inventory.write_text(json.dumps(contents))
        request['input_inventory']['sha256'] = self.sha(inventory)
        self.request = request
        code, before = self.cli('generate')
        self.assertEqual(code, 0, before)
        (source/'helper.py').write_text('new upstream helper\n')
        self.git(source, 'add', '.')
        self.git(source, 'commit', '-qm', 'unrelated advance')
        self.assertEqual(adopt(provision, 'verify')['status'], 'verified')
        self.assertEqual(self.cli('generate'), (0, before))
        (destination/'helper.py').write_text('selected byte drift')
        self.assertEqual(self.cli('generate')[0], 1)

    def test_generation_collects_independent_errors_after_source_authentication(self):
        self.request, _ = self.generation_request()
        self.request['environment'] = {'BAD=KEY': 'value'}
        self.request['capture']['argv'] = [str(self.root/'missing-capture')]
        self.request['runner']['argv'] = [str(self.root/'missing-runner')]
        code, result = self.cli('generate')
        self.assertEqual(code, 1)
        for message in ('Invalid child environment', 'capture:', 'runner:'):
            self.assertIn(message, result['error'])
        self.assertFalse((self.evidence/'attempt-1').exists())

    def test_static_errors_are_collected_without_launch(self):
        self.request['environment'] = {'BAD=KEY': 'value'}
        self.request['capture']['argv'].append('\x00')
        self.request['runner']['executable_sha256'] = '0'*64
        code, result = self.cli('prepare')
        self.assertEqual(code, 1)
        for message in ('Invalid child environment', 'capture:', 'runner:'):
            self.assertIn(message, result['error'])
        self.assertFalse((self.evidence/'attempt-1').exists())
        self.input.write_text('mismatched authority source')
        code, result = self.cli('prepare')
        self.assertNotIn('Static preflight', result['error'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX executable permission required')
    def test_nonexecutable_selected_operations_refuse_before_edits(self):
        for name in ('capture', 'runner'):
            with self.subTest(operation=name):
                script = getattr(self, name)
                script.chmod(0o644)
                code, result = self.cli('prepare')
                self.assertEqual(code, 1)
                self.assertIn(str(script), result['error'])
                self.assertIn('not executable', result['error'])
                request, _ = self.generation_request()
                original = self.request
                self.request = request
                self.assertEqual(self.cli('generate')[0], 1)
                self.request = original
                self.assertFalse((self.evidence/'attempt-1').exists())
                self.assertEqual((self.workspace/'source.txt').read_text(), 'before\n')
                script.chmod(0o755)
        self.assertEqual(self.cli('prepare')[0], 0)
        self.assertEqual(self.cli('run')[0], 0)

    @unittest.skipUnless(os.name == 'posix', 'POSIX executable permission required')
    def test_permission_change_after_prepare_refuses_before_edit(self):
        self.assertEqual(self.cli('prepare')[0], 0)
        self.capture.chmod(0o644)
        code, result = self.cli('run')
        self.assertEqual(code, 1)
        self.assertIn('not executable', result['error'])
        self.assertEqual((self.workspace/'source.txt').read_text(), 'before\n')
        self.assertFalse((self.evidence/'attempt-1'/'LAUNCHED').exists())

    def test_atomic_save_failure_preserves_previous_return_and_cleans_temp(self):
        target=self.evidence/'RETURN.json';save(target,{'status':'incomplete'})
        before=target.read_bytes()
        with patch('repository_intelligence.worker_execution.os.replace',side_effect=OSError('injected')):
            with self.assertRaises(OSError):save(target,{'status':'complete'})
        self.assertEqual(target.read_bytes(),before)
        self.assertEqual(list(self.evidence.glob('RETURN.json.tmp-*')),[])

    def test_git_identity_change_and_out_of_scope_capture_refused(self):
        self.request['edit']=self.op(self.script('wrong-git','git remote add unexpected /not-a-project\n'))
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,1)
        self.assertIn('Workspace identity',result['error'])
        self.assertEqual([row['operation'] for row in result['operations']],['edit'])
        self.git(self.workspace,'remote','remove','unexpected')
        self.request['attempt']='out-of-scope'
        self.request['edit']=self.op(self.script('extra','echo extra > unauthorized.txt\n'))
        self.request['capture']=self.op(self.script('capture-extra','git add .\ngit commit -qm extra\n'))
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,1)
        self.assertIn('unauthorized changed paths',result['error'])
        self.assertFalse(any(row['operation']=='runner' for row in result['operations']))

    def test_selected_instruction_drift_and_out_of_scope_capture_refused(self):
        self.assertEqual(self.cli('prepare')[0],0)
        self.input.write_text('changed grant')
        self.assertEqual(self.cli('run')[0],1)
        self.assertEqual((self.workspace/'source.txt').read_text(),'before\n')


if __name__=='__main__':
    unittest.main()
