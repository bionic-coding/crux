---
name: serve-llm
description: "FastAPI HTTP wrapper around the crux LLM caller and tracer. Exposes /health, /models, and /chat endpoints so non-Python clients (web UIs, curl, agent frameworks) can call the crux single-gateway LLM caller (OpenRouter). Use when you need programmatic HTTP access to crux. Not for interactive Python sessions — import `crux.core.llm_caller` directly instead."
disable-model-invocation: true
metadata:
  tags: "server, fastapi, http, infrastructure"
  bundles: "crux-infrastructure"
  risk_level: "low"
  requires_env: "OPENROUTER_API_KEY"
---

# Crux Server

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

- When a non-Python client (browser, agent runtime, another service) needs to
  call the crux LLM router over HTTP
- When you want a single in-process FastAPI app you can mount, embed, or
  deploy locally
- When you want chat traffic to be auto-traced into a crux session by
  passing `session_id`
- **Not** for: interactive Python work — use
  `from crux.core.llm_caller import call_model` directly (see
  `call-llm`)
- **Not** for: long-running orchestration (hypothesis loops, council). Those run
  in-process — see `council`

## File Locations

```text
crux/scripts/crux/server/
├── __init__.py            ← Re-exports the FastAPI `app`
└── crux_server.py     ← FastAPI app, request/response models, routes
```

FastAPI app object: `crux.server.crux_server:app` (also re-exported
as `crux.server:app`).

## Required env

The server itself needs no env vars. The underlying crux LLM caller reads one
key via `crux_env.require(...)` from `~/.crux/env`, and that key reaches every
model the server serves:

```env
OPENROUTER_API_KEY=sk-or-...
```

Manage it via the `crux-env` CLI (`crux-env` is a CLI/Python
module, not part of the skill catalog) — do NOT load dotenv files
manually.

## Usage

### Running it (PEP 723 launcher under `uv`)

`crux_server.py` needs FastAPI/uvicorn and pulls in the LLM router, which
imports `httpx` — bare `python3` dies with `ModuleNotFoundError`. Write a small launcher to a
temp `.py` starting with the standard PEP 723 header — **plus `fastapi` and
`uvicorn` for the server** — then run it with `uv`, which provisions the deps
into a cached, isolated environment:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "fastapi>=0.110", "uvicorn>=0.30"]
# ///
import sys
sys.path.insert(0, "${CRUX_PLUGIN_ROOT}/scripts")

import uvicorn

uvicorn.run("crux.server.crux_server:app", port=8000, reload=True)
```

Launch the server:

```bash
d=$(mktemp -d) && uv run "$d/serve_crux.py"
```

Write the launcher into a private per-run directory as above, never a fixed shared
path like `/tmp/serve_crux.py` — a predictable name in a world-writable directory is
a symlink hazard.

When writing the temp file, substitute `${CRUX_PLUGIN_ROOT}` (crux's portable
plugin-root name — in Claude Code, the value of `CLAUDE_PLUGIN_ROOT`; in Codex,
derived from this `SKILL.md`'s path per the Runtime compatibility note above)
with its actual value; in a source checkout substitute
the checkout's `crux/` directory. Without `uv` this fails at the shell
(`command not found: uv`, exit 127) — install uv (https://docs.astral.sh/uv/).

Health probe:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

List configured models:

```bash
curl http://localhost:8000/models
# {"models":["claude-opus-5","gemini-3.1-pro-preview", ...]}
```

Single-turn chat:

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "What is the capital of France?",
    "model": "gemini-3.1-pro-preview",
    "system": "You are concise.",
    "session_id": "demo_20260526"
  }'
# {"reply":"Paris.","model_used":"gemini-3.1-pro-preview"}
```

Multi-turn chat: include prior turns in `history` (most recent last; the
last 20 are kept):

```json
{
  "message": "And its population?",
  "history": [
    {"role": "user", "content": "What is the capital of France?"},
    {"role": "assistant", "content": "Paris."}
  ]
}
```

## Endpoints

| Method | Path     | Request shape                                              | Response shape                          |
|--------|----------|------------------------------------------------------------|-----------------------------------------|
| GET    | /health  | —                                                          | `{"status": "ok"}`                      |
| GET    | /models  | —                                                          | `{"models": [str, ...]}`                |
| POST   | /chat    | `{message, model?, system?, history?, session_id?}` (JSON) | `{"reply": str, "model_used": str}`     |

Notes:

- `model` defaults to `get_default_model("google_top")` (Gemini Pro by default).
- `history` is trimmed to the last 20 entries before prompt assembly.
- `session_id` (≤100 chars) routes a tracer event under `Phase.EXECUTION`
  with title `"Server Chat"`.
- CORS configuration is wide open — see the security callout under
  **Deployment notes** below.

## Deployment notes

> ⚠️ **SECURITY — CORS is wide open; do NOT deploy as-is.** The app sets
> `allow_origins=["*"]`, so **any** website can call your `/chat` endpoint
> from a user's browser and spend your provider API budget. This is fine for
> `localhost` development and nothing else. Before exposing the server beyond
> `localhost`, you **must** narrow `allow_origins` to the specific origins
> you trust (and add auth + a request budget — see below). Treat shipping the
> default `["*"]` CORS policy to any reachable host as a defect.

- **Local dev only.** No auth, no rate limiting, no TLS, wide-open CORS (see
  the callout above).
- No `Dockerfile`, no `pyproject` script entry, no production deployment
  story currently — launch via `uvicorn` for ad-hoc use.
- If exposing beyond `localhost`, put it behind a reverse proxy that handles
  auth + TLS, narrow `allow_origins` to trusted origins, and add a request
  budget.

## Implementation Notes

- Backing module: `crux/scripts/crux/server/crux_server.py`
- Depends on: `crux.core.llm_caller` (`call_model`,
  `list_available_models`, `get_default_model`) and `crux.core.tracer`
  (`get_tracer`, `Phase`)
- Related skills: `call-llm` for the underlying router;
  `trace-runtime-ops` for `session_id` semantics.
- Related CLI (not a skill): the `crux-env` CLI for environment
  bootstrap.
