---
name: cycle
description: "Plan, run, resume, inspect, finish or reopen one development cycle, or start a release or the next queued item. One lead, native delegation, independent review."
metadata:
  tags: "cycles, workflow, planning, implementation"
  bundles: "crux-docs"
  risk_level: "high"
  requires_access: "write-tree"
  triggers: "start a cycle | run the cycle | resume the cycle | cycle status | inspect the cycle | finish the cycle | reopen the cycle | release cycle | add to the queue | show the queue | run the next item | run the next N items | run the queue | show queue history | show the full queue | archive completed queue items | migrate the queue"
  routing_note: "One undertaking with one lead, native delegation, selected checks and independent review; completion is separate from PR, CI, merge and publication."
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
Run `uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --help` for the commands and append a
subcommand and `--help` for its options. [lightweight.md](references/lightweight.md)
states the record and the writer commands, [commands.md](references/commands.md) the
queue, council and release commands, [testing.md](references/testing.md) the check
selection and [review.md](references/review.md) the review.

## One lead

One lead runs each cycle, records its plan and meaningful progress through the writer,
and delegates through the host's native tools: `Agent` in Claude Code, `spawn_agent` in
Codex, `subagent` in OpenCode and `task` in OMP.[^lead] The lead is the main session, or
the commander when the main session hands the cycle over. Small work needs one task and
no other role.

- The lead writes the record: `plan`, `task`, `check`, `batch`, `delivery`, `finish`,
  `pause`, `resume`, `reopen` and `abandon`. Each takes `--actor LEAD --expect-revision N`.
  The writer refuses a stale revision and a late result from a superseded task run.[^stale]
- Workers (dev-lead, developer, architect, historian, test coordinator) return native
  results to the lead and never write the record.
- A dev-lead may implement directly or fan independent units out to developers in
  isolated worktrees on a host that isolates each call, as Claude Code does. Keep one
  editor per checkout. On Codex, OpenCode and OMP, which lack per-call isolation, units
  run serially. The dev-lead integrates by ordinary git, fast-forward or merge, on the
  lead's checkout.
- The test coordinator, one dev-lead, runs any full suite the selected checks include.
  Developers and reviewers run focused checks only.
- The writer does not commit. The lead commits the cycle record with ordinary work
  checkpoints, at handoff and at completion. No dispatch bundle, execution proof,
  delivery token, ancestry check or per-operation record commit applies.[^ceremony]
- If a required role cannot be invoked, report the gap; never assume its identity.
  An operational blocker, such as an unresolvable git identity, a missing interpreter or
  an `index.lock` of unknown owner, returns to the main session with the quoted error.
  Never remove an unknown `index.lock`.

Commander owns a cycle it holds through completion. Delegation transfers work, not
accountability; an interim notification or a failed child does not justify handing the
cycle back. Report planned, dispatched, running, completed, failed and unknown work
separately, and report unknown liveness as unknown. A host handle proves no liveness.

## Create, plan, resume

`create --title T --lead L` with `--plan FILE`, or with `--goal`, `--scope` and
`--acceptance`, allocates the record at `<docs_dir>/cycles/<CYC-NNNN>/cycle.json`. The
plan holds the goal, scope, acceptance criteria, verification, a council decision and the
tasks with owners and dependencies.
Use `show` to inspect it. A status request reports state without advancing it.
For a readable progress view run `cycle.py status`, as the `cycle-status` skill does.

The cycle states are `planning`, `working`, `reviewing`, `reviewed`, `completed`,
`paused` and `abandoned`. A cycle has no fixed step sequence and no retry count; ceremony
scales with the change.[^nophase] A task is `pending`, `working`, `blocked` or `done`. The owner's
request can authorize implementation within the plan's scope and acceptance. A change
to acceptance takes effect only with the owner's recorded words, through
`plan --owner-approval`. A change to scope does too, except that the lead may add each
path that a blocking finding, recorded by the cycle's requested independent reviewer,
names as the place to fix an unmet acceptance criterion of the current plan:
`plan --finding TASK --criterion N` records the finding and the criterion.[^owner]

`resume ID --reason TEXT --reconcile TEXT` continues a paused cycle after the lead
inspects the record, git status, diff and actual host state. It never creates another
run of the same undertaking. After an interrupted write, `recover ID` reconciles the
checkout claims. A completed or abandoned cycle takes no `resume`: reopen it (below) or
create a follow-up with `create --follows CYC-NNNN`.[^restart]

## Council for consequential plan choices

Convene council when the owner asks, a consequential trade-off needs resolving,
uncertainty blocks a defensible plan or a durable constraint changes.[^council] Record
the decision and a one-sentence reason in the plan. Then:

1. `council-subject ID` freezes the exact plan revision and returns its path and identity.
2. Run `cycle-council.py --purpose consultation --subject SUBJECT --identity IDENTITY
   --question QUESTION_FILE` and follow its configured mode and continuation commands.
3. `council ID --record PATH --response TEXT` records the approved result and the
   response to its findings.

Tasks that depend on the choice wait; unrelated tasks proceed. A council dispute stays
with council and never goes to the owner. An uncertain council request is reconciled
before any retry, never repeated because a session resumed.[^external] The purposes
`idr` and `adr-creation` are retired.

## Checks

Run focused checks while building. Before completion the lead selects final checks by
scope and risk, including the drift gates the change touches and, where the project
labels tests, the tier check whenever a test or tier manifest changes.[^checks] Record
each observation with `check` (or `batch`): command, result, tested revision, summary and
reason. A recorded observation is an attestation, not execution. Reuse a passing
observation only explicitly within the same cycle and never after a later failure of the
same check.[^reuse] No stage requires a full suite. [testing.md](references/testing.md)
covers the selection.

## Review

When the work is committed and the selected checks are recorded, the lead runs
`review-start ID --reviewer NAME`. The named independent reviewer reads the cycle,
assesses acceptance, diff, integration and testing under [review.md](references/review.md),
and submits its own verdict with `review ID --actor NAME`. The lead never submits it.[^verdict]
When the host denies the reviewer's write, quote the denial and report it.

A blocking finding, or an acceptance failure observed at any time, becomes a task in the
same cycle. Fix it, record the new checks and request review of the changed work.[^findings]
A review counts for the plan revision and code range it names; later implementation work
or a plan revision makes it obsolete.

## Finish, delivery and reopening

`finish ID [--summary TEXT]` completes the cycle when its agreed tasks are done, its
selected checks pass and an approving review of the current plan revision still covers
the final change with every acceptance criterion met.[^complete] The completed record
holds a summary, from the review JSON or from `--summary`, and no reflection step
follows.[^summary]

PR, CI, merge, commit and publication are delivery facts. Record them with
`delivery ID --file FILE` before or after completion. None completes or reopens a cycle,
and none is required for `finish`.[^delivery] When CI fails or the delivered work shows a
defect, record the fact and offer the owner two routes: reopen the cycle with
`reopen ID --reason TEXT --owner-instruction TEXT --file TASKS`, or create a linked cycle
with `create --follows CYC-NNNN`. Reopen only on the owner's recorded instruction.[^reopen]
An abandoned cycle, a historical shortcut cycle and a completed release record never
restart.

## Stops

Pause with `pause ID --reason TEXT` when progress stalls, including repeated failure
without new evidence, scope changes materially, an owner decision is needed or evidence
contradicts the premise.[^stops] Report the blocker, the evidence and the next step.
Elapsed time and an expired wait window pause nothing. Routine authorized work needs no
per-step permission. Publication, external sends and other outward actions still need
their own authorization. `abandon ID --reason TEXT` records an abandonment with its reason.

## Decisions

Raise an ADR only for a constraint future work must preserve. A cycle drafts one in any
active state with `decision-policy.py propose --origin cycle --cycle CYC-NNNN`. No
council approves its creation and the owner need not request it.[^cycle-adr] Council
approves the exact draft, and acceptance follows the configured policy: human acceptance
by default, `adr.acceptance: council-only` in `.bionic.yml` otherwise, through
`decision-policy.py accept`. A task that
depends on the ADR names it in `adr_dependencies`; the writer refuses `working` or `done`
for that task until the ADR is Accepted. Do not reinterpret historical provenance.
Record an owner's answer only as the owner's actual words, never invented. Present one
concrete proposal per answer; never ask the owner to pick among alternatives inside one
presentation.

## Release cycles

`create --release-list beta|official --version X.Y.Z` starts a release record of kind
`release` with fixed step tasks, in order. `tools/release.py` advances and completes it,
and its ledger stays the release authority. The ordinary `task`, `plan`, `review`, `finish`
and `reopen` writes refuse a release record. The runbook (`DEPLOY.md` in the Crux
repository) maps each step to its commands.

- Beta: prep, prepare, verify, beta-and-smoke, tag, record. `release.py verify` is the
  only step that runs the registered suites and it reuses valid receipts. `release.py beta`
  publishes untagged to the pre-release target and smoke precedes the tag.
- Official: live-check-and-go-ahead, official, record. The owner's queued go-ahead, given
  after the beta tag, attests the tagged beta was hand-tested. `release.py official`
  records it from the queue quote and publishes the tagged tree.
- `release.py record --cycle CYC-NNNN` copies the ledger into the cycle. A target that
  did not publish takes `--reason`.

Agents run each step, including the bare `release.py beta` and `release.py official`
commands. Authorizing a release queue item authorizes publishing that item's version to
its target and no push or other outward action. Run the publish command bare, with no
environment prefix, compound command or redirection; the owner's quote comes from the
queue chain. When the host denies it, quote the denial and hand the owner that bare
command. A changed artifact, or a release not started from the queue, needs the owner's
new words through `--authorization`; never supply them yourself. A failed step stops the
release; after the fix, rerun that step through `release.py`. A fix that changes the
artifact restarts at verify. Never repeat an external action whose
outcome is uncertain before reconciling the ledger.[^external] `tools/crux-release.json`
supplies literal prep scope, targets and argv; it grants no authority.

## Queue

The owner captures and orders work once in `<docs_dir>/queue/cycles.yaml`. Every command
is `cycle.py [--repo-root R] [--compact] queue <op>` and takes flags only; see
[commands.md](references/commands.md). Pass free text single-quoted, with an embedded
single quote written as `'\''`.

- "Add to the queue" runs `queue add`; "show the queue" runs `queue list`, and
  `queue list --full` prints every item and the authorization history. "Show queue
  history" and "show the full queue" use the same view; `queue show Q-NNNN` names one item.
- "Run the next item", "run the next N items" and "run the queue" run `queue authorize`
  with `--instruction` set to the owner's own message, verbatim, then `queue start-next`.
  An agent report, council verdict or automatic inspection never supplies the instruction.
- `queue start-next` starts every non-release item as a cycle record. The item's `--type`
  label is recorded only, and no classifier sizes the item. Authorization starts cycles
  only: it authorizes no push, approves no ADR and extends no limit, except that a release
  item also authorizes its own publication.
- `queue start-next` returns one outcome. `started`, or `adopted` or `in-progress` with an
  active cycle: drive that cycle to completion. With a paused cycle: stop at the pause and
  report. `adopted` with a completed or abandoned cycle: run it again.
- A stop ends the run with a report naming the reason, the item and the next step. The
  reasons are `queue-empty`, `not-authorized`, `previous-abandoned`,
  `authorization-exhausted`, `outside-authorization`, `held`, `blocked`,
  `dependency-abandoned`, `type-unsupported` and `cycle-missing`.
- `queue revoke --reason TEXT` stops further starts only; pause a running cycle through
  its own `pause`. On resume, run `queue list` and continue within the remaining allowance.
- `queue archive --dry-run` previews, and `queue archive --migrate` explicitly migrates a
  format 1 queue to format 2. Terminal items move once to immutable history; cycle and
  evidence paths never move. A queue writer commits the queue file, which no one commits
  by hand. The lead commits the cycle record.
- A cycle created outside the queue that did a queued item's work is associated with
  `queue reconcile Q-NNNN --pilot CYC-NNNN`; [lightweight.md](references/lightweight.md)
  states the evidence it needs.

## Progress and historical records

`cycle.py status` shows each cycle's state, completed and total tasks, named blockers,
whether its review still covers the final change, its completion and its delivery
facts.[^progress] Do not substitute a percentage. Legacy cycle records (schema versions 1
to 3, typed release cycles) and historical promptbooks are read-only through the history
reader; `status` shows them, and nothing resumes, converts or rewrites them.[^history]
Every former typed subcommand exits 1 with the code `command-retired` and names its
replacement. A materially changed historical undertaking starts a new cycle that names
its predecessor.

[^ceremony]: rule:no-execution-ceremony
[^checks]: rule:checks-follow-scope-and-risk
[^complete]: rule:completion-needs-work-checks-and-review
[^council]: rule:council-reviews-consequential-plan-choices
[^cycle-adr]: rule:cycle-adrs-need-no-creation-council
[^delivery]: rule:delivery-facts-never-complete-a-cycle
[^external]: rule:uncertain-external-effects-are-reconciled-first
[^findings]: rule:findings-become-cycle-tasks
[^history]: rule:historical-cycles-are-read-only
[^lead]: rule:one-lead-maintains-each-cycle
[^nophase]: rule:development-cycles-have-no-phases-or-passes
[^owner]: rule:acceptance-changes-only-with-the-owner, rule:scope-changes-with-the-owner-or-a-review-finding
[^progress]: rule:progress-view-shows-cycle-record-state
[^reopen]: rule:completed-cycle-reopens-only-on-owner-instruction
[^restart]: rule:abandoned-cycles-never-restart
[^reuse]: rule:observations-are-reused-only-within-their-cycle
[^stale]: rule:stale-writes-and-late-results-are-refused
[^stops]: rule:named-stops-pause-any-cycle
[^summary]: rule:closure-records-a-summary
[^verdict]: rule:reviewer-records-its-own-verdict
