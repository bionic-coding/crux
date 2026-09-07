# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""generate-index-rollup.py — the vendored regenerator for the `## ADRs` rollup
section of docs/index.md.

The second conformance instance of ADR-0056 ("every derived artifact — or the
derived *region* of a file — must have a vendored regenerator AND a drift
gate"), and the mechanical implementation of `audit-docs` CHK-MI-2 for the ADR
concern specifically.

Why this exists (PB-0052 finding 4): the rollup read `## ADRs (54)` with 54 rows
against 58 ADR files, and an `audit-docs` pass on the same day reported index
counts clean. CHK-MI-2's prose is correct and sufficient; what failed is that a
prose rule's execution is a judgment call inside a long walk, with no way to
distinguish a skipped check from a passed one. This script makes that one rule
mechanical.

SCOPE — deliberately narrow. This regenerates ONLY the `## ADRs (N)` section of
docs/index.md. Every other byte of the file (the other concern rollups, the
header, the What's next section) is preserved verbatim. The remaining concern
rollups stay under prose CHK-MI-2 and are ADR-0056's already-anticipated
follow-on sweep ("in-scope-but-not-yet-audited — flagged for a follow-on sweep,
not fixed here").

Modes (shared crux exit-code convention):
  (no flag)   rewrite the `## ADRs` section of docs/index.md; exit 0.
  --dry-run   the DRIFT GATE: compare the on-disk section to a freshly generated
              one; exit 0 if byte-identical, exit 1 + unified diff on drift.
              (exit 2 = capability error, e.g. PyYAML missing.)

Deterministic + byte-stable: rows in DESCENDING ADR id order (newest first,
matching the established docs/index.md convention). No timestamps in the body.

DELIBERATELY NOT UPDATED: the file's `_Last updated: YYYY-MM-DD` line. docs/
CLAUDE.md §5 asks authors to bump it on every change, but a regenerator that
stamped today's date would not be byte-stable — the `--dry-run` gate would then
fail on every day after the last regeneration, for no drift. That is ADR-0056's
"regenerated-but-time-varying" trap. Keeping the timestamp out of this script's
scope is what lets the gate be a hard tier. Bumping `_Last updated:` stays an
authoring/audit-docs concern. Do not "fix" this.
"""
from __future__ import annotations

import argparse
import difflib
import glob
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "generate-index-rollup.py requires PyYAML — run via `uv run` (PEP 723 supplies it).\n"
    )
    raise SystemExit(2)

# The section this script owns. Matched on the heading; terminated by the next
# top-level heading (or EOF).
SECTION_RE = re.compile(r"^## ADRs \(\d+\)\n.*?(?=^## |\Z)", re.M | re.S)


def _tree_name(root) -> str:
    """Resolve the tree directory via bionic_config, falling back to the default."""
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


def load_adrs(adrs_dir: Path) -> list[dict]:
    """Read every ADR-NNNN-*.md frontmatter. The filename stem is the wiki-link
    target (docs/CLAUDE.md §9 cites ADRs by page name, not by id alone)."""
    recs: list[dict] = []
    # Walk BOTH tiers (active + cold archive), per ADR-0063: an archived ADR stays
    # in the master rollup and lineage; only the active-index reading path shrinks.
    both = glob.glob(str(adrs_dir / "ADR-*.md")) + glob.glob(str(adrs_dir / "archive" / "ADR-*.md"))
    for p in sorted(both):
        path = Path(p)
        m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
        if not m:
            continue
        fm = yaml.safe_load(m.group(1)) or {}
        recs.append(
            {
                "num": int(str(fm["id"]).split("-")[-1]),
                "stem": path.stem,
                "title": str(fm["title"]),
                "status": str(fm["status"]),
                "date": str(fm["date"]),
            }
        )
    recs.sort(key=lambda r: r["num"], reverse=True)
    return recs


def render_section(recs: list[dict]) -> str:
    lines = [f"## ADRs ({len(recs)})", "", "| id | title | status | date |", "|---|---|---|---|"]
    for r in recs:
        lines.append(f"| [[adrs/{r['stem']}]] | {r['title']} | {r['status']} | {r['date']} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Regenerate the ## ADRs rollup section of docs/index.md from ADR frontmatter."
    )
    ap.add_argument("--repo-root", default=".", help="repo root (default: cwd)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="drift gate: exit 1 + diff if the on-disk section differs",
    )
    args = ap.parse_args(argv)

    root = Path(args.repo_root)
    index = root / _tree_name(root) / "index.md"
    adrs_dir = root / _tree_name(root) / "adrs"
    if not index.is_file():
        sys.stderr.write(f"generate-index-rollup.py: {index} not found\n")
        return 2
    if not adrs_dir.is_dir():
        sys.stderr.write(f"generate-index-rollup.py: {adrs_dir} not found\n")
        return 2

    current = index.read_text(encoding="utf-8")
    m = SECTION_RE.search(current)
    if not m:
        sys.stderr.write("generate-index-rollup.py: no '## ADRs (N)' section found in docs/index.md\n")
        return 2

    want = render_section(load_adrs(adrs_dir))
    have = m.group(0)

    if args.dry_run:
        if have == want:
            return 0
        sys.stdout.writelines(
            difflib.unified_diff(
                have.splitlines(keepends=True),
                want.splitlines(keepends=True),
                fromfile="docs/index.md (on disk)",
                tofile="docs/index.md (regenerated)",
            )
        )
        return 1

    if have != want:
        index.write_text(current[: m.start()] + want + current[m.end():], encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
