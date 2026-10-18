"""Completion proves committed delivery and declared related-test coverage."""
import subprocess
import unittest
import test_cycle_workflow as workflow
from cycle_workflow import CycleError, check_coverage, check_completion, tree


class DeliveryTests(unittest.TestCase):
    setUp = workflow.CycleTests.setUp
    cycle = workflow.CycleTests.cycle
    apply = workflow.CycleTests.apply
    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def repository(self):
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        return self.git('rev-parse', 'HEAD')

    def test_missing_coverage_and_incomplete_selection_refused(self):
        doc = self.cycle()
        with self.assertRaisesRegex(CycleError, 'coverage'):
            check_coverage(doc)
        doc = self.apply(doc, 'checks', checks=['unit', 'integration'])
        with self.assertRaisesRegex(CycleError, 'selected checks'):
            self.apply(doc, 'coverage', coverage={'affected': ['parser'], 'checks': [{'check_id': 'unit', 'rationale': 'empty-input behavior'}], 'not_selected': 'none'})

    def test_coverage_reasons_and_check_selection_are_retained(self):
        doc = self.apply(self.cycle(), 'checks', checks=['unit'])
        coverage = {'affected': ['parser and callers'], 'checks': [{'check_id': 'unit', 'rationale': 'covers parser callers and regression'}], 'not_selected': 'release packaging unaffected'}
        doc = self.apply(doc, 'coverage', coverage=coverage)
        check_coverage(doc)
        self.assertEqual(doc['coverage'], coverage)
        doc = self.apply(doc, 'checks', checks=['other'])
        with self.assertRaisesRegex(CycleError, 'selected checks'):
            check_coverage(doc)

    def test_completion_requires_commit_or_explicit_owner_exception(self):
        doc = self.cycle()
        with self.assertRaisesRegex(CycleError, 'completion'):
            check_completion(tree(self.repo), doc)
        doc = self.apply(doc, 'completion', commits=[], exception='Owner: leave this change uncommitted for inspection.', remaining='src/a.py awaits owner inspection')
        check_completion(tree(self.repo), doc)
        (self.repo/'src/a.py').write_text('changed')
        with self.assertRaisesRegex(CycleError, 'changed'):
            check_completion(tree(self.repo), doc)

    def test_real_commit_rejects_dirty_and_untracked_scope_but_allows_unrelated_work(self):
        sha = self.repository()
        doc = self.cycle()
        doc = self.apply(doc, 'completion', commits=[sha], exception=None, remaining='cycle bookkeeping remains for final record commit')
        (self.repo/'unrelated.txt').write_text('another assignment')
        check_completion(tree(self.repo), doc)
        (self.repo/'src/new.py').write_text('untracked')
        with self.assertRaisesRegex(CycleError, 'uncommitted'):
            self.apply(doc, 'completion', commits=[sha], exception=None, remaining='none')
        (self.repo/'src/new.py').unlink()
        (self.repo/'src/a.py').write_text('changed')
        with self.assertRaisesRegex(CycleError, 'uncommitted'):
            self.apply(doc, 'completion', commits=[sha], exception=None, remaining='none')

    def test_historical_records_do_not_gain_new_requirements(self):
        doc = self.cycle()
        doc['schema_version'] = 1
        doc.pop('coverage', None)
        doc.pop('completion', None)
        check_coverage(doc)
        check_completion(tree(self.repo), doc)

    def test_staged_only_divergence_is_not_committed_delivery(self):
        sha = self.repository()
        doc = self.cycle()
        path = self.repo/'src/a.py'
        original = path.read_text()
        path.write_text('staged = 2\n')
        self.git('add', 'src/a.py')
        path.write_text(original)
        with self.assertRaisesRegex(CycleError, 'uncommitted'):
            self.apply(doc, 'completion', commits=[sha], exception=None, remaining='none')

    def test_ancestor_commit_cannot_hide_unstaged_reversion(self):
        sha = self.repository()
        doc = self.cycle()
        path = self.repo/'src/a.py'
        original = path.read_text()
        path.write_text('later_commit = 2\n')
        self.git('add', 'src/a.py')
        self.git('commit', '-qm', 'later behavior')
        path.write_text(original)
        with self.assertRaisesRegex(CycleError, 'uncommitted'):
            self.apply(doc, 'completion', commits=[sha], exception=None, remaining='none')
