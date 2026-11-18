"""Rule-handle collisions are refused before council review and before acceptance writes anything.

A proposed governs handle collides when its slug equals a live slug, a retired slug, or the slug of a
handle the same ADR retires. `decision_policy.propose` refuses it before allocation, `adr-precouncil.py
rules` reports it, and `decision_policy.accept` refuses it before any receipt or lifecycle byte.
Every test builds a throwaway repository; none reads this repository's tree.
"""
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import decision_policy as dp
from cycle_store import CycleError, digest, encoded

SCRIPTS = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}


class CorpusFixture(unittest.TestCase):
    """ADR-0001 rule `preserve-evidence` is retired by Accepted ADR-0002, whose live rule is `keep-evidence`."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docs = self.root / 'bionic'
        self.docs.mkdir()
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs / 'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        first = self.accepted('Keep durable evidence', 'preserve-evidence')
        self.assertIn('ADR-0001', first)
        second = self.accepted('Keep evidence under a new rule', 'keep-evidence',
                               retires=['ADR-0001/preserve-evidence'], amends=['ADR-0001'])
        self.assertIn('ADR-0002', second)

    def proposal(self, handle, retires=None, amends=None):
        rule = {'domain': 'evidence', 'rule': f'Rule {handle} holds.', 'scope': 'src/', 'handle': handle}
        if retires:
            rule['retires'] = retires
        proposal = {'title': f'Decide {handle}', 'body': '# Decision\n\nDecide it.\n', 'governs': [rule]}
        if amends:
            proposal['amends'] = amends
        return proposal

    def council(self, subject):
        row = {'format': 'crux.cycle-council', 'purpose': 'adr', 'subject': subject,
               'subject_sha256': digest((self.docs / subject).read_bytes()),
               'outcome': 'approved', 'cycle_id': None,
               'seats': [{'provider': p, 'decision': 'APPROVE', 'errored': False, 'findings': []}
                         for p in ['one', 'two', 'three']]}
        row['record_sha256'] = digest(encoded(row))
        path = self.docs / 'adrs/councils' / f"{subject.split('/')[-1]}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(encoded(row))
        return path.relative_to(self.docs).as_posix()

    def accepted(self, title, handle, **kw):
        proposal = self.proposal(handle, **kw)
        proposal['title'] = title
        subject = dp.propose(self.root, proposal, origin='direct')['path']
        dp.accept(self.root, subject, self.council(subject), human_approval='Owner: accept')
        return subject


class ProposeRefusesCollisionsTests(CorpusFixture):
    def assert_refused(self, proposal, shape, other):
        before = snapshot(self.docs)
        with self.assertRaisesRegex(CycleError, 'propose refused: rule-handle collision') as caught:
            dp.propose(self.root, proposal, origin='direct')
        message = str(caught.exception)
        self.assertIn(other, message)
        self.assertIn({'live': 'slug of live rule', 'retired': 'slug of retired rule',
                       'retired-by-same-adr': 'rule this ADR retires'}[shape], message)
        self.assertEqual(before, snapshot(self.docs), 'a refused proposal writes nothing')

    def test_a_live_slug_refuses(self):
        self.assert_refused(self.proposal('keep-evidence'), 'live', 'ADR-0002/keep-evidence')

    def test_a_retired_slug_refuses(self):
        self.assert_refused(self.proposal('preserve-evidence'), 'retired', 'ADR-0001/preserve-evidence')

    def test_a_slug_the_same_adr_retires_refuses(self):
        self.assert_refused(self.proposal('keep-evidence', retires=['ADR-0002/keep-evidence']),
                            'retired-by-same-adr', 'ADR-0002/keep-evidence')

    def test_positive_control_a_fresh_slug_is_admitted(self):
        result = dp.propose(self.root, self.proposal('restated-evidence-rule', retires=['ADR-0002/keep-evidence']),
                            origin='direct')
        self.assertEqual('ADR-0003', result['adr'])
        self.assertTrue((self.docs / result['path']).is_file())


class PrecouncilReportsCollisionsTests(CorpusFixture):
    def rules(self, handle, retires=None):
        summaries = self.docs / 'adrs/summaries'
        summaries.mkdir(exist_ok=True)
        (summaries / 'resolver.json').write_text('{}')
        (summaries / 'rule-table.md').write_text('| handle | domain |\n|---|---|\n')
        lines = ['---', 'id: ADR-0009', 'title: Draft', 'status: Proposed', 'amends: []', 'supersedes: []',
                 'governs:', f'- handle: ADR-0009/{handle}', '  rule: Draft rule.', '  domain: evidence',
                 '  scope: src/', '  provenance: authored']
        if retires:
            lines += ['  retires:'] + [f'  - {target}' for target in retires]
        draft = self.root / 'draft.md'
        draft.write_text('\n'.join(lines + ['---', '', '# Body', '']))
        spec = importlib.util.spec_from_file_location('adr_precouncil', SCRIPTS / 'adr-precouncil.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(['rules', '--repo-root', str(self.root), '--adr', str(draft), '--json'])
        self.assertEqual(0, code)
        return json.loads(out.getvalue())['collisions']

    def test_reports_the_three_collision_shapes(self):
        cases = (('keep-evidence', None, 'live', ['ADR-0002/keep-evidence']),
                 ('preserve-evidence', None, 'retired', ['ADR-0001/preserve-evidence']),
                 ('keep-evidence', ['ADR-0002/keep-evidence'], 'retired-by-same-adr', ['ADR-0002/keep-evidence']))
        for handle, retires, shape, other in cases:
            with self.subTest(shape=shape):
                found = self.rules(handle, retires)
                self.assertEqual([(f'ADR-0009/{handle}', shape, other)],
                                 [(f['handle'], f['collision'], f['with']) for f in found])

    def test_positive_control_a_fresh_slug_reports_nothing(self):
        self.assertEqual([], self.rules('restated-evidence-rule', ['ADR-0002/keep-evidence']))


class AcceptanceRefusesCollisionsBeforeAnyWriteTests(CorpusFixture):
    """A Proposed ADR edited to collide, then council-approved on those bytes, is refused at acceptance."""

    def setUp(self):
        super().setUp()
        self.subject = dp.propose(self.root, self.proposal('restated-evidence-rule'), origin='direct')['path']
        # The derived outputs an acceptance would regenerate: the index, the lineage and the rollup.
        (self.docs / 'adrs/index.md').write_text('# ADR index\n\n- ADR-0003 Proposed\n')
        (self.docs / 'adrs/lineage.md').write_text('# Lineage\n')
        (self.docs / 'index.md').write_text('# Index\n\n<!-- rollup -->\nADR-0003 Proposed\n')

    def edit_to(self, handle, retires=None):
        path = self.docs / self.subject
        text = path.read_text().replace('ADR-0003/restated-evidence-rule', f'ADR-0003/{handle}')
        if retires:
            text = text.replace('  provenance: authored\n',
                                '  provenance: authored\n  retires:\n' + ''.join(f'  - {t}\n' for t in retires), 1)
        path.write_text(text)

    def assert_refused_unchanged(self):
        approval = self.council(self.subject)
        before = snapshot(self.docs)
        with self.assertRaisesRegex(CycleError, 'acceptance refused: rule-handle collision'):
            dp.accept(self.root, self.subject, approval, human_approval='Owner: accept')
        self.assertEqual(before, snapshot(self.docs), 'a refused acceptance writes nothing')
        self.assertEqual('Proposed', dp.frontmatter((self.docs / self.subject).read_text())[0]['status'])
        self.assertFalse((self.docs / 'adrs/acceptances/ADR-0003.json').exists())

    def test_a_live_slug_refuses_before_any_write(self):
        self.edit_to('keep-evidence')
        self.assert_refused_unchanged()

    def test_a_retired_slug_refuses_before_any_write(self):
        self.edit_to('preserve-evidence')
        self.assert_refused_unchanged()

    def test_a_slug_the_same_adr_retires_refuses_before_any_write(self):
        self.edit_to('keep-evidence', retires=['ADR-0002/keep-evidence'])
        self.assert_refused_unchanged()

    def test_a_rule_accepted_meanwhile_makes_the_slug_live_and_refuses(self):
        self.accepted('Claim the slug first', 'restated-evidence-rule')
        self.assert_refused_unchanged()

    def test_positive_control_a_fresh_slug_is_accepted(self):
        result = dp.accept(self.root, self.subject, self.council(self.subject), human_approval='Owner: accept')
        self.assertEqual('binding', result['standing'])
        self.assertEqual('Accepted', dp.frontmatter((self.docs / self.subject).read_text())[0]['status'])


if __name__ == '__main__':
    unittest.main()
