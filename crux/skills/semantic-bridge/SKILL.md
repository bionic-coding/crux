---
name: semantic-bridge
description: "Coordinate team verification: check existing probes before testing, then register results to avoid duplicate work."
user-invocable: false
metadata:
  tags: "reasoning, probes, deduplication"
  bundles: "crux-core"
  risk_level: "low"
---

# Crux Semantic Bridge

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->


## Scope and defaults (read first)

- **In-process only — no cross-process dedup.** A `SemanticBridge` lives in the memory of the process that created it. Probe/dissent registrations are visible only to teammates sharing that same `SemanticBridge` instance (the agent-team pattern below passes one instance around in-process). It does **not** persist to disk and does **not** deduplicate across separate processes, separate runs, or separate sessions — two independently-launched processes each get their own empty bridge and will happily re-run the same probe. If you need cross-process coordination, that is out of scope for this skill.
- **`answer_threshold` defaults to `0.5`.** This is the keyword-overlap score above which `is_answered_by_probe()` / `get_answer_for_dissent()` treat a prior probe as already answering a dissent. The default is `0.5` (a moderate-overlap match); raise it toward `1.0` to demand stronger keyword overlap before declaring a dissent answered, lower it to dedup more aggressively. Override it via `create_semantic_bridge(answer_threshold=...)` (shown below).

## File Location
```
crux/scripts/crux/semantic_bridge/
├── __init__.py
└── bridge.py    ← Core SemanticBridge
```

## Exports
```
From crux.semantic_bridge:
  SemanticBridge, BridgeStatistics, create_semantic_bridge
```

## Running it (PEP 723 driver under `uv`, NOT bare `python3`)

The bridge's own code is stdlib, **but** `import crux.semantic_bridge`
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

from crux.semantic_bridge import SemanticBridge
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

## Usage

```python
from crux.semantic_bridge import SemanticBridge

bridge = SemanticBridge()

# BEFORE running a probe — check first!
if bridge.is_answered_by_probe("dissent_auth_bypass_risk"):
    answer = bridge.get_answer_for_dissent("dissent_auth_bypass_risk")
    print(f"Already verified: {answer}")  # SKIP
else:
    result = run_my_probe()
    bridge.register_probe("probe_rbac_enforcement", result)
    bridge.register_dissent("dissent_auth_bypass_risk", dissent_obj)
```

## Agent Team Pattern
```
@backend-architect → registers "probe_rbac_enforcement"
@rag-engineer → checks bridge → already proven → SKIP
@frontend-lead → checks bridge → not proven → runs probe → registers
```

## Custom Keyword Groups

```python
from crux.semantic_bridge import create_semantic_bridge

bridge = create_semantic_bridge(
    keyword_groups={
        "auth": ["authn", "authz", "rbac", "permission"],
        "schema": ["schema", "type", "format", "structure"],
    },
    answer_threshold=0.5,
)
```

## Stats

```python
stats = bridge.get_stats()
report = bridge.get_coverage_report()
unanswered = bridge.get_unanswered_dissents()
```

## Rules
- ALWAYS check `is_answered_by_probe()` before new verification
- ALWAYS `register_probe()` after running any probe
- Use descriptive IDs: `probe_rbac_technician_wo_scoping` not `probe_1`
