"""A path's identity without following a link, for memos that must notice a change.

The signature holds the file type, inode, size and modification time, and the link
target of a symlink. A regular file younger than two seconds also contributes its
digest, because a rewrite of the same size inside one timestamp tick moves none of the
other fields (the racy-file case git itself guards with a content comparison).
"""

from __future__ import annotations

import hashlib
import os
import stat

RACY_NS = 2_000_000_000


def signature(path: str, now_ns: int):
    """The identity of one path, or None when it is absent. `now_ns` dates the racy window."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as error:
        return ("error", error.errno)
    base = (stat.S_IFMT(info.st_mode), info.st_ino, info.st_size, info.st_mtime_ns)
    try:
        if stat.S_ISLNK(info.st_mode):
            return base + (os.readlink(path),)
        if stat.S_ISREG(info.st_mode) and now_ns - info.st_mtime_ns < RACY_NS:
            with open(path, "rb") as handle:
                return base + (hashlib.sha256(handle.read()).hexdigest(),)
    except OSError as error:
        return base + ("error", error.errno)
    return base
