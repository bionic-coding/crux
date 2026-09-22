---
name: verify-code-docs
description: "Check generated code documentation against source and report drift without regenerating it."
metadata:
  tags: "code-docs, verification, drift-detection"
  bundles: "crux-docs"
  risk_level: "low"
  triggers: "verify docs | check code docs drift | are the code docs in sync? | lint docs"
  routing_note: "Read-only; emits `lint` log entry."
---

# Verify Code Docs

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

The read-only drift detector for the regenerative `docs/code/` concern. Invokes the same dispatcher script `extract-code-docs` uses, but with `--dry-run`: the extractor's `discover()` + `extract()` passes run, the would-be manifest is computed, and the diff against the on-disk `docs/code/_meta/manifest.json` is emitted to stdout. **Nothing under `docs/code/` is written.**

The skill is the verification gate, not the fix. When drift is found, it surfaces the change counts and explicitly offers to print the `extract-code-docs` invocation. The user (or a CI hook) decides whether to regenerate.

**Flag:** `--no-log` (alias `--ci`) suppresses the `lint` log entry (step 5) for high-frequency non-interactive runs (CI gates, pre-push hooks) that would otherwise append one `docs/log.md` entry per push. It changes nothing else — same drift report, same exit semantics. See step 5.

Pairs with: `extract-code-docs` (which actually writes), `audit-docs` (which invokes this skill — i.e. the dispatcher's `--dry-run` mode — as part of the broader audit). Distinct from `refresh-research-sources` (research concern) and `refresh-research-synthesis` (research concern).

## When to use

- User says: "verify docs", "verify code docs", "check code docs drift", "are the code docs in sync?", "lint docs".
- Pre-merge / pre-push hook (CI) wants a fast read-only check before allowing the merge.
- Proactively after a non-trivial refactor of source files where you suspect `docs/code/` no longer reflects the code.
- During `audit-docs`, which calls this skill internally.

Do **not** use this skill for:
- Regenerating `docs/code/` — that's `extract-code-docs`. This skill never writes there.
- Refreshing research sources — use `refresh-research-sources`.
- Generic file-level diffing of `docs/` — use `audit-docs` for the cross-concern view.
- Editing `docs/code/` files by hand. **Manual edits to `docs/code/` are blown away on the next `extract-code-docs` run.** This skill is the early warning that next regeneration will produce a diff; it does not preserve hand edits.

## Preconditions

1. `docs/manifest.yml` exists and lists at least one entry under `code.extractors[]`. If absent, refuse cleanly: "No code extractors configured in `docs/manifest.yml`. Run `init-docs` or edit the manifest first."
2. The dispatcher script exists at `${CRUX_PLUGIN_ROOT}/scripts/extract-code-docs.py`. If absent, refuse: "Plugin install incomplete: `extract-code-docs.py` not found. Reinstall Crux using `install-docs-skills`."
3. `docs/code/_meta/manifest.json` may be absent — that means no prior extraction has run. The skill should still complete: every discoverable page will show as `added`. Surface this clearly in the report.

## The pipeline

Execute in order. Never reorder, never skip.

### 1. Invoke the dispatcher in dry-run mode

Run from the repo root:

```bash
${CRUX_PLUGIN_ROOT}/scripts/extract-code-docs.py --dry-run --config docs/manifest.yml
```

Capture stdout (the drift report — JSON per the dispatcher's contract) and stderr (extractor-level warnings, per-plugin messages).

**Exit-code semantics (do not get this wrong):**

- `0` + valid JSON stdout with `added/changed/removed` keys: clean — no drift detected.
- `1` + valid JSON stdout with `added/changed/removed` keys: **drift detected**. THIS IS THE EXPECTED PATH on first run after `init-docs` (no `_meta/manifest.json` yet) and any time source files have changed. Treat the stdout as the drift report and proceed to step 2.
- Non-zero exit + empty or unparseable stdout: extractor crash, malformed config, or missing language toolchain. Surface stderr. Do not write a log entry. Do not proceed.

In other words: try to parse stdout as JSON FIRST. If it parses with the expected keys, the exit code distinguishes "clean" (0) from "drift" (1) — both are normal operating modes, both proceed. Only treat exit-code failure as a crash when stdout is missing or malformed.

If diagnosed as a crash:
- Suggest fixes: missing CLI tools (e.g., "TypeScript extractor needs `typedoc` on PATH"), bad globs in `docs/manifest.yml`, etc.
- Exit cleanly.

### 2. Parse the drift report

The dispatcher emits a structured diff against `docs/code/_meta/manifest.json`:

- **added**: source units present in `discover()` output but not in the on-disk manifest. New files, new exported modules, new classes/functions.
- **changed**: source units in both, but the freshly-extracted `DocPage` differs from the on-disk page (content hash mismatch, signature changed, doc-comment edited).
- **removed**: source units in the on-disk manifest but not in `discover()` output. Source file deleted, module renamed, export removed.

For each category, the dispatcher includes the page path (`docs/code/<lang-namespace>/<unit>.md`) and a one-line summary (e.g., for `changed`: which fields differ — `signature`, `description`, `examples`).

### 3. Report

**Zero drift** (added = 0, changed = 0, removed = 0):

```
Code docs are in sync.
Extractors run: <list>
Pages verified: <total count>
```

(No "last extracted" timestamp is reported — `_meta/manifest.json` deliberately omits timestamps so it stays byte-stable across runs; extraction recency lives in `docs/log.md`.)

Done. Skip to step 5 (log).

**Drift detected**:

```
Code docs are out of sync: N added / M changed / K removed.

Added (N):
- docs/code/<lang>/<unit>.md — <source path>
- ...

Changed (M):
- docs/code/<lang>/<unit>.md — <which fields differ>
- ...

Removed (K):
- docs/code/<lang>/<unit>.md — <source path no longer present>
- ...
```

If the on-disk manifest was absent, frame the report as "first run":

```
No prior extraction found (docs/code/_meta/manifest.json missing).
N pages would be created on first extraction. Run `extract-code-docs` to populate.
```

### 4. Offer regeneration — **never auto-regenerate**

After the drift report, print exactly:

```
Run `extract-code-docs` to regenerate. This will:
- Add N new page(s)
- Overwrite M changed page(s)
- Delete K removed page(s)
- Rewrite docs/code/_meta/manifest.json

Manual edits in docs/code/ will be lost. (The regenerate model is the contract.)

Want the exact command to run? (y/n — defaults to n)
```

**What the prompt does (it never regenerates):** this skill is read-only and never calls `extract-code-docs` itself. The prompt is *not* an offer to regenerate — it only asks whether to **print the exact invocation** for the user to run themselves:
- **"yes"** = print the literal `${CRUX_PLUGIN_ROOT}/scripts/extract-code-docs.py --config docs/manifest.yml` command (and a one-line reminder that the user must run it). Nothing under `docs/code/` is touched.
- **"no"** (or a non-interactive / CI trigger) = skip printing the command and exit cleanly with the report.

Either way, regeneration is a separate, explicit user action. This keeps the verify/extract responsibility split clean:
- `verify-code-docs` is read-only.
- `extract-code-docs` is the only writer to `docs/code/`.

After the prompt resolves, log the lint entry per step 5 (subject to `--no-log`/`--ci`; see below).

### 5. Append to `docs/log.md`

**First check `--no-log` / `--ci`.** If the invocation passed `--no-log` (alias `--ci`), **skip this entire step** — do not append anything to `docs/log.md`. This is the only effect of the flag: it suppresses the `lint` log entry for frequent, non-interactive runs (CI gates, pre-push hooks) that would otherwise spam `docs/log.md` with one entry per push. The drift report (steps 2–3) and the exit-code semantics (step 1) are unchanged; only the log append is suppressed. When the flag is absent, log exactly as below.

> **Flag scope:** `--no-log`/`--ci` is a **skill-level** flag this skill checks here before writing the log entry. It does **not** belong to the underlying dispatcher. If a caller wants to pass it through the dispatcher CLI, the `extract-code-docs.py` dispatcher must learn to accept (and ignore for extraction purposes) `--no-log`/`--ci` so the dry-run invocation in step 1 doesn't error on an unknown flag — **that dispatcher-side change is out of this SKILL.md's scope and is flagged for the developer.** As specified here, the skill reads the flag from its own invocation and gates step 5 on it; step 1's dispatcher command stays exactly as written (no `--no-log` appended to it).

One entry (newest-first):

```
## [YYYY-MM-DD] lint | verify-code-docs (N added / M changed / K removed)
```

Body, 1–3 lines:
- The drift summary in one line.
- Whether the user opted to regenerate (yes/no/n/a if non-interactive).
- Pointer to the next step if regeneration was deferred: "Re-run `verify-code-docs` after `extract-code-docs` to confirm zero drift."

Even on **zero drift**, log it:

```
## [YYYY-MM-DD] lint | verify-code-docs (in sync)
```

The `lint` op is distinct from `audit` — `lint` records a targeted check; `audit` records the broader vault walk. Both are first-class ops in the `docs/AGENTS.md` §6 enum.

### 6. Hand-off

If drift exists and the user declined regeneration, remind them:
- The diff will accumulate until `extract-code-docs` is run.
- A pre-merge hook can be configured to refuse merges when verify reports drift.
- Manual edits in `docs/code/` are not preserved by regeneration — if there's something to keep, write the doc-comment into the source file.

If no drift, no hand-off needed beyond the report and the log entry.

## Verification checklist

- [ ] `docs/manifest.yml` was read and at least one extractor is configured.
- [ ] The dispatcher was invoked with `--dry-run` and `--config docs/manifest.yml`.
- [ ] No file under `docs/code/` was created, modified, or deleted by this skill.
- [ ] No file under `docs/code/_meta/` was modified by this skill.
- [ ] The drift counts (added / changed / removed) match the dispatcher's output.
- [ ] The "Run `extract-code-docs` to regenerate" prompt was shown verbatim when drift exists.
- [ ] The skill did NOT invoke `extract-code-docs` itself — the user must run it explicitly.
- [ ] One `lint` op entry was appended to top of `docs/log.md` — even on zero drift — **unless** `--no-log`/`--ci` was passed, in which case NO log entry was written (and that was the only behavioral change).

## Red flags — STOP and reconsider

- About to write to `docs/code/` directly. **Never.** This skill is read-only.
- About to call `extract-code-docs` from inside this skill because "the drift is obvious". **Never.** The split between verify and extract is intentional.
- About to suppress the drift report because "it's a tiny diff". The user decides what's tiny. Show the report.
- About to skip the log entry because "no drift means nothing happened". A verification IS something that happened — log it. (The **only** sanctioned skip is an explicit `--no-log`/`--ci` invocation; "it was quiet" is not a reason.)
- About to fall back to a manual file-by-file diff because the dispatcher errored. The dispatcher is the source of truth; if it can't run, fix it, don't bypass.
- About to claim "in sync" without actually running the dispatcher (e.g., reading `_meta/manifest.json` mtime and inferring). Run the dispatcher.
- About to edit `docs/manifest.yml` to "make it work". Manifest edits are an explicit user decision; not part of this skill.
- About to claim drift without the dispatcher's structured output to back it up. The skill reports what the dispatcher says, full stop.

## Rationalization table

| Excuse | Reality |
|--------|---------|
| "The diff is one whitespace change — call it in-sync." | The dispatcher computes the diff; the dispatcher decides. If it says "changed", report it. |
| "I'll just go ahead and regenerate since the user clearly wants up-to-date docs." | No. Verify and regenerate are two separate user decisions. Surface drift; let the user invoke `extract-code-docs`. |
| "The extractor warned about an unsupported language; I'll ignore that." | Don't ignore stderr. Surface every warning the dispatcher emitted. |
| "There's no `_meta/manifest.json` — that's an error." | No — that's "no prior extraction". Frame as first-run; offer to populate. |
| "Manual edits in `docs/code/foo.md` are useful; I should preserve them in the diff." | Manual edits are explicitly out of contract. The next regenerate erases them. This skill flags drift, not edits-to-preserve. |
| "I'll write the log entry only if there's drift." | Always log — drift or not. The one exception is an explicit `--no-log`/`--ci` run, which suppresses the entry by design for high-frequency CI/pre-push gates. |
| "The CI hook is non-interactive; I'll auto-regenerate so the merge can proceed." | Never auto-regenerate. CI hooks should fail loud on drift; regeneration is a human (or scheduled) decision. |
| "I can read the dispatcher's exit code and infer the answer without parsing stdout." | The exit code says "ran successfully", not "in sync". Always parse the drift report. |

## Common mistakes

- **Auto-invoking `extract-code-docs`** when drift is found. The split is intentional — this skill is read-only.
- **Skipping the log entry on zero drift**. Verification with no drift is still a verification event — log it (unless `--no-log`/`--ci` was passed, the one sanctioned suppression).
- **Treating dispatcher exit code 0 as "no drift"**. Exit 0 means the run succeeded; the drift counts come from the parsed stdout.
- **Using the `audit` op in the log** instead of `lint`. The op enum is fixed; this skill is `lint`.
- **Reading `_meta/manifest.json` directly to compare**, bypassing the dispatcher. The on-disk manifest is one side of the diff; the freshly-extracted manifest is the other. The dispatcher computes both — don't reinvent.
- **Suggesting the user hand-edit `docs/code/<file>.md`** to fix drift. Hand-edits are lost. Edits must land in the source file's doc-comment.
- **Calling the dispatcher without `--config docs/manifest.yml`** — it relies on the manifest to know which extractors to enable.
- **Promising the user that "no drift now" means stable indefinitely.** Drift accumulates as source changes. The check is point-in-time.
- **Surfacing only "added/removed" counts and forgetting "changed"**. All three categories are first-class.
