---
title: Runtime state
read_when: Reading or changing `~/.crux/` state, its env file or the `crux-env` interface
sections:
  - "§13"
---

# Runtime state

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §13.2`, resolves to this file.

## 13. crux runtime state (`~/.crux/`)

`crux` stores user-scoped secrets and env vars outside the repo, under `~/.crux/` — secrets must never live in a repository (commit risk; lost on fresh clone; doesn't compose across projects). The `crux-env` CLI manages this directory; the `crux_env` Python module reads from it.

`CRUX_HOME` env var overrides `~/.crux` (used in tests).

### 13.1 `~/.crux/` layout

```
~/.crux/
  env                 KEY=value file. mode 0600.
  required.yml        Per-project required/optional env vars manifest. mode 0600.
  secrets/            Optional per-service file-form credentials (e.g., service-account JSON). mode 0700 dir, 0600 files.
  log/
    crux-env.log  Append-only op log. mode 0600. NO VALUES recorded — only key names.
```

### 13.2 `~/.crux/env` file format (locked)

- One `KEY=value` per line.
- Keys match `^[A-Z][A-Z0-9_]*$` (ASCII uppercase + digits + underscore; must start with letter). Non-matching lines outside comments/blanks are a parse error.
- Values are unquoted by default. If a value contains a space, `#`, or any whitespace, it MUST be wrapped in double quotes: `KEY="my value with #hash"`. Inside double quotes, `\"` escapes a literal quote and `\\` escapes a literal backslash. No other escape sequences are recognized — `\X` for unrecognized X is a parse error (the parser rejects loudly rather than silently passing it through).
- No whitespace permitted between `=` and the value; leading whitespace before a key is also a parse error. Surface format mistakes loudly rather than guessing.
- `#` to end-of-line is a comment, OUTSIDE of double-quoted values.
- Empty values are not stored. `crux-env set KEY ""` is rejected with a hint to use `crux-env rm KEY` to remove the key; the reader treats a missing key and `KEY=` identically, so there is no way to express "intentionally empty."
- Blank lines and comment-only lines are preserved on rewrite (the CLI's `set`/`rm` operations are line-oriented and stable).
- File trailing-newline is preserved.
- The parser MUST behave identically in `crux-env.py` (CLI) and `crux_env.py` (module). Conformance test: same `env` fixture → same dict. (Implementation: the CLI imports the parser from the module so there is exactly one implementation.)

Example:

```
# API keys
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxx
OPENAI_API_KEY="sk-proj-xxxxxxxxxxxx"

# Linear with embedded spaces in description (quoted)
LINEAR_API_KEY=lin_api_xxx
LINEAR_DEFAULT_TEAM="Backend # primary"
```

### 13.3 `~/.crux/required.yml` schema (locked)

```yaml
# Top-level map of project name → required/optional key lists.
# Hand-edited. Additively maintained by `crux-env --auto-update` (future flag).
projects:
  crux:
    required:
      - CRUX_HOME      # implicitly always set; included here as the canonical "this is what's checked"
    optional:
      - CRUX_DEBUG
  some-future-skill:
    required:
      - OPENROUTER_API_KEY
      - LINEAR_API_KEY
    optional:
      - LINEAR_DEFAULT_TEAM
```

- `projects:` is the only required top-level key. Each project name (string) maps to an object with `required: [list-of-keys]` and `optional: [list-of-keys]`.
- Key names match the same regex as `env` keys: `^[A-Z][A-Z0-9_]*$`.
- Empty lists are valid; missing `optional:` defaults to `[]`.
- File mode 0600.

### 13.4 `~/.crux/log/crux-env.log` format (locked)

Append-only. One line per op. ASCII only.

```
YYYY-MM-DD HH:MM:SS  <op>  <KEY>  [reason]
```

- Whitespace separator: two spaces between fields (so values containing single spaces don't confuse parsers — but values are never logged here anyway).
- `<op>` enum: `init | set | rm | rotate | check`.
- `<KEY>` is the env var key name (NEVER the value).
- `[reason]` is optional free-form text (no leading space if absent; one leading space if present).
- `rotate` is a two-step `rm` + `set` that records "rotate" instead so audit trails distinguish a value swap from a remove-then-add.
- The `check` op is logged when the user explicitly runs `crux-env check` (not when the Python module auto-checks on `require()` — that would log too noisily).

**Invariant:** the file MUST never contain a key's value. The CLI guarantees this; tests verify it.

### 13.5 Python module API (locked)

The plugin's `scripts/crux_env.py` exposes exactly:

```python
def require(*keys: str) -> tuple[str, ...]:
    """Return the values for each key in order. Raises EnvNotConfigured if any are missing or empty.

    Reads from os.environ first, then ~/.crux/env.
    Single-key call returns a 1-tuple (use indexing or unpacking).
    """

def get(key: str, default: str | None = None) -> str | None:
    """Return the value or default. Never raises."""

def get_optional(key: str, default: Any = None, cast: Callable = str) -> Any:
    """Typed accessor. Cast can be bool, int, float, or any callable.

    bool casts: 'true|1|yes|on' → True, 'false|0|no|off' → False (case-insensitive).
    Other strings raise ValueError.
    """

def load_all() -> dict[str, str]:
    """Return a fresh dict of every key in ~/.crux/env (no os.environ overlay)."""

class EnvNotConfigured(Exception):
    """Raised by require() when keys are missing or empty.

    Attributes:
        missing_keys: list[str]  -- the keys that were missing/empty
        remediation: str         -- a one-line message instructing the user how to fix it
    """
    missing_keys: list[str]
    remediation: str
```

Module behavior:

- The `~/.crux/env` file is parsed lazily on first access and cached for the process lifetime.
- `_reset_cache()` (underscore-prefixed) is exposed for tests; not part of the public API.
- `CRUX_HOME` env var overrides `~/.crux` lookup (so a script can point at a temp dir without monkey-patching `os.path.expanduser`).
- All four public functions read `os.environ` before the file — a shell-exported value wins.

### 13.6 CLI surface (locked)

The plugin's `scripts/crux-env.py` provides exactly these subcommands. Exit codes match crux convention (`0` clean, `1` user error or validation failure, non-zero with empty stdout = crash).

| Subcommand | Args | Behavior |
|---|---|---|
| `init` | — | Create `~/.crux/` tree with correct modes. Idempotent. |
| `check` | `[--project NAME]` | Validate required keys present. JSON on stdout if missing. Exit 1 on missing. |
| `load` | — | Print `export KEY="value"` lines for shell sourcing. |
| `get` | `KEY` | Print one value. Exit 1 if missing. |
| `set` | `KEY VALUE` | Add/update key. Log without value. |
| `rm` | `KEY` | Remove key. Log. |
| `list` | `[--project NAME]` | Print required vs present keys. NEVER prints values. |

The CLI script imports the same env-file parser as the module so the two stay in lock-step; a conformance test verifies they produce identical dicts for the same input.

**JSON error contract (locked).** Stdout JSON payloads emitted by `check` and `list` use stable top-level keys. On missing required keys: `{"missing": [{"project": NAME, "keys": [KEY, …]}, …], "extra": [KEY, …]}`. On unknown `--project NAME`: `{"error": "unknown_project", "project": NAME, "known_projects": [NAME, …]}`. On unparseable required.yml: `{"error": "required.yml parse failure", "detail": MSG}`. Downstream callers MAY rely on these field names and the `error` enum; new error variants MUST extend the enum without renaming existing keys.
