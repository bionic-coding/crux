#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Extract documentation from source code per docs/manifest.yml.

Dispatcher: reads manifest.yml, loads per-language extractor plugins from
./extractors/, runs them, writes results under docs/code/.

Each plugin module under scripts/extractors/<name>.py exposes:

    def discover(repo_root: Path, config: dict) -> list[SourceUnit]: ...
    def extract(unit: SourceUnit) -> DocPage: ...

The dispatcher:
  1. Parses manifest.yml at --config (default: docs/manifest.yml).
  2. For each enabled language under code.extractors, imports the matching
     module from scripts/extractors/<extractor-name>.py.
  3. Calls discover() then extract() on each unit.
  4. Writes pages to <output-dir>/<lang-namespace>/<unit>.md.
  5. Writes a fresh <output-dir>/_meta/manifest.json.

Determinism: alphabetical ordering everywhere; no timestamps in page body
(only in _meta/manifest.json).

Regenerative invariant: any pre-existing content under <output-dir> that is
NOT listed in the newly-built manifest is removed. Hand-edits never survive.

--dry-run runs discover() + extract() but emits a diff summary instead of
writing pages. Exits 1 if drift detected, 0 if clean (CI-friendly).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

EXTRACTOR_VERSION = "1"


# ────────────────────────── shared data contracts ──────────────────────────


@dataclass
class SourceUnit:
    """One documentable unit discovered by an extractor.

    Fields:
        language: the extractor language key (e.g. "elixir").
        identifier: the unit name (e.g. "MyApp.MyModule" or "lib/foo/bar.ex").
                    Determines the output filename via path-safe transformation.
        source_path: relative path (from repo root) to the file backing this
                     unit. Used for the manifest provenance row.
        payload: arbitrary extractor-internal data carried into extract().
                 Not persisted; opaque to the dispatcher.
    """

    language: str
    identifier: str
    source_path: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocPage:
    """One rendered documentation page emitted by an extractor.

    Fields:
        title: the page's H1 (and the page's logical name).
        path: output path RELATIVE to --output-dir. The dispatcher writes the
              file at <output-dir>/<path>. Must end in .md.
        body: full markdown body. The dispatcher writes it verbatim; do NOT
              embed timestamps or other non-deterministic content here.
        source_path: relative path (from repo root) to the underlying source.
                     Carried into _meta/manifest.json.
    """

    title: str
    path: str
    body: str
    source_path: str


# ─────────────────────────────── argparse ──────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="extract-code-docs",
        description=(
            "Regenerate docs/code/ from in-source documentation. "
            "Reads docs/manifest.yml to decide which language extractors to run."
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        type=Path,
        help="Path to the docs manifest (default: <docs_dir>/manifest.yml, "
             "with docs_dir from the repo-root .crux per ADR-0032).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        type=Path,
        help="Output directory (default: <docs_dir>/code per the repo-root .crux).",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Filter to one extractor by language key. Default: run all enabled.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run discover()+extract() but do NOT write pages. Exit 1 if drift.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging to stderr.",
    )
    return parser.parse_args(argv)


# ─────────────────────── repo-root .crux config loader ────────────────────


def _load_crux_config():
    """Import the sibling crux_config module (hyphen-free, but scripts/ may not
    be on sys.path) and resolve the repo-root .crux per ADR-0032."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "crux_config", Path(__file__).resolve().parent / "crux_config.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    global CruxConfigError
    CruxConfigError = mod.CruxConfigError
    return mod.load_config()


class CruxConfigError(Exception):
    # Placeholder so `except CruxConfigError` resolves at module scope before
    # crux_config is loaded. _load_crux_config rebinds this global to the real
    # class BEFORE calling load_config(), and except-clause types are evaluated
    # at raise time — so the except always catches the real class. Do not
    # "clean up" the global rebind without restructuring the lazy load.
    pass


# ─────────────────────────── minimal YAML loader ──────────────────────────


def load_yaml(path: Path) -> dict:
    """Load manifest.yml. Uses PyYAML when available; otherwise a minimal
    hand-rolled parser sufficient for crux's flat-ish manifest format.
    """
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return _parse_minimal_yaml(text)


def _parse_minimal_yaml(text: str) -> dict:
    """Tiny YAML subset: nested mappings via 2-space indent, scalars, and flow
    lists [a, b]. Enough for docs/manifest.yml. Comments stripped. No anchors,
    no multi-line strings, no block-style lists.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        # Strip trailing comments unless quoted.
        line = _strip_yaml_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if ":" not in content:
            continue
        key, _, value = content.partition(":")
        key = key.strip()
        value = value.strip()
        # Pop stack until current indent fits.
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else root
        if value == "":
            new: dict = {}
            if isinstance(parent, dict):
                parent[key] = new
            stack.append((indent, new))
        else:
            parsed = _parse_scalar(value)
            if isinstance(parent, dict):
                parent[key] = parsed
    return root


def _strip_yaml_comment(line: str) -> str:
    out = []
    in_str: str | None = None
    for ch in line:
        if in_str:
            out.append(ch)
            if ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'"):
            in_str = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out)


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p.strip()) for p in inner.split(",")]
    if value.lower() in ("null", "~", ""):
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    try:
        if "." not in value:
            return int(value)
        return float(value)
    except ValueError:
        return value


# ─────────────────────────── plugin discovery ─────────────────────────────


def _extractors_dir() -> Path:
    return Path(__file__).resolve().parent / "extractors"


def load_extractor_module(name: str):
    """Import scripts/extractors/<name>.py as a module."""
    path = _extractors_dir() / f"{name}.py"
    if not path.is_file():
        raise FileNotFoundError(f"extractor plugin not found: {path}")
    spec = importlib.util.spec_from_file_location(f"docs_suite_extractor_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load spec for {path}")
    module = importlib.util.module_from_spec(spec)
    # Make `from extractors.X import Y` style work by exposing the dispatcher
    # module so the plugin can reach SourceUnit/DocPage.
    sys.modules.setdefault("extract_code_docs_dispatcher", sys.modules[__name__])
    spec.loader.exec_module(module)
    return module


# ─────────────────────────── manifest helpers ─────────────────────────────


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_existing_manifest(meta_path: Path) -> dict:
    if not meta_path.is_file():
        return {"pages": []}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"pages": []}


def build_manifest(pages: list[DocPage]) -> dict:
    # NOTE: per-row `extracted_at` was intentionally removed — its presence
    # caused manifest.json to churn on every run (timestamp diff with no
    # content change), making "regenerate produces no diff" assertions
    # impossible. Provenance is recoverable via `git log` on the file.
    # The content-stable fields (source_path, doc_path, sha256,
    # extractor_version) are sufficient for drift detection.
    rows = []
    for page in sorted(pages, key=lambda p: p.source_path):
        rows.append(
            {
                "source_path": page.source_path,
                "doc_path": page.path,
                "sha256": sha256_text(page.body),
                "extractor_version": EXTRACTOR_VERSION,
            }
        )
    return {"pages": rows, "extractor_version": EXTRACTOR_VERSION}


def diff_manifests(old: dict, new: dict) -> dict:
    """Compare two manifest dicts. Returns added/changed/removed page paths."""
    old_map = {row["doc_path"]: row["sha256"] for row in old.get("pages", [])}
    new_map = {row["doc_path"]: row["sha256"] for row in new.get("pages", [])}
    added = sorted(set(new_map) - set(old_map))
    removed = sorted(set(old_map) - set(new_map))
    changed = sorted(p for p in set(old_map) & set(new_map) if old_map[p] != new_map[p])
    return {"added": added, "changed": changed, "removed": removed}


def _atomic_write_text(path: Path, body: str) -> None:
    """Atomic UTF-8 text write with no platform newline translation.

    Writes to <path>.tmp then os.replace()s into place. We write bytes
    directly so Python does NOT translate '\\n' → '\\r\\n' on Windows;
    that translation would shift the file's sha256 across platforms and
    break the byte-stable regenerative output invariant.

    [SECURITY:S5] Neither the target nor `<path>.tmp` may be a symlink. The
    tmp path is predictable and `Path.write_bytes` follows a link, so a
    pre-created link turns a regeneration into a write into someone else's
    file, while `os.replace` moves the tmp PATH and leaves the link standing.
    Checked explicitly for a readable error, then created O_NOFOLLOW|O_EXCL so
    the check is not a TOCTOU window. This helper has BEHAVIORAL parity with
    the one in validate-catalog.py — same guards, same order, same exception
    type — but the two are not byte-identical: each names its own subject in
    its messages ("generated content" here, "catalog contents" there). Treat
    the messages as the only licensed difference. A fail-closed sibling sweep
    found the same gap in both, plus in `_yaml_min.write_catalog_yaml`, and
    all three were fixed together. Change one, change all three.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    for label, candidate in (("target", path), ("temporary file", tmp)):
        if candidate.is_symlink():
            raise OSError(
                f"refusing to write {path}: the {label} {candidate} is a symlink — "
                "writing through it would put generated content in the link's target"
            )
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    except FileExistsError as exc:
        raise OSError(
            f"refusing to write {path}: the temporary file {tmp} already exists; "
            "remove it after checking what created it"
        ) from exc
    except OSError as exc:  # ELOOP from O_NOFOLLOW, or an unwritable directory
        raise OSError(f"refusing to write {path}: cannot create {tmp} ({exc})") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body.encode("utf-8"))
        os.replace(tmp, path)
    except Exception:
        # Clean up partial tmp before re-raising (SC-1).
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


# ─────────────────────────────── pipeline ─────────────────────────────────


SAFE_PATH_RE = re.compile(r"[^A-Za-z0-9_./\-]")


def _safe_relpath(p: str) -> str:
    """Strip leading slashes; reject .. components."""
    p = p.lstrip("/")
    if any(part == ".." for part in p.split("/")):
        raise ValueError(f"unsafe doc path: {p!r}")
    return p


def run_extractor(
    name: str,
    config: dict,
    repo_root: Path,
    verbose: bool,
) -> list[DocPage]:
    module = load_extractor_module(name)
    if not hasattr(module, "discover") or not hasattr(module, "extract"):
        raise RuntimeError(f"extractor {name!r} missing discover/extract")
    units: list[SourceUnit] = list(module.discover(repo_root, config))
    if verbose:
        print(f"[{name}] discovered {len(units)} unit(s)", file=sys.stderr)
    units.sort(key=lambda u: (u.source_path, u.identifier))
    pages: list[DocPage] = []
    for unit in units:
        page = module.extract(unit)
        if page is None:
            continue
        if not isinstance(page, DocPage):
            # Allow extractors to return a duck-typed object.
            page = DocPage(
                title=getattr(page, "title", unit.identifier),
                path=getattr(page, "path"),
                body=getattr(page, "body"),
                source_path=getattr(page, "source_path", unit.source_path),
            )
        page.path = _safe_relpath(page.path)
        pages.append(page)
    pages.sort(key=lambda p: p.path)
    return pages


def write_pages(pages: list[DocPage], output_dir: Path, verbose: bool) -> None:
    """Write all pages and prune output-dir of stale files (regenerative).

    All writes are atomic (write-tmp + os.replace). Prune resolves the
    output_dir once and refuses to unlink any file whose resolved path
    escapes the tree — so symlinks pointing outside docs/code are skipped
    with a warning rather than blindly removed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_output = output_dir.resolve()
    # `kept` is normalized on resolved paths so the symmetry holds across
    # symlinks and relative components.
    kept: set[Path] = {
        (resolved_output / "_meta" / "manifest.json").resolve(),
        (resolved_output / "index.md").resolve(),
    }
    for page in pages:
        dest = output_dir / page.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(dest, page.body)
        kept.add(dest.resolve())
        if verbose:
            print(f"wrote {dest}", file=sys.stderr)
    # Prune: every .md under output_dir not in kept is deleted (regenerative
    # invariant). _meta/manifest.json is always kept. index.md is regenerated.
    for path in sorted(output_dir.rglob("*.md")):
        resolved = path.resolve()
        if resolved in kept:
            continue
        # Guard against symlinks (or rglob race) pointing OUTSIDE the
        # output tree — never unlink files we don't own.
        try:
            inside = resolved.is_relative_to(resolved_output)  # py3.9+
        except AttributeError:  # pragma: no cover — pre-3.9 fallback
            try:
                resolved.relative_to(resolved_output)
                inside = True
            except ValueError:
                inside = False
        if not inside:
            print(
                f"extract-code-docs: refusing to prune {path} "
                f"(resolves outside {resolved_output})",
                file=sys.stderr,
            )
            continue
        if verbose:
            print(f"pruned {path}", file=sys.stderr)
        path.unlink()
    _write_index(pages, output_dir)


def _write_index(pages: list[DocPage], output_dir: Path) -> None:
    """Write a deterministic docs/code/index.md grouped by language namespace."""
    by_lang: dict[str, list[DocPage]] = {}
    for page in pages:
        ns = page.path.split("/", 1)[0] if "/" in page.path else "_root"
        by_lang.setdefault(ns, []).append(page)
    lines: list[str] = ["# Code documentation", "", "_Regenerated by `extract-code-docs`. Do not hand-edit._", ""]
    for lang in sorted(by_lang):
        rows = sorted(by_lang[lang], key=lambda p: p.path)
        lines.append(f"## {lang} ({len(rows)})")
        lines.append("")
        for page in rows:
            lines.append(f"- [{page.title}]({page.path})")
        lines.append("")
    _atomic_write_text(output_dir / "index.md", "\n".join(lines))


def write_meta(manifest: dict, output_dir: Path) -> None:
    meta_dir = output_dir / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(
        meta_dir / "manifest.json",
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )


# ──────────────────────────────── main ────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Derived defaults come from the repo-root .crux (ADR-0032); an explicitly
    # passed flag wins unconditionally and is never recomputed.
    config_was_explicit = args.config is not None
    crux_repo_root = None
    if args.config is None or args.output_dir is None:
        try:
            _cfg = _load_crux_config()
        except CruxConfigError as exc:
            print(f"extract-code-docs: .crux configuration error: {exc}", file=sys.stderr)
            return 1
        crux_repo_root = _cfg.repo_root
        if args.config is None:
            args.config = _cfg.docs_root / "manifest.yml"
        if args.output_dir is None:
            args.output_dir = _cfg.docs_root / "code"

    if not args.config.is_file():
        print(f"extract-code-docs: config not found: {args.config}", file=sys.stderr)
        return 1
    manifest = load_yaml(args.config)
    # Destructive-consumer marker check (ADR-0032 §1): this script PRUNES
    # under the output dir, so refuse to treat a tree without a readable
    # schema_version as a crux tree.
    if not isinstance(manifest.get("schema_version"), (str, int)):
        print(
            f"extract-code-docs: {args.config} has no readable schema_version; refusing to operate on a non-crux tree",
            file=sys.stderr,
        )
        return 1
    code_cfg = (manifest.get("code") or {}).get("extractors") or {}
    if not isinstance(code_cfg, dict) or not code_cfg:
        print("extract-code-docs: no extractors configured under code.extractors.", file=sys.stderr)
        return 0

    # An explicitly passed --config always anchors repo_root (its own
    # parent.parent), regardless of other flags — pointing --config at a
    # foreign repo must scan THAT repo's sources, not the cwd's. Only a
    # .crux-derived config uses the .crux repo root (which, unlike
    # parent.parent, survives a multi-segment docs_dir like meta/docs).
    if config_was_explicit or crux_repo_root is None:
        repo_root = args.config.resolve().parent.parent
    else:
        repo_root = crux_repo_root
    if args.verbose:
        print(f"extract-code-docs: repo_root={repo_root}", file=sys.stderr)

    selected = sorted(code_cfg.items())
    if args.lang:
        selected = [(k, v) for k, v in selected if k == args.lang]
        if not selected:
            print(f"extract-code-docs: --lang {args.lang!r} not found in manifest", file=sys.stderr)
            return 1

    all_pages: list[DocPage] = []
    for lang_key, entry in selected:
        if not isinstance(entry, dict):
            print(f"extract-code-docs: skipping {lang_key!r} (not a mapping)", file=sys.stderr)
            continue
        extractor_name = entry.get("extractor") or lang_key
        try:
            pages = run_extractor(extractor_name, entry, repo_root, args.verbose)
        except FileNotFoundError as exc:
            print(f"extract-code-docs: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"extract-code-docs: extractor {extractor_name!r} failed: {exc}", file=sys.stderr)
            return 1
        all_pages.extend(pages)

    new_manifest = build_manifest(all_pages)
    meta_path = args.output_dir / "_meta" / "manifest.json"
    old_manifest = read_existing_manifest(meta_path)
    diff = diff_manifests(old_manifest, new_manifest)

    if args.dry_run:
        summary = {
            "added": len(diff["added"]),
            "changed": len(diff["changed"]),
            "removed": len(diff["removed"]),
            "pages_total": len(new_manifest["pages"]),
            "detail": diff,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        drift = bool(diff["added"] or diff["changed"] or diff["removed"])
        return 1 if drift else 0

    write_pages(all_pages, args.output_dir, args.verbose)
    write_meta(new_manifest, args.output_dir)

    print(
        f"extract-code-docs: wrote {len(all_pages)} page(s) "
        f"({len(diff['added'])} added, {len(diff['changed'])} changed, "
        f"{len(diff['removed'])} removed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
