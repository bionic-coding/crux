"""Vertical slice of the typed cycle operations: one task end to end on a version-3 record.

inspect -> prepare-dispatch (claude-code) -> attach-execution -> deliver -> finish, through
`cycle.py op`, with no classification and no decisions transport. Claude Code's default mode is
`blocking`, which has no handle to attach: the default path is prepare-dispatch -> deliver -> finish,
and the `background` mode keeps the attach step."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle
import cycle_hosts
import cycle_ops
from cycle_workflow import create, load, mutate, validate, CycleError
from test_evidence import execute
from _classifier_isolation import isolate_classifier
from cycle_historical import rename_phase


def shared_interpreter_env():
    """The environment for a shipped script the test starts on `sys.executable`.

    It carries the test's own import path, so the child resolves the packages the test resolved (httpx, yaml)
    even when the interpreter is a base one and the packages came from an overlay the child would not see."""
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(p for p in [*sys.path, env.get('PYTHONPATH', '')] if p)
    return env

SCRIPTS = Path(__file__).resolve().parents[1]
TEXT = "Implement the answer.\nOutcome: src/a.py returns 2.\nEvidence: unit check passes.\nConstraint: edit only src/a.py; it's small.\n"


def version_two(path):
    """Rewrite the cycle record at `path` as a genuine version-2 record and validate it.

    Strips every version-3 field (revision, operations, results_dir, phase_names, the assignment host, mode, base and
    delivery, the history revision stamps) and sets schema_version 2. Other test modules import this
    helper when a test asserts version-2 behavior on purpose."""
    raw = json.loads(Path(path).read_text())
    for key in ('revision', 'operations', 'results_dir', 'phase_names'):
        raw.pop(key, None)
    for entry in raw.get('assignments', []):
        for key in (*cycle_ops.ASSIGNMENT_V3_FIELDS, 'mode', 'delivery_token', 'previous_results', 'invocation_snapshot', 'invocation_history',
                    'execution', 'execution_history', 'execution_started'):
            entry.pop(key, None)
    for entry in raw['history']:
        entry.pop('revision', None)
    raw['schema_version'] = 2
    rename_phase(raw, 'verify', 'test')  # a version-2 record predates the Verify name
    validate(raw)
    Path(path).write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')
    return raw


class SliceBase(unittest.TestCase):
    def setUp(self):
        isolate_classifier(self)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        env = patch.dict(os.environ, {'CRUX_TEST_EVIDENCE_STORE': str(self.repo.parent / (self.repo.name + '-evidence'))})
        env.start(); self.addCleanup(env.stop)
        (self.repo / 'bionic').mkdir()
        (self.repo / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        (self.repo / 'bionic/objectives.md').write_text('Mission: useful changes.\n')
        (self.repo / 'src').mkdir(); (self.repo / 'src/a.py').write_text('answer = 1\n')
        self.git('init', '-q'); self.git('config', 'user.email', 't@example.com'); self.git('config', 'user.name', 't')
        (self.repo / '.gitignore').write_text('*.lock\n__pycache__/\nbionic/\n')
        self.git('add', '.gitignore', 'src'); self.git('commit', '-q', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.cid = self.fixture()
        self.addCleanup(self.cleanup_results)

    def cleanup_results(self):
        try:
            directory = json.loads(self.record_path().read_text()).get('results_dir')
        except (OSError, ValueError):
            return
        if directory and Path(directory).is_dir():
            for path in Path(directory).iterdir():
                path.unlink()
            Path(directory).rmdir()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True).stdout.strip()

    def record_path(self, cid=None):
        return self.repo / f'bionic/cycles/{cid or self.cid}/cycle.json'

    def fixture(self, version=3):
        """A quick-fix cycle with one Build task as a version-2 or version-3 record.

        `create` writes version 3 with revision 1; the task-add makes it revision 2. The fixture normalizes
        both versions to the shape it always had: version 3 sits at revision 1 with unstamped history."""
        doc = create(self.repo, 'quick-fix', 'Answer', 'Return 2', ['src'], ['answer is 2'], 'builder', 'tester')
        mutate(self.repo, doc['id'], 'task-add', task={'id': 'build-it', 'phase': 'build', 'description': 'set the answer',
                                                     'depends_on': [], 'status': 'pending', 'expected_evidence': ['commit']})
        path = self.record_path(doc['id'])
        raw = version_two(path)  # a genuine version-2 record carries no phase_names
        if version == 3:
            # Keep the revision at 1 and the history unstamped, as the fixture has always been.
            raw.update(schema_version=3, phase_names='verify', **{**cycle_ops.v3_fields(), 'revision': 1})
            for entry in raw.get('assignments', []):
                entry.update({k: None for k in cycle_ops.ASSIGNMENT_V3_FIELDS})
            rename_phase(raw, 'test', 'verify')
            validate(raw)
            path.write_text(json.dumps(raw, indent=2, sort_keys=True) + '\n')
        return doc['id']

    def op(self, request, cid=None, form='inline'):
        """Run `cycle.py op` in process; return (exit code, response)."""
        argv = ['--repo-root', str(self.repo), 'op', cid or self.cid]
        stdin = None
        if form == 'inline':
            argv += ['--json', json.dumps(request)]
        elif form == 'stdin':
            argv += ['--json', '-']; stdin = io.StringIO(json.dumps(request))
        else:
            path = self.repo.parent / (self.repo.name + '-request.json'); path.write_text(json.dumps(request))
            self.addCleanup(path.unlink); argv += ['--file', str(path)]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch('sys.stdin', stdin or sys.stdin):
            code = cycle.main(argv)
        return code, json.loads(out.getvalue())

    def ok(self, request, **kw):
        code, response = self.op(request, **kw)
        self.assertEqual(code, 0, response); self.assertTrue(response['ok'])
        return response

    def refused(self, request, *codes, **kw):
        before = self.record_path(kw.get('cid')).read_bytes()
        code, response = self.op(request, **kw)
        self.assertEqual(code, 1, response); self.assertFalse(response['ok'])
        self.assertEqual(sorted(e['code'] for e in response['errors']), sorted(codes))
        self.assertEqual(self.record_path(kw.get('cid')).read_bytes(), before, 'a refusal wrote the record')
        return response

    def prepare(self, op_id='prep-0001', **extra):
        return self.ok({'op': 'prepare-dispatch', 'op_id': op_id, 'task_id': 'build-it', 'role': 'developer',
                        'host': 'claude-code', 'assignment_text': TEXT, **extra})

    def work(self, prepared, *, marker=True, trailer=True, body='answer = 2\n'):
        """Act as the dispatched developer: commit with the trailer and write the result file."""
        (self.repo / 'src/a.py').write_text(body)
        self.git('add', 'src/a.py')
        self.git('commit', '-q', '-m', 'set the answer' + ('\n\nCycle-Task: build-it' if trailer else ''))
        sha = self.git('rev-parse', 'HEAD')
        self.write_result(prepared, marker=marker)
        return sha

    def checkpoint_work(self, prepared, *, marker=True, body='answer = 2\n'):
        """Opt in to the supported clean-start and before-commit proof for recovery fixtures."""
        base = {'op': 'execution-check', 'assignment': prepared['assignment'], 'attempt': prepared['attempt']}
        self.ok({**base, 'op_id': 'fixture-clean-start-1'})
        (self.repo / 'src/a.py').write_text(body)
        self.ok({**base, 'op_id': 'fixture-precommit-2', 'edited_paths': ['src/a.py']})
        return self.work(prepared, marker=marker, body=body)

    def write_result(self, prepared, *, marker=True, assignment=None, attempt=None):
        a, n = assignment or prepared['assignment'], attempt or prepared['attempt']
        lines = [f'Assignment: {a}', f'Attempt: {n}', '', 'Outcome: DONE. Answer set to 2.']
        if marker:
            lines.append(cycle_hosts.marker(a, n, prepared.get('delivery_token')))
        Path(prepared['result_path']).write_text('\n'.join(lines) + '\n\n')

    def to_reflect(self):
        """Low-level Test and Review with a real receipt and an independent review."""
        cid = self.cid
        mutate(self.repo, cid, 'advance')
        mutate(self.repo, cid, 'checks', checks=['unit'])
        mutate(self.repo, cid, 'coverage', coverage={'affected': ['the answer'], 'checks': [{'check_id': 'unit', 'rationale': 'reads src/a.py'}],
                                                     'not_selected': 'no other behavior'})
        decl = {'check_id': 'unit', 'command': [sys.executable, '-c', "from pathlib import Path; assert Path('src/a.py').read_text() == 'answer = 2\\n'"],
                'inputs': ['src'], 'environment': []}
        result = execute(self.repo, decl)
        mutate(self.repo, cid, 'evidence', check_id='unit', evidence_id=result['evidence']['id'], use=result['action'])
        mutate(self.repo, cid, 'advance')
        mutate(self.repo, cid, 'review', report={'reviewer': 'independent', 'scope': ['src'], 'evidence': [result['evidence']['id']],
                                                 'blocking': [], 'advisory': [], 'cosmetic': [], 'verdict': 'approve', 'rationale': 'reviewed the change'})
        return mutate(self.repo, cid, 'advance')


class EndToEndTests(SliceBase):
    def test_one_task_end_to_end(self):
        """The background mode: the host returns an agentId while the child runs, and the caller attaches it."""
        seen = self.ok({'op': 'inspect', 'host': 'claude-code'})
        self.assertEqual((seen['revision'], seen['phase'], seen['head']), (1, 'build', self.base))
        dispatch = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'prepare-dispatch']
        self.assertEqual(dispatch[0]['request'], {'op': 'prepare-dispatch', 'task_id': 'build-it', 'host': 'claude-code'})
        self.assertEqual(dispatch[0]['caller_fills'], ['op_id'])

        prepared = self.prepare(mode='background')
        self.assertEqual((prepared['assignment'], prepared['attempt'], prepared['base'], prepared['revision']), ('build-it', 1, self.base, 2))
        invocation = prepared['invocation']
        self.assertEqual((invocation['tool'], invocation['parameters']['subagent_type']), ('Agent', 'crux:developer'))
        self.assertIs(invocation['parameters']['run_in_background'], True)
        self.assertEqual(invocation['attach']['request'], {'op': 'attach-execution', 'assignment': 'build-it', 'attempt': 1})
        self.assertEqual(invocation['wait']['parameters']['run_in_background'], True)
        doc = load(self.repo, self.cid)
        entry = doc['assignments'][0]
        self.assertEqual((entry['state'], entry['host'], entry['base'], entry['agent']), ('reserved', 'claude-code', self.base, None))
        self.assertEqual(doc['plan']['tasks'][0]['status'], 'active')
        self.assertTrue(Path(prepared['result_path']).parent.is_dir())

        attached = self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'agent-abc'})
        self.assertEqual((attached['changed'], attached['revision']), (True, 3))
        seen = self.ok({'op': 'inspect'})
        self.assertEqual((seen['assignments'][0]['observation'], seen['assignments'][0]['liveness']), ('running-bound', 'unknown'))

        sha = self.work(prepared)
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['assignments'][0]['observation'], 'result-arrived')
        self.assertIn({'request': {'op': 'deliver', 'assignment': 'build-it', 'attempt': 1}, 'caller_fills': ['op_id', 'outcome'],
                       'purpose': 'record the arrived result; add commits, evidence, stage and note as the report states'}, seen['actions'])

        delivered = self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done',
                             'commits': [sha], 'stage': 'integrated'})
        self.assertEqual((delivered['status'], delivered['untrailered_commits']), ('done', []))
        retained = self.repo / 'bionic' / delivered['retained']
        self.assertEqual(retained.read_bytes(), Path(prepared['result_path']).read_bytes())
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['plan']['tasks'][0]['commits'], [sha])
        self.assertEqual(doc['assignments'][0]['delivery']['outcome'], 'done')

        self.to_reflect()
        seen = self.ok({'op': 'inspect'})
        self.assertEqual(seen['phase'], 'reflect'); self.assertEqual(seen['unmet']['completion'], [])
        finish = [a for a in seen['actions'] if a.get('request', {}).get('op') == 'finish'][0]
        self.assertEqual(finish['caller_fills'], ['op_id', 'lessons', 'remaining'])
        done = self.ok({**finish['request'], 'op_id': 'finish-001', 'lessons': ['typed operations carried the bookkeeping'], 'remaining': ['none']})
        self.assertEqual((done['status'], done['completion']['tip']), ('completed', sha))
        doc = load(self.repo, self.cid)
        self.assertEqual(doc['status'], 'completed'); self.assertEqual(doc['completion']['commits'], [sha])
        self.assertIn('Delivered tasks: build-it', doc['reflection']['outcome'])
        self.assertFalse(Path(prepared['result_path']).exists(), 'finish leaves the attempt file')
        self.assertFalse(Path(prepared['result_path']).parent.exists(), 'finish leaves the result directory')
        self.assertEqual([op['op'] for op in doc['operations']], ['prepare-dispatch', 'attach-execution', 'deliver', 'finish'])
        # Low-level saves between deliver and finish increment the revision too.
        revisions = [op['revision'] for op in doc['operations']]
        self.assertEqual(revisions[:3], [2, 3, 4]); self.assertGreater(revisions[3], 4)
        self.assertEqual(revisions[3], doc['revision'])
        self.assertEqual([e.get('revision') for e in doc['history']], sorted(e.get('revision') for e in doc['history']))
        # A retry of finish after it succeeded replays rather than refusing.
        replay = self.ok({**finish['request'], 'op_id': 'finish-001', 'lessons': ['typed operations carried the bookkeeping'], 'remaining': ['none']})
        self.assertEqual((replay['replayed'], replay['changed']), (True, False))

    def test_default_blocking_mode_reserves_then_delivers_with_no_attach(self):
        prepared = self.prepare()
        invocation = prepared['invocation']
        self.assertEqual((invocation['mode'], invocation['tool']), ('blocking', 'Agent'))
        self.assertNotIn('run_in_background', invocation['parameters'])
        self.assertEqual(invocation['wait']['mechanism'], 'blocking-dispatch')
        self.assertIsNone(invocation['handle'])
        self.assertTrue(invocation['attach']['conditional'])
        self.assertEqual(load(self.repo, self.cid)['assignments'][0]['mode'], 'blocking')
        seen = self.ok({'op': 'inspect'})
        self.assertEqual((seen['assignments'][0]['observation'], seen['assignments'][0]['recovery']),
                         ('reserved-unbound', ['await-marker', 'deliver', 'mark-lost']))
        self.assertNotIn('attach-execution', [a['request']['op'] for a in seen['actions'] if 'request' in a])
        sha = self.work(prepared)
        self.assertEqual(self.ok({'op': 'inspect'})['assignments'][0]['observation'], 'result-arrived')
        delivered = self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [sha]})
        self.assertEqual(delivered['status'], 'done')
        self.assertEqual([op['op'] for op in load(self.repo, self.cid)['operations']], ['prepare-dispatch', 'deliver'])

    def test_an_agent_id_without_a_final_report_is_attached_and_awaited(self):
        self.prepare()
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'agent-abc'})
        view = self.ok({'op': 'inspect'})['assignments'][0]
        self.assertEqual((view['observation'], view['mode'], view['handle']), ('running-bound', 'blocking', 'agent-abc'))
        self.assertEqual((view['wait']['mechanism'], view['wait']['tool']), ('background-command', 'Bash'))
        # A handle is bound, so a returned call is no longer evidence the child ended.
        before = self.record_path().read_bytes()
        code, response = self.op({'op': 'mark-lost', 'op_id': 'lost-0001', 'assignment': 'build-it', 'attempt': 1, 'note': 'quoted',
                                  'evidence': {'kind': 'blocking-returned', 'detail': 'the Agent result carried the final-report'}})
        self.assertEqual((code, [e['code'] for e in response['errors']]), (1, ['not-affirmative']))
        self.assertEqual(self.record_path().read_bytes(), before)
        self.ok({'op': 'mark-lost', 'op_id': 'lost-0002', 'assignment': 'build-it', 'attempt': 1, 'note': 'host status quoted',
                 'evidence': {'kind': 'terminal-status', 'detail': 'failed'}})

    def test_a_rejected_background_flag_is_recovered_by_a_blocking_second_attempt(self):
        """The host rejects `run_in_background` before any execution exists: mark-lost quotes the
        invalid-parameters refusal, and attempt 2 in blocking mode spends one attempt, not a pause."""
        self.prepare(mode='background')
        self.ok({'op': 'mark-lost', 'op_id': 'lost-0001', 'assignment': 'build-it', 'attempt': 1,
                 'note': 'the Agent call was rejected: run_in_background is not a parameter',
                 'evidence': {'kind': 'dispatch-refusal', 'detail': 'invalid-parameters'}})
        again = self.prepare(op_id='prep-0002', assignment='build-it', mode='blocking')
        self.assertEqual((again['assignment'], again['attempt'], again['invocation']['mode']), ('build-it', 2, 'blocking'))
        doc = load(self.repo, self.cid)
        self.assertEqual([(a['attempt'], a['state'], a['mode']) for a in doc['assignments'] if a['id'] == 'build-it'][-1], (2, 'reserved', 'blocking'))
        self.assertEqual([(r['attempt'], r['mode']) for r in cycle_ops.reservations(doc, 'build-it')], [(1, 'background'), (2, 'blocking')],
                         'attempt 1 keeps the mode it was reserved in')
        self.assertEqual(doc['status'], 'active', 'a rejected flag is not a pause')

    def test_request_forms(self):
        self.assertEqual(self.ok({'op': 'inspect'}, form='stdin')['phase'], 'build')
        self.assertEqual(self.ok({'op': 'inspect'}, form='file')['phase'], 'build')
        out = subprocess.run([sys.executable, str(SCRIPTS / 'cycle.py'), '--repo-root', str(self.repo), '--compact', 'op', self.cid,
                              '--json', json.dumps({'op': 'inspect'})], capture_output=True, text=True, cwd=SCRIPTS, env=shared_interpreter_env())
        self.assertEqual(out.returncode, 0, out.stderr); self.assertEqual(len(out.stdout.strip().splitlines()), 1)
        self.assertTrue(json.loads(out.stdout)['ok'])
        code, response = self.op({'op': 'inspect'}, form='inline')
        self.assertEqual(code, 0)

    def test_inline_apostrophe_and_newline(self):
        text = "It's the owner's work.\nSecond line."
        argv = ['--repo-root', str(self.repo), 'op', self.cid, '--json',
                '{"op":"prepare-dispatch","op_id":"inline-01","task_id":"build-it","role":"developer","host":"claude-code","assignment_text":"It\\u0027s the owner\\u0027s work.\\nSecond line."}']
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cycle.main(argv), 0)
        prompt = json.loads(out.getvalue())['invocation']['parameters']['prompt']
        self.assertIn('Optional caller addendum', prompt)
        self.assertIn(text, prompt)


class InvocationTests(SliceBase):
    def test_prompt_is_mandatory_assignment_then_optional_addendum_then_engine_facts(self):
        prepared = self.prepare()
        prompt = prepared['invocation']['parameters']['prompt']
        self.assertTrue(prompt.startswith('Mandatory assignment'))
        self.assertIn(TEXT, prompt)
        facts = prompt[prompt.index('Engine facts for this attempt'):]
        for expected in (str(self.repo / 'bionic/objectives.md'), prepared['result_path'], self.base, 'Assignment: build-it', 'Attempt: 1',
                         'Result-End: build-it/1', 'Cycle-Task: build-it'):
            self.assertIn(expected, facts)
        raw = self.record_path().read_text()
        self.assertNotIn('Implement the answer', raw)
        self.assertNotIn('Implement the answer', json.dumps(load(self.repo, self.cid)['operations']))

    def test_second_attempt_lists_earlier_task_commits(self):
        prepared = self.prepare()
        sha = self.checkpoint_work(prepared, marker=False)
        self.ok({'op': 'mark-lost', 'op_id': 'fixture-typed-loss-3', 'assignment': prepared['assignment'], 'attempt': 1,
                 'evidence': {'kind': 'owner-confirmation', 'detail': 'Fixture owner confirms execution terminated'},
                 'note': 'Offline fixture host termination.'})
        again = self.prepare(op_id='prep-0002', assignment='build-it')
        self.assertEqual((again['assignment'], again['attempt'], again['base']), ('build-it', 2, self.base))
        self.assertIn(sha, again['invocation']['parameters']['prompt'])

    def test_adapter_role_names_and_wait(self):
        adapter = cycle_hosts.adapter('claude-code')
        self.assertEqual([adapter.role_name(r) for r in ('developer', 'reviewer')], ['crux:developer', 'crux:reviewer'])
        wait = adapter.wait(repo_root=self.repo, result_path='/tmp/x.md', assignment='a', attempt=1, mode=adapter.modes['background'])
        self.assertNotIn('windows', wait)
        self.assertEqual((wait['window_seconds'], wait['marker']), (1800, 'Result-End: a/1'))
        self.assertIn('await --path /tmp/x.md', wait['parameters']['command'])


class TrailerParserTests(SliceBase):
    """Git reads trailers from a message's final paragraph only; deliver keeps reading git trailers."""

    def commit(self, name, message):
        (self.repo / 'src' / name).write_text(f'{name} = 1\n')
        self.git('add', f'src/{name}'); self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def test_final_paragraph_with_co_authored_by_is_listed_and_a_middle_paragraph_is_not(self):
        prepared = self.prepare()
        listed = self.commit('listed.py', 'add listed\n\nbody of the change\n\nCycle-Task: build-it\nCo-Authored-By: Pair <pair@example.com>')
        middle = self.commit('middle.py', 'add middle\n\nCycle-Task: build-it\n\nCo-Authored-By: Pair <pair@example.com>\nMore prose after the trailer.')
        cfg = cycle_ops.tree(self.repo)
        self.assertEqual(cycle_ops.trailer_commits(cfg, self.base, 'build-it'), [listed])
        self.assertTrue(cycle_ops.carries_trailer(cfg, listed, 'build-it'))
        self.assertFalse(cycle_ops.carries_trailer(cfg, middle, 'build-it'))
        self.write_result(prepared)
        delivered = self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done',
                             'commits': [middle]})
        self.assertEqual(delivered['untrailered_commits'], [middle])


class ReplayTests(SliceBase):
    def test_identical_retry_replays_and_rebuilds_the_invocation_while_reserved(self):
        first = self.prepare()
        before = self.record_path().read_bytes()
        # Re-serialized with another key order: the canonical digest matches.
        request = {'assignment_text': TEXT, 'host': 'claude-code', 'role': 'developer', 'task_id': 'build-it', 'op_id': 'prep-0001', 'op': 'prepare-dispatch'}
        again = self.ok(request)
        self.assertEqual((again['replayed'], again['changed'], again['attempt_state']), (True, False, 'reserved'))
        self.assertEqual(again['invocation'], first['invocation'])
        self.assertEqual(self.record_path().read_bytes(), before)

    def test_replay_after_attach_returns_no_invocation(self):
        self.prepare()
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
        again = self.prepare()
        self.assertEqual((again['replayed'], again['attempt_state']), (True, 'running'))
        self.assertNotIn('invocation', again)

    def test_replay_recreates_a_vanished_result_directory(self):
        first = self.prepare()
        directory = Path(first['result_path']).parent; directory.rmdir()
        again = self.prepare()
        self.assertTrue(directory.is_dir()); self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        self.assertIn('invocation', again)

    def test_reused_op_id_with_other_contents_is_refused(self):
        self.prepare()
        response = self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'reviewer',
                                 'host': 'claude-code', 'assignment_text': TEXT}, 'op-id-reused')
        recovery = response['errors'][0]['recovery'][0]
        self.assertEqual(recovery['caller_fills'], ['op_id']); self.assertNotIn('op_id', recovery['request'])

    def test_second_reservation_is_an_unresolved_dispatch(self):
        self.prepare()
        self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0002', 'task_id': 'build-it', 'role': 'developer',
                      'host': 'claude-code', 'assignment_text': TEXT}, 'unresolved-dispatch', 'task-not-eligible')


class RefusalTests(SliceBase):
    def test_errors_are_collected_before_any_write(self):
        response = self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer',
                                 'host': 'nowhere', 'assignment_text': '   ', 'result_path': 'relative.md'},
                                'unknown-host', 'result-path-not-absolute')
        for error in response['errors']:
            self.assertEqual(set(error), {'code', 'field', 'expected', 'observed', 'problem', 'recovery'})

    def test_schema_refusal_names_fields(self):
        # lessons and remaining are optional in the schema (a listed release cycle takes neither); finish refuses their absence itself.
        response = self.refused({'op': 'finish', 'op_id': 'short'}, 'invalid-request', 'invalid-request')
        self.assertEqual(sorted(e['field'] for e in response['errors']), ['expect_revision', 'op_id'])

    def test_attach_with_another_handle_is_refused(self):
        self.prepare()
        self.ok({'op': 'attach-execution', 'op_id': 'attach-001', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
        same = self.ok({'op': 'attach-execution', 'op_id': 'attach-002', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h1'})
        self.assertEqual(same['changed'], False)
        self.refused({'op': 'attach-execution', 'op_id': 'attach-003', 'assignment': 'build-it', 'attempt': 1, 'handle': 'h2'}, 'handle-conflict')
        self.refused({'op': 'attach-execution', 'op_id': 'attach-004', 'assignment': 'build-it', 'attempt': 2, 'handle': 'h1'}, 'superseded-attempt')

    def test_result_without_marker_is_incomplete(self):
        prepared = self.prepare()
        sha = self.work(prepared, marker=False)
        self.refused({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [sha]}, 'result-incomplete')
        self.assertNotEqual(self.ok({'op': 'inspect'})['assignments'][0]['observation'], 'result-arrived')
        self.write_result(prepared, assignment='other')
        self.refused({'op': 'deliver', 'op_id': 'deliver-02', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [sha]}, 'result-header')

    def test_result_through_a_symlink_is_refused(self):
        prepared = self.prepare()
        target = self.repo.parent / (self.repo.name + '-real.md'); self.addCleanup(lambda: target.unlink(missing_ok=True))
        self.write_result({**prepared, 'result_path': str(target)})
        Path(prepared['result_path']).symlink_to(target)
        self.refused({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'blocked'}, 'result-is-symlink')

    def test_missing_result_and_directory_result(self):
        prepared = self.prepare()
        self.refused({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'failed'}, 'result-missing')
        Path(prepared['result_path']).mkdir()
        self.addCleanup(lambda: Path(prepared['result_path']).rmdir() if Path(prepared['result_path']).is_dir() else None)
        self.refused({'op': 'deliver', 'op_id': 'deliver-02', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'failed'}, 'result-is-directory')

    def test_commit_outside_the_task_base_is_refused(self):
        prepared = self.prepare()
        empty = subprocess.run(['git', '-C', str(self.repo), 'hash-object', '-t', 'tree', '-w', '--stdin'], input='', capture_output=True,
                               text=True, check=True).stdout.strip()
        stray = self.git('commit-tree', empty, '-m', 'unrelated root')
        self.write_result(prepared)
        self.refused({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [stray]},
                     'commit-not-from-base')

    def test_partial_task_commit_must_be_delivered(self):
        prepared = self.prepare()
        partial = self.work(prepared, body='answer = 3\n')
        (self.repo / 'src/a.py').write_text('answer = 2\n'); self.git('commit', '-qam', 'finish')
        final = self.git('rev-parse', 'HEAD')
        # A done delivery that names only a commit before the partial one leaves it outside the range.
        self.git('checkout', '-q', '-b', 'side', self.base); (self.repo / 'src/b.py').write_text('x = 1\n')
        self.git('add', 'src/b.py'); self.git('commit', '-qm', 'side'); side = self.git('rev-parse', 'HEAD'); self.git('checkout', '-q', '-')
        response = self.refused({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [side]},
                                'undelivered-task-commit')
        self.assertEqual(response['errors'][0]['observed'], partial)
        delivered = self.ok({'op': 'deliver', 'op_id': 'deliver-02', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [final]})
        self.assertEqual(delivered['untrailered_commits'], [final])

    def test_delivery_is_immutable(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        request = {'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'done', 'commits': [sha]}
        self.ok(request)
        same = self.ok({**request, 'op_id': 'deliver-02'})
        self.assertEqual((same['changed'], same['replayed']), (False, False))
        response = self.refused({**request, 'op_id': 'deliver-03', 'outcome': 'blocked'}, 'delivery-conflict')
        recovery = response['errors'][0]['recovery']
        self.assertEqual(recovery[0]['argv'][-4:], ['--task-id', 'build-it', '--state', 'pending'])
        self.assertEqual(recovery[1]['request']['op'], 'prepare-dispatch')
        # A replay of the original op_id after the result bytes changed is refused.
        Path(prepared['result_path']).write_text(Path(prepared['result_path']).read_text() + 'tampered\n')
        self.refused(request, 'delivery-conflict')

    def test_failed_delivery_returns_the_task_and_allows_attempt_two(self):
        prepared = self.prepare()
        self.write_result(prepared)
        self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': 'build-it', 'attempt': 1, 'outcome': 'failed', 'note': 'tests failed'})
        self.assertEqual(load(self.repo, self.cid)['plan']['tasks'][0]['status'], 'pending')
        again = self.prepare(op_id='prep-0002', assignment='build-it')
        self.assertEqual(again['attempt'], 2)

    def test_attempt_limit(self):
        for n in range(1, 4):
            prepared = self.prepare(op_id=f'prep-000{n}', assignment='build-it')
            self.write_result(prepared)
            self.ok({'op': 'deliver', 'op_id': f'deliver-0{n}', 'assignment': 'build-it', 'attempt': n, 'outcome': 'failed'})
        response = self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0004', 'task_id': 'build-it', 'role': 'developer',
                                 'host': 'claude-code', 'assignment_text': TEXT}, 'attempt-limit')
        self.assertEqual([r['argv'][6] for r in response['errors'][0]['recovery']], ['pause'])

    def test_finish_refusals(self):
        self.prepare()
        response = self.refused({'op': 'finish', 'op_id': 'finish-001', 'expect_revision': 1, 'lessons': ['x'], 'remaining': ['none']},
                                'wrong-phase', 'stale-revision', 'open-attempts', 'no-commits')
        self.assertIn('prepare-dispatch', response['errors'][[e['code'] for e in response['errors']].index('stale-revision')]['problem'])

    def test_every_mutating_operation_has_a_handler(self):
        # Advice refresh reads under the lock, requests outside it, then commits
        # under the lock. Its dedicated dispatcher cannot use a locked handler.
        self.assertTrue(callable(cycle_ops.refresh_advice))
        self.assertEqual(set(cycle_ops.HANDLERS) | {'advice-refresh'},
                         set(cycle_ops.OPERATIONS) - set(cycle_ops.UNJOURNALED))


class CompatibilityTests(SliceBase):
    def test_version_two_records_need_upgrade_and_inspect_reads_them(self):
        cid = self.fixture(version=2)
        self.refused({'op': 'prepare-dispatch', 'op_id': 'prep-0001', 'task_id': 'build-it', 'role': 'developer', 'host': 'claude-code',
                      'assignment_text': TEXT}, 'needs-upgrade', cid=cid)
        seen = self.ok({'op': 'inspect'}, cid=cid)
        self.assertEqual((seen['schema_version'], seen['revision']), (2, None))
        self.assertEqual(seen['actions'][0]['request'], {'op': 'upgrade'})

    def test_schema_keeps_version_two_strict_and_requires_version_three_fields(self):
        doc = load(self.repo, self.cid)
        missing = dict(doc); missing.pop('revision')
        with self.assertRaisesRegex(CycleError, 'revision'):
            validate(missing)
        v2 = load(self.repo, self.fixture(version=2))
        for extra in ({'revision': 1}, {'operations': []}, {'results_dir': None}):
            with self.assertRaises(CycleError):
                validate({**v2, **extra})
        reserved = dict(v2, assignments=[{'id': 'x', 'role': 'developer', 'task': None, 'agent': None, 'result_path': None, 'state': 'reserved',
                                          'attempt': 1, 'started_at': 'now', 'last_seen': 'now', 'ended_at': None, 'note': None}])
        with self.assertRaisesRegex(CycleError, 'enum'):
            validate(reserved)

    def test_committed_cycle_records_still_validate(self):
        root = Path(__file__).resolve().parents[3] / 'bionic/cycles'
        if not root.is_dir():
            self.skipTest('the dogfood tree is not in this checkout')
        records = sorted(root.glob('*/cycle.json'))
        self.assertTrue(records)
        for path in records:
            with self.subTest(path=path.parent.name):
                validate(json.loads(path.read_text()))

    def test_recovery_actions_validate_against_the_operation_schema(self):
        self.prepare()
        response = self.refused({'op': 'finish', 'op_id': 'finish-001', 'expect_revision': 1, 'lessons': ['x'], 'remaining': ['none']},
                                'wrong-phase', 'stale-revision', 'open-attempts', 'no-commits')
        fills = {'op_id': 'filled-001', 'assignment_text': 'text', 'role': 'developer', 'host': 'claude-code', 'handle': 'h', 'outcome': 'done',
                 'lessons': ['l'], 'remaining': ['none'], 'quote': 'q', 'conversation': 'c', 'date': '2026-10-30', 'tip': self.base}
        actions = [r for e in response['errors'] for r in e['recovery'] if 'request' in r]
        actions += [a for a in self.ok({'op': 'inspect'})['actions'] if 'request' in a]
        self.assertTrue(actions)
        for item in actions:
            request = {**item['request'], **{k: fills[k] for k in item['caller_fills']}}
            self.assertEqual(cycle_ops.schema_errors(request), [], item)


if __name__ == '__main__':
    unittest.main()
