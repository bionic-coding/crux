"""The flagged list: the tests that can differ between interpreters or between the checkout and the package.

The committed list ``crux/scripts/tests/flagged_tests.json`` names those tests. The staged ``flagged``
check (``parallel_suite.py --flagged``) runs exactly the entries that apply to the running Python minor,
on the staged tree. Every other test runs once in the main run on the floor minor.

An entry is a mapping with these keys:

* ``test``: a module, class or method id, as ``parallel_suite.py --select`` reads it. List a method id
  when the class holds a method that skips on some interpreters, because a selected test that skips
  fails the check.
* ``class``: ``cross-minor`` (the result depends on the interpreter), ``packaging`` (the result depends
  on the packaged tree) or ``harness`` (the result depends on the test environment: interpreter path,
  working directory, cache, dependency resolution).
* ``reason``: why the test is flagged.
* ``origin``: the evidence receipt (``TE-...``) or commit that showed it.
* ``minors`` (optional): the Python minors the entry applies to. Absent means every supported minor.

The validator refuses an entry that lacks a class, a reason or an origin, and a minor that
``pyproject.toml`` ``[tool.crux] python-versions`` does not list. On a minor an entry applies to, an
entry that selects no test, and an entry whose test skips, fail the check; ``parallel_suite.py`` applies
those two rules when it runs the list.
"""
from __future__ import annotations

import json
from pathlib import Path

CLASSES = ("cross-minor", "packaging", "harness")
REQUIRED = ("test", "class", "reason", "origin")
OPTIONAL = ("minors",)
DEFAULT_RELATIVE = "crux/scripts/tests/flagged_tests.json"


class FlaggedError(Exception):
    """The list cannot be read as a list of entries."""


def default_path(root=None):
    base = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    return base / DEFAULT_RELATIVE


def load(path):
    """The entries of the list file at ``path``. Raises ``FlaggedError`` when it is not a list of mappings."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FlaggedError(f"cannot read the flagged list {path}: {type(exc).__name__}: {exc}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
        raise FlaggedError(f"the flagged list {path} must be an object with an `entries` list of objects")
    return entries


def _blank(value):
    return not isinstance(value, str) or not value.strip()


def validate(entries, minors=None, tiers_dir=None):
    """The problems of ``entries``, one string each; empty when the list is valid.

    ``minors`` is the supported Python minors (``pyproject.toml`` ``[tool.crux] python-versions``).
    ``None`` skips the minor check, for a tree that carries no project file. ``tiers_dir`` is the
    directory of the tier manifest that ships beside the list; when given, the manifest is required and
    every entry must select release-tier tests only (``tier_problems``).
    """
    problems = []
    seen = set()
    for position, item in enumerate(entries):
        name = item.get("test") if isinstance(item.get("test"), str) and item.get("test").strip() else f"entry {position}"
        unknown = sorted(set(item) - set(REQUIRED) - set(OPTIONAL))
        if unknown:
            problems.append(f"{name}: unknown key(s) {', '.join(unknown)}")
        for key in REQUIRED:
            if _blank(item.get(key)):
                problems.append(f"{name}: missing {key}")
        if not _blank(item.get("class")) and item["class"] not in CLASSES:
            problems.append(f"{name}: class {item['class']!r} is not one of {', '.join(CLASSES)}")
        if "minors" in item:
            listed = item["minors"]
            if not isinstance(listed, list) or not listed or not all(isinstance(m, str) for m in listed):
                problems.append(f"{name}: minors must be a nonempty list of Python minors")
            elif minors is not None:
                outside = [m for m in listed if m not in minors]
                if outside:
                    problems.append(f"{name}: minor(s) {', '.join(outside)} not in python-versions ({', '.join(minors)})")
        if not _blank(item.get("test")):
            if item["test"] in seen:
                problems.append(f"{name}: listed twice")
            seen.add(item["test"])
    if tiers_dir is not None:
        problems += tier_problems(entries, tiers_dir)
    return problems


def tier_problems(entries, tests_dir):
    """The problems of ``entries`` against the tier manifest in ``tests_dir``; empty when all is release.

    The manifest ships beside the list, so it is required: a missing or invalid one is a problem. Every
    test unit an entry selects must resolve to the release tier, so the staged per-minor flagged check
    runs only release-tier tests (IDR test-tiers A4).
    """
    import test_tiers
    try:
        data = test_tiers.load(tests_dir)
    except test_tiers.ManifestError as exc:
        return [f"the tier manifest beside the flagged list is required: {exc}"]
    rows = test_tiers.units(data, tests_dir)
    problems = []
    for item in entries:
        name = item.get("test")
        if _blank(name):
            continue
        parts = name.split(".")
        tiers = {effective["tier"] for file, cls, method, effective in rows
                 if file[:-3] == parts[0] and (len(parts) == 1 or (parts[1] == cls and (len(parts) == 2 or parts[2] == method)))}
        if not tiers:
            found = test_tiers.tier_of_id(data, name)
            tiers = {found} if found else set()
        if not tiers:
            problems.append(f"{name}: no test unit of the tier manifest matches it")
        elif tiers != {"release"}:
            problems.append(f"{name}: selects tests outside the release tier ({', '.join(sorted(tiers - {'release'}))})")
    return problems


def applicable(entries, minor):
    """The entries that apply to ``minor``: those with no ``minors`` key, or whose ``minors`` lists it."""
    return [item for item in entries if "minors" not in item or minor in item["minors"]]


def selection(entries, minor):
    """The sorted test ids of the entries that apply to ``minor``."""
    return sorted({item["test"] for item in applicable(entries, minor)})
