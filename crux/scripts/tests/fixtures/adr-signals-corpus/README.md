# adr-signals-corpus

Two miniature repo roots read by `crux/scripts/tests/test_adr_signals.py`. Each
of the five signals has one fixture that trips it (`trips/`) and one that does
not (`quiet/`). Nothing here is a real record; the ids and slugs are fictitious.

| signal | `trips/` | `quiet/` |
|---|---|---|
| `amendment_fan_in` | ADR-0001 is amended by ADR-0002 and superseded-by-name in ADR-0003 | every count is 0 |
| `carve_out_count` | manifest key + doctrine roster (deduped to 1) + a 2-name `EXEMPT_THINGS` literal = 3 | no exempt key, no roster, no literal = 0 |
| `paper_only` | ADR-0001 is all `not-run-bound` (true); ADR-0003 carries no row (null) | ADR-0001 carries a `run-bound` row (false) |
| `dormancy_days` | ADR-0002 is named by a two-id log entry, so it carries a day count | ADR-0001 is named ONLY by a four-id roster entry, so it is null |
| `friction_citations` | the journal carries `### ` headings, so the verdict is `computed` | the journal carries none, so the verdict is `unmeasurable` |

`trips/bionic/adrs/archive/ADR-0009-archived-thing.md` exists so the archive
exclusion has something to exclude: it amends ADR-0001 and must contribute
nothing to that ADR's fan-in.

## Why the forge log is `forge-log.src.md`

`adr-signals.py` reads the forge log at `<root>/.claude/skills/forge-log.md`,
and `tools/sync_stage.py`'s `STAGE_IGNORE_NAMES` strips every `.claude`
directory from the staged public artifact. A committed `.claude/` under this
corpus would therefore exist in the dev checkout and vanish at release, and the
friction-citation counts asserted against it would false-fail the staged test
gate. Each root ships the body as `forge-log.src.md` instead, and
`test_adr_signals.setUpModule` materializes both roots into a temp directory
with `.claude/skills/forge-log.md` written from that file.
