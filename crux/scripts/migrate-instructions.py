#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""migrate-instructions.py — report or migrate repository instruction files.

The entry point for the canonical-AGENTS.md discovery and migration contract.
`audit-docs` reports through `--dry-run` in plain mode and applies through
`--migrate`; the logic lives in `instruction_migration.py`, shared by both.

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--working-dir", default=None,
                    help="the directory a host would load instructions from; "
                         "decides which suppressors bear on a verdict")
    ap.add_argument("--resolution", default=None,
                    help="reviewed JSON resolution bound to the preview receipt")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report only")
    mode.add_argument("--migrate", action="store_true", help="apply the plan")
    args = ap.parse_args(argv)

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"repo root is not a directory: {root}", file=sys.stderr)
        return 2

    try:
        d = im.discover(root, denylist=im.load_denylist(root),
                        working_dir=Path(args.working_dir) if args.working_dir else root)
    except im.CapabilityError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    resolution_errors: list[str] = []
    resolutions = None
    if args.resolution:
        try:
            resolutions = im.load_reviewed_resolutions(
                Path(args.resolution), root, d)
        except im.PlanInvalid as exc:
            resolution_errors.append(str(exc))
    plan = im.build_plan(d, resolutions=resolutions)
    plan.errors.extend(resolution_errors)

    payload = {
        "repo_root": str(root),
        "managed": [p.as_posix() for p in d.managed_paths()],
        "excluded": d.excluded,
        "suppressors": [
            {"path": s.path.as_posix(), "reason": s.reason,
             "on_chain": s.on_chain, "remedy": s.remedy}
            for s in d.suppressors
        ],
        "actions": [
            {"kind": a.kind, "scope": a.scope.as_posix(),
             "sources": [s.as_posix() for s in a.sources],
             "dest": a.dest.as_posix(), "blocked": a.blocked, "reason": a.reason}
            for a in plan.actions
        ],
        "validation_errors": plan.errors,
    }

    if args.migrate:
        if not plan.valid:
            payload["applied"] = False
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 1
        receipt = im.apply_plan(plan, root)
        payload["applied"] = True
        payload["dispositions"] = receipt.dispositions
        payload["unresolved"] = receipt.unresolved
        payload["merge_rows"] = receipt.merge_rows
        payload["staging_note"] = receipt.staging_note
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if receipt.has_unresolved() else 0

    clean = not plan.actions and not plan.errors
    payload["clean"] = clean
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
