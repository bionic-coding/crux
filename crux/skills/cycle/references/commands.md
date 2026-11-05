# Cycle command interface

Run scripts with `uv run` and the resolved plugin root. `--repo-root` comes before
the cycle subcommand. The `cycle.py` examples use the literal form the commander
types: replace `/abs/plugin-root` with the absolute plugin root. Values below are
examples to replace with the actual task. The cycle writer and schema validate
inputs; never hand-edit a record to bypass them.

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact create \
  --type iterate --title 'Correct parser handling' --goal 'Accept valid inputs' \
  --scope 'src/parser.py' --scope 'tests/test_parser.py' \
  --acceptance 'Valid empty input is accepted' \
  --implementer developer-1 --coordinator tester-1
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact show CYC-0001
```

Use the returned ID, including any configured prefix. `create` makes one record;
`show` and `validate` inspect it without advancing. By default both print a bounded
summary: identity, phase, pass and limit, blocker, one line per task with 12-character
commits, required checks, evidence count, latest review verdict, and the last five
history actions. `--full` prints the whole record. `--compact` prints the one-line
status.

Every command that takes a cycle accepts it positionally, as above, or as `--cycle
CYC`; naming both with different values is refused. `task` and `assignment` accept an
evidence or result path relative to the docs root or to the repository root, and
refuse a relative path that names a different file under each root; give an absolute
path to choose one.

`status [CYC-ID] [--json] [--watch SECONDS]` prints the progress view that
`visualize-cycle-progress.py` prints, and writes nothing. With no ID it shows active
cycles first, then the others by cycle number, highest first, at most 60, followed by
the queue. `--json` prints the visualizer's JSON document. `--watch` clears the screen
and redraws every SECONDS until Ctrl-C, for a second terminal beside a session. Exit 0
printed, 1 invalid or unknown cycle, 2 environment.

## Typed operations

`op` is the normal path for dispatch, delivery, loss, advancement and completion. Code
runs the procedure; the agent supplies judgment. Run `inspect`, then the action it
returns.

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . op CYC-0001 --json '{"op":"inspect"}'
uv run /abs/plugin-root/scripts/cycle.py --repo-root . op CYC-0001 --json -    # request on standard input
uv run /abs/plugin-root/scripts/cycle.py --repo-root . op CYC-0001 --file request.json
```

`--json REQUEST` takes one JSON string. The commander passes it single-quoted and
inline: inside a JSON string an apostrophe is `\u0027` and a newline is `\n`. `--json -`
and `--file PATH` serve roles whose shell permits them. Every `--json` option also accepts
`'@PATH'`: the request is read from PATH, a regular file that resolves inside the
repository root (a relative PATH is read from that root). A path that escapes the root,
through `..` or a symlink, or names no file is refused. Write a long request, such as an
assignment with quotes and newlines, to a file and pass `--json '@PATH'` instead of
escaping it. Every command that takes `--file`
also accepts `--json` with the same content, so a role that cannot write a file submits
content another agent authored and returned, such as a review report, inline. `crux/schemas/cycle-operation.schema.json`
holds the request shapes. Exit 0 means success or a replay, 1 a refusal, 2 an
environment error. A refusal writes nothing.

Request fields. Mutating requests carry `op_id` (8 to 64 characters from
`[A-Za-z0-9._-]`), except `commit-record`, which accepts it optionally and does not
journal it. `inspect` takes none. Invalid JSON names the `--file PATH` recovery;
that path must be a regular file.

| `op` | Fields |
|---|---|
| `inspect` | `host` and `summary` (both optional) |
| `dispatch-invocation` | `assignment`, `attempt`; read-only, no `op_id` |
| `execution-check` | `assignment`, `attempt`; optional `checkout`, `edited_paths`; mutating, requires `op_id` |
| `prepare-dispatch` | `task_id`, `host`; optional `role`, `assignment_text`, `assignment`, `result_path`, `mode`, `integration_owner`, `capabilities`, `release_continuation: {version}` |
| `advice-refresh` | Optional `kinds`, `task_id`, `role`, `assignment`, `evidence_id`; requires `op_id` |
| `child-link` | `assignment`, `attempt`, `child_task`; requires `op_id` |
| `release-continue` | `assignment`, `attempt`, `delivery_token`, `handle`, `host`, `target` (`beta` or `official`), `outcome`, `step_result: {step, exit_code, ledger_sha256?}`; optional `commits`, `evidence`, `stop`; requires `op_id` |
| `attach-execution` | `assignment`, `attempt`, `handle` |
| `deliver` | `assignment`, `attempt`, `outcome` (`done`, `blocked` or `failed`); optional `commits`, `evidence`, `stage`, `note`, `stop: {kind, note}` |
| `mark-lost` | `assignment`, `attempt`, `evidence` (`{kind, detail}`), `note` |
| `advance` | `expect_revision` |
| `finish` | `expect_revision`; `lessons` and `remaining` (optional in the schema, required except on a listed release cycle); optional `tip` |
| `owner-exception` | `quote`, `conversation`, `date` (`YYYY-MM-DD`); optional `references` |
| `upgrade` | none beyond `op_id` |
| `commit-record` | optional `op_id` (echoed, not journaled) |
| `withdraw-decision` | `name`, `reason`, `tasks` (plan task ids that depend on the IDR; may be empty) |

`commit-record` commits pending cycle bookkeeping, excluding queue-owned paths, and returns
`{changed, commit, paths, message, deferred, detail}`; a repeat with nothing to commit
returns `changed: false`. Phase-changing `advance`, `finish`, `owner-exception`,
dispatch, attach, delivery, loss, execution-check, child-link and release-continue operations return
the same object as `record_commit`. The message is `<cycle> record: <event> (rev N)` with
no `Cycle-Task` trailer. `inspect` returns `record: {git, pending, files, deferred}` and
offers `commit-record` when `pending`.
A replay commits a record an interrupted operation left pending without repeating
its mutation. `queue start-next` commits the queue and new record together.

`withdraw-decision` runs in Plan only. One record write marks `name` withdrawn
(`withdrawals` in the record) and removes `tasks` from the plan, recording a
`plan-revised` event with the removed tasks and the reason. It refuses a task that has
started or that a remaining task depends on. The low-level form is `cycle.py
withdraw-decision CYC --name N --reason R --task T`. `cycle.py defer CYC --decision N
--note TEXT` records the follow-up with the reason and the attempt history. `inspect`
reports `withdrawal-not-deferred`, `replaces-missing`, `council-attempts-exhausted`,
`withdrawn-no-attempts-left` and `nit-dispositions-missing`, and offers the matching
action. It also returns `classifications`, `councils` (each decision's rounds) and
`test_runs` (executed and reused suite runs, the retry subtotal and test minutes).

A success prints `{ok: true, op, cycle, op_id, changed, revision, replayed, ...}` with
the operation's own fields. A refusal prints `{ok: false, op, cycle, errors: [...]}`;
each error carries `code`, `field`, `expected`, `observed`, `problem` and `recovery`.
A recovery item is an action `{request, caller_fills, purpose}` or an argv
`{argv, caller_fills, purpose}`. Submit a `request` once the fields `caller_fills`
names are filled; the engine inserts no placeholder.

- `inspect` returns `revision`, `schema_version`, `status`, `phase`, `pass`,
  `pass_limit`, `head`, the `assignments` with their observation, `unmet` (`next` and
  `completion`), `reusable_evidence`, `problems` and `actions`. On a linked worktree it
  reads the main checkout's record. A typed `advance` action carries `expect_revision`;
  the low-level `return` and `pause` appear as argv. An unmet Verify or Review declaration
  appears as argv too: `checks CYC-ID` (caller fills `--check`) when no required check is
  declared, `coverage CYC-ID` (fills `--json`) when the coverage is unmet, and
  `review CYC-ID` (fills `--json`) when Review has no passing report and the latest report
  does not request changes. The caller writes the
  declaration or report; a `requirement-unmet` refusal carries the same argv. Each open attempt carries
  `recovery` (ordered), `window` and `liveness`, which is `unknown` unless a host reports
  a status its adapter lists. `problems` holds `orphan-retained-result` and
  `result-path-missing`; a lost attempt carries `leftovers`.
  `inspect` also returns `activity: {state, last, text}`: `state` is `idle` or
  `attempts-open`, and `last` is the newest event: record write, attempt last-seen,
  `Cycle-Task` commit, result file or worktree change. Each open attempt carries `last_activity`. Activity age is
  not liveness and never loss evidence.
  With `summary: true`, `inspect` prints `revision`, `status`, `phase`, `pass`,
  `pass_limit`, `unmet`, `actions` (each with its `request` or `argv` and
  `caller_fills`), `open_attempts` (identity, `state`, `observation`, `liveness`,
  `last_activity`, `problem` and `recovery`), `problems`, `record`, `activity` and
  `summary: true`. The full
  output is the default and keeps every field.
- `prepare-dispatch` returns `assignment`, `attempt`, `task`, `result_path`, `base` and
  an `invocation`: `{host, mode, tool, parameters, role_name, handle, attach, wait}`.
  The prompt begins with the mandatory role boundary, exact role-source read
  requirement, objectives, task, expected evidence, acceptance, constraints, scope,
  decision bindings and integration owner. `assignment_text` is an optional
  subordinate addendum. The generated
  preamble names the engine path, isolation, the attempt's result path, the task base, the
  task's trailer-tagged commits since that base and the required header lines and last
  line. The caller performs the invocation with its own dispatch tool, never through
  the cycle writer. `handle.source` says where the host returns the execution handle;
  `null` means the mode returns none and `attach-execution` is skipped. The Claude Code
  `blocking` invocation carries a conditional `attach` for an agentId that arrives without
  the child's final report; that agentId is a handle, and the caller waits on it with the
  marker await. `mode` is one of
  the host adapter's modes and defaults to the adapter's default: Claude Code `blocking`
  (the `Agent` call without `run_in_background`; handle-less) or `background` (the call with
  the flag; agentId); Codex `spawn`; OpenCode `foreground` (handle-less) or `background` (session id); OMP
  `blocking` (handle-less) or `background` (task id). Another value is refused
  `unknown-mode`. The mode is stored on the attempt and
  selects the invocation, whether a handle is returned and the recovery and loss-evidence
  rules.
- A result is complete only when its last non-blank line is
  the exact generated marker: new attempts use
  `Result-End: <assignment>/<attempt>#<token>`, and historical tokenless attempts keep
  `Result-End: <assignment>/<attempt>`. Its first lines are `Assignment: <id>` and
  `Attempt: <n>`. Before resuming the same open host execution after a hand-back,
  run inspect's `assignment --resume-token CURRENT --note TEXT` command. It retains
  prior result bytes and returns the new marker to relay. Cycle resume also rotates
  modern open tokens. A marker establishes completeness, never correctness.
- `deliver` returns `assignment`, `attempt`, `task`, `outcome`, `retained`, `sha256`,
  `result_path`, `status` and `untrailered_commits`. Every commit descends from the task
  base, and every trailer-tagged task commit since the base lies in the delivered range
  (`undelivered-task-commit`). Evidence paths are regular files in the docs tree.
  A blocked `stop` is retained and suppresses semantic failure routing. A stopless
  block lists its pause beside any route. The final listed release delivery also
  finishes the cycle; a failed finish remains under `finish` and in `inspect` while
  the delivered result stays committed.
- `mark-lost` takes `evidence: {kind, detail}` and a `note`. The kinds that count are
  `dispatch-refusal`, `terminal-status`, `blocking-returned`, `listing-absence` and
  `owner-confirmation`. For Claude Code `blocking`, `blocking-returned` counts only when the
  returned `Agent` result carries the child's final report (the detail names `final-report`),
  only the caller that saw the call return reports it, and it is refused once a handle is
  bound. `dispatch-error`, `wait-error`, `status-error`, `window-expired`,
  `result-missing` and `elapsed-time` are never evidence. A complete result at the path
  is refused `result-arrived`; deliver it. An attempt with no recorded host is refused
  `attempt-without-host`, and the recovery is the low-level `assignment --state lost`.
  `inspect` offers `mark-lost` inside each open attempt's recovery, never as a top-level
  action. Recovery order is the marker await, `attach-execution` (handle modes only),
  `deliver`, then `mark-lost`. While an attempt has no complete result, `inspect`
  returns its `wait` descriptor for the next window of at most 30 minutes. Windows are
  uncapped, and an ended window adds no action and changes no state.
- `advance` and `finish` refuse `stale-revision` when `expect_revision` is not the
  current `revision`. `advance` attaches a matching reusable receipt, never executes a
  check and never attaches a failure. `finish` returns `{status, completion}` and
  refuses `commits-not-linear` or an open attempt. Its response also carries
  `worktrees: {removed: [{path, branch, task}], kept: [{path, branch, reason}]}` for the
  cycle's merged, clean agent worktrees. A detached or locked worktree is kept. A removed
  worktree whose branch `git branch -d` refuses to delete shows `branch_kept`. A replay
  does not carry the field. An active or paused cycle's open attempt protects a
  worktree through its task trailer or a result path within it. Unknown ownership
  keeps the worktree and reports the owner record; cleanup never guesses from age.
- `owner-exception` records `quote` and `conversation` verbatim, the unmet completion
  requirements unchanged and every open attempt, in an `owner-exception` history event
  whose `owner` field has the shape `owner-complete` writes. It records an owner's actual
  instruction and is not a routine close path. A `references` entry that is a directory refuses
  `reference-is-directory` with candidate files.
- `prepare-dispatch` refuses `attempt-limit` after three attempts per task and role in
  one pass. A counted `return` is offered only in Verify/Test or Review with a remaining
  pass, outside fixed release lists; otherwise the handler offers a stop. A reserved attempt left by a crash
  refuses the next `prepare-dispatch` with `unresolved-dispatch`.
- A version-2 record refuses every mutating operation `needs-upgrade` and returns the
  `upgrade` request; a version-1 record refuses `unsupported-version`. `upgrade`
  refuses `assignments-running` while legacy assignments run and returns the low-level
  `assignment --state finished` argv (after the legacy agent's final report; legacy
  results carry no marker) and a conditional `--state lost` argv. It keeps the version-2
  bytes at `<docs_dir>/cycles/<id>/upgrade/v2-cycle.json` and records an `upgraded` history
  event with `previous_sha256`; a different file already at that path refuses
  `upgrade-backup-conflict`. `create` writes version-3 records.
- An operation the engine does not yet provide refuses `operation-unavailable`.

Each operation runs under one hold of the cycle lock: read, journal lookup, validation,
mutation, atomic save. A mutating command on a linked worktree refuses
`linked-worktree` and names the main checkout.

### Bounded context, frozen invocation and checkout proof

Full inspect exposes `context_read.references` with ready argv. Select a listed
`repo:RELATIVE`, `plugin:RELATIVE`, `result:ASSIGNMENT/ATTEMPT` or
`retained-result:ASSIGNMENT/ATTEMPT`. Only that exact recorded attempt binds an
external live report. Plan scope and report prose add no arbitrary read grant.

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact context-read CYC-0001 --ref repo:AGENTS.md
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact op CYC-0001 --json '{"op":"dispatch-invocation","assignment":"parser","attempt":1}'
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact op CYC-0001 --json '{"op":"execution-check","op_id":"parser-clean-start","assignment":"parser","attempt":1,"checkout":"/abs/repo"}'
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact op CYC-0001 --json '{"op":"execution-check","op_id":"parser-source-stage","assignment":"parser","attempt":1,"checkout":"/abs/repo","edited_paths":["src/parser.py","tests/test_parser.py"]}'
```

The read response includes path, size, full `sha256`, UTF-8 `text`, byte `offset`,
`end_offset`, `next_offset` and `complete`. Pages hold at most 16384 bytes, with no
split characters. For every later page pass `--offset NEXT --sha256 FIRST_DIGEST`;
changed bytes refuse. Total objects are bounded to 1048576 bytes. Oversized objects
refuse without content and report `sha256:null`; they were not read or hashed.
Invalid UTF-8, unsafe content and unavailable scanners refuse without text. Paths
must satisfy the code-owned roster, canonical containment and no-follow regular-file
checks. Credential locations, symlinks and special files grant no read. No output-file,
shell, network or secret-store capability is added.

Reservation scans and retains a complete immutable invocation bundle, including
selected content-addressed bodies, within that same total bound. Full inspect lists
`original_context.snapshot/retrieve` and `invocation_history`.
`invocation:ASSIGNMENT/ATTEMPT` and
`invocation-history:ASSIGNMENT/ATTEMPT/SNAPSHOT_SHA256` retrieve retained context.
Read every selected object completely with its supplied digest/pagination and
canonical origin/source directory. Never resolve references relative to storage.

`dispatch-invocation` needs no original prepare request. It returns exact frozen
parameters for a current eligible reserved attempt after current source/grant checks.
Running/closed attempts expose context without permitting another dispatch. Stale
bindings refuse with exact-attempt recovery; no handle alone proves no execution.
Replay never rerenders. Token rotation preserves history and binds a new snapshot.
Historical attempts without snapshots report original context unavailable.

Codex spawn parameters are `task_name`, `agent_type`, `message`; native wait receives
only `timeout_ms` (at most 60000), no `ids`. A global wake-up is not completion.
Use the recorded handle/attempt and exact current marker; liveness stays unknown.
Report actual host/version observations separately from fixtures or projections.

Workers use `execution-check` before edits, with a fresh op_id and current attempt.
The original review base stays immutable; separate proof records the execution HEAD.
Exact paths/provenance permit bookkeeping descendants and retained same-task source.
A commit-message prefix or a blanket docs exclusion proves nothing. A clean older
registered checkout gets ff-only recovery; foreign source, unrelated ancestry and dirty
initial source require normal isolation/integration. No reset or inferred loss follows.

Before a source commit, stage intended edits and checkpoint exact `edited_paths`.
The clean-start token and checkpoint seal exact index/working-file object identities.
Each task-trailered source commit may contain a nonempty sealed subset;
changed bytes, unsealed paths and skipped source commits refuse. The verified child merge below is the only admitted merge form. A later
check retains remaining sealed edits. Recheck unexpected HEAD changes. Optional
attach/delivery proof failure preserves actual handles/results with unavailable
metadata; explicit worker proof remains strict. Plan scope grants no edit ownership.

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
checkouts until parent proof and delivery finish.

### Route classification

Finding disposition permits `return` only for a blocking finding. Advisory and cosmetic
findings never spend a pass.

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

`inspect` exposes recorded classifications and current cached suggestions. Suggestions
select only permitted routes and establish no correctness, authorization or test pass.
Compare their premises with retained evidence before acting. Missing or contradicted
advice leaves deterministic legal actions available. Keep the recorded review floor.
Use `cycle.py defer` for follow-up findings. A sizing fallback prints a receipt for
`create --sizing-receipt` after the responsible agent chooses the type.
`.bionic.yml` `decisions: {classifier: off}` opts out. Historical classifications retain
their original interpretation. Status and dashboards show `Classifications: N`; full
inspect retains question, answer, fallback, model, provider and reported cost.

The `advice-refresh.kinds` values are `execution-arrangement`, `context-selection`,
`focused-test-ranking`, `review-routing`, `finding-disposition`,
`review-finding-grouping`, `handoff-completeness` and `failure-routing`.
Task, role, assignment and failed `TE-…` receipt references must exist; arbitrary report
text is not accepted. For example, after replacing the cycle/task with recorded IDs:

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . op CYC-0001 --json '{"op":"advice-refresh","op_id":"refresh-advice-1","task_id":"parser","role":"developer","kinds":["context-selection","focused-test-ranking"]}'
```

Known refusal codes return deterministic `recovery_handlers`: `unresolved-dispatch`,
`attempt-limit`, `delivery-conflict`, `superseded-attempt`, `result-path-missing`,
`stale-revision` and `op-id-reused`. Each action keeps its existing prerequisites.
Generated reopen actions carry `--expect-revision`; stale offers refuse without writing.
Inspect before retrying. A report's explicit stop suppresses semantic failure routing.

## Low-level commands

The commands below stay for diagnosis, for version-1 and version-2 records, and for
the recoveries a typed refusal returns. On a version-3 record, a low-level command that
assigns or changes a task refuses while a reserved or running attempt holds it. Do not
sequence `handoff`, `assignment` and `task` by hand as the normal path.

## Plan and tasks

`plan CYC-ID --file plan.json --reason TEXT` takes the complete plan in Plan or Build,
preserving its predecessor. Fields are `scope`, `constraints`, `acceptance`,
`verification`, `tasks`, optional `streams`, and `revision` (the writer updates revision). Refactor adds
`preserved_behavior` and `improvement`. Plan tasks cover every phase of the type.
Each task has this shape:

```json
{
  "id": "build-parser",
  "phase": "build",
  "description": "Correct empty-input parsing",
  "depends_on": [],
  "status": "pending",
  "expected_evidence": ["Empty input regression check passes"]
}
```

A plan file sets plan content and carries no delivery field: `assignee`,
`result_path`, `commits`, `evidence`, `stage`, `note` or `replaced_commits`. Each file
task carries status `pending`, with one exception: while the cycle is in Plan, a
Plan-phase task may carry `done`, so the plan writer marks its own finished Plan tasks
in the same write. Such a task's dependencies must be done too. The writer refuses
anything else and names `task`, the command that records state.

`create` seeds one Plan-phase task, `plan`, in every type that starts in Plan, so the
first `inspect` offers its `prepare-dispatch`. `change-type` into such a type seeds the
same task. A plan file that omits `plan` drops it,
unless an attempt holds it; then the recorded task stays.

A revision pairs file tasks with recorded tasks by id. A paired task keeps its status
and delivery when its `phase`, `description`, `expected_evidence` and `depends_on`
are unchanged. A change to any of them, including a reordered list, makes the task
pending and clears its stage. Its commits, evidence, assignee, result path and note
stay. A new id starts pending. An omitted task leaves the plan, and the
`plan-revised` event keeps it. Re-adding that id later starts a new pending task.
A kept task is revalidated as described under Advancement and loops.
Changing `integrates` participates in that task revalidation. Optional `streams`
entries are `{id, paths, independent}`. IDs and literal repository-relative paths
are unique; independent scopes cannot overlap by path or directory prefix.
Absolute paths, traversal and glob scopes refuse. A Build task may name
`integrates: [TASK-A, TASK-B]`; each is a distinct existing Build task also listed
in `depends_on`. Missing historical fields mean no declared facts.

Use `task-add CYC-ID --file task.json` for a task and
`task CYC-ID --task-id ID --state pending|active|done|blocked` for its state.
Quick-fix has no Plan transition. It accepts `task-add` for its current phase or any
later phase, so it can record expected evidence for Verify, Review, and Reflect up
front. Other types add tasks for the current phase, or any phase while in Plan.

**Fix task.** In Verify or Review, `task-add` accepts a task carrying
`fix: {finding, eligibility}`. The task phase equals the cycle phase, the task starts
pending with no delivery fields, and the writer sets `fix.pass`. Allow one fix per phase
per pass. A Review fix needs the pass's latest review to be blocking with at least one
blocking finding. One fix may answer several; `finding` names them, and the optional
`fix.findings` lists their ids (`r<N>:blocking:<index>`, distinct, from the latest
review). Each finding meets the eligibility and the whole fix stays small. `task --fix-before TE-ID` names a receipt that recorded the failure.
`--fix-after TE-ID` names the current passing receipt for the same check id. Done
needs a commit, both receipts and, for a Review fix, an approving fix-diff review.
`fix` is bookkeeping for the review basis (the basis version is unchanged) and a
delivery field, so plan files refuse it. A done fix stays done on a new pass; an
unfinished one leaves the plan. `handoff` lists fixes. A fix changes no pass, phase or
plan revision.

A failed acceptance criterion also qualifies for the same one fix allowance.
Supply `fix.criterion: {index: N, observation: PATH}` with the zero-based acceptance
index and a committed docs-relative JSON observation. Its exact fields are
`criterion` (the same integer), `value` (the observed measurement), `met` (boolean),
and `commit` (the measured ancestor commit). The before observation has `met: false`.
Attach a committed after observation with `task --fix-observation PATH`; done needs
`met: true`, a fix commit and the existing scope, size and review obligations. Criterion
fixes use these observations rather than `--fix-before`/`--fix-after` receipts.

## Task records

Add `--compact` before the subcommand to print one JSON line instead of the full
record: `ok`, `cycle`, `phase`, `pass`, `status`, `updated_at`, `changed`, and `task`
when a task was named. A refusal prints `{"ok": false, "error": ...}` and exits 1.
Check the exit code of every call; never pipe it away.

Write each command in full, with the absolute plugin root, the absolute result path
and the full commit SHA typed out. The commander's role contract forbids a shell
variable, `cd`, chaining, pipes, redirection and `--output`. Its OpenCode allow-list denies a
command line that starts with anything other than an allowed form, such as a variable
or `cd`. The allow-list does not stop chaining, pipes, redirection, `git log --output`,
a `${CRUX_PLUGIN_ROOT}` form inside an allowed line, or another script whose arguments
contain `cycle.py`. Those bounds rest on the role contract.

```bash
# A low-level record of an active unit, with its recorded result path:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact task CYC-0001 --task-id build-parser --state active --assignee developer-1 --result-path /abs/os-temp/crux-results-CYC-0001-RANDOM/developer-parser-attempt-1.md
# A delivered unit:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact task CYC-0001 --task-id build-parser --state done --stage implemented --commit 0123456789abcdef0123456789abcdef01234567 --evidence evidence/build/parser.md --note 'unit committed'
# After the dev-lead merges the unit:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact task CYC-0001 --task-id build-parser --state done --stage integrated --commit 0123456789abcdef0123456789abcdef01234567
```

`task` takes these optional flags: `--assignee TEXT`, `--result-path PATH` (absolute,
or relative to the repository root; never docs relative), `--commit SHA` (repeatable;
must resolve to a commit), `--evidence PATH` (repeatable; docs relative, must exist),
`--stage implemented|integrated` (integrated needs every recorded commit to be an
ancestor of HEAD), and `--note TEXT`. `reconcile` resolves a result path from the
same base. The writer refuses to mark a task done when its relative result path
names a file only under the docs root. Record the path again in the repository-root
form. An identical repeat
writes nothing and returns `changed: false`, so a duplicate notification is safe.
A late `--stage implemented` after `integrated` that names only recorded commits is
already satisfied and also returns `changed: false`. Evidence paths are stored in
normalized form, so `./e.md` and `e.md` are one entry.

`--adopt-commit SHA` (repeatable) adopts a commit already delivered by this cycle in
an earlier pass. It must be an ancestor of HEAD with the current task's trailer and
matching earlier delivery provenance. The writer retains that source delivery,
records adoption provenance and leaves the ordinary current-base gate intact.
Historical low-level deliveries have a null source attempt. Adoption never admits
a foreign or undelivered commit.

After a rebase, record the rebased commit in place of the old one:

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact task CYC-0001 --task-id build-parser --replace-commit 0123456789abcdef0123456789abcdef01234567 89abcdef0123456789abcdef0123456789abcdef --note 'rebased onto HEAD before merge'
```

`--replace-commit OLD NEW` requires `--note`. OLD must be a recorded commit; it need
not still exist. NEW must resolve and must not already be recorded. The writer swaps
NEW in for OLD and appends `{from, to, at, note}` to the task's `replaced_commits`.
The history event records the swap too, so the old reference stays traceable. An
identical repeat returns `changed: false`. Then `--stage integrated` succeeds once
NEW is an ancestor of HEAD. `reconcile` does not propose a replaced commit again.
Tested and reviewed are not stages: the evidence, coverage and review gates alone
establish them.

Every developer commit message ends with one final paragraph of trailers, with no blank
line between them, because git reads trailers only from the last
paragraph. A host-added `Co-Authored-By:` line joins that paragraph; after a blank line it
hides `Cycle-Task:`.

```text
CYC-0001 build-parser: correct empty-input parsing

Cycle-Task: build-parser
Co-Authored-By: Name <name@example.com>
```

`handoff CYC-ID` is read-only. It prints the phase, pass, status, active tasks with
assignee and result path, delivered tasks with stage and commits, pending tasks, and
a `next_action` line. It also prints `assignments`, the running assignments with
`last_seen` and `elapsed_seconds`, and fixed `resume_steps`. Include its output in a
hand-back, and read it before any resume or dispatch.

## Assignments

On a version-1 or version-2 record an assignment records that an agent is running a
piece of the cycle. Its id is a task id, a stream id such as `stream-a`, or a singleton
role name. Version-3 records take assignments through `prepare-dispatch`; these
commands diagnose or repair them:

```bash
# Start a legacy assignment; add --agent when the handle is known:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact assignment CYC-0001 --id build-parser --state running --role developer --task build-parser --result-path /abs/os-temp/crux-results-CYC-0001-RANDOM/developer-parser-attempt-1.md
# Record a handle that arrived after the start:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact assignment CYC-0001 --id build-parser --seen --agent HOST-HANDLE
# After its final report has returned and its execution has ended:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact assignment CYC-0001 --id build-parser --state finished
# Only with host evidence that it ended without a final report:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact assignment CYC-0001 --id build-parser --state lost --note 'host lists no live handle HOST-HANDLE'
```

A completed or abandoned cycle refuses every mutation except one: `assignment --state finished`
on a running entry. A final hand-back that arrives after closure is still recorded.

`--state running` refuses while the same id is running, even as an identical replay,
and while another running assignment holds the same `--task`. The refusal names the
live entry's id, role, agent (or result path while the agent is unknown), `started_at`
and `last_seen`. Message or await that agent instead, and dispatch nothing. A start on
a finished or lost id resumes it as the next attempt; the history event keeps the
previous entry. `--seen` refuses unless the entry is running, and always advances
`last_seen`. An identical `finished` or `lost` repeat writes nothing and returns
`changed: false`. A paused cycle accepts `--seen`, `finished` and `lost`, and refuses
a start.

**The lost rule.** An assignment becomes lost only through `--state lost` with a note
naming host evidence that the execution ended without a final report: the host
reports it terminated or failed, the host lists no live handle for it, or the owner
says it stopped. Elapsed time since `last_seen` never makes an entry lost. When the
agent is null, look for a live host execution matching its role and result path
before recording it lost. A forced hand-back whose background work still runs stays
`running`.

`reconcile CYC-ID` recovers a stale record from evidence: commits whose message names
the cycle and carries a `Cycle-Task: <task-id>` trailer, worktrees, and the recorded
commits and result paths. It reports discrepancies and changes nothing. `reconcile
CYC-ID --apply` writes only what that evidence establishes, such as marking a linked
build task implemented, or integrated when every linked commit is an ancestor of HEAD.
A commit establishes implementation only. A commit linked to a test, review, release
or reflect task leaves that task unchanged and is reported as unresolved. Reconcile
never infers tested, review approval or completion, and never advances a phase. It
applies updates in dependency order. When the writer refuses one, it exits 1 and
reports the updates already applied. A missing result file counts as a discrepancy
only for a done task. Use it for recovery, not to keep the dashboard current.

`plan-details CYC-ID --file details.json --reason TEXT` records constraints and
verification on a quick-fix in Build or Verify. Other types use `plan`. The file holds
`constraints`, `verification`, or both, each a non-empty list of non-empty strings.
No other key is accepted. The command replaces the named fields, keeps the rest of
the plan, raises `plan.revision`, and records the previous plan with the reason in a
`plan-revised` history event.

## Checks and review

Declare required checks through `checks CYC-ID --check CHECK-ID` (repeat `--check`
for the complete set). Execute or reuse them with `test-evidence.py` as described
in [testing.md](testing.md). Attach valid results using:

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact evidence CYC-0001 \
  --check-id parser --evidence-id TE-ID --use reused
```

For new version-two records, also use `coverage CYC-ID --file coverage.json`:

```json
{
  "affected": ["Empty-input parsing and parser callers"],
  "checks": [{"check_id": "parser", "rationale": "Regression and existing caller tests cover the affected behavior"}],
  "not_selected": "Packaging is unchanged. Cycle bookkeeping is excluded because this check does not read it."
}
```

The selected IDs must match `required_checks`. This declaration and valid evidence
are required before Verify advancement, Review, and completion.

Declare Build checks through `checks CYC-ID --phase build --check CHECK-ID`, in the
Build phase, repeating `--check` for the complete set; each call replaces the set.
`advance` out of Build refuses unless every Build check has current-pass evidence
that validates, with the same `missing passing evidence` and `invalid evidence`
messages as Verify. A failing receipt cannot be attached, so a failing related test
stops the cycle in Build. Coverage is not required at Build. In a plugin-authoring
checkout the Build checks must include every registered `checkout:` check except the
release-tier suites (`checkout:unittest-release:...`): the two full suites,
`checkout:unittest:crux/scripts/tests:test*.py` and
`checkout:unittest:tools/tests:test*.py`, and the tier check `checkout:test-tiers`; the
refusal names each missing id. A release-tier receipt never satisfies Build, Verify,
Review, Reflect or `finish`. In that checkout Verify, Review and Reflect also refuse
unless both full suites and the tier check have current passing evidence. Elsewhere
an empty set is allowed. A Build check that is also a required check is satisfied at
Verify by the same evidence id, with no new execution while its inputs are unchanged.
Build checks stay outside the review basis. [testing.md](testing.md) gives the
selection rule.
Changing coverage does not itself execute checks.

A passing review binds to a basis: the plan's scope, constraints, acceptance,
verification, preserved behavior and improvement, the plan tasks up to the
review-bearing phase, the required checks, the review policy, the current-pass
evidence declarations and the coverage. Each task contributes only `id`, `phase`, `description`
and `expected_evidence`. Changing any basis field after approval invalidates the
review, as does a source change or a task added before the review-bearing phase.
Bookkeeping does not: a task's `status`, `depends_on`, `assignee`, `result_path`,
`commits`, `evidence`, `stage`, `fix` and `note`, the plan's revision counter, plan tasks of
phases after the review-bearing phase (Reflect today), the reflection, completion
and history. A task field outside both lists is refused, so a new field needs a
classification. A historian can add a Reflect task after approval and still
complete the cycle. Reports record `basis_version: 4`.

`evidence` stores the receipt's normalized-declaration digest on the ref as
`declaration_sha256`. The version 4 basis maps each required check to the
`declaration_sha256` of its latest current-pass ref; a ref recorded without the field
contributes its evidence id. Refreshing a check with the same declaration keeps the
review bound. A changed command, inputs or exclusions under the same check id unbinds
it, and a scope change unbinds it through the report's source fingerprint. Changes
outside the reviewed scope, such as a merge, are covered by live evidence validation
at every gate, not by the review.

The source fingerprint matches scope entries with Python glob semantics, so `**` is
recursive. It excludes untracked git-ignored files, the cycle's own record directory and
`__pycache__`. Tracked files always count, even when an ignore rule matches them.
Writers record it as fingerprint version 2, which is folded into the digest and adds no
schema field. Version 1 hashes ignored files too. It applies when the project root is not
inside a git work tree, git is not installed, or git cannot classify a path. A review,
completion or reduction record made under version 1 still binds while every file,
ignored ones included, is unchanged. A binding check accepts either version's digest
of the current source.

A version 3 report binds to the version 3 digest, which hashes the current-pass
evidence list. A version 1 or 2 report binds only to its own version's digest. A report without a version, recorded before
versioning, still binds when its digest matches the version 2 basis or the earlier
whole-plan basis.

`--use` is `executed`, `reused`, or `waited`; report what happened.
Use `scrutiny CYC-ID --scrutiny LEVEL --rationale TEXT` with repeated `--risk`
when needed. `review CYC-ID --file report.json` takes exactly these fields:

```json
{
  "reviewer": "reviewer-1",
  "scope": ["src/parser.py", "tests/test_parser.py"],
  "evidence": ["The referenced test record and reviewed diff"],
  "blocking": [],
  "advisory": [],
  "cosmetic": [],
  "verdict": "approve",
  "rationale": "The correction satisfies the criterion with focused coverage."
}
```

Use the actual scope declared in the plan, evidence, and independent reviewer. A
report that omits `scope` records the plan scope, so the reviewer need not copy it.
A blocking finding includes `path`, `consequence`, and `evidence`. The alternative
verdict is `changes-required`. The writer binds the report to current inputs and
adds effective scrutiny; it cannot perform the review on the agent's behalf.

A fix-diff review is this same `review` command with the optional key `fix_task`
naming that pass's Review fix task. The fix task needs a recorded commit. The
reviewer must differ from the fix assignee and the implementers, and the scope still
equals the plan scope. One fix-diff review is allowed; a blocking one needs a counted
return. The writer stores the ref in `fix.review`.

## Simplify cycles

A simplify cycle needs a selection IDR. Its `contents` add `assessed` (a non-empty
string), `proposals` (a non-empty list) and `selected` (a non-empty subset of the
proposal ids) to the required keys. Each proposal has exactly `id`, `removes`,
`retained_behavior`, `objectives`, `decision_clauses` (or one entry `none: <reason>`),
`expected_savings`, `verification` and `paths`. Every selected proposal's `paths` lie
within the plan scope. The authority is the approval of that exact revision: an owner
approval always suffices, and a council approval only for a queue-started cycle whose
plan scope lies within the item's frozen scope. A queue-started cycle change-typed into
simplify qualifies on the same terms.

Scope containment is textual. A plan entry lies within the item scope when it equals an
item entry or lies under one as a directory. A glob or `.` in a queue item scope never
covers a plan entry other than an identical one. Such a scope fails the council path,
and owner approval is required.

`reduction CYC-ID --file reduction.json` records the reduction evidence. It runs only
for simplify and only in the Verify phase:

```json
{"areas": {"production": {"change": "decrease", "before": "3 branches, 1 fixture",
  "after": "2 branches, no fixture", "evidence": ["git diff --stat HEAD~1"]},
  "tests": {"change": "unchanged", "before": "n", "after": "n", "evidence": ["tests/"]},
  "instructions": {"change": "unchanged", "before": "n", "after": "n", "evidence": ["AGENTS.md"]},
  "execution": {"change": "unchanged", "before": "n", "after": "n", "evidence": ["Makefile"]}}}
```

The file holds exactly `areas`, whose object holds exactly the keys `production`,
`tests`, `instructions` and `execution`. Each area holds exactly `change` (`decrease`,
`unchanged` or `increase`), `before`, `after` and `evidence`. An area's dimensions are
its concepts, branches, states, dependencies, configuration, fixtures, mocks and
operational steps, as they apply, not only lines. Each area's `before` and `after` name
every dimension that changed. An area is `increase` when any dimension rises. It is
`decrease` only when one falls and none rises. The writer checks the shape, and the
reviewer checks the named dimensions against the diff. The writer stores `pass`, `at`
and `input_sha256` (the source fingerprint) with the areas. Verify advance and Reflect completion refuse an
`increase`, no `decrease`, or a record from another pass or an older fingerprint. Report
an increase and propose it as different work, a queue item or an owner report.

## IDRs and ADRs

`decision CYC-ID --kind idr --name NAME --file decision.json` retains reasoning.
The contents require `alternatives`, `approach`, `assumptions`, `constraints`, and
`intended_evidence`. Inspect the returned decision path, then convene:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle-council.py" --repo-root . \
  --cycle CYC-0001 --purpose idr --subject DOCS-RELATIVE-DECISION-PATH \
  --question question.txt
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact approve-decision CYC-0001 \
  --subject DOCS-RELATIVE-DECISION-PATH --approval DOCS-RELATIVE-APPROVAL-PATH
```

Council purposes are `idr`, `adr-creation`, `adr`, and `consultation`.
Omitted, `--max-tokens` leaves each seat's output budget to its registry output limit:
half the limit, at least `32000`, at most the limit. A reply that stops on its budget is
retried once at the seat's limit. Given, the value is the first-attempt budget for every
seat, for example `--max-tokens 64000`; it must be a positive integer no larger than the
smallest output limit of the three selected models. An oversized request is refused before
an attempt is created or any request is sent. The council library records the
`max_tokens` of each seat attempt in the vote's `attempts`, and the council
record's `seats` carry them. Legacy attempt metadata records the explicit
value, or null when omitted; historical attempts need no new field. Each seat call has a
1200 s deadline per attempt, so run the council as a background command. This option
changes no seat assignment, retry count, round limit, or approval threshold.
Consultation is advisory. Retain exact subjects; do not edit approved reasoning.
A revision is a new decision record with the same name and fresh council approval.

Full inspect's `councils` recovery view supplies exact subject/attempt/result
references, digests, supported probe/await/recover argv and prerequisites. Architect
actions appear only for an eligible current result. Inspect sends no provider call,
writes no attempt and recovers nothing. Descriptors do not expand a role's grants.

New gateway attempts always persist a request checkpoint before transport and an
outcome checkpoint before a locally available result is acknowledged. Persistence
failure stops further requests and positive approval. A crash before durable outcome
leaves that call unknown; a known negative and validated event references survive
interruption. Recovery sends no request and closes the same counted attempt.
Partial events never constitute approval, copy votes into a new attempt or reset a
budget. Later authorized convening retains findings as historical context beside
fresh votes. New architect approval/application revalidates current checkpoint
bindings; pure sealed historical validation and already-applied acceptance retain
their standing. Historical/native-Lite protocols remain unchanged.

The owner may approve an exact IDR revision directly. Write
an owner approval record under the cycle directory and pass its path as
`--approval`. It carries exactly `format` (`crux.owner-approval`), `purpose`
(`idr`), `cycle_id`, `subject`, `subject_sha256`, `origin`
(`owner-conversation`), `quote`, `date` (`YYYY-MM-DD`) and `conversation`.
`quote` is the owner's own words, verbatim. Never write this record without an
actual owner instruction to quote. A later revision needs a new approval.

The legacy `owner-approval CYC-ID --subject PATH --quote TEXT --conversation TEXT` writes that
record for you at `cycles/CYC-ID/approvals/owner-<decision>.json`, binding the
subject's current sha256. It refuses an empty quote, a missing subject and an
existing record, and never defaults the quote. `--approve` also runs
`approve-decision`. Its `--print-command` option still prints one shell-quoted line
without writing. New conversational handling uses the supported evidence interface
below; it requires no owner terminal handoff.

### Conversational owner decisions

Use `cycle.py owner-decision present|capture|apply --json REQUEST`. These are
standalone subcommands, not values of the typed operation's `op` field. The same
literal cycle.py shell lane supports them. The record schema is
`crux/schemas/owner-decision.schema.json`; inspect each subcommand's help for input.

Every request carries `purpose` (`idr` or `adr-acceptance`), `cycle_id` (exact owning
cycle, or null for a standalone ADR), canonical docs-relative `subject`, and exact
presented `subject_sha256`. No actual owner evidence is supplied by these examples.

- `owner-decision present` also takes `op_id` and the concrete `question`. It
  binds the current subject digest and returns a `presentation` path/digest.
- `capture` also takes its own `op_id`, that `presentation` reference,
  `disposition` (`approve`, `reject` or `pending`), verbatim `quote`,
  `source` (`kind: conversation|tool-question`, `reference: ACTUAL_REFERENCE`),
  `owner_date` (`YYYY-MM-DD`) and `supersedes` (null for the first capture; otherwise
  the exact current capture path/digest). Transcribe only the explicit answer the
  trusted owner-facing caller observed or its parent supplied with real provenance.
  Ambiguous continuation is pending. An operation id is not conversation provenance.
  Never manufacture an identifier or infer disposition from a continuation.
- `apply` takes `capture` path/digest; ADR acceptance also takes `approval` naming
  the existing exact council record. Fresh application requires the unique current
  unsuperseded approval, current presented bytes and existing lifecycle/council checks.

The writer checks structure, retained presentation, purpose, cycle, subject and
digest; it authenticates neither the speaker nor the truth of a transcribed quote.
Reject/pending never approve. Lineages include purpose, cycle-or-standalone ownership,
subject and digest; a new revision has a new lineage. Forks, cycles, stale predecessors,
cross-subject supersession and conflicting replay refuse under the mutation lock.
Corrections append immutable superseding captures, never overwrite earlier words.

Already-applied replay reports `already_applied`, the original application and the
later current disposition with `lifecycle_changed:false`. It neither reapplies an
old approval nor revokes historical acceptance. A lifecycle change uses the existing
separately authorized transition; an IDR follows its revision/withdrawal rules.
Receipt-before-lifecycle recovery preserves prior receipt bytes and records the
current descendant approval through the writer's sealed binding. Never repair these
files manually. Legacy approvals and acceptances retain their original interpretation.

This evidence interface grants no pass extension, owner exception or outward action.
The commander may record real owner evidence through cycle.py; council execution and
judgment-bearing document authorship retain their existing role lanes.

Create ADRs through `decision-policy.py propose`, not `cycle.py decision`.
Inside a cycle, first approve an `adr-creation` justification subject. Then:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/decision-policy.py" --repo-root . propose \
  --file proposal.json --origin cycle --cycle CYC-0001 \
  --creation-subject DOCS-RELATIVE-JUSTIFICATION-PATH \
  --creation-approval DOCS-RELATIVE-APPROVAL-PATH
```

Other origins are `direct`, `whiteboard`, and `inbox`; omit cycle arguments there.
The proposal contains `title`, `body`, and `governs`. Each rule needs `domain`,
`rule`, `scope`, and a kebab-case `handle`; the writer binds the allocated ADR ID.
Council must separately approve the resulting ADR with purpose `adr`.
Use `decision-policy.py accept --subject PATH --approval PATH`, plus
`--human-approval TEXT` containing the owner's actual instruction when required.
Regenerate standard ADR indexes/projections after writes, respecting their commit
preconditions. Never retrofit new acceptance onto historical provenance.

## Advancement and loops

`advance CYC-ID` advances only when the phase requirements hold.
`return CYC-ID --progress yes|no --improved TEXT --unresolved TEXT
--next-change TEXT --justification TEXT` records the assessment and return.
No progress or an exhausted limit pauses instead. `pause` takes `--reason`.
`resume` takes `--reason` and, after stalled progress, `--new-evidence`.

A return or resume keeps delivered Plan and Build work. Two events start a new pass: a
counted return that does not pause, and a resume after a pass-limit or
progress-stalled blocker. Such an event lands in Build and sets every Verify, Review and
Reflect task to pending. A Plan or Build task keeps its status and delivery only when
it revalidates. Each check is independent: an integrated task's recorded commits are
all ancestors of HEAD, and every evidence path still exists. A failed check or a git
error makes the task pending and clears its stage; its commits and evidence stay. A
Plan task that fails is redone and marked done from Build. A return that pauses
changes no task; its resume applies the rule. A resume that starts no pass changes no
task. The `return-requested` and `plan-revised` events keep the full prior plan. Only
the first Plan exit checks plan completeness; a plan revised in Build is not
re-checked, though the later gates still hold.

No flag reopens a task. To rework a delivered build task, change its `description`
or `expected_evidence` in the replan, for example by adding the finding's regression
check. Both fields enter the next review basis. Adding a fix task to its `depends_on`
also reopens it. Or add a separate fix task and leave the original done. Reopening
is not transitive: a done task that depends on a reopened task stays done. Verify and
Review on the integrated source are the backstop for those dependents. Without a
replan after a return, no build task reopens.

A task that failed revalidation is pending again. Recover it by its cause:

- Evidence file missing: restore the file or record its replacement with
  `task --evidence`, then mark the task done.
- Commit no longer on HEAD after a rebase: record the rebased commit with
  `task --replace-commit`, then mark it done with `--stage integrated`.
- Commit object gone, or the work must be redone: replace the commit the same way,
  or omit the task in one replan and re-add it under the same id in the next.
`extend CYC-ID --limit N --human-approval TEXT` records explicit owner approval;
never invent or infer the owner's instruction. `change-type` takes `--type` and
`--reason`, plus human approval when required to avoid bypassing an exhausted limit.
Changing type out of simplify always needs `--human-approval`.

`reflect CYC-ID --file reflection.json` records `outcome` (a string) and `lessons` and `remaining` (each a non-empty list of
non-empty strings; use `["none"]` when there is nothing).
Use `advance` to complete or `abandon` after recording an abandonment reflection.
A listed release cycle has no reflection (see Release cycles above).

When the owner closes a cycle whose gates cannot be satisfied, record
`owner-complete CYC-ID --file owner.json`. The file carries exactly `origin`
(`owner-conversation`), `quote` (the owner's verbatim words), `date`
(`YYYY-MM-DD`), `conversation`, and `authority` (repository-relative files the
owner cites). The writer sets the status to completed and appends a history event
with the quote and each authority file's sha256. It rewrites no blocker, evidence,
review, release, or reflection. Never use it without an actual owner instruction. It
is not a routine close path: Reflect bookkeeping needs no evidence refresh and no
review re-record (see [testing.md](testing.md)).

Before completing a version-two record, commit the intended changes, then record:

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact completion CYC-0001 \
  --commit FULL-COMMIT-SHA --remaining 'Only final cycle bookkeeping awaits commit'
```

Repeat `--commit` for multiple delivery commits, latest last. Commits must exist,
be ancestors of HEAD, and cover current scoped inputs. Dirty or untracked scoped
changes block completion. Untracked git-ignored files, such as council `attempt-*.lock` files, are
neither scope changes nor part of the source fingerprint. Completion fails closed when
git cannot classify the scope files. Unrelated work may remain; describe it in `--remaining`.
Only a real user request for uncommitted delivery allows `--exception TEXT` instead
of commits. Quote the instruction and its context; no council or agent can grant it.
Re-record completion after scoped changes. The record's own bookkeeping is excluded
from commit binding to avoid a self-reference; commander commits that final record
after `advance` closes the cycle and reports its SHA too.

Version-one records remain readable and retain their original completion semantics.
For an active version-one cycle, follow the current coverage and commit instructions
and report the evidence explicitly; the old schema does not enforce the new fields.

## Friction log

`friction CYC-ID --json REQUEST` appends one row to
`<docs_dir>/cycles/<id>/evidence/friction.md` under the cycle lock and commits the record.
The request holds exactly `who`, `what`, `cost`, `category` and `fix`, each a non-empty
string:

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . friction CYC-0001 \
  --json '{"who":"commander","what":"queue list printed 88 KB","cost":"one extra read","category":"tooling","fix":"print one line per item"}'
```

The writer creates the file with the standard header when it is missing, takes the next
`F<N>` id, folds newlines to spaces and escapes `|`. It prints `{ok, cycle, id, path,
record_commit}`. The Reflect phase reads the log.

## Release cycles

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

Opt in through `prepare-dispatch.release_continuation: {"version":"X.Y.Z"}`.
Supply `capabilities: {available: [...], unavailable: [...], observation: "..."}`
from actual host evidence. Continuation requires `read-context`, `write-result`,
`source-edit`, `execution-check` and `release-continue`; no required capability may
be unknown. Do not claim those capabilities from generated files alone.

Write the current marked report before `release-continue`. Supply the actual step's
exit code and, except for prep, the SHA-256 of the current canonical release ledger.
Prep supplies its committed source. Read `continuation.message`, `commands`,
`result_path`, `base` and fresh `delivery_token` for the next logical task.
The `stop` values are `owner-decision`, `approval-wait`, `contradicted-premise`,
`outward-act` and `escalation-loop`. Use a distinct operation ID for each delivery;
replay the same request only for recovery. Do not rerun publication to replay bookkeeping.

`create --type release --list beta|official` makes a release cycle. `--list` is
required: `create` refuses a release without it, and refuses `--list` on any other
type. The writer generates the tasks, each in phase `release` and depending on its
predecessor. The beta list is `prep`, `prepare`, `verify`, `beta-and-smoke`, `tag`,
`record`. The official list is `live-check-and-go-ahead`, `official`, `record`. The
cycle has one phase, `release`, and pass 1. Its limit of 1 is inert and the progress
view shows no limit. A beta cycle's scope names the release-prep paths and the log file;
an official cycle's scope names the log file.

A listed release cycle allows only `task`, `completion`, `pause`, `resume`, `abandon`,
`owner-complete`, `advance`, `assignment` and the read-only commands. `assignment` is
bookkeeping: it adds no step, phase or gate. The writer refuses every other
action: plan, task-add, plan-details, checks, coverage, evidence, review, decision,
reflect, return, extend and change-type. `validate` refuses a record whose task ids,
order, phase or dependencies differ from its list.

Record each step with `task`. `advance` completes the cycle when every task is done and
the completion record holds. In the Crux development repository `release.py record --cycle` closes the
cycle for a published target: after its copy and secret scan succeed, it prepends the
log op, commits the copy and the log alone, and marks unheld tasks done. An open
assignment awaits its delegator's normal delivery; the last listed delivery finishes
the cycle. With no open assignment, record runs `finish` itself. Repeating record
recovers local copy/commit/completion work and never repeats publication, tagging or
official sync. It needs no reflection, coverage, review or decision.
`abandon` needs no reflection, because the record step keeps the closure reason.

Authorizing a release queue item also authorizes publishing that item's version to its
target. It authorizes no push and no other outward action. In the Crux development
repository `release.py beta` and `release.py official` take the owner's quote from the
queue chain of the bound cycle, so the agent runs the bare command:
`uv run tools/release.py beta --version X.Y.Z` or
`uv run tools/release.py official --version X.Y.Z --cycle CYC-NNNN`, with no environment
prefix, compound command or redirection. When the host denies it, quote the denial and
hand the owner that one bare command, which carries no quote. A queued official item
(`queue add --release-list official`) whose instruction names the version is the owner's
go-ahead. A changed artifact, or a release not started from the queue, needs the owner's
new words through `--authorization`.

To rerun after a failure, set the failed step's task back to pending once the fix has
landed:

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact task CYC-0001 \
  --task-id verify --state pending --note 'fix 0123456789ab'
```

The writer reopens every later task, so the release resumes at that step. It records no
return, pass or new cycle. The note is optional and never validated; an interruption
rerun carries none.

A release record without `release_list` was created before the lists. It validates and
displays with its phases plan, release and reflect and a limit of 2. The writer allows
only `pause`, `reflect` and `abandon` on it.

## Prospective migration preparation

`adr-migration.py` prepares non-authoritative records. It does not activate
migrations or change any authority reader. The five `adr-migration-*.schema.json`
schemas define queues, exact packages, approvals, policy instructions and
publication candidates. Unknown formats refuse without historical fallback.
IDs are letter-led kebab-case slugs; writers use fixed migration subdirectories.
Bindings use repository-relative paths and SHA256. Council subjects remain
relative to the configured documentation root.

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/adr-migration.py" queue-create --repo-root . \
  --id authority-review --input queue-items.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/adr-migration.py" queue-resume --repo-root . \
  --path bionic/adrs/migrations/queues/authority-review.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/adr-migration.py" package --repo-root . \
  --path bionic/adrs/migrations/packages/authority-review.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/adr-migration.py" bundle --repo-root . \
  --path bionic/adrs/migrations/packages/authority-review.json
```

A package includes the exact human record, inline machine clause map, governing
ADR and acceptance receipt, objective and material dependencies, and owner stops.
Present the complete package bytes and bound content to council and owner. A TXT
approval alone cannot approve a subsequently authored map. The initial record's
identity comes from the governing ADR's explicit named record path and SHA256;
a partial identity match refuses. Only the acceptance receipt's verified
Proposed-to-Accepted lifecycle metadata bridge permits source-byte differences.
Semantic or dependency changes invalidate approval.

The disposition council has a distinct purpose and requires committed U1
readiness before requesting any provider. It supports standalone and cycle-owned
subjects. The selected Lite, Standard or Strict mode determines council approval.
Historical receipts retain their original provider and approval requirements.

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle-council.py" --repo-root . \
  --purpose disposition --subject adrs/migrations/packages/authority-review.json \
  --question disposition-question.txt --readiness u1-readiness.json
uv run "${CRUX_PLUGIN_ROOT}/scripts/adr-migration.py" approve --repo-root . \
  --id authority-review --package bionic/adrs/migrations/packages/authority-review.json \
  --council bionic/adrs/councils/council-ID.json --readiness u1-readiness.json \
  --owner owner-instruction.json
```

Readiness has `commit` (full Git SHA), `sources` and `tests` (binding lists), and
`review` (one binding). These files must already exist at that commit. Each test
summary carries `result: passed`, its `command` array and exact source `inputs`.
The review summary carries `verdict: approve`, `reviewer`, `implementers` and
source `inputs`; its reviewer must be independent. A mutable test-evidence ID
alone is insufficient. Validation proves the readiness commit precedes the
commits introducing the council and approval records.

Owner evidence has `origin: owner-conversation`, verbatim `quote`, `action:
approve-dispositions`, `at`, `conversation` provenance, and `presented` package
path/SHA256. Its date may precede or follow tooling or council. Identity is not
verified. An ADR-only acceptance, repository quotation, council verdict or silence
never supplies owner approval. Initial bootstrap dispositions need owner approval
under both policies. Later dispositions follow the policy already in force before
the approval commit. `policy --id ID --policy VALUE --owner instruction.json`
records an explicit owner configuration instruction with action `change-policy`;
it cannot weaken its own pending action. A policy edit in an approval commit
cannot authorize that approval.

Commit the approval receipt before using `candidate --id ID --package PATH
--approval PATH`. `approval --path PATH` validates committed evidence; `--pending`
checks a not-yet-committed receipt and grants no authority. `candidate-show --path
PATH` revalidates its exact approval. Candidates carry `authority: none` and live
under `adrs/migrations/candidates/`, outside publication discovery. Queue resume
preserves evidence and revisions while invalidating changed inputs and dependents.
Outstanding owner stops block affected packages under either policy; only an
explicit owner `clear-stop` instruction clears one, and clearance approves no
disposition.

The package's `governing_adr.receipt` is its canonical repository-relative receipt
path. The receipt can be created after an owner's instruction; the immutable
package binds the reviewed ADR source, without requiring a future receipt hash.
Council records and disposition approvals additionally bind `review_bundle_sha256`
to the actual source and receipt proof presented. Altered proof bytes invalidate
that council evidence. An explicitly combined owner instruction uses action
`accept-adr-and-approve-dispositions`; `package_owner_instructions` preserves its
provenance in separate acceptance and disposition actions.

For later migrations in consuming projects, `installed-support` emits
`crux.adr-migration-installed-support.v1` with the installed plugin's exact
module, CLI and schema bindings. It requires no vendored Crux source or upstream
commit ancestry. The initial bootstrap always refuses this alternative and
requires committed independent verification. Both council and approval bind the
applicable support basis.

`queue-stop --path PATH --input stop.json` records an explicit stop.
`queue-clear-stop --path PATH --id STOP --owner instruction.json` records its
explicit clearance. Resume keeps affected items and dependents blocked while
an unresolved stop exists. Clearance returns them to pending assessment, never
approval, and preserves the stop and its provenance.

`accept-package --package PATH --council ADR-COUNCIL --owner instruction.json`
accepts a new Proposed ADR under the policy committed before the action.
An explicitly selected council-only policy needs no owner instruction for that
ADR acceptance. The initial disposition still needs its separate owner scope.
Package acceptance receipts bind the package and policy basis, and preserve owner
provenance when required. `package-acceptance --package PATH` validates that receipt
against its introducing commit's first parent; `--pending` validates before commit.
Ordinary historical ADR acceptance receipts retain their original interpretation.

## Wait for a delegated result

`await CYC-ID --task-id ID [--task-id ID ...] --timeout SECONDS` waits for the
recorded `result_path` of any named task. `await --path ABS [--path ABS ...] --timeout
SECONDS` waits for exact absolute result paths instead. The path form reads no cycle,
so it serves a dispatch with no recorded task, such as an architect IDR, council or
plan-writing dispatch, and bookkeeping after the cycle closes. It takes no cycle id
and no `--task-id`. A path arrives when it is a non-empty
regular file whose size is unchanged after a one-second settle check. The first
path to arrive wins. The command writes nothing and takes no lock. It waits on a
timed event, not `sleep`, so a host can run it as a background command and resume
the caller when it exits.

With `--marker ASSIGNMENT/ATTEMPT` the path form returns when the file's last
non-blank line is `Result-End: <assignment>/<attempt>`, with no settle interval. A
symlink never arrives. Wait that way for a typed attempt: every host adapter's wait uses
the marker form, in windows of 30 minutes. A blocking mode performs its dispatch call once;
`inspect` re-offers only this marker await. Claude Code `background` attempts recorded before
the `blocking` mode, and already bound, leave the lost route only through the owner's
statement, because no task notification reports a terminal status for them (a complete
result still delivers).

It prints one JSON line with `ok`, `cycle`, `arrived`, `task`, `result_path` and
`waited_seconds`, with or without `--compact`. The path form prints `cycle` and
`task` as null. Exit 0 means a result arrived. Exit 1
with `ok: true, arrived: false` means the timeout elapsed. Exit 1 with `ok: false`
refuses an unknown task, a task with no recorded `result_path`, a relative `--path`,
a cycle id or `--task-id` combined with `--path`, a missing form, or a timeout at or
below 0 or above 3600. A file that arrived proves neither that the agent is alive
nor that its work is complete: read and validate the report.

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact await CYC-0001 --task-id build-parser --timeout 1800
# A dispatch with no task, or bookkeeping after closure:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact await --path /abs/os-temp/crux-results-CYC-0001-RANDOM/architect-idr-attempt-1.md --timeout 1800
```

## Queue commands

The queue is `<docs_dir>/queue/cycles.yaml`. Every op is
`cycle.py [--repo-root R] [--compact] queue <op>`; `--compact` prints one JSON line,
otherwise the JSON is indented. All inputs are flags, so no `--file` is needed. Pass
free-text values single-quoted, with an embedded single quote written as `'\''`. Repeat
`--scope`, `--acceptance`, `--depends-on` and `--reference` for several values.

| Command | Effect |
|---|---|
| `queue add --title T --outcome O --type TYPE --scope P --acceptance A [--depends-on Q] [--reference PATH] [--position N] [--held --reason TEXT] [--release-list beta\|official]` | Appends an item (or inserts at `--position`). The outcome becomes the cycle goal. `--release-list` belongs to a release item: `beta`, the default, starts a beta-list cycle and `official` an official-list cycle. |
| `queue list [--full]` | One line per open item, the count of closed items, a one-line authorization summary and the head item with its stop reason. `--full` prints every item with position, id, title, state, derived cycle status, dependencies with satisfied flags, cycle and `in_scope`, plus the authorization history. |
| `queue show Q` | One active or archived item. |
| `queue archive [--dry-run] [--migrate]` | Preview terminal items or archive them; `--migrate` explicitly converts format 1 to format 2. |
| `queue edit Q [--title] [--outcome] [--type] [--scope] [--acceptance] [--depends-on \| --no-depends] [--reference \| --no-references]` | Replaces the named fields of a pending or held item. |
| `queue move Q --position N` | Moves an unstarted item to a 1-based position. |
| `queue hold Q --reason TEXT`, `queue unhold Q` | Holds or releases an unstarted item. |
| `queue remove Q` | Removes a pending or held item that no other item depends on. |
| `queue authorize --kind next\|next-n\|queue [--count N] --instruction TEXT --date YYYY-MM-DD` | Records the one authorization. The instruction is the owner's own message, verbatim. A new authorize replaces the current one. |
| `queue revoke --reason TEXT` | Ends the authorization. It stops further starts only. |
| `queue start-next [--implementer NAME] [--coordinator NAME]` | Starts the head item as a cycle, or reports why it cannot. Both names default to `dev-lead`. |

Every mutating op except `start-next` commits its touched active/history paths together with
`git commit --only` and returns the result as `queue_commit`. The commit defers with a
reason, and the queue change stays saved, while a full suite runs, during a merge or
rebase, under an index lock or outside a repository. `start-next` owns the joint queue/new-cycle commit under the queue lock. `add`, `edit` and
`start-next` split each `--scope` value on commas, so `'a, b'` names two paths; a stored
comma-joined value is split when its cycle starts.

A reference is a repository path to a supporting document, such as a brief. `queue add`
and `queue edit` refuse a reference that does not exist or resolves outside the
repository; `queue list` and `queue show` display the list. `queue start-next` appends
the references to the created cycle's goal under `References (read before planning;
read-only, not scope):`, so Plan reads them first. References are read, not edited:
they never enter plan scope or the review scope comparison.

Authorization starts cycles only. It never authorizes push or another outward action,
never extends a pass limit and never approves an IDR or ADR. The one exception is a
release item: authorizing it also authorizes publishing that item's version to its
target (see Release cycles). `next`
captures the first unstarted item, `next-n` the first N, `queue` every unstarted item.
It captures ids, not content. An item added later is outside the scope.

`queue start-next` exits 0 with one outcome: `started` (a new cycle exists), `adopted`
(an interrupted start was completed; it reports the cycle and its status) or
`in-progress` (a started item's cycle is active or paused; nothing was allocated).
Act on an outcome by its cycle status: active, drive the cycle to completion; paused,
stop at its pause and report; completed or abandoned, run `queue start-next` again.

It exits 1 with `{ok: false, stop: {reason, item, detail}}` and one reason, checked in
this order: `cycle-missing` (a started item's cycle record is absent or unreadable;
restore it), `queue-empty`, `not-authorized`, `previous-abandoned` (checked before
`authorization-exhausted`; the owner re-authorizes to continue),
`authorization-exhausted`, `outside-authorization`, `held` (the head is never skipped),
`blocked` or `dependency-abandoned` (a dependency is satisfied only when started and
completed; an abandoned one needs an owner decision), and `type-unsupported` (the type
is not a cycle type). Exit 1 also reports a refusal as `{ok: false, error}`, including an
invalid queue file with its path, the failing location and the repair. Exit 2 reports an
environment problem as `{ok: false, error}`: unresolved configuration, a missing tree, an
unreadable or unlockable queue path, or PyYAML unavailable.

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

Format 1 retains its historical lifetime cap; format 2 caps active entries. `start-next` considers
only queue-started cycles. Each started cycle keeps its own type, pass limit and stops.

## Configured council commands

`cycle-council.py` preserves historical receipts and adds mode-aware execution.
Read its `--help` and the `council` skill. Configuration uses `council.mode`, optional
`council.overrides.{adr,idr,migration}`, and `council.max_attempts` (1 through 7).
Missing legacy mode remains Strict. Setup records an explicit Standard/Lite choice.

- `--identity`: stable consultation or creation identity across subject renames.
- `--architect PATH --record <council>`: exact-final agreement and typed dissent, read
  from the JSON file PATH. A result whose votes suffice and that lacks only this
  agreement reports `outcome: awaiting-architect` and `next_command`, the exact command
  with PATH left for the architect; the exit code stays 1 and the sealed record keeps
  `changes-required`.
  When `agrees` is true the JSON names every nit as `nits: [{id, disposition, note}]`,
  with `disposition` `apply-in-build` or `declined` (a declined nit carries its reason).
- `--prepare-pass challenge|final`: sealed native request; the host dispatches it.
- `--ingest-result <host JSON> --request <request>`: validate and retain actual host evidence.
- `--recover <attempt>`: persist an original result without making a request.
- `--record-policy <slug> --owner-instruction <path>`: retain an explicit owner mode instruction.
- `--policy-action extend-council-limit --extension <limit> --identity <logical id>`:
  record an extension the owner gave on their own initiative, rather than resetting the
  decision count. No agent requests one; at the limit the architect withdraws or narrows.

`--initialize-council standard|lite|strict --selection <explicit choice>` is for
first Crux enrollment. It preserves unrelated configuration and records provenance.
It cannot reset an existing project policy. Read `council/references/native-lite.md`
for exact Codex and Claude host contracts. Native contexts are council evidence
only through the owning writer; independent implementation review stays separate.
