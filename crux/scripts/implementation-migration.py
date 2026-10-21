# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml==6.0.3", "httpx>=0.27,<1"]
# ///
"""Inventory source-bound implementation clause migrations.

`dry-run` and `apply` are retired: each refuses with `historical-migration-writes-retired`
and changes nothing. Existing historical publications are still verified by every authority
reader. Propose new clause migrations in the prospective format through migrate-adrs.
"""
from __future__ import annotations

import argparse
import json
import sys

import bionic_config
import implementation_migration as migration


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "dry-run", "apply"),
                        help="inventory reports; dry-run and apply are retired and refuse")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    try:
        if args.command == "apply":
            import implementation_migration_apply as application
            application.apply(args.repo_root, args.batch)
        elif args.command == "dry-run":
            migration.dry_run(args.repo_root, args.batch)
        else:
            print(json.dumps(migration.inventory(args.repo_root, args.batch), sort_keys=True))
            return 0
        raise AssertionError("a retired command returned")
    except migration.Refused as exc:
        print(json.dumps({"authority": "none", "limit": exc.code}))
        _remedy(exc)
        return 1
    except (bionic_config.BionicConfigError, OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"authority": "none", "limit": "migration-inventory-unavailable"}), file=sys.stderr)
        return 2


def _remedy(exc):
    """Print a refusal's next step on stderr. Stdout keeps its one-line contract."""
    remedy = getattr(exc, "remedy", None)
    if remedy:
        print(json.dumps({"remedy": remedy}), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
