"""The test-tier reader: label every test with one tier and select tests by tier.

A *test root* is a directory of test files. It holds one ``test-tiers.json`` manifest that gives each
test file a tier: ``dev`` (the default development loop), ``release`` (the tests that show a shipped
system area works end to end, run at release verify) or ``ephemeral`` (a test of a one-time transition
or historical record, labelled with a reason and an expiry or retirement condition). This module is
the one reader: the CLI ``test-tiers.py``, ``parallel_suite.py --tier`` and any other consumer call
it. It uses the standard library only, so it runs in the staged tree and in a project without the
crux environment.

Manifest shape (``crux/schemas/test-tiers.schema.json`` documents it; this module is authoritative)::

    {"format": "crux.test-tiers", "version": 1, "kind": "python-unittest", "pattern": "test*.py",
     "areas": {"<area id>": "<one-line description>"},
     "files": {"test_x.py": {"tier": "dev",
                              "overrides": {"Klass": {"tier": "release", "area": "<area id>"},
                                            "Klass.test_m": {"tier": "ephemeral", "reason": "...",
                                                             "retire_when": "..."}}}}}

``kind`` is ``python-unittest`` or ``file-glob``. ``files`` keys are bare file names matching
``pattern``. A method override wins over a class override, which wins over the file entry, so every
test resolves to exactly one tier. A release entry carries ``area`` (declared in ``areas``); an
ephemeral entry carries ``reason`` and ``expires`` (YYYY-MM-DD) or ``retire_when``; a dev entry
carries neither.

Counting rule: a ``python-unittest`` root counts one unit per ``test*`` method of each module-level
class defined in the file (an AST walk); a ``file-glob`` root counts one unit per file. A class
imported from another module is absent from that file's AST, so only the file default labels it; a
method a local class inherits can be labelled by the file default or a class override, never a
method override. Runtime selection (``tier_of_id``) uses real discovery ids.
"""
from __future__ import annotations

import ast
import datetime
import fnmatch
import json
import os
import re
import subprocess
from pathlib import Path

FORMAT = "crux.test-tiers"
VERSION = 1
MANIFEST_NAME = "test-tiers.json"
KINDS = ("python-unittest", "file-glob")
TIERS = ("dev", "release", "ephemeral")
TOP_KEYS = ("format", "version", "kind", "pattern", "areas", "files")
ENTRY_KEYS = ("tier", "area", "reason", "expires", "retire_when", "overrides")
OVERRIDE_KEYS = ("tier", "area", "reason", "expires", "retire_when")
FIELD_KEYS = ("area", "reason", "expires", "retire_when")
TIER_FIELDS = {"dev": (), "release": ("area",), "ephemeral": ("reason", "expires", "retire_when")}
FAILED_TEST_PREFIX = "unittest.loader._FailedTest."
COUNTING_RULE = ("python-unittest: one unit per test* method of each module-level class defined in "
                 "the file (AST); file-glob: one unit per file")

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


class ManifestError(Exception):
    """A manifest cannot be read as JSON, or has no usable top-level shape."""


def finding(code, path, detail):
    return {"code": code, "path": str(path), "detail": detail}


# --- loading -------------------------------------------------------------------------------------

def read_json(path):
    """``(data, duplicate_keys)`` of the JSON file at ``path``.

    A duplicate object key at any level is recorded, not raised, so the checker can report it as a
    doubly-labelled finding. Raises ``ManifestError`` when the file is unreadable or not JSON.
    """
    duplicates = []

    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                duplicates.append(key)
            seen[key] = value
        return seen

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, ValueError) as exc:
        raise ManifestError(f"cannot read the tier manifest {path}: {type(exc).__name__}: {exc}") from exc
    return data, duplicates


def manifest_path(root):
    return Path(root) / MANIFEST_NAME


def load(root):
    """The validated manifest of ``root`` (per-root rules).

    Raises ``ManifestError`` when the manifest is missing, unreadable or has a finding. Consumers that
    select tests (``parallel_suite.py --tier``, ``list``) call this and fail closed on the error.
    """
    path = manifest_path(root)
    if not path.is_file():
        raise ManifestError(f"no tier manifest at {path}")
    data, duplicates = read_json(path)
    findings = [finding("duplicate-key", path, f"duplicate JSON key {key!r}") for key in duplicates]
    findings += validate(data, root)
    if findings:
        detail = "; ".join(f"{f['code']}: {f['detail']}" for f in findings[:5])
        raise ManifestError(f"the tier manifest {path} is invalid: {detail}")
    return data


# --- AST units -----------------------------------------------------------------------------------

def file_units(path):
    """``[(class, method), ...]`` for the ``test*`` methods of the module-level classes in a file.

    Raises ``SyntaxError`` or ``OSError`` when the file cannot be parsed.
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    units = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name.startswith("test"):
                    units.append((node.name, member.name))
    return units


def file_classes(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


# --- resolution ----------------------------------------------------------------------------------

def resolve(entry, cls=None, method=None):
    """The effective entry (a mapping with ``tier``) of a test: method override, class override, file entry."""
    overrides = entry.get("overrides") or {}
    if cls and method and f"{cls}.{method}" in overrides:
        return overrides[f"{cls}.{method}"]
    if cls and cls in overrides:
        return overrides[cls]
    return entry


def tier_of(entry, cls=None, method=None):
    return resolve(entry, cls, method)["tier"]


def tier_of_id(data, test_id):
    """The tier of a discovery id ``module.Class.method``, or ``None`` when its module has no entry."""
    parts = test_id.split(".")
    module = parts[0]
    entry = data["files"].get(module + ".py")
    if entry is None:
        return None
    cls = parts[1] if len(parts) > 1 else None
    method = parts[2] if len(parts) > 2 else None
    return tier_of(entry, cls, method)


def units(data, root):
    """``[(file, class, method, effective_entry), ...]`` for every test unit under the manifest's files.

    Files that are absent or unparseable contribute no unit (the checker reports them).
    """
    rows = []
    for name in sorted(data["files"]):
        entry = data["files"][name]
        if data["kind"] == "file-glob":
            if (Path(root) / name).is_file():
                rows.append((name, None, None, entry))
            continue
        try:
            found = file_units(Path(root) / name)
        except (OSError, SyntaxError, ValueError):
            continue
        for cls, method in found:
            rows.append((name, cls, method, resolve(entry, cls, method)))
    return rows


# --- validation ----------------------------------------------------------------------------------

def _is_date(value):
    if not isinstance(value, str) or not _DATE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _effective(entry):
    return {key: entry.get(key) for key in ("tier", *FIELD_KEYS) if entry.get(key) is not None}


def validate_entry(entry, where, path, allowed, kind):
    """Findings for one entry or override: allowed keys, tier, and the tier's fields."""
    out = []
    if not isinstance(entry, dict):
        return [finding("bad-field", path, f"{where}: an entry must be an object")]
    for key in sorted(set(entry) - set(allowed)):
        out.append(finding("bad-field", path, f"{where}: unknown or disallowed key {key!r}"))
    tier = entry.get("tier")
    if tier not in TIERS:
        out.append(finding("bad-field", path, f"{where}: tier {tier!r} is not one of {', '.join(TIERS)}"))
        return out
    for key in FIELD_KEYS:
        if key in entry and key not in TIER_FIELDS[tier]:
            out.append(finding("bad-field", path, f"{where}: a {tier} entry carries no {key}"))
    if tier == "release" and not _text(entry.get("area")):
        out.append(finding("missing-area", path, f"{where}: a release entry needs an area"))
    if tier == "ephemeral":
        if not _text(entry.get("reason")):
            out.append(finding("ephemeral-no-reason", path, f"{where}: an ephemeral entry needs a reason"))
        if not _text(entry.get("expires")) and not _text(entry.get("retire_when")):
            out.append(finding("ephemeral-no-expiry", path,
                               f"{where}: an ephemeral entry needs expires or retire_when"))
        if "expires" in entry and not _is_date(entry["expires"]):
            out.append(finding("bad-date", path, f"{where}: expires {entry['expires']!r} is not YYYY-MM-DD"))
    return out


def validate(data, root, *, shard=False, label=None):
    """Per-root findings for parsed manifest ``data`` at ``root``.

    ``shard`` skips the unlabelled rules, for a partial manifest a classifier writes. ``label`` is the
    path findings report (default the root's manifest).
    """
    path = label or manifest_path(root)
    root = Path(root)
    out = []
    if not isinstance(data, dict):
        return [finding("invalid-manifest", path, "the manifest must be a JSON object")]
    for key in sorted(set(data) - set(TOP_KEYS)):
        out.append(finding("bad-field", path, f"unknown top-level key {key!r}"))
    for key in TOP_KEYS:
        if key not in data:
            out.append(finding("invalid-manifest", path, f"missing top-level key {key!r}"))
    if out:
        return out
    if data["format"] != FORMAT:
        out.append(finding("invalid-manifest", path, f"format must be {FORMAT!r}"))
    if data["version"] != VERSION or isinstance(data["version"], bool):
        out.append(finding("invalid-manifest", path, f"version must be {VERSION}"))
    if data["kind"] not in KINDS:
        out.append(finding("invalid-manifest", path, f"kind must be one of {', '.join(KINDS)}"))
    if not _text(data["pattern"]):
        out.append(finding("invalid-manifest", path, "pattern must be a nonempty string"))
    if not isinstance(data["areas"], dict) or not all(_text(k) and _text(v) for k, v in data["areas"].items()):
        out.append(finding("invalid-manifest", path, "areas must map an area id to a one-line description"))
    if not isinstance(data["files"], dict):
        out.append(finding("invalid-manifest", path, "files must map a test file name to an entry"))
    if out:
        return out
    kind, pattern = data["kind"], data["pattern"]
    for name in sorted(data["files"]):
        entry = data["files"][name]
        where = f"files.{name}"
        if "/" in name or "\\" in name or ".." in name or not fnmatch.fnmatchcase(name, pattern):
            out.append(finding("bad-field", path, f"{where}: a files key is a bare file name matching {pattern!r}"))
            continue
        allowed = ENTRY_KEYS if kind == "python-unittest" else tuple(k for k in ENTRY_KEYS if k != "overrides")
        problems = validate_entry(entry, where, path, allowed, kind)
        out += problems
        target = root / name
        if not target.is_file():
            out.append(finding("stale-file", path, f"{where}: names a file absent from {root}"))
            continue
        overrides = entry.get("overrides") if isinstance(entry, dict) else None
        if overrides is None:
            continue
        if not isinstance(overrides, dict):
            out.append(finding("bad-field", path, f"{where}.overrides must be an object"))
            continue
        try:
            units_here = file_units(target)
            classes = file_classes(target)
        except (OSError, SyntaxError, ValueError) as exc:
            out.append(finding("unparseable-file", path, f"{where}: cannot parse {name}: {exc}"))
            continue
        methods = {}
        for cls, method in units_here:
            methods.setdefault(cls, set()).add(method)
        for key in sorted(overrides):
            spot = f"{where}.overrides.{key}"
            parts = key.split(".")
            if len(parts) > 2 or not all(_IDENT.match(p) for p in parts):
                out.append(finding("bad-field", path, f"{spot}: an override key is ClassName or ClassName.test_method"))
                continue
            sub = validate_entry(overrides[key], spot, path, OVERRIDE_KEYS, kind)
            out += sub
            if parts[0] not in classes:
                out.append(finding("stale-override", path, f"{spot}: class {parts[0]} is not defined in {name}"))
                continue
            if len(parts) == 2 and parts[1] not in methods.get(parts[0], set()):
                out.append(finding("stale-override", path, f"{spot}: {parts[1]} is not a test method of {parts[0]}"))
                continue
            if sub or not isinstance(overrides[key], dict) or not isinstance(entry, dict):
                continue
            inherited = entry
            if len(parts) == 2 and parts[0] in overrides and isinstance(overrides[parts[0]], dict):
                inherited = overrides[parts[0]]
            if _effective(overrides[key]) == _effective(inherited):
                out.append(finding("redundant-override", path,
                                   f"{spot}: equals what it would inherit; remove it"))
    for name in sorted(data["files"]):
        entry = data["files"][name]
        for scope, item in [(f"files.{name}", entry), *[(f"files.{name}.overrides.{k}", v)
                                                      for k, v in (entry.get("overrides") or {}).items()
                                                      if isinstance(entry, dict) and isinstance(entry.get("overrides"), dict)]]:
            if isinstance(item, dict) and item.get("tier") == "release" and _text(item.get("area")) \
                    and item["area"] not in data["areas"]:
                out.append(finding("undeclared-area", path, f"{scope}: area {item['area']!r} is not declared in areas"))
    if not shard:
        out += unlabelled(data, root, path)
    return out


def _walk_matching(root, pattern):
    """Pattern-matching files below ``root`` (not directly in it), as ``(relative path, dir parts)``."""
    found = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS and not d.startswith("."))
        if Path(current) == Path(root):
            continue
        for name in sorted(files):
            if fnmatch.fnmatchcase(name, pattern):
                found.append(Path(current) / name)
    return found


def reach(data, root):
    """Files a runner would discover for this root that sit below it (the unlabelled-nested set)."""
    root = Path(root)
    if data["kind"] == "file-glob":
        nested_roots = [p.parent for p in root.rglob(MANIFEST_NAME)
                        if p.parent != root and not (set(p.relative_to(root).parts) & _SKIP_DIRS)]
        return [p for p in _walk_matching(root, data["pattern"])
                if not any(n == p.parent or n in p.parents for n in nested_roots)]
    reached = []
    for p in _walk_matching(root, data["pattern"]):
        between = [q for q in p.parents if q != root and root in q.parents]
        if all((q / "__init__.py").is_file() for q in between):
            reached.append(p)
    return reached


def unlabelled(data, root, path):
    out = []
    root = Path(root)
    pattern = data["pattern"]
    for child in sorted(root.iterdir()):
        if child.name == MANIFEST_NAME:
            continue  # the manifest is not a test, even when the pattern (such as *.json) matches it
        if child.is_file() and fnmatch.fnmatchcase(child.name, pattern) and child.name not in data["files"]:
            out.append(finding("unlabelled", path, f"{child.name} matches {pattern!r} and has no files entry"))
    for nested in reach(data, root):
        out.append(finding("unlabelled-nested", path,
                           f"{nested.relative_to(root)} is below the root; move it to the root or drop __init__.py"))
    return out


# --- project-wide check --------------------------------------------------------------------------

def _git(repo, *args):
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done if done.returncode == 0 else None


def git_toplevel(repo):
    done = _git(repo, "rev-parse", "--show-toplevel")
    return Path(done.stdout.strip()).resolve() if done else None


def discover_manifests(repo, mode="auto"):
    """Manifest roots under ``repo``: git-tracked files named exactly ``test-tiers.json``, or a walk.

    ``mode`` is ``git``, ``filesystem`` or ``auto`` (git when ``repo`` is the top of a work tree, else a
    walk that skips ``.git``).
    """
    repo = Path(repo).resolve()
    use_git = mode == "git" or (mode == "auto" and git_toplevel(repo) == repo)
    roots = []
    if use_git:
        done = _git(repo, "ls-files", "-z")
        if done is None:
            raise ManifestError(f"git ls-files failed in {repo}")
        for rel in done.stdout.split("\0"):
            if rel and Path(rel).name == MANIFEST_NAME and (repo / rel).is_file():
                roots.append((repo / rel).parent)
    else:
        for current, dirs, files in os.walk(repo):
            dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
            if MANIFEST_NAME in files:
                roots.append(Path(current))
    return sorted(set(roots)), use_git


def _tracked(repo, path):
    return _git(repo, "ls-files", "--error-unmatch", "--", str(path)) is not None


def counts_of(data, root):
    counts = {tier: 0 for tier in TIERS}
    for _, _, _, effective in units(data, root):
        counts[effective["tier"]] += 1
    return counts


def check_roots(repo, roots, *, expect=(), require_release=(), mode="auto", today=None):
    """The project-wide check over manifest ``roots`` (paths) plus the ``expect`` roots (relative to ``repo``).

    Returns ``{"configured", "roots", "counts", "findings", "expired", "counting"}``.
    """
    repo = Path(repo).resolve()
    today = today or datetime.date.today()
    findings, expired = [], []
    use_git = mode == "git" or (mode == "auto" and git_toplevel(repo) == repo)
    chosen = {Path(r).resolve() for r in roots}
    for item in expect:
        root = (repo / item).resolve()
        if not manifest_path(root).is_file():
            findings.append(finding("missing-root", manifest_path(root), "an expected root holds no manifest"))
        else:
            if use_git and not _tracked(repo, manifest_path(root)):
                findings.append(finding("untracked-root", manifest_path(root),
                                        "the manifest is not tracked by git; a checkout would not carry it"))
            chosen.add(root)
    configured = bool(chosen)
    report_roots, totals = {}, {tier: 0 for tier in TIERS}
    manifests = {}
    areas_seen, release_areas = {}, set()
    for root in sorted(chosen):
        name = os.path.relpath(root, repo)
        path = manifest_path(root)
        try:
            data, duplicates = read_json(path)
        except ManifestError as exc:
            findings.append(finding("invalid-manifest", path, str(exc)))
            continue
        findings += [finding("duplicate-key", path, f"duplicate JSON key {key!r}") for key in duplicates]
        problems = validate(data, root)
        findings += problems
        if any(p["code"] == "invalid-manifest" for p in problems):
            continue
        manifests[root] = data
        counts = counts_of(data, root)
        report_roots[name] = {"kind": data["kind"], "counts": counts, "files": len(data["files"])}
        for tier in TIERS:
            totals[tier] += counts[tier]
        for area, description in data["areas"].items():
            if area in areas_seen and areas_seen[area] != description:
                findings.append(finding("area-conflict", path, f"area {area!r} has two descriptions"))
            areas_seen.setdefault(area, description)
        seen_expired = set()
        for fname, _, _, effective in units(data, root):
            if effective["tier"] == "release" and effective.get("area"):
                release_areas.add(effective["area"])
            if effective["tier"] == "ephemeral" and _is_date(effective.get("expires", "")) \
                    and datetime.date.fromisoformat(effective["expires"]) < today:
                row = (fname, effective["expires"], effective.get("reason", ""))
                if row not in seen_expired:  # one row per file and label, not one per unit
                    seen_expired.add(row)
                    expired.append({"path": str(path), "file": fname, "expires": row[1], "reason": row[2]})
    for item in require_release:
        key = os.path.relpath((repo / item).resolve(), repo)
        if key not in report_roots:
            findings.append(finding("root-no-release-units", key,
                                    "a root named by --require-release-units has no checked manifest"))
        elif report_roots[key]["counts"]["release"] == 0:
            findings.append(finding("root-no-release-units", key, "a root named by --require-release-units holds no release unit"))
    # a file reachable from two manifests is doubly-labelled
    owners = {}
    for root, data in manifests.items():
        for name in data["files"]:
            owners.setdefault((root / name).resolve(), []).append(root)
        for nested in reach(data, root):
            owners.setdefault(nested.resolve(), []).append(root)
    for target, held in sorted(owners.items()):
        if len(set(held)) > 1:
            findings.append(finding("doubly-labelled", target, "covered by manifests of " + ", ".join(
                sorted(os.path.relpath(h, repo) for h in set(held)))))
    if configured and manifests:
        total = sum(totals.values())
        if total < 2 or not areas_seen:
            findings.append(finding("too-small", repo, "a project adopts tiers with at least two tests and one declared area"))
        if totals["release"] == 0:
            findings.append(finding("no-release-units", repo, "the release tier holds no test unit"))
        if total - totals["release"] == 0:
            findings.append(finding("no-non-release-units", repo, "the release tier is not a proper subset"))
        for area in sorted(set(areas_seen) - release_areas):
            findings.append(finding("uncovered-area", repo, f"area {area!r} has no release unit"))
    return {"configured": configured, "roots": report_roots, "counts": totals, "findings": findings,
            "expired": expired, "counting": COUNTING_RULE}


# --- selection -----------------------------------------------------------------------------------

def selected_files(data, root, tiers):
    """Files holding at least one unit in ``tiers`` (a file with no countable unit follows its file entry)."""
    tiers = set(tiers)
    by_file = {}
    for name, _, _, effective in units(data, root):
        by_file.setdefault(name, set()).add(effective["tier"])
    out = []
    for name in sorted(data["files"]):
        held = by_file.get(name)
        if held is None or not held:
            held = {data["files"][name]["tier"]}
        if held & tiers:
            out.append(name)
    return out


def selected_ids(data, root, tiers):
    """Module, class and method ids of the tests in ``tiers``, as ``parallel_suite.py --select`` reads them.

    A module id is emitted when the file entry and every unit are selected, a class id when the class's
    resolved tier and every unit of it are selected, and method ids otherwise.
    """
    tiers = set(tiers)
    ids = []
    for name in sorted(data["files"]):
        entry = data["files"][name]
        module = name[:-3] if name.endswith(".py") else name
        if data["kind"] == "file-glob":
            if entry["tier"] in tiers:
                ids.append(name)
            continue
        try:
            found = file_units(Path(root) / name)
        except (OSError, SyntaxError, ValueError):
            continue
        by_class = {}
        for cls, method in found:
            by_class.setdefault(cls, []).append(method)
        every = all(tier_of(entry, c, m) in tiers for c, ms in by_class.items() for m in ms)
        if entry["tier"] in tiers and every:
            ids.append(module)
            continue
        for cls, methods in by_class.items():
            chosen = [m for m in methods if tier_of(entry, cls, m) in tiers]
            if not chosen:
                continue
            if len(chosen) == len(methods) and tier_of(entry, cls) in tiers:
                ids.append(f"{module}.{cls}")
            else:
                ids += [f"{module}.{cls}.{m}" for m in chosen]
        if not by_class and entry["tier"] in tiers:
            ids.append(module)
    return ids
