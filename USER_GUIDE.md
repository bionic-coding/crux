<!-- generated-from: USER_GUIDE.md@sha256:b91ea1ef8e9b9cf3974002bb12989d50f83fc8afc0c4ad1b4424d21659d5d958; model: claude-fable-5.1; date: 2026-09-14 -->
# crux User Guide

crux is a Claude Code plugin that turns a `bionic/` folder in your project into a maintained knowledge base you and Claude share — seven concerns, plus the two default-on surfaces `arch` and `observations`. **You do not write these docs by hand.** You curate, decide, and discuss. Claude does the bookkeeping.

This guide is for humans. If you are an LLM agent picking up a crux-managed repo, read the project's `bionic/CLAUDE.md` — that's the operational schema.

---

## At a glance (the 30,000ft view)

There are four moving parts:

1. **The `bionic/` tree — seven concerns, plus two default-on surfaces.** Code docs, research wiki, ADRs, briefs, work journal, promptbooks, invariants — plus the derived `arch` map and the `observations` records. You curate and decide; Claude does the bookkeeping. → [The seven concerns](#the-seven-concerns)
2. **60 skills — natural language, no slash commands.** "propose an ADR", "process inbox", "audit docs", "start a cycle", "forge a skill". Each is triggered by a phrase routed through the skill's description. → [What to say to Claude](#what-to-say-to-claude) (the README has the full catalog)
3. **10 agents — a role layer over the skills.** A `commander` conductor delegates to `architect` / `dev-lead` / `developer` / `reviewer` / `historian` / `librarian` / `brainstormer` / `wayfinder`, each fenced by a tool allowlist so duties are separated *structurally*. → [The agent layer](#the-agent-layer)
4. **Three workflows for change.** `dev-cycle` (net-new / architectural — ADR + council + review), `iterate` (non-architectural fixes — verify + council + review, no ADR), and `patch-cycle` (a small reversible fix — five phases, one prompt each, with a declared blast radius). All three are tracked promptbooks. A defect whose fix you can name before starting: `fix-directly` — no book, a failing test first. → [Planning multi-step work](#planning-multi-step-work--promptbooks--cycles)

Under the hood: Python **scripts** (extractors, validators, the LLM router) that the skills call for you, plus the `crux-env` **CLI** for secrets. → [Tools & scripts](#tools--scripts)

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
│  • Track promptbook progress                     │
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

_This guide names the default `bionic/` layout. In a repo with a custom `docs_dir` (see [Per-project configuration](#per-project-configuration-the-repo-root-bionicyml-file)), that directory takes the place of `bionic/` everywhere below._

| Directory | What lives there | Who edits |
|---|---|---|
| `bionic/code/` | Auto-extracted from source code (docstrings, @doc, JSDoc) | **Regenerated — never edit by hand.** Hand edits are deleted on every extract run. |
| `bionic/research/` | Articles, papers, web pages, meeting notes, chat exports | You drop sources in the unified `bionic/inbox/`; `process-inbox` routes them to `ingest-research`, which captures each into the immutable `bionic/research/raw/` and runs the ingest pipeline |
| `bionic/adrs/` | Architecture Decision Records — the "why" of every load-bearing decision | You decide; Claude writes the ADR. **Once `Accepted`, the body is frozen.** |
| `bionic/briefs/` | Pre-decision exploration documents (`BRIEF-<slug>.md`) | You write; Claude tracks them |
| `bionic/journal/` | Day-by-day record of work performed (`YYYY-MM.md`) | Claude appends entries; you ask for them |
| `bionic/promptbooks/` | Plans of prompts you'd like to execute, plus immutable run snapshots | Co-authored. Mutable plan + frozen run history |
| `bionic/invariants/` | Pinned, executable statements of *what must be true* — a ledger page per pin plus the executable check suite in `invariants/checks/`, reconciled via `invariants/reconciliation.yml` | **Machine proposes, you ratify.** `recover-invariants` mines candidates as `observed`; you ratify/reject/retire via `transition-invariant`. Recovery never self-ratifies. |
| `bionic/observations/` (default-on) | Records of what the code *already does* (`OBS-NNNN-<slug>.md`), each evidenced by a `path:line-range` and never by a code excerpt | **You write, you ratify.** `propose-observation` scaffolds one as `observed`; `transition-observation` is the only single-record route past `observed`, to `ratified`, `rejected`, `retired`, or `decided`. The batch sign-off is the only batch route. No scan writes an observation file in any state. |
| `bionic/arch/` (default-on) | Derived architecture spine — the current-state map: data model, interface surface, module graph, decision index, plus a synthesized overview | **Regenerated — never edit by hand.** Built on demand by `derive-arch`; enrolled by default on new trees (existing trees opt in by adding `arch` to `concerns_enabled`). |

The seventh concern, **invariants**, is the "far half of the bridge": where the other concerns record knowledge, invariants pin *what must stay true* as executable checks that survive regeneration. A new repo stands it up empty — an invitation to run `recover-invariants` when you're ready; an empty invariants concern is clean, not broken.

Beyond the seven, there is a **default-on eighth surface: `bionic/arch/`** — the derived architecture. It is the primary place to answer *"how is this project shaped right now?"*: a deterministic spine (data model, interface surface, module graph, decision index) plus a synthesized overview, all regenerated wholesale from the project's own sources. ADRs are the secondary path (the *why*); the librarian and historian fill the gaps. arch is **default-on for new repos** (init-docs enrolls it), so just say **"build the arch"** to derive it, and keep it current with `derive-arch` (or let `audit-docs` auto-regenerate it on drift). An **existing tree that predates the default** opts in first by adding `arch` to `concerns_enabled`, then derives. Like `code/`, it is never hand-edited.

There is a **second default-on surface: `bionic/observations/`** — the record of what the code already does. An observation describes; it does not decide. Where an ADR records a choice somebody made, an observation records a fact nobody ever wrote down, evidenced by a `path:line-range` into the real source. A repository that has never authored an ADR uses observations as its starting layer, and a repository full of ADRs uses them for everything the ADRs never covered. Say **"propose observation"** to scaffold one; it lands as `observed`. Only you move it past that: `transition-observation` is the only single-record route, and `survey-signoff` the only batch route. No scan ever writes or ratifies one. Ratified records feed the same summaries and doctrine projections the ADRs feed, so an observation earns real authority once you have affirmed it.

The batch route runs in two steps and covers as many candidates as you put on one sheet. Say **"scaffold a survey sheet"** and `survey-sheet` builds one sheet over the candidates in `observed`, seeding each row with a claim and a proposed domain. You author the rest of each row: a verdict of `ratify`, `reject`, or `defer`, a one-line rationale, and a domain that overrides the proposed one where it is wrong. Say **"sign off the survey"** and `survey-signoff` renders every claim and its verdict for you to read. It publishes the batch under one digest-bound receipt once you confirm, so one signature covers every ratification in it. Both commands are yours to invoke, and neither runs unattended.

---

## The agent layer

crux ships ten **agents** that operate the skills above. Claude Code loads the agents from the plugin. Codex and OpenCode use generated native forms.

- **commander** runs a promptbook/cycle and delegates everything (never edits).
- **brainstormer** explores a design with you (drives the `whiteboarding` skill), then hands the session to the historian to file.
- **architect** owns ADRs and decisions (drafts, runs the council, accepts).
- **dev-lead** leads implementation and fans independent work out to **developer**s.
- **reviewer** independently reviews code — read-only, so it reports findings and never fixes-and-hides.
- **historian** owns every write under `bionic/`.
- **librarian** answers questions from `bionic/` (read-only retrieval).
- **wayfinder** goes ahead and finds the way through large/uncertain or external data — reads it in an isolated context, judges its fitness for your purpose, and returns a verdict + condensed digest so a primary spends its own context only on proven-fit content (read-only; the only agent with `WebFetch`/`WebSearch`, fenced by an egress guardrail).
- **night-gardener** is the overnight presence — runs as a scheduled routine, reviews what changed since your last move, and leaves a morning note under `bionic/garden/` (ideas, codebase improvements, missing tests/CI/guards, research, news). Turn-based (skips when only her own work changed), full co-CTO behind existing gates, never pushes. Dismiss or snooze her advice via `bionic/garden/tending.md` — no acknowledgment needed. Her news pass reads a curated source list via the `read-news` skill.

Each role declares tool boundaries and required skills. Host permissions can override a role's default sandbox, so the role prompt remains binding. The agents embed the craft disciplines they need, including testing, verification, debugging, and two-stage review.

| Agent | Reach for it when you want… | Bounded so it cannot… |
|---|---|---|
| `commander` | a whole cycle/promptbook driven end-to-end (it delegates each step) | edit code or docs itself |
| `brainstormer` | to explore a fuzzy idea before committing (drives `whiteboarding`) | write files or touch code |
| `architect` | a decision recorded + council-reviewed (`propose-adr` → `council` → accept) | implement code |
| `dev-lead` | implementation coordinated across parallel units | merge / push (human-gated) |
| `developer` | one scoped unit built test-first | re-delegate, or write docs/ADRs |
| `reviewer` | an independent check of a diff | edit files (it reports; never fix-and-hide) |
| `historian` | anything written under `bionic/` (intake, journaling, indexes) | edit source code |
| `librarian` | a question answered from `bionic/` (`query-docs`) | write anything |
| `night-gardener` | an overnight pass that records ideas, gaps, research, and news | push, merge, or send material externally |
| `wayfinder` | a large/uncertain or external source triaged for context-fitness + condensed before you read it | write, execute, delegate, or relay local content outbound |

In Codex, say **"install the Crux agents in Codex"** after installing the plugin. The installer writes the ten namespaced `crux_*` roles to `~/.codex/agents/` by default. Each role pins its catalog model and reasoning effort and binds its declared skills to the installed plugin. An explicit `--repo-root` selects one project's `.codex/agents/` directory.

An unchanged refresh is a no-op. Changed or stale managed files require `--force` after review. Plugin relocation appears as drift because skill bindings use absolute paths. `--check --project-context <repo>` reports managed drift and project agents that shadow personal roles. The report separates canonical expectations from managed TOML state parsed from disk. Its runtime result stays `unverified` until fresh-session host evidence confirms discovery, settings, skills, and representative workflows for the selected Codex version.

**How you actually use them:** you rarely name an agent — a cycle (and the `commander`) dispatches them for you. But you can be explicit: *"have the architect propose an ADR for X"*, *"send this design to the council"*, *"have the reviewer check the diff"*, *"ask the librarian what we decided about Y"*.

---

## What to say to Claude

These phrases trigger the right skill. Use them in natural-language sentences; Claude figures out the rest.

### Recording decisions

- **"Propose an ADR for X"** → Claude writes a new `ADR-NNNN-<slug>.md` in `bionic/adrs/`, status `Proposed`. You review the alternatives, then…
- **"Accept ADR-NNNN"** → Status flips to `Accepted`. Body is now frozen.
- **"Supersede ADR-NNNN with ADR-MMMM"** → Both ends of the supersession link update atomically.
- **"Deprecate ADR-NNNN"** → Decision retracted (no replacement).
- **"Sign off backfill batch <id>"** → the owner sign-off for one governs backfill batch (`backfill-signoff`). Every enumerated receipt's rule and anchor renders verbatim for your read before anything writes; the script is the only write path onto the backfill surfaces (signed-date flip, admission ledger, log op, journal hook, completion marker). Never hand-edit those surfaces.

ADRs are append-only history. You can't edit one once accepted; you write a new one that supersedes it.

### Capturing anything — the unified inbox

There is **one** place to drop raw input: `bionic/inbox/`. Drop any kind of item there — a research file, a pasted URL, a half-formed decision note, a stray idea — then say **"process inbox"**. The `process-inbox` skill classifies each item, shows you a confirmation table (item → proposed skill → confidence), and on your `ok` dispatches each to the skill that owns its concern:

- research source (file, URL, or a `urls.md` manifest) → `ingest-research`
- architectural decision → `propose-adr`
- pre-decision exploration → `propose-brief`
- work-log note → `log-work`

Classification is **classify-then-confirm**: only items Claude is confident about auto-dispatch on `ok`; anything unsure is held back for you to `override N=<target>` or `defer N`. ADRs are only ever created as `Proposed` — `process-inbox` never auto-accepts.

**Research flows through `ingest-research`.** When a dropped item is classified as research, it goes through the ingest pipeline — moved into a dated, immutable `bionic/research/raw/` capture, with an audited source page and synthesis updates.

- **Drop a file in `bionic/inbox/`** and say "process inbox" — research items are moved to a dated `raw/` capture, get an audited source page, and update synthesis pages.
- **Paste a URL** into a file under `bionic/inbox/` (or hand it to Claude) and say "ingest this" — same pipeline, fetched via the bundled `web-to-markdown.py`.
- **Bulk import**: drop a `urls.md` file in `bionic/inbox/` with one URL per line. Add `(static)` after a URL to opt it out of refresh checks. A partially-drained `urls.md` is left in place and retried on the next run.

When upstream sources may have changed:
- **"Refresh sources"** → re-fetches non-static URLs, files updates as new dated captures, flags affected synthesis pages.
- **"Refresh synthesis"** → walks you through accumulated markers (contradictions, source updates) per page.

### Journaling work

- **"Log work"** or **"journal this"** → adds an entry to `bionic/journal/YYYY-MM.md` with today's date and a category.
- Claude may also call this silently after meaningful operations (ADR accepted, promptbook completed, large refactor).

Categories: `decision | implementation | bug | learning | blocker | refactor | meeting | review | misc`.

### Planning multi-step work — promptbooks & cycles

Several ways to drive multi-step work, in increasing rigor:

- **"Start a cycle for X"** (`dev-cycle`) — for **net-new / architectural** work. Assembles a tracked promptbook of ADR + dev + review modules: a decision is recorded as an ADR and council-reviewed, implemented, then independently reviewed (≥13 prompts).
- **"Iterate on X"** / **"remediate X"** (`iterate`) — for **non-architectural fixes** (bugs, drift, refinements to existing behavior). Same council + review rigor, but a *verify* module (reproduce + root-cause + council-review the diagnosis) instead of an ADR — there's no decision to record. If the verify council finds the work *is* actually architectural, it stops and routes you to `dev-cycle`.
- **"Patch this"** (`patch-cycle`) — for a **small reversible** non-architectural change you can bound by naming the paths it may touch. Five phases (verify, plan, implement, review, summary), one prompt each. You declare a *blast radius* up front: the council checks it is no wider than the work needs, and archival checks the paths the run actually changed against it, using git. A change that reaches outside the declaration cannot archive as delivered — it is re-authored as an `iterate` or a `dev-cycle`. Work needing an ADR is not a patch.
- **"Just fix it"** (`fix-directly`) — for a defect whose files, failing test, and unchanged contracts you can name before starting. No book, no council, no promptbook number: a failing test first, the smallest change that turns it green, the suite and the drift gates, one commit, one journal entry. A security label sets a defect's priority, not its size; the sizing test sets the tier.
- **"New promptbook for X"** (`author-promptbook`) — a bespoke multi-prompt plan you co-author, with **no** enforced council/review. For sequences that don't need the ceremony.

Then drive any of them: **"run it"** starts an immutable run snapshot under `bionic/promptbooks/runs/<book-id>-<slug>/run-RUN-NNN.yaml`; **"advance"** / **"next prompt"** marks the current prompt done and moves on; **"abandon this run"** closes a run that will not finish; **"archive promptbook"** closes the book once its run has either completed with every prompt terminal (done / skipped / blocked) or been deliberately abandoned.

Books and runs are structured `.yaml` documents validated against a JSON Schema (the cycle kinds also pass the cycle-coverage invariants). Edit the prompts list mid-run? You can't — abandon the run, then author a successor book that names its predecessor. Numbers are never reused.

### Extracting code docs

- **"Extract code docs"** → runs the extraction dispatcher per `bionic/manifest.yml`. Regenerates `bionic/code/` from source.
- **"Verify code docs"** → dry-run version. Reports drift without writing.

Configure which extractors run by editing `code.extractors:` in `bionic/manifest.yml`. Day-one extractors: Elixir, fallback (header-comment scrape). More languages land as extractor plugins in the installed plugin.

### Summarizing the current architecture

- **"Build the arch"** / **"summarize the current architecture"** / **"regenerate the architecture"** → runs `derive-arch`, which detects your stack and regenerates `bionic/arch/` — the derived current-state map — wholesale from the project's own sources. Batteries-included packs cover Python, Ruby, Node.js, and Elixir/Phoenix. Each pack derives the data model from your ORM or schema (SQLAlchemy, SQLModel and Django models; ActiveRecord's `schema.rb`; Prisma, TypeORM and Sequelize; Ecto). It derives the interface surface from a committed OpenAPI document or the framework's routes, and the module graph from the import graph. Each concern gets a `populated | stubbed` verdict, recorded in `_meta/coverage.json`. The same verdicts print as a coverage table, with one remediation line per non-`populated` concern. The tool reports what it found and grades nothing. A machine missing a stack's declared parser (`tree-sitter` plus its grammar — Elixir needs `tree-sitter-elixir`; Node.js and Ruby also declare grammars) gets exit 2 with nothing written; the fix is the environment, not the docs.
- **"What's the current architecture?"** → read `bionic/arch/overview.md` (or ask the librarian). Building is `derive-arch`'s job; answering from it is the librarian's.
- **"Escalate the arch runtime"** (`escalate-arch-runtime`; Python projects; you invoke it explicitly — it never auto-fires) → an optional fidelity upgrade you may choose, never the remedy `derive-arch` points you at. Recovers what the static extractor missed — the route table, the ORM schema — by running your FastAPI/Flask/Django app's import-time code in a confined subprocess, behind the `CRUX_ARCH_ALLOW_RUNTIME=1` consent gate plus a per-run permission prompt. Results land in `bionic/inbox/` as advisory material, never in `bionic/arch/`.

arch is **default-on for new repos** (init-docs enrolls it), so on a fresh tree you just build it. On an **existing tree that predates the default**, enable it first by adding `arch` to `concerns_enabled` in `bionic/manifest.yml`, then build it. Keep it current by re-running `derive-arch` after a change to any input, or let a routine **"audit docs"** auto-regenerate a drifted spine. Never hand-edit `bionic/arch/` — the next derive overwrites it.

### Asking questions

- **"What does X do?"** → searches `bionic/code/`, cites pages.
- **"Why did we choose Y?"** → searches `bionic/adrs/` and `bionic/briefs/`.
- **"What's the plan for Z?"** → checks active promptbooks.
- **"What do we know about W?"** → searches research.

Good answers can be filed back into `bionic/research/ideas/` — Claude will offer.

### Checking health

- **"Audit docs"** → runs ~54 integrity checks across every enabled concern. Auto-fixes safe drift (counts, dates, missing index rows); surfaces broken cases for your decision.

Run after every ~10 writes, after a large refresh, before any release.

- **"Review the decisions"** / "run a decision review" / "decision review" / "do the decisions still serve the objectives" / "review the ADR set against the objectives" / "is the decision set still right" → `review-decisions` reads the decision set and measures it against `bionic/objectives.md`. It writes one dated report per pass at `bionic/adrs/reviews/YYYY-MM-DD.md`. **Findings live in four sections — Propose, Amend, Repair, and Revoke — and at most five findings survive across all four, per pass.** Two further sections carry no findings and no cap: Keep lists decisions read this pass that still serve, and Coverage names what the pass could not see. Zero findings is a legitimate outcome. The report is hand-kept; only `bionic/adrs/reviews/index.md` is regenerated. The boundary: the review proposes findings and transitions nothing. Enacting a finding is a separate act — "propose ADR" or "accept ADR-NNNN" — that the review never invokes.

Run the review weekly. `cleanup-campsite` nudges when the newest report is older than `adr_review_due_days`, which is seven by default.

---

## Tools & scripts

Everything Claude does is backed by Python scripts shipped inside the installed plugin (under `${CLAUDE_PLUGIN_ROOT}/scripts/`) — stdlib-only for the docs tooling; the multi-model substrate (below) adds PEP 723-declared dependencies. **You almost never run these directly** — the skills invoke them for you — but knowing they exist helps when something looks off.

**Invoked by skills (you don't run these):**

| Script | Skill that calls it | What it does |
|---|---|---|
| `extract-code-docs.py` | `extract-code-docs` / `verify-code-docs` | Regenerates `bionic/code/` from source docstrings, via per-language extractor plugins. |
| `web-to-markdown.py` | `ingest-research` / `refresh-research-sources` | Fetches a URL into audited markdown. |
| `transcribe-video.py` | `ingest-research` | Transcribes a video source to text. |
| `migrate-promptbooks.py` | `migrate-promptbooks` | Translates legacy `.md` books/runs → structured `.yaml`. |
| `visualize-run-progress.py` | `visualize-run-progress` | Renders a run snapshot as a terminal progress bar + a byte-stable markdown artifact. |
| `validate-promptbook.py` | `dev-cycle` / `iterate` / `patch-cycle` / `archive-promptbook` | Validates a promptbook or run `.yaml` against its JSON Schema **and** the cycle-coverage invariants (`--kind promptbook\|run`). Never publishes. |
| `check-blast-radius.py` | `archive-promptbook` | Compares a `patch` run's git-recorded changed paths against the blast radius its book declared. |

> **PyYAML requirement.** `validate-promptbook.py`, `migrate-promptbooks.py`, and `visualize-run-progress.py` require a real YAML parser — the bundled minimal fallback isn't faithful enough for validation verdicts or content hashes. Without PyYAML they automatically re-run themselves under `uv run --no-project --with pyyaml>=6.0` when `uv` is installed (announced on stderr; may fetch PyYAML from your configured index on first use), or exit **2** with a remediation message — exit 2 always means *your environment*, never *your docs*. Locked-down environments can set `CRUX_NO_UV_REEXEC=1` to disable the auto-repair and install PyYAML themselves.
>
> **Dependency resolution for shipped scripts (PEP 723).** Shipped scripts whose documented invocation is `uv run …` carry PEP 723 inline metadata; on first use, `uv` resolves those dependencies — **unpinned by hash** — from *your configured index* (cached afterwards). Same trust model as the PyYAML re-exec above. Hermetic or locked-down environments should pre-provision the declared dependencies themselves rather than letting first use touch the network; for stricter reproducibility pin resolution with `uv run --exclude-newer <date>` (or the `UV_EXCLUDE_NEWER` environment variable). `uv` itself is a prerequisite for those invocations — without it the command fails at the shell (`command not found`); install it from https://docs.astral.sh/uv/.

**The multi-model substrate** ships with the plugin: the LLM router (`call-llm`), the multi-model `council`, `srde`, the tracer, and the identity / knowledge / task-planning modules that power the agent layer. These need API keys (next section) and run under `uv` (Python ≥3.11, per each script's PEP 723 header); `serve-llm` exposes the router over HTTP for non-Python clients. The **`forge-skill` capability-gap loop** (below) is a prose workflow — it needs no API keys of its own.

**`forge-skill`** closes a capability gap mid-task by autonomously authoring or revising a project-local skill under `.claude/skills/`. Trigger phrases: *"forge a skill"*, *"author a skill for this"*, *"close this capability gap"*. It runs autonomously and reports after the fact — propose-first (wait for approval) applies only when the capability is outward-facing or irreversible (external sends, spend, publishing), would touch anything outside the repo or any secrets, or when the gap would change project structure or external surfaces (those take the brief/ADR path instead). Every forge act is recorded in the append-only **forge log at `.claude/skills/forge-log.md`** — a reviewable history of what was authored, when, and why.

**`retrospective`** is purposeful reflection over finished work. Trigger phrases: *"what should we learn from recent work"*, *"run a retrospective"*, *"retrospective over the last N books"*. It mines `bionic/log.md`, the work journal, and recent run snapshots to surface patterns; distills findings into ≤2 skill proposals; gates each proposal through the council before building it via `forge-skill`. Outcomes are recorded with a `Retrospective:` journal entry (the `## [YYYY-MM-DD HH:MM] learning | Retrospective: …` heading) — the marker `cleanup-campsite` tracks to nudge you when enough archived books have accumulated since the last retrospective.

The **`crux-env` CLI** keeps your API keys outside any repo — its own section follows.

---

## Working with secrets and API keys

`~/.crux/` is your per-user secrets home, outside any repo. One file (`~/.crux/env`) holds all API keys for every project on your machine that uses crux. The keys never leave your machine and never live in git.

You manage it with the `crux-env` CLI, which ships inside the installed plugin. The canonical invocation is:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" <subcommand> …
```

`${CLAUDE_PLUGIN_ROOT}` is the plugin's installed root — Claude Code sets it inside sessions, so it resolves to wherever the marketplace installed crux on your machine. The examples below abbreviate that invocation to `crux-env` — define your own shell alias if you use it often. The commands below are the whole interface.

### One-time setup

```
crux-env init
```

Creates `~/.crux/` with the right file modes (`0600` on `env`, `0700` on `secrets/`). Idempotent — re-running on an existing setup is safe.

### Adding a key

```
crux-env set OPENROUTER_API_KEY sk-or-xxxxxxxxxxxxxx
```

The value is stored in `~/.crux/env`, mode `0600` — only you can read it. The key **name** is recorded in `~/.crux/log/crux-env.log`; the **value is not**. The log is safe to share for debugging.

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

`✓` means set; `✗` means missing. Values are never printed — only key names.

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

- ❌ **Never commit `~/.crux/` to git.** It lives outside your repo by design — don't symlink it in.
- ❌ **Never share `~/.crux/env`.** The mode-`0600` protection only matters if it's not posted to Slack.
- ❌ **Never paste a key into an issue, PR description, chat message, or screenshot.**
- ❌ **Never edit `~/.crux/log/crux-env.log`** to hide that you rotated a compromised key. The log is the audit trail.
- ✅ **Do rotate** any key you suspect was leaked — the cost is one `set` command.

### Where to read more

- Your project's `bionic/CLAUDE.md` §13 — the full byte-level spec for the secrets store and CLI contract.

---

## Per-project configuration: the repo-root `.bionic.yml` file

Don't confuse these two crux config surfaces: the committed repo-root **`.bionic.yml` FILE** is per-project configuration; the user-home **`~/.crux/` DIRECTORY** (above) is your secrets store and is never committed.

A default `.bionic.yml` reads:

```yaml
config_version: "1"
docs_dir: bionic
artifact_prefix: ""
```

`.bionic.yml` supersedes the legacy `.crux` file (still read for back-compat). Every tree crux creates or migrates carries one — `init-docs` writes it on bootstrap, and `audit-docs --migrate` writes it on the 4→5 upgrade — so the layout is a read rather than an inference. Commit changes to it when you want a non-default convention:

- **`docs_dir`** — relocate the tree (e.g. `documentation/` or `meta/docs/`). Repo-root-relative, no absolute paths, no `..`. The default is `bionic`.
- **`artifact_prefix`** — brand artifact ids so they're distinguishable across repos: with `artifact_prefix: "CRX"`, new ADRs get ids like `CRX-ADR-0012`, and new promptbooks are prefixed the same way. Existing artifacts are never renamed.

To use a non-default `docs_dir` in a new repo, copy the shipped template to the repo root and edit it **before** you say "init docs" — `init-docs` writes this file itself when it is absent and merges (never clobbers) one you already committed:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/templates/bionic-yml.tmpl" .bionic.yml
```

Validation is fail-loud: a malformed or invalid `.bionic.yml` makes every consumer exit `1` with the validation error rather than silently falling back to defaults. Check yours with:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bionic-config.py"    # prints the resolved config as JSON
```

- ❌ **Never put secrets, tokens, or API keys in `.bionic.yml`.** It is committed to git, and unknown keys are silently ignored — a misfiled secret wouldn't even produce an error. Secrets go in `~/.crux/` (above), full stop.

Full contract: your project's `bionic/CLAUDE.md` §14.

---

## Where to look first

You've just opened a crux-managed project. Read in this order:

1. **`bionic/CLAUDE.md`** (~1000 lines — skim §1–§7 first) — the operational schema. The single source of truth for what lives where and who edits what.
2. **`bionic/index.md`** — rollup catalog of everything. Section per concern with counts.
3. **`bionic/adrs/`** — start at the lowest-numbered ADR, walk forward in number order. This is the "why" of the project.
4. **`bionic/journal/`** — the most recent month tells you what's happening now.
5. **`bionic/research/sources.md`** — registry of external context the project draws from.
6. **`bionic/promptbooks/index.md`** — what work is in flight.

---

## What you should NEVER do

- ❌ **Edit anything in `bionic/code/`.** Hand edits are deleted on every extract run.
- ❌ **Edit an ADR body once it's `Accepted`.** Write a new ADR that supersedes it.
- ❌ **Reorder `bionic/log.md` or edit past entries.** It's append-only audit history.
- ❌ **Delete `bionic/research/raw/`.** Old captures are the audit chain.
- ❌ **Reuse an ADR or promptbook number.** Numbers are monotonic forever.
- ❌ **Manually edit `bionic/research/sources.md` rows.** Let `ingest-research` and `audit-docs` maintain it.

If something feels wrong (a contradiction, a stale page, a missing source), say so. Don't fix it silently — the system catches drift via `audit-docs`, and your nose for "this looks off" is the canonical trigger.

---

## What you SHOULD do by hand

- Write `bionic/briefs/BRIEF-<slug>.md` files — these are *your* pre-decision exploration. Claude tracks them but doesn't author them.
- Co-author the `## Goal`, `## Strategy`, and `## Prompts` sections of an active promptbook.
- Edit the repo-root `CLAUDE.md` to add project-specific notes Claude should know about (just don't remove the `See bionic/CLAUDE.md` line).

---

## Day-one quick start

You're in a fresh repo with `bionic/` just initialized. To start using it:

1. **Capture today's intent as an ADR.** Say: *"Propose an ADR explaining why we're using crux for this project."* You'll review, then *"Accept ADR-0001."*
2. **Capture the planning material.** Drop your existing design notes / specs / chat exports into `bionic/inbox/` and say *"Process inbox."* Claude classifies each item and routes the research ones through `ingest-research`.
3. **Plan the first chunk of work.** Say: *"New promptbook for <thing>."* Co-author the prompt list. Then *"Run it."*
4. **Journal at end of day.** Say: *"Log today's work — `<one line summary>`."*
5. **Audit after the first ten writes.** Say: *"Audit docs."* Confirm there's no drift.

---

## When things go wrong

| Symptom | Try this |
|---|---|
| "Where did Claude put X?" | Look at `bionic/index.md` and `bionic/<concern>/index.md`. |
| `bionic/code/` has stale content | Run *"extract code docs"* — it regenerates fully. |
| ADR was accepted but it's wrong | Don't edit — write a new ADR that supersedes it. |
| Research synthesis page contradicts itself | Run *"refresh synthesis"* — Claude walks you through reconciliation. |
| Lost track of a promptbook's progress | `bionic/promptbooks/index.md` shows current_run and percent complete. |
| A script exits `2` | Your environment, not your docs — read the remediation message (usually a missing parser, PyYAML, or `uv`). |
| Whole `bionic/` tree feels broken | Run *"audit docs"* — the full check set across all concerns. |

---

## Plugin and schema

crux maintains your project's documentation tree at `schema_version 5` (the `bionic/` layout). The installed plugin lives at `${CLAUDE_PLUGIN_ROOT}`. In Claude Code, install or upgrade with `/plugin marketplace add bionic-coding/crux` and `/plugin install crux@crux`. In Codex, use `codex plugin marketplace add bionic-coding/crux` and `codex plugin add crux@crux`. After upgrading, run *"audit docs --migrate"* if the tree uses an older `schema_version`. Codex users can install the ten Crux role agents personally with the `install-codex-agents` skill.

When the plugin's schema changes, run *"audit docs --migrate"* to bring `bionic/` up to date.
