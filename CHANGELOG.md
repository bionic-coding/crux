<!-- generated-from: CHANGELOG.md@sha256:46a0e0dbb43d942e8a8a163042273a131c30b86431ee325ba85bef9f70235415; model: claude-fable-5.1; date: 2026-09-07 -->
# Changelog

All notable changes to crux. The format roughly follows [Keep a Changelog](https://keepachangelog.com/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [3.9.0] — 2026-09-07

### Added

- **`review-decisions`, a periodic architect review of your decision set.** The skill reads your accepted ADRs as a set and asks whether they still serve the project's objectives, working from the doctrine index and the summaries rule table and opening an ADR body only where a signal flags a domain. It writes at most five findings into one dated report at `docs/adrs/reviews/YYYY-MM-DD.md` and only proposes: it transitions no record, signs off no batch, and authors no skill.
- **`adr-signals.py` computes five mechanical signals over the ADR set.** The stdlib-only script reports amendment fan-in, carve-out count, paper-only status, dormancy, and friction citations, each as a uniform record with `signal`, `verdict`, `value`, `basis`, and `filter` fields and no severity or recommendation. `friction_citations` reports `unmeasurable` rather than `0` when a tree has no journal reflective sections to read.
- **A reviews index, regenerated and drift-gated.** `generate-reviews-index.py` derives `docs/adrs/reviews/index.md` from the dated reports and fails closed on a filename outside the `YYYY-MM-DD.md` grammar or a report whose frontmatter disagrees with its filename. A tree with no reviews directory is neither drift nor a refusal: both modes exit 0 and set `"surface_absent": true`, which `check-drift` reports as N/A rather than as a clean gate.
- **An objectives file, `docs/objectives.md`.** It holds the project's mission and `OBJ-N` goals (each with a kind, statement, measure, and status), a `maturity` ladder saying what may still drift, and an append-only `## Shifts` table. `init-docs` seeds it as a placeholder; every reader asks the owner to fill it in rather than citing a placeholder.
- **Lint rules for objectives and review cadence.** `audit-docs` gains five `CHK-OBJ-*` rules over `docs/objectives.md`, including a WARNING when `reviewed_at` is older than `review_every_days`. `cleanup-campsite` gains `CLN-ADR-5` (a decision review older than `adr_review_due_days`, default 7) and `CLN-OBJ-1` (an objectives file still at `maturity: placeholder`), for 20 rules total. The log op enum gains `adr-review`.

### Changed

### Fixed

- **A second `review-decisions` pass on one date no longer overwrites the first.** The skill now refuses an occupied report path and amends the existing report in place, keeping every earlier finding id.
- **`adr-signals.py` reads doctrine rows whose rule text contains an escaped pipe.** Such rows previously vanished silently and could mark an ADR rowless or paper-only; the parser now splits on unescaped pipes only.
- **The friction signal reads the forge log under every runtime's local skills directory.** It previously read only `.claude/skills/forge-log.md`; it now also reads Codex's `.agents/skills` and OpenCode's `.opencode/skills` / `.opencode/skill`.
- **A future-dated review report is refused.** `generate-reviews-index.py` now rejects a report dated after `--today` (default: the system date), and the gardener applies the same filter, so one file can no longer suppress the review-cadence reminder indefinitely.

### Removed

## [3.8.0] — 2026-09-04

### Added

### Changed

- **Async text and image councils use GPT-6 Astra as their OpenAI judge.** Astra replaces Sol in the `openai_top` role through OpenRouter, pinned to OpenAI as the serving provider. The synchronous council keeps its Terra seat.
- **Council Fable judges use Fable 5.1.** The high- and medium-effort entries replace Fable 5.0 while preserving their effort settings; other callers of the shared Anthropic roles also receive Fable 5.1.
- **Codex apex roles (commander and reviewer) use GPT-6 Astra with high effort.** Codex flagship and standard roles keep Sol and Terra.

### Fixed

### Removed

## [3.7.1] — 2026-09-02

### Added

### Changed

### Fixed

- **Every script's PEP 723 header now declares the real Python floor, 3.11.** Fifty-two scripts said `>=3.10`, but the Python arch pack uses `tomllib` (stdlib from 3.11), so a 3.10 run failed on the environment rather than the code. The headers, the user guide, and the schema example now say 3.11; four corpus-golden comparison tests skip below 3.13 with a named reason.
- **The README states the Python floor and the test command.** The test suite needs the tree-sitter grammar packages that only the PEP 723 headers name, so a bare `pip install` environment failed ~140 arch-pack tests. The Requirements section now carries the `uv run` invocation that resolves them.

### Removed

## [3.7.0] — 2026-09-02

### Added

- **The skill runtime-compatibility block is now generated from one canonical source.** The block that most `SKILL.md` files carried by hand is regenerated from a single template and checked by a `--dry-run` drift gate.

### Changed

- **Breaking: the OpenCode projection now emits the V2 schema exclusively.** The generated OpenCode agent files replace the singular `permission:` map with an ordered `permissions` array of `{action, resource, effect}` rules under last-match-wins, and two actions are renamed: `bash` becomes `shell`, and `task` becomes `subagent`. The install target moves from `.opencode/agent/` to `.opencode/agents/`. `install-opencode-agents` gains `--migrate-legacy-agent-dir` to move a populated legacy directory into the new target (refusing on a name collision unless `--force`), and runs a V2 preflight that refuses when no `opencode2` binary is discoverable. A V1 OpenCode runner reading the new projection drops every deny with no warning; this is an accepted residual risk if you have not upgraded to V2.
- **The commander can dispatch the wayfinder.** Its agent allowlist gains `wayfinder`, for sizing up a large, uncertain, or external source before another agent spends context on it; the OpenCode projection carries the matching `subagent` allow rule.
- **`dev-lead` routes to GLM 5.3 on OpenCode.** The model catalog row moves from `kimi-latest` to `glm-latest` (`openrouter/z-ai/glm-5.3`); the Claude and Codex seats are unchanged.

### Fixed

- **`web-to-markdown` passes a Markdown or plain-text response through unchanged.** A `text/markdown` or `text/plain` body previously went through the HTML converter and came out as one collapsed line; it is now emitted as-is, with the title taken from its first heading.

### Removed

## [3.6.0] — 2026-09-02

### Added

- **A decision is now cited as `rule:<slug>`, the slug half of the governs handle that carries the rule.** The form is identical in code comments, prose, promptbook prompts, and journal refs. The linter that resolves the token now has a default scope over authored sources; an empty resolved scope fails the gate rather than passing on zero files, an unknown slug fails, and a retired slug fails naming every live rule that displaced it.

### Changed

### Fixed

- **The archive-tier ADR readers in the summaries projection no longer follow a symlink out of the tree.** An `ADR-*.md` symlink planted in `adrs/archive/` was previously read from outside the repository; both readers now refuse a symlink with the same message the active-tier reader uses.
- **The `srde` skill's batch example now builds `DissentPoint` objects,** which is what `attempt_batch_resolution` takes, instead of passing raw dissent strings.
- **The plugin's own README now says 59 skills** (it said 55) and is held to the on-disk count going forward.

### Removed

## [3.5.0] — 2026-08-31

### Added

- **Batch ratification for observations: the `survey-sheet` and `survey-signoff` skills.** `survey-sheet` scaffolds one `SVY-NNNN` review sheet from the candidate state file, seeding `anchor_id` and `proposed_domain` and leaving `verdict`, `domain`, and `rationale` for you. `survey-signoff` is the single human sign-off that publishes the sheet under one digest-bound receipt; one signature equals N individual ratifications and is the only batch route past `observed`. Both carry `disable-model-invocation`; `audit-docs` gains four `CHK-OBS-SURVEY-*` rules.
- **The `fix-directly` skill: the rung below the three cycle tiers.** "Just fix it" now routes to a named contract — no book, no council; a failing test first, the smallest green change, the suite and the drift gates, one commit, one `log-work` entry. A five-question sizing test decides between it and `patch-cycle` / `iterate` / `dev-cycle`; a security label sets a defect's priority, not its size.

### Changed

- **`cleanup-campsite` retires `CLN-ADR-1`.** The rule reported an accepted ADR unmentioned in README/USER_GUIDE within 30 days and only ever accumulated findings; its id stays retired with a stub, and 18 rules remain implemented.
- **The verify templates carry a reproduction budget.** The `iterate` verify module and the `patch` verify phase now state that a failing test is a complete reproduction, a class earns its own reproduction only at a second independent instance, and a security label must not widen the fix. The `whiteboarding` skill gains a sizing step and the same one-instance-is-a-bug rule.

### Fixed

- **Three survey sign-off defects.** A `config_version: "1"` sheet beside a receipt skipped `assert_signable` on the resumed-batch path (it now runs on every publish path; v1 stays readable for digest verification only); the index retire loop tore an escaped `\|` in a `domain` cell (it now splits on unescaped pipes only); and `CHK-OBS-BIJECTION` grepped the whole index page so a mined cell could forge or suppress a finding (it now reads each row's id column).
- **The arch drift gate no longer treats the decision-recovery state file as a stale artifact.** `derive-arch.py --dry-run` now excludes `arch/_recovered/`, which the first `recover-decisions` run writes by design; a stray file anywhere else under `arch/` still drifts.

### Removed

## [3.4.0] — 2026-08-30

### Added

### Changed

- **The OpenCode commander runs Qwen3.8 Max (1M context) instead of Kimi K3,** which could not sustain the orchestration role. Every other role's OpenCode model is unchanged.
- **Each arch stack-pack probe now declares its own input class against a committed roster.** The doctrine index's `implemented` column is renamed `basis`, and a `governs` entry's new `retires` sub-field displaces a rule while keeping its record on the ledger.
- **Breaking: a `governs` entry's sub-field set is now closed.** `summarize-adrs.py` and `compile-doctrine.py` both hard-refuse an unrecognized sub-field, so a tree carrying any other annotation key fails both regenerators on upgrade.

### Fixed

- **A book's `current_run` pointer now survives a run's completion,** so `archive-promptbook` can read the pointer its own precondition requires. `current_run` now nulls only at archival, by exactly one writer.

### Removed

## [3.3.0] — 2026-08-30

### Added

- **A repository that has never authored an ADR can now build a doctrine from what its code already does.** The `observations` concern adds `OBS-NNNN` records of observed behavior, each evidenced by a `path:line-range` and ratified by a human; a ratified record projects into the summaries rule table and the doctrine index beside the ADRs.

### Changed

- **`derive-arch` records a per-concern verdict instead of grading its own confidence.** A concern is `populated` or `stubbed`, and every stub names one reason from a closed set of six. The new `arch.require` list in `manifest.yml` fails the derive when a required concern is not `populated`.
- **The arch extractors read committed artifacts and real parsers, never regular expressions over source.** Python routers parse through the standard-library AST; Ruby reads a committed `rails routes` dump; Ruby, Node, and Elixir source parses through tree-sitter grammars declared in the script's dependency block. Node routes now compose `app.use` mount prefixes, and Elixir routes parse the parenthesized form. On a ten-repository corpus, the stubbed-concern rate outside `decision-index` fell from 13 of 30 to 2 of 33.

### Fixed

### Removed

- **The `arch_confidence_threshold` key in `.bionic.yml` is retired.** A tree that still sets it loads clean and produces no attribute.

## [3.2.2] — 2026-08-29

### Added

### Changed

### Fixed

- **The agent-catalog strict-YAML test skips cleanly without PyYAML** instead of reporting a spurious failure in an environment without it.

### Removed

## [3.2.1] — 2026-08-29

### Added

### Changed

### Fixed

- **The cycle machinery can accept ADRs and archive books again.** `transition-adr` and `archive-promptbook` no longer carry `disable-model-invocation`, which had blocked `dev-cycle`, `iterate`, and `patch` runs from accepting an ADR or archiving a completed book without a human keystroke. A guard test now fails if any skill named in a cycle template's `side_effects` carries the field; the four true human gates (`reconcile-signoff`, `backfill-signoff`, `escalate-arch-runtime`, `transition-invariant`) keep it.

### Removed

## [3.2.0] — 2026-08-28

### Added

### Changed

- **Corrected the OpenCode `permission.task` projection.** A restricted `Agent(role)` grant now projects as a faithful deny-first per-role glob object instead of collapsing to a coarse boolean. The widened-grant report, its sign-off file, and the `report_drift` dry-run key are retired as unneeded.
- **Documented the fields OpenCode ignores.** A runtime-compatibility note records that `$adr`/`$book` argument placeholders bind only in Claude Code, and a new `OPENCODE_GUIDE.md` section lists the invocation-control fields OpenCode does not honor.
- **The model catalog no longer disables `fable`,** so it is a routable agent `model:` value again.

### Fixed

- **`forge-skill`'s frontmatter guidance matches the schema-3 metadata contract.** It no longer names the removed `owner`/`version`/`status` keys, so a forged skill promoted into the plugin passes `validate-catalog`.

### Removed

## [3.1.0] — 2026-08-28

### Added

- **`compile-doctrine` — the skill front for the doctrine regenerator.** It regenerates the `adrs/doctrine/` directory wholesale from the summaries projection, reconciled against ratified invariants and the human-signed reconciliation ledger; `--dry-run` is the drift check. It stops and recommends `summarize-adrs.py` first when the summaries projection has drifted, and never writes the reconciliation ledger.
- **`check-drift` — a read-only runner for every enrolled drift gate.** It runs each regenerator's `--dry-run` in one pass and reports one table of gate, verdict (clean / drift / broken / crash / refusal), drifted paths, and the regenerator that fixes it. It regenerates nothing and is wired into `audit-docs` as `CHK-DRIFT-1`.
- **`reconcile-signoff` — the single human write path for one doctrine reconciliation.** It renders the invariant text and the rule text, takes the verdict (compatible / reconciled / collision) and rationale from you, then upserts a digest-bound record and re-compiles doctrine on explicit confirmation. It never chooses a verdict and never batch-signs; `audit-docs` `CHK-DOCTRINE-1` counts pending pairings and points to it.
- **A signed sign-off for the OpenCode widened-grant report.** A sign-off file names each agent role whose OpenCode restriction is unenforceable, with rationale, signer, and date, and a test asserts it matches the live report exactly.

### Changed

- **Catalog schema 3: invocation-control frontmatter and a constant-metadata prune.** `SKILL.md` now admits the Claude Code invocation-control keys (`disable-model-invocation`, `user-invocable`, `context`, `agent`, `model`, `effort`, `background`, `arguments`, `disallowed-tools`), and agents admit `maxTurns`, `effort`, `skills`, `memory`, `isolation`, and `disallowedTools`, each projecting to Codex and OpenCode by a locked faithful-or-drop table. The dispatch tool `Task` is renamed to `Agent` (with the restricted `Agent(role)` form). **Breaking for skill authors:** the constant metadata keys `owner`, `version`, and `status` are removed from every skill and agent, and a lingering one is now a validation error. The skill invocation table is now regenerated from skill frontmatter and gated by `--dry-run`. `plugin.json` `schema_version` goes `"2"` → `"3"`.

### Fixed

- **A block-style `disallowedTools`/`skills` agent frontmatter list now fails validation instead of silently mis-projecting** (previously `bash` rendered `allow` instead of `deny` in the generated OpenCode agent file). Every shipped agent already authors these inline.

### Removed

- **Retired the `inject-knowledge` skill.** Its bundled knowledge layer shipped only a README and nothing referenced it; the skill, its module, its `crux-core` bundle membership, and its catalog rows are removed. Git history is the recovery path.

## [3.0.0] — 2026-08-28

### Added

- **The doctrine layer — a third ADR-decision tier, compiled and reconciled.** `adrs/doctrine/` projects each governs domain's live rule, disposition, and implemented-vs-on-paper state from the summaries projection, reconciled against ratified invariants through a digest-bound, human-signed ledger, with a deterministic regenerator and a drift gate. Reads now route doctrine → summaries → ADR body, with the ADR body winning on disagreement.

### Changed

- **The `qwen-max` OpenCode model alias points to `openrouter/qwen/qwen3.8-2.4t-a95b`.** The standard-rung OpenCode agents — historian, librarian, and wayfinder — resolve through it.
- **The architect agent's OpenCode model is now the flagship default `kimi-latest` (`openrouter/moonshotai/kimi-k3`),** dropping its per-agent `glm-latest` override.

### Fixed

### Removed

## [2.2.0] — 2026-08-28

### Added

- **Governs backfill machinery — a historic ADR can now enter the summaries projection.** An ADR numbered below `adr.governs_from` joins the projection only through an anchored, digest-bound, reviewed, at-most-once backfill. The increment adds the `anchor` `governs` sub-field, the enforcing checks, a `backfill-reviews.yml` receipts manifest, the `backfill-signoff` owner-gate skill, and the `backfill` log op.

### Changed

- **The "Silver" ADR-summary layer is renamed to "summaries".** `adrs/silver/` → `adrs/summaries/` and `generate-silver.py` → `summarize-adrs.py`. Forward-only: frozen ADR bodies, `log.md`, the journal, and archived runs keep "Silver" as history.

### Fixed

### Removed

## [2.1.0] — 2026-08-26

### Added

- **ADR frontmatter gains a `governs` block, and a regenerator projects it.** An ADR may now author a `governs` entry — `domain`, `rule`, `scope`, `handle`, `provenance` — cohort-bound by the new `adr.governs_from` manifest field. `generate-silver.py` projects every block into a rule table, a resolver, and an ADR↔run implementation map, behind its own `--dry-run` drift gate; a coverage gate and a two-tier reference linter distinguish a rule handle from a plain ADR citation. The rule table coexists with the arch decision-index.

### Changed

- **Model calls crux itself performs now route through OpenRouter as a single inference gateway.** The router, the council, the catalog aliases, and the video transcriber resolve every call through one OpenAI-compatible endpoint under one `OPENROUTER_API_KEY`. The direct Anthropic/OpenAI/Google SDKs and the Fireworks provider are retired.

### Fixed

### Removed

## [2.0.1] — 2026-08-25

### Added

### Changed

### Fixed

- **Release tooling in the development repository no longer misreports on a machine whose default `python3` predates the required interpreter.** Every release-gate invocation now routes through `uv run`, and the development repository pins Python 3.13 via a `.python-version` file. No plugin behavior change.

### Removed

## [2.0.0] — 2026-08-25

### Added

- **Arch drift is CI-gateable.** `derive-arch.py --dry-run` exits 1 for drift only when it has put a JSON payload on stdout; every other failure means the gate did not execute, so a CI job can tell a stale `arch/` tree from a broken run.
- **A deterministic per-derive coverage report.** `arch/_meta/coverage.json` records, for each spine concern, whether it populated or fell back to a stub, and why. It is byte-stable and rides the existing drift gate.
- **Confidence-graded arch extraction.** Each spine concern self-assesses a grade — high, medium, low, or none — stored in the coverage report. At or below the new `arch_confidence_threshold` config key (default `low`), a stubbed or partial concern offers an attended runtime-escalation session in chat; `none` is never offered. The unattended pipeline stays static and deterministic.
- **A model catalog — one hand-authored file decides which model every agent runs on.** `crux/catalog/models.yml` (`schema_version 2`) carries a provider allowlist, an alias table that is the only place a model id appears, the ten-agent roster keyed to three levels (`apex`, `flagship`, `standard`), the level table, and the `claude_aliases` / `claude_disabled` pins. A shared reader refuses a malformed catalog rather than degrading to a partial roster.
- **Validator rules V0–V9 over the catalog.** `validate-catalog.py` checks the roster against the agent files, every alias against the provider allowlist, each level's cells, the Codex slugs against the router registry, and the confinement of every document-derived key; `--dry-run` is the gate.
- **Python import-only runtime arch introspection, behind an attended two-factor consent gate.** The new `escalate-arch-runtime` skill runs a target FastAPI, Flask, or Django app's import-time code in a subprocess-isolated child, recovering its route table and ORM schema, and files the result as an advisory outside the arch spine. It executes only with `CRUX_ARCH_ALLOW_RUNTIME=1` set and a per-execution, non-model-mediated permission event.
- **A third cycle tier, `patch`, with a blast radius the archive gate checks.** `patch-cycle` authors a five-phase book at one prompt each, and the book declares the repository paths it may touch before its run starts. `archive-promptbook` draws the paths the run actually changed from git and refuses to archive a run that reached outside the declaration; the declaration is frozen by `book_content_hash` and `base_commit` is pinned at both ends.
- **An ADR body content rule with a gate.** An ADR body states requirements and postconditions, carries a 120-line budget over its four narrative sections, and names a source of truth rather than restating it. `audit-docs` gains `CHK-ADR-SPEC`, inert in any tree that has not set the new `adr.spec_rule_from` cohort boundary.
- **Two arch spine files are now thin projections, and readers have a route to the spine.** `arch/api-surface.md` and `arch/decision-index.md` are projected from the skill catalog and the ADR index instead of re-parsing those sources; a stale input is refused at exit 2 naming which regenerator to run. `query-docs` gains an architecture route, and all ten role definitions name `arch/` first for a question about the project's own shape.

### Changed

- **Council rounds are routed by blocking findings, and SRDE is de-wired from the ADR path.** A round past the first fires only on a finding that names a failing check against an artifact inside the work tree; round 3 is one adjudicator who is not the runner, inside the unchanged three-round bound. SRDE stays wired to the verify path.
- **The OpenCode and Codex projections no longer carry their own model tables.** Both regenerators, both installers, and the plugin-load smoke test resolve through the model catalog instead.
- **In `crux/catalog/`, the file extension now declares provenance.** `.json` means regenerated from a source of truth elsewhere; `.yml` means hand-authored, validated, and never written by a generator. `CHK-CAT` coverage reaches every catalog file.

### Fixed

- **The arch drift gate no longer fires on edits that leave the spine byte-identical.** `--dry-run` byte-compared a manifest carrying a SHA-256 per tracked source, so editing any tracked source reported drift; it now compares every property of that file except the `sources` values. `derive-arch.py` also declares PyYAML, so one source tree no longer produces two spine hashes.
- **The runtime arch-introspection executor's entry point is genuinely stdlib-only** and no longer crashes with `ModuleNotFoundError: httpx` in a shipped install. The `escalate-arch-runtime` child-env docs no longer mention `PYTHONPATH`.
- **The runtime introspection child no longer writes bytecode into the installed plugin.** `sys.dont_write_bytecode` is now set before the module load rather than after.
- **The curated decision-index path was unreachable.** A new `arch_decision_index_mode` config key makes the curated mode selectable; the default stays `complete`, so there is no behavior change without it.

### Removed

- **Breaking: per-advance run bookkeeping and three promptbook surfaces.** `run-promptbook` no longer writes a `log.md` op or regenerates the promptbooks index per advance; the `promptbook` op is written at authoring, run start, and archive only, and a run's per-prompt chronology comes from its snapshot timestamps. The `cycle-status` skill is deleted and every trigger phrase moves to `visualize-run-progress`. The per-prompt `blocked_confirmed` flag is retired; archive eligibility is now a run-level property. `author-promptbook --fork-from` is deleted — change a plan mid-run by abandoning the run and authoring a successor book.
- **Breaking: `crux/catalog/bundles.json`** is replaced by `crux/catalog/bundles.yml`, a mapping keyed by bundle id, read through a loader that refuses anchors, aliases, merge keys, explicit tags, and a second document. The catalog ships inside the plugin, so no downstream repo owes a migration.

## [1.14.0] — 2026-08-18

### Added

- **An Elixir/Phoenix arch stack pack — completing the batteries-included set (Python, Ruby, Node, Elixir).** The interface surface comes from a committed OpenAPI spec, else a static parse of the Phoenix router (never booting the app), including `resources` expansion, nested resources, `scope` prefixes, and LiveView routes; the data model comes from Ecto schemas, with the `null` column honestly left blank for non-key columns; the module graph keeps an edge only when it resolves to an in-repo module. A fail-closed, sigil-aware scrubber degrades an unparseable file to a hashed note rather than a wrong parse.
- **A Node.js arch stack pack.** The interface surface comes from a committed OpenAPI spec, else a static scan of Express, Fastify, and NestJS routes; the data model from Prisma's `schema.prisma`, else TypeORM `@Entity` classes or Sequelize models; the module graph from explicit TS/JS imports with `tsconfig` `@/*` alias resolution. All parsing is static and never boots Node, reads are confined under the repo root, and rendered content is escaped.
- **A Ruby arch stack pack.** The interface surface comes from a committed `openapi.json` when present, else a static parse of `config/routes.rb`; the data model from `db/schema.rb`; and the module graph from a resolve-or-drop pass over the Zeitwerk autoload roots. All parsing is static and stdlib-only.

### Changed

### Fixed

### Removed

## [1.13.0] — 2026-08-17

### Added

- **Pluggable arch stack packs, with a Python pack.** `derive-arch` detects the project's stack and resolves each spine file through a per-concern probe registry: a per-repo override, then the detected pack, then a stub. The Python pack derives the interface surface from a committed `openapi.json`, the data model from SQLAlchemy models plus the Alembic migration history, and the module graph from the project's own package. Two `.bionic.yml` keys configure it: `arch_stack` pins the pack, and `arch_extractors` registers a per-repo override that runs only under `CRUX_ARCH_ALLOW_OVERRIDES=1`.

### Changed

### Fixed

### Removed

## [1.12.0] — 2026-08-17

### Added

- **`install-opencode-agents` skill** — the OpenCode counterpart to `install-codex-agents`. Say "install the Crux agents in OpenCode" to write the ten projected roles into that project's `.opencode/agent/`. It refuses to overwrite a locally modified role without `--force`, refuses a crux-managed entry that is a symlink, refuses when the target resolves outside the repo root, and never touches a project's own agent files. Skill count 49 → 50.
- **A shared OpenCode projection module** backs both the regenerator and the new installer, so the two cannot drift apart; the regenerated output is byte-identical.
- **A `.gitignore` in the published repository** covers the generated `opencode/` tree so following the OpenCode setup does not leave permanent `git status` noise.

### Changed

- **The skill runtime-compatibility contract now names OpenCode.** The block previously described Claude Code and Codex only; it now states the OpenCode form of each rule: plugin root derived from the selected `SKILL.md` path, `.opencode/skill` for project-local skills, lowercase tool labels with `edit` covering both `Edit` and `Write`, and `install-opencode-agents` with bare hyphenated role names.
- **OpenCode setup documents the singular `~/.config/opencode/agent/`** in both the README and `OPENCODE_GUIDE.md`, noting that OpenCode reads the plural form too and that populating both leaves you guessing which copy is live.

### Fixed

- **A non-directory agent output path no longer ends `install-codex-agents` or the agent regenerators in a traceback.** A regular file, a symlink to a file, or a dangling symlink at the output path now produces a structured error and exit 2 on both the Codex and OpenCode lanes.
- **The OpenCode agent regenerator wrote through a symlinked agent file.** Replacing a generated agent file with a symlink made it overwrite the link's target and report success; it now refuses a symlinked agent file on both the write path and the `--dry-run` path.
- **`crux_wayfinder` was missing from the agent roster in every skill's compatibility block,** and `install-codex-agents` still described itself as installing nine roles. Both now say ten and include `crux_wayfinder`.
- **The OpenCode setup had no upgrade step.** `opencode/agents/` is a generated projection git does not track, so a `git pull` silently left it behind; both docs now instruct regenerating after every pull, and `OPENCODE_GUIDE.md` gains troubleshooting rows for stale-projection and dangling-symlink failures.
- **Stale references in `OPENCODE_GUIDE.md`** — tree paths that should have moved to `bionic/`, and a hardcoded skill count.

### Removed

## [1.11.0] — 2026-08-16

### Added

- **`derive-arch` skill** — the user-facing entry point to the `arch` concern. Say "build the arch", "summarize the current architecture", or "regenerate the architecture" to regenerate `bionic/arch/` — the derived current-state map (data model, interface surface, module graph, decision index, plus a synthesized overview) — wholesale from the project's own sources. `arch` is now documented as the primary current-state discovery surface, with a dedicated `arch` log op. Skill count 48 → 49.
- **Arch-spine coverage in `audit-docs`** — `CHK-ARCH-1` checks the derived spine for drift and regenerates it in place as a DRIFT-tier auto-fix (every arch input is already committed, so a regenerate cannot capture uncommitted source); `CHK-ARCH-2` recognizes arch enablement.

### Changed

- **`init-docs` enables the `arch` concern by default for new repositories.** A fresh tree enrolls `arch` in `concerns_enabled` and scaffolds `bionic/arch/` with a placeholder; the first "build the arch" or the first `audit-docs` run derives the spine. No `schema_version` bump. Existing trees are unchanged — add `arch` to `concerns_enabled`, then derive.

### Fixed

### Removed

## [1.10.2] — 2026-08-14

### Added

- **The development repository gains a drift gate over the skill, agent, and writing-rule counts in its docs,** so a future added skill either updates the prose automatically or fails the release.

### Fixed

- **Two stale skill counts in the README and USER_GUIDE** (46 → 48).

## [1.10.1] — 2026-08-14

### Added

### Changed

### Fixed

- **The arch `module-graph.md` was incomplete** — the extractor matched only absolute imports, so relative `from .x import` edges were missing. It now resolves relative imports, uses full-module node ids, and lists isolated modules.
- **Arch over-triggered drift on a manifest counter bump** — it hashed the whole `manifest.yml` though only key names render; it now hashes the key-name subset, so a routine `next_number` bump no longer drifts.
- **README/skill doc drift** — skill count (46 → 48), agent count (nine → ten), three missing skill rows (`prose-review`, `recover-decisions`, `transition-decision`); `prose-review`'s description now says "seven writing rules".

### Removed

## [1.10.0] — 2026-08-14

### Added

- **Decision recovery.** `recover-decisions` mines load-bearing decisions latent in code into `observed` candidates — structural-anchor identity, `path:line-range` evidence with no code excerpt, redaction-scanned statements — in `bionic/arch/_recovered/state.yml`; `transition-decision` ratifies a candidate into a Proposed ADR (idempotent via `recovered_id`), or rejects or defers it. `derive-arch.py` gains `decision_index_mode: complete|curated`, and a new `recover` log op is added.
- **ADR archival cold tier.** Superseded and Deprecated ADRs move to `bionic/adrs/archive/`, shrinking the active reading path while staying immutable and resolvable. `transition-adr` moves an ADR on Supersede/Deprecate; `propose-adr`'s counter scans both tiers so an archived id is never reissued; a new `generate-adr-index.py` regenerates `adrs/index.md` with its `## Archived` roster; `audit-docs` gains `CHK-ADR-ARCHIVE`.
- **Writing rule #7 — footnote-only ADR citation.** In human-facing prose, reference an ADR by a footnote, never an inline number or a link that renders it; ADR bodies and the journal are carved out. A new AST-based check flags inline ADR references while skipping code, link destinations, frontmatter, blockquotes, HTML, and footnote definitions, with a ratchet baseline so it enforces going forward.

### Changed

### Fixed

### Removed

## [1.9.0] — 2026-08-14

### Added

- **The arch concern.** `<docs_dir>/arch/` is the project's *derived* architecture — a deterministic spine (`data-model`, `api-surface`, `module-graph`, `decision-index`) plus a synthesized `overview.md`, regenerated by `derive-arch.py`. A SHA-256 hash-stamp over the four spine files gates the narrative: `derive-arch.py --dry-run` fails when the spine moved without a re-derive. Ships extractors for crux's own stack; other stacks degrade to an empty-but-valid file. `docs_dir` is containment-checked before any write.

### Changed

### Fixed

### Removed

## [1.8.2] — 2026-08-02

### Added

### Changed

- **`init-docs` bootstraps the unified `bionic/` tree.** The skill now creates the schema-5 layout at the resolved `docs_dir` (never a hardcoded literal): concerns directly under the tree, the invariants concern as one folder, and `.bionic.yml` written for every tree with merge-never-clobber semantics (preserving `artifact_prefix`). The guard refuses symlinked trees and cross-checks the other well-known location for a second tree; rollback removes only paths written this run and restores modified pre-existing files.
- **Templates and schema docs describe the v5 world.** The operational schema's version history gains the `"5"` row, diagram roots sit at `bionic/`, paths use `<docs_dir>`, and both USER_GUIDEs name `bionic/`, `schema_version 5`, and `.bionic.yml`. `install-docs-skills` fresh-install detection resolves the tree instead of testing for a literal `docs/`.

### Fixed

- **User-reported: fresh installs bootstrapped a `docs/` tree with schema_version "4" prose instead of the `bionic/` tree at "5".** The `init-docs` skill prose still instructed the v4 split layout even though the templates had moved on; the verification checklist would also have rolled back a correct v5 bootstrap. Skill prose is now pinned to the shipped templates by tests.
- **`docs_dir` rejects shell metacharacters.** A committed `.bionic.yml` could set `docs_dir` to a value like `$(id)`, which executed when skills composed shell commands around the resolved path. Each segment must now match `^[A-Za-z0-9_.][A-Za-z0-9._-]*$`.

### Removed

## [1.8.1] — 2026-07-31

### Added

### Changed

### Fixed

- **`migrate-tree.py` could not migrate a relocated tree, and would have damaged one if forced.** It hardcoded its source to `<root>/docs` and never resolved the configured `docs_dir`. Source is now resolved through both config files, the destination is anchored at the true repo root, and a relocated tree stays where its owner put it — only the invariants suite merges into it. `--docs-dir` is the escape hatch for a layout no config declares.
- **The documented upgrade path was a closed loop.** The schema gate says to run `audit-docs --migrate`, but that skill documented only the 2→3 and 3→4 rungs. The 4→5 rung is now documented with its invocation, exit codes, and fail-closed behaviors.
- **Containment on every path that reads, writes, or removes.** A `docs_dir` of `../elsewhere`, an absolute path, or a symlink escaping the repo is refused rather than followed; symlinked directories are refused during merges even when in-repo.
- **The distributed `CLAUDE.md.tmpl` shipped eight literal `<tree>` placeholders** that no render step substitutes, and described a nested `bionic/docs/` mechanism that was never built.
- **`install-docs-skills` hardcoded schema `"3"`** while the plugin shipped `"5"`; it now reads the supported value from the installed manifest.
- **`audit-docs` was self-contradictory about the supported schema** and still called the invariants concern deferred.

### Removed

## [1.8.0] — 2026-07-30

### Added

- **The tree lives at `bionic/`, and the invariants concern is one folder.** The seven concerns sit directly under `bionic/` — no nested `docs/` level — and the invariants concern holds its ledger pages, a `checks/` subdirectory, and `reconciliation.yml` together. `init-docs` always writes `.bionic.yml` naming the tree. **Breaking:** `schema_version` `"4"` → `"5"`.
- **Bare-directory discovery.** A tree is recognized by a manifest carrying both `schema_version` and `concerns_enabled`. Two valid trees refuse loudly unless a migration marker names one; exactly one resolves to it; none resolves to `bionic`. **An existing `docs/` tree keeps working with zero config and no migration.**
- **`migrate-tree.py`, the 4 → 5 rung.** A staged, resumable merge: entries merge one at a time, `manifest.yml` moves last so a crash leaves discovery resolving to the source, and a marker lets replay tell an already-moved entry from a real collision. Config is merged, never overwritten.
- **A schema gate.** Commands that read the tree refuse an unmigrated one with exit 2 and a message on stderr, rather than reporting clean because they cannot find their own reconciliation surface.
- **Six writing rules, and `prose-review` — the 46th skill — to check them.** One name per thing, no hedge without a cause, verbs stay verbs, adjectives must be checkable, one idea per sentence, single-word verbs; accuracy outranks all six. There is no banned-word list — only tests applied per sentence. `prose-review` reports only findings that carry a rewrite: `fix` when the rewrite follows from the text, `confirm` when it needs a fact only the author holds.
- **`generate-writing-rules.py`.** One canonical rules text projects byte-equivalently into `AGENTS.md` (read by Codex and OpenCode, which never load `CLAUDE.md`), the operational schema, and the shipped `prose-review` skill, with a `--dry-run` drift gate.

### Changed

- **`prose-review` is now mandatory at three points**: the release preflight (advisory), the `dev-cycle` / `iterate` prep prompt, and `tend-garden` before it writes the morning note.

### Fixed

### Removed

## [1.7.0] — 2026-07-24

### Added

- **Opus 5 refusal handling in the council seats.** A safety refusal returns HTTP 200 with `stop_reason: "refusal"`, which previously surfaced as a JSON-parse error or `unknown`. A new `ModelRefusedError` maps to a new closed-vocabulary redaction label `"refused"`, so the seat still degrades correctly and the recorded reason is truthful.
- **Spawn caps on the delegating agent roles.** `commander` and `dev-lead` now spawn one agent per genuinely independent unit, never for work finishable in ~3 or fewer tool calls, and never solely to double-check — with an explicit carve-out for independent review, per-threat-class security review, and two-architect ADR acceptance.
- **Scope-discipline guidance** on `dev-lead`: deliver at the scope intended, without unrequested refactors.

### Changed

- **Model swap: `claude-opus-4-8` → `claude-opus-5`** across the LLM router config and the OpenCode agent generator. `claude-opus-4-8` is removed from the router registry entirely; the lineup is Fable 5 / Opus 5 / Sonnet 5 / Haiku 4.5. Router config `1.4.0` → `1.5.0`.
- **Agent and cycle-skill prose re-tuned for Opus 5's defaults.** `architect` states plan coverage and type consistency as required properties rather than a self-review pass; the `dev-cycle` and `iterate` checklists no longer re-derive what `validate-promptbook.py` guarantees. Every cross-agent gate is preserved.

### Fixed

- **`dev-cycle` / `iterate` checklists overstated validator coverage.** The cycle-coverage pass checks module size and contiguity, not prompt content, and `cycle_grandfathered: true` short-circuits it entirely; both checklists now say so.

### Removed

## [1.6.0] — 2026-07-23

_A larger release than the version bump suggests: fixes for six defects surfaced by a downstream repo driving real work on v1.5.0, a durability program under which every derived artifact needs a vendored regenerator and a drift gate, and a hardening of the council's secret-redaction path._

### Added

- **`generate-lineage.py` — a vendored regenerator for `adrs/lineage.md`.** `link-adr-graph`'s engine is now a committed, deterministic script rather than prose-only instructions, with a byte-stable drift gate.
- **`generate-index-rollup.py` — a regenerator for the `## ADRs (N)` rollup of `index.md`,** which is now a pure function of ADR frontmatter with a `--dry-run` drift gate. Regenerating it surfaced two silent drifts a prose audit had missed.
- **`advance-run.py` — a vendored safe-advance script for promptbook run snapshots.** It mutates the `n == current_prompt` element, moves the pointer (or completes the run), updates the active book's pointer, and round-trips every top-level key so the run-level `notes` / `pr_draft` / `summary` fields survive each advance. `run-promptbook` now prefers it.
- **The development repository ratified its first invariant** (council aggregation excludes errored seats) and gained a standalone, reversible pre-release preflight.

### Changed

- **Council deliberation is hardened against a single errored provider seat.** Aggregation now runs over responding seats only, gates on a quorum of ≥ 2 (`NO_QUORUM` below it), surfaces `errored_seats` and a `degraded` flag, caps a degraded verdict at `EXECUTE_WITH_MONITORING`, and counts `APPROVE_WITH_NITS` as an approval. `run-adr-council` gains failure-table rows and a multi-round-composition section.
- **Wiki-link resolution is lifecycle-agnostic and reference-inclusive.** An ADR's `related_research` entry now resolves to any research page (a bare slug → `sources/`, a `<category>/<slug>` → a synthesis page), and a journal→promptbook link resolves on its `PB-NNNN` id across `active/` or `archive/`; the neutral `[[promptbooks/PB-NNNN-<slug>]]` is the write form and legacy spellings still resolve.
- **Whiteboarding sessions now carry into the brief body.** `propose-brief --from-inbox <session-path>` populates the brief body from a whiteboarding session, and `process-inbox` passes it for whiteboarding-classified items.
- **Derived artifacts now require a vendored regenerator and a drift gate.** Any artifact — or derived region of an authored file — that should be a pure function of an in-repo source of truth must have a committed deterministic regenerator and a drift check.
- **`CLN-TMPL-1` now guards section content, not just section presence,** with four curated content-marker clauses.
- **The `invariant` log op is a first-class member of the op enum,** and `transition-invariant` emits it directly.

### Fixed

- A single errored council provider no longer poisons `consensus_confidence` or makes `UNANIMOUS_APPROVE` unreachable; the council driver no longer punts the multi-round loop it depends on.
- Two growing wiki-link dangle classes are retired: ADR `related_research` pointing at a `references/` synthesis page, and journal refs to now-archived promptbooks.
- The `whiteboarding → process-inbox → propose-brief` pipeline no longer orphans the session body behind an empty scaffold.
- **Provider exception text can no longer leak through council error paths.** Error redaction is now closed-vocabulary structured omission — a fixed label set plus a range-validated integer status — so no substring of a provider exception is ever copied onto a persisted deliberation surface. The previous regex leaked 12 of 18 adversarial credential shapes; it now leaks 0. The sibling log lines, the sync council's `Opinion.position`, and the visual council's `observations` are closed too.

### Removed

## [1.5.0] — 2026-07-18

### Added

- **The invariants concern — the seventh concern.** Pinned, ratified, executable statements of what must be true, verifiable against regeneration: a human-readable ledger under `docs/invariants/` plus a peer executable check suite at `bionic/invariants/`, reconciled through a `.bionic.yml`-rooted manifest. Two new skills implement a machine-proposes / human-ratifies model — `recover-invariants` (mines code for `observed` candidate pins; never self-ratifies) and `transition-invariant` (the human gate: `observed → ratified | rejected`, `ratified → retired`). `audit-docs` gains five `CHK-INV` rules. `manifest.yml` `schema_version` `"3"` → `"4"`.
- **`init-docs` enables the invariants concern by default for new repositories.** A fresh tree bootstraps at `schema_version: "4"` with all seven concerns. Existing trees adopt the concern opt-in via `audit-docs --migrate` (a new 3→4 rung); `init-docs` never upgrades a populated tree in place, and `--force` archives-and-rebuilds rather than migrating.
- **`.bionic.yml` — the repo-root layout source of truth.** A committed config file (`config_version`, `docs_dir`, `artifact_prefix`) that supersedes the legacy `.crux` file, resolved with a two-file precedence (`.bionic.yml` > legacy `.crux` > convention) via the new `bionic-config.py` CLI; `crux-config.py` is retained as a back-compat delegator.

### Changed

- **Forged-skill promotion is now judgment-driven, not mechanically auto-nominated.** The former promotion floor (≥2 `effective` evaluations on ≥2 distinct dates) becomes supporting evidence the owner weighs; the `retrospective` skill's promotion scan becomes an owner-facing evidence report. The `evaluated` forge-log discipline is retained in full.
- **`audit-docs` supports `schema_version` `"4"`** — it walks the invariants concern, and its `--migrate` ladder gains a `3→4` rung.
- **Concern framing moved from six to seven** across the README, USER_GUIDE, and the operational schema.

### Fixed

### Removed

## [1.4.2] — 2026-07-13

### Added

### Changed

### Fixed

- **Release-commit authorship in the development repository's publish tooling now uses a sanctioned machine identity** rather than a legacy noreply address GitHub attributed to an unaffiliated real account. No plugin, skill, or docs-tree behavior change.

### Removed

## [1.4.1] — 2026-07-10

### Added

- **Public manual OpenCode setup instructions** in `README.md` (a new `### OpenCode (manual setup)` section) and a refreshed `OPENCODE_GUIDE.md`: clone to a stable path, `uv run generate-opencode-agents.py`, merge the absolute `crux/skills` path into `opencode.json`, glob-symlink all ten generated agents, restart the host, and verify with `opencode debug skill` / `opencode agent list`. There is no native Crux OpenCode marketplace package yet; the setup is manual and preview-grade.

### Changed

### Fixed

- Corrected the `README.md` status/footer version and completed the 43-skill table. Docs-only.
- `OPENCODE_GUIDE.md` stale counts corrected (42 → 43 skills, nine → ten agents), and the agent symlink step is now glob-based so it covers all ten roles (including `wayfinder`).

### Removed

## [1.4.0] — 2026-07-10

### Added

- **The OpenCode agent projection is drift-gated with generator test coverage.** The generator's `--dry-run` is checked on every change, alongside a test suite covering transform rules, hard-error paths, dry-run semantics, and verbatim body/description passthrough.
- **Codex is a supported distribution target and the fourth regenerative agent projection.** `.codex/agents/crux-*.toml` is generated from the same agent source of truth by `generate-codex-agents.py`, never hand-edited, with the shared `--dry-run` drift contract. Install with `codex plugin marketplace add bionic-coding/crux` then `codex plugin add crux@crux`; target repos get the ten agents via the no-clobber, path-contained `install-codex-agents` skill, which refuses to overwrite a differing `crux-*.toml` role or remove a stale one without `--force`. The portable `CRUX_PLUGIN_ROOT` bridge is now stated correctly everywhere (Claude Code = `CLAUDE_PLUGIN_ROOT`; Codex = derived from the selected `SKILL.md` path; source checkout = `crux/`). A leaf-symlink write-through in the shared generator/installer write path was closed, and the generated agents' model mapping was corrected against the live Codex catalog (seven roles → `gpt-5.6-sol`, three → `gpt-5.6-terra`).

### Changed

- **LLM router model refresh for the latest OpenAI and Anthropic releases.** Router config v1.2.0 → 1.3.0: the seven-SKU OpenAI lineup consolidates into three effort-controlled GPT-5.6 SKUs — Sol (flagship reasoning and coding, alias `gpt-5.6`), Terra (balanced workhorse), Luna (cost/high-volume) — all Responses-API-only; `gpt-image-1` → `gpt-image-2`; the `openai_reasoning` / `openai_reasoning_fast` roles are retired. `claude-sonnet-4-6` → `claude-sonnet-5`, which rejects the temperature parameter — a behavior change from 4.6. Anthropic pricing corrected against the official source. `fast_council`'s arbiter stays Sol pinned to LOW reasoning effort via an effort-alias entry `gpt-5.6-sol-low`.

### Fixed

- **OpenAI `/v1/responses` is first-class in the caller and async council.** The async council's OpenAI seat hardcoded `chat.completions.create`, so a Responses-API-only model errored into a degraded vote, and the caller never forwarded reasoning `effort` on the responses path. Both async OpenAI seats now route by the model's `openai_endpoint` through `responses.create` (JSON mode, `reasoning.effort`, vision via `input_image`), and the caller threads `config.effort` → `reasoning.effort`.
- **Codex-integration corrections.** The `CRUX_PLUGIN_ROOT` mislabeling is corrected across the template, the operational schema, and 13 skill bodies; strict-YAML tests skip cleanly on a PyYAML-less interpreter; dated provenance comments anchor the external Codex model-slug and schema assumptions so future drift is diagnosable. Publication tooling in the development repository also closed a symlink-bypass in its staging path.

### Removed

## [1.3.3] — 2026-07-10

### Added

- **Self-detecting `CLN-TMPL-1` cleanup-campsite rule** checks dogfood↔distributed-template clause parity: drift surfaces as a P2 suggestion naming the divergent section; a stale manifest anchor reports P3; with no template twins present it reports 0 findings. A general-purpose `cleanup-campsite --only <RULE-ID>` selector (CSV-capable; an unknown id is a loud error) enables single-rule runs.
- **`dev-cycle` and `iterate` now record forge-log `used`/`evaluated` entries for forged skills they invoke** — a `used` entry at the review module's convergence prompt and an `evaluated` entry at the summary prompt — so cycle-used forged skills accrue the evidence promotion needs. No prompt-count formula change.
- **`scout` — crux's 10th agent, a read-only context-preservation reconnaissance subagent** (renamed `wayfinder` below). A primary delegates the consume-to-judge step to it: it reads large, uncertain, or external data in an isolated context, judges its fitness for a stated purpose, and returns a verdict plus a condensed digest. Tool grant `Read, Grep, Glob, WebFetch, WebSearch`; it is the first read-only agent with outbound network reach, fenced by an embedded egress guardrail (never relay local content outbound; never read secrets). Model `sonnet`. Catalog 9 → 10 agents.
- **`run-adr-council` graduates into the plugin** (catalog 41 → 42, joining `council` in the `crux-verification` bundle) — the ADR council runner, rebuilt so the council prompt is a data file written by the file-write tool and no shell string ever holds ADR prose. The first forged skill to travel the full authored → nominated → graduated → pruned lifecycle.
- **The forged-skill promotion path.** Forged skills are usable in the session that forged them, every authoring or using session writes a session-end `evaluated` forge-log entry, the retrospective gains a promotion scan nominating skills that clear a mechanical floor, and graduation into the plugin is always a dev-cycle with the local copy pruned last. `CLN-FG-2` backstops the evaluation discipline. Project-local skills cannot PR into the public repo; share via issue.
- **The night-gardener — crux's 9th agent — and her two skills.** A standing overnight co-CTO who reviews recent work and writes a morning note under `docs/garden/`: new ideas, improvement vectors, missing tests/CI/guards, research directions, and relevant news. Turn-based — she moves only after you've moved — and may run a retrospective when due, whiteboard solo into the inbox, and draft `garden/<slug>` branches, never pushed or merged. `tending.md` is your only control surface: dismiss (permanent veto) or snooze, with no acknowledgment burden and a 90-day decay. New skills `tend-garden` (the night-pass orchestrator) and `read-news` (Perplexity-backed reading of curated sources with a Perplexity → WebSearch → skip fallback; `PERPLEXITY_API_KEY` optional via `~/.crux/`). Adds the `garden` log op. Catalog 39 → 41 skills, 8 → 9 agents. The nightly routine is owner-installed; crux never self-installs persistence.
- **`retrospective` — purposeful reflection that harvests skills from finished work.** It mines the operations log, journal reflections, archived promptbooks and run notes, whats_next, and the forge log since the last retrospective marker, distills 0–2 evidence-cited skill proposals (recurrence = ≥2 distinct incidents), gates each through a fixed council rubric, and builds approvals via the forge-skill pipeline. Cadence via trigger phrases and the new `cleanup-campsite` rule `CLN-RETRO-1` (`retro_due_runs` default 5). Catalog 38 → 39.
- **`forge-skill` — the capability-gap loop.** When a gap surfaces mid-task, the model diagnoses it (testable closure criterion required), micro-whiteboards, researches, authors or revises a permanent project-local skill under `.claude/skills/<name>/`, and self-tests on the live problem — autonomous by default, propose-first for outward-facing, out-of-repo, or secrets-touching capabilities. Every act lands in the append-only forge log (`.claude/skills/forge-log.md`), plus a new `skill` op. Detection is an embedded reflex in all agent definitions. New `cleanup-campsite` rule `CLN-FG-1` flags forged skills idle past `forged_skill_stale_days` (default 30).
- **PEP 723 + `uv run "${CLAUDE_PLUGIN_ROOT}/..."` runtime contract.** All 18 shipped runnable scripts carry PEP 723 inline-metadata blocks and are self-describing under `uv run`; a test enforces that every documented `uv run` entry point has a conforming block.
- **A release-content scan** bans concrete internal decision references on distributed surfaces (skills, agents, templates).

### Changed

- **The reconnaissance agent is renamed `scout` → `wayfinder`** — one unified name across Claude Code and OpenCode. A pure rename: capability, tool grant, model, mode, and security contract are unchanged. It resolves the collision with OpenCode's built-in `scout`, so no override is needed.
- **The `architect` agent now holds `Bash`** so it can execute the multi-model council driver its own remit requires; it already held `Edit`/`Write`, so this adds execution, not write capability.
- **The dev-cycle quality gate now mandates the FULL test suite**, not a hand-picked subset, whenever a change touches a shared or enumerated surface (agent roster, router config, catalog). Both `dev-cycle` and `iterate` inherit it.
- **LLM router curated to the latest-generation lineup; `claude-fable-5` disabled.** Older models removed (gpt-5.2 family, o3, o4-mini, gemini-2.5-\*, claude-haiku-4-5, claude-fable-5-medium); `gpt-5.5-pro` and `gemini-3.5-flash` added; pricing and context corrected. `claude-fable-5` is retained but `enabled: false`, and the two Fable-pinned OpenCode agents (`architect`, `commander`) are remapped onto `claude-opus-4-8`. (Superseded by the GPT-5.6 refresh in 1.4.0.)
- **Split-repo publication model.** crux is now developed in a private repository and published to the public `bionic-coding/crux` repository as a generated artifact, one squash commit and tag per release. The three public docs are human-reviewed artifacts with source fingerprints that publication refuses to ship stale. Releases attach no zip assets; the marketplace model makes them redundant.
- **The abandoned "Crux Lite" framing is gone from every live surface.** All three manifest descriptions converge on functional phrasing, and the README/USER_GUIDE open on the product's own terms.
- **Marketplace-only install story.** The install path is the two slash commands `/plugin marketplace add bionic-coding/crux` + `/plugin install crux@crux`; README, USER_GUIDE, templates, and skills all converge on it.
- **`${PLUGIN_DIR}` → `${CLAUDE_PLUGIN_ROOT}`** as the canonical plugin-root variable in every documented invocation.
- **Spawner runtime directory `.crux` → `.crux-runtime`**, with refusal-on-foreign-target (`SpawnTargetConflictError`) plus symlink and containment guards.
- **Provenance fields (`origin`/`origin_ref`/`origin_date`) removed** from the SKILL.md frontmatter contract and the regenerated catalog; internal decision references removed from distributed surfaces; git softened to enhancement-not-requirement.
- **Distributed `CLAUDE.md.tmpl` rebuilt** to the current contracts.

### Fixed

- **The release-content scan is wired into the in-cycle quality-gate sequence across all three cycle templates,** so a banned internal-reference leak onto a distributed surface fails in-cycle rather than only at release time (exit 1 = finding to fix; exit ≥ 2 = environment error).
- **The bare-`python3` test lane is honest.** Module-import-time capability guards make uv-less runs report clean skips instead of errors, and the PyYAML re-exec lane no longer exec-replaces the unittest runner mid-suite. `check-no-stale-skill-names.py` gained kebab-boundary guards so a stale name embedded in a longer slug is no longer a false positive. README agent count corrected to 9.
- **The test suite is green again after the router curation.** Six router tests re-pointed to the surviving lineup; a hardcoded 9-agent list updated for the 10th. A real config gap was fixed: `gpt-5.5-pro` was missing `openai_endpoint: "responses"` and would have routed to `/chat/completions`.

### Removed

- **`spin` (the Python RSI engine) is decommissioned** — succeeded, not abandoned: its disciplines (three testable hypotheses, confidence-gated outcomes, self-reflection breadcrumbs) survive as prose in `forge-skill`, while the `spin` modules, skill, and tests are deleted. The eager spin import is gone from the package `__init__` (a lighter import chain for every `crux.*` consumer); `author-runbook` and the spawner teach the hypothesis discipline inline. Catalog stays at 38 skills.
- **Breaking: `crux/install.sh`** — the curl|bash install path is gone; the marketplace flow is the only install path.

## [0.9.0] — 2026-06-10

### Added

- **Honest YAML-capability failures and automatic uv repair.** The minimal fallback YAML parser could silently mis-parse valid documents outside its subset, poisoning `book_content_hash`. The three correctness-critical scripts (`validate-promptbook.py`, `migrate-promptbooks.py`, `visualize-run-progress.py`) now require a real YAML parser at entry — without PyYAML they self-re-exec under `uv run --no-project --with pyyaml>=6.0` (loop-guarded, opt-out `CRUX_NO_UV_REEXEC=1`) or exit 2 with a `YamlCapabilityError` remediation on stderr, never reporting an environment problem as a document verdict.
- **Repo-root `.crux` configuration file** — committed per-project config: `docs_dir` relocates the docs tree, `artifact_prefix` brands promptbook/ADR ids (`CRX` → `CRX-PB-0040`; `RUN-NNN` never prefixed; ids immutable over mixed trees). A stdlib loader with textual and containment validation (including a denylist of execution-adjacent directories) plus a `crux
