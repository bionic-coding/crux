---
title: Per-repository configuration
read_when: Resolving or changing `.bionic.yml`, the tree location or the artifact prefix
sections:
  - "§14"
---

# Per-repository configuration

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §14.2`, resolves to this file.

## 14. Per-repo configuration — the repo-root `.bionic.yml` file (superseding the legacy `.crux`)

A repository MAY carry a single optional YAML file named `.bionic.yml` at its root as the **layout source of truth**. It **supersedes the legacy `.crux` file** — named for the destination methodology, not the tool, so the durable home still makes sense if crux is ever replaced. A legacy `.crux` is still read for back-compat (see the precedence chain in §14.1). Current Crux writes an explicit `.bionic.yml` for every tree it creates (`init-docs` on bootstrap). The pinned public `v3.23.2` release wrote it during its historical rung 4→5 migration; the current release has no tree migrator. The optional, zero-config posture applies to a pre-existing tree Crux did not create or migrate. The file is **designed to be committed so the team shares one config — everything works identically untracked.** **Disambiguation (always spell it this way in prose): this is the repo-root `.bionic.yml` / legacy `.crux` FILE surface (shareable project config) — distinct from the user-home `~/.crux/` DIRECTORY (uncommitted secrets, §13).** Both files share one grammar (v1 schema); `.bionic.yml`:

```yaml
# .bionic.yml — per-project layout source of truth (config_version 1)
config_version: "1"        # REQUIRED. String, like every other crux version field.
docs_dir: bionic           # OPTIONAL. Repo-root-relative path to the documentation tree. Default: "bionic"; init-docs always writes this key explicitly for trees it creates.
artifact_prefix: ""        # OPTIONAL. ^[A-Z][A-Z0-9]{1,9}$ or blank. Blank/absent = bare ids.
```

A legacy `.crux` uses the identical keys and validation (the surface moved, not the semantics — same grammar, same `prefixed()`, same textual + containment validation). Note: `docs_dir` names the tree. New trees are created at `bionic/`; an existing schema-5 `docs/` tree keeps working at its configured location. The current `audit-docs --migrate` changes instruction files only. The ledger and its check suite live together inside that tree — there is no separate peer root.

### 14.1 Resolution contract

- **File precedence:** `.bionic.yml` present → authoritative; else a legacy `.crux` present → read it (superseded, retained for back-compat, no warning); else content-validated bare-directory discovery, then the built-in default `bionic`. Among *explicit config files* the **new** one wins (`.bionic.yml` > `.crux`); a malformed/dangling `.bionic.yml` is fail-loud on its own tier and **never** falls through to `.crux`.
- **Repo root only.** The repo root is *defined* as: the explicitly passed `--repo-root` flag when a consumer offers one; otherwise the process working directory at invocation. No upward walk, no `git rev-parse` — a parent directory's config must never silently capture a nested repo.
- **Absent both files → bare-directory discovery, then the default.** A directory counts as a tree when its `manifest.yml` parses and carries both `schema_version` and `concerns_enabled`. The resolver then applies three cases. Two matching directories: it refuses loudly, naming both, unless a migration marker records one of them as the source. Exactly one matching directory: it resolves there — so a legacy `docs/` tree keeps working with zero config. No matching directory: it resolves to the default, `bionic`. One deliberate tightening applies even with no config present: the containment check runs on every resolution, so a resolved tree directory that is a symlink escaping the repo root fails loud rather than being followed.
- **Malformed or invalid file → fail loud** (exit 1 with the validation error). NEVER fall back to defaults or the lower-precedence file: silently writing artifacts into `./docs/` with bare ids when the user configured otherwise would split the tree.
- **Forward compat:** unknown top-level keys are ignored on read (the forward-compat valve for future config), but an unsupported `config_version` is refused loudly.
- **Precedence, per flag class:** explicit CLI flag > config file (`.bionic.yml` > `.crux`) > built-in default. `--repo-root` governs only where the config file is looked up; each explicit path flag (`--config`, `--output-dir`, a future `--docs-dir`) overrides only its own derived default; non-path flags are unaffected by the config file entirely.

### 14.2 How skills resolve it

Prose skills MUST resolve the layout config by invoking the CLI — canonically `python3 "${CRUX_PLUGIN_ROOT}/scripts/bionic-config.py" [--repo-root PATH]` (the retained `crux-config.py` is a back-compat delegator; both emit the same JSON, with `source` reporting `".bionic.yml" | ".crux" | "discovery:<dir>"` (plus combined forms like `".bionic.yml+discovery:<dir>"` when a keyless config falls through to discovery)) — and NEVER by reading the YAML ad hoc, so the two-file precedence + textual + containment validation in `bionic_config.py` (the single implementation; `crux_config.py` re-exports it) always runs. On exit 1, STOP and surface the error. A skill that cannot invoke the CLI MUST refuse any `docs_dir` it cannot prove passes the textual layer (in particular any absolute, `~`-prefixed, or `..`-containing value) — refusal, never a silent fallback.

**Normative definition clause:** within every crux skill, agent definition, and template, a literal `docs/` path segment **denotes** `<docs_dir>/` as resolved by this section. The literal spelling is the default *rendering*, not a binding location — skill prose stays correct in a relocated tree without a per-file rewrite.

### 14.3 Artifact prefix rules

- Grammar: `^[A-Z][A-Z0-9]{1,9}$` (2–10 chars, uppercase alphanumeric, starts with a letter, no hyphen). The reserved type tokens `PB`, `ADR`, `RUN`, `BRIEF` are rejected as prefix values.
- The prefix **prepends the whole id** with a literal `-`: `CRX-PB-NNNN`, `CRX-ADR-NNNN`. The prefixed string IS the id — verbatim on every surface (filenames, YAML `id:`/`book_id:`/`forked_from:`, ADR frontmatter, wiki-links, indexes, operations-log subjects).
- **`RUN-NNN` and `BRIEF-<slug>` are NEVER prefixed** — run ids are book-scoped (the run dir + `book_id` carry the prefix); briefs are slug-keyed.
- **Ids are immutable history.** Adopting or changing a prefix never renames existing artifacts; a mixed bare/prefixed tree is valid (one repo SHOULD converge on one prefix — `audit-docs` CHK-CFG-2 warns).
- **Allocation is unchanged:** the §7 manifest counters (`adr.next_number` / `promptbook.next_number`) still supply the `NNNN` — monotonic, never reused, one shared sequence per artifact type regardless of prefix. The prefix is applied only when *formatting* the new id. Filesystem scans MUST use the dual-form regex `([A-Z][A-Z0-9]{1,9}-)?(PB|ADR)-(\d{4})` and take max/uniqueness over the digits capture across bare AND prefixed spellings.

### 14.4 Boundary — three config surfaces

| Surface | What it holds | Lifetime |
|---|---|---|
| repo-root `.bionic.yml` *file* (legacy `.crux`) | Pre-tree bootstrap config: anything you must know *before* opening the docs tree, or that brands artifacts repo-wide (`docs_dir`, `artifact_prefix`) | Designed to be committed so the team shares one config (works identically untracked) |
| `docs/manifest.yml` | The tree's own state: `schema_version`, `concerns_enabled`, extractors, counters | Lives inside the tree, alongside it |
| `~/.crux/` *directory* | User-scoped secrets and env vars (§13) | User home, NEVER committed |

**Never put secrets, tokens, or keys in the repo-root `.bionic.yml` (or legacy `.crux`) file** — it is designed to be shared and committed. Unknown keys are silently ignored (forward compat), so a misfiled secret would not even error; secrets belong only in the user-home `~/.crux/` directory (§13).
