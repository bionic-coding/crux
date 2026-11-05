"""The Verify phase vocabulary slice: a new record names the phase after Build 'verify'; a record without phase_names keeps 'test'."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle_progress import render, view
from cycle_workflow import CHECK_PHASES, PHASES, create, load, mutate, phases_of
from test_cycle_ops_advance import AdvanceBase


class VerifyVocabularyTests(AdvanceBase):
    def make_historical(self):
        """Strip phase_names: the record now reads as one created before the rename."""
        path = self.record_path()
        raw = json.loads(path.read_text())
        raw.pop('phase_names')
        path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')

    def run_through_check_phase(self, name):
        self.deliver_build()
        self.ok(self.advance('advance-b1'))
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['phase'], name)
        self.assertEqual(view(self.repo, self.cid)['cycles'][0]['phase'], name)
        self.assertIn(f'{name.title()} · active', render(view(self.repo, self.cid)))
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        mutate(self.repo, self.cid, 'coverage', coverage={'affected': ['x'], 'checks': [{'check_id': 'unit', 'rationale': 'r'}], 'not_selected': 'none'})
        self.receipt()
        self.assertEqual(self.ok(self.advance('advance-t1'))['phase'], 'review')

    def test_a_new_cycle_records_phase_names_and_goes_build_verify_review(self):
        self.assertEqual(load(self.repo, self.cid)['phase_names'], 'verify')
        self.assertEqual(phases_of(load(self.repo, self.cid)), ['build', 'verify', 'review', 'reflect'])
        self.run_through_check_phase('verify')
        self.assertEqual(view(self.repo, self.cid)['cycles'][0]['phases'], ['build', 'verify', 'review', 'reflect'])

    def test_a_record_without_phase_names_keeps_test(self):
        self.make_historical()
        self.assertEqual(phases_of(load(self.repo, self.cid)), ['build', 'test', 'review', 'reflect'])
        self.run_through_check_phase('test')
        self.assertNotIn('phase_names', load(self.repo, self.cid))

    def test_every_new_type_names_verify_and_release_keeps_its_sequence(self):
        for kind in ('dev', 'iterate', 'refactor', 'simplify', 'quick-fix'):
            doc = create(self.repo, kind, 't', 'g', ['src'], ['a'], 'b', 'c')
            sequence = phases_of(doc)
            self.assertIn('verify', sequence, kind)
            self.assertNotIn('test', sequence, kind)
            self.assertEqual(sequence.index('verify'), PHASES[kind].index('test'))
        release = create(self.repo, 'release', 't', 'g', ['src'], ['a'], 'b', 'c', release_list='beta')
        self.assertEqual(phases_of(release), ['release'])

    def test_check_phases_name_both(self):
        self.assertEqual(CHECK_PHASES, ('test', 'verify'))


if __name__ == '__main__':
    unittest.main()
