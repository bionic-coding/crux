#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Install the shipped standalone guide and an explicit root AGENTS.md instruction.

Requires an existing supported Crux documentation tree. No initialization,
network schema lookup, or guide rendering occurs. Exit 0 means installed,
unchanged, or a successful dry run; 1 means a preserved conflict; 2 means an
environment error. Interrupted writes retain intent for a subsequent invocation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from micro_crux import InstallConflict, install


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="target project; defaults to cwd")
    parser.add_argument("--dry-run", action="store_true", help="inspect the complete update without writing")
    args = parser.parse_args(argv)
    try:
        result = install(args.repo_root, Path(__file__).resolve().parent.parent, dry_run=args.dry_run)
    except InstallConflict as exc:
        print(json.dumps({"changed": False, "error": str(exc), "differences": exc.differences}, sort_keys=True))
        return 1
    except OSError as exc:
        print(f"micro-crux installation: {exc}. Preserve any pending installation metadata and rerun after resolving the error.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
