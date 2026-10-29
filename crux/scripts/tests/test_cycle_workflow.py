"""Behavioral coverage for bounded cycles and evidence/approval transitions."""
import json
from pathlib import Path
import sys
import subprocess
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
        return create(self.repo,kind,'Change','Improve behavior',['src'],['Works'],'builder','tester',release_list='beta' if kind=='release' else None)
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
        self.assertEqual((doc['pass'],doc['phase'],{t['phase']:t['status'] for t in doc['plan']['tasks']}),(2,'build',{'plan':'done','build':'done','test':'pending','review':'pending','reflect':'pending'}))
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
    def owner_approval(self,doc,subject,**override):
        cfg=tree(self.repo)
        record={'format':'crux.owner-approval','purpose':'idr','cycle_id':doc['id'],'subject':subject,'subject_sha256':digest((cfg.docs_root/subject).read_bytes()),
                'origin':'owner-conversation','quote':'I approve revision 1. Proceed.','date':'2026-10-18','conversation':'owner conversation relayed by main session'}
        record.update(override)
        path=f"cycles/{doc['id']}/approvals/owner.json";(cfg.docs_root/path).parent.mkdir(parents=True,exist_ok=True)
        (cfg.docs_root/path).write_text(json.dumps(record))
        return path
    def idr(self,doc):
        contents={k:['reason'] for k in ('alternatives','approach','assumptions','constraints','intended_evidence')}
        return self.apply(doc,'decision',kind='idr',name='choice',contents=contents)
    def test_owner_direct_idr_approval_binds_exact_revision(self):
        doc=self.idr(self.plan(self.cycle('dev')))
        subject=doc['decisions'][-1]['path']
        doc=self.apply(doc,'approve-decision',subject=subject,approval=self.owner_approval(doc,subject))
        self.assertEqual(self.advance(doc)['phase'],'build')
    def test_owner_direct_approval_refusals(self):
        doc=self.idr(self.plan(self.cycle('dev')))
        subject=doc['decisions'][-1]['path']
        for override,message in (({'quote':'  '},'verbatim quote'),({'origin':'agent'},'owner-conversation'),({'subject_sha256':'0'*64},'exact'),
                                 ({'cycle_id':'CYC-9999'},'another cycle'),({'purpose':'adr'},'IDR revisions only'),({'date':'today'},'YYYY-MM-DD')):
            with self.subTest(override=override),self.assertRaisesRegex(CycleError,message):
                self.apply(doc,'approve-decision',subject=subject,approval=self.owner_approval(doc,subject,**override))
        record=json.loads((tree(self.repo).docs_root/self.owner_approval(doc,subject)).read_text());record.pop('quote')
        path=f"cycles/{doc['id']}/approvals/noquote.json";(tree(self.repo).docs_root/path).write_text(json.dumps(record))
        with self.assertRaisesRegex(CycleError,'exactly'):self.apply(doc,'approve-decision',subject=subject,approval=path)
        approved=self.apply(doc,'approve-decision',subject=subject,approval=self.owner_approval(doc,subject))
        approved=self.idr(approved)
        with self.assertRaisesRegex(CycleError,'not approved'):self.apply(approved,'advance')
    def owner_completion(self,**override):
        (self.repo/'authority.md').write_text('owner override\n')
        owner={'origin':'owner-conversation','quote':'i authorize marking it as completed','date':'2026-10-18','conversation':'owner conversation','authority':['authority.md']}
        owner.update(override);return owner
    def test_owner_complete_preserves_record_and_quotes_owner(self):
        doc=self.plan(self.cycle('iterate'))
        doc=self.apply(doc,'pause',reason='gates cannot be satisfied')
        before=deepcopy(doc)
        doc=self.apply(doc,'owner-complete',owner=self.owner_completion())
        self.assertEqual(doc['status'],'completed')
        for key in ('blocker','evidence','reviews','release','reflection','decisions','plan','phase','pass','completion'):
            self.assertEqual(doc[key],before[key],key)
        self.assertEqual(doc['history'][:-1],before['history'])
        last=doc['history'][-1]
        self.assertEqual(last['action'],'owner-complete');self.assertEqual(last['owner']['quote'],'i authorize marking it as completed')
        self.assertEqual(last['owner']['authority'],[{'path':'authority.md','sha256':digest(b'owner override\n')}])
        with self.assertRaisesRegex(CycleError,'closed'):self.apply(doc,'owner-complete',owner=self.owner_completion())
    def test_owner_complete_refusals(self):
        doc=self.apply(self.cycle('iterate'),'pause',reason='blocked')
        for override,message in (({'quote':''},'verbatim quote'),({'origin':'agent'},'owner-conversation'),({'authority':[]},'authority file'),
                                 ({'authority':['missing.md']},'does not exist'),({'authority':['../x']},'parent'),({'date':'x'},'YYYY-MM-DD')):
            with self.subTest(override=override),self.assertRaisesRegex(CycleError,message):
                self.apply(doc,'owner-complete',owner=self.owner_completion(**override))
        owner=self.owner_completion();owner.pop('quote')
        with self.assertRaisesRegex(CycleError,'exactly'):self.apply(doc,'owner-complete',owner=owner)
        self.assertEqual(load(self.repo,doc['id'])['status'],'paused')
    def test_reflect_and_closed_cycles(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.review(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        with self.assertRaises(CycleError):self.advance(doc)
        doc=self.apply(doc,'reflect',reflection={'outcome':'fixed','lessons':['focused tests suffice'],'remaining':['none']})
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
        doc=self.apply(doc,'reflect',reflection={'outcome':'fixed','lessons':['test'],'remaining':['none']})
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

    # --- ignored files are outside the scope fingerprint and the completion check ---
    def git(self,*args):
        return subprocess.run(['git','-C',str(self.repo),*args],capture_output=True,text=True,check=True).stdout.strip()
    def git_repo(self):
        self.git('init','-q');self.git('config','user.email','t@example.com');self.git('config','user.name','t')
        (self.repo/'.gitignore').write_text('*.lock\n__pycache__/\n')
        self.git('add','.gitignore','src');self.git('commit','-q','-m','base')
        return self.git('rev-parse','HEAD')
    def v1_review(self,doc):
        original=source_fingerprint
        with patch('cycle_workflow.source_fingerprint',lambda repo,d:original(repo,d,version=1)):
            return self.review(doc)
    def to_review(self):
        doc=self.cycle('quick-fix');doc=self.advance(doc)
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        return doc
    def test_ignored_file_in_scope_keeps_review_and_completion_bound(self):
        sha=self.git_repo()
        doc=self.to_review();doc=self.review(doc)
        lock=self.repo/'src/attempt-1.lock';lock.write_text('held\n')
        self.assertEqual(self.git('status','--porcelain','--ignored','src').splitlines(),['!! src/attempt-1.lock'])
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        doc=self.apply(doc,'reflect',reflection={'outcome':'fixed','lessons':['ignored files stay out'],'remaining':['none']})
        doc=self.apply(doc,'completion',commits=[sha],remaining='none')
        lock.unlink()
        with patch('cycle_workflow.check_tests'):doc=self.advance(doc)
        self.assertEqual(doc['status'],'completed')
    def test_ignored_file_does_not_change_fingerprint_but_tracked_and_untracked_do(self):
        self.git_repo();doc=self.cycle('quick-fix');base=source_fingerprint(self.repo,doc)
        lock=self.repo/'src/attempt-1.lock';lock.write_text('x');(self.repo/'src/__pycache__').mkdir();(self.repo/'src/__pycache__/a.pyc').write_text('x')
        self.assertEqual(source_fingerprint(self.repo,doc),base)
        lock.unlink();self.assertEqual(source_fingerprint(self.repo,doc),base)
        (self.repo/'src/a.py').write_text('answer = 2\n');self.assertNotEqual(source_fingerprint(self.repo,doc),base)
        (self.repo/'src/a.py').write_text('answer = 1\n');(self.repo/'src/new.py').write_text('x = 1\n')
        self.assertNotEqual(source_fingerprint(self.repo,doc),base)
    def test_untracked_and_tracked_edits_still_block_completion(self):
        sha=self.git_repo();doc=self.cycle('quick-fix');cfg=tree(self.repo)
        doc['completion']={'commits':[sha],'exception':None,'remaining':'none','input_sha256':source_fingerprint(self.repo,doc)}
        check_completion(cfg,doc)
        (self.repo/'src/attempt-1.lock').write_text('x');check_completion(cfg,doc)
        (self.repo/'src/new.py').write_text('x = 1\n')
        doc['completion']['input_sha256']=source_fingerprint(self.repo,doc)
        with self.assertRaisesRegex(CycleError,'uncommitted'):check_completion(cfg,doc)
        (self.repo/'src/new.py').unlink()
        (self.repo/'src/a.py').write_text('answer = 2\n');doc['completion']['input_sha256']=source_fingerprint(self.repo,doc)
        with self.assertRaisesRegex(CycleError,'uncommitted'):check_completion(cfg,doc)
    def test_v1_recorded_review_still_binds_and_is_never_looser(self):
        self.git_repo();doc=self.to_review();doc=self.v1_review(doc)
        report=read_retained(tree(self.repo),doc['reviews'][-1])
        self.assertEqual(report['input_sha256'],source_fingerprint(self.repo,doc,version=1))
        with patch('cycle_workflow.check_tests'):check_review(tree(self.repo),doc)
        lock=self.repo/'src/attempt-1.lock';lock.write_text('held\n')
        self.assertNotEqual(source_fingerprint(self.repo,doc,version=1),report['input_sha256'])
        with patch('cycle_workflow.check_tests'),self.assertRaises(CycleError):check_review(tree(self.repo),doc)
        lock.unlink()
        with patch('cycle_workflow.check_tests'):check_review(tree(self.repo),doc)
    def test_v2_recorded_review_survives_the_same_ignored_change(self):
        self.git_repo();doc=self.to_review();doc=self.review(doc)
        (self.repo/'src/attempt-1.lock').write_text('held\n')
        with patch('cycle_workflow.check_tests'):check_review(tree(self.repo),doc)
    def test_v1_recorded_completion_and_reduction_bind_via_either_version(self):
        self.git_repo();doc=self.cycle('simplify');cfg=tree(self.repo)
        v1=source_fingerprint(self.repo,doc,version=1)
        self.assertTrue(fingerprint_binds(self.repo,doc,v1));self.assertTrue(fingerprint_binds(self.repo,doc,source_fingerprint(self.repo,doc)))
        area={'change':'decrease','before':'3 branches','after':'2 branches','evidence':['diff']}
        doc['reduction']={'pass':doc['pass'],'at':'t','input_sha256':v1,'areas':{n:dict(area) for n in REDUCTION_AREAS}}
        check_reduction(cfg,doc)
        (self.repo/'src/attempt-1.lock').write_text('x')
        with self.assertRaisesRegex(CycleError,'stale'):check_reduction(cfg,doc)
        doc['reduction']['input_sha256']=source_fingerprint(self.repo,doc);check_reduction(cfg,doc)
        (self.repo/'src/attempt-1.lock').unlink()
        doc['completion']={'commits':[],'exception':'owner asked','remaining':'none','input_sha256':v1}
        check_completion(cfg,doc)
    def test_scope_pattern_shapes_and_missing_pattern(self):
        self.git_repo();(self.repo/'src/sub').mkdir();(self.repo/'src/sub/b.py').write_text('b\n')
        doc=self.cycle('quick-fix');doc['plan']['scope']=['src/a.py']
        single=source_fingerprint(self.repo,doc)
        doc['plan']['scope']=['src/**/*.py'];globbed=source_fingerprint(self.repo,doc)
        doc['plan']['scope']=['src/missing.py'];missing=source_fingerprint(self.repo,doc)
        (self.repo/'src/missing.py').write_text('m\n')
        self.assertNotEqual(source_fingerprint(self.repo,doc),missing)
        self.assertEqual(len({single,globbed,missing}),3)
        doc['plan']['scope']=['src/a.py'];(self.repo/'src/a.py').unlink()
        self.assertNotEqual(source_fingerprint(self.repo,doc),single)
    def test_non_git_tree_keeps_working(self):
        doc=self.cycle('quick-fix');base=source_fingerprint(self.repo,doc)
        (self.repo/'src/x.lock').write_text('x');self.assertNotEqual(source_fingerprint(self.repo,doc),base)

    def test_project_below_git_top_level_still_blocks_untracked_scope_files(self):
        proj=self.repo/'proj';(proj/'bionic').mkdir(parents=True)
        for name in ('manifest.yml','objectives.md'):(proj/'bionic'/name).write_bytes((self.repo/'bionic'/name).read_bytes())
        (proj/'src').mkdir();(proj/'src/a.py').write_text('answer = 1\n')
        self.git_repo()
        self.git('add','proj');self.git('commit','-q','-m','proj');sha=self.git('rev-parse','HEAD')
        doc=create(proj,'quick-fix','Change','Improve behavior',['src'],['Works'],'builder','tester');cfg=tree(proj)
        (proj/'src/attempt-1.lock').write_text('x')
        doc['completion']={'commits':[sha],'exception':None,'remaining':'none','input_sha256':source_fingerprint(proj,doc)}
        check_completion(cfg,doc)
        (proj/'src/new.py').write_text('x = 1\n')
        doc['completion']['input_sha256']=source_fingerprint(proj,doc)
        with self.assertRaisesRegex(CycleError,'uncommitted'):check_completion(cfg,doc)

    def test_recursive_glob_scope_sees_direct_children(self):
        sha=self.git_repo();doc=self.cycle('quick-fix');cfg=tree(self.repo)
        (self.repo/'top.md').write_text('t\n');self.git('add','top.md');self.git('commit','-q','-m','top');sha=self.git('rev-parse','HEAD')
        for scope,edited in ((['src/**/*.py'],'src/a.py'),(['**/*.md'],'top.md')):
            doc['plan']['scope']=scope;base=source_fingerprint(self.repo,doc)
            path=self.repo/edited;original=path.read_text();path.write_text(original+'more\n')
            self.assertNotEqual(source_fingerprint(self.repo,doc),base,scope)
            path.write_text(original);self.assertEqual(source_fingerprint(self.repo,doc),base)
        doc['plan']['scope']=['src/**/*.py']
        doc['completion']={'commits':[sha],'exception':None,'remaining':'none','input_sha256':source_fingerprint(self.repo,doc)}
        check_completion(cfg,doc)
        (self.repo/'src/attempt-1.lock').write_text('x');check_completion(cfg,doc)
        (self.repo/'src/new.py').write_text('x = 1\n')
        doc['completion']['input_sha256']=source_fingerprint(self.repo,doc)
        with self.assertRaisesRegex(CycleError,'uncommitted'):check_completion(cfg,doc)
    def test_ignored_file_matching_a_previously_empty_glob_changes_nothing(self):
        self.git_repo();doc=self.cycle('quick-fix');doc['plan']['scope']=['src/*.lock'];base=source_fingerprint(self.repo,doc)
        (self.repo/'src/attempt-1.lock').write_text('x');self.assertEqual(source_fingerprint(self.repo,doc),base)
    def test_tracked_file_matching_an_ignore_rule_still_counts(self):
        self.git_repo();(self.repo/'src/kept.lock').write_text('x');self.git('add','-f','src/kept.lock');self.git('commit','-q','-m','kept')
        doc=self.cycle('quick-fix');base=source_fingerprint(self.repo,doc)
        (self.repo/'src/kept.lock').write_text('y');self.assertNotEqual(source_fingerprint(self.repo,doc),base)
    def test_without_git_binary_fingerprint_falls_back_to_v1_and_completion_fails_closed(self):
        sha=self.git_repo();doc=self.cycle('quick-fix');cfg=tree(self.repo)
        empty=tempfile.mkdtemp(dir=self.temp.name)
        doc['completion']={'commits':[sha],'exception':None,'remaining':'none','input_sha256':source_fingerprint(self.repo,doc,version=1)}
        with patch.dict('os.environ',{'PATH':empty}):
            self.assertEqual(source_fingerprint(self.repo,doc),source_fingerprint(self.repo,doc,version=1))
            with self.assertRaises(CycleError):check_completion(cfg,doc)
    def test_project_below_git_top_level_uses_the_ignored_file_rule(self):
        proj=self.repo/'proj';(proj/'bionic').mkdir(parents=True)
        for name in ('manifest.yml','objectives.md'):(proj/'bionic'/name).write_bytes((self.repo/'bionic'/name).read_bytes())
        (proj/'src').mkdir();(proj/'src/a.py').write_text('answer = 1\n')
        self.git_repo();self.git('add','proj');self.git('commit','-q','-m','proj')
        doc=create(proj,'quick-fix','Change','Improve behavior',['src'],['Works'],'builder','tester');base=source_fingerprint(proj,doc)
        (proj/'src/attempt-1.lock').write_text('x');self.assertEqual(source_fingerprint(proj,doc),base)
        (proj/'src/new.py').write_text('x\n');self.assertNotEqual(source_fingerprint(proj,doc),base)

    def completion_doc(self,scope,sha):
        doc=self.cycle('quick-fix');doc['plan']['scope']=scope
        doc['completion']={'commits':[sha],'exception':None,'remaining':'none','input_sha256':source_fingerprint(self.repo,doc)}
        return doc
    def assert_blocked(self,cfg,doc):
        doc['completion']['input_sha256']=source_fingerprint(self.repo,doc)
        with self.assertRaisesRegex(CycleError,'uncommitted'):check_completion(cfg,doc)
    def test_recursive_glob_scope_blocks_uncommitted_tracked_changes(self):
        sha=self.git_repo();cfg=tree(self.repo);doc=self.completion_doc(['src/**/*.py'],sha)
        check_completion(cfg,doc)
        path=self.repo/'src/a.py'
        path.write_text('answer = 2\n');self.assert_blocked(cfg,doc)  # unstaged
        self.git('add','src/a.py');self.assert_blocked(cfg,doc)  # staged
        self.git('commit','-q','-m','later');self.assert_blocked(cfg,doc)  # committed after the recorded commit
        self.git('reset','-q','--hard',sha);doc['completion']['input_sha256']=source_fingerprint(self.repo,doc);check_completion(cfg,doc)
        path.unlink();self.assert_blocked(cfg,doc)  # deleted tracked path, unstaged
        self.git('rm','-q','--cached','src/a.py');self.assert_blocked(cfg,doc)  # staged deletion
    def test_recursive_glob_scope_ignores_changes_outside_the_scope(self):
        sha=self.git_repo();cfg=tree(self.repo);doc=self.completion_doc(['src/**/*.py'],sha)
        (self.repo/'other.txt').write_text('o\n');self.git('add','other.txt');check_completion(cfg,doc)
        (self.repo/'.gitignore').write_text('*.lock\n');check_completion(cfg,doc)
    def test_recursive_glob_scope_below_git_top_level(self):
        proj=self.repo/'proj';(proj/'bionic').mkdir(parents=True)
        for name in ('manifest.yml','objectives.md'):(proj/'bionic'/name).write_bytes((self.repo/'bionic'/name).read_bytes())
        (proj/'src').mkdir();(proj/'src/a.py').write_text('answer = 1\n')
        self.git_repo();self.git('add','proj');self.git('commit','-q','-m','proj');sha=self.git('rev-parse','HEAD')
        doc=create(proj,'quick-fix','Change','Improve behavior',['src/**/*.py'],['Works'],'builder','tester');cfg=tree(proj)
        doc['completion']={'commits':[sha],'exception':None,'remaining':'none','input_sha256':source_fingerprint(proj,doc)}
        check_completion(cfg,doc)
        (self.repo/'src/a.py').write_text('outside the project\n');check_completion(cfg,doc)
        (proj/'src/a.py').write_text('answer = 2\n');doc['completion']['input_sha256']=source_fingerprint(proj,doc)
        with self.assertRaisesRegex(CycleError,'uncommitted'):check_completion(cfg,doc)
    def test_rename_out_of_scope_blocks_completion_staged_and_committed(self):
        sha=self.git_repo();cfg=tree(self.repo);doc=self.completion_doc(['src/**/*.py'],sha)
        check_completion(cfg,doc)
        (self.repo/'other').mkdir();self.git('mv','src/a.py','other/a.py')
        self.assert_blocked(cfg,doc)  # staged rename: the in-scope source must still count
        self.git('commit','-q','-m','move');self.assert_blocked(cfg,doc)  # committed after the recorded commit
    def test_scope_walk_and_name_predicate_agree_on_glob_shapes(self):
        self.git_repo();cfg=tree(self.repo);doc=self.cycle('quick-fix')
        for name in ('src/sub/b.py','src/sub/deep/c.py','src/notes.md','docs/top.py','top.py'):
            path=self.repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('x\n')
        own=(cfg.docs_root/'cycles').relative_to(cfg.repo_root).as_posix()
        root=cfg.repo_root;files=[p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()]
        files=[f for f in files if not f.startswith(own+'/') and '.git' not in f.split('/')]
        for pattern in ('**/*.py','src/*','src/a.py','src/**','src','src/**/*.py'):
            walked={n for _,names in scope_files(root,cfg,doc,[pattern]) for n in names}
            named={f for f in files if scope_name_in_scope(f,[pattern])}
            self.assertTrue(walked,pattern);self.assertEqual(walked,named,pattern)

if __name__=='__main__':unittest.main()
