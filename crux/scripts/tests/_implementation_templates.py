"""Prepared fixtures built once per worker process and cloned for each test.

This module is a helper, not a test module: unittest discovery matches `test*.py` only.

A migration fixture is a real Git repository that took real writer subprocesses to build
(advance-run closes, apply, commits). Building one per test, or per class, repeats the same
deterministic work. A *template* is the built fixture kept on disk for the life of the worker.
Each test receives a *clone*: a copy of the repository tree, including its Git history, and a
copy of the Python state that describes it, with every path under the template root moved to
the clone's root.

Rules that keep a clone as strong as a rebuild:

* A template is never handed to a test. Only clones are, so one test's writes cannot reach
  another.
* A clone shares no Python object with the template: the state is deep-copied.
* A clone fails closed when its state embeds the template's absolute path in text. Such a
  path would silently point a clone at the template's repository.
* A template is built by the same code a test used to run, so a failure to build raises in
  every test that needs it.
* The key names every input of the build: a different construction needs a different key.
"""
from __future__ import annotations

import atexit
import copy
import dataclasses
import os
import shutil
import functools
import tempfile
import types
from pathlib import Path

_TEMPLATES: dict = {}


def ambient() -> tuple:
    """The inherited environment and working directory a template build depends on."""
    return (tuple(sorted(os.environ.items())), os.getcwd())


def _children(value):
    if isinstance(value, dict):
        yield from value.keys()
        yield from value.values()
    elif isinstance(value, (list, tuple, set, frozenset)):
        yield from value
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            yield getattr(value, field.name, None)
    elif hasattr(value, "__dict__") and not isinstance(value, (type, Path)):
        yield from vars(value).values()


_CAPTURING = (types.FunctionType, types.MethodType, types.BuiltinFunctionType, functools.partial)


def _paths_under(value, root: Path) -> dict:
    """Every Path object in `value` under `root`, by identity.

    Refuses a state that holds a function, bound method or partial: deep copy keeps those by
    reference, so a clone would call back into the template's repository."""
    found, seen, pending = {}, set(), [value]
    while pending:
        item = pending.pop()
        if isinstance(item, (str, bytes, int, float, bool, type(None))) or id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, _CAPTURING):
            raise AssertionError("fixture state holds %r, which a clone would share with its "
                                 "template" % (item,))
        if isinstance(item, Path):
            if item == root or root in item.parents:
                found[id(item)] = item
            continue
        pending.extend(_children(item))
    return found


def clone_state(state: dict, old_root: Path, new_root: Path) -> dict:
    """A deep copy of `state` with each Path under `old_root` moved under `new_root`."""
    old_root, new_root = Path(old_root), Path(new_root)
    memo = {identity: new_root / path.relative_to(old_root)
            for identity, path in _paths_under(state, old_root).items()}
    copied = copy.deepcopy(state, memo)
    if str(old_root) in repr(copied):
        raise AssertionError("fixture state embeds its template path %s as text; a clone "
                             "would point at the template" % old_root)
    return copied


def fingerprint(value) -> str:
    """A text that equals another's exactly when the two states hold equal data.

    Objects compare by type name and attributes, never by address."""
    if isinstance(value, dict):
        return "{" + ",".join(sorted(fingerprint(k) + ":" + fingerprint(v) for k, v in value.items())) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(fingerprint(v) for v in value) + "]"
    if isinstance(value, (set, frozenset)):
        return "<" + ",".join(sorted(fingerprint(v) for v in value)) + ">"
    if isinstance(value, (str, bytes, int, float, bool, type(None), Path)):
        return repr(value)
    return type(value).__name__ + fingerprint(vars(value) if hasattr(value, "__dict__") else repr(value))


def clone_repository(template_root: Path, destination: Path) -> Path:
    """Copy a template repository, history included, and return its resolved root."""
    shutil.copytree(template_root, destination)
    return Path(destination).resolve()


def adopt(target, template, destination: Path) -> None:
    """Give `target` (a TestCase) a clone of `template`'s repository and built state.

    `template.root` is the repository root. The built state is every attribute the
    template's build added to a freshly constructed instance of its class, except `temp`,
    which belongs to the receiving test."""
    fresh = set(vars(type(template)("runTest")))
    state = {name: value for name, value in vars(template).items()
             if name not in fresh and name != "temp"}
    new_root = clone_repository(template.root, destination)
    target.__dict__.update(clone_state(state, template.root, new_root))


def built_state(case) -> dict:
    """The attributes a build added to `case`, apart from its temporary directory."""
    fresh = set(vars(type(case)("runTest")))
    return {name: value for name, value in vars(case).items()
            if name not in fresh and name != "temp"}


def merge_into(old, new):
    """Make `old` hold `new`'s data, keeping the identity of every unchanged container.

    A test may hold a reference into the fixture's state, such as an entry of the batch
    dictionary. Replacing the state by a copy would detach that reference, so a container
    that still has the same type is updated in place. Returns the object to keep."""
    if fingerprint(old) == fingerprint(new):
        return old
    if isinstance(old, dict) and isinstance(new, dict):
        for key in [key for key in old if key not in new]:
            del old[key]
        for key, value in new.items():
            old[key] = merge_into(old[key], value) if key in old else value
        return old
    if isinstance(old, list) and isinstance(new, list):
        if len(old) == len(new):
            for index, value in enumerate(new):
                old[index] = merge_into(old[index], value)
        else:
            old[:] = new
        return old
    if (type(old) is type(new) and hasattr(old, "__dict__") and not isinstance(old, Path)
            and not dataclasses.is_dataclass(old)):
        for key in [key for key in vars(old) if key not in vars(new)]:
            delattr(old, key)
        for key, value in vars(new).items():
            setattr(old, key, merge_into(getattr(old, key), value) if hasattr(old, key) else value)
        return old
    return new


def shared(key, build):
    """The template `build()` returns, built once per worker for `key`.

    `build` takes no argument and returns a fully built TestCase instance whose `root`
    attribute is the repository root. Its temporary directory lives until the worker exits."""
    full = (key, ambient())
    if full not in _TEMPLATES:
        _TEMPLATES[full] = build()
    return _TEMPLATES[full]


def cleanup_at_exit(case) -> None:
    """Run `case`'s registered cleanups when the worker exits."""
    atexit.register(case.doCleanups)


def clone(test, key, build):
    """A private, test-owned copy of the shared template for `key`.

    The copy is a new instance of the template's class with its own `temp` directory, which
    `test` removes at cleanup."""
    template = shared(key, build)
    copy_ = type(template)("runTest")
    copy_.temp = tempfile.TemporaryDirectory()
    test.addCleanup(copy_.temp.cleanup)
    adopt(copy_, template, Path(copy_.temp.name) / "repo")
    return copy_
