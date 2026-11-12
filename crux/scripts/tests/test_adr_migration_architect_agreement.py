"""A council record admits only the council writer's own architect-agreement commit.

`adr_migration.introduction` refuses a committed record whose bytes changed after the commit
that added it. A Standard-mode council record is added before the architect agrees, and the
council writer then rewrites it in place with the agreement. That one commit is accepted, on
both the disposition approval path and the disposition council path in `cycle_council`, which
share this function; every other later edit, and any later edit of another record, refuses.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adr_migration as m  # noqa: E402
import council_policy as policy  # noqa: E402
from cycle_workflow import CycleError, encoded  # noqa: E402

RECORD = 'bionic/cycles/CYC-0001/councils/decisions/x/council-1.json'
SUBJECT_SHA = 'a' * 64
IDENTITY = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.invalid',
            'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid',
            'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}


def council_record() -> dict:
    """A sealed Standard-mode record with three approving seats and no architect yet."""
    seats = [{'provider': p, 'decision': 'APPROVE', 'findings': []} for p in ('one', 'two', 'three')]
    row = {'format': policy.RECORD, 'id': '1', 'attempt': 'cycles/CYC-0001/councils/decisions/x/attempt-1.json',
           'policy': {'mode': 'standard'}, 'subject_sha256': SUBJECT_SHA, 'seats': seats, 'passes': [],
           'binding_failures': [], 'architect': None}
    row['outcome'] = policy.evaluate(row)
    return policy.seal(row)


def agreed(row: dict, **architect) -> dict:
    """What the council writer's disposition writes: architect, derived outcome, new seal."""
    row = dict(row)
    row['architect'] = {'agrees': True, 'subject_sha256': SUBJECT_SHA, 'rationale': 'agreed', 'dissent': [],
                        **architect}
    row['outcome'] = policy.evaluate(row)
    return policy.seal(row)


class ArchitectAgreementIntroductionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.git('init', '-q', '-b', 'main')
        self.before = council_record()
        self.introduced = self.commit({RECORD: self.before}, 'council record')

    def git(self, *args: str) -> str:
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(IDENTITY)
        r = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, text=True, env=env)
        if r.returncode:
            raise AssertionError(f'git {args} failed: {r.stderr}')
        return r.stdout

    def commit(self, files: dict, message: str) -> str:
        for rel, value in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value if isinstance(value, bytes) else encoded(value))
        self.git('add', '--', *files)
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD').strip()

    def allowed(self) -> str:
        return m.introduction(self.root, RECORD)

    def test_a_standard_record_with_its_architect_agreement_commit_passes(self):
        after = agreed(self.before)
        self.assertEqual(self.before['outcome'], 'changes-required')
        self.assertEqual(after['outcome'], 'approved')
        self.commit({RECORD: after}, 'Record exact architect council disposition')
        self.assertEqual(self.allowed(), self.introduced)

    def test_the_same_edit_of_a_record_that_is_not_a_mode_aware_council_record_refuses(self):
        for fmt in ('crux.cycle-council', 'crux.adr-migration-approval.v1'):
            with self.subTest(format=fmt):
                before = policy.seal(dict(self.before, format=fmt))
                rel = f'bionic/other/{fmt}.json'
                self.commit({rel: before}, 'record')
                after = dict(before, architect={'agrees': True, 'subject_sha256': SUBJECT_SHA, 'rationale': 'agreed'})
                self.commit({rel: policy.seal(after)}, 'Record exact architect council disposition')
                with self.assertRaisesRegex(CycleError, 'edited after introduction'):
                    m.introduction(self.root, rel)

    def test_the_disposition_council_path_reads_the_same_introduction(self):
        import cycle_council
        source = Path(cycle_council.__file__).read_text()
        self.assertIn('from adr_migration import validate_package, validate_readiness, introduction', source)

    def test_an_unedited_record_passes(self):
        self.assertEqual(self.allowed(), self.introduced)

    def test_an_agreement_commit_that_also_changes_an_earlier_field_refuses(self):
        after = dict(agreed(self.before)); after['seats'] = after['seats'][:2] + [
            {'provider': 'three', 'decision': 'APPROVE_WITH_NITS', 'findings': []}]
        self.commit({RECORD: policy.seal(after)}, 'Record exact architect council disposition')
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()

    def test_an_agreement_commit_that_adds_a_field_refuses(self):
        after = dict(agreed(self.before)); after['note'] = 'added'
        self.commit({RECORD: policy.seal(after)}, 'Record exact architect council disposition')
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()

    def test_an_outcome_the_policy_does_not_derive_refuses(self):
        after = dict(agreed(self.before)); after['architect'] = dict(after['architect'], rationale='')
        after['outcome'] = 'approved'
        self.commit({RECORD: policy.seal(after)}, 'Record exact architect council disposition')
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()

    def test_a_disagreeing_architect_or_another_revision_refuses(self):
        for architect in ({'agrees': False}, {'subject_sha256': 'b' * 64}):
            with self.subTest(architect=architect):
                self.commit({RECORD: agreed(self.before, **architect)}, 'disposition')
                with self.assertRaisesRegex(CycleError, 'edited after introduction'):
                    self.allowed()

    def test_a_broken_seal_refuses(self):
        after = agreed(self.before); after['record_sha256'] = 'c' * 64
        self.commit({RECORD: after}, 'Record exact architect council disposition')
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()

    def test_an_agreement_commit_that_touches_another_path_refuses(self):
        self.commit({RECORD: agreed(self.before), 'other.txt': b'x\n'}, 'Record exact architect council disposition')
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()

    def test_a_second_edit_after_the_agreement_refuses(self):
        after = agreed(self.before)
        self.commit({RECORD: after}, 'Record exact architect council disposition')
        self.commit({RECORD: agreed(after, rationale='again')}, 'Record exact architect council disposition')
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()

    def test_an_uncommitted_agreement_refuses(self):
        (self.root / RECORD).write_bytes(encoded(agreed(self.before)))
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()

    def test_an_edit_of_a_record_that_already_carried_an_architect_refuses(self):
        first = agreed(self.before)
        (self.root / RECORD).unlink(); self.git('rm', '-q', '--cached', RECORD); self.git('commit', '-q', '-m', 'drop')
        self.commit({RECORD: first}, 're-add with an architect')
        self.commit({RECORD: agreed(first, rationale='changed')}, 'Record exact architect council disposition')
        with self.assertRaisesRegex(CycleError, 'edited after introduction'):
            self.allowed()


if __name__ == '__main__':
    unittest.main()
