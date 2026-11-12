#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""generate-log-summary.py — the regenerator and drift gate for `<docs_dir>/log/summary.md`.

`summary.md` summarises each settled month of the operations log. A month M is settled on a
host from the third day of month M+1 in that host's local date. The file holds a header, a
rollup region and one section per settled month, newest first. Each section is a `## YYYY-MM`
heading and a GENERATED region that states the detail file's path and sha256, the entry count,
the first and last heading dates, the count of each op, and the ADR ids that `adr` entries
name. Every rendered token comes from a closed grammar, so no subject text reaches the file.
Text after a month's END marker and before the next month heading is that month's narrative,
which the historian writes on request; this script keeps it byte for byte. The logic lives in
`operation_log.py` (`summarize`); this file is the command-line driver.

MODES.
  write mode (no flag)  The catch-up. It creates `summary.md` when the first settled month
                        with a detail file appears, adds a section for each settled month that
                        has none, rewrites each settled month's region that differs from its
                        derivation, and regenerates the rollup. It never writes a section or a
                        region for a month that is not settled. It refuses and writes nothing
                        on a document finding, a structure failure, an incomplete first split,
                        or a legacy `log.md` with no completion record.
  --dry-run             The summary gate. It writes nothing. It exits 1 on a region failure (a
                        region or the rollup that differs from its derivation; the catch-up
                        repairs it) or a structure failure (a section for the current or a
                        later month, a second section for one month, a section without a detail
                        file, a missing, duplicated or misordered marker, or an incomplete
                        split; the remedy is a hand edit of `summary.md` or
                        `operation-log.py repair`). Each failure carries its `kind`. A settled
                        month with a detail file and no section is listed under
                        `pending_months` and exits 0 when it is the only finding;
                        `cleanup-campsite` runs the catch-up.

The gate never reads the detail file of the month holding the checking host's local date, so
its exit code on a tree that `operation-log.py check` finds clean does not change with the date
alone: settling a month adds pending work, not a failure.

`--today YYYY-MM-DD` replaces the host's local date. Write mode accepts it only while
`CRUX_OPERATION_LOG_TEST=1`, which the tests set; `--dry-run` accepts it always.

LANES. A tree with no `<docs_dir>/log/` (ENOENT or ENOTDIR) holds no detail file: both modes
exit 0 with `surface_absent: true`, no sections and no pending months, and write nothing, except
that write mode refuses on an unsplit legacy `log.md`. A detail file or `summary.md` that cannot
be read for a cause at its path, that is a symlink or not a regular file, that is not UTF-8, or
a read detail file whose heading fails the section 6 historical-reader regex or carries a date
that is not a real calendar date, is a document finding: exit 1, `validation_errors`, nothing
written. A `log/` that exists and cannot be listed or is not a directory, and any other read
failure, is an environment failure: exit 2, nothing on stdout, a message on stderr.

COMMITS. The write-mode result names `status` (`written`, `unchanged` or `refused`), the months
it added and rewritten, and no commit paths. A caller commits `summary.md` by name only when the
status is `written`, beside the `commit_paths` and `restore_paths` of its last
`operation-log.py` run (repair or append), which list the log's other paths; this script's
result never supplies those lists.

Exit codes: 0 clean, pending only, written or unchanged; 1 drift, a refusal or a document
finding (JSON on stdout); 2 environment.

Stdlib plus the sibling modules `operation_log`, `input_lanes` and `bionic_config`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bionic_config import BionicConfigError, load_config  # noqa: E402
import input_lanes  # noqa: E402
import operation_log as ol  # noqa: E402

SCRIPT = "generate-log-summary"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=".", help="the repository whose tree is summarised")
    parser.add_argument("--dry-run", action="store_true", help="the summary gate: compare and write nothing")
    parser.add_argument("--today", help=f"replace the local date (write mode only while {ol.TEST_ENV}=1)")
    args = parser.parse_args(argv)
    try:
        root = Path(args.repo_root).resolve()
        tree = load_config(root, require_tree=True).docs_root
    except (BionicConfigError, OSError) as exc:
        print(f"{SCRIPT}: {exc}", file=sys.stderr)
        return 2
    try:
        today = ol.resolve_today(args.today, write=not args.dry_run)
    except ol.Refusal as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "error": str(exc),
                          "validation_errors": [{"file": "--today", "error": str(exc)}]}, sort_keys=True))
        return 1
    try:
        code, payload = ol.summarize(tree, root, today, write=not args.dry_run)
    except input_lanes.EnvironmentLaneError as exc:
        return input_lanes.emit_environment_failure(exc, SCRIPT, sys.stderr)
    except ol.Refusal as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "error": str(exc)}, sort_keys=True))
        return 1
    except OSError as exc:
        print(f"{SCRIPT}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
