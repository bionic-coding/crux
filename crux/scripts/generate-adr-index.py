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

Exit: 0 clean/written · 1 drift (JSON on stdout) · 2 env error.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path


def _tree_name(root: Path) -> str:
    cfg = root / ".bionic.yml"
    if cfg.exists():
        m = re.search(r"^docs_dir\s*:\s*[\"']?([^\"'\s#]+)", cfg.read_text(encoding="utf-8"),
                      re.MULTILINE)
        if m:
            return m.group(1)
    return "bionic"


def _load(paths) -> list[dict]:
    recs = []
    for p in sorted(paths):
        path = Path(p)
        m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
        if not m:
            continue
        import yaml
        fm = yaml.safe_load(m.group(1)) or {}
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
    if not adrs.is_dir():
        raise FileNotFoundError(f"{adrs} not found")
    active = _load(glob.glob(str(adrs / "ADR-*.md")))
    archived = _load(glob.glob(str(adrs / "archive" / "ADR-*.md")))
    return adrs / "index.md", render(active, archived)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate adrs/index.md from both ADR tiers.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        path, want = build(root)
    except Exception as exc:
        sys.stderr.write(f"generate-adr-index: {type(exc).__name__}: {exc}\n")
        return 2
    have = path.read_text(encoding="utf-8") if path.exists() else ""
    if args.dry_run:
        drift = have != want
        print(json.dumps({"drift": drift, "path": str(path.relative_to(root))}, sort_keys=True))
        return 1 if drift else 0
    path.write_text(want, encoding="utf-8")
    print(json.dumps({"written": str(path.relative_to(root))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
