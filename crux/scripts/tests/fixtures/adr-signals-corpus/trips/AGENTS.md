# AGENTS.md

A fictitious project's repo-root pointer. Nothing here is a real record.

## Two regenerative outputs — do not hand-edit

The heading above spells its count as an English word. `gate_count` therefore
locates the roster by the four-column header row below it and never by the
heading, because mining a word into a signal record is forbidden.

| Output | Source of truth | Regenerator | Drift check |
|---|---|---|---|
| `catalog/things.json` | `things/*/THING.md` frontmatter | `scripts/validate-things.py` | `validate-things.py --dry-run` |
| `docs/code/` | source docstrings | `scripts/extract-code-docs.py` | `extract-code-docs.py --dry-run` |

The blank line above ends the table, so the prose that follows it is not
counted as an enrolled row.
