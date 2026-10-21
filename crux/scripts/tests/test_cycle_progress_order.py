"""Cycle dashboard ordering (active first, numeric id descending) and the single approval line."""
import json
import os
import shutil
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import create
from cycle_progress import view,render


def decision(name,approval,kind='idr',accepted=False):
    return {'accepted':accepted,'approval':approval,'kind':kind,'name':name,'path':'decisions/x.json','sha256':'0'*64}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'bionic').mkdir();(self.root/'src').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        base=create(self.root,'iterate','Seed','Goal',['src'],['passes'],'builder','tester')
        self.seed=json.loads((self.root/'bionic/cycles'/base['id']/'cycle.json').read_text())
        shutil.rmtree(self.root/'bionic/cycles'/base['id'])
    def put(self,cid,status,mtime,decisions=None):
        doc=json.loads(json.dumps(self.seed));doc['id']=cid;doc['status']=status;doc['title']='T '+cid
        if decisions is not None:doc['decisions']=decisions
        d=self.root/'bionic/cycles'/cid;d.mkdir(parents=True);p=d/'cycle.json';p.write_text(json.dumps(doc));os.utime(p,(mtime,mtime))
    def ids(self):return [c['id'] for c in view(self.root)['cycles']]


class OrderTests(Base):
    def test_active_first_then_others_by_numeric_id_descending(self):
        # Modification times run opposite to the ids, so a time or lexical sort fails.
        self.put('CYC-0009','active',3000);self.put('CYC-0010','completed',1000);self.put('CYC-0013','active',2000)
        self.put('CYC-0002','abandoned',4000);self.put('CYC-0011','paused',5000)
        self.assertEqual(self.ids(),['CYC-0013','CYC-0009','CYC-0011','CYC-0010','CYC-0002'])
    def test_numeric_not_lexical_across_digit_counts(self):
        self.put('CYC-0099','completed',1);self.put('CYC-10000','completed',2);self.put('CYC-0100','completed',3)
        self.assertEqual(self.ids(),['CYC-10000','CYC-0100','CYC-0099'])
    def test_prefix_aware(self):
        self.put('ACME-CYC-0009','completed',1);self.put('CYC-0010','completed',2);self.put('ACME-CYC-0013','active',3)
        self.assertEqual(self.ids(),['ACME-CYC-0013','CYC-0010','ACME-CYC-0009'])


class ApprovalTests(Base):
    def test_superseded_revisions_render_no_stale_wait_lines(self):
        # Minimized from CYC-0012: nine unapproved revisions of one decision, the last approved.
        revs=[decision('release-evidence',None) for _ in range(9)]+[decision('release-evidence','approvals/r10.json')]
        self.put('CYC-0012','completed',1,revs)
        document=view(self.root)
        self.assertEqual(document['cycles'][0]['waits'],[])
        self.assertNotIn('Awaiting approval',render(document))
    def test_current_unapproved_revision_waits_once(self):
        revs=[decision('plan-a','approvals/a.json')]+[decision('plan-b',None) for _ in range(4)]+[decision('adr-c',None,'adr')]
        self.put('CYC-0013','active',1,revs)
        document=view(self.root)
        self.assertEqual(document['cycles'][0]['waits'],['plan-b','adr-c'])
        out=render(document)
        self.assertEqual(out.count('Awaiting approval'),1);self.assertIn('Awaiting approval: plan-b, adr-c',out)

if __name__=='__main__':unittest.main()
