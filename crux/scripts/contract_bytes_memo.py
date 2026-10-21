"""Remember the policy contract bytes of one profile for the life of the process.

`implementation_approval.gate_contract_bytes` walks the profile's policy modules and
serialises the source and live constants they own. It takes a quarter of a second, and a
single proof asks for it again each time. Its output is a function of what this module's
key holds, and nothing else:

* each policy module object, by identity, with the identity of every global it holds, so
  a patched constant or a replaced module object is a different key;
* each module's source file, by `path_signature.signature`, so an edited file is a
  different key even when the loaded module object is not;
* the reader functions the walk calls (`Path.read_bytes`, `inspect.getsource` and the like),
  so a replaced reader is a different key;
* every file a global names with a `Path`, by the same signature. The walk reads those
  files, for example the schemas it hashes.

The bytes are stored only after the walk returned them, so a refusal is an exception and
is never stored. The key is computed again after the walk, and bytes are stored only when
it did not move. A key that cannot be computed disables the memo for that call.
"""

from __future__ import annotations

import ast
import inspect
import json
import threading
import time
from collections import OrderedDict
from pathlib import Path

import council_records
from path_signature import signature

_LIMIT = 16
_lock = threading.Lock()
_MEMO: OrderedDict = OrderedDict()


class _Key(tuple):
    """A key that keeps alive every object whose identity it holds.

    An identity is unique only while its object lives. A key held by the memo would
    otherwise match a different object later allocated at the same address."""
    refs: tuple = ()


def _named_paths(value, found: set, depth: int = 0) -> None:
    if isinstance(value, Path):
        found.add(str(value))
    elif depth < 4 and isinstance(value, (list, tuple, set, frozenset)):
        for item in list(value):
            _named_paths(item, found, depth + 1)
    elif depth < 4 and isinstance(value, dict):
        for item in list(value.values()):
            _named_paths(item, found, depth + 1)


def _primitives() -> tuple:
    """The reader functions the walk calls outside the policy modules."""
    return (Path.read_bytes, Path.read_text, Path.is_file, Path.relative_to, inspect.getsource,
            inspect.isfunction, ast.parse, json.dumps, council_records.sha256_bytes)


def key(version: str, modules) -> tuple | None:
    """The memo key for `version` over its policy `modules`, or None when it cannot be computed."""
    try:
        now = time.time_ns()
        primitives = _primitives()
        refs: list = [primitives, tuple(modules)]
        parts = [version, tuple(id(function) for function in primitives)]
        paths: set[str] = set()
        for module in modules:
            if module is None:
                parts.append(None)
                continue
            names = list(vars(module).items())
            refs.append([value for _, value in names])
            for _, value in names:
                _named_paths(value, paths)
            file = getattr(module, "__file__", None)
            parts.append((id(module), getattr(module, "__name__", None), file,
                          signature(file, now) if file else None,
                          tuple((name, id(value)) for name, value in names)))
        parts.append(tuple((path, signature(path, now)) for path in sorted(paths)))
        found = _Key(parts)
        found.refs = tuple(refs)
        return found
    except Exception:  # noqa: BLE001 - an unreadable key only turns the memo off
        return None


def recall(memo_key):
    """The bytes stored under `memo_key`, or None."""
    if memo_key is None:
        return None
    with _lock:
        found = _MEMO.get(memo_key)
        if found is not None:
            _MEMO.move_to_end(memo_key)
        return found


def remember(memo_key, content: bytes) -> None:
    """Store bytes the walk returned under the key computed before it."""
    if memo_key is None or not isinstance(content, bytes):
        return
    with _lock:
        _MEMO[memo_key] = content
        _MEMO.move_to_end(memo_key)
        while len(_MEMO) > _LIMIT:
            _MEMO.popitem(last=False)


def forget() -> None:
    """Drop every stored contract."""
    with _lock:
        _MEMO.clear()
