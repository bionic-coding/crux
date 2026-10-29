"""reflect accepts lessons and remaining only as non-empty lists of non-empty strings.

Historical records that hold strings still validate and show, byte for byte.
"""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
from cycle_workflow import CycleError, PHASES, create, mutate, validate
from _dev_surface import require_dev_surface

HISTORICAL = Path(__file__).resolve().parents[3] / 'bionic/cycles/CYC-0068/cycle.json'


class ReflectionListTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'; (self.repo / 'bionic').mkdir(parents=True)
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.')
        doc = create(self.repo, 'iterate', 'Change', 'Goal', ['src'], ['Works'], 'dev', 'lead')
        plan = json.loads(json.dumps(doc['plan']))
        plan.update(verification=['t'], tasks=[{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['x']} for p in PHASES['iterate']])
        self.cid = mutate(self.repo, doc['id'], 'plan', plan=plan, reason='p')['id']
        self.paused()  # reflect is legal while paused, which avoids walking every phase

    def paused(self):
        path = self.repo / f'bionic/cycles/{self.cid}/cycle.json'
        doc = json.loads(path.read_text()); doc['status'] = 'paused'
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + '\n')
        return doc

    def reflect(self, **fields):
        reflection = {'outcome': 'o', 'lessons': ['l'], 'remaining': ['none']}
        reflection.update(fields)
        return mutate(self.repo, self.cid, 'reflect', reflection=reflection)

    def test_lists_of_non_empty_strings_are_accepted(self):
        doc = self.reflect(lessons=['a', 'b'], remaining=['none'])
        self.assertEqual(doc['reflection'], {'outcome': 'o', 'lessons': ['a', 'b'], 'remaining': ['none']})

    def test_invalid_shapes_are_refused_and_name_the_field(self):
        shapes = {'a string': 'text', 'an empty list': [], 'an empty item': ['ok', ''], 'a blank item': ['  '],
                  'a non-string item': ['ok', 3], 'a null': None, 'a dict': {'a': 'b'}}
        for field in ('lessons', 'remaining'):
            for label, value in shapes.items():
                with self.subTest(field=field, shape=label):
                    with self.assertRaises(CycleError) as raised:
                        self.reflect(**{field: value})
                    message = str(raised.exception)
                    self.assertIn(field, message)
                    self.assertIn('non-empty list of non-empty strings', message)
                    self.assertIn('["none"]', message)

    def test_empty_outcome_is_still_refused(self):
        with self.assertRaises(CycleError) as raised:
            self.reflect(outcome='')
        self.assertIn('outcome', str(raised.exception))

    def test_historical_string_record_validates_and_keeps_its_bytes(self):
        require_dev_surface(self, HISTORICAL, 'CYC-0068 historical cycle record')
        root = Path(self.temp.name) / 'history'
        target = root / 'bionic/cycles/CYC-0068/cycle.json'
        target.parent.mkdir(parents=True)
        (root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        shutil.copyfile(HISTORICAL, target)
        before = target.read_bytes()
        self.assertIsInstance(json.loads(before)['reflection']['lessons'], str)
        validate(json.loads(before))
        for command in ('validate', 'show'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cycle.main(['--repo-root', str(root), '--compact', command, 'CYC-0068'])
            self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(target.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
