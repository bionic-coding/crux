"""The review refusal names the exact-match scope rule the check enforces."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_cycle_review_basis as basis
from test_evidence import execute


class ReviewScopeMessageTests(basis.CliCycleCase):
    def in_review(self, scopes=('src',)):
        (self.root / 'src2').mkdir(exist_ok=True)
        (self.root / 'src2/b.txt').write_text('b')
        args = [a for s in scopes for a in ('--scope', s)]
        cid = self.ok('create', '--type', 'quick-fix', '--title', 'Fix', '--goal', 'Outcome', '--implementer', 'builder', '--coordinator', 'tester', *args, '--acceptance', 'correct')['id']
        self.ok('checks', cid, '--check', 'unit')
        self.ok('coverage', cid, '--file', self.write_json('coverage.json', self.coverage()))
        self.ok('advance', cid)
        result = execute(self.root, self.decl('unit'))
        self.evidence_id = result['evidence']['id']
        self.ok('evidence', cid, '--check-id', 'unit', '--evidence-id', self.evidence_id, '--use', result['action'])
        self.assertEqual(self.ok('advance', cid)['phase'], 'review')
        return cid

    def report(self, scope):
        return {'reviewer': 'independent', 'scope': scope, 'evidence': [self.evidence_id], 'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve', 'rationale': 'reviewed'}

    def refusal(self, plan_scopes, review_scope):
        cid = self.in_review(plan_scopes)
        return self.refused('review', cid, '--file', self.write_json('report.json', self.report(review_scope)))

    def assert_exact_rule(self, message):
        self.assertIn('equal the declared scope exactly', message)
        self.assertNotIn('cover', message)

    def test_superset_scope_is_refused_with_exact_rule(self):
        self.assert_exact_rule(self.refusal(('src',), ['src', 'src2']))

    def test_subset_scope_is_refused_with_exact_rule(self):
        self.assert_exact_rule(self.refusal(('src', 'src2'), ['src']))

    def test_matching_scope_is_accepted(self):
        cid = self.in_review()
        self.ok('review', cid, '--file', self.write_json('report.json', self.report(['src'])))


if __name__ == '__main__':
    unittest.main()
