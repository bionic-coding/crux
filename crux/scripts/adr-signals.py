#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""adr-signals.py — the five mechanical signals of the periodic decision review.

The script computes; it grades nothing. It emits five verdict envelopes and no
severity and no recommendation. The architect makes the judgment against the
objectives; this script only says what was measured and what could not be.

WHAT "NO MINED CONTENT" MEANS HERE, STATED EXACTLY. No prose is mined: no
journal sentence, no run-snapshot note, no ADR body line, and no doctrine rule
sentence reaches the envelope. What the envelope carries beyond counts and
dates is IDENTIFIERS — the ADR ids that key the three ADR-keyed maps, the
`EXEMPT*` variable names and script filenames named in `carve_out_count`'s
basis, and the tree-relative paths in every `basis`. Two of those three are
bounded by the grammar that produced them (`\\bADR-\\d{4}\\b` for a mention,
`EXEMPT[A-Za-z0-9_]*` for a literal); the map KEYS are not, because they are
the verbatim `id:` scalar of an ADR's frontmatter and this script reads that
scalar with `re` rather than validating it. A hostile `id:` therefore reaches
the envelope at its own length. That is the residue of this claim, named here
rather than left for a reader to discover. It is also why every value reaching
STDERR is routed through `untrusted.redact` instead: a forged line there
changes what a human reads.

DEPENDENCY FLOOR. Stdlib only, `dependencies = []`, `requires-python = ">=3.11"`.
It imports neither `summaries_projection.py` nor `doctrine_projection.py`: both
declare `requires-python = ">=3.13"` plus PyYAML, and importing either would
force that floor onto this script. It imports no `yaml` itself. THREE sibling
modules load on the import path, not two: this file imports `untrusted.py` and
`bionic_config.py` directly, and `bionic_config.py` in turn imports
`_yaml_min.py`. All three run without PyYAML — `_yaml_min.py` takes a PyYAML
fast path when one is installed and falls back to its own stdlib reader when
none is — and `untrusted.py` carries no PEP 723 header of its own. The small
amount of frontmatter this file needs — a two-key read of the tree manifest,
and `id` / `amends` / `supersedes` / `status` out of ADR frontmatter — is
parsed with `re`. No network access. It reads only committed in-repo artifacts
and writes nothing.

NOT A REGENERATOR, AND THE NAME IS PART OF THAT. This script derives no
artifact: it writes no file, and its output is an envelope on stdout that
nothing on disk is compared against. Every `crux/scripts/generate-*.py` is a
regenerator, and `RegeneratorEnrollmentTests` in
`tools/tests/test_schema_invariants.py` globs exactly that name and fails on
one missing a row in the `CLAUDE.md` roster table. Renaming this file to
`generate-adr-signals.py` would therefore redden that gate, and the repair is
not to add a roster row — there is nothing to regenerate and nothing to
drift-check. `generate-reviews-index.py`, the review's OTHER script, is the
regenerator and does carry a roster row.

THE ENVELOPE. With `--json`, stdout is one object:

    {"active_adrs": <int>, "signals": [<five records>]}

Each record carries EXACTLY the five members `signal`, `verdict`, `value`,
`basis`, `filter`, all present on every record whatever the verdict. `verdict`
is "computed" or "unmeasurable"; `value` is null when unmeasurable; `basis`
names the file(s) read; `filter` names the filter applied and is null when none
was. No record carries a `severity` field and no record carries a
`recommendation` field, now or later — that is rule:signal-verdict-envelope.

`filter` IS ONE SLOT HOLDING FOUR SHAPES, and a reader who expects only the
narrow reading ("which rows were dropped") will misread three of the five
records. The slot holds the qualification `value` cannot be read correctly
without, and across the five signals that is:

  1. AN EXCLUSION — which inputs were dropped before counting.
     `amendment_fan_in` (archived ADRs) and `dormancy_days` (bulk entries,
     with the count excluded on this run) are the narrow reading.
  2. A DEDUPLICATION — which inputs were counted once rather than twice.
     `carve_out_count`, where the manifest key and its doctrine projection are
     one surface.
  3. A VALUE-DOMAIN NOTE — what a member of `value` means. `paper_only`, where
     `null` is a third state and not a falsy `false`.
  4. THE REASON A MEASUREMENT WAS IMPOSSIBLE — mandatory on every
     `unmeasurable` record, which is the one verdict where `filter` may not be
     null. `friction_citations` when the journal carries no reflective section.

All four are "the filter applied" in the envelope contract's sense. The four
names above are for the reader, not for the JSON: no record declares which
shape it carries, and none should be added.

`active_adrs` sits at the envelope level rather than inside a record, so the
record contract stays exactly five members. The three ADR-keyed signals map an
ADR id to a per-ADR result, and each of those mappings carries exactly
`active_adrs` keys.

USAGE.
  adr-signals.py --repo-root DIR              human-readable table
  adr-signals.py --repo-root DIR --json       the JSON envelope
  adr-signals.py --repo-root DIR --today D    pin the reference date

`--today YYYY-MM-DD` is the reference date `dormancy_days` measures against and
defaults to the system date. It exists so the tests are deterministic: a
dormancy measured against a moving clock cannot be asserted.

EXIT LANES.
  0 — the envelope was emitted and every signal record is well-formed. A verdict
      of `unmeasurable` is a reported measurement state, not a failure: the
      script grades nothing, so it does not change the exit code.
  1 — the envelope could not be emitted in full because a required input was
      malformed in a way the script refuses to guess around. Partial JSON with
      an `errors` array on stdout.
  2 — environment error: `--repo-root` absent, the resolved root is not a
      crux repo root (no `<docs_dir>/adrs` directory), or `.bionic.yml` is
      malformed / names a `docs_dir` that resolves outside the repo root. A
      `--today` that is not an ISO calendar date joins the same lane through
      this script's own check, which returns 2 to match argparse's usage-error
      code. Message on stderr, empty stdout.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from untrusted import MESSAGE_LIMIT, redact  # noqa: E402

# An entry naming this many or more distinct ADR ids is a roster, not a mention.
# Measured over bionic/log.md: 1371 entries, 713 naming at least one ADR id —
# 656 name one to three, 57 name four or more, and the tail above three is flat.
BULK_ENTRY_THRESHOLD = 4

ADR_ID = re.compile(r"\bADR-\d{4}\b")
ADR_FILE = re.compile(r"^ADR-\d{4}-.*\.md$")
DOCTRINE_ROW = re.compile(r"^\|\s*((?:ADR|OBS)-\d{4})/[a-z0-9][a-z0-9-]*\s*\|")
UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
DOCTRINE_EXEMPT_HEADING = re.compile(r"^##\s+Exempt ADRs\b")
EXEMPT_ROSTER_ROW = re.compile(r"^-\s+((?:[A-Z][A-Z0-9]{1,9}-)?ADR-\d{4})\b")
LOG_HEADING = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})[^\]]*\]")
FORGE_ENTRY = re.compile(r"^## \[[^\]]+\]\s+([a-z]+)\s+\|")
# One entry per runtime's project-local skills directory, in the order the
# runtime-compatibility block names them. The forge log lives at
# `<dir>/forge-log.md` in each.
LOCAL_SKILLS_DIRS = (".claude/skills", ".agents/skills", ".opencode/skills", ".opencode/skill")
BASIS_VALUES = {"run-bound", "not-run-bound", "evidence-resolves", "evidence-missing"}
NOT_RUN_BOUND = "not-run-bound"


# --------------------------------------------------------------------------
# layout + small parsers
# --------------------------------------------------------------------------

def _load_bionic_config():
    """Import the sibling `bionic_config.py` by path and cache it."""
    key = "_bionic_config"
    module = sys.modules.get(key)
    if module is None:
        target = Path(__file__).resolve().parent / "bionic_config.py"
        spec = importlib.util.spec_from_file_location(key, target)
        if spec is None or spec.loader is None:
            raise ImportError(f"could not load spec for {target}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[key] = module
    return module


def _tree_name(root: Path) -> str:
    """The documentation tree's directory name, resolved per bionic/CLAUDE.md §14.1.

    Resolution runs through `bionic_config`, never an ad-hoc read: a local
    regex over `.bionic.yml` skips the legacy `.crux` tier and skips
    bare-directory discovery, so a zero-config `docs/` tree resolves to
    `bionic` and its real surface reads as absent.
    """
    return _load_bionic_config().resolve_tree_name(root)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _frontmatter(text: str) -> str | None:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else None


def _fm_scalar(fm: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}\s*:\s*(.*)$", fm, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip().strip("'\"") or None


def _fm_list(fm: str, key: str) -> list[str]:
    """An inline `key: [a, b]` list or a block `key:` / `- a` list."""
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest.startswith("["):
            body = rest[1:rest.rindex("]")] if "]" in rest else rest[1:]
            return [t.strip().strip("'\"") for t in body.split(",") if t.strip()]
        if rest:
            return [rest.strip("'\"")]
        out = []
        for nxt in lines[i + 1:]:
            mm = re.match(r"^\s*-\s*(.+?)\s*$", nxt)
            if not mm:
                break
            out.append(mm.group(1).strip("'\""))
        return out
    return []


def _yaml_top_value(text: str, key: str) -> str:
    """The value of a top-level YAML key: inline scalar, or a block scalar body.

    Enough to answer "is this key non-empty", which is all this script asks of
    a run snapshot's `notes`.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest and rest[0] not in "|>":
            return rest.strip("'\"")
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and not nxt.startswith((" ", "\t")):
                break
            body.append(nxt.strip())
        return "\n".join(body).strip()
    return ""


# --------------------------------------------------------------------------
# input readers
# --------------------------------------------------------------------------

def read_active_adrs(adrs_dir: Path, errors: list[dict]) -> dict[str, dict]:
    """Top-level `<docs_dir>/adrs/ADR-*.md` only; `archive/` excluded."""
    out: dict[str, dict] = {}
    for path in sorted(adrs_dir.iterdir()):
        if not path.is_file() or not ADR_FILE.match(path.name):
            continue
        fm = _frontmatter(_read(path))
        if fm is None:
            errors.append({"input": redact(path.name, quoted=False),
                           "problem": "ADR file carries no YAML frontmatter block"})
            continue
        adr_id = _fm_scalar(fm, "id")
        if not adr_id:
            errors.append({"input": redact(path.name, quoted=False),
                           "problem": "ADR frontmatter carries no `id`"})
            continue
        out[adr_id] = {
            "path": path,
            "status": _fm_scalar(fm, "status"),
            "amends": _fm_list(fm, "amends"),
            "supersedes": _fm_list(fm, "supersedes"),
        }
    return out


def read_doctrine_index(path: Path, errors: list[dict]) -> tuple[dict[str, list[str]], list[str]]:
    """Per-rule rows keyed by the source ADR/OBS id, plus the exempt roster.

    The row grammar, reverse-engineered from `bionic/adrs/doctrine/index.md`: a
    rule row is a Markdown table row whose FIRST cell is a rule handle
    (`ADR-NNNN/<slug>` or `OBS-NNNN/<slug>`) and which carries SIX CONTENT
    cells — handle, citation, rule, source ADR, disposition, basis.

    THE CODE BELOW TESTS FOR EIGHT, AND EIGHT IS CORRECT. A pipe-delimited
    Markdown row is written `| a | b | ... | f |`, so `line.split("|")` yields
    the six content cells PLUS an empty string before the leading pipe and
    another after the trailing one: six content cells, eight split parts, and
    `cells[6]` is therefore the sixth content cell, `basis`. "Fixing" the
    comparison to `!= 6` to match the prose would make the condition true for
    every real row, `continue` past all of them, and leave `rows` empty — and
    an empty `rows` raises no error: `paper_only` would map every ADR to
    `null` and the script would exit 0. That false green is why this
    paragraph exists rather than a shorter comment.

    The file also carries `_Observed evidence:_` tables and reconciliation
    tables with three content cells (five split parts); the cell-count check
    is what excludes them.
    """
    rows: dict[str, list[str]] = {}
    exempt: list[str] = []
    in_exempt = False
    for line in _read(path).splitlines():
        if line.startswith("## "):
            in_exempt = bool(DOCTRINE_EXEMPT_HEADING.match(line))
            continue
        if in_exempt:
            m = EXEMPT_ROSTER_ROW.match(line)
            if m:
                exempt.append(m.group(1))
            continue
        m = DOCTRINE_ROW.match(line)
        if not m:
            continue
        # The doctrine renderer escapes a literal pipe inside a cell as `\|`.
        # Splitting on every pipe would read nine cells and drop the row with
        # no error, so a run-bound rule would vanish and its ADR read as
        # paper-only. Split on unescaped pipes only, then unescape the cells.
        cells = [c.strip().replace("\\|", "|") for c in UNESCAPED_PIPE.split(line)]
        if len(cells) != 8:
            continue
        basis = cells[6]
        if basis not in BASIS_VALUES:
            errors.append({"input": redact(path.name, quoted=False),
                           "problem": f"rule row for {redact(m.group(1), quoted=False)} "
                                      f"carries an unknown basis value "
                                      f"{redact(basis, quoted=False)}"})
            continue
        rows.setdefault(m.group(1), []).append(basis)
    return rows, exempt


def read_governs_exempt(manifest: Path) -> list[str]:
    """A two-key stdlib read of `adr.governs_exempt` — no YAML parser."""
    lines = _read(manifest).splitlines()
    in_adr = False
    for i, line in enumerate(lines):
        if re.match(r"^adr\s*:\s*$", line):
            in_adr = True
            continue
        if in_adr and line[:1].strip():
            break
        if not in_adr:
            continue
        m = re.match(r"^\s+governs_exempt\s*:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest.startswith("["):
            body = rest[1:rest.rindex("]")] if "]" in rest else rest[1:]
            return [t.strip().strip("'\"") for t in body.split(",") if t.strip()]
        if rest:
            return [] if rest in ("~", "null") else [rest.strip("'\"")]
        out = []
        for nxt in lines[i + 1:]:
            mm = re.match(r"^\s+-\s*(.+?)\s*$", nxt)
            if not mm:
                break
            out.append(mm.group(1).strip("'\""))
        return out
    return []


def read_exempt_literals(scripts_dir: Path) -> list[tuple[str, str, list[str]]]:
    """Module-level `EXEMPT*` set/frozenset/tuple/list literals under a scripts dir.

    `ast` rather than `re`: the shipped instance is `frozenset({...})`, a call
    wrapping a set literal, which a regex reads as a set literal only by luck.
    """
    found: list[tuple[str, str, list[str]]] = []
    for path in sorted(scripts_dir.glob("*.py")):
        try:
            tree = ast.parse(_read(path))
        except (SyntaxError, ValueError):
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            else:
                continue
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) \
                    and value.func.id in {"frozenset", "set", "tuple", "list"} \
                    and len(value.args) == 1:
                value = value.args[0]
            if not isinstance(value, (ast.Set, ast.List, ast.Tuple)):
                continue
            try:
                members = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                continue
            entries = sorted({m for m in members if isinstance(m, str)})
            for name in names:
                if name.startswith("EXEMPT") and entries:
                    found.append((path.name, name, entries))
    return found


def _dated_entries(docs: Path) -> list[tuple[str, str, set[str]]]:
    """(source label, ISO date, distinct ADR ids) over every dated mention surface."""
    entries: list[tuple[str, str, set[str]]] = []

    def _split(path: Path, label: str) -> None:
        text = _read(path)
        chunks = re.split(r"(?m)^(## \[\d{4}-\d{2}-\d{2}[^\]]*\].*)$", text)
        for i in range(1, len(chunks), 2):
            head = chunks[i]
            body = head + chunks[i + 1] if i + 1 < len(chunks) else head
            m = LOG_HEADING.match(head)
            if m:
                entries.append((label, m.group(1), set(ADR_ID.findall(body))))

    log = docs / "log.md"
    if log.is_file():
        _split(log, "log.md")
    journal = docs / "journal"
    if journal.is_dir():
        for path in sorted(journal.glob("*.md")):
            if path.name != "index.md":
                _split(path, "journal")
    runs = docs / "promptbooks" / "runs"
    if runs.is_dir():
        for path in sorted(runs.glob("**/*.yaml")):
            text = _read(path)
            started = _yaml_top_value(text, "started_at")[:10]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", started):
                entries.append(("run snapshot", started, set(ADR_ID.findall(text))))
    return entries


# --------------------------------------------------------------------------
# the five signals
# --------------------------------------------------------------------------

def _record(signal: str, verdict: str, value, basis: str, filt: str | None) -> dict:
    return {"signal": signal, "verdict": verdict, "value": value,
            "basis": basis, "filter": filt}


def signal_amendment_fan_in(active: dict[str, dict], tree: str) -> dict:
    fan_in = {adr_id: 0 for adr_id in active}
    for meta in active.values():
        for target in set(meta["amends"]) | set(meta["supersedes"]):
            if target in fan_in:
                fan_in[target] += 1
    return _record(
        "amendment_fan_in", "computed", fan_in,
        f"the `amends` and `supersedes` frontmatter of the {len(active)} active ADRs "
        f"under {tree}/adrs/",
        f"archive exclusion: only top-level {tree}/adrs/ADR-*.md are read, so an "
        f"archived ADR neither carries a count nor contributes one",
    )


def signal_carve_out_count(governs_exempt: list[str], doctrine_exempt: list[str],
                           literals: list[tuple[str, str, list[str]]], tree: str,
                           scripts_present: bool = True) -> dict:
    manifest_surface = sorted(set(governs_exempt) | set(doctrine_exempt))
    literal_total = sum(len(entries) for _, _, entries in literals)
    total = len(manifest_surface) + literal_total
    # [SECURITY:S1] `name` is an identifier lifted out of a source file by
    # `ast` and `fname` is a filename off the filesystem, and both land in
    # `basis` — an envelope member the report renders. Redacted for the same
    # reason as the three sibling call sites twelve lines up in
    # `read_doctrine_index`: a value this script did not author does not reach
    # a channel unbounded. Legitimate values (`EXEMPT_THINGS`,
    # `summarize-adrs.py`) round-trip to exactly themselves.
    named = ", ".join(
        f"{redact(name, quoted=False)} in "
        f"crux/scripts/{redact(fname, quoted=False)}"
        for fname, name, _ in literals)
    return _record(
        "carve_out_count", "computed", total,
        f"`adr.governs_exempt` in {tree}/manifest.yml, the `## Exempt ADRs` roster in "
        f"{tree}/adrs/doctrine/index.md, and {len(literals)} module-level EXEMPT* "
        f"literal(s) under crux/scripts/*.py"
        + ("" if scripts_present else " (surface absent in this repo)")
        + (f" ({named})" if named else ""),
        "deduped: `adr.governs_exempt` and the doctrine index's `## Exempt ADRs` roster "
        "are ONE surface and are counted ONCE, because the roster projects that same "
        "manifest key and counting both would double-count one fact; entries are deduped "
        "within each EXEMPT* literal and not across literals, because two literals carve "
        "out two different things",
    )


def signal_paper_only(active: dict[str, dict], rows: dict[str, list[str]], tree: str) -> dict:
    """`True` when no doctrine rule row sourced from this ADR is run-bound.

    THE NAME OVERSTATES THE MEASUREMENT, so read the value and not the name.
    "Paper-only" suggests "decided but never implemented", and the doctrine
    `basis` column cannot support that claim: it records whether a rule
    RESOLVES TO EVIDENCE — a run-snapshot artifact binding — and deliberately
    makes no implementation claim at all. An ADR fully implemented in code,
    whose rules nobody bound to a run, reads `True` here. What the signal
    licenses is "go look at this ADR", which is all a signal ever licenses:
    the judgment is the architect's, in step 4 of the skill.
    """
    value: dict[str, bool | None] = {}
    for adr_id in active:
        basis_values = rows.get(adr_id)
        if not basis_values:
            value[adr_id] = None
        else:
            value[adr_id] = all(b == NOT_RUN_BOUND for b in basis_values)
    return _record(
        "paper_only", "computed", value,
        f"the per-rule `basis` column of {tree}/adrs/doctrine/index.md, joined to the "
        f"{len(active)} active ADRs by rule-handle prefix",
        "value-domain note. `true` means every doctrine rule row sourced from this ADR "
        "carries basis `not-run-bound`, which is a statement about evidence bindings and "
        "NOT a claim that the ADR is unimplemented — the basis column makes no "
        "implementation claim. And an ADR carrying NO doctrine rule row maps to null "
        "rather than to false: the "
        "doctrine index is the only surface read, so an ADR it never names is "
        "unmeasurable at the ADR level, and null is what makes those ADRs visible as a "
        "class instead of silently reading as not-paper-only; the null entries are the "
        "rowless cohort and are enumerated on their own Coverage line, so this record's "
        "`computed` verdict is not a claim about them",
    )


def signal_dormancy_days(active: dict[str, dict], entries, today: dt.date, tree: str) -> dict:
    excluded = sum(1 for _l, _d, ids in entries if len(ids) >= BULK_ENTRY_THRESHOLD)
    newest: dict[str, str] = {}
    for _label, date, ids in entries:
        if len(ids) >= BULK_ENTRY_THRESHOLD:
            continue
        for adr_id in ids:
            if adr_id in active and date > newest.get(adr_id, ""):
                newest[adr_id] = date
    value: dict[str, int | None] = {}
    for adr_id in active:
        date = newest.get(adr_id)
        if date is None:
            value[adr_id] = None
        else:
            value[adr_id] = (today - dt.date.fromisoformat(date)).days
    return _record(
        "dormancy_days", "computed", value,
        f"dated entries in {tree}/log.md, the monthly files under {tree}/journal/, and the "
        f"run snapshots under {tree}/promptbooks/runs/, measured against {today.isoformat()}",
        f"an entry naming {BULK_ENTRY_THRESHOLD} or more distinct ADR ids is a roster, not "
        f"a mention, and is excluded; {excluded} of {len(entries)} dated entries were "
        f"excluded on this run. The threshold is a judgment: the measured tail above "
        f"three has no gap.",
    )


def signal_friction_citations(root: Path, docs: Path, tree: str) -> dict:
    journal = docs / "journal"
    journal_files = sorted(p for p in journal.glob("*.md")
                           if p.name != "index.md") if journal.is_dir() else []
    headings = sum(
        sum(1 for line in _read(p).splitlines() if line.startswith("### "))
        for p in journal_files
    )

    runs = docs / "promptbooks" / "runs"
    run_files = sorted(runs.glob("**/*.yaml")) if runs.is_dir() else []
    with_notes_key, notes = 0, 0
    for path in run_files:
        text = _read(path)
        if re.search(r"(?m)^notes\s*:", text):
            with_notes_key += 1
            if _yaml_top_value(text, "notes"):
                notes += 1

    whats_next = docs / "whats_next.md"
    dismissals, has_dismissed_block = 0, False
    if whats_next.is_file():
        fm = _frontmatter(_read(whats_next)) or ""
        idx = fm.find("dismissed:")
        if idx >= 0:
            has_dismissed_block = True
            block = fm[idx:]
            for entry in re.split(r"(?m)^\s*-\s*id:", block)[1:]:
                if ADR_ID.search(entry):
                    dismissals += 1

    # forge-skill writes its log under the runtime's local skills directory:
    # `.claude/skills` in Claude Code, `.agents/skills` in Codex, and
    # `.opencode/skills` in OpenCode, which also reads the singular
    # `.opencode/skill`. A tree driven from more than one runtime carries more
    # than one log, so the leg is a union over every log present.
    forge_logs = [root / rel / "forge-log.md" for rel in LOCAL_SKILLS_DIRS]
    present_logs = [p for p in forge_logs if p.is_file()]
    forge, has_forge_log = 0, bool(present_logs)
    for forge_log in present_logs:
        for line in _read(forge_log).splitlines():
            m = FORGE_ENTRY.match(line)
            if m and m.group(1) in {"fallback", "escalated"}:
                forge += 1

    legs = [
        (f"journal reflective sections (`### ` headings across {tree}/journal/*.md)",
         headings > 0, headings),
        (f"run-snapshot notes ({tree}/promptbooks/runs/**/*.yaml; {with_notes_key} snapshot(s) "
         f"carry a `notes` key, {notes} of them non-empty)", bool(run_files), notes),
        (f"ADR references in {tree}/whats_next.md dismissals", has_dismissed_block, dismissals),
        ("fallback-or-escalated entries in forge-log.md under the local skills directory "
         "(" + ", ".join(LOCAL_SKILLS_DIRS) + ")", has_forge_log, forge),
    ]
    present = "; ".join(f"{name} — {'present' if ok else 'absent'}" for name, ok, _ in legs)
    basis = f"a union over four legs: {present}"

    if headings == 0:
        return _record(
            "friction_citations", "unmeasurable", None, basis,
            f"the journal-reflective-section leg has no grammar at all: zero `### ` headings "
            f"exist across the {len(journal_files)} file(s) under {tree}/journal/, so a `0` "
            f"meaning \"no surface exists\" would be indistinguishable from a `0` meaning "
            f"\"no friction found\"",
        )
    return _record("friction_citations", "computed", sum(n for _, _, n in legs), basis, None)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _render_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        sample = ", ".join(f"{k}={json.dumps(v)}" for k, v in list(value.items())[:3])
        more = len(value) - 3
        return f"{len(value)} entries" + (f"; {sample}" + (f", +{more} more" if more > 0 else "")
                                          if sample else "")
    return json.dumps(value)


def render_table(envelope: dict) -> str:
    out = [f"active_adrs: {envelope['active_adrs']}", ""]
    for rec in envelope["signals"]:
        out.append(f"{rec['signal']}")
        out.append(f"  verdict: {rec['verdict']}")
        out.append(f"  value:   {_render_value(rec['value'])}")
        out.append(f"  basis:   {rec['basis']}")
        out.append(f"  filter:  {rec['filter'] if rec['filter'] is not None else 'null'}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def build(root: Path, today: dt.date) -> tuple[dict, list[dict]]:
    tree = _tree_name(root)
    docs = root / tree
    adrs = docs / "adrs"
    errors: list[dict] = []

    active = read_active_adrs(adrs, errors)

    doctrine = adrs / "doctrine" / "index.md"
    if doctrine.is_file():
        rows, doctrine_exempt = read_doctrine_index(doctrine, errors)
    else:
        rows, doctrine_exempt = {}, []
        errors.append({"input": f"{tree}/adrs/doctrine/index.md",
                       "problem": "the doctrine index is missing; paper_only and "
                                  "carve_out_count cannot be computed from it"})

    manifest = docs / "manifest.yml"
    if manifest.is_file():
        governs_exempt = read_governs_exempt(manifest)
    else:
        governs_exempt = []
        errors.append({"input": f"{tree}/manifest.yml",
                       "problem": "the tree manifest is missing; `adr.governs_exempt` "
                                  "cannot be read"})

    scripts_dir = root / "crux" / "scripts"
    scripts_present = scripts_dir.is_dir()
    literals = read_exempt_literals(scripts_dir)
    entries = _dated_entries(docs)

    envelope = {
        "active_adrs": len(active),
        "signals": [
            signal_amendment_fan_in(active, tree),
            signal_carve_out_count(governs_exempt, doctrine_exempt, literals, tree,
                                   scripts_present),
            signal_paper_only(active, rows, tree),
            signal_dormancy_days(active, entries, today, tree),
            signal_friction_citations(root, docs, tree),
        ],
    }
    return envelope, errors


def _environment_error(exc: Exception) -> int:
    """Report an environment failure on stderr and return the exit-2 code.

    [SECURITY:S1] The composed message is redacted at MESSAGE_LIMIT rather
    than LIMIT: its untrusted parts were already bounded where they were
    interpolated, and the value bound would cut a real two-sentence
    containment refusal in half. What is still wanted here is the
    control-character replacement, so an unrouted path cannot forge a line on
    stderr. Shared posture with generate-reviews-index.py — same lane, same
    message shape, each naming its own script. Change one, change all.
    """
    sys.stderr.write(
        f"adr-signals: {type(exc).__name__}: "
        f"{redact(exc, quoted=False, limit=MESSAGE_LIMIT)}\n")
    return 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compute the five mechanical signals of the decision review.")
    ap.add_argument("--repo-root", required=True,
                    help="the repository root holding the documentation tree")
    ap.add_argument("--json", action="store_true",
                    help="emit the JSON envelope on stdout instead of the table")
    ap.add_argument("--today", default=None, metavar="YYYY-MM-DD",
                    help="reference date for dormancy_days (default: the system date)")
    args = ap.parse_args(argv)

    root = Path(args.repo_root).resolve()
    try:
        # INSIDE the try. `_tree_name` reads `.bionic.yml` and raises
        # `BionicConfigError` on a malformed one or on a `docs_dir` that
        # resolves outside the repo root. Outside the try it escaped as an
        # uncaught traceback — exit 1 with EMPTY stdout, which is neither
        # documented lane: exit 1 carries partial JSON on stdout and exit 2
        # carries a message. The traceback also printed absolute filesystem
        # paths and the raw `docs_dir` through an unrouted `{value!r}`.
        # Mirrors generate-reviews-index.py's handler.
        tree = _tree_name(root)
    except Exception as exc:  # unreadable config, bad encoding — env error
        return _environment_error(exc)
    adrs = root / tree / "adrs"
    if not adrs.is_dir():
        sys.stderr.write(
            f"adr-signals: not a crux repo root — no adrs directory at "
            f"{redact(str(adrs), quoted=False)}\n")
        return 2

    if args.today is None:
        today = dt.date.today()
    else:
        try:
            today = dt.date.fromisoformat(args.today)
        except ValueError:
            sys.stderr.write(
                f"adr-signals: --today must be an ISO calendar date, got "
                f"{redact(args.today, quoted=False)}\n")
            return 2

    try:
        # `build` calls `_tree_name` a second time, so it carries the same
        # lane; an unreadable ADR or a bad encoding lands here too.
        envelope, errors = build(root, today)
    except Exception as exc:
        return _environment_error(exc)
    if errors:
        payload = dict(envelope)
        payload["errors"] = errors
        print(json.dumps(payload, sort_keys=True))
        return 1
    if args.json:
        print(json.dumps(envelope, sort_keys=True))
    else:
        sys.stdout.write(render_table(envelope))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
