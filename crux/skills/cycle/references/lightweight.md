# Lightweight cycle pilot

This path is opt-in. Use it only when the owner explicitly requests the pilot;
ordinary cycles, releases and historical records keep their existing workflows.
It introduces no service, bulk migration or automatic default rollout.

## Commands and files

Prepare a plan definition, not a complete stored cycle record. For example:

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

Save the definition as `/tmp/plan.json`, then create the pilot explicitly:

```bash
uv run /abs/plugin-root/scripts/cycle.py pilot create --title 'Bounded change' --lead session-a --plan /tmp/plan.json
uv run /abs/plugin-root/scripts/cycle.py pilot show CYC-0123
```

Creation uses the existing allocator and stores `format: crux.cycle.vNext` at
`<docs_dir>/cycles/<CYC-ID>/cycle.json`. Allocate before branching. Do not copy an
existing ID into another pilot. The queue keeps its existing route; this pilot
command is a separate opt-in entry, not a queue-wide policy switch.

After creation, mutations require `--actor ACTOR --expect-revision N`. The actor is the
lead for every command except `review`, where it is the requested reviewer. Read the
current revision with `pilot show`; a stale write requires reading and reconciling
current state before retrying. Actor identity is an ownership declaration for
cooperating agents, not authentication against arbitrary filesystem writers.

```bash
uv run /abs/plugin-root/scripts/cycle.py pilot task CYC-0123 --actor session-a --expect-revision 1 --task parser --owner session-a --run 1 --status working --checkout /abs/checkout
uv run /abs/plugin-root/scripts/cycle.py pilot check CYC-0123 --actor session-a --expect-revision 2 --file /tmp/check.json
```

The revision numbers illustrate successive writes; use the actual current revision.
A task whose work is already observed needs no `working` write: record `--status done`
(or `blocked`) with `--run` one above the task's current run, the owner and a summary.
A refusal that starts `late or mismatched result` names a superseded or reassigned run;
one that starts `invalid transition` names a result the task's status cannot take.

Record several milestones in one write with `pilot batch ID --file /tmp/batch.json`:

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
Consult `cycle.py pilot SUBCOMMAND --help` for flags. The stored record schema is
`crux/schemas/cycle-pilot.schema.json`; command inputs omit writer-owned fields.
Use `pilot show ID --full` to retrieve the complete record. Do not pass a legacy
cycle plan or TE receipt as a pilot observation.

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

Run the example check in the project's selected environment with its interpreter and dependencies.
Replace the command, result and revision with observed facts. To reuse a passing
observation, supply `check_id`, `reuse` (its `LC-...` ID), `summary` and `reason`.
Omit `executed_command`, `tested_revision` and `result`; their original values remain.
Reassess applicability after a plan change before explicitly reusing older results.
A later failed result prevents reuse of an earlier pass.

Review input requires `reviewer`, `plan_revision`, `base_commit`, `head_commit`,
`verdict`, `blocking`, `acceptance`, `test_selection` and `summary`. Use verdict
`approve` or `changes-required`. Each acceptance entry contains a zero-based
`criterion`, Boolean `met`, and nonempty `evidence`. The reviewer names the original
cycle base and the committed head it assessed. Commit source edits before requesting
review; uncommitted source cannot be bound to that range.

The lead requests review with `review-start ID --reviewer NAME`. The named reviewer
submits its own report: `pilot review ID --actor NAME --expect-revision N --file FILE`,
after reading the revision with `pilot show`. The writer refuses the lead as review
actor, a reviewer other than the requested one, and a reviewer who led or implemented.
It refuses a stale report: one that names a superseded plan revision, or a head after
which code changed. Commits that change only bookkeeping after the reviewed head keep
the report valid. Bookkeeping is the cycle records, council records, journal,
operations log and queue under the documentation tree. `test_selection` explains coverage
and applicability. `blocking` lists unresolved findings. Optional fields are
`advisory`, `lessons` and `remaining`.

| Command after `pilot` | Purpose |
| --- | --- |
| `plan ID --file FILE --reason TEXT` | Revise the plan; scope or acceptance changes require actual owner words through `--owner-approval`. |
| `task ID --task TASK --owner OWNER --run N --status STATUS` | Record assignment or progress with the current owner/run. Supply checkout and outcome where relevant. A result needs `--summary`. A pending task can record `done` directly. |
| `batch ID --file FILE` | Record several task updates and check observations as one validated write. |
| `check ID --file FILE` | Record a compact observation: check ID, actual command, result, summary, tested revision and rationale. This command records rather than executes. |
| `review-start ID --reviewer NAME` | The lead requests review from one named independent reviewer, after committing the final code and recording the selected checks. |
| `review ID --actor NAME --file FILE` | The requested reviewer records its own report: plan revision, code base/head, coverage assessment, acceptance outcomes and findings. A passing review establishes `reviewed`. |
| `finish ID [--summary TEXT]` | Complete the cycle once its work, selected checks and independent review are done. It needs no PR, CI, merge or branch. A repeat changes nothing. |
| `delivery ID --file FILE` | Record observed `pr`, `ci`, `merge`, `commit` and `published` facts. They never complete or reopen a cycle. |
| `recover ID` | Reconcile this pilot's checkout claims with its record after an interrupted write. It changes nothing else and is safe to repeat. |
| `reopen ID --reason TEXT --owner-instruction TEXT --file TASKS` | Reopen a completed cycle for a related repair, on the owner's actual instruction. `TASKS` is a JSON list of repair task definitions. |
| `pause ID --reason TEXT`, `resume ID --reason TEXT --reconcile TEXT`, `abandon ID --reason TEXT` | Record a stop, reconciled continuation, or abandonment. |
| `council-subject ID` | Freeze the plan subject and return its path, identity and invocation guidance; this does not convene council. |
| `council ID --record PATH --response TEXT` | Record an approved council result for the exact plan and the response to its findings. |

The lead performs every write except the review verdict, which the requested reviewer
submits itself. Workers return native results to the lead. The lead still requests
review and addresses its findings. When the host denies the reviewer's write, keep the
exact denial and report it; the lead never submits the verdict in the reviewer's place.
These commands do not require typed `prepare-dispatch`, `attach-execution`,
`execution-check`, marked result files, or an operation for every host interaction.
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
a defensible plan, or a durable constraint changes. Council considers the exact plan
revision. Preserve its verdict and responses to substantive findings. A pending
council-required choice blocks dependent tasks, not unrelated work.

The lead implements directly or delegates through native host tools. Tasks move
through `pending`, `working`, `blocked` and `done`. Record ownership changes,
completion, blockers and material plan changes. Do not retain every tool call,
prompt copy or delivery report. Status shows completed/total tasks and named blockers;
that ratio is not an estimate of effort.

Run focused checks for changed and related behavior, then select pre-PR checks by
scope and risk. Record compact commands, results, tested revision, coverage rationale
and known gaps. Fix failures and rerun affected checks. State changes alone never
require tests to repeat. The lead reassesses applicability after edits; independent
review checks the selection and applicability to the final change.

An independent reviewer assesses acceptance, code diff, integration and testing.
Findings become tasks. Fix them within the authorized scope; the reviewer revisits
the changed portions and consequences without a counted phase return. `reviewed`
requires passing selected checks, no unresolved blocking findings, and satisfied
acceptance criteria. Only the owner can change or defer acceptance; record remaining
work explicitly.

Progress states are `planning`, `working`, `reviewing`, `reviewed` and `completed`.
`paused` and `abandoned` are separate outcomes. `reviewed` means an approving review is
recorded and the cycle awaits `finish`.

## Finish, delivery and reopening

A cycle wraps up when its agreed work is finished, its selected checks pass and the
independent review approves the final change. The lead then runs `pilot finish`. It
requires every implementation task done, every selected check passing, an approving
review of the current plan revision with every acceptance criterion met, no blocking
finding, and a review that still covers the final change. It requires no PR, merge,
branch ancestry or integration event. Do not leave a finished cycle open to wait for one.

The review covers the final change while every reviewed path holds, in the checkout, the
content it had at the reviewed head. The reviewed paths are the code paths that differ
between the cycle base and the reviewed head. Committed and uncommitted changes to them
both count, so finish before the next cycle edits the same files. Other paths do not
count: commits elsewhere on a shared branch are other work. This is a content
comparison of paths. It does not detect a later change of the same cycle that touches
only new paths, and it does not prove that other work left the reviewed code's
behavior unchanged. An implementation task added or run again after the approval also
makes the review obsolete. `pilot show`, `queue show`, `queue list --full` and the
dashboard report four separate facts from this same rule: the recorded review, whether
it still covers the final change, whether the cycle completed, and the delivery facts.
The short `queue list` line carries the status alone.

`completed` is the cycle's own outcome. PR URL, CI result, merge status and publication
are delivery facts, recorded with `pilot delivery` at any time, before or after
completion. Completion claims none of them, and none of them completes a cycle. Later
commits never reopen a completed cycle or change its recorded review.

When PR CI fails or the delivered work shows a defect, record the fact. The cycle stays
as it is, and the writer prints the choice to offer the owner: reopen the cycle for the
related repair, or create a linked cycle with `pilot create --follows CYC-ID` when the
repair deserves its own scope. Reopen only on the owner's instruction, quoted in
`--owner-instruction`. Reopening keeps the earlier completion, checks and review in the
record, adds the repair tasks and returns the cycle to `working`. It completes again
after the repair tasks, their checks and a review recorded after the reopening. Checks
that the repair does not affect are not rerun.

## Record and recovery

Only the lead changes the structured record through the pilot writer, except for the
requested reviewer's own report. The writer
validates shape, writes atomically and refuses stale expected revisions. Save at
milestones, then commit with ordinary work checkpoints and at handoff or completion.
The writer does not commit each operation. Directory loss can lose uncommitted
progress; atomic writes prevent partial files, not disk loss.

Allocate a distinct cycle ID through the existing allocator before branching.
Duplicate IDs are allocation errors. Concurrent cycles use separate checkouts and
branches; separate branches in one checkout do not isolate edits. Keep one editor
per checkout and one integration owner. A local ownership claim coordinates
cooperating agents; it cannot prevent arbitrary external edits.

Every reassignment increments the task's run number. A return from an earlier run
cannot complete its replacement. On resume inspect the record, Git status, diff and
actual host state. Reconcile unfinished work before restarting it. Record those observations with
`resume --reconcile`; a local ownership claim never expires automatically. Host handles do
not prove liveness. Preserve unknown edits and unknown Git locks. Routine work needs
no per-file proof, ancestry classification, token rotation or staged-byte seal.

Review names the plan revision and code commit range. Source changes need an
independent assessment of the delta. Material scope, acceptance or council-choice
changes require reassessment of affected planning and review. Bookkeeping preserves
review. Use Git code identity, not a second source inventory. A task update during
review leaves the cycle state as it is. Unfinished implementation work, a plan
revision or a change to a reviewed path after the reviewed head makes the review
obsolete, and `finish` refuses it.

## Queue item

The queue starts the head item as a pilot only when the caller selects it:

```bash
uv run /abs/plugin-root/scripts/cycle.py queue start-next --pilot --lead session-a --plan /tmp/start.json
```

The plan file holds exactly `verification`, `council` and `tasks`; the item supplies
goal, scope and acceptance. Authorization, dependency checks and interrupted-start
recovery are those of an ordinary start, and a retry adopts the pilot already created.
Without `--pilot` an item starts a typed cycle, as before. A release item never starts
as a pilot.

When a pilot created outside the queue did a queued item's work, name the item id in
the pilot title or goal. After review, the lead associates the two through the queue writer:

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
started under the pilot's own cycle id. The authorization, the other items and the
allocator are untouched, and no legacy cycle is created. An authorization that captured
the item records it as started, as an ordinary start does. Repeating the command writes
and commits nothing; repeating an interrupted call finishes it. A queue binding has no
effect on review status.

The queue follows cycle completion. It reports a pilot item as running, `reviewed`
(awaiting finish) or `completed`. A reviewed item is open: it is not counted closed, it
satisfies no dependency, and it holds the queue as a running cycle does until the lead
finishes it. A completed pilot satisfies dependencies whatever its PR, CI or merge
status, and its item archives through `queue archive` or the next queue write once the
pilot record is committed. No item carries a merged-code dependency condition; when one
genuinely needs merged code, say so in the item's acceptance. Reopening a completed
pilot leaves an archived item archived, creates no second item and undoes no dependent
cycle already started; an item not yet archived shows the reopened cycle as running.
The queue writer commits the queue file; commit the pilot record with the next ordinary
checkpoint.

A task or batch write changes the record and the checkout claims as one unit under the
runtime lock. A refused or failed write restores the claims exactly as they stood, and
two tasks of one batch cannot claim one checkout.

The record is the commit point. The writer saves added claims before the record and
drops released claims after it, so a process killed during a write leaves at most a claim
the record does not back, never a working task without its claim. The next write to the
same pilot removes such a leftover, and so does `pilot recover ID`, which changes nothing
else and reports what it reconciled. Retrying the interrupted write is enough. Recovery
removes only a claim that carries this pilot's id and matches no working assignment in
its record. It never removes another owner's claim and never assumes an owner is dead
from elapsed time; a checkout another pilot's leftover holds is freed by that pilot's
next write or its `recover`.

Diagnose repeated failure without new evidence, or pause. Do not add a cycle-wide
retry counter. Individual tools retain bounded retries for cost or external effects.
Pause for an unresolved blocker, an owner decision on scope or acceptance, a failed
premise, or an owner stop. Preserve authorization and duplicate-action protection
for council and publishing; an uncertain external act must be reconciled before retry.

## Durable decisions and completion

Create an ADR only for a constraint future work must preserve, such as compatibility,
data policy or an architecture boundary. Routine implementation choices stay in the
plan. Keep the constraint, reason, alternatives and consequences concise. Council
approves the exact draft; a person explicitly accepts it. This prototype does not
add automatic pilot-origin ADR creation. Use the existing direct-request or
whiteboarding proposal route only when its actual provenance applies. Otherwise
retain the candidate constraint in the plan for the owner to request separately.
Never relabel pilot-origin work as a direct request. The existing legacy cycle
creation gate remains intact. Plan approval is not ADR acceptance or external-action
authorization.

Record the outcome in review JSON: `summary` for the delivered outcome and consequential
choices, with optional `lessons` and `remaining` lists. `finish --summary` replaces the
summary when a shorter completion statement serves better. There is no mandatory Reflect phase or empty
lessons section. Retain plan revisions, council conclusions, test summaries and final
review. Keep temporary logs or host details only when they explain unresolved problems.

## Pilot assessment

Exercise a direct fix, council-planned shared-code work, interruption/resume,
concurrent checkouts, review/fix, and PR CI failure. Check ownership, plan recovery
and rejection of obsolete review in every scenario. Compare coordination operations,
retained record bytes and unnecessary reruns against comparable existing cycles.
Report wall time separately; smaller tasks or faster models do not prove workflow
savings. Council-review the enduring policy and obtain explicit human acceptance
before any default rollout. Preserve historical records and evidence.
