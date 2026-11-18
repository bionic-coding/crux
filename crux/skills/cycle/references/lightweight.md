# Cycle workflow reference

This is the reference for the ordinary cycle: the record, the writer commands, review,
completion, delivery facts, reopening, the queue start and recovery. The cycle skill
states the workflow; this page states the record details. `cycle.py` implements the
writer in `cycle_writer.py`. `cycle.py pilot SUB` is an alias of `SUB`.

Historical cycle records are read-only through the history reader; nothing resumes or
rewrites them.

## Commands and files

Prepare a plan definition, not a complete stored record. For example:

```json
{
  "goal": "Handle empty parser input",
  "scope": ["src/parser.py", "tests/test_parser.py"],
  "acceptance": ["Empty input returns the documented result"],
  "verification": {
    "checks": [{"id": "parser", "rationale": "Changed behavior and existing callers"}],
    "gaps": "Packaging is unchanged; broader integration remains covered by PR CI"
  },
  "council": {"needed": false, "reason": "Bounded correction within the agreed behavior"},
  "tasks": [{"id": "parser", "description": "Fix parsing and verify callers"}]
}
```

Save the definition as `/tmp/plan.json`, then create the cycle:

```bash
uv run /abs/plugin-root/scripts/cycle.py create --title 'Bounded change' --lead session-a --plan /tmp/plan.json
uv run /abs/plugin-root/scripts/cycle.py show CYC-0123
```

With `--goal`, `--scope` and `--acceptance` (the last two repeat) instead of `--plan`, the
lead records the rest with `plan`. Every new cycle except a release record starts in
`planning`, a full `--plan` included. It leaves `planning` at its first task write: a
`task`, or a `batch` with a task entry. That write needs verification, a council decision
and at least one task in the plan. A `check` write leaves the state as it is. A plan revision returns the cycle to `planning` until the
next task write. The plan may also carry `scrutiny`, a level and a reason.

A change to acceptance takes effect only with the owner's recorded words.[^acceptance] A
change to scope does too, except that the lead may add each path that a blocking
finding, recorded by the cycle's requested independent reviewer, names as the place to
fix an unmet acceptance criterion of the current plan.[^scope] Name the containing
directory in `scope` when the file list may be incomplete.

Without `--owner-approval`, `plan` admits a scope difference only through
`--finding TASK --criterion N`. `TASK` is the id of the task the finding became, such as
`review-4-1`; the review stores these ids in finding order as `finding_tasks`. `N` is a
zero-based criterion of the current plan. The writer refuses the revision unless all of
these hold:

- the finding is a blocking finding of a review recorded for this cycle by its requested
  reviewer, who is still independent of the lead and the implementers;
- every added path appears in that finding, and the recorded scope entries stay in place
  and in order;
- acceptance is unchanged.

A finding names a path when the exact path occurs in its text, or in a string value of a
structured finding, bounded on each side by a character that cannot continue a path. A
longer path, a prefix of one or a directory above the path does not count; a full stop
that ends a sentence still bounds it. An advisory finding, a lead's note, a task summary
and a check observation are no finding. The plan history entry records the finding, its
reviewer and text, the criterion and the added paths. The revision returns the cycle to
`planning` and makes the earlier review obsolete. The next review judges whether the
finding named each added path as the place to fix and whether the named criterion
requires the fix; the writer judges neither.

Creation uses the allocator and stores `format: crux.cycle.v1` at
`<docs_dir>/cycles/<CYC-ID>/cycle.json`. Records of format `crux.cycle.vNext` stay
readable. Allocate before branching and never copy an existing ID into another cycle.
Create a follow-up with `create --follows CYC-ID`. A release record uses
`create --release-list beta|official --version X.Y.Z` and is described in the cycle skill.

After creation, every mutation requires `--actor ACTOR --expect-revision N`. The actor is
the lead for every command except `review`, where it is the requested reviewer. Read the
current revision with `show`; a stale write requires reading and reconciling current
state before retrying. Actor identity is an ownership declaration for cooperating
agents, not authentication against arbitrary filesystem writers.

```bash
uv run /abs/plugin-root/scripts/cycle.py task CYC-0123 --actor session-a --expect-revision 1 --task parser --owner session-a --run 1 --status working --checkout /abs/checkout
uv run /abs/plugin-root/scripts/cycle.py check CYC-0123 --actor session-a --expect-revision 2 --file /tmp/check.json
```

The revision numbers illustrate successive writes; use the actual current revision.
A task whose work is already observed needs no `working` write: record `--status done`
(or `blocked`) with `--run` one above the task's current run, the owner and a summary.
A refusal that starts `late or mismatched result` names a superseded or reassigned run;
one that starts `invalid transition` names a result the task's status cannot take.

Record several milestones in one write with `batch ID --file /tmp/batch.json`:

```json
{
  "tasks": [{"task": "parser", "owner": "session-a", "run": 1, "status": "done", "summary": "Parsing fixed"}],
  "checks": [{"check_id": "parser", "executed_command": "python3 -m unittest tests.test_parser",
              "tested_revision": "ACTUAL_COMMIT", "result": "passed",
              "summary": "Empty-input and caller cases pass", "reason": "Changed parsing behavior"}]
}
```

A batch applies its tasks, then its checks, under one expected revision. The writer
validates every entry first; one refused entry leaves the record unchanged. Each entry
takes the keys and the rules of the single `task` and `check` commands.
Run `cycle.py SUBCOMMAND --help` for flags. The stored record schema is
`crux/schemas/cycle-record.schema.json`; command inputs omit writer-owned fields.
Use `show ID --full` to retrieve the complete record.

For `/tmp/check.json`, record an actual result with these input keys:

```json
{
  "check_id": "parser",
  "executed_command": "python3 -m unittest tests.test_parser",
  "tested_revision": "ACTUAL_COMMIT",
  "result": "passed",
  "summary": "Empty-input and caller cases pass",
  "reason": "Changed parsing behavior and related callers"
}
```

Run the check in the project's selected environment with its interpreter and dependencies.
Replace the command, result and revision with observed facts. To reuse a passing
observation, supply `check_id`, `reuse` (its `LC-...` ID), `summary` and `reason`.
Omit `executed_command`, `tested_revision` and `result`; their original values remain.
Reassess applicability after a plan change before explicitly reusing older results.
A later failed result prevents reuse of an earlier pass.

An observation counts only for the plan revision it was recorded under, so a plan
revision makes every selected check read `missing`. One `batch` of `reuse` entries
re-records the passing observations that still apply. A rerun with a narrower command
takes its own check id, or the plan's rationale for that check states the narrower
command.

Review input requires `reviewer`, `plan_revision`, `base_commit`, `head_commit`,
`verdict`, `blocking`, `acceptance`, `test_selection` and `summary`. Use verdict
`approve` or `changes-required`. Each acceptance entry contains a zero-based
`criterion`, Boolean `met`, and nonempty `evidence`. The reviewer names the original
cycle base and the committed head it assessed. Commit source edits before requesting
review; uncommitted source cannot be bound to that range.

The lead requests review with `review-start ID --reviewer NAME`. The named reviewer
submits its own report: `review ID --actor NAME --expect-revision N --file FILE`,
after reading the revision with `show`. The writer refuses the lead as review
actor, a reviewer other than the requested one, and a reviewer who led or implemented.
It refuses a stale report: one that names a superseded plan revision, or one the
reviewed-path rule below makes obsolete before it is recorded. It also refuses a head
that lacks the code committed when review was requested. Bookkeeping is the cycle
records, council records, journal, operations log and queue under the documentation
tree. `test_selection` explains coverage
and applicability. `blocking` lists unresolved findings. Optional fields are
`advisory`, `lessons` and `remaining`.

| Command | Purpose |
| --- | --- |
| `create --title T --lead L (--plan FILE \| --goal G --scope S --acceptance A)` | Allocate a cycle. `--follows CYC` links a follow-up; `--release-list` starts a release record. |
| `plan ID --file FILE --reason TEXT` | Revise the plan. An acceptance change needs the owner's actual words through `--owner-approval`; so does a scope change, except a path added with `--finding TASK --criterion N` as stated above. A revision returns the cycle to `planning` and moves an open review request into its history entry; request review again afterwards. On a paused cycle it records the change and keeps the pause and its blocker. |
| `task ID --task TASK --owner OWNER --run N --status STATUS` | Record assignment or progress with the current owner and run. Statuses are `working`, `blocked` and `done`. Supply checkout and outcome where relevant. A result needs `--summary`. A pending task can record `done` directly; `--checkout` names the linked worktree that holds its work. |
| `batch ID --file FILE` | Record several task updates and check observations as one validated write. |
| `check ID --file FILE` | Record a compact observation: check ID, actual command, result, summary, tested revision and rationale. This command records rather than executes. |
| `review-start ID --reviewer NAME` | The lead requests review from one named independent reviewer, after committing the final code and recording the selected checks. |
| `review ID --actor NAME --file FILE` | The requested reviewer records its own report: plan revision, code base and head, coverage assessment, acceptance outcomes and findings. A passing review establishes `reviewed`. |
| `finish ID [--summary TEXT]` | Complete the cycle once its work, selected checks and independent review are done. It needs no PR, CI, merge or branch. A repeat changes nothing. |
| `delivery ID --file FILE` | Record observed `pr`, `ci`, `merge`, `commit` and `published` facts. They never complete or reopen a cycle. |
| `recover ID` | Reconcile this cycle's checkout claims with its record after an interrupted write. It changes nothing else and is safe to repeat. |
| `reopen ID --reason TEXT --owner-instruction TEXT --file TASKS` | Reopen a completed cycle for a related repair, on the owner's actual instruction. `TASKS` is a JSON list of repair task definitions. |
| `pause ID --reason TEXT`, `resume ID --reason TEXT --reconcile TEXT`, `abandon ID --reason TEXT` | Record a stop, a reconciled continuation, or abandonment. A paused cycle leaves its pause only through `resume`, which returns it to the state it paused from, or to `planning` after a plan revision. While paused it refuses a new task run and accepts a running task's result. |
| `council-subject ID` | Freeze the plan subject and return its path, identity and invocation guidance; this does not convene council. |
| `council ID --record PATH --response TEXT` | Record an approved council result for the exact plan and the response to its findings. |
| `status [ID]` | Show progress; read-only. It also shows historical records. |

The lead performs every write except the review verdict, which the requested reviewer
submits itself. Workers return native results to the lead. The lead still requests
review and addresses its findings. When the host denies the reviewer's write, keep the
exact denial and report it; the lead never submits the verdict in the reviewer's place.
For an actual council, use the returned subject and identity with the configured
runner: `cycle-council.py --purpose consultation --subject SUBJECT --identity IDENTITY --question QUESTION_FILE`.
The question file contains the lead's unresolved questions for the exact approach.
Follow its configured council instructions and returned continuation commands.
Never invent provider verdicts or rerun an uncertain external action merely because
a session resumed.

## Plan, work, review

One lead records the outcome, scope, acceptance criteria, intended checks, tasks,
dependencies and owners. The owner's request can authorize implementation within
those boundaries. A small fix can have one task; planning need not dispatch another
role when the lead has enough context.

Record whether council is needed and one sentence explaining why. Use council when
requested by the owner, consequential tradeoffs need resolution, uncertainty prevents
a defensible plan, or a durable constraint changes.[^council] Council considers the exact
plan revision. Preserve its verdict and responses to substantive findings. A pending
council-required choice blocks dependent tasks, not unrelated work.

The lead implements directly or delegates through native host tools. Tasks move
through `pending`, `working`, `blocked` and `done`. Record ownership changes,
completion, blockers and material plan changes. Do not retain every tool call,
prompt copy or delivery report. Status shows completed and total tasks and named
blockers; that ratio is not an estimate of effort.

Run focused checks for changed and related behavior, then select final checks by
scope and risk, including the drift gates the change touches and, where the project
labels tests, the tier check when a test or tier manifest changes.[^checks] Record
compact commands, results, tested revision, coverage rationale and known gaps. Fix
failures and rerun affected checks. State changes alone never require tests to repeat.
The lead reassesses applicability after edits; independent review checks the selection
and applicability to the final change.

An independent reviewer assesses acceptance, code diff, integration and testing.
A blocking finding or a known acceptance failure becomes a task in the same cycle.[^findings]
The reviewer revisits the changed portions and consequences; no counted return applies.
`reviewed` requires passing selected checks, no unresolved blocking findings, and
satisfied acceptance criteria. Only the owner can change or defer acceptance; record
remaining work explicitly.

Progress states are `planning`, `working`, `reviewing`, `reviewed` and `completed`.
`paused` and `abandoned` are separate outcomes. `reviewed` means an approving review is
recorded and the cycle awaits `finish`.

## Finish, delivery and reopening

A cycle wraps up when its agreed work is finished, its selected checks pass and the
independent review approves the final change. The lead then runs `finish`. It
requires every implementation task done, every selected check passing, an approving
review of the current plan revision with every acceptance criterion met, no blocking
finding, and a review that still covers the final change. It requires no PR, merge,
branch ancestry or integration event. Do not leave a finished cycle open to wait for one.

The review covers the final change while every reviewed path holds, in the checkout, the
content it had at the reviewed head. This one reviewed-path rule governs both the
`review` write, which refuses a report it already makes obsolete, and `finish`. The
reviewed paths are the code paths that differ between the cycle base and the reviewed
head. Committed and uncommitted changes to them both count, so finish before the next
cycle edits the same files. Other paths do not count: commits elsewhere on a shared
branch are other work, so a later cycle's commits on other paths refuse no review. This
is a content comparison of paths. It does not detect a later change of the same cycle
that touches only new paths, and it does not prove that other work left the reviewed
code's behavior unchanged. The reviewed range runs from the cycle base to the reviewed
head, so it also holds other cycles' commits made after this cycle's base. The `review`
write also refuses a head that lacks the code committed when review was requested, so
`review-start` refuses while finished work recorded in another checkout is missing from
HEAD: integrate it first. A task marked done from a linked worktree records that
worktree's HEAD commit on its attempt, and `review-start` refuses while HEAD lacks that
commit, even after the worktree is removed; a record without a captured commit skips a
checkout that no longer exists. A pending or blocked task completed directly with
`--checkout` naming a linked worktree records that worktree and its commit the same way.

A squash merge or cherry-pick integrates the work under new commit IDs, so HEAD never
contains the recorded commit and `review-start` keeps refusing. The ancestry check stays;
the refusal names the route. First verify that HEAD holds the change:
`git diff COMMIT HEAD` on the task's paths shows only work committed after the squash.
Then reassign the task in the review checkout at the next run,
`task ID --task TASK --owner OWNER --run N --status working`, and record completion
there with `--status done` at the same run. That attempt ran in the review checkout, so
`review-start` judges it and admits the review.

The writer and `review-start` read a checkout's HEAD only when Git names that directory
as its own worktree root. A nested worktree that lost its `.git` link is refused; run
`git worktree repair PATH` from the main checkout to restore the link. Git 2.54 restores
the link but still prints `error: unable to locate repository; .git file broken` and exits
1. Verify the repair instead of trusting that exit status:
`git -C PATH rev-parse --show-toplevel` prints PATH itself, and a second
`git worktree repair PATH` exits 0 with no output. A lead commit to new paths after `review-start`,
with no recorded task work, passes admission as it passes `finish`. When
implementation work was recorded after the request, it refuses a report after which any
code changed. An implementation task added or run again after the approval also makes
the review obsolete. `show`, `queue show`, `queue list --full` and the
dashboard report four separate facts from this same rule: the recorded review, whether
it still covers the final change, whether the cycle completed, and the delivery facts.
The short `queue list` line carries the status alone.

`completed` is the cycle's own outcome. PR URL, CI result, merge status and publication
are delivery facts, recorded with `delivery` at any time, before or after completion.[^delivery]
Completion claims none of them, and none of them completes a cycle. Later commits never
reopen a completed cycle or change its recorded review.

When PR CI fails or the delivered work shows a defect, record the fact. The cycle stays
as it is, and the writer prints the choice to offer the owner: reopen the cycle for the
related repair, or create a linked cycle with `create --follows CYC-ID` when the
repair deserves its own scope. Reopen only on the owner's instruction, quoted in
`--owner-instruction`.[^reopen] Reopening keeps the earlier completion, checks and review
in the record, adds the repair tasks and returns the cycle to `working`. It completes again
after the repair tasks, their checks and a review recorded after the reopening. Checks
that the repair does not affect are not rerun. An abandoned cycle, a historical shortcut
cycle and a completed release record never restart; follow-up work is a new cycle.[^restart]

## Record and recovery

Only the lead changes the structured record through the writer, except for the
requested reviewer's own report. The writer validates shape, writes atomically and
refuses stale expected revisions. Save at milestones, then commit with ordinary work
checkpoints and at handoff or completion. The writer does not commit each operation.
A record commit message names the cycle and what the record gained, for example
`cycle: record CYC-0123 plan revision and checks`. A message that names only the cycle
tells a reader nothing the path does not. Commit nothing while a full suite runs,
because a commit moves HEAD under the running tests.
Directory loss can lose uncommitted progress; atomic writes prevent partial files,
not disk loss.

Allocate a distinct cycle ID through the allocator before branching. Duplicate IDs are
allocation errors. Concurrent cycles use separate checkouts and branches; separate
branches in one checkout do not isolate edits. Keep one editor per checkout and one
integration owner. A local ownership claim coordinates cooperating agents; it cannot
prevent arbitrary external edits.

Every reassignment increments the task's run number. A return from an earlier run
cannot complete its replacement. On resume inspect the record, Git status, diff and
actual host state. Reconcile unfinished work before restarting it. Record those
observations with `resume --reconcile`; a local ownership claim never expires
automatically. Host handles do not prove liveness. Preserve unknown edits and unknown
Git locks.

Review names the plan revision and code commit range. Source changes need an
independent assessment of the delta. Material scope, acceptance or council-choice
changes require reassessment of affected planning and review. Bookkeeping preserves
review. Use Git code identity, not a second source inventory. A task update during
review leaves the cycle state as it is. Unfinished implementation work, a plan
revision or a change to a reviewed path after the reviewed head makes the review
obsolete, and `finish` refuses it.

A task or batch write changes the record and the checkout claims as one unit under the
runtime lock. A refused or failed write restores the claims exactly as they stood, and
two tasks of one batch cannot claim one checkout. The record is the commit point. The
writer saves added claims before the record and drops released claims after it, so a
process killed during a write leaves at most a claim the record does not back, never a
working task without its claim. A claiming write (`task`, `batch`, `resume`, `finish`,
`abandon` or `recover`) removes such a leftover, and so does `recover ID`, which changes
nothing else and reports what it reconciled. Recovery removes only a claim that carries
this cycle's id and matches no working assignment in its record. It never removes
another owner's claim and never assumes an owner is dead from elapsed time.

Diagnose repeated failure without new evidence, or pause.[^stops] Do not add a
cycle-wide retry counter. Individual tools retain bounded retries for cost or external
effects. Pause for an unresolved blocker, an owner decision on scope or acceptance, a
failed premise, or an owner stop. Reconcile an uncertain external act, such as a council
request or a publication, before any retry.[^external]

## Queue item

`queue start-next` starts every non-release head item as a `crux.cycle.v1` record:

```bash
uv run /abs/plugin-root/scripts/cycle.py queue start-next --lead session-a --plan /tmp/start.json
```

The item supplies goal, scope and acceptance. The optional plan file holds any of
`verification`, `council`, `tasks` and `scrutiny`. A non-release cycle starts in
planning either way. Without the file it has no tasks, and the lead records the rest with `plan`, which keeps the
queued goal, scope and acceptance when the file omits them. The lead defaults to
`--implementer`. `--pilot` is accepted and changes nothing. The item's type is a recorded
label, and no classifier sizes the item. Authorization, dependency checks and
interrupted-start recovery apply as before, and a retry adopts the record already
created. A release item starts a release record.

When a cycle created outside the queue did a queued item's work, name the item id in
the cycle title or goal. After review, the lead associates the two through the queue writer:

```bash
uv run /abs/plugin-root/scripts/cycle.py queue reconcile Q-0042 --pilot CYC-0123 --actor session-a --file /tmp/assessment.json
```

The assessment states how the reviewed work met the queued request:

```json
{"outcome": "Evidence that the queued outcome holds",
 "acceptance": [{"criterion": 0, "evidence": "Evidence for the item's first acceptance criterion"}]}
```

The operation requires a pending item, a recorded approving review whose head HEAD
contains, and one evidence entry per queue acceptance criterion. The item becomes
started under the cycle's own id. The authorization, the other items and the allocator
are untouched. Repeating the command writes and commits nothing; repeating an
interrupted call finishes it. A queue binding has no effect on review status.

The queue follows cycle completion. It reports an item as running, `reviewed`
(awaiting finish) or `completed`. A reviewed item is open: it is not counted closed, it
satisfies no dependency, and it holds the queue as a running cycle does until the lead
finishes it. A completed cycle satisfies dependencies whatever its PR, CI or merge
status, and its item archives through `queue archive` or the next queue write once the
cycle record is committed. No item carries a merged-code dependency condition; when one
genuinely needs merged code, say so in the item's acceptance. Reopening a completed
cycle leaves an archived item archived, creates no second item and undoes no dependent
cycle already started; an item not yet archived shows the reopened cycle as running.
The queue writer commits the queue file; commit the cycle record with the next ordinary
checkpoint.

## Durable decisions and completion

Create an ADR only for a constraint future work must preserve, such as compatibility,
data policy or an architecture boundary. Routine implementation choices stay in the
plan. Keep the constraint, reason, alternatives and consequences concise. Propose it with
`decision-policy.py propose --origin cycle --cycle CYC-NNNN` while the cycle is planning,
working or reviewing; no council approves its creation.[^adr] Council approves the exact
draft, and a person accepts it unless `.bionic.yml` sets another acceptance policy. A
task that depends on the ADR names it in `adr_dependencies`, and the writer refuses
`working` or `done` for that task until the ADR is Accepted. An ADR that another cycle
or route proposed is found under `adrs/` by its id; its Accepted status counts only
with a valid acceptance receipt where its `acceptance_format` requires one. An `acceptance_format`
the writer does not know satisfies no dependency. Plan approval is not ADR
acceptance or external-action authorization.

Record the outcome in review JSON: `summary` for the delivered outcome and consequential
choices, with optional `lessons` and `remaining` lists. `finish --summary` replaces the
summary when a shorter completion statement serves better.[^summary] There is no
mandatory reflection step or empty lessons section. Retain plan revisions, council
conclusions, test summaries and final review. Keep temporary logs or host details only
when they explain unresolved problems.

[^acceptance]: rule:acceptance-changes-only-with-the-owner
[^adr]: rule:cycle-adrs-need-no-creation-council
[^checks]: rule:checks-follow-scope-and-risk
[^council]: rule:council-reviews-consequential-plan-choices
[^delivery]: rule:delivery-facts-never-complete-a-cycle
[^external]: rule:uncertain-external-effects-are-reconciled-first
[^findings]: rule:findings-become-cycle-tasks
[^reopen]: rule:completed-cycle-reopens-only-on-owner-instruction
[^restart]: rule:abandoned-cycles-never-restart
[^scope]: rule:scope-changes-with-the-owner-or-a-review-finding
[^stops]: rule:named-stops-pause-any-cycle
[^summary]: rule:closure-records-a-summary
