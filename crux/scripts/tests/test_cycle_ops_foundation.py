"""Shared foundation of the typed operations on the low-level writer.

Revision stamping on every version-3 save, the main-checkout guard, the low-level
holder rule and attempt-bound transitions on version-3 records, the shared owner
reference validator, and the one requirements policy the low-level advance reads."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_ops
from cycle_workflow import CycleError, LinkedWorktree, check_references, create, load, mutate, requirements, tree
from test_cycle_slice import SliceBase


class RevisionTests(SliceBase):
    def test_low_level_saves_increment_and_stamp_the_revision(self):
        before = load(self.repo, self.cid)['revision']
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['revision'], before + 1)
        self.assertEqual(doc['history'][-1]['revision'], before + 1)

    def test_version_two_saves_carry_no_revision(self):
        cid = self.fixture(version=2)
        mutate(self.repo, cid, 'checks', checks=['unit'])
        doc = load(self.repo, cid)
        self.assertNotIn('revision', doc)
        self.assertNotIn('revision', doc['history'][-1])

    def test_events_before_an_upgraded_event_stay_revisionless(self):
        path = self.record_path()
        raw = json.loads(path.read_text())
        for entry in raw['history']:
            entry.pop('revision', None)
        raw['history'].append({**raw['history'][-1], 'action': 'upgraded', 'previous_sha256': '0' * 64})
        path.write_text(json.dumps(raw))
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        doc = load(self.repo, self.cid)
        upgraded = max(i for i, e in enumerate(doc['history']) if e['action'] == 'upgraded')
        self.assertTrue(all('revision' not in e for e in doc['history'][:upgraded]))
        self.assertTrue(all('revision' in e for e in doc['history'][upgraded:]))


class HolderRuleTests(SliceBase):
    def test_low_level_reassignment_of_a_reserved_task_is_refused(self):
        self.prepare()
        with self.assertRaisesRegex(CycleError, 'held by reserved assignment build-it'):
            mutate(self.repo, self.cid, 'assignment', id='other', state='running', role='developer', task='build-it')

    def test_low_level_status_change_of_a_held_task_is_refused(self):
        self.prepare()
        with self.assertRaisesRegex(CycleError, 'typed deliver operation'):
            mutate(self.repo, self.cid, 'task', task_id='build-it', state='pending')

    def test_holder_may_be_recorded_lost_at_low_level(self):
        self.prepare()
        mutate(self.repo, self.cid, 'assignment', id='build-it', state='lost', note='the Agent call returned permission-denied')
        entry = load(self.repo, self.cid)['assignments'][0]
        self.assertEqual(entry['state'], 'lost')

    def test_low_level_finished_on_a_typed_attempt_names_deliver(self):
        prepared = self.prepare(mode='background')
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': prepared['assignment'], 'attempt': 1, 'handle': 'h1'})
        with self.assertRaisesRegex(CycleError, 'typed deliver operation'):
            mutate(self.repo, self.cid, 'assignment', id='build-it', state='finished')

    def test_low_level_entries_on_version_three_carry_null_typed_fields(self):
        mutate(self.repo, self.cid, 'assignment', id='lead-x', state='running', role='dev-lead')
        entry = load(self.repo, self.cid)['assignments'][0]
        self.assertEqual({k: entry[k] for k in cycle_ops.ASSIGNMENT_V3_FIELDS}, {'host': None, 'base': None, 'delivery': None})


class ReferenceTests(SliceBase):
    def test_directory_reference_lists_candidate_files(self):
        (self.repo / 'bionic/cycles/CYC-0032').mkdir(parents=True)
        for name in ('cycle.json', 'notes.md'):
            (self.repo / 'bionic/cycles/CYC-0032' / name).write_text('x\n')
        refs, problems = check_references(tree(self.repo), ['bionic/cycles/CYC-0032'])
        self.assertEqual(refs, [])
        self.assertEqual(problems[0]['code'], 'reference-is-directory')
        self.assertEqual(problems[0]['candidates'], ['bionic/cycles/CYC-0032/cycle.json', 'bionic/cycles/CYC-0032/notes.md'])

    def test_owner_complete_names_the_directory_and_accepts_no_authority(self):
        (self.repo / 'bionic/cycles/CYC-0032').mkdir(parents=True)
        (self.repo / 'bionic/cycles/CYC-0032/cycle.json').write_text('{}\n')
        owner = {'origin': 'owner-conversation', 'quote': 'close it', 'date': '2026-10-30', 'conversation': 'c'}
        with self.assertRaisesRegex(CycleError, 'reference-is-directory.*CYC-0032/cycle.json'):
            mutate(self.repo, self.cid, 'owner-complete', owner={**owner, 'authority': ['bionic/cycles/CYC-0032']})
        doc = mutate(self.repo, self.cid, 'owner-complete', owner=owner)
        self.assertEqual(doc['status'], 'completed')
        self.assertEqual(doc['history'][-1]['owner']['authority'], [])


class LinkedWorktreeTests(SliceBase):
    def setUp(self):
        super().setUp()
        self.linked = self.repo.parent / (self.repo.name + '-linked')
        self.git('worktree', 'add', '-q', '--detach', str(self.linked))
        self.addCleanup(lambda: subprocess.run(['git', '-C', str(self.repo), 'worktree', 'remove', '--force', str(self.linked)], capture_output=True))
        # The docs tree is ignored in the fixture, so the worktree needs its own copy to load at all.
        subprocess.run(['cp', '-R', str(self.repo / 'bionic'), str(self.linked / 'bionic')], check=True)

    def test_low_level_mutation_from_a_linked_worktree_is_refused(self):
        with self.assertRaises(LinkedWorktree) as caught:
            mutate(self.linked, self.cid, 'checks', checks=['unit'])
        self.assertEqual(caught.exception.main, self.repo)

    def test_typed_mutation_from_a_linked_worktree_is_refused(self):
        request = {'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer',
                   'host': 'claude-code', 'assignment_text': 'x'}
        code, response = cycle_ops.run(self.linked, self.cid, request)
        self.assertEqual(code, 1)
        self.assertEqual(response['errors'][0]['code'], 'linked-worktree')
        self.assertEqual(response['errors'][0]['expected'], str(self.repo))

    def test_inspect_from_a_linked_worktree_reads_the_main_record(self):
        mutate(self.repo, self.cid, 'checks', checks=['unit'])
        main_revision = load(self.repo, self.cid)['revision']
        code, response = cycle_ops.run(self.linked, self.cid, {'op': 'inspect'})
        self.assertEqual(code, 0, response)
        self.assertEqual(response['revision'], main_revision)
        self.assertNotEqual(load(self.linked, self.cid)['revision'], main_revision)


class RequirementsParityTests(SliceBase):
    def test_low_level_advance_raises_the_first_unmet_requirement(self):
        doc = load(self.repo, self.cid)
        first = requirements(tree(self.repo), doc, 'next')[0]['problem']
        with self.assertRaises(CycleError) as caught:
            mutate(self.repo, self.cid, 'advance')
        self.assertEqual(str(caught.exception), first)

    def test_first_stops_after_one_item(self):
        doc = load(self.repo, self.cid)
        self.assertGreater(len(requirements(tree(self.repo), doc, 'completion')), 1)
        self.assertEqual(len(requirements(tree(self.repo), doc, 'completion', first=True)), 1)


if __name__ == '__main__':
    unittest.main()
