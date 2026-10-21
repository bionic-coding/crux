---
name: install-omp-agents
description: "Install, refresh, or check crux's OMP (Oh My Pi) role agents in the personal or specified project directory. Preserve conflicting roles."
disable-model-invocation: true
metadata:
  tags: "omp, agents, installation, roles"
  bundles: "crux-infrastructure, crux-docs"
  risk_level: "medium"
  requires_access: "write-host"
  triggers: "install omp agents | install crux agents for omp | refresh the omp agents"
---

# Install OMP Agents

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, OpenCode, and OMP (Oh My Pi). This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex, OpenCode, and OMP, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory (in OMP `bash`, `skill://<name>` resolves to the skill directory). In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, `.opencode/skills` in OpenCode (which also reads the singular `.opencode/skill`), and `.omp/skills` in OMP. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`; OMP uses `task`, `read`, `edit`, `write`, `bash`, `grep`, `glob`, `find`, `todo`, and `web_search` (where `read` also handles URLs and `skill://` URIs). Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode, `install-omp-agents` in OMP. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode and OMP use the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder` (in OMP, `scout` may also be used for reconnaissance alongside `wayfinder`). If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

## Overview

OMP (Oh My Pi) discovers task subagents from `~/.omp/agent/agents/*.md` (personal scope)
and `<repo>/.omp/agents/*.md` (project scope). When OMP loads `crux/agents/*.md` directly
from a Claude-dialect marketplace plugin, it strips the frontmatter `model` field and does
not parse Claude Code's `Agent(role)` tool syntax into `spawns`.

This skill projects the ten Crux roles into OMP's native agent Markdown format and installs
them into the active user's personal OMP agent directory (`~/.omp/agent/agents/`) by default:

`architect`, `brainstormer`, `commander`, `dev-lead`, `developer`,
`historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`.

Each generated `<role>.md` file sets `model` to `["@crux_<role_underscored>", "<resolved_openrouter_model>"]`
(so OMP users can customize per-role models in `~/.omp/agent/config.yml` `modelRoles` while
falling back to `crux/catalog/models.yml`), maps `effort` to `thinking-level`, sets
`read-summarize: false` on `wayfinder` and `librarian`, translates tool grants to OMP's
native tools (`read`, `grep`, `glob`, `find`, `edit`, `write`, `bash`, `task`, `todo`,
`web_search`) without redundant `Skill`/`WebFetch`/`SendMessage` wrappers, and projects
`Agent(role)` restrictions to `spawns` (allowing OMP's native `scout` alongside `wayfinder`).

## Install

Let `<skill-dir>` be the directory containing this selected `SKILL.md` (in OMP, `skill://install-omp-agents`).

Install for the active user (targets `~/.omp/agent/agents/`):

```bash
uv run <skill-dir>/scripts/install.py
```

Supply the current repository when you also want the health report to scan for
project-scoped `.omp/agents/` files that shadow a personal Crux role:

```bash
uv run <skill-dir>/scripts/install.py --project-context "$PWD"
```

Use project scope when the user requests repository-local agents (targets `<repo>/.omp/agents/`):

```bash
uv run <skill-dir>/scripts/install.py --repo-root "$PWD"
```

`--repo-root` and `--omp-home` are mutually exclusive. `--omp-home <path>` sets the
personal target to `<path>/agents` (supporting isolated tests and named OMP profiles).

### Check health without writing

```bash
uv run <skill-dir>/scripts/install.py --check --project-context "$PWD"
```

`--check` prints JSON and does not create the target. Its exit status is `0` when
`drift.status` and `installed.status` are `clean` and the shadow scan has no findings.
It returns `1` for managed drift, installed-state findings, or shadow findings. It
returns `2` for a configuration or environment error.

### Refreshing modified roles

If an existing Crux-managed `<role>.md` differs from the generated projection, the
installer exits `1` without writing. Review the reported diff and rerun with `--force`:

```bash
uv run <skill-dir>/scripts/install.py --force
```

## Verification

- [ ] Target directory (`~/.omp/agent/agents/` or `<repo>/.omp/agents/`) contains the ten `<role>.md` files.
- [ ] Existing non-Crux agent files in the target directory remain untouched.
- [ ] `install.py --check` exits `0` with `drift.status: "clean"` and `installed.status: "clean"`.
- [ ] OMP's `task` tool resolves and dispatches roles by their bare name (e.g. `architect`, `reviewer`, `wayfinder`).

## Guardrails

- Do not hand-edit the generated `<role>.md` files. Edit `crux/agents/*.md` in the Crux source, regenerate, and refresh with `--force`.
- The installer only touches the ten managed role filenames from the catalog roster. Unrelated custom agents in `~/.omp/agent/agents/` or `.omp/agents/` are left alone.
- Refuses fail-closed if any managed agent leaf is a symlink or if the target directory resolves outside the selected scope root.
