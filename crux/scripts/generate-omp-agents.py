#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Generate OMP agents into an explicitly selected output directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omp_agents import SpecViolation, diff, generate, write


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="report drift without writing")
    args = parser.parse_args(argv)

    try:
        generated = generate()
        added, changed, removed = diff(args.output_dir, generated)
        if args.dry_run:
            report = {"added": added, "changed": changed, "removed": removed}
            print(json.dumps(report, indent=2))
            return 1 if any(report.values()) else 0
        written, removed = write(args.output_dir, generated)
    except SpecViolation as exc:
        print(f"generate-omp-agents: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"written": written, "removed": removed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
