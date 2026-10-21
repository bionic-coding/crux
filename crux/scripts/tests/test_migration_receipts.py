"""Committed replay receipts: the read-time binding, the writer and the verification check.

A receipt replaces one step of a publication read, the parent reader's subprocess, and
nothing else. These tests build one small published repository per scenario, copy it for
each test, and count the parent reader's runs with a spy on `subprocess.run`. A spy that
reports zero runs proves nothing alone, so every such test pairs it with a read that
replays and shows the spy counting one.
"""
import contextlib
import copy
import importlib.util
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
from test_adr_migration import MigrationFixture
import adr_migration as m
import adr_migration_publication as p
import decision_policy as dp
import implementation_migration as historical
import migration_receipts as mr
from cycle_workflow import CycleError, digest, encoded

SCRIPTS = Path(__file__).resolve().parents[1]
_REAL_RUN = subprocess.run
PUBLICATION = 'bionic/adrs/migrations/publication-one.publication.json'


def _load_cli():
    spec = importlib.util.spec_from_file_location('migration_receipt_cli', SCRIPTS / 'migration-receipt.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLI = _load_cli()


class Reader:
    """Counts the parent approval reader's runs. `stub` answers them without running the reader."""

    def __init__(self, stub=None):
        self.calls = []
        self.stub = stub

    def __call__(self, command, *args, **kwargs):
        if len(command) > 2 and str(command[1]).endswith('adr-migration.py') and command[2] == 'approval':
            self.calls.append(command)
            if self.stub is not None:
                return subprocess.CompletedProcess(command, self.stub, stdout=b'', stderr=b'')
        return _REAL_RUN(command, *args, **kwargs)

    @contextlib.contextmanager
    def watching(self):
        with patch.object(subprocess, 'run', side_effect=self):
            yield self


class _Builder(MigrationFixture):
    """Builds the repository of one scenario. Its steps are shared by every scenario."""

    def build_only(self):
        pass

    def vendor(self):
        # The parent reader is the real committed module graph, as in the publication tests.
        for source in SCRIPTS.glob('*.py'):
            self.write('crux/scripts/' + source.name, source.read_text())
        for source in (SCRIPTS.parent / 'schemas').glob('*.json'):
            self.write('crux/schemas/' + source.name, source.read_text())
        self.commit('Parent validator installed')

    def approve(self):
        self.vendor()
        m.record_approval(self.root, 'approval-one', self.package_path, self.council_path, self.readiness, owner=self.owner)
        self.approval = 'bionic/adrs/migrations/approvals/approval-one.json'
        self.commit('Disposition approval before activation')
        m.write_candidate(self.root, 'publication-one', self.package_path, self.approval)
        self.candidate = 'bionic/adrs/migrations/candidates/publication-one.json'

    def activate(self):
        self.write(PUBLICATION, json.loads((self.root / self.candidate).read_bytes()))
        self.commit('Activate')

def _plain_template():
    builder = _Builder('build_only')
    builder.setUp()
    builder.approve()
    builder.activate()
    return builder


def _derived(name):
    """A builder over a private copy of another scenario, so a scenario need not rebuild its base."""
    info = _template(name)
    builder = _Builder('build_only')
    holder = tempfile.TemporaryDirectory()
    builder.addCleanup(holder.cleanup)
    builder.root = Path(holder.name).resolve() / 'repo'
    shutil.copytree(info['root'], builder.root, symlinks=True)
    builder.docs = builder.root / 'bionic'
    for key, value in info['attrs'].items():
        setattr(builder, key, copy.deepcopy(value))
    return builder


def _forged_template():
    """The parent's approval is invalid, so the real parent reader refuses it."""
    builder = _derived('plain')
    builder.git('reset', '-q', '--hard', 'HEAD~1')  # back to the commit that holds the valid approval
    bad = json.loads((builder.root / builder.approval).read_bytes())
    bad['owner'] = None
    builder.write(builder.approval, bad)
    builder.commit('Invalid approval in parent')
    builder.write(PUBLICATION, {'format': m.FORMATS['publication'], 'id': 'publication-one', 'authority': 'none',
                                'package': builder.bind(builder.package_path), 'approval': builder.bind(builder.approval)})
    builder.commit('Activate over a refused approval')
    return builder


def _installed_template():
    """A consuming project: no vendored plugin source, so the installed reader is the parent reader."""
    builder = _Builder('build_only')
    builder.setUp()
    builder.vendor()
    builder.write('later.txt', 'A later migration, independently approved.\n')
    builder.package.update(initial=False, record=builder.bind('later.txt'))
    builder.write(builder.package_path, builder.package)
    builder.owner['presented'] = builder.bind(builder.package_path)
    builder.readiness = m.installed_support()
    builder.council_path = 'bionic/adrs/councils/later.json'
    vote = builder.council(builder.package_path.removeprefix('bionic/'), builder.bind(builder.package_path)['sha256'])
    vote['readiness'] = builder.readiness
    vote['review_bundle_sha256'] = digest(encoded(m.review_bundle(builder.root, builder.package_path)))
    builder.write(builder.council_path, builder.seal(vote))
    builder.commit('Later installed-support council')
    m.record_approval(builder.root, 'approval-one', builder.package_path, builder.council_path, builder.readiness, owner=builder.owner)
    builder.approval = 'bionic/adrs/migrations/approvals/approval-one.json'
    builder.commit('Later approval')
    shutil.rmtree(builder.root / 'crux')
    builder.commit('Consumer has no vendored Crux source')
    m.write_candidate(builder.root, 'publication-one', builder.package_path, builder.approval)
    builder.candidate = 'bionic/adrs/migrations/candidates/publication-one.json'
    builder.activate()
    return builder


def _chained_template():
    """Two published migrations. Reading the second reads the first inside the parent clone."""
    builder = _derived('plain')
    root = builder.root
    subject = dp.propose(root, {'title': 'Second migration', 'body': '# Decision\nKeep the second rule.\n',
        'governs': [{'domain': 'migration', 'rule': 'Keep the second rule.', 'scope': 'adrs', 'handle': 'second-rule'}]},
        origin='direct')['path']
    raw = (builder.docs / subject).read_bytes()
    builder.write('bionic/adrs/councils/adr-two.json', builder.council(subject, digest(raw), purpose='adr'))
    dp.accept(root, subject, 'adrs/councils/adr-two.json', human_approval='Owner: accept ADR two')
    builder.write('later-two.txt', 'The second independent record.\n')
    source = builder.bind('bionic/' + subject)
    rule = dp.frontmatter((builder.docs / subject).read_text())[0]['governs'][0]
    package = copy.deepcopy(builder.package)
    package.update(id='batch-two', initial=False, record=builder.bind('later-two.txt'))
    package['governing_adr'] = {'source': source, 'receipt': 'bionic/adrs/acceptances/ADR-0002.json'}
    package['items'][0].update(id='item-two', source=source, handle=rule['handle'], clause_sha256=digest(encoded(rule)),
        ceasing=['Keep the second rule.'])
    package_path = 'bionic/adrs/migrations/packages/batch-two.json'
    builder.write(package_path, package)
    owner = dict(builder.owner, presented=builder.bind(package_path))
    council_path = 'bionic/adrs/councils/disposition-two.json'
    vote = builder.council(package_path.removeprefix('bionic/'), builder.bind(package_path)['sha256'])
    vote['readiness'] = builder.readiness
    vote['review_bundle_sha256'] = digest(encoded(m.review_bundle(root, package_path)))
    builder.write(council_path, builder.seal(vote))
    builder.commit('Second package and council')
    # Only the first migration is read with the current reader's full approval validation; the second
    # approval is bound by hash and its reader step is answered by the spy, so building it skips that check.
    with patch.object(m, '_validate_approval_data', side_effect=lambda repo, approval, **kwargs: approval):
        m.record_approval(root, 'approval-two', package_path, council_path, builder.readiness, owner=owner)
        builder.commit('Second disposition approval')
        m.write_candidate(root, 'aaa-two', package_path, 'bionic/adrs/migrations/approvals/approval-two.json')
    builder.write('bionic/adrs/migrations/aaa-two.publication.json',
                  json.loads((root / 'bionic/adrs/migrations/candidates/aaa-two.json').read_bytes()))
    builder.commit('Activate the second migration')
    return builder


_TEMPLATES = {}


def _template(name):
    """Build each scenario's repository once per process; every test reads its own copy."""
    if name not in _TEMPLATES:
        builder = {'plain': _plain_template, 'forged': _forged_template,
                   'installed': _installed_template, 'chained': _chained_template}[name]()
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name).resolve() / 'repo'
        shutil.copytree(builder.root, root, symlinks=True)
        attrs = {k: copy.deepcopy(v) for k, v in vars(builder).items()
                 if k in ('subject', 'proposed', 'readiness', 'package', 'package_path', 'council_path', 'vote',
                          'owner', 'approval', 'candidate')}
        _TEMPLATES[name] = {'holder': holder, 'root': root, 'attrs': attrs}
        builder.doCleanups()
    return _TEMPLATES[name]


class ReceiptCase(MigrationFixture):
    """A private copy of one scenario's published repository."""
    scenario = 'plain'

    def setUp(self):
        info = _template(self.scenario)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        shutil.copytree(info['root'], self.root, symlinks=True)
        self.docs = self.root / 'bionic'
        for key, value in info['attrs'].items():
            setattr(self, key, copy.deepcopy(value))
        self.published = self.head()
        self.parent = self.git('rev-parse', 'HEAD~1')

    def rows(self):
        """Inventory rows by publication id. The commits are fixed by the template, so read them once."""
        info = _template(self.scenario)
        if 'rows' not in info:
            info['rows'] = {json.loads(row['content'])['id']: row for row in p.inventory(self.root)}
        return info['rows']

    def row(self):
        return next(iter(self.rows().values()))

    def receipt_path(self, name='publication-one'):
        return mr.receipt_path(self.root, name)

    def proven(self, row=None):
        """The receipt the parent reader's success proves for a publication, recorded once per scenario."""
        row = row or self.row()
        identity = json.loads(row['content'])['id']
        info = _template(self.scenario)
        key = 'receipt-' + identity
        if key not in info:
            with mr.disabled(), mr.recording() as ran:
                self.facts(Reader(stub=0), row=row)
            info[key] = mr.build(ran[identity])
        return copy.deepcopy(info[key])

    def put(self, value=None, *, commit=True, name='publication-one'):
        value = self.proven() if value is None else value
        self.write(self.receipt_path(name), value)
        if commit:
            self.commit('Replay receipt')

    def reset(self):
        self.git('reset', '-q', '--hard', self.published)
        self.git('clean', '-qfd')

    def facts(self, reader, *, root=None, row=None, standing=False):
        """The publication's parent boundary: the clean clone, the reader step and the receipt hook.

        The current reader's approval check and the baseline standing are answered with fixed values, so a
        test about the reader step does not pay for them. `standing=True` runs both for real, which reads the
        earlier publications inside the parent clone. `full` runs the whole admission.
        """
        root = root or self.root
        row = row or self.row()
        record = json.loads(row['content'])
        identity = dict(id=record['id'], path=row['path'], sha256=row['sha256'], publication_commit=row['publication_commit'])
        context = dict(publication=identity, approval=record['approval'], package=record['package'])
        parent = self.git('rev-parse', row['publication_commit'] + '^1')
        with contextlib.ExitStack() as stack:
            stack.enter_context(reader.watching())
            stack.enter_context(mr.scope(root))
            if not standing:
                stack.enter_context(patch.object(m, 'validate_approval', return_value={}))
                stack.enter_context(patch.object(m, 'current_standing', return_value={}))
            return p.validate_boundary(root, record['approval']['path'], parent, _with_standing=True, receipt=context)

    def full(self, reader, row=None):
        """The whole publication admission, as an authority read runs it."""
        with reader.watching():
            return p.publication_facts(self.root, row or self.row())


class SchemaTests(unittest.TestCase):
    def valid(self):
        return {'format': mr.FORMAT, 'result': 'approved', 'parent': 'a' * 40,
                'publication': {'id': 'publication-one', 'path': 'bionic/adrs/migrations/publication-one.publication.json',
                                'sha256': 'b' * 64, 'publication_commit': 'c' * 40},
                'approval': {'path': 'bionic/adrs/migrations/approvals/a.json', 'sha256': 'd' * 64},
                'package': {'path': 'bionic/adrs/migrations/packages/p.json', 'sha256': 'e' * 64},
                'reader': {'source': 'parent-tree', 'path': 'crux/scripts/adr-migration.py', 'sha256': 'f' * 64,
                           'support_sha256': None}}

    def parsed(self, value):
        return mr.parse(json.dumps(value).encode())

    def test_a_success_admits_and_a_refusal_has_no_representation(self):
        self.assertEqual(self.parsed(self.valid())['result'], 'approved')
        for result in ('refused', 'failed', 'rejected', '', None):
            with self.subTest(result=result):
                value = self.valid()
                value['result'] = result
                with self.assertRaisesRegex(CycleError, mr.INVALID):
                    self.parsed(value)

    def test_the_schema_is_closed_and_binds_the_reader_variants(self):
        installed = self.valid()
        installed['reader'] = {'source': 'installed-support', 'path': 'scripts/adr-migration.py', 'sha256': 'f' * 64,
                               'support_sha256': '1' * 64}
        self.assertEqual(self.parsed(installed)['reader']['source'], 'installed-support')
        broken = []
        extra = self.valid(); extra['note'] = 'x'; broken.append(extra)
        inner = self.valid(); inner['publication']['stale'] = 1; broken.append(inner)
        missing = self.valid(); del missing['parent']; broken.append(missing)
        short = self.valid(); short['parent'] = 'abc'; broken.append(short)
        wrong_format = self.valid(); wrong_format['format'] = 'crux.migration-replay-receipt.v2'; broken.append(wrong_format)
        tree_with_support = self.valid(); tree_with_support['reader']['support_sha256'] = '1' * 64; broken.append(tree_with_support)
        tree_with_installed_path = self.valid(); tree_with_installed_path['reader']['path'] = 'scripts/adr-migration.py'
        broken.append(tree_with_installed_path)
        installed_without_support = copy.deepcopy(installed); installed_without_support['reader']['support_sha256'] = None
        broken.append(installed_without_support)
        installed_with_tree_path = copy.deepcopy(installed); installed_with_tree_path['reader']['path'] = 'crux/scripts/adr-migration.py'
        broken.append(installed_with_tree_path)
        for index, value in enumerate(broken):
            with self.subTest(case=index), self.assertRaisesRegex(CycleError, mr.INVALID):
                self.parsed(value)

    def test_malformed_bytes_refuse(self):
        for raw in (b'', b'{', b'[]', b'null', b'\xff\xfe', json.dumps({'format': mr.FORMAT}).encode()):
            with self.subTest(raw=raw), self.assertRaisesRegex(CycleError, mr.INVALID):
                mr.parse(raw)

    def test_the_receipt_format_joins_no_pinned_inventory(self):
        self.assertNotIn(mr.FORMAT, m.FORMATS.values())
        for inventory in (m.READINESS_INVENTORY, m.INSTALLED_INVENTORY):
            self.assertFalse([name for name in inventory if 'receipt' in name])


class TrustedReadTests(ReceiptCase):
    def counted(self, reader):
        """The facts of one read and how often each non-reader check ran."""
        with patch.object(m, 'validate_approval', wraps=m.validate_approval) as current, \
                patch.object(m, 'current_standing', wraps=m.current_standing) as standing, \
                patch.object(historical, '_revision_repository', wraps=historical._revision_repository) as clone:
            facts = self.full(reader)
        return facts, (clone.call_count, current.call_count, standing.call_count)

    def test_a_trusted_receipt_skips_the_parent_reader_and_nothing_else(self):
        # Objectives that differ from the parent's change nothing: the parent's own are replayed.
        self.write('bionic/objectives.md', '---\nmaturity: forming\n---\n# Objectives\nPreserve durable decisions.\n\n## Shifts\nA later owner edit.\n')
        self.commit('Owner edits objectives after publication')
        replayed = Reader(stub=0)
        expected, checks = self.counted(replayed)
        self.assertEqual(len(replayed.calls), 1)
        self.assertEqual(checks[0], 1, 'the clean parent clone ran')
        self.assertGreaterEqual(checks[1], 1, 'the current reader validated the approval')
        self.assertGreaterEqual(checks[2], 1, 'the standing was computed')
        self.put()
        trusted = Reader(stub=0)
        facts, trusted_checks = self.counted(trusted)
        self.assertEqual(trusted.calls, [])
        self.assertEqual(facts, expected)
        # The clean parent clone, the current reader's approval check and the standing still ran.
        self.assertEqual(trusted_checks, checks)

    def test_a_missing_receipt_replays_and_the_view_bytes_do_not_depend_on_the_receipt(self):
        self.put()
        trusted = Reader(stub=0)
        with trusted.watching():
            with_receipt = json.dumps(historical.authority_view(self.root), sort_keys=True)
        self.assertEqual(trusted.calls, [])
        self.git('rm', '-q', self.receipt_path())
        self.commit('Delete the receipt')
        replayed = Reader(stub=0)
        with replayed.watching():
            without = json.dumps(historical.authority_view(self.root), sort_keys=True)
        self.assertEqual(len(replayed.calls), 1)
        self.assertEqual(with_receipt, without)
        self.assertNotIn('receipts', with_receipt)

    def test_a_receipt_changes_no_discovery_or_inventory(self):
        before = (p.inventory(self.root), historical._discover_publications(self.root))
        self.put()
        self.assertEqual((p.inventory(self.root), historical._discover_publications(self.root)), before)

    def test_no_scope_leaks_between_two_repositories_read_one_after_the_other(self):
        self.put()
        sibling = Path(self.temp.name).resolve() / 'sibling'
        shutil.copytree(self.root, sibling, symlinks=True)
        (sibling / self.receipt_path()).unlink()
        subprocess.run(['git', '-C', str(sibling), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(sibling), 'commit', '-qm', 'Sibling has no receipt'], check=True)
        first = Reader(stub=0)
        self.facts(first)
        self.assertIsNone(mr._SCOPE.get())
        self.assertEqual(first.calls, [])
        second = Reader(stub=0)
        self.facts(second, root=sibling)
        self.assertEqual(len(second.calls), 1)


class UntrustedReceiptTests(ReceiptCase):
    def test_a_new_or_changed_receipt_replays_and_the_reader_refusal_refuses(self):
        cases = {}
        cases['untracked'] = lambda: self.put(commit=False)

        def uncommitted_edit():
            self.put()
            self.write(self.receipt_path(), json.dumps(self.proven(), indent=4))
        cases['edited after introduction, uncommitted'] = uncommitted_edit

        def committed_edit():
            self.put()
            self.write(self.receipt_path(), json.dumps(self.proven(), indent=4))
            self.commit('Edit the receipt after its introduction')
        cases['edited after introduction, committed'] = committed_edit
        for name, arrange in cases.items():
            with self.subTest(case=name):
                self.reset()
                arrange()
                admitted = Reader(stub=0)
                self.facts(admitted)
                self.assertEqual(len(admitted.calls), 1, 'an untrusted receipt must replay')
                refused = Reader(stub=1)
                with self.assertRaisesRegex(CycleError, 'parent migration validator refused'):
                    self.facts(refused)
                self.assertEqual(len(refused.calls), 1)

    def test_a_receipt_introduced_at_or_before_its_publication_commit_refuses(self):
        self.put()
        receipt = self.proven()
        path = self.receipt_path()
        for name, introduced in (('at the publication commit', self.published), ('before it', self.parent)):
            with self.subTest(introduced=name), patch.object(m, 'introduction', return_value=introduced):
                with self.assertRaisesRegex(CycleError, mr.MISMATCH):
                    mr.trust(self.root, path, receipt)
        # Control: the real introduction is a strict descendant of the publication commit.
        self.assertEqual(mr.trust(self.root, path, receipt), 'trusted')
        spy = Reader(stub=0)
        with patch.object(m, 'introduction', return_value=self.published):
            with self.assertRaisesRegex(CycleError, mr.MISMATCH):
                self.facts(spy)
        self.assertEqual(spy.calls, [])


class BindingTests(ReceiptCase):
    def mutations(self):
        other = '9' * 64
        installed = {'source': 'installed-support', 'path': 'scripts/adr-migration.py', 'sha256': other, 'support_sha256': other}
        return [
            ('publication.id', ('publication', 'id'), 'publication-two'),
            ('publication.path', ('publication', 'path'), 'bionic/adrs/migrations/publication-two.publication.json'),
            ('publication.sha256', ('publication', 'sha256'), other),
            ('publication.publication_commit', ('publication', 'publication_commit'), self.parent),
            ('parent', ('parent',), self.published),
            ('approval.path', ('approval', 'path'), 'bionic/adrs/migrations/approvals/approval-two.json'),
            ('approval.sha256', ('approval', 'sha256'), other),
            ('package.path', ('package', 'path'), 'bionic/adrs/migrations/packages/batch-two.json'),
            ('package.sha256', ('package', 'sha256'), other),
            ('reader.sha256', ('reader', 'sha256'), other),
            ('reader.source and path', ('reader',), installed),
        ]

    def test_every_unequal_binding_refuses_with_the_distinct_message_before_any_reader_run(self):
        self.put()
        control = Reader(stub=0)
        self.facts(control)
        self.assertEqual(control.calls, [], 'positive control: the unmodified receipt admits without a reader run')
        for label, route, value in self.mutations():
            with self.subTest(binding=label):
                self.reset()
                receipt = self.proven()
                target = receipt
                for step in route[:-1]:
                    target = target[step]
                target[route[-1]] = value
                self.put(receipt)
                spy = Reader(stub=0)
                with self.assertRaisesRegex(CycleError, mr.MISMATCH):
                    self.facts(spy)
                self.assertEqual(spy.calls, [])

    def test_authority_view_maps_the_new_refusals_to_the_existing_code(self):
        receipt = self.proven()
        receipt['parent'] = self.published
        self.put(receipt)
        with self.assertRaises(historical.Refused) as raised:
            historical.authority_view(self.root)
        self.assertEqual(raised.exception.code, 'migration-authority-input-invalid')
        self.reset()
        self.put(commit=False)
        (self.root / self.receipt_path()).write_bytes(b'{')
        self.commit('Malformed receipt')
        with self.assertRaises(historical.Refused) as raised:
            historical.authority_view(self.root)
        self.assertEqual(raised.exception.code, 'migration-authority-input-invalid')

    def test_no_existing_refusal_message_is_reworded(self):
        self.assertNotEqual(mr.MISMATCH, 'parent migration validator refused disposition approval')
        self.assertNotEqual(mr.INVALID, mr.MISMATCH)
        source = (SCRIPTS / 'adr_migration_publication.py').read_text()
        for message in ('parent migration validator refused disposition approval', 'parent installed validator source changed',
                        'parent migration validator is unavailable', 'publication evidence must exist before activation'):
            self.assertIn(message, source)


class InvalidFileTests(ReceiptCase):
    def refuses(self, label):
        spy = Reader(stub=0)
        with self.assertRaisesRegex(CycleError, mr.INVALID):
            self.facts(spy)
        self.assertEqual(spy.calls, [], label)

    def test_an_unreadable_malformed_symlinked_oversized_or_non_regular_receipt_refuses(self):
        path = self.receipt_path()
        directory = Path(path).parent.as_posix()
        self.put()
        control = Reader(stub=0)
        self.facts(control)
        self.assertEqual(control.calls, [], 'positive control: the intact receipt admits')

        def arrange_malformed():
            self.put(commit=False)
            (self.root / path).write_bytes(b'{"format": ')

        def arrange_schema_invalid():
            receipt = self.proven()
            receipt['result'] = 'refused'
            self.put(receipt, commit=False)

        def arrange_empty():
            self.put(commit=False)
            (self.root / path).write_bytes(b'')

        def arrange_oversized():
            self.put(commit=False)
            (self.root / path).write_bytes(encoded(self.proven()) + b' ' * (mr.MAX_BYTES + 1))

        def arrange_symlinked_file():
            self.put(commit=False)
            (self.root / path).rename(self.root / 'elsewhere.json')
            (self.root / path).symlink_to(self.root / 'elsewhere.json')

        def arrange_symlinked_directory():
            self.put(commit=False)
            shutil.move(str(self.root / directory), str(self.root / 'moved-receipts'))
            (self.root / directory).symlink_to(self.root / 'moved-receipts', target_is_directory=True)

        def arrange_directory_in_place_of_file():
            (self.root / path).mkdir(parents=True)

        def arrange_fifo():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            os.mkfifo(self.root / path)

        for name, arrange in (('malformed', arrange_malformed), ('schema-invalid', arrange_schema_invalid),
                              ('empty', arrange_empty), ('oversized', arrange_oversized),
                              ('symlinked file', arrange_symlinked_file),
                              ('symlinked directory', arrange_symlinked_directory),
                              ('directory in place of the file', arrange_directory_in_place_of_file),
                              ('named pipe', arrange_fifo)):
            with self.subTest(case=name):
                self.reset()
                arrange()
                self.refuses(name)

    def test_a_dangling_symlink_holds_no_receipt_so_the_read_replays(self):
        self.reset()
        directory = Path(self.receipt_path()).parent
        (self.root / directory).parent.mkdir(parents=True, exist_ok=True)
        (self.root / directory).symlink_to(self.root / 'nowhere', target_is_directory=True)
        spy = Reader(stub=0)
        self.facts(spy)
        self.assertEqual(len(spy.calls), 1)


class StageTransactionTests(ReceiptCase):
    def test_a_receipt_path_can_never_ride_in_an_activation(self):
        candidate = json.loads((self.root / self.candidate).read_bytes())
        path = self.receipt_path()
        base = {PUBLICATION: encoded(candidate)}
        reached = KeyError('reached the parent validation')
        with patch.object(p, 'validate_boundary', side_effect=reached):
            # Control: the same publication-only transaction passes the confinement checks.
            with self.assertRaises(KeyError):
                p.stage_transaction(self.root, self.candidate, dict(base), initial_scope=set(base))
            changes = dict(base, **{path: b'{}'})
            with self.assertRaisesRegex(CycleError, 'cannot write approval, configuration, objectives or historical proof'):
                p.stage_transaction(self.root, self.candidate, changes, initial_scope=set(changes))
        # The second prefix list (the snapshot loop) refuses it as well.
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse((self.root / path).exists())


class WriterTests(ReceiptCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = CLI.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_write_runs_the_real_parent_reader_once_and_is_deterministic(self):
        reader = Reader()
        with reader.watching():
            code, out, err = self.run_cli('write', '--repo-root', str(self.root), '--publication', PUBLICATION)
        self.assertEqual((code, err), (0, ''), out)
        self.assertEqual(len(reader.calls), 1)
        result = json.loads(out)
        self.assertEqual((result['status'], result['changed'], result['path']), ('written', True, self.receipt_path()))
        raw = (self.root / self.receipt_path()).read_bytes()
        self.assertEqual(raw, encoded(self.proven()))
        self.assertEqual(mr.parse(raw)['result'], 'approved')
        # No timestamp, host path, interpreter or environment value is recorded.
        for forbidden in (str(self.root).encode(), self.temp.name.encode(), sys.executable.encode()):
            self.assertNotIn(forbidden, raw)
        self.assertNotRegex(raw.decode(), r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}')
        self.assertEqual(mr.parse(raw)['reader']['path'], 'crux/scripts/adr-migration.py')

    def test_write_is_a_no_op_on_identical_bytes_and_never_overwrites(self):
        # The replay it consumes is the one the real write above proves; here only the file rules are in question.
        with patch.object(CLI, 'replay', side_effect=lambda repo, row: self.proven()):
            self.assertEqual(self.run_cli('write', '--repo-root', str(self.root), '--publication', PUBLICATION)[0], 0)
            code, out, _ = self.run_cli('write', '--repo-root', str(self.root), '--publication', PUBLICATION)
            self.assertEqual((code, json.loads(out)['changed']), (0, False))
            target = self.root / self.receipt_path()
            target.write_bytes(target.read_bytes() + b' ')
            before = target.read_bytes()
            code, out, _ = self.run_cli('write', '--repo-root', str(self.root), '--publication', PUBLICATION)
        self.assertEqual(code, 1)
        self.assertIn('other bytes', json.loads(out)['error'])
        self.assertEqual(target.read_bytes(), before)

    def test_write_refuses_an_unknown_or_uncommitted_publication_and_writes_nothing(self):
        self.write('bionic/adrs/migrations/unlisted.publication.json',
                   json.loads((self.root / self.candidate).read_bytes()))
        for publication in ('bionic/adrs/migrations/unlisted.publication.json',
                            'bionic/adrs/migrations/missing.publication.json', '../outside.json'):
            with self.subTest(publication=publication):
                code, out, _ = self.run_cli('write', '--repo-root', str(self.root), '--publication', publication)
                self.assertEqual(code, 1, out)
                self.assertEqual(json.loads(out)['status'], 'refused')
        self.assertFalse((self.root / self.receipt_path()).exists())

    def test_the_command_line_rejects_misuse_with_exit_two(self):
        for argv in (['write', '--repo-root', str(self.root)], ['verify', '--repo-root', str(self.root)],
                     ['verify', '--repo-root', str(self.root), '--all', '--since', self.published],
                     ['write', '--repo-root', str(self.root), '--publication', PUBLICATION, '--all'],
                     ['verify', '--repo-root', str(self.root), '--all', '--publication', PUBLICATION], ['unknown']):
            with self.subTest(argv=argv):
                code, out, err = self.run_cli(*argv)
                self.assertEqual((code, out), (2, ''))
                self.assertTrue(err)


class ForgedReceiptTests(ReceiptCase):
    scenario = 'forged'

    def test_the_writer_refuses_over_a_refused_approval_and_writes_nothing(self):
        reader = Reader()
        with reader.watching():
            code, out, _ = WriterTests.run_cli(self, 'write', '--repo-root', str(self.root), '--publication', PUBLICATION)
        self.assertEqual(code, 1, out)
        self.assertIn('parent migration validator refused disposition approval', json.loads(out)['error'])
        self.assertEqual(len(reader.calls), 1)
        self.assertFalse((self.root / self.receipt_path()).exists())

    def test_an_uncommitted_forged_receipt_is_replayed_and_the_replay_refuses(self):
        self.put(commit=False)
        reader = Reader()
        with self.assertRaisesRegex(CycleError, 'parent migration validator refused'):
            self.facts(reader)
        self.assertEqual(len(reader.calls), 1)

    def test_a_committed_forged_receipt_is_caught_by_verification_not_by_the_read(self):
        self.put()
        # The read trusts the committed receipt by design; the current reader is relaxed here
        # exactly as in the parent-refusal control, so only the skipped step is in question.
        trusted = Reader()
        self.facts(trusted)
        self.assertEqual(trusted.calls, [])
        # The verification check replays against the exact parent and names the receipt.
        out, err = io.StringIO(), io.StringIO()
        reader = Reader()
        with reader.watching(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = CLI.main(['verify', '--repo-root', str(self.root), '--since', self.published])
        self.assertEqual(code, 1, err.getvalue())
        report = json.loads(out.getvalue())
        self.assertEqual(report['status'], 'findings')
        self.assertEqual(report['findings'][0]['receipt'], self.receipt_path())
        self.assertIn('parent migration validator refused', report['findings'][0]['error'])
        self.assertEqual(len(reader.calls), 1)
        # Control: a read with no receipt replays and refuses (the refusal is real, not cached).
        self.git('rm', '-q', self.receipt_path())
        self.commit('Delete the forged receipt')
        replayed = Reader()
        with self.assertRaisesRegex(CycleError, 'parent migration validator refused'):
            self.facts(replayed)
        self.assertEqual(len(replayed.calls), 1)


class VerifyTests(ReceiptCase):
    def verify(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = CLI.main(['verify', '--repo-root', str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()

    def orphan(self, name):
        receipt = self.proven()
        receipt['publication']['id'] = name
        self.write(self.receipt_path(name), receipt)

    def test_a_clean_committed_receipt_verifies_after_one_replay(self):
        self.put(self.proven())
        reader = Reader(stub=0)
        with reader.watching():
            code, out, err = self.verify('--all')
        self.assertEqual((code, err), (0, ''), out)
        self.assertEqual(json.loads(out)['checked'], ['publication-one.json'])
        self.assertEqual(len(reader.calls), 1)
        # A receipt whose bytes are not the canonical encoding is a finding.
        self.write(self.receipt_path(), json.dumps(self.proven(), indent=4))
        self.commit('Re-encode the receipt')
        with Reader(stub=0).watching():
            code, out, _ = self.verify('--all')
        self.assertEqual(code, 1)

    def test_since_selects_only_receipts_added_or_changed_after_the_anchor(self):
        self.put()
        anchor = self.head()
        self.orphan('zz-orphan')
        self.commit('A second receipt')
        with patch.object(CLI, 'replay', return_value=self.proven()) as replay:
            code, out, _ = self.verify('--since', anchor)
            report = json.loads(out)
            self.assertEqual(report['checked'], ['zz-orphan.json'])
            self.assertEqual(code, 1)
            self.assertIn('orphan', report['findings'][0]['error'])
            self.assertEqual(replay.call_count, 0)
            code, out, _ = self.verify('--since', self.published)
            self.assertEqual(json.loads(out)['checked'], ['publication-one.json', 'zz-orphan.json'])
            self.assertEqual(replay.call_count, 1)
            code, out, _ = self.verify('--all')
            self.assertEqual(json.loads(out)['checked'], ['publication-one.json', 'zz-orphan.json'])
            # A change since the anchor brings an already-anchored receipt back into scope.
            self.write(self.receipt_path(), self.proven())
            (self.root / self.receipt_path()).write_bytes((self.root / self.receipt_path()).read_bytes() + b'\n')
            self.commit('Touch the first receipt')
            code, out, _ = self.verify('--since', anchor)
            self.assertEqual(json.loads(out)['checked'], ['publication-one.json', 'zz-orphan.json'])

    def test_an_unusable_anchor_exits_two_and_never_narrows_the_scope(self):
        self.put()
        self.git('checkout', '-q', '-b', 'side', self.published)
        self.write('side.txt', 'a commit that is not an ancestor of the branch under test\n')
        self.commit('Side commit')
        side = self.head()
        self.git('checkout', '-q', '-')
        head = self.head()
        with patch.object(CLI, 'replay', return_value=self.proven()) as replay:
            code, out, _ = self.verify('--since', head)
            self.assertEqual(code, 0, 'control: a full ancestor commit is accepted')
            replays = replay.call_count
            for anchor in (head[:12], 'HEAD', 'side', '0' * 40, 'f' * 40, side, '--all', ''):
                with self.subTest(anchor=anchor):
                    code, out, err = self.verify('--since', anchor)
                    self.assertEqual((code, out), (2, ''))
                    self.assertIn('--since', err)
            self.assertEqual(replay.call_count, replays, 'an unusable anchor replays nothing')

    def test_an_orphan_uncommitted_or_unexpected_entry_is_a_finding(self):
        self.put()
        self.orphan('zz-orphan')
        (self.root / Path(self.receipt_path()).parent / 'notes.txt').write_text('stray\n')
        with patch.object(CLI, 'replay', return_value=self.proven()):
            code, out, _ = self.verify('--all')
        report = json.loads(out)
        self.assertEqual(code, 1)
        errors = {Path(f['receipt']).name: f['error'] for f in report['findings']}
        self.assertIn('orphan', errors['zz-orphan.json'])
        self.assertIn('unexpected entry', errors['notes.txt'])
        self.assertNotIn('publication-one.json', errors)

    def test_an_uncommitted_receipt_is_untrusted_and_reported(self):
        self.put(commit=False)
        with patch.object(CLI, 'replay', return_value=self.proven()):
            code, out, _ = self.verify('--all')
        self.assertEqual(code, 1)
        self.assertIn('uncommitted', json.loads(out)['findings'][0]['error'])

    def test_a_mismatched_receipt_names_the_differing_fields(self):
        receipt = self.proven()
        receipt['reader']['sha256'] = '9' * 64
        self.put(receipt)
        with patch.object(CLI, 'replay', return_value=self.proven()):
            code, out, _ = self.verify('--all')
        self.assertEqual(code, 1)
        self.assertIn('reader', json.loads(out)['findings'][0]['error'])

    def test_a_symlinked_receipts_directory_or_ancestor_refuses_the_listing(self):
        self.put()
        directory = Path(self.receipt_path()).parent
        shutil.move(str(self.root / directory), str(self.root / 'moved-receipts'))
        (self.root / directory).symlink_to(self.root / 'moved-receipts', target_is_directory=True)
        code, out, _ = self.verify('--all')
        self.assertEqual(code, 1)
        self.assertIn('symlink', json.loads(out)['error'])
        # The same class at an ancestor of the directory.
        (self.root / directory).unlink()
        shutil.move(str(self.root / 'moved-receipts'), str(self.root / directory))
        migrations = self.root / 'bionic/adrs/migrations'
        shutil.move(str(migrations), str(self.root / 'moved-migrations'))
        migrations.symlink_to(self.root / 'moved-migrations', target_is_directory=True)
        code, out, _ = self.verify('--all')
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)['status'], 'refused')

    def test_no_receipts_is_clean(self):
        code, out, _ = self.verify('--all')
        self.assertEqual((code, json.loads(out)['checked']), (0, []))


class InstalledSupportTests(ReceiptCase):
    scenario = 'installed'

    def test_an_installed_support_receipt_binds_the_installed_reader_and_its_support_record(self):
        receipt = self.proven()
        script = (SCRIPTS / 'adr-migration.py').read_bytes()
        self.assertEqual(receipt['reader'], {'source': 'installed-support', 'path': 'scripts/adr-migration.py',
                                             'sha256': digest(script), 'support_sha256': digest(encoded(self.readiness))})
        replayed = Reader(stub=0)
        expected = self.facts(replayed)
        self.assertEqual(len(replayed.calls), 1)
        self.put(receipt)
        trusted = Reader(stub=0)
        self.assertEqual(self.facts(trusted), expected)
        self.assertEqual(trusted.calls, [])

    def test_a_support_record_mismatch_refuses(self):
        for label, field, value in (('support_sha256', 'support_sha256', '9' * 64), ('reader sha256', 'sha256', '9' * 64)):
            with self.subTest(field=label):
                self.reset()
                receipt = self.proven()
                receipt['reader'][field] = value
                self.put(receipt)
                spy = Reader(stub=0)
                with self.assertRaisesRegex(CycleError, mr.MISMATCH):
                    self.facts(spy)
                self.assertEqual(spy.calls, [])
        # A receipt for the vendored-tree reader does not describe an installed reader.
        self.reset()
        receipt = self.proven()
        receipt['reader'] = {'source': 'parent-tree', 'path': 'crux/scripts/adr-migration.py',
                             'sha256': receipt['reader']['sha256'], 'support_sha256': None}
        self.put(receipt)
        with self.assertRaisesRegex(CycleError, mr.MISMATCH):
            self.facts(Reader(stub=0))

    def test_a_changed_installed_script_refuses_before_any_receipt_check(self):
        self.put()
        real = digest
        changed = Reader(stub=0)
        with patch.object(p, 'digest', side_effect=lambda raw: 'f' * 64 if raw.startswith(b'#!/usr/bin/env python3') else real(raw)), \
                patch.object(mr, 'consult', side_effect=AssertionError('the receipt was consulted first')):
            with self.assertRaisesRegex(CycleError, 'parent installed validator source changed'):
                self.facts(changed)
        self.assertEqual(changed.calls, [])


class NestedReadTests(ReceiptCase):
    """The second migration sorts first, so admitting it reads the first one inside its parent clone."""
    scenario = 'chained'

    def receipts_for_both(self):
        for identity, row in self.rows().items():
            self.put(self.proven(row), name=identity, commit=False)
        self.commit('Both receipts')

    def admit(self, reader):
        return self.facts(reader, row=self.rows()['aaa-two'], standing=True)

    @staticmethod
    def approvals(reader):
        return [Path(call[-1]).name for call in reader.calls]

    def test_two_chained_publications_read_with_no_reader_run_when_both_receipts_exist(self):
        self.assertEqual(list(self.rows()), ['aaa-two', 'publication-one'])
        replayed = Reader(stub=0)
        expected = self.admit(replayed)
        # The earlier migration is proved inside the later one's parent clone.
        self.assertEqual(self.approvals(replayed), ['approval-two.json', 'approval-one.json'])
        self.receipts_for_both()
        trusted = Reader(stub=0)
        actual = self.admit(trusted)
        self.assertEqual(trusted.calls, [])
        self.assertEqual(actual, expected)

    def test_a_missing_or_untrusted_outer_receipt_for_the_earlier_publication_replays_in_the_nested_read(self):
        earlier = self.receipt_path('publication-one')
        # A receipt that is missing for the earlier publication replays there too: the first test reads the
        # chain with no receipt at all and sees that nested replay. Here the earlier receipt is edited.
        self.receipts_for_both()
        raw = (self.root / earlier).read_text()
        self.write(earlier, json.dumps(json.loads(raw), indent=4))
        spy = Reader(stub=0)
        self.admit(spy)
        self.assertEqual(self.approvals(spy), ['approval-one.json'],
                         'only the earlier publication replays, inside the later one\'s parent clone')


if __name__ == '__main__':
    unittest.main()
