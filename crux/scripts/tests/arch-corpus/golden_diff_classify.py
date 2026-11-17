#!/usr/bin/env python3
"""Classify a corpus golden diff, and refuse an unnamed extraction-content change.

ADR-0096 clause 12 makes byte-identity the split's gate: every corpus golden is
unchanged across it. After the split, three units deliberately move goldens, and
each is supposed to move a DIFFERENT and bounded thing:

  * retiring the confidence layer (clause 10) removes three `coverage.json` keys
    and touches no extracted content at all;
  * the honest stub line (clauses 3/4) rewrites stub sentences and coverage
    vocabulary and touches no route, table or edge;
  * detection (clause 6) changes extraction content, in two named repositories
    and nowhere else.

The risk this script exists to close is that a re-bless is a `--bless` flag and a
human eye. Nothing mechanical distinguishes "the three coverage keys came out"
from "a route table silently lost nine rows in the same commit". ADR-0096's own
Consequences say it plainly: an expectation edited to match a regression passes
the gate exactly as a careless re-bless does. This script narrows that to one
question a human must answer explicitly — *which repositories may change
extracted content in this unit* — and refuses everything else.

Four classes, assigned per changed line:

  `coverage-vocabulary`  a change confined to `_meta/coverage.json` that ADDS
                         or REMOVES a key in the set this script names. A key
                         appearing on both sides of one file's diff is a VALUE
                         change, not a vocabulary change, and is classed as
                         extraction content however the key is named. Changing
                         `inputs_found` is never vocabulary, because that is
                         what the extractor actually read.
  `stub-line`            a change to a stub sentence in a spine file — the line
                         a concern renders to name a non-`populated` verdict. A
                         stub line cannot carry a table row, a route or a graph
                         edge, so it cannot hide extraction movement. Matched
                         against the renderer's own grammar (`STUB_LINE_RE`),
                         NOT against "is a blockquote": every spine file also
                         renders blockquote-italic prose, and that prose is
                         extraction content.
  `omission`             ADR-0181's three admitted moves: a line of a spine
                         file's `## Omissions` section in its closed grammar; a
                         REMOVED whole-input residual line whose every
                         backticked path that file's new Omissions section
                         names; and a `coverage.json` line that, on its own
                         side of the diff, assigns the `omissions` key or lies
                         inside that key's value at any depth, whether the key
                         is one-sided or both-sided. A line whose enclosing
                         key is not visible within its hunk keeps the class
                         the other rules give it.
  `extraction-content`   everything else. This is the class that means the
                         derived facts moved.

Exit 0 when no `extraction-content` hunk survives the allow-list; exit 1 when one
does, naming the repository and the line. Exit 2 for an environment problem —
not a git work tree, no diff obtainable — never a verdict.

Usage:
    uv run python3 crux/scripts/tests/arch-corpus/golden_diff_classify.py
    uv run python3 .../golden_diff_classify.py --allow-content djangoproject-com \\
                                               --allow-content sequelize-express-example

`--allow-content` names a repository whose extracted content this unit is
expected to move. It is per-repository and never global: there is deliberately
no `--allow-all`, because the whole value here is that the eight repositories
nobody claimed would move are still proven not to have moved.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "golden"
OVERLAY = HERE / "golden-by-python"
REPO_ROOT = HERE.parents[3]

# The `coverage.json` keys whose APPEARANCE OR DISAPPEARANCE is vocabulary
# rather than extraction. `inputs_found` is deliberately ABSENT: it lists the
# files the extractor actually read, so a change there is a change in what was
# extracted, and calling it vocabulary would let a real regression through the
# one gate meant to catch it.
#
# **Membership here is necessary and not sufficient**, and that is the whole
# repair. The earlier form bucketed by key NAME alone, so these three lines all
# classified as vocabulary:
#
#     "verdict": "stubbed",
#     "n_entities": 0,
#     "stub_reason": "no_entities",
#
# A `populated` concern regressing to `no_entities` moves exactly those lines in
# `coverage.json`, and in the spine file `_apply_stub_line` INSERTS the stub line
# rather than replacing content — the table rows stay, so the only `.md` change
# is one `stub-line`. The gate saw zero `extraction-content` and exited 0 over a
# repository that had just lost its extraction, which is the one thing it exists
# to refuse.
#
# `_side_keys` supplies the missing half: a key is vocabulary only when the diff
# for that file assigns it on ONE SIDE. A key on both sides is a value change,
# which is extraction content however it is named. That distinction is what the
# docstring always claimed ("adding or removing a coverage KEY is vocabulary")
# and what the code did not do.
COVERAGE_VOCABULARY_KEYS = frozenset({
    "confidence",
    "confidence_reason",
    "escalation_offered",
    "reason",
    "status",
    "inputs_missing",
    "verdict",
    "stub_reason",
    "expected",
    "found",
    "n_sources",
    "n_entities",
    "_note",
})

# A changed markdown line is a stub line when it MATCHES THE STUB-LINE GRAMMAR
# the renderer emits — not merely when it is a blockquote.
#
# The earlier form of this check was a prefix pair, `("> _no extractor for this
# stack", "> _")`, and the second entry subsumed the first: every
# blockquote-italic line classified as `stub-line`. Every spine renderer emits
# blockquote-italic PROSE too (`> _Derived from db/schema.rb._`), so that prefix
# could not tell a moved stub line from a moved prose cell — in the one unit
# where all 23 stub lines move and no extraction content may, which is exactly
# where the distinction has to hold.
#
# Two spellings are stub lines, and nothing else is:
#
#   legacy   `> _no extractor for this stack — empty-but-valid spine file._`
#   clause 4 `> _stub: <reason> — expected <expected>, found <found>._`
#
# `<reason>` is one of `core.StubReason`'s six members. That enum is the source
# of truth; this list is a deliberate copy, because this script is stdlib-only
# and standalone by design (importing `crux.arch` pulls the package's eager
# httpx chain). `test_golden_diff_classify.py` asserts the two agree, so the
# copy cannot drift silently.
STUB_REASONS = (
    "precondition_missing",
    "unsupported_stack",
    "ambiguous_stack",
    "ambiguous_package",
    "parse_failed",
    "no_entities",
)

STUB_LINE_RE = re.compile(
    r"^> _(?:"
    r"no extractor for this stack\b"
    r"|stub: (?:" + "|".join(STUB_REASONS) + r")\b"
    r")"
)

# The omission class (ADR-0181). A descriptive spine file names the inputs it
# does not describe in an `## Omissions` section, and `coverage.json` carries
# each concern's `omissions` list. A golden may move by exactly three things
# under that decision, and these are the only things the `omission` class admits:
#
#   * a line of an Omissions section: its heading, its fixed intro sentence, or
#     an omission line in the one closed template `core.omission_line` renders;
#   * a REMOVED whole-input residual line whose every backticked path is named
#     by an omission line on the new side of the same file's diff;
#   * a `coverage.json` line the `omissions` key encloses on the line's own side
#     of the diff: the key line itself and every line of its value at any depth,
#     whether the key appears on one side or on both. The old side reads context
#     and removed lines, the new side context and added lines. A line whose
#     enclosing key lies outside its hunk keeps the class the other rules give
#     it; `main()` asks git for whole-file context, so the key is visible.
#
# `OMISSION_REASONS` copies `core.OMISSION_REASONS` for the same reason
# `STUB_REASONS` copies the stub enum; `test_golden_diff_classify.py` asserts
# the two agree.
OMISSION_REASONS = ("undecodable", "unparseable", "over-cap", "absent", "not-a-file")

OMISSIONS_HEADING = "## Omissions"
OMISSIONS_INTRO = "_Recognizable inputs this map does not describe:_"

OMISSION_LINE_RE = re.compile(
    r"^- (?:`(?P<path>[^`]+)`"
    r"|scan cap `[^`]+` under `(?P<dir>[^`]+)` skipped \d+ input\(s\))"
    r" — (?:" + "|".join(re.escape(r) for r in OMISSION_REASONS) + r")"
    r" \([^()]+\)$"
)

_BACKTICKED = re.compile(r"`([^`]+)`")

# The context `main()` asks git for: every line of a changed file, so each
# changed `coverage.json` line shows the key that encloses it and each spine
# file shows its whole Omissions section. git takes the largest signed 32-bit
# count; no golden comes near it.
WHOLE_FILE_CONTEXT = f"--unified={2**31 - 1}"


def _run(args: list[str]) -> str:
    try:
        proc = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True)
    except OSError as exc:                       # git missing entirely
        print(f"golden_diff_classify: cannot run git: {exc}", file=sys.stderr)
        raise SystemExit(2)
    if proc.returncode not in (0, 1):
        print(f"golden_diff_classify: git failed: {proc.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return proc.stdout


def _repo_of(path: str) -> str:
    """The corpus repository a golden path belongs to, or '' when it is not
    under `golden/`."""
    marker = "arch-corpus/golden/"
    if marker in path:
        return path.split(marker, 1)[1].split("/", 1)[0]
    # A per-minor overlay file: `golden-by-python/<major>.<minor>/<name>/<rel>`.
    overlay = "arch-corpus/golden-by-python/"
    if overlay in path:
        parts = path.split(overlay, 1)[1].split("/")
        return parts[1] if len(parts) > 2 else ""
    return ""


def _coverage_key(line: str) -> str | None:
    """The JSON key a changed `coverage.json` line assigns, if it assigns one.

    `coverage.json` is emitted with `indent=2, sort_keys=True`, so an assignment
    line is always `"key": value`. A line that is only structural — a brace, a
    bracket, an array element — has no key and is not vocabulary.
    """
    stripped = line.strip().rstrip(",")
    if not stripped.startswith('"'):
        return None
    head, sep, _ = stripped.partition(":")
    if not sep:
        return None
    try:
        return json.loads(head)
    except ValueError:
        return None


def classify_line(path: str, line: str, both_sided_keys: frozenset[str] = frozenset()) -> str:
    """Classify one changed line (without its leading +/-).

    `both_sided_keys` names the `coverage.json` keys this file's diff assigns on
    BOTH sides — the keys whose value changed rather than appeared or vanished.
    A key in that set is never vocabulary, whatever `COVERAGE_VOCABULARY_KEYS`
    says. Defaulting it empty keeps single-line classification callable on its
    own, and `classify_diff` always supplies the real set.
    """
    if path.endswith("_meta/coverage.json"):
        key = _coverage_key(line)
        if key is not None:
            if key in COVERAGE_VOCABULARY_KEYS and key not in both_sided_keys:
                return "coverage-vocabulary"
            return "extraction-content"
        if not line.strip().startswith('"'):
            # A brace or bracket that moved because a key above it did.
            return "coverage-vocabulary"
        return "extraction-content"
    if path.endswith(".md"):
        if STUB_LINE_RE.match(line):
            return "stub-line"
        if is_omissions_section_line(line):
            return "omission"
        return "extraction-content"
    return "extraction-content"


def is_omissions_section_line(line: str) -> bool:
    """True for a line an Omissions section renders: the heading, the intro
    sentence, or an omission line in the closed template."""
    text = line.rstrip()
    return (text in (OMISSIONS_HEADING, OMISSIONS_INTRO)
            or OMISSION_LINE_RE.match(text) is not None)


def _omitted_path(line: str) -> str | None:
    """The path or directory an omission line names, or None."""
    m = OMISSION_LINE_RE.match(line.rstrip())
    if m is None:
        return None
    return m.group("path") or m.group("dir")


def _changed_lines(diff: str, *, context: bool = False) -> list[tuple[str, str, str]]:
    """`(path, sign, line)` for every changed line in a unified diff.

    With `context=True` the hunk's unchanged lines are returned too, with the
    sign `" "`; the omission class reads them to learn what the new side of a
    file's Omissions section names."""
    return [(path, sign, line) for path, sign, line, _hunk in _hunk_lines(diff)
            if context or sign != " "]


def _hunk_lines(diff: str) -> list[tuple[str, str, str, int]]:
    """`(path, sign, line, hunk)` for every changed and context line in a
    unified diff, where `hunk` numbers the hunks of the whole diff from 1.

    Two properties this walk has and the previous one did not.

    **A deleted file is attributed to ITS OWN path.** `git diff` writes
    `+++ /dev/null` for a deletion, which matches no `+++ b/` prefix, so the
    previous walk left `path` pointing at whatever file came before — every
    removed row of repository B landed under repository A, and an
    `--allow-content A` licensed a deletion in B. The `--- a/` side is tracked
    too, and the current path is the `b` side when there is one and the `a` side
    otherwise. `+++ /dev/null` also stopped being counted as a changed line,
    which it was.

    **Header lines are recognized by POSITION, not by prefix.** `---` and `+++`
    are file headers only before the first `@@` of a file. Inside a hunk they are
    content: a removed line reading `-- x` is written `--- x`, and reading that
    as a header would silently retarget every line after it.
    """
    out: list[tuple[str, str, str, int]] = []
    a_path = b_path = ""
    in_hunk = False
    hunk = 0
    for raw in diff.splitlines():
        if raw.startswith("diff --git"):
            a_path = b_path = ""
            in_hunk = False
            continue
        if raw.startswith("@@"):
            in_hunk = True
            hunk += 1
            continue
        if not in_hunk:
            if raw.startswith("--- "):
                rest = raw[4:]
                a_path = "" if rest == "/dev/null" else rest[2:] if rest.startswith("a/") else rest
                continue
            if raw.startswith("+++ "):
                rest = raw[4:]
                b_path = "" if rest == "/dev/null" else rest[2:] if rest.startswith("b/") else rest
                continue
            continue                      # index / mode / similarity headers
        if not raw or raw[0] not in "+- ":
            continue
        line = raw[1:]
        if not line.strip():
            continue
        path = b_path or a_path
        if path:
            out.append((path, raw[0], line, hunk))
    return out


def _side_keys(changed: list[tuple[str, str, str]]) -> dict[str, frozenset[str]]:
    """Per `coverage.json` path, the keys assigned on BOTH sides of its diff.

    Scoped to one file rather than the whole diff, because `coverage.json` holds
    one record per concern: a key added for one concern and changed for another
    within the same file is the conservative case, and it falls to extraction
    content, which is the safe direction for a gate.
    """
    sides: dict[str, dict[str, set[str]]] = {}
    for path, sign, line in changed:
        if not path.endswith("_meta/coverage.json"):
            continue
        key = _coverage_key(line)
        if key is None:
            continue
        sides.setdefault(path, {"+": set(), "-": set()})[sign].add(key)
    return {path: frozenset(s["+"] & s["-"]) for path, s in sides.items()}


def _new_side_omissions(diff: str) -> dict[str, frozenset[str]]:
    """Per spine file, the paths its Omissions section names on the NEW side of
    the diff: added omission lines and unchanged ones alike."""
    named: dict[str, set[str]] = {}
    for path, sign, line in _changed_lines(diff, context=True):
        if sign == "-" or not path.endswith(".md"):
            continue
        omitted = _omitted_path(line)
        if omitted is not None:
            named.setdefault(path, set()).add(omitted)
    return {path: frozenset(s) for path, s in named.items()}


def _is_named_residual(sign: str, line: str, omitted: frozenset[str]) -> bool:
    """A REMOVED whole-input residual line whose every backticked path the same
    file's new Omissions section names. A table row is never one, and a line
    naming a path the section does not name stays extraction content."""
    if sign != "-" or not omitted:
        return False
    text = line.strip()
    if not text.startswith("- ") or "|" in text or is_omissions_section_line(text):
        return False
    paths = _BACKTICKED.findall(text)
    return bool(paths) and all(p in omitted for p in paths)


_JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def _omission_enclosed(walked: list[tuple[str, str, str, int]]) -> set[int]:
    """Indexes into `walked` of every changed `coverage.json` line that the
    `omissions` key encloses on the line's own side of the diff.

    Each hunk keeps two container stacks. The OLD side reads context and removed
    lines; the NEW side reads context and added lines. A line that opens a
    container pushes a frame, marked when the line assigns the `omissions` key.
    A changed line is enclosed when it assigns that key itself, or when a marked
    frame is open on its side as the line is read. The key may appear on one side
    or on both.

    Both stacks start empty at every hunk. A line inside an array whose key line
    lies before the hunk is therefore not enclosed, and keeps the classification
    `classify_line` gives it: the conservative direction. `main()` asks git for
    whole-file context, so in practice the key is always visible.
    """
    out: set[int] = set()
    stacks: dict[str, list[bool]] = {"-": [], "+": []}
    current: tuple[str, int] | None = None
    for index, (path, sign, line, hunk) in enumerate(walked):
        if not path.endswith("_meta/coverage.json"):
            continue
        if (path, hunk) != current:
            current = (path, hunk)
            stacks = {"-": [], "+": []}
        is_key = _coverage_key(line) == "omissions"
        if sign != " " and (is_key or any(stacks[sign])):
            out.add(index)
        bare = _JSON_STRING.sub('""', line)
        for side in (("-", "+") if sign == " " else (sign,)):
            stack = stacks[side]
            opened = False
            for char in bare:
                if char in "[{":
                    stack.append(is_key and not opened)
                    opened = True
                elif char in "]}" and stack:
                    stack.pop()
    return out


def classify_diff(diff: str) -> dict[str, dict[str, list[str]]]:
    """Walk a unified diff and bucket every changed line by repository and class."""
    walked = _hunk_lines(diff)
    enclosed = _omission_enclosed(walked)
    indexed = [(i, (p, s, l)) for i, (p, s, l, _h) in enumerate(walked) if s != " "]
    changed = [entry for _i, entry in indexed]
    both_sided = _side_keys(changed)
    omitted = _new_side_omissions(diff)
    findings: dict[str, dict[str, list[str]]] = {}
    for index, (path, sign, line) in indexed:
        repo = _repo_of(path)
        if not repo:
            continue
        if index in enclosed or _is_named_residual(sign, line, omitted.get(path, frozenset())):
            cls = "omission"
        else:
            cls = classify_line(path, line, both_sided.get(path, frozenset()))
        findings.setdefault(repo, {}).setdefault(cls, []).append(f"{path}: {sign}{line.strip()}")
    return findings


def classify_files(diff: str) -> dict[str, dict[str, int]]:
    """Per changed golden file, the number of changed lines in each class."""
    out: dict[str, dict[str, int]] = {}
    for classes in classify_diff(diff).values():
        for cls, lines in classes.items():
            for entry in lines:
                path = entry.split(": ", 1)[0]
                out.setdefault(path, {}).setdefault(cls, 0)
                out[path][cls] += 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--allow-content", action="append", default=[], metavar="REPO",
                    help="a corpus repository whose extracted content this unit "
                         "is expected to move (repeatable; never global)")
    ap.add_argument("--json", action="store_true", help="emit the classification as JSON")
    args = ap.parse_args(argv)

    if not GOLDEN.is_dir():
        print(f"golden_diff_classify: no golden tree at {GOLDEN}", file=sys.stderr)
        return 2

    trees = [str(GOLDEN)] + ([str(OVERLAY)] if OVERLAY.is_dir() else [])
    diff = _run(["git", "diff", "--no-renames", WHOLE_FILE_CONTEXT, "--", *trees])
    diff += _run(["git", "diff", "--no-renames", WHOLE_FILE_CONTEXT, "--cached", "--", *trees])
    findings = classify_diff(diff)

    allowed = set(args.allow_content)
    unknown = allowed - {p.name for p in GOLDEN.iterdir() if p.is_dir()}
    if unknown:
        print("golden_diff_classify: --allow-content names a repository that is "
              f"not in the corpus: {sorted(unknown)}", file=sys.stderr)
        return 2

    offenders = {
        repo: lines["extraction-content"]
        for repo, lines in findings.items()
        if "extraction-content" in lines and repo not in allowed
    }

    if args.json:
        print(json.dumps({
            "moved": sorted(findings),
            "allowed_content": sorted(allowed),
            "classes": {r: {c: len(v) for c, v in d.items()} for r, d in findings.items()},
            "files": classify_files(diff),
            "unnamed_extraction_content": {r: v for r, v in offenders.items()},
        }, indent=2, sort_keys=True))
    else:
        if not findings:
            print("golden_diff_classify: no golden moved.")
        for repo in sorted(findings):
            classes = findings[repo]
            summary = ", ".join(f"{c}={len(classes[c])}" for c in sorted(classes))
            flag = "  [content allowed]" if repo in allowed else ""
            print(f"{repo}: {summary}{flag}")
        for repo in sorted(offenders):
            print(f"\nREFUSED — {repo} moved extraction content and was not named "
                  f"by --allow-content:", file=sys.stderr)
            for line in offenders[repo][:20]:
                print(f"    {line}", file=sys.stderr)
            extra = len(offenders[repo]) - 20
            if extra > 0:
                print(f"    ... and {extra} more", file=sys.stderr)

    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
