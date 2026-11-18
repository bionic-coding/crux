#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""migrate-instructions.py — report or migrate repository instruction files.

The entry point for the canonical-AGENTS.md discovery and migration contract.
`audit-docs` reports through `--dry-run` in plain mode and applies through
`--migrate`; the logic lives in `instruction_migration.py`, shared by both.

`--operational-schema` runs the second migration this entry point owns: it brings
the tree's own `<docs_dir>/AGENTS.md` to the routing a fresh init writes. Unmodified
template sections are refreshed, or removed where their contract moved to a task
reference; sections the owner edited stay verbatim and are reported.

The repo root comes from `--repo-root`, defaulting to the working directory —
never from this file's own path, which names the plugin and never the project.

Exit codes: 0 clean, 1 findings or refusal with JSON on stdout, 2 capability
error with a message on stderr.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "instruction_migration", _HERE / "instruction_migration.py")
im = importlib.util.module_from_spec(_spec)
sys.modules["instruction_migration"] = im
_spec.loader.exec_module(im)


def _payload(root: Path, d, plan) -> dict:
    """The report every run prints, dry runs included."""
    left = {im._rel(sp.scope, sp.winner.name) for sp in plan.scopes
            if sp.winner is not None and sp.winner_left}
    excluded = {k: v for k, v in d.excluded.items() if k not in left}
    for sp in plan.scopes:
        excluded.update(sp.excluded)
    suppressors = []
    for s in d.suppressors:
        rel = s.path.as_posix()
        row = {"path": im.show(rel), "reason": s.reason, "on_chain": s.on_chain,
               "remedy": s.remedy}
        if rel in left:
            # A winner left in place is reported once, as a suppressor whose
            # content AGENTS.md carries, with no next step.
            row["reason"] = "winner left in place; AGENTS.md carries its content"
            row["remedy"] = ""
        suppressors.append(row)
    return {
        "repo_root": str(root),
        "managed": [im.show(p.as_posix()) for p in d.managed_paths()],
        "excluded": {im.show(k): v for k, v in sorted(excluded.items())},
        "suppressors": suppressors,
        "actions": [s.to_json() for s in plan.actions],
        "scopes": [sp.to_json() for sp in plan.scopes],
        "set_asides": [sa for sp in plan.scopes for sa in sp.set_asides],
        "refusals": plan.refusals,
        "temporaries": [t for sp in plan.scopes for t in sp.temporaries],
    }


def _tree_dir(root: Path) -> str:
    """The configured documentation tree, through the shared config resolver."""
    spec = importlib.util.spec_from_file_location("_bionic_config", _HERE / "bionic_config.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_bionic_config", mod)
    spec.loader.exec_module(mod)
    return mod.resolve_tree_name(root)


def operational_schema(root: Path, migrate: bool, today: str | None = None) -> int:
    """Bring `<docs_dir>/AGENTS.md` to the routing a fresh init writes.

    Exit 0: nothing to change (dry run) or written with no section left for the
    owner. Exit 1: changes pending (dry run), or owner-edited sections reported.
    Exit 2: no readable regular schema file, or the plugin template is missing.
    """
    import datetime

    plugin_root = _HERE.parent
    try:
        tree = _tree_dir(root)
        target = root / tree / "AGENTS.md"
        if target.is_symlink() or not target.is_file():
            print(f"{target}: not a regular file", file=sys.stderr)
            return 2
        old = target.read_bytes()
        template = (plugin_root / "templates" / "AGENTS.md.tmpl").read_text(encoding="utf-8")
        shipped = im.load_shipped_sections(plugin_root / "references" / im.SHIPPED_SECTIONS_NAME)
        moved = im.reference_section_keys(plugin_root)
        text, report = im.plan_schema_upgrade(
            old.decode("utf-8"), template, repo_name=root.name,
            today=today or datetime.date.today().isoformat(), shipped=shipped, moved=moved)
    except (im.CapabilityError, OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"cannot plan the operational-schema upgrade: {exc}", file=sys.stderr)
        return 2
    payload = {"schema": f"{tree}/AGENTS.md", **report}
    if migrate and report["changed"]:
        try:
            im.write_schema(target, old, text.encode("utf-8"))
        except (im.CapabilityError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        payload["applied"] = True
    print(json.dumps(payload, indent=2, sort_keys=True))
    if migrate:
        return 1 if report["preserved"] else 0
    return 1 if report["changed"] or report["preserved"] else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--working-dir", default=None,
                    help="the directory a host would load instructions from; "
                         "decides which suppressors bear on a verdict")
    ap.add_argument("--operational-schema", action="store_true",
                    help="upgrade <docs_dir>/AGENTS.md to the current template's routing "
                         "instead of migrating repository instruction files")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report only")
    mode.add_argument("--migrate", action="store_true", help="apply the plan")
    args = ap.parse_args(argv)

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"repo root is not a directory: {root}", file=sys.stderr)
        return 2
    if args.operational_schema:
        return operational_schema(root, args.migrate)

    try:
        d = im.discover(root, denylist=im.load_denylist(root),
                        working_dir=Path(args.working_dir) if args.working_dir else root)
        plan = im.build_plan(d)
    except im.CapabilityError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"cannot read the repository: {exc}", file=sys.stderr)
        return 2

    if args.migrate:
        try:
            receipt = im.apply_plan(plan, root)
        except im.RunStopped as exc:
            print(str(exc), file=sys.stderr)
            return 2
        payload = _payload(root, d, plan)
        payload["applied"] = True
        payload["receipt"] = receipt.to_json()
        payload["dispositions"] = receipt.dispositions
        payload["staging_note"] = receipt.staging_note
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if plan.findings() else 0

    payload = _payload(root, d, plan)
    clean = not plan.actions and not plan.findings()
    payload["clean"] = clean
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
