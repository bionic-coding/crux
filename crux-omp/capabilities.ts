// The capability manifest of crux-omp. Between the markers it is strict JSON, so tools/omp_gate.py
// can parse it with a JSON parser: no comment, no single-quoted string and no trailing comma. The
// gate also checks the source against it: only index.ts imports a host API, and the widget and
// status keys here are the ones index.ts writes.
// BEGIN CAPABILITIES
export const capabilities = {
  "format_version": 1,
  "extension_id": "crux-omp",
  "host": "omp",
  "entry": "index.ts",
  "label": "Crux dashboard",
  "events": ["session_start", "session_switch", "session_shutdown", "before_subagent_spawn", "tool_execution_start", "tool_execution_update", "tool_execution_end", "tool_result", "input"],
  "commands": ["crux-dashboard"],
  "ui_methods": ["setStatus", "setWidget", "notify"],
  "widgets": {"band": "crux-band", "panel": "crux-panel"},
  "status": "crux",
  "env_reads": ["HOME"],
  "launch": {
    "launcher": "/usr/bin/env",
    "launcher_args": ["-i"],
    "uv_locations": ["/opt/homebrew/bin/uv", "/usr/local/bin/uv", "{HOME}/.local/bin/uv", "{HOME}/.cargo/bin/uv"],
    "uv_args": ["run", "--offline", "--no-project", "--no-config", "--quiet"],
    "env_allow": ["HOME", "PATH", "UV_OFFLINE", "UV_NO_CONFIG", "UV_PYTHON_DOWNLOADS", "PYTHONDONTWRITEBYTECODE", "CRUX_NO_UV_REEXEC", "NO_COLOR"],
    "env_constants": {"PATH": "/usr/bin:/bin", "UV_OFFLINE": "1", "UV_NO_CONFIG": "1", "UV_PYTHON_DOWNLOADS": "never", "PYTHONDONTWRITEBYTECODE": "1", "CRUX_NO_UV_REEXEC": "1", "NO_COLOR": "1"},
    "env_derived": {"HOME": "env:HOME"},
    "scripts": {"visualize-run-progress": {"path": "scripts/visualize-run-progress.py", "args": ["--json", "--project-root", "{project_root}"]}},
    "timeout_ms": 10000
  }
} as const;
// END CAPABILITIES
