---
name: extract-code-docs
description: "Regenerate code documentation from source using language extractors. Replaces generated files, including manual edits."
context: fork
model: sonnet
metadata:
  tags: "code-docs, extraction, regeneration"
  bundles: "crux-docs"
  risk_level: "low"
  triggers: "extract docs | refresh code docs | regenerate code docs"
  routing_note: "Regenerative — wipes `docs/code/`."
---

# Extract Code Docs

> **Execution context:** this skill runs in a forked subagent and returns a summary to the caller. The fork does not see the main-thread conversation, so pass any needed context explicitly at invocation.

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

This skill is a thin wrapper around `scripts/extract-code-docs.py`. The script does all the work: reads `docs/manifest.yml`, loads per-language extractor plugins from `scripts/extractors/`, runs them against the source tree, and rewrites `docs/code/` from scratch.

**Regenerative invariant.** `docs/code/` is throw-away output. Any `.md` files there that aren't produced by the current extraction run are deleted. The `_meta/manifest.json` row is the only record that a doc page exists. NEVER hand-edit anything under `docs/code/`. NEVER read `docs/code/*` as an input to anything else — the only canonical state lives in source-code doc comments.

The skill is otherwise mechanical:
1. Confirm prerequisites (manifest, extractors registered).
2. Run the dispatcher.
3. Interpret the output.
4. Log the operation.

## When to use

- User says: "extract docs", "regenerate code docs", "refresh code docs", "rebuild docs/code/".
- A pre-push or CI hook invokes this skill (no human intent needed).
- After a large refactor where module/function-level doc comments changed substantially.
- After `audit-docs` reports `docs/code/` drift (it calls the dispatcher with `--dry-run` and surfaces the diff).

Do **not** use this skill for:
- Verifying drift without writing — that's `verify-code-docs`, which invokes the same script with `--dry-run`.
- Editing doc content — edits go in the source files (e.g. `@moduledoc`, TSDoc), not in `docs/code/`.
- Adding a new language — that's a plugin author task: drop `scripts/extractors/<lang>.py` and register it in `manifest.yml`.

## Prerequisites

Before invoking the script, confirm:

1. `docs/manifest.yml` exists and has at least one entry under `code.extractors`.
2. Each entry's `extractor:` key matches a file `scripts/extractors/<name>.py`.
3. The repo root is determined (parent of `docs/`).

If any prerequisite fails: tell the user what to fix and STOP. Do not silently write nothing — that masks a configuration bug.

## The pipeline

### 1. Read `docs/manifest.yml`

Confirm `code.extractors` is a non-empty mapping. List the enabled language keys.

If the manifest's `concerns_enabled` does not contain `code`, refuse: this concern is opted out of for this project.

### 2. Run the dispatcher

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/extract-code-docs.py"
```

Useful flags:
- `--config PATH` — override manifest path (default `docs/manifest.yml`). One manifest owns
  both the sources scanned and the pages written, so an explicit path also supplies the
  default output directory: `<the config's own dir>/code`, never the current repo's.
  This relies on the convention every crux tree follows — the manifest lives AT the docs
  root — under which `<the config's own dir>` and the `.bionic.yml` `docs_dir` name the same
  directory, so the two default paths agree. A manifest kept somewhere other than its docs
  root is the one case where they diverge; pass `--output-dir` explicitly there.
- `--output-dir PATH` — override output directory (default: the `code/` dir of the tree that
  owns `--config`). This script prunes the named directory, so the directory's parent must
  hold a `manifest.yml` carrying a readable `schema_version`. When that manifest is missing
  or carries no `schema_version`, the run refuses before writing anything. Combining one
  tree's config with another tree's output dir is allowed and reported on stderr.
- `--lang KEY` — run only one extractor by language key.
- `--dry-run` — discover and extract but don't write; emits a diff summary and exits 1 if drift detected.
- `--verbose` — log per-extractor and per-file progress to stderr.

The script's exit code:
- `0` — success (or `--dry-run` with no drift).
- `1` — error, OR `--dry-run` detected drift.

### 3. Interpret the output

Final line: `extract-code-docs: wrote N page(s) (X added, Y changed, Z removed).`

These counts come from a SHA256 comparison against the previous `_meta/manifest.json`. Use them in the log entry.

If `removed > 0`, surface the removed list to the user. A removal means either:
- The source module was deleted (expected) — no action.
- The source file/module was renamed (expected) — confirm the rename produced a corresponding `added` row.
- An extractor stopped discovering the unit due to a config or extraction bug — investigate.

### 4. Handle `--dry-run` drift

When invoked in dry-run mode (typically from `verify-code-docs` or `audit-docs`):
- Exit 0 means the on-disk `docs/code/` matches the source-truth — no action.
- Exit 1 means drift. The stdout JSON shows added/changed/removed pages. Surface counts; recommend the user run a real extraction.

### 5. Append to `docs/log.md`

```
## [YYYY-MM-DD] extract | regenerated docs/code/ (N pages: X added, Y changed, Z removed)
```

Body: 1–3 lines summarizing which extractors ran and any noteworthy removals.

### 6. Verification

- [ ] `docs/code/_meta/manifest.json` exists and has one row per page.
- [ ] Every row's `doc_path` corresponds to an existing `.md` file under `docs/code/`.
- [ ] No `.md` file under `docs/code/` is absent from the manifest (the script's pruning guarantees this; check anyway).
- [ ] `docs/code/index.md` lists every doc page grouped by language namespace.
- [ ] `docs/log.md` has a new top-of-file `extract |` entry.

## Red flags — STOP and reconsider

- About to read `docs/code/<anything>` to "preserve" hand-edits before regenerating. **NEVER.** Manual edits there are not authoritative. If a user wants persistent prose about a module, it belongs in the module's source comments OR in `docs/research/` — not in `docs/code/`.
- About to write directly to `docs/code/` without going through the dispatcher. NEVER. The dispatcher owns the entire directory.
- About to commit `docs/code/` to git without first verifying the project's policy (the gitignore-or-not decision should be recorded in your project's ADR log). Check that ADR before assuming it's tracked.
- About to skip the log entry because "nothing changed". Even a no-op run is auditable — the entry is `(0 added, 0 changed, 0 removed)`, still logged.
- About to mask a script failure as success. If the dispatcher exits non-zero outside dry-run mode, the operation failed; surface it.
- About to run extraction when `docs/code/` contains uncommitted changes the user might not know about. Suggest stashing or committing first so the regenerative deletion isn't silently destructive.

## Rationalization table

| Excuse | Reality |
|---|---|
| "I'll just edit `docs/code/foo.md` directly to fix the typo." | Next extraction deletes the edit. Fix the source comment. |
| "The dispatcher's output is verbose; I'll suppress it." | The added/changed/removed counts are the operation's audit trail. Surface them. |
| "I'll skip the log entry — `extract` is too noisy to journal every time." | The log is `docs/log.md`, not the journal. Operations log every time; journal entries are separate and selective. |
| "The user asked for docs of a new language — I'll hand-write `docs/code/<lang>/...`." | New language = new extractor plugin (`scripts/extractors/<lang>.py`) + manifest entry. Don't bypass the architecture. |
| "Removed pages are scary — I'll skip the prune step." | Without pruning, deletions accumulate as ghost pages. The regenerative invariant requires the prune. |
| "Drift on `--dry-run` is informational; exit 0 is fine." | Exit 1 is the contract — CI hooks rely on it to gate merges. |

## Common mistakes

- **Running the dispatcher from a non-repo cwd**: the `--config` default is relative (`docs/manifest.yml`). Either `cd` to the repo root or pass an absolute path.
- **Skipping a language because its extractor is "missing"**: an extractor entry pointing to a non-existent plugin is an error, not a no-op. The dispatcher exits 1. Don't catch and continue.
- **Forgetting that `--dry-run` exits 1 on drift**: that's a feature for CI hooks, not a bug. Don't wrap it in `|| true`.
- **Treating `extractor_version` as the schema version**: it's the extractor module's version, not the crux schema. They're independent.
- **Editing the dispatcher to add per-language logic**: extractor-specific logic belongs in `scripts/extractors/<lang>.py`. The dispatcher is generic.
- **Believing the dispatcher reads `docs/code/`**: it doesn't. It reads `_meta/manifest.json` for diff purposes only; everything else under `docs/code/` is overwritten or pruned.
