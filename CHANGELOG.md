<!-- generated-from: CHANGELOG.md@sha256:398eaf6326e9d570d880ddea7d15a0328142d2d594a50277e6ac9b9bf66ad22f; model: claude-fable-5.1; date: 2026-09-09 -->
# Changelog

All notable changes to crux. The format roughly follows [Keep a Changelog](https://keepachangelog.com/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [3.10.1] — 2026-09-09

### Changed

- **Beta before official.** Every version is now released first to a private beta channel, installed from it and tested, and only then published to the public repository `bionic-coding/crux` with the same bytes. A version that fails beta never ships publicly.
- **README title and opening line.** The README is titled "Crux" and describes an Agentic Harness plugin, matching the public repository.

## [3.10.0] — 2026-09-08

### Added

- **Three delivery signals join the decision-review signal set.** `adr-signals.py` now computes `release_cadence`, `schema_growth`, and `gate_count` beside its original five, for eight signals in total. `schema_growth` compares the operational schema and skill catalog against the previous release tag and reports a null baseline with a reason when the tag cannot be resolved. Every git call runs with a fixed argument list under an explicit environment allowlist (`PATH`, `LC_ALL=C`, `GIT_CONFIG_NOSYSTEM=1`, and `SYSTEMROOT` on Windows), so neither your user nor system git configuration is read.
- **The decision-review report has six sections.** A report dated after 2026-09-07 carries Propose, Amend, Repair, Revoke, Keep, and Coverage in that order, with one summary table and one data-framing note. Repair holds findings whose remedy writes no ADR file (skill prose, templates, the schema, manifest data, scripts, fixtures); Revoke holds any finding that retires a decision. The five-finding cap applies across Propose, Amend, Repair, and Revoke; Keep and Coverage are uncapped, and Coverage gains a per-goal matrix. Older reports keep their original sections.
- **A `Friction:` line in journal entries.** A journal entry body may carry one `Friction:` line naming a specific friction, placed before `Refs:` when both are present and counted within the 1–10 body-line budget. An empty remainder is a contract violation — omit the line instead. The new `journal.friction_line_from` manifest key records the date from which friction counts are measurable, so a zero can be told from an unmeasured window. `log-work` writes the line; `retrospective` and the friction signal count it, so `friction_citations` can now report `computed`.

### Changed

- **The public repository moved to the `bionic-coding` GitHub organization.** Install paths are now `/plugin marketplace add bionic-coding/crux`, `codex plugin marketplace add bionic-coding/crux`, and the OpenCode clone of `bionic-coding/crux`. The plugin manifests' `homepage` fields point at the documentation site, `https://bionic-coding.com/crux/`, and the README opens with a "Start here" link to it. Author identities and the release-bot address are unchanged.
- **Apex roles run Fable 5.1 on Claude, and the night gardener joins the apex tier.** The commander, reviewer, and night gardener run Fable 5.1 (a `fable-latest` alias is added); the night gardener moves from flagship to apex and keeps its OpenCode seat. The reviewer's turn budget rises to 150 and the night gardener's to 100. Standard-tier Codex roles now run at high reasoning effort.
- **`review-decisions` aims the pass at delivery.** The skill runs eight signals rather than five, routes each finding by two ordered questions about its proposed act, and disposes the top three most-dormant and top three paper-only ADRs each pass with `keep`, `revoke`, or `defer` plus one reason. Mined values are rendered redacted via stdin rather than passed as shell arguments. An objectives file still at `placeholder` maturity stops the pass and empties the finding sections rather than yielding a judgment with no yardstick.
- **The template-parity check gains five clauses (30 → 35).** The new clauses pin the `adr_review_due_days` and `journal.friction_line_from` manifest keys, the `Friction:` line grammar, the reviews-surface report shape, and the `adr-review` log-op body grammar across the operational schema and its shipped template twin.

### Fixed

- **`init-docs` creates the decision-review surface.** A bootstrapped tree had no `adrs/reviews/` directory, so the first review-cadence nudge pointed at a path that did not exist. The directory is now created, gitkept, and listed in the verification checklist.
- **`log-work` no longer cites a retired caller for its log-only branch.** The prose now records that `run-promptbook` no longer logs per-advance at all.
- **`adr-signals.py` reads both member shapes of `adr.governs_exempt`.** Its manifest reader understood only the bare-id form; a reason-bearing `{adr, reason}` member would have miscounted the carve-outs. Both shapes, in flow or block form, now resolve to their ids.
- **The operational schema documents both exemption forms.** §7 now states the two member shapes the projection parses and that the coverage lane reads only the id; the reason-bearing form is no longer described as deferred.
- **Mined values are split into lines by the CommonMark rule, not `str.splitlines()`.** `splitlines()` breaks on characters such as `\x0b`, `\x0c`, `U+2028`, and `U+2029`, none of which ends a Markdown line, so a mined value could forge a heading, table row, or fence closer. All ten call sites in `adr-signals.py` and `check_template_parity.py` now share one line splitter that ends a line only on `\n`, `\r\n`, or `\r`, backed by one conformance suite.
- **Fence detection bounds its indent and closer consistently.** A fence indented with a tab or a `U+00A0` previously slipped past the four-space indent limit, and a closing fence shorter than its opener was accepted. Both holes are closed.
- **Release keys in `prep_commits` carry a full 64-character digest.** A 16-character digest was a reachable collision target for anyone who authors changelog headings; the key now carries the full 256 bits alongside a redacted, legible head.
- **Table output redacts a mined value's key as well as its value.** The three ADR-keyed signals key on the verbatim `id:` scalar of an ADR's frontmatter, and an unredacted key could emit terminal escape sequences (measured: `\x1b[2J` cleared the terminal). Keys now render redacted and quoted.
- **An uncompilable version pattern is a finding, not an environment error.** A regex error while matching version subjects previously turned all eight signals into exit 2. It is now caught per version: that version counts `null` and appears in the unmatchable list, and everything else still computes.

## [3.9.0] — 2026-09-07

### Added

- **`review-decisions` — the periodic architect review of your decision set.** The 60th skill reads the accepted decisions as a set and asks whether they still serve the objectives. It enters through the doctrine index and the summaries rule table, opens an ADR body only for a domain a signal flagged, and writes at most five findings into one dated report at `adrs/reviews/YYYY-MM-DD.md`. It proposes only — its write set is four paths, and it transitions no record, signs off no batch, and authors no skill.
- **`adr-signals.py` — five mechanical signals as verdict envelopes.** A stdlib-only script computes amendment fan-in, carve-out count, paper-only, dormancy, and friction citations. Every signal is a five-member record (`signal`, `verdict`, `value`, `basis`, `filter`) with no severity or recommendation: the script grades nothing. `friction_citations` reports `unmeasurable` rather than `0` when the journal carries no reflective sections to count.
- **A regenerated reviews index.** `generate-reviews-index.py` derives `adrs/reviews/index.md` from the dated reports and fails closed on a filename outside the `YYYY-MM-DD.md` grammar or a report whose frontmatter disagrees with its filename. A tree with no reviews directory exits 0 with `"surface_absent": true`, which `check-drift` reports as N/A, never as a clean gate.
- **The objectives file.** `objectives.md` holds the product's mission and goals — the yardstick a decision review measures against. The format is locked in the operational schema §5.B: a six-key frontmatter with a `maturity` ladder, a required `## Mission`, `OBJ-N` goals each with a kind, statement, measure, and status, and an append-only `## Shifts` table. `init-docs` seeds it as a placeholder from `templates/objectives.md.tmpl`; every reader asks the owner to fill it in rather than citing a placeholder.
- **Lint rules for the review substrate.** `audit-docs` gains five `CHK-OBJ-*` rules over `objectives.md` (structure, enums and dates, heading order, per-goal fields once maturity leaves `placeholder`, a Shifts row for every dropped goal, and a WARNING when `reviewed_at` is older than `review_every_days`). `cleanup-campsite` gains two rules and now ships 20: `CLN-ADR-5` flags a decision review older than `adr_review_due_days` (default 7), and `CLN-OBJ-1` flags an objectives file still at `maturity: placeholder`. The log op enum gains `adr-review`.

### Fixed

- **A second `review-decisions` pass on one date no longer overwrites the first.** The skill refuses an occupied report path and amends the existing report in place, keeping every earlier finding id.
- **`adr-signals.py` reads doctrine rows whose rule text carries an escaped pipe.** A row containing `\|` previously read as nine cells and vanished, which could mark an ADR rowless or paper-only. It now splits on unescaped pipes only.
- **The friction signal reads the forge log under every runtime's local skills directory.** It read only `.claude/skills/forge-log.md`; it now also reads `.agents/skills` (Codex) and `.opencode/skills` or `.opencode/skill` (OpenCode).
- **A future-dated review report is refused.** A report such as `2999-01-01.md` could suppress the cadence reminder indefinitely. The index regenerator now refuses a date after `--today` (default: the system date), and the night gardener applies the same filter.

## [3.8.0] — 2026-09-04

### Changed

- **Async text and image councils use GPT-6 Astra as their OpenAI judge.** Astra replaces Sol in the `openai_top` role through OpenRouter, pinned to OpenAI as the serving provider. The synchronous council keeps its Terra seat.
- **Council Fable judges use Fable 5.1.** The high- and medium-effort entries replace Fable 5.0 while preserving their effort settings; other callers of the shared Anthropic roles also receive Fable 5.1.
- **Codex apex roles use GPT-6 Astra at high effort.** The commander and reviewer receive this model through the shared model catalog; Codex flagship and standard roles keep Sol and Terra.

## [3.7.1] — 2026-09-02

### Fixed

- **Every shipped script declares the real Python floor, 3.11.** Fifty-two scripts declared `>=3.10`, but the Python arch pack uses `tomllib` and the arch tests use `unittest.TestCase.enterContext`, both stdlib from 3.11, so a 3.10 run failed on the environment rather than on the code. The PEP 723 headers, the user guide, and the schema example now say 3.11.
- **The README states the Python floor and the test command.** The test suite needs the tree-sitter grammar packages named only in the PEP 723 headers, so a bare `pip install` environment failed ~140 arch-pack tests. The Requirements section now carries the `uv run` invocation that resolves them.

## [3.7.0] — 2026-09-02

### Added

- **The runtime-compatibility block is generated.** The block that 55 of 59 skills carried by hand now has one canonical template source, a regenerator, and a `--dry-run` drift gate.

### Changed

- **Breaking: the OpenCode projection emits the V2 schema exclusively.** Generated `.opencode/agents/` files replace the singular `permission:` map with an ordered `permissions` array of `{action, resource, effect}` rules under last-match-wins, with every deny for an action preceding its exceptions. Two actions are renamed: `bash` → `shell` and `task` → `subagent`. The install target moves from `.opencode/agent/` to `.opencode/agents/`. `install-opencode-agents` gains `--migrate-legacy-agent-dir` to move a populated legacy directory into the new target; it refuses on a destination-name collision unless `--force` is passed, and it runs a V2 preflight that refuses when no `opencode2` binary is discoverable. **Warning:** a V1 OpenCode runner reading the new projection silently drops every deny rule; run V2.
- **The commander can dispatch the wayfinder.** Its agent allowlist gains `wayfinder`, for sizing up a large, uncertain, or external source before another agent spends context on it. The OpenCode projection carries the matching `subagent` allow rule.
- **`dev-lead` routes to GLM 5.3 on OpenCode.** The catalog row moves from `kimi-latest` to `glm-latest` (`openrouter/z-ai/glm-5.3`); Claude and Codex seats are unchanged.

### Fixed

- **`web-to-markdown` passes Markdown and plain-text responses through unchanged.** A `text/markdown` or `text/plain` body (Anthropic's `.md` doc URLs, for one) previously went through the HTML converter and came out as one collapsed line. The script now detects the content type and emits the body as-is, taking the title from its first heading.

## [3.6.0] — 2026-09-02

### Added

- **Decisions are cited as `rule:<slug>`.** A rule is now referenced by the slug half of the governs handle that carries it, identically in code comments, prose, promptbook prompts, and journal refs. The linter that resolves the token has a default scope over authored sources; an empty resolved scope fails, an unknown slug fails, and a retired slug fails naming every live rule that displaced it. Writing rule 7's footnote definition now names the rule rather than an ADR number.

### Fixed

- **Archive-tier ADR readers no longer follow a symlink out of the tree.** Two readers in the summaries projection followed an `ADR-*.md` symlink planted in `adrs/archive/` to a file outside the repository. Both now refuse a symlink with the same message the active-tier reader uses.
- **The `srde` skill's batch example builds `DissentPoint` objects.** It previously passed raw dissent strings to `attempt_batch_resolution`, which takes `DissentPoint` objects.
- **The plugin's own `README.md` says 59 skills.** It shipped saying 55 against 59 on disk; it is now covered by the doc-count drift gate.

## [3.5.0] — 2026-08-31

### Added

- **Batch ratification for observations: `survey-sheet` and `survey-signoff`.** `survey-sheet` scaffolds one `SVY-NNNN` review sheet from the candidate state file, seeding `anchor_id` and `proposed_domain` and leaving `verdict`, `domain`, and `rationale` empty. `survey-signoff` is the single human sign-off that publishes the sheet under one digest-bound receipt — one signature equals N individual ratifications, and it is the only batch route past `observed`. Both carry `disable-model-invocation` and are excluded from run-execution autonomy. The state table lives in the operational schema §17.5, and `audit-docs` gains four `CHK-OBS-SURVEY-*` rules.
- **`fix-directly` — the rung below the three cycle tiers.** "Just fix it" now routes to a named contract: no book, no council, no promptbook; a failing test first, the smallest green change, the suite and drift gates, one commit, one `log-work` entry. A five-question sizing test decides between it and `patch-cycle` / `iterate` / `dev-cycle`. A security label sets a defect's priority, not its size.

### Changed

- **`cleanup-campsite` retires `CLN-ADR-1`.** The rule reported an accepted ADR unmentioned in the README or USER_GUIDE within 30 days — a convention that only accumulated findings. The id stays retired with a stub; 18 rules remain implemented.
- **The verify templates carry a reproduction budget.** The `iterate` verify module and the `patch` verify phase now state three rules: a failing test is a complete reproduction; a class earns its own reproduction only at a second independent instance; a security label must not widen the fix. `whiteboarding` gains a sizing step and the same one-instance-is-a-bug rule.

### Fixed

- **Three survey sign-off defects.** `assert_signable` now runs on every publish path, including a resumed batch beside a `config_version: "1"` sheet (v1 stays readable for digest verification only). The index retire loop splits on unescaped pipes only, so an escaped `\|` in a mined `domain` cell no longer tears a row. `CHK-OBS-BIJECTION` reads each row's id column rather than grepping the whole page, so a mined cell can no longer forge or suppress a finding.
- **The arch drift gate no longer treats the decision-recovery state file as a stale artifact.** `derive-arch.py --dry-run` swept every file under `arch/` the derive would not write, and the first `recover-decisions` run writes `arch/_recovered/state.yml` there by design. `_recovered/` is now excluded; a stray file anywhere else under `arch/` still drifts.

## [3.4.0] — 2026-08-30

### Changed

- **The OpenCode commander runs Qwen3.8 Max (1M context) instead of Kimi K3.** Kimi K3 could not sustain the commander's orchestration role under OpenCode. Every other role's OpenCode model is unchanged.
- **Arch stack-pack probes declare their own input class against a committed roster.** The doctrine index's `implemented` column is renamed `basis`, and a `governs` entry's new `retires` sub-field displaces a rule while keeping its record on the ledger.
- **Breaking: a `governs` entry's sub-field set is now closed.** `summarize-adrs.py` and `compile-doctrine.py` both refuse an unrecognized sub-field. A tree carrying any other annotation key on a `governs` entry fails both regenerators on upgrade.

### Fixed

- **A book's `current_run` pointer survives run completion.** The completion advance previously erased `current_run` before `archive-promptbook` could read it, so archival's own precondition failed. `current_run` now nulls only at archival, by exactly one writer.

## [3.3.0] — 2026-08-30

### Added

- **A repository that has never authored an ADR can build a doctrine from what its code already does.** The `observations` concern adds `OBS-NNNN` records of observed behavior, each evidenced by a `path:line-range` and ratified by a human. A ratified record projects into the summaries rule table and the doctrine index beside the ADRs.

### Changed

- **`derive-arch` records a per-concern verdict instead of grading its own confidence.** A concern is `populated` or `stubbed`, and every stub names one reason from a closed set of six. The new `arch.require` list in `manifest.yml` fails the derive when a required concern is not `populated`.
- **Arch extractors read committed artifacts and real parsers, never regular expressions over source.** Python routers parse through the stdlib AST; Ruby reads a committed `rails routes` dump; Ruby, Node, and Elixir source parses through tree-sitter grammars declared in the script's dependency block. Node routes compose `app.use` mount prefixes, and Elixir routes parse the parenthesized form. On a ten-repository corpus of real applications, the stubbed-concern rate outside `decision-index` fell from 13 of 30 to 2 of 33.

### Removed

- **The `arch_confidence_threshold` key in `.bionic.yml` is retired.** A tree that still sets it loads clean and produces no attribute.

## [3.2.2] — 2026-08-29

### Fixed

- **The agent-catalog strict-YAML test skips cleanly without PyYAML.** The test for rejecting an unquoted mid-value colon now carries the same `skipUnless` guard as its siblings, so a no-PyYAML environment skips it instead of reporting a spurious failure.

## [3.2.1] — 2026-08-29

### Fixed

- **The cycle machinery can accept ADRs and archive books again.** `transition-adr` and `archive-promptbook` no longer carry `disable-model-invocation`, which had been mis-applied and blocked dev-cycle, iterate, and patch runs from accepting an ADR or archiving a completed book without a human keystroke. A guard test now fails if any skill named in a cycle template's `side_effects` carries the field. The four true human gates (`reconcile-signoff`, `backfill-signoff`, `escalate-arch-runtime`, `transition-invariant`) keep it.

## [3.2.0] — 2026-08-28

### Changed

- **Corrected the OpenCode `permission.task` projection.** A restricted `Agent(role)` grant now projects as a faithful deny-first per-role glob object instead of collapsing to a coarse boolean. The widened-grant report, its sign-off file, and the `report_drift` dry-run key are retired as unneeded.
- **Documented the fields OpenCode ignores.** A runtime-compatibility note records that `$adr`/`$book` argument placeholders bind only in Claude Code, and a new `OPENCODE_GUIDE.md` section lists the invocation-control fields OpenCode does not honor.
- **The model catalog no longer disables `fable`.** The `claude_disabled` table that refused `fable` as an agent `model:` value is removed, so `fable` is routable again.

### Fixed

- **`forge-skill`'s frontmatter guidance matches the schema-3 metadata contract.** It no longer names the removed `owner`/`version`/`status` keys, so a forged skill promoted into the plugin passes `validate-catalog`.

## [3.1.0] — 2026-08-28

### Added

- **`compile-doctrine` — the skill front for the doctrine regenerator.** Regenerates `adrs/doctrine/` wholesale from the summaries projection, reconciled against the ratified invariants and the human-signed reconciliation ledger; `--dry-run` is the drift check. It stops and recommends `summarize-adrs.py` first when the summaries projection has drifted, and never writes the reconciliation ledger.
- **`check-drift` — a read-only runner for every enrolled drift gate.** Runs each regenerator's `--dry-run` in one pass and reports one table of gate, verdict (clean / drift / broken / crash / refusal), drifted paths, and the regenerator that fixes it. It regenerates nothing. Wired into `audit-docs` as `CHK-DRIFT-1`.
- **`reconcile-signoff` — the single human write path for one doctrine reconciliation.** Renders the invariant and rule text, takes the verdict (compatible / reconciled / collision) and rationale from you, then upserts a digest-bound record and re-compiles doctrine on explicit confirmation. It never chooses a verdict and never batch-signs; it carries `disable-model-invocation`, and `audit-docs` `CHK-DOCTRINE-1` counts pending pairings and points to it.
- **A signed gate for the OpenCode `Agent(role)` widened-grant report.** A sign-off file names each agent role whose OpenCode restriction is unenforceable, with rationale, signer, and date; a new or stale unenforced restriction fails a gate instead of shipping silently. (Retired in 3.2.0 once the projection was corrected.)

### Changed

- **Catalog schema 3: invocation-control frontmatter and a constant-metadata prune.** SKILL.md admits the Claude Code invocation-control keys (`disable-model-invocation`, `user-invocable`, `context`, `agent`, `model`, `effort`, `background`, `arguments`, `disallowed-tools`), and agents admit `maxTurns`, `effort`, `skills`, `memory`, `isolation`, and `disallowedTools`; each new agent field projects to Codex and OpenCode by a locked faithful-or-drop table. The dispatch tool `Task` is renamed to `Agent` (with the restricted `Agent(role)` form). **Breaking:** the constant metadata keys `owner`, `version`, and `status` are removed from every skill and agent, and a lingering one is now a validation error. A bundle-closure rule keeps every skill a default-on skill depends on default-on. The skill invocation table is regenerated by `generate-routing-table.py` from skill frontmatter and gated by `--dry-run`. `plugin.json` `schema_version` goes `"2"` → `"3"`.

### Fixed

- **A block-style `disallowedTools`/`skills` agent list now fails validation instead of silently mis-projecting.** The list form validated clean but projected `bash` as `allow` instead of `deny` and left orphan lines in the generated OpenCode agent file. `validate-catalog.py` now rejects the block form for these two keys; every shipped agent already authors them inline.

### Removed

- **Retired the `inject-knowledge` skill.** Its bundled knowledge layer shipped only a README and nothing referenced it. The skill, its module, its `crux-core` bundle membership, and its catalog and routing rows are removed; git history is the recovery path.

## [3.0.0] — 2026-08-28

### Added

- **The doctrine layer — a third ADR-decision tier, compiled and reconciled.** `adrs/doctrine/` projects each governs domain's live rule, disposition, and implemented-vs-on-paper state from the summaries projection, reconciled against ratified invariants through a digest-bound, human-signed ledger. A deterministic regenerator, a drift gate, and a companion warn-gate round out the increment. Reads now route doctrine → summaries → ADR body, with the ADR body winning on disagreement.

### Changed

- **The `qwen-max` OpenCode model alias points to `openrouter/qwen/qwen3.8-2.4t-a95b`.** The standard-rung OpenCode agents (historian, librarian, wayfinder) resolve through this alias, and their projected agent files are regenerated.
- **The architect's OpenCode model is the flagship default `kimi-latest` (`openrouter/moonshotai/kimi-k3`).** Its per-agent `opencode: glm-latest` override is dropped, so architect inherits the flagship rung like the other flagship agents.

## [2.2.0] — 2026-08-28

### Added

- **Governs backfill — a historic ADR can now enter the summaries projection.** An ADR numbered below `adr.governs_from` joins the summaries projection only through an anchored, digest-bound, reviewed, at-most-once backfill. This adds the `anchor` `governs` sub-field (verified by space-folded containment), the enforcing checks, a `backfill-reviews.yml` receipts manifest hashed into the summaries input domain, the `backfill-signoff` owner-gate skill, the `backfill` log op, and a completion marker.

### Changed

- **The "Silver" ADR-summary layer is renamed to "summaries".** `adrs/silver/` → `adrs/summaries/` and `generate-silver.py` → `summarize-adrs.py`. The rename is forward-only: frozen ADR bodies, the log, the journal, and archived runs keep "Silver" as history.

## [2.1.0] — 2026-08-26

### Added

- **ADR frontmatter gains a `governs` block, and a regenerator projects it.** An ADR may author a `governs` entry — `domain`, `rule`, `scope`, `handle`, `provenance` — cohort-bound by the new `adr.governs_from` manifest field. `generate-silver.py` projects every `governs` block into a rule table, a resolver, and an ADR↔run implementation map under `adrs/silver/`, behind its own `--dry-run` drift gate. A coverage gate and a two-tier reference linter distinguish a rule handle from a plain ADR citation. The rule table coexists with the arch decision index rather than replacing it.

### Changed

- **Breaking: model calls crux itself performs now route through OpenRouter as a single inference gateway.** The router, the council, the catalog aliases, and the video transcriber resolve every call through one OpenAI-compatible endpoint under one `OPENROUTER_API_KEY`. The direct Anthropic/OpenAI/Google SDKs and the Fireworks provider are retired.

## [2.0.1] — 2026-08-25

### Fixed

- **Development repository only: release checks no longer misreport on a machine whose `python3` predates the required interpreter.** The development repository's release checks now invoke Python through `uv run`, which resolves the pinned interpreter regardless of `PATH` order, and the development repository pins Python 3.13. No plugin, skill, or docs-tree behavior changed.

## [2.0.0] — 2026-08-25

### Added

- **A deterministic per-derive coverage report.** `arch/_meta/coverage.json` records, for each spine concern, whether it populated or fell back to a stub, and why. The report is byte-stable and rides the existing drift gate.
- **Confidence-graded arch extraction.** Each spine concern self-assesses a confidence grade — high, medium, low, or none — recorded in `coverage.json` with the reason. At or below the new `arch_confidence_threshold` config key (default `low`), a stubbed or partial concern offers an attended runtime-escalation session in chat; `none` is never offered. The unattended pipeline stays static, deterministic, and drift-gated.
- **A model catalog — one hand-authored file decides which model every agent runs on.** `crux/catalog/models.yml` (`schema_version 2`) carries a provider allowlist, an alias table that is the only place a model id appears, the ten-agent roster keyed to three levels (`apex`, `flagship`, `standard`), the level table, and the `claude_aliases` / `claude_disabled` pins. A shared reader refuses a malformed catalog rather than degrading to a partial roster.
- **Validator rules V0–V9 over the catalog.** `validate-catalog.py` checks the roster against the agent files, every alias against the provider allowlist, each level's cells, the Codex slugs against the router registry, and the confinement of every document-derived key.
- **Python import-only runtime arch introspection, behind an attended two-factor consent gate.** The new `escalate-arch-runtime` skill runs a target FastAPI, Flask, or Django app's import-time code in a subprocess-isolated child, recovering its route table and ORM schema, and files the result as an advisory outside the arch spine. It executes only with `CRUX_ARCH_ALLOW_RUNTIME=1` set and a per-execution, non-model-mediated permission event. The unattended `derive` pipeline is unchanged and reads no flag.
- **A third cycle tier, `patch`, with a blast radius the archive gate checks.** `patch-cycle` authors a five-phase book at one prompt each, and the book declares the repository paths it may touch before its run starts. `archive-promptbook` compares the paths the run actually changed (`git diff --no-renames` against the `base_commit` stamped at run start, plus untracked files) and refuses to archive a run that reached outside the declaration. The declaration is frozen by `book_content_hash`.
- **An ADR body content rule.** An ADR body states requirements and postconditions, carries a 120-line budget over its four narrative sections, and names a source of truth rather than restating it. `audit-docs` gains `CHK-ADR-SPEC`, inert in any tree that has not set the new `adr.spec_rule_from` cohort boundary.
- **Two arch spine files are thin projections, and readers have a route to the spine.** `arch/api-surface.md` and `arch/decision-index.md` are projected from the skill catalog and the ADR index instead of re-parsing those sources, so each fact has one answerer. A stale input is refused at exit 2 with the name of the regenerator to run. `query-docs` gains an architecture route, and all ten role definitions name `arch/` first for a question about the project's own shape.

### Changed

- **Council rounds are routed by blocking findings, and SRDE is de-wired from the ADR path.** A round past the first fires only on a finding that names a failing check against an artifact inside the repository work tree. Round 3 is one adjudicator who is not the runner, inside the unchanged three-round bound. SRDE stays wired to the verify path.
- **The OpenCode and Codex projections no longer carry their own model tables.** `MODEL_MAP` and `RUNTIME` are deleted; both regenerators and both installers resolve through the catalog. Four generated files moved as a result: the `architect`, `commander`, and `developer` OpenCode roles and `.codex/agents/crux-developer.toml`.
- **In `crux/catalog/`, the file extension declares provenance.** `.json` means regenerated from a source of truth elsewhere and enrolled in the derived-artifacts roster; `.yml` means hand-authored, validated, and never written by a generator. CHK-CAT coverage now reaches every catalog file.

### Fixed

- **The arch drift gate no longer fires on edits that leave the spine byte-identical.** `--dry-run` byte-compared `_meta/manifest.json`, whose `sources` map carries a SHA-256 per tracked source, so editing any tracked source reported drift. The gate now compares every property of that file except the value of `sources`. `derive-arch.py` also declares PyYAML, so one source tree no longer produces two spine hashes depending on which frontmatter parser ran.
- **The runtime arch-introspection entry point is genuinely stdlib-only.** It loads its runtime modules by file path instead of importing through the `crux` package, so it no longer crashes with `ModuleNotFoundError: httpx` in a shipped install. The `escalate-arch-runtime` child-env docs no longer mention `PYTHONPATH`.
- **The runtime introspection child no longer writes bytecode into the installed plugin.** `sys.dont_write_bytecode` is now set before the module load it was meant to cover.
- **The curated decision-index path was unreachable.** `derive-arch.py` never bound `decision_index_mode` to any input, so it always resolved to "complete". A new `arch_decision_index_mode` config key makes the curated mode selectable; the default stays "complete".

### Removed

- **Breaking: per-advance run bookkeeping and three promptbook surfaces.** `run-promptbook` no longer writes a log op or regenerates the promptbooks index per advance; a run's per-prompt chronology now comes from its snapshot timestamps, and the `promptbook` op is written at authoring, run start, and archive only. The `cycle-status` skill is deleted and its trigger phrases move to `visualize-run-progress`. The per-prompt `blocked_confirmed` flag is retired; archive eligibility is now a run-level property. `author-promptbook --fork-from` is deleted — change a plan mid-run by abandoning the run and authoring a successor book. The pinned spine-hash constant is replaced by a `derive-arch --dry-run` preflight.
- **`crux/catalog/bundles.json`** is replaced by `crux/catalog/bundles.yml`, a mapping keyed by bundle id, read through a loader that refuses anchors, aliases, merge keys, explicit tags, and a second document. The catalog ships inside the plugin, so no downstream repo owes a migration.

## [1.14.0] — 2026-08-18

### Added

- **An Elixir/Phoenix arch stack pack — completing the batteries-included set (Python, Ruby, Node, Elixir).** The interface surface comes from a committed OpenAPI spec, else a static parse of the Phoenix router (verbs, `resources` REST expansion, nested resources, `scope` prefixes, and LiveView routes) without booting the app. The data model comes from Ecto schemas, with the `null` column left blank for non-key columns because Ecto cannot express NOT-NULL. The module graph is a real dependency graph over `alias`/`import`/`use` and remote calls, keeping only in-repo edges. An unparseable file degrades to a hashed note rather than a wrong parse.
- **A Node.js arch stack pack.** The interface surface comes from a committed OpenAPI spec, else a static scan of Express, Fastify, and NestJS routes (guarded to `/`-leading string paths). The data model comes from Prisma's `schema.prisma`, else TypeORM `@Entity` classes or Sequelize models. The module graph resolves explicit TS/JS imports, including `tsconfig` `@/*` aliases, and keeps only in-repo edges. All parsing is static and never boots Node.
- **A Ruby arch stack pack.** A Rails or Ruby repo now derives a real architecture spine: the interface surface from a committed `openapi.json`, else a static parse of `config/routes.rb`; the data model from `db/schema.rb`; and the module graph from a resolve-or-drop pass over the Zeitwerk autoload roots. All parsing is static and stdlib-only, every read is confined under the repo root, and all rendered content is escaped.

## [1.13.0] — 2026-08-17

### Added

- **Pluggable arch stack packs, with a Python pack.** `derive-arch` detects the project's stack and resolves each spine file through a per-concern probe registry: a per-repo override, then the detected pack, then a stub. The Python pack derives the interface surface from a committed `openapi.json`, the data model from SQLAlchemy models plus Alembic migration history, and the module graph from the project's own package — so a FastAPI + SQLAlchemy service gets a real architecture spine with no repo code. Two `.bionic.yml` keys configure it: `arch_stack` pins the pack, and `arch_extractors` registers a per-repo override that runs only under `CRUX_ARCH_ALLOW_OVERRIDES=1`.

## [1.12.0] — 2026-08-17

### Added

- **`install-opencode-agents` skill** — the OpenCode counterpart to `install-codex-agents`. Say "install the Crux agents in OpenCode" to write the ten projected roles into that project's `.opencode/agent/`. It refuses to overwrite a locally modified role without `--force`, refuses fail-closed on a crux-managed entry that is a symlink, refuses when the target resolves outside the repo root, and never touches a project's own agent files. Project-scoped installation is now an alternative to the machine-wide symlink flow in the README. Skill count 49 → 50.
- **A `.gitignore` in the public repository.** Anyone who clones the public repo and follows the OpenCode setup generates an untracked `opencode/` tree; it is now ignored rather than permanent `git status` noise.

### Changed

- **The skill runtime-compatibility contract names OpenCode.** All 46 skills carrying the boilerplate said "portable across Claude Code and Codex" and described plugin-root resolution, project-local skill paths, tool-label translation, and agent installation for those two hosts only. The block now states the OpenCode form of each: plugin root derived from the selected `SKILL.md` path, `.opencode/skill` for project-local skills, lowercase tool labels with `edit` covering both `Edit` and `Write`, and `install-opencode-agents` with the bare hyphenated role names.
- **OpenCode setup documents the singular `~/.config/opencode/agent/`** in both the README and `OPENCODE_GUIDE.md`, noting that OpenCode reads the plural form too and that populating both leaves you guessing which copy is live.

### Fixed

- **`install-codex-agents` and `generate-codex-agents.py` no longer traceback on a non-directory output path.** A regular file, a symlink to a regular file, or a dangling symlink at the agent output path ended the run in a traceback (and exit 1 for the generator, which reserves that code for the dry-run drift report). Both now refuse with a structured error and exit 2, and the same guard applies to the OpenCode lane.
- **`generate-opencode-agents.py` wrote through a symlinked agent file.** Replacing a generated agent file with a symlink made the regenerator overwrite the link's target — any file the running user can write — and report success. It now runs every filesystem step through the shared implementation and refuses a symlinked agent file on both the write and `--dry-run` paths.
- **`crux_wayfinder` was missing from the agent roster in all 46 skills**, and `install-codex-agents` still described itself as installing "nine" roles. Both now say ten and include `crux_wayfinder`.
- **The OpenCode setup had no upgrade step.** `opencode/agents/` is a generated, untracked projection, so a `git pull` advanced its source and silently left the projection behind. Both docs now instruct regenerating after every pull, and `OPENCODE_GUIDE.md` gains troubleshooting rows for the stale-projection and dangling-symlink failures.
- **Stale references in `OPENCODE_GUIDE.md`** — tree paths that should have moved to `bionic/`, and a hardcoded "47 skills" figure.

## [1.11.0] — 2026-08-16

### Added

- **`derive-arch` skill** — the user-facing entry point to the `arch` concern. Say "build the arch", "summarize the current architecture", or "regenerate the architecture" to regenerate `bionic/arch/` — the derived current-state map (data model, interface surface, module graph, decision index, plus a synthesized overview) — from the project's own sources. `arch` is now documented as the primary current-state discovery surface (ADRs are the secondary "why") across the README, USER_GUIDE, the operational schema, and the downstream `CLAUDE.md` template, with a dedicated `arch` log op. Skill count 48 → 49.
- **Arch-spine coverage in `audit-docs`** — `CHK-ARCH-1` checks the derived spine for drift and regenerates it in place, reporting the regenerate as a DRIFT-tier auto-fix; `CHK-ARCH-2` recognizes arch enablement. It auto-regenerates (unlike the code-doc and catalog checks) because every arch input is already committed.

### Changed

- **`init-docs` enables the `arch` concern by default for new repositories.** A fresh tree enrolls `arch` in `concerns_enabled` alongside the seven established concerns and scaffolds `bionic/arch/` with a placeholder; the first "build the arch" or `audit-docs` run derives the spine. No `schema_version` bump. Existing trees are unchanged: add `arch` to `concerns_enabled`, then derive.

## [1.10.2] — 2026-08-14

### Fixed

- **Two stale skill counts in the docs** — the README's OpenCode setup and the USER_GUIDE's quickstart said 46 skills; both now say 48. The development repository gains a drift gate that rewrites these live counts from disk and fails a release when they drift.

## [1.10.1] — 2026-08-14

### Fixed

- **arch `module-graph.md` was incomplete** — the extractor matched only absolute imports, so relative `from .x import` edges were missing. It now resolves relative imports, uses full-module node ids, and lists isolated modules so all modules are represented.
- **arch over-triggered drift on a manifest counter bump** — `_meta` hashed the whole `manifest.yml` though `data-model` renders only its key names; it now hashes the derived key-name subset, so a routine `next_number` bump no longer drifts arch.
- **README and skill doc drift** — skill count 46 → 48, agent count nine → ten, three missing skill rows (`prose-review`, `recover-decisions`, `transition-decision`), and `prose-review`'s description now says "seven writing rules".

## [1.10.0] — 2026-08-14

### Added

- **Decision recovery.** `recover-decisions` mines load-bearing decisions latent in code into `observed` candidates — structural-anchor identity, `path:line-range` evidence with no code excerpt, redaction-scanned statements — in the mutable `bionic/arch/_recovered/state.yml`. `transition-decision` ratifies a candidate into a Proposed ADR (idempotent via `recovered_id`), or rejects or defers it. `derive-arch.py` gains `decision_index_mode: complete|curated`, and a new `recover` log op.
- **ADR archival cold tier.** Superseded and Deprecated ADRs move to `bionic/adrs/archive/`, shrinking the active reading path while staying immutable and resolvable. `transition-adr` moves an ADR on Supersede/Deprecate; `propose-adr`'s counter and collision check scan both tiers so an archived id is never reissued; `generate-adr-index.py` regenerates `adrs/index.md`'s active table and `## Archived` roster from both tiers (byte-stable, drift-gated); `audit-docs` gains `CHK-ADR-ARCHIVE` and a raw-path guard.
- **Writing rule #7 — footnote-only ADR citation.** In human-facing prose, reference an ADR by a footnote, never an inline number or a link that renders it, with carve-outs for ADR bodies and the journal. A new AST-based check flags inline ADR references while skipping code, link destinations, frontmatter, blockquotes, HTML, and footnote definitions, with a ratchet baseline so it enforces going forward without blocking un-migrated surfaces.

## [1.9.0] — 2026-08-14

### Added

- **The arch concern.** `<docs_dir>/arch/` is the project's *derived* architecture — a deterministic spine (`data-model`, `api-surface`, `module-graph`, `decision-index`) plus a synthesized `overview.md`, regenerated by `derive-arch.py`. A SHA-256 hash-stamp over the four spine files gates the narrative: `derive-arch.py --dry-run` fails when the spine moved without a re-derive. Ships four extractors for the crux stack (JSON Schemas, ADR frontmatter, skill catalog, Python import graph); other stacks degrade to an empty-but-valid file. `docs_dir` is containment-checked before any write.

## [1.8.2] — 2026-08-02

### Changed

- **`init-docs` bootstraps the unified `bionic/` tree.** The skill creates the schema-5 layout at the resolved `docs_dir`, never a hardcoded literal: concerns directly under the tree, the invariants concern as one folder (`checks/` + `reconciliation.yml` inside), and `.bionic.yml` written for every tree with merge-never-clobber semantics (preserving `artifact_prefix`). The guard refuses symlinked trees, cross-checks the other well-known location for a second tree, and archives with collision, symlink, and containment refusals. Rollback removes only paths written this run, restores modified pre-existing files, and restores the `--force` archive.
- **Templates and schema docs describe the schema-5 world.** The operational schema template gains the `"5"` version row, diagram roots at `bionic/` with the unified invariants folder, documented bare-directory discovery with the `bionic` default, and `<docs_dir>` paths in place of undefined aliases. Both USER_GUIDEs name `bionic/`, `schema_version 5`, and `.bionic.yml`. `install-docs-skills` fresh-install detection resolves the tree instead of testing for a literal `docs/`. `audit-docs` `CHK-CFG-1` reports the real `source` enum and calls `"5"` the supported version.

### Fixed

- **User-reported: fresh installs bootstrapped a `docs/` tree with `schema_version` "4" prose instead of the `bionic/` tree at "5".** The templates had moved to schema 5 but the `init-docs` skill prose still instructed the v4 split layout. Drift gates between skill prose and shipped templates now prevent a recurrence.
- **`docs_dir` rejects shell metacharacters.** A committed `.bionic.yml` could set `docs_dir` to a value like `$(id)`, which passed validation and executed when skills composed shell commands around the path. Each segment must now match `^[A-Za-z0-9_.][A-Za-z0-9._-]*$`.
- **The template-parity gate was silently dead since the tree move** — its canonical paths pointed at the retired `docs/CLAUDE.md`, so every clause reported stale. Paths now resolve to `bionic/CLAUDE.md`, and a liveness test prevents recurrence.

## [1.8.1] — 2026-07-31

### Fixed

- **`migrate-tree.py` could not migrate a relocated tree, and would have damaged one if forced.** It hardcoded its source to `<root>/docs` and never resolved the configured `docs_dir`. Source is now resolved through both config files, the destination is anchored at the true repo root, and a relocated tree stays where its owner put it — only the invariants suite merges into it. `--docs-dir` is the escape hatch for a layout no config declares, authoritative over both the conventional fallback and a stale marker.
- **The documented upgrade path was a closed loop.** The schema gate says to run `audit-docs --migrate`, but that skill documented only rungs 2→3 and 3→4. The 4→5 rung is now documented with its invocation, both forms, exit codes, and fail-closed behaviors.
- **Containment on every path that reads, writes, or removes.** A `docs_dir` of `../elsewhere`, an absolute path, or a symlink escaping the repo is refused rather than followed; symlinked directories are refused during merges and suite placement even when they stay in-repo.
- **The `CLAUDE.md` template shipped eight literal `<tree>` placeholders** that no render step substitutes, so every generated schema file carried them verbatim. It also described tree relocation as "deferred" and a nested `bionic/docs/` mechanism that was never built.
- **`install-docs-skills` hardcoded schema `"3"`** while the plugin shipped `"5"`. It now reads the supported value from the installed manifest.
- **`audit-docs` was self-contradictory about the supported schema** (predicate `"5"`, surrounding text `"4"`) and its `CHK-CFG-1` breadcrumb still called the invariants concern deferred.

## [1.8.0] — 2026-07-30

### Added

- **Breaking: the tree lives at `bionic/`, and the invariants concern is one folder.** The seven concerns sit directly under `bionic/` — no nested `docs/` level — and the invariants concern holds its ledger pages, a `checks/` subdirectory, and `reconciliation.yml` together. `init-docs` always writes `.bionic.yml` naming the tree. `schema_version` `"4"` → `"5"`.
- **Bare-directory discovery.** A tree is recognized by a manifest carrying both `schema_version` and `concerns_enabled`. Two valid trees refuse loudly unless a migration marker names one; exactly one resolves to it; none resolves to `bionic`. **An existing `docs/` tree keeps working with zero config and no migration** — the legacy directory wins when it is the only one.
- **`migrate-tree.py`, the 4 → 5 rung.** A staged, resumable merge rather than a rename: entries merge one at a time, `manifest.yml` moves last so a crash leaves discovery resolving to the source, and a marker records the source inventory so replay can tell an already-moved entry from a real collision. Config is merged, never overwritten.
- **A schema gate.** Commands that read the tree refuse an unmigrated one with exit 2 and a message on stderr, so an audit can never report clean because it cannot find its own reconciliation surface.
- **Six writing rules, and `prose-review` — the 46th skill — to check them.** One name per thing, no hedge without a cause, verbs stay verbs, adjectives must be checkable, one idea per sentence, single-word verbs; accuracy outranks all six. They descend from ASD-STE100 Simplified Technical English, so there is no banned-word list — only tests applied per sentence. `prose-review` reports only findings that carry a rewrite: `fix` when the rewrite follows from the text, `confirm` when it needs a fact only the author holds.
- **`generate-writing-rules.py`.** One canonical writing-rules text projects byte-equivalently into its consumers, including the shipped `prose-review` skill and the operational schema §16; reads and writes preserve line endings, every target is validated before any is written, and each write is atomic.

### Changed

- **`prose-review` is now mandatory at three points**: the release preflight (advisory), the `dev-cycle` / `iterate` prep prompt, and `tend-garden` before it writes the morning note.
- **The README's catalog-history sentence was rewritten** from 104 words carrying thirteen ideas to two sentences of 25; per-release detail lives in this file.

## [1.7.0] — 2026-07-24

### Added

- **Opus 5 refusal handling in the council seats.** A safety refusal returns HTTP 200 with `stop_reason: "refusal"`, not an error, and previously surfaced as a JSON-parse failure or as `unknown`. A new `ModelRefusedError` maps to a new redaction label, `"refused"` — a decline wants a prompt change or a fallback model, not a retry, credential fix, or bug report. Council aggregation already excluded errored seats; this makes the reason truthful.
- **Spawn caps on the delegating agent roles.** `commander` and `dev-lead` now carry an explicit cap — one agent per genuinely independent unit, never for work finishable in ~3 or fewer t
