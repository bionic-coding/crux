"""Review basis versioning: bookkeeping after approval keeps the review binding."""
import contextlib
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_workflow as workflow
from cycle_workflow import CycleError, PHASES
from test_evidence import execute

FIXTURES = Path(__file__).resolve().parent / 'fixtures/cycle-records'
REVIEW_REQUIRED = 'a passing independent review of the current scope is required'


class CliCycleCase(unittest.TestCase):
    """Drives the real writer through the `cycle.py` entry point in a temp tree."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        env = patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.root / 'evidence')})
        env.start()
        self.addCleanup(env.stop)
        (self.root / 'bionic').mkdir()
        (self.root / 'src').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root / 'src/a.txt').write_text('good')

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.root), *argv])
        return code, json.loads(out.getvalue())

    def ok(self, *argv):
        code, payload = self.run_cli(*argv)
        self.assertEqual(code, 0, payload)
        return payload['cycle']

    def refused(self, *argv):
        code, payload = self.run_cli(*argv)
        self.assertEqual(code, 1, payload)
        self.assertFalse(payload['ok'])
        return payload['error']

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return str(path)

    def decl(self, check_id='unit'):
        return {'check_id': check_id, 'command': [sys.executable, '-c', "from pathlib import Path; assert Path('src/a.txt').read_text() == 'good'"], 'inputs': ['src'], 'environment': []}

    def coverage(self, checks=('unit',), not_selected='No unrelated suite needed.'):
        return {'affected': ['src'], 'checks': [{'check_id': c, 'rationale': 'exercises the source'} for c in checks], 'not_selected': not_selected}

    def task(self, phase, status='pending', identity=None):
        return {'id': identity or 'extra-' + phase, 'phase': phase, 'description': 'd', 'depends_on': [], 'status': status, 'expected_evidence': ['e']}

    def create_quick_fix(self):
        doc = self.ok('create', '--type', 'quick-fix', '--title', 'Fix', '--goal', 'Outcome', '--implementer', 'builder', '--coordinator', 'tester', '--scope', 'src', '--acceptance', 'correct')
        return doc['id']

    def approved_quick_fix(self, checks=('unit',), build_tasks=()):
        """Create, build, test and approve a quick-fix; return its id (phase review, approved)."""
        cid = self.create_quick_fix()
        for identity in build_tasks:
            self.ok('task-add', cid, '--file', self.write_json(identity + '.json', self.task('build', identity=identity)))
            self.ok('task', cid, '--task-id', identity, '--state', 'done')
        self.ok('checks', cid, *[a for c in checks for a in ('--check', c)])
        self.ok('coverage', cid, '--file', self.write_json('coverage.json', self.coverage(checks)))
        self.ok('advance', cid)
        self.evidence_ids = {}
        for check in checks:
            result = execute(self.root, self.decl(check))
            self.evidence_ids[check] = result['evidence']['id']
            self.ok('evidence', cid, '--check-id', check, '--evidence-id', result['evidence']['id'], '--use', result['action'])
        doc = self.ok('advance', cid)
        self.assertEqual(doc['phase'], 'review')
        report = {'reviewer': 'independent', 'scope': ['src'], 'evidence': list(self.evidence_ids.values()), 'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve', 'rationale': 'reviewed changes and acceptance evidence'}
        self.ok('review', cid, '--file', self.write_json('report.json', report))
        return cid


class ReflectTaskAfterApprovalTests(CliCycleCase):
    def test_reflect_task_added_after_approval_still_completes(self):
        """A1/A2: the historian adds a reflect task after approval; the cycle completes."""
        cid = self.approved_quick_fix()
        self.ok('advance', cid)
        task = {'id': 'historian-reflect', 'phase': 'reflect', 'description': 'record lessons', 'depends_on': [], 'status': 'pending', 'expected_evidence': ['reflection']}
        self.ok('task-add', cid, '--file', self.write_json('task.json', task))
        self.ok('task', cid, '--task-id', 'historian-reflect', '--state', 'done')
        self.ok('reflect', cid, '--file', self.write_json('reflection.json', {'outcome': 'fixed', 'lessons': 'none', 'remaining': 'none'}))
        self.ok('completion', cid, '--exception', 'Fixture owner requests uncommitted delivery.', '--remaining', 'none')
        doc = self.ok('advance', cid)
        self.assertEqual(doc['status'], 'completed')

    def test_new_review_records_basis_version_four(self):
        cid = self.approved_quick_fix()
        doc = workflow.load(self.root, cid)
        report = workflow.read_retained(workflow.tree(self.root), doc['reviews'][-1])
        self.assertEqual(report['basis_version'], 4)
        self.assertEqual(report['basis_sha256'], workflow.review_basis(doc))


class ChangesAfterApprovalTests(CliCycleCase):
    """A3: material changes after approval make `advance` refuse; each has a positive control."""

    def change_checks_order(self, cid):
        self.ok('checks', cid, '--check', 'other', '--check', 'unit')

    def change_scrutiny(self, cid):
        self.ok('scrutiny', cid, '--scrutiny', 'intensive', '--rationale', 'raised after approval')

    def change_coverage(self, cid):
        self.ok('coverage', cid, '--file', self.write_json('coverage2.json', self.coverage(('unit', 'other'), 'Changed after approval.')))

    def add_review_task(self, cid):
        self.ok('task-add', cid, '--file', self.write_json('late.json', self.task('review', identity='late-review')))
        self.ok('task', cid, '--task-id', 'late-review', '--state', 'done')

    def test_material_change_after_approval_refuses_advance(self):
        cases = {
            'required checks': self.change_checks_order,
            'review policy': self.change_scrutiny,
            'coverage': self.change_coverage,
            'review-phase task': self.add_review_task,
        }
        for name, change in cases.items():
            with self.subTest(name):
                control = self.approved_quick_fix(('unit', 'other'))
                self.assertEqual(self.ok('advance', control)['phase'], 'reflect')
                cid = self.approved_quick_fix(('unit', 'other'))
                change(cid)
                self.assertEqual(self.refused('advance', cid), REVIEW_REQUIRED)

    def test_reflect_bookkeeping_after_approval_keeps_binding(self):
        """Positive control for the refusals above: reflect tasks and status changes keep the binding."""
        cid = self.approved_quick_fix()
        self.ok('advance', cid)
        for index in range(2):
            identity = f'reflect-{index}'
            self.ok('task-add', cid, '--file', self.write_json('t.json', self.task('reflect', identity=identity)))
            self.ok('task', cid, '--task-id', identity, '--state', 'done')
        workflow.check_review(workflow.tree(self.root), workflow.load(self.root, cid))


class DirectBasisTests(CliCycleCase):
    """Changes the writer forbids after approval, or that need a phase it no longer offers.

    `plan` needs the Plan phase and `plan-details` needs Build or Test, so no
    CLI path edits scope, constraints, acceptance or verification once a review
    exists, and quick-fix refuses build/test tasks in Review. These tests call
    `review_basis` and `check_review` on an in-memory edit of the loaded record.
    """

    def setUp(self):
        super().setUp()
        self.cid = self.approved_quick_fix()
        self.cfg = workflow.tree(self.root)
        self.doc = workflow.load(self.root, self.cid)

    def edited(self, edit):
        doc = deepcopy(self.doc)
        edit(doc)
        return doc

    def test_positive_control_unedited_record_binds(self):
        self.assertEqual(workflow.check_review(self.cfg, self.doc)['verdict'], 'approve')

    def test_plan_fields_change_the_basis_and_refuse(self):
        edits = {
            'constraints': lambda d: d['plan'].update(constraints=['new']),
            'acceptance': lambda d: d['plan'].update(acceptance=['new']),
            'verification': lambda d: d['plan'].update(verification=['new']),
            'build task': lambda d: d['plan']['tasks'].append(self.task('build')),
            'test task': lambda d: d['plan']['tasks'].append(self.task('test')),
            'review task': lambda d: d['plan']['tasks'].append(self.task('review')),
        }
        base = workflow.review_basis(self.doc)
        for name, edit in edits.items():
            with self.subTest(name):
                doc = self.edited(edit)
                self.assertNotEqual(workflow.review_basis(doc), base)
                with self.assertRaisesRegex(CycleError, 'independent review'):
                    workflow.check_review(self.cfg, doc)

    def test_scope_change_refuses(self):
        (self.root / 'lib').mkdir()
        (self.root / 'lib/b.txt').write_text('x')
        doc = self.edited(lambda d: d['plan'].update(scope=['src', 'lib']))
        self.assertNotEqual(workflow.review_basis(doc), workflow.review_basis(self.doc))
        with self.assertRaisesRegex(CycleError, 'independent review'):
            workflow.check_review(self.cfg, doc)

    def test_bookkeeping_leaves_the_basis_unchanged(self):
        base = workflow.review_basis(self.doc)
        edits = {
            'reflect task': lambda d: d['plan']['tasks'].append(self.task('reflect')),
            'reflect task done': lambda d: d['plan']['tasks'].append(self.task('reflect', 'done')),
            'reflection': lambda d: d.update(reflection={'outcome': 'o', 'lessons': 'l', 'remaining': 'r'}),
            'completion': lambda d: d.update(completion={'commits': [], 'exception': 'e', 'remaining': 'r'}),
            'history': lambda d: d['history'].append({'at': 'x', 'action': 'note', 'pass': 1, 'phase': 'reflect'}),
            'blocker': lambda d: d.update(blocker={'reason': 'r', 'evidence': [], 'next_step': 'n'}),
            'status': lambda d: d.update(status='paused'),
            'plan revision counter': lambda d: d['plan'].update(revision=9),
        }
        for name, edit in edits.items():
            with self.subTest(name):
                self.assertEqual(workflow.review_basis(self.edited(edit)), base)
                workflow.check_review(self.cfg, self.edited(edit))

    def test_only_phases_after_the_review_bearing_phase_are_omitted(self):
        """Each type's later-phase tasks leave the basis; earlier and review-bearing ones stay in it."""
        for kind, sequence in PHASES.items():
            if kind == 'release':
                continue  # a release cycle has no Review phase and no review basis
            bearing = 'review'
            doc = self.edited(lambda d: d.update(type=kind))
            base = workflow.review_basis(doc)
            for phase in sequence:
                with self.subTest(kind=kind, phase=phase):
                    other = self.edited(lambda d: d.update(type=kind))
                    other['plan']['tasks'].append(self.task(phase))
                    changed = workflow.review_basis(other) != base
                    self.assertEqual(changed, sequence.index(phase) <= sequence.index(bearing))
                    # Version 1 hashes the whole plan, so it always changes.
                    self.assertNotEqual(workflow.review_basis_v1(other), workflow.review_basis_v1(doc))


class LegacyAndVersionedReportTests(CliCycleCase):
    """The dual-digest rule, driven through `check_review` on a record whose v1 and v2 differ."""

    def setUp(self):
        super().setUp()
        self.cid = self.approved_quick_fix()
        self.ok('advance', self.cid)
        self.ok('task-add', self.cid, '--file', self.write_json('t.json', self.task('reflect', identity='reflect-note')))
        self.cfg = workflow.tree(self.root)
        self.doc = workflow.load(self.root, self.cid)
        self.v1, self.v2 = workflow.review_basis_v1(self.doc), workflow.review_basis_v2(self.doc)
        self.v3, self.v4 = workflow.review_basis_digest(self.doc, 3), workflow.review_basis(self.doc)
        self.assertNotEqual(self.v1, self.v2)
        self.assertNotEqual(self.v2, self.v3)
        self.assertNotEqual(self.v3, self.v4)

    def rewrite(self, drop=(), **changes):
        """Rewrite the retained report and its reference, as a historical record would hold it."""
        path = self.root / 'bionic/cycles' / self.cid / 'cycle.json'
        doc = json.loads(path.read_text())
        ref = doc['reviews'][-1]
        report_path = self.root / 'bionic' / ref['path']
        report = json.loads(report_path.read_text())
        for key in drop:
            report.pop(key, None)
        report.update(changes)
        data = workflow.encoded(report)
        report_path.write_bytes(data)
        ref['sha256'] = workflow.digest(data)
        path.write_bytes(workflow.encoded(doc))
        self.doc = workflow.load(self.root, self.cid)

    def binds(self):
        try:
            workflow.check_review(self.cfg, self.doc)
            return True
        except CycleError as exc:
            self.assertEqual(str(exc), REVIEW_REQUIRED)
            return False

    def test_legacy_report_binds_to_version_one_or_two(self):
        self.rewrite(drop=('basis_version',), basis_sha256=self.v1)
        self.assertTrue(self.binds())
        self.rewrite(drop=('basis_version',), basis_sha256=self.v2)
        self.assertTrue(self.binds())

    def test_legacy_report_with_another_digest_does_not_bind(self):
        self.rewrite(drop=('basis_version',), basis_sha256='0' * 64)
        self.assertFalse(self.binds())

    def test_version_two_report_binds_only_to_version_two(self):
        self.rewrite(basis_version=2, basis_sha256=self.v2)
        self.assertTrue(self.binds())
        self.rewrite(basis_version=2, basis_sha256=self.v1)
        self.assertFalse(self.binds())

    def test_version_one_report_binds_only_to_version_one(self):
        self.rewrite(basis_version=1, basis_sha256=self.v1)
        self.assertTrue(self.binds())
        self.rewrite(basis_version=1, basis_sha256=self.v2)
        self.assertFalse(self.binds())

    def test_version_three_report_binds_only_to_version_three(self):
        self.rewrite(basis_version=3, basis_sha256=self.v3)
        self.assertTrue(self.binds())
        for other in (self.v1, self.v2, self.v4):
            self.rewrite(basis_version=3, basis_sha256=other)
            self.assertFalse(self.binds())

    def test_version_four_report_binds_only_to_version_four(self):
        self.rewrite(basis_version=4, basis_sha256=self.v4)
        self.assertTrue(self.binds())
        for other in (self.v1, self.v2, self.v3):
            self.rewrite(basis_version=4, basis_sha256=other)
            self.assertFalse(self.binds())

    def test_legacy_report_never_binds_to_version_three_or_four(self):
        for other in (self.v3, self.v4):
            self.rewrite(drop=('basis_version',), basis_sha256=other)
            self.assertFalse(self.binds())

    def test_unknown_version_never_binds(self):
        for version in (5, 0, '4', True, 4.0, [4]):
            with self.subTest(version=repr(version)):
                self.rewrite(basis_version=version, basis_sha256=self.v4)
                self.assertFalse(self.binds())
        self.rewrite(basis_version=4, basis_sha256=self.v4)
        self.assertTrue(self.binds())


class Version4EvidenceTests(CliCycleCase):
    """Acceptance 4: re-running a check against unchanged inputs keeps a recorded review bound."""

    def refresh(self, cid, declaration, use='executed'):
        result = execute(self.root, declaration)
        self.ok('evidence', cid, '--check-id', declaration['check_id'], '--evidence-id', result['evidence']['id'], '--use', use)
        return result['evidence']['id']

    def binds(self, cid):
        try:
            workflow.check_review(workflow.tree(self.root), workflow.load(self.root, cid))
            return True
        except CycleError as exc:
            self.assertEqual(str(exc), REVIEW_REQUIRED)
            return False

    def test_evidence_command_stores_the_normalized_declaration_digest(self):
        from test_evidence import digest, normalize
        cid = self.approved_quick_fix()
        ref = workflow.load(self.root, cid)['evidence'][-1]
        self.assertEqual(ref['declaration_sha256'], digest(normalize(self.decl())))
        self.assertRegex(ref['declaration_sha256'], '^[0-9a-f]{64}$')

    def test_refresh_under_a_new_evidence_id_with_the_same_declaration_keeps_the_review_bound(self):
        cid = self.approved_quick_fix()
        doc = workflow.load(self.root, cid)
        base = workflow.review_basis(doc)
        refreshed = deepcopy(doc)
        latest = refreshed['evidence'][-1]
        refreshed['evidence'].append({**latest, 'evidence_id': 'TE-' + 'f' * 32, 'use': 'executed'})
        self.assertEqual(workflow.review_basis(refreshed), base)
        # Version 3 hashed the evidence list, so the same refresh unbound a review.
        self.assertNotEqual(workflow.review_basis_digest(refreshed, 3), workflow.review_basis_digest(doc, 3))
        workflow.check_review(workflow.tree(self.root), refreshed)

    def test_changed_declaration_under_the_same_check_id_unbinds(self):
        cid = self.approved_quick_fix()
        for name, change in {
            'command': lambda d: d.update(command=[sys.executable, '-c', "from pathlib import Path; assert Path('src/a.txt').exists()"]),
            'inputs': lambda d: d.update(inputs=['src', 'bionic/manifest.yml']),
            'exclusions': lambda d: d.update(exclude_inputs=['src/skip.txt']),
        }.items():
            with self.subTest(name):
                other = self.approved_quick_fix()
                declaration = self.decl()
                change(declaration)
                self.refresh(other, declaration)
                self.assertFalse(self.binds(other))
        self.assertTrue(self.binds(cid))

    def test_scope_change_unbinds(self):
        cid = self.approved_quick_fix()
        doc = workflow.load(self.root, cid)
        (self.root / 'lib').mkdir()
        (self.root / 'lib/b.txt').write_text('x')
        doc['plan']['scope'] = ['src', 'lib']
        with self.assertRaisesRegex(CycleError, 'independent review'):
            workflow.check_review(workflow.tree(self.root), doc)

    def test_legacy_ref_without_the_digest_falls_back_to_its_evidence_id(self):
        cid = self.approved_quick_fix()
        doc = workflow.load(self.root, cid)
        legacy = deepcopy(doc)
        for ref in legacy['evidence']:
            ref.pop('declaration_sha256')
        other = deepcopy(legacy)
        other['evidence'][-1]['evidence_id'] = 'TE-' + 'e' * 32
        self.assertNotEqual(workflow.review_basis(legacy), workflow.review_basis(other))
        self.assertNotEqual(workflow.review_basis(legacy), workflow.review_basis(doc))
        self.assertEqual(workflow.review_basis(legacy), workflow.review_basis(deepcopy(legacy)))

    def test_ref_with_a_malformed_digest_is_refused_by_the_schema(self):
        cid = self.approved_quick_fix()
        doc = workflow.load(self.root, cid)
        workflow.validate(doc)
        legacy = deepcopy(doc)
        legacy['evidence'][-1].pop('declaration_sha256')
        workflow.validate(legacy)
        for bad in ('A' * 64, 'a' * 63):
            broken = deepcopy(doc)
            broken['evidence'][-1]['declaration_sha256'] = bad
            with self.assertRaisesRegex(CycleError, 'invalid cycle'):
                workflow.validate(broken)


class HistoricalRecordTests(unittest.TestCase):
    """A4: committed copies of the first four cycle records, with their stored review digests."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'bionic').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        shutil.copytree(FIXTURES, self.root / 'bionic/cycles')
        self.cfg = workflow.tree(self.root)

    def reviews(self, cid):
        doc = workflow.load(self.root, cid)
        return doc, [workflow.read_retained(self.cfg, ref) for ref in doc['reviews']]

    def digests(self, doc):
        return workflow.review_basis_v1(doc), workflow.review_basis_v2(doc)

    def test_fixtures_exist(self):
        self.assertEqual(sorted(p.name for p in FIXTURES.iterdir()), ['CYC-0001', 'CYC-0002', 'CYC-0003', 'CYC-0004'])

    def test_every_fixture_record_validates_through_the_cli(self):
        for number in range(1, 5):
            cid = f'CYC-000{number}'
            with self.subTest(cid):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = cycle.main(['--repo-root', str(self.root), 'validate', cid, '--full'])
                self.assertEqual(code, 0, out.getvalue())
                self.assertEqual(json.loads(out.getvalue())['cycle']['id'], cid)

    def test_cyc_0004_review_matches_version_two_only(self):
        doc, (report,) = self.reviews('CYC-0004')
        v1, v2 = self.digests(doc)
        self.assertEqual(report['basis_sha256'], '39a946568330ca6c691c1433a0a491d820ba36d3a4af3ab9450369b03b1bb422')
        self.assertEqual(v2, report['basis_sha256'])
        self.assertNotEqual(v1, report['basis_sha256'])
        self.assertNotIn('basis_version', report)
        self.assertTrue(workflow.basis_binds(report, v1, v2))

    def test_earlier_records_match_version_one(self):
        expected = {
            'CYC-0001': ('74432ef0b44c01f8fcc331430a0397026f8a999f99943c4df05018199ef52df5', 1),
            'CYC-0002': ('72ebc4f5528bfcb3ff1dba752bad8c72daa422f8484f7dc42df56249743bb014', 2),
            'CYC-0003': ('6fdae71c020a074687ed102e08d3975cbe247be42a7a7f0085f827640c660a1c', 1),
        }
        for cid, (digest, review_pass) in expected.items():
            with self.subTest(cid):
                doc, reports = self.reviews(cid)
                v1, v2 = self.digests(doc)
                report = next(r for r in reports if r['pass'] == review_pass)
                self.assertEqual(report['basis_sha256'], digest)
                self.assertEqual(v1, digest)
                # The record has reflect tasks, so version 2 differs: the report binds only through the legacy rule.
                self.assertNotEqual(v2, digest)
                self.assertTrue(workflow.basis_binds(report, v1, v2))

    def test_cyc_0002_pass_one_review_matches_neither_version(self):
        doc, reports = self.reviews('CYC-0002')
        earlier = next(r for r in reports if r['pass'] == 1)
        self.assertEqual(earlier['verdict'], 'changes-required')
        self.assertFalse(workflow.basis_binds(earlier, *self.digests(doc)))

    def test_versioned_report_does_not_bind_a_version_one_only_match(self):
        doc, reports = self.reviews('CYC-0001')
        report = dict(reports[0])
        v1, v2 = self.digests(doc)
        self.assertNotEqual(v1, v2)
        self.assertTrue(workflow.basis_binds(report, v1, v2))
        self.assertTrue(workflow.basis_binds({**report, 'basis_version': 1}, v1, v2))
        self.assertFalse(workflow.basis_binds({**report, 'basis_version': 2}, v1, v2))
        self.assertFalse(workflow.basis_binds({**report, 'basis_version': 3}, v1, v2))
        self.assertFalse(workflow.basis_binds({**report, 'basis_version': 3}, v1, v2, '0' * 64))
        self.assertFalse(workflow.basis_binds({**report, 'basis_version': 4}, v1, v2, v2))


class Version3PreservingTests(CliCycleCase):
    """The CYC-0015 failure: delivery bookkeeping after approval stopped the review binding."""

    TASK = 'build-work'

    def setUp(self):
        super().setUp()
        env = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}
        for argv in (['init', '-q'], ['add', '-A'], ['commit', '-q', '-m', 'seed']):
            subprocess.run(['git', '-C', str(self.root), *argv], check=True, env={**os.environ, **env})
        self.commit = subprocess.run(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()

    def approved(self):
        return self.approved_quick_fix(build_tasks=(self.TASK,))

    def test_cyc_0015_sequence_keeps_the_binding(self):
        cid = self.approved()
        v2_before = workflow.review_basis_v2(workflow.load(self.root, cid))
        self.ok('task', cid, '--task-id', self.TASK, '--assignee', 'main-session')
        self.ok('task', cid, '--task-id', self.TASK, '--state', 'done', '--commit', self.commit, '--stage', 'integrated', '--note', 'integrated after review')
        doc = workflow.load(self.root, cid)
        self.assertNotEqual(workflow.review_basis_v2(doc), v2_before, 'version 2 loses the approval on these writes')
        self.assertEqual(workflow.check_review(workflow.tree(self.root), doc)['verdict'], 'approve')

    def test_each_bookkeeping_write_keeps_the_binding(self):
        (self.root / 'bionic/result.md').write_text('result')
        (self.root / 'result-file.md').write_text('result')
        writes = {
            'assignee': ('--assignee', 'main-session'),
            'result_path': ('--result-path', str(self.root / 'result-file.md')),
            'commits': ('--commit', self.commit),
            'stage': ('--commit', self.commit, '--stage', 'implemented'),
            'note': ('--note', 'late note'),
            'evidence': ('--evidence', 'result.md'),
            'status': ('--state', 'active'),
        }
        for name, flags in writes.items():
            with self.subTest(name):
                cid = self.approved()
                v2_before = workflow.review_basis_v2(workflow.load(self.root, cid))
                self.ok('task', cid, '--task-id', self.TASK, *flags)
                doc = workflow.load(self.root, cid)
                if name != 'status':
                    self.assertNotEqual(workflow.review_basis_v2(doc), v2_before)
                workflow.check_review(workflow.tree(self.root), doc)

    def test_commits_and_dependencies_keep_the_binding(self):
        cid = self.approved_quick_fix(build_tasks=(self.TASK, 'other-work'))
        doc = workflow.load(self.root, cid)
        base = workflow.review_basis(doc)
        edited = deepcopy(doc)
        task = next(t for t in edited['plan']['tasks'] if t['id'] == self.TASK)
        task['commits'] = ['a' * 40]
        task['depends_on'] = ['other-work']
        self.assertEqual(workflow.review_basis(edited), base)
        workflow.check_review(workflow.tree(self.root), edited)
        self.assertNotEqual(workflow.review_basis_v2(edited), workflow.review_basis_v2(doc))


class Version3InvalidatingTests(CliCycleCase):
    """Material changes still refuse under version 3; the unedited record is the positive control."""

    def setUp(self):
        super().setUp()
        self.cid = self.approved_quick_fix(build_tasks=('build-work',))
        self.cfg = workflow.tree(self.root)
        self.doc = workflow.load(self.root, self.cid)

    def edited(self, edit):
        doc = deepcopy(self.doc)
        edit(doc)
        return doc

    def task_of(self, doc):
        return next(t for t in doc['plan']['tasks'] if t['id'] == 'build-work')

    def test_control_unedited_record_binds(self):
        self.assertEqual(workflow.check_review(self.cfg, self.doc)['verdict'], 'approve')

    def test_material_edits_refuse(self):
        edits = {
            'description': lambda d: self.task_of(d).update(description='changed'),
            'expected_evidence': lambda d: self.task_of(d).update(expected_evidence=['changed']),
            'phase': lambda d: self.task_of(d).update(phase='test'),
            'id': lambda d: self.task_of(d).update(id='renamed'),
            'new pre-review task': lambda d: d['plan']['tasks'].append(self.task('build', identity='added')),
            'scope': lambda d: d['plan'].update(scope=['src', 'lib']),
            'acceptance': lambda d: d['plan'].update(acceptance=['new']),
            'constraints': lambda d: d['plan'].update(constraints=['new']),
            'verification': lambda d: d['plan'].update(verification=['new']),
            'preserved_behavior': lambda d: d['plan'].update(preserved_behavior='new'),
            'improvement': lambda d: d['plan'].update(improvement='new'),
            'required checks': lambda d: d.update(required_checks=['unit', 'extra']),
            'review policy': lambda d: d['review_policy'].update(scrutiny='intensive'),
            'coverage': lambda d: d['coverage'].update(not_selected='changed'),
            'evidence declaration': lambda d: d['evidence'][0].update(declaration_sha256='0' * 64),
        }
        (self.root / 'lib').mkdir()
        (self.root / 'lib/b.txt').write_text('x')
        for name, edit in edits.items():
            with self.subTest(name):
                doc = self.edited(edit)
                self.assertNotEqual(workflow.review_basis(doc), workflow.review_basis(self.doc))
                with self.assertRaisesRegex(CycleError, 'independent review'):
                    workflow.check_review(self.cfg, doc)

    def test_source_change_refuses(self):
        (self.root / 'src/a.txt').write_text('changed after approval')
        with self.assertRaisesRegex(CycleError, 'independent review'):
            workflow.check_review(self.cfg, workflow.load(self.root, self.cid))

    def test_unclassified_task_field_fails_loudly(self):
        doc = self.edited(lambda d: self.task_of(d).update(surprise='x'))
        with self.assertRaisesRegex(CycleError, 'unclassified task field.*surprise'):
            workflow.review_basis(doc)
        # Versions 1 and 2 are unchanged and do not classify.
        workflow.review_basis_v1(doc)
        workflow.review_basis_v2(doc)

    def test_every_schema_task_field_is_classified(self):
        schema = json.loads((Path(__file__).resolve().parents[2] / 'schemas/cycle.schema.json').read_text())
        fields = set(schema['properties']['plan']['properties']['tasks']['items']['properties'])
        classified = set(workflow.TASK_BASIS_FIELDS) | set(workflow.TASK_BOOKKEEPING_FIELDS)
        self.assertEqual(fields, classified)
        self.assertFalse(set(workflow.TASK_BASIS_FIELDS) & set(workflow.TASK_BOOKKEEPING_FIELDS))


class PlanDetailsTests(CliCycleCase):
    """A5: quick-fix plan details and later-phase tasks."""

    def details(self, **value):
        return self.write_json('details.json', value)

    def test_plan_details_replaces_fields_and_keeps_the_previous_plan(self):
        cid = self.create_quick_fix()
        first = self.ok('plan-details', cid, '--file', self.details(constraints=['no new files'], verification=['run unit']), '--reason', 'record scope limits')
        self.assertEqual(first['plan']['constraints'], ['no new files'])
        self.assertEqual(first['plan']['verification'], ['run unit'])
        self.assertEqual(first['plan']['revision'], 2)
        self.assertEqual(first['plan']['acceptance'], ['correct'])
        second = self.ok('plan-details', cid, '--file', self.details(constraints=['only src']), '--reason', 'narrow')
        self.assertEqual(second['plan']['constraints'], ['only src'])
        self.assertEqual(second['plan']['verification'], ['run unit'])
        self.assertEqual(second['plan']['revision'], 3)
        revised = [e for e in second['history'] if e['action'] == 'plan-revised']
        self.assertEqual([e['reason'] for e in revised], ['record scope limits', 'narrow'])
        self.assertEqual(revised[0]['previous']['constraints'], [])
        self.assertEqual(revised[1]['previous']['constraints'], ['no new files'])
        self.assertEqual(revised[1]['previous']['revision'], 2)

    def test_plan_details_is_allowed_in_test(self):
        cid = self.create_quick_fix()
        self.ok('checks', cid, '--check', 'unit')
        self.ok('coverage', cid, '--file', self.write_json('cov.json', self.coverage()))
        self.assertEqual(self.ok('advance', cid)['phase'], 'test')
        doc = self.ok('plan-details', cid, '--file', self.details(verification=['v']), '--reason', 'late detail')
        self.assertEqual(doc['plan']['verification'], ['v'])

    def test_plan_details_refuses_outside_build_and_test(self):
        in_review = self.approved_quick_fix()
        in_reflect = self.approved_quick_fix()
        self.ok('advance', in_reflect)
        for phase, cid in (('review', in_review), ('reflect', in_reflect)):
            with self.subTest(phase):
                self.assertEqual(workflow.load(self.root, cid)['phase'], phase)
                self.assertIn('Build or Test', self.refused('plan-details', cid, '--file', self.details(constraints=['c']), '--reason', 'r'))
        # Positive control: the same file is accepted in Build.
        fresh = self.create_quick_fix()
        self.ok('plan-details', fresh, '--file', self.details(constraints=['c']), '--reason', 'r')

    def test_plan_details_refuses_other_types(self):
        for kind in ('dev', 'iterate', 'refactor'):
            with self.subTest(kind):
                doc = self.ok('create', '--type', kind, '--title', 'T', '--goal', 'G', '--implementer', 'b', '--coordinator', 'c', '--scope', 'src', '--acceptance', 'a')
                self.assertIn('quick-fix', self.refused('plan-details', doc['id'], '--file', self.details(constraints=['c']), '--reason', 'r'))

    def test_plan_details_validates_the_file(self):
        cid = self.create_quick_fix()
        bad = {
            'empty object': {},
            'other key': {'constraints': ['c'], 'scope': ['x']},
            'empty list': {'constraints': []},
            'empty string': {'verification': ['']},
            'blank string': {'verification': ['  ']},
            'non-string item': {'constraints': [1]},
            'non-list': {'constraints': 'c'},
            'not an object': ['constraints'],
        }
        for name, value in bad.items():
            with self.subTest(name):
                code, payload = self.run_cli('plan-details', cid, '--file', self.write_json('bad.json', value), '--reason', 'r')
                self.assertEqual(code, 1)
                self.assertTrue(payload['error'].startswith('plan details must be') or 'non-empty list' in payload['error'], payload)
        code, payload = self.run_cli('plan-details', cid, '--file', self.details(constraints=['c']), '--reason', ' ')
        self.assertEqual(code, 1)
        self.assertIn('reason', payload['error'])
        self.assertEqual(workflow.load(self.root, cid)['plan']['revision'], 1)
        # Positive control: a valid file is accepted.
        self.assertEqual(self.ok('plan-details', cid, '--file', self.details(constraints=['c']), '--reason', 'r')['plan']['revision'], 2)

    def test_quick_fix_task_add_accepts_current_and_later_phases(self):
        cid = self.create_quick_fix()
        for phase in ('build', 'test', 'review', 'reflect'):
            with self.subTest(phase):
                doc = self.ok('task-add', cid, '--file', self.write_json('t.json', self.task(phase)))
                self.assertIn('extra-' + phase, [t['id'] for t in doc['plan']['tasks']])

    def test_quick_fix_task_add_refuses_an_earlier_phase(self):
        cid = self.create_quick_fix()
        self.ok('checks', cid, '--check', 'unit')
        self.ok('coverage', cid, '--file', self.write_json('cov.json', self.coverage()))
        self.assertEqual(self.ok('advance', cid)['phase'], 'test')
        self.assertIn('current or a later phase', self.refused('task-add', cid, '--file', self.write_json('t.json', self.task('build'))))
        # Positive control: the current phase is accepted.
        self.ok('task-add', cid, '--file', self.write_json('t2.json', self.task('test')))

    def test_other_types_keep_the_current_phase_task_rule(self):
        doc = self.ok('create', '--type', 'iterate', '--title', 'T', '--goal', 'G', '--implementer', 'b', '--coordinator', 'c', '--scope', 'src', '--acceptance', 'a')
        # While in Plan, any phase is accepted.
        self.ok('task-add', doc['id'], '--file', self.write_json('t.json', self.task('reflect')))
        plan = deepcopy(doc['plan'])
        plan.update(verification=['v'], tasks=[{'id': p, 'phase': p, 'description': p, 'depends_on': [], 'status': 'pending', 'expected_evidence': ['e']} for p in PHASES['iterate']])
        self.ok('plan', doc['id'], '--file', self.write_json('plan.json', plan), '--reason', 'plan')
        self.ok('task', doc['id'], '--task-id', 'plan', '--state', 'done')
        self.ok('advance', doc['id'])
        self.assertIn('current phase', self.refused('task-add', doc['id'], '--file', self.write_json('t3.json', self.task('reflect', identity='later'))))
        self.ok('task-add', doc['id'], '--file', self.write_json('t4.json', self.task('build', identity='now')))


if __name__ == '__main__':
    unittest.main()
