#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List the test files whose text names a changed path.

Usage:
    uv run python3 crux/scripts/related-tests.py PATH [PATH ...] [--repo-root DIR] [--json]
        [--tier TIER]... [--ids]

Output: one repository-relative test path per line, sorted, on stdout. A run that finds none prints
nothing and exits 0. ``--json`` prints one object instead::

    {"changed": [...], "tests": {"<test path>": ["<token that matched>", ...]}, "readers": {"<script>": [...]}}

Run each listed file with ``unittest discover -s <its directory> -p <its file name>``.

``--tier TIER`` (repeatable; dev, release or ephemeral) keeps a related file when any of its test units
resolves to a selected tier in the tier manifest beside it (``test-tiers.json``; ``test_tiers.py`` reads
it), and always keeps a file the change itself edits, of any tier. A missing or invalid manifest in a
test directory that holds a related file exits 2. ``--ids`` prints the module, class and method ids a
runner selects (``parallel_suite.py --select`` reads them) instead of file paths, and needs ``--tier``.
Tiers narrow a development loop only. A gate (a unit's completion, Build exit, cycle completion, a merge)
runs every test, so a gate never calls this option.

A test file is a ``test*.py`` file directly under ``crux/scripts/tests`` or ``tools/tests`` of the
repository root (``--repo-root``, default the working directory; never this script's own path). A
directory that is absent is skipped, so the tool runs in the staged plugin artifact, which has no
``tools/``. Exit codes: 0 listed (possibly nothing), 2 environment error on stderr (no test directory,
a path outside the root, an unreadable root).

A test is related to a changed path when its text names one of these tokens:

* the repository path, for example ``crux/templates/micro-crux.md.tmpl``;
* the file name, for example ``micro-crux.md.tmpl``;
* for a ``.py`` file, the module stem (``suite_evidence``) and its importable underscore form
  (``generate-micro-crux`` also matches ``generate_micro_crux``). A stem under four characters is
  too common to name anything and is skipped.

A token matches only as a whole word, so ``test_evidence`` does not match ``test_evidence_registry``.
A changed path that is itself a test file is listed.

``extra_candidates(repo_root, changed_paths)`` separately returns optional tests and declared drift
gates whose identifiers share tokens with changed modules or their direct readers. It performs no
execution or ranking. Literal test matches are excluded from that list and remain authoritative.
The CLI output above is unchanged; callers explicitly opt into the candidate API.

One hop through readers, for a changed path that is not a ``.py`` file (a template, a schema, a data
file; a changed module is already named by the tests that import it, and hopping through its importers
would list most of the suite): a script directly under ``crux/scripts`` or ``tools`` that names the changed
path in code (a ``#`` comment line does not count) is a reader of it, and the tests that name the reader's module stem are listed too. This is how a
change to ``crux/templates/micro-crux.md.tmpl`` reaches ``test_micro_crux_contracts.py``, which runs
``generate-micro-crux.py`` and never names the template.

Limits, stated plainly:

* A test that enumerates a directory (a glob, a walk, ``rglob``) without naming the changed file is
  not found.
* A test that reaches the path through a second reader, through a constant built at run time, or
  through a path split across string pieces is not found.
* A match is textual, so a comment or a docstring that names the path also lists the test. The list
  is a superset of the tests that read the path in the cases it finds, and says nothing about the
  rest. Run the full suite when the change is wide.
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import os
import re
import sys
from pathlib import Path

TEST_DIRECTORIES = ("crux/scripts/tests", "tools/tests")
READER_DIRECTORIES = ("crux/scripts", "tools")
MIN_STEM = 4
CANDIDATE_NOISE = frozenset(("test", "tests", "check", "generate", "script", "scripts", "crux"))


class EnvironmentProblem(Exception):
    """The tool cannot run here: exit 2."""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise EnvironmentProblem(f"cannot read {path}: {exc.strerror or exc}") from exc


def _without_comment_lines(text: str) -> str:
    """A script that names the path only in a ``#`` comment line does not read it."""
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _repo_relative(root: Path, raw: str) -> str:
    path = Path(raw)
    resolved = path if path.is_absolute() else root / path
    try:
        relative = Path(resolved).resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise EnvironmentProblem(f"{raw} is outside the repository root {root}") from exc
    if not relative.parts:
        raise EnvironmentProblem(f"{raw} is the repository root; name a file")
    return relative.as_posix()


def tokens_for(relative: str) -> list[str]:
    """The strings that name ``relative`` in a test: its path, its file name, and for .py its module stem forms."""
    path = Path(relative)
    found = [relative, path.name]
    if path.suffix == ".py" and len(path.stem) >= MIN_STEM:
        found += [path.stem, path.stem.replace("-", "_")]
    seen = []
    for token in found:
        if token not in seen:
            seen.append(token)
    return seen


def _pattern(tokens: list[str]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True))
    return re.compile(rf"(?<![\w-])(?:{alternatives})(?![\w-])")


def _check(checkpoint):
    if checkpoint is not None:
        checkpoint()


def _files(root: Path, directories: tuple[str, ...], pattern: str, *, checkpoint=None) -> list[Path]:
    found = []
    for directory in directories:
        _check(checkpoint)
        base = root / directory
        if base.is_dir():
            entries = []
            for path in base.glob(pattern):
                _check(checkpoint)
                if path.is_file():
                    entries.append(path)
            found += sorted(entries)
    _check(checkpoint)
    return found


def related(root: Path, changed: list[str], *, checkpoint=None) -> dict:
    """``{"changed", "tests", "readers"}`` for the repository-relative ``changed`` paths."""
    test_files = _files(root, TEST_DIRECTORIES, "test*.py", checkpoint=checkpoint)
    if not test_files:
        raise EnvironmentProblem(f"no test directory under {root}: looked for {', '.join(TEST_DIRECTORIES)}")
    texts = {}
    for path in test_files:
        _check(checkpoint)
        texts[path.relative_to(root).as_posix()] = _read(path)
    tests: dict[str, list[str]] = {}
    readers: dict[str, list[str]] = {}

    def note(test: str, token: str) -> None:
        if token not in tests.setdefault(test, []):
            tests[test].append(token)

    reader_texts = None
    for path in changed:
        _check(checkpoint)
        if path in texts:
            note(path, path)
        direct = tokens_for(path)
        direct_pattern = _pattern(direct)
        for test, text in texts.items():
            _check(checkpoint)
            for match in sorted(set(direct_pattern.findall(text))):
                note(test, match)
        # One hop: scripts that name the path read it, so the tests that name those scripts are related.
        # Only for a path that is not a module: tests import a changed module by its stem already, and
        # hopping through its importers would list most of the suite.
        if path.endswith(".py"):
            continue
        if reader_texts is None:
            reader_texts = {}
            for reader in _files(root, READER_DIRECTORIES, "*.py", checkpoint=checkpoint):
                _check(checkpoint)
                if reader.name != Path(__file__).name:
                    reader_texts[reader.relative_to(root).as_posix()] = _without_comment_lines(_read(reader))
        for reader, text in reader_texts.items():
            _check(checkpoint)
            if reader == path or reader in texts or not direct_pattern.search(text):
                continue
            via = [t for t in tokens_for(reader) if t not in (reader, Path(reader).name)]
            if not via:
                continue
            readers.setdefault(reader, []).append(path)
            via_pattern = _pattern(via)
            for test, test_text in texts.items():
                _check(checkpoint)
                for match in sorted(set(via_pattern.findall(test_text))):
                    note(test, f"{match} (reads {path})")
    _check(checkpoint)
    return {"changed": changed, "tests": dict(sorted(tests.items())), "readers": dict(sorted(readers.items()))}


def _identifier_tokens(relative: str) -> set[str]:
    """Whole name components, without directory names or generic test/generator prefixes."""
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", Path(relative).name.split(".", 1)[0])
    return {token for token in re.findall(r"[a-z0-9]+", name.lower())
            if len(token) >= 3 and token not in CANDIDATE_NOISE}


def _candidate_path(root: Path, path: Path) -> str | None:
    """Only existing regular files inside this repository may become optional suggestions."""
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        return None
    return path.relative_to(root).as_posix()


def _drift_candidates(root: Path, *, checkpoint=None) -> set[str]:
    """Read script names from the two canonical drift tables, never commands from prose."""
    declaration = root / "crux/skills/check-drift/SKILL.md"
    if _candidate_path(root, declaration) is None:
        return set()
    found = set()
    in_table = False
    for line in _read(declaration).splitlines():
        _check(checkpoint)
        if line.startswith(("| Gate (output) | Scope |", "| Guard | Scope |")):
            in_table = True
            continue
        if not line.startswith("|"):
            in_table = False
        if not in_table:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        for name in re.findall(r"(?<![\w./-])([a-z0-9_-]+\.py)(?![\w./-])", cells[2]):
            relative = _candidate_path(root, root / "crux/scripts" / name)
            if relative is not None:
                found.add(relative)
    return found


def extra_candidates(repo_root: Path, changed_paths: Sequence[str], *, checkpoint=None) -> list[dict[str, str]]:
    """Deterministic optional overlap candidates; never removes or executes a required check.

    IDs are ``test:<relative path>`` or ``drift:<relative path>``. A reason contains sorted shared
    tokens and one representative source per token. Reader discovery here includes
    changed Python modules; that broader, candidate-only hop does not alter ``related`` selection.
    Token overlap is a heuristic, not a dependency or a claim that these checks suffice.
    """
    _check(checkpoint)
    root = Path(repo_root).resolve()
    changed = set()
    for raw in changed_paths:
        _check(checkpoint)
        changed.add(_repo_relative(root, raw))
    changed = sorted(changed)
    if not changed:
        return []
    authoritative = related(root, changed, checkpoint=checkpoint)["tests"]
    origins: dict[str, set[str]] = {}

    def add_origin(path: str, reason: str) -> None:
        for token in _identifier_tokens(path):
            origins.setdefault(token, set()).add(reason)

    for path in changed:
        _check(checkpoint)
        add_origin(path, path)
    patterns = [(path, _pattern(tokens_for(path))) for path in changed]
    for reader in _files(root, READER_DIRECTORIES, "*.py", checkpoint=checkpoint):
        _check(checkpoint)
        relative = _candidate_path(root, reader)
        if relative is None or reader.name == Path(__file__).name:
            continue
        text = _without_comment_lines(_read(reader))
        for path, pattern in patterns:
            _check(checkpoint)
            if relative != path and pattern.search(text):
                add_origin(relative, f"{relative} (reads {path})")

    candidates = {}
    for path in _files(root, TEST_DIRECTORIES, "test*.py", checkpoint=checkpoint):
        _check(checkpoint)
        if (relative := _candidate_path(root, path)) is not None:
            candidates[relative] = 'test'
    for path in _drift_candidates(root, checkpoint=checkpoint):
        _check(checkpoint)
        candidates.setdefault(path, "drift")
    result = []
    for path, kind in sorted(candidates.items()):
        _check(checkpoint)
        if path in authoritative:
            continue
        shared = sorted(_identifier_tokens(path) & origins.keys())
        if shared:
            sources = sorted({min(origins[token]) for token in shared})
            result.append({"id": kind + ":" + path, "path": path,
                           "reason": "shared tokens: " + ", ".join(shared) + "; sources: " + "; ".join(sources)})
    _check(checkpoint)
    return sorted(result, key=lambda row: (row["path"], row["id"]))


def apply_tier(root: Path, report: dict, tiers: Sequence[str]) -> dict:
    """``{"tests", "ids"}``: the related files narrowed to ``tiers`` plus the edited files, and their ids.

    A file stays when one of its test units resolves to a selected tier, or when the change edits it
    (an edited file runs whole, whatever its tiers). Raises ``EnvironmentProblem`` when a test directory
    that holds a related file has a missing or invalid manifest.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_tiers
    edited = set(report["changed"])
    manifests: dict[str, dict] = {}
    kept: dict[str, list[str]] = {}
    ids: list[str] = []
    for test, tokens in report["tests"].items():
        directory, name = test.rsplit("/", 1)
        if directory not in manifests:
            try:
                manifests[directory] = test_tiers.load(root / directory)
            except test_tiers.ManifestError as exc:
                raise EnvironmentProblem(f"--tier needs a valid tier manifest for {directory}: {exc}")
        data = manifests[directory]
        module = name[:-3]
        if test in edited:
            kept[test] = tokens
            ids.append(module)
        elif name in test_tiers.selected_files(data, root / directory, tiers):
            kept[test] = tokens
            ids += [i for i in test_tiers.selected_ids(data, root / directory, tiers)
                    if i == module or i.startswith(module + ".")]
    return {"tests": kept, "ids": sorted(set(ids))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="List the test files whose text names a changed path.")
    parser.add_argument("paths", nargs="+", metavar="PATH", help="a changed path, relative to the repository root or absolute")
    parser.add_argument("--repo-root", default=None, help="the repository root (default: the working directory)")
    parser.add_argument("--json", action="store_true", help="print one JSON object with the matched tokens")
    parser.add_argument("--tier", action="append", default=[], choices=("dev", "release", "ephemeral"), metavar="TIER",
                        help="keep the related files with a unit in this tier, plus the files the change edits; repeatable")
    parser.add_argument("--ids", action="store_true", help="with --tier: print selection ids instead of file paths")
    args = parser.parse_args(argv)
    if args.ids and not args.tier:
        parser.error("--ids needs --tier")
    try:
        root = Path(args.repo_root or Path.cwd()).resolve()
        if not root.is_dir():
            raise EnvironmentProblem(f"repository root {root} is not a directory")
        changed = []
        for raw in args.paths:
            relative = _repo_relative(root, raw)
            if relative not in changed:
                changed.append(relative)
        report = related(root, changed)
        narrowed = apply_tier(root, report, args.tier) if args.tier else None
    except EnvironmentProblem as exc:
        print(f"related-tests: {exc}", file=sys.stderr)
        return 2
    if narrowed is not None:
        report = {**report, "tests": narrowed["tests"], "ids": narrowed["ids"]}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.ids:
        for test_id in report["ids"]:
            print(test_id)
    else:
        for test in report["tests"]:
            print(test)
    return 0


if __name__ == "__main__":
    sys.exit(main())
