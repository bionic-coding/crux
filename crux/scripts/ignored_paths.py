"""The one predicate that decides whether documentation-tree paths are ignored by git.

Every writer and gate that relaxes its behaviour for an ignored tree calls `ignored`, and no
other code added for that purpose calls `git check-ignore`.

`ignored` runs `git -C <repo> check-ignore -z --stdin` once, under the ambient environment
(`os.environ`), so every ignore source the user's own git reads counts: `.gitignore`,
`.git/info/exclude`, and a `core.excludesFile` set in the global or system configuration. It
removes `GIT_LITERAL_PATHSPECS`, because `check-ignore` exits 128 under literal pathspecs, and it
removes every name in `drop_env`. Council callers pass the gateway-key and crux env-file names
and the git redirect names their own git environment drops, so no git child inherits the key and
the query reads the same repository as the council's own `git add`.

Git never reports a tracked path, even inside an ignored directory, so a tracked file keeps the
caller's strict handling. A directory that holds any tracked file is not reported; callers ask
about each file, never about the documentation root alone.

The ambient answer is meant as a superset of what each caller's `git add` refuses. One known
exception: when a global `core.excludesFile` points elsewhere, the council's isolated git (global
and system configuration set to /dev/null) can still read the default
`$XDG_CONFIG_HOME/git/ignore`, which the user's own git then skips. The predicate reports such a
path tracked, and the council's `git add` refuses it with today's error. That case fails closed.

A query the predicate cannot answer relaxes nothing: any exit other than 0 or 1, a missing git
or an OSError returns the empty set, so the caller keeps its strict behaviour. Two cases land
there by design. A documentation root reached through a symlink makes `check-ignore` refuse the
path, as `git add` does. One fatal path in the single batch empties the whole answer.

Standard library only.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable


def ignored(repo: Path | str, rels: Iterable[str], *, drop_env: Iterable[str] = ()) -> frozenset[str]:
    """Return the subset of the repository-relative paths `rels` that git ignores in `repo`."""
    paths = [str(rel) for rel in rels]
    if not paths or any('\0' in path for path in paths):
        return frozenset()
    dropped = {'GIT_LITERAL_PATHSPECS', *drop_env}
    env = {key: value for key, value in os.environ.items() if key not in dropped}
    payload = b''.join(os.fsencode(path) + b'\0' for path in paths)
    try:
        result = subprocess.run(['git', '-C', str(repo), 'check-ignore', '-z', '--stdin'],
                                input=payload, capture_output=True, env=env)
    except OSError:
        return frozenset()
    if result.returncode not in (0, 1):
        return frozenset()
    reported = {os.fsdecode(item) for item in result.stdout.split(b'\0') if item}
    return frozenset(path for path in paths if path in reported)
