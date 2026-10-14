import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from repository_intelligence.worker_execution import execute, identity, read, ExecutionError


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
        self.assertEqual(result['runner_result']['sha256'],self.sha(self.evidence/'attempt-1'/'consumer.json'))
        self.assertEqual(result['references'][0]['sha256'],self.sha(self.evidence/'attempt-1'/'consumer.log'))

    def test_timeout_records_partial_invocation_output(self):
        self.request['timeout_seconds']=1
        self.request['capture']=self.op(self.script('timeout','echo partial\nexec sleep 2\n'))
        self.assertEqual(self.cli('prepare')[0],0)
        code,result=self.cli('run');self.assertEqual(code,1)
        row=result['operations'][-1]
        self.assertEqual(row['status'],'incomplete')
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
