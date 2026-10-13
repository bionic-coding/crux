// The capability manifest of crux-mods: every event the mods hook, every call
// they make on `$`, every environment variable they read, and the one process
// they may start. The release gate compares this object with what
// `claude plugin validate --strict --json` lists and refuses on any difference.
// The object between the markers is strict JSON: the gate parses it with a
// JSON parser, so it carries no comment, no single quote and no trailing comma.
//
// claude_code: min is the first Claude Code with strict validation of mods. There
// is no max: the gate refuses a newer Claude Code only when its validator listing
// does not parse or differs from this manifest. Each recorded output under
// tests/fixtures/validator/ keeps the parser tested against a real listing.
// events: behaviour is observe, draw or command-text (no decision needed: the hook
// changes nothing Claude Code does, and command-text answers only a command this
// module registers), or a behaviour-changing value that names an Accepted decision.
// gating and has_catch repeat what the validator lists for a hook whose failure
// can stop the event; tools/mods_gate.py compares both.
// launch.timeout_ms: the reader takes about 0.3 s on a tree of 144 runs; 10 s
// leaves room for a cold uv cache, and the reader stops itself at 8 s.
// BEGIN CAPABILITIES
export const capabilities = {
  "format_version": 1,
  "plugin": "crux-mods",
  "claude_code": {"min": "2.1.287"},
  "events": [
    {"event": "session.start", "behaviour": "observe", "decision": null},
    {"event": "tool.call", "behaviour": "observe", "decision": null, "gating": true, "has_catch": false},
    {"event": "ui.render{component=AbovePrompt}", "behaviour": "draw", "decision": null},
    {"event": "ui.render{component=Pane}", "behaviour": "draw", "decision": null},
    {"event": "command.run{command=crux-dashboard}", "behaviour": "command-text", "decision": null}
  ],
  "calls": ["$.agent.list", "$.clock.after", "$.clock.every", "$.command.register", "$.env.get", "$.fs.read", "$.fs.stat", "$.process.run", "$.session.root", "$.ui.invalidate", "$.ui.open", "$.ui.resolve"],
  "env_reads": ["CLAUDE_CONFIG_DIR", "DYLD_FALLBACK_FRAMEWORK_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "DYLD_IMAGE_SUFFIX", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_ROOT_PATH", "DYLD_VERSIONED_FRAMEWORK_PATH", "DYLD_VERSIONED_LIBRARY_PATH", "HOME", "LD_AUDIT", "LD_LIBRARY_PATH", "LD_PRELOAD"],
  "env_writes": [],
  "launch": {
    "launcher": "/usr/bin/env",
    "launcher_args": ["-i"],
    "uv_locations": ["/opt/homebrew/bin/uv", "/usr/local/bin/uv", "{HOME}/.local/bin/uv", "{HOME}/.cargo/bin/uv"],
    "uv_args": ["run", "--offline", "--no-project", "--no-config", "--quiet"],
    "env_allow": ["HOME", "PATH", "UV_OFFLINE", "UV_NO_CONFIG", "UV_PYTHON_DOWNLOADS", "PYTHONDONTWRITEBYTECODE", "CRUX_NO_UV_REEXEC", "NO_COLOR"],
    "env_constants": {"PATH": "/usr/bin:/bin", "UV_OFFLINE": "1", "UV_NO_CONFIG": "1", "UV_PYTHON_DOWNLOADS": "never", "PYTHONDONTWRITEBYTECODE": "1", "CRUX_NO_UV_REEXEC": "1", "NO_COLOR": "1"},
    "env_derived": {"HOME": "env:HOME"},
    "loader_vars": ["LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FALLBACK_FRAMEWORK_PATH", "DYLD_VERSIONED_LIBRARY_PATH", "DYLD_VERSIONED_FRAMEWORK_PATH", "DYLD_ROOT_PATH", "DYLD_IMAGE_SUFFIX"],
    "scripts": {"visualize-run-progress": {"path": "scripts/visualize-run-progress.py", "args": ["--json", "--project-root", "{project_root}"]}},
    "timeout_ms": 10000
  }
} as const;
// END CAPABILITIES
