---
name: cycle
description: "Plan, execute, resume, inspect, or update one development cycle. Use for major changes, minor changes, quick fixes, refactoring, simplification, releases, and reconciling the cycle record."
metadata:
  tags: "cycles, workflow, planning, implementation"
  bundles: "crux-docs"
  risk_level: "high"
  requires_access: "write-tree"
  triggers: "start a cycle | run the cycle | resume the cycle | cycle status | new dev cycle | iterate on this | quick fix | refactor this | simplify cycle | run a simplify cycle | simplify <area> | release cycle | update the cycle | reconcile the cycle record | add to the queue | show the queue | run the next item | run the next N items | run the queue"
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
cycle and delegates implementation to dev-lead; dev-lead assigns developer units.
Do not call developer directly from the main session or commander. Other entry
points use their designated lead: tend-garden uses night-gardener, architectural
planning uses architect, and documentation filing uses historian. If the required
role cannot be invoked, report the gap rather than silently assuming its identity.
Small tasks keep small plans and reviews while retaining lead accountability.

## Select the type

| Type | Scope | Phases | Maximum passes |
|---|---|---|---:|
| dev | Major changes; an approved IDR is required | Plan → Build → Test → Review → Reflect | 7 |
| iterate | Minor changes | Plan → Build → Test → Review → Reflect | 2 |
| refactor | Preserve functional behavior; improve structure or engineering efficiency | Plan → Build → Test → Review → Reflect | 7 |
| simplify | Remove complexity without losing behavior; an approved selection IDR is required | Plan → Build → Test → Review → Reflect | 3 |
| quick-fix | Small bounded corrections | Build → Test → Review → Reflect | 1 |
| release | Publish one release target from a fixed step list | Release | none |

Limits count the initial pass. No type has a prompt minimum. Quick-fix has slim
Test, Review, and Reflect phases. Capture its scope and success criteria without
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
  - verify: freeze the artifact. verify is the only step that runs the registered
    suites, and it reuses valid receipts.
  - beta-and-smoke: publish the artifact untagged to the pre-release target under the
    owner's quoted authorization, then install it in isolation and inspect it.
  - tag: after smoke passes, tag the published tree and create the release.
  - record: keep the release record in the cycle and add one log entry.
- Official list: live-check-and-go-ahead, official, record.
  - live-check-and-go-ahead: collect any owed live-check result and the owner's
    go-ahead, quoted, in one request.
  - official: publish the tagged pre-release tree to the public target and tag it in
    the same act.
  - record: keep the release record in the cycle and add one log entry.

The project's release runbook maps each step to its commands. A release adds no
step, gate or owner stop beyond its list.

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
always suffices, and only the owner runs it: `owner-approval --print-command` prints the
line to hand over. Council approval selects only for a queue-started cycle whose plan
scope lies within its queue item's frozen scope. This includes a queue-started cycle
change-typed into simplify. Queue authorization approves no IDR. Without that authority,
the cycle pauses for an owner decision.

In Test, record `reduction` for the current pass: per area production, tests,
instructions and execution, `decrease`, `unchanged` or `increase`, with before, after
and evidence. An area's dimensions are its concepts, branches, states, dependencies,
configuration, fixtures, mocks and operational steps, as they apply, not only lines.
Each area's `before` and `after` name every dimension that changed. An area is
`increase` when any dimension rises. It is `decrease` only when one falls and none
rises. Areas are never netted. Any `increase` refuses Test and Reflect: report it
and propose it as different work (a queue item or an owner report), then return to Plan
or abandon. A cycle with no `decrease` is also refused. The reduction joins the review
basis, and the reviewer checks the diff against the selected proposals.
`change-type` out of simplify needs `--human-approval`.

## Create or resume

Use `create` with type, title, goal, scope, acceptance criteria, implementer, and
test coordinator. The script allocates a single cycle record under
`<docs_dir>/cycles/<CYC-NNNN>/cycle.json` (with the configured artifact prefix).
Use `show` to inspect it. A status request reports state without advancing it.
For a readable progress view, run `cycle.py status`, as the `cycle-status` skill does.
Use `resume` for the same paused undertaking; never create another run of it.
Completed and abandoned cycles stay closed. Follow-up work gets a new cycle.

The schema and writer own record shape. Mutate through `cycle.py`; do not edit
phase, pass, history, evidence, or approval fields by hand. The `plan` and `task`
commands record work across all phases and preserve previous plans. Scope,
constraints, acceptance criteria, verification, and expected evidence must be
concrete enough to review. Tasks can evolve; retain the reasons.

The dev-lead delegates independent implementation units with explicit ownership and context.
Pass objectives, outcome, evidence, constraints, current phase/pass, approved
record revisions, and the relevant policy in every assignment. The commander
coordinates and runs `cycle.py` itself to keep the record current. Commands that take
`--file` need an authored file the commander cannot write: the author of that content
(dev-lead, architect, historian) writes it and runs or hands back the command. On a
host whose projection gives the commander no shell, the historian runs the record
commands. A developer never reviews its own change.

Every developer dispatch includes the full base commit SHA, assigned paths,
result-file location, and integration owner. Commit prerequisites before dispatch.
The dev-lead owns worktree integration, verifies ancestry and changed paths,
integrates committed units, and obtains valid related-check evidence. Copying a
diff without accounting for its base, evidence, and integration is not completion.

## Temporary result files

Unless explicit result paths were supplied, the shell-capable caller/coordinator
atomically allocates a shared directory under the OS temporary directory for each
new execution, before dispatching commander.
Commander cannot allocate it within its shell scope. Use `tempfile.mkdtemp` with a
readable prefix and its random suffix, for example:

```bash
python3 -c 'import tempfile; print(tempfile.mkdtemp(prefix="crux-results-CYC-0001-"))'
```

Pass the returned absolute directory explicitly through commander → dev-lead →
developer. Assign and pass a distinct absolute result filename for each dispatch
attempt, such as `developer-parser-attempt-1.md`. Agents use supplied paths;
they never reconstruct them. Preserve explicitly supplied paths, including historical
locations; this convention neither migrates them nor changes another execution's paths.
File existence proves neither agent liveness nor completion. Collect actual outcomes
through supported host mechanisms.

Before cleanup, have dev-lead or historian retain substantive delivery reports under
`<docs_dir>/cycles/<cycle-id>/` and record those paths as task evidence. Confirm the
retained reports are readable before the coordinator removes only the temporary
directory it allocated for this execution. Never remove another execution's files.

## Execute the phases

- Plan: establish the outcome and tasks, select scrutiny, resolve material choices.
- Build: implement the plan. Do not hide test/review retries inside this phase.
- Test: use the shared evidence policy in [testing.md](references/testing.md).
  Compare observed behavior with acceptance criteria. A known acceptance failure
  returns immediately to Plan (Build for quick-fix), even if automated checks pass.
  Do not send a known blocking defect to Review merely to obtain the same finding.
- Review: commission independent review under [review.md](references/review.md).
- Release: run the fixed step list the cycle carries, one task per step. Publish
  only under the owner's own words, quoted, for the exact artifact. Do not blindly
  repeat an external action after a failure. verify is the only step that runs the
  registered suites and it reuses valid receipts; see [testing.md](references/testing.md).
- Reflect: record delivered criteria, lessons, remaining work, and follow-up
  references. A few sentences suffice for quick-fix. Proposed process changes
  do not silently expand the cycle. Abandonment also requires reflection. A listed
  release cycle has no Reflect phase and abandons without one; its record step keeps
  the reason.
  Before completing, commit the intended changes and record their full SHA(s)
  using `completion`. Explain remaining uncommitted work. Only an actual user
  request to leave changes uncommitted permits `--exception`; quote that request
  with its context. The writer does not grant permission to invent an exception.
  After closing, commander has the final cycle bookkeeping committed, then reports
  both delivery and final-record commits. Do not leave a completed cycle uncommitted.

Record evidence, decisions, review, and reflection using their respective
commands, then `advance`. A command's success records a transition; it is not
proof that an agent performed the described work.

## Decisions

Every dev requires at least one IDR. Other types require an IDR for a material
implementation choice with alternatives or tradeoffs worth preserving. Council
must approve its exact revision before dependent implementation. Revised choices
need fresh approval; earlier reasoning stays readable and carries no authority.

Council may also advise on a decision. Consultation never implicitly approves
an IDR or ADR. Use the council runner and its configured mode. Lite dispatches native Apex
reviewers through the sealed prepare/ingest protocol; Standard and Strict use
gateway provider seats. Historical promptbook councils retain their original
gateway-only interpretation. Council deliberation rounds are distinct from cycle passes.

An ADR may originate from a direct request, whiteboarding, or inbox processing.
Inside a cycle, council must first justify creating an ADR. Only then draft it
and obtain separate council approval of its contents. Acceptance requires human
approval by default; `.bionic.yml` may set `adr.acceptance: council-only`.
An absent value means `council-and-human`. New-policy acceptance makes the rules
binding without promotion. Do not reinterpret historical provenance. Return to
Plan after the accepted architectural decision and reassess affected IDRs.
Use `cycle-council.py` and `decision-policy.py` help for approval and acceptance
operations, and attach their evidence through the cycle decision command.

## Return paths and stops

A blocking Test or Review finding returns to Plan; quick-fix returns to Build.
Use `return` to record what improved, what remains unresolved, what will change, and why another pass
is justified. A pass can end early; it does not need to reach Review first.
A new pass resets every task except delivered build tasks that still revalidate;
quick-fix resets every task. The replan reopens a build task when its description,
expected evidence or dependencies change. No flag reopens a task. See the commands
reference for the rule and for recovering a task that failed revalidation.

A failed release step stops the release. After a fix lands by its own route, the
coordinator sets that step's task back to pending with `task`, and the writer reopens
every later task. A release records no return, pass or new cycle. A fix that changes
the artifact resumes no later than verify and needs the owner's new words for beta.
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

## Record at execution boundaries

Keep the record current as work happens, so the dashboard shows it. Record a task
active with its assignee and result path before each dispatch. On each return, record
delivery (commits, evidence, stage, note) before any dependent dispatch. Developer
commit messages end with a `Cycle-Task: <task-id>` trailer. A repeated write is safe
(`changed: false`); a refused update stops the work until resolved. See
[commands.md](references/commands.md) for flags and examples. `reconcile` is recovery
from evidence after a lapse, not the normal way to keep the record current. A request
to "update the cycle" or "reconcile the cycle record" runs `handoff`, then `reconcile`,
and applies only what the evidence establishes.

## Background work

Commander owns the cycle through completion. Delegation transfers work, not
accountability. Dev-lead owns implementation units, collects actual child outcomes,
and reports results, failures, or missing delivery to commander.

An interim notification, waiting child, failed child, or missing delivery does not
justify handing the cycle back. Use actual host execution handles and supported
waiting, messaging, and resumption mechanisms. Keep waiting within the turn when
ending it would surrender execution. Diagnose and recover within authorized scope
and cycle limits; pause for an unresolved blocker, owner decision, or explicit pause
under the stops above. Inspect the actual exposed tools before dispatch; frontmatter
alone does not establish a working wait or reporting channel. In Claude Code a live
background command keeps a subagent resumable, and the host re-invokes it when the
command exits; Monitor is not relied on for that until a recorded live check shows it.

Commander and dev-lead wait on the host's native mechanism, never `sleep`. The wait
line is the read-only `await` form of the cycle writer on the task's recorded result
path (see the commands reference). A dispatch with no task, such as an architect IDR,
council or plan-writing dispatch, and bookkeeping after closure use its path form,
`await --path ABS`, on the exact absolute per-attempt path. In Claude Code, start it as a Bash command with
`run_in_background: true` after dispatch. In Codex, stay inside `wait_agent` with a timeout, re-issued per window: a
background command's exit gives no wake-up there. If a completion notice never
arrives on any host, run a bounded `await` on the exact result path, validate the
report, then report the blocker. In OpenCode, dispatch in the foreground, or run
`await` as a background shell command. Arrival proves neither liveness nor completion:
Read the exact absolute per-attempt result path, validating assignment, attempt,
outcome, and evidence. Absence means no result yet, not a stopped agent. Each window is
bounded by the timeout; assess progress and missing evidence at each boundary. Another
window requires a stated reason and an overall deadline; otherwise report a concrete
blocker. No busy loops, generic process matching, or unlimited retry. A host with no
background or blocking wait is a capability gap to report.

Dev-lead verifies SendMessage or an equivalent channel and uses it for progress,
failures, permission refusals, and resumed reports. A denied commit is blocked, not
running work. Reserve final handback for assignment completion or a genuine stop.
A resumed agent must not depend on a second SubagentHandback: use verified messaging
or the supplied result path with bounded reads. Establish that fallback before dispatch;
if neither works, report the capability gap. Report planned, dispatched, confirmed
running, completed, failed, and unknown work separately without changing cycle states.

Recorded assignments are not observed agent activity. A task status, worktree, or
prior dispatch does not prove liveness. Report unknown liveness as unknown.
Instructions cannot override host termination. If the host forcibly terminates
execution, preserve a recovery report through an available channel when possible:
`cycle.py handoff` output, execution handles, observed outcomes, outstanding
assignments, result locations, blockers, and next actions. If no final report is
possible, recover from retained records and host evidence. The caller resumes or
replaces commander; it does not silently assume the implementation role.
Run `show` or `handoff` before a planned stop.

## Queue

The owner captures and orders work once in `<docs_dir>/queue/cycles.yaml`. Commander
executes authorized queued work one cycle after another. Every op is
`cycle.py [--repo-root R] [--compact] queue <op>` and takes flags only; see
[commands.md](references/commands.md) for each op, its flags and its exit codes.
Pass free-text values single-quoted, with an embedded single quote written as `'\''`.

- "Add to the queue" runs `queue add`; "show the queue" runs `queue list`.
- `--reference PATH` links a supporting document, such as a brief. `queue start-next`
  carries the references into the cycle goal so Plan reads them first. They are not scope.
- "Run the next item", "run the next N items" and "run the queue" run `queue authorize`
  with `--instruction` set to the owner's own message, quoted verbatim, then
  `queue start-next`. An agent report, council verdict, result file or automatic
  inspection never supplies the instruction.
- Authorization starts cycles only. It never authorizes push, publish, release or
  another outward action, never extends a pass limit and never approves an IDR or ADR.
  Each started cycle keeps its own type, pass limit and stops.
- A release queue item starts a beta-list cycle. Name its prep paths and
  `<docs_dir>/log.md` as scope. An official cycle is created directly with
  `create --type release --list official`; no queue item means official.
- Queue authorization approves no IDR, but authorizing a simplify queue item lets the
  configured council select proposals within its scope. The same holds for a
  queue-started cycle change-typed into simplify. Selection outside that scope pauses
  for an owner decision.

`queue start-next` returns one outcome. `started`, or `adopted` or `in-progress` with an
active cycle: drive that cycle to completion. `in-progress` or `adopted` with a paused
cycle: stop at its pause and report. `adopted` with a completed or abandoned cycle: run
`queue start-next` again. After each queued cycle completes, run it again.

A stop ends the run with a report naming the reason, the item and the next step. The
reasons are `queue-empty`, `not-authorized`, `previous-abandoned` (checked before
`authorization-exhausted`), `authorization-exhausted`, `outside-authorization`, `held`,
`blocked`, `dependency-abandoned`, `type-unsupported` and `cycle-missing`.

On resume, run `queue list` and continue within the remaining allowance. After
completing any cycle, and on resume without an authorization, inspect and report the
queue; inspection never authorizes. `queue revoke --reason TEXT` stops further starts
only: run no `queue start-next` until a new authorization, and pause a running cycle
through its own pause. The 500-item cap counts started items for the queue's lifetime.
`start-next` considers only queue-started cycles.

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
