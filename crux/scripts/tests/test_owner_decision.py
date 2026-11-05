"""Explicit owner evidence binds a shown revision; recording never invents intent."""
import contextlib
from datetime import datetime
import io
import json
import multiprocessing
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
from cycle_workflow import CycleError, create, digest, encoded, load, mutate, tree
import test_cycle_workflow as fixtures
import test_cycle_decision_policy as adr_fixtures
import decision_policy as dp
import test_cycle_simplify as simplify_fixtures


def decision_worker(repo, operation, request, announced, gate, release, results, hold=False):
    """A real process holds the production flock across the controlled mutation boundary."""
    import owner_decision as owner
    announced.set()
    name = 'save' if operation == 'apply' else 'atomic'
    original = getattr(owner, name)
    def holding(*args, **kwargs):
        if hold:
            gate.set()
            if not release.wait(10):
                raise RuntimeError('test coordination expired')
        return original(*args, **kwargs)
    try:
        with patch.object(owner, name, side_effect=holding):
            value = getattr(owner, operation)(repo, request)
        results.put({'operation': operation, 'ok': True, 'value': value})
    except Exception as exc:
        results.put({'operation': operation, 'ok': False, 'code': str(exc)})


class OwnerDecisionTests(unittest.TestCase):
    setUp_base = fixtures.CycleTests.setUp
    cycle = fixtures.CycleTests.cycle
    apply_cycle = fixtures.CycleTests.apply
    plan = fixtures.CycleTests.plan
    idr = fixtures.CycleTests.idr
    # The borrowed plan/idr helpers invoke apply.
    apply = fixtures.CycleTests.apply

    def setUp(self):
        self.setUp_base()
        self.doc = self.idr(self.plan(self.cycle('dev')))
        self.cfg = tree(self.repo)
        self.subject = self.doc['decisions'][-1]['path']
        self.binding = {'purpose': 'idr', 'cycle_id': self.doc['id'], 'subject': self.subject,
                        'subject_sha256': digest((self.cfg.docs_root / self.subject).read_bytes())}

    def owner(self):
        import owner_decision
        return owner_decision

    def presentation(self, ident='present-0001', **changes):
        return self.owner().present(self.repo, {**self.binding, 'op_id': ident,
                    'question': 'Do you approve this exact revision?', **changes})

    def capture_request(self, shown, ident='capture-0001', **changes):
        return {**self.binding, 'op_id': ident, 'presentation': shown['presentation'],
                'disposition': 'approve', 'quote': 'I approve this exact revision.',
                'source': {'kind': 'conversation', 'reference': 'session-1/message-7'},
                'owner_date': '2026-11-01', 'supersedes': None, **changes}

    def capture(self, shown=None, ident='capture-0001', **changes):
        return self.owner().capture(self.repo, self.capture_request(shown or self.presentation(), ident, **changes))

    def application(self, captured, **changes):
        return self.owner().apply(self.repo, {**self.binding, 'capture': captured['capture'], **changes})

    def test_cli_present_capture_apply_retains_verbatim_provenance(self):
        request = {**self.binding, 'op_id': 'present-cli-1', 'question': 'Approve the shown revision?'}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'owner-decision', 'present', '--json', json.dumps(request)])
        self.assertEqual(code, 0, out.getvalue())
        shown = json.loads(out.getvalue())
        quote = "I approve it; keep `these bytes`, $HOME, and this newline.\nExactly."
        captured = self.capture(shown, quote=quote)
        self.assertEqual(captured['record']['quote'], quote)
        self.assertEqual(captured['record']['source'], {'kind': 'conversation', 'reference': 'session-1/message-7'})
        self.assertEqual(captured['record']['subject_sha256'], self.binding['subject_sha256'])
        result = self.application(captured)
        self.assertTrue(result['applied'])
        self.assertFalse(result['already_applied'])
        self.assertEqual(load(self.repo, self.doc['id'])['decisions'][-1]['approval'], captured['capture']['path'])
        self.assertEqual(fixtures.CycleTests.advance(self, load(self.repo, self.doc['id']))['phase'], 'build')

    def test_reject_and_pending_continuation_cannot_apply(self):
        for index, disposition in enumerate(('reject', 'pending')):
            captured = self.capture(ident=f'capture-negative-{index}', disposition=disposition,
                                    quote='No.' if disposition == 'reject' else 'continue',
                                    supersedes=None if index == 0 else captured['capture'])
            with self.assertRaisesRegex(CycleError, 'not-approved'):
                self.application(captured)
        self.assertIsNone(load(self.repo, self.doc['id'])['decisions'][-1]['approval'])

    def test_superseded_approve_cannot_newly_apply(self):
        approved = self.capture()
        self.capture(ident='capture-reject-2', disposition='reject', quote='I reject it.', supersedes=approved['capture'])
        with self.assertRaisesRegex(CycleError, 'superseded'):
            self.application(approved)

    def test_already_applied_acknowledgment_is_truthful_after_rejection(self):
        approved = self.capture()
        first = self.application(approved)
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='I reject it.', supersedes=approved['capture'])
        before = (self.cfg.docs_root / f'cycles/{self.doc["id"]}/cycle.json').read_bytes()
        replay = self.application(approved)
        self.assertTrue(replay['already_applied'])
        self.assertEqual(replay['application'], first['application'])
        self.assertEqual(replay['current_capture'], rejected['capture'])
        self.assertEqual(replay['current_disposition'], 'reject')
        self.assertFalse(replay['lifecycle_changed'])
        self.assertEqual(before, (self.cfg.docs_root / f'cycles/{self.doc["id"]}/cycle.json').read_bytes())

    def test_exact_replay_and_conflicting_replay(self):
        shown = self.presentation()
        self.assertEqual(self.presentation()['presentation'], shown['presentation'])
        with self.assertRaisesRegex(CycleError, 'operation-conflict'):
            self.presentation(question='Different question')
        approved = self.capture(shown)
        self.assertEqual(self.capture(shown)['capture'], approved['capture'])
        with self.assertRaisesRegex(CycleError, 'operation-conflict'):
            self.capture(shown, quote='Different owner words')
        first = self.application(approved)
        second = self.application(approved)
        self.assertEqual(first['application'], second['application'])
        self.assertTrue(second['already_applied'])
        self.assertEqual(sum(e['action'] == 'owner-decision-applied' for e in load(self.repo, self.doc['id'])['history']), 1)

    def test_pending_capture_requires_explicit_disposition_and_actual_source(self):
        shown = self.presentation()
        for changes in [{'source': {'kind': 'conversation', 'reference': ''}},
                        {'source': {'kind': 'agent-guess', 'reference': 'message-1'}},
                        {'owner_date': '2026-02-30'}, {'quote': '   '}, {'disposition': 'continue'}]:
            with self.subTest(changes=changes), self.assertRaises(CycleError):
                self.capture(shown, **changes)
        request = self.capture_request(shown)
        del request['disposition']
        with self.assertRaisesRegex(CycleError, 'invalid-request'):
            self.owner().capture(self.repo, request)
        self.assertEqual(list((self.cfg.docs_root / f'cycles/{self.doc["id"]}/owner-decisions/captures').glob('*.json')), [])

    def test_tool_question_source_and_owner_local_date_are_retained(self):
        captured = self.capture(source={'kind': 'tool-question', 'reference': 'question-actual-7/answer-1'}, owner_date='2026-01-01')
        self.assertEqual(captured['record']['source']['kind'], 'tool-question')
        self.assertEqual(captured['record']['owner_date'], '2026-01-01')
        self.assertEqual(datetime.fromisoformat(captured['record']['at']).utcoffset().total_seconds(), 0)

    def test_capture_resolves_presentation_before_writing_and_checks_bindings(self):
        shown = self.presentation()
        for changes in [{'presentation': {'path': 'cycles/CYC-0001/absent.json', 'sha256': '0' * 64}},
                        {'presentation': {**shown['presentation'], 'sha256': '0' * 64}},
                        {'subject_sha256': '0' * 64}, {'subject': 'cycles/CYC-0001/decisions/other.json'},
                        {'purpose': 'adr-acceptance'}, {'cycle_id': None}]:
            with self.subTest(changes=changes), self.assertRaises(CycleError):
                self.capture(shown, **changes)
        self.assertEqual(list((self.cfg.docs_root / f'cycles/{self.doc["id"]}/owner-decisions/captures').glob('*.json')), [])

    def test_application_rejects_caller_binding_mismatches(self):
        approved = self.capture()
        for changes in [{'subject_sha256': '0' * 64}, {'subject': 'adrs/ADR-0001-other.md'},
                        {'cycle_id': 'CYC-9999'}, {'purpose': 'adr-acceptance', 'approval': 'none.json'}]:
            with self.subTest(changes=changes), self.assertRaises((CycleError, OSError)):
                self.application(approved, **changes)
        self.assertIsNone(load(self.repo, self.doc['id'])['decisions'][-1]['approval'])

    def test_missing_or_modified_subject_cannot_be_presented_or_applied(self):
        approved = self.capture()
        path = self.cfg.docs_root / self.subject
        path.write_text('Changed revision bytes')
        with self.assertRaises(CycleError):
            self.application(approved)
        with self.assertRaises(CycleError):
            self.presentation(ident='present-stale-2')
        path.unlink()
        with self.assertRaises(CycleError):
            self.application(approved)

    def test_new_revision_starts_separate_lineage(self):
        rejected = self.capture(disposition='reject', quote='Reject revision 1.')
        contents = {k: ['new reason'] for k in ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence')}
        updated = mutate(self.repo, self.doc['id'], 'decision', kind='idr', name='choice', contents=contents)
        old_binding = self.binding
        self.subject = updated['decisions'][-1]['path']
        self.binding = {**self.binding, 'subject': self.subject,
                        'subject_sha256': digest((self.cfg.docs_root / self.subject).read_bytes())}
        shown = self.presentation(ident='present-revision-2')
        with self.assertRaisesRegex(CycleError, 'cross-subject'):
            self.capture(shown, ident='capture-cross-2', supersedes=rejected['capture'])
        approved = self.capture(shown, ident='capture-revision-2')
        self.assertTrue(self.application(approved)['applied'])
        with self.assertRaises(CycleError):
            self.owner().apply(self.repo, {**old_binding, 'capture': rejected['capture']})

    def test_forks_self_reference_and_cross_subject_supersession_refuse(self):
        approved = self.capture()
        for supersedes in [None, {'path': f'cycles/{self.doc["id"]}/owner-decisions/captures/capture-self-2.json', 'sha256': '0' * 64}]:
            with self.subTest(supersedes=supersedes), self.assertRaises(CycleError):
                self.capture(ident='capture-self-2', disposition='reject', quote='Reject.', supersedes=supersedes)
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        with self.assertRaises(CycleError):
            self.capture(ident='capture-forked-3', disposition='pending', supersedes=approved['capture'])
        self.assertEqual(rejected['record']['disposition'], 'reject')

    def test_corrupt_cycle_or_fork_in_retained_lineage_refuses_application(self):
        approved = self.capture()
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        path = self.cfg.docs_root / approved['capture']['path']
        record = json.loads(path.read_text())
        record['supersedes'] = rejected['capture']
        record.pop('record_sha256')
        record['record_sha256'] = digest(encoded(record))
        path.write_bytes(encoded(record))
        with self.assertRaises(CycleError):
            self.application(rejected)

    def test_unapplied_capture_cannot_use_legacy_approval_lane(self):
        approved = self.capture()
        with self.assertRaisesRegex(CycleError, 'owner-decision apply'):
            mutate(self.repo, self.doc['id'], 'approve-decision', subject=self.subject, approval=approved['capture']['path'])
        from cycle_council import validate_approval
        with self.assertRaises((CycleError, OSError)):
            validate_approval(self.repo, approved['capture']['path'], purpose='idr', subject=self.subject)
        self.application(approved)
        self.assertEqual(validate_approval(self.repo, approved['capture']['path'], purpose='idr', subject=self.subject)['quote'], approved['record']['quote'])

    def test_owner_selection_retains_existing_simplify_authority(self):
        self.doc = self.plan(self.cycle('simplify'))
        self.doc = mutate(self.repo, self.doc['id'], 'decision', kind='idr', name='selection',
                          contents=simplify_fixtures.selection(proposals=[simplify_fixtures.proposal('P1')]))
        self.subject = self.doc['decisions'][-1]['path']
        self.binding = {'purpose': 'idr', 'cycle_id': self.doc['id'], 'subject': self.subject,
                        'subject_sha256': digest((self.cfg.docs_root / self.subject).read_bytes())}
        self.application(self.capture())
        self.assertEqual(fixtures.CycleTests.advance(self, load(self.repo, self.doc['id']))['phase'], 'build')

    def test_pause_refuses_new_capture_or_application_but_retains_exact_replay(self):
        shown = self.presentation()
        approved = self.capture(shown)
        mutate(self.repo, self.doc['id'], 'pause', reason='test owner pause')
        with self.assertRaisesRegex(CycleError, 'cycle-not-active'):
            self.capture(shown, ident='capture-paused-2', supersedes=approved['capture'])
        with self.assertRaisesRegex(CycleError, 'cycle-not-active'):
            self.application(approved)
        self.assertEqual(self.capture(shown)['capture'], approved['capture'])

    def test_nonartifact_presentation_path_is_never_read(self):
        shown = self.presentation()
        ref = {'path': 'secrets/.env', 'sha256': '0' * 64}
        original = self.owner()._reader
        calls = []
        def tracking(cfg):
            read = original(cfg)
            def observed(path):
                calls.append(path)
                return read(path)
            return observed
        with patch.object(self.owner(), '_reader', side_effect=tracking):
            with self.assertRaisesRegex(CycleError, 'path-mismatch'):
                self.capture(shown, presentation=ref)
        self.assertNotIn('secrets/.env', calls)

    def test_idr_save_before_receipt_crash_replays_applied_state_after_reject(self):
        approved = self.capture()
        with patch.object(self.owner(), '_application_record', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        result = self.application(approved)
        self.assertTrue(result['already_applied'])
        self.assertEqual(result['current_capture'], rejected['capture'])
        self.assertEqual(load(self.repo, self.doc['id'])['decisions'][-1]['approval'], approved['capture']['path'])

    def test_secret_evidence_and_scanner_failure_write_no_capture(self):
        shown = self.presentation()
        with self.assertRaisesRegex(CycleError, 'unsafe-owner'):
            self.capture(shown, quote='ghp_' + 'a' * 36)
        with patch.object(self.owner(), 'scan_fields', side_effect=RuntimeError('private scanner detail')):
            with self.assertRaisesRegex(CycleError, 'scanner-unavailable'):
                self.capture(shown)
        self.assertEqual(list((self.cfg.docs_root / f'cycles/{self.doc["id"]}/owner-decisions/captures').glob('*.json')), [])

    def _race(self, first):
        approved = self.capture()
        shown = self.presentation()
        requests = {'apply': {**self.binding, 'capture': approved['capture']},
                    'capture': self.capture_request(shown, 'capture-reject-race', disposition='reject',
                                                    quote='Reject this revision.', supersedes=approved['capture'])}
        ctx = multiprocessing.get_context('fork')
        gate, release, started_first, started_second = (ctx.Event() for _ in range(4))
        results = ctx.Queue()
        second = 'capture' if first == 'apply' else 'apply'
        workers = [ctx.Process(target=decision_worker, args=(self.repo, first, requests[first], started_first,
                                                             gate, release, results, True)),
                   ctx.Process(target=decision_worker, args=(self.repo, second, requests[second], started_second,
                                                             gate, release, results, False))]
        try:
            workers[0].start()
            self.assertTrue(gate.wait(10), 'first mutation did not enter its locked boundary')
            workers[1].start()
            self.assertTrue(started_second.wait(10), 'competing mutation was not attempted')
            release.set()
            observed = [results.get(timeout=15), results.get(timeout=15)]
        finally:
            release.set()
            for worker in workers:
                if worker.pid is not None:
                    worker.join(timeout=10)
                    if worker.is_alive():
                        worker.terminate()
                        worker.join(timeout=5)
            results.close()
        self.assertTrue(all(worker.exitcode == 0 for worker in workers))
        return approved, {row['operation']: row for row in observed}

    def test_concurrent_apply_then_reject_has_truthful_applied_replay(self):
        approved, rows = self._race('apply')
        self.assertTrue(rows['apply']['ok'], rows)
        self.assertTrue(rows['capture']['ok'], rows)
        replay = self.application(approved)
        self.assertTrue(replay['already_applied'])
        self.assertEqual(replay['current_disposition'], 'reject')

    def test_concurrent_reject_then_apply_refuses_superseded_approve(self):
        _, rows = self._race('capture')
        self.assertTrue(rows['capture']['ok'], rows)
        self.assertFalse(rows['apply']['ok'], rows)
        self.assertEqual(rows['apply']['code'], 'superseded-owner-capture')
        self.assertIsNone(load(self.repo, self.doc['id'])['decisions'][-1]['approval'])


class OwnerAdrTests(unittest.TestCase):
    setUp_base = adr_fixtures.DecisionPolicyTests.setUp
    propose = adr_fixtures.DecisionPolicyTests.propose
    council = adr_fixtures.DecisionPolicyTests.council
    owner = OwnerDecisionTests.owner
    presentation = OwnerDecisionTests.presentation
    capture_request = OwnerDecisionTests.capture_request
    capture = OwnerDecisionTests.capture

    def setUp(self):
        self.setUp_base()
        self.repo = self.root
        self.cfg = tree(self.repo)
        self.subject = self.propose()
        self.binding = {'purpose': 'adr-acceptance', 'cycle_id': None, 'subject': self.subject,
                        'subject_sha256': digest((self.docs / self.subject).read_bytes())}
        self.approval = self.council(self.subject)

    def application(self, captured, **changes):
        return self.owner().apply(self.repo, {**self.binding, 'capture': captured['capture'], 'approval': self.approval, **changes})

    def test_acceptance_preserves_body_and_binding_policy(self):
        original = (self.docs / self.subject).read_text()
        approved = self.capture()
        self.assertTrue(self.application(approved)['applied'])
        current = (self.docs / self.subject).read_text()
        self.assertEqual(dp.frontmatter(original)[1], dp.frontmatter(current)[1])
        receipt = dp.validate_acceptance(self.cfg, {'path': self.subject})
        self.assertEqual(receipt['owner_decision'], approved['capture'])
        self.assertEqual(receipt['human_approval'], approved['record']['quote'])
        self.assertEqual(receipt['standing'], 'binding')
        from summaries_projection import collect_records
        self.assertEqual(len(collect_records(self.docs / 'adrs')), 1)

    def test_recovery_projection_uses_operation_source_io_for_all_proofs(self):
        _, current = self._interrupted_reapproval()
        applied = self.application(current)
        from summaries_projection import collect_records
        import test_summaries_source_io as source_fixtures
        guard = source_fixtures.RecordingIO(self.repo)
        self.assertEqual(collect_records(self.docs / 'adrs'),
                         collect_records(self.docs / 'adrs', _source_io=guard))
        reads = {path for method, path in guard.calls if method == 'read_bytes'}
        expected = {self.docs / 'adrs/acceptances/ADR-0001.json',
                    self.docs / 'adrs/acceptances/ADR-0001.current.json',
                    self.docs / applied['application']['path'], self.docs / self.approval,
                    self.docs / current['capture']['path'], self.docs / current['record']['presentation']['path']}
        expected = {path.resolve() for path in expected}
        self.assertTrue(expected.issubset(reads), expected - reads)

    def test_already_accepted_replay_after_reject_never_reapplies_lifecycle(self):
        approved = self.capture()
        first = self.application(approved)
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        before = (self.docs / self.subject).read_bytes()
        with patch.object(dp, 'write_text_atomic', side_effect=AssertionError('must not reapply')):
            replay = self.application(approved)
        self.assertTrue(replay['already_applied'])
        self.assertEqual(replay['application'], first['application'])
        self.assertEqual(replay['current_capture'], rejected['capture'])
        self.assertEqual(replay['current_disposition'], 'reject')
        self.assertIn('transition-adr', replay['lifecycle_route'])
        self.assertEqual(before, (self.docs / self.subject).read_bytes())
        dp.validate_acceptance(self.cfg, {'path': self.subject})

    def test_receipt_before_write_crash_cannot_bypass_later_rejection(self):
        approved = self.capture()
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        with self.assertRaisesRegex(CycleError, 'superseded'):
            self.application(approved)
        with self.assertRaisesRegex(CycleError, 'superseded'):
            dp.accept(self.repo, self.subject, self.approval)
        self.assertEqual(dp.frontmatter((self.docs / self.subject).read_text())[0]['status'], 'Proposed')

    def test_receipt_before_write_crash_recovers_with_current_approval(self):
        approved = self.capture()
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        self.assertFalse(self.application(approved)['already_applied'])
        dp.validate_acceptance(self.cfg, {'path': self.subject})

    def test_receipt_recovery_requires_current_events_but_applied_history_does_not(self):
        import council_policy
        import cycle_council
        from test_cycle_council import ModeAwareCouncilTests
        (self.docs / 'objectives.md').write_text('Durable evidence and explicit owner decisions.')
        council_policy.initialize(self.repo, 'standard', selection='Offline fixture selects Standard')
        for args in (('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'),
                     ('config', 'user.name', 'Fixture'), ('add', '.'), ('commit', '-qm', 'Fixture')):
            fixtures.CycleTests.git(self, *args)
        output, _ = ModeAwareCouncilTests.call(self, purpose='adr', subject=self.subject)
        self.approval = output['record']
        council_policy.disposition(self.repo, self.approval, {
            'agrees': True, 'subject_sha256': self.binding['subject_sha256'],
            'rationale': 'Offline fixture agrees.', 'dissent': []})
        council = cycle_council.validate_approval(self.repo, self.approval, purpose='adr', subject=self.subject)
        self.assertEqual(len(council['call_evidence']['events']), 6)
        approved = self.capture()
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        path = self.docs / self.subject
        proposed = path.read_bytes()
        receipt = self.docs / 'adrs/acceptances/ADR-0001.json'
        retained = receipt.read_bytes()
        event = self.docs / next(ref['path'] for ref in council['call_evidence']['events']
                                if ref['path'].endswith('-outcome.json'))
        original = event.read_bytes()
        for changed in (None, b'{}'):
            with self.subTest(event='missing' if changed is None else 'changed'):
                if changed is None:
                    event.unlink()
                else:
                    event.write_bytes(changed)
                try:
                    with patch.object(dp, 'write_text_atomic', side_effect=AssertionError('unexpected lifecycle write')):
                        with self.assertRaisesRegex(CycleError, 'checkpoint'):
                            self.application(approved)
                    self.assertEqual(path.read_bytes(), proposed)
                    self.assertEqual(receipt.read_bytes(), retained)
                finally:
                    event.write_bytes(original)
        self.assertFalse(self.application(approved)['already_applied'])
        accepted = path.read_bytes()
        event.unlink()
        with patch.object(dp, 'write_text_atomic', side_effect=AssertionError('must not reapply')):
            self.assertTrue(self.application(approved)['already_applied'])
        self.assertEqual(path.read_bytes(), accepted)
        dp.validate_acceptance(self.cfg, {'path': self.subject})

    def test_interrupted_acceptance_recovers_after_reject_and_reapprove(self):
        approved = self.capture()
        proposed = (self.docs / self.subject).read_bytes()
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        canonical = self.docs / 'adrs/acceptances/ADR-0001.json'
        original = canonical.read_bytes()
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.',
                                supersedes=approved['capture'])
        current = self.capture(ident='capture-approve-3', quote='Approve again.', supersedes=rejected['capture'])
        self.assertEqual(proposed, (self.docs / self.subject).read_bytes())
        applied = self.application(current)
        self.assertFalse(applied['already_applied'])
        receipt = dp.validate_acceptance(self.cfg, {'path': self.subject})
        self.assertEqual(receipt['owner_decision'], current['capture'])
        self.assertEqual(canonical.read_bytes(), original)
        self.assertEqual(receipt['accepted_sha256'], json.loads(original)['accepted_sha256'])
        self.assertNotEqual(applied['application']['path'], canonical.relative_to(self.docs).as_posix())
        self.assertTrue(self.application(current)['already_applied'])
        with self.assertRaises(CycleError):
            self.application(approved)
        from summaries_projection import collect_records
        self.assertEqual(len(collect_records(self.docs / 'adrs')), 1)

    def _interrupted_reapproval(self):
        approved = self.capture()
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.',
                                supersedes=approved['capture'])
        current = self.capture(ident='capture-approve-3', quote='Approve again.', supersedes=rejected['capture'])
        return approved, current

    def test_recovery_receipt_and_binding_crashes_preserve_currentness(self):
        approved, current = self._interrupted_reapproval()
        canonical = self.docs / 'adrs/acceptances/ADR-0001.json'
        original = canonical.read_bytes()
        original_atomic = dp.atomic
        def interrupt_binding(path, value):
            if path.name.endswith('.current.json'):
                raise OSError('binding interrupted')
            return original_atomic(path, value)
        with patch.object(dp, 'atomic', side_effect=interrupt_binding):
            with self.assertRaisesRegex(OSError, 'binding interrupted'):
                self.application(current)
        recovery = next((self.docs / 'adrs/acceptances/recoveries/ADR-0001').glob('*.json'))
        retained = recovery.read_bytes()
        self.assertEqual(canonical.read_bytes(), original)
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('file interrupted')):
            with self.assertRaisesRegex(OSError, 'file interrupted'):
                self.application(current)
        self.assertEqual(recovery.read_bytes(), retained)
        rejected = self.capture(ident='capture-reject-4', disposition='reject', quote='Reject again.',
                                supersedes=current['capture'])
        for old in (approved, current):
            with self.assertRaisesRegex(CycleError, 'superseded'):
                self.application(old)
        latest = self.capture(ident='capture-approve-5', quote='Approve the unchanged proposal.',
                               supersedes=rejected['capture'])
        self.application(latest)
        receipt = dp.validate_acceptance(self.cfg, {'path': self.subject})
        self.assertEqual(receipt['recovery_of']['path'], recovery.relative_to(self.docs).as_posix())
        self.assertEqual(recovery.read_bytes(), retained)
        self.assertEqual(canonical.read_bytes(), original)
        self.assertTrue(self.application(latest)['already_applied'])
        self.capture(ident='capture-reject-6', disposition='reject', quote='Reject after acceptance.',
                     supersedes=latest['capture'])
        with patch.object(dp, 'write_text_atomic', side_effect=AssertionError('must not reapply')):
            self.assertEqual(self.application(latest)['current_disposition'], 'reject')

    def test_recovery_readers_refuse_corrupt_or_missing_bindings(self):
        _, current = self._interrupted_reapproval()
        applied = self.application(current)
        binding = self.docs / 'adrs/acceptances/ADR-0001.current.json'
        original = binding.read_bytes()
        record = json.loads(original)
        from summaries_projection import collect_records, GovernsValidationError
        from adr_migration import _governing
        package = {'governing_adr': {'receipt': 'bionic/adrs/acceptances/ADR-0001.json',
                    'source': {'path': 'bionic/' + self.subject, 'sha256': self.binding['subject_sha256']}}}
        with self.assertRaisesRegex(CycleError, 'current immutable'):
            _governing(self.repo, package)
        package['governing_adr']['receipt'] = 'bionic/' + applied['application']['path']
        self.assertEqual(_governing(self.repo, package)['owner_decision'], current['capture'])
        variants = [None, b'{}', json.dumps({**record, 'current': {**record['current'], 'sha256': '0' * 64}}).encode(),
                    json.dumps({**record, 'original': {**record['original'], 'sha256': '0' * 64}}).encode(),
                    json.dumps({**record, 'current': {**record['current'], 'path': '../outside.json'}}).encode()]
        for damaged in variants:
            with self.subTest(binding=damaged):
                if damaged is None:
                    binding.unlink()
                else:
                    binding.write_bytes(damaged)
                try:
                    with self.assertRaises((CycleError, KeyError)):
                        dp.validate_acceptance(self.cfg, {'path': self.subject})
                    with self.assertRaises(GovernsValidationError):
                        collect_records(self.docs / 'adrs')
                    with self.assertRaises((CycleError, KeyError)):
                        self.application(current)
                finally:
                    binding.write_bytes(original)
        for path in (self.docs / applied['application']['path'], self.docs / 'adrs/acceptances/ADR-0001.json'):
            before = path.read_bytes()
            path.unlink()
            try:
                with self.assertRaises((CycleError, OSError)):
                    dp.validate_acceptance(self.cfg, {'path': self.subject})
                with self.assertRaises((CycleError, OSError)):
                    self.application(current)
            finally:
                path.write_bytes(before)

    def test_recovery_refuses_changed_proposal_council_and_conflicting_retained_receipt(self):
        _, current = self._interrupted_reapproval()
        path = self.docs / self.subject
        original = path.read_bytes()
        path.write_bytes(original + b'changed\n')
        with self.assertRaisesRegex(CycleError, 'changed during acceptance recovery'):
            self.application(current)
        path.write_bytes(original)
        council_path = self.docs / self.approval
        council_bytes = council_path.read_bytes()
        wrong = self.council(self.subject, purpose='consultation')
        with self.assertRaises(CycleError):
            self.application(current, approval=wrong)
        council_path.write_bytes(council_bytes)
        recovery = self.docs / f'adrs/acceptances/recoveries/ADR-0001/{current["capture"]["sha256"]}.json'
        recovery.parent.mkdir(parents=True)
        recovery.write_text('{"conflict":true}')
        with self.assertRaisesRegex(CycleError, 'conflicting immutable acceptance recovery'):
            self.application(current)
        self.assertEqual(recovery.read_text(), '{"conflict":true}')
        self.assertEqual(path.read_bytes(), original)

    def test_conversation_approval_does_not_replace_council(self):
        approved = self.capture()
        self.approval = self.council(self.subject, purpose='consultation')
        with self.assertRaises(CycleError):
            self.application(approved)
        self.assertEqual(dp.frontmatter((self.docs / self.subject).read_text())[0]['status'], 'Proposed')

    def test_missing_retained_provenance_invalidates_acceptance_proof(self):
        approved = self.capture()
        self.application(approved)
        (self.docs / approved['record']['presentation']['path']).unlink()
        with self.assertRaises(CycleError):
            dp.validate_acceptance(self.cfg, {'path': self.subject})

    def test_accepted_file_before_cycle_save_recovers_bookkeeping_without_reapplying(self):
        doc = create(self.repo, 'iterate', 'Accept decision', 'Accept the reviewed ADR',
                     ['bionic/adrs'], ['body unchanged'], 'builder', 'tester')
        creation_subject = f'cycles/{doc["id"]}/evidence/creation.json'
        creation_path = self.docs / creation_subject
        creation_path.parent.mkdir(parents=True)
        creation_path.write_text('{"question":"Is an ADR justified?"}')
        temporary = self.council(creation_subject, purpose='adr-creation', cycle_id=doc['id'])
        creation_approval = 'adrs/councils/creation.json'
        (self.docs / temporary).rename(self.docs / creation_approval)
        self.subject = dp.propose(self.repo, self.proposal, origin='cycle', cycle_id=doc['id'],
                                  creation_approval=creation_approval, creation_subject=creation_subject)['path']
        self.binding = {'purpose': 'adr-acceptance', 'cycle_id': doc['id'], 'subject': self.subject,
                        'subject_sha256': digest((self.docs / self.subject).read_bytes())}
        self.approval = self.council(self.subject, cycle_id=doc['id'])
        approved = self.capture()
        with patch.object(dp, 'save', side_effect=OSError('cycle save interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        self.assertFalse(load(self.repo, doc['id'])['decisions'][-1]['accepted'])
        self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        before = (self.docs / self.subject).read_bytes()
        with patch.object(dp, 'write_text_atomic', side_effect=AssertionError('must not reapply')):
            recovered = self.application(approved)
        self.assertTrue(recovered['already_applied'])
        self.assertEqual(recovered['current_disposition'], 'reject')
        self.assertTrue(load(self.repo, doc['id'])['decisions'][-1]['accepted'])
        self.assertEqual(before, (self.docs / self.subject).read_bytes())


if __name__ == '__main__':
    unittest.main()
