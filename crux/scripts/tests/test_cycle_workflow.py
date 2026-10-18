"""Behavioral coverage for bounded cycles and evidence/approval transitions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import *
from bionic_config import load_workflow_policy, BionicConfigError
from cycle_council import validate_approval, validate_record


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=Path(self.temp.name)
        (self.repo/'bionic').mkdir()
        (self.repo/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo/'bionic/objectives.md').write_text('Mission: useful changes with proportional ceremony.')
        (self.repo/'src').mkdir();(self.repo/'src/a.py').write_text('answer = 1\n')
    def cycle(self,kind='iterate'):
        return create(self.repo,kind,'Change','Improve behavior',['src'],['Works'],'builder','tester')
    def apply(self,doc,action,**args):
        return mutate(self.repo,doc['id'],action,**args)
    def plan(self,doc):
        plan=deepcopy(doc['plan'])
        plan.update(verification=['focused tests'],tasks=[{'id':p,'phase':p,'description':p,'depends_on':[],'status':'pending','expected_evidence':['observation']} for p in PHASES[doc['type']]])
        if doc['type']=='refactor':plan.update(preserved_behavior='public API',improvement='shorter test time')
        return self.apply(doc,'plan',plan=plan,reason='initial plan')
    def advance(self,doc):
        for t in doc['plan']['tasks']:
            if t['phase']==doc['phase']:doc=self.apply(doc,'task',task_id=t['id'],state='done')
        return self.apply(doc,'advance')
    def review(self,doc,**override):
        report={'reviewer':'other','scope':['src'],'evidence':['TE-example'], 'blocking':[], 'advisory':[], 'cosmetic':[],'verdict':'approve','rationale':'acceptance and changed behavior reviewed'}
        report.update(override)
        with patch('cycle_workflow.check_tests'):
            return self.apply(doc,'review',report=report)
    def fixture_approval(self,doc,subject,purpose='idr',**override):
        cfg=tree(self.repo)
        record={'format':'crux.cycle-council','purpose':purpose,'subject':subject,'subject_sha256':digest((cfg.docs_root/subject).read_bytes()),'cycle_id':doc['id'],'outcome':'approved','seats':[{'provider':p,'decision':'APPROVE','errored':False,'findings':[]} for p in ('openai','anthropic','google')]}
        record.update(override);record['record_sha256']=digest(encoded(record))
        ref=retained(cfg,doc['id'],'councils',record)
        return ref['path']
    def test_types_and_limits(self):
        for kind in PHASES:
            doc=self.cycle(kind)
            self.assertEqual(doc['phase'],PHASES[kind][0]);self.assertEqual(doc['pass_limit'],LIMITS[kind]);self.assertEqual(doc['pass'],1)
    def test_plan_required_and_tasks_gate(self):
        doc=self.cycle()
        with self.assertRaises(CycleError):self.apply(doc,'advance')
        doc=self.plan(doc)
        with self.assertRaisesRegex(CycleError,'unfinished'):self.apply(doc,'advance')
        self.assertEqual(self.advance(doc)['phase'],'build')
    def test_quick_fix_no_plan(self):
        doc=self.cycle('quick-fix');self.assertEqual(self.advance(doc)['phase'],'test')
        with self.assertRaises(CycleError):self.apply(doc,'plan',plan=doc['plan'],reason='cannot')
    def test_loop_limit_cannot_resume_without_extension(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        args=dict(improved='isolated failure',unresolved='fix needed',next_change='correct path',justification='new cause',progress=True)
        doc=self.apply(doc,'return',**args)
        self.assertEqual(doc['status'],'paused');self.assertEqual(doc['pass'],1)
        with self.assertRaises(CycleError):self.apply(doc,'resume',reason='try again')
        with self.assertRaises(CycleError):self.apply(doc,'change-type',kind='dev',reason='bigger')
        doc=self.apply(doc,'extend',limit=2,human_approval='Owner: one extra pass')
        doc=self.apply(doc,'resume',reason='approved another pass')
        self.assertEqual(doc['pass'],2);self.assertEqual(doc['phase'],'build')
    def test_progress_stall_requires_new_evidence(self):
        doc=self.plan(self.cycle());doc=self.advance(self.advance(doc))
        doc=self.apply(doc,'return',improved='none',unresolved='same issue',next_change='unknown',justification='stalled',progress=False)
        with self.assertRaises(CycleError):self.apply(doc,'resume',reason='retry')
        doc=self.apply(doc,'resume',reason='new root cause',new_evidence='reproduction identifies missing fixture')
        self.assertEqual(doc['pass'],2)
    def test_loop_preserves_plan_history(self):
        doc=self.plan(self.cycle());doc=self.advance(self.advance(doc))
        doc=self.apply(doc,'return',improved='reproduced',unresolved='one failing test',next_change='fix condition',justification='cause established',progress=True)
        self.assertEqual((doc['pass'],doc['phase']),(2,'plan'))
        self.assertTrue(any('plan' in e for e in doc['history']))
    def test_missing_and_stale_tests_block(self):
        doc=self.plan(self.cycle());doc=self.advance(self.advance(doc))
        with self.assertRaisesRegex(CycleError,'coverage'):self.advance(doc)
        doc=self.apply(doc,'checks',checks=['unit'])
        doc=self.apply(doc,'coverage',coverage={'affected':['source behavior'],'checks':[{'check_id':'unit','rationale':'source unit coverage'}],'not_selected':'none'})
        with self.assertRaisesRegex(CycleError,'missing passing'):self.advance(doc)
    def test_independent_review_and_scope(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        with self.assertRaises(CycleError):self.review(doc,reviewer='builder')
        with self.assertRaises(CycleError):self.review(doc,scope=[])
        doc=self.review(doc)
        with patch('cycle_workflow.check_tests'):self.assertEqual(self.advance(doc)['phase'],'reflect')
    def test_changed_scope_invalidates_review(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.review(doc)
        (self.repo/'src/a.py').write_text('answer = 2\n')
        with patch('cycle_workflow.check_tests'),self.assertRaisesRegex(CycleError,'current scope'):self.advance(doc)
    def test_blocking_report_and_nonblocking_advice(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.review(doc,blocking=[{'path':'src/a.py','consequence':'wrong result','evidence':'example'}],verdict='changes-required')
        with patch('cycle_workflow.check_tests'),self.assertRaisesRegex(CycleError,'blocking'):self.advance(doc)
        (self.repo/'src/a.py').write_text('fix attempted without a return')
        with self.assertRaisesRegex(CycleError,'counted return'):self.review(doc)
    def test_dev_requires_exact_idr_revision(self):
        doc=self.plan(self.cycle('dev'))
        with self.assertRaisesRegex(CycleError,'IDR'):self.advance(doc)
        contents={k:['reason'] for k in ('alternatives','approach','assumptions','constraints','intended_evidence')}
        doc=self.apply(doc,'decision',kind='idr',name='choice',contents=contents)
        subject=doc['decisions'][-1]['path'];approval=self.fixture_approval(doc,subject)
        doc=self.apply(doc,'approve-decision',subject=subject,approval=approval)
        self.assertEqual(self.advance(doc)['phase'],'build')
        path=tree(self.repo).docs_root/subject;path.write_text('{}')
        with self.assertRaises(CycleError):self.apply(doc,'advance')
    def test_new_idr_revision_needs_new_approval(self):
        doc=self.plan(self.cycle('dev'));contents={k:['reason'] for k in ('alternatives','approach','assumptions','constraints','intended_evidence')}
        doc=self.apply(doc,'decision',kind='idr',name='choice',contents=contents)
        subject=doc['decisions'][-1]['path'];approval=self.fixture_approval(doc,subject)
        doc=self.apply(doc,'approve-decision',subject=subject,approval=approval)
        doc=self.apply(doc,'decision',kind='idr',name='choice',contents=contents)
        with self.assertRaises(CycleError):self.advance(doc)
    def test_reflect_and_closed_cycles(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.review(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        with self.assertRaises(CycleError):self.advance(doc)
        doc=self.apply(doc,'reflect',reflection={'outcome':'fixed','lessons':'focused tests suffice','remaining':'none'})
        doc=self.apply(doc,'completion',commits=[],exception='Fixture owner requests uncommitted delivery.',remaining='fixture source uncommitted')
        with patch('cycle_workflow.check_tests'):
            doc=self.advance(doc)
        self.assertEqual(doc['status'],'completed')
        with self.assertRaises(CycleError):self.apply(doc,'resume',reason='again')
    def test_bookkeeping_does_not_change_scope(self):
        doc=self.cycle();before=source_fingerprint(self.repo,doc)
        self.apply(doc,'pause',reason='owner pause')
        self.assertEqual(source_fingerprint(self.repo,doc),before)
    def test_bad_configuration_fails_closed(self):
        self.assertEqual(load_workflow_policy(self.repo)['review.scrutiny'],'standard')
        (self.repo/'.bionic.yml').write_text('config_version: "1"\nreview:\n  scrutiny: careless\n')
        with self.assertRaises(BionicConfigError):self.cycle()
    def test_type_preserves_identity_pass_and_history(self):
        doc=self.cycle();updated=self.apply(doc,'change-type',kind='refactor',reason='behavior preserved')
        self.assertEqual(updated['id'],doc['id']);self.assertEqual(updated['pass'],doc['pass'])
        self.assertEqual(updated['pass_limit'],7)
    def test_symlink_scope_refused(self):
        (self.repo/'link').symlink_to(self.repo/'src')
        with self.assertRaises(CycleError):create(self.repo,'iterate','x','y',['link'],['z'],'a','b')
    def test_council_binding_rejects_wrong_provider_or_findings(self):
        doc=self.cycle();cfg=tree(self.repo);subject=retained(cfg,doc['id'],'decisions',{'x':1})['path']
        approval=self.fixture_approval(doc,subject)
        validate_approval(self.repo,approval,purpose='idr',subject=subject)
        record=json.loads((cfg.docs_root/approval).read_text());record['seats'][0]['findings']=[{'kind':'blocking'}]
        record.pop('record_sha256');record['record_sha256']=digest(encoded(record))
        with self.assertRaises(CycleError):validate_record(record,purpose='idr',subject=subject,subject_sha256=record['subject_sha256'])

    def test_reflect_revalidates_source_before_completion(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.review(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.apply(doc,'reflect',reflection={'outcome':'fixed','lessons':'test','remaining':'none'})
        (self.repo/'src/a.py').write_text('changed after review')
        with patch('cycle_workflow.check_tests'),self.assertRaises(CycleError):self.advance(doc)
    def test_change_type_cannot_replace_a_counted_return(self):
        doc=self.plan(self.cycle());doc=self.advance(self.advance(doc))
        with self.assertRaises(CycleError):self.apply(doc,'change-type',kind='refactor',reason='try again')
        paused=self.apply(doc,'pause',reason='scope reassessment')
        with self.assertRaises(CycleError):self.apply(paused,'change-type',kind='refactor',reason='try again while paused')
        doc=self.apply(paused,'resume',reason='record counted return')
        doc=self.apply(doc,'return',improved='cause found',unresolved='failure',next_change='fix condition',justification='new evidence',progress=True)
        updated=self.apply(doc,'change-type',kind='refactor',reason='behavior must stay unchanged')
        self.assertEqual(updated['pass'],2)
        with self.assertRaises(CycleError):self.apply(updated,'change-type',kind='refactor',reason='again')

    def test_decision_query_current_review_requires_current_basis(self):
        doc=self.plan(self.cycle())
        contents={k:['reason'] for k in ('alternatives','approach','assumptions','constraints','intended_evidence')}
        doc=self.apply(doc,'decision',kind='idr',name='choice',contents=contents)
        subject=doc['decisions'][-1]['path'];approval=self.fixture_approval(doc,subject)
        doc=self.apply(doc,'approve-decision',subject=subject,approval=approval)
        doc=self.advance(self.advance(doc))
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.review(doc)
        with patch('cycle_workflow.check_tests'):
            observation=query_decisions(self.repo,doc['id'])
        self.assertTrue(observation['decisions'][0]['delivery']['reviewed_evidence'][0]['matches_current'])
        doc=self.apply(doc,'scrutiny',scrutiny='intensive',rationale='sensitive change',risks=['credentials'])
        with patch('cycle_workflow.check_tests'):
            observation=query_decisions(self.repo,doc['id'])
        report=observation['decisions'][0]['delivery']['reviewed_evidence'][0]
        self.assertTrue(report['matches_current_source'])
        self.assertFalse(report['matches_current'])

if __name__=='__main__':unittest.main()
