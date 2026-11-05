"""Host adapters: invocations, wait descriptors, liveness and loss evidence for every host.

These test the adapter module's own contract. The engine-level crash-point and
attempt-limit tests live in test_cycle_dispatch_recovery.py."""
import json
from pathlib import Path
import shlex
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_hosts
from cycle_hosts import ADAPTERS, ROLES

PLUGIN = Path(__file__).resolve().parents[2]
TEXT = 'Outcome: x.\nEvidence: y.\nConstraint: z; it\'s "quoted".\n'
PRE = cycle_hosts.preamble(cycle='CYC-0001', task='build-it', assignment='build-it', attempt=2, objectives='/r/bionic/objectives.md',
                           result_path='/tmp/res/build-it-attempt-2.md', base='a' * 40, task_commits=[])


def invoke(host, role='developer', mode=None):
    return cycle_hosts.invocation(host, role=role, assignment_text=TEXT, preamble_text=PRE, description='build-it attempt 2',
                                  repo_root=Path('/r'), result_path='/tmp/res/build-it-attempt-2.md',
                                  assignment='build-it', attempt=2, mode=mode)


def every_mode():
    for host, found in ADAPTERS.items():
        for name in found.modes:
            yield host, name


class RegistryTests(unittest.TestCase):
    def test_four_hosts_registered(self):
        self.assertEqual(sorted(ADAPTERS), ['claude-code', 'codex', 'omp', 'opencode'])
        for host, found in ADAPTERS.items():
            self.assertIs(cycle_hosts.adapter(host), found)
            self.assertEqual(cycle_hosts.modes(host)[0], found.default_mode)
            self.assertEqual(set(cycle_hosts.modes(host)), set(found.modes))
        self.assertIsNone(cycle_hosts.adapter('vscode'))

    def test_handle_less_modes(self):
        self.assertEqual({(h, m) for h, m in every_mode() if not cycle_hosts.returns_handle(h, m)},
                         {('claude-code', 'blocking'), ('opencode', 'foreground'), ('omp', 'blocking')})
        # The defaults: the three handle-less hosts default to the mode that blocks until the child ends.
        self.assertFalse(cycle_hosts.returns_handle('claude-code'))
        self.assertFalse(cycle_hosts.returns_handle('opencode'))
        self.assertFalse(cycle_hosts.returns_handle('omp'))
        self.assertTrue(cycle_hosts.returns_handle('claude-code', 'background'))
        self.assertTrue(cycle_hosts.returns_handle('codex'))

    def test_claude_code_blocks_by_default_and_offers_background(self):
        found = ADAPTERS['claude-code']
        self.assertEqual(found.default_mode, 'blocking')
        self.assertEqual(sorted(found.modes), ['background', 'blocking'])
        self.assertEqual(cycle_hosts.modes('claude-code'), ('blocking', 'background'))

    def test_every_listing_is_not_authoritative(self):
        # No host observation has established a listing that covers every session's pending executions.
        for host, name in every_mode():
            with self.subTest(host=host, mode=name):
                self.assertFalse(cycle_hosts.mode_of(host, name).listing_authoritative)

    def test_unobserved_behaviour_is_declared(self):
        for host, found in ADAPTERS.items():
            with self.subTest(host=host):
                self.assertIn('listing semantics', found.unverified)
                self.assertIn('dispatch refusals that prove no execution', found.unverified)
        self.assertIn('every waiting behaviour', ADAPTERS['omp'].unverified)
        self.assertIn('the hand-back path at default depth', ADAPTERS['codex'].unverified)
        for item in ("a top-level session's blocking behaviour", 'acceptance of the background flag',
                     "the background mode's handle while the child runs"):
            self.assertIn(item, ADAPTERS['claude-code'].unverified)


class RoleNameTests(unittest.TestCase):
    """Projected role names match what the installers project."""

    def test_claude_code_names_plugin_namespaced_agents(self):
        plugin = json.loads((PLUGIN / '.claude-plugin/plugin.json').read_text())['name']
        for role in ROLES:
            self.assertTrue((PLUGIN / 'agents' / f'{role}.md').is_file(), role)
            self.assertEqual(ADAPTERS['claude-code'].role_name(role), f'{plugin}:{role}')

    def test_codex_names_match_the_projection(self):
        import codex_agents
        for role in ROLES:
            self.assertEqual(ADAPTERS['codex'].role_name(role), codex_agents.codex_agent_name(role))

    def test_opencode_names_match_the_projection(self):
        import opencode_agents
        self.assertEqual({ADAPTERS['opencode'].role_name(r) + '.md' for r in ROLES}, set(opencode_agents.managed_filenames()))

    def test_omp_names_match_the_projection(self):
        import omp_agents
        for role in ROLES:
            self.assertEqual(ADAPTERS['omp'].role_name(role) + '.md', omp_agents.omp_agent_filename(role))


class InvocationTests(unittest.TestCase):
    PROMPT_KEY = {'claude-code': 'prompt', 'codex': 'message', 'opencode': 'prompt', 'omp': 'prompt'}
    ROLE_KEY = {'claude-code': 'subagent_type', 'codex': 'agent_type', 'opencode': 'subagent_type', 'omp': 'agent'}

    def test_prompt_is_assignment_text_byte_for_byte_then_preamble(self):
        for host, name in every_mode():
            for role in ROLES:
                with self.subTest(host=host, mode=name, role=role):
                    out = invoke(host, role, name)
                    prompt = out['parameters'][self.PROMPT_KEY[host]]
                    self.assertEqual(prompt, TEXT + PRE)
                    self.assertTrue(prompt.startswith(TEXT))
                    self.assertEqual(out['parameters'][self.ROLE_KEY[host]], ADAPTERS[host].role_name(role))
                    self.assertEqual(out['role_name'], ADAPTERS[host].role_name(role))
                    self.assertEqual((out['host'], out['mode'], out['tool']), (host, name, cycle_hosts.mode_of(host, name).tool))

    def test_preamble_carries_objectives_result_path_and_marker(self):
        for line in ('Read the objectives at /r/bionic/objectives.md before work.', 'Write your result to /tmp/res/build-it-attempt-2.md.',
                     'Assignment: build-it', 'Attempt: 2', 'Result-End: build-it/2', 'Cycle-Task: build-it'):
            self.assertIn(line, PRE)

    def test_preamble_puts_the_trailer_in_one_final_paragraph(self):
        self.assertIn('a final trailer paragraph, separated from the body by one blank line, that holds', PRE)
        self.assertIn('that holds `Cycle-Task: build-it` and any other trailer, such as `Co-Authored-By:`, on adjacent lines.', PRE)

    def test_handle_modes_pair_with_a_valid_attach_request(self):
        from cycle_ops import schema_errors
        for host, name in every_mode():
            with self.subTest(host=host, mode=name):
                out = invoke(host, mode=name)
                if cycle_hosts.returns_handle(host, name):
                    self.assertEqual(out['handle'], {'source': cycle_hosts.mode_of(host, name).handle_source})
                    self.assertEqual(out['attach']['caller_fills'], ['op_id', 'handle'])
                    filled = {**out['attach']['request'], 'op_id': 'attach-0001', 'handle': 'h-1'}
                    self.assertEqual(schema_errors(filled), [])
                elif (host, name) == ('claude-code', 'blocking'):
                    # No handle while the child runs; an agentId that arrives without the final report is one.
                    self.assertIsNone(out['handle'])
                    self.assertEqual(out['attach']['conditional'], True)
                    self.assertIn('final report', out['attach']['condition'])
                    self.assertEqual(out['attach']['caller_fills'], ['op_id', 'handle'])
                    filled = {**out['attach']['request'], 'op_id': 'attach-0001', 'handle': 'agent-1'}
                    self.assertEqual(schema_errors(filled), [])
                else:
                    self.assertIsNone(out['handle']); self.assertIsNone(out['attach'])

    def test_claude_code_background_flag_only_in_the_background_mode(self):
        self.assertNotIn('run_in_background', invoke('claude-code')['parameters'])
        self.assertNotIn('run_in_background', invoke('claude-code', mode='blocking')['parameters'])
        self.assertIs(invoke('claude-code', mode='background')['parameters']['run_in_background'], True)
        self.assertEqual(invoke('claude-code')['mode'], 'blocking')

    def test_background_flag_only_where_the_mode_is_background(self):
        self.assertNotIn('background', invoke('opencode', mode='foreground')['parameters'])
        self.assertTrue(invoke('opencode', mode='background')['parameters']['background'])
        self.assertNotIn('background', invoke('omp', mode='blocking')['parameters'])
        self.assertTrue(invoke('omp', mode='background')['parameters']['background'])

    def test_codex_carries_the_hand_back_route(self):
        self.assertIn('re-invokes the delegator', invoke('codex')['hand_back'])
        for host in ('claude-code', 'opencode', 'omp'):
            self.assertNotIn('hand_back', invoke(host))

    def test_unknown_mode_refused(self):
        with self.assertRaises(KeyError):
            invoke('claude-code', mode='foreground')


class WaitDescriptorTests(unittest.TestCase):
    def marker_command(self, command):
        argv = shlex.split(command)
        self.assertEqual(argv[:3], ['uv', 'run', str(PLUGIN / 'scripts/cycle.py')])
        i = argv.index('await')
        self.assertEqual(argv[i + 1:i + 3], ['--path', '/tmp/res/build-it-attempt-2.md'])
        self.assertEqual(argv[argv.index('--marker') + 1], 'build-it/2')
        return float(argv[argv.index('--timeout') + 1])

    def test_every_descriptor_waits_on_the_marker(self):
        for host, name in every_mode():
            with self.subTest(host=host, mode=name):
                wait = invoke(host, mode=name)['wait']
                self.assertEqual(wait['marker'], 'Result-End: build-it/2')
                self.assertNotIn('windows', wait)
                self.assertEqual(wait['window_seconds'], 1800)
                self.assertEqual(wait['unverified'], list(ADAPTERS[host].unverified))
                commands = [wait['parameters']['command']] if 'command' in wait['parameters'] else []
                if 'check' in wait:
                    commands.append(wait['check']['parameters']['command'])
                self.assertTrue(commands, 'a descriptor with no marker await')
                for command in commands:
                    self.assertLessEqual(self.marker_command(command), cycle_hosts.WINDOW_SECONDS)

    def test_mechanism_per_host(self):
        expected = {('claude-code', 'blocking'): ('blocking-dispatch', 'Agent'),
                    ('claude-code', 'background'): ('background-command', 'Bash'),
                    ('codex', 'spawn'): ('host-wait', 'wait_agent'),
                    ('opencode', 'foreground'): ('blocking-dispatch', 'subagent'),
                    ('opencode', 'background'): ('background-command', 'shell'),
                    ('omp', 'blocking'): ('blocking-dispatch', 'task'),
                    ('omp', 'background'): ('background-command', 'bash')}
        self.assertEqual({(h, m): (invoke(h, mode=m)['wait']['mechanism'], invoke(h, mode=m)['wait']['tool']) for h, m in every_mode()}, expected)

    def test_claude_code_runs_the_await_in_the_background_for_one_window(self):
        wait = invoke('claude-code', mode='background')['wait']
        self.assertIs(wait['parameters']['run_in_background'], True)
        self.assertEqual(self.marker_command(wait['parameters']['command']), 1800)

    def test_codex_global_wait_cross_checks_the_bound_path(self):
        wait = invoke('codex')['wait']
        self.assertEqual(wait['parameters'], {'timeout_ms': 60000})
        self.assertNotIn('caller_fills', wait)
        self.assertEqual(wait['binding'], {'assignment': 'build-it', 'attempt': 2, 'result_path': '/tmp/res/build-it-attempt-2.md'})
        self.assertEqual(self.marker_command(wait['check']['parameters']['command']), cycle_hosts.CHECK_SECONDS)

    def test_blocking_dispatch_checks_the_result_after_it_returns(self):
        for host, name in (('claude-code', 'blocking'), ('opencode', 'foreground'), ('omp', 'blocking')):
            wait = invoke(host, mode=name)['wait']
            self.assertEqual(wait['parameters'], {})
            self.assertIn('proves nothing alone', wait['check']['purpose'])


class ReofferedWaitTests(unittest.TestCase):
    """inspect re-offers the wait for an open attempt. The invocation performed the blocking call once;
    a handle-less attempt with no complete result is offered only the marker await, never a dispatch."""

    def reoffer(self, host, name):
        return cycle_hosts.wait_descriptor(host, mode=name, repo_root=Path('/r'), result_path='/tmp/res/build-it-attempt-2.md',
                                           assignment='build-it', attempt=2)

    def test_blocking_modes_are_offered_only_the_marker_await(self):
        for host, name in (('claude-code', 'blocking'), ('opencode', 'foreground'), ('omp', 'blocking')):
            with self.subTest(host=host, mode=name):
                wait = self.reoffer(host, name)
                self.assertEqual(wait['mechanism'], 'background-command')
                self.assertNotEqual(wait['tool'], cycle_hosts.mode_of(host, name).tool)
                self.assertNotIn('check', wait)
                self.assertEqual(wait['window_seconds'], 1800)
                argv = shlex.split(wait['parameters']['command'])
                self.assertEqual(argv[argv.index('--marker') + 1], 'build-it/2')
                self.assertEqual(float(argv[argv.index('--timeout') + 1]), 1800)

    def test_handle_modes_keep_their_wait(self):
        for host, name in (('claude-code', 'background'), ('codex', 'spawn'), ('opencode', 'background'), ('omp', 'background')):
            with self.subTest(host=host, mode=name):
                self.assertEqual(self.reoffer(host, name), invoke(host, mode=name)['wait'])


class MarkerTests(unittest.TestCase):
    HEAD = 'Assignment: a\nAttempt: 1\nbody\n'

    def test_parse_marker(self):
        self.assertEqual(cycle_hosts.parse_marker('build-it/2'), ('build-it', 2))
        for bad in ('', 'a', 'a/0', 'a/-1', '/1', 'a b/1', 'a/1/2', None):
            self.assertIsNone(cycle_hosts.parse_marker(bad), bad)

    def test_trailing_newline_tolerated_and_text_after_marker_is_incomplete(self):
        self.assertTrue(cycle_hosts.has_marker(self.HEAD + 'Result-End: a/1\n\n  \n', 'a', 1))
        self.assertFalse(cycle_hosts.has_marker(self.HEAD + 'Result-End: a/1\nPS\n', 'a', 1))
        self.assertFalse(cycle_hosts.has_marker(self.HEAD, 'a', 1))
        self.assertFalse(cycle_hosts.has_marker('', 'a', 1))
        self.assertIsNone(cycle_hosts.result_problem(self.HEAD + 'Result-End: a/1\n', 'a', 1))
        self.assertEqual(cycle_hosts.result_problem(self.HEAD, 'a', 1)[0], 'result-incomplete')

    def test_marker_arrived_reads_only_regular_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / 'r.md'; real.write_text(self.HEAD + 'Result-End: a/1\n')
            self.assertTrue(cycle_hosts.marker_arrived(real, 'a', 1))
            self.assertFalse(cycle_hosts.marker_arrived(real, 'a', 2))
            link = root / 'l.md'; link.symlink_to(real)
            self.assertFalse(cycle_hosts.marker_arrived(link, 'a', 1))
            self.assertFalse(cycle_hosts.marker_arrived(root, 'a', 1))
            self.assertFalse(cycle_hosts.marker_arrived(root / 'missing.md', 'a', 1))


class LivenessTests(unittest.TestCase):
    def test_unknown_without_a_host_status_or_a_handle(self):
        for host, name in every_mode():
            with self.subTest(host=host, mode=name):
                self.assertEqual(cycle_hosts.liveness(host, mode=name, state='running'), 'unknown')
                self.assertEqual(cycle_hosts.liveness(host, mode=name, state='reserved', host_status='completed'), 'unknown')
                self.assertEqual(cycle_hosts.liveness(host, mode=name, state='running', host_status='no-such-status'), 'unknown')

    def test_listed_statuses(self):
        self.assertEqual(cycle_hosts.liveness('codex', state='running', host_status='errored'), 'terminated')
        self.assertEqual(cycle_hosts.liveness('codex', state='running', host_status='running'), 'running')
        self.assertEqual(cycle_hosts.liveness('claude-code', mode='background', state='running', host_status='killed'), 'terminated')
        self.assertEqual(cycle_hosts.liveness('claude-code', state='running', host_status='killed'), 'terminated')
        # OpenCode and OMP list no statuses: nothing they report moves liveness off unknown.
        for host in ('opencode', 'omp'):
            self.assertEqual(cycle_hosts.liveness(host, mode='background', state='running', host_status='completed'), 'unknown')


class LossEvidenceTests(unittest.TestCase):
    """mark-lost needs affirmative evidence; nothing else establishes loss."""

    def allowed(self, host, **kw):
        kw.setdefault('mode', None)
        return cycle_hosts.loss_evidence(host, **kw) is None

    def test_listed_dispatch_refusal_on_a_reserved_attempt(self):
        for host, name in every_mode():
            for refusal in cycle_hosts.PRE_EXECUTION_REFUSALS:
                with self.subTest(host=host, mode=name, refusal=refusal):
                    self.assertTrue(self.allowed(host, mode=name, state='reserved', kind='dispatch-refusal', detail=refusal))
                    # A bound handle shows the dispatch call succeeded.
                    self.assertFalse(self.allowed(host, mode=name, state='running', kind='dispatch-refusal', detail=refusal))

    def test_dispatch_timeout_or_transport_error_establishes_nothing(self):
        for host, name in every_mode():
            with self.subTest(host=host, mode=name):
                code, problem = cycle_hosts.loss_evidence(host, mode=name, state='reserved', kind='dispatch-refusal', detail='timeout')
                self.assertEqual(code, 'not-affirmative'); self.assertIn('timeout', problem)
                for kind in cycle_hosts.NOT_EVIDENCE:
                    self.assertEqual(cycle_hosts.loss_evidence(host, mode=name, state='reserved', kind=kind, detail='x')[0], 'not-affirmative')
                    self.assertEqual(cycle_hosts.loss_evidence(host, mode=name, state='running', kind=kind, detail='x')[0], 'not-affirmative')

    def test_terminal_status_needs_a_bound_handle_and_a_listed_status(self):
        self.assertTrue(self.allowed('codex', state='running', kind='terminal-status', detail='shutdown'))
        self.assertTrue(self.allowed('claude-code', state='running', kind='terminal-status', detail='failed'))
        self.assertFalse(self.allowed('codex', state='reserved', kind='terminal-status', detail='shutdown'))
        self.assertFalse(self.allowed('codex', state='running', kind='terminal-status', detail='running'))
        self.assertFalse(self.allowed('codex', state='running', kind='terminal-status', detail='not_found'))
        self.assertFalse(self.allowed('opencode', mode='background', state='running', kind='terminal-status', detail='completed'))

    def test_blocking_return_only_for_handle_less_modes(self):
        # opencode foreground and omp blocking keep the general rule: any quoted return, no final report required.
        self.assertTrue(self.allowed('opencode', mode='foreground', state='reserved', kind='blocking-returned', detail='returned: no file'))
        self.assertTrue(self.allowed('omp', mode='blocking', state='reserved', kind='blocking-returned', detail='returned: no file'))
        for host, name in every_mode():
            if cycle_hosts.returns_handle(host, name):
                self.assertFalse(self.allowed(host, mode=name, state='running', kind='blocking-returned', detail='returned final-report'))

    def test_claude_code_blocking_return_needs_the_final_report(self):
        self.assertTrue(self.allowed('claude-code', mode='blocking', state='reserved', kind='blocking-returned',
                                     detail='the Agent result carried the final-report: DONE, no result file'))
        code, problem = cycle_hosts.loss_evidence('claude-code', mode='blocking', state='reserved', kind='blocking-returned',
                                                  detail='the Agent call returned')
        self.assertEqual(code, 'not-affirmative'); self.assertIn('final-report', problem)

    def test_claude_code_blocking_return_is_refused_once_a_handle_is_bound(self):
        code, problem = cycle_hosts.loss_evidence('claude-code', mode='blocking', state='running', kind='blocking-returned',
                                                  detail='the Agent result carried the final-report')
        self.assertEqual(code, 'not-affirmative'); self.assertIn('handle', problem)
        # A bound handle's host status still ends the attempt, as for any handle.
        self.assertTrue(self.allowed('claude-code', mode='blocking', state='running', kind='terminal-status', detail='failed'))

    def test_claude_code_background_return_stays_non_evidence(self):
        for state in ('reserved', 'running'):
            self.assertFalse(self.allowed('claude-code', mode='background', state=state, kind='blocking-returned',
                                          detail='the Agent result carried the final-report'))

    def test_an_agent_error_with_no_report_and_no_agent_id(self):
        # Listed pre-execution refusals are dispatch-refusals; any other error establishes nothing; the owner's statement leads on.
        for refusal in cycle_hosts.PRE_EXECUTION_REFUSALS:
            self.assertTrue(self.allowed('claude-code', mode='blocking', state='reserved', kind='dispatch-refusal', detail=refusal))
        for detail in ('timeout', 'Agent error: connection reset', 'internal-error'):
            self.assertEqual(cycle_hosts.loss_evidence('claude-code', mode='blocking', state='reserved', kind='dispatch-refusal',
                                                       detail=detail)[0], 'not-affirmative')
        self.assertEqual(cycle_hosts.loss_evidence('claude-code', mode='blocking', state='reserved', kind='blocking-returned',
                                                   detail='Agent error: connection reset')[0], 'not-affirmative')
        self.assertTrue(self.allowed('claude-code', mode='blocking', state='reserved', kind='owner-confirmation',
                                     detail='"the owner: that call never started"'))

    def test_listing_absence_establishes_nothing_on_every_adapter(self):
        for host, name in every_mode():
            for state in ('reserved', 'running'):
                with self.subTest(host=host, mode=name, state=state):
                    code, problem = cycle_hosts.loss_evidence(host, mode=name, state=state, kind='listing-absence', detail='not listed')
                    self.assertEqual(code, 'not-affirmative'); self.assertIn('not recorded as authoritative', problem)

    def test_owner_confirmation_quoted(self):
        for host, name in every_mode():
            self.assertTrue(self.allowed(host, mode=name, state='running', kind='owner-confirmation', detail='"that session ended"'))
            self.assertEqual(cycle_hosts.loss_evidence(host, mode=name, state='running', kind='owner-confirmation', detail='  ')[0],
                             'evidence-detail-missing')

    def test_complete_result_or_closed_attempt_is_never_lost(self):
        self.assertEqual(cycle_hosts.loss_evidence('codex', state='running', kind='terminal-status', detail='completed',
                                                   result_complete=True)[0], 'result-arrived')
        for state in ('finished', 'lost'):
            self.assertEqual(cycle_hosts.loss_evidence('codex', state=state, kind='owner-confirmation', detail='x')[0], 'attempt-not-open')

    def test_unknown_kind(self):
        self.assertEqual(cycle_hosts.loss_evidence('codex', state='running', kind='vibes', detail='x')[0], 'unknown-evidence-kind')


class WindowTests(unittest.TestCase):
    def test_windows_are_uncapped_and_derive_nothing_from_time(self):
        """A window is a wait length only: no count, no exhaustion, no time-derived status."""
        self.assertEqual(cycle_hosts.WINDOW_SECONDS, 1800)
        for name in ('WAIT_WINDOWS', 'window_status'):
            self.assertFalse(hasattr(cycle_hosts, name), name)
        self.assertIn('window-expired', cycle_hosts.NOT_EVIDENCE)


class RecoveryOrderTests(unittest.TestCase):
    def test_reserved_with_handle(self):
        for host, name in (('claude-code', 'background'), ('codex', 'spawn')):
            self.assertEqual(cycle_hosts.recovery_order(host, mode=name, observation='reserved-unbound'),
                             ['await-marker', 'attach-execution', 'deliver', 'mark-lost'])

    def test_reported_refusal_goes_straight_to_mark_lost(self):
        for host, name in every_mode():
            self.assertEqual(cycle_hosts.recovery_order(host, mode=name, observation='reserved-unbound', refusal_reported=True), ['mark-lost'])

    def test_handle_less_never_offers_attach(self):
        for host, name in (('claude-code', 'blocking'), ('opencode', 'foreground'), ('omp', 'blocking')):
            self.assertEqual(cycle_hosts.recovery_order(host, mode=name, observation='reserved-unbound'), ['await-marker', 'deliver', 'mark-lost'])

    def test_bound_arrived_and_closed(self):
        for host, name in every_mode():
            self.assertEqual(cycle_hosts.recovery_order(host, mode=name, observation='running-bound'), ['await-marker', 'deliver', 'mark-lost'])
            self.assertEqual(cycle_hosts.recovery_order(host, mode=name, observation='result-arrived'), ['deliver'])
            self.assertEqual(cycle_hosts.recovery_order(host, mode=name, observation='delivered'), [])
            self.assertEqual(cycle_hosts.recovery_order(host, mode=name, observation='lost'), [])


if __name__ == '__main__':
    unittest.main()
