---
name: log-work
description: "Use when finishing a unit of work, when the user says \"log work\", \"journal this\", \"record progress\", \"log this\", at end-of-day, or after any other crux skill completes a non-trivial side effect that warrants narrative context. Owns the append to `docs/journal/YYYY-MM.md`, the `journal` op entry in `docs/log.md`, and the rollup row in `docs/journal/index.md`. Supports a `--silent` mode for other skills to auto-log."
metadata:
  tags: "journal, work-log, narrative"
  bundles: "crux-docs"
  risk_level: "low"
  routing_note: "Categorization required."
---

# Log Work

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

The work journal and the operations log answer two different questions and **must not be conflated**:

| File | Question it answers | Voice |
|---|---|---|
| `docs/log.md` | *What did the skills do?* | Mechanical, third-person, terse. One line per op, no commentary. The audit chain. |
| `docs/journal/YYYY-MM.md` | *What did I (the agent / the human) figure out, attempt, get wrong, and learn?* | Narrative, first-person voice, reflective. The story behind the log. |

The log is a ledger. The journal is a retrospective. If a journal entry reads like a press release ("we did X, then Y, then Z; result: success"), it has failed its purpose — that content already lives in `log.md` and the git diff.

This skill owns the journal write, plus the corresponding pointer entry in `log.md`. Both files are append-only; this skill never edits past entries.

Core principle: **journal worthwhile work, log every operation**. Not every skill run becomes a journal entry; only ones a future human (or onboarding LLM) would want to know happened. Whether an invocation journals is controlled by the explicit `--journal` flag: in `--silent` mode it defaults OFF (the caller is log-only and passes its own op via `--log-op`); interactively it defaults ON. `--journal` gates BOTH the journal-file write and the journal-index rollup; the `docs/log.md` op entry is written either way (under `--log-op` when log-only, under `journal` when journaling).

### A journal entry must include reflection

The journal exists so future-you doesn't repeat past mistakes and can see WHY things ended up the way they did. A reflective entry beats a summary entry every time. Treat the body as four bands — name what applies, skip what doesn't:

1. **What we set out to do** — one sentence of intent. (The log already records the *what*; the journal records the *why we tried it this way*.)
2. **What didn't work the first time** — prompts that misfired, branches we backed out of, assumptions that turned out wrong, code we wrote then deleted. Specific. Naming the failure mode is what lets it not repeat.
3. **What surprised us** — claims in docs/ADRs/skills that turned out to be stale or wrong, behaviors of dependencies we hadn't seen before, edge cases we didn't model.
4. **What we'd do differently next time** — concrete, actionable, future-tense. (Distinct from a TODO — this is "if I started this work over, here's what I'd change about my approach.")

A success summary with no failure mode named is a signal that the entry skipped the reflection. Push back on yourself: name at least one thing that didn't work or surprised you, even on smooth runs.

The four bands above are what a human reads. The friction line is separate: a countable marker for band 2, "what didn't work the first time," present only when the unit of work had friction. It does not replace the prose in that band — it flags, for a machine, that this entry has friction worth counting.

What makes work worth journaling (vs. just logging): a decision was made; a non-obvious bug was diagnosed; a meaningful refactor was completed; a learning emerged that future-you will forget; a blocker was hit or cleared; a meeting produced a commitment. What is NOT worth journaling: routine file moves; tool invocations whose output is already captured elsewhere; ingests with no surprising content; index rebuilds.

## When to use

- User says: "log work", "journal this", "record progress", "log this", "make a journal entry", "what did we do today".
- End of a working session, before context-switch or end-of-day.
- After any skill in this suite completes a user-meaningful side effect (called with `--silent` and the category/subject pre-filled).
- When the user describes work they did outside Claude and wants it captured.

Do **not** use this skill for:
- The terse per-skill `log.md` entry — that's the skill's own responsibility (this skill appends its own `journal` entry to `log.md` but does not log on behalf of other skills).
- Operational drift detection — that's `audit-docs`.
- Decisions that warrant an ADR — call `propose-adr` instead, then optionally `log-work` once the ADR is filed.
- Editing past journal entries (refuse; the journal is append-only).

## Inputs

- Flags:
  - `--silent` — invoked by another skill. Skips user prompts ONLY; it does NOT by itself change journaling behavior (see `--journal`). Uses the passed `--category` / `--subject` / `--body`.
  - `--journal` — controls whether this invocation writes a **journal entry**. The default is **mode-dependent BY DESIGN**: `false` in `--silent` mode (a log-only caller owns its op and passes it via `--log-op`; `run-promptbook` once took this branch per advance and no longer logs an advance at all), `true` in interactive mode. When set, `log-work` writes BOTH `docs/journal/YYYY-MM.md` AND the `docs/journal/index.md` rollup row. When NOT set (log-only), it writes neither — only the `docs/log.md` entry (see `--log-op`).
  - `--log-op <op>` — the `docs/log.md` op for this invocation. **Required in log-only `--silent` mode** (i.e. `--silent` without `--journal`): the entry is written under the caller's own op (e.g. `promptbook`), NOT a misleading `journal |` entry. When `--journal` IS set, this is ignored and the op is `journal`. **Must be a valid op from the `docs/CLAUDE.md` §6 canonical enum** (e.g. `adr`, `promptbook`, `skill` — see §6 for the exhaustive list; `docs/CLAUDE.md` §6 is the single source of truth). **STOP on an invalid `--log-op` — do NOT fall back to a default.** A misspelled or out-of-enum op would write a BROKEN `docs/log.md` entry that `audit-docs` CHK-LOG-4 then flags. So if `--log-op` is not in the §6 enum: (1) emit an error to the caller naming the bad op and the allowed enum, (2) write **nothing** to `docs/log.md` (and nothing to the journal), and (3) return a non-zero exit. The caller (e.g. `run-promptbook`) surfaces the failure rather than silently committing a corrupt log line. This STOP is **distinct** from the `--category` fallback (step 1) — `--category` falls back to `misc` with a WARN; `--log-op` never falls back.
  - `--category <enum>` — required in silent mode. One of: `decision | implementation | bug | learning | blocker | refactor | meeting | review | misc`.
  - `--subject "<one-line>"` — required in silent mode.
  - `--body "<text>"` — optional in silent mode. Multi-line body, 1–10 lines.
  - `--refs "[[promptbooks/PB-0003-...]] [[research/sources/<slug>]] rule:<slug>"` — optional space-delimited refs: wiki-links (ADR pages, promptbooks, research sources, …) and `rule:<slug>` citations, where the slug is the part of a rule's governs handle after the slash (e.g. `rule:rule-slug-citation-token`). A citation must resolve in the tree's `docs/adrs/summaries/resolver.json`; cite a rule by its slug, never by its `ADR-NNNN/slug` ledger handle. Cite promptbooks **lifecycle-neutrally** (`[[promptbooks/PB-NNNN-<slug>]]`, no `active/`/`archive/` segment) so the Ref doesn't dangle when the book archives — the resolver keys on the `PB-NNNN` id across active-or-archive (see `docs/CLAUDE.md` §11).
- Non-silent (interactive): the skill asks the user for category and subject, drafts a body from session context, asks the user to confirm. `--journal` defaults to `true` here (an interactive `log-work` is a deliberate journaling act); the op is `journal`.

## The pipeline

Execute in order. Never reorder, never skip.

### 1. Validate inputs, then determine category and subject

**Validate `--log-op` before any write side effect** (log-only `--silent` mode only — when `--journal` is set the op is `journal`, no validation needed). Validation is performed against the `docs/CLAUDE.md` §6 canonical enum — reading `docs/CLAUDE.md` to consult §6 is required and permitted as part of this step. If `--log-op` is missing or not in the §6 enum (e.g. `adr`, `promptbook`, `skill` — §6 is the single source of truth; consult it for the full exhaustive list): **STOP** — emit an error to the caller (naming the offending value + the allowed enum), write nothing to `docs/log.md` or the journal, and return non-zero. **Never fall back to a default op** — a fallback would commit a BROKEN log line (CHK-LOG-4). This is the §6-enum **op** gate; it is separate from and stricter than the `--category` gate below.

- **Silent mode**: take category/subject from `--category` / `--subject` flags. Validate the category is in the journal-category enum (`decision | implementation | bug | learning | blocker | refactor | meeting | review | misc`); if not, **fall back to `misc` and surface a WARNING** (this is a WARN fallback — a wrong category still yields a valid, greppable entry, unlike a wrong `--log-op` which corrupts the op-enum). Note: the `--category` enum (journal categories) and the `--log-op` enum (§6 log ops) are **two different enums** — only `--log-op` triggers a STOP; `--category` always falls back.
- **Interactive mode**:
  - Propose a category from the session signal (e.g., recent ADR write → `decision`; recent test failure → `bug`; recent extract-code-docs run → not journal-worthy by default).
  - Propose a one-line subject (≤80 chars). Confirm with the user.
- Subject must be a single line. If it has a newline, take the first line and warn.

### 2. Compute timestamp

- `${TODAY}` = today's date in `YYYY-MM-DD`.
- `${NOW}` = current local time in `HH:MM` (24-hour). The entry heading uses `YYYY-MM-DD HH:MM`.
- `${MONTH}` = `YYYY-MM` portion of `${TODAY}`.

### 3. Ensure the monthly file exists

- Path: `docs/journal/${MONTH}.md`.
- If missing, create it with this header (and ONLY this header):

  ```markdown
  # Journal — ${MONTH}

  _Append-only. Newest entries at the top._
  ```

- If `docs/journal/` itself does not exist, **STOP** — `init-docs` was never run. Tell the user.

### 4. Compose the entry

Entry block, exact format:

```markdown
## [${TODAY} ${NOW}] <category> | <subject>

<body, 1–10 lines — see body-content rules below>

Friction: <one line naming a specific friction in this unit of work — omit if none>

Refs: <wiki-links and rule:<slug> citations, space-delimited, omit line if no refs>
```

Rules:
- The heading is greppable: prefix `## [`, date+time in brackets, single space, category from enum, ` | `, subject, no trailing punctuation.
- Body is 1–10 lines. Strip trailing whitespace. No trailing blank line inside the entry; a single blank line separates entries.
- **Body lines must not begin with `## [`** — the heading prefix is reserved for entry headings. Content that would start a body line with `## [` is rewritten or dropped; a line beginning with that prefix is regex-indistinguishable from a real heading and would corrupt the window-detection anchor used by `retrospective` and `cleanup-campsite`.
- The friction line is a single line beginning `Friction:` that names one specific friction in this unit of work. An entry carries at most one friction line. It is a body line and counts toward the 1–10 line budget. When both are present, it sits before the `Refs:` line.
- A `Friction:` line whose remainder is empty violates this rule. The way to record no friction is to omit the line; a bare `Friction: none` is the same violation, not a valid way to state there was none.
- `Refs:` line is omitted if no refs. If present, it's a space-delimited list of refs, each either a wiki-link `[[<path>]]` or a `rule:<slug>` citation. The journal is a dated record: cite `rule:<slug>` where a rule exists, and the ADR page (`ADR-NNNN`) only where the ADR carries no `governs` block.

**Body content — what to write (see the Overview §"A journal entry must include reflection"):**

A useful body explicitly answers at least two of the following, in the agent's voice (first-person if Claude is logging on its own behalf; user-voice if the user dictated):

- *What I tried first that didn't work* — name the failed approach or wrong assumption. Be specific (which file, which prompt, which command, which library behavior).
- *What surprised me* — a doc claim that was stale, a dependency behaving differently than expected, a test that passed for the wrong reason, a tool flag that didn't do what its name suggests.
- *Why the chosen path was the right one given what we now know* — not just what we did, but what made it correct relative to the alternatives we ruled out.
- *What I'd do differently if I started this over* — concrete, future-tense, distinct from a TODO.

Avoid:
- Summary-only bodies ("Did X. Did Y. Result: success."). Those belong in `log.md`. The journal should make the reader smarter, not just informed.
- Vague "learnings" without a named instance ("learned a lot about YAML"). Name the specific surprise.
- Marketing language. The journal is for honesty, not optics.

When the body is genuinely short (a small bug fix, a 5-minute decision), one well-chosen reflective sentence beats five lines of recap. Optimize for "future-you reads this in 6 months and says *oh right, that's what tripped us up*."

Add the friction line only when the work had friction; name the specific friction (see §4's grammar rule). Omit the line entirely when there was none — it is a marker for a machine to count, not a mandatory field, and it never substitutes for the prose above.

### 5. Prepend the entry to the monthly file

- The file's first ## heading is the newest entry. Insert the new block immediately after the header section (after the italicized append-only line and its trailing blank line) and before any existing entry.
- Never insert at the bottom.
- Never modify any pre-existing entry's content.

### 6. Update `docs/journal/index.md`

- Read the existing index. It is a table with columns `month | first entry | last entry | entries | top categories`.
- If a row for `${MONTH}` already exists:
  - `last entry`: set to `${TODAY}`.
  - `entries`: increment by 1.
  - `first entry`: leave unchanged unless missing/`—`, in which case set to `${TODAY}`.
  - `top categories`: recompute by scanning the monthly file (top 3 by count, comma-separated).
- If no row exists for `${MONTH}`: insert a new row in reverse-chronological position (newer months at the top) with `first entry = last entry = ${TODAY}`, `entries = 1`, `top categories = <category>`.
- Bump the `_Last updated:_` line to `${TODAY}`.

### 7. Append to `docs/log.md`

Single entry, prepended (newest first). **The op depends on whether this invocation journaled**:

**(a) Journaling invocation** (`--journal` set, or interactive) — op is `journal`:

```markdown
## [${TODAY}] journal | <category>: <subject>

Entry in `docs/journal/${MONTH}.md` at ${NOW}. ${refs_line_if_any}
```

**(b) Log-only invocation** (`--silent` without `--journal`) — op is the caller's `--log-op` value (NOT `journal`); no journal entry was written, so the body must not claim one:

```markdown
## [${TODAY}] <--log-op> | <subject>

<one-line body — what the caller did; no "Entry in docs/journal/..." line>. ${refs_line_if_any}
```

Both `journal` and the caller's `--log-op` value MUST be canonical ops from the `docs/CLAUDE.md` §6 enum (§6 is the single source of truth) — and for the log-only path the `--log-op` value was already validated in step 1 (an invalid op STOPped the run before reaching this step, so no BROKEN entry is ever written here). Body is one or two lines max.

### 8. Run the verification checklist

If any item fails, the entry was not written cleanly — roll back the journal write (the log entry stays; surface the inconsistency as a WARNING for `audit-docs`).

## Verification checklist

- [ ] `docs/journal/${MONTH}.md` exists.
- [ ] The new entry appears at the top (immediately after the file header, before any other `## [` heading).
- [ ] The entry heading matches the regex `^## \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] (decision|implementation|bug|learning|blocker|refactor|meeting|review|misc) \| .+$`.
- [ ] Body is 1–10 lines, no trailing blank line inside the block.
- [ ] **Body contains at least one reflective sentence** — a named failure, surprise, or "would do differently." **In interactive mode this is a hard gate:** a pure-summary body fails this check; loop back to §4's body-content rules and rewrite before committing. **In `--silent` mode this is informational (WARN), not blocking:** the caller pre-filled `--body` and there is no interactive loop to rewrite it, so surface a WARNING that the auto-logged entry reads as a summary (for the caller / a later human pass to improve) but still write the entry — do NOT STOP the caller's run on a thin reflective body. (Applies only when this `--silent` invocation actually journaled, i.e. `--journal` was set; a log-only `--silent` call writes no journal body and this check does not apply at all.)
- [ ] If a `Friction:` line is present, it is a single line, its remainder is non-empty, and it sits before the `Refs:` line when one is present.
- [ ] If `Refs:` is present, every ref is either a `[[...]]` wiki-link or a `rule:<slug>` citation — no bare path, no `ADR-NNNN/slug` ledger handle.
- [ ] `docs/journal/index.md` row for `${MONTH}` reflects the new entry (incremented count, updated last-entry date, recomputed top categories).
- [ ] `docs/journal/index.md` `_Last updated:_` is `${TODAY}`.
- [ ] `docs/log.md` has a new entry at the top. If this invocation journaled (`--journal` set, or interactive), the op is `journal`. If it was log-only (`--silent` without `--journal`), the op is the caller's `--log-op` value (e.g. `promptbook`) — NOT `journal`.
- [ ] No prior entry in any file was modified.

**The journal-write checks above (the `docs/journal/${MONTH}.md` and `docs/journal/index.md` items) apply ONLY when this invocation journaled**. In log-only `--silent` mode (no `--journal`), confirm the inverse: NO write occurred to `docs/journal/${MONTH}.md` or `docs/journal/index.md`, and the only write was the `docs/log.md` entry under `--log-op`.

## Red flags — STOP and reconsider

- About to write a journal entry whose body is a pure summary of changes ("did X, then Y, all green"). That's `log.md`'s job, not the journal's. Rewrite to name a failed first attempt, a surprise, or a lesson — even on smooth runs. If you genuinely can't name one, the work probably wasn't journal-worthy.
- About to edit a journal entry from a prior day. The journal is append-only — if a correction is needed, write a new entry referencing the old one.
- About to journal a routine skill operation (a clean ingest, an index rebuild). The op log already captured it; journaling is for *meaningful* work.
- About to journal in `--silent` mode without an explicit `--category`. Refuse; the caller must specify.
- About to use a category outside the enum. Map to `misc` and surface a WARNING — never invent a new category.
- About to append at the bottom of the monthly file. Always prepend.
- About to skip the `docs/log.md` op entry "to reduce noise". The log entry is the audit anchor; write it on every invocation (op `journal` when journaling, the caller's `--log-op` when log-only — never skipped).
- About to emit a `journal |` op entry for a log-only `--silent` call (no `--journal`). Wrong op — use the caller's `--log-op`; a `journal |` entry falsely implies a journal entry was written.
- About to fall back to a default op (or write the entry anyway) when `--log-op` is missing or outside the §6 enum. **NEVER.** STOP: emit an error to the caller, write nothing to `docs/log.md` or the journal, return non-zero. A bad op committed to the log is a CHK-LOG-4 BROKEN finding; surfacing the failure to the caller (e.g. `run-promptbook`, which then surfaces it) is correct. This is the ONE input that STOPs — `--category` always falls back to `misc`; `--log-op` never falls back.
- About to write the entry timestamp from wall-clock seconds when minute precision is the contract.
- About to combine multiple unrelated work items into one entry. One subject per entry.

## Rationalization table

| Excuse | Reality |
|--------|---------|
| "This was a small thing — not worth a journal entry." | Then it goes only into `log.md` by whatever skill ran. Journal entries are user-meaningful by definition; skip without guilt. |
| "I'll batch today's work into one end-of-day entry." | Batching loses time granularity and conflates categories. One entry per coherent unit. |
| "The subject is long — I'll squeeze it onto two lines." | The heading is greppable on one line. Truncate to ≤80 chars and move the rest to the body. |
| "I'll edit yesterday's entry to add today's follow-up." | Append-only. Write a new entry. Reference the old one in `Refs:`. |
| "The category enum doesn't fit — I'll add `planning`." | Pick the closest existing category. The enum is locked; expansion is an ADR-worthy decision. |
| "I'll skip the rollup update — `audit-docs` will fix it." | Audit catches drift; it shouldn't be the primary maintainer. Update the rollup on every write. |
| "The user said 'log this' — I'll write to `log.md` directly." | "Log this" maps to journal + log pointer. The user means human-readable; the op log is downstream. |
| "I'll auto-journal every skill operation." | Most operations don't warrant a journal entry. Only call `--silent` from a caller skill when the work is user-meaningful (ADR proposed, promptbook completed, large refactor closed). |
| "The work went smoothly — there's nothing to reflect on." | If you genuinely can't name a single failed first attempt, surprise, or thing you'd do differently, the work was either trivial (skip the journal entry) or you're not looking hard enough (there's always *something* — the prompt you initially mis-scoped, the wrong directory you started in, the dependency you assumed was there). Make the reflection specific. |
| "I'll lead with the bullet list of changes; reflection can go at the bottom." | The journal's load-bearing content is the reflection. Lead with what you tried and where it broke; the change list is downstream of that and partly captured by git anyway. |

## Common mistakes

- **Using `HH:MM:SS`**: the contract is `HH:MM`. Strip seconds.
- **Timezone confusion**: local time is fine for journal timestamps (humans read it). The `log.md` `journal` op uses date-only.
- **Empty `Refs:` line**: omit the line entirely when there are no refs. Don't write `Refs:` with nothing after.
- **Citing a rule by its ledger handle or by number**: the citation form is `rule:<slug>`. The `ADR-NNNN/slug` handle belongs to the projections, and a bare ADR page ref is right only when the ADR carries no `governs` block.
- **Sorting entries by category**: the file is chronological, not categorized. Top categories live only in the rollup.
- **Forgetting `top categories` in the rollup**: it's recomputed every write — don't carry stale values forward.
- **Writing two log entries (one `journal`, one `lint`) when category is `misc`**: there's no lint case here. One `journal` entry only.
- **Creating `journal/index.md` if it's missing**: don't auto-create — that's `init-docs`'s job. If missing, surface as a BROKEN finding for `audit-docs`.
- **Writing a journal entry without a body**: the heading alone is too thin. Require at least one body line; if interactive, prompt the user.
