---
name: iterate
description: "Compatibility alias: route iterate requests to the unified cycle workflow with type iterate."
metadata:
  tags: "promptbooks, workflow, cycle, iterate, fix"
  bundles: "crux-docs"
  risk_level: "low"
  requires_access: "write-tree"
  triggers: "iterate on X | start an iterate cycle | iterate-cycle for X | remediate X | fix X with rigor"
  routing_note: "New work uses cycle with type iterate; no promptbook is allocated."
---

# iterate compatibility alias

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, OpenCode, and OMP (Oh My Pi). This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex, OpenCode, and OMP, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory (in OMP `bash`, `skill://<name>` resolves to the skill directory). In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, `.opencode/skills` in OpenCode (which also reads the singular `.opencode/skill`), and `.omp/skills` in OMP. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`; OMP uses `task`, `read`, `edit`, `write`, `bash`, `grep`, `glob`, `find`, `todo`, and `web_search` (where `read` also handles URLs and `skill://` URIs). Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode, `install-omp-agents` in OMP. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode and OMP use the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder` (in OMP, `scout` may also be used for reconnaissance alongside `wayfinder`). If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

For new work, read `../cycle/SKILL.md` and use type `iterate`.
There is no prompt minimum and no new promptbook or numbered run.

For an explicitly named existing promptbook, use `run-promptbook` only to inspect
or finish that historical run under its original contract. Preserve its records;
never convert it in place or start another run of a completed book.
