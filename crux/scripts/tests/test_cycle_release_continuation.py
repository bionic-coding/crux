"""Fixed logical release steps share one simulated native execution, retaining gates."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_hosts
from cycle_workflow import CycleError, RELEASE_LISTS, create, load, mutate
from test_cycle_slice import SliceBase


class ReleaseContinuationTests(SliceBase):
    def setUp(self):
        super().setUp()
        (self.repo / 'tools').mkdir()
        self.descriptor = {'format': 1, 'prep_scope': ['src', 'bionic/log.md'],
            'targets': {'beta': 'private/project', 'official': 'public/project'},
            'commands': {kind: {step: [['uv', 'run', 'tools/release.py', step, '--version', '{version}']]
                               for step, _, _ in steps} for kind, steps in RELEASE_LISTS.items()}}
        self.descriptor['commands']['beta']['beta-and-smoke'] = [
            ['uv', 'run', 'tools/release.py', name, '--version', '{version}'] for name in ('beta', 'smoke')]
        self.descriptor['commands']['official']['official'] = [
            ['uv', 'run', 'tools/release.py', 'official', '--version', '{version}', '--cycle', '{cycle}']]
        self.descriptor_path = self.repo / cycle_hosts.RELEASE_DESCRIPTOR
        self.descriptor_path.write_text(json.dumps(self.descriptor))
        self.git('add', 'tools'); self.git('commit', '-q', '-m', 'Project release descriptor')
        self.cid = create(self.repo, 'release', 'Beta v5.0.4', 'Release the fixed artifact',
                          ['src', 'bionic/log.md'], ['released'], 'builder', 'tester', release_list='beta')['id']
        self.capabilities = {'available': ['read-context', 'write-result', 'source-edit', 'execution-check', 'release-continue'],
                             'observation': 'Simulated host with the explicit narrow native role grant.'}
        self.ledger_path = self.repo / '.git/crux/releases/5.0.4/ledger.json'
        self.ledger = {'version': '5.0.4', 'cycles': {'beta': self.cid, 'official': None},
                       'artifact': None, 'steps': {}, 'authorizations': {}, 'targets': {}}
        self.native_calls = 0

    def start(self):
        with patch.object(cycle_hosts, 'continuation_capability', return_value=True):
            prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'continue-initial-prepare', 'task_id': 'prep',
                'host': 'codex', 'role': 'dev-lead', 'capabilities': self.capabilities,
                'release_continuation': {'version': '5.0.4'}})
        self.native_calls += 1  # The fake host performs this invocation exactly once.
        self.ok({'op': 'attach-execution', 'op_id': 'continue-initial-attach',
                 'assignment': prepared['assignment'], 'attempt': 1, 'handle': 'one-native-host'})
        return prepared

    def ledger_step(self, step):
        names = ['beta', 'smoke'] if step == 'beta-and-smoke' else [step]
        for name in names:
            self.ledger['steps'][name] = {'state': 'passed'}
        if step == 'verify':
            self.ledger['artifact'] = {'stage_sha256': 'a' * 64, 'git_tree': 'b' * 40}
        if step == 'beta-and-smoke':
            self.ledger['authorizations']['beta'] = {'quote': 'I approve the 5.0.4 beta release',
                'repo': 'private/project', 'artifact': dict(self.ledger['artifact'])}
            self.ledger['targets']['beta'] = {'repo': 'private/project', 'tree': 'b' * 40, 'commit': 'c' * 40}
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(self.ledger).encode()
        self.ledger_path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def request(self, current, *, outcome='done', code=0, stop=None):
        entry = next(a for a in load(self.repo, self.cid)['assignments'] if a['id'] == current['assignment'])
        self.write_result(current)
        observation = {'step': entry['task'], 'exit_code': code}
        commits = []
        if entry['task'] == 'prep' and outcome == 'done':
            (self.repo / 'src/a.py').write_text('answer = 2\n')
            self.git('add', 'src/a.py'); self.git('commit', '-q', '-m', 'Release prep\n\nCycle-Task: prep')
            commits = [self.git('rev-parse', 'HEAD')]
        elif outcome == 'done':
            observation['ledger_sha256'] = self.ledger_step(entry['task'])
        request = {'op': 'release-continue', 'op_id': 'continue-step-' + entry['task'],
            'assignment': entry['id'], 'attempt': entry['attempt'], 'delivery_token': current['delivery_token'],
            'handle': 'one-native-host', 'host': 'codex', 'target': 'beta', 'outcome': outcome,
            'step_result': observation, 'commits': commits}
        if stop:
            request['stop'] = stop
        return request

    def through_verify(self):
        current = self.start()
        for _ in range(3):
            current = self.ok(self.request(current))['continuation']
        return current

    def official_live_request(self, live_note='Fixture live check passed'):
        beta_cycle = self.cid
        self.cid = create(self.repo, 'release', 'Official v5.0.4', 'Release the beta artifact',
                          ['src', 'bionic/log.md'], ['released'], 'builder', 'tester', release_list='official')['id']
        self.ledger.update(cycles={'beta': beta_cycle, 'official': None},
            artifact={'stage_sha256': 'a' * 64, 'git_tree': 'b' * 40},
            steps={name: {'state': 'passed'} for name in ('verify', 'beta', 'smoke', 'tag')},
            live_check={'required': True, 'note': live_note})
        self.ledger['authorizations']['beta'] = {'quote': 'I approve the 5.0.4 beta release',
            'repo': 'private/project', 'artifact': dict(self.ledger['artifact'])}
        self.ledger['targets']['beta'] = {'repo': 'private/project', 'tree': 'b' * 40, 'commit': 'c' * 40}
        with patch.object(cycle_hosts, 'continuation_capability', return_value=True):
            current = self.ok({'op': 'prepare-dispatch', 'op_id': 'official-initial-prepare',
                'task_id': 'live-check-and-go-ahead', 'host': 'codex', 'role': 'dev-lead',
                'capabilities': self.capabilities, 'release_continuation': {'version': '5.0.4'}})
        self.ok({'op': 'attach-execution', 'op_id': 'official-initial-attach',
                 'assignment': current['assignment'], 'attempt': 1, 'handle': 'one-native-host'})
        request = self.request(current)
        request['target'] = 'official'
        return request

    def test_official_successor_allows_binding_created_by_publish_command(self):
        request = self.official_live_request()
        first = self.ok(request)
        self.assertEqual(first['continuation']['task'], 'official')
        self.assertEqual(self.ok(request)['continuation'], first['continuation'])
        self.assertIsNone(self.ledger['cycles']['official'])

    def test_live_check_and_go_ahead_proceeds_with_a_required_check_and_no_note(self):
        """The official publish records the owner's go-ahead as the attestation, so this step no longer refuses."""
        request = self.official_live_request(live_note=None)
        first = self.ok(request)
        self.assertEqual(first['continuation']['task'], 'official')
        self.assertNotIn('continuation_unavailable', first)

    def test_official_successor_rejects_another_cycle_binding(self):
        request = self.official_live_request()
        self.ok(request)
        self.ledger['cycles']['official'] = 'CYC-9999'
        self.ledger_path.write_text(json.dumps(self.ledger))
        replay = self.ok(request)
        self.assertNotIn('continuation', replay)
        self.assertIn('normal recovery', replay['continuation_unavailable'])

    def test_official_record_replay_requires_published_cycle_binding(self):
        live_request = self.official_live_request()
        current = self.ok(live_request)['continuation']
        self.ledger['cycles']['official'] = self.cid
        self.ledger['authorizations']['official'] = {'quote': 'I approve the 5.0.4 official release',
            'repo': 'public/project', 'artifact': dict(self.ledger['artifact'])}
        self.ledger['targets']['official'] = {'repo': 'public/project', 'tree': 'b' * 40, 'commit': 'd' * 40}
        publish_request = self.request(current)
        publish_request['target'] = 'official'
        self.assertEqual(self.ok(publish_request)['continuation']['task'], 'record')
        self.ledger['cycles']['official'] = None
        self.ledger_path.write_text(json.dumps(self.ledger))
        replay = self.ok(publish_request)
        self.assertNotIn('continuation', replay)
        self.assertIn('normal recovery', replay['continuation_unavailable'])

    def test_official_publish_before_delivery_replay_checks_published_facts(self):
        request = self.official_live_request()
        self.ok(request)
        # The command completed, while its logical attempt still awaits delivery.
        self.ledger['steps']['official'] = {'state': 'passed'}
        self.ledger['authorizations']['official'] = {'quote': 'I approve the 5.0.4 official release',
            'repo': 'public/project', 'artifact': dict(self.ledger['artifact'])}
        self.ledger['targets']['official'] = {'repo': 'public/project', 'tree': 'b' * 40, 'commit': 'd' * 40}
        self.ledger_path.write_text(json.dumps(self.ledger))
        missing_binding = self.ok(request)
        self.assertNotIn('continuation', missing_binding, 'published official needs its cycle binding before delivery')
        self.ledger['cycles']['official'] = self.cid
        self.ledger['targets']['official']['repo'] = 'another/project'
        self.ledger_path.write_text(json.dumps(self.ledger))
        changed_target = self.ok(request)
        self.assertNotIn('continuation', changed_target, 'published target must be checked before delivery')
        self.ledger['targets']['official']['repo'] = 'public/project'
        self.ledger['authorizations']['official']['quote'] = ''
        self.ledger_path.write_text(json.dumps(self.ledger))
        changed_authorization = self.ok(request)
        self.assertNotIn('continuation', changed_authorization, 'published authorization must be checked before delivery')
        self.ledger['authorizations']['official']['quote'] = 'I approve the 5.0.4 official release'
        self.ledger_path.write_text(json.dumps(self.ledger))
        self.assertEqual(self.ok(request)['continuation']['task'], 'official')
        self.ledger['steps']['official'] = {'state': 'pending', 'attempts': [{'outcome': 'interrupted'}]}
        self.ledger['cycles']['official'] = None
        self.ledger['targets'].pop('official')
        self.ledger['authorizations'].pop('official')
        self.ledger_path.write_text(json.dumps(self.ledger))
        attempted = self.ok(request)
        self.assertNotIn('continuation', attempted, 'an interrupted publication attempt cannot regain an unbound exception')

    def test_official_failed_publish_before_delivery_stops_replay_with_valid_facts(self):
        request = self.official_live_request()
        self.ok(request)
        self.ledger['cycles']['official'] = self.cid
        self.ledger['authorizations']['official'] = {'quote': 'I approve the 5.0.4 official release',
            'repo': 'public/project', 'artifact': dict(self.ledger['artifact'])}
        self.ledger['targets']['official'] = {'repo': 'public/project', 'tree': 'b' * 40, 'commit': 'd' * 40}
        for state in ('interrupted', 'failed'):
            with self.subTest(state=state):
                self.ledger['steps']['official'] = {'state': state, 'attempts': [{'outcome': state}]}
                self.ledger_path.write_text(json.dumps(self.ledger))
                replay = self.ok(request)
                self.assertNotIn('continuation', replay, 'failure stops continuation even with valid published facts')
                self.assertIn('normal recovery', replay['continuation_unavailable'])

    def assert_failed_current_step_stops_replay(self, task, command):
        current = self.start()
        while current['assignment'] != task:
            request = self.request(current)
            current = self.ok(request)['continuation']
        if task == 'beta-and-smoke':
            self.ledger_step(task)  # A successful beta cannot hide the smoke failure.
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        for state in ('failed', 'interrupted'):
            with self.subTest(command=command, state=state):
                self.ledger['steps'][command] = {'state': state, 'attempts': [{'outcome': state}]}
                self.ledger_path.write_text(json.dumps(self.ledger))
                replay = self.ok(request)
                self.assertNotIn('continuation', replay, 'the current logical command failure must stop replay')
                self.assertIn('normal recovery', replay['continuation_unavailable'])

    def test_failed_current_smoke_stops_replay_with_valid_beta_facts(self):
        self.assert_failed_current_step_stops_replay('beta-and-smoke', 'smoke')

    def test_failed_current_prepare_stops_replay_before_artifact_exists(self):
        self.assert_failed_current_step_stops_replay('prepare', 'prepare')

    def test_failed_current_verify_stops_replay_before_artifact_exists(self):
        self.assert_failed_current_step_stops_replay('verify', 'verify')

    def test_failed_current_tag_stops_replay_with_valid_beta_facts(self):
        self.assert_failed_current_step_stops_replay('tag', 'tag')

    def test_failed_current_record_stops_replay_with_valid_beta_facts(self):
        self.assert_failed_current_step_stops_replay('record', 'record')

    def test_six_steps_use_one_native_dispatch_and_attach(self):
        current = self.start()
        for step, _, _ in RELEASE_LISTS['beta']:
            request = self.request(current)
            result = self.ok(request)
            if step != 'record':
                current = result['continuation']
                self.assertEqual(current['action'], 'continue-in-same-host')
                self.assertEqual(current['handle'], 'one-native-host')
                self.assertNotIn('invocation', result)
        doc = load(self.repo, self.cid)
        self.assertEqual(self.native_calls, 1)
        self.assertEqual(sum(e['action'] == 'attach-execution' for e in doc['history']), 1)
        self.assertEqual(sum(e['action'] == 'prepare-dispatch' for e in doc['history']), 1)
        self.assertEqual([t['status'] for t in doc['plan']['tasks']], ['done'] * 6)
        self.assertEqual(len(doc['assignments']), 6)
        self.assertEqual(len({a['delivery_token'] for a in doc['assignments']}), 6)
        self.assertEqual(doc['status'], 'completed')

    def test_replay_resumes_bookkeeping_without_repeating_external_step(self):
        current = self.start()
        request = self.request(current)
        first = self.ok(request)
        replay = self.ok(request)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['continuation'], replay['continuation'])
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 2)

    def test_replay_with_changed_descriptor_withholds_context_and_retains_delivery(self):
        request = self.request(self.start())
        first = self.ok(request)
        retained = load(self.repo, self.cid)['assignments'][0]['delivery'].copy()
        self.descriptor['prep_scope'].append('README.md')
        self.descriptor_path.write_text(json.dumps(self.descriptor))
        replay = self.ok(request)
        self.assertTrue(replay['replayed'])
        self.assertFalse('continuation' in replay, 'changed descriptor must withhold executable replay context')
        self.assertIn('normal recovery', replay['continuation_unavailable'])
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['delivery'], retained)
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 2)
        self.assertIn('continuation', first)

    def test_replay_with_changed_pinned_artifact_withholds_publish_context(self):
        current = self.start()
        for _ in range(3):
            request = self.request(current)
            current = self.ok(request)['continuation']
        self.ledger['artifact']['stage_sha256'] = 'd' * 64
        self.ledger_path.write_text(json.dumps(self.ledger))
        replay = self.ok(request)
        self.assertTrue(replay['replayed'])
        self.assertFalse('continuation' in replay, 'changed artifact must withhold executable replay context')
        self.assertIn('normal recovery', replay['continuation_unavailable'])
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 4)

    def test_replay_with_changed_role_withholds_context(self):
        request = self.request(self.start())
        self.ok(request)
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory)
            (plugin / 'agents').mkdir()
            role = cycle_hosts.PLUGIN_ROOT / 'agents/dev-lead.md'
            (plugin / 'agents/dev-lead.md').write_bytes(role.read_bytes() + b'\nChanged grant fixture.\n')
            with patch.object(cycle_hosts, 'PLUGIN_ROOT', plugin):
                replay = self.ok(request)
        self.assertFalse('continuation' in replay, 'changed native grant must withhold replay context')
        self.assertIn('normal recovery', replay['continuation_unavailable'])

    def test_replay_with_changed_published_target_withholds_tag_context(self):
        current = self.start()
        for _ in range(4):
            request = self.request(current)
            current = self.ok(request)['continuation']
        self.ledger['targets']['beta']['repo'] = 'public/project'
        self.ledger_path.write_text(json.dumps(self.ledger))
        replay = self.ok(request)
        self.assertFalse('continuation' in replay, 'changed published target must withhold tag context')
        self.assertIn('normal recovery', replay['continuation_unavailable'])

    def test_stale_token_wrong_handle_and_target_refuse(self):
        current = self.start()
        request = self.request(current)
        for field, value in [('delivery_token', '0' * 32), ('handle', 'another-host'), ('target', 'official')]:
            self.refused({**request, field: value}, 'release-continuation-mismatch')

    def test_old_replay_never_releases_a_paused_or_rotated_next_task(self):
        current = self.start()
        request = self.request(current)
        self.ok(request)
        mutate(self.repo, self.cid, 'pause', reason='owner stopped the release')
        paused = self.ok(request)
        self.assertNotIn('continuation', paused)
        self.assertEqual(paused['continuation_unavailable'], 'cycle-not-active')
        mutate(self.repo, self.cid, 'resume', reason='owner resumed the same release')
        resumed = self.ok(request)
        self.assertNotIn('continuation', resumed)
        self.assertIn('token-rotated', resumed['continuation_unavailable'])

    def test_failed_command_and_host_denial_stop_without_successor(self):
        current = self.start()
        request = self.request(current, outcome='blocked', code=1, stop='outward-act')
        result = self.ok(request)
        self.assertTrue(result['stopped'])
        self.assertNotIn('continuation', result)
        self.assertEqual(len(load(self.repo, self.cid)['assignments']), 1)
        self.assertEqual(load(self.repo, self.cid)['plan']['tasks'][1]['status'], 'pending')

    def test_nonzero_result_cannot_claim_success(self):
        current = self.start()
        request = self.request(current)
        request['step_result']['exit_code'] = 1
        self.refused(request, 'release-step-not-passed')

    def test_changed_artifact_needs_normal_recovery_and_new_words(self):
        current = self.through_verify()
        request = self.request(current)
        self.ledger['artifact']['stage_sha256'] = 'd' * 64
        request['step_result']['ledger_sha256'] = self.ledger_step('beta-and-smoke')
        self.refused(request, 'release-artifact-changed')

    def test_beta_quote_cannot_cover_another_target(self):
        current = self.through_verify()
        request = self.request(current)
        self.ledger['authorizations']['beta']['repo'] = 'public/project'
        raw = json.dumps(self.ledger).encode(); self.ledger_path.write_bytes(raw)
        request['step_result']['ledger_sha256'] = hashlib.sha256(raw).hexdigest()
        self.refused(request, 'release-authorization-unverified')

    def test_changed_descriptor_and_owner_pause_stop(self):
        current = self.start()
        request = self.request(current)
        self.descriptor['prep_scope'].append('README.md')
        self.descriptor_path.write_text(json.dumps(self.descriptor))
        self.refused(request, 'release-continuation-stale')
        mutate(self.repo, self.cid, 'pause', reason='owner requested stop')
        self.refused(request, 'cycle-paused')

    def test_unknown_native_grant_keeps_normal_dispatch_available(self):
        code, result = self.op({'op': 'prepare-dispatch', 'op_id': 'continue-unknown-grant', 'task_id': 'prep',
             'host': 'codex', 'role': 'dev-lead', 'release_continuation': {'version': '5.0.4'}})
        self.assertEqual(code, 1, result)
        self.assertIn('normal dispatch', str(result))
        prepared = self.ok({'op': 'prepare-dispatch', 'op_id': 'continue-normal-fallback', 'task_id': 'prep',
                           'host': 'codex', 'role': 'dev-lead'})
        self.assertIn('invocation', prepared)
        self.assertIn('read-context', prepared['capability_status']['unknown'])

    def test_known_reader_gap_refuses_before_native_invocation(self):
        self.refused({'op': 'prepare-dispatch', 'op_id': 'continue-reader-unavailable', 'task_id': 'prep',
            'host': 'codex', 'role': 'dev-lead', 'capabilities': {'unavailable': ['read-context'],
            'observation': 'The native role has no callable reader.'}}, 'role-capability-unavailable')

    def test_frozen_scope_omission_refuses_before_cycle_allocation(self):
        before = set((self.repo / 'bionic/cycles').iterdir())
        with self.assertRaisesRegex(CycleError, 'mandatory paths: bionic/log.md'):
            create(self.repo, 'release', 'Beta', 'Release', ['src'], ['released'], 'builder', 'tester', release_list='beta')
        self.assertEqual(set((self.repo / 'bionic/cycles').iterdir()), before)

    def test_original_queue_capture_completes_descriptor_scope(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cycle.main(['--repo-root', str(self.repo), 'queue', 'add', '--title', 'Beta v5.0.4',
                '--outcome', 'Release', '--type', 'release', '--scope', 'src', '--acceptance', 'released'])
        self.assertEqual(code, 0, out.getvalue())
        import cycle_queue
        from cycle_workflow import tree
        doc = cycle_queue.read_queue(tree(self.repo))
        self.assertEqual(doc['items'][0]['scope'], ['src', 'bionic/log.md'])

    def test_direct_queue_capture_and_frozen_start_preflight_are_atomic(self):
        import cycle_queue
        from cycle_workflow import tree
        cycle_queue.add(self.repo, 'Beta v5.0.4', 'Release', 'release', ['src'], ['released'])
        self.assertEqual(cycle_queue.read_queue(tree(self.repo))['items'][0]['scope'], ['src', 'bionic/log.md'])
        cycle_queue.remove(self.repo, 'Q-0001')
        raw = self.descriptor_path.read_bytes()
        self.descriptor_path.unlink()
        cycle_queue.add(self.repo, 'Beta v5.0.4', 'Release', 'release', ['src'], ['released'])
        cycle_queue.authorize(self.repo, 'next', 'I approve beta v5.0.4', '2026-11-01')
        self.descriptor_path.write_bytes(raw)
        queue_path = self.repo / 'bionic/queue/cycles.yaml'
        before = queue_path.read_bytes()
        cycles = set((self.repo / 'bionic/cycles').iterdir())
        with self.assertRaisesRegex(CycleError, 'mandatory paths'):
            cycle_queue.start_next(self.repo)
        self.assertEqual(queue_path.read_bytes(), before)
        self.assertEqual(set((self.repo / 'bionic/cycles').iterdir()), cycles)
