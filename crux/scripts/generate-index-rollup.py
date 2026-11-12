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
AGENTS.md §5 asks authors to bump it on every change, but a regenerator that
stamped today's date would not be byte-stable — the `--dry-run` gate would then
fail on every day after the last regeneration, for no drift. That is ADR-0056's
"regenerated-but-time-varying" trap. Keeping the timestamp out of this script's
scope is what lets the gate be a hard tier. Bumping `_Last updated:` stays an
authoring/audit-docs concern. Do not "fix" this.

INPUT LANES. docs/index.md is a required input named by path, because the
regenerated region sits inside hand-authored bytes. Its confirmed absence, a
failure to read it for a cause at its path, and a missing `## ADRs (N)`
section are each a `validation_errors` finding naming it (exit 1).[^file] A
read failure for a cause in the process or host is the environment lane
(exit 2, nothing on stdout).[^process] The adrs directory is absent only when
its `stat` fails with ENOENT or ENOTDIR;[^absence] that keeps exit 2 "not
found". A path there that exists and cannot be listed is the environment
lane.[^unlistable] Every input is tried before the run exits, and a run that
takes exit 2 names every finding it met on stderr.[^precedence] Every refusal
leaves every output byte-unchanged and creates none.

[^file]: rule:path-attributable-read-failure-is-a-document-finding
[^process]: rule:process-level-read-failure-is-an-environment-failure
[^absence]: rule:absence-is-confirmed-by-enoent-or-enotdir
[^unlistable]: rule:unlistable-input-directory-is-an-environment-failure
[^precedence]: rule:environment-failure-takes-precedence
"""
from __future__ import annotations

import argparse
import difflib
import json
import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adr_frontmatter  # noqa: E402
import input_lanes  # noqa: E402

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

#: The finding for a host file that carries no section for the rollup to own.
MISSING_SECTION = ("has no '## ADRs (N)' section — add the heading, for example "
                   "'## ADRs (0)', where the rollup belongs")


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


def load_adrs(adrs_dir: Path, rel=None) -> list[dict]:
    """Read every ADR-NNNN-*.md frontmatter. The filename stem is the wiki-link
    target (docs/AGENTS.md §9 cites ADRs by page name, not by id alone)."""
    recs: list[dict] = []
    # REFUSAL BEFORE WRITING: every file matching the glob, in both tiers, is
    # read once and validated before a single record is built. `rel` renders
    # the reported path; it defaults to `str` so existing callers keep their
    # signature. Walk BOTH tiers (active + cold archive), per ADR-0063: an
    # archived ADR stays in the master rollup and lineage; only the
    # active-index reading path shrinks.
    texts = adr_frontmatter.validated_adr_texts(adrs_dir, rel or str)
    for path in sorted(texts):
        # The fence is read through the ONE shared reader. `validated_adr_texts`
        # already refused this run if any input failed it, so `None` here is
        # unreachable — and it raises rather than skipping, because a second
        # copy of the fence test with a bare `continue` is the paired construct
        # this change exists to remove.
        block = adr_frontmatter.frontmatter_block(texts[path])
        if block is None:
            raise adr_frontmatter.FenceValidationError(
                [{"file": str(path), "error": adr_frontmatter.FENCE_ERROR}])
        fm = yaml.safe_load(block) or {}
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


def _read_index(index: Path, rel_of, findings: list[dict], failures: list[str]):
    """Read the host file `<docs_dir>/index.md`, a required input named by path.

    Returns `(text, section_match)`, or `(None, None)` after appending the
    run's finding or failure. The regenerated `## ADRs` region sits inside
    hand-authored bytes, so the rollup cannot produce its output without
    them, and every failure to read them is repaired at that path.[^file]
    A cause in the process or host takes the environment lane.[^process]
    """
    try:
        state = input_lanes.path_state(index)
        if state is None:
            findings.append({"file": rel_of(index), "error": input_lanes.absent_reason("file")})
            return None, None
        current = index.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, MemoryError) as exc:
        if input_lanes.is_path_attributable(exc):
            findings.append({"file": rel_of(index), "error": input_lanes.document_reason(exc)})
        else:
            failures.append(input_lanes.environment_reason(rel_of(index), exc))
        return None, None
    m = SECTION_RE.search(current)
    if not m:
        findings.append({"file": rel_of(index), "error": MISSING_SECTION})
        return current, None
    return current, m


def _adrs_present(adrs_dir: Path, rel_of, failures: list[str]) -> bool:
    """Whether the adrs directory is present, by the operating system's answer.

    False only on a confirmed absence.[^absence] A path that exists and is not
    a directory, or whose existence cannot be determined, appends an
    environment-lane failure naming the directory and returns True, so that
    the run does not also report it as not found.[^unlistable]
    """
    try:
        return input_lanes.directory_exists(adrs_dir)
    except OSError as exc:
        failures.append(input_lanes.environment_reason(rel_of(adrs_dir), exc))
        return True


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
    tree = _tree_name(root)
    index = root / tree / "index.md"
    adrs_dir = root / tree / "adrs"
    rel_of = adr_frontmatter.repo_relative(root)

    # Every declared input is tried before the run decides its lane, so one
    # run reports every finding it met.[^precedence]
    findings: list[dict] = []
    failures: list[str] = []
    current, m = _read_index(index, rel_of, findings, failures)
    met = len(failures)
    adrs_present = _adrs_present(adrs_dir, rel_of, failures)
    adrs_listable = adrs_present and len(failures) == met

    want = None
    if adrs_listable:
        try:
            want = render_section(load_adrs(adrs_dir, rel_of))
        except adr_frontmatter.FenceValidationError as exc:
            findings.extend(exc.errors)
        except input_lanes.EnvironmentLaneError as exc:
            # A read that failed for a cause in the process or host (EMFILE,
            # EIO, a MemoryError). A file unreadable for a cause at its path
            # (EACCES, a dangling link, a non-UTF-8 byte) is a finding above.
            failures.extend(exc.failures)
            findings.extend(exc.findings)
        except OSError as exc:
            # A tier directory that exists and cannot be listed: the
            # environment lane, never an empty tier.[^unlistable]
            failures.append(input_lanes.environment_reason(
                rel_of(exc.filename) if exc.filename else rel_of(adrs_dir), exc))

    if not adrs_present or failures:
        # A confirmed-absent adrs directory keeps its exit 2 and ranks with an
        # environment-lane failure: nothing on stdout, every finding on stderr.
        if not adrs_present:
            sys.stderr.write(f"generate-index-rollup.py: {adrs_dir} not found\n")
        if failures or findings:
            input_lanes.emit_environment_failure(
                input_lanes.EnvironmentLaneError(failures, findings),
                "generate-index-rollup", sys.stderr)
        return 2
    if findings:
        return adr_frontmatter.print_validation_errors(
            findings, "generate-index-rollup", sys.stdout, sys.stderr)
    have = m.group(0)

    # JSON on every lane. `check-drift` and `audit-docs` both parse each gate's
    # stdout as JSON regardless of exit code, and a prose diff parses as nothing --
    # the row could not be classified, so the roster accounting could not reconcile.
    # The diff survives as a field, because it is what a reader wants to see.
    rel = str(index.relative_to(root)) if index.is_relative_to(root) else str(index)
    if args.dry_run:
        if have == want:
            print(json.dumps({"drift": False, "path": rel, "region": "## ADRs"}, sort_keys=True))
            return 0
        diff = "".join(difflib.unified_diff(
            have.splitlines(keepends=True), want.splitlines(keepends=True),
            fromfile=f"{rel} (on disk)", tofile=f"{rel} (regenerated)"))
        print(json.dumps({"drift": True, "paths": [rel], "region": "## ADRs", "diff": diff,
                          "fix": "generate-index-rollup.py"}, sort_keys=True))
        return 1

    if have != want:
        index.write_text(current[: m.start()] + want + current[m.end():], encoding="utf-8")
        print(json.dumps({"written": rel, "region": "## ADRs"}, sort_keys=True))
        return 0
    print(json.dumps({"written": None, "region": "## ADRs"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
