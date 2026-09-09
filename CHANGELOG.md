<!-- generated-from: CHANGELOG.md@sha256:e177b5a8f8f4fe3193d1ccd9bb2fe94ba2ab93a2436e2141417e80e37e39b3f5; model: claude-fable-5.1; date: 2026-09-09 -->
# Changelog

All notable changes to crux. The format follows [Keep a Changelog](https://keepachangelog.com/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [3.11.0] — 2026-09-09

### Added

- **The journal index is now a regenerated artifact.** A new `generate-journal-index.py` regenerator derives the `journal/index.md` month rows (entry counts and category rollups) from the month files, with a `--dry-run` drift gate. Headings quoted inside a code fence no longer open a journal entry, and an unclosed fence refuses the write at exit 2, naming the source file and the line of the opening fence.
- **Decision-review findings are tracked across dates.** A review report's `## Coverage` section now carries a record table (source report date, finding id, pass, event, locator). A finding's standing follows its records in order: no record leaves it open, `re-verified` leaves it open, `disputed` disputes it, and only `resolved` closes it. The generated reviews index gains a `standing` column beside `raised`.

### Changed

- **`log-work` derives the journal-index row instead of incrementing it.** Every journaling write recomputes counts from the month file rather than carrying an existing count forward, and `init-docs` writes the first index when it creates the tree.
- **`check-drift` reports a missing review or journal surface as N/A for any gate**, and names the remedy: `review-decisions` when a review is due, `init-docs` when the journal surface was never created.
- **A report's finding count is the number of finding definitions, and the reviews index renders four columns** (`raised`, `standing`, `dismissed`, report link). Only `###`-headed definitions under Propose, Amend, Repair or Revoke count toward the five-finding cap; a summary table whose ids duplicate or disagree with the four sections is refused. A new `report_grammar` frontmatter key selects the grammar: a report with no discriminator reads as legacy, a report dated after 2026-09-08 with none is refused, and an unrecognized value is refused. `generate-reviews-index.py` now refuses a symlinked or dangling `adrs` or `reviews` directory by name, reads reports without newline translation, and bounds the resolver read at 64 KiB.

### Fixed

- **The architect agent and both user guides cite the current decision-review boundary** (five write paths, two log ops). The OpenCode and Codex agent projections are regenerated from the corrected source.
- **`adr-signals.py` refuses a symlinked `log.md`, `journal/` or `promptbooks/runs/` by name, even when the link dangles**, instead of silently treating the surface as absent when computing dormancy.
- **`review-decisions` records completely.** Its write set is now five paths across two operation kinds: the review writes one `adr-review` op directly, and `log-work` writes the `journal` op, the entry and the journal-index row, so a completed pass no longer leaves the index stale.

## [3.10.1] — 2026-09-09

### Changed

- **Beta before official.** Every version is now installed and tested from a private beta channel before the same bytes are published to the public `bionic-coding/crux` repository; a version that fails beta never ships. The README and deployment docs describe the two-step process.
- **The README is titled "Crux"** and describes the project as an Agentic Harness plugin, matching the public repository.

## [3.10.0] — 2026-09-08

### Added

- **Three delivery signals in `adr-signals.py`: `release_cadence`, `schema_growth` and `gate_count`**, beside the five it shipped with. Every git read runs a fixed argument list under an environment allowlist (`PATH`, `LC_ALL=C`, `GIT_CONFIG_NOSYSTEM=1`, and `SYSTEMROOT` on Windows), so neither user nor system git configuration is consulted.
- **Decision-review reports carry six sections.** A report dated after 2026-09-07 has Propose, Amend, Repair, Revoke, Keep and Coverage in that order, one summary table, and one data-framing note. Repair holds findings whose fix writes no ADR (skill prose, a template, the schema, a script); Revoke holds findings that revoke a decision. The five-finding cap counts across those four sections; Coverage gains a per-goal matrix. Older reports keep the sections they were written with.
- **The journal `Friction:` line.** A journal entry may carry one `Friction:` line naming a specific friction, placed before `Refs:` and counting toward the 1–10 body-line budget; an empty remainder is a contract violation. The new `journal.friction_line_from` manifest key records the date from which friction is measurable. `log-work` writes the line; `retrospective` and the friction signal count it.

### Changed

- **The public repository moved to the `bionic-coding` GitHub organization.** Install with `/plugin marketplace add bionic-coding/crux` or `codex plugin marketplace add bionic-coding/crux`; the plugin manifests' `homepage` now points at `https://bionic-coding.com/crux/`, and the README opens with a "Start here" link to that site.
- **Apex roles run Fable 5.1 on Claude, and the night gardener joins the apex tier.** A `fable-latest` alias is added; the commander, reviewer and night gardener run Fable. The reviewer's turn budget rises to 150 and the night gardener's to 100. Standard-tier Codex roles run at high reasoning effort.
- **`review-decisions` aims the pass at delivery.** It runs eight signals, routes each finding by two ordered questions about its proposed act, and disposes the top three dormant and top three paper-only ADRs each pass with `keep`, `revoke` or `defer` and one reason. An objectives file still at `placeholder` maturity stops the pass rather than yielding a judgment with no yardstick.

### Fixed

- **`init-docs` creates the `adrs/reviews/` directory**, so the first review cadence nudge no longer points at a path that does not exist.
- **`log-work` no longer describes a retired `run-promptbook` log-only call path.**
- **`adr-signals.py` reads both member shapes of `adr.governs_exempt`** (a bare id, or an `{adr, reason}` mapping), and the operational schema documents both.
- **Markdown mined from ADRs is split into lines by the CommonMark rule** (`\n`, `\r\n` or a bare `\r`) rather than Python's `str.splitlines()`, so exotic separator characters can no longer forge a heading, table row or fence closer. Fence indent and closer detection are bounded on the same character class, so a tab- or NBSP-indented fence no longer opens.
- **Rendered signal output is hardened.** Mined keys and values are both redacted before rendering (terminal escape sequences can no longer reach the output), the `prep_commits` mapping key carries a full 64-character digest, and an uncompilable version pattern becomes a `null` finding for that version instead of failing all eight signals.

## [3.9.0] — 2026-09-07

### Added

- **`review-decisions` — the periodic architect review of the decision set.** The 60th skill reads the accepted decisions as a set and asks whether they still serve the objectives. It enters through the doctrine index and rule table, opens an ADR body only for a domain a signal flagged, and writes at most five findings into one dated report at `adrs/reviews/YYYY-MM-DD.md`. It proposes only: it transitions no record, signs off no batch, and authors no skill.
- **`adr-signals.py` — five mechanical signals as verdict envelopes.** A stdlib-only script computes amendment fan-in, carve-out count, paper-only, dormancy and friction citations. Every signal is a five-field record (`signal`, `verdict`, `value`, `basis`, `filter`) with no severity or recommendation. A signal whose evidence surface does not exist reports `unmeasurable` rather than `0`.
- **The reviews index is a regenerated artifact.** `generate-reviews-index.py` derives `adrs/reviews/index.md` from the dated reports and fails closed on a filename outside `YYYY-MM-DD.md` or frontmatter that disagrees with the filename. A tree with no reviews directory exits 0 with `"surface_absent": true`, which `check-drift` reads as N/A rather than a clean gate.
- **The objectives file.** `objectives.md` holds the product's mission and `OBJ-N` goals (kind, statement, measure, status), a `maturity` ladder, and an append-only `## Shifts` table. `init-docs` seeds it as a placeholder; every reader asks the owner to fill it in rather than citing a placeholder.
- **Lint rules for the review.** `audit-docs` gains five `CHK-OBJ-*` rules over the objectives file. `cleanup-campsite` gains `CLN-ADR-5` (a decision review older than `adr_review_due_days`, default 7) and `CLN-OBJ-1` (an objectives file still at `maturity: placeholder`), and now ships 20 rules. The log op enum gains `adr-review`.

### Fixed

- **A second `review-decisions` pass on one date amends the existing report in place**, keeping every earlier finding id, rather than overwriting it.
- **`adr-signals.py` reads doctrine rows whose rule text carries an escaped pipe (`\|`)** instead of dropping the row.
- **The friction signal reads the forge log under every runtime's local skills directory** — `.claude/skills`, `.agents/skills`, `.opencode/skills` and `.opencode/skill`.
- **A future-dated review report is refused.** `generate-reviews-index.py` refuses a date after `--today` (default: the system date), and the night gardener's review-age check applies the same filter, so one file can no longer suppress the cadence reminder indefinitely.

## [3.8.0] — 2026-09-04

### Changed

- **Async text and image councils use GPT-6 Astra as their OpenAI judge**, replacing Sol through OpenRouter. The synchronous council keeps its Terra seat.
- **Council Fable judges use Fable 5.1**, with effort settings preserved; other callers of the shared Anthropic roles also receive Fable 5.1.
- **Codex apex roles (commander, reviewer) use GPT-6 Astra with high effort.** Codex flagship and standard roles keep Sol and Terra.

## [3.7.1] — 2026-09-02

### Fixed

- **The plugin's scripts declare their real Python floor, 3.11.** Fifty-two scripts previously declared `>=3.10`, but the Python arch pack uses `tomllib` (stdlib from 3.11), so a 3.10 run failed on the environment rather than on the code. The PEP 723 headers, the user guide and the schema example now say 3.11.
- **The README states the Python floor and the `uv run` test invocation**, which resolves the tree-sitter grammar packages a bare `pip install` environment lacks.

## [3.7.0] — 2026-09-02

### Added

- **The runtime-compatibility block every skill carries is now derived from one canonical source**, with a regenerator and a `--dry-run` drift gate, instead of being hand-copied into 55 skill files.

### Changed

- **Breaking: the OpenCode agent projection emits the V2 permission schema exclusively.** The singular `permission:` map becomes an ordered `permissions` array of `{action, resource, effect}` rules under last-match-wins. Two actions are renamed: `bash` → `shell`, `task` → `subagent`. The install target moves from `.opencode/agent/` to `.opencode/agents/`. `install-opencode-agents` gains `--migrate-legacy-agent-dir` to move a populated legacy directory (refusing on a name collision unless `--force`), and runs a V2 preflight that refuses when no `opencode2` binary is found. A V1 runner reading the new projection silently drops every deny rule — an accepted residual risk.
- **The commander can dispatch the wayfinder** to size up a large, uncertain or external source before another agent spends context on it.
- **`dev-lead` routes to GLM 5.3 on OpenCode** (`openrouter/z-ai/glm-5.3`); its Claude and Codex seats are unchanged.

### Fixed

- **`web-to-markdown` passes a `text/markdown` or `text/plain` response through unchanged**, with the title taken from its first heading, instead of collapsing it to one line through the HTML converter.

## [3.6.0] — 2026-09-02

### Added

- **A decision is now cited as `rule:<slug>`**, the slug half of the governs handle that carries the rule, identically in code comments, prose, promptbook prompts and journal refs. The citation linter gains a default scope; an empty scope, an unknown slug, or a retired slug (naming the live rules that displaced it) fails the gate.

### Fixed

- **The archive-tier ADR readers in the summaries projection refuse a symlink** instead of following it out of the tree.
- **The `srde` skill's batch example builds `DissentPoint` objects**, as `attempt_batch_resolution` requires.
- **The plugin's own README is enrolled in the documentation count gate** and now says 59 skills, matching disk.

## [3.5.0] — 2026-08-31

### Added

- **Batch ratification for observations: `survey-sheet` and `survey-signoff`.** `survey-sheet` scaffolds one `SVY-NNNN` review sheet from the candidate state file; `survey-signoff` is the single human sign-off that publishes it under one digest-bound receipt, equivalent to N individual ratifications. Both carry `disable-model-invocation`. `audit-docs` gains four `CHK-OBS-SURVEY-*` rules.
- **The `fix-directly` skill — the rung below the three cycle tiers.** "Just fix it" now routes to a named contract: a failing test first, the smallest green change, the suite and drift gates, one commit, one `log-work` entry. A five-question sizing test decides between it and `patch-cycle` / `iterate` / `dev-cycle`.

### Changed

- **`cleanup-campsite` retires `CLN-ADR-1`**, which enforced a convention the project never kept; 18 rules remain.
- **The `iterate` and `patch` verify templates carry a reproduction budget**: a failing test is a complete reproduction, a class earns its own reproduction only at a second independent instance, and a security label must not widen the fix. `whiteboarding` gains a sizing step.

### Fixed

- **Three survey sign-off defects**: `assert_signable` now runs on every publish path; the index retire loop splits on unescaped pipes only; `CHK-OBS-BIJECTION` reads each row's id column rather than grepping the whole page.
- **`derive-arch.py --dry-run` no longer flags `arch/_recovered/state.yml` as a stale artifact**; the `_recovered/` directory is excluded from the sweep.

## [3.4.0] — 2026-08-30

### Changed

- **The OpenCode commander runs Qwen3.8 Max (1M context) instead of Kimi K3**, which could not sustain the orchestration role. Every other role's OpenCode model is unchanged.
- **Each arch stack-pack probe declares its own input class against a committed roster.** The doctrine index's `implemented` column is renamed `basis`, and a `governs` entry's `retires` sub-field displaces a rule while keeping its record.
- **Breaking: a `governs` entry's sub-field set is now closed.** `summarize-adrs.py` and `compile-doctrine.py` refuse an unrecognized sub-field; a tree carrying any other annotation key fails both regenerators on upgrade.

### Fixed

- **A book's `current_run` pointer survives a run's completion**, so `archive-promptbook` can read the pointer its precondition requires. `current_run` now nulls only at archival.

## [3.3.0] — 2026-08-30

### Added

- **A repository that has never authored an ADR can build a doctrine from what its code already does.** The `observations` concern adds `OBS-NNNN` records, each evidenced by a `path:line-range` and ratified by a human, projected into the summaries rule table and doctrine index beside the ADRs.

### Changed

- **`derive-arch` records a per-concern verdict instead of grading its own confidence.** A concern is `populated` or `stubbed`, with one reason from a closed set. The new `arch.require` list in `manifest.yml` fails the derive when a required concern is not populated.
- **The arch extractors read committed artifacts and real parsers.** Python routers parse through the AST; Ruby reads a committed `rails routes` dump; Ruby, Node and Elixir source parses through tree-sitter grammars. Node routes compose `app.use` mount prefixes, and Elixir routes parse the parenthesized form.

### Removed

- **The `arch_confidence_threshold` key in `.bionic.yml` is retired.** A tree that still sets it loads clean.

## [3.2.2] — 2026-08-29

### Fixed

- **The agent-catalog strict-YAML test skips cleanly when PyYAML is absent** instead of reporting a spurious failure.

## [3.2.1] — 2026-08-29

### Fixed

- **`transition-adr` and `archive-promptbook` no longer carry `disable-model-invocation`.** The field had been mis-applied to them, blocking `dev-cycle`, `iterate` and `patch` runs from accepting an ADR or archiving a book without a human keystroke. The four true human gates (`reconcile-signoff`, `backfill-signoff`, `escalate-arch-runtime`, `transition-invariant`) keep it.

## [3.2.0] — 2026-08-28

### Changed

- **Corrected the OpenCode `permission.task` projection.** A restricted `Agent(role)` grant now projects as a deny-first per-role glob object instead of a coarse boolean; the widened-grant report and its sign-off are retired.
- **Documented the fields OpenCode ignores.** `$adr`/`$book` argument placeholders bind only in Claude Code, and a new `OPENCODE_GUIDE.md` section lists the invocation-control fields OpenCode does not honor.
- **`fable` is a routable agent `model:` value again**; the table that disabled it is removed.

### Fixed

- **`forge-skill`'s frontmatter guidance matches catalog schema 3** and no longer names the removed `owner`/`version`/`status` keys.

## [3.1.0] — 2026-08-28

### Added

- **`compile-doctrine`** regenerates the doctrine directory from the summaries projection, reconciled against ratified invariants and the human-signed reconciliation ledger; `--dry-run` is the drift check. It stops and recommends `summarize-adrs.py` first when the summaries have drifted.
- **`check-drift`** runs every enrolled regenerator's `--dry-run` in one pass and reports one table of gate, verdict (clean / drift / broken / crash / refusal), drifted paths and the fixing regenerator. It regenerates nothing. Wired into `audit-docs` as `CHK-DRIFT-1`.
- **`reconcile-signoff`** is the single human write path for one doctrine reconciliation: it renders the invariant and rule text, takes the verdict (compatible / reconciled / collision) and rationale from the user, and upserts a digest-bound record. It carries `disable-model-invocation`; `audit-docs` `CHK-DOCTRINE-1` counts pending pairings.
- **A signed gate for OpenCode `Agent(role)` grants that cannot be enforced**, naming each affected role with rationale, signer and date.

### Changed

- **Catalog schema 3 — invocation-control frontmatter.** SKILL.md admits the Claude Code invocation-control keys (`disable-model-invocation`, `user-invocable`, `context`, `agent`, `model`, `effort`, `background`, `arguments`, `disallowed-tools`); agents admit `maxTurns`, `effort`, `skills`, `memory`, `isolation` and `disallowedTools`, each projected to Codex and OpenCode by a faithful-or-drop table. The dispatch tool `Task` is renamed `Agent` (with the restricted `Agent(role)` form). **Breaking:** the constant metadata keys `owner`, `version` and `status` are removed from every skill and agent — a lingering one is a validation error. The skill routing table is now generated from skill frontmatter. `plugin.json` `schema_version` goes `"2"` → `"3"`.

### Fixed

- **A block-style `disallowedTools`/`skills` agent frontmatter list fails validation** instead of silently mis-projecting (`bash` rendered `allow` instead of `deny`).

### Removed

- **The `inject-knowledge` skill.** Its bundled knowledge layer shipped only a README and nothing referenced it. Git history is the recovery path.

## [3.0.0] — 2026-08-28

### Added

- **The doctrine layer — a third ADR-decision tier, compiled and reconciled.** `adrs/doctrine/` projects each governs domain's live rule, disposition and implemented-vs-on-paper state from the summaries projection, reconciled against ratified invariants through a human-signed ledger, with a regenerator and drift gate. Reads route doctrine → summaries → ADR body, with the ADR body winning on disagreement.

### Changed

- **The `qwen-max` OpenCode alias points to `openrouter/qwen/qwen3.8-2.4t-a95b`**; the historian, librarian and wayfinder resolve through it.
- **The architect's OpenCode model is the flagship default `kimi-latest`** (`openrouter/moonshotai/kimi-k3`); its per-agent override was dropped.

## [2.2.0] — 2026-08-28

### Added

- **Governs backfill machinery.** An ADR numbered below `adr.governs_from` can join the summaries projection through an anchored, digest-bound, reviewed, at-most-once backfill: the `anchor` sub-field, the `backfill-reviews.yml` receipts manifest, the `backfill-signoff` owner-gate skill and the `backfill` log op.

### Changed

- **The "Silver" ADR-summary layer is renamed "summaries".** `adrs/silver/` → `adrs/summaries/`, and `generate-silver.py` → `summarize-adrs.py`. Forward-only: frozen history keeps "Silver".

## [2.1.0] — 2026-08-26

### Added

- **ADR frontmatter gains a `governs` block** (`domain`, `rule`, `scope`, `handle`, `provenance`), cohort-bound by the new `adr.governs_from` manifest field. `generate-silver.py` projects every block into a rule table, a resolver and an ADR↔run implementation map, behind a `--dry-run` drift gate, alongside a coverage gate and a reference linter.

### Changed

- **Model calls crux performs route through OpenRouter as a single gateway** under one `OPENROUTER_API_KEY`. The direct Anthropic/OpenAI/Google SDKs and the Fireworks provider are retired.

## [2.0.1] — 2026-08-25

### Fixed

- **Release tooling in the development repository runs under `uv run`** so its gates use the pinned interpreter regardless of the operator's `python3`; the development repository pins Python 3.13. No plugin behavior changed. *(private-history reference)*

## [2.0.0] — 2026-08-25

### Added

- **A deterministic per-derive coverage report** at `arch/_meta/coverage.json` records, for each spine concern, whether it populated or fell back to a stub, and why. Byte-stable, and covered by the arch drift gate.
- **Confidence-graded arch extraction.** Each concern self-assesses high, medium, low or none; at or below the new `arch_confidence_threshold` config key (default `low`) a stubbed concern offers an attended runtime-escalation session. The unattended pipeline stays static and deterministic.
- **A model catalog.** `models.yml` (`schema_version 2`) decides which model every agent runs on: a provider allowlist, an alias table, the ten-agent roster keyed to three levels (`apex`, `flagship`, `standard`), the level table, and Claude alias pins. Every consumer resolves through one shared reader that refuses a malformed catalog. `validate-catalog.py` gains rules V0–V9 over it.
- **Python import-only runtime arch introspection behind a two-factor consent gate.** The new `escalate-arch-runtime` skill runs a FastAPI, Flask or Django app's import-time code in an isolated subprocess to recover its route table and ORM schema, filed as an advisory. It executes only with `CRUX_ARCH_ALLOW_RUNTIME=1` and a per-execution permission event.
- **A third cycle tier, `patch`.** `patch-cycle` authors a five-phase book that declares the paths it may touch; `archive-promptbook` compares the run's actual git changes against that declaration and refuses to archive a run that reached outside it.
- **An ADR body content rule.** An ADR body states requirements and postconditions within a 120-line budget over its narrative sections. `audit-docs` gains `CHK-ADR-SPEC`, inert until a tree sets `adr.spec_rule_from`.
- **Two arch spine files are thin projections.** `arch/api-surface.md` and `arch/decision-index.md` are projected from the skill catalog and ADR index; a stale input is refused at exit 2 naming the regenerator to run. `query-docs` gains an architecture route, and all ten roles name `arch/` first for questions about the project's own shape.

### Changed

- **Council rounds are routed by blocking findings.** A round past the first fires only on a finding naming a failing check against a repository artifact; round 3 is one adjudicator, within the three-round bound. SRDE stays wired to the verify path.
- **The OpenCode and Codex projections resolve models through the catalog** instead of carrying their own model tables.
- **In the catalog, the file extension declares provenance:** `.json` is regenerated, `.yml` is hand-authored and never written by a generator.

### Fixed

- **The arch drift gate no longer fires on edits that leave the spine byte-identical.** `--dry-run` no longer compares the per-source hash map, and `derive-arch.py` declares PyYAML so one source tree produces one spine hash.
- **The runtime introspection executor is genuinely stdlib-only** and no longer crashes with `ModuleNotFoundError: httpx` in a shipped install, nor writes `__pycache__` into the installed plugin.
- **The curated decision-index mode is reachable** via the new `arch_decision_index_mode` config key; the default stays `complete`.

### Removed

- **Breaking: per-advance run bookkeeping and three promptbook surfaces.** `run-promptbook` no longer writes a log op or regenerates the promptbooks index per advance; the `promptbook` op is written at authoring, run start and archive only. The `cycle-status` skill is deleted and its triggers move to `visualize-run-progress`. The per-prompt `blocked_confirmed` flag is retired; archive eligibility is a run-level property. `author-promptbook --fork-from` is deleted — abandon the run and author a successor book instead.
- **`catalog/bundles.json`** is replaced by `catalog/bundles.yml`. The catalog ships inside the plugin, so no downstream repo owes a migration.

## [1.14.0] — 2026-08-18

### Added

- **An Elixir/Phoenix arch stack pack**, completing the batteries-included set (Python, Ruby, Node, Elixir). Interface surface from a committed OpenAPI spec or a static parse of `router.ex` (including `resources`, `scope` prefixes and LiveView routes); data model from Ecto schemas; module graph from `alias`/`import`/`use` and remote calls. The app is never booted.
- **A Node.js arch stack pack.** Routes from a committed OpenAPI spec or a static scan of Express, Fastify and NestJS; data model from Prisma's `schema.prisma`, TypeORM `@Entity` classes or Sequelize models; module graph from TS/JS imports with `tsconfig` `@/*` alias resolution.
- **A Ruby arch stack pack.** Routes from `openapi.json` or a static parse of `config/routes.rb`; data model from `db/schema.rb`; module graph over the Zeitwerk autoload roots. All parsing is static and stdlib-only.

## [1.13.0] — 2026-08-17

### Added

- **Pluggable arch stack packs, with a Python pack.** `derive-arch` detects the project's stack and resolves each spine file through a per-repo override, then the detected pack, then a stub. The Python pack derives the interface surface from `openapi.json`, the data model from SQLAlchemy models plus Alembic history, and the module graph from the project's own package. Two `.bionic.yml` keys configure it: `arch_stack` pins the pack; `arch_extractors` registers an override that runs only under `CRUX_ARCH_ALLOW_OVERRIDES=1`.

## [1.12.0] — 2026-08-17

### Added

- **`install-opencode-agents` skill.** Say "install the Crux agents in OpenCode" to write the ten projected roles into a project's `.opencode/agent/`. It refuses to overwrite a locally modified role without `--force`, refuses a symlinked crux-managed entry, refuses a target outside the repo root, and never touches a project's own agent files. Skill count 49 → 50.
- **A `.gitignore` in the public repository** so the OpenCode setup's generated `opencode/` tree is not permanent `git status` noise.

### Changed

- **The skill runtime-compatibility block names OpenCode** alongside Claude Code and Codex: plugin root derived from the selected `SKILL.md`, `.opencode/skill` for project-local skills, lowercase tool labels with `edit` covering `Edit` and `Write`, and `install-opencode-agents`.
- **OpenCode setup documents the singular `~/.config/opencode/agent/`**, noting OpenCode also reads the plural form and that populating both leaves you guessing which is live.

### Fixed

- **`install-codex-agents` and both agent generators refuse a non-directory output path with a structured error (exit 2)** instead of a traceback.
- **`generate-opencode-agents.py` no longer writes through a symlinked agent file.**
- **`crux_wayfinder` is listed in the agent roster in every skill**, and `install-codex-agents` now says ten roles.
- **OpenCode setup gains an upgrade step**: regenerate the agent projection after every pull, with troubleshooting rows for stale projections and dangling symlinks. Stale paths and skill counts in `OPENCODE_GUIDE.md` are corrected.

## [1.11.0] — 2026-08-16

### Added

- **`derive-arch` skill.** Say "build the arch" or "regenerate the architecture" to regenerate the derived current-state map (data model, interface surface, module graph, decision index, plus an overview) from the project's own sources. `arch` is now documented as the primary current-state discovery surface, with a dedicated `arch` log op. Skill count 48 → 49.
- **`audit-docs` checks the arch spine.** `CHK-ARCH-1` regenerates a drifted spine in place as a DRIFT-tier auto-fix; `CHK-ARCH-2` recognizes arch enablement.

### Changed

- **`init-docs` enables the `arch` concern by default for new repositories**, scaffolding `arch/` with a placeholder; the first "build the arch" or `audit-docs` run derives the spine. Existing trees are unchanged — add `arch` to `concerns_enabled` to opt in.

### Fixed

- **The `audit-docs` skill's arch section cites its schema section** rather than an inline ADR number.

## [1.10.2] — 2026-08-14

### Fixed

- **Stale skill counts in the README and user guide** (46 → 48), now held by a documentation count gate so an added skill either updates the prose or fails the release.

## [1.10.1] — 2026-08-14

### Fixed

- **The arch `module-graph.md` was incomplete.** The extractor now resolves relative imports, uses full-module node ids and lists isolated modules.
- **A routine `next_number` bump in `manifest.yml` no longer drifts the arch spine.**
- **README and skill documentation drift**: skill count 46 → 48, agent count nine → ten, three missing skill rows, and `prose-review` now says seven writing rules.

## [1.10.0] — 2026-08-14

### Added

- **Decision recovery.** `recover-decisions` mines load-bearing decisions latent in code into `observed` candidates with `path:line-range` evidence; `transition-decision` ratifies a candidate into a Proposed ADR or rejects/defers it; `derive-arch.py` gains `decision_index_mode: complete|curated`. New `recover` log op.
- **ADR archival cold tier.** Superseded and Deprecated ADRs move to `adrs/archive/`; `transition-adr` moves them, `propose-adr` never reissues an archived id, and `generate-adr-index.py` regenerates `adrs/index.md` from both tiers. `audit-docs` gains `CHK-ADR-ARCHIVE`.
- **Writing rule #7 — footnote-only ADR citation.** In human-facing prose, reference an ADR by a footnote, never an inline number. A new check flags inline references with a ratchet baseline.

## [1.9.0] — 2026-08-14

### Added

- **The arch concern.** `<docs_dir>/arch/` is the project's derived architecture: a deterministic spine (`data-model`, `api-surface`, `module-graph`, `decision-index`) plus a synthesized `overview.md`, regenerated by `derive-arch.py`, with `--dry-run` as the drift gate. Other stacks degrade to an empty-but-valid file.

## [1.8.2] — 2026-08-02

### Changed

- **`init-docs` bootstraps the unified `bionic/` tree** at the resolved `docs_dir`, with the invariants concern as one folder and `.bionic.yml` written with merge-never-clobber semantics. The guard refuses symlinked trees and a second tree at the other well-known location; rollback removes only paths written this run.
- **Templates and schema docs describe the schema 5 layout**, including `<docs_dir>`-relative paths and bare-directory discovery.

### Fixed

- **Fresh installs bootstrapped a `docs/` tree with schema 4 prose instead of `bionic/` at schema 5.** The `init-docs` skill prose now matches the shipped templates, and a gate pins them together.
- **`docs_dir` in `.bionic.yml` rejects shell metacharacters.** Each segment must match `^[A-Za-z0-9_.][A-Za-z0-9._-]*$`, so a value like `$(id)` can no longer execute when a skill composes a shell command.

## [1.8.1] — 2026-07-31

### Fixed

- **`migrate-tree.py` migrates a relocated tree.** It now resolves the configured `docs_dir` instead of assuming `<root>/docs`, and a relocated tree stays where its owner put it — only the invariants suite merges in. `--docs-dir` is the escape hatch for a layout no config declares.
- **The 4→5 upgrade path is documented** in `audit-docs --migrate`, with both forms, exit codes and fail-closed behaviors.
- **Every path that reads, writes or removes is containment-checked**; `../elsewhere`, absolute paths and escaping symlinks are refused.
- **The schema template no longer ships literal `<tree>` placeholders**, and `install-docs-skills` and `audit-docs` agree on the supported schema version (`"5"`) by reading it from the installed manifest.

## [1.8.0] — 2026-07-30

### Added

- **Breaking: the tree lives at `bionic/`, `schema_version` `"4"` → `"5"`.** The seven concerns sit directly under `bionic/`, and the invariants concern is one folder. `init-docs` always writes `.bionic.yml` naming the tree.
- **Bare-directory discovery.** A tree is recognized by a manifest carrying `schema_version` and `concerns_enabled`. An existing `docs/` tree keeps working with zero config when it is the only one; two valid trees refuse unless a migration marker names one.
- **`migrate-tree.py`, the 4→5 rung.** A staged, resumable merge with config merged, never overwritten.
- **A schema gate.** Commands that read the tree refuse an unmigrated one with exit 2.
- **Six writing rules, and `prose-review` (the 46th skill) to check them**: one name per thing, no hedge without a cause, verbs stay verbs, adjectives must be checkable, one idea per sentence, single-word verbs. `prose-review` reports only findings that carry a rewrite. The rules are projected byte-equivalently from one canonical text into `AGENTS.md`, the schema and the skill by `generate-writing-rules.py`.

### Changed

- **`prose-review` runs at three points**: the release preflight (advisory), the `dev-cycle` / `iterate` prep prompt, and `tend-garden` before it writes the morning note.
- **The README's catalog-history sentence was rewritten** from 104 words to 25; per-release detail lives in this file.

## [1.7.0] — 2026-07-24

### Added

- **Opus 5 refusal handling in the council seats.** A safety refusal (`stop_reason: "refusal"`) now surfaces as the new `refused` redaction label instead of a JSON-parse error or `unknown`.
- **Spawn caps on `commander` and `dev-lead`**: one agent per genuinely independent unit, never for work finishable in ~3 tool calls, with a carve-out for the architectural gates the cap must not throttle.
- **Scope-discipline guidance on `dev-lead`.**

### Changed

- **Model swap: `claude-opus-4-8` → `claude-opus-5`** across the router config and OpenCode agent generator; `claude-opus-4-8` is removed from the router registry. Router config `1.4.0` → `1.5.0`.
- **Agent and cycle-skill prose re-tuned for Opus 5's defaults**; every cross-agent review gate is preserved.

### Fixed

- **`dev-cycle` / `iterate` checklists no longer overstate validator coverage**: the cycle-coverage pass checks module size and contiguity, not prompt content, and `cycle_grandfathered: true` short-circuits it.

## [1.6.0] — 2026-07-23

### Added

- **`generate-lineage.py`** — a deterministic regenerator for `adrs/lineage.md`, with a drift gate.
- **INV-0001 — the first ratified invariant**: council aggregation excludes errored seats.
- **`generate-index-rollup.py` and `generate-readme-footer.py`** regenerate the ADR rollup in `index.md` and the README version footer, each with `--dry-run`.
- **`advance-run.py`** — a safe-advance script for run snapshots that round-trips every top-level key, so run-level `notes` / `pr_draft` / `summary` survive each advance.

### Changed

- **Council deliberation is hardened against a single errored provider seat.** Aggregation runs over responding seats only, requires a quorum of ≥ 2 (`NO_QUORUM` otherwise), surfaces `errored_seats` and a `degraded` flag, caps a degraded verdict at `EXECUTE_WITH_MONITORING`, and counts `APPROVE_WITH_NITS` as approval.
- **Wiki-link resolution is lifecycle-agnostic.** An ADR's `related_research` resolves to any research page; a journal→promptbook link resolves on its `PB-NNNN` id across `active/` or `archive/`.
- **Whiteboarding sessions carry into the brief body** via `propose-brief --from-inbox <session-path>`, passed by `process-inbox`.
- **Every derived artifact now requires a vendored regenerator and a drift gate.**
- **`CLN-TMPL-1` guards section content, not just section presence.**
- **The `invariant` log op is a first-class member of the op enum.**

### Fixed

- **Provider exception text can no longer leak through council error paths.** Error output is built only from a fixed label set plus a range-validated status code, so no substring of a provider exception reaches a persisted deliberation surface.
- A single errored council seat no longer poisons `consensus_confidence`; two wiki-link dangle classes are retired; the `whiteboarding → process-inbox → propose-brief` pipeline no longer orphans the session body.

## [1.5.0] — 2026-07-18

### Added

- **The invariants concern — the seventh concern.** Ratified, executable statements of what must be true: a human-readable ledger plus an executable check suite under `bionic/invariants/`. `recover-invariants` mines code for `observed` candidates and never self-ratifies; `transition-invariant` is the human gate. `audit-docs` gains five `CHK-INV` rules. `manifest.yml` `schema_version` `"3"` → `"4"`.
- **`init-docs` enables the invariants concern by default for new repositories.** Existing trees adopt it via `audit-docs --migrate` (a new 3→4 rung).
- **`.bionic.yml` — the repo-root layout source of truth** (`config_version`, `docs_dir`, `artifact_prefix`), superseding the legacy `.crux` file with precedence `.bionic.yml` > `.crux` > convention. Resolved via `bionic-config.py`; `crux-config.py` remains as a delegator.

### Changed

- **Forged-skill promotion is judgment-driven.** The former mechanical floor (≥2 `effective` evaluations on ≥2 dates) is now supporting evidence the owner weighs; `retrospective`'s promotion scan becomes an evidence report.
- **`audit-docs` supports `schema_version` `"4"`** and gains the `3→4` migration rung.
- **Concern framing moved from six to seven** across the README, user guide and schema.

## [1.4.2] — 2026-07-13

### Fixed

- **Release commits in the development repository are authored by a sanctioned machine identity** (`crux release bot`) rather than a legacy noreply address GitHub attributes to an unrelated account. Release tooling only — no plugin, skill or docs behavior change. *(private-history reference)*

## [1.4.1] — 2026-07-10

### Added

- **Public manual OpenCode setup instructions** in the README and a refreshed `OPENCODE_GUIDE.md`: clone to a stable path, `uv run generate-opencode-agents.py`, merge the skills path into `opencode.json`, symlink all ten generated agents, restart the host, and verify with `opencode debug skill` / `opencode agent list`. There is no native OpenCode marketplace package.

### Fixed

- **README version footer and the 43-skill table corrected.** `OPENCODE_GUIDE.md` counts corrected (43 skills, ten agents), and the agent symlink step made glob-based.

## [1.4.0] — 2026-07-10

### Added

- **Codex is a supported distribution target.** `.codex/agents/crux-*.toml` is generated from the same agent source as the OpenCode projection by `generate-codex-agents.py`, never hand-edited. Install via `codex plugin marketplace add` followed by `codex plugin add crux@crux` (the marketplace source has since moved to `bionic-coding/crux`). Target repos get the ten agents via the no-clobber `install-codex-agents` skill, which refuses to overwrite or remove a differing role without `--force`. Generated model mapping: seven roles → `gpt-5.6-sol`, three → `gpt-5.6-terra`. A reachable leaf-symlink write-through in the shared generator/installer write path was closed.
- **The OpenCode agent projection gains generator test coverage** for transform rules, hard-error paths and dry-run semantics.

### Changed

- **LLM router model refresh** (`1.2.0` → `1.3.0`). The OpenAI lineup consolidates into the three effort-controlled GPT-5.6 SKUs — Sol (flagship, alias `gpt-5.6`), Terra (workhorse), Luna (cost) — all Responses-API-only; `gpt-image-1` → `gpt-image-2`; the `openai_reasoning`/`openai_reasoning_fast` roles retire. `claude-sonnet-4-6` → `claude-sonnet-5` (which rejects the temperature parameter). Pricing corrected against official sources. `fast_council`'s arbiter is pinned to low effort via `gpt-5.6-sol-low`.

### Fixed

- **OpenAI `/v1/responses` is first-class in the caller and async council.** Both async OpenAI seats route by the model's `openai_endpoint` through `responses.create`, and the caller forwards `effort` → `reasoning.effort`, making the `gpt-5.6-sol-low` pin live.
- **Seven Codex-integration corrections**: `CRUX_PLUGIN_ROOT` is described correctly everywhere as a portable bridge (Claude Code = `CLAUDE_PLUGIN_ROOT`; Codex = derived from the selected `SKILL.md`; source checkout = `crux/`); strict-YAML tests skip without PyYAML; dated provenance comments anchor external Codex schema assumptions. A symlinked-directory bypass in the development repository's release staging was closed. *(private-history reference)*

## [1.3.3] — 2026-07-10

### Added

- **`CLN-TMPL-1` cleanup-campsite rule** checks operational-schema ↔ distributed-template clause parity, inert when no template twins are present. New `cleanup-campsite --only <RULE-ID>` selector (CSV-capable).
- **`dev-cycle` and `iterate` record forge-log `used`/`evaluated` entries for forged skills they invoke**, so cycle-used forged skills accrue evidence toward promotion.
- **`scout` — the 10th agent**, a read-only reconnaissance subagent that reads large or external data in an isolated context, judges fitness for a stated purpose, and returns a verdict plus digest. Tool grant `Read, Grep, Glob, WebFetch, WebSearch`, with an egress guardrail. Renamed `wayfinder` below.
- **`run-adr-council` graduates into the plugin** (catalog 41 → 42, `crux-verification` bundle) — the ADR council runner, with the council prompt written as a data file so no shell string ever holds ADR prose.
- **The forged-skill promotion path.** Forged skills are usable in the session that forged them; every session writes a session-end `evaluated` forge-log entry; `retrospective` nominates skills that clear a floor; graduation into the plugin is a `dev-cycle`. `CLN-FG-2` backstops the evaluation discipline. Project-local skills cannot PR into the public repo — share via issue.
- **The night-gardener — the 9th agent — and her two skills.** A standing overnight co-CTO who reviews recent work and writes a morning note under `garden/`. She moves only after you have moved; tending (`tending.md`) — dismiss or snooze — is the only control surface, with dismissals decaying over 90 days. New skills `tend-garden` and `read-news` (Perplexity → WebSearch → skip fallback; `PERPLEXITY_API_KEY` optional via `~/.crux/`). New `garden` log op. Catalog 39 → 41 skills, 8 → 9 agents. The nightly routine is owner-installed.
- **`retrospective`** mines the log, journal, archived promptbooks and forge log since the last marker and distills 0–2 evidence-cited skill proposals, each council-gated and built via `forge-skill`. New `cleanup-campsite` rule `CLN-RETRO-1` (`retro_due_runs`, default 5). Catalog 38 → 39.
- **`forge-skill` — the capability-gap loop.** When a gap surfaces mid-task, the model diagnoses it, researches, authors or revises a project-local skill under `.claude/skills/<name>/`, and self-tests on the live problem; every act lands in the append-only forge log. Detection is embedded in every agent definition. New `cleanup-campsite` rule `CLN-FG-1` (`forged_skill_stale_days`, default 30).
- **PEP 723 + `uv run "${CLAUDE_PLUGIN_ROOT}/..."` runtime contract.** All 18 shipped runnable scripts carry inline-metadata blocks and are self-describing under `uv run`.

### Changed

- **The reconnaissance agent is renamed `scout` → `wayfinder`**, one name across Claude Code and OpenCode, resolving the collision with OpenCode's built-in `scout`. Capability, tool grant and model are unchanged.
- **The `architect` agent holds `Bash`** so it can run the multi-model council driver its remit requires.
- **The `dev-cycle` quality gate mandates the full test suite** whenever a change touches a shared or enumerated surface.
- **LLM router curated to the latest-generation lineup** (`1.2.0` → `1.3.0`): older models removed, `gpt-5.5-pro` and `gemini-3.5-flash` added, pricing corrected. `claude-fable-5` is retained but `enabled: false`; the two Fable-pinned OpenCode agents remap to `claude-opus-4-8`. (Superseded by the 1.4.0 refresh.)
- **Split-repo publication model.** The public repository is a generated artifact receiving one squash commit and tag per release; releases attach no zip assets, since the marketplace model makes them redundant.
- **The "Crux Lite" edition framing is gone from every live surface.** Crux is not the lite version of anything.
- **Marketplace-only install story**: `/plugin marketplace add <marketplace>` + `/plugin install crux@crux` (the marketplace source is now `bionic-coding/crux`).
- **`${PLUGIN_DIR}` → `${CLAUDE_PLUGIN_ROOT}`** as the canonical plugin-root variable.
- **Spawner runtime directory `.crux` → `.crux-runtime`**, with refusal on a foreign target and symlink/containment guards.
- **Provenance fields (`origin`/`origin_ref`/`origin_date`) removed** from the SKILL.md frontmatter contract and catalog; internal ADR references removed from distributed surfaces; git softened to enhancement-not-requirement.
- **Distributed `CLAUDE.md.tmpl` rebuilt** to the current contracts.

### Fixed

- **The public-release content scan runs inside every cycle template**, so a banned internal-reference leak fails in-cycle rather than at release time.
- **The bare-`python3` test lane reports clean skips** without `uv` instead of errors, and `check-no-stale-skill-names.py` no longer false-positives on a stale name embedded in a longer path token. README agent count corrected to 9.
- **The test suite is green after the router curation**; `gpt-5.5-pro` now carries `openai_endpoint: "responses"`.

### Removed

- **`spin` (the Python RSI engine) is decommissioned**, succeeded by `forge-skill`; its modules, skill and tests are deleted, and the eager import is gone from the package init. Catalog stays at 38 skills.
- **`crux/install.sh`** — the curl|bash install path is gone; the marketplace flow is the only install path.

## [0.9.0] — 2026-06-10

### Added

- **Honest YAML-capability failures with automatic uv repair.** `validate-promptbook.py`, `migrate-promptbooks.py` and `visualize-run-progress.py` require a real YAML parser: without PyYAML they re-exec under `uv run --no-project --with pyyaml>=6.0` (opt out with `CRUX_NO_UV_REEXEC=1`) or exit 2 with a remediation message, never reporting an environment problem as a document verdict.
- **Repo-root `.crux` configuration file**: `docs_dir` relocates the docs tree and `artifact_prefix` brands promptbook/ADR ids (e.g. `CRX-PB-0040`). Skills read it through the `crux-config.py` CLI; `audit-docs` gains `CHK-CFG-1..4`. Zero-config repos are unaffected.
- **`transition-brief` and `cycle-status`** (catalog 36 → 38). `transition-brief` closes the briefs lifecycle (`draft → published | abandoned`), mutating only frontmatter and writing a `brief` log op. `cycle-status` is a read-only "where am I / what's next" view over a run.
- **`iterate` skill** (catalog 35 → 36) — a cycle for non-architectural reactive work with a verify module (`cycle_kind: verify`) in place of the ADR module; minimum 13 prompts. Routing: architectural → `dev-cycle`; reactive fix → `iterate`; trivial → `author-promptbook`.
- **Machine-enforced cycle-coverage validation.** The promptbook schema gains a `cycle_kind` (`adr`|`verify`) discriminator and `cycle_grandfathered`/`grandfather_reason`; `validate-promptbook.py` enforces the `4N+4M+3K+2` formula and per-module prompt counts.

### Changed

- **Structural skill/agent improvements across the catalog**: `## When NOT to Use` on five substrate skills, sharpened routing descriptions, validation visibly before side effects in ~18 skills (`verify-code-docs --no-log`, `log-work` STOP-on-invalid `--log-op`, `serve-llm` CORS callout), and hardened agent disciplines.
- **Default Claude Opus model `claude-opus-4-7` → `claude-opus-4-8`** across the router config and skill examples.
- **`USER_GUIDE.md` expanded** with an at-a-glance overview, an agent-layer capability table, a tools & scripts section, and a rewritten planning section covering `dev-cycle` vs `iterate` vs `author-promptbook`.

### Fixed

- **`council` and the router-dependent skills are runnable by the docs**: the canonical `PYTHONPATH=crux/scripts uv run --extra openai python …` invocation is documented, and result-API examples use the real `consensus` / `consensus_confidence` / `votes[].dissenting_points` fields.
- **Seven skill-doc corrections**, including `council`, `call-llm` and `serve-llm` declaring `ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY` in `requires_env`.
- **README and user guide refreshed** (skill count 33 → 35, agent-layer sections added).
- **`migrate-promptbooks` grandfathers legacy cycle books** so they pass the cycle-coverage pass.
- **`whiteboarding` added to the `crux-docs` bundle.**

## [0.7.0] — 2026-06-02

### Added

- **Bundled agent layer** — eight role-based agents (commander, brainstormer, architect, dev-lead, developer, reviewer, historian, librarian) with tool-allowlist guardrails, and a `whiteboarding` skill. Agents are catalogued in a regenerated `catalog/agents.json` and an `agents:` array in `plugin.json`, with craft disciplines embedded so the `superpowers` plugin can be uninstalled.

### Changed

- **`validate-catalog.py` regenerates `catalog/agents.json`** alongside `skills.json`.
- **Briefs may be whiteboarding-authored**, arriving via the inbox.

## [0.6.0] — 2026-06-01

### Added

- **`visualize-run-progress` skill** (catalog 33 → 34) — a read-only renderer for run snapshots: a colored terminal progress bar plus an opt-in byte-stable Markdown artifact `run-RUN-NNN-progress.md`. Control bytes are stripped from author-controlled fields.
- **`migrate-promptbooks` skill** (catalog 32 → 33) — migrates legacy `.md` promptbooks and run snapshots to structured YAML, recomputes each `book_content_hash`, and preserves every original under `promptbooks/legacy/`.

### Changed

- **`audit-docs` gains `CHK-PB-LEGACY`** and excludes `promptbooks/legacy/` from every `CHK-PB-*` walk. `archive-promptbook`'s "extension is permanent" guidance narrows to extension-only. `schema_version` stays `"3"`.

## [0.5.1] — 2026-05-29

### Added

- **Single-source-of-truth schema sections** for the log op enum, ADR frontmatter and run-snapshot per-prompt shape; the skills that hand-copied them now reference them. New `audit-docs` rule `CHK-ADR-1a`.
- **`propose-brief` and `link-adr-graph`** (catalog 29 → 31). `propose-brief` scaffolds a human-authored brief and adds a `brief` op; `link-adr-graph` regenerates `adrs/lineage.md` as a deterministic supersedes/amends graph.
- **`audit-docs` rules `CHK-PB-13` and `CHK-PB-SCHEMA`**, and **`CHK-INBOX-1/2/3` and `CHK-SCHEMA-1`**.
- **`process-inbox` skill and a unified `inbox/`** (catalog 31 → 32) — one drop folder for any raw input, classified then confirmed, and routed to `ingest-research`, `propose-adr`, `propose-brief` or `log-work`; idempotent via an `inbox/_dispatched/` ledger. `audit-docs --migrate` is now implemented.
- **Promptbook and run JSON Schemas with a vendored stdlib validator.** `validate-promptbook.py --kind {promptbook|run}` implements a documented draft-2020-12 subset with a reject-on-load guard for unimplemented keywords, plus `compute_book_hash`.

### Changed

- **Promptbooks and runs are a single structured YAML document (`format_version: "1"`)**, with long-form fields as Markdown block scalars. A run binds to its book by `book_content_hash` over the frozen-plan subset; a mismatch is a `CHK-PB-BIND` drift signal. Legacy `.md` books are still read.
- **`dev-cycle` hardened**: deeper architectural review with auto-escalation to `srde` (or `--deep-review`), a fifth Security council dimension, a multi-threat-class post-dev security review, a tiered dev-practice conformance audit, and explicit run autonomy.
- **Run execution autonomy**: once a run starts against an approved book, the runner advances to completion; only escalation loops, unauthorized irreversible actions, an explicit pause or contradicting new information are legitimate stops.
- **`run-promptbook` `blocked` handling (behavior change)**: `block`/`stuck` marks a prompt `blocked` but keeps the book open; an explicit "abandon" writes `blocked-confirmed: true` for archival.
- **`log-work` gains `--journal` and `--log-op`.** `--silent` now skips prompts only; journaling is controlled by `--journal`; log-only calls write under the caller's own op.
- **Breaking: `manifest.yml` `schema_version` 2 → 3.** The research-local `research/new/` drop folder is retired in favor of `inbox/`. Run `audit-docs --migrate` after upgrading; it creates `inbox/`, relocates in-flight items and rewrites the version.

### Fixed

- **`init-docs` `schema_version` prose** now says `"2"`, matching the template.

### Removed

- **Breaking: four optional skill bundles (18 skills)** — `crux-analysis-excel`, `crux-media-generation`, `crux-document-analysis`, `crux-verification-extended` — narrowing the plugin from 47 skills / 8 bundles to 29 / 4. The removed skills remain available in the pre-prune release history for anyone who wants to fork them. *(private-history reference)*
- **Four dead optional-dependency groups** removed from the development repository's `pyproject.toml`. *(private-history reference)*

## [0.4.1] — 2026-05-27

- No user-facing changes.

## [0.4.0] — 2026-05-27

### Added

- **`promote-changelog.py`** promotes `## [Unreleased]` under a new dated version heading (em-dash preserved) and leaves a fresh empty shell. CLI: `--version`, `--changelog`, `--release-notes-out`, `--dry-run`, `--date`.
- **The aggregate skill zip ships a README** carrying the upload-incompatibility warning; zip bytes are deterministic. *(private-history reference — releases no longer attach zip assets)*
- **`cleanup` skill v0.1.1**: new `CLN-PB-4` rule detects duplicate `### Prompt N` headings in run snapshots; 13 rules total.

### Changed

- **Breaking: skill names no longer carry the `crux-` prefix.** `plugin.json` 0.3.0 → 0.4.0; the catalog is now 47 skills. Substantive renames: `crux-code-review` → `probe-review`, `crux-browser` → `inspect-url`, `crux-server` → `serve-llm`, `crux-pdf` → `process-pdf`, `crux-runbook` → `author-runbook`, `crux-knowledge` → `inject-knowledge`, `crux-identity` → `agent-identity`, `crux-llm` → `call-llm`, `crux-mermaid` → `render-mermaid`, `crux-consistency` → `audit-conventions`, `crux-tracer` → `trace-runtime-ops`, `crux-spawner` → `install-runtime`, `crux-local-image` → `generate-local-image`, `cleanup` → `cleanup-campsite`, `cycle` → `dev-cycle`. Seventeen skills dropped the prefix only. Deleted: `crux-workflow` (content preserved as the skill orchestration cheat-sheet) and `crux-browser-automation` (a stub). `check-no-stale-skill-names.py` gates stale references. Consumers parsing SKILL.md by name should update to the new names.
- **`cycle` skill v0.3.0**: the final prompt now invokes `archive-promptbook`, so a completed cycle no longer sits in `active/`.
- **`USER_GUIDE.md`** gains a maintainers' release section; the cycle template points changelog entries at `## [Unreleased]`.

### Removed

- **`crux/CHANGELOG.md`** — the root `CHANGELOG.md` is the canonical changelog.

## [0.3.0] — 2026-05-27

### Added

- **`cleanup` skill** — the forward-looking counterpart to `audit-docs`, running 12 process-state scans and regenerating `whats_next.md` with prioritized P1/P2/P3 suggestions; `dismissed:` frontmatter is its only persistent state. Invoke via "cleanup", "hygiene check", "what's next".
- **`cleanup` log op**, an optional `cleanup:` block in `manifest.yml` (`adr_proposed_stale_days`, `stuck_promptbook_days`, `audit_stale_days`, default 14), and a schema section defining the `whats_next.md` format.
- **A release workflow that packages every skill as a zip** and publishes them as release assets, with `build-skill-zips.py` (closed content allowlist, 30 MiB cap, deterministic bytes). *(private-history reference — since retired)*

### Changed

- **`plugin.json` 0.2.0 → 0.3.0.**
- **`cycle` skill v0.2.0**: `total_prompts ≥ 13` with three invariants, assembled from modular ADR/dev/review blocks.
- **`log-work` v0.2.0**: self-reflection is a first-class requirement — named failure modes, surprises and "what I'd do differently".

## [0.2.0] — 2026-05-27

### Changed

- **Breaking for external SKILL.md consumers: frontmatter conforms to the public Agent Skills Spec.** Extended fields (`tags`, `bundles`, `owner`, `version`, `risk_level`, `status`, `requires_env`, `origin`, `origin_ref`, `origin_date`) move under a `metadata:` block; list values use `", "` CSV encoding. Consumers of `catalog/skills.json` are unaffected — the validator lifts fields back into the flat shape. `plugin.json` `schema_version` `"1"` → `"2"`.

### Added

- **`validate-skills`** (`uv run validate-skills`) wraps `skills-ref validate` over every skill; the `skills-ref` dev dependency is pinned in the development repository. *(private-history reference)*
- **`migrate-skill-frontmatter.py`** — an idempotent one-shot migration with `--dry-run`.

### Fixed

- **`validate-catalog.py`'s minimal YAML parser handles** nested mappings, folded and literal block scalars with chomp indicators, and quoted-string escapes.

## [0.1.0] — 2026-05-26

- Initial release. 15 skills across six concerns (code docs, research wiki, ADRs, briefs, work journal, promptbooks), expanded to a final catalog of 47 skills across 8 bundles, with secrets managed under `~/.crux/`.
