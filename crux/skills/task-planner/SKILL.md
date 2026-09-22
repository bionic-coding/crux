---
name: task-planner
description: "Break a complex goal into subtasks with dependencies, priorities, and acceptance criteria. Does not generate a prompt runbook."
metadata:
  tags: "planning, task-decomposition, gemini"
  bundles: "crux-core"
  risk_level: "medium"
  triggers: "plan this task | break this down | decompose this goal | make a task plan"
  requires_env: "OPENROUTER_API_KEY"
---

# Crux Task Planner

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->


## When to / NOT to Use

**Use when:**
- Decomposing a large, multi-part goal into structured subtasks before you start building — to surface dependencies, priorities, and acceptance criteria up front.
- You want a machine-readable `TaskPlan` (saveable / loadable JSON) to drive or track the work.

**Do NOT use when:**
- The work is a single edit, a one-shot question, or a task small enough to hold in your head — the Gemini call isn't worth it.
- You think a `TaskPlan` is a prerequisite for `author-runbook`. **It is not.** See below.

### Relationship to `author-runbook` (they do NOT chain)

`task-planner` and `author-runbook` are **independent planners that each call Gemini on their own** — the `TaskPlan` this skill produces is **not** consumed by the runbook generator. `author-runbook --ai-plan` calls Gemini afresh to draft its *own* task list and then wraps each task in the implement / review / apply / verify / re-review cycle; it does not read, load, or require a saved `TaskPlan`. So:
- Run `task-planner` when you want a structured plan to reason over or track against.
- Run `author-runbook` when you want a hands-off autonomous prompt list.
- Running both is fine but redundant on the planning step — each pays its own Gemini call; one's output never feeds the other.

## File Locations
```
crux/scripts/crux/task_planner/
├── __init__.py
└── task_planner.py    ← decompose_goal, Task, TaskPlan
```

The standalone runbook CLI ships separately as the `author-runbook`
skill (under `crux/scripts/crux/runbook/`); this skill owns only goal
decomposition.

## Exports
```
From crux.task_planner:
  TaskStatus, TaskPriority, Task, TaskPlan,
  decompose_goal, create_fallback_plan, save_plan, load_plan,
  gather_codebase_context
```

## Running it (PEP 723 driver under `uv`)

`task_planner.py` calls the LLM router, which imports `httpx`, so bare
`python3` dies with `ModuleNotFoundError`. Write your driver to a temp `.py` starting with the
standard PEP 723 header, then run it with `uv`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
import sys
sys.path.insert(0, "${CRUX_PLUGIN_ROOT}/scripts")

from crux.task_planner import decompose_goal
# ... your driver code
```

```bash
uv run /tmp/driver.py
```

Substitute `${CRUX_PLUGIN_ROOT}` (crux's portable plugin-root name — in Claude Code, the value of `CLAUDE_PLUGIN_ROOT`; in Codex, derived from this `SKILL.md`'s path per the Runtime compatibility note above) with
its actual value when writing the temp file; in a source checkout substitute
the checkout's `crux/` directory. Without `uv` this fails at the shell
(`command not found: uv`, exit 127) — install uv (https://docs.astral.sh/uv/).
See `council/SKILL.md` and `docs/AGENTS.md` §10.A for the canonical reference.

## Task Decomposition

Break a large goal into structured, prioritized subtasks:

```python
from pathlib import Path
from crux.task_planner import decompose_goal, save_plan, load_plan

plan = decompose_goal(
    goal="<your high-level goal here>",
    codebase_path=Path("apps/api/"),   # optional — provides codebase context
    tracer=None,                        # optional Tracer instance
)

for task in plan.tasks:
    print(f"[{task.priority.value}] {task.title}: {task.description}")
    print(f"  Dependencies: {task.dependencies}")
    print(f"  Acceptance: {task.acceptance_criteria}")

# Save/load plans
save_plan(plan, Path("logs/plans/my_plan.json"))
loaded = load_plan(Path("logs/plans/my_plan.json"))
```

### Task dataclass fields
- `id` — short unique identifier
- `title` — task title
- `description` — what needs to be done
- `priority` — `TaskPriority` enum (CRITICAL, HIGH, MEDIUM, LOW)
- `status` — `TaskStatus` enum (PENDING, IN_PROGRESS, COMPLETED, BLOCKED, CANCELLED)
- `dependencies` — list of task IDs this depends on
- `estimated_hours`, `files_involved`, `acceptance_criteria`

## From Goal to Runbook (separate path, not a handoff)

If you want an autonomous prompt list instead of a `TaskPlan`, call
`author-runbook` directly — it does **not** consume this skill's `TaskPlan`:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/crux/runbook/__main__.py" "<goal>" --ai-plan --target-prompts 75 \
    --output logs/agent_runs/<RUN_ID>/runbook.md
```

`author-runbook` calls Gemini to draft its **own** plan from the same goal
string, then wraps each task in the implement / review / apply / verify /
re-review cycle. The two planners run independently and each pays its own
Gemini call; the `TaskPlan` from `decompose_goal()` is not an input to the
runbook generator. See "When to / NOT to Use" above.
