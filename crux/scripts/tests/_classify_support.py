"""Shared fixtures for the cycle classification tests: a scripted `decisions.ask_many` and the cycle scenarios.

No test here sends a live request. `ClassifyBase` replaces `crux.decisions.ask_many` with a script of
controlled outcomes and `crux.decisions.classifier_status` with a configured status.
"""
import contextlib
from dataclasses import dataclass
import fcntl
import io
import json
from pathlib import Path
import sys
import threading
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle
import cycle_classify
import cycle_context
from crux import decisions
from cycle_workflow import load, mutate
from test_cycle_ops_advance import AdvanceBase, FAILING, PASSING, REVIEW
from test_evidence import execute

MODEL = decisions.EXPECTED_SERVED_MODEL
LEGACY_KINDS = ('work-sizing', 'review-routing', 'finding-disposition', 'failure-routing')
AUTO_HOOK_KINDS = ('execution-arrangement', 'context-selection', 'handoff-completeness', 'focused-test-ranking')
BLOCKING = {'path': 'src/a.py', 'consequence': 'LEAK-ZQ-consequence wrong answer', 'evidence': 'LEAK-ZQ-evidence the unit check'}


class SimulatedCrash(BaseException):
    """A process death between the triggering commit and the classification write."""


@dataclass
class QuestionReply:
    """An explicit automatic reply that needs the wire question's own id."""
    answer: object


def one_at_a_time(single):
    """An `ask_many` stand-in that answers each question through the scripted single-question `single`."""
    def ask_many(state, questions, *, deadline, client=None, kinds=()):
        return {qid: single(state, qid, question, deadline=deadline, client=client) for qid, question in questions.items()}
    return ask_many


def answered(choice, request_id='gen-req-0001', probabilities=None):
    return decisions.Outcome(status=decisions.ANSWERED, choice=choice, probabilities=probabilities, confidence=0.9,
                             request_id=request_id, served_model=MODEL, attempts=1)


def review_reply(reply):
    """One scripted reply applied to every review-routing predicate of a Review entry (review-routing version 2).

    An `add:<id>` answer answers yes for the question offering that specialist and floor-only for every other;
    any other reply (floor-only, insufficient-information or a fallback) answers every predicate alike."""
    def answer(state, question):
        # Only an add of a known specialist is a yes for that specialist alone; an unknown add is sent as it is.
        known = (reply.choice or '')[4:] in cycle_classify.SPECIALISTS
        if reply.status == decisions.ANSWERED and (reply.choice or '').startswith('add:') and known and reply.choice not in question.options:
            return decisions.Outcome(**{**reply.__dict__, 'choice': 'floor-only'})
        return reply
    return answer


def is_review_question(question):
    return 'floor-only' in getattr(question, 'options', {})


def failed(status, request_id=None, attempts=1, http_status=None):
    return decisions.Outcome(status=status, request_id=request_id, attempts=attempts, http_status=http_status)


class ClassifyBase(AdvanceBase):
    """Explicitly enabled advice helpers, scripted answers, and scenario helpers.

    The public operation gate stays covered without this policy mock in
    test_cycle_fast_operations. This fixture tests the reusable advice transaction
    and routing safety contracts, rather than asking routine operations to send.
    """

    def setUp(self):
        super().setUp()
        policy = mock.patch.object(cycle_context, 'provider_requests_allowed', return_value=True)
        policy.start(); self.addCleanup(policy.stop)
        self.asked, self.replies, self.default, self.hook, self.review = [], [], None, None, None
        self.provider_calls, self.auto_hook_asked, self.auto_hook_replies = [], [], {}
        self._engine_question_depth = 0
        self.status = decisions.Status(True, None)
        for target, replacement in (('classifier_status', lambda: self.status), ('ask', self.scripted_ask),
                                    ('ask_many', self.scripted_many)):
            patcher = mock.patch.object(decisions, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    PROBE = threading.Lock()

    def lock_is_free(self):
        # Concurrent requests probe the lock file; serialize the probes so one probe never reads another's hold as the cycle lock.
        with self.PROBE, (self.repo / 'bionic/cycles/.lock').open('a') as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            fcntl.flock(stream, fcntl.LOCK_UN)
            return True

    @contextlib.contextmanager
    def engine_questions(self):
        """Label real engine-hook calls without disabling hooks or hiding stored entries."""
        self._engine_question_depth += 1
        try:
            yield
        finally:
            self._engine_question_depth -= 1

    def scripted_many(self, state, questions, *, deadline, client=None, kinds=()):
        kind = kinds[0] if len(kinds) == 1 else None
        automatic = bool(self._engine_question_depth and kind in AUTO_HOOK_KINDS)
        method = self.scripted_auto_hook if automatic else self.scripted_ask
        return {qid: method(state, qid, question, deadline=deadline, client=client, _kind=kind)
                for qid, question in questions.items()}

    def scripted_auto_hook(self, state, question_id, question, *, deadline, client=None, _kind=None):
        call = {'state': state, 'id': question_id, 'question': question, 'deadline': deadline,
                'lock_free': self.lock_is_free(), 'kind': _kind, 'automatic': True}
        self.auto_hook_asked.append(call)
        self.provider_calls.append(call)
        if _kind in self.auto_hook_replies:
            reply = self.auto_hook_replies[_kind]
            if isinstance(reply, QuestionReply):
                return reply.answer(state, question_id, question)
            if isinstance(reply, dict):
                reply = reply[question_id]
            return reply(state, question) if callable(reply) else reply
        if _kind == 'handoff-completeness':
            route = next((route for route in question.options if route.startswith('answered:')), 'unresolved')
        elif _kind == 'execution-arrangement':
            route = 'developer' if 'developer' in question.options else decisions.INSUFFICIENT_INFORMATION
        else:
            route = 'omit'
        return answered(route, request_id='fixture-auto-hook')

    def scripted_ask(self, state, question_id, question, *, deadline, client=None, _kind=None):
        call = {'state': state, 'id': question_id, 'question': question, 'deadline': deadline,
                'lock_free': self.lock_is_free(), 'kind': _kind, 'automatic': False}
        self.asked.append(call)
        self.provider_calls.append(call)
        if self.hook:
            self.hook(len(self.asked))
        if self.review is not None and is_review_question(question):
            return self.review(state, question)
        reply = self.replies.pop(0) if self.replies else self.default
        if reply is None:
            raise AssertionError(f'no scripted reply for question {len(self.asked)}')
        if isinstance(reply, dict):
            # Keyed on the question id, so the answer holds whatever order concurrent requests run in.
            reply = reply[question_id]
        return reply(state, question) if callable(reply) else reply

    def entries(self, kind=None):
        return [e for e in load(self.repo, self.cid).get('classifications', []) if kind in (None, e['kind'])]

    def legacy_entries(self):
        """The original four kinds, named explicitly by pre-hook regression assertions."""
        return [entry for entry in self.entries() if entry['kind'] in LEGACY_KINDS]

    def op(self, request, **kwargs):
        with self.engine_questions():
            return super().op(request, **kwargs)

    def write_result(self, prepared, **kwargs):
        super().write_result(prepared, **kwargs)
        path = Path(prepared['result_path'])
        lines = path.read_text().rstrip().splitlines()
        marker = lines.pop() if lines and lines[-1].startswith('Result-End:') else None
        lines += ['', '## Evidence', 'commit:' + self.git('rev-parse', 'HEAD'), 'path:src/a.py:1']
        if marker is not None:
            lines.append(marker)
        path.write_text('\n'.join(lines) + '\n')

    def cli(self, *argv, cid=None):
        out = io.StringIO()
        with self.engine_questions(), contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), *argv[:1], cid or self.cid, *argv[1:]])
        return code, json.loads(out.getvalue())

    def inspect(self, **extra):
        return self.ok({'op': 'inspect', 'host': 'claude-code', **extra})

    def refused_with_entry(self, request, *codes):
        """A refusal that wrote only classification entries: every other field of the record is unchanged."""
        before = json.loads(self.record_path().read_text())
        code, response = self.op(request)
        self.assertEqual(code, 1, response)
        self.assertEqual(sorted(e['code'] for e in response['errors']), sorted(codes))
        after = json.loads(self.record_path().read_text())
        for key in ('classifications', 'history', 'revision', 'updated_at'):
            before.pop(key, None); after.pop(key, None)
        self.assertEqual(before, after, 'a refusal wrote more than the classification entry')
        return response

    # scenarios
    def ready_for_review(self):
        """Test phase with a passing receipt attached by the next typed advance; returns the receipt id."""
        self.to_test()
        return self.receipt()

    def add_review_task(self, description='review the change'):
        mutate(self.repo, self.cid, 'task-add', task={'id': 'review-it', 'phase': 'review', 'description': description, 'depends_on': [],
                                                       'status': 'pending', 'expected_evidence': ['report']})

    def enter_review(self, *replies):
        """Run the Test-to-Review advance with scripted replies; return the response.

        One Outcome answers every review-routing predicate through `review_reply`; it stays in force for later
        review questions until a test clears `self.review`. Several replies, or a callable, are scripted in order."""
        receipt = self.ready_for_review()
        if len(replies) == 1 and isinstance(replies[0], decisions.Outcome):
            self.review = review_reply(replies[0])
            self.replies[:] = []
        else:
            self.replies[:] = list(replies)
        response = self.ok(self.advance('advance-t1'))
        self.receipt_id = receipt
        return response

    def review_entry(self, ident=None):
        """The review-routing entry for one specialist: the named one, else the one an add answer chose, else the first."""
        entries = self.entries('review-routing')
        if ident is None:
            ident = next((e['route'][4:] for e in entries if (e.get('route') or '').startswith('add:')), None)
        if ident is None:
            return entries[0]
        return next(e for e in entries if e['subject'] == 'review:' + ident)

    def record_review(self, receipt, report=None):
        report = {**REVIEW, 'evidence': [receipt], **(report or {})}
        return self.cli('review', '--json', json.dumps(report))

    def blocking_report(self):
        return {'verdict': 'changes-required', 'blocking': [BLOCKING],
                'advisory': ['LEAK-ZQ-advisory consider a docstring'], 'cosmetic': ['LEAK-ZQ-cosmetic trailing space']}

    def review_with_findings(self, *replies, report=None):
        """Enter Review with the classifier answering `floor-only`, then record a report; the replies answer its findings."""
        self.enter_review(answered('floor-only'))
        self.asked.clear()
        self.replies[:] = list(replies)
        return self.record_review(self.receipt_id, report or self.blocking_report())

    def failed_delivery(self, *replies):
        prepared = self.prepare()
        self.write_result(prepared)
        self.replies[:] = list(replies)
        return self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'failed'})

    def second_reservation(self, op_id='prep-0002'):
        return {'op': 'prepare-dispatch', 'op_id': op_id, 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code', 'assignment_text': 'text'}

    def lose(self, op_id, attempt=1, assignment='build-it'):
        """Typed mark-lost on the owner's confirmation, which releases the task for another attempt."""
        return self.ok({'op': 'mark-lost', 'op_id': op_id, 'assignment': assignment, 'attempt': attempt, 'note': 'the owner confirmed the session ended',
                        'evidence': {'kind': 'owner-confirmation', 'detail': 'the owner confirmed the dispatching session has ended'}})

    def failing_receipt(self):
        return execute(self.repo, FAILING)['evidence']['id']


__all__ = ['ClassifyBase', 'SimulatedCrash', 'answered', 'failed', 'review_reply', 'MODEL', 'BLOCKING', 'PASSING', 'FAILING', 'REVIEW']
