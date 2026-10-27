// The capability manifest of crux-opencode. Between the markers it is strict JSON, in crux-mods'
// convention, so a gate can parse it with a JSON parser: no comment, no single-quoted string and no
// trailing comma. Each group names what the files under crux-opencode use, and the source check
// compares the two in both directions:
// modules: the module specifiers tui.tsx imports. jsx_runtime: the package the JSX elements come
//   from; no import names it.
// host_members, type_members: per host package, the members tui.tsx uses and the types it imports.
// builtin_members: the named imports from each built-in module, and the members of a stat result and
//   of the process spawn returns.
// runtime_globals: each runtime-global form any file of the closure or the tests uses.
// context_members: each member of the host's context at its full path, with its kind: primitive (a
//   value), theme (a theme leaf), callable, pair (returns a reader and a setter), disposer (returns
//   a disposer) or void (returns nothing).
// render_input: per slot, the fields of the render input a component reads.
// callbacks: the functions the host or the process calls, and each one's parameter list.
// jsx: per JSX element, the props it may carry, and which of them take a colour. A colour prop that
//   holds an object names the one key it admits in colour_keys.
// events, slots, commands, panels, env_reads: the host events subscribed to (none), the slots filled,
//   the commands registered (by id, for the two page-turn commands, each naming its decision), the panels
//   they open and the environment names read.
// kit: the members of the test runner's kit that the test files use.
// launch: the launcher and its arguments, the places to look for uv, uv's arguments, the
//   allow-listed environment names and the constants among them, the reader script and its
//   arguments, and the timeout. Every array holds strings, and every value is a string, a number,
//   an array of strings or an object of the same kinds.
// BEGIN CAPABILITIES
export const capabilities = {
  "format_version": 1,
  "plugin": "crux-opencode",
  "modules": ["@opencode/plugin/tui", "node:child_process", "node:fs", "node:path", "node:url", "solid-js"],
  "jsx_runtime": "@opentui/solid",
  "host_members": ["@opencode/plugin/tui:Plugin.define", "solid-js:createEffect", "solid-js:onCleanup"],
  "type_members": [],
  "builtin_members": ["node:child_process:spawn", "node:child_process:spawn().kill", "node:child_process:spawn().on", "node:child_process:spawn().stderr.on", "node:child_process:spawn().stdout.on", "node:fs:readFileSync", "node:fs:realpathSync", "node:fs:statSync", "node:fs:statSync().isDirectory", "node:fs:statSync().isFile", "node:path:dirname", "node:url:fileURLToPath"],
  "runtime_globals": ["JSON.parse", "Object.keys", "Object.values", "Object.prototype.hasOwnProperty.call", "Array.isArray", "Array.from", "Number.isInteger", "Number.isFinite", "String.fromCharCode", "Math.max", "Math.min", "Math.floor", "Math.ceil", "Math.round", "String()", "new RegExp", "new Set", "new Map", "new Promise", "new Error", "extends Error", "new Date(1)", "import.meta.url", "setTimeout", "clearTimeout", "setInterval", "clearInterval"],
  "context_members": [
    {"path": "context.app.version", "kind": "primitive"},
    {"path": "context.location.directory", "kind": "primitive"},
    {"path": "context.theme.text.base", "kind": "theme"},
    {"path": "context.theme.text.muted", "kind": "theme"},
    {"path": "context.theme.text.feedback.error.base", "kind": "theme"},
    {"path": "context.theme.text.feedback.warning.base", "kind": "theme"},
    {"path": "context.theme.text.feedback.success.base", "kind": "theme"},
    {"path": "context.theme.text.feedback.info.base", "kind": "theme"},
    {"path": "context.theme.syntax.keyword", "kind": "theme"},
    {"path": "context.theme.syntax.type", "kind": "theme"},
    {"path": "context.theme.syntax.function", "kind": "theme"},
    {"path": "context.storage.memory", "kind": "pair"},
    {"path": "context.ui.slot", "kind": "disposer"},
    {"path": "context.ui.panel.open", "kind": "callable"},
    {"path": "context.ui.panel.current", "kind": "callable"},
    {"path": "context.ui.panel.close", "kind": "callable"},
    {"path": "context.ui.toast.show", "kind": "callable"},
    {"path": "context.keymap.layer", "kind": "void"}
  ],
  "render_input": {"session.composer.top": [], "session.panel": ["name", "width", "focused"]},
  "callbacks": {"setup": ["context"], "slot.band": [], "slot.panel": ["input"], "effect": [], "panel.cleanup": [], "layer.run": [], "memory.update": ["draft"], "child.spawn": [], "child.exit": [], "child.stdout.data": ["chunk"], "child.stderr.data": ["chunk"], "child.error": [], "child.close": ["code"]},
  "jsx": {
    "box": {"props": ["width", "flexDirection", "border", "borderStyle", "borderColor", "paddingLeft", "paddingRight"], "colour_props": ["borderColor"]},
    "text": {"props": [], "colour_props": []},
    "span": {"props": ["style"], "colour_props": ["style"], "colour_keys": ["fg"]},
    "b": {"props": ["style"], "colour_props": ["style"], "colour_keys": ["fg"]}
  },
  "events": [],
  "slots": ["session.composer.top", "session.panel"],
  "commands": ["crux-dashboard", {"name": "crux-dashboard-next", "decision": "ADR-0164"}, {"name": "crux-dashboard-previous", "decision": "ADR-0164"}],
  "panels": ["crux-dashboard"],
  "env_reads": ["HOME"],
  "kit": {"specifier": "claude-code/testing", "members": ["test", "expect", "expect().toBe", "expect().toBeDefined", "expect().toBeGreaterThan", "expect().toBeLessThanOrEqual", "expect().toBeNull", "expect().toContain", "expect().toEqual", "expect().toThrow", "expect().not.toBe", "expect().not.toBeNull", "expect().not.toContain", "expect().not.toEqual"]},
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
