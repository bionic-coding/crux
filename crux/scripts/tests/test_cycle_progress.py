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


class QueueDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'bionic').mkdir();(self.root/'src').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root/'bionic/objectives.md').write_text('Mission: useful changes.')
    def add(self,title='Do it'):
        import cycle_queue
        return cycle_queue.add(self.root,title,'Outcome','iterate',['src'],['ok'])['item']['id']
    def test_queue_is_null_without_a_queue_file_and_for_an_explicit_id(self):
        doc=create(self.root,'quick-fix','Fix','Goal',['src'],['ok'],'builder','tester')
        self.assertIsNone(view(self.root)['queue'])
        self.add()
        self.assertIsNone(view(self.root,doc['id'])['queue'])
        self.assertEqual(view(self.root,doc['id'])['format_version'],2)
    def test_a_valid_queue_gives_bounded_cleaned_items_with_status_and_authorization(self):
        import cycle_queue
        ids=[self.add(str(n)+'x'*190) for n in range(12)]
        path=self.root/'bionic/queue/cycles.yaml'
        doc=cycle_queue.parse_queue(path.read_text())
        first=create(self.root,'quick-fix','Fix','Goal',['src'],['ok'],'builder','tester')
        doc['items'][0].update(state='started',cycle=first['id'],started_at='2026-01-01T00:00:00+00:00',start_token='a'*32)
        doc['items'][2]['state']='held';doc['items'][2]['hold_reason']='wait'
        doc['items'][1].update(state='started',cycle='CYC-9999',started_at='2026-01-01T00:00:00+00:00',start_token='b'*32)
        doc['authorization']={'instruction':'go','kind':'queue','count':None,'scope':ids[:3],'started':[ids[0],ids[1]],'authorized_at':'2026-01-01T00:00:00+00:00','date':'2026-01-01'}
        from bionic_config import load_config
        cycle_queue.write_queue(load_config(self.root,require_tree=True),doc)
        q=view(self.root)['queue']
        self.assertTrue(q['ok']);self.assertEqual(len(q['items']),12)
        a,c,b,d=q['items'][:4]
        self.assertEqual(set(a),{'id','title','state','suggested_type','cycle','cycle_status'})
        self.assertEqual((a['id'],a['state'],a['cycle'],a['cycle_status']),(ids[0],'started',first['id'],'active'))
        self.assertEqual((b['state'],b['cycle_status']),('held',None))
        self.assertEqual((c['state'],c['cycle_status']),('started','missing'))
        self.assertEqual((d['state'],d['cycle'],d['cycle_status'],d['suggested_type']),('pending',None,None,'iterate'))
        self.assertLessEqual(len(a['title']),200)
        self.assertEqual(q['authorization'],{'kind':'queue','remaining':[ids[2]]})
    def test_a_long_queue_keeps_every_unstarted_item_and_the_last_two_started(self):
        import cycle_queue
        from bionic_config import load_config
        ids=[self.add('t'+str(n)) for n in range(60)]
        path=self.root/'bionic/queue/cycles.yaml'
        doc=cycle_queue.parse_queue(path.read_text())
        for n in range(30):doc['items'][n].update(state='started',cycle='CYC-%04d'%(9000+n),started_at='2026-01-01T00:00:00+00:00',start_token=('%032x'%n))
        cycle_queue.write_queue(load_config(self.root,require_tree=True),doc)
        q=view(self.root)['queue']
        self.assertEqual([i['id'] for i in q['items']],ids[28:60])
        self.assertEqual([i['state'] for i in q['items']][:2],['started','started'])
        self.assertIn(ids[59],[i['id'] for i in q['items']])
    def test_more_than_fifty_unstarted_keeps_the_first_fifty_in_run_order(self):
        ids=[self.add('t'+str(n)) for n in range(55)]
        q=view(self.root)['queue']
        self.assertEqual([i['id'] for i in q['items']],ids[:50])
    def test_the_authorization_remaining_counts_the_whole_queue_not_the_slice(self):
        import cycle_queue
        from bionic_config import load_config
        ids=[self.add('t'+str(n)) for n in range(60)]
        path=self.root/'bionic/queue/cycles.yaml'
        doc=cycle_queue.parse_queue(path.read_text())
        doc['authorization']={'instruction':'go','kind':'queue','count':None,'scope':ids,'started':[],'authorized_at':'2026-01-01T00:00:00+00:00','date':'2026-01-01'}
        cycle_queue.write_queue(load_config(self.root,require_tree=True),doc)
        q=view(self.root)['queue']
        self.assertEqual(len(q['items']),50);self.assertEqual(q['authorization']['remaining'],ids)
    def test_no_authorization_gives_null(self):
        self.add();self.assertIsNone(view(self.root)['queue']['authorization'])
    def test_an_invalid_queue_gives_ok_false_while_cycles_render(self):
        create(self.root,'quick-fix','Fix','Goal',['src'],['ok'],'builder','tester')
        (self.root/'bionic/queue').mkdir();(self.root/'bionic/queue/cycles.yaml').write_text('format: wrong\n')
        out=view(self.root)
        self.assertFalse(out['queue']['ok']);self.assertLessEqual(len(out['queue']['error']),300);self.assertEqual(set(out['queue']),{'ok','error'})
        self.assertEqual(len(out['cycles']),1)
    def test_the_text_render_is_unchanged_and_omits_the_queue_key(self):
        create(self.root,'quick-fix','Fix','Goal',['src'],['ok'],'builder','tester')
        self.add('Queued thing')
        text=render(view(self.root))
        self.assertIn('Queued requests\n  1. Q-0001 pending Queued thing',text)
        self.assertTrue(text.endswith('Authorization: none'))
        self.assertNotIn('"queue"',text)


if __name__=='__main__':unittest.main()
