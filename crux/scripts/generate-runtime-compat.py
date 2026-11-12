#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""generate-runtime-compat.py — the vendored regenerator for the runtime-compatibility block.

The fifteenth regenerative output (per ADR-0056's enrollment discipline,
established by ADR-0100 point 7). One canonical file, one projected region in
every non-exempt `crux/skills/*/SKILL.md`:

    canonical   crux/templates/runtime-compatibility.md   (the WHOLE file body)
    projection  crux/skills/<name>/SKILL.md   between BEGIN/END GENERATED: runtime-compat

The provenance note above lives HERE and not in the canonical file, and that is
a constraint rather than a preference. `check-public-release-content.py` fails
on the `ADR-\\d{4}` token anywhere under `crux/skills`, `crux/agents` or
`crux/templates`, line by line, with no carve-out for an HTML comment. The
canonical file and all of its projections sit in those roots, so neither may
cite an ADR by number. `crux/scripts/` is not one of those roots, exactly as
`generate-writing-rules.py` relies on.

This file follows `generate-writing-rules.py` deliberately and closely — same
whole-line marker matching, same fail-closed region resolution, same
validate-everything-then-write-anything ordering, same atomic mode-preserving
write. The two regenerators are NOT merged into one shared module in this
change: that refactor would put every writing-rules target at risk for a
benefit this output does not need. The duplication is named rather than hidden.

Properties, each with a test:

1. **No newline translation in transit.** Files are read and written with
   `newline=""`, so nothing rewrites an ending on the way through and a CRLF
   target keeps its CRLF endings everywhere outside the projected region. The
   region's own boundaries are NOT byte-preserving: `_load_canonical` returns
   `"\\n" + body.strip("\\r\\n") + "\\n"`, which hard-codes LF at both ends. A
   CRLF canonical body therefore projects its last content line with a bare LF,
   leaving the region not byte-equivalent to that body and mixing endings
   inside it. That costs nothing today because the canonical file is LF, and
   nothing enforces that it stays LF. `test_crlf_line_endings_survive` converts
   the TARGET only and asserts outside the region, so it covers the half that
   holds and not the half that does not.
2. **Markers are matched as whole lines**, tolerating trailing blanks and a
   `\\r`, so a marker mentioned mid-sentence is never a delimiter.
3. **Every target is validated before any target is written**, and each write is
   atomic (temp file + `os.replace`) with the original mode preserved.
4. **The canonical body may not contain the projection markers**, which would
   inject a second delimiter into every target and wedge every later run.
5. **Target derivation fails closed.** Targets are derived from the BEGIN
   marker, then cross-checked against the skill catalog on three legs: every
   catalogued skill must be either marked or named in `EXEMPT_SKILLS`; no
   exempt skill may carry the markers; and every `EXEMPT_SKILLS` entry must
   still name a catalogued skill. A skill that silently loses its markers
   FAILS rather than dropping out of the projection, a skill that is both
   marked and exempt fails, and an exemption left behind by a deleted skill
   fails — so the exemption list rots in no direction.

Residual risk, stated rather than papered over: a marker on its own line inside
a fenced code block IS counted as a marker. A target carrying real markers PLUS
a fenced example raises a loud duplicate-marker error and writes nothing, which
is the common case and fails closed. A target whose ONLY marker pair lives
inside a fence would be mis-delimited; nothing here prevents that, and what
prevents it today is that no target is authored that way.

The declared input set has four parts: the canonical file and the skill
catalog (required files named by path), the `crux/skills` directory (listed),
and each `<skill>/SKILL.md` (a catalogue member when the catalog names the
skill, a listed candidate otherwise). Each input takes one lane:

* A required file that is confirmed absent (its `stat` fails with ENOENT or
  ENOTDIR), or that cannot be opened, read or decoded for a cause at its path,
  is a document-lane finding naming it.[^file] So is a catalogued skill whose
  SKILL.md is confirmed absent,[^member] and a listed SKILL.md absent at open.
* A failure for any other cause (EIO, descriptor or memory exhaustion) takes
  the environment lane naming the input,[^process] and so does a skills
  directory that exists and cannot be listed, or whose existence cannot be
  determined.[^unlistable] A confirmed-absent skills directory is a finding.
* The run tries every input and every target before it exits. A check that
  depends on a refused input is skipped, so only that input's own finding is
  reported: the catalogue checks depend on the catalog, and the region
  comparison and the planned write depend on the canonical file. A run that
  met an environment-lane failure takes that lane and names its document
  findings on stderr.[^precedence] Every refusal writes nothing.

Exit codes (the contract every sibling regenerator follows):
    0  clean — wrote (or, under --dry-run, found no drift)
    1  drift (--dry-run, `{"drifted": ...}`) or document-lane refusal
       (`{"validation_errors": [{"file", "error"}, ...]}`), with JSON on stdout
    2  environment-lane failure, or a pass-2 write failure: nothing on stdout,
       a message on stderr

[^file]: rule:path-attributable-read-failure-is-a-document-finding
[^member]: rule:absent-catalogue-member-is-a-document-finding
[^process]: rule:process-level-read-failure-is-an-environment-failure
[^unlistable]: rule:unlistable-input-directory-is-an-environment-failure
[^precedence]: rule:environment-failure-takes-precedence
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

CANONICAL_FILE = "crux/templates/runtime-compatibility.md"
SKILLS_DIR = "crux/skills"
CATALOG_FILE = "crux/catalog/skills.json"

PROJECTION_BEGIN = "<!-- BEGIN GENERATED: runtime-compat -->"
PROJECTION_END = "<!-- END GENERATED: runtime-compat -->"

# Skills that carry NO runtime-compatibility block, exempt by name. Measured
# against the 60-skill catalog: 56 carry the block byte-identically and these
# four do not. Property 5 above polices this list on all three of its failure
# modes — an exempt skill that grows markers fails, a non-exempt skill that
# loses them fails, and an entry naming a skill the catalog no longer carries
# fails.
EXEMPT_SKILLS = frozenset(
    {
        "escalate-arch-runtime",
        "prose-review",
        "recover-decisions",
        "transition-decision",
    }
)


sys.path.insert(0, str(Path(__file__).resolve().parent))
import authoring_scope as _scope  # noqa: E402
import input_lanes  # noqa: E402

SCRIPT_NAME = "generate-runtime-compat.py"
#: The file that holds EXEMPT_SKILLS: the repair path for an exemption finding.
SCRIPT_FILE = f"crux/scripts/{SCRIPT_NAME}"

_ABSENT_DIRECTORY_REASON = (
    "is the required skills directory and is absent — restore the directory at "
    "this path")


class RegenError(Exception):
    """A document-lane refusal: exit 1 with `validation_errors` on stdout.

    `errors` is the full list of `{"file", "error"}` entries, each naming the
    repository-relative path whose repair clears it. `str(exc)` joins them.
    """

    def __init__(self, errors: list[dict]) -> None:
        self.errors = [dict(e) for e in errors]
        super().__init__("; ".join(f"{e['file']}: {e['error']}" for e in self.errors))


class _Lanes:
    """The findings and environment failures one run meets, collected before exit."""

    def __init__(self) -> None:
        self.findings: list[dict] = []
        self.failures: list[str] = []

    def finding(self, rel: str, error: str) -> None:
        self.findings.append({"file": rel, "error": error})

    def read_failure(self, rel: str, exc: BaseException) -> None:
        """Classify a failed stat, open, read or decode of the input `rel`."""
        if input_lanes.is_path_attributable(exc):
            self.finding(rel, input_lanes.document_reason(exc))
        else:
            self.failures.append(input_lanes.environment_reason(rel, exc))

    def raise_if_refused(self) -> None:
        if self.failures:
            raise input_lanes.EnvironmentLaneError(self.failures, self.findings)
        if self.findings:
            raise RegenError(self.findings)


def _repo_root(explicit: str | None) -> Path:
    """The project root under inspection -- never this script's own location.

    `Path(__file__).parents[2]` used to stand here. In the authoring checkout it
    lands on the repo root and looks right; in an installed plugin it lands on the
    plugin cache, so a gate run from a consuming project inspected the plugin's own
    copy of itself and reported the result as if it were the project's.
    """
    return _scope.resolve_repo_root(explicit)


def read_text_verbatim(path: Path) -> str:
    """Read without universal-newline translation, so line endings survive."""
    with path.open("r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write_text_atomically(path: Path, text: str) -> None:
    """Write via a temp file in the same directory, then atomically replace.

    The original file's permission bits are copied onto the temp file before
    the replace. `mkstemp` creates 0600 and `os.replace` carries that mode onto
    the target, so without this every regeneration would silently turn a 0644
    document into an owner-only one.
    """
    mode = path.stat().st_mode
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        os.fchmod(fd, stat.S_IMODE(mode))
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _marker_line(marker: str) -> re.Pattern[str]:
    """Match the marker only as a whole line (surrounding blanks tolerated).

    `\\r` is in the trailing class deliberately: reads use `newline=""`, so a
    CRLF file keeps its `\\r`, and `$` in MULTILINE mode matches before the
    `\\n` — with the `\\r` still sitting between the marker and the `$`.
    Omitting it makes every marker in a CRLF file invisible.
    """
    return re.compile(r"^[ \t]*" + re.escape(marker) + r"[ \t\r]*$", re.MULTILINE)


def has_marker(text: str, marker: str = PROJECTION_BEGIN) -> bool:
    return _marker_line(marker).search(text) is not None


def find_region(text: str, begin: str, end: str, label: str) -> tuple[int, int]:
    """Return (start, end) offsets of the bytes strictly between the marker lines.

    Fails closed on anything ambiguous: a missing marker, a duplicate marker,
    or END before BEGIN. Never guesses an insertion point.
    """
    def refuse(error: str) -> RegenError:
        return RegenError([{"file": label, "error": error}])

    b = _marker_line(begin).findall(text)
    e = _marker_line(end).findall(text)
    if len(b) == 0 or len(e) == 0:
        missing = "BEGIN" if len(b) == 0 else "END"
        raise refuse(
            f"missing marker ({missing} not found as its own line). "
            f"Expected exactly one line {begin!r} and one line {end!r}."
        )
    if len(b) > 1 or len(e) > 1:
        raise refuse(
            f"duplicate marker (BEGIN x{len(b)}, END x{len(e)}). "
            "Exactly one of each is required; refusing to guess which pair is real."
        )
    mb = _marker_line(begin).search(text)
    me = _marker_line(end).search(text)
    assert mb is not None and me is not None  # counts above guarantee both
    if me.start() < mb.end():
        raise refuse("END marker precedes BEGIN marker.")
    return mb.end(), me.start()


def extract_region(text: str, begin: str, end: str, label: str) -> str:
    i, j = find_region(text, begin, end, label)
    return text[i:j]


def replace_region(text: str, begin: str, end: str, body: str, label: str) -> str:
    i, j = find_region(text, begin, end, label)
    return text[:i] + body + text[j:]


def _read_required(root: Path, rel: str, lanes: _Lanes) -> str | None:
    """Read the required file `rel`, or record why it cannot be read and return None.

    `path_state` decides its presence: a confirmed absence is a finding. A
    failed stat, open, read or decode is classified by its cause.
    """
    path = root / rel
    try:
        if input_lanes.path_state(path) is None:
            lanes.finding(rel, input_lanes.absent_reason("file"))
            return None
        return read_text_verbatim(path)
    except (OSError, UnicodeDecodeError, MemoryError) as exc:
        lanes.read_failure(rel, exc)
        return None


def _canonical(root: Path, lanes: _Lanes) -> str | None:
    """The whole canonical file body, normalized to one leading and one trailing newline.

    The projected region is the bytes strictly between the two marker LINES, so
    it necessarily opens with the newline that ends the BEGIN line and closes
    with the newline that starts the END line. Normalizing here is what makes
    regeneration idempotent regardless of how many blank lines the canonical
    file happens to end with. Returns None when the file is refused.
    """
    body = _read_required(root, CANONICAL_FILE, lanes)
    if body is None:
        return None
    if not body.strip():
        lanes.finding(CANONICAL_FILE, "canonical file is empty; refusing to project nothing.")
        return None
    for marker in (PROJECTION_BEGIN, PROJECTION_END):
        if marker in body:
            lanes.finding(
                CANONICAL_FILE,
                f"the canonical body contains the projection marker {marker!r}. "
                "Projecting it would write a second delimiter into every target and "
                "wedge every later run. Remove it from the canonical file.",
            )
            return None
    return "\n" + body.strip("\r\n") + "\n"


def _catalog(root: Path, lanes: _Lanes) -> list[str] | None:
    """The catalogued skill names, sorted, or None when the catalog is refused."""
    text = _read_required(root, CATALOG_FILE, lanes)
    if text is None:
        return None
    try:
        records = json.loads(text)
    except json.JSONDecodeError as exc:
        lanes.finding(CATALOG_FILE, f"not valid JSON ({exc})")
        return None
    if not isinstance(records, list) or not records:
        lanes.finding(CATALOG_FILE, "expected a non-empty list of skill records.")
        return None
    try:
        return sorted(str(record["name"]) for record in records)
    except (TypeError, KeyError) as exc:
        lanes.finding(CATALOG_FILE, f"a record has no `name` key ({exc})")
        return None


def _load_canonical(root: Path) -> str:
    """The canonical body; raises RegenError or EnvironmentLaneError when refused."""
    lanes = _Lanes()
    canonical = _canonical(root, lanes)
    lanes.raise_if_refused()
    assert canonical is not None
    return canonical


def _catalogued_skills(root: Path) -> list[str]:
    """The catalogued names; raises RegenError or EnvironmentLaneError when refused."""
    lanes = _Lanes()
    names = _catalog(root, lanes)
    lanes.raise_if_refused()
    assert names is not None
    return names


def _skill_rel(name: str) -> str:
    return f"{SKILLS_DIR}/{name}/SKILL.md"


def _probe_skill(root: Path, name: str, lanes: _Lanes) -> tuple[str, str | None]:
    """Probe and read one `<name>/SKILL.md`. Returns (state, text).

    state is "absent" (confirmed by an lstat failing with ENOENT or ENOTDIR,
    so a regular file such as `.gitkeep` is no candidate), "refused" (a finding
    or an environment failure was recorded) or "read".
    """
    rel = _skill_rel(name)
    path = root / rel
    try:
        if input_lanes.path_state(path, follow=False) is None:
            return "absent", None
        # It exists, possibly as a symbolic link; ENOENT at this open is the
        # listed-then-absent case, which document_reason names.
        return "read", read_text_verbatim(path)
    except (OSError, UnicodeDecodeError, MemoryError) as exc:
        lanes.read_failure(rel, exc)
        return "refused", None


def _targets(
    root: Path, lanes: _Lanes, catalogued: list[str] | None
) -> tuple[list[str], dict[str, str]]:
    """Derive the targets from the BEGIN marker, then cross-check the catalog.

    Deriving from the marker alone would let a skill that lost its markers drop
    silently out of the projection — the exact failure this gate exists to
    catch. So the marker scan decides the targets, and the catalog decides
    whether that set is COMPLETE. Returns the target paths and each target's
    text; every refusal is recorded on `lanes`.
    """
    skills_root = root / SKILLS_DIR
    states: dict[str, str] = {}
    texts: dict[str, str] = {}
    listed = False
    try:
        if input_lanes.directory_exists(skills_root):
            entries = input_lanes.list_directory(skills_root)
            listed = True
        else:
            lanes.finding(SKILLS_DIR, _ABSENT_DIRECTORY_REASON)
            entries = []
            listed = True  # confirmed absent: every member is confirmed absent too
    except (OSError, MemoryError) as exc:
        # An existing directory that cannot be listed, or whose existence
        # cannot be determined, is never read as empty.
        lanes.failures.append(input_lanes.environment_reason(SKILLS_DIR, exc))
        entries = []

    for name in entries:
        state, text = _probe_skill(root, name, lanes)
        states[name] = state
        if text is not None:
            texts[name] = text
    marked = {name for name, text in texts.items() if has_marker(text)}

    if catalogued is not None:
        stale_exempt = sorted(EXEMPT_SKILLS - set(catalogued))
        if stale_exempt:
            lanes.finding(
                SCRIPT_FILE,
                "EXEMPT_SKILLS entries naming skills the catalog does not carry: "
                f"{', '.join(stale_exempt)}. An exemption outliving its skill is the one "
                "way this list rots undetected — the other two legs only look at skills "
                "that still exist. Delete the entry, or run `validate-catalog.py` if the "
                "skill is present but uncatalogued.",
            )
    if catalogued is not None and listed:
        for name in catalogued:
            if name not in states:
                # Not in the listing: probe the member itself.
                state, text = _probe_skill(root, name, lanes)
                states[name] = state
                if text is not None:
                    texts[name] = text
                    if has_marker(text):
                        marked.add(name)
            state = states[name]
            if state == "absent":
                lanes.finding(_skill_rel(name), input_lanes.absent_reason("member"))
            elif state == "read" and name not in marked and name not in EXEMPT_SKILLS:
                lanes.finding(
                    _skill_rel(name),
                    "carries neither the runtime-compat markers nor an exemption. A "
                    "skill that loses its markers must fail here rather than drop "
                    "silently out of the projection. Restore the markers, or add the "
                    "skill to EXEMPT_SKILLS if it genuinely carries no block.",
                )
        exempt_but_marked = sorted(marked & EXEMPT_SKILLS)
        if exempt_but_marked:
            lanes.finding(
                SCRIPT_FILE,
                "skills listed in EXEMPT_SKILLS that DO carry the runtime-compat markers: "
                f"{', '.join(exempt_but_marked)}. Remove them from EXEMPT_SKILLS so the "
                "projection reaches them.",
            )
        for name in sorted(marked - set(catalogued)):
            lanes.finding(
                _skill_rel(name),
                "is a marked skill absent from the catalog. Run `validate-catalog.py` "
                "first — projecting into a skill the catalog does not know would hide "
                "a catalog fault.",
            )
    targets = sorted(marked)
    return [_skill_rel(n) for n in targets], {_skill_rel(n): texts[n] for n in targets}


def resolve_targets(root: Path) -> list[str]:
    """The target paths; raises RegenError or EnvironmentLaneError when refused."""
    lanes = _Lanes()
    catalogued = _catalog(root, lanes)
    targets, _texts = _targets(root, lanes, catalogued)
    lanes.raise_if_refused()
    return targets


def run(root: Path, dry_run: bool) -> tuple[int, dict]:
    lanes = _Lanes()
    canonical = _canonical(root, lanes)
    catalogued = _catalog(root, lanes)
    targets, texts = _targets(root, lanes, catalogued)

    # Pass 1 — validate EVERY target before mutating ANY of them, so a
    # malformed later target cannot leave earlier ones rewritten. A malformed
    # region is reported whether or not the canonical file was refused; the
    # comparison and the planned write need the canonical body.
    planned: list[tuple[str, Path, str]] = []
    drifted: list[str] = []
    for rel in targets:
        text = texts[rel]
        try:
            region = extract_region(text, PROJECTION_BEGIN, PROJECTION_END, rel)
        except RegenError as exc:
            lanes.findings.extend(exc.errors)
            continue
        if canonical is None or region == canonical:
            continue
        drifted.append(rel)
        planned.append(
            (rel, root / rel, replace_region(text, PROJECTION_BEGIN, PROJECTION_END, canonical, rel))
        )

    lanes.raise_if_refused()

    if dry_run:
        if drifted:
            return 1, {
                "drifted": drifted,
                "canonical": CANONICAL_FILE,
                "targets": len(targets),
                "remediation": "run `python3 crux/scripts/generate-runtime-compat.py`",
            }
        return 0, {"drifted": [], "canonical": CANONICAL_FILE, "targets": len(targets)}

    # Pass 2 — write. Every target already parsed cleanly, so no validation
    # failure can strike mid-write. An I/O error still can: each individual
    # write is atomic, but the set is not, so a failure here can leave earlier
    # targets updated and later ones stale. That state is safe and
    # self-correcting — the drift gate reports it and a re-run converges,
    # because regeneration is idempotent. A write failure is not a refusal; it
    # keeps exit 2 on stderr.
    for _rel, path, text in planned:
        write_text_atomically(path, text)
    return 0, {"written": drifted, "canonical": CANONICAL_FILE, "targets": len(targets)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--dry-run", action="store_true", help="report drift; write nothing")
    ap.add_argument(
        "--repo-root", default=None, help="repo root to inspect (default: the working directory)"
    )
    args = ap.parse_args(argv)

    root = _repo_root(args.repo_root)

    # SURFACE-ABSENT LANE, on the `extract-code-docs` model. Every surface this
    # regenerator reads and every region it projects into lives in the plugin's own
    # source checkout. A consuming project owns none of them, so nothing here can
    # have drifted for that project and nothing can have been verified for it either.
    # Reporting a failure would file an inapplicable check as a defect in the reader's
    # repository; reporting a clean pass would file it as verified. This lane says
    # neither, and `check-drift` renders it N/A with the reason.
    if not _scope.is_authoring_checkout(root, __file__):
        return _scope.print_surface_absent()

    try:
        code, payload = run(root, args.dry_run)
    except input_lanes.EnvironmentLaneError as exc:
        return input_lanes.emit_environment_failure(exc, SCRIPT_NAME, sys.stderr)
    except RegenError as exc:
        print(json.dumps({"validation_errors": exc.errors}, indent=2))
        return 1
    except OSError as exc:
        # A pass-2 write failure: not a refusal, so it keeps exit 2 on stderr.
        # Every read is classified in run(), so none reaches this handler.
        sys.stderr.write(f"{SCRIPT_NAME}: {exc}\n")
        return 2

    print(json.dumps(payload, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
