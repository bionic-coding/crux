"""A scoped memo of `yaml.safe_load` for one read phase.

One authority view parses the same few hundred ADR frontmatter blocks and run snapshots
again and again: once per clause entry, once per nested clone view. `yaml.safe_load` of a
`str` is a function of that string alone (the loader is fixed, nothing else is read), so
inside `scope()` a repeat of the same text is answered from memory.

What is stored: only a parse that returned. A text that raised is parsed again, and raises
again, on every repeat. A hit returns a deep copy, so no caller can change what a later
caller receives. Only a `str` argument is memoized; a byte string or a stream goes to the
real loader unchanged, as does any call that passes a second argument.

How it attaches. Callers reach the loader as `yaml.safe_load` on the module, so the scope
replaces that attribute for as long as at least one scope is open and puts back what it
displaced when the last scope closes. A caller that patched the attribute in between keeps
its patch: the scope restores the original only when the attribute is still its own wrapper.
"""

from __future__ import annotations

import contextlib
import copy
import threading

import yaml

_MAX_ENTRIES = 20000
_MAX_TEXT = 1 << 20

_lock = threading.Lock()
_open_scopes = 0
_displaced = None
_wrapper = None
_memo: dict = {}
stats = {"hits": 0, "misses": 0}


def _make_wrapper(real):
    def safe_load(stream, *args, **kwargs):
        if args or kwargs or type(stream) is not str or len(stream) > _MAX_TEXT:
            return real(stream, *args, **kwargs)
        with _lock:
            held = _memo.get(stream)
        if held is not None:
            stats["hits"] += 1
            return copy.deepcopy(held[0])
        stats["misses"] += 1
        value = real(stream)
        with _lock:
            if len(_memo) < _MAX_ENTRIES:
                _memo[stream] = (copy.deepcopy(value),)
        return value
    safe_load.__wrapped__ = real
    return safe_load


@contextlib.contextmanager
def scope():
    """Answer repeated `yaml.safe_load` calls on the same text from memory inside the block."""
    global _open_scopes, _displaced, _wrapper
    with _lock:
        if _open_scopes == 0:
            _displaced = yaml.safe_load
            _wrapper = _make_wrapper(_displaced)
            yaml.safe_load = _wrapper
        _open_scopes += 1
    try:
        yield
    finally:
        with _lock:
            _open_scopes -= 1
            if _open_scopes == 0:
                if yaml.safe_load is _wrapper:
                    yaml.safe_load = _displaced
                _displaced = _wrapper = None
                _memo.clear()
