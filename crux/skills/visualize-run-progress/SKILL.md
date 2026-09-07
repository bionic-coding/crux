---
name: visualize-run-progress
description: "Use when the user says \"visualize run progress\", \"show run progress\", \"how far along is PB-NNNN\", \"progress of PB-NNNN\", \"run progress bar/chart\", OR asks where a cycle stands — \"where am I\", \"where was I on PB-NNNN\", \"resume my cycle\", \"what's next on PB-NNNN\", \"cycle status\", \"how do I pick this run back up\". One read-only surface answers both: it renders a run snapshot against its book as a colored terminal progress bar + per-prompt checklist (plus an opt-in byte-stable `run-RUN-NNN-progress.md` artifact), and it narrates the status query — which book and run, the current prompt, the next pending prompt verbatim, and the exact command to resume. READ-ONLY: derives a view, never mutates run state. Validates `.yaml` inputs against run.schema.json / promptbook.schema.json."
arguments: [book]
metadata:
  tags: "promptbooks, visualization, regenerative, cli"
  bundles: "crux-docs"
  risk_level: "low"
  routing_note: "Read-only, and the single surface for both read-only questions a run raises. Renders a run snapshot as a terminal progress bar + per-prompt checklist plus an opt-in byte-stable `run-RUN-NNN-progress.md` artifact, and narrates the status query — which book and run, the current prompt, the next pending prompt verbatim from the book, and the resume command. Joins `module_tag` from the book (`—` on hash mismatch / legacy `.md`). Never mutates; a status query writes nothing and logs nothing."
---

# Visualize Run Progress

> **Invocation:** a bound `$book` argument names the promptbook number — `/crux:visualize-run-progress 0007` binds `$book` to `0007`. Read the value from `$book` where this skill needs the promptbook number.

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

The read-side counterpart to `run-promptbook`. A run snapshot carries each prompt's `state` (`pending | running | done | skipped | blocked`); this skill **derives a progress view** from that state and the run's book, and renders it for a human (terminal) or for the repo (a Markdown artifact).

### The derive-only / byte-stable contract (canonical statement)

> **Derive, don't decide; regenerate byte-stably.** A derive-only renderer reads an upstream source of truth and emits a view of it — it **never mutates** the source (no proposing, transitioning, advancing, or "fixing" the upstream while rendering). Its output is a **regenerated artifact** on the same model as `docs/code/` and `catalog/skills.json`: the body is wholly rewritten on every run; hand-edits are blown away. The body carries **no timestamps and no per-run-varying values**, so the artifact is **byte-identical across runs** given the same input (deterministic ordering throughout); "when it ran" lives only in the `docs/log.md` entry, never in the body.

This is the canonical wording shared with the sibling renderer `link-adr-graph` (kept identical in both, deliberately in sync; `link-adr-graph`'s SKILL.md is the home copy). For `visualize-run-progress` specifically: the upstream source is the run snapshot + its book (read-only — state changes are `run-promptbook`'s job), and the regenerated artifact is the opt-in `run-RUN-NNN-progress.md` written only on `--markdown` (the default terminal render produces no artifact at all).

## Two questions, one surface

This skill answers both read-only questions a run raises, because they are the same read of the same two files:

- **"How far along?"** — the progress bar + per-prompt checklist, and the opt-in Markdown artifact. See "The helper script".
- **"Where am I, and how do I resume?"** — the status query. See "Status query".

Both derive from the run snapshot plus its book. Neither mutates anything.

## When to use

- User says: "visualize run progress", "show run progress", "how far along is PB-NNNN", "progress of PB-NNNN", "run progress bar".
- User says: "where am I", "where was I on PB-NNNN", "resume my cycle", "what's next on PB-NNNN", "cycle status", "how do I pick this run back up".
- Mid-cycle, to see which prompts are done / running / blocked at a glance.
- After stepping away from a cycle, to reorient before deciding whether to advance.
- To write a progress snapshot into the repo (`--markdown`) — e.g. to commit it so a run's state is visible in a PR or on GitHub (committing is optional; the artifact works identically untracked).

Do **not** use this skill to:
- Advance, block, abandon, or otherwise change run state — that's `run-promptbook` (this skill is read-only).
- Author or edit a book — that's `author-promptbook` / `dev-cycle` / `iterate` / `patch-cycle`.
- Convert legacy `.md` runs to `.yaml` — that's `migrate-promptbooks`.

## The helper script

`${CRUX_PLUGIN_ROOT}/scripts/visualize-run-progress.py` does the work:

```bash
# Terminal view (default) — colored progress bar + per-prompt checklist:
uv run "${CRUX_PLUGIN_ROOT}/scripts/visualize-run-progress.py" PB-0018

# Write the byte-stable Markdown artifact next to the snapshot:
uv run "${CRUX_PLUGIN_ROOT}/scripts/visualize-run-progress.py" PB-0018 --markdown

# A specific run, or an explicit snapshot path:
uv run "${CRUX_PLUGIN_ROOT}/scripts/visualize-run-progress.py" PB-0018 --run RUN-002
uv run "${CRUX_PLUGIN_ROOT}/scripts/visualize-run-progress.py" docs/promptbooks/runs/PB-0018-visualize-run-progress/run-RUN-001.yaml --markdown
```

(In a source checkout, where `${CRUX_PLUGIN_ROOT}` is unset, substitute the checkout's `crux/` directory — source checkout: `<checkout>/crux/scripts/visualize-run-progress.py`.)

- **Target**: a `PB-NNNN` id (the book is found under `docs/promptbooks/{active,archive}/`) or an explicit run-snapshot path.
- **Run resolution** for a bare `PB-NNNN`: `--run RUN-NNN` if given, else the book's `current_run`, else the highest-numbered run in the book's `runs/` dir.
- **`--markdown`** writes `run-RUN-NNN-progress.md` beside the snapshot; **`--terminal`** (the default when neither flag is given) prints to stdout. Both may be combined.
- **Color** is auto-disabled when stdout is not a TTY or `NO_COLOR` is set; `--no-color` forces it off. State→color: done=green, skipped=yellow, blocked=red, running=cyan, pending=dim.
- **Exit codes**: `0` clean; `1` not-found / schema-validation error.

## The pipeline

1. **Resolve** the run snapshot and its book (above).
2. **Format-detect + load** (mirrors `run-promptbook`): `.yaml` is validated against `run.schema.json` / `promptbook.schema.json` via the vendored `validate-promptbook.py`; a `.yaml` without `format_version` is an error (never sent to the legacy parser); `.md` is read via the legacy `## Prompt N` block parse.
3. **Build the model**: per-prompt `(n, title, module_tag, state)`, per-state counts, and the terminal-progress percentage (`done + skipped + blocked` over total). **`module_tag` is joined from the book** by `n` — but only after `compute_book_hash(book)` equals the run's `book_content_hash`. On a mismatch (a plan edited in place) or a legacy `.md` run, `module_tag` renders `—`.
4. **Render** terminal and/or the Markdown artifact. Author-controlled `title`/`result` text has C0/C1 control bytes stripped before printing (no ANSI/escape injection) and `|`/newlines escaped in Markdown cells.
5. **Log — ONLY on a deliberate operation.** A **deliberate operation** is one that writes a persistent artifact into the repo, i.e. an invocation with `--markdown` (which produces `run-RUN-NNN-progress.md`). On such a run, append a `promptbook` op entry to `docs/log.md` — `## [YYYY-MM-DD] promptbook | visualized PB-NNNN/RUN-NNN`. Reuse the existing `promptbook` op; do NOT mint a new op. **A transient terminal render (the default / `--terminal`, no `--markdown`) is NOT a deliberate operation: it produces no persistent artifact and MUST NOT write a log entry** — otherwise every glance at a progress bar would spam `docs/log.md`. Combined `--terminal --markdown` logs once (the `--markdown` write is the deliberate part).

## Status query — "where am I, and how do I resume?"

A status query is a narration, not a render. It writes nothing at all: no artifact, no `docs/log.md` entry. Report four parts.

1. **Which book and run.** The `PB-NNNN` id, the book title, the run id, and the run's `status` (`in_progress | completed | abandoned`). Name the book's `cycle_kind` when it has one. **When the run is `abandoned`, report its `abandonment.kind`** — `deliberate` means the run was closed on purpose and the book can archive as abandoned; `superseded` means a later run rolled over a stale one, and it confers no archive eligibility. The two look identical without the `kind`.
2. **The current prompt.** Its `n`, its verbatim `title`, and its `state` (`pending | running | done | skipped | blocked`).
3. **The next pending prompt, verbatim.** The lowest-`n` prompt whose state is `pending`, printed with its `n`, `title`, and **the full `prompt` body from the BOOK**, joined by `n` — the run snapshot denormalizes only the `title`. If no `pending` prompt remains, say so, and distinguish a `completed` run from a dormant one holding non-pending, non-terminal states.
4. **The resume command**, branched on the pointed-to run's `status`: `current_run` is `null` → `run-promptbook start PB-NNNN`. Non-null + `in_progress` → `run-promptbook advance PB-NNNN`. Non-null + terminal AND archive-eligible (`completed`, or `abandoned` with `abandonment.kind: deliberate`) → `archive-promptbook PB-NNNN` — the book's run is finished, not resumable. Non-null + `abandoned` with `abandonment.kind: superseded` → `run-promptbook start PB-NNNN`: a superseded run confers no archive eligibility, so naming the archive there would dead-end the user. Print it; never invoke it.

### Resolving the target for a bare "where am I"

1. **Explicit `PB-NNNN`** → locate the book at the constructed path `docs/promptbooks/active/PB-NNNN-<slug>.{yaml,md}` (prefer `.yaml`; resolve the slug from `docs/promptbooks/index.md` — do NOT glob `*`). An archived book lives under `docs/promptbooks/archive/`.
2. **No id given** → the most-recently-active cycle: scan `docs/promptbooks/active/` for the book whose `current_run` is non-null. A completed-but-unarchived book (its `current_run` still names a `completed` run, pending archival) is an EXPECTED hit here, not a bug — the resume command in part 4 distinguishes it, since it prints "archive", not "advance". If several books qualify, pick the one whose current run snapshot was modified most recently. If exactly one qualifies, use it without asking. If none does, say "no active run" and list the active books so the user can name one.
3. **Run precedence for the chosen book** (identical to the render path): `--run RUN-NNN` if the user named one, else the book's `current_run`, else the highest-numbered `run-RUN-NNN.{yaml,md}` in the book's `runs/` directory.

If the book's `compute_book_hash` no longer equals the run's `book_content_hash`, note that the plan was edited in place instead of being abandoned and re-authored, so the book text shown may diverge from what the run started against. Note it; never fix it.

## Verification checklist

- [ ] Output reflects the run's actual per-prompt `state` (cross-check against the snapshot).
- [ ] `--markdown` artifact has **no timestamps in the body** — running twice with `--markdown` produces a **byte-identical** file (diff the two outputs to confirm).
- [ ] A `docs/log.md` `promptbook | visualized …` entry was written **only on a `--markdown` run** (the deliberate operation). A terminal-only render (default / `--terminal`) wrote **no** log entry — confirm `docs/log.md` is unchanged after a terminal-only invocation.
- [ ] `module_tag` column is populated only when the book hash matches; `—` otherwise.
- [ ] No run snapshot or book was modified (read-only).
- [ ] A status query wrote NOTHING — no artifact, no log entry; the repo is byte-for-byte unchanged after it.
- [ ] The status query's "next" prompt is the lowest-`n` `pending` one, and its body is the verbatim `prompt` text from the BOOK, not the snapshot's denormalized title.
- [ ] An `abandoned` run was reported with its `abandonment.kind`, distinguishing a deliberate abandonment from a start-path supersession.
- [ ] `.yaml` inputs validated (a malformed snapshot exits 1 with a schema error, not a stack trace).

## Red flags — STOP and reconsider

- About to **edit the run snapshot** to "fix" a state while visualizing. NEVER — this skill is read-only; state changes are `run-promptbook`'s job.
- About to put a **timestamp in the Markdown artifact body**. NEVER — it breaks byte-stability. Time lives in `docs/log.md`.
- About to print **un-sanitized** `title`/`result` to a TTY. NEVER — strip control bytes first (the script does; don't bypass it).
- About to **hand-roll the book hash** to decide the `module_tag` join. Use `compute_book_hash` from `validate-promptbook.py` — the same function `run-promptbook` uses.
- About to send a `.yaml` without `format_version` to the legacy parser. It's an error; surface it.
- About to write a `docs/log.md` entry for a status query or a terminal-only render. NEVER — only the `--markdown` write is a deliberate operation. Logging a glance would spam the log.
- About to invoke `run-promptbook advance` "to be helpful" after reporting status. NEVER — this skill prints the resume command; advancing is a separate, explicit act.
- About to print the next prompt's text from the run snapshot. The snapshot denormalizes only the `title`; the verbatim body lives in the BOOK — join by `n` and read it there.

## See also

- `run-promptbook` — the only mutator of run state (start / advance / abandon); this skill points the user at it to resume.
- `migrate-promptbooks` — produces the `.yaml` runs this skill visualizes.
- `link-adr-graph` — the regenerated-artifact + derive-don't-decide precedent.
- `dev-cycle` / `iterate` / `patch-cycle` — produce the cycle books this skill reports on.
- Schema: `${CRUX_PLUGIN_ROOT}/schemas/run.schema.json` (the run format), `promptbook.schema.json`; validator `${CRUX_PLUGIN_ROOT}/scripts/validate-promptbook.py`.
