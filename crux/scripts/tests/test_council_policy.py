"""Mode policy, typed dissent and historical/default authorization controls."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import CycleError,digest,encoded
import bionic_config


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'bionic').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.write('config_version: "1"\ndocs_dir: bionic\n')
    def write(self,text): (self.root/'.bionic.yml').write_text(text)
    def test_legacy_and_override_limits(self):
        self.assertEqual(bionic_config.load_council_policy(self.root)['mode'],'strict')
        self.write('config_version: "1"\ndocs_dir: bionic\ncouncil:\n  mode: standard\n  overrides:\n    idr: lite\n  max_attempts: 2\n')
        from council_policy import resolve
        # A hand-edited reduction alone is not permission.
        with self.assertRaisesRegex(CycleError,'authoriz|initial'):
            resolve(self.root,'idr')
        policy=bionic_config.load_council_policy(self.root)
        self.assertEqual(policy['overrides'],{'idr':'lite'});self.assertEqual(policy['max_attempts'],2)
        for value in (0,8,True,'2'):
            with self.subTest(value=value),self.assertRaises(bionic_config.BionicConfigError):
                bionic_config.validate_council_policy({'council':{'max_attempts':value}})
        for value in ('easy',None,{},True):
            with self.subTest(value=value),self.assertRaises(bionic_config.BionicConfigError):
                bionic_config.validate_council_policy({'council':{'mode':value}})
    def test_explicit_initializer_and_frozen_policy_changes(self):
        from council_policy import initialize,resolve
        initialize(self.root,'lite',selection='Explicit setup choice: Lite')
        first=resolve(self.root,'idr')
        self.assertEqual(first['mode'],'lite');self.assertEqual(first['human_policy'],'council-and-human')
        self.write((self.root/'.bionic.yml').read_text().replace('lite','standard'))
        with self.assertRaisesRegex(CycleError,'authoriz'):
            resolve(self.root,'idr',previous=first)
    def test_existing_committed_config_cannot_authorize_itself(self):
        from council_policy import resolve
        for args in (('init','-q'),('config','user.email','test@example.invalid'),('config','user.name','Test'),('add','.'),('commit','-qm','Legacy project')):
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        self.write((self.root/'.bionic.yml').read_text()+'council:\n  mode: standard\n')
        with self.assertRaisesRegex(CycleError,'authoriz'):resolve(self.root,'adr')
        self.assertFalse(list(self.root.rglob('attempt-*.json')))
    def test_apex_level_does_not_use_reviewer_override(self):
        from models_catalog import load
        catalog=load();apex=catalog.resolve_level('apex')
        self.assertEqual(apex.codex,catalog.levels['apex'].codex)
        self.assertNotEqual(apex.codex,catalog.resolve('reviewer').codex)


class EvaluatorTests(unittest.TestCase):
    def row(self,mode='standard'):
        return {'policy':{'mode':mode},'subject_sha256':'a'*64,
            'seats':[{'provider':p,'decision':'APPROVE','errored':False,'findings':[]} for p in ('a','b','c')],
            'architect':{'agrees':True,'subject_sha256':'a'*64,'rationale':'Proceed after checking obligations.','dissent':[]},'binding_failures':[]}
    def test_three_thresholds_and_exact_architect(self):
        from council_policy import evaluate
        row=self.row();row['seats'][2].update(decision='REQUEST_CHANGES',findings=[{'kind':'blocking','id':'F1'}])
        row['architect']['dissent']=[{'provider':'c','kind':'accepted-tradeoff','explanation':'A non-binding presentation preference.'}]
        self.assertEqual(evaluate(row),'approved')
        row['policy']['mode']='strict';self.assertEqual(evaluate(row),'changes-required')
        row['policy']['mode']='standard';row['architect']['subject_sha256']='b'*64
        self.assertEqual(evaluate(row),'changes-required')
    def test_dissent_requires_typed_evidence_and_unresolved_safety_blocks(self):
        from council_policy import evaluate
        row=self.row();row['seats'][2]['decision']='REQUEST_CHANGES'
        for disposition in ({'provider':'c','kind':'refuted','explanation':'Just trust me'},
                            {'provider':'c','kind':'accepted-tradeoff'},
                            {'provider':'c','kind':'unresolved-safety','explanation':'Need a targeted check'},
                            {'provider':'c','kind':'unsupported','explanation':'No'}):
            row['architect']['dissent']=[disposition]
            with self.subTest(disposition=disposition):self.assertEqual(evaluate(row),'changes-required')
        text='Check output: named assertion passed.'
        row['architect']['dissent']=[{'provider':'c','kind':'refuted','explanation':'The named check refutes it.',
            'evidence':{'path':'evidence/check.txt','sha256':digest(text.encode())},'evidence_text':text}]
        self.assertEqual(evaluate(row),'approved')
        row['binding_failures']=['missing required authorization'];self.assertEqual(evaluate(row),'changes-required')
    def test_missing_errored_votes_never_approve(self):
        from council_policy import evaluate
        for mode in ('standard','strict'):
            row=self.row(mode);row['seats'][0]['errored']=True;row['seats'][1]['decision']=None
            self.assertEqual(evaluate(row),'changes-required')
        row=self.row('strict');row['seats'][0]['decision']='APPROVE_WITH_NITS'
        self.assertEqual(evaluate(row),'approved')
    def test_lite_challenge_never_approves_and_failed_final_fails(self):
        from council_policy import evaluate
        row=self.row('lite');row['seats']=[];row['passes']=[{'pass':'challenge','status':'closed','vote':{'decision':'APPROVE','errored':False}}]
        self.assertEqual(evaluate(row),'changes-required')
        row['passes'].append({'pass':'final','status':'closed','subject_sha256':'a'*64,'vote':{'decision':'APPROVE_WITH_NITS','errored':False}})
        self.assertEqual(evaluate(row),'approved')
        row['passes'][1]['vote']['errored']=True;self.assertEqual(evaluate(row),'changes-required')


class AdditionalPolicyControls(unittest.TestCase):
    setUp=PolicyTests.setUp
    write=PolicyTests.write
    def test_first_crux_enrollment_in_existing_code_repository(self):
        from council_policy import initialize,resolve
        (self.root/'source.py').write_text('answer = 42\n')
        for args in (('init','-q'),('config','user.email','test@example.invalid'),('config','user.name','Test'),('add','source.py'),('commit','-qm','Existing code')):
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        initialized=initialize(self.root,'standard',selection='New Crux setup default Standard')
        self.assertTrue(initialized['basis']);self.assertEqual(resolve(self.root,'adr')['mode'],'standard')
    def test_mode_only_owner_instruction_does_not_authorize_override(self):
        from council_policy import record_policy
        for args in (('init','-q'),('config','user.email','test@example.invalid'),('config','user.name','Test'),('add','.'),('commit','-qm','Legacy Crux')):
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        self.write((self.root/'.bionic.yml').read_text()+'council:\n  mode: standard\n  overrides:\n    idr: lite\n')
        owner={'origin':'owner-conversation','quote':'Choose Standard','conversation':'test/message',
               'approved_actions':[{'action':'select-council-mode','value':'standard'}]}
        (self.root/'owner.json').write_text(json.dumps(owner))
        with self.assertRaisesRegex(CycleError,'override'):
            record_policy(self.root,'must-refuse','owner.json')

    def test_extension_retained_across_subsequent_attempt_resolution(self):
        from council_policy import record_policy,resolve
        for args in (('init','-q'),('config','user.email','test@example.invalid'),('config','user.name','Test'),('add','.'),('commit','-qm','Existing Crux')):
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        owner={'origin':'owner-conversation','quote':'Extend this decision to nine attempts','conversation':'test/message',
               'action':'extend-council-limit','limit':9}
        (self.root/'owner.json').write_text(json.dumps(owner))
        record_policy(self.root,'extended-limit','owner.json',action='extend-council-limit',logical_id='consultation:test',limit=9)
        first=resolve(self.root,'consultation',logical_id='consultation:test',extension=9)
        self.assertEqual(first['max_attempts'],9)
        second=resolve(self.root,'consultation',previous=first,logical_id='consultation:test')
        self.assertEqual(second['max_attempts'],9)

    def test_unrelated_config_commit_cannot_hide_unauthorized_policy_transition(self):
        from council_policy import resolve
        def commit(message):
            for args in (('add','.'),('commit','-qm',message)):
                subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        for args in (('init','-q'),('config','user.email','test@example.invalid'),('config','user.name','Test')):
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        commit('Legacy Strict')
        self.write((self.root/'.bionic.yml').read_text()+'council:\n  mode: standard\n');commit('Unapproved reduction')
        self.write((self.root/'.bionic.yml').read_text()+'# unrelated comment\n');commit('Unrelated config edit')
        with self.assertRaisesRegex(CycleError,'authoriz'):resolve(self.root,'adr')


class AdditionalEvaluatorControls(unittest.TestCase):
    row=EvaluatorTests.row
    def test_provider_error_is_failed_attempt_even_with_two_approvals(self):
        from council_policy import evaluate
        row=self.row();row['seats'][2].update(decision=None,errored=True)
        row['architect']['dissent']=[{'provider':'c','kind':'accepted-tradeoff','explanation':'Provider unavailable'}]
        self.assertEqual(evaluate(row),'changes-required')
