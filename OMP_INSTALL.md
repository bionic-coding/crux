<!-- generated-from: OMP_INSTALL.md@sha256:58b66457b5ac6af48da63c046f6e068056d91eda99a8b261553c9fdf9e094e2c; model: deterministic-copy; date: 2026-10-20 -->
# Install Crux for OMP

This guide installs Crux in Oh My Pi (OMP) on another machine. It covers human installation and the procedure an OMP agent should follow after the plugin is available: 55 skills, ten native role agents, an optional TUI dashboard, and optional council credentials.

## Prerequisites

- OMP with marketplace support, native Markdown task agents, and, for the optional dashboard, the TypeScript `ExtensionAPI`.
- `uv` available on `PATH` to run Crux's Python scripts. The agent installer requires Python 3.11 or newer; `uv` can provision the script's declared interpreter. See <https://docs.astral.sh/uv/getting-started/installation/>.
- Network access for the marketplace installation and any first-time interpreter or dependency downloads. Configure the model provider used by your OMP session separately; installing Crux does not authenticate OMP to a provider.
- Write access to the selected personal or project agent directory. No Crux gateway key is required to install or check skills and agents.

## Human installation

### 1. Install the plugin

Run these commands in OMP:

```text
/marketplace add bionic-coding/crux
/marketplace install crux@crux
```

The marketplace makes the 55 Crux skills available, including `install-omp-agents`. Start a fresh OMP session after installation so it can discover the selected installation. Then say:

> Install the Crux agents for OMP.

The skill projects the plugin's role definitions into OMP's native format and installs these ten `<role>.md` files in `~/.omp/agent/agents/` by default:

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

The marketplace skill installation and the native agent installation are separate steps. Loading Claude-dialect role definitions directly from the marketplace does not preserve all OMP model and spawn declarations. Use the installer rather than copying those definitions by hand.

Each native role carries its model selectors, thinking level, native tools, and applicable spawn restrictions. Model selectors try the machine's `@crux_<role_underscored>` alias before the catalog's OpenRouter fallback. Configure overrides through `modelRoles` in `~/.omp/agent/config.yml`, not by editing generated agent files. The installer preserves unrelated agents and does not rewrite your OMP configuration.

Crux's cycle workflow needs `main -> commander -> dev-lead -> developer` delegation (three levels of nesting). OMP's default `task.maxRecursionDepth` is `2`, so set it to at least `3` in `~/.omp/agent/config.yml`:

```yaml
task:
  maxRecursionDepth: 3
```

### 2. Check the installation

Ask OMP:

> Check the Crux OMP agents and inspect this project for shadows.

The agent runs the installer with `--check --project-context` pointing to your repository. The JSON report must have `installed.status: clean`, `drift.status: clean`, the ten roles installed, and no shadow findings. Check mode is read-only and does not create the target directory. Its exit codes are `0` for clean static health, `1` for installed-state, drift, or shadow findings, and `2` for configuration or environment errors.

Static health checks do not prove live host discovery. Start a fresh OMP session in the target project and ask it to dispatch representative roles through `task` and use a Crux skill, such as “what's next.” Runtime loading is verified in that session, not by the installer. Leave runtime status unverified until you have observed the host resolve and invoke the installed roles and skills.

### Project-only installation

When the roles should exist only in one repository, say:

> Install the Crux agents for OMP in this project only.

The agent uses `--repo-root <repo>` and writes `<repo>/.omp/agents/`. A same-name project agent can shadow a personal role. Choose the intended scope deliberately and inspect that repository with `--project-context`; do not delete other agents to clear a shadow without reviewing the conflict.

## OMP agent installation procedure

Follow this section when you are the OMP agent performing installation for a user.

1. Read `skill://install-omp-agents`. If the skill is unavailable, have the user install or update Crux with the marketplace commands above and start a fresh session.
2. Resolve the selected installed skill's absolute `SKILL.md` path. Its directory is `<plugin-root>/skills/install-omp-agents`; the plugin root is the parent of `skills/`. Do not assume `CLAUDE_PLUGIN_ROOT` exists, use a development-checkout path, or select an older duplicate installation.
3. Set these shell variables from that resolved path. Replace the example placeholder with the actual absolute path before running commands:

   ```bash
   CRUX_OMP_SKILL_DIR="/absolute/installed/plugin/skills/install-omp-agents"
   CRUX_PLUGIN_ROOT="${CRUX_OMP_SKILL_DIR%/skills/install-omp-agents}"
   ```

   In a public Crux tree, this plugin root is the `crux/` directory, not the release root that contains it. The installer is shipped as `crux/skills/install-omp-agents/scripts/install.py`; the commands below locate it through the selected skill, independent of the marketplace's cache layout.
4. Select the user-requested scope. For the default personal installation, with a project shadow scan:

   ```bash
   uv run "$CRUX_OMP_SKILL_DIR/scripts/install.py" --project-context "$PWD"
   ```

   Omit `--project-context` when there is no repository to inspect. This flag only selects the shadow-scan context; it does not change the installation scope. For project-only installation:

   ```bash
   uv run "$CRUX_OMP_SKILL_DIR/scripts/install.py" --repo-root "$PWD"
   ```

   For an isolated personal profile, pass `--omp-home /absolute/profile/agent`. It targets `/absolute/profile/agent/agents/`. `--omp-home` and `--repo-root` are mutually exclusive. Use an isolated profile for automation, never a real personal agent directory. The flag selects the installer's target; ensure the OMP session you test actually uses that profile.
5. Read the JSON result. Inspect installed state, managed drift, and shadows separately; a canonical role roster alone is not proof that its files are installed. If the installer refuses changed or stale managed files, show the reported `added`, `changed`, and `removed` lists. Use `--force` only after reviewing the replacement with the user.
6. Check the same target without writing:

   ```bash
   uv run "$CRUX_OMP_SKILL_DIR/scripts/install.py" --check --project-context "$PWD"
   ```

   Retain `--repo-root` or `--omp-home` when checking a nondefault target. A personal check does not check a project installation.
7. Start a fresh OMP session for runtime verification. Report static results separately from observed host loading; do not claim a clean installer result proves discovery, applied models, tools, or spawn restrictions.

## Updating and conflicts

Update Crux through OMP's marketplace, then start a fresh session and resolve the installed skill path again. Say:

> Refresh the OMP agents.

Rerun the installer for each scope or profile you use. Review its drift report before allowing a refresh with `--force`:

```bash
uv run "$CRUX_OMP_SKILL_DIR/scripts/install.py" --force --project-context "$PWD"
```

Add the original `--repo-root` or `--omp-home` when applicable. Refreshing carries updated role instructions and model projections into installed agents. An unchanged refresh writes nothing. The installer manages the ten roster filenames and preserves unrelated custom agents; a pre-existing custom file using one of those ten names is a conflict to review, not an unrelated file to overwrite automatically.

Do not hand-edit generated `<role>.md` files. Make intentional role changes in Crux's sources and refresh through the installer. Keep machine-specific model overrides in OMP configuration. Unsafe managed symlinks or paths escaping the selected scope are refused; `--force` is not a bypass for those checks.

## Run dashboard in the OMP TUI (optional)

`crux-omp` is an optional extension shipped beside `crux/` and `crux-mods/` in the public tree. It displays run state in the status bar, an above-editor band, and a panel toggled with `/crux-dashboard`. In layouts where OMP's band and status bar sit adjacent (for example, `composer: { shape: band }`), the same cycle line appears twice. The extension registers a launch flag, `--cruxOmpBand`, which defaults to `true`; pass `--cruxOmpBand=false` to the launch that loads the extension to keep only the status-bar entry and hide the duplicated above-editor band. This is an extension launch argument read through OMP's extension flag channel, not a `config.yml` setting. The status bar and the `/crux-dashboard` panel remain available.

It requires the sibling `crux-mods/hooks/lib/` shared core tree. Its TypeScript modules import that core by relative path (`../../crux-mods/hooks/lib/` from `crux-omp/lib/`). Keep the complete sibling layout; copying only `crux-omp/` elsewhere breaks those imports. There is no separate npm package or build step to substitute for the shared tree.

From the public release root containing those siblings, load it for a session:

```bash
omp -e ./crux-omp/index.ts
omp -e ./crux-omp/index.ts --cruxOmpBand=false
```

The second form hides only the above-editor band.

Equivalently, after deriving `CRUX_PLUGIN_ROOT` above, run from your project with an absolute entry path:

```bash
omp -e "$CRUX_PLUGIN_ROOT/../crux-omp/index.ts"
```

Installing skills or agents alone does not load the dashboard. Opt in through the extension entry and verify it in a live TUI session. Use a project with a Crux documentation tree and a run to inspect; absence of a run is not evidence that the extension failed to load. Keep the extension and shared core from the same Crux installation when updating.

## crux-env and optional credentials

`crux/scripts/crux-env.py` manages runtime state outside the repository. Its default credential file is `~/.crux/env`. Credentials are optional: they are needed only for council/gateway features, not marketplace installation, native agent installation, static health checks, or dashboard loading. OMP's own provider authentication is separate.

With `CRUX_PLUGIN_ROOT` derived from the installed skill as above:

```bash
uv run python3 "$CRUX_PLUGIN_ROOT/scripts/crux-env.py" init
uv run python3 "$CRUX_PLUGIN_ROOT/scripts/crux-env.py" check
uv run python3 "$CRUX_PLUGIN_ROOT/scripts/crux-env.py" list
```

`init` is idempotent and creates the private runtime-state tree, with directories mode `0700` and credential files mode `0600`. `check` validates keys declared in `required.yml`; `list` reports required/optional key presence per project without printing values. An empty declaration is not proof that a gateway credential works.

| Command | Purpose and handling |
|---|---|
| `init` | Create the runtime-state tree with private modes. |
| `check [--project NAME]` | Validate declared required keys; report missing keys, not values. |
| `load` | Emit shell exports containing values. Use only in a private local shell, never through a captured agent tool or transcript. |
| `get KEY` | Emit one value. Use only for private local consumption; never paste its output into chat or logs. |
| `set KEY VALUE` | Add or update a key; the operation log omits its value. |
| `rm KEY` | Remove a key. |
| `list [--project NAME]` | Show declared key presence without values. |

For councils or gateway-backed features, the owner can store `OPENROUTER_API_KEY` locally with `set`. This example uses a placeholder, not a real credential:

```bash
uv run python3 "$CRUX_PLUGIN_ROOT/scripts/crux-env.py" set OPENROUTER_API_KEY '<your-key>'
```

Do not run that literal placeholder as setup. Enter the real value privately, taking shell history and command capture into account. Never print real key values, request them in chat, commit the env file, or attach it to diagnostics. Use `check` and `list` for shareable health results, not `get` or `load`.

Set `CRUX_HOME` to an absolute private directory for isolation; it replaces `~/.crux`, so the env file becomes `$CRUX_HOME/env`. For example, initialize an empty test profile without touching personal credentials:

```bash
CRUX_HOME=/absolute/private/crux-test uv run python3 "$CRUX_PLUGIN_ROOT/scripts/crux-env.py" init
```

Keep the same `CRUX_HOME` for subsequent commands in that profile. Do not copy real credentials into test artifacts.

## Troubleshooting

| Symptom | Action |
|---|---|
| `install-omp-agents` is unavailable | Check the marketplace installation, update if needed, and start a fresh OMP session. |
| `uv` or a required interpreter is unavailable | Install `uv`, ensure it is on `PATH`, and allow its first-time interpreter/dependency setup. |
| The installer reports managed drift | Review the selected plugin root and the changed/removed lists, then authorize `--force` for the intended scope only. |
| A role resolves differently in one repository | Run `--check --project-context <repo>` against the intended target and inspect same-name project shadows. |
| A symlink or escaping-path refusal occurs | Inspect and correct the unsafe target with the owner; do not bypass the refusal or delete unrelated agents. |
| Static health is clean but a role is unavailable | Start a fresh session using the intended home/project; observe `task` dispatch. Static health does not prove runtime loading. |
| Dashboard imports fail | Restore the complete sibling `crux-omp/`, `crux-mods/hooks/lib/`, and `crux/` layout from one installation. |
| Skills work but no dashboard appears | Load `crux-omp/index.ts` explicitly with `omp -e` in a TUI session; skills and agents do not load it. |
| A council reports a missing gateway key | Initialize the intended crux-env profile and set the key privately; use `check`/`list`, never key values, in diagnostics. |
