<!-- generated-from: USER_GUIDE.md@sha256:39110b80b152fe6478108427076f23ff9d9a6f776b07f5685ea365952df8d424; model: claude-opus-5.5; date: 2026-09-26 -->
# crux User Guide

crux keeps your project's documentation in a `bionic/` folder. The tree holds seven concerns plus two default-on surfaces, `arch` and `observations`. **You do not write these docs by hand.** You curate, decide, and discuss, and Claude does the bookkeeping.

This guide is for humans. An LLM agent working in your project should read `bionic/AGENTS.md` instead. That file is the operational schema, and crux writes it into your project when you initialize the tree.

---

## At a glance

crux turns a `./bionic/` folder into a maintained knowledge base that you and Claude share. It has four moving parts:

1. **The `bionic/` tree: seven concerns plus two default-on surfaces.** The concerns are code docs, the research wiki, ADRs, briefs, the work journal, promptbooks, and invariants. The two surfaces are the derived `arch` map and the `observations` records. You curate and decide, and Claude does the bookkeeping. See [The seven concerns](#the-seven-concerns).
2. **60 skills, triggered by natural language instead of slash commands.** Examples are "propose an ADR", "process inbox", "audit docs", "start a cycle", and "forge a skill". Claude routes each phrase to a skill through the skill's description. See [What to say to Claude](#what-to-say-to-claude). The README has the full catalog.
3. **10 agents, a role layer over the skills.** A `commander` delegates work to `architect`, `dev-lead`, `developer`, `reviewer`, `historian`, `librarian`, `brainstormer`, and `wayfinder`. An overnight `night-gardener` runs on a schedule. Each agent has a tool allowlist, so the separation of duties is *structural*. See [The agent layer](#the-agent-layer).
4. **Three workflows for change.** All three are tracked promptbooks:
   - `dev-cycle` handles net-new or architectural work with an ADR, a council, and a review.
   - `iterate` handles non-architectural fixes with verification, a council, and a review, but no ADR.
   - `patch-cycle` handles a small reversible fix in five phases, one prompt each, with a declared blast radius.

   For a defect whose fix you can name before starting, use `fix-directly`: no promptbook, and a failing test first. See [Planning multi-step work](#planning-multi-step-work--promptbooks--cycles).

Underneath, the skills call Python **scripts** that ship with the plugin: extractors, validators, and the LLM router. The `crux-env` **CLI** manages secrets. See [Tools & scripts](#tools--scripts).

**If you read nothing else:**
- Drop anything into `bionic/inbox/` and say *"process inbox"*.
- Ask *"what does X do?"* or *"why did we choose Y?"*.
- Say *"start a cycle for X"* or *"iterate on X"* to ship a change with the receipts attached.

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

_This guide uses the default `bionic/` layout. If your project sets a custom `docs_dir`, that directory replaces `bionic/` everywhere below. See [Per-project configuration](#per-project-configuration-the-repo-root-bionicyml-file)._

| Directory | What lives there | Who edits |
|---|---|---|
| `bionic/code/` | Docs extracted automatically from source code (docstrings, @doc, JSDoc) | **Regenerated. Never edit by hand.** Every extract run deletes hand edits. |
| `bionic/research/` | Articles, papers, web pages, meeting notes, chat exports | You drop sources in the shared `bionic/inbox/`. `process-inbox` routes them to `ingest-research`, which captures each source into the immutable `bionic/research/raw/` and runs the ingest pipeline. |
| `bionic/adrs/` | Architecture Decision Records: the "why" behind every load-bearing decision | You decide and Claude writes the ADR. **Once an ADR is `Accepted`, its body is frozen.** |
| `bionic/briefs/` | Exploration documents written before a decision (`BRIEF-<slug>.md`) | You write them and Claude tracks them. |
| `bionic/journal/` | A day-by-day record of work performed (`YYYY-MM.md`) | Claude appends entries when you ask. |
| `bionic/promptbooks/` | Plans of prompts you want to execute, plus immutable run snapshots | Co-authored. The plan is mutable and the run history is frozen. |
| `bionic/invariants/` | Pinned, executable statements of *what must be true*. Each pin has a ledger page. The executable checks live in `invariants/checks/` and are reconciled through `invariants/reconciliation.yml`. | **The machine proposes and you ratify.** `recover-invariants` mines candidates and files them as `observed`. You ratify, reject, or retire them with `transition-invariant`. Recovery never ratifies its own candidates. |
| `bionic/observations/` (default-on) | Records of what the code *already does* (`OBS-NNNN-<slug>.md`). Each record cites a `path:line-range` as evidence and never quotes code. | **You write and you ratify.** `propose-observation` scaffolds a record as `observed`. `transition-observation` is the only way to move a single record out of `observed`, to `ratified`, `rejected`, `retired`, or `decided`. The survey sign-off is the only batch route. No scan writes an observation file in any state. |
| `bionic/arch/` (default-on) | The derived architecture spine, a map of the current state: data model, interface surface, module graph, decision index, and a synthesized overview | **Regenerated. Never edit by hand.** `derive-arch` builds it on demand. New trees enroll it by default. Existing trees opt in by adding `arch` to `concerns_enabled`. |

### Invariants

Invariants are the seventh concern. The other concerns record knowledge, and invariants pin *what must stay true* as executable checks that survive regeneration. A new project starts with an empty invariants concern. An empty concern is clean, not broken. Run `recover-invariants` when you are ready to populate it.

### The arch surface

**`bionic/arch/`** is the first default-on surface beyond the seven concerns. It holds the derived architecture and is the main place to answer *"how is this project shaped right now?"* It contains:
- a deterministic spine: data model, interface surface, module graph, and decision index
- a synthesized overview

All of it is regenerated wholesale from your project's own sources. ADRs are the secondary path because they record the *why*. The librarian and historian fill any gaps.

- **New projects** enroll arch by default through `init-docs`. Say **"build the arch"** to derive it.
- **Existing trees** that predate the default must add `arch` to `concerns_enabled` before deriving it.

Keep arch current by re-running `derive-arch`, or let `audit-docs` regenerate it automatically when it drifts. Like `code/`, it is never edited by hand.

### The observations surface

**`bionic/observations/`** is the second default-on surface. It records what the code already does. An observation describes behavior and does not decide anything.
- An ADR records a choice somebody made.
- An observation records a fact nobody wrote down. It cites a `path:line-range` in the real source as evidence.

A project with no ADRs uses observations as its starting layer. A project with many ADRs uses observations for everything the ADRs never covered.

To create an observation, say **"propose observation"**. The new record lands as `observed`. Only you can move it past that state:
- `transition-observation` is the only route for a single record.
- `survey-signoff` is the only batch route.

No scan ever writes or ratifies an observation. Ratified observations feed the same summaries and doctrine projections that ADRs feed, so an observation gains real authority once you affirm it.

#### Ratifying observations in a batch

The batch route has two steps and covers as many candidates as you put on one sheet. You invoke both steps yourself, and neither runs unattended.

1. **Build the sheet.** Say **"scaffold a survey sheet"**. `survey-sheet` builds one sheet over the candidates in `observed` and seeds each row with a claim and a proposed domain. You complete each row with:
   - a verdict: `ratify`, `reject`, or `defer`
   - a one-line rationale
   - a domain, if the proposed one is wrong
2. **Sign it off.** Say **"sign off the survey"**. `survey-signoff` renders every claim and its verdict for you to read. When you confirm, it publishes the batch under one digest-bound receipt, so one signature covers every ratification on the sheet.

---

## The agent layer

crux ships ten **agents** that operate the skills. Claude Code loads the agents directly from the plugin. Codex and OpenCode use generated native forms of the same agents.

- **commander** runs a promptbook or cycle and delegates every step. It never edits anything itself.
- **brainstormer** explores a design with you using the `whiteboarding` skill, then hands the session to the historian to file.
- **architect** owns ADRs and decisions. It drafts ADRs, runs the council, and accepts decisions.
- **dev-lead** leads implementation and fans independent work out to **developer** agents.
- **reviewer** reviews code independently. It is read-only, so it reports findings and cannot quietly fix and hide them.
- **historian** owns every write under `bionic/`.
- **librarian** answers questions from `bionic/`. It is read-only.
- **wayfinder** handles large, uncertain, or external material before other agents spend context on it.
  - It reads the material in an isolated context and judges whether it fits your purpose.
  - It returns a verdict and a condensed digest, so the main agent spends its own context only on material that proved relevant.
  - It is read-only. It is the only agent with `WebFetch` and `WebSearch`, and an egress guardrail fences it.
- **night-gardener** runs overnight as a scheduled routine.
  - **What it does:** it reviews what changed since your last move and leaves a morning note under `bionic/garden/`. The note can cover ideas, codebase improvements, missing tests, CI, or guards, research, and news. Its news pass reads a curated source list through the `read-news` skill.
  - **When it runs:** it is turn-based, so it skips a run when the only changes are its own work.
  - **Limits:** it acts as a full co-CTO but works behind existing gates and never pushes.
  - **Dismissing advice:** dismiss or snooze its advice in `bionic/garden/tending.md`. No acknowledgment is needed.

Each agent definition declares its tool boundaries and required skills. Host permissions can override an agent's default sandbox, but the agent's role prompt stays binding either way. The agents build in the craft disciplines they need, including testing, verification, debugging, and two-stage review.

| Agent | Reach for it when you want… | Bounded so it cannot… |
|---|---|---|
| `commander` | a whole cycle or promptbook driven end-to-end, with each step delegated | edit code or docs itself |
| `brainstormer` | to explore a fuzzy idea before committing to it (uses `whiteboarding`) | write files or touch code |
| `architect` | a decision recorded and reviewed by the council (`propose-adr` → `council` → accept) | implement code |
| `dev-lead` | implementation coordinated across parallel units | merge or push (both need a human) |
| `developer` | one scoped unit built test-first | delegate again, or write docs or ADRs |
| `reviewer` | an independent check of a diff | edit files (it reports and never fixes and hides) |
| `historian` | anything written under `bionic/` (intake, journaling, indexes) | edit source code |
| `librarian` | a question answered from `bionic/` (`query-docs`) | write anything |
| `night-gardener` | an overnight pass that records ideas, gaps, research, and news | push, merge, or send material externally |
| `wayfinder` | a large, uncertain, or external source checked for fit and condensed before you read it | write, execute, delegate, or send local content outbound |

### Installing the agents in Codex

After installing the plugin in Codex, say **"install the Crux agents in Codex"**. This runs the `install-codex-agents` skill.
- **Default location:** the installer writes the ten namespaced `crux_*` roles to `~/.codex/agents/`.
- **Role settings:** each role pins its catalog model and reasoning effort, and binds its declared skills to the installed plugin.
- **Per-project install:** pass `--repo-root` to install into one project's `.codex/agents/` directory instead.

To refresh the agents:
- An unchanged refresh does nothing.
- If managed files have changed or gone stale, review them and then re-run with `--force`.
- Skill bindings use absolute paths, so moving the plugin shows up as drift.

To check the installed agents, run `--check --project-context <repo>`. The report covers two things:
- managed drift
- project agents that shadow your personal roles

The report keeps the expected canonical state separate from the managed TOML state it parses from disk. Its runtime result stays `unverified` until a fresh Codex session confirms, for your Codex version, that the host discovers the agents and applies their settings and skills, and that representative workflows run.

### How you use the agents

You rarely need to name an agent, because a cycle and the `commander` dispatch them for you. You can still ask for one explicitly:
- *"have the architect propose an ADR for X"*
- *"send this design to the council"*
- *"have the reviewer check the diff"*
- *"ask the librarian what we decided about Y"*

---

## What to say to Claude

These phrases trigger the right skill. Use them inside ordinary sentences, and Claude works out the rest.

### Recording decisions

| Say | What happens |
|---|---|
| **"Propose an ADR for X"** | Claude writes a new `ADR-NNNN-<slug>.md` in `bionic/adrs/` with status `Proposed`. You review the alternatives. |
| **"Accept ADR-NNNN"** | The status changes to `Accepted`, and the body is frozen. |
| **"Supersede ADR-NNNN with ADR-MMMM"** | Both ends of the supersession link update together, as one atomic change. |
| **"Deprecate ADR-NNNN"** | The decision is retracted without a replacement. |
| **"Sign off backfill batch <id>"** | `backfill-signoff` records your owner sign-off for one backfill batch. See below. |

When you sign off a backfill batch, `backfill-signoff` first renders the rule and anchor of every listed receipt verbatim for you to read. Nothing is written before that. The script is the only way to write to the backfill surfaces:
- the signed-date flip
- the admission ledger
- the log entry
- the journal hook
- the completion marker

Never edit those surfaces by hand.

ADRs are append-only history. You cannot edit an accepted ADR. Instead, you write a new ADR that supersedes it.

### Capturing anything with the shared inbox

There is **one** place to drop raw input: `bionic/inbox/`. Drop any kind of item there, such as a research file, a pasted URL, a half-formed decision note, or a stray idea. Then say **"process inbox"**. The `process-inbox` skill:

1. classifies each item
2. shows you a confirmation table listing each item, its proposed skill, and a confidence level
3. dispatches each item to the skill that owns its concern once you reply `ok`

| Item type | Routed to |
|---|---|
| Research source (a file, a URL, or a `urls.md` manifest) | `ingest-research` |
| Architectural decision | `propose-adr` |
| Exploration before a decision | `propose-brief` |
| Work-log note | `log-work` |

Claude classifies first and asks you to confirm. Only items Claude is confident about are dispatched when you reply `ok`. Uncertain items are held back so you can reply `override N=<target>` or `defer N`. `process-inbox` only ever creates ADRs as `Proposed` and never accepts one automatically.

#### Research

Research always goes through `ingest-research`. The pipeline:
- moves each source into a dated, immutable capture in `bionic/research/raw/`
- writes an audited source page for it
- updates the relevant synthesis pages

You can feed research in three ways:
- **Drop a file** in `bionic/inbox/` and say "process inbox".
- **Paste a URL** into a file under `bionic/inbox/`, or hand it to Claude, and say "ingest this". Claude fetches the page with the bundled `web-to-markdown.py`, and it goes through the same pipeline.
- **Bulk import** by dropping a `urls.md` file in `bionic/inbox/` with one URL per line.
  - Add `(static)` after a URL to exclude it from refresh checks.
  - If a run processes only part of the file, `urls.md` stays in place and the next run retries the rest.

When upstream sources may have changed:

| Say | What happens |
|---|---|
| **"Refresh sources"** | Claude re-fetches non-static URLs, files any updates as new dated captures, and flags the affected synthesis pages. |
| **"Refresh synthesis"** | Claude walks you through the accumulated markers, such as contradictions and source updates, page by page. |

### Journaling work

- **"Log work"** or **"journal this"** adds a dated, categorized entry to `bionic/journal/YYYY-MM.md`.
- Claude may also log silently after meaningful operations, such as an accepted ADR, a completed promptbook, or a large refactor.

The categories are `decision | implementation | bug | learning | blocker | refactor | meeting | review | misc | release`.

### Planning multi-step work — promptbooks & cycles

Choose a workflow by the kind of change:

| Say | Skill | Use it for |
|---|---|---|
| **"Start a cycle for X"** | `dev-cycle` | **Net-new or architectural** work. |
| **"Iterate on X"** / **"remediate X"** | `iterate` | **Non-architectural fixes**: bugs, drift, and refinements to existing behavior. |
| **"Patch this"** | `patch-cycle` | A **small reversible** non-architectural change you can bound by naming the paths it may touch. |
| **"Just fix it"** | `fix-directly` | A defect whose files, failing test, and unchanged contracts you can name before starting. |
| **"New promptbook for X"** | `author-promptbook` | A custom multi-prompt plan for a sequence that does not need the ceremony. |

- **`dev-cycle`** assembles a tracked promptbook of ADR, development, and review modules. It records the decision as an ADR, has the council review it, implements it, and then reviews the result independently. A cycle has at least 13 prompts.
- **`iterate`** applies the same council and review rigor as `dev-cycle`. It uses a *verify* module instead of an ADR, because there is no decision to record. The verify module reproduces the problem, finds the root cause, and has the council review the diagnosis. If the council finds that the work is architectural after all, `iterate` stops and routes you to `dev-cycle`.
- **`patch-cycle`** runs five phases, one prompt each: verify, plan, implement, review, and summary.
  - **Declared blast radius:** you declare a *blast radius* up front. The council checks that it is no wider than the work needs.
  - **Archive check:** at archival, crux uses git to compare the paths the run actually changed against the declaration.
  - **Out-of-bounds changes:** a change that reaches outside the declaration cannot be archived as delivered. It has to be redone as an `iterate` or a `dev-cycle`.
  - **Not for ADR-level work:** work that needs an ADR is not a patch.
- **`fix-directly`** uses no promptbook, no council, and no promptbook number. It works in this order:
  1. write a failing test first
  2. make the smallest change that turns the test green
  3. run the test suite and the drift gates
  4. make one commit
  5. write one journal entry

  A security label sets a defect's priority, not its size. The sizing test decides which workflow applies.
- **`author-promptbook`** creates a plan you co-author, with **no** enforced council or review.

#### Running a promptbook

| Say | What happens |
|---|---|
| **"run it"** | Starts an immutable run snapshot under `bionic/promptbooks/runs/`. |
| **"advance"** / **"next prompt"** | Marks the current prompt done and moves to the next one. |
| **"abandon this run"** | Closes a run that will not finish. |
| **"archive promptbook"** | Closes the promptbook. See the conditions below. |

You can archive a promptbook in two cases:
- Its run completed with every prompt in a final state: done, skipped, or blocked.
- Its run was deliberately abandoned.

Promptbooks and runs are structured `.yaml` documents validated against a JSON Schema. The cycle kinds must also pass the cycle-coverage invariants.

You cannot edit the prompt list during a run. To change it, abandon the run and write a successor promptbook that names its predecessor. Numbers are never reused.

### Extracting code docs

| Say | What happens |
|---|---|
| **"Extract code docs"** | Runs the bundled `extract-code-docs.py` dispatcher according to `bionic/manifest.yml` and regenerates `bionic/code/` from source. |
| **"Verify code docs"** | A dry run that reports drift without writing anything. |

To choose which extractors run, edit `code.extractors:` in `bionic/manifest.yml`. The plugin ships extractors for Elixir and Python, plus a fallback that scrapes header comments.

#### Python extractor

A `python` key under `code.extractors:` takes exactly three fields:
- `extractor`
- `glob`
- `include_private`, which is optional and on by default

Any other key at that level makes the run refuse to start.

```yaml
code:
  extractors:
    python:
      extractor: python
      glob: "src/**/*.py"
      include_private: true
```

The dispatcher runs the Python extractor under `uv run --no-config`, so `uv` ignores any `uv.toml` file or `[tool.uv]` table. The script's PEP 723 block pins `griffelib==2.3.0`, and any other installed version exits 2. The extractor reads your sources statically. It never imports or runs your code, installs your code's dependencies, or executes documentation examples.

#### Dispatcher outcomes

The dispatcher reports one of five outcomes:

| Outcome | Exit | Output | Meaning and fix |
|---|---|---|---|
| Clean | `0` | — | No drift. |
| Drift | `1` | a `drift` payload | The docs on disk are stale. Run without `--dry-run` to regenerate them. |
| Content refusal | `1` | see below | The input is broken, and regenerating does not fix it. |
| Configuration error | `1` | message on stderr, empty stdout | Fix the configuration. This outcome is the same with or without `--dry-run`. |
| Capability failure | `2` | message on stderr, empty stdout | Fix the environment. |

- **Content refusals** cover a parse failure, an oversized source, an output root that crux does not own, or an extractor name the plugin does not ship.
  - Under `--dry-run`, which is what the `verify-code-docs` skill uses, a refusal returns a `validation_errors` payload.
  - In write mode, a refusal writes a message to stderr, leaves stdout empty, and changes no output byte.
- **Configuration errors** cover a `--config` path that does not exist, a `--lang KEY` that the manifest does not configure, or a `.bionic.yml` or `.crux` file that cannot be resolved.
- **Capability failures** cover an interpreter older than 3.13, or a missing or mismatched `griffelib`.
- **`uv` resolution failures** exit with `uv`'s own exit code and also leave stdout empty.

### Summarizing the current architecture

#### Building the arch

Say **"Build the arch"**, **"summarize the current architecture"**, or **"regenerate the architecture"**. `derive-arch` detects your stack and regenerates `bionic/arch/` wholesale from your project's own sources.

Built-in packs cover these stacks:
- Python
- Ruby
- Node.js
- Elixir/Phoenix
- Swift, including Swift packages and Xcode projects with their targets, product types, membership, and `@main` owners

Each pack derives three things:
- **Data model:** from your ORM, schema, or type declarations. Supported sources include:
  - SQLAlchemy, SQLModel, and Django models
  - ActiveRecord's `schema.rb`
  - Prisma, TypeORM, and Sequelize
  - Ecto
  - Swift `struct`, `class`, `enum`, and `actor` declarations
- **Interface surface:** from a committed OpenAPI document or the framework's routes. The Swift pack uses `public`, `package`, and `open` declarations, every protocol, the package products, and the `@main` declarations.
- **Module graph:** from the import graph. The Swift pack adds the targets and dependencies declared in `Package.swift` manifests and Xcode project files.

Some inputs get special treatment in Swift projects:
- An XcodeGen or Tuist manifest whose generated project file is missing renders as missing input.
- A conditional build setting renders as a `conditional-setting` residual.

#### Coverage and failures

Each concern gets a `populated | stubbed` verdict, recorded in `_meta/coverage.json`. The same verdicts print as a coverage table, with one remediation line for each concern that is not `populated`. The tool reports what it found and does not grade anything.

Some stacks need a parser: `tree-sitter` plus a grammar for the language. Elixir needs `tree-sitter-elixir`, Swift needs `tree-sitter-swift`, and Node.js and Ruby also declare grammars. If the parser a stack declares is missing, `derive-arch` exits 2 and writes nothing. The fix is in your environment, not your docs.

#### Reading and extending the arch

- **"What's the current architecture?"**: read `bionic/arch/overview.md` or ask the librarian. `derive-arch` builds the arch, and the librarian answers questions from it.
- **"Escalate the arch runtime"** runs `escalate-arch-runtime`. It works only for Python projects, and only when you invoke it explicitly. It never fires automatically.
  - **What it is:** an optional fidelity upgrade. `derive-arch` never points you to it as a fix.
  - **What it recovers:** details the static extractor missed, such as the route table and the ORM schema.
  - **How it works:** it runs your FastAPI, Flask, or Django app's import-time code in a confined subprocess.
  - **Consent:** it requires both the `CRUX_ARCH_ALLOW_RUNTIME=1` consent gate and a permission prompt on each run.
  - **Results:** they land in `bionic/inbox/` as advisory material and never go into `bionic/arch/`.

#### Enabling and maintaining arch

New projects enroll arch by default through `init-docs`, so on a fresh tree you can build it straight away. On an existing tree that predates the default, first add `arch` to `concerns_enabled` in `bionic/manifest.yml`, then build it.

To keep the arch current, re-run `derive-arch` after any of its inputs changes, or let a routine **"audit docs"** regenerate a drifted spine automatically. Never edit `bionic/arch/` by hand, because the next derive overwrites it.

### Asking questions

| Say | What Claude searches |
|---|---|
| **"What does X do?"** | `bionic/code/`, with page citations |
| **"Why did we choose Y?"** | `bionic/adrs/` and `bionic/briefs/` |
| **"What's the plan for Z?"** | active promptbooks |
| **"What do we know about W?"** | the research wiki |

Claude will offer to file good answers back into `bionic/research/ideas/`.

### Checking health

#### Auditing the docs

**"Audit docs"** runs about 54 integrity checks across every enabled concern. It fixes safe drift automatically, such as counts, dates, and missing index rows. It brings broken cases to you for a decision.

Run an audit:
- after roughly every 10 writes
- after a large refresh
- before any release

#### Reviewing decisions

**"Review the decisions"** runs `review-decisions`. These phrases also trigger it:
- "run a decision review" or "decision review"
- "do the decisions still serve the objectives"
- "review the ADR set against the objectives"
- "is the decision set still right"

The review reads the decision set, measures it against `bionic/objectives.md`, and writes one dated report per pass at `bionic/adrs/reviews/YYYY-MM-DD.md`. The report has six sections:
- **Findings** go in four sections: **Propose**, **Amend**, **Repair**, and **Revoke**. At most five findings survive per pass, across all four sections combined.
- **Keep** lists decisions read in this pass that still serve the objectives. It holds no findings and has no cap.
- **Coverage** names what the pass could not see. It also holds no findings and has no cap.

Zero findings is a legitimate outcome. The report is kept by hand, and only `bionic/adrs/reviews/index.md` is regenerated.

The review only proposes findings and never changes a decision's status. Acting on a finding is a separate step, such as "propose ADR" or "accept ADR-NNNN", and the review never takes that step.

Run the review weekly. `cleanup-campsite` reminds you when the newest report is older than `adr_review_due_days`, which defaults to seven.

---

## Tools & scripts

Everything Claude does is backed by Python scripts that ship with the plugin under `${CLAUDE_PLUGIN_ROOT}/scripts/`. The docs tooling uses only the standard library. The multi-model substrate adds dependencies declared through PEP 723. **You almost never run these scripts directly** because the skills call them for you. Knowing they exist helps when something looks wrong.

**Scripts the skills call for you:**

| Script | Called by | What it does |
|---|---|---|
| `extract-code-docs.py` | `extract-code-docs` / `verify-code-docs` | Regenerates `bionic/code/` from source docstrings using a plugin for each language. |
| `web-to-markdown.py` | `ingest-research` / `refresh-research-sources` | Fetches a URL into audited markdown. |
| `transcribe-video.py` | `ingest-research` | Transcribes a video source to text. |
| `migrate-promptbooks.py` | `migrate-promptbooks` | Converts legacy `.md` promptbooks and runs to structured `.yaml`. |
| `visualize-run-progress.py` | `visualize-run-progress` | Renders a run snapshot as a terminal progress bar and a byte-stable markdown artifact. |

**Validators, run on demand or in CI. They never publish anything.**

| Script | What it does |
|---|---|
| `validate-promptbook.py` | Validates a promptbook or run `.yaml` (`--kind promptbook\|run`) against its draft-2020-12 JSON Schema **and** the cycle-coverage invariants. Books for `dev-cycle`, `iterate`, and `patch-cycle` must pass this gate. |
| `check-blast-radius.py` | Compares the changed paths git recorded for a `patch` run against the blast radius declared in its book. `archive-promptbook` runs it as a precondition. |

### PyYAML requirement

`validate-promptbook.py`, `migrate-promptbooks.py`, and `visualize-run-progress.py` need a real YAML parser. The bundled minimal fallback is not faithful enough for validation verdicts or content hashes. If PyYAML is missing, each script does one of two things:
- **If `uv` is installed,** it re-runs itself under `uv run --no-project --with pyyaml>=6.0`. It announces this on stderr, and on first use it may fetch PyYAML from your configured index.
- **Otherwise,** it exits **2** with a message explaining the fix. Exit 2 always points to *your environment*, never *your docs*.

In locked-down environments, set `CRUX_NO_UV_REEXEC=1` to turn off the automatic re-run and install PyYAML yourself.

### Dependency resolution for shipped scripts (PEP 723)

Shipped scripts whose documented invocation is `uv run …` carry PEP 723 inline metadata. The first time you use one, `uv` resolves its dependencies from *your configured index*. The dependencies are **not pinned by hash**, and `uv` caches them afterwards. This is the same trust model as the PyYAML re-run above.

In hermetic or locked-down environments, pre-install the declared dependencies yourself rather than letting first use reach the network. For stricter reproducibility, pin resolution with `uv run --exclude-newer <date>` or the `UV_EXCLUDE_NEWER` environment variable.

These invocations require `uv`. Without it, the command fails at the shell with `command not found`. Install `uv` from https://docs.astral.sh/uv/.

### The multi-model substrate

The plugin bundles a multi-model substrate that powers the agent layer:
- the LLM router (`call-llm`)
- the multi-model `council`
- `srde`
- the tracer
- the identity, knowledge, and task-planning modules

These tools need API keys, covered in the next section. They run under `uv`, which picks the interpreter named in each script's PEP 723 header. crux supports Python 3.13 and 3.14. `serve-llm` exposes the router over HTTP for clients that do not use Python.

### Self-improvement skills

**`forge-skill`** closes a capability gap in the middle of a task by writing or revising a skill local to your project under `.claude/skills/`. It is a prose workflow and needs no API keys of its own. Trigger it with *"forge a skill"*, *"author a skill for this"*, or *"close this capability gap"*.

It normally runs on its own and reports afterwards. It proposes first and waits for your approval when the capability:
- faces outward or is irreversible, such as sending externally, spending money, or publishing
- would touch anything outside the repository, or any secrets

A gap that would change project structure or external surfaces takes the brief or ADR path instead.

Every forge action is recorded in the append-only **forge log at `.claude/skills/forge-log.md`**. The log is a reviewable history of what was written, when, and why.

**`retrospective`** reflects on finished work. Trigger it with *"what should we learn from recent work"*, *"run a retrospective"*, or *"retrospective over the last N books"*. It works in these steps:

1. It mines `bionic/log.md`, the work journal, and recent run snapshots for patterns.
2. It distills the findings into at most two skill proposals.
3. It sends each proposal through the council before building it with `forge-skill`.
4. It records the outcome in a `Retrospective:` journal entry with a heading like `## [YYYY-MM-DD HH:MM] learning | Retrospective: …`.

`cleanup-campsite` tracks that entry and reminds you when enough archived promptbooks have piled up since the last retrospective.

The **`crux-env` CLI** keeps your API keys outside any repository. It has its own section below.

---

## Working with secrets and API keys

`~/.crux/` is your per-user secrets home, outside any repository. One file, `~/.crux/env`, holds the API keys for every crux project on your machine. The keys never leave your machine and never go into git.

### Running `crux-env`

You manage the file with the `crux-env` CLI, which ships inside the installed plugin. The full invocation is:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" <subcommand> …
```

`${CLAUDE_PLUGIN_ROOT}` is the plugin's installed root directory, and Claude Code sets it inside sessions. The examples below shorten the invocation to `crux-env`. Define your own shell alias if you use it often. These commands are the whole interface.

### One-time setup

```
crux-env init
```

This creates `~/.crux/` with safe file modes: `0600` on `env` and `0700` on `secrets/`. It is idempotent, so re-running it on an existing setup is safe.

### Adding a key

```
crux-env set OPENROUTER_API_KEY sk-or-xxxxxxxxxxxxxx
```

The value is stored in `~/.crux/env` with mode `0600`, so only you can read it. The key **name** is recorded in `~/.crux/log/crux-env.log`, but the **value is not**. That makes the log safe to share when debugging.

### Validating what's required

```
crux-env check --project <name>
```

This reads `~/.crux/required.yml` to find which environment variables the project needs, then checks that each one is set. It exits `0` if everything is present. It exits `1` with a JSON list of the missing variables if not. Run it before a workflow that depends on external services.

### Listing required keys without revealing values

```
crux-env list --project crux
```

This prints output like:

```
crux — required:
  ✓ CRUX_HOME
crux — optional:
  ✓ CRUX_DEBUG
```

`✓` means the key is set and `✗` means it is missing. Values are never printed, only key names.

### Removing a key

```
crux-env rm OLD_API_KEY
```

To rotate a key, `rm` the old one and `set` the new one.

### Reference

| Command | What it does |
|---|---|
| `crux-env init` | Creates `~/.crux/` with safe modes. Idempotent. |
| `crux-env set KEY VALUE` | Stores a key. Logs the name, never the value. |
| `crux-env rm KEY` | Removes a key. The removal is logged. |
| `crux-env check --project <name>` | Verifies that required variables are set. Exit 1 lists what is missing. |
| `crux-env list --project <name>` | Shows key names and whether each is set. Never prints values. |

### What NEVER to do

- ❌ **Never commit `~/.crux/` to git.** It lives outside your repository by design, so don't symlink it in.
- ❌ **Never share `~/.crux/env`.** Its mode-`0600` protection is useless once the file is posted to Slack.
- ❌ **Never paste a key into an issue, PR description, chat message, or screenshot.**
- ❌ **Never edit `~/.crux/log/crux-env.log`** to hide that you rotated a compromised key. The log is the audit trail.
- ✅ **Do rotate** any key you suspect has leaked. It costs one `set` command.

The full byte-level specification for the secrets store and the CLI contract is in §13 of `bionic/AGENTS.md` in your project.

---

## Per-project configuration: the repo-root `.bionic.yml` file

crux has two config surfaces, and they are easy to confuse:
- The repo-root **`.bionic.yml` file** holds per-project configuration and is committed.
- The **`~/.crux/` directory** in your home folder, described above, is your secrets store and is never committed.

A default `.bionic.yml` looks like this:

```yaml
config_version: "1"
docs_dir: bionic
artifact_prefix: ""
```

`.bionic.yml` replaces the legacy repo-root `.crux` file, which crux still reads for backward compatibility. Every tree crux creates or migrates gets a `.bionic.yml`:
- `init-docs` writes it when it bootstraps a tree.
- `audit-docs --migrate` writes it during the schema 4→5 upgrade.

Because the file always exists, crux reads the layout instead of guessing it.

### Settings

Edit and commit the file when you want a non-default convention:

- **`docs_dir`** moves the tree to another directory, such as `documentation/` or `meta/docs/`. The path is relative to the repository root. Absolute paths and `..` are not allowed.
- **`artifact_prefix`** adds a prefix to artifact ids so you can tell them apart across repositories. For example, with `artifact_prefix: "CRX"`, new ADRs get ids like `CRX-ADR-0012`, and new promptbooks get the same prefix. Existing artifacts are never renamed.

### Using a custom `docs_dir` in a new project

Copy the shipped template to the repository root and edit it **before** you say "init docs":

```bash
cp "${CLAUDE_PLUGIN_ROOT}/templates/bionic-yml.tmpl" .bionic.yml
```

`init-docs` writes the file itself when none exists. If you already committed one, `init-docs` merges into it and never overwrites it.

### Validating the file

Validation fails loudly. If `.bionic.yml` is malformed or invalid, every consumer exits `1` with the validation error instead of quietly falling back to defaults. Check your file with:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bionic-config.py"    # prints the resolved config as JSON
```

- ❌ **Never put secrets, tokens, or API keys in `.bionic.yml`.** The file is committed to git, and unknown keys are silently ignored, so a misplaced secret would not even produce an error. Secrets go in `~/.crux/`, full stop.

The full contract is in §14 of `bionic/AGENTS.md` in your project.

---

## Where to look first

When you open a project that uses crux, read in this order:

1. **`bionic/AGENTS.md`** is the operational schema and the single source of truth for what lives where and who edits what. It is long, so skim §1–§7 first.
2. **`bionic/index.md`** is the catalog of everything, with a section and counts for each concern.
3. **`bionic/adrs/`** holds the project's "why". Start at the lowest-numbered ADR and read forward in number order.
4. **`bionic/journal/`**: the most recent month shows what is happening now.
5. **`bionic/research/sources.md`** is the registry of external context the project draws on.
6. **`bionic/promptbooks/index.md`** shows what work is in progress.

---

## What you should NEVER do

- ❌ **Edit anything in `bionic/code/`.** Every extract run deletes hand edits.
- ❌ **Edit an ADR body once it is `Accepted`.** Write a new ADR that supersedes it.
- ❌ **Reorder `bionic/log.md` or edit past entries.** It is append-only audit history.
- ❌ **Delete `bionic/research/raw/`.** The old captures form the audit chain.
- ❌ **Reuse an ADR or promptbook number.** Numbers only ever increase.
- ❌ **Edit rows in `bionic/research/sources.md` by hand.** Let `ingest-research` and `audit-docs` maintain them.

If something feels wrong, such as a contradiction, a stale page, or a missing source, say so. Don't fix it silently. `audit-docs` catches drift, and your sense that "this looks off" is exactly what should trigger it.

---

## What you SHOULD do by hand

- Write `bionic/briefs/BRIEF-<slug>.md` files. They are *your* exploration before a decision. Claude tracks them but doesn't write them.
- Co-author the `## Goal`, `## Strategy`, and `## Prompts` sections of an active promptbook.
- Edit the repo-root `AGENTS.md` to add project-specific notes Claude should know. Just don't remove the `See bionic/AGENTS.md` line.

---

## Day-one quick start

In a project where `bionic/` was just initialized:

1. **Record today's intent as an ADR.** Say *"Propose an ADR explaining why we're using crux for this project."* Review it, then say *"Accept ADR-0001."*
2. **Capture the planning material.** Drop your existing design notes, specs, and chat exports into `bionic/inbox/` and say *"Process inbox."* Claude classifies each item and routes the research items through `ingest-research`.
3. **Plan the first piece of work.** Say *"New promptbook for <thing>."* Co-author the prompt list, then say *"Run it."*
4. **Journal at the end of the day.** Say *"Log today's work — `<one line summary>`."*
5. **Audit after the first ten writes.** Say *"Audit docs"* and confirm there is no drift.

---

## When things go wrong

| Symptom | Try this |
|---|---|
| "Where did Claude put X?" | Look at `bionic/index.md` and `bionic/<concern>/index.md`. |
| `bionic/code/` has stale content | Say *"extract code docs"*. It regenerates the directory completely. |
| An accepted ADR is wrong | Don't edit it. Write a new ADR that supersedes it. |
| A research synthesis page contradicts itself | Say *"refresh synthesis"*, and Claude walks you through reconciling it. |
| You lost track of a promptbook's progress | `bionic/promptbooks/index.md` shows the current run and its percent complete. |
| The whole `bionic/` tree feels broken | Say *"audit docs"* to run the integrity checks across all concerns. |

---

## Plugin and schema

This guide describes the `crux` documentation tree at `schema_version 5`, the `bionic/` layout. The installed plugin lives at `${CLAUDE_PLUGIN_ROOT}`.

### Installing and upgrading

| Host | Commands |
|---|---|
| Claude Code | `/plugin marketplace add bionic-coding/crux`, then `/plugin install crux@crux` |
| Codex | `codex plugin marketplace add bionic-coding/crux`, then `codex plugin add crux@crux` |

Codex users can then install the ten Crux role agents personally with the `install-codex-agents` skill.

### Migrating from a release before 3.19.0

After upgrading from a release before 3.19.0, say *"audit docs --migrate"*, even if `schema_version` is already `"5"`.

The migration converts tracked `CLAUDE.md` files to `AGENTS.md`. When both files exist at the same scope, it keeps the blocks unique to each file and removes only exact duplicates under the same heading path.

Sometimes the migration cannot merge cleanly: two headings conflict, or a block cannot keep its heading ancestry. In that case it keeps both source files and writes `.instruction-migration-preview.md`. To finish:

1. Create a JSON resolution file that reconciles each named block.
2. Copy `source_hashes` into it from `.instruction-migration-receipt.json`.
3. Say *"audit docs --migrate using the resolution file at `<path>`"*.

The migration also reports untracked and private suppressors, but it does not edit them.

`init-docs` also writes a copy of this guide into your project. Re-running `init-docs --force` overwrites that copy.
