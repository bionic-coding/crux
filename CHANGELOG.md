<!-- generated-from: CHANGELOG.md@sha256:51dd4238f672128f8d91c11f0ac90b6a92d06394f761cd287f4f021a0f34a581; model: claude-fable-5.1; date: 2026-09-09 -->
# Changelog

All notable changes to crux. The format roughly follows [Keep a Changelog](https://keepachangelog.com/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [3.10.0] — 2026-09-08

### Added

- **Three new delivery signals in `adr-signals.py`.** `release_cadence`, `schema_growth`, and `gate_count` join the five existing signals, for eight in total. Every git invocation runs under a fixed environment allowlist (`LC_ALL=C`, `GIT_CONFIG_NOSYSTEM=1`, no `HOME`/`XDG_CONFIG_HOME`), so neither your user nor system git configuration is read.
- **Decision-review reports carry six sections.** A report dated after 2026-09-07 has Propose, Amend, Repair, Revoke, Keep, and Coverage in that order, one summary table, and one data-framing note; Repair holds findings whose remedy writes no ADR file, and Revoke holds findings that revoke a decision. The five-finding cap counts across Propose, Amend, Repair, and Revoke combined; Coverage gains a per-goal matrix. Older reports keep the sections they were written with.
- **A `Friction:` line in journal entries.** A journal entry body may carry one `Friction:` line naming a specific friction, placed before `Refs:` and counting toward the body-line budget; an empty remainder is a contract violation. The new `journal.friction_line_from` manifest key records when counting became measurable, `log-work` writes the line, and `retrospective` and the friction signal count it.
- **One shared Markdown fence module, `md_fences.py`.** Both `adr-signals.py` and `check_template_parity.py` now read code fences through the same conformance-tested implementation instead of two hand-copied variants.

### Changed

- **The public repository moved to the `bionic-coding` GitHub organization.** Install with `/plugin marketplace add bionic-coding/crux` (Claude Code) or `codex plugin marketplace add bionic-coding/crux` (Codex), and clone from `bionic-coding/crux` for the OpenCode stable-path setup. The plugin manifests' `homepage` fields point at the documentation site, `https://bionic-coding.com/crux/`, and the README opens with a "Start here" link to it.
- **Apex roles run Fable 5.1 on Claude, and the night gardener joins the apex tier.** The commander, reviewer, and night gardener now run Fable 5.1 (a `fable-latest` alias is added); the night gardener keeps its OpenCode seat. The reviewer's turn budget rises to 150 and the night gardener's to 100. Standard-tier Codex roles run at high reasoning effort.
- **`review-decisions` aims the pass at delivery.** The skill reads eight signals, routes each finding by two ordered questions about its proposed act, and disposes the top three `dormancy_days` and the top three paper-only ADRs each pass as `keep`, `revoke`, or `defer` with one reason. An objectives file still at `maturity: placeholder` now stops the review and leaves the finding sections empty rather than producing a judgment with no yardstick.
- **The template-parity check grows from 30 to 35 clauses.** Five new clauses pin the `adr_review_due_days` and `journal.friction_line_from` manifest keys, the `Friction:` line grammar, the reviews-surface report shape, and the `adr-review` log-op body grammar between the operational schema and its shipped template.

### Fixed

- **`init-docs` creates the `adrs/reviews/` directory.** A bootstrapped tree had no decision-review surface, so the first cadence nudge pointed at a path that did not exist.
- **`log-work` no longer describes a retired log-only caller.** Its prose now records that `run-promptbook` no longer logs per-advance entries.
- **`adr-signals.py` reads both shapes of `adr.governs_exempt`.** Both bare-id members and `{adr, reason}` members are now counted, in flow or block form; previously a reason-bearing member miscounted the carve-outs.
- **The operational schema template documents both exemption forms** and states that the coverage lane reads only the id.
- **Mined values are split into lines by the CommonMark rule.** Ten readers across `adr-signals.py` and `check_template_parity.py` previously used `str.splitlines()`, which breaks on characters such as `\x0b`, `U+2028`, and `U+2029` that no Markdown renderer treats as line ends, letting a mined value forge a heading, table row, or fence closer. Lines now end only on `\n`, `\r\n`, or a bare `\r`.
- **Code-fence detection bounds indent and closer consistently.** A fence indented with a tab or a non-breaking space no longer opens, and a closer shorter than its opener no longer closes.
- **The `prep_commits` mapping key uses a full 64-character digest.** A 16-character digest was short enough that two version strings could collide and silently overwrite one another's commit counts.
- **The table rendering lane redacts a mined value's key as well as its value.** An ADR whose frontmatter `id:` carried a terminal escape sequence could clear or recolour the terminal on three signals; keys now render through the same quoted redaction as values.
- **An uncompilable version pattern is reported as a finding, not as an environment error.** Previously one bad heading turned all eight signals into exit 2; now that version counts `null`, its key is listed as unmatchable, and every other signal still computes.

### Removed

## [3.9.0] — 2026-09-07

### Added

- **`review-decisions`, a periodic architect review of the decision set.** The 60th skill reads the accepted decisions as a set and asks whether they still serve the objectives, entering through the doctrine index and rule table and opening an ADR body only for a domain a signal flagged. It writes at most five findings into one dated report at `adrs/reviews/YYYY-MM-DD.md` under your docs tree. It proposes only: it transitions no record, signs off no batch, and authors no skill.
- **`adr-signals.py`, five mechanical signals as verdict envelopes.** A stdlib-only script computes amendment fan-in, carve-out count, paper-only, dormancy, and friction citations. Every signal is a five-member record — `signal`, `verdict`, `value`, `basis`, `filter` — with no severity and no recommendation. `friction_citations` reports `unmeasurable` rather than `0` when the tree offers no measurable source.
- **A regenerated reviews index.** `generate-reviews-index.py` derives `adrs/reviews/index.md` from the dated reports and refuses a filename outside the `YYYY-MM-DD.md` grammar or a report whose frontmatter disagrees with its filename. A tree without a reviews directory exits 0 with `"surface_absent": true`, which `check-drift` reports as N/A rather than as a clean gate.
- **The objectives file.** `objectives.md` in your docs tree holds the product's mission and goals — the yardstick a decision review measures against — with a six-key frontmatter including a `maturity` ladder, a required `## Mission`, `OBJ-N` goals, and an append-only `## Shifts` table. `init-docs` seeds it as a placeholder; every reader asks you to fill it in rather than citing the placeholder.
- **Lint rules for the review surface.** `audit-docs` gains five `CHK-OBJ-*` rules over the objectives file, including a WARNING when `reviewed_at` is older than `review_every_days`. `cleanup-campsite` gains `CLN-ADR-5` (a decision review older than `adr_review_due_days`, default 7) and `CLN-OBJ-1` (an objectives file still at `maturity: placeholder`), for 20 rules. The log-op enum gains `adr-review`.

### Changed

### Fixed

- **A second `review-decisions` pass on one date amends the existing report** instead of overwriting it, keeping every earlier finding id.
- **`adr-signals.py` reads doctrine rows containing an escaped pipe (`\|`).** Such rows previously vanished silently, which could mark an ADR rowless or paper-only.
- **The friction signal reads the forge log under every runtime's local skills directory** — `.claude/skills`, `.agents/skills`, `.opencode/skills`, and `.opencode/skill` — not only Claude Code's.
- **A future-dated review report is refused.** `generate-reviews-index.py` rejects a date after `--today` (default: the system date), and the night gardener's review-age check applies the same filter, so one file can no longer suppress the cadence reminder indefinitely.

### Removed

## [3.8.0] — 2026-09-04

### Added

### Changed

- **Async text and image councils use GPT-6 Astra as their OpenAI judge.** Astra replaces Sol in the `openai_top` role via OpenRouter, pinned to OpenAI as the serving provider. The synchronous council keeps its Terra seat.
- **Council Fable judges use Fable 5.1**, replacing Fable 5.0 at the same effort settings. Other callers of the shared Anthropic roles also receive Fable 5.1.
- **Codex apex roles use GPT-6 Astra at high effort.** The commander and reviewer receive it through the shared model catalog; Codex flagship and standard roles keep Sol and Terra.

### Fixed

### Removed

## [3.7.1] — 2026-09-02

### Added

### Changed

### Fixed

- **Every script's PEP 723 header now declares the real Python floor, 3.11.** Fifty-two scripts declared `>=3.10`, but the Python arch pack uses `tomllib` and several tests use `enterContext`, both 3.11 features, so a 3.10 run failed on the environment rather than the code. The user guide and the schema example now say 3.11. The four corpus-golden comparison tests skip below 3.13 with a named reason.
- **The README states the Python floor and the test command.** The suite needs the tree-sitter grammar packages named only in PEP 723 headers, so a bare `pip install` environment failed ~140 arch-pack tests; the Requirements section now carries the `uv run` invocation that resolves them.

### Removed

## [3.7.0] — 2026-09-02

### Added

- **The runtime-compatibility block in every skill is regenerated from one template.** The block that 55 of 59 `SKILL.md` files carried by hand now has one canonical source, a regenerator, and a `--dry-run` drift gate.

### Changed

- **Breaking: the OpenCode projection emits the V2 schema exclusively.** Generated agent files replace the singular `permission:` map with an ordered `permissions` array of `{action, resource, effect}` rules under last-match-wins. Two actions are renamed: `bash` becomes `shell` and `task` becomes `subagent`. The install target moves from `.opencode/agent/` to `.opencode/agents/`; `install-opencode-agents` gains `--migrate-legacy-agent-dir` to move a populated legacy directory (refusing on a name collision unless `--force`) and refuses to write when no `opencode2` binary is discoverable. A V1 OpenCode runner reading the new projection silently drops every deny rule.
- **The commander can dispatch the wayfinder** to size up a large, uncertain, or external source before another agent spends context on it.
- **`dev-lead` routes to GLM 5.3 on OpenCode** (`openrouter/z-ai/glm-5.3`); its Claude and Codex seats are unchanged.

### Fixed

- **`web-to-markdown` passes a Markdown or plain-text response through unchanged.** A `text/markdown` or `text/plain` body previously went through the HTML converter and came out as one collapsed line.

### Removed

## [3.6.0] — 2026-09-02

### Added

- **A decision is cited as `rule:<slug>`.** The form is identical in code comments, prose, promptbook prompts, and journal refs. The linter that resolves the token gains a default scope over authored sources, fails on an empty scope rather than passing on zero files, fails on an unknown slug, and on a retired slug names every live rule that displaced it.

### Changed

### Fixed

- **The two archive-tier ADR readers in the summaries projection no longer follow a symlink out of the tree.** An `ADR-*.md` symlink planted in `adrs/archive/` was previously read from outside the repository; both readers now refuse a symlink.
- **The `srde` skill's batch example builds `DissentPoint` objects**, which `attempt_batch_resolution` requires, instead of passing raw dissent strings.
- **The plugin's `crux/README.md` reports 59 skills**, not 55, and is now covered by the doc-count drift gate.

### Removed

## [3.5.0] — 2026-08-31

### Added

- **Batch ratification for observations: `survey-sheet` and `survey-signoff`.** `survey-sheet` scaffolds one `SVY-NNNN` review sheet from the candidate state file; `survey-signoff` is the single human sign-off that publishes the sheet under one digest-bound receipt, and one signature is equivalent to N individual ratifications. Both carry `disable-model-invocation`. `audit-docs` gains four `CHK-OBS-SURVEY-*` rules.
- **`fix-directly`, the rung below the three cycle tiers.** "Just fix it" now has a named contract — no book, no council, no `PB-NNNN`: a failing test first, the smallest green change, the suite and drift gates, one commit, one `log-work` entry. A five-question sizing test decides between it and `patch-cycle` / `iterate` / `dev-cycle`.

### Changed

- **`cleanup-campsite` retires `CLN-ADR-1`.** The rule flagged an accepted ADR unmentioned in README/USER_GUIDE within 30 days and only ever accumulated findings; 18 rules remain implemented.
- **The verify templates carry a reproduction budget.** The `iterate` verify module and the `patch` verify phase state that a failing test is a complete reproduction, a class earns its own reproduction only at a second independent instance, and a security label must not widen the fix. `whiteboarding` gains a sizing step.

### Fixed

- **Three survey sign-off defects.** A `config_version: "1"` sheet on the resumed-batch path now runs `assert_signable`; the index retire loop splits only on unescaped pipes; `CHK-OBS-BIJECTION` reads each row's id column instead of grepping the whole page, so a mined cell can no longer forge or suppress a finding.
- **The arch drift gate no longer treats the decision-recovery state file as stale.** `derive-arch.py --dry-run` excludes `arch/_recovered/`, which the first `recover-decisions` run writes by design.

### Removed

## [3.4.0] — 2026-08-30

### Added

### Changed

- **The OpenCode commander runs Qwen3.8 Max (1M context) instead of Kimi K3**, which could not sustain the orchestration role. Every other role's OpenCode model is unchanged.
- **Each arch stack-pack probe declares its own input class against a committed roster.** The doctrine index's `implemented` column is renamed `basis`, and a `governs` entry's `retires` sub-field displaces a rule while keeping its record on the ledger.
- **Breaking: a `governs` entry's sub-field set is closed.** `summarize-adrs.py` and `compile-doctrine.py` hard-refuse an unrecognized sub-field, so a tree carrying any other annotation key fails both regenerators on upgrade.

### Fixed

- **A book's `current_run` pointer survives a run's completion**, so `archive-promptbook` can read the pointer its precondition requires. `current_run` now nulls only at archival.

### Removed

## [3.3.0] — 2026-08-30

### Added

- **A repository that has never authored an ADR can build a doctrine from what its code already does.** The `observations` concern adds `OBS-NNNN` records, each evidenced by a `path:line-range` and ratified by a human; a ratified record projects into the summaries rule table and the doctrine index beside the ADRs.

### Changed

- **`derive-arch` records a per-concern verdict instead of grading its own confidence.** A concern is `populated` or `stubbed`, and every stub names one reason from a closed set of six. The new `arch.require` list in `manifest.yml` fails the derive when a required concern is not `populated`.
- **The arch extractors read committed artifacts and real parsers.** Python routers parse through the standard-library AST, Ruby reads a committed `rails routes` dump, and Ruby, Node, and Elixir source parses through tree-sitter grammars declared in the script's dependency block. Node routes compose `app.use` mount prefixes, and Elixir routes parse the parenthesized form.

### Fixed

### Removed

- **The `arch_confidence_threshold` key in `.bionic.yml` is retired.** A tree that still sets it loads clean.

## [3.2.2] — 2026-08-29

### Added

### Changed

### Fixed

- **The agent-catalog strict-YAML test skips cleanly without PyYAML** instead of reporting a spurious failure.

### Removed

## [3.2.1] — 2026-08-29

### Added

### Changed

### Fixed

- **Cycles can accept ADRs and archive books again.** `transition-adr` and `archive-promptbook` no longer carry `disable-model-invocation`, which had blocked `dev-cycle`, `iterate`, and `patch` runs from completing those steps without a human keystroke. The four true human gates (`reconcile-signoff`, `backfill-signoff`, `escalate-arch-runtime`, `transition-invariant`) keep it.

### Removed

## [3.2.0] — 2026-08-28

### Added

### Changed

- **Corrected the OpenCode `permission.task` projection.** A restricted `Agent(role)` grant projects as a deny-first per-role glob object instead of collapsing to a coarse boolean. The widened-grant report and its sign-off file are retired as unneeded.
- **Documented the fields OpenCode ignores.** `$adr`/`$book` argument placeholders bind only in Claude Code, and a new `OPENCODE_GUIDE.md` section lists the invocation-control fields OpenCode does not honor.
- **The model catalog no longer disables `fable`**, so it is a routable agent `model:` value again.

### Fixed

- **`forge-skill`'s frontmatter guidance matches the schema-3 metadata contract.** It no longer names the removed `owner`/`version`/`status` keys, so a forged skill promoted into the plugin passes `validate-catalog`.

### Removed

## [3.1.0] — 2026-08-28

### Added

- **`compile-doctrine`, the skill front for the doctrine regenerator.** It regenerates `adrs/doctrine/` from the summaries projection, reconciled against ratified invariants and the human-signed reconciliation ledger; `--dry-run` is the drift check. It stops and recommends `summarize-adrs.py` first when the summaries projection has drifted.
- **`check-drift`, a read-only runner for every enrolled drift gate.** It runs each regenerator's `--dry-run` in one pass and reports one table of gate, verdict (clean / drift / broken / crash / refusal), drifted paths, and the regenerator that fixes it. Wired into `audit-docs` as `CHK-DRIFT-1`.
- **`reconcile-signoff`, the single human write path for one doctrine reconciliation.** It renders the invariant and rule text, takes the verdict (compatible / reconciled / collision) and rationale from you, and upserts a digest-bound record. It never chooses a verdict, never batch-signs, and carries `disable-model-invocation`.

### Changed

- **Catalog schema 3: invocation-control frontmatter and a metadata prune.** `SKILL.md` admits the Claude Code invocation-control keys (`disable-model-invocation`, `user-invocable`, `context`, `agent`, `model`, `effort`, `background`, `arguments`, `disallowed-tools`); agents admit `maxTurns`, `effort`, `skills`, `memory`, `isolation`, and `disallowedTools`, each projected to Codex and OpenCode by a locked faithful-or-drop table. The dispatch tool `Task` is renamed to `Agent` (with the restricted `Agent(role)` form). **Breaking:** the `owner`, `version`, and `status` metadata keys are removed from every skill and agent, and a lingering one is a validation error. `plugin.json` `schema_version` goes `"2"` → `"3"`.

### Fixed

- **A block-style `disallowedTools`/`skills` agent list fails validation instead of silently mis-projecting** (`bash` rendered `allow` instead of `deny`). Every shipped agent authors these inline.

### Removed

- **The `inject-knowledge` skill is retired.** Its bundled knowledge layer shipped only a README and nothing referenced it; the skill, its module, and its bundle and routing rows are removed.

## [3.0.0] — 2026-08-28

### Added

- **The doctrine layer, a third ADR-decision tier.** `adrs/doctrine/` projects each governs domain's live rule, disposition, and implemented-vs-on-paper state from the summaries projection, reconciled against ratified invariants through a digest-bound, human-signed ledger, with a deterministic regenerator and a drift gate. Reads now route doctrine → summaries → ADR body, with the ADR body winning on disagreement.

### Changed

- **The `qwen-max` OpenCode alias points to `openrouter/qwen/qwen3.8-2.4t-a95b`.** The standard-rung OpenCode agents — historian, librarian, and wayfinder — resolve through it.
- **The architect's OpenCode model is the flagship default `kimi-latest`** (`openrouter/moonshotai/kimi-k3`); its per-agent `glm-latest` override was dropped.

### Fixed

### Removed

## [2.2.0] — 2026-08-28

### Added

- **Governs backfill: a historic ADR can enter the summaries projection.** An ADR numbered below `adr.governs_from` joins the projection only through an anchored, digest-bound, reviewed, at-most-once backfill, via the `anchor` `governs` sub-field, a `backfill-reviews.yml` receipts manifest, the `backfill-signoff` owner-gate skill, and the `backfill` log op.

### Changed

- **The "Silver" ADR-summary layer is renamed "summaries".** `adrs/silver/` → `adrs/summaries/` and `generate-silver.py` → `summarize-adrs.py`. Forward-only: frozen ADR bodies, logs, and journals keep "Silver" as history.

### Fixed

### Removed

## [2.1.0] — 2026-08-26

### Added

- **ADR frontmatter gains a `governs` block, and a regenerator projects it.** An ADR may author a `governs` entry — `domain`, `rule`, `scope`, `handle`, `provenance` — cohort-bound by the new `adr.governs_from` manifest field. `generate-silver.py` projects every block into a rule table, a resolver, and an ADR↔run implementation map under `adrs/silver/`, behind its own `--dry-run` drift gate. A coverage gate and a reference linter distinguish a rule handle from a plain ADR citation.

### Changed

- **Model calls crux itself performs route through OpenRouter as a single gateway.** The router, the council, the catalog aliases, and the video transcriber resolve every call through one OpenAI-compatible endpoint under one `OPENROUTER_API_KEY`. The direct Anthropic/OpenAI/Google SDKs and the Fireworks provider are retired.

### Fixed

### Removed

## [2.0.1] — 2026-08-25

### Added

### Changed

### Fixed

- No plugin behavior change. The development repository's release gates now run under `uv run` rather than a bare `python3`, so a machine whose default `python3` predates the required interpreter no longer misreports a ready tree; the development repository pins Python 3.13 for that tooling.

### Removed

## [2.0.0] — 2026-08-25

### Added

- **A deterministic per-derive coverage report.** `arch/_meta/coverage.json` records, for each spine concern, whether it populated or fell back to a stub, and why; it is byte-stable and rides the existing drift gate.
- **Confidence-graded arch extraction.** Each spine concern self-assesses a grade — high, medium, low, or none — recorded in the coverage report. At or below the new `arch_confidence_threshold` config key (default `low`), a stubbed or partial concern offers an attended runtime-escalation session in chat. The unattended pipeline stays static and deterministic.
- **A model catalog.** `crux/catalog/models.yml` (`schema_version 2`) decides which model every agent runs on through a provider allowlist, an alias table, the ten-agent roster keyed to three levels (`apex`, `flagship`, `standard`), and the `claude_aliases` / `claude_disabled` pins. `models_catalog.py` is the shared reader and refuses a malformed catalog rather than degrading.
- **Validator rules V0–V9 over the catalog.** `validate-catalog.py` checks the roster against the agent files, every alias against the provider allowlist, each level's cells, and the Codex slugs against the router registry.
- **`escalate-arch-runtime`: Python import-only runtime introspection behind an attended two-factor consent gate.** It runs a target FastAPI, Flask, or Django app's import-time code in a subprocess-isolated child, recovering its route table and ORM schema as an advisory outside the arch spine. It executes only with `CRUX_ARCH_ALLOW_RUNTIME=1` set and a per-execution, non-model-mediated permission event.
- **A third cycle tier, `patch`, with a checked blast radius.** `patch-cycle` authors a five-phase book at one prompt each and declares the repository paths it may touch. `archive-promptbook` draws the actually-changed paths from `git diff` against the run's `base_commit` and refuses to archive a run that reached outside the declaration.
- **An ADR body content rule.** An ADR body states requirements and postconditions and carries a 120-line budget over its four narrative sections. `audit-docs` gains `CHK-ADR-SPEC`, inert in any tree that has not set the `adr.spec_rule_from` cohort boundary.
- **Two arch spine files are thin projections, and readers have a route to the spine.** `arch/api-surface.md` and `arch/decision-index.md` are projected from the skill catalog and the ADR index; a stale input is refused at exit 2 naming the regenerator to run. `query-docs` gains an architecture route, and all ten agents name `arch/` first for a question about the project's own shape.

### Changed

- **Council rounds are routed by blocking findings.** A round past the first fires only on a finding that names a failing check against an artifact in the repository work tree; round 3 is one adjudicator who is not the runner, within the three-round bound. SRDE is de-wired from the ADR path and stays wired to the verify path.
- **The OpenCode and Codex projections resolve models through the catalog** instead of carrying their own model tables. Adopting it moved four generated files: the `architect`, `commander`, and `developer` OpenCode roles, and the Codex `crux-developer` agent.
- **In `crux/catalog/`, the file extension declares provenance.** `.json` means regenerated from a source of truth elsewhere; `.yml` means hand-authored and never written by a generator.

### Fixed

- **The arch drift gate no longer fires on edits that leave the spine byte-identical.** It compared the whole `_meta/manifest.json`, whose `sources` map carries a hash per tracked file, so editing any tracked source reported drift. `derive-arch.py` also declares PyYAML, so one source tree produces one spine hash.
- **The runtime introspection entry point is genuinely stdlib-only** and no longer crashes with `ModuleNotFoundError: httpx` in a shipped install.
- **The runtime introspection child no longer writes bytecode into the installed plugin.**
- **The curated decision-index mode is reachable** via the new `arch_decision_index_mode` config key. The default stays `complete`.

### Removed

- **Breaking: per-advance run bookkeeping, three promptbook surfaces, and the pinned spine-hash constant.** `run-promptbook` no longer writes a log op or regenerates the promptbooks index per advance; a run's chronology comes from its snapshot timestamps. The `cycle-status` skill is deleted and its trigger phrases move to `visualize-run-progress`. The per-prompt `blocked_confirmed` flag is retired; archive eligibility is a run-level property. `author-promptbook --fork-from` is deleted — change a plan mid-run by abandoning the run and authoring a successor book.
- **`crux/catalog/bundles.json` is replaced by `crux/catalog/bundles.yml`**, a mapping keyed by bundle id, read through a loader that refuses anchors, aliases, merge keys, explicit tags, and a second document. The catalog ships inside the plugin, so no downstream repo owes a migration.

## [1.14.0] — 2026-08-18

### Added

- **An Elixir/Phoenix arch stack pack, completing the set (Python, Ruby, Node, Elixir).** The interface surface comes from a committed OpenAPI spec, else a static parse of the Phoenix router (never booting the app); the data model from Ecto schemas, with the `null` column left blank where a schema cannot express it; the module graph from `alias`/`import`/`use` and remote calls resolving to in-repo modules.
- **A Node.js arch stack pack.** Routes come from a committed OpenAPI spec, else a static scan of Express, Fastify, and NestJS; the data model from Prisma's `schema.prisma`, else TypeORM entities or Sequelize models; the module graph from explicit TS/JS imports with `tsconfig` alias resolution. All parsing is static and never boots Node.
- **A Ruby arch stack pack.** Routes come from a committed `openapi.json`, else a static parse of `config/routes.rb`; the data model from `db/schema.rb`; the module graph from a resolve-or-drop pass over the Zeitwerk autoload roots.

### Changed

### Fixed

### Removed

## [1.13.0] — 2026-08-17

### Added

- **Pluggable arch stack packs, with a Python pack.** `derive-arch` detects the project's stack and resolves each spine file through a per-repo override, then the detected pack, then a stub. The Python pack derives the interface surface from a committed `openapi.json`, the data model from SQLAlchemy models plus Alembic history, and the module graph from the project's own package. Two `.bionic.yml` keys configure it: `arch_stack` pins the pack, and `arch_extractors` registers a per-repo override that runs only under `CRUX_ARCH_ALLOW_OVERRIDES=1`.

### Changed

### Fixed

### Removed

## [1.12.0] — 2026-08-17

### Added

- **`install-opencode-agents` skill**, the OpenCode counterpart to `install-codex-agents`. Say "install the Crux agents in OpenCode" to write the ten projected roles into a project's `.opencode/agent/`. It refuses to overwrite a locally modified role without `--force`, refuses a symlinked managed entry, refuses a target outside the repo root, and never touches a project's own agent files. Skill count 49 → 50.
- **The public repository ships a `.gitignore`** covering the untracked `opencode/` tree the OpenCode setup generates.

### Changed

- **The skill runtime-compatibility contract names OpenCode.** Every skill's compatibility block now states the OpenCode form of plugin-root resolution, `.opencode/skill` for project-local skills, the lowercase tool labels (`edit` covering both `Edit` and `Write`), and `install-opencode-agents` with the bare hyphenated role names.
- **OpenCode setup documents the singular `~/.config/opencode/agent/`** in the README and `OPENCODE_GUIDE.md`, noting that populating both singular and plural forms leaves you guessing which copy is live.

### Fixed

- **`install-codex-agents` and `generate-codex-agents.py` no longer traceback on a non-directory output path.** A regular file, a symlink to one, or a dangling symlink now produces a structured refusal and exit 2. The same guard applies to the OpenCode lane.
- **`generate-opencode-agents.py` no longer writes through a symlinked agent file.** Replacing a generated agent file with a symlink previously overwrote the link's target anywhere the user could write.
- **`crux_wayfinder` was missing from the agent roster in every skill's compatibility block**, and `install-codex-agents` still said it installed "nine" roles. Both now say ten.
- **The OpenCode setup gained an upgrade step.** `opencode/agents/` is a generated projection, so a `git pull` left it stale while the symlinks still resolved. Both docs now instruct regenerating after every pull, and `OPENCODE_GUIDE.md` gains troubleshooting rows for stale projections and dangling symlinks.
- **Stale paths and a hardcoded "47 skills" figure in `OPENCODE_GUIDE.md`** were corrected.

### Removed

## [1.11.0] — 2026-08-16

### Added

- **`derive-arch` skill**, the user-facing entry point to the `arch` concern. Say "build the arch", "summarize the current architecture", or "regenerate the architecture" to regenerate the derived current-state map (data model, interface surface, module graph, decision index, and a synthesized overview). `arch` is now the primary current-state discovery surface, with ADRs the secondary "why", and gains a dedicated `arch` log op. Skill count 48 → 49.
- **Arch coverage in `audit-docs`.** `CHK-ARCH-1` checks the derived spine for drift and regenerates it in place as a DRIFT-tier auto-fix; `CHK-ARCH-2` recognizes arch enablement.

### Changed

- **`init-docs` enables the `arch` concern by default for new repositories.** A fresh tree enrolls `arch` in `concerns_enabled` and scaffolds `arch/` with a placeholder; the first "build the arch" or `audit-docs` run derives the spine. Existing trees are unchanged — add `arch` to `concerns_enabled`, then derive. No `schema_version` bump.

### Fixed

### Removed

## [1.10.2] — 2026-08-14

### Added

### Fixed

- **Two stale skill counts in the docs.** `README.md`'s OpenCode setup and `USER_GUIDE.md`'s quickstart said 46 skills; both now say 48, and a drift gate keeps the anchored counts matching what is on disk.

## [1.10.1] — 2026-08-14

### Added

### Changed

### Fixed

- **The arch `module-graph.md` was incomplete.** The extractor matched only absolute imports; it now resolves relative imports, uses full-module node ids, and lists isolated modules.
- **Arch no longer drifts on a routine manifest counter bump.** The meta hash covers only the manifest key names the data model renders.
- **README/skill doc drift**: skill count 46 → 48, agent count nine → ten, three missing skill rows (`prose-review`, `recover-decisions`, `transition-decision`), and `prose-review`'s description now says "seven writing rules".

### Removed

## [1.10.0] — 2026-08-14

### Added

- **Decision recovery.** `recover-decisions` mines load-bearing decisions latent in code into `observed` candidates — structural-anchor identity, `path:line-range` evidence with no code excerpt, redaction-scanned statements — in `arch/_recovered/state.yml`; `transition-decision` ratifies a candidate into a Proposed ADR (idempotent via `recovered_id`), or rejects or defers it. `derive-arch.py` gains `decision_index_mode: complete|curated`, and a new `recover` log op.
- **An ADR archival cold tier.** Superseded and Deprecated ADRs move to `adrs/archive/`, shrinking the active reading path while staying immutable and resolvable. `transition-adr` moves an ADR on Supersede/Deprecate; `propose-adr` scans both tiers so an archived id is never reissued; `generate-adr-index.py` regenerates `adrs/index.md` with an `## Archived` roster; `audit-docs` gains `CHK-ADR-ARCHIVE`.
- **Writing rule #7: footnote-only ADR citation.** In human-facing prose, reference an ADR by footnote, never an inline number or link, with carve-outs for ADR bodies and the journal. A new AST-based check flags inline references while skipping code, link destinations, frontmatter, blockquotes, HTML, and footnote definitions, with a ratchet baseline so it enforces going forward.

### Changed

### Fixed

### Removed

## [1.9.0] — 2026-08-14

### Added

- **The arch concern.** `<docs_dir>/arch/` is the project's derived architecture — a deterministic spine (`data-model`, `api-surface`, `module-graph`, `decision-index`) plus a synthesized `overview.md`, regenerated by `derive-arch.py`. A SHA-256 hash-stamp over the spine gates the narrative, and `derive-arch.py --dry-run` fails when the spine moved without a re-derive. `docs_dir` is containment-checked before any write.

### Changed

### Fixed

### Removed

## [1.8.2] — 2026-08-02

### Added

- **Prose-vs-template drift gates.** New tests pin the `init-docs` skill prose to the shipped templates and catch template comments that contradict a template's own values, so the class of drift fixed below cannot recur.

### Changed

- **`init-docs` bootstraps the unified `bionic/` tree.** The skill creates the schema-5 layout at the resolved `docs_dir` (never a hardcoded literal), with concerns directly under the tree and the invariants concern as one folder, and writes `.bionic.yml` with merge-never-clobber semantics. The guard refuses symlinked trees, checks the other well-known location for a second tree, and rollback removes only paths written this run.
- **Templates and schema docs describe the schema-5 world.** The shipped `CLAUDE.md.tmpl` gains the `"5"` row, diagram roots at `bionic/`, and `<docs_dir>` paths; template comments agree with their values; both USER_GUIDEs name `bionic/`, `schema_version 5`, and `.bionic.yml`. `install-docs-skills` resolves the tree instead of testing for a literal `docs/`.

### Fixed

- **Fresh installs bootstrapped a `docs/` tree with schema version "4" prose instead of the `bionic/` tree at "5".** The `init-docs` skill prose still described the old split layout, and its verification checklist would have rolled back a correct bootstrap.
- **`docs_dir` rejects shell metacharacters.** A committed `.bionic.yml` could set `docs_dir` to a value like `$(id)`, which passed validation and executed when skills composed shell commands around it. Each segment must now match `^[A-Za-z0-9_.][A-Za-z0-9._-]*$`.
- **The template-parity gate was silently inert since the tree move**, because its canonical paths pointed at the retired location; it now resolves correctly and has a liveness test.

### Removed

## [1.8.1] — 2026-07-31

### Fixed

- **`migrate-tree.py` could not migrate a relocated tree, and would have damaged one if forced.** It hardcoded its source to `<root>/docs` and ignored the configured `docs_dir`. Source is now resolved through both config files, the destination is anchored at the true repo root, and a relocated tree stays where its owner put it — only the invariants suite merges into it. `--docs-dir` is the escape hatch for a layout no config declares.
- **The documented upgrade path was a closed loop.** `audit-docs --migrate` documented only rungs 2→3 and 3→4; the 4→5 rung is now documented with its invocation, exit codes, and fail-closed behaviors.
- **Containment on every path that reads, writes, or removes.** A `docs_dir` of `../elsewhere`, an absolute path, or an escaping symlink is refused rather than followed; symlinked directories are refused during merges even when they stay in-repo.
- **`CLAUDE.md.tmpl` shipped eight literal `<tree>` placeholders** that no render step substitutes, and described tree relocation as "deferred".
- **`install-docs-skills` hardcoded schema `"3"`** while the plugin shipped `"5"`; it now reads the supported value from the installed manifest.
- **`audit-docs` was self-contradictory about the supported schema** (predicate `"5"`, surrounding text `"4"`) and its `CHK-CFG-1` breadcrumb still called the invariants concern deferred.

## [1.8.0] — 2026-07-30

### Added

- **Breaking: the tree lives at `bionic/`, and the invariants concern is one folder.** The seven concerns sit directly under `bionic/` — no nested `docs/` level — and the invariants concern holds its ledger pages, `checks/`, and `reconciliation.yml` together. `init-docs` always writes `.bionic.yml` naming the tree. `schema_version` `"4"` → `"5"`.
- **Bare-directory discovery.** A tree is recognized by a manifest carrying both `schema_version` and `concerns_enabled`. Two valid trees refuse loudly unless a migration marker names one; exactly one resolves to it; none resolves to `bionic`. An existing `docs/` tree keeps working with zero config and no migration.
- **`migrate-tree.py`, the 4 → 5 rung.** A staged, resumable merge: `manifest.yml` moves last so a crash leaves discovery resolving to the source, and a marker records the source inventory so replay can tell an already-moved entry from a real collision. Config is merged, never overwritten.
- **A schema gate.** Commands that read the tree refuse an unmigrated one with exit 2 and a message on stderr.
- **Six writing rules, and `prose-review` — the 46th skill — to check them.** One name per thing, no hedge without a cause, verbs stay verbs, adjectives must be checkable, one idea per sentence, single-word verbs; accuracy outranks all six. There is no banned-word list, only tests applied per sentence. `prose-review` reports only findings that carry a rewrite: `fix` when the rewrite follows from the text, `confirm` when it needs a fact only the author holds.
- **`generate-writing-rules.py`.** One canonical rules text projects byte-equivalently into `AGENTS.md`, the operational schema template, and the shipped `prose-review` skill, with atomic writes and a `--dry-run` drift gate.

### Changed

- **`prose-review` runs at fixed points**: the `dev-cycle` / `iterate` prep prompt, and `tend-garden` before it writes the morning note.

### Fixed

### Removed

## [1.7.0] — 2026-07-24

### Added

- **Opus 5 refusal handling in the council seats.** A safety refusal returns HTTP 200 with `stop_reason: "refusal"` and previously surfaced as a JSON-parse error or `unknown`. A new `ModelRefusedError` maps to a new closed-vocabulary redaction label, `"refused"`, so the operator knows to change the prompt or fall back to another model rather than retry.
- **Spawn caps on the delegating agent roles.** `commander` and `dev-lead` spawn one agent per genuinely independent unit, never for work finishable in about three tool calls, never solely to double-check — with a carve-out for the architectural gates (independent review, per-threat-class security review, two-architect ADR acceptance).
- **Scope-discipline guidance on `dev-lead`**: deliver at the intended scope, without unrequested refactors.

### Changed

- **Model swap: `claude-opus-4-8` → `claude-opus-5`** across the LLM router config and the OpenCode agent generator. `claude-fable-5` remains the flagship seat; `claude-opus-4-8` is removed from the router registry. Router config `1.4.0` → `1.5.0`.
- **Agent and cycle-skill prose re-tuned for Opus 5's defaults.** `architect` states plan coverage and type consistency as required properties; the `dev-cycle` and `iterate` checklists no longer re-derive by hand what `validate-promptbook.py` machine-guarantees. Every cross-agent gate is preserved verbatim.

### Fixed

- **`dev-cycle` / `iterate` checklists overstated validator coverage.** The cycle-coverage pass checks module size and contiguity, not prompt content, and `cycle_grandfathered: true` short-circuits it entirely; both checklists now say so.

### Removed

## [1.6.0] — 2026-07-23

_Three bodies of work land together: remediation of six defects a downstream repository surfaced while using v1.5.0; a durability program in which every derived artifact gains a regenerator and a drift gate; and a hardening of the council's secret-redaction path._

### Added

- **`generate-lineage.py`, a regenerator for `adrs/lineage.md`.** `link-adr-graph`'s engine is now a committed, deterministic script rather than prose-only instructions.
- **`generate-index-rollup.py`, a regenerator for the `## ADRs (N)` rollup in `index.md`**, which is now a pure function of ADR frontmatter with a `--dry-run` drift gate. Regenerating it surfaced a truncated ADR title, a sort-order violation, and four missing rows a prose audit had missed.
- **`advance-run.py`, a safe-advance script for promptbook run snapshots.** It mutates the current prompt, moves the pointer or completes the run, updates the book's pointer, and round-trips every top-level key so run-level `notes` / `pr_draft` / `summary` fields survive each advance. `run-promptbook` now prefers it.

### Changed

- **Council deliberation is hardened against a single errored provider seat.** Aggregation runs over responding seats only, requires a quorum of ≥ 2 (`NO_QUORUM` below it), surfaces `errored_seats` and a `degraded` flag, caps a degraded verdict at `EXECUTE_WITH_MONITORING`, and counts `APPROVE_WITH_NITS` as an approval. `run-adr-council` documents single-errored-seat and mixed-verdict outcomes and multi-round composition.
- **Wiki-link resolution is lifecycle-agnostic and reference-inclusive.** An ADR's `related_research` entry resolves to any research page behind a fail-closed containment grammar, and a journal→promptbook link resolves on its `PB-NNNN` id across `active/` or `archive/`; `[[promptbooks/PB-NNNN-<slug>]]` is the write form and legacy spellings still resolve.
- **Whiteboarding sessions carry into the brief body.** `propose-brief --from-inbox <session-path>` populates the brief from a whiteboarding session, `process-inbox` passes it for whiteboarding-classified items, and the three skills describe one behavior.
- **`CLN-TMPL-1` guards section content, not just section presence**, with curated content-marker clauses between the operational schema and the shipped `CLAUDE.md.tmpl`.
- **The `invariant` log op is a first-class member of the op enum**; `transition-invariant` emits it directly.

### Fixed

- A single errored council provider no longer poisons `consensus_confidence` or makes `UNANIMOUS_APPROVE` unreachable, and the driver no longer omits the multi-round loop it depends on.
- Two growing wiki-link dangle classes are retired: ADR `related_research` pointing at a synthesis page, and journal refs to now-archived promptbooks.
- The `whiteboarding → process-inbox → propose-brief` pipeline no longer orphans the session body behind an empty scaffold.
- **Provider exception text can no longer leak through council error paths.** Error redaction now builds its output only from a fixed label set plus a range-validated integer status, so no substring of a provider exception reaches a persisted deliberation surface. The previous regex leaked 12 of 18 adversarial credential shapes (AWS-shaped keys, DSNs with inline passwords, `apikey=` pairs); it now leaks 0. The same fix covers the sync council's `Opinion.position` and the visual council's `observations`.

### Removed

## [1.5.0] — 2026-07-18

### Added

- **The invariants concern, the seventh concern.** Pinned, ratified, executable statements of what must be true, verifiable against regeneration: a human-readable ledger under `docs/invariants/` plus an executable check suite at `bionic/invariants/`, reconciled through a `.bionic.yml`-rooted manifest. Two new skills implement a machine-proposes / human-ratifies model: `recover-invariants` mines code for `observed` candidate pins and never self-ratifies; `transition-invariant` is the human gate (`observed → ratified | rejected`, `ratified → retired`). `audit-docs` gains five `CHK-INV` rules. `manifest.yml` `schema_version` `"3"` → `"4"`.
- **`init-docs` enables the invariants concern by default for new repositories.** A fresh tree bootstraps at `schema_version: "4"` with all seven concerns. Existing trees adopt it opt-in via `audit-docs --migrate` (a new 3→4 rung); `init-docs` never upgrades a populated tree in place.
- **`.bionic.yml`, the repo-root layout source of truth.** A committed config file (`config_version`, `docs_dir`, `artifact_prefix`) supersedes the legacy `.crux` file, resolved with the precedence `.bionic.yml` > `.crux` > convention. Resolve it via the new `bionic-config.py` CLI; `crux-config.py` remains as a back-compat delegator.

### Changed

- **Forged-skill promotion is judgment-driven, not mechanically auto-nominated.** The former floor (≥2 `effective` evaluations on ≥2 distinct dates) is now supporting evidence the owner weighs, and `retrospective`'s promotion scan becomes an owner-facing evidence report. The `evaluated` forge-log discipline is unchanged.
- **`audit-docs` supports `schema_version` `"4"`**, walks the invariants concern, and gains the `3→4` migration rung.
- **Concern framing moved from six to seven** across the README, USER_GUIDE and its shipped template, and the operational schema.

### Fixed

### Removed

## [1.4.2] — 2026-07-13

### Added

### Changed

### Fixed

- **Release commits no longer attribute authorship to an unaffiliated real GitHub account.** The publish tooling previously used `sync@users.noreply.github.com`, which GitHub attributes to the real account `sync`. Release commits and annotated tags in the public repository are now authored by a dedicated machine identity (`crux release bot` / `no-reply@idyll.io`). Development-repository release tooling only — no plugin, skill, or docs-tree behavior change.

### Removed

## [1.4.1] — 2026-07-10

### Added

- **Public manual OpenCode setup instructions** in `README.md` (a new `### OpenCode (manual setup)` section) and a refreshed `OPENCODE_GUIDE.md`: clone to a stable path, `uv run generate-opencode-agents.py`, merge the absolute `crux/skills` path into `opencode.json`, glob-symlink all ten generated agents, restart the host, and verify with `opencode debug skill` / `opencode agent list`. There is no native Crux OpenCode marketplace package yet; the flow is manual and preview-grade.

### Changed

### Fixed

- Corrected the `README.md` status/footer version and completed the 43-skill table in the public README. Docs-only.
- `OPENCODE_GUIDE.md` counts corrected (42 → 43 skills, nine → ten agents), and the agent symlink step made glob-based so it covers all ten roles including `wayfinder`.

### Removed

## [1.4.0] — 2026-07-10

### Added

- **Generator test coverage for the OpenCode agent projection**, including body/description verbatim passthrough and YAML frontmatter validity, with PyYAML pinned so the YAML tests can no longer silently skip.
- **Codex becomes a fourth regenerated agent projection and a supported distribution target.** `.codex/agents/crux-*.toml` is generated from the same agent source files by `generate-codex-agents.py`, never hand-edited, with the shared `--dry-run` drift contract. Install with `codex plugin marketplace add idyll/crux` then `codex plugin add crux@crux`; the version lock-step now spans all four manifest surfaces. Target repos get the ten agents via the no-clobber, path-contained `install-codex-agents` skill, which refuses to overwrite a differing `crux-*.toml` role or remove a stale one without `--force`. The portable `CRUX_PLUGIN_ROOT` bridge is stated correctly everywhere (Claude Code = `CLAUDE_PLUGIN_ROOT`; Codex = derived from the selected `SKILL.md`'s path; source checkout = `crux/`). A leaf-symlink write-through in the shared generator/installer write path was closed, and the generated agents' models were corrected against the live Codex catalog (seven roles → `gpt-5.6-sol`, three → `gpt-5.6-terra`).

### Changed

- **LLM router refresh for the latest OpenAI and Anthropic releases.** The seven-SKU OpenAI lineup consolidates into three effort-controlled GPT-5.6 SKUs — Sol (flagship reasoning and coding, alias `gpt-5.6`), Terra (balanced), Luna (cost/high-volume) — all Responses-API-only; `gpt-image-1` → `gpt-image-2`; the `openai_reasoning` / `openai_reasoning_fast` roles are retired. `claude-sonnet-4-6` → `claude-sonnet-5`, which rejects the temperature parameter. Anthropic pricing corrected against the official source. `fast_council`'s arbiter is pinned to low reasoning effort via the `gpt-5.6-sol-low` alias.

### Fixed

- **OpenAI `/v1/responses` is first-class in the caller and the async council.** The async council's OpenAI seat hardcoded `chat.completions.create`, so the Responses-only GPT-5.6 lineup errored into a degraded vote, and `call_openai` never forwarded reasoning `effort` on the responses path, leaving the `gpt-5.6-sol-low` pin inert. Both seats now route by the model's `openai_endpoint`, with JSON mode, vision via `input_image`, and `reasoning.effort` forwarding.
- **Codex-integration corrections.** `CRUX_PLUGIN_ROOT` was mislabeled as a Claude-Code-loader-set variable across the shipped `CLAUDE.md.tmpl` and 13 skill bodies; strict-YAML tests skip cleanly without PyYAML; dated provenance comments anchor the external Codex model-slug and schema assumptions so future drift is diagnosable. A symlinked-ancestor bypass in the development repository's publish staging was also closed.

### Removed

## [1.3.3] — 2026-07-10

### Added

- **A self-detecting `CLN-TMPL-1` cleanup-campsite rule** checks operational-schema ↔ shipped-template clause parity: drift is a P2 finding naming the divergent section, a stale anchor is P3, and a tree with no template twins yields 0 findings. A new `cleanup-campsite --only <RULE-ID>` selector (CSV-capable; an unknown id is a loud error) enables single-rule runs.
- **`dev-cycle` and `iterate` record forge-log `used` / `evaluated` entries for forged skills they invoke**, so a cycle-used forged skill accrues the evidence it needs for promotion. No prompt-count or schema change.
- **`scout`, the tenth agent: a read-only context-preservation reconnaissance subagent.** A primary delegates the consume-to-judge step to it: it reads large, uncertain, or external data in an isolated context, judges fitness for a stated purpose, and returns a verdict plus a condensed digest. Tool grant `Read, Grep, Glob, WebFetch, WebSearch`; `Edit`/`Write`/`Bash`/`Task` withheld, with an embedded egress guardrail (never relay local content outbound, never read secrets). Model `sonnet`. Catalog 9 → 10 agents.
- **`run-adr-council` joins the plugin** (catalog 41 → 42, in the `crux-verification` bundle): the ADR council runner, rebuilt so the council prompt is a data file written by the file-write tool and no shell string ever holds ADR prose.
- **The forged-skill promotion path.** Forged skills are usable in the session that forged them, every authoring or using session writes a session-end `evaluated` forge-log entry, `retrospective` gains a promotion scan nominating skills that clear a floor (≥2 effective evaluations, ≥2 distinct dates, ≥1 post-authoring, no unresolved fell-short), and graduation into the plugin is always a dev-cycle. New `cleanup-campsite` rule `CLN-FG-2` backstops the evaluation discipline. Project-local skills cannot PR into the public repo; share via issue.
- **The night gardener, the ninth agent, and her two skills.** A standing overnight visionary/coach/co-CTO who reviews recent work and writes a morning note under `docs/garden/`: new ideas, improvement vectors, missing tests/guards, research directions, and relevant news. She is turn-based — she moves only after you have moved — and may run a retrospective when due, whiteboard into the inbox, and draft `garden/<slug>` branches, never pushed or merged. `tending.md` is your control surface: dismiss (permanent) or snooze, with no acknowledgment burden. New skills `tend-garden` (the night-pass orchestrator) and `read-news` (Perplexity-Search-backed reading with a Perplexity → WebSearch → skip fallback; `PERPLEXITY_API_KEY` optional via `~/.crux/`). Adds the `garden` log op. Catalog 39 → 41 skills, 8 → 9 agents. The nightly routine is owner-installed; crux never self-installs persistence.
- **`retrospective`, purposeful reflection that harvests skills from finished work.** It mines the operations log, journal reflections, archived promptbooks, `whats_next`, and the forge log since the last `Retrospective:` marker, distills 0–2 evidence-cited skill proposals, gates each through a fixed rubric, and builds approvals via `forge-skill`. Cadence via trigger phrases and new `cleanup-campsite` rule `CLN-RETRO-1` (P3, `retro_due_runs` default 5). Catalog 38 → 39.
- **`forge-skill`, the capability-gap loop.** When a capability gap surfaces mid-task, the model diagnoses it with a testable closure criterion, whiteboards, researches, authors or revises a permanent project-local skill under `.claude/skills/<name>/`, and self-tests on the live problem — autonomous by default, propose-first for outward-facing or secrets-touching capabilities. Every act lands in the append-only forge log (`.claude/skills/forge-log.md`), plus a new `skill` log op. All eight agents carry the capability-gap reflex. New `cleanup-campsite` rule `CLN-FG-1` flags forged skills idle past `forged_skill_stale_days` (default 30).
- **PEP 723 + `uv run "${CLAUDE_PLUGIN_ROOT}/..."` runtime contract.** All 18 shipped runnable scripts carry PEP 723 inline-metadata blocks and are self-describing under `uv run`; a test enforces that every documented `uv run` entry point has one.
- **`check-public-release-content.py`**, a scan that bans concrete ADR references on distributed surfaces (`crux/skills`, `crux/agents`, `crux/templates`).

### Changed

- **The reconnaissance agent is renamed `scout` → `wayfinder`**, one name across Claude Code and OpenCode. A pure rename — capability, tool grant, model, mode, and security contract are unchanged. It resolves the collision with OpenCode's built-in `scout`.
- **The `architect` agent holds `Bash`**, so a dispatched architect can run the multi-model council driver its remit requires.
- **The `dev-cycle` quality gate mandates the full test suite**, not a hand-picked subset, whenever a change touches a shared or enumerated surface (agent roster, router config, catalog). Applied to `dev-cycle` and `iterate`.
- **LLM router curated to the latest-generation lineup; `claude-fable-5` disabled.** Router config 1.2.0 → 1.3.0: older models removed (gpt-5.2 family, o3, o4-mini, gemini-2.5-*, claude-haiku-4-5, claude-fable-5-medium); `gpt-5.5-pro` and `gemini-3.5-flash` added; pricing and context corrected. `claude-fable-5` is retained but `enabled: false`, and the OpenCode `architect` and `commander` remap to `claude-opus-4-8`. (Superseded by the GPT-5.6 refresh in 1.4.0.)
- **Split-repo publication model.** The public `idyll/crux` repository is a generated artifact receiving one squash commit and tag per release; the three public docs are generated, human-reviewed artifacts. Releases attach no zip assets — the marketplace model makes them redundant.
- **The "Crux Lite" framing is gone from every live surface.** All three manifest descriptions converge on functional phrasing; the README and USER_GUIDE open on the product's own terms.
- **Marketplace-only install story**: `/plugin marketplace add idyll/crux` + `/plugin install crux@crux`, across README, USER_GUIDE, templates, and skills.
- **`${PLUGIN_DIR}` → `${CLAUDE_PLUGIN_ROOT}`** as the canonical plugin-root variable in every documented invocation.
- **Spawner runtime directory `.crux` → `.crux-runtime`**, with refusal on a foreign target (`SpawnTargetConflictError`) plus symlink and containment guards.
- **Provenance fields (`origin`/`origin_ref`/`origin_date`) removed** from the SKILL.md frontmatter contract and the regenerated catalog; ~200 internal ADR references removed from distributed surfaces; git softened to enhancement-not-requirement.
- **Distributed `CLAUDE.md.tmpl` rebuilt** to the current contracts.

### Fixed

- **The public-release content scan runs inside the cycle quality gates** (`dev-cycle`, `iterate`), so a banned internal reference on a distributed surface fails in-cycle. Exit 1 = a finding to fix; exit ≥ 2 = environment error.
- **The bare-`python3` test lane is honest.** Module-import-time capability guards make `uv`-less runs report clean skips instead of 28 errors, and `validate-promptbook`'s PyYAML re-exec lane no longer replaces the unittest runner mid-suite. `check-no-stale-skill-names.py` gained kebab-boundary guards. README agent count corrected to 9.
- **The test suite is green again after the router curation.** Six router tests re-pointed to the surviving lineup; a
