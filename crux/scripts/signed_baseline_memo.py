"""Remember the signed-dependency baseline of one publication commit.

`implementation_migration._published_signed_inputs` reads the signed baseline from a
fresh clone of the repository checked out at the publication commit. The baseline is a
function of that commit's tree alone: the clone runs with every ambient git setting
removed, and a commit object id names one tree for as long as the object exists, in any
repository. So the baseline of a commit that was read once is the baseline every later
read of that commit produces.

What is stored: a baseline that was read successfully, under the full commit id the
caller resolved, and nothing else. A refusal is an exception and is never stored, so the
same commit refuses again whenever the clone or the baseline read refuses. A caller
resolves and checks the revision on every call before it asks this memo, so the
shallow-history and unknown-revision refusals do not depend on it. The memo keeps at
most `_LIMIT` commits for the life of the process, and returns a copy to each caller.
"""

from __future__ import annotations

import copy
import re
import threading
from collections import OrderedDict

_LIMIT = 64
_COMMIT = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_lock = threading.Lock()
_BASELINES: OrderedDict = OrderedDict()


def recall(commit: str):
    """A copy of the baseline read for `commit`, or None when none was stored."""
    if not isinstance(commit, str) or not _COMMIT.match(commit):
        return None
    with _lock:
        found = _BASELINES.get(commit)
        if found is None:
            return None
        _BASELINES.move_to_end(commit)
        return copy.deepcopy(found)


def remember(commit: str, baseline) -> None:
    """Store a baseline that was read successfully under the full commit id `commit`."""
    if not isinstance(commit, str) or not _COMMIT.match(commit):
        return
    with _lock:
        _BASELINES[commit] = copy.deepcopy(baseline)
        _BASELINES.move_to_end(commit)
        while len(_BASELINES) > _LIMIT:
            _BASELINES.popitem(last=False)


def forget() -> None:
    """Drop every stored baseline."""
    with _lock:
        _BASELINES.clear()
