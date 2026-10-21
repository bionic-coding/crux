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

`status [CYC-ID] [--json] [--watch SECONDS]` prints the progress view that
`visualize-cycle-progress.py` prints, and writes nothing. With no ID it shows active
cycles first, then the others by cycle number, highest first, at most 20, followed by
the queue. `--json` prints the visualizer's JSON document. `--watch` clears the screen
and redraws every SECONDS until Ctrl-C, for a second terminal beside a session. Exit 0
printed, 1 invalid or unknown cycle, 2 environment.

## Plan and tasks

`plan CYC-ID --file plan.json --reason TEXT` takes the complete plan, preserving
its predecessor. Fields are `scope`, `constraints`, `acceptance`, `verification`,
`tasks`, and `revision` (the writer updates revision). Refactor adds
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

A plan file sets plan content, never task state. Each file task carries status
`pending` and no delivery field: `assignee`, `result_path`, `commits`, `evidence`,
`stage`, `note` or `replaced_commits`. The writer refuses anything else and names
`task`, the command that records state.

A revision pairs file tasks with recorded tasks by id. A paired task keeps its status
and delivery when its `phase`, `description`, `expected_evidence` and `depends_on`
are unchanged. A change to any of them, including a reordered list, makes the task
pending and clears its stage. Its commits, evidence, assignee, result path and note
stay. A new id starts pending. An omitted task leaves the plan, and the
`plan-revised` event keeps it. Re-adding that id later starts a new pending task.
A kept task is revalidated as described under Advancement and loops.

Use `task-add CYC-ID --file task.json` for a task and
`task CYC-ID --task-id ID --state pending|active|done|blocked` for its state.
Quick-fix has no Plan transition. It accepts `task-add` for its current phase or any
later phase, so it can record expected evidence for Test, Review, and Reflect up
front. Other types add tasks for the current phase, or any phase while in Plan.

## Record at execution boundaries

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
# Before dispatching the unit, substitute the actual coordinator-supplied path:
uv run /abs/plugin-root/scripts/cycle.py --repo-root . --compact task CYC-0001 --task-id build-parser --state active --assignee developer-1 --result-path /abs/os-temp/crux-results-CYC-0001-RANDOM/developer-parser-attempt-1.md
# When the unit returns, before any dependent dispatch:
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

Every developer commit message ends with a trailer line naming the task:

```text
CYC-0001 build-parser: correct empty-input parsing

Cycle-Task: build-parser
```

`handoff CYC-ID` is read-only. It prints the phase, pass, status, active tasks with
assignee and result path, delivered tasks with stage and commits, pending tasks, and
a `next_action` line. Include its output in a hand-back.

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
verification on a quick-fix in Build or Test. Other types use `plan`. The file holds
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
are required before Test advancement, Review, and completion.
Changing coverage does not itself execute checks.

A passing review binds to a basis: the plan's scope, constraints, acceptance,
verification, preserved behavior and improvement, the plan tasks up to the
review-bearing phase, the required checks, the review policy, the current-pass
evidence declarations and the coverage. Each task contributes only `id`, `phase`, `description`
and `expected_evidence`. Changing any basis field after approval invalidates the
review, as does a source change or a task added before the review-bearing phase.
Bookkeeping does not: a task's `status`, `depends_on`, `assignee`, `result_path`,
`commits`, `evidence`, `stage` and `note`, the plan's revision counter, plan tasks of
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

Use the actual scope declared in the plan, evidence, and independent reviewer.
A blocking finding includes `path`, `consequence`, and `evidence`. The alternative
verdict is `changes-required`. The writer binds the report to current inputs and
adds effective scrutiny; it cannot perform the review on the agent's behalf.

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
for simplify and only in the Test phase:

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
and `input_sha256` (the source fingerprint) with the areas. Test advance and Reflect completion refuse an
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
`--max-tokens` sets the output token budget per seat request, including its
existing fault retry. It defaults to `32000`; for example, use
`--max-tokens 64000` when a larger response budget is needed. The value must be a
positive integer no larger than the smallest output limit of the three selected
models in the registry. An oversized request is refused before an attempt is
created or any request is sent. New attempt metadata records the effective
`max_tokens`; historical attempts need no new field. This option changes no
seat assignment, retry policy, round limit, or approval threshold.
Consultation is advisory. Retain exact subjects; do not edit approved reasoning.
A revision is a new decision record with the same name and fresh council approval.

The owner may approve an exact IDR revision directly. Write
an owner approval record under the cycle directory and pass its path as
`--approval`. It carries exactly `format` (`crux.owner-approval`), `purpose`
(`idr`), `cycle_id`, `subject`, `subject_sha256`, `origin`
(`owner-conversation`), `quote`, `date` (`YYYY-MM-DD`) and `conversation`.
`quote` is the owner's own words, verbatim. Never write this record without an
actual owner instruction to quote. A later revision needs a new approval.

`owner-approval CYC-ID --subject PATH --quote TEXT --conversation TEXT` writes that
record for you at `cycles/CYC-ID/approvals/owner-<decision>.json`, binding the
subject's current sha256. It refuses an empty quote, a missing subject and an
existing record, and never defaults the quote. `--approve` also runs
`approve-decision`. An agent recording an owner approval looks like
self-approval and the permission classifier can deny it, so the owner runs it:
add `--print-command` to print one complete command line (quote shell-quoted,
nothing written) and hand that line to the owner.

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

A return or resume keeps delivered build work. Two events start a new pass: a
counted return that does not pause, and a resume after a pass-limit or
progress-stalled blocker. In a type with a Plan phase, such an event sets every task
to pending except build tasks. A build task keeps its status and delivery only when
it revalidates. Each check is independent: an integrated task's recorded commits are
all ancestors of HEAD, and every evidence path still exists. A failed check or a git
error makes the task pending and clears its stage; its commits and evidence stay. A
return that pauses changes no task; its resume applies the rule. A resume that starts
no pass changes no task. Quick-fix has no Plan phase, so a pass-starting event resets
every task. The `return-requested` and `plan-revised` events keep the full prior plan.

No flag reopens a task. To rework a delivered build task, change its `description`
or `expected_evidence` in the replan, for example by adding the finding's regression
check. Both fields enter the next review basis. Adding a fix task to its `depends_on`
also reopens it. Or add a separate fix task and leave the original done. Reopening
is not transitive: a done task that depends on a reopened task stays done. Test and
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

`reflect CYC-ID --file reflection.json` records `outcome`, `lessons`, and `remaining`.
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
changes block completion. Unrelated work may remain; describe it in `--remaining`.
Only a real user request for uncommitted delivery allows `--exception TEXT` instead
of commits. Quote the instruction and its context; no council or agent can grant it.
Re-record completion after scoped changes. The record's own bookkeeping is excluded
from commit binding to avoid a self-reference; commander commits that final record
after `advance` closes the cycle and reports its SHA too.

Version-one records remain readable and retain their original completion semantics.
For an active version-one cycle, follow the current coverage and commit instructions
and report the evidence explicitly; the old schema does not enforce the new fields.

## Release cycles

`create --type release --list beta|official` makes a release cycle. `--list` is
required: `create` refuses a release without it, and refuses `--list` on any other
type. The writer generates the tasks, each in phase `release` and depending on its
predecessor. The beta list is `prep`, `prepare`, `verify`, `beta-and-smoke`, `tag`,
`record`. The official list is `live-check-and-go-ahead`, `official`, `record`. The
cycle has one phase, `release`, and pass 1. Its limit of 1 is inert and the progress
view shows no limit. A beta cycle's scope names the release-prep paths and the log file;
an official cycle's scope names the log file.

A listed release cycle allows only `task`, `completion`, `pause`, `resume`, `abandon`,
`owner-complete`, `advance` and the read-only commands. The writer refuses every other
action: plan, task-add, plan-details, checks, coverage, evidence, review, decision,
reflect, return, extend and change-type. `validate` refuses a record whose task ids,
order, phase or dependencies differ from its list.

Record each step with `task`. `advance` completes the cycle when every task is done and
the completion record holds. It needs no reflection, coverage, review or decision.
`abandon` needs no reflection, because the record step keeps the closure reason.

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
| `queue add --title T --outcome O --type TYPE --scope P --acceptance A [--depends-on Q] [--reference PATH] [--position N] [--held --reason TEXT]` | Appends an item (or inserts at `--position`). The outcome becomes the cycle goal. |
| `queue list` | Every item with position, id, title, state, derived cycle status, dependencies with satisfied flags, cycle and `in_scope`, plus the authorization summary and the head item with its stop reason. |
| `queue show Q` | One item. |
| `queue edit Q [--title] [--outcome] [--type] [--scope] [--acceptance] [--depends-on \| --no-depends] [--reference \| --no-references]` | Replaces the named fields of a pending or held item. |
| `queue move Q --position N` | Moves an unstarted item to a 1-based position. |
| `queue hold Q --reason TEXT`, `queue unhold Q` | Holds or releases an unstarted item. |
| `queue remove Q` | Removes a pending or held item that no other item depends on. |
| `queue authorize --kind next\|next-n\|queue [--count N] --instruction TEXT --date YYYY-MM-DD` | Records the one authorization. The instruction is the owner's own message, verbatim. A new authorize replaces the current one. |
| `queue revoke --reason TEXT` | Ends the authorization. It stops further starts only. |
| `queue start-next [--implementer NAME] [--coordinator NAME]` | Starts the head item as a cycle, or reports why it cannot. Both names default to `dev-lead`. |

A reference is a repository path to a supporting document, such as a brief. `queue add`
and `queue edit` refuse a reference that does not exist or resolves outside the
repository; `queue list` and `queue show` display the list. `queue start-next` appends
the references to the created cycle's goal under `References (read before planning;
read-only, not scope):`, so Plan reads them first. References are read, not edited:
they never enter plan scope or the review scope comparison.

Authorization starts cycles only. It never authorizes push, publish, release or another
outward action, never extends a pass limit and never approves an IDR or ADR. `next`
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

The 500-item cap counts started items for the queue's lifetime. `start-next` considers
only queue-started cycles. Each started cycle keeps its own type, pass limit and stops.

## Configured council commands

`cycle-council.py` preserves historical receipts and adds mode-aware execution.
Read its `--help` and the `council` skill. Configuration uses `council.mode`, optional
`council.overrides.{adr,idr,migration}`, and `council.max_attempts` (1 through 7).
Missing legacy mode remains Strict. Setup records an explicit Standard/Lite choice.

- `--identity`: stable consultation or creation identity across subject renames.
- `--architect <JSON> --record <council>`: exact-final agreement and typed dissent.
- `--prepare-pass challenge|final`: sealed native request; the host dispatches it.
- `--ingest-result <host JSON> --request <request>`: validate and retain actual host evidence.
- `--recover <attempt>`: persist an original result without making a request.
- `--record-policy <slug> --owner-instruction <path>`: retain an explicit owner mode instruction.
- `--policy-action extend-council-limit --extension <limit> --identity <logical id>`:
  bind an explicit owner extension, rather than resetting the decision count.

`--initialize-council standard|lite|strict --selection <explicit choice>` is for
first Crux enrollment. It preserves unrelated configuration and records provenance.
It cannot reset an existing project policy. Read `council/references/native-lite.md`
for exact Codex and Claude host contracts. Native contexts are council evidence
only through the owning writer; independent implementation review stays separate.
