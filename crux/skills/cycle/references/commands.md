# Cycle commands

The commands a cycle lead runs. `scripts/cycle.py` is the cycle writer; it writes
`crux.cycle.v1` records and refuses a command it cannot verify. For the record, plan
JSON, review JSON, finish, delivery, reopening and recovery behaviour, read
[lightweight.md](lightweight.md). This file lists the commands and their inputs.

`--repo-root DIR` and `--compact` go before the command. `cycle.py pilot SUB` is an
alias of `SUB`. Exit 0 means success, 1 a refusal with a JSON `code`, 2 an environment
error. Every example below uses the absolute plugin root, never a shell variable.

## Writer commands

Every write after `create` takes `--actor ACTOR --expect-revision N`. The actor is the
lead, except in `review`, where it is the requested reviewer. A stale revision or a
late result from a superseded run is refused: read the record with `show`, then retry.

| Command | Inputs | Effect |
|---|---|---|
| `create` | `--title`, `--lead`; `--plan FILE` or `--goal`, `--scope` (repeatable), `--acceptance` (repeatable); `--follows CYC`; `--release-list {beta,official}` with `--version X.Y.Z` | Allocates the id and writes the record. An ordinary cycle starts in planning, with or without `--plan`, and leaves planning at the first task write. A release record starts in working. `--follows` links a repair cycle to the cycle it repairs. |
| `show ID` | `--full` | Prints the record. Read-only. |
| `plan ID` | `--file`, `--reason`; `--owner-approval TEXT`, or `--finding TASK` with `--criterion N` | Replaces the plan revision. An acceptance change takes effect only with `--owner-approval` holding the owner's own words.[^acceptance] So does a scope change, except that the lead may add each path that a blocking finding, recorded by the cycle's requested independent reviewer, names as the place to fix an unmet acceptance criterion of the current plan: `--finding` names that finding's task id and `--criterion` the zero-based criterion, and `lightweight.md` states what the writer checks.[^scope] The cycle returns to planning, and every selected check reads missing until it is recorded again or reused. |
| `task ID` | `--task`, `--owner`, `--run N`, `--status {working,blocked,done}`; `--checkout`, `--summary` | Records who works a task and its result. `--run` is one above the task's current run. |
| `check ID` | `--file` | Records one check observation: command, result, tested revision, summary, reason. |
| `batch ID` | `--file` | Records tasks and checks in one write. |
| `review-start ID` | `--reviewer NAME` | Asks the independent reviewer for a verdict. The lead never submits it. |
| `review ID` | `--file` | The requested reviewer records its own verdict, with `summary`, `lessons` and `remaining`. |
| `delivery ID` | `--file` | Records PR, CI, merge, commit and publication facts. None completes or reopens a cycle. |
| `finish ID` | `--summary TEXT` | Completes the cycle when the agreed tasks are done, the selected checks pass and an approving review of the current plan revision covers the final change.[^completion] |
| `reopen ID` | `--file`, `--reason`, `--owner-instruction TEXT` | Reopens a completed cycle on the owner's recorded words. |
| `pause ID` | `--reason` | Stops a cycle at a named stop.[^stops] |
| `resume ID` | `--reason`, `--reconcile TEXT` | Resumes a paused cycle after stating what changed. |
| `abandon ID` | `--reason` | Ends a cycle for good. An abandoned cycle never restarts.[^abandon] |
| `recover ID` | none | Settles the checkout claims an interrupted write left. |
| `council-subject ID` | none | Freezes the exact plan revision as a council subject. |
| `council ID` | `--record PATH`, `--response TEXT` | Attaches an approved plan council to the cycle. |
| `status [ID]` | `--cycle`, `--json`, `--watch SECONDS` | Renders cycle progress and the queue. Read-only. |

Examples:

```bash
uv run /abs/plugin-root/scripts/cycle.py --repo-root /abs/repo --compact create --title 'Bounded change' --lead session-a --plan /abs/repo/plan.json
uv run /abs/plugin-root/scripts/cycle.py --repo-root /abs/repo --compact show CYC-0123
uv run /abs/plugin-root/scripts/cycle.py --repo-root /abs/repo --compact task CYC-0123 --actor session-a --expect-revision 1 --task parser --owner session-a --run 1 --status working
uv run /abs/plugin-root/scripts/cycle.py --repo-root /abs/repo --compact check CYC-0123 --actor session-a --expect-revision 2 --file /abs/repo/check.json
uv run /abs/plugin-root/scripts/cycle.py --repo-root /abs/repo --compact review-start CYC-0123 --actor session-a --expect-revision 3 --reviewer reviewer
uv run /abs/plugin-root/scripts/cycle.py --repo-root /abs/repo --compact finish CYC-0123 --actor session-a --expect-revision 5
```

The writer does not commit. The lead commits the cycle record with ordinary work
checkpoints, at handoff and at completion, under a message that names the cycle and
what the record gained.

## Plan council

Convene a council on the plan when the owner asks, a consequential trade-off needs
resolving, uncertainty blocks a defensible plan or a durable constraint changes.[^council]
Tasks that depend on the choice wait for the approval.

1. `council-subject ID` freezes the plan revision.
2. The architect runs `scripts/cycle-council.py --purpose consultation` on that subject. Read the `council` skill for its flags, recovery and await actions.
3. `council ID --record PATH --response TEXT` attaches the approved record.

The convening purposes `idr` and `adr-creation` are retired.

## Cycle-origin ADRs

Propose an ADR raised in a cycle with
`decision-policy.py propose --file FILE --origin cycle --cycle CYC-NNNN`. The cycle is
planning, working or reviewing. The proposal needs no creation council.[^adr] Council
approves the exact draft, and the configured acceptance policy still applies: by
default a person accepts it. Run `decision-policy.py accept --subject ADR
--approval RECORD [--human-approval TEXT]` only with the owner's actual words; the
`transition-adr` skill states the owner capture. A task that names `adr_dependencies`
cannot move to working or done until each ADR is Accepted.
`--creation-approval` and `--creation-subject` are retired.

## Queue

`cycle.py queue SUB` captures and orders work, then starts authorized items one at a
time. The queue writer commits the queue file.

| Subcommand | Inputs | Effect |
|---|---|---|
| `add` | `--title`, `--outcome`, `--type`, `--scope`, `--acceptance`; `--depends-on`, `--position`, `--reference`, `--release-list`, `--held` with `--reason` | Adds an item. `--type` is a suggestion only. |
| `list` | `--full` | One line per open item and the authorization. `--full` gives one row per item and the authorization history; an archived item's row omits its outcome, scope, acceptance and references. |
| `show ITEM` | none | One item with its fields and its cycle's history facts. In `show` and `list --full`, `position` counts unstarted items in queue order and is null once an item has started. |
| `edit`, `move`, `hold`, `unhold`, `remove` | per `--help` | Change the list. |
| `authorize` | `--kind {next,next-n,queue}`, `--count`, `--instruction TEXT`, `--date YYYY-MM-DD` | Records the owner's verbatim instruction and the items it covers. |
| `revoke` | `--reason` | Ends the active authorization, for an owner pause. |
| `start-next` | `--lead`, `--implementer`, `--coordinator`, `--plan FILE` | Starts the head item as a cycle, or reports the open cycle or the stop reason. `--pilot` is accepted and ignored. |
| `reconcile ITEM` | `--pilot CYC`, `--actor`, `--file` | Associates a pending item with the completed cycle that did it. A repeat changes nothing. |
| `archive` | `--dry-run`, `--migrate` | Archives terminal started items. |

Every non-release item starts a `crux.cycle.v1` record. Authorization, dependencies,
interrupted-start recovery, completion and archival keep their behaviour; the Queue
section of [lightweight.md](lightweight.md) states them.

## Release records

A release item starts a record with the fixed beta (prep, prepare, verify,
beta-and-smoke, tag, record) or official (live-check-and-go-ahead, official, record)
step list. `tools/release.py` advances and completes it, and its ledger stays the
release authority. `task`, `finish` and `reopen` refuse a release record. DEPLOY.md is
the runbook for the commands, the authorization text and the bare publish command.

## Retired commands

Each former typed subcommand exits 1 with the JSON code `command-retired` and names its
replacement. Nothing is written.

| Retired | Replacement |
|---|---|
| `op`, `advance`, `checks`, `coverage`, `evidence`, `local-check`, `validate` | `check` records an observation; `plan --file` holds the selected checks; `task`, `review-start` and `finish` move the work |
| `assignment`, `await`, `context-read` | `task` records who works a task; wait with the host's native wait; read context files directly |
| `task-add`, `plan-details`, `withdraw-decision`, `scrutiny` | `plan --file --reason` replaces the plan |
| `decision`, `approve-decision`, `query-decisions`, `owner-decision`, `owner-approval` | `decision-policy.py propose` and `accept` for ADRs; `decision-policy.py owner-decision present`, `capture` and `apply` for an owner decision on an ADR acceptance; `council-subject` and `council` for a plan council; `plan --owner-approval` for a scope change |
| `return`, `change-type`, `extend`, `reflect`, `defer`, `friction`, `reduction` | no such step; `review` records findings, and a blocking finding becomes a task |
| `completion`, `owner-complete`, `shortcut` | `finish`; `reopen` on the owner's instruction; `create --follows` for follow-up work |
| `handoff`, `reconcile` | `show --full` and `status`; `recover` |

## Historical records

Records with `schema_version` 1 to 3, typed release cycles and promptbooks are
historical. They are read-only through `cycle.py show` and `cycle.py status`. Nothing
resumes or rewrites them, and a retired command that names one changes nothing.

[^completion]: rule:completion-needs-work-checks-and-review
[^acceptance]: rule:acceptance-changes-only-with-the-owner
[^scope]: rule:scope-changes-with-the-owner-or-a-review-finding
[^stops]: rule:named-stops-pause-any-cycle
[^abandon]: rule:abandoned-cycles-never-restart
[^council]: rule:council-reviews-consequential-plan-choices
[^adr]: rule:cycle-adrs-need-no-creation-council
