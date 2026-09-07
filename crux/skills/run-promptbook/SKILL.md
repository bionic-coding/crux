---
name: run-promptbook
description: "Use when the user says \"run promptbook\", \"start promptbook\", \"advance promptbook\", \"next prompt\", \"skip prompt\", \"block on prompt\", \"abandon this run\", or to capture the result of a prompt that just executed. Creates a new run snapshot under `docs/promptbooks/runs/<book>/` on `start`; mutates the current snapshot's state on `advance`; records a deliberate abandonment of the run on `abandon`. This skill mutates run state but does NOT edit the prompts list — to change the plan mid-run, abandon the run and author a fresh book that cites its predecessor. For a read-only \"where am I / what's next / how do I resume PB-NNNN\" status query (no mutation), use `visualize-run-progress`."
arguments: [book]
metadata:
  tags: "promptbooks, execution, state"
  bundles: "crux-docs"
  risk_level: "low"
  routing_note: "Mutates run snapshot, not the book."
---

# Run Promptbook

> **Invocation:** a bound `$book` argument names the promptbook number — `/crux:run-promptbook 0007` binds `$book` to `0007`. Read the value from `$book` where this skill needs the promptbook number.

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->


## Overview

Promptbooks separate plan from state. The plan lives in `docs/promptbooks/active/PB-NNNN-<slug>.{md,yaml}`. The state lives in an immutable-bodied run snapshot at `docs/promptbooks/runs/PB-NNNN-<slug>/run-RUN-NNN.{md,yaml}`. This skill manages the snapshot.

Three modes:
- **`start`** — begin a new run against an existing active book. Allocates a per-book monotonic `RUN-NNN`, creates the snapshot, records the run's commit boundary, and sets `current_run` and `current_prompt` on the active book.
- **`advance`** — move the current snapshot's `current_prompt` forward by recording the outcome of the prompt that just ran. Terminal states: `done`, `skipped`, `blocked`.
- **`abandon`** — record a deliberate abandonment of the whole run. A run-level act, not a per-prompt one.

The skill is invoked many times per book — once on `start`, then once per prompt completion via `advance`.

### What an advance writes, and what it no longer writes

An advance writes exactly **two surfaces**: the run snapshot and the active book's `current_prompt` pointer. It regenerates no index and appends no log entry.

A book writes one `promptbook` op when a run **starts** and one when the book **archives**. Advancing a prompt writes **none**. The per-prompt chronology stays reconstructable from the run snapshot's own `started`/`completed` timestamps, which are per-prompt and immutable.

The derived indexes therefore regenerate at run start and at archive, not per advance. Name the consequence when it matters: between those two points the indexes hold the state as of the run's start, so a mid-run reader sees a stale progress figure. Once the book archives, every index holds what per-advance regeneration would have produced.

## Format detection (do this FIRST, every invocation — see `docs/CLAUDE.md` §3 for the `.md`/`.yaml` coexistence contract)

Two on-disk formats coexist; **detect before reading or writing anything**. The decision table routes on `(extension, format_version-present)` for the BOOK (mode `start`) and is fixed-by-the-snapshot's-own-extension for the RUN (mode `advance`):

| extension | `format_version` | route |
|---|---|---|
| `.yaml` | present | **new-format** (structured YAML; validated by the JSON Schema) |
| `.yaml` | absent | **error** — a malformed new-format document; do NOT send to the legacy parser |
| `.md` | (ignored) | **legacy-markdown** (the existing frontmatter + `## Prompt N` body parse path) |

**Coexistence is load-bearing.** Both paths stay live until the deferred migration ADR collapses them. The legacy `.md` path is preserved fully intact — every legacy step below is unchanged. The new `.yaml` path is ADDED alongside it.

**Format symmetry:** a `.yaml` run is created **only for a `.yaml` book** (so `book_content_hash` is never null in a valid new-format run); a run against a legacy `.md` book stays `.md`. **A run's format is fixed at its own start from the book's format _as of that start_, and never tracks later book changes.** Because the snapshot body is immutable, an **in-flight `.md` run finishes as `.md`** — converting it in place would rewrite frozen prompt blocks (forbidden); format conversion is `migrate-promptbooks`'s job.

> **Any in-flight legacy `.md` run (`status: in_progress`) MUST keep advancing on the legacy `.md` path, untouched** — every advance against it follows the legacy steps in mode `advance` below, exactly as before. Do NOT upgrade an in-flight `.md` run to `.yaml`.

## When to use

- User says: "start running PB-NNNN", "begin run", "run promptbook" (with no active run) → mode `start`.
- User says: "advance", "next prompt", "mark done", "mark skipped", "block this prompt" (during an in-progress run) → mode `advance`.
- User says: "abandon this run", "give up on PB-NNNN", "we're not finishing this run" → mode `abandon`.
- Another skill in the suite completed a side-effect that should advance the current prompt (called with `--silent`).

Do **not** use this skill for:
- Authoring a book or editing its `## Prompts` list — that's `author-promptbook`. If the user asks to edit prompts mid-run, REFUSE and route them to the abandon rule below.
- Archiving a completed or abandoned book — that's `archive-promptbook`.

## Abandon rule (critical)

If the user wants to edit `## Prompts` in the active book while a run is in_progress: REFUSE. Tell them:

> The active book's `## Prompts` list is frozen while RUN-NNN is in progress. To change the plan, abandon the run and author a fresh book: `run-promptbook abandon PB-NNNN --reason "<why>"`, then `author-promptbook`. The new book cites its predecessor in its `goal`/`strategy` prose; the abandoned run keeps its snapshot as the record of how far the old plan got.

Editing the plan mid-run breaks the snapshot's reference to it — `book_content_hash` binds the run to the plan it started against, and an in-place edit shows up as a CHK-PB-BIND mismatch that is never auto-fixed. Always abandon and re-author.

The mid-run fork path is deleted. `forked_from` remains an accepted book field that is always `null`, and nothing writes it. State the consequence plainly when it comes up: the successor relation now lives in prose and no longer resolves mechanically.

## The pipeline (mode: start)

### 0. Resolve per-repo configuration (.crux) — applies to BOTH modes

Run `python3 "${CRUX_PLUGIN_ROOT}/scripts/crux-config.py"` from the repo root (or pass `--repo-root <repo-root>`), and confirm the returned `repo_root` is the repo you are operating in — `source: "discovery:<dir>"` with an unexpected `repo_root` means you resolved the wrong directory, not that no config exists. On exit 1, **STOP** and surface the `{"error": ...}` payload — never fall back to defaults. Use the returned `docs_dir` to resolve the docs root wherever this skill says `docs/` (per the docs/CLAUDE.md §14 normative definition clause), and accept prefixed book ids (e.g. `CRX-PB-0040`) anywhere this skill says `PB-NNNN` — the prefixed string is the id, verbatim, in paths and `book_id`. `RUN-NNN` ids are never prefixed.

### 1. Resolve the target book (FORMAT-DETECT here)

User must supply or imply `PB-NNNN`. If ambiguous, list active books from `docs/promptbooks/index.md` and ask.

Locate the book at the exact constructed path `docs/promptbooks/active/PB-NNNN-<slug>.{yaml,md}` (prefer `.yaml` if present, else `.md` — do NOT glob `*` for discovery; resolve the slug from the index). **Run the format-detection table** on it:
- **`.yaml` + `format_version` present** → **new-format book**. This run will be a `.yaml` run (format symmetry). Parse the structured document: top-level `id`, `title`, `total_prompts`, `current_run`, `current_prompt`, and the structured `prompts:` array (each element carries `n`, `title`, `purpose`, `prompt`, `expected_output`, optional `side_effects`/`module_tag`).
- **`.yaml` + `format_version` absent** → **error**: a malformed new-format book. Surface it; do NOT fall through to the legacy parser.
- **`.md`** → **legacy book**. This run will be a legacy `.md` run (format symmetry). Parse frontmatter + the `### Prompt N — <title>` body blocks, exactly as before.

Confirm (both formats):
- `status: active`.
- `current_run`, branched on the pointed-to run's `status`: `null` → no run in progress, start one. Non-null + `in_progress` → surface the in-progress run and ask whether the user wants to supersede it or advance it instead. Non-null + ARCHIVE-ELIGIBLE terminal (`completed`, or `abandoned` with `abandonment.kind: deliberate`) → this book's run is finished, not in progress; tell the user and route to `archive-promptbook` rather than offering supersession. Non-null + `abandoned` with `abandonment.kind: superseded` → that run confers no archive eligibility, so `archive-promptbook` would refuse it; treat it as a stale run and take the supersession path below. Read the `kind`: routing a superseded run to the archive dead-ends it, because neither skill will accept it.

**The start-path supersession.** When the user chooses to start fresh over a stale run, set the PRIOR run snapshot's `status: abandoned`, `current_prompt: null`, and

```yaml
abandonment:
  kind: superseded
  at: <ISO 8601 UTC>
  reason: "superseded by RUN-NNN"
```

This is a DIFFERENT act from a deliberate abandonment and the `kind` is what distinguishes them. `kind: superseded` **confers no archive eligibility** — a book whose current run was merely superseded cannot archive. Only `kind: deliberate`, written by mode `abandon`, does. Never write `kind: deliberate` here.

### 2. Allocate `RUN-NNN`

Walk `docs/promptbooks/runs/PB-NNNN-<slug>/`. Find the maximum existing `run-RUN-NNN.{md,yaml}` (enumerate BOTH extensions — a directory may hold legacy `.md` runs and new `.yaml` runs side by side) and add 1 (or start at `001` if the directory doesn't exist yet). Per-book monotonic, zero-padded to 3 digits. Numbers are never reused across formats either.

### 3. Write the snapshot — branch on the book's detected format

The snapshot's format mirrors the book's (§1 / format symmetry): a `.yaml` book → a `.yaml` run; a `.md` book → a `.md` run.

#### 3a. New-format `.yaml` run (book is new-format `.yaml`)

Path: `docs/promptbooks/runs/PB-NNNN-<slug>/run-RUN-NNN.yaml`.

Write a single structured YAML document per `${CRUX_PLUGIN_ROOT}/schemas/run.schema.json`. Top-level keys:

```yaml
format_version: "1"
run_id: RUN-NNN
book_id: PB-NNNN
book_content_hash: "sha256:<64 lowercase hex>"   # the binding — see below
started_at: <ISO 8601 UTC>
completed_at: null
status: in_progress
current_prompt: 1
base_commit: "<40 lowercase hex from `git rev-parse HEAD`, or null>"
prompts:
  - n: 1
    title: "<title denormalized from the book's prompts[0].title>"
    state: pending
    started: null
    completed: null
    result: ""
    artifacts: []
  - n: 2
    title: "<title denormalized from the book's prompts[1].title>"
    state: pending
    started: null
    completed: null
    result: ""
    artifacts: []
# notes / pr_draft / summary are optional trailing Markdown literal-block scalars; "" until populated.
```

- **`prompts:` is populated from the book's `prompts[]`** — one element per book prompt, in order. Each element: `n` (1-based, contiguous from 1 — the validator's post-schema pass enforces `n == index+1`), `title` **denormalized** from the book (copy the verbatim value so the run renders offline; the abandon rule guarantees it can't legitimately diverge), `state: pending`, `started: null`, `completed: null`, `result: ""` (empty is `""`, NOT the legacy `—` placeholder), `artifacts: []`.
- **`base_commit` (the run's commit boundary — written ONCE at start, never rewritten):** run `git rev-parse HEAD` at the repo root and store the 40 lowercase hex commit id. This is the evidence source the `patch` tier's archive check reads: it lets `check-blast-radius.py` draw the run's changed paths from the repository's own change record rather than from anything the run wrote about itself. "Never rewritten" is enforced at both ends, not merely asked: `advance-run.py` refuses to write a snapshot whose `base_commit` diverges from the value in its own committed version, and `check-blast-radius.py` refuses to pass one at archival. If the repository is not a git work tree, write `base_commit: null` — and say so, because a `patch` book whose run has no commit boundary cannot archive as completed. For an `adr` or `verify` book the field is recorded but unused.
- **`abandonment` is OMITTED at creation.** It is written later, once, either by mode `abandon` (`kind: deliberate`) or by a later run's start-path supersession (`kind: superseded`).
- **`book_content_hash` (the binding — load-bearing, computed ONCE at start, immutable for the run's life):** compute it by calling the validator's hash function over the book's frozen-plan subset — `${CRUX_PLUGIN_ROOT}/scripts/validate-promptbook.py` (source checkout: `<checkout>/crux/scripts/validate-promptbook.py`) exposes `compute_book_hash(book_dict)` (which internally calls `frozen_plan_subset` and `canonical_json`). Pass the parsed `.yaml` book document; it returns `"sha256:" + sha256(canonical_plan_bytes).hexdigest()`. **Do NOT hand-roll a hash** and do NOT hash the raw file bytes — the hash is over the canonical-JSON of the frozen plan subset (`format_version`, `id`, `title`, `tags`, `total_prompts`, `goal`, `strategy`, plus `modules` and `blast_radius` when present, and each prompt's `n`/`title`/`purpose`/`prompt`/`expected_output` plus `side_effects`/`module_tag`/`phase` when present), EXCLUDING the mutable run-state fields `current_run`/`current_prompt`/`status`. `blast_radius` and `phase` are inside the subset deliberately: that is what fixes a `patch` book's declaration and its phase sequence once the run starts. This is exactly the subset the §4 abandon rule freezes, so the hash is stable across the run-state writes every advance makes; a later mismatch (`audit-docs` CHK-PB-BIND, and for a `patch` book `check-blast-radius.py` at archival) means the plan was edited in place instead of the run being abandoned and a successor book authored.
- The per-prompt shape is validated by `run.schema.json` (audit invokes `validate-promptbook --kind run`); the prose contract for the fields (the `State` enum, the lifecycle, archive eligibility) is **`docs/CLAUDE.md` §11.B**, with the title-case Markdown labels mapping to lowercase snake_case YAML keys (`State`→`state`, `Started`→`started`, `Completed`→`completed`, `Result`→`result`, `Artifacts`→`artifacts`).

On snapshot creation every prompt is `pending`; prompt 1 transitions to `running` on the first advance.

#### 3b. Legacy `.md` run (book is legacy `.md`) — UNCHANGED

Path: `docs/promptbooks/runs/PB-NNNN-<slug>/run-RUN-NNN.md`.

Frontmatter:

```yaml
---
run_id: RUN-NNN
book_id: PB-NNNN
started_at: <ISO 8601 UTC>
completed_at: null
status: in_progress
current_prompt: 1
---
```

Body: one section per prompt in the active book, in order. The per-prompt block shape (heading + `State`/`Started`/`Completed`/`Result`/`Artifacts` fields, and the `State` enum) is defined canonically in **`docs/CLAUDE.md` §11.B "Run-snapshot per-prompt shape"** (the single source of truth — read §11.B for the authoritative field list). On snapshot creation every prompt is `pending`; prompt 1 transitions to `running` on the first advance.

```markdown
## Prompt 1 — <title from book>
- **State:** pending
- **Started:** null
- **Completed:** null
- **Result:** —
- **Artifacts:** —

## Prompt 2 — <title from book>
- **State:** pending
- **Started:** null
- **Completed:** null
- **Result:** —
- **Artifacts:** —
```

Copy each `### Prompt N — <title>` from the active book as `## Prompt N — <title>` here (run snapshots flatten the prompts section by one level — they're no longer nested under a `## Prompts` heading).

### 4. Update the active book

Set the run-state fields on `docs/promptbooks/active/PB-NNNN-<slug>.{yaml,md}` — for a new-format `.yaml` book these are **top-level YAML keys**; for a legacy `.md` book they are **frontmatter keys** (same field names either way):
- `current_run: RUN-NNN`
- `current_prompt: 1`

Do NOT touch the body. Plan is frozen now.

### 5. Regenerate `docs/promptbooks/index.md`

Walk active, runs, and archive. Rebuild the index (same format as documented in `author-promptbook`). Progress for this book is now `1/<total_prompts>`.

### 5b. Bump `docs/index.md` `_Last updated:`

Read `docs/index.md`, update only the `_Last updated:` line to today. Counts under `## Promptbooks` don't change on run start (active/archived counts are unchanged); the per-book `current_run`/progress is in `docs/promptbooks/index.md`, not the master rollup.

### 6. Append to `docs/log.md`

```
## [YYYY-MM-DD] promptbook | started PB-NNNN-<slug>/RUN-NNN
```

Body: book id, run id, total_prompts, current_prompt.

## The pipeline (mode: advance)

### 1. Locate the in-flight snapshot (FORMAT-DETECT here)

Read the active book at `docs/promptbooks/active/PB-NNNN-<slug>.{yaml,md}`. Take `current_run` (RUN-NNN) and `current_prompt`. Open the snapshot at `docs/promptbooks/runs/PB-NNNN-<slug>/run-RUN-NNN.{yaml,md}`.

**Detect the SNAPSHOT's format** (its own extension is authoritative — a run's format is fixed at its start and never tracks the book; an in-flight `.md` run stays `.md` even after the book converts):
- **`run-RUN-NNN.yaml` with `format_version`** → mutate as a structured `.yaml` run (§3a below).
- **`run-RUN-NNN.yaml` without `format_version`** → error (malformed new-format run; do NOT send to the legacy parser).
- **`run-RUN-NNN.md`** → mutate via the legacy `## Prompt N`-block path (§3b below). **This is the path any in-flight legacy `.md` run takes — unchanged.**

If `current_run` is `null`, the user wants to advance with no active run — refuse, tell them to `start` first.

### 2. Decide the outcome

The user's intent maps to a terminal state for `current_prompt`:
- "done" / "next" / "advance" → `done`
- "skip" → `skipped`
- "block" / "stuck" → `blocked`

`blocked` now means blocked, with no second field and no pause-versus-abandon question at the prompt level. Ask if the outcome is ambiguous; don't infer `done` when the user might mean `skipped`. A `blocked` prompt is terminal for the run, so a run whose remaining prompts all reach a terminal state still completes, and the book archives as delivered with the block recorded in its terminal-state counts.

**When the user means "we are not finishing this run at all", that is mode `abandon`, not an outcome.** Abandonment moved from the prompt to the run (see below).

### 3. Mutate the snapshot — branch on the snapshot's detected format

The outcome decided in §2 (`done`/`skipped`/`blocked`, and the pause-vs-abandon distinction) is identical for both formats. Only the on-disk mutation differs.

#### 3a. New-format `.yaml` run — mutate ONE element of `prompts:`

**Preferred: use the vendored `advance-run.py`.** Hand-editing the snapshot across N advances is error-prone and a naive re-emit silently drops the run-level trailing fields. Run
`uv run "${CRUX_PLUGIN_ROOT}/scripts/advance-run.py" <run-RUN-NNN.yaml> --outcome done|skipped|blocked [--result "…"] [--artifacts docs/a.md,docs/b.md] [--book <active-book.yaml>]`
(source checkout: `<checkout>/crux/scripts/advance-run.py`). It mutates the `n == current_prompt` element, moves the pointer (next `pending` → `running`, or completes the run), updates the active book's pointer when `--book` is passed, and **round-trips every top-level key** (so `notes`/`pr_draft`/`summary` survive). It refuses a `.md` snapshot or a `.yaml` without `format_version`. If you cannot run it, mutate by hand per the field list below — and heed the trailing-field rule.

Mutate exactly the array element whose `n == current_prompt` (the JOIN KEY). On that element, set:
- `state: <outcome>` (lowercase enum `done|skipped|blocked`).
- `started: <set on first advance if still null — this advance's start time best-effort, or the actual prompt-start time if known>`.
- `completed: <now ISO 8601 UTC>`.
- `result: "<one-line summary the user provides, or \"\" (empty string) if none>"` — empty is `""`, never the legacy `—`.
- `artifacts: [<docs/ paths the prompt touched, as a real YAML list>]` — `[]` if none (a list, not a CSV cell).

Do NOT alter the element's `title` or any other element. Only the listed keys change. Never edit prior elements (their state was finalized in earlier advances). **Preserve the run-level trailing fields `notes` / `pr_draft` / `summary` verbatim on every advance** — they are set later in the run (Prep/Summary) and a re-emit that omits them silently drops accumulated notes, the PR draft, and the completion summary (`advance-run.py` round-trips them for you; a hand re-emit must copy them through). The per-prompt shape is validated by `run.schema.json` (audit invokes `validate-promptbook --kind run`); the prose contract is `docs/CLAUDE.md` §11.B, unchanged in meaning.

#### 3b. Legacy `.md` run — mutate the `## Prompt N` block — UNCHANGED

Update only the `## Prompt <current_prompt>` block in the snapshot body (the field set and `State` enum are canonical in `docs/CLAUDE.md` §11.B):
- `**State:** <outcome>`
- `**Started:** <set on first advance if still null — use this advance's start time as best-effort, or the actual prompt-start time if known>`
- `**Completed:** <now ISO 8601 UTC>`
- `**Result:** <one-line summary the user provides, or "—" if none>`
- `**Artifacts:** <comma-separated list of docs/ paths the prompt touched, or "—">`

A frozen `.md` snapshot may still carry a `**blocked-confirmed:** true` line from before the field was retired. Leave it exactly where it is: those bodies are immutable, and the field now means nothing to any reader.

Do NOT alter the prompt's title or any other block. Only the listed fields change. Never edit prior prompts' bodies (their state was already finalized in earlier advances).

### 4. Move the pointer — branch on the snapshot's detected format

Find the next prompt whose state is `pending` (the next `prompts[]` element for `.yaml`; the next `## Prompt N` block for `.md`). If found:
- Set the snapshot's top-level `current_prompt: <next>` (`.yaml` top-level key / `.md` frontmatter).
- Set the next prompt's state to `running` (`.yaml`: that element's `state: running` and `started:` becomes "now" best-effort; `.md`: the `## Prompt N` block's `**State:** running` / `**Started:**`) — updated to the exact start on the next advance.
- Set the active book's `current_prompt: <next>`.

If no `pending` prompts remain (i.e. **all prompts are terminal** — `status: completed` ⇔ every prompt is `done`/`skipped`/`blocked`):
- Set the snapshot's `status: completed`, `completed_at: <now>`, `current_prompt: null` (`.yaml` top-level keys / `.md` frontmatter). (Run-level `abandoned` is NEVER written here — it is written only by mode `abandon` or by the start-path supersession of a stale prior run, §1 of mode `start`.)
- The active book's `current_run` is UNCHANGED — it still names this run. Set only the active book's `current_prompt: null`. Only a book's current run can authorize its archive, so the pointer stays until `archive-promptbook` nulls it. (Book stays `status: active` — `archive-promptbook` moves it to `archive/`.)

### 5. Stop — the advance is finished

Those two surfaces are the whole write. Do not regenerate `docs/promptbooks/index.md`, do not bump `docs/index.md`, do not call `log-work`, and do not append to `docs/log.md`. The indexes regenerate at run start and at archive; the log records the start and the archive and nothing between.

### 6. Verification

- [ ] Only the current prompt's state changed in the snapshot body — `.yaml`: exactly one `prompts[]` element (the one with `n == prior current_prompt`, plus the new `running` element) mutated, no other element touched; `.md`: only the `## Prompt <prior>` block changed — diff confirms no other lines moved.
- [ ] The snapshot's `current_prompt` (`.yaml` top-level / `.md` frontmatter) matches the active book's `current_prompt`.
- [ ] If run completed: `status: completed`, `completed_at:` set, `current_prompt: null`, active book's `current_run` UNCHANGED — still names this run. (`status: abandoned` is NOT set by advance.)
- [ ] For a `.yaml` run: the snapshot still validates against `run.schema.json` (`validate-promptbook --kind run`) — `n` contiguous from 1, no stray keys.
- [ ] Exactly two surfaces changed: the run snapshot and the book's pointer. `docs/promptbooks/index.md`, `docs/index.md` and `docs/log.md` are untouched by this advance.

## The pipeline (mode: abandon)

Abandoning is a **run-level** act. It is how a book that will not finish still closes cleanly, and it is the signal `archive-promptbook` reads.

1. **Locate the in-flight snapshot** exactly as in mode `advance` §1. Refuse if `current_run` is `null`.
2. **Record the abandonment.** Run
   `uv run "${CRUX_PLUGIN_ROOT}/scripts/advance-run.py" <run-RUN-NNN.yaml> --abandon --reason "<one line>" --book <active-book.yaml>`.
   It sets `status: abandoned`, `completed_at: <now>`, `current_prompt: null`, and
   ```yaml
   abandonment:
     kind: deliberate
     at: <ISO 8601 UTC>
     reason: "<one line>"
   ```
   It leaves every prompt element's `state` untouched. That is deliberate: the prompt left `running` or `pending` is the evidence of how far the run got, and rewriting it would erase the record.
3. **The book keeps `current_run`.** Only a book's current run can authorize its archive, so the pointer stays until `archive-promptbook` nulls it. Only `current_prompt` is nulled here.
4. **Two surfaces, as ever.** No index regeneration, no log entry. The `promptbook` op comes at archive.

**The record is written when the abandonment is taken, and never retrofitted.** `advance-run.py` refuses a run that is already `completed` or `abandoned`, or that already carries an `abandonment` record. If a run ended without one, it ended without one — a book cannot be made archive-eligible after the fact by backdating a reason.

**`kind: deliberate` versus `kind: superseded`.** Only `deliberate` — this mode — confers archive eligibility. `superseded`, written by a later run's start over a stale run, confers none. The two share a `status` and are told apart only by `kind`.

## Red flags — STOP and reconsider

- About to pause mid-run to ask permission for a step the current prompt already authorizes (e.g. an in-repo file edit the prompt mandates). DON'T — the plan is the authorization. The only legitimate mid-run stops are the module escalation loops and genuinely irreversible/outward-facing actions the plan didn't authorize (push/merge, deploy, external send, data deletion, spend). Editing in-repo files — including `docs/CLAUDE.md`, skill files, code — is none of those, however important the file feels. See `docs/CLAUDE.md` §11 "Run execution autonomy."
- About to upgrade an in-flight `.md` run to `.yaml` because "the new format is better." NEVER. A run's format is fixed at its start; converting in place rewrites a frozen immutable body. Format conversion is the deferred migration ADR's job. Keep legacy runs on the legacy path.
- About to hand-roll the `book_content_hash` (e.g. `sha256sum` of the book file, or your own canonicalizer). NEVER. Call `validate-promptbook`'s `compute_book_hash` — a raw-byte hash mismatches by the second advance (the book's run-state frontmatter changes by design), and a divergent canonicalizer breaks CHK-PB-BIND. There is exactly one correct serialization and the validator owns it.
- About to send a `.yaml` file lacking `format_version` to the legacy `.md` parser, or a `.md` file to the `.yaml` path. NEVER — format-detect first (§"Format detection"); a `.yaml` without `format_version` is an ERROR, not a legacy doc.
- About to edit a prompt body in the snapshot (title, purpose, expected output / the denormalized `title`). NEVER. Only the state/started/completed/result/artifacts fields (`.yaml` element keys / `.md` block fields) change.
- About to edit `## Prompts` / the book's `prompts:` array in the active book because the user asked. REFUSE → the Abandon rule above.
- About to edit a prior run snapshot (a previous `run-RUN-NNN.{md,yaml}` that's already `completed` or `abandoned`). NEVER. Past runs are immutable archive material.
- About to advance when `current_run` is `null` on the active book. The user probably wants `start` — ask.
- About to advance when `current_run` is non-null but the pointed-to run is TERMINAL (`completed` or `abandoned`). That is not an in-progress run either — route to `archive-promptbook`, unless the run is `abandoned` with `abandonment.kind: superseded`, which confers no archive eligibility and belongs on the start-path supersession instead.
- About to mark a prompt `done` when the user said "I skipped it" or "I got stuck". Ask for explicit outcome.
- About to write a `docs/log.md` entry, call `log-work`, or regenerate an index on an advance. NEVER — an advance writes two surfaces. The log records a run's start and a book's archive; a prompt is a step, not an operation.
- About to update only the snapshot but forget the active book's `current_prompt` pointer. Both writes happen together or the audit will flag the mismatch.
- About to write a `blocked` prompt an extra field to mark it "really" terminal. That field is gone. If the run will not finish, use mode `abandon`.
- About to retrofit an `abandonment` record onto a run that already ended. NEVER — an abandonment is recorded when it is taken. A run that ended without one is not archive-eligible.
- About to write `kind: deliberate` when superseding a stale run at start. NEVER — that is `kind: superseded`, and it confers no archive eligibility.

## Rationalization table

| Excuse | Reality |
|---|---|
| "The user said 'next' — I'll mark prompt N done and move to N+1 without asking what 'next' means." | "Next" sometimes means "done, advance"; sometimes "skip this". Ask. |
| "I'll edit the snapshot's prompt title — it has a typo." | Snapshots are immutable. Fix the typo in the active book and let future runs carry the correction. |
| "I'll fix the user's typo'd `## Prompts` list right now — it's faster than abandoning and re-authoring." | The plan is frozen for the run's life; `book_content_hash` binds them. Abandon the run and author a successor book. |
| "The previous run-001 ended with prompt 3 still `running` — I'll quietly set it to `done`." | Past runs are immutable. If a prior run was abandoned, leave the running state — it's evidence. |
| "The log lost its per-prompt chronology — I'll keep writing one entry per advance anyway." | The chronology moved, it did not vanish: every prompt carries its own `started`/`completed` in the immutable snapshot. Re-adding the entry restores a duplicate, not a record. |
| "I'll just reuse an earlier RUN-NNN — the first one is junk." | RUN-NNN is monotonic per book, across BOTH extensions. Never reuse. Supersede the prior run instead. |
| "This run is dead and the book needs closing — I'll mark the leftover prompts `skipped` so it archives as done." | That records delivery of work nobody did. Abandon the run; the book then archives as abandoned, which is the truth. |
| "The book just converted to `.yaml`, so I'll convert its in-flight `.md` run to match." | A run's format is fixed at its own start. The `.md` run finishes as `.md`; only a NEW run started afterward is `.yaml`. Converting a live run rewrites its frozen body. |
| "I'll write `book_content_hash` by `sha256sum`-ing the book file — simpler than calling the validator." | The raw file bytes change every advance (run-state frontmatter). The hash is over the canonical frozen-plan subset only; call `compute_book_hash`. |
| "Empty result on a `.yaml` run — I'll write `—` like the `.md` runs do." | On `.yaml` the empty result is `""`, and empty artifacts is `[]`. The `—` placeholder is legacy-`.md`-only. |

## Common mistakes

- **Confusing `current_prompt` between book and snapshot**: they must agree at all times. After advance, write both.
- **Forgetting `running` state**: between `pending` and a terminal state, the active prompt is `running`. Skipping `running` is fine, but if you set `running` on advance N, you must transition it to a terminal state on advance N+1.
- **Computing `total_prompts` from the snapshot body**: don't — it's the book's `total_prompts` (a `.md` book's frontmatter / a `.yaml` book's top-level key). The snapshot inherits the value at creation time (and `len(prompts)` must equal it — an audit cross-check).
- **Marking `status: completed` while a prompt is still `running`**: the run is only complete when ALL prompts have terminal states (`done`/`skipped`/`blocked`). `status: completed` ⇔ all prompts terminal.
- **Looking for a per-prompt archive-eligibility flag**: there isn't one. `blocked` is terminal for the run, so a run holding one still completes and the book archives as delivered. Archive eligibility is a RUN property — see `docs/CLAUDE.md` §11.B.
- **Using local timestamps**: always ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`). Local times collide across timezones.
- **Nulling the book's `current_run` on any terminal outcome — completed or abandoned**: don't. Only a book's current run can authorize its archive, and `archive-promptbook` reads `current_run` to find the completion or abandonment record. Null `current_prompt` only; `archive-promptbook` nulls `current_run` at archival.
