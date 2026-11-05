"""Typed arrangement facts are validated by the writer, never guessed from prose."""
from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cycle_workflow import CycleError, load, mutate, review_basis_digest, validate
from test_cycle_slice import SliceBase


class ArrangementFactsTests(SliceBase):
    def planned(self):
        doc = deepcopy(load(self.repo, self.cid))
        doc['plan']['streams'] = [{'id': 'a', 'paths': ['src/a.py'], 'independent': True},
                                  {'id': 'b', 'paths': ['lib'], 'independent': True}]
        doc['plan']['tasks'] += [dict(doc['plan']['tasks'][0], id='second'),
                                dict(doc['plan']['tasks'][0], id='integrate', depends_on=['build-it', 'second'],
                                     integrates=['build-it', 'second'])]
        return doc

    def test_optional_fields_validate_and_legacy_stays_unchanged(self):
        old = load(self.repo, self.cid)
        self.assertNotIn('streams', old['plan'])
        self.assertIs(validate(old), old)
        planned = self.planned()
        self.assertIs(validate(planned), planned)
        before = review_basis_digest(old, 4)
        self.assertEqual(review_basis_digest(deepcopy(old), 4), before)
        digest = review_basis_digest(planned, 4)
        del planned['plan']['tasks'][-1]['integrates']
        self.assertNotEqual(review_basis_digest(planned, 4), digest)

    def test_invalid_stream_claims_refuse(self):
        for streams in ([{'id': 'a', 'paths': ['src'], 'independent': True},
                         {'id': 'b', 'paths': ['src/file.py'], 'independent': True}],
                        [{'id': 'a', 'paths': ['src'], 'independent': False},
                         {'id': 'a', 'paths': ['lib'], 'independent': False}],
                        *[[{'id': 'a', 'paths': [path], 'independent': True}]
                          for path in ('../src', '/src', 'src/*', 'src/../lib', './src', 'src\\file', 'src//file')]):
            with self.subTest(streams=streams), self.assertRaises(CycleError):
                doc = self.planned(); doc['plan']['streams'] = streams; validate(doc)

    def test_only_independent_streams_require_disjoint_paths(self):
        doc = self.planned()
        doc['plan']['streams'][1].update(paths=['src'], independent=False)
        validate(doc)

    def test_invalid_integration_facts_refuse(self):
        for integrates, phase, depends in ((['build-it'], 'build', ['build-it']),
                                           (['build-it', 'build-it'], 'build', ['build-it']),
                                           (['build-it', 'missing'], 'build', ['build-it']),
                                           (['build-it', 'second'], 'verify', ['build-it', 'second']),
                                           (['build-it', 'second'], 'build', ['build-it'])):
            with self.subTest(integrates=integrates, phase=phase, depends=depends), self.assertRaises(CycleError):
                doc = self.planned(); doc['plan']['tasks'][-1].update(integrates=integrates, phase=phase, depends_on=depends)
                validate(doc)

    def test_plan_details_writes_streams_and_invalid_update_is_atomic(self):
        streams = self.planned()['plan']['streams']
        mutate(self.repo, self.cid, 'plan-details', details={'streams': streams}, reason='declare arrangement facts')
        self.assertEqual(load(self.repo, self.cid)['plan']['streams'], streams)
        before = self.record_path().read_bytes()
        with self.assertRaises(CycleError):
            mutate(self.repo, self.cid, 'plan-details', details={'streams': [dict(streams[0], paths=['../escape'])]}, reason='bad')
        self.assertEqual(self.record_path().read_bytes(), before)
