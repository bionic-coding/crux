<!-- generated-from: CHANGELOG.md@sha256:01b21998b711cc4826835b0869b3f786a373dff8025c400675e46addd93e5469; model: claude-fable-5.1; date: 2026-09-10 -->
# Changelog

All notable changes to crux. The format roughly follows [Keep a Changelog](https://keepachangelog.com/) and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [3.11.1] — 2026-09-10

### Added

- **The decision review assesses each objective against its declared measure, part by part.** The report's Coverage section gains a seven-column assessment table (objective, measure, evidence, locator, domains, conclusion, findings) with one row per measure part. Evidence availability (`resolved | partial | unavailable | not-attempted`) and alignment (`serves | gap | inconclusive | not-assessed`) are separate fields; one counterexample establishes a gap, and only evidence covering the whole claim establishes alignment, so partial evidence can reach `gap` but never `serves`.
- **Attempting an assessment and measuring one are distinct outcomes.** `measured_objectives` in a review report now carries one entry per counted thing — the outcome, the writing pass, and an evidence locator or a blocker. Both outcomes discharge the three-report rotation, a third consecutive attempt owes a finding proposing what would make the measure reachable, a report with no key reads as `unknown`, and an older flat list of ids reads as `attempted`, so no existing report needs rewriting.
- **A finding must earn its causal claim.** Each finding names the mechanism linking the cited decision to the observed measure state, a confidence (`established | contributing | correlated | unresolved`), and the one check that would move it. An `unresolved` finding is never routed to Revoke, and revocation requires positive evidence of a cost — dormancy, a missing run binding and unavailable evidence establish none.
- **Where no signal reaches a measure, the objective initiates a bounded investigation.** An investigation slip names the objective, the measure verbatim, the question, the domain and the intended evidence. The budget is three investigations per pass and five surfaces; a command whose output would exceed the budget is refused rather than partly spent.
- **Every delivery measurement is bounded by a release mark.** A release is identified by the first-parent commit that introduces the version's dated changelog heading. `release_cadence` reports `span_commits` (first-parent commits in the release's half-open interval) and `prep_commits` (commits in that interval whose subject matches the declared prefix) per release, so consecutive intervals partition history without overlap.
- **Nine named conditions replace a bare null in delivery signals.** `no-release-record`, `baseline-ref-unresolved`, `baseline-ref-ambiguous`, `history-unavailable`, `no-baseline`, `surface-absent`, `surface-unreadable`, `surface-malformed`, and `surface-not-comparable` each name one situation. Zero is always a measurement, never a substitute for missing data.
- **The escalation count is carried across review dates rather than recomputed.** Each entry carries `escalation_strikes`, `escalation_owed`, `escalation_owed_since`, `escalation_spent_on`, and `escalation_state`, verified against the previous report; a contradiction is refused. Where a legacy report breaks the chain, the count is reconstructed from the twelve newest dates and marked `unverified`.

### Changed

- **A blocked measure part is counted in its own right.** `measured_objectives` keys on the objective-and-part pair when an entry names a part, so a goal reading `measured` on one part no longer resets the count that surfaces another part's blockage. Every entry carries a digest of the measure text it concerns.
- **A null baseline no longer concludes.** A trend measured against a null baseline is `partial` evidence reaching `inconclusive`, always. Where a measure asserts that something is measurable, a separate part carries that claim and can reach `gap` honestly.

### Fixed

- **`extract-code-docs` could write one tree's pages into another and prune what it found there.** Run from tree A with `--config` naming tree B's manifest and no `--output-dir`, it wrote B's pages over A's and deleted A's own pages, reporting the deletions as an ordinary `removed` count at exit 0. One manifest now owns both the sources scanned and the pages written; an explicit `--output-dir` is still supported, and combining one tree's config with another tree's output directory is reported on stderr.
- **A fresh tree recorded no friction adoption date, so it could never measure friction.** The shipped manifest template carried no `journal:` block, so every tree `init-docs` created read `unmeasurable` on `friction_citations`. The template now carries `journal.friction_line_from`, which `init-docs` substitutes, and a `--force` re-bootstrap carries an existing tree's recorded date forward rather than resetting it.
- **A trailing comment on the `journal:` manifest key hid the adoption date from its reader**, so friction reported `unmeasurable` against a manifest that recorded a date.
- **Twelve skills rendered an empty routing cell.** The routing table takes trigger phrases from a description's first sentence, and the extractor ended that sentence at any period — including one inside a dotted identifier. The sentence now ends at a period followed by whitespace or end-of-text, eleven descriptions state their phrases where the table reads them, and validation fails on any user-invocable skill with no trigger phrase.
- **`prep_commits` counted development commits between subject labels, not preparation.** The count is now bounded by release intervals; a release whose interval is unbounded reports null instead of a zero indistinguishable from a measured one.
- **The schema-growth baseline resolved against a release tag that need not exist.** It is now the release mark (a commit) of the second-newest dated changelog heading.
- **A review report written from the shipped template read as a positive record of zero measurements**, because the template's `##` guidance lines ended the `measured_objectives` block. The reader now treats a `#` comment as transparent at any indent.
- **Carried escalation fields were unfalsifiable, unbounded, or silently dropped.** `escalation_spent_on` now has a grammar, `escalation_state` is a closed set (a typo no longer reads as `verified`), and an unrecognised entry field is refused.
- **An objective id such as `OBJ-99999` could match its own four-digit prefix and discharge a goal nobody named**, and a mistyped header in the per-goal matrix dropped every row beneath it. Both are now refused.
- **Malformed `measured_objectives` frontmatter is refused instead of read as zero entries.** An entry naming no goal, an id outside `OBJ-N`, a missing or unknown outcome, an unrecognised scalar, or an unclosed bracketed list each previously produced an undischarged rotation with nothing to show why.

## [3.11.0] — 2026-09-09

### Added

- **The journal index is now a regenerated output.** `generate-journal-index.py` derives the month row of `journal/index.md` from the month file, with a `--dry-run` drift gate. An unclosed code fence refuses the write at exit 2, naming the source file and line, rather than guessing at entry boundaries.
- **The decision review tracks a finding across dates.** A report carries a five-column record table under `## Coverage` (source report date, finding id, pass, event, locator). A finding with no record is open, `re-verified` leaves it open, `disputed` disputes it, and only `resolved` clears a dispute. The reviews index gains a `standing` column beside `raised`.

### Changed

- **`log-work` derives the journal-index row instead of incrementing it.** Every write recomputes counts and category rollups from the month file. `init-docs` writes the first index when it creates the tree.
- **`check-drift`'s `surface_absent` verdict now applies to any gate that emits it**, with a remedy per surface: `review-decisions` when a review is due, `init-docs` when the journal surface was never created.
- **A report's finding count is its definitions, and the reviews index renders four columns.** Only a `###`-headed entry under Propose, Amend, Repair or Revoke counts toward the total and the five-finding cap; a summary table whose ids are not distinct or disagree with the sections is refused. A new `report_grammar` frontmatter discriminator selects the grammar: a report with none reads as legacy, a report dated after 2026-09-08 with none is refused, and an unrecognised value is refused. The index row reads `raised`, `standing`, `dismissed` and the report link. `generate-reviews-index.py` also refuses symlinked or dangling `adrs`/`reviews` segments, reads reports with newline translation off, and bounds reads at 64 KiB.

### Fixed

- **The architect agent and both user guides cite the live review boundary.** The architect now states the five-path write set and two log ops, and the OpenCode and Codex agent projections are regenerated from it.
- **A symlinked dormancy surface is refused and named even when the link dangles.** `adr-signals.py` previously followed the link, so a dangling symlink at `log.md`, `journal/`, or `promptbooks/runs/` read as absent and could produce a null day count.
- **The decision review's write set is five paths, and its recording composes with `log-work`.** A completed `review-decisions` pass previously left the journal index stale; the index is now reconciled from the current month's journal file.

## [3.10.1] — 2026-09-09

### Changed

- **Releases ship to beta before official.** A version is released first to a private beta repository, installed and tested, and only then published to `bionic-coding/crux` with the same bytes. A version that fails beta never ships officially.
- **The README is titled "Crux" and describes an Agentic Harness plugin**, matching the public repository.

## [3.10.0] — 2026-09-08

### Added

- **Three delivery signals.** `adr-signals.py` gains `release_cadence`, `schema_growth`, and `gate_count` beside its five existing signals. Every git leg runs one fixed argument list under an environment allowlist (`PATH`, `LC_ALL=C`, `GIT_CONFIG_NOSYSTEM=1`, and `SYSTEMROOT` on Windows) with `HOME`, `USERPROFILE`, `HOMEDRIVE`, `HOMEPATH`, and `XDG_CONFIG_HOME` excluded, so neither user nor system git configuration is read.
- **The decision review report carries six sections.** A report dated after 2026-09-07 carries Propose, Amend, Repair, Revoke, Keep, and Coverage in that order, one summary table, and one data-framing note. Repair holds findings whose enacting act writes no ADR file; the five-finding cap counts across Propose, Amend, Repair and Revoke combined. Coverage gains a per-goal matrix. Older reports keep the sections they were written with.
- **The journal `Friction:` line.** A journal entry body may carry one `Friction:` line naming a specific friction, placed before `Refs:` and counting toward the body-line budget. The new `journal.friction_line_from` manifest key records the date from which a count is measurable. `log-work` writes the line; `retrospective` and the friction signal count it.
- **One CommonMark fence parser.** `adr-signals.py` and the template-parity check now share a single fence module with one conformance suite, replacing two hand-copied functions that carried the same defect.

### Changed

- **The public repository moved to the `bionic-coding` GitHub organization.** Every install path now reads `bionic-coding/crux` (`/plugin marketplace add bionic-coding/crux`, `codex plugin marketplace add bionic-coding/crux`, the OpenCode stable-path clone), and the plugin manifests' `homepage` fields point at `https://bionic-coding.com/crux/`. The README opens with a "Start here" link to that site.
- **Apex roles run Fable 5.1 on Claude, and the night gardener joins the apex tier.** The commander, reviewer, and night gardener run Fable 5.1 (a `fable-latest` alias is added). The reviewer's turn budget rises to 150 and the night gardener's to 100. Standard-tier Codex roles run at high reasoning effort.
- **`review-decisions` and its report template aim the pass at delivery.** The skill runs eight signals rather than five, routes each finding by two ordered questions about its proposed act, and disposes the top three `dormancy_days` and top three paper-only ADRs each pass with `keep`, `revoke`, or `defer` and one reason. A `placeholder` objectives file stops the pass rather than yielding a judgment with no yardstick.

### Fixed

- **`init-docs` creates the decision-review surface.** A bootstrapped tree had no `adrs/reviews/` directory, so the first cadence nudge pointed at a path that did not exist.
- **`log-work` no longer cites a retired caller for its log-only branch.**
- **`adr-signals.py` reads both member shapes of `adr.governs_exempt`**, the bare id and the reason-bearing `{adr, reason}` form, in flow or block form.
- **The operational schema states both `governs_exempt` member shapes** rather than calling the reason-bearing form deferred.
- **Nine mined-value readers in `adr-signals.py` split lines by the CommonMark rule, not `str.splitlines()`.** A value carrying `\x0b`, `\x0c`, `U+2028` or similar could forge a heading, table row, or fence closer that no renderer would agree existed. Lines now end only on `\n`, `\r\n`, or a bare `\r`.
- **The fence reader bounds its indent and its closer on the same character class**, so a fence indented with a tab or `U+00A0` no longer opens, and a closer shorter than its opener no longer closes.
- **The `prep_commits` mapping key carries a full 64-character digest** rather than a 16-character one, so two version strings cannot collide and silently overwrite one another's count.
- **The table lane redacts a mined value's key as well as its value.** A forged ADR `id:` could previously carry a terminal escape sequence into the report.
- **An uncompilable version pattern reaches the reader as a finding, not an environment error.** Previously one bad pattern turned all eight signals into exit 2; now that version counts `null` and the rest still compute.

## [3.9.0] — 2026-09-07

### Added

- **`review-decisions`, the periodic architect review of the decision set.** The 60th skill reads the accepted decisions as a set and asks whether they still serve the objectives. It enters through the doctrine index and rule table, opens an ADR body only for a domain a signal flagged, and writes at most five findings into one dated report at `<docs_dir>/adrs/reviews/YYYY-MM-DD.md`. It proposes only: it transitions no record, signs off no batch, and authors no skill.
- **`adr-signals.py`, five mechanical signals as verdict envelopes.** A stdlib-only script computes amendment fan-in, carve-out count, paper-only, dormancy, and friction citations. Every signal is a five-member record (`signal`, `verdict`, `value`, `basis`, `filter`) with no severity or recommendation. `friction_citations` reports `unmeasurable` rather than `0` when the evidence it needs does not exist.
- **The reviews index is a regenerated output.** `generate-reviews-index.py` derives `adrs/reviews/index.md` from the dated reports and fails closed on a filename outside `YYYY-MM-DD.md` or frontmatter disagreeing with its filename. A tree with no reviews directory exits 0 with `"surface_absent": true`, which `check-drift` reads as N/A rather than a clean gate.
- **The objectives file.** `objectives.md` holds the product's mission and goals, the yardstick a decision review measures against: a six-key frontmatter with a `maturity` ladder, a required `## Mission`, `OBJ-N` goals with kind, statement, measure and status, and an append-only `## Shifts` table. `init-docs` seeds it as a placeholder, and every reader asks the owner to fill it in rather than citing a placeholder.
- **Lint rules for the review.** `audit-docs` gains five `CHK-OBJ-*` rules over the objectives file. `cleanup-campsite` gains `CLN-ADR-5` (a decision review older than `adr_review_due_days`, default 7) and `CLN-OBJ-1` (an objectives file still at `maturity: placeholder`), and now ships 20 rules. The log op enum gains `adr-review`.

### Fixed

- **A second `review-decisions` pass on one date no longer overwrites the first.** It refuses an occupied report path and amends the existing report in place, keeping every earlier finding id.
- **`adr-signals.py` reads doctrine rows whose rule text carries an escaped pipe (`\|`)**, which previously made the row vanish without an error.
- **The friction signal reads the forge log under every runtime's local skills directory** — `.claude/skills`, `.agents/skills`, `.opencode/skills` and `.opencode/skill` — not just Claude Code's.
- **A future-dated review report is refused.** `generate-reviews-index.py` refuses a date after `--today` (default: the system date), and the gardener's review-age step applies the same filter, so one file can no longer suppress the cadence reminder indefinitely.

## [3.8.0] — 2026-09-04

### Changed

- **Async text and image councils use GPT-6 Astra as their OpenAI judge**, through OpenRouter pinned to OpenAI as the serving provider. The synchronous council keeps its Terra seat.
- **Council Fable judges use Fable 5.1**, replacing Fable 5.0 at the same effort settings.
- **Codex apex roles (commander and reviewer) use GPT-6 Astra with high effort.** Codex flagship and standard roles keep Sol and Terra.

### Fixed

- **Two test-suite fixes for contributors:** the OpenCode installer error test no longer requires a local OpenCode installation, and the model-catalog tests handle distinct apex and flagship models.

## [3.7.1] — 2026-09-02

### Fixed

- **Every script's PEP 723 header now declares the real Python floor, 3.11.** Fifty-two scripts declared `>=3.10`, but the arch pack uses `tomllib` and several tests use `unittest.TestCase.enterContext`, both 3.11. The headers, the user guide and the schema example now say 3.11. The suite passes on 3.11 except four corpus-golden comparisons, which skip below 3.13 with a named reason.
- **The README states the Python floor and the test command.** The suite needs tree-sitter grammar packages that only the PEP 723 headers name, so the Requirements section now carries the `uv run` invocation that resolves them.

## [3.7.0] — 2026-09-02

### Added

- **The runtime-compatibility block in skills is now a regenerated region.** The block that 55 of 59 `SKILL.md` files carried by hand has one canonical source, a regenerator, and a `--dry-run` drift gate.

### Changed

- **Breaking: the OpenCode projection emits the V2 schema exclusively.** Generated `.opencode/agents/` files replace the singular `permission:` map with an ordered `permissions` array of `{action, resource, effect}` rules under last-match-wins. Two actions are renamed: `bash` becomes `shell`, and `task` becomes `subagent`. The install target moves from `.opencode/agent/` to `.opencode/agents/`. `install-opencode-agents` gains `--migrate-legacy-agent-dir`, which moves a populated legacy directory into the new target and refuses on a name collision unless `--force` is given; it also refuses when no `opencode2` binary is discoverable. A V1 OpenCode runner reading the new projection drops every deny without warning — this is accepted residual risk.
- **The commander can dispatch the wayfinder** for a large, uncertain, or external source that should be sized up before another agent spends context on it.
- **`dev-lead` routes to GLM 5.3 on OpenCode** (`openrouter/z-ai/glm-5.3`); the Claude and Codex seats are unchanged.

### Fixed

- **`web-to-markdown` passes a Markdown or plain-text response through unchanged.** A `text/markdown` or `text/plain` body previously went through the HTML converter and came out as one collapsed line.

## [3.6.0] — 2026-09-02

### Added

- **A decision is now cited as `rule:<slug>`**, the same form on every surface — code comments, prose, promptbook prompts, and journal refs. The linter that resolves the token gains a default scope; an empty scope, an unknown slug, or a retired slug now fails the gate (a retired slug names every live rule that displaced it).

### Fixed

- **The archive-tier ADR readers in the summaries projection no longer follow a symlink out of the tree.**
- **The `srde` skill's batch example now builds `DissentPoint` objects**, which `attempt_batch_resolution` requires, instead of passing raw dissent strings.
- **The plugin's own `crux/README.md` is enrolled in the doc-count gate.** It reached the public repository saying "55 skills" against 59 on disk; it now reads 59 and is held by two count anchors.

## [3.5.0] — 2026-08-31

### Added

- **Batch ratification for observations: `survey-sheet` and `survey-signoff`.** `survey-sheet` scaffolds one `SVY-NNNN` review sheet from the candidate state file; `survey-signoff` is the single human sign-off that publishes it under one digest-bound receipt — one signature is equivalent to N individual ratifications. Both carry `disable-model-invocation`. `audit-docs` gains four `CHK-OBS-SURVEY-*` rules.
- **The `fix-directly` skill: the rung below the three cycle tiers.** "Just fix it" now routes to a named contract — no book, no council, no cycle: a failing test first, the smallest green change, the suite and the drift gates, one commit, one `log-work` entry. A five-question sizing test decides between it and `patch-cycle` / `iterate` / `dev-cycle`.

### Changed

- **`cleanup-campsite` retires `CLN-ADR-1`.** It enforced a convention no project kept and only accumulated findings. The id stays retired with a stub; 18 rules remain.
- **The verify templates carry a reproduction budget.** The `iterate` verify module and the `patch` verify phase state that a failing test is a complete reproduction, a class earns its own reproduction only at a second independent instance, and a security label must not widen the fix. `whiteboarding` gains a sizing step.

### Fixed

- **Three survey sign-off defects.** A v1 sheet beside a receipt skipped signability checks on the resumed-batch path; the index retire loop tore an escaped `\|` in a mined `domain` cell; and `CHK-OBS-BIJECTION` read references by grepping the whole page so a mined cell could forge or suppress a finding.
- **The arch drift gate no longer treats the decision-recovery state file as a stale artifact.** `derive-arch.py --dry-run` now excludes `arch/_recovered/`, which `recover-decisions` writes by design.

## [3.4.0] — 2026-08-30

### Changed

- **The OpenCode commander runs Qwen3.8 Max (1M context) instead of Kimi K3**, which could not sustain the orchestration role under OpenCode. Every other role's OpenCode model is unchanged.
- **Each arch stack-pack probe declares its own input class against a committed roster.** The doctrine index's `implemented` column is renamed `basis`, and a `governs` entry's `retires` sub-field displaces a rule while keeping its record on the ledger.
- **Breaking: a `governs` entry's sub-field set is now closed.** `summarize-adrs.py` and `compile-doctrine.py` hard-refuse an unrecognized sub-field. A tree carrying any other annotation key fails both regenerators on upgrade.

### Fixed

- **A book's `current_run` pointer survives a run's completion**, so `archive-promptbook` can read the pointer its precondition requires. `current_run` now nulls only at archival.

## [3.3.0] — 2026-08-30

### Added

- **A repository that has never authored an ADR can build a doctrine from what its code already does.** The `observations` concern adds `OBS-NNNN` records, each evidenced by a `path:line-range` and ratified by a human. A ratified record projects into the summaries rule table and the doctrine index beside the ADRs.

### Changed

- **`derive-arch` records a per-concern verdict instead of grading its own confidence.** A concern is `populated` or `stubbed`, and every stub names one reason from a closed set of six. The new `arch.require` list in `manifest.yml` fails the derive when a required concern is not `populated`.
- **The arch extractors read committed artifacts and real parsers, never regular expressions over source.** Python routers parse through the standard-library AST; Ruby reads a committed `rails routes` dump; Ruby, Node, and Elixir source parse through tree-sitter grammars. Node routes compose `app.use` mount prefixes, and Elixir routes parse the parenthesized form.

### Removed

- **The `arch_confidence_threshold` key in `.bionic.yml` is retired.** A tree that still sets it loads clean.

## [3.2.2] — 2026-08-29

### Fixed

- **The agent-catalog strict-YAML test skips cleanly without PyYAML** instead of reporting a spurious failure.

## [3.2.1] — 2026-08-29

### Fixed

- **The cycle machinery can accept ADRs and archive books again.** `transition-adr` and `archive-promptbook` no longer carry `disable-model-invocation`, which had blocked dev-cycle, iterate, and patch runs from completing without a human keystroke. The four true human gates (`reconcile-signoff`, `backfill-signoff`, `escalate-arch-runtime`, `transition-invariant`) keep it.

## [3.2.0] — 2026-08-28

### Changed

- **Corrected the OpenCode `permission.task` projection.** A restricted `Agent(role)` grant now projects as a deny-first per-role glob object instead of collapsing to a coarse boolean. The widened-grant report is retired as unneeded.
- **Documented the fields OpenCode ignores.** `$adr`/`$book` argument placeholders bind only in Claude Code, and a new `OPENCODE_GUIDE.md` section lists the invocation-control fields OpenCode does not honor.
- **`fable` is a routable model designation again**; the model catalog no longer disables it.

### Fixed

- **`forge-skill`'s frontmatter guidance matches the schema-3 metadata contract**, so a forged skill promoted into the plugin passes `validate-catalog` rather than failing on the removed `owner`/`version`/`status` keys.

## [3.1.0] — 2026-08-28

### Added

- **`compile-doctrine`** regenerates the doctrine layer from the summaries projection, reconciled against ratified invariants and the human-signed ledger; `--dry-run` is the drift check. It stops and recommends `summarize-adrs.py` first when the summaries have drifted, and never writes the reconciliation ledger.
- **`check-drift`** runs every enrolled regenerator's `--dry-run` in one pass and reports a table of gate, verdict (clean / drift / broken / crash / refusal), drifted paths, and the regenerator that fixes it. It regenerates nothing. Wired into `audit-docs` as `CHK-DRIFT-1`.
- **`reconcile-signoff`** is the single human write path for one doctrine reconciliation. It renders the invariant and rule text, takes the verdict (compatible / reconciled / collision) and rationale from the user, and upserts a digest-bound record. It carries `disable-model-invocation`; `audit-docs` `CHK-DOCTRINE-1` counts pending pairings and points to it.

### Changed

- **Breaking: catalog schema 3 — invocation-control frontmatter and a constant-metadata prune.** `SKILL.md` now admits the Claude Code invocation-control keys (`disable-model-invocation`, `user-invocable`, `context`, `agent`, `model`, `effort`, `background`, `arguments`, `disallowed-tools`), and agents admit `maxTurns`, `effort`, `skills`, `memory`, `isolation`, and `disallowedTools`. The dispatch tool `Task` is renamed to `Agent` (with the restricted `Agent(role)` form). The metadata keys `owner`, `version`, and `status` are removed from every skill and agent — a lingering one is a validation error. The skill routing table is now regenerated from skill frontmatter. `plugin.json` `schema_version` goes `"2"` → `"3"`.

### Fixed

- **A block-style `disallowedTools`/`skills` agent frontmatter list now fails validation** instead of silently mis-projecting (`bash` rendered `allow` instead of `deny`). Every shipped agent authors them inline.

### Removed

- **The `inject-knowledge` skill is retired.** Its bundled layer shipped only a README and nothing referenced it. Git history is the recovery path.

## [3.0.0] — 2026-08-28

### Added

- **The doctrine layer — a third ADR-decision tier, compiled and reconciled.** `adrs/doctrine/` projects each governs domain's live rule, disposition, and implemented-vs-on-paper state from the summaries projection, reconciled against ratified invariants through a digest-bound, human-signed ledger, with a deterministic regenerator and drift gate. Reads route doctrine → summaries → ADR body, with the ADR body winning on disagreement.

### Changed

- **The `qwen-max` OpenCode model alias points to `openrouter/qwen/qwen3.8-2.4t-a95b`.** The standard-rung OpenCode agents (historian, librarian, wayfinder) resolve through it.
- **The architect agent's OpenCode model is the flagship default `kimi-latest`** (`openrouter/moonshotai/kimi-k3`); its per-agent `glm-latest` override was dropped.

## [2.2.0] — 2026-08-28

### Added

- **A historic ADR can now enter the summaries projection.** An ADR numbered below `adr.governs_from` joins only through an anchored, digest-bound, reviewed, at-most-once backfill: the `anchor` `governs` sub-field, the `backfill-signoff` owner-gate skill, and the `backfill` log op.

### Changed

- **The "Silver" ADR-summary layer is renamed to "summaries".** `adrs/silver/` → `adrs/summaries/`, and `generate-silver.py` → `summarize-adrs.py`. Forward-only: frozen ADR bodies, the log, and the journal keep "Silver" as history.

## [2.1.0] — 2026-08-26

### Added

- **ADR frontmatter gains a `governs` block, and a regenerator projects it.** An ADR may author a `governs` entry — `domain`, `rule`, `scope`, `handle`, `provenance` — cohort-bound by the new `adr.governs_from` manifest field. `generate-silver.py` projects every block into a rule table, a resolver, and an ADR↔run implementation map, behind its own `--dry-run` drift gate. The rule table coexists with the arch decision-index.

### Changed

- **Breaking: model calls crux itself performs now route through OpenRouter as a single inference gateway.** The router, the council, the catalog aliases, and the video transcriber resolve every call through one OpenAI-compatible endpoint under one `OPENROUTER_API_KEY`. The direct Anthropic/OpenAI/Google SDKs and the Fireworks provider are retired.

## [2.0.1] — 2026-08-25

### Fixed

- **The development repository's release gates no longer misreport on a machine whose `python3` predates the pinned interpreter.** Bare `python3` invocations in the release tooling are routed through `uv run`, and the development repository pins Python 3.13 via a `.python-version` file. No plugin behavior changes.

## [2.0.0] — 2026-08-25

### Added

- **A deterministic per-derive coverage report.** `arch/_meta/coverage.json` records, for each spine concern, whether it populated or fell back to a stub, and why. The report has no timestamps and rides the existing drift gate.
- **Confidence-graded arch extraction.** Each spine concern self-assesses a grade — high, medium, low, or none. At or below the new `arch_confidence_threshold` config key (default `low`), a stubbed or partial concern offers an attended runtime-escalation session in chat. The unattended pipeline stays static and deterministic.
- **A model catalog: one hand-authored file decides which model every agent runs on.** `crux/catalog/models.yml` (`schema_version 2`) carries a provider allowlist, an alias table, the ten-agent roster keyed to three levels (`apex`, `flagship`, `standard`), the level table, and the Claude alias pins. A malformed catalog is refused rather than degraded.
- **Validator rules V0–V9 over the catalog.** `validate-catalog.py` checks the roster against the agent files, every alias against the provider allowlist, each level's cells, and the Codex slugs against the router registry.
- **`escalate-arch-runtime`: import-only runtime arch introspection behind an attended consent gate.** It runs a FastAPI, Flask, or Django app's import-time code in an isolated subprocess, recovering its route table and ORM schema as an advisory outside the arch spine. It executes only with `CRUX_ARCH_ALLOW_RUNTIME=1` and a per-execution permission event. The unattended `derive` pipeline is unchanged.
- **A third cycle tier, `patch`, with a blast radius the archive gate checks.** `patch-cycle` authors a five-phase book at one prompt each and declares the repository paths it may touch. `archive-promptbook` draws the paths actually changed from git (a diff against the `base_commit` stamped at run start, plus untracked files) and refuses to archive a run that reached outside the declaration.
- **An ADR body content rule.** An ADR body states requirements and postconditions, carries a 120-line budget over its four narrative sections, and names a source of truth rather than restating it. `audit-docs` gains `CHK-ADR-SPEC`, inert in any tree that has not set the new `adr.spec_rule_from` boundary.
- **Two arch spine files are now thin projections.** `arch/api-surface.md` and `arch/decision-index.md` are projected from the skill catalog and the ADR index. A stale input is refused at exit 2 and the refusal names which regenerator to run. `query-docs` gains an architecture route, and all ten role definitions name `arch/` first for a question about the project's own shape.

### Changed

- **Council rounds are routed by blocking findings, and SRDE is de-wired from the ADR path.** A round past the first fires only on a finding that names a failing check against an artifact in the work tree; round 3 is one adjudicator who is not the runner. SRDE stays wired to the verify path.
- **The OpenCode and Codex projections no longer carry their own model tables.** Both regenerators and both installers resolve through the model catalog.
- **In `crux/catalog/`, the file extension declares provenance.** `.json` means regenerated from a source of truth elsewhere; `.yml` means hand-authored, validated, and never written by a generator.

### Fixed

- **The arch drift gate no longer fires on edits that leave the spine byte-identical.** It previously byte-compared a manifest carrying a hash per tracked source file, so editing any source reported drift. `derive-arch.py` also now declares PyYAML, so one source tree produces one spine hash.
- **The runtime arch-introspection entry point is genuinely stdlib-only** and no longer crashes with `ModuleNotFoundError: httpx` in a shipped install.
- **The runtime introspection child no longer writes bytecode into the installed plugin.**
- **The curated decision-index path was unreachable.** A new `arch_decision_index_mode` config key makes the curated mode selectable; the default stays `complete`.

### Removed

- **Breaking: per-advance run bookkeeping and three promptbook surfaces.** `run-promptbook` no longer writes a log op or regenerates the promptbooks index per advance; the `promptbook` op is written at authoring, run start, and archive only. The `cycle-status` skill is deleted and its trigger phrases move to `visualize-run-progress`. The per-prompt `blocked_confirmed` flag is retired; archive eligibility is a run-level property. `author-promptbook --fork-from` is deleted — change a plan mid-run by abandoning the run and authoring a successor book.
- **`crux/catalog/bundles.json`** — replaced by `crux/catalog/bundles.yml`, a mapping keyed by bundle id, read through a loader that refuses anchors, aliases, merge keys, explicit tags, and a second document. The catalog ships inside the plugin, so no downstream repo owes a migration.

## [1.14.0] — 2026-08-18

### Added

- **An Elixir/Phoenix arch stack pack**, completing the batteries-included set (Python, Ruby, Node, Elixir). The interface surface comes from a committed OpenAPI spec, else a static parse of the Phoenix router (never booting the app); the data model from Ecto schemas, with the `null` column honestly left blank for non-key columns; and the module graph from `alias`/`import`/`use` and remote calls that resolve to an in-repo module.
- **A Node.js arch stack pack.** Routes come from a committed OpenAPI spec, else a static scan of Express, Fastify, and NestJS; the data model from Prisma's `schema.prisma`, else TypeORM `@Entity` classes or Sequelize models; the module graph from explicit TS/JS imports with `tsconfig` `@/*` alias resolution. All parsing is static and never boots Node.
- **A Ruby arch stack pack.** Routes come from a committed `openapi.json`, else a static parse of `config/routes.rb`; the data model from `db/schema.rb`; the module graph from a resolve-or-drop pass over the Zeitwerk autoload roots. All parsing is static and stdlib-only.

## [1.13.0] — 2026-08-17

### Added

- **Pluggable arch stack packs, with a Python pack.** `derive-arch` detects the project's stack and resolves each spine file through a per-repo override, then the detected pack, then a stub. The Python pack derives the interface surface from a committed `openapi.json`, the data model from SQLAlchemy models plus Alembic history, and the module graph from the project's own package. Two `.bionic.yml` keys configure it: `arch_stack` pins the pack, and `arch_extractors` registers a per-repo override that runs only under `CRUX_ARCH_ALLOW_OVERRIDES=1`.

## [1.12.0] — 2026-08-17

### Added

- **`install-opencode-agents`** — the OpenCode counterpart to `install-codex-agents`. Say "install the Crux agents in OpenCode" to write the ten projected roles into that project's `.opencode/agent/`. It refuses to overwrite a locally modified role without `--force`, refuses a symlinked crux-managed entry, refuses a target outside the repo root, and never touches a project's own agent files. Skill count 49 → 50.
- **A `.gitignore` in the public repository** covering the untracked `opencode/` tree that the OpenCode setup generates.

### Changed

- **The skill runtime-compatibility contract names OpenCode.** The block in every skill now states the OpenCode form of plugin-root resolution, project-local skill paths (`.opencode/skill`), tool labels (`edit` covers both `Edit` and `Write`), and agent installation.
- **OpenCode setup documents the singular `~/.config/opencode/agent/`** in the README and `OPENCODE_GUIDE.md`.

### Fixed

- **`install-codex-agents` and `generate-codex-agents.py` turned a non-directory agent output path into a traceback.** Both now refuse with a structured error and exit 2; the same guard applies to the OpenCode lane.
- **`generate-opencode-agents.py` wrote through a symlinked agent file.** It now refuses a symlinked agent file on both the write path and `--dry-run`.
- **`crux_wayfinder` was missing from the agent roster in all 46 skills**, and `install-codex-agents` still described "nine" roles. Both now say ten.
- **The OpenCode setup had no upgrade step.** Both docs now instruct regenerating the agent projection after every pull, and `OPENCODE_GUIDE.md` gains troubleshooting rows for stale projections and dangling symlinks.
- **Stale paths and a hardcoded "47 skills" figure in `OPENCODE_GUIDE.md`.**

## [1.11.0] — 2026-08-16

### Added

- **`derive-arch`** — the user-facing entry point to the `arch` concern. Say "build the arch", "summarize the current architecture", or "regenerate the architecture" to regenerate the derived current-state map (data model, interface surface, module graph, decision index, plus a synthesized overview) from the project's own sources. `arch` is now the primary current-state discovery surface, with a dedicated `arch` log op. Skill count 48 → 49.
- **Arch coverage in `audit-docs`.** `CHK-ARCH-1` checks the derived spine for drift and regenerates it in place as a DRIFT-tier auto-fix; `CHK-ARCH-2` recognizes arch enablement.

### Changed

- **`init-docs` enables the `arch` concern by default for new repositories** and scaffolds `arch/` with a placeholder; the first "build the arch" or `audit-docs` run derives the spine. Existing trees are unchanged — add `arch` to `concerns_enabled`, then derive.

## [1.10.2] — 2026-08-14

### Added

- **A drift gate keeps the skill, agent, and writing-rule counts in the README, the user guide, and `prose-review` in step with disk**, so an added skill either updates the prose automatically or fails the release loudly.

### Fixed

- **Two stale skill counts** in the README's OpenCode setup and the user guide's quickstart (46 → 48).

## [1.10.1] — 2026-08-14

### Fixed

- **The arch `module-graph.md` was incomplete**: the extractor matched only absolute imports, so relative `from .x import` edges were missing. It now resolves relative imports and lists isolated modules.
- **arch over-triggered drift on a routine manifest counter bump.** It now hashes only the key-name subset the data model renders.
- **README and skill doc drift**: skill count 46 → 48, agent count nine → ten, three missing skill rows (`prose-review`, `recover-decisions`, `transition-decision`), and `prose-review` now says "seven writing rules".

## [1.10.0] — 2026-08-14

### Added

- **Decision recovery.** `recover-decisions` mines load-bearing decisions latent in code into `observed` candidates with `path:line-range` evidence, held in `arch/_recovered/state.yml`; `transition-decision` ratifies a candidate into a Proposed ADR, or rejects or defers it. `derive-arch.py` gains `decision_index_mode: complete|curated`. New `recover` log op.
- **An ADR archival cold tier.** Superseded and Deprecated ADRs move to `adrs/archive/`, shrinking the active reading path while staying resolvable. `transition-adr` moves an ADR on Supersede/Deprecate, `propose-adr`'s counter scans both tiers so an archived id is never reissued, `generate-adr-index.py` regenerates the index's active table and `## Archived` roster, and `audit-docs` gains `CHK-ADR-ARCHIVE`.
- **Writing rule #7 — footnote-only ADR citation.** In human-facing prose, reference an ADR by a footnote, never an inline number. A new check flags inline ADR references while skipping code, link destinations, frontmatter, blockquotes, HTML, and footnote definitions, with a ratchet baseline.

## [1.9.0] — 2026-08-14

### Added

- **The arch concern.** `<docs_dir>/arch/` is the project's *derived* architecture — a deterministic spine (`data-model`, `api-surface`, `module-graph`, `decision-index`) plus a synthesized `overview.md`, regenerated by `derive-arch.py`. A hash stamp over the spine gates the narrative: `derive-arch.py --dry-run` fails when the spine moved without a re-derive. Ships extractors for the crux stack; other stacks degrade to an empty-but-valid file.

## [1.8.2] — 2026-08-02

### Added

- **Prose-vs-template drift gates.** The `init-docs` skill text is now pinned to the shipped templates, and template comments are checked against the values they describe, so skill prose and templates can no longer disagree silently.

### Changed

- **`init-docs` bootstraps the unified `bionic/` tree.** It creates the layout at the resolved `docs_dir`, with concerns directly under the tree and the invariants concern as one folder, and writes `.bionic.yml` with merge-never-clobber semantics. The guard refuses symlinked trees and cross-checks for a second tree; rollback removes only paths written this run.
- **Templates and schema docs describe the v5 world**: `schema_version "5"` is current, diagram roots sit at `bionic/`, paths use `<docs_dir>`, and both user guides name `bionic/` and `.bionic.yml`. `install-docs-skills` resolves the tree instead of testing for a literal `docs/`.

### Fixed

- **User-reported: fresh installs bootstrapped a `docs/` tree with `schema_version` "4" prose instead of the `bionic/` tree at "5".** The templates had moved but the `init-docs` skill prose had not.
- **`docs_dir` now rejects shell metacharacters.** A committed `.bionic.yml` could set `docs_dir` to a value like `$(id)` that executed when skills composed shell commands around it. Each segment must match `^[A-Za-z0-9_.][A-Za-z0-9._-]*$`.

## [1.8.1] — 2026-07-31

### Fixed

- **`migrate-tree.py` could not migrate a relocated tree, and would have damaged one if forced.** It now resolves the configured `docs_dir` through both config files, anchors the destination at the true repo root, and leaves a relocated tree where its owner put it — only the invariants suite merges into it. `--docs-dir` is the escape hatch for a layout no config declares.
- **The documented upgrade path was a closed loop.** The 4→5 migration rung is now documented with its invocation, exit codes, and fail-closed behaviors.
- **Containment on every path that reads, writes, or removes.** A `docs_dir` of `../elsewhere`, an absolute path, or a symlink escaping the repo is refused rather than followed.
- **The shipped `CLAUDE.md.tmpl` carried eight literal `<tree>` placeholders** that no render step substitutes.
- **`install-docs-skills` hardcoded schema `"3"`** while the plugin shipped `"5"`; it now reads the value from the installed manifest.
- **`audit-docs` was self-contradictory about the supported schema** and still called the invariants concern deferred.

## [1.8.0] — 2026-07-30

### Added

- **Breaking: the tree lives at `bionic/`, and the invariants concern is one folder.** The seven concerns sit directly under `bionic/`, and the invariants concern holds its ledger pages, `checks/`, and `reconciliation.yml` together. `init-docs` always writes `.bionic.yml` naming the tree. `schema_version` `"4"` → `"5"`.
- **Bare-directory discovery.** A tree is recognized by a manifest carrying both `schema_version` and `concerns_enabled`. Two valid trees refuse loudly unless a migration marker names one. **An existing `docs/` tree keeps working with zero config and no migration.**
- **`migrate-tree.py`, the 4 → 5 rung.** A staged, resumable merge: `manifest.yml` moves last so a crash leaves discovery resolving to the source, a marker records the source inventory so replay can tell an already-moved entry from a collision, and config is merged, never overwritten.
- **A schema gate.** Commands that read the tree refuse an unmigrated one with exit 2 and a message on stderr.
- **Six writing rules, and `prose-review` — the 46th skill — to check them.** One name per thing, no hedge without a cause, verbs stay verbs, adjectives must be checkable, one idea per sentence, single-word verbs; accuracy outranks all six. There is no banned-word list, only tests applied per sentence. `prose-review` reports only findings that carry a rewrite.
- **`generate-writing-rules.py`.** One canonical rules text projects byte-equivalently into the root `AGENTS.md` (read by Codex and OpenCode, which never load `CLAUDE.md`), the operational schema, and the shipped `prose-review` skill.

### Changed

- **`prose-review` is now mandatory** in the `dev-cycle` / `iterate` prep prompt and in `tend-garden` before it writes the morning note.

## [1.7.0] — 2026-07-24

### Added

- **Opus 5 refusal handling in the council seats.** A safety refusal returns HTTP 200 with `stop_reason: "refusal"`, which previously surfaced as a JSON parse failure or `unknown`. A new `ModelRefusedError` maps to a new redaction label `"refused"` — a decline wants a prompt change or a fallback model, not a retry.
- **Spawn caps on `commander` and `dev-lead`**: one agent per genuinely independent unit, never for work finishable in about three tool calls, never solely to double-check — with a carve-out for the architectural gates (independent review, per-threat-class security review, two-architect ADR acceptance).
- **Scope-discipline guidance on `dev-lead`**: deliver at the scope intended, without unrequested refactors.

### Changed

- **Model swap: `claude-opus-4-8` → `claude-opus-5`** across the router config and the OpenCode agent generator. `claude-opus-4-8` is removed from the router registry; the lineup is Fable 5 / Opus 5 / Sonnet 5 / Haiku 4.5. Router config `1.4.0` → `1.5.0`.
- **Agent and cycle-skill prose re-tuned for Opus 5's defaults** (it self-verifies unprompted and delegates readily). Every cross-agent gate is preserved.

### Fixed

- **`dev-cycle` / `iterate` checklists overstated validator coverage.** The cycle-coverage pass checks module size and contiguity, not prompt content, and `cycle_grandfathered: true` short-circuits it entirely; both checklists now say so.

## [1.6.0] — 2026-07-23

### Added

- **`generate-lineage.py`** — a committed, deterministic regenerator for `adrs/lineage.md`, behind a drift gate; `link-adr-graph` no longer relies on prose-only instructions.
- **`generate-index-rollup.py` and `generate-readme-footer.py`** — regenerators for the `## ADRs (N)` rollup of the index and the README version footer, each with a `--dry-run` drift gate.
- **`advance-run.py`** — a safe-advance script for promptbook run snapshots that round-trips every top-level key, so run-level `notes` / `pr_draft` / `summary

## [1.5.0] — 2026-07-18

### Added

- **The invariants concern — the seventh concern.** Pinned, ratified, executable statements of what must be true: a human-readable ledger plus a peer executable check suite, reconciled through a `.bionic.yml`-rooted manifest. `recover-invariants` mines code for `observed` candidates and never self-ratifies; `transition-invariant` is the human gate (`observed → ratified | rejected`, `ratified → retired`). `audit-docs` gains five `CHK-INV` rules. `schema_version` `"3"` → `"4"`.
- **`init-docs` enables the invariants concern by default for new repositories.** Existing trees adopt it via `audit-docs --migrate` (a new 3 → 4 rung); `init-docs` never upgrades a populated tree in place.
- **`.bionic.yml` — the repo-root layout source of truth** (`config_version`, `docs_dir`, `artifact_prefix`), superseding the legacy `.crux` file with precedence `.bionic.yml` > `.crux` > convention. Resolved via the new `bionic-config.py` CLI; `crux-config.py` is retained as a back-compat delegator.

### Changed

- **Forged-skill promotion is judgment-driven.** The former mechanical floor (≥2 `effective` evaluations on ≥2 dates) becomes supporting evidence the owner weighs; `retrospective`'s promotion scan is an evidence report.
- **`audit-docs` supports `schema_version "4"`** and its `--migrate` ladder gains a 3 → 4 rung.
- **Concern framing moved from six to seven** across the README, user guide, and operational schema.

## [1.4.2] — 2026-07-13

### Fixed

- **Release commits in the public repository are authored by a dedicated release-bot identity** (`crux release bot` / `no-reply@idyll.io`) applied to author, committer, and tagger, rather than a generic noreply address that GitHub attributed to an unrelated real account. Release tooling only; no plugin behavior change.

## [1.4.1] — 2026-07-10

### Added

- **Public manual OpenCode setup instructions** in the README and a refreshed `OPENCODE_GUIDE.md`: clone to a stable path, `uv run generate-opencode-agents.py`, merge the absolute `crux/skills` path into `opencode.json`, glob-symlink all ten agents, restart the host, and verify with `opencode debug skill` / `opencode agent list`. There is no native OpenCode marketplace package; this path is manual and preview-grade.

### Fixed

- Corrected the README's version footer and completed the 43-skill table in the public README.
- `OPENCODE_GUIDE.md` counts corrected (42 → 43 skills, nine → ten agents), and the agent symlink step made glob-based so it covers `wayfinder`.

## [1.4.0] — 2026-07-10

### Added

- **The OpenCode agent projection is drift-gated with generator test coverage**, including verbatim body/description passthrough.
- **Codex is a supported distribution target and the fourth regenerative agent projection.** `.codex/agents/crux-*.toml` is generated from the same `crux/agents/*.md` source by `generate-codex-agents.py`. Install with `codex plugin marketplace add idyll/crux` then `codex plugin add crux@crux` (the marketplace has since moved to `bionic-coding/crux`; see 3.10.0). Target repos get the ten agents via the no-clobber, path-contained `install-codex-agents` skill, which refuses to overwrite a differing role or remove a stale one without `--force`. The portable `CRUX_PLUGIN_ROOT` bridge is stated correctly everywhere (Claude Code = `CLAUDE_PLUGIN_ROOT`; Codex = derived from the selected `SKILL.md` path). The generated agents' models are corrected against the live Codex catalog (seven roles → `gpt-5.6-sol`, three → `gpt-5.6-terra`).

### Changed

- **LLM router model refresh** (`1.2.0` → `1.3.0`): the seven-SKU OpenAI lineup consolidates into the three effort-controlled GPT-5.6 SKUs — Sol (flagship, alias `gpt-5.6`), Terra, and Luna — all Responses-API-only; `gpt-image-1` → `gpt-image-2`; `openai_reasoning` roles retired. `claude-sonnet-4-6` → `claude-sonnet-5` (rejects the temperature param). Anthropic pricing corrected. `fast_council`'s arbiter is pinned to low effort via `gpt-5.6-sol-low`.

### Fixed

- **OpenAI `/v1/responses` is first-class in the caller and async council.** The async OpenAI seat hardcoded `chat.completions.create`, losing its voice under a Responses-only model; `effort` was not forwarded. Both now route by the model's `openai_endpoint` and forward `reasoning.effort`.
- **Seven Codex-integration review findings remediated**: `CRUX_PLUGIN_ROOT` framing corrected across templates, schema, and 13 skill bodies; PyYAML-dependent tests skip without it; provenance comments anchor external Codex schema assumptions. Release-staging tooling in the development repository is hardened against symlinked grant roots.

## [1.3.3] — 2026-07-10

### Added

- **`CLN-TMPL-1` cleanup-campsite rule** checks operational-schema ↔ distributed-template clause parity, inert when no template twin is present. A general `cleanup-campsite --only <RULE-ID>` selector (CSV-capable) enables single-rule runs.
- **`dev-cycle` and `iterate` record forge-log `used`/`evaluated` entries** for forged skills they invoke, so cycle-used skills accrue the evidence promotion requires.
- **`scout` — the 10th agent, a read-only reconnaissance subagent.** It reads large, uncertain, or external data in an isolated context, judges fitness for a stated purpose, and returns a verdict plus a condensed digest. Tool grant `Read, Grep, Glob, WebFetch, WebSearch`, with an embedded egress guardrail. Model `sonnet`.
- **`run-adr-council` graduates into the plugin** (catalog 41 → 42, `crux-verification` bundle): the ADR council runner, with the council prompt written as a data file so no shell string holds ADR prose.
- **The forged-skill promotion path.** Forged skills are usable in the session that forged them, every session writes an `evaluated` forge-log entry, `retrospective` nominates skills that clear a floor, and graduation into the plugin is always a dev-cycle. `CLN-FG-2` backstops the evaluation discipline.
- **The night-gardener — the 9th agent — and her skills `tend-garden` and `read-news`.** An overnight co-CTO that reviews recent work and writes a morning note under `garden/`, moving only after you have moved. `tending.md` is your control surface: dismiss or snooze, with 90-day decay. `read-news` reads curated sources through Perplexity Search with a WebSearch fallback; `PERPLEXITY_API_KEY` is optional via `~/.crux/`. New `garden` log op. Catalog 39 → 41 skills.
- **`retrospective`** mines the log, journal, archived promptbooks, and forge log since the last marker, distills 0–2 evidence-cited skill proposals, gates each through a fixed council rubric, and builds approvals via `forge-skill`. New `CLN-RETRO-1` rule (`retro_due_runs`, default 5). Catalog 38 → 39.
- **`forge-skill` — the capability-gap loop.** When a gap surfaces mid-task, the model diagnoses it, researches, authors or revises a permanent project-local skill under `.claude/skills/<name>/`, and self-tests on the live problem. Every act lands in the append-only forge log. Detection is embedded in every agent definition. New `CLN-FG-1` rule flags forged skills idle past `forged_skill_stale_days` (default 30).
- **PEP 723 + `uv run "${CLAUDE_PLUGIN_ROOT}/..."` runtime contract**: every shipped runnable script carries an inline-metadata block and is self-describing under `uv run`.

### Changed

- **The reconnaissance agent is renamed `scout` → `wayfinder`**, one name across Claude Code and OpenCode. A pure rename resolving a collision with OpenCode's built-in `scout`.
- **The `architect` agent holds `Bash`** so it can run the multi-model council driver its remit requires.
- **The dev-cycle quality gate mandates the full test suite**, and explicitly whenever a change touches a shared surface (agent roster, router config, catalog).
- **LLM router curated to the latest lineup; `claude-fable-5` disabled** (`enabled: false`, not routable). Older models removed; `gpt-5.5-pro` and `gemini-3.5-flash` added; the two Fable-pinned agents remapped to `claude-opus-4-8`. (Superseded by the GPT-5.6 refresh in 1.4.0.)
- **Split publication model.** The development repository is private; this public repository is a generated artifact receiving one squash commit and tag per release. Releases attach no zip assets — the marketplace makes them redundant.
- **The "Crux Lite" framing is gone from every live surface.** crux is not the lite version of anything.
- **Marketplace-only install story**: `/plugin marketplace add idyll/crux` + `/plugin install crux@crux` (now `bionic-coding/crux`; see 3.10.0).
- **`${PLUGIN_DIR}` → `${CLAUDE_PLUGIN_ROOT}`** as the canonical plugin-root variable in every documented invocation.
- **Spawner runtime directory `.crux` → `.crux-runtime`**, with refusal on a foreign target plus symlink and containment guards.
- **Provenance fields (`origin`/`origin_ref`/`origin_date`) removed** from the SKILL.md frontmatter contract and the catalog; internal decision references removed from distributed surfaces; git softened to enhancement-not-requirement.
- **The distributed `CLAUDE.md` template rebuilt** to the current contracts.

### Fixed

- **The public-release content scan is wired into every cycle template's quality-gate sequence**, so an internal-reference leak onto a distributed surface fails in-cycle.
- **The bare-`python3` test lane is honest**: uv-less runs report clean skips instead of errors, and the PyYAML re-exec lane no longer replaces the test runner mid-suite. `check-no-stale-skill-names.py` gains kebab-boundary guards. README agent count corrected to 9.
- **The test suite is green after the router curation**: tests re-pointed to the surviving lineup, `scout`'s reflex block made canonical, and `gpt-5.5-pro` gains its missing `openai_endpoint: "responses"`.

### Removed

- **`spin` (the Python RSI engine) is decommissioned**, succeeded by `forge-skill`: its disciplines survive as prose, and its modules, skill, and tests are deleted. Catalog stays at 38 (spin out, forge-skill in).
- **`crux/install.sh`** — the curl|bash install path is gone; the marketplace flow is the only install path.

## [0.9.0] — 2026-06-10

### Added

- **Honest YAML-capability failures and automatic uv repair.** `validate-promptbook.py`, `migrate-promptbooks.py`, and `visualize-run-progress.py` require a real YAML parser at entry: without PyYAML they re-exec under `uv run --no-project --with pyyaml>=6.0` (opt-out `CRUX_NO_UV_REEXEC=1`) or exit 2 with a `YamlCapabilityError`, never reporting an environment problem as a document verdict. The fallback parser could silently mis-parse valid documents.
- **Repo-root `.crux` configuration file**: `docs_dir` relocates the docs tree and `artifact_prefix` brands promptbook and ADR ids (`CRX` → `CRX-PB-0040`). Resolved via the `crux-config.py` CLI with containment validation; `audit-docs` gains `CHK-CFG-1..4`. Zero-config repos are byte-for-byte unaffected.
- **`transition-brief` and `cycle-status`** (catalog 36 → 38). `transition-brief` closes the briefs lifecycle (`draft → published | abandoned`), mutating only `status`/`updated_at`. `cycle-status` is a read-only "where am I / what's next" view over a run snapshot.
- **`iterate` skill** (catalog 35 → 36) — a cycle for non-architectural reactive work with `dev-cycle`'s rigor and a verify module in place of the ADR module (`cycle_kind: verify`); the durable record is a journal entry. Minimum 13 prompts.
- **Machine-enforced cycle-coverage validation for all cycle-kind books.** The promptbook schema gains a `cycle_kind` enum (`adr`|`verify`), an extended `module_tag` pattern, and `cycle_grandfathered`/`grandfather_reason`. `validate-promptbook.py` enforces the `4N+4M+3K+2` formula and per-module prompt counts.

### Changed

- **Structural skill and agent improvements across the catalog**: `## When NOT to Use` on five substrate skills, sharper routing descriptions, validation visibly before side effects (`verify-code-docs --no-log`, `log-work` STOP on an invalid `--log-op`), and hardened agent disciplines.
- **Default Claude Opus model bumped `claude-opus-4-7` → `claude-opus-4-8`** across the router and council config and skill examples.
- **The user guide expanded** with an overview, an agent-layer capability table, a tools-and-scripts section, and a rewritten section on `dev-cycle` vs `iterate` vs `author-promptbook`.

### Fixed

- **`council` and the router skills are runnable by the docs.** The canonical `uv run` invocation (with the OpenAI extra; private-history reference to the pre-split project layout) is documented across eleven router-dependent skills, since any `crux.*` import needs the router's dependencies. Result-API examples corrected to the real `CouncilDeliberation`/`CouncilVote` fields.
- **Seven quick-win skill-doc corrections**, including `council`, `call-llm`, and `serve-llm` declaring `ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY` in `requires_env`.
- **Docs drift**: README and user guide refreshed to v0.7.0 reality (33 → 35 skills, new agent-layer sections).
- **`migrate-promptbooks` grandfathers legacy cycle books**, emitting `cycle_grandfathered: true` so migrated books pass validation.
- **`adrs/lineage.md` regenerated** with repaired topic clusters.
- **`whiteboarding` added to the `crux-docs` bundle.**

## [0.7.0] — 2026-06-02

### Added

- **Bundled agent layer** — eight role-based agents (commander, brainstormer, architect, dev-lead, developer, reviewer, historian, librarian) with tool-allowlist guardrails, and a `whiteboarding` skill for docs-aware brainstorming. Agents are catalogued in `catalog/agents.json` and `plugin.json` and embed the craft disciplines (TDD, verification, systematic debugging, two-stage review) directly, so the `superpowers` plugin can be uninstalled.

### Changed

- `validate-catalog.py` regenerates `catalog/agents.json` alongside `skills.json`.
- Briefs may now be whiteboarding-authored, arriving via the inbox.

## [0.6.0] — 2026-06-01

### Added

- **`visualize-run-progress`** (catalog 33 → 34) — a read-only renderer for run snapshots: a colored terminal progress bar and per-prompt checklist, plus an opt-in byte-stable Markdown artifact at `run-RUN-NNN-progress.md`. Author-controlled text is scrubbed of control bytes.
- **`migrate-promptbooks`** (catalog 32 → 33) — migrates legacy `.md` promptbooks and run snapshots to the structured YAML format, recomputes each run's `book_content_hash`, and preserves every original under `promptbooks/legacy

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
