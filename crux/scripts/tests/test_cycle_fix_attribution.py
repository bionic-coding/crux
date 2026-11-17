"""Fix-commit attribution: a fix task becomes done only on commits it can be held to.

IDR receipt-interpretation-and-fix-attribution approach 4, tests (iv) to (vi) of approach 7. A fix
commit is admitted on at least one basis: (a) its Cycle-Task trailer names the fix task, (b) it is a
recorded adoption, (c) it is a cycle-record commit that changes fix evidence after the task's first
execution-check. Every refusal pairs with the records-only delivery as its positive control.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_hosts
import cycle_workflow as workflow
from test_cycle_fix_step import FixBase


class FixAttributionBase(FixBase):
    counter = 0

    def setUp(self):
        super().setUp()
        # Fixture files at the root and the receipt store stay out of git, so the checkout reads clean.
        (self.root / '.gitignore').write_text('/evidence/\n/*.json\n__pycache__/\n*.lock\n')
        self.git('add', '.gitignore')
        self.git('commit', '-qm', 'ignore fixture files')

    def op(self, request, cid):
        type(self).counter += 1
        request = {'op_id': f'{request["op"]}-{type(self).counter:06d}', **request}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.root), 'op', cid, '--json', json.dumps(request)])
        return code, json.loads(out.getvalue())

    def op_ok(self, request, cid):
        code, response = self.op(request, cid)
        self.assertEqual(code, 0, response)
        return response

    def head(self):
        return self.git('rev-parse', 'HEAD')

    def evidence(self, cid, name, text='fix evidence\n'):
        path = self.root / 'bionic/cycles' / cid / 'evidence' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def commit_record(self, cid):
        response = self.op_ok({'op': 'commit-record'}, cid)
        self.assertTrue(response['changed'], response)
        return response['commit']

    def changed(self, sha):
        return self.git('diff-tree', '--no-commit-id', '--name-only', '-r', sha).splitlines()

    def review_fix_task(self, mode='blocking'):
        """A Review fix, dispatched to a dev-lead; returns the cycle id and the prepared attempt."""
        cid = self.to_review(blocking=1)
        self.add_fix(cid, 'review')
        self.commit_record(cid)
        prepared = self.op_ok({'op': 'prepare-dispatch', 'task_id': 'fix-1', 'host': 'claude-code', 'mode': mode}, cid)
        return cid, prepared

    def check(self, cid, prepared):
        return self.op_ok({'op': 'execution-check', 'assignment': prepared['assignment'], 'attempt': prepared['attempt']}, cid)

    def deliver(self, cid, prepared, commits):
        lines = [f'Assignment: {prepared["assignment"]}', f'Attempt: {prepared["attempt"]}', '', 'Outcome: DONE.',
                 cycle_hosts.marker(prepared['assignment'], prepared['attempt'], prepared.get('delivery_token'))]
        Path(prepared['result_path']).write_text('\n'.join(lines) + '\n')
        return self.op({'op': 'deliver', 'assignment': prepared['assignment'], 'attempt': prepared['attempt'],
                        'outcome': 'done', 'commits': commits}, cid)

    def refused_unattributed(self, cid, prepared, sha):
        record = (self.root / 'bionic/cycles' / cid / 'cycle.json').read_bytes()
        code, response = self.deliver(cid, prepared, [sha])
        self.assertEqual(code, 1, response)
        self.assertEqual([e['code'] for e in response['errors']], ['fix-commit-unattributed'])
        problem = response['errors'][0]['problem']
        self.assertIn(sha[:12], problem)
        self.assertIn('git log -1 -- PATH', problem)
        self.assertEqual((self.root / 'bionic/cycles' / cid / 'cycle.json').read_bytes(), record, 'a refusal wrote the record')

    def records_only_fix(self, cid, prepared):
        """Act as the dev-lead of a records-only fix: receipts on the evidence file, commit-record, fix-diff review."""
        note = self.evidence(cid, 'review/fix-note.md', 'bad\n')
        rel = note.relative_to(self.root).as_posix()
        decl = {'check_id': 'records', 'inputs': [rel], 'environment': [],
                'command': [sys.executable, '-c', f"from pathlib import Path; assert Path('{rel}').read_text() == 'good\\n'"]}
        before = workflow_execute(self.root, decl)
        self.assertEqual(before['status'], 'failed')
        note.write_text('good\n')
        sha = self.commit_record(cid)
        after = workflow_execute(self.root, decl)
        self.assertEqual(after['status'], 'passed')
        self.ok('task', cid, '--task-id', 'fix-1', '--commit', sha, '--fix-before', before['id'], '--fix-after', after['id'])
        self.ok('review', cid, '--file', self.write_json('fix-review.json', self.report_dict(fix_task='fix-1', reviewer='second')))
        return sha


def workflow_execute(root, decl):
    from test_evidence import execute
    return execute(root, decl)['evidence']


class RecordsOnlyFixTests(FixAttributionBase):
    def test_iv_a_records_only_review_fix_delivers_done_on_its_commit_record_commit(self):
        cid, prepared = self.review_fix_task()
        self.check(cid, prepared)
        sha = self.records_only_fix(cid, prepared)
        self.assertIn(f'bionic/cycles/{cid}/evidence/review/fix-note.md', self.changed(sha))
        self.assertNotIn('Cycle-Task', self.git('log', '-1', '--format=%B', sha))
        code, response = self.deliver(cid, prepared, [sha])
        self.assertEqual(code, 0, response)
        self.assertEqual((response['status'], response['untrailered_commits']), ('done', [sha]))
        rows = {row['sha']: row for row in response['execution']['commits']}
        self.assertEqual(rows[sha]['kind'], 'bookkeeping')
        task = self.task_of(workflow.load(self.root, cid))
        self.assertEqual((task['status'], task['commits']), ('done', [sha]))

    def test_v_dispatch_and_attach_record_commits_that_swept_evidence_are_refused(self):
        cid = self.to_review(blocking=1)
        self.add_fix(cid, 'review')
        self.commit_record(cid)
        self.evidence(cid, 'review/swept-at-prepare.md')
        prepared = self.op_ok({'op': 'prepare-dispatch', 'task_id': 'fix-1', 'host': 'claude-code', 'mode': 'background'}, cid)
        prepare_commit = prepared['record_commit']['commit']
        self.assertIn(f'bionic/cycles/{cid}/evidence/review/swept-at-prepare.md', self.changed(prepare_commit))
        self.evidence(cid, 'review/swept-at-attach.md')
        attached = self.op_ok({'op': 'attach-execution', 'assignment': prepared['assignment'], 'attempt': prepared['attempt'],
                               'handle': 'agent-fix'}, cid)
        attach_commit = attached['record_commit']['commit']
        self.assertIn(f'bionic/cycles/{cid}/evidence/review/swept-at-attach.md', self.changed(attach_commit))
        checked = self.check(cid, prepared)
        self.assertEqual(checked['execution']['execution_head'], attach_commit)
        check_commit = checked['record_commit']['commit']
        self.assertFalse([p for p in self.changed(check_commit) if '/evidence/' in p])
        sha = self.records_only_fix(cid, prepared)
        for unattributed in (prepare_commit, attach_commit, check_commit):
            with self.subTest(unattributed):
                self.refused_unattributed(cid, prepared, unattributed)
        # Positive control: the same attempt delivers on its commit-record commit.
        code, response = self.deliver(cid, prepared, [sha])
        self.assertEqual(code, 0, response)

    def test_v_an_untrailered_source_commit_is_refused_and_a_trailered_one_completes(self):
        cid, prepared = self.review_fix_task()
        self.check(cid, prepared)
        records = self.records_only_fix(cid, prepared)
        untrailered = self.fix_source(trailer=False)
        self.refused_unattributed(cid, prepared, untrailered)
        # (vi) and the positive control: a trailered source commit, with the records commit, completes.
        self.git('commit', '--allow-empty', '-qm', 'fix b\n\nCycle-Task: fix-1')
        trailered = self.head()
        code, response = self.deliver(cid, prepared, [records, trailered])
        self.assertEqual(code, 0, response)
        self.assertEqual(response['untrailered_commits'], [records])

    def test_v_a_fix_with_no_commit_keeps_its_refusal(self):
        cid, prepared = self.review_fix_task()
        self.check(cid, prepared)
        code, response = self.deliver(cid, prepared, [])
        self.assertEqual(code, 1, response)
        self.assertIn('at least one commit', response['errors'][0]['problem'])


class RecordsCommitRuleTests(FixAttributionBase):
    """Basis (c) on commits whose paths the writer itself writes, compared as whole path components."""

    def setUp(self):
        super().setUp()
        self.cid = self.to_test()
        self.commit_record(self.cid)
        self.anchor = self.head()
        self.cfg = workflow.tree(self.root)
        self.doc = workflow.load(self.root, self.cid)

    def commit_paths(self, *names, message='writer commit'):
        for name in names:
            path = self.root / 'bionic/cycles' / self.cid / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'{name}\n')
            self.git('add', '-f', str(path))
        self.git('commit', '-qm', message)
        return self.head()

    def admitted(self, sha, anchor=None):
        return workflow.records_fix_commit(self.cfg, self.doc, sha, anchor or self.anchor)

    def test_writer_written_and_record_only_commits_are_refused_and_fix_evidence_is_admitted(self):
        refused = {
            'record and execution proof only': ('cycle.json', 'execution/0000.json'),
            'friction log only': ('evidence/friction.md',),
            'hand-back resume': ('cycle.json', 'invocations/0000.json', 'evidence/resumed-results/fix-1-1-token.md'),
            'release ledger': ('evidence/release/ledger.json',),
        }
        for name, paths in refused.items():
            with self.subTest(name):
                self.assertFalse(self.admitted(self.commit_paths(*paths)))
        # Positive control in the same window: a fix evidence file beside the record.
        self.assertTrue(self.admitted(self.commit_paths('cycle.json', 'evidence/review/fix.md')))

    def test_prefixes_compare_whole_components(self):
        self.assertTrue(self.admitted(self.commit_paths('evidence/release-notes/fix.md')))
        self.assertTrue(self.admitted(self.commit_paths('evidence/friction.md.bak')))
        self.assertFalse(self.admitted(self.commit_paths('evidence/release/notes.md')))

    def test_a_commit_outside_the_cycle_directory_or_before_the_anchor_is_refused(self):
        (self.root / 'src/c.txt').write_text('c')
        self.git('add', 'src/c.txt')
        mixed = self.commit_paths('evidence/review/fix.md', message='mixed')
        self.assertFalse(self.admitted(mixed))
        later = self.commit_paths('evidence/review/later.md')
        self.assertTrue(self.admitted(later))
        self.assertFalse(self.admitted(later, anchor=later), 'the anchor itself is no proper descendant')
        self.assertFalse(workflow.records_fix_commit(self.cfg, self.doc, later, None), 'no execution-check, no window')

    def test_the_anchor_is_the_first_execution_check_of_this_task_in_this_pass(self):
        history = [{'action': 'execution-check', 'task': 'other', 'pass': 1, 'execution_head': 'a' * 40},
                   {'action': 'execution-check', 'task': 'fix-1', 'pass': 0, 'execution_head': 'b' * 40},
                   {'action': 'attach-execution', 'task': 'fix-1', 'pass': 1},
                   {'action': 'execution-check', 'task': 'fix-1', 'pass': 1, 'execution_head': 'c' * 40},
                   {'action': 'execution-check', 'task': 'fix-1', 'pass': 1, 'execution_head': 'd' * 40}]
        self.assertEqual(workflow.fix_window_anchor({'pass': 1, 'history': history}, 'fix-1'), 'c' * 40)
        self.assertIsNone(workflow.fix_window_anchor({'pass': 1, 'history': history[:3]}, 'fix-1'))


class AdoptedFixTests(FixAttributionBase):
    def test_b_an_untrailered_adopted_commit_completes_the_fix(self):
        cid = self.to_test()
        before = self.record('regress')
        self.ok('task-add', cid, '--file', self.write_json('early.json', self.task('test', identity='early')))
        source = self.fix_source(task='early')
        self.ok('task', cid, '--task-id', 'early', '--commit', source, '--state', 'done')
        doc = workflow.load(self.root, cid)
        doc['pass'] = doc['pass_limit'] = 2
        (self.root / 'bionic/cycles' / cid / 'cycle.json').write_text(json.dumps(doc))
        self.add_fix(cid, 'test')
        self.assertNotIn('Cycle-Task: fix-1', self.git('log', '-1', '--format=%B', source))
        after = self.record('regress')
        self.ok('task', cid, '--task-id', 'fix-1', '--adopt-commit', source, '--fix-before', before['id'], '--fix-after', after['id'])
        done = self.ok('task', cid, '--task-id', 'fix-1', '--state', 'done')
        self.assertEqual(self.task_of(done)['status'], 'done')

    def test_b_the_same_commit_without_the_adoption_is_refused(self):
        cid = self.to_test()
        before = self.record('regress')
        self.add_fix(cid, 'test')
        source = self.fix_source(task='early')
        after = self.record('regress')
        self.ok('task', cid, '--task-id', 'fix-1', '--commit', source, '--fix-before', before['id'], '--fix-after', after['id'])
        self.assertIn('fix-commit-unattributed', self.refused('task', cid, '--task-id', 'fix-1', '--state', 'done'))


if __name__ == '__main__':
    unittest.main()
