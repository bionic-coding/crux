---
name: fix-directly
description: "Use when the user says \"just fix it\", \"fix it directly\", \"fix this directly\", \"no book for this\", \"this is small, skip the cycle\", or \"direct fix\", or when a defect passes the sizing test: its files can be named now, a failing test can be written before the fix, and no contract changes. The rung below the three cycle tiers: no promptbook, no council, no PB number. The contract is a failing test first, the smallest change that turns it green, the full suite plus the drift gates, one commit naming the defect, and a `log-work` entry so retrospectives still see the work. Escalates to `patch-cycle` when the fix needs a review gate, `iterate` when the diagnosis is open, and `dev-cycle` when a contract changes. A security label on a defect changes its priority, not its size."
metadata:
  tags: "promptbooks, workflow, fix, small-change, direct"
  bundles: "crux-docs"
  risk_level: "low"
  routing_note: "The rung below the three cycle tiers (§11.C): no book, no council, no PB number. A failing test first, the smallest green change, the suite and the drift gates, one commit, one `log-work` entry. Passes the sizing test or escalates to `patch-cycle` / `iterate` / `dev-cycle`. See `fix-directly/SKILL.md`."
---

# Fix Directly

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

A **direct fix** is the rung below the three cycle tiers. It exists because a defect too small
for `patch-cycle` used to have no name: the only alternatives were a five-prompt book with a
council, or an unrecorded edit. Both are wrong for a bug whose fix a careful engineer can name
before starting.

**No book, no council, no PB number.** The record of a direct fix is the commit, the regression
test, and one journal entry. That is enough for a retrospective to find it, and it is all the
process a bug of this size can carry without the process becoming the work.

**Three tiers stay three.** This skill neither relaxes a floor nor adds a fourth `cycle_kind`. A
direct fix is not a cycle; it authors no book and passes no cycle gate. `validate-promptbook.py`
never sees it.

## The sizing test

A defect is a direct fix when every answer is yes. One no routes it to a tier.

1. **Can you name every file the fix touches, now, before starting?** If not → `iterate`.
2. **Can you write the failing test before the fix?** A failing test is a complete reproduction
   of a bug. If the failure cannot be pinned in a test → `iterate` (the diagnosis is open).
3. **Does the fix change no contract?** No ADR, no schema, no rule in the tree's `CLAUDE.md`, no
   regenerated-output roster row. If it does → `dev-cycle`.
4. **Is one instance all the evidence there is?** One instance is a bug. A *class* earns a design
   when a second, independent instance exists — the same recurrence floor `retrospective` holds
   a skill proposal to. If you are designing for the class → stop, fix the instance, and record
   the class as an open question.
5. **Does the fix need an independent review gate?** A change under a signed or digest-bound
   surface, or one whose blast radius you want checked mechanically → `patch-cycle`.

**A security label does not change the size.** "Bypass", "forgery", and "injection" describe
what a defect *lets through*, not how large its fix is. A boolean guard that skips on one branch,
a `split("|")` that ignores an escape, and a regex over the wrong text are each a direct fix,
whatever the finding was called. The label sets priority; the sizing test sets the tier.

## When to use

- The user says: "just fix it", "fix it directly", "fix this directly", "no book for this",
  "this is small, skip the cycle", "direct fix".
- A review, an audit, or a run surfaced a defect that passes the sizing test.
- A cycle's verify module has already produced a diagnosis whose fix passes the sizing test, and
  the owner steps out of the cycle. Abandon the run first (`run-promptbook abandon`); the direct
  fix's commit message names the abandoned book.

Do **not** use this skill for:

- **Anything that fails the sizing test.** Route it to the tier the failing answer names.
- **A change to the cycle machinery itself** — `validate-promptbook.py`, the schemas, the
  templates, the cycle skills. Those are contracts; a direct fix to them is question 3 answered no.
- **A change under `docs/` that a skill owns** — an ADR transition, a brief transition, an
  observation transition, a sign-off. Use the owning skill.

## The pipeline

Execute in order.

### 0. Resolve per-repo configuration

Run `python3 "${CRUX_PLUGIN_ROOT}/scripts/bionic-config.py"` from the repo root. On exit 1,
STOP and surface the `{"error": ...}` payload. Use the returned `docs_dir` wherever this skill
says `docs/`.

### 1. Answer the sizing test in writing

Five answers, one line each, in the chat. A no ends the pipeline here and names the tier.

### 2. Write the failing test

One test per defect, in the existing test file for the module. Run it and confirm it **fails**
for the defect's reason, not for a typo. A test that passes before the fix proves nothing; a test
that fails for the wrong reason proves the wrong thing.

### 3. Make the smallest change that turns it green

Touch only the files named in question 1. If the fix wants a file you did not name, the sizing
test was wrong: stop and re-answer it.

### 4. Run the suite and the drift gates

The full test suite, then `check-drift`. Both green, or the fix is not done.

### 5. One commit, naming the defect

One commit per defect, or one commit for a set fixed together. The message names the defect and
its fix in one sentence each, names the regression test, and names any abandoned book.

### 6. One `log-work` entry

Invoke `log-work` with category `implementation` and a title beginning `fixed directly:`. The body
carries the defect, the fix, the test, and the sizing answers that kept it out of a tier. This
entry is how `retrospective` and `cleanup-campsite` see the work; skip it and the fix is invisible
to every process that mines finished work.

## Verification checklist

- [ ] The five sizing answers were written down before the first edit.
- [ ] The regression test failed before the fix, for the defect's reason.
- [ ] Only the files named in question 1 changed.
- [ ] The full suite and `check-drift` are green.
- [ ] One commit names the defect, the fix, and the test.
- [ ] One `log-work` entry with the `fixed directly:` title prefix exists.
- [ ] No book was authored, no counter moved, no council ran.

## Red flags — STOP and reconsider

- About to write "reproduction steps" instead of a failing test. The test is the reproduction.
- About to build a corpus of inputs to demonstrate a class. One failing input is the bug; the
  class is an open question until a second instance exists.
- About to widen the fix because the finding was called a bypass or a forgery. The label sets
  priority, not size. Re-answer the sizing test.
- About to edit a schema, a template, a `CLAUDE.md` rule, or a roster row. That is a contract
  change; question 3 said no.
- About to skip the `log-work` entry because the commit "is the record". The commit is invisible
  to the retrospective; the journal entry is not.
- About to fix directly inside a running cycle without abandoning it. The run's record would
  claim the cycle did the work. Abandon first.

## Rationalization table

| Excuse | Reality |
|---|---|
| "This is security-adjacent, so it deserves a cycle." | Security sets priority. The sizing test sets the tier. Answer it. |
| "Each of these bugs is really a class." | One instance is a bug. Fix it; record the class as an open question; design for it at the second instance. |
| "I'll skip the test — the fix is obvious." | The failing test is the reproduction and the proof. Without it the fix is a claim. |
| "The rigor is the product." | The rigor is proportional to the work. A council over a `split("|")` is ceremony, and ceremony has a cost the retrospective can see. |
| "It touched one extra file; close enough." | An extra file means the sizing test was wrong. Re-answer it; the extra file may be `patch-cycle`'s reason to exist. |
| "It's fixed and committed; the journal can wait." | The journal is the only surface that mines finished work. An unlogged fix never happened, as far as the retrospective knows. |

## See also

- `patch-cycle` — the tier above: five phases, a council, a review, a declared blast radius.
- `iterate` — the tier for a fix whose diagnosis is still open.
- `dev-cycle` — the tier for work that changes a contract.
- `log-work` — writes the one journal entry a direct fix owes.
- `check-drift` — the drift gates step 4 runs.
- `docs/CLAUDE.md` §11.C — the three cycle tiers this rung sits below.
