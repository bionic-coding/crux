<!-- generated-from: OPENCODE.md@sha256:6348d40e7d0191b49a31659a88bc55331ff6c0cb67411efd760baa49b42da27a; model: deterministic-copy; date: 2026-10-27 -->
# Install Crux for OpenCode

Crux has no native OpenCode marketplace package. OpenCode installation uses a stable clone of the public Crux repository. This guide covers machine-wide and project-only installation for humans and agents.

The generated agents require OpenCode V2. A V1 runner ignores the V2 `permissions` array and drops the role restrictions.

## Human installation

### 1. Clone Crux to a stable path

```bash
git clone https://github.com/bionic-coding/crux ~/.local/share/crux
cd ~/.local/share/crux
```

The OpenCode configuration uses absolute paths. Moving the clone breaks skill and agent loading until you update the configuration and symlinks.

### 2. Install `uv`

Crux scripts use PEP 723 metadata and run through `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

### 3. Generate the OpenCode agents

The public repository does not commit the generated `opencode/agents/` directory. Generate it after cloning and after every update:

```bash
uv run python3 crux/scripts/generate-opencode-agents.py
```

### 4. Register the skills

Merge this entry into `~/.config/opencode/opencode.json`. Replace `/Users/you/.local/share/crux` with the absolute clone path:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": ["/Users/you/.local/share/crux/crux/skills"]
}
```

The `skills` value is a V2 array of directories. Preserve existing configuration keys and existing skill entries.

### 5. Register the agents

Create one symlink per generated role:

```bash
mkdir -p ~/.config/opencode/agents
for f in ~/.local/share/crux/opencode/agents/*.md; do
  ln -sf "$f" ~/.config/opencode/agents/"$(basename "$f")"
done
```

Use the plural `~/.config/opencode/agents/` directory. Remove old Crux links from the legacy singular directory:

```bash
rm -f ~/.config/opencode/agent/{architect,brainstormer,commander,dev-lead,developer,historian,librarian,night-gardener,reviewer,wayfinder}.md
```

### 6. Restart and verify

Fully quit and restart the OpenCode host. Starting a new thread alone is insufficient. For Zed or ACP, restart Zed or reconnect the ACP process.

Verify the agents:

```bash
opencode debug agents
```

The command should list these ten Crux roles:

- `architect`
- `brainstormer`
- `commander`
- `dev-lead`
- `developer`
- `historian`
- `librarian`
- `night-gardener`
- `reviewer`
- `wayfinder`

The command can return `[]` at exit 0 while the background service resolves the project. Run it again before diagnosing a missing agent.

OpenCode V2 has no skill-listing command. Verify skills by asking OpenCode to use one, such as “audit docs” or “what's next.”

### Project-only agents

After registering the Crux skills, ask OpenCode:

> Install the Crux agents in this project.

The `install-opencode-agents` skill writes the ten roles to `.opencode/agents/`. It checks for an OpenCode V2 runner, preserves unrelated agents, and refuses changed managed roles without `--force`.

A project role shadows a machine-wide role with the same name. Choose one scope for each project.

## Agent installation procedure

Follow this section when you are the OpenCode agent performing installation for a user.

1. Confirm that an OpenCode 2.x runner is available: `opencode --version` reports a version whose major is 2. The installer identifies the runner by that reported version, never by the name of its executable, so a 2.x runner installed under any name passes. Set `CRUX_OPENCODE_BIN` to name a runner the installer would not otherwise find.
2. Resolve the absolute Crux clone or plugin path. Do not write a relative skill path into the global configuration.
3. Read the existing `~/.config/opencode/opencode.json`. Merge the Crux skill directory into its `skills` array without dropping other keys or entries.
4. Generate the projection with `uv run python3 <clone>/crux/scripts/generate-opencode-agents.py`.
5. For machine-wide installation, create glob-based per-file symlinks from `<clone>/opencode/agents/*.md` into `~/.config/opencode/agents/`. Do not hardcode a partial roster.
6. For project scope, invoke the installer through `uv`:

   ```bash
   uv run <install-opencode-agents-skill-dir>/scripts/install.py --repo-root "$PWD"
   ```

7. If the legacy `.opencode/agent/` directory contains a roster filename, report it. Use `--migrate-legacy-agent-dir` only after reviewing the move and any destination collision.
8. Use `--force` only after showing the user the managed-file or migration collision.
9. Tell the user which host process must restart. Do not claim that a file-level check proves the running host loaded the new configuration.

## Updating Crux

```bash
cd ~/.local/share/crux
git pull --ff-only
uv run python3 crux/scripts/generate-opencode-agents.py
```

The global symlinks continue pointing at the generated files. After an upgrade, regenerate the agents so each installed role carries the new council and review text, then restart OpenCode. A project install refreshes through `install-opencode-agents`. Run the generator with `--dry-run` to check for drift without writing:

```bash
uv run python3 crux/scripts/generate-opencode-agents.py --dry-run
```

Project-only installations do not update through the global symlinks. Invoke `install-opencode-agents` again in each project and review drift before using `--force`.

## Run dashboard in the OpenCode TUI (optional)

`crux-opencode` is a separate, optional plugin for OpenCode's terminal interface (the TUI) in OpenCode 2. It lives in the `crux-opencode/` directory of your clone, beside `crux/`. It draws the state of a crux promptbook run inside OpenCode:

- **A band above the composer.** One line for the run in progress, shown on a session screen. The home screen shows nothing.
- **A panel.** The run dashboard panel, named `crux-dashboard`, opens beside the session.
- **Page keys.** With more closed cycles than fit on one page, the panel lists them three to a page under `cycles:`. While the panel is focused (click it), `n` shows the next page and `p` the previous one. The panel ends with a `page X/Y` line and the hint `p previous · n next`. When the panel is closed or your prompt has focus, `n` and `p` type into the prompt as usual.
- **A command.** `/crux-dashboard` opens the panel. It adds nothing to the transcript, to your prompt or to a model request. When no panel can open, such as outside a session, it shows a toast that carries only a status code.

It draws the same run progress as the Claude Code dashboard, because it uses the same reader (`visualize-run-progress`) and the same drawing code from your clone. Installing the crux skills loads nothing in OpenCode's terminal interface. You opt in with the entry below.

### 1. Add the plugin to `cli.json`

OpenCode 2 reads terminal plugins from `~/.config/opencode/cli.json`. Create the file if it is absent, and merge this entry. Replace `/Users/you/.local/share/crux` with the absolute path of your clone:

```json
{
  "plugins": ["/Users/you/.local/share/crux/crux-opencode"]
}
```

Keep the other keys and entries that the file already holds. The entry names the directory itself, not a file in it. Use an absolute path. Do not list `crux-opencode` in `opencode.json`: it has no server half. See OpenCode's CLI plugin docs: <https://opencode.ai/v2/docs/build/plugins/cli/>.

Before you restart, warm the `uv` cache while you are online. The plugin runs `uv` with `--offline`, so a Python or PyYAML missing from the cache shows `offline-unavailable`. Run these once, with the absolute path of any project in place of `<project path>`:

```bash
uv python install 3.13
cd ~/.local/share/crux/crux
uv run --no-project --no-config scripts/visualize-run-progress.py --json --project-root "<project path>"
```

Then fully quit and restart OpenCode's terminal interface. There is nothing to install or build. crux-opencode is never published to npm or any other package registry, and it carries no version of its own: it is the version of your clone.

### 2. What you see

Open a session in a project that has a crux documentation tree and a run in progress. The first view appears at least 4 seconds after OpenCode's terminal interface starts. After that the band and the panel refresh every 10 seconds, when the panel opens and when you run `/crux-dashboard`. After a slow status (`reader-timeout`, `reader-cpu-limit` or `reader-failed:time-limit`), the 10-second refresh pauses. Opening the panel or running the command still refreshes both. The 10-second refresh resumes after a refresh that ends with any other result.

- The band draws at most 40 columns, because OpenCode's band slot reports no width. The panel fits the width OpenCode reports for it.
- Every colour is a token of your OpenCode theme, and no colour carries a meaning alone: a glyph or a word repeats it.
- The dashboard is static. It draws no motion and no pictures, reads none of your prompts, shows subagent status only as `agents unavailable`, and adds no stop to a run.

### 3. When it shows a status instead of a view

The dashboard draws a status code when it cannot check the run safely. It refuses and does not guess. The band reads `crux-opencode dashboard: <code>` and the panel reads `Dashboard unavailable: <code>`. For `unsupported OpenCode version`, both read `crux-opencode dashboard: unsupported OpenCode version` when that line fits the region, and the words alone when it does not. The band is 40 columns wide, so it always shows the words alone. The band stays empty for `no-active-run`, which means no run is in progress.

| Code | Meaning | What to do |
|---|---|---|
| `unsupported OpenCode version` | OpenCode reports a version other than 2.x, or none. The plugin starts no process. | Use OpenCode 2.x. |
| `inside-project` | The project root holds your crux clone, `uv`, its cache or its interpreter directory. The home directory counts, and so does a workspace folder that holds the clone. | Start OpenCode in the project's own directory. |
| `project-root-unresolved` | The directory OpenCode names for the session does not resolve to an existing directory, for example because it was removed after OpenCode's terminal interface started. | Restore the directory. The next refresh picks it up. |
| `crux-not-found` | The plugin cannot find `crux/` in the clone that holds `crux-opencode/`. | List the plugin by its path in a complete clone. |
| `version-mismatch` | `crux/plugin.json` and the crux-mods manifest in the clone carry different versions. | Update the clone with `git pull --ff-only`. |
| `home-invalid` | `HOME` is unset or not an absolute path. | Start OpenCode with `HOME` set to an absolute path. |
| `uv-not-found` | `uv` is not at one of the places the plugin looks: `/opt/homebrew/bin/uv`, `/usr/local/bin/uv`, `~/.local/bin/uv` or `~/.cargo/bin/uv`. | Install `uv` at one of those places. |
| `reader-timeout` | The reader was still running after 10 seconds. | Retry. A cold `uv` cache can be slow the first time. |
| `reader-cannot-start` | The plugin could not start the reader process. | Check that `/usr/bin/env` and `uv` are executable. |
| `reader-cpu-limit` | The system stopped the reader at its CPU limit. | Retry. If the code persists, run the reader command below. |
| `offline-unavailable` | `uv` cannot run the reader without the network, because a Python or PyYAML is not in its cache. | Run `uv python install 3.13` once. Then, while online, run `cd ~/.local/share/crux/crux && uv run --no-project --no-config scripts/visualize-run-progress.py --json --project-root "<project path>"` once. |
| `reader-no-json-mode` | The crux in your clone is too old to have the reader's JSON mode. | Update the clone with `git pull --ff-only`. |
| `reader-format-mismatch` | The reader answered with a JSON format version the plugin does not accept. | Update the clone with `git pull --ff-only`. |
| `reader-failed:<code>` | The reader answered with an error code, such as `tree-missing` (no crux tree in this project). | For `tree-missing`, start OpenCode at the project root. Otherwise run the reader command below. |
| `reader-failed`, `reader-output-invalid` | The reader failed without an answer, or its output did not match the shape the plugin accepts. | Run the reader command below to see the cause. |
| `panel-unavailable` | The command shows this in a toast when no panel can open. | Open a session, then run the command again. |

To see the reader's own answer, run it from the clone's `crux/` directory and never from inside the project, in a shell with no virtual environment active:

```bash
cd ~/.local/share/crux/crux
uv run --offline --no-project --no-config scripts/visualize-run-progress.py --json --project-root "<project path>"
```

### 4. Limits

- **OpenCode 2.x only.** The plugin draws a view only when OpenCode reports a 2.x version. It was written against OpenCode 2.0.26, and OpenCode documents its plugin interface as unstable, so a later 2.x release can break the view until a fix ships.
- **Local projects.** The plugin reads only the directory OpenCode names for the session. A terminal attached to a remote server shows the run state of that local directory, which can differ from the server's project.
- **The reader is your clone's, never the project's.** OpenCode itself loads TUI plugins from a project's `.opencode/plugins/` into the same process without asking, and crux-opencode's guarantee does not cover that code. The plugin runs only the reader in your clone, through `uv`, offline, with a fixed environment. It never runs a script, interpreter or environment variable that the project supplies.
- **POSIX systems.** The plugin starts its reader through `/usr/bin/env`. On a host without it, such as native Windows, it starts no process and shows no view.
- **Paths compare case-sensitively.** The `inside-project` check compares paths case-sensitively. On a case-insensitive APFS volume, a path inside the project that spells the project's path in different case is not seen as inside it.
- **No dogfooding in place.** The project root cannot hold the clone, so OpenCode run inside a crux checkout shows a status, not that checkout's runs. Keep a second clone, list that one in `cli.json`, and run OpenCode in the first.

### 5. Updating and turning it off

The plugin updates with the clone. Run `git pull --ff-only`, then restart OpenCode's terminal interface. It needs no regeneration. To turn it off, remove its entry from `cli.json` and restart. Your documentation tree and runs are unchanged.

## Model gateway

Most Crux skills work without external model credentials. A cycle's council gates need the gateway key. An ad-hoc council and the LLM-backed skills use it too. All of them read one OpenRouter key stored outside the repository:

```bash
python3 crux/scripts/crux-env.py init
python3 crux/scripts/crux-env.py set OPENROUTER_API_KEY <value>
python3 crux/scripts/crux-env.py check --project crux
```

The check command never prints secret values.

Council deliberation runs only through the council runner (`run-council.py`). Without the key, the council runner cannot run. It writes a DEFER_TO_HUMAN record, and the run stops for you. No agent casts a seat's vote in its place. Before a run's next gate prompt, store the key and commit every council subject. The council runner commits its attempt record and its council record itself; do not commit either by hand. When the council runner exits 2 and stderr names `timeout`, or names outside work the commit moved, the owner's remedy comes first. Restore the work a hook set aside (`git stash list`; the pre-commit framework keeps a backup patch under its cache directory). Only then remove a stale `index.lock` in the git directory. After those two steps, and after any other exit 2 or an open attempt, run the process check and probe the lock with `run-council.py --recover <run> --prompt <n> --probe`. Once no live council runner holds it, run `run-council.py --recover <run> --prompt <n>`, never a new round. A hook that rewrites a council file (a JSON formatter with another indent or key order, for example) must exclude `<docs_dir>/promptbooks/runs/`, for example `exclude: ^<docs_dir>/promptbooks/runs/` in the pre-commit framework. Otherwise each council commit whose file the hook rewrites fails closed (`hook-or-commit-failed`, or `mismatch` when the hook re-stages its rewrite) and stops for you. A hook slower than the commit's 120-second bound makes the commit time out and leaves the attempt open, so the owner's remedy above comes before recovery.

## Troubleshooting

| Symptom | Action |
|---|---|
| `opencode debug agents` omits Crux roles | Regenerate the projection, inspect the symlinks, and restart the host. |
| An agent file reports an invalid comma-separated `tools` field | The symlink targets `crux/agents/` instead of generated `opencode/agents/`. |
| A role runs without its deny rules | The runner is older than 2 and ignored the `permissions` array. Check `opencode --version`, and upgrade to 2.x. |
| A skill is missing | Check the absolute `skills` path in `opencode.json`, then restart OpenCode. |
| Roles use old instructions after `git pull` | Regenerate `opencode/agents/`; the public clone leaves that directory untracked. |
| The project installer refuses a legacy role | Review `.opencode/agent/`, then use the migration flag if those files belong to Crux. |

## Security boundaries

Do not commit `~/.config/opencode/opencode.json`, API keys, or user-level agent links into a project. Do not run generated V2 roles with the V1 `opencode` binary.

The machine-wide setup uses no Crux installer code after projection generation. The project installer only manages the ten current role filenames and preserves unrelated files.

The `crux-opencode` plugin reads only its own files, the clone's `crux/` and `crux-mods/` files, the `uv` locations and environment values it declares, and the reader's output. It keeps nothing outside OpenCode's in-memory plugin storage, writes nothing in your documentation tree, and never reads `~/.crux/` or another credential file.
