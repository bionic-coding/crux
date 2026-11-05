"""The cycle.py command line: `--json @PATH`, the cycle positionally or as `--cycle`, and either path base.

Each test reproduces a friction of CYC-0095 (F32, F36, F45, F-R4) against a temporary repository."""
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
from cycle_workflow import load
from test_cycle_ops_advance import AdvanceBase, REVIEW

# 5 KB with every shell-hostile character: apostrophes, double quotes, backticks, newlines, a backslash and a dollar sign.
HOSTILE = ("Implement `the answer`: it's \"small\".\nOutcome: src/a.py returns 2.\nConstraint: don't touch $HOME \\ or anything else.\n" * 50)[:5000] + "\nend\n"


class CliBase(AdvanceBase):
    def cli(self, *argv, stdin=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch('sys.stdin', stdin or sys.stdin):
            code = cycle.main(['--repo-root', str(self.repo), *argv])
        return code, out.getvalue()

    def cli_json(self, *argv, **kw):
        code, text = self.cli(*argv, **kw)
        return code, json.loads(text)

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def task(self):
        return next(t for t in load(self.repo, self.cid)['plan']['tasks'] if t['id'] == 'build-it')


class JsonFromFileTests(CliBase):
    def prepare_request(self):
        return {'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code', 'assignment_text': HOSTILE}

    def assert_caller_text_preserved(self, response):
        prompt = response['invocation']['parameters']['prompt']
        self.assertTrue(prompt.startswith('Mandatory assignment'))
        _, separator, addendum = prompt.partition('Optional caller addendum')
        self.assertTrue(separator)
        self.assertEqual(addendum.split('\n\n', 1)[1][:len(HOSTILE)], HOSTILE)

    def test_op_json_at_path_dispatches_the_assignment_byte_for_byte(self):
        self.assertGreater(len(HOSTILE), 5000)
        path = self.write('request.json', json.dumps(self.prepare_request()))
        code, response = self.cli_json('op', self.cid, '--json', f'@{path}')
        self.assertEqual(code, 0, response)
        self.assert_caller_text_preserved(response)

    def test_op_json_at_a_relative_path_is_read_from_the_repository_root(self):
        self.write('requests/request.json', json.dumps(self.prepare_request()))
        code, response = self.cli_json('op', self.cid, '--json', '@requests/request.json')
        self.assertEqual(code, 0, response)
        self.assert_caller_text_preserved(response)

    def test_inline_and_standard_input_forms_still_work(self):
        code, response = self.cli_json('op', self.cid, '--json', json.dumps({'op': 'inspect', 'summary': True}))
        self.assertEqual(code, 0, response)
        code, response = self.cli_json('op', self.cid, '--json', '-', stdin=io.StringIO(json.dumps({'op': 'inspect', 'summary': True})))
        self.assertEqual(code, 0, response)

    def test_review_json_at_path_records_the_report(self):
        receipt = self.unreviewed_phase()
        path = self.write('review.json', json.dumps({**REVIEW, 'evidence': [receipt]}))
        code, response = self.cli_json('review', self.cid, '--json', f'@{path}')
        self.assertEqual(code, 0, response)
        self.assertEqual(len(load(self.repo, self.cid)['reviews']), 1)

    def test_a_path_that_climbs_out_of_the_repository_is_refused(self):
        outside = self.repo.parent / (self.repo.name + '-outside.json')
        outside.write_text(json.dumps({'op': 'inspect'})); self.addCleanup(outside.unlink)
        code, response = self.cli_json('op', self.cid, '--json', f'@../{outside.name}')
        self.assertEqual(code, 1, response)
        self.assertEqual(response['errors'][0]['code'], 'request-unreadable')
        self.assertIn('outside the repository root', response['errors'][0]['problem'])

    def test_a_symlink_that_leaves_the_repository_is_refused(self):
        outside = self.repo.parent / (self.repo.name + '-target.json')
        outside.write_text(json.dumps({'op': 'inspect'})); self.addCleanup(outside.unlink)
        link = self.repo / 'link.json'
        link.symlink_to(outside)
        code, response = self.cli_json('op', self.cid, '--json', '@link.json')
        self.assertEqual(code, 1, response)
        self.assertIn('outside the repository root', response['errors'][0]['problem'])

    def test_a_file_command_refuses_an_escaping_path_and_writes_nothing(self):
        before = self.record_path().read_bytes()
        code, response = self.cli_json('review', self.cid, '--json', '@../elsewhere.json')
        self.assertEqual(code, 1, response)
        self.assertIn('outside the repository root', response['error'])
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_a_missing_file_is_refused_with_its_path(self):
        code, response = self.cli_json('op', self.cid, '--json', '@nothing-here.json')
        self.assertEqual(code, 1, response)
        self.assertIn('no file at', response['errors'][0]['problem'])


class CycleFormTests(CliBase):
    def test_status_takes_the_cycle_positionally_and_as_an_option(self):
        self.assertEqual(self.cli('status', self.cid)[0], 0)
        self.assertEqual(self.cli('status', '--cycle', self.cid)[0], 0)

    def test_op_takes_the_cycle_before_or_after_json_or_as_an_option(self):
        request = json.dumps({'op': 'inspect', 'summary': True})
        for argv in (['op', self.cid, '--json', request], ['op', '--json', request, self.cid], ['op', '--cycle', self.cid, '--json', request], ['op', '--json', request, '--cycle', self.cid]):
            code, response = self.cli_json(*argv)
            self.assertEqual((code, response['cycle']), (0, self.cid), argv)

    def test_per_cycle_commands_take_the_option(self):
        code, response = self.cli_json('show', '--cycle', self.cid, '--full')
        self.assertEqual((code, response['cycle']['id']), (0, self.cid))
        code, response = self.cli_json('--compact', 'validate', '--cycle', self.cid)
        self.assertEqual((code, response['cycle']), (0, self.cid))

    def test_await_takes_the_option(self):
        code, response = self.cli_json('await', '--cycle', self.cid, '--task-id', 'build-it', '--timeout', '1')
        self.assertEqual(code, 1)
        self.assertIn('no recorded result_path', response['error'])

    def test_the_same_cycle_twice_is_accepted_and_two_cycles_are_refused(self):
        self.assertEqual(self.cli('status', self.cid, '--cycle', self.cid)[0], 0)
        code, response = self.cli_json('show', self.cid, '--cycle', 'CYC-9999')
        self.assertEqual(code, 1)
        self.assertIn('twice with different values', response['error'])

    def test_no_cycle_is_still_refused(self):
        with contextlib.redirect_stderr(io.StringIO()) as err, self.assertRaises(SystemExit) as raised:
            self.cli('show')
        self.assertEqual(raised.exception.code, 2)
        self.assertIn('cycle', err.getvalue())


class PathBaseTests(CliBase):
    def test_evidence_given_repository_relative_is_recorded_docs_relative(self):
        self.write(f'bionic/cycles/{self.cid}/evidence/e.md', 'evidence\n')
        code, response = self.cli_json('task', self.cid, '--task-id', 'build-it', '--evidence', f'bionic/cycles/{self.cid}/evidence/e.md')
        self.assertEqual(code, 0, response)
        self.assertEqual(self.task()['evidence'], [f'cycles/{self.cid}/evidence/e.md'])

    def test_evidence_given_docs_relative_still_works(self):
        self.write(f'bionic/cycles/{self.cid}/evidence/e.md', 'evidence\n')
        code, response = self.cli_json('task', self.cid, '--task-id', 'build-it', '--evidence', f'cycles/{self.cid}/evidence/e.md')
        self.assertEqual(code, 0, response)
        self.assertEqual(self.task()['evidence'], [f'cycles/{self.cid}/evidence/e.md'])

    def test_evidence_that_exists_under_both_bases_as_different_files_is_refused_naming_both(self):
        self.write('bionic/x/same.md', 'docs\n')
        self.write('x/same.md', 'repository\n')
        before = self.record_path().read_bytes()
        code, response = self.cli_json('task', self.cid, '--task-id', 'build-it', '--evidence', 'x/same.md')
        self.assertEqual(code, 1, response)
        self.assertIn(str(self.repo / 'bionic/x/same.md'), response['error'])
        self.assertIn(str(self.repo / 'x/same.md'), response['error'])
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_evidence_that_exists_nowhere_is_passed_through_for_the_writer_to_report(self):
        code, response = self.cli_json('task', self.cid, '--task-id', 'build-it', '--evidence', 'nowhere/e.md')
        self.assertEqual(code, 1)
        self.assertIn('evidence nowhere/e.md does not exist under the docs root', response['error'])

    def test_result_path_given_docs_relative_is_recorded_repository_relative(self):
        self.write(f'bionic/cycles/{self.cid}/evidence/r.md', 'result\n')
        code, response = self.cli_json('task', self.cid, '--task-id', 'build-it', '--result-path', f'cycles/{self.cid}/evidence/r.md')
        self.assertEqual(code, 0, response)
        self.assertEqual(self.task()['result_path'], f'bionic/cycles/{self.cid}/evidence/r.md')

    def test_result_path_given_repository_relative_is_unchanged(self):
        self.write(f'bionic/cycles/{self.cid}/evidence/r.md', 'result\n')
        code, response = self.cli_json('task', self.cid, '--task-id', 'build-it', '--result-path', f'bionic/cycles/{self.cid}/evidence/r.md')
        self.assertEqual(code, 0, response)
        self.assertEqual(self.task()['result_path'], f'bionic/cycles/{self.cid}/evidence/r.md')

    def test_result_path_under_both_bases_as_different_files_is_refused_naming_both(self):
        self.write('bionic/y/r.md', 'docs\n')
        self.write('y/r.md', 'repository\n')
        code, response = self.cli_json('task', self.cid, '--task-id', 'build-it', '--result-path', 'y/r.md')
        self.assertEqual(code, 1, response)
        self.assertIn(str(self.repo / 'bionic/y/r.md'), response['error'])
        self.assertIn(str(self.repo / 'y/r.md'), response['error'])

    def test_assignment_result_path_is_normalized_the_same_way(self):
        self.write(f'bionic/cycles/{self.cid}/evidence/r.md', 'result\n')
        code, response = self.cli_json('assignment', self.cid, '--id', 'build-it', '--state', 'running', '--role', 'developer', '--task', 'build-it',
                                       '--result-path', f'cycles/{self.cid}/evidence/r.md')
        self.assertEqual(code, 0, response)
        entry = next(e for e in load(self.repo, self.cid)['assignments'] if e['id'] == 'build-it')
        self.assertEqual(entry['result_path'], f'bionic/cycles/{self.cid}/evidence/r.md')


if __name__ == '__main__':
    unittest.main()
