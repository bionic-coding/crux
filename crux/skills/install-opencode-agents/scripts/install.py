#!/usr/bin/env python3
"""Install Crux-generated OpenCode agents into a target project without clobbering edits."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from opencode_agents import (  # noqa: E402
    SpecViolation,
    diff,
    generate,
    managed_filenames,
    write,
)

# The V2 runner this installer probes before writing. Overridable by
# `CRUX_OPENCODE2_BIN` so the refusal lane is reachable in a test and on a
# machine that installs the binary under another name; the default is the
# documented one.
V2_BINARY_ENV = "CRUX_OPENCODE2_BIN"
V2_BINARY_DEFAULT = "opencode2"


def _is_contained(candidate: Path, root: Path) -> bool:
    """Return True if candidate (already resolved) is root or lives under it.

    resolve-then-contain: a symlink whose resolved target stays under root is
    PERMITTED — this checks the final resolved location, not whether any path
    component is a symlink. Only an escape is refused. Stronger TOCTOU
    hardening (re-verifying between check and write, O_NOFOLLOW-style open
    discipline) is explicitly out of scope, mirroring the same containment
    proportionality install-codex-agents applies.

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


def _v2_preflight_error() -> str | None:
    """Return an error message when no OpenCode V2 runner is discoverable.

    The projection this installer writes is V2-only: a V1 runner reading it
    drops every deny. So the write path refuses unless `opencode2 --version`
    resolves and exits 0.

    NECESSARY, NOT SUFFICIENT — and the distinction is not a hedge. Exit 0
    proves a V2 binary is installed on this machine. It does not prove the
    runner that later reads the projection is V2: on a machine carrying both
    binaries a user passes this preflight and then invokes V1 by hand. That
    case is accepted residual risk covered by documentation, not by this
    check. The preflight reaches the installer's write path and nothing else;
    the manual `ln -s` install executes no crux code at all.
    """
    binary = os.environ.get(V2_BINARY_ENV) or V2_BINARY_DEFAULT
    resolved = shutil.which(binary)
    if resolved is None:
        return (
            f"refusing to write: no OpenCode V2 runner found. `{binary}` is not on PATH. "
            "The generated agents use the V2 `permissions` array, which a V1 runner "
            f"ignores. Install OpenCode V2, or set {V2_BINARY_ENV} to its path."
        )
    try:
        probe = subprocess.run(
            [resolved, "--version"],
            check=False, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"refusing to write: could not run `{binary} --version` ({exc})"
    if probe.returncode != 0:
        return (
            f"refusing to write: `{binary} --version` exited {probe.returncode}, so no "
            "OpenCode V2 runner is discoverable. The generated agents use the V2 "
            "`permissions` array, which a V1 runner ignores."
        )
    return None


class LegacyScanError(Exception):
    """The legacy directory exists but could not be listed.

    Its own class because the guard must FAIL CLOSED on it. Returning an empty
    offender list for an unreadable `.opencode/agent/` would let the installer
    write the plural directory beside a legacy copy it never managed to read —
    producing exactly the invisible shadow the guard exists to prevent, and
    reporting success while doing it.
    """


def _legacy_offenders(legacy_dir: Path, roster: frozenset[str]) -> list[str]:
    """Roster-named entries in the singular `.opencode/agent/`, sorted.

    "Populated" is at least one roster-named entry, not the whole roster.
    Crux stamps no provenance marker on a projected agent file, so membership
    is decided by roster filename alone — `managed_filenames()` IS that
    definition. A user's own `.opencode/agent/architect.md` is therefore
    indistinguishable from a crux-managed one and DOES trip the guard. That
    limitation is stated rather than worked around: refusal is still the
    default because the plural directory silently wins over the singular, so
    a stale singular copy is an invisible shadow rather than a visible
    conflict.
    """
    if not legacy_dir.is_dir():
        return []
    try:
        return sorted(entry.name for entry in legacy_dir.iterdir() if entry.name in roster)
    except OSError as exc:
        raise LegacyScanError(
            f"refusing to write: cannot list the legacy {legacy_dir} ({exc}). "
            "Whether it holds a shadow copy of a crux-managed agent is unknown, so "
            "this refuses rather than installing beside it."
        ) from exc


def _legacy_containment_error(
    repo_root: Path, legacy_dir: Path, output_dir: Path, names: list[str]
) -> str | None:
    """Resolve and contain BOTH endpoints of every planned move, before any move.

    The destination-directory check `main` already runs does not reach these:
    migration adds a SECOND source directory and moves files one at a time, so
    a legacy `.opencode/agent/<roster-name>.md` that is a symlink escaping the
    repo root would otherwise be relocated with no check at all.
    """
    for name in names:
        for label, path in (("source", legacy_dir / name), ("destination", output_dir / name)):
            resolved = path.resolve()
            if not _is_contained(resolved, repo_root):
                return (
                    f"refusing to migrate: {name} resolves outside the repo root "
                    f"({label} {resolved} is not under {repo_root}). "
                    "Nothing was moved."
                )
    return None


def _legacy_contents(legacy_dir: Path, names: list[str]) -> dict[str, str]:
    """Read the legacy files' bytes so the no-clobber question is answerable BEFORE the move.

    The no-clobber gate compares what is on disk in the destination against the
    projection. Run after the migration it sees the moved files and can exit 1
    — with the stale legacy bytes already promoted into `.opencode/agents/`,
    the directory OpenCode resolves, and the rest of the roster never written.
    Reading the bytes here lets that gate decide over the post-move state while
    the files are still in `.opencode/agent/`, so the refusal moves nothing.

    A symlinked legacy source is refused rather than read through: comparing
    the link TARGET's bytes would answer the gate's question about the wrong
    file, and moving the link would relocate it into the resolved directory.
    `diff()` refuses a symlinked managed leaf once it sits in the destination,
    but by then the move has happened; `_legacy_containment_error` only covers
    a link whose target escapes the repo, so an in-repo link reaches this.
    """
    symlinked = sorted(name for name in names if (legacy_dir / name).is_symlink())
    if symlinked:
        raise SpecViolation(
            "refusing to migrate: legacy agent file(s) are symlinks, and moving one would "
            "relocate the link into the directory OpenCode resolves: "
            + ", ".join(symlinked)
            + ". Nothing was moved."
        )
    return {name: (legacy_dir / name).read_text(encoding="utf-8") for name in names}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="replace changed Crux-managed agent files")
    parser.add_argument(
        "--migrate-legacy-agent-dir",
        action="store_true",
        help="move roster-named files out of the legacy .opencode/agent/ into .opencode/agents/",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        print(json.dumps({"error": f"repo root is not a directory: {repo_root}"}))
        return 2

    # OpenCode V2 reads project agents from the plural `.opencode/agents/`.
    # When both directories hold a file of the same name the plural one wins
    # silently — no merge, no warning — which is why the singular is guarded
    # below rather than tolerated beside this one.
    output_dir = repo_root / ".opencode" / "agents"
    legacy_dir = repo_root / ".opencode" / "agent"

    preflight_error = _v2_preflight_error()
    if preflight_error:
        print(json.dumps({"error": preflight_error}))
        return 2

    # Path containment (resolve-then-contain): resolve the repo root and the
    # output path up front, and refuse to write when .opencode/agents/ resolves
    # outside the resolved repo root.
    contain_error = _containment_error(repo_root, output_dir, [])
    if contain_error:
        print(json.dumps({"error": contain_error}))
        return 2

    try:
        # `generate()` first, and deliberately so: it is the lane that reports
        # a malformed or empty source roster, and running the catalog lookup
        # ahead of it would replace that diagnosis with a downstream catalog
        # read error for the same broken tree.
        generated = generate(PLUGIN_ROOT / "agents")
        roster = managed_filenames()
    except SpecViolation as exc:
        # Fail-closed: a malformed source agent, or a catalog fault surfacing
        # at first use. Structured error, never a traceback.
        print(json.dumps({"error": str(exc)}))
        return 2

    migrated: list[str] = []

    def emit(payload: dict, code: int) -> int:
        """Print a payload that always names what the migration already moved.

        Every refusal reachable AFTER the move must say so, or the user is
        told to "review" `.opencode/agent/` — a directory the same run has just
        emptied.

        Stated honestly: moving the no-clobber gate ahead of the migration
        closed the one lane a test could drive here with `migrated` non-empty.
        Two refusals are still sited after the move — the `os.replace` loop's
        OSError, which can fire on the second file after the first has moved,
        and a `write()` fault — and no fixture reaches either with a non-empty
        `migrated`, because every shape that would is caught by a check now
        running first. So this is a last-line defense rather than a measured
        path, on the same rationale as `_refuse_leaf_symlinks` in
        `opencode_agents`: a mid-loop failure, or a later edit reopening a
        post-move refusal, must still name what moved. Do not delete it as
        dead code.
        """
        if migrated:
            payload["migrated"] = migrated
        print(json.dumps(payload, indent=2))
        return code

    try:
        offenders = _legacy_offenders(legacy_dir, roster)
    except LegacyScanError as exc:
        return emit({"error": str(exc)}, 2)
    if offenders and not args.migrate_legacy_agent_dir:
        return emit({
            "error": (
                f"refusing to write: the legacy {legacy_dir} still holds crux-managed agent "
                f"files ({', '.join(offenders)}). The plural {output_dir.name}/ directory wins "
                "silently over the singular one, so leaving both would install an invisible "
                "shadow copy. Rerun with --migrate-legacy-agent-dir to move them, or delete "
                "them by hand."
            ),
            "legacy_dir": str(legacy_dir),
            "legacy_files": offenders,
        }, 1)

    # Past the refusal above, this same list is the migration PAYLOAD rather
    # than a set of offences, so it changes name for the rest of the run.
    to_migrate = offenders

    # What the pending migration would put in the destination, keyed by
    # filename. Empty on every run that migrates nothing.
    pending: dict[str, str] = {}

    if to_migrate:
        # Containment first, and it is NOT overridable by --force: --force is
        # the collision override, never a path-escape override.
        contain_error = _legacy_containment_error(repo_root, legacy_dir, output_dir, to_migrate)
        if contain_error:
            return emit({"error": contain_error}, 2)

        colliding = [name for name in to_migrate if (output_dir / name).exists()
                     or (output_dir / name).is_symlink()]
        if colliding and not args.force:
            # The refusal is over the WHOLE move: a partially migrated
            # directory is unreachable, so the non-colliding files stay put.
            return emit({
                "error": (
                    "refusing to migrate: these files already exist in "
                    f"{output_dir} — {', '.join(colliding)}. The destination copy is the one "
                    "OpenCode resolves, so overwriting it would replace the live file with the "
                    "stale shadow this guard exists to catch. Nothing was moved. Review them, "
                    "then rerun with --force to overwrite."
                ),
                "colliding": colliding,
            }, 1)

        try:
            pending = _legacy_contents(legacy_dir, to_migrate)
        except SpecViolation as exc:
            return emit({"error": str(exc)}, 2)
        except (OSError, UnicodeDecodeError) as exc:
            # An unreadable or non-UTF-8 legacy file. Decided here rather than
            # after the move, and on the exit-2 lane WITH a payload, because
            # exit-1 stdout is contractually the JSON report.
            return emit({
                "error": (
                    f"refusing to migrate: cannot read a legacy file in {legacy_dir} "
                    f"to decide whether the move would clobber a local edit ({exc}). "
                    "Nothing was moved."
                )
            }, 2)

    try:
        added, changed, removed = diff(output_dir, generated)
    except SpecViolation as exc:
        # Fail-closed: a crux-managed leaf that is a symlink (live or
        # dangling) is refused rather than read/clobbered through. Structured
        # error, never a traceback.
        return emit({"error": str(exc)}, 2)
    except (OSError, UnicodeDecodeError) as exc:
        # A roster-named DIRECTORY or a non-UTF-8 file sitting in the
        # destination: `diff()` reads every managed leaf it finds, and neither
        # shape is a symlink, so its own guard passes them through to a raw
        # read error. This lane is NOT reachable via the migration. `diff()`
        # runs ahead of the `os.replace` loop below, so nothing out of
        # `.opencode/agent/` has reached the destination when it reads. What
        # it covers is a shape already sitting in `.opencode/agents/`; the
        # migration's copy of both shapes is caught earlier, by the
        # `_legacy_contents` read above.
        return emit({
            "error": f"refusing to write: cannot read {output_dir} ({exc})"
        }, 2)

    # Decide the no-clobber question over the state the move WOULD produce, and
    # decide it before moving anything. Running the gate after the migration
    # promotes a stale legacy file into `.opencode/agents/` — the directory
    # OpenCode resolves — and then exits 1 without writing the rest of the
    # roster, leaving the tree half-installed on a refusal that was supposed to
    # change nothing. Folding the pending bytes into `changed` here keeps every
    # refusal a no-op on the filesystem.
    #
    # In the non-force lane the collision check above has already proven the
    # migrated names are absent from the destination, so `diff` and `pending`
    # describe disjoint files and this union is exactly the post-move `changed`.
    # A `pending` name the projection does not produce compares unequal to
    # `None` and so counts as changed — fail-closed, and unreachable while the
    # catalog loader checks the roster against the agent glob in both directions.
    changed = sorted(set(changed) | {
        name for name, body in pending.items() if body != generated.get(name)
    })
    # `added` is read off the pre-move destination, where a name about to be
    # migrated is still absent. Reporting it as BOTH added and changed would
    # describe a state no run ever reaches.
    added = sorted(set(added) - set(pending))

    # Re-check containment for every individual file this run would write or
    # remove, in case output_dir itself is contained but a specific existing
    # entry is a symlink escaping the repo root.
    contain_error = _containment_error(repo_root, output_dir, list(generated) + removed)
    if contain_error:
        return emit({"error": contain_error}, 2)

    if (changed or removed) and not args.force:
        return emit({
            "error": "generated Crux agents differ; review and rerun with --force",
            "added": added,
            "changed": changed,
            "removed": removed,
        }, 1)

    if to_migrate:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            for name in to_migrate:
                os.replace(legacy_dir / name, output_dir / name)
                migrated.append(name)
        except OSError as exc:
            # A non-directory sitting at `.opencode/agents`, or a destination
            # name that is a directory under --force. Exit-1 stdout is
            # contractually the JSON report, so an environment fault belongs on
            # the exit-2 lane WITH a payload — never as a traceback over empty
            # stdout. `migrated` names whatever the loop had already moved.
            return emit({"error": f"refusing to migrate: {exc}"}, 2)

    try:
        written, removed = write(output_dir, generated)
    except SpecViolation as exc:
        # Fail-closed: write() refuses to clobber a crux-managed leaf that is a
        # symlink (in-repo or escaping target). Surface it as a structured
        # error, never a traceback.
        return emit({"error": str(exc)}, 2)
    print(json.dumps({"written": written, "removed": removed, "migrated": migrated}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
