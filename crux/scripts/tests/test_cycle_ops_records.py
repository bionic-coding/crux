"""Typed owner-exception: the exceptional close, the malformed-authority closure scenario and its records."""
import json
import shlex
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_ops
from cycle_workflow import CycleError, create, load, mutate
from test_cycle_slice import SCRIPTS, SliceBase, shared_interpreter_env

QUOTE = "Close it: that's what I want.\nThe checks cannot pass."
BASE_REQUEST = {'op': 'owner-exception', 'op_id': 'exception-01', 'quote': QUOTE, 'conversation': 'Owner, 2026-10-30 session', 'date': '2026-10-30'}


class OwnerExceptionBase(SliceBase):
    def authority_directory(self, name='bionic/cycles/CYC-0032'):
        """A fixture of the historical CYC-0032 directory, in this temporary repository only."""
        directory = self.repo / name
        directory.mkdir(parents=True)
        for file in ('cycle.json', 'notes.md', 'evidence/receipt.json'):
            (directory / file).parent.mkdir(parents=True, exist_ok=True)
            (directory / file).write_text('{}\n')
        return name


class ClosureScenarioTests(OwnerExceptionBase):
    """CYC-0032: an owner closed a cycle that could not complete, citing a directory as authority."""

    def test_directory_reference_through_owner_exception_names_field_directory_and_candidates(self):
        directory = self.authority_directory()
        before = self.record_path().read_bytes()
        response = self.refused({**BASE_REQUEST, 'references': [directory]}, 'reference-is-directory')
        error = response['errors'][0]
        self.assertEqual((error['field'], error['observed']), ('references', directory))
        self.assertEqual(error['candidates'], ['bionic/cycles/CYC-0032/cycle.json', 'bionic/cycles/CYC-0032/evidence/receipt.json',
                                               'bionic/cycles/CYC-0032/notes.md'])
        self.assertIn(directory, error['problem'])
        recovery = error['recovery'][0]
        self.assertEqual(recovery['caller_fills'], ['op_id'])
        self.assertEqual(recovery['request'], {k: v for k, v in BASE_REQUEST.items() if k != 'op_id'})
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_the_returned_recovery_closes_the_cycle_with_no_other_write(self):
        directory = self.authority_directory()
        recovery = self.refused({**BASE_REQUEST, 'references': [directory]}, 'reference-is-directory')['errors'][0]['recovery'][0]
        self.assertEqual(cycle_ops.schema_errors({**recovery['request'], 'op_id': 'recovery-01'}), [])
        done = self.ok({**recovery['request'], 'op_id': 'recovery-01'})
        self.assertEqual(done['status'], 'completed')
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['status'], 'completed')
        self.assertEqual(doc.get('assignments', []), [], 'closing recorded an assignment')
        self.assertEqual([e['action'] for e in doc['history']][-1], 'owner-exception')
        self.assertEqual(doc['history'][-1]['owner']['authority'], [])
        self.assertEqual([op['op'] for op in doc['operations']], ['owner-exception'])

    def test_the_low_level_owner_complete_returns_the_same_precise_error(self):
        directory = self.authority_directory()
        owner = {'origin': 'owner-conversation', 'quote': 'close it', 'conversation': 'Owner session', 'date': '2026-10-30', 'authority': [directory]}
        with self.assertRaises(CycleError) as caught:
            mutate(self.repo, self.cid, 'owner-complete', owner=owner)
        message = str(caught.exception)
        self.assertIn('reference-is-directory', message)
        self.assertIn(directory, message)
        self.assertIn('bionic/cycles/CYC-0032/notes.md', message)
        self.assertEqual(load(self.repo, self.cid)['status'], 'active')
        # Omitting the authority closes it.
        done = mutate(self.repo, self.cid, 'owner-complete', owner={k: v for k, v in owner.items() if k != 'authority'})
        self.assertEqual(done['status'], 'completed')

    def test_other_reference_classes_refuse_with_their_own_code(self):
        self.authority_directory()
        (self.repo / 'bionic/real.md').write_text('real\n')
        (self.repo / 'bionic/link.md').symlink_to(self.repo / 'bionic/real.md')
        for name, code in (('bionic/absent.md', 'reference-missing'), ('bionic/link.md', 'reference-symlink'),
                           ('../outside.md', 'reference-outside-repository')):
            with self.subTest(code=code):
                error = self.refused({**BASE_REQUEST, 'references': [name]}, code)['errors'][0]
                self.assertEqual(error['field'], 'references')
                self.assertEqual(error['candidates'], [])

    def test_a_file_reference_is_recorded_with_its_digest(self):
        (self.repo / 'bionic/note.md').write_text('the owner said close it\n')
        self.ok({**BASE_REQUEST, 'references': ['bionic/note.md']})
        authority = load(self.repo, self.cid)['history'][-1]['owner']['authority']
        self.assertEqual([a['path'] for a in authority], ['bionic/note.md'])
        self.assertEqual(len(authority[0]['sha256']), 64)


class RecordTests(OwnerExceptionBase):
    def test_requirements_stay_unmet_and_open_attempts_are_listed(self):
        prepared = self.prepare()
        unmet = self.ok({'op': 'inspect'})['unmet']['completion']
        self.assertTrue(unmet)
        done = self.ok(BASE_REQUEST)
        self.assertEqual((done['status'], done['changed'], done['replayed']), ('completed', True, False))
        doc = load(self.repo, self.cid)
        entry = doc['history'][-1]
        self.assertEqual(entry['action'], 'owner-exception')
        self.assertEqual(entry['owner'], {'origin': 'owner-conversation', 'quote': QUOTE, 'conversation': 'Owner, 2026-10-30 session',
                                          'date': '2026-10-30', 'authority': []})
        self.assertEqual(entry['unmet'], unmet)
        self.assertEqual(entry['open_attempts'], [{'id': 'build-it', 'attempt': 1, 'task': 'build-it', 'state': 'reserved',
                                                   'result_path': prepared['result_path']}])
        self.assertEqual(doc['plan']['tasks'][0]['status'], 'active', 'the exception satisfied a requirement')
        self.assertEqual(doc['assignments'][0]['state'], 'reserved')
        self.assertEqual(doc['status'], 'completed')

    def test_replay_and_closed_cycles(self):
        self.ok(BASE_REQUEST)
        again = self.ok(BASE_REQUEST)
        self.assertEqual((again['replayed'], again['changed']), (True, False))
        self.refused({**BASE_REQUEST, 'op_id': 'exception-02'}, 'cycle-closed')

    def test_a_paused_cycle_can_be_closed(self):
        mutate(self.repo, self.cid, 'pause', reason='blocked by the host')
        self.assertEqual(self.ok(BASE_REQUEST)['status'], 'completed')

    def test_a_listed_release_cycle_closes_through_the_owner_mapping(self):
        doc = create(self.repo, 'release', 'Beta', 'Ship beta', ['src'], ['beta'], 'releaser', 'tester', release_list='beta')
        if doc['schema_version'] == 2:  # create writes version 2 until the workflow unit changes it
            self.ok({'op': 'upgrade', 'op_id': 'upgrade-001'}, cid=doc['id'])
        done = self.ok(BASE_REQUEST, cid=doc['id'])
        self.assertEqual(done['status'], 'completed')
        entry = load(self.repo, doc['id'])['history'][-1]
        self.assertEqual((entry['action'], entry['owner']['quote']), ('owner-exception', QUOTE))
        self.assertTrue(entry['unmet'])

    def test_the_no_commits_finish_refusal_offers_the_exception(self):
        response = self.refused({'op': 'finish', 'op_id': 'finish-001', 'expect_revision': 1, 'lessons': ['x'], 'remaining': ['none']},
                                'wrong-phase', 'no-commits')
        recovery = [r for e in response['errors'] for r in e['recovery'] if r['request']['op'] == 'owner-exception'][0]
        self.assertEqual(cycle_ops.schema_errors({**recovery['request'], **{k: BASE_REQUEST[k] for k in recovery['caller_fills']}}), [])

    def test_inline_quote_with_apostrophe_and_newline_through_a_real_shell(self):
        argument = ('{"op":"owner-exception","op_id":"inline-0001","conversation":"Owner session","date":"2026-10-30",'
                    '"quote":"Close it: that\\u0027s what I want.\\nThe checks cannot pass."}')
        script = f"{shlex.quote(sys.executable)} {SCRIPTS / 'cycle.py'} --repo-root {self.repo} --compact op {self.cid} --json '{argument}'"
        out = subprocess.run(['sh', '-c', script], capture_output=True, text=True, cwd=SCRIPTS, env=shared_interpreter_env())
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertTrue(json.loads(out.stdout)['ok'])
        self.assertEqual(load(self.repo, self.cid)['history'][-1]['owner']['quote'], QUOTE)

    def test_version_two_cycles_need_the_upgrade(self):
        cid = self.fixture(version=2)
        self.refused(BASE_REQUEST, 'needs-upgrade', cid=cid)


if __name__ == '__main__':
    unittest.main()
