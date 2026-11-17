"""_census_coverage.py — record every read a driver makes, for the census-coverage tests.

Run as a child process:

    python3 _census_coverage.py RECORDS_JSON SCRIPT [driver arguments...]

It records each `open` audit event (`read`, or `write` for an open that can
write), each `os.listdir` and `os.scandir` audit event (`list`), and each
call of `os.stat` and `os.lstat` (`stat`). Each record carries its absolute
path, its access kind, the phase (`census` while `summaries_projection.
input_census` runs, `build` afterwards, `pre` before), the module and
function of the innermost crux frame past the generic helpers, and every
crux frame on the stack past them. It then writes the records, the census
members and the driver's exit code to RECORDS_JSON.

`coverage_gaps` compares the records with the census members in both
directions. It is a helper module, not a test module, so discovery never
collects it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent

#: Modules whose frames are generic helpers: attribution looks past them,
#: and an exemption never matches them (rule F2 of the approved revision).
GENERIC_MODULES = frozenset({"input_lanes", "operation_log", "untrusted", "_yaml_min"})
#: Functions of other modules that are generic helpers in the same sense.
GENERIC_FUNCTIONS = frozenset({("observation_evidence", "resolve_contained"),
                               ("observation_evidence", "valid_evidence_path")})

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def _crux_stack(skip: int) -> list[tuple[str, str]]:
    """(module, function) of every crux frame on the stack, innermost first,
    past the generic helpers and this harness."""
    here = os.path.abspath(__file__)
    root = str(SCRIPTS) + os.sep
    out = []
    frame = sys._getframe(skip)
    while frame is not None:
        filename = os.path.abspath(frame.f_code.co_filename)
        if filename.startswith(root) and filename != here:
            module = Path(filename).stem
            function = frame.f_code.co_name
            if module not in GENERIC_MODULES and (module, function) not in GENERIC_FUNCTIONS:
                out.append((module, function))
        frame = frame.f_back
    return out


def main(argv: list[str]) -> int:
    out_path, script, *args = argv
    sys.path.insert(0, str(SCRIPTS))
    import summaries_projection as sp

    records: list[dict] = []
    state = {"phase": "pre", "on": True}
    members: list = []

    def record(path, access: str) -> None:
        if not state["on"] or isinstance(path, int):
            return
        state["on"] = False
        try:
            stack = _crux_stack(3)
            if not stack:
                return
            records.append({"path": os.path.abspath(os.fsdecode(path)), "access": access,
                            "phase": state["phase"], "module": stack[0][0],
                            "function": stack[0][1], "stack": stack})
        finally:
            state["on"] = True

    def hook(event: str, hook_args) -> None:
        if event == "open":
            path, mode, flags = hook_args
            if path is None:
                return
            writes = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & _WRITE_FLAGS)
            record(path, "write" if writes else "read")
        elif event in ("os.listdir", "os.scandir"):
            record(hook_args[0] if hook_args[0] is not None else ".", "list")

    real_stat, real_lstat = os.stat, os.lstat

    def stat(path, *a, **kw):
        record(path, "stat")
        return real_stat(path, *a, **kw)

    def lstat(path, *a, **kw):
        record(path, "stat")
        return real_lstat(path, *a, **kw)

    real_census = sp.input_census

    def input_census(*a, **kw):
        state["phase"] = "census"
        try:
            census = real_census(*a, **kw)
        finally:
            state["phase"] = "build"
        members.extend(census.members)
        return census

    sp.input_census = input_census
    os.stat, os.lstat = stat, lstat
    sys.addaudithook(hook)
    import runpy
    sys.argv = [script, *args]
    code = 0
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    finally:
        state["on"] = False
        os.stat, os.lstat = real_stat, real_lstat
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"exit": code, "records": records, "members": members}, handle)
    return 0


def _under(path: str, base: str) -> bool:
    return path == base or path.startswith(base.rstrip(os.sep) + os.sep)


def coverage_gaps(data: dict, *, root: Path, tree: Path, outputs: list[Path],
                  exempt_functions: frozenset = frozenset(),
                  exempt_modules: frozenset = frozenset(),
                  members: list | None = None) -> tuple[list[dict], list[tuple[str, str]]]:
    """(uncovered build records, untouched census members).

    A build-phase record beneath the documentation tree is covered when it
    is a census member whose access kind covers it (read covers read and
    stat; list covers list and stat), a stat of an ancestor directory of a
    member, an exemption (by a function or a module anywhere on its crux
    stack), or a read or write of a declared output or its temporary file.
    Each census member must be touched by a build-phase record with the
    member's own access kind. `members` replaces the recorded members, so a
    positive control can remove or widen one.
    """
    root = Path(root)
    trees = {os.path.abspath(tree), os.path.realpath(tree)}
    members = data["members"] if members is None else members
    by_path: dict[str, set[str]] = {}
    for rel, access in members:
        by_path.setdefault(os.path.abspath(root / rel), set()).add(access)
    output_paths = set()
    for path in outputs:
        output_paths.update({os.path.abspath(path), os.path.abspath(str(path) + ".tmp")})
    covers = {"read": {"read", "stat"}, "list": {"list", "stat"}, "stat": {"stat"}}
    build = [r for r in data["records"] if r["phase"] == "build"
             and any(_under(r["path"], t) for t in trees)]
    uncovered = []
    for r in build:
        path, access = r["path"], r["access"]
        stack = {tuple(frame) for frame in r["stack"]}
        if any(frame in exempt_functions for frame in stack):
            continue
        if any(module in exempt_modules for module, _ in stack):
            continue
        if path in output_paths:
            continue
        if access in {a2 for a in by_path.get(path, ()) for a2 in covers[a]}:
            continue
        if access == "stat" and any(_under(m, path) and m != path for m in by_path):
            continue
        uncovered.append(r)
    touched = {(r["path"], r["access"]) for r in build}
    untouched = [(rel, access) for rel, access in members
                 if (os.path.abspath(root / rel), access) not in touched]
    return uncovered, sorted(set(untouched))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
