#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6.0"]
# ///
"""adr-precouncil.py -- advisory pre-council helpers for a draft ADR.

Read-only. Writes nothing, blocks nothing, never refuses a council.

Subcommand `rules --repo-root R --adr PATH`:
  Lists the live rules a draft must reconcile: every rule of each ADR it
  amends or supersedes, plus every rule in each domain its `governs` entries
  name, minus the draft's own handles. Emits a reconciliation table skeleton
  for the Consequences section, and an advisory when the draft amends plus
  supersedes more than three ADRs. `--json` emits the same data as JSON.

The rules come from `<docs_dir>/adrs/summaries/resolver.json` (rule text, source
ADR) and `rule-table.md` (domain per handle), resolved through the configured
docs_dir.

Subcommand `challenge`:
  Prints the shared challenge instruction, the council operating assumptions and
  the one-round findings sentence: the brief for one fresh-agent challenge.

Exit: 0 report produced (advisory or not) · 1 malformed draft frontmatter ·
      2 environment error (missing tree, resolver or rule table), message on stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adr_frontmatter as af
import summaries_projection as sp

SPLIT_LIMIT = 3


class Malformed(Exception):
    pass


class Environment(Exception):
    pass


def read_draft(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Malformed(f"cannot read draft {path}: {exc}")
    block = af.frontmatter_block(text)
    if block is None:
        raise Malformed(f"{path}: no parseable frontmatter fence")
    import yaml
    try:
        fm = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise Malformed(f"{path}: malformed frontmatter: {exc}")
    if not isinstance(fm, dict) or not fm.get("id"):
        raise Malformed(f"{path}: frontmatter is not a mapping with an id")
    return fm


def id_list(fm: dict, key: str) -> list[str]:
    value = fm.get(key) or []
    if not isinstance(value, list):
        raise Malformed(f"frontmatter `{key}` is not a list")
    return [str(v) for v in value]


def load_rules(root: Path) -> tuple[dict, dict]:
    try:
        summaries = sp.adrs_dir(root) / "summaries"
    except Exception as exc:
        raise Environment(f"cannot resolve the docs tree: {exc}")
    resolver_path = summaries / "resolver.json"
    table_path = summaries / "rule-table.md"
    for p, what in ((resolver_path, "resolver"), (table_path, "rule table")):
        if not p.is_file():
            raise Environment(f"missing summaries {what}: {p}")
    try:
        resolver = json.loads(resolver_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise Environment(f"unreadable resolver {resolver_path}: {exc}")
    domains = {}
    for line in table_path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and "/" in cells[0] and not cells[0].startswith(("-", "handle")):
            domains[cells[0]] = cells[1]
    return resolver, domains


def collect(fm: dict, resolver: dict, domains: dict) -> list[dict]:
    own = str(fm["id"])
    own_handles = {str(g.get("handle")) for g in (fm.get("governs") or [])
                   if isinstance(g, dict)}
    targets = set(id_list(fm, "amends")) | set(id_list(fm, "supersedes"))
    wanted = {str(g.get("domain")) for g in (fm.get("governs") or [])
              if isinstance(g, dict) and g.get("domain")}
    rows = []
    for handle in sorted(resolver):
        row = resolver[handle]
        if not isinstance(row, dict) or "rule" not in row:
            continue
        if handle in own_handles or handle.split("/")[0] == own:
            continue
        if row.get("source_status", "Accepted") != "Accepted":
            continue
        why = []
        if row.get("source_adr") in targets:
            why.append(f"rule of {row['source_adr']}")
        if domains.get(handle) in wanted:
            why.append(f"domain {domains[handle]}")
        if why:
            rows.append({"handle": handle, "rule": row["rule"], "why": "; ".join(why)})
    return rows


def render(fm: dict, rows: list[dict], advisory: str | None) -> str:
    out = [f"# Pre-council rules for {fm['id']}", ""]
    if advisory:
        out += [f"Advisory: {advisory}", ""]
    if not rows:
        out.append("No live rules to reconcile.")
        return "\n".join(out) + "\n"
    out += ["Paste into the Consequences section; set each disposition.", "",
            "| handle | rule | disposition (retain/narrow/retire) | retires |",
            "|---|---|---|---|"]
    for r in rows:
        text = r["rule"].replace("|", "\\|").replace("\n", " ")
        out.append(f"| {r['handle']} | {text} |  |  |")
    return "\n".join(out) + "\n"


def cmd_rules(args) -> int:
    root = Path(args.repo_root).resolve()
    try:
        fm = read_draft(Path(args.adr))
        count = len(id_list(fm, "amends")) + len(id_list(fm, "supersedes"))
        resolver, domains = load_rules(root)
    except Malformed as exc:
        sys.stderr.write(f"adr-precouncil: malformed draft frontmatter: {exc}\n")
        return 1
    except Environment as exc:
        sys.stderr.write(f"adr-precouncil: {exc}\n")
        return 2
    rows = collect(fm, resolver, domains)
    advisory = None
    if count > SPLIT_LIMIT:
        advisory = (f"this draft amends plus supersedes {count}, more than three ADRs: "
                    "split it, narrow it, or declare in one line why it stays whole.")
    if args.json:
        print(json.dumps({"adr": fm["id"], "advisory": advisory, "rules": rows}, indent=2))
    else:
        sys.stdout.write(render(fm, rows, advisory))
    return 0


def cmd_challenge(args) -> int:
    import council_assumptions as ca
    print("\n".join((ca.LITE_CHALLENGE_INSTRUCTION.rstrip("\n"),
                     ca.COUNCIL_OPERATING_ASSUMPTIONS, ca.ONE_ROUND_FINDINGS)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Advisory pre-council helpers for a draft ADR.")
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("rules", help="list live rules the draft must reconcile")
    r.add_argument("--repo-root", default=".")
    r.add_argument("--adr", required=True, help="path to the draft ADR")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_rules)
    c = sub.add_parser("challenge", help="print the brief for a fresh-agent challenge")
    c.set_defaults(func=cmd_challenge)
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        sys.stderr.write(f"adr-precouncil: {type(exc).__name__}: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
