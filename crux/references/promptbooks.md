---
title: Promptbooks and historical runs
read_when: Reading, finishing or auditing a historical promptbook, run snapshot or retained demonstration holding
sections:
  - "§3 promptbook holdings and formats"
  - "§4 promptbooks"
  - "§10.A"
  - "§11 Citation conventions: promptbook book-link resolution"
  - "§11 Promptbook side-effects must be logged"
  - "§11 Historical run execution autonomy"
  - "§11.B"
  - "§11.C"
---

# Promptbooks and historical runs

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §11.B`, resolves to this file.

## Promptbook holdings and formats (§3)

**Retained demonstration holdings.** `<docs_dir>/promptbooks/runs/<complete-book-directory>/evidence/implementation-cycles/retained-repositories/` holds nonauthoritative demonstration repositories, source exports and complete Git bundles. It is not a concern and has no index section. It contributes no records, rules, artifact bindings, census/allocation counts, archive eligibility, overdue-revocation candidates, recovered anchors or current architecture to its containing project.

Anchor recognition at the containing project's canonically configured documentation root. `<complete-book-directory>` is one direct child of `promptbooks/runs/`. New authored book directories require a complete optional artifact prefix, `PB-` followed by four ASCII digits, and a kebab slug. Holding recognition also preserves historical complete prefixes and legacy slugs with leading, repeated or trailing hyphens, regardless of the current prefix. There is no hard length cap. Any other direct-child run directory carrying the exact `evidence/implementation-cycles/retained-repositories` subtree refuses with `retained-evidence-layout-refused` before descent; it never becomes an admissible source. Match the remaining components literally; substring identities never match. Recognition requires no marker, manifest entry, exclude flag, configuration key, council/close/run-status proof or extant owning book. Deleting the book must not admit retained records. A `retained-repositories` basename elsewhere is outside this contract. Do not exclude all evidence or all run directories; real bindings and gate records remain sources.

Prune this subtree before source discovery, configuration discovery, token matching, record parsing or recursive walking. Never execute or import held code/configuration merely because a normal walk encountered it. Evidence retrieval may inspect explicitly selected artifacts read-only. Reconstruct bundles in an isolated repository and query it with its own explicit root and configuration; that inspection grants no authority to the containing project. Never retain recursive `.git` directories. Existing legacy holdings remain unchanged.

New books and runs are written as structured `.yaml`. Legacy `.md` books and run snapshots remain **readable as history** (a reading skill format-detects by extension + `format_version` before parsing); a run's format is fixed at its own start from the book's format as of that start. The current distribution does not convert or execute `.md` files. Eligible archived or truthfully finishable runs may use the pinned public `v3.23.2` recovery release on a copy, with book-before-run conversion and original-byte preservation. An unfinishable run remains readable and unresolved; the tagged release has no verified deliberate Markdown-abandon path. Schema pointers: `${CRUX_PLUGIN_ROOT}/schemas/promptbook.schema.json` (book shape, SSOT for CHK-PB-1) and `${CRUX_PLUGIN_ROOT}/schemas/run.schema.json` (run/per-prompt shape, SSOT for §11.B), validated by `${CRUX_PLUGIN_ROOT}/scripts/validate-promptbook.py`. **`format_version`** is a third, independent version axis (a per-file on-disk-format signal, value `"1"` or `"2"`), deliberately distinct from `docs/manifest.yml`'s tree-layout `schema_version` (§7) and `plugin.json`'s SKILL.md-contract `schema_version` (§7.A) — it governs the intra-file structure of one promptbook/run document and is also the `.md`↔`.yaml` coexistence discriminator.

New cycle books use format two; each run inherits its book's format at start.
Format-one records retain their original structure and cycle classification.
Never convert a live or archived record implicitly. Council evidence versions
and approval profiles are separate axes; §11 states their execution rules.

### promptbooks (mutable plan, immutable runs)
- Active book is **mutable narrative**. The prompts list is mutable *only between runs*. To change the plan mid-run, abandon the run and author a successor book that cites its predecessor in prose — the mid-run fork path is deleted, and `forked_from` remains an accepted field that is always `null` and that nothing writes.
- Run snapshots are **append-only after creation**. Only state/timestamp/result/artifacts fields update.
- **Implementation Decisions (run-local).** The author of the implementation module, of an iterate verify module with a declared slot, or of a patch verify phase with a patch slot, writes each revision from `implementation-decision-template.yaml` under `promptbooks/runs/<id>-<slug>/implementations/<RUN-NNN>/<slug>/`. A gate advance records its approval binding in the run snapshot. `implementation-decisions.py` validates records, writes `result-NNN.yaml` and `annotation-NNN.yaml`, and answers `query`; nothing else writes them. Reviewed revisions are immutable, and a later revision or a replacement cycle never edits, revokes or supersedes an earlier one. Results and annotations are append-only. The record schemas are the only definition of their shape; this file restates none of it. Writer and query results declare `authority: none`.
- Archived books are immutable. **Immutability is by content, not file extension**: an earlier tagged release converted eligible `.md` records to `.yaml` while preserving originals byte-for-byte under `docs/promptbooks/legacy/`. The current distribution never converts a live or archived Markdown record.
- `docs/promptbooks/legacy/` holds the preserved pre-migration `.md` originals (mirroring `archive/` + `runs/<id>-<slug>/`). It is a frozen holding area, **not a concern surface**: no `docs/index.md` section, excluded from every CHK-PB-* walk (its only audit coverage is CHK-PB-LEGACY). Written by earlier migrations; the current distribution does not add files there.
- Skills: `author-promptbook`, `dev-cycle`, `iterate`, `patch-cycle` (the three cycle tiers, §11.C), `fix-directly` (the rung below the tiers — no book, §11.C), `run-promptbook`, `archive-promptbook`. `run-promptbook` status renders the progress bar and answers "where am I?" over a run snapshot and book without advancing.
- Triggers: "new promptbook", "patch this", "run", "advance", "next prompt", "abandon this run", "archive promptbook", "show the run", "show run progress", "where am I / what's next on PB-NNNN" (via `run-promptbook` status). Requests to convert legacy Markdown route to the versioned recovery guidance; the current distribution has no converter.

## 10.A. Historical skill orchestration cheat-sheet

For new work, use the current cycle contract in §11.E. The routes below describe
legacy promptbook workflows and do not authorize new books or repeated runs.

The patterns below describe how the agent-team skills compose in a session.

### Full agent-team pipeline

```
1. CREATE IDENTITY      → retained identity API (`box/runtime-apis.md`)
2. LEARN FROM EXPERTS   → retained identity API
3. PLAN TASKS           → whiteboarding / author-promptbook
4. DECIDE ARCHITECTURE  → council runner (cycle gate) / council skill (ad hoc)
5. CHECK SEMANTIC GAPS  → retained probe API (`box/runtime-apis.md`)
6. EXTRACT LEARNINGS    → retained identity API
```

### Quick reference — situation → skill → key API

| Situation | Skill | Key Function/Class |
|-----------|-------|--------------------|
| Call an LLM | `call-llm` | `call_model()`, `call_claude_opus()` |
| Log reasoning | `box/runtime-apis.md` | `get_tracer()`, `log_reasoning()` |
| "Should I use A or B?" | `council` | `create_async_council()` → `council.deliberate()` |
| A council gate inside a run | `run-council.py` (the council runner) | Its council record is the gate evidence; the ad-hoc async council satisfies no gate. |
| Models disagreed on an `iterate` cycle's verify path | `srde` | `create_srde()` → `srde.attempt_resolution()`. An evidence tool, never a gate; it never runs on the ADR path. |
| Plan a large feature | `author-promptbook` or applicable cycle | Retained `decompose_goal()` API in `box/runtime-apis.md` |
| About to run a probe | `box/runtime-apis.md` | `SemanticBridge()` |
| Starting a session | `box/runtime-apis.md` | `get_or_create_identity()` |
| Generate a runbook explicitly | `box/operator-services.md` | `uv run "${CRUX_PLUGIN_ROOT}/scripts/crux/runbook/__main__.py"` |

### Async-first rule

Every council/SRDE call inside an agent team MUST use the async variant where one exists. `create_async_council()` → `await council.deliberate()`. Wrap sync-only callsites in `asyncio.to_thread()`. 5 parallel teammates × 5 concurrent LLM calls — blocking eats the wall-clock budget.

The rule covers the ad-hoc async council only. A council gate inside a run uses the council runner, `run-council.py`, never the ad-hoc async council; the council runner is the only source of council gate evidence.[^council]

**Any** `crux.*` import needs the LLM-router dependency — not just council/LLM-router calls. Importing *any* submodule executes `scripts/crux/__init__.py`, which imports `council` → the LLM router; that chain pulls in `httpx`, the HTTP client. Bare `python3` lacks it and dies with `ModuleNotFoundError: No module named 'httpx'`. So even nominally stdlib-only runtime APIs (`srde`, the probe bridge, and identity) need `uv`. That dependency is supplied by **PEP 723 inline script metadata + `uv run`** — no `PYTHONPATH`, no project extras, no surrounding project:

- **Shipped runnable scripts are self-describing.** Every script whose documented invocation is `uv run …` carries a PEP 723 inline-metadata block; the canonical invocation is `uv run "${CRUX_PLUGIN_ROOT}/scripts/<entry>.py" …` (module entry points: `uv run "${CRUX_PLUGIN_ROOT}/scripts/crux/<module>/__main__.py" …`). In a source checkout, where `${CRUX_PLUGIN_ROOT}` is unset, substitute the checkout's plugin directory — the same form works there because inline metadata makes `uv` ignore the surrounding project.
- **API-style usage (Python snippets importing `crux.*`)** uses the **PEP 723 driver pattern**: write your driver to a temp `.py` starting with the standard block

  ```python
  # /// script
  # requires-python = ">=3.11"
  # dependencies = ["httpx>=0.27"]
  # ///
  import sys
  sys.path.insert(0, "/REPLACE/WITH/PLUGIN/ROOT/scripts")  # the actual ${CRUX_PLUGIN_ROOT} value — Python won't expand env-var syntax
  ```

  then your imports; write the driver into a private per-run directory and run it from there — `d=$(mktemp -d) && uv run "$d/driver.py"` (never a fixed shared path like `/tmp/driver.py`; predictable /tmp names are a symlink/TOCTOU hazard). Add `fastapi`/`uvicorn` to the list for the retained HTTP service (`box/operator-services.md`).
- **uv-less failure mode, stated honestly:** under `uv run …`, a machine without `uv` fails at the *shell* — `command not found: uv`, exit 127; the script never executes. Remediation: install uv (https://docs.astral.sh/uv/). The **exit-2 capability lane remains as defense-in-depth for the bare-`python3` invocation style**, where the script DOES run and self-repairs or exits 2 honestly (see below).
- **No state is ever written under `${CRUX_PLUGIN_ROOT}`** — it is ephemeral across plugin updates; anything persistent belongs in `${CLAUDE_PLUGIN_DATA}` or the user-home `~/.crux/` directory.

**Broader rule: invoke EVERY crux script via `uv run` — `uv run "${CRUX_PLUGIN_ROOT}/scripts/<script>.py" …`** — not only the `crux.*` importers. The YAML-parsing scripts (`validate-promptbook.py`, `visualize-run-progress.py`) **require a real YAML parser**: the `_yaml_min` minimal fallback silently diverges from PyYAML outside its subset (which would poison `book_content_hash`), so those scripts refuse the fallback outright. Their PEP 723 blocks declare PyYAML, so the canonical `uv run` invocation always has it. The bare-`python3` lane stays honest as defense-in-depth: without PyYAML they (a) announce and re-exec themselves under `uv run --no-project --with pyyaml` when `uv` is on PATH (cwd-independent; loop-guarded by `CRUX_UV_REEXEC`; opt out with `CRUX_NO_UV_REEXEC=1`), or (b) exit **2** with a `YamlCapabilityError` remediation on stderr — the pre-existing *crash* lane of the script convention, deliberately distinct from exit 1's findings-JSON, so an environment problem can never read as "your docs are broken." The floor is honest: with neither PyYAML nor uv available, nothing is auto-repaired — you get the loud capability error. (Dependency resolution — for the PEP 723 blocks and the re-exec's `--with pyyaml>=6.0` alike — intentionally trusts the user's configured uv index and may touch the network on first use; hermetic CI should pre-provision and, for the bare-python3 lane, set `CRUX_NO_UV_REEXEC=1`.)

### Confidence-gated execution

The canonical confidence-gated-outcomes table now lives in `forge-skill`'s SKILL.md (inherited discipline; canonical table in `${CRUX_PLUGIN_ROOT}/skills/forge-skill/SKILL.md`); see that file for the thresholds and actions. For deliberation results (council/review verdicts) the same thresholds map to: ≥85% ship; ≥70% ship with caveats noted in the journal; ≥50% get an independent check; <50% STOP and escalate to a human.

#### Promptbook book-link resolution (single source of truth)

This block is the **single source of truth** for resolving a promptbook **book** wiki-link; `audit-docs` CHK-JR-4 (both the inline rule and the Explore-agent item) references it by §-name rather than restating it. A book-link resolves iff a book with the referenced **`PB-NNNN` id** (per the §14.3 dual-form prefix regex) exists under `docs/promptbooks/active/` **OR** `archive/` (union; `legacy/` excluded). The **id is the sole authoritative match key**; the slug AND the `active/`|`archive/` path segment are both **non-authoritative hints** (the ADR-parity model — §9 cites ADRs id-only). Three spellings resolve: `[[promptbooks/(active|archive)/PB-NNNN-<slug>]]` (legacy), `[[promptbooks/PB-NNNN-<slug>]]` (lifecycle-neutral, the canonical write form), and `[[promptbooks/PB-NNNN]]` (id-only). A stale-slug legacy link (id matches, slug drifted) still resolves — a cosmetic slug typo is tolerated, not dangled. **Run**-links (`[[promptbooks/runs/<book>/run-RUN-NNN]]`) are matched FIRST and keep **exact-path** resolution (`runs/` never moves).

### Promptbook side-effects must be logged
A promptbook step may emit ADRs, journal entries, or research pages as side-effects. The run snapshot's per-prompt **Side effects** and **Artifacts** lines MUST list every such emission. `audit-docs` cross-checks: a journal entry citing a promptbook must appear in that book's run snapshot's artifacts.

### Historical run execution autonomy (promptbooks)

Once a run is started (`run-promptbook start` against an approved book), the runner advances through the prompts to completion. **The plan is the authorization** — a prompt's instructions are pre-approved work, not a proposal awaiting per-step confirmation. An accepted ADR + an approved promptbook prompt + a "start running" instruction is the maximal pre-authorization that can exist; pausing inside it to ask permission signals a problem where there is none and stalls the run.

The **only** legitimate mid-run stops are:

1. **A module escalation loop fires** — 3-round non-convergence on a council, a quality-gate loop, or a review fix-loop; or the preflight retry sequence (a third preflight refusal at one convening prompt). STOP and escalate to the user per the module contract.
2. **A genuinely irreversible or outward-facing action the plan did NOT already authorize** — pushing/merging git, deploying, sending an external message, deleting data outside the repo, spending money, publishing. Editing in-repo files — **including `docs/AGENTS.md`, skill files, and code** — is **not** this, however important the file feels: it is version-controlled, internal, and reversible.
3. **The prompt's own instructions explicitly say to pause** for the user.
4. **New information contradicts the plan's premise** (e.g. a cited ADR turns out to be Superseded) — surface it; don't silently proceed.

Do not stop to confirm a step the plan already authorizes. **If you find yourself about to confirm a mandated in-repo edit, that is a red flag that you are misclassifying internal work as outward-facing** — re-read this section and proceed. This contract governs `run-promptbook` and `dev-cycle`; both skills' red-flag tables reference it.

#### Council and review gates

Council deliberation and independent review are two processes with two gates, and neither satisfies the other's gate.[^council][^review] The gate check in `advance-run.py`, never the conductor, decides whether a council gate passes, routes to its address-findings prompt, or stops.[^gate] A held round, a tied or misnumbered round, a council at an adr module's round 3, a round above three that no owner-exception record authorizes, and a third preflight refusal at one convening prompt are each an instance of stop 1. A council that cannot run, a subject the conductor may not repair (`preflight-needs-owner`), an open council attempt, a record-order stop (section 8 of the gates reference), a round whose write the secret scan refused, and an implementation or verify council's `ARCHITECTURAL` escape verdict are each an instance of stop 4.[^defer] Record order is committed order, never a record's `written_at`. The council runner commits the attempt record and the council record itself. It commits the attempt record before any council request, and a council record counts only when its committed bytes are the bytes the council runner computed.[^attempt] A preflight refusal is raised before any council request. A preflight refusal the conductor may repair writes no council record. The conductor repairs the input (retype the path, or commit a subject this run wrote with `run-work-witness.py commit`) and runs the council runner again. The council runner refuses a `--prompt` that is not the run's current prompt (`"refused": "prompt"`), so the retry count always names the prompt the run is at. When the council runner exits 2 and stderr names `timeout`, or names outside work the commit moved, the conductor reports a contradicted-premise stop for the owner. The owner first restores any work a hook set aside (`git stash list`, or the hook framework's backup patch), then removes a stale `index.lock` in the git directory. After the owner reports both steps done, and after any other exit 2, the conductor runs the process check. The process check confirms that no council runner it started for this module is still running. The conductor then probes the attempt's lock with `run-council.py --recover <run> --prompt <n> --probe`. Once no live runner holds the lock, it runs `run-council.py --recover <run> --prompt <n>`, which makes no council request. A persistence failure is never a reason to convene another round.[^attempt] A commit that exceeds the council runner's 120-second bound (a slow hook) refuses with `timeout` and leaves the attempt open, so the owner's remedy comes first. Hooks that rewrite a council file must exclude `<docs_dir>/promptbooks/runs/`; otherwise each council commit whose file the hook rewrites fails closed (`hook-or-commit-failed`, or `mismatch` when the hook re-stages its rewrite). A stopped gate starts no further prompt, and the run stays in progress until the owner acts. For a could-not-run stop, that wait holds by prose. The `run-promptbook` skill's `references/gates.md` holds the procedure and states what the check cannot see.

**Execution formats and retained approval.** Book and run format versions remain independent of council records and approval profiles. Both book formats use the current attempt-aware gate. New council records use format two; attempt records use format one. Legacy council records require the gate's committed pre-cutover run-start proof. New formal closes retain context three with approval profile four. Historical context two/profile three and context one/profile two stay immutable and support historical replay only. Never select an approval profile from a book's format or substitute the live registry for retained context. Unknown or inconsistent context refuses approval. A format-two close publishes DONE, its binding and retained context through `advance-run.py`; commit them before a consumer reads them. Raw receipts or a DONE state alone establish no approval. Approved intent, independently reviewed delivery and source facts remain separate.

**Write-time witness and ownership.** Immediately after each initial or revised council subject write, record its run-work witness. This includes Implementation Decision revisions. Never create a witness after a refusal to claim ownership. A later advance changes snapshot bytes without renewing the earlier witness; commit the current snapshot before convening. The council runner and recovery own attempt/result commits; a parent commit cannot substitute. Finish an open Git sequence before any council request. Use the exact implementation-revision selector, role, declared slot, path and digest; a retained artifact in another role grants no approval. The `--migration-batch` selector is retired: `run-council.py` and `advance-run.py` refuse it with `historical-migration-writes-retired`. Follow `run-promptbook/references/gates.md` for the supported commands and refusal/recovery procedures.

Record each subject at write time with the existing writer:

```bash
uv run "${CRUX_PLUGIN_ROOT}/scripts/run-work-witness.py" record <run-RUN-NNN.yaml> --prompt <n> --path <subject-path>
```

## 11.B. Run-snapshot per-prompt shape — lifecycle prose + schema pointer

The **single source of truth for the per-prompt SHAPE** is the JSON Schema `${CRUX_PLUGIN_ROOT}/schemas/run.schema.json` (draft 2020-12) — `run-promptbook` (writer), `archive-promptbook` (precondition reader), and `audit-docs` (CHK-PB-SCHEMA + CHK-PB-9 + adjacent) MUST reference that schema by name rather than restating the field list. This mirrors how §11.A references the ADR template and how `promptbook.schema.json` is the SSOT that CHK-PB-1 references. This section keeps **only the prose the schema cannot express** (the lifecycle, the archival-terminal rule, the autonomy cross-ref) plus the title-case→snake_case field-name mapping.

For new-format `.yaml` snapshots (`docs/promptbooks/runs/<id>-<slug>/run-RUN-NNN.yaml`), each prompt is one element of the top-level `prompts:` array, validated against `run.schema.json` (and the `n == index+1` / contiguous-from-1 invariant by the validator's post-schema pass). The **legacy `.md` form is still validated by the regex path** — a `## Prompt N — <title>` heading followed by bulleted `- **Field:** value` lines — to read archived and stranded Markdown history; CHK-PB-SCHEMA dual-paths (schema for `.yaml`, regex for `.md`). Validation does not authorize current-version Markdown mutation.

**Field-name mapping (title-case Markdown labels → snake_case YAML keys).** The bulleted-Markdown labels of the legacy form map to YAML keys on the schema-defined `prompts[]` element:

| legacy `.md` label | `.yaml` key (in `run.schema.json`) | note |
|---|---|---|
| `State` | `state` | enum lowercased: `pending \| running \| done \| skipped \| blocked` |
| `Started` | `started` | ISO 8601 UTC \| null |
| `Completed` | `completed` | ISO 8601 UTC \| null |
| `Result` | `result` | Markdown string; `""` when empty (the legacy `—` placeholder is NOT carried into YAML; validators MAY accept `—` only on `.md` reads) |
| `Artifacts` | `artifacts` | array of `docs/` path strings; `[]` if none (normalizes the legacy CSV cell into a real list) |

**Lifecycle prose (not expressible in draft-2020-12 — kept here):**
- `pending` → `running` → one of {`done`, `skipped`, `blocked`}.
- **A prompt's terminal states are `done`, `skipped`, and `blocked`.** There is no per-prompt archive-eligibility flag: a run holding a `blocked` prompt still reaches `status: completed` once no `pending` prompt remains.
- **Archive eligibility is a property of the RUN, not of any prompt.** A book may archive only via its `current_run`, and only by one of exactly two paths. The pointer this rule reads SURVIVES a run reaching either terminal status — `current_run` is not erased when a run completes any more than when it is abandoned; `archive-promptbook` is the sole writer that nulls it, and only at archival.
  1. **Delivered** — the run has `status: completed` AND every prompt is terminal.
  2. **Abandoned** — the run has `status: abandoned` AND `abandonment.kind: deliberate`. Its prompts may be `pending`, `running`, or `blocked`; the non-terminal prompt left behind is the record of how far the run got.

  Everything else refuses: `status: in_progress`; `status: abandoned` with `abandonment.kind: superseded`; and `status: abandoned` with no `abandonment` mapping at all.
- **`abandonment: {kind, at, reason}`** is the run-level record. `kind: deliberate` is written by `run-promptbook`'s abandon mode and is the archive-eligibility signal. `kind: superseded` is written when a later run's start rolls over a stale run, and **confers no eligibility** — the two share a `status` and are told apart only by `kind`. The record is written at the moment the abandonment is taken and is **never retrofitted**, so a run that ended without one cannot be made eligible after the fact.
- **`base_commit`** is the run's commit boundary: 40 lowercase hex from `git rev-parse HEAD`, or `null` outside a git work tree, written once at run start and never rewritten. It exists so the `patch` tier's archive check can draw a run's changed paths from the repository's own change record rather than from anything the run wrote about itself (§11.C). A `patch` run whose `base_commit` is `null` cannot archive as completed.
- This lifecycle runs under the **§11 "Run execution autonomy"** contract — the plan is the authorization; do not pause inside a started run except for the stop-points §11 enumerates.

**Run-level shape** (top-level keys of the run document — `format_version`, `run_id`, `book_id`, `book_content_hash`, `started_at`, `completed_at`, `status`, `current_prompt`, `base_commit`, `abandonment`, `prompts`, `notes`, `pr_draft`, `summary`) is owned by the same `run.schema.json`. The **`book_content_hash` binding** ties a run to the exact plan text it executed (recomputed by the validator; mismatches surface via CHK-PB-BIND). Note the **three distinct enums** across the book↔run pair: book `status: active | archived` (§3), run `status: in_progress | completed | abandoned`, and per-prompt `state: pending | running | done | skipped | blocked` — do not conflate them.

## 11.C. Historical cycle tiers and the `patch` blast radius

A format-two cycle book declares one of four cycle kinds across three ceremony tiers. Each kind has an authoring skill, count formula and floor:

| `cycle_kind` | skill | shape | formula | floor |
|---|---|---|---|---|
| `adr` | `dev-cycle` | A ADR + I implementation + D dev + R review modules, plus prep + summary | `4(A+I)+4D+3R+2` | 13 |
| `implementation` | `dev-cycle` | I implementation + D dev + R review modules, plus prep + summary | `4I+4D+3R+2` | 13 |
| `verify` | `iterate` | V verify + D dev + R review modules, plus prep + summary | `4V+4D+3R+2` | 13 |
| `patch` | `patch-cycle` | five phases, one prompt each | the constant `5` | 5 |

Architectural kind requires A≥1 and V=0; I may be zero. Implementation kind
requires I≥1 and A=V=0. Verify kind requires V≥1 and A=I=0.
All counts are nonnegative integers; D and R are at least one.
Module cycles keep their thirteen-prompt floor and two final untagged prompts.
Patch remains the five-phase tier. Direct fixes retain their existing path.

A combined architectural book dispatches council by its structural module kind,
never by a council kind named `combined`. A replaceable choice under unchanged
architectural constraints needs no ADR. Preserve each earlier Implementation
Decision without revocation, deprecation or supersession. Formal decisions require
a declared slot and exact-revision council approval at their existing gate.
An empty `implementation_slots` list permits incidental choices.
Reviewed intent, independently reviewed delivery and queried source facts remain
separate. Implementation reasoning supplies no governing authority.
Format-one books and runs retain their original cycle interpretation.

**Below the tiers: the direct fix.** A defect that passes `fix-directly`'s sizing test — its files nameable now, a failing test writable before the fix, no contract changed, one instance, no review gate wanted — is fixed with no book, no council, and no `PB-NNNN`. Its record is the regression test, the commit, and one `log-work` entry with the `fixed directly:` title prefix, which is how `retrospective` sees it. This is not a fourth tier: it authors no book, so no floor and no formula apply. A security label on a defect sets its priority, not its size. Guidance text is no contract for that sizing test. A change to guidance or instruction text needs no ADR while every binding rule still holds.[^guidance-cheap]

A `patch` book runs five phases **in order — verify, plan, implement, review, summary**, carried on each prompt's `phase` field. It carries no `modules` block and no `module_tag` on any prompt. The council gate is a postcondition of the verify phase and the review gate a postcondition of the review phase, both positional, so a `patch` book that archives a completed run has passed both. `validate-promptbook.py`'s cycle-coverage pass machine-checks the count, the phase sequence, the absence of module tags, and the blast radius.

### The blast radius

A `patch` book declares its blast radius as a set of repo-relative repository paths in `blast_radius`, before its run starts. Two guards hold it, and only the second is mechanical:

1. **Proportion** — the verify phase's council reviews the declaration against the change and refuses the patch framing when it is drawn wider than the work needs.
2. **Containment** — `archive-promptbook`'s precondition runs `crux/scripts/check-blast-radius.py`, comparing the declaration against the paths the run actually changed.

**The evidence source is git, and never anything the run authors.** The changed set is `git diff --name-only --no-renames <base_commit>` (base to working tree) union the untracked files, where `base_commit` is the boundary `run-promptbook` stamped at run start (§11.B). Neither the snapshot's `artifacts` nor its `notes` is consulted. `--no-renames` is required for correctness. With rename detection on, git reports only a rename's destination, so moving a file out of an undeclared path into a declared one presents one declared path while the undeclared source disappears.

**One value does come from the run, and it is pinned rather than trusted.** That value is `base_commit`. Two ends enforce the pin, and both are load-bearing. `advance-run.py` refuses to write a snapshot whose `base_commit` differs from the value in that snapshot's own committed version, because moving it forward shrinks the diff the check draws. `check-blast-radius.py` refuses to pass such a snapshot, because a run that overshoots can commit its work, hand-edit `base_commit` forward, and archive without ever calling the writer — and the gate then drew its diff from the new base and passed with an empty changed set. The comparison has one implementation, `base_commit_pin.divergence`, so the two ends cannot disagree about what the committed record is. The pin compares against the snapshot's version at HEAD, so it refuses an uncommitted edit only: a rewrite committed to HEAD passes it, and the archive check then reads the rewritten value. Before the snapshot's first commit nothing holds the value, so the gate check reads an edit made then as the run-start value. After that commit, the gate check reads `base_commit` from the snapshot's first committed version and refuses a later rewrite of that field alone, committed or not.

**Both ends must read the same repository.** The diff is drawn through the repo root the check is given, while the pin reads the committed record through the snapshot's own directory. When those are two different repositories, the pin compares a decoy repository's record against itself and holds nothing. So the check refuses a book or run document lying outside the repo root, in the same fail-closed lane as a repo root that is not the work-tree top.

**The declaration is fixed once the run starts, and no prompt may widen it.** `blast_radius` is inside the frozen-plan subset that `book_content_hash` covers, so widening it mid-run moves the hash. `check-blast-radius.py` recomputes that hash itself and refuses on a mismatch. It has to: it reads the *live* declaration, and CHK-PB-BIND is an audit rule that the archive path never runs, so a freeze checked only by audit bought nothing at the gate that consumes it.

**The declared-path grammar has one implementation** — `invalid_blast_radius_entry` in `crux/scripts/validate-promptbook.py` — shared by the authoring validator and the archive check so the two give the same verdict. Its rejections are stated there and are not restated here, in any audit rule, or in any skill.

**The bookkeeping exclusion set** — the paths the run machinery writes while running *this* book, so they are not "the paths the run changed". A changed path is excluded when it is under `<docs_dir>/journal/`, `<docs_dir>/log/` or `<docs_dir>/arch/`; when it is exactly `<docs_dir>/log.md`, `<docs_dir>/index.md`, `<docs_dir>/manifest.yml`, `<docs_dir>/whats_next.md`, or `<docs_dir>/promptbooks/index.md`; or when it is this book's own run directory or its own plan file under `active/` or `archive/`. Under `promptbooks/` the exclusion is book-scoped rather than blanket: another book's plan and every archived book must reach containment, because a blanket exclusion hid edits to records that are immutable or belong to other work. Everything else must be covered by a declared entry, where an entry covers a path that equals it or lies under it as a directory prefix. **An ADR path is deliberately not excluded:** a patch that writes an ADR fails containment, which is the intent — work that needs an ADR is not a patch.

**`<docs_dir>/manifest.yml` is the exclusion set's known blind spot.** It is excluded because its counters move on every allocation, and it also carries this tree's governance config — `concerns_enabled` and `adr.spec_rule_from`. A patch that changes how the tree is governed therefore passes containment unremarked. Nothing mechanical closes this; the verify council is the only reader that can.

**A `.gitignored` path is the exclusion set's second blind spot.** Both evidence commands exclude ignored files, so a patch that writes one is never compared against the declaration and the check reports clean. The verify council is again the only reader that can catch it.

**When containment fails**, the run does not archive as completed work. It is abandoned and the work re-authored in whichever non-patch tier fits — `iterate` when the diagnosis still holds, `dev-cycle` when the overshoot revealed a decision. The overshoot stays legible in the run record, and no overshot book is stranded open.

**The honest limit:** containment is machine-checked, proportion is a council judgment. A blast radius waved through by the council passes the containment check for free. That includes a declaration wide enough to cover the cycle machinery itself, which no mechanical guard can close — the check that would refuse it is code the patch would be licensed to edit. The verify council must challenge any declaration reaching the validator, the archive check, or the schemas.

[^council]: rule:council-is-never-harness-native, rule:council-gate-needs-a-runner-record
[^review]: rule:review-gate-needs-a-reviewer-report
[^gate]: rule:gate-reads-every-recorded-round, rule:convergence-is-derived-per-seat, rule:a-seat-without-a-blocking-finding-holds-the-gate, rule:council-gate-advances-on-convergence-or-refutation, rule:blocked-gate-needs-evidence
[^defer]: rule:only-a-preflight-refusal-is-retried
[^attempt]: rule:an-open-council-attempt-stops-the-gate, rule:council-evidence-matches-its-attempt, rule:recovery-never-deliberates-again
[^guidance-cheap]: rule:guidance-edits-need-no-adr, rule:guidance-is-no-sizing-contract
