---
title: Invariants concern
read_when: Proposing, ratifying, checking or auditing an invariant pin
sections:
  - "§15"
---

# Invariants concern

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §15.2`, resolves to this file.

## 15. The invariants concern

The seventh concern, **invariants** — pinned, ratified, executable statements of *what must be true*, verifiable against regeneration. This section is the **single source of truth** for the concern's contract; the skills (`recover-invariants`, `transition-invariant`) and `audit-docs` (the CHK-INV rules) reference it by name rather than restating it.

> **Enablement:** the invariants concern is enabled only at `schema_version: "5"` (see §7). While the tree is at `"3"` this section is the *defined-but-not-yet-enabled* contract; enabling it (adding `invariants` to `concerns_enabled`, creating the surfaces) is the breaking `"3"→"4"` migration.

### 15.1 The pin and its two projections

An **invariant** is the durable pinned concept. It has an `id` and projects into two artifacts keyed by that id:
- a **ledger page** (human-readable: intent, `class`, the *why*-link) under the invariants concern at `<docs_dir>/invariants/<slug>.md`; and
- **zero-or-more checks** (the executable form) under the `invariants/checks/` subdirectory.

The invariant is neither the page nor the check; both are projections of the pin.

**Cardinalities:** pin ↔ ledger page is **1:1** (bijective — a pinless page or a duplicate id is BROKEN). pin → checks is **1:many (0..N)** — an `observed` pin legitimately has zero checks; one check traces to exactly one pin (an orphan check is BROKEN).

**Authority:** the **ledger page frontmatter is the source of truth** for a pin's identity, `class`, `provenance`, and `ratification`. The reconciliation manifest (§15.4) is *derived* for the check→pin mapping and *authoritative only* for each check's `last_result`/`last_checked`. On divergence, the ledger wins and `audit-docs` flags it BROKEN.

### 15.2 Canonical ledger frontmatter schema

Required keyset on every `<docs_dir>/invariants/<slug>.md` (the canonical contract `audit-docs` enforces):

| field | type | notes |
|---|---|---|
| `id` | string | `INV-NNNN` (4-digit, zero-padded; optional artifact prefix per §14.3). Matches the pin; unique. |
| `class` | enum | `data \| shape \| behavior \| contract \| experience` (the five invariant classes). |
| `provenance` | enum | `authored \| recovered \| reconstructed` (origin). |
| `ratification` | enum | `observed \| ratified \| rejected \| retired`. Machine-recovered pins enter `observed`; only a human transitions (§15.3). |
| `verification` | mapping | v1 field `last_result` ∈ `pass \| fail \| stale \| none` (the aggregate per §15.4). Strength grades are a deferred follow-on. |
| `related_adrs` | list | the *why*-link; ADR ids or `[]`. |
| `related_briefs` | list | brief slugs or `[]`. |
| `checks` | list | `check_id`s in the suite (possibly empty). |

The four ladder names (`observed-unratified`, `recovered-and-ratified`, …) are **derived rendering views** over (provenance, ratification, verification), never stored enums.

### 15.3 Safety invariant: machine proposes, human disposes

Recovery is autonomous but **cannot self-ratify**. Anything a machine extracts enters `provenance: recovered, ratification: observed` and nothing else. Only a human transitions `observed → ratified | rejected`, and `ratified → retired` (retirement is explicit). Two skills implement the split:
- **`recover-invariants`** (machine) — mines code, emits *candidate* checks into `<docs_dir>/invariants/checks/`, writes `observed` ledger stubs at recovery time (so no candidate is invisible), records provenance/verification in the reconciliation; never sets `ratified`.
- **`transition-invariant`** (human gate) — the `observed → ratified | rejected` and `ratified → retired` state machine; mirrors `transition-adr` (frontmatter-only mutation, bidirectional/audited write). Trigger phrases route to it.

### 15.4 Reconciliation manifest + pin-level aggregation

The reconciliation manifest, `reconciliation.yml`, lives at `<docs_dir>/invariants/reconciliation.yml` — beside the ledger, NOT inside `checks/` — and is the single reconciliation surface `audit-docs` reads. One **entry per check**, v1 shape:

```yaml
{ check_id: <stable path/id in <docs_dir>/invariants/checks/>, pin_id: INV-NNNN, last_result: pass|fail|stale|none, last_checked: <ISO date|null> }
```

The check→pin mapping is derived (regenerable); `last_result`/`last_checked` are authored data persisted here (crux is **not** a test runner — a human/CI annotation or a check's recorded exit sets them). A **resolvable check** = a `check_id` present in `<docs_dir>/invariants/checks/` whose entry maps to an existing pin.

**Pin-level aggregation** (a pin with 0..N checks): `fail` if any check is `fail`; else `stale` if any is `stale`; else `pass` if ≥1 is `pass` and none fail/stale; else `none`.

### 15.5 Audit rules (owned by `audit-docs`; stated here as the contract)

- **CHK-INV-BIJECTION** — pin↔ledger 1:1; pinless page, duplicate id, or reconciliation entry naming a pin with no ledger page → BROKEN.
- **CHK-INV-ORPHAN-CHECK** — every check resolves to exactly one existing pin; a check tracing to no/missing pin, or a `check_id` absent from the suite → BROKEN.
- **CHK-INV-DECORATION** — a `ratified` pin with no resolvable check OR aggregate `last_result: none` → BROKEN (a trusted pin nothing proves). An `observed` pin with zero checks is NOT flagged.
- **CHK-INV-FAILING** — a `ratified` pin whose aggregate is `fail` → BROKEN; `stale` → WARNING.
- **CHK-INV-DANGEROUS** — an `observed` pin with aggregate `last_result: pass` → WARNING (a green check that may be cementing unratified behavior). Plus **survey-debt**: the count of `observed` pins per region, surfaced (never as a coverage percentage).
