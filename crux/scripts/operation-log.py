#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Append to the operations log, or check it.

`append` writes one entry into the detail file `<docs_dir>/log/YYYY-MM.md` of the month that
holds the host's local date, whatever the entry's heading date. It validates the request,
plans and runs the repair, and inserts the entry, with no other write between those steps. It
prints one JSON result: `status` (`written`, `recorded` or `refused`), `file`, `changed_paths`,
`commit_paths`, `restore_paths` and `left_strays`. A caller's commit step runs
`git restore --staged` on `restore_paths` when that list is not empty, then `git add` and
`git commit --only` on its own paths and `commit_paths` when that combined list is not empty.
It commits every listed log path, a file the check reports as undefined included.

An append that refuses after the caller's own writes leaves them in place and adds no entry.
It refuses on the caller's own body or heading (fix it), on a tree fault that names its own
fix, or on another writer's change to a planned file or the destination (rerun). After the
fix, rerun the append alone: it writes the entry once, and a second rerun reports `recorded`.

`repair` runs the first split while the completion record is absent and merges every stray
(a `log.md` beside a split tree, or a staged stray). It plans the whole repair in memory
first, so a refusal writes nothing; `--dry-run` prints the plan and the split's proof (the
legacy sha256, the entries per month and the reconstruction equality) and writes nothing. It
prints `changed_paths`, `commit_paths` and `restore_paths` as `append` does.

`check` runs the operations-log audit checks CHK-LOG-1 to CHK-LOG-7 and prints one JSON
report. A BROKEN or DRIFT finding exits 1; a WARNING alone leaves the exit at 0. CHK-LOG-5's
DRIFT findings are fixed by `repair`; its BROKEN conflicts have no auto-fix. CHK-LOG-7 runs the
summary gate (`generate-log-summary.py --dry-run`): a region failure is DRIFT fixed by the
regenerator, a structure failure is DRIFT with no auto-fix (a hand edit of `summary.md` or
`repair`), and pending months are a WARNING that `cleanup-campsite` clears. `check --today`
replaces the local date the summary gate reads.

`--today YYYY-MM-DD` replaces the host's local date. `append` accepts it only while
`CRUX_OPERATION_LOG_TEST=1`, which the tests set.

Exit codes: 0 written, recorded, repaired, planned or clean; 1 refused or findings;
2 environment.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bionic_config import BionicConfigError, load_config  # noqa: E402
import input_lanes  # noqa: E402
import operation_log as ol  # noqa: E402


def _emit(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True))


def _body(args: argparse.Namespace) -> str:
    if args.body_stdin:
        return sys.stdin.read()
    path = Path(args.body_file)
    if path.is_symlink() or not path.is_file():
        raise ol.Refusal("body file is missing, a symlink or not a regular file", "invalid-body")
    return ol._decode(path.read_bytes(), "body file")


def cmd_append(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve()
    try:
        today = ol.resolve_today(args.today, write=True)
        tree = load_config(root, require_tree=True).docs_root
        body = _body(args)
    except ol.Refusal as exc:
        _emit({"status": "refused", "file": None, "changed_paths": [], "commit_paths": [],
               "restore_paths": [], "left_strays": [], "error": str(exc), "code": exc.code})
        return 1
    except (BionicConfigError, OSError) as exc:
        print(f"operation-log: {exc}", file=sys.stderr)
        return 2
    try:
        result = ol.append_entry(tree, root, args.date, args.op, args.subject, body, today)
        result.update(ol.log_commit_paths(root, tree))
    except OSError as exc:
        print(f"operation-log: {exc}", file=sys.stderr)
        return 2
    except ol.Refusal as exc:
        print(f"operation-log: {exc}", file=sys.stderr)
        return 2
    _emit(result)
    return 0 if result["status"] in ("written", "recorded") else 1


def cmd_repair(args: argparse.Namespace) -> int:
    """Plan the repair, print the plan and its proof, and run it unless `--dry-run`."""
    root = Path(args.repo_root).resolve()
    result: dict = {"status": "refused", "dry_run": bool(args.dry_run), "actions": [], "proof": {},
                    "changed_paths": [], "commit_paths": [], "restore_paths": [], "error": None, "code": None}
    try:
        today = ol.resolve_today(args.today, write=not args.dry_run)
        tree = load_config(root, require_tree=True).docs_root
    except ol.Refusal as exc:
        result.update(error=str(exc), code=exc.code)
        _emit(result)
        return 1
    except (BionicConfigError, OSError) as exc:
        print(f"operation-log: {exc}", file=sys.stderr)
        return 2
    prefix = tree.relative_to(root).as_posix()
    changed: list[str] = []
    try:
        try:
            plan = ol.plan_repair(tree, today)
            result.update(actions=list(plan.actions), proof=plan.proof)
            if args.dry_run:
                result.update(status="planned", planned_paths=[f"{prefix}/{rel}" for rel in plan.paths])
            else:
                changed = ol.repair(tree, plan, root)
                result["status"] = "repaired"
        except ol.Refusal as exc:
            changed = list(getattr(exc, "changed", []))
            result.update(error=str(exc), code=exc.code)
        result["changed_paths"] = [f"{prefix}/{rel}" for rel in changed]
        result.update(ol.log_commit_paths(root, tree))
    except (OSError, ol.Refusal) as exc:
        print(f"operation-log: {exc}", file=sys.stderr)
        return 2
    _emit(result)
    return 0 if result["status"] in ("planned", "repaired") else 1


# --------------------------------------------------------------------------- check

def _finding(findings: list, check: str, severity: str, path: str, message: str) -> None:
    findings.append({"check": check, "severity": severity, "path": path, "message": message})


def _lstat(path: Path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


REPAIR_FIX = "run operation-log.py repair, which is lossless"


def _regular_bytes(path: Path) -> bytes | None:
    details = _lstat(path)
    return path.read_bytes() if details is not None and stat.S_ISREG(details.st_mode) else None


def _chk_log_5(tree: Path, rel, findings: list) -> None:
    """CHK-LOG-5: repair sources and an absent completion record (DRIFT), and conflicts (BROKEN)."""
    log_dir = tree / ol.LOG_DIR
    names = sorted(os.listdir(log_dir)) if _lstat(log_dir) is not None and log_dir.is_dir() \
        and not log_dir.is_symlink() else []
    completion = ol.COMPLETION_NAME in names
    staged_legacy = [name for name in names if ol.STAGED_LEGACY_NAME.match(name)]
    staged_strays = [name for name in names if ol.STAGED_STRAY_NAME.match(name)]
    transactions = [name for name in names if ol.TRANSACTION_NAME.match(name)]
    if _lstat(tree / ol.LEGACY_NAME) is not None:
        role = "a stray" if completion or staged_legacy or transactions else "the legacy log, not yet split"
        _finding(findings, "CHK-LOG-5", "DRIFT", rel(ol.LEGACY_NAME), f"{ol.LEGACY_NAME} is {role}; {REPAIR_FIX}")
    for name in staged_legacy:
        _finding(findings, "CHK-LOG-5", "DRIFT", rel(f"{ol.LOG_DIR}/{name}"),
                 f"a staged legacy file: the first split is incomplete; {REPAIR_FIX}")
    for name in staged_strays:
        _finding(findings, "CHK-LOG-5", "DRIFT", rel(f"{ol.LOG_DIR}/{name}"), f"a staged stray; {REPAIR_FIX}")
    for name in transactions:
        what = "a leftover split transaction file" if completion else "a split transaction file: the first split is incomplete"
        _finding(findings, "CHK-LOG-5", "DRIFT", rel(f"{ol.LOG_DIR}/{name}"), f"{what}; {REPAIR_FIX}")
    if not completion:
        _finding(findings, "CHK-LOG-5", "DRIFT", rel(f"{ol.LOG_DIR}/{ol.COMPLETION_NAME}"),
                 f"no completion record of the first split; {REPAIR_FIX}")
    legacy_bytes = {name: _regular_bytes(log_dir / name) for name in staged_legacy}
    if len(set(legacy_bytes.values())) > 1:
        _finding(findings, "CHK-LOG-5", "BROKEN", rel(ol.LOG_DIR),
                 "distinct staged legacy files: " + ", ".join(staged_legacy) + "; no auto-fix")
    for name in staged_strays:
        raw = _regular_bytes(log_dir / name)
        if raw is not None and raw in legacy_bytes.values():
            _finding(findings, "CHK-LOG-5", "BROKEN", rel(f"{ol.LOG_DIR}/{name}"),
                     "a staged stray holds the bytes of a staged legacy file; no auto-fix")
    if completion and staged_legacy:
        _finding(findings, "CHK-LOG-5", "BROKEN", rel(ol.LOG_DIR),
                 "a staged legacy file beside the completion record; no auto-fix")


SUMMARY_REGION_FIX = "auto-fix: run generate-log-summary.py"
SUMMARY_STRUCTURE_FIX = ("no auto-fix: edit summary.md by hand (remove the section or repair the marker) "
                         "or run operation-log.py repair")


def _chk_log_7(root: Path, tree: Path, today: str, rel, findings: list) -> None:
    """CHK-LOG-7: the summary gate's region failures and structure failures (DRIFT), pending months (WARNING)."""
    path = rel(f"{ol.LOG_DIR}/{ol.SUMMARY_NAME}")
    try:
        _, payload = ol.summarize(tree, root, today, write=False)
    except input_lanes.EnvironmentLaneError as exc:
        _finding(findings, "CHK-LOG-7", "BROKEN", path,
                 "the summary gate could not read its inputs: " + "; ".join(exc.failures))
        return
    for error in payload.get("validation_errors", []):
        _finding(findings, "CHK-LOG-7", "DRIFT", error["file"],
                 f"the summary gate cannot read this input: {error['error']}")
    for failure in payload.get("failures", []):
        fix = SUMMARY_REGION_FIX if failure["kind"] == "region" else SUMMARY_STRUCTURE_FIX
        _finding(findings, "CHK-LOG-7", "DRIFT", path, f"{failure['kind']} failure: {failure['problem']}; {fix}")
    pending = payload.get("pending_months", [])
    if pending:
        _finding(findings, "CHK-LOG-7", "WARNING", path,
                 "settled months without a summary section: " + ", ".join(pending)
                 + "; run cleanup-campsite, which runs the catch-up")


def check(root: Path, tree: Path, today: str | None = None) -> dict:
    """The CHK-LOG-1 to CHK-LOG-7 findings for one tree."""
    findings: list[dict] = []
    prefix = tree.relative_to(root).as_posix()
    rel = lambda name: f"{prefix}/{name}"  # noqa: E731

    regexes = None
    try:
        regexes = ol.op_regexes(tree)
        for warning in regexes.warnings:
            _finding(findings, "CHK-LOG-4", "WARNING", rel("AGENTS.md"), warning)
    except ol.Refusal as exc:
        _finding(findings, "CHK-LOG-4", "BROKEN", rel("AGENTS.md"), str(exc))

    # CHK-LOG-6: names and file kinds under log/, and the legacy file's kind.
    readable: list[tuple[str, str]] = []  # (tree-relative path, kind)
    legacy = _lstat(tree / ol.LEGACY_NAME)
    if legacy is not None:
        if stat.S_ISREG(legacy.st_mode):
            readable.append((ol.LEGACY_NAME, "legacy"))
        else:
            _finding(findings, "CHK-LOG-6", "BROKEN", rel(ol.LEGACY_NAME),
                     "the log file is a symlink or not a regular file")
    log_dir = _lstat(tree / ol.LOG_DIR)
    if log_dir is not None and not stat.S_ISDIR(log_dir.st_mode):
        _finding(findings, "CHK-LOG-6", "BROKEN", rel(ol.LOG_DIR), "log/ is a symlink or not a directory")
    elif log_dir is not None:
        for name in sorted(os.listdir(tree / ol.LOG_DIR)):
            path = f"{ol.LOG_DIR}/{name}"
            details = _lstat(tree / path)
            if details is None:
                continue
            if not ol.is_defined_name(name):
                _finding(findings, "CHK-LOG-6", "BROKEN", rel(path), "the name is not one the operations log defines")
                continue
            if ol.TEMPORARY_NAME.match(name):
                _finding(findings, "CHK-LOG-6", "WARNING", rel(path), "a leftover write temporary")
                continue
            if not stat.S_ISREG(details.st_mode):
                _finding(findings, "CHK-LOG-6", "BROKEN", rel(path), "the log file is a symlink or not a regular file")
                continue
            if ol.DETAIL_NAME.match(name):
                readable.append((path, "detail"))
            elif ol.STAGED_LEGACY_NAME.match(name) or ol.STAGED_STRAY_NAME.match(name):
                readable.append((path, "staged"))

    headings = 0
    for path, kind in readable:
        raw = (tree / path).read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            _finding(findings, "CHK-LOG-1", "DRIFT", rel(path), f"the file is not UTF-8: {exc}")
            continue
        pieces = ol.cut(text)
        for entry in pieces.entries:
            headings += 1
            heading = entry.split("\n", 1)[0].removesuffix("\r")
            parsed = ol.HEADING.match(heading)
            if parsed is None or not ol.real_date(parsed.group(1)):
                _finding(findings, "CHK-LOG-1", "DRIFT", rel(path),
                         f"malformed heading or a date that is not a real calendar date: {heading!r}")
                continue
            if regexes is not None and not regexes.historical.match(heading):
                _finding(findings, "CHK-LOG-1", "DRIFT", rel(path),
                         f"heading fails the section 6 historical-reader regex: {heading!r}")
                _finding(findings, "CHK-LOG-4", "BROKEN", rel(path),
                         f"op {parsed.group(2)!r} is outside the enum: {heading!r}")
        if pieces.open_fence and pieces.entries:
            _finding(findings, "CHK-LOG-1", "DRIFT", rel(path),
                     "the last entry ends inside an open fence")
        elif pieces.open_fence:
            _finding(findings, "CHK-LOG-1", "DRIFT", rel(path), "the outside bytes leave a fence open")
        if kind == "detail":
            expected = ol.detail_header(Path(path).stem)
            if pieces.outside != expected:
                _finding(findings, "CHK-LOG-2", "DRIFT", rel(path),
                         f"the outside bytes are not the detail header; expected {expected!r}")

    _chk_log_5(tree, rel, findings)
    _chk_log_7(root, tree, today or ol.local_date(), rel, findings)

    has_init = False
    try:
        has_init = any((entry.parsed() or ("", "", ""))[1] == "init" for entry in ol.read_entries(tree))
        if not has_init:
            _finding(findings, "CHK-LOG-3", "BROKEN", rel(ol.LOG_DIR), "the log holds no init entry")
    except ol.Refusal as exc:
        _finding(findings, "CHK-LOG-3", "BROKEN", rel(ol.LOG_DIR), f"the log cannot be read: {exc}")

    failing = [item for item in findings if item["severity"] in ("BROKEN", "DRIFT")]
    return {"status": "findings" if failing else "clean", "findings": findings,
            "coverage": {"files": len(readable), "headings": headings}}


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve()
    try:
        tree = load_config(root, require_tree=True).docs_root
        today = ol.resolve_today(args.today, write=False)
        report = check(root, tree, today)
    except ol.Refusal as exc:
        _emit({"status": "refused", "error": str(exc), "code": exc.code})
        return 1
    except (BionicConfigError, OSError) as exc:
        print(f"operation-log: {exc}", file=sys.stderr)
        return 2
    _emit(report)
    return 1 if report["status"] == "findings" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    append = sub.add_parser("append", help="append one entry to the current month's detail file")
    append.add_argument("--repo-root", default=".")
    append.add_argument("--op", required=True)
    append.add_argument("--subject", required=True)
    append.add_argument("--date", required=True, help="the heading date, YYYY-MM-DD")
    bodies = append.add_mutually_exclusive_group(required=True)
    bodies.add_argument("--body-file")
    bodies.add_argument("--body-stdin", action="store_true")
    append.add_argument("--today", help=f"replace the local date (only while {ol.TEST_ENV}=1)")
    fixer = sub.add_parser("repair", help="run the first split and merge every stray")
    fixer.add_argument("--repo-root", default=".")
    fixer.add_argument("--dry-run", action="store_true", help="print the plan and the proof; write nothing")
    fixer.add_argument("--today", help=f"replace the local date (a write only while {ol.TEST_ENV}=1)")
    checker = sub.add_parser("check", help="run CHK-LOG-1 to CHK-LOG-7")
    checker.add_argument("--repo-root", default=".")
    checker.add_argument("--today", help="replace the local date the summary gate reads")
    args = parser.parse_args(argv)
    commands = {"append": cmd_append, "repair": cmd_repair, "check": cmd_check}
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
