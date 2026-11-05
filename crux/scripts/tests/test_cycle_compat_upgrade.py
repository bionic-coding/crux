"""Active-cycle upgrade from version 2 to version 3: retention, boundaries, continuation and the rollback limit."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_ops
from cycle_workflow import load, mutate, v3_fields, validate
from test_cycle_slice import SliceBase

# The cycle schema as released in 4.9.1 (commit 72ed53dd, blob b0d9f9ad), committed as a fixture so the
# rollback-limit test runs on every machine and in the staged suite. The digest pins the exact bytes.
PREVIOUS_SCHEMA = Path(__file__).resolve().parent / 'fixtures/cycle-schema-4.9.1/cycle.schema.json'
PREVIOUS_SCHEMA_SHA256 = '69cbd19b0d298ac60220929860ec77d18d3fb1a7bff9aef4fd0419a7977b36cb'
UPGRADE = {'op': 'upgrade', 'op_id': 'upgrade-001'}
OWNER = {'origin': 'owner-conversation', 'quote': 'close it', 'conversation': 'Owner session', 'date': '2026-10-30'}


class UpgradeBase(SliceBase):
    def setUp(self):
        super().setUp()
        self.old = self.fixture(version=2)

    def backup_path(self, cid=None):
        return self.repo / f'bionic/cycles/{cid or self.old}/upgrade/v2-cycle.json'

    def start_legacy(self, state=None, note=None):
        mutate(self.repo, self.old, 'assignment', id='build-it', state='running', role='developer', task='build-it')
        if state:
            mutate(self.repo, self.old, 'assignment', id='build-it', state=state, **({'note': note} if note else {}))

    def raw(self, cid=None):
        return json.loads(self.record_path(cid or self.old).read_text())


class RefusalTests(UpgradeBase):
    def test_a_running_assignment_blocks_the_upgrade_and_both_recoveries_are_returned(self):
        self.start_legacy()
        before = self.record_path(self.old).read_bytes()
        response = self.refused(UPGRADE, 'assignments-running', cid=self.old)
        error = response['errors'][0]
        self.assertEqual((error['field'], error['observed']), ('assignments', ['build-it/1']))
        finished, lost = error['recovery']
        self.assertEqual(finished['argv'][-6:], ['assignment', self.old, '--id', 'build-it', '--state', 'finished'])
        self.assertIn('final report', finished['purpose'])
        self.assertEqual(lost['argv'][-7:], ['assignment', self.old, '--id', 'build-it', '--state', 'lost', '--note'])
        self.assertEqual(lost['caller_fills'], ['--note'])
        self.assertIn('affirmative evidence', lost['purpose'])
        self.assertFalse(self.backup_path().exists(), 'a refusal wrote the backup')
        self.assertEqual(self.record_path(self.old).read_bytes(), before)

    def test_version_two_inspect_is_read_only_and_typed_mutations_need_the_upgrade(self):
        self.start_legacy()
        before = self.record_path(self.old).read_bytes()
        seen = self.ok({'op': 'inspect'}, cid=self.old)
        self.assertEqual((seen['schema_version'], seen['assignments'][0]['state']), (2, 'running'))
        self.assertEqual(seen['actions'], [cycle_ops.action({'op': 'upgrade'}, [], 'upgrade the record to version 3 before typed operations')])
        self.refused({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h'}, 'needs-upgrade', cid=self.old)
        self.assertEqual(self.record_path(self.old).read_bytes(), before)

    def test_a_closed_cycle_never_upgrades(self):
        mutate(self.repo, self.old, 'owner-complete', owner=OWNER)
        before = self.record_path(self.old).read_bytes()
        self.refused(UPGRADE, 'cycle-closed', cid=self.old)
        self.assertFalse(self.backup_path().exists())
        self.assertEqual(self.record_path(self.old).read_bytes(), before)

    def test_a_version_one_record_is_unsupported(self):
        path = self.record_path(self.old)
        raw = json.loads(path.read_text())
        raw['schema_version'] = 1
        try:
            validate(raw)
        except Exception:
            self.skipTest('a version-1 record cannot be built from the version-2 fixture')
        path.write_text(json.dumps(raw))
        self.refused(UPGRADE, 'unsupported-version', cid=self.old)

    def test_a_version_three_record_is_already_upgraded(self):
        self.refused(UPGRADE, 'already-upgraded')

    def test_a_different_file_at_the_backup_path_is_refused(self):
        self.backup_path().parent.mkdir(parents=True)
        self.backup_path().write_text('something else\n')
        before = self.record_path(self.old).read_bytes()
        response = self.refused(UPGRADE, 'upgrade-backup-conflict', cid=self.old)
        self.assertEqual(response['errors'][0]['field'], 'backup')
        self.assertEqual(self.backup_path().read_text(), 'something else\n')
        self.assertEqual(self.record_path(self.old).read_bytes(), before)


class RetentionTests(UpgradeBase):
    def test_the_previous_bytes_are_kept_and_only_the_version_three_fields_are_added(self):
        self.start_legacy('finished', None)
        mutate(self.repo, self.old, 'assignment', id='lost-one', state='running', role='reviewer')
        mutate(self.repo, self.old, 'assignment', id='lost-one', state='lost', note='the host reported the agent terminated')
        before_bytes = self.record_path(self.old).read_bytes()
        before = json.loads(before_bytes)
        done = self.ok(UPGRADE, cid=self.old)
        self.assertEqual((done['changed'], done['revision'], done['replayed']), (True, 1, False))
        self.assertEqual(self.backup_path().read_bytes(), before_bytes)
        after = self.raw()
        self.assertEqual(after['schema_version'], 3)
        added = set(after) - set(before)
        self.assertEqual(added, set(v3_fields()))
        self.assertEqual((after['operations'][0]['op'], after['operations'][0]['revision'], after['results_dir']), ('upgrade', 1, None))
        self.assertEqual(len(after['operations']), 1)
        for key in set(before) - {'schema_version', 'history', 'assignments', 'updated_at'}:
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(after['history'][:-1], before['history'])
        event = after['history'][-1]
        self.assertEqual((event['action'], event['previous_sha256'], event['revision']),
                         ('upgraded', hashlib.sha256(before_bytes).hexdigest(), 1))
        self.assertEqual(len(after['assignments']), 2)
        for old, new in zip(before['assignments'], after['assignments']):
            self.assertEqual({k: v for k, v in new.items() if k not in cycle_ops.ASSIGNMENT_V3_FIELDS}, old)
            self.assertEqual([new[k] for k in cycle_ops.ASSIGNMENT_V3_FIELDS], [None, None, None])
        self.assertEqual([a['state'] for a in after['assignments']], ['finished', 'lost'])
        validate(after)

    def test_active_and_paused_cycles_upgrade(self):
        paused = self.fixture(version=2)
        mutate(self.repo, paused, 'pause', reason='waiting on the owner')
        for cid in (self.old, paused):
            with self.subTest(cid=cid):
                done = self.ok(UPGRADE, cid=cid)
                self.assertEqual(done['revision'], 1)
                self.assertEqual(self.raw(cid)['status'], 'paused' if cid == paused else 'active')
                self.assertTrue(self.backup_path(cid).is_file())

    def test_a_retry_replays_and_a_new_op_id_is_already_upgraded(self):
        self.ok(UPGRADE, cid=self.old)
        before = self.record_path(self.old).read_bytes()
        again = self.ok(UPGRADE, cid=self.old)
        self.assertEqual((again['replayed'], again['changed']), (True, False))
        self.assertEqual(self.record_path(self.old).read_bytes(), before)
        self.refused({**UPGRADE, 'op_id': 'upgrade-002'}, 'already-upgraded', cid=self.old)

    def test_a_crash_between_the_backup_and_the_save_is_recoverable(self):
        before = self.record_path(self.old).read_bytes()
        with patch.object(cycle_ops, 'save', side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError):
                cycle_ops.run(self.repo, self.old, UPGRADE)
        self.assertEqual(self.backup_path().read_bytes(), before)
        self.assertEqual(self.record_path(self.old).read_bytes(), before)
        done = self.ok(UPGRADE, cid=self.old)
        self.assertTrue(done['changed'])
        self.assertEqual(self.backup_path().read_bytes(), before)
        self.assertEqual(self.raw()['schema_version'], 3)


class BoundaryTests(UpgradeBase):
    def test_events_before_the_upgrade_have_no_revision_and_later_ones_do(self):
        mutate(self.repo, self.old, 'checks', checks=['unit'])
        self.ok(UPGRADE, cid=self.old)
        mutate(self.repo, self.old, 'checks', checks=['unit', 'lint'])
        history = self.raw()['history']
        mark = [e['action'] for e in history].index('upgraded')
        self.assertTrue(mark > 0)
        self.assertTrue(all('revision' not in e for e in history[:mark]))
        self.assertEqual([e['revision'] for e in history[mark:]], [1, 2])
        # The stale-revision listing counts events whose revision exceeds the caller's; it can name none from before the upgrade.
        listed = [e['action'] for e in history if e.get('revision', 0) > 1]
        self.assertEqual(listed, ['checks'])

    def test_a_lost_legacy_attempts_partial_commit_stays_outside_the_first_base_and_reconcile_proposes_it(self):
        self.start_legacy()
        (self.repo / 'src/a.py').write_text('answer = 5\n')
        self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', f'partial\n\nCycle: {self.old}\nCycle-Task: build-it')
        partial = self.git('rev-parse', 'HEAD')
        mutate(self.repo, self.old, 'assignment', id='build-it', state='lost', note='the host reported the agent terminated')
        mutate(self.repo, self.old, 'task', task_id='build-it', state='pending')
        self.ok(UPGRADE, cid=self.old)
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code',
                            'assignment_text': 'Finish the answer.\n'}, cid=self.old)
        self.assertEqual(prepared['base'], partial)
        self.assertNotIn(partial, [c for c in cycle_ops.trailer_commits(cycle_ops.tree(self.repo), prepared['base'], 'build-it')])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cycle.main(['--repo-root', str(self.repo), 'reconcile', self.old])
        report = json.loads(out.getvalue())
        self.assertIn(partial, json.dumps(report['discrepancies']))
        self.assertIn('linked-commit-not-recorded', json.dumps(report['discrepancies']))


class ContinuationTests(UpgradeBase):
    def test_completed_work_survives_and_the_remaining_flow_reaches_completion(self):
        cid = self.old
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', 'set the answer\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        evidence = self.repo / f'bionic/cycles/{cid}/build-evidence.md'
        evidence.write_text('the unit check passed\n')
        mutate(self.repo, cid, 'task', task_id='build-it', state='done', commits=[sha], stage='integrated', evidence=[f'cycles/{cid}/build-evidence.md'])
        self.ok(UPGRADE, cid=cid)
        task = self.raw()['plan']['tasks'][0]
        self.assertEqual((task['status'], task['commits'], task['evidence']), ('done', [sha], [f'cycles/{cid}/build-evidence.md']))
        self.cid = cid
        self.to_reflect()
        seen = self.ok({'op': 'inspect'}, cid=cid)
        self.assertEqual((seen['phase'], seen['unmet']['completion'], seen['schema_version']), ('reflect', [], 3))
        finish = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'finish'][0]
        done = self.ok({**finish['request'], 'op_id': 'finish-001', 'lessons': ['upgrade kept the work'], 'remaining': ['none']}, cid=cid)
        self.assertEqual((done['status'], done['completion']['tip']), ('completed', sha))
        doc = self.raw()
        self.assertEqual(doc['plan']['tasks'][0]['commits'], [sha])
        self.assertEqual([op['op'] for op in doc['operations']], ['upgrade', 'finish'])


class RecoveryAndRollbackTests(UpgradeBase):
    def test_recovery_requests_validate_against_the_operation_schema(self):
        refusal = self.refused({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'x', 'attempt': 1, 'handle': 'h'}, 'needs-upgrade', cid=self.old)
        actions = list(refusal['errors'][0]['recovery']) + [a for a in self.ok({'op': 'inspect'}, cid=self.old)['actions']]
        self.assertTrue(actions)
        for item in actions:
            request = {**item['request'], 'op_id': 'filled-0001'} if 'op_id' in item['caller_fills'] else item['request']
            self.assertEqual(cycle_ops.schema_errors(request), [], item)

    def test_the_previous_release_schema_reads_version_two_and_rejects_version_three(self):
        from council_records import _validator
        self.assertEqual(hashlib.sha256(PREVIOUS_SCHEMA.read_bytes()).hexdigest(), PREVIOUS_SCHEMA_SHA256,
                         'the 4.9.1 schema fixture changed')
        validator = _validator()
        schema = validator.load_schema(PREVIOUS_SCHEMA)

        def problems(doc):
            errors = []
            validator.validate(doc, schema, '#', '#', errors, 'cycle')
            return errors
        mutate(self.repo, self.old, 'owner-complete', owner=OWNER)
        closed = self.raw()
        self.assertEqual(closed['history'][-1]['owner']['authority'], [])
        self.assertEqual(problems(closed), [])
        other = self.fixture(version=2)
        self.ok(UPGRADE, cid=other)
        self.assertTrue(problems(self.raw(other)), 'the 4.9.1 schema accepted a version-3 record; the rollback limit changed')


if __name__ == '__main__':
    unittest.main()
