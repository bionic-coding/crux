---
title: Operations log
read_when: Writing, repairing, summarizing or checking an operations-log entry
sections:
  - "§6 log format, writer, commit step and op meanings"
---

# Operations log

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §6`, resolves to this file.

## 6. `docs/log/` format — the operations log

The op enum and its two regex blocks stay in `<docs_dir>/AGENTS.md` §6, because the log writer reads them from that file.

The operations log is the set of monthly detail files `docs/log/YYYY-MM.md`, one file per month.[^oplog-files] Each detail file starts with this header and then holds its entries, the latest write at the top:[^oplog-latest-first]

```
# Operations log: YYYY-MM

_Append-only. Latest write first._
```

Each entry starts with the exact heading prefix:

```
## [YYYY-MM-DD] <op> | <subject>
```

**Routing by write time.** The writer adds each entry to the detail file of the month that holds its host's local date, whatever date the heading carries. The choice of file changes no byte of the entry.[^oplog-local-month] A release entry headed with its publication date in another zone, or an entry recorded late, therefore sits in the month it was written. Heading dates inside one file need not be in order, and no check orders them.

**Writing an entry.** Every entry goes through the one log writer, and no writer creates `docs/log.md` or adds an entry to it.[^oplog-writer] A skill writes its own records first, writes the entry's body lines to a file outside the tree, and then runs:

```
uv run "${CRUX_PLUGIN_ROOT}/scripts/operation-log.py" append --repo-root <repo-root> \
  --op <op> --subject '<subject>' --date <YYYY-MM-DD> --body-file <path>
```

`--body-stdin` reads the body from standard input instead. The command validates the entry against the current-writer regex in `<docs_dir>/AGENTS.md` §6. It completes the first split and merges any stray before it adds the entry, and it adds no entry that a detail file already holds.[^oplog-repair-first] It prints one JSON result: `status` (`written`, `recorded` or `refused`), `file`, `changed_paths`, `commit_paths`, `restore_paths` and `left_strays`. It exits 0 on `written` or `recorded`, 1 on `refused`, and 2 on an environment fault.

**A refused append.** An append that refuses leaves the skill's own writes in place and adds no entry. It refuses for one of three causes:

- The skill's own body or heading fails validation: an unfenced `## ` body line, a fence left open, a subject that holds a pipe or a newline, an op outside the enum, or a heading date that is not a real calendar date. Fix the body or the heading.
- A tree fault that names its own fix, such as a malformed stray heading or a destination whose bytes outside its entries leave a fence open. Apply the named fix.
- Another writer changed a planned file or the destination during the write. No fix is needed.

Then rerun the append step alone. It writes the entry once, and a further rerun reports `recorded`.

**The commit step.** Run it after every append, whatever the status, because a refused append can still have repaired the log:

1. When `restore_paths` is not empty, run `git restore --staged --quiet -- <restore_paths>`. It resets each path's index entry to HEAD and changes no work-tree file.
2. Combine the skill's own paths with `commit_paths`. The skill's own paths are those its own rule commits; a skill that commits nothing of its own, and any skill after a refused append, adds none. When the combined list is not empty, drop every path that `git check-ignore -- <paths>` prints. Git ignores each such path, so the step never commits it. `git check-ignore` exits 1 when it prints no path, which is not an error. When paths remain, run `git add -- <paths>` and then `git commit --only -- <paths>`; otherwise the step ends after the restore. Report each dropped path and that its commit was skipped.

Known limit: the commit step commits every log path that `git status` lists. That includes a file that `operation-log.py check` reports as undefined and a half-finished hand edit of a detail file, as the whole-file commit of `docs/log.md` did.

**The legacy file and strays.** A tree written before this layout holds one `docs/log.md`. The first log write, or `operation-log.py repair`, splits it into detail files by heading month, changes no entry's bytes, and records completion last, in `docs/log/.split-complete.json`.[^oplog-split] An older plugin keeps writing `docs/log.md` after the split. That file is a stray: the next log write or repair moves its new entries, as one block, to the top of the current month's detail file and removes it.[^oplog-stray] Resolve a git modify/delete conflict on `docs/log.md` by keeping the branch's whole file, which the stray merge places, and never by taking the deletion. `operation-log.py repair --dry-run` prints the plan and the split's proof and writes nothing.

**Names under `docs/log/`.** These names are defined, and no other. Three stay: the detail files `YYYY-MM.md`, the summary `summary.md` and the completion record `.split-complete.json`. A fourth stays too: the kept file `.kept-<sha256>.txt` holds, once, the bytes that came before the first entry of the legacy log or a stray, such as its old header. The split and the stray merge write it only when those bytes are not empty. Four names are transient, and a log write or repair creates and removes each one: the staged legacy file `.legacy-<sha256>.md`, the staged stray `.stray-<sha256>.md`, the split transaction file `.split-<sha256>.json` and the writer temporary `.write-journal-<hex>`. In the kept, staged legacy and staged stray names, `<sha256>` is the digest of the file's own bytes; in a transaction file's name it is the digest of the staged legacy file. A staged or transaction file that remains marks an interrupted split or merge, which the next log write or `operation-log.py repair` completes. A remaining writer temporary is reported as a warning.

**The summary.** `docs/log/summary.md` holds one section per settled month, newest first. A month M settles on the third day of month M+1 by the generating host's local date, and no section is written before its month settles.[^oplog-summary] Each section is a `## YYYY-MM` heading and a GENERATED region: the detail file's path and sha256, the entry count, the first and last heading dates, the count of each op, and the ADR ids that `adr` entries name. A rollup region above the sections tabulates them. `generate-log-summary.py` writes the regions, and its `--dry-run` is the summary gate. A settled month with no section is pending, not drift; `cleanup-campsite` runs the catch-up. Text after a month's region and before the next month heading is that month's narrative, which the historian writes on request and the regenerator keeps byte for byte.

**Checks.** `uv run "${CRUX_PLUGIN_ROOT}/scripts/operation-log.py" check --repo-root <repo-root>` runs the audit checks CHK-LOG-1 to CHK-LOG-7, which `audit-docs` reports.

#### Op-enum changes and op meanings (§6)

**Changing either enum is not a one-line edit here.** The installed crux skills carry their own copy of both enums, and each does something different with it. `log-work` refuses a log op its copy does not carry, and writes nothing. It does NOT refuse an unknown journal category: it falls back to `misc` and warns, so the entry lands under the wrong name rather than not at all. `audit-docs` reports a heading outside either enum and edits neither — CHK-LOG-1 surfaces a log heading as drift, CHK-JR-1 a journal heading as a warning. `generate-journal-index.py` refuses a month file whose heading carries a category outside its tuple. An op or category added to this file alone therefore reaches none of them. Extending either enum is a change to the crux plugin rather than to this file.

- `init` — `init-docs` ran.
- `extract` — `extract-code-docs` regenerated `docs/code/`.
- `arch` — `derive-arch` regenerated the `arch` spine (`docs/arch/`). Body: N files re-emitted, the new spine hash, and the trigger. The derived-architecture concern (per §4); default-on for new repos, additive.
- `ingest` — a source landed in the research wiki.
- `refresh` — `refresh-research-sources` or `refresh-research-synthesis` ran.
- `audit` — full vault-walk by `audit-docs`.
- `cleanup-campsite` — `cleanup-campsite` regenerated `docs/whats_next.md`. Body: `N open (X P1, Y P2, Z P3), M closed, K dismissed` plus top-3 P1 ids.
- `lint` — drift-check / verification result. Distinct from `audit` — narrower and triggered by `verify-code-docs` or by `audit-docs` sub-checks.
- `adr` — ADR proposed, accepted, deprecated, or superseded.
- `brief` — either `propose-brief` scaffolded a brief under `docs/briefs/` (body: title + path + `status: draft`), or `transition-brief` transitioned a brief's status (body: `BRIEF-<slug>: <old-status> → <new-status>`).
- `journal` — `log-work` appended a journal entry.
- `promptbook` — a book-level OPERATION, not a step. The op keeps its enum entry and its meaning; only its cardinality changed. **Three write points in a book's life, and advancing a prompt is not one of them.** An authoring skill (`author-promptbook` / `dev-cycle` / `iterate` / `patch-cycle`) writes one op when the book is authored; `run-promptbook` writes one when a run STARTS; `archive-promptbook` writes one when the book archives. Authoring keeps its op because it IS an operation — the cardinality cut is aimed at the per-step entry, and a book authored but never run would otherwise leave no trace in the log at all. **Advancing a prompt writes none.** Postcondition: the per-prompt chronology stays reconstructable from the run snapshot's own `started`/`completed` timestamps, which are per-prompt and immutable — a reader walks the snapshot directory instead of grepping one file. (`run-promptbook` status also writes this op, but only on the deliberate `--markdown` artifact write.)
- `invariant` — `transition-invariant` dispositioned an invariant pin (ratify/reject/retire). Body: pin id, class, the transition. The machine-side `recover-invariants` candidate emit logs no op of its own; only the human ratification gate writes `invariant`. (Invariants concern, schema_version 4+.)
- `observation` — an observation record was created or transitioned. Body: record id, the operation, one line. Two human-invoked commands write it on creation — `propose-observation` (the reconstructed ramp) and `transition-decision ratify --as observation` (the mined ramp) — and `transition-observation` writes it on a disposition (ratify/reject/retire/decide). This op splits from `invariant` by artifact class, not by writer: an observation is a distinct record with its own id space (`OBS-NNNN`) and its own lifecycle (§17.2). (`recover` splits from `adr` for the opposite reason — the machine emit of a decision candidate is itself logged. No scan writes an observation file in any state, so no scan logs an `observation` op.) A fourth writer, the batch sign-off, writes one entry per signed batch under the subject grammar `survey batch <batch-id>`, with the sorted record ids in the body; the protocol is §17.5. That batch entry reuses this op and mints none, because `audit-docs` reads the target tree's own op enum. Observations concern, additive.
- `recover` — `recover-decisions` emitted N observed decision candidates into `<docs_dir>/arch/_recovered/state.yml`. Body: partition scanned, candidate count. NEVER ratifies — only `transition-decision` writes `adr` on the recovery path. Arch/decision-recovery.
- `query` — `query-docs` answered a question. Optional log entry; off by default.
- `schema` — `manifest.yml` schema changed (new concern enabled, language extractor added, etc.).
- `skill` — forge-skill authored, revised, or pruned a project-local skill under `.claude/skills/`. Body: gap one-liner, path, self-test outcome, forge-log pointer. The `skill` op is the act's sole op written directly by forge-skill; the accompanying `log-work` journal call writes its own standard `journal |` op recording the append, as for every journaled act — never a duplicate `skill` op. Added for the forge-skill capability-gap loop.
- `origin` — a skill (or group of skills) was ported into the project from an external source. Body: which skill(s), from what ref, on what date.
- `garden` — `tend-garden` wrote a morning note under `docs/garden/`. Body: note date, headline count, artifact count. Written immediately BEFORE the note (the op is the note's log_head anchor and corroboration).
- `adr-review` — historical decision-review operation. Existing entries preserve the review date, historical report path and recorded finding counts. The token remains valid in old logs and in the backlog category and finding-id prefix; `migrate-adrs` writes no new decision-review report or `adr-review` operation. Historical reports and their log entries remain unchanged.[^historical-reviews]
- `backfill` — a governs backfill batch sign-off ran, initial or correction. Body: the batch id and the affected ADR ids, carried as `ADRs: <sorted ids>` so the receipts↔log↔journal cross-validation joins all three surfaces by batch id and date. One entry per batch; written only by the backfill sign-off skill. Heading: `## [<signed-date>] backfill | <batch-id>` — the subject IS the batch id. Body carries `ADRs: <sorted ids>`. The paired journal hook is category `review`, subject `backfill sign-off <batch-id>`, in the signed month.
- `release` — a version was published to a release target. Body: the publication time carrying an explicit timezone, the version, the target repo, and the published revision. The heading date is the publication date in that same timezone, so the heading and the instant below it never name different days. A release published at 05:08 UTC therefore reads as the previous day in Mountain time, which is the day the person who ran it experienced. Name the zone rather than an offset, so a winter release reads MST and a summer one MDT. One entry per target, so a version that reaches the private beta and then the public repo carries two entries. The beta entry is written first, because a version that fails beta never reaches the public repo. A record written after the fact also names when it was recorded, so a reader can tell the act from the note of it. Written by whoever runs the release.

Body under the heading: 1–5 lines. List specific paths touched. Keep terse — the operations log is for grep, not reading.

`grep -h "^## \[" docs/log/[0-9]*.md` lists every entry heading, each month's entries in write order. `grep -ohE "^## \[[^]]+\] \w+" docs/log/[0-9]*.md | sort | uniq -c` returns per-op counts.

[^historical-reviews]: rule:historical-review-reports-stay-readable
[^oplog-files]: rule:operations-log-is-monthly-detail-files
[^oplog-latest-first]: rule:detail-file-puts-the-latest-write-first
[^oplog-local-month]: rule:log-writer-uses-its-local-month, rule:placement-changes-no-entry-byte
[^oplog-writer]: rule:log-entries-go-through-the-log-writer, rule:no-writer-writes-the-legacy-log-file
[^oplog-repair-first]: rule:log-writer-completes-the-split-first, rule:log-writer-merges-a-stray-first, rule:log-write-adds-nothing-already-placed
[^oplog-split]: rule:first-split-routes-by-heading-month, rule:log-split-keeps-every-byte, rule:first-split-records-completion-last
[^oplog-stray]: rule:stray-log-merges-into-the-local-month, rule:stray-merge-removes-the-stray
[^oplog-summary]: rule:no-section-before-its-month-settles, rule:pending-month-is-not-drift, rule:cleanup-campsite-runs-the-log-summary-catch-up, rule:log-summary-narrative-is-optional
