#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""visualize-run-progress — render a promptbook run snapshot's progress.

Per ADR-0025. READ-ONLY: derives a progress view from a run snapshot (the
ADR-0023 `.yaml` format, or a legacy `.md` snapshot) and its book, and renders
it two ways:

  * terminal (default) — a progress bar + a colored per-prompt checklist;
  * markdown (--markdown) — a byte-stable artifact written next to the snapshot
    at `run-RUN-NNN-progress.md` (no timestamps in the body; deterministic).

It never mutates run state (derive, don't decide — the link-adr-graph principle).
`module_tag` lives only on the *book* (`promptbook.schema.json`), not the run's
`prompts[]` (`run.schema.json`), so it is joined from the book by `n` after the
run's `book_content_hash` verifies the plan still matches; on a mismatch (a
plan edited in place) or a legacy `.md` run it renders `—`.

Exit codes: 0 clean; 1 not-found / validation error (the repo convention);
2 environment cannot supply a real YAML parser (PB-0026 capability error —
remediation on stderr, nothing on stdout).

JSON mode (`--json --project-root <ABSOLUTE_DIR> [PB-NNNN [--run RUN-NNN]]`)
is a third, contained rendering for a dashboard to draw. It reads the project
only through an anchored SourceIO rooted at `--project-root`, admits a tree file
only when it resolves inside the resolved documentation tree, validates in
memory, never re-execs through uv and never writes. It runs no git and reads
nothing under `.git/`. It prints exactly one JSON object and a newline on stdout
and nothing on stderr for every outcome. It emits no run `result`, `notes` or
`artifacts` text and no council reasoning or finding text. The free text it
emits is titles, which lose control characters and stop at 200 code points, and
the summary of the last completed run, as control-free lines.
Free text is not safe to draw as emitted. Titles and summary lines keep U+2028,
U+2029 and the bidirectional format characters U+061C, U+200E, U+200F, U+202A
to U+202E and U+2066 to U+2069, and a title can keep a lone surrogate. A
consumer removes them before drawing, as crux-mods' safeText does.
Exit codes: 0 ok; 1 error envelope; 2 error envelope with code `yaml-unavailable`.

The JSON document (format `crux.run-progress`, format_version 2). crux-mods checks
the exact key set at every level and accepts format_version 2 only, so adding,
removing or renaming any key is a breaking change: bump JSON_FORMAT_VERSION and
the mod in the same release. A time is whole epoch seconds, floored, in
0 to 4102444800, or null. A count is a non-negative integer.

  success: {format, format_version, ok: true, reader_version, docs_dir, now_s,
            runs: [RunView], runs_skipped, last_completed: RunView | null,
            last_completed_status, last_completed_undated,
            last_completed_unresolved}
  RunView: {book_id, run_id, status, current_prompt, run_path, book_path,
            modified_s, started_s, completed_s, tag_joined,
            progress: {total, terminal, done, pct,
            counts: {done, skipped, blocked, running, pending}},
            prompts: [{n, state, module_tag, title, started_s, completed_s}],
            councils: [Council], councils_skipped, gates: [Gate],
            summary: [string], summary_truncated, escalations: [Escalation]}
  Council: {record_path, prompt, module_tag, council_kind, round, outcome,
            quorum_met, degraded, aggregate_action, converged, seats: [{role,
            decision, errored, findings: {blocking, nit}}]}
  Gate:    {n, gate_class, state, evidence: [path], evidence_count}
  Escalation: {prompt, module_tag, round}
  error:   {format, format_version: 2, ok: false, error: {code}}

Paths are relative to the documentation tree. `now_s` is this reader's own clock
when it built the document, null when that lies outside the time range.
`modified_s` is the run file's modification time in whole seconds since the epoch,
0 when the time cannot be read or lies beyond 2100-01-01; crux-mods draws the band
for the run with the newest one. `started_s` and `completed_s` come from the run's
`started_at` and `completed_at`, and a prompt's from its `started` and `completed`.
A time is a string of the form `YYYY-MM-DD`, `T` or one space, `HH:MM:SS`, an
optional fraction, then `Z` or a numeric offset, in ASCII digits, or a
timezone-aware datetime. A naive time, any other string, an impossible
calendar date such as `2026-02-30` and a time outside the range give null.
A seat `decision` is a council decision token (run-council.py's
_DECISION_TOKENS) and `aggregate_action` is a route action (JSON_ROUTE_ACTIONS);
a value outside its set is null. A council's `converged` holds when the record
ran, its quorum is met, every seat that did not error approved, and no such seat
carries a blocking finding: the gate's per-record rule
(rule:convergence-is-derived-per-seat), held equal to council_history_v4 by a
test. `gates` lists each prompt the cycle gate classifies by position as
`council`, `module-close` or `independent-review` (council_gate.classify, read
with the book's own cycle fields because this mode runs no git), with the run's
recorded state and its evidence. A council or module-close gate's `evidence`
lists only the attached artifacts that equal the `record_path` of a council
record this same view opened and validated (an attempt record, an
owner-exception record or a refused file never appears), and `evidence_count`
is its length. An independent-review gate's `evidence` is always empty: its
`evidence_count` is the number of distinct attached artifacts that name an
existing file in the run's own `reviews/` directory, at most 20, and the reader
never reads such a file. `gates` is empty when the book does not join the run.
`runs_skipped` and `councils_skipped` count files the reader refused or could
not read.

`escalations` lists, in ascending `prompt`, each module whose recorded rounds show
an escalation stop coming. A module is a module tag that a prompt of the joined
book carries, with the run's councils tagged so; or, for councils with a null tag
(a patch book), a prompt that those councils bind. A module gets one entry when
the run is `in_progress`, the book joins the run, the module has an open prompt
(not `done` or `skipped`), `councils_skipped` is 0, its `ran` records carry the
rounds 1 to k exactly once with k at least 3, every one has its quorum met, and
none converged. The entry holds the round-k record's prompt, the tag (null for a
patch module) and k. The entry says what the files show. It does not say that the
gate stops: the gate counts only records whose seals and committed history hold,
and this mode reads no git, no attempt record and no refutation or
owner-exception record.

Active mode (no PB argument) reports `runs`: every schema-valid in-progress YAML
run. `last_completed` is the last completed run, set only when no run can be in
progress. `last_completed_status` is one of `not-requested` (target mode, which
also gives null, 0 and 0), `run-in-progress` (a schema-valid in-progress run was
found, so no search runs), `undetermined`, `none`, `latest` and `latest-dated`.
The scan decides in this order. An entry the scan cannot read counts in
`last_completed_unresolved`: an entry whose name is outside the path alphabet
and that is not a regular file, a link leaving the tree or the project root, an
entry that vanished, a listing or a read that was refused, a file over 4 MiB, a
file that is not UTF-8, a misnamed run file, or a file that is neither plain
closed form nor a valid run. Any unresolved entry gives `undetermined`. An
entry that holds no run counts in neither `last_completed_unresolved` nor
`last_completed_undated`: a loose file under `runs/`, a progress render, a
legacy Markdown run and an abandoned run. A legacy Markdown run, and a loose
file whose name is outside the path alphabet, still count in `runs_skipped`.
A completed run is a candidate, dated by its completion time
(`last_completed_undated` counts those that give no seconds). With no dated
candidate the status is `none`, or `undetermined` when some candidate is undated.
Otherwise the reader parses the newest dated candidate only (equal dates rank by
run path in descending code-point order). It wins when its document validates, is
still `completed`, carries the same completion seconds as its scan, and its view
builds. A winner gives `latest`, or `latest-dated` when some candidate is undated.
Any other result is `undetermined`, counted in `last_completed_unresolved` and
`runs_skipped`. `latest` and `latest-dated` rank schema-valid YAML runs only, so
either label means the latest YAML run.

`summary` holds the last completed run's summary, in no other view (the others
carry `[]` and false). It splits on CRLF, LF and CR only; every C0, DEL and C1
character and every surrogate code point is removed from each line; U+2028 and
U+2029 stay inside their line. A line is cut to 1000 code points, and at most 240
lines and 32000 code points in all are kept. `summary_truncated` is true when a cap
cut text. An interior empty line is kept as an empty string.

Plain closed form. Active mode never parses a run file whose text is in plain
closed form: the scanned `status` and `completed_at` decide. `_plain_closed(text)`
accepts a text when all seven rules hold:
  P1  no CR, NEL (U+0085), U+2028 or U+2029, so LF is the only line break;
  P2  every column-0 line (not empty, first character not a space) is a comment,
      a sequence entry, or a plain key of `_RUN_TOP_KEYS` (the top-level
      properties of run.schema.json);
  P3  the first line that is not empty and not a column-0 comment is a plain-key
      line, with no indented line before it;
  P4  no key occurs on two plain-key lines;
  P5  after the `status:` and `completed_at:` lines, the next non-empty line does
      not begin with a space or a tab;
  P6  a `status:` line exists and names `completed` or `abandoned`, bare or in
      matching quotes, then only spaces, or at least one space and a comment;
  P7  a `completed_at:` line exists and holds `null` or a time, bare or in
      matching quotes, then only spaces.
Invariant: for a text in plain closed form that loads to a schema-valid run, the
loader's root `status` is the scanned word and its `completed_at` gives the same
seconds as the scanned time. P1 makes the loader's lines the scan's lines. P3 makes
the root a block mapping at indentation 0 whose keys start their lines. P2 and P4
make the two scanned lines the only root key lines for those keys, so a column-0
line inside a quoted or flow value that repeats a key is refused by P4. P5 stops a
bare value from continuing, and P6 and P7 leave no escape, anchor, tag or comment
that could change the value. A text in plain closed form that is no schema-valid
run is never shown and is never taken for a newer run: ranked first its parse
fails and the status is `undetermined`, and ranked lower it changes nothing.
Undated, it counts in `last_completed_undated`, which lowers `latest` to
`latest-dated`, or gives `undetermined` when no candidate is dated. A file that
breaks any rule is parsed in full.

Error codes: usage (a malformed command line); project-root-invalid (not an
absolute directory); config-invalid (the layout config cannot be read);
tree-missing (no documentation tree); containment (a path leaves the tree);
book-not-found, run-not-found (target mode); run-invalid, book-invalid (target
mode: the file fails its schema or is a legacy .md run); token-set-unavailable
(run-council.py's decision tokens cannot be read); yaml-unavailable (no PyYAML;
exit 2); time-limit (the reader ran past its own time limit); internal (anything
else, never with a traceback).
"""
from __future__ import annotations

import argparse
import ast
import datetime
import importlib.util
import json
import math
import os
import re
import signal
import sys
import time
from collections import Counter
from typing import NamedTuple
from pathlib import Path

_HERE = Path(__file__).resolve().parent


class _NoBytecode:
    """Hold `sys.dont_write_bytecode` true for a block, then restore it.

    The reader never writes into the installed crux, and a compiled-module cache
    is a write.
    """

    def __enter__(self):
        self._saved = sys.dont_write_bytecode
        sys.dont_write_bytecode = True

    def __exit__(self, *exc):
        sys.dont_write_bytecode = self._saved
        return False


def _load_sibling(modname: str, filename: str):
    """Import a sibling script (incl. hyphenated names) by path."""
    spec = importlib.util.spec_from_file_location(modname, _HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    with _NoBytecode():
        spec.loader.exec_module(mod)
    return mod


# The vendored promptbook validator owns load_yaml + compute_book_hash +
# validate_file; reuse it so parsing/hashing/validation stay in lock-step.
_vp = _load_sibling("validate_promptbook", "validate-promptbook.py")
load_yaml = _vp.load_yaml
compute_book_hash = _vp.compute_book_hash
# SINGLE-INSTANCE RULE (PB-0026 review): the capability guard + exception
# class must come from the SAME _yaml_min instance _vp.load_yaml raises from
# — a fresh sibling load would create a distinct class our except clauses
# silently fail to catch. _vp re-exports both names.
ensure_real_yaml = _vp.ensure_real_yaml
YamlCapabilityError = _vp.YamlCapabilityError

# Repo-root .crux config (ADR-0032) — supplies the docs tree location.
_crux_config = _load_sibling("crux_config", "crux_config.py")
validate_file = _vp.validate_file

# ----------------------------------------------------------------------------
# Rendering constants
# ----------------------------------------------------------------------------
STATES = ["done", "skipped", "blocked", "running", "pending"]
TERMINAL_STATES = {"done", "skipped", "blocked"}
GLYPH = {"done": "✓", "skipped": "⊘", "blocked": "✗", "running": "▸", "pending": "·"}
# state -> ANSI SGR code (per ADR-0025): done=green, skipped=yellow, blocked=red,
# running=cyan(bold), pending=dim.
COLOR = {"done": "32", "skipped": "33", "blocked": "31", "running": "36;1", "pending": "2"}

# Strip C0 (except tab) + DEL + C1 control bytes — defends the terminal renderer
# against ANSI/escape injection from author-controlled title/result, and keeps
# the markdown cells clean.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def _sanitize(s: str) -> str:
    """Remove control/escape bytes from author-controlled text."""
    return _CONTROL_RE.sub("", s or "")


def _md_cell(s: str) -> str:
    """Sanitize + escape a value for a Markdown table cell (no pipe/newline breaks)."""
    return _sanitize(s).replace("|", r"\|").replace("\n", " ").strip()


# ----------------------------------------------------------------------------
# Loading / format detection
# ----------------------------------------------------------------------------
class ProgressError(Exception):
    """Surfaced to the user with exit code 1."""


def _detect_and_load(path: Path, kind: str) -> dict:
    """Load a `.yaml` (validated) or legacy `.md` promptbook/run document.

    `kind` is "run" or "promptbook" — used for `.yaml` schema validation.
    """
    if not path.exists():
        raise ProgressError(f"not found: {path}")
    if path.suffix == ".yaml":
        try:
            doc = load_yaml(path.read_text(encoding="utf-8"))
        except YamlCapabilityError:
            raise  # environment problem -> main()'s exit-2 lane, not a parse finding
        except Exception as exc:  # malformed YAML must surface as a clean exit-1, not a traceback
            raise ProgressError(f"could not parse {path}: {exc}")
        if not isinstance(doc, dict) or "format_version" not in doc:
            raise ProgressError(f"malformed new-format document (no format_version): {path}")
        code, errors = validate_file(path, kind)
        if code != 0:
            msgs = "; ".join(e.get("message", str(e)) for e in errors[:5])
            raise ProgressError(f"{path} fails {kind}.schema.json: {msgs}")
        return doc
    if path.suffix == ".md":
        try:
            return _parse_legacy(path.read_text(encoding="utf-8"), kind)
        except YamlCapabilityError:
            raise  # environment problem -> main()'s exit-2 lane
        except Exception as exc:
            raise ProgressError(f"could not parse legacy {path}: {exc}")
    raise ProgressError(f"unrecognized extension (expected .yaml/.md): {path}")


_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_LEGACY_PROMPT_RE = re.compile(r"^##+ +Prompt +(\d+) +[—-] +(.*?) *$", re.MULTILINE)
_LEGACY_STATE_RE = re.compile(r"\*\*State:\*\* *(\w+)")


def _parse_legacy(text: str, kind: str) -> dict:
    """Minimal legacy-`.md` parse: frontmatter scalars + `## Prompt N — title` blocks."""
    doc: dict = {"format_version": None}
    m = _FM_RE.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition(":")
                doc[k.strip()] = v.strip().strip('"') or None
    prompts = []
    matches = list(_LEGACY_PROMPT_RE.finditer(text))
    for i, mt in enumerate(matches):
        block = text[mt.end():(matches[i + 1].start() if i + 1 < len(matches) else len(text))]
        sm = _LEGACY_STATE_RE.search(block)
        prompts.append({
            "n": int(mt.group(1)),
            "title": mt.group(2).strip(),
            "state": (sm.group(1) if sm else "pending"),
        })
    doc["prompts"] = prompts
    return doc


# ----------------------------------------------------------------------------
# Resolution: target (path | PB-NNNN) -> (run_path, book_path|None)
# ----------------------------------------------------------------------------
# Accepts an optional non-reserved artifact prefix per ADR-0032 (CRX-PB-0040).
# The reserved alternation must stay in lock-step with crux_config.RESERVED_PREFIXES.
_PB_RE = re.compile(r"^(?:(?!(?:PB|ADR|RUN|BRIEF)-)[A-Z][A-Z0-9]{1,9}-)?PB-\d{4}$")


_DOCS_ROOT_CACHE: Path | None = None


def _docs_root() -> Path:
    # Resolved exactly once per process (the ADR-0032 resolve-once rule);
    # this function is hit multiple times per invocation.
    global _DOCS_ROOT_CACHE
    if _DOCS_ROOT_CACHE is not None:
        return _DOCS_ROOT_CACHE
    try:
        cfg = _crux_config.load_config()
    except _crux_config.CruxConfigError as exc:
        raise ProgressError(f".crux configuration error: {exc}")
    root = cfg.docs_root / "promptbooks"
    if not root.is_dir():
        raise ProgressError(f"{cfg.docs_dir}/promptbooks/ not found (run from the project root)")
    _DOCS_ROOT_CACHE = root
    return root


def _find_book(pb_id: str) -> Path | None:
    root = _docs_root()
    for sub in ("active", "archive"):
        for ext in (".yaml", ".md"):
            hits = sorted((root / sub).glob(f"{pb_id}-*{ext}")) if (root / sub).is_dir() else []
            if hits:
                return hits[0]
    return None


def _highest_run(run_dir: Path) -> Path | None:
    if not run_dir.is_dir():
        return None
    runs = list(run_dir.glob("run-RUN-*.yaml")) + list(run_dir.glob("run-RUN-*.md"))
    if not runs:
        return None

    def _key(p: Path) -> tuple[int, int]:
        m = re.search(r"RUN-(\d+)", p.name)
        # highest run number wins; for the SAME number prefer .yaml (the
        # authoritative post-migration format) over a coexisting legacy .md.
        return (int(m.group(1)) if m else -1, 1 if p.suffix == ".yaml" else 0)

    return max(runs, key=_key)


def resolve(target: str, run_override: str | None) -> tuple[Path, Path | None]:
    """Return (run_path, book_path). `target` is an explicit run-file path or a PB-NNNN id."""
    p = Path(target)
    if p.exists() and p.is_file():
        # explicit run path; locate its book by id from the doc.
        doc = _detect_and_load(p, "run")
        book = _find_book(doc.get("book_id", "")) if doc.get("book_id") else None
        return p, book
    if not _PB_RE.match(target):
        raise ProgressError(f"target is neither an existing file nor a PB-NNNN id: {target}")
    book = _find_book(target)
    if book is None:
        raise ProgressError(f"no book found for {target} under {_docs_root()}/{{active,archive}}/")
    slug_dir = _docs_root() / "runs" / book.stem
    if run_override:
        for ext in (".yaml", ".md"):
            cand = slug_dir / f"run-{run_override}{ext}"
            if cand.exists():
                return cand, book
        raise ProgressError(f"run {run_override} not found under {slug_dir}")
    # default: book.current_run, else highest run in the dir
    bdoc = _detect_and_load(book, "promptbook")
    cur = bdoc.get("current_run")
    if cur:
        for ext in (".yaml", ".md"):
            cand = slug_dir / f"run-{cur}{ext}"
            if cand.exists():
                return cand, book
    hi = _highest_run(slug_dir)
    if hi is None:
        raise ProgressError(f"no runs found under {slug_dir}")
    return hi, book


# ----------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------
def _summarize(rows: list[dict]) -> tuple[Counter, int, int, int]:
    """Counts by state, total, terminal count and percent terminal for `rows`."""
    counts = Counter(r["state"] for r in rows)
    total = len(rows)
    terminal = sum(counts.get(s, 0) for s in TERMINAL_STATES)
    pct = round(100 * terminal / total) if total else 0
    return counts, total, terminal, pct


def build_model(run_path: Path, book_path: Path | None) -> dict:
    """Derive the progress model: rows of (n, title, module_tag, state) + counts."""
    run = _detect_and_load(run_path, "run")
    run_prompts = run.get("prompts", []) or []

    # module_tag join: only valid for a .yaml book whose hash matches the run.
    tag_by_n: dict[int, str] = {}
    joined = False
    if book_path is not None and book_path.suffix == ".yaml" and run_path.suffix == ".yaml":
        book = _detect_and_load(book_path, "promptbook")
        if run.get("book_content_hash") == compute_book_hash(book):
            for bp in book.get("prompts", []) or []:
                if bp.get("module_tag"):
                    tag_by_n[bp["n"]] = bp["module_tag"]
            joined = True

    rows = []
    for p in run_prompts:
        rows.append({
            "n": p["n"],
            "title": p.get("title", ""),
            "module_tag": tag_by_n.get(p["n"], "—") if joined else "—",
            "state": p.get("state", "pending"),
        })
    counts, total, terminal, pct = _summarize(rows)
    return {
        "run_id": run.get("run_id", run_path.stem),
        "book_id": run.get("book_id", ""),
        "status": run.get("status", ""),
        "rows": rows,
        "counts": counts,
        "total": total,
        "terminal": terminal,
        "done": counts.get("done", 0),
        "pct": pct,
        "tag_joined": joined,
    }


# ----------------------------------------------------------------------------
# Renderers
# ----------------------------------------------------------------------------
def _bar(pct: int, width: int = 24) -> str:
    filled = round(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def render_terminal(model: dict, color: bool) -> str:
    def c(code: str, s: str) -> str:
        return f"\033[{code}m{s}\033[0m" if color else s

    out = []
    out.append(f"{model['book_id']} · {model['run_id']} · {model['status']}")
    counts = model["counts"]
    breakdown = "  ".join(
        f"{GLYPH[s]} {counts.get(s, 0)} {s}" for s in STATES if counts.get(s, 0)
    )
    out.append(f"[{_bar(model['pct'])}] {model['pct']}%  ({model['terminal']}/{model['total']} terminal, {model['done']} done)")
    if breakdown:
        out.append(breakdown)
    out.append("")
    for r in model["rows"]:
        glyph = c(COLOR.get(r["state"], "2"), GLYPH.get(r["state"], "?"))
        tag = "" if r["module_tag"] == "—" else f" [{r['module_tag']}]"
        title = _sanitize(r["title"])
        out.append(f"  {glyph} {r['n']:>2}. {title}{tag}")
    return "\n".join(out) + "\n"


def render_markdown(model: dict) -> str:
    """Byte-stable artifact body — NO timestamps (the 'when' lives in docs/log.md)."""
    out = []
    out.append(f"# Run progress — {_sanitize(model['book_id'])} / {_sanitize(model['run_id'])}")
    out.append("")
    out.append(
        "> Regenerated by `run-promptbook` status. Body wholly rewritten "
        "on every run; hand-edits are blown away. No timestamps in the body — "
        "byte-stable given the same run state."
    )
    out.append("")
    out.append(f"**Status:** {_sanitize(model['status'])} · "
               f"**Progress:** {model['terminal']}/{model['total']} terminal ({model['pct']}%) · "
               f"**done:** {model['done']}")
    out.append("")
    counts = model["counts"]
    out.append("| state | count |")
    out.append("|-------|-------|")
    for s in STATES:
        out.append(f"| {s} | {counts.get(s, 0)} |")
    out.append("")
    if not model["tag_joined"]:
        out.append("_`module_tag` unavailable (legacy `.md` run or `book_content_hash` "
                   "mismatch on a plan edited in place); rendered as `—`._")
        out.append("")
    out.append("| n | state | module_tag | title |")
    out.append("|---|-------|------------|-------|")
    for r in model["rows"]:
        out.append(f"| {r['n']} | {GLYPH.get(r['state'], '?')} {r['state']} "
                   f"| {_md_cell(r['module_tag'])} | {_md_cell(r['title'])} |")
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------------------
# JSON mode (contained rendering for a dashboard)
# ----------------------------------------------------------------------------
JSON_FORMAT = "crux.run-progress"
JSON_FORMAT_VERSION = 2
# What `last_completed_status` says about the last completed run (active mode only).
JSON_LAST_COMPLETED_STATUSES = (
    "not-requested", "run-in-progress", "undetermined", "none", "latest", "latest-dated",
)
# The closed error-code set. An error envelope carries one of these and no other key.
JSON_ERROR_CODES = (
    "usage", "project-root-invalid", "config-invalid", "tree-missing", "containment",
    "book-not-found", "run-not-found", "run-invalid", "book-invalid",
    "token-set-unavailable", "yaml-unavailable", "time-limit", "internal",
)
# The actions a council's aggregate routes to (crux/council/async_council.py). A
# test pins this set to the literals that module assigns, without importing it.
JSON_ROUTE_ACTIONS = ("AUTO_EXECUTE", "EXECUTE_WITH_MONITORING", "DEFER_TO_HUMAN", "ABORT")
# The gate classes council_gate.classify returns for a prompt that is a gate.
JSON_GATE_CLASSES = ("council", "module-close", "independent-review")
_MAX_EVIDENCE = 20
# The dashboard launch gives the reader 10 s. The reader stops itself before
# that, so it never depends on which signal the launcher sends.
_JSON_TIME_LIMIT_S = 8
# Matches crux-mods view.ts EPOCH_MAX (2100-01-01); a parity test holds them equal.
_JSON_EPOCH_MAX = 4_102_444_800
_TITLE_CAP = 200
# The round bound of a module's council loop: an escalation entry needs the recorded rounds 1 to
# at least this round. crux-mods view.ts holds the same value as ESCALATION_ROUND; a parity test
# holds the two equal.
_ESCALATION_ROUND = 3
# The caps on the last completed run's summary, in code points; crux-mods holds the same three.
_SUMMARY_LINES_CAP = 240
_SUMMARY_LINE_CAP = 1000
_SUMMARY_TOTAL_CAP = 32000
# A summary splits on CRLF, LF and CR only. C0, DEL, C1 and the surrogate code points are
# removed from each line; U+2028 and U+2029 stay, because the mod removes them when it draws.
_SUMMARY_BREAK_RE = re.compile(r"\r\n|\n|\r")
_SUMMARY_STRIP_RE = re.compile("[\x00-\x1f\x7f-\x9f\ud800-\udfff]")
# One path segment of the mod's path alphabet; every name the reader reads or emits fits it.
_SAFE_NAME_RE = re.compile(r"[A-Za-z0-9._-]+", re.ASCII)
_MAX_READ_BYTES = 4 * 1024 * 1024
# C0 (tab and newline included), DEL and C1: wider than the terminal's _CONTROL_RE.
_JSON_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
# Every pattern that checks a value the JSON document emits is applied with
# fullmatch: `$` would admit a trailing newline.
_MODULE_TAG_RE = re.compile(r"[a-z]+-\d+", re.ASCII)
_BOOK_ID_RE = re.compile(r"(?:(?!(?:PB|ADR|RUN|BRIEF)-)[A-Z][A-Z0-9]{1,9}-)?PB-\d{4}", re.ASCII)
_EVIDENCE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}\.json", re.ASCII)
_RUN_YAML_RE = re.compile(r"^run-RUN-(\d{3})\.yaml$", re.ASCII)
_RUN_LEGACY_RE = re.compile(r"^run-RUN-(\d{3})\.md$", re.ASCII)
_RUN_PROGRESS_RE = re.compile(r"^run-RUN-\d{3}-progress\.md$", re.ASCII)
# The one time form the reader accepts as text: ASCII digits, `T` or one space, optional
# fraction, then `Z` or a numeric offset. Applied with fullmatch. `_TIME_TEXT` holds no
# group, so the plain closed form embeds it.
_TIME_TEXT = r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
_TIME_RE = re.compile(_TIME_TEXT, re.ASCII)
_RUN_ID_RE = re.compile(r"RUN-\d{3}", re.ASCII)
_SEMVER_RE = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]+)?", re.ASCII)
# Where the decision-token set is read from. Read by `ast`, never imported.
_RUN_COUNCIL = _HERE / "run-council.py"


# The top-level keys of crux/schemas/run.schema.json. A test holds the two equal, so a
# schema change fails that test; until this set is updated, a file that uses a new key is
# parsed and never skipped.
_RUN_TOP_KEYS = frozenset({
    "abandonment", "base_commit", "book_content_hash", "book_id", "completed_at", "current_prompt",
    "format_version", "implementation_bindings", "migration_bindings", "notes", "pr_draft",
    "prompts", "run_id", "started_at", "status", "summary",
})
# The line patterns of the plain closed form. Each is applied with fullmatch, at most once
# per line, and nests no quantifier, so its time is linear in the line.
_PLAIN_ENTRY_RE = re.compile(r"-(?: .*)?")
_PLAIN_KEY_RE = re.compile(r"([a-z_]+):(?: .*)?")
_PLAIN_STATUS_RE = re.compile(r"""status: +(["']?)(completed|abandoned)\1(?: *| +#.*)""")
_PLAIN_DATE_RE = re.compile(
    rf"""completed_at: +(?:(null)|({_TIME_TEXT})|'({_TIME_TEXT})'|"({_TIME_TEXT})") *""", re.ASCII)
# Every line break a YAML loader reads besides LF. A text that holds one is never plain.
_PLAIN_FOREIGN_BREAKS = ("\r", "\x85", "\u2028", "\u2029")


def _plain_scan(text: str) -> tuple[list[str], tuple[str, str] | None]:
    """Check `text` against the seven rules of the plain closed form, all of them.

    Returns the broken rules (`P1` to `P7`, sorted) and, when none is broken, the scanned
    (status, completed_at text) pair. The completed_at text has its matching quotes removed.
    The rules, with LF the only line break (P1) and a column-0 line one that is not empty
    and does not begin with a space:
      P2  every column-0 line is a comment, a sequence entry or a plain key of `_RUN_TOP_KEYS`;
      P3  the first line that is not empty and not a column-0 comment is a plain-key line;
      P4  no key occurs on two plain-key lines;
      P5  the next non-empty line after the status and completed_at lines is not indented;
      P6  a `status:` line exists and names a closed status;
      P7  a `completed_at:` line exists and holds `null` or a time.
    Under these a loader reads the same root `status` and `completed_at` as this scan does,
    for every text that loads to a schema-valid run; the module docstring states the proof."""
    broken: set[str] = set()
    if any(ch in text for ch in _PLAIN_FOREIGN_BREAKS):
        broken.add("P1")
    lines = text.split("\n")
    key_lines: dict[str, list[int]] = {}
    first = None  # the kind of the first line that is not empty and not a column-0 comment
    for index, line in enumerate(lines):
        if not line:
            continue
        lead = line[0]
        if lead == " ":
            kind = None
        elif lead == "#":
            continue
        elif lead == "-" and _PLAIN_ENTRY_RE.fullmatch(line):
            kind = "entry"
        else:
            match = _PLAIN_KEY_RE.fullmatch(line)
            if match is not None and match.group(1) in _RUN_TOP_KEYS:
                kind = "key"
                key_lines.setdefault(match.group(1), []).append(index)
            else:
                kind = "bad"
                broken.add("P2")
        if first is None:
            first = kind if lead != " " else "indented"
        # (an indented line is no column-0 line, so P2 does not read it)
    if first != "key":
        broken.add("P3")
    if any(len(places) > 1 for places in key_lines.values()):
        broken.add("P4")

    def indented_next(index: int) -> bool:
        index += 1
        while index < len(lines) and not lines[index]:
            index += 1
        return index < len(lines) and lines[index][0] in " \t"

    status = date = None
    for key in ("status", "completed_at"):
        for index in key_lines.get(key, []):
            if indented_next(index):
                broken.add("P5")
    status_places = key_lines.get("status", [])
    date_places = key_lines.get("completed_at", [])
    for index in status_places:
        match = _PLAIN_STATUS_RE.fullmatch(lines[index])
        if match is None:
            broken.add("P6")
        elif status is None:
            status = match.group(2)
    if not status_places:
        broken.add("P6")
    for index in date_places:
        match = _PLAIN_DATE_RE.fullmatch(lines[index])
        if match is None:
            broken.add("P7")
        elif date is None:
            date = next(g for g in match.groups() if g is not None)
    if not date_places:
        broken.add("P7")
    if broken:
        return sorted(broken), None
    return [], (status, date)


def _plain_broken_rules(text: str) -> list[str]:
    """The rules of the plain closed form that `text` breaks; empty when it is plain."""
    return _plain_scan(text)[0]


def _plain_closed(text: str) -> tuple[str, str] | None:
    """The scanned (status, completed_at text) of a text in plain closed form, else None."""
    return _plain_scan(text)[1]


class _OverTimeLimit(BaseException):
    """The reader ran past its own time limit. A BaseException, so no `except
    Exception` that refuses one file can swallow it."""


def _over_time_limit(_signum, _frame):
    raise _OverTimeLimit()


def _bound_json_process() -> None:
    """Stop this process before the dashboard's launch budget runs out.

    A wall-clock alarm at `limit` seconds raises _OverTimeLimit, which becomes the
    `time-limit` envelope. The soft CPU limit at `limit + 1` seconds sends SIGXCPU, whose
    default action kills the process. This call sets that default action, because an
    ignored SIGXCPU survives exec. The kill stops native code that ignores signals,
    where a Python handler would be deferred forever (Darwin sends SIGXCPU at the limit
    and never SIGKILL). The process is single-threaded, so CPU time never
    exceeds wall time; code that checks signals meets the alarm first and the CPU limit
    fires only for code that does not. That ordering holds while the process has used
    under one second of CPU before this call (RLIMIT_CPU counts from process start) and
    no inherited hard limit lies below `limit + 1`. The hard limit is the soft limit plus
    one second, or the inherited hard limit when that is lower; the soft limit never
    exceeds the hard one. The core file limit is zero, so the kill writes no core file
    holding tree text. Only the script's own entry point calls this; an in-process
    caller keeps its limits."""
    limit = _JSON_TIME_LIMIT_S
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _over_time_limit)
        signal.alarm(limit)
    if hasattr(signal, "SIGXCPU"):
        signal.signal(signal.SIGXCPU, signal.SIG_DFL)
    try:
        import resource  # noqa: PLC0415 — POSIX only
    except ImportError:
        return
    try:
        _soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        soft_new = limit + 1
        hard_new = soft_new + 1 if hard == resource.RLIM_INFINITY else min(hard, soft_new + 1)
        resource.setrlimit(resource.RLIMIT_CPU, (min(soft_new, hard_new), hard_new))
    except (ValueError, OSError):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, OSError):
        pass


class _JsonFailure(Exception):
    """A JSON-mode outcome that becomes an error envelope; carries only a code."""

    def __init__(self, code: str):
        assert code in JSON_ERROR_CODES
        self.code = code
        super().__init__(code)


class _Refused(Exception):
    """One tree file was not admitted. `reason` is a coarse class, never source text."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _json_title(title) -> str:
    """A prompt title for drawing: control characters removed, at most 200 code points."""
    if not isinstance(title, str):
        return ""
    return _JSON_CONTROL_RE.sub("", title)[:_TITLE_CAP]


def _summary_lines(text) -> tuple[list[str], bool]:
    """The summary as control-free lines, and whether a cap cut text.

    The final empty line that a trailing break leaves is dropped; an interior empty line and a
    line that control stripping empties stay as empty strings. Lines are kept in order, each cut
    to `_SUMMARY_LINE_CAP` code points, until `_SUMMARY_LINES_CAP` lines are kept or the total
    reaches `_SUMMARY_TOTAL_CAP`; the line that crosses the total is cut to fit and the rest
    drop. The flag is set when a cap removed any text."""
    if not isinstance(text, str) or not text:
        return [], False
    raw = _SUMMARY_BREAK_RE.split(text)
    if len(raw) > 1 and raw[-1] == "":
        raw.pop()
    kept: list[str] = []
    truncated = False
    used = 0
    for line in raw:
        line = _SUMMARY_STRIP_RE.sub("", line)
        if len(kept) >= _SUMMARY_LINES_CAP or used >= _SUMMARY_TOTAL_CAP:
            truncated = truncated or bool(line)
            continue
        cut = line[:min(_SUMMARY_LINE_CAP, _SUMMARY_TOTAL_CAP - used)]
        truncated = truncated or len(cut) < len(line)
        kept.append(cut)
        used += len(cut)
    return kept, truncated


def _epoch_in_range(seconds: int) -> int | None:
    return seconds if 0 <= seconds <= _JSON_EPOCH_MAX else None


def _time_s(value) -> int | None:
    """A time as whole epoch seconds, floored, or None.

    `value` is a string that fullmatches `_TIME_RE`, or a timezone-aware datetime. A naive
    time, any other value, an impossible date and a time outside 0 to `_JSON_EPOCH_MAX`
    give None. The fraction is dropped."""
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return None
        try:
            return _epoch_in_range(math.floor(value.timestamp()))
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or _TIME_RE.fullmatch(value) is None:
        return None
    try:
        if value[-1] == "Z":
            tz = datetime.timezone.utc
        else:
            offset = datetime.timedelta(hours=int(value[-5:-3]), minutes=int(value[-2:]))
            tz = datetime.timezone(-offset if value[-6] == "-" else offset)
        when = datetime.datetime(int(value[0:4]), int(value[5:7]), int(value[8:10]),
                                 int(value[11:13]), int(value[14:16]), int(value[17:19]), tzinfo=tz)
        return _epoch_in_range(math.floor(when.timestamp()))
    except (OverflowError, OSError, ValueError):
        return None


def _clock() -> float:
    """The reader's one clock read: the wall clock, in seconds since the epoch."""
    return time.time()


def _now_s() -> int | None:
    """The reader's clock at document build, floored; None when it lies outside the range."""
    try:
        return _epoch_in_range(math.floor(_clock()))
    except (OverflowError, ValueError, TypeError):
        return None


def _decision_tokens() -> frozenset:
    """The closed decision-token set, read from the installed run-council.py by `ast`.

    The script is parsed, never imported: importing it would run its module code.
    """
    try:
        tree = ast.parse(_RUN_COUNCIL.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "_DECISION_TOKENS" for t in node.targets):
                value = ast.literal_eval(node.value)
                if (isinstance(value, (tuple, list)) and value
                        and all(isinstance(v, str) and v for v in value)):
                    return frozenset(value)
                break
    except (OSError, SyntaxError, ValueError, TypeError, RecursionError, MemoryError, UnicodeError):
        pass
    raise _JsonFailure("token-set-unavailable")


def _reader_version() -> str:
    """The installed crux's version, from the plugin.json beside this script's directory."""
    try:
        version = json.loads((_HERE.parent / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, TypeError):
        raise _JsonFailure("internal")
    if not isinstance(version, str) or not _SEMVER_RE.fullmatch(version):
        raise _JsonFailure("internal")
    return version


def _json_dependencies():
    """Import the anchored-read helpers from the installed scripts directory.

    `scripts/` goes first on `sys.path` so a project directory can never supply
    one of these modules.
    """
    sys.path.insert(0, str(_HERE))
    import admission_source_io  # noqa: PLC0415
    import bionic_config  # noqa: PLC0415
    import council_gate  # noqa: PLC0415
    import council_records  # noqa: PLC0415
    return admission_source_io, bionic_config, council_records, council_gate


class _TreeReader:
    """Reads tree files through one anchored SourceIO and admits only files inside the tree."""

    def __init__(self, sio, tree: Path, refusal):
        self.sio = sio
        self.tree = tree
        self._refusal = refusal

    @staticmethod
    def rel(*parts: str) -> str:
        return "/".join(parts)

    @staticmethod
    def safe_name(name: str) -> bool:
        return _SAFE_NAME_RE.fullmatch(name) is not None

    def inside(self, path: Path) -> bool:
        """True when `path` resolves, through the anchor, to a place inside the tree."""
        try:
            return self.sio.resolve(path).is_relative_to(self.tree)
        except self._refusal:
            return False

    def glob(self, path: Path, pattern: str) -> list[Path]:
        try:
            return self.sio.glob(path, pattern)
        except self._refusal:
            raise _Refused("containment")

    def kind(self, path: Path):
        try:
            return self.sio.kind(path)
        except self._refusal:
            raise _Refused("containment")

    def read(self, path: Path) -> str:
        if not self.safe_name(path.name):
            raise _Refused("invalid")
        if not self.inside(path):
            raise _Refused("containment")
        try:
            data = self.sio.read_bytes(path, max_bytes=_MAX_READ_BYTES)
        except self._refusal:
            raise _Refused("containment")
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            raise _Refused("invalid")

    @staticmethod
    def refuse_anchors(text: str) -> None:
        """Refuse a document that holds an anchor or an alias, before any load expands it.

        A few kilobytes of chained aliases expand to billions of nodes, so the load must
        never see one. The scan reads parser events only and builds no node, so its cost
        stays linear in the document size. A document the parser rejects is refused too.
        """
        try:
            import yaml as _pyyaml  # noqa: PLC0415
        except ImportError:
            raise YamlCapabilityError("PyYAML is not importable in this interpreter")
        try:
            for event in _pyyaml.parse(text, Loader=_pyyaml.SafeLoader):
                if isinstance(event, _pyyaml.AliasEvent) or getattr(event, "anchor", None):
                    raise _Refused("invalid")
        except _Refused:
            raise
        except Exception:  # noqa: BLE001 — a parse failure is "invalid"; the text stays unsaid
            raise _Refused("invalid")

    def yaml(self, path: Path, kind: str) -> dict:
        """Parse and validate one run or promptbook in memory; never names source text."""
        text = self.read(path)
        self.refuse_anchors(text)
        try:
            doc = load_yaml(text)
        except YamlCapabilityError:
            raise
        except Exception:  # noqa: BLE001 — any parse failure is "invalid"; the text stays unsaid
            raise _Refused("invalid")
        if not isinstance(doc, dict) or "format_version" not in doc:
            raise _Refused("invalid")
        try:
            schema = _vp.load_schema(_vp.RUN_SCHEMA if kind == "run" else _vp.PROMPTBOOK_SCHEMA)
            errors: list[dict] = []
            _vp.validate(doc, schema, "#", "#", errors, kind)
            _vp.post_schema_pass(doc, errors, kind)
            if kind == "promptbook":
                _vp.cycle_coverage_pass(doc, errors, kind)
        except YamlCapabilityError:
            raise
        except Exception:  # noqa: BLE001
            raise _Refused("invalid")
        if errors:
            raise _Refused("invalid")
        return doc

    def find_book(self, book_id: str):
        """The first `active` then `archive` YAML book for `book_id` as (sub, path), or None."""
        for sub in ("active", "archive"):
            hits = self.glob(self.tree / "promptbooks" / sub, f"{book_id}-*.yaml")
            if hits:
                return sub, hits[0]
        return None


def _json_run_view(reader: _TreeReader, council_records, council_gate, tokens: frozenset,
                   run: dict, run_dir: Path, run_name: str, book, strict_book: bool,
                   docs_dir: str, with_summary: bool = False) -> dict:
    """Build one RunView. `book` is (sub, path) or None. A book that cannot be used
    raises in strict (target) mode and degrades to no book in active mode. A run
    whose ids are not exact ids raises _Refused: the schema checks them with `$`,
    which admits a trailing newline. Only the last completed run's view carries a summary
    (`with_summary`); every other view has an empty one."""
    if not (isinstance(run.get("run_id"), str) and _RUN_ID_RE.fullmatch(run["run_id"])
            and isinstance(run.get("book_id"), str) and _BOOK_ID_RE.fullmatch(run["book_id"])):
        raise _Refused("invalid")
    run_dir_rel = reader.rel("promptbooks", "runs", run_dir.name)
    book_doc, book_rel = None, None
    if book is not None:
        sub, book_path = book
        try:
            book_doc = reader.yaml(book_path, "promptbook")
            book_rel = reader.rel("promptbooks", sub, book_path.name)
        except _Refused as exc:
            if strict_book:
                raise _JsonFailure("containment" if exc.reason == "containment" else "book-invalid")
    tag_by_n: dict[int, str] = {}
    joined = False
    if book_doc is not None:
        try:
            joined = run.get("book_content_hash") == compute_book_hash(book_doc)
        except Exception:  # noqa: BLE001
            joined = False
        if joined:
            for bp in book_doc.get("prompts", []) or []:
                tag = bp.get("module_tag")
                if isinstance(tag, str) and _MODULE_TAG_RE.fullmatch(tag):
                    tag_by_n[bp["n"]] = tag
    rows = []
    for p in run.get("prompts", []) or []:
        state = p.get("state", "pending")
        rows.append({
            "n": p["n"], "title": _json_title(p.get("title", "")),
            "module_tag": tag_by_n.get(p["n"]) if joined else None,
            "state": state if state in STATES else "pending",
            "started_s": _time_s(p.get("started")), "completed_s": _time_s(p.get("completed")),
        })
    counts, total, terminal, pct = _summarize(rows)
    councils, skipped = _json_councils(reader, council_records, tokens, run["book_id"],
                                       run["run_id"], run_dir, run_dir_rel)
    current = run.get("current_prompt")
    gates = _json_gates(reader, council_gate, book_doc if joined else None, run, run_dir, docs_dir,
                        frozenset(c["record_path"] for c in councils))
    summary, summary_truncated = _summary_lines(run.get("summary")) if with_summary else ([], False)
    return {
        "book_id": run["book_id"], "run_id": run["run_id"], "status": run["status"],
        "current_prompt": current if isinstance(current, int) and not isinstance(current, bool) else None,
        "run_path": reader.rel(run_dir_rel, run_name), "book_path": book_rel,
        "modified_s": _modified_s(reader, run_dir / run_name),
        "started_s": _time_s(run.get("started_at")), "completed_s": _time_s(run.get("completed_at")),
        "tag_joined": joined,
        "progress": {"total": total, "terminal": terminal, "done": counts.get("done", 0), "pct": pct,
                     "counts": {s: counts.get(s, 0) for s in STATES}},
        "prompts": [{"n": r["n"], "state": r["state"], "module_tag": r["module_tag"],
                     "title": r["title"], "started_s": r["started_s"], "completed_s": r["completed_s"]}
                    for r in rows],
        "councils": councils, "councils_skipped": skipped, "gates": gates,
        "summary": summary, "summary_truncated": summary_truncated,
        "escalations": _json_escalations(run["status"], joined, rows, councils, skipped),
    }


def _json_escalations(status: str, joined: bool, rows: list[dict], councils: list[dict],
                      councils_skipped: int) -> list[dict]:
    """The modules whose recorded rounds show an escalation stop coming.

    A module is a module tag that a prompt of the joined book carries, with the run's councils
    tagged so; or, for councils with no tag (a patch book), a prompt that those councils bind. A
    module gets one entry when the run is in progress, the book joins, the module has an open
    prompt (one not `done` or `skipped`), no council file was refused, its `ran` records carry
    the rounds 1 to k exactly once with k at least `_ESCALATION_ROUND` (3), every one has its
    quorum met and none converged. The entry names the round-k record's prompt. The reader reads no attempt,
    refutation or owner-exception record and no git, so the entry says what the files show and
    never that the gate will stop: the gate counts only records whose seals and committed
    history hold (rule:gate-reads-every-recorded-round, rule:council-record-order-is-committed-order,
    rule:introducing-commit-is-unique-and-read-in-isolation)."""
    if status != "in_progress" or not joined or councils_skipped:
        return []
    state_of = {r["n"]: r["state"] for r in rows}
    tags = {r["module_tag"] for r in rows if r["module_tag"]}
    groups: dict[tuple, list[dict]] = {}
    for council in councils:
        tag = council["module_tag"]
        if tag is not None:
            if tag in tags:
                groups.setdefault((tag, None), []).append(council)
        elif council["prompt"] in state_of:
            groups.setdefault((None, council["prompt"]), []).append(council)
    entries = []
    for (tag, bound), group in groups.items():
        prompts = [r["n"] for r in rows if r["module_tag"] == tag] if tag is not None else [bound]
        if not any(state_of[n] not in ("done", "skipped") for n in prompts):
            continue
        ran = sorted((c for c in group if c["outcome"] == "ran"), key=lambda c: c["round"])
        rounds = [c["round"] for c in ran]
        k = len(ran)
        if k < _ESCALATION_ROUND or rounds != list(range(1, k + 1)):
            continue
        if not all(c["quorum_met"] for c in ran) or any(c["converged"] for c in ran):
            continue
        entries.append({"prompt": ran[-1]["prompt"], "module_tag": tag, "round": k})
    entries.sort(key=lambda e: (e["prompt"], e["module_tag"] or ""))
    return entries


def _modified_s(reader: _TreeReader, path: Path) -> int:
    """The run file's modification time, whole seconds since the epoch; 0 when the time
    cannot be read or lies beyond _JSON_EPOCH_MAX."""
    try:
        meta = reader.sio.metadata(path)
    except reader._refusal:
        return 0
    if not meta or not isinstance(meta.get("st_mtime_ns"), int):
        return 0
    seconds = max(0, meta["st_mtime_ns"] // 1_000_000_000)
    return seconds if seconds <= _JSON_EPOCH_MAX else 0


def _json_gates(reader: _TreeReader, council_gate, book_doc, run: dict, run_dir: Path,
                docs_dir: str, record_paths: frozenset) -> list[dict]:
    """The run's recorded gate results: one entry per prompt the cycle gate classifies
    as a gate, with its state and its evidence. Never reads prompt text, a result string
    or notes. Empty without a joined book.

    A council gate's evidence is only an attached artifact equal to the `record_path` of
    a council record this view validated (`record_paths`). A review gate's evidence is
    empty; `evidence_count` counts the distinct attached artifacts that name an existing
    file in the run's own `reviews/` directory, and no such file is read."""
    if book_doc is None:
        return []
    start = council_gate.StartFields.of(book_doc)
    state_by_n = {p["n"]: p for p in run.get("prompts", []) or [] if isinstance(p, dict)}
    out = []
    for bp in book_doc.get("prompts", []) or []:
        n = bp.get("n") if isinstance(bp, dict) else None
        if not isinstance(n, int) or isinstance(n, bool):
            continue
        try:
            cls = council_gate.classify(book_doc, n, start).cls
        except Exception:  # noqa: BLE001 — a book the gate cannot classify has no gates
            return []
        if cls not in JSON_GATE_CLASSES:
            continue
        row = state_by_n.get(n, {})
        state = row.get("state", "pending")
        review = cls == "independent-review"
        sub = "reviews" if review else "council"
        prefix = f"{docs_dir}/promptbooks/runs/{run_dir.name}/{sub}/"
        found: list[str] = []
        for artifact in row.get("artifacts", []) or []:
            if len(found) >= _MAX_EVIDENCE:
                break
            if not isinstance(artifact, str) or not artifact.startswith(prefix):
                continue
            name = artifact[len(prefix):]
            if not _EVIDENCE_NAME_RE.fullmatch(name):
                continue
            rel = reader.rel("promptbooks", "runs", run_dir.name, sub, name)
            if rel in found:
                continue
            if review:
                path = run_dir / sub / name
                try:
                    if reader.kind(path) != "file" or not reader.inside(path):
                        continue
                except _Refused:
                    continue
            elif rel not in record_paths:
                continue
            found.append(rel)
        out.append({"n": n, "gate_class": cls, "state": state if state in STATES else "pending",
                    "evidence": [] if review else found, "evidence_count": len(found)})
    return out


def _reject_constant(_name):
    # A council record with NaN or Infinity is not schema JSON, so it is counted as refused.
    raise ValueError("non-finite number")


def _json_councils(reader: _TreeReader, council_records, tokens: frozenset, book_id: str,
                   run_id: str, run_dir: Path, run_dir_rel: str) -> tuple[list[dict], int]:
    """Council records under the run's own `council/` directory, plus the count not admitted."""
    directory = run_dir / "council"
    try:
        names = reader.glob(directory, "*.json")
    except _Refused:
        return [], 1
    if names and not reader.inside(directory):
        return [], 1
    out, skipped = [], 0
    other_types = frozenset(council_records.RECORD_TYPES) - {"council-record"}
    for path in names:
        try:
            doc = json.loads(reader.read(path), parse_constant=_reject_constant)
            if isinstance(doc, dict) and doc.get("record_type") in other_types:
                continue  # an attempt, owner-exception or other record: not a council, not refused
            if not isinstance(doc, dict) or council_records.schema_errors(doc, "council-record"):
                raise _Refused("invalid")
            if doc["run_id"] != run_id or doc["book"]["id"] != book_id:
                raise _Refused("invalid")
            # The schema checks the tag with \d, which admits non-ASCII digits.
            tag = doc["binding"]["module_tag"]
            if tag is not None and not (isinstance(tag, str) and _MODULE_TAG_RE.fullmatch(tag)):
                raise _Refused("invalid")
            out.append(_json_council_view(doc, tokens, reader.rel(run_dir_rel, "council", path.name)))
        except YamlCapabilityError:
            raise
        except Exception:  # noqa: BLE001 — a record that fails for any reason is counted, never named
            skipped += 1
    out.sort(key=lambda c: (c["prompt"], c["round"], c["record_path"]))
    return out, skipped


def _closed(value, tokens):
    return value if isinstance(value, str) and value in tokens else None


def _is_nit(finding: dict) -> bool:
    """The council record schema's nit rule, the same predicate as
    `council_history_v4.is_blocking` negated: `kind` is `nit`, `dimension` is present and
    not Security, and `safety_adjacent` is false. Every other finding blocks."""
    dim = finding.get("dimension")
    return (finding.get("kind") == "nit" and isinstance(dim, str) and bool(dim.strip())
            and dim.strip().lower() != "security" and finding.get("safety_adjacent") is False)


_APPROVING = ("APPROVE", "APPROVE_WITH_NITS")


def _converged(doc: dict) -> bool:
    """Whether one council record converged, by the gate's per-record rule
    (rule:convergence-is-derived-per-seat): the record ran, its quorum is met, every seat
    that did not error approved, and no such seat carries a blocking finding. A test holds
    this equal to `council_history_v4._analyze`, which the reader never calls: that module
    holds the gate's git readers, and JSON mode runs no git. (council_gate imports the
    module; importing it runs no git.)"""
    if doc.get("outcome") != "ran" or not doc.get("quorum_met"):
        return False
    for seat in doc.get("seats", []):
        if seat.get("errored"):
            continue
        if seat.get("decision") not in _APPROVING:
            return False
        if not all(_is_nit(f) for f in seat.get("findings", [])):
            return False
    return True


def _json_council_view(doc: dict, tokens: frozenset, record_path: str) -> dict:
    seats = []
    for seat in doc["seats"]:
        findings = seat.get("findings", [])
        nit = sum(1 for f in findings if _is_nit(f))
        seats.append({
            "role": seat["role"], "decision": _closed(seat.get("decision"), tokens),
            "errored": bool(seat["errored"]), "findings": {"blocking": len(findings) - nit, "nit": nit},
        })
    return {
        "record_path": record_path, "prompt": doc["binding"]["prompt"],
        "module_tag": doc["binding"]["module_tag"], "council_kind": doc["council_kind"],
        "round": doc["round"], "outcome": doc["outcome"], "quorum_met": bool(doc["quorum_met"]),
        "degraded": bool(doc["degraded"]),
        "aggregate_action": _closed(doc["aggregate"].get("action"), JSON_ROUTE_ACTIONS),
        "converged": _converged(doc), "seats": seats,
    }


class _Candidate(NamedTuple):
    """A dated completed run the scan saw: its discovery date in epoch seconds, its path
    relative to the tree (the tie-break) and the places a view needs. An undated completed run
    is only counted, never made a candidate."""

    date: int
    rel: str
    path: Path
    entry: Path


class _RunScan(NamedTuple):
    found: list  # (doc, path, entry) for each schema-valid in-progress run
    skipped: int  # files the reader refused or could not read
    unresolved: int  # entries that may hold a run in progress or a newer completed run
    undated: int  # completed candidates whose date gives no seconds
    dated: list  # the dated _Candidate list


def _active_runs(reader: _TreeReader) -> _RunScan:
    """Scan `promptbooks/runs/` for schema-valid in-progress YAML runs and for completed ones.

    A file in plain closed form is never parsed: its scanned status and date decide. Any other
    file is parsed in full. Every path that could hide a run in progress or a newer completed
    run counts in `unresolved`. The paths that cannot (a loose file, a progress render, a
    legacy Markdown run, an abandoned run) count in neither `unresolved` nor `undated`; a legacy
    Markdown run, and a loose file whose name is outside the path alphabet, still count in
    `skipped`."""
    runs_dir = reader.tree / "promptbooks" / "runs"
    if not reader.inside(runs_dir):
        raise _JsonFailure("containment")
    found: list = []
    dated: list = []
    skipped = unresolved = undated = 0
    try:
        entries = reader.glob(runs_dir, "*")
    except _Refused:
        raise _JsonFailure("containment")

    def candidate(date, path, entry):
        nonlocal undated
        if date is None:
            undated += 1
        else:
            dated.append(_Candidate(date, reader.rel("promptbooks", "runs", entry.name, path.name), path, entry))

    for entry in entries:
        try:
            if not reader.safe_name(entry.name):
                if reader.kind(entry) == "file":
                    skipped += 1  # a loose file holds no run, whatever its name
                    continue
                raise _Refused("invalid")
            kind = reader.kind(entry)
            if kind is None:
                unresolved += 1  # the entry vanished after the listing
                continue
            if kind != "directory":
                continue  # a loose file holds no run: a run lives at runs/<book>/run-RUN-NNN.yaml
            if not reader.inside(entry):
                raise _Refused("containment")
            files = reader.glob(entry, "run-RUN-*")
        except _Refused:
            skipped += 1
            unresolved += 1
            continue
        for path in files:
            name = path.name
            if _RUN_PROGRESS_RE.fullmatch(name):
                continue  # this reader's own Markdown render
            if _RUN_LEGACY_RE.fullmatch(name):
                skipped += 1  # a legacy Markdown run is never in progress and never ranked
                continue
            if not _RUN_YAML_RE.fullmatch(name):
                skipped += 1  # a name outside the run-file pattern
                unresolved += 1
                continue
            try:
                text = reader.read(path)
            except _Refused:
                skipped += 1
                unresolved += 1
                continue
            plain = _plain_closed(text)
            if plain is not None:
                if plain[0] == "completed":
                    candidate(_time_s(plain[1]), path, entry)
                continue  # a closed run is never reported, so it is not parsed
            try:
                doc = reader.yaml(path, "run")
            except _Refused:
                skipped += 1
                unresolved += 1
                continue
            if doc.get("status") == "in_progress":
                found.append((doc, path, entry))
            elif doc.get("status") == "completed":
                candidate(_time_s(doc.get("completed_at")), path, entry)
    return _RunScan(found, skipped, unresolved, undated, dated)


def _last_completed_view(reader: _TreeReader, council_records, council_gate, tokens: frozenset,
                         top: _Candidate, docs_dir: str):
    """The RunView of the newest dated completed run, or None when the run cannot be shown.

    This is the one parse of the search. The run must validate, still be `completed`, and carry
    the same completion time in seconds as the scan dated it by; a file that changed between
    the two reads, or a defect in `_plain_closed`, gives None and the caller reports
    `undetermined`."""
    try:
        doc = reader.yaml(top.path, "run")
        if doc.get("status") != "completed" or _time_s(doc.get("completed_at")) != top.date:
            return None
        try:
            book = reader.find_book(doc["book_id"])
        except _Refused:
            book = None
        return _json_run_view(reader, council_records, council_gate, tokens, doc, top.entry,
                              top.path.name, book, strict_book=False, docs_dir=docs_dir,
                              with_summary=True)
    except _Refused:
        return None


def _target_run(reader: _TreeReader, target: str, run_id):
    """Resolve PB-NNNN [+ run id] to (run doc, run path, run dir, book) or raise."""
    try:
        book = reader.find_book(target)
    except _Refused:
        raise _JsonFailure("containment")
    if book is None:
        raise _JsonFailure("book-not-found")
    try:
        book_doc = reader.yaml(book[1], "promptbook")
    except _Refused as exc:
        raise _JsonFailure("containment" if exc.reason == "containment" else "book-invalid")
    run_dir = reader.tree / "promptbooks" / "runs" / book[1].stem
    try:
        names = reader.glob(run_dir, "run-RUN-*")
    except _Refused:
        raise _JsonFailure("containment")
    candidates = {}
    for path in names:
        for rx in (_RUN_YAML_RE, _RUN_LEGACY_RE):
            m = rx.fullmatch(path.name)
            if m:
                candidates[(int(m.group(1)), path.suffix)] = path
    wanted = run_id or book_doc.get("current_run")
    chosen = None
    if isinstance(wanted, str) and _RUN_ID_RE.fullmatch(wanted):
        number = int(wanted[4:])
        chosen = candidates.get((number, ".yaml")) or candidates.get((number, ".md"))
    if chosen is None and not run_id and candidates:
        # the book names no usable current run: the highest run wins, .yaml over .md
        chosen = candidates[max(candidates, key=lambda k: (k[0], 1 if k[1] == ".yaml" else 0))]
    if chosen is None:
        raise _JsonFailure("run-not-found")
    if chosen.suffix != ".yaml":
        raise _JsonFailure("run-invalid")  # legacy .md runs are refused
    try:
        doc = reader.yaml(chosen, "run")
    except _Refused as exc:
        raise _JsonFailure("containment" if exc.reason == "containment" else "run-invalid")
    return doc, chosen, run_dir, book


def _require_yaml_without_reexec() -> None:
    """Run the PyYAML guard with uv re-exec off, whatever the caller's environment says.

    A dashboard must never start a package manager. With re-exec off the guard
    raises when PyYAML is missing instead of replacing this process.
    """
    saved = os.environ.get("CRUX_NO_UV_REEXEC")
    os.environ["CRUX_NO_UV_REEXEC"] = "1"
    try:
        ensure_real_yaml(__file__)
    except YamlCapabilityError:
        raise _JsonFailure("yaml-unavailable")
    finally:
        if saved is None:
            os.environ.pop("CRUX_NO_UV_REEXEC", None)
        else:
            os.environ["CRUX_NO_UV_REEXEC"] = saved


def _build_json_document(args) -> dict:
    """The success document for `args`, or a raised _JsonFailure."""
    root_text = args.project_root
    if root_text is None or not os.path.isabs(root_text):
        raise _JsonFailure("project-root-invalid")
    try:
        if not Path(root_text).is_dir():
            raise _JsonFailure("project-root-invalid")
    except OSError:
        raise _JsonFailure("project-root-invalid")
    _require_yaml_without_reexec()
    admission_source_io, bionic_config, council_records, council_gate = _json_dependencies()
    refusal = admission_source_io.SourceIORefusal
    try:
        sio = admission_source_io.SourceIO(Path(root_text), max_bytes=_MAX_READ_BYTES)
    except refusal:
        raise _JsonFailure("project-root-invalid")
    try:
        try:
            cfg = bionic_config.load_config(sio.root, require_tree=True, _source_io=sio)
        except refusal:
            raise _JsonFailure("containment")
        except bionic_config.BionicConfigError:
            # Tell a missing tree from a bad layout config: the same call without the tree check.
            try:
                bionic_config.load_config(sio.root, require_tree=False, _source_io=sio)
            except refusal:
                raise _JsonFailure("containment")
            except bionic_config.BionicConfigError:
                raise _JsonFailure("config-invalid")
            raise _JsonFailure("tree-missing")
        if (_JSON_CONTROL_RE.search(cfg.docs_dir)
                or not all(_SAFE_NAME_RE.fullmatch(seg) for seg in cfg.docs_dir.split("/"))):
            raise _JsonFailure("config-invalid")
        tokens = _decision_tokens()
        version = _reader_version()
        reader = _TreeReader(sio, cfg.docs_root, refusal)
        views, skipped = [], 0
        now_s = _now_s()
        last_completed, last_status, undated, unresolved = None, "not-requested", 0, 0
        if args.target is None:
            scan = _active_runs(reader)
            skipped, undated, unresolved = scan.skipped, scan.undated, scan.unresolved
            for doc, path, run_dir in scan.found:
                try:
                    book = reader.find_book(doc["book_id"])
                except _Refused:
                    book = None
                try:
                    views.append(_json_run_view(reader, council_records, council_gate, tokens, doc,
                                                run_dir, path.name, book, strict_book=False,
                                                docs_dir=cfg.docs_dir))
                except _Refused:
                    skipped += 1
            if scan.found:
                last_status = "run-in-progress"
            elif unresolved:
                last_status = "undetermined"
            elif not scan.dated:
                last_status = "none" if undated == 0 else "undetermined"
            else:
                top = max(scan.dated, key=lambda c: (c.date, c.rel))
                last_completed = _last_completed_view(reader, council_records, council_gate, tokens,
                                                      top, cfg.docs_dir)
                if last_completed is None:
                    last_status = "undetermined"
                    skipped += 1
                    unresolved += 1
                else:
                    last_status = "latest" if undated == 0 else "latest-dated"
        else:
            doc, path, run_dir, book = _target_run(reader, args.target, args.run)
            try:
                views.append(_json_run_view(reader, council_records, council_gate, tokens, doc,
                                            run_dir, path.name, book, strict_book=True,
                                            docs_dir=cfg.docs_dir))
            except _Refused:
                raise _JsonFailure("run-invalid")
        views.sort(key=lambda r: (r["book_id"], r["run_id"]))
        return {
            "format": JSON_FORMAT, "format_version": JSON_FORMAT_VERSION, "ok": True,
            "reader_version": version, "docs_dir": cfg.docs_dir, "now_s": now_s,
            "runs": views, "runs_skipped": skipped, "last_completed": last_completed,
            "last_completed_status": last_status, "last_completed_undated": undated,
            "last_completed_unresolved": unresolved,
        }
    except _Refused:
        raise _JsonFailure("containment")
    finally:
        sio.close()


def _json_error(code: str) -> dict:
    return {"format": JSON_FORMAT, "format_version": JSON_FORMAT_VERSION, "ok": False,
            "error": {"code": code}}


def _json_main(args, usage_error: str | None, bound: bool = False) -> int:
    """Print exactly one JSON object and a newline on stdout; nothing on stderr."""
    code = 0
    with _NoBytecode():
        try:
            # The outer try also covers the handlers below: an alarm that lands inside
            # one of them still yields the `time-limit` envelope, not a traceback.
            try:
                if bound:
                    _bound_json_process()
                if usage_error is not None:
                    raise _JsonFailure("usage")
                if args.markdown or args.terminal or not args.project_root:
                    raise _JsonFailure("usage")
                if args.target is not None and not _BOOK_ID_RE.fullmatch(args.target):
                    raise _JsonFailure("usage")
                if args.run is not None and (args.target is None or not _RUN_ID_RE.fullmatch(args.run)):
                    raise _JsonFailure("usage")
                document = _build_json_document(args)
            except _OverTimeLimit:
                raise
            except _JsonFailure as failure:
                document = _json_error(failure.code)
                code = 2 if failure.code == "yaml-unavailable" else 1
            except Exception:  # noqa: BLE001 — no traceback, no message: an unexpected failure is `internal`
                document = _json_error("internal")
                code = 1
        except _OverTimeLimit:
            document = _json_error("time-limit")
            code = 1
        finally:
            if bound and hasattr(signal, "SIGALRM"):
                signal.alarm(0)
    sys.stdout.write(json.dumps(document, ensure_ascii=True) + "\n")
    return code


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _use_color(force: bool | None) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if force is not None:
        return force
    return sys.stdout.isatty()


class _UsageError(Exception):
    """Raised by the JSON-mode parser instead of printing usage and exiting."""


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise _UsageError(message)


def _build_parser(json_mode: bool) -> argparse.ArgumentParser:
    cls = _JsonArgumentParser if json_mode else argparse.ArgumentParser
    kwargs = {"add_help": False} if json_mode else {}
    ap = cls(
        prog="visualize-run-progress",
        description="Render a promptbook run snapshot's progress (terminal view, byte-stable "
                    "Markdown artifact, or a contained JSON view with --json).",
        **kwargs,
    )
    ap.add_argument("target", nargs="?", default=None,
                    help="A PB-NNNN id or a path to a run snapshot (.yaml/.md). With --json: an "
                         "optional PB-NNNN id; omitted, every in-progress run is reported.")
    ap.add_argument("--run", dest="run", default=None, metavar="RUN-NNN",
                    help="Select a specific run when target is a PB-NNNN id (default: current_run, else highest).")
    ap.add_argument("--markdown", action="store_true", help="Write the byte-stable progress.md artifact.")
    ap.add_argument("--terminal", action="store_true", help="Print the terminal view (default when neither flag is given).")
    ap.add_argument("--no-color", action="store_true", help="Disable ANSI color (also honors NO_COLOR / non-TTY).")
    ap.add_argument("--json", action="store_true",
                    help="Print one JSON object (the contained dashboard view); requires --project-root.")
    ap.add_argument("--project-root", dest="project_root", default=None, metavar="ABSOLUTE_DIR",
                    help="With --json: the project whose documentation tree is read (absolute path).")
    return ap


def main(argv: list[str] | None = None, bound: bool = False) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    # "--j" through "--json" can only abbreviate --json; a JSON-mode caller gets an
    # envelope for every outcome, including a malformed command line.
    json_mode = any(a.startswith("--j") and "--json".startswith(a) for a in argv_list)
    ap = _build_parser(json_mode)
    if json_mode:
        try:
            args, usage_error = ap.parse_args(argv_list), None
        except _UsageError as exc:
            args, usage_error = argparse.Namespace(), str(exc)
        return _json_main(args, usage_error, bound)
    args = ap.parse_args(argv_list)
    if args.target is None:
        ap.error("the following arguments are required: target")
    if args.project_root is not None:
        print("visualize-run-progress: --project-root is only valid with --json", file=sys.stderr)
        return 1
    # Correctness-critical: the module_tag join verifies book_content_hash, so
    # parse fidelity matters — require real YAML (PB-0026), uv-repair if
    # possible. After parse_args so --help works without PyYAML.
    try:
        ensure_real_yaml(__file__)
    except YamlCapabilityError as exc:
        print(f"visualize-run-progress: {exc}", file=sys.stderr)
        return 2

    try:
        run_path, book_path = resolve(args.target, args.run)
        model = build_model(run_path, book_path)
        wrote = None
        if args.markdown:
            artifact = run_path.with_name(run_path.stem + "-progress.md")
            artifact.write_text(render_markdown(model), encoding="utf-8")
            wrote = artifact
        if args.terminal or not args.markdown:
            color = _use_color(False if args.no_color else None)
            sys.stdout.write(render_terminal(model, color))
        if wrote is not None:
            print(f"wrote {wrote}", file=sys.stderr)
    except ProgressError as e:
        # _sanitize: an error can embed an attacker-adjacent filename; strip
        # control bytes so a crafted name can't smuggle terminal escapes.
        print(f"visualize-run-progress: {_sanitize(str(e))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(bound=True))
