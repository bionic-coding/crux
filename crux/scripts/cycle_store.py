"""Shared record primitives: errors, time, canonical bytes, contained paths, atomic writes, the cycle lock,
the exact-path commit and the bounded no-follow reader.

Retained consumers import these instead of the typed cycle engine. Each body moved unchanged from
`cycle_workflow.py`, `cycle_commit.py` or `cycle_context_read.py`, so `encoded()` and `digest()` keep
their bytes and every recorded digest recomputes equal. This module holds no state machine, record
loader, phase table or event writer.

`commit_paths` commits exact paths with `git commit --only` and defers, without failing, while a
merge or rebase runs, the index is locked or a full suite holds `<git-common-dir>/crux/full-suite.lock`.
It reports

    {"changed": bool, "commit": SHA|None, "paths": [...], "message": str|None, "deferred": REASON|None}

`paths` names only the files the commit changed, read from the commit itself. With no commit it names
the files that wait to be committed, and it is empty when nothing waits. `deferred` names why no commit
was made: ``not-a-git-repository``, ``operation-in-progress`` (merge, rebase, cherry-pick or revert),
``index-locked``, ``full-suite-running`` or ``commit-failed``. A deferral is not a failure: the files
stay on disk for a later commit. A path git ignores is never staged or committed: `commit_paths` drops
every path `ignored_paths.ignored` reports, and its result then carries ``commit_skipped: "tree-ignored"``
and ``skipped_paths``.

`bounded_bytes` reads one regular file under a size bound, opening every path component relative to a
no-follow directory descriptor; `scan` runs the secret scanner inside the reader's refusal contract.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

from bionic_config import load_config, require_schema_version

# A cycle identity, with an optional artifact prefix.
ID = re.compile(r'^(?:[A-Z][A-Z0-9]{1,9}-)?CYC-[0-9]{4,}$')
# The terminal record statuses.
CLOSED = {'completed', 'abandoned', 'shortcut'}

SUITE_LOCK = ('crux', 'full-suite.lock')
IN_PROGRESS = (('MERGE_HEAD', 'merge'), ('CHERRY_PICK_HEAD', 'cherry-pick'), ('REVERT_HEAD', 'revert'),
               ('rebase-merge', 'rebase'), ('rebase-apply', 'rebase'))


class CycleError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def contained(root: Path, relative: str | Path) -> Path:
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise CycleError('path must be relative and contain no parent segments')
    target = root / path
    if not target.resolve().is_relative_to(root.resolve()):
        raise CycleError('path escapes its owning tree')
    # No symlink writes or retained subjects, including symlinks pointing inward.
    if any(parent.is_symlink() for parent in (target, *target.parents) if parent != root.parent):
        raise CycleError('symlink paths are refused')
    return target


def atomic(path: Path, value):
    atomic_bytes(path, encoded(value))


def atomic_bytes(path: Path, data: bytes):
    """Write through a temp file, fsync, then os.replace, so a reader sees a whole file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.cycle-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def tree(repo):
    cfg = load_config(repo, require_tree=True)
    require_schema_version(cfg.docs_root)
    return cfg


class LinkedWorktree(CycleError):
    """A mutating command ran in a linked worktree; `main` is the main checkout's project root."""
    def __init__(self, main):
        super().__init__(f'linked-worktree: cycle records are written only from the main checkout; rerun with --repo-root {main}')
        self.main = main


def main_checkout(repo):
    """The main checkout's project root when `repo` lies in a linked worktree; None otherwise.

    The main checkout is the parent of the common git directory; the project root keeps its
    offset below the worktree's top level. None outside git, or when git cannot answer."""
    repo = Path(repo).resolve()
    try:
        done = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--path-format=absolute', '--git-dir', '--git-common-dir', '--show-toplevel'],
                              capture_output=True, text=True)
    except OSError:
        return None
    lines = done.stdout.split('\n')
    if done.returncode or len(lines) < 3 or not all(lines[:3]):
        return None
    git_dir, common, top = (Path(line).resolve() for line in lines[:3])
    if git_dir == common or common.name != '.git':
        return None
    return common.parent / repo.relative_to(top)


def require_main_checkout(repo):
    """The shared guard every mutating command calls: refuse a linked worktree, naming the main checkout."""
    main = main_checkout(repo)
    if main is not None:
        raise LinkedWorktree(main)


@contextmanager
def locked(repo):
    require_main_checkout(repo)
    cfg = tree(repo)
    directory = contained(cfg.docs_root, 'cycles')
    directory.mkdir(exist_ok=True)
    lock = contained(directory, '.lock')
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield cfg, directory


def run_git(cfg, *argv):
    done = subprocess.run(['git', '-C', str(cfg.repo_root), *argv], capture_output=True, text=True)
    return done.returncode, done.stdout


def git(root, *argv):
    done = subprocess.run(['git', '--no-optional-locks', '--literal-pathspecs', '-C', str(root), *argv], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def pending_files(cfg, paths):
    """Changed or untracked files under `paths`, or None when this is not a git work tree."""
    code, out, _ = git(cfg.repo_root, 'status', '--porcelain', '--untracked-files=all', '--', *paths)
    if code != 0:
        return None
    return [line[3:] for line in out.splitlines() if line]


def suite_lock_state(cfg):
    """Read flock ownership and its diagnostic holder; a stale record is not a live process."""
    code,out,_=git(cfg.repo_root,'rev-parse','--path-format=absolute','--git-common-dir')
    if code!=0:return {'flock':'unavailable','holder':None,'path':None}
    path=Path(out.strip()).joinpath(*SUITE_LOCK)
    try:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    except FileNotFoundError:return {'flock':'not-held','holder':None,'path':str(path)}
    except OSError:return {'flock':'unavailable','holder':None,'path':str(path)}
    try:
        try:fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB);state='not-held'
        except OSError:state='held'
        raw=os.pread(fd,4096,0).decode(errors='replace').strip()
        try:holder=json.loads(raw) if raw else None
        except ValueError:holder={'unparsed':raw}
        return {'flock':state,'holder':holder,'path':str(path)}
    finally:os.close(fd)


def suite_running(cfg):
    """True while a full suite holds `<git-common-dir>/crux/full-suite.lock`. Probes with a shared, non-blocking lock."""
    code, out, _ = git(cfg.repo_root, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if code != 0:
        return False
    lock = Path(out.strip()).joinpath(*SUITE_LOCK)
    try:
        fd = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except OSError:
        return True
    finally:
        os.close(fd)
    return False


def deferral(cfg):
    """(reason, detail) when a commit must wait, else None."""
    code, out, _ = git(cfg.repo_root, 'rev-parse', '--absolute-git-dir')
    if code != 0:
        return 'not-a-git-repository', 'git cannot find a work tree here'
    git_dir = Path(out.strip())
    for name, kind in IN_PROGRESS:
        if (git_dir / name).exists():
            return 'operation-in-progress', f'a {kind} is in progress'
    if (git_dir / 'index.lock').exists():
        return 'index-locked', 'another git process holds the index lock'
    if suite_running(cfg):
        return 'full-suite-running', 'a full suite holds the full-suite lock'
    return None


def commit_paths(cfg, paths, message):
    """Commit `paths` alone with `git commit --only`, under the record commit's deferral conditions.

    `message` is a string or a callable that returns one; it is called only when there is something to commit.
    Returns the result described in the module docstring. The caller holds whatever lock guards `paths`.
    Paths `ignored_paths.ignored` reports are dropped and named in `skipped_paths`."""
    from ignored_paths import ignored
    skipped = ignored(cfg.repo_root, paths)
    extra = {}
    if skipped:
        extra = {'commit_skipped': 'tree-ignored', 'skipped_paths': [path for path in paths if path in skipped]}
        paths = [path for path in paths if path not in skipped]
    base = {'changed': False, 'commit': None, 'paths': paths, 'message': None, 'deferred': None, **extra}
    if skipped and not paths:
        return base
    files = pending_files(cfg, paths)
    if files is None:
        return {**base, 'deferred': 'not-a-git-repository', 'detail': 'git cannot find a work tree here'}
    if not files:
        return {**base, 'paths': []}
    found = deferral(cfg)
    if found:
        return {**base, 'paths': files, 'deferred': found[0], 'detail': found[1], 'pending': files}
    text = message() if callable(message) else message
    code, _, err = git(cfg.repo_root, 'add', '--', *paths)
    if code == 0:
        code, _, err = git(cfg.repo_root, 'commit', '--only', '--no-verify', '-m', text, '--', *paths)
    if code != 0:
        return {**base, 'paths': files, 'deferred': 'commit-failed', 'detail': err.strip()[:300], 'pending': files}
    _, head, _ = git(cfg.repo_root, 'rev-parse', 'HEAD')
    return {**base, 'paths': committed_paths(cfg), 'changed': True, 'commit': head.strip(), 'message': text}


def committed_paths(cfg):
    """The paths the HEAD commit changed, which is what a commit result reports in `paths`."""
    code, out, _ = git(cfg.repo_root, 'diff-tree', '--root', '--no-commit-id', '--name-only', '-r', '-z', 'HEAD')
    return [path for path in out.split('\0') if path] if code == 0 else []


# The bounded reader, moved unchanged from cycle_context_read: a council call checkpoint is read and
# written under the same 1 MiB bound and secret scan as before.
MAX_OBJECT_BYTES = 1024 * 1024


class ReadRefused(Exception):
    def __init__(self, code, **metadata):
        self.code = code
        self.metadata = metadata


def scan(text):
    """Keep scanner infrastructure failures inside the bounded reader's refusal contract."""
    from secret_scan import scan_text
    try:
        return scan_text(text)
    except Exception:
        raise ReadRefused('scanner-unavailable') from None


@dataclass(frozen=True)
class Reference:
    path: Path
    root: Path
    sha256: str | None = None


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def bounded_bytes(ref: Reference, *, limit: int = MAX_OBJECT_BYTES) -> bytes:
    """Open every component relative to a no-follow directory descriptor.

    Compare descriptor and path identities before/after reading. Nonblocking open
    and fstat refuse a raced special file without waiting on its writer. `limit`
    defaults to the context bound; identity-only callers may pass a larger one.
    """
    path, root = ref.path, ref.root
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(root):
        raise ReadRefused('unsafe-path')
    if (not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK'))
            or os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd
            or os.stat not in os.supports_follow_symlinks):
        raise ReadRefused('read-capability-unavailable')
    descriptors = []
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        # Roots themselves may contain links, so start at the filesystem root.
        directory = os.open(path.anchor, directory_flags)
        descriptors.append(directory)
        parts = path.parts[1:]
        for part in parts[:-1]:
            directory = os.open(part, directory_flags, dir_fd=directory)
            descriptors.append(directory)
        before_path = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        if stat.S_ISLNK(before_path.st_mode):
            raise ReadRefused('unsafe-path')
        if not stat.S_ISREG(before_path.st_mode):
            raise ReadRefused('not-regular')
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or _identity(before) != _identity(before_path):
            raise ReadRefused('object-changed')
        if before.st_size > limit:
            raise ReadRefused('object-too-large', size_bytes=before.st_size, sha256=None)
        chunks = []
        size = 0
        while size <= limit:
            data = os.read(descriptor, min(65536, limit + 1 - size))
            if not data:
                break
            chunks.append(data)
            size += len(data)
        after = os.fstat(descriptor)
        after_path = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        # Compare the opened leaf with its directory entry after the read.
        if (_identity(before) != _identity(after) or _identity(before) != _identity(after_path)
                or size != before.st_size):
            raise ReadRefused('object-changed')
        if size > limit:
            raise ReadRefused('object-too-large', size_bytes=size, sha256=None)
        # All components remain the directories we opened, even if renamed.
        current = Path(path.anchor)
        for info_fd, part in zip(descriptors[1:-1], parts[:-1]):
            current = current / part
            info = os.stat(current, follow_symlinks=False)
            held = os.fstat(info_fd)
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != (held.st_dev, held.st_ino):
                raise ReadRefused('object-changed')
        return b''.join(chunks)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            raise ReadRefused('object-missing') from None
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ReadRefused('unsafe-path') from None
        raise ReadRefused('object-unreadable') from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
