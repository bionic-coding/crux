#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6.0"]
# ///
"""generate-rules-catalog.py — project this project's own rules into a catalog the plugin ships.

WHY THIS EXISTS. The plugin cites its own rules by slug on the surfaces it ships, and until this
catalog it shipped nothing that defined one. The release artifact carries no decision tree, so
every one of those citations was unresolvable for the reader it shipped to, while the shipped
contract said a citation must resolve. Per rule:citation-resolves-by-its-citing-surface, a
citation on a shipped surface resolves against this catalog; per
rule:shipped-catalog-is-derived-and-names-no-decision-record, this catalog is derived and carries
no decision-record identifier.

INPUT DOMAIN, and why it is the cited set rather than every rule. The catalog carries the DISTINCT
slugs cited on shipped surfaces, excluding test fixtures and the catalog's own output so the
projection cannot feed on itself. A citation naming a slug the catalog does not yet carry drifts
it until this runs; a citation naming a slug already carried drifts nothing, and removing a slug's
last citation drifts it again. That is what makes the drift gate a coverage gate for slugs.

NO DECISION-RECORD IDENTIFIER. `source_adr` is deliberately dropped. The catalog directory is not
one of the three prose surfaces the release-content scan governs, so carrying it would be legal —
it is omitted because a reader without this project cannot open that record, and the citation form
those surfaces use names a rule rather than a record.

Exit codes follow the repository convention: 0 clean, 1 drift (valid JSON on stdout), 2
environment or input error (stderr, no stdout payload).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import summaries_projection as sp  # noqa: E402

# The citation token the contract's grammar defines: `rule:` followed by a lowercase
# letter, then lowercase letters, digits and hyphens. The token ends at the first
# character outside that set, which is what makes the `rule:<slug>` placeholder form
# a non-token.
CITATION_RE = re.compile(r"rule:([a-z][a-z0-9-]*)")

# Shipped surfaces scanned for citations. `crux/catalog` is excluded so the projection
# cannot feed on itself, and `crux/scripts/tests` because a fixture citation is test
# data rather than a claim a reader acts on.
SCAN_ROOTS = ("skills", "agents", "templates", "scripts")
EXCLUDED_PARTS = ("tests", "catalog", "__pycache__")
MAX_FILE_BYTES = 4 * 1024 * 1024  # the sibling lint's ceiling
TEXT_SUFFIXES = {".md", ".tmpl", ".py", ".yaml", ".yml", ".json", ".toml", ".sh", ".txt"}


def cited_slugs(plugin_root: Path) -> set[str]:
    """Every distinct slug cited on a shipped surface, excluding fixtures and the catalog."""
    found: set[str] = set()
    for root in SCAN_ROOTS:
        base = plugin_root / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if any(part in EXCLUDED_PARTS for part in path.relative_to(plugin_root).parts):
                continue
            # Containment and size refusals, matching the sibling citation lint rather
            # than diverging from it: a symlink out of the plugin root is not a shipped
            # surface, and an oversized file is refused rather than read whole.
            try:
                real = path.resolve(strict=True)
                real.relative_to(plugin_root.resolve())
                if real.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = real.read_text(encoding="utf-8")
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            found.update(CITATION_RE.findall(text))
    return found


def build_catalog(repo_root: Path, plugin_root: Path) -> dict:
    """The catalog payload: slug -> {rule, domain}, sorted, no decision-record identifier."""
    # No `hasattr` guard with a hardcoded `bionic` fallback: the tree's name is
    # configurable, so a helper rename would have silently projected the wrong tree
    # instead of failing. An AttributeError here is the exit-2 lane, which is correct.
    docs = sp.resolve_tree(repo_root)
    records = sp.live_records(
        sp.collect_records(docs / "adrs", governs_from=None, observations=docs / "observations")
    )
    by_slug: dict[str, dict] = {}
    for r in records:
        handle = r.get("handle") or ""
        if "/" not in handle:
            continue
        slug = handle.split("/", 1)[1]
        by_slug[slug] = {"rule": r.get("rule", ""), "domain": r.get("domain", "")}

    wanted = cited_slugs(plugin_root)
    missing = sorted(s for s in wanted if s not in by_slug)
    rules = {s: by_slug[s] for s in sorted(wanted & set(by_slug))}
    return {"schema": "1", "rules": rules, "unresolved": missing}


def render(catalog: dict) -> str:
    return json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    plugin_root = repo_root / "crux"
    target = plugin_root / "catalog" / "rules.json"

    # SURFACE-ABSENT LANE, on the `extract-code-docs` model and for the same reason the
    # parity check skips a clause whose twin is absent. This regenerator projects THIS
    # project's own governs blocks, which exist only in the authoring checkout; an
    # installed project has the plugin in its plugin cache, not at `<repo>/crux/`.
    # Without this lane a downstream `check-drift` run reported drift against a file it
    # had no business owning, and the remedy that row names WROTE a `crux/` tree into the
    # reader's repository — which the decision explicitly disclaims.
    if not (plugin_root / "scripts" / Path(__file__).name).is_file():
        print(json.dumps({"surface_absent": True, "drift": False, "written": None,
                          "reason": "not the plugin's authoring checkout; nothing to project"},
                         sort_keys=True))
        return 0

    try:
        catalog = build_catalog(repo_root, plugin_root)
    except Exception as exc:  # noqa: BLE001 — environment/input failures are the exit-2 lane
        print(f"generate-rules-catalog: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if catalog["unresolved"]:
        print(
            "generate-rules-catalog: shipped surfaces cite slugs no live rule defines: "
            f"{catalog['unresolved']}",
            file=sys.stderr,
        )
        return 2

    payload = render(catalog)
    current = target.read_text(encoding="utf-8") if target.is_file() else None

    if args.dry_run:
        drift = current != payload
        print(json.dumps({"drift": drift, "path": str(target.relative_to(repo_root)),
                          "rules": len(catalog["rules"])}, sort_keys=True))
        return 1 if drift else 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")
    print(json.dumps({"written": str(target.relative_to(repo_root)),
                      "rules": len(catalog["rules"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
