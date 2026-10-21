"""Remember a validated source read for the life of one read scope.

`implementation_migration._read` and `_checked` each open a fresh descriptor-anchored
`SourceIO`, walk the path component by component, read the leaf and walk it all again.
One authority view asks for the same few hundred paths thousands of times. Inside a
`git_read_cache.scope()` this module answers a repeat from memory, and only when the
path still has the identity it had when the full read validated it.

What is stored: a read or a path check that completed. A refusal is an exception, and an
exception is never stored, so the same call refuses again on every repeat.

What a hit proves. The stamp of a path holds, for the repository root and every
component down to the leaf, the file type, device and inode; for the leaf also its size,
modification time and change time. A directory renamed, replaced or turned into a link
changes its inode or type. A leaf rewritten changes its change time, which no user-space
call can set back, and a leaf younger than two seconds also contributes its digest, as
git does for a racy file. A component that is absent contributes its absence, so a path
that did not exist stays a hit only while it still does not exist. Any difference is a
miss, and the caller runs the full validated read again.

An entry is stored only when the stamp taken before the read equals the stamp taken after
it, so an answer is never filed under an identity it was not read under.
"""

from __future__ import annotations

import hashlib
import os
import stat
import time

import git_read_cache

_SCOPE_NAME = "validated-source-reads"
RACY_NS = 2_000_000_000


def table():
    """The scope's table of remembered reads, or None outside a scope."""
    return git_read_cache.scope_memo(_SCOPE_NAME)


def stamp(root: str, rel: str):
    """The identity of `root/rel` and each directory above it, without following any link."""
    now = time.time_ns()
    try:
        info = os.lstat(root)
    except OSError as error:
        return ("error", error.errno)
    chain = [(stat.S_IFMT(info.st_mode), info.st_dev, info.st_ino)]
    parts = [p for p in rel.split("/") if p]
    path = root
    for index, part in enumerate(parts):
        path = os.path.join(path, part)
        leaf = index == len(parts) - 1
        try:
            info = os.lstat(path)
        except FileNotFoundError:
            chain.append(("absent", part))
            return tuple(chain)
        except OSError as error:
            chain.append(("error", error.errno))
            return tuple(chain)
        if not leaf:
            chain.append((stat.S_IFMT(info.st_mode), info.st_dev, info.st_ino))
            continue
        entry = (stat.S_IFMT(info.st_mode), info.st_dev, info.st_ino, info.st_size,
                 info.st_mtime_ns, info.st_ctime_ns)
        try:
            if stat.S_ISLNK(info.st_mode):
                entry += (os.readlink(path),)
            elif stat.S_ISREG(info.st_mode) and now - max(info.st_mtime_ns, info.st_ctime_ns) < RACY_NS:
                with open(path, "rb") as handle:
                    entry += (hashlib.sha256(handle.read()).hexdigest(),)
        except OSError as error:
            entry += ("error", error.errno)
        chain.append(entry)
    return tuple(chain)


def recall(kind: str, root: str, rel: str, extra=None):
    """``(stamp, value)`` of a remembered answer whose path is still unchanged, or None.

    The stamp is the identity the path has now, which equals the one it was stored under."""
    memo = table()
    if memo is None:
        return None
    key = (kind, root, rel, extra)
    held = memo.get(key)
    if held is None:
        return None
    current = stamp(root, rel)
    if current != held[0]:
        del memo[key]
        return None
    return current, held[1]


def remember(kind: str, root: str, rel: str, extra, before, value) -> None:
    """Store `value` under the stamp `before` when the path still has that identity."""
    memo = table()
    if memo is None or before is None or stamp(root, rel) != before:
        return
    memo[(kind, root, rel, extra)] = (before, value)
