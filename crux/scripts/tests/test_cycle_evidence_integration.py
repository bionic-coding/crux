"""Actual test executions are reused across cycle phases."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import *
from test_evidence import execute


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        environment = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.root / "evidence")})
        environment.start();self.addCleanup(environment.stop)
        (self.root/'bionic').mkdir();(self.root/'src').mkdir();(self.root/'dist').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root/'src/a.txt').write_text('good')
        (self.root/'dist/release.txt').write_text('artifact')
    def create(self,kind):return create(self.root,kind,'Fix','Outcome',['src','dist'],['correct'],'builder','tester')
    def apply(self,doc,action,**args):
        updated=mutate(self.root,doc['id'],action,**args)
        if action=='checks':
            updated=mutate(self.root,doc['id'],'coverage',coverage={'affected':['source and release artifact'],'checks':[{'check_id':c,'rationale':'related behavior exercised by '+c} for c in args['checks']],'not_selected':'No unrelated full-suite run needed for this fixture.'})
        if action=='reflect':
            updated=mutate(self.root,doc['id'],'completion',commits=[],exception='Fixture owner requests uncommitted delivery.',remaining='fixture inputs uncommitted')
        return updated
    def check(self,inputs=None,identity='unit'):
        return {'check_id':identity,'command':[sys.executable,'-c',"from pathlib import Path; assert Path('src/a.txt').read_text() == 'good'"],'inputs':inputs or ['src'],'environment':[]}
    def evidence(self,doc,decl):
        result=execute(self.root,decl)
        return self.apply(doc,'evidence',check_id=decl['check_id'],evidence_id=result['evidence']['id'],use=result['action']),result
    def review(self,doc):
        return self.apply(doc,'review',report={'reviewer':'independent','scope':['src','dist'],'evidence':[r['evidence_id'] for r in doc['evidence']],'blocking':[],'advisory':[],'cosmetic':[],'verdict':'approve','rationale':'reviewed changes and acceptance evidence'})
    def test_one_execution_shared_across_cycles_and_phases(self):
        first=self.create('quick-fix');second=self.create('quick-fix');decl=self.check()
        first=self.apply(first,'checks',checks=['unit']);first=self.apply(first,'advance')
        first,ran=self.evidence(first,decl)
        first=self.apply(first,'advance');first=self.review(first);first=self.apply(first,'advance')
        first=self.apply(first,'reflect',reflection={'outcome':'fixed','lessons':['reuse'],'remaining':['none']})
        first=self.apply(first,'advance');self.assertEqual(first['status'],'completed')
        second=self.apply(second,'checks',checks=['unit']);second=self.apply(second,'advance')
        second,reused=self.evidence(second,decl)
        self.assertEqual(ran['evidence']['id'],reused['evidence']['id']);self.assertEqual(reused['action'],'reused')
    def test_source_edit_invalidates_shared_evidence(self):
        doc=self.create('quick-fix');doc=self.apply(doc,'checks',checks=['unit']);doc=self.apply(doc,'advance');doc,result=self.evidence(doc,self.check())
        (self.root/'src/a.txt').write_text('bad')
        with self.assertRaises(CycleError):self.apply(doc,'advance')
    def test_identical_repeated_evidence_writes_nothing(self):
        doc=self.create('quick-fix');doc=self.apply(doc,'checks',checks=['unit']);doc=self.apply(doc,'advance')
        doc,result=self.evidence(doc,self.check())
        before=(tree(self.root).docs_root/'cycles'/doc['id']/'cycle.json').read_bytes()
        again,changed=mutate_tracked(self.root,doc['id'],'evidence',check_id='unit',evidence_id=result['evidence']['id'],use=result['action'])
        self.assertFalse(changed)
        self.assertEqual(len(again['evidence']),1)
        self.assertEqual((tree(self.root).docs_root/'cycles'/doc['id']/'cycle.json').read_bytes(),before)
        # Positive control: a different use is a new entry and is written.
        _,changed=mutate_tracked(self.root,doc['id'],'evidence',check_id='unit',evidence_id=result['evidence']['id'],use='reused' if result['action']!='reused' else 'executed')
        self.assertTrue(changed)
    def test_non_release_evidence_attachment_stores_receipt_id_and_digest_not_log_bytes(self):
        marker='LOG-MARKER-'+'7f3a91'
        decl={'check_id':'unit','command':[sys.executable,'-c',f"print('{marker}' * 50)"],'inputs':['src'],'environment':[]}
        doc=self.create('quick-fix');doc=self.apply(doc,'checks',checks=['unit']);doc=self.apply(doc,'advance')
        doc,result=self.evidence(doc,decl)
        self.assertEqual(set(doc['evidence'][-1]),{'check_id','evidence_id','pass','use','declaration_sha256'})
        self.assertEqual(doc['evidence'][-1]['evidence_id'],result['evidence']['id'])
        self.assertRegex(doc['evidence'][-1]['declaration_sha256'],r'^[0-9a-f]{64}$')
        # Positive control: the run's log bytes exist, in the evidence store.
        stored=[p for p in (self.root/'evidence').rglob('*') if p.is_file() and marker.encode() in p.read_bytes()]
        self.assertTrue(stored)
        cycle_dir=tree(self.root).docs_root/'cycles'/doc['id']
        copied=[p for p in cycle_dir.rglob('*') if p.is_file() and marker.encode() in p.read_bytes()]
        self.assertEqual(copied,[])
    def reviewed(self):
        doc=self.create('quick-fix');doc=self.apply(doc,'checks',checks=['unit']);doc=self.apply(doc,'advance');doc,_=self.evidence(doc,self.check())
        doc=self.apply(doc,'advance');return self.review(doc)
    def test_scrutiny_change_invalidates_review(self):
        doc=self.reviewed();doc=self.apply(doc,'scrutiny',scrutiny='intensive',rationale='sensitive boundary',risks=['credentials'])
        with self.assertRaisesRegex(CycleError,'independent review'):check_review(tree(self.root),doc)

if __name__=='__main__':unittest.main()
