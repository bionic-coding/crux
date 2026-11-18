"""A release record carries one of two fixed task lists chosen at create and the cycle writer completes it.

The release ledger (`tools/release.py`) is the evidence of a release; the record holds one task per fixed step
of its list. `create_release` fixes the list and the version, `record_release` closes the steps once the ledger
shows the target published, and the writer refuses every ordinary milestone on such a record. The CLI form of
create is covered by test_cycle_writer.py (the release create command tests).
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_writer
from cycle_store import CycleError

try:
    from ._dev_surface import REPO_ROOT, TREE, require_dev_surface
except ImportError:
    from _dev_surface import REPO_ROOT, TREE, require_dev_surface

SCRIPTS = Path(__file__).resolve().parents[1]
BETA = ['prep', 'prepare', 'verify', 'beta-and-smoke', 'tag', 'record']
OFFICIAL = ['live-check-and-go-ahead', 'official', 'record']
SCOPE = ['src', 'bionic/log.md']


def arguments(**values):
    return SimpleNamespace(**values)


class ListedBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        for directory in ('bionic', 'src'):
            (self.root / directory).mkdir(parents=True)
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.root / 'bionic/log.md').write_text('log\n')
        (self.root / 'src/a.txt').write_text('good')
        self.git('init', '-q')
        # The fixture's own identity: a release record is created against HEAD, and CI configures no identity.
        self.git('config', 'user.name', 'T')
        self.git('config', 'user.email', 't@example.invalid')
        self.git('add', '-A')
        self.git('commit', '-qm', 'base')

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@example.invalid', *args], cwd=self.root, capture_output=True, check=True, text=True).stdout.strip()

    def make(self, release_list='beta', version='1.2.3'):
        return cycle_writer.create_release(self.root, release_list, version, 'Release', 'Outcome', SCOPE, ['published'], 'tester')

    def path(self, doc):
        return self.root / 'bionic/cycles' / doc['id'] / 'cycle.json'

    def mutate(self, doc, action, **values):
        return cycle_writer.mutate(self.root, doc['id'], 'tester', doc['revision'], action, arguments(**values))


class CreateTests(ListedBase):
    def test_a_release_record_needs_a_known_list_and_a_version_and_burns_no_id(self):
        for release_list, version in ((None, '1.2.3'), ('both', '1.2.3'), ('beta', None), ('beta', '1.2')):
            with self.subTest(release_list=release_list, version=version), self.assertRaises(CycleError):
                self.make(release_list, version)
        self.assertFalse((self.root / 'bionic/cycles').exists() and any((self.root / 'bionic/cycles').glob('CYC-*')))
        self.assertEqual(self.make('official')['release']['list'], 'official')  # positive control

    def test_the_beta_list(self):
        doc = self.make('beta')
        self.assertEqual([t['id'] for t in doc['tasks']], BETA)
        self.assertEqual((doc['kind'], doc['release'], doc['state']), ('release', {'list': 'beta', 'version': '1.2.3'}, 'working'))

    def test_the_official_list(self):
        doc = self.make('official')
        self.assertEqual([t['id'] for t in doc['tasks']], OFFICIAL)
        self.assertEqual(doc['release']['list'], 'official')

    def test_every_task_is_chained_pending_and_carries_a_description(self):
        for name in ('beta', 'official'):
            doc = self.make(name)
            previous = None
            for task in doc['tasks']:
                self.assertEqual(task['depends_on'], [previous] if previous else [])
                self.assertEqual(task['status'], 'pending')
                self.assertTrue(task['description'].strip())
                self.assertNotRegex(json.dumps(task), r'ADR-\d')
                previous = task['id']

    def test_the_writer_beta_list_equals_the_list_of_a_frozen_historical_record(self):
        frozen = json.loads((Path(__file__).resolve().parent / 'fixtures/cycle-history/fresh/release.json').read_text())
        expected = [(t['id'], t['description'], t['expected_evidence'][0]) for t in frozen['plan']['tasks']]
        self.assertEqual(cycle_writer.RELEASE_LISTS['beta'], expected)


class ActionTests(ListedBase):
    """Pause, resume and abandon stay available on a release record; the refusal of every ordinary milestone is covered by
    test_cycle_writer.py (test_a_release_record_refuses_ordinary_task_batch_finish_and_reopen_writes)."""

    def test_pause_resume_and_abandon_need_no_reflection(self):
        doc = self.make()
        doc = self.mutate(doc, 'pause', reason='withheld go-ahead')
        doc = self.mutate(doc, 'resume', reconcile='git status and the ledger show the same step', reason='go-ahead given')
        self.assertEqual(doc['state'], 'working')
        doc = self.mutate(doc, 'abandon', reason='the owner stopped the release')
        self.assertEqual(doc['state'], 'abandoned')


class AdvanceTests(ListedBase):
    """`record_release` completes a release record once the ledger shows the target published."""

    def test_record_release_completes_both_lists_with_every_step_done(self):
        for name, ids in (('beta', BETA), ('official', OFFICIAL)):
            doc, changed = cycle_writer.record_release(self.root, self.make(name)['id'], 'a' * 40, 'cycles/x/evidence/release/release-op.md')
            self.assertTrue(changed)
            self.assertEqual((doc['state'], [t['id'] for t in doc['tasks']], {t['status'] for t in doc['tasks']}), ('completed', ids, {'done'}), name)
            self.assertEqual(doc['completion']['commit'], 'a' * 40)

    def test_a_replay_changes_nothing_and_an_abandoned_record_refuses(self):
        doc = self.make()
        first, _ = cycle_writer.record_release(self.root, doc['id'], 'a' * 40, 'ledger.json')
        before = self.path(doc).read_bytes()
        again, changed = cycle_writer.record_release(self.root, doc['id'], 'b' * 40, 'other.json')
        self.assertEqual((changed, again, self.path(doc).read_bytes()), (False, first, before))
        other = self.make()
        self.mutate(other, 'abandon', reason='the owner stopped the release')
        with self.assertRaisesRegex(CycleError, 'abandoned'):
            cycle_writer.record_release(self.root, other['id'], 'a' * 40, 'ledger.json')


class CommittedRecordsTests(unittest.TestCase):
    """Every committed legacy cycle record loads, checks and renders its facts through the read-only history reader."""
    ROOT = REPO_ROOT

    def test_every_committed_record_validates_and_renders(self):
        require_dev_surface(self, self.ROOT / TREE / 'cycles' / 'CYC-0040' / 'cycle.json', 'committed cycle records')
        import cycle_history
        # A record with a format value has its own reader, outside this one.
        ids = sorted(p.name for p in (self.ROOT / TREE / 'cycles').glob('CYC-*') if (p / 'cycle.json').is_file()
                     and json.loads((p / 'cycle.json').read_text()).get('format') not in ('crux.cycle.vNext', 'crux.cycle.v1'))
        legacy = {'CYC-0009', 'CYC-0015', 'CYC-0018', 'CYC-0021', 'CYC-0022', 'CYC-0031', 'CYC-0032', 'CYC-0034', 'CYC-0037', 'CYC-0040'}
        self.assertLessEqual(legacy, set(ids))
        for cid in ids:
            with self.subTest(cycle=cid):
                doc = cycle_history.load_record(self.ROOT, cid)
                shown = cycle_history.facts(doc)
                self.assertEqual(shown['id'], cid)
                if cid in legacy:
                    self.assertNotIn('release_list', doc)
                    self.assertEqual(shown['phases'], ['plan', 'release', 'reflect'])
                    self.assertEqual(shown['pass_limit'], doc['pass_limit'])


if __name__ == '__main__':
    unittest.main()
