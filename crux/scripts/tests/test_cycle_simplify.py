"""The simplify cycle type: selection authority, reduction record, gates, review basis, queue start.

Every test runs in a temporary repository whose docs_dir is `notes`.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_queue
from cycle_workflow import CycleError, LIMITS, PHASES, create, digest, encoded, load, mutate, retained, review_basis_digest, tree, validate

DATE = '2026-10-19'
AREAS = ('production', 'tests', 'instructions', 'execution')
# Digests of a fixed non-simplify record, computed with the unmodified function before simplify existed.
PINNED = {1: 'deaf1c82c7df731da70db13c16bff54df272c55a2ab728ac1c177f95c0076e3e',
          2: '6fd024c0e92232c49a0fbb65f455250c75210c682417de749ae883fdc0ec75e7',
          3: '589526a1529c1910949e3d805f147ebc663dfbfd31884c25d705cb5027fc5705'}


def proposal(pid='P1', paths=('src/a.py',), **override):
    value = {'id': pid, 'removes': 'the unused helper', 'retained_behavior': 'a.py answers as before', 'objectives': ['OBJ-5'],
             'decision_clauses': ['none: no rule names the helper'], 'expected_savings': 'one function and its test',
             'verification': 'focused tests', 'paths': list(paths)}
    value.update(override)
    return value


def selection(**override):
    value = {k: ['reason'] for k in ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence')}
    value.update(assessed='the helper module, after ADR-0001', proposals=[proposal('P1'), proposal('P2', ('src/b.py',))], selected=['P1'])
    value.update(override)
    return value


def reduction(**changes):
    areas = {a: {'change': 'unchanged', 'before': 'one', 'after': 'one', 'evidence': ['git diff']} for a in AREAS}
    areas['production'] = {'change': 'decrease', 'before': 'two functions', 'after': 'one function', 'evidence': ['git diff src/a.py']}
    for area, change in changes.items():
        areas[area] = {**areas[area], 'change': change}
    return {'areas': areas}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: notes\n')
        (self.repo / 'notes').mkdir()
        (self.repo / 'notes/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'notes/objectives.md').write_text('Mission: useful changes.')
        for name in ('src', 'other'):
            (self.repo / name).mkdir()
        (self.repo / 'src/a.py').write_text('x = 1\n')
        (self.repo / 'src/b.py').write_text('y = 1\n')
        (self.repo / 'other/c.py').write_text('z = 1\n')

    # -- helpers -----------------------------------------------------------
    def apply(self, doc, action, **args):
        return mutate(self.repo, doc['id'], action, **args)

    def direct(self, kind='simplify'):
        return create(self.repo, kind, 'Simplify', 'Remove the helper', ['src'], ['Behavior preserved'], 'builder', 'tester')

    def queue_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'queue', *argv])
        return code, json.loads(out.getvalue())

    def queued(self, kind='simplify', scope='src'):
        code, got = self.queue_cli('add', '--title', 'Trim', '--outcome', 'Remove the helper', '--type', kind, '--scope', scope, '--acceptance', 'it works')
        self.assertEqual(code, 0, got)
        code, got = self.queue_cli('authorize', '--kind', 'next', '--instruction', 'run it', '--date', DATE)
        self.assertEqual(code, 0, got)
        code, got = self.queue_cli('start-next')
        self.assertEqual(code, 0, got)
        return load(self.repo, got['cycle'])

    def replan(self, doc, scope=None):
        plan = deepcopy(doc['plan'])
        plan.update(verification=['focused tests'], tasks=[{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['observation']} for p in PHASES[doc['type']]])
        if scope is not None:
            plan['scope'] = scope
        return self.apply(doc, 'plan', plan=plan, reason='plan')

    def record(self, doc, contents=None, name='selection'):
        doc = self.apply(doc, 'decision', kind='idr', name=name, contents=contents or selection())
        return doc, doc['decisions'][-1]['path']

    def council(self, doc, subject):
        cfg = tree(self.repo)
        value = {'format': 'crux.cycle-council', 'purpose': 'idr', 'subject': subject, 'subject_sha256': digest((cfg.docs_root / subject).read_bytes()), 'cycle_id': doc['id'],
                 'outcome': 'approved', 'seats': [{'provider': p, 'decision': 'APPROVE', 'errored': False, 'findings': []} for p in ('openai', 'anthropic', 'google')]}
        value['record_sha256'] = digest(encoded(value))
        return retained(cfg, doc['id'], 'councils', value)['path']

    def owner(self, doc, subject):
        cfg = tree(self.repo)
        value = {'format': 'crux.owner-approval', 'purpose': 'idr', 'cycle_id': doc['id'], 'subject': subject, 'subject_sha256': digest((cfg.docs_root / subject).read_bytes()),
                 'origin': 'owner-conversation', 'quote': 'I select P1. Proceed.', 'date': DATE, 'conversation': 'owner conversation'}
        path = f"cycles/{doc['id']}/approvals/owner-{Path(subject).stem}.json"
        (cfg.docs_root / path).parent.mkdir(parents=True, exist_ok=True)
        (cfg.docs_root / path).write_text(json.dumps(value))
        return path

    def approved(self, doc, authority, contents=None, scope=None):
        doc = self.replan(doc, scope)
        doc, subject = self.record(doc, contents)
        approval = self.council(doc, subject) if authority == 'council' else self.owner(doc, subject)
        return self.apply(doc, 'approve-decision', subject=subject, approval=approval)

    def finish(self, doc):
        for task in doc['plan']['tasks']:
            if task['phase'] == doc['phase']:
                doc = self.apply(doc, 'task', task_id=task['id'], state='done')
        return self.apply(doc, 'advance')

    def to_test(self, doc):
        """Advance an approved simplify cycle from Plan to the Test phase."""
        doc = self.finish(doc)
        doc = self.finish(doc)
        self.assertEqual(doc['phase'], 'test')
        return doc


class TypeTests(Base):
    def test_type_has_five_phases_and_limit_three(self):
        self.assertEqual(PHASES['simplify'], ['plan', 'build', 'test', 'review', 'reflect'])
        self.assertEqual(LIMITS['simplify'], 3)
        doc = self.direct()
        self.assertEqual((doc['type'], doc['phase'], doc['pass_limit']), ('simplify', 'plan', 3))

    def test_schema_accepts_the_type_and_an_optional_reduction(self):
        doc = self.direct()
        validate(doc)
        doc['reduction'] = {'pass': 1, 'at': 'now', 'input_sha256': '0' * 64, 'areas': reduction()['areas']}
        validate(doc)
        broken = deepcopy(doc)
        broken['reduction'].pop('input_sha256')
        with self.assertRaises(CycleError):
            validate(broken)

    def test_queue_start_next_starts_a_simplify_item(self):
        doc = self.queued()
        self.assertEqual((doc['type'], doc['phase'], doc['pass_limit']), ('simplify', 'plan', 3))
        self.assertEqual(doc['history'][0]['queue']['item'], 'Q-0001')


class SelectionTests(Base):
    def test_owner_approval_is_accepted_without_a_queue_origin(self):
        doc = self.approved(self.direct(), 'owner')
        self.assertEqual(self.finish(doc)['phase'], 'build')

    def test_owner_approval_is_accepted_with_a_queue_origin_even_outside_the_item_scope(self):
        doc = self.approved(self.queued(), 'owner', scope=['src', 'other'])
        self.assertEqual(self.finish(doc)['phase'], 'build')

    def test_council_approval_is_accepted_for_a_queue_cycle_inside_the_item_scope(self):
        doc = self.approved(self.queued(), 'council')
        self.assertEqual(self.finish(doc)['phase'], 'build')

    def test_council_approval_is_accepted_for_a_plan_scope_narrower_than_the_item_scope(self):
        doc = self.approved(self.queued(scope='src'), 'council', scope=['src/a.py'], contents=selection(proposals=[proposal('P1')]))
        self.assertEqual(self.finish(doc)['phase'], 'build')

    def test_council_approval_is_refused_without_a_queue_origin(self):
        doc = self.approved(self.direct(), 'council')
        with self.assertRaisesRegex(CycleError, 'owner selection is required'):
            self.finish(doc)

    def test_council_approval_is_refused_when_the_plan_scope_leaves_the_item_scope(self):
        doc = self.approved(self.queued(), 'council', scope=['src', 'other'])
        with self.assertRaisesRegex(CycleError, 'owner selection is required outside a scope authorized in advance'):
            self.finish(doc)

    def test_selected_paths_outside_the_plan_scope_are_refused(self):
        contents = selection(proposals=[proposal('P1', ('other/c.py',))])
        doc = self.approved(self.direct(), 'owner', contents=contents)
        with self.assertRaisesRegex(CycleError, 'outside the plan scope'):
            self.finish(doc)

    def test_unselected_paths_outside_the_plan_scope_are_allowed(self):
        contents = selection(proposals=[proposal('P1'), proposal('P2', ('other/c.py',))], selected=['P1'])
        doc = self.approved(self.direct(), 'owner', contents=contents)
        self.assertEqual(self.finish(doc)['phase'], 'build')

    def test_a_simplify_cycle_without_an_idr_is_refused(self):
        doc = self.replan(self.direct())
        with self.assertRaisesRegex(CycleError, 'IDR'):
            self.finish(doc)

    def test_a_plain_idr_without_selection_keys_is_refused(self):
        plain = {k: ['reason'] for k in ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence')}
        doc = self.approved(self.direct(), 'owner', contents=plain)
        with self.assertRaisesRegex(CycleError, 'selection'):
            self.finish(doc)

    def test_malformed_selection_idrs_are_refused(self):
        cases = {
            'assessed': selection(assessed=' '),
            'proposals': selection(proposals=[], selected=[]),
            'selected': selection(selected=[]),
            'subset': selection(selected=['P9']),
            'duplicate': selection(proposals=[proposal('P1'), proposal('P1')]),
            'extra key': selection(proposals=[proposal('P1', extra='x')]),
            'missing key': selection(proposals=[{k: v for k, v in proposal('P1').items() if k != 'verification'}]),
            'objectives': selection(proposals=[proposal('P1', objectives=[])]),
            'clauses': selection(proposals=[proposal('P1', decision_clauses=[])]),
            'none mixed': selection(proposals=[proposal('P1', decision_clauses=['none: reason', 'rule:x'])]),
            'none without reason': selection(proposals=[proposal('P1', decision_clauses=['none'])]),
            'paths': selection(proposals=[proposal('P1', paths=[])]),
        }
        for label, contents in cases.items():
            with self.subTest(label):
                doc = self.approved(self.direct(), 'owner', contents=contents)
                with self.assertRaises(CycleError):
                    self.finish(doc)

    def test_two_current_selection_revisions_are_refused(self):
        doc = self.replan(self.direct())
        doc, first = self.record(doc, selection(), name='one')
        doc = self.apply(doc, 'approve-decision', subject=first, approval=self.owner(doc, first))
        doc, second = self.record(doc, selection(), name='two')
        doc = self.apply(doc, 'approve-decision', subject=second, approval=self.owner(doc, second))
        with self.assertRaisesRegex(CycleError, 'exactly one'):
            self.finish(doc)

    def test_a_new_revision_needs_its_own_approval(self):
        doc = self.approved(self.direct(), 'owner')
        doc, _ = self.record(doc, selection(selected=['P2']))
        with self.assertRaisesRegex(CycleError, 'not approved'):
            self.finish(doc)

    def test_a_non_simplify_cycle_ignores_the_selection_rules(self):
        doc = self.direct('dev')
        doc = self.replan(doc)
        plain = {k: ['reason'] for k in ('alternatives', 'approach', 'assumptions', 'constraints', 'intended_evidence')}
        doc, subject = self.record(doc, plain)
        doc = self.apply(doc, 'approve-decision', subject=subject, approval=self.council(doc, subject))
        self.assertEqual(self.finish(doc)['phase'], 'build')


class ReductionTests(Base):
    def at_test(self):
        return self.to_test(self.approved(self.direct(), 'owner'))

    def write(self, doc, value):
        return self.apply(doc, 'reduction', reduction=value)

    def advance_test(self, doc):
        with patch('cycle_workflow.check_tests'):
            return self.finish(doc)

    def test_reduction_is_refused_outside_the_test_phase(self):
        doc = self.approved(self.direct(), 'owner')
        with self.assertRaisesRegex(CycleError, 'Test phase'):
            self.write(doc, reduction())

    def test_reduction_is_refused_outside_simplify(self):
        doc = self.direct('iterate')
        with self.assertRaisesRegex(CycleError, 'simplify'):
            self.write(doc, reduction())

    def test_reduction_structure_is_validated(self):
        doc = self.at_test()
        bad = {}
        bad['no areas'] = {}
        bad['extra top key'] = {**reduction(), 'total': 3}
        bad['missing area'] = {'areas': {k: v for k, v in reduction()['areas'].items() if k != 'tests'}}
        bad['extra area'] = {'areas': {**reduction()['areas'], 'docs': reduction()['areas']['tests']}}
        bad['bad change'] = reduction()
        bad['bad change']['areas']['tests']['change'] = 'smaller'
        bad['empty before'] = reduction()
        bad['empty before']['areas']['tests']['before'] = ' '
        bad['no evidence'] = reduction()
        bad['no evidence']['areas']['tests']['evidence'] = []
        bad['extra area key'] = reduction()
        bad['extra area key']['areas']['tests']['score'] = 1
        for label, value in bad.items():
            with self.subTest(label):
                with self.assertRaises(CycleError):
                    self.write(doc, value)
        self.assertNotIn('reduction', load(self.repo, doc['id']))

    def test_reduction_is_stored_with_pass_time_and_source_fingerprint_and_recorded_in_history(self):
        from cycle_workflow import source_fingerprint
        doc = self.write(self.at_test(), reduction())
        stored = doc['reduction']
        self.assertEqual(set(stored), {'pass', 'at', 'input_sha256', 'areas'})
        self.assertEqual((stored['pass'], stored['areas']), (1, reduction()['areas']))
        self.assertEqual(stored['input_sha256'], source_fingerprint(self.repo, doc))
        self.assertEqual(doc['history'][-1]['action'], 'reduction')

    def test_test_advance_is_refused_without_a_reduction(self):
        with self.assertRaisesRegex(CycleError, 'reduction'):
            self.advance_test(self.at_test())

    def test_test_advance_is_refused_for_a_stale_reduction(self):
        doc = self.write(self.at_test(), reduction())
        (self.repo / 'src/a.py').write_text('x = 2\n')
        with self.assertRaisesRegex(CycleError, 'stale'):
            self.advance_test(doc)

    def test_test_advance_is_refused_for_any_increase_and_names_the_area(self):
        for area in AREAS:
            with self.subTest(area):
                doc = self.write(self.at_test_fresh(), reduction(**{area: 'increase'}))
                with self.assertRaises(CycleError) as caught:
                    self.advance_test(doc)
                message = str(caught.exception)
                self.assertIn(area, message)
                self.assertIn('queue item', message)
                self.assertIn('owner report', message)
                self.assertIn('different work', message)

    def at_test_fresh(self):
        # A new cycle per subtest: ids are allocated in order, so the directory stays valid.
        return self.to_test(self.approved(self.direct(), 'owner'))

    def test_every_increasing_area_is_named(self):
        doc = self.write(self.at_test(), reduction(tests='increase', execution='increase'))
        with self.assertRaisesRegex(CycleError, 'tests, execution'):
            self.advance_test(doc)

    def test_test_advance_is_refused_without_a_decrease(self):
        value = reduction()
        value['areas']['production']['change'] = 'unchanged'
        doc = self.write(self.at_test(), value)
        with self.assertRaisesRegex(CycleError, 'decrease'):
            self.advance_test(doc)

    def test_a_decrease_cannot_net_an_increase(self):
        doc = self.write(self.at_test(), reduction(tests='increase'))
        with self.assertRaisesRegex(CycleError, 'tests'):
            self.advance_test(doc)

    def test_test_advance_is_accepted_with_a_decrease_and_no_increase(self):
        doc = self.write(self.at_test(), reduction())
        self.assertEqual(self.advance_test(doc)['phase'], 'review')

    def test_a_reduction_from_an_earlier_pass_is_stale(self):
        doc = self.write(self.at_test(), reduction())
        path = tree(self.repo).docs_root / 'cycles' / doc['id'] / 'cycle.json'
        stale = json.loads(path.read_text())
        stale['reduction']['pass'] = 2
        path.write_text(json.dumps(stale))
        with self.assertRaisesRegex(CycleError, 'stale'):
            self.advance_test(load(self.repo, doc['id']))

    def to_reflect(self):
        doc = self.write(self.at_test(), reduction())
        doc = self.advance_test(doc)
        report = {'reviewer': 'other', 'scope': ['src'], 'evidence': ['TE-example'], 'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve', 'rationale': 'selected proposals reviewed'}
        with patch('cycle_workflow.check_tests'):
            doc = self.apply(doc, 'review', report=report)
            doc = self.finish(doc)
        self.assertEqual(doc['phase'], 'reflect')
        return doc

    def complete(self, doc):
        doc = self.apply(doc, 'reflect', reflection={'outcome': 'removed', 'lessons': ['none'], 'remaining': ['none']})
        doc = self.apply(doc, 'completion', commits=[], exception='Fixture owner requests uncommitted delivery.', remaining='none')
        with patch('cycle_workflow.check_tests'):
            for task in doc['plan']['tasks']:
                if task['phase'] == 'reflect':
                    doc = self.apply(doc, 'task', task_id=task['id'], state='done')
            return self.apply(doc, 'advance')

    def tamper(self, doc, change):
        path = tree(self.repo).docs_root / 'cycles' / doc['id'] / 'cycle.json'
        stored = json.loads(path.read_text())
        change(stored)
        path.write_text(json.dumps(stored))

    def test_completion_is_accepted_with_a_current_reduction(self):
        self.assertEqual(self.complete(self.to_reflect())['status'], 'completed')

    def test_completion_is_refused_without_a_reduction(self):
        doc = self.to_reflect()
        self.tamper(doc, lambda d: d.pop('reduction'))
        with self.assertRaisesRegex(CycleError, 'reduction'):
            self.complete(load(self.repo, doc['id']))

    def test_completion_is_refused_for_an_increase(self):
        doc = self.to_reflect()
        self.tamper(doc, lambda d: d['reduction']['areas']['instructions'].update(change='increase'))
        with self.assertRaisesRegex(CycleError, 'instructions'):
            self.complete(load(self.repo, doc['id']))

    def test_completion_is_refused_without_a_decrease(self):
        doc = self.to_reflect()
        self.tamper(doc, lambda d: d['reduction']['areas']['production'].update(change='unchanged'))
        with self.assertRaisesRegex(CycleError, 'decrease'):
            self.complete(load(self.repo, doc['id']))

    def test_completion_is_refused_for_a_stale_reduction(self):
        doc = self.to_reflect()
        (self.repo / 'src/a.py').write_text('x = 3\n')
        with self.assertRaisesRegex(CycleError, 'stale'):
            self.complete(doc)

    def test_cli_reduction_command_reads_a_file(self):
        doc = self.at_test()
        path = self.repo / 'reduction.json'
        path.write_text(json.dumps(reduction()))
        out = io.StringIO()
        with redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'reduction', doc['id'], '--file', str(path)])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn('reduction', load(self.repo, doc['id']))
        path.write_text(json.dumps({'areas': {}}))
        with redirect_stdout(io.StringIO()) as bad:
            code = cycle.main(['--repo-root', str(self.repo), 'reduction', doc['id'], '--file', str(path)])
        self.assertEqual(code, 1)

    def test_cli_create_accepts_the_type(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'create', '--type', 'simplify', '--title', 'T', '--goal', 'G', '--implementer', 'b', '--coordinator', 'c', '--scope', 'src', '--acceptance', 'ok'])
        self.assertEqual(code, 0, out.getvalue())


class ChangeTypeTests(Base):
    def test_leaving_simplify_requires_human_approval(self):
        doc = self.direct()
        with self.assertRaisesRegex(CycleError, 'human approval'):
            self.apply(doc, 'change-type', kind='dev', reason='bigger')
        changed = self.apply(doc, 'change-type', kind='dev', reason='bigger', human_approval='Owner: make it dev')
        self.assertEqual(changed['type'], 'dev')
        event = next(h for h in changed['history'] if h['action'] == 'type-changed')
        self.assertEqual((event['previous_type'], event['human_approval']), ('simplify', 'Owner: make it dev'))

    def test_entering_simplify_needs_no_approval(self):
        doc = self.direct('dev')
        self.assertEqual(self.apply(doc, 'change-type', kind='simplify', reason='narrower')['type'], 'simplify')


class ReviewBasisTests(Base):
    at_test = ReductionTests.at_test
    write = ReductionTests.write
    advance_test = ReductionTests.advance_test
    to_reflect = ReductionTests.to_reflect
    tamper = ReductionTests.tamper

    def test_non_simplify_digests_are_unchanged(self):
        doc = {'type': 'dev', 'schema_version': 2, 'pass': 1, 'required_checks': ['unit'], 'review_policy': {'scrutiny': 'standard', 'rationale': 'repository default', 'risks': []},
               'evidence': [{'check_id': 'unit', 'evidence_id': 'TE-1', 'pass': 1, 'use': 'executed'}], 'coverage': {'affected': ['a'], 'checks': [{'check_id': 'unit', 'rationale': 'r'}], 'not_selected': 'none'},
               'plan': {'revision': 2, 'scope': ['src'], 'constraints': [], 'acceptance': ['ok'], 'verification': ['v'], 'tasks': [
                   {'id': 't', 'phase': 'build', 'description': 'd', 'depends_on': [], 'status': 'done', 'expected_evidence': ['e']},
                   {'id': 'r', 'phase': 'reflect', 'description': 'd', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['e']}]}}
        for version, expected in PINNED.items():
            self.assertEqual(review_basis_digest(doc, version), expected)
        doc['reduction'] = {'pass': 1}
        for version, expected in PINNED.items():
            self.assertEqual(review_basis_digest(doc, version), expected)

    def test_simplify_version_three_digest_binds_the_reduction_only_there(self):
        doc = self.write(self.at_test(), reduction())
        changed = deepcopy(doc)
        changed['reduction']['areas']['tests']['after'] = 'different'
        self.assertNotEqual(review_basis_digest(doc, 3), review_basis_digest(changed, 3))
        self.assertEqual(review_basis_digest(doc, 2), review_basis_digest(changed, 2))
        self.assertEqual(review_basis_digest(doc, 1), review_basis_digest(changed, 1))

    def test_a_reduction_changed_after_review_invalidates_the_review(self):
        doc = self.to_reflect()
        self.tamper(doc, lambda d: d['reduction']['areas']['tests'].update(after='changed after approval'))
        from cycle_workflow import check_review
        with self.assertRaisesRegex(CycleError, 'independent review'):
            check_review(tree(self.repo), load(self.repo, doc['id']))


if __name__ == '__main__':
    unittest.main()
