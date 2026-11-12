"""Host adapters for typed cycle dispatch.

An adapter is data plus small pure functions. It turns a reserved attempt into the
`invocation` the calling agent performs with its own dispatch tool, and it describes
how that agent waits for the result. An adapter never runs a host tool: the dispatch
tools (Agent in Claude Code, spawn_agent in Codex, the subagent tool in OpenCode, the
task tool in OMP) are exposed to the agent, not to this process.

Four adapters are registered in `ADAPTERS`: claude-code, codex, opencode and omp. The
engine reads only the functions below, so a new host needs no engine change.

Result contract (shared by every host): the result file's first two non-blank lines
are `Assignment: <id>` and `Attempt: <N>`, and its last non-blank line is
`Result-End: <id>/<N>#<delivery token>` on a new dispatch. Historical attempts
without a token keep `Result-End: <id>/<N>`. A mismatched marker is incomplete.

Recovery contract (shared by every host). The engine reserves an attempt before the
host call and binds the handle after it; the host call itself is outside every
transaction. `loss_evidence` decides whether a report establishes that an execution
terminated or never started; elapsed time, an expired wait window, a missing result,
a wait or status error, and absence from a listing that is not authoritative establish
nothing. A wait window is only a wait length: windows are uncapped, and ending one
changes no state and pauses nothing. `recovery_order` names the recoveries for an open
attempt, in order.

Host behaviour that has not been observed is listed in each adapter's `unverified`
tuple and in every wait descriptor. Listing a refusal or status here is the adapter's
claim about documented host semantics; the Verify phase's host observation record (the Test phase on records created before the rename) says
which claims were observed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import shlex

# The ten crux roles, as the agent definitions under crux/agents/ name them.
ROLES = ('architect', 'brainstormer', 'commander', 'dev-lead', 'developer', 'historian',
         'librarian', 'night-gardener', 'reviewer', 'wayfinder')
# A wait window lasts at most thirty minutes. Windows are uncapped: ending one changes no
# state, and the caller starts the next one while the attempt has no complete result.
WINDOW_SECONDS = 1800
# A one-shot check of a result path after a blocking dispatch or a host wait returned.
CHECK_SECONDS = 5
CODEX_WAIT_MS = 60000
CODEX_INTERFACE = {
    'host': 'codex', 'version': None, 'version_status': 'unknown-not-exposed',
    'observation': 'CYC-0100 exposed Codex collaboration tools; schema observation, not native-role injection',
    'spawn': {'tool': 'collaboration.spawn_agent', 'required': ['task_name', 'message'],
              'emitted': ['task_name', 'agent_type', 'message']},
    'wait': {'tool': 'collaboration.wait_agent', 'parameters': ['timeout_ms'], 'global_wake_up': True},
    'resume': {'tool': 'collaboration.followup_task', 'parameters': ['target', 'message']},
}

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# The engine that writes a reservation; the preamble names it so a resume brief cites it.
ENGINE = PLUGIN_ROOT / 'scripts/cycle.py'
RELEASE_DESCRIPTOR = 'tools/crux-release.json'


def release_descriptor(cfg):
    """Read project release data only; the engine never runs repository commands."""
    from cycle_workflow import contained, CycleError
    import cycle_context_read as reader
    path = contained(cfg.repo_root, RELEASE_DESCRIPTOR)
    if not path.exists():
        return None
    try:
        raw = reader._bounded_bytes(reader.Reference(path, cfg.repo_root))
        value = json.loads(raw)
        if (not isinstance(value, dict) or set(value) != {'format', 'prep_scope', 'commands', 'targets'}
                or value['format'] != 1 or not isinstance(value['prep_scope'], list)
                or not value['prep_scope'] or not isinstance(value['commands'], dict)
                or not isinstance(value['targets'], dict) or set(value['targets']) != {'beta', 'official'}
                or any(not isinstance(repo, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)
                       for repo in value['targets'].values())):
            raise ValueError('invalid descriptor fields')
        for name in value['prep_scope']:
            if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('invalid prep path')
            contained(cfg.repo_root, name)
        if len(set(value['prep_scope'])) != len(value['prep_scope']):
            raise ValueError('duplicate prep path')
        for kind, steps in value['commands'].items():
            if kind not in ('beta', 'official') or not isinstance(steps, dict):
                raise ValueError('invalid release list')
            for step, commands in steps.items():
                if (not isinstance(step, str) or not isinstance(commands, list) or not commands
                        or any(not isinstance(command, list) or not command
                               or any(not isinstance(arg, str) or not arg or '\x00' in arg for arg in command)
                               for command in commands)):
                    raise ValueError('invalid command descriptor')
        return {'path': RELEASE_DESCRIPTOR, 'sha256': hashlib.sha256(raw).hexdigest(), **value}
    except (ValueError, OSError, reader.ReadRefused) as exc:
        raise CycleError('release descriptor is unavailable or invalid: ' + type(exc).__name__) from None


def release_scope(cfg, scope, release_list, *, capture=False):
    """Complete original capture, or refuse a frozen scope before allocation."""
    from cycle_workflow import CycleError, scope_name_in_scope
    descriptor = release_descriptor(cfg)
    if descriptor is None or release_list != 'beta':
        return list(scope)
    missing = [name for name in descriptor['prep_scope'] if not scope_name_in_scope(name, scope)]
    if missing and not capture:
        raise CycleError('release prep scope omits mandatory paths: ' + ', '.join(missing)
                         + '; correct the unstarted queue item before authorization/start')
    return list(dict.fromkeys([*scope, *missing]))


def capability_requirements(role, *, continuation=False):
    required = ['read-context', 'write-result']
    if role in ('developer', 'dev-lead'):
        required += ['source-edit', 'execution-check']
    if continuation:
        required.append('release-continue')
    return required


def capability_status(role, evidence=None, *, continuation=False):
    """Report known capability gaps; absence is unknown, never fabricated support."""
    required = capability_requirements(role, continuation=continuation)
    evidence = evidence or {}
    available, unavailable = set(evidence.get('available', [])), set(evidence.get('unavailable', []))
    if (available or unavailable) and not evidence.get('observation'):
        raise ValueError('known capability evidence needs its observed source')
    if available & unavailable:
        raise ValueError('capability evidence contradicts itself')
    return {'required': required, 'available': sorted(available),
            'missing': sorted(set(required) & unavailable),
            'unknown': sorted(set(required) - available - unavailable),
            'evidence': evidence.get('observation')}


def continuation_capability(role, evidence):
    """Canonical grant and actual observed host support are separate requirements."""
    status = capability_status(role, evidence, continuation=True)
    raw = (PLUGIN_ROOT / 'agents' / (role + '.md')).read_text()
    return role == 'dev-lead' and not status['missing'] and not status['unknown'] and 'release-continue' in raw


def continuation_spec(cfg, doc, request, role):
    """Freeze an opt-in fixed-list transport without granting native capabilities."""
    from cycle_workflow import CycleError, listed
    option = request.get('release_continuation')
    if not option:
        return None
    if not listed(doc) or role != 'dev-lead':
        raise CycleError('release continuation belongs only to a fixed-list release dev-lead')
    if not continuation_capability(role, request.get('capabilities')):
        raise CycleError('release continuation capability is not observed in this native role; use normal dispatch')
    descriptor = release_descriptor(cfg)
    kind = doc['release_list']
    if descriptor is None:
        raise CycleError('release continuation needs the project release descriptor')
    steps = [task['id'] for task in doc['plan']['tasks']]
    if set(descriptor['commands'].get(kind, {})) != set(steps):
        raise CycleError('release descriptor commands must describe every fixed logical step exactly')
    release_scope(cfg, doc['plan']['scope'], kind)
    commands = {step: [[arg.replace('{version}', option['version']).replace('{cycle}', doc['id'])
                       for arg in command] for command in values]
                for step, values in descriptor['commands'][kind].items()}
    publish = ['uv', 'run', 'tools/release.py', kind, '--version', option['version']]
    if kind == 'official':
        publish += ['--cycle', doc['id']]
    if publish not in commands['beta-and-smoke' if kind == 'beta' else 'official']:
        raise CycleError('continuation needs the existing bare publish command in its frozen descriptor')
    return {'format': 1, 'list': kind, 'version': option['version'], 'target': descriptor['targets'][kind],
            'steps': steps, 'owner': request.get('integration_owner') or 'commander',
            'descriptor': {'path': descriptor['path'], 'sha256': descriptor['sha256']},
            'commands': commands, 'capabilities': request['capabilities'],
            'role_sha256': hashlib.sha256((PLUGIN_ROOT / 'agents' / (role + '.md')).read_bytes()).hexdigest(),
            'artifact': None}

# The kinds of report a caller may offer as evidence that an execution terminated or
# never started. Only `loss_evidence` decides whether one is affirmative.
EVIDENCE_KINDS = ('dispatch-refusal', 'terminal-status', 'blocking-returned', 'listing-absence', 'owner-confirmation')
# Reports that never establish loss. Named so a refusal can say why.
NOT_EVIDENCE = ('dispatch-error', 'wait-error', 'status-error', 'window-expired', 'result-missing', 'elapsed-time')

MARKER_FORM = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._-]{0,63})/([1-9][0-9]*)(?:#([0-9a-f]{32}))?$')


def marker(assignment: str, attempt: int, token: str | None = None) -> str:
    """The required last non-blank line of a complete result."""
    return f'Result-End: {assignment}/{attempt}' + (f'#{token}' if token else '')


def headers(assignment: str, attempt: int) -> tuple[str, str]:
    """The required first two non-blank lines of a result."""
    return f'Assignment: {assignment}', f'Attempt: {attempt}'


def parse_marker(value: str) -> tuple[str, int] | tuple[str, int, str] | None:
    """Parse the await marker, with an optional modern delivery token; None when malformed."""
    found = MARKER_FORM.fullmatch(value or '')
    if not found:
        return None
    return (found.group(1), int(found.group(2)), found.group(3)) if found.group(3) else (found.group(1), int(found.group(2)))


def has_marker(text: str, assignment: str, attempt: int, token: str | None = None) -> bool:
    """Whether the last non-blank line is the end marker; trailing blank lines are tolerated."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return bool(lines) and lines[-1] == marker(assignment, attempt, token)


def marker_arrived(path: Path, assignment: str, attempt: int, token: str | None = None) -> bool:
    """Whether `path` is a regular file whose last non-blank line is the end marker.

    No stability interval: the marker is written last, so its presence is the signal."""
    try:
        if path.is_symlink() or not path.is_file():
            return False
        return has_marker(path.read_text(errors='replace'), assignment, attempt, token)
    except OSError:
        return False


def result_problem(text: str, assignment: str, attempt: int, token: str | None = None) -> tuple[str, str] | None:
    """None for a complete result; otherwise (code, problem).

    `result-header` when the first two non-blank lines do not name the assignment and
    attempt; `result-incomplete` when the last non-blank line is not the marker."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if tuple(lines[:2]) != headers(assignment, attempt):
        return 'result-header', (f'the first two non-blank lines must be {headers(assignment, attempt)[0]!r} '
                                 f'and {headers(assignment, attempt)[1]!r}')
    if not lines or lines[-1] != marker(assignment, attempt, token):
        return 'result-incomplete', f'the last non-blank line must be {marker(assignment, attempt, token)!r}; the result is incomplete'
    return None


# Roles whose invocations run in an isolated worktree where the host accepts isolation on the
# dispatch call. The decision lives here, not in the role definition, so the dev-lead, the
# commander and the cycle record stay on the main checkout (IDR dev-lead-owned-build approach 3).
ISOLATED_ROLES = frozenset({'developer'})

# Roles whose invocation preamble states that they run focused checks only (approach 6).
FOCUSED_CHECK_ROLES = frozenset({'developer', 'reviewer'})


def role_boundary(role: str) -> tuple[Path, str]:
    """Read the canonical role's opening boundary; the native role retains its whole contract."""
    path = PLUGIN_ROOT / 'agents' / f'{role}.md'
    if role not in ROLES:
        raise ValueError(f'unknown role {role}')
    text = path.read_text()
    body = text.split('\n---', 1)[1].strip() if text.startswith('---\n') and '\n---' in text else text.strip()
    opening = body.split('\n## ', 1)[0].strip()
    if not opening.startswith('# ') or len(opening.splitlines()) < 3:
        raise ValueError(f'{path} has no role boundary')
    return path, opening


def assignment(*, role: str, host: str, objectives: str, repo_root: Path, docs_root: Path,
               cycle: dict, task: dict, addendum: str = '', integration_owner: str | None = None) -> str:
    """Mandatory recorded context first, optional caller prose last. No model can omit it."""
    source, boundary = role_boundary(role)
    plan = cycle['plan']
    def items(values):
        return '\n'.join(f'- {value}' for value in values) or '- None recorded.'
    withdrawn = {entry['name'] for entry in cycle.get('withdrawals', [])}
    decisions = {(entry['kind'], entry['name']): entry for entry in cycle['decisions']
                 if entry['kind'] != 'idr' or entry['name'] not in withdrawn}
    bindings = [f'{entry["kind"]} {entry["name"]}: {docs_root / entry["path"]}; '
                f'sha256: {entry["sha256"]}; approval: '
                f'{docs_root / entry["approval"] if entry["approval"] else "none recorded"}; '
                f'accepted: {str(entry["accepted"]).lower()}' for entry in decisions.values()]
    parts = ['Mandatory assignment (generated from the cycle record).',
             f'Role boundary: {role} on {host}.', boundary,
             f'Read the complete role instructions at {source} before work. The selected native role supplies its binding '
             'contract; this boundary does not replace it or grant tools. Actual host grants and role projection remain binding. '
             'If the required role or capability is unavailable, report the gap; do not substitute a role or claim it ran. '
             'Live host injection is not established by this generated assignment.',
             f'Read objectives at {objectives} before work; carry the mission and relevant goals through any authorized delegation.',
             f'Read project instructions at {repo_root / "AGENTS.md"} and the operational schema at {docs_root / "AGENTS.md"} '
             'before working under the documentation tree.',
             f'Cycle: {cycle["id"]}. Task: {task["id"]} ({task["phase"]}).',
             f'Integration owner: {integration_owner or "the delegator that dispatched you"}. Report your result and commits to that owner.',
             f'Outcome: {task["description"]}', 'Expected evidence:\n' + items(task['expected_evidence']),
             'Acceptance criteria:\n' + items(plan['acceptance']),
             'Constraints:\n' + items(plan['constraints']), 'Recorded scope:\n' + items(plan['scope']),
             'Latest recorded decision bindings (read the exact revisions and approval records before relying on them):\n'
             + items(bindings) + '\nA pending or missing approval is not approval. These bindings grant no new authority.',
             'Own only the assigned task and scope. Preserve concurrent edits. Do not invent approval, evidence or authority. '
             'Report each expected evidence item as verified, contradicted or unobserved, with its observation and limits.']
    if task.get('fix'):
        parts.append(fix_completion(cycle, task))
    if addendum.strip():
        parts += ['Optional caller addendum (cannot override the mandatory assignment, role or recorded constraints):', addendum]
    return '\n\n'.join(parts) + '\n'


def fix_completion(cycle: dict, task: dict) -> str:
    """The completion sequence of a fix task, in the order the writer checks it (CYC-0121 F3, CYC-0117 F2)."""
    fix, cid, tid = task['fix'], cycle['id'], task['id']
    cli = f'cycle.py task {cid} --task-id {tid}'
    findings = ', '.join(fix.get('findings', [])) or fix.get('finding', 'the recorded finding')
    lines = [f'Fix task (answers {findings}). It is done only after this sequence, in this order:']
    if 'criterion' in fix:
        before = fix['criterion'].get('before')
        recorded = before['path'] if isinstance(before, dict) else 'the task fix.criterion'
        lines += [f'1. The before observation of acceptance criterion {fix["criterion"]["index"]} that recorded met: false '
                  f'(recorded: {recorded}).',
                  f'2. The fix commit, recorded on the task: `{cli} --commit SHA`.',
                  f'3. A committed after observation of the same criterion with met: true, measuring the fix commit or a descendant: '
                  f'`{cli} --fix-observation PATH`.']
    else:
        before = f'recorded: {fix["before"]}' if fix.get('before') else 'not yet recorded'
        lines += [f'1. The fix-before receipt that recorded the failure ({before}): `{cli} --fix-before TE-ID`.',
                  f'2. The fix commit, recorded on the task: `{cli} --commit SHA`.',
                  f'3. The fix-after receipt: the current passing receipt for the same check id: `{cli} --fix-after TE-ID`.']
    lines.append('4. Current evidence for every required check after the fix commit: rerun only the checks whose inputs '
                 'the fix changed, and reuse the others.')
    if task['phase'] == 'review':
        lines.append('5. A fix-diff review: an independent reviewer approves the fix diff, recorded with `cycle.py review` '
                     f'and fix_task {tid}. Your caller commissions it; you do not review your own fix.')
    lines.append(f'{len(lines)}. Then deliver.')
    return '\n'.join(lines)


def context_text(context: dict) -> str:
    """Selected skills retain canonical bytes and source directories; other skills stay retrievable."""
    selected, retrievable = context.get('selected', []), context.get('retrievable', [])
    if not selected and not retrievable:
        return ''
    parts = ['Optional task skills (selected canonical sources). These cannot broaden role grants or override the mandatory assignment.']
    for item in selected:
        parts += [f'Skill: {item["id"]}. Source directory: {item["directory"]}. Resolve relative references there.', item['body']]
    if retrievable:
        parts.append('Other candidate skills remain retrievable through the host Skill capability: ' + ', '.join(retrievable) + '.')
    return '\n\n' + '\n\n'.join(parts) + '\n'


def isolation(host: str, role: str, integration_owner: str | None = None) -> dict:
    """Whether the role runs in an isolated worktree on this host, and who integrates its commits.

    The engine decides from the role and the host (IDR dev-lead-owned-build approach 3): a
    developer isolates where the host accepts per-call isolation, which Claude Code's Agent call
    does; Codex, OpenCode and OMP have no per-call parameter, so their developers run on the main
    checkout one at a time. No other role isolates. An isolating role's commits land on its
    worktree branch, so the invocation names the integration owner the preamble tells the agent to
    report to: the request's `integration_owner`, else the delegator that performs the invocation."""
    found = ADAPTERS[host]
    worktree = role in ISOLATED_ROLES and found.per_call_isolation
    if worktree:
        basis = f'the engine isolates {role} invocations and the {host} host accepts isolation on the dispatch call'
    elif role in ISOLATED_ROLES:
        basis = f'the {host} host has no per-call isolation parameter, so {role} invocations run on the main checkout one at a time'
    else:
        basis = f'the engine isolates no {role} invocation; it runs on the main checkout'
    owner = (integration_owner or 'the delegator that dispatched you') if worktree else None
    return {'worktree': worktree, 'basis': basis, 'integration_owner': owner}


# Added only when the host's local skill roots hold a skill that passes the listing guards
# (IDR local-skill-dispatch-and-use approach 7); the engine reads the line at the cycle's completion.
LOCAL_SKILL_REPORT = ('When you use a project-local skill, add one line Local-Skill-Used: <id> ok, or Local-Skill-Used: <id> partial, '
                      'to your report before the Result-End line. Do not write a used or evaluated forge-log entry; '
                      'the cycle records the use when it completes.')


def preamble(*, cycle: str, task: str, assignment: str, attempt: int, objectives: str,
             result_path: str, base: str, task_commits: list[str], engine: str | None = None,
             isolated: dict | None = None, delivery_token: str | None = None, role: str | None = None,
             local_skill_report: bool = False) -> str:
    """Engine facts appended after the delegator's assignment text; recorded facts only."""
    first, second = headers(assignment, attempt)
    prior = ('\n'.join(f'  - {sha}' for sha in task_commits) + '\n  Build on these commits; never reset or drop them.'
             if task_commits else '  none')
    placement = []
    if isolated is not None:
        if isolated['worktree']:
            placement = [f"- You run in an isolated git worktree on this host, so your commits land on its branch, not on the main checkout. "
                         f"Report the branch and every commit SHA; {isolated['integration_owner']} integrates them onto the main checkout.",
                         '- Before your first edit, run `git rev-parse --path-format=absolute --git-dir --git-common-dir` and compare '
                         'the two absolute paths it prints. Report your checkout path (`pwd`) and branch. When the two paths are '
                         'equal, or the command fails, the promised isolation did not happen: make no edit and deliver `blocked` '
                         'with no stop, quoting both values.']
        else:
            placement = ['- You run in the main checkout on this host; commit there.']
    if role in FOCUSED_CHECK_ROLES:
        placement.append('- Run focused checks only: the tests that exercise your change or your finding. Full suites, the '
                         "staged sync.sh dry run and per-minor runs belong to the cycle's test coordinator, the dev-lead.")
    return '\n'.join([
        '',
        '---',
        'Engine facts for this attempt (generated from the cycle record):',
        f'- Read the objectives at {objectives} before work.',
        f'- Cycle {cycle}, task {task}, assignment {assignment}, attempt {attempt}.',
        *([f'- Cycle engine that reserved this attempt: {engine}. Cite this path; do not restate another.'] if engine else []),
        f'- Task base commit: {base}. Start from it.',
        *placement,
        '- Commits already on HEAD for this task:',
        prior,
        f'- End every commit message for this task with a final trailer paragraph, separated from the body by one blank line, that holds `Cycle-Task: {task}` and any other trailer, such as `Co-Authored-By:`, on adjacent lines.',
        *([f'- {LOCAL_SKILL_REPORT}'] if local_skill_report else []),
        f'- Write your result to {result_path}.',
        '- Its first two lines must be exactly:',
        f'  {first}',
        f'  {second}',
        '- Its last line must be exactly:',
        f'  {marker(assignment, attempt, delivery_token)}',
        '  Write that line last, once the report is complete.',
    ]) + '\n'


def await_argv(repo_root: Path, result_path: str, assignment: str, attempt: int, timeout: float) -> list[str]:
    """The read-only marker await: returns when the result's last line is the end marker."""
    return ['uv', 'run', str(PLUGIN_ROOT / 'scripts/cycle.py'), '--repo-root', str(repo_root), '--compact',
            'await', '--path', result_path, '--marker', f'{assignment}/{attempt}', '--timeout', str(timeout)]


@dataclass(frozen=True)
class Mode:
    """One dispatch mode of a host."""
    name: str
    tool: str
    background: bool
    # Where the execution handle appears in the tool result; None when the mode returns none.
    handle_source: str | None
    # Host statuses that affirmatively show a bound execution terminated.
    terminal_statuses: tuple[str, ...] = ()
    # Host statuses that show a bound execution still running or about to.
    running_statuses: tuple[str, ...] = ()
    # Dispatch-call refusals that prove no execution was created, as classes the caller
    # matches the host's refusal against and quotes in the mark-lost note.
    no_execution_refusals: tuple[str, ...] = ()
    # Whether absence from the host's agent listing proves the execution neither exists
    # nor can start. False on every adapter until a host observation establishes it.
    listing_authoritative: bool = False
    # A handle the host may return in a mode that has none while the child runs (Claude Code
    # blocking: an agentId that arrives without the child's final report). The invocation
    # carries a conditional attach request for it; inspect never offers attach for the mode.
    conditional_handle_source: str | None = None
    # Whether `blocking-returned` is loss evidence only when the returned result carries the
    # child's final report (detail names `final-report`) and no handle is bound.
    return_needs_final_report: bool = False


@dataclass(frozen=True)
class Adapter:
    name: str
    modes: dict[str, Mode]
    default_mode: str
    # Parts of this adapter not yet observed on the host; reported, never assumed.
    unverified: tuple[str, ...] = field(default=())
    # Set when a delegator on this host may hold no working dispatch tool and returns
    # the invocation to its caller instead.
    hand_back: str | None = None
    # Whether the host's dispatch call accepts a per-call worktree isolation parameter (Claude
    # Code's Agent call does; Codex, OpenCode and OMP have none).
    per_call_isolation: bool = False

    def role_name(self, role: str) -> str:
        raise NotImplementedError

    def parameters(self, role: str, prompt: str, description: str, mode: Mode) -> dict:
        raise NotImplementedError

    def wait(self, *, repo_root: Path, result_path: str, assignment: str, attempt: int, mode: Mode) -> dict:
        raise NotImplementedError

    def descriptor(self, mechanism: str, tool: str, parameters: dict, *, assignment: str, attempt: int,
                   caller_fills=(), check=None) -> dict:
        out = {
            'mechanism': mechanism,
            'tool': tool,
            'parameters': parameters,
            'marker': marker(assignment, attempt),
            'window_seconds': WINDOW_SECONDS,
            'unverified': list(self.unverified),
        }
        if caller_fills:
            out['caller_fills'] = list(caller_fills)
        if check is not None:
            out['check'] = check
        return out

    # The host's own tool and flag for a background shell command, which the marker await uses.
    await_tool = ''
    await_flag = None

    def marker_wait(self, *, repo_root, result_path, assignment, attempt) -> dict:
        """The window-bounded marker await alone: what inspect re-offers for an open attempt
        whose dispatch already ran. It carries no dispatch tool call."""
        return self.background_await(self.await_tool, self.await_flag, repo_root=repo_root, result_path=result_path,
                                     assignment=assignment, attempt=attempt)

    def background_await(self, tool: str, flag: dict, *, repo_root, result_path, assignment, attempt) -> dict:
        command = shlex.join(await_argv(repo_root, result_path, assignment, attempt, WINDOW_SECONDS))
        return self.descriptor('background-command', tool, {'command': command, **flag}, assignment=assignment, attempt=attempt)

    def check(self, tool: str, *, repo_root, result_path, assignment, attempt) -> dict:
        """A short foreground marker await, run after a blocking dispatch or a host wait returned."""
        return {'tool': tool, 'parameters': {'command': shlex.join(await_argv(repo_root, result_path, assignment, attempt, CHECK_SECONDS))},
                'purpose': 'confirm the result is complete; a returned dispatch or wait proves nothing alone'}


# Dispatch-call refusals returned before any execution exists: the host's permission
# system denied the tool call, or the host rejected its parameters (an unknown agent
# type, a missing field). Basis: each host's documented tool-call contract.
PRE_EXECUTION_REFUSALS = ('permission-denied', 'invalid-parameters', 'unknown-agent-type')


class ClaudeCode(Adapter):
    """Claude Code: the Agent tool. `blocking` (no flag) is the default. From a subagent caller a
    blocking call has been observed to return with the child's final report, and also (CYC-0117
    friction F1, Claude Code 2.1.319) to return at once with an agentId and no final report; the
    conditional handle route covers the second case. `background` sends the flag and expects the
    agentId while the child runs."""

    await_tool = 'Bash'
    await_flag = {'run_in_background': True}

    def role_name(self, role):
        # Plugin agents are namespaced by the plugin name.
        return f'crux:{role}'

    def parameters(self, role, prompt, description, mode):
        out = {'subagent_type': self.role_name(role), 'description': description, 'prompt': prompt}
        if role in ISOLATED_ROLES and self.per_call_isolation:
            # Per-call isolation: only developer invocations carry it (approach 3).
            out['isolation'] = 'worktree'
        if mode.background:
            out['run_in_background'] = True
        return out

    def wait(self, *, repo_root, result_path, assignment, attempt, mode):
        if mode.background:
            # A live background command keeps the delegating subagent resumable.
            return self.marker_wait(repo_root=repo_root, result_path=result_path, assignment=assignment, attempt=attempt)
        return self.descriptor('blocking-dispatch', mode.tool, {}, assignment=assignment, attempt=attempt,
                               check=self.check('Bash', repo_root=repo_root, result_path=result_path,
                                                assignment=assignment, attempt=attempt))


class Codex(Adapter):
    """Codex waits globally; a wake-up must be checked against the exact attempt marker."""

    def role_name(self, role):
        return f"crux_{role.replace('-', '_')}"

    def parameters(self, role, prompt, description, mode):
        stem = re.sub('[^a-z0-9_]', '_', description.lower()).strip('_')[:40] or 'task'
        identity = hashlib.sha256((role + '\n' + description + '\n' + prompt).encode()).hexdigest()[:12]
        return {'task_name': stem + '_' + identity, 'agent_type': self.role_name(role), 'message': prompt}

    def wait(self, *, repo_root, result_path, assignment, attempt, mode):
        out = self.descriptor('host-wait', 'wait_agent', {'timeout_ms': CODEX_WAIT_MS},
                              assignment=assignment, attempt=attempt,
                              check=self.check('shell', repo_root=repo_root, result_path=result_path,
                                               assignment=assignment, attempt=attempt))
        out['wake_up'] = 'Global notification only; check this bound assignment/attempt/handle and exact marker. Unknown liveness stays unknown.'
        out['binding'] = {'assignment': assignment, 'attempt': attempt, 'result_path': result_path}
        return out


class OpenCode(Adapter):
    """OpenCode: the subagent tool runs a child in the foreground by default and returns
    when it ends; `background: true` returns a session id instead."""

    await_tool = 'shell'
    await_flag = {'background': True}

    def role_name(self, role):
        return role

    def parameters(self, role, prompt, description, mode):
        # OpenCode has no per-call isolation parameter, so no invocation carries one.
        out = {'subagent_type': self.role_name(role), 'description': description, 'prompt': prompt}
        if mode.background:
            out['background'] = True
        return out

    def wait(self, *, repo_root, result_path, assignment, attempt, mode):
        if mode.background:
            return self.marker_wait(repo_root=repo_root, result_path=result_path, assignment=assignment, attempt=attempt)
        return self.descriptor('blocking-dispatch', mode.tool, {}, assignment=assignment, attempt=attempt,
                               check=self.check('shell', repo_root=repo_root, result_path=result_path,
                                                assignment=assignment, attempt=attempt))


class Omp(Adapter):
    """OMP (Oh My Pi): the task tool runs a child; where it blocks it returns at the
    child's end, otherwise it returns a task id and the parent awaits the marker."""

    await_tool = 'bash'
    await_flag = {'background': True}

    def role_name(self, role):
        return role

    def parameters(self, role, prompt, description, mode):
        out = {'agent': self.role_name(role), 'description': description, 'prompt': prompt}
        if mode.background:
            out['background'] = True
        return out

    def wait(self, *, repo_root, result_path, assignment, attempt, mode):
        if mode.background:
            return self.marker_wait(repo_root=repo_root, result_path=result_path, assignment=assignment, attempt=attempt)
        return self.descriptor('blocking-dispatch', mode.tool, {}, assignment=assignment, attempt=attempt,
                               check=self.check('bash', repo_root=repo_root, result_path=result_path,
                                                assignment=assignment, attempt=attempt))


ADAPTERS: dict[str, Adapter] = {
    'claude-code': ClaudeCode(
        name='claude-code',
        modes={'blocking': Mode(name='blocking', tool='Agent', background=False, handle_source=None,
                                terminal_statuses=('completed', 'failed', 'killed'),
                                running_statuses=('running',),
                                no_execution_refusals=PRE_EXECUTION_REFUSALS,
                                conditional_handle_source='the agentId in an Agent result that carries no final report',
                                return_needs_final_report=True),
               'background': Mode(name='background', tool='Agent', background=True,
                                  handle_source='the agentId in the Agent tool result',
                                  terminal_statuses=('completed', 'failed', 'killed'),
                                  running_statuses=('running',),
                                  no_execution_refusals=PRE_EXECUTION_REFUSALS)},
        default_mode='blocking',
        # Per-call worktree isolation of a plugin-defined agent was observed top level and nested
        # (bionic/cycles/CYC-0117/evidence/build/isolation-probe.json, Claude Code 2.1.319).
        per_call_isolation=True,
        unverified=('terminal statuses of a task notification', 'dispatch refusals that prove no execution',
                    'listing semantics', "a top-level session's blocking behaviour", 'acceptance of the background flag',
                    "the background mode's handle while the child runs",
                    "which form a subagent's blocking call returns: the final report or an agentId"),
    ),
    'codex': Codex(
        name='codex',
        modes={'spawn': Mode(name='spawn', tool='spawn_agent', background=True,
                             handle_source='the agent id in the spawn_agent result',
                             terminal_statuses=('completed', 'errored', 'shutdown'),
                             running_statuses=('pending_init', 'running'),
                             no_execution_refusals=PRE_EXECUTION_REFUSALS)},
        default_mode='spawn',
        unverified=('wait_agent status names',
                    'dispatch refusals that prove no execution', 'listing semantics',
                    'the hand-back path at default depth'),
        hand_back=('Under the default depth a delegator running as a subagent may hold no working dispatch tool. '
                   'It returns this invocation, with its attach request and wait descriptor, to its caller; the caller '
                   'dispatches, attaches the handle, waits with the marker, delivers, then re-invokes the delegator, '
                   'which continues from inspect.'),
    ),
    'opencode': OpenCode(
        name='opencode',
        modes={'foreground': Mode(name='foreground', tool='subagent', background=False, handle_source=None,
                                  no_execution_refusals=PRE_EXECUTION_REFUSALS),
               'background': Mode(name='background', tool='subagent', background=True,
                                  handle_source='the session id in the subagent tool result',
                                  no_execution_refusals=PRE_EXECUTION_REFUSALS)},
        default_mode='foreground',
        unverified=('subagent parameter names', 'the background flag and its session id',
                    'background shell commands', 'session terminal statuses',
                    'dispatch refusals that prove no execution', 'listing semantics',
                    'completion notices for a background child'),
    ),
    'omp': Omp(
        name='omp',
        modes={'blocking': Mode(name='blocking', tool='task', background=False, handle_source=None,
                                no_execution_refusals=PRE_EXECUTION_REFUSALS),
               'background': Mode(name='background', tool='task', background=True,
                                  handle_source='the task id in the task tool result',
                                  no_execution_refusals=PRE_EXECUTION_REFUSALS)},
        default_mode='blocking',
        unverified=('task tool parameter names', 'whether the task tool blocks', 'the background flag and its task id',
                    'background bash commands', 'task terminal statuses', 'every waiting behaviour',
                    'dispatch refusals that prove no execution', 'listing semantics'),
    ),
}


def adapter(host: str) -> Adapter | None:
    return ADAPTERS.get(host)


def modes(host: str) -> tuple[str, ...]:
    """The dispatch modes a host offers, default first."""
    found = ADAPTERS[host]
    return (found.default_mode, *sorted(m for m in found.modes if m != found.default_mode))


def mode_of(host: str, mode: str | None = None) -> Mode:
    found = ADAPTERS[host]
    return found.modes[mode or found.default_mode]


def returns_handle(host: str, mode: str | None = None) -> bool:
    return mode_of(host, mode).handle_source is not None


def bind_wait_token(descriptor, assignment, attempt, token):
    """Bind only generated wait markers and await commands, preserving legacy adapter APIs."""
    if not token:
        return descriptor
    identity = f'{assignment}/{attempt}'
    def bind(value):
        if isinstance(value, dict):
            return {key: bind(item) for key, item in value.items()}
        if isinstance(value, list):
            return [bind(item) for item in value]
        if isinstance(value, str):
            if value == marker(assignment, attempt):
                return marker(assignment, attempt, token)
            return value.replace(f'--marker {identity} --timeout', f'--marker {identity}#{token} --timeout')
        return value
    return bind(descriptor)


def wait_descriptor(host: str, *, mode: str | None, repo_root: Path, result_path: str, assignment: str, attempt: int,
                    delivery_token: str | None = None) -> dict:
    """The wait descriptor for an open attempt, offered again by inspect for the next window.

    The invocation's own wait performs a blocking dispatch once. A mode that does not run in the
    background is never offered that dispatch again: the attempt has no complete result, so the caller
    is offered only the window-bounded marker await."""
    found, chosen = ADAPTERS[host], mode_of(host, mode)
    if not chosen.background:
        descriptor = found.marker_wait(repo_root=repo_root, result_path=result_path, assignment=assignment, attempt=attempt)
    else:
        descriptor = found.wait(repo_root=repo_root, result_path=result_path, assignment=assignment, attempt=attempt, mode=chosen)
    return bind_wait_token(descriptor, assignment, attempt, delivery_token)


def invocation(host: str, *, role: str, assignment_text: str, preamble_text: str, description: str,
               repo_root: Path, result_path: str, assignment: str, attempt: int, mode: str | None = None,
               integration_owner: str | None = None, delivery_token: str | None = None) -> dict:
    """The tool call the calling agent performs, with its attach request and wait descriptor.

    The prompt is the assignment text byte-for-byte followed by the engine preamble."""
    found = ADAPTERS[host]
    chosen = found.modes[mode or found.default_mode]
    out = {
        'host': host,
        'mode': chosen.name,
        'tool': chosen.tool,
        'parameters': found.parameters(role, assignment_text + preamble_text, description, chosen),
        'role_name': found.role_name(role),
        'isolation': isolation(host, role, integration_owner),
    }
    if host == 'codex':
        from copy import deepcopy
        out['interface'] = deepcopy(CODEX_INTERFACE)
    if chosen.handle_source:
        out['handle'] = {'source': chosen.handle_source}
        out['attach'] = {'request': {'op': 'attach-execution', 'assignment': assignment, 'attempt': attempt},
                         'caller_fills': ['op_id', 'handle'],
                         'purpose': 'bind the execution handle the host returned to this attempt'}
    elif chosen.conditional_handle_source:
        # No handle while the child runs. An agentId that arrives without the final report is one.
        out['handle'] = None
        out['attach'] = {'request': {'op': 'attach-execution', 'assignment': assignment, 'attempt': attempt},
                         'caller_fills': ['op_id', 'handle'],
                         'conditional': True,
                         'condition': (f'only when {chosen.conditional_handle_source}: the call returned an agentId '
                                       'without the child\'s final report'),
                         'purpose': 'bind that agentId to this attempt, then wait with the marker await'}
    else:
        out['handle'] = None
        out['attach'] = None
    out['wait'] = bind_wait_token(found.wait(repo_root=repo_root, result_path=result_path, assignment=assignment, attempt=attempt, mode=chosen),
                                  assignment, attempt, delivery_token)
    if found.hand_back:
        out['hand_back'] = found.hand_back
    return out


# ───────────────────────────── liveness and recovery ─────────────────────────────

def liveness(host: str, *, mode: str | None = None, state: str, host_status: str | None = None) -> str:
    """`unknown`, `running` or `terminated` for an open attempt; never inferred from time.

    Only a status the adapter lists, reported by the host for a bound handle, moves the
    answer off `unknown`. A reserved attempt has no handle, so the host has nothing to report."""
    chosen = mode_of(host, mode)
    if state != 'running' or host_status is None:
        return 'unknown'
    if host_status in chosen.terminal_statuses:
        return 'terminated'
    if host_status in chosen.running_statuses:
        return 'running'
    return 'unknown'


def loss_evidence(host: str, *, mode: str | None = None, state: str, kind: str, detail: str,
                  result_complete: bool = False) -> tuple[str, str] | None:
    """None when the report affirmatively shows the execution terminated or never started.

    Otherwise (code, problem), and the attempt must not be marked lost. `state` is the
    attempt's stored state (`reserved` or `running`); `detail` is the refusal class, the
    host status, or the quoted text the caller reports."""
    chosen = mode_of(host, mode)
    detail = (detail or '').strip()
    if state not in ('reserved', 'running'):
        return 'attempt-not-open', f'a {state} attempt is not open; there is nothing to mark lost'
    if result_complete:
        return 'result-arrived', 'a complete result is at the recorded path; deliver it instead of marking the attempt lost'
    if kind in NOT_EVIDENCE:
        return 'not-affirmative', (f'{kind} establishes nothing: the host may still have started or be running the '
                                   'execution, so liveness stays unknown')
    if kind not in EVIDENCE_KINDS:
        return 'unknown-evidence-kind', f'evidence kind {kind!r} is not one of {", ".join(EVIDENCE_KINDS)}'
    if not detail:
        return 'evidence-detail-missing', 'quote the refusal, status or confirmation the evidence rests on'
    if kind == 'dispatch-refusal':
        if state != 'reserved':
            return 'not-affirmative', 'a bound handle shows the dispatch call succeeded; a refusal cannot apply to it'
        if detail not in chosen.no_execution_refusals:
            return 'not-affirmative', (f'{detail!r} is not a refusal the {host} adapter lists as proving no execution '
                                       f'({", ".join(chosen.no_execution_refusals) or "none"}); a timeout or transport '
                                       'error may follow a started child')
        return None
    if kind == 'terminal-status':
        if state != 'running':
            return 'not-affirmative', 'a host status applies only to a bound handle; this attempt has none'
        if detail not in chosen.terminal_statuses:
            return 'not-affirmative', (f'{detail!r} is not a status the {host} adapter lists as terminal '
                                       f'({", ".join(chosen.terminal_statuses) or "none"})')
        return None
    if kind == 'blocking-returned':
        if chosen.handle_source is not None:
            return 'not-affirmative', f'the {host} {chosen.name} mode returns a handle and does not block until the child ends'
        if chosen.return_needs_final_report:
            if state != 'reserved':
                return 'not-affirmative', (f'a handle is bound to this {host} {chosen.name} attempt, so a returned call does not '
                                           'show it ended; wait with the marker or report a host status')
            if 'final-report' not in detail:
                return 'not-affirmative', (f'a returned {host} {chosen.name} call is evidence only when its result carries the '
                                           "child's final report; quote it and name `final-report` in the detail. A result with "
                                           'an agentId and no report is a handle, and an error with neither is not evidence')
        return None
    if kind == 'listing-absence':
        if not chosen.listing_authoritative:
            return 'not-affirmative', (f'the {host} {chosen.name} listing is not recorded as authoritative; absence from it '
                                       'does not show the execution cannot still start')
        return None
    # owner-confirmation: the owner's explicit words, quoted in the note.
    return None


def recovery_order(host: str, *, mode: str | None = None, observation: str, refusal_reported: bool = False) -> list[str]:
    """The recoveries for one attempt, in the order the caller tries them.

    `await-marker` waits on the end marker; `attach-execution` binds a handle the host
    showed; `deliver` records a complete result; `mark-lost` is always conditional on
    affirmative evidence (see `loss_evidence`) and never on elapsed time."""
    chosen = mode_of(host, mode)
    if observation == 'result-arrived':
        return ['deliver']
    if observation not in ('reserved-unbound', 'running-bound'):
        return []
    if observation == 'reserved-unbound' and refusal_reported:
        return ['mark-lost']
    steps = ['await-marker']
    if observation == 'reserved-unbound' and chosen.handle_source is not None:
        steps.append('attach-execution')
    return steps + ['deliver', 'mark-lost']
