---
name: migrate-promptbooks
description: "Use when the user says \"migrate promptbooks\", \"convert legacy promptbooks to yaml\", \"migrate the promptbook corpus\", \"upgrade the .md promptbooks\", or after the structured-YAML book/run format has landed and the legacy Markdown books + run snapshots need translating. Translates legacy `.md` promptbooks and run snapshots into structured `.yaml` (validated against promptbook.schema.json / run.schema.json), recomputes each run's book_content_hash against its migrated book, preserves every original by relocating it into `docs/promptbooks/legacy/`, regenerates the promptbooks index, and logs the migration. Idempotent and re-runnable; never touches the in-flight active book or its in_progress run."
disable-model-invocation: true
metadata:
  tags: "promptbooks, migration, yaml"
  bundles: "crux-docs"
  risk_level: "low"
  routing_note: "Translates legacy `.md` books + runs to `.yaml`; preserves originals under `docs/promptbooks/legacy/`; recomputes each run's `book_content_hash`. Idempotent; never touches the in-flight active book."
---

# Migrate Promptbooks

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

An **idempotent per-file** format migration: legacy Markdown promptbooks and run
snapshots (frontmatter + prose body) → the structured-YAML format defined by
`promptbook.schema.json` / `run.schema.json`.
It migrates each file **once** (an already-migrated file is a no-op — see step 1),
but the skill itself is **re-runnable**: invoke it whenever new `.md` files appear
in the corpus and it will pick up only the not-yet-migrated ones.

The decision that makes this safe against the "archived books are immutable /
run snapshots are append-only" contract: **immutability attaches to content,
not file extension.** This skill never destroys an original — it writes the
`.yaml`, validates it, and only then relocates the original `.md` (byte-for-byte
unchanged) into `docs/promptbooks/legacy/`. After migration the `.yaml` is the
live immutable artifact and the `legacy/.md` is the frozen original.

Engine vs. orchestration split (mirrors `extract-code-docs` / `validate-catalog`):

- **`${CRUX_PLUGIN_ROOT}/scripts/migrate-promptbooks.py`** is the pure per-file engine:
  parse one legacy `.md` → emit structured `.yaml` → self-validate (call
  `validate-promptbook.py`) → for runs, recompute `book_content_hash` against
  the migrated book and assert it matches. `--dry-run` writes nothing;
  `--relocate` performs the preserve-then-move.
- **This skill** is the orchestrator: resolve the corpus, drive the script
  book-before-run, regenerate `docs/promptbooks/index.md`, and write the
  `docs/log.md` entry.

Pairs with: `author-promptbook` / `run-promptbook` / `archive-promptbook` (which
emit + read the new format on the new-format path; legacy `.md` coexists until a
later cleanup collapses the dual read paths).

## When to use

- User says: "migrate promptbooks", "convert legacy promptbooks to yaml",
  "migrate the promptbook corpus", "upgrade the .md promptbooks".
- A `.md` book or run snapshot remains in `docs/promptbooks/` after the
  structured-YAML format is in force, and you want it on the new format.

Do **not** use this skill for:
- The in-flight active book or its `in_progress` run — **never migrate a book
  whose `status: active` or a run whose `status: in_progress`** (a run's format
  is fixed at its start; converting mid-flight rewrites a live snapshot). Migrate
  the active book only after it archives.
- Authoring or advancing books — that's `author-promptbook` / `run-promptbook`.
- Editing an archived book's content — migration is a format rewrite only; the
  semantic content is preserved verbatim.

## Inputs

- **Optional**: explicit paths to migrate. Default: the whole legacy corpus
  (every `.md` under `docs/promptbooks/archive/` and their run snapshots under
  `docs/promptbooks/runs/<id>-<slug>/`).
- **Optional**: `--dry-run` to preview the emitted YAML without writing.

## The pipeline

Execute in order.

### 1. Resolve the corpus (exclude the in-flight book)

- Books to migrate = every `.md` in `docs/promptbooks/archive/` (NOT
  `docs/promptbooks/active/` — the active book is in-flight).
- Runs to migrate = `run-*.md` under `docs/promptbooks/runs/<id>-<slug>/` **only
  for `<id>-<slug>` whose book is in `archive/`**. This excludes the active
  book's run dir by construction.
- A book already migrated (its `.yaml` exists AND its `legacy/` original exists)
  is a no-op — skip it. A half-state (live `.yaml` present but no `legacy/`
  original) is an ERROR: surface it; do not silently re-migrate.

### 2. Migrate books first (book-before-run ordering)

For each book `.md`: run `migrate-promptbooks.py --relocate <book.md>`. The
script writes `archive/<id>-<slug>.yaml`, validates it, and (on success) `git
mv`s the original to `docs/promptbooks/legacy/archive/<id>-<slug>.md`. If the
script exits non-zero, STOP and surface the JSON errors — do not proceed to that
book's runs.

### 3. Migrate runs

For each run `.md` whose book is now migrated: run
`migrate-promptbooks.py --relocate <run.md>`. The script writes
`runs/<id>-<slug>/run-RUN-NNN.yaml` (normalizing the older `run-001.md`
basename to `run-RUN-001.yaml`), validates it, recomputes `book_content_hash`
against the on-disk migrated book and asserts it matches, then relocates the
original to `docs/promptbooks/legacy/runs/<id>-<slug>/<original-basename>.md`
(original basename preserved). A run whose book `.yaml` does not exist is an
error (book-before-run precondition).

### 4. Regenerate `docs/promptbooks/index.md`

Walk `active/`, `runs/`, `archive/` (NOT `legacy/`). Rebuild the index. Because
wiki-links are extension-less, the Active / Recent-runs / Archived sections are
unchanged except the underlying files are now `.yaml`. `docs/promptbooks/legacy/`
gets no index section (it is a preservation holding area, not a catalogued
surface — treated like `docs/inbox/`).

### 5. Bump `docs/index.md` `_Last updated:`; append to `docs/log.md`

One `promptbook` op: `## [YYYY-MM-DD] promptbook | migrated corpus to .yaml`.
Body: counts (N books + M runs migrated), the originals' location
(`docs/promptbooks/legacy/`), and a note that the live dirs are now `.yaml`-only.

### 6. Verification

- [ ] Every migrated `.yaml` validates: `validate-promptbook.py docs/promptbooks/**/*.yaml` → exit 0.
- [ ] Every migrated run's `book_content_hash` equals a fresh `compute_book_hash` of its migrated book.
- [ ] Every original is preserved under `docs/promptbooks/legacy/` (no `.md` lost).
- [ ] `active/`, `archive/`, and `runs/` contain no `.md` (except the in-flight active book + its run, deliberately left).
- [ ] `docs/promptbooks/index.md` counts unchanged; `_Last updated:` bumped.
- [ ] `docs/log.md` has the `promptbook | migrated corpus` entry.

## Red flags — STOP and reconsider

- About to migrate the active book or its `in_progress` run. **Never** — exclude
  by construction (only `archive/` books + their run dirs).
- About to migrate a run before its book's `.yaml` exists. Book-before-run is a
  hard precondition (the run's `book_content_hash` is computed against the
  on-disk migrated book).
- About to DELETE an original instead of relocating it. Never — the contract is
  preserve-by-relocate.
- About to relocate the original BEFORE its `.yaml` validates. The order is
  write → validate → (hash-check for runs) → relocate. A failed validation
  aborts that file with the original untouched.
- About to walk `docs/promptbooks/legacy/` when rebuilding the index or in
  `audit-docs`. It is excluded from the concern walk.
- About to hand-edit `catalog/skills.json`. It is regenerated — run
  `validate-catalog.py`.

## Rationalization table

| Excuse | Reality |
|---|---|
| "I'll just delete the `.md` originals; git has them." | The contract is preserve-by-relocate into `legacy/`. A present, navigable original is the immutability guarantee; git history is weaker. |
| "The active book is `.md` too — migrate it for consistency." | A run's format is fixed at its start; migrating the in-flight book/run rewrites a live snapshot. Migrate it only after it archives. |
| "Migrate the runs first, they're independent." | A run binds to its book by `book_content_hash` over the migrated book. Book-before-run, always. |
| "Leave the original as a `.md` twin next to the `.yaml`." | Twins in the live dirs defeat format-detection and double-count in the index. Relocate to `legacy/`. |
| "Re-running will double-migrate." | Already-migrated files are a no-op (the `.md` is gone from the live dir); the corpus glob is empty. Idempotent. |

## Common mistakes

- **Walking `legacy/`** in the index rebuild → double-counted archived books.
- **Migrating a run whose book is still `.md`** → `book_content_hash` has no
  valid input. Order matters.
- **Normalizing the relocated original's basename** — preserve it byte-for-byte
  (the older `run-001.md` form stays `run-001.md` under `legacy/`); only the
  emitted live file normalizes to `run-RUN-001.yaml`.

## See also

- `${CRUX_PLUGIN_ROOT}/scripts/migrate-promptbooks.py` — the engine.
- `validate-promptbook.py` — the validator the engine self-checks against.
- `author-promptbook` / `run-promptbook` / `archive-promptbook` — emit/read the new format.
