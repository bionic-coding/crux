---
name: install-codex-agents
description: "Install or refresh Crux's ten Codex-native role agents in a target project's .codex/agents directory. Use when a Codex user asks to install Crux agents, enable the Crux architect/developer/reviewer roles, or refresh generated Codex role definitions after a plugin upgrade. Does not overwrite a conflicting role without --force."
disable-model-invocation: true
metadata:
  tags: "codex, agents, installation, roles"
  bundles: "crux-infrastructure, crux-docs"
  risk_level: "medium"
---

# Install Codex Agents

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

Codex reads custom subagents from `.codex/agents/*.toml`; it does not consume
Crux's Claude Code agent Markdown files. This skill generates the ten
namespaced Crux roles into the target repo:

`crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`,
`crux_developer`, `crux_historian`, `crux_librarian`,
`crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`.

The generated files are `crux-<role>.toml`. They preserve a target project's
unrelated `.codex/agents/*.toml` files. Read-oriented roles default to Codex's
`read-only` sandbox; writer roles default to `workspace-write`.

## Install

<!-- Provenance: this skill assumes the crux plugin is already installed in
Codex via `codex plugin marketplace add bionic-coding/crux` then `codex plugin add
crux@crux` (documented in install-docs-skills/SKILL.md). That CLI syntax is
an external Codex contract owned by OpenAI, not by crux — track it against
upstream, don't assume it. Verified 2026-07-09 against the official docs
(https://developers.openai.com/codex/plugins/build) and against the local
`codex plugin ... --help` for codex-cli 0.144.0, which accept the
`owner/repo` marketplace source and the `PLUGIN@MARKETPLACE` positional
(`crux@crux`) forms. -->

Codex provides this selected skill's absolute `SKILL.md` path in context. Let
`<skill-dir>` be its containing directory, then run the sibling installer from
the **target repository root**:

```bash
python3 <skill-dir>/scripts/install.py --repo-root "$PWD"
```

The first install writes the generated roles. A later run refuses if an existing
`crux-*.toml` file differs, so a locally modified role is never silently lost.
The installer also refuses fail-closed (never writing) if a `crux-*.toml` entry
is a symlink, so it can never clobber the link's target inside or outside the
repo; it likewise refuses if `.codex/agents/` resolves outside the repo root.
Review the diff, then refresh deliberately:

```bash
python3 <skill-dir>/scripts/install.py --repo-root "$PWD" --force
```

Start a new Codex thread after installation so the project-scoped custom agents
are loaded. Ask Codex to spawn a role by its namespaced identifier, for example
`crux_reviewer` or `crux_developer`.

## Verification

- [ ] `.codex/agents/` contains exactly the ten generated `crux-*.toml` files.
- [ ] Existing non-Crux agent files remain unchanged.
- [ ] The installer returned JSON with `written` and no unreviewed conflicts.
- [ ] A new Codex thread can see the `crux_*` agent names.

## Guardrails

- Do not hand-edit generated `crux-*.toml` files. Change `crux/agents/*.md` in
  the Crux source, regenerate, and refresh intentionally.
- Do not use `--force` to bypass a target project's local role changes without
  reviewing them first.
- Codex parent-session permission overrides can be broader than a role's default
  sandbox. The role prompt remains binding even when that occurs.
