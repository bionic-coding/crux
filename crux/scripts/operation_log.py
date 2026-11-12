"""operation_log.py — the operations log as monthly detail files under `<docs_dir>/log/`.

One module owns the log's names, its entry grammar, its readers and its one writer, so no
skill computes a month, creates a header or places an entry by hand.

NAMES UNDER `log/`. A detail file is `YYYY-MM.md` (`DETAIL_NAME`). `summary.md` is the
summary. `.split-complete.json` is the completion record of the first split. The first
split and the stray merge also define a staged legacy file `.legacy-<sha256>.md`, a split
transaction file `.split-<sha256>.json`, a staged stray `.stray-<sha256>.md` and a kept
file `.kept-<sha256>.txt`. The replacement helper's temporary `.write-journal-<hex>` is a
defined name too, which the check reports only as a leftover. Any other name is undefined.

THE ENTRY CUTTER. `cut` reads a file line by line and tracks fenced code blocks with
`md_fences`. An entry starts at a line outside a fence that starts with `## ` and runs to
the next such line or the end of the file. A `## ` line inside a fence belongs to its entry,
and a fence left open runs to the end of the file. The bytes before the first entry are the
outside bytes. A last entry without a newline gains one terminal newline, which belongs to
the entry wherever entries are compared or placed. Every comparison of entries compares cut
entries.

THE WRITER. Every in-process caller runs one order: `validate_entry`, `preflight`,
`repair`, its own writes, `insert_entry`. The caller reads the local date once, before
`validate_entry`, and passes that one value to every later step, so a run that crosses
midnight at a month boundary verifies and writes one month's file. `preflight` writes
nothing. `repair(tree, plan)` is the one repair entry point; it refuses with nothing written
when a file the plan read changed, and it repeats the insertion check after its last step.
`insert_entry` runs no repair; its refusals (the insertion check and the replacement's
changed-file check) each need another writer's change after the repair phase. `append_entry`
runs the whole order with no caller write between the steps; only `operation-log.py append`
calls it.

An append that refuses after a skill's own writes leaves those writes in place and adds no
entry. Three causes refuse there: `validate_entry` rejects the skill's own body or heading
(fix the body), a tree fault names its own fix (a malformed stray heading, an open fence in
the destination's outside bytes), or another writer changed a planned file or the destination
(rerun). After the fix, a rerun of the append step alone adds the entry once, and a second
rerun reports `recorded`.

THE REPAIR. `plan_repair` runs the whole repair in memory and writes nothing; `preflight`
is that plan plus the insertion check of the caller's entry. `repair(tree, plan)` runs it on
disk, each step re-reading the files, in this order. It first names every staged file by the
digest of its bytes (a crash can leave a misnamed or duplicated one). It refuses on a
conflict: distinct staged legacy files, a staged legacy file and a staged stray with equal
bytes, or a staged legacy file beside the completion record. Classification reads the
completion record first. With it, the split is complete, `log.md` is a stray and a leftover
transaction file is removed. Without it, a staged legacy file or a transaction file means an
incomplete split, which resumes, and `log.md` is then a stray; with neither, `log.md` is the
legacy log. The first split stages the legacy log under its digest, cuts and proves it,
writes a transaction file naming each target's entry positions and digests before and after,
replaces each target by digest, removes the staged file, writes the completion record and
removes the transaction file. Each stray merge stages its source, moves the entries no detail
file holds as one block to the top of the local month's file, keeps non-empty outside bytes
once in a content-addressed kept file, and removes the staged stray. A source heading that
fails the historical-reader regex or a real calendar date, or an entry ending inside an open
fence, refuses the whole repair in the plan, before any write.

THE COMMIT STEP. `log_commit_paths` lists every log path git reports, whatever its index or
work-tree state, except `summary.md` and write temporaries. A caller's commit step runs
`git restore --staged` on `restore_paths` when that list is not empty, and then runs `git add`
and `git commit --only` on its own paths and `commit_paths` only when that combined list is not
empty; a restore-only run stops there. `commit_step` is that step. Like the whole-file commit
of `log.md` before it, the step commits every listed log path, including a file the check
reports as undefined and a half-finished hand edit of a detail file.

THE SUMMARY. `summarize` is the logic of `generate-log-summary.py`: the summary gate and the
catch-up of `<docs_dir>/log/summary.md`. A month M is settled from the third day of month M+1 by
the host's local date (`settled`). The gate never reads the current month's detail file, and no
mode writes a section or a region for a month that is not settled. A region renders only tokens
from closed grammars (a path, a digest, a count, a date, an op the historical-reader regex
matched, an `ADR-NNNN` id), so no subject text reaches the file. The rollup is read from the
sections' regions alone. Text outside the regions is kept byte for byte.

Stdlib plus `bionic_config`, `md_fences` and, for the summary, `input_lanes`; no third-party
import.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from md_fences import closes_fence, fence_marker  # noqa: E402

LOG_DIR = "log"
LEGACY_NAME = "log.md"
SUMMARY_NAME = "summary.md"
COMPLETION_NAME = ".split-complete.json"
COMPLETION_FORMAT = "crux.operation-log-split.v1"
DETAIL_NAME = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])\.md$")
STAGED_LEGACY_NAME = re.compile(r"^\.legacy-[0-9a-f]{64}\.md$")
TRANSACTION_NAME = re.compile(r"^\.split-[0-9a-f]{64}\.json$")
STAGED_STRAY_NAME = re.compile(r"^\.stray-[0-9a-f]{64}\.md$")
KEPT_NAME = re.compile(r"^\.kept-[0-9a-f]{64}\.txt$")
TEMPORARY_PREFIX = ".write-journal-"
TEMPORARY_NAME = re.compile(r"^\.write-journal-[0-9a-f]+$")
#: The entry heading grammar: `## [YYYY-MM-DD] <op> | <subject>`.
HEADING = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (\S+) \| (.*)$")
DATE_FORM = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
#: A write mode accepts `--today` only while this variable is `1`.
TEST_ENV = "CRUX_OPERATION_LOG_TEST"
CURRENT_LABEL = "**Current-writer regex**"
HISTORICAL_LABEL = "**Historical-reader regex**"


class Refusal(Exception):
    """Input or on-disk state is unsafe before mutation. `code` names the class."""

    def __init__(self, message: str, code: str = "refused"):
        super().__init__(message)
        self.code = code


def detail_header(month: str) -> str:
    """The exact outside bytes of the detail file of `month` (YYYY-MM)."""
    return f"# Operations log: {month}\n\n_Append-only. Latest write first._\n\n"


def is_defined_name(name: str) -> bool:
    """Whether `name` is one of the names this module defines under `log/`."""
    return bool(name == SUMMARY_NAME or name == COMPLETION_NAME or DETAIL_NAME.match(name)
                or STAGED_LEGACY_NAME.match(name) or TRANSACTION_NAME.match(name)
                or STAGED_STRAY_NAME.match(name) or KEPT_NAME.match(name)
                or TEMPORARY_NAME.match(name))


def real_date(value: str) -> bool:
    """Whether `value` is a real calendar date written YYYY-MM-DD."""
    if not DATE_FORM.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def local_date() -> str:
    """The host's local date, YYYY-MM-DD, in the host time zone."""
    return date.today().isoformat()


def resolve_today(override: str | None, *, write: bool) -> str:
    """The one local date of a run. A write accepts an override only under `TEST_ENV=1`."""
    if override is None:
        return local_date()
    if write and os.environ.get(TEST_ENV) != "1":
        raise Refusal(f"--today is accepted in a write mode only while {TEST_ENV}=1", "today-not-allowed")
    if not real_date(override):
        raise Refusal("--today must be a real date written YYYY-MM-DD", "invalid-today")
    return override


# --------------------------------------------------------------------------- the cutter

@dataclass(frozen=True)
class Cut:
    """A file cut into its outside bytes and its entries."""

    outside: str
    entries: tuple[str, ...]
    open_fence: bool
    added_newline: bool


def _lines(text: str) -> list[str]:
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def _bare(raw_line: str) -> str:
    line = raw_line.removesuffix("\n")
    return line.removesuffix("\r")


def cut(text: str) -> Cut:
    """Cut `text` into outside bytes and entries, tracking fenced code blocks."""
    lines = _lines(text)
    fence: tuple[str, int] | None = None
    starts: list[int] = []
    for index, raw_line in enumerate(lines):
        line = _bare(raw_line)
        marker = fence_marker(line)
        if fence is not None:
            if closes_fence(marker, fence):
                fence = None
            continue
        if marker is not None:
            fence = (marker[0], marker[1])
            continue
        if line.startswith("## "):
            starts.append(index)
    if not starts:
        return Cut("".join(lines), (), fence is not None, False)
    outside = "".join(lines[:starts[0]])
    entries = ["".join(lines[start:end]) for start, end in zip(starts, [*starts[1:], len(lines)])]
    added = False
    if not entries[-1].endswith("\n"):
        entries[-1] += "\n"
        added = True
    return Cut(outside, tuple(entries), fence is not None, added)


def reconstructs(text: str, pieces: Cut) -> bool:
    """Whether the outside bytes and entries, in order, equal `text` (less an added newline)."""
    joined = pieces.outside + "".join(pieces.entries)
    if pieces.added_newline:
        joined = joined[:-1]
    return joined == text


def insert(text: str, new_entries: list[str]) -> str:
    """`text` with `new_entries` placed at its insertion point, above its first entry."""
    pieces = cut(text)
    point = len(pieces.outside) if pieces.entries else len(text)
    head, tail = text[:point], text[point:]
    if head and not head.endswith("\n"):
        head += "\n"
    return head + "".join(new_entries) + tail


def check_insertion(before: str, rendered: str, new_entries: list[str], name: str) -> None:
    """Refuse unless the inserted entries are the first cut entries and the earlier ones follow."""
    old, new = cut(before), cut(rendered)
    count = len(new_entries)
    if list(new.entries[:count]) != list(new_entries) or new.entries[count:] != old.entries:
        reason = ("its outside bytes leave a fence open" if old.open_fence and not old.entries
                  else "the inserted entry would not stay one entry above the existing entries")
        raise Refusal(f"{name}: cannot insert the entry, because {reason}; close the fence or "
                      "repair the file by hand without changing any entry's bytes", "insertion-check")


# --------------------------------------------------------------------------- op-enum readers

@dataclass(frozen=True)
class OpRegexes:
    current: re.Pattern[str]
    historical: re.Pattern[str]
    warnings: tuple[str, ...]


def _regex_after(source: str, label: str) -> re.Pattern[str] | None:
    at = source.find(label)
    if at < 0:
        return None
    match = re.search(r"```[^\n]*\n([^`]+)```", source[at + len(label):])
    if not match or not match.group(1).strip():
        raise Refusal(f"AGENTS.md {label.strip('*')} is malformed", "no-op-enum")
    try:
        # The canonical expression ends in a significant space after `|`.
        return re.compile(match.group(1).splitlines()[0].lstrip(" \t"))
    except re.error as exc:
        raise Refusal(f"AGENTS.md {label.strip('*')} is invalid", "no-op-enum") from exc


def op_regexes_from_text(source: str) -> OpRegexes:
    """Locate the section 6 regex blocks by their bullet labels."""
    current = _regex_after(source, CURRENT_LABEL)
    if current is None:
        raise Refusal("AGENTS.md has no canonical log-operation block", "no-op-enum")
    historical = _regex_after(source, HISTORICAL_LABEL)
    warnings: tuple[str, ...] = ()
    if historical is None:
        historical = current
        warnings = ("AGENTS.md section 6 has no historical-reader regex block; "
                    "the current-writer regex reads history",)
    return OpRegexes(current, historical, warnings)


def op_regexes(tree: Path) -> OpRegexes:
    """The current-writer and historical-reader regexes of the tree's own section 6."""
    tree_fd = _open_tree(tree)
    try:
        raw = _read_name(tree_fd, "AGENTS.md")
    finally:
        os.close(tree_fd)
    if raw is None:
        raise Refusal("AGENTS.md is missing", "no-op-enum")
    return op_regexes_from_text(_decode(raw, "AGENTS.md"))


# --------------------------------------------------------------------------- pinned reads

def _decode(raw: bytes, name: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Refusal(f"{name} is not UTF-8: {exc}", "not-utf8") from exc


def _open_chain(path: Path, *, missing_ok: bool = False) -> int | None:
    """A directory descriptor for `path`, opened component by component without following links."""
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    for component in path.parts[1:]:
        try:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        except FileNotFoundError:
            os.close(fd)
            if missing_ok:
                return None
            raise Refusal(f"{component} is missing", "missing-directory")
        except OSError as exc:
            os.close(fd)
            raise Refusal(f"{component} is a symlink or not a directory", "unsafe-path") from exc
        os.close(fd)
        fd = child
    return fd


def _open_tree(tree: Path) -> int:
    fd = _open_chain(tree)
    assert fd is not None
    return fd


def _open_log_dir(tree_fd: int) -> int | None:
    try:
        return os.open(LOG_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=tree_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise Refusal(f"{LOG_DIR}/ is a symlink or not a directory", "unsafe-log-directory") from exc


def read_at(directory_fd: int, name: str) -> tuple[bytes | None, int | None]:
    """Read a regular target without following its final component."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        raise Refusal(f"{name} is a symlink or not a regular file", "unsafe-path") from exc
    with os.fdopen(fd, "rb") as handle:
        details = os.fstat(handle.fileno())
        if not stat.S_ISREG(details.st_mode):
            raise Refusal(f"{name} is not a regular file", "unsafe-path")
        return handle.read(), stat.S_IMODE(details.st_mode)


def _read_name(directory_fd: int, name: str) -> bytes | None:
    return read_at(directory_fd, name)[0]


def _exists(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _digest(raw: bytes | None) -> str | None:
    return None if raw is None else hashlib.sha256(raw).hexdigest()


# --------------------------------------------------------------------------- the readers

@dataclass(frozen=True)
class Entry:
    """One cut entry with the tree-relative path of the file that holds it."""

    text: str
    path: str

    @property
    def heading(self) -> str:
        return self.text.split("\n", 1)[0].removesuffix("\r")

    def parsed(self) -> tuple[str, str, str] | None:
        match = HEADING.match(self.heading)
        return (match.group(1), match.group(2), match.group(3)) if match else None


@dataclass
class _Files:
    """Every log file of a tree, read through pinned no-follow handles."""

    legacy: bytes | None = None
    legacy_role: str | None = None  # "legacy" or "stray"
    log_dir: bool = False
    names: list[str] = field(default_factory=list)
    details: dict[str, bytes] = field(default_factory=dict)
    staged_legacy: dict[str, bytes] = field(default_factory=dict)
    staged_strays: list[tuple[float, str, bytes]] = field(default_factory=list)
    completion: bytes | None = None
    transactions: list[str] = field(default_factory=list)


def _gather(tree: Path) -> _Files:
    files = _Files()
    tree_fd = _open_tree(tree)
    try:
        files.legacy = _read_name(tree_fd, LEGACY_NAME)
        log_fd = _open_log_dir(tree_fd)
    finally:
        os.close(tree_fd)
    if log_fd is not None:
        files.log_dir = True
        try:
            files.names = sorted(os.listdir(log_fd))
            for name in files.names:
                if DETAIL_NAME.match(name):
                    files.details[name] = _required(log_fd, name)
                elif STAGED_LEGACY_NAME.match(name):
                    files.staged_legacy[name] = _required(log_fd, name)
                elif STAGED_STRAY_NAME.match(name):
                    raw = _required(log_fd, name)
                    mtime = os.stat(name, dir_fd=log_fd, follow_symlinks=False).st_mtime
                    files.staged_strays.append((mtime, name, raw))
                elif name == COMPLETION_NAME:
                    files.completion = _required(log_fd, name)
                elif TRANSACTION_NAME.match(name):
                    files.transactions.append(name)
        finally:
            os.close(log_fd)
    if files.legacy is not None:
        incomplete = bool(files.staged_legacy or files.transactions)
        files.legacy_role = "stray" if files.completion is not None or incomplete else "legacy"
    files.staged_strays.sort(key=lambda item: (item[0], item[1]))
    return files


def _required(directory_fd: int, name: str) -> bytes:
    raw = _read_name(directory_fd, name)
    if raw is None:
        raise Refusal(f"{LOG_DIR}/{name} disappeared during the read", "changed")
    return raw


def read_entries(tree: Path) -> list[Entry]:
    """The log's entries: strays newest first, detail files newest month first, then legacy.

    A legacy or staged legacy entry is returned only for its count beyond the detail files'
    multiset. A stray entry is returned only when it appears in no detail file, no legacy file
    and no stray earlier in merge order; two identical entries inside one stray both stay.
    """
    files = _gather(Path(tree))
    detail_entries: list[Entry] = []
    for name in sorted(files.details, reverse=True):
        text = _decode(files.details[name], f"{LOG_DIR}/{name}")
        detail_entries += [Entry(item, f"{LOG_DIR}/{name}") for item in cut(text).entries]
    in_details = Counter(entry.text for entry in detail_entries)

    legacy_sources: list[tuple[str, list[str]]] = []
    if files.legacy is not None and files.legacy_role == "legacy":
        legacy_sources.append((LEGACY_NAME, list(cut(_decode(files.legacy, LEGACY_NAME)).entries)))
    seen_bytes: set[bytes] = set()
    for name in sorted(files.staged_legacy):
        raw = files.staged_legacy[name]
        if raw in seen_bytes:
            continue
        seen_bytes.add(raw)
        legacy_sources.append((f"{LOG_DIR}/{name}", list(cut(_decode(raw, name)).entries)))
    legacy_count: Counter[str] = Counter()
    for _, entries in legacy_sources:
        for text, count in Counter(entries).items():
            legacy_count[text] = max(legacy_count[text], count)
    legacy_entries: list[Entry] = []
    emitted: Counter[str] = Counter()
    for path, entries in legacy_sources:
        for text in entries:
            if emitted[text] < legacy_count[text] - in_details[text]:
                emitted[text] += 1
                legacy_entries.append(Entry(text, path))

    merge_order: list[tuple[str, bytes]] = []
    stray_bytes: set[bytes] = set()
    for _, name, raw in files.staged_strays:
        if raw in stray_bytes:
            continue
        stray_bytes.add(raw)
        merge_order.append((f"{LOG_DIR}/{name}", raw))
    if files.legacy is not None and files.legacy_role == "stray":
        merge_order.append((LEGACY_NAME, files.legacy))
    known = set(in_details) | set(legacy_count)
    stray_blocks: list[list[Entry]] = []
    for path, raw in merge_order:
        entries = list(cut(_decode(raw, path)).entries)
        stray_blocks.append([Entry(text, path) for text in entries if text not in known])
        known |= set(entries)
    stray_entries = [entry for block in reversed(stray_blocks) for entry in block]
    return stray_entries + detail_entries + legacy_entries


def read_text(tree: Path) -> str:
    """The concatenation of `read_entries`, for a reader that parses one log text."""
    return "".join(entry.text for entry in read_entries(tree))


# --------------------------------------------------------------------------- validation

@dataclass(frozen=True)
class LogEntry:
    """A validated entry ready to place."""

    heading_date: str
    op: str
    subject: str
    text: str

    @property
    def heading(self) -> str:
        return f"## [{self.heading_date}] {self.op} | {self.subject}"


def render(heading_date: str, op: str, subject: str, body: str) -> str:
    """The entry text: heading, a blank line, the body and a blank line."""
    return f"## [{heading_date}] {op} | {subject}\n\n{body.rstrip(chr(10))}\n\n"


def validate_entry(tree: Path, heading_date: str, op: str, subject: str, body: str) -> LogEntry:
    """Validate the whole request and render one entry, or refuse with nothing written."""
    if not isinstance(heading_date, str) or not real_date(heading_date):
        raise Refusal("the heading date must be a real calendar date written YYYY-MM-DD", "invalid-date")
    if (not subject or subject != subject.strip() or any(ch in subject for ch in "\n\r|\x00")):
        raise Refusal("subject must be one nonempty line without a pipe", "invalid-subject")
    if "\r" in body or "\x00" in body:
        raise Refusal("body contains a carriage return or NUL", "invalid-body")
    if not body.strip():
        raise Refusal("body requires at least one nonempty line", "invalid-body")
    regexes = op_regexes(Path(tree))
    if not op or any(ch.isspace() or ch == "|" for ch in op) or \
            not regexes.current.fullmatch(f"## [{heading_date}] {op} | "):
        raise Refusal("log operation is missing or outside the canonical enum", "invalid-op")
    text = render(heading_date, op, subject, body)
    pieces = cut(text)
    if pieces.outside or len(pieces.entries) != 1 or pieces.entries[0] != text or pieces.open_fence:
        raise Refusal("body must hold no unfenced `## ` line and leave no fence open", "invalid-body")
    return LogEntry(heading_date, op, subject, text)


# --------------------------------------------------------------------------- preflight and repair

@dataclass(frozen=True)
class Plan:
    """A repair planned in memory, and the destination as the repair would leave it.

    `reads` holds the digest of `log.md` and of every file under `log/` the plan read
    (`None` for an absent file). `actions` and `paths` are the repair's steps and the
    tree-relative paths it would create, replace or remove. `proof` carries the first
    split's reconstruction proof and each stray merge's report.
    """

    today: str
    actions: tuple[str, ...]
    reads: dict[str, str | None]
    paths: tuple[str, ...]
    destination: str
    destination_text: str | None
    entry_text: str | None
    proof: dict = field(default_factory=dict)


def destination_for(today: str) -> str:
    """The tree-relative detail file of the month holding `today`."""
    return f"{LOG_DIR}/{today[:7]}.md"


#: Called after each repair step that changes the disk, with the step's name (`7b`, `7e`,
#: `7f`, `7g`, `7h`, `7i`, `8a`, `8d`, `8e`, `8f`, `normalize`, `leftover`). Tests replace
#: it to inject a failure; it does nothing otherwise.
def _after_step(step: str) -> None:
    return None


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _repair_names(names: list[str]) -> list[str]:
    """The names under `log/` a repair reads: every defined name but summaries and temporaries."""
    return sorted(name for name in names if is_defined_name(name) and name != SUMMARY_NAME
                  and not TEMPORARY_NAME.match(name))


def _state(tree: Path) -> tuple[bytes | None, dict[str, tuple[bytes, float]]]:
    """`log.md` and every file a repair reads under `log/`, through pinned no-follow handles."""
    tree_fd = _open_tree(tree)
    try:
        legacy = _read_name(tree_fd, LEGACY_NAME)
        log_fd = _open_log_dir(tree_fd)
    finally:
        os.close(tree_fd)
    found: dict[str, tuple[bytes, float]] = {}
    if log_fd is not None:
        try:
            for name in _repair_names(os.listdir(log_fd)):
                raw = _required(log_fd, name)
                found[name] = (raw, os.stat(name, dir_fd=log_fd, follow_symlinks=False).st_mtime)
        finally:
            os.close(log_fd)
    return legacy, found


def _reads(legacy: bytes | None, found: dict[str, tuple[bytes, float]]) -> dict[str, str | None]:
    reads: dict[str, str | None] = {LEGACY_NAME: _digest(legacy)}
    for name, (raw, _) in found.items():
        reads[f"{LOG_DIR}/{name}"] = _digest(raw)
    return reads


class _MemFS:
    """The log files in memory: the repair runs here first, as its plan."""

    def __init__(self, legacy: bytes | None, found: dict[str, tuple[bytes, float]]):
        self.legacy_bytes = legacy
        self.files = {name: raw for name, (raw, _) in found.items()}
        self.mtimes = {name: mtime for name, (_, mtime) in found.items()}
        self.changed: list[str] = []

    def legacy(self) -> bytes | None:
        return self.legacy_bytes

    def names(self) -> list[str]:
        return sorted(self.files)

    def read(self, name: str) -> bytes | None:
        return self.files.get(name)

    def mtime(self, name: str) -> float:
        return self.mtimes.get(name, 0.0)

    def write(self, name: str, data: bytes, have: bytes | None) -> None:
        if self.files.get(name) != have:
            raise Refusal(f"{LOG_DIR}/{name} changed during this write", "changed")
        self.files[name] = data
        self.changed.append(f"{LOG_DIR}/{name}")

    def unlink(self, name: str) -> None:
        self.files.pop(name, None)
        self.mtimes.pop(name, None)
        self.changed.append(f"{LOG_DIR}/{name}")

    def move(self, source: str, target: str) -> None:
        raw = self.files[source]
        if target in self.files and self.files[target] != raw:
            raise Refusal(f"{LOG_DIR}/{target} exists with other bytes", "staged-conflict")
        self.files[target] = raw
        self.mtimes[target] = self.mtimes.get(source, 0.0)
        self.unlink(source)
        self.changed.append(f"{LOG_DIR}/{target}")

    def stage(self, name: str) -> None:
        raw = self.legacy_bytes
        if raw is None:
            raise Refusal(f"{LEGACY_NAME} disappeared during the repair", "changed")
        if name in self.files:
            if self.files[name] != raw:
                raise Refusal(f"{LEGACY_NAME} changed during the repair", "changed")
        else:
            self.files[name] = raw
            self.mtimes[name] = float("inf")
            self.changed.append(f"{LOG_DIR}/{name}")
        self.legacy_bytes = None
        self.changed.append(LEGACY_NAME)

    def after(self, step: str) -> None:
        return None


class _DiskFS:
    """The log files on disk, through pinned no-follow directory handles."""

    def __init__(self, tree: Path, root: Path):
        self.tree, self.root = tree, root
        self.changed: list[str] = []

    def _log_fd(self, create: bool = False) -> int | None:
        tree_fd = _open_tree(self.tree)
        try:
            fd = _open_log_dir(tree_fd)
            if fd is None and create:
                os.mkdir(LOG_DIR, 0o755, dir_fd=tree_fd)
                fd = _open_log_dir(tree_fd)
            return fd
        finally:
            os.close(tree_fd)

    def legacy(self) -> bytes | None:
        tree_fd = _open_tree(self.tree)
        try:
            return _read_name(tree_fd, LEGACY_NAME)
        finally:
            os.close(tree_fd)

    def names(self) -> list[str]:
        fd = self._log_fd()
        if fd is None:
            return []
        try:
            return _repair_names(os.listdir(fd))
        finally:
            os.close(fd)

    def read(self, name: str) -> bytes | None:
        fd = self._log_fd()
        if fd is None:
            return None
        try:
            return _read_name(fd, name)
        finally:
            os.close(fd)

    def mtime(self, name: str) -> float:
        fd = self._log_fd()
        assert fd is not None
        try:
            return os.stat(name, dir_fd=fd, follow_symlinks=False).st_mtime
        finally:
            os.close(fd)

    def write(self, name: str, data: bytes, have: bytes | None) -> None:
        atomic_replace(self.tree / LOG_DIR / name, data, have, self.tree, self.root)
        self.changed.append(f"{LOG_DIR}/{name}")

    def unlink(self, name: str) -> None:
        fd = self._log_fd()
        assert fd is not None
        try:
            os.unlink(name, dir_fd=fd)
        finally:
            os.close(fd)
        self.changed.append(f"{LOG_DIR}/{name}")

    def move(self, source: str, target: str) -> None:
        """Move without replacing: link the new name, which fails when it exists, then unlink."""
        fd = self._log_fd()
        assert fd is not None
        try:
            try:
                os.link(source, target, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
            except FileExistsError:
                if _read_name(fd, target) != _read_name(fd, source):
                    raise Refusal(f"{LOG_DIR}/{target} exists with other bytes", "staged-conflict")
            self.changed.append(f"{LOG_DIR}/{target}")
            os.unlink(source, dir_fd=fd)
            self.changed.append(f"{LOG_DIR}/{source}")
        finally:
            os.close(fd)

    def stage(self, name: str) -> None:
        """Rename `log.md` to `name` in one rename, or unlink it when `name` holds its bytes."""
        tree_fd = _open_tree(self.tree)
        log_fd: int | None = None
        try:
            log_fd = self._log_fd(create=True)
            assert log_fd is not None
            if _exists(log_fd, name):
                if _read_name(log_fd, name) != _read_name(tree_fd, LEGACY_NAME):
                    raise Refusal(f"{LEGACY_NAME} changed during the repair", "changed")
                os.unlink(LEGACY_NAME, dir_fd=tree_fd)
            else:
                os.rename(LEGACY_NAME, name, src_dir_fd=tree_fd, dst_dir_fd=log_fd)
                self.changed.append(f"{LOG_DIR}/{name}")
            self.changed.append(LEGACY_NAME)
        finally:
            if log_fd is not None:
                os.close(log_fd)
            os.close(tree_fd)

    def after(self, step: str) -> None:
        _after_step(step)


class _Repair:
    """The first split and the stray merges, run against one file system view."""

    def __init__(self, fs, today: str, tree: Path):
        self.fs, self.today, self.tree = fs, today, tree
        self.actions: list[str] = []
        self.proof: dict = {"split": None, "merges": []}
        self._regexes: OpRegexes | None = None

    def historical(self) -> re.Pattern[str]:
        if self._regexes is None:
            self._regexes = op_regexes(self.tree)
        return self._regexes.historical

    # -- sources

    def check_source(self, raw: bytes, path: str) -> Cut:
        """Cut a source, prove its reconstruction and check every heading and its fences."""
        text = _decode(raw, path)
        pieces = cut(text)
        if not reconstructs(text, pieces):  # pragma: no cover - the cutter keeps every byte
            raise Refusal(f"{path}: the cut entries do not reconstruct the file", "reconstruction")
        for item in pieces.entries:
            heading = item.split("\n", 1)[0].removesuffix("\r")
            parsed = HEADING.match(heading)
            if parsed is None or not real_date(parsed.group(1)) or not self.historical().match(heading):
                raise Refusal(f"{path}: the heading {heading!r} fails the section 6 historical-reader "
                              "regex or carries a date that is not a real calendar date; edit the "
                              "heading and rerun the repair", "malformed-heading")
        if pieces.open_fence and pieces.entries:
            heading = pieces.entries[-1].split("\n", 1)[0]
            raise Refusal(f"{path}: the entry {heading!r} ends inside an open fence; close the "
                          "fence and rerun the repair", "open-fence")
        return pieces

    def stage(self, kind: str, planned: bytes) -> str:
        """Stage `log.md` under the digest of `planned`, then name it by the bytes it holds."""
        name = f".{kind}-{_sha(planned)}.md"
        self.fs.stage(name)
        raw = self.fs.read(name)
        if raw is None:  # pragma: no cover - the staged name was just written
            raise Refusal(f"{LOG_DIR}/{name} disappeared during the repair", "changed")
        actual = f".{kind}-{_sha(raw)}.md"
        if actual != name:
            self.fs.move(name, actual)
        return actual

    def detail_entries(self) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for name in self.fs.names():
            if DETAIL_NAME.match(name):
                raw = self.fs.read(name) or b""
                found += [(item, name) for item in cut(_decode(raw, f"{LOG_DIR}/{name}")).entries]
        return found

    # -- the whole repair

    def run(self) -> None:
        self.normalize()
        names = self.fs.names()
        staged_legacy = [name for name in names if STAGED_LEGACY_NAME.match(name)]
        staged_strays = [name for name in names if STAGED_STRAY_NAME.match(name)]
        transactions = [name for name in names if TRANSACTION_NAME.match(name)]
        completion = COMPLETION_NAME in names
        if len(staged_legacy) > 1:
            raise Refusal("the log holds distinct staged legacy files: "
                          + ", ".join(f"{LOG_DIR}/{name}" for name in staged_legacy)
                          + "; keep the one that is the legacy log and move the others aside",
                          "legacy-conflict")
        if staged_legacy:
            legacy_raw = self.fs.read(staged_legacy[0])
            for stray in staged_strays:
                if self.fs.read(stray) == legacy_raw:
                    raise Refusal(f"{LOG_DIR}/{staged_legacy[0]} and {LOG_DIR}/{stray} hold equal bytes; "
                                  "decide which one the log keeps", "legacy-conflict")
            if completion:
                raise Refusal(f"{LOG_DIR}/{staged_legacy[0]} sits beside the completion record "
                              f"{LOG_DIR}/{COMPLETION_NAME}; no crash leaves that state", "legacy-conflict")
        if completion:
            for name in transactions:
                self.fs.unlink(name)
                self.fs.after("leftover")
                self.actions.append(f"remove-leftover:{LOG_DIR}/{name}")
        else:
            if len(transactions) > 1:
                raise Refusal("the log holds more than one split transaction file: "
                              + ", ".join(f"{LOG_DIR}/{name}" for name in transactions), "legacy-conflict")
            self.first_split(staged_legacy[0] if staged_legacy else None,
                             transactions[0] if transactions else None)
        order = sorted(staged_strays, key=lambda name: (self.fs.mtime(name), name))
        for name in order:
            self.merge(name)
        legacy = self.fs.legacy()
        if legacy is not None:
            self.check_source(legacy, LEGACY_NAME)
            name = self.stage("stray", legacy)
            self.fs.after("8a")
            self.merge(name)

    def normalize(self) -> None:
        """Name each staged file by the digest of its bytes; one name per byte string."""
        for name in self.fs.names():
            kind = "legacy" if STAGED_LEGACY_NAME.match(name) else "stray" if STAGED_STRAY_NAME.match(name) else None
            if kind is None:
                continue
            raw = self.fs.read(name)
            if raw is None:
                continue
            actual = f".{kind}-{_sha(raw)}.md"
            if actual != name:
                self.fs.move(name, actual)
                self.fs.after("normalize")
                self.actions.append(f"normalize:{LOG_DIR}/{name}")

    # -- the first split (approach 7)

    def first_split(self, staged: str | None, transaction: str | None) -> None:
        if staged is None and transaction is None:
            legacy = self.fs.legacy()
            if legacy is None:
                self.fs.write(COMPLETION_NAME, completion_bytes(None, {}), None)
                self.actions.append("record-completion")
                return
            self.check_source(legacy, LEGACY_NAME)
            staged = self.stage("legacy", legacy)
            self.fs.after("7b")
        if transaction is None:
            assert staged is not None
            transaction = self.write_transaction(staged)
        self.apply_transaction(staged, transaction)

    def split_targets(self, pieces: Cut) -> tuple[list[dict], dict[str, int], dict]:
        """Group entry positions by heading month; each is placed only beyond the detail files."""
        held = Counter(text for text, _ in self.detail_entries())
        wanted = Counter(pieces.entries)
        emitted: Counter[str] = Counter()
        by_month: dict[str, list[int]] = {}
        per_month: Counter[str] = Counter()
        placed = 0
        for position, text in enumerate(pieces.entries):
            month = HEADING.match(text.split("\n", 1)[0].removesuffix("\r")).group(1)[:7]
            per_month[month] += 1
            if emitted[text] < wanted[text] - held[text]:
                emitted[text] += 1
                by_month.setdefault(month, []).append(position)
                placed += 1
        targets: list[dict] = []
        for month in sorted(by_month):
            name = f"{month}.md"
            before = self.fs.read(name)
            after = self.render_target(name, before, pieces, by_month[month])
            targets.append({"name": name, "positions": by_month[month],
                            "before": _digest(before), "after": _sha(after)})
        kept = None
        if pieces.outside:
            outside = pieces.outside.encode("utf-8")
            kept = f".kept-{_sha(outside)}.txt"
            current = self.fs.read(kept)
            if current is not None and current != outside:
                raise Refusal(f"{LOG_DIR}/{kept} holds bytes other than its name", "migration-conflict")
            targets.append({"name": kept, "positions": [], "before": _digest(current), "after": _sha(outside)})
        stats = {"entries": len(pieces.entries), "placed": placed,
                 "already_held": len(pieces.entries) - placed, "outside_bytes": len(pieces.outside.encode("utf-8")),
                 "kept_file": None if kept is None else f"{LOG_DIR}/{kept}"}
        return targets, dict(sorted(per_month.items())), stats

    def render_target(self, name: str, before: bytes | None, pieces: Cut, positions: list[int]) -> bytes:
        if KEPT_NAME.match(name):
            return pieces.outside.encode("utf-8")
        base = _decode(before, f"{LOG_DIR}/{name}") if before is not None else detail_header(name[:-3])
        placing = [pieces.entries[position] for position in positions]
        rendered = insert(base, placing)
        check_insertion(base, rendered, placing, f"{LOG_DIR}/{name}")
        return rendered.encode("utf-8")

    def write_transaction(self, staged: str) -> str:
        raw = self.fs.read(staged)
        assert raw is not None
        digest = _sha(raw)
        pieces = self.check_source(raw, f"{LOG_DIR}/{staged}")
        targets, per_month, stats = self.split_targets(pieces)
        record = {"format": "crux.operation-log-split-transaction.v1", "legacy_sha256": digest,
                  "entries_per_month": per_month, "targets": targets}
        name = f".split-{digest}.json"
        self.fs.write(name, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"), None)
        self.fs.after("7e")
        self.proof["split"] = {"legacy_sha256": digest, "legacy_bytes": len(raw),
                               "entries_per_month": per_month, "reconstruction_equal": True, **stats}
        self.actions.append(f"split:{LOG_DIR}/{staged}")
        return name

    def apply_transaction(self, staged: str | None, transaction: str) -> None:
        raw = self.fs.read(transaction)
        digest = transaction[len(".split-"):-len(".json")]
        try:
            record = json.loads(_decode(raw or b"", f"{LOG_DIR}/{transaction}"))
            targets = record["targets"]
            per_month = record["entries_per_month"]
        except (ValueError, KeyError, TypeError) as exc:
            raise Refusal(f"{LOG_DIR}/{transaction} is not a split transaction file", "migration-conflict") from exc
        if staged is not None and staged != f".legacy-{digest}.md":
            raise Refusal(f"{LOG_DIR}/{staged} does not belong to {LOG_DIR}/{transaction}", "migration-conflict")
        pieces = None
        if staged is not None:
            source = self.fs.read(staged)
            assert source is not None
            pieces = self.check_source(source, f"{LOG_DIR}/{staged}")
        if self.proof["split"] is None:
            self.proof["split"] = {"legacy_sha256": digest, "entries_per_month": per_month, "resumed": True}
            self.actions.append(f"resume-split:{LOG_DIR}/{transaction}")
        for target in targets:
            name = target["name"]
            current = self.fs.read(name)
            if _digest(current) == target["after"]:
                continue
            conflict = Refusal(f"{LOG_DIR}/{name} holds bytes the split neither started from nor wrote; "
                               "migration-conflict: restore it or move it aside, then rerun the repair",
                               "migration-conflict")
            if _digest(current) != target["before"] or pieces is None:
                raise conflict
            want = self.render_target(name, current, pieces, list(target["positions"]))
            if _sha(want) != target["after"]:
                raise conflict
            self.fs.write(name, want, current)
            self.fs.after("7f")
        if staged is not None:
            self.fs.unlink(staged)
            self.fs.after("7g")
        self.fs.write(COMPLETION_NAME, completion_bytes(digest, per_month), self.fs.read(COMPLETION_NAME))
        self.fs.after("7h")
        self.fs.unlink(transaction)
        self.fs.after("7i")

    # -- the stray merge (approach 8)

    def merge(self, name: str) -> None:
        raw = self.fs.read(name)
        assert raw is not None
        pieces = self.check_source(raw, f"{LOG_DIR}/{name}")
        held = {}
        for text, holder in self.detail_entries():
            held.setdefault(text, holder)
        moved = [text for text in pieces.entries if text not in held]
        skipped = [{"position": position, "file": f"{LOG_DIR}/{held[text]}"}
                   for position, text in enumerate(pieces.entries) if text in held]
        kept = None
        if pieces.outside:
            outside = pieces.outside.encode("utf-8")
            kept = f".kept-{_sha(outside)}.txt"
            if self.fs.read(kept) is None:
                self.fs.write(kept, outside, None)
                self.fs.after("8d")
        destination = f"{self.today[:7]}.md"
        if moved:
            current = self.fs.read(destination)
            base = _decode(current, f"{LOG_DIR}/{destination}") if current is not None else detail_header(self.today[:7])
            rendered = insert(base, moved)
            check_insertion(base, rendered, moved, f"{LOG_DIR}/{destination}")
            self.fs.write(destination, rendered.encode("utf-8"), current)
            self.fs.after("8e")
        self.fs.unlink(name)
        self.fs.after("8f")
        self.actions.append(f"merge:{LOG_DIR}/{name}")
        self.proof["merges"].append({"stray": f"{LOG_DIR}/{name}", "stray_sha256": _sha(raw),
                                     "entries": len(pieces.entries), "moved": len(moved),
                                     "into": f"{LOG_DIR}/{destination}" if moved else None,
                                     "skipped": skipped,
                                     "kept_file": None if kept is None else f"{LOG_DIR}/{kept}",
                                     "reconstruction_equal": True})


def _dedupe(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(paths))


def plan_repair(tree: Path, today: str, entry_text: str | None = None) -> Plan:
    """Plan the whole repair in memory and write nothing; refuse as `repair` would."""
    tree = Path(tree)
    if not real_date(today):
        raise Refusal("today must be a real date written YYYY-MM-DD", "invalid-today")
    legacy, found = _state(tree)
    reads = _reads(legacy, found)
    memory = _MemFS(legacy, found)
    work = _Repair(memory, today, tree)
    work.run()
    destination = destination_for(today)
    reads.setdefault(f"{LOG_DIR}/{COMPLETION_NAME}", None)
    reads.setdefault(destination, None)
    raw = memory.read(destination.split("/", 1)[1])
    destination_text = None if raw is None else _decode(raw, destination)
    return Plan(today, tuple(work.actions), reads, tuple(_dedupe(memory.changed)), destination,
                destination_text, entry_text, work.proof)


def preflight(tree: Path, today: str, entry: LogEntry) -> Plan:
    """Plan the repair and verify the entry's insertion into the destination it would leave.

    Every file it plans from, older detail files included, is read through the pinned
    no-follow reader, so a non-regular file or a symlinked `log/` refuses here, before any
    repair or caller write. A heading or fence the split or a merge would refuse on refuses
    here too. A refusing preflight writes nothing.
    """
    plan = plan_repair(tree, today, entry.text)
    base = plan.destination_text if plan.destination_text is not None else detail_header(today[:7])
    check_insertion(base, insert(base, [entry.text]), [entry.text], plan.destination)
    return plan


def completion_bytes(legacy_sha256: str | None, per_month: dict[str, int]) -> bytes:
    """The completion record of the first split."""
    record = {"format": COMPLETION_FORMAT, "legacy_sha256": legacy_sha256,
              "entries_per_month": dict(sorted(per_month.items()))}
    return (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")


def repair(tree: Path, plan: Plan, root: Path | None = None) -> list[str]:
    """Run the planned repair; return the tree-relative paths it created, replaced or removed.

    It refuses with nothing written when a log file differs from the plan's read. It then
    runs the first split while the completion record is absent and one stray merge per
    staged stray and stray `log.md`, each step re-reading the disk, so a crash at any step
    leaves a state the next repair resumes. A refusal after a step carries the paths
    changed so far as `changed`. When the plan carries an entry, the insertion check runs
    again against the destination as the repair left it, before any caller write.
    """
    tree = Path(tree)
    root = Path(root) if root is not None else tree.parent
    legacy, found = _state(tree)
    current = _reads(legacy, found)
    keys = set(plan.reads) | set(current)
    stale = sorted(rel for rel in keys if plan.reads.get(rel) != current.get(rel))
    if stale:
        raise Refusal("a planned log file changed after preflight: " + ", ".join(stale)
                      + "; rerun the write", "plan-stale")
    disk = _DiskFS(tree, root)
    try:
        _Repair(disk, plan.today, tree).run()
        if plan.entry_text is not None:
            _verify_destination(tree, plan.destination, plan.entry_text)
    except Refusal as exc:
        exc.changed = _dedupe(disk.changed)  # type: ignore[attr-defined]
        raise
    return _dedupe(disk.changed)


def _destination_text(tree: Path, destination: str) -> tuple[str | None, bytes | None]:
    tree_fd = _open_tree(tree)
    try:
        log_fd = _open_log_dir(tree_fd)
    finally:
        os.close(tree_fd)
    if log_fd is None:
        return None, None
    try:
        raw = _read_name(log_fd, destination.split("/", 1)[1])
    finally:
        os.close(log_fd)
    return (None if raw is None else _decode(raw, destination)), raw


def _verify_destination(tree: Path, destination: str, entry_text: str) -> None:
    text, _ = _destination_text(tree, destination)
    base = text if text is not None else detail_header(destination[len(LOG_DIR) + 1:-3])
    check_insertion(base, insert(base, [entry_text]), [entry_text], destination)


# --------------------------------------------------------------------------- the write

def left_strays(tree: Path) -> list[str]:
    """Tree-relative strays present now: a `log.md` and staged strays under `log/`."""
    files = _gather(Path(tree))
    found = [LEGACY_NAME] if files.legacy is not None else []
    return found + [f"{LOG_DIR}/{name}" for _, name, _ in files.staged_strays]


def insert_entry(tree: Path, entry: LogEntry, today: str, root: Path | None = None) -> dict:
    """Add `entry` to the detail file of the month holding `today`, or report where it is.

    It runs no repair. Its only refusals are the insertion check and the replacement's
    changed-file check.
    """
    tree = Path(tree)
    root = Path(root) if root is not None else tree.parent
    strays = left_strays(tree)
    for held in read_entries(tree):
        if held.text == entry.text:
            return {"status": "recorded", "file": held.path, "changed": [], "left_strays": strays}
    destination = destination_for(today)
    text, raw = _destination_text(tree, destination)
    base = text if text is not None else detail_header(today[:7])
    rendered = insert(base, [entry.text])
    check_insertion(base, rendered, [entry.text], destination)
    atomic_replace(tree / destination, rendered.encode("utf-8"), raw, tree, root)
    return {"status": "written", "file": destination, "changed": [destination], "left_strays": strays}


def append_entry(tree: Path, root: Path, heading_date: str, op: str, subject: str, body: str,
                 today: str) -> dict:
    """Validate, preflight, repair and insert in one process, with no caller write between."""
    tree, root = Path(tree), Path(root)
    changed: list[str] = []
    result: dict = {"status": "refused", "file": None, "left_strays": [], "error": None, "code": None}
    try:
        entry = validate_entry(tree, heading_date, op, subject, body)
        plan = preflight(tree, today, entry)
        changed += repair(tree, plan, root)
        placed = insert_entry(tree, entry, today, root)
        changed += placed["changed"]
        result.update(status=placed["status"], file=placed["file"], left_strays=placed["left_strays"])
    except Refusal as exc:
        changed += getattr(exc, "changed", [])
        result.update(error=str(exc), code=exc.code)
    prefix = tree.relative_to(root).as_posix()
    result["changed_paths"] = [f"{prefix}/{rel}" for rel in changed]
    if result["file"] is not None:
        result["file"] = f"{prefix}/{result['file']}"
    result["left_strays"] = [f"{prefix}/{rel}" for rel in result["left_strays"]]
    return result


def atomic_replace(path: Path, want: bytes, have: bytes | None, tree: Path, root: Path) -> None:
    """Replace through pinned, no-follow directory handles.

    The admitted parents are the tree's `journal/` and `log/`; `log/` is created when absent.
    The pathname is checked again just before the descriptor-relative rename, so a swapped
    symlink cannot redirect the temporary or final write. The file must still hold `have`.
    """
    try:
        tree_parts = tree.relative_to(root).parts
        parent_parts = path.parent.relative_to(tree).parts
    except ValueError as exc:
        raise Refusal(f"{path.name} is outside the repository tree", "unsafe-path") from exc
    if not tree_parts or parent_parts not in (("journal",), (LOG_DIR,)):
        raise Refusal(f"{path.name} has an unsafe parent", "unsafe-path")

    opened: list[int] = []
    links: list[tuple[int, str, int]] = []
    temporary: str | None = None
    try:
        first = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened.append(first)
        parent_fd = first
        components = (*root.parts[1:], *tree_parts, *parent_parts)
        for position, component in enumerate(components):
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            try:
                child = os.open(component, flags, dir_fd=parent_fd)
            except FileNotFoundError:
                if position != len(components) - 1 or component != LOG_DIR:
                    raise
                os.mkdir(component, 0o755, dir_fd=parent_fd)
                child = os.open(component, flags, dir_fd=parent_fd)
            except OSError as exc:
                raise Refusal(f"{component} is a symlink or not a directory", "unsafe-path") from exc
            opened.append(child)
            links.append((parent_fd, component, child))
            parent_fd = child

        def check_binding() -> None:
            for ancestor_fd, component, child_fd in links:
                name_stat = os.stat(component, dir_fd=ancestor_fd, follow_symlinks=False)
                fd_stat = os.fstat(child_fd)
                if (not stat.S_ISDIR(name_stat.st_mode) or
                        (name_stat.st_dev, name_stat.st_ino) != (fd_stat.st_dev, fd_stat.st_ino)):
                    raise Refusal(f"{component} directory changed during this write", "changed")

        check_binding()
        current, old_mode = read_at(parent_fd, path.name)
        if current != have:
            raise Refusal(f"{path.name} changed during this write", "changed")
        temp_name = TEMPORARY_PREFIX + secrets.token_hex(12)
        temp_fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                          0o644, dir_fd=parent_fd)
        temporary = temp_name
        with os.fdopen(temp_fd, "wb") as handle:
            handle.write(want)
            if old_mode is not None:
                os.fchmod(handle.fileno(), old_mode)
        check_binding()
        if read_at(parent_fd, path.name)[0] != have:
            raise Refusal(f"{path.name} changed during this write", "changed")
        os.replace(temporary, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        temporary = None
    finally:
        if temporary is not None and opened:
            try:
                os.unlink(temporary, dir_fd=opened[-1])
            except FileNotFoundError:
                pass
        for fd in reversed(opened):
            os.close(fd)


# --------------------------------------------------------------------------- the commit step

def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True)


def log_commit_paths(root: Path, tree: Path) -> dict:
    """Read-only: the log paths a commit step commits and the index entries it resets first.

    `commit_paths` holds every listed path that HEAD or the work tree holds; `restore_paths`
    every listed path that the work tree does not hold. A path only the index holds is in
    `restore_paths` alone, because `git commit --only` refuses a pathspec that matches nothing.
    Outside a git work tree both lists are empty.
    """
    root, tree = Path(root), Path(tree)
    prefix = tree.relative_to(root).as_posix()
    scope = [f"{prefix}/{LEGACY_NAME}", f"{prefix}/{LOG_DIR}"]
    if _git(root, "rev-parse", "--is-inside-work-tree").returncode:
        return {"commit_paths": [], "restore_paths": []}
    status = _git(root, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all",
                  "--", *scope)
    if status.returncode:
        raise Refusal(f"git status failed: {status.stderr.decode('utf-8', 'replace').strip()}", "git")
    listed: list[str] = []
    for record in status.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if len(record) < 4:
            continue
        path = record[3:]
        name = path.rsplit("/", 1)[-1]
        if path == f"{prefix}/{LOG_DIR}/{SUMMARY_NAME}" or TEMPORARY_NAME.match(name):
            continue
        if path not in listed:
            listed.append(path)
    tree_listing = _git(root, "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", *scope)
    in_head = set(tree_listing.stdout.decode("utf-8", "surrogateescape").split("\0")) if not tree_listing.returncode else set()
    commit = [path for path in listed if path in in_head or os.path.lexists(root / path)]
    restore = [path for path in listed if not os.path.lexists(root / path)]
    return {"commit_paths": sorted(commit), "restore_paths": sorted(restore)}


def commit_step(root: Path, own_paths: list[str], commit_paths: list[str], restore_paths: list[str],
                message: str) -> dict:
    """Reset `restore_paths` to HEAD in the index, then commit own paths with `commit_paths`.

    A run whose combined path list is empty stops after the restore and commits nothing.
    """
    root = Path(root)
    if restore_paths:
        done = _git(root, "restore", "--staged", "--quiet", "--", *restore_paths)
        if done.returncode:
            raise Refusal(f"git restore --staged failed: {done.stderr.decode('utf-8', 'replace').strip()}", "git")
    paths = list(dict.fromkeys([*own_paths, *commit_paths]))
    if not paths:
        return {"restored": list(restore_paths), "committed": [], "commit": None}
    added = _git(root, "add", "-A", "--", *paths)
    if added.returncode:
        raise Refusal(f"git add failed: {added.stderr.decode('utf-8', 'replace').strip()}", "git")
    staged = _git(root, "diff", "--cached", "--quiet", "--", *paths)
    if staged.returncode == 0:
        return {"restored": list(restore_paths), "committed": [], "commit": None}
    made = _git(root, "commit", "--only", "-m", message, "--", *paths)
    if made.returncode:
        raise Refusal(f"git commit failed: {made.stderr.decode('utf-8', 'replace').strip()}", "git")
    head = _git(root, "rev-parse", "HEAD").stdout.decode().strip()
    return {"restored": list(restore_paths), "committed": paths, "commit": head}


# --------------------------------------------------------------------------- the summary

#: The file header `summary.md` starts with.
SUMMARY_HEADER = ("# Operations log summary\n\n"
                  "GENERATED regions are rewritten by `generate-log-summary.py`; other text is kept.\n\n")
ROLLUP = "rollup"
ROLLUP_COLUMNS = ("| Month | Entries | First heading date | Last heading date | Most frequent ops |\n"
                  "|---|---|---|---|---|\n")
_MARKER = re.compile(r"^<!-- (BEGIN|END) GENERATED: log-summary (rollup|[0-9]{4}-(?:0[1-9]|1[0-2])) -->$")
_MARKER_LIKE = re.compile(r"^\s*<!--\s*(?:BEGIN|END)\s+GENERATED:\s*log-summary")
_MONTH_HEADING = re.compile(r"^## ([0-9]{4}-(?:0[1-9]|1[0-2]))$")
_ADR_ID = re.compile(r"(?<![A-Za-z0-9])ADR-([0-9]{4})(?![0-9])")
_REGION = re.compile(
    r"\A- Detail file: `log/(?P<month>[0-9]{4}-[0-9]{2})\.md`\n"
    r"- sha256: `[0-9a-f]{64}`\n"
    r"- Entries: (?P<entries>[0-9]+)\n"
    r"- First heading date: (?P<first>none|[0-9]{4}-[0-9]{2}-[0-9]{2})\n"
    r"- Last heading date: (?P<last>none|[0-9]{4}-[0-9]{2}-[0-9]{2})\n"
    r"- Ops: (?P<ops>none|[a-z][a-z-]* [0-9]+(?:, [a-z][a-z-]* [0-9]+)*)\n"
    r"- ADRs: (?P<adrs>none|ADR-[0-9]{4}(?:, ADR-[0-9]{4})*)\n\Z")


def summary_marker(kind: str, name: str) -> str:
    """One GENERATED marker line, without its newline. `kind` is BEGIN or END."""
    return f"<!-- {kind} GENERATED: log-summary {name} -->"


def month_of(day: str) -> str:
    """The month, YYYY-MM, that holds the date `day`."""
    return day[:7]


def settled(month: str, today: str) -> bool:
    """Whether `month` is settled on a host whose local date is `today`.

    A month M is settled from the third day of month M+1, so a host in another time zone, or a
    release op recorded the next morning, still lands in M's file before M's summary is written.
    """
    year, number = int(month[:4]), int(month[5:7])
    year, number = (year + 1, 1) if number == 12 else (year, number + 1)
    return today >= f"{year:04d}-{number:02d}-03"


@dataclass(frozen=True)
class MonthStats:
    """What a month's region states. Every value comes from a closed grammar."""

    entries: int
    first: str | None
    last: str | None
    ops: tuple[tuple[str, int], ...]
    adrs: tuple[str, ...]


def month_stats(text: str, historical: re.Pattern[str]) -> tuple[MonthStats, list[str]]:
    """The counts of one detail file, and one error per heading the gate cannot count.

    A heading that fails the historical-reader regex, or carries a date that is not a real
    calendar date, is an error; no subject text reaches the counts except an ADR id of an
    `adr` entry, which must match `ADR-[0-9]{4}`.
    """
    errors: list[str] = []
    dates: list[str] = []
    ops: Counter[str] = Counter()
    adrs: set[int] = set()
    for item in cut(text).entries:
        heading = item.split("\n", 1)[0].removesuffix("\r")
        parsed = HEADING.match(heading)
        if parsed is None or not historical.match(heading) or not real_date(parsed.group(1)):
            errors.append("a heading fails the section 6 historical-reader regex or carries a date "
                          f"that is not a real calendar date: {heading[:160]!r}")
            continue
        day, op, subject = parsed.groups()
        dates.append(day)
        ops[op] += 1
        if op == "adr":
            adrs.update(int(number) for number in _ADR_ID.findall(subject))
    stats = MonthStats(len(dates), min(dates) if dates else None, max(dates) if dates else None,
                       tuple(sorted(ops.items())), tuple(f"ADR-{n:04d}" for n in sorted(adrs)))
    return stats, errors


def render_region(month: str, raw: bytes, stats: MonthStats) -> str:
    """The body of a month's region: the lines between its two markers."""
    ops = ", ".join(f"{op} {count}" for op, count in stats.ops) or "none"
    return (f"- Detail file: `{LOG_DIR}/{month}.md`\n"
            f"- sha256: `{hashlib.sha256(raw).hexdigest()}`\n"
            f"- Entries: {stats.entries}\n"
            f"- First heading date: {stats.first or 'none'}\n"
            f"- Last heading date: {stats.last or 'none'}\n"
            f"- Ops: {ops}\n"
            f"- ADRs: {', '.join(stats.adrs) or 'none'}\n")


def parse_region(body: str) -> MonthStats | None:
    """The values a region body states, or None when the body is not a rendered region."""
    found = _REGION.match(body)
    if found is None:
        return None
    ops: tuple[tuple[str, int], ...] = ()
    if found["ops"] != "none":
        ops = tuple((op, int(count)) for op, count in
                    (pair.rsplit(" ", 1) for pair in found["ops"].split(", ")))
    adrs = () if found["adrs"] == "none" else tuple(found["adrs"].split(", "))
    first = None if found["first"] == "none" else found["first"]
    last = None if found["last"] == "none" else found["last"]
    return MonthStats(int(found["entries"]), first, last, ops, adrs)


def render_rollup(rows: list[tuple[str, MonthStats]]) -> str:
    """The rollup body: one row per month section, newest first, from the regions alone."""
    lines = [ROLLUP_COLUMNS]
    for month, stats in sorted(rows, key=lambda row: row[0], reverse=True):
        top = sorted(stats.ops, key=lambda pair: (-pair[1], pair[0]))[:3]
        frequent = ", ".join(f"{op} {count}" for op, count in top) or "none"
        lines.append(f"| {month} | {stats.entries} | {stats.first or 'none'} | "
                     f"{stats.last or 'none'} | {frequent} |\n")
    return "".join(lines)


@dataclass
class _Region:
    begin: int | None = None
    end: int | None = None

    def complete(self) -> bool:
        return self.begin is not None and self.end is not None


@dataclass
class _Section:
    month: str
    heading: int
    region: _Region = field(default_factory=_Region)


@dataclass
class SummaryDoc:
    """`summary.md` cut into its rollup region, its month sections and its marker errors."""

    lines: list[str]
    rollup: _Region
    sections: list[_Section]
    errors: list[str]

    def body(self, region: _Region) -> str:
        assert region.begin is not None and region.end is not None
        return "".join(self.lines[region.begin + 1:region.end])

    def offset(self, line: int) -> int:
        return sum(len(text) for text in self.lines[:line])

    def replace_body(self, region: _Region, body: str) -> str:
        assert region.begin is not None and region.end is not None
        return ("".join(self.lines[:region.begin + 1]) + body + "".join(self.lines[region.end:]))


def parse_summary(text: str) -> SummaryDoc:
    """Find the month headings and the markers outside fences, and every marker error."""
    lines = _lines(text)
    rollup = _Region()
    sections: list[_Section] = []
    errors: list[str] = []
    fence: tuple[str, int] | None = None
    current: _Section | None = None
    for index, raw_line in enumerate(lines):
        line = _bare(raw_line)
        found_fence = fence_marker(line)
        if fence is not None:
            if closes_fence(found_fence, fence):
                fence = None
            continue
        if found_fence is not None:
            fence = (found_fence[0], found_fence[1])
            continue
        heading = _MONTH_HEADING.match(line)
        if heading:
            current = _Section(heading.group(1), index)
            sections.append(current)
            continue
        found = _MARKER.match(line)
        if found is None:
            if _MARKER_LIKE.match(line):
                errors.append(f"line {index + 1}: a malformed log-summary marker")
            continue
        kind, name = found.groups()
        if name == ROLLUP:
            target = rollup if current is None else None
        else:
            target = current.region if current is not None and current.month == name else None
        if target is None:
            errors.append(f"line {index + 1}: the {kind} marker of {name} is outside its section")
        elif kind == "BEGIN" and target.begin is not None:
            errors.append(f"line {index + 1}: a second BEGIN marker of {name}")
        elif kind == "BEGIN":
            target.begin = index
        elif target.begin is None:
            errors.append(f"line {index + 1}: the END marker of {name} comes before its BEGIN marker")
        elif target.end is not None:
            errors.append(f"line {index + 1}: a second END marker of {name}")
        else:
            target.end = index
    if fence is not None:
        errors.append("a fence left open hides the rest of the file")
    if not rollup.complete():
        errors.append("the rollup region's BEGIN or END marker is missing")
    for section in sections:
        if not section.region.complete():
            errors.append(f"the region of section {section.month} is missing its BEGIN or END marker")
    return SummaryDoc(lines, rollup, sections, errors)


class _NotRegular(Exception):
    """A log input that is not a regular file."""


def _read_log_input(directory_fd: int, name: str) -> bytes:
    """Read one gate input through a no-follow handle. OSError keeps its errno for the lanes."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise _NotRegular(name)
        return handle.read()


@dataclass
class SummaryInputs:
    """The summary gate's declared inputs, read once."""

    log_present: bool = False
    months: list[str] = field(default_factory=list)
    details: dict[str, bytes] = field(default_factory=dict)
    summary: bytes | None = None
    completion: bool = False
    staged_legacy: list[str] = field(default_factory=list)
    transactions: list[str] = field(default_factory=list)
    legacy: bool = False
    findings: list[dict] = field(default_factory=list)


def read_summary_inputs(tree: Path, today: str, prefix: str):
    """Read the summary gate's inputs; the current month's detail file is listed, never read.

    A failed read whose cause is attributable to the file's path, a non-regular file and
    content that is not UTF-8 are document findings. Any other read failure, a `log/` that
    exists and cannot be listed, or a `log/` that is a symlink or not a directory, raises
    `input_lanes.EnvironmentLaneError`. An absent `log/` (ENOENT or ENOTDIR) is no input.
    """
    import input_lanes

    inputs = SummaryInputs()
    failures: list[str] = []
    current = month_of(today)
    try:
        tree_fd = _open_tree(tree)
    except (Refusal, OSError) as exc:
        raise input_lanes.EnvironmentLaneError([f"{prefix}: {exc}"]) from exc
    log_fd: int | None = None
    try:
        try:
            os.stat(LEGACY_NAME, dir_fd=tree_fd, follow_symlinks=False)
            inputs.legacy = True
        except FileNotFoundError:
            inputs.legacy = False
        try:
            details = os.stat(LOG_DIR, dir_fd=tree_fd, follow_symlinks=False)
        except OSError as exc:
            if exc.errno not in input_lanes.ABSENCE_ERRNOS:
                raise input_lanes.EnvironmentLaneError(
                    [input_lanes.environment_reason(f"{prefix}/{LOG_DIR}", exc)]) from exc
            return inputs
        if not stat.S_ISDIR(details.st_mode):
            raise input_lanes.EnvironmentLaneError(
                [f"{prefix}/{LOG_DIR}: is a symlink or not a directory, so it cannot be listed"])
        try:
            log_fd = os.open(LOG_DIR, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=tree_fd)
            names = sorted(os.listdir(log_fd))
        except OSError as exc:
            if log_fd is not None:
                os.close(log_fd)
            raise input_lanes.EnvironmentLaneError(
                [input_lanes.environment_reason(f"{prefix}/{LOG_DIR}", exc)]) from exc
    finally:
        os.close(tree_fd)
    inputs.log_present = True
    try:
        for name in names:
            path = f"{prefix}/{LOG_DIR}/{name}"
            month = name[:7] if DETAIL_NAME.match(name) else None
            if name == COMPLETION_NAME:
                inputs.completion = True
            elif STAGED_LEGACY_NAME.match(name):
                inputs.staged_legacy.append(name)
            elif TRANSACTION_NAME.match(name):
                inputs.transactions.append(name)
            if month is not None:
                inputs.months.append(month)
            if (month is None or month == current) and name != SUMMARY_NAME:
                continue
            try:
                raw = _read_log_input(log_fd, name)
            except _NotRegular:
                inputs.findings.append({"file": path, "error": "is a symlink or not a regular file"})
                continue
            except OSError as exc:
                if input_lanes.is_path_attributable(exc):
                    inputs.findings.append({"file": path, "error": input_lanes.document_reason(exc)})
                else:
                    failures.append(input_lanes.environment_reason(path, exc))
                continue
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                inputs.findings.append({"file": path, "error": input_lanes.document_reason(exc)})
                continue
            if month is None:
                inputs.summary = raw
            else:
                inputs.details[month] = raw
    finally:
        os.close(log_fd)
    if failures:
        raise input_lanes.EnvironmentLaneError(failures, inputs.findings)
    return inputs


def _summary_failure(failures: list[dict], kind: str, code: str, month: str | None, problem: str) -> None:
    failures.append({"kind": kind, "code": code, "month": month, "problem": problem})


def summarize(tree: Path, root: Path, today: str, *, write: bool) -> tuple[int, dict]:
    """Run the summary gate (`write=False`) or the catch-up (`write=True`).

    Returns the exit code and the JSON payload. Raises `input_lanes.EnvironmentLaneError` for
    the environment lane. The gate exits 1 on a region failure (a region or the rollup that
    differs from its derivation, which the catch-up repairs) and on a structure failure (a
    section for a month that is not settled and not past, a second section, a section without a
    detail file, a marker error or an incomplete split, which the catch-up cannot repair). It
    lists each settled month that has a detail file and no section under `pending_months` and
    exits 0 when they are the only finding. It never reads the current month's detail file.

    The catch-up refuses and writes nothing on a document finding, a structure failure, an
    incomplete split, or a legacy `log.md` with no completion record. Otherwise it creates
    `summary.md` when the first settled month with a detail file appears, inserts a section
    for each pending month, rewrites each settled month's region that differs, and regenerates
    the rollup. It changes no byte outside the regions and inserts only the file header and the
    month headings with their separating blank lines.
    """
    tree, root = Path(tree), Path(root)
    prefix = tree.relative_to(root).as_posix()
    rel_summary = f"{prefix}/{LOG_DIR}/{SUMMARY_NAME}"
    inputs = read_summary_inputs(tree, today, prefix)
    base = {"path": rel_summary, "today": today}
    if not inputs.log_present:
        if write and inputs.legacy:
            return 1, {**base, "status": "refused", "code": "legacy-unsplit",
                       "error": f"{prefix}/{LEGACY_NAME} is not split yet; run operation-log.py repair first"}
        payload = {**base, "surface_absent": True, "drift": False, "failures": [], "pending_months": [],
                   "sections": [], "reason": f"{prefix}/{LOG_DIR}/ is absent, so the tree holds no detail file"}
        if write:
            payload["status"] = "unchanged"
        return 0, payload

    findings = list(inputs.findings)
    stats: dict[str, MonthStats] = {}
    if inputs.details:
        try:
            historical = op_regexes(tree).historical
        except Refusal as exc:
            findings.append({"file": f"{prefix}/AGENTS.md", "error": str(exc)})
            historical = None
        for month, raw in sorted(inputs.details.items()):
            if historical is None:
                continue
            stats[month], errors = month_stats(raw.decode("utf-8"), historical)
            findings += [{"file": f"{prefix}/{LOG_DIR}/{month}.md", "error": error} for error in errors]
    text = inputs.summary.decode("utf-8") if inputs.summary is not None else None
    if findings:
        payload = {"path": rel_summary, "validation_errors": findings}
        if write:
            payload["status"] = "refused"
        return 1, payload

    current = month_of(today)
    months = set(inputs.months)
    derived = {month: render_region(month, inputs.details[month], stats[month]) for month in stats}
    doc = parse_summary(text) if text is not None else None
    failures: list[dict] = []
    incomplete = not inputs.completion and bool(inputs.staged_legacy or inputs.transactions)
    if incomplete:
        _summary_failure(failures, "structure", "incomplete-split", None,
                         "the first split is incomplete; run operation-log.py repair")
    present: list[str] = []
    if doc is not None:
        for error in doc.errors:
            _summary_failure(failures, "structure", "marker", None, error)
        counts = Counter(section.month for section in doc.sections)
        for month, count in sorted(counts.items()):
            if count > 1:
                _summary_failure(failures, "structure", "second-section", month,
                                 f"{count} sections for {month}; remove all but one by hand")
        present = [section.month for section in doc.sections]
        for section in doc.sections:
            month = section.month
            if month >= current:
                _summary_failure(failures, "structure", "unsettled-section", month,
                                 f"a section for {month}, which is not settled on {today}; remove it by hand")
            elif month not in months:
                _summary_failure(failures, "structure", "no-detail-file", month,
                                 f"a section for {month}, which has no detail file; remove it by hand")
            elif counts[month] == 1 and section.region.complete() and doc.body(section.region) != derived.get(month):
                _summary_failure(failures, "region", "region", month,
                                 f"the region of {month} differs from its derivation; run generate-log-summary.py")
        if doc.rollup.complete() and doc.body(doc.rollup) != _rollup_of(doc):
            _summary_failure(failures, "region", "rollup", None,
                             "the rollup differs from the sections' regions; run generate-log-summary.py")
    pending = sorted(month for month in months if settled(month, today) and month not in present)
    report = {**base, "drift": bool(failures), "failures": failures, "pending_months": pending,
              "sections": sorted(set(present), reverse=True),
              "settled_months": sorted(month for month in months if settled(month, today))}
    if not write:
        return (1 if failures else 0), report

    structure = [item for item in failures if item["kind"] == "structure"]
    if incomplete:
        return 1, {**report, "status": "refused", "code": "incomplete-split",
                   "error": "the first split is incomplete; run operation-log.py repair first"}
    if inputs.legacy and not inputs.completion:
        return 1, {**report, "status": "refused", "code": "legacy-unsplit",
                   "error": f"{prefix}/{LEGACY_NAME} is not split yet; run operation-log.py repair first"}
    if structure:
        return 1, {**report, "status": "refused", "code": "structure",
                   "error": "a structure failure needs a hand edit of summary.md or operation-log.py repair"}
    if text is None and not pending:
        return 0, {**report, "status": "unchanged", "created": False, "added_months": [],
                   "rewritten_months": [], "rollup_changed": False}

    created = text is None
    new = text if text is not None else (SUMMARY_HEADER + summary_marker("BEGIN", ROLLUP) + "\n"
                                         + ROLLUP_COLUMNS + summary_marker("END", ROLLUP) + "\n")
    for month in sorted(pending, reverse=True):
        new = _insert_section(new, month, derived[month])
    rewritten: list[str] = []
    for month in sorted(derived):
        if not settled(month, today):
            continue
        doc = parse_summary(new)
        section = next((item for item in doc.sections if item.month == month), None)
        if section is not None and doc.body(section.region) != derived[month]:
            new = doc.replace_body(section.region, derived[month])
            if month not in pending:
                rewritten.append(month)
    doc = parse_summary(new)
    rollup = _rollup_of(doc)
    rollup_changed = created or text is None or parse_summary(text).body(parse_summary(text).rollup) != rollup
    new = doc.replace_body(doc.rollup, rollup)
    want = new.encode("utf-8")
    result = {**report, "created": created, "added_months": pending, "rewritten_months": rewritten,
              "rollup_changed": rollup_changed, "pending_months": []}
    if want == inputs.summary:
        return 0, {**result, "status": "unchanged"}
    atomic_replace(tree / LOG_DIR / SUMMARY_NAME, want, inputs.summary, tree, root)
    return 0, {**result, "status": "written"}


def _rollup_of(doc: SummaryDoc) -> str:
    rows = []
    for section in doc.sections:
        if section.region.complete():
            parsed = parse_region(doc.body(section.region))
            if parsed is not None:
                rows.append((section.month, parsed))
    return render_rollup(rows)


def _insert_section(text: str, month: str, body: str) -> str:
    """`text` with a new section for `month` directly above the next older section, or at the end."""
    block = (f"## {month}\n\n{summary_marker('BEGIN', month)}\n{body}"
             f"{summary_marker('END', month)}\n")
    doc = parse_summary(text)
    older = [section for section in doc.sections if section.month < month]
    if older:
        at = doc.offset(max(older, key=lambda section: section.month).heading)
        return text[:at] + block + "\n" + text[at:]
    if not text.endswith("\n"):
        text += "\n"
    if not text.endswith("\n\n"):
        text += "\n"
    return text + block
