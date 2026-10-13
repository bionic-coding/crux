#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6.0,<7"]
# ///
"""adr-provenance.py — write an ADR's provenance record, append owner promotions, list open requests.

WHAT IT DECIDES. Text added to an ADR during the run that accepts it is guidance;
binding text is the ADR as it stood at that run's `base_commit`, plus what the owner promotes.
`record` runs the one diff, between the ADR at `base_commit` and the ADR in the working tree,
and writes the result as `<adrs>/provenance/ADR-NNNN.yaml`. The record grammar, standing after
promotions and the open request live in `adr_provenance.py`; this script only computes the diff
and does the file writes.

SUBCOMMANDS (every one takes `--repo-root DIR`, default "."):

  record --adr ADR-NNNN --run <run snapshot> [--authorized-by ADR-MMMM/<slug>] [--dry-run]
      A relative `--run` path is read against `--repo-root`. Rules match by handle only. A rule
      absent at `base_commit` is guidance. A rule present there is binding at its governs entry
      at `base_commit`; an in-run edit to any of its fields but `handle` and `provenance` is
      guidance. Rules the run deleted are listed in `removed_in_run` and stay binding at their
      base entry until the owner promotes the deletion. The snapshot must carry a `base_commit`
      that is a full lowercase commit id, resolves in this repository, and agrees with the
      snapshot's committed version (`base_commit_pin.divergence`); otherwise the reader refuses
      rather than guessing. `--run` is required: an ADR accepted outside a run has no in-run
      text, so every rule binds at its current wording and no record is written. A record is
      written once; an existing record, a symlinked provenance directory and a target outside
      the adrs directory all refuse.
      SCOPE. A record is written at an ADR's acceptance, inside the run that accepts it. A
      write reads the run's facts from the snapshot as committed at HEAD, never from the
      working tree, and refuses when the snapshot has no committed version. It refuses unless
      the committed `status` is `in_progress`, the run names the ADR, and the ADR's
      `accepted_date` is no earlier than the day before the run's `started_at` date (the date
      is the acceptor's local calendar day and `started_at` is UTC, so one day of slack keeps
      a same-day acceptance inside its run). The run names the ADR by the module-close gate's
      own predicate (`council_records.named_adr`): a prompt artifact, or a path in the
      committed `run-work-witness.json` beside the snapshot, is a file of the ADR under the
      tree's adrs/ or adrs/archive/. `--authorized-by` names an owner-promoted rule whose ADR
      lists the target in `amends` and whose wording names the target. It lifts only the
      in-progress requirement, for a record that promotion grants to an ADR accepted earlier.
      `--dry-run` writes nothing, so it checks no scope and inspects any Accepted ADR. Every
      write and every dry-run refuses a credential-shaped value anywhere in the record, naming
      the field and never the value.

  promote --adr ADR-NNNN --rules <N[,N...]|all> --instruction '<words>' --date YYYY-MM-DD
          [--body] [--dry-run]
      Appends one promotion to the record. Numbers are those `open` prints: the record's rules
      1..R in order, then the rules the run deleted, R+1..R+D. `all` selects every unpromoted
      in-run change. THE CALLER COPIES `--instruction` VERBATIM FROM THE OWNER'S OWN MESSAGE,
      single-quoted so the shell expands nothing, with each single quote inside written '\''.
      This script cannot verify that the words are the owner's. An agent report, a run note or
      a council verdict is never that instruction (rule:owner-promotes-guidance). `--body`
      records that the owner promoted the ADR's in-run body passages; no projection reads it. A
      promotion is never a gate and never pauses a run.

  open
      Prints `{"open": [...]}`: the open request of every record that still has an
      unpromoted in-run change, sorted by ADR id, with its `guidance`, `edited` and `removed`
      lists. An open request is information, so the exit code is 0 whether or not any is open.

EXIT CODES. 0 done. 1 a validation error, with `{"validation_errors": [...]}` on stdout (a
malformed record, or a governs block that does not parse). 2 a refusal or an environment error,
with a message on stderr and nothing written.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import adr_provenance as ap  # noqa: E402
import council_records as cr  # noqa: E402
import secret_scan as ss  # noqa: E402
import summaries_projection as sp  # noqa: E402
from base_commit_pin import divergence  # noqa: E402
from council_records import git_isolated_env  # noqa: E402

_ADR_ARG_RE = re.compile(r"^ADR-[0-9]{4}\Z")
_COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_ADR_FILE_RE = re.compile(r"^(ADR-[0-9]{4})-.+\.md\Z")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_HANDLE_ARG_RE = re.compile(r"^(ADR-[0-9]{4})/[a-z][a-z0-9-]*\Z")
_RULES_RE = re.compile(r"^[0-9]+(?:,[0-9]+)*\Z")
_SYMLINK_MODE = "120000"
_REGULAR_MODES = ("100644", "100755")
_WITNESS_NAME = "run-work-witness.json"


class Refusal(Exception):
    """A refusal or environment error: exit 2, message on stderr, nothing written."""


class _GovernsProblems(Exception):
    def __init__(self, problems: list[dict]):
        self.problems = problems


# ── the diff ────────────────────────────────────────────────────────────────

def classify(current: list[dict], base: list[dict] | None) -> tuple[list[dict], list[dict]]:
    """(rules, removed_in_run) from the current governs entries and the ones at `base_commit`.

    `current` and `base` are lists of `{handle, entry}`, where `entry` is the governs entry
    without its handle. `base` is None when the ADR had no text at `base_commit`, so every rule
    is guidance. Match is by handle only."""
    base_by_handle = {} if base is None else {e["handle"]: e["entry"] for e in base}
    rules = []
    for item in current:
        handle = item["handle"]
        rules.append({"handle": handle,
                      "standing": ap.STANDING_BINDING if handle in base_by_handle else ap.STANDING_GUIDANCE,
                      "entry": item["entry"], "base": base_by_handle.get(handle)})
    present = {e["handle"] for e in current}
    removed = [{"handle": e["handle"], "base": e["entry"]}
               for e in (base or []) if e["handle"] not in present]
    return rules, removed


def frontmatter_of(text: str, source: str) -> dict:
    """The ADR's frontmatter mapping. Invalid YAML, or frontmatter that is not a mapping, is a
    validation error; text with no frontmatter reads as an empty mapping."""
    try:
        fm = sp.read_frontmatter(text)
    except yaml.YAMLError as exc:
        raise _GovernsProblems([{"source_adr": source, "handle": None,
                                 "problem": f"frontmatter is not valid YAML: {exc}"}]) from exc
    if not isinstance(fm, dict):
        raise _GovernsProblems([{"source_adr": source, "handle": None,
                                 "problem": "frontmatter is not a mapping"}])
    return fm


def governs_of(text: str, source: str) -> list[dict]:
    """The `{handle, entry}` pairs of an ADR's governs block, in governs order, where `entry` is
    the governs entry without its handle. A member that is not a mapping with a string handle, a
    field outside the governs set, a field of the wrong type, or a handle named twice is a
    validation error."""
    fm = frontmatter_of(text, source)
    problems, out, seen = [], [], set()
    for raw in sp.raw_governs_entries(fm):
        handle = raw.get("handle") if isinstance(raw, dict) else None
        if not isinstance(handle, str):
            problems.append({"source_adr": source, "handle": None,
                             "problem": "a governs entry needs a mapping with a string handle"})
            continue
        entry = {k: v for k, v in raw.items() if k != "handle"}
        found = ap.entry_problems(entry, source, handle, "governs entry")
        if found:
            problems.extend(found)
        elif handle in seen:
            problems.append({"source_adr": source, "handle": handle,
                             "problem": "governs handle appears twice"})
        else:
            seen.add(handle)
            out.append({"handle": handle, "entry": ap.normal_entry(entry)})
    if problems:
        raise _GovernsProblems(problems)
    return out


# ── git and the tree ────────────────────────────────────────────────────────

def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False,
                              env=git_isolated_env())
    except OSError as exc:
        raise Refusal(f"git cannot run: {exc}") from exc


def _tree(root: Path) -> Path:
    """The adrs directory, proven to resolve inside the repository root."""
    adrs = sp.adrs_dir(root)
    resolved, top = adrs.resolve(), root.resolve()
    if top not in resolved.parents:
        raise Refusal(f"the adrs directory {adrs} resolves outside the repository root")
    return adrs


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _working_adr(adrs: Path, adr: str) -> Path:
    found = sorted(adrs.glob(f"{adr}-*.md")) if adrs.is_dir() else []
    found = [p for p in found if _ADR_FILE_RE.match(p.name)]
    if len(found) != 1:
        raise Refusal(f"expected exactly one {adr}-*.md at the top of {adrs}, found {len(found)}")
    path = found[0]
    if path.is_symlink() or not path.is_file():
        raise Refusal(f"{path.name} is not a regular file")
    return path


def _base_adr(root: Path, base: str, reldir: str, adr: str) -> tuple[str, bytes] | None:
    """(path relative to the root, bytes) of the ADR at `base`, or None when it had no file."""
    listing = _git(root, "ls-tree", "-z", base, "--", f"{reldir}/")
    if listing.returncode != 0:
        raise Refusal(f"git ls-tree failed at {base}: {listing.stderr.decode(errors='replace').strip()}")
    names = []
    for item in filter(None, listing.stdout.split(b"\0")):
        meta, _, path = item.decode("utf-8", errors="replace").partition("\t")
        mode, kind, _sha = meta.split(" ")
        match = _ADR_FILE_RE.match(path.rsplit("/", 1)[-1])
        if kind == "blob" and match and match.group(1) == adr and path.rsplit("/", 1)[0] == reldir:
            names.append((path, mode))
    if not names:
        return None
    if len(names) > 1:
        raise Refusal(f"{adr} has {len(names)} files at {base}; the reader refuses rather than guessing")
    path, mode = names[0]
    if mode == _SYMLINK_MODE:
        raise Refusal(f"{path} is a symlink at {base}")
    blob = _git(root, "cat-file", "blob", f"{base}:./{path}")
    if blob.returncode != 0:
        raise Refusal(f"git cannot read {path} at {base}")
    return path, blob.stdout


def _base_text(data: bytes, adr: str, base: str, path: str) -> str:
    """The base bytes as text. They refuse, rather than read as an ADR with no governs block,
    when they are not strict UTF-8 or their frontmatter is not a non-empty mapping: such bytes
    would classify every rule that stood at `base` as guidance."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refusal(f"{adr} at {base} ({path}) is not valid UTF-8; "
                      "the reader refuses rather than guessing") from None
    if not frontmatter_of(text, adr):
        raise Refusal(f"{adr} at {base} ({path}) has no readable frontmatter "
                      "(for example CRLF line endings); the reader refuses rather than guessing")
    return text


def _read_snapshot(root: Path, run_arg: str) -> tuple[dict, Path, str]:
    """The run snapshot, read only from a regular file inside the repository that is no secret
    location (`secret_scan.check_input_path`). A parse failure is reported by its type and line,
    never with the file's text."""
    path = Path(run_arg)
    path = path if path.is_absolute() else root / path
    code = ss.check_input_path(path, root)
    if code is not None:
        raise Refusal(f"the run snapshot {run_arg} is refused ({code})")
    try:
        rel = _rel(root, path)
    except ValueError:
        raise Refusal(f"the run snapshot {run_arg} is outside the repository root") from None
    if not path.is_file():
        raise Refusal(f"the run snapshot {run_arg} is not a file")
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        raise Refusal(f"the run snapshot {run_arg} is not UTF-8") from None
    except yaml.YAMLError as exc:
        raise Refusal(f"the run snapshot {run_arg} is {ap.yaml_problem(exc)}") from None
    if not isinstance(doc, dict):
        raise Refusal(f"the run snapshot {run_arg} is not a mapping")
    return doc, path, rel


def _checked_base_commit(root: Path, run: dict, run_path: Path) -> str:
    base = run.get("base_commit")
    if not (isinstance(base, str) and _COMMIT_RE.match(base)):
        raise Refusal("the run snapshot's base_commit is absent or not a full lowercase commit id; "
                      "the reader refuses rather than guessing")
    moved = divergence(run, run_path)
    if moved is not None:
        raise Refusal(f"the run snapshot's base_commit {moved[1]!r} diverges from its committed "
                      f"value {moved[0]!r}; the reader refuses rather than guessing")
    if _git(root, "cat-file", "-e", f"{base}^{{commit}}").returncode != 0:
        raise Refusal(f"the run's base_commit {base} does not resolve to a commit in this repository "
                      "(a shallow clone can lack it); the reader refuses rather than guessing")
    return base


# ── scope ───────────────────────────────────────────────────────────────────

def _calendar_day(value) -> datetime.date | None:
    """A frontmatter or snapshot date as a calendar day: a YAML date, a YYYY-MM-DD string, or
    an ISO timestamp (taken in UTC when it carries an offset); anything else None."""
    if isinstance(value, datetime.datetime):
        return (value.astimezone(datetime.UTC) if value.tzinfo else value).date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return (parsed.astimezone(datetime.UTC) if parsed.tzinfo else parsed).date()
    return None


def _committed_blob(root: Path, rel: str) -> bytes | None:
    """The bytes of `rel` as committed at HEAD, or None when HEAD holds no regular file there."""
    listing = _git(root, "ls-tree", "-z", "HEAD", "--", rel)
    if listing.returncode != 0 or not listing.stdout:
        return None
    meta, _, _path = listing.stdout.split(b"\0")[0].decode("utf-8", errors="replace").partition("\t")
    mode, kind, _sha = meta.split(" ")
    if kind != "blob" or mode not in _REGULAR_MODES:
        return None
    blob = _git(root, "cat-file", "blob", f"HEAD:./{rel}")
    return blob.stdout if blob.returncode == 0 else None


def _committed_snapshot(root: Path, run_rel: str) -> dict:
    """[SECURITY:S3] The run snapshot as committed at HEAD: the scope reads the run's status,
    start and named ADR from here, so an uncommitted edit to the snapshot cannot widen it, the
    way `base_commit_pin.divergence` holds `base_commit`. A snapshot with no committed version
    refuses."""
    data = _committed_blob(root, run_rel)
    if data is None:
        raise Refusal(f"the run snapshot {run_rel} has no committed version; commit the snapshot "
                      "before writing its ADR's provenance record")
    try:
        doc = yaml.safe_load(data.decode("utf-8"))
    except UnicodeDecodeError:
        raise Refusal(f"the committed run snapshot {run_rel} is not UTF-8") from None
    except yaml.YAMLError as exc:
        raise Refusal(f"the committed run snapshot {run_rel} is {ap.yaml_problem(exc)}") from None
    if not isinstance(doc, dict):
        raise Refusal(f"the committed run snapshot {run_rel} is not a mapping")
    return doc


def _committed_witness_paths(root: Path, run_rel: str) -> list[str]:
    """The paths of the committed run-work witness beside the snapshot; none when it is absent or
    does not parse, as the module-close gate reads it."""
    rel = f"{run_rel.rsplit('/', 1)[0]}/{_WITNESS_NAME}" if "/" in run_rel else _WITNESS_NAME
    data = _committed_blob(root, rel)
    try:
        entries = json.loads(data).get("entries", []) if data is not None else []
    except (ValueError, AttributeError):
        entries = []
    return [e["path"] for e in entries if isinstance(e, dict) and isinstance(e.get("path"), str)] \
        if isinstance(entries, list) else []


def _names_adr(root: Path, run: dict, witness_paths: list[str], adr: str) -> bool:
    """True when a prompt artifact of the snapshot, or a run-work witness path, names a file of
    `adr` by the module-close gate's predicate (`council_records.named_adr`)."""
    pattern = cr.tree_adr_path(root)
    candidates = list(witness_paths)
    for prompt in run.get("prompts") if isinstance(run.get("prompts"), list) else []:
        artifacts = prompt.get("artifacts") if isinstance(prompt, dict) else None
        candidates += [a for a in (artifacts if isinstance(artifacts, list) else []) if isinstance(a, str)]
    for text in candidates:
        hit = cr.named_adr(root, text, pattern)
        if hit is not None and hit[0] == adr:
            return True
    return False


def _check_authorization(adrs: Path, adr: str, handle: str) -> None:
    """`handle` is an owner-promoted rule whose ADR lists `adr` in `amends` and whose accepted
    wording names `adr`."""
    match = _HANDLE_ARG_RE.match(handle)
    if match is None:
        raise Refusal(f"--authorized-by must be ADR-NNNN/<slug>, got {handle!r}")
    records, _digest = sp.read_provenance(adrs)
    record = records.get(match.group(1))
    if record is None:
        raise Refusal(f"--authorized-by {handle}: {match.group(1)} has no provenance record")
    rule = next((r for r in record["rules"] if r["handle"] == handle), None)
    if rule is None:
        raise Refusal(f"--authorized-by {handle} is not a rule of {match.group(1)}'s provenance record")
    if not ap.effective_rules(record)[handle]["promoted"]:
        raise Refusal(f"--authorized-by {handle}: the owner has not promoted that rule, so {adr} "
                      "gets no provenance record yet")
    if not re.search(rf"(?<![0-9A-Za-z-]){re.escape(adr)}(?![0-9])", rule["entry"]["rule"]):
        raise Refusal(f"--authorized-by {handle}: that rule's wording does not name {adr}")
    authorizing = match.group(1)
    amends = frontmatter_of(_working_adr(adrs, authorizing).read_text(encoding="utf-8"),
                            authorizing).get("amends")
    if not (isinstance(amends, list) and adr in amends):
        raise Refusal(f"--authorized-by {handle}: {authorizing} does not list {adr} in amends")


def _check_scope(root: Path, adrs: Path, adr: str, fm: dict, run_rel: str,
                 authorized_by: str | None) -> None:
    """[SECURITY:S3] Refuse a record outside the scope decided for provenance records: an ADR
    accepted inside the run that names it, written while that run is in progress, or a
    retroactive record an owner-promoted rule grants. Reads tree facts only, never ADR
    numbers, and reads the run's facts from the committed snapshot."""
    run = _committed_snapshot(root, run_rel)
    accepted = _calendar_day(fm.get("accepted_date"))
    if accepted is None:
        raise Refusal(f"{adr} carries no readable accepted_date; the writer refuses rather than guessing")
    started = _calendar_day(run.get("started_at"))
    if started is None:
        raise Refusal("the run snapshot carries no readable started_at; the writer refuses rather than guessing")
    if accepted < started - datetime.timedelta(days=1):
        raise Refusal(f"{adr} was accepted on {accepted}, before its run started on {started}; "
                      "a provenance record is written only for an ADR accepted inside its run")
    if not _names_adr(root, run, _committed_witness_paths(root, run_rel), adr):
        raise Refusal(f"the run snapshot names no {adr} file in its prompt artifacts or its run-work "
                      "witness; a provenance record is written for the run whose ADR module accepted "
                      "the ADR")
    if authorized_by is not None:
        _check_authorization(adrs, adr, authorized_by)
        return
    status = run.get("status")
    if status != "in_progress":
        raise Refusal(f"the run is {status!r}, not in_progress; a provenance record is written at "
                      "acceptance, inside the run. A record an owner promotion grants to an earlier ADR "
                      "names the promoted rule with --authorized-by")


# ── writes ──────────────────────────────────────────────────────────────────

def _provenance_dir(adrs: Path, *, create: bool) -> Path:
    directory = adrs / ap.DIRNAME
    if directory.is_symlink():
        raise Refusal(f"{directory} is a symlink; the provenance directory must be a real directory")
    if directory.exists() and not directory.is_dir():
        raise Refusal(f"{directory} is not a directory")
    if not directory.exists():
        if not create:
            return directory
        directory.mkdir()
    if directory.resolve().parent != adrs.resolve():
        raise Refusal(f"{directory} resolves outside the adrs directory")
    return directory


def _write_atomic(directory: Path, name: str, text: str, *, replace: bool) -> Path:
    """Write `name` in `directory` through a temporary file, never through a link.

    [SECURITY:S5] The temporary file is created by `tempfile.mkstemp`: an unpredictable name,
    opened `O_CREAT|O_EXCL` (and `O_NOFOLLOW` where the platform has it), so a link planted
    beside the record is never followed. A record path that is a link refuses. A first write
    hard-links the temporary file into place without following a link, so it refuses when any
    entry, a dangling link included, appeared at the record path meanwhile. A replacement
    renames over the record path, which replaces a link rather than writing through it."""
    target = directory / name
    if target.is_symlink():
        raise Refusal(f"{target} is a symlink")
    if not replace and os.path.lexists(target):
        raise Refusal(f"{target} already exists; a provenance record is written once")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=directory)
    tmp = Path(tmp_name)
    try:
        os.fchmod(fd, 0o644)          # mkstemp creates 0600; a record lands 0644 like its siblings
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        if replace:
            os.replace(tmp, target)
        else:
            try:
                os.link(tmp, target, follow_symlinks=False)   # refuses an entry that appeared meanwhile
            except FileExistsError:
                raise Refusal(f"{target} already exists; a provenance record is written once") from None
    finally:
        tmp.unlink(missing_ok=True)
    return target


def _refuse_credentials(record: dict) -> None:
    """[SECURITY:S2] A record is committed and a dry-run prints it whole, so a credential shape
    anywhere in it refuses before either. The refusal names the field, never the value."""
    hits = sorted({field for field, _shape in ss.scan_fields(record)})
    if hits:
        raise Refusal(f"the record would carry a credential-shaped value in {', '.join(hits)}; "
                      "nothing written or printed")


def _emit(record: dict) -> None:
    print(json.dumps(record, indent=2, ensure_ascii=False))


# ── subcommands ─────────────────────────────────────────────────────────────

def cmd_record(args, root: Path) -> int:
    adr = args.adr
    if args.run is None:
        raise Refusal("an ADR accepted outside a run has no in-run text; no provenance record is written")
    adrs = _tree(root)
    run, run_path, run_rel = _read_snapshot(root, args.run)
    base = _checked_base_commit(root, run, run_path)
    working = _working_adr(adrs, adr)
    text = working.read_text(encoding="utf-8")
    fm = frontmatter_of(text, adr)
    status = fm.get("status")
    if status != "Accepted":
        raise Refusal(f"{adr} has status {status!r}; only an Accepted ADR gets a provenance record")
    current = governs_of(text, adr)
    reldir = _rel(root, adrs)
    if not args.dry_run:
        _check_scope(root, adrs, adr, fm, run_rel, args.authorized_by)
    found = _base_adr(root, base, reldir, adr)
    if found is None:
        base_path, base_sha, base_entries = None, None, None
    else:
        base_path, data = found
        base_sha = hashlib.sha256(data).hexdigest()
        base_entries = governs_of(_base_text(data, adr, base, base_path), adr)
    rules, removed = classify(current, base_entries)
    record = {"schema": ap.SCHEMA, "adr": adr,
              "run": {"book_id": run.get("book_id"), "run_id": run.get("run_id"), "snapshot": run_rel},
              "base_commit": base, "base_path": base_path, "base_sha256": base_sha,
              "rules": rules, "removed_in_run": removed, "promotions": []}
    rendered = ap.render_record(record)
    _refuse_credentials(record)
    if args.dry_run:
        _emit(record)
        return 0
    directory = _provenance_dir(adrs, create=True)
    target = _write_atomic(directory, f"{adr}.yaml", rendered, replace=False)
    print(json.dumps({"written": _rel(root, target), "adr": adr}))
    return 0


def _select(record: dict, spec: str) -> list[str]:
    """The handles a `--rules` selection names, in the numbering `open` prints."""
    effective = ap.effective_rules(record)
    items = ap.numbered(record)
    if spec == "all":
        return [handle for _n, handle, _item in items if effective[handle]["in_run_edit"]]
    if not _RULES_RE.match(spec):         # int() alone admits other decimal digits, a sign, spaces
        raise Refusal("--rules takes rule numbers like 1,3,5, or all")
    numbers = [int(part) for part in spec.split(",")]
    if len(set(numbers)) != len(numbers):
        raise Refusal("--rules names a rule number twice")
    handles = []
    for number in numbers:
        if not 1 <= number <= len(items):
            raise Refusal(f"rule number {number} is out of range; the record numbers "
                          f"{len(record['rules'])} rules and {len(record['removed_in_run'])} deletions")
        _n, handle, _item = items[number - 1]
        if effective[handle]["promoted"]:
            raise Refusal(f"rule {number} ({handle}) is already promoted")
        if not effective[handle]["in_run_edit"]:
            raise Refusal(f"rule {number} ({handle}) carries no in-run text to promote")
        handles.append(handle)
    return handles


def cmd_promote(args, root: Path) -> int:
    adr = args.adr
    adrs = _tree(root)
    directory = _provenance_dir(adrs, create=False)
    path = directory / f"{adr}.yaml"
    if path.is_symlink() or not path.is_file():
        raise Refusal(f"no provenance record for {adr} at {path}")
    if not args.instruction.strip():
        raise Refusal("--instruction must carry the owner's own words, verbatim")
    if not (_DATE_RE.match(args.date) and _valid_date(args.date)):
        raise Refusal(f"--date must be YYYY-MM-DD, got {args.date!r}")
    record = ap.parse_record(path.read_text(encoding="utf-8"), name=path.name)
    handles = _select(record, args.rules)
    if not handles and not args.body:
        raise Refusal("nothing to promote: the selection holds no rule with unpromoted in-run text "
                      "and --body is not set")
    promotion = {"date": args.date, "instruction": args.instruction, "handles": handles,
                 "body": bool(args.body)}
    updated = {**record, "promotions": [*record["promotions"], promotion]}
    rendered = ap.render_record(updated)
    _refuse_credentials(updated)
    if args.dry_run:
        _emit(updated)
        return 0
    _write_atomic(directory, path.name, rendered, replace=True)
    print(json.dumps({"written": _rel(root, path), "adr": adr, "promoted": handles}))
    return 0


def _valid_date(value: str) -> bool:
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def cmd_open(args, root: Path) -> int:
    records, _digest = sp.read_provenance(_tree(root))
    requests = [req for _adr, rec in sorted(records.items()) if (req := ap.open_request(rec))]
    print(json.dumps({"open": requests}, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adr-provenance.py", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--repo-root", default=".", help="repository root (default: .)")

    rec = sub.add_parser("record", help="write an ADR's provenance record from the run's base_commit")
    common(rec)
    rec.add_argument("--adr", required=True)
    rec.add_argument("--run", metavar="SNAPSHOT",
                     help="required: the accepting run's snapshot path (relative paths read against "
                          "--repo-root); an ADR accepted outside a run gets no record")
    rec.add_argument("--authorized-by", metavar="ADR-NNNN/SLUG",
                     help="an owner-promoted rule whose ADR lists this ADR in amends and whose "
                          "wording names this ADR; lifts only the in-progress requirement")
    rec.add_argument("--dry-run", action="store_true",
                     help="print the record as JSON; write nothing and check no scope")
    pro = sub.add_parser("promote", help="append an owner promotion to a record")
    common(pro)
    pro.add_argument("--adr", required=True)
    pro.add_argument("--rules", required=True,
                     help="the numbers `open` prints (rules, then deletions) like 1,3,5, or all")
    pro.add_argument("--instruction", required=True,
                     help="the owner's words, copied verbatim from the owner's own message; "
                          "an agent report, run note or council verdict is never this instruction")
    pro.add_argument("--date", required=True, help="YYYY-MM-DD")
    pro.add_argument("--body", action="store_true",
                     help="record that the owner promoted the ADR's in-run body passages")
    pro.add_argument("--dry-run", action="store_true", help="print the updated record; write nothing")
    opn = sub.add_parser("open", help="list the open requests records still carry")
    common(opn)

    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        if hasattr(args, "adr") and not _ADR_ARG_RE.match(args.adr):
            raise Refusal(f"--adr must be ADR-NNNN, got {args.adr!r}")
        return {"record": cmd_record, "promote": cmd_promote, "open": cmd_open}[args.command](args, root)
    except Refusal as exc:
        print(f"adr-provenance: {exc}", file=sys.stderr)
        return 2
    except (ap.ProvenanceError, sp.GovernsValidationError, _GovernsProblems) as exc:
        print(json.dumps({"validation_errors": exc.problems}, indent=2, ensure_ascii=False))
        return 1
    except (OSError, ValueError) as exc:
        print(f"adr-provenance: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
