---
name: agent-identity
description: "Cross-agent learning system. Each agent creates a persistent identity (GUID), learns from sessions, shares knowledge, and finds domain experts. Use at START of agent team sessions to create identity + learn from experts, and at END to extract learnings for future agents. Substrate skill: typically called by `dev-cycle` / `author-runbook` agent teams as part of their session lifecycle; call directly only for custom multi-agent wiring (hand-rolling an agent team outside those orchestrators)."
user-invocable: false
metadata:
  tags: "identity, learning, agent-teams"
  bundles: "crux-core"
  risk_level: "low"
---

# Crux Identity (Cross-Agent Learning)

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->


## File Locations
```
crux/scripts/crux/identity/
├── __init__.py
└── identity.py     ← KnowledgeStore, get_or_create_identity, Learner

~/.crux/identity/        ← User-extensible storage (default base_dir)
  └── {guid}/identity.json   ← Persisted identities
```

The storage base honors `CRUX_HOME` if set (consistent with
`crux-env`); otherwise defaults to `~/.crux/identity/`.

## Exports
```
From crux.identity:
  Identity, KnowledgeStore, Learner, get_or_create_identity,
  Hint, Pattern, Warning_, DEFAULT_REGISTRY_DIR
```

## Running it (PEP 723 driver under `uv`, NOT bare `python3`)

This skill's own code is mostly stdlib, **but** `import crux.identity`
triggers `crux/scripts/crux/__init__.py`, which eagerly imports the
router (`httpx`) — so bare `python3` dies with `ModuleNotFoundError: No module
named 'httpx'`. Write your driver to a temp `.py` starting with the standard
PEP 723 header, then run it with `uv`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
import sys
sys.path.insert(0, "${CRUX_PLUGIN_ROOT}/scripts")

from crux.identity import get_or_create_identity
# ... your driver code
```

```bash
uv run /tmp/driver.py
```

Substitute `${CRUX_PLUGIN_ROOT}` (crux's portable plugin-root name — in Claude Code, the value of `CLAUDE_PLUGIN_ROOT`; in Codex, derived from this `SKILL.md`'s path per the Runtime compatibility note above) with
its actual value when writing the temp file; in a source checkout substitute
the checkout's `crux/` directory. Without `uv` this fails at the shell
(`command not found: uv`, exit 127) — install uv (https://docs.astral.sh/uv/).
See `council/SKILL.md` and `docs/CLAUDE.md` §10.A ("Async-first rule") for the
canonical reference.

## Session Start: Create + Learn

```python
from crux.identity import (
    KnowledgeStore, get_or_create_identity, Learner
)

store = KnowledgeStore()  # defaults to ~/.crux/identity/
me = get_or_create_identity(
    store=store,
    name="<YOUR-ROLE>",
    purpose="<describe what this agent does>",
)

learner = Learner(store)
for domain in ["<relevant>", "<domains>", "<here>"]:
    expert = store.find_expert(domain)
    if expert:
        result = learner.learn_from(me, expert.guid, domains=[domain])
        print(f"Learned {result['hints_learned']} hints from {expert.name}")
```

## Session End: Extract Learnings

```python
from pathlib import Path

learner.extract_learnings_from_session(
    identity=me,
    session_dir=Path("logs/agent_runs/<RUN_ID>"),
)
# Future agents calling store.find_expert("rag") will find YOUR learnings
```

## What Gets Stored
- **hints** — specific actionable knowledge with context and importance
- **patterns** — recurring observations with confidence scores
- **warnings** — things to avoid with severity
- **domains** — areas of expertise
- **capabilities** — skill levels per domain
- **children** — spawned sub-identity GUIDs
- **learned_from** — other identities this one learned from

## Agent Teams: Every Teammate Gets an Identity
At session end, an architect/lead agent learns from ALL identities.
Knowledge compounds across sessions — the team gets smarter.
