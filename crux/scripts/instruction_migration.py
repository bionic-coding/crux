#!/usr/bin/env python3
"""instruction_migration.py — discovery and migration for the canonical AGENTS.md.

Implements the discovery and migration contract decided for the canonical
repository instruction file. `migrate-instructions.py` is the CLI entry point;
`audit-docs` reports in plain mode and applies under `--migrate`.

Two sets, and the difference between them is the whole safety argument:

  MUTATION set    the tracked files of ONE checkout. A vendored dependency cache
                  and a linked worktree are outside it by construction rather
                  than by an enumerated exclusion, because neither is tracked
                  here. Nothing outside this set is ever written.

  SUPPRESSION set wider, and it includes untracked files. A file this tool must
                  not touch can still silence the canonical one: under the host's
                  default mode a CLAUDE.md, .claude/CLAUDE.md or CLAUDE.local.md
                  between the root and the working directory suppresses AGENTS.md
                  entirely. Reporting one and failing on one are different acts.

**No projected rule carries the suppression clause.** The rule table names the
mutation boundary only, so an implementer reading the projection alone would
build a tracked-only scan and ship no suppressor reporting at all. The decision
body is the authority here, and this docstring is the reminder.

Deduplication matches on (heading path, bytes), never bytes alone. Matching on
bytes alone lets a block be REPARENTED — deduplicate `# General`, append its
child `## Security` after `# JavaScript`, and Security silently moves from
General/Security to JavaScript/Security while every block still records as
retained or deduplicated. The accounting pairs each source path with its
resulting path so that move cannot balance.

Staging is per file. A crash leaves committed files committed and the rest
untouched, and a rerun converges. **This claims no multi-file atomicity.**

Exit codes (entry point): 0 clean, 1 findings/refusal with JSON on stdout,
2 capability error with a message on stderr.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

# The three names discovery matches, case-insensitively.
CANONICAL = "AGENTS.md"
_NAMES = {"agents.md", "claude.md", "claude.local.md"}

RECEIPT_NAME = ".instruction-migration-receipt.json"
PREVIEW_NAME = ".instruction-migration-preview.md"

# Path prefixes excluded from mutation regardless of the denylist.
_TEMPLATE_MARKERS = ("crux/templates/", "templates/")


class PlanInvalid(Exception):
    """Raised when apply is called on a plan that did not validate."""


class CapabilityError(Exception):
    """An environment problem — exit 2, never a findings exit."""


def load_denylist(root: Path) -> list[str]:
    """The one declaration surface for a fixture or a generated runtime copy.

    An absent key, and an absent configuration, are both an empty denylist rather
    than an error, so a project audited before initialization still reports.

    Shared by every caller on purpose: a review found the compatibility check
    reading suppressors without it while the migration CLI read them with it, so
    one surface called a withheld path "suppresses until migrated" and the other
    did not. Two callers, one helper, one answer.
    """
    root = Path(root)
    for name in (".bionic.yml", ".crux"):
        cfg = root / name
        if not cfg.exists():
            continue
        try:
            text = cfg.read_text(encoding="utf-8")
        except OSError:
            return []
        out: list[str] = []
        in_block = False
        for line in text.splitlines():
            if line.strip().startswith("instruction_migration_denylist:"):
                in_block = True
                continue
            if in_block:
                stripped = line.strip()
                if stripped.startswith("- "):
                    out.append(stripped[2:].strip().strip('"').strip("'"))
                    continue
                if stripped and not line.startswith((" ", "\t")):
                    break
        return out
    return []


def is_instruction_name(name: str) -> bool:
    return name.lower() in _NAMES


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------- block parsing

_ATX = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_SETEXT = re.compile(r"^\s{0,3}(=+|-+)\s*$")


@dataclass(frozen=True)
class Block:
    path: tuple[str, ...]
    text: str
    level: int


def _heading_lines(lines: list[str]) -> dict[int, tuple[int, str]]:
    """Map line index -> (level, title) for real headings only.

    A `#` is not a heading inside a fenced code block, an indented code block, or
    an HTML comment. These instruction files carry fenced examples and
    commented-out regions, so a parser that missed this would split on them.
    """
    out: dict[int, tuple[int, str]] = {}
    fence: str | None = None
    in_comment = False
    prev_blank = True

    for i, raw in enumerate(lines):
        stripped = raw.strip()

        if fence is not None:
            if stripped.startswith(fence[0] * len(fence)) and _FENCE.match(raw):
                closing = _FENCE.match(raw).group(1)
                if closing[0] == fence[0] and len(closing) >= len(fence):
                    fence = None
            prev_blank = not stripped
            continue

        if in_comment:
            if "-->" in raw:
                in_comment = False
            prev_blank = not stripped
            continue

        m = _FENCE.match(raw)
        if m:
            fence = m.group(1)
            prev_blank = False
            continue

        if stripped.startswith("<!--") and "-->" not in raw:
            in_comment = True
            prev_blank = False
            continue

        # An indented code block: 4+ spaces or a tab, opening after a blank line.
        if prev_blank and (raw.startswith("    ") or raw.startswith("\t")):
            prev_blank = not stripped
            continue

        atx = _ATX.match(raw)
        if atx:
            out[i] = (len(atx.group(1)), atx.group(2).strip())
            prev_blank = False
            continue

        # Setext: this line underlines the previous non-blank, non-heading line.
        if _SETEXT.match(raw) and i > 0 and not prev_blank:
            prior = lines[i - 1].strip()
            if prior and (i - 1) not in out:
                level = 1 if raw.strip()[0] == "=" else 2
                out[i - 1] = (level, prior)
                out.pop(i, None)
        prev_blank = not stripped

    return out


def split_blocks(text: str) -> list[Block]:
    """Split into heading-delimited blocks, each carrying its full ancestry.

    The span above the first heading carries the empty heading path and
    participates in every rule exactly as a headed block does.
    """
    lines = text.splitlines(keepends=True)
    heads = _heading_lines([l.rstrip("\n") for l in lines])

    starts = sorted(heads)
    blocks: list[Block] = []

    def _emit(path, chunk, level):
        if chunk.strip() or path:
            blocks.append(Block(path=path, text=chunk, level=level))

    preamble_end = starts[0] if starts else len(lines)
    _emit((), "".join(lines[:preamble_end]), 0)

    stack: list[tuple[int, str]] = []
    for idx, start in enumerate(starts):
        level, title = heads[start]
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        path = tuple(t for _, t in stack)
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        # A setext heading occupies two source lines; keep the underline with it.
        span_end = end
        _emit(path, "".join(lines[start:span_end]), level)

    return blocks


# ----------------------------------------------------------------------- merge


@dataclass
class ReceiptRow:
    source: str                      # "agents" | "claude" | "-"
    source_path: tuple[str, ...] | None
    result_path: tuple[str, ...] | None
    disposition: str                 # retained|deduplicated|resolved|synthesized|blocked


@dataclass
class Flag:
    kind: str                        # overlap | reparent
    path: tuple[str, ...]
    detail: str


@dataclass
class MergeResult:
    text: str
    receipt_rows: list[ReceiptRow]
    flags: list[Flag]
    applied: bool

    def accounting(self) -> dict:
        counts: dict[str, int] = {}
        for row in self.receipt_rows:
            counts[row.disposition] = counts.get(row.disposition, 0) + 1
        result_blocks = len(split_blocks(self.text)) if self.text else 0
        return {"counts": counts, "result_blocks": result_blocks}

    def accounting_balances(self) -> bool:
        """result blocks == retained + synthesized + resolved, and nothing else.

        Counting blocks alone would balance across a reparenting; each retained
        row additionally asserts source_path == result_path.
        """
        if not self.applied:
            return False
        a = self.accounting()
        expected = sum(a["counts"].get(k, 0)
                       for k in ("retained", "synthesized", "resolved"))
        if expected != a["result_blocks"]:
            return False
        return all(r.source_path == r.result_path
                   for r in self.receipt_rows if r.disposition == "retained")


def _render(blocks: list[Block]) -> str:
    out = []
    for b in blocks:
        chunk = b.text
        if chunk and not chunk.endswith("\n"):
            chunk += "\n"
        out.append(chunk)
    return "".join(out)


def _synth_heading(path: tuple[str, ...]) -> Block:
    level = len(path)
    return Block(path=path, text=f"{'#' * level} {path[-1]}\n", level=level)


def merge_documents(agents_text: str, claude_text: str,
                    resolutions: dict[tuple[str, ...], str] | None = None
                    ) -> MergeResult:
    """Deterministic merge. The automatic half removes only exact duplicates."""
    resolutions = resolutions or {}
    a_blocks = split_blocks(agents_text)
    c_blocks = split_blocks(claude_text)

    result: list[Block] = []
    rows: list[ReceiptRow] = []
    flags: list[Flag] = []

    emitted_paths: set[tuple[str, ...]] = set()
    emitted_exact: set[tuple[tuple[str, ...], str]] = set()

    for b in a_blocks:
        if (b.path, b.text) in emitted_exact:
            rows.append(ReceiptRow("agents", b.path, None, "deduplicated"))
            continue
        result.append(b)
        emitted_paths.add(b.path)
        emitted_exact.add((b.path, b.text))
        rows.append(ReceiptRow("agents", b.path, b.path, "retained"))

    def _tail_chain() -> list[tuple[str, ...]]:
        """The ancestry the next appended block would land under."""
        return [blk.path for blk in result]

    for b in c_blocks:
        if (b.path, b.text) in emitted_exact:
            rows.append(ReceiptRow("claude", b.path, None, "deduplicated"))
            continue

        if b.path in emitted_paths:
            if b.path in resolutions:
                for i, blk in enumerate(result):
                    if blk.path == b.path:
                        result[i] = Block(b.path, resolutions[b.path], blk.level)
                        break
                # Both sources are SUPERSEDED; the resulting block is one
                # `resolved` row. Marking both sources resolved would count two
                # result blocks for one and the balance could never hold.
                for r in rows:
                    if r.source_path == b.path and r.disposition == "retained":
                        r.disposition = "superseded"
                rows.append(ReceiptRow("claude", b.path, None, "superseded"))
                rows.append(ReceiptRow("-", None, b.path, "resolved"))
                emitted_exact.add((b.path, resolutions[b.path]))
                continue
            flags.append(Flag("overlap", b.path,
                              f"heading path {'/'.join(b.path) or '(preamble)'} "
                              "is present in both sources with differing bodies"))
            rows.append(ReceiptRow("claude", b.path, None, "blocked"))
            continue

        # Placing it must not change its ancestry.
        ancestors = [b.path[:i] for i in range(1, len(b.path))]
        missing = [a for a in ancestors if a not in emitted_paths]
        present = [a for a in ancestors if a in emitted_paths]

        tail = _tail_chain()

        def _open_at_tail(anc: tuple[str, ...]) -> bool:
            """Is `anc` still the open chain at the end of the result?"""
            for blk in reversed(tail):
                if blk == anc:
                    return True
                if len(blk) <= len(anc):
                    return False
            return False

        reparents = [a for a in present if not _open_at_tail(a)]
        if reparents:
            if b.path in resolutions:
                parent = b.path[:-1]
                insertion = next(
                    (i for i, block in enumerate(result)
                     if block.path == parent),
                    None)
                if insertion is None:
                    raise PlanInvalid(
                        f"cannot place reviewed resolution for {'/'.join(b.path)} "
                        "under its missing ancestor")
                insertion += 1
                while (insertion < len(result)
                       and result[insertion].path[:len(parent)] == parent):
                    insertion += 1
                result.insert(insertion,
                              Block(b.path, resolutions[b.path], b.level))
                emitted_paths.add(b.path)
                emitted_exact.add((b.path, resolutions[b.path]))
                rows.append(ReceiptRow("claude", b.path, None, "superseded"))
                rows.append(ReceiptRow("-", None, b.path, "resolved"))
                continue
            flags.append(Flag(
                "reparent", b.path,
                f"placing {'/'.join(b.path)} at the end would change its ancestry; "
                f"ancestor {'/'.join(reparents[-1])} exists but is not open at the tail"))
            rows.append(ReceiptRow("claude", b.path, None, "blocked"))
            continue

        for anc in missing:
            synth = _synth_heading(anc)
            result.append(synth)
            emitted_paths.add(anc)
            emitted_exact.add((anc, synth.text))
            rows.append(ReceiptRow("-", None, anc, "synthesized"))

        result.append(b)
        emitted_paths.add(b.path)
        emitted_exact.add((b.path, b.text))
        rows.append(ReceiptRow("claude", b.path, b.path, "retained"))

    applied = not flags
    return MergeResult(_render(result) if applied else "", rows, flags, applied)


# ------------------------------------------------------------------- discovery


@dataclass
class Suppressor:
    path: Path
    reason: str
    on_chain: bool
    remedy: str = ""



@dataclass
class Discovery:
    root: Path
    managed: list[Path]
    excluded: dict[str, str]
    suppressors: list[Suppressor]

    def managed_paths(self) -> list[Path]:
        return sorted(self.managed, key=lambda p: p.as_posix())

    def disposition(self, rel: str) -> str | None:
        return self.excluded.get(rel)

    def by_scope(self) -> dict[Path, list[Path]]:
        scopes: dict[Path, list[Path]] = {}
        for rel in self.managed:
            scopes.setdefault(PurePosixPath(rel).parent, []).append(rel)
        return {Path(str(k)): v for k, v in scopes.items()}


def git_tracked_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                             capture_output=True, text=True, check=True).stdout
    except FileNotFoundError as exc:
        raise CapabilityError("git is not available on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise CapabilityError(f"git ls-files failed in {root}: {exc.stderr}") from exc
    return [p for p in out.split("\0") if p]


def _contained(root: Path, rel: str) -> bool:
    """Does `rel` resolve to a location inside `root`?

    Checked over the FULLY RESOLVED path, not the leaf. A leaf-only check passes a
    tracked path whose intermediate directory was replaced by a symlink after
    checkout, and the commit would then write and unlink outside the repository.
    """
    try:
        target = (root / rel).resolve()
        base = root.resolve()
    except (OSError, RuntimeError):
        return False
    return target == base or base in target.parents


def _classify(root: Path, rel: str) -> str | None:
    """Return an exclusion reason, or None when the file is managed."""
    p = PurePosixPath(rel)
    name = p.name.lower()

    if (root / rel).is_symlink():
        return "excluded:symlink"
    if not _contained(root, rel):
        return "excluded:escapes-root"
    if name == "claude.local.md":
        return "excluded:local-override"
    if ".claude" in p.parts and name == "claude.md":
        return "excluded:dot-claude"
    if any(rel.startswith(m) or f"/{m}" in f"/{rel}" for m in _TEMPLATE_MARKERS):
        return "excluded:template"
    return None


def _scan_suppressors(root: Path, working_dir: Path,
                      deny: set[str] | None = None) -> list[Suppressor]:
    """Clause 5. The whole checkout, not one ancestor chain.

    The chain that matters runs from the root to whatever working directory a
    developer later runs from, which an audit cannot know. A private
    `<docs_dir>/CLAUDE.local.md` silences the tree for anyone working inside it,
    and an ancestor-only scan would miss it.
    """
    found: list[Suppressor] = []
    # Resolve BOTH ends before comparing. On macOS a temp root is /var/... while
    # its resolved parents are /private/var/..., so comparing an unresolved root
    # against resolved parents made every chain empty and every suppressor
    # off-chain — the exact shape that would silently disarm the verdict.
    rroot = root.resolve()
    try:
        wd = working_dir.resolve()
    except OSError:
        wd = rroot
    chain_set = {rroot}
    if wd == rroot or rroot in wd.parents:
        cur = wd
        while True:
            chain_set.add(cur)
            if cur == rroot or rroot not in cur.parents:
                break
            cur = cur.parent

    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        # Skip a nested or linked checkout BELOW the root. The root carries a
        # .git entry too, and a scan that skipped it would scan nothing.
        if here != root and (here / ".git").exists():
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d != ".git"]

        for fn in filenames:
            low = fn.lower()
            if low not in {"claude.md", "claude.local.md"}:
                continue
            full = here / fn
            rel = full.relative_to(root).as_posix()
            if low == "claude.md" and ".claude" in PurePosixPath(rel).parts:
                reason = "dot-claude instruction file"
                remedy = ("move its content into the AGENTS.md of the same scope "
                          "and delete this file; no host is known to load "
                          "`.claude/AGENTS.md`, so it is never renamed for you")
            elif low == "claude.local.md":
                reason = "private local override"
                remedy = ("yours to delete or rename; crux never touches a private "
                          "override. Until then it silences the canonical file for "
                          "you alone, on any host using the default mode")
            elif deny and rel in deny:
                # A denylisted path is not managed and will never be migrated, so
                # "suppresses until migrated" would name an event that never comes.
                reason = "withheld by the instruction-migration denylist"
                remedy = ("none while the denylist names it; remove that entry "
                          "first if this file should migrate")
            else:
                reason = "legacy managed file, suppresses until migrated"
                remedy = "run `audit-docs --migrate` to convert it to AGENTS.md"
            found.append(Suppressor(Path(rel), reason,
                                    here.resolve() in chain_set, remedy))
    return sorted(found, key=lambda s: s.path.as_posix())


def discover(root: Path, tracked_files: list[str] | None = None,
             denylist: list[str] | None = None,
             working_dir: Path | None = None) -> Discovery:
    root = Path(root)
    working_dir = Path(working_dir) if working_dir else root
    # An absent key, and an absent configuration, are both an empty denylist
    # rather than an error, so a project audited before init still reports.
    deny = set(denylist or ())
    tracked = tracked_files if tracked_files is not None else git_tracked_files(root)

    managed: list[Path] = []
    excluded: dict[str, str] = {}

    for rel in tracked:
        if not is_instruction_name(PurePosixPath(rel).name):
            continue
        if rel in deny:
            excluded[rel] = "excluded:denylist"
            continue
        # A tracked path that is already gone. This is the RESUME case, not an
        # error: after a partial run `git ls-files` still lists the old path
        # until the deletion is staged, so a rerun must step over it rather than
        # fail reading it. Checked before _classify, which stats the file.
        full = root / rel
        if not full.exists() and not full.is_symlink():
            excluded[rel] = "excluded:absent"
            continue
        reason = _classify(root, rel)
        if reason:
            excluded[rel] = reason
            continue
        managed.append(Path(rel))

    suppressors = _scan_suppressors(root, working_dir, deny)
    tracked_set = set(tracked)
    for s in suppressors:
        rel = s.path.as_posix()
        if rel not in tracked_set and rel not in excluded:
            excluded[rel] = "excluded:untracked"

    return Discovery(root, managed, excluded, suppressors)


# -------------------------------------------------------------------- planning


@dataclass
class Action:
    kind: str                        # rename | collapse | merge
    scope: Path
    sources: list[Path]
    dest: Path
    blocked: bool = False
    reason: str = ""
    needs_case_staging: bool = False
    merge: MergeResult | None = None


@dataclass
class Plan:
    root: Path
    actions: list[Action]
    errors: list[str] = field(default_factory=list)
    discovery: Discovery | None = None

    @property
    def valid(self) -> bool:
        return not self.errors


def _read(root: Path, rel: Path) -> str:
    return (root / rel).read_text(encoding="utf-8")


def build_plan(d: Discovery,
               resolutions: dict[tuple[str, tuple[str, ...]], str] | None = None
               ) -> Plan:
    root = d.root
    actions: list[Action] = []
    errors: list[str] = []
    resolutions = resolutions or {}

    for scope, rels in sorted(d.by_scope().items(), key=lambda kv: str(kv[0])):
        family: dict[str, list[Path]] = {}
        for rel in rels:
            family.setdefault(Path(rel).name.lower(), []).append(Path(rel))

        for low, members in family.items():
            if len(members) > 1:
                errors.append(
                    f"ambiguous: {scope}/ holds {len(members)} names in one "
                    f"case-folded family ({', '.join(m.name for m in members)}); "
                    "a reviewed resolution is required")

        agents = family.get("agents.md", [])
        claude = family.get("claude.md", [])
        if errors:
            continue

        dest = Path(str(scope)) / CANONICAL if str(scope) != "." else Path(CANONICAL)

        if claude and not agents:
            src = claude[0]
            actions.append(Action(
                "rename", Path(str(scope)), [src], dest,
                needs_case_staging=src.name.lower() == dest.name.lower()
                and src.name != dest.name))
        elif agents and not claude:
            src = agents[0]
            if src.name != CANONICAL:
                actions.append(Action("rename", Path(str(scope)), [src], dest,
                                      needs_case_staging=True))
        elif agents and claude:
            a_text, c_text = _read(root, agents[0]), _read(root, claude[0])
            if a_text == c_text:
                actions.append(Action("collapse", Path(str(scope)),
                                      [agents[0], claude[0]], dest))
            else:
                scope_resolutions = {
                    path: text
                    for (resolution_scope, path), text in resolutions.items()
                    if resolution_scope == Path(str(scope)).as_posix()
                }
                m = merge_documents(a_text, c_text, resolutions=scope_resolutions)
                # Clause 8's refusal. `applied` only says no flag fired; the
                # accounting says the result actually accounts for every source
                # block under its own heading path. A merge that flags nothing and
                # still fails to balance is the merge logic being wrong, which is
                # precisely the case this refusal exists for — so it is checked
                # here, before a byte is written, and not merely asserted in a test.
                unbalanced = m.applied and not m.accounting_balances()
                reasons = [f.detail for f in m.flags]
                if unbalanced:
                    reasons.append(
                        "the merge accounting does not balance: "
                        f"{m.accounting()} — refusing rather than writing a result "
                        "whose source blocks are unaccounted for")
                actions.append(Action(
                    "merge", Path(str(scope)), [agents[0], claude[0]], dest,
                    blocked=not m.applied or unbalanced,
                    reason="; ".join(reasons),
                    merge=m))

    return Plan(root, actions, errors, d)


# -------------------------------------------------------------------- applying


@dataclass
class Receipt:
    root: Path
    source_hashes: dict[str, str] = field(default_factory=dict)
    dispositions: dict[str, str] = field(default_factory=dict)
    merge_rows: list[dict] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    atomic: bool = False
    staging_note: str = (
        "Staging is per-file: a temporary file beside the target, then a rename. "
        "A crash leaves committed files committed and the rest untouched, and a "
        "rerun converges. This claims no multi-file filesystem atomicity."
    )

    def has_unresolved(self) -> bool:
        return bool(self.unresolved)

    def is_noop(self) -> bool:
        return not self.dispositions and not self.unresolved

    def to_json(self) -> dict:
        return {
            "source_hashes": self.source_hashes,
            "dispositions": self.dispositions,
            "merge_rows": self.merge_rows,
            "unresolved": self.unresolved,
            "atomic": self.atomic,
            "staging_note": self.staging_note,
        }


def receipt_path(root: Path) -> Path:
    return Path(root) / RECEIPT_NAME


def preview_path(root: Path) -> Path:
    return Path(root) / PREVIEW_NAME


def read_receipt(path: Path) -> Receipt:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    r = Receipt(Path(path).parent)
    r.source_hashes = data.get("source_hashes", {})
    r.dispositions = data.get("dispositions", {})
    r.merge_rows = data.get("merge_rows", [])
    r.unresolved = data.get("unresolved", [])
    r.atomic = data.get("atomic", False)
    return r


def resolution_still_binds(receipt: Receipt, d: Discovery) -> bool:
    """A source that changed after the preview invalidates the plan."""
    for rel, recorded in receipt.source_hashes.items():
        p = d.root / rel
        if not p.exists():
            continue
        if _sha(p.read_bytes()) != recorded:
            return False
    return True


def load_reviewed_resolutions(path: Path, root: Path,
                              d: Discovery) -> dict[tuple[str, tuple[str, ...]], str]:
    """Load a reviewed resolution only when its preview receipt still binds.

    The receipt written with the preview is the binding object. Repeating its
    source hashes in the resolution file makes the reviewer attest to exactly
    the preview they read, and prevents a changed source from borrowing an old
    resolution.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanInvalid(f"cannot read resolution file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PlanInvalid("resolution file must contain a JSON object")
    hashes = data.get("source_hashes")
    items = data.get("resolutions")
    if not isinstance(hashes, dict) or not isinstance(items, list):
        raise PlanInvalid(
            "resolution file must contain source_hashes and resolutions")
    receipt_file = receipt_path(root)
    if not receipt_file.exists():
        raise PlanInvalid(
            f"resolution file requires the preview receipt {RECEIPT_NAME}")
    try:
        preview = read_receipt(receipt_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanInvalid(f"cannot read preview receipt {receipt_file}: {exc}") from exc
    if hashes != preview.source_hashes:
        raise PlanInvalid("resolution source_hashes do not match the preview receipt")
    if not resolution_still_binds(preview, d):
        raise PlanInvalid("a source changed after the preview; review a new resolution")

    resolutions: dict[tuple[str, tuple[str, ...]], str] = {}
    for item in items:
        if not isinstance(item, dict):
            raise PlanInvalid("each resolution must be a JSON object")
        scope, heading_path, text = item.get("scope"), item.get("path"), item.get("text")
        if (not isinstance(scope, str) or not isinstance(heading_path, list)
                or not all(isinstance(part, str) and part for part in heading_path)
                or not isinstance(text, str) or not text):
            raise PlanInvalid(
                "each resolution requires a scope, a non-empty string path, and text")
        blocks = split_blocks(text)
        expected_path = (heading_path[-1],) if heading_path else ()
        expected_level = len(heading_path)
        if (len(blocks) != 1 or blocks[0].path != expected_path
                or blocks[0].level != expected_level):
            raise PlanInvalid(
                "resolution text must contain exactly one block whose heading "
                f"matches {'/'.join(heading_path) or '(preamble)'}")
        key = (Path(scope).as_posix(), tuple(heading_path))
        if key in resolutions:
            raise PlanInvalid(
                f"resolution file repeats {'/'.join(heading_path)} in scope {scope}")
        resolutions[key] = text
    return resolutions


def _atomic_write(target: Path, data: bytes) -> None:
    tmp = target.with_name(target.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()


def _commit_action(action: Action, root: Path, receipt: Receipt) -> None:
    """Commit one action. Per-file; a crash here leaves earlier actions done."""
    root = Path(root)
    dest = root / action.dest

    if action.kind == "rename":
        src = root / action.sources[0]
        data = src.read_bytes()
        if action.needs_case_staging:
            staged = src.with_name(src.name + ".case-stage")
            os.replace(src, staged)
            os.replace(staged, dest)
        else:
            _atomic_write(dest, data)
            src.unlink()
        receipt.dispositions[action.sources[0].as_posix()] = "renamed"

    elif action.kind == "collapse":
        agents, claude = action.sources
        (root / claude).unlink()
        receipt.dispositions[agents.as_posix()] = "kept"
        receipt.dispositions[claude.as_posix()] = "collapsed"

    elif action.kind == "merge":
        if action.merge is None or not action.merge.applied:
            raise PlanInvalid(f"merge action for {action.scope} did not apply")
        if not action.merge.accounting_balances():
            raise PlanInvalid(
                f"merge accounting does not balance for {action.scope}: "
                f"{action.merge.accounting()}")
        _atomic_write(dest, action.merge.text.encode("utf-8"))
        for src in action.sources:
            if (root / src) != dest and (root / src).exists():
                (root / src).unlink()
            receipt.dispositions[src.as_posix()] = "merged"
        receipt.merge_rows.extend(
            {"source": r.source,
             "source_path": list(r.source_path) if r.source_path else None,
             "result_path": list(r.result_path) if r.result_path else None,
             "disposition": r.disposition}
            for r in action.merge.receipt_rows)


def _write_preview(root: Path, blocked: list[Action]) -> None:
    lines = ["# Instruction migration — unresolved conflicts", "",
             "Both sources are left on disk. Create a reviewed JSON resolution file",
             f"that copies source_hashes from `{RECEIPT_NAME}` and carries",
             "resolutions with scope, path, and text. Rerun with",
             'Say "audit docs --migrate using the resolution file at <path>".', ""]
    for a in blocked:
        lines.append(f"## Scope `{a.scope}`")
        lines.append("")
        lines.append(f"- {a.reason}")
        lines.append("")
        for src in a.sources:
            lines.append(f"### Source `{src.as_posix()}`")
            lines.append("")
            lines.append("```markdown")
            lines.append((root / src).read_text(encoding="utf-8").rstrip("\n"))
            lines.append("```")
            lines.append("")
    _atomic_write(preview_path(root), "\n".join(lines).encode("utf-8"))


def apply_plan(plan: Plan, root: Path) -> Receipt:
    """Validate the complete plan, then commit each action, staged per file."""
    if not plan.valid:
        raise PlanInvalid("; ".join(plan.errors))

    root = Path(root)
    receipt = Receipt(root)

    for action in plan.actions:
        for src in action.sources:
            p = root / src
            if p.exists():
                receipt.source_hashes[src.as_posix()] = _sha(p.read_bytes())

    if plan.discovery:
        for rel, reason in plan.discovery.excluded.items():
            receipt.dispositions[rel] = reason

    runnable = [a for a in plan.actions if not a.blocked]
    blocked = [a for a in plan.actions if a.blocked]

    for action in runnable:
        _commit_action(action, root, receipt)

    for a in blocked:
        receipt.unresolved.append({"scope": a.scope.as_posix(), "reason": a.reason})
    if blocked:
        _write_preview(root, blocked)

    if receipt.source_hashes or receipt.unresolved:
        _atomic_write(receipt_path(root),
                      json.dumps(receipt.to_json(), indent=2, sort_keys=True).encode())
    return receipt


# ------------------------------------------------------------------------- log


def append_log(log_path: Path, receipt: Receipt, date: str) -> None:
    """One `schema` op per migration — never one entry per file."""
    log_path = Path(log_path)
    migrated = [k for k, v in receipt.dispositions.items()
                if v in {"renamed", "merged", "collapsed"}]
    heading = (f"## [{date}] schema | migrate instruction files to {CANONICAL} "
               f"({len(migrated)} files)")
    body = [
        f"Migrated {len(migrated)} managed instruction file(s) to `{CANONICAL}`.",
        f"Unresolved scopes: {len(receipt.unresolved)}.",
        f"Receipt: `{RECEIPT_NAME}`.",
    ]
    entry = heading + "\n\n" + "\n".join(body) + "\n\n"

    text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "_Append-only. Newest first._\n\n"
    if marker in text:
        text = text.replace(marker, marker + entry, 1)
    else:
        text = entry + text
    _atomic_write(log_path, text.encode("utf-8"))
