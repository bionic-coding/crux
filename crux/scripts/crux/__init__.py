"""
crux - Multi-model reasoning substrate for the crux toolkit.

Top-level capabilities, each imported from its own subpackage:

- council: Multi-model deliberation (sync + async).
- srde: Self-Resolving Dissent Engine.
- semantic_bridge: Probe/dissent/resolution linker.
- identity: Cross-agent learning store.
- task_planner: Goal decomposition into actionable tasks.
- runbook: Autonomous prompt-runbook generator CLI.
- knowledge: Domain knowledge injection with mental models.

The shared `core` subpackage holds the LLM caller, tracer, and dataclasses;
`crux.llm` names the same module (see `llm.py`).

# Nothing heavy at import time

Importing any subpackage runs this file first. A script that reads the
decision corpus imports `crux.arch.recover`, and its PEP 723 environment
carries no HTTP client. So this file imports no subpackage: the council
names below resolve on first attribute access (PEP 562), and only a caller
that actually uses the council or the LLM caller pays for httpx.

# crux_env reachability

The ported code reads API keys via `crux_env` (~/.crux/env). That
module lives one level up from this package at `scripts/crux_env.py`,
so we prepend that directory to sys.path here to make `import crux_env`
work regardless of how this package is installed. The bare `import` form
matches docs/AGENTS.md §13 and keeps the crux_env API single-import.
"""

import sys as _sys
from pathlib import Path as _Path

# Make `import crux_env` resolvable from inside this package. The env
# module lives in the parent `scripts/` directory.
_SCRIPTS_DIR = str(_Path(__file__).resolve().parent.parent)
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

_COUNCIL_NAMES = (
    "create_async_council",
    "AsyncCouncil",
    "AsyncVisualCouncil",
    "AsyncCouncilConfig",
    "council_vote",
    "quick_council",
)

__all__ = [*_COUNCIL_NAMES, "llm"]


def __getattr__(name):
    """Resolve the council re-exports and `crux.llm` on first use."""
    import importlib

    if name in _COUNCIL_NAMES:
        return getattr(importlib.import_module(".council", __name__), name)
    if name == "llm":
        return importlib.import_module(".llm", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
