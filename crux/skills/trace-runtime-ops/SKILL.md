---
name: trace-runtime-ops
description: "Instrument crux workflows with structured logs and Markdown traces of model calls and reasoning phases."
user-invocable: false
metadata:
  tags: "tracing, logging, observability"
  bundles: "crux-core, crux-docs"
  risk_level: "low"
---

# Crux Semantic Tracer

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->


## When NOT to Use
- **One-shot utility calls.** A single `call-llm` lookup, a lone probe, or a throwaway one-liner does not need a tracer — instrumenting it adds a session dir and markdown files for nothing. Trace *multi-step* reasoning (hypothesis loops, councils, agent-team workflows), not isolated utility calls.
- **Per-step in a tight loop** where the trace would be pure noise.

The previous guidance to "ALWAYS get a tracer at session start" is too aggressive: tracing earns its keep when there's a *reasoning trajectory* worth reconstructing (loops, dissents, self-reflections). For a one-shot call there's no trajectory, so skip it.

## File Locations
```
crux/scripts/crux/core/
└── tracer.py         ← Tracer, TraceEntry, get_tracer, log_reasoning

logs/
├── semantic_tracers/traces/   ← Default trace output
│   └── {trace_session_id}/
│       ├── 001_council.md
│       ├── execution_log.md
│       └── README.md
└── agent_runs/{run_id}/traces/ ← Colocated traces (via CRUX_TRACES_DIR)
```

## Exports
```
From crux.core:
  Tracer, TraceEntry, ModelCall, Phase, SelfReflection,
  get_tracer, log_reasoning
```

## Running it (PEP 723 driver under `uv`)

Importing `tracer.py` executes `crux/scripts/crux/__init__.py`, which loads
the LLM router and its `httpx` HTTP client — bare `python3` dies with
`ModuleNotFoundError`.
Write your driver to a temp `.py` starting with the standard PEP 723 header,
then run it with `uv`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
import sys
sys.path.insert(0, "${CRUX_PLUGIN_ROOT}/scripts")

from crux.core import get_tracer
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

## Getting a Tracer

```python
from crux.core import get_tracer

# Get or create a tracer for this session
tracer = get_tracer()
```

## Logging Model Calls

```python
from crux.core import Tracer, ModelCall, get_tracer

tracer = get_tracer()

# Log an LLM call
tracer.log_model_call(ModelCall(
    model="claude-opus-5",
    prompt="Analyze this code...",
    response="The code has...",
    tokens_in=500,
    tokens_out=1200,
))
```

## Logging Reasoning Phases

```python
from crux.core import Phase

# Log a reasoning phase
tracer.log_phase(Phase(
    name="hypothesis_generation",
    description="Generating 3 hypotheses for loop 1",
    result="Generated H1, H2, H3",
))
```

## Logging Self-Reflections

```python
from crux.core import SelfReflection

tracer.log_reflection(SelfReflection(
    future_hints=["Check page 5 for continuation of table"],
    patterns_noticed=["All IDs use UUID v4 format"],
    warnings=["Don't call external API in test mode"],
    incomplete_work=[{"what": "Reranker tuning", "next_step": "Benchmark"}],
))
```

## Quick Logging Helper

```python
from crux.core import log_reasoning

# One-liner for simple reasoning traces
log_reasoning(
    phase="implementation",
    detail="Built auth middleware with JWT validation",
    confidence=0.75,
)
```

## Trace Entries

```python
from crux.core import TraceEntry

entry = TraceEntry(
    timestamp="2026-01-17T14:30:22",
    type="model_call",
    content={...},
)
```

## Passing Tracer to Other Tools

Many crux functions accept an optional `tracer` parameter:

```python
from crux.core import get_tracer
from crux.task_planner import decompose_goal

tracer = get_tracer()

# Task decomposition with tracing
plan = decompose_goal(goal="...", tracer=tracer)
```

## Trace Colocation (recommended for autonomous runs)

Force traces into a run folder:

```bash
export CRUX_TRACES_DIR="logs/agent_runs/<RUN_ID>/traces"
```

## Rules
- Get a tracer at the start of any **multi-step** workflow (loops, councils, agent teams) — skip it for one-shot utility calls (see "When NOT to Use")
- ALWAYS pass the tracer to crux functions that accept it once you have one
- ALWAYS log self-reflections at the end of each loop
- Traces are markdown files — human-readable by design
