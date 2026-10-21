"""A committed copy of this checkout that carries none of its live bookkeeping.

WHY THIS EXISTS. The checkout suites declare every tracked file as an input except the cycle records,
the bookkeeping documents under the docs directory (`suite_evidence.DOCS_EXCLUSIONS`) and the files
`.bionic.yml` names as bookkeeping (`suite_evidence.bookkeeping_paths`): the journal, the operations
log, the inbox, the garden notes, the next-steps record, the cycle queue and the root notes. They
change with every logged operation, and a suite whose receipt they invalidate runs again for nothing.
This module takes both lists from `suite_evidence`, the one producer, and keeps `cycles` in the copy.

A test that runs a gate over the live checkout, such as the citation linter, the doctrine
consistency gate or a skill self-test, reads two of those documents without meaning to. The
historical-authority view corroborates each signed backfill batch against its `backfill` log
operation and its `review` journal hook, and each published survey batch against its
`observation` log operation and its `review` journal hook. Unrelated appends never change that
corroboration, so `seed_corroboration` carries the corroborating entries as a frozen fixture. The rest of
the copy is the live working tree, uncommitted edits included, so the gate still judges this
checkout's decisions, prose and projections.

The copy is a `--shared --no-checkout` clone of this repository with the working tree copied on
top and committed. A tree that has published an implementation migration proves it from Git
history, so a fresh `git init` would refuse where this clone does not. A tree with no `.git`
(the staged artifact) carries no documentation tree to publish from and gets a fresh repository.

ACCEPTED COVERAGE LOSS (CYC-0036, OBJ-2). The copy omits `bionic/queue`, so the suite tests that lint
the copy (the governs-reference lint, the doctrine gate, the skill self-tests) no longer see
`bionic/queue/cycles.yaml`, and a broken `rule:` citation in a queue item is not reported by the
suites. The CI governs-reference step and the on-demand check-drift guard still lint the live queue.

Used by the tests that read the live authority view. `test_derive_arch.py` calls `bookkeeping_filter` for its
own write-path tests.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import _council_gate_support as support

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import suite_evidence  # noqa: E402

# The live bookkeeping documents under the docs directory: the shared list, less the cycle records,
# which stay in the copy because a published migration proof may read a historical cycle record.
# `queue` is omitted too: the copy's lint no longer sees bionic/queue/cycles.yaml (accepted loss, OBJ-2).
BOOKKEEPING = frozenset(suite_evidence.DOCS_EXCLUSIONS) - {"cycles"}
CORROBORATION_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "live_docs" / "corroboration"

# What a scratch copy leaves behind: caches and venvs that cost time and no derive reads, and the
# two scratch directories other runners create and remove at the repository root.
_IGNORED_NAMES = shutil.ignore_patterns(
    ".git", "__pycache__", "*.pyc", "node_modules", ".venv", ".cache", "logs",
    ".pytest_cache", ".ruff_cache", ".crux-arch-scratch", ".crux-selftest-scratch",
)


def bookkeeping_filter(repo: Path):
    """A function `(directory, names) -> set` of the names a bookkeeping-free copy of `repo` omits.

    The docs-directory bookkeeping names, and each file `suite_evidence.bookkeeping_paths` returns,
    matched by repository-relative path. The configured files are read once, not per directory.
    """
    repo = repo.resolve()
    targets = [repo / entry for entry in suite_evidence.bookkeeping_paths(repo)]

    def omit(directory: str, names: list[str]) -> set[str]:
        here = Path(directory).resolve()
        found = set(BOOKKEEPING.intersection(names)) if here == repo / "bionic" else set()
        found.update(t.name for t in targets if t.parent == here and t.name in names)
        return found

    return omit


def omitted(repo: Path, directory: str, names: list[str]) -> set[str]:
    """`bookkeeping_filter(repo)(directory, names)`, for one-off callers."""
    return bookkeeping_filter(repo)(directory, names)


def _ignore_for(repo: Path):
    harness = (repo / ".claude").resolve()
    omit = bookkeeping_filter(repo)

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = set(_IGNORED_NAMES(directory, names))
        here = Path(directory).resolve()
        ignored.update(omit(directory, names))
        if here == harness:
            # Other checkouts are isolation state. Keep similarly named project fixtures.
            ignored.update({"worktrees"}.intersection(names))
        return ignored

    return ignore


def seed_corroboration(repo: Path, scratch: Path) -> None:
    """Give a bookkeeping-free copy the log and journal entries the authority view corroborates.

    A tree with no operations log (the staged artifact) has nothing to corroborate and gets nothing.
    """
    docs = scratch / "bionic"
    if not (repo / "bionic" / "log.md").is_file() or not docs.is_dir():
        return
    (docs / "journal").mkdir(exist_ok=True)
    shutil.copyfile(CORROBORATION_FIXTURE / "log.md", docs / "log.md")
    shutil.copyfile(CORROBORATION_FIXTURE / "journal" / "2026-08.md", docs / "journal" / "2026-08.md")


def committed_copy(repo: Path, scratch: Path) -> Path:
    """Copy `repo` to `scratch` without its live bookkeeping, and commit the copy."""
    ignore = _ignore_for(repo)
    if (repo / ".git").exists():
        scratch.parent.mkdir(parents=True, exist_ok=True)
        support.git(scratch.parent, "clone", "-q", "--shared", "--no-checkout", str(repo), str(scratch))
        shutil.copytree(repo, scratch, ignore=ignore, symlinks=True, dirs_exist_ok=True)
    else:
        shutil.copytree(repo, scratch, ignore=ignore, symlinks=True)
        support.init_repo(scratch)
    seed_corroboration(repo, scratch)
    support.git(scratch, "config", "gc.auto", "0")
    support.git(scratch, "config", "maintenance.auto", "false")
    support.git(scratch, "add", "-A")
    # A clean live tree can equal HEAD's tree; the baseline commit still lands.
    support.git(scratch, "commit", "-q", "--allow-empty", "-m", "synthetic copied source baseline")
    return scratch
