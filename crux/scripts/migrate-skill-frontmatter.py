#!/usr/bin/env python3
"""One-shot migration: move crux's extended SKILL.md frontmatter fields
into a `metadata:` block, per ADR-0005.

Before:
    ---
    name: dev-cycle
    description: '...'
    tags: [a, b, c]
    bundles: [crux-docs]
    owner: crux
    version: "0.1.0"
    risk_level: low
    status: production
    ---

After:
    ---
    name: dev-cycle
    description: '...'
    metadata:
      tags: "a, b, c"
      bundles: "crux-docs"
      owner: "crux"
      version: "0.1.0"
      risk_level: "low"
      status: "production"
    ---

CSV encoding for list-valued fields: ", " (comma + single space).

Reads SKILL.md via the same tolerant YAML parser that validate-catalog.py
uses, so it can ingest the current flow-style frontmatter. Re-emits the
frontmatter block in deterministic block-style YAML. Body bytes are
preserved exactly.

Idempotent: a file that already has the new shape is left untouched.

Usage:
    python3 crux/scripts/migrate-skill-frontmatter.py SKILL_DIR [SKILL_DIR ...]
    python3 crux/scripts/migrate-skill-frontmatter.py --all   # all skills in crux/skills/
    python3 crux/scripts/migrate-skill-frontmatter.py --dry-run --all
"""

from __future__ import annotations

import argparse

# Reuse validate-catalog.py's minimal YAML parser. Import by file path since
# the script has a hyphen in its name and isn't a normal module.
import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
VC_PATH = SCRIPTS_DIR / "validate-catalog.py"
_spec = importlib.util.spec_from_file_location("_vc", VC_PATH)
assert _spec and _spec.loader
_vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vc)  # type: ignore[union-attr]

load_yaml = _vc.load_yaml

# Top-level keys that the Agent Skills Spec allows.
SPEC_TOPLEVEL = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}

# Extended crux fields that move under `metadata:`.
# Order here is the order they will be emitted under `metadata:`.
METADATA_KEYS_ORDERED = [
    "tags",          # list → CSV string
    "bundles",       # list → CSV string
    "owner",
    "version",
    "risk_level",
    "status",
    "requires_env",  # list → CSV string
    "origin",
    "origin_ref",
    "origin_date",
]

LIST_VALUED = {"tags", "bundles", "requires_env"}


def split_frontmatter(text: str) -> tuple[str, str, str]:
    """Return (leading_marker, frontmatter_block, body_with_trailing_marker).
    Raises ValueError if the file isn't a valid frontmatter document.
    """
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        raise ValueError("file does not start with '---'")
    # Find the closing '---' on its own line.
    lines = text.splitlines(keepends=True)
    # First line is the opening '---'.
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("frontmatter not closed by '---'")
    leading = lines[0]
    fm_block = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx:])  # closing '---' + everything after
    return leading, fm_block, body


def _yaml_quote(value: str) -> str:
    """Emit a YAML double-quoted string. Always quote — keeps emit deterministic
    and side-steps strictyaml's bare-string ambiguity rules.
    """
    # Escape backslashes and double quotes.
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _emit_description(value: str) -> str:
    """Description preservation. The Agent Skills Spec treats `description`
    as a single-line free-form string (≤1024 chars). Folded-scalar inputs
    arrive with their newlines already collapsed to spaces — but `_parse_minimal_yaml`
    preserves one trailing newline (clip chomp). Strip trailing whitespace,
    and collapse any remaining internal newlines to spaces so the emitted
    form is a single double-quoted line that round-trips through the parser
    cleanly.
    """
    normalized = " ".join(value.split())  # collapses any whitespace runs
    return _yaml_quote(normalized)


def _csv_join(items: list) -> str:
    """Comma + single space, items stripped. Reject empty items (would round-trip
    to a phantom empty tag).
    """
    out: list[str] = []
    for item in items:
        s = str(item).strip()
        if s == "":
            raise ValueError(f"empty list item in {items!r}")
        if "," in s:
            raise ValueError(f"list item contains comma (invalid in CSV encoding): {s!r}")
        out.append(s)
    return ", ".join(out)


def migrate(parsed: dict) -> dict:
    """Return a new dict with extended fields moved under metadata: as CSV strings.
    Idempotent: if `metadata` already exists AND no extended fields exist at
    top level, returns parsed unchanged (a copy, but byte-equivalent on re-emit).
    """
    has_extended_at_top = any(k in parsed for k in METADATA_KEYS_ORDERED)
    if not has_extended_at_top:
        return dict(parsed)  # already migrated

    new: dict = {}
    # Required-by-spec keys first, in canonical order.
    if "name" in parsed:
        new["name"] = parsed["name"]
    if "description" in parsed:
        new["description"] = parsed["description"]
    # Other spec top-level keys preserved if present.
    for k in ("license", "allowed-tools", "compatibility"):
        if k in parsed:
            new[k] = parsed[k]

    # Build metadata block from extended fields + any existing metadata dict.
    existing_meta = parsed.get("metadata", {})
    if not isinstance(existing_meta, dict):
        existing_meta = {}

    metadata: dict = {}
    for k in METADATA_KEYS_ORDERED:
        if k not in parsed:
            continue
        v = parsed[k]
        if k in LIST_VALUED:
            if v is None:
                continue
            if not isinstance(v, list):
                # Already a CSV string — pass through but normalize.
                tokens = [t.strip() for t in str(v).split(",") if t.strip()]
                metadata[k] = ", ".join(tokens)
            else:
                metadata[k] = _csv_join(v)
        else:
            if v is None:
                continue
            metadata[k] = str(v)

    # Preserve any pre-existing metadata.* keys NOT in METADATA_KEYS_ORDERED,
    # appended at the end (alphabetical).
    extra_keys = sorted(set(existing_meta.keys()) - set(METADATA_KEYS_ORDERED))
    for k in extra_keys:
        metadata[k] = str(existing_meta[k])

    if metadata:
        new["metadata"] = metadata
    return new


def emit_frontmatter(d: dict) -> str:
    """Emit a deterministic block-style YAML frontmatter block (no opening /
    closing `---` markers — caller adds them).
    """
    lines: list[str] = []

    # Required top-level keys first, in spec-canonical order.
    if "name" in d:
        lines.append(f"name: {d['name']}")  # bare-string OK if no special chars
    if "description" in d:
        lines.append(f"description: {_emit_description(str(d['description']))}")
    for k in ("license", "allowed-tools", "compatibility"):
        if k in d:
            lines.append(f"{k}: {_yaml_quote(str(d[k]))}")

    if "metadata" in d and d["metadata"]:
        lines.append("metadata:")
        meta = d["metadata"]
        for mk, mv in meta.items():
            # All metadata values are strings (or coerced to strings by skills-ref).
            lines.append(f"  {mk}: {_yaml_quote(str(mv))}")

    return "\n".join(lines) + "\n"


def migrate_file(path: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Migrate one SKILL.md. Returns (changed, message).
    `changed=False` means the file was already in the new shape (idempotent).
    """
    text = path.read_text()
    try:
        leading, fm_block, body = split_frontmatter(text)
    except ValueError as e:
        return False, f"SKIP ({e})"

    parsed = load_yaml(fm_block)
    if not isinstance(parsed, dict) or not parsed:
        return False, "SKIP (empty or non-dict frontmatter)"

    new_parsed = migrate(parsed)

    # Idempotency check: if migrate returned the same dict (no extended fields
    # at top), don't write.
    has_extended_at_top = any(k in parsed for k in METADATA_KEYS_ORDERED)
    if not has_extended_at_top:
        return False, "OK (already migrated)"

    new_fm = emit_frontmatter(new_parsed)
    new_text = leading + new_fm + body

    if dry_run:
        return True, "WOULD MIGRATE"

    path.write_text(new_text)
    return True, "MIGRATED"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="SKILL.md files or skill directories")
    ap.add_argument("--all", action="store_true",
                    help="migrate every directory under crux/skills/")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would change without writing")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.all:
        skills_root = SCRIPTS_DIR.parent / "skills"
        for d in sorted(skills_root.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                targets.append(d / "SKILL.md")
    for p_str in args.paths:
        p = Path(p_str)
        if p.is_dir():
            sm = p / "SKILL.md"
            if sm.exists():
                targets.append(sm)
        elif p.is_file():
            targets.append(p)

    if not targets:
        print("no SKILL.md files found", file=sys.stderr)
        return 2

    changed_count = 0
    repo_root = SCRIPTS_DIR.parent.parent
    for sm in targets:
        sm_abs = sm.resolve()
        try:
            display = sm_abs.relative_to(repo_root)
        except ValueError:
            display = sm
        changed, msg = migrate_file(sm_abs, dry_run=args.dry_run)
        prefix = "CHG" if changed else "   "
        print(f"{prefix}  {display}: {msg}")
        if changed:
            changed_count += 1

    print(f"\n{changed_count} of {len(targets)} files {'would change' if args.dry_run else 'changed'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
