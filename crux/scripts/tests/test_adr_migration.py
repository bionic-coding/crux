"""Prospective migration validation is exact, resumable and non-authoritative."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adr_migration as m
import decision_policy as dp
from cycle_workflow import CycleError, digest, encoded, tree


class MigrationFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.docs = self.root/'bionic'; self.docs.mkdir()
        self.git('init', '-q'); self.git('config', 'user.email', 'test@example.invalid'); self.git('config', 'user.name', 'Test')
        (self.root/'.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs/'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.docs/'objectives.md').write_text('---\nmaturity: forming\n---\n# Objectives\nPreserve durable decisions.\n')
        self.write('record.txt', 'Keep existing approvals.\n')
        self.subject = dp.propose(self.root, {'title':'Migration', 'body':f'# Decision\nPreserve approvals.\nThis decision names `record.txt` at sha256 `{self.bind("record.txt")["sha256"]}`.\n',
            'governs':[{'domain':'migration','rule':'Preserve approvals.','scope':'adrs','handle':'preserve-approvals'}]}, origin='direct')['path']
        self.proposed = (self.docs/self.subject).read_bytes()
        self.adr_council = self.write('bionic/adrs/councils/adr.json', self.council(self.subject, digest(self.proposed), purpose='adr'))
        dp.accept(self.root, self.subject, 'adrs/councils/adr.json', human_approval='Owner: accept ADR only')
        self.write('record.txt', 'Keep existing approvals.\n')
        self.write('proof/source.py', '# validator source\n')
        for name in m.READINESS_INVENTORY:
            self.write(name,(Path(__file__).resolve().parents[3]/name).read_text())
        self.verified_sources=[self.bind(name) for name in (*m.READINESS_INVENTORY,'proof/source.py')]
        self.write('proof/tests.json', {'result':'passed', 'command':['python','-m','unittest','test_migration'], 'inputs':self.verified_sources})
        self.write('proof/review.json', {'verdict':'approve', 'reviewer':'independent', 'implementers':['developer'], 'inputs':self.verified_sources})
        self.commit('U1 verified')
        self.readiness = {'commit':self.head(), 'sources':self.verified_sources, 'tests':[self.bind('proof/tests.json')], 'review':self.bind('proof/review.json')}
        source = self.bind('bionic/'+self.subject)
        from decision_policy import frontmatter
        rule = frontmatter((self.docs/self.subject).read_text())[0]['governs'][0]
        self.package = {'format':m.FORMATS['package'], 'id':'batch-one', 'initial':True,
            'record':self.bind('record.txt'), 'governing_adr':{'source':source,'receipt':'bionic/adrs/acceptances/ADR-0001.json'},
            'dependencies':[dict(self.bind('bionic/objectives.md'), kind='objectives')], 'items':[{
                'id':'item-one','source':source,'handle':rule['handle'],'clause_sha256':digest(encoded(rule)),
                'disposition':'retire','rationale':'This obligation serves no current objective, evidenced by the reviewed assessment.',
                'original_rationale':'Preserved approval evidence.', 'continuing':[], 'ceasing':['Preserve approvals.'], 'successors':[], 'depends_on':[]}], 'owner_stops':[]}
        self.package_path = 'bionic/adrs/migrations/packages/batch-one.json'
        self.write(self.package_path, self.package)
        self.council_path = 'bionic/adrs/councils/disposition.json'
        self.vote = self.council(self.package_path.removeprefix('bionic/'), digest(encoded(self.package)))
        self.vote['readiness'] = self.readiness; self.vote['review_bundle_sha256']=digest(encoded(m.review_bundle(self.root,self.package_path))); self.seal(self.vote)
        self.write(self.council_path, self.vote); self.commit('Council after readiness')
        self.owner = {'origin':'owner-conversation','quote':'I approve these dispositions.', 'action':'approve-dispositions', 'at':'2026-10-16T10:00:00Z','conversation':'conversation/message-42',
                      'presented':self.bind(self.package_path)}

    def git(self, *args):
        r = subprocess.run(['git','-C',str(self.root),*args], capture_output=True)
        if r.returncode: raise AssertionError(r.stderr.decode())
        return r.stdout.decode().strip()
    def commit(self, text): self.git('add','.'); self.git('commit','-qm',text)
    def head(self): return self.git('rev-parse','HEAD')
    def write(self, path, value):
        target=self.root/path; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value.encode() if isinstance(value,str) else encoded(value)); return target
    def bind(self,path): return {'path':path,'sha256':digest((self.root/path).read_bytes())}
    def seal(self, row):
        row.pop('record_sha256',None); row['record_sha256']=digest(encoded(row)); return row
    def council(self,subject,sha,purpose='disposition'):
        return self.seal({'format':'crux.cycle-council','purpose':purpose,'subject':subject,'subject_sha256':sha,'outcome':'approved','cycle_id':None,
            'seats':[{'provider':p,'decision':'APPROVE','errored':False,'findings':[]} for p in ('one','two','three')]})
    def evidence(self, initial=True, policy='council-and-human', owner=True, vote=None):
        return m.validate_evidence(self.root, self.package_path, vote or self.vote, readiness=self.readiness,
            initial=initial, policy=policy, owner=self.owner if owner else None)


class ApprovalMatrixTests(MigrationFixture):
    def test_mode_aware_migration_uses_shared_standard_evaluator(self):
        from council_policy import RECORD,normalized
        council=copy.deepcopy(self.vote)
        council.update(format=RECORD,id='fixture',logical_id='migration:batch-one',at='2026-10-17T00:00:00Z',
            attempt='adrs/councils/attempt-fixture.json',policy={'mode':'standard','settings':normalized({'council':{'mode':'standard'}}),
                'human_policy':'council-and-human','max_attempts':7,'policy_inputs':[],'initialization':True,'models':{}},passes=[],reason=None,binding_failures=[],
            architect={'agrees':True,'subject_sha256':council['subject_sha256'],'rationale':'Non-binding preference disposition.',
                'dissent':[{'provider':'three','kind':'accepted-tradeoff','explanation':'Presentation preference, no binding failure.'}]})
        council['seats'][2].update(decision='REQUEST_CHANGES',findings=[{'kind':'blocking','id':'F1'}])
        self.seal(council)
        self.evidence(vote=council)
        council['binding_failures']=['Demonstrated missing owner authorization'];self.seal(council)
        with self.assertRaises(CycleError):self.evidence(vote=council)

    def test_four_rows_by_council_controls(self):
        for initial in (True,False):
            for policy in ('council-and-human','council-only'):
                with self.subTest(initial=initial,policy=policy,control='C0'):
                    self.evidence(initial,policy,owner=initial or policy=='council-and-human')
                for case in range(1,11):
                    vote=copy.deepcopy(self.vote); package=copy.deepcopy(self.package); readiness=copy.deepcopy(self.readiness)
                    if case==1: vote={}
                    elif case==2: vote['seats'][0]['findings']=[{'kind':'blocking'}]
                    elif case==3: vote['seats'].pop()
                    elif case==4: vote['seats'][0]['errored']=True
                    elif case==5: vote['seats'][0]['decision']='TRUNCATED'
                    elif case==6: vote['seats'][0]['decision']=None
                    elif case==7: vote['subject_sha256']='0'*64
                    elif case==8: vote['purpose']='adr'
                    elif case==9: readiness['commit']='0'*40; vote['readiness']=readiness
                    elif case==10: package['dependencies'][0]['sha256']='0'*64; self.write(self.package_path,package)
                    if vote:self.seal(vote)
                    with self.subTest(initial=initial,policy=policy,control=f'C{case}'), self.assertRaises((CycleError,ValueError)):
                        m.validate_evidence(self.root,self.package_path,vote,readiness=readiness,initial=initial,policy=policy,owner=self.owner)
                    self.write(self.package_path,self.package)

    def test_owner_controls_and_initial_council_only_exception(self):
        for initial,policy in ((True,'council-and-human'),(True,'council-only'),(False,'council-and-human')):
            for change in (None,{'quote':''},{'action':'accept-adr'},{'origin':'repository'},{'origin':'model'},{'origin':'council'}, {'conversation':''},{'at':''},{'presented':{'path':self.package_path,'sha256':'0'*64}}):
                owner=copy.deepcopy(self.owner)
                if change is None:owner=None
                else:owner.update(change)
                with self.subTest(initial=initial,policy=policy,change=change),self.assertRaises(CycleError):
                    m.validate_evidence(self.root,self.package_path,self.vote,readiness=self.readiness,initial=initial,policy=policy,owner=owner)
        self.evidence(False,'council-only',owner=False)

    def test_early_late_owner_and_metadata_bridge(self):
        for timestamp in ('2000-01-01T00:00:00Z','2099-01-01T00:00:00Z'):
            self.owner['at']=timestamp; self.evidence()
        self.package['governing_adr']['source']['sha256']=digest(self.proposed)
        self.write(self.package_path,self.package)
        m.validate_package(self.root,self.package_path)
        path=self.docs/self.subject; original=path.read_text()
        path.write_text(original.replace('Preserve approvals.','Discard approvals.'))
        with self.assertRaises(CycleError):m.validate_package(self.root,self.package_path)

    def test_exact_map_and_reserialization_invalidate_owner(self):
        for change in ('whitespace','map','record'):
            if change=='whitespace':(self.root/self.package_path).write_text(json.dumps(self.package))
            if change=='map':
                updated=copy.deepcopy(self.package);updated['items'][0]['ceasing']=['Different'];self.write(self.package_path,updated)
            if change=='record':self.write('record.txt','changed')
            with self.subTest(change=change),self.assertRaises(CycleError):self.evidence()
            self.write(self.package_path,self.package);self.write('record.txt','Keep existing approvals.\n')

    def test_owner_stop_is_independent_of_policy_and_clearance_is_no_approval(self):
        self.package['owner_stops']=[{'id':'stop-one','items':['item-one'],'instruction':dict(self.owner,action='stop'),'resolution':None}]
        self.write(self.package_path,self.package)
        for initial in (True,False):
            for policy in ('council-and-human','council-only'):
                with self.assertRaisesRegex(CycleError,'owner stop'):m.validate_package(self.root,self.package_path)
        resolution=copy.deepcopy(self.owner);resolution['action']='clear-stop'; self.package['owner_stops'][0]['resolution']=resolution
        self.write(self.package_path,self.package);m.validate_package(self.root,self.package_path)
        # A clearance itself can never stand in for disposition approval.
        with self.assertRaises(CycleError):m.validate_owner(resolution,self.bind(self.package_path),'approve-dispositions')


class QueueAndFormatTests(MigrationFixture):
    def test_queue_resume_transitive_invalidation_and_preservation(self):
        items=[{'id':name,'bindings':[self.bind('record.txt')] if name=='a' else [],'depends_on':deps,'revision':1,'status':'done','evidence':[self.bind('proof/source.py')]} for name,deps in (('a',[]),('b',['a']),('c',[]))]
        queue=m.create_queue(self.root,'queue-one',items)
        path='bionic/adrs/migrations/queues/queue-one.json'; before=(self.root/path).read_bytes()
        self.assertEqual(m.resume_queue(self.root,path),queue);self.assertEqual(before,(self.root/path).read_bytes())
        self.write('record.txt','drift'); resumed=m.resume_queue(self.root,path)
        self.assertEqual([x['status'] for x in resumed['items']],['invalidated','invalidated','done'])
        self.assertEqual(resumed['items'][0]['evidence'],[self.bind('proof/source.py')])

    def test_unknown_absent_and_schema_invalid_refuse_without_write(self):
        queue=m.create_queue(self.root,'queue-one',[]); path='bionic/adrs/migrations/queues/queue-one.json'
        for change in ({'format':None},{'format':'crux.adr-migration-queue.v2'},{'items':'wrong'},{'extra':True}):
            updated=dict(queue);updated.update(change);self.write(path,updated);before=(self.root/path).read_bytes()
            with self.assertRaises(CycleError):m.resume_queue(self.root,path)
            self.assertEqual(before,(self.root/path).read_bytes())
        for identity in ('../escape','x/y','x.application','x.publication','Bad',''):
            with self.subTest(identity=identity),self.assertRaises(CycleError):m.create_queue(self.root,identity,[])

    def test_candidate_is_explicitly_nonauthoritative_and_cli_roundtrip(self):
        self.assertEqual(m.candidate_facts(self.root,self.package_path)['authority'],'none')
        spec=importlib.util.spec_from_file_location('adr_migration_cli',Path(__file__).resolve().parents[1]/'adr-migration.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli.main(['package','--repo-root',str(self.root),'--path',self.package_path]),0)
        self.assertEqual(json.loads(out.getvalue())['authority'],'none')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['package','--repo-root',str(self.root),'--path','../escape']),1)


class CommittedEvidenceTests(MigrationFixture):
    def test_approval_write_commit_validate_candidate_and_resume(self):
        receipt=m.record_approval(self.root,'approval-one',self.package_path,self.council_path,self.readiness,owner=self.owner)
        path='bionic/adrs/migrations/approvals/approval-one.json'
        self.assertEqual(receipt,m.validate_approval(self.root,path,committed=False))
        with self.assertRaisesRegex(CycleError,'committed'):m.validate_approval(self.root,path)
        self.commit('Owner disposition approval')
        self.assertEqual(receipt,m.validate_approval(self.root,path))
        candidate=m.write_candidate(self.root,'publication-one',self.package_path,path)
        self.assertEqual(candidate['authority'],'none')
        self.assertEqual(m.validate_candidate(self.root,'bionic/adrs/migrations/candidates/publication-one.json')['authority'],'none')
        before=(self.root/path).read_bytes()
        # Calling the writer after its receipt is committed must reuse that exact
        # receipt, not rebind its policy to a later HEAD or request owner approval.
        self.assertEqual(m.record_approval(self.root,'approval-one',self.package_path,self.council_path,self.readiness,owner=self.owner),receipt)
        self.assertEqual(before,(self.root/path).read_bytes())
        for change in ({'format':None},{'format':'crux.adr-migration-publication.v2'},{'authority':'governing'},{'package':'wrong'}):
            value=dict(candidate);value.update(change);self.write('bionic/adrs/migrations/candidates/publication-one.json',value)
            with self.assertRaises(CycleError):m.validate_candidate(self.root,'bionic/adrs/migrations/candidates/publication-one.json')
        self.assertFalse(list((self.docs/'adrs/migrations').glob('*.application.json')))
        self.assertFalse(list((self.docs/'adrs/migrations').glob('*.publication.json')))

    def test_readiness_commit_test_review_ancestry_and_immutability(self):
        m.validate_readiness(self.root,self.readiness)
        for change in ({'commit':self.head()[:8]},{'commit':'0'*40},{'tests':[]},{'sources':[]},{'review':dict(self.readiness['review'],sha256='0'*64)}):
            value=copy.deepcopy(self.readiness);value.update(change)
            with self.subTest(change=change),self.assertRaises(CycleError):m.validate_readiness(self.root,value)
        # An uncommitted edited passing test summary cannot replace basis evidence.
        for name in m.READINESS_INVENTORY:
            self.write(name,(Path(__file__).resolve().parents[3]/name).read_text())
        self.verified_sources=[self.bind(name) for name in (*m.READINESS_INVENTORY,'proof/source.py')]
        self.write('proof/tests.json',{'result':'passed','command':['true'],'inputs':[]})
        changed=copy.deepcopy(self.readiness);changed['tests']=[self.bind('proof/tests.json')]
        with self.assertRaises(CycleError):m.validate_readiness(self.root,changed)
        # A basis created after the council was committed cannot validate it.
        self.commit('Later evidence');future=copy.deepcopy(self.readiness);future['commit']=self.head()
        future['tests']=[self.bind('proof/tests.json')]
        with self.assertRaises(CycleError):m.validate_readiness(self.root,future,action_commit=m.introduction(self.root,self.council_path))

    def test_approval_rejects_pre_readiness_council_and_changed_record(self):
        earlier=copy.deepcopy(self.readiness);earlier['commit']=self.head()
        self.vote['readiness']=earlier;self.seal(self.vote);self.write(self.council_path,self.vote)
        with self.assertRaisesRegex(CycleError,'edited|precede'):m.record_approval(self.root,'one',self.package_path,self.council_path,earlier,owner=self.owner)

    def test_policy_requires_prior_owner_instruction_and_first_parent(self):
        parent=self.head()
        config='config_version: "1"\ndocs_dir: bionic\nadr:\n  acceptance: council-only\n'
        self.write('.bionic.yml',config)
        self.commit('Unapproved policy')
        with self.assertRaisesRegex(CycleError,'owner instruction'):m.policy_at(self.root,self.head())
        instruction=dict(self.owner,action='change-policy',presented=self.bind('.bionic.yml'))
        record={'format':m.FORMATS['policy'],'id':'policy-one','previous_policy':'council-only','policy':'council-only','instruction':instruction,'pending_action':None}
        self.write('bionic/adrs/migrations/policies/policy-one.json',record);self.commit('Owner selects policy')
        self.assertEqual(m.policy_at(self.root,self.head()),'council-only')
        self.assertEqual(m.policy_at(self.root,parent),'council-and-human')
        approval={'format':m.FORMATS['approval'],'id':'one','package':self.bind(self.package_path),'council':self.bind(self.council_path),'readiness':self.readiness,
                  'review_bundle_sha256':self.vote['review_bundle_sha256'],'policy':'council-only','policy_basis':self.head(),'owner':self.owner,'at':'2026-10-16T12:00:00Z'}
        # Policy authored in the action commit cannot authorize itself.
        with self.assertRaisesRegex(CycleError,'before the action'):m.validate_approval_data(self.root,approval,action_commit=self.head())
        record['pending_action']='this-action'
        with self.assertRaises(CycleError):m.validate_schema(record,'policy')

    def test_bootstrap_partial_identity_and_path_containment(self):
        for field,value in (('path','relocated.txt'),('sha256','0'*64)):
            modified=copy.deepcopy(self.package);modified['record'][field]=value
            self.write('relocated.txt','Keep existing approvals.\n');self.write(self.package_path,modified)
            with self.assertRaises(CycleError):m.validate_package(self.root,self.package_path)
        self.write(self.package_path,self.package)
        self.package['initial']=False;self.write(self.package_path,self.package)
        with self.assertRaisesRegex(CycleError,'bootstrap'):m.validate_package(self.root,self.package_path)
        for path in ('../record.txt','/tmp/nope'):
            with self.assertRaises(CycleError):m.read(self.root,path)
        (self.root/'link').symlink_to(self.root/'record.txt')
        with self.assertRaises(CycleError):m.read(self.root,'link')


class ReadinessInventoryAndStandingTests(MigrationFixture):
    def test_unrelated_verified_source_does_not_establish_u1_readiness(self):
        unrelated=copy.deepcopy(self.readiness)
        unrelated['sources']=[self.bind('proof/source.py')]
        with self.assertRaisesRegex(CycleError,'implementation inventory'):
            m.validate_readiness(self.root,unrelated)

    def test_retired_rule_cannot_supply_current_source_or_successor(self):
        from decision_policy import frontmatter
        original=self.docs/self.subject
        rule=frontmatter(original.read_text())[0]['governs'][0]
        self.write('bionic/adrs/ADR-0002-retirement.md',
            '---\nid: ADR-0002\nstatus: Accepted\ngoverns:\n- handle: ADR-0002/replacement\n  rule: Use the replacement.\n  domain: migration\n  scope: adrs\n  provenance: authored\n  retires: ['+rule['handle']+']\n---\n# Decision\n')
        with self.assertRaisesRegex(CycleError,'current governing'):
            m.validate_package(self.root,self.package_path)

    def test_stale_policy_instruction_cannot_authorize_new_switch(self):
        config='config_version: "1"\ndocs_dir: bionic\nadr:\n  acceptance: council-only\n'
        self.write('.bionic.yml',config)
        owner=dict(self.owner,action='change-policy',presented=self.bind('.bionic.yml'))
        m.record_policy(self.root,'policy-one','council-only',owner);self.commit('Approved council-only')
        self.assertEqual(m.policy_at(self.root,self.head()),'council-only')
        self.write('.bionic.yml','config_version: "1"\ndocs_dir: bionic\n');self.commit('Return to human')
        self.write('.bionic.yml',config);self.commit('Unapproved new switch')
        with self.assertRaisesRegex(CycleError,'latest policy change'):
            m.policy_at(self.root,self.head())

    def test_readiness_requires_the_new_package_policy_writer_dependency(self):
        readiness=copy.deepcopy(self.readiness)
        readiness['sources']=[s for s in readiness['sources'] if s['path']!='crux/scripts/decision_policy.py']
        with self.assertRaisesRegex(CycleError,'implementation inventory'):
            m.validate_readiness(self.root,readiness)


class EarlySourceAndInstalledSupportTests(MigrationFixture):
    def test_real_package_approval_before_acceptance_preserves_exact_package(self):
        # Re-establish the genuine Proposed state before the explicit package
        # instruction. The future acceptance receipt does not exist at this point.
        (self.docs/self.subject).write_bytes(self.proposed)
        (self.docs/'adrs/acceptances/ADR-0001.json').unlink()
        self.package['governing_adr']['source']['sha256']=digest(self.proposed)
        self.package['items'][0]['source']['sha256']=digest(self.proposed)
        self.write(self.package_path,self.package)
        self.commit('Proposed exact package before owner instruction')
        before=(self.root/self.package_path).read_bytes()
        owner=dict(self.owner,action='accept-adr-and-approve-dispositions',presented=self.bind(self.package_path))
        instructions=m.package_owner_instructions(self.root,self.package_path,owner)
        self.assertNotEqual(instructions['acceptance']['action'],instructions['disposition']['action'])
        receipt=m.accept_package(self.root,self.package_path,'adrs/councils/adr.json',owner=owner)
        m.validate_package_acceptance(self.root,self.package_path,committed=False)
        self.commit('Accept exact early package')
        self.assertEqual(before,(self.root/self.package_path).read_bytes())
        m.validate_package(self.root,self.package_path)
        vote=self.council(self.package_path.removeprefix('bionic/'),digest(before));vote['readiness']=self.readiness
        vote['review_bundle_sha256']=digest(encoded(m.review_bundle(self.root,self.package_path)));self.seal(vote)
        path='bionic/adrs/councils/early-source.json';self.write(path,vote);self.commit('Post-acceptance disposition council')
        approval=m.record_approval(self.root,'early-source',self.package_path,path,self.readiness,owner=instructions['disposition'])
        self.assertEqual(approval['owner']['at'],owner['at']);self.assertEqual(approval['owner']['quote'],owner['quote'])
        self.assertEqual(receipt['format'],'crux.adr-acceptance');self.assertEqual(approval['format'],m.FORMATS['approval'])

    def test_later_consumer_uses_installed_support_without_vendoring_or_upstream_ancestry(self):
        import shutil
        shutil.rmtree(self.root/'crux')
        self.write('later-record.txt','A later independent record.\n')
        self.package['record']=self.bind('later-record.txt');self.package['initial']=False
        self.write(self.package_path,self.package)
        support=m.installed_support();m.validate_readiness(self.root,support,initial=False)
        self.assertFalse((self.root/'crux').exists())
        with self.assertRaisesRegex(CycleError,'initial bootstrap'):m.validate_readiness(self.root,support,initial=True)
        vote=self.council(self.package_path.removeprefix('bionic/'),digest(encoded(self.package)));vote['readiness']=support
        vote['review_bundle_sha256']=digest(encoded(m.review_bundle(self.root,self.package_path)));self.seal(vote)
        owner=dict(self.owner,presented=self.bind(self.package_path))
        m.validate_evidence(self.root,self.package_path,vote,readiness=support,initial=False,policy='council-only',owner=None)
        invalid=copy.deepcopy(support);invalid['sha256']='0'*64
        with self.assertRaises(CycleError):m.validate_readiness(self.root,invalid,initial=False)
        # A historical byte pin keeps its own reader.
        invalid=legacy_v1_support();invalid['sources'][0]['sha256']='0'*64
        with self.assertRaises(CycleError):m.validate_readiness(self.root,invalid,initial=False)

    def test_council_proof_binding_detects_changed_receipt_with_same_owner_package(self):
        receipt_path=self.package['governing_adr']['receipt']
        receipt=json.loads((self.root/receipt_path).read_text());receipt['human_approval']='Different exact receipt bytes'
        self.write(receipt_path,receipt)
        # The permitted lifecycle mapping still holds; old council proof does not.
        m.validate_package(self.root,self.package_path)
        with self.assertRaisesRegex(CycleError,'proof inputs changed'):self.evidence()

class FinalBoundaryTests(MigrationFixture):
    def test_queue_stop_resume_clearance_never_approves_and_unrelated_progresses(self):
        items=[{'id':name,'bindings':[],'depends_on':deps,'revision':1,'status':'done','evidence':[]} for name,deps in (('a',[]),('b',['a']),('c',[]))]
        m.create_queue(self.root,'stop-queue',items);path='bionic/adrs/migrations/queues/stop-queue.json'
        stop={'id':'stop-one','items':['a'],'instruction':dict(self.owner,action='stop'),'resolution':None}
        stopped=m.queue_stop(self.root,path,stop)
        self.assertEqual([i['status'] for i in stopped['items']],['blocked','blocked','done'])
        before=(self.root/path).read_bytes();m.resume_queue(self.root,path);self.assertEqual(before,(self.root/path).read_bytes())
        for origin in ('council','repository','model'):
            with self.assertRaises(CycleError):m.clear_queue_stop(self.root,path,'stop-one',dict(self.owner,action='clear-stop',origin=origin))
        cleared=m.clear_queue_stop(self.root,path,'stop-one',dict(self.owner,action='clear-stop'))
        self.assertEqual([i['status'] for i in cleared['items']],['pending','pending','done'])
        self.assertTrue(cleared['owner_stops'][0]['resolution']);self.assertEqual(cleared['items'][0]['evidence'],[])

    def test_closed_schemas_and_historical_payload_no_fallback(self):
        for kind in m.FORMATS:
            with self.subTest(kind=kind),self.assertRaises(CycleError):m.validate_schema({'format_version':'2'},kind)
        for change in ({'items':[{}]},{'items':'bad'},{'extra':True},{'format':'crux.adr-migration-package.v2'}):
            package=copy.deepcopy(self.package);package.update(change);self.write(self.package_path,package)
            with self.assertRaises(CycleError):m.validate_package(self.root,self.package_path)
        self.write(self.package_path,self.package)
        facts=m.candidate_facts(self.root,self.package_path)
        handle=self.package['items'][0]['handle']
        self.assertEqual(facts['projection']['historical_handles'][handle]['replacements'],[])
        self.assertEqual(facts['origins'][handle]['origin'],'prospective-candidate')
        self.assertEqual(facts['authority'],'none')

    def test_typed_or_outside_tree_markdown_is_no_architectural_source(self):
        original=(self.docs/self.subject).read_text()
        for relative,text in (('outside.md',original),('bionic/adrs/ADR-0002-wrong.md',original),('bionic/adrs/ADR-0001-typed.md',original.replace('id: ADR-0001','record_type: implementation-decision\nid: ADR-0001'))):
            self.write(relative,text)
            item=copy.deepcopy(self.package['items'][0]);item['source']=self.bind(relative)
            with self.assertRaises(CycleError):m._clause(self.root,item,self.package,m._governing(self.root,self.package))
            (self.root/relative).unlink()


    def test_stop_then_source_drift_then_clear_persists_invalidation(self):
        items=[{'id':name,'bindings':[self.bind('record.txt')] if name=='a' else [],'depends_on':deps,
                'revision':1,'status':'done','evidence':[]} for name,deps in (('a',[]),('b',['a']),('c',[]))]
        m.create_queue(self.root,'drift-stop',items);path='bionic/adrs/migrations/queues/drift-stop.json'
        stop={'id':'stop-one','items':['a'],'instruction':dict(self.owner,action='stop'),'resolution':None}
        m.queue_stop(self.root,path,stop)
        self.write('record.txt','Changed while owner stop was outstanding.\n')
        resumed=m.clear_queue_stop(self.root,path,'stop-one',dict(self.owner,action='clear-stop'))
        self.assertEqual([i['status'] for i in resumed['items']],['invalidated','invalidated','done'])
        self.assertEqual(m.load_queue(self.root,path),resumed)
        self.assertEqual(resumed['items'][2],items[2])


class EffectiveStandingTests(MigrationFixture):
    def test_unpromoted_material_edits_do_not_supply_binding_current_wording(self):
        handle=self.package['items'][0]['handle']
        with patch('summaries_projection.provenance_standing',return_value={handle:{'standing':'binding','in_run_edit':['rule'],'binding_rule':'Older binding wording.'}}):
            self.assertNotIn(handle,m.current_standing(self.root))

    def test_external_effective_amender_requires_exact_material_binding(self):
        handle=self.package['items'][0]['handle']
        path='bionic/adrs/ADR-0002-amender.md'
        self.write(path,'---\nid: ADR-0002\nstatus: Accepted\ngoverns: []\n---\n# Decision\nNarrow the scope.\n')
        with patch.object(m,'current_standing',return_value={handle:{'amended_by':['ADR-0002/narrow-scope']}}):
            with self.assertRaisesRegex(CycleError,'amender source'):m.validate_package(self.root,self.package_path)
            self.package['dependencies'].append(dict(self.bind(path),kind='source'));self.write(self.package_path,self.package)
            m.validate_package(self.root,self.package_path)
            self.write(path,'Changed amender source')
            with self.assertRaises(CycleError):m.validate_package(self.root,self.package_path)


class PackageAcceptancePolicyTests(MigrationFixture):
    def proposed_package(self):
        (self.docs/self.subject).write_bytes(self.proposed)
        (self.docs/'adrs/acceptances/ADR-0001.json').unlink()
        self.package['governing_adr']['source']['sha256']=digest(self.proposed)
        self.package['items'][0]['source']['sha256']=digest(self.proposed)
        self.write(self.package_path,self.package)
        self.commit('New Proposed package before acceptance')
        return dict(self.owner,action='accept-adr-and-approve-dispositions',presented=self.bind(self.package_path))

    def test_same_action_weaker_config_cannot_replace_parent_human_policy(self):
        owner=self.proposed_package()
        self.write('.bionic.yml','config_version: "1"\ndocs_dir: bionic\nadr:\n  acceptance: council-only\n')
        with self.assertRaisesRegex(CycleError,'owner package acceptance'):
            m.accept_package(self.root,self.package_path,'adrs/councils/adr.json')
        receipt=m.accept_package(self.root,self.package_path,'adrs/councils/adr.json',owner=owner)
        self.assertEqual(receipt['policy'],'council-and-human')
        # The exact package's owner instruction exists before acceptance and is
        # preserved while acceptance and disposition remain distinct records.
        self.assertEqual(receipt['migration_owner'],owner)
        self.assertEqual(receipt['migration_package'],self.bind(self.package_path))

    def test_previously_owner_selected_council_only_accepts_without_owner(self):
        self.write('.bionic.yml','config_version: "1"\ndocs_dir: bionic\nadr:\n  acceptance: council-only\n')
        instruction=dict(self.owner,action='change-policy',presented=self.bind('.bionic.yml'))
        m.record_policy(self.root,'package-policy','council-only',instruction);self.commit('Owner chooses council-only before action')
        self.proposed_package()
        receipt=m.accept_package(self.root,self.package_path,'adrs/councils/adr.json')
        self.assertEqual(receipt['policy'],'council-only')
        m.validate_package_acceptance(self.root,self.package_path,committed=False)
        self.commit('Package acceptance under earlier policy')
        self.assertEqual(m.validate_package_acceptance(self.root,self.package_path),receipt)
        # Package policy recorded in its own action commit is never its parent.
        with self.assertRaisesRegex(CycleError,'before its action'):
            m.validate_package_acceptance_data(self.root,dict(receipt,policy_basis=self.head()))


if __name__=='__main__':unittest.main()


class InvocationReuseTests(MigrationFixture):
    def test_one_record_action_validates_its_package_once(self):
        with patch.object(m,'validate_package',wraps=m.validate_package) as validate:
            m.record_approval(self.root,'once',self.package_path,self.council_path,self.readiness,owner=self.owner)
        self.assertEqual(validate.call_count,1)

    def test_public_approval_calls_are_fresh_and_changed_inputs_refuse(self):
        m.record_approval(self.root,'fresh',self.package_path,self.council_path,self.readiness,owner=self.owner)
        approval='bionic/adrs/migrations/approvals/fresh.json';self.commit('Committed approval')
        with patch.object(m,'validate_package',wraps=m.validate_package) as validate:
            m.validate_approval(self.root,approval);m.validate_approval(self.root,approval)
        self.assertEqual(validate.call_count,2)
        for name in (self.package_path,'bionic/'+self.subject,self.council_path,'bionic/adrs/acceptances/ADR-0001.json'):
            path=self.root/name;raw=path.read_bytes()
            try:
                path.write_bytes(raw+b'changed input')
                with self.subTest(input=name),self.assertRaises((CycleError,ValueError)):
                    m.validate_approval(self.root,approval)
            finally:path.write_bytes(raw)
        self.assertEqual(m.validate_approval(self.root,approval)['id'],'fresh')

    def test_public_bundle_and_evidence_actions_do_not_share_reuse(self):
        with patch.object(m,'validate_package',wraps=m.validate_package) as validate:
            m.review_bundle(self.root,self.package_path);m.review_bundle(self.root,self.package_path)
        self.assertEqual(validate.call_count,2)
        with patch.object(m,'validate_package',wraps=m.validate_package) as validate:
            self.evidence();self.evidence()
        self.assertEqual(validate.call_count,2)


def legacy_v1_support():
    """The installed-support v1 basis as the v5.3.0 writer built it: a byte pin."""
    plugin=Path(m.__file__).resolve().parent.parent
    return {'format':m.INSTALLED_SUPPORT_V1,'sources':[
        {'path':name.removeprefix('crux/'),'sha256':digest((plugin/name.removeprefix('crux/')).read_bytes())}
        for name in m.INSTALLED_INVENTORY]}


class IssuedInstalledSupportTests(MigrationFixture):
    def drifted(self):
        # A recorded v1 basis whose first inventory file has since changed.
        basis=legacy_v1_support();basis['sources'][0]['sha256']='0'*64
        return basis

    def test_listed_v1_basis_is_accepted_through_the_issued_route_after_bytes_change(self):
        basis=self.drifted()
        with self.assertRaisesRegex(CycleError,'installed support source changed'):
            m.validate_readiness(self.root,basis,initial=False)
        with patch.object(m,'ISSUED_INSTALLED_SUPPORT',frozenset({digest(encoded(basis))})):
            self.assertEqual(m.validate_readiness(self.root,basis,initial=False,with_route=True),(basis,'issued'))
            # The default return value is unchanged: the readiness object alone.
            self.assertEqual(m.validate_readiness(self.root,basis,initial=False),basis)
            with self.assertRaisesRegex(CycleError,'initial bootstrap'):
                m.validate_readiness(self.root,basis,initial=True)
            extra=dict(basis,profile='1')
            with self.assertRaisesRegex(CycleError,'invalid installed support basis'):
                m.validate_readiness(self.root,extra,initial=False)

    def test_unlisted_byte_equal_v1_basis_keeps_the_byte_route(self):
        basis=legacy_v1_support()
        self.assertNotIn(digest(encoded(basis)),m.ISSUED_INSTALLED_SUPPORT)
        self.assertEqual(m.validate_readiness(self.root,basis,initial=False,with_route=True),(basis,'byte'))
        self.assertEqual(m.validate_readiness(self.root,self.readiness,with_route=True),(self.readiness,'committed'))

    def test_issued_list_equals_the_v1_bases_of_committed_approvals(self):
        from _dev_surface import REPO_ROOT, TREE, require_dev_surface
        approvals=REPO_ROOT/TREE/'adrs/migrations/approvals'
        require_dev_surface(self,approvals,f'{TREE}/adrs/migrations/approvals')
        bases={}
        for path in sorted(approvals.glob('*.json')):
            readiness=json.loads(path.read_text())['readiness']
            if readiness.get('format')==m.INSTALLED_SUPPORT_V1:
                bases[path.name]=readiness
        self.assertEqual(m.ISSUED_INSTALLED_SUPPORT,{digest(encoded(r)) for r in bases.values()})
        self.assertEqual(list(bases),['authority-reset-2026-11.json'])
        readiness=bases['authority-reset-2026-11.json']
        self.assertEqual(m.validate_readiness(REPO_ROOT,readiness,initial=False,with_route=True)[1],'issued')


def _cli():
    spec=importlib.util.spec_from_file_location('adr_migration_cli_profile',Path(__file__).resolve().parents[1]/'adr-migration.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    return cli


def schema_levels(schema):
    """Every object level of a migration schema, as an approval profile declares it."""
    levels={}
    def visit(node,key):
        types=node.get('type');types=[types] if isinstance(types,str) else list(types or [])
        if 'object' in types and 'properties' in node:
            levels[key]={'fields':sorted(node['properties']),'required':sorted(node.get('required',[])),
                         'nullable':'null' in types}
            for name,sub in node['properties'].items():
                # The approval's readiness is a leaf; its if/then/else lies inside it.
                if key=='' and name=='readiness':continue
                visit(sub,f'{key}.{name}' if key else name)
        elif 'array' in types and 'items' in node:
            visit(node['items'],key+'[]')
    visit(schema,'')
    return levels


class ApprovalProfileTests(MigrationFixture):
    COUNCIL='bionic/adrs/councils/later.json'
    APPROVAL='bionic/adrs/migrations/approvals/later.json'

    @contextlib.contextmanager
    def patched_schema(self,kind,change):
        """Admit a record shape in the schema so the profile leg, not the schema, refuses."""
        vp=m._validator();original=vp.load_schema
        def load(path):
            schema=original(path)
            if Path(path).name==f'adr-migration-{kind}.schema.json':
                schema=copy.deepcopy(schema);change(schema)
            return schema
        with patch.object(vp,'load_schema',side_effect=load):yield

    def later(self,change=None,readiness=None):
        """A later, non-initial package and its committed council on an installed basis."""
        self.write('later-record.txt','A later independent record.\n')
        self.package['record']=self.bind('later-record.txt');self.package['initial']=False
        if change:change(self.package)
        self.write(self.package_path,self.package)
        self.owner['presented']=self.bind(self.package_path)
        readiness=readiness or m.installed_support()
        vote=self.council(self.package_path.removeprefix('bionic/'),self.bind(self.package_path)['sha256']);vote['readiness']=readiness
        vote['review_bundle_sha256']=digest(encoded(m.review_bundle(self.root,self.package_path)));self.seal(vote)
        self.write(self.COUNCIL,vote);self.commit('Later council on installed support')
        return readiness

    def approve(self,readiness,owner=None):
        """Run the adr-migration.py approve entry point; return its exit code and JSON."""
        self.write('readiness.json',readiness);self.write('owner.json',owner or self.owner)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code=_cli().main(['approve','--repo-root',str(self.root),'--id','later','--package',self.package_path,
                '--council',self.COUNCIL,'--readiness',str(self.root/'readiness.json'),'--owner',str(self.root/'owner.json')])
        return code,json.loads(out.getvalue())

    def test_profile_one_names_every_object_level_of_both_schemas_at_the_cycle_base(self):
        from _dev_surface import REPO_ROOT, TREE, require_dev_surface
        require_dev_surface(self,REPO_ROOT/TREE/'adrs/migrations/approvals',f'{TREE}/adrs/migrations/approvals')
        for kind in ('package','approval'):
            raw=subprocess.run(['git','-C',str(REPO_ROOT),'show',f'fb675e557:crux/schemas/adr-migration-{kind}.schema.json'],
                capture_output=True)
            self.assertEqual(raw.returncode,0,raw.stderr.decode())
            with self.subTest(kind=kind):
                self.assertEqual(m.APPROVAL_PROFILES['1'][kind],schema_levels(json.loads(raw.stdout)))
        top=m.APPROVAL_PROFILES['1']['approval']['']
        self.assertIn('readiness',top['fields']);self.assertIn('readiness',top['required'])
        self.assertFalse(any(level.startswith('readiness') for level in m.APPROVAL_PROFILES['1']['approval']))

    def test_profile_digest_is_pinned_and_an_edited_profile_refuses(self):
        self.assertEqual(m.APPROVAL_PROFILE_DIGESTS,{'1':'8143c7f20a1428d52911afaf8a7f2429b4ab1fe1713dfb5b722f1c6b388fc4a2'})
        self.assertEqual(m.CURRENT_APPROVAL_PROFILE,'1')
        edited=copy.deepcopy(m.APPROVAL_PROFILES['1']);edited['package']['record']['fields'].append('note')
        with patch.dict(m.APPROVAL_PROFILES,{'1':edited}):
            with self.assertRaisesRegex(CycleError,r'approval profile 1 changed; issue a new profile'):
                m.validate_readiness(self.root,{'format':m.INSTALLED_SUPPORT_V2,'profile':'1','sha256':m.APPROVAL_PROFILE_DIGESTS['1']},initial=False)
            with self.assertRaisesRegex(CycleError,'approval profile 1 changed'):m.installed_support()

    def test_v2_basis_is_accepted_only_through_its_pinned_digest(self):
        support=m.installed_support()
        self.assertEqual(support,{'format':m.INSTALLED_SUPPORT_V2,'profile':'1','sha256':m.APPROVAL_PROFILE_DIGESTS['1']})
        self.assertEqual(m.validate_readiness(self.root,support,initial=False,with_route=True),(support,'profile'))
        for label,value,message in (('unknown profile',dict(support,profile='2'),'unsupported approval profile'),
                ('other digest',dict(support,sha256='0'*64),'profile digest'),
                ('extra key',dict(support,sources=[]),'invalid installed support basis')):
            with self.subTest(label),self.assertRaisesRegex(CycleError,message):
                m.validate_readiness(self.root,value,initial=False)
        with self.assertRaisesRegex(CycleError,'initial bootstrap'):m.validate_readiness(self.root,support,initial=True)
        m.validate_schema({'format':m.FORMATS['approval'],'id':'x','package':self.bind(self.package_path),'council':self.bind(self.council_path),
            'readiness':support,'policy':'council-only','policy_basis':self.head(),'owner':None,'at':'2026-11-07T00:00:00Z',
            'review_bundle_sha256':'0'*64},'approval')

    def test_conforming_package_is_approved_on_a_v2_basis(self):
        readiness=self.later()
        code,result=self.approve(readiness)
        self.assertEqual(code,0,result);self.assertEqual(result['readiness'],readiness)
        self.commit('Approval on installed support v2')
        self.assertEqual(m.validate_approval(self.root,self.APPROVAL)['readiness'],readiness)
        # A null owner is a nullable level the profile skips.
        self.assertIs(m.check_profile('approval',dict(result,owner=None),'1')['owner'],None)

    def test_conforming_package_still_approves_when_the_schema_adds_an_unused_optional_field(self):
        def optional(schema):schema['properties']['items']['items']['properties']['note']={'type':'string'}
        with self.patched_schema('package',optional):
            readiness=self.later()
            code,result=self.approve(readiness)
        self.assertEqual(code,0,result)

    def test_package_field_the_profile_does_not_name_refuses_with_its_path_and_profile(self):
        def optional(schema):schema['properties']['items']['items']['properties']['note']={'type':'string'}
        def carry(package):package['items'][0]['note']='A field a later schema admits.'
        with self.patched_schema('package',optional):
            readiness=self.later(carry)
            code,result=self.approve(readiness)
        self.assertEqual(code,1)
        self.assertEqual(result['error'],'approval profile 1 does not name package field items[0].note')
        self.assertFalse((self.root/self.APPROVAL).exists())

    def test_package_missing_a_profile_required_nested_field_refuses(self):
        def relax(schema):schema['properties']['items']['items']['required'].remove('original_rationale')
        def drop(package):del package['items'][0]['original_rationale']
        with self.patched_schema('package',relax):
            readiness=self.later(drop)
            with self.assertRaisesRegex(CycleError,r'^approval profile 1 requires package field items\[0\]\.original_rationale$'):
                m.record_approval(self.root,'later',self.package_path,self.COUNCIL,readiness,owner=self.owner)
        self.assertFalse((self.root/self.APPROVAL).exists())

    def test_approval_nested_field_the_profile_does_not_name_refuses(self):
        def admit(schema):schema['properties']['owner']['properties']['presented']['properties']['note']={'type':'string'}
        readiness=self.later()
        owner=copy.deepcopy(self.owner);owner['presented']['note']='An extra presented field.'
        with self.patched_schema('approval',admit):
            code,result=self.approve(readiness,owner=owner)
        self.assertEqual(code,1)
        self.assertEqual(result['error'],'approval profile 1 does not name approval field owner.presented.note')
        self.assertFalse((self.root/self.APPROVAL).exists())

    def test_basis_named_profile_refuses_a_field_only_a_later_current_profile_names(self):
        readiness=self.later()
        second=copy.deepcopy(m.APPROVAL_PROFILES['1']);second['package']['items[]']['fields']=sorted([*second['package']['items[]']['fields'],'note'])
        pins=dict(m.APPROVAL_PROFILE_DIGESTS,**{'2':digest(encoded(second))})
        def optional(schema):schema['properties']['items']['items']['properties']['note']={'type':'string'}
        def carry(package):package['items'][0]['note']='A field only profile 2 names.'
        with self.patched_schema('package',optional):
            readiness=self.later(carry,readiness=readiness)
            with patch.dict(m.APPROVAL_PROFILES,{'2':second}),patch.object(m,'APPROVAL_PROFILE_DIGESTS',pins),\
                    patch.object(m,'CURRENT_APPROVAL_PROFILE','2'):
                code,result=self.approve(readiness)
        self.assertEqual(readiness['profile'],'1')
        self.assertEqual(code,1)
        self.assertEqual(result['error'],'approval profile 1 does not name package field items[0].note')
        self.assertFalse((self.root/self.APPROVAL).exists())

    def test_new_approval_refuses_an_installed_support_v1_basis_including_an_issued_one(self):
        legacy=legacy_v1_support()
        readiness=self.later(readiness=legacy)
        for label,issued in (('byte-equal',frozenset()),('issued',frozenset({digest(encoded(legacy))}))):
            with self.subTest(label),patch.object(m,'ISSUED_INSTALLED_SUPPORT',issued):
                code,result=self.approve(readiness)
                self.assertEqual((code,result['error']),(1,'new approvals bind installed support v2'))
        self.assertFalse((self.root/self.APPROVAL).exists())

    def test_rerunning_approve_for_a_recorded_v1_approval_returns_it_unchanged(self):
        legacy=legacy_v1_support()
        readiness=self.later(readiness=legacy)
        # Record the approval as the v5.3.0 writer did, before v1 refusal existed.
        with patch.object(m,'_new_approval_basis'):
            recorded=m.record_approval(self.root,'later',self.package_path,self.COUNCIL,readiness,owner=self.owner)
        self.commit('Approval recorded on installed support v1')
        before=(self.root/self.APPROVAL).read_bytes()
        code,result=self.approve(readiness)
        self.assertEqual((code,result),(0,recorded))
        self.assertEqual(before,(self.root/self.APPROVAL).read_bytes())

    def test_readiness_command_output_is_unchanged(self):
        for readiness,initial in ((self.readiness,True),(m.installed_support(),False)):
            self.write('readiness.json',readiness)
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code=_cli().main(['readiness','--repo-root',str(self.root),'--readiness',str(self.root/'readiness.json')])
            if initial:self.assertEqual((code,json.loads(out.getvalue())),(0,self.readiness))
            else:self.assertEqual((code,json.loads(out.getvalue())['error']),(1,'initial bootstrap requires committed U1 readiness'))
