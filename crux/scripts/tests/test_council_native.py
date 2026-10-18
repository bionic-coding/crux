"""Deterministic native host controls. These are never live model evidence."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import CycleError,digest


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.docs=self.root/'bionic';self.docs.mkdir()
        (self.root/'.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.docs/'objectives.md').write_text('Use proportional review with durable history.')
        (self.docs/'adrs').mkdir();(self.docs/'adrs/subject.txt').write_text('Read-only proposal, exact content.')
        self.git('init','-q');self.git('config','user.email','test@example.invalid');self.git('config','user.name','Test')
        from council_policy import initialize
        initialize(self.root,'lite',selection='Explicit test setup selects Lite')
        self.git('add','.');self.git('commit','-qm','Initialize Lite fixture')
    def git(self,*args):
        result=subprocess.run(['git','-C',str(self.root),*args],capture_output=True,check=True)
        return result.stdout.decode().strip()
    def prepare(self,**kwargs):
        from council_native import prepare
        return prepare(self.root,'consultation','adrs/subject.txt','Check all five dimensions.',
            harness='codex',author_context='/root/author',identity='fixture-consultation',**kwargs)
    def host(self,request,context='/root/challenger',decision='REQUEST_CHANGES'):
        vote={'decision':decision,'reasoning':'Check completed.','findings':[]}
        return {'tool':'collaboration.spawn_agent','input':request['dispatch'],
            'result':{'task_name':context},'final':f'Message Type: FINAL_ANSWER\nTask name: /root\nSender: {context}\nPayload:\n'+json.dumps(vote)}
    def test_two_pass_no_key_and_exact_final_architect(self):
        from council_native import ingest
        from council_policy import disposition
        with patch('crux_env.get',side_effect=AssertionError('Native must not read gateway credentials')):
            first=self.prepare();closed=ingest(self.root,first['request'],self.host(first))
            self.assertEqual(closed['outcome'],'challenge-complete')
            with self.assertRaisesRegex(CycleError,'open|unresolved|attempt'):
                self.prepare()
            final=self.prepare(phase='final',attempt_path=first['attempt'],response='Architect checked each finding; unchanged final content is justified.')
            reviewed=ingest(self.root,final['request'],self.host(final,'/root/final','APPROVE'))
            self.assertNotEqual(reviewed['outcome'],'approved')
            result=disposition(self.root,reviewed['record'],{'agrees':True,'subject_sha256':digest((self.docs/'adrs/subject.txt').read_bytes()),
                'rationale':'Proceed on exact final revision.','dissent':[]})
            self.assertEqual(result['outcome'],'approved')
    def test_missing_wrong_host_metadata_fails_attempt_and_no_replacement(self):
        from council_native import ingest
        first=self.prepare();host=self.host(first);host['input']=dict(host['input'],model='wrong-model')
        failed=ingest(self.root,first['request'],host);self.assertEqual(failed['outcome'],'could-not-run')
        with self.assertRaisesRegex(CycleError,'closed|failed|already'):
            ingest(self.root,first['request'],self.host(first))
    def test_same_author_or_final_context_cannot_approve(self):
        from council_native import ingest
        first=self.prepare();result=ingest(self.root,first['request'],self.host(first,'/root/author'))
        self.assertEqual(result['outcome'],'could-not-run')
    def test_protected_mutation_and_new_evidence_refuse(self):
        from council_native import ingest
        first=self.prepare();(self.root/'.bionic.yml').write_text((self.root/'.bionic.yml').read_text()+'# changed\n')
        failed=ingest(self.root,first['request'],self.host(first));self.assertEqual(failed['outcome'],'could-not-run')
    def test_unrelated_cycle_write_does_not_change_guard(self):
        from council_native import ingest
        first=self.prepare();path=self.docs/'cycles/CYC-9999/cycle.json';path.parent.mkdir(parents=True);path.write_text('{}')
        self.assertEqual(ingest(self.root,first['request'],self.host(first))['outcome'],'challenge-complete')
    def test_pending_request_cannot_redispatch_or_skip_to_final(self):
        first=self.prepare()
        with self.assertRaisesRegex(CycleError,'open|unresolved|prepared'):
            self.prepare()
        with self.assertRaisesRegex(CycleError,'challenge|open|prepared'):
            self.prepare(phase='final',attempt_path=first['attempt'],response='Response')
    def test_final_same_context_and_execution_error_fail(self):
        from council_native import ingest
        first=self.prepare();ingest(self.root,first['request'],self.host(first))
        final=self.prepare(phase='final',attempt_path=first['attempt'],response='Architect response')
        failed=ingest(self.root,final['request'],self.host(final,'/root/challenger','APPROVE'))
        self.assertEqual(failed['outcome'],'could-not-run')
    def test_request_hash_and_context_evidence_are_not_model_claims(self):
        from council_native import ingest
        first=self.prepare();host=self.host(first);host['input']=dict(host['input'],message=host['input']['message']+'changed')
        failed=ingest(self.root,first['request'],host);self.assertEqual(failed['outcome'],'could-not-run')

    def test_between_pass_config_drift_refuses_before_prepared_final(self):
        from council_native import ingest
        first=self.prepare();ingest(self.root,first['request'],self.host(first))
        config=self.root/'.bionic.yml';original=config.read_bytes();config.write_bytes(original+b'# drift\n')
        with self.assertRaisesRegex(CycleError,'frozen input'):
            self.prepare(phase='final',attempt_path=first['attempt'],response='Response')
        attempt=json.loads((self.docs/first['attempt']).read_bytes());self.assertEqual(len(attempt['passes']),1)
        config.write_bytes(original)
        self.assertEqual(self.prepare(phase='final',attempt_path=first['attempt'],response='Response')['outcome'],'prepared')
    def test_evidence_addition_and_missing_host_metadata_fail(self):
        from council_native import ingest
        first=self.prepare();folder=(self.docs/first['request']).parent;(folder/'unowned.lock').write_text('injected')
        self.assertEqual(ingest(self.root,first['request'],self.host(first))['outcome'],'could-not-run')
    def test_changed_subject_and_reported_actual_model_mismatch_fail(self):
        from council_native import ingest
        first=self.prepare();(self.docs/'adrs/subject.txt').write_text('Modified while reviewer was running')
        self.assertEqual(ingest(self.root,first['request'],self.host(first))['outcome'],'could-not-run')
    def test_recovery_retains_original_result_without_redispatch(self):
        from council_native import ingest,recover
        first=self.prepare()
        with patch('council_native.commit_evidence',side_effect=OSError('interrupted evidence commit')):
            with self.assertRaises(OSError):ingest(self.root,first['request'],self.host(first))
        self.assertEqual(recover(self.root,first['attempt'])['outcome'],'challenge-complete')
        with self.assertRaisesRegex(CycleError,'already closed'):
            ingest(self.root,first['request'],self.host(first))
    def test_failed_final_cannot_replace_reviewer(self):
        from council_native import ingest
        first=self.prepare();ingest(self.root,first['request'],self.host(first))
        final=self.prepare(phase='final',attempt_path=first['attempt'],response='Response')
        reviewed=ingest(self.root,final['request'],self.host(final,'/root/final','REQUEST_CHANGES'))
        self.assertEqual(reviewed['outcome'],'changes-required')
        with self.assertRaisesRegex(CycleError,'closed|failed'):
            self.prepare(phase='final',attempt_path=first['attempt'],response='Try again')
    def test_unverified_harness_is_predispatch_refusal(self):
        from council_native import prepare
        with self.assertRaisesRegex(CycleError,'unverified'):
            prepare(self.root,'consultation','adrs/subject.txt','Review',harness='opencode',author_context='/root/author',identity='unsupported')
        self.assertFalse(list(self.docs.rglob('attempt-*.json')))
    def test_missing_actual_context_is_not_a_model_authored_claim(self):
        from council_native import ingest
        first=self.prepare();host=self.host(first);host['result']={}
        host['final']=host['final'].replace('Check completed.','I am the selected Apex model in a fresh context.')
        self.assertEqual(ingest(self.root,first['request'],host)['outcome'],'could-not-run')
    def test_actual_model_mismatch_is_not_ignored(self):
        from council_native import ingest
        first=self.prepare();host=self.host(first);host['result']['model']='different-served-model'
        self.assertEqual(ingest(self.root,first['request'],host)['outcome'],'could-not-run')

    def test_claude_cli_contract_from_observed_probe_and_model_refusal(self):
        # Deterministic reduced fixture derived from the real 2026-10-17 CLI
        # capability probe. This test is not a live native council execution.
        from council_native import prepare,ingest
        first=prepare(self.root,'consultation','adrs/subject.txt','Review all five dimensions.',
            harness='claude',author_context='/root/author',identity='claude-fixture')
        dispatch=first['dispatch'];model=dispatch['argv'][dispatch['argv'].index('--model')+1]
        self.assertIn('--safe-mode',dispatch['argv']);self.assertNotIn('--resume',dispatch['argv'])
        stdout={'type':'result','subtype':'success','is_error':False,'session_id':dispatch['session_id'],
                'modelUsage':{model:{'canonicalModel':model}},'result':json.dumps({'decision':'REQUEST_CHANGES','reasoning':'Checked','findings':[]})}
        host={'tool':'claude-cli','input':dispatch,'result':{'returncode':0,'stdout':json.dumps(stdout),'stderr':''}}
        self.assertEqual(ingest(self.root,first['request'],host)['outcome'],'challenge-complete')
        final=prepare(self.root,'consultation','adrs/subject.txt','Review all five dimensions.',phase='final',
            attempt_path=first['attempt'],harness='claude',author_context='/root/author',identity='claude-fixture',response='Architect response')
        bad=dict(stdout,session_id=final['dispatch']['session_id'],modelUsage={'wrong-model':{}})
        host={'tool':'claude-cli','input':final['dispatch'],'result':{'returncode':0,'stdout':json.dumps(bad),'stderr':''}}
        self.assertEqual(ingest(self.root,final['request'],host)['outcome'],'could-not-run')

    def test_secret_input_refuses_before_attempt_and_output_cannot_be_written(self):
        from council_native import ingest
        synthetic='sk-ant-api03-'+('x'*96)
        subject=self.docs/'adrs/subject.txt';original=subject.read_bytes();subject.write_text(synthetic)
        with self.assertRaisesRegex(CycleError,'secret scan'):self.prepare()
        self.assertFalse(list(self.docs.rglob('attempt-*.json')))
        subject.write_bytes(original);first=self.prepare();host=self.host(first)
        host['final']=host['final'].replace('Check completed.',synthetic)
        self.assertEqual(ingest(self.root,first['request'],host)['outcome'],'could-not-run')
        for path in self.docs.rglob('*.result.json'):
            self.assertNotIn(synthetic,path.read_text())
    def test_catalog_and_policy_inputs_are_guarded_outside_evidence_directory(self):
        import council_native as native
        selected=native._apex('codex');local=self.root/'models.yml';local.write_bytes(Path(selected['catalog']).read_bytes())
        selected=dict(selected,catalog=str(local))
        with patch('council_native._apex',return_value=selected):first=self.prepare()
        local.write_text(local.read_text()+'# changed\n')
        self.assertEqual(native.ingest(self.root,first['request'],self.host(first))['outcome'],'could-not-run')
    def test_deleted_trace_and_missing_apex_cannot_fall_back(self):
        from council_native import ingest
        with patch('models_catalog.load',side_effect=ValueError('missing Apex')),patch('crux_env.get',side_effect=AssertionError('no gateway fallback')):
            with self.assertRaisesRegex(CycleError,'Apex'):self.prepare()
        self.assertFalse(list(self.docs.rglob('attempt-*.json')))
        first=self.prepare();request=json.loads((self.docs/first['request']).read_bytes());(self.root/request['trace']['path']).unlink()
        self.assertEqual(ingest(self.root,first['request'],self.host(first))['outcome'],'could-not-run')

    def test_frozen_policy_record_mutation_fails_pass(self):
        from council_native import ingest
        first=self.prepare();policy_file=self.docs/'adrs/councils/initialization.json'
        policy_file.write_bytes(policy_file.read_bytes()+b'\n')
        self.assertEqual(ingest(self.root,first['request'],self.host(first))['outcome'],'could-not-run')
    def test_malformed_reviewer_json_is_failed_attempt_not_replaceable(self):
        from council_native import ingest
        first=self.prepare();host=self.host(first);host['final']=host['final'][:-1]
        self.assertEqual(ingest(self.root,first['request'],host)['outcome'],'could-not-run')
        with self.assertRaisesRegex(CycleError,'closed|failed'):
            ingest(self.root,first['request'],self.host(first))

    def test_approved_lite_requires_retained_exact_proof_at_every_read(self):
        from council_native import ingest
        from council_policy import disposition
        from cycle_council import validate_approval
        first=self.prepare();ingest(self.root,first['request'],self.host(first))
        final=self.prepare(phase='final',attempt_path=first['attempt'],response='Architect response')
        reviewed=ingest(self.root,final['request'],self.host(final,'/root/final','APPROVE'))
        disposition(self.root,reviewed['record'],{'agrees':True,'subject_sha256':digest((self.docs/'adrs/subject.txt').read_bytes()),'rationale':'Proceed','dissent':[]})
        validate_approval(self.root,reviewed['record'],purpose='consultation',subject='adrs/subject.txt')
        request=json.loads((self.docs/final['request']).read_bytes());trace=self.root/request['trace']['path'];trace.unlink()
        with self.assertRaises(CycleError):
            validate_approval(self.root,reviewed['record'],purpose='consultation',subject='adrs/subject.txt')
    def test_standalone_lite_receipt_and_projection_replay_retained_proof(self):
        import decision_policy as dp
        import summaries_projection
        from council_native import prepare,ingest
        from council_policy import disposition
        from cycle_workflow import tree
        (self.docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        subject=dp.propose(self.root,{'title':'Native evidence','body':'# Decision\nPreserve exact proof.\n',
            'governs':[{'domain':'evidence','scope':'tree','rule':'Keep proof.','handle':'keep-proof'}]},origin='direct')['path']
        args={'harness':'codex','author_context':'/root/author'}
        first=prepare(self.root,'adr',subject,'Review',**args);ingest(self.root,first['request'],self.host(first))
        final=prepare(self.root,'adr',subject,'Review',phase='final',attempt_path=first['attempt'],response='Architect response',**args)
        reviewed=ingest(self.root,final['request'],self.host(final,'/root/final','APPROVE'))
        disposition(self.root,reviewed['record'],{'agrees':True,'subject_sha256':digest((self.docs/subject).read_bytes()),'rationale':'Proceed','dissent':[]})
        dp.accept(self.root,subject,reviewed['record'],human_approval='Owner accepts this exact proposal')
        dp.validate_acceptance(tree(self.root),{'path':subject});self.assertTrue(summaries_projection.collect_records(self.docs/'adrs'))
        record=json.loads((self.docs/reviewed['record']).read_bytes());result=self.root/record['passes'][1]['result']['path'];result.write_bytes(result.read_bytes()+b'\n')
        with self.assertRaises(CycleError):dp.validate_acceptance(tree(self.root),{'path':subject})
        with self.assertRaises(ValueError):summaries_projection.collect_records(self.docs/'adrs')
