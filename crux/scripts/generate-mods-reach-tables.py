#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""generate-mods-reach-tables.py -- the regenerator for the crux-mods reach tables.

The user guide's crux-mods section says what the mod can reach and where each part
of the dashboard draws from. Those facts have one source, the capability manifest
`crux-mods/hooks/capabilities.ts`, so the guide carries them as a derived region
between `<!-- BEGIN GENERATED: mods-reach -->` and `<!-- END GENERATED: mods-reach -->`
(plugin-authoring scope; decisions ADR-0150 and ADR-0153).
Only the bytes between the two marker lines are rewritten. Every other byte of
`USER_GUIDE.md` is read with no newline translation and written back unchanged.

INPUTS. `USER_GUIDE.md` and `crux-mods/hooks/capabilities.ts`, nothing else. The
derived bytes depend on those two files alone, so the drift gate reads only them.
The manifest is parsed the way `tools/mods_gate.py` parses it (one marker pair,
`export const capabilities = ... as const;`, strict JSON, no duplicate key, no
`NaN`) and is never executed. This script imports nothing from `tools/`.

THE NOTES KEY. The manifest names what the mod reaches and holds no prose. A new
top-level `notes` object beside `launch` carries the prose a table needs: a
`sees` and a `keeps` text per entry, a `surface` text per draw event, one `never`
sentence, and a `surfaces` list of drawn parts with their `from` sources. The mod
never reads `notes`. Names, kind words, behaviour words and the launch command
come from the manifest's own entries; only note text comes from `notes`. The
headings, column labels and lead-in sentences are constants of this script.

FAIL CLOSED. Every join is checked and every failure is collected, then the run
exits 1 with `{"validation_errors": [{"code", "where"}, ...]}` and writes nothing.
A refusal names the field and the code and never the offending text. The codes are:
missing-note, orphan-note, unknown-notes-key, missing-notes-key, unknown-note-key,
missing-note-key, missing-surface, surface-on-non-draw, row-not-draw,
draw-without-row, duplicate-row, empty-from, duplicate-source, bad-origin,
bad-launch-field, bad-field, bad-note-text, bad-name, unexplained-placeholder,
marker-missing, marker-duplicated, marker-misordered and manifest-unparsed.

PLACEHOLDERS. A launch string may carry a placeholder the mod fills when it starts
the process: `{project_root}` or `{HOME}`. The launch sentences explain each one
that appears, in the order it first appears, from a constant of this script. Any
other brace in a launch string is `unexplained-placeholder`, so the guide never
shows a notation it does not explain.

THE ORIGIN RESTRICTION. A From source is `<origin>:<field>`, split at its last
colon. The origin is one of four data-yielding kinds and nothing else: the literal
`launch` (field exactly `outcome`); a `launch.scripts` key, the reader (field a
reader path); `$.agent.list`, admitted only while the manifest's `calls` lists it
(field one segment); the row's own event (field exactly `props.<name>`). Any other
call, another row's event and any unknown name is `bad-origin`. An origin that
yields no data would let a table name a source the mod never reads.

THE AUTOLINK REFUSAL. Note text is markdown that GitHub renders. A GFM extended
autolink needs `://`, `www.` or `@`, so those substrings are refused anywhere in
note text, inside backticks too. Together with the refused `<`, `>`, `&`, `[`, `]`
and backslash, no link form, entity, tag or forged marker is left. Backticks must
pair, and a `$` is allowed only inside a code span, because GitHub renders a bare
`$...$` as math. A `|` renders as `\\|`. The character allow-list is an explicit
constant, not a Unicode category test, so the verdict cannot differ between
Python 3.13 and 3.14.

WHY `view.ts` IS NOT READ. Reading the dashboard's TypeScript here would widen the
drift gate's input domain past the output's dependency and ship a TypeScript
scraper in the plugin. Traceability of each From field is a test's job
(`crux/scripts/tests/test_generate_mods_reach_tables.py`), run before anything ships.

THE FINGERPRINT LANE. The public clone and the staged artifact carry a
`USER_GUIDE.md` whose first line is the fingerprint `tools/sync_stage.py` writes.
That file is a rendition whose source is upstream, a different surface, so the run
reports surface-absent (exit 0, nothing written). The match is the whole line.

SCOPE AND IO. Plugin-authoring. The root comes from `--repo-root`, defaulting to the
working directory, through `authoring_scope`. Outside an authoring checkout, or with
the guide or manifest absent, the run reports surface-absent. The root is resolved
first, each component of each input path is checked with `lstat` and a symlink at
any component is refused (exit 2, cause on stderr, empty stdout), and the write goes
through a contained atomic write that keeps the target's permission bits.

EXIT CODES. 0 clean, written or surface-absent; 1 drift under `--dry-run` or a
validation failure, with JSON on stdout; 2 an environment fault (unreadable file,
symlink or containment refusal, write failure), with the cause on stderr.

A CONSEQUENCE FOR LATER BOOKS. The live surface-parts literal, the pinned `never`
literal and the From cross-check live in the test file, and ADR-0153's phase radius
does not reach that file. A later phase book that changes a drawn part, a reader
key, an event property the dashboard reads or `notes.never` must declare
`crux/scripts/tests/test_generate_mods_reach_tables.py`. A book that adds a
manifest name must also add its note, or this script fails closed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import authoring_scope as _scope  # noqa: E402

GUIDE_REL = "USER_GUIDE.md"
MANIFEST_REL = "crux-mods/hooks/capabilities.ts"
FIX_COMMAND = "generate-mods-reach-tables.py"

BEGIN_REGION = "<!-- BEGIN GENERATED: mods-reach -->"
END_REGION = "<!-- END GENERATED: mods-reach -->"

MANIFEST_BEGIN = "// BEGIN CAPABILITIES"
MANIFEST_END = "// END CAPABILITIES"

AGENT_LIST_CALL = "$.agent.list"
DRAW_BEHAVIOUR = "draw"

FINGERPRINT_RE = re.compile(
    r"<!-- generated-from: USER_GUIDE\.md@sha256:[0-9a-f]{64}; model: [^;\r\n]+; "
    r"date: \d{4}-\d{2}-\d{2} -->"
)
NAME_RE = re.compile(r"[A-Za-z0-9_.$={}/:@+-]{1,200}")
BEHAVIOUR_RE = re.compile(r"[a-z][a-z-]*")
FIELD_RE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(\[\])?(\.[A-Za-z_][A-Za-z0-9_]*(\[\])?)*"
)
PROPS_RE = re.compile(r"props\.[A-Za-z_][A-Za-z0-9_]*")
ONE_SEGMENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

TEXT_MIN, TEXT_MAX = 1, 400
ASCII_REFUSED = frozenset("\\<>&[]")
# The admitted non-ASCII code points: middle dot, dashes, quotes, ellipsis and the
# dashboard's own glyphs. Written as escapes; never a Unicode category test.
ADMITTED_NON_ASCII = frozenset(
    "\u00b7\u2013\u2014\u2018\u2019\u201c\u201d\u2026\u2205\u2296\u2297\u2298"
    "\u25ac\u25ae\u25af\u25b8\u25cc\u2713\u2717\u2b26"
)

NOTES_REQUIRED = ("events", "calls", "env_reads", "env_writes", "launch", "never", "surfaces")
NOTES_ALLOWED = NOTES_REQUIRED
ENTRY_KEYS = ("sees", "keeps")
SURFACE_KEYS = ("event", "part", "from")

LEAD_IN = (
    "The capability manifest, `crux-mods/hooks/capabilities.ts`, lists everything the "
    "mod can reach. Each row is one entry: an event it handles, a call it makes on `$`, "
    "an environment variable it reads, or the process it starts."
)
NO_OTHER = (
    "It handles no other event, makes no other call and reads no other environment variable."
)
SETS_NONE = "It sets no variable in Claude Code's environment."
SETS_ONLY = "It sets only these variables in Claude Code's environment: "
SHOWS_LEAD_IN = (
    "Each row below is one part of what the mod draws. The From column names what that "
    "part draws from: a field of the reader's output, a subagent field, a property of "
    "the event, or the launch outcome."
)
VALIDATE_POINTER = (
    "To see the same events, calls, environment variables and session state listed by "
    "Claude Code itself, run `claude plugin validate --strict` on the installed `crux-mods` "
    "directory."
)
PLACEHOLDER_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
# What each placeholder a launch string may carry stands for. Any other brace is refused.
PLACEHOLDERS = {
    "{project_root}": "the session's project root",
    "{HOME}": "the value of `HOME`",
}
REACH_HEADER = "| Through | Kind | What it sees | What it keeps |\n|---|---|---|---|"
SHOWS_HEADER = "| Where | Shows | From |\n|---|---|---|"


class ManifestError(ValueError):
    """The manifest cannot be read as a capability manifest. `where` names the field."""

    def __init__(self, where: str, reason: str = ""):
        super().__init__(reason or where)
        self.where = where


class EnvironmentFault(OSError):
    """An environment fault: unreadable file, symlink or containment refusal, write failure."""


# ---------------------------------------------------------------------------- fingerprint


def is_public_fingerprint(line: str) -> bool:
    """True when `line` (line ending removed) is exactly the fingerprint line
    `tools/sync_stage.py` writes on the public `USER_GUIDE.md`."""
    return FINGERPRINT_RE.fullmatch(line) is not None


# ---------------------------------------------------------------------------- manifest


def _no_constants(name: str):
    raise ValueError(f"non-strict JSON constant {name}")


def _no_duplicates(pairs):
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key {key!r}")
        out[key] = value
    return out


def _str_list(obj: dict, key: str, where: str, *, unique: bool) -> list[str]:
    value = obj.get(key)
    if not isinstance(value, list):
        raise ManifestError(where, "expected a list")
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item:
            raise ManifestError(f"{where}[{i}]", "expected a non-empty string")
    if unique:
        seen: set[str] = set()
        for i, item in enumerate(value):
            if item in seen:
                raise ManifestError(f"{where}[{i}]", "duplicate entry")
            seen.add(item)
    return value


def parse_manifest(text: str) -> dict:
    """Parse the manifest text into its whole JSON object, `notes` included.

    Raises ManifestError. Never executes the file.
    """
    lines = text.splitlines()
    begins = [i for i, line in enumerate(lines) if line.strip() == MANIFEST_BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == MANIFEST_END]
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        raise ManifestError(MANIFEST_REL, "markers")
    body = "\n".join(lines[begins[0] + 1:ends[0]]).strip()
    m = re.fullmatch(r"export const capabilities = (.*) as const;", body, re.S)
    if not m:
        raise ManifestError(MANIFEST_REL, "not an export const")
    try:
        data = json.loads(m.group(1), parse_constant=_no_constants, object_pairs_hook=_no_duplicates)
    except ValueError as exc:
        raise ManifestError(MANIFEST_REL, "not strict JSON") from exc
    _check_shape(data)
    return data


def _check_shape(data) -> None:
    if not isinstance(data, dict):
        raise ManifestError(MANIFEST_REL, "not an object")
    events = data.get("events")
    if not isinstance(events, list):
        raise ManifestError("events", "expected a list")
    seen: set[str] = set()
    for i, entry in enumerate(events):
        if not isinstance(entry, dict) or not isinstance(entry.get("event"), str) or not entry["event"]:
            raise ManifestError(f"events[{i}].event", "expected an event string")
        if entry["event"] in seen:
            raise ManifestError(f"events[{i}].event", "duplicate event")
        seen.add(entry["event"])
        if not isinstance(entry.get("behaviour"), str):
            raise ManifestError(f"events[{i}].behaviour", "expected a string")
    _str_list(data, "calls", "calls", unique=True)
    _str_list(data, "env_reads", "env_reads", unique=True)
    _str_list(data, "env_writes", "env_writes", unique=True)
    launch = data.get("launch")
    if not isinstance(launch, dict):
        raise ManifestError("launch", "expected an object")
    if not isinstance(launch.get("launcher"), str) or not launch["launcher"]:
        raise ManifestError("launch.launcher", "expected a non-empty string")
    _str_list(launch, "launcher_args", "launch.launcher_args", unique=False)
    _str_list(launch, "uv_locations", "launch.uv_locations", unique=False)
    _str_list(launch, "uv_args", "launch.uv_args", unique=False)
    _str_list(launch, "env_allow", "launch.env_allow", unique=False)
    scripts = launch.get("scripts")
    if not isinstance(scripts, dict):
        raise ManifestError("launch.scripts", "expected an object")
    for i, (key, script) in enumerate(scripts.items()):
        if not isinstance(script, dict):
            raise ManifestError(f"launch.scripts[{i}]", "expected an object")
        if not isinstance(script.get("path"), str) or not script["path"]:
            raise ManifestError(f"launch.scripts[{i}].path", "expected a non-empty string")
        _str_list(script, "args", f"launch.scripts[{i}].args", unique=False)


def load_manifest(path: Path) -> dict:
    """Read and parse the manifest at `path`. Refuses a symlink at the file itself.

    Raises ManifestError on a parse or shape fault and OSError when unreadable.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        raw = handle.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError(MANIFEST_REL, "not UTF-8") from exc
    return parse_manifest(text)


# ---------------------------------------------------------------------------- note text


def check_text(value) -> bool:
    """True when `value` is admissible note text. See the module docstring."""
    if not isinstance(value, str) or not (TEXT_MIN <= len(value) <= TEXT_MAX):
        return False
    for ch in value:
        cp = ord(ch)
        if 0x20 <= cp <= 0x7E:
            if ch in ASCII_REFUSED:
                return False
        elif ch not in ADMITTED_NON_ASCII:
            return False
    if "://" in value or "www." in value.lower() or "@" in value:
        return False
    if "``" in value or value.count("`") % 2 == 1:
        return False
    for i, segment in enumerate(value.split("`")):
        if i % 2 == 0 and "$" in segment:
            return False
    return True


def _safe(key, position: int) -> str:
    """A label for a key that names nothing: the key when it is a name, else its position."""
    if isinstance(key, str) and NAME_RE.fullmatch(key):
        return key
    return f"#{position}"


# ---------------------------------------------------------------------------- validation


class _Report:
    def __init__(self) -> None:
        self.errors: list[dict] = []

    def add(self, code: str, where: str) -> None:
        item = {"code": code, "where": where}
        if item not in self.errors:
            self.errors.append(item)


def _check_names(manifest: dict, rep: _Report) -> None:
    for i, entry in enumerate(manifest["events"]):
        if not NAME_RE.fullmatch(entry["event"]):
            rep.add("bad-name", f"events[{i}].event")
        if not BEHAVIOUR_RE.fullmatch(entry["behaviour"]):
            rep.add("bad-name", f"events[{i}].behaviour")
    for key in ("calls", "env_reads", "env_writes"):
        for i, name in enumerate(manifest[key]):
            if not NAME_RE.fullmatch(name):
                rep.add("bad-name", f"{key}[{i}]")
    launch = manifest["launch"]
    if not NAME_RE.fullmatch(launch["launcher"]):
        rep.add("bad-name", "launch.launcher")
    for key in ("launcher_args", "uv_locations", "uv_args", "env_allow"):
        for i, name in enumerate(launch[key]):
            if not NAME_RE.fullmatch(name):
                rep.add("bad-name", f"launch.{key}[{i}]")
    for i, (key, script) in enumerate(launch["scripts"].items()):
        if not NAME_RE.fullmatch(key):
            rep.add("bad-name", f"launch.scripts[{i}]")
        if not NAME_RE.fullmatch(script["path"]):
            rep.add("bad-name", f"launch.scripts[{i}].path")
        for j, arg in enumerate(script["args"]):
            if not NAME_RE.fullmatch(arg):
                rep.add("bad-name", f"launch.scripts[{i}].args[{j}]")
    for where, value in _launch_strings(launch):
        rest = value
        for token in PLACEHOLDERS:
            rest = rest.replace(token, "")
        if "{" in rest or "}" in rest:
            rep.add("unexplained-placeholder", where)


def _launch_strings(launch: dict):
    """Each launch string the launch sentences show, with its field, in the order shown."""
    for i, script in enumerate(launch["scripts"].values()):
        yield "launch.launcher", launch["launcher"]
        for j, value in enumerate(launch["launcher_args"]):
            yield f"launch.launcher_args[{j}]", value
        for j, value in enumerate(launch["uv_args"]):
            yield f"launch.uv_args[{j}]", value
        yield f"launch.scripts[{i}].path", script["path"]
        for j, value in enumerate(script["args"]):
            yield f"launch.scripts[{i}].args[{j}]", value
    for j, value in enumerate(launch["env_allow"]):
        yield f"launch.env_allow[{j}]", value
    for j, value in enumerate(launch["uv_locations"]):
        yield f"launch.uv_locations[{j}]", value


def _check_entry(where: str, entry, rep: _Report, *, behaviour: str | None = None) -> None:
    """One `{"sees", "keeps"}` note. `behaviour` is set for an event note."""
    if not isinstance(entry, dict):
        rep.add("missing-note-key", where)
        return
    allowed = set(ENTRY_KEYS) | ({"surface"} if behaviour is not None else set())
    for i, key in enumerate(entry):
        if key not in allowed:
            rep.add("unknown-note-key", f"{where}.{_safe(key, i)}")
    for field in ENTRY_KEYS:
        if field not in entry:
            rep.add("missing-note-key", f"{where}.{field}")
        elif not check_text(entry[field]):
            rep.add("bad-note-text", f"{where}.{field}")
    if behaviour is None:
        return
    if behaviour == DRAW_BEHAVIOUR:
        if "surface" not in entry:
            rep.add("missing-surface", f"{where}.surface")
        elif not check_text(entry["surface"]):
            rep.add("bad-note-text", f"{where}.surface")
    elif "surface" in entry:
        rep.add("surface-on-non-draw", f"{where}.surface")


def _check_section(label: str, expected: list[str], section: dict,
                   behaviours: dict[str, str] | None, rep: _Report) -> None:
    for i, name in enumerate(expected):
        where = f"notes.{label}[{_safe(name, i)}]"
        if name not in section:
            rep.add("missing-note", where)
            continue
        _check_entry(where, section[name], rep,
                     behaviour=None if behaviours is None else behaviours[name])
    for i, key in enumerate(section):
        if key in expected:
            continue
        where = f"notes.{label}[{_safe(key, i)}]"
        rep.add("orphan-note", where)


def _check_source(where: str, source, row_event, launch_scripts: dict, calls: list[str],
                  rep: _Report) -> None:
    if not isinstance(source, str):
        rep.add("bad-field", where)
        return
    if ":" not in source:
        rep.add("bad-origin", where)
        return
    origin, field = source.rsplit(":", 1)
    if origin == "launch":
        if field != "outcome":
            rep.add("bad-launch-field", where)
    elif origin in launch_scripts:
        if not FIELD_RE.fullmatch(field):
            rep.add("bad-field", where)
    elif origin == AGENT_LIST_CALL and AGENT_LIST_CALL in calls:
        if not ONE_SEGMENT_RE.fullmatch(field):
            rep.add("bad-field", where)
    elif isinstance(row_event, str) and origin == row_event:
        if not PROPS_RE.fullmatch(field):
            rep.add("bad-field", where)
    else:
        rep.add("bad-origin", where)


def _check_surfaces(surfaces: list, manifest: dict, rep: _Report) -> None:
    draw_events = [e["event"] for e in manifest["events"] if e["behaviour"] == DRAW_BEHAVIOUR]
    seen_rows: set[tuple] = set()
    covered: set[str] = set()
    for i, row in enumerate(surfaces):
        where = f"notes.surfaces[{i}]"
        if not isinstance(row, dict):
            rep.add("missing-note-key", where)
            continue
        for j, key in enumerate(row):
            if key not in SURFACE_KEYS:
                rep.add("unknown-note-key", f"{where}.{_safe(key, j)}")
        for field in SURFACE_KEYS:
            if field not in row:
                rep.add("missing-note-key", f"{where}.{field}")
        event = row.get("event")
        if "event" in row:
            if isinstance(event, str) and event in draw_events:
                covered.add(event)
            else:
                rep.add("row-not-draw", f"{where}.event")
        if "part" in row and not check_text(row["part"]):
            rep.add("bad-note-text", f"{where}.part")
        if isinstance(event, str) and isinstance(row.get("part"), str):
            key = (event, row["part"])
            if key in seen_rows:
                rep.add("duplicate-row", where)
            seen_rows.add(key)
        if "from" not in row:
            continue
        sources = row["from"]
        if not isinstance(sources, list):
            rep.add("bad-field", f"{where}.from")
            continue
        if not sources:
            rep.add("empty-from", f"{where}.from")
        seen_sources: set[str] = set()
        for k, source in enumerate(sources):
            _check_source(f"{where}.from[{k}]", source, event, manifest["launch"]["scripts"],
                          manifest["calls"], rep)
            if isinstance(source, str):
                if source in seen_sources:
                    rep.add("duplicate-source", f"{where}.from[{k}]")
                seen_sources.add(source)
    for i, name in enumerate(draw_events):
        if name not in covered:
            rep.add("draw-without-row", f"notes.events[{_safe(name, i)}]")


def validate(manifest: dict) -> list[dict]:
    """Every failure of the manifest and its notes, in discovery order."""
    rep = _Report()
    _check_names(manifest, rep)
    notes = manifest.get("notes")
    if not isinstance(notes, dict):
        rep.add("missing-notes-key", "notes")
        return rep.errors
    for i, key in enumerate(notes):
        if key not in NOTES_ALLOWED:
            rep.add("unknown-notes-key", f"notes.{_safe(key, i)}")
    wrong_type = set()
    for key in NOTES_REQUIRED:
        if key not in notes:
            rep.add("missing-notes-key", f"notes.{key}")
            wrong_type.add(key)
            continue
        want = {"never": str, "surfaces": list}.get(key, dict)
        if not isinstance(notes[key], want):
            rep.add("missing-notes-key" if key != "never" else "bad-note-text", f"notes.{key}")
            wrong_type.add(key)
    launch = manifest["launch"]
    events = manifest["events"]
    behaviours = {e["event"]: e["behaviour"] for e in events}
    if "events" not in wrong_type:
        _check_section("events", [e["event"] for e in events], notes["events"], behaviours, rep)
    if "calls" not in wrong_type:
        _check_section("calls", manifest["calls"], notes["calls"], None, rep)
    if "env_reads" not in wrong_type:
        _check_section("env_reads", manifest["env_reads"], notes["env_reads"], None, rep)
    if "env_writes" not in wrong_type:
        _check_section("env_writes", manifest["env_writes"], notes["env_writes"], None, rep)
    if "launch" not in wrong_type:
        _check_section("launch", list(launch["scripts"]), notes["launch"], None, rep)
    if "never" not in wrong_type:
        never = notes["never"]
        if not check_text(never) or not never[:1].isascii() or not never[:1].isalpha():
            rep.add("bad-note-text", "notes.never")
    if "surfaces" not in wrong_type:
        _check_surfaces(notes["surfaces"], manifest, rep)
    return rep.errors


# ---------------------------------------------------------------------------- rendering


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _code(text: str) -> str:
    return "`" + _cell(text) + "`"


def _join(items: list[str]) -> str:
    codes = [_code(i) for i in items]
    if len(codes) == 1:
        return codes[0]
    return ", ".join(codes[:-1]) + " and " + codes[-1]


def _row(*cells: str) -> str:
    return "| " + " | ".join(cells) + " |"


def render_region(manifest: dict) -> str:
    """The region body: everything strictly between the two marker lines."""
    notes = manifest["notes"]
    launch = manifest["launch"]
    rows = [REACH_HEADER]
    for e in manifest["events"]:
        n = notes["events"][e["event"]]
        rows.append(_row(_code(e["event"]), f"event ({e['behaviour']})",
                         _cell(n["sees"]), _cell(n["keeps"])))
    for name in manifest["calls"]:
        n = notes["calls"][name]
        rows.append(_row(_code(name), "call", _cell(n["sees"]), _cell(n["keeps"])))
    for name in manifest["env_reads"]:
        n = notes["env_reads"][name]
        rows.append(_row(_code(name), "environment read", _cell(n["sees"]), _cell(n["keeps"])))
    for name in manifest["env_writes"]:
        n = notes["env_writes"][name]
        rows.append(_row(_code(name), "environment write", _cell(n["sees"]), _cell(n["keeps"])))
    for key in launch["scripts"]:
        n = notes["launch"][key]
        rows.append(_row(_code(key), "process", _cell(n["sees"]), _cell(n["keeps"])))

    if manifest["env_writes"]:
        sets = SETS_ONLY + _join(manifest["env_writes"]) + "."
    else:
        sets = SETS_NONE

    sentences = []
    for key, script in launch["scripts"].items():
        tokens = [launch["launcher"], *launch["launcher_args"], "<variables>", "<uv>",
                  *launch["uv_args"], "<crux>/" + script["path"], *script["args"]]
        sentences.append(f"To run {_code(key)}, it starts {_code(' '.join(tokens))}.")
    sentences.append("`<variables>` stands for the only variables the process starts with: "
                     + _join(launch["env_allow"]) + ".")
    sentences.append("`<uv>` is the first file found among " + _join(launch["uv_locations"]) + ".")
    sentences.append("`<crux>` is the installed crux plugin's directory.")
    shown: list[str] = []
    for _, value in _launch_strings(launch):
        for token in PLACEHOLDER_RE.findall(value):
            if token not in shown:
                shown.append(token)
    for token in shown:
        sentences.append(f"{_code(token)} is {PLACEHOLDERS[token]}.")

    shows = [SHOWS_HEADER]
    for row in notes["surfaces"]:
        where = notes["events"][row["event"]]["surface"]
        shows.append(_row(_cell(where), _cell(row["part"]),
                          ", ".join(_code(s) for s in row["from"])))

    blocks = [
        LEAD_IN,
        "\n".join(rows),
        NO_OTHER + " " + sets,
        " ".join(sentences),
        _cell(notes["never"]),
        SHOWS_LEAD_IN,
        "\n".join(shows),
        VALIDATE_POINTER,
    ]
    return "\n\n" + "\n\n".join(blocks) + "\n\n"


# ---------------------------------------------------------------------------- guide region


def _marker_line(marker: str) -> re.Pattern[str]:
    """Match the marker only as a whole line; `\\r` is tolerated for CRLF files."""
    return re.compile(r"^[ \t]*" + re.escape(marker) + r"[ \t\r]*$", re.MULTILINE)


def find_region(text: str) -> tuple[int, int] | str:
    """Offsets of the bytes strictly between the marker lines, or a marker error code."""
    b = list(_marker_line(BEGIN_REGION).finditer(text))
    e = list(_marker_line(END_REGION).finditer(text))
    if not b or not e:
        return "marker-missing"
    if len(b) > 1 or len(e) > 1:
        return "marker-duplicated"
    if e[0].start() < b[0].end():
        return "marker-misordered"
    return b[0].end(), e[0].start()


# ---------------------------------------------------------------------------- IO


def _check_path(root: Path, rel: str) -> Path | None:
    """The file at `root/rel`, or None when absent.

    Walks each component from the root down with `lstat` and refuses a symlink at
    any component, the file itself included. Raises EnvironmentFault.
    """
    current = root
    parts = rel.split("/")
    for i, part in enumerate(parts):
        current = current / part
        try:
            st = os.lstat(current)
        except (FileNotFoundError, NotADirectoryError):
            return None
        except OSError as exc:
            raise EnvironmentFault(f"cannot inspect {rel}: {exc.strerror}") from exc
        if stat.S_ISLNK(st.st_mode):
            raise EnvironmentFault(f"refusing {rel}: {'/'.join(parts[:i + 1])} is a symlink")
        last = i == len(parts) - 1
        if last and not stat.S_ISREG(st.st_mode):
            raise EnvironmentFault(f"refusing {rel}: not a regular file")
        if not last and not stat.S_ISDIR(st.st_mode):
            return None
    resolved = current.resolve()
    if root not in resolved.parents:
        raise EnvironmentFault(
            f"refusing {rel}: it resolves outside the repository root")
    return current


def _read_guide(path: Path) -> str:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            return handle.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise EnvironmentFault(f"cannot read {GUIDE_REL}: {exc}") from exc


def _atomic_write_text(path: Path, body: str, *, contained_under: Path) -> None:
    """Atomic UTF-8 write, no newline translation, keeping the target's permission bits.

    Vendored from `generate-journal-index.py`: parent containment, symlink refusal for
    the target and the temporary file, `O_CREAT | O_EXCL | O_NOFOLLOW`, then `os.replace`.
    The temporary file is `.USER_GUIDE.md.tmp`.
    """
    root_resolved = Path(contained_under).resolve()
    parent_resolved = path.parent.resolve()
    if parent_resolved != root_resolved and root_resolved not in parent_resolved.parents:
        raise EnvironmentFault(
            f"refusing to write {path.name}: its directory is outside the repository root")
    tmp = path.with_name("." + path.name + ".tmp")
    for label, candidate in (("target", path), ("temporary file", tmp)):
        if candidate.is_symlink():
            raise EnvironmentFault(f"refusing to write {path.name}: the {label} is a symlink")
    mode = stat.S_IMODE(os.lstat(path).st_mode)
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError as exc:
        raise EnvironmentFault(
            f"refusing to write {path.name}: the temporary file {tmp.name} already exists") from exc
    except OSError as exc:
        raise EnvironmentFault(f"cannot create {tmp.name}: {exc.strerror}") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body.encode("utf-8"))
            os.fchmod(handle.fileno(), mode)
        os.replace(tmp, path)
    except Exception as exc:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise EnvironmentFault(f"cannot write {path.name}: {exc}") from exc


def _emit(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True))


def run(root: Path, *, dry_run: bool) -> int:
    if not _scope.is_authoring_checkout(root, __file__):
        return _scope.print_surface_absent()
    guide_path = _check_path(root, GUIDE_REL)
    manifest_path = _check_path(root, MANIFEST_REL)
    if guide_path is None:
        return _scope.print_surface_absent(f"{GUIDE_REL} is absent; nothing to project into")
    if manifest_path is None:
        return _scope.print_surface_absent(f"{MANIFEST_REL} is absent; nothing to project from")
    text = _read_guide(guide_path)
    if is_public_fingerprint(text.split("\n", 1)[0].removesuffix("\r")):
        return _scope.print_surface_absent(
            f"{GUIDE_REL} is the public rendition (fingerprint on line 1); its source is upstream")
    errors: list[dict] = []
    manifest: dict | None = None
    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        errors.append({"code": "manifest-unparsed", "where": exc.where})
    except OSError as exc:
        raise EnvironmentFault(f"cannot read {MANIFEST_REL}: {exc}") from exc
    if manifest is not None:
        errors.extend(validate(manifest))
    region = find_region(text)
    if isinstance(region, str):
        errors.append({"code": region, "where": GUIDE_REL})
    if errors:
        _emit({"validation_errors": errors})
        return 1
    assert manifest is not None and not isinstance(region, str)
    start, end = region
    new_text = text[:start] + render_region(manifest) + text[end:]
    if new_text == text:
        _emit({"drift": False, "paths": []} if dry_run
              else {"drift": False, "paths": [], "written": []})
        return 0
    if dry_run:
        _emit({"drift": True, "paths": [GUIDE_REL], "fix": FIX_COMMAND})
        return 1
    _atomic_write_text(guide_path, new_text, contained_under=root)
    _emit({"drift": False, "paths": [], "written": [GUIDE_REL]})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=FIX_COMMAND,
        description="Regenerate the crux-mods reach tables in USER_GUIDE.md from the "
                    "capability manifest, or check them for drift.")
    parser.add_argument("--dry-run", action="store_true",
                        help="report drift (exit 1) without writing")
    parser.add_argument("--repo-root", default=None,
                        help="the project root (default: the working directory)")
    args = parser.parse_args(argv)
    root = _scope.resolve_repo_root(args.repo_root)
    try:
        return run(root, dry_run=args.dry_run)
    except EnvironmentFault as exc:
        print(f"{FIX_COMMAND}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
