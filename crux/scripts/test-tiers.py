#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check, list and merge test-tier manifests (``test-tiers.json``).

Usage:
    test-tiers.py check [--repo-root DIR] [--expect-root ROOT]... [--require-release-units ROOT]...
                        [--discover auto|git|filesystem]
    test-tiers.py check --root ROOT                      # per-root rules only
    test-tiers.py check --root ROOT --shard PATH         # a partial manifest, no unlabelled rules
    test-tiers.py list --root ROOT --tier T [--tier T]... [--ids]
    test-tiers.py merge --root ROOT --shard PATH [--shard PATH]...

``check`` prints one JSON object: ``configured``, ``roots``, ``counts`` per tier, ``findings`` (each
``code``, ``path``, ``detail``), ``expired`` (ephemeral labels past their ``expires`` date; reported,
never failing) and ``counting`` (the unit-counting rule). Exit 0 clean, 1 findings, 2 environment
error (a missing or unreadable manifest or shard, bad usage). With no manifest and no ``--expect-root``
a project exits 0 with ``configured`` false; ``--expect-root`` makes that a ``missing-root`` finding.

``list`` first applies the per-root rules and exits 2 on a finding or a missing manifest. It prints
the test files that hold at least one test of a selected tier, one per line, or with ``--ids`` the
module, class and method ids a runner selects (``parallel_suite.py --select`` reads them).

``merge`` writes the union of the shards to ROOT/test-tiers.json. It refuses, writing nothing, a file
named by two shards, an area id with two descriptions, and a differing format, version, kind or
pattern. Name a shard ``<root-slug>.shard.json``, never ``test-tiers.json``.

The tool uses the standard library only and the reader ``test_tiers.py`` beside it, so it runs in the
staged plugin tree and in a project without the crux environment.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_tiers as tt  # noqa: E402


def _emit(payload):
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _env_error(message):
    sys.stderr.write(f"test-tiers: {message}\n")
    return 2


def _single_root_report(root, data, findings, today=None):
    counts = tt.counts_of(data, root) if isinstance(data, dict) and "files" in data and "kind" in data else {}
    return {"configured": True, "roots": {str(root): {"counts": counts}}, "counts": counts,
            "findings": findings, "expired": [], "counting": tt.COUNTING_RULE}


def cmd_check(args):
    if args.shard and not args.root:
        return _env_error("--shard needs --root")
    if args.root:
        root = Path(args.root)
        if not root.is_dir():
            return _env_error(f"the root {root} is not a directory")
        source = Path(args.shard) if args.shard else tt.manifest_path(root)
        try:
            data, duplicates = tt.read_json(source)
        except tt.ManifestError as exc:
            return _env_error(str(exc))
        findings = [tt.finding("duplicate-key", source, f"duplicate JSON key {key!r}") for key in duplicates]
        findings += tt.validate(data, root, shard=bool(args.shard), label=source)
        report = _single_root_report(root, data, findings)
        _emit(report)
        return 1 if findings else 0
    repo = Path(args.repo_root).resolve()
    if not repo.is_dir():
        return _env_error(f"the repository root {repo} is not a directory")
    try:
        roots, _ = tt.discover_manifests(repo, args.discover)
    except tt.ManifestError as exc:
        return _env_error(str(exc))
    report = tt.check_roots(repo, roots, expect=args.expect_root, require_release=args.require_release_units,
                            mode=args.discover)
    _emit(report)
    return 1 if report["findings"] else 0


def cmd_list(args):
    if not args.tier:
        return _env_error("list needs at least one --tier")
    for tier in args.tier:
        if tier not in tt.TIERS:
            return _env_error(f"tier {tier!r} is not one of {', '.join(tt.TIERS)}")
    try:
        data = tt.load(args.root)
    except tt.ManifestError as exc:
        return _env_error(str(exc))
    lines = tt.selected_ids(data, args.root, args.tier) if args.ids else tt.selected_files(data, args.root, args.tier)
    sys.stdout.write("".join(line + "\n" for line in lines))
    return 0


def cmd_merge(args):
    root = Path(args.root)
    if not root.is_dir():
        return _env_error(f"the root {root} is not a directory")
    shards = []
    for path in args.shard:
        try:
            data, duplicates = tt.read_json(path)
        except tt.ManifestError as exc:
            return _env_error(str(exc))
        problems = [tt.finding("duplicate-key", path, f"duplicate JSON key {key!r}") for key in duplicates]
        problems += tt.validate(data, root, shard=True, label=path)
        if problems:
            _emit({"merged": False, "findings": problems})
            return 1
        shards.append((str(path), data))
    findings = []
    head = shards[0][1]
    for key in ("format", "version", "kind", "pattern"):
        for path, data in shards[1:]:
            if data[key] != head[key]:
                findings.append(tt.finding("shard-mismatch", path, f"{key} differs from {shards[0][0]}"))
    areas, files = {}, {}
    owner = {}
    for path, data in shards:
        for area, description in data["areas"].items():
            if area in areas and areas[area] != description:
                findings.append(tt.finding("area-conflict", path, f"area {area!r} has a different description"))
            areas.setdefault(area, description)
        for name, entry in data["files"].items():
            if name in files:
                findings.append(tt.finding("doubly-labelled", path, f"{name} is also named by {owner[name]}"))
                continue
            files[name] = entry
            owner[name] = path
    if findings:
        _emit({"merged": False, "findings": findings})
        return 1
    merged = {"format": head["format"], "version": head["version"], "kind": head["kind"],
              "pattern": head["pattern"], "areas": dict(sorted(areas.items())), "files": dict(sorted(files.items()))}
    target = tt.manifest_path(root)
    target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    after = tt.validate(merged, root)
    _emit({"merged": True, "path": str(target), "files": len(files), "findings": after})
    return 1 if after else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="test-tiers.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="check manifests and print a JSON report")
    check.add_argument("--repo-root", default=".", help="the project root (default: the working directory)")
    check.add_argument("--root", help="check this one test root (per-root rules only)")
    check.add_argument("--shard", help="check this partial manifest against --root (no unlabelled rules)")
    check.add_argument("--expect-root", action="append", default=[], metavar="ROOT",
                       help="a root, relative to --repo-root, that must hold a tracked manifest; repeatable")
    check.add_argument("--require-release-units", action="append", default=[], metavar="ROOT",
                       help="a root that must hold at least one release unit; repeatable")
    check.add_argument("--discover", choices=("auto", "git", "filesystem"), default="auto",
                       help="how to find manifests: git-tracked files, a filesystem walk, or git when the "
                            "root is a work tree top (default auto)")
    listing = sub.add_parser("list", help="print the files or ids of the selected tiers")
    listing.add_argument("--root", required=True)
    listing.add_argument("--tier", action="append", default=[], metavar="TIER")
    listing.add_argument("--ids", action="store_true")
    merge = sub.add_parser("merge", help="write the union of shards to ROOT/test-tiers.json")
    merge.add_argument("--root", required=True)
    merge.add_argument("--shard", action="append", required=True, metavar="PATH")
    args = parser.parse_args(argv)
    return {"check": cmd_check, "list": cmd_list, "merge": cmd_merge}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
