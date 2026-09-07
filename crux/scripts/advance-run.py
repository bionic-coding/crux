# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""advance-run.py — advance a structured `.yaml` promptbook run snapshot by one prompt.

The vendored counterpart to `validate-promptbook.py` for the `run-promptbook`
advance path. Hand-editing a run snapshot across many advances is error-prone,
and a naive re-emit silently drops the run-level trailing fields
(`notes` / `pr_draft` / `summary`) — this script round-trips ALL top-level keys,
so those fields survive every advance (the Issue-3 hazard).

Two modes.

`--outcome` (advance) mutates ONLY the element whose `n == current_prompt`: sets its
`state`/`started`/`completed`/`result`/`artifacts`, then moves the pointer to the
next `pending` element (set `running`) or, if none remain, marks the run `completed`.
`book_content_hash` and every prior element are left untouched.

`--abandon` (abandon) is a RUN-level act, not a per-prompt one (ADR-0077 clause 5(b),
which deleted the per-prompt `blocked_confirmed` flag). It sets run `status: abandoned`
plus an `abandonment` record, and leaves every prompt element's state untouched — a
prompt left `running` or `pending` is the evidence that the run was abandoned mid-flight.
`abandonment.kind: deliberate` is what makes the book archive-eligible while it holds a
non-terminal prompt; the `abandoned` a later run-start writes over a stale run carries
`kind: superseded` and confers no eligibility. An abandonment is recorded when it is
taken and never retrofitted, so this refuses a run that is already terminal.

Neither terminal status — `completed` nor `abandoned` — nulls the book's `current_run`
pointer. Only a book's current run can authorize its archive (ADR-0077 clause 5(b)), so
the pointer survives both terminal paths; `archive-promptbook` is the sole writer that
nulls it, at archival. This script nulls only `current_prompt` on completion.

Both modes pin `base_commit`. It is written once at run start and never rewritten, and
it is the one value the `patch` tier's archive check reads out of the run — so moving it
forward shrinks the diff that check proves. This script refuses to write a snapshot whose
`base_commit` differs from the value in the snapshot's own committed version. The pin
binds from the snapshot's first commit onward; before that there is no committed record
to compare against and the guard makes no claim.

This is the writer end of the pin. `check-blast-radius.py` refuses the same divergence
at the archive gate, since a hand-edited snapshot can be committed without passing
through this script. Both call `base_commit_pin.divergence` — one implementation, so
the two ends cannot disagree about what the committed record is.

New-format `.yaml` only (a `.yaml` without `format_version`, or a `.md` snapshot, is
refused — format conversion is `migrate-promptbooks`' job). It does NOT schema-validate
the snapshot against `run.schema.json` (that is `audit-docs`' job); it guards only the
fields it mutates.

Usage:
    uv run advance-run.py <run-RUN-NNN.yaml> --outcome done|skipped|blocked \
        [--result "one line"] [--artifacts docs/a.md,docs/b.md] \
        [--book <active-book.yaml>]
    uv run advance-run.py <run-RUN-NNN.yaml> --abandon --reason "one line" \
        [--book <active-book.yaml>]

Exit codes (crux convention): 0 clean; 1 usage/validation error (JSON on stdout);
non-zero with empty stdout = crash (stderr).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("advance-run.py requires PyYAML — run via `uv run` (PEP 723 supplies it).\n")
    raise SystemExit(2)

# The pin on `base_commit` has two enforcers — this writer and the archive-time
# containment check — so it has one implementation, imported by both. See
# `base_commit_pin.py` for the no-claim lane and the honest limit.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_commit_pin import divergence  # noqa: E402  (sys.path insert before import)

TERMINAL = ("done", "skipped", "blocked")

# The ONLY line this script may rewrite in a book. Anchored and narrowly scoped on
# purpose: an unanchored `current_prompt:` match would also hit a nested or
# commented occurrence. `current_run` is deliberately absent — see the writer below.
BOOK_CURRENT_PROMPT_RE = r"^current_prompt: .*$"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(json.dumps({"error": msg}))
    raise SystemExit(1)


def _dump(doc: dict) -> str:
    def str_presenter(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|" if "\n" in data else None)

    class D(yaml.Dumper):
        pass

    def flow_list(dumper, data):
        if all(isinstance(x, str) for x in data) and len(data) <= 8:
            return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
        return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=False)

    yaml.add_representer(str, str_presenter, Dumper=D)
    yaml.add_representer(list, flow_list, Dumper=D)
    return yaml.dump(doc, Dumper=D, sort_keys=False, allow_unicode=True, width=100)


def _check_base_commit_pin(run: dict, run_path: Path) -> None:
    """Refuse to write a snapshot whose ``base_commit`` diverges from its committed
    record. ``base_commit`` is written once at run start and never rewritten.

    It is the one value the `patch` tier's archive check reads out of the run, so
    moving it forward shrinks the diff that check proves — which is precisely what an
    overshooting run is motivated to do. This mirrors the never-retrofit guard on
    `abandonment`: a value recorded once is not rewritten by this tool.

    This is the WRITER end of a two-ended pin. `check-blast-radius.py` refuses the
    same divergence at the archive gate, because a hand-edited snapshot can be
    committed without ever passing through this tool. Both ends call
    `base_commit_pin.divergence`, so neither can drift from the other's idea of the
    committed record.

    HONEST LIMIT: the pin binds from the snapshot's first commit onward. In the
    window between run start and that commit there is no committed record, so nothing
    holds the value, and this returns without a claim."""
    diverged = divergence(run, run_path)
    if diverged is None:
        return
    pinned, live = diverged
    _fail(
        f"base_commit is written once at run start and never rewritten, but this "
        f"snapshot's value diverges from its committed record (committed {pinned!r}, "
        f"on disk {live!r}). It is the evidence source the patch tier's archive check "
        f"reads, so moving it shrinks the diff that check proves. Restore the committed "
        f"value, or abandon the run and author a successor book."
    )


def _ensure_trailing_fields(run: dict) -> dict:
    """Existing notes/pr_draft/summary survive via the whole-dict re-emit in main()
    (yaml.dump over the full `run`); this only ensures the keys EXIST (absent → ""),
    so a fresh snapshot that never populated them stays schema-clean."""
    for k in ("notes", "pr_draft", "summary"):
        run.setdefault(k, "")
    return run


def abandon(run: dict, reason: str) -> dict:
    """Record a DELIBERATE abandonment of the run (a run-level act; the per-prompt
    archive-eligibility flag is retired). Sets the run-level
    `status`/`abandonment`/`completed_at`/`current_prompt` and touches no prompt
    element — the non-terminal prompt left behind is the evidence.

    Refuses to retrofit: an abandonment is recorded at the moment it is taken, so a
    run that is already `completed` or `abandoned`, or that already carries an
    `abandonment` record, is rejected.

    EVERY guard runs before the first mutation, matching ``advance()``. That order is
    load-bearing here in a way it is not elsewhere: because an abandonment is never
    retrofitted, a `status: abandoned` that reached disk from a half-applied call
    would make the retrofit guard refuse every later attempt, and the run could then
    archive by neither path. A validation that runs after the write is not a
    validation."""
    if not reason or not reason.strip():
        _fail("--abandon requires a non-empty --reason")
    if not isinstance(run.get("prompts"), list) or not run["prompts"]:
        _fail("malformed run snapshot: missing or empty 'prompts' list")
    if run.get("abandonment") is not None:
        _fail("run already carries an 'abandonment' record; an abandonment is never retrofitted")
    status = run.get("status")
    if status in ("completed", "abandoned"):
        _fail(f"run status is already terminal ({status!r}); nothing to abandon")

    now = _now()
    run["status"] = "abandoned"
    run["completed_at"] = now
    run["current_prompt"] = None
    run["abandonment"] = {"kind": "deliberate", "at": now, "reason": reason.strip()}
    return _ensure_trailing_fields(run)


def advance(run: dict, outcome: str, result: str, artifacts: list[str]) -> dict:
    """Advance the run document in memory (does no filesystem I/O — that is main()'s
    job — but may _fail() with a JSON error + SystemExit on bad input). Returns the
    mutated run document. Does NOT schema-validate against run.schema.json (audit does
    that separately); it guards only the keys it touches."""
    if outcome not in TERMINAL:
        _fail(f"--outcome must be one of {TERMINAL}")
    if not isinstance(run.get("prompts"), list) or not run["prompts"]:
        _fail("malformed run snapshot: missing or empty 'prompts' list")

    cur = run.get("current_prompt")
    if cur is None:
        _fail("run has current_prompt: null (already completed); nothing to advance")

    prompts = run["prompts"]
    try:
        el = next(p for p in prompts if p["n"] == cur)
    except StopIteration:
        _fail(f"no prompt element with n == current_prompt ({cur})")

    now = _now()
    if el.get("started") is None:
        el["started"] = now
    el["state"] = outcome
    el["completed"] = now
    el["result"] = result
    el["artifacts"] = artifacts

    nxt = next((p for p in prompts if p["state"] == "pending"), None)
    if nxt is not None:
        nxt["state"] = "running"
        if nxt.get("started") is None:
            nxt["started"] = now
        run["current_prompt"] = nxt["n"]
    else:
        run["status"] = "completed"
        run["completed_at"] = now
        run["current_prompt"] = None

    return _ensure_trailing_fields(run)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Advance a .yaml promptbook run snapshot by one prompt, "
                    "or record a deliberate abandonment of the run.")
    ap.add_argument("run", help="path to run-RUN-NNN.yaml")
    ap.add_argument("--outcome", choices=TERMINAL, help="advance mode: the current prompt's terminal state")
    ap.add_argument("--result", default="")
    ap.add_argument("--artifacts", default="", help="comma-separated docs/ paths")
    ap.add_argument("--abandon", action="store_true",
                    help="abandon mode: record a deliberate abandonment of the RUN (needs --reason)")
    ap.add_argument("--reason", default="", help="one-line reason for --abandon")
    ap.add_argument("--book", default=None, help="active book .yaml — its current_prompt pointer is updated too")
    args = ap.parse_args(argv)

    if args.abandon and args.outcome:
        _fail("--abandon and --outcome are mutually exclusive (abandonment is a run-level act)")
    if not args.abandon and not args.outcome:
        _fail("one of --outcome or --abandon is required")

    run_path = Path(args.run)
    if not run_path.is_file():
        _fail(f"run snapshot not found: {run_path}")
    if run_path.suffix != ".yaml":
        _fail("only new-format .yaml run snapshots are supported (a .md run stays on the legacy path)")

    run = yaml.safe_load(run_path.read_text())
    if not isinstance(run, dict) or "format_version" not in run:
        _fail("malformed new-format run snapshot: missing top-level format_version")

    # Both modes write, so both are pinned. Checked before either mutates.
    _check_base_commit_pin(run, run_path)

    # `--book` is VALIDATED BEFORE THE RUN SNAPSHOT IS WRITTEN. A validation that
    # runs after the write is not a validation: a refusal would leave the run
    # advanced while the book's pointer stayed stale, and re-running the same
    # command would then mark `done` a prompt that was never executed. `abandon()`
    # states the same rule for its own guards.
    book_path = None
    book_text = ""
    pre_current_run = None
    if args.book:
        book_path = Path(args.book)
        if not book_path.is_file():
            _fail(f"--book not found: {book_path}")
        book_text = book_path.read_text()
        try:
            pre_write_book = yaml.safe_load(book_text)
        except yaml.YAMLError as exc:
            _fail(f"--book does not parse as YAML ({type(exc).__name__}); only a "
                  f"new-format .yaml book may be passed to --book: {book_path}")
        if not isinstance(pre_write_book, dict):
            _fail(f"--book does not parse as a YAML mapping: {book_path}")
        pre_current_run = pre_write_book.get("current_run")
        n_matches = len(re.findall(BOOK_CURRENT_PROMPT_RE, book_text, flags=re.M))
        if n_matches != 1:
            _fail(
                f"--book has {n_matches} lines matching '{BOOK_CURRENT_PROMPT_RE}' "
                f"(expected exactly 1); refusing to rewrite an ambiguous book: {book_path}"
            )

    if args.abandon:
        run = abandon(run, args.reason)
    else:
        artifacts = [a for a in (s.strip() for s in args.artifacts.split(",")) if a]
        run = advance(run, args.outcome, args.result, artifacts)

    # Two preconditions on the `--book` rewrite, BOTH checked before either write.
    # A precondition that fires below the writes has already advanced the run and
    # rewritten a book it then refuses — the same ordering defect the `--book`
    # validation above was hoisted to close.
    if book_path is not None:
        cp = run["current_prompt"]
        if not (cp is None or (isinstance(cp, int) and not isinstance(cp, bool))):
            _fail(
                f"run's current_prompt is {type(cp).__name__}, not an int or null; "
                f"refusing to interpolate it into the book rewrite: {run_path}"
            )
        # A precondition on PRE-EXISTING book state: a book whose `current_run` is
        # null or malformed cannot authorize the archive the completing advance is
        # handing it, so the advance is refused rather than half-applied.
        if cp is None and run["status"] == "completed":
            if not isinstance(pre_current_run, str) or not re.match(r"^RUN-\d{3}$", pre_current_run):
                _fail(
                    f"--book's current_run does not match ^RUN-\\d{{3}}$ on a "
                    f"completing advance (got {pre_current_run!r}): {book_path}"
                )

    run_path.write_text(_dump(run))

    if book_path is not None:
        # Neither a completed nor an abandoned run nulls the book's `current_run`
        # pointer — only a book's current run can authorize its archive (ADR-0077
        # clause 5(b)). `archive-promptbook` is the sole writer that nulls
        # `current_run`, and it does so at archival. This writer only ever moves
        # `current_prompt`.
        replacement = ("current_prompt: null" if run["current_prompt"] is None
                        else f"current_prompt: {run['current_prompt']}")
        # A `lambda` replacement, never a string. `re.sub` processes backreferences
        # in a string replacement, so a `\1` or `\g<0>` reaching `replacement`
        # would splice matched book text back into the book. The type check above
        # bounds the VALUE to an int or null; this bounds the MECHANISM.
        book_text = re.sub(BOOK_CURRENT_PROMPT_RE, lambda _m: replacement, book_text,
                           count=1, flags=re.M)
        book_path.write_text(book_text)

        try:
            post_write_book = yaml.safe_load(book_path.read_text())
        except yaml.YAMLError as exc:
            _fail(f"--book no longer parses as YAML after write "
                  f"({type(exc).__name__}); the rewrite corrupted it: {book_path}")
        if not isinstance(post_write_book, dict):
            _fail(f"--book no longer parses as a YAML mapping after write: {book_path}")
        post_current_run = post_write_book.get("current_run")
        if post_current_run != pre_current_run:
            _fail(
                f"--book's current_run pointer changed during a write that must not "
                f"touch it (was {pre_current_run!r}, now {post_current_run!r}): {book_path}"
            )
    done = sum(1 for p in run["prompts"] if p["state"] in TERMINAL)
    payload = {
        "run": str(run_path),
        "current_prompt": run["current_prompt"],
        "status": run["status"],
        "terminal": f"{done}/{len(run['prompts'])}",
    }
    if run.get("abandonment"):
        payload["abandonment_kind"] = run["abandonment"]["kind"]
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
