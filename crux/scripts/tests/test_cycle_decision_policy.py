"""Prospective ADR acceptance preserves reviewed bytes and historical records."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import decision_policy as dp
import cycle_writer as pilot
from cycle_store import CycleError, digest, encoded, tree


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

    def test_cycle_origin_names_its_cycle_and_creation_approval_is_retired(self):
        with self.assertRaisesRegex(CycleError, 'names its cycle record'):
            dp.propose(self.root, self.proposal, origin='cycle')
        for origin, cycle_id in (('cycle', 'CYC-0001'), ('direct', None)):
            with self.subTest(origin=origin), self.assertRaisesRegex(CycleError, 'ADR-creation council is retired'):
                dp.propose(self.root, self.proposal, origin=origin, cycle_id=cycle_id,
                           creation_approval='adrs/councils/creation.json', creation_subject='cycles/CYC-0001/x.json')
        self.assertFalse((self.docs / 'adrs').exists())


class CycleOriginProposalTests(unittest.TestCase):
    """A cycle drafts a necessary ADR in any active state; council review and human acceptance still bind."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.docs = self.root / 'bionic'
        self.docs.mkdir(parents=True)
        (self.root / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs / 'manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.docs / 'objectives.md').write_text('Durable decisions with proportional ceremony.\n')
        (self.root / 'src').mkdir()
        (self.root / 'src/value.py').write_text('value = 1\n')
        for argv in (('init', '-q'), ('config', 'user.email', 'test@example.invalid'), ('config', 'user.name', 'Test'),
                     ('add', '.'), ('commit', '-qm', 'baseline')):
            subprocess.run(['git', '-C', str(self.root), *argv], check=True, capture_output=True)
        self.proposal = {'title': 'Correct a colliding rule handle', 'body': '# Decision\n\nRestate the rule under a new handle.\n',
                         'governs': [{'domain': 'workflow', 'rule': 'Restate the rule.', 'scope': 'src/', 'handle': 'restate-the-rule'}]}

    def cycle(self, state='working'):
        spec = {'goal': 'Correct the value', 'scope': ['src'], 'acceptance': ['value equals two'],
                'verification': {'checks': [{'id': 'focused', 'rationale': 'the value'}], 'gaps': 'none'},
                'council': {'needed': False, 'reason': 'bounded correction'},
                'tasks': [{'id': 'build', 'description': 'Correct the value', 'owner': 'worker'}]}
        doc = pilot.create(self.root, 'Correction', 'lead', spec)
        def apply(action, **kwargs):
            return pilot.mutate(self.root, doc['id'], 'lead', pilot.load_pilot(self.root, doc['id'])['revision'],
                                action, SimpleNamespace(**kwargs))
        if state in ('working', 'reviewing'):
            apply('task', task='build', owner='worker', run=1, status='working', checkout=None, summary='started')
        if state == 'reviewing':
            apply('review-start', reviewer='reviewer')
        if state == 'paused':
            apply('pause', reason='owner stopped work')
        if state == 'reviewed':
            apply('task', task='build', owner='worker', run=1, status='done', checkout=None, summary='already correct')
            apply('check', value={'check_id': 'focused', 'executed_command': 'python -m unittest', 'result': 'passed',
                                  'tested_revision': 'HEAD', 'summary': 'passed', 'reason': 'the value'})
            apply('review-start', reviewer='reviewer')
            head = subprocess.run(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
            stored = pilot.load_pilot(self.root, doc['id'])
            pilot.mutate(self.root, doc['id'], 'reviewer', stored['revision'], 'review', SimpleNamespace(value={
                'reviewer': 'reviewer', 'plan_revision': stored['plan']['revision'], 'base_commit': stored['base_commit'],
                'head_commit': head, 'verdict': 'approve', 'blocking': [],
                'acceptance': [{'criterion': 0, 'met': True, 'evidence': 'observed'}], 'test_selection': 'focused', 'summary': 'done'}))
        doc = pilot.load_pilot(self.root, doc['id'])
        self.assertEqual(doc['state'], state)
        return doc

    def snapshot(self):
        return {p.relative_to(self.docs).as_posix(): p.read_bytes() for p in sorted(self.docs.rglob('*'))
                if p.is_file() and '.lock' not in p.name}

    def council(self, subject, cycle_id, purpose='adr', name='approval'):
        row = {'format': 'crux.cycle-council', 'purpose': purpose, 'subject': subject,
               'subject_sha256': digest((self.docs / subject).read_bytes()), 'outcome': 'approved', 'cycle_id': cycle_id,
               'seats': [{'provider': p, 'decision': 'APPROVE', 'errored': False, 'findings': []} for p in ['one', 'two', 'three']]}
        row['record_sha256'] = digest(encoded(row))
        path = self.docs / f'adrs/councils/{name}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded(row))
        return path.relative_to(self.docs).as_posix()

    def test_working_and_reviewing_cycles_propose_with_truthful_provenance(self):
        for state in ('planning', 'working', 'reviewing'):
            with self.subTest(state=state):
                self.setUp()  # a fresh repository: one cycle per checkout claim
                doc = self.cycle(state)
                result = dp.propose(self.root, self.proposal, origin='cycle', cycle_id=doc['id'])
                identity = 'ADR-0001'
                self.assertEqual((result['adr'], result['creation_approval']), (identity, None))
                metadata = json.loads((self.docs / f'adrs/proposals/{identity}.json').read_text())
                self.assertEqual({k: metadata[k] for k in ('origin', 'cycle_id', 'cycle_format', 'creation_approval', 'creation_subject')},
                                 {'origin': 'cycle', 'cycle_id': doc['id'], 'cycle_format': 'crux.cycle.v1',
                                  'creation_approval': None, 'creation_subject': None})
                stored = pilot.load_pilot(self.root, doc['id'])
                self.assertEqual(stored['adrs'], [{'adr': identity, 'path': result['path'],
                                                   'sha256': digest((self.docs / result['path']).read_bytes())}])
                self.assertEqual(stored['state'], state)
                self.assertEqual(dp.frontmatter((self.docs / result['path']).read_text())[0]['status'], 'Proposed')

    def test_closed_paused_release_and_legacy_cycles_refuse_before_any_write(self):
        paused = self.cycle('paused')
        before = self.snapshot()
        with self.assertRaisesRegex(CycleError, 'planning, working or reviewing; .* is paused'):
            dp.propose(self.root, self.proposal, origin='cycle', cycle_id=paused['id'])
        self.assertEqual(self.snapshot(), before)
        self.setUp()  # a fresh repository: one cycle per checkout claim
        reviewed = self.cycle('reviewed')
        before = self.snapshot()
        with self.assertRaisesRegex(CycleError, f"{reviewed['id']} is reviewed; a plan revision returns the cycle to planning"):
            dp.propose(self.root, self.proposal, origin='cycle', cycle_id=reviewed['id'])
        legacy = self.docs / 'cycles/CYC-0090/cycle.json'
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({'schema_version': 3, 'id': 'CYC-0090', 'status': 'active', 'phase': 'build'}))
        with self.assertRaisesRegex(CycleError, 'legacy typed record'):
            dp.propose(self.root, self.proposal, origin='cycle', cycle_id='CYC-0090')
        legacy.unlink()
        self.assertEqual(self.snapshot(), before)

    def test_an_interrupted_propose_resumes_by_identity_and_adds_no_second_entry(self):
        doc = self.cycle('working')
        # Interrupted after the counter: the number is a gap and the retry allocates the next one.
        with patch.object(dp, 'atomic', side_effect=OSError('metadata write interrupted')), self.assertRaises(OSError):
            dp.propose(self.root, self.proposal, origin='cycle', cycle_id=doc['id'])
        self.assertIn('next_number: 2', (self.docs / 'manifest.yml').read_text())
        self.assertFalse((self.docs / 'adrs/proposals').exists())
        # Interrupted after the metadata and the ADR file, before the cycle entry.
        with patch.object(pilot, 'record_adr', side_effect=OSError('entry write interrupted')), self.assertRaises(OSError):
            dp.propose(self.root, self.proposal, origin='cycle', cycle_id=doc['id'])
        files = sorted(p.name for p in (self.docs / 'adrs').glob('ADR-*.md'))
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith('ADR-0002-'))
        self.assertNotIn('adrs', pilot.load_pilot(self.root, doc['id']))
        # Interrupted after the metadata, before the ADR file: the retry writes the file, then the entry.
        (self.docs / 'adrs' / files[0]).unlink()
        result = dp.propose(self.root, self.proposal, origin='cycle', cycle_id=doc['id'])
        self.assertEqual(result['adr'], 'ADR-0002')
        self.assertTrue((self.docs / result['path']).is_file())
        self.assertEqual([e['adr'] for e in pilot.load_pilot(self.root, doc['id'])['adrs']], ['ADR-0002'])
        # A repeat after completion changes nothing.
        before = self.snapshot()
        self.assertEqual(dp.propose(self.root, self.proposal, origin='cycle', cycle_id=doc['id'])['adr'], 'ADR-0002')
        self.assertEqual(self.snapshot(), before)
        self.assertIn('next_number: 3', (self.docs / 'manifest.yml').read_text())
        # An edited draft is not overwritten by a stale retry.
        path = self.docs / result['path']
        path.write_text(path.read_text() + 'Edited after review.\n')
        with self.assertRaisesRegex(CycleError, 'differs from the proposal'):
            dp.propose(self.root, self.proposal, origin='cycle', cycle_id=doc['id'])

    def test_acceptance_needs_council_approval_of_the_exact_draft_and_the_owner_answer(self):
        doc = self.cycle('working')
        subject = dp.propose(self.root, self.proposal, origin='cycle', cycle_id=doc['id'])['path']
        # A council of the retired creation purpose, of another cycle, or of earlier bytes approves nothing.
        creation = self.council(subject, doc['id'], purpose='adr-creation', name='creation')
        other = self.council(subject, 'CYC-0099', name='other')
        earlier = self.council(subject, doc['id'], name='earlier')
        path = self.docs / subject
        draft = path.read_bytes()
        path.write_bytes(draft.replace(b'new handle', b'replacement handle'))
        before = self.snapshot()
        for label, approval in (('creation purpose', creation), ('other cycle', other), ('earlier bytes', earlier)):
            with self.subTest(label), self.assertRaises(CycleError):
                dp.accept(self.root, subject, approval, human_approval='Owner: accept it')
            self.assertEqual(self.snapshot(), before, label)
        # The exact draft approved, but no recorded owner answer: refused, tree unchanged.
        approval = self.council(subject, doc['id'])
        before = self.snapshot()
        for answer in (None, '  '):
            with self.subTest(answer=answer), self.assertRaisesRegex(CycleError, 'human acceptance approval is required'):
                dp.accept(self.root, subject, approval, human_approval=answer)
            self.assertEqual(self.snapshot(), before)
        # Positive control: both present, the ADR is accepted and its body is unchanged.
        receipt = dp.accept(self.root, subject, approval, human_approval='Owner: accept the corrective ADR')
        self.assertEqual((receipt['cycle_id'], receipt['standing']), (doc['id'], 'binding'))
        self.assertEqual(dp.frontmatter(path.read_text())[0]['status'], 'Accepted')
        dp.validate_acceptance(tree(self.root), {'path': subject})

    def test_a_historical_creation_approval_proposal_still_validates(self):
        historical_subject = 'cycles/CYC-0001/evidence/creation.json'
        (self.docs / historical_subject).parent.mkdir(parents=True)
        (self.docs / historical_subject).write_text('{"question":"Is an ADR justified?"}')
        creation = self.council(historical_subject, 'CYC-0001', purpose='adr-creation', name='creation')
        self.assertEqual(dp.validate_approval(self.root, creation, purpose='adr-creation', subject=historical_subject)['purpose'],
                         'adr-creation')
        subject = dp.propose(self.root, self.proposal, origin='direct')['path']
        dp.accept(self.root, subject, self.council(subject, None), human_approval='Owner approved')
        metadata = self.docs / 'adrs/proposals/ADR-0001.json'
        historical = dict(json.loads(metadata.read_text()), origin='cycle', cycle_id='CYC-0001',
                          creation_approval=creation, creation_subject=historical_subject)
        metadata.write_text(json.dumps(historical))
        dp.validate_acceptance(tree(self.root), {'path': subject})
        from summaries_projection import collect_records
        self.assertEqual(len(collect_records(self.docs / 'adrs')), 1)


LEGACY_ADR = '''---
id: ADR-0001
title: Keep durable evidence
status: Proposed
acceptance_format: crux.adr-acceptance.v1
governs:
- domain: evidence
  rule: Preserve evidence.
  scope: src/
  handle: ADR-0001/preserve-evidence
  provenance: authored
---

# Decision

Preserve the evidence.
'''
SCRIPT = Path(__file__).resolve().parents[1] / 'decision-policy.py'


class OwnerDecisionCommandTests(unittest.TestCase):
    """A legacy-adoption acceptance under council-and-human runs wholly through decision-policy.py."""
    council = DecisionPolicyTests.council

    def setUp(self):
        DecisionPolicyTests.setUp(self)
        self.subject = 'adrs/ADR-0001-keep-durable-evidence.md'
        self.path = self.docs / self.subject
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(LEGACY_ADR)
        for args in (('init', '-q'), ('config', 'user.email', 't@example.com'), ('config', 'user.name', 't'),
                     ('add', '.'), ('commit', '-q', '-m', 'legacy ADR')):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        self.binding = {'purpose': 'adr-acceptance', 'cycle_id': None, 'subject': self.subject,
                        'subject_sha256': digest(self.path.read_bytes())}

    def run_command(self, *argv, stdin=None):
        done = subprocess.run([sys.executable, str(SCRIPT), '--repo-root', str(self.root), *argv],
                              input=stdin, capture_output=True, text=True, timeout=60)
        return done.returncode, json.loads(done.stdout) if done.stdout.strip() else None, done.stderr

    def test_legacy_adoption_under_council_and_human_runs_adopt_council_present_capture_apply(self):
        code, adopted, err = self.run_command('adopt', '--subject', self.subject)
        self.assertEqual((code, adopted and adopted['ok']), (0, True), err)
        approval = self.council(self.subject)
        present = {**self.binding, 'op_id': 'present-0001', 'question': 'Accept this exact ADR?'}
        code, shown, err = self.run_command('owner-decision', 'present', '--json', json.dumps(present))
        self.assertEqual((code, shown and shown['ok']), (0, True), err)
        capture = {**self.binding, 'op_id': 'capture-0001', 'presentation': shown['presentation'],
                   'disposition': 'approve', 'quote': 'I accept ADR-0001 as shown.',
                   'source': {'kind': 'conversation', 'reference': 'session-2/message-3'},
                   'owner_date': '2026-11-08', 'supersedes': None}
        # The request travels on standard input.
        code, captured, err = self.run_command('owner-decision', 'capture', '--json', '-', stdin=json.dumps(capture))
        self.assertEqual((code, captured and captured['ok']), (0, True), err)
        self.assertEqual(captured['record']['quote'], 'I accept ADR-0001 as shown.')
        self.assertEqual(dp.frontmatter(self.path.read_text())[0]['status'], 'Proposed')
        # The request travels in a repository file.
        request = self.root / 'apply-request.json'
        request.write_text(json.dumps({**self.binding, 'capture': captured['capture'], 'approval': approval}))
        code, applied, err = self.run_command('owner-decision', 'apply', '--json', '@apply-request.json')
        self.assertEqual((code, applied and applied['ok'], applied and applied['applied']), (0, True, True), err)
        self.assertEqual(dp.frontmatter(self.path.read_text())[0]['status'], 'Accepted')
        receipt = dp.validate_acceptance(tree(self.root), {'path': self.subject})
        self.assertEqual((receipt['policy'], receipt['standing'], receipt['owner_decision']),
                         ('council-and-human', 'binding', captured['capture']))

    def test_refusals_print_their_code_and_a_file_outside_the_repository_is_an_environment_error(self):
        for purpose, code in (('idr', 'idr-council-retired'), ('acceptance-change', 'acceptance-change-retired')):
            for action in ('present', 'capture', 'apply'):
                with self.subTest(purpose=purpose, action=action):
                    request = {**self.binding, 'purpose': purpose, 'cycle_id': 'CYC-0001', 'op_id': 'retired-0001'}
                    status, refused, _ = self.run_command('owner-decision', action, '--json', json.dumps(request))
                    self.assertEqual((status, refused['ok'], refused['error']['code']), (1, False, code))
        outside = self.root.parent / 'outside-request.json'
        outside.write_text('{}')
        status, refused, _ = self.run_command('owner-decision', 'present', '--json', '@' + str(outside))
        self.assertEqual((status, refused['ok']), (2, False))
        self.assertIn('outside the repository root', refused['error'])
        status, refused, _ = self.run_command('owner-decision', 'present', '--json', '{"purpose":')
        self.assertEqual((status, refused['ok'], refused['error']['code']), (1, False, 'invalid-request-json'))


if __name__ == '__main__':
    unittest.main()
