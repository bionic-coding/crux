# Cycle command interface

Run scripts with `uv run` and the resolved plugin root. `--repo-root` comes before
the cycle subcommand. Values below are examples to replace with the actual task.
The cycle writer and schema validate inputs; never hand-edit a record to bypass them.

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --repo-root . create \
  --type iterate --title 'Correct parser handling' --goal 'Accept valid inputs' \
  --scope 'src/parser.py' --scope 'tests/test_parser.py' \
  --acceptance 'Valid empty input is accepted' \
  --implementer developer-1 --coordinator tester-1
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --repo-root . show CYC-0001
```

Use the returned ID, including any configured prefix. `create` makes one record;
`show` and `validate` inspect it without advancing.

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

Use `task-add CYC-ID --file task.json` for a task and
`task CYC-ID --task-id ID --state pending|active|done|blocked` for its state.
Quick-fix has no Plan transition. It accepts `task-add` for its current phase or any
later phase, so it can record expected evidence for Test, Review, and Reflect up
front. Other types add tasks for the current phase, or any phase while in Plan.

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
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --repo-root . evidence CYC-0001 \
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
are required before Test advancement, Review, Release readiness, and completion.
Changing coverage does not itself execute checks.

A passing review binds to a basis: the plan's scope, constraints, acceptance,
verification and tasks, the required checks, the review policy, the current-pass
evidence and the coverage. Changing any of them after approval invalidates the review.
Bookkeeping does not: plan tasks of phases after the review-bearing phase (Reflect
today), task status, the reflection, completion and history. A historian can add a
Reflect task after approval and still complete the cycle. Reports record
`basis_version: 2`. A report without a version, recorded before versioning, still
binds when its digest matches the current basis or the earlier whole-plan basis.

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

## IDRs and ADRs

`decision CYC-ID --kind idr --name NAME --file decision.json` retains reasoning.
The contents require `alternatives`, `approach`, `assumptions`, `constraints`, and
`intended_evidence`. Inspect the returned decision path, then convene:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle-council.py" --repo-root . \
  --cycle CYC-0001 --purpose idr --subject DOCS-RELATIVE-DECISION-PATH \
  --question question.txt
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --repo-root . approve-decision CYC-0001 \
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
`extend CYC-ID --limit N --human-approval TEXT` records explicit owner approval;
never invent or infer the owner's instruction. `change-type` takes `--type` and
`--reason`, plus human approval when required to avoid bypassing an exhausted limit.

For Release, record `release-ready` with actual `--authorization`, repeated
`--destination`, and repeated `--artifact` only after passing checks and independent
review. Publish only under that authorization. Record `release-verified` with
`--verification` after checking the actual published state, then advance.

`reflect CYC-ID --file reflection.json` records `outcome`, `lessons`, and `remaining`.
Use `advance` to complete or `abandon` after recording an abandonment reflection.

Before completing a version-two record, commit the intended changes, then record:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --repo-root . completion CYC-0001 \
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
