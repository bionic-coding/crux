#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Write one journal or log-only request with replayable, per-file writes.

The caller owns the narrative and keeps its timestamped request for retry.
The writer never runs version control: every file it touches stays modified and
uncommitted. Each result reports `recorded` (surfaces holding the requested
content on disk) and `written` (surfaces this run changed). A partial result
lists the recorded surfaces when a later stage fails.

The log record goes through `operation_log` in its phased order: the whole request
is validated (the log entry by `validate_entry`) and `preflight` plans the repair
before any write; then the repair runs, the journal month file and the index are
written, and `insert_entry` places the entry in the detail file of the month that
holds the host's local date. The result adds `changed_paths` (the log paths this run
created, replaced or removed), `commit_paths`, `restore_paths` and `left_strays`;
log-work commits the log paths by the commit step that `operation_log` describes.
`--today` replaces the local date only while `CRUX_OPERATION_LOG_TEST=1`.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bionic_config import BionicConfigError, load_config  # noqa: E402
from journal_index import (CATEGORIES, ENTRY_RE, derive_row, find_unclosed_fence,
                           render_index, unknown_category_headings)  # noqa: E402
from md_fences import closes_fence, fence_marker, split_lines  # noqa: E402
import operation_log as ol  # noqa: E402
from operation_log import Refusal  # noqa: E402


GENERATOR = Path(__file__).with_name("generate-journal-index.py")
HEADER = "# Journal — {month}\n\n_Append-only. Newest entries at the top._\n\n"
LOG_HEADING = re.compile(r"^## \[[0-9]{4}-[0-9]{2}-[0-9]{2}\] [^\n]+$")
REF = re.compile(r"(?:\[\[[^\[\]\n]+\]\]|rule:[a-z][a-z0-9-]*)\Z")


def _regular_read(path: Path, *, missing_ok: bool = True) -> bytes | None:
    if path.is_symlink():
        raise Refusal(f"{path.name} is a symlink")
    if not path.exists():
        if missing_ok:
            return None
        raise Refusal(f"{path.name} is missing")
    if not path.is_file():
        raise Refusal(f"{path.name} is not a regular file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        return handle.read()


def _text(raw: bytes | None, name: str) -> str:
    if raw is None:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Refusal(f"{name} is not UTF-8: {exc}") from exc


def _timestamp(value: str) -> tuple[str, str, str, str]:
    try:
        instant = datetime.fromisoformat(value)
    except ValueError as exc:
        raise Refusal("--at must be an ISO8601 timestamp") from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise Refusal("--at requires an explicit local offset")
    minute = instant.replace(second=0, microsecond=0)
    return (minute.strftime("%Y-%m-%d %H:%M"), minute.strftime("%Y-%m"),
            minute.strftime("%Y-%m-%d"), minute.isoformat(timespec="minutes"))


def _body(raw: str, mode: str, refs: str | None) -> tuple[str, str]:
    if "\r" in raw or "\x00" in raw:
        raise Refusal("body contains a carriage return or NUL")
    lines = [line.rstrip(" \t") for line in split_lines(raw)]
    while lines and not lines[-1]:
        lines.pop()
    if not lines or not any(lines):
        raise Refusal("body requires at least one nonempty line")
    if mode == "journal" and not 1 <= len(lines) <= 10:
        raise Refusal("journal body requires 1–10 lines")
    if mode == "log-only" and len(lines) != 1:
        raise Refusal("log-only body requires one line")
    if any(line.startswith("## [") for line in lines):
        raise Refusal("body contains a reserved entry heading")
    if find_unclosed_fence("\n".join(lines)) is not None:
        raise Refusal("body leaves a Markdown fence open")
    friction = [i for i, line in enumerate(lines) if line.startswith("Friction:")]
    if len(friction) > 1 or any(lines[i].split(":", 1)[1].strip().lower() in ("", "none", "none.") for i in friction):
        raise Refusal("Friction line is empty, repeated, or says none")
    refs_tokens = refs.split() if refs else []
    if refs is not None and not refs_tokens:
        raise Refusal("--refs is empty")
    if any(not REF.fullmatch(token) for token in refs_tokens):
        raise Refusal("--refs requires wiki-links or rule citations")
    if mode == "journal":
        if any(line.startswith("Refs:") for line in lines):
            raise Refusal("put references in --refs, not the body")
        if refs_tokens:
            lines.append("Refs: " + " ".join(refs_tokens))
    return "\n".join(lines), " ".join(refs_tokens)


def _entry_ranges(text: str, pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    """Return `(heading, exact block)` for headings outside fenced content."""
    # Preserve the exact bytes while using md_fences' newline-only boundary.
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]] + [parts[-1]]
    found: list[tuple[str, str]] = []
    fence: tuple[str, int] | None = None
    start: int | None = None
    heading = ""
    for pos, raw_line in enumerate(lines):
        line = raw_line.removesuffix("\n").removesuffix("\r")
        marker = fence_marker(line)
        if fence is not None:
            if closes_fence(marker, fence):
                fence = None
            continue
        if marker is not None:
            fence = (marker[0], marker[1])
            continue
        if pattern.match(line):
            if start is not None:
                found.append((heading, "".join(lines[start:pos])))
            start, heading = pos, line
    if start is not None:
        found.append((heading, "".join(lines[start:])))
    return found


def _month_insertion(text: str, month: str) -> tuple[str, str]:
    """Keep the existing month preamble above the first journal entry."""
    title = f"# Journal — {month}\n\n"
    if not text.startswith(title):
        raise Refusal("monthly journal lacks a recognized header")
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]] + [parts[-1]]
    offset = 0
    first_entry: int | None = None
    fence: tuple[str, int] | None = None
    for raw_line in lines:
        line = raw_line.removesuffix("\n").removesuffix("\r")
        marker = fence_marker(line)
        if fence is not None:
            if closes_fence(marker, fence):
                fence = None
        elif marker is not None:
            fence = (marker[0], marker[1])
        elif ENTRY_RE.match(line):
            first_entry = offset
            break
        offset += len(raw_line)
    split_at = first_entry if first_entry is not None else len(text)
    preamble = text[:split_at]
    if not preamble.endswith("\n\n"):
        preamble += "\n" if preamble.endswith("\n") else "\n\n"
    return preamble, text[split_at:]


def _exact_record(existing: str, heading: str, candidate: str,
                  pattern: re.Pattern[str], minute: str | None = None,
                  log_mode: str | None = None) -> bool:
    for old_heading, block in _entry_ranges(existing, pattern):
        if old_heading != heading:
            continue
        if minute is not None:
            lines = split_lines(block)
            field_index = 3 if log_mode == "log-only" else 2
            if len(lines) <= field_index:
                continue
            field = lines[field_index]
            field_pattern = (r"Recorded at (?P<minute>[^ .]+)\.(?: Refs: .*)?"
                             if log_mode == "log-only" else
                             r"Entry in `[^`\n]+` at (?P<minute>[^ .]+)\.(?: Refs: .*)?")
            matched = re.fullmatch(field_pattern, field)
            if matched is None:
                continue
            recorded_minute = matched.group("minute")
            if recorded_minute[:16] == minute[:16] and recorded_minute != minute:
                raise Refusal("the same civil minute and heading already carry a different UTC offset")
            if recorded_minute != minute:
                continue
        if block == candidate:
            return True
        raise Refusal("the same recorded minute and heading already carry different content")
    return False


# The pinned no-follow reader and replacement live in operation_log, which admits the
# `journal` and `log` parents. The names stay here for the tests that patch them.
_read_at = ol.read_at
_atomic_replace = ol.atomic_replace


def _preflight(root: Path, month: str, prospective: str) -> None:
    result = subprocess.run(["uv", "run", "--no-config", str(GENERATOR),
                             "--check-stdin", "--month", month, "--repo-root", str(root)],
                            input=prospective, text=True, capture_output=True)
    if result.returncode:
        detail = result.stdout.strip() or result.stderr.strip()
        raise Refusal(f"prospective journal index check failed: {detail}")


def _render_index(tree: Path, config_docs_dir: str) -> tuple[bytes | None, bytes]:
    """Use the regenerator's own walk and the shared derivation primitives."""
    spec = importlib.util.spec_from_file_location("journal_generator", GENERATOR)
    assert spec and spec.loader
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    journal_dir = tree / "journal"
    month_texts, errors, failures = generator._walk_journal_dir(
        journal_dir, f"{config_docs_dir}/journal")
    if errors or failures:
        raise Refusal(f"journal index input changed: {errors + failures}")
    rows = []
    for month in sorted(month_texts, reverse=True):
        month_text = month_texts[month][0]
        if find_unclosed_fence(month_text) is not None or unknown_category_headings(month_text):
            raise Refusal("journal index input became malformed")
        rows.append(derive_row(month, month_text))
    path = journal_dir / "index.md"
    old = _regular_read(path)
    # The generator owns output-path validation as well as month-file validation.
    generator._validate_output_index(path, tree, f"{config_docs_dir}/journal/index.md")
    dates = [row["last"] for row in rows if row["last"] != "—"]
    return old, render_index(rows, max(dates) if dates else "—").encode("utf-8")


def _result(status: str, mode: str, timestamp: str | None, warnings: list[str],
            recorded: list[str], pending: list[str], written: list[str], error: str | None,
            log: dict) -> int:
    print(json.dumps({"status": status, "mode": mode, "timestamp": timestamp,
                      "warnings": warnings, "recorded": recorded, "pending": pending,
                      "written": written, "error": error, **log}, sort_keys=True))
    return 0 if status == "complete" else 1


def _log_paths(root: Path | None, tree: Path | None, changed: list[str],
               strays: list[str], code: str | None) -> dict:
    """The log part of the result: changed, commit and restore paths, and left strays."""
    found = {"changed_paths": [], "commit_paths": [], "restore_paths": [], "left_strays": [],
             "code": code}
    if root is None or tree is None:
        return found
    prefix = tree.relative_to(root).as_posix()
    found["changed_paths"] = [f"{prefix}/{path}" for path in changed]
    found["left_strays"] = [f"{prefix}/{path}" for path in strays]
    try:
        found.update(ol.log_commit_paths(root, tree))
    except (Refusal, OSError) as exc:
        found["error_commit_paths"] = str(exc)
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--mode", required=True, choices=("journal", "log-only"))
    ap.add_argument("--at", required=True)
    ap.add_argument("--category", required=True)
    ap.add_argument("--subject", required=True)
    bodies = ap.add_mutually_exclusive_group(required=True)
    bodies.add_argument("--body-file")
    bodies.add_argument("--body-stdin", action="store_true")
    ap.add_argument("--refs")
    ap.add_argument("--log-op")
    ap.add_argument("--today", help=f"replace the local date (only while {ol.TEST_ENV}=1)")
    args = ap.parse_args(argv)

    warnings: list[str] = []
    recorded: list[str] = []
    written: list[str] = []
    timestamp: str | None = None
    surfaces = ["log"] if args.mode == "log-only" else ["journal/{month}.md", "journal/index.md", "log"]
    root: Path | None = None
    tree: Path | None = None
    changed: list[str] = []
    strays: list[str] = []
    try:
        # One local date, read once before validation, governs preflight, repair and insertion.
        log_today = ol.resolve_today(args.today, write=True)
        log_surface = ol.destination_for(log_today)
        surfaces[-1] = log_surface
        record_minute, month, today, timestamp = _timestamp(args.at)
        surfaces = [path.replace("{month}", month) for path in surfaces]
        category = args.category if args.category in CATEGORIES else "misc"
        if category != args.category:
            warnings.append(f"unknown category {args.category!r}; using misc")
        if not args.subject or args.subject != args.subject.strip() or "\n" in args.subject or "\r" in args.subject or "|" in args.subject or "\x00" in args.subject:
            raise Refusal("subject must be one nonempty line without a pipe")
        root = Path(args.repo_root).resolve()
        config = load_config(root, require_tree=True)
        tree = config.docs_root
        journal_dir = tree / "journal"
        if args.mode == "journal":
            if journal_dir.is_symlink() or not journal_dir.is_dir() or journal_dir.resolve() != tree / "journal":
                raise Refusal("journal directory is missing or unsafe")
        op = "journal" if args.mode == "journal" else args.log_op
        if not op or not ol.op_regexes(tree).current.fullmatch(f"## [{today}] {op} | "):
            raise Refusal("log operation is missing or outside the canonical enum")
        if args.body_stdin:
            raw_body = sys.stdin.read()
        else:
            raw_body = _text(_regular_read(Path(args.body_file), missing_ok=False), "body file")
        body, refs = _body(raw_body, args.mode, args.refs)
        if args.mode == "journal":
            month_path = journal_dir / f"{month}.md"
            old_month = _regular_read(month_path)
            month_text = _text(old_month, month_path.name) if old_month is not None else HEADER.format(month=month)
            preamble, prior_entries = _month_insertion(month_text, month)
            heading = f"## [{record_minute}] {category} | {args.subject}"
            entry = f"{heading}\n\n{body}\n\n"
            month_done = _exact_record(month_text, heading, entry, ENTRY_RE)
            if month_done:
                prospective = month_text
            else:
                prospective = preamble + entry + prior_entries
            log_heading = f"## [{today}] journal | {category}: {args.subject}"
            log_body = f"Entry in `{config.docs_dir}/journal/{month}.md` at {timestamp}."
            if refs:
                log_body += f" Refs: {refs}"
        else:
            prospective = None
            log_heading = f"## [{today}] {op} | {args.subject}"
            log_body = f"{body}\nRecorded at {timestamp}."
            if refs:
                log_body += f" Refs: {refs}"
        log_record = ol.validate_entry(tree, today, op, log_heading.split(" | ", 1)[1], log_body)
        plan = ol.preflight(tree, log_today, log_record)
        log_entries = ol.read_entries(tree)
        log_text = "".join(held.text for held in log_entries)
        log_done = _exact_record(log_text, log_heading, log_record.text, LOG_HEADING,
                                 timestamp, args.mode)
        if args.mode == "journal" and month_done:
            recorded.append(surfaces[0])
            if not log_done:
                warnings.append("offset unverified: the month entry has no offset and no matching log record confirms the supplied offset")
        if args.mode == "journal":
            _preflight(root, month, prospective)
        if log_done:
            held_at = next((held.path for held in log_entries if held.text == log_record.text), log_surface)
            surfaces[-1] = held_at
            recorded.append(held_at)
        changed += ol.repair(tree, plan, root)
        if args.mode == "journal" and not month_done:
            _atomic_replace(month_path, prospective.encode("utf-8"), old_month, tree, root)
            written.append(surfaces[0])
            recorded.append(surfaces[0])
        if args.mode == "journal":
            old_index, wanted_index = _render_index(tree, config.docs_dir)
            if old_index == wanted_index:
                recorded.append(surfaces[1])
            else:
                _atomic_replace(tree / "journal" / "index.md", wanted_index, old_index, tree, root)
                written.append(surfaces[1])
                recorded.append(surfaces[1])
        placed = ol.insert_entry(tree, log_record, log_today, root)
        strays = placed["left_strays"]
        if placed["status"] == "written":
            changed += placed["changed"]
            written.append(placed["file"])
        surfaces[-1] = placed["file"]
        if placed["file"] not in recorded:
            recorded.append(placed["file"])
        return _result("complete", args.mode, timestamp, warnings,
                       surfaces, [], written, None, _log_paths(root, tree, changed, strays, None))
    except (Refusal, BionicConfigError, OSError, UnicodeDecodeError, ValueError) as exc:
        changed += getattr(exc, "changed", [])
        pending = [surface for surface in surfaces if surface not in recorded]
        status = "partial" if recorded else "refused"
        return _result(status, args.mode, timestamp, warnings, recorded, pending, written,
                       str(exc), _log_paths(root, tree, changed, strays,
                                            getattr(exc, "code", None)))


if __name__ == "__main__":
    raise SystemExit(main())
