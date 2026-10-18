"""The one frozen initial exception; ordinary policy stays unchanged.

Readiness existence is a separate committed checkpoint owned by integration.
These controls inspect the real frozen package/council and isolate that boundary
so they never manufacture a ready checkpoint or an actual owner approval.
"""
import copy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import adr_migration as m
import summaries_projection as sp
from cycle_workflow import CycleError,encoded,digest

REPO=Path(__file__).resolve().parents[3]
EXCEPTION='bionic/adrs/migrations/exceptions/adr-0160-initial-owner-override.json'


class InitialExceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (REPO/EXCEPTION).is_file():raise unittest.SkipTest('initial exception is a project-specific frozen fixture')
        import implementation_migration as historical
        # This control exercises the initial approval, before publication and
        # later objective changes. Pending validation must retain exact inputs.
        cls.checkpoint=m.introduction(REPO,EXCEPTION)
        snapshot=historical._revision_repository(REPO,cls.checkpoint)
        cls.repo=snapshot.__enter__()
        cls.addClassCleanup(snapshot.__exit__,None,None,None)
        cls.ref,cls.exception=m.validate_owner_exception(cls.repo,EXCEPTION)
        cls.package_path=cls.exception['package']['path']
        cls.council_path=cls.exception['council']['path']
        cls.council=json.loads(m.read(cls.repo,cls.council_path))
        cls.raw_council=m.read(cls.repo,cls.council_path)
        cls.rows={r['handle']:r for r in sp.live_records(sp.collect_records(cls.repo/'bionic/adrs')) if r['source_status']=='Accepted'}

    def owner(self):
        return {'origin':'owner-conversation','quote':'Synthetic test approval of both exact objects.',
            'action':'approve-dispositions','at':'2026-10-17T05:00:00Z',
            'conversation':'synthetic-unit-test-only; never a recorded owner action',
            'presented':self.exception['package'],'owner_exception':self.ref}

    def test_exact_scope_positive_preserves_rejected_council(self):
        readiness={'commit':m._git(self.repo,'rev-parse','HEAD').decode().strip(),
            'sources':[{'path':p,'sha256':digest(m.blob(self.repo,m._git(self.repo,'rev-parse','HEAD').decode().strip(),p))}
                       for p in m.READINESS_INVENTORY]}
        with patch.object(m,'current_standing',return_value=self.rows),patch.object(m,'validate_readiness') as ready:
            # Disable the new scoped route: original/default policy refuses.
            with self.assertRaises(CycleError):m.validate_package(self.repo,self.package_path)
            with m.owner_exception_scope(self.repo,self.ref):
                result=m.validate_evidence(self.repo,self.package_path,self.council,readiness=readiness,
                    initial=True,policy='council-and-human',owner=self.owner())
            self.assertTrue(result['initial'])
            self.assertTrue(any(c.kwargs.get('action_commit')==m.introduction(self.repo,self.council_path)
                and c.args[1]==self.council['readiness'] for c in ready.call_args_list))
            self.assertTrue(any(c.args[1]==readiness for c in ready.call_args_list))
        self.assertEqual(m.read(self.repo,self.council_path),self.raw_council)
        self.assertEqual(self.council['outcome'],'changes-required')

    def test_pending_objectives_change_still_refuses_in_initial_exception_scope(self):
        path=self.repo/'bionic/objectives.md'
        original=path.read_bytes()
        try:
            path.write_bytes(original+b'\nA later objective change.\n')
            with m.owner_exception_scope(self.repo,self.ref), \
                 patch.object(m,'current_standing',return_value=self.rows), \
                 patch.object(m,'validate_readiness'), \
                 self.assertRaisesRegex(CycleError,'migration input changed: bionic/objectives.md'):
                m.validate_evidence(self.repo,self.package_path,self.council,
                    readiness=self.council['readiness'],initial=True,
                    policy='council-and-human',owner=self.owner())
            self.assertEqual(path.read_bytes(),original+b'\nA later objective change.\n')
            self.assertEqual(m.read(self.repo,self.council_path),self.raw_council)
        finally:
            path.write_bytes(original)

    def test_final_owner_must_bind_both_exact_objects(self):
        with m.owner_exception_scope(self.repo,self.ref):
            for owner in (None,{},dict(self.owner(),owner_exception=dict(self.ref,sha256='0'*64)),
                          {k:v for k,v in self.owner().items() if k!='owner_exception'}):
                with self.subTest(owner=owner),self.assertRaises(CycleError):
                    m.validate_evidence(self.repo,self.package_path,self.council,
                        readiness=self.council['readiness'],initial=True,policy='council-only',owner=owner)

    def test_other_package_and_ordinary_council_veto_are_not_waived(self):
        with m.owner_exception_scope(self.repo,self.ref):
            with self.assertRaises(CycleError):
                m.validate_evidence(self.repo,self.exception['original_package']['path'],self.council,
                    readiness=self.council['readiness'],initial=True,policy='council-and-human',owner=self.owner())
        with self.assertRaises(CycleError):
            m.validate_evidence(self.repo,self.package_path,self.council,
                readiness=self.council['readiness'],initial=True,policy='council-and-human',owner=self.owner())

    def test_external_binding_drift_and_fabricated_approval_flag_refuse(self):
        with self.assertRaises(CycleError):m.validate_owner_exception(self.repo,dict(self.ref,sha256='0'*64))
        updated=copy.deepcopy(self.exception);updated['council_approved']=True
        with patch.object(m,'bound_bytes',return_value=encoded(updated)):
            with self.assertRaisesRegex(CycleError,'scope'):m.validate_owner_exception(self.repo,self.ref)

    def test_prior_ready_source_replays_after_intentional_u2_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)
            def git(*args):
                return subprocess.check_output(['git','-C',temp,*args],stderr=subprocess.DEVNULL).decode().strip()
            git('init','-q');git('config','user.name','Test');git('config','user.email','test@example.invalid')
            path='crux/scripts/adr_migration.py';target=repo/path;target.parent.mkdir(parents=True)
            target.write_text('reviewed U1 validator\n');git('add','.');git('commit','-qm','Ready U1')
            basis=git('rev-parse','HEAD');proof={'sources':[m.binding(repo,path)]}
            target.write_text('intentional U2 reader integration\n');git('add','.');git('commit','-qm','U2')
            m._readiness_sources_at(repo,proof,basis)
            with self.assertRaises(CycleError):m._readiness_sources_at(repo,proof,git('rev-parse','HEAD'))


if __name__=='__main__':unittest.main()
