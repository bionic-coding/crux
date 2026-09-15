---
name: author-runbook
description: "Generate an autonomous, multi-phase prompt runbook from a goal, with hypothesis testing and review checkpoints."
metadata:
  tags: "planning, runbook, autonomous, codegen"
  bundles: "crux-core"
  risk_level: "medium"
  triggers: "author a runbook | generate a runbook | build me a runbook | write an autonomous prompt runbook"
  requires_env: "OPENROUTER_API_KEY"
---

# Crux Runbook (Goal -> Autonomous Prompt List)

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->


## When to Use

- You have a goal that needs many ordered steps (feature build, refactor, research)
- You want truly hands-off execution: agent runs `PROMPT #1 ... #N` in order without check-ins
- You want every implement step paired with a crux review + apply + re-review + validate cycle
- **Not** for: a single question, a tiny edit, or anything where you'd prefer to micromanage

## File Locations

```
crux/scripts/crux/runbook/
├── __init__.py
├── __main__.py       ← Entry script (run via `uv run …/crux/runbook/__main__.py`)
└── runbook.py        ← Generator + CLI
```

The upstream `tools_registry.py` and bundled `decompose_goal.txt` prompt
template are NOT carried over in v0.1.0. The `--ai-plan` mode uses a
built-in prompt that calls Gemini directly via `crux.core.llm_caller`.

## Running it (under `uv`)

`runbook.py`'s `--ai-plan` mode calls the LLM router, which imports `httpx`,
so bare `python3` dies with `ModuleNotFoundError`. The entry script is PEP 723 self-describing —
run it directly with `uv`, which provisions the deps into a cached, isolated
environment:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/crux/runbook/__main__.py" "Your goal here" --ai-plan
```

`${CRUX_PLUGIN_ROOT}` is crux's portable plugin-root name (in Claude Code, the
value of `CLAUDE_PLUGIN_ROOT`; in Codex, derived from this `SKILL.md`'s path per
the Runtime compatibility note above); in a source
checkout (where it is unset) substitute the checkout's `crux/` directory.
Without `uv` this fails at the shell (`command not found: uv`, exit 127) —
install uv (https://docs.astral.sh/uv/). `--template-only` makes no LLM call,
but `uv run` is still the canonical invocation.

## Usage

```bash
# Recommended: AI-tailored plan, 75 prompts, explicit output dir
uv run "${CRUX_PLUGIN_ROOT}/scripts/crux/runbook/__main__.py" "Your goal here" \
    --ai-plan \
    --target-prompts 75 \
    --output logs/agent_runs/<RUN_ID>/runbook.md

# Read goal from a file instead of an arg
uv run "${CRUX_PLUGIN_ROOT}/scripts/crux/runbook/__main__.py" --file goal.md --ai-plan -n 80

# Deterministic (no LLM call) — useful for CI / offline
uv run "${CRUX_PLUGIN_ROOT}/scripts/crux/runbook/__main__.py" "Goal" --template-only --target-prompts 60
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| positional `goal` or `--file/-f` | — | Source of the GOAL (one is required) |
| `--target-prompts / -n` | `75` (clamped to 10-100) | Number of prompts to emit |
| `--output / -o` | `logs/prompt_lists/{YYYYMMDD_HHMMSS}_prompt_list.md` | Output markdown file |
| `--ai-plan` | off | Use Gemini Pro to tailor tasks to the goal (recommended) |
| `--template-only` | off | Deterministic scaffold, no API calls (mutually exclusive with `--ai-plan`) |

Default mode (neither flag set) emits the generic template scaffold and prints
a notice recommending `--ai-plan`.

## Required env

- `OPENROUTER_API_KEY` — one key, required for both halves of the work.
  `--ai-plan` needs it at generation time (the generator calls
  `call_gemini_pro`, which resolves through the gateway); without it the
  generator falls back to template-only and prepends a warning prompt. The
  generated prompts then invoke `council_vote` during execution, which reaches
  the same gateway with the same key.
- The key lives in `~/.crux/env` (see `crux-env`).

## Output

- Markdown file at `--output` (default
  `logs/prompt_lists/<timestamp>_prompt_list.md`).
- Structure:
  - Header: goal, mode, generated-at, total prompts, autonomy instructions
  - `## PROMPT #1: AUTONOMY SETUP` — RUN_ID + folder +
    `CRUX_TRACES_DIR` export
  - `## PROMPT #2: HYPOTHESIS LOOP (1 pass)` — runs the 3-testable-hypotheses
    discipline inline, writes hypotheses + test results
  - `## PROMPT #3: TASK PLAN` — execution checklist with the crux
    5-step cycle
  - Per task / cycle (5 prompts each): IMPLEMENT -> CRUX REVIEW ->
    APPLY FINDINGS -> VERIFY APPLIED -> RE-REVIEW + VALIDATE
  - Optional padding checkpoints (progress log, council sanity,
    constraints, artifact inventory)
  - Tail: full-system validation, final review, handoff summary,
    self-reflection JSON

### What "CRUX REVIEW" invokes

The **CRUX REVIEW** step in each per-task cycle (and the tail "Final
crux review") is a **multi-model council review of the task's
deliverable** — concretely, the generated prompt runs
`from crux.council import council_vote` (see `council`) against the
deliverable or diff and asks for failures-vs-constraints plus concrete
improvements; the RE-REVIEW step re-runs the same council pass to confirm
CRITICAL/HIGH findings are resolved. It is **not** `verify-code-docs` and
**not** `audit-docs` — those are docs-tree skills, whereas CRUX REVIEW
reviews the *work product* of the task regardless of type (code or non-code
deliverable). When the deliverable happens to be source code or generated
docs, the executing agent may *additionally* run `verify-code-docs` (code-doc
drift) or `audit-docs` (docs-graph integrity) as a complementary check, but
the runbook's own "CRUX REVIEW" prompt is the council pass.

Prompts are designed to be pasted whole into an AI agent (any agent runtime
that can execute shell + edit files — e.g. Claude Code, Cursor, or a similar
hands-off coding agent). The runbook tells the agent to set
`CRUX_TRACES_DIR=logs/agent_runs/<RUN_ID>/traces` so traces and
sessions co-locate inside the run folder.

## Implementation Notes

- Backing module: `crux/scripts/crux/runbook/runbook.py`
  (`MIN_PROMPTS=10`, `MAX_PROMPTS=100`, `DEFAULT_TARGET_PROMPTS=75`).
- `--ai-plan` calls only `call_gemini_pro`; failures (network, parse
  errors, missing key) degrade gracefully to template-only with a
  warning prompt.
- Cycle blocks always come in full 5-step units; padding never produces
  a partial Implement->Review->Apply->Verify->Re-review cycle.
