---
title: Manifest schema
read_when: Reading or changing `<docs_dir>/manifest.yml`
sections:
  - "§7"
---

# Manifest schema

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §7`, resolves to this file.

## 7. `manifest.yml` schema

```yaml
schema_version: "5"

concerns_enabled:           # which concerns this project uses (seven default plus the default-on arch spine and observations)
  - code
  - research
  - adrs
  - briefs
  - journal
  - promptbooks
  - invariants              # enabled by default on new trees; opt-in on migration (§15)
  - arch                    # default-on for new repos; opt-in for existing trees (§4)
  - observations            # default-on for new repos; opt-in for existing trees (§17)

code:
  extractors:               # one entry per language; name → extractor plugin
    <language>:
      extractor: <plugin-name>     # matches scripts/extractors/<name>.py
      glob: "<glob>"               # string or list of strings
      include_private: true        # python only; any other key refuses the python run

research:
  refresh_interval_days: 90        # source-staleness threshold for refresh-research-sources

adr:
  next_number: 1                   # monotonic, never reused; allocated by propose-adr
  spec_rule_from: null             # OPTIONAL. The CHK-ADR-SPEC cohort boundary (§11.D):
                                   # null/absent = rule inert; NNNN = governs every ADR numbered >= NNNN.
  governs_from: null               # OPTIONAL. The governs-block cohort boundary: null/absent = no
                                   # governs block expected; NNNN = every ADR numbered >= NNNN is
                                   # expected to carry a governs block or a recorded exemption.
  governs_exempt: []               # OPTIONAL. List of ADR IDs excused from the governs-coverage
                                   # cohort even though their number is >= governs_from. Default [].
  governs_backfilled: {}           # OPTIONAL. The backfill admission ledger: {ADR-NNNN: [handles]},
                                   # append-only per handle — a removed handle is retained against
                                   # re-admission. Written ONLY by the backfill sign-off skill.
  governs_backfill_cohort: []      # OPTIONAL. The frozen backfill cohort: the enumerated ADR ids
                                   # (Accepted, non-archived, numbered below governs_from)
                                   # snapshotted when the backfill machinery lands; closed forever.
  governs_backfill_complete: ~     # OPTIONAL. Terminal binary marker: absent or `true`. Set only
                                   # when Σ backfilled + Σ no-rule = |cohort| over distinct ADRs;
                                   # any pending cohort ADR defeats it.
  governs_rule_baseline: []        # OPTIONAL. The rule-length advisory baseline (§11.D rule 7): the
                                   # ENUMERATED ADR ids that predate the advisory IN THIS TREE,
                                   # snapshotted once and closed from then on. `[]` is correct for a
                                   # new tree and self-maintaining — with no ADRs yet, every ADR you
                                   # write is advised on. ABSENT leaves the advisory inert, and the
                                   # governs-coverage gate says so in its `warnings`. Adopting it in
                                   # a tree that already has ADRs is a ONE-OFF snapshot of their ids,
                                   # not a list regenerated on each run and never grown to excuse a
                                   # newly written ADR.

arch:                              # OPTIONAL block. The arch concern's strict gate (§4).
  require:                         # OPTIONAL. The concerns this tree REQUIRES. Absent = no gate.
    - data-model                   # A concern named here whose RECORDED verdict is not `populated`
    - api-surface                  # fails the derive with exit 1 and its verdict on stdout, having
    - module-graph                 # written the spine. ALWAYS checked, no flag needed. `--strict` is
    - decision-index               # a separate route requiring EVERY concern for one run.
                                   # Name only concerns this repository already produces: requiring
                                   # one it does not would fail your own build. Read by
                                   # `derive-arch.py`, never by the deriver's `_build`, so it never
                                   # enters the arch source set and never flaps the drift gate.

journal:                           # OPTIONAL block. The friction-line cohort boundary.
  friction_line_from: null         # OPTIONAL. ISO date, nullable. null/absent = friction-line count
                                   # unmeasurable; a date sets the boundary at or after which a
                                   # `Friction:` count is measurable (rule:journal-friction-line).
                                   # init-docs writes the initialization date here, never null.

promptbook:
  next_number: 1                   # monotonic, never reused; allocated by every authoring skill, incl. a successor book

observation:                       # the observations concern (§17); present when `observations` is enabled
  next_number: 1                   # monotonic, never reused; allocated by propose-observation and by the
                                    # transition-decision observation terminal
  stale_days: 90                   # OPTIONAL. CHK-OBS-STALE's threshold, on the research.refresh_interval_days
                                    # model. Absent falls back to 90.
  next_survey_number: 1            # monotonic, never reused; allocated by the survey scaffold as the
                                    # SVY-NNNN batch id (§17.5). Machine-derived, never content-derived.
  survey_stub_days: 1              # OPTIONAL. The window in which a receipt recording no completion is
                                    # WARNING rather than BROKEN (§17.3, §17.5). Absent falls back to 1.

cleanup:                           # OPTIONAL block. Cleanup falls back to defaults if absent.
  adr_proposed_stale_days: 14      # Used by CLN-ADR-2 — flag Proposed ADRs older than this.
  stuck_promptbook_days: 14        # Used by CLN-PB-1 — flag promptbooks whose current_run snapshot mtime hasn't moved.
  audit_stale_days: 14             # Cleanup emits a P1 "run audit-docs" suggestion if audit hasn't run within this window.
  forged_skill_stale_days: 30      # no authored/revised/used/evaluated event within this window (timestamp comparison). Used by CLN-FG-1 and CLN-FG-2.
  retro_due_runs: 5                # Used by CLN-RETRO-1 — flag when ≥ this many cycles closed (completed, abandoned or shortcut) since the last 'Retrospective:' journal entry.
  adr_review_due_days: 7           # CLN-ADR-5 may suggest migrate-adrs when historical reviews are older than this; no pass is required. Absent falls back to 7.
```

`journal.friction_line_from` is prospective and per-tree, on the same cohort model `adr.spec_rule_from` already establishes. Absent or `null` leaves every friction reader `unmeasurable` — there is no boundary before which a zero count could mean anything. Set to an ISO date, it marks the boundary at or after which a `Friction:` line is expected wherever `log-work` is the writer; a reader counts only entries dated at or after it, and its `basis` says the window was truncated when the asked-about window starts earlier. The recorded date is not earlier than the date the conforming writer was in use in that tree — an earlier date reintroduces the ambiguity the boundary exists to remove. A tree `init-docs` creates records the initialization date here rather than `null`, so a fresh tree measures friction from its first conforming entry; a `--force` re-bootstrap carries the existing tree's recorded date forward rather than resetting it forward.

`schema_version` here governs the **`docs/` tree layout only** — it does NOT cover the plugin's SKILL.md frontmatter contract. That contract has its own `schema_version` under `plugin.json` (see §7.A). The two namespaces are intentionally separate: `docs/manifest.yml` schema bumps when this directory tree's layout changes, with the one exception the version history names; `plugin.json` schema bumps when SKILL.md frontmatter conventions change. A **third** version axis, the per-file **`format_version`** on promptbook/run documents (see §3), is distinct from both: it governs the intra-file structure of one promptbook/run YAML document (not a directory-tree layout and not the SKILL.md contract), so changing a promptbook/run file format bumps `format_version`, **never** this `schema_version`.

The installed plugin refuses to operate on a `docs/` tree whose `schema_version` is outside its supported range.

**`docs/manifest.yml` schema version history:**
- `"1"` — initial layout.
- `"2"` — Layout unchanged since v1 introduction; the bump aligned with a broader plugin-schema revision. Additive — v1 trees read cleanly under a v2 validator.
- `"3"` — **BREAKING — the first non-additive layout bump; it ends the additive-only precedent the `"1"`/`"2"` rows established** (do not read the rows above as asserting all bumps are additive). Retires the research-local `docs/research/new/` drop folder in favor of the cross-concern top-level `docs/inbox/` staging area processed by `process-inbox`. A v2 tree has `docs/research/new/` and no `docs/inbox/`; recognized now only as a needs-migration state. **Historical upgrade path on pinned public `v3.23.2`:** its `audit-docs --migrate` creates `docs/inbox/`, relocates any in-flight `docs/research/new/*` (incl. a pending `urls.md`) into it, removes the emptied `docs/research/new/`, and rewrites `schema_version` to `"3"`.
- `"4"` — BREAKING. Adds the seventh concern, **invariants** (§15): a ledger under `docs/invariants/` + a peer executable check suite at `<tree>/invariants/checks/` reconciled via the `.bionic.yml`-rooted manifest. Breaking because the peer suite lives *outside* the docs tree and an older plugin cannot gracefully degrade (ignoring an unreconciled suite risks treating durable checks as disposable). Superseded by `"5"`; recognized now only as a needs-migration state (rung 4→5). **Historical upgrade path on pinned public `v3.23.2`:** its `audit-docs --migrate` (rung 3→4) bumps to `"4"`, **opt-in-enables** `invariants` (only when the `bionic/` layout is present or you confirm — an existing repo with no `bionic/` degrades gracefully), and creates the empty ledger + suite + reconciliation surfaces (idempotent, fail-closed).
- `"5"` — **current. BREAKING.** Unifies the whole tree under `bionic/` and retires `docs/` as a layout name. Concerns sit directly under `bionic/`. The invariants concern becomes one folder — `<docs_dir>/invariants/`, with `checks/` and `reconciliation.yml` inside. The default `docs_dir` becomes `bionic`, and `init-docs` writes an explicit `.bionic.yml` for every tree it creates. A tree at a custom `docs_dir` is still a valid `"5"` tree. The upgraded plugin operates only on `"5"` (the supported-range predicate is the single-value check `schema_version == "5"`) and recognizes `"4"`/`"3"`/`"2"` solely as needs-migration states. **Historical upgrade path on pinned public `v3.23.2`:** its `audit-docs --migrate` (rung 4→5, implemented there by `crux/scripts/migrate-tree.py`) folds the check suite into `invariants/checks/`, merges the tree entry-by-entry into `bionic/` with `manifest.yml` moved last, merges (never overwrites) the config, and sets `schema_version: "5"` (idempotent, fail-closed, resumable). Existing `docs/` trees keep resolving via bare-directory discovery with zero config and no migration.

**The operations-log split keeps `"5"`.** Moving the operations log from `docs/log.md` to the monthly detail files under `docs/log/` (§6) changes the tree layout, and it is the one layout change that bumps no `schema_version`.[^oplog-schema] The log writer splits a legacy `log.md` on its first write and every reader reads both forms, so no tree needs a migration step. A bump would add a manifest write, and so a crash point, to that split, and it would make an older `audit-docs` report a split tree as broken.

The plugin's SKILL.md frontmatter contract (see §7.A) was revised separately, bumping `plugin.json` `schema_version` from `"1"` to `"2"` — `docs/manifest.yml` `schema_version` did not move because no `docs/` layout changed. Likewise the `cleanup-campsite` additions (the log op, the regenerated `docs/whats_next.md`, the optional `cleanup:` block above) were **additive** — older readers gracefully degrade (the new op shows as a `CHK-LOG-*` warning at worst; absent `whats_next.md` is the v1 default; absent `cleanup:` block falls back to defaults) — and did not bump this `schema_version`. The promptbook/run Markdown→YAML format change is a `format_version` change, NOT a tree-layout bump: the files still live at `promptbooks/active/`, `promptbooks/runs/<id>-<slug>/`, `promptbooks/archive/` — only their extension and intra-file shape changed, and legacy `.md` files coexist with new `.yaml` ones.

[^oplog-schema]: rule:log-split-keeps-tree-schema-5
