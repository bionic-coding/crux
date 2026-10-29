<!-- generated-from: README.md@sha256:5e98407633a38113646a431f71d70b9e88b90a6ceec139752cb410ec93463179; model: claude-sonnet-5.5; date: 2026-10-29 -->
# Crux

An Agentic Harness plugin that maintains a `./bionic/` tree inside any software project, so that Claude can navigate, query, and update project knowledge without anyone having to remember where things go. Everything runs locally: no server, no accounts, no background service, just skills, scripts, and your repo.

## Start here

Visit the [Crux guide](https://bionic-coding.com/crux/) for installation and usage instructions.

## About this repository

This repository is generated from a private development repo on every release (see `.generated`). Each release is one squash commit. Please file issues; pull requests would be overwritten.

## Install

crux installs through Claude Code's plugin marketplace. In any Claude Code session, run two slash commands:

```
/plugin marketplace add bionic-coding/crux
/plugin install crux@crux
```

The second command installs the plugin named `crux` from the marketplace you just added (also named `crux`). The same two commands handle upgrades: re-run `/plugin install crux@crux` after `/plugin marketplace update crux` to pick up a new version. Installation does **not** touch your `./docs/` folder; you bootstrap that yourself. Restart the session so the plugin's skills and agents register, then say:

> **init docs**

That bootstraps the seven-concern `bionic/` tree plus the default-on arch spine, and seeds `bionic/AGENTS.md` (the operational schema the three supported harnesses share), `bionic/manifest.yml`, and the meta-ADR `ADR-0000`.

Optional, Claude Code only: `/plugin install crux-mods@crux` adds the run dashboard, a band above the prompt and a `/crux-dashboard` pane. See [USER_GUIDE.md](./USER_GUIDE.md), "crux-mods".

Using Codex, OMP, or OpenCode? See [Install on other hosts](#install-on-other-hosts) below.

---

## What crux maintains

**56 skills** across seven concerns, plus a default-on, derived **arch** surface (the current-state architecture map, built on demand by `derive-arch`) and the default-on **observations** concern (what the code already does, evidenced and ratified rather than decided). It also ships a **10-agent operator layer** (see **Agents** below). All skills share one naming convention, with no `crux-` prefix.

`crux/catalog/bundles.yml` records the bundle organization: docs suite, core agent-team, verification, infrastructure.

| Concern | What lives there | Who writes it |
|---|---|---|
| `bionic/code/` | Auto-extracted from source docstrings (`@moduledoc`, JSDoc, etc.) | Regenerated — never hand-edit |
| `bionic/research/` | Articles, papers, URLs, meeting notes, chat exports | You drop sources; Claude ingests |
| `bionic/adrs/` | Architecture Decision Records — the "why" of every load-bearing decision | You decide; Claude writes. Frozen once Accepted |
| `bionic/briefs/` | Pre-decision exploration documents | You author; Claude tracks |
| `bionic/journal/` | Day-by-day record of work performed | Claude appends; you ask |
| `bionic/cycles/` | Current plans, tasks, decisions, evidence, and pass history | Maintained by the cycle workflow |
| `bionic/promptbooks/` | Historical plans and immutable run snapshots | Preserved |
| `bionic/invariants/` | Pinned, executable statements of what must stay true, each backed by a real check | Machine proposes; **you ratify** |
| `bionic/observations/` | Records of what the code already does, each evidenced by a `path:line-range` — described, not decided | You write via `propose-observation`; **you ratify**. No scan writes one |
| `bionic/arch/` | Derived architecture spine — the current-state map (data model, interface surface, module graph, decision index) | Regenerated on demand by `derive-arch`; default-on for new repos, never hand-edited |

**You curate, decide, and discuss. Claude does the bookkeeping.**

To learn how a project is shaped *right now*, start with `bionic/arch/`, the derived current-state map. ADRs are the secondary path (the *why* behind each decision); the librarian and historian agents fill whatever those two don't cover. arch is **default-on for new repos** (init-docs enrolls it, so a fresh tree ships it). Just run **"build the arch"** to derive the spine, then keep it current with `derive-arch` (or let `audit-docs` auto-regenerate it on drift). An **existing tree that predates the default** opts in first (add `arch` to `concerns_enabled`), then derives.

To learn what a project currently holds to be true, and whether that belief is live or only on paper, start with `bionic/adrs/doctrine/` instead. It is a derived, per-domain, plain-language view compiled from the ADR summaries and reconciled against ratified invariants. Doctrine is derived and holds no independent authority. Resolve disagreements through source decisions and validated published dispositions. Historical decision bodies remain preserved even when their clauses no longer govern. This is a different question from the shape question `bionic/arch/` answers: arch says what exists, doctrine says what's currently believed.

The full mental model and conventions live in [USER_GUIDE.md](./USER_GUIDE.md). The operational schema Claude follows lives in `bionic/AGENTS.md` (created on first run). The tree's location is recorded in `.bionic.yml`; an existing `docs/` tree keeps working unchanged.

---

## The cycle — crux's primary workflow

A **cycle** is one trip around crux's development loop for a single feature or change. Most of your time inside crux happens here. Once the tree is bootstrapped, the typical day looks less like "I'll write some code, then update some docs" and more like:

> **"Start a cycle for &lt;feature&gt;. The goal is &lt;one paragraph&gt;."**

Crux creates one cycle with a visible plan, tasks, phase, pass count, and evidence.
There is no prompt minimum and no separate repeat run.

| Type | Sequence | Default pass limit |
|---|---|---:|
| dev — major changes | Plan → Build → Test → Review → Reflect | 7 |
| iterate — minor changes | Plan → Build → Test → Review → Reflect | 2 |
| refactor — nonfunctional improvements | Plan → Build → Test → Review → Reflect | 7 |
| simplify — remove complexity, keep behavior | Plan → Build → Test → Review → Reflect | 3 |
| quick-fix — bounded corrections | Build → Test → Review → Reflect | 1 |
| release — one fixed step list, beta or official | Release | none |

The initial attempt counts toward the limit. Failed tests and blocking review findings
return to Build in every type. Stalled progress pauses the cycle early;
additional passes require human approval. A release has one phase and no pass limit; it runs a fixed step list, so no plan or review is authored.

Dev requires a council-approved Implementation Decision Record (IDR). Simplify requires
an approved selection IDR that names the proposals to build. Other types need an IDR
for material implementation choices. ADRs can originate from a direct
request, whiteboarding, or inbox processing. Inside a cycle, council must first justify
creating an ADR. Draft approval is a separate council decision; acceptance also needs
human approval by default. New-policy acceptance makes its rules binding.

Configure review scrutiny and ADR acceptance in `.bionic.yml`. Review defaults to
`standard`, with `focused` and `intensive` alternatives. Every cycle has independent
review, with specialists selected for actual risks. Tests reuse repository-owned
passing evidence when relevant inputs and environment match, including across cycles.
Historical promptbooks remain readable; new work uses cycles.

Cycle requests go through Commander, who assigns implementation to Dev Lead and
independent review to Reviewer. Dev Lead supplies each developer's base commit
and owns integration. Before completion, new cycles record related-test coverage
and committed implementation changes, unless you explicitly request uncommitted work.

---

## Agents — the role layer

crux bundles a **role-based agent layer**: **ten** Claude Code subagents that *operate* the skills above. Each carries a `tools` allowlist that **structurally enforces** what it may and may not do, so separation of duties comes from tooling, not from instruction.

| Agent | Role | Structurally cannot |
|---|---|---|
| **commander** | Conductor — drives a cycle or existing historical run; delegates every unit of work | edit code or docs (delegates only) |
| **brainstormer** | Docs-aware design exploration; drives the `whiteboarding` skill | write files (returns a session the historian files) or edit code |
| **architect** | Owns ADRs/decisions (`propose-adr`, `council`, `transition-adr`) | implement code |
| **dev-lead** | Lead implementer; the one agent that fans out to `developer`s | merge/push (human-gated) |
| **developer** | Implements one scoped unit, test-first | re-delegate; write docs/ADRs |
| **reviewer** | Independent code review + verification | edit files (reviews; never fix-and-hide) |
| **historian** | Owns *all* `docs/` writes — setup, maintenance, intake, preservation | edit source code |
| **librarian** | Read-only retrieval from `docs/` (`query-docs`) | write anything |
| **night-gardener** | Overnight visionary/coach/co-CTO — reviews recent work, writes a morning note under `docs/garden/` (ideas, gaps, research, news) | push/merge, send externally, or self-install the routine |
| **wayfinder** | Read-only reconnaissance — reads large/uncertain or external data ahead of the caller, judges fitness, returns a verdict + condensed digest so the primary spends its context only on proven-fit content | write, execute, delegate, or relay local content outbound |

Two choices make the layer portable and safe. Agents are **self-contained**: the craft disciplines (TDD with its proof-mechanism, verification-before-completion, systematic debugging, two-stage review) are embedded in each agent's prompt rather than depending on separately installed skills. And they are **first-class catalog citizens**: agent frontmatter is regenerated into `catalog/agents.json` exactly like skills, with an `agents:` array in `plugin.json`. The agents register once the plugin is installed or upgraded to a version that ships `crux/agents/` and the session is restarted.

Codex installs the same ten roles as namespaced `crux_*` agents. Each installed
role pins its catalog model and reasoning effort. It also binds every declared
skill to the selected Crux plugin. Codex runtime verification remains
`unverified` until fresh-session host evidence confirms discovery, settings,
skill availability, and representative workflows for that client version.

---

## Skills — what each does, and when to reach for it

You never type a slash command. Each skill is triggered by natural-language phrases routed through its `description`. The 56 skills, grouped by what you're trying to do (the **say this** column is a representative trigger, not the exhaustive list):

### Getting set up
| Skill | Say this / when | What it does |
|---|---|---|
| `init-docs` | "init docs" — first run in a repo | Bootstraps the seven-concern `bionic/` tree plus the default-on arch spine + `bionic/AGENTS.md` + `manifest.yml` + the meta-ADR. |
| `install-docs-skills` | "which Crux version is active?" / "install docs skills" / "upgrade the docs suite" | Reports the active Crux version when the selected skill path or host trace proves it; otherwise says unverified. Gives marketplace install/upgrade instructions on request. |
| `install-micro-crux` | "install micro-crux" / "update micro-crux" | Opt-in: installs or updates standalone `micro-crux.md` and an explicit root `AGENTS.md` read instruction. Preserves local edits and reports conflicts. |
| `install-runtime` | "install the crux runtime" | Deploys the runtime (scripts + LLM router) into a target repo. |
| `install-codex-agents` | "install the Crux agents in Codex" / "refresh Codex agents" — Codex users only | Installs or refreshes the ten generated Crux roles in `~/.codex/agents/` by default. `--repo-root` selects one project. `--check` reports canonical expectations, parsed installed state, drift, shadows, and runtime status. |
| `install-opencode-agents` | "install the Crux agents in OpenCode" / "refresh OpenCode agents" — OpenCode users only | Installs or refreshes the ten generated Crux role agents into a target repo's `.opencode/agents/`; no-clobber (`--force` required to overwrite a modified role). |
| `install-omp-agents` | "install the Crux agents in OMP" / "refresh OMP agents" — OMP users only | Installs or refreshes the ten generated Crux roles in `~/.omp/agent/agents/` by default (`--repo-root` selects `.omp/agents/`); no-clobber (`--force` required to overwrite a modified role). |

### Code docs (regenerated from source — never hand-edited)
| Skill | Say this / when | What it does |
|---|---|---|
| `extract-code-docs` | "extract code docs" / pre-push hook | Regenerates `docs/code/` from source docstrings (`@moduledoc`, TSDoc, Python via Griffe, …). |
| `verify-code-docs` | "verify code docs" / before merge | Read-only drift check — reports staleness without writing. |

### Architecture (derived current-state map — default-on for new repos)
| Skill | Say this / when | What it does |
|---|---|---|
| `derive-arch` | "build the arch" / "summarize the current architecture" / "regenerate the architecture" | Regenerates `docs/arch/` — the derived spine (data model, interface surface, module graph, decision index) plus a synthesized overview — wholesale from the project's own sources. Detects the repo's stack and derives a real spine with batteries-included packs for Python, Ruby, Node.js, Elixir/Phoenix, and Swift. The Swift pack reads Swift packages and Xcode projects, with targets, product types, membership and `@main` owners. An unsupported stack degrades to an empty-but-valid spine. `--dry-run` is the drift check. The primary current-state discovery surface. |
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
| `migrate-adrs` | "migrate ADRs" / "review historic ADRs" / "review the decisions" | Architect-led clause assessment against current objectives, with resumable pages and exact approval before committed publication. |
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

### Cycles and historical promptbooks
| Skill | Say this / when | What it does |
|---|---|---|
| `cycle` | "start a cycle" / "quick fix" / "release" / "refactor" | Runs one task-sized cycle with type-specific phases, bounded returns, independent review, and reusable test evidence. |
| `cycle-status` | "show cycle status" / "watch the cycle" | Prints cycle progress read-only; `--watch` redraws it in a second terminal and `--json` prints the machine-readable document. |
| `dev-cycle` | "develop this" | Compatibility alias for a dev cycle. |
| `iterate` | "iterate on this" | Compatibility alias for an iterate cycle. |
| `patch-cycle` | "patch this" | Routes to quick-fix or iterate according to scope. |
| `fix-directly` | "just fix it" | Routes to a quick-fix cycle with slim testing, review, and reflection. |
| `author-promptbook` | "new promptbook" | Routes new work to a cycle; preserves historical promptbook guidance. |
| `run-promptbook` | "inspect this promptbook" / "advance this existing run" | Reads or finishes existing historical runs. New work uses cycles. |
| `archive-promptbook` | "archive promptbook" | Archives a completed or deliberately abandoned historical book. |

Choose dev for major changes, iterate for minor changes, refactor for nonfunctional improvements,
simplify to remove complexity without losing behavior, quick-fix for bounded corrections, and
release for publication work.

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
These power the council + agent layer; you mostly invoke them indirectly (new decisions use `cycle-council.py`; historical runs retain `run-council.py`).
| Skill | Say this / when | What it does |
|---|---|---|
| `council` | "ask the council" / choosing between approaches | Configured Lite, Standard, or Strict council. Lite uses native Apex models from the model catalog; Standard and Strict use gateway seats from the router registry. New cycles use `cycle-council.py` to record approvals; historical runs retain their original runner. |
| `run-adr-council` | "run the council on ADR-NNNN" / "council review ADR-NNNN" | Reviews the exact ADR draft through council. New-policy approval supports acceptance inside or outside a cycle; cycle-originated ADRs also need separate creation justification. Historical runs retain their original evidence format. |
| `srde` | after a split council verdict where its workflow permits | Self-Resolving Dissent Engine: gathers shared context and existing probes on a split verdict. An evidence tool, never a gate; it never runs on the ADR path. |
| `forge-skill` | a capability you lack mid-task | RSI (recursive self-intelligence) capability-gap loop: diagnose → research → author a project-local skill in `.claude/skills/`, autonomous with gates. |
| `tend-garden` | "tend the garden" / "night pass" / overnight sessions | The night-gardener's pass: reviews recent moves, reads diagnostics + news, writes a morning note under `docs/garden/`. |
| `retrospective` | "what should we learn from recent work" | Purposeful reflection: mines logs/journal/runs, harvests ≤2 council-gated skill proposals, builds them via forge-skill. |
| `call-llm` | programmatic single-model calls | Multi-provider LLM caller (Claude / Gemini / GPT). |

For ad-hoc decomposition, ask to whiteboard the goal or use your host's planning facility. For a tracked plan, use a cycle. The retained task planner, tracer, probe bridge, and identity APIs are documented in `crux/box/runtime-apis.md`. The explicit runbook generator and HTTP service are documented in `crux/box/operator-services.md`. Both references ship with the plugin; the Python modules and existing artifacts remain available.

**Reaching for an agent directly:** you rarely name an agent. The cycle and the `commander` dispatch them for you (see [Agents](#agents--the-role-layer) above). But you can: *"have the architect propose an ADR for X"*, *"send this design to the council"*, *"have the reviewer check the diff"*, *"ask the librarian what we decided about Y"*.

---

## Install on other hosts

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

### OMP (Oh My Pi)

See [OMP_INSTALL.md](./OMP_INSTALL.md) for complete machine-wide and project installation instructions.

OMP natively supports the Claude Code marketplace catalog for skills. Install the plugin in OMP:

```
/marketplace add bionic-coding/crux
/marketplace install crux@crux
```

Then say **"install the Crux agents in OMP"**. The `install-omp-agents` skill writes the ten projected `<role>.md` agents into `~/.omp/agent/agents/` by default (or `<repo>/.omp/agents/` with `--repo-root`), configuring per-role `@crux_<role>` model role selectors with OpenRouter fallbacks, `thinking-level`, `read-summarize: false` on retrieval roles, and native `tools`/`spawns` allowlists. Optional: load `crux-omp` (`omp -e ./crux-omp/index.ts`) for the TUI run dashboard.

### OpenCode (manual setup)

See [OPENCODE.md](./OPENCODE.md) for complete machine-wide and project
installation instructions for humans and agents.

There is **no native Crux OpenCode marketplace package yet**. OpenCode support is a **manual, preview-grade setup** for now, and a public OpenCode distribution channel is a deliberately deferred future decision. The steps below wire the full Crux skill set and the 10 agents into OpenCode 2.x from a public clone. Install OpenCode 2.x with `curl -fsSL https://opencode.ai/v2/install | bash`, which leaves a binary named `opencode`.

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

**Per-project agents instead of machine-wide.** The steps above give every project on the machine the ten roles. To scope them to one repo, skip steps 3 and 5 and say **"install the Crux agents in OpenCode"** from that repo. The `install-opencode-agents` skill generates the same ten projected roles from `crux/agents/` and writes them into `.opencode/agents/`. It refuses to overwrite a locally modified role without `--force` and leaves the project's own agent files alone. A project-scoped role shadows a global one of the same name.

---

## Requirements

- [Claude Code](https://claude.ai/code) v2.1.284 or later. The agents and skills that name `claude-sonnet-5-5` need that version. Claude Code reads `AGENTS.md` from v2.1.277 under its default settings, except on the Bedrock, Vertex and Foundry distributions.
- Python 3.13 or newer, and [uv](https://docs.astral.sh/uv/). Every script declares its interpreter floor and its dependencies in a PEP 723 header, so `uv run <script>` resolves both. A bare `python3` runs only the stdlib-only scripts. macOS ships 3.9 at `/usr/bin/python3`, which cannot parse this code.

### Optional: secrets management

If any of your workflows need API keys, crux ships a `crux-env` CLI that keeps them in `~/.crux/env` (mode `0600`, outside any repo, never committed). Invoke it via the installed plugin (`${CLAUDE_PLUGIN_ROOT}` is the plugin's install root, set inside Claude Code sessions; in a plain terminal substitute the plugin's install path. Alias the command if you use it often):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" init                       # one-time setup
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" set OPENROUTER_API_KEY ...  # store a key
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crux-env.py" check --project crux      # verify what a project needs
```

See [USER_GUIDE.md → "Working with secrets and API keys"](./USER_GUIDE.md#working-with-secrets-and-api-keys) for the full surface.

### Optional: per-project configuration

A repo can commit an optional `.bionic.yml` file at its root (distinct from the `~/.crux/` secrets directory — never put secrets in it). Besides the required `config_version: "1"`, optional keys can relocate the tree (`docs_dir`) or brand artifact ids with a prefix (`artifact_prefix: "CRX"`). It supersedes the legacy `.crux` file, which is still read for back-compat. Copy `crux/templates/bionic-yml.tmpl` to get started; see [USER_GUIDE.md → "Per-project configuration"](./USER_GUIDE.md#per-project-configuration-the-repo-root-bionicyml-file).

---

## Tips for using it

### 1. It's all natural language — no slash commands

Skills are triggered by phrases routed through each skill's description. Say what you mean; Claude picks the right skill.

| Say this | …and Claude will |
|---|---|
| **"start a cycle for X"** | **Start a task-sized cycle with the appropriate type and pass limit.** |
| "advance" / "next prompt" | Advance the active cycle when its phase evidence is satisfied; historical runs retain prompt advancement |
| "propose an ADR for X" | Allocate the next ADR number, draft a `Proposed` decision record |
| "accept ADR-0007" | Flip status to `Accepted` — body is now frozen forever |
| "process inbox" (after dropping anything in `docs/inbox/`) | Classify each dropped item + confirm + dispatch to the right skill (research → ingest, decision → ADR, exploration → brief, note → journal) |
| "log work — fixed the X bug" | Append a categorized entry to `docs/journal/YYYY-MM.md` |
| "new promptbook for X" | Route new work to a cycle |
| "run promptbook <id>" | Inspect or finish an existing historical run; do not repeat a completed run |
| "extract code docs" | Regenerate `docs/code/` from your source's docstrings |
| "audit docs" | Run ~97 integrity checks across every enabled concern and auto-fix safe drift; `audit docs --migrate` migrates instruction files only and cannot upgrade older tree schemas — for an older-schema tree, run the pinned public `v3.23.2` procedure on a copy |
| "what does X do?" / "why did we choose Y?" | Search `docs/`, return answers with citations |

### 2. Run `audit docs` regularly

Especially after large batches of writes, after a research refresh, or before a release. It catches dangling links, supersession asymmetries, missing index rows, and stale counters, and fixes the safe ones automatically.

One rule is now mechanical rather than prose: the `## ADRs (N)` rollup in `docs/index.md` is a pure function of your ADR frontmatter, so `crux/scripts/generate-index-rollup.py` regenerates it (`--dry-run` reports drift, exit 1). Prefer running it over hand-fixing that section. The rest of the rollups are still checked by `audit-docs` reading them. A prose check that passes tells you an agent believed it walked everything, not that it did.

### 3. The append-only stuff really is append-only

- **ADRs**: once Accepted, the body is immutable. To change a decision, write a new ADR that supersedes the old one (e.g. `"supersede ADR-0001 with ADR-0005"`). Claude updates both ends of the link atomically.
- **`docs/code/`**: regenerated on every extract run. Hand-edits are blown away. If a docstring is wrong, fix it in the source.
- **`docs/research/raw/`**: every fetched capture lives there forever, dated. Don't prune it — that's your audit chain when a synthesis page is challenged.
- **`docs/journal/`**: chronological narrative. Don't reorder past entries.

### 4. Capture anything by dropping it in the inbox

The fastest path to building a useful docs tree:

1. Drop a PDF, screenshot, markdown file, a stray decision note, or a half-formed idea into `docs/inbox/`.
2. Or paste URLs — one per line — into `docs/inbox/urls.md`.
3. Say **"process inbox"**. `process-inbox` classifies each item, shows you a confirmation batch, and dispatches it to the right skill (research → `ingest-research` → immutable `raw/` capture; decision → `propose-adr`; exploration → `propose-brief`; note → `log-work`).

Claude fetches, captures a dated raw copy, writes an audited source page in `bionic/research/sources/`, and offers to update synthesis pages where the content is relevant.

Later, say **"refresh sources"** to re-fetch URLs and mark synthesis pages affected by upstream changes.

### 5. Cycles preserve the plan and its changes

Each cycle keeps its plan, tasks, decisions, evidence, and pass history in
`bionic/cycles/<CYC-NNNN>/cycle.json`. Replanning preserves earlier plans and records
why work returned. Pause and resume keep the same identity. Completed or abandoned
cycles stay closed; follow-up work starts a new cycle.

Historical promptbooks and their run snapshots retain their original interpretation.
Do not rewrite them or create new repeat runs.

### 6. Read the schema before deep work

`bionic/AGENTS.md` (created by `init-docs`) is the operational schema the three supported harnesses share. If you find yourself wondering "wait, should an agent be writing here?", that file has the answer. Skim §1–§7 once.

### 7. Don't hand-edit; ask Claude to fix it

If you spot something wrong, such as a stale page, a contradiction, or a broken link, tell Claude. The whole point is that the bookkeeping is automated. Hand-edits to managed files can leak through audits and quietly desynchronize counters or indexes.

### 8. What's in this repository

- `crux/` — the plugin itself. This is what the marketplace (`/plugin install crux@crux`) distributes into your projects.
- `crux-mods/` — the opt-in Claude Code mods plugin, released with crux at the same version.

---

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

## Where to go next

- **[USER_GUIDE.md](./USER_GUIDE.md)** — the deep human-facing guide. Mental model, phrase reference, secrets, troubleshooting.
- **`bionic/AGENTS.md`** (after `init docs`) — the operational schema Claude reads. Authoritative.
- **[The Crux guide](https://bionic-coding.com/crux/)** — installation and usage documentation.

## License & status

MIT licensed (see [LICENSE](./LICENSE)). v4.8.0 — see [CHANGELOG.md](./CHANGELOG.md) for the per-release breakdown. Issues welcome; the public repo is regenerated on every release, so pull requests there cannot be merged.
