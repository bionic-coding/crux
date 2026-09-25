<!-- generated-from: README.md@sha256:9d840bc109df81244417572a09813aff8b7924faa1fd5b6d168abe63b8681ad6; model: claude-opus-5.5; date: 2026-09-25 -->
# Crux

An Agentic Harness plugin that maintains a `./bionic/` tree inside any software project, so that Claude can navigate, query, and update project knowledge without anyone having to remember where things go. Everything runs locally: no server, no accounts, no background service. Just skills, scripts, and your repo.

## Start here

Visit the [Crux guide](https://bionic-coding.com/crux/) for installation and usage instructions.

## Install

crux installs through Claude Code's plugin marketplace. In any Claude Code session, run two slash commands:

```
/plugin marketplace add bionic-coding/crux
/plugin install crux@crux
```

Restart the session, then say **"init docs"**. Codex and OpenCode instructions, requirements, and configuration are [further down](#installing-in-claude-code-in-detail).

## About this repository

This repository is **generated** from a private development repo on every release (see [`.generated`](./.generated)). Each release is one squash commit. Please **file issues** here. Pull requests can't be merged, because the next release would overwrite them.

---

## What you get

**60 skills** across seven concerns. On top of those, crux adds a default-on, derived **arch** surface (the current-state architecture map, built on demand by `derive-arch`) and the default-on **observations** concern (what the code already does, evidenced and ratified rather than decided). It also adds a **10-agent operator layer** (see [Agents](#agents--the-role-layer) below). Everything follows one naming convention, with no `crux-` prefix.

`crux/catalog/bundles.yml` records the bundle organization: docs suite, core agent-team, verification, infrastructure.

| Concern | What lives there | Who writes it |
|---|---|---|
| `bionic/code/` | Auto-extracted from source docstrings (`@moduledoc`, JSDoc, etc.) | Regenerated — never hand-edit |
| `bionic/research/` | Articles, papers, URLs, meeting notes, chat exports | You drop sources; Claude ingests |
| `bionic/adrs/` | Architecture Decision Records — the "why" of every load-bearing decision | You decide; Claude writes. Frozen once Accepted |
| `bionic/briefs/` | Pre-decision exploration documents | You author; Claude tracks |
| `bionic/journal/` | Day-by-day record of work performed | Claude appends; you ask |
| `bionic/promptbooks/` | Plans of prompts with immutable run snapshots | Co-authored |
| `bionic/invariants/` | Pinned, executable statements of what must stay true, each backed by a real check | Machine proposes; **you ratify** |
| `bionic/observations/` | Records of what the code already does, each evidenced by a `path:line-range` — described, not decided | You write via `propose-observation`; **you ratify**. No scan writes one |
| `bionic/arch/` | Derived architecture spine — the current-state map (data model, interface surface, module graph, decision index) | Regenerated on demand by `derive-arch`; default-on for new repos, never hand-edited |

**You curate, decide, and discuss. Claude does the bookkeeping.**

**To learn how a project is shaped right now**, start with `bionic/arch/`, the derived current-state map.
- ADRs are the secondary path: they record the *why* behind each decision.
- The librarian and historian agents fill whatever those two don't cover.
- New repos get arch by default, because `init-docs` enrolls it. Say **"build the arch"** to derive the spine.
- Keep it current with `derive-arch`, or let `audit-docs` regenerate it automatically when it drifts.
- An existing tree created before arch was the default must opt in first (add `arch` to `concerns_enabled`), then derive.

**To learn what a project currently holds to be true**, and whether that belief is live or only on paper, start with `bionic/adrs/doctrine/` instead.
- Doctrine is a derived, per-domain, plain-language view. It is compiled from the ADR summaries and reconciled against ratified invariants.
- Doctrine holds zero authority. When it disagrees with an ADR body, the ADR body is the record and wins.
- The two views answer different questions: arch says what exists, doctrine says what's currently believed.

**Where the rest is documented:**
- The full mental model and conventions are in [USER_GUIDE.md](./USER_GUIDE.md).
- The operational schema Claude follows is `bionic/AGENTS.md`, created on first run.
- The tree's location is recorded in `.bionic.yml`. An existing `docs/` tree keeps working unchanged.

---

## The cycle — crux's primary workflow

A **cycle** is one trip around crux's development loop for a single feature or change. Most of your time inside crux happens here. Once the tree is bootstrapped, you stop splitting the day into "write some code, then update some docs". You start a cycle instead:

> **"Start a cycle for &lt;feature&gt;. The goal is &lt;one paragraph&gt;."**

Claude allocates the next `PB-NNNN` and assembles a promptbook from modular building blocks. You drive it forward with **"advance"** / **"next"**. A cycle has three module types, each appearing once or many times depending on the work. A fixed prep step and a fixed summary step close every cycle:

| Module | Prompts per instance | What it does |
|---|---|---|
| **ADR module** | 4 | Planning agents draft an ADR; a 4-agent LLM council reviews it (completeness, correctness, consistency, clarity); iterate until consensus, then accept the ADR |
| **Dev module** | 4 | Derive an implementation plan from the accepted ADRs; spawn implementer agents; run quality gates; internal code review |
| **Review module** | 3 | External multi-dimension review + test/comment/doc audit + apply feedback (loop until zero MUST-FIX) |
| **Prep (fixed)** | 1 | Changelog entry, docs updates, journal entry, PR notes |
| **Summary (fixed)** | 1 | Completion report (stats, key decisions, links) **and archival** — the cycle ends with `archive-promptbook` so finished books don't straggle in `active/` |

`total_prompts = 4·(ADRs) + 4·(dev loops) + 3·(review cycles) + 2`. The **minimum cycle** is 1 + 1 + 1 → **13 prompts**, matching the canonical `cycle-promptbook-template.yaml`. Bigger cycles are valid when the work needs them:
- two ADRs for a feature with two distinct architectural commitments;
- two dev loops when the implementation splits cleanly (backend + UI, schema + migration);
- an extra review cycle in the middle of a multi-loop dev phase.

**Three invariants every cycle MUST satisfy:**

1. `total_prompts ≥ 13`. No shorter cycles. If you want a quick fix, use `author-promptbook` instead.
2. Every proposed ADR has a paired council-approval prompt. You cannot create an ADR without sending it through the 4-agent council.
3. Every artifact produced has a review cycle that closes its MUST-FIX findings. Internal review (in the dev module) and external review (in the review module) are both required. Neither can be skipped.

Each module has a built-in 3-round escalation. If a loop doesn't converge after three tries, the runner stops and surfaces the stuck decision to you. There is no endless agent ping-pong.

**Why most of your time goes here:** a cycle bundles ADR creation, multi-agent planning, implementation, review, and PR prep into one tracked artifact. That turns crux from "a docs folder" into "an opinionated way to ship a change with the receipts attached."

**When NOT to use cycle:**

- One-off bug fixes that don't warrant an ADR. Just make the fix and `log-work` the outcome.
- Non-feature multi-step plans. Use `author-promptbook` instead: there's no canned body, and you write the prompts.

---

## Agents — the role layer

crux bundles a **role-based agent layer**: **ten** Claude Code subagents that *operate* the skills. Each agent carries a `tools` allowlist that **structurally enforces** what it may and may not do. Separation of duties comes from tooling, not from instructions.

| Agent | Role | Structurally cannot |
|---|---|---|
| **commander** | Conductor — drives a promptbook/cycle run; delegates every unit of work | edit code or docs (delegates only) |
| **brainstormer** | Docs-aware design exploration; drives the `whiteboarding` skill | write files (returns a session the historian files) or edit code |
| **architect** | Owns ADRs/decisions (`propose-adr`, `council`, `transition-adr`) | implement code |
| **dev-lead** | Lead implementer; the one agent that fans out to `developer`s | merge/push (human-gated) |
| **developer** | Implements one scoped unit, test-first | re-delegate; write docs/ADRs |
| **reviewer** | Independent code review + verification | edit files (reviews; never fix-and-hide) |
| **historian** | Owns *all* `docs/` writes — setup, maintenance, intake, preservation | edit source code |
| **librarian** | Read-only retrieval from `docs/` (`query-docs`) | write anything |
| **night-gardener** | Overnight visionary/coach/co-CTO — reviews recent work, writes a morning note under `docs/garden/` (ideas, gaps, research, news) | push/merge, send externally, or self-install the routine |
| **wayfinder** | Read-only reconnaissance — reads large/uncertain or external data ahead of the caller, judges fitness, returns a verdict + condensed digest so the primary spends its context only on proven-fit content | write, execute, delegate, or relay local content outbound |

Two design choices make the layer portable and safe:
- **Agents are self-contained.** The craft disciplines are embedded in each agent's prompt rather than depending on separately installed skills. These are TDD with its proof mechanism, verification-before-completion, systematic debugging, and two-stage review.
- **Agents are first-class catalog citizens.** Agent frontmatter is regenerated into `catalog/agents.json` exactly like skills, with an `agents:` array in `plugin.json`.

The agents register once you install or upgrade the plugin and restart the session.

Codex installs the same ten roles as namespaced `crux_*` agents:
- Each installed role pins its catalog model and reasoning effort.
- Each role binds every declared skill to the selected Crux plugin.
- Codex runtime verification stays `unverified` until fresh-session host evidence confirms four things for that client version: discovery, settings, skill availability, and representative workflows.

---

## Skills — what each does, and when to reach for it

You never type a slash command. Each skill is triggered by natural-language phrases routed through its `description`. The 60 skills are grouped below by what you're trying to do. The **say this** column shows a representative trigger, not the full list.

### Getting set up
| Skill | Say this / when | What it does |
|---|---|---|
| `init-docs` | "init docs" — first run in a repo | Bootstraps the seven-concern `bionic/` tree plus the default-on arch spine + `bionic/AGENTS.md` + `manifest.yml` + the meta-ADR. |
| `install-docs-skills` | "install docs skills" / "upgrade the docs suite" / "what version is installed?" | Reports the installed plugin version + manifest and prints the marketplace install/upgrade commands. |
| `install-runtime` | "install the crux runtime" | Deploys the runtime (scripts + LLM router) into a target repo. |
| `install-codex-agents` | "install the Crux agents in Codex" / "refresh Codex agents" — Codex users only | Installs or refreshes the ten generated Crux roles in `~/.codex/agents/` by default. `--repo-root` selects one project. `--check` reports canonical expectations, parsed installed state, drift, shadows, and runtime status. |
| `install-opencode-agents` | "install the Crux agents in OpenCode" / "refresh OpenCode agents" — OpenCode users only | Installs or refreshes the ten generated Crux role agents into a target repo's `.opencode/agents/`; no-clobber (`--force` required to overwrite a modified role). |

### Code docs (regenerated from source — never hand-edited)
| Skill | Say this / when | What it does |
|---|---|---|
| `extract-code-docs` | "extract code docs" / pre-push hook | Regenerates `docs/code/` from source docstrings (`@moduledoc`, TSDoc, …). |
| `verify-code-docs` | "verify code docs" / before merge | Read-only drift check — reports staleness without writing. |

### Architecture (derived current-state map — default-on for new repos)
| Skill | Say this / when | What it does |
|---|---|---|
| `derive-arch` | "build the arch" / "summarize the current architecture" / "regenerate the architecture" | Regenerates `docs/arch/` — the derived spine (data model, interface surface, module graph, decision index) plus a synthesized overview — wholesale from the project's own sources. Detects the repo's stack and derives a real spine with batteries-included packs for Python, Ruby, Node.js, and Elixir/Phoenix (an unsupported stack degrades to an empty-but-valid spine). `--dry-run` is the drift check. The primary current-state discovery surface. |
| `escalate-arch-runtime` | "escalate the arch runtime" / "recover the routes by running my app" — Python only, human-invoked only | Recovers what a static extractor missed (the route table, the ORM schema) by running your FastAPI/Flask/Django app's import-time code in a subprocess-isolated child behind the two-factor `CRUX_ARCH_ALLOW_RUNTIME=1` consent gate. The advisory lands in `docs/inbox/`, never in `docs/arch/`. |

### Research wiki
| Skill | Say this / when | What it does |
|---|---|---|
| `process-inbox` | drop anything in `docs/inbox/` → "process inbox" | Classifies each dropped item and routes it to the owning skill. |
| `ingest-research` | "ingest this" / paste a URL | Captures a source into an immutable dated `raw/` copy + an audited page. |
| `refresh-research-sources` | "refresh sources" | Re-fetches non-static source URLs; flags affected synthesis pages. |
| `read-news` | "read the news" / "what's new in the ecosystem" | Perplexity-backed reading pass over curated sources; keepers land in the inbox, stale wiki sources get refreshed. |
| `refresh-research-synthesis` | "refresh synthesis" | Walks accumulated contradiction / source-updated markers per page. |

### Decisions — ADRs & briefs
| Skill | Say this / when | What it does |
|---|---|---|
| `propose-adr` | "propose an ADR for X" | Allocates the next `ADR-NNNN` and writes it `Proposed` (never auto-accepts). |
| `transition-adr` | "accept / deprecate / supersede ADR-NNNN" | Runs the ADR state machine; writes both ends of a supersession (supersede/deprecate moves the ADR to the cold `adrs/archive/` tier). |
| `recover-decisions` | "recover decisions" / "mine decisions from the code" | Machine pass: mines code for load-bearing decisions that have no ADR, writes `observed` candidates — never authors an ADR. |
| `transition-decision` | "ratify / reject / defer decision <id>" | The human gate: ratifies a recovered candidate into a `Proposed` ADR (idempotent), or rejects/defers it. |
| `review-decisions` | "review the decisions" / "run a decision review" / "is the decision set still right" | Periodic architect review of the accepted decision set against `docs/objectives.md`: reads mechanical signals, writes a dated report under `docs/adrs/reviews/`, and proposes findings — it transitions nothing. |
| `link-adr-graph` | "show ADR lineage" / "what supersedes what" | Regenerates `docs/adrs/lineage.md` (Mermaid graph + table). |
| `whiteboarding` | "brainstorm" / "let's explore X" / "whiteboard this" | Pre-decision design dialogue; produces a session the historian files as a brief and the architect turns into an ADR. |
| `transition-brief` | "publish brief" / "abandon brief" | Closes the brief lifecycle (`draft → published \| abandoned`); frontmatter only, never the body. |
| `propose-brief` | "draft a brief for X" / "explore X before deciding" | Scaffolds a pre-decision exploration doc (you write the body). |
| `backfill-signoff` | "sign off backfill batch <id>" / "backfill sign-off" / "sign the backfill" | The single owner write path for a governs backfill batch: renders every enumerated receipt's rule and anchor verbatim for your read, validates fail-closed, then writes the four surfaces (signed-date flip, admission ledger, log op, journal hook) plus the completion marker when the cohort arithmetic holds. Idempotent. |
| `compile-doctrine` | "compile the doctrine" / "is the doctrine current" / "doctrine drift" | Regenerates `docs/adrs/doctrine/` — the per-domain view of current belief — wholesale from the summaries projection, reconciled against the ratified invariants and the human-signed reconciliation ledger. `--dry-run` is the drift check. Never writes the reconciliation ledger. |
| `reconcile-signoff` | "sign off the reconciliation" / "reconcile INV-NNNN with ADR-NNNN" / "mark the collision between" | The single human write path for one doctrine reconciliation: renders the invariant text and the rule text, takes your verdict (compatible / reconciled / collision) and rationale, then upserts a digest-bound record and re-compiles doctrine on your confirmation. Never chooses a verdict for you; never batch-signs. |

### Work journal
| Skill | Say this / when | What it does |
|---|---|---|
| `log-work` | "log work" / "journal this" / end of day | Appends a reflective entry to `docs/journal/YYYY-MM.md`. |

### Promptbooks & cycles — the workflow core
| Skill | Say this / when | What it does |
|---|---|---|
| `dev-cycle` | "start a cycle for X" — **net-new / architectural** | Assembles an ADR + dev + review cycle book (≥13 prompts). |
| `iterate` | "iterate on X" / "remediate X" — **non-architectural fix** | Same rigor, but a **verify** module (council-reviewed diagnosis) instead of an ADR. |
| `patch-cycle` | "patch this" — a **small reversible** fix that still needs the gates | Five phases (verify, plan, implement, review, summary), one prompt each. Declares a blast radius that the council reviews for proportion and the archive checks against the paths the run changed. |
| `fix-directly` | "just fix it" — a defect whose files, failing test, and unchanged contracts you can name now | No book, no council, no PB number. A failing test first, the smallest green change, the suite and the drift gates, one commit, one `log-work` entry. Escalates to `patch-cycle` / `iterate` / `dev-cycle` when its sizing test says no. |
| `author-promptbook` | "new promptbook" — a custom plan, no enforced rigor | A bespoke multi-prompt book you co-author. |
| `run-promptbook` | "run it" / "advance" / "next prompt" / "abandon this run" | Starts / advances a run snapshot against a book, or records a deliberate abandonment. |
| `archive-promptbook` | "archive promptbook" — the run completed, or was deliberately abandoned | Moves a finished book to `archive/` with an archive note. |
| `migrate-promptbooks` | "migrate promptbooks" | Converts legacy `.md` books/runs to structured `.yaml`. |
| `visualize-run-progress` | "show run progress" / "how far along is PB-NNNN" / "where am I on PB-NNNN" / "resume my cycle" | Read-only. Renders a run as a progress bar + per-prompt checklist, and answers "where am I?" — current prompt, next prompt, the resume command. |

> **Which workflow skill?**
> - *Net-new or architectural work* → `dev-cycle`.
> - *Fixing or refining something that exists* → `iterate`. Use `patch-cycle` instead when the fix is small and reversible, and you can honestly name its file footprint before starting.
> - *A defect whose fix you can name before starting* → `fix-directly`, with no book at all.
> - *A bespoke sequence that doesn't need council + review* → `author-promptbook`.

### Invariants (pinned, executable truth — machine proposes, human ratifies)
| Skill | Say this / when | What it does |
|---|---|---|
| `recover-invariants` | "recover invariants" / "mine invariants" | Machine pass: mines code for candidate invariants, writes `observed` ledger stubs + candidate checks — never ratifies. |
| `transition-invariant` | "ratify invariant INV-NNNN" / "reject" / "retire" | The human gate: `observed → ratified \| rejected`, `ratified → retired`. Recovery cannot self-ratify. |

### Observations (what the code already does — machine proposes, human ratifies)
| Skill | Say this / when | What it does |
|---|---|---|
| `propose-observation` | "propose observation" / "record what the code does" / "this is observed not decided" | Scaffolds an `OBS-NNNN` record in `observed` with `provenance: reconstructed` (you write the body). Evidence is a `path:line-range`, never a code excerpt. |
| `transition-observation` | "ratify observation OBS-NNNN" / "reject" / "retire" / "mark decided" | The human gate: `observed → ratified \| rejected`, `ratified → retired \| decided`. No scan or scaffold sets a state past `observed`. |
| `survey-sheet` | "scaffold a survey sheet" / "start a batch review of observations" — the machine half | Scaffolds one `SVY-NNNN` batch review sheet from the observed candidates, seeding `anchor_id` and `proposed_domain` per row and leaving `verdict`, `domain` and `rationale` empty for you to author. Fills no human cell, ratifies nothing, writes no record. One live sheet at a time. |
| `survey-signoff` | "sign off the survey" / "sign off SVY-NNNN" / "publish the batch" | The single human write path for one filled-in review sheet: renders every claim and verdict, refuses an empty verdict or a sheet edited since it was signed, then publishes the batch under one digest-bound receipt on your confirmation. Equivalent to N ratifications under one signature, and the only batch route past `observed`. |

### Health & questions
| Skill | Say this / when | What it does |
|---|---|---|
| `audit-docs` | "audit docs" / before a release | ~97 integrity checks across all concerns; auto-fixes safe drift. |
| `check-drift` | "check drift" / "is the tree in sync" / "pre-release drift check" | Runs every enrolled regenerator's `--dry-run` gate read-only and reports one table of gate / verdict / drifted paths / the regenerator that fixes it. Never regenerates — the whole-tree counterpart to `verify-code-docs`. |
| `cleanup-campsite` | "what's next" / "cleanup" | Forward-looking process-state scan → regenerates `docs/whats_next.md`. |
| `query-docs` | "what does X do?" / "why did we choose Y?" | Index-first search of `docs/` with cited answers. |
| `prose-review` | "review this writing" / "does this follow our writing rules?" | Checks text against the seven writing rules and returns a concrete rewrite for every finding. |

### Multi-model & agent-team substrate
These skills power the council and the agent layer. You mostly invoke them indirectly: a cycle's ADR module calls `council`, and a split verdict calls `srde`.

| Skill | Say this / when | What it does |
|---|---|---|
| `council` | "ask the council" / choosing between approaches | Multi-model deliberation (Claude + Gemini + GPT). |
| `run-adr-council` | "run the council on ADR-NNNN" / "council review ADR-NNNN" | Parameterized ADR council runner: reads the ADR, fences its body as data, invokes the async council, returns a structured verdict — no per-ADR driver. |
| `srde` | after a split council verdict | Self-Resolving Dissent Engine — resolves disagreements without a human. |
| `task-planner` | "plan this feature" | Decomposes a goal into ordered, independently-testable tasks. |
| `agent-identity` | session start / capturing learnings | Cross-agent identity + learning capture. |
| `semantic-bridge` | multi-agent runs | Shares probes / dissents / resolutions across teammates. |
| `trace-runtime-ops` | debugging an agent run | Structured tracing + logging of crux operations. |
| `forge-skill` | a capability you lack mid-task | RSI (recursive self-intelligence) capability-gap loop: diagnose → research → author a project-local skill in `.claude/skills/`, autonomous with gates. |
| `tend-garden` | "tend the garden" / "night pass" / overnight sessions | The night-gardener's pass: reviews recent moves, reads diagnostics + news, writes a morning note under `docs/garden/`. |
| `retrospective` | "what should we learn from recent work" | Purposeful reflection: mines logs/journal/runs, harvests ≤2 council-gated skill proposals, builds them via forge-skill. |
| `call-llm` | programmatic single-model calls | Multi-provider LLM caller (Claude / Gemini / GPT). |
| `author-runbook` | "generate a runbook for X" | Builds a 50–100-prompt autonomous runbook from one goal. |
| `serve-llm` | non-Python clients | FastAPI HTTP wrapper around the LLM caller + tracer. |

**Reaching for an agent directly:** you rarely name an agent, because the cycle and the `commander` dispatch them for you (see [Agents](#agents--the-role-layer) above). But you can: *"have the architect propose an ADR for X"*, *"send this design to the council"*, *"have the reviewer check the diff"*, *"ask the librarian what we decided about Y"*.

---

## Installing in Claude Code in detail

crux installs through Claude Code's plugin marketplace. In any Claude Code session, run two slash commands:

```
/plugin marketplace add bionic-coding/crux
/plugin install crux@crux
```

That's the whole flow. The second command installs the plugin named `crux` from the marketplace you just added, which is also named `crux`.
- **Upgrading** works the same way: run `/plugin marketplace update crux`, then re-run `/plugin install crux@crux` to pick up a new version.
- **Your files:** installation does **not** touch your `./docs/` folder. You bootstrap the tree yourself.

Restart the session so the plugin's skills and agents register, then say:

> **init docs**

That bootstraps the seven-concern `bionic/` tree plus the default-on arch spine. It also seeds three files:
- `bionic/AGENTS.md`, the operational schema the three supported harnesses share;
- `bionic/manifest.yml`;
- the meta-ADR `ADR-0000`.

## Installing in Codex and OpenCode

### Codex

See [CODEX.md](./CODEX.md) for complete installation instructions for humans
and agents.

crux is also a supported Codex distribution target. The same ten roles are
generated from `crux/agents/` as Codex-native `.codex/agents/*.toml` files.
Install the plugin through Codex's marketplace flow:

```
codex plugin marketplace add bionic-coding/crux
codex plugin add crux@crux
```

Start a new Codex thread, then say **"install the Crux agents in Codex"**. The
`install-codex-agents` skill writes the namespaced `crux_*` roles to
`~/.codex/agents/` by default. Each role pins its model and reasoning effort and
binds its declared skills to the installed plugin. Pass `--repo-root` only when
you want one project's `.codex/agents/` directory.

The installer does not replace changed or stale managed files without
`--force`. An unchanged refresh is a no-op. Plugin relocation appears as drift
because installed skill bindings use absolute paths. Run `--check` with
`--project-context` to inspect drift and project agents that shadow personal
roles. The static report separates canonical expectations from the managed TOML
state parsed from disk. It keeps runtime status `unverified` until fresh-session
host evidence confirms the effective Codex configuration. Parent permissions,
credentials, sandbox policy, eager skill loading, and delegation depth remain
Codex host constraints.

### OpenCode (manual setup)

See [OPENCODE.md](./OPENCODE.md) for complete machine-wide and project
installation instructions for humans and agents.

There is **no native Crux OpenCode marketplace package yet**. OpenCode support is a **manual, preview-grade setup** for now; a public OpenCode distribution channel is a deliberately deferred future decision. The steps below wire the full 60-skill + 10-agent set into OpenCode 2.x from a public clone, and work from the published repo — no dev checkout required. Install OpenCode 2.x with `curl -fsSL https://opencode.ai/v2/install | bash`, which leaves a binary named `opencode`.

1. **Clone to a stable path** (the config below uses absolute paths, so pick a permanent home — moving it later breaks the setup):

   ```bash
   git clone https://github.com/bionic-coding/crux ~/.local/share/crux
   ```

2. **Install [uv](https://docs.astral.sh/uv/)** (needed to run the agent generator):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Generate the OpenCode agent tree** (`opencode/agents/*.md` is a regenerated projection of `crux/agents/`, produced on demand — the public artifact does not ship it):

   ```bash
   cd ~/.local/share/crux
   uv run python3 crux/scripts/generate-opencode-agents.py
   ```

4. **Point OpenCode's skill scanner at the clone.** Merge this into `~/.config/opencode/opencode.json` (create it if absent), using the **absolute** path to `<clone>/crux/skills`:

   ```json
   {
     "$schema": "https://opencode.ai/config.json",
     "skills": ["/Users/you/.local/share/crux/crux/skills"]
   }
   ```

   V2 reads `skills` as an array of directories; V1's `{"paths": [...]}` object is the same setting in its earlier form. Entries from every config document merge, and a relative entry resolves against OpenCode's working directory — which is why this one is absolute.

5. **Symlink every generated agent** into `~/.config/opencode/agents/` (OpenCode has no `paths` escape hatch for agents — the files must physically exist there). The glob catches all ten roles — `wayfinder` and any future role — automatically. Symlinks, not copies, so a later regenerate needs no re-symlink:

   ```bash
   mkdir -p ~/.config/opencode/agents
   for f in ~/.local/share/crux/opencode/agents/*.md; do
     ln -sf "$f" ~/.config/opencode/agents/"$(basename "$f")"
   done
   ```

   Leave the legacy singular `~/.config/opencode/agent/` empty. In the project-local pair, the plural directory wins with no warning; the global pair was not measured. Populating both therefore leaves you guessing which copy is live. Upgrading from a release that installed into the singular directory leaves ten symlinks there — prune them:

   ```bash
   rm -f ~/.config/opencode/agent/{architect,brainstormer,commander,dev-lead,developer,historian,librarian,night-gardener,reviewer,wayfinder}.md
   ```

   > **These symlinks expose a V2-only projection — run the roles with a 2.x runner.** The generated files carry V2's `permissions` array. A runner older than 2 does not read that key, so it loads each role with every `deny` dropped. The role then grants what the file meant to refuse. Nothing warns you: the file parses, the role appears, and the restriction is gone. Check the version, not the name. Release 2.0.3 installs as `opencode`, and an upgraded machine may keep an `opencode2` shim onto the same binary. Run `opencode --version` and read the major.

6. **Fully quit and restart the OpenCode host.** OpenCode loads config once at startup and does not hot-reload. For the **Zed / ACP** integration, restart Zed itself (or the ACP connection) — opening a new thread alone is **not** sufficient.

7. **Verify:**

   ```bash
   opencode debug agents   # should list the 10 Crux roles alongside the built-ins
   ```

   Until the background service has resolved the project, `debug agents` returns `[]` at exit 0 — re-run it rather than reading `[]` as a failure.

   V2 has no skill-listing command; `opencode debug` offers exactly `agents`, `config` and `paths`. Verify skills by asking for one instead — say *"what's next"* and expect `cleanup-campsite` to run.

> **Re-run step 3 after every `git pull`.** `opencode/agents/` is a generated projection that git does not track, so an upgrade updates its source (`crux/agents/`) and leaves the projection on the old content. Nothing errors — the symlinks still resolve, and OpenCode goes on loading the previous release's role definitions. Regenerate, then restart the host:
>
> ```bash
> cd ~/.local/share/crux && git pull && uv run python3 crux/scripts/generate-opencode-agents.py
> ```
>
> Skills need no equivalent step: the `skills` entry points at the tracked `crux/skills/`, so a pull updates them in place.

> Moving or deleting the clone breaks the absolute `skills` entry and every agent symlink — rerun this setup (re-clone, re-generate, re-symlink) if you relocate it.

**Per-project agents instead of machine-wide.** The steps above give every project on the machine the ten roles. To scope them to one repo, skip steps 3 and 5 and say **"install the Crux agents in OpenCode"** from that repo — the `install-opencode-agents` skill generates the same ten projected roles from `crux/agents/` and writes them into `.opencode/agents/`, refuses to overwrite a locally modified role without `--force`, and leaves the project's own agent files alone. A project-scoped role shadows a global one of the same name.

## Requirements

- [Claude Code](https://claude.ai/code) installed.
- `python3` 3.11 or newer on PATH, and [uv](https://docs.astral.sh/uv/).
  - Every script declares its dependencies in a PEP 723 header, so `uv run <script>` resolves them.
  - A bare `python3` runs only the stdlib-only scripts.
  - macOS ships 3.9 at `/usr/bin/python3`, which cannot parse this code.

### Optional: secrets management

If any of your workflows need API keys, crux ships a `crux-env` CLI. It keeps them in `~/.crux/env`: mode `0600`, outside any repo, never committed.

Invoke it via the installed plugin. `${CLAUDE_PLUGIN_ROOT}` is the plugin's install root and is set inside Claude Code sessions. In a plain terminal, substitute the plugin's install path. Alias the command if you use it often:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" init                       # one-time setup
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" set OPENROUTER_API_KEY ...  # store a key
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" check --project crux      # verify what a project needs
```

See [USER_GUIDE.md → "Working with secrets and API keys"](./USER_GUIDE.md#working-with-secrets-and-api-keys) for the full surface.

### Optional: per-project configuration

A repo can commit an optional `.bionic.yml` file at its root. It is distinct from the `~/.crux/` secrets directory, so never put secrets in it.

It takes a required `config_version: "1"` and two optional keys:
- `docs_dir` relocates the tree;
- `artifact_prefix` brands artifact ids with a prefix (`artifact_prefix: "CRX"` → `CRX-PB-0040`).

`.bionic.yml` supersedes the legacy `.crux` file, which is still read for back-compat. Copy `crux/templates/bionic-yml.tmpl` to get started, and see [USER_GUIDE.md → "Per-project configuration"](./USER_GUIDE.md#per-project-configuration-the-repo-root-bionicyml-file).

---

## Tips for using it

### 1. It's all natural language — no slash commands

Skills are triggered by phrases routed through each skill's description. Say what you mean, and Claude picks the right skill.

| Say this | …and Claude will |
|---|---|
| **"start a cycle for X"** | **Assemble the modular feature-delivery promptbook (≥13 prompts, see above). This is the main entry point.** |
| "advance" / "next prompt" | Move the active cycle (or any running promptbook) forward one prompt |
| "propose an ADR for X" | Allocate the next ADR number, draft a `Proposed` decision record |
| "accept ADR-0007" | Flip status to `Accepted` — body is now frozen forever |
| "process inbox" (after dropping anything in `docs/inbox/`) | Classify each dropped item + confirm + dispatch to the right skill (research → ingest, decision → ADR, exploration → brief, note → journal) |
| "log work — fixed the X bug" | Append a categorized entry to `docs/journal/YYYY-MM.md` |
| "new promptbook for X" | Scaffold a plan-of-prompts artifact you'll co-author (use this for non-cycle plans) |
| "run promptbook PB-0003" | Start an immutable run snapshot of that book |
| "extract code docs" | Regenerate `docs/code/` from your source's docstrings |
| "audit docs" | Run ~97 integrity checks across every enabled concern and auto-fix safe drift; `audit docs --migrate` upgrades an older docs tree |
| "what does X do?" / "why did we choose Y?" | Search `docs/`, return answers with citations |

### 2. Run `audit docs` regularly

Run it especially after large batches of writes, after a research refresh, or before a release. It catches dangling links, supersession asymmetries, missing index rows, and stale counters, and fixes the safe ones automatically.

One rule is mechanical rather than prose. The `## ADRs (N)` rollup in `docs/index.md` is a pure function of your ADR frontmatter, so `crux/scripts/generate-index-rollup.py` regenerates it (`--dry-run` reports drift, exit 1). Prefer running it over hand-fixing that section.

The other rollups are still checked by `audit-docs` reading them. That matters: a passing prose check tells you an agent believed it walked everything, not that it did.

### 3. The append-only stuff really is append-only

- **ADRs**: once Accepted, the body is immutable. To change a decision, write a new ADR that supersedes the old one (e.g. `"supersede ADR-0001 with ADR-0005"`). Claude updates both ends of the link atomically.
- **`docs/code/`**: regenerated on every extract run, so hand-edits are blown away. If a docstring is wrong, fix it in the source.
- **`docs/research/raw/`**: every fetched capture lives there forever, dated. Don't prune it. It's your audit chain when someone challenges a synthesis page.
- **`docs/journal/`**: a chronological narrative. Don't reorder past entries.

### 4. Capture anything by dropping it in the inbox

The fastest path to building a useful docs tree:

1. Drop a PDF, screenshot, markdown file, a stray decision note, or a half-formed idea into `docs/inbox/`.
2. Or paste URLs, one per line, into `docs/inbox/urls.md`.
3. Say **"process inbox"**. `process-inbox` classifies each item, shows you a confirmation batch, and dispatches each item to the right skill:
   - research → `ingest-research` → immutable `raw/` capture;
   - decision → `propose-adr`;
   - exploration → `propose-brief`;
   - note → `log-work`.

For research, Claude fetches the source and captures a dated raw copy. It writes an audited source page in `bionic/research/sources/` and offers to update synthesis pages where the content is relevant.

Later, say **"refresh sources"** to re-fetch URLs and mark synthesis pages affected by upstream changes.

### 5. Promptbooks are for multi-step work you'll repeat

Anything you'd otherwise paste into Claude as a long prompt-by-prompt sequence belongs in a promptbook. Each book has:

- A **mutable plan** (`active/PB-NNNN-<slug>.md`) you co-author.
- **Immutable run snapshots** (`runs/PB-NNNN-<slug>/run-RUN-NNN.md`), one per execution.

You can't edit the plan mid-run. Abandon the run, then author a successor book with a fresh `PB-NNNN`. Numbers are never reused.

### 6. Read the schema before deep work

`bionic/AGENTS.md` (created by `init-docs`) is the operational schema the three supported harnesses share. If you find yourself wondering "wait, should an agent be writing here?", that file has the answer. Skim §1–§7 once.

### 7. Don't hand-edit; ask Claude to fix it

If you spot something wrong, such as a stale page, a contradiction, or a broken link, tell Claude. The whole point is that the bookkeeping is automated. Hand-edits to managed files can slip past audits and quietly desynchronize counters or indexes.

### 8. The `crux/` directory in this repo IS the plugin

`crux/` is what the marketplace (`/plugin install crux@crux`) distributes into other projects. Skill definitions live at `crux/skills/*/SKILL.md`. The catalogs under `crux/catalog/` are regenerated, so don't hand-edit them.

---

## Where to go next

- **[Crux guide](https://bionic-coding.com/crux/)**: installation and usage on the public documentation site.
- **[USER_GUIDE.md](./USER_GUIDE.md)**: the deep human-facing guide, covering the mental model, phrase reference, secrets, and troubleshooting.
- **[CODEX.md](./CODEX.md)** and **[OPENCODE.md](./OPENCODE.md)**: detailed Codex and OpenCode installation instructions for humans and agents.
- **`bionic/AGENTS.md`** (after `init docs`): the operational schema Claude reads. It is authoritative.

## License & status

MIT licensed (see [LICENSE](./LICENSE)). v3.23.2 — see [CHANGELOG.md](./CHANGELOG.md) for the per-release breakdown. Issues welcome; the public repo is regenerated on every release, so pull requests there cannot be merged.
