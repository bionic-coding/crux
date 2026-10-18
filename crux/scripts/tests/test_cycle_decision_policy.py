"""Prospective ADR acceptance preserves reviewed bytes and historical records."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import decision_policy as dp
from cycle_workflow import CycleError, digest, encoded, tree


class DecisionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docs = self.root / 'bionic'
        self.docs.mkdir()
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs / 'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        self.proposal = {'title': 'Keep durable evidence', 'body': '# Decision\n\nPreserve the evidence.\n',
                         'governs': [{'domain': 'evidence', 'rule': 'Preserve evidence.', 'scope': 'src/', 'handle': 'preserve-evidence'}]}

    def propose(self):
        return dp.propose(self.root, self.proposal, origin='direct')['path']

    def test_numeric_rule_slug_refuses_before_allocation(self):
        before = (self.docs / 'manifest.yml').read_bytes()
        self.proposal['governs'][0]['handle'] = '123-rule'
        with self.assertRaisesRegex(CycleError, 'letter-led'):
            self.propose()
        self.assertEqual(before, (self.docs / 'manifest.yml').read_bytes())

    def council(self, subject, **changes):
        row = {'format': 'crux.cycle-council', 'purpose': 'adr', 'subject': subject,
               'subject_sha256': digest((self.docs / subject).read_bytes()),
               'outcome': 'approved', 'cycle_id': None,
               'seats': [{'provider': p, 'decision': 'APPROVE', 'errored': False, 'findings': []}
                         for p in ['one', 'two', 'three']]}
        row.update(changes)
        row['record_sha256'] = digest(encoded(row))
        path = self.docs / 'adrs/councils/test.json'
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(encoded(row))
        return path.relative_to(self.docs).as_posix()

    def test_default_requires_human_and_acceptance_preserves_body(self):
        subject = self.propose()
        original = (self.docs / subject).read_text()
        approval = self.council(subject)
        with self.assertRaisesRegex(CycleError, 'human'):
            dp.accept(self.root, subject, approval)
        self.assertEqual(original, (self.docs / subject).read_text())
        result = dp.accept(self.root, subject, approval, human_approval='Owner: accept this proposal')
        front, body = dp.frontmatter((self.docs / subject).read_text())
        self.assertEqual('Accepted', front['status'])
        self.assertEqual(front['date'], front['accepted_date'])
        self.assertEqual(body, dp.frontmatter(original)[1])
        self.assertEqual('binding', result['standing'])
        self.assertFalse((self.docs / 'adrs/provenance').exists())
        dp.validate_acceptance(tree(self.root), {'path': subject})

    def test_council_only_and_prefix(self):
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\nartifact_prefix: DEMO\nadr:\n  acceptance: council-only\n')
        subject = self.propose()
        self.assertIn('DEMO-ADR-0001-', subject)
        result = dp.accept(self.root, subject, self.council(subject))
        self.assertEqual('council-only', result['policy'])
        dp.validate_acceptance(tree(self.root), {'path': subject})

    def test_authority_projection_validates_acceptance_evidence(self):
        from summaries_projection import collect_records
        subject = self.propose()
        dp.accept(self.root, subject, self.council(subject), human_approval='Owner approves')
        self.assertEqual(1, len(collect_records(self.docs / 'adrs')))
        path = self.docs / subject
        path.write_text(path.read_text().replace('Preserve the evidence.', 'Discard the evidence.'))
        with self.assertRaisesRegex(ValueError, 'accepted decision contents changed'):
            collect_records(self.docs / 'adrs')

    def test_missing_both_sidecars_cannot_downgrade_to_historical(self):
        from summaries_projection import collect_records
        subject = self.propose()
        dp.accept(self.root, subject, self.council(subject), human_approval='Owner approves')
        for directory in ('proposals', 'acceptances'):
            (self.docs / 'adrs' / directory / 'ADR-0001.json').unlink()
        with self.assertRaisesRegex(ValueError, 'acceptance receipt missing'):
            collect_records(self.docs / 'adrs')

    def test_changed_proposal_and_wrong_purpose_refuse(self):
        subject = self.propose()
        approval = self.council(subject, purpose='consultation')
        with self.assertRaises(CycleError):
            dp.accept(self.root, subject, approval, human_approval='yes')
        approval = self.council(subject)
        with (self.docs / subject).open('a') as stream:
            stream.write('Changed after approval.\n')
        with self.assertRaises(CycleError):
            dp.accept(self.root, subject, approval, human_approval='yes')

    def test_historical_proposal_not_admitted(self):
        subject = self.propose()
        (self.docs / 'adrs/proposals/ADR-0001.json').unlink()
        with self.assertRaisesRegex(CycleError, 'new-policy'):
            dp.accept(self.root, subject, self.council(subject), human_approval='yes')

    def test_crash_after_receipt_can_resume(self):
        subject = self.propose()
        approval = self.council(subject)
        with patch.object(dp, 'write_text_atomic', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                dp.accept(self.root, subject, approval, human_approval='Owner approved')
        self.assertEqual('Proposed', dp.frontmatter((self.docs / subject).read_text())[0]['status'])
        dp.accept(self.root, subject, approval)
        dp.validate_acceptance(tree(self.root), {'path': subject})

    def test_acceptance_detects_changed_council_or_decision(self):
        subject = self.propose()
        approval = self.council(subject)
        dp.accept(self.root, subject, approval, human_approval='Owner approved')
        with (self.docs / subject).open('a') as stream:
            stream.write('Unreviewed text.\n')
        with self.assertRaises(CycleError):
            dp.validate_acceptance(tree(self.root), {'path': subject})

    def test_cycle_origin_requires_creation_approval(self):
        with self.assertRaisesRegex(CycleError, 'justification'):
            dp.propose(self.root, self.proposal, origin='cycle')
        self.assertFalse((self.docs / 'adrs').exists())


if __name__ == '__main__':
    unittest.main()
