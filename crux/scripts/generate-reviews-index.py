#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""generate-reviews-index.py — the vendored regenerator for
<docs_dir>/adrs/reviews/index.md.

Per ADR-0101 requirement 5: the reviews index is a *derived* artifact. Each
dated report under `<docs_dir>/adrs/reviews/YYYY-MM-DD.md` is hand-kept; the
index that lists them is not. One row per report, newest first, carrying the
report's date, its finding count, its dismissed count, and a relative link.
Byte-stable — the rendering carries no timestamp — so a stale index is drift
the gate catches rather than a special repair case, exactly as
`generate-adr-index.py` is stable for the same reason.

Counting rules, both read from the report itself:
  findings   the number of UNIQUE `adr-review-<slug>` tokens in the report body
             BELOW the frontmatter, matched as
             `\\badr-review-[a-z0-9]+(?:-[a-z0-9]+)*\\b`. The bare word
             `adr-review` (the frontmatter `type`) cannot match — the pattern
             requires a slug after the second hyphen.
  dismissed  the length of the report frontmatter's `dismissed:` list, read in
             either the flow form (`dismissed: [a, b]`) or the block form
             (`dismissed:` followed by indented `- ` items).

FAIL-CLOSED BEHAVIOUR (the reading of requirement 5 this script implements).
The regenerator refuses to build an index it cannot describe rather than
silently dropping a file it does not understand. Two refusals, both in BOTH
modes — a drift gate that passes on a corpus the writer would refuse is a
false green.

A refusal is a DOCUMENT finding, not an environment problem. Both exit 1 with
a `"validation_errors"` list on stdout, of the `{"file", "error"}` shape
`validate-catalog.py` emits, plus the message on stderr. `check-drift` reads a
non-empty `validation_errors` as BROKEN — the named input must be repaired,
and regenerating cannot fix it — which is the right verdict for a hand-edited
report. Exit 2 stays reserved for a genuine environment failure (an unreadable
file, a bad encoding, a malformed `.bionic.yml`), which `check-drift` reads as
CRASH. The two refusals:

  1. A NAME OUTSIDE THE GRAMMAR. An entry under `<docs_dir>/adrs/reviews/`
     whose name is neither `index.md` nor a valid ISO `YYYY-MM-DD.md` calendar
     date. `2026-02-30.md` is parseable as digits and is still refused: the
     date must exist. A subdirectory is refused for the same reason — the
     grammar admits no nesting. Dotfiles are the one carve-out: a name
     beginning with `.` is editor or filesystem debris (`.DS_Store` occurs in
     this very tree), never a review report, and is skipped without comment.
  2. A REPORT THAT DOES NOT DECLARE ITSELF. Frontmatter missing, `type` not
     `adr-review`, or `date` disagreeing with the filename.
AN ABSENT REVIEWS DIRECTORY IS NOT A REFUSAL. A tree that has never run a
review carries no `<docs_dir>/adrs/reviews/` at all, and that is the state of
every target repo on the day it installs the plugin. There is no derived
artifact, so there is nothing that can have drifted. Both modes exit 0 and set
`"surface_absent": true` on the JSON. That key is a POSITIVE DISCRIMINATOR, not
a silent pass: `check-drift` reads it as verdict N/A and never as a clean gate,
so an absent surface cannot be mistaken for a measured one. This is the one
place the script distinguishes "no reviews yet" — an empty directory, which
renders `Reports: 0` and is a real measured pass — from "no reviews surface".

ORPHAN ROWS are drift, not a refusal. An on-disk `index.md` row naming a report
file that does not exist is a row the reports cannot justify. In `--dry-run`
that is exit 1 with `"drift": true` and an `"orphan_rows"` list in the JSON; in
write mode the index is rebuilt from the reports on disk, which removes it.
The distinction is deliberate — an orphan row is a stale *output*, which
regeneration fixes, while a malformed *input* is a fact about the corpus that
only a human can resolve.

CONTAINMENT AND REDACTION. Two guards, because this regenerator reads a
directory whose contents a pull request can add to and writes a file whose
path is derived from `.bionic.yml`.

  * [SECURITY:S5] Every resolved path is containment-checked before it is read
    or written. The tree dir must resolve under the repo root, the reviews dir
    under the tree dir, and — through this file's own copy of
    `_atomic_write_text`, which each script carries rather than shares — the
    index's parent under the tree dir, which is ADR-0101 requirement 5's "the
    resolved write path is containment-checked under the resolved
    `<docs_dir>`". An entry under the reviews directory that is a symlink is
    refused rather than followed, so no read leaves the tree either.
  * [SECURITY:S1] Every value this script quotes back — a filename, a
    frontmatter scalar, an orphan row's link text — is a value the report's
    author chose, and all three reach `validation_errors` on stdout AND the
    message on stderr. Each is routed through `untrusted.redact`, which bounds
    the rendered length and replaces every unprintable character, so a 40 KB
    `type:` cannot inflate the envelope and a newline in a filename cannot
    forge a second stderr line. `redact` does no channel escaping and is not a
    substitute for it; nothing here renders into Markdown.

Usage:
  generate-reviews-index.py [--repo-root DIR]     rewrite adrs/reviews/index.md
  generate-reviews-index.py --dry-run [...]       exit 1 + JSON if drift

Exit: 0 clean/written · 1 drift or a report validation error (JSON on
stdout) · 2 env error (stderr).
"""

from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from untrusted import MESSAGE_LIMIT, redact  # noqa: E402

DATE_NAME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
FINDING_TOKEN = re.compile(r"\badr-review-[a-z0-9]+(?:-[a-z0-9]+)*\b")
INDEX_ROW_REPORT = re.compile(r"^\|[^|]*\|[^|]*\|[^|]*\|\s*\[([^\]]+)\]\([^)]*\)\s*\|\s*$")

HEADER = [
    "# Decision reviews",
    "",
    "<!-- Generated by crux/scripts/generate-reviews-index.py — do not hand-edit. -->",
    "",
    "One row per `review-decisions` pass, newest first. Each dated report is "
    "hand-kept; this index is derived from the reports in this directory.",
    "",
    "| date | findings | dismissed | report |",
    "|------|----------|-----------|--------|",
]


class ReviewsError(Exception):
    """A report this regenerator refuses to describe — a validation error.

    Carries the offending path and the problem separately so `main` can emit a
    `validation_errors` entry of the same `{"file", "error"}` shape
    `validate-catalog.py` uses, rather than reparsing the message string.

    [SECURITY:S1] `file` is bound-and-redacted HERE rather than at each raise
    site, because it reaches two channels — the `validation_errors[]["file"]`
    key on stdout and the composed message on stderr — and a filename is a
    value the report's author chose. A newline is legal in a POSIX filename
    and forged a second stderr line where the contract is one; every
    unprintable character is now replaced. A short printable path round-trips
    to exactly itself, so no existing assertion moves. Callers redact the
    untrusted parts of `problem` at their own sites, where the surrounding
    prose tells them which value is theirs.
    """

    def __init__(self, file: str, problem: str) -> None:
        safe = redact(file, quoted=False)
        super().__init__(f"{safe}: {problem}")
        self.file = safe
        self.problem = problem


def _atomic_write_text(path: Path, body: str, *, contained_under: Path) -> None:
    """Atomic UTF-8 text write with no platform newline translation.

    Writes to <path>.tmp then os.replace()s into place. Bytes are written
    directly so Python does NOT translate '\\n' -> '\\r\\n' on Windows; that
    translation would shift the file's sha256 across platforms and break the
    byte-stable regenerative output contract.

    [SECURITY:S5] Every write target's RESOLVED parent directory must sit under
    `contained_under` — the validated tree dir. This guard covers the
    INTERMEDIATE directories (a symlink at <tree>/adrs or <tree>/adrs/reviews
    leaves every entry under it a real file while steering the write outside the
    repo root); the leaf checks below guard the target and its tmp file. Shared
    posture with compile-doctrine.py / summarize-adrs.py / signoff-backfill.py —
    same guards, same order, same exception type (OSError); each names its own
    subject in its messages ("reviews index content" here). Change one, change
    all.
    """
    root_resolved = Path(contained_under).resolve()
    parent_resolved = path.parent.resolve()
    if parent_resolved != root_resolved \
            and root_resolved not in parent_resolved.parents:
        raise OSError(
            f"refusing to write {path}: the parent directory resolves to "
            f"{parent_resolved}, which is not contained under the validated "
            f"tree dir {root_resolved} — a symlinked intermediate directory "
            "would put reviews index content outside the tree"
        )
    tmp = path.with_suffix(path.suffix + ".tmp")
    for label, candidate in (("target", path), ("temporary file", tmp)):
        if candidate.is_symlink():
            raise OSError(
                f"refusing to write {path}: the {label} {candidate} is a symlink — "
                "writing through it would put reviews index content in the "
                "link's target"
            )
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except FileExistsError as exc:
        raise OSError(
            f"refusing to write {path}: the temporary file {tmp} already exists; "
            "remove it after checking what created it"
        ) from exc
    except OSError as exc:  # ELOOP from O_NOFOLLOW, or an unwritable directory
        raise OSError(f"refusing to write {path}: cannot create {tmp} ({exc})") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body.encode("utf-8"))
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


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


def _contained(child: Path, parent: Path, subject: str) -> Path:
    """`child`, refused when it resolves outside `parent`.

    [SECURITY:S5] The READ-side twin of `_atomic_write_text`'s write-side
    guard, applied to the reviews directory. A checkout supplies the
    directories under the tree, so `<tree>/adrs` or `<tree>/adrs/reviews` can
    be a symlink pointing anywhere on the filesystem; without this,
    `iterdir()` would enumerate — and `_read_report` would read — a directory
    outside the repository, and its first line would be quoted back into
    `validation_errors`. Raised as OSError so it lands in `main`'s environment
    lane (exit 2, CRASH to `check-drift`): a symlinked directory is a fact
    about the checkout, not a hand-edited document a human repairs by fixing a
    report.
    """
    resolved = child.resolve()
    parent_resolved = parent.resolve()
    if resolved != parent_resolved and parent_resolved not in resolved.parents:
        raise OSError(
            f"refusing to read {child}: the {subject} resolves to {resolved}, "
            f"which is not contained under {parent_resolved}")
    return child


def _scalar(raw: str) -> str:
    return raw.strip().strip("\"'").strip()


def _field(fm: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}[ \t]*:[ \t]*(.*)$", fm, re.MULTILINE)
    return _scalar(m.group(1)) if m else None


def _dismissed_count(fm: str, rel: str) -> int:
    """Length of the frontmatter `dismissed:` list, flow or block form."""
    m = re.search(r"^dismissed[ \t]*:[ \t]*(.*)$", fm, re.MULTILINE)
    if not m:
        raise ReviewsError(rel, "frontmatter carries no `dismissed:` list")
    inline = m.group(1).strip()
    if inline.startswith("["):
        body = inline[1:inline.rindex("]")] if "]" in inline else inline[1:]
        return len([item for item in body.split(",") if item.strip()])
    if inline:
        raise ReviewsError(
            rel, f"`dismissed:` must be a list, found the scalar "
                 f"{redact(inline)}")
    count = 0
    for line in fm[m.end():].splitlines():
        if not line.strip():
            continue
        if re.match(r"^[ \t]*-[ \t]", line):
            count += 1
            continue
        break  # the next key at any indent ends the block list
    return count


def _read_report(path: Path, rel: str) -> dict:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    if not m:
        raise ReviewsError(rel, "no frontmatter block — a review report must open with ---")
    fm, body = m.group(1), text[m.end():]
    kind = _field(fm, "type")
    if kind != "adr-review":
        raise ReviewsError(
            rel, f"frontmatter `type` is {redact(kind)}, expected 'adr-review'")
    stem = path.name[: -len(".md")]
    declared = _field(fm, "date")
    if declared != stem:
        raise ReviewsError(
            rel, f"frontmatter `date` is {redact(declared)} but the filename "
                 f"says {redact(stem)}")
    return {
        "date": stem,
        "name": path.name,
        "findings": len(set(FINDING_TOKEN.findall(body))),
        "dismissed": _dismissed_count(fm, rel),
    }


def collect(reviews: Path, tree_rel: Path, today: datetime.date | None = None) -> list[dict]:
    """Every report under `reviews`, newest first. Raises on a refusal.

    `today` is the clock the future-date refusal reads; `None` means the
    system date. A future-dated report would anchor every cadence check
    (`cleanup-campsite` CLN-ADR-5, the gardener's review-age step) on a date
    that never arrives and suppress the nudge for as long as it sits there.
    """
    today = datetime.date.today() if today is None else today
    reports: list[dict] = []
    for entry in sorted(reviews.iterdir()):
        if entry.name.startswith("."):
            continue
        rel = str(tree_rel / entry.name)
        # [SECURITY:S5] Checked BEFORE the `index.md` skip, so the derived
        # index cannot be a symlink either: `build` reads it back for the
        # orphan-row scan, and that content reaches the JSON envelope.
        # `is_file()` follows the link, so a `2026-01-01.md -> /etc/passwd`
        # entry would otherwise be read as a report and its first line quoted
        # into `validation_errors`.
        if entry.is_symlink():
            raise ReviewsError(
                rel, "is a symlink — the reviews grammar admits only regular "
                     "files, and following one would read outside the tree")
        if entry.name == "index.md" and entry.is_file():
            continue
        m = DATE_NAME.match(entry.name) if entry.is_file() else None
        if not m:
            raise ReviewsError(
                rel, "name is outside the reviews grammar — expected "
                     "index.md or a YYYY-MM-DD.md report file")
        try:
            report_date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError as exc:
            raise ReviewsError(
                rel, f"{redact(m.group(0)[:-3], quoted=False)} is not a "
                     f"calendar date ({redact(exc, quoted=False)})") from exc
        if report_date > today:
            raise ReviewsError(
                rel, f"{redact(m.group(0)[:-3], quoted=False)} is in the future "
                     f"(today is {today.isoformat()}) — a future-dated report would "
                     f"suppress the decision-review cadence nudge")
        reports.append(_read_report(entry, rel))
    reports.sort(key=lambda r: r["date"], reverse=True)
    return reports


def render(reports: list[dict]) -> str:
    out = list(HEADER)
    for r in reports:
        out.append(f"| {r['date']} | {r['findings']} | {r['dismissed']} | "
                   f"[{r['name']}](./{r['name']}) |")
    out += ["", f"Reports: {len(reports)}"]
    return "\n".join(out) + "\n"


def orphan_rows(index_text: str, known: set[str]) -> list[str]:
    """Report filenames an existing index links to that are not on disk.

    [SECURITY:S1] The link text is hand-editable content that reaches the
    `orphan_rows` array on stdout, so it is bound-and-redacted on the way out.
    The membership test runs on the RAW text and the redaction applies only to
    what is emitted, so redaction can neither create nor mask an orphan. A
    legitimate `YYYY-MM-DD.md` name round-trips to exactly itself.
    """
    out: list[str] = []
    seen: set[str] = set()
    for line in index_text.splitlines():
        m = INDEX_ROW_REPORT.match(line)
        if m and m.group(1) not in known and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(redact(m.group(1), quoted=False))
    return out


def build(root: Path, today: datetime.date | None = None) -> tuple[Path | None, str, list[str], Path]:
    """The index path, its wanted body, any orphan rows, and the tree dir.

    A `None` path means the reviews surface is absent — not an error, and not
    a clean gate either. `main` turns it into the `surface_absent` discriminator.
    The tree dir comes back so `main` passes the SAME validated directory to
    `_atomic_write_text` that the reads were checked against, rather than
    recomputing it and risking the two disagreeing.
    """
    # The TREE dir's own containment is `bionic_config.load_config`'s job and
    # is not repeated here: it refuses a `docs_dir` resolving outside the repo
    # root on BOTH resolution paths (`.bionic.yml` and bare-directory
    # discovery), and `_tree_name` above raises before this line is reached.
    # What is left to this file is everything UNDER the tree dir, which
    # nothing else checks.
    tree = root / _tree_name(root)
    tree_rel = Path(_tree_name(root)) / "adrs" / "reviews"
    reviews = root / tree_rel
    if not reviews.is_dir():
        return None, "", [], tree
    _contained(reviews, tree, "reviews directory")
    reports = collect(reviews, tree_rel, today)
    index = reviews / "index.md"
    have = index.read_text(encoding="utf-8") if index.is_file() else ""
    orphans = orphan_rows(have, {r["name"] for r in reports})
    return index, render(reports), orphans, tree


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Regenerate adrs/reviews/index.md from the dated review reports.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--today", default=None,
                    help="ISO date the future-date check reads; default: the system date")
    args = ap.parse_args(argv)
    root = Path(args.repo_root).resolve()
    today: datetime.date | None = None
    if args.today is not None:
        try:
            today = datetime.date.fromisoformat(args.today)
        except ValueError:
            sys.stderr.write("generate-reviews-index: --today must be an ISO calendar date "
                             "(YYYY-MM-DD)\n")
            return 2
    try:
        # INSIDE the try. `_tree_name` reads `.bionic.yml` and raises
        # `BionicConfigError` on a malformed one or on a `docs_dir` that
        # resolves outside the repo root. Outside the try it escaped as an
        # uncaught traceback — exit 1 with EMPTY stdout, which reads to
        # `check-drift` as neither the documented drift lane (exit 1 with JSON)
        # nor the documented crash lane (exit 2). Both belong in the
        # environment lane below.
        rel_index = str(Path(_tree_name(root)) / "adrs" / "reviews" / "index.md")
        path, want, orphans, tree_dir = build(root, today)
    except ReviewsError as exc:
        # A hand-edited report is a DOCUMENT finding, not an environment
        # problem: exit 1 with `validation_errors` on stdout, which
        # `check-drift` classifies BROKEN. Exit 2 stays reserved for a
        # genuine environment failure, which it reads as CRASH.
        payload = {"path": rel_index,
                   "validation_errors": [{"file": exc.file, "error": exc.problem}]}
        if args.dry_run:
            payload |= {"drift": False, "orphan_rows": []}
        else:
            payload |= {"written": None}
        print(json.dumps(payload, sort_keys=True))
        sys.stderr.write(f"generate-reviews-index: {exc}\n")
        return 1
    except Exception as exc:  # unreadable file, bad encoding — still an env error
        # [SECURITY:S1] The composed message is redacted at MESSAGE_LIMIT
        # rather than LIMIT: its untrusted parts were already bounded where
        # they were interpolated, and the value bound would cut a real
        # two-sentence containment refusal in half. What is still wanted here
        # is the control-character replacement, so an unrouted path cannot
        # forge a line on stderr.
        sys.stderr.write(
            f"generate-reviews-index: {type(exc).__name__}: "
            f"{redact(exc, quoted=False, limit=MESSAGE_LIMIT)}\n")
        return 2
    if path is None:
        rel = str(Path(_tree_name(root)) / "adrs" / "reviews" / "index.md")
        payload = {"path": rel, "surface_absent": True}
        if args.dry_run:
            payload |= {"drift": False, "orphan_rows": []}
        else:
            payload |= {"written": None}
        print(json.dumps(payload, sort_keys=True))
        return 0
    rel = str(path.relative_to(root))
    have = path.read_text(encoding="utf-8") if path.exists() else ""
    if args.dry_run:
        drift = have != want or bool(orphans)
        print(json.dumps({"drift": drift, "path": rel, "orphan_rows": orphans},
                         sort_keys=True))
        return 1 if drift else 0
    try:
        _atomic_write_text(path, want, contained_under=tree_dir)
    except OSError as exc:
        sys.stderr.write(
            f"generate-reviews-index: {redact(exc, quoted=False, limit=MESSAGE_LIMIT)}\n")
        return 2
    print(json.dumps({"written": rel}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
