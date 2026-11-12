---
name: cycle
description: "Plan, execute, resume, inspect, or update one development cycle. Use for major changes, minor changes, quick fixes, refactoring, simplification, releases, and reconciling the cycle record."
metadata:
  tags: "cycles, workflow, planning, implementation"
  bundles: "crux-docs"
  risk_level: "high"
  requires_access: "write-tree"
  triggers: "start a cycle | run the cycle | resume the cycle | cycle status | new dev cycle | iterate on this | quick fix | refactor this | simplify cycle | run a simplify cycle | simplify <area> | release cycle | update the cycle | reconcile the cycle record | add to the queue | show the queue | run the next item | run the next N items | run the queue | refresh cycle advice | show queue history | show the full queue | archive completed queue items | migrate the queue"
  routing_note: "One undertaking with type-specific phases, bounded passes, independent review, and shared test evidence; no prompt minimum or repeated runs."
---

# Cycle

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, OpenCode, and OMP (Oh My Pi). This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex, OpenCode, and OMP, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory (in OMP `bash`, `skill://<name>` resolves to the skill directory). In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, `.opencode/skills` in OpenCode (which also reads the singular `.opencode/skill`), and `.omp/skills` in OMP. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`; OMP uses `task`, `read`, `edit`, `write`, `bash`, `grep`, `glob`, `find`, `todo`, and `web_search` (where `read` also handles URLs and `skill://` URIs). Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode, `install-omp-agents` in OMP. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode and OMP use the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder` (in OMP, `scout` may also be used for reconnaissance alongside `wayfinder`). If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

Read the resolved project's objectives and operational schema before work. Resolve
`docs_dir` through the config reader; never assume the directory is named `docs`.
Use `uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --help` for supported commands.
For command-specific options, append the subcommand and `--help`.
Read [commands.md](references/commands.md) when creating plans or recording evidence.

## Route through the lead

The main session dispatches cycle execution to commander. Commander owns the
cycle, coordinates it and runs the cycle tools; it does no implementation.
The commander dispatches a dev-lead for every Build task and every fix task, and
never a developer. The dev-lead implements bounded work itself on the main checkout,
or fans independent units out to developers and integrates them on main. Developers
work in their own worktrees on a host that isolates each call, as Claude Code does;
on a host without per-call isolation the dev-lead implements units itself. The
commander keeps at most one Build or fix dev-lead attempt open at a time, whether
that dev-lead implements or fans out. The test coordinator is the
dev-lead dispatched for the task that runs the full checks, and with one dev-lead it
is that dev-lead. Full suites, the staged dry run and per-minor runs run only in the
test coordinator, one at a time; developers and reviewers run focused checks only.
In a linked worktree, `parallel_suite.py` refuses a whole suite root with the code
`focused-check-rule` unless `--allow-linked-worktree` is passed.

`prepare-dispatch` selects the dev-lead for a Build or fix task that names no role. A
dev-lead adds each developer unit with `task-add`, dispatches it with
`prepare-dispatch`, `role: "developer"` and `integration_owner: "dev-lead"`, and
integrates it with `child-link`. On Claude Code the engine
adds per-call worktree isolation to every developer invocation and to no other role's.
A developer whose promised isolation did not happen makes no edit and delivers
`blocked`; its dev-lead implements the unit itself or redispatches it. An explicit developer dispatch outside a dev-lead stays accepted for replay of
older records; its dispatcher integrates it. Other entry points use their designated
lead: tend-garden uses night-gardener, architectural planning uses architect, and
documentation filing uses historian. If the required role cannot be invoked, report
the gap rather than silently assuming its identity. Small tasks keep small plans and
reviews while retaining lead accountability.

An operational blocker stops the next legal action, needs no owner decision, and no
role the commander may dispatch can clear it within its grants: an unresolvable git
identity, a missing interpreter or tool, an integration the dev-lead reports it cannot
complete, an `index.lock` whose owner is unknown, or a refusal that names a missing
grant or role. An operational blocker returns to the main session without a pause. The
commander runs `inspect`, records a friction row with `cycle.py friction`, and returns
to its caller with the blocker, the quoted error, the inspect summary, the open
attempts and the next action after the fix. It runs no `pause`; the cycle stays
active. A dev-lead that meets one delivers `blocked` with no stop. The caller fixes the
cause and re-invokes the commander, which resumes from `inspect` and redispatches the
blocked task. When the caller cannot clear the blocker, it runs `pause --reason` with
a reason that names the blocker as an owner decision, or as a contradicted premise for
a missing grant or role. Owner decisions and the named stops still pause.

Parallel streams go to developers in worktrees under one dev-lead. No two agents edit
or stage source in the main checkout at the same time; the cycle writer's bookkeeping
commits are not source edits. The commander redispatches the coordinating task and
never a unit, and only a coordinating dev-lead redispatches a unit. `inspect` offers no
task that holds a developer reservation in the current pass. A dev-lead that needs a
change in another stream's path records a hand-over before editing: a `task-add`
Build task, assigned to itself, whose description starts `Hand-over:` and names the
path, the owning stream and the reason. It names the hand-over in its report to commander, who relays it; the owning
stream leaves that path alone until the hand-over task is done.

The coordinating dev-lead commits its own source, with `execution-check` on the staged
bytes, before it reserves any unit, and adds each unit with `task-add` immediately
before it dispatches that unit. From its first unit reservation until every unit task
is done or can take no next attempt in the pass, it makes no source edit and no source
commit on the main checkout. It then integrates the done units with `child-link` and a
two-parent merge whose message carries its own `Cycle-Task` trailer, and reports any
other unit in a blocked delivery.

When the latest attempt in the pass of a Build or fix task that is not done ended
blocked, failed or lost, the commander dispatches that task's next attempt before any
other Build or fix task, because another task's source commit makes that next attempt
refuse `execution-foreign-source`. This covers a coordinating task whose attempt was
lost while units are open. The commander reads the latest attempt in the `assignments`
of the full `inspect` output: its `state` is `lost`, or `finished` with
`delivery.outcome` set to `blocked` or `failed`. A task that can take no next attempt
in the pass, such as one at its attempt limit, follows the existing return or pause
route. A blocked delivery that names another Build task as its prerequisite goes to a
replan or a return, not a retry.

Before an editing attempt delivers blocked or failed, its worker runs `execution-check`
on the staged bytes, commits its owned work in progress under its own task's
`Cycle-Task` trailer and lists that commit in the delivery. The next attempt of the same
task admits the commit as same-task-resume. Bytes left uncommitted refuse
`execution-dirty-owned-paths` at the next reservation, and a commit with no matching
checkpoint, left by a crashed attempt, refuses `execution-foreign-source` after
`mark-lost`; a return to a new pass recovers both. Work-in-progress exception: after an
`execution-check` that refused `execution-foreign-source` or
`execution-source-outside-scope`, the worker commits with `git commit --only` naming
exactly that refused check's edited paths, under its own task's trailer and with no
passing checkpoint, because that check proved the paths owned. A developer in a worktree
commits on its worktree branch, and its next attempt reapplies the earlier delivered diff
in a fresh worktree as uncommitted edits and commits them itself. A checkout held by an
attempt that no agent can deliver and no host evidence can mark lost is an operational
blocker that returns to the main session, with no pause and no new stop reason.

Committed work in progress is unreviewed until Review, which covers the range from its
review base. A task first reserved after that commit carries it in its base, and its
worker re-verifies the inherited work with focused checks. A shortcut or abandoned
cycle, or a return to a new pass whose later review base follows the commit, can leave
such commits outside every Review range; the reflection lists them.

## Select the type

| Type | Scope | Phases | Maximum passes |
|---|---|---|---:|
| dev | Major changes; an approved IDR is required | Plan → Build → Verify → Review → Reflect | 7 |
| iterate | Minor changes | Plan → Build → Verify → Review → Reflect | 2 |
| refactor | Preserve functional behavior; improve structure or engineering efficiency | Plan → Build → Verify → Review → Reflect | 7 |
| simplify | Remove complexity without losing behavior; an approved selection IDR is required | Plan → Build → Verify → Review → Reflect | 3 |
| quick-fix | Small bounded corrections | Build → Verify → Review → Reflect | 1 |
| release | Publish one release target from a fixed step list | Release | none |

Limits count the initial pass. Records created before the rename show Test, which is the same phase as Verify, and plan and task input accepts either name. No type has a prompt minimum. Quick-fix has slim
Verify, Review, and Reflect phases. Capture its scope and success criteria without
inventing a Plan phase. Record constraints and verification with `plan-details`. A material decision or substantial planning changes its
type. Refactor records both unchanged behavior and the improvement to verify.
Functional changes require iterate or dev.

### Release cycles

A release cycle has one phase, Release, no Plan, Review or Reflect phase and no
pass limit. Create it with `--list beta` or `--list official`. The type carries the
step list, so nobody authors a release plan. Each step below is a task, in order.

- Beta list: prep, prepare, verify, beta-and-smoke, tag, record.
  - prep: bump the version surfaces and version records, promote the changelog,
    regenerate the generated release documents, check the release metadata and commit.
  - prepare: check the prep and bind the cycle to the release record.
  - verify: freeze the artifact. The release verify step (`release.py verify`) is the
    only step that runs the registered suites, and it reuses valid receipts.
  - beta-and-smoke: publish the artifact untagged to the pre-release target with
    `release.py beta`, then install the beta in isolation and inspect it (`smoke`).
  - tag: after smoke passes, tag the published tree and create the release.
  - record: keep the release record in the cycle and add one log entry.
    `release.py record --cycle` completes unheld steps and preserves open attempts
    for their delegator's normal delivery. The last listed delivery finishes the cycle.
- Official list: live-check-and-go-ahead, official, record.
  - live-check-and-go-ahead: take the owner's queued go-ahead, given after the beta
    was tagged, as the owner's attestation that the tagged beta was hand-tested,
    including any owed live check. A queued official item
    (`queue add --release-list official`) whose instruction names the version, or names
    none and whose title names the candidate, is the owner's go-ahead; `release.py official`
    records the attestation from the queue quote. A request that names no version runs
    the project's candidate command (in the Crux development repository
    `uv run tools/release.py candidate`) and relays its line as the chosen version. The
    agent collects no version and no live-check note from the owner on this path.
  - official: publish the tagged pre-release tree to the public target with
    `release.py official`, which tags it in the same act, then run record.
  - record: keep the release record in the cycle and add one log entry.
    `release.py record --cycle` completes unheld steps and preserves open attempts
    for their delegator's normal delivery. The last listed delivery finishes the cycle.

A capable dev-lead may opt into fixed-list `release-continue` at initial dispatch.
The frozen invocation binds the cycle, list, target, integration owner, commands and
authority limits. Beta keeps six logical tasks; official keeps three. Each retains its
own counted attempt, immutable base, current marker, report, command result and evidence.
After the actual command succeeds, continuation retains that exact marked report and
reserves the next eligible task on the same attached host handle. The returned context
delta supplies its fresh marker. It requests no new native dispatch or attach and proves
no liveness. The engine never executes repository command text.

The loaded role must grant `release-continue`; actual host evidence must establish all
required capabilities. Unknown or missing support uses ordinary per-task dispatch.
Regenerating roles proves no installed reload. Failure, interruption, denial, an owner
stop, stale token, wrong handle/list/target or changed artifact stops continuation.
Another host needs normal dispatch/attach. Replay completes pending bookkeeping without
repeating an external act. The existing artifact/target authorization and bare publish
commands remain binding; beta never authorizes official.

Optional `tools/crux-release.json` supplies literal prep scope, targets and fixed argv
arrays. Queue capture completes known mandatory prep scope before authorization.
Creation/start refuses omissions before allocation; never widen frozen queue authority.
The descriptor does not replace editorial duties, the owed live check or owner words.

The project's release runbook maps each step to its commands. A release adds no
step, gate or owner stop beyond its list.

Authorizing a release queue item also authorizes publishing that item's version to its
target. It authorizes no push and no other outward action. The publish command takes
the owner's quote from the queue chain, so the agent runs it in its bare form. In the
Crux development repository that is `uv run tools/release.py beta --version X.Y.Z` or
`uv run tools/release.py official --version X.Y.Z --cycle CYC-NNNN`, with no
environment prefix, compound command or redirection. When the host denies it, quote the
denial and hand the owner that one bare command, which carries no quote. A changed
artifact, or a release not started from the queue, needs the owner's new words: hand the
owner the command with its `--authorization` quote placeholder, and never supply the
words yourself.

### Simplify cycles

A simplify cycle removes complexity and keeps behavior. Plan starts with the
architect assessing recent decision-driven changes or a named feature or code area.
The architect records one selection IDR whose contents add `assessed`, `proposals` and
`selected` to the usual keys. Each proposal has `id`, `removes`, `retained_behavior`,
`objectives`, `decision_clauses`, `expected_savings`, `verification` and `paths`.
`selected` lists proposal ids; unselected proposals stay recorded. The plan scope must
cover every path the cycle changes in all four areas: production, tests, instructions
and execution.

The approval of that exact IDR revision selects the proposals. The owner's approval
always suffices: present the exact revision, then record the actual explicit answer
through `owner-decision present/capture/apply`. The legacy
`owner-approval --print-command` route remains available. Council approval selects only for a queue-started cycle whose plan
scope lies within its queue item's frozen scope. This includes a queue-started cycle
change-typed into simplify. Queue authorization approves no IDR. Without that authority,
the cycle pauses for an owner decision.

In Verify, record `reduction` for the current pass: per area production, tests,
instructions and execution, `decrease`, `unchanged` or `increase`, with before, after
and evidence. An area's dimensions are its concepts, branches, states, dependencies,
configuration, fixtures, mocks and operational steps, as they apply, not only lines.
Each area's `before` and `after` name every dimension that changed. An area is
`increase` when any dimension rises. It is `decrease` only when one falls and none
rises. Areas are never netted. Any `increase` refuses Verify and Reflect: report it
and propose it as different work (a queue item or an owner report), then `return`
or abandon. A cycle with no `decrease` is also refused. The reduction joins the review
basis, and the reviewer checks the diff against the selected proposals.
`change-type` out of simplify needs `--human-approval`.

## Create or resume

Use `create` with type, title, goal, scope, acceptance criteria, implementer, and
test coordinator. The script allocates a single cycle record under
`<docs_dir>/cycles/<CYC-NNNN>/cycle.json` (with the configured artifact prefix).
For a type with a Plan phase, `create` seeds one Plan task, `plan`, so the first
`inspect` offers its `prepare-dispatch`. The plan writer may mark its Plan-phase
tasks done in the plan file, so no separate task call follows the plan.
Use `show` to inspect it. A status request reports state without advancing it.
For a readable progress view, run `cycle.py status`, as the `cycle-status` skill does.
Use `resume` for the same paused undertaking; never create another run of it.
Completed, abandoned and shortcut cycles stay closed. Follow-up work gets a new cycle.

The schema and writer own record shape. Mutate through `cycle.py`; do not edit
phase, pass, history, evidence, or approval fields by hand. The `plan` and `task`
commands record work across all phases and preserve previous plans. Scope,
constraints, acceptance criteria, verification, and expected evidence must be
concrete enough to review. Tasks can evolve; retain the reasons.

Record explicit stream ownership in optional `plan.streams` entries
`{id, paths, independent}`. Paths are literal repository-relative scopes; independent
streams cannot overlap. A Build task's optional `integrates` lists at least two
existing Build dependencies also present in `depends_on`. The writer validates
these facts. Missing historical fields mean no declared streams or integration;
never infer them from prose.

The dev-lead delegates independent implementation units with explicit ownership and context.
Pass objectives, outcome, evidence, constraints, current phase/pass, approved
record revisions, and the relevant policy in every assignment. The commander
coordinates and runs the typed operations itself, through the inline form below, to
keep the record current. The author of authored content (dev-lead, architect,
historian) writes it. Content another agent authored and returned to you, such as a
review report, is submitted through that command's `--json` form. The historian handles synthesis and documentation that need
judgment, never clerical record work. A developer never reviews its own change.

Every assignment names the full base commit SHA, assigned paths and integration owner.
`prepare-dispatch` renders the mandatory role boundary, objectives, task, expected
evidence, acceptance criteria, constraints, scope, decision bindings and integration
owner from the record. `assignment_text` is an optional subordinate addendum.
Perform its native-role invocation; the host's role contract and tool grants remain
binding. Read the exact role source when required. Missing role capabilities are
reported, never silently substituted. The engine adds the result path, the task base
and the completion marker. Commit the
source a unit needs before dispatch. The dev-lead owns worktree integration, verifies
ancestry and changed paths, integrates committed units, and obtains valid
related-check evidence. Copying a diff without accounting for its base, evidence, and
integration is not completion.

## Typed operations

Code owns the bookkeeping; you own the judgment. Run `inspect`, then the action it
returns. `inspect` reads the record and reports the phase, pass, unmet requirements,
every attempt with its observation, and the next actions as requests ready to submit.
Every operation is one call with one JSON request:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" op CYC-0001 --json '{"op":"inspect"}'
```

The commander passes the request single-quoted and inline, with no file and no pipe.
Inside a JSON string it writes an apostrophe as `\u0027` and a newline as `\n`, for
example `"note":"owner said:\nit\u0027s gone"`. `--json -` (standard input) and
`--file PATH` serve roles whose shell permits them. Every command that takes `--file`
(plan, review, decision, reflect, task-add, coverage, plan-details, owner-complete,
reduction) also accepts `--json REQUEST` or `--json -` with the same content. A
single quote inside the single-quoted argument is written `'\''`. Every `--json`
option also accepts `'@PATH'`, which reads the request from a file inside the
repository. A role that can write a file submits a long request this way, such as an
assignment with quotes and newlines, without escaping it. Every command that takes a cycle
accepts it positionally or as `--cycle CYC`. A mutating request carries an
`op_id` of 8 to 64 characters from `[A-Za-z0-9._-]`; a repeat of the same request
replays the recorded result. `commit-record` is the exception: its `op_id` is optional
and not journaled. [commands.md](references/commands.md) gives each request.

- `inspect` is read-only and takes no `op_id`. `{"op":"inspect","summary":true}` prints
  only the position, unmet requirements, next actions, open attempts with their state
  and recovery, problems and record state. Use it to pick the next action. The full output returns `reusable_evidence`, a typed
  `advance` action that carries `expect_revision`, the low-level `return` and `pause`
  argv, the low-level `checks`, `coverage` and `review` argv for an unmet Verify or Review
  declaration (the caller writes its content), and for each open attempt its `recovery`
  list (ordered), its `window` and its `liveness`. Liveness is unknown unless a host reports a status the adapter lists.
  `problems` names an `orphan-retained-result` or a `result-path-missing`, and a lost
  attempt carries `leftovers`, the plan-scope paths still changed.
- `prepare-dispatch` reserves the next attempt of a task and returns an invocation: the
  host tool, its complete parameters, the attach request and the wait descriptor. An
  optional `mode`, one of the host adapter's modes, is stored on the attempt and
  selects the invocation, whether the host returns a handle (and so whether
  `attach-execution` applies) and the recovery and loss-evidence rules for that mode.
  Its mandatory assignment precedes any optional caller addendum and generated engine
  facts. The invocation states isolation and the integration owner; the preamble names
  the engine path. The calling agent
  performs it with its own dispatch tool, never through the cycle writer.
- `attach-execution` binds the handle the host returned. A handle-less mode skips
  `attach-execution`; reserved followed by `deliver` is its normal path.
- `deliver` retains a complete result once and records the attempt, its commits and
  evidence. A repeat of an identical delivery changes nothing. A blocked delivery may
  retain `stop: {kind, note}`; an explicit stop suppresses semantic failure routing.
  A stopless block lists the pause beside any offered route. A listed release's final
  delivery also finishes the cycle; a refused finish stays visible in the response
  and `inspect`, while the delivery remains committed.
- `mark-lost` ends an attempt that affirmative host evidence shows terminated or never
  started, and returns its task to pending. Its request carries `evidence`
  (`{kind, detail}`) and `note`.
- `advance` applies the next legal transition. It attaches a matching reusable receipt
  and never executes a check or attaches a failure. It does not change the return or
  pass-limit policy.
- `finish` completes the cycle from Reflect.
- `owner-exception` is the owner's exceptional close, recorded as a history event.
- `upgrade` converts an older record (see below).
- `commit-record` commits pending cycle bookkeeping, excluding queue-owned paths. Its optional `op_id`
  is echoed and is not journaled (see Commits and reports).
- `withdraw-decision` withdraws an IDR in Plan (see Decisions).
- `advice-refresh` optionally batches recorded advisory questions; routine operations never call providers.
- `child-link` declares a completed child for an active dev-lead integration.
- `release-continue` delivers a fixed release step and returns the next context on the same bound host.
- `execution-check` verifies source provenance and commits its proof bookkeeping.

### Dispatch and waiting

At reservation, the engine retains the complete rendered invocation and selected
context in an immutable, scanned bundle bounded to 1 MiB. On takeover use the
read-only `dispatch-invocation` operation, without the original prepare request.
It returns the frozen message, addendum, preamble, native parameters and context
bindings. Initial dispatch checks current role/grant/source bindings; stale inputs
refuse. Replay never rerenders from changed context. Running/closed attempts expose
retained context without another dispatch; historical missing snapshots report
unavailable-original-context. Token rotation preserves earlier snapshots.

Read every selected body completely through its retained reference. Keep the
canonical origin and source directory for relative references. A reference proves
no read; failed retrieval is unavailable context, never permission to omit a body
or substitute mutable source. Full inspect lists `context-read` references and argv.
The reader admits only canonical repository/plugin context and exact bound reports.
It returns 16 KiB UTF-8 byte pages, path, size and full digest. Follow `next_offset`
with the original `--sha256` until complete. Objects over 1 MiB, invalid UTF-8,
credential paths, unsafe content, symlinks and unavailable scanners refuse without
content. Native readers remain usable under existing grants; no arbitrary shell
reader, network capability, installation or reload follows from this interface.

Wait as the invocation's wait descriptor says, and never with `sleep`. New dispatches
use the exact generated tokenized marker, `Result-End: <assignment>/<attempt>#<token>`.
Historical tokenless attempts retain `Result-End: <assignment>/<attempt>`. A result is
complete only when its last line matches the attempt's current marker; the marker
form `cycle.py await --marker` returns when that line is present. Arrival proves the
result is whole, not that it is right: read the report, then `deliver`, which retains
it once. The adapters name these default modes: Claude Code (`Agent`, role `crux:<role>`,
`blocking` by default: the call carries no background flag and, from a subagent,
returns with the child's final report or, as observed on Claude Code 2.1.319, with an
agentId and no report (a top-level session is unverified), with a `background` mode that sends the flag and expects the
agentId while the child runs); Codex (`spawn_agent`, role `crux_<role>`, agent id handle, with the
hand-back route below at default depth); OpenCode (`subagent`, foreground and handle-less
by default, with a `background` mode that returns a session id); OMP (`task`, blocking
and handle-less by default, with a `background` mode that returns a task id). The
engine waits on the marker form only, in windows of 30 minutes. A blocking invocation
performs its dispatch call once: never repeat the call for the same attempt, because
`inspect` re-offers only the marker await and the `mark-lost` routes. An agentId that
a Claude Code `blocking` call returns without the child's final report is a handle:
submit the conditional `attach-execution` from the invocation and wait with the marker
await. A dev-lead runs parallel units concurrently in the `blocking` mode only when it
issues their `Agent` calls together in one turn, after a `prepare-dispatch` for each.
A part of a descriptor not yet observed on that host is unverified: Claude Code's
terminal statuses and refusal classes, a top-level session's blocking behavior, the
acceptance of the background flag and the background mode's handle while the child
runs, OpenCode's parameter names, background flag and statuses, and every
waiting behavior on OMP. Codex's exposed spawn contract requires `task_name`,
`agent_type` and `message`; wait uses only `timeout_ms`, no `ids`, and at most
60000 ms per call. A global wake-up proves no child completed: attribute the result
through its recorded handle/attempt and exact marker. Uncapped overall windows and
unknown-liveness rules remain. Record the actual host/interface and exposed version;
an unexposed version stays unknown. Static fixtures and generated roles establish
no fresh native host injection. Distinguish actual observations from unobserved
Claude Code/OpenCode/OMP behavior. Report
planned, dispatched, confirmed running, completed, failed, and unknown work
separately, and report unknown liveness as unknown.

Under Codex's default depth a delegator running as a subagent may hold no working
dispatch. It still authors the assignment and calls `prepare-dispatch`, then hands the
invocation back to its caller. The caller performs it, submits `attach-execution`,
waits and submits `deliver`, then re-invokes the delegator, which continues from
`inspect`.

### Loss and limits

`execution-check` commits its exact proof and cycle bookkeeping through the writer's
normal deferral policy. A successful commit needs no separate proof flush or handback.
An unchanged proof replays only across its own validated writer checkpoint; other
bookkeeping changes require a fresh observation. Never remove an unknown index lock.

Before pausing, seal pending owned worktree bytes and index identities. Same-execution
resume may admit those exact bytes after token rotation only with the same bound host
handle, checkout, immutable review base and validated ancestor proof. Changed sealed
bytes, foreign edits, unrelated ancestry or another execution require normal recovery.
An `edited_paths` list alone proves no ownership. Never reset, restore files around a
check, accept a stale marker or exempt source by a trailer or directory name.

An active dev-lead can use `child-link` to declare a completed child without reopening
its own task or changing its marker/base. Integration proof admits exact delivered child
commits with retained marked reports and checkpoints. It also admits an exact two-parent
merge whose tree equals conflict-free built-in `git merge-tree` output. Unknown children,
extra edits, manual resolutions and custom merge drivers refuse. Retain registered child
checkouts until parent proof and delivery finish. An undeclared child that is a done,
delivered task of this cycle is admitted as `cycle-task-source` or `cycle-task-merge`.

Workers keep the immutable task base as the original review base. Before edits,
use `execution-check` with a fresh op_id, current assignment/attempt and registered
checkout. Proof accepts bookkeeping descendants or retained same-task source and
records the separate execution HEAD. Never reset a base, trust a commit subject or
ignore all docs. Follow ff-only recovery for a clean older checkout; foreign source,
unrelated ancestry and dirty initial source use normal isolation/integration.
Before a source commit, stage intended edits and checkpoint exact `edited_paths`.
Each task-trailered source commit may include a nonempty sealed subset only,
with unchanged object identities. Recheck after unexpected HEAD changes. Routine
bookkeeping proof refresh requires no handback. The commands reference defines fields.

Before resuming the same open host execution after a hand-back, run the resume
command `inspect` returns, then relay its new marker to the worker. The writer keeps
the previous result and rotates modern delivery tokens. Cycle resume also rotates
modern open tokens. A stale marker cannot satisfy the resumed invocation.

`mark-lost` needs affirmative host evidence, quoted in its note: a dispatch-call
refusal the adapter lists as proving no execution was created; a host status the
adapter lists as terminal for a bound handle; a blocking handle-less dispatch that
returned without a complete result (for Claude Code, a returned `Agent` result that
carries the child's final report, with `final-report` in the detail, reported only by
the caller that saw it return and refused once a handle is bound); absence from a host listing the adapter records as
authoritative; or the owner's confirmation, quoted, that the execution terminated or
never started. A timeout or transport error from the dispatch call, an error from a
wait, an expired wait window, a missing result and absence from a listing that is not
authoritative establish nothing. Elapsed time never makes an attempt lost. The evidence kinds are `dispatch-refusal`,
`terminal-status`, `blocking-returned`, `listing-absence` and `owner-confirmation`;
`dispatch-error`, `wait-error`, `status-error`, `window-expired`, `result-missing` and
`elapsed-time` are never evidence. Every adapter records its listing as not
authoritative. `mark-lost` refuses `result-arrived` when a complete result is at the
path (deliver it) and refuses an attempt with no recorded host (the recovery is the
low-level `assignment --state lost`). `inspect` orders the recoveries of an open attempt:
await the marker, `attach-execution` (handle modes only), `deliver`, then `mark-lost`
on evidence. The adapter names `mark-lost` alone after a reported pre-execution refusal.
Never
message an agent whose attempt is still running; a resume starts a duplicate run.

A task and role get three attempts in one pass, of any outcome and across assignment ids.
After that, `prepare-dispatch` refuses `attempt-limit`. A counted `return` is offered only in
Verify/Test or Review with a remaining pass, outside fixed release lists; otherwise
stop or pause. A wait window lasts at most 30 minutes, and windows are uncapped. Ending one
pauses nothing, changes no state and is no escalation stop: `inspect` returns the wait
descriptor again and the caller starts the next window. No liveness, loss, pause or
escalation is inferred from elapsed time. An attempt whose host session died silently,
or whose dispatch call failed with an error the adapter does not list, therefore waits
without bound. The caller reports it each window, quoting any error, and only the
owner's statement then leads to `mark-lost`. An `Agent` error that carries neither a
final report nor an agentId is evidence only when it is a listed refusal; otherwise
only the owner's statement leads to `mark-lost`. A host that rejects the background
flag returns the listed `invalid-parameters` refusal: mark the attempt lost quoting it
and prepare a second attempt in `blocking` mode, waiting on the assignment and attempt
the invocation names, which spends one attempt and is no pause. Claude
Code `background` attempts recorded before the `blocking` mode, and already bound,
leave the lost route only through the owner's statement, because no task notification
reports a terminal status for them (a complete result still delivers). This is a stated limit for the owner to
judge in the beta. After a missing-grant refusal and the cycle's resume, mark that
attempt lost with the quoted refusal when the adapter lists it, otherwise with the
owner's statement; it counts as one of the three attempts. A cycle paused under the
removed window limit keeps its recorded reason and resumes normally.

A refusal carries a `code`, plus field, expected, observed, problem and recovery, where each
recovery is a complete request or argv and the caller fills only the fields it names.
Resolve the cause the refusal names; do not retry the same request.

### Completion

`finish` takes `lessons` and `remaining`, because lessons and remaining need judgment;
`["none"]` is an explicit answer. The schema marks both optional, and `finish` refuses
without them except on a listed release cycle. The routine outcome text is generated from the
acceptance criteria, delivered tasks and the latest review verdict. Commit the
intended changes first: `finish` records the completion commits and refuses a scope
change that is not committed.

`finish` also removes the cycle's own agent worktrees. It removes a linked worktree
under `.claude/worktrees` only when its branch tip carries a `Cycle-Task:` trailer
naming a task of this cycle, is an ancestor of HEAD and has a clean tree, with
`git worktree remove` and then `git branch -d`, never `--force` or `-D`. A detached or
locked worktree is kept. Its response carries `worktrees: {removed, kept}`, which lists
every other linked worktree with the reason it stays.

`owner-exception` records the owner's exact words and conversation reference, the
unmet completion requirements unchanged and every open attempt, in a history event
`owner-exception` whose `owner` field has the shape `owner-complete` writes. Use it only on an
actual owner instruction; references are optional and never invented. No agent or
council grants it.

`shortcut` closes a stopped cycle whose delivered work has gaps. Only the owner's quoted
request sets the status `shortcut`; `inspect` never offers it, and no agent, council or
classifier runs it. When the owner asks to close a cycle as a shortcut, record the
reflection with `reflect` (its outcome names the delivered work and where it lies, and
its remaining list names the gaps), run `shortcut CYC --present`, show its output to the
owner, and quote the owner's reply into `shortcut CYC --file`. Never use
`owner-complete` for a closure with gaps. Any other caller is refused with a named code,
a shortcut cycle never restarts, and a release cycle never closes as a shortcut. The
commands reference lists the refusal codes in order.

### Route classification

Routine cycle operations use only current, locally validated cached advice and make
no provider request. This includes prepare/inspect, dispatch retrieval, execution proof,
attach, delivery, ordinary advancement, review boundaries, finish and release continuation.
Missing advice returns immediately to the responsible agent without an approval step.
Explicit `create --type auto`, queue items explicitly typed `auto`, and optional
`advice-refresh` are the intentional classifier request paths. Explicitly typed queue
items keep their type without a sizing request.

Say “refresh cycle advice” to request `advice-refresh`. It batches admitted questions
about recorded tasks, assignments, findings or failed receipts. It is never a prerequisite
or an automatic delivery tail. One five-second cooperative discovery/transport budget
bounds the refresh; exhaustion returns unavailable. A filesystem or Git call already
running cannot be preempted. Each answer has independent validation and fallback.
Current input fingerprints, privacy scans, configured model/endpoint, denial policy,
opt-out and deterministic review/test/authorization gates still apply. Replaying an
operation ID does not issue another request.

Task/role domain eligibility filters optional context before ranking. Broad repository
scope alone admits no skill. Mandatory role/project instructions and expressly required
workflows remain. Compare the invocation's required capabilities with actual known host
evidence before dispatch. Unknown support stays unknown; report known gaps before work.
Never route a read to a role whose contract forbids the only available reader.

Project-local skills pass the same domain filter. An invocation offers at most 8 of
them, from the roots of the attempt's recorded host, after the plugin candidates. A
local skill is eligible when the task description names its id or contains one of its
`metadata.domain_terms`. Scope paths never admit one. The listing refuses a symlinked
or escaping path, an id that shadows a plugin skill and a frontmatter that declares a
tool grant. A refusal never fails the dispatch. Local candidates change only prompt
text and widen no grant. When a host root holds a usable local skill, the preamble asks
for one `Local-Skill-Used: <id> ok` or `Local-Skill-Used: <id> partial` report line
per use. The role then writes no `used` or `evaluated` forge-log entry. The record
commit of a completed cycle writes each reported use as a `used` entry in the forge
log. The commands reference gives the fields and the known limits.

`inspect` exposes recorded classifications and current cached suggestions. Suggestions
select only permitted routes and establish no correctness, authorization or test pass.
Compare their premises with retained evidence before acting. Missing or contradicted
advice leaves deterministic legal actions available. Keep the recorded review floor.
Use `cycle.py defer` for follow-up findings. A finding is deferred in Review, where its
report was recorded: `cycle.py defer` refuses a finding in any other phase, so Reflect
cannot defer one. A sizing fallback prints a receipt for
`create --sizing-receipt` after the responsible agent chooses the type.
Finding disposition offers `return` only for a blocking finding. Advisory and cosmetic
findings never spend a pass.
`.bionic.yml` `decisions: {classifier: off}` opts out. Historical classifications retain
their original interpretation. Every classification remains readable in
`inspect` (`classifications`) and in the `finish` response. These retain
each question, answer, route or fallback, serving model/provider and reported cost.
`cycle status` and the dashboards show only the line `Classifications: N`,
where N is the number of classifications the cycle record holds.

### Older records

Typed mutations on a version-2 record refuse `needs-upgrade` and return the upgrade
request; a version-1 record keeps the low-level commands. `upgrade` refuses
`assignments-running` while legacy assignments run, and returns the low-level
`assignment --state finished` argv, to run after the legacy agent's final report, and a
conditional `--state lost` argv that needs the same affirmative evidence. `upgrade`
keeps the version-2 bytes under the cycle's `upgrade/` directory, so rollback restores
them. `create` writes version-3 records. `upgrade` writes `upgrade/v2-cycle.json`, the
prior record byte for byte, and an `upgraded` history event carrying `previous_sha256`;
a different file already at that path refuses `upgrade-backup-conflict`. Restoring the retained bytes discards everything recorded since the upgrade, and a
cycle created under the beta has no version-2 form. The previous release cannot read version-3 records.

## Execute the phases

- Plan: establish the outcome and tasks, select scrutiny, resolve material choices.
  Order the tasks so the first Build task delivers one working end-to-end path
  before the remaining units. When Build splits into streams, give each test that
  asserts instruction text to the stream that owns that text. A stream that changes
  behaviour such text describes reports the wording to the owning stream and leaves
  the test alone.
- Build: implement the plan. Do not hide test/review retries inside this phase.
  Build checks include, besides focused tests, every test that imports, invokes,
  reads, globs or enumerates a changed path; when a test enumerates a directory
  that holds a changed path, select the suite that contains it. The test coordinator
  records the complete set once the streams integrate, with `checks --phase build`;
  each call replaces the set. Build ends only when every Build check has current
  passing evidence, and Verify reuses it while inputs are unchanged.
- Verify: use the shared evidence policy in [testing.md](references/testing.md).
  Every test runs once per code state in the main run on the floor minor. A
  decision-only commit to the docs tree leaves its receipts reusable; Verify declares
  drift-gates, governs-references and governs-coverage, which keep the decision records
  as inputs. The per-minor checks are the flagged list and the health check against
  the staged artifact.
  Compare observed behavior with acceptance criteria. A known acceptance failure
  returns immediately to Build (or takes the fix step), even if automated checks pass.
  Do not send a known blocking defect to Review merely to obtain the same finding.
- Review: commission independent review under [review.md](references/review.md). A
  review binds when its report scope covers every plan scope path, a parent directory
  entry included; a report that omits a plan path is refused `review-scope-incomplete`
  and names the uncovered paths. Review covers the range from its review base, so it
  misses committed work in progress left by a shortcut cycle, an abandoned cycle or a
  return to a new pass; the reflection lists those commits. A demonstrated defect
  blocks only as a plausible failure within the operating assumptions.
- Release: run the fixed step list the cycle carries, one task per step. Agents run
  every step, including the bare `release.py beta` and `release.py official` commands;
  the owner runs a publish command only after the host denies it. Publish
  only under the owner's own words, quoted, for the exact artifact. Do not blindly
  repeat an external action after a failure. The release verify step is the only step that runs the
  registered suites and it reuses valid receipts; see [testing.md](references/testing.md).
- Reflect: record delivered criteria, lessons, remaining work, and follow-up
  references. A few sentences suffice for quick-fix. Proposed process changes
  do not silently expand the cycle. Abandonment also requires reflection. A listed
  release cycle has no Reflect phase and abandons without one; its record step keeps
  the reason.
  Before completing, commit the intended changes; `finish` records their full SHAs.
  Explain remaining uncommitted work. On a version-3 record the owner-directed
  exceptional close, including an owner's request to leave changes uncommitted, is
  `owner-exception`, quoting the owner. The low-level `completion --exception` and
  `owner-complete` remain for version-1 and version-2 records and diagnosis. The
  writer does not grant permission to invent an exception.
  Do not leave a completed cycle uncommitted.

Record evidence, decisions, review, and reflection using their respective
commands, then `advance`. A command's success records a transition; it is not
proof that an agent performed the described work.

## Decisions

For explicit conversational IDR approval, new-policy ADR acceptance, or an owner's
change to the cycle's acceptance criteria (purpose `acceptance-change`), use
`owner-decision present/capture/apply` through cycle.py. Present the exact subject
and digest before the answer. A trusted owner-facing caller transcribes only an
actual explicit answer with verbatim words, real conversation/message or tool-question
reference and owner-local date. Ambiguous continuation is pending; neither the writer
nor a classifier invents disposition or provenance. Reject/pending cannot approve.
Fresh application requires current digest and the unique unsuperseded approval
under the mutation lock, plus the existing council/lifecycle checks. A correction
is an immutable superseding capture in that revision's lineage. Already-applied
replay acknowledges the existing receipt and later disposition without reapplying
or revoking historical standing. No owner terminal command is required. This grants
no pass extension, owner exception or outward authorization. See the commands reference.

For an ADR acceptance, `apply` writes the ADR's lifecycle bytes and its record under
`adrs/acceptances/`, and commits neither. Run `apply` inside the accept task: after the
task's clean-start `execution-check`, the task runs `apply`, checkpoints both paths as
`edited_paths` and commits them under its `Cycle-Task` trailer. An `apply` run outside
a task leaves dirty owned paths, and the next dispatch refuses them.

An acceptance criterion changes only in Plan or Build (`acceptance-change-phase`).
Compare each criterion with what Build produced before advancing out of Build, and
raise a needed narrowing there. From Verify or Review, a narrowing needs a return to
Build, which spends a pass; at the pass limit it also needs an owner-approved `extend`.

Every role that a cycle task dispatches runs `execution-check` before its first write,
generators included, and delivers with nothing staged or uncommitted. The plan scope
names the journal and log paths the Reflect entry writes, and the ADR and
acceptance-record paths of an accept task.

Gateway cycle councils convene detached by default. Initial success reports a
running attempt and its `await_command`; it establishes no approval. Use that command
(`--await ATTEMPT`) for the terminal result, then record the architect disposition.
`--foreground` is the synchronous diagnostic form and `--probe ATTEMPT` reads the
attempt flock. `--recover ATTEMPT` sends no request: it refuses a held flock,
recovers the original persisted result, or closes an unowned attempt as interrupted.
The interrupted attempt still counts. Never delete or hand-edit a record to retry.
A missing launcher acknowledgement proves nothing: after the exact child ends,
the launcher checks its exact claim identity and recovers a claim that already exists.
Do not replace infrastructure recovery with an owner design approval. Native Lite
keeps its separate sealed-dispatch procedure.

Full inspect adds exact subject/attempt/result references and supported recovery
argv with prerequisites. It makes no provider call, writes no attempt and recovers
nothing. New gateway request/outcome checkpoints are mandatory under the existing
attempt ownership. A persistence failure stops further calls and positive approval.
Durable negative findings survive; an unrecorded in-flight outcome stays unknown.
Recovery sends no request and resets no attempt budget. Events never independently
approve; later convening uses prior findings as historical context beside fresh votes.
New approval/application revalidates current bound events. Pure sealed historical
validation and already-applied acceptance retain their original standing.

Every dev requires at least one IDR. Other types require an IDR for a material
implementation choice with alternatives or tradeoffs worth preserving. Council
must approve its exact revision before dependent implementation. Revised choices
need fresh approval; earlier reasoning stays readable and carries no authority.

Council may also advise on a decision. Consultation never implicitly approves
an IDR or ADR. Use the council runner and its configured mode. Historical
promptbook councils retain their original gateway-only interpretation.
Council deliberation rounds are distinct from cycle passes.

IDR councils run in Plan. For every approved IDR the architect records an agreement
naming the approved sha256 and each nit with `apply-in-build` or `declined` (with its
reason); a nit never starts another attempt. A council result whose votes suffice
and that lacks only the architect agreement reports the outcome `awaiting-architect`,
exits 1 and prints the `--architect PATH --record RESULT` command; it is not a
rejection. A new revision of an IDR whose earlier
revision was approved is reviewed as a delta: the writer stores the changed top-level
keys in the attempt, the seats judge the change against the full revision, and approval
binds the new revision's sha256. `inspect` and `cycle status` list each decision's
council rounds: attempt, outcome, and the reason convened (`initial`, the progress
text, or `delta revision`); `architect-settled` is an outcome, not a reason.

A council dispute never goes to the owner. When a council cannot approve an IDR within
its attempt limit, or the same blocking finding recurs on two consecutive attempts after
a revision that addressed it, the architect withdraws the record in Plan: run `inspect`,
then `withdraw-decision` with the IDR name, a reason and the ids of the plan tasks that
depend on it. A Standard-mode single-seat dissent that the architect disposes as
`accepted-tradeoff` on an approved attempt is answered, not unanswered; it does not
count toward the recurrence trigger, and neither does its repetition on a later
attempt over the same subject bytes. A finding counts toward recurrence only when it
blocks approval of an attempt. One write marks the name withdrawn and removes those
tasks from the plan; the `plan-revised` event keeps them. Record the follow-up with `cycle.py defer CYC
--decision NAME --note TEXT`; the entry keeps the reason and the attempt history. A
withdrawn name accepts no revision, approval or council attempt. A narrowed replacement
carries a new name and `replaces: <withdrawn name>`; its attempts continue the withdrawn
record's count, so a rename never resets the limit. Leaving Plan is refused while a
withdrawn name's listed task is in the plan. A delta revision of an approved name that
reaches the limit leaves withdrawal of the whole name as the route; no operation falls
back to the approved revision. When a withdrawn record has no attempts left and the
type needs an approved IDR, a dev cycle changes type to iterate when the remaining scope
needs no material decision, or defers the remaining scope and abandons with a
reflection; a simplify cycle defers its selection and abandons with a reflection. No
agent requests an attempt-limit extension. Two limits stay: the dependent-task list and
the Plan check key on task ids the architect declares, so an omitted dependent task
passes the check; and the attempt limit counts per cycle, so deferred work in a new
cycle starts a fresh count, with the deferred entry carrying the history. An unresolved
required safety fact about data policy or publishing is not a council dispute; it goes
to the owner as an outward-facing question.

Pre-council self-check for a decision record (an IDR, a simplify selection IDR, or
an ADR-creation justification; an ADR keeps the `propose-adr` self-check). Run it
before round 1 and again before each reconvene. It is advisory and blocks nothing.
- Cite `path:line` for every factual claim about code, tests or the corpus.
- Name each protected obligation or category the decision removes, narrows or
  relies on, and what still covers it afterwards, including in a reduced run that
  ships the project, such as a staged release suite.
- Consider the failure classes: the recurring threats listed in the `propose-adr`
  self-check.
- Give one obligation per clause of `constraints`, `retained_behavior` and
  `verification`.

Before round 1 of every cycle decision council, run the fresh-agent challenge dispatch
stated in `run-adr-council` ("Before round 1"). Its `propose-adr` self-check applies only
to ADRs; an IDR author uses this skill's pre-council self-check. Apply the `council`
skill's fix-round discipline to each revision between rounds.

An ADR may originate from a direct request, whiteboarding, or inbox processing.
Inside a cycle, council must first justify creating an ADR. Only then draft it,
run the `propose-adr` pre-council self-check, and obtain separate council approval of its contents. Acceptance requires human
approval by default; `.bionic.yml` may set `adr.acceptance: council-only`.
An absent value means `council-and-human`. New-policy acceptance makes the rules
binding without promotion. Do not reinterpret historical provenance. After the
accepted architectural decision, revise the plan and reassess affected IDRs.
A task that depends on a pending cycle ADR names it in its optional `adr_dependencies`
list. Tasks that do not name it proceed and the Plan phase can end; a named ADR that is
not accepted refuses the dependent task's dispatch and its phase exit with
`adr-dependency-awaiting-acceptance`, and a name with no recorded ADR decision refuses
with `adr-dependency-unrecorded`. Acceptance releases both.
Use `cycle-council.py` and `decision-policy.py` help for approval and acceptance
operations, and attach their evidence through the cycle decision command.

## Return paths and stops

A blocking Verify or Review finding returns to Build in every type, unless it
qualifies for the fix step below. Use `return` to
record what improved, what remains unresolved, what will change, and why another pass
is justified. A pass can end early; it does not need to reach Review first.
A new pass keeps delivered Plan and Build tasks that still revalidate and resets the
rest. Revise the plan in Build when a finding needs it; the commands reference covers
reopening and recovery. Mark a replaced task with `task --state superseded
--superseded-by` instead of rewiring its dependents.

### Fix step

In Verify or Review the commander may answer small findings with a fix task instead
of a return. One fix task may answer several blocking findings of the latest review.
No pass is consumed and Plan stays closed. Each finding qualifies when the fix for it
stays in plan scope, changes no approved decision, schema, interface or dependency,
the finding states its cause, and a reviewer can check it in the fix diff. The whole
fix stays small: a few files, about 50 changed lines. One fix per phase per pass; the
commander records why it qualifies.

Add the task with `task-add`, carrying `fix: {finding, eligibility}`; a Review fix may
add `findings`, the blocking finding ids it answers. A dev-lead writes the fix itself,
with no developer unit; the commander's shell stays the cycle writer and read-only git.
The task finishes with a commit, a failed check that now passes, and a rerun of only the
checks whose inputs changed. After a Review finding, a reviewer checks only the fix
diff against the finding. After a Verify finding, the normal Review covers it.

An ineligible finding, a failed fix, or a blocking fix-diff review returns to Build.
Metrics count fix tasks. [commands.md](references/commands.md) gives the fields.

A failed acceptance criterion can also justify the one fix step. Name its zero-based
index and a committed JSON observation with `criterion`, `value`, `met` and `commit`.
The before observation records `met: false`; attach the committed after observation
with `task --fix-observation PATH`. Completion requires `met: true`, a fix commit,
and the same scope, size and review obligations as a finding fix. Prior-pass commits
already delivered by this cycle may be adopted with `--adopt-commit`; the writer
checks ancestry, task trailer and delivery provenance. Adoption does not rewrite the
earlier delivery or admit an unrelated commit.

A failed release step stops the release. After a fix lands by its own route, the
coordinator sets that step's task back to pending with `task`, and the writer reopens
every later task. A release records no return, pass or new cycle. A fix that changes
the artifact resumes no later than the release verify step and needs the owner's new words for beta.
An interruption reruns the step with no commit and no note. A defect in the tagged
bytes ends that version: run record with its reason, abandon the open official cycle,
and ship the fix under a new version in a new beta cycle. A withheld go-ahead or a
tooling outage pauses the official cycle; it never abandons it.

Pause when progress stalls, the limit is exhausted, scope changes materially,
a decision needs owner input, an explicit pause applies, or new evidence
contradicts the premise. Report the blocker, evidence, and recommended next step.
Do not retry solely because passes remain. Additional passes require explicit
human approval recorded through `extend`; approval never disables the progress
rule. A type change preserves identity, history, and pass count and cannot
silently bypass an exhausted limit. Routine authorized work needs no per-step
permission. Publication, external sends, and other outward actions still need
applicable authorization.

## Commits and reports

Keep the record current as work happens, so the dashboard shows it; the operations do
this for dispatch, delivery and loss. A dashboard refresh requested while its reader runs
does not reuse that run's result, because the reader read the record when it started.
The request schedules one more run that starts when the current run ends, so after a
cycle write the next refresh shows the record as it stands after the write.

A commit holds one coherent change on the committer's owned paths; use `git commit
--only` when streams share the index. Developer commit messages end with a
`Cycle-Task: <task-id>` trailer, in one final paragraph with any `Co-Authored-By:` line and no blank line between them. The cycle writer commits
its cycle bookkeeping itself; the queue writer owns active/history commits. A phase-changing `advance`, `finish`,
`owner-exception`, every dispatch and delivery operation (`prepare-dispatch`,
`attach-execution`, `deliver`, `mark-lost`), `execution-check`, `child-link`,
`release-continue` and the low-level `pause` commit `<docs>/cycles/<id>/`, with `git commit --only`; other staged
work stays staged. The result names the commit under `record_commit`. The commit defers,
with a reason and without failing the operation, while a full suite holds
`<git-common-dir>/crux/full-suite.lock`, outside a git repository, during a merge or
rebase, and under an index lock. Run `commit-record` at a recovery checkpoint (a pause,
a planned stop or hand-back, or a tool that refuses a dirty tree) and whenever `inspect`
reports `record.pending`. Nobody asks the main session to commit cycle bookkeeping.
A replay catches up a pending record commit without applying the operation again.
`inspect` reports the full-suite flock separately from its holder metadata; a stale
holder is cleared only after acquiring that flock. An owner-unknown `index.lock`
is reported and never removed by this recovery. `finish` preserves worktrees held
by an active or paused cycle's open attempt, naming its owner and reason.
`cycle.py friction CYC --json REQUEST` (or `--file PATH`) appends one row to the cycle's friction log and
commits it with the record, so a role that writes no file, such as the commander,
records friction itself instead of relaying it in a brief. Reports cite rather than
restate. Each agent reports its own assignment, attempt, outcome, commits and
evidence paths. A lead lists each unit's task id, outcome, commit and result path and
cites the child report. Commander reports its blockers and the decisions it needs.

A repeated write is safe (`changed: false`); a refused update stops the work until
resolved. See [commands.md](references/commands.md) for flags and examples.
`reconcile` is recovery from evidence after a lapse, not the normal way to keep the record current. A request
to "update the cycle" or "reconcile the cycle record" runs `inspect`, then `reconcile`,
and applies only what the evidence establishes.

Commander owns the cycle through completion. Delegation transfers work, not
accountability. An interim notification, waiting child, failed child, or missing
delivery does not justify handing the cycle back; recover within authorized scope and
cycle limits, and pause for an owner decision or explicit pause under the stops above.
An operational blocker returns to the main session instead, as Route through the lead
states. A denied commit is blocked, not running work. Recorded
assignments are not observed agent activity. Instructions cannot override host
termination: when a host forcibly ends a run, leave `inspect` output, execution
handles, observed outcomes, result locations, blockers and next actions through an
available channel, and run `inspect` before a planned stop. The caller resumes or
replaces commander; it does not silently assume the implementation role.

## Queue

The owner captures and orders work once in `<docs_dir>/queue/cycles.yaml`. Commander
executes authorized queued work one cycle after another. Every op is
`cycle.py [--repo-root R] [--compact] queue <op>` and takes flags only; see
[commands.md](references/commands.md) for each op, its flags and its exit codes.
Pass free-text values single-quoted, with an embedded single quote written as `'\''`.

- "Add to the queue" runs `queue add`; "show the queue" runs `queue list`, which
  prints one line per open item, and `queue list --full` prints every item and the
  authorization history.
- Every queue write except `start-next` commits its touched active/history paths, under the same
  deferral conditions as the record commit; `start-next` commits the queue file and
  the new cycle record together. Nobody commits the queue file by hand.
- `--scope` takes one path per value; a comma-separated value is split into paths.
- `--reference PATH` links a supporting document, such as a brief. `queue start-next`
  carries the references into the cycle goal so Plan reads them first. They are not scope.
- "Run the next item", "run the next N items" and "run the queue" run `queue authorize`
  with `--instruction` set to the owner's own message, quoted verbatim, then
  `queue start-next`. An agent report, council verdict, result file or automatic
  inspection never supplies the instruction.
- Authorization starts cycles only. It never authorizes push or another outward
  action, never extends a pass limit and never approves an IDR or ADR. The one
  exception is a release item: authorizing it also authorizes publishing that item's
  version to its target (see Release cycles). Each started cycle keeps its own type,
  pass limit and stops.
- A release queue item starts a beta-list cycle. Name its prep paths and
  `<docs_dir>/log`, the operations-log directory, as scope. An item added with
  `queue add --release-list official` starts an official-list cycle; its instruction, given after the version's beta tag,
  is the owner's go-ahead. Queue no official item before that tag. Add it titled with the
  version at the head of the queue (`--position 1`), run `queue authorize next`, and
  confirm the scope names that item alone. An official cycle not started from the queue
  is created directly with `create --type release --list official`.
- Queue authorization approves no IDR, but authorizing a simplify queue item lets the
  configured council select proposals within its scope. The same holds for a
  queue-started cycle change-typed into simplify. Selection outside that scope pauses
  for an owner decision.

`queue start-next` returns one outcome. `started`, or `adopted` or `in-progress` with an
active cycle: drive that cycle to completion. `in-progress` or `adopted` with a paused
cycle: stop at its pause and report. `adopted` with a completed, abandoned or shortcut cycle: run
`queue start-next` again. After each queued cycle completes, run it again.

A stop ends the run with a report naming the reason, the item and the next step. The
reasons are `queue-empty`, `not-authorized`, `previous-abandoned` (checked before
`authorization-exhausted`), `authorization-exhausted`, `outside-authorization`, `held`,
`blocked`, `dependency-abandoned`, `type-unsupported`, `cycle-missing` and
`environment-prerequisite`. A dependency on an item whose cycle closed as a shortcut
stops `blocked` with text that names the shortcut closure; the owner edits the dependent
item's `depends_on` or removes the item.

`cycle.py create` and `queue start-next` check the environment before any write: a
resolvable git author and committer identity, each Python minor the repository's
`pyproject.toml` declares under `[tool.crux] python-versions`, and `node` when the scope
reaches a TypeScript test root. `create` refuses with code `environment-prerequisite` and
lists every missing prerequisite with its fix. `queue start-next` stops with the reason
`environment-prerequisite` and leaves the item pending. Either is an operational blocker:
the caller fixes the environment and runs the command again.

On resume, run `queue list` and continue within the remaining allowance. After
completing any cycle, and on resume without an authorization, inspect and report the
queue; inspection never authorizes. `queue revoke --reason TEXT` stops further starts
only: run no `queue start-next` until a new authorization, and pause a running cycle
through its own pause. Format 1 retains its historical lifetime cap; format 2 caps active entries.
`start-next` considers only queue-started cycles.

Queue format 2 keeps active/unresolved items, the monotonic counter and all current
and ended authorizations in `queue/cycles.yaml`. Each terminal started item moves once
to immutable `queue/history/items/Q-NNNN.json`, retaining original fields, order,
provenance, digest and terminal cycle binding. Cycle and evidence paths never move.
Readers support formats 1 and 2. Migration is explicit: inspect `queue archive --dry-run`,
then use `queue archive --migrate`. Reads and ordinary format-1 writes never migrate.
Format-2 mutations and terminal-cycle completion sweep eligible terminal items.
Pending, held, active, paused, missing or invalid records remain active.

The queue writer validates selected items, writes history before removing active copies,
then commits exactly touched active/history paths together. Identical copies coalesce;
conflicts refuse. Recovery completes an interrupted transaction without losing an item.
The terminal sweep runs after releasing the cycle lock; joint start uses queue-then-cycle
lock order. Ordinary cycle commits cannot capture pending queue changes.

Say “show queue history” for `queue list --full`, “show the full queue” for the full
list, or name an item for `queue show Q-NNNN`. These use the same resolver as dependencies
and release authorization. Missing/corrupt required history and revoked quotes refuse.
History items cannot be edited, requeued or reused. The 500-item cap applies to active
entries in format 2; allocation also checks history collisions. Existing removal of an
unstarted item creates no history tombstone. Old plugins that reject format 2 and old
release readers that cannot resolve archived items are unsupported after migration.

## Progress and historical records

The record drives visualization: current phase/pass/limit, tasks, return reasons,
approval waits, and outcome. Use `visualize-cycle-progress.py --help` for its
reader interface. Do not substitute a percentage for the evolving plan.

Old promptbooks, snapshots, templates, and their validators are historical
compatibility surfaces. New work uses this skill. Existing in-progress legacy
runs may finish under their original contract; never convert them in place or
start a repeated legacy run. A materially changed legacy undertaking starts a
new cycle referencing its predecessor. Generic new plans also use cycles with
the type matching their work, rather than a newly authored promptbook.
