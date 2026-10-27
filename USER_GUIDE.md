<!-- generated-from: USER_GUIDE.md@sha256:4b36f15548b739033f1cb1090c1e49bb2ccf8a3091e6406d9c36da89d8e479d2; model: claude-sonnet-5.5; date: 2026-10-27 -->
# Working with `bionic/` in your project

Your project keeps its documentation in `bionic/`: seven concerns, plus the two default-on surfaces `arch` and `observations`, all maintained by the `crux` Claude Code plugin. **You do not write these docs by hand.** You curate, decide, and discuss. Claude does the bookkeeping.

This guide is for humans. If you are an LLM agent working in a project that uses crux, read `bionic/AGENTS.md`. That is the operational schema.

---

## Working with a standalone guide

Say "install micro-crux" to add the self-contained `micro-crux.md` guide to an
existing Crux project. It explains the philosophy, where to recover context,
supported schemas, authorized manual record maintenance, and useful inbox notes.
An agent can use it with ordinary repository tools when Crux is unavailable.
Local instructions and genuine approval requirements retain their meaning.

Installation is opt-in. It copies the shipped guide to the project root and
adds an explicit read instruction in a managed root `AGENTS.md` region. An
unchanged repeat writes nothing. An update replaces managed unchanged bytes;
local guide or pointer edits remain intact and produce a conflict to resolve.
Instruction text outside the managed region stays under your control.

The pointer reaches harnesses that read root `AGENTS.md`. A harness that reads
only a Claude instruction file needs its owner to add an explicit read
instruction. Existing Claude instruction files stay intact; the installer reports the applicable
restriction instead of claiming automatic inclusion. Installation metadata
under the configured tree records ownership and interruption recovery only.

## Working in cycles

Say "start a cycle", "quick fix", "refactor this", or "release cycle". Crux uses
one undertaking with a visible plan, tasks, phase, pass count, evidence, and history.
There is no prompt minimum or repeat run. Pausing and resuming keeps the same cycle.

| Type | Sequence | Pass limit |
|---|---|---:|
| dev (major change) | Plan → Build → Test → Review → Reflect | 7 |
| iterate (minor change) | Plan → Build → Test → Review → Reflect | 2 |
| refactor (nonfunctional improvement) | Plan → Build → Test → Review → Reflect | 7 |
| simplify (remove complexity, keep behavior) | Plan → Build → Test → Review → Reflect | 3 |
| quick-fix (bounded correction) | Build → Test → Review → Reflect | 1 |
| release (one fixed step list, beta or official) | Release | none |

Limits include the initial attempt. Tests and blocking review findings return to
Plan, or Build for quick-fix. Crux pauses sooner if progress stalls; extra passes
need your approval. Changing type preserves history and pass count.

Dev requires a council-approved IDR. Simplify requires an approved selection IDR that
names the proposals to build. Other types need one only for material choices.
A cycle can propose an ADR after council justifies its creation; approving the draft
is a separate council decision. Acceptance requires you by default and makes its
rules binding. Configure the defaults in `.bionic.yml`:

```yaml
review:
  scrutiny: standard
adr:
  acceptance: council-and-human
```

Review alternatives are `focused` and `intensive`; ADR acceptance can explicitly
use `council-only`. Every cycle retains independent review, with targeted specialists
for actual risks rather than a fixed security panel. Quick-fix review stays slim.

Test results belong to the repository. Matching evidence is reused across cycles,
including releases; changes to relevant inputs or freshness requirements trigger
new checks. Reviewers inspect evidence without rerunning suites by default. Packaging
and deployment checks still establish their own coverage. A release has no review phase
and publishes only on the owner's quoted authorization for each target.

Records live in the configured tree's `cycles/<CYC-NNNN>/cycle.json`. The cycle
progress reader shows phases, tasks, passes, loops, and approval waits. Completed
or abandoned cycles close permanently with a reflection. Follow-up work starts a
new cycle. Historical promptbook sections below describe existing records only;
new work never creates a promptbook or repeats its run.

## At a glance (the 30,000ft view)

crux turns a `./bionic/` folder into a maintained knowledge base that you and Claude share. There are four moving parts:

1. **The `bionic/` tree: seven concerns, plus two default-on surfaces.** Code docs, research wiki, ADRs, briefs, work journal, promptbooks, invariants, plus the derived `arch` map and the `observations` records. You curate and decide; Claude does the bookkeeping. → [The seven concerns](#the-seven-concerns)
2. **56 skills: natural language, no slash commands.** "propose an ADR", "process inbox", "audit docs", "start a cycle", "forge a skill". Each is triggered by a phrase routed through the skill's description. → [What to say to Claude](#what-to-say-to-claude) (and the plugin's `README.md` has the full catalog)
3. **10 agents: a role layer over the skills.** A `commander` conductor delegates to `architect` / `dev-lead` / `developer` / `reviewer` / `historian` / `librarian` / `brainstormer` / `wayfinder`, and `night-gardener` works overnight. Each is fenced by a tool allowlist so duties are separated *structurally*. → [The agent layer](#the-agent-layer)
4. **One workflow for change.** The `cycle` skill selects dev, iterate, refactor, simplify, quick-fix, or release. Plans and evidence scale with the task. → [Working in cycles](#working-in-cycles)

Under the hood: stdlib Python **scripts** (extractors, validators, the LLM router) that the skills call for you, plus the `crux-env` **CLI** for secrets. → [Tools & scripts](#tools--scripts)

**If you read nothing else:** drop anything into `bionic/inbox/` and say *"process inbox"*; ask *"what does X do?"* / *"why did we choose Y?"*; and say *"start a cycle for X"* or *"iterate on X"* to ship a change with the receipts attached.

---

## The mental model

```
┌─ Your job ──────────────────────────────────────┐
│  • Make architectural decisions                  │
│  • Drop anything in bionic/inbox/ (files, URLs,  │
│    notes); process-inbox sorts and routes it     │
│  • Direct the work (what to build next)          │
│  • Ask questions of the docs                     │
└─────────────────┬───────────────────────────────┘
                  │ conversation
                  ▼
┌─ Claude's job ──────────────────────────────────┐
│  • Capture decisions as ADRs                     │
│  • Ingest sources into the research wiki         │
│  • Journal what got done                         │
│  • Track cycle progress                          │
│  • Extract code docs from source                 │
│  • Audit for drift                               │
└─────────────────┬───────────────────────────────┘
                  │ writes
                  ▼
              bionic/  tree
```

You read the wiki. Claude writes it.

---

## The seven concerns

_This guide names the default `bionic/` layout. In a project with a custom `docs_dir`, that directory takes the place of `bionic/` everywhere below._

| Directory | What lives there | Who edits |
|---|---|---|
| `bionic/code/` | Auto-extracted from source code (docstrings, @doc, JSDoc) | **Regenerated, never edit by hand.** Hand edits are deleted on every extract run. |
| `bionic/research/` | Articles, papers, web pages, meeting notes, chat exports | You drop sources in the unified `bionic/inbox/`; `process-inbox` routes them to `ingest-research`, which captures each into the immutable `bionic/research/raw/` and runs the ingest pipeline |
| `bionic/adrs/` | Architecture Decision Records, the "why" of every load-bearing decision | You decide; Claude writes the ADR. **Once `Accepted`, the body is frozen.** |
| `bionic/briefs/` | Pre-decision exploration documents (`BRIEF-<slug>.md`) | You write; Claude tracks them |
| `bionic/journal/` | Day-by-day record of work performed (`YYYY-MM.md`) | Claude appends entries; you ask for them |
| `bionic/cycles/` | Plans, tasks, phase evidence, decisions, and pass history | Maintained by the cycle workflow |
| `bionic/promptbooks/` | Historical plans and immutable run snapshots | Preserved with their original meaning |
| `bionic/invariants/` | Pinned, executable statements of *what must be true*: a ledger page per pin plus the executable check suite in `invariants/checks/`, reconciled via `invariants/reconciliation.yml` | **Machine proposes, you ratify.** `recover-invariants` mines candidates as `observed`; you ratify/reject/retire via `transition-invariant`. Recovery never self-ratifies. |
| `bionic/observations/` (default-on) | Records of what the code *already does* (`OBS-NNNN-<slug>.md`), each evidenced by a `path:line-range` and never by a code excerpt | **You write, you ratify.** `propose-observation` scaffolds one as `observed`; `transition-observation` is the only single-record route past `observed`, to `ratified`, `rejected`, `retired`, or `decided`. The batch sign-off is the only batch route. No scan writes an observation file in any state. |
| `bionic/arch/` (default-on) | Derived architecture spine, the current-state map: data model, interface surface, module graph, decision index, plus a synthesized overview | **Regenerated, never edit by hand.** Built on demand by `derive-arch`; enrolled by default on new trees (existing trees opt in by adding `arch` to `concerns_enabled`). |

The seventh concern, **invariants**, is the "far half of the bridge": where the other concerns record knowledge, invariants pin *what must stay true* as executable checks that survive regeneration. A new project stands it up empty, as an invitation to run `recover-invariants` when you're ready; an empty invariants concern is clean, not broken.

Beyond the seven, there is a **default-on eighth surface: `bionic/arch/`**, the derived architecture. It is the primary place to answer *"how is this project shaped right now?"*: a deterministic spine (data model, interface surface, module graph, decision index) plus a synthesized overview, all regenerated wholesale from the project's own sources. ADRs are the secondary path (the *why*); the librarian and historian fill the gaps. arch is **default-on for new projects** (init-docs enrolls it), so just say **"build the arch"** to derive it, and keep it current with `derive-arch` (or let `audit-docs` auto-regenerate it on drift). An **existing tree that predates the default** opts in first by adding `arch` to `concerns_enabled`, then derives. Like `code/`, it is never hand-edited.

There is a **second default-on surface: `bionic/observations/`**, the record of what the code already does. An observation describes; it does not decide. Where an ADR records a choice somebody made, an observation records a fact nobody ever wrote down, evidenced by a `path:line-range` into the real source. A project that has never authored an ADR uses observations as its starting layer, and a project full of ADRs uses them for everything the ADRs never covered. Say **"propose observation"** to scaffold one; it lands as `observed`. Only you move it past that: `transition-observation` is the only single-record route, and `survey-signoff` the only batch route. No scan ever writes or ratifies one. Ratified records feed the same summaries and doctrine projections the ADRs feed, so an observation earns real authority once you have affirmed it.

The batch route runs in two steps and covers as many candidates as you put on one sheet. Say **"scaffold a survey sheet"** and `survey-sheet` builds one sheet over the candidates in `observed`, seeding each row with a claim and a proposed domain. You author the rest of each row: a verdict of `ratify`, `reject`, or `defer`, a one-line rationale, and a domain that overrides the proposed one where it is wrong. Say **"sign off the survey"** and `survey-signoff` renders every claim and its verdict for you to read. It publishes the batch under one digest-bound receipt once you confirm, so one signature covers every ratification in it. Both commands are yours to invoke, and neither runs unattended.

---

## The agent layer

Cycle work enters through Commander, then Dev Lead assigns scoped implementation
to Developers. Dev Lead supplies the base commit and integrates worktree results
before testing. Commander arranges independent review and records completion.
Whiteboarding enters through Brainstormer; garden work enters through Night Gardener.
Use the responsible lead instead of bypassing coordination to assign a Developer.

New cycles explain which related tests cover the affected behavior. They run
missing or invalidated checks and reuse matching evidence. Completion records
the implementation commits, or your explicit instruction to leave work uncommitted.
The final cycle record is then committed. Tests need not repeat merely because
the phase changed or bookkeeping was committed.

crux also ships ten **agents** that operate the skills above.
Claude Code loads the source agents from the plugin. Codex and OpenCode use
generated native forms.

- **commander** runs a cycle or existing historical run and delegates everything (never edits).
- **brainstormer** explores a design with you (drives the `whiteboarding` skill), then hands the session to the historian to file.
- **architect** owns ADRs and decisions (drafts, runs the council, accepts).
- **dev-lead** leads implementation and fans independent work out to **developer**s.
- **reviewer** independently reviews code. It is read-only, so it reports findings and never fixes-and-hides.
- **historian** owns every write under `bionic/`.
- **librarian** answers questions from `bionic/` (read-only retrieval).
- **wayfinder** goes ahead and finds the way through large/uncertain or external data. It reads the data in an isolated context, judges its fitness for your purpose, and returns a verdict + condensed digest so a primary spends its own context only on proven-fit content (read-only; the only agent with `WebFetch`/`WebSearch`, fenced by an egress guardrail).
- **night-gardener** is the overnight presence. She runs as a scheduled routine, reviews what changed since your last move, and leaves a morning note under `bionic/garden/` (ideas, codebase improvements, missing tests/CI/guards, research, news). Turn-based (skips when only her own work changed), full co-CTO behind existing gates, never pushes. Dismiss or snooze her advice via `bionic/garden/tending.md`; no acknowledgment needed. Her news pass reads a curated source list via the `read-news` skill.

The role definitions declare tool boundaries and required skills. Host permissions
can override a role's default sandbox, so the role prompt remains binding. The
agents embed the craft disciplines they need, including testing, verification,
debugging, and two-stage review.

| Agent | Reach for it when you want… | Bounded so it cannot… |
|---|---|---|
| `commander` | a cycle or existing historical run driven end-to-end (it delegates each step) | edit code or docs itself |
| `brainstormer` | to explore a fuzzy idea before committing (drives `whiteboarding`) | write files or touch code |
| `architect` | a decision recorded + council-reviewed (`propose-adr` creates the Proposed decision → `council` → `transition-adr` accepts) | implement code |
| `dev-lead` | implementation coordinated across parallel units | merge / push (human-gated) |
| `developer` | one scoped unit built test-first | re-delegate, or write docs/ADRs |
| `reviewer` | an independent check of a diff | edit files (it reports; never fix-and-hide) |
| `historian` | anything written under `bionic/` (intake, journaling, indexes) | edit source code |
| `librarian` | a question answered from `bionic/` (`query-docs`) | write anything |
| `night-gardener` | an overnight pass that records ideas, gaps, research, and news | push, merge, or send material externally |
| `wayfinder` | a large/uncertain or external source triaged for context-fitness + condensed before you read it | write, execute, delegate, or relay local content outbound |

In Codex, say **"install the Crux agents in Codex"** after installing the
plugin. The installer writes the ten namespaced `crux_*` roles to
`~/.codex/agents/` by default. Each role pins its catalog model and reasoning
effort and binds its declared skills to the installed plugin. An explicit
`--repo-root` selects one project's `.codex/agents/` directory.

An unchanged refresh is a no-op. Changed or stale managed files require
`--force` after review. Plugin relocation appears as drift because skill
bindings use absolute paths. `--check --project-context <repo>` reports managed
drift and project agents that shadow personal roles. The report separates
canonical expectations from managed TOML state parsed from disk. Its runtime
result stays `unverified` until fresh-session host evidence confirms discovery,
settings, skills, and representative workflows for the selected Codex version.

**How you actually use them:** you rarely name an agent. A cycle (and the `commander`) dispatches them for you. But you can be explicit: *"have the architect propose an ADR for X"*, *"send this design to the council"*, *"have the reviewer check the diff"*, *"ask the librarian what we decided about Y"*.

---

## What to say to Claude

These phrases trigger the right skill. Use them in natural-language sentences; Claude figures out the rest.

### Recording decisions

- **"Propose an ADR for X"** → `propose-adr` writes a new `ADR-NNNN-<slug>.md` in `bionic/adrs/`, status `Proposed`. You review the alternatives, then…
- **"Accept ADR-NNNN"** → `transition-adr` changes the status to `Accepted`. Body is now frozen; `propose-adr` only creates a new `Proposed` decision.
- **"Supersede ADR-NNNN with ADR-MMMM"** → `transition-adr` updates both ends of the supersession link atomically.
- **"Deprecate ADR-NNNN"** → `transition-adr` retracts the decision (no replacement).
- **"Sign off backfill batch <id>"** → the owner sign-off for one governed backfill batch (`backfill-signoff`). Every enumerated receipt's rule and anchor renders verbatim for your read before anything writes; the script is the only write path onto the backfill surfaces (signed-date flip, admission ledger, log op, journal hook, completion marker). Never hand-edit those surfaces.

ADRs are append-only history. You can't edit one once accepted; you write a new one that supersedes it. An ADR records an enduring constraint, not every implementation choice; a replaceable choice is an Implementation Decision (see [Implementation Decisions](#implementation-decisions)).

#### Historical promptbook guidance and promotion

New-policy ADR acceptance makes its rules binding immediately. No separate promotion is required. The following rules describe historical promptbook records only; they do not govern new cycles or change historical interpretation.

Under the historical policy, text added while a council answered findings was **guidance** until promoted. Binding text was the ADR as it stood when the run started, plus promoted text. An ADR first proposed in a historical run bound nothing until promotion.

- **Provenance records.** Accepting an ADR in a run writes one record under `bionic/adrs/provenance/`. It lists each rule as `binding` or `guidance`, with the binding wording. The summaries and the doctrine read that record, so each rule shows its standing. A guidance rule is never deleted, and every citation of it keeps resolving.
- **Promote.** Reply to the cycle's promotion request with "promote ADR-NNNN: rules N", where N is the rule numbers or `all`. Claude then runs `transition-adr`, which records your words in the provenance record. Promotion never blocks a run.
- **Change guidance cheaply.** A `fix-directly` change or a patch may change what guidance describes. It cites the guidance rule and needs no ADR, provided every binding rule still holds. A patch still runs its own council.

### Capturing anything: the unified inbox

There is **one** place to drop raw input: `bionic/inbox/`. Drop any kind of item there (a research file, a pasted URL, a half-formed decision note, a stray idea), then say **"process inbox"**. The `process-inbox` skill classifies each item, shows you a confirmation table (item → proposed skill → confidence), and on your `ok` dispatches each to the skill that owns its concern:

- research source (file, URL, or a `urls.md` manifest) → `ingest-research`
- architectural decision → `propose-adr`
- pre-decision exploration → `propose-brief`
- work-log note → `log-work`

Classification is **classify-then-confirm**: only items Claude is confident about auto-dispatch on `ok`; anything unsure is held back for you to `override N=<target>` or `defer N`. ADRs are only ever created as `Proposed`; `process-inbox` never auto-accepts.

**Research still flows through `ingest-research`.** When a dropped item is classified as research, it goes through the ingest pipeline: moved into a dated, immutable `bionic/research/raw/` capture, with an audited source page and synthesis updates.

- **Drop a file in `bionic/inbox/`** and say "process inbox". Research items are moved to a dated `raw/` capture, get an audited source page, and update synthesis pages.
- **Paste a URL** into a file under `bionic/inbox/` (or hand it to Claude) and say "ingest this". It uses the same pipeline, fetched via the bundled `web-to-markdown.py`.
- **Bulk import**: drop a `urls.md` file in `bionic/inbox/` with one URL per line. Add `(static)` after a URL to opt it out of refresh checks. A partially-drained `urls.md` is left in place and retried on the next run.

When upstream sources may have changed:
- **"Refresh sources"** → re-fetches non-static URLs, files updates as new dated captures, flags affected synthesis pages.
- **"Refresh synthesis"** → walks you through accumulated markers (contradictions, source updates) per page.

### Journaling work

- **"Log work"** or **"journal this"** → adds an entry to `bionic/journal/YYYY-MM.md` with today's date and a category.
- Claude may also call this silently after meaningful operations (ADR accepted, promptbook completed, large refactor).

Categories: `decision | implementation | bug | learning | blocker | refactor | meeting | review | misc | release`.

`log-work` selects one procedure before writing. An interactive journal request adds a reflective monthly entry, regenerates the journal index, and records one `journal` operation. A silent call defaults to log-only: it requires a valid operation and writes only `bionic/log.md`. The bundled writer checks the request before writing and reports `complete`, `refused`, or `partial`. Keep the original request and its explicit local UTC offset for retry. A month-only partial entry cannot prove that offset; the writer warns `offset unverified`. If the offset was lost, stop automated replay and resolve it from evidence. A journal body allows 1–10 authored lines; an optional `Refs:` line is separate from that limit.

### Planning multi-step work: cycles

Say **"start a cycle for X"** and provide the outcome, constraints, and acceptance evidence.
Select dev for major changes, iterate for minor changes, refactor for nonfunctional
improvements, simplify to remove complexity without losing behavior, quick-fix for
bounded corrections, or release for publication work.
The [cycle overview](#working-in-cycles) describes their phases and pass limits.

Say **"cycle status"** to inspect phases, tasks, evidence, approval waits, and pass history.
The plan remains visible as work proceeds. Returns preserve earlier plans; pausing and
resuming never starts another run. New work requested through `dev-cycle`, `iterate`,
`patch-cycle`, `fix-directly`, or `author-promptbook` routes to the unified cycle workflow.

`run-promptbook` and `archive-promptbook` remain for existing historical records.
They do not create new work or repeat a completed run.

For installations upgrading from the seven retired entries, use these routes.
In Claude Code, Codex, and OpenCode, derive `CRUX_PLUGIN_ROOT` from the selected
Crux `SKILL.md`: it is the parent of that skill's `skills/` directory. References
to the plugin's `box/` files below mean `${CRUX_PLUGIN_ROOT}/box/` in an installed plugin.
`${CLAUDE_PLUGIN_ROOT}` is a Claude Code variable, not a portable plugin path.

| Former entry | Current route |
|---|---|
| `task-planner` | `whiteboarding` for exploration; a cycle for a tracked plan. The Python task-planner API remains in `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`. |
| `author-runbook` | Tracked planning by default; explicit generator instructions in `${CRUX_PLUGIN_ROOT}/box/operator-services.md`. |
| `visualize-run-progress` | `run-promptbook` status; the renderer script remains available. |
| `trace-runtime-ops`, `semantic-bridge`, `agent-identity` | Python APIs in `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`. |
| `serve-llm` | HTTP service instructions in `${CRUX_PLUGIN_ROOT}/box/operator-services.md`. |

These names no longer select installed skills. Existing runs, runbooks, identities, and Python modules remain in place.

Historical books and runs remain structured `.yaml` records with their original validation. New work uses cycle records; do not author successor books.

#### Implementation Decisions

An ADR records an enduring constraint the project must keep. A choice of how to build something within those constraints is an **Implementation Decision**, and it needs no ADR.

- **New cycles.** Dev requires a council-approved IDR; other cycle types require one for material choices. Approval binds the exact reviewed revision. IDRs record reasoning, not governing rules.
- **Preserved history.** Replacing an earlier choice in a later cycle needs no revocation, deprecation or supersession of the earlier record. Its reasoning and council evidence stay readable.
- **A material revision needs a fresh council.** An approval binds the exact revision the council reviewed. Any change to the reviewed record needs a new revision and a new council. Only a correction to the display title or a source label is a separate annotation that keeps the reviewed original.
- **Intent, delivery and current state stay separate.** An approval records what was reviewed. A result records what was delivered and independently reviewed. Neither says what holds today: `query-docs` reads the source at the source revision you name (`HEAD` by default) and answers `UNOBSERVED` when it finds no evidence. A proposal alone is never current. The `implementation-decisions.py` command (`validate`, `result`, `annotate` and `query`) is documented in the `query-docs` skill; only `result` and `annotate` write.
- **Architectural conflict.** When review finds the approach conflicts with a constraint, the work stops and moves to the ADR process.
- **No authority.** Implementation Decisions, results and annotations author no rule. Doctrine, summaries and every other governing reader exclude them, including constraints quoted inside them. Demonstration repositories under a run's `evidence/implementation-cycles/retained-repositories/` are nonauthoritative holdings: they contribute no record, rule or current architecture.
- **Legacy records.** Format-one books and runs (written before `format_version "2"`) and Markdown records keep their original meaning and are never converted or rewritten. A format-one cycle book follows the original formula and may be grandfathered with `cycle_grandfathered`. A format-two book declares its cycle kind (`adr`, `implementation`, `verify` or `patch`) in a field that its frozen plan hash covers, and refuses grandfathering. Moving an old ADR clause to historical status is a separately reviewed migration batch, and the ADR body stays as the historical record.
- **Historical migration writes are retired.** `implementation-migration.py apply` and `dry-run`, `run-council.py --migration-batch` and `advance-run.py --migration-batch` refuse every call with `historical-migration-writes-retired`. Nothing is read, staged or written before the refusal. Propose new clause migrations in the prospective format through `migrate-adrs` (`adr-migration.py`). Every authority reader still verifies a historical publication that is already recorded, and `inventory` still reports. `inventory` exits 0 whenever it prints a report. `dry-run` and `apply` exit 1, print `{"authority": "none", "limit": "historical-migration-writes-retired"}` on stdout, and print one `{"remedy": "<next step>"}` line on stderr. `run-council.py --migration-batch` exits 2 with `the selected migration batch was refused: historical-migration-writes-retired`. `advance-run.py --migration-batch` exits 1 with `{"error": "historical-migration-writes-retired; nothing was written"}`. A legacy run that declares a migration slot cannot convene that slot's councils or record its close. Its other prompts advance as before, a close already recorded in it stays verifiable, and the run may be abandoned.
- **Shallow clones.** A tree that has published a clause migration needs full Git history. In a shallow clone (the default `actions/checkout` depth of 1 in CI, for example) the governing readers (summaries, doctrine, rules catalog, arch and reviews index) refuse with `history-unavailable`. Set `fetch-depth: 0` in CI, or run `git fetch --unshallow` locally.
- **Missing or linked instruction files.** In a tree that has published a clause migration, every governing reader (summaries, doctrine, rules catalog, arch, reviews index and the `query-docs` authority view) refuses with `migration-source-unreadable` while a tracked instruction or skill file is missing from the working tree. Each refuses with `migration-symlink-refused` on a linked instruction or skill path. A tracked link anywhere under a project-local skill root refuses, including a harmless mirror link from one harness's skill root to another's. A submodule at or under a skill root refuses with `migration-citation-scope-refused`. Summaries, doctrine and the authority view also print the `{"remedy": "<next step>"}` line on stderr. The rules catalog, arch and the reviews index print the code without a remedy line. Restore the file or stage its deletion with `git rm`. Replace a link with a copy of the regular file or directory it points to. To keep a submodule's skill as regular files, follow these steps in order (summaries, doctrine and the authority view also print them as the remedy line): untrack the submodule with `git rm --cached`; if `.gitmodules` has the submodule's section, remove that section and stage `.gitmodules` with `git add`; move the `.git` entry at the top of the submodule path out of the repository (moving it keeps the nested repository's history; deleting an embedded clone's `.git` directory loses any history not pushed elsewhere); then `git add` the files.
- **Host verification.** The tests behind this feature exercise schemas, projections and the command line. No test has run the feature inside a native Claude Code, Codex or OpenCode session, so its behaviour in each host is unobserved.

#### Historical promptbook councils and independent reviews

This subsection applies only to existing promptbook runs. New cycles use
`cycle-council.py` and the review policy in [Working in cycles](#working-in-cycles).

Council deliberation runs only through the council runner, and its council record is the only evidence a council gate accepts. Independent review is a reviewer's examination, and its reviewer report is the only evidence an independent-review gate accepts. Neither satisfies the other's gate.

- **The key.** Standard and Strict call three provider seats through the gateway and require `OPENROUTER_API_KEY` in `crux-env`. Native Lite needs no OpenRouter account; follow [Council review modes](#council-review-modes). Historical promptbooks retain their gateway-only policy and stop when the key is unavailable.
- **After an upgrade.** Refresh the installed roles so they carry the new council and review text. Claude Code reads the roles from the plugin, so restart the session. In Codex, run `install-codex-agents` again. In OpenCode, run `install-opencode-agents` again for a project install, or regenerate the symlinked tree and restart.
- **Before a gate prompt.** Store the key. Commit every council subject, because the council runner accepts only a tracked, clean subject. The council runner commits the attempt record and the council record itself, and the gate check reads only committed records.
- **Preflight refusals.** A preflight refusal is raised before any council request and names its repair. A preflight refusal the conductor may repair writes no council record. The conductor repairs the input (retype the path, or commit a subject the run wrote with `run-work-witness.py commit`) and runs the council runner again. The council runner refuses a `--prompt` that is not the run's current prompt, so the retry count always names the prompt the run is at. The third refusal at one convening prompt stops the run for you, and so does a refusal the conductor may not repair.
- **Recovery.** When the council runner exits 2 and stderr names `timeout`, or names outside work the commit moved, the owner's remedy under **Hooks** below comes first: restore the set-aside work, then remove a stale `index.lock`. After those two steps, and after any other exit 2, run the process check: confirm that no council runner you started for this module is still running. Then probe the attempt's lock with `run-council.py --recover <run> --prompt <n> --probe`. Once no live council runner holds the lock, run `run-council.py --recover <run> --prompt <n>`. Recovery makes no council request and reads no key. A persistence failure is never a reason to convene another round.
- **Hooks.** A hook that rewrites a council file (a JSON formatter with another indent or key order, for example) must exclude `<docs_dir>/promptbooks/runs/`, for example `exclude: ^<docs_dir>/promptbooks/runs/` in the pre-commit framework. Otherwise each council commit whose file the hook rewrites fails closed (`hook-or-commit-failed`, or `mismatch` when the hook re-stages its rewrite) and stops for you. A hook slower than the commit's 120-second bound makes the commit time out and leaves the attempt open. When the commit times out, or a refused commit names outside work it moved, look first for the work the hook set aside (`git stash list`; the pre-commit framework keeps a backup patch under its cache directory) and restore it. Only then remove a stale `index.lock` in the git directory, and run recovery. Councils in a promptbook run need `fcntl`, which native Windows lacks. There the council runner exits 2 before it claims a round, and recovery and the run-work witness writer exit 2 as well, so no council gate can pass. Run promptbook councils on macOS, Linux or WSL.
- **Run directory files.** After each council record, the council runner also commits the run's diagnostics log (`council-preflight.jsonl`) and run-work witness (`run-work-witness.json`), each when its bytes differ from HEAD's. A retryable refusal's diagnostics line stays uncommitted until the next such commit, or your commit of the run snapshot, carries it.
- **Stops.** A stop for a council that could not run clears: fix its cause and reconvene at the same round number. A stop on a round no owner exception authorizes clears when the owner commits an owner-exception record and that round converges. An open council attempt stops the gate until recovery commits its original record or the owner voids it with a void-attempt owner-exception record. Every other council stop is permanent for the module once its record is committed: abandon the run and start a new cycle for follow-up work.
- **Runs in flight.** The gate check applies to every cycle run that is active when you upgrade, at its next gate prompt. A module whose council ran before council records existed closes only on a council-runner round convened at module close. No book's bytes change.
- **Templates.** A change to a template reaches only books you author afterward. It fixes no book that already exists. The gate check corrects an existing book when that book runs.
- **Limits.** The gate check binds hashes, not content, and it cannot see councils outside a promptbook. The `run-promptbook` skill's `references/gates.md` holds the procedure and states what the gate check cannot see.

### Extracting code docs

- **"Extract code docs"** → runs the plugin's dispatcher (`scripts/extract-code-docs.py`) per `bionic/manifest.yml`. Regenerates `bionic/code/` from source.
- **"Verify code docs"** → dry-run version. Reports drift without writing.

Configure which extractors run by editing `code.extractors:` in `bionic/manifest.yml`. The plugin ships extractors for Elixir and Python, plus a fallback (header-comment scrape). More languages arrive as extractor plugins.

**Python.** A `python` key under `code.extractors:` takes exactly three fields (`extractor`, `glob`, and the optional `include_private`, default on); any other key at that level refuses the run:

```yaml
code:
  extractors:
    python:
      extractor: python
      glob: "src/**/*.py"
      include_private: true
```

The dispatcher runs the Python path under `uv run --no-config`, so `uv` ignores any `uv.toml` or `[tool.uv]` table. The script's PEP 723 block pins `griffelib==2.3.0`; any other installed version exits 2. The extractor reads your sources statically. It never imports or runs your code, installs its dependencies, or executes documentation examples.

The dispatcher reports one of five outcomes: exit `0` means clean, no drift. Exit `1` with a `drift` payload means the on-disk docs are stale; run without `--dry-run` to regenerate. Exit `1` with a `validation_errors` payload is a content refusal (a parse failure, an oversized source, an unowned output root, an extractor name the plugin doesn't ship). That is broken input, not drift, and no regenerator run fixes it; this payload appears only under `--dry-run` (the `verify-code-docs` skill). In write mode the same content refusal exits `1` with a message on stderr and empty stdout, and no output byte changes. A configuration error (a `--config` path that doesn't exist, a `--lang KEY` the manifest doesn't configure, or an unresolvable `.bionic.yml`/`.crux`) also exits `1`, with a message on stderr and empty stdout, whether or not `--dry-run` was passed. Exit `2` is a capability failure (an interpreter older than 3.13, or a missing or mismatched `griffelib`), reported on stderr with empty stdout. A `uv` resolution failure exits with `uv`'s own code, also with empty stdout.

### Summarizing the current architecture

- **"Build the arch"** / **"summarize the current architecture"** / **"regenerate the architecture"** → runs `derive-arch`, which detects your stack and regenerates `bionic/arch/` (the derived current-state map) wholesale from the project's own sources. Batteries-included packs cover Python, Ruby, Node.js, Elixir/Phoenix, and Swift (Swift packages and Xcode projects, with targets, product types, membership and `@main` owners). An XcodeGen or Tuist manifest missing its generated project file renders as missing input. A conditional build setting renders as a `conditional-setting` residual. Each pack derives the data model from your ORM, schema or type declarations (SQLAlchemy, SQLModel and Django models; ActiveRecord's `schema.rb`; Prisma, TypeORM and Sequelize; Ecto; Swift `struct`, `class`, `enum` and `actor` declarations). It derives the interface surface from a committed OpenAPI document or the framework's routes. The Swift pack derives it from `public`, `package` and `open` declarations, every protocol, the package products and the `@main` declarations. The module graph comes from the import graph. The Swift pack adds the targets and dependencies that `Package.swift` manifests and Xcode project files declare. Each concern gets a `populated | stubbed` verdict, recorded in `_meta/coverage.json`. The same verdicts print as a coverage table, with one remediation line per non-`populated` concern. The tool reports what it found and grades nothing. A machine missing a stack's declared parser (`tree-sitter` plus its grammar; Elixir needs `tree-sitter-elixir`, Swift `tree-sitter-swift`; Node.js and Ruby also declare grammars) gets exit 2 with nothing written; the fix is the environment, not the docs.
- **"What's the current architecture?"** → read `bionic/arch/overview.md` (or ask the librarian). Building is `derive-arch`'s job; answering from it is the librarian's.
- **"Escalate the arch runtime"** (`escalate-arch-runtime`; Python projects; you invoke it explicitly, it never auto-fires) → an optional fidelity upgrade you may choose, never the remedy `derive-arch` points you at. Recovers what the static extractor missed (the route table, the ORM schema) by running your FastAPI/Flask/Django app's import-time code in a confined subprocess, behind the `CRUX_ARCH_ALLOW_RUNTIME=1` consent gate plus a per-run permission prompt. Results land in `bionic/inbox/` as advisory material, never in `bionic/arch/`.

arch is **default-on for new projects** (init-docs enrolls it), so on a fresh tree you just build it. On an **existing tree that predates the default**, enable it first by adding `arch` to `concerns_enabled` in `bionic/manifest.yml`, then build it. Keep it current by re-running `derive-arch` after a change to any input, or let a routine **"audit docs"** auto-regenerate a drifted spine. Never hand-edit `bionic/arch/`; the next derive overwrites it.

### Asking questions

- **"What does X do?"** → searches `bionic/code/`, cites pages.
- **"Why did we choose Y?"** → searches `bionic/adrs/` and `bionic/briefs/`. For a replaceable implementation choice, `query-docs` also reads the run's Implementation Decision and reports it as reviewed intent, with no authority.
- **"What's the plan for Z?"** → checks cycles and relevant historical plans.
- **"What do we know about W?"** → searches research.

Good answers can be filed back into `bionic/research/ideas/`; Claude will offer.

### Checking health

- **"Audit docs"** → runs ~54 integrity checks across every enabled concern. Auto-fixes safe drift (counts, dates, missing index rows); surfaces broken cases for your decision.

Run after every ~10 writes, after a large refresh, before any release.

- **"Migrate ADRs"** / "review historic ADRs" / "review the decisions" → `migrate-adrs` asks the architect to assess clauses against current objectives. Pages contain five ADRs by default, with drill-in and durable resume. Exact council and configured owner approval precede committed publication. Historical reports and ADR bodies stay unchanged.

Run the review weekly. `cleanup-campsite` nudges when the newest report is older than `adr_review_due_days`, which is seven by default.

---

## Tools & scripts

Everything Claude does is backed by Python scripts shipped inside the installed plugin. The docs tooling is stdlib-only; the multi-model substrate (below) adds PEP 723-declared dependencies. **You almost never run these directly**, since the skills invoke them for you, but knowing they exist helps when something looks off.

**Invoked by skills (you don't run these):**

| Script | Skill that calls it | What it does |
|---|---|---|
| `extract-code-docs.py` | `extract-code-docs` / `verify-code-docs` | Regenerates `bionic/code/` from source docstrings, via per-language extractor plugins. |
| `web-to-markdown.py` | `ingest-research` / `refresh-research-sources` | Fetches a URL into audited markdown. |
| `transcribe-video.py` | `ingest-research` | Transcribes a video source to text. |
| `visualize-run-progress.py` | `run-promptbook` status; the `crux-mods` dashboard | Reads run progress; writes a byte-stable Markdown artifact only on explicit `--markdown`. `--json --project-root <dir>` prints one contained JSON document for a dashboard and writes nothing; it never re-runs itself through `uv`, and without PyYAML it prints an error envelope with code `yaml-unavailable` and exits 2. |
| `write-journal.py` | `log-work` | Validates and writes a journal entry plus derived index and log operation, or one log-only operation. Reports partial writes for replay. |

**Validators (run on demand or in CI, they never publish):**

| Script | What it does |
|---|---|
| `validate-promptbook.py` | Validates a promptbook or run `.yaml` against its draft-2020-12 JSON Schema **and** the cycle-coverage invariants (`--kind promptbook|run`). This preserves validation for historical books and runs. |
| `check-blast-radius.py` | Compares a `patch` run's git-recorded changed paths against the blast radius its book declared. `archive-promptbook` runs it as a precondition. |

> **PyYAML requirement.** `validate-promptbook.py` and `visualize-run-progress.py` require a real YAML parser, because the bundled minimal fallback isn't faithful enough for validation verdicts or content hashes. Without PyYAML they automatically re-run themselves under `uv run --no-project --with pyyaml>=6.0` when `uv` is installed (announced on stderr; may fetch PyYAML from your configured index on first use), or exit **2** with a remediation message. Exit 2 always means *your environment*, never *your docs*. Locked-down environments can set `CRUX_NO_UV_REEXEC=1` to disable the auto-repair and install PyYAML themselves.
>
> **Dependency resolution for shipped scripts (PEP 723).** Shipped scripts whose documented invocation is `uv run …` carry PEP 723 inline metadata; on first use, `uv` resolves those dependencies, **unpinned by hash**, from *your configured index* (cached afterwards). This is the same trust model as the PyYAML re-exec above. Hermetic or locked-down environments should pre-provision the declared dependencies themselves rather than letting first use touch the network; for stricter reproducibility pin resolution with `uv run --exclude-newer <date>` (or the `UV_EXCLUDE_NEWER` environment variable). `uv` itself is a prerequisite for those invocations. Without it the command fails at the shell (`command not found`); install it from https://docs.astral.sh/uv/.

**The multi-model substrate** ships with the plugin: the LLM router (`call-llm`), the multi-model `council`, `srde`, the tracer, and the identity / knowledge / task-planning modules that power the agent layer. These need API keys (next section) and run under `uv`, which picks the interpreter each script's PEP 723 header names; crux supports Python 3.13 and 3.14. The retained HTTP service exposes the router to non-Python clients; see `${CRUX_PLUGIN_ROOT}/box/operator-services.md`. For tracing, probe coordination, identity, and task-planning APIs, see `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`. The **`forge-skill` capability-gap loop** (below) is a prose workflow and needs no API keys of its own.

**`forge-skill`** closes a capability gap mid-task by autonomously authoring or revising a project-local skill under `.claude/skills/`. Trigger phrases: *"forge a skill"*, *"author a skill for this"*, *"close this capability gap"*. It runs autonomously and reports after the fact. Propose-first (wait for approval) applies only when the capability is outward-facing or irreversible (external sends, spend, publishing), would touch anything outside the repo or any secrets, or when the gap would change project structure or external surfaces (those take the brief/ADR path instead). Every forge act is recorded in the append-only **forge log at `.claude/skills/forge-log.md`**, a reviewable history of what was authored, when, and why.

**`retrospective`** is purposeful reflection over finished work. Trigger phrases: *"what should we learn from recent work"*, *"run a retrospective"*, *"retrospective over the last N books"*. It mines `bionic/log.md`, the work journal, and recent run snapshots to surface patterns; distills findings into ≤2 skill proposals; gates each proposal through the council before building it via `forge-skill`. Outcomes are recorded with a `Retrospective:` journal entry (the `## [YYYY-MM-DD HH:MM] learning | Retrospective: …` heading), the marker `cleanup-campsite` tracks via `CLN-RETRO-1` to nudge you when enough archived books have accumulated since the last retrospective.

The **`crux-env` CLI** keeps your API keys outside any repo. Its own section follows.

---

## Working with secrets and API keys

`~/.crux/` is your per-user secrets home, outside any repo. One file (`~/.crux/env`) holds all API keys for every project on your machine that uses crux. The keys never leave your machine and never live in git.

You manage it with the `crux-env` CLI, which ships inside the installed plugin. In Claude Code, the canonical invocation is:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" <subcommand> …
```

`${CLAUDE_PLUGIN_ROOT}` is the plugin's installed root. It is a Claude Code-specific variable that Claude Code sets inside sessions, so the command above (and the other `${CLAUDE_PLUGIN_ROOT}` examples in this guide) is a Claude Code example. In Codex and OpenCode, derive `CRUX_PLUGIN_ROOT` from the selected Crux `SKILL.md`: it is the parent of that skill's `skills/` directory. Then use `${CRUX_PLUGIN_ROOT}/scripts/crux-env.py`. The examples below abbreviate that invocation to `crux-env`; define your own shell alias if you use it often. The commands below are the whole interface.

### One-time setup

```
crux-env init
```

Creates `~/.crux/` with the right file modes (`0600` on `env`, `0700` on `secrets/`). Idempotent; re-running on an existing setup is safe.

### Adding a key

```
crux-env set OPENROUTER_API_KEY sk-or-xxxxxxxxxxxxxx
```

The value is stored in `~/.crux/env`, mode `0600`, so only you can read it. The key **name** is recorded in `~/.crux/log/crux-env.log`; the **value is not**. The log is safe to share for debugging.

### Validating what's required

```
crux-env check --project crux
```

Reads `~/.crux/required.yml` to see which env vars `crux` needs, then checks each is set. Exits `0` if everything's there; exits `1` with a JSON list of what's missing if not. Use this before running a workflow that depends on external services.

### Listing required keys (without revealing values)

```
crux-env list --project crux
```

Prints something like:

```
crux — required:
  ✓ CRUX_HOME
crux — optional:
  ✓ CRUX_DEBUG
```

`✓` means set; `✗` means missing. Values are never printed, only key names.

### Removing a key

```
crux-env rm OLD_API_KEY
```

For rotation: `rm` the old, `set` the new. (A future `rotate` subcommand may do this atomically.)

### Reference

| Command | What it does |
|---|---|
| `crux-env init` | Create `~/.crux/` with safe modes. Idempotent. |
| `crux-env set KEY VALUE` | Store a key. Logs the name, never the value. |
| `crux-env rm KEY` | Remove a key. Logged. |
| `crux-env check --project <name>` | Verify required env vars are set. Exit 1 lists what's missing. |
| `crux-env list --project <name>` | Show key names and set/missing status. Never prints values. |

### What NEVER to do

- ❌ **Never commit `~/.crux/` to git.** It lives outside your repo by design; don't symlink it in.
- ❌ **Never share `~/.crux/env`.** The mode-`0600` protection only matters if it's not posted to Slack.
- ❌ **Never paste a key into an issue, PR description, chat message, or screenshot.**
- ❌ **Never edit `~/.crux/log/crux-env.log`** to hide that you rotated a compromised key. The log is the audit trail.
- ✅ **Do rotate** any key you suspect was leaked. The cost is one `set` command.

### Where to read more

- `bionic/AGENTS.md` §13 is the full byte-level spec for the secrets store and CLI contract.

---

## Per-project configuration: the repo-root `.bionic.yml` file

Don't confuse these two crux config surfaces: the committed repo-root **`.bionic.yml` FILE** is per-project configuration; the user-home **`~/.crux/` DIRECTORY** (above) is your secrets store and is never committed.

A default `.bionic.yml` reads:

```yaml
config_version: "1"
docs_dir: bionic
artifact_prefix: ""
```

`.bionic.yml` supersedes the legacy `.crux` file (still read for back-compat). Every tree crux creates carries one; `init-docs` writes it on bootstrap. The pinned public `v3.23.2` recovery release writes it on a 4→5 upgrade, so the layout is a read rather than an inference. Commit changes to it when you want a non-default convention:

- **`docs_dir`**: relocate the tree (e.g. `documentation/` or `meta/docs/`). Repo-root-relative, no absolute paths, no `..`. The default is `bionic`.
- **`artifact_prefix`**: brand artifact ids so they're distinguishable across projects. With `artifact_prefix: "CRX"`, new books and ADRs get ids prefixed `CRX-` (for example `CRX-ADR-NNNN`). Existing artifacts are never renamed.

To use a non-default `docs_dir` in a new project, copy the shipped template to the repo root and edit it **before** you say "init docs". `init-docs` writes this file itself when it is absent and merges (never clobbers) one you already committed. Claude Code example:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/templates/bionic-yml.tmpl" .bionic.yml
```

Validation is fail-loud: a malformed or invalid `.bionic.yml` makes every consumer exit `1` with the validation error rather than silently falling back to defaults. Check yours with (Claude Code example):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bionic-config.py"    # prints the resolved config as JSON
```

- ❌ **Never put secrets, tokens, or API keys in `.bionic.yml`.** It is committed to git, and unknown keys are silently ignored, so a misfiled secret wouldn't even produce an error. Secrets go in `~/.crux/` (above), full stop.

Full contract: `bionic/AGENTS.md` §14.

---

## Where to look first

When you open a project that uses crux, read in this order:

1. **`bionic/AGENTS.md`** (~1000 lines; skim §1–§7 first) is the operational schema. It is the single source of truth for what lives where and who edits what.
2. **`bionic/index.md`** is the rollup catalog of everything, with a section per concern and counts.
3. **`bionic/adrs/`**: start at the lowest-numbered ADR and walk forward in number order. This is the "why" of the project.
4. **`bionic/journal/`**: the most recent month tells you what's happening now.
5. **`bionic/research/sources.md`** is the registry of external context the project draws from.
6. **`bionic/cycles/`** holds current work and its recorded progress; `bionic/promptbooks/index.md` retains historical runs.

---

## What you should NEVER do

- ❌ **Edit anything in `bionic/code/`.** Hand edits are deleted on every extract run.
- ❌ **Edit an ADR body once it's `Accepted`.** Write a new ADR that supersedes it.
- ❌ **Reorder `bionic/log.md` or edit past entries.** It's append-only audit history.
- ❌ **Delete `bionic/research/raw/`.** Old captures are the audit chain.
- ❌ **Reuse an ADR or promptbook number.** Numbers are monotonic forever.
- ❌ **Manually edit `bionic/research/sources.md` rows.** Let `ingest-research` and `audit-docs` maintain it.

If something feels wrong (a contradiction, a stale page, a missing source), say so. Don't fix it silently. The system catches drift via `audit-docs`, and your nose for "this looks off" is the canonical trigger.

---

## What you SHOULD do by hand

- Write `bionic/briefs/BRIEF-<slug>.md` files. These are *your* pre-decision exploration; Claude tracks them but doesn't author them.
- Discuss the cycle goal, plan, tasks, and acceptance criteria with the assistant; let the cycle commands maintain its record.
- Edit the repo-root `AGENTS.md` to add project-specific notes your agents should know about. When the repository root holds no `AGENTS.md` or `CLAUDE.md` in any letter case, `init-docs` creates that file with a ``See `bionic/AGENTS.md` for documentation operations.`` line and an instruction to read `bionic/objectives.md`. A `CLAUDE.local.md` does not block that create. When an exact `AGENTS.md` exists, `init-docs` appends each of the two where it is missing. Keep both when you edit. `init-docs` writes nothing to a `CLAUDE.md` in any letter case, to a case variant of `AGENTS.md`, or through a symlink. The init summary reports each such entry with its remedy, which names `audit-docs --migrate` where that migration applies. The `See` line is plain text, not an include.

---

## Day-one quick start

You're in a fresh project with `bionic/` just initialized. To start using it:

1. **Capture today's intent as an ADR.** Say: *"Propose an ADR explaining why we're using crux for this project."* You'll review, then say *"Accept it."*
2. **Capture the planning material.** Drop your existing design notes / specs / chat exports into `bionic/inbox/` and say *"Process inbox."* Claude classifies each item and routes the research ones through `ingest-research`.
3. **Plan the first chunk of work.** Say: *"Start a cycle for <thing>."* Agree on the outcome and acceptance evidence.
4. **Journal at end of day.** Say: *"Log today's work — `<one line summary>`."*
5. **Audit after the first ten writes.** Say: *"Audit docs."* Confirm there's no drift.

---

## When things go wrong

| Symptom | Try this |
|---|---|
| "Where did Claude put X?" | Look at `bionic/index.md` and `bionic/<concern>/index.md`. |
| `bionic/code/` has stale content | Run *"extract code docs"*; it regenerates fully. |
| ADR was accepted but it's wrong | Don't edit. Write a new ADR that supersedes it. |
| Research synthesis page contradicts itself | Run *"refresh synthesis"*; Claude walks you through reconciliation. |
| Lost track of current work | Say *"cycle status"* for phases, tasks, pass count, and approval waits. Historical runs remain in `bionic/promptbooks/index.md`. |
| Whole `bionic/` tree feels broken | Run *"audit docs"*, which runs integrity checks across all concerns. |

---

## crux-mods: the run dashboard (Claude Code only, opt-in)

`crux-mods` is a second plugin in the crux marketplace. It holds Claude Code mods: small additions to the Claude Code interface. Its first mod is a run dashboard. Installing crux alone installs no mod and changes nothing. Codex and OpenCode are unaffected: crux behaves the same there, and `crux-mods` does not run there.

### Install

After you add the crux marketplace, install the plugin:

```
/plugin install crux-mods@crux
```

`crux-mods` needs Claude Code v2.1.287 or later; before that version Claude Code runs no mods, and the dashboard draws nothing. It also needs the `crux` plugin installed at the same version, because the dashboard reads your run through crux's own reader.

### What it shows

For new cycles, the band shows the cycle identity, type, pass and limit, phase, and status.
The pane shows a phase track, task glyphs, a progress bar, and `loop N`.
Open cycles come first, up to two panels, then a `+N open` line.
Below them, a queue card lists up to five upcoming items, the last two finished, and the queue's authorization, with `+N more` for hidden upcoming items.
The most recent closed cycle follows the queue as a full panel.
The other closed cycles follow under `cycles:`, one row each, three per page; press `n` and `p` to turn the page.
The crux-opencode panel pages the list the same way: while the panel is focused, `n` and `p` turn the page. Past one page, a last line reads `p previous · n next`. With the panel closed or unfocused, `n` and `p` reach your prompt.
Narrow panes keep the current phase and active task visible. Colour distinctions
also have a glyph or word. Return reasons and approval waits remain visible.
The details below describe the retained historical promptbook display.

- **A band above the prompt.** One line for one run, fitted to the width Claude Code reports, or to 40 columns when it reports none. When several runs are in progress, the band shows the run whose run file was written last, because each advance rewrites the run file of the run you are driving. The segments appear in this order, and a segment with nothing to say is left out:
  1. the book and run;
  2. the prompt strip: one glyph per prompt, with `|` between modules;
  3. the current prompt's module kind as a word, such as `dev`, or `untagged` for a prompt with no module tag;
  4. the current prompt out of the total (`p3/13`, or `prompt none of 13` when the run has no current prompt);
  5. the percent done;
  6. the time the current prompt has run, when it is running or blocked and has a start time;
  7. an escalation, in the error colour, when the current prompt's module has recorded three council rounds and none converged;
  8. a stall, in the error colour, when the run file has not changed for 20 minutes and this session lists no running subagent;
  9. the current prompt's title;
  10. the last council round and its aggregate action;
  11. the last gate with a recorded state;
  12. the number of running subagents;
  13. how many other runs are in progress.

  A line too long for the width loses its least important segments first. The escalation and the stall first shorten to `escalation p3 r3` and `stalled 25m`. Then the band drops segments in this order: the other runs, the subagents, the gate, the council, the title, the elapsed time and the kind word. The title shrinks to 8 cells before it goes. The strip keeps the glyphs nearest the current prompt and counts the rest as `+N` before it goes. The book and run, the percent and the position go next. The stall and the escalation go last. The band has no legend: the pane's legend names its glyphs.
- **Glyphs and colours.** A prompt or a gate is `✓` done, `✗` blocked, `▸` running, `◌` pending or `⊘` skipped. A council seat is `✓` approve, `~` approve with nits, `✗` request changes, `⊗` reject, `⬦` architectural or `⊖` defer to the owner. In the council grid, `-` is a seat with no decision, `!` an errored seat, `.` a role the record does not seat and `∅` a council that could not run. A subagent is `▸` running, `✓` completed or `✗` failed. A lane fills with `▬` on a dim track of `.`. The track's `.` never shares a panel with the council grid's `.`. `lanes withheld` is dim. `?` marks a value the dashboard does not recognise. Each colour is a key of your Claude Code theme. No colour carries a meaning alone. The error colour repeats what a `✗`, a `⊗` or a word already says. A module kind's colour sits on its kind word.
- **The last run, when none is in progress.** The band shows a dim line for the last completed run for 48 hours after it completed: its book and run, how long ago it completed, how many prompts finished out of the total, and how long it took. A finished prompt is done, skipped or blocked. It reads `CRUX: Last run <book> <run> completed 2h23m ago. Progress: 13/13. Time: 7h48m.` The line begins `CRUX: Last dated run` when some completed runs carry no valid completion time. Past 48 hours the band is empty, and the pane still shows the last run with no time limit. When the reader finds a run in progress that it cannot show, the band reads `run in progress, view refused`.
- **A stall, and its limit.** The stall segment reads `run file unchanged <time>, no subagent running in this session`. The agent list is this session's only. A run driven from another Claude Code session, from Codex or from OpenCode, work on the main thread and a long background command all show a stall while they work. Read the segment as a prompt to look.
- **An escalation, and its limit.** The escalation segment names the prompt and the last recorded round: `records r1-r3 show quorum met, none converged`. It reads the council records' own round numbers in your working tree. It does not decide whether a record counts or whether the gate stops: the gate check decides, and it reads committed history.
- **A `/crux-dashboard` pane.** Docked, the pane opens with a one-line legend: the glyphs and module kinds in view, then the other state glyphs while they fit. A panel follows for each run in progress, up to five, then a count of the rest. Each run panel holds:
  - the book, run, status, current prompt and percent;
  - the prompt strip, each module labelled with its kind word, and a progress bar of `▮` and `▯`;
  - when the run started and how long it has run. The last run shows its start, its completion and how long it took, from its recorded times only. From 30 columns, times that do not fit on one row wrap, each part whole;
  - one lane per prompt, on one time axis that the run's prompts share. The axis runs from the run's start to the reader's clock while the run is in progress, and to the run's completion after that. A lane fills the prompt's span with `▬` and ends with the prompt's state glyph. The rest of the lane is a dim track of `.`. A prompt with no start time shows `no start` in place of its lane. A lane of track alone means the prompt has no span to draw, never that it took no time. Lanes grow with the width and stop at 120 cells. Below 10 cells the pane draws no lanes. A run in progress draws no lanes when the reader reports no clock;
  - `lanes withheld`, dim, in place of the lanes of a run of more than 100 prompts. The pane also keeps a size budget of 90000 UTF-16 code units of text and 18000 nodes, counting each drawn element and each string. A run whose lanes would pass the budget draws `lanes withheld` too, from the bottom run panel shown upward. Its durations stay whole. When the pane passes the budget with every run's lanes withheld, it draws the rows it drew before the time axis. Those rows hold no lanes and no `lanes withheld`, and the times stand on one row. Each prompt row is cut at its end, so a row wider than its panel loses its duration;
  - the counts of prompts by state;
  - the stall and escalation lines, each followed by a dim note on its limit;
  - every prompt with its state, its module tag, its title and its duration, which is its end time minus its start time. A running or blocked prompt of a run in progress shows the time since it started. When a row is wider than its panel, its title is cut first, then its module tag, and its duration stays whole. Below 30 columns that holds only while the prompt's number, state and duration fit. Past the size budget, the pane draws the rows it drew before the time axis, as above;
  - the count of refused council files.

  The row of the run's current prompt is bold and starts with `▸ `, whatever its state. A blocked current prompt is also in the error colour. A councils panel draws a grid: a row per seat and a column per council record, headed `p<prompt>r<round>`. The panel stands beside the runs when the docked pane is 110 columns or wider, and after them otherwise. Under the grid, one row names the newest record's prompt and round, kind, aggregate action and whether it converged, and adds `could not run`, `quorum not met` or `degraded` when it applies. A gates panel lists each recorded gate as its state glyph, its prompt and its class: `council`, `module-close` or `review`. A gate result is a prompt that the cycle's gate classifies by its position as a council, module-close or independent-review gate, with its state and its evidence. A council or module-close gate's evidence is each attached council record that the reader opened and validated. An independent-review gate's evidence is the number of attached files that exist in the run's `reviews/` directory. The reader never reads one, so it shows no path. The text answer lists the evidence. An agents panel lists this session's subagents, and reads `agents unavailable` when Claude Code cannot list them. A panel with nothing to show takes no room.
- **Pane layouts.** From 40 columns each panel has a rounded border, and below 40 it has none. From 110 columns the docked pane draws two columns: the runs on the left, and their councils, gates and subagents on the right. Inline above the prompt, the pane draws at most 8 rows, borders included, and no lanes. It fills them in the order run, legend, gates, councils and subagents. The run section shows the book, position and percent, a stall, an escalation, the strip and the current prompt. A last row, `+N more:`, names what did not fit.
- **Widths.** Every row fits the width Claude Code reports. The dashboard draws at most 400 columns wide, even on a wider terminal. The dashboard measures text in terminal cells, where an East Asian wide character takes two. A long title or description is cut with `…`. Notes and summary lines wrap. The dashboard's own glyphs each take one cell. A terminal that draws an ambiguous-width character, such as `…`, two cells wide can still misalign a row.
- **The last run in the pane.** When no run is in progress, the pane shows the last completed run under `Last run`, or `Last dated run` with a count of undated runs. It shows the run's start, completion and duration, its lanes on an axis from its start to its completion, its prompts, councils and gates, and the run's summary under `Summary`. The summary is text from your run file. The pane removes control, format, bidirectional, zero-width, invisible and tag characters from it before it draws, and it shows `summary truncated` when the reader cut it. A summary stops at 4000 rows, with a count of the rows it leaves out. When the reader cannot rule out a hidden run, the pane draws the `undetermined` row instead: `Last run not shown: <n> unresolved, <m> undated; a run in progress or a newer completed run cannot be ruled out.` When no completed run carries a valid completion time, the row reads `Last run not shown: no completed run carries a valid completion time (<m> undated).`
- **A text answer.** Every `/crux-dashboard` call also answers with text, which Claude reads. The text carries these reader-derived values, fenced as data:
  - `now`, the reader's clock in whole epoch seconds, and each run's started, completed and modified integers;
  - each prompt's number, state, started and completed values;
  - counts, seat decisions and aggregate actions, and each council's `converged` value;
  - the gate results and the checked record paths, where a checked record path names a council record the reader opened and validated;
  - one `escalation p<n> r<n>` line for each escalation;
  - the last-run block: its status, the undated and unresolved counts and, when a last run exists, that run's lines.

  The text leaves out titles, module tags, summary lines, subagents, the stall flag and the paths of attached review files. It never repeats free text from run files.

The command is `/crux-dashboard` because Claude Code reserves `/dashboard` for a built-in command.

The dashboard refreshes at session start, every 15 seconds, and 1.5 seconds after Claude writes a run file with its Write, Edit, MultiEdit or NotebookEdit tool, or runs a Bash command that names one. After `reader-failed:time-limit`, `reader-cpu-limit` or `reader-timeout`, the 15-second refresh stops. It resumes once a refresh answers in time. Claude writing a run file or running a Bash command that names one, your `/crux-dashboard`, a matched phrase or a new session starts such a refresh. A matched phrase starts its refresh through a 0 ms timer.

### Open the pane by typing

Type one of these six phrases as your whole prompt, and the `/crux-dashboard` pane opens:

- `show the run`
- `show run progress`
- `visualize run progress`
- `run status`
- `promptbook status`
- `cycle status`

Letter case, extra spaces and one closing `.`, `?` or `!` do not matter, provided the whole prompt, spaces included, stays within 38 characters. The phrase must be the whole prompt: `please show the run` opens nothing, and neither does a phrase with an attachment. The pane opens only for a prompt you type in the prompt box or send through Remote Control, which Claude Code labels with the origin kind `bridge`. A prompt from the SDK, a schedule, a notification, a peer session or another plugin opens nothing.

Only Claude Code opens the pane from a typed phrase. In Claude Code, Codex and OpenCode alike, the agent answers cycle status through the cycle reader and historical run status through `run-promptbook`.

#### What the hook reads

To match a phrase, crux-mods reads the text and origin kind of every prompt you submit, and whether the prompt carries attachments. It keeps none of it: it stores no prompt text, passes none to a process and draws none. The prompt goes on unchanged, and the hook never blocks or delays it.

The `read_prompts` setting turns the reading off. Switch off "Read prompts" for `crux-mods` in `/config`. While it is off, crux-mods reads no prompt, and the phrases open nothing. The band, the pane and `/crux-dashboard` keep working. Disabling `crux-mods` in `/plugin`, or relaunching Claude Code with `--safe-mode`, also stops the reading.

A changed `read_prompts` applies when the hooks module next loads. If Claude Code reports that the plugin did not reload, run `/reload-plugins`. `read_prompts` was observed working on Claude Code 2.1.293, 2.1.296 and 2.1.299 in the test kit. No other version was tested, including 2.1.287 to 2.1.292 at the bottom of the manifest's range. The plugin's minimum, 2.1.287, is unchanged. On an engine that passes the hooks module no options, the phrases open nothing and crux-mods reads no prompt.

#### Where the pane seats

A pane you open seats at any width. A pane that opens unasked waits below 144 columns, or below 110 once you have opened the pane yourself. It stays hidden until the terminal widens or you run `/crux-dashboard`. crux-mods shows no message, retries nothing and asks for the pane once.

On Claude Code 2.1.296 and 2.1.299, a phrase seated the pane as a pane you open. At 100 columns, below the 144-column floor, the pane seated for a phrase typed while Claude was idle and for one typed while a turn ran. The test held that turn open without a model request.

### What it can reach

The capability manifest, `crux-mods/hooks/capabilities.ts`, lists everything the mod can reach. Each row is one entry: an event it handles, a call it makes on `$`, an environment variable it reads, or the process it starts.

| Through | Kind | What it sees | What it keeps |
|---|---|---|---|
| `session.start` | event (observe) | That a session started. It then registers `/crux-dashboard`, starts the 15-second refresh and runs the reader. | Nothing from the event. |
| `tool.call` | event (observe) | Each tool call's tool name, and the file path of a Write, Edit, MultiEdit or NotebookEdit call or the command of a Bash call. | Nothing. A call that names a run file schedules a refresh 1.5 seconds later. |
| `prompt.submit` | event (observe) | The text and origin kind of every prompt you submit, and whether it carries attachments. It reads nothing while the `read_prompts` setting is off. | Nothing of it. The prompt goes on unchanged. A prompt you type or send through the bridge, with no attachment, that is one of the phrases that ask to see the run opens the `/crux-dashboard` pane and starts a refresh. |
| `ui.render{component=AbovePrompt}` | event (draw) | The band's width and whether a survey is showing. | Nothing from the event. |
| `ui.render{component=Pane}` | event (draw) | The pane's request id, width and placement, and the page of the `cycles:` list you chose with the `n` and `p` keys. | Nothing from the event. |
| `command.run{command=crux-dashboard}` | event (command-text) | That you ran `/crux-dashboard`. It reads nothing else from the event. | Nothing from the event. It refreshes, opens the pane and answers with text that Claude reads. |
| `$.agent.list` | call | This session's subagents, and each one's status, type and description. | Nothing. It reads the list again for each drawing. |
| `$.clock.after` | call | Nothing. It sets the one-time timer for the refresh after a run-file write, and for the refresh after a prompt that asks to see the run. | The pending timer, until it fires. |
| `$.clock.every` | call | Nothing. It sets the 15-second refresh timer. | The timer, for the session. |
| `$.command.register` | call | Nothing. It registers the `/crux-dashboard` command. | Nothing. |
| `$.env.get` | call | The values of the environment variables in the rows below. | Nothing between launches. |
| `$.fs.read` | call | Two files: Claude Code's plugin record (`plugins/installed_plugins.json` in the Claude config directory) and the `plugin.json` of `crux-mods` itself. | Nothing between launches. It takes the installed crux's path and version, and its own version, from them. |
| `$.fs.stat` | call | Whether a path exists, its kind and its resolved path. It checks the launcher, the project root, the Claude config directory, the plugin record, the installed crux, `HOME`, uv, uv's cache and uv's interpreter directory. | Nothing between launches. |
| `$.process.run` | call | The reader's exit code, standard output and standard error. | Nothing of its own: the checked output is what `$.state.set` keeps. Standard error only selects a status code. |
| `$.session.root` | call | The session's project root. | Nothing between launches. The reader receives it as `--project-root`. |
| `$.state.get` | call | The last reader result this mod kept, under `crux-mods.current`, and the page of the `cycles:` list, under `crux-mods.page`. | Nothing. It reads the values again for each drawing. |
| `$.state.set` | call | Nothing. | The last reader result, once checked, under `crux-mods.current` for the session, so a reload of the mod's code keeps the band and the pane. Claude Code holds it in memory and writes no file. Other plugins in the session can read it. A press of the pane's `n` or `p` key writes the page number under `crux-mods.page` the same way. The page changes only which cycles the list draws. |
| `$.ui.invalidate` | call | Nothing. It asks Claude Code to draw the band and the pane again after each refresh. | Nothing. |
| `$.ui.open` | call | Nothing. It opens the `/crux-dashboard` pane. | Nothing. |
| `$.ui.resolve` | call | The `Box`, `Text` and `Button` components Claude Code draws with. | Nothing. |
| `CLAUDE_CONFIG_DIR` | environment read | Its value, to find the Claude config directory and to refuse one that differs from where the plugin was loaded. | Nothing between launches. |
| `HOME` | environment read | Its value, to find uv, uv's cache, uv's interpreter directory and the default Claude config directory. | Nothing between launches. The reader starts with it as its `HOME`. |
| `visualize-run-progress` | process | Your project's crux configuration and the cycles and historical runs, books and council records in its documentation tree, read by the installed crux's reader. | Nothing. The reader writes no file and answers with one JSON object on its standard output. |

It handles no other event, makes no other call and reads no other environment variable. It sets no variable in Claude Code's environment.

To run `visualize-run-progress`, it starts `/usr/bin/env -i <variables> <uv> run --offline --no-project --no-config --quiet <crux>/scripts/visualize-run-progress.py --json --project-root {project_root}`. `<variables>` stands for the only variables the process starts with: `HOME`, `PATH`, `UV_OFFLINE`, `UV_NO_CONFIG`, `UV_PYTHON_DOWNLOADS`, `PYTHONDONTWRITEBYTECODE`, `CRUX_NO_UV_REEXEC` and `NO_COLOR`. `<uv>` is the first file found among `/opt/homebrew/bin/uv`, `/usr/local/bin/uv`, `{HOME}/.local/bin/uv` and `{HOME}/.cargo/bin/uv`. `<crux>` is the installed crux plugin's directory. `{project_root}` is the session's project root. `{HOME}` is the value of `HOME`.

Directly or through the process it starts, it makes no network request, calls no model and reads no credential or environment secret. It writes nothing in your documentation tree or your project: its only write is uv's cache, and it refuses a uv cache inside your project.

Each row below is one part of what the mod draws. The From column names what that part draws from: a field of the reader's output, a subagent field, a property of the event, or the launch outcome.

| Where | Shows | From |
|---|---|---|
| the band above the prompt | the current cycle type, phase and pass limit | `visualize-run-progress:cycles[].id`, `visualize-run-progress:cycles[].type`, `visualize-run-progress:cycles[].phase`, `visualize-run-progress:cycles[].pass`, `visualize-run-progress:cycles[].pass_limit`, `visualize-run-progress:cycles[].status` |
| the `/crux-dashboard` pane | cycle phases, task progress, returns, approval waits and outcome | `visualize-run-progress:cycles[].phases`, `visualize-run-progress:cycles[].tasks`, `visualize-run-progress:cycles[].returns`, `visualize-run-progress:cycles[].waits`, `visualize-run-progress:cycles[].blocker`, `visualize-run-progress:cycles[].reflection` |
| the `/crux-dashboard` pane | the queue card: the count of queued items, whether the queue is authorized, and each upcoming or recently finished item | `visualize-run-progress:queue.items[].id`, `visualize-run-progress:queue.items[].title`, `visualize-run-progress:queue.items[].state`, `visualize-run-progress:queue.items[].cycle`, `visualize-run-progress:queue.items[].cycle_status`, `visualize-run-progress:queue.authorization.kind`, `visualize-run-progress:queue.authorization.remaining` |
| the `/crux-dashboard` pane | the `cycles:` list: the closed cycles after the latest as one-line rows, three to a page, with the page number and the `n` and `p` keys that turn the page | `visualize-run-progress:cycles[].id`, `visualize-run-progress:cycles[].title`, `visualize-run-progress:cycles[].type`, `visualize-run-progress:cycles[].status`, `visualize-run-progress:cycles[].tasks` |
| the `/crux-dashboard` pane | a cycle's elapsed time, and its paused time when there is any | `visualize-run-progress:cycles[].started_s`, `visualize-run-progress:cycles[].ended_s`, `visualize-run-progress:cycles[].paused_s`, `visualize-run-progress:cycles[].basis`, `visualize-run-progress:now_s` |
| the band above the prompt | the book and run of the run whose run file changed last | `visualize-run-progress:runs[].book_id`, `visualize-run-progress:runs[].run_id`, `visualize-run-progress:runs[].modified_s` |
| the band above the prompt | the prompt strip: one glyph per prompt, with `\|` between modules | `visualize-run-progress:runs[].prompts[].state`, `visualize-run-progress:runs[].prompts[].module_tag`, `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n` |
| the band above the prompt | the current prompt's module kind word | `visualize-run-progress:runs[].prompts[].module_tag`, `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n` |
| the band above the prompt | the current prompt's position out of the total | `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].progress.total` |
| the band above the prompt | the percent done | `visualize-run-progress:runs[].progress.pct` |
| the band above the prompt | the time the current prompt has run | `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n`, `visualize-run-progress:runs[].prompts[].state`, `visualize-run-progress:runs[].prompts[].started_s`, `visualize-run-progress:runs[].prompts[].completed_s`, `visualize-run-progress:now_s` |
| the band above the prompt | an escalation of the current prompt's module | `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n`, `visualize-run-progress:runs[].prompts[].module_tag`, `visualize-run-progress:runs[].escalations[].prompt`, `visualize-run-progress:runs[].escalations[].module_tag`, `visualize-run-progress:runs[].escalations[].round` |
| the band above the prompt | a stall | `visualize-run-progress:runs[].status`, `visualize-run-progress:runs[].modified_s`, `visualize-run-progress:now_s`, `$.agent.list:status` |
| the band above the prompt | the current prompt's title | `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n`, `visualize-run-progress:runs[].prompts[].title` |
| the band above the prompt | the last council round and its aggregate action | `visualize-run-progress:runs[].councils[].prompt`, `visualize-run-progress:runs[].councils[].round`, `visualize-run-progress:runs[].councils[].aggregate_action` |
| the band above the prompt | the last gate with a recorded state | `visualize-run-progress:runs[].gates[].n`, `visualize-run-progress:runs[].gates[].state` |
| the band above the prompt | the number of running subagents | `$.agent.list:status` |
| the band above the prompt | how many other runs are in progress | `visualize-run-progress:runs` |
| the band above the prompt | the last completed run, for 48 hours after it completed | `visualize-run-progress:last_completed_status`, `visualize-run-progress:last_completed.book_id`, `visualize-run-progress:last_completed.run_id`, `visualize-run-progress:last_completed.started_s`, `visualize-run-progress:last_completed.completed_s`, `visualize-run-progress:last_completed.progress.counts.done`, `visualize-run-progress:last_completed.progress.total`, `visualize-run-progress:now_s` |
| the band above the prompt | the line `run in progress, view refused` | `visualize-run-progress:runs`, `visualize-run-progress:last_completed_status` |
| the band above the prompt | the status code | `launch:outcome`, `visualize-run-progress:error.code`, `visualize-run-progress:format_version`, `visualize-run-progress:runs`, `visualize-run-progress:last_completed_status` |
| the band above the prompt | the band's width | `ui.render{component=AbovePrompt}:props.bodyColumns` |
| the band above the prompt | no band while a survey shows | `ui.render{component=AbovePrompt}:props.hasSurvey` |
| the `/crux-dashboard` pane | the legend of the glyphs and module kinds in view | `visualize-run-progress:runs[].prompts[].state`, `visualize-run-progress:runs[].prompts[].module_tag`, `visualize-run-progress:runs[].councils[].seats[].decision` |
| the `/crux-dashboard` pane | each run panel's heading: book, run, status, current prompt and percent | `visualize-run-progress:runs[].book_id`, `visualize-run-progress:runs[].run_id`, `visualize-run-progress:runs[].status`, `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].progress.total`, `visualize-run-progress:runs[].progress.pct` |
| the `/crux-dashboard` pane | the prompt strip, each module labelled with its kind word | `visualize-run-progress:runs[].prompts[].state`, `visualize-run-progress:runs[].prompts[].module_tag`, `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n` |
| the `/crux-dashboard` pane | the progress bar of `▮` and `▯` | `visualize-run-progress:runs[].progress.total`, `visualize-run-progress:runs[].progress.pct` |
| the `/crux-dashboard` pane | when the run started, and how long it has run or took | `visualize-run-progress:runs[].status`, `visualize-run-progress:runs[].started_s`, `visualize-run-progress:runs[].completed_s`, `visualize-run-progress:now_s` |
| the `/crux-dashboard` pane | one lane per prompt on one time axis | `visualize-run-progress:runs[].status`, `visualize-run-progress:runs[].started_s`, `visualize-run-progress:runs[].completed_s`, `visualize-run-progress:runs[].prompts[].n`, `visualize-run-progress:runs[].prompts[].state`, `visualize-run-progress:runs[].prompts[].started_s`, `visualize-run-progress:runs[].prompts[].completed_s`, `visualize-run-progress:now_s`, `ui.render{component=Pane}:props.bodyColumns` |
| the `/crux-dashboard` pane | `lanes withheld`, in place of the lanes of a long run or of a pane past its size budget | `visualize-run-progress:runs[].status`, `visualize-run-progress:runs[].started_s`, `visualize-run-progress:runs[].completed_s`, `visualize-run-progress:now_s`, `visualize-run-progress:runs[].prompts`, `ui.render{component=Pane}:props.bodyColumns` |
| the `/crux-dashboard` pane | the counts of prompts by state | `visualize-run-progress:runs[].progress.counts.done`, `visualize-run-progress:runs[].progress.counts.skipped`, `visualize-run-progress:runs[].progress.counts.blocked`, `visualize-run-progress:runs[].progress.counts.running`, `visualize-run-progress:runs[].progress.counts.pending` |
| the `/crux-dashboard` pane | the stall line and its note | `visualize-run-progress:runs[].status`, `visualize-run-progress:runs[].modified_s`, `visualize-run-progress:now_s`, `$.agent.list:status` |
| the `/crux-dashboard` pane | the escalation lines and their note | `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n`, `visualize-run-progress:runs[].prompts[].module_tag`, `visualize-run-progress:runs[].escalations[].prompt`, `visualize-run-progress:runs[].escalations[].module_tag`, `visualize-run-progress:runs[].escalations[].round` |
| the `/crux-dashboard` pane | a row per prompt: its state, module tag, title and duration | `visualize-run-progress:runs[].status`, `visualize-run-progress:runs[].current_prompt`, `visualize-run-progress:runs[].prompts[].n`, `visualize-run-progress:runs[].prompts[].state`, `visualize-run-progress:runs[].prompts[].module_tag`, `visualize-run-progress:runs[].prompts[].title`, `visualize-run-progress:runs[].prompts[].started_s`, `visualize-run-progress:runs[].prompts[].completed_s`, `visualize-run-progress:now_s` |
| the `/crux-dashboard` pane | the count of refused council files | `visualize-run-progress:runs[].councils_skipped` |
| the `/crux-dashboard` pane | the count of runs past the five shown | `visualize-run-progress:runs` |
| the `/crux-dashboard` pane | the councils grid, with the newest record's aggregate action and whether it converged | `visualize-run-progress:runs[].book_id`, `visualize-run-progress:runs[].run_id`, `visualize-run-progress:runs[].councils[].prompt`, `visualize-run-progress:runs[].councils[].round`, `visualize-run-progress:runs[].councils[].council_kind`, `visualize-run-progress:runs[].councils[].outcome`, `visualize-run-progress:runs[].councils[].quorum_met`, `visualize-run-progress:runs[].councils[].degraded`, `visualize-run-progress:runs[].councils[].aggregate_action`, `visualize-run-progress:runs[].councils[].converged`, `visualize-run-progress:runs[].councils[].seats[].role`, `visualize-run-progress:runs[].councils[].seats[].decision`, `visualize-run-progress:runs[].councils[].seats[].errored` |
| the `/crux-dashboard` pane | the gates panel | `visualize-run-progress:runs[].book_id`, `visualize-run-progress:runs[].run_id`, `visualize-run-progress:runs[].gates[].n`, `visualize-run-progress:runs[].gates[].state`, `visualize-run-progress:runs[].gates[].gate_class` |
| the `/crux-dashboard` pane | the agents panel | `$.agent.list:status`, `$.agent.list:type`, `$.agent.list:description` |
| the `/crux-dashboard` pane | the last run when none is in progress, with its summary | `visualize-run-progress:last_completed`, `visualize-run-progress:last_completed_status`, `visualize-run-progress:last_completed_undated`, `visualize-run-progress:last_completed.summary`, `visualize-run-progress:last_completed.summary_truncated` |
| the `/crux-dashboard` pane | the `undetermined` row | `visualize-run-progress:last_completed_status`, `visualize-run-progress:last_completed_unresolved`, `visualize-run-progress:last_completed_undated` |
| the `/crux-dashboard` pane | the line saying the reader refused a run in progress | `visualize-run-progress:runs`, `visualize-run-progress:last_completed_status` |
| the `/crux-dashboard` pane | the reader's version and the count of refused run files | `visualize-run-progress:reader_version`, `visualize-run-progress:runs_skipped` |
| the `/crux-dashboard` pane | the status code | `launch:outcome`, `visualize-run-progress:error.code`, `visualize-run-progress:format_version`, `visualize-run-progress:runs`, `visualize-run-progress:last_completed_status` |
| the `/crux-dashboard` pane | the layout: borders, one or two columns, and the inline layout with its `+N more` row | `ui.render{component=Pane}:props.bodyColumns`, `ui.render{component=Pane}:props.placement`, `visualize-run-progress:runs[].modified_s` |

To see the same events, calls, environment variables and session state listed by Claude Code itself, run `claude plugin validate --strict` on the installed `crux-mods` directory.

crux-mods never runs a script, interpreter, `uv` configuration or environment variable that your project supplies.

Text from run files renders as text. It is never treated as an instruction.

### When it cannot show a view

The dashboard prints a status code instead of a view when it cannot check the run safely. It refuses and does not guess. The band stays empty for `no-active-run` and for `reader-failed:tree-missing`. A project without a crux tree reports `tree-missing`. So does a session started in a subdirectory of a crux project: start Claude Code at the project root. The pane and the text still name the code. The code is the pane's only row. Except for those two codes, it also takes the band's line. When the code and its prefix do not fit, the dashboard drops the prefix, then cuts the code with `…`. The text answer always carries the whole code.

| Code | Meaning | What to do |
|---|---|---|
| `no-active-run` | No run is in progress. | Nothing. |
| `crux-not-installed` | It cannot find the installed crux plugin. | Install crux from the same marketplace as `crux-mods`. |
| `version-mismatch` | The installed crux is at another version than `crux-mods`. | Update crux or `crux-mods` so both carry the same version. |
| `home-invalid` | `HOME` is unset or not an absolute path in the session. | Start Claude Code with `HOME` set to an absolute path. |
| `uv-not-found` | `uv` is not at one of the places the dashboard looks: `/opt/homebrew/bin/uv`, `/usr/local/bin/uv`, `~/.local/bin/uv` or `~/.cargo/bin/uv`. | Install `uv` at one of those places. |
| `inside-project` | The project root contains the Claude config directory, the crux install or `uv` or its cache (for example, a session started in your home directory). | Start the session in the project's own directory. |
| `offline-unavailable` | `uv` cannot run the reader without the network, because a Python or PyYAML is not in its cache. | Run `uv python install 3.13` once, then run the reader once while online: `cd "<crux plugin dir>" && uv run --no-project --no-config scripts/visualize-run-progress.py --json --project-root "<project path>"` |
| `reader-no-json-mode` | The installed crux is too old to have the reader's JSON mode. | Update crux. |
| `reader-format-mismatch` | The reader answered with a JSON format version other than the one the dashboard accepts, which is 2. | Update crux and `crux-mods` so both carry the same version. |
| `reader-timeout` | The reader was still running after 10 seconds. | Retry; a cold `uv` cache can be slow the first time. |
| `reader-cannot-start` | Claude Code could not start the reader process. | Check that `/usr/bin/env` and `uv` are executable. |
| `reader-cpu-limit` | The system stopped the reader at its CPU limit of 9 seconds. | Retry. If the code persists, run the reader command in the `reader-failed` row to see the cause. |
| `reader-failed:<code>` | The reader answered with an error code, such as `tree-missing` (no crux tree in this project), `containment` (a path leaves the tree) or `time-limit` (the reader stopped itself after 8 seconds). | For `tree-missing`, start Claude Code at the project root, or nothing if the project has no crux tree. Otherwise run `cd "<crux plugin dir>" && uv run --offline --no-project --no-config scripts/visualize-run-progress.py --json --project-root "<project path>"` to see the code. |
| `reader-failed` | The reader failed without an answer. | Run `cd "<crux plugin dir>" && uv run --offline --no-project --no-config scripts/visualize-run-progress.py --json --project-root "<project path>"` to see the cause. |
| `reader-output-invalid` | The reader's output did not match the shape the dashboard accepts, for example more than 20 runs in progress. | Close or abandon finished runs. If the code persists, report it with the output of the reader command in the `reader-failed` row. |
| `no-env-binary` | `/usr/bin/env` is missing, as on native Windows. | None: the dashboard needs a POSIX system. |

In these remedies, `<crux plugin dir>` is the installed crux: `<Claude config>/plugins/cache/crux/crux/<version>`, where `<Claude config>` is `CLAUDE_CONFIG_DIR` when that is set, else `~/.claude`. `<project path>` is the project's absolute path. Run the reader command from `<crux plugin dir>`, never from inside the project: there, when the project has a `.venv`, `uv` runs that environment's Python interpreter. Run it in a shell with no virtual environment active; run `deactivate` first.

Two further codes, `project-root-invalid` and `config-dir-mismatch`, mean the dashboard cannot use the session's project root, or the Claude config directory the plugin was loaded from differs from `CLAUDE_CONFIG_DIR`.

The pane's `refused council files` and `refused run files` count files the reader would not read: a file that fails its schema, a path that leaves the tree, or a legacy `.md` run. A count above zero needs no action unless you expected that file to show.

### Turn it off

Disable or uninstall `crux-mods` in `/plugin`. Your documentation tree and runs are unchanged. To keep the dashboard and stop only the prompt reading, switch off `read_prompts` in `/config`.

## crux-opencode: the run dashboard in OpenCode 2 (opt-in)

`crux-opencode` is a separate plugin for the OpenCode 2 terminal interface. It is not part of `crux-mods`, which stays Claude Code only. It lives in the `crux-opencode/` directory of a clone of the crux repository. OpenCode loads it only when you list its path in `cli.json`, so installing crux alone loads nothing in the OpenCode terminal interface.

Add the entry to `~/.config/opencode/cli.json`, replacing the path with your clone's absolute path, and restart the OpenCode terminal interface:

```json
{
  "plugins": ["/Users/you/.local/share/crux/crux-opencode"]
}
```

It draws a band above the composer, a `crux-dashboard` panel, and a `/crux-dashboard` command that opens the panel. It reads your run through the same reader and draws it with the same drawing code as the Claude Code dashboard, both taken from your clone. There is nothing to install or build, and it has no version of its own: updating the clone updates it.

- **Where it works.** OpenCode 2.x only. On another version the band and the panel show `unsupported OpenCode version`.
- **Width.** The band draws at most 40 columns. The panel fits the width OpenCode reports.
- **Static.** It draws no motion, reads none of your prompts, and shows subagent status only as `agents unavailable`.
- **Status codes.** When it cannot check the run safely it draws a status code, as the Claude Code dashboard does. The most common is `inside-project`: the project root holds your crux clone, `uv`, its cache or its interpreter directory. The home directory counts, and so does running OpenCode on a crux checkout. Keep the clone you list in `cli.json` outside the project you are watching. `OPENCODE.md` in the clone lists every code and its remedy.

## Plugin and schema

Your project uses the `crux` documentation tree at `schema_version 5` (the
`bionic/` layout). The plugin is the marketplace-installed copy (in Claude Code,
`${CLAUDE_PLUGIN_ROOT}`). In Claude Code, install
or upgrade with `/plugin marketplace add bionic-coding/crux` and
`/plugin install crux@crux`. In Codex, use
`codex plugin marketplace add bionic-coding/crux` and
`codex plugin add crux@crux`. After upgrading from a release before 3.19.0, say
*"audit docs --migrate"* even when `schema_version` is already `"5"`. The migration
converts tracked `CLAUDE.md` files to `AGENTS.md`. When a scope also holds an
`AGENTS.md`, the legacy file wins: it becomes the new `AGENTS.md`, and the previous
`AGENTS.md` is kept byte for byte under a name the report gives. Where a move is
unsafe, the migration changes nothing in that scope and names the next step. It
reports untracked and private suppressors without editing them.
Codex users can install the ten Crux role agents personally with the
`install-codex-agents` skill.

### Recover older trees and Markdown promptbooks

The current plugin operates on tree schema 5. New work uses cycles; existing YAML promptbook runs remain supported.
For a schema-2, schema-3, or schema-4 tree, work on a copy or backup with the
public `v3.23.2` release. Verify its annotated tag and commit before using its
schema ladder:

```bash
recovery_dir="$(mktemp -d)"
git clone --branch v3.23.2 --single-branch https://github.com/bionic-coding/crux.git "$recovery_dir/crux"
git -C "$recovery_dir/crux" rev-parse refs/tags/v3.23.2
git -C "$recovery_dir/crux" rev-parse HEAD
```

The two results must be `c1298c4a9229ed41ae7017c25321d27e5b3f6e4d`
and `08ee30ec2f1d1b4b0ce970f2e1582bb4f83cd20d`, respectively. Read that
release's `crux/skills/audit-docs/SKILL.md` and use its 2→3→4→5 ladder in order.
A valid `.migrating` marker follows its recorded resume or abandon procedure;
an invalid marker or two ambiguous trees require investigation. The current
plugin does not run the ladder. Its `audit-docs --migrate` handles instruction
files on a schema-5 tree.

The tagged release can finish a Markdown run when its remaining prompts can
truthfully be completed. Archive it there, then convert its book before its
run with that release's `migrate-promptbooks` skill. It preserves Markdown
originals. Validate the YAML files and their content-hash binding before
returning to the current plugin. The tag cannot deliberately abandon a
Markdown run. If one cannot finish, keep its bytes unchanged as stranded,
readable history. Continue separate work in new cycles; do not mark that
run complete, skip unfinished prompts to migrate, or convert it in place.

Use a separate project copy for recovery. Before starting any host, inspect
that copy's project-level Crux registrations and disable only the current
version there: Claude Code's project settings and `.claude/skills/`, Codex's
`.agents/plugins/marketplace.json`, `.agents/skills/`, and `.codex/config.toml`,
and OpenCode's project `opencode.json`, `.opencode/skills/`, and
`.opencode/skill/`. Keep unrelated entries and the original project
unchanged. OpenCode merges project `skills` arrays with XDG settings, so an
isolated XDG directory alone does not remove a current project skill path.
If you cannot verify that only the tagged Crux skills are active, stop before
mutating the copy.

Use only the tagged plugin during recovery. In Claude Code, disable the
currently installed Crux plugin in its installation scope with
`claude plugin disable crux@crux`, then start a separate session with
`claude --plugin-dir "$recovery_dir/crux/crux"`. The `--plugin-dir` flag adds
that source for the session; verify that the current plugin is disabled.
After recovery, run `claude plugin enable crux@crux` and restart.

In Codex, use an isolated home so the normal plugin installation is absent.
The tagged checkout contains a local marketplace named `crux` whose source
is `./crux`. Codex's local-marketplace command accepts a directory path:

```bash
mkdir -p "$recovery_dir/codex-home"
CODEX_HOME="$recovery_dir/codex-home" codex plugin marketplace add "$recovery_dir/crux"
CODEX_HOME="$recovery_dir/codex-home" codex plugin add crux@crux
```

Start the recovery Codex session with that same `CODEX_HOME`, in a project
copy without another project-scoped Crux plugin. Verify the tagged skill is
available before mutation. End that session and return to your normal Codex
home to resume the current plugin. [Codex's local-marketplace instructions](https://developers.openai.com/plugins/build/plugins)
explain the path form; these commands have been checked against local CLI
help, not exercised as a fresh-session recovery.

In OpenCode, use an isolated XDG config for a separate recovery session. Put
this file at `$recovery_dir/opencode-config/opencode/opencode.json`, replacing
`TAGGED_CHECKOUT` with the absolute path of `$recovery_dir/crux`:

```json
{"skills": ["TAGGED_CHECKOUT/crux/skills"]}
```

Create the config directory and start OpenCode with isolated paths:

```bash
mkdir -p "$recovery_dir/opencode-config/opencode" "$recovery_dir/opencode-data" "$recovery_dir/opencode-cache"
XDG_CONFIG_HOME="$recovery_dir/opencode-config" XDG_DATA_HOME="$recovery_dir/opencode-data" XDG_CACHE_HOME="$recovery_dir/opencode-cache" opencode
```

Verify that only tagged Crux skills load; quit and restore the normal XDG
settings after recovery. This follows the OpenCode `skills`
array contract. The local tagged-script and fixture checks do not establish
fresh-session execution in Claude Code, Codex, or OpenCode; publication still
requires those three host observations.

---

_Generated by `init-docs`. Re-running `init-docs --force` overwrites this file._

## Council review modes

Configure council review independently of human acceptance in `.bionic.yml`:

```yaml
council:
  mode: standard
  max_attempts: 7
  overrides:
    idr: lite
adr:
  acceptance: council-and-human
```

Lite uses native Apex challenge and fresh final review with architect agreement;
it needs no OpenRouter account. Codex and Claude CLI have verified host adapters.
Standard requires two of three gateway provider approvals and a reasoned architect
disposition of dissent. Strict requires all three approvals without blockers.
Demonstrated binding failures and missing authorization block every mode.

New setup records Standard explicitly and offers Lite. Existing projects retain
Strict until an explicit owner instruction changes policy. Historical and in-flight
reviews keep their original policy. Review attempts stop on stalled progress or the
configured limit; extensions beyond seven need owner approval. Missing capability
or credentials never silently change the mode or model.
