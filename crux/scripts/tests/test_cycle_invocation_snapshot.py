"""Exact native contracts and immutable invocation recovery, with offline fixtures."""
import json
import contextlib
import multiprocessing
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_hosts
import cycle_ops
import cycle_dispatch
import cycle_context_read as reader
import test_cycle_slice as fixtures
from cycle_workflow import digest, load, mutate, tree


def prepare_worker(repo, cid, request, gate, results):
    gate.wait(10)
    code, response = cycle_ops.run(repo, cid, request)
    results.put((code, response))


class InvocationSnapshotTests(fixtures.SliceBase):
    def selected_context(self, names=('cycle',)):
        directory = self.repo / 'plugin'
        directory.mkdir(exist_ok=True)
        (directory / 'agents').mkdir(exist_ok=True)
        shutil.copyfile(cycle_hosts.PLUGIN_ROOT / 'agents/developer.md', directory / 'agents/developer.md')
        role = directory / 'agents/developer.md'
        role.write_text(role.read_text().replace('skills: []', 'skills: [cycle]'))
        selected = []
        for name in names:
            target = directory / 'skills' / name
            target.mkdir(parents=True, exist_ok=True)
            raw = (cycle_hosts.PLUGIN_ROOT / 'skills' / name / 'SKILL.md').read_bytes()
            # Prove line endings survive the selector's historical read_text normalization.
            raw = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            (target / 'SKILL.md').write_bytes(raw)
            selected.append({'id': name, 'directory': str(target), 'body': (target / 'SKILL.md').read_text()})
        return directory, {'selected': selected, 'retrievable': ['forge-skill']}

    def selected_scope(self, directory, context):
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(cycle_hosts, 'PLUGIN_ROOT', directory))
        stack.enter_context(patch.object(cycle_ops, 'optional_context', return_value=context))
        return stack

    def bundle(self, prepared):
        return json.loads((tree(self.repo).docs_root / prepared['invocation_snapshot']['path']).read_bytes())

    def page_all(self, ref):
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        pieces, offset, sha = [], 0, None
        while True:
            page = reader.read_context(cfg, doc, ref, offset=offset, sha256=sha)
            self.assertTrue(page['ok'], page)
            pieces.append(page['text'])
            sha = page['sha256']
            if page['complete']:
                return ''.join(pieces).encode('utf-8')
            offset = page['next_offset']

    def test_codex_exposed_spawn_and_global_wait_signature(self):
        out = self.prepare(host='codex')['invocation']
        self.assertEqual(set(out['parameters']), {'task_name', 'agent_type', 'message'})
        self.assertRegex(out['parameters']['task_name'], r'^[a-z0-9_]+$')
        self.assertEqual(out['wait']['parameters'], {'timeout_ms': 60000})
        self.assertNotIn('caller_fills', out['wait'])
        contract = json.loads((Path(__file__).parent / 'fixtures/host_contracts/codex-cyc0100.json').read_text())
        self.assertIsNone(out['interface']['version'])
        for name, params in (('collaboration.spawn_agent', out['parameters']),
                             ('collaboration.wait_agent', out['wait']['parameters'])):
            schema = contract['tools'][name]
            self.assertTrue(set(schema['required']).issubset(params))
            self.assertTrue(set(params).issubset(schema['properties']))
        self.assertEqual(out['interface']['spawn']['tool'], 'collaboration.spawn_agent')
        self.assertEqual(out['interface']['wait']['tool'], 'collaboration.wait_agent')

    def test_prepare_retains_exact_takeover_invocation_without_request(self):
        """Positive control: an accepted request persists the refused cases' snapshot marker."""
        prepared = self.prepare(assignment_text='Keep these exact addendum bytes.\r\n')
        reference = prepared['invocation_snapshot']
        self.assertTrue((tree(self.repo).docs_root / reference['path']).is_file())
        raw = (tree(self.repo).docs_root / reference['path']).read_bytes()
        bundle = json.loads(raw)
        self.assertEqual(bundle['addendum'], 'Keep these exact addendum bytes.\r\n')
        self.assertEqual(bundle['invocation'], prepared['invocation'])
        recovered = self.ok({'op': 'dispatch-invocation', 'assignment': prepared['assignment'], 'attempt': 1})
        self.assertEqual(recovered['invocation'], prepared['invocation'])

    def test_unsafe_addendum_refuses_without_reservation_or_snapshot(self):
        before = self.record_path().read_bytes()
        code, _ = self.op({'op': 'prepare-dispatch', 'op_id': 'unsafe-addendum-1', 'task_id': 'build-it',
                           'role': 'developer', 'host': 'codex',
                           'assignment_text': 'OPENROUTER_API_KEY=sk-or-v1-' + 'a' * 64})
        self.assertEqual(code, 1)
        self.assertEqual(before, self.record_path().read_bytes())
        self.assertFalse((tree(self.repo).docs_root / 'cycles' / self.cid / 'invocations').exists())

    def test_mandatory_and_native_context_retained_optional_bytes_fully_retrievable(self):
        directory, context = self.selected_context(('cycle', 'archive-promptbook', 'audit-docs'))
        with self.selected_scope(directory, context):
            prepared = self.prepare(assignment_text='Exact question, with original provenance.\r\n')
            bundle = self.bundle(prepared)
            message = prepared['invocation']['parameters']['prompt']
            for required in ('Mandatory assignment', 'Expected evidence:', 'Acceptance criteria:', 'Constraints:',
                             'Integration owner:', 'Exact question', prepared['delivery_token']):
                self.assertIn(required, message)
            self.assertEqual(bundle['native_context']['preloads'][0]['id'], 'cycle')
            self.assertEqual(bundle['native_context']['role']['body'].encode(), (directory / 'agents/developer.md').read_bytes())
            self.assertEqual(bundle['native_context']['preloads'][0]['body'].encode(), (directory / 'skills/cycle/SKILL.md').read_bytes())
            for item in bundle['selected']:
                raw = self.page_all('repo:' + (tree(self.repo).docs_root / item['path']).relative_to(self.repo).as_posix())
                self.assertEqual(raw, Path(item['origin']).read_bytes())
                self.assertEqual(digest(raw), item['sha256'])
                self.assertEqual(len(raw), item['size_bytes'])
                self.assertEqual(item['directory'], str(Path(item['origin']).parent))
                self.assertNotEqual(item['directory'], str((tree(self.repo).docs_root / item['path']).parent))
                self.assertIn('--sha256 ' + item['sha256'], message)
            frozen = self.page_all('invocation:build-it/1')
            self.assertEqual(digest(frozen), prepared['invocation_snapshot']['sha256'])
            self.assertLess(len(message), len(bundle['mandatory_message'] + cycle_hosts.context_text(context) + bundle['preamble']))

    def test_canonical_mutation_preserves_frozen_retrieval_but_refuses_first_dispatch(self):
        directory, context = self.selected_context()
        with self.selected_scope(directory, context):
            prepared = self.prepare()
            frozen = self.page_all('invocation:build-it/1')
            original = (directory / 'skills/cycle/SKILL.md').read_bytes()
            (directory / 'skills/cycle/SKILL.md').write_bytes(original + b'\nChanged canonical context.\n')
            self.assertEqual(frozen, self.page_all('invocation:build-it/1'))
            item = self.bundle(prepared)['selected'][0]
            self.assertEqual(original, (tree(self.repo).docs_root / item['path']).read_bytes())
            before = self.record_path().read_bytes()
            refused = self.refused({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1}, 'invocation-source-changed')
            self.assertEqual(refused['errors'][0]['recovery'][0]['request'], {'op': 'inspect'})
            self.assertEqual(before, self.record_path().read_bytes())

    def test_edit_during_selected_capture_refuses_before_persisting(self):
        directory, context = self.selected_context()
        source = directory / 'skills/cycle/SKILL.md'
        original = source.read_bytes()
        native = cycle_dispatch._native
        def change_after_native(role):
            retained = native(role)
            source.write_bytes(original + b'\nConcurrent selected/preload edit.\n')
            return retained
        with self.selected_scope(directory, context), patch.object(cycle_dispatch, '_native', side_effect=change_after_native):
            self.refused({'op': 'prepare-dispatch', 'op_id': 'selected-fence-1', 'task_id': 'build-it',
                          'role': 'developer', 'host': 'codex'}, 'invocation-source-changed')
        self.assertFalse((tree(self.repo).docs_root / 'cycles' / self.cid / 'invocations').exists())

    def test_edit_during_mandatory_render_refuses_before_persisting(self):
        directory, context = self.selected_context()
        role = directory / 'agents/developer.md'
        original = role.read_text()
        assignment = cycle_hosts.assignment
        def change_after_assignment(**kwargs):
            retained = assignment(**kwargs)
            role.write_text(original.replace('The host supplies this role contract.', 'The host supplies a changed role contract.'))
            return retained
        with self.selected_scope(directory, context), patch.object(cycle_hosts, 'assignment', side_effect=change_after_assignment):
            self.refused({'op': 'prepare-dispatch', 'op_id': 'mandatory-fence-1', 'task_id': 'build-it',
                          'role': 'developer', 'host': 'codex'}, 'invocation-source-changed')
        self.assertFalse((tree(self.repo).docs_root / 'cycles' / self.cid / 'invocations').exists())

    def test_scanner_failure_and_invalid_utf8_refuse_before_persistence(self):
        with patch.object(reader, 'scan_text', side_effect=RuntimeError('scanner diagnostic')):
            self.refused({'op': 'prepare-dispatch', 'op_id': 'scan-unavailable', 'task_id': 'build-it',
                          'role': 'developer', 'host': 'codex'}, 'invocation-scanner-unavailable')
        self.refused({'op': 'prepare-dispatch', 'op_id': 'invalid-utf8-1', 'task_id': 'build-it',
                      'role': 'developer', 'host': 'codex', 'assignment_text': '\ud800'}, 'invocation-invalid-utf8')
        self.assertFalse((tree(self.repo).docs_root / 'cycles' / self.cid / 'invocations').exists())

    def test_observed_large_assignment_shapes_are_completely_readable(self):
        for length in (95029, 196384, 222385):
            with self.subTest(characters=length):
                cid = self.fixture()
                prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'large-' + str(length), 'task_id': 'build-it',
                                    'role': 'developer', 'host': 'codex', 'assignment_text': 'x' * length}, cid=cid)
                doc, cfg = load(self.repo, cid), tree(self.repo)
                page = reader.read_context(cfg, doc, 'invocation:build-it/1')
                chunks = [page['text']]
                while not page['complete']:
                    page = reader.read_context(cfg, doc, 'invocation:build-it/1', offset=page['next_offset'], sha256=page['sha256'])
                    self.assertTrue(page['ok'], page)
                    chunks.append(page['text'])
                raw = ''.join(chunks).encode()
                self.assertEqual(digest(raw), prepared['invocation_snapshot']['sha256'])
                self.assertEqual(len(json.loads(raw)['addendum']), length)
                self.addCleanup(shutil.rmtree, Path(prepared['result_path']).parent, True)

    def test_over_bound_refuses_without_persisted_snapshot_or_reservation(self):
        self.refused({'op': 'prepare-dispatch', 'op_id': 'over-reader-bound', 'task_id': 'build-it',
                      'role': 'developer', 'host': 'codex', 'assignment_text': 'x' * (reader.MAX_OBJECT_BYTES + 1)},
                     'invocation-too-large')
        self.assertFalse((tree(self.repo).docs_root / 'cycles' / self.cid / 'invocations').exists())

    def test_snapshot_before_save_crash_reuses_exact_bytes_and_conflicting_op_refuses(self):
        with patch.object(cycle_ops, 'save', side_effect=OSError('save interrupted')):
            code, response = self.op({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it',
                                      'role': 'developer', 'host': 'claude-code', 'assignment_text': fixtures.TEXT})
            self.assertEqual((code, response['error']), (1, 'save interrupted'))
        paths = list((tree(self.repo).docs_root / 'cycles' / self.cid / 'invocations').glob('*.json'))
        self.assertEqual(len(paths), 1)
        original = paths[0].read_bytes()
        code, response = self.op({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it',
                                 'role': 'developer', 'host': 'claude-code', 'assignment_text': 'Changed caller bytes.'})
        self.assertEqual(code, 1, response)
        self.assertEqual(response['errors'][0]['code'], 'invocation-request-conflict')
        prepared = self.prepare()
        self.assertEqual(paths[0].read_bytes(), original)
        self.assertEqual(prepared['invocation'], json.loads(original)['invocation'])
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 1)

    def test_save_before_response_crash_replays_one_reservation(self):
        commit = cycle_ops.commit
        def interrupt(*args, **kwargs):
            commit(*args, **kwargs)
            raise OSError('response interrupted')
        with patch.object(cycle_ops, 'commit', side_effect=interrupt):
            code, response = self.op({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it',
                                      'role': 'developer', 'host': 'claude-code', 'assignment_text': fixtures.TEXT})
            self.assertEqual((code, response['error']), (1, 'response interrupted'))
        prepared = self.prepare()
        self.assertTrue(prepared['replayed'])
        doc = load(self.repo, self.cid)
        self.assertEqual(len(doc['assignments']), 1)
        self.assertEqual(len(cycle_ops.reservations(doc)), 1)

    def test_token_rotation_retains_original_and_derives_only_new_marker(self):
        prepared = self.prepare(assignment_text='Original immutable caller bytes.\r\n')
        original = self.bundle(prepared)
        old_ref = prepared['invocation_snapshot']
        mutate(self.repo, self.cid, 'assignment', id='build-it', resume_token=prepared['delivery_token'], note='fixture host resumes same execution')
        doc = load(self.repo, self.cid)
        entry = doc['assignments'][0]
        self.assertEqual(entry['invocation_history'], [old_ref])
        current = cycle_dispatch.load(tree(self.repo), doc, entry['invocation_snapshot'])
        for key in ('mandatory_message', 'addendum', 'context_message', 'selected', 'native_context', 'sources', 'request'):
            self.assertEqual(current[key], original[key])
        self.assertIn(entry['delivery_token'], current['preamble'])
        self.assertNotIn(prepared['delivery_token'], current['preamble'])
        self.assertEqual(self.page_all('invocation-history:build-it/1/' + old_ref['sha256']),
                         (tree(self.repo).docs_root / old_ref['path']).read_bytes())
        self.assertNotIn('invocation', self.prepare(assignment_text='Original immutable caller bytes.\r\n'))
        self.assertEqual(self.ok({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1})['invocation'], current['invocation'])

    def test_real_same_op_race_retains_one_snapshot_and_reservation(self):
        ctx = multiprocessing.get_context('fork')
        gate, results = ctx.Event(), ctx.Queue()
        request = {'op': 'prepare-dispatch', 'op_id': 'same-op-race-1', 'task_id': 'build-it', 'role': 'developer',
                   'host': 'codex', 'assignment_text': 'Retain this exact concurrent request.'}
        workers = [ctx.Process(target=prepare_worker, args=(self.repo, self.cid, request, gate, results)) for _ in range(2)]
        try:
            for worker in workers: worker.start()
            gate.set()
            observed = [results.get(timeout=30) for _ in workers]
            for worker in workers: worker.join(timeout=10)
            self.assertTrue(all(worker.exitcode == 0 for worker in workers))
            self.assertTrue(all(code == 0 for code, _ in observed), observed)
            self.assertEqual(observed[0][1]['invocation'], observed[1][1]['invocation'])
            self.assertEqual(observed[0][1]['invocation_snapshot'], observed[1][1]['invocation_snapshot'])
            self.assertEqual(len(cycle_ops.reservations(load(self.repo, self.cid))), 1)
        finally:
            for worker in workers:
                if worker.is_alive(): worker.terminate(); worker.join(timeout=5)
            results.close()

    def test_missing_tampered_objects_and_changed_pages_never_return_executable_invocation(self):
        directory, context = self.selected_context()
        with self.selected_scope(directory, context):
            prepared = self.prepare()
            cfg, doc = tree(self.repo), load(self.repo, self.cid)
            item = self.bundle(prepared)['selected'][0]
            path = cfg.docs_root / item['path']
            ref = 'repo:' + path.relative_to(self.repo).as_posix()
            page = reader.read_context(cfg, doc, ref, limit=4)
            self.assertTrue(page['ok'], page)
            original = path.read_bytes()
            for changed in (None, original + b'\nchanged\n'):
                with self.subTest(missing=changed is None):
                    if changed is None: path.unlink()
                    else: path.write_bytes(changed)
                    try:
                        code, response = self.op({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1})
                        self.assertEqual(code, 1)
                        self.assertNotIn('invocation', response)
                        refused = reader.read_context(cfg, doc, ref, offset=page['next_offset'], sha256=page['sha256'])
                        self.assertFalse(refused['ok'])
                        self.assertNotIn('text', refused)
                    finally:
                        path.write_bytes(original)
            snapshot_path = cfg.docs_root / prepared['invocation_snapshot']['path']
            before = snapshot_path.read_bytes()
            snapshot_path.write_bytes(before + b'\n')
            self.refused({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1}, 'invocation-digest-changed')
            refused = reader.read_context(cfg, doc, 'invocation:build-it/1')
            self.assertEqual(refused['error']['code'], 'bound-digest-changed')
            self.assertNotIn('text', refused)

    def test_role_record_and_source_change_refuse_without_replacing_original(self):
        directory, context = self.selected_context()
        with self.selected_scope(directory, context):
            prepared = self.prepare()
            snapshot = self.page_all('invocation:build-it/1')
            role = directory / 'agents/developer.md'
            original = role.read_bytes()
            role.write_bytes(original + b'\nDifferent grants in current role.\n')
            self.refused({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1}, 'invocation-source-changed')
            role.write_bytes(original)
            source = self.repo / 'src/a.py'
            original = source.read_bytes()
            source.write_bytes(b'answer = 999\n')
            self.refused({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1}, 'invocation-source-changed')
            source.write_bytes(original)
            mutate(self.repo, self.cid, 'plan-details', details={'constraints': ['Changed mandatory constraint.']},
                   reason='fixture changes mandatory context')
            self.refused({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1}, 'invocation-record-changed')
            self.assertEqual(snapshot, self.page_all('invocation:build-it/1'))
            self.assertEqual(prepared['invocation_snapshot']['sha256'], digest(snapshot))

    def test_historical_no_snapshot_never_fabricates_original_message(self):
        prepared = self.prepare()
        path = self.record_path()
        raw = json.loads(path.read_text())
        raw['assignments'][0].pop('invocation_snapshot')
        for operation in raw['operations']:
            operation['result'].pop('invocation_snapshot', None)
        path.write_text(json.dumps(raw))
        before = path.read_bytes()
        recovered = self.ok({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1})
        self.assertIn('historical-no-snapshot', recovered['invocation_unavailable'])
        self.assertNotIn('invocation', recovered)
        replay = self.prepare()
        self.assertNotIn('invocation', replay)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(prepared['invocation_snapshot']['sha256'], digest(self.page_all('repo:' +
                         (tree(self.repo).docs_root / prepared['invocation_snapshot']['path']).relative_to(self.repo).as_posix())))

    def test_historical_inline_snapshot_replay_is_byte_identical(self):
        prepared = self.prepare()
        cfg, doc = tree(self.repo), load(self.repo, self.cid)
        ref = prepared['invocation_snapshot']
        path = cfg.docs_root / ref['path']
        bundle = json.loads(path.read_bytes())
        # Retain an older valid inline rendering; recovery must not run today's renderer.
        bundle['context_message'] = '\nHistorical complete inline selected body.\r\n'
        bundle['invocation']['parameters']['prompt'] = bundle['mandatory_message'] + bundle['context_message'] + bundle['preamble']
        data = json.dumps(bundle).encode()
        path.write_bytes(data)
        doc['assignments'][0]['invocation_snapshot']['sha256'] = digest(data)
        for operation in doc['operations']:
            operation['result']['invocation_snapshot']['sha256'] = digest(data)
        self.record_path().write_text(json.dumps(doc))
        with patch.object(cycle_ops, 'build_invocation', side_effect=AssertionError('must not rerender')):
            replay = self.prepare()
        self.assertEqual(replay['invocation'], bundle['invocation'])
        self.assertEqual(path.read_bytes(), data)

    def test_global_wakeup_checks_exact_concurrent_attempt_handle_and_marker(self):
        mutate(self.repo, self.cid, 'task-add', task={'id': 'second-task', 'phase': 'build', 'description': 'other work',
               'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit']})
        first = self.prepare(host='codex')
        second = self.ok({'op': 'prepare-dispatch', 'op_id': 'second-prepare-1', 'task_id': 'second-task',
                          'role': 'developer', 'host': 'codex'})
        for prepared, handle in ((first, 'actual-first-handle'), (second, 'actual-second-handle')):
            self.ok({'op': 'attach-execution', 'op_id': 'attach-' + handle, 'assignment': prepared['assignment'],
                     'attempt': 1, 'handle': handle})
        self.write_result(second)
        observed = self.ok({'op': 'inspect'})['assignments']
        rows = {row['id']: row for row in observed}
        self.assertEqual(rows['build-it']['observation'], 'running-bound')
        self.assertEqual(rows['build-it']['liveness'], 'unknown')
        self.assertEqual(rows['build-it']['wait']['binding']['handle'], 'actual-first-handle')
        self.assertEqual(rows['build-it']['wait']['parameters'], {'timeout_ms': 60000})
        self.assertEqual(rows['second-task']['observation'], 'result-arrived')
        self.assertNotEqual(first['delivery_token'], second['delivery_token'])
        self.assertNotIn('invocation', self.ok({'op': 'dispatch-invocation', 'assignment': 'build-it', 'attempt': 1}))


if __name__ == '__main__':
    unittest.main()
