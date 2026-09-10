---
name: install-docs-skills
description: "Use when the user says \"install docs skills\", \"add this plugin\", \"set up crux\", or \"upgrade docs suite\", asks about the installed version, or the Crux plugin is not loaded. Install or upgrade the Crux plugin in Codex or Claude Code. In Codex, provide `codex plugin marketplace add bionic-coding/crux` then `codex plugin add crux@crux`; in Claude Code, provide its marketplace slash commands. Report the installed manifest before guiding a schema migration. Distinct from `init-docs`, which bootstraps the target repository's docs tree."
disable-model-invocation: true
metadata:
  tags: "installation, plugin, distribution"
  bundles: "crux-docs"
  risk_level: "low"
  routing_note: "Re-runs the installer."
---

# Install Docs Skills

<!-- BEGIN GENERATED: runtime-compat -->
## Runtime compatibility

This skill is portable across Claude Code, Codex, and OpenCode. This section overrides platform-specific labels below.

- Before running a command that uses `CRUX_PLUGIN_ROOT`, set it to the installed plugin root. In Claude Code, use the value of `CLAUDE_PLUGIN_ROOT`. In Codex and OpenCode, derive it from the absolute path of this selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, use the checkout `crux/` directory.
- For project-local skills, use `.claude/skills` in Claude Code, `.agents/skills` in Codex, and `.opencode/skills` in OpenCode, which also reads the singular `.opencode/skill`. Set `CRUX_LOCAL_SKILLS_DIR` to that path before following any command below that uses it.
- Translate Claude Code tool labels such as `Agent`, `Read`, `Write`, `Bash`, `WebSearch`, and `WebFetch` to the matching capability in the current session. Codex names its own capabilities; OpenCode uses the lowercase forms `subagent`, `read`, `edit`, `shell`, `websearch`, and `webfetch`, where `edit` covers both `Edit` and `Write`. Do not attempt to invoke the Claude Code labels as literal commands on another host.
- Install the generated role agents before delegating: `install-codex-agents` in Codex, `install-opencode-agents` in OpenCode. Codex names them `crux_architect`, `crux_brainstormer`, `crux_commander`, `crux_dev_lead`, `crux_developer`, `crux_historian`, `crux_librarian`, `crux_night_gardener`, `crux_reviewer`, and `crux_wayfinder`; OpenCode uses the bare role names `architect`, `brainstormer`, `commander`, `dev-lead`, `developer`, `historian`, `librarian`, `night-gardener`, `reviewer`, and `wayfinder`. If a required role or capability is unavailable, report that truthfully instead of claiming it ran.
- Argument placeholders such as `$adr` and `$book` bind only in Claude Code. On a host without argument binding they are unset — take the value from the user's phrase. The "Fields OpenCode ignores" section of `OPENCODE_GUIDE.md` names the invocation-control fields OpenCode ignores.
<!-- END GENERATED: runtime-compat -->


## Codex CLI (takes precedence in Codex)

The Codex marketplace entry for this repository lives at
`.agents/plugins/marketplace.json`; it packages the `crux/` directory, whose
`.codex-plugin/plugin.json` exposes all bundled skills.

For a first install, provide these commands from any terminal. Do not run them
unprompted because they change the user's configured plugin marketplaces:

<!-- provenance: the `codex plugin marketplace add` → `codex plugin add` install
     CLI syntax below is an external contract owned by OpenAI, not by crux.
     Verified 2026-07-09 against the official docs
     (https://developers.openai.com/codex/plugins/build) and the local
     `codex plugin --help` / `plugin add --help` / `plugin marketplace add --help`
     for codex-cli 0.144.0: `marketplace add <SOURCE>` accepts an `owner/repo`
     source, and `plugin add <PLUGIN[@MARKETPLACE]>` accepts the `crux@crux`
     positional. The docs additionally confirm `marketplace list/upgrade/remove`
     and `plugin list/remove`. No live-network validation is performed — upstream
     drift is diagnosed by comparison against this dated citation. -->
```bash
codex plugin marketplace add bionic-coding/crux
codex plugin add crux@crux
```

Start a new Codex thread after installation so its skill inventory is refreshed.
To make the Crux role agents available in a particular repository, then invoke
`install-codex-agents` from that repository. Plugin installation supplies skills;
the agent installer supplies project-scoped `.codex/agents/*.toml` files.

For an upgrade, refresh the configured Git marketplace and reinstall:

```bash
codex plugin marketplace upgrade crux
codex plugin add crux@crux
```

If Codex reports that no marketplace named `crux` exists, repeat the first
install command. Use `codex plugin marketplace list` and `codex plugin list` to
inspect configured marketplaces and installed plugins. Never search or modify
`~/.claude/plugins/` or use Claude Code slash commands in a Codex session.

## Claude Code Instructions

The install-guidance skill. Its job is to make the Claude Code install path for
`crux` discoverable and unambiguous without taking any installing action itself.
The instructions in this section apply only to Claude Code; Codex uses the
commands above.

```
/plugin marketplace add bionic-coding/crux
/plugin install crux@crux
```

Slash commands are typed by the user in the Claude Code UI — this skill cannot run them. The skill's entire write surface is *output to the user*: install state, installed version/manifest, and the commands above.

When the plugin is already installed, this skill reports the installed `version`, the `schema_version` it expects, and the full list of bundled skills and agents (read from the installed `plugin.json`). When the plugin is missing, the skill prints the two marketplace commands.

Pairs with: `init-docs` (the post-install bootstrap that creates `docs/` in the target repo). Distinct from `audit-docs --migrate` (the schema migration that runs after an upgrade; a real, implemented mode — not part of install itself). The plugin's supported schema is a single value; read it from the installed `plugin.json` rather than from this prose, which has gone stale before. Any lower value is a "needs migration" state whose recovery is `audit-docs --migrate`.

## When to use

- User says: "install docs skills", "add this plugin", "set up crux", "install the docs plugin".
- User says: "upgrade docs suite", "update the plugin", "pull the latest docs skills".
- User asks: "what version is installed?", "is crux up to date?".
- A session where crux skills are expected but the plugin isn't loaded.
- `audit-docs` or another skill detects that the installed plugin version is older than what `docs/manifest.yml` expects.

Do **not** use this skill for:
- Bootstrapping `docs/` content inside the target repo — that's `init-docs`. This skill guides the plugin install; `init-docs` creates the docs tree.
- Migrating `docs/` schema after an upgrade — use `audit-docs --migrate`.
- Adding unrelated plugins. This skill knows about `crux` only.
- Editing the plugin source (a development checkout of the crux repo). This skill is about the installed plugin.

## Default mode: informational

This skill is **purely instructional**. The behavior is:

1. Detect installation state.
2. If installed, read `plugin.json` and report version + manifest.
3. Print the two marketplace commands verbatim.
4. Stop. The user runs the slash commands; the marketplace does the rest.

There is no Bash-install path. Marketplace commands are user-typed slash commands; there is nothing for this skill to execute.

## The pipeline

### 1. Detect the current state

Check, in order:

1. **`${CRUX_PLUGIN_ROOT}`** — crux's portable name for the installed plugin root (in Claude Code, the value of the loader-set `CLAUDE_PLUGIN_ROOT`; in Codex, derived from the selected `SKILL.md`'s path). When this skill is running *from* the crux plugin, that root resolves to the installed plugin directory. If it resolves and `${CRUX_PLUGIN_ROOT}/plugin.json` exists, the plugin is installed and that file is the manifest to read.
2. **The marketplace plugin cache** — look for a `crux` plugin directory under `~/.claude/plugins/` (the cache layout may nest by marketplace; search for a directory containing a `plugin.json` whose `name` is `crux`).

Two states:

- **Absent** → first install. Skip to step 3 (print the marketplace commands).
- **Present** → read `plugin.json` (step 2), report, then print the upgrade guidance (step 4).

If the directory is present but `plugin.json` is missing or malformed, report that the installation looks broken and recommend re-running `/plugin install crux@crux` — never attempt to repair the plugin cache by hand.

### 2. Read `plugin.json` if installed

Path: `${CRUX_PLUGIN_ROOT}/plugin.json` (or the cache path found in step 1).

Fields to extract:

- `name` — should be `crux`.
- `version` — semver of the installed plugin.
- `schema_version` — the tree schema version this plugin supports.
- `skills` — list of skill names bundled in this version.
- `agents` — list of bundled agents (when present).
- `scripts` — list of helper scripts.

Sanity checks:
- If `name` is not `crux`, refuse: "Plugin at `<path>` reports name `<X>`, not `crux`. Inspect the directory; do not assume it's this plugin."
- If `version` is missing or not semver, warn and proceed.
- If `schema_version` is missing, warn — the schema-compatibility check will be skipped.

Resolve whether the target repo has an existing tree — via `bionic-config.py --repo-root "<target repo>"`, or directly by checking for `.bionic.yml`, a `bionic/` tree, or a legacy `docs/` tree (any one of these existing counts as an existing tree; never test literal `docs/` absence alone, which misclassifies an established `bionic/`-only repo). If an existing tree is found, read its `manifest.yml` `schema_version` and compare against the plugin's supported value. The current plugin supports **exactly one** value — a single-value check, not an inclusive range. Read the supported value from the installed manifest; do not hardcode it here. There is no "newer/older within a range" gradient; a tree is either at the supported value or it needs migration:

Compare the tree's value against the supported value you just read from the manifest — **never against a number written in this file.** This prose has shipped stale twice; the manifest is the only source of truth.

- **Equal (match)** → all good. The plugin operates on this tree.
- **Below the supported value (needs migration)** → the upgraded plugin does NOT operate on it; this is a distinct "needs migration" state, not an install error. Recommend running `audit-docs --migrate` AFTER upgrading the plugin. Its ladder walks every rung between the tree's value and the supported one, in order.
- **Above the supported value (plugin too old)** → STOP. The tree was written by a newer plugin; upgrade the plugin first (or, rarely, downgrade the schema).
- **Below the ladder's earliest rung (tree too old)** → STOP. `audit-docs --migrate` cannot upgrade it. Surface this for a manual re-init — there is no automated recovery path.

### 3. Print the install commands (absent state)

Print to the user:

```
crux is not installed.

Install it with two slash commands in Claude Code:

    /plugin marketplace add bionic-coding/crux
    /plugin install crux@crux

Then restart the session so the plugin's skills and agents register.
After installation, say "init docs" to bootstrap the project's docs tree.
```

### 4. Print the upgrade guidance (present state)

Print to the user:

```
crux is already installed.

Installed:    version <X.Y.Z>, schema_version <N>
Schema match: <ok | needs migration (tree at "2") | plugin too old (tree above "3") | tree too old (below "2")>
Skills:       <count> — <comma-separated names from plugin.json>
Agents:       <count> — <comma-separated names from plugin.json>

To upgrade, refresh the marketplace and re-install:

    /plugin marketplace update crux
    /plugin install crux@crux

(If the marketplace was never added in this environment, run
`/plugin marketplace add bionic-coding/crux` first.)

Upgrading does NOT touch the existing tree. After upgrade, if `schema_version`
changed, run `audit-docs --migrate` to apply schema migrations.
```

### 5. Post-install hand-off

After the user reports the install succeeded (or a later session detects the plugin loaded):

- Confirm `plugin.json` is readable and `name == "crux"`.
- Resolve whether the target repo already has an existing tree — via `bionic-config.py --repo-root "<target repo>"`, or directly by checking for `.bionic.yml`, a legacy `.crux`, a `bionic/` tree, or a legacy `docs/` tree. Any one of these existing counts as an existing installation. Never key this on literal `docs/` absence alone: a repo bootstrapped under the default `bionic/` layout has no `docs/` at all and would be misclassified as a fresh install otherwise.
- **If none of these exist (fresh install)**, print:

  ```
  Plugin installed: crux v<X.Y.Z> (schema_version <N>)
  Next step: say "init docs" to bootstrap the docs tree in this project.
  ```

- **If any of these exist (upgrade of a bootstrapped project)**, do NOT print the "init docs" hand-off. Print instead:

  ```
  Plugin upgraded: crux v<X.Y.Z> (schema_version <N>)
  If schema_version changed, run `audit-docs --migrate` to apply schema migrations; otherwise no action needed.
  ```

- Do **not** invoke `init-docs` automatically. The user decides when to bootstrap.

### 6. Log the operation

If an upgrade actually happened in this session (the user ran the slash commands and the new version is confirmed), and the target repo has an existing tree (`.bionic.yml`, a `bionic/` tree, or a legacy `docs/` tree — same detection as step 5) whose `log.md` already exists (i.e., this was an upgrade of an already-bootstrapped project), append a `schema` op entry to that tree's `log.md`:

```
## [YYYY-MM-DD] schema | install-docs-skills (<install | upgrade>) v<X.Y.Z> schema_version <N>
```

Body, 1–2 lines:
- Before-version and after-version.
- Whether `audit-docs --migrate` is recommended.

If no tree exists yet (fresh project), there's no `log.md` to write to — skip the log entry. The next `init-docs` run will start the log.

## Verification checklist

- [ ] Installation state was detected via `${CRUX_PLUGIN_ROOT}` or the marketplace plugin cache — not by guessing.
- [ ] If present, `plugin.json` was read and `name == "crux"` was verified.
- [ ] Installed `version` and `schema_version` were reported to the user.
- [ ] The full skill list (and agent list, when present) from `plugin.json` was surfaced.
- [ ] The two marketplace commands were printed verbatim: `/plugin marketplace add bionic-coding/crux` and `/plugin install crux@crux`.
- [ ] No install action was attempted by the skill itself — marketplace commands are user-typed.
- [ ] Existing-tree detection checked for `.bionic.yml`, a `bionic/` tree, and a legacy `docs/` tree — never literal `docs/` absence alone.
- [ ] If the target repo has an existing tree, its `manifest.yml` schema compatibility was checked and reported.
- [ ] The hand-off ("next: say 'init docs'") was printed after a fresh install only — not after an upgrade of an already-bootstrapped project.
- [ ] If an upgrade was confirmed AND the existing tree's `log.md` exists, one `schema` op entry was appended.

## Red flags — STOP and reconsider

- About to run any shell command to install or upgrade the plugin. **Never.** There is no script-based install path; the marketplace flow is the only one, and it's user-typed.
- About to delete or rename anything under the plugin cache to "clean up". **Never.** A broken install is reported; the fix is re-running `/plugin install crux@crux`.
- About to bootstrap `docs/` from this skill. **Never.** That's `init-docs`. The skills are split on purpose.
- About to edit `.claude/settings.json` or any marketplace state by hand. The marketplace flow owns registration; this skill does not.
- About to report a plugin at some path as crux when its `plugin.json` says a different `name`. Refuse — could be a collision with another plugin.
- About to recommend an upgrade across a schema-incompatible jump without warning. If the schema bumps, recommend `audit-docs --migrate` AFTER the upgrade.
- About to invent install commands or paths. The commands are `/plugin marketplace add bionic-coding/crux` + `/plugin install crux@crux`, period.
- About to claim the plugin is installed because a directory exists but `plugin.json` is missing or malformed. Validate before reporting.
- About to key fresh-install-vs-upgrade detection on literal `docs/` absence alone. **Never.** A `bionic/`-only repo (the default layout) has no `docs/` at all; check for `.bionic.yml`, a legacy `.crux`, a `bionic/` tree, or a legacy `docs/` tree.

## Rationalization table

| Excuse | Reality |
|--------|---------|
| "The user obviously wants the install — let me find a way to run it." | Marketplace commands are user-typed slash commands. Print them; the user runs them. There is nothing for this skill to execute. |
| "I'll skip reading `plugin.json` since I know the structure." | The whole point of `plugin.json` is to be the truth. Read it. Reports about installed version, schema, skill list MUST come from the file. |
| "I'll auto-run `init-docs` right after install." | No. Install and bootstrap are separate user decisions. After install, hand off to the user. |
| "The directory exists, so the plugin is installed." | Existence is not validity. Validate `plugin.json` first. |
| "`schema_version` mismatch is fine — `init-docs` will sort it." | `init-docs` doesn't migrate. Mismatch needs `audit-docs --migrate` AFTER the plugin upgrade. |
| "I'll edit the plugin cache or settings myself to register the plugin." | That's the marketplace flow's job. Don't reimplement it. |
| "The user said 'set me up' — that covers everything including bootstrap." | "Set me up" is ambiguous. Report install state first, then ask about bootstrap. Two operations, two confirmations. |
| "I'll skip the log entry since the install isn't a docs op." | Plugin upgrades affect the docs schema; that's a `schema` op when the existing tree's `log.md` exists. |
| "There must be a curl/clone fallback for users without marketplace access." | There isn't. Marketplace-only distribution is the architecture. Don't invent one. |

## Common mistakes

- **Attempting to execute the install** instead of printing the commands. Slash commands run in the user's UI, not in Bash.
- **Skipping `plugin.json` validation** when reporting installed version. The directory's mere presence isn't proof of a valid install.
- **Auto-bootstrapping the tree after install.** Install and bootstrap are separate.
- **Forgetting the marketplace-add step** when guiding a fresh environment. `/plugin install crux@crux` fails if the `crux` marketplace was never added.
- **Writing to a tree's `log.md` for a fresh install** (where no tree, and so no `log.md`, exists yet). Skip the log entry on fresh installs; the next `init-docs` starts the log.
- **Using a non-`schema` op for the install/upgrade log entry.** The op enum is fixed; `schema` is the right op for plugin/schema-version changes.
- **Reporting the skill list from a directory listing** instead of `plugin.json`. The manifest is the truth; a stale or partial directory listing is not.
- **Treating a different-name plugin at the same path as crux.** If `plugin.json` says it's something else, surface that and stop.
- **Skipping the schema compatibility check** when the target repo has an existing tree (`.bionic.yml`, `bionic/`, or legacy `docs/`). Plugin version vs. schema version vs. target schema is a three-way check; do it before recommending upgrade.
- **Telling the user to run "init docs" after an upgrade of an already-bootstrapped project.** That's a fresh-install instruction. After an upgrade, the right next step is `audit-docs --migrate` (only if `schema_version` changed) — otherwise no action.
