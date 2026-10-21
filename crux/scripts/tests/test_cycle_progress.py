"""Cycle visualization uses guarded reads and distinct cycle semantics."""
import importlib.util
import io
import math
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_workflow import create,mutate,CycleError
from cycle_progress import view,render
from admission_source_io import SourceIORefusal


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'bionic').mkdir();(self.root/'src').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
    def test_cycle_phases_passes_and_history(self):
        doc=create(self.root,'quick-fix','Fix','Correct behavior',['src'],['passes'],'builder','tester')
        output=view(self.root)
        c=output['cycles'][0]
        self.assertEqual(output['format'],'crux.cycle-progress');self.assertEqual(c['phases'],['build','test','review','reflect'])
        self.assertEqual(c['pass_limit'],1);self.assertIn('Pass 1 of 1',render(output))
        mutate(self.root,doc['id'],'pause',reason='needs owner')
        self.assertEqual(view(self.root)['cycles'][0]['blocker'],'needs owner')
    def test_a_listed_release_cycle_shows_one_phase_and_no_pass_limit(self):
        doc=create(self.root,'release','Ship','Goal',['src'],['published'],'builder','tester',release_list='beta')
        output=view(self.root,doc['id']);c=output['cycles'][0]
        self.assertEqual((c['type'],c['phases'],c['pass'],c['pass_limit']),('release',['release'],1,1))
        text=render(output)
        self.assertNotIn('Pass 1 of 1',text);self.assertNotIn(' of ',text.splitlines()[1]);self.assertIn('Release · active',text)
        self.assertEqual(len(c['tasks']),6)
    def test_a_legacy_release_cycle_keeps_its_phases_and_pass_limit(self):
        doc=create(self.root,'release','Old','Goal',['src'],['published'],'builder','tester',release_list='beta')
        path=self.root/'bionic/cycles'/doc['id']/'cycle.json'
        record=json.loads(path.read_text());record.pop('release_list');record.update(phase='plan',pass_limit=2)
        record['plan']['tasks']=[{'id':p,'phase':p,'description':p,'depends_on':[],'status':'pending','expected_evidence':['x']} for p in ('plan','release','reflect')]
        path.write_text(json.dumps(record))
        output=view(self.root,doc['id']);c=output['cycles'][0]
        self.assertEqual((c['phases'],c['pass_limit']),(['plan','release','reflect'],2))
        self.assertIn('Pass 1 of 2 · Plan',render(output))
    def test_new_history_events_record_the_resulting_status(self):
        doc=create(self.root,'quick-fix','Fix','Correct behavior',['src'],['passes'],'builder','tester')
        mutate(self.root,doc['id'],'pause',reason='needs owner')
        mutate(self.root,doc['id'],'resume',reason='owner answered')
        history=json.loads((self.root/'bionic/cycles'/doc['id']/'cycle.json').read_text())['history']
        self.assertEqual([(e['action'],e['status']) for e in history],[('created','active'),('pause','paused'),('resume','active')])
    def test_format_2_carries_elapsed_fields_for_every_type(self):
        for kind in ('dev','iterate','refactor','quick-fix','release'):
            with self.subTest(kind=kind):
                doc=create(self.root,kind,'T '+kind,'Goal',['src'],['passes'],'builder','tester',release_list='beta' if kind=='release' else None)
                created=math.ceil(datetime.fromisoformat(doc['created_at']).timestamp())
                a=view(self.root,doc['id'],now=created+90)
                b=view(self.root,doc['id'],now=created+4000)
                c=a['cycles'][0]
                self.assertEqual(a['format_version'],2);self.assertEqual(a['now_s'],created+90)
                self.assertEqual((c['started_s'],c['ended_s'],c['paused_s'],c['basis']),(int(datetime.fromisoformat(doc['created_at']).timestamp()),None,0,'recorded'))
                self.assertEqual(c['open_started_s'],c['started_s'])
                self.assertEqual(c['phase_times'],[{'phase':c['phase'],'active_s':90,'paused_s':0}])
                self.assertEqual(b['cycles'][0]['phase_times'][0]['active_s'],4000)
                self.assertIn('Elapsed 1m',render(a));self.assertIn('Elapsed 1h06m',render(b))
    def test_paused_time_is_reported_for_old_records_without_status(self):
        doc=create(self.root,'dev','Old','Goal',['src'],['passes'],'builder','tester')
        mutate(self.root,doc['id'],'pause',reason='wait')
        path=self.root/'bionic/cycles'/doc['id']/'cycle.json'
        record=json.loads(path.read_text());base=math.ceil(datetime.fromisoformat(record['created_at']).timestamp())
        for e in record['history']:e.pop('status')
        record['history'][1]['at']=datetime.fromtimestamp(base+10,timezone.utc).isoformat()
        path.write_text(json.dumps(record))
        c=view(self.root,doc['id'],now=base+70)['cycles'][0]
        self.assertEqual((c['paused_s'],c['status'],c['basis']),(60,'paused','recorded'))
        self.assertIn('paused 1m',render(view(self.root,doc['id'],now=base+70)))
    def test_outside_symlink_config_is_refused(self):
        other=Path(self.temp.name).parent/'cycle-reader-outside.yml'
        other.write_text('config_version: "1"\ndocs_dir: bionic\n');self.addCleanup(other.unlink)
        (self.root/'.bionic.yml').symlink_to(other)
        with self.assertRaises(SourceIORefusal):view(self.root)
    def test_dashboard_entry_automatically_selects_cycles(self):
        create(self.root,'iterate','Fix','Correct behavior',['src'],['passes'],'builder','tester')
        path=Path(__file__).resolve().parents[1]/'visualize-run-progress.py'
        spec=importlib.util.spec_from_file_location('cycle_dashboard_legacy',path);mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
        output=io.StringIO()
        with redirect_stdout(output):code=mod.main(['--json','--project-root',str(self.root)])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['format'],'crux.cycle-progress')
    def test_symlink_cycle_record_refused(self):
        doc=create(self.root,'iterate','Fix','Correct behavior',['src'],['passes'],'builder','tester')
        path=self.root/'bionic/cycles'/doc['id']/'cycle.json';data=path.read_text();path.unlink()
        other=self.root/'other.json';other.write_text(data);path.symlink_to(other)
        with self.assertRaises((CycleError,SourceIORefusal)):view(self.root)

if __name__=='__main__':unittest.main()
