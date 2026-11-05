"""`cycle.py friction`: one table row per call, appended under the cycle lock and committed with the record."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
from test_cycle_slice import SliceBase

ROW = {'who': 'dev', 'what': 'ran `status CYC` and got usage', 'cost': 'one round', 'category': 'engine', 'fix': 'accept --cycle'}


class FrictionTests(SliceBase):
    def setUp(self):
        super().setUp()
        (self.repo / '.gitignore').write_text('*.lock\n__pycache__/\n')
        self.log = self.repo / f'bionic/cycles/{self.cid}/evidence/friction.md'

    def friction(self, request, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'friction', self.cid, '--json', request if isinstance(request, str) else json.dumps(request), *extra])
        return code, json.loads(out.getvalue())

    def rows(self):
        return [line for line in self.log.read_text().splitlines() if line.startswith('| F')]

    def test_two_calls_append_f1_and_f2_and_each_is_committed_with_the_record(self):
        code, first = self.friction(ROW)
        self.assertEqual((code, first['id']), (0, 'F1'))
        self.assertTrue(first['record_commit']['changed'], first)
        self.assertEqual(first['record_commit']['commit'], self.git('rev-parse', 'HEAD'))
        code, second = self.friction({**ROW, 'what': 'second'})
        self.assertEqual((code, second['id']), (0, 'F2'))
        text = self.log.read_text()
        self.assertEqual(text.count('| Id | Who |'), 1)
        self.assertTrue(text.startswith(f'# {self.cid} friction log\n'))
        self.assertEqual([r.split(' | ')[0] for r in self.rows()], ['| F1', '| F2'])
        self.assertIn(f'bionic/cycles/{self.cid}/evidence/friction.md', self.git('show', '--stat', '--format=', 'HEAD'))
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all', '--', 'bionic/cycles'), '')

    def test_other_id_forms_are_skipped_when_counting(self):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_text('# x\n\n| Id | Who |\n|---|---|\n| G7 | a |\n| F3 | b |\n| F12 | c |')
        code, response = self.friction(ROW)
        self.assertEqual((code, response['id']), (0, 'F13'))
        self.assertEqual(self.log.read_text().splitlines()[-2:], ['| F12 | c |', self.rows()[-1]])

    def test_pipes_and_newlines_stay_in_one_row(self):
        code, response = self.friction({**ROW, 'what': 'a | b\nc\r\nd', 'fix': 'x|y'})
        self.assertEqual(code, 0, response)
        row = self.rows()[0]
        self.assertIn('a \\| b c d', row)
        self.assertIn('x\\|y', row)
        self.assertEqual(len(self.rows()), 1)

    def test_a_request_from_a_file_is_accepted(self):
        (self.repo / 'row.json').write_text(json.dumps(ROW))
        code, response = self.friction('@row.json')
        self.assertEqual((code, response['id']), (0, 'F1'))

    def test_refused_requests_write_nothing(self):
        head = self.git('rev-parse', 'HEAD')
        for request, message in (({**ROW, 'extra': 'x'}, 'unknown friction keys: extra'),
                                 ({k: v for k, v in ROW.items() if k != 'fix'}, 'fix'),
                                 ({**ROW, 'cost': '  '}, 'cost'),
                                 ({**ROW, 'who': 3}, 'who'),
                                 ([1], 'JSON object')):
            code, response = self.friction(request)
            self.assertEqual(code, 1, request)
            self.assertIn(message, response['error'])
        self.assertFalse(self.log.exists())
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)


if __name__ == '__main__':
    unittest.main()
