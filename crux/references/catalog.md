---
title: Plugin catalog schema
read_when: Authoring a skill or role, or changing the plugin catalogs
sections:
  - "§7.A"
---

# Plugin catalog schema

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §7.A`, resolves to this file.

## 7.A. Catalog schema (`plugin.json` schema_version `"4"`)

The current SKILL.md frontmatter contract is **conformant to the public Agent Skills Spec** (the rationale for the revision: extended catalog fields must live where spec validators like `skills-ref` allow them, so the catalog layer rides under `metadata:` instead of inventing top-level keys).

`crux` ships a **catalog layer** above the skills. The catalog is four files under `${CRUX_PLUGIN_ROOT}/catalog/` plus extended `SKILL.md` frontmatter on every skill, validated by `skills-ref`. **The extension declares provenance:** `skills.json` and `agents.json` are regenerated projections whose hand-edits are blown away, while `bundles.yml` and `models.yml` are hand-authored sources of truth that `validate-catalog.py` checks and never writes. (`${CRUX_PLUGIN_ROOT}` is crux's own **portable, platform-neutral** name for the installed plugin root — it is NOT a loader-set variable. In Claude Code, assign it the value of `CLAUDE_PLUGIN_ROOT` (the variable Claude Code's plugin loader sets). In Codex, derive it from the absolute path of the selected `SKILL.md`: the plugin root is the parent of its `skills/` directory. In a source checkout, substitute the checkout's plugin directory. It is ephemeral across plugin updates: never write state under it; anything persistent belongs in `${CLAUDE_PLUGIN_DATA}` or `~/.crux/`.)

**Regenerative invariant** — `catalog/skills.json` is regenerated from `SKILL.md` frontmatter on every `validate-catalog.py` run. **Manual edits to `catalog/skills.json` are blown away** (same model as `docs/code/`). The skill files are the source of truth; the catalog is the projection. `catalog/bundles.yml` is hand-authored — the validator only checks it against the regenerated `skills.json` for referential integrity.

### `SKILL.md` frontmatter shape

Per the public Agent Skills Spec, the **top-level allowlist** for SKILL.md frontmatter is exactly: `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`. Any other top-level key fails `skills-ref validate`.

Top-level required:

| Key | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Must equal the skill's directory name. Lowercase, ≤64 chars, alphanumeric + hyphens. |
| `description` | string | yes | ≤1024 chars. Single-line free-form prose. |

Top-level optional (per spec):

| Key | Type | Required | Notes |
|---|---|---|---|
| `license` | string | no | License identifier. Free-form. |
| `allowed-tools` | string | no | Tool allowlist patterns. Experimental per spec. |
| `compatibility` | string | no | ≤500 chars. Compatibility constraints. |

**All crux extended catalog/governance fields live under `metadata:`** as a YAML mapping with flat string key/value pairs (the spec parser stringifies all `metadata.*` values). The contract is:

| `metadata.` key | Type at rest | Required | Notes |
|---|---|---|---|
| `tags` | CSV string | yes | 2-5 kebab-case ASCII tags. CSV format: `", "` (comma + single space). On parse: split on `,`, strip each token, reject empty tokens. |
| `bundles` | CSV string | yes | Bundle ids the skill belongs to. Same CSV encoding as `tags`. At minimum: `crux-core` or `crux-docs`. |
| `risk_level` | enum | yes | `low \| medium \| high`. Default: `low`. |
| `requires_access` | enum string | yes | The highest access the skill's default path needs: one of `read-local`, `run-plugin-script`, `write-run`, `write-tree`, `write-host`, each covering the ones before it. A step taken only under an opt-in is left out. A missing, empty or unknown value fails validation; there is no default. |
| `supplied_access` | enum string | no | The lower need the skill runs at when its caller supplies the output of the steps above it. It must be strictly lower than `requires_access`. |
| `requires_env` | CSV string | no | Env-var keys the skill needs at runtime. Each token must match `^[A-Z][A-Z0-9_]*$`. Empty string means "no env requirement." |
| `routing_note` | string | no | The optional Notes cell for the skill's routing-table row. |
| `triggers` | PIPE-separated string | no | The user phrases that route to this skill, projected into `catalog/skills.json` as a JSON array. The separator is `\|`, not the comma `tags`, `bundles` and `requires_env` use: a trigger is a natural-language phrase and may contain a comma, which a CSV split would cut in two. On parse: split on `\|` and strip each token; empty tokens are dropped. A non-string token is refused, and so is one carrying the separator, a control character, or a duplicate of another token. A skill that is `user-invocable: false` declares none, and that is not a gap. |

Each `requires_access` token names what the skill's default path does. `read-local` reads and searches local files, its own instructions included. `run-plugin-script` also runs a crux script or a private temporary driver, and writes only uv's cache and a private temporary directory. `write-run` also writes records inside a run directory, only through a vendored crux writer, its own commit included. `write-tree` also writes anything else under the repository, commits included. `write-host` also writes outside the repository. Choose the highest token over every operation's default path. Count the reference files that path routes to and the need of every skill it invokes. Leave out a step taken only under an opt-in: a flag, a named request, an accepted offer, or a mode the caller names. A role's envelope in a harness is what that harness's projection lets it do: its effective tools in Claude Code, its sandbox mode and shell permit in Codex, and its permission rules in OpenCode. An opt-in step above the envelope of a role that declares the skill still needs an instruction, in the role body or the skill body, that routes or declines it. Declare `supplied_access` only where the skill body names the output a caller supplies.[^access]

Concrete example:

```yaml
---
name: dev-cycle
description: "Use when the user says 'start a cycle'..."
metadata:
  tags: "promptbooks, workflow, cycle, planning"
  bundles: "crux-docs"
  owner: "crux"
  version: "0.1.0"
  risk_level: "low"
  status: "production"
  requires_access: "write-tree"
---
```

Skills that need runtime env vars additionally carry `requires_env` in the `metadata:` block.

### `catalog/skills.json` shape

`validate-catalog.py` lifts the extended fields out of `metadata:` and emits the catalog JSON in the FLAT shape consumers use. CSV strings under `metadata:` are split on `,` and emitted as JSON arrays — only the wire-format SKILL.md frontmatter carries the CSV encoding.

JSON array. One object per skill. Sorted alphabetically by `id`. Keys within each object in fixed order.

```json
[
  {
    "id": "init-docs",
    "name": "init-docs",
    "description": "Use when ...",
    "tags": ["bootstrap", "initialization", "scaffolding"],
    "bundles": ["crux-docs"],
    "owner": "crux",
    "version": "0.1.0",
    "risk_level": "low",
    "status": "production"
  }
]
```

`id` matches the skill's directory name under `skills/`. `name` and `description` mirror the frontmatter (no edits). The list-valued fields (`tags`, `bundles`, `requires_env`) appear as JSON arrays even though they live under `metadata:` as CSV strings in SKILL.md — the validator round-trips them.

### `catalog/bundles.yml` shape

A top-level block mapping keyed by bundle id. The mapping key IS the `id`, so it is not repeated inside the value.

```yaml
example-bundle:
  name: "example bundle"
  description: "Illustrative only — not a bundle this repo ships."
  audiences:
    - "software-project-maintainers"
  default_provision: false
  skills:
    - "some-skill-id"
    - "another-skill-id"
```

The id above is deliberately fictitious. An example that copies a real bundle's
values goes stale the first time that bundle is edited, and a stale example in a
schema document is read as the schema. Read `catalog/bundles.yml` for live values.

Required keys per bundle: `name`, `description`, `audiences`, `default_provision`, `skills`. `skills:` lists skill `id`s; every entry must resolve to a skill in `catalog/skills.json`, and every skill whose frontmatter names a bundle must appear in that bundle's list — the validator enforces the first direction and the audit enforces both.

The file is read through the shared minimal-YAML loader on a strict path that refuses an anchor, an alias, a merge key, an explicit tag, a second document, and any duplicate key, and that requires a non-empty mapping root. Those refusals are why the shape is a mapping and not a sequence: a top-level sequence parses to an empty mapping on both parse paths, which reads as a clean run over zero bundles.

### Validator contract

`${CRUX_PLUGIN_ROOT}/scripts/validate-catalog.py`:

- `--dry-run`: parse + validate + emit JSON diff to stdout; do not write files. Exit 0 if no drift, exit 1 if drift (with valid JSON on stdout).
- (no flag): regenerate `catalog/skills.json` and `catalog/agents.json` from frontmatter; validate every hand-authored catalog file named in the validator's `CATALOG_TARGETS` — `bundles.yml` against the regenerated skills, and `models.yml` against its schema rules; exit 0 if everything resolves.
- Non-zero exit with empty/unparseable stdout: extractor crash, malformed config, or missing language toolchain. Surface stderr.

The JSON payload carries a top-level `warnings` key alongside `validation_errors`: a
list of findings that are reported but **do not affect the exit code**. It exists so a
tree that passes today does not turn red tomorrow on the passage of time alone — the
staleness clock on a `models.yml` `verified:` date is the current member. Read
`warnings` when reporting validator state; a run with `warnings` non-empty and exit 0
is a passing run with something worth looking at, not a failure.

Same exit-code semantics as `uv run --no-config "${CRUX_PLUGIN_ROOT}/scripts/extract-code-docs.py" --dry-run`. The two scripts are sibling validators.

[^access]: rule:skill-declares-its-access-need, rule:access-need-covers-the-mandatory-path, rule:opt-in-above-the-envelope-is-routed, rule:supplied-access-is-below-required-access
