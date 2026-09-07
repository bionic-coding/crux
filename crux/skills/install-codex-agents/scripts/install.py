#!/usr/bin/env python3
"""Install Crux-generated Codex agents into a target project without clobbering edits."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from codex_agents import SpecViolation, diff, generate, write  # noqa: E402


def _is_contained(candidate: Path, root: Path) -> bool:
    """Return True if candidate (already resolved) is root or lives under it.

    resolve-then-contain: a symlink whose resolved target stays under root is
    PERMITTED — this checks the final resolved location, not whether any path
    component is a symlink. Only an escape is refused. Stronger TOCTOU
    hardening (re-verifying between check and write, O_NOFOLLOW-style open
    discipline) is explicitly out of scope, mirroring the same containment
    proportionality this project applies to its other resolve-then-contain
    path checks elsewhere in the docs tooling.

    `Path.is_relative_to` exists on all supported interpreters (added in Python
    3.9, and crux requires >= 3.13); the `os.path.commonpath` branch is a
    belt-and-suspenders fallback, never reached on a supported interpreter.
    """
    try:
        return candidate == root or candidate.is_relative_to(root)
    except AttributeError:  # pragma: no cover - unreachable on Python >= 3.9
        try:
            return os.path.commonpath([str(root), str(candidate)]) == str(root)
        except ValueError:
            return False


def _containment_error(repo_root: Path, output_dir: Path, filenames: list[str]) -> str | None:
    """Return an error message if output_dir or any target filename escapes repo_root."""
    resolved_output_dir = output_dir.resolve()
    if not _is_contained(resolved_output_dir, repo_root):
        return (
            f"refusing to write: {output_dir} resolves outside the repo root "
            f"({resolved_output_dir} is not under {repo_root})"
        )
    for name in filenames:
        resolved_file = (output_dir / name).resolve()
        if not _is_contained(resolved_file, repo_root):
            return (
                f"refusing to write: {name} resolves outside the repo root "
                f"({resolved_file} is not under {repo_root})"
            )
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="replace changed Crux-managed agent files")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        print(json.dumps({"error": f"repo root is not a directory: {repo_root}"}))
        return 2

    output_dir = repo_root / ".codex" / "agents"

    # Path containment (resolve-then-contain): resolve the repo root and the
    # output path up front, and refuse to write when .codex/agents/ resolves
    # outside the resolved repo root.
    contain_error = _containment_error(repo_root, output_dir, [])
    if contain_error:
        print(json.dumps({"error": contain_error}))
        return 2

    try:
        generated = generate(PLUGIN_ROOT / "agents")
        added, changed, removed = diff(output_dir, generated)
    except SpecViolation as exc:
        # Fail-closed: a malformed or missing source agent, or a crux-*.toml
        # leaf that is a symlink (live or dangling), is refused rather than
        # read/clobbered through. Structured error, never a traceback.
        print(json.dumps({"error": str(exc)}))
        return 2

    # Re-check containment for every individual file this run would write or
    # remove, in case output_dir itself is contained but a specific existing
    # entry is a symlink escaping the repo root.
    contain_error = _containment_error(repo_root, output_dir, list(generated) + removed)
    if contain_error:
        print(json.dumps({"error": contain_error}))
        return 2

    if (changed or removed) and not args.force:
        print(json.dumps({
            "error": "generated Crux agents differ; review and rerun with --force",
            "added": added,
            "changed": changed,
            "removed": removed,
        }, indent=2))
        return 1

    try:
        written, removed = write(output_dir, generated)
    except SpecViolation as exc:
        # Fail-closed: write() refuses to clobber a crux-*.toml leaf that is
        # a symlink (in-repo or escaping target). Surface it as a structured
        # error, never a traceback.
        print(json.dumps({"error": str(exc)}))
        return 2
    print(json.dumps({"written": written, "removed": removed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
