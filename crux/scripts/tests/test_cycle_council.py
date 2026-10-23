"""The cycle council uses configured gate seats and exact retained subjects."""
import fcntl
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import create,tree,retained,CycleError,atomic
from cycle_council import convene,validate_approval,recover
_cli_spec=importlib.util.spec_from_file_location('cycle_council_cli',Path(__file__).resolve().parents[1]/'cycle-council.py')
cli=importlib.util.module_from_spec(_cli_spec);_cli_spec.loader.exec_module(cli)
try:
    from crux.core.data_classes import CouncilVote,CouncilDeliberation
    from crux.council.async_council import AsyncCouncilConfig
    HAVE_GATEWAY=True
except ImportError:
    HAVE_GATEWAY=False


FIRST_BUDGET=64000
def truncating_gateway():
    """A fake gateway: the first request answers finish "length", every other request approves.

    Returns (transport, models, seen) where seen maps each model's api string to the max_tokens it was sent.
    """
    import httpx
    from crux.council.async_council import validate_gate_assignment
    from crux.core.llm_caller import get_model_config
    models={cfg.api_string:cfg for cfg in (get_model_config(m) for m in validate_gate_assignment().values())}
    seen={};calls=[]
    def reply(request):
        payload=json.loads(request.content);cfg=models[payload['model']]
        seen.setdefault(payload['model'],[]).append(payload['max_tokens']);calls.append(payload['model'])
        served={'model':cfg.api_string,'provider':next(iter(cfg.accepted_served_providers))}
        if len(calls)==1:
            return httpx.Response(200,json=dict(served,choices=[{'finish_reason':'length','message':{'content':'{'}}]))
        vote={'decision':'APPROVE','confidence':.9,'reasoning':'supported','findings':[]}
        return httpx.Response(200,json=dict(served,choices=[{'finish_reason':'stop','message':{'content':json.dumps(vote)}}]))
    return httpx.MockTransport(reply),models,seen,calls

def assert_record_budgets(case,record,models,seen,calls):
    """The written record's seat attempts hold the budget each request used, escalated after a truncation."""
    seats=record['seats'];case.assertEqual(len(seats),3)
    truncated_model=calls[0];limit=models[truncated_model].max_output_tokens
    case.assertGreater(limit,FIRST_BUDGET)
    case.assertEqual(seen[truncated_model],[FIRST_BUDGET,limit])
    escalated=[s for s in seats if len(s['attempts'])==2];case.assertEqual(len(escalated),1)
    a=escalated[0]['attempts']
    case.assertEqual((a[0]['max_tokens'],a[0]['finish_reason'],a[0]['fault_label']),(FIRST_BUDGET,'length','truncated'))
    case.assertEqual(a[1]['max_tokens'],limit)
    for seat in seats:
        if seat is not escalated[0]:case.assertEqual([x['max_tokens'] for x in seat['attempts']],[FIRST_BUDGET])


@unittest.skipUnless(HAVE_GATEWAY,'gateway dependencies unavailable')
class CouncilTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        (self.root/'bionic').mkdir();(self.root/'src').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root/'bionic/objectives.md').write_text('Proportional ceremony and durable decisions.')
        self.doc=create(self.root,'iterate','Fix','Outcome',['src'],['correct'],'builder','tester')
        self.cfg=tree(self.root);self.subject=retained(self.cfg,self.doc['id'],'decisions',{'approach':'bounded fix'})['path']
    def run_council(self,votes=None,**kwargs):
        votes=votes or [CouncilVote(model=p+'/model',provider=p,decision='APPROVE',reasoning='supported',confidence=.9) for p in ('openai','anthropic','google')]
        result=CouncilDeliberation(votes=votes,consensus='UNANIMOUS_APPROVE',consensus_confidence=.9,key_agreements=[],key_disagreements=[],final_recommendation={})
        limits={'one':128000,'two':128000,'three':65536}
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.validate_gate_assignment',return_value={'openai_top':'one','anthropic_top':'two','google_top':'three'}),patch('crux.core.llm_caller.get_model_config',side_effect=lambda model:SimpleNamespace(max_output_tokens=limits[model])),patch('crux.council.async_council.AsyncCouncil') as council:
            council.return_value.deliberate=AsyncMock(return_value=result)
            output=convene(self.root,'idr',self.subject,'Review the material implementation choice.',cycle_id=self.doc['id'],**kwargs)
            config=council.call_args.args[0]
            self.assertIsInstance(config,AsyncCouncilConfig);self.assertTrue(config.gate)
            self.assertEqual(config.council_kind,'implementation');self.assertEqual(config.openai_model,'one')
            self.assertEqual(config.max_tokens,kwargs.get('max_tokens'))
            attempt=json.loads((self.cfg.docs_root/output['attempt']).read_text())
            self.assertEqual(attempt['max_tokens'],config.max_tokens)
            prompt=council.return_value.deliberate.call_args.args[0]
            self.assertIn('untrusted review data',prompt)
            self.assertIn('Proportional ceremony',prompt)
            return output
    def test_configured_gate_approval_exact_bytes(self):
        output=self.run_council();self.assertEqual(output['outcome'],'approved')
        validate_approval(self.root,output['record'],purpose='idr',subject=self.subject)
        (self.cfg.docs_root/self.subject).write_text('{}')
        with self.assertRaises(CycleError):validate_approval(self.root,output['record'],purpose='idr',subject=self.subject)
    def test_blocking_finding_prevents_approval(self):
        votes=[CouncilVote(model=p+'/model',provider=p,decision='APPROVE',reasoning='supported',confidence=.9,findings=[{'kind':'blocking'}] if p=='openai' else []) for p in ('openai','anthropic','google')]
        self.assertEqual(self.run_council(votes)['outcome'],'changes-required')
    def test_secret_subject_never_sent(self):
        (self.cfg.docs_root/self.subject).write_text('test-gateway-credential')
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.AsyncCouncil') as council:
            output=convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'])
            self.assertEqual(output['outcome'],'could-not-run');council.assert_not_called()
    def test_recovery_refuses_live_attempt(self):
        path=self.cfg.docs_root/'cycles'/self.doc['id']/'councils/attempt-test.json';path.parent.mkdir()
        atomic(path,{'format':'crux.cycle-council-attempt','status':'running'})
        with path.with_suffix('.lock').open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(CycleError,'still running'):recover(self.root,path.relative_to(self.cfg.docs_root).as_posix())
        self.assertEqual(recover(self.root,path.relative_to(self.cfg.docs_root).as_posix())['status'],'interrupted')
    def test_another_round_requires_progress(self):
        self.run_council()
        with self.assertRaisesRegex(CycleError,'meaningful progress'):
            convene(self.root,'idr',self.subject,'review again',cycle_id=self.doc['id'])

    def test_explicit_64k_output_budget_reaches_config_and_attempt(self):
        self.assertEqual(self.run_council(max_tokens=64000)['outcome'],'approved')

    def test_explicit_64k_reaches_each_gateway_payload_without_network(self):
        import httpx
        from crux.council.async_council import validate_gate_assignment
        from crux.core.llm_caller import get_model_config
        models={cfg.api_string:cfg for cfg in
                (get_model_config(model) for model in validate_gate_assignment().values())}
        requests=[]
        def reply(request):
            payload=json.loads(request.content);requests.append(payload)
            cfg=models[payload['model']]
            vote={'decision':'APPROVE','confidence':.9,'reasoning':'supported','findings':[]}
            return httpx.Response(200,json={'model':cfg.api_string,'provider':next(iter(cfg.accepted_served_providers)),
                                           'choices':[{'finish_reason':'stop','message':{'content':json.dumps(vote)}}]})
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.get',return_value='test-gateway-credential'):
            output=convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'],
                           max_tokens=64000,transport=httpx.MockTransport(reply))
        self.assertEqual(output['outcome'],'approved');self.assertEqual(len(requests),3)
        self.assertEqual({row['model'] for row in requests},set(models))
        self.assertTrue(all(row['max_tokens']==64000 for row in requests))

    def test_smallest_seat_output_limit_is_allowed(self):
        self.assertEqual(self.run_council(max_tokens=65536)['outcome'],'approved')

    def test_budget_above_smallest_seat_limit_refuses_before_attempt_or_request(self):
        with patch('crux.council.async_council.validate_gate_assignment',return_value={'openai_top':'one','anthropic_top':'two','google_top':'three'}),patch('crux.core.llm_caller.get_model_config',side_effect=lambda model:SimpleNamespace(max_output_tokens={'one':128000,'two':128000,'three':65536}[model])),patch('crux.council.async_council.AsyncCouncil') as council:
            with self.assertRaisesRegex(CycleError,'max_tokens.*65536'):
                convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'],max_tokens=65537)
            council.assert_not_called()
        self.assertFalse(list(self.cfg.docs_root.rglob('attempt-*')))

    def test_invalid_api_output_budgets_refuse_before_attempt_or_request(self):
        for value in (0,-1,True,False,1.5,'64000'):
            with self.subTest(value=value),patch('crux.council.async_council.AsyncCouncil') as council:
                with self.assertRaisesRegex(CycleError,'max_tokens.*positive integer'):
                    convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'],max_tokens=value)
                council.assert_not_called()
        self.assertFalse(list(self.cfg.docs_root.rglob('attempt-*')))

    def test_missing_key_preserves_no_key_outcome_even_with_invalid_assignment(self):
        with patch('crux_env.get',return_value=None),patch('crux.council.async_council.validate_gate_assignment',side_effect=ValueError('invalid registry')),patch('crux.council.async_council.AsyncCouncil') as council:
            output=convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'],max_tokens=64000)
            council.assert_not_called()
        record=json.loads((self.cfg.docs_root/output['record']).read_text())
        self.assertEqual(output['outcome'],'could-not-run');self.assertEqual(record['reason'],'no-key')
        attempt=json.loads((self.cfg.docs_root/output['attempt']).read_text())
        self.assertEqual(attempt['status'],'finished');self.assertEqual(attempt['max_tokens'],64000)

    def test_invalid_assignment_preserves_setup_failure_record(self):
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.validate_gate_assignment',side_effect=ValueError('invalid registry')),patch('crux.council.async_council.AsyncCouncil') as council:
            output=convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'])
            council.assert_not_called()
        record=json.loads((self.cfg.docs_root/output['record']).read_text())
        self.assertEqual(output['outcome'],'could-not-run');self.assertEqual(record['reason'],'ValueError')

    def test_invalid_selected_output_limit_preserves_setup_failure_record(self):
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.validate_gate_assignment',return_value={'openai_top':'one','anthropic_top':'two','google_top':'three'}),patch('crux.core.llm_caller.get_model_config',side_effect=lambda model:SimpleNamespace(max_output_tokens={'one':128000,'two':True,'three':65536}[model])),patch('crux.council.async_council.AsyncCouncil') as council:
            output=convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'])
            council.assert_not_called()
        record=json.loads((self.cfg.docs_root/output['record']).read_text())
        self.assertEqual(output['outcome'],'could-not-run');self.assertEqual(record['reason'],'ValueError')


@unittest.skipUnless(HAVE_GATEWAY,'gateway dependencies unavailable')
class CouncilRecordBudgetTests(unittest.TestCase):
    setUp=CouncilTests.setUp
    def test_legacy_record_carries_per_attempt_budget_with_escalated_retry(self):
        transport,models,seen,calls=truncating_gateway()
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.get',return_value='test-gateway-credential'):
            output=convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'],max_tokens=FIRST_BUDGET,transport=transport)
        record=json.loads((self.cfg.docs_root/output['record']).read_text())
        assert_record_budgets(self,record,models,seen,calls)


class CouncilPerSeatBudgetTests(CouncilTests):
    def test_omitted_budget_is_per_seat_and_recorded_as_null(self):
        output=self.run_council()
        attempt=json.loads((self.cfg.docs_root/output['attempt']).read_text())
        self.assertIsNone(attempt['max_tokens'])

    def test_explicit_budget_is_recorded_as_the_integer(self):
        output=self.run_council(max_tokens=40000)
        attempt=json.loads((self.cfg.docs_root/output['attempt']).read_text())
        self.assertEqual(attempt['max_tokens'],40000)

    def test_explicit_budget_above_smallest_limit_is_still_refused(self):
        with patch('crux.council.async_council.validate_gate_assignment',return_value={'openai_top':'one','anthropic_top':'two','google_top':'three'}),patch('crux.core.llm_caller.get_model_config',side_effect=lambda model:SimpleNamespace(max_output_tokens={'one':128000,'two':128000,'three':65536}[model])),patch('crux.council.async_council.AsyncCouncil') as council:
            with self.assertRaisesRegex(CycleError,'max_tokens.*65536'):
                convene(self.root,'idr',self.subject,'review',cycle_id=self.doc['id'],max_tokens=65537)
            council.assert_not_called()


class CouncilCliBudgetTests(unittest.TestCase):
    def test_default_and_explicit_output_budget_forwarded(self):
        with tempfile.TemporaryDirectory() as directory:
            question=Path(directory)/'question.txt';question.write_text('review')
            for flags,expected in (([],None),(['--max-tokens','64000'],64000)):
                with self.subTest(flags=flags),patch.object(cli,'convene',return_value={'outcome':'approved'}) as call,contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main(['--purpose','adr','--subject','adrs/proposal.md','--question',str(question),*flags]),0)
                    self.assertEqual(call.call_args.kwargs['max_tokens'],expected)

    def test_invalid_cli_output_budgets_refuse_before_convene(self):
        for value in ('0','-1','1.5','true'):
            with self.subTest(value=value),patch.object(cli,'convene') as call,contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    cli.main(['--max-tokens',value])
                self.assertEqual(error.exception.code,2);call.assert_not_called()

if __name__=='__main__':unittest.main()

# Share the small immutable migration fixture instead of regenerating historical
# pilot proofs for each prospective council control.
from test_adr_migration import MigrationFixture


@unittest.skipUnless(HAVE_GATEWAY,'gateway dependencies unavailable')
class DispositionCouncilTests(MigrationFixture):
    def test_distinct_standalone_purpose_sends_complete_exact_bundle(self):
        import httpx
        from crux.council.async_council import validate_gate_assignment
        from crux.core.llm_caller import get_model_config
        from cycle_workflow import digest
        from cycle_council import validate_approval
        models={cfg.api_string:cfg for cfg in (get_model_config(model) for model in validate_gate_assignment().values())}
        requests=[]
        def reply(request):
            payload=json.loads(request.content);requests.append(payload)
            cfg=models[payload['model']]
            vote={'decision':'APPROVE','confidence':.9,'reasoning':'Exact reviewed package.','findings':[]}
            return httpx.Response(200,json={'model':cfg.api_string,'provider':next(iter(cfg.accepted_served_providers)),
                'choices':[{'finish_reason':'stop','message':{'content':json.dumps(vote)}}]})
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.get',return_value='test-gateway-credential'):
            output=convene(self.root,'disposition',self.package_path.removeprefix('bionic/'),'Review every disposition.',readiness=self.readiness,transport=httpx.MockTransport(reply))
        self.assertEqual(output['outcome'],'approved');self.assertEqual(len(requests),3)
        record=json.loads((self.docs/output['record']).read_text())
        self.assertEqual(record['readiness'],self.readiness);self.assertEqual(record['purpose'],'disposition')
        for request in requests:
            content=request['messages'][-1]['content']
            self.assertIn('Keep existing approvals.',content)
            self.assertIn('continuing',content);self.assertIn('ceasing',content)
            self.assertIn(self.bind(self.package['governing_adr']['receipt'])['sha256'],content)
        with self.assertRaises(CycleError):validate_approval(self.root,output['record'],purpose='disposition',subject=self.package_path.removeprefix('bionic/'))
        self.commit('Commit disposition council')
        validate_approval(self.root,output['record'],purpose='disposition',subject=self.package_path.removeprefix('bionic/'))

    def test_disposition_requires_committed_verified_readiness_before_attempt(self):
        for readiness in (None,dict(self.readiness,commit='0'*40),dict(self.readiness,tests=[])):
            with self.subTest(readiness=readiness),patch('crux.council.async_council.AsyncCouncil') as council:
                with self.assertRaises(CycleError):convene(self.root,'disposition',self.package_path.removeprefix('bionic/'),'Review',readiness=readiness)
                council.assert_not_called()
        self.assertFalse(list((self.docs/'adrs/councils').glob('attempt-*.json')))

    def test_disposition_cli_forwards_readiness(self):
        path=self.root/'readiness.json';path.write_text(json.dumps(self.readiness))
        question=self.root/'question.txt';question.write_text('Review')
        with patch.object(cli,'convene',return_value={'outcome':'approved'}) as call,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--purpose','disposition','--subject',self.package_path.removeprefix('bionic/'),'--question',str(question),'--readiness',str(path)]),0)
            self.assertEqual(call.call_args.kwargs['readiness'],self.readiness)


@unittest.skipUnless(HAVE_GATEWAY,'gateway dependencies unavailable')
class ModeAwareCouncilTests(unittest.TestCase):
    def setUp(self):
        import subprocess
        from council_policy import initialize
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.docs=self.root/'bionic';self.docs.mkdir()
        (self.root/'.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.docs/'objectives.md').write_text('Proportional review and durable history.')
        (self.docs/'adrs').mkdir();(self.docs/'adrs/subject.txt').write_text('A bounded proposal.')
        for args in (('init','-q'),('config','user.email','test@example.invalid'),('config','user.name','Test')):
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        initialize(self.root,'standard',selection='New setup explicitly selects Standard')
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.root),'commit','-qm','Fixture'],check=True,capture_output=True)
    def call(self,votes=None,**options):
        votes=votes or [CouncilVote(model=p+'/model',provider=p,decision='APPROVE',reasoning='supported',confidence=.9) for p in ('openai','anthropic','google')]
        result=CouncilDeliberation(votes=votes,consensus='UNANIMOUS_APPROVE',consensus_confidence=.9,key_agreements=[],key_disagreements=[],final_recommendation={})
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.validate_gate_assignment',return_value={'openai_top':'one','anthropic_top':'two','google_top':'three'}),patch('crux.core.llm_caller.get_model_config',return_value=SimpleNamespace(max_output_tokens=65536)),patch('crux.council.async_council.AsyncCouncil') as council:
            council.return_value.deliberate=AsyncMock(return_value=result)
            output=convene(self.root,options.pop('purpose','consultation'),options.pop('subject','adrs/subject.txt'),'Review all five dimensions.',identity='stable-consultation',**options)
            return output,council.return_value.deliberate.call_args.args[0]
    def test_policy_record_carries_per_attempt_budget_with_escalated_retry(self):
        transport,models,seen,calls=truncating_gateway()
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.get',return_value='test-gateway-credential'):
            output=convene(self.root,'consultation','adrs/subject.txt','Review',identity='budget-record',max_tokens=FIRST_BUDGET,transport=transport)
        record=json.loads((self.docs/output['record']).read_text())
        assert_record_budgets(self,record,models,seen,calls)
    def test_standard_writer_and_common_accepting_validator(self):
        from council_policy import disposition
        from cycle_workflow import digest
        output,_=self.call();self.assertEqual(output['outcome'],'changes-required')
        result=disposition(self.root,output['record'],{'agrees':True,'subject_sha256':digest((self.docs/'adrs/subject.txt').read_bytes()),'rationale':'All constraints checked.','dissent':[]})
        self.assertEqual(result['outcome'],'approved')
        validate_approval(self.root,output['record'],purpose='consultation',subject='adrs/subject.txt')
    def test_missing_key_and_invalid_seat_refuse_without_attempt_or_native(self):
        with patch('crux_env.get',return_value=None),patch('crux.council.async_council.AsyncCouncil') as council:
            output=convene(self.root,'consultation','adrs/subject.txt','Review',identity='no-key')
            self.assertEqual(output['reason'],'no-key');council.assert_not_called()
        with patch('crux_env.get',return_value='test-gateway-credential'),patch('crux.council.async_council.AsyncCouncilConfig',side_effect=ValueError('configured google seat unavailable')):
            output=convene(self.root,'consultation','adrs/subject.txt','Review',identity='invalid-seat')
            self.assertIn('google seat unavailable',output['reason'])
        self.assertFalse(list(self.docs.rglob('attempt-*.json')))
    def test_after_dispatch_error_cannot_pass_with_two_votes(self):
        from council_policy import disposition
        from cycle_workflow import digest
        votes=[CouncilVote(model=p+'/model',provider=p,decision='APPROVE' if p!='google' else None,reasoning='supported',confidence=.9,errored=p=='google') for p in ('openai','anthropic','google')]
        output,_=self.call(votes)
        result=disposition(self.root,output['record'],{'agrees':True,'subject_sha256':digest((self.docs/'adrs/subject.txt').read_bytes()),'rationale':'Proceed','dissent':[{'provider':'google','kind':'accepted-tradeoff','explanation':'Unavailable provider'}]})
        self.assertEqual(result['outcome'],'changes-required')
    def test_renamed_subject_preserves_attempt_count_and_prior_findings(self):
        first,_=self.call();(self.docs/'adrs/renamed.txt').write_bytes((self.docs/'adrs/subject.txt').read_bytes())
        second,prompt=self.call(subject='adrs/renamed.txt',progress='New evidence addresses the prior concern.')
        attempt=json.loads((self.docs/second['attempt']).read_bytes());self.assertEqual(attempt['round'],2)
        self.assertIn('prior_reviews',prompt);self.assertIn(first['record'],json.dumps(attempt))
    def test_unknown_mode_record_format_never_reinterprets_as_legacy(self):
        from cycle_council import validate_record
        with self.assertRaises(CycleError):
            validate_record({'format':'crux.cycle-council.v99'},purpose='adr',subject='adrs/subject.txt',subject_sha256='0'*64)

    def test_adr_acceptance_and_idr_gate_share_mode_evaluator(self):
        import decision_policy as dp
        from council_policy import disposition
        from cycle_workflow import digest,mutate,load
        (self.docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        proposal=dp.propose(self.root,{'title':'Evidence','body':'# Decision\nKeep evidence.\n',
            'governs':[{'domain':'evidence','scope':'tree','rule':'Keep evidence.','handle':'keep-evidence'}]},origin='direct')['path']
        reviewed,_=self.call(purpose='adr',subject=proposal)
        disposition(self.root,reviewed['record'],{'agrees':True,'subject_sha256':digest((self.docs/proposal).read_bytes()),'rationale':'Proceed','dissent':[]})
        accepted=dp.accept(self.root,proposal,reviewed['record'],human_approval='Owner accepts this exact ADR')
        self.assertEqual(accepted['standing'],'binding');dp.validate_acceptance(tree(self.root),{'path':proposal})
        cycle=create(self.root,'iterate','Choice','Outcome',['source'],['Correct'],'developer','coordinator')
        contents={'approach':'Use shared reader','alternatives':'Separate readers','assumptions':['Accepted constraints'],
                  'constraints':'Preserve history','intended_evidence':'Related checks'}
        mutate(self.root,cycle['id'],'decision',kind='idr',name='shared-choice',contents=contents)
        first=load(self.root,cycle['id'])['decisions'][-1]['path']
        review,_=self.call(purpose='idr',subject=first,cycle_id=cycle['id'])
        disposition(self.root,review['record'],{'agrees':True,'subject_sha256':digest((self.docs/first).read_bytes()),'rationale':'Proceed','dissent':[]})
        mutate(self.root,cycle['id'],'approve-decision',subject=first,approval=review['record'])
        from cycle_council import logical_identity,history
        logical=logical_identity(tree(self.root),'idr',first,cycle['id'])
        mutate(self.root,cycle['id'],'decision',kind='idr',name='shared-choice',contents=dict(contents,approach='Use the same shared reader after evidence'))
        second=load(self.root,cycle['id'])['decisions'][-1]['path']
        self.assertNotEqual(first,second)
        self.assertEqual(logical_identity(tree(self.root),'idr',second,cycle['id']),logical)
        self.assertEqual(len(history(tree(self.root),'idr',second,logical,cycle['id'])),1)

    def test_section_removal_cannot_reset_started_mode_history(self):
        self.call()
        (self.root/'.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        with patch('crux_env.get',return_value=None):
            with self.assertRaisesRegex(CycleError,'authoriz'):
                convene(self.root,'consultation','adrs/subject.txt','Review again',identity='stable-consultation',progress='New evidence')

    def test_subject_change_between_prompt_and_attempt_refuses_before_dispatch(self):
        import cycle_council
        original=cycle_council.begin_mode
        def change_before_claim(*args,**kwargs):
            (self.docs/'adrs/subject.txt').write_text('Materially different proposal, never shown to providers.')
            return original(*args,**kwargs)
        with patch('cycle_council.begin_mode',side_effect=change_before_claim):
            with self.assertRaisesRegex(CycleError,'changed|mismatch'):
                self.call()
        self.assertFalse(list(self.docs.rglob('attempt-*.json')))

    def test_normalized_reject_and_architectural_are_dispositionable_dissent(self):
        from crux.council.async_council import _parse_gate_findings
        from council_policy import disposition
        from cycle_workflow import digest
        for token in ('REJECT','ARCHITECTURAL'):
            votes=[CouncilVote(model=p+'/model',provider=p,decision=token if p=='google' else 'APPROVE',reasoning='supported',confidence=.9,
                findings=_parse_gate_findings('google_top',[{'id':'F1','dimension':'Security','safety_adjacent':True,'kind':'blocking','text':'Potential constraint conflict; verify artifact.'}]) if p=='google' else []) for p in ('openai','anthropic','google')]
            output,_=self.call(votes,progress='Checkable artifact resolves the allegation '+token if token=='ARCHITECTURAL' else None)
            (self.root/'check.txt').write_text('Named safety assertion passes; alleged constraint does not apply.')
            evidence={'path':'check.txt','sha256':digest((self.root/'check.txt').read_bytes())}
            result=disposition(self.root,output['record'],{'agrees':True,'subject_sha256':digest((self.docs/'adrs/subject.txt').read_bytes()),
                'rationale':'Proceed with named check evidence.','dissent':[{'provider':'google','kind':'refuted','explanation':'Artifact refutes the allegation.','evidence':evidence}]})
            self.assertEqual(result['outcome'],'approved')
    def test_architect_cannot_clear_established_binding_failure_by_omission(self):
        from council_policy import disposition
        from cycle_workflow import digest
        output,_=self.call();base={'agrees':True,'subject_sha256':digest((self.docs/'adrs/subject.txt').read_bytes()),'rationale':'Await required authorization','dissent':[]}
        blocked=disposition(self.root,output['record'],dict(base,binding_failures=['Missing required owner authorization']))
        self.assertEqual(blocked['outcome'],'changes-required')
        again=disposition(self.root,output['record'],base)
        self.assertEqual(again['outcome'],'changes-required')
        with self.assertRaises(CycleError):
            disposition(self.root,output['record'],dict(base,binding_failures=[]))
        artifact=self.root/'authorization-check.txt';artifact.write_text('The named owner authorization is now present and verified.')
        resolution={'failure':'Missing required owner authorization','kind':'resolved','explanation':'Named evidence establishes authorization.',
                    'evidence':{'path':'authorization-check.txt','sha256':digest(artifact.read_bytes())}}
        cleared=disposition(self.root,output['record'],dict(base,binding_resolutions=[resolution]))
        self.assertEqual(cleared['outcome'],'approved')
