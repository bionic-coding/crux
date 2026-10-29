---
name: cycle-status
description: "Show cycle progress without changing it: one cycle, every cycle, the JSON document, or a view that redraws in a second terminal."
metadata:
  tags: "cycles, status, progress, read-only"
  bundles: "crux-docs"
  risk_level: "low"
  requires_access: "run-plugin-script"
  triggers: "show cycle status | what's the status of CYC-NNNN | where are the cycles | list the cycles | watch the cycle | show the cycle dashboard"
  routing_note: "Read-only. Runs `cycle.py status` and shows its output; never advances or edits a cycle. The bare phrase \"cycle status\" routes to `cycle`."
---

# Cycle Status

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, OpenCode, and OMP (Oh My Pi). This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex, OpenCode, and OMP, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory (in OMP `bash`, `skill://<name>` resolves to the skill directory). In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, `.opencode/skills` in OpenCode (which also reads the singular `.opencode/skill`), and `.omp/skills` in OMP. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`; OMP uses `task`, `read`, `edit`, `write`, `bash`, `grep`, `glob`, `find`, `todo`, and `web_search` (where `read` also handles URLs and `skill://` URIs). Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode, `install-omp-agents` in OMP. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode and OMP use the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder` (in OMP, `scout` may also be used for reconnaissance alongside `wayfinder`). If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->

## Run it

Run the status command and show its output to the user as printed:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" status            # every cycle
uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" status CYC-NNNN   # one cycle
```

Run it from the project root, or pass `--repo-root PATH` before `status`.

With no cycle named, it shows active cycles first, then the others by cycle number,
highest first, at most 60, followed by the queue. Name a cycle to see older ones.

Each cycle shows its type, pass and limit, current phase and status, elapsed time,
tasks, return reasons, approval waits, any pause reason and the recorded outcome.

## Options

- `--json` prints the machine-readable document that `visualize-cycle-progress.py --json` prints.
- `--watch SECONDS` clears the screen and redraws every SECONDS until Ctrl-C. Suggest it
  for a second terminal beside a session, for example while Codex or OpenCode runs a cycle:
  `uv run "${CRUX_PLUGIN_ROOT}/scripts/cycle.py" --repo-root PATH status --watch 5`.
  Do not start a watch inside the agent session; it runs until interrupted.

## Rules

- The command writes nothing. It never advances, pauses or edits a cycle; route those
  requests to `cycle`.
- Exit 0 means it printed the view. Exit 1 means the cycle identity is invalid or unknown.
  Exit 2 means an environment problem, such as no documentation tree; report its message.
- Report the output as printed. Do not summarize progress as a percentage.
