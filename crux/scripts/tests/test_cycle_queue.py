"""The persistent cycle queue: ordering, authorization, sequential start and recovery.

Every test runs in a temporary repository whose docs_dir is `notes`, never `bionic`.
Acceptance criteria 1-9 of the queue plan are named in the test names (ac1 ... ac9).
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_queue
from cycle_workflow import create, load, now, PHASES
from cycle_progress import view, render

DATE = '2026-10-19'
IDENTITY = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.invalid',
            'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid'}


class Crash(BaseException):
    """Stands in for a process death: not an Exception, so no cleanup handler runs."""


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        # The root is no git repository, so the fixture's identity comes from the environment:
        # `queue start-next` stops without one, and CI configures none.
        identity = patch.dict(os.environ, IDENTITY)
        identity.start()
        self.addCleanup(identity.stop)
        (self.repo / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: notes\n')
        (self.repo / 'notes').mkdir()
        (self.repo / 'notes/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.repo / 'notes/objectives.md').write_text('Mission: useful changes.')
        (self.repo / 'src').mkdir()
        (self.repo / 'src/a.py').write_text('x = 1\n')
        self.assertFalse((self.repo / 'bionic').exists())

    # -- helpers -----------------------------------------------------------
    def cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'queue', *argv])
        return code, json.loads(out.getvalue())

    def ok(self, *argv):
        code, payload = self.cli(*argv)
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload['ok'], payload)
        return payload

    def refused(self, *argv, code=1):
        got, payload = self.cli(*argv)
        self.assertEqual(got, code, payload)
        self.assertFalse(payload['ok'])
        return payload

    def add(self, title='Item', depends=(), kind='quick-fix', *extra):
        argv = ['add', '--title', title, '--outcome', f'Deliver {title}', '--type', kind, '--scope', 'src', '--acceptance', 'it works']
        for d in depends:
            argv += ['--depends-on', d]
        return self.ok(*argv, *extra)['item']['id']

    def authorize(self, kind, count=None, instruction='run it'):
        argv = ['authorize', '--kind', kind, '--instruction', instruction, '--date', DATE]
        if count is not None:
            argv += ['--count', str(count)]
        return self.ok(*argv)

    def start(self):
        return self.cli('start-next')

    def stop_reason(self):
        code, payload = self.start()
        self.assertEqual(code, 1, payload)
        self.assertFalse(payload['ok'])
        return payload['stop']['reason']

    def cycle_dirs(self):
        return sorted(p.name for p in (self.repo / 'notes/cycles').glob('*CYC-*'))

    def end_cycle(self, identity, status):
        path = self.repo / 'notes/cycles' / identity / 'cycle.json'
        doc = json.loads(path.read_text())
        doc['status'] = status
        doc['history'].append({'at': now(), 'action': 'reflect', 'pass': doc['pass'], 'phase': doc['phase'], 'status': status})
        path.write_text(json.dumps(doc))

    def item(self, qid):
        return next(i for i in self.ok('list', '--full')['items'] if i['id'] == qid)

    def queue_doc(self):
        import yaml
        return yaml.safe_load((self.repo / 'notes/queue/cycles.yaml').read_text())


class ArchiveTests(Base):
    def test_full_history_keeps_earlier_unresolved_active_cycle_in_execution_order(self):
        for fault in ('missing', 'malformed'):
            with self.subTest(fault=fault):
                case = Base()
                case.setUp()
                self.addCleanup(case.doCleanups)
                earlier, later = case.add('earlier'), case.add('later')
                pending, held = case.add('pending'), case.add('held')
                case.ok('hold', held, '--reason', 'Owner hold')
                case.authorize('queue', instruction='I authorize the original queue order')
                first = case.start()[1]
                case.end_cycle(first['cycle'], 'completed')
                second = case.start()[1]
                case.end_cycle(second['cycle'], 'completed')
                record = case.repo / 'notes/cycles' / first['cycle'] / 'cycle.json'
                if fault == 'missing':
                    record.unlink()
                else:
                    record.write_text('{invalid JSON')
                authorization = case.queue_doc()['authorization']
                case.ok('archive', '--migrate')
                full = case.ok('list', '--full')['items']
                self.assertEqual([item['id'] for item in full], [earlier, later, pending, held])
                self.assertEqual([item['position'] for item in full], [1, 2, 3, 4])
                self.assertEqual(case.queue_doc()['authorization'], authorization)
                self.assertEqual(case.stop_reason(), 'cycle-missing')

    def test_full_history_keeps_moved_execution_order_across_three_sweeps(self):
        a, b, c = self.add('A'), self.add('B'), self.add('C')
        self.ok('move', c, '--position', '1')
        self.ok('edit', a, '--depends-on', c)
        self.ok('edit', b, '--depends-on', a)
        for index, qid in enumerate((c, a, b)):
            self.authorize('next', instruction='I authorize only ' + qid)
            started = self.start()[1]
            self.assertEqual(started['item'], qid)
            self.end_cycle(started['cycle'], 'completed')
            authorization = self.queue_doc()['authorization']
            self.ok('archive', *(['--migrate'] if index == 0 else []))
            self.assertEqual(self.queue_doc()['authorization'], authorization)
        self.assertEqual([item['id'] for item in self.ok('list', '--full')['items']], [c, a, b])

    def test_actual_queue_budget_accepts_multibyte_limit_and_refuses_one_more(self):
        self.add('budget')
        self.authorize('queue', instruction='漢')
        cfg = cycle_queue.tree(self.repo)
        doc = cycle_queue.read_queue(cfg)
        remaining = cycle_queue.MAX_QUEUE_BYTES - len(cycle_queue.queue_bytes(doc))
        doc['authorization']['instruction'] += '漢' * (remaining // 3) + 'x' * (remaining % 3)
        payload = cycle_queue.queue_bytes(doc)
        self.assertEqual(len(payload), cycle_queue.MAX_QUEUE_BYTES)
        cycle_queue.write_queue(cfg, doc)
        self.assertTrue(view(self.repo)['queue']['ok'])
        doc['authorization']['instruction'] += 'x'
        with self.assertRaisesRegex(cycle_queue.QueueError, 'byte limit'):
            cycle_queue.write_queue(cfg, doc)
        self.assertEqual(cycle_queue.queue_file(cfg).read_bytes(), payload)

    def test_active_queue_byte_budget_is_utf8_and_atomic(self):
        self.add('漢字')
        cfg = cycle_queue.tree(self.repo)
        path = cycle_queue.queue_file(cfg)
        original = path.read_bytes()
        doc = cycle_queue.read_queue(cfg)
        doc['items'][0]['title'] += '漢'
        encoded = cycle_queue._yaml().safe_dump(cycle_queue._ordered(doc), sort_keys=False,
            default_flow_style=False, allow_unicode=True, width=100).encode('utf-8')
        with patch.object(cycle_queue, 'MAX_QUEUE_BYTES', len(encoded), create=True):
            cycle_queue.write_queue(cfg, doc)
            self.assertEqual(cycle_queue.read_queue(cfg), doc)
            self.assertTrue(view(self.repo)['queue']['ok'])
        path.write_bytes(original)
        with patch.object(cycle_queue, 'MAX_QUEUE_BYTES', len(encoded) - 1, create=True):
            with self.assertRaisesRegex(cycle_queue.QueueError, 'byte limit'):
                cycle_queue.write_queue(cfg, doc)
            self.assertEqual(path.read_bytes(), original)
        path.write_bytes(encoded)
        with patch.object(cycle_queue, 'MAX_QUEUE_BYTES', len(encoded) - 1, create=True):
            with self.assertRaisesRegex(cycle_queue.QueueError, 'byte limit'):
                cycle_queue.read_queue(cfg)
            unavailable = view(self.repo)['queue']
            self.assertFalse(unavailable['ok'])
            self.assertIn('byte limit', unavailable['error'])

    def test_oversized_mutation_refuses_before_archiving(self):
        first = self.add('first')
        self.authorize('queue')
        started = self.start()[1]
        self.end_cycle(started['cycle'], 'completed')
        self.ok('archive', '--migrate')
        self.add('second')
        self.authorize('queue')
        self.end_cycle(self.start()[1]['cycle'], 'completed')
        cfg = cycle_queue.tree(self.repo)
        path = cycle_queue.queue_file(cfg)
        original = path.read_bytes()
        with patch.object(cycle_queue, 'MAX_QUEUE_BYTES', len(original) + 1):
            self.refused('add', '--title', 'extra', '--outcome', 'X' * 2000, '--type', 'quick-fix',
                '--scope', 'src', '--acceptance', 'works')
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual([p.stem for p in (self.repo / 'notes/queue/history/items').glob('*.json')], [first])

    def test_archive_is_explicit_and_resolves_completed_dependency(self):
        first = self.add('first')
        second = self.add('second', (first,))
        self.authorize('queue')
        code, started = self.start()
        self.assertEqual(code, 0)
        self.end_cycle(started['cycle'], 'completed')
        preview = self.ok('archive', '--dry-run')
        self.assertEqual(preview['items'], [first])
        self.assertEqual(self.queue_doc()['format_version'], 1)
        self.ok('archive', '--migrate')
        self.assertEqual(self.queue_doc()['format_version'], 2)
        self.assertEqual([i['id'] for i in self.queue_doc()['items']], [second])
        self.assertEqual(self.ok('show', first)['item']['id'], first)
        self.assertEqual([i['id'] for i in self.ok('list', '--full')['items']], [first, second])
        self.assertTrue(view(self.repo)['queue']['ok'])
        self.assertIn(first, render(view(self.repo)))
        self.assertEqual(self.start()[1]['outcome'], 'started')

    def test_archive_replay_coalesces_duplicate_and_rejects_conflict(self):
        first = self.add('first')
        self.authorize('next')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'completed')
        with patch('cycle_queue.write_queue', side_effect=Crash):
            with self.assertRaises(Crash):
                cycle_queue.archive(self.repo, migrate=True)
        self.assertEqual(self.queue_doc()['format_version'], 1)
        self.ok('archive', '--migrate')
        self.assertEqual(self.ok('show', first)['item']['id'], first)
        record = self.repo / 'notes/queue/history/items' / (first + '.json')
        original = json.loads(record.read_text())
        original['item']['title'] = 'conflicting'
        record.write_text(json.dumps(original))
        self.refused('show', first)

    def test_archived_release_authorization_and_revocation(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
        import release
        first = self.add('Release v8.9.1', (), 'release')
        self.authorize('next', instruction='I approve the 8.9.1 beta')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'completed')
        self.ok('archive', '--migrate')
        quote, source = release.queue_authorization(self.repo, started['cycle'], '8.9.1', 'beta')
        self.assertEqual(quote, 'I approve the 8.9.1 beta')
        self.assertEqual(source['item'], first)
        self.ok('revoke', '--reason', 'withdrawn')
        quote, reason = release.queue_authorization(self.repo, started['cycle'], '8.9.1', 'beta')
        self.assertIsNone(quote)
        self.assertIn('revoked', reason)

    def test_reader_exposes_more_than_fifty_unstarted_items(self):
        for n in range(55):
            self.add(f'Item {n}')
        queue = view(self.repo)['queue']
        self.assertTrue(queue['ok'], queue)
        self.assertEqual(len(queue['items']), 55)
        self.assertEqual(queue['items'][-1]['id'], 'Q-0055')

    def test_missing_history_dependency_refuses(self):
        first = self.add('first')
        self.add('second', (first,))
        self.authorize('queue')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'completed')
        self.ok('archive', '--migrate')
        (self.repo / 'notes/queue/history/items' / (first + '.json')).unlink()
        self.refused('list')

    def test_archived_abandoned_item_still_stops_authorized_queue(self):
        first = self.add('first')
        self.add('second', (first,))
        self.authorize('queue')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'abandoned')
        self.ok('archive', '--migrate')
        self.assertEqual(self.stop_reason(), 'previous-abandoned')

    def test_archive_frees_capacity_without_reusing_ids_and_refuses_collision(self):
        with patch.object(cycle_queue, 'MAX_ITEMS', 1):
            first = self.add('first')
            self.authorize('next')
            _, started = self.start()
            self.end_cycle(started['cycle'], 'completed')
            self.ok('archive', '--migrate')
            self.assertEqual(self.add('second'), 'Q-0002')
            self.ok('remove', 'Q-0002')
            doc = self.queue_doc()
            doc['next_number'] = 1
            cycle_queue.write_queue(cycle_queue.tree(self.repo), doc)
            result = self.refused('add', '--title', 'collision', '--outcome', 'o', '--type', 'quick-fix',
                                  '--scope', 'src', '--acceptance', 'works')
            self.assertIn('collides with history', result['error'])
            self.assertEqual(first, 'Q-0001')

    def test_add_sweeps_terminal_item_before_applying_capacity(self):
        with patch.object(cycle_queue, 'MAX_ITEMS', 1):
            first = self.add('first')
            self.authorize('next')
            _, started = self.start()
            self.ok('archive', '--migrate')
            self.end_cycle(started['cycle'], 'completed')
            second = self.add('second', (first,))
            self.assertEqual(second, 'Q-0002')
            self.assertEqual([item['id'] for item in self.queue_doc()['items']], [second])
            self.assertEqual(self.ok('show', first)['item']['id'], first)

    def test_invalid_add_does_not_write_preflight_archive(self):
        with patch.object(cycle_queue, 'MAX_ITEMS', 1):
            first = self.add('first')
            self.authorize('next')
            _, started = self.start()
            self.ok('archive', '--migrate')
            self.end_cycle(started['cycle'], 'completed')
            path = self.repo / 'notes/queue/cycles.yaml'
            before = path.read_bytes()
            self.refused('add', '--title', 'bad', '--outcome', 'o', '--type', 'quick-fix',
                         '--scope', '../outside', '--acceptance', 'works')
            self.refused('add', '--title', 'bad dependency', '--outcome', 'o', '--type', 'quick-fix',
                         '--scope', 'src', '--acceptance', 'works', '--depends-on', 'Q-9999')
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((self.repo / 'notes/queue/history/items' / (first + '.json')).exists())

    def test_start_next_stop_does_not_archive_pending_terminal_item(self):
        first = self.add('first')
        self.add('held', (), 'quick-fix', '--held', '--reason', 'waiting')
        self.authorize('queue')
        _, started = self.start()
        self.ok('archive', '--migrate')
        self.end_cycle(started['cycle'], 'completed')
        path = self.repo / 'notes/queue/cycles.yaml'
        before = path.read_bytes()
        self.assertEqual(self.stop_reason(), 'held')
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.repo / 'notes/queue/history/items' / (first + '.json')).exists())

    def test_archive_reads_valid_large_unicode_item(self):
        arguments = ['add', '--title', 'large', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src']
        for _ in range(40):
            arguments.extend(['--acceptance', 'é' * 2000])
        first = self.ok(*arguments)['item']['id']
        self.authorize('next')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'completed')
        self.ok('archive', '--migrate')
        self.assertEqual(len(self.ok('show', first)['item']['acceptance']), 40)

    def test_archive_refuses_oversized_record_before_removal(self):
        first = self.add('first')
        self.authorize('next')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'completed')
        with patch.object(cycle_queue, 'MAX_HISTORY_BYTES', 100):
            result = self.refused('archive', '--migrate')
        self.assertIn('exceeds', result['error'])
        self.assertEqual(self.queue_doc()['format_version'], 1)
        self.assertEqual(self.queue_doc()['items'][0]['id'], first)
        self.assertFalse((self.repo / 'notes/queue/history/items' / (first + '.json')).exists())

    def test_format2_is_rejected_by_the_format1_schema(self):
        self.add('waiting')
        self.ok('archive', '--migrate')
        from council_records import _validator
        schema = _validator().load_schema(Path(__file__).resolve().parents[2] / 'schemas/cycle-queue.schema.json')
        schema['properties']['format_version'] = {'const': 1}
        errors = []
        _validator().validate(self.queue_doc(), schema, '#', '#', errors, 'queue')
        self.assertTrue(any('format_version' in error['instance_path'] for error in errors), errors)

    def test_conflicting_valid_duplicate_refuses_replay(self):
        first = self.add('first')
        self.authorize('next')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'completed')
        with patch('cycle_queue.write_queue', side_effect=Crash):
            with self.assertRaises(Crash):
                cycle_queue.archive(self.repo, migrate=True)
        record = self.repo / 'notes/queue/history/items' / (first + '.json')
        data = json.loads(record.read_text())
        data['item']['title'] = 'another valid title'
        data['source_sha256'] = cycle_queue._item_digest(data['item'])
        record.write_text(json.dumps(data))
        self.assertIn('conflicting', self.refused('archive', '--migrate')['error'])

    def test_cycle_commit_cannot_split_archive_from_queue_removal(self):
        first = self.add('first')
        self.authorize('next')
        _, started = self.start()
        def git(*args):
            return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                                  text=True, capture_output=True).stdout.strip()
        git('init')
        git('config', 'user.name', 'Queue Test')
        git('config', 'user.email', 'queue@example.invalid')
        git('add', '.')
        git('commit', '-m', 'baseline')
        self.end_cycle(started['cycle'], 'completed')
        import cycle_commit
        cycle_commit.commit_record(self.repo, started['cycle'])
        with patch('cycle_queue.write_queue', side_effect=Crash):
            with self.assertRaises(Crash):
                cycle_queue.archive(self.repo, migrate=True)
        note = self.repo / 'notes/cycles' / started['cycle'] / 'note.md'
        note.write_text('unrelated cycle checkpoint\n')
        cycle_commit.commit_record(self.repo, started['cycle'])
        self.assertNotIn('notes/queue/', git('show', '--pretty=', '--name-only', 'HEAD'))
        self.ok('archive', '--migrate')
        changed = git('show', '--pretty=', '--name-only', 'HEAD').splitlines()
        self.assertIn('notes/queue/cycles.yaml', changed)
        self.assertIn(f'notes/queue/history/items/{first}.json', changed)
        self.assertEqual(self.ok('show', first)['item']['id'], first)

    def test_terminal_cycle_without_queue_item_does_not_commit_pending_queue(self):
        self.add('waiting')
        self.ok('archive', '--migrate')
        unrelated = create(self.repo, 'quick-fix', 'Other', 'Goal', ['src'], ['ok'], 'builder', 'tester')
        def git(*args):
            return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                                  text=True, capture_output=True).stdout.strip()
        git('init')
        git('config', 'user.name', 'Queue Test')
        git('config', 'user.email', 'queue@example.invalid')
        git('add', '.')
        git('commit', '-m', 'baseline')
        self.end_cycle(unrelated['id'], 'completed')
        queue = self.repo / 'notes/queue/cycles.yaml'
        queue.write_text(queue.read_text().replace('title: waiting', 'title: still waiting'))
        import cycle_commit
        result = cycle_commit.after_write(self.repo, unrelated['id'])
        self.assertEqual(result['queue_sweep']['items'], [])
        self.assertNotIn('notes/queue/', git('show', '--pretty=', '--name-only', 'HEAD'))
        self.assertIn('notes/queue/cycles.yaml', git('status', '--porcelain'))

    def test_deferred_archive_is_committed_with_history_by_next_queue_writer(self):
        first = self.add('first')
        second = self.add('second', (first,))
        self.authorize('queue')
        _, started = self.start()
        def git(*args):
            return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                                  text=True, capture_output=True).stdout.strip()
        git('init')
        git('config', 'user.name', 'Queue Test')
        git('config', 'user.email', 'queue@example.invalid')
        git('add', '.')
        git('commit', '-m', 'baseline')
        self.end_cycle(started['cycle'], 'completed')
        import cycle_commit
        cycle_commit.commit_record(self.repo, started['cycle'])
        with patch('cycle_commit.deferral', return_value=('full-suite-running', 'held')):
            result = self.ok('archive', '--migrate')
        self.assertEqual(result['queue_commit']['deferred'], 'full-suite-running')
        self.ok('hold', second, '--reason', 'test recovery')
        changed = git('show', '--pretty=', '--name-only', 'HEAD').splitlines()
        self.assertIn('notes/queue/cycles.yaml', changed)
        self.assertIn(f'notes/queue/history/items/{first}.json', changed)
        self.assertEqual(self.ok('show', first)['item']['id'], first)


class OrderingTests(Base):
    def test_ac1_add_reorder_hold_edit_and_remove_unstarted_items(self):
        a, b, c = self.add('A'), self.add('B'), self.add('C')
        self.assertEqual([a, b, c], ['Q-0001', 'Q-0002', 'Q-0003'])
        self.ok('move', c, '--position', '1')
        self.assertEqual([i['id'] for i in self.ok('list', '--full')['items']], [c, a, b])
        self.assertEqual([i['position'] for i in self.ok('list', '--full')['items']], [1, 2, 3])
        held = self.ok('hold', a, '--reason', 'waiting on the owner')['item']
        self.assertEqual((held['state'], held['hold_reason']), ('held', 'waiting on the owner'))
        self.assertEqual(self.ok('unhold', a)['item']['state'], 'pending')
        edited = self.ok('edit', a, '--title', 'A2', '--scope', 'src/a.py', '--acceptance', 'one', '--acceptance', 'two')['item']
        self.assertEqual((edited['title'], edited['scope'], edited['acceptance']), ('A2', ['src/a.py'], ['one', 'two']))
        self.ok('remove', b)
        self.assertEqual([i['id'] for i in self.ok('list', '--full')['items']], [c, a])
        # Ids are never reused, even after removal.
        self.assertEqual(self.add('D'), 'Q-0004')

    def test_ac1_add_position_and_held_flags(self):
        a = self.add('A')
        b = self.add('B', (), 'quick-fix', '--position', '1', '--held', '--reason', 'later')
        items = self.ok('list', '--full')['items']
        self.assertEqual([i['id'] for i in items], [b, a])
        self.assertEqual(items[0]['state'], 'held')
        self.refused('add', '--title', 'X', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a', '--held')
        self.refused('add', '--title', 'X', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a', '--reason', 'r')

    def test_ac1_values_the_cycle_would_refuse_are_refused_at_add_and_edit(self):
        base = ['add', '--title', 'X', '--outcome', 'o', '--type', 'quick-fix', '--acceptance', 'a']
        self.refused(*base, '--scope', '../outside')
        self.refused(*base, '--scope', '/abs/path')
        self.refused(*base, '--scope', ':(glob)src')
        self.refused('add', '--title', ' ', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a')
        self.refused('add', '--title', 'X', '--outcome', 'o', '--type', 'Bad Type', '--scope', 'src', '--acceptance', 'a')
        self.refused('add', '--title', 'x' * 201, '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a')
        a = self.add('A')
        self.refused('edit', a, '--scope', '../outside')
        self.refused('edit', a)  # nothing to change
        self.refused('edit', a, '--depends-on', a)  # self-reference
        self.assertEqual(self.item(a)['scope'], ['src'])

    def test_ac1_started_and_starting_items_are_immutable_and_fix_the_order(self):
        a, b = self.add('A'), self.add('B')
        self.authorize('queue')
        code, started = self.start()
        self.assertEqual((code, started['outcome']), (0, 'started'))
        for argv in (('edit', a, '--title', 'new'), ('hold', a, '--reason', 'r'), ('remove', a), ('move', a, '--position', '2')):
            self.refused(*argv)
        # An unstarted item may not move ahead of a started one.
        self.refused('move', b, '--position', '1')
        self.refused('add', '--title', 'X', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a', '--position', '1')
        self.assertEqual(self.add('C', (), 'quick-fix', '--position', '2'), 'Q-0003')
        self.assertEqual([i['id'] for i in self.ok('list', '--full')['items']], [a, 'Q-0003', b])

    def test_ac1_dependency_must_precede_its_dependent(self):
        a, b = self.add('A'), self.add('B')
        c = self.add('C', (a,))
        self.refused('move', c, '--position', '1')  # would precede its dependency
        self.refused('move', a, '--position', '3')  # would follow its dependent
        self.refused('edit', a, '--depends-on', c)  # dependency after dependent / cycle
        self.refused('add', '--title', 'X', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a', '--depends-on', 'Q-0099')
        self.ok('move', c, '--position', '2')
        self.assertEqual([i['id'] for i in self.ok('list', '--full')['items']], [a, c, b])
        self.refused('remove', a)  # c depends on it
        self.ok('edit', c, '--no-depends')
        self.ok('remove', a)

    def test_hold_and_unhold_refuse_the_wrong_state(self):
        a = self.add('A')
        self.refused('unhold', a)
        self.ok('hold', a, '--reason', 'r')
        self.refused('hold', a, '--reason', 'again')
        self.refused('show', 'Q-0042')
        self.refused('show', 'not-an-id')


class AuthorizationTests(Base):
    def test_authorization_records_the_owner_words_and_captures_ids(self):
        a, b, c = self.add('A'), self.add('B'), self.add('C')
        record = self.authorize('next-n', 2, instruction="run the next 2 items, it's ok")['authorization']
        self.assertEqual((record['kind'], record['count'], record['scope'], record['started'], record['date']), ('next-n', 2, [a, b], [], DATE))
        self.assertEqual(record['instruction'], "run the next 2 items, it's ok")
        self.assertEqual(self.queue_doc()['authorization']['instruction'], "run the next 2 items, it's ok")
        again = self.authorize('queue')['authorization']
        self.assertEqual(again['scope'], [a, b, c])
        doc = self.queue_doc()
        self.assertEqual([h['ended'] for h in doc['authorization_history']], ['superseded'])
        self.ok('revoke', '--reason', 'owner paused the queue')
        doc = self.queue_doc()
        self.assertIsNone(doc['authorization'])
        self.assertEqual([h['ended'] for h in doc['authorization_history']], ['superseded', 'revoked'])
        self.assertEqual(doc['authorization_history'][1]['reason'], 'owner paused the queue')
        self.refused('revoke', '--reason', 'nothing to revoke')

    def test_authorize_refuses_bad_input(self):
        self.refused('authorize', '--kind', 'next', '--instruction', 'go', '--date', DATE)  # empty capture
        self.add('A')
        self.refused('authorize', '--kind', 'next', '--instruction', ' ', '--date', DATE)
        self.refused('authorize', '--kind', 'next', '--instruction', 'go', '--date', '19-10-2026')
        self.refused('authorize', '--kind', 'next-n', '--instruction', 'go', '--date', DATE)
        self.refused('authorize', '--kind', 'next-n', '--count', '0', '--instruction', 'go', '--date', DATE)
        self.refused('authorize', '--kind', 'next', '--count', '2', '--instruction', 'go', '--date', DATE)
        self.assertIsNone(self.ok('list', '--full')['authorization'])


class StartNextTests(Base):
    def test_a_started_cycle_is_a_version_three_record(self):
        self.add('A')
        self.authorize('queue')
        code, got = self.start()
        self.assertEqual(code, 0, got)
        doc = load(self.repo, got['cycle'])
        self.assertEqual((doc['schema_version'], doc['revision'], doc['history'][0]['revision']), (3, 1, 1))
        self.assertEqual(self.item(got['item'])['state'], 'started')
        # The queue readers accept the version-3 record: a second start reports the open cycle.
        code, again = self.start()
        self.assertEqual((code, again['outcome']), (0, 'in-progress'))

    def test_ac2_a_dependency_prevents_premature_start(self):
        a = self.add('A')
        b = self.add('B', (a,))
        self.authorize('queue')
        self.ok('hold', a, '--reason', 'not yet')
        self.assertEqual(self.stop_reason(), 'held')
        self.assertEqual(self.item(b)['state'], 'pending')
        self.ok('unhold', a)
        code, got = self.start()
        self.assertEqual((code, got['item']), (0, a))
        # B stays unstarted while A is open, whatever the reason reported.
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['item']), (0, 'in-progress', a))
        self.end_cycle(got['cycle'], 'paused')
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['status']), (0, 'in-progress', 'paused'))
        self.assertEqual(self.item(b)['state'], 'pending')
        self.assertEqual(len(self.cycle_dirs()), 1)
        view_b = self.item(b)
        self.assertEqual([(d['id'], d['satisfied']) for d in view_b['dependencies']], [(a, False)])

    def test_ac2_a_completed_dependency_releases_the_dependent(self):
        a = self.add('A')
        b = self.add('B', (a,))
        self.authorize('queue')
        _, first = self.start()
        self.end_cycle(first['cycle'], 'completed')
        self.assertTrue(self.item(b)['dependencies'][0]['satisfied'])
        code, second = self.start()
        self.assertEqual((code, second['outcome'], second['item']), (0, 'started', b))

    def test_ac2_an_abandoned_dependency_stops_with_its_own_reason(self):
        a = self.add('A')
        b = self.add('B', (a,))
        self.authorize('queue')
        _, first = self.start()
        self.end_cycle(first['cycle'], 'abandoned')
        # The abandoned cycle stops the authorized run (council note: this check comes first).
        self.assertEqual(self.stop_reason(), 'previous-abandoned')
        # A fresh authorization excludes the abandoned item; the dependent still waits for an owner decision.
        self.authorize('next')
        self.assertEqual(self.stop_reason(), 'dependency-abandoned')
        self.assertEqual(self.item(b)['state'], 'pending')
        self.assertEqual(len(self.cycle_dirs()), 1)
        self.ok('edit', b, '--no-depends')
        self.assertEqual(self.start()[1]['item'], b)

    def test_a_shortcut_cycle_is_terminal_and_the_authorized_queue_continues(self):
        a, b = self.add('A'), self.add('B')
        self.authorize('next-n', 2)
        _, first = self.start()
        self.end_cycle(first['cycle'], 'shortcut')
        code, second = self.start()  # no previous-abandoned stop: a shortcut is not an abandonment
        self.assertEqual((code, second['outcome'], second['item']), (0, 'started', b))
        self.assertEqual(self.item(a)['cycle_status'], 'shortcut')

    def test_a_shortcut_cycle_item_is_archived_like_a_completed_one(self):
        a = self.add('A')
        self.authorize('queue')
        _, started = self.start()
        self.end_cycle(started['cycle'], 'shortcut')
        self.ok('archive', '--migrate')
        self.assertNotIn(a, [i['id'] for i in self.queue_doc()['items']])
        self.assertTrue((self.repo / 'notes/queue/history/items' / (a + '.json')).exists())

    def test_an_open_cycle_is_never_archived_the_positive_control(self):
        a = self.add('A')
        self.authorize('queue')
        self.start()
        self.ok('archive', '--migrate')
        self.assertIn(a, [i['id'] for i in self.queue_doc()['items']])

    def test_a_dependency_on_a_shortcut_cycle_stops_blocked_with_the_shortcut_text(self):
        a = self.add('A')
        b = self.add('B', (a,))
        self.authorize('queue')
        _, first = self.start()
        self.end_cycle(first['cycle'], 'shortcut')
        code, payload = self.start()
        self.assertEqual((code, payload['stop']['reason']), (1, 'blocked'))
        self.assertIn('shortcut', payload['stop']['detail'])
        self.assertIn(a, payload['stop']['detail'])
        self.assertFalse(self.item(b)['dependencies'][0]['satisfied'])
        self.assertEqual(self.item(b)['state'], 'pending')
        self.assertEqual(len(self.cycle_dirs()), 1)
        self.ok('edit', b, '--no-depends')  # the owner's repair
        self.assertEqual(self.start()[1]['item'], b)

    def test_a_dependency_stopped_by_an_active_cycle_carries_no_shortcut_text(self):
        a = self.add('A')
        self.add('B', (a,))
        self.authorize('queue')
        self.start()
        code, payload = self.start()  # the open cycle reports in-progress, not a blocked stop
        self.assertEqual(code, 0)
        self.assertEqual(payload['outcome'], 'in-progress')

    def test_ac3_one_authorized_item_completes_without_starting_another(self):
        a, b = self.add('A'), self.add('B')
        self.authorize('next')
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['item'], got['status']), (0, 'started', a, 'active'))
        self.end_cycle(got['cycle'], 'completed')
        self.assertEqual(self.stop_reason(), 'authorization-exhausted')
        self.assertEqual(self.item(b)['state'], 'pending')
        self.assertEqual(len(self.cycle_dirs()), 1)

    def test_ac4_an_authorized_two_item_run_continues_after_the_first_completes(self):
        a, b = self.add('A'), self.add('B')
        self.authorize('next-n', 2)
        _, first = self.start()
        self.assertEqual(first['item'], a)
        self.end_cycle(first['cycle'], 'completed')
        code, second = self.start()
        self.assertEqual((code, second['outcome'], second['item']), (0, 'started', b))
        self.assertNotEqual(first['cycle'], second['cycle'])
        self.end_cycle(second['cycle'], 'completed')
        # A third item added after authorization stays unstarted.
        c = self.add('C')
        self.assertEqual(self.stop_reason(), 'authorization-exhausted')
        self.assertEqual(self.item(c)['state'], 'pending')
        self.assertEqual(len(self.cycle_dirs()), 2)

    def test_ac5_newly_added_items_stay_outside_existing_authorization(self):
        a = self.add('A')
        self.authorize('next')
        early = self.add('Early', (), 'quick-fix', '--position', '1')
        late = self.add('Late')
        self.assertFalse(self.item(late)['in_scope'])
        self.assertTrue(self.item(a)['in_scope'])
        self.assertEqual(self.stop_reason(), 'outside-authorization')
        self.assertEqual(self.item(early)['state'], 'pending')
        self.assertEqual(self.cycle_dirs(), [])
        # Editing a captured item keeps it under the authorization (ids, not content).
        self.ok('move', early, '--position', '2')
        self.ok('edit', a, '--title', 'Renamed')
        code, got = self.start()
        self.assertEqual((code, got['item']), (0, a))

    def test_ac5_unauthorized_queue_never_starts(self):
        self.add('A')
        self.assertEqual(self.stop_reason(), 'not-authorized')
        self.assertEqual(self.cycle_dirs(), [])
        self.authorize('next')
        self.ok('revoke', '--reason', 'pause')
        self.assertEqual(self.stop_reason(), 'not-authorized')

    def test_empty_queue_and_held_head_stop(self):
        self.assertEqual(self.stop_reason(), 'queue-empty')
        a, b = self.add('A'), self.add('B')
        self.ok('hold', a, '--reason', 'owner wants to review')
        self.authorize('queue')
        code, got = self.start()
        self.assertEqual((code, got['stop']['reason'], got['stop']['item']), (1, 'held', a))
        self.assertEqual(self.item(b)['state'], 'pending')  # never skipped
        self.assertEqual(self.cycle_dirs(), [])

    def test_ac6_a_blocker_stops_the_queue(self):
        a, b = self.add('A'), self.add('B')
        self.authorize('queue')
        _, first = self.start()
        self.end_cycle(first['cycle'], 'paused')
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['status']), (0, 'in-progress', 'paused'))
        self.end_cycle(first['cycle'], 'abandoned')
        self.assertEqual(self.stop_reason(), 'previous-abandoned')
        self.assertEqual(self.item(b)['state'], 'pending')
        self.assertEqual(len(self.cycle_dirs()), 1)

    def test_ac6_a_missing_cycle_record_stops_even_for_an_independent_next_item(self):
        a, b = self.add('A'), self.add('B')  # B has no dependency
        self.authorize('queue')
        _, first = self.start()
        (self.repo / 'notes/cycles' / first['cycle'] / 'cycle.json').unlink()
        code, got = self.start()
        self.assertEqual((code, got['stop']['reason'], got['stop']['item']), (1, 'cycle-missing', a))
        self.assertEqual(self.item(a)['cycle_status'], 'missing')
        self.assertEqual(self.item(b)['state'], 'pending')
        self.assertEqual(len(self.cycle_dirs()), 1)

    def test_a_type_without_phases_stops_with_type_unsupported(self):
        a = self.add('A', (), 'spike')
        self.authorize('queue')
        self.assertEqual(self.stop_reason(), 'type-unsupported')
        self.assertEqual(self.item(a)['state'], 'pending')
        self.assertEqual(self.cycle_dirs(), [])
        self.ok('edit', a, '--type', 'dev')
        self.assertEqual(self.start()[1]['outcome'], 'started')

    def test_started_cycle_carries_the_item_scope_and_origin(self):
        a = self.add('A', (), 'dev')
        self.authorize('next')
        _, got = self.start()
        doc = load(self.repo, got['cycle'])
        self.assertEqual((doc['type'], doc['title'], doc['goal'], doc['plan']['scope'], doc['plan']['acceptance']), ('dev', 'A', 'Deliver A', ['src'], ['it works']))
        self.assertEqual(doc['implementers'], ['dev-lead'])
        self.assertEqual(doc['coordinator'], 'dev-lead')
        created = doc['history'][0]
        self.assertEqual(created['action'], 'created')
        token = self.queue_doc()['items'][0]['start_token']
        self.assertEqual(created['queue'], {'item': a, 'token': token})
        code, other = self.cli('start-next', '--implementer', 'x', '--coordinator', 'y')
        self.assertEqual(other['outcome'], 'in-progress')

    def test_implementer_and_coordinator_flags_reach_the_cycle(self):
        self.add('A')
        self.authorize('next')
        _, got = self.cli('start-next', '--implementer', 'impl', '--coordinator', 'coord')
        doc = load(self.repo, got['cycle'])
        self.assertEqual((doc['implementers'], doc['coordinator']), (['impl'], 'coord'))

    def test_ac8_repeated_start_requests_allocate_no_duplicate_cycle(self):
        self.add('A')
        self.add('B')
        self.authorize('queue')
        _, first = self.start()
        for _ in range(3):
            code, again = self.start()
            self.assertEqual((code, again['outcome'], again['cycle']), (0, 'in-progress', first['cycle']))
        self.assertEqual(self.cycle_dirs(), [first['cycle']])

    def test_ac8_concurrent_start_requests_start_exactly_one_cycle(self):
        self.add('A')
        self.add('B')
        self.authorize('queue')
        results = []

        def run():
            results.append(cycle_queue.start_next(self.repo))

        threads = [threading.Thread(target=run) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
            self.assertFalse(t.is_alive())
        self.assertEqual(sorted(r['outcome'] for r in results), ['in-progress'] * 3 + ['started'])
        self.assertEqual(len(self.cycle_dirs()), 1)

    def test_lock_order_queue_lock_is_held_while_create_takes_the_cycles_lock(self):
        self.add('A')
        self.authorize('next')
        seen = {}
        real = cycle_queue.create

        def spy(*args, **kwargs):
            import fcntl
            with open(self.repo / 'notes/queue/.lock', 'a') as probe:
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    seen['queue_lock_held'] = False
                except BlockingIOError:
                    seen['queue_lock_held'] = True
            return real(*args, **kwargs)

        done = []
        with patch.object(cycle_queue, 'create', spy):
            t = threading.Thread(target=lambda: done.append(cycle_queue.start_next(self.repo)))
            t.start()
            t.join(30)
        self.assertFalse(t.is_alive(), 'start-next deadlocked')
        self.assertTrue(seen['queue_lock_held'])
        self.assertEqual(done[0]['outcome'], 'started')
        # Cycle mutations never take the queue lock: one works while the queue lock is held elsewhere.
        import fcntl
        from cycle_workflow import mutate
        with open(self.repo / 'notes/queue/.lock', 'a') as holder:
            fcntl.flock(holder, fcntl.LOCK_EX)
            finished = []
            t = threading.Thread(target=lambda: finished.append(mutate(self.repo, done[0]['cycle'], 'pause', reason='r')))
            t.start()
            t.join(30)
            self.assertFalse(t.is_alive(), 'a cycle mutation waited for the queue lock')


class RecoveryTests(Base):
    def setUp(self):
        super().setUp()
        self.a = self.add('A')
        self.b = self.add('B')
        self.authorize('queue')

    def test_ac7_interruption_after_create_before_the_queue_write_is_adopted(self):
        real_write = cycle_queue.write_queue
        calls = []

        def crash_on_second(cfg, doc):
            calls.append(1)
            if len(calls) == 2:  # the intent write succeeded; the started write dies
                raise Crash()
            return real_write(cfg, doc)

        with patch.object(cycle_queue, 'write_queue', crash_on_second):
            with self.assertRaises(Crash):
                cycle_queue.start_next(self.repo)
        self.assertEqual(len(self.cycle_dirs()), 1)
        self.assertEqual(self.item(self.a)['state'], 'starting')
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['item'], got['cycle'], got['status']), (0, 'adopted', self.a, self.cycle_dirs()[0], 'active'))
        self.assertEqual(len(self.cycle_dirs()), 1)  # no second allocation
        after = self.queue_doc()
        self.assertEqual(after['items'][0]['state'], 'started')
        self.assertEqual(after['authorization']['started'], [self.a])
        self.assertEqual(self.start()[1]['outcome'], 'in-progress')

    def test_ac7_create_raising_after_the_cycle_was_written_adopts_it(self):
        real = cycle_queue.create

        def write_then_fail(*args, **kwargs):
            real(*args, **kwargs)
            raise OSError('disk went away after the record landed')

        with patch.object(cycle_queue, 'create', write_then_fail):
            code, got = self.start()
        self.assertEqual((code, got['outcome']), (0, 'adopted'))
        self.assertEqual(len(self.cycle_dirs()), 1)
        self.assertEqual(self.item(self.a)['state'], 'started')

    def test_a_failed_create_with_no_record_restores_pending_and_refuses(self):
        with patch.object(cycle_queue, 'create', side_effect=ValueError('nope')):
            code, got = self.start()
        self.assertEqual(code, 1)
        self.assertIn('nope', got['error'])
        item = self.item(self.a)
        self.assertEqual(item['state'], 'pending')
        self.assertIsNone(self.queue_doc()['items'][0]['start_token'])
        self.assertEqual(self.cycle_dirs(), [])
        self.assertEqual(self.start()[1]['outcome'], 'started')

    def test_interruption_after_intent_before_create_then_revoke_cancels_the_intent(self):
        with patch.object(cycle_queue, 'create', side_effect=Crash()):
            with self.assertRaises(Crash):
                cycle_queue.start_next(self.repo)
        self.assertEqual(self.item(self.a)['state'], 'starting')
        self.assertEqual(self.cycle_dirs(), [])
        self.ok('revoke', '--reason', 'owner paused')
        code, got = self.start()
        self.assertEqual((code, got['stop']['reason']), (1, 'not-authorized'))
        self.assertEqual(self.item(self.a)['state'], 'pending')  # unfulfilled intent cancelled
        self.assertIsNone(self.queue_doc()['items'][0]['start_token'])
        self.assertEqual(self.cycle_dirs(), [])

    def test_interruption_before_create_then_fresh_next_authorization_starts_one_cycle(self):
        with patch.object(cycle_queue, 'create', side_effect=Crash()):
            with self.assertRaises(Crash):
                cycle_queue.start_next(self.repo)
        # The authorization still holds the starting item in scope, so a stranded intent cannot start outside it.
        self.authorize('next')
        self.assertEqual(self.ok('list', '--full')['authorization']['scope'], [self.a])
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['item']), (0, 'started', self.a))
        self.assertEqual(len(self.cycle_dirs()), 1)
        self.end_cycle(got['cycle'], 'completed')
        self.assertEqual(self.stop_reason(), 'authorization-exhausted')

    def test_unreadable_cycle_record_during_adoption_refuses_and_keeps_the_intent(self):
        with patch.object(cycle_queue, 'create', side_effect=Crash()):
            with self.assertRaises(Crash):
                cycle_queue.start_next(self.repo)
        broken = self.repo / 'notes/cycles/CYC-0900'
        broken.mkdir(parents=True)
        (broken / 'cycle.json').write_text('{not json')
        code, got = self.start()
        self.assertEqual(code, 1)
        self.assertIn('CYC-0900', got['error'])
        self.assertEqual(self.item(self.a)['state'], 'starting')
        self.assertEqual(self.cycle_dirs(), ['CYC-0900'])
        # A directory without cycle.json is a burned id and does not block adoption.
        (broken / 'cycle.json').unlink()
        code, got = self.start()
        self.assertEqual((code, got['outcome']), (0, 'started'))

    def test_unreadable_record_when_create_fails_keeps_the_intent_and_allocates_nothing(self):
        broken = self.repo / 'notes/cycles/CYC-0900'
        broken.mkdir(parents=True)
        (broken / 'cycle.json').write_text('[]')
        with patch.object(cycle_queue, 'create', side_effect=ValueError('boom')):
            code, got = self.start()
        self.assertEqual(code, 1)
        self.assertIn('CYC-0900', got['error'])
        self.assertEqual(self.item(self.a)['state'], 'starting')
        self.assertEqual(self.cycle_dirs(), ['CYC-0900'])

    def test_adoption_matches_the_token_not_the_title(self):
        # An unrelated cycle with the same title and an unrelated queue token must not be adopted.
        create(self.repo, 'quick-fix', 'A', 'Deliver A', ['src'], ['it works'], 'dev-lead', 'dev-lead', origin={'item': self.a, 'token': 'f' * 32})
        create(self.repo, 'quick-fix', 'A', 'Deliver A', ['src'], ['it works'], 'dev-lead', 'dev-lead')
        with patch.object(cycle_queue, 'create', side_effect=Crash()):
            with self.assertRaises(Crash):
                cycle_queue.start_next(self.repo)
        self.assertEqual(len(self.cycle_dirs()), 2)
        self.revoke_and_reauthorize_then_start_creates_third()

    def revoke_and_reauthorize_then_start_creates_third(self):
        code, got = self.start()  # no cycle carries the token: intent cancelled, a fresh start follows
        self.assertEqual((code, got['outcome']), (0, 'started'))
        self.assertEqual(len(self.cycle_dirs()), 3)

    def test_two_cycles_carrying_one_token_refuse_adoption(self):
        with patch.object(cycle_queue, 'create', side_effect=Crash()):
            with self.assertRaises(Crash):
                cycle_queue.start_next(self.repo)
        token = self.queue_doc()['items'][0]['start_token']
        for _ in range(2):
            create(self.repo, 'quick-fix', 'A', 'Deliver A', ['src'], ['it works'], 'dev-lead', 'dev-lead', origin={'item': self.a, 'token': token})
        code, got = self.start()
        self.assertEqual(code, 1)
        self.assertIn('CYC-0001', got['error'])
        self.assertIn('CYC-0002', got['error'])
        self.assertEqual(self.item(self.a)['state'], 'starting')

    def test_adoption_of_a_completed_cycle_reports_it_and_the_next_start_continues(self):
        real_write = cycle_queue.write_queue
        calls = []

        def crash_on_second(cfg, doc):
            calls.append(1)
            if len(calls) == 2:
                raise Crash()
            return real_write(cfg, doc)

        with patch.object(cycle_queue, 'write_queue', crash_on_second):
            with self.assertRaises(Crash):
                cycle_queue.start_next(self.repo)
        self.end_cycle(self.cycle_dirs()[0], 'completed')
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['status']), (0, 'adopted', 'completed'))
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['item']), (0, 'started', self.b))

    def test_ac7_resume_preserves_authorization_and_creates_no_duplicate(self):
        _, first = self.start()
        before = self.ok('list', '--full')
        # A fresh process (a new CLI call) sees the same authorization and the same cycle.
        after = self.ok('list', '--full')
        self.assertEqual(before['authorization'], after['authorization'])
        self.assertEqual(after['authorization']['remaining'], [self.b])
        self.assertEqual(after['authorization']['started'], [self.a])
        code, got = self.start()
        self.assertEqual((code, got['outcome'], got['cycle']), (0, 'in-progress', first['cycle']))
        self.assertEqual(self.cycle_dirs(), [first['cycle']])
        self.end_cycle(first['cycle'], 'completed')
        self.assertEqual(self.start()[1]['item'], self.b)


class ReadTests(Base):
    def test_list_reports_state_status_dependencies_authorization_and_next(self):
        a = self.add('A')
        b = self.add('B', (a,))
        listing = self.ok('list', '--full')
        self.assertIsNone(listing['authorization'])
        self.assertEqual(listing['next'], {'item': a, 'startable': False, 'stop': 'not-authorized', 'detail': listing['next']['detail']})
        self.authorize('queue')
        listing = self.ok('list', '--full')
        self.assertEqual(listing['next']['item'], a)
        self.assertTrue(listing['next']['startable'])
        self.assertEqual(listing['authorization']['remaining'], [a, b])
        self.assertEqual(listing['authorization']['kind'], 'queue')
        row = listing['items'][1]
        self.assertEqual((row['position'], row['id'], row['state'], row['cycle'], row['in_scope']), (2, b, 'pending', None, True))
        self.assertEqual(row['dependencies'], [{'id': a, 'state': 'pending', 'cycle_status': None, 'satisfied': False}])

    def test_ac9_queue_and_cycle_views_report_consistent_state(self):
        a, b = self.add('A'), self.add('B')
        self.authorize('queue')
        _, got = self.start()
        for status in ('active', 'paused', 'completed', 'abandoned'):
            if status != 'active':
                self.end_cycle(got['cycle'], status)
            row = self.item(a)
            self.assertEqual((row['state'], row['cycle'], row['cycle_status']), ('started', got['cycle'], status))
            cycle_json = json.loads((self.repo / 'notes/cycles' / got['cycle'] / 'cycle.json').read_text())
            self.assertEqual(row['cycle_status'], cycle_json['status'])
            document = view(self.repo)
            self.assertEqual(document['cycles'][0]['status'], status)
            text = render(document)
            self.assertIn('Queued requests', text)
            self.assertIn(f'{a} {status}', text)
            self.assertIn(got['cycle'], text.split('Queued requests')[1])
            self.assertIn(f'{b} pending', text)

    def test_visualizer_shows_nothing_for_an_absent_queue_and_one_line_for_an_invalid_one(self):
        create(self.repo, 'quick-fix', 'Fix', 'Goal', ['src'], ['ok'], 'builder', 'tester')
        self.assertNotIn('Queued', render(view(self.repo)))
        (self.repo / 'notes/queue').mkdir()
        (self.repo / 'notes/queue/cycles.yaml').write_text('format: wrong\n')
        text = render(view(self.repo))
        self.assertEqual(sum(1 for line in text.splitlines() if line.startswith('Queued requests unavailable')), 1)
        self.assertIn('CYC-0001', text)  # the cycle view survives
        self.assertNotIn('format: wrong', text)
        document = view(self.repo)
        self.assertEqual(document['format_version'], 5)

    def test_visualizer_reports_missing_pyyaml_without_crashing_the_cycle_view(self):
        self.add('A')
        create(self.repo, 'quick-fix', 'Fix', 'Goal', ['src'], ['ok'], 'builder', 'tester')
        real_yaml = sys.modules['yaml']
        import cycle_progress
        original = cycle_progress.queue_lines

        def without_yaml(*args, **kwargs):
            with patch.dict(sys.modules, {'yaml': None}):
                return original(*args, **kwargs)

        with patch.object(cycle_progress, 'queue_lines', without_yaml):
            text = render(view(self.repo))
        self.assertIs(sys.modules['yaml'], real_yaml)
        self.assertIn('Queued requests unavailable', text)
        self.assertIn('CYC-0001', text)

    def test_cycle_progress_json_key_set_is_unchanged_for_a_queue_started_cycle(self):
        self.add('A')
        self.authorize('next')
        _, got = self.start()
        queue_cycle = view(self.repo, got['cycle'])
        plain = create(self.repo, 'quick-fix', 'Plain', 'Goal', ['src'], ['ok'], 'builder', 'tester')
        plain_cycle = view(self.repo, plain['id'])
        self.assertEqual(set(queue_cycle), set(plain_cycle))
        self.assertEqual(set(queue_cycle['cycles'][0]), set(plain_cycle['cycles'][0]))
        self.assertEqual(set(queue_cycle), {'format', 'format_version', 'ok', 'docs_dir', 'now_s', 'cycles', 'queue'})
        self.assertIsNone(queue_cycle['queue'])  # an explicit identity carries no queue
        listing = view(self.repo)
        self.assertEqual(set(listing), {'format', 'format_version', 'ok', 'docs_dir', 'now_s', 'cycles', 'queue'})
        self.assertTrue(listing['queue']['ok'])
        self.assertEqual(json.loads(json.dumps(listing))['format_version'], 5)


class StorageTests(Base):
    def test_file_lives_under_the_configured_docs_dir_with_fixed_key_order(self):
        self.add('A')
        path = self.repo / 'notes/queue/cycles.yaml'
        self.assertTrue(path.is_file())
        self.assertFalse((self.repo / 'bionic').exists())
        doc = self.queue_doc()
        self.assertEqual(list(doc), ['format', 'format_version', 'next_number', 'items', 'authorization', 'authorization_history'])
        self.assertEqual((doc['format'], doc['format_version'], doc['next_number']), ('crux.cycle-queue', 1, 2))
        self.assertEqual(list(doc['items'][0]), ['id', 'title', 'outcome', 'suggested_type', 'scope', 'acceptance', 'depends_on', 'state', 'hold_reason', 'start_token', 'cycle', 'added_at', 'started_at'])
        self.assertFalse(list((self.repo / 'notes/queue').glob('.cycle-*')))

    def test_an_absent_file_is_an_empty_queue_and_reads_create_nothing(self):
        listing = self.ok('list', '--full')
        self.assertEqual((listing['items'], listing['authorization'], listing['next']['stop']), ([], None, 'queue-empty'))
        self.assertFalse((self.repo / 'notes/queue').exists())

    def test_an_invalid_queue_file_is_refused_with_path_location_and_repair(self):
        self.add('A')
        path = self.repo / 'notes/queue/cycles.yaml'
        doc = self.queue_doc()
        doc['items'][0]['state'] = 'bogus'
        import yaml
        path.write_text(yaml.safe_dump(doc))
        for argv in (('list',), ('add', '--title', 'x', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a'), ('start-next',)):
            got = self.refused(*argv)
            self.assertIn('queue/cycles.yaml', got['error'])
            self.assertIn('/items/0/state', got['error'])
            self.assertIn('restore it from git', got['error'])
        path.write_text('items: [unclosed')
        self.assertIn('queue/cycles.yaml', self.refused('list')['error'])

    def test_read_time_cross_checks_refuse_a_hand_edited_queue(self):
        import yaml
        a = self.add('A')
        b = self.add('B', (a,))
        path = self.repo / 'notes/queue/cycles.yaml'
        good = self.queue_doc()

        def broken(edit):
            doc = json.loads(json.dumps(good))
            edit(doc)
            path.write_text(yaml.safe_dump(doc, sort_keys=False))
            return self.refused('list')['error']

        self.assertIn('unique', broken(lambda d: d['items'][1].update(id=a)))
        self.assertIn('next_number', broken(lambda d: d.update(next_number=2)))
        self.assertIn('exist', broken(lambda d: d['items'][1].update(depends_on=['Q-0077'])))
        self.assertIn('precede', broken(lambda d: d['items'].reverse()))
        self.assertIn('start_token', broken(lambda d: d['items'][0].update(state='starting')))
        self.assertIn('cycle', broken(lambda d: d['items'][0].update(state='started', start_token='a' * 32, cycle='nope', started_at='x')))
        self.assertIn('cycle', broken(lambda d: d['items'][0].update(cycle='CYC-0001')))

        def started_after_unstarted(d):
            d['items'][1].update(state='started', start_token='b' * 32, cycle='CYC-0001', started_at='x')
            d['items'][1]['depends_on'] = []

        self.assertIn('unstarted', broken(started_after_unstarted))
        self.assertIn('scope', broken(lambda d: d.update(authorization={'instruction': 'go', 'kind': 'next', 'count': 1, 'scope': [a], 'started': [b], 'authorized_at': 'x', 'date': DATE})))
        self.assertIn('itself', broken(lambda d: d['items'][1].update(depends_on=[b])))
        path.write_text(yaml.safe_dump(good, sort_keys=False))
        self.ok('list', '--full')

    def test_missing_tree_unconfigured_repo_and_missing_pyyaml_exit_2(self):
        (self.repo / 'notes/manifest.yml').unlink()
        self.assertIn('error', self.refused('list', code=2))
        (self.repo / 'notes/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.add('A')
        with patch.dict(sys.modules, {'yaml': None}):
            got = self.refused('list', code=2)
        self.assertIn('PyYAML', got['error'])

    def test_unwritable_queue_path_exits_2(self):
        (self.repo / 'notes/queue').write_text('a file where the directory belongs')
        self.refused('add', '--title', 'x', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a', code=2)

    def test_item_cap_counts_every_item(self):
        with patch.object(cycle_queue, 'MAX_ITEMS', 2):
            self.add('A')
            self.add('B')
            self.refused('add', '--title', 'C', '--outcome', 'o', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'a')

    def test_existing_subcommands_keep_their_exit_mapping(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'show', 'CYC-0042'])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out.getvalue())['ok'])
        os.remove(self.repo / 'notes/manifest.yml')
        out = io.StringIO()
        with redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'show', 'CYC-0001'])
        self.assertEqual(code, 1)  # a missing tree keeps exit 1 outside the queue group

    def test_non_compact_output_is_indented_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'queue', 'list'])
        self.assertEqual(code, 0)
        self.assertIn('\n  "ok": true', out.getvalue())


class ReferenceTests(Base):
    BASE = ['add', '--title', 'R', '--outcome', 'Deliver R', '--type', 'quick-fix', '--scope', 'src', '--acceptance', 'ok']

    def setUp(self):
        super().setUp()
        (self.repo / 'notes/brief.md').write_text('# brief\n')
        (self.repo / 'notes/extra.md').write_text('# extra\n')

    def add_ref(self, *refs):
        argv = list(self.BASE)
        for ref in refs:
            argv += ['--reference', ref]
        return self.ok(*argv)['item']

    def test_add_stores_references_and_list_and_show_display_them(self):
        item = self.add_ref('notes/brief.md', 'notes/extra.md')
        self.assertEqual(item['references'], ['notes/brief.md', 'notes/extra.md'])
        self.assertEqual(self.item(item['id'])['references'], ['notes/brief.md', 'notes/extra.md'])
        self.assertEqual(self.ok('show', item['id'])['item']['references'], ['notes/brief.md', 'notes/extra.md'])
        self.assertEqual(self.queue_doc()['items'][0]['references'], ['notes/brief.md', 'notes/extra.md'])

    def test_a_directory_is_a_valid_reference(self):
        self.assertEqual(self.add_ref('notes')['references'], ['notes'])

    def test_item_without_references_shows_an_empty_list_and_stores_no_key(self):
        qid = self.add('Plain')
        self.assertEqual(self.item(qid)['references'], [])
        self.assertNotIn('references', self.queue_doc()['items'][0])

    def test_edit_replaces_the_list_and_no_references_clears_it(self):
        qid = self.add_ref('notes/brief.md')['id']
        self.assertEqual(self.ok('edit', qid, '--reference', 'notes/extra.md')['item']['references'], ['notes/extra.md'])
        self.assertEqual(self.ok('edit', qid, '--no-references')['item']['references'], [])
        self.assertNotIn('references', self.queue_doc()['items'][0])
        self.refused('edit', qid, '--reference', 'notes/brief.md', '--no-references')

    def test_edit_of_a_started_item_is_refused(self):
        qid = self.add_ref('notes/brief.md')['id']
        self.authorize('queue')
        self.start()
        self.refused('edit', qid, '--reference', 'notes/extra.md')

    def test_unusable_references_are_refused_at_add_and_edit(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / 'secret.md').write_text('x')
        (self.repo / 'escape').symlink_to(outside.name)
        (self.repo / 'filelink').symlink_to(Path(outside.name) / 'secret.md')
        qid = self.add('Plain')
        bad = ['notes/missing.md', '../outside.md', 'notes/../../x', str(Path(outside.name) / 'secret.md'), 'escape/secret.md',
               'filelink', ':(glob)notes', ' ', '', 'x' * 2001]
        for ref in bad:
            with self.subTest(ref=ref[:40]):
                self.refused(*self.BASE, '--reference', ref)
                self.refused('edit', qid, '--reference', ref)
        self.assertEqual(self.item(qid)['references'], [])
        self.assertEqual(len(self.ok('list', '--full')['items']), 1)

    def test_duplicate_and_excess_references_are_refused(self):
        self.refused(*self.BASE, '--reference', 'notes/brief.md', '--reference', 'notes/brief.md')
        (self.repo / 'many').mkdir()
        names = []
        for n in range(51):
            (self.repo / f'many/{n}.md').write_text('x')
            names.append(f'many/{n}.md')
        argv = list(self.BASE)
        for name in names:
            argv += ['--reference', name]
        self.refused(*argv)

    def test_a_queue_file_without_the_key_reads_and_round_trips_unchanged(self):
        self.add('Plain')
        path = self.repo / 'notes/queue/cycles.yaml'
        before = path.read_bytes()
        self.assertNotIn(b'references', before)
        self.ok('list', '--full')
        self.ok('edit', 'Q-0001', '--title', 'Plain')
        self.assertEqual(path.read_bytes(), before)

    def test_a_deleted_reference_does_not_break_reading_the_queue(self):
        qid = self.add_ref('notes/extra.md')['id']
        (self.repo / 'notes/extra.md').unlink()
        self.assertEqual(self.item(qid)['references'], ['notes/extra.md'])

    def test_a_malformed_stored_list_is_refused_at_read_time(self):
        import yaml
        self.add_ref('notes/brief.md')
        path = self.repo / 'notes/queue/cycles.yaml'
        for bad in (['a', 'a'], [' '], 'notes/brief.md', [1], ['x' * 2001], [f'p{n}' for n in range(51)]):
            with self.subTest(bad=str(bad)[:30]):
                doc = yaml.safe_load(path.read_text())
                doc['items'][0]['references'] = bad
                path.write_text(yaml.safe_dump(doc, sort_keys=False))
                self.refused('list')
                self.assertRaises(cycle_queue.QueueError, cycle_queue.check_queue, doc)

    def test_start_next_puts_references_in_the_goal_and_never_in_scope(self):
        qid = self.add_ref('notes/brief.md', 'notes/extra.md')['id']
        self.authorize('queue')
        code, started = self.start()
        self.assertEqual(code, 0, started)
        doc = load(self.repo, started['cycle'])
        outcome = 'Deliver R'
        self.assertEqual(doc['goal'], outcome + '\n\nReferences (read before planning; read-only, not scope):\n- notes/brief.md\n- notes/extra.md')
        self.assertEqual(doc['plan']['scope'], ['src'])
        self.assertEqual(doc['plan']['constraints'], [])
        self.assertNotIn('notes/brief.md', json.dumps(doc['plan']))
        self.assertEqual(doc['history'][0]['queue']['item'], qid)
        self.assertEqual(set(doc['history'][0]['queue']), {'item', 'token'})

    def test_start_next_without_references_leaves_the_goal_equal_to_the_outcome(self):
        self.add('Plain')
        self.authorize('queue')
        code, started = self.start()
        self.assertEqual(code, 0, started)
        self.assertEqual(load(self.repo, started['cycle'])['goal'], 'Deliver Plain')

    def test_start_next_starts_a_release_item_as_a_beta_list_cycle(self):
        self.add('Ship', kind='release')
        self.authorize('queue')
        code, started = self.start()
        self.assertEqual(code, 0, started)
        doc = load(self.repo, started['cycle'])
        self.assertEqual((doc['type'], doc['release_list'], doc['phase']), ('release', 'beta', 'release'))
        self.assertEqual([t['id'] for t in doc['plan']['tasks']], ['prep', 'prepare', 'verify', 'beta-and-smoke', 'tag', 'record'])
        self.assertEqual((doc['plan']['scope'], doc['plan']['acceptance']), (['src'], ['it works']))
        self.assertNotIn('release_list', self.queue_items()[0], 'an item without the key stores none')
        self.assertEqual(self.item_view(started['item'])['release_list'], 'beta')

    def queue_items(self):
        return cycle_queue.read_queue(cycle_queue.tree(self.repo))['items']

    def item_view(self, qid):
        return self.ok('show', qid)['item']

    def test_queue_add_release_list_official_stores_the_list_and_start_next_creates_an_official_list_cycle(self):
        qid = self.ok('add', '--title', 'Promote', '--outcome', 'Deliver Promote', '--type', 'release', '--scope', 'src',
                    '--acceptance', 'it works', '--release-list', 'official')['item']['id']
        self.assertEqual(self.queue_items()[0]['release_list'], 'official')
        self.assertEqual(self.item_view(qid)['release_list'], 'official')
        self.authorize('queue')
        code, started = self.start()
        self.assertEqual(code, 0, started)
        doc = load(self.repo, started['cycle'])
        self.assertEqual((doc['type'], doc['release_list'], doc['phase']), ('release', 'official', 'release'))
        self.assertEqual([t['id'] for t in doc['plan']['tasks']], ['live-check-and-go-ahead', 'official', 'record'])

    def test_queue_add_release_list_beta_is_stored_and_starts_a_beta_list_cycle(self):
        self.ok('add', '--title', 'Ship', '--outcome', 'Deliver Ship', '--type', 'release', '--scope', 'src',
                '--acceptance', 'it works', '--release-list', 'beta')
        self.assertEqual(self.queue_items()[0]['release_list'], 'beta')
        self.authorize('queue')
        code, started = self.start()
        self.assertEqual(code, 0, started)
        self.assertEqual(load(self.repo, started['cycle'])['release_list'], 'beta')

    def test_a_release_list_belongs_to_release_items_and_names_a_known_list(self):
        refused = self.refused('add', '--title', 'Fix', '--outcome', 'Deliver Fix', '--type', 'quick-fix', '--scope', 'src',
                               '--acceptance', 'it works', '--release-list', 'official')
        self.assertIn('--release-list', refused['error'])
        self.assertEqual(self.queue_items(), [])
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), patch('sys.stderr', io.StringIO()):
                cycle.main(['--repo-root', str(self.repo), 'queue', 'add', '--title', 'S', '--outcome', 'o', '--type', 'release',
                            '--scope', 'src', '--acceptance', 'a', '--release-list', 'nightly'])
        qid = self.ok('add', '--title', 'Promote', '--outcome', 'Deliver Promote', '--type', 'release', '--scope', 'src',
                      '--acceptance', 'it works', '--release-list', 'official')['item']['id']
        changed = self.refused('edit', qid, '--type', 'quick-fix')
        self.assertIn('release_list', changed['error'])

    def test_the_schema_refuses_an_unknown_release_list_in_the_file(self):
        self.ok('add', '--title', 'Ship', '--outcome', 'Deliver Ship', '--type', 'release', '--scope', 'src',
                '--acceptance', 'it works', '--release-list', 'official')
        path = self.repo / 'notes/queue/cycles.yaml'
        path.write_text(path.read_text().replace('release_list: official', 'release_list: nightly'))
        with self.assertRaises(cycle_queue.QueueError):
            cycle_queue.read_queue(cycle_queue.tree(self.repo))


class OriginTests(Base):
    def test_create_records_origin_on_the_created_event_only_when_given(self):
        plain = create(self.repo, 'quick-fix', 'P', 'g', ['src'], ['a'], 'i', 'c')
        queued = create(self.repo, 'quick-fix', 'Q', 'g', ['src'], ['a'], 'i', 'c', origin={'item': 'Q-0001', 'token': 'a' * 32})
        self.assertNotIn('queue', plain['history'][0])
        self.assertEqual(queued['history'][0]['queue'], {'item': 'Q-0001', 'token': 'a' * 32})
        self.assertEqual(load(self.repo, queued['id'])['history'][0]['queue']['item'], 'Q-0001')


if __name__ == '__main__':
    unittest.main()
