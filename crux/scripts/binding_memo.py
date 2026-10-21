"""Remember one proved historical migration binding for the life of a git-read scope.

`implementation_approval.validate_historical_migration_binding` re-proves a past close
from the complete shared history. One migration apply asks for the same proof dozens of
times, each time over unchanged inputs. Inside a `git_read_cache.scope()` this module
answers a repeat from memory, and only under these conditions:

* Only a successful proof is stored. A refusal is an exception, and an exception is never
  stored, so the same call refuses again on every repeat.
* The proof is read over the repository's git state and over working-tree files. The key
  holds the bytes `git_read_cache._repository_state` covers (index, HEAD, the ref HEAD
  names, packed refs, config, shallow), the process environment, the real path of the
  repository and of the run, the slot, the batch path and its digest, and the identity of
  the proof function that ran, so a replaced function is a different key.
* A hit also re-checks a fingerprint of every working-tree input the proof read. The
  first run records them: each file opened and each directory listed under the
  repository (Python audit events), every ancestor directory of those, the ignore files
  along them, the whole run directory, both promptbook tiers the run could belong to and
  the pending council copies in the git directory. A file's fingerprint is its type,
  inode, size and modification time, plus its digest while it is younger than two
  seconds. Any difference is a miss, and the proof runs again.
* A proof is not stored when it started any child process other than git (the issued
  profile-two worker replays in a separate process this module cannot observe), when the
  git state cannot be read exactly, when the state moved while the proof ran, or when an
  input was modified shortly before the proof started.

The memo lives in the scope's memo and ends with the outermost `with` block.
"""

from __future__ import annotations

import contextvars
import copy
import hashlib
import os
import sys
import time
from pathlib import Path

import council_records as cr
import git_read_cache
import implementation_approval as ap
from path_signature import signature as _signature

_SCOPE_NAME = "historical-migration-binding"
_RECORDER: contextvars.ContextVar = contextvars.ContextVar("crux_binding_reads", default=None)
_QUIET_NS = 50_000_000
_hook_installed = False


class _Reads:
    """What one proof opened, listed and spawned."""

    def __init__(self, *roots: str):
        self.roots = tuple(dict.fromkeys(roots))
        self.paths: set[str] = set()
        self.foreign_process = False


def _audit(event, args):
    reads = _RECORDER.get()
    if reads is None:
        return
    try:
        if event in ("open", "os.listdir", "os.scandir"):
            target = args[0]
            if isinstance(target, int) or target is None:
                return
            path = os.path.abspath(os.fsdecode(target))
            if any(path == root or path.startswith(root + os.sep) for root in reads.roots):
                reads.paths.add(path)
        elif event == "subprocess.Popen":
            program = args[0]
            if os.path.basename(os.fsdecode(program)) != "git":
                reads.foreign_process = True
        elif event == "os.posix_spawn":
            # `git_read_cache` starts git through `posix_spawn`; any other program is foreign.
            if os.path.basename(os.fsdecode(args[0])) != "git":
                reads.foreign_process = True
        elif event in ("os.exec", "os.spawn", "os.system", "os.fork", "os.forkpty"):
            reads.foreign_process = True
    except (TypeError, ValueError, OSError):
        reads.foreign_process = True


def _install_hook() -> None:
    global _hook_installed
    if not _hook_installed:
        sys.addaudithook(_audit)
        _hook_installed = True


def _tree(root: str):
    """Every directory and file below `root`, links not followed."""
    found = []
    stack = [root]
    while stack:
        current = stack.pop()
        found.append(current)
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    else:
                        found.append(entry.path)
        except OSError:
            continue
    return found


def _fingerprint(explicit, trees, now_ns: int):
    paths = set(explicit)
    for root in trees:
        paths.update(_tree(root))
    return tuple((path, _signature(path, now_ns)) for path in sorted(paths))


def _normal(path: str) -> str:
    """The path with its directory resolved and its last component left as spelled."""
    return os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path))


def _covered(repo: str, git_dir: str, reads: set[str], extra: set[str], book_candidates):
    """The explicit paths the fingerprint covers, from what the proof read."""
    # The git directory's state files are the key's bytes; its pending copies are a tree root.
    explicit = {_normal(path) for path in set(reads)}
    explicit = {path for path in explicit if path.startswith(repo + os.sep)
                and not (path == git_dir or path.startswith(git_dir + os.sep))}
    explicit |= {_normal(path) for path in set(extra) | set(book_candidates)}
    for path in list(explicit):
        parent = os.path.dirname(path)
        while len(parent) > len(repo) and parent != git_dir:
            explicit.add(parent)
            if not (parent == git_dir or parent.startswith(git_dir + os.sep)):
                explicit.add(os.path.join(parent, ".gitignore"))
            parent = os.path.dirname(parent)
    explicit.add(os.path.join(repo, ".gitignore"))
    explicit.add(os.path.join(git_dir, "info", "exclude"))
    return explicit


def _environment() -> str:
    return hashlib.sha256(repr(sorted(os.environ.items())).encode("utf-8", "surrogateescape")).hexdigest()


def _inputs(proof, repo: str, run: str):
    """Roots and candidates beyond the recorded reads: the run directory, both book tiers, pending copies."""
    git_dir = os.path.join(repo, ".git")
    run_dir = os.path.dirname(run)
    books = os.path.dirname(os.path.dirname(run_dir))
    candidates = {os.path.join(books, tier, os.path.basename(run_dir) + ".yaml") for tier in ("active", "archive")}
    candidates |= {os.path.dirname(path) for path in candidates}
    trees = {run_dir}
    binding = proof.binding
    try:
        pending = os.path.join(git_dir, *cr.PENDING_SUBDIR, str(binding["book_id"]), str(binding["run_id"]))
    except (KeyError, TypeError):
        return git_dir, None, None
    trees.add(pending)
    return git_dir, candidates, trees


def validate_historical_migration_binding(repo_root, run_path, *, slot, batch_path, batch_sha256):
    """`implementation_approval.validate_historical_migration_binding`, answered from the scope's
    memory when every input it proved over is unchanged. Outside a scope it is that function."""
    prove = ap.validate_historical_migration_binding
    memo = git_read_cache.scope_memo(_SCOPE_NAME)
    if memo is None:
        return prove(repo_root, run_path, slot=slot, batch_path=batch_path, batch_sha256=batch_sha256)
    repo = os.path.realpath(os.fspath(repo_root))
    state = git_read_cache._repository_state(repo)
    if state is None:
        return prove(repo_root, run_path, slot=slot, batch_path=batch_path, batch_sha256=batch_sha256)
    key = (repo, state, _environment(), os.path.realpath(os.fspath(run_path)), slot, batch_path,
           batch_sha256, id(prove))
    entry = memo.get(key)
    if entry is not None:
        # The key holds an identity; the entry keeps its object alive, so only that object matches.
        if entry["prove"] is prove and _fingerprint(entry["explicit"], entry["trees"], time.time_ns()) == entry["fingerprint"]:
            return copy.deepcopy(entry["proof"])
        del memo[key]
    started = time.time_ns()
    reads = _Reads(repo, os.path.abspath(os.fspath(repo_root)))
    _install_hook()
    token = _RECORDER.set(reads)
    try:
        proof = prove(repo_root, run_path, slot=slot, batch_path=batch_path, batch_sha256=batch_sha256)
    finally:
        _RECORDER.reset(token)
    if reads.foreign_process or git_read_cache._repository_state(repo) != state:
        return proof
    run = os.path.realpath(os.fspath(run_path))
    git_dir, candidates, trees = _inputs(proof, repo, run)
    if candidates is None:
        return proof
    explicit = _covered(repo, git_dir, reads.paths, {run}, candidates)
    now = time.time_ns()
    fingerprint = _fingerprint(explicit, trees, now)
    newest = max((sig[3] for _, sig in fingerprint if isinstance(sig, tuple) and len(sig) > 3
                  and isinstance(sig[3], int)), default=0)
    if newest >= started - _QUIET_NS or git_read_cache._repository_state(repo) != state:
        return proof
    memo[key] = {"prove": prove, "proof": copy.deepcopy(proof), "explicit": frozenset(explicit),
                 "trees": frozenset(trees), "fingerprint": fingerprint}
    return proof
