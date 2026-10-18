---
name: cycle
description: "Plan, execute, resume, or inspect one development cycle. Use for major changes, minor changes, quick fixes, refactoring, and releases."
metadata:
  tags: "cycles, workflow, planning, implementation"
  bundles: "crux-docs"
  risk_level: "high"
  requires_access: "write-tree"
  triggers: "start a cycle | run the cycle | resume the cycle | cycle status | new dev cycle | iterate on this | quick fix | refactor this | release cycle"
  routing_note: "One undertaking with type-specific phases, bounded passes, independent review, and shared test evidence; no prompt minimum or repeated runs."
---

# Cycle

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

Read the resolved project's objectives and operational schema before work. Resolve
`docs_dir` through the config reader; never assume the directory is named `docs`.
Use `uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --help` for supported commands.
For command-specific options, append the subcommand and `--help`.
Read [commands.md](references/commands.md) when creating plans or recording evidence.

## Route through the lead

The main session dispatches cycle execution to commander. Commander owns the
cycle and delegates implementation to dev-lead; dev-lead assigns developer units.
Do not call developer directly from the main session or commander. Other entry
points use their designated lead: tend-garden uses night-gardener, architectural
planning uses architect, and documentation filing uses historian. If the required
role cannot be invoked, report the gap rather than silently assuming its identity.
Small tasks keep small plans and reviews while retaining lead accountability.

## Select the type

| Type | Scope | Phases | Maximum passes |
|---|---|---|---:|
| dev | Major changes; an approved IDR is required | Plan → Build → Test → Review → Reflect | 7 |
| iterate | Minor changes | Plan → Build → Test → Review → Reflect | 2 |
| refactor | Preserve functional behavior; improve structure or engineering efficiency | Plan → Build → Test → Review → Reflect | 7 |
| quick-fix | Small bounded corrections | Build → Test → Review → Reflect | 1 |
| release | Prepare and publish an authorized release | Plan → Release → Reflect | 2 |

Limits count the initial pass. No type has a prompt minimum. Quick-fix has slim
Test, Review, and Reflect phases. Capture its scope and success criteria without
inventing a Plan phase. Record constraints and verification with `plan-details`. A material decision or substantial planning changes its
type. Refactor records both unchanged behavior and the improvement to verify.
Functional changes require iterate or dev.

## Create or resume

Use `create` with type, title, goal, scope, acceptance criteria, implementer, and
test coordinator. The script allocates a single cycle record under
`<docs_dir>/cycles/<CYC-NNNN>/cycle.json` (with the configured artifact prefix).
Use `show` to inspect it. A status request reports state without advancing it.
Use `resume` for the same paused undertaking; never create another run of it.
Completed and abandoned cycles stay closed. Follow-up work gets a new cycle.

The schema and writer own record shape. Mutate through `cycle.py`; do not edit
phase, pass, history, evidence, or approval fields by hand. The `plan` and `task`
commands record work across all phases and preserve previous plans. Scope,
constraints, acceptance criteria, verification, and expected evidence must be
concrete enough to review. Tasks can evolve; retain the reasons.

The dev-lead delegates independent implementation units with explicit ownership and context.
Pass objectives, outcome, evidence, constraints, current phase/pass, approved
record revisions, and the relevant policy in every assignment. The commander
coordinates; a shell-capable historian executes cycle record mutations when
the commander cannot. A developer never reviews its own change.

Every developer dispatch includes the full base commit SHA, assigned paths,
result-file location, and integration owner. Commit prerequisites before dispatch.
The dev-lead owns worktree integration, verifies ancestry and changed paths,
integrates committed units, and obtains valid related-check evidence. Copying a
diff without accounting for its base, evidence, and integration is not completion.

## Execute the phases

- Plan: establish the outcome and tasks, select scrutiny, resolve material choices.
- Build: implement the plan. Do not hide test/review retries inside this phase.
- Test: use the shared evidence policy in [testing.md](references/testing.md).
  Compare observed behavior with acceptance criteria. A known acceptance failure
  returns immediately to Plan (Build for quick-fix), even if automated checks pass.
  Do not send a known blocking defect to Review merely to obtain the same finding.
- Review: commission independent review under [review.md](references/review.md).
- Release: follow the project's release procedure. Validate artifacts, obtain
  independent review before publication, confirm destination authorization,
  publish, and verify. Reuse valid correctness evidence. Do not blindly repeat
  an external action after a failure.
- Reflect: record delivered criteria, lessons, remaining work, and follow-up
  references. A few sentences suffice for quick-fix. Proposed process changes
  do not silently expand the cycle. Abandonment also requires reflection.
  Before completing, commit the intended changes and record their full SHA(s)
  using `completion`. Explain remaining uncommitted work. Only an actual user
  request to leave changes uncommitted permits `--exception`; quote that request
  with its context. The writer does not grant permission to invent an exception.
  After closing, commander has the final cycle bookkeeping committed, then reports
  both delivery and final-record commits. Do not leave a completed cycle uncommitted.

Record evidence, decisions, review, and reflection using their respective
commands, then `advance`. A command's success records a transition; it is not
proof that an agent performed the described work.

## Decisions

Every dev requires at least one IDR. Other types require an IDR for a material
implementation choice with alternatives or tradeoffs worth preserving. Council
must approve its exact revision before dependent implementation. Revised choices
need fresh approval; earlier reasoning stays readable and carries no authority.

Council may also advise on a decision. Consultation never implicitly approves
an IDR or ADR. Use the council runner and its configured mode. Lite dispatches native Apex
reviewers through the sealed prepare/ingest protocol; Standard and Strict use
gateway provider seats. Historical promptbook councils retain their original
gateway-only interpretation. Council deliberation rounds are distinct from cycle passes.

An ADR may originate from a direct request, whiteboarding, or inbox processing.
Inside a cycle, council must first justify creating an ADR. Only then draft it
and obtain separate council approval of its contents. Acceptance requires human
approval by default; `.bionic.yml` may set `adr.acceptance: council-only`.
An absent value means `council-and-human`. New-policy acceptance makes the rules
binding without promotion. Do not reinterpret historical provenance. Return to
Plan after the accepted architectural decision and reassess affected IDRs.
Use `cycle-council.py` and `decision-policy.py` help for approval and acceptance
operations, and attach their evidence through the cycle decision command.

## Return paths and stops

A blocking Test or Review finding returns to Plan; quick-fix returns to Build.
Release findings requiring replanning return to Plan. Use `return` to record
what improved, what remains unresolved, what will change, and why another pass
is justified. A pass can end early; it does not need to reach Review first.

Pause when progress stalls, the limit is exhausted, scope changes materially,
a decision needs owner input, an explicit pause applies, or new evidence
contradicts the premise. Report the blocker, evidence, and recommended next step.
Do not retry solely because passes remain. Additional passes require explicit
human approval recorded through `extend`; approval never disables the progress
rule. A type change preserves identity, history, and pass count and cannot
silently bypass an exhausted limit. Routine authorized work needs no per-step
permission. Publication, external sends, and other outward actions still need
applicable authorization.

## Progress and historical records

The record drives visualization: current phase/pass/limit, tasks, return reasons,
approval waits, and outcome. Use `visualize-cycle-progress.py --help` for its
reader interface. Do not substitute a percentage for the evolving plan.

Old promptbooks, snapshots, templates, and their validators are historical
compatibility surfaces. New work uses this skill. Existing in-progress legacy
runs may finish under their original contract; never convert them in place or
start a repeated legacy run. A materially changed legacy undertaking starts a
new cycle referencing its predecessor. Generic new plans also use cycles with
the type matching their work, rather than a newly authored promptbook.
