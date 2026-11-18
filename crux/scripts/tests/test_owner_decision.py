"""Explicit owner evidence binds a shown revision; recording never invents intent."""
import contextlib
from datetime import datetime
import importlib.util
import io
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_writer
from cycle_store import CycleError, atomic, digest, encoded, tree
import test_cycle_decision_policy as adr_fixtures
import decision_policy as dp

_spec = importlib.util.spec_from_file_location('decision_policy_cli', Path(__file__).resolve().parents[1] / 'decision-policy.py')
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)


def decision_worker(repo, operation, request, announced, gate, release, results, hold=False):
    """A real process holds the production flock across the controlled mutation boundary."""
    import decision_policy
    import owner_decision as owner
    announced.set()
    target, name = (decision_policy, 'write_text_atomic') if operation == 'apply' else (owner, 'atomic')
    original = getattr(target, name)
    def holding(*args, **kwargs):
        if hold:
            gate.set()
            if not release.wait(10):
                raise RuntimeError('test coordination expired')
        return original(*args, **kwargs)
    try:
        with patch.object(target, name, side_effect=holding):
            value = getattr(owner, operation)(repo, request)
        results.put({'operation': operation, 'ok': True, 'value': value})
    except Exception as exc:
        results.put({'operation': operation, 'ok': False, 'code': str(exc)})


class AdrFixture:
    """A Proposed ADR for cycle_id null, with a council approval of its exact bytes."""
    setUp_base = adr_fixtures.DecisionPolicyTests.setUp
    propose = adr_fixtures.DecisionPolicyTests.propose
    council = adr_fixtures.DecisionPolicyTests.council

    def setUp(self):
        self.setUp_base()
        self.repo = self.root
        self.cfg = tree(self.repo)
        self.subject = self.propose()
        self.binding = {'purpose': 'adr-acceptance', 'cycle_id': None, 'subject': self.subject,
                        'subject_sha256': digest((self.docs / self.subject).read_bytes())}
        self.approval = self.council(self.subject)

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
        return self.owner().apply(self.repo, {**self.binding, 'capture': captured['capture'], 'approval': self.approval, **changes})

    def command(self, action, request):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(['--repo-root', str(self.repo), 'owner-decision', action, '--json', json.dumps(request)])
        return code, json.loads(out.getvalue())

    def captures(self):
        return list((self.docs / 'adrs/owner-decisions/captures').glob('*.json'))

    def status(self):
        return dp.frontmatter((self.docs / self.subject).read_text())[0]['status']


class OwnerDecisionTests(AdrFixture, unittest.TestCase):
    def test_cli_present_capture_apply_retains_verbatim_provenance(self):
        request = {**self.binding, 'op_id': 'present-cli-1', 'question': 'Approve the shown revision?'}
        code, shown = self.command('present', request)
        self.assertEqual(code, 0, shown)
        quote = "I approve it; keep `these bytes`, $HOME, and this newline.\nExactly."
        captured = self.capture(shown, quote=quote)
        self.assertEqual(captured['record']['quote'], quote)
        self.assertEqual(captured['record']['source'], {'kind': 'conversation', 'reference': 'session-1/message-7'})
        self.assertEqual(captured['record']['subject_sha256'], self.binding['subject_sha256'])
        result = self.application(captured)
        self.assertTrue(result['applied'])
        self.assertFalse(result['already_applied'])
        self.assertEqual(self.status(), 'Accepted')
        self.assertEqual(dp.validate_acceptance(self.cfg, {'path': self.subject})['human_approval'], quote)

    def test_reject_and_pending_continuation_cannot_apply(self):
        captured = None
        for index, disposition in enumerate(('reject', 'pending')):
            captured = self.capture(ident=f'capture-negative-{index}', disposition=disposition,
                                    quote='No.' if disposition == 'reject' else 'continue',
                                    supersedes=None if index == 0 else captured['capture'])
            with self.assertRaisesRegex(CycleError, 'not-approved'):
                self.application(captured)
        self.assertEqual(self.status(), 'Proposed')

    def test_superseded_approve_cannot_newly_apply(self):
        approved = self.capture()
        self.capture(ident='capture-reject-2', disposition='reject', quote='I reject it.', supersedes=approved['capture'])
        with self.assertRaisesRegex(CycleError, 'superseded'):
            self.application(approved)
        self.assertEqual(self.status(), 'Proposed')

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
        self.assertEqual(self.captures(), [])

    def test_tool_question_source_and_owner_local_date_are_retained(self):
        captured = self.capture(source={'kind': 'tool-question', 'reference': 'question-actual-7/answer-1'}, owner_date='2026-01-01')
        self.assertEqual(captured['record']['source']['kind'], 'tool-question')
        self.assertEqual(captured['record']['owner_date'], '2026-01-01')
        self.assertEqual(datetime.fromisoformat(captured['record']['at']).utcoffset().total_seconds(), 0)

    def test_capture_resolves_presentation_before_writing_and_checks_bindings(self):
        shown = self.presentation()
        for changes in [{'presentation': {'path': 'adrs/owner-decisions/presentations/absent-0001.json', 'sha256': '0' * 64}},
                        {'presentation': {**shown['presentation'], 'sha256': '0' * 64}},
                        {'subject_sha256': '0' * 64}, {'subject': 'adrs/ADR-0009-other.md'},
                        {'purpose': 'idr'}, {'cycle_id': 'CYC-0001'}]:
            with self.subTest(changes=changes), self.assertRaises(CycleError):
                self.capture(shown, **changes)
        self.assertEqual(self.captures(), [])

    def test_application_rejects_caller_binding_mismatches(self):
        approved = self.capture()
        for changes in [{'subject_sha256': '0' * 64}, {'subject': 'adrs/ADR-0009-other.md'}, {'cycle_id': 'CYC-9999'}]:
            with self.subTest(changes=changes), self.assertRaises((CycleError, OSError)):
                self.application(approved, **changes)
        self.assertEqual(self.status(), 'Proposed')

    def test_missing_or_modified_subject_cannot_be_presented_or_applied(self):
        approved = self.capture()
        path = self.docs / self.subject
        path.write_text('Changed revision bytes')
        with self.assertRaises(CycleError):
            self.application(approved)
        with self.assertRaises(CycleError):
            self.presentation(ident='present-stale-2')
        path.unlink()
        with self.assertRaises((CycleError, OSError)):
            self.application(approved)

    def test_new_revision_starts_separate_lineage(self):
        rejected = self.capture(disposition='reject', quote='Reject revision 1.')
        old_binding = self.binding
        path = self.docs / self.subject
        path.write_text(path.read_text() + '\nRevised wording.\n')
        self.binding = {**self.binding, 'subject_sha256': digest(path.read_bytes())}
        self.approval = self.council(self.subject)
        shown = self.presentation(ident='present-revision-2')
        with self.assertRaisesRegex(CycleError, 'cross-subject'):
            self.capture(shown, ident='capture-cross-2', supersedes=rejected['capture'])
        approved = self.capture(shown, ident='capture-revision-2')
        self.assertTrue(self.application(approved)['applied'])
        with self.assertRaises(CycleError):
            self.owner().apply(self.repo, {**old_binding, 'capture': rejected['capture'], 'approval': self.approval})

    def test_forks_self_reference_and_cross_subject_supersession_refuse(self):
        approved = self.capture()
        for supersedes in [None, {'path': 'adrs/owner-decisions/captures/capture-self-2.json', 'sha256': '0' * 64}]:
            with self.subTest(supersedes=supersedes), self.assertRaises(CycleError):
                self.capture(ident='capture-self-2', disposition='reject', quote='Reject.', supersedes=supersedes)
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        with self.assertRaises(CycleError):
            self.capture(ident='capture-forked-3', disposition='pending', supersedes=approved['capture'])
        self.assertEqual(rejected['record']['disposition'], 'reject')

    def test_corrupt_cycle_or_fork_in_retained_lineage_refuses_application(self):
        approved = self.capture()
        rejected = self.capture(ident='capture-reject-2', disposition='reject', quote='Reject.', supersedes=approved['capture'])
        path = self.docs / approved['capture']['path']
        record = json.loads(path.read_text())
        record['supersedes'] = rejected['capture']
        record.pop('record_sha256')
        record['record_sha256'] = digest(encoded(record))
        path.write_bytes(encoded(record))
        with self.assertRaises(CycleError):
            self.application(rejected)

    def test_present_refusal_names_the_missing_and_unknown_fields(self):
        request = {**self.binding, 'op_id': 'present-fields-1', 'question': 'Approve the shown revision?'}
        # Positive control: the complete request is presented.
        code, shown = self.command('present', request)
        self.assertEqual(code, 0, shown)
        broken = {key: value for key, value in request.items() if key != 'question'}
        broken['questions'] = 'misspelled'
        code, refused = self.command('present', broken)
        self.assertEqual(code, 1, refused)
        self.assertEqual(refused['error'], {'code': 'invalid-request-fields', 'missing': ['question'], 'unknown': ['questions']})

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

    def test_secret_evidence_and_scanner_failure_write_no_capture(self):
        shown = self.presentation()
        with self.assertRaisesRegex(CycleError, 'unsafe-owner'):
            self.capture(shown, quote='ghp_' + 'a' * 36)
        with patch.object(self.owner(), 'scan_fields', side_effect=RuntimeError('private scanner detail')):
            with self.assertRaisesRegex(CycleError, 'scanner-unavailable'):
                self.capture(shown)
        self.assertEqual(self.captures(), [])

    def _race(self, first):
        approved = self.capture()
        shown = self.presentation()
        requests = {'apply': {**self.binding, 'capture': approved['capture'], 'approval': self.approval},
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
        self.assertEqual(self.status(), 'Proposed')

    def test_a_paused_lightweight_cycle_refuses_a_new_capture_and_names_the_resume_recovery(self):
        case = adr_fixtures.CycleOriginProposalTests('test_a_historical_creation_approval_proposal_still_validates')
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.repo, self.docs, self.cfg = case.root, case.docs, tree(case.root)
        doc = case.cycle('working')
        self.subject = dp.propose(self.repo, case.proposal, origin='cycle', cycle_id=doc['id'])['path']
        self.binding = {'purpose': 'adr-acceptance', 'cycle_id': doc['id'], 'subject': self.subject,
                        'subject_sha256': digest((self.docs / self.subject).read_bytes())}
        shown = self.presentation()
        # Positive control: the same request is captured while the cycle is active.
        code, active = self.command('capture', self.capture_request(shown, 'capture-active-1'))
        self.assertEqual(code, 0, active)
        from types import SimpleNamespace
        cycle_writer.mutate(self.repo, doc['id'], 'lead', cycle_writer.load_pilot(self.repo, doc['id'])['revision'],
                            'pause', SimpleNamespace(reason='test owner pause'))
        code, paused = self.command('capture', self.capture_request(shown, 'capture-paused-1', supersedes=active['capture']))
        self.assertEqual(code, 1, paused)
        error = paused['error']
        self.assertEqual((error['code'], error['status']), ('cycle-not-active', 'paused'))
        self.assertIn(f"{doc['id']} with the cycle writer's resume command", error['recovery'])
        self.assertIn('repeats this request unchanged', error['recovery'])
        # An exact replay of the captured answer stays readable while the cycle is paused.
        self.assertEqual(self.capture(shown, 'capture-active-1')['capture'], active['capture'])

    def test_adr_acceptance_binds_no_legacy_typed_record(self):
        legacy = self.docs / 'cycles/CYC-0090/cycle.json'
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({'schema_version': 3, 'id': 'CYC-0090', 'status': 'active', 'phase': 'build'}))
        before = legacy.read_bytes()
        request = {**self.binding, 'cycle_id': 'CYC-0090', 'op_id': 'typed-0001', 'question': 'Accept?'}
        code, refused = self.command('present', request)
        self.assertEqual((code, refused['error']['code']), (1, 'typed-cycle-record'))
        self.assertEqual(legacy.read_bytes(), before)
        self.assertFalse((self.docs / 'cycles/CYC-0090/owner-decisions').exists())

    def test_idr_and_acceptance_change_refuse_by_a_named_code_and_write_nothing(self):
        expected = {'idr': 'idr-council-retired', 'acceptance-change': 'acceptance-change-retired'}
        before = sorted(p.relative_to(self.docs).as_posix() for p in self.docs.rglob('*'))
        for purpose, code in expected.items():
            for action in ('present', 'capture', 'apply'):
                for shape in ({'purpose': purpose}, {**self.binding, 'purpose': purpose, 'cycle_id': 'CYC-0149', 'op_id': 'retired-0001',
                                                      'question': 'Approve?', 'capture': {'path': 'x', 'sha256': '0' * 64}}):
                    with self.subTest(purpose=purpose, action=action, keys=len(shape)):
                        with self.assertRaises(self.owner().OwnerDecisionError) as raised:
                            getattr(self.owner(), action)(self.repo, shape)
                        self.assertEqual(raised.exception.code, code)
                        status, refused = self.command(action, shape)
                        self.assertEqual((status, refused['error']['code']), (1, code))
                        self.assertNotIn('withdraw-decision', json.dumps(refused))
        self.assertEqual(sorted(p.relative_to(self.docs).as_posix() for p in self.docs.rglob('*')), before)


class HistoricalOwnerEvidenceTests(unittest.TestCase):
    """Committed IDR and acceptance-change captures of retired typed records keep validating, read-only."""
    def setUp(self):
        from _dev_surface import REPO_ROOT, TREE, require_dev_surface
        self.repo, self.docs = REPO_ROOT, REPO_ROOT / TREE
        require_dev_surface(self, self.docs / 'cycles/CYC-0149/owner-decisions', 'committed historical owner decisions')
        import owner_decision
        self.owner = owner_decision
        self.cfg = tree(self.repo)

    def test_an_applied_idr_capture_validates_against_its_typed_record_without_changing_it(self):
        path = 'cycles/CYC-0149/owner-decisions/captures/c149-capture-idr-r2.json'
        record = json.loads((self.docs / path).read_text())
        typed = (self.docs / 'cycles/CYC-0149/cycle.json').read_bytes()
        validated = self.owner.validate_applied_idr(self.cfg, path, purpose='idr', subject=record['subject'],
                                                    subject_sha256=record['subject_sha256'], cycle_id='CYC-0149')
        self.assertEqual((validated['purpose'], validated['disposition']), ('idr', 'approve'))
        self.assertEqual((self.docs / 'cycles/CYC-0149/cycle.json').read_bytes(), typed)
        with self.assertRaisesRegex(CycleError, 'capture-binding-mismatch'):
            self.owner.validate_applied_idr(self.cfg, path, purpose='idr', subject=record['subject'],
                                            subject_sha256=record['subject_sha256'], cycle_id='CYC-0136')

    def test_an_acceptance_change_capture_and_its_presentation_validate(self):
        ref = {'path': 'cycles/CYC-0136/owner-decisions/captures/od-0136-narrow-c2-capture.json'}
        ref['sha256'] = digest((self.docs / ref['path']).read_bytes())
        capture = self.owner.validate_capture_evidence(self.owner._reader(self.cfg), ref)
        self.assertEqual((capture['purpose'], capture['cycle_id'], capture['disposition']),
                         ('acceptance-change', 'CYC-0136', 'approve'))


class OwnerAdrTests(AdrFixture, unittest.TestCase):
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

    def test_adr_apply_refuses_an_approval_or_capture_of_the_wrong_type_naming_the_field(self):
        """CYC-0155 friction F1: an approval object crashed apply with a TypeError and wrote nothing."""
        approved = self.capture()
        cases = {'approval object': ('approval', {'path': self.approval, 'sha256': '0' * 64}, 'invalid-approval-field'),
                 'approval empty': ('approval', '', 'invalid-approval-field'),
                 'capture path string': ('capture', approved['capture']['path'], 'invalid-capture-field')}
        for name, (field, value, code) in cases.items():
            with self.subTest(name):
                request = {**self.binding, 'capture': approved['capture'], 'approval': self.approval, field: value}
                status, refused = self.command('apply', request)
                self.assertEqual(status, 1, refused)
                self.assertEqual((refused['error']['code'], refused['error']['field']), (code, field))
                self.assertEqual(dp.frontmatter((self.docs / self.subject).read_text())[0]['status'], 'Proposed')
        # Positive control: the path string approval and the reference object capture apply.
        self.assertTrue(self.application(approved)['applied'])

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
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)
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

    def test_a_lightweight_cycle_adr_accepts_through_the_owner_answer_and_replays_without_reapplying(self):
        """A cycle-origin ADR of a lightweight cycle: the owner answer binds it, and a replay changes nothing."""
        case = adr_fixtures.CycleOriginProposalTests('test_a_historical_creation_approval_proposal_still_validates')
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.repo, self.docs, self.cfg = case.root, case.docs, tree(case.root)
        doc = case.cycle('reviewing')
        self.subject = dp.propose(self.repo, case.proposal, origin='cycle', cycle_id=doc['id'])['path']
        self.binding = {'purpose': 'adr-acceptance', 'cycle_id': doc['id'], 'subject': self.subject,
                        'subject_sha256': digest((self.docs / self.subject).read_bytes())}
        self.approval = case.council(self.subject, doc['id'])
        approved = self.capture()
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('acceptance write interrupted')):
            with self.assertRaises(OSError):
                self.application(approved)
        self.assertEqual(dp.frontmatter((self.docs / self.subject).read_text())[0]['status'], 'Proposed')
        record = (self.docs / f'cycles/{doc["id"]}/cycle.json').read_bytes()
        applied = self.application(approved)
        self.assertFalse(applied['already_applied'])
        self.assertEqual(dp.frontmatter((self.docs / self.subject).read_text())[0]['status'], 'Accepted')
        before = (self.docs / self.subject).read_bytes()
        with patch.object(dp, 'write_text_atomic', side_effect=AssertionError('must not reapply')):
            self.assertTrue(self.application(approved)['already_applied'])
        self.assertEqual(before, (self.docs / self.subject).read_bytes())
        # Acceptance writes the ADR file and its receipt; the cycle record keeps its proposal-time entry.
        self.assertEqual(record, (self.docs / f'cycles/{doc["id"]}/cycle.json').read_bytes())
        dp.validate_acceptance(self.cfg, {'path': self.subject})

if __name__ == '__main__':
    unittest.main()
