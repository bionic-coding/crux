"""Identical work inside one authority-view evaluation runs once.

The historical approval boundary is one immutable proof per (parent commit,
approval path). Inside one evaluation it runs once; a refusal, a different
commit or path, and any call outside an evaluation run it again. The reviews-index
generator evaluates the view under one read scope, which already re-checks bound
inputs and repository state before it answers a repeat.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_adr_migration import MigrationFixture
import adr_migration as m
import implementation_migration as historical
from cycle_workflow import CycleError


_REAL_RUN = subprocess.run


def _counting_run():
    """A subprocess.run wrapper that counts the parent approval reader's runs."""
    calls = []

    def run(command, *args, **kwargs):
        if len(command) > 2 and str(command[1]).endswith('adr-migration.py') and command[2] == 'approval':
            calls.append(command)
        return _REAL_RUN(command, *args, **kwargs)
    return run, calls


class BoundaryRepeatTests(MigrationFixture):
    """The boundary's decision logic, with the parent reader stubbed to a fixed outcome."""

    def reader(self, returncode=0):
        calls = []

        def run(command, *args, **kwargs):
            if len(command) > 2 and str(command[1]).endswith('adr-migration.py') and command[2] == 'approval':
                calls.append(command)
                return subprocess.CompletedProcess(command, returncode, stdout=b'', stderr=b'')
            return _REAL_RUN(command, *args, **kwargs)
        return run, calls

    def boundary(self, parent, *, returncode=0, approval='unused-approval.json'):
        import adr_migration_publication as p
        run, calls = self.reader(returncode)
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(historical, '_revision_repository', return_value=contextlib.nullcontext(self.root)))
        stack.enter_context(patch.object(p.subprocess, 'run', side_effect=run))
        stack.enter_context(patch.object(m, 'current_standing', return_value={'h': {'standing': 'binding'}}))
        stack.enter_context(patch.object(m, 'validate_approval', return_value={'approved': True}))
        return p, calls, stack

    def test_same_parent_and_approval_run_the_reader_once_inside_one_evaluation(self):
        p, calls, stack = self.boundary(self.head())
        with stack:
            # Positive control: with no evaluation open, each call runs the reader.
            first = p.validate_boundary(self.root, 'unused-approval.json', self.head(), _with_standing=True)
            p.validate_boundary(self.root, 'unused-approval.json', self.head())
            self.assertEqual(len(calls), 2)
            del calls[:]
            with historical._evaluation_scope():
                inside = p.validate_boundary(self.root, 'unused-approval.json', self.head(), _with_standing=True)
                repeat = p.validate_boundary(self.root, 'unused-approval.json', self.head(), _with_standing=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(inside, repeat)
        self.assertEqual(inside, first)

    def test_a_remembered_standing_is_a_copy(self):
        p, calls, stack = self.boundary(self.head())
        with stack, historical._evaluation_scope():
            _, standing = p.validate_boundary(self.root, 'unused-approval.json', self.head(), _with_standing=True)
            standing['h']['standing'] = 'tampered'
            _, again = p.validate_boundary(self.root, 'unused-approval.json', self.head(), _with_standing=True)
        self.assertEqual(again, {'h': {'standing': 'binding'}})
        # The first call ran the parent reader; the second was served from the evaluation's memo.
        self.assertEqual(len(calls), 1)

    def test_a_refusal_is_never_remembered(self):
        p, calls, stack = self.boundary(self.head(), returncode=1)
        with stack, historical._evaluation_scope():
            for _ in range(2):
                with self.assertRaisesRegex(CycleError, 'parent.*refused'):
                    p.validate_boundary(self.root, 'unused-approval.json', self.head())
        self.assertEqual(len(calls), 2)

    def test_a_different_parent_or_approval_path_is_proved_again(self):
        earlier = self.head()
        self.write('later.txt', 'a later commit\n')
        self.commit('Later parent')
        p, calls, stack = self.boundary(earlier)
        with stack, historical._evaluation_scope():
            p.validate_boundary(self.root, 'unused-approval.json', earlier)
            p.validate_boundary(self.root, 'unused-approval.json', self.head())
            p.validate_boundary(self.root, 'other-approval.json', earlier)
            self.assertEqual(len(calls), 3)
            p.validate_boundary(self.root, 'unused-approval.json', earlier)
            self.assertEqual(len(calls), 3)

    def test_an_outer_standing_basis_bypasses_the_memo(self):
        p, calls, stack = self.boundary(self.head())
        with stack, historical._evaluation_scope():
            token = m._STANDING_BASIS.set({'outer': {}})
            try:
                p.validate_boundary(self.root, 'unused-approval.json', self.head())
                p.validate_boundary(self.root, 'unused-approval.json', self.head())
            finally:
                m._STANDING_BASIS.reset(token)
        self.assertEqual(len(calls), 2)

    def test_the_memo_dies_with_its_evaluation(self):
        p, calls, stack = self.boundary(self.head())
        with stack:
            with historical._evaluation_scope():
                p.validate_boundary(self.root, 'unused-approval.json', self.head())
            self.assertIsNone(historical._BOUNDARY_MEMO.get())
            with historical._evaluation_scope():
                p.validate_boundary(self.root, 'unused-approval.json', self.head())
        self.assertEqual(len(calls), 2)


class PublishedViewTests(MigrationFixture):
    """One real publication: the view's bytes do not depend on a remembered boundary."""

    def approve(self):
        # The parent validator is the real committed module graph, as in the publication tests.
        scripts = Path(__file__).resolve().parents[1]
        for source in scripts.glob('*.py'):
            self.write('crux/scripts/'+source.name, source.read_text())
        for source in (scripts.parent/'schemas').glob('*.json'):
            self.write('crux/schemas/'+source.name, source.read_text())
        self.commit('Parent validator installed')
        m.record_approval(self.root, 'approval-one', self.package_path, self.council_path, self.readiness, owner=self.owner)
        self.approval = 'bionic/adrs/migrations/approvals/approval-one.json'
        self.commit('Disposition approval before activation')
        m.write_candidate(self.root, 'publication-one', self.package_path, self.approval)
        self.candidate = 'bionic/adrs/migrations/candidates/publication-one.json'

    def test_view_bytes_are_identical_with_and_without_a_remembered_boundary(self):
        import adr_migration_publication as p
        self.approve()
        self.write('bionic/adrs/migrations/publication-one.publication.json',
                   json.loads((self.root/self.candidate).read_bytes()))
        self.commit('Activate')
        parent = self.git('rev-parse', 'HEAD~1')
        run, calls = _counting_run()
        with patch.object(subprocess, 'run', side_effect=run):
            alone = historical.authority_view(self.root)
            self.assertEqual(len(calls), 1)
            del calls[:]
            with historical._evaluation_scope():
                # Remember the boundary the publication itself proves, then evaluate.
                p.validate_boundary(self.root, self.approval, parent)
                remembered = historical.authority_view(self.root)
        self.assertEqual(json.dumps(alone, sort_keys=True), json.dumps(remembered, sort_keys=True))
        self.assertEqual(alone['state'], 'published')
        # The view's own boundary proof reused the one remembered above.
        self.assertEqual(len(calls), 1)


class ReviewsIndexViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'bionic/adrs/reviews').mkdir(parents=True)
        (self.root/'.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.root/'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.root/'bionic/objectives.md').write_text('---\nmaturity: forming\n---\n# Objectives\nPreserve durable decisions.\n')
        for args in (('init', '-q'), ('config', 'user.email', 'test@example.invalid'), ('config', 'user.name', 'Test')):
            subprocess.run(['git', '-C', str(self.root), *args], check=True)
        spec = importlib.util.spec_from_file_location(
            'generate_reviews_index_under_test', Path(__file__).resolve().parents[1]/'generate-reviews-index.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def commit(self):
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'commit', '-qm', 'fixture'], check=True)

    def run_main(self):
        computed = []
        original = historical._computed_authority_view

        def counting(repo):
            computed.append(repo)
            return original(repo)
        out, err = io.StringIO(), io.StringIO()
        with patch.object(historical, '_computed_authority_view', side_effect=counting), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.module.main(['--dry-run', '--repo-root', str(self.root)])
        return code, out.getvalue(), err.getvalue(), computed

    def test_dry_run_computes_the_authority_view_once(self):
        # An empty reviews directory still takes the probe's view and the closing proof.
        (self.root/'bionic/adrs/reviews/index.md').write_text('placeholder\n')
        self.commit()
        code, out, err, computed = self.run_main()
        self.assertIn(code, (0, 1), err)
        self.assertEqual(len(computed), 1)

    def test_output_is_the_same_whether_or_not_the_view_is_remembered(self):
        (self.root/'bionic/adrs/reviews/index.md').write_text('placeholder\n')
        self.commit()
        code, out, err, _ = self.run_main()
        baseline = (code, out)
        with patch.object(historical, '_view_key', return_value=None):
            code, out, err, computed = self.run_main()
        # With no key the repeat is recomputed (positive control), and the bytes agree.
        self.assertEqual(len(computed), 2)
        self.assertEqual((code, out), baseline)


if __name__ == '__main__':
    unittest.main()
