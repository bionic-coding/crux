"""Mixed-format pilot progress keeps review and delivery distinct."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _dev_surface import require_dev_surface
from _cycle_fixtures import fresh, put
from cycle_progress import view, render
from cycle_store import CycleError


class PilotProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'bionic').mkdir()
        (self.root/'src').mkdir()
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.doc = {'format':'crux.cycle.vNext','id':'CYC-0099','title':'Pilot',
                    'revision':1,'state':'working','lead':'lead',
                    'created_at':'2026-11-16T00:00:00+00:00','updated_at':'2026-11-16T00:01:00+00:00',
                    'tasks':[{'id':'change','description':'Change','owner':'lead','run':1,'status':'working','kind':'implementation','summary':''}],
                    'plan':{'revision':1,'council':{'needed':False}},'councils':[],
                    'delivery':{'pr':None,'ci':'unknown','merge':'unmerged'},'blockers':[]}

    def save(self):
        path=self.root/'bionic/cycles'/self.doc['id']/'cycle.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.doc))

    def test_mixed_list_does_not_run_legacy_readers_on_pilot(self):
        legacy={'id':put(self.root,fresh('quick-fix'),'CYC-0001')}
        self.save()
        out=view(self.root)
        by={c['id']:c for c in out['cycles']}
        self.assertEqual(by[legacy['id']]['type'],'quick-fix')
        self.assertEqual(by[self.doc['id']]['type'],'pilot')
        text=render(view(self.root,self.doc['id']))
        self.assertIn('Tasks 0/1 done',text)
        self.assertIn('lead run 1',text)
        self.assertNotIn('Pass 1',text)
        self.assertIn('CI: unknown; merge: unmerged',text)

    def test_a_current_record_renders_no_type_tag_and_no_phase_chain(self):
        # A current record has no type and no phases; the terminal renderer names neither.
        self.save()
        text=render(view(self.root,self.doc['id']))
        self.assertTrue(text.startswith('CYC-0099 Pilot\n'),text)
        self.assertNotIn('[pilot]',text)
        self.assertNotIn('→',text)
        self.assertIn('Working · active',text)

    def facts(self, applicable, reason='ok', completed=False):
        return {'status': 'completed' if completed else 'reviewed', 'review': {'verdict': 'approve'}, 'review_applicable': applicable,
                'applicability': reason, 'completed': completed, 'reopened': 0, 'delivery': self.doc['delivery']}

    def test_reviewed_is_not_completed_and_a_review_that_no_longer_applies_is_reported(self):
        self.doc['state']='reviewed';self.doc['tasks'][0]['status']='done';self.save()
        for applies in (True,False):
            with self.subTest(applies=applies), patch('cycle_writer.status_facts',return_value=self.facts(applies,'reviewed paths changed')):
                out=view(self.root,self.doc['id']);c=out['cycles'][0]
                # The recorded review, its applicability and completion are separate facts: the status stays reviewed.
                self.assertEqual(c['status'],'reviewed')
                self.assertIn('merge: unmerged',render(out))
                self.assertEqual('independent delta review' in render(out),not applies)
                self.assertEqual('awaiting finish' in render(out),applies)

    def test_completed_is_reported_apart_from_delivery(self):
        self.doc['state']='completed';self.doc['tasks'][0]['status']='done';self.save()
        with patch('cycle_writer.status_facts',return_value=self.facts(None,completed=True)):
            out=view(self.root,self.doc['id']);c=out['cycles'][0]
        self.assertEqual(c['status'],'completed')
        self.assertIn('Completed. Delivery, recorded separately: PR: none; CI: unknown; merge: unmerged',render(out))
        self.assertNotIn('delta review',render(out))

    def test_one_unreadable_pilot_record_does_not_blank_the_listing(self):
        self.save()
        broken=dict(self.doc,id='CYC-0100',state='finalized')  # a state this reader does not know
        path=self.root/'bionic/cycles/CYC-0100/cycle.json'
        path.parent.mkdir(parents=True);path.write_text(json.dumps(broken))
        out=view(self.root)
        by={c['id']:c for c in out['cycles']}
        self.assertEqual(by['CYC-0099']['title'],'Pilot')
        row=by['CYC-0100']
        self.assertEqual((row['title'],row['type'],row['status']),('Unreadable cycle record','pilot','paused'))
        self.assertIn('This record cannot be read: invalid pilot cycle',row['blocker'])
        self.assertIn('This record cannot be read',render(out))
        # An explicit request for the unreadable record still fails, and names the reason.
        with self.assertRaisesRegex(Exception,'invalid pilot cycle'):
            view(self.root,'CYC-0100')

    def test_the_committed_completed_pilot_records_render(self):
        """The record shapes that blanked the dashboard: CYC-0165 to CYC-0167, completed."""
        tree=Path(__file__).resolve().parents[3]/'bionic/cycles'
        require_dev_surface(self,tree/'CYC-0167/cycle.json','the committed pilot cycle records')
        for identity in ('CYC-0165','CYC-0166','CYC-0167'):
            target=self.root/'bionic/cycles'/identity/'cycle.json'
            target.parent.mkdir(parents=True);target.write_text((tree/identity/'cycle.json').read_text())
        out=view(self.root)
        self.assertEqual({c['id']:(c['type'],c['status'],c['phase']) for c in out['cycles']},
                         {i:('pilot','completed','completed') for i in ('CYC-0165','CYC-0166','CYC-0167')})
        for row in out['cycles']:
            self.assertEqual(row['phases'],['planning','working','reviewing','reviewed','completed'])
            self.assertIn('Completed. Delivery, recorded separately: PR: none; CI: unknown; merge: unmerged',row['reflection'])

    def test_paused_blocker_and_wrong_identity(self):
        self.doc['state']='paused';self.doc['resume_state']='working'
        self.doc['blockers']=['Owner decision needed'];self.save()
        self.assertIn('Owner decision needed',render(view(self.root,self.doc['id'])))
        path=self.root/'bionic/cycles'/self.doc['id']/'cycle.json'
        bad=copy.deepcopy(self.doc);bad['id']='CYC-0100';path.write_text(json.dumps(bad))
        with self.assertRaises(CycleError):view(self.root,self.doc['id'])

    def test_an_abandoned_record_stands_on_the_step_it_stopped_in(self):
        # The writer keeps no state on abandonment, so the reader derives the step from the record.
        approve={'verdict':'approve','at':'2026-11-16T00:05:00+00:00'}
        cases=[
            ('paused first, in reviewing',{'resume_state':'reviewing'},'reviewing'),
            ('an open review request',{'review_request':{'reviewer':'r','at':'2026-11-16T00:04:00+00:00'}},'reviewing'),
            ('an approving review',{'review':approve},'reviewed'),
            ('a plan revision after the approval',{'review':approve,'history':[{'kind':'plan','at':'2026-11-16T00:06:00+00:00'}]},'working'),
            ('a review that required changes',{'review':{'verdict':'changes-required','at':'2026-11-16T00:05:00+00:00'}},'working'),
            ('no task started',{'tasks':[{**self.doc['tasks'][0],'run':0,'status':'pending'}]},'planning'),
            ('a started task',{},'working'),
        ]
        base=copy.deepcopy(self.doc);base['tasks'][0]['status']='done'
        for name,over,step in cases:
            with self.subTest(name), patch('cycle_writer.status_facts',return_value=self.facts(None)):
                self.doc={**copy.deepcopy(base),'state':'abandoned',**over};self.save()
                c=view(self.root,self.doc['id'])['cycles'][0]
                self.assertEqual((c['status'],c['phase']),('abandoned',step))
        self.doc=base
        # Positive control: a paused record keeps the state it paused from.
        self.doc={**self.doc,'state':'paused','resume_state':'reviewed'};self.save()
        self.assertEqual(view(self.root,self.doc['id'])['cycles'][0]['phase'],'reviewed')

    def test_a_v1_record_renders_as_a_vNext_record_and_the_json_carries_its_own_format(self):
        rows,texts={},{}
        for fmt in ('crux.cycle.vNext','crux.cycle.v1'):
            self.doc['format']=fmt;self.save()
            out=view(self.root,self.doc['id'])
            rows[fmt]=out['cycles'][0];texts[fmt]=render(out)
            self.assertEqual(rows[fmt]['type'],'pilot')
            self.assertEqual(rows[fmt]['schema_version'],fmt)
            self.assertEqual(out['format_version'],5)
        self.assertEqual(texts['crux.cycle.v1'],texts['crux.cycle.vNext'])
        self.assertEqual({**rows['crux.cycle.v1'],'schema_version':None},{**rows['crux.cycle.vNext'],'schema_version':None})
        self.assertEqual(set(rows['crux.cycle.v1']),set(rows['crux.cycle.vNext']))
        # A listing marks a broken v1 record unreadable, as it does a broken vNext record, and keeps its format.
        self.doc['format']='crux.cycle.v1';self.doc['state']='finalized';self.save()
        row=view(self.root)['cycles'][0]
        self.assertEqual((row['title'],row['schema_version']),('Unreadable cycle record','crux.cycle.v1'))

    def test_unresolved_council_is_visible_in_status(self):
        self.doc['plan']['council']['needed'] = True
        self.save()
        self.assertIn('council required for dependent tasks', render(view(self.root,self.doc['id'])))
