#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""migrate-tree.py — the schema_version 4 -> 5 migration rung.

Relocates a crux tree to `bionic/` and unifies the invariants concern into one
folder. Invoked by `audit-docs --migrate`; runnable directly for testing.

**This is a staged merge, not a rename.** `bionic/` already exists in a v4 tree
(it holds the invariants check suite), so moving `docs/` onto it with a plain
rename would nest the tree as `bionic/docs/` — the exact arrangement this
migration eliminates — and `docs/invariants/` would collide with
`bionic/invariants/`. Every safety property below exists because a review of an
earlier design found it would have deleted the invariants concern.

Ordering, and why each step sits where it does:

  1. Preconditions. Fail closed on anything ambiguous.
  2. Write the marker, recording source, step, and the SOURCE INVENTORY. The
     inventory is what makes replay decidable: after a crash, an entry missing
     from the source is identifiable as already-moved precisely because it
     appears in the recorded inventory.
  3. Clear the check namespace FIRST — bionic/invariants/<id>.md moves down into
     bionic/invariants/checks/ — so nothing from the ledger can collide with a
     check when the ledger arrives.
  4. Merge the tree entry by entry. Directory meets directory => recurse.
  5. Move manifest.yml LAST. It is discovery's key, so while it remains at the
     source, resolution still returns the source tree and a re-run resumes from
     there. Moving it first would strand a torn tree that discovery reads as
     already migrated.
  6. Merge the config (never overwrite — an existing artifact_prefix is baked
     into every id on disk) and set schema_version to "5".
  7. Remove the emptied source, then the marker. The marker is deleted last, so
     its presence always means "unfinished".

Exit codes: 0 clean, 1 refusal/validation error with JSON on stdout, 2
capability error with a message on stderr.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

MARKER_NAME = ".migrating"
TARGET_SCHEMA = "5"
SOURCE_SCHEMA = "4"
DEFAULT_TREE = "bionic"
LEGACY_TREE = "docs"


class MigrationError(Exception):
    """A refusal that belongs on the exit-1 lane."""


# ──────────────────────────── small helpers ───────────────────────────────


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _write_atomic(path: Path, text: str) -> None:
    # Guarded once `_ROOT` is established; the pre-migrate config read path calls
    # this only for in-repo config, and the guard is a no-op before `_ROOT` is set
    # (no mutation has a repo context to violate yet).
    if _ROOT is not None:
        # A file's parent may BE the repo root (`.bionic.yml` lives there);
        # `contained()` deliberately rejects the root for TREES, so this path
        # uses the weaker "at or under the root" test.
        rp = path.parent.resolve()
        if not rp.is_relative_to(_ROOT.resolve()):
            raise MigrationError(
                f"refusing to write {path}: its parent resolves outside the repository root."
            )
        if path.is_symlink():
            raise MigrationError(f"{path} is a symlink; refusing to write through it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def is_crux_manifest(path: Path) -> bool:
    """A manifest counts only if it carries schema_version AND concerns_enabled."""
    text = _read(path)
    if text is None:
        return False
    return (
        re.search(r"^schema_version\s*:", text, re.MULTILINE) is not None
        and re.search(r"^concerns_enabled\s*:", text, re.MULTILINE) is not None
    )


def read_schema_version(manifest: Path) -> str | None:
    text = _read(manifest)
    if text is None:
        return None
    m = re.search(r"""^schema_version\s*:\s*["']?([^"'\s#]+)["']?""", text, re.MULTILINE)
    return m.group(1) if m else None


# ───────────────────────────── the marker ─────────────────────────────────


class Marker:
    """The in-flight migration record. Written atomically; deleted last."""

    def __init__(self, path: Path, source: str, step: int, inventory: list[str]):
        self.path, self.source, self.step, self.inventory = path, source, step, inventory

    @classmethod
    def load(cls, path: Path) -> Marker | None:
        text = _read(path)
        if text is None:
            return None
        src = re.search(r"^source\s*:\s*(.+?)\s*$", text, re.MULTILINE)
        if not src:
            return None  # unparseable marker accounts for nothing
        step = re.search(r"^step\s*:\s*(\d+)\s*$", text, re.MULTILINE)
        inv = re.findall(r"^\s+-\s+(.+?)\s*$", text, re.MULTILINE)
        return cls(path, src.group(1).strip("'\""), int(step.group(1)) if step else 0, inv)

    def save(self) -> None:
        lines = [f"source: {self.source}", f"step: {self.step}", "inventory:"]
        lines += [f"  - {e}" for e in self.inventory]
        _write_atomic(self.path, "\n".join(lines) + "\n")

    def advance(self, step: int) -> None:
        self.step = step
        self.save()


# ──────────────────────── per-entry classification ────────────────────────


def classify(src: Path, dst: Path, inventory: set[str], rel: str) -> str:
    """Four-way classification (ADR-0059). Returns move | skip-done | recurse | collide.

    The third row is why both sides plus the inventory must be consulted: an
    already-moved entry and a genuine collision are otherwise identical.
    """
    s, d = src.exists(), dst.exists()
    if s and d:
        if src.is_dir() and dst.is_dir():
            return "recurse"  # the invariants merge lives here
        return "collide"
    if s and not d:
        return "move"
    if not s and d:
        return "skip-done" if rel in inventory else "collide"
    return "skip-none"


def merge_entry(src: Path, dst: Path, inventory: set[str], rel: str, moved: list[str]) -> None:
    verdict = classify(src, dst, inventory, rel)
    if verdict == "move":
        # A symlinked destination directory would let recursion write outside;
        # treat it as a collision rather than following it.
        if dst.parent.is_symlink():
            raise MigrationError(f"destination parent {dst.parent} is a symlink; refusing to follow it.")
        g_mkdir(dst.parent)
        g_move(src, dst)
        moved.append(rel)
    elif verdict == "recurse":
        if src.is_symlink() or dst.is_symlink():
            raise MigrationError(
                f"symlinked directory at {rel!r}; refusing to merge through a link."
            )
        for child in sorted(src.iterdir()):
            merge_entry(child, dst / child.name, inventory, f"{rel}/{child.name}", moved)
        if not any(src.iterdir()):
            g_rmdir(src)
    elif verdict == "collide":
        raise MigrationError(
            f"collision at {rel!r}: both source and destination hold it and it is not "
            "an entry this migration moved. Refusing to overwrite or merge blindly."
        )


# ─────────────────────────── config merging ───────────────────────────────


def merge_config(root: Path, docs_dir: str) -> str:
    """Set `docs_dir`, preserving every other key. Never a template overwrite.

    An existing `artifact_prefix` is baked into every id already on disk, so
    discarding it is unrecoverable.
    """
    path = root / ".bionic.yml"
    legacy = root / ".crux"
    existing = _read(path)
    if existing is None and legacy.is_file():
        existing = _read(legacy)
    if existing is None:
        _write_atomic(path, f'config_version: "1"\ndocs_dir: {docs_dir}\nartifact_prefix: ""\n')
        return "created"

    if re.search(r"^docs_dir\s*:", existing, re.MULTILINE):
        merged = re.sub(r"^docs_dir\s*:.*$", f"docs_dir: {docs_dir}", existing, count=1,
                        flags=re.MULTILINE)
    else:
        merged = existing.rstrip("\n") + f"\ndocs_dir: {docs_dir}\n"
    _write_atomic(path, merged)
    return "merged"


def set_schema_version(manifest: Path) -> None:
    text = _read(manifest)
    if text is None:
        raise MigrationError(f"cannot read {manifest}")
    if not re.search(r"^schema_version\s*:", text, re.MULTILINE):
        raise MigrationError(f"{manifest} carries no schema_version")
    _write_atomic(manifest, re.sub(r"^schema_version\s*:.*$", f'schema_version: "{TARGET_SCHEMA}"',
                                   text, count=1, flags=re.MULTILINE))


# ───────────────────────────── the rung ───────────────────────────────────


def unify_invariants(tree: Path, bionic_inv: Path, moved: list[str]) -> None:
    """Step 3: clear the check namespace before any ledger content arrives.

    `reconciliation.yml` moves only when the destination differs from where it
    already sits. In the default form the suite and the destination are the same
    directory, so it is already home; in the custom form the tree stayed put and
    the suite must travel to it. Skipping it unconditionally left the manifest
    stranded at the repo root and the husk undeletable.
    """
    if not bionic_inv.is_dir():
        return
    # The SUITE SOURCE, not just the destination. `bionic/invariants` reached
    # through a symlink would otherwise have its contents moved OUT of an
    # external location — a removal outside the repo, which is exactly what the
    # module claims cannot happen.
    _guard(bionic_inv, "the invariants suite source")
    dest_inv = tree / "invariants"
    checks = dest_inv / "checks"
    # BOTH sides. The destination-only check left a source-side
    # `bionic/invariants/checks -> elsewhere-in-repo` followed on iteration,
    # draining an unrelated in-repo directory. Containment bounded the damage to
    # the repo but did not prevent it.
    for candidate in (dest_inv, dest_inv / "checks", bionic_inv, bionic_inv / "checks"):
        if candidate.is_symlink():
            raise MigrationError(
                f"symlinked invariants directory at {candidate}; refusing to read or place the "
                "suite through a link, even one that stays inside the repository."
            )
    same_place = bionic_inv.resolve() == dest_inv.resolve()
    for entry in sorted(bionic_inv.iterdir()):
        if entry.name == "checks" or entry.name.startswith("."):
            # Skipping these is correct only when the suite ALREADY sits at the
            # destination. When it does not (the custom form), an existing
            # checks/ directory or a dotfile would be stranded and the husk left
            # undeletable with no error — the silent-skip failure this rung
            # exists to prevent, one entry-type over.
            if same_place:
                continue
            if entry.name == "checks" and entry.is_dir():
                g_mkdir(checks)
                for child in sorted(entry.iterdir()):
                    target = checks / child.name
                    if target.exists():
                        raise MigrationError(
                            f"collision merging the check suite: {target} already exists."
                        )
                    g_move(child, target)
                    moved.append(f"checks/{child.name}")
                if not any(entry.iterdir()):
                    g_rmdir(entry)
                continue
            raise MigrationError(
                f"unexpected entry in the invariants suite: {entry}. Refusing to migrate "
                "around something this rung does not know how to place."
            )
        if entry.name == "reconciliation.yml":
            if bionic_inv.resolve() != dest_inv.resolve():
                g_mkdir(dest_inv)
                target = dest_inv / entry.name
                if target.exists():
                    raise MigrationError(
                        f"both {bionic_inv}/reconciliation.yml and {target} exist. Refusing "
                        "to overwrite a reconciliation manifest or merge two of them."
                    )
                g_move(entry, target)
                moved.append("reconciliation.yml")
            continue
        if entry.is_file() and entry.suffix == ".md":
            g_mkdir(checks)
            target = checks / entry.name
            if target.exists():
                # The checks/-directory and reconciliation paths refused on
                # collision; this one overwrote. Same guard, same reason.
                raise MigrationError(
                    f"collision merging the check suite: {target} already exists."
                )
            g_move(entry, target)
            moved.append(f"checks/{entry.name}")
            continue
        # Anything else — a stray .yml, a nested directory — would have been
        # silently skipped, leaving an undeletable husk with no error and no
        # report: the exact failure this rung claims to fix, one entry-type over.
        raise MigrationError(
            f"unexpected entry in the invariants suite: {entry}. Refusing to migrate around "
            "something this rung does not know how to place. Move or remove it, then re-run."
        )




def contained(root: Path, p: Path) -> bool:
    """True iff `p` resolves to a PROPER subdirectory of the resolved repo root.

    Module-level and used by EVERY path that reads, writes, or removes: the
    source, the destination, the marker holders, and the husk cleanup. Three
    review rounds each found another call site I had left unchecked — source,
    then marker-derived source, then destination — because each fix was a
    point-check at the site that happened to be under discussion. A chokepoint
    every path must pass is the only shape that stops the next one.
    """
    try:
        rp = p.resolve()
    except OSError:
        return False
    return rp != root.resolve() and rp.is_relative_to(root.resolve())


def require_contained(root: Path, p: Path, what: str) -> Path:
    """`contained` or raise. Returns `p` so it can wrap an expression."""
    if not contained(root, p):
        raise MigrationError(
            f"{what} {p} resolves outside the repository root (or to the root itself). "
            "Refusing to read, write, or remove a path this repo does not contain."
        )
    return p


# ───────────────── guarded mutation primitives (the real chokepoint) ──────────
#
# Four review rounds each found another unchecked call site. The pattern was
# always the same: a `require_contained()` call added at whichever site was
# under discussion, while the next site kept its raw `shutil.move` / `mkdir` /
# `rmdir`. A helper call sites must REMEMBER to call is not a chokepoint.
#
# These wrappers are. Every mutation in this module goes through one, and each
# validates BOTH operands against the repo root — so a symlinked descendant
# (`bionic/invariants -> ../elsewhere`, `destination/adrs -> ../outside`) cannot
# route a write, a move, or a removal outside the repository no matter which
# code path reaches it. `_ROOT` is set once at the top of `migrate()`.

# Process-global, set at the top of every `migrate()` / `abandon()` call. A CLI
# run has exactly one repo root, so this is sound for the shipped entry point;
# a caller that drives several roots in one process must set it per call, which
# `migrate()` and `abandon()` both do.
_ROOT: Path | None = None


def _guard(p: Path, what: str) -> Path:
    if _ROOT is None:  # pragma: no cover — set before any mutation
        raise MigrationError("internal: repo root not established before a mutation")
    return require_contained(_ROOT, p, what)


def g_move(src: Path, dst: Path) -> None:
    """Move, with BOTH endpoints containment-checked — dst included.

    Guarding only `dst.parent` left a symlink AT `dst` able to redirect the
    write: `shutil.move` treats a symlink-to-directory as a directory and moves
    the source inside it. A dangling symlink at `dst` also passed `classify()`
    as `move` and would have been clobbered in place.
    """
    _guard(src, "a move source")
    _guard(dst.parent, "a move destination's parent")
    if dst.is_symlink():
        raise MigrationError(f"destination {dst} is a symlink; refusing to move through it.")
    if dst.exists():
        _guard(dst, "a move destination")
    shutil.move(str(src), str(dst))


def g_unlink(p: Path) -> None:
    """Remove a file, containment-checked."""
    _guard(p, "a file to remove")
    p.unlink(missing_ok=True)


def g_mkdir(p: Path) -> None:
    _guard(p, "a directory to create")
    p.mkdir(parents=True, exist_ok=True)


def g_rmdir(p: Path) -> None:
    _guard(p, "a directory to remove")
    p.rmdir()

def resolve_configured_tree(root: Path) -> str | None:
    """Return the `docs_dir` this repo declares, or None when it declares none.

    Reads BOTH config files, newest first — `.bionic.yml` then legacy `.crux` —
    through the same precedence the plugin's resolver uses. A shallow line-scan
    keeps this script stdlib-only, matching `is_crux_manifest` above.

    This function exists because its absence was a shipped bug: source discovery
    looked only at `docs/` and `bionic/`, so a repo using the documented
    relocation feature could not migrate at all, and forcing it with
    `--repo-root <subdir>` would have moved a deliberately-gitignored vault to a
    git-visible path and stranded the real invariants suite.
    """
    for name in (".bionic.yml", ".crux"):
        text = _read(root / name)
        if text is None:
            continue
        m = re.search(r"^docs_dir\s*:\s*(\S+)\s*$", text, re.MULTILINE)
        if m:
            return m.group(1).strip("'\"")
    return None

def migrate(root: Path, dry_run: bool = False, docs_dir: str | None = None) -> dict:
    global _ROOT
    root = root.resolve()
    _ROOT = root
    bionic = root / DEFAULT_TREE          # the destination is ALWAYS at the repo root
    legacy = root / LEGACY_TREE

    # Candidate source trees, widest first: an explicit --docs-dir, then whatever
    # the repo's own config declares, then the two conventional locations. The
    # configured tree is checked BEFORE the conventions so a relocated vault is
    # found where its owner put it rather than not at all.
    def _norm(v: str) -> str:
        """Trailing slashes and separator style must not defeat a string compare."""
        return PurePosixPath(v.replace("\\", "/")).as_posix().rstrip("/") or v

    configured_raw = docs_dir or resolve_configured_tree(root)
    configured = _norm(configured_raw) if configured_raw else None
    if configured is not None and not contained(root, root / configured):
        raise MigrationError(
            f"docs_dir {configured_raw!r} resolves outside the repository root (or to the "
            f"root itself). Refusing to migrate a tree this repo does not contain."
        )

    candidates: list[Path] = []
    if configured:
        candidates.append(root / configured)
    if docs_dir is None:
        # An explicit --docs-dir is AUTHORITATIVE: a typo must fail loudly rather
        # than silently migrating whichever conventional tree happens to exist.
        candidates += [legacy, bionic]

    # The marker lives at the DESTINATION, which under the custom form is the
    # configured tree — not bionic/ or docs/. Searching only the two conventional
    # locations meant an interrupted custom migration never resumed.
    # Marker discovery searches the repo's OWN configured tree as well as an
    # explicit override: hiding it meant a stale marker in the config-declared
    # tree went unfound, and the "explicit override is authoritative" refusal
    # never fired.
    declared = resolve_configured_tree(root)
    holder_names = [configured] if configured else []
    if declared and _norm(declared) not in holder_names:
        holder_names.append(_norm(declared))
    existing_marker = None
    for holder in [root / h for h in holder_names if contained(root, root / h)] + [bionic, legacy]:
        existing_marker = Marker.load(holder / MARKER_NAME)
        if existing_marker is not None:
            break
    # An explicit --docs-dir is authoritative over a stale marker too. Letting a
    # leftover marker silently redirect the operator's named tree would defeat
    # the same guarantee the fallback suppression above establishes.
    if existing_marker is not None and docs_dir is not None and \
            _norm(existing_marker.source) != configured:
        raise MigrationError(
            f"an in-flight marker names {existing_marker.source!r} but --docs-dir names "
            f"{configured!r}. Finish or `--abandon` that migration before overriding it."
        )

    seen: set[Path] = set()
    valid: list[Path] = []
    for c in candidates:
        rc = c.resolve()
        if rc in seen:
            continue
        seen.add(rc)
        if is_crux_manifest(c / "manifest.yml"):
            valid.append(c)

    def _label(p: Path) -> str:
        """Repo-relative, POSIX-separated, LEXICAL label for a candidate.

        Lexical on purpose. An earlier version used `p.resolve()`, which expands
        symlinks: a tree literally at `docs/` that symlinks elsewhere got labeled
        with its target, mis-firing the custom form and failing its own
        config-agreement check. Physical identity is still enforced separately by
        `_contained()` — the two questions are "what is this called?" and "is it
        inside the repo?", and conflating them broke both.
        """
        try:
            rel = p.relative_to(root)
        except ValueError:
            # Reachable only if a caller labels an uncontained path; every
            # SELECTED source is containment-checked before use, so this is a
            # defensive fallback rather than the unreachable branch an earlier
            # comment claimed it was.
            return p.as_posix()
        return rel.as_posix()

    # 1. Preconditions
    if len(valid) > 1 and (existing_marker is None or
                           existing_marker.source not in {_label(d) for d in valid}):
        raise MigrationError(
            "two crux trees found (" + " and ".join(f"{_label(d)}/manifest.yml" for d in valid) +
            ") and no marker accounts for the state. Refusing to guess which is "
            "authoritative or to merge two independent trees."
        )
    source = (root / existing_marker.source) if existing_marker else (
        valid[0] if valid else None)
    # Containment applies to EVERY selected source, not only the configured one.
    # A marker is repo-controlled content: a crafted or committed `.migrating`
    # naming `../elsewhere` would otherwise select — and under the custom form
    # also DESTINATION — a tree outside the repository. A conventional `docs/`
    # that symlinks outside is the same hazard by another route.
    #
    # Stated precisely: candidate manifests and markers are READ during discovery
    # above, before this point. What this guarantees is that nothing is WRITTEN,
    # moved, or removed outside the repo — an earlier comment overclaimed "before
    # any read", which was false.
    if source is not None:
        require_contained(root, source, "the selected tree")
    if source is None:
        if docs_dir is not None:
            raise MigrationError(
                f"--docs-dir {docs_dir!r} holds no valid manifest.yml. An explicit override is "
                "authoritative; refusing to fall back to a conventional tree you did not name."
            )
        hint = (f" (config declares docs_dir: {configured!r}, which holds no valid manifest.yml)"
                if configured else "")
        raise MigrationError(f"no crux tree found to migrate (no valid manifest.yml){hint}.")

    version = read_schema_version(source / "manifest.yml")
    if version == TARGET_SCHEMA and existing_marker is None:
        return {"status": "already-migrated", "tree": _label(source), "schema_version": version}
    if version != SOURCE_SCHEMA and existing_marker is None:
        raise MigrationError(
            f"tree schema_version is {version!r}; this rung migrates {SOURCE_SCHEMA!r} -> "
            f"{TARGET_SCHEMA!r}. Run the earlier rungs first."
        )

    # A config that names a third location disagrees with the tree being moved.
    # Direction matters: ask whether the CONFIG's value names the tree being
    # migrated or the destination — not whether the source appears in that pair.
    # The reversed form silently accepted any third-location config whenever the
    # source happened to be bionic/.
    if configured and docs_dir is None and configured not in (_label(source), DEFAULT_TREE):
        raise MigrationError(
            f"config declares docs_dir: {configured!r}, which is neither the tree being "
            f"migrated ({_label(source)!r}) nor the destination. Refusing to relocate a "
            "tree the config disagrees about."
        )

    # The custom form: a tree that is NOT at a conventional location stays where
    # its owner put it. Relocating it would move a deliberately-placed (often
    # gitignored) vault into a git-visible path — a privacy change no schema
    # migration is entitled to make. Only the invariants suite moves in.
    custom_form = _label(source) not in (LEGACY_TREE, DEFAULT_TREE)
    destination = source if (custom_form or _label(source) == DEFAULT_TREE) else bionic
    # The DESTINATION needs the same guard as the source. Checking only the
    # source left a `bionic -> ../elsewhere` symlink able to receive the whole
    # merge outside the repository, with a valid in-repo docs/ passing as source.
    require_contained(root, destination, "the destination tree")

    if dry_run:
        return {"status": "would-migrate", "source": _label(source),
                "destination": _label(destination), "form": "custom" if custom_form else "default",
                "resuming": existing_marker is not None}

    # 2. Marker with the source inventory
    def _walk(base: Path) -> list[str]:
        """Every entry, recursively, as repo-source-relative POSIX paths.

        Top-level names alone made replay undecidable for a nested merge: if
        `docs/foo/a` moved into an existing `bionic/foo/`, a crash left `foo/a`
        absent at source and present at destination — but only `foo` was in the
        inventory, so replay called it a collision instead of already-moved.
        """
        out: list[str] = []
        for child in sorted(base.rglob("*")):
            if child.name == MARKER_NAME:
                continue
            try:
                out.append(child.relative_to(base).as_posix())
            except ValueError:  # pragma: no cover
                continue
        return out

    inventory = existing_marker.inventory if existing_marker else _walk(source)
    marker = existing_marker or Marker(destination / MARKER_NAME, _label(source), 1, inventory)
    g_mkdir(destination)
    marker.path = destination / MARKER_NAME
    marker.save()

    inv_set = set(inventory)
    moved: list[str] = []

    # 3. Clear the check namespace before the ledger arrives.
    # `bionic / "invariants"` is anchored at the REPO ROOT, not at the source's
    # parent — under the custom form the v4 suite still lives at the root while
    # the tree lives elsewhere, and pointing this at the wrong parent is what
    # would have stranded it.
    unify_invariants(destination, bionic / "invariants", moved)
    marker.advance(3)

    # 4. Merge the tree, manifest deliberately excluded
    if destination != source:
        for entry in sorted(source.iterdir()):
            if entry.name in ("manifest.yml", MARKER_NAME):
                continue
            merge_entry(entry, destination / entry.name, inv_set, entry.name, moved)
    marker.advance(4)

    # 5. manifest.yml last — it is discovery's key
    if destination != source:
        src_manifest = source / "manifest.yml"
        if src_manifest.exists():
            g_move(src_manifest, destination / "manifest.yml")
            moved.append("manifest.yml")
    marker.advance(5)

    # 6. Config + schema version
    # `_label`, not `.name`: a relocated tree's last path segment ("docs" from
    # ".lodestar/docs") would rewrite the config to point at a directory that
    # does not exist, which resolution then refuses.
    cfg_action = merge_config(root, _label(destination))
    set_schema_version(destination / "manifest.yml")
    marker.advance(6)

    # 7. Remove the emptied source, then the marker.
    if destination != source and source.exists():
        leftovers = [e.name for e in source.iterdir()]
        if leftovers:
            raise MigrationError(
                f"source {source.name}/ is not empty after the merge ({leftovers}); "
                "refusing to remove a directory whose contents are unaccounted for."
            )
        g_rmdir(source)
    # Under the custom form the tree never moved, but the root-level v4 suite was
    # drained into it — remove the husk, and bionic/ itself if that emptied it.
    stale = bionic / "invariants"
    if custom_form and contained(root, stale) and stale.exists() and not any(stale.iterdir()):
        g_rmdir(stale)
        if bionic.exists() and not any(bionic.iterdir()):
            g_rmdir(bionic)
    g_unlink(marker.path)

    return {"status": "migrated", "source": _label(source), "destination": _label(destination),
            "form": "custom" if custom_form else "default", "config": cfg_action,
            "moved": len(moved), "schema_version": TARGET_SCHEMA}


def abandon(root: Path) -> dict:
    """Remove a marker after confirming the tree is coherent.

    A stale marker suppresses the dual-manifest refusal, so it needs an explicit
    exit rather than an indefinite silent suppression.

    The coherence pair includes the CONFIGURED tree. Checking only the two
    conventional locations meant a custom-form repo — where the real tree is at
    a configured path — could have its marker abandoned while two trees were
    still present, re-arming the ambiguity the marker was suppressing.
    """
    global _ROOT
    root = root.resolve()
    _ROOT = root
    removed = []
    configured = resolve_configured_tree(root)

    pair: list[Path] = []
    if configured:
        pair.append(root / configured)
    pair += [root / LEGACY_TREE, root / DEFAULT_TREE]

    seen: set[Path] = set()
    valid: list[Path] = []
    for d in pair:
        if not contained(root, d):
            continue
        rd = d.resolve()
        if rd in seen:
            continue
        seen.add(rd)
        if is_crux_manifest(d / "manifest.yml"):
            valid.append(d)

    for holder in pair:
        if not contained(root, holder):
            continue  # never unlink outside the repository
        marker = holder / MARKER_NAME
        if not marker.is_file():
            continue
        if len(valid) > 1:
            raise MigrationError(
                "refusing to abandon: two crux trees are still present (" +
                " and ".join(str(d.relative_to(root)) for d in valid) +
                "). Finish the migration or reconcile the trees by hand first."
            )
        g_unlink(marker)
        removed.append(str(marker.relative_to(root)))
    return {"status": "abandoned" if removed else "no-marker", "removed": removed}


def find_marker(root: Path) -> str | None:
    """Used by the warn-on-marker guard in every non-migrate command.

    Searches the configured tree too: under the custom form the marker lives
    there, not at either conventional location.
    """
    root = Path(root)
    configured = resolve_configured_tree(root)
    holders = ([root / configured] if configured else []) + [root / DEFAULT_TREE, root / LEGACY_TREE]
    for holder in holders:
        if not contained(root, holder):
            continue  # a config naming an out-of-repo tree names nothing we may touch
        marker = holder / MARKER_NAME
        if marker.is_file():
            try:
                return str(marker.relative_to(root))
            except ValueError:
                return str(marker)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="crux tree migration rung (schema 4 -> 5)")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--dry-run", action="store_true", help="report what would happen; write nothing")
    ap.add_argument("--docs-dir", default=None,
                    help="explicit source tree, repo-root-relative. Escape hatch for a layout the "
                         "config does not declare; overrides config resolution.")
    ap.add_argument("--abandon", action="store_true", help="remove a stale in-flight marker")
    args = ap.parse_args(argv)

    root = Path(args.repo_root)
    try:
        payload = abandon(root) if args.abandon else migrate(
            root, dry_run=args.dry_run, docs_dir=args.docs_dir)
    except MigrationError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    except OSError as exc:
        sys.stderr.write(f"migrate-tree.py: {exc}\n")
        return 2
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
