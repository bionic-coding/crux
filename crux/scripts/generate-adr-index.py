#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""generate-adr-index.py — the vendored regenerator for <docs_dir>/adrs/index.md.

Per ADR-0063 (SP-4): the ADR index becomes a *derived* artifact walking BOTH tiers.
The active table lists active ADRs (Proposed/Accepted) from `adrs/`; the collapsed
`## Archived (N)` roster lists Superseded/Deprecated ADRs from `adrs/archive/`,
ordered by id descending. Byte-stable (no date) so a crash-stale index is drift the
gate catches, not a special repair case (ADR-0063 Decision 4). Enrolled in the
regenerative-outputs roster.

Usage:
  generate-adr-index.py [--repo-root DIR]        rewrite adrs/index.md
  generate-adr-index.py --dry-run [...]          exit 1 + JSON diff if drift

Exit: 0 clean/written · 1 drift or findings (JSON on stdout) · 2 env error.

INPUT LANES. The adrs directory is absent only when its `stat` fails with
ENOENT or ENOTDIR;[^absence] that keeps exit 2 "not found". A path there that
exists and is not a directory, or whose existence cannot be determined, is the
environment lane: exit 2, nothing on stdout, the real reason on
stderr.[^unlistable] An ADR unreadable for a cause at its path is a
`validation_errors` finding (exit 1);[^file] a cause in the process or host is
the environment lane, and its stderr names every finding the run
met.[^process][^precedence]

THE OUTPUT READ. `--dry-run` reads adrs/index.md to compare it, and only after
every input read clean, so a run that refuses on its inputs never reads it. A
confirmed-absent output reads as empty. A failure to read it for a cause at its
path is a `validation_errors` finding naming it by its repository-relative
path; any other cause is the environment lane naming it. Write mode never
reads the output, because it overwrites it, so it replaces a corrupt one.
Every refusal leaves every output byte-unchanged and creates none.

[^file]: rule:path-attributable-read-failure-is-a-document-finding
[^process]: rule:process-level-read-failure-is-an-environment-failure
[^absence]: rule:absence-is-confirmed-by-enoent-or-enotdir
[^unlistable]: rule:unlistable-input-directory-is-an-environment-failure
[^precedence]: rule:environment-failure-takes-precedence
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adr_frontmatter  # noqa: E402
import input_lanes  # noqa: E402


def _tree_name(root) -> str:
    """Resolve the tree directory via bionic_config, the resolver the rollup and lineage use.

    It raises on a configuration it cannot resolve; `main` maps that to exit 2.
    """
    _PATH = Path(__file__).resolve().parent / "bionic_config.py"
    import importlib.util as _ilu
    import sys as _sys
    _key = "_bionic_config"
    _m = _sys.modules.get(_key)
    if _m is None:
        _s = _ilu.spec_from_file_location(_key, _PATH)
        _m = _ilu.module_from_spec(_s)
        _s.loader.exec_module(_m)
        _sys.modules[_key] = _m   # cache so class identity holds across calls
    return _m.resolve_tree_name(root)


def _load(paths, texts: dict[Path, str]) -> list[dict]:
    recs = []
    for p in sorted(paths):
        path = Path(p)
        # The fence is read through the ONE shared reader. `validated_adr_texts`
        # already refused this run if any input failed it, so `None` here is
        # unreachable — and it raises rather than skipping, because a second
        # copy of the fence test with a bare `continue` is the paired construct
        # this change exists to remove.
        block = adr_frontmatter.frontmatter_block(texts[path])
        if block is None:
            raise adr_frontmatter.FenceValidationError(
                [{"file": str(path), "error": adr_frontmatter.FENCE_ERROR}])
        import yaml
        fm = yaml.safe_load(block) or {}
        recs.append({
            "num": int(str(fm["id"]).split("-")[-1]),
            "id": str(fm["id"]),
            "title": str(fm["title"]),
            "status": str(fm["status"]),
            "date": str(fm["date"]),
            "supersedes": fm.get("supersedes") or [],
            "amends": fm.get("amends") or [],
            "superseded_by": fm.get("superseded_by"),
            "tags": fm.get("tags") or [],
        })
    recs.sort(key=lambda r: r["num"], reverse=True)
    return recs


def _sup(r: dict) -> str:
    base = ", ".join(r["supersedes"]) if r["supersedes"] else "—"
    if r["amends"]:
        base += f" (amends {', '.join(r['amends'])})"
    return base


def _tags(r: dict) -> str:
    t = r["tags"]
    if isinstance(t, str):
        return t
    return ", ".join(t) if t else "—"


def render(active: list[dict], archived: list[dict]) -> str:
    out = ["# ADRs", "",
           "| id | title | status | date | supersedes | superseded_by | tags |",
           "|----|-------|--------|------|------------|---------------|------|"]
    for r in active:
        out.append(f"| {r['id']} | {r['title']} | {r['status']} | {r['date']} | "
                   f"{_sup(r)} | {r['superseded_by'] or '—'} | {_tags(r)} |")
    out += ["", f"## Archived ({len(archived)})", "", "| id | title | status |", "|----|-------|--------|"]
    for r in archived:
        out.append(f"| {r['id']} | {r['title']} | {r['status']} |")
    return "\n".join(out) + "\n"


def build(root: Path) -> tuple[Path, str]:
    adrs = root / _tree_name(root) / "adrs"
    rel_of = adr_frontmatter.repo_relative(root)
    try:
        present = input_lanes.directory_exists(adrs)
    except OSError as exc:
        # Exists and is not a directory, or its existence cannot be
        # determined: the unlistable-directory case, never "not found".[^unlistable]
        raise input_lanes.EnvironmentLaneError(
            [input_lanes.environment_reason(rel_of(adrs), exc)]) from exc
    if not present:
        raise FileNotFoundError(f"{adrs} not found")
    # REFUSAL BEFORE WRITING. Both tiers are read once and validated here,
    # before the caller reads the existing index to diff against or opens it to
    # write, so one unreadable ADR cannot shorten the index and cannot create
    # one that did not exist. Raises FenceValidationError, which `main` maps to
    # exit 1, for an unparseable fence or a file unreadable for a cause at its
    # path; raises EnvironmentLaneError or OSError, which `main` maps to exit 2,
    # for a process-level read failure or a tier it cannot list.
    texts = adr_frontmatter.validated_adr_texts(adrs, rel_of)
    active = _load([p for p in texts if p.parent == adrs], texts)
    archived = _load([p for p in texts if p.parent == adrs / "archive"], texts)
    return adrs / "index.md", render(active, archived)


def read_output(path: Path) -> str:
    """The wholly generated output's text, or "" when its absence is confirmed.

    Every other failure raises for the caller to classify by lane.[^absence]
    """
    if input_lanes.path_state(path) is None:
        return ""
    return path.read_text(encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate adrs/index.md from both ADR tiers.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        path, want = build(root)
    except adr_frontmatter.FenceValidationError as exc:
        return adr_frontmatter.print_validation_errors(
            exc.errors, "generate-adr-index", sys.stdout, sys.stderr)
    except input_lanes.EnvironmentLaneError as exc:
        return input_lanes.emit_environment_failure(exc, "generate-adr-index", sys.stderr)
    except Exception as exc:
        sys.stderr.write(f"generate-adr-index: {type(exc).__name__}: {exc}\n")
        return 2
    rel = str(path.relative_to(root))
    if args.dry_run:
        # The output is read only here, after every input read clean.
        try:
            have = read_output(path)
        except (OSError, UnicodeDecodeError, MemoryError) as exc:
            if input_lanes.is_path_attributable(exc):
                return adr_frontmatter.print_validation_errors(
                    [{"file": rel, "error": input_lanes.output_reason(exc)}],
                    "generate-adr-index", sys.stdout, sys.stderr)
            return input_lanes.emit_environment_failure(
                input_lanes.EnvironmentLaneError([input_lanes.environment_reason(rel, exc)]),
                "generate-adr-index", sys.stderr)
        drift = have != want
        print(json.dumps({"drift": drift, "path": rel}, sort_keys=True))
        return 1 if drift else 0
    try:
        path.write_text(want, encoding="utf-8")
    except OSError as exc:
        # A failed write is no input finding: exit 2 on stderr, never a traceback.
        sys.stderr.write(f"generate-adr-index: could not write {rel}: {type(exc).__name__}: {exc}\n")
        return 2
    print(json.dumps({"written": rel}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
