#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""Migrate legacy Markdown promptbooks + run snapshots to structured YAML
(per ADR-0024).

The pre-ADR-0022/0023 corpus stored each promptbook and run snapshot as
Markdown (YAML frontmatter + a prose body). This engine parses one legacy
``.md`` book OR run snapshot and emits the equivalent single-document YAML that
validates against ``promptbook.schema.json`` / ``run.schema.json`` (the same
schemas ``validate-promptbook.py`` enforces).

Design (ADR-0024 §1/§2):
  - stdlib-only engine (a real YAML parser is required at entry per PB-0026);
    reuses ``_yaml_min.load_yaml`` for the frontmatter and a small
    block-scalar emitter LOCAL to this script (deliberately not added to
    ``_yaml_min.py``, whose surface is locked).
  - ``compute_book_hash`` is loaded from ``validate-promptbook.py`` via
    ``importlib.util.spec_from_file_location`` (the hyphenated filename can't be
    plain-imported). A run's ``book_content_hash`` is computed over the migrated
    **book as read from its live ``.yaml`` on disk** (``migrate_path`` passes the
    on-disk-parsed book to ``build_run``); the post-write gate in ``migrate_path``
    then re-reads the on-disk book and asserts the stored hash matches what
    ``compute_book_hash`` yields — i.e. exactly what CHK-PB-BIND recomputes.
  - section parsing keys off ``^## `` / ``^### `` heading NAMES, never position
    (legacy bodies interleave ``## Notes`` / ``## Summary`` among prompt blocks).
  - block scalars round-trip through ``_yaml_min.load_yaml`` (clip chomping).

Self-validation gate (per file), canonical order: build -> emit -> write the
``.yaml`` to its live path -> ``validate_file`` (must be clean) -> for runs,
recompute ``book_content_hash`` from the on-disk book and assert it matches ->
only then (with ``--relocate``) ``git mv`` the original into the legacy tree.
Book-before-run ordering is a hard precondition: migrating a run requires the
live ``.yaml`` book to already exist.

Exit codes (mirror the sibling validators, plus the PB-0026 capability lane):
  0 — clean.
  1 — migration/validation error; ``{"errors": [...]}`` JSON on stdout.
  2 — PyYAML unavailable and the uv repair unavailable/declined (capability
      error; remediation on stderr, nothing on stdout).
  non-zero with empty/unparseable stdout — crash; surface stderr.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent


def _load_sibling(mod_name: str, filename: str):
    """Load a sibling script as a module (handles the hyphenated filename)."""
    spec = importlib.util.spec_from_file_location(mod_name, _SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:  # _yaml_min has no hyphen, so a plain import works when scripts/ is on path.
    import _yaml_min as _yaml_min_mod
except ImportError:  # pragma: no cover - exercised outside scripts/ cwd
    _yaml_min_mod = _load_sibling("_yaml_min", "_yaml_min.py")
# SINGLE-INSTANCE RULE (PB-0026 review): load_yaml, ensure_real_yaml, and the
# YamlCapabilityError class used in except clauses MUST all come from the SAME
# module object — sibling-loading a second copy creates a distinct exception
# class that except clauses silently fail to catch.
load_yaml = _yaml_min_mod.load_yaml

_VP = _load_sibling("_validate_promptbook", "validate-promptbook.py")
_crux_config = _load_sibling("crux_config", "crux_config.py")


_DOCS_PB_ROOT_CACHE: Path | None = None


def _docs_pb_root() -> Path:
    """Resolve <docs_dir>/promptbooks via the repo-root .crux (ADR-0032).

    Anchored to the process cwd (the documented run-from-repo-root
    convention), not the script location — an installed plugin's scripts/
    dir is nowhere near the target repo's docs tree. Resolved exactly once
    per process (the ADR-0032 resolve-once rule); the cache also keeps an
    N-file migration from re-reading .crux per file."""
    global _DOCS_PB_ROOT_CACHE
    if _DOCS_PB_ROOT_CACHE is None:
        _DOCS_PB_ROOT_CACHE = _crux_config.load_config().docs_root / "promptbooks"
    return _DOCS_PB_ROOT_CACHE
compute_book_hash = _VP.compute_book_hash
validate_file = _VP.validate_file


class MigrationError(Exception):
    """A legacy document could not be parsed/migrated."""


# ─────────────────────────────── parsing ──────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_BULLET_RE = re.compile(r"^\s*-\s+\*\*(?P<label>.+?):\*\*\s?(?P<value>.*)$")
_H2_RE = re.compile(r"^## (.+?)\s*$")
_BOOK_PROMPT_RE = re.compile(r"^### Prompt (\d+)\s+—\s+(.+?)\s*$")
_RUN_PROMPT_TITLE_RE = re.compile(r"^Prompt (\d+)\s+—\s+(.+?)\s*$")


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text). Raises if no frontmatter block."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise MigrationError("no leading '---' frontmatter block")
    fm = load_yaml(m.group(1))
    if not isinstance(fm, dict):
        raise MigrationError("frontmatter did not parse to a mapping")
    return fm, m.group(2)


def detect_legacy_kind(fm: dict) -> str:
    """'run' if frontmatter carries run_id+book_id; 'promptbook' if id without
    run_id. Mirrors validate-promptbook.detect_kind on the legacy frontmatter."""
    if "run_id" in fm and "book_id" in fm:
        return "run"
    if "id" in fm and "run_id" not in fm:
        return "promptbook"
    raise MigrationError("cannot classify legacy frontmatter as book or run")


def _is_fence(line: str) -> bool:
    """A fenced-code-block delimiter line (```` ``` ````, optionally with a lang)."""
    return line.lstrip().startswith("```")


def h2_sections(body: str) -> list[tuple[str, list[str]]]:
    """Ordered (title, lines) for each top-level ``## `` section. Lines before
    the first ``## `` (the ``# Cycle`` H1 + blanks) are dropped.

    **Fence-aware:** a ``## `` line INSIDE a ```` ``` ```` fenced code block is NOT a
    section boundary. Legacy run snapshots embed a PR-draft fence whose body
    contains literal ``## Summary`` / ``## Test plan`` lines (markdown the draft
    quotes); treating those as real sections would truncate the enclosing section
    and silently drop content."""
    out: list[tuple[str, list[str]]] = []
    title: str | None = None
    buf: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if _is_fence(line):
            in_fence = not in_fence
            if title is not None:
                buf.append(line)
            continue
        m = _H2_RE.match(line)
        if m and not in_fence:
            if title is not None:
                out.append((title, buf))
            title, buf = m.group(1).strip(), []
        elif title is not None:
            buf.append(line)
    if title is not None:
        out.append((title, buf))
    return out


def parse_bullets(lines: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Parse ``- **Label:** value`` bullets with multi-line continuation. Returns
    ``(fields, trailing)``:

    - ``fields``: label -> raw lines (inline tail first, then continuation lines).
    - ``trailing``: block content AFTER the bullets that is NOT part of any field —
      i.e. lines reached once a *structural break* (an HTML comment, a ``###``+
      sub-heading, or a fence) ends bullet absorption. The caller decides what to
      do with it (runs append it to ``notes`` so embedded PR-drafts / plans are
      never lost; books discard the inter-prompt ``<!-- MODULE BOUNDARY -->`` line).

    A field's continuation stops at the next bullet OR a structural break. This
    prevents a trailing ``<!-- ... -->`` comment or an embedded ``### PR Draft``
    fence from being absorbed into (and corrupting) the last bullet's value.
    Blockquoted headings/fences (``> ## x`` / ``> ``` ``) are NOT breaks — they are
    part of a Prompt blockquote body."""
    fields: dict[str, list[str]] = {}
    trailing: list[str] = []
    cur: str | None = None
    seen_bullet = False
    in_fence = False
    for line in lines:
        if _is_fence(line):
            in_fence = not in_fence
            cur = None  # a fence ends bullet absorption
            if seen_bullet:
                trailing.append(line)
            continue
        if in_fence:
            if seen_bullet:
                trailing.append(line)
            continue
        m = _BULLET_RE.match(line)
        if m:
            cur = m.group("label").strip()
            fields[cur] = [m.group("value")]
            seen_bullet = True
            continue
        stripped = line.lstrip()
        if stripped.startswith("<!--") or re.match(r"^#{2,6}\s", stripped):
            cur = None  # structural break: stop absorbing into the current field
            if seen_bullet:
                trailing.append(line)
            continue
        if cur is not None:
            fields[cur].append(line)
        elif seen_bullet and line.strip() != "":
            trailing.append(line)
    return fields, trailing


def _prose(raw_lines: list[str]) -> str:
    """Inline tail + continuation lines -> a single de-wrapped string (cosmetic
    line wraps collapsed to spaces). For the short scalar fields."""
    parts = [ln.strip() for ln in raw_lines if ln.strip() != ""]
    return " ".join(parts).strip()


def _blockquote(raw_lines: list[str]) -> str:
    """Strip a uniform ``> ``/``>`` blockquote prefix, preserving internal
    newlines and blank lines. For the prompt body field."""
    out: list[str] = []
    started = False
    for ln in raw_lines:
        s = ln.lstrip()
        if not started and s == "":
            continue  # skip blanks before the quote begins
        if s.startswith(">"):
            started = True
            rest = s[1:]
            out.append(rest[1:] if rest.startswith(" ") else rest)
        elif s == "":
            out.append("")
        else:
            out.append(s)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def _section_text(lines: list[str]) -> str:
    """Strip leading/trailing blank lines from a section body; keep internal."""
    out = list(lines)
    while out and out[0].strip() == "":
        out.pop(0)
    while out and out[-1].strip() == "":
        out.pop()
    return "\n".join(out)


def _split_list_cell(value: str) -> list[str]:
    """A legacy ``Artifacts:`` / ``Side effects:`` cell -> a list of strings.
    ``—``/empty/``none`` -> []. Splits on **top-level commas only** (not commas
    inside parentheses), because legacy cells carry parenthetical annotations like
    ``tools/rename.py (W1, 32 renames + 2 deletions)`` that a naive comma-split
    shreds into bogus fragments. Shared by side_effects (books) and artifacts (runs)."""
    v = value.strip()
    if v in ("", "—", "-", "none", "None", "—."):
        return []
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in v:
        if ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


# ──────────────────────────── build documents ─────────────────────────────


def build_book(fm: dict, body: str) -> dict:
    secs = {t: ls for t, ls in h2_sections(body)}
    book: dict[str, Any] = {"format_version": "1"}
    for k in ("id", "title", "status", "created_at", "total_prompts"):
        if k not in fm:
            raise MigrationError(f"book frontmatter missing {k!r}")
        book[k] = str(fm[k]) if k in ("id", "title", "status", "created_at") else fm[k]
    book["current_run"] = fm.get("current_run")
    book["current_prompt"] = fm.get("current_prompt")
    book["forked_from"] = fm.get("forked_from")
    book["tags"] = list(fm.get("tags") or [])
    if "Goal" not in secs or _section_text(secs["Goal"]) == "":
        raise MigrationError("book missing a non-empty '## Goal' section")
    if "Strategy" not in secs or _section_text(secs["Strategy"]) == "":
        raise MigrationError("book missing a non-empty '## Strategy' section")
    book["goal"] = _section_text(secs["Goal"])
    book["strategy"] = _section_text(secs["Strategy"])
    if "Prompts" not in secs:
        raise MigrationError("book missing a '## Prompts' section")
    book["prompts"] = _build_book_prompts(secs["Prompts"])
    # modules: carry the frontmatter block when present. A cycle-tagged book that
    # predates the modules frontmatter (e.g. PB-0005, authored before dev-cycle
    # emitted it) must still satisfy the schema's `if cycle then require modules`
    # rule — infer the block from the prompt structure, cross-checked against the
    # 4N+4M+3K+2 cycle formula so we never fabricate counts that don't reconcile.
    if fm.get("modules") is not None:
        book["modules"] = fm["modules"]
    elif "cycle" in book["tags"]:
        inferred = _infer_modules(book["prompts"], book["total_prompts"])
        if inferred is None:
            raise MigrationError(
                "cycle-tagged book has no modules block and it could not be "
                "inferred from the prompt structure (formula did not reconcile)"
            )
        book["modules"] = inferred
    # Legacy cycle books predate ADR-0029's machine-enforced cycle-coverage
    # contract and carry no per-prompt module_tag, so they cannot satisfy it.
    # Grandfather them (the validator skips grandfathered books) — the same
    # treatment carried by the migrated corpus.
    if "cycle" in book["tags"]:
        book["cycle_grandfathered"] = True
        book["grandfather_reason"] = (
            "Pre-ADR-0029 archived cycle book; grandfathered per the ADR-0029 "
            "migration (not retrofitted to the machine-enforced cycle-coverage "
            "contract). See [[adrs/ADR-0029-add-iterate-skill-and-cycle-coverage-validation]]."
        )
    note = _build_archive_note(secs.get("Archive note"))
    if note is not None:
        book["archive_note"] = note
    return book


def _build_book_prompts(lines: list[str]) -> list[dict]:
    # First pass: collect candidate (n, title, block_lines) in document order.
    candidates: list[list] = []
    cur: list | None = None
    for line in lines:
        m = _BOOK_PROMPT_RE.match(line)
        if m:
            cur = [int(m.group(1)), m.group(2).strip(), []]
            candidates.append(cur)
        elif cur is not None:
            cur[2].append(line)
    # Second pass: accept only the contiguous-from-1 sequence. This drops a stale
    # duplicate/trailing prompt block (legacy snapshots occasionally carry one;
    # see PB-0008's run) without inventing or reordering prompts.
    prompts: list[dict] = []
    expected = 1
    for n, title, block in candidates:
        if n != expected:
            continue
        f, _trailing = parse_bullets(block)  # book prompt bodies have no orphan tail
        p: dict[str, Any] = {"n": expected, "title": title}
        p["purpose"] = _prose(f.get("Purpose", [""]))
        p["prompt"] = _blockquote(f.get("Prompt", [""]))
        p["expected_output"] = _prose(f.get("Expected output", [""]))
        se = _split_list_cell(" ".join(f.get("Side effects", [""])))
        if se:
            p["side_effects"] = se
        prompts.append(p)
        expected += 1
    return prompts


# Module-signature substrings (lowercased prompt titles): one council/accept per
# ADR module, one internal review per dev module, one fix-loop per review module.
def _infer_modules(prompts: list[dict], total_prompts: int) -> dict | None:
    titles = [str(p.get("title", "")).lower() for p in prompts]
    adrs = sum(1 for t in titles if "accept the adr" in t)
    dev_loops = sum(1 for t in titles if "internal review" in t)
    review_cycles = sum(1 for t in titles if "implement feedback" in t)
    if adrs >= 1 and dev_loops >= 1 and review_cycles >= 1 and \
            (4 * adrs + 4 * dev_loops + 3 * review_cycles + 2) == total_prompts:
        return {"adrs": adrs, "dev_loops": dev_loops, "review_cycles": review_cycles}
    return None


def _build_archive_note(lines: list[str] | None) -> dict | None:
    if not lines:
        return None
    text = _section_text(lines)
    if text == "":
        return None
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    run_m = re.search(r"(RUN-\d{3})", text)
    if not date_m or not run_m:
        # Schema requires all three keys; if we can't extract, drop the optional
        # note rather than emit an invalid object.
        return None
    return {"archived_at": date_m.group(1), "final_run": run_m.group(1), "note": text}


def build_run(fm: dict, body: str, book_doc: dict) -> dict:
    run: dict[str, Any] = {"format_version": "1"}
    for k in ("run_id", "book_id"):
        if k not in fm:
            raise MigrationError(f"run frontmatter missing {k!r}")
        run[k] = str(fm[k])
    run["book_content_hash"] = compute_book_hash(book_doc)
    started = fm.get("started_at")
    run["started_at"] = str(started) if started is not None else ""
    completed = fm.get("completed_at")
    run["completed_at"] = str(completed) if completed is not None else None
    run["status"] = str(fm.get("status", "completed"))
    run["current_prompt"] = fm.get("current_prompt")
    sections = h2_sections(body)
    secs = {t: ls for t, ls in sections}
    prompts, prompt_extras = _build_run_prompts(sections)
    run["prompts"] = prompts
    for label, key in (("Notes", "notes"), ("PR Draft", "pr_draft"), ("Summary", "summary")):
        if label in secs:
            txt = _section_text(secs[label])
            if txt:
                run[key] = txt
    # Lossless catch-all (per ADR-0024 "preserve content"): any top-level section
    # that isn't a Prompt / Notes / PR Draft / Summary (e.g. an old run's top-level
    # `## Artifacts`), plus content trailing a prompt's fields (an embedded
    # `### PR Draft` / plan that parse_bullets split off), is appended to `notes`
    # under a marker so the structured view never silently drops legacy content.
    addenda: list[str] = []
    for title, lines in sections:
        if _RUN_PROMPT_TITLE_RE.match(title) or title in ("Notes", "PR Draft", "Summary"):
            continue
        txt = _section_text(lines)
        if txt:
            addenda.append(f"## {title}\n\n{txt}")
    for n, ttext in prompt_extras:
        addenda.append(f"### Migrated from Prompt {n} body\n\n{ttext}")
    if addenda:
        block = ("## Migrated extra content (preserved verbatim from the legacy snapshot)\n\n"
                 + "\n\n".join(addenda))
        run["notes"] = (run["notes"] + "\n\n" + block) if "notes" in run else block
    return run


def _build_run_prompts(sections: list[tuple[str, list[str]]]) -> tuple[list[dict], list[tuple[int, str]]]:
    """Returns (prompts, extras). ``extras`` is (prompt_n, trailing_text) for any
    content found after a prompt's recognized fields (an embedded PR-draft/plan),
    which build_run folds into ``notes`` so nothing is lost."""
    prompts: list[dict] = []
    extras: list[tuple[int, str]] = []
    expected = 1
    for title, lines in sections:
        tm = _RUN_PROMPT_TITLE_RE.match(title)
        if not tm:
            continue
        # Accept only the contiguous-from-1 sequence; skip a stale duplicate tail
        # (e.g. PB-0008's run re-lists prompts 9-13 as pending) and any out-of-order
        # heading. The original .md is preserved under legacy/ regardless.
        if int(tm.group(1)) != expected:
            continue
        f, trailing = parse_bullets(lines)
        p: dict[str, Any] = {"n": expected, "title": tm.group(2).strip()}
        p["state"] = _prose(f.get("State", [""])).lower()
        p["started"] = _nullable(_prose(f.get("Started", [""])))
        p["completed"] = _nullable(_prose(f.get("Completed", [""])))
        result = _prose(f.get("Result", [""]))
        p["result"] = "" if result in ("—", "-", "") else result
        p["artifacts"] = _split_list_cell(" ".join(f.get("Artifacts", [""])))
        # The legacy per-prompt `blocked-confirmed` field is RETIRED (ADR-0077 clause
        # 5(b)) — archive eligibility is now a run-level property. It is dropped rather
        # than reified: carrying it across would emit a run that `run.schema.json` no
        # longer accepts. The preserved `.md` original keeps the field verbatim under
        # `legacy/`, so nothing is lost.
        prompts.append(p)
        ttext = _section_text(trailing)
        if ttext:
            extras.append((expected, ttext))
        expected += 1
    return prompts, extras


def _nullable(value: str) -> str | None:
    v = value.strip()
    return None if v in ("", "null", "~", "—", "-") else v


# ──────────────────────────────── emitter ─────────────────────────────────
#
# Minimal YAML emitter, LOCAL to this script. Long-form fields (those containing
# a newline) become ``|`` literal block scalars with a 2-space body indent and
# clip chomping; everything else is a plain or double-quoted scalar. The output
# MUST round-trip through _yaml_min.load_yaml — the self-validation gate enforces
# this operationally, and the run hash is taken from the re-loaded file.

_PLAIN_SAFE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _./-]*$")
_YAML_KEYWORDS = {"true", "false", "yes", "no", "on", "off", "null", "none", "~"}
# C0 control chars (excluding the \n that block scalars carry and \t which both
# parse paths keep literally) plus CR and DEL. The local emitter only escapes
# `\` and `"`; `_yaml_min`'s `_unescape_double_quoted` does NOT decode `\r`/`\xNN`,
# so emitting a raw control char would parse DIFFERENTLY under PyYAML vs the stdlib
# fallback (breaking the ADR-0023 §3 byte-parity the hash depends on). The corpus
# has none; reject loudly rather than emit an ambiguous document (security S3).
_BAD_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\r]")


def _assert_emittable(s: str, where: str) -> None:
    if _BAD_CTRL_RE.search(s):
        raise MigrationError(
            f"{where}: value contains a control character the minimal emitter cannot "
            "represent identically across the PyYAML and stdlib parse paths; "
            "clean the legacy source before migrating"
        )


def _emit_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    s = str(value)
    _assert_emittable(s, "scalar")
    if s != "" and "\n" not in s and _PLAIN_SAFE_RE.match(s) and s.lower() not in _YAML_KEYWORDS:
        return s
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped + '"'


def _flow_list(items: list) -> str:
    return "[" + ", ".join(_emit_scalar(x) for x in items) + "]"


def _field_lines(key: str, value: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, str) and "\n" in value:
        _assert_emittable(value, f"field {key!r}")
        lines = value.split("\n")
        while lines and lines[-1] == "":
            lines.pop()
        body_pad = " " * (indent + 2)
        out = [f"{pad}{key}: |"]
        out.extend(body_pad + ln if ln != "" else "" for ln in lines)
        return out
    if isinstance(value, list):
        return [f"{pad}{key}: {_flow_list(value)}"]
    return [f"{pad}{key}: {_emit_scalar(value)}"]


def _emit_mapping(d: dict, keys: list[str], indent: int) -> list[str]:
    out: list[str] = []
    for k in keys:
        if k not in d:
            continue
        out.extend(_field_lines(k, d[k], indent))
    return out


_BOOK_TOP = ["format_version", "id", "title", "status", "created_at",
             "total_prompts", "current_run", "current_prompt", "forked_from", "tags",
             "cycle_grandfathered", "grandfather_reason"]
_BOOK_PROMPT_KEYS = ["n", "title", "purpose", "prompt", "expected_output",
                     "side_effects", "module_tag"]
_RUN_TOP = ["format_version", "run_id", "book_id", "book_content_hash",
            "started_at", "completed_at", "status", "current_prompt"]
_RUN_PROMPT_KEYS = ["n", "title", "state", "started", "completed", "result",
                    "artifacts"]


def _emit_prompt_items(prompts: list[dict], keys: list[str]) -> list[str]:
    out: list[str] = ["prompts:"]
    for p in prompts:
        first = True
        for k in keys:
            if k not in p:
                continue
            field = _field_lines(k, p[k], 4)
            if first:
                # Replace the 4-space pad of the first field's first line with
                # the '  - ' sequence list marker.
                field[0] = "  - " + field[0][4:]
                first = False
            out.extend(field)
    return out


def emit_book(book: dict) -> str:
    out = _emit_mapping(book, _BOOK_TOP, 0)
    if "modules" in book:
        out.append("modules:")
        out.extend(_emit_mapping(book["modules"], ["adrs", "dev_loops", "review_cycles"], 2))
    out.extend(_field_lines("goal", book["goal"], 0))
    out.extend(_field_lines("strategy", book["strategy"], 0))
    if "run_autonomy" in book:
        out.extend(_field_lines("run_autonomy", book["run_autonomy"], 0))
    if "archive_note" in book:
        out.append("archive_note:")
        out.extend(_emit_mapping(book["archive_note"], ["archived_at", "final_run", "note"], 2))
    out.extend(_emit_prompt_items(book["prompts"], _BOOK_PROMPT_KEYS))
    return "\n".join(out) + "\n"


def emit_run(run: dict) -> str:
    out = _emit_mapping(run, _RUN_TOP, 0)
    out.extend(_emit_prompt_items(run["prompts"], _RUN_PROMPT_KEYS))
    for key in ("notes", "pr_draft", "summary"):
        if key in run:
            out.extend(_field_lines(key, run[key], 0))
    return "\n".join(out) + "\n"


# ──────────────────────────── high-level API ──────────────────────────────


def migrate_book_text(text: str) -> str:
    fm, body = split_frontmatter(text)
    if detect_legacy_kind(fm) != "promptbook":
        raise MigrationError("not a promptbook (frontmatter has run_id)")
    return emit_book(build_book(fm, body))


def migrate_run_text(text: str, migrated_book_yaml: str) -> str:
    fm, body = split_frontmatter(text)
    if detect_legacy_kind(fm) != "run":
        raise MigrationError("not a run snapshot (frontmatter lacks run_id/book_id)")
    book_doc = load_yaml(migrated_book_yaml)
    return emit_run(build_run(fm, body, book_doc))


# ────────────────────────────────── CLI ───────────────────────────────────


def _live_yaml_path(src: Path) -> Path:
    """The live ``.yaml`` path for a legacy ``.md`` source. Run snapshots whose
    basename is the older ``run-001.md`` form normalize to ``run-RUN-001.yaml``."""
    name = src.stem
    m = re.match(r"^run-(\d{3})$", name)
    if m:
        name = f"run-RUN-{m.group(1)}"
    return src.with_name(name + ".yaml")


def _find_book_yaml(book_id: str) -> Path | None:
    for sub in ("archive", "active"):
        for cand in (_docs_pb_root() / sub).glob(f"{book_id}-*.yaml"):
            return cand
    return None


def _relocate(src: Path, legacy_root: Path) -> Path:
    """Move the original ``.md`` into the legacy tree, mirroring its path under
    docs/promptbooks/. Uses ``git mv`` when the file is tracked, else os.rename.

    The destination is derived by ``relative_to`` the repo's ``docs/promptbooks/``
    root (not a first-match path-component scan), so an ancestor dir that happens
    to be named ``promptbooks`` can't mis-anchor the move and a source NOT under
    ``docs/promptbooks/`` (e.g. an already-relocated ``legacy/`` file) is rejected
    by the raised ``ValueError`` rather than nested deeper (security S4)."""
    pb_root = _docs_pb_root().resolve()
    rel = src.resolve().relative_to(pb_root)  # archive/PB-0001-x.md or runs/PB-0001-x/run-RUN-001.md
    dest = legacy_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(src)],
        cwd=str(_SCRIPTS.parent.parent), capture_output=True,
    ).returncode == 0
    if tracked:
        subprocess.run(["git", "mv", str(src), str(dest)],
                       cwd=str(_SCRIPTS.parent.parent), check=True)
    else:
        src.rename(dest)
    return dest


def migrate_path(src: Path, kind_override: str | None, dry_run: bool,
                 relocate: bool, legacy_root: Path) -> list[dict]:
    """Migrate one file. Returns a list of error dicts ([] on success)."""
    label = str(src)

    def err(msg: str) -> list[dict]:
        return [{"file": label, "error": msg}]

    try:
        text = src.read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
        kind = kind_override or detect_legacy_kind(fm)
    except (_yaml_min_mod.YamlCapabilityError, _VP.YamlCapabilityError):
        # Environment problem, never a migration finding (PB-0026) — must
        # reach main()'s crash-lane handler, not the findings JSON.
        raise
    except Exception as exc:  # noqa: BLE001
        return err(f"parse error: {exc}")

    try:
        if kind == "promptbook":
            yaml_text = migrate_book_text(text)
        else:
            book_id = str(fm.get("book_id", ""))
            book_yaml = _find_book_yaml(book_id)
            if book_yaml is None:
                return err(f"book {book_id} has no migrated .yaml yet "
                           "(book-before-run ordering: migrate the book first)")
            yaml_text = migrate_run_text(text, book_yaml.read_text(encoding="utf-8"))
    except (_yaml_min_mod.YamlCapabilityError, _VP.YamlCapabilityError):
        # Environment problem, never a migration finding (PB-0026) — must
        # reach main()'s crash-lane handler, not the findings JSON.
        raise
    except Exception as exc:  # noqa: BLE001
        return err(f"migration error: {exc}")

    dest = _live_yaml_path(src)
    if dry_run:
        print(yaml_text)
        return []

    dest.write_text(yaml_text, encoding="utf-8")
    code, errors = validate_file(dest, kind)
    if code != 0:
        return errors

    if kind == "run":
        on_disk_book = _find_book_yaml(str(fm.get("book_id", "")))
        expected = compute_book_hash(load_yaml(on_disk_book.read_text(encoding="utf-8")))
        got = load_yaml(dest.read_text(encoding="utf-8")).get("book_content_hash")
        if got != expected:
            return err(f"book_content_hash mismatch: stored {got} != recomputed {expected}")

    if relocate:
        _relocate(src, legacy_root)
    return []


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="migrate-promptbooks",
        description="Migrate legacy .md promptbooks/runs to structured YAML (ADR-0024).",
    )
    p.add_argument("paths", nargs="+", type=Path, help="Legacy .md file(s).")
    p.add_argument("--kind", choices=["promptbook", "run"], default=None,
                   help="Force kind; else auto-detect from frontmatter.")
    p.add_argument("--dry-run", action="store_true",
                   help="Emit YAML to stdout; write/relocate nothing.")
    p.add_argument("--relocate", action="store_true",
                   help="After a clean migration, git mv the original into --legacy-root.")
    p.add_argument("--legacy-root", type=Path, default=None,
                   help="Destination tree for preserved originals "
                        "(default: <docs_dir>/promptbooks/legacy per the repo-root .crux).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Correctness-critical: migration recomputes book_content_hash and emits
    # the canonical YAML — require real YAML (PB-0026), uv-repair if possible.
    try:
        _yaml_min_mod.ensure_real_yaml(__file__)
    except _yaml_min_mod.YamlCapabilityError as exc:
        print(f"migrate-promptbooks: {exc}", file=sys.stderr)
        return 2
    # Pre-warm the .crux resolution unconditionally so a config error always
    # surfaces through the JSON contract here — never as a raw traceback from
    # a later _find_book_yaml/_relocate call (those run outside this handler).
    try:
        pb_root = _docs_pb_root()
    except _crux_config.CruxConfigError as exc:
        print(json.dumps({"errors": [{"error": f".crux configuration error: {exc}"}]}))
        return 1
    if args.legacy_root is None:
        args.legacy_root = pb_root / "legacy"
    all_errors: list[dict] = []
    for path in args.paths:
        if not path.is_file():
            all_errors.append({"file": str(path), "error": "file not found"})
            continue
        try:
            all_errors.extend(
                migrate_path(path, args.kind, args.dry_run, args.relocate, args.legacy_root)
            )
        except (_yaml_min_mod.YamlCapabilityError, _VP.YamlCapabilityError) as exc:
            # Defense-in-depth (the entry guard should prevent this): a
            # capability error must hit the crash lane, never a traceback or
            # the findings JSON. Mirrors validate-promptbook's main loop.
            print(f"migrate-promptbooks: {exc}", file=sys.stderr)
            return 2
    if all_errors:
        print(json.dumps({"errors": all_errors}, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
