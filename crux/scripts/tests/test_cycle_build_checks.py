"""Build checks: a cycle declares them in Build and cannot leave Build while one fails."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cycle_workflow import *
from suite_evidence import preset_declaration, registered_declarations
from test_evidence import EvidenceError, execute

CORE = 'checkout:unittest:crux/scripts/tests:test*.py'
TOOLS = 'checkout:unittest:tools/tests:test*.py'
CONTRACT = '''import unittest
from pathlib import Path


class SkillContract(unittest.TestCase):
    def test_no_skill_teaches_the_forbidden_form(self):
        for path in sorted((Path(__file__).resolve().parent.parent / "skills").glob("**/*.md")):
            self.assertNotIn("run-the-old-way", path.read_text(), str(path))
'''


class Scratch(unittest.TestCase):
    """A scratch consuming-project tree and the helpers both groups use."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        environment = patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.root.parent / (self.root.name + '-evidence'))})
        environment.start()
        self.addCleanup(environment.stop)
        (self.root / 'bionic').mkdir()
        (self.root / 'src').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root / 'src/a.txt').write_text('good')

    def create(self):
        return create(self.root, 'quick-fix', 'Fix', 'Outcome', ['src'], ['correct'], 'builder', 'tester')

    def apply(self, doc, action, **args):
        return mutate(self.root, doc['id'], action, **args)

    def unit(self, text='good'):
        return {'check_id': 'unit', 'inputs': ['src'], 'environment': [],
                'command': [sys.executable, '-c', f"from pathlib import Path; assert Path('src/a.txt').read_text() == {text!r}"]}

    def attach(self, doc, declaration):
        result = execute(self.root, declaration)
        return self.apply(doc, 'evidence', check_id=declaration['check_id'], evidence_id=result['evidence']['id'], use=result['action'])

    def cover(self, doc, checks):
        doc = self.apply(doc, 'checks', checks=checks)
        return self.apply(doc, 'coverage', coverage={'affected': ['src'], 'checks': [{'check_id': c, 'rationale': 'related behavior exercised by ' + c} for c in checks], 'not_selected': 'No unrelated full-suite run needed for this fixture.'})



class BuildChecksTests(Scratch):
    def test_failing_or_missing_build_check_refuses_advance_and_a_pass_reaches_test(self):
        doc = self.apply(self.create(), 'checks', checks=['unit'], phase='build')
        self.assertEqual(doc['build_checks'], ['unit'])
        with self.assertRaisesRegex(CycleError, 'missing passing evidence for unit'):
            self.apply(doc, 'advance')
        failing = self.unit('bad')
        failing['check_id'] = 'unit'
        result = execute(self.root, failing)
        self.assertEqual(result['evidence']['status'], 'failed')
        with self.assertRaises(EvidenceError):
            self.apply(doc, 'evidence', check_id='unit', evidence_id=result['evidence']['id'], use='executed')
        with self.assertRaisesRegex(CycleError, 'missing passing evidence for unit'):
            self.apply(doc, 'advance')
        doc = self.attach(doc, self.unit())
        self.assertEqual(self.apply(doc, 'advance')['phase'], 'test')

    def test_stale_build_evidence_refuses_advance(self):
        doc = self.attach(self.apply(self.create(), 'checks', checks=['unit'], phase='build'), self.unit())
        (self.root / 'src/a.txt').write_text('changed')
        with self.assertRaisesRegex(CycleError, 'invalid evidence for unit'):
            self.apply(doc, 'advance')

    def test_test_reuses_the_same_evidence_with_no_new_receipt(self):
        doc = self.apply(self.create(), 'checks', checks=['unit'], phase='build')
        doc = self.attach(doc, self.unit())
        built = doc['evidence'][-1]['evidence_id']
        doc = self.apply(doc, 'advance')
        doc = self.cover(doc, ['unit'])
        again = execute(self.root, self.unit())
        self.assertEqual((again['action'], again['evidence']['id']), ('reused', built))
        self.assertEqual(self.apply(doc, 'advance')['phase'], 'review')
        self.assertEqual([ref['evidence_id'] for ref in doc['evidence']], [built])

    def test_checks_without_phase_is_unchanged(self):
        doc = self.apply(self.create(), 'checks', checks=['unit'])
        self.assertEqual(doc['required_checks'], ['unit'])
        self.assertNotIn('build_checks', doc)
        self.assertEqual(self.apply(doc, 'advance')['phase'], 'test')

    def test_record_without_build_checks_advances_as_before(self):
        doc = self.create()
        self.assertNotIn('build_checks', doc)
        self.assertEqual(self.apply(doc, 'advance')['phase'], 'test')

    def test_build_checks_are_unique_and_leave_the_review_basis_alone(self):
        doc = self.create()
        with self.assertRaisesRegex(CycleError, 'unique'):
            self.apply(doc, 'checks', checks=['unit', 'unit'], phase='build')
        before = review_basis_digest(doc, BASIS_VERSION)
        doc = self.apply(doc, 'checks', checks=['unit'], phase='build')
        self.assertEqual(review_basis_digest(doc, BASIS_VERSION), before)

    def test_the_set_is_recorded_in_build_only(self):
        doc = self.apply(self.create(), 'advance')
        with self.assertRaisesRegex(CycleError, 'Build phase'):
            self.apply(doc, 'checks', checks=['unit'], phase='build')

    def test_the_cli_accepts_phase_build(self):
        doc = self.create()
        script = Path(__file__).resolve().parents[1] / 'cycle.py'
        done = subprocess.run([sys.executable, str(script), '--repo-root', str(self.root), 'checks', doc['id'], '--phase', 'build', '--check', 'unit'],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)['cycle']['build_checks'], ['unit'])


class AuthoringCheckoutTests(Scratch):
    """A scratch tree the shared probe classifies as the authoring checkout."""
    def setUp(self):
        super().setUp()
        (self.root / 'crux/scripts').mkdir(parents=True)
        (self.root / 'crux/scripts/cycle_workflow.py').write_text('')

    def test_build_exit_names_each_missing_registered_suite(self):
        ids = [c for c in registered_declarations(self.root) if c.startswith('checkout:')]
        self.assertEqual(sorted(ids), sorted([CORE, TOOLS]))
        doc = self.create()
        with self.assertRaises(CycleError) as raised:
            self.apply(doc, 'advance')
        self.assertIn(CORE, str(raised.exception))
        self.assertIn(TOOLS, str(raised.exception))
        doc = self.apply(doc, 'checks', checks=[CORE], phase='build')
        with self.assertRaises(CycleError) as raised:
            self.apply(doc, 'advance')
        self.assertNotIn(CORE, str(raised.exception))
        self.assertIn(TOOLS, str(raised.exception))

    def test_declared_suites_still_need_passing_evidence(self):
        doc = self.apply(self.create(), 'checks', checks=[CORE, TOOLS], phase='build')
        with self.assertRaisesRegex(CycleError, 'missing passing evidence for ' + CORE.replace('*', r'\*')):
            self.apply(doc, 'advance')


class SkillsContractConflictTests(unittest.TestCase):
    """The CYC-0072 pass-1 conflict: a contract test elsewhere forbids what a changed file teaches."""
    def git(self, *args):
        subprocess.run(['git', *args], cwd=self.root, check=True, capture_output=True,
                       env={**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        environment = patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.root.parent / (self.root.name + '-evidence'))})
        environment.start()
        self.addCleanup(environment.stop)
        (self.root / 'bionic').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root / 'tests').mkdir()
        (self.root / 'tests/test_contract.py').write_text(CONTRACT)
        (self.root / 'skills/cycle/references').mkdir(parents=True)
        self.reference = self.root / 'skills/cycle/references/testing.md'
        self.reference.write_text('Run it with run-the-old-way for speed.\n')
        self.git('init', '-q')
        self.git('add', '-A')
        self.git('commit', '-qm', 'base')

    def declaration(self):
        return preset_declaration(self.root, 'whole-tree', 'contract',
                                  command=['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_contract.py'])

    def test_the_conflict_stops_the_cycle_in_build_and_a_fix_reaches_test(self):
        doc = create(self.root, 'quick-fix', 'Teach', 'Outcome', ['skills'], ['correct'], 'builder', 'tester')
        doc = mutate(self.root, doc['id'], 'checks', checks=['contract'], phase='build')
        failed = execute(self.root, self.declaration())
        self.assertEqual(failed['evidence']['status'], 'failed')
        with self.assertRaises(EvidenceError):
            mutate(self.root, doc['id'], 'evidence', check_id='contract', evidence_id=failed['evidence']['id'], use='executed')
        with self.assertRaisesRegex(CycleError, 'missing passing evidence for contract'):
            mutate(self.root, doc['id'], 'advance')
        self.reference.write_text('Run it with the current form.\n')
        passed = execute(self.root, self.declaration(), retry_reason='reference corrected')
        self.assertEqual(passed['evidence']['status'], 'passed')
        doc = mutate(self.root, doc['id'], 'evidence', check_id='contract', evidence_id=passed['evidence']['id'], use=passed['action'])
        doc = mutate(self.root, doc['id'], 'advance')
        self.assertEqual(doc['phase'], 'test')
        doc = mutate(self.root, doc['id'], 'checks', checks=['contract'])
        doc = mutate(self.root, doc['id'], 'coverage', coverage={'affected': ['skills'], 'checks': [{'check_id': 'contract', 'rationale': 'the contract test reads the changed reference'}], 'not_selected': 'No unrelated full-suite run needed for this fixture.'})
        again = execute(self.root, self.declaration())
        self.assertEqual((again['action'], again['evidence']['id']), ('reused', passed['evidence']['id']))
        self.assertEqual(mutate(self.root, doc['id'], 'advance')['phase'], 'review')
        self.assertEqual([ref['evidence_id'] for ref in load(self.root, doc['id'])['evidence']], [passed['evidence']['id']])


if __name__ == '__main__':
    unittest.main()
