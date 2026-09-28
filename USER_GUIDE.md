<!-- generated-from: USER_GUIDE.md@sha256:3c0ea1a364e3d6f0f97ddc65be40b46a6a443d9414794b809aad2792329d2060; model: claude-opus-5.5; date: 2026-09-27 -->
# Working with crux

crux keeps your project's documentation in a `bionic/` tree. The tree holds seven concerns plus two default-on surfaces, `arch` and `observations`. **You do not write these docs by hand.** You curate, decide, and discuss, and Claude does the bookkeeping.

This guide is for humans. If you are an LLM agent working in a crux-enabled repo, read `bionic/AGENTS.md`. That file is the operational schema.

---

## At a glance

crux turns a `./bionic/` folder into a maintained knowledge base that you and Claude share. It has four moving parts:

1. **The `bionic/` tree.** It holds seven concerns: code docs, research wiki, ADRs, briefs, work journal, promptbooks, and invariants. It also holds two default-on surfaces: the derived `arch` map and the `observations` records. You curate and decide, and Claude does the bookkeeping. → [The seven concerns](#the-seven-concerns)
2. **52 skills, triggered by natural language instead of slash commands.** Examples: "propose an ADR", "process inbox", "audit docs", "start a cycle", "forge a skill". Claude matches each phrase to a skill through the skill's description. → [What to say to Claude](#what-to-say-to-claude). The plugin's `README.md` has the full catalog.
3. **10 agents, a role layer over the skills.** A `commander` delegates to `architect`, `dev-lead`, `developer`, `reviewer`, `historian`, `librarian`, `brainstormer`, and `wayfinder`. A `night-gardener` runs overnight. Each agent has a tool allowlist, so duties are separated by structure. → [The agent layer](#the-agent-layer)
4. **Three workflows for change.** All three are tracked promptbooks.
   - `dev-cycle` handles net-new or architectural work: an ADR, a council, and a review.
   - `iterate` handles non-architectural fixes: verification, a council, and a review, with no ADR.
   - `patch-cycle` handles a small reversible fix: five phases, one prompt each, with a declared blast radius.

   For a defect whose fix you can name before starting, use `fix-directly`. It needs no book and starts with a failing test. → [Planning multi-step work](#planning-multi-step-work--promptbooks--cycles)

Under the hood, the skills call Python **scripts** for you: extractors, validators, and the LLM router. The `crux-env` **CLI** manages secrets. → [Tools & scripts](#tools--scripts)

**If you read nothing else:**

- Drop anything into `bionic/inbox/` and say *"process inbox"*.
- Ask *"what does X do?"* or *"why did we choose Y?"*.
- Say *"start a cycle for X"* or *"iterate on X"* to ship a change with a full record attached.

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

_This guide uses the default `bionic/` layout. If your repo sets a custom `docs_dir`, that directory replaces `bionic/` everywhere below. See [Per-project configuration](#per-project-configuration-the-repo-root-bionicyml-file)._

| Directory | What lives there | Who edits |
|---|---|---|
| `bionic/code/` | Docs extracted automatically from source code (docstrings, @doc, JSDoc). | **Regenerated. Never edit by hand.** Every extract run deletes hand edits. |
| `bionic/research/` | Articles, papers, web pages, meeting notes, chat exports. | You drop sources in `bionic/inbox/`. `process-inbox` routes them to `ingest-research`, which captures each one into the immutable `bionic/research/raw/` and runs the ingest pipeline. |
| `bionic/adrs/` | Architecture Decision Records: the reasoning behind every load-bearing decision. | You decide, and Claude writes the ADR. **Once an ADR is `Accepted`, its body is frozen.** |
| `bionic/briefs/` | Pre-decision exploration documents (`BRIEF-<slug>.md`). | You write them, and Claude tracks them. |
| `bionic/journal/` | A day-by-day record of work performed (`YYYY-MM.md`). | Claude appends entries when you ask. |
| `bionic/promptbooks/` | Plans of prompts to execute, plus immutable run snapshots. | Co-authored. The plan is mutable, and the run history is frozen. |
| `bionic/invariants/` | Pinned, executable statements of what must stay true. Each pin has a ledger page. The executable checks live in `invariants/checks/` and are reconciled via `invariants/reconciliation.yml`. | **The machine proposes, and you ratify.** `recover-invariants` mines candidates as `observed`. You ratify, reject, or retire them with `transition-invariant`. Recovery never ratifies its own candidates. |
| `bionic/observations/` (default-on) | Records of what the code already does (`OBS-NNNN-<slug>.md`). Each one cites a `path:line-range` as evidence and never includes a code excerpt. | **You write, and you ratify.** `propose-observation` creates a record as `observed`. `transition-observation` is the only way to move a single record past `observed`, to `ratified`, `rejected`, `retired`, or `decided`. The survey sign-off is the only batch route. No scan writes an observation file in any state. |
| `bionic/arch/` (default-on) | The derived architecture map of the current state: data model, interface surface, module graph, and decision index, plus a synthesized overview. | **Regenerated. Never edit by hand.** `derive-arch` builds it on demand. New trees enroll it by default. Existing trees opt in by adding `arch` to `concerns_enabled`. |

### Invariants

The seventh concern, **invariants**, works differently from the others. The other concerns record knowledge. Invariants pin what must stay true, as executable checks that survive regeneration. A new repo starts with an empty invariants concern. Run `recover-invariants` when you are ready. An empty invariants concern is clean, not broken.

### The arch surface

Beyond the seven concerns, **`bionic/arch/`** is a default-on surface that holds the derived architecture. It is the primary place to answer *"how is this project shaped right now?"*

- It contains a deterministic core (data model, interface surface, module graph, decision index) and a synthesized overview.
- It is regenerated wholesale from the project's own sources.
- ADRs are the secondary path and explain the reasoning. The librarian and historian fill the gaps.

On a new repo, `init-docs` enrolls arch automatically. Say **"build the arch"** to derive it, and keep it current with `derive-arch`. A routine `audit-docs` also regenerates it when it drifts. A tree created before arch became the default opts in first: add `arch` to `concerns_enabled`, then derive. Like `code/`, arch is never hand-edited.

### The observations surface

**`bionic/observations/`** is the second default-on surface. It records what the code already does.

- An observation describes. It does not decide. An ADR records a choice somebody made. An observation records a fact nobody wrote down, with a `path:line-range` into the real source as evidence.
- A repository with no ADRs can use observations as its starting layer. A repository full of ADRs uses them for everything the ADRs never covered.
- Say **"propose observation"** to create one. It starts as `observed`.
- Only you can move it past `observed`. `transition-observation` is the only single-record route, and `survey-signoff` is the only batch route. No scan ever writes or ratifies an observation.
- Ratified observations feed the same summaries and doctrine projections that ADRs feed. An observation carries real authority once you affirm it.

The batch route has two steps and covers as many candidates as you put on one sheet:

1. Say **"scaffold a survey sheet"**. `survey-sheet` builds one sheet over the candidates in `observed` and fills each row with a claim and a proposed domain. You complete each row with:
   - a verdict of `ratify`, `reject`, or `defer`
   - a one-line rationale
   - a domain, which overrides the proposed one where it is wrong
2. Say **"sign off the survey"**. `survey-signoff` shows every claim and its verdict for you to read. Once you confirm, it publishes the batch under one digest-bound receipt, so one signature covers every ratification in the batch.

You invoke both commands yourself. Neither runs unattended.

---

## The agent layer

crux ships ten **agents** that operate the skills. Claude Code loads the agents from the plugin. Codex and OpenCode use generated native forms.

- **commander** runs a promptbook or cycle and delegates every step. It never edits.
- **brainstormer** explores a design with you by driving the `whiteboarding` skill. It then hands the session to the historian to file.
- **architect** owns ADRs and decisions: it drafts them, runs the council, and accepts them.
- **dev-lead** leads implementation and hands independent work to **developer** agents.
- **reviewer** reviews code independently. It is read-only, so it reports findings and never quietly fixes them.
- **historian** owns every write under `bionic/`.
- **librarian** answers questions from `bionic/`. It only reads.
- **wayfinder** triages large, uncertain, or external data before a primary agent reads it.
  - It reads the data in an isolated context and judges whether it fits your purpose.
  - It returns a verdict and a condensed digest, so the primary agent spends context only on content that has proven useful.
  - It is read-only. It is the only agent with `WebFetch` and `WebSearch`, and an egress guardrail limits what it can send out.
- **night-gardener** runs as a scheduled routine overnight.
  - It reviews what changed since your last move and leaves a morning note under `bionic/garden/`. The note covers ideas, codebase improvements, missing tests, CI, or guards, research, and news.
  - It works in turns and skips a night when only its own work changed.
  - It acts as a full co-CTO behind the existing gates and never pushes.
  - Dismiss or snooze its advice in `bionic/garden/tending.md`. No acknowledgment is needed.
  - Its news pass reads a curated source list through the `read-news` skill.

Each role declares tool boundaries and required skills. Host permissions can override a role's default sandbox, but the role prompt still binds the agent. The agents include the working disciplines they need, such as testing, verification, debugging, and two-stage review.

| Agent | Reach for it when you want… | Bounded so it cannot… |
|---|---|---|
| `commander` | a whole cycle or promptbook driven end-to-end, delegating each step | edit code or docs itself |
| `brainstormer` | to explore a fuzzy idea before committing (drives `whiteboarding`) | write files or touch code |
| `architect` | a decision recorded and reviewed by the council (`propose-adr` → `council` → accept) | implement code |
| `dev-lead` | implementation coordinated across parallel units | merge or push (a human does that) |
| `developer` | one scoped unit built test-first | re-delegate, or write docs or ADRs |
| `reviewer` | an independent check of a diff | edit files (it reports and never quietly fixes) |
| `historian` | anything written under `bionic/` (intake, journaling, indexes) | edit source code |
| `librarian` | a question answered from `bionic/` (`query-docs`) | write anything |
| `night-gardener` | an overnight pass that records ideas, gaps, research, and news | push, merge, or send material outside the repo |
| `wayfinder` | a large, uncertain, or external source judged for fit and condensed before you read it | write, execute, delegate, or send local content out |

### Installing the agents in Codex

After installing the plugin in Codex, say **"install the Crux agents in Codex"**. The `install-codex-agents` skill does the following:

- By default, it writes the ten namespaced `crux_*` roles to `~/.codex/agents/`.
- Each role pins its catalog model and reasoning effort, and binds its declared skills to the installed plugin.
- An explicit `--repo-root` writes to one project's `.codex/agents/` directory instead.

Refreshing behaves as follows:

- Re-running with no changes does nothing.
- Changed or stale managed files require `--force`. Review them first.
- Skill bindings use absolute paths, so moving the plugin shows up as drift.

To check an installation, run `--check --project-context <repo>`. It reports:

- drift in the managed files
- project agents that shadow personal roles

The report separates the expected state from the managed TOML state read from disk. The runtime result stays `unverified` until evidence from a fresh session confirms discovery, settings, skills, and representative workflows for your Codex version.

### How you use the agents

You rarely name an agent. A cycle, through the `commander`, dispatches them for you. You can still be explicit:

- *"have the architect propose an ADR for X"*
- *"send this design to the council"*
- *"have the reviewer check the diff"*
- *"ask the librarian what we decided about Y"*

---

## What to say to Claude

These phrases trigger the right skill. Use them in ordinary sentences, and Claude works out the rest.

### Recording decisions

| Say this | What happens |
|---|---|
| **"Propose an ADR for X"** | `propose-adr` creates a **new** `ADR-NNNN-<slug>.md` in `bionic/adrs/` with status `Proposed`. You then review the alternatives. |
| **"Accept ADR-NNNN"** | `transition-adr` changes an **existing** ADR's status to `Accepted`. The body is then frozen. |
| **"Supersede ADR-NNNN with ADR-MMMM"** | `transition-adr` updates both ends of the supersession link atomically. |
| **"Deprecate ADR-NNNN"** | `transition-adr` retracts the decision without a replacement. |
| **"Sign off backfill batch <id>"** | `backfill-signoff` records your sign-off for one backfill batch. See below. |

`propose-adr` only ever creates a new `Proposed` decision. `transition-adr` accepts, supersedes, or deprecates a decision that already exists.

Backfill sign-off works as follows:

- Before anything is written, every enumerated receipt's rule and anchor is shown to you word for word.
- The script is the only thing that writes to the backfill surfaces: the signed-date flip, the admission ledger, the log operation, the journal hook, and the completion marker.
- Never hand-edit those surfaces.

ADRs are append-only history. You cannot edit an accepted ADR. Instead, write a new one that supersedes it.

### Capturing anything: the unified inbox

There is **one** place to drop raw input: `bionic/inbox/`. Drop any kind of item there, such as a research file, a pasted URL, a half-formed decision note, or a stray idea. Then say **"process inbox"**.

`process-inbox` classifies each item and shows you a confirmation table: item, proposed skill, and confidence. When you reply `ok`, it sends each item to the skill that owns its concern:

| Item type | Skill |
|---|---|
| Research source (a file, a URL, or a `urls.md` manifest) | `ingest-research` |
| Architectural decision | `propose-adr` |
| Pre-decision exploration | `propose-brief` |
| Work-log note | `log-work` |

Claude classifies first and asks you to confirm:

- On `ok`, only items Claude is confident about are dispatched.
- Uncertain items are held back. Reply `override N=<target>` to reroute item N, or `defer N` to leave it for later.
- ADRs are only ever created as `Proposed`. `process-inbox` never accepts one.

**Research still flows through `ingest-research`.** An item classified as research goes through the full ingest pipeline. It moves into a dated, immutable capture under `bionic/research/raw/`, gets an audited source page, and updates the synthesis pages.

- **Drop a file** in `bionic/inbox/` and say "process inbox".
- **Paste a URL** into a file under `bionic/inbox/`, or hand the URL to Claude, and say "ingest this". The bundled `web-to-markdown.py` fetches it through the same pipeline.
- **Bulk import** by dropping a `urls.md` file in `bionic/inbox/` with one URL per line.
  - Add `(static)` after a URL to exclude it from refresh checks.
  - If only some URLs in `urls.md` are processed, the file stays in place and the rest are retried on the next run.

When upstream sources may have changed:

- **"Refresh sources"** re-fetches non-static URLs, files any updates as new dated captures, and flags the affected synthesis pages.
- **"Refresh synthesis"** walks you through the accumulated markers, such as contradictions and source updates, page by page.

### Journaling work

- **"Log work"** or **"journal this"** adds an entry to `bionic/journal/YYYY-MM.md` with today's date and a category.
- Claude may also call this silently after meaningful operations, such as an accepted ADR, a completed promptbook, or a large refactor.

Categories: `decision | implementation | bug | learning | blocker | refactor | meeting | review | misc | release`.

`log-work` picks one of two procedures before writing:

- **Interactive request.** It adds a reflective monthly entry, regenerates the journal index, and records one `journal` operation.
- **Silent call.** It defaults to log-only. It requires a valid operation and writes only `bionic/log.md`.

The bundled writer checks the request before writing and reports `complete`, `refused`, or `partial`. If you need to retry:

- Keep the original request and its explicit local UTC offset.
- A partial entry with only a month cannot prove that offset, so the writer warns `offset unverified`.
- If the offset was lost, stop automated replay and work out the offset from evidence.

A journal body allows 1–10 authored lines. An optional `Refs:` line does not count toward that limit.

### Planning multi-step work — promptbooks & cycles

These are the ways to drive multi-step work, roughly in order of increasing rigor:

| Say this | Skill | Use it for |
|---|---|---|
| **"Start a cycle for X"** | `dev-cycle` | Net-new or architectural work. It assembles a tracked promptbook of ADR, development, and review modules (at least 13 prompts). The decision is recorded as an ADR and reviewed by the council, then implemented, then reviewed independently. |
| **"Iterate on X"** / **"remediate X"** | `iterate` | Non-architectural fixes: bugs, drift, and refinements to existing behavior. It has the same council and review rigor. A *verify* module replaces the ADR: it reproduces the problem, finds the root cause, and has the council review the diagnosis. If the verify council finds the work is architectural, it stops and sends you to `dev-cycle`. |
| **"Patch this"** | `patch-cycle` | A small, reversible, non-architectural change that you can bound by naming the paths it may touch. See below. |
| **"Just fix it"** | `fix-directly` | A defect whose files, failing test, and unchanged contracts you can name before starting. See below. |
| **"New promptbook for X"** | `author-promptbook` | A custom multi-prompt plan that you co-author, with **no** required council or review. Use it for sequences that don't need the ceremony. |

**`patch-cycle`** runs five phases, one prompt each: verify, plan, implement, review, and summary.

- You declare a *blast radius* up front.
- The council checks that the blast radius is no wider than the work needs.
- At archive time, git reports the paths the run actually changed, and they are compared against the declaration.
- A change that reaches outside the declaration cannot be archived as delivered. It must be redone as an `iterate` or a `dev-cycle`.
- Work that needs an ADR is not a patch.

**`fix-directly`** has no book, no council, and no promptbook number. It runs these steps:

1. Write a failing test.
2. Make the smallest change that turns it green.
3. Run the test suite and the drift gates.
4. Make one commit.
5. Add one journal entry.

A security label sets a defect's priority, not its size. The sizing test decides which workflow applies.

**Driving a book:**

- **"run it"** starts an immutable run snapshot under `bionic/promptbooks/runs/`.
- **"advance"** or **"next prompt"** marks the current prompt done and moves on.
- **"abandon this run"** closes a run that will not finish.
- **"archive promptbook"** closes the book once its run is in one of two states:
  - completed, with every prompt terminal (done, skipped, or blocked)
  - deliberately abandoned

**"Promptbook status"** shows the current run using the progress renderer. The `run-promptbook` status procedure owns this read-only view.

- A terminal view or status answer writes nothing.
- A Markdown progress file is written only when you explicitly ask with `--markdown`.
- Advancing changes only the run snapshot and the active book pointer. It writes no per-prompt log entry.

Books and runs are structured `.yaml` documents validated against a JSON Schema. Cycle books must also pass the cycle-coverage invariants. You cannot edit the prompt list in the middle of a run. Instead, abandon the run and author a successor book that names its predecessor. Numbers are never reused.

#### Retired skill entries

If you are upgrading from an installation that used one of seven retired entries, use the routes below.

In Claude Code, Codex, and OpenCode, `CRUX_PLUGIN_ROOT` is derived from the selected Crux `SKILL.md`: it is the parent of that skill's `skills/` directory. `${CLAUDE_PLUGIN_ROOT}` is a Claude Code-only variable, not a portable plugin path. Do not substitute it in the routes below.

| Former entry | Current route |
|---|---|
| `task-planner` | `whiteboarding` for exploration. `author-promptbook` or a cycle for a tracked plan. The Python task-planner API is documented in `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`. |
| `author-runbook` | Tracked planning by default. Explicit generator instructions are in `${CRUX_PLUGIN_ROOT}/box/operator-services.md`. |
| `visualize-run-progress` | `run-promptbook` status. The renderer script is still available. |
| `trace-runtime-ops`, `semantic-bridge`, `agent-identity` | Python APIs documented in `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`. |
| `serve-llm` | HTTP service instructions in `${CRUX_PLUGIN_ROOT}/box/operator-services.md`. |

These names no longer select installed skills. Existing runs, runbooks, identities, and Python modules stay in place.

### Extracting code docs

- **"Extract code docs"** runs the plugin's `scripts/extract-code-docs.py` dispatcher according to `bionic/manifest.yml`. It regenerates `bionic/code/` from source.
- **"Verify code docs"** is the dry-run version. It reports drift without writing anything.

To choose which extractors run, edit `code.extractors:` in `bionic/manifest.yml`. The plugin ships extractors for Elixir and Python, plus a fallback that scrapes header comments. Extractors for more languages are added under the plugin's `scripts/extractors/`.

**Python extractor configuration.** A `python` key under `code.extractors:` takes exactly three fields:

- `extractor`
- `glob`
- `include_private` (optional, default on)

Any other key at that level makes the run refuse.

```yaml
code:
  extractors:
    python:
      extractor: python
      glob: "src/**/*.py"
      include_private: true
```

How the Python extractor runs:

- The dispatcher runs it under `uv run --no-config`, so `uv` ignores any `uv.toml` or `[tool.uv]` table.
- The script's PEP 723 block pins `griffelib==2.3.0`. Any other installed version exits 2.
- The extractor reads your sources statically. It never imports or runs your code, installs your dependencies, or executes documentation examples.

**Dispatcher outcomes:**

| Result | Meaning |
|---|---|
| Exit `0` | Clean, no drift. |
| Exit `1` with a `drift` payload | The on-disk docs are stale. Run without `--dry-run` to regenerate. |
| Exit `1` with a `validation_errors` payload | A content refusal, such as a parse failure, an oversized source, an unowned output root, or an extractor name the plugin doesn't ship. This is broken input, not drift, and regenerating won't fix it. This payload appears only under `--dry-run` (the `verify-code-docs` skill). In write mode, the same refusal exits `1` with a message on stderr, empty stdout, and no output bytes changed. |
| Exit `1`, message on stderr, empty stdout | A configuration error: a `--config` path that doesn't exist, a `--lang KEY` the manifest doesn't configure, or an unresolvable `.bionic.yml` or `.crux`. This applies with or without `--dry-run`. |
| Exit `2`, message on stderr, empty stdout | A capability failure: an interpreter older than 3.13, or a missing or mismatched `griffelib`. |
| `uv`'s own exit code, empty stdout | A `uv` resolution failure. |

### Summarizing the current architecture

**"Build the arch"**, **"summarize the current architecture"**, or **"regenerate the architecture"** runs `derive-arch`. It detects your stack and regenerates `bionic/arch/`, the derived map of the current state, from the project's own sources.

**Supported stacks.** Built-in packs cover Python, Ruby, Node.js, Elixir/Phoenix, and Swift. Swift support covers Swift packages and Xcode projects, including targets, product types, membership, and `@main` owners.

- An XcodeGen or Tuist manifest whose generated project file is missing is reported as missing input.
- A conditional build setting is reported as a `conditional-setting` residual.

**Where each concern comes from:**

| Concern | Source |
|---|---|
| Data model | Your ORM, schema, or type declarations: SQLAlchemy, SQLModel, and Django models; ActiveRecord's `schema.rb`; Prisma, TypeORM, and Sequelize; Ecto; Swift `struct`, `class`, `enum`, and `actor` declarations. |
| Interface surface | A committed OpenAPI document or the framework's routes. For Swift: `public`, `package`, and `open` declarations, every protocol, the package products, and the `@main` declarations. |
| Module graph | The import graph. For Swift, also the targets and dependencies declared in `Package.swift` manifests and Xcode project files. |

**Coverage reporting:**

- Each concern gets a `populated | stubbed` verdict, recorded in `_meta/coverage.json`.
- The same verdicts print as a coverage table, with one remediation line for each concern that is not `populated`.
- The tool reports what it found and does not grade anything.

**Missing parsers.** If a stack's declared parser is missing, the run exits 2 and writes nothing. The parser is `tree-sitter` plus the stack's grammar: Elixir needs `tree-sitter-elixir` and Swift needs `tree-sitter-swift`. Node.js and Ruby also declare grammars. Fix your environment, not the docs.

**Reading the arch.** Ask **"What's the current architecture?"**, read `bionic/arch/overview.md`, or ask the librarian. `derive-arch` builds the map, and the librarian answers questions from it.

**"Escalate the arch runtime"** runs `escalate-arch-runtime`, an optional fidelity upgrade for Python projects.

- You must invoke it explicitly. It never runs on its own, and `derive-arch` never points you to it as a fix.
- It recovers what the static extractor missed, such as the route table and the ORM schema.
- It does this by running your FastAPI, Flask, or Django app's import-time code in a confined subprocess.
- It requires the `CRUX_ARCH_ALLOW_RUNTIME=1` consent gate plus a permission prompt on each run.
- Results land in `bionic/inbox/` as advisory material, never in `bionic/arch/`.

New repos enroll arch by default through `init-docs`, so on a fresh tree you just build it. A tree created before arch became the default needs it enabled first: add `arch` to `concerns_enabled` in `bionic/manifest.yml`, then build. To keep it current, re-run `derive-arch` after any input changes, or let a routine **"audit docs"** regenerate it when it drifts. Never hand-edit `bionic/arch/`, because the next derive overwrites it.

### Asking questions

| Say this | Where Claude looks |
|---|---|
| **"What does X do?"** | `bionic/code/`, with page citations |
| **"Why did we choose Y?"** | `bionic/adrs/` and `bionic/briefs/` |
| **"What's the plan for Z?"** | Active promptbooks |
| **"What do we know about W?"** | Research |

Claude will offer to file good answers into `bionic/research/ideas/`.

### Checking health

**"Audit docs"** runs about 54 integrity checks across every enabled concern. It fixes safe drift automatically, such as counts, dates, and missing index rows. It shows you the broken cases to decide on.

Run it after every 10 or so writes, after a large refresh, and before any release.

**"Review the decisions"** runs `review-decisions`. These phrases also work:

- "run a decision review"
- "decision review"
- "do the decisions still serve the objectives"
- "review the ADR set against the objectives"
- "is the decision set still right"

The review reads the decision set and measures it against `bionic/objectives.md`. Each pass writes one dated report at `bionic/adrs/reviews/YYYY-MM-DD.md`.

The report has these sections:

- **Four finding sections: Propose, Amend, Repair, and Revoke.** At most five findings survive per pass, across all four sections combined.
- **Keep** lists decisions read this pass that still serve. It holds no findings and has no cap.
- **Coverage** names what the pass could not see. It holds no findings and has no cap.

Zero findings is a legitimate outcome. You maintain the reports by hand. Only `bionic/adrs/reviews/index.md` is regenerated.

The review proposes findings and changes nothing. Acting on a finding is a separate step, such as "propose ADR" or "accept ADR-NNNN", and the review never takes it.

Run the review weekly. `cleanup-campsite` reminds you when the newest report is older than `adr_review_due_days`, which is seven days by default.

---

## Tools & scripts

Everything Claude does is backed by Python scripts that ship inside the plugin. The docs tooling uses only the standard library. The multi-model substrate (described below) adds dependencies declared with PEP 723. **You almost never run these scripts yourself.** The skills call them for you, but knowing they exist helps when something looks off.

**Called by skills (you don't run these):**

| Script | Skill that calls it | What it does |
|---|---|---|
| `extract-code-docs.py` | `extract-code-docs` / `verify-code-docs` | Regenerates `bionic/code/` from source docstrings, using per-language extractors. |
| `web-to-markdown.py` | `ingest-research` / `refresh-research-sources` | Fetches a URL into audited markdown. |
| `transcribe-video.py` | `ingest-research` | Transcribes a video source to text. |
| `visualize-run-progress.py` | `run-promptbook` status | Reads run progress. Writes a byte-stable Markdown file only when you pass `--markdown`. |
| `write-journal.py` | `log-work` | Validates and writes either a journal entry (plus its index and log operation) or a single log-only operation. Reports partial writes so they can be replayed. |

**Validators (run on demand or in CI; they never publish):**

| Script | What it does |
|---|---|
| `validate-promptbook.py` | Validates a promptbook or run `.yaml` against its draft-2020-12 JSON Schema **and** the cycle-coverage invariants (`--kind promptbook\|run`). Every `dev-cycle`, `iterate`, and `patch-cycle` book must pass it. |
| `check-blast-radius.py` | Compares the changed paths git recorded for a `patch` run against the blast radius its book declared. `archive-promptbook` runs it before archiving. |

> **PyYAML requirement.** `validate-promptbook.py` and `visualize-run-progress.py` need a real YAML parser. The bundled minimal fallback is not accurate enough for validation verdicts or content hashes.
>
> - If PyYAML is missing and `uv` is installed, the scripts re-run themselves under `uv run --no-project --with pyyaml>=6.0`. They announce this on stderr, and the first use may fetch PyYAML from your configured index.
> - Otherwise they exit **2** with a message explaining the fix. Exit 2 always points to a problem in your environment, never in your docs.
> - In locked-down environments, set `CRUX_NO_UV_REEXEC=1` to turn off the automatic re-run, and install PyYAML yourself.
>
> **Dependency resolution for shipped scripts (PEP 723).** Shipped scripts that are documented as `uv run …` carry PEP 723 inline metadata.
>
> - **On first use, `uv` resolves those dependencies from your configured index. Resolution is not pinned by hash.** The results are cached afterwards. This is the same trust model as the PyYAML re-run above.
> - In hermetic or locked-down environments, install the declared dependencies yourself before first use, so the first run does not touch the network.
> - For stricter reproducibility, pin resolution with `uv run --exclude-newer <date>` or the `UV_EXCLUDE_NEWER` environment variable.
> - `uv` must be installed for these commands. Without it, the command fails at the shell with `command not found`. Install `uv` from https://docs.astral.sh/uv/.

**The multi-model substrate** lives under the plugin's `scripts/crux/`. It contains the LLM router (`call-llm`), the multi-model `council`, `srde`, the tracer, and the identity, knowledge, and task-planning modules behind the agent layer.

- These modules need API keys (see the next section).
- They run under `uv`, which picks the interpreter named in each script's PEP 723 header. crux supports Python 3.13 and 3.14.
- An HTTP service exposes the router to non-Python clients. See `${CRUX_PLUGIN_ROOT}/box/operator-services.md`.
- For the tracing, probe coordination, identity, and task-planning APIs, see `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`.

The `forge-skill` loop described below is a prose workflow and needs no API keys of its own.

**`forge-skill`** closes a capability gap in the middle of a task. It writes or revises a project-local skill under `.claude/skills/` on its own. Trigger phrases: *"forge a skill"*, *"author a skill for this"*, *"close this capability gap"*.

- It works autonomously and reports afterwards.
- It asks for your approval first only when the capability:
  - reaches outward or cannot be undone (external sends, spending, publishing)
  - would touch anything outside the repo, or any secrets
  - would change project structure or external surfaces (these take the brief or ADR path instead)
- Every forge action is recorded in the append-only **forge log at `.claude/skills/forge-log.md`**, a reviewable history of what was written, when, and why.

**`retrospective`** reflects on finished work. Trigger phrases: *"what should we learn from recent work"*, *"run a retrospective"*, *"retrospective over the last N books"*.

- It mines `bionic/log.md`, the work journal, and recent run snapshots for patterns.
- It condenses the findings into at most two skill proposals.
- Each proposal goes through the council before `forge-skill` builds it.
- It records outcomes with a `Retrospective:` journal entry, using the heading `## [YYYY-MM-DD HH:MM] learning | Retrospective: …`.
- `cleanup-campsite` tracks that entry and reminds you when enough archived books have piled up since the last retrospective.

The **`crux-env` CLI** keeps your API keys outside any repo. It has its own section below.

---

## Working with secrets and API keys

`~/.crux/` is your per-user secrets home, outside any repo. One file, `~/.crux/env`, holds the API keys for every crux project on your machine. The keys never leave your machine and never go into git.

You manage it with the `crux-env` CLI, which ships inside the installed plugin. In **Claude Code**, run it like this:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" <subcommand> …
```

`${CLAUDE_PLUGIN_ROOT}` is the plugin's installed root. Claude Code sets it inside sessions, and it is a Claude Code-only variable.

In other hosts, use the portable plugin root. `CRUX_PLUGIN_ROOT` is derived from the selected Crux `SKILL.md`: it is the parent of that skill's `skills/` directory. Run `python3 "${CRUX_PLUGIN_ROOT}/scripts/crux-env.py" <subcommand> …`.

The examples below shorten the invocation to `crux-env`. Define your own shell alias if you use it often. The commands below are the entire interface.

### One-time setup

```
crux-env init
```

This creates `~/.crux/` with safe file modes: `0600` on `env` and `0700` on `secrets/`. It is idempotent, so re-running it on an existing setup is safe.

### Adding a key

```
crux-env set OPENROUTER_API_KEY sk-or-xxxxxxxxxxxxxx
```

The value is stored in `~/.crux/env` with mode `0600`, so only you can read it. The key **name** is recorded in `~/.crux/log/crux-env.log`, but the **value is never logged**. The log is safe to share for debugging.

### Validating what's required

```
crux-env check --project myproject
```

This reads `~/.crux/required.yml` to find which environment variables the project needs, then checks that each one is set.

- It exits `0` if everything is set.
- It exits `1` with a JSON list of what's missing otherwise.

Run it before a workflow that depends on external services.

### Listing required keys (without revealing values)

```
crux-env list --project myproject
```

This prints something like:

```
myproject — required:
  ✓ CRUX_HOME
myproject — optional:
  ✓ CRUX_DEBUG
```

`✓` means set, and `✗` means missing. Values are never printed, only key names.

### Removing a key

```
crux-env rm OLD_API_KEY
```

To rotate a key, `rm` the old one and `set` the new one.

### Reference

| Command | What it does |
|---|---|
| `crux-env init` | Create `~/.crux/` with safe modes. Idempotent. |
| `crux-env set KEY VALUE` | Store a key. Logs the name, never the value. |
| `crux-env rm KEY` | Remove a key. The removal is logged. |
| `crux-env check --project <name>` | Verify that required environment variables are set. Exit 1 lists what's missing. |
| `crux-env list --project <name>` | Show key names and whether each is set. Never prints values. |

### What NEVER to do

- ❌ **Never commit `~/.crux/` to git.** It lives outside your repo by design. Don't symlink it in.
- ❌ **Never share `~/.crux/env`.** Mode `0600` only protects the file if nobody posts it to a chat channel.
- ❌ **Never paste a key into an issue, PR description, chat message, or screenshot.**
- ❌ **Never edit `~/.crux/log/crux-env.log`** to hide that you rotated a compromised key. The log is the audit trail.
- ✅ **Do rotate** any key you suspect has leaked. It costs one `set` command.

For the full specification of the secrets store and the CLI contract, see `bionic/AGENTS.md`.

---

## Per-project configuration: the repo-root `.bionic.yml` file

crux has two configuration surfaces. Don't confuse them:

- The repo-root **`.bionic.yml` FILE** holds per-project configuration and is committed.
- The user-home **`~/.crux/` DIRECTORY** (above) is your secrets store and is never committed.

A default `.bionic.yml` reads:

```yaml
config_version: "1"
docs_dir: bionic
artifact_prefix: ""
```

`.bionic.yml` replaces the legacy repo-root `.crux` file. crux still reads `.crux` for backward compatibility.

Every tree crux creates has a `.bionic.yml`. `init-docs` writes it when it sets up a tree. The pinned public `v3.23.2` recovery release writes it during a 4→5 upgrade. As a result, crux reads the layout from the file rather than guessing it.

Commit changes to `.bionic.yml` when you want a non-default setting:

- **`docs_dir`** moves the tree, for example to `documentation/` or `meta/docs/`. The path is relative to the repo root. Absolute paths and `..` are not allowed.
- **`artifact_prefix`** brands artifact ids so they are distinguishable across repos. With `artifact_prefix: "CRX"`, new ADRs get ids like `CRX-ADR-0012`, and new promptbooks carry the same prefix. Existing artifacts are never renamed.

To use a non-default `docs_dir` in a new repo, set up `.bionic.yml` **before** you say "init docs". `init-docs` writes the file when it is absent, and merges into (never overwrites) a file you already committed. In **Claude Code**, copy the shipped template like this:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/templates/bionic-yml.tmpl" .bionic.yml
```

In other hosts, use `${CRUX_PLUGIN_ROOT}/templates/bionic-yml.tmpl`.

Validation fails loudly. If `.bionic.yml` is malformed or invalid, every tool that reads it exits `1` with the validation error instead of quietly falling back to defaults. To check your file in **Claude Code**, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bionic-config.py"    # prints the resolved config as JSON
```

In other hosts, use `${CRUX_PLUGIN_ROOT}/scripts/bionic-config.py`.

- ❌ **Never put secrets, tokens, or API keys in `.bionic.yml`.** The file is committed to git, and unknown keys are silently ignored, so a misplaced secret wouldn't even produce an error. Secrets belong in `~/.crux/`.

The full contract is in `bionic/AGENTS.md`.

---

## Where to look first

In a project that uses crux, read in this order:

1. **`bionic/AGENTS.md`**: the operational schema. Skim the opening sections first. It is the single source of truth for what lives where and who edits what.
2. **`bionic/index.md`**: a catalog of everything, with one section per concern and counts.
3. **`bionic/adrs/`**: start at the lowest-numbered ADR and read forward in order. This explains why the project is the way it is.
4. **`bionic/journal/`**: the most recent month shows what is happening now.
5. **`bionic/research/sources.md`**: a registry of the external sources the project draws from.
6. **`bionic/promptbooks/index.md`**: the work currently in progress.

---

## What you should NEVER do

- ❌ **Edit anything in `bionic/code/`.** Every extract run deletes hand edits.
- ❌ **Edit an ADR body once it's `Accepted`.** Write a new ADR that supersedes it.
- ❌ **Reorder `bionic/log.md` or edit past entries.** It is append-only audit history.
- ❌ **Delete `bionic/research/raw/`.** Old captures are the audit chain.
- ❌ **Reuse an ADR or promptbook number.** Numbers only ever increase.
- ❌ **Edit rows in `bionic/research/sources.md` by hand.** Let `ingest-research` and `audit-docs` maintain it.

If something feels wrong, such as a contradiction, a stale page, or a missing source, say so. Don't fix it silently. `audit-docs` catches drift, and your sense that something looks off is what should trigger it.

---

## What you SHOULD do by hand

- Write `bionic/briefs/BRIEF-<slug>.md` files. These are your own pre-decision explorations. Claude tracks them but doesn't write them.
- Co-author the `## Goal`, `## Strategy`, and `## Prompts` sections of an active promptbook.
- Edit the repo-root `AGENTS.md` to add project-specific notes for Claude. Don't remove the `See bionic/AGENTS.md` line.

---

## Day-one quick start

You're in a fresh repo with `bionic/` just initialized. To start using it:

1. **Record today's intent as an ADR.** Say *"Propose an ADR explaining why we're using crux for this project."* Review it, then say *"Accept ADR-0001."*
2. **Capture your planning material.** Drop your existing design notes, specs, and chat exports into `bionic/inbox/` and say *"Process inbox."* Claude classifies each item and sends the research items through `ingest-research`.
3. **Plan the first chunk of work.** Say *"New promptbook for <thing>."* Co-author the prompt list, then say *"Run it."*
4. **Journal at the end of the day.** Say *"Log today's work — `<one line summary>`."*
5. **Audit after the first ten writes.** Say *"Audit docs."* and confirm there is no drift.

---

## When things go wrong

| Symptom | Try this |
|---|---|
| "Where did Claude put X?" | Look at `bionic/index.md` and `bionic/<concern>/index.md`. |
| `bionic/code/` has stale content | Say *"extract code docs"*. It regenerates everything. |
| An ADR was accepted but it's wrong | Don't edit it. Write a new ADR that supersedes it. |
| A research synthesis page contradicts itself | Say *"refresh synthesis"*. Claude walks you through reconciling it. |
| You lost track of a promptbook's progress | `bionic/promptbooks/index.md` shows the current run and percent complete. |
| The whole `bionic/` tree feels broken | Say *"audit docs"* to run the integrity checks across all concerns. |

---

## Plugin and schema

crux maintains your documentation tree at `schema_version 5`, the `bionic/` layout. The plugin runs from its marketplace-installed copy. In Claude Code, that copy's root is `${CLAUDE_PLUGIN_ROOT}`. Portably, it is `${CRUX_PLUGIN_ROOT}`, the parent of the selected Crux `SKILL.md`'s `skills/` directory.

**Install or upgrade:**

- In Claude Code, run `/plugin marketplace add bionic-coding/crux` and then `/plugin install crux@crux`.
- In Codex, run `codex plugin marketplace add bionic-coding/crux` and then `codex plugin add crux@crux`.
- Codex users can install the ten Crux role agents personally with the `install-codex-agents` skill.

### Upgrading from a release before 3.19.0

Say *"audit docs --migrate"*, even if `schema_version` is already `"5"`. The migration converts tracked `CLAUDE.md` files to `AGENTS.md`.

- When both files exist at the same scope, it keeps unique blocks and removes only exact duplicates under the same heading path.
- It reports untracked and private suppressors without editing them.

If a heading conflicts, or a block cannot keep its heading ancestry, the migration keeps both source files and writes `.instruction-migration-preview.md`. To resolve it:

1. Write a JSON resolution file that reconciles each named block.
2. Copy the `source_hashes` from `.instruction-migration-receipt.json` into it.
3. Say *"audit docs --migrate using the resolution file at `<path>`"*.

### Recover older trees and Markdown promptbooks

The current plugin works on schema 5 trees and runs YAML promptbooks only.

#### Get and verify the recovery release

For a schema-2, schema-3, or schema-4 tree, work on a copy or backup using the public `v3.23.2` release. Verify its annotated tag and commit before using its schema upgrade steps:

```bash
recovery_dir="$(mktemp -d)"
git clone --branch v3.23.2 --single-branch https://github.com/bionic-coding/crux.git "$recovery_dir/crux"
git -C "$recovery_dir/crux" rev-parse refs/tags/v3.23.2
git -C "$recovery_dir/crux" rev-parse HEAD
```

The two results must match:

- tag: `c1298c4a9229ed41ae7017c25321d27e5b3f6e4d`
- commit: `08ee30ec2f1d1b4b0ce970f2e1582bb4f83cd20d`

#### Upgrade the schema

Read that release's `crux/skills/audit-docs/SKILL.md` and follow its 2→3→4→5 upgrade steps in order.

- If a valid `.migrating` marker exists, follow its recorded resume or abandon procedure.
- An invalid marker, or two ambiguous trees, needs investigation before you continue.

The current plugin does not run these upgrade steps. Its `audit-docs --migrate` only handles instruction files on a schema-5 tree.

#### Finish or strand Markdown runs

The tagged release can finish a Markdown run if its remaining prompts can truthfully be completed. If so:

1. Archive the run using the tagged release.
2. Convert the book, then the run, with that release's `migrate-promptbooks` skill. It keeps the Markdown originals.
3. Validate the YAML files and their content-hash binding before returning to the current plugin.

The tagged release cannot deliberately abandon a Markdown run. If a run cannot finish:

- Leave its bytes unchanged as stranded, readable history.
- Continue separate work in new YAML books.
- Do not mark the run complete, skip unfinished prompts so you can migrate it, or convert it in place.

#### Isolate the project copy

Use a separate project copy for recovery. Before starting any host, inspect that copy's project-level Crux registrations and disable only the current version there:

- **Claude Code:** project settings and `.claude/skills/`
- **Codex:** `.agents/plugins/marketplace.json`, `.agents/skills/`, and `.codex/config.toml`
- **OpenCode:** project `opencode.json`, `.opencode/skills/`, and `.opencode/skill/`

Leave unrelated entries and the original project unchanged. OpenCode merges project `skills` arrays with XDG settings, so an isolated XDG directory alone does not remove a current project skill path. If you cannot verify that only the tagged Crux skills are active, stop before changing the copy.

Use only the tagged plugin during recovery.

#### Claude Code

1. Disable the currently installed Crux plugin in its installation scope with `claude plugin disable crux@crux`.
2. Start a separate session with `claude --plugin-dir "$recovery_dir/crux/crux"`. The `--plugin-dir` flag adds that source for this session only.
3. Verify that the current plugin is disabled.
4. After recovery, run `claude plugin enable crux@crux` and restart.

#### Codex

Use an isolated Codex home so your normal plugin installation is absent. The tagged checkout contains a local marketplace named `crux` whose source is `./crux`. Codex's local-marketplace command accepts a directory path:

```bash
mkdir -p "$recovery_dir/codex-home"
CODEX_HOME="$recovery_dir/codex-home" codex plugin marketplace add "$recovery_dir/crux"
CODEX_HOME="$recovery_dir/codex-home" codex plugin add crux@crux
```

1. Start the recovery session with the same `CODEX_HOME`, in a project copy with no other project-scoped Crux plugin.
2. Verify that the tagged skill is available before changing anything.
3. When done, end the session and return to your normal Codex home to resume the current plugin.

[Codex's local-marketplace instructions](https://developers.openai.com/plugins/build/plugins) explain the path form. These commands have been checked against local CLI help but not exercised as a fresh-session recovery.

#### OpenCode

Use an isolated XDG config for a separate recovery session.

1. Put this file at `$recovery_dir/opencode-config/opencode/opencode.json`, replacing `TAGGED_CHECKOUT` with the absolute path of `$recovery_dir/crux`:

   ```json
   {"skills": ["TAGGED_CHECKOUT/crux/skills"]}
   ```

2. Create the directories and start OpenCode with isolated paths:

   ```bash
   mkdir -p "$recovery_dir/opencode-config/opencode" "$recovery_dir/opencode-data" "$recovery_dir/opencode-cache"
   XDG_CONFIG_HOME="$recovery_dir/opencode-config" XDG_DATA_HOME="$recovery_dir/opencode-data" XDG_CACHE_HOME="$recovery_dir/opencode-cache" opencode
   ```

3. Verify that only the tagged Crux skills load.
4. After recovery, quit and restore your normal XDG settings.

This setup follows crux's OpenCode `skills` array contract.

These recovery procedures have not been verified end-to-end in fresh Claude Code, Codex, or OpenCode sessions.
