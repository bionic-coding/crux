---
name: check-drift
description: "Use when the user says \"check drift\", \"is the tree in sync\", \"run the drift gates\", \"any drift?\", \"verify all regenerated outputs\", or \"pre-release drift check\". Runs every enrolled regenerator in `--dry-run` mode read-only, parses each JSON verdict regardless of exit code, and reports one table of gate / verdict / drifted paths / the regenerator that fixes it. Never regenerates anything — it recommends the regenerator by name. The whole-tree counterpart to `verify-code-docs`, which checks the single `code/` gate."
metadata:
  tags: "drift-detection, regeneration, verification, release-gate"
  bundles: "crux-docs"
  risk_level: "low"
  routing_note: "Read-only. Runs every enrolled regenerator's `--dry-run` gate in one pass and reports one table — gate, verdict, drifted paths, and the regenerator that fixes it; never regenerates. The whole-tree counterpart to `verify-code-docs`. Emits a `lint` log op."
---

# Check Drift

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

Every derived artifact in this repo has a vendored regenerator and a `--dry-run` drift gate — the enrollment roster is the "regenerative outputs" table in the repo-root `CLAUDE.md`. This skill runs **all** of those gates in one read-only pass and reports a single table, so a developer or a release gate learns in one step whether any regenerated output has drifted from its source.

It is the whole-tree counterpart to `verify-code-docs`, which runs the one `code/` gate. Same contract, wider surface: **it never regenerates anything.** For every drifted or broken gate it names the regenerator the user runs to fix it.

**Read-only invariant.** This skill invokes each regenerator with `--dry-run` only. It writes nothing under the tree, `crux/catalog/`, `opencode/agents/`, `.codex/agents/`, or any source file. When it finds drift, it recommends the regenerator by name; the user (or a CI hook) decides whether to run it.

## When to use

- User says: "check drift", "is the tree in sync", "run the drift gates", "any drift?", "verify all regenerated outputs", "pre-release drift check".
- Before a release, before opening a PR, or after a change that touches any source of a regenerated output (ADR frontmatter, a skill's SKILL.md, an agent definition, the writing-rules block, `plugin.json`'s version).
- When `audit-docs` reports drift and you want the full regenerated-output picture in one table.

Do **not** use this skill for:
- Regenerating anything — this skill is read-only. Run the recommended regenerator yourself.
- The document-graph integrity walk (index ↔ files ↔ cross-references) — that is `audit-docs`. This skill checks only the regenerated-output drift gates.
- Fixing a single code-doc drift — `verify-code-docs` is the focused version for that one gate.

## The pipeline

Execute in order. Never reorder, never skip a gate.

### 0. Resolve per-repo configuration (.bionic.yml)

Run `python3 "${CRUX_PLUGIN_ROOT}/scripts/bionic-config.py"` from the repo root. On exit 1, STOP and surface the `{"error": ...}` payload. Use the returned `docs_dir` wherever a gate below needs `<docs_dir>` (default `bionic`).

### 1. Run every enrolled drift gate

Run each command below from the repo root. **Parse each command's stdout as JSON regardless of its exit code** — the exit code alone does not tell clean from drift. Collect a verdict per gate; do not stop on the first drift.

| Gate (output) | Dry-run command | Regenerator that fixes it |
|---|---|---|
| `crux/catalog/skills.json` + `agents.json` | `validate-catalog.py --dry-run` | `validate-catalog.py` |
| `docs/code/` | `extract-code-docs.py --dry-run --config <docs_dir>/manifest.yml` | `extract-code-docs.py --config <docs_dir>/manifest.yml` (skill `extract-code-docs`) |
| `<docs_dir>/arch/` spine | `derive-arch.py --dry-run --docs-dir <docs_dir>` | `derive-arch.py --docs-dir <docs_dir>` (skill `derive-arch`) |
| `<docs_dir>/adrs/summaries/` | `summarize-adrs.py --dry-run` | `summarize-adrs.py` |
| `<docs_dir>/adrs/doctrine/` | `compile-doctrine.py --dry-run` | `compile-doctrine.py` (skill `compile-doctrine`) |
| `opencode/agents/` | `generate-opencode-agents.py --dry-run` | `generate-opencode-agents.py` |
| `.codex/agents/` | `generate-codex-agents.py --dry-run` | `generate-codex-agents.py` |
| `<docs_dir>/adrs/lineage.md` | `generate-lineage.py --dry-run` | `generate-lineage.py` (skill `link-adr-graph`) |
| `<docs_dir>/adrs/index.md` | `generate-adr-index.py --dry-run` | `generate-adr-index.py` |
| `<docs_dir>/index.md` `## ADRs` rollup | `generate-index-rollup.py --dry-run` | `generate-index-rollup.py` |
| `README.md` version footer | `generate-readme-footer.py --dry-run` | `generate-readme-footer.py` |
| writing-rules block (3 surfaces) | `generate-writing-rules.py --dry-run` | `generate-writing-rules.py` |
| runtime-compatibility block (56 skills) | `generate-runtime-compat.py --dry-run` | `generate-runtime-compat.py` |
| `<tree>/CLAUDE.md` §10 routing-table region | `generate-routing-table.py --dry-run` | `generate-routing-table.py` |
| `<docs_dir>/adrs/reviews/index.md` | `generate-reviews-index.py --dry-run` | `generate-reviews-index.py` |

Invoke each via `uv run "${CRUX_PLUGIN_ROOT}/scripts/<name>" ...` from the repo root. This roster is the source of truth for what a derived artifact owes; if the repo-root `CLAUDE.md` roster grows a row, add its gate here.

### 1.A. Run the validation checks

A validation check is not a drift gate. It regenerates nothing, so it owns no row in the repo-root `CLAUDE.md` "regenerative outputs" roster, and enrolling it there would break the derived-artifact rule rather than keep it — a roster row promises a regenerator, and a validation check has none to promise. The roster count is unchanged by this section, and `audit-docs`'s CHK-DRIFT-1 still covers twelve outputs.

Run each check below from the repo root, after the drift gates and before the report.

| Check | Command | What a finding means | The fix |
|---|---|---|---|
| rule citations resolve | `lint-governs-references.py` | a `rule:<slug>` citation names a rule that does not exist or has been retired, or a ledger handle does not resolve | edit the citation, or restore the rule |

Invoke it as `uv run "${CRUX_PLUGIN_ROOT}/scripts/lint-governs-references.py"` with no flags. `--path` is its one flag: it narrows the scan to the files and directories you name, and passing none is what selects the default scope — the plugin source and the documentation tree. There is no `--dry-run`, because the linter never writes, so every run is already the read-only form.

**A citation failure is BROKEN, never DRIFT.** Regenerating fixes nothing here, because nothing is derived: a citation is authored text making a claim about a rule, and a stale claim is repaired by editing the claim. Report each finding in the same table as the gates, with BROKEN as its verdict and the path, line and token as the problem. A retired-slug finding names the rule that displaced it — carry that name into the report, because it is the fix.[^retired]

**An empty resolved scope is BROKEN, not a clean pass.** A check that scanned nothing has verified nothing. The linter exits nonzero and names the condition; report it as BROKEN and fix the scope. The same holds for its other refusals — a containment breach, a non-regular file, a file past the byte ceiling, a scope past the file ceiling, or a file that does not decode. Each is a refusal the check reports rather than a file it silently skips.

**Zero `rule:` citations inside a non-empty scope is clean.** The citation form is greenfield by the decision's own premise, so a pass over a scope that carries no citation yet is a real pass. Do not read it as a broken check, and never plant a citation to give the check something to find.

### 2. Classify each gate's verdict

Shared exit-code semantics (the same contract `verify-code-docs`, CHK-CODE-4, CHK-CAT-3, and CHK-ARCH-1 use): `0` clean, `1` drift or a validation error with valid JSON on stdout, any other non-zero with empty or unparseable stdout = crash (surface stderr, never a document finding). Map each gate to one verdict:

- **clean** — exit 0, JSON says no drift (`{"drift": false}` / `{"clean": true}` / `added=changed=removed=0` / empty diff), no `validation_errors`.
- **DRIFT** — exit 1 with a JSON drift payload (`{"drift": true, "paths": [...]}`, non-empty `added/changed/removed`, or a section diff). Capture the drifted paths. The fix is the regenerator in the table's third column.
- **BROKEN** — the JSON carries a non-empty `validation_errors` key (a malformed `governs` entry, a malformed reconciliation ledger, a schema error). Regenerating does NOT fix a validation error; the named input must be repaired first. Report the problems.
- **CRASH** — non-zero exit with empty or unparseable stdout (a missing dependency, an unhandled exception). Surface stderr; this is an environment problem, never a document finding.
- **N/A** — exit 0 with `"surface_absent": true` on the JSON. `generate-reviews-index.py` emits this when the tree carries no `<docs_dir>/adrs/reviews/` at all, which is every project that has not yet run a decision review. There is no derived artifact, so nothing can have drifted, and nothing was measured either. **Report it as N/A, never as clean** — a gate that scanned an absent surface has verified nothing, and recording it green is the vacuous-green shape this skill exists to prevent. The fix is not the regenerator: run `review-decisions` when a review is due.

**Warnings ride alongside, never change the verdict.** Read any top-level `warnings` key (`validate-catalog.py` emits one — the `models.yml` `verified:` staleness clock; `check-doctrine-reconciliation.py`'s S1 warn lane is similar). Surface it as WARNING beside the gate's verdict. A gate at exit 0 with a non-empty `warnings` list is a **clean pass worth reporting with its warning**, not a failure.

### 3. The one roster exception — `derive-arch.py --dry-run` exit 2

`derive-arch.py --dry-run` has a third lane the others do not: **exit 2, and stderr says which of two lanes it is** (copy the CHK-ARCH-1 distinction exactly).

- **Crash lane** — a missing dependency or unhandled exception. Verdict **CRASH**; surface stderr; fix the environment.
- **Deliberate refusal** — stderr names `StaleProjectionInput`. A spine file that projects a gated artifact declined because that artifact is not what its own regenerator produces. Nothing was written. This is **not a crash and not arch drift.** Verdict **REFUSAL**: report the capability failure, name the stale input from stderr, and recommend *that input's* own regenerator (`validate-catalog.py` for the skill catalog, `generate-adr-index.py` for the ADR index) followed by a re-derive. **Do NOT recommend re-deriving arch as the fix** — a re-derive reads the same stale input and refuses again.

### 4. Report one table

Print a single table with one row per gate and one row per validation check: **name · verdict (clean / DRIFT / BROKEN / CRASH / REFUSAL) · drifted paths (or the problem / stderr summary) · the command that fixes it**. Then a one-line summary: `N gates + M checks: C clean, D drift, B broken, X crash/refusal, W with warnings.`

For DRIFT rows, the recommended fix is the third-column regenerator. For BROKEN rows, the fix is repairing the named input, then re-running its regenerator — except a validation-check row, whose fix is editing the authored text the finding names, with no regenerator involved. For CRASH rows, the fix is the environment. For a REFUSAL row, the fix is the named upstream input's regenerator, then a re-derive.

### 5. Append to `<docs_dir>/log.md`

One `lint` op entry (the same op `verify-code-docs` uses — a targeted check, distinct from `audit`'s full walk). Newest entry at the top:

```
## [YYYY-MM-DD] lint | check-drift (C clean / D drift / B broken / X crash)
```

Body, 1–3 lines: the summary line, and for any non-clean gate its name plus the regenerator that fixes it. On an all-clean pass, log it anyway — a verification is an event:

```
## [YYYY-MM-DD] lint | check-drift (all N gates clean)
```

### 6. Hand-off

- If every gate is clean, report the all-clean table and stop.
- If any gate drifted, list the exact regenerator command per drifted gate and let the user run them. This skill never runs them.
- If a gate is BROKEN or CRASH or REFUSAL, surface the problem and the specific next action; a release must not proceed on a broken gate.

## Red flags — STOP and reconsider

- About to regenerate a drifted output "since I'm already here". NEVER — this skill is read-only. Recommend the regenerator; the user runs it.
- About to skip a gate because "that one never drifts". Run every gate every time. The roster is the contract.
- About to read a gate's exit code without parsing its stdout. The exit code says "ran", not "in sync". Parse the JSON.
- About to report a `derive-arch` exit 2 `StaleProjectionInput` as a crash or as arch drift. It is a deliberate refusal — recommend the upstream input's regenerator, not a re-derive.
- About to treat a `validation_errors` payload as drift and recommend the regenerator. A validation error is BROKEN — the named input must be repaired first; regenerating reproduces the same error.
- About to let a `warnings` key flip a clean gate to a failure. Warnings are surfaced beside the verdict and never change it.
- About to skip the log entry because "nothing drifted". A drift check is an event — log it.
- About to report a citation finding as DRIFT and recommend a regenerator. Nothing regenerates a citation. It is BROKEN, and the fix is editing the text that carries it.
- About to add the citation linter to the repo-root roster because it now runs here. It regenerates nothing, so a roster row would promise a regenerator that does not exist.
- About to call an empty resolved scope a clean pass. A check that scanned nothing verified nothing.
- About to plant a citation so the check has something to find. A scope with no citation yet is a pass; manufacturing work for a gate is how a gate stops meaning anything.

## Rationalization table

| Excuse | Reality |
|---|---|
| "One gate drifted; I'll just regenerate it to save a step." | This skill is read-only. Regenerating is a separate, explicit user action — mirror the verify/extract split `verify-code-docs` keeps. |
| "The exit code was 0, so the gate is clean." | Exit 0 means the run succeeded. Parse stdout: a `warnings` key or a validation payload can ride an exit you did not expect. |
| "`derive-arch` returned 2 — the environment is broken." | Read stderr. `StaleProjectionInput` is a deliberate refusal with an in-repo fix: regenerate the named upstream input, then re-derive. |
| "The catalog gate warned about a stale `verified:` date — that's a failure." | It is a WARNING that deliberately does not change the exit code. Report it beside a clean verdict. |
| "A validation error just means regenerate harder." | Regenerating reproduces the same bytes and clears nothing. Fix the malformed input the error names. |
| "The citation check found nothing, so it is not wired up." | A scope with no citation yet is a clean pass. Read the scanned-file count: zero files is BROKEN, zero citations across many files is clean. |
| "The citation linter runs in check-drift, so it belongs on the roster." | The roster enrolls derived artifacts, and a linter derives nothing. It is a validation check, reported in the same table and enrolled nowhere. |

## Common mistakes

- **Regenerating from inside this skill.** The split between checking and fixing is intentional — check-drift reports, the regenerator writes.
- **Stopping at the first drift.** Run every gate and report the full table; a release wants the whole picture, not the first failure.
- **Treating `derive-arch` exit 2 as one thing.** Two lanes share it — a crash and a `StaleProjectionInput` refusal. stderr says which; they take different fixes.
- **Letting warnings change a verdict.** A `warnings` key is informational and never flips clean to failing.
- **Recommending a re-derive for a `StaleProjectionInput` refusal.** The fix is the upstream input's regenerator, then a re-derive — never a re-derive alone.
- **Skipping the log entry on an all-clean run.** Verification with no drift is still a verification event — log it.
- **Reading a citation finding as drift.** A drift gate compares an output against its source. A validation check reads a claim. Only the first has a regenerator.
- **Reporting a linter refusal at exit 0.** A containment breach, a non-regular file, a bound breach or a decoding failure all exit nonzero. A refusal reported at exit 0 is the fail-open the check exists to close.

## See also

- `verify-code-docs` — the single-gate version: the read-only drift check for just the `code/` concern. This skill is that pattern applied to every enrolled regenerator.
- `audit-docs` — the document-graph integrity walk; its CHK-CAT-3 / CHK-CODE-4 / CHK-ARCH-1 run three of these gates individually, and CHK-DRIFT-1 folds in the rest.
- `compile-doctrine`, `derive-arch`, `link-adr-graph`, `extract-code-docs` — the skills that actually regenerate the outputs this skill only checks.
- The repo-root `CLAUDE.md` "regenerative outputs" table — the enrollment roster this skill's gate list mirrors. The validation checks of §1.A are deliberately absent from it.

[^retired]: `rule:retired-cite-fails-lint` — a retired slug fails the lint, and the failure names the rule that displaced it.
