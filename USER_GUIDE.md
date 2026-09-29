<!-- generated-from: USER_GUIDE.md@sha256:d48a650896b9aae304c772a626cfc98e82ceed2b72e3e161bcd473678e8e4abb; model: claude-opus-5.5; date: 2026-09-28 -->
# Working with `bionic/` in crux

A project that uses crux keeps its documentation in a `bionic/` folder at the repository root. The folder holds seven concerns plus two default-on surfaces, `arch` and `observations`, and the `crux` plugin maintains all of it. **You do not write these docs by hand.** You curate, decide, and discuss, and Claude does the bookkeeping.

This guide is for humans. An LLM agent working in your project should read `bionic/AGENTS.md`, which is the operational schema. `init-docs` writes that file into your project.

---

## At a glance

crux turns a `./bionic/` folder in your project into a knowledge base that you and Claude share and maintain together. It has four moving parts:

1. **The `bionic/` tree: seven concerns plus two default-on surfaces.**
   - The seven concerns are code docs, the research wiki, ADRs, briefs, the work journal, promptbooks, and invariants.
   - The two surfaces are the derived `arch` map and the `observations` records.
   - You curate and decide; Claude does the bookkeeping. See [The seven concerns](#the-seven-concerns).
2. **52 skills, triggered by natural language instead of slash commands.**
   - Examples: "propose an ADR", "process inbox", "audit docs", "start a cycle", "forge a skill".
   - Claude matches each phrase to a skill through the skill's description.
   - See [What to say to Claude](#what-to-say-to-claude). The plugin's `README.md` has the full catalog.
3. **10 agents: a role layer over the skills.**
   - A `commander` conductor delegates to `architect`, `dev-lead`, `developer`, `reviewer`, `historian`, `librarian`, `brainstormer`, and `wayfinder`.
   - A tool allowlist fences each agent, so duties are separated structurally.
   - See [The agent layer](#the-agent-layer).
4. **Three workflows for change.** All three are tracked promptbooks.
   - `dev-cycle` handles net-new or architectural work: ADR, council, and review.
   - `iterate` handles non-architectural fixes: verify, council, and review, with no ADR.
   - `patch-cycle` handles a small reversible fix: five phases, one prompt each, and a declared blast radius.
   - For a defect whose fix you can name before starting, use `fix-directly`. It needs no promptbook, only a failing test first.
   - See [Planning multi-step work](#planning-multi-step-work--promptbooks--cycles).

Underneath, the plugin ships Python **scripts** that the skills call for you: extractors, validators, and the LLM router. It also ships the `crux-env` **CLI** for secrets. See [Tools & scripts](#tools--scripts).

**If you read nothing else:**
- Drop anything into `bionic/inbox/` and say *"process inbox"*.
- Ask *"what does X do?"* or *"why did we choose Y?"*.
- Say *"start a cycle for X"* or *"iterate on X"* to ship a change with a record of the work attached.

---

## Plugin paths in this guide

Some references in this guide point at files inside the installed plugin, not inside your project.

- **`CRUX_PLUGIN_ROOT`** is the installed plugin's root on any host (Claude Code, Codex, or OpenCode). To find it, locate the selected Crux `SKILL.md`. That file sits inside a `skills/` directory, and `CRUX_PLUGIN_ROOT` is the parent of that `skills/` directory. Shared references to the plugin's reference files use `${CRUX_PLUGIN_ROOT}/box/...`.
- **`${CLAUDE_PLUGIN_ROOT}`** is a Claude Code variable. Claude Code sets it inside sessions to the plugin's installed root. It is not a portable path. Command examples that use it are labeled Claude Code-specific. On other hosts, substitute `${CRUX_PLUGIN_ROOT}`.

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

_This guide uses the default `bionic/` layout. If your project sets a custom `docs_dir`, read that directory wherever this guide says `bionic/`._

| Directory | What lives there | Who edits |
|---|---|---|
| `bionic/code/` | Docs extracted automatically from source code (docstrings, @doc, JSDoc) | **Regenerated. Never edit by hand.** Every extract run deletes hand edits. |
| `bionic/research/` | Articles, papers, web pages, meeting notes, and chat exports | You drop sources in `bionic/inbox/`. `process-inbox` routes them to `ingest-research`, which stores each one in the immutable `bionic/research/raw/` and runs the ingest pipeline. |
| `bionic/adrs/` | Architecture Decision Records: the "why" behind each load-bearing decision | You decide; Claude writes the ADR. **Once an ADR is `Accepted`, its body is frozen.** |
| `bionic/briefs/` | Exploration documents written before a decision (`BRIEF-<slug>.md`) | You write them; Claude tracks them. |
| `bionic/journal/` | A day-by-day record of work performed (`YYYY-MM.md`) | Claude appends entries when you ask. |
| `bionic/promptbooks/` | Plans of prompts you want to execute, plus immutable run snapshots | Co-authored. The plan is editable; run history is frozen. |
| `bionic/invariants/` | Pinned, executable statements of *what must be true*. Each pin has a ledger page. The executable checks live in `invariants/checks/`, and `invariants/reconciliation.yml` reconciles pins with checks. | **The machine proposes; you ratify.** `recover-invariants` mines candidates and records them as `observed`. You ratify, reject, or retire each one with `transition-invariant`. Recovery never ratifies its own candidates. |
| `bionic/observations/` (default-on) | Records of what the code *already does* (`OBS-NNNN-<slug>.md`). Each one cites a `path:line-range` as evidence and never quotes the code itself. | **You write and ratify them.** `propose-observation` creates one in the `observed` state. `transition-observation` is the only route that moves a single record past `observed`, to `ratified`, `rejected`, `retired`, or `decided`. The survey sign-off is the only batch route. No scan writes an observation file in any state. |
| `bionic/arch/` (default-on) | The derived architecture map of the project's current state: data model, interface surface, module graph, decision index, and a synthesized overview | **Regenerated. Never edit by hand.** `derive-arch` builds it on demand. New trees enroll it by default. |

### Invariants

**Invariants** complete what the other concerns start. The other concerns record knowledge. Invariants pin *what must stay true* as executable checks, and those checks survive regeneration.

A new project starts with an empty invariants concern. An empty concern is clean, not broken. Run `recover-invariants` when you're ready to mine candidates.

### The `arch` surface

Beyond the seven concerns, crux enables **`bionic/arch/`**, the derived architecture, by default. It is the main place to answer *"how is this project shaped right now?"*

- It contains a deterministic core (data model, interface surface, module graph, and decision index) plus a synthesized overview.
- crux regenerates all of it from your project's own sources on every derive.
- ADRs are the secondary source: they explain *why*. The librarian and historian fill the remaining gaps.

`init-docs` enrolls arch in new projects, so you can just say **"build the arch"**. Keep it current with `derive-arch`, or let `audit-docs` regenerate it when it drifts.

A tree created before arch became a default must opt in first: add `arch` to `concerns_enabled`, then derive. Like `code/`, arch is never edited by hand.

### The `observations` surface

crux also enables **`bionic/observations/`** by default. It records what the code already does.

- **An observation describes; it does not decide.** An ADR records a choice somebody made. An observation records a fact nobody wrote down, with a `path:line-range` into the real source as evidence.
- A project with no ADRs uses observations as its starting layer. A project with many ADRs uses them for everything the ADRs never covered.
- Say **"propose observation"** to create one. It starts in the `observed` state.
- Only you can move it further. `transition-observation` is the only route for a single record, and `survey-signoff` is the only batch route. No scan ever writes or ratifies an observation.
- Ratified observations feed the same summaries and doctrine projections that ADRs feed. Once you affirm an observation, it carries real authority.

The batch route takes two steps and covers as many candidates as you put on one sheet:

1. Say **"scaffold a survey sheet"**. `survey-sheet` builds one sheet covering the candidates in `observed`, and fills each row with a claim and a proposed domain. You complete each row:
   - a verdict of `ratify`, `reject`, or `defer`;
   - a one-line rationale;
   - a domain, if the proposed one is wrong.
2. Say **"sign off the survey"**. `survey-signoff` displays every claim with its verdict for you to read. After you confirm, it publishes the batch under one receipt bound to a digest of its contents. One signature covers every ratification in the batch.

Only you invoke these two commands, and neither runs unattended.

---

## The agent layer

crux ships ten **agents** that operate the skills above.
- Claude Code loads the agents directly from the plugin.
- Codex and OpenCode use generated native versions.

### What each agent does

- **commander** runs a promptbook or cycle and delegates every step. It never edits anything itself.
- **brainstormer** explores a design with you using the `whiteboarding` skill, then hands the session to the historian to file.
- **architect** owns ADRs and decisions. It drafts them, runs the council, and accepts them.
- **dev-lead** leads implementation and hands independent pieces of work to **developer** agents.
- **reviewer** reviews code independently. It is read-only, so it reports findings and cannot quietly fix problems itself.
- **historian** owns every write under `bionic/`.
- **librarian** answers questions from `bionic/`. It only reads.
- **wayfinder** handles large, uncertain, or external data before a primary agent reads it.
  - It reads the data in an isolated context and judges whether it fits your purpose.
  - It returns a verdict and a condensed digest, so the primary agent spends its own context only on content that fits.
  - It is read-only. It is the only agent with `WebFetch` and `WebSearch`, and an egress guardrail limits what it can send out.
- **night-gardener** works overnight as a scheduled routine.
  - It reviews what changed since your last move and leaves a morning note under `bionic/garden/`. The note covers ideas, codebase improvements, missing tests, CI, or guards, research, and news.
  - It takes turns with you: it skips a run when the only changes since the last one are its own.
  - It works as a full co-CTO, but only behind the existing gates, and it never pushes.
  - To dismiss or snooze its advice, edit `bionic/garden/tending.md`. It needs no acknowledgment.
  - Its news pass reads a curated source list through the `read-news` skill.

### Roles and hosts

Each role declares its tool boundaries and required skills. Host permissions can override a role's default sandbox, but the role prompt remains binding either way. The agents build in the disciplines they need, including testing, verification, debugging, and two-stage review.

| Agent | Use it when you want… | It is bounded so it cannot… |
|---|---|---|
| `commander` | a whole cycle or promptbook driven end to end, with each step delegated | edit code or docs itself |
| `brainstormer` | to explore a fuzzy idea before committing (it drives `whiteboarding`) | write files or touch code |
| `architect` | a decision recorded and council-reviewed (`propose-adr` → `council` → `transition-adr`) | implement code |
| `dev-lead` | implementation coordinated across parallel units | merge or push (a human must approve) |
| `developer` | one scoped unit built test-first | delegate further, or write docs or ADRs |
| `reviewer` | an independent check of a diff | edit files (it reports and never fixes quietly) |
| `historian` | anything written under `bionic/` (intake, journaling, indexes) | edit source code |
| `librarian` | a question answered from `bionic/` (`query-docs`) | write anything |
| `night-gardener` | an overnight pass that records ideas, gaps, research, and news | push, merge, or send material externally |
| `wayfinder` | a large, uncertain, or external source checked for fit and condensed before you read it | write, execute, delegate, or send local content outbound |

### Installing the agents in Codex

After installing the plugin in Codex, say **"install the Crux agents in Codex"**.
- The installer writes ten namespaced `crux_*` roles to `~/.codex/agents/` by default.
- Each role pins the model and reasoning effort from the catalog, and binds its declared skills to the installed plugin.
- Pass `--repo-root` to install into one project's `.codex/agents/` directory instead.

Refreshing and checking:
- Refreshing unchanged files does nothing.
- If managed files have changed or gone stale, review them, then pass `--force`.
- Skill bindings use absolute paths, so moving the plugin shows up as drift.
- `--check --project-context <repo>` reports managed drift, and project agents that shadow your personal roles.
- The report lists what the files should contain separately from what the TOML files on disk actually contain.
- The runtime result stays `unverified` until a fresh session on your Codex version confirms discovery, settings, skills, and representative workflows.

### How you actually use them

You rarely name an agent: a cycle, through the `commander`, dispatches them for you. You can still be explicit. For example:
- *"have the architect propose an ADR for X"*
- *"send this design to the council"*
- *"have the reviewer check the diff"*
- *"ask the librarian what we decided about Y"*

---

## What to say to Claude

These phrases trigger the right skill. Use them in ordinary sentences, and Claude works out the rest.

### Recording decisions

| Say | Skill | What happens |
|---|---|---|
| "Propose an ADR for X" | `propose-adr` | Creates a **new** `ADR-NNNN-<slug>.md` in `bionic/adrs/` with status `Proposed`. You then review the alternatives. |
| "Accept ADR-NNNN" | `transition-adr` | Moves an **existing** decision from `Proposed` to `Accepted`. The body is frozen from then on. |
| "Supersede ADR-NNNN with ADR-MMMM" | `transition-adr` | Updates both ends of the supersession link in one step. |
| "Deprecate ADR-NNNN" | `transition-adr` | Retracts an existing decision without a replacement. |
| "Sign off backfill batch `<id>`" | `backfill-signoff` | Records your sign-off as owner for one backfill batch, as described below. |

`propose-adr` only creates new `Proposed` decisions. `transition-adr` only changes an existing decision's status: it accepts, supersedes, or deprecates.

When you sign off a backfill batch, crux shows you the rule and anchor of every listed receipt, word for word, before anything is written. The sign-off script is the only way to write to the backfill surfaces:
- the signed-date flip;
- the admission ledger;
- the log operation;
- the journal hook;
- the completion marker.

Never edit those surfaces by hand.

ADRs are append-only history. You can't edit an accepted ADR; instead, propose a new one and supersede the old one.

### Capturing anything: the unified inbox

`bionic/inbox/` is the one place to drop raw input. You can drop any kind of item there: a research file, a pasted URL, a rough decision note, or a stray idea. Then say **"process inbox"**.

The `process-inbox` skill classifies each item and shows you a confirmation table with the item, the proposed skill, and a confidence level. When you reply `ok`, it sends each item to the skill that owns its concern:

| Item type | Routed to |
|---|---|
| Research source: a file, a URL, or a `urls.md` manifest | `ingest-research` |
| Architectural decision | `propose-adr` (always created as `Proposed`) |
| Exploration before a decision | `propose-brief` |
| Work-log note | `log-work` |

Claude classifies first and asks you to confirm. Your `ok` sends only the items Claude is confident about. Items it is unsure about are held back:
- `override N=<target>` sends item N to a skill you choose.
- `defer N` leaves item N for a later run.

`process-inbox` never accepts an ADR automatically.

**Research items go through the `ingest-research` pipeline.** The pipeline does three things:
- it moves each item into a dated, immutable capture under `bionic/research/raw/`;
- it writes an audited source page;
- it updates the affected synthesis pages.

Ways to add research:

| Say / do | What happens |
|---|---|
| Drop a file in `bionic/inbox/`, then say "process inbox" | Research items go through the pipeline above. |
| Paste a URL into a file under `bionic/inbox/`, or hand it to Claude, and say "ingest this" | Same pipeline. The bundled `web-to-markdown.py` fetches the page. |
| Drop a `urls.md` file in `bionic/inbox/` with one URL per line | Bulk import. Add `(static)` after a URL to exclude it from refresh checks. If some URLs fail, `urls.md` stays in place and the next run retries them. |
| "Refresh sources" | Re-fetches the URLs not marked static, stores updates as new dated captures, and flags the synthesis pages they affect. |
| "Refresh synthesis" | Walks you through the accumulated markers on each page, such as contradictions and source updates. |

### Journaling work

| Say | What happens |
|---|---|
| "Log work" / "journal this" | Adds an entry to `bionic/journal/YYYY-MM.md` with today's date and a category. |

Claude may also log work on its own after meaningful operations, such as an accepted ADR, a completed promptbook, or a large refactor.

Categories: `decision | implementation | bug | learning | blocker | refactor | meeting | review | misc | release`.

**Two modes.** `log-work` chooses a mode before writing:
- **When you ask for a journal entry**, it adds a reflective entry to the monthly journal, regenerates the journal index, and records one `journal` operation.
- **When Claude calls it on its own**, it defaults to log-only mode. That mode requires a valid operation and writes only to `bionic/log.md`.

**Results.** The bundled writer checks the request before writing and reports one of three results: `complete`, `refused`, or `partial`.

**Retrying a partial write.**
- Keep the original request and its explicit local UTC offset, so you can retry it.
- A partial entry that records only the month cannot prove which offset was used, so the writer warns `offset unverified`.
- If the offset was lost, stop any automated retry and work out the offset from the available evidence.

**Entry size.** A journal body can have 1 to 10 lines you write yourself. An optional `Refs:` line doesn't count toward that limit.

### Planning multi-step work: promptbooks and cycles

Five ways to plan multi-step work:

| Say | Skill | Use it for |
|---|---|---|
| "Start a cycle for X" | `dev-cycle` | **Net-new or architectural** work. It assembles a tracked promptbook of ADR, dev, and review modules. The decision is recorded as an ADR and reviewed by the council, then implemented, then independently reviewed. The cycle has at least 13 prompts. |
| "Iterate on X" / "remediate X" | `iterate` | **Non-architectural fixes**: bugs, drift, and refinements to existing behavior. It has the same council and review rigor as `dev-cycle`, but a *verify* module replaces the ADR. The verify module reproduces the problem, finds the root cause, and has the council review the diagnosis. If the council finds the work is architectural after all, it stops and sends you to `dev-cycle`. |
| "Patch this" | `patch-cycle` | A **small, reversible**, non-architectural change that you can bound by naming the paths it may touch. See below. |
| "Just fix it" | `fix-directly` | A defect whose files, failing test, and unchanged contracts you can name before starting. There is no book, no council, and no promptbook number. You write a failing test first, then make the smallest change that turns it green, then run the suite and the drift checks. The result is one commit and one journal entry. A security label raises a defect's priority, not its size; the sizing test decides the tier. |
| "New promptbook for X" | `author-promptbook` | A custom multi-prompt plan that you write with Claude, with **no** required council or review. Use it for sequences that don't need that process. |

**Patch cycles.** A patch cycle has five phases, one prompt each: verify, plan, implement, review, and summary.
- You declare a *blast radius* up front: the set of paths the change may touch.
- The council checks that the declared radius is no wider than the work needs.
- Before archiving, crux uses git to compare the paths the run actually changed against the declaration.
- A change that reaches outside its declaration can't be archived as delivered. You must redo it as an `iterate` or `dev-cycle`.
- Work that needs an ADR is never a patch.

**Driving any of them:**

| Say | What happens |
|---|---|
| "Run it" | Starts an immutable run snapshot under `bionic/promptbooks/runs/PB-NNNN-<slug>/run-RUN-NNN.yaml`. |
| "Advance" / "next prompt" | Marks the current prompt done and moves to the next. This changes only the run snapshot and the active book pointer; it writes no log entry for the prompt. |
| "Abandon this run" | Closes a run that will not finish. |
| "Archive promptbook" | Closes the book. The run must have completed with every prompt in a terminal state (done, skipped, or blocked), or have been deliberately abandoned. |
| "Promptbook status" | Shows the current run's progress through the `run-promptbook` status procedure. |

Checking status is read-only. A terminal view or status answer writes nothing. The status procedure writes a Markdown progress file only if you explicitly pass `--markdown`.

Books and runs are structured `.yaml` documents. crux validates them against a JSON Schema, and cycle books must also pass the cycle-coverage checks.

You can't edit a book's prompt list during a run. To change it, abandon the run and write a successor book that names its predecessor. Book numbers are never reused.

#### Retired entries

If you're upgrading from an installation that used any of the seven retired entries, use these routes instead.

Find the plugin root the same way on Claude Code, Codex, and OpenCode: `CRUX_PLUGIN_ROOT` is the parent of the `skills/` directory that contains the selected Crux `SKILL.md`. `${CLAUDE_PLUGIN_ROOT}` exists only in Claude Code and is not a portable plugin path.

| Former entry | Current route |
|---|---|
| `task-planner` | `whiteboarding` for exploration; `author-promptbook` or a cycle for a tracked plan. The Python task-planner API is documented in `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`. |
| `author-runbook` | Tracked planning by default. Explicit generator instructions are in `${CRUX_PLUGIN_ROOT}/box/operator-services.md`. |
| `visualize-run-progress` | `run-promptbook` status. The renderer script is still available. |
| `trace-runtime-ops`, `semantic-bridge`, `agent-identity` | The Python APIs in `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`. |
| `serve-llm` | The HTTP service instructions in `${CRUX_PLUGIN_ROOT}/box/operator-services.md`. |

These names no longer select installed skills. Your existing runs, runbooks, identities, and Python modules are unaffected.

### Extracting code docs

| Say | What happens |
|---|---|
| "Extract code docs" | Runs the plugin's `extract-code-docs.py` dispatcher with the settings in `bionic/manifest.yml`, and regenerates `bionic/code/` from source. |
| "Verify code docs" | Does a dry run that reports drift without writing anything. |

To choose which extractors run, edit `code.extractors:` in `bionic/manifest.yml`. The plugin ships extractors for Elixir and Python, plus a fallback that scrapes header comments. Additional languages arrive as extractor plugins in the plugin's `scripts/extractors/` directory.

**Python.** A `python` key under `code.extractors:` accepts exactly three fields:
- `extractor`;
- `glob`;
- `include_private` (optional, on by default).

Any other key at that level makes the run refuse to start:

```yaml
code:
  extractors:
    python:
      extractor: python
      glob: "src/**/*.py"
      include_private: true
```

**How the Python extractor runs:**
- The dispatcher runs it under `uv run --no-config`, so `uv` ignores any `uv.toml` file or `[tool.uv]` table.
- The script's PEP 723 block pins `griffelib==2.3.0`. Any other installed version makes it exit with code 2.
- The extractor reads your sources statically. It never imports or runs your code, never installs your dependencies, and never executes documentation examples.

**Dispatcher outcomes:**

| Outcome | Meaning |
|---|---|
| Exit `0` | Clean: no drift. |
| Exit `1` with a `drift` payload | The docs on disk are stale. Run again without `--dry-run` to regenerate them. |
| Exit `1` with a `validation_errors` payload | The content was refused. Causes include a parse failure, an oversized source, an output root that no extractor owns, or an extractor name the plugin doesn't ship. The input is broken; this is not drift, and regenerating won't fix it. This payload appears only under `--dry-run`, which is what the `verify-code-docs` skill uses. In write mode, the same refusal exits `1` with a message on stderr, prints nothing to stdout, and changes no output files. |
| Exit `1`, message on stderr, nothing on stdout | A configuration error, with or without `--dry-run`. Causes include a `--config` path that doesn't exist, a `--lang KEY` the manifest doesn't configure, or a `.bionic.yml` or `.crux` file that can't be resolved. |
| Exit `2`, message on stderr, nothing on stdout | Your environment lacks something the extractor needs: the Python interpreter is older than 3.13, or `griffelib` is missing or the wrong version. |
| `uv`'s own exit code, nothing on stdout | `uv` failed to resolve dependencies. |

### Summarizing the current architecture

| Say | What happens |
|---|---|
| "Build the arch" / "summarize the current architecture" / "regenerate the architecture" | Runs `derive-arch`. It detects your stack and regenerates `bionic/arch/` entirely from your project's own sources. |
| "What's the current architecture?" | Reads `bionic/arch/overview.md` (or ask the librarian). `derive-arch` builds the map; the librarian answers questions from it. |
| "Escalate the arch runtime" | Runs `escalate-arch-runtime`, an optional, opt-in upgrade for Python projects. See below. |

#### Supported stacks

`derive-arch` includes packs for Python, Ruby, Node.js, Elixir/Phoenix, and Swift. The Swift pack covers Swift packages and Xcode projects, including targets, product types, membership, and `@main` owners.

Each pack derives three things.

- **The data model** comes from your ORM, schema, or type declarations:
  - SQLAlchemy, SQLModel, and Django models;
  - ActiveRecord's `schema.rb`;
  - Prisma, TypeORM, and Sequelize;
  - Ecto;
  - Swift `struct`, `class`, `enum`, and `actor` declarations.
- **The interface surface** comes from a committed OpenAPI document or from the framework's routes. For Swift, it comes from `public`, `package`, and `open` declarations, every protocol, the package products, and the `@main` declarations.
- **The module graph** comes from the import graph. For Swift, it also includes the targets and dependencies declared in `Package.swift` manifests and Xcode project files.

Two Swift edge cases:
- If an XcodeGen or Tuist manifest is present but its generated project file is missing, the map marks that input as missing.
- A conditional build setting appears as a `conditional-setting` residual.

#### Coverage report

Each concern gets a verdict of `populated` or `stubbed`, recorded in `_meta/coverage.json`. The same verdicts print as a coverage table, with one remediation line for each concern that isn't `populated`. The tool reports what it found and doesn't grade it.

#### Missing parsers

If your machine lacks a parser that a stack declares, `derive-arch` exits with code 2 and writes nothing. The parser is `tree-sitter` plus the language's grammar: `tree-sitter-elixir` for Elixir and `tree-sitter-swift` for Swift. Node.js and Ruby also declare grammars. The fix is to install the parser, not to change your docs.

#### Escalating the arch runtime

`escalate-arch-runtime` is an optional upgrade for Python projects. It never runs on its own, and `derive-arch` never suggests it as a fix.

- **What it does:** it recovers what the static extractor missed, such as the route table and the ORM schema. It does this by running your FastAPI, Flask, or Django app's import-time code in a sandboxed subprocess.
- **Consent:** it requires the `CRUX_ARCH_ALLOW_RUNTIME=1` consent setting, and it asks your permission on every run.
- **Output:** results go to `bionic/inbox/` as advisory material, never to `bionic/arch/`.

#### Enabling and maintaining arch

New projects get arch by default because `init-docs` enrolls it, so you can build it right away. On a tree created before that default, first add `arch` to `concerns_enabled` in `bionic/manifest.yml`, then build it.

Keep arch current by re-running `derive-arch` whenever any of its inputs change, or let a routine **"audit docs"** regenerate a map that has drifted. Never edit `bionic/arch/` by hand: the next derive overwrites it.

### Asking questions

| Say | What happens |
|---|---|
| "What does X do?" | Searches `bionic/code/` and cites the pages it used. |
| "Why did we choose Y?" | Searches `bionic/adrs/` and `bionic/briefs/`. |
| "What's the plan for Z?" | Checks the active promptbooks. |
| "What do we know about W?" | Searches the research wiki. |

Claude will offer to file good answers back into `bionic/research/ideas/`.

### Checking health

| Say | What happens |
|---|---|
| "Audit docs" | Runs about 54 integrity checks across every enabled concern. It fixes safe drift automatically, such as counts, dates, and missing index rows, and shows you anything broken for your decision. |
| "Review the decisions" / "run a decision review" / "decision review" / "do the decisions still serve the objectives" / "review the ADR set against the objectives" / "is the decision set still right" | Runs `review-decisions`, which measures your decisions against `bionic/objectives.md`. See below. |

Run an audit after about every ten writes, after a large refresh, and before any release.

**How a decision review works:**
- **Output.** Each review writes one dated report to `bionic/adrs/reviews/YYYY-MM-DD.md`.
- **Finding sections.** Findings go in four sections: **Propose, Amend, Repair, and Revoke.** A review keeps at most five findings in total across the four sections.
- **Other sections.** Two further sections hold no findings and have no limit:
  - **Keep** lists decisions read during the review that still serve the objectives.
  - **Coverage** names what the review could not see.
- **Zero findings** is a valid result.
- **Editing.** You keep the report by hand; crux regenerates only `bionic/adrs/reviews/index.md`.
- **Scope.** A review proposes findings and changes nothing. Acting on a finding is a separate step that the review never takes:
  - For a new decision, say "propose an ADR" (`propose-adr`).
  - For an existing one, say "accept", "supersede", or "deprecate ADR-NNNN" (`transition-adr`).

Run the review weekly. `cleanup-campsite` reminds you when the newest report is older than `adr_review_due_days`, which defaults to seven days.

---

## Tools & scripts

Python scripts in the plugin's `scripts/` directory back everything Claude does. The documentation tooling uses only the Python standard library. The multi-model substrate, described below, adds dependencies declared through PEP 723. **You almost never run these scripts yourself**, because the skills run them for you. Knowing they exist helps when something looks wrong.

**Scripts that skills run for you:**

| Script | Skill that runs it | What it does |
|---|---|---|
| `extract-code-docs.py` | `extract-code-docs` / `verify-code-docs` | Regenerates `bionic/code/` from source docstrings, using a plugin for each language in `scripts/extractors/`. |
| `web-to-markdown.py` | `ingest-research` / `refresh-research-sources` | Fetches a URL and converts it to audited Markdown. |
| `transcribe-video.py` | `ingest-research` | Transcribes a video source to text. |
| `visualize-run-progress.py` | `run-promptbook` status | Reads run progress. It writes a byte-stable Markdown file only when you pass `--markdown`. |
| `write-journal.py` | `log-work` | Validates and writes a journal entry, together with the derived index and log operation, or a single log-only operation. It reports partial writes so you can retry them. |

**Validators (run on demand or in CI; they never publish):**

| Script | What it does |
|---|---|
| `validate-promptbook.py` | Validates a promptbook or run `.yaml` file (`--kind promptbook\|run`) against its draft-2020-12 JSON Schema **and** the cycle-coverage checks. `dev-cycle`, `iterate`, and `patch-cycle` books must pass it. |
| `check-blast-radius.py` | Compares the paths a `patch` run changed, as recorded by git, against the blast radius its book declared. `archive-promptbook` runs it before archiving. |

> **PyYAML requirement.** `validate-promptbook.py` and `visualize-run-progress.py` need a real YAML parser. The bundled minimal fallback isn't accurate enough for validation verdicts or content hashes.
>
> When PyYAML is missing, each script does one of two things:
> - If `uv` is installed, it re-runs itself under `uv run --no-project --with pyyaml>=6.0` and says so on stderr. The first run may download PyYAML from your configured package index.
> - Otherwise, it exits with code **2** and a message explaining how to fix it. Exit code 2 always points to *your environment*, never *your docs*.
>
> In locked-down environments, set `CRUX_NO_UV_REEXEC=1` to turn off the automatic re-run, and install PyYAML yourself.
>
> **Runtime and first-use dependency resolution (uv / PEP 723).** Shipped scripts that you invoke with `uv run …` declare their dependencies in inline PEP 723 metadata.
> - **What happens on first use.** The first time you run one, `uv` resolves those dependencies from *your configured package index* and caches them. Dependencies are **not pinned by hash**. This is the same trust model as the PyYAML re-run above.
> - **Hermetic or locked-down environments.** Install the declared dependencies yourself beforehand, so the first run doesn't reach the network.
> - **Stricter reproducibility.** Limit resolution to packages published before a date with `uv run --exclude-newer <date>`, or set the `UV_EXCLUDE_NEWER` environment variable.
> - **`uv` is required.** Without it, these commands fail at the shell with `command not found`. Install it from https://docs.astral.sh/uv/.

**The multi-model substrate** lives in the plugin's `scripts/crux/` package. It includes:
- the LLM router (`call-llm`);
- the multi-model `council`;
- `srde`;
- the tracer;
- the identity, knowledge, and task-planning modules that power the agent layer.

These tools need API keys (see the next section). They run under `uv`, which picks the Python interpreter named in each script's PEP 723 header. crux supports Python 3.13 and 3.14.

Further references:
- An HTTP service makes the router available to clients not written in Python. See `${CRUX_PLUGIN_ROOT}/box/operator-services.md`.
- For the tracing, probe coordination, identity, and task-planning APIs, see `${CRUX_PLUGIN_ROOT}/box/runtime-apis.md`.

The `forge-skill` loop described below is a written workflow, not code, so it needs no API keys.

**`forge-skill`** fills a missing capability during a task by writing or revising a skill local to your project, under `.claude/skills/`.
- **Trigger phrases:** *"forge a skill"*, *"author a skill for this"*, *"close this capability gap"*.
- **When it asks first:** normally it works on its own and reports afterwards. It waits for your approval first in three cases:
  - The capability is outward-facing or irreversible, such as sending messages externally, spending money, or publishing.
  - It would touch anything outside the repo, or any secrets.
  - The change would alter project structure or external surfaces. These cases go through a brief or an ADR instead.
- **Record:** every forge action goes into the append-only **forge log at `.claude/skills/forge-log.md`**. It gives you a reviewable history of what was written, when, and why.

**`retrospective`** reflects on finished work.
- **Trigger phrases:** *"what should we learn from recent work"*, *"run a retrospective"*, *"retrospective over the last N books"*.
- **What it does:** it looks for patterns in `bionic/log.md`, the work journal, and recent run snapshots. It turns its findings into at most two skill proposals, and each proposal must pass the council before `forge-skill` builds it.
- **Record:** outcomes go into a journal entry with the heading `## [YYYY-MM-DD HH:MM] learning | Retrospective: …`. `cleanup-campsite` uses that heading to remind you when enough books have been archived since the last retrospective.

The **`crux-env` CLI** keeps your API keys outside every repo. The next section covers it.

---

## Working with secrets and API keys

`~/.crux/` is your personal secrets folder, outside every repo. One file, `~/.crux/env`, holds the API keys for every project on your machine that uses crux. The keys never leave your machine and never go into git.

You manage the keys with the `crux-env` CLI, which ships with the plugin. In **Claude Code**, run it like this:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" <subcommand> …
```

Claude Code sets `${CLAUDE_PLUGIN_ROOT}` to the plugin's installed root during sessions. On other hosts, or outside a session, use `${CRUX_PLUGIN_ROOT}` instead. To find that path, see [Plugin paths in this guide](#plugin-paths-in-this-guide).

The examples below shorten the full command to `crux-env`. If you use it often, define a shell alias. These commands make up the whole interface.

### One-time setup

```
crux-env init
```

This creates `~/.crux/` with safe file permissions: mode `0600` on `env` and `0700` on `secrets/`. You can safely run it again on an existing setup.

### Adding a key

```
crux-env set OPENROUTER_API_KEY sk-or-xxxxxxxxxxxxxx
```

The value is stored in `~/.crux/env` with mode `0600`, so only you can read it. The key **name** is recorded in `~/.crux/log/crux-env.log`, but the **value never is**. The log is therefore safe to share when debugging.

### Checking required keys

```
crux-env check --project <name>
```

This reads `~/.crux/required.yml` to find which environment variables the project needs, then checks that each one is set. For example, `crux-env check --project crux` checks what crux itself needs. The command exits `0` if everything is set. Otherwise it exits `1` and prints a JSON list of what's missing. Run it before any workflow that depends on external services.

### Listing required keys without revealing values

```
crux-env list --project crux
```

This prints something like:

```
crux — required:
  ✓ CRUX_HOME
crux — optional:
  ✓ CRUX_DEBUG
```

`✓` means the key is set, and `✗` means it's missing. Only key names are printed, never values.

### Removing a key

```
crux-env rm OLD_API_KEY
```

To rotate a key, `rm` the old one and `set` the new one.

### Reference

| Command | What it does |
|---|---|
| `crux-env init` | Creates `~/.crux/` with safe permissions. Safe to re-run. |
| `crux-env set KEY VALUE` | Stores a key. Logs the name, never the value. |
| `crux-env rm KEY` | Removes a key and logs the removal. |
| `crux-env check --project <name>` | Checks that required environment variables are set. Exits `1` and lists what's missing. |
| `crux-env list --project <name>` | Shows key names and whether each is set. Never prints values. |

### What NEVER to do

- ❌ **Never commit `~/.crux/` to git.** It lives outside your repo on purpose, so don't symlink it into one.
- ❌ **Never share `~/.crux/env`.** Its `0600` permissions stop helping the moment someone posts the file in Slack.
- ❌ **Never paste a key into an issue, PR description, chat message, or screenshot.**
- ❌ **Never edit `~/.crux/log/crux-env.log`**, for example to hide that you rotated a compromised key. The log is the audit trail.
- ✅ **Do rotate** any key you suspect has leaked. It costs one `set` command.

### Where to read more

`bionic/AGENTS.md` §13 in your project gives the full byte-level specification for the secrets store and the CLI.

---

## Per-project configuration: the repo-root `.bionic.yml` file (formerly `.crux`)

crux has two configuration locations, and they are easy to confuse:

| Location | Purpose | Committed to git? |
|---|---|---|
| **`.bionic.yml`**, a file at the repo root | Per-project configuration | Yes |
| **`~/.crux/`**, a directory in your home folder (see above) | Your secrets store | Never |

A default `.bionic.yml` looks like this:

```yaml
config_version: "1"
docs_dir: bionic
artifact_prefix: ""
```

`.bionic.yml` replaces the legacy repo-root `.crux` file. crux still reads `.crux` for backward compatibility.

Every tree crux creates has a `.bionic.yml`:
- `init-docs` writes it when it sets up a new tree.
- The pinned public `v3.23.2` recovery release writes it when it upgrades a tree from schema 4 to 5.

As a result, crux reads the layout from the file instead of guessing it.

Commit changes to `.bionic.yml` when you want something other than the defaults:

- **`docs_dir`** moves the tree, for example to `documentation/` or `meta/docs/`. The path is relative to the repo root. Absolute paths and `..` are not allowed. The default is `bionic`.
- **`artifact_prefix`** adds a prefix to artifact IDs so you can tell them apart across repos. With `artifact_prefix: "CRX"`, new books and ADRs get IDs like `CRX-PB-NNNN` and `CRX-ADR-NNNN`. Existing artifacts keep their IDs.

To use a non-default `docs_dir` in a new repo, copy the shipped template to the repo root and edit it **before** you say "init docs". `init-docs` writes the file itself only when it's missing, and it merges into a committed file without overwriting it. In **Claude Code**:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/templates/bionic-yml.tmpl" .bionic.yml
```

On other hosts, replace `${CLAUDE_PLUGIN_ROOT}` with `${CRUX_PLUGIN_ROOT}`.

Validation fails loudly. If `.bionic.yml` is malformed or invalid, every tool that reads it exits `1` with the validation error. None of them silently falls back to the defaults. To check your file (Claude Code syntax shown):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bionic-config.py"    # prints the resolved config as JSON
```

- ❌ **Never put secrets, tokens, or API keys in `.bionic.yml`.** The file is committed to git. crux also ignores unknown keys without complaint, so a secret put there by mistake wouldn't even cause an error. Secrets belong only in `~/.crux/`.

For the full contract, see `bionic/AGENTS.md` §14 in your project.

---

## Where to look first

In a project that uses crux, read these in order:

1. **`bionic/AGENTS.md`**: the operational schema and the single source of truth for what lives where and who edits what. It runs to about 1,000 lines, so skim §1–§7 first.
2. **`bionic/index.md`**: a catalog of everything, with one section and a count per concern.
3. **`bionic/adrs/`**: start at the lowest-numbered ADR and read forward in order. This is the project's "why".
4. **`bionic/journal/`**: the most recent month shows what's happening now.
5. **`bionic/research/sources.md`**: the registry of external sources the project draws on.
6. **`bionic/promptbooks/index.md`**: the work currently in progress.

---

## What you should NEVER do

- ❌ **Edit anything in `bionic/code/`.** Every extract run deletes hand edits.
- ❌ **Edit an ADR body after it's `Accepted`.** Write a new ADR that supersedes it.
- ❌ **Reorder `bionic/log.md` or edit past entries.** It's an append-only audit history.
- ❌ **Delete `bionic/research/raw/`.** The old captures form the audit chain.
- ❌ **Reuse an ADR or promptbook number.** Numbers only ever increase.
- ❌ **Edit rows in `bionic/research/sources.md` by hand.** Let `ingest-research` and `audit-docs` maintain it.

If something looks wrong, such as a contradiction, a stale page, or a missing source, say so instead of fixing it quietly. `audit-docs` catches drift, and your sense that something looks off is the main trigger for running it.

---

## What you SHOULD do by hand

- Write the `bionic/briefs/BRIEF-<slug>.md` files. These are *your* explorations before a decision. Claude tracks them but doesn't write them.
- Co-write the `## Goal`, `## Strategy`, and `## Prompts` sections of an active promptbook.
- Edit the repo-root `AGENTS.md`, if you keep one, to add project-specific notes for your agents. See below.

`init-docs` never creates a repo-root `AGENTS.md`.
- **If the file exists**, `init-docs` appends two lines when they're missing: ``See `bionic/AGENTS.md` for documentation operations.``, and an instruction to read `bionic/objectives.md`. Keep both when you edit the file. The `See` line is plain text, not an include.
- **If the file doesn't exist**, the `init-docs` summary warns you and suggests both lines. Whether to create the file is your call.
- **If you also have a legacy instruction file**, run `audit-docs --migrate` before adding a repo-root `AGENTS.md`. It converts tracked `CLAUDE.md` files to `AGENTS.md`.

---

## Day-one quick start

You're in a repo where `bionic/` has just been initialized. To start using it:

1. **Record today's intent as an ADR.** Say *"Propose an ADR explaining why we're using crux for this project."* Review it, then say *"Accept ADR-NNNN"*, using the number Claude assigned.
2. **Bring in your planning material.** Drop your existing design notes, specs, and chat exports into `bionic/inbox/` and say *"Process inbox."* Claude classifies each item and sends the research items through `ingest-research`.
3. **Plan the first piece of work.** Say *"New promptbook for <thing>."* Write the prompt list together with Claude, then say *"Run it."*
4. **Journal at the end of the day.** Say *"Log today's work: `<one-line summary>`."*
5. **Audit after the first ten writes.** Say *"Audit docs"* and confirm there's no drift.

---

## When things go wrong

| Symptom | Try this |
|---|---|
| "Where did Claude put X?" | Look at `bionic/index.md` and `bionic/<concern>/index.md`. |
| `bionic/code/` has stale content | Say *"extract code docs"*. It regenerates everything. |
| An ADR was accepted but it's wrong | Don't edit it. Propose a new ADR, then supersede the old one with it (`transition-adr`). |
| A research synthesis page contradicts itself | Say *"refresh synthesis"*, and Claude walks you through reconciling it. |
| You've lost track of a promptbook's progress | `bionic/promptbooks/index.md` shows the current run and percent complete. |
| The whole `bionic/` tree feels broken | Say *"audit docs"*. It runs the full set of integrity checks across all concerns. |

---

## Plugin and schema

crux maintains the documentation tree at `schema_version 5`, which uses the `bionic/` layout. The plugin itself lives at its installed root. In Claude Code that's `${CLAUDE_PLUGIN_ROOT}`; on any host, find it as `CRUX_PLUGIN_ROOT` as described in [Plugin paths in this guide](#plugin-paths-in-this-guide).

**Installing or upgrading:**
- **Claude Code:** `/plugin marketplace add bionic-coding/crux`, then `/plugin install crux@crux`.
- **Codex:** `codex plugin marketplace add bionic-coding/crux`, then `codex plugin add crux@crux`.
- Codex users can install the ten Crux role agents for themselves with the `install-codex-agents` skill.

**Upgrading from a release before 3.19.0:** say *"audit docs --migrate"*, even if `schema_version` already reads `"5"`.

What the migration does:
- It converts tracked `CLAUDE.md` files to `AGENTS.md`.
- Where both files exist at the same level, it keeps every block that appears in only one file. It removes a block only when it exactly duplicates another under the same heading path.
- It reports untracked and private files that block the conversion, and leaves them unchanged.

When the migration can't merge automatically:
1. This happens when headings conflict, or a block can't keep its heading hierarchy. The migration then keeps both source files and writes `.instruction-migration-preview.md`.
2. Reconcile each named block in a JSON resolution file. Copy the `source_hashes` into it from `.instruction-migration-receipt.json`.
3. Say *"audit docs --migrate using the resolution file at `<path>`"*.

### Recovering older trees and Markdown promptbooks

The current plugin works only on schema-5 trees and runs only YAML promptbooks. A schema-2, schema-3, or schema-4 tree has to go through the public `v3.23.2` release first. The steps below cover:
- getting and verifying that release;
- finishing Markdown promptbook runs;
- isolating each host so that only the tagged plugin is active.

#### Get and verify the recovery release

Work on a copy or backup of your project. Verify the release's annotated tag and commit before using its schema upgrade steps:

```bash
recovery_dir="$(mktemp -d)"
git clone --branch v3.23.2 --single-branch https://github.com/bionic-coding/crux.git "$recovery_dir/crux"
git -C "$recovery_dir/crux" rev-parse refs/tags/v3.23.2
git -C "$recovery_dir/crux" rev-parse HEAD
```

The first command must print `c1298c4a9229ed41ae7017c25321d27e5b3f6e4d`, and the second must print `08ee30ec2f1d1b4b0ce970f2e1582bb4f83cd20d`.

Then read the tagged release's `audit-docs` skill at `$recovery_dir/crux/crux/skills/audit-docs/SKILL.md`. Apply its upgrade steps in order: 2→3, then 3→4, then 4→5.
- If a valid `.migrating` marker is present, follow the resume or abandon procedure it records.
- If the marker is invalid, or there are two trees and it's unclear which is which, investigate before continuing.

The current plugin doesn't run these upgrade steps. Its `audit-docs --migrate` only handles instruction files on a schema-5 tree.

#### Markdown promptbook runs

**If a run can honestly be finished**, the tagged release can finish it:
1. Archive the run in the tagged release.
2. Convert the book, then its run, with that release's `migrate-promptbooks` skill. The skill keeps the Markdown originals.
3. Validate the YAML files and their content-hash binding before switching back to the current plugin.

**If a run can't be finished**, the tagged release has no way to abandon it on purpose.
- Keep its files unchanged, as readable history of a stranded run.
- Continue any separate work in new YAML books.
- Don't mark the run complete, don't skip its unfinished prompts to force a migration, and don't convert it in place.

#### Isolate the recovery environment

Use a separate copy of the project for recovery. Before starting any host, inspect the copy's project-level Crux registrations and disable only the current Crux version there:

| Host | Where project-level Crux registrations live |
|---|---|
| Claude Code | Project settings and `.claude/skills/` |
| Codex | `.agents/plugins/marketplace.json`, `.agents/skills/`, and `.codex/config.toml` |
| OpenCode | The project's `opencode.json`, `.opencode/skills/`, and `.opencode/skill/` |

- Leave unrelated entries and the original project unchanged.
- OpenCode merges a project's `skills` arrays with your XDG settings. An isolated XDG directory alone therefore does not remove a current project skill path.
- If you can't confirm that only the tagged Crux skills are active, stop before changing the copy.

Use only the tagged plugin during recovery. The sections below explain how on each host.

#### Claude Code

1. Disable the installed Crux plugin in the scope where it's installed: `claude plugin disable crux@crux`.
2. Start a separate session with `claude --plugin-dir "$recovery_dir/crux/crux"`. The `--plugin-dir` flag adds that plugin source for the session only.
3. Check that the current plugin is disabled.
4. After recovery, run `claude plugin enable crux@crux` and restart.

#### Codex

Use an isolated Codex home so your normal plugin installation isn't present. The tagged checkout contains a local marketplace named `crux` whose source is `./crux`. Codex's local-marketplace command accepts a directory path:

```bash
mkdir -p "$recovery_dir/codex-home"
CODEX_HOME="$recovery_dir/codex-home" codex plugin marketplace add "$recovery_dir/crux"
CODEX_HOME="$recovery_dir/codex-home" codex plugin add crux@crux
```

1. Start the recovery Codex session with the same `CODEX_HOME`, in a project copy that has no other project-scoped Crux plugin.
2. Check that the tagged skill is available before changing anything.
3. When you're done, end the session and go back to your normal Codex home to use the current plugin again.

[Codex's local-marketplace instructions](https://developers.openai.com/plugins/build/plugins) explain the path form. These commands were checked against the Codex CLI help. They have not been tested in an actual fresh-session recovery.

#### OpenCode

Use an isolated XDG configuration for a separate recovery session.

1. Create the file `$recovery_dir/opencode-config/opencode/opencode.json` with the content below. Replace `TAGGED_CHECKOUT` with the absolute path of `$recovery_dir/crux`.

   ```json
   {"skills": ["TAGGED_CHECKOUT/crux/skills"]}
   ```

2. Create the directories and start OpenCode with isolated paths:

   ```bash
   mkdir -p "$recovery_dir/opencode-config/opencode" "$recovery_dir/opencode-data" "$recovery_dir/opencode-cache"
   XDG_CONFIG_HOME="$recovery_dir/opencode-config" XDG_DATA_HOME="$recovery_dir/opencode-data" XDG_CACHE_HOME="$recovery_dir/opencode-cache" opencode
   ```

3. Check that only the tagged Crux skills load.
4. After recovery, quit OpenCode and go back to your normal XDG settings.

This setup follows crux's OpenCode `skills` array contract.

#### Verification status

Recovery in a fresh session hasn't been verified in Claude Code, Codex, or OpenCode. On every host, confirm which skills are active before changing anything.
