---
title: Forward-action backlog
read_when: Regenerating or reading `<docs_dir>/whats_next.md`
sections:
  - "§5.A"
---

# Forward-action backlog

A task reference of the documentation tree's operational schema, `<docs_dir>/AGENTS.md`. Read it only when its task applies. Section numbers keep their `<docs_dir>/AGENTS.md` meaning: a citation of a section held here, such as `docs/AGENTS.md §5.A`, resolves to this file.

## 5.A. `docs/whats_next.md` format

A single top-level file owned by the `cleanup-campsite` skill. **Body is fully regenerated on every cleanup run**; only the `dismissed:` frontmatter list persists across runs. Hand-edits to the body are blown away — same regenerative model as `docs/code/` and `catalog/skills.json`, with the deliberate divergence that `dismissed:` is hand-editable.

Frontmatter (locked schema):

```yaml
---
generated_at: <ISO 8601 UTC>
generator: cleanup          # historical value, kept stable across the skill rename
generator_version: "<semver>"
scan_findings: <int>
suggestions_open: <int>
suggestions_dismissed_carried: <int>
dismissed:
  - id: <stable id>
    dismissed_at: <YYYY-MM-DD>
    reason: "<one line>"
    dismissed_last_seen: <int>   # incremented per run until condition recurs; cleanup surfaces P3 housekeeping at >= 30
---
```

Body (locked structure):

```markdown
# What's next

_Generated <YYYY-MM-DD HH:MM> by `cleanup-campsite` v<semver>. **Body regenerated each run; only `dismissed:` persists.** Hand-edits to the body are blown away._

## Open suggestions (N)

### 1. [P1] <subject>
- **id:** `cleanup-<rule-id>-<artifact-slug>`     # stable; never includes a timestamp
- **category:** version-drift | adr-review | adr-followon | promptbook-hygiene | journal-gap | whats-next-stale | forge-hygiene | retro-cadence | template-parity | objectives | log-repair
- **severity:** P1 | P2 | P3
- **finding:** <one-to-two lines>
- **source:** scan rule `CLN-XX-N` against `<inspected paths>`
- **proposed action:** <what to do; may name a downstream skill>
- **refs:** [[wiki-link]] [[wiki-link]] ...

## Truncated (M not shown)
- `<id1>`, `<id2>`, ...

## Recently closed (since last run)
- ~~`<id>`~~ — addressed <YYYY-MM-DD>.
```

**Severity scale (locked):** P1 = decision-blocking / process-state contract violation; P2 = degrades trust or clarity; P3 = visibility-only, non-blocking.

**Caps:** ≤ 5 P1, ≤ 10 P2 per run; P3 uncapped. Surplus findings beyond a cap go under `## Truncated` (ids only). Stale-dismissal housekeeping entries (CLN-WN-1) are always P3 and sort LAST within P3.

**Sort order:** severity DESC, then stable `id` ASC for determinism.

**Dismissal lifecycle:** dismissals are permanent until removed from frontmatter. Recurring conditions stay suppressed. Rename / removal of a scan rule leaves stale dismissals in place as no-ops. A dismissal whose underlying condition hasn't recurred for >= 30 cleanup runs is surfaced as a P3 housekeeping suggestion to prune.

**Who writes what:** `cleanup-campsite` owns the body and the `generated_at` / counts / `dismissed_last_seen` fields. The user (or Claude under direct instruction) edits the `dismissed:` list — add an entry to suppress a suggestion, remove one to re-surface.
