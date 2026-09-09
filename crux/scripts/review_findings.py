"""review_findings.py — the decision-review finding grammar, in ONE place.

WHAT IS IN HERE. The parse of one decision-review report into three structures
— definitions, lifecycle records, and lifecycle notes — plus the three
questions a reader asks across dates: does this finding still stand, how many
of a report's own findings sit in each standing, and how many of a report's
records name a finding some other report defined. The reviews-index
regenerator is the consumer; the reader that writes a report is the other.

WHAT IS DELIBERATELY NOT IN HERE.

  * I/O OF ANY KIND, AFTER IMPORT. No `open`, no `Path.exists`, no `os.stat`
    in any function here. (Import time is the one exception, and it is not an
    exception to the property: the `sys.path` insert and the two sibling
    imports below run once, read no report, and touch no hand-edited file.)
    The module takes text and returns structures. That is a supply-chain property (the
    parser of a hand-editable report reaches for nothing) and a testability
    property (every lane is drivable from a string). The one question that
    needs the filesystem — does a `resolved` record's locator name a surface
    that exists — is asked through an INJECTED probe, `locator_exists`, which
    the caller supplies already bounded to the repository root.
  * ANY GRADE. `validate_structure` checks the SHAPE of a report. Whether a
    finding is right, whether a resolution really enacted it, whether a
    dispute is fair — none of that is a question this module has an opinion
    about, and the decision behind it says so explicitly.

REFUSALS ARE DOCUMENT-LANE REFUSALS. One exception type, `ReviewFindingsError`,
carrying a `problem` string. The caller turns it into exit 1 with a
`validation_errors` entry, the shape `generate-reviews-index.py` already
emits. Nothing here raises `OSError`: a hand-edited report is a fact about the
corpus a human repairs, never an environment failure. And nothing here
truncates a value into admission — a locator outside the grammar is refused,
never trimmed until it fits.

EVERY QUOTED-BACK VALUE IS UNTRUSTED. A report is hand-editable content, and
every cell this module refuses reaches a JSON envelope and stderr through the
caller. All of them render through `untrusted.redact`, which bounds the
rendered length and replaces every unprintable character. A record lives in a
table cell and no fence stands inside a table cell, so the fencing half of the
usual mined-value rule is unavailable here and the bounding half carries the
whole load.

THE TWO GRAMMARS, AND THE KEY THAT TELLS THEM APART. `report_grammar` is the
discriminator, and `lifecycle` is its one recognised value.

  * ABSENT. The report reads under the FROZEN LEGACY COUNTING RULE: `raised`
    is the number of distinct `adr-review-<slug>` tokens below the
    frontmatter, exactly as `generate-reviews-index.py` counted before this
    module existed, so the two historical reports keep rendering 6 and 5.
    `LEGACY_TOKEN` is that pattern, spelled ONCE, here. The regenerator no
    longer carries a copy: it imports this module, and
    `test_the_legacy_token_regex_has_exactly_one_copy` reads the regenerator's
    source and fails on a second spelling.
  * ABSENT ON A REPORT DATED AFTER 2026-09-08. Refused. The boundary is a day
    later than the six-section cohort's, because the newer of the two
    historical reports is dated 2026-09-08 and both must read as legacy.
  * PRESENT WITH ANY OTHER VALUE. Refused.

Neither absence nor an unrecognised value is ever defaulted in either
direction, and historical Coverage prose is never read as a confirmed
lifecycle event: a legacy report yields zero records, full stop.

DEFINITION VERSUS REFERENCE. A finding DEFINITION is a `### `-level heading
under one of the four finding sections whose heading text carries exactly one
id. Zero ids, or two or more, is refused. A heading deeper than `### ` inside
an entry is neither a definition nor a refusal. Every other occurrence of an
id anywhere — the summary table, a Coverage line, a fenced block, a lifecycle
record, a note — is a REFERENCE and defines nothing. Under THIS grammar,
content inside a fenced block never defines anything and never records
anything; fence state comes from `md_fences`, never from a local scanner.

The legacy path is deliberately NOT fence-aware, and saying so here is the
point: its count is FROZEN, so it must reproduce what
`generate-reviews-index.py` counted before this module existed — a bare
`findall` over the whole body, fences included. A fenced id on a legacy report
is therefore counted, and `_definitions_across` claims it as that report's
definition. Making the legacy path fence-aware would move a historical
report's number, which is the one thing the freeze exists to prevent.

Stdlib only, and imported through the `__file__`-derived `sys.path` insert the
scripts beside it already use — the one filesystem-adjacent act in this file,
and it happens at import, before any report is read.
"""

from __future__ import annotations

import datetime
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from md_fences import closes_fence, fence_marker, split_lines  # noqa: E402
from untrusted import redact  # noqa: E402

#: The one recognised value of the `report_grammar` discriminator.
LIFECYCLE = "lifecycle"

#: The last date on which a report may carry no discriminator. A report dated
#: after this and carrying none is refused.
LEGACY_BOUNDARY = "2026-09-08"

#: The FROZEN legacy counting pattern, and the ONLY spelling of it in the
#: tree. `generate-reviews-index.py` used to define a second copy of it; a
#: comparison across two copies can find a divergence but never a shared
#: error, so the copy was deleted and the regenerator imports this module
#: instead. `test_the_legacy_token_regex_has_exactly_one_copy` reads the
#: regenerator's source and fails on a redefinition, on a missing import, or
#: on this pattern appearing there at all — the pattern cannot drift if it
#: exists once. That test names the deleted constant; this module does not,
#: so a reader here is never sent looking for a name that resolves to nothing.
LEGACY_TOKEN = re.compile(r"\badr-review-[a-z0-9]+(?:-[a-z0-9]+)*\b")

#: A finding id in FULL FORM. A bare slug is not one.
FINDING_ID = re.compile(r"\Aadr-review-[a-z0-9]+(?:-[a-z0-9]+)*\Z")

#: A lifecycle note, recognised on a line inside a finding entry. The note's
#: finding is the id of the `### ` definition heading whose entry it sits in.
#:
#: [SECURITY:S1] The ordinal is the same BOUNDED ASCII digit run `_POSITIVE_INT`
#: admits, and for the same two reasons. `\d` matches every Unicode decimal
#: digit in a `str` pattern, so `pass \u0662` parsed and reached `int()`; and an
#: unbounded run put its whole length into a rendered refusal. A line outside
#: this grammar is not a note at all — it is prose, and the parser never reads
#: prose as an event.
NOTE_MARKER = re.compile(
    r"^[ \t]*-[ \t]+\*\*(re-verified|resolved|disputed), "
    r"pass ([1-9][0-9]{0,3})\*\*")

#: The note marker's SHAPE, with the ordinal left free. A line that carries the
#: shape but misses `NOTE_MARKER` is a note whose ordinal is out of grammar —
#: `pass 10000`, `pass 0`, `pass \u0662` — and it is REFUSED naming the line
#: rather than degrading to prose. Degrading was the silent failure: a pass that
#: believed it wrote a note wrote nothing a reader or the pairing check sees.
_NOTE_MARKER_SHAPE = re.compile(
    r"^[ \t]*-[ \t]+\*\*(?:re-verified|resolved|disputed), "
    r"pass ([^*]{0,40})\*\*")

#: The evidence locator: a reference, never a quotation. Pipe, newline and
#: carriage return are excluded because the value lives in a table cell;
#: backtick because no fence stands inside one; `[` and `^` because they are
#: the first characters of a wiki-link and of a footnote marker. [SECURITY:S1]
#: The C0 and C1 control ranges are excluded whole, so a value that reaches
#: stderr cannot carry an escape sequence or forge a line; `\r` and `\n` stay
#: named above for the reader, though the ranges already cover them.
#:
#: A locator names a SURFACE and carries no `:line` suffix. It is not the
#: `path:line-range` grammar `observation_evidence.EVIDENCE_RE` declares for an
#: observation's evidence, and the two must not be confused: this one answers
#: "does that surface exist", never "what does line 40 say".
#:
#: 200 is longer than the longest repo-relative path this repository ships, so
#: a real locator is never refused for its length. The RENDERING bound is a
#: different number and a smaller one: every refusal below renders the value
#: through `redact`, whose default `untrusted.LIMIT` is 120 characters, so a
#: refused locator longer than that renders truncated and carries the
#: truncation note. That is the channel bound working, not a defect — the
#: grammar refuses an out-of-grammar locator rather than trimming it into
#: admission, and the refusal names as much of it as the channel allows.
LOCATOR_LIMIT = 200
LOCATOR = re.compile(r"^[^|\r\n`\[\^\x00-\x1f\x7f-\x9f]{1,%d}$" % LOCATOR_LIMIT)

#: The written event kinds. `raised` is implicit — the definition itself — and
#: is never written as a record.
RECORD_KINDS = ("re-verified", "resolved", "disputed")

#: The note kinds that must pair with a record of the same finding, kind and
#: pass. A `resolved` note is recognised and is not bound: the decision names
#: the disputed note and the re-verification note, and this module implements
#: what it names rather than a stricter reading of its own.
PAIRED_NOTE_KINDS = ("re-verified", "disputed")

#: The four standings, in the order a renderer shows them.
STANDINGS = ("open", "resolved", "disputed", "unknown")

#: The four finding sections, lowercased for comparison.
FINDING_SECTIONS = ("propose", "amend", "repair", "revoke")

#: The header row that identifies the summary table, and the one that
#: identifies the lifecycle record table. Each table is found BY ITS HEADER
#: ROW and never by position — the per-goal coverage matrix sits under the
#: same `## Coverage` heading and the two must never merge.
SUMMARY_HEADER = ("finding id", "section", "objective", "proposed act", "size")
RECORD_HEADER = ("source report date", "finding id", "pass", "event", "locator")

_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$")
_DELIMITER_CELL = re.compile(r"^:?-{3,}:?$")
#: [SECURITY:S1] `[0-9]`, never `\d`: `\d` matches every Unicode decimal digit
#: in a `str` pattern, so a date spelled in Arabic-Indic digits matched a
#: pattern whose whole job is to say "this is an ISO calendar date".
_ISO_DATE = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
#: A pass ordinal: ASCII digits only, no leading zero, and a BOUNDED run.
#: [SECURITY:S1] `[0-9]*` is unbounded, so a 4000-digit cell parsed, reached
#: `int()`, and rendered 4000 characters into a refusal that `redact` never saw
#: because the value was no longer a string. Four digits is far past any real
#: pass ordinal, and the refusal below still renders the raw cell through
#: `redact` rather than the parsed int.
_POSITIVE_INT = re.compile(r"\A[1-9][0-9]{0,3}\Z")

#: How many ids a set-difference refusal names before it stops counting.
#: [SECURITY:S1] A hand-editable summary table carries as many rows as its
#: author typed; joining the whole difference put the entire table into one
#: error string, on stdout and on stderr both.
_ID_LIST_LIMIT = 10


def _join_ids(ids: Sequence[str]) -> str:
    """`ids`, redacted and joined, capped at `_ID_LIST_LIMIT` plus a count."""
    shown = ", ".join(redact(fid) for fid in ids[:_ID_LIST_LIMIT])
    if len(ids) > _ID_LIST_LIMIT:
        shown += f", and {len(ids) - _ID_LIST_LIMIT} more"
    return shown


class ReviewFindingsError(Exception):
    """A report this module refuses to read — a document-lane validation error.

    Carries the problem separately from the message so a caller can build a
    `{"file", "error"}` entry without reparsing a string. Every untrusted part
    of `problem` is redacted at the raise site, where the surrounding prose
    says which value is the report's.
    """

    def __init__(self, problem: str) -> None:
        super().__init__(problem)
        self.problem = problem


@dataclass(frozen=True)
class Definition:
    """One finding, defined by a `### ` heading under a finding section."""

    finding_id: str
    section: str
    date: str
    line: int


@dataclass(frozen=True)
class Record:
    """One lifecycle record: five fields, plus where it was written.

    `source_date` is the date of the report that DEFINED the finding, and it
    is the only date a record carries of its own. `report_date` is the
    containing report's date — the record's own position in the stream.
    """

    source_date: str
    finding_id: str
    pass_ordinal: int
    event: str
    locator: str
    report_date: str
    line: int


@dataclass(frozen=True)
class Note:
    """One lifecycle note, and the entry it sits in."""

    finding_id: str
    kind: str
    pass_ordinal: int
    line: int


@dataclass(frozen=True)
class ParsedReport:
    """One report, read under whichever grammar its discriminator selects.

    On a legacy report `definitions`, `records`, `notes` and `summary_row_ids`
    are all empty, `legacy_ids` holds the frozen token set, and `raised` is its
    size. On a lifecycle report `legacy_ids` is empty and `raised` is the
    number of definitions.
    """

    date: str
    grammar: str | None
    is_legacy: bool
    definitions: tuple[Definition, ...]
    records: tuple[Record, ...]
    notes: tuple[Note, ...]
    summary_row_ids: tuple[str, ...]
    legacy_ids: frozenset[str]
    raised: int


# ── reading one report ────────────────────────────────────────────────────


def _calendar_date(value: str, subject: str) -> str:
    """`value`, refused unless it is an ISO calendar date that exists."""
    if not _ISO_DATE.match(value or ""):
        raise ReviewFindingsError(
            f"{subject} is {redact(value)}, which is not an ISO calendar date "
            "of the form YYYY-MM-DD")
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise ReviewFindingsError(
            f"{subject} is {redact(value)}, which is not a calendar date that "
            "exists") from None
    return value


def _frontmatter_scalar(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}[ \t]*:[ \t]*(.*)$", frontmatter or "",
                      re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'").strip()


def _cells(line: str) -> list[str] | None:
    """The stripped cells of a Markdown table row, or None for a non-row."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    inner = stripped[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def _is_delimiter(cells: Sequence[str]) -> bool:
    return bool(cells) and all(_DELIMITER_CELL.match(cell) for cell in cells)


def _header_matches(cells: Sequence[str], header: Sequence[str]) -> bool:
    return tuple(cell.strip().lower() for cell in cells) == tuple(header)


def _content_lines(body: str, line_offset: int):
    """Every line of `body` that stands OUTSIDE a fenced block, with its number.

    Fence state comes from `md_fences`, so an opener's info string, the indent
    bound, the two fence characters and the closer's run length are all decided
    in one place. A marker line — opener or closer — is itself content the
    grammar never reads, so neither is yielded.
    """
    opener: tuple[str, int] | None = None
    for index, line in enumerate(split_lines(body), start=1):
        marker = fence_marker(line)
        if opener is not None:
            if closes_fence(marker, opener):
                opener = None
            continue
        if marker is not None:
            opener = (marker[0], marker[1])
            continue
        yield index + line_offset, line


def _refuse_escaping_shape(locator: str, line: int) -> None:
    """Refuse the three locator shapes that reach outside the repository root.

    Outcome 2 refuses an absolute path, a `~`-prefixed path and a `..`
    traversal without qualifying the event kind, and the skill and the template
    both promise it. Those refusals used to live only in the injected existence
    probe, which is asked about a `resolved` record alone — so a `re-verified`
    record naming `/etc/passwd` was admitted and the promise was false for two
    of the three kinds. The check moves here, where every record passes.

    A PURE STRING check: `Path(...).parts` parses, it does not stat. This
    module still touches the filesystem nowhere after import.
    """
    if locator.startswith("~") or PurePosixPath(locator).is_absolute() \
            or PureWindowsPath(locator).is_absolute():
        raise ReviewFindingsError(
            f"the locator of the lifecycle record at line {line} is "
            f"{redact(locator)}, which is an absolute or home-relative path; a "
            "locator resolves only inside the repository root, and such a path "
            "is refused rather than followed")
    # BOTH flavours, as the absolute check above already does: `PurePosixPath`
    # treats `\` as an ordinary character, so `a\..\b` is one component to it
    # and its `..` went unseen — the same value is three components on Windows,
    # where it traverses.
    if ".." in PurePosixPath(locator).parts \
            or ".." in PureWindowsPath(locator).parts:
        raise ReviewFindingsError(
            f"the locator of the lifecycle record at line {line} is "
            f"{redact(locator)}, which traverses out of the repository root "
            "with `..`; it is refused rather than followed")


def _record_from_row(cells: Sequence[str], report_date: str,
                     line: int) -> Record:
    if len(cells) != len(RECORD_HEADER):
        raise ReviewFindingsError(
            f"the lifecycle record at line {line} carries {len(cells)} cells; "
            f"a record row carries {len(RECORD_HEADER)} cells — "
            + ", ".join(RECORD_HEADER))
    raw_date, raw_id, raw_pass, raw_event, raw_locator = cells

    source_date = _calendar_date(
        raw_date, f"the source report date of the lifecycle record at line {line}")

    # ONE BACKTICK RULE. Backticks are Markdown formatting on a closed-
    # vocabulary cell, and a reader who backticks the id cell backticks the two
    # beside it; they are stripped before the vocabulary check. The LOCATOR
    # cell is the deliberate exception and is NOT stripped — a backtick run
    # terminates a fence, so the grammar refuses the character outright in the
    # one free field.
    finding_id = raw_id.strip().strip("`").strip()
    raw_pass = raw_pass.strip().strip("`").strip()
    raw_event = raw_event.strip().strip("`").strip()

    if not FINDING_ID.match(finding_id):
        raise ReviewFindingsError(
            f"the lifecycle record at line {line} names {redact(finding_id)}, "
            "which is not a finding id in full form (`adr-review-<slug>`)")

    if not _POSITIVE_INT.match(raw_pass):
        raise ReviewFindingsError(
            f"the pass of the lifecycle record at line {line} is "
            f"{redact(raw_pass)}, which is not a pass ordinal: 1 to 4 ASCII "
            "digits with no leading zero")

    if raw_event == "raised":
        raise ReviewFindingsError(
            f"the lifecycle record at line {line} carries the event "
            f"{redact(raw_event)}; `raised` is the definition itself: it is "
            "dated by the report that carries the definition, so a record "
            "claiming it would date the definition a second time, and it is "
            "never written as a record")
    if raw_event not in RECORD_KINDS:
        raise ReviewFindingsError(
            f"the lifecycle record at line {line} carries the event "
            f"{redact(raw_event)}, which is outside the closed set "
            + " | ".join(RECORD_KINDS))

    if not LOCATOR.match(raw_locator):
        raise ReviewFindingsError(
            f"the locator of the lifecycle record at line {line} is "
            f"{redact(raw_locator)}, which is outside the locator grammar: 1 to "
            f"{LOCATOR_LIMIT} characters carrying no pipe, line break, "
            "backtick, control character, `[` or `^`")
    _refuse_escaping_shape(raw_locator, line)

    return Record(source_date=source_date, finding_id=finding_id,
                  pass_ordinal=int(raw_pass), event=raw_event,
                  locator=raw_locator, report_date=report_date, line=line)


def parse_report(*, date: str, frontmatter: str, body: str,
                 line_offset: int = 0) -> ParsedReport:
    """One report, read under the grammar its discriminator selects.

    `frontmatter` is the raw text between the `---` delimiters and `body` is
    everything below them. `line_offset` is added to every reported line
    number, so a caller that read a file hands back file-relative lines by
    passing the frontmatter's own line count; the default reports lines
    relative to the body.
    """
    date = _calendar_date(date, "the report date")
    grammar = _frontmatter_scalar(frontmatter, "report_grammar")

    if grammar is None or grammar == "":
        if date > LEGACY_BOUNDARY:
            raise ReviewFindingsError(
                f"the {date} report carries no `report_grammar` key; a report "
                f"dated after {LEGACY_BOUNDARY} declares its grammar, and the "
                "absent key is never defaulted")
        ids = frozenset(LEGACY_TOKEN.findall(body))
        return ParsedReport(date=date, grammar=None, is_legacy=True,
                            definitions=(), records=(), notes=(),
                            summary_row_ids=(), legacy_ids=ids,
                            raised=len(ids))

    if grammar != LIFECYCLE:
        raise ReviewFindingsError(
            f"the {date} report declares `report_grammar` {redact(grammar)}, "
            f"which is outside the recognised set ({LIFECYCLE}); an "
            "unrecognised value is never defaulted")

    definitions: list[Definition] = []
    defined_at: dict[str, int] = {}
    records: list[Record] = []
    notes: list[Note] = []
    summary_row_ids: list[str] = []

    section = ""
    current: Definition | None = None
    seen_definition_section = False
    summary_table_seen = False
    record_table_seen = False
    reading: str | None = None   # "summary" | "record" | None

    for line, text in _content_lines(body, line_offset):
        heading = _HEADING.match(text)
        if heading:
            reading = None
            level, title = len(heading.group(1)), heading.group(2)
            if level <= 2:
                section = title.strip().lower()
                current = None
                if section in FINDING_SECTIONS:
                    seen_definition_section = True
                continue
            if level == 3:
                current = None
                if section not in FINDING_SECTIONS:
                    continue
                found = LEGACY_TOKEN.findall(title)
                if len(found) != 1:
                    raise ReviewFindingsError(
                        f"the `### ` heading at line {line} under `## "
                        f"{section}` carries "
                        + ("no finding id" if not found
                           else f"{len(found)} finding ids")
                        + "; a finding definition carries exactly one")
                current = Definition(finding_id=found[0], section=section,
                                     date=date, line=line)
                # A DICT lookup rather than a rescan of every definition read
                # so far: the rescan was quadratic in a hand-editable file's
                # definition count.
                earlier_line = defined_at.get(current.finding_id)
                if earlier_line is not None:
                    raise ReviewFindingsError(
                        f"the finding id {redact(current.finding_id)} is "
                        f"defined twice in the {date} report, at lines "
                        f"{earlier_line} and {line}; a slug defined twice "
                        "is refused rather than disambiguated")
                defined_at[current.finding_id] = line
                definitions.append(current)
            continue

        cells = _cells(text)
        if cells is None:
            reading = None
            if current is not None:
                note = NOTE_MARKER.match(text)
                if note:
                    notes.append(Note(finding_id=current.finding_id,
                                      kind=note.group(1),
                                      pass_ordinal=int(note.group(2)),
                                      line=line))
                else:
                    near = _NOTE_MARKER_SHAPE.match(text)
                    if near:
                        raise ReviewFindingsError(
                            f"the note at line {line} carries the pass ordinal "
                            f"{redact(near.group(1))}, which is outside the "
                            "ordinal grammar: 1 to 4 ASCII digits with no "
                            "leading zero; a note the parser cannot read is "
                            "refused rather than read as prose")
            continue

        if _header_matches(cells, SUMMARY_HEADER):
            if summary_table_seen:
                raise ReviewFindingsError(
                    f"the {date} report carries a second summary table at line "
                    f"{line}; the report carries one summary table, between "
                    "the title and `## Propose`")
            if seen_definition_section:
                raise ReviewFindingsError(
                    f"the summary table at line {line} stands after a finding "
                    "section; the summary table sits between the title and "
                    "`## Propose`")
            summary_table_seen = True
            reading = "summary"
            continue

        if _header_matches(cells, RECORD_HEADER):
            if record_table_seen:
                raise ReviewFindingsError(
                    f"the {date} report carries a second lifecycle record "
                    f"table at line {line}; the records live in one table "
                    "under `## Coverage`")
            if section != "coverage":
                raise ReviewFindingsError(
                    f"the lifecycle record table at line {line} stands outside "
                    "`## Coverage`; the records live in one table under that "
                    "heading")
            record_table_seen = True
            reading = "record"
            continue

        if _is_delimiter(cells):
            continue

        if reading is None:
            # INTEGRITY. The record table is found BY ITS HEADER ROW, so a
            # mistyped header left every row beneath it owned by nothing and
            # skipped in silence: a pass that believed it recorded a
            # resolution recorded nothing, and the index computed the finding
            # open. A five-cell, ISO-dated row under `## Coverage` is a record
            # row whose table went missing, and that is a refusal rather than
            # a drop.
            if (section == "coverage" and len(cells) == len(RECORD_HEADER)
                    and _ISO_DATE.match(cells[0].strip().strip("`").strip())):
                raise ReviewFindingsError(
                    f"the row at line {line} under `## Coverage` carries "
                    f"{len(RECORD_HEADER)} cells and an ISO date in the first, "
                    "and no table owns it; the lifecycle record table is found "
                    "by its header row — "
                    + " | ".join(RECORD_HEADER)
                    + " — so a mistyped header drops every row beneath it")
            continue

        if reading == "summary":
            found = LEGACY_TOKEN.findall(cells[0])
            if len(found) != 1:
                raise ReviewFindingsError(
                    f"the summary row at line {line} carries "
                    + ("no finding id" if not found
                       else f"{len(found)} finding ids")
                    + " in its first cell; one row names one finding")
            summary_row_ids.append(found[0])
            continue

        records.append(_record_from_row(cells, date, line))

    return ParsedReport(date=date, grammar=LIFECYCLE, is_legacy=False,
                        definitions=tuple(definitions),
                        records=tuple(records), notes=tuple(notes),
                        summary_row_ids=tuple(summary_row_ids),
                        legacy_ids=frozenset(), raised=len(definitions))


# ── checking one report's shape ───────────────────────────────────────────


def validate_structure(report: ParsedReport) -> None:
    """The summary-table postcondition and the note-pairing requirement.

    A STRUCTURAL check, deliberately distinct from any judgement about whether
    a finding is right. Returns None; raises `ReviewFindingsError` on a
    disagreement. A legacy report is outside both rules and passes.
    """
    if report.is_legacy:
        return None

    seen: set[str] = set()
    repeated = sorted({fid for fid in report.summary_row_ids
                       if fid in seen or seen.add(fid)})
    if repeated:
        raise ReviewFindingsError(
            f"the {report.date} report's summary-table row ids are not "
            "pairwise distinct: " + _join_ids(repeated))

    defined = {definition.finding_id for definition in report.definitions}
    rows = set(report.summary_row_ids)
    if rows != defined:
        missing = sorted(defined - rows)
        extra = sorted(rows - defined)
        parts = []
        if extra:
            parts.append("in the summary table and defined by no finding "
                         "section: " + _join_ids(extra))
        if missing:
            parts.append("defined by a finding section and absent from the "
                         "summary table: " + _join_ids(missing))
        raise ReviewFindingsError(
            f"the {report.date} report's summary-table row id set does not "
            "equal the set of ids its finding sections define — "
            + "; ".join(parts))

    paired = {(record.finding_id, record.event, record.pass_ordinal)
              for record in report.records}
    for note in report.notes:
        if note.kind not in PAIRED_NOTE_KINDS:
            continue
        if (note.finding_id, note.kind, note.pass_ordinal) not in paired:
            raise ReviewFindingsError(
                f"the {note.kind} note at line {note.line} of the "
                f"{report.date} report names {redact(note.finding_id)} and "
                f"pairs with no lifecycle record of that finding, that kind "
                f"and pass {redact(str(note.pass_ordinal), quoted=False)}; the "
                "note's prose is not quoted here")
    return None


# ── reading the stream across dates ───────────────────────────────────────


def _definitions_across(reports: Iterable[ParsedReport]) -> dict[str, tuple[str, bool]]:
    """`{finding id: (defining report date, whether that report is legacy)}`.

    Definitions are recognised per grammar: on a lifecycle report by its
    `### `-headed entries, and on a legacy report by the id set of the frozen
    legacy count. One id is defined once across the directory, so a second
    claim on the same id is refused rather than disambiguated.
    """
    claims: dict[str, tuple[str, bool]] = {}

    def claim(finding_id: str, date: str, legacy: bool) -> None:
        held = claims.get(finding_id)
        if held is not None:
            raise ReviewFindingsError(
                f"the finding id {redact(finding_id)} is defined twice — by "
                f"the {held[0]} report and by the {date} report; a slug "
                "defined twice is refused rather than disambiguated")
        claims[finding_id] = (date, legacy)

    for report in sorted(reports, key=lambda r: r.date):
        for definition in report.definitions:
            claim(definition.finding_id, report.date, False)
        for finding_id in sorted(report.legacy_ids):
            claim(finding_id, report.date, True)
    return claims


def standing_by_finding(
        reports: Iterable[ParsedReport], *,
        locator_exists: Callable[[str], bool] | None = None) -> dict[str, str]:
    """`{finding id: standing}` over every finding the corpus defines.

    Records order by containing-report date, then by pass ordinal. Standing
    follows the stream in order rather than a rank table: no record is `open`,
    a `re-verified` record leaves the standing where it stands, a `disputed`
    record disputes it, and a `resolved` record resolves it and CLOSES the
    stream — a later record of any kind against that finding is refused. A
    finding a legacy report defined is `unknown` and stays `unknown`: the
    legacy row is never recomputed from later records.

    `locator_exists` is the injected existence probe. `None` skips the check
    entirely. When supplied, it is asked about a `resolved` record's locator
    alone; a False answer refuses the record, and a `ReviewFindingsError` the
    probe raises is re-raised carrying the record's line and report date. The
    caller supplies a probe already bounded to the repository root; this module
    performs no I/O after import. The three textual shapes that reach outside
    the root — an absolute path, a `~` prefix and a `..` traversal — are
    already refused at parse time by `_refuse_escaping_shape`, on every record
    whatever its event, so the probe never sees one.
    """
    reports = list(reports)
    claims = _definitions_across(reports)
    standing = {finding_id: ("unknown" if legacy else "open")
                for finding_id, (_date, legacy) in claims.items()}

    ordered = sorted(
        (record for report in reports for record in report.records),
        key=lambda r: (r.report_date, r.pass_ordinal, r.finding_id, r.event))

    seen_pass: set[tuple[str, str, int]] = set()
    closed: dict[str, Record] = {}

    for record in ordered:
        held = claims.get(record.finding_id)
        if held is None or held[0] != record.source_date:
            raise ReviewFindingsError(
                f"the lifecycle record at line {record.line} of the "
                f"{record.report_date} report names {redact(record.finding_id)} "
                f"on {record.source_date}, and no definition of that finding "
                "stands on that date")
        if record.report_date < record.source_date:
            raise ReviewFindingsError(
                f"the lifecycle record at line {record.line} of the "
                f"{record.report_date} report names "
                f"{redact(record.finding_id)} and predates the "
                f"{record.source_date} definition it names; a record cannot "
                "predate the definition it references")

        key = (record.finding_id, record.report_date, record.pass_ordinal)
        if key in seen_pass:
            raise ReviewFindingsError(
                f"the {record.report_date} report carries two lifecycle "
                f"records for {redact(record.finding_id)} from pass "
                f"{redact(str(record.pass_ordinal), quoted=False)}; one pass "
                "writes at most one record per finding")
        seen_pass.add(key)

        earlier = closed.get(record.finding_id)
        if earlier is not None:
            raise ReviewFindingsError(
                f"the lifecycle record at line {record.line} of the "
                f"{record.report_date} report stands against "
                f"{redact(record.finding_id)}, which the {earlier.report_date} "
                "report resolved; a resolution closed the stream, and a "
                "recurrence is a new finding naming the resolved one")

        if record.event == "resolved":
            # The probe is handed a locator and nothing else, so its own
            # refusal can name neither the record nor the report it came from.
            # This is the layer that knows both, so this is the layer that adds
            # them — on a corpus of several reports the reader would otherwise
            # grep the string to find the row.
            try:
                found = locator_exists is None or locator_exists(record.locator)
            except ReviewFindingsError as exc:
                raise ReviewFindingsError(
                    f"the resolved record at line {record.line} of the "
                    f"{record.report_date} report: {exc.problem}") from None
            if not found:
                raise ReviewFindingsError(
                    f"the resolved record at line {record.line} of the "
                    f"{record.report_date} report names the locator "
                    f"{redact(record.locator)}, which is no surface in the tree")
            closed[record.finding_id] = record

        if held[1]:
            continue                       # a legacy row never moves
        if record.event == "resolved":
            standing[record.finding_id] = "resolved"
        elif record.event == "disputed":
            standing[record.finding_id] = "disputed"
        # `re-verified` leaves the standing where it stands: it keeps an open
        # finding open, and it never clears a dispute.

    return standing


def report_standing(report: ParsedReport, standing: dict[str, str]) -> dict[str, int]:
    """The per-standing count over the report's OWN raised findings.

    A legacy report reports its frozen legacy count under `unknown`, and that
    key is always present — the row carries a value rather than a blank, and
    it is never recomputed from a later report's records. A lifecycle report
    reports only the states its findings actually occupy, so a renderer reads
    an absent key as zero.
    """
    if report.is_legacy:
        return {"unknown": report.raised}
    counts: dict[str, int] = {}
    for definition in report.definitions:
        state = standing.get(definition.finding_id, "unknown")
        counts[state] = counts.get(state, 0) + 1
    return counts


def events_elsewhere(report: ParsedReport,
                     reports: Iterable[ParsedReport]) -> int:
    """How many of `report`'s records name a finding another report defined.

    The count belongs on the RECORDING report's row and is never projected
    onto the row of the report that defined the finding. A record whose target
    resolves to no definition counts here too; `standing_by_finding` is the
    lane that refuses it.
    """
    claims = _definitions_across(reports)
    return sum(1 for record in report.records
               if claims.get(record.finding_id, (None, False))[0] != report.date)
