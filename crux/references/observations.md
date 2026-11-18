---
title: Observations concern
read_when: Proposing, ratifying, surveying or auditing an observation record
sections:
  - "§17"
---

# Observations concern

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §17.5`, resolves to this file.

## 17. The observations concern

An **observation** is a `governs`-shaped record of what the code already does, hosted in its own file at `<docs_dir>/observations/OBS-NNNN-<slug>.md`. It describes; it does not decide. A repository that has never authored an ADR uses observations as its bronze layer, and a repository that has ADRs uses them for the facts nobody ever decided. This section is the **single source of truth** for the concern's contract; the template `OBS-template.md`, the `propose-observation` and `transition-observation` skills, the `transition-decision` observation terminal, and `audit-docs` all reference it by name. None of them restates the §17.1 field set. A skill may carry a bounded mirror of the §17.2 lifecycle table or the §17.3 rule list, on the §15.3/§15.5 precedent, and that mirror is subordinate to this section.

Four artifact types can be ratified in this tree, and one verb tells them apart:

- an **ADR** decides, and its authority is the decision;
- an **invariant** (§15) prescribes what must be true, and an executable check proves it;
- an **observation** describes what is true, and a `path:line-range` evidences it;
- a **decision candidate** (§4 `arch`) proposes nothing yet — it is a machine's guess held in the candidate state file `<docs_dir>/arch/_recovered/state.yml`, a scan artifact inside the tree but never a citable record, until `transition-decision` turns it into an ADR or, with `ratify --as observation`, an observation.

The first three are records a reader can cite. The fourth is not, and that is the distinction to hold: a candidate is unratified machine output, and ratifying it is what produces a citable record. A candidate has exactly two terminals, ADR and observation; it has no invariant terminal. An invariant pin is born only through `recover-invariants` and `transition-invariant` (§15).

The concern is enabled additively — no `schema_version` bump and no migration rung — default-on for new trees and opt-in for existing ones. It does not require the `adrs` concern. A tree may enable observations and never enable ADRs.

Ratification runs one record at a time or one batch at a time. `transition-observation` is the single-record gate (§17.2); the survey sign-off is **the only batch route**, equivalent to N individual ratifications under one signed receipt (§17.5). A batch's signed sheet and its receipt live in the frozen `_surveys/` holding area (§3), which is no concern surface: it has no index section and every record walk excludes it. The publish order is fixed, because **completion precedes visibility** — the receipt's completion lands before any record becomes visible, so a visible record never stands behind a receipt recording no completion. And `defer` is the one verdict that writes nothing to the candidate state file, which is what keeps a deferred candidate re-scaffoldable into a later batch.

### 17.1 Canonical observation frontmatter schema (single source of truth)

This table is the **single source of truth** for observation frontmatter, on the §11.A model. Adding a field is a one-row edit here. The field-name column uses backtick markup so the comparison is mechanical: the backticked tokens in the first column are the canonical keyset.

| field | type | required? | semantics |
|---|---|---|---|
| `id` | string | required | `OBS-NNNN`, 4-digit zero-padded, optionally carrying the repo's configured artifact prefix per §14.3. Matches the filename. Allocated from `observation.next_number` (§7); never reused. |
| `title` | string | required | Declarative present-tense statement of what the code does. |
| `status` | enum | required | `observed \| ratified \| rejected \| retired \| decided`. |
| `date` | ISO date | required | Date of the current status entry. Moves on every transition. |
| `observed_date` | ISO date | required | Immutable; date the record was first written. |
| `ratified_date` | ISO date \| null | required | Set on ratify; `null` until then. |
| `rejected_date` | ISO date \| null | required | Set on reject; `null` until then. |
| `retired_date` | ISO date \| null | required | Set on retire; `null` until then. |
| `decided_date` | ISO date \| null | required | Set on the `decided` transition; `null` until then. |
| `provenance` | enum | required | `recovered \| reconstructed`. The §15.2 enum minus `authored`: an authored rule is an ADR, so `authored` on an observation is a validation error. |
| `decided_by` | string \| null | required | The ADR id that records this rule as a decision, or `null`. Non-null exactly when `status` is `decided`. |
| `evidence` | list | required | One or more `path:line-range` strings, each repo-relative — for example `crux/scripts/summaries_projection.py:1240-1268`. Never a code excerpt, and never prose quoting one. |
| `anchor_id` | string | required | The structural anchor identity, `sha256(anchor_kind + NUL + canonical_anchor)[:16]`, on **every** record including a reconstructed one. It is what makes a re-mine recognize a fact already recorded. |
| `related_invariants` | list | required | `INV-NNNN` ids, or `[]`. |
| `tags` | list | required | Topic tags. |
| `governs` | list | required | One or more rule records, each a mapping using the §11.A `governs` sub-fields unchanged. Four constraints apply here and nowhere else: each entry's `provenance` equals the record's `provenance`; each entry's `handle` is namespaced by the record id, `OBS-NNNN/<rule-slug>`, so a handle cannot collide across records or with an ADR handle; `anchor` is unused, because a record's claim is bound to code by `anchor_id` rather than to a body span — an `anchor` sub-field on an observation entry is a validation error; and `retires` is unused on an observation entry, because an observation describes what the code does and cannot displace a decided rule — a `retires` sub-field on an observation entry is a validation error. |

The body below the frontmatter is prose for a human: what the code does, where the evidence is, and why this is observed rather than decided. It carries no code excerpt either.

### 17.2 The lifecycle, the writer boundary, and the immutable claim

The state machine is the invariants ratification machine (§15.3) plus one terminal:

```
observed ──ratify──▶ ratified ──retire──▶ retired
   │                     │
   │                     └──decide──▶ decided
   └──reject──▶ rejected
```

| From | Op | To | Notes |
|---|---|---|---|
| observed | ratify | ratified | A human affirms the record describes the code. |
| observed | reject | rejected | A human judges the record wrong or not worth keeping. |
| ratified | retire | retired | The code moved away from what the record describes. |
| ratified | decide | decided | A human authored an ADR for the same rule; `decided_by` names it. |

Every other transition is refused. The lifecycle is forward-only, there is no path back into `observed`, and a revived observation is a new record.

**The writer boundary is human-invoked against scan, not one component.** An observation file is created and mutated only by a human-invoked command. **No scan writes an observation file in any state.** Two commands create one — `transition-decision ratify --as observation` on the mined ramp and `propose-observation` on the reconstructed ramp — and both are human-invoked. Two commands mutate one. `transition-observation` remains the **only single-record route** past `observed`, and the batch sign-off is the **only batch route**, equivalent to N individual ratifications under one signed receipt (§17.5). `transition-observation` keeps its batch refusal verbatim and redirects to the sign-off, because a refusal made conditional on a flag is a false green over the safety property. The extraction path creates neither an observation nor an ADR; it writes only its own candidate state file.

**A ratified record's claim is immutable.** Its `governs` rule, `domain`, `scope`, `provenance`, `evidence`, and `anchor_id` never change. Only the lifecycle fields change, and only through the gate. A re-mine that finds a recorded `anchor_id` carrying different rule text or different evidence therefore revises nothing: it opens a **successor candidate** in the candidate state file, on that same `anchor_id`, and a human ratifies the successor and retires its predecessor, or rejects it.

**Anchor loss is a signal, never a transition.** A re-mine that no longer finds a recorded `anchor_id` writes a stale-anchor signal to its own candidate state file. It does not touch the observation. A human retires the record through the gate.

### 17.3 Audit rules (owned by `audit-docs`; stated here as the contract)

These read §17.1 and restate none of it. They are silent when `observations` is absent from `concerns_enabled`.

- **CHK-OBS-BIJECTION** — record↔file is 1:1: a file under `<docs_dir>/observations/` with no parseable `id`, a duplicate `id`, an `id` that disagrees with its filename, an index row naming a record with no file, or a record file whose `id` appears in no index row → **BROKEN**. The last direction is the reverse of the one before it, and both run only when `index.md` exists — a tree with no index yet would otherwise emit one finding per record.
- **CHK-OBS-ANCHOR** — `anchor_id` is present on every record and matches `^[0-9a-f]{16}$` → **BROKEN** when it is absent or malformed. No two records in `observed` or `ratified` status share an `anchor_id` → **BROKEN** on a collision. This is the rule that makes a re-mine recognize a fact already recorded (§17.2); without it a record missing the field is silently skipped by the re-mine, which then proposes a duplicate.
- **CHK-OBS-EVIDENCE** — every `evidence` entry matches the `path:line-range` grammar, and a `ratified` record resolves every path it cites → **BROKEN** on an unresolvable path, an unparseable entry, or an empty `evidence` list. A cited path must also resolve to a location **inside** the repository root: an absolute path, a `~`-prefixed path, a `..` traversal, or a path reaching outside the root through a symlink is the same finding.
- **CHK-OBS-DECIDED** — a `decided` record names a `decided_by` ADR that exists → **BROKEN** when it does not. A non-`decided` record carrying a non-null `decided_by`, or a `decided` record carrying `null`, is the same finding.
- **CHK-OBS-STALE** — an `observed` record whose `observed_date` is older than `observation.stale_days` (§7; absent falls back to 90) → **WARNING**. Report survey-debt as the **count** of `observed` records, never as a coverage percentage: the denominator would be the facts nobody has written down, which nobody knows.

Four more rules read the batch surfaces. Each derives batch state through the one shared function named in §17.5, so a gate never disagrees with the writer.

- **CHK-OBS-SURVEY-STUB** — a receipt under `_surveys/SVY-NNNN/` recording no completion → **WARNING** inside `observation.survey_stub_days` (§7; absent falls back to 1), where a sign-off in progress produces one, and **BROKEN** past that window. The remedy is re-running the sign-off, which completes the publish.
- **CHK-OBS-SURVEY-VISIBLE** — a record visible under `<docs_dir>/observations/` whose receipt records no completion → **BROKEN** at any age. No healthy in-flight state produces one, because §17.5 lands completion before visibility.
- **CHK-OBS-SURVEY-DIGEST** — a receipt whose recomputed digest no longer matches the sheet archived beside it → **BROKEN**.
- **CHK-OBS-SURVEY-RECORD** — a `ratified` record whose `anchor_id` no receipt covers **and** behind which no `observation` log op stands → **BROKEN**. The rule is a disjunction and stays one: the single-record path writes no receipt, so a conjunction would report BROKEN on every record that path wrote. It detects an unrecorded batch and never a forgery, because an actor with write access can write every surface.

### 17.5 Batch ratification: the review sheet, the receipt, and the write protocol

Batch ratification is one human-invoked sign-off over one human-authored review sheet. This subsection is the **single source of truth** for that protocol. §17.2's per-record gate stands unchanged beside it.

**The two commands.** The skill `survey-sheet` scaffolds a sheet; the skill `survey-signoff` signs it. Both read and write through one shared module, so the sheet's reader and its writer can never disagree about its shape. Both skills carry `disable-model-invocation: true` and appear in no cycle template's `side_effects`, and the sign-off is a §11 run-execution stop point.

**Batch identity.** A batch is `SVY-NNNN`, allocated by the scaffold from the monotonic `observation.next_survey_number` (§7). It is machine-derived and never reused, and it is unique across every batch the tree ever signs. Nothing derives it from the sheet's content: a content-derived id collides across re-scaffolds of an identical candidate set, and two such re-scaffolds are two batches.

**Layout.** The live sheet is `<docs_dir>/observations/survey-SVY-NNNN.yml`. The signed sheet and its receipt archive to `<docs_dir>/observations/_surveys/SVY-NNNN/sheet.yml` and `.../receipt.yml`, with a transient `staged/` beneath during publish. `_surveys/` is a frozen holding area on the `promptbooks/legacy/` model (§3): it has no index section and is excluded from every record walk. The sheet is a `.yml` so the concern's `*.md` record walks cannot see it.

**The row schema.** One row per candidate, keyed by `anchor_id`.

| cell | author | semantics |
|---|---|---|
| `anchor_id` | machine (scaffold) | The candidate's structural anchor identity (§17.1). Immutable on the sheet; an edit here breaks the digest. |
| `proposed_domain` | machine (scaffold) | The mined `governs.domain` the scaffold seeds. |
| `rule` | machine (scaffold) | The candidate's rule, seeded verbatim. Read-only; a human edit breaks the digest and the sign-off refuses. |
| `evidence` | machine (scaffold) | The candidate's evidence entries, seeded verbatim and comma-joined. Read-only on the same terms as `rule`. |
| `verdict` | human | `ratify \| reject \| defer`. Empty refuses. |
| `domain` | human | Optional override of `proposed_domain`. Empty accepts the seed. |
| `slug` | machine (scaffold) proposes; human may overwrite | The published record's slug, at `config_version` `"3"`. The scaffold proposes it; the human may overwrite it. Empty refuses a `ratify` row. |
| `rationale` | human | Free prose recording why. |

**Why the sheet carries `rule` and `evidence`.** The human signs a claim, never an anchor id. The two seeded cells sit immediately before `verdict`, so the claim is on screen beside the cell that disposes it. Both are inside the digest. A human edit to either is therefore a digest mismatch, and the sign-off refuses the batch. The sheet is no second source of truth for either cell: the published record copies the rule and the evidence from the candidate. A seeded cell that no longer matches the candidate refuses the row, which is what catches a re-mine between the signature and the publish. The split is symmetric for every cell but `slug`: a machine fills no human-authored cell, and a human fills no machine-authored cell. `slug` is the one cell both authors write; its own paragraph below covers it.

**The receipt records `domain_source` per row.** For every row the receipt carries a `domain_source` of `proposed` or `overridden`: `proposed` when the human left the `domain` cell empty and the seeded `proposed_domain` stands as the record's domain, `overridden` when the human wrote a domain of their own. It is a receipt field and never a sheet cell — the sheet carries what the human wrote, and the receipt carries what the sign-off made of it, so the seeded-or-overridden question is answerable from the receipt alone without re-reading the sheet.

**The sheet carries a `slug` cell at `config_version` `"3"`.** The scaffold proposes it and the human may overwrite it. It is the one cell both authors write. The proposal is never a claim, so overwriting it changes nothing the human signs about the candidate. At `"3"` the cell is inside the digest like every other cell. The value becomes the published record's slug on both of its surfaces — the filename stem of `OBS-NNNN-<slug>.md` and the slug half of the governs handle `OBS-NNNN/<slug>`. Its grammar is therefore the two grammars intersected: `^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$`, a lowercase letter followed by lowercase letters, digits and hyphens. The value is validated on read rather than trusted, because the two grammars differ at the first character. A digit-led slug passes the filename grammar and fails the handle grammar, and the summaries projection then fails closed for the whole tree. The sign-off refuses a `ratify` row whose slug is empty, malformed, or already taken by a live or a retired slug. The retired case refuses too: a retired slug must keep resolving to the rules that displaced it, so reusing one makes a citation ambiguous. OBS-0001 through OBS-0003 keep the slugs they have. They are bound into a signed receipt, and renaming one invalidates that signature.

**The receipt records `slug_source` per row.** For every row the receipt carries a `slug_source` of `proposed` or `overridden`, on the terms `domain_source` sets: `proposed` when the human left the proposal standing, `overridden` when the human wrote a slug of their own. The enum is `domain_source`'s enum reused, never a second one. The decision that added the cell words the receipt's question as "proposed or **human**". That word "human" is rendered by the existing `overridden` value. The concept is the one `domain_source` already names, and one name per thing wins over a second constant. Like `domain_source`, it is a receipt field and never a sheet cell — the sheet carries what the human wrote, and the receipt carries what the sign-off made of it.

**The scaffold provenance names the tree.** `scaffold_provenance` carries `tool`, `scaffolded`, `state_file`, `candidates`, `tree` and `tree_id`. `tree` is the tree's path relative to the repo root. `tree_id` is a hash over that relative path plus the bytes of the layout config naming it. Identity is therefore the tree's committed configuration and never its absolute location. The same tree cloned, renamed, or checked out on a CI runner still publishes. Both keys are inside the digest, so the receipt carries them, and the sign-off refuses a batch signed against another tree. That refusal is load-bearing because anchor ids are content-derived. Two repositories depending on one library carry the same anchor, so a batch signed in one used to publish cleanly into the other.

**The digest domain.** The digest covers the batch id, the scaffold provenance, and every row's cells, canonicalized per cell and joined in anchor order. It is one digest over the whole sheet, never one per row. `config_version` is **not hashed as a value**: no line of the preimage carries it. It is not inert either. It **selects the preimage** — the cell list and the per-cell canonicalization are both read off it. Relabelling a sheet to another version therefore hashes a different string and yields a different digest. So the marker is not "outside the digest domain" in the sense that phrase once carried here: it is not hashed, and it decides what is. That selection is what lets the cell list widen without recomputing the digest of a sheet already archived downstream.

**The v1/v2/v3 migration.** Both the sheet and the receipt carry `config_version`, validated on read. Three versions are read, `"1"`, `"2"` and `"3"`; one is written, `"3"`. Only a newly scaffolded sheet emits it. A `"1"` sheet carries five cells per row and no tree identity. A `"2"` sheet carries no `slug` cell, and its receipt carries no `slug_source`. Each still reads and still digests to the value its receipt recorded. An archived batch therefore stays CHK-OBS-SURVEY-DIGEST green across either upgrade. Publishing is another matter: only a `"3"` sheet may be published, whether that publish is a first signature or a resume. The sign-off checks the version on every publish path, so a `"1"` or `"2"` batch bound before the upgrade cannot resume either. The refusal names the cells the sheet's own version lacks: a `"1"` row lacks `rule`, `evidence` and `slug`; a `"2"` row lacks `slug`. Signing a `"1"` row would sign an anchor id. The remedy is to re-scaffold the batch with the `survey-sheet` skill.

**The state table.** This table is the protocol's source of truth. State is derived from disk on every read by one shared function, used by the sign-off's resume, the §17.3 audit rules, and the projection refusal alike — so a gate can never disagree with the writer.

| # | State | On-disk predicate | Event | Next | The one write |
|---|---|---|---|---|---|
| 1 | S0 absent | no receipt.yml | signoff, sheet valid | S1 | atomic write sheet.yml then receipt.yml with digest, sheet_ref, scaffold_provenance, rows carrying `domain_source` and, at `"3"`, `slug_source`, completed null, no records |
| 2 | S0 | — | signoff, invalid or digest refusal | S0 | none |
| 3 | S1 bound | receipt, completed null, no staged/ | signoff re-run, digest matches | S2 | allocate ids from observation.next_number, atomic-write the manifest counter, rewrite receipt rows with record_id and record_path |
| 4 | S1 | — | signoff re-run, digest differs | S1 | none — refuse, exit 1 |
| 5 | S1 | — | audit | S1 | none — WARNING inside survey_stub_days, BROKEN past it |
| 6 | S2 staged-ids | receipt has record_id per ratify row | signoff re-run | S3 | write every planned record body and the planned index.md into staged/, atomic per file |
| 7 | S3 staged | staged/ holds every planned file | signoff re-run | S4 | the commit point — one atomic write flipping the receipt to completed with the sorted record list |
| 8 | S3 | — | audit | S3 | none — WARNING or BROKEN by age; no record is visible, so the visibility rule is clean |
| 9 | S4 committed | completed set, staged/ non-empty | signoff re-run | S5 | os.replace each staged record into observations/, in sorted id order |
| 10 | S4 or S5 partial | some promoted, index stale | audit | unchanged | none — CHK-OBS-BIJECTION BROKEN; the remedy is re-running the sign-off |
| 11 | S5 records-visible | all promoted, staged index remains | signoff re-run | S6 | os.replace the staged index over observations/index.md; remove staged/ |
| 12 | S6 indexed | staged/ gone, no log op | signoff re-run | S7 | prepend one observation log op with subject `survey batch SVY-NNNN` (absence-conditional) |
| 13 | S7 logged | log op present, no journal hook | signoff re-run | S8 | append the journal hook, category review (absence-conditional) |
| 14 | S8 recorded | all surfaces present | signoff re-run | S9 | dispose the candidate state file — ratify to ratified, reject to rejected, defer writes nothing |
| 15 | S9 published | everything consistent | signoff re-run | S9 | none — a reported no-op, exit 0 |
| 16 | any of S4–S9 | a surface contradicts the receipt | signoff re-run | unchanged | none — refuse, never overwrite |
| 17 | S1–S9 | — | a downstream projection over ratified records | unchanged | none — exit 2, nothing written, while the batch is below S9 |

Row 17 is the projections' side of the same state: the per-batch receipts are one declared source in the projection's input domain, so an incomplete batch refuses to render under the existing fail-closed rule.

**Why this order.** Completion precedes visibility. Records stage where no walk sees them, and the receipt's completion lands before any record becomes visible, so no visible record ever has a receipt recording no completion. The reverse order trips CHK-OBS-SURVEY-VISIBLE on every healthy publish, which would make the rule useless. One window survives: the receipt is complete, some records are promoted, and the index is stale. CHK-OBS-BIJECTION already reports it, and the projections already refuse to render it.

**Why `defer` writes nothing to the candidate state file.** The candidate state file suppresses a `deferred` candidate unconditionally, so writing `defer` there would make the deferral permanent. Recording `defer` in the receipt alone is what makes "`defer` is the only re-scaffoldable verdict" hold mechanically rather than by convention.
