"""Bounded, read-only context through the commander's existing cycle.py lane."""
import contextlib
import hashlib
import io
import json
import os
import shutil
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_ops
from cycle_workflow import load, tree
from test_cycle_slice import SliceBase


class ContextReadTests(SliceBase):
    def cli(self, ref, *flags):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), '--compact', 'context-read', self.cid,
                               '--ref', ref, *map(str, flags)])
        return code, json.loads(out.getvalue())

    def reader(self):
        import cycle_context_read
        return cycle_context_read

    def result(self, text='An uncommitted report.\n'):
        prepared = self.prepare()
        path = Path(prepared['result_path'])
        path.write_text(text, encoding='utf-8')
        return path, 'result:build-it/1'

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def assert_refused(self, ref, reason, *flags):
        before = self.record_path().read_bytes()
        code, response = self.cli(ref, *flags)
        self.assertEqual(code, 1, response)
        self.assertEqual(response['error']['code'], reason, response)
        self.assertNotIn('text', response)
        self.assertEqual(self.record_path().read_bytes(), before)
        return response

    def test_cli_reads_uncommitted_exact_bound_result_without_writes(self):
        path, ref = self.result()
        before = self.record_path().read_bytes()
        head = self.git('rev-parse', 'HEAD')
        code, response = self.cli(ref)
        self.assertEqual(code, 0, response)
        self.assertEqual(response['source_path'], str(path))
        self.assertEqual(response['text'], path.read_text())
        self.assertEqual(response['size_bytes'], len(path.read_bytes()))
        self.assertEqual(response['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertTrue(response['complete'])
        self.assertIsNone(response['next_offset'])
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)

    def test_new_default_directory_binds_canonical_path_but_preserves_old_or_explicit_paths(self):
        actual = self.repo / 'scratch'
        actual.mkdir()
        alias = self.repo / 'temp-alias'
        alias.symlink_to(actual, target_is_directory=True)
        with patch.object(cycle_ops.tempfile, 'mkdtemp', return_value=str(alias)):
            doc = {'id': self.cid}
            self.assertEqual(cycle_ops.results_directory(doc), actual)
            self.assertEqual(doc['results_dir'], str(actual))
        old = {'id': self.cid, 'results_dir': str(alias / 'old')}
        (actual / 'old').mkdir()
        self.assertEqual(cycle_ops.results_directory(old), alias / 'old')
        explicit = alias / 'report.md'
        explicit.write_text('explicit path stays recorded')
        prepared = self.prepare(result_path=str(explicit))
        self.assertEqual(prepared['result_path'], str(explicit))
        self.assert_refused('result:build-it/1', 'unsafe-path')

    def test_project_and_plugin_context_are_code_owned_references(self):
        self.write('AGENTS.md', 'Project instructions.\n')
        for ref in ['repo:AGENTS.md', 'repo:bionic/objectives.md',
                    'plugin:agents/commander.md', 'plugin:skills/cycle/SKILL.md',
                    'plugin:skills/cycle/references/testing.md', 'plugin:schemas/cycle.schema.json']:
            code, response = self.cli(ref)
            self.assertEqual(code, 0, response)
            self.assertTrue(response['text'])
        code, response = self.op({'op': 'inspect'})
        self.assertEqual(code, 0, response)
        refs = {row['ref'] for row in response['context_read']['references']}
        self.assertIn('repo:AGENTS.md', refs)
        self.assertIn('plugin:agents/commander.md', refs)
        self.assertEqual(response['context_read']['max_object_bytes'], self.reader().MAX_OBJECT_BYTES)

    def test_canonical_cycle_artifact_and_retained_report(self):
        path, ref = self.result()
        text = path.read_text()
        artifact = self.write(f'bionic/cycles/{self.cid}/evidence/plan/notes.md', 'Build notes.\n')
        self.assertEqual(self.cli('repo:' + str(artifact.relative_to(self.repo)))[1]['text'], 'Build notes.\n')
        # Retained reports are identified by the attempt, never by an external caller's path.
        raw = json.loads(self.record_path().read_text())
        retained = f'cycles/{self.cid}/results/build-it-attempt-1.md'
        self.write('bionic/' + retained, text)
        raw['assignments'][0]['delivery'] = {'path': retained, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
                                            'outcome': 'blocked', 'commits': [], 'evidence': [], 'at': raw['updated_at']}
        # Use the reader's pure reference builder to avoid fabricating a valid engine delivery.
        response = self.reader().read_context(tree(self.repo), raw, 'retained-result:build-it/1')
        self.assertEqual(response['text'], text)
        self.write('bionic/' + retained, 'changed')
        response = self.reader().read_context(tree(self.repo), raw, 'retained-result:build-it/1')
        self.assertEqual(response['error']['code'], 'bound-digest-changed')
        self.assertNotIn('text', response)

    def test_unknown_external_and_unlisted_repository_paths_are_refused(self):
        self.write('src/private.txt', 'not context')
        for ref in ['/etc/passwd', 'repo:src/private.txt', 'plugin:scripts/secret_scan.py',
                    'result:other/1', 'result:build-it/2']:
            self.assert_refused(ref, 'unknown-reference')

    def test_traversal_and_noncanonical_reference_spellings_refuse(self):
        for ref in ['repo:../AGENTS.md', 'repo:bionic/../AGENTS.md', 'repo:/etc/passwd',
                    'plugin:agents/../agents/commander.md', 'repo:./AGENTS.md', 'repo:AGENTS.md\x00']:
            self.assert_refused(ref, 'invalid-reference')

    def test_missing_allowed_object_reports_no_content(self):
        self.assert_refused('repo:AGENTS.md', 'object-missing')

    def test_missing_nofollow_capability_is_explicit(self):
        self.write('AGENTS.md', 'context')
        with patch.object(self.reader().os, 'supports_dir_fd', set()):
            self.assert_refused('repo:AGENTS.md', 'read-capability-unavailable')

    def test_result_symlink_and_parent_symlink_refuse(self):
        path, ref = self.result()
        target = self.write('target.md', 'must not read')
        path.unlink()
        path.symlink_to(target)
        self.assert_refused(ref, 'unsafe-path')
        path.unlink()
        directory = path.parent
        moved = directory.with_name(directory.name + '-moved')
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        self.addCleanup(lambda: directory.unlink())
        self.addCleanup(lambda: shutil.rmtree(moved))
        self.assert_refused(ref, 'unsafe-path')

    def test_project_symlink_pointing_inside_and_plugin_symlink_refuse(self):
        self.write('target.md', 'must not read')
        (self.repo / 'AGENTS.md').symlink_to(self.repo / 'target.md')
        self.assert_refused('repo:AGENTS.md', 'unsafe-path')
        with patch.object(self.reader(), 'PLUGIN_ROOT', self.repo / 'plugin'):
            self.write('plugin/agents/commander.md', 'context')
            (self.repo / 'plugin/agents/commander.md').unlink()
            (self.repo / 'plugin/agents/commander.md').symlink_to(self.repo / 'target.md')
            self.assert_refused('plugin:agents/commander.md', 'unsafe-path')

    def test_fifo_and_directory_refuse_without_blocking(self):
        path, ref = self.result()
        path.unlink()
        os.mkfifo(path)
        self.assert_refused(ref, 'not-regular')
        path.unlink()
        path.mkdir()
        self.addCleanup(path.rmdir)
        self.assert_refused(ref, 'not-regular')

    def test_credential_locations_refuse_even_when_bound(self):
        reader = self.reader()
        for name in ['.env', '.env.production', 'config.env', '.envrc', '.aws/credentials',
                     '.ssh/id_ed25519', '.crux/env', 'credentials.json', 'secrets/token.txt',
                     '.codex/auth.json', '.claude/.credentials.json', '.git-credentials', '.docker/config.json']:
            raw = load(self.repo, self.cid)
            raw['assignments'] = [{'id': 'bound', 'attempt': 1, 'result_path': str(self.repo / name)}]
            response = reader.read_context(tree(self.repo), raw, 'result:bound/1')
            self.assertEqual(response['error']['code'], 'forbidden-path', name)
            self.assertNotIn('text', response)
        with patch.dict(os.environ, {'CRUX_HOME': str(self.repo / 'runtime')}):
            raw['assignments'][0]['result_path'] = str(self.repo / 'runtime/env')
            response = reader.read_context(tree(self.repo), raw, 'result:bound/1')
            self.assertEqual(response['error']['code'], 'forbidden-path')

    def test_secret_scans_entire_object_before_returning_any_page(self):
        path, ref = self.result('Public opening.\n' + 'x' * 20000 + '\nghp_' + 'a' * 36)
        response = self.assert_refused(ref, 'secret-detected', '--limit', 100)
        self.assertEqual(response['size_bytes'], path.stat().st_size)
        self.assertEqual(response['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertNotIn('a' * 36, json.dumps(response))

    def test_scanner_exception_during_reference_selection_refuses_without_details(self):
        self.write('AGENTS.md', 'Context for the reader.\n')
        with patch.object(self.reader(), 'scan_text', side_effect=RuntimeError('private scanner diagnostics')):
            response = self.assert_refused('repo:AGENTS.md', 'scanner-unavailable')
        self.assertNotIn('private scanner diagnostics', json.dumps(response))
        self.assertNotIn('RuntimeError', json.dumps(response))

    def test_scanner_exception_during_whole_object_scan_keeps_safe_metadata(self):
        text = 'Context for the reader.\n'
        path = self.write('AGENTS.md', text)
        original_scan = self.reader().scan_text
        def unavailable(value):
            if value == text:
                raise RuntimeError('private scanner diagnostics')
            return original_scan(value)
        with patch.object(self.reader(), 'scan_text', side_effect=unavailable):
            response = self.assert_refused('repo:AGENTS.md', 'scanner-unavailable')
        self.assertEqual(response['source_path'], str(path))
        self.assertEqual(response['size_bytes'], len(text.encode()))
        self.assertEqual(response['sha256'], hashlib.sha256(text.encode()).hexdigest())
        self.assertNotIn('private scanner diagnostics', json.dumps(response))
        self.assertNotIn('RuntimeError', json.dumps(response))

    def test_scanner_exception_in_inspect_lists_no_partial_references_and_writes_nothing(self):
        before = self.record_path().read_bytes()
        head = self.git('rev-parse', 'HEAD')
        with patch.object(self.reader(), 'scan_text', side_effect=RuntimeError('private scanner diagnostics')):
            code, response = self.op({'op': 'inspect'})
        self.assertEqual(code, 0, response)
        self.assertEqual(response['context_read']['error']['code'], 'scanner-unavailable')
        self.assertFalse(response['context_read']['ok'])
        self.assertEqual(response['context_read']['references'], [])
        self.assertNotIn('private scanner diagnostics', json.dumps(response))
        self.assertNotIn('RuntimeError', json.dumps(response))
        self.assertEqual(self.record_path().read_bytes(), before)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)

    def test_invalid_utf8_refuses_entire_object_with_safe_metadata(self):
        path, ref = self.result()
        path.write_bytes(b'opening\n\xff')
        response = self.assert_refused(ref, 'invalid-utf8')
        self.assertEqual(response['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_large_assignment_shape_and_exact_total_boundary_are_readable(self):
        reader = self.reader()
        # Both the plan's original observation and the expanded dispatch must fit.
        for size in [95029, 196384, reader.MAX_OBJECT_BYTES]:
            assignment = 'Mandatory assignment — objectives, approved scope, and exact result marker.\n'
            text = ((assignment * (size // len(assignment) + 1))[:size]
                    if size < reader.MAX_OBJECT_BYTES else 'a' * size)
            path = self.write('AGENTS.md', text)
            code, first = self.cli('repo:AGENTS.md')
            self.assertEqual(code, 0, first)
            parts = [first['text']]
            page = first
            while page['next_offset'] is not None:
                code, page = self.cli('repo:AGENTS.md', '--offset', page['next_offset'], '--sha256', first['sha256'])
                self.assertEqual(code, 0, page)
                parts.append(page['text'])
            self.assertEqual(''.join(parts).encode(), path.read_bytes())
            self.assertEqual(first['size_bytes'], len(text.encode()))
        self.write('AGENTS.md', 'x' * (reader.MAX_OBJECT_BYTES + 1))
        response = self.assert_refused('repo:AGENTS.md', 'object-too-large')
        self.assertEqual(response['size_bytes'], reader.MAX_OBJECT_BYTES + 1)
        self.assertIsNone(response['sha256'])  # An oversized object is never read to hash it.

    def test_utf8_pages_use_byte_offsets_and_never_split_characters(self):
        text = 'aé🙂z' * 30
        self.write('AGENTS.md', text)
        code, first = self.cli('repo:AGENTS.md', '--limit', 5)
        parts = [first['text']]
        page = first
        while page['next_offset'] is not None:
            code, page = self.cli('repo:AGENTS.md', '--limit', 5, '--offset', page['next_offset'], '--sha256', first['sha256'])
            self.assertEqual(code, 0, page)
            self.assertLessEqual(len(page['text'].encode()), 5)
            parts.append(page['text'])
        self.assertEqual(''.join(parts), text)
        self.assert_refused('repo:AGENTS.md', 'invalid-offset', '--offset', 2, '--sha256', first['sha256'])

    def test_pagination_requires_full_digest_and_changed_file_refuses(self):
        self.write('AGENTS.md', 'x' * 300)
        _, first = self.cli('repo:AGENTS.md', '--limit', 100)
        self.assert_refused('repo:AGENTS.md', 'digest-required', '--offset', 100)
        self.write('AGENTS.md', 'y' * 300)
        self.assert_refused('repo:AGENTS.md', 'digest-changed', '--offset', 100, '--sha256', first['sha256'])
        self.assert_refused('repo:AGENTS.md', 'invalid-digest', '--sha256', 'not-a-digest')

    def test_page_limits_and_offsets_are_explicit_refusals(self):
        self.write('AGENTS.md', 'abc')
        for limit in [0, 3, self.reader().MAX_PAGE_BYTES + 1]:
            self.assert_refused('repo:AGENTS.md', 'invalid-limit', '--limit', limit)
        self.assert_refused('repo:AGENTS.md', 'invalid-offset', '--offset', -1)
        self.assert_refused('repo:AGENTS.md', 'invalid-offset', '--offset', 4, '--sha256', hashlib.sha256(b'abc').hexdigest())
        self.write('AGENTS.md', '')
        code, response = self.cli('repo:AGENTS.md')
        self.assertEqual((code, response['text'], response['complete']), (0, '', True))

    def test_descriptor_identity_refuses_replaced_leaf(self):
        self.write('AGENTS.md', 'original')
        reader = self.reader()
        real_read = reader.os.read
        changed = False
        def replace(fd, size):
            nonlocal changed
            if not changed:
                changed = True
                other = self.write('replacement.md', 'replacement')
                other.replace(self.repo / 'AGENTS.md')
            return real_read(fd, size)
        with patch.object(reader.os, 'read', side_effect=replace):
            self.assert_refused('repo:AGENTS.md', 'object-changed')


    def _log_doc(self, *names):
        """A record whose goal References block names `names`, the route the IDR keeps for the log."""
        raw = json.loads(self.record_path().read_text())
        heading = '\n\nReferences (read before planning; read-only, not scope):\n'
        raw['goal'] = raw.get('goal', '') + heading + ''.join(f'- {name}\n' for name in names)
        return raw

    def test_operation_log_above_one_mebibyte_pages_through_a_goal_reference(self):
        reader = self.reader()
        entry = '## 2026-11-08 log entry\n\nOne operation recorded newest first.\n\n'
        text = (entry * ((reader.MAX_OBJECT_BYTES + 200000) // len(entry) + 1))
        path = self.write('bionic/log.md', text)
        self.assertGreater(path.stat().st_size, reader.MAX_OBJECT_BYTES)
        raw = self._log_doc('bionic/log.md')
        first = reader.read_context(tree(self.repo), raw, 'repo:bionic/log.md')
        self.assertTrue(first['ok'], first)
        self.assertEqual(first['size_bytes'], len(text.encode()))
        self.assertEqual(first['text'], text[:reader.MAX_PAGE_BYTES])
        last_offset = len(text.encode()) - 100
        last = reader.read_context(tree(self.repo), raw, 'repo:bionic/log.md',
                                   offset=last_offset, sha256=first['sha256'])
        self.assertTrue(last['complete'], last)
        self.assertEqual(last['text'], text[last_offset:])

    def test_non_log_object_of_the_same_size_still_refuses_too_large(self):
        reader = self.reader()
        size = reader.MAX_OBJECT_BYTES + 200000
        self.write('bionic/notes.md', 'x' * size)
        raw = self._log_doc('bionic/notes.md')
        response = reader.read_context(tree(self.repo), raw, 'repo:bionic/notes.md')
        self.assertEqual(response['error']['code'], 'object-too-large', response)
        self.assertEqual(response['size_bytes'], size)
        self.assertNotIn('text', response)

    def test_operation_log_with_a_secret_like_line_refuses_whole_object(self):
        reader = self.reader()
        self.write('bionic/log.md', 'x' * (reader.MAX_OBJECT_BYTES + 10) + '\nghp_' + 'a' * 36 + '\n')
        raw = self._log_doc('bionic/log.md')
        response = reader.read_context(tree(self.repo), raw, 'repo:bionic/log.md')
        self.assertEqual(response['error']['code'], 'secret-detected', response)
        self.assertNotIn('text', response)

    def test_operation_log_above_eight_mebibytes_refuses_too_large(self):
        reader = self.reader()
        self.assertEqual(reader.LOG_OBJECT_BYTES, 8 * 1024 * 1024)
        self.write('bionic/log.md', 'x' * (reader.LOG_OBJECT_BYTES + 1))
        raw = self._log_doc('bionic/log.md')
        response = reader.read_context(tree(self.repo), raw, 'repo:bionic/log.md')
        self.assertEqual(response['error']['code'], 'object-too-large', response)
        self.assertEqual(response['size_bytes'], reader.LOG_OBJECT_BYTES + 1)
        self.assertNotIn('text', response)

    STRAY = 'bionic/log/.stray-' + 'a' * 64 + '.md'
    STAGED_LEGACY = 'bionic/log/.legacy-' + 'b' * 64 + '.md'

    def test_detail_files_and_a_staged_stray_between_one_and_eight_mebibytes_are_readable(self):
        reader = self.reader()
        for name in ('bionic/log/2026-11.md', self.STRAY):
            with self.subTest(name=name):
                size = reader.MAX_OBJECT_BYTES + 200000
                self.write(name, 'x' * size)
                response = reader.read_context(tree(self.repo), self._log_doc(name), 'repo:' + name)
                self.assertTrue(response['ok'], response)
                self.assertEqual(response['size_bytes'], size)

    def test_a_staged_legacy_file_between_one_and_eight_mebibytes_is_readable(self):
        reader = self.reader()
        size = reader.MAX_OBJECT_BYTES + 200000
        # POSITIVE CONTROL: a summary file of this size refuses, so the read below
        # succeeds because of the staged legacy name and not because of the size.
        self.write('bionic/log/summary.md', 'x' * size)
        control = reader.read_context(tree(self.repo), self._log_doc('bionic/log/summary.md'),
                                      'repo:bionic/log/summary.md')
        self.assertEqual(control['error']['code'], 'object-too-large', control)
        self.write(self.STAGED_LEGACY, 'x' * size)
        response = reader.read_context(tree(self.repo), self._log_doc(self.STAGED_LEGACY),
                                       'repo:' + self.STAGED_LEGACY)
        self.assertTrue(response['ok'], response)
        self.assertEqual(response['size_bytes'], size)

    def test_a_detail_file_above_eight_mebibytes_refuses_too_large(self):
        reader = self.reader()
        name = 'bionic/log/2026-11.md'
        self.write(name, 'x' * (reader.LOG_OBJECT_BYTES + 1))
        response = reader.read_context(tree(self.repo), self._log_doc(name), 'repo:' + name)
        self.assertEqual(response['error']['code'], 'object-too-large', response)
        self.assertEqual(response['size_bytes'], reader.LOG_OBJECT_BYTES + 1)
        self.assertNotIn('text', response)

    def test_other_objects_under_the_log_directory_keep_the_one_mebibyte_bound(self):
        reader = self.reader()
        size = reader.MAX_OBJECT_BYTES + 200000
        # POSITIVE CONTROL: a detail file of this size is readable, so the refusals below
        # come from the path and not from the size.
        self.write('bionic/log/2026-11.md', 'x' * size)
        control = reader.read_context(tree(self.repo), self._log_doc('bionic/log/2026-11.md'),
                                      'repo:bionic/log/2026-11.md')
        self.assertTrue(control['ok'], control)
        for name in ('bionic/log/summary.md', 'bionic/log/.split-complete.json',
                     'bionic/log/2026-13.md', 'bionic/log/nested/2026-11.md', 'bionic/notlog/2026-11.md'):
            with self.subTest(name=name):
                self.write(name, 'x' * size)
                response = reader.read_context(tree(self.repo), self._log_doc(name), 'repo:' + name)
                self.assertEqual(response['error']['code'], 'object-too-large', response)
                self.assertEqual(response['size_bytes'], size)

    def test_operation_log_without_a_listed_reference_stays_unknown(self):
        self.write('bionic/log.md', 'Newest first.\n')
        self.assert_refused('repo:bionic/log.md', 'unknown-reference')

if __name__ == '__main__':
    unittest.main()
