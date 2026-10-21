---
name: author-promptbook
description: "Compatibility entry point that routes new tracked plans to cycle; preserves historical promptbook authoring documentation."
metadata:
  tags: "promptbooks, authoring, planning"
  bundles: "crux-docs"
  risk_level: "low"
  requires_access: "write-tree"
  triggers: "new promptbook | draft a plan-of-prompts | formalize a workflow"
  routing_note: "Compatibility alias for new cycle plans; historical authoring text is replay-only."
---

# Author Promptbook

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, OpenCode, and OMP (Oh My Pi). This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex, OpenCode, and OMP, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory (in OMP `bash`, `skill://<name>` resolves to the skill directory). In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, `.opencode/skills` in OpenCode (which also reads the singular `.opencode/skill`), and `.omp/skills` in OMP. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`; OMP uses `task`, `read`, `edit`, `write`, `bash`, `grep`, `glob`, `find`, `todo`, and `web_search` (where `read` also handles URLs and `skill://` URIs). Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode, `install-omp-agents` in OMP. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode and OMP use the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder` (in OMP, `scout` may also be used for reconnaissance alongside `wayfinder`). If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

## Historical compatibility boundary

New work uses `../cycle/SKILL.md`. Do not author new promptbooks or start another
run of an existing book. To inspect or finish an existing historical run under its
original contract, use `run-promptbook`; to archive it, use `archive-promptbook`.
Preserve its evidence and interpretation, and never convert it in place. Materially
changed work starts a new cycle referencing the predecessor.

## Promptbook index format

`docs/promptbooks/index.md` is rewritten from a walk of `docs/promptbooks/active/`,
`docs/promptbooks/runs/`, and `docs/promptbooks/archive/`, enumerating both `*.yaml`
and legacy `*.md` books:

```markdown
# Promptbooks

_Last updated: YYYY-MM-DD_

## Active (N)

| id | title | status | current_run | progress | tags | created_at |
|---|---|---|---|---|---|---|
| PB-0003 | <title> | active | null | 0/12 (0%) | <tags> | 2026-05-26 |

## Recent runs (last 20)

- `PB-0003/RUN-001` — in_progress — started 2026-05-26 — current prompt 4

## Archived (N)

- [[promptbooks/archive/PB-0001-...]] — completed 2026-05-12
```

`current_run` is `null` when no run has started.
