"""Autonomous council settlement: nit dispositions, delta review, the shared attempt count, and the rounds display.

Fixture records only. No council is convened and no model is called: attempts come from `begin_mode` with the
git commit stubbed, and council records are written sealed, as the owning writer would write them.
"""
import json
import re
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_policy as policy
import cycle_council
import cycle_ops
import cycle_progress
from cycle_workflow import CycleError, council_state, digest, load, mutate, tree
from test_cycle_withdraw_decision import WithdrawBase, contents

PROVIDERS = ('openai', 'anthropic', 'google')


def finding(fid, kind='nit'):
    return {'id': fid, 'kind': kind, 'text': 'text ' + fid}


class SettlementBase(WithdrawBase):
    def setUp(self):
        super().setUp()
        patcher = patch('cycle_council.commit_evidence')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cid = self.new_cycle('iterate')
        self.plan(self.cid)
        self.attempts(self.cid, 'warmup', 0, limit=3)

    def revision(self, name='choice', replaces=None, **change):
        body = contents(**{k: v for k, v in change.items() if v is not None})
        if replaces:
            body['replaces'] = replaces
        for key in [k for k, v in change.items() if v is None]:
            body.pop(key, None)
        doc = mutate(self.repo, self.cid, 'decision', kind='idr', name=name, contents=body)
        return doc, doc['decisions'][-1]['path']

    def begin(self, subject, progress=None, question='Judge the decision.'):
        return cycle_council.begin_mode(self.repo, 'idr', subject, question, cycle_id=self.cid, progress=progress)

    def record_for(self, attempt_path, attempt, seats, architect, subject):
        cfg = tree(self.repo)
        value = {'format': policy.RECORD, 'id': attempt['id'], 'purpose': 'idr', 'logical_id': attempt['logical_id'],
                 'subject': subject, 'subject_sha256': digest((cfg.docs_root / subject).read_bytes()), 'cycle_id': self.cid,
                 'at': '2026-10-31T00:00:00+00:00', 'attempt': attempt_path.relative_to(cfg.docs_root).as_posix(),
                 'policy': attempt['policy'], 'outcome': 'changes-required', 'seats': seats, 'passes': [], 'architect': architect,
                 'binding_failures': [], 'reason': None}
        value['outcome'] = policy.evaluate(value)
        out = attempt_path.with_name('council-' + attempt['id'] + '.json')
        out.write_text(json.dumps(policy.seal(value)))
        attempt['status'] = 'finished'
        attempt['record'] = out.relative_to(cfg.docs_root).as_posix()
        attempt_path.write_text(json.dumps(attempt))
        return out.relative_to(cfg.docs_root).as_posix()

    def seats(self, decisions=('APPROVE', 'APPROVE', 'APPROVE'), nits=None):
        rows = []
        for provider, decision in zip(PROVIDERS, decisions):
            found = [finding(f'{provider}:{n}') for n in (nits or {}).get(provider, ())]
            rows.append({'provider': provider, 'decision': decision, 'errored': False, 'findings': found})
        return rows

    def agreement(self, subject, **extra):
        sha = digest((tree(self.repo).docs_root / subject).read_bytes())
        return {'agrees': True, 'subject_sha256': sha, 'rationale': 'The seats approve the exact revision.', 'dissent': [], **extra}


class NitDispositionTests(SettlementBase):
    def settled(self, nits, dispositions):
        doc, subject = self.revision()
        self.rounds = getattr(self, 'rounds', 0) + 1
        cfg, path, attempt, _ = self.begin(subject, progress=None if self.rounds == 1 else f'try {self.rounds}')
        rel = self.record_for(path, attempt, self.seats(nits=nits), None, subject)
        out = policy.disposition(self.repo, rel, self.agreement(subject, nits=dispositions))
        return rel, subject, out

    def test_all_nits_approving_attempt_records_approval_and_dispositions_with_no_further_attempt(self):
        rel, subject, out = self.settled({'anthropic': ['F1', 'F2']}, [
            {'id': 'anthropic:F1', 'disposition': 'apply-in-build', 'note': 'Build note'},
            {'id': 'anthropic:F2', 'disposition': 'declined', 'note': 'out of scope for this change'}])
        self.assertEqual(out['outcome'], 'approved')
        record = json.loads((tree(self.repo).docs_root / rel).read_text())
        self.assertEqual(record['architect']['subject_sha256'], record['subject_sha256'])
        self.assertEqual([n['id'] for n in record['architect']['nits']], ['anthropic:F1', 'anthropic:F2'])
        # One attempt exists and approval needs no second one: the vote rule excludes a nit-only seat from dissent.
        self.assertEqual(len(council_state(tree(self.repo), load(self.repo, self.cid), 'choice')['attempts']), 1)
        self.assertEqual(policy.evaluate(record), 'approved')

    def test_unanimous_approve_with_nits_needs_the_agreement_to_name_each_nit(self):
        with self.assertRaisesRegex(CycleError, 'nit.*anthropic:F2'):
            self.settled({'anthropic': ['F1', 'F2']}, [{'id': 'anthropic:F1', 'disposition': 'apply-in-build', 'note': 'n'}])

    def test_a_declined_nit_names_its_reason(self):
        with self.assertRaisesRegex(CycleError, 'declined.*reason'):
            self.settled({'anthropic': ['F1']}, [{'id': 'anthropic:F1', 'disposition': 'declined'}])

    def test_a_disposition_for_an_unknown_nit_or_with_an_unknown_value_is_refused(self):
        with self.assertRaisesRegex(CycleError, 'unknown nit'):
            self.settled({'anthropic': ['F1']}, [{'id': 'anthropic:F1', 'disposition': 'apply-in-build', 'note': 'n'},
                                                  {'id': 'anthropic:F9', 'disposition': 'apply-in-build', 'note': 'n'}])
        with self.assertRaisesRegex(CycleError, 'disposition'):
            self.settled({'anthropic': ['F1']}, [{'id': 'anthropic:F1', 'disposition': 'later', 'note': 'n'}])

    def test_a_record_without_nits_needs_no_disposition_list(self):
        rel, subject, out = self.settled({}, [])
        self.assertEqual(out['outcome'], 'approved')

    def test_strict_and_lite_records_name_nits_the_same_way(self):
        strict = {'policy': {'mode': 'strict'}, 'seats': self.seats(nits={'openai': ['F1']}), 'passes': []}
        lite = {'policy': {'mode': 'lite'}, 'seats': [], 'passes': [
            {'pass': 'challenge', 'vote': {'findings': []}},
            {'pass': 'final', 'vote': {'findings': [finding('final:F1'), finding('final:F2', 'blocking')]}}]}
        self.assertEqual(policy.nit_ids(strict), ['openai:F1'])
        self.assertEqual(policy.nit_ids(lite), ['final:F1'])

    def test_standard_two_of_three_with_one_dissent_settles_with_recorded_architect_agreement(self):
        doc, subject = self.revision()
        cfg, path, attempt, _ = self.begin(subject)
        seats = self.seats(('APPROVE', 'REQUEST_CHANGES', 'APPROVE'))
        seats[1]['findings'] = [finding('anthropic:B1', 'blocking')]
        rel = self.record_for(path, attempt, seats, None, subject)
        self.assertEqual(json.loads((cfg.docs_root / rel).read_text())['outcome'], 'changes-required')
        agreement = self.agreement(subject, dissent=[{'provider': 'anthropic', 'kind': 'accepted-tradeoff', 'explanation': 'The cost is accepted.'}])
        self.assertEqual(policy.disposition(self.repo, rel, agreement)['outcome'], 'approved')
        record = json.loads((cfg.docs_root / rel).read_text())
        self.assertEqual(record['architect']['dissent'][0]['kind'], 'accepted-tradeoff')


class DeltaReviewTests(SettlementBase):
    def two_revisions(self):
        doc, first = self.revision(notes=['old'], extra=['gone'])
        cfg, path, attempt, _ = self.begin(first)
        rel = self.record_for(path, attempt, self.seats(), None, first)
        policy.disposition(self.repo, rel, self.agreement(first))
        mutate(self.repo, self.cid, 'approve-decision', subject=first, approval=rel)
        doc, second = self.revision(approach=['changed'], extra=None, risks=['new'], notes=['old'])
        return first, second

    def test_a_first_revision_carries_no_delta(self):
        doc, subject = self.revision()
        cfg, path, attempt, _ = self.begin(subject)
        self.assertNotIn('delta', attempt)

    def test_a_revision_of_an_approved_name_carries_a_computed_delta_and_the_full_revision(self):
        first, second = self.two_revisions()
        cfg, path, attempt, data = self.begin(second, progress='answers the first review')
        self.assertEqual(attempt['delta']['keys'], {'approach': 'changed', 'extra': 'removed', 'risks': 'added'})
        self.assertEqual(attempt['delta']['base']['path'], first)
        self.assertEqual(attempt['delta']['new']['path'], second)
        self.assertEqual(data, (cfg.docs_root / second).read_bytes())  # the council reviews the full new revision
        for line in ('approach: changed', 'extra: removed', 'risks: added'):
            self.assertIn(line, attempt['question'])
        self.assertIn('Judge the change', attempt['question'])
        self.assertNotIn('alternatives: changed', attempt['question'])  # an unchanged key is not marked
        self.assertEqual(attempt['round'], 2)  # a delta attempt counts toward the same limit

    def approved_delta_record(self, second):
        cfg, path, attempt, _ = self.begin(second, progress='answers the first review')
        rel = self.record_for(path, attempt, self.seats(), None, second)
        policy.disposition(self.repo, rel, self.agreement(second))
        return path, attempt, rel

    def test_approval_binds_the_new_revision_sha256(self):
        first, second = self.two_revisions()
        path, attempt, rel = self.approved_delta_record(second)
        doc = mutate(self.repo, self.cid, 'approve-decision', subject=second, approval=rel)
        record = json.loads((tree(self.repo).docs_root / rel).read_text())
        self.assertEqual(record['subject_sha256'], digest((tree(self.repo).docs_root / second).read_bytes()))
        self.assertEqual(doc['decisions'][-1]['approval'], rel)

    def test_a_stale_stored_delta_is_refused_at_approve_decision(self):
        first, second = self.two_revisions()
        path, attempt, rel = self.approved_delta_record(second)
        stored = json.loads(path.read_text())
        stored['delta']['keys']['approach'] = 'added'
        path.write_text(json.dumps(stored))
        with self.assertRaisesRegex(CycleError, 'stale delta'):
            mutate(self.repo, self.cid, 'approve-decision', subject=second, approval=rel)

    def test_a_base_revision_changed_after_convening_is_refused(self):
        first, second = self.two_revisions()
        path, attempt, rel = self.approved_delta_record(second)
        base = tree(self.repo).docs_root / first
        base.write_text(base.read_text().replace('gone', 'other'))
        with self.assertRaises(CycleError):
            mutate(self.repo, self.cid, 'approve-decision', subject=second, approval=rel)

    def test_convening_refuses_a_delta_that_no_longer_matches_the_revisions(self):
        first, second = self.two_revisions()
        stale = cycle_council.delta_for(tree(self.repo), 'idr', second, self.cid)
        stale['keys']['approach'] = 'added'
        with self.assertRaisesRegex(CycleError, 'stale delta'):
            cycle_council.begin_mode(self.repo, 'idr', second, 'Judge.', cycle_id=self.cid, progress='p', expected_delta=stale)


class AttemptCountTests(SettlementBase):
    def test_the_limit_refusal_names_withdraw_decision_and_no_owner_action(self):
        doc, subject = self.revision()
        self.attempts(self.cid, 'choice', 3, limit=3)
        with self.assertRaises(CycleError) as raised:
            self.begin(subject, progress='new progress')
        text = str(raised.exception)
        self.assertIn('withdraw-decision', text)
        for word in ('owner', 'extension', 'extend'):
            self.assertNotIn(word, text.lower())

    def test_the_extension_parameter_keeps_working(self):
        doc, subject = self.revision()
        self.attempts(self.cid, 'choice', 3, limit=3)
        with self.assertRaisesRegex(CycleError, 'extension'):
            cycle_council.begin_mode(self.repo, 'idr', subject, 'q', cycle_id=self.cid, progress='p', extension=5)

    def replacement(self):
        self.plan(self.cid, extra=('dep',))
        doc, old = self.revision('choice')
        self.attempts(self.cid, 'choice', 2, limit=3)
        self.withdraw(self.cid, 'choice', tasks=('dep',))
        doc, new = self.revision('narrow', replaces='choice')
        return old, new

    def test_a_replacements_first_attempt_is_numbered_after_the_withdrawn_records_last(self):
        old, new = self.replacement()
        cfg, path, attempt, _ = self.begin(new)
        self.assertEqual(attempt['round'], 3)
        self.assertEqual(len(attempt['history']), 2)
        path.write_text(json.dumps({**attempt, 'status': 'finished'}))
        with self.assertRaisesRegex(CycleError, 'withdraw-decision'):
            self.begin(new, progress='another try')

    def test_an_attempt_on_a_withdrawn_name_is_refused(self):
        old, new = self.replacement()
        with self.assertRaisesRegex(CycleError, 'withdrawn'):
            self.begin(old, progress='again')

    def test_council_state_and_the_council_writer_share_one_count(self):
        old, new = self.replacement()
        cfg = tree(self.repo)
        doc = load(self.repo, self.cid)
        with patch.object(cycle_council, 'idr_history', wraps=cycle_council.idr_history) as shared:
            state = council_state(cfg, doc, 'narrow')
        shared.assert_called_once()
        self.assertEqual(len(state['attempts']), 2)
        self.assertEqual([r['id'] for r in state['attempts']], [r['id'] for r in cycle_council.idr_history(cfg, doc, 'narrow')])


class RoundsTests(SettlementBase):
    def test_rounds_show_attempt_outcome_and_reason(self):
        doc, subject = self.revision()
        cfg, path, attempt, _ = self.begin(subject)
        self.record_for(path, attempt, self.seats(('APPROVE', 'REQUEST_CHANGES', 'APPROVE')), None, subject)
        cfg, path2, attempt2, _ = self.begin(subject, progress='answers F1 and F2')
        seats = self.seats(('APPROVE', 'REQUEST_CHANGES', 'APPROVE'))
        seats[1]['findings'] = [finding('anthropic:B1', 'blocking')]
        rel2 = self.record_for(path2, attempt2, seats, None, subject)
        policy.disposition(self.repo, rel2, self.agreement(subject, dissent=[{'provider': 'anthropic', 'kind': 'accepted-tradeoff', 'explanation': 'accepted'}]))
        out = self.inspect(self.cid)
        rows = out['councils']['choice']
        self.assertEqual([r['round'] for r in rows], [1, 2])
        self.assertEqual([r['attempt'] for r in rows], [attempt['id'], attempt2['id']])
        self.assertEqual(rows[0]['reason'], 'initial')
        self.assertEqual(rows[1]['reason'], 'answers F1 and F2')
        self.assertEqual(rows[1]['outcome'], 'architect-settled')
        self.assertNotEqual(rows[0]['outcome'], 'architect-settled')

    def test_a_delta_attempt_shows_delta_revision(self):
        first, second = DeltaReviewTests.two_revisions(self)
        self.begin(second, progress='folds the nits')
        rows = self.inspect(self.cid)['councils']['choice']
        self.assertTrue(rows[-1]['reason'].startswith('delta revision'))
        self.assertIn('folds the nits', rows[-1]['reason'])

    def test_cycle_status_renders_the_rounds(self):
        doc, subject = self.revision()
        cfg, path, attempt, _ = self.begin(subject)
        path.write_text(json.dumps({**attempt, 'status': 'finished'}))
        self.begin(subject, progress='answers B1')
        text = cycle_progress.render(cycle_progress.view(self.repo, self.cid))
        self.assertIn('Council choice', text)
        self.assertIn('initial', text)
        self.assertIn('answers B1', text)

    def test_a_v2_record_with_nits_and_no_agreement_is_reported(self):
        doc, subject = self.revision()
        cfg, path, attempt, _ = self.begin(subject)
        rel = self.record_for(path, attempt, self.seats(nits={'anthropic': ['F1']}), None, subject)
        doc = load(self.repo, self.cid)
        ref = dict(doc['decisions'][-1], approval=rel)
        self.assertEqual(cycle_ops.nit_gaps(cfg, doc, ref), ['anthropic:F1'])


class AwaitingArchitectTests(SettlementBase):
    def finish(self, seats):
        doc, subject = self.revision()
        self.rounds = getattr(self, 'rounds', 0) + 1
        cfg, path, attempt, _ = self.begin(subject, progress=None if self.rounds == 1 else f'try {self.rounds}')
        record = cycle_council.base_record(cfg, path, attempt)
        record['seats'] = seats
        record['outcome'] = policy.evaluate(record)
        return cfg, cycle_council.finish_mode(cfg, path, attempt, record)

    def test_approve_with_nits_and_no_agreement_reports_awaiting_architect_and_the_command(self):
        cfg, result = self.finish(self.seats(nits={'anthropic': ['F1']}))
        self.assertEqual(result['outcome'], 'awaiting-architect')
        sealed = json.loads((cfg.docs_root / result['record']).read_text())
        self.assertEqual(sealed['outcome'], 'changes-required', 'the sealed record keeps its schema value')
        command = result['next_command']
        self.assertRegex(command, r'^uv run \S+/scripts/cycle-council\.py --repo-root \S+ --architect PATH --record ' + re.escape(result['record']) + '$')
        self.assertTrue(Path(command.split()[2]).is_file())

    def test_the_printed_command_quotes_paths_that_hold_a_space_or_a_metacharacter(self):
        import shlex
        repo = '/tmp/a repo; $(x)'
        record = "adrs/councils/it's here/attempt-1.json"
        argv = shlex.split(cycle_council.architect_command(repo, record))
        self.assertEqual(argv[:2], ['uv', 'run'])
        self.assertTrue(argv[2].endswith('/scripts/cycle-council.py'))
        self.assertEqual(argv[3:], ['--repo-root', repo, '--architect', 'PATH', '--record', record])

    def test_a_binding_failure_or_one_approval_stays_changes_required(self):
        bound = self.seats(nits={'anthropic': ['F1']})
        bound[0]['findings'].append(dict(finding('openai:B', 'blocking'), binding_failure=True))
        one = self.seats(decisions=('APPROVE', 'REQUEST_CHANGES', 'REQUEST_CHANGES'))
        for seats in (bound, one):
            self.assertEqual(self.finish(seats)[1]['outcome'], 'changes-required')

    def test_the_cli_exits_one_and_names_path_in_the_architect_help(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('cycle_council_cli', Path(__file__).resolve().parents[1] / 'cycle-council.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch('cycle_council.convene', return_value={'outcome': 'awaiting-architect'}), patch('sys.stdout'):
            code = cli.main(['--purpose', 'idr', '--subject', 's', '--question', __file__])
        self.assertEqual(code, 1)
        import io, contextlib
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), self.assertRaises(SystemExit):
            cli.main(['--help'])
        self.assertRegex(buffer.getvalue(), r'--architect PATH\s+PATH to a JSON file')


if __name__ == '__main__':
    unittest.main()
