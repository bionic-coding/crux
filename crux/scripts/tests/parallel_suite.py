# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Run the plugin suite across worker processes, and fail closed on any discrepancy.

Usage:

    python3 crux/scripts/tests/parallel_suite.py START [-p PATTERN]
        [-t TOP] [-w N] [--records PATH] [--timings PATH]
        [--select ID]... [--failed-from RECORDS] [--tier TIER]...
    python3 crux/scripts/tests/parallel_suite.py --write-timings RECORDS
        [--timings-out PATH]

`--tier TIER` (dev, release or ephemeral; repeatable) runs only the tests that the
`test-tiers.json` manifest in START labels with a selected tier. It fails closed when START holds
no valid manifest, when a discovered test has no label, or when the selection keeps no test. It
cannot combine with `--flagged`, `--shared-evidence` or `--write-timings`.

The driver runs the tests that `python -m unittest discover -s START` runs,
through the same loader call, and prints the same summary lines. The literal
`unittest discover` command stays the serial reference. CI uses this driver.

`--failed-from RECORDS` reruns only what failed in an earlier `--records` run: every test
whose record has outcome `fail`, `error` or `uxsuccess`, a failed subtest selecting its parent
test, and a failed `setUpClass` or `setUpModule` holder selecting its class or module. The ids go
through `--select`, so a stale id (a test the tree no longer has) fails closed exactly as there.
A records file with no such test runs nothing, prints that, and exits 0. A missing file, a line
that is not JSON, or a file with no test record exits 2 with `FAILED CLOSED`. With `--select`,
the rerun keeps only the failed ids under a selected id. START and `-p` still name the tree to
discover. It cannot combine with `--flagged`, `--shared-evidence` or `--write-timings`.

How a run works:

1. The coordinator sets `sys.path[0]` to the working directory, as
   `python -m unittest` does, and snapshots `sys.path`. It then discovers the
   suite once. The discovered suite has one top-level child per module.
2. It cuts the children into units. A unit is the smallest group of tests the
   driver schedules. A module is one unit, except that a module splits into
   one unit per test class (named `module.Class`) when the split is safe: the
   module defines no `setUpModule` or `tearDownModule`, defines no `load_tests`,
   never calls `addModuleCleanup`, is in no `AFFINITY` group, and every one of
   its tests belongs to a class whose defining module is likewise free of those
   fixtures (a class a module imports runs the fixtures of its own module). A
   failed import, a module-level skip and any other shape stay one unit. The
   units hold exactly the discovered tests, each once, in discovery order.
3. It assigns the units to bins by position, never by test id. Each group in
   `AFFINITY` is one task that one bin runs whole. The assignment is
   longest-processing-time first: weight descending, then discovery order,
   with ties going to the lowest bin. A bin runs its units in discovery
   order. A unit weighs the seconds that the committed timings file holds for
   it (see below). Weights decide which bin runs a unit and never which tests
   run or in what order inside a module.
4. One spawned worker process runs each bin. A worker leads a process group
   of its own, restores the snapshot of `sys.path`, points fd 0 at /dev/null,
   repeats the identical discovery and the identical cut into units, and runs
   its positions as one `TestSuite`, so class and module fixtures behave as in
   a serial run. It sends one message as each unit begins and one result
   payload at the end.
5. The coordinator reconciles every payload against its own discovery. Any
   discrepancy fails the run closed with exit 2, naming the bin, and the test
   id where one applies. The discrepancies are: a manifest position that no
   bin holds or that two bins hold, a missing record, a duplicate
   record, a record outside the bin, a malformed payload, a worker manifest
   that differs from the coordinator's, a worker `sys.path` that differs from
   the coordinator's, a test neither started nor covered by a class or module
   fixture record, and zero tests. A worker that exits before its payload, or
   exits non-zero, also fails the run closed.

The shared pool. `CRUX_GATE_POOL` names a directory of slot files (see "The shared slot pool"
below), which `tools/release.py verify` and the release scheduler create so that every driver on the
host draws on one worker budget. A pooled run cuts the suite into bins of about POOL_BIN_SECONDS of
timings weight (at least one per slot), starts the heaviest bin first and starts each further bin when
it can take a slot, so a slot that a finished peer returns widens this run. Workers, reconciliation
and every refusal above are unchanged; the bins are only started later. `--workers N` still caps the
bins that run at once. A worker removes the variable from its environment, so a test that starts a
driver of its own does not draw on its parent's budget. A variable that names no usable pool fails
the run closed with exit 2. Without the variable the run is as described above.

The live environment. A run replaces `CRUX_HOME` with a fresh empty directory, removed when the run
ends, and removes `OPENROUTER_API_KEY`, `PERPLEXITY_API_KEY` and `CRUX_ALLOW_LIVE` from the environment
its workers inherit, so a suite started from an ordinary shell cannot reach a live model. The caller's
environment is restored on exit. A test that needs a key sets its own controlled value.
A run that names `--python-minor` also gets a fresh `UV_CACHE_DIR` (unless the caller set one),
because suites for different minors run at once and a shared uv cache lets one rebuild a script
environment while another runs it. The cost is a cold cache: each script environment downloads again.

The full-suite lock. A `--shared-evidence` run of a registered checkout suite holds
`<git-common-dir>/crux/full-suite.lock` while it executes, the lock `tools/test-suite.py` holds for a
full run, so the cycle writer defers its record commit and a second full run refuses with exit 2
naming the holder. It holds nothing under `--plan-test-evidence` or `--reuse-test-evidence-only`, for
a staged run, for a focused run of an unregistered start, or when `tools/test-suite.py` started it
(that tool names its inherited descriptor in `CRUX_FULL_SUITE_LOCK_FD`).

The timings file. `suite_timings.json` beside this driver maps a unit key to
seconds. A key is the last dotted part of the module name, plus `.ClassName`
for a class unit. A module unit weighs the sum of its class entries. A unit
with no entry weighs the median of all entries, or 1 when there are none.
`--timings PATH` reads another file, and a path that does not exist is
refused. When the default file is absent, every unit weighs 1 and the header
says so. A file that is not a JSON object of non-negative numbers fails the
run closed with exit 2 before discovery, because a half-read table would skew
the bins without a sign. A stale entry costs speed and nothing else.

`--write-timings RECORDS` regenerates the file from a `--records` JSONL, and
needs no START. It adds up the `duration` of each `test` record under its key
(`module.Class`, taken from the record id), ignores a record with no
duration, rounds to 0.01 s, and writes sorted keys with a trailing newline, so
equal input gives equal bytes. `--timings-out PATH` names the output file. Run
it after a full run: `parallel_suite.py crux/scripts/tests --records r.jsonl`,
then `parallel_suite.py --write-timings r.jsonl`. The first test record in each
unit also carries `fixture_duration`: elapsed unit time outside test methods,
including class setup. The timing writer includes it in the scheduling weight.

The interpreter check. When START is this driver's own directory, the driver
first imports `PLUGIN_SUITE_MODULES` in a child started with the argv prefix
the spawn context gives each worker (the interpreter and its flags). A bare
`uv run` of this file builds an isolated interpreter from the PEP 723 block
above, which declares no dependency, so discovery would fail on an import and
the run would exit 1 as a test failure. When a module cannot be imported the
driver exits 3 before discovery, names the interpreter, the missing modules and
the working command `uv run python3 crux/scripts/tests/parallel_suite.py
crux/scripts/tests`, and prints nothing on stdout. A START that is any other
directory is not checked, because its tests own their environment.

Exit codes: 0 when every test passed; 1 when a test failed or errored, or an
expected failure passed; 2 when the driver failed closed (a worker death, a
reconciliation mismatch with the discovery, or a driver exception); 3 when the
interpreter check refused the interpreter before discovery, so no test started;
128 plus the signal number when SIGINT, SIGTERM or SIGHUP stopped the run. The
evidence engine records exit 2 as a failed run and exit 3 as an interrupted one. A signal that arrives
during discovery takes effect once discovery returns, before any worker starts,
because the unittest loader turns an exception raised inside an import into a
failed-import test. A signal the driver inherited as ignored stays ignored, as
it does for the serial run.

When a run stops early, on a signal or a fail-closed discrepancy, the
coordinator names the unit each unfinished worker was running. It then stops
each such worker's process group, which holds every process that worker's
tests started. A worker that delivered its payload and exited 0 is left alone.

The header on stderr names the interpreter, `sys.executable`, `sys.prefix`,
where `crux` resolves, the discovered count, the worker and bin counts, and
each bin's weight and units, and the timings source, so a red test can be
traced to its bin. The driver prints no reproduction command. The serial reference for the whole
suite is `python -m unittest discover -s START`, run from the same directory.

The driver writes no file except the `--records` JSONL and, under
`--write-timings`, the timings file. Those records keep
every subtest's parameters, passing or not, so treat the file as test output.
The driver is stdlib-only.
"""

import argparse
import atexit
import collections
import contextlib
import datetime
import fcntl
import importlib.util
import json
import math
import multiprocessing
import multiprocessing.spawn
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import warnings
from multiprocessing.connection import wait as _wait_ready

# Use larger hosts while keeping the CPU cap in effective_workers. The full
# checkout command divides its own budget between plugin and tool suites.
DEFAULT_WORKERS = 16
DEFAULT_PATTERN = "test*.py"

# Modules that share on-disk state (the corpus derive's scratch directory)
# and so must run in one process. Each group runs whole in one bin, in
# discovery order. This list bears on correctness: test_parallel_suite fails
# when a module that calls the corpus derive sits outside every group.
AFFINITY = (("test_arch_corpus", "test_arch_pack_acceptance", "test_swift_app_gate"),)

# The measured seconds per scheduling unit. Absent from a checkout means uniform weights.
# `--write-timings` regenerates the file from a `--records` run.
DEFAULT_TIMINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "suite_timings.json")
# Decimal places the file keeps (0.01 s). MIN_WEIGHT is the least a unit weighs: a unit always
# costs a process turn, so a unit that rounds to zero still counts when the bins fill.
TIMINGS_ROUND = 2
MIN_WEIGHT = 0.01

Bin = collections.namedtuple("Bin", "index weight positions")
# One scheduling unit: `module` is the dotted module name, `name` is the module or
# `module.Class`, `ids` are its test ids in discovery order, `suite` is what a worker runs,
# and `key` is its timings key (the short module name, plus `.Class` for a class unit; a
# class a module imports keys under the module that defines it, as its test ids do).
Unit = collections.namedtuple("Unit", "module name ids suite key")

_PREFIX = "parallel_suite:"

# The third-party modules the discovered plugin suite imports at module level: yaml (two test
# modules), griffe (four; its distribution is griffelib) and httpx (forty-one, through the eager
# `crux` package import). Names only, no pins: the installers hold the pins. Modules the tests
# skip on when absent, the tree-sitter grammars, are not listed. A test scans the suite and fails
# when a test imports a module that is not listed here.
PLUGIN_SUITE_MODULES = ("yaml", "httpx", "griffe")
WORKING_COMMAND = "uv run python3 crux/scripts/tests/parallel_suite.py crux/scripts/tests"
_PROBE_TIMEOUT_SECONDS = 120
# The child reports on one marked line, so anything else an interpreter prints at startup
# (a sitecustomize, a .pth hook, a module that prints on import) is never read as a name.
_PROBE_MARKER = "crux-probe-missing:"
_PROBE_SOURCE = (
    "import importlib, sys\n"
    "_PROBE_MARKER = %r\n" % _PROBE_MARKER +
    "missing = []\n"
    "for name in sys.argv[1:]:\n"
    "    try:\n"
    "        importlib.import_module(name)\n"
    "    except ImportError:\n"
    "        missing.append(name)\n"
    "sys.stdout.write('\\n' + _PROBE_MARKER + ','.join(missing) + '\\n')\n"
)
# How long the coordinator waits for a message before it checks whether a
# worker has exited. A ready pipe or sentinel ends the wait at once.
_POLL_SECONDS = 1.0


class LedgerError(Exception):
    """A discrepancy that makes a run's result untrustworthy. Exit 2."""

    def __init__(self, branch, message, bin=None, test_id=None, module=None):
        super().__init__(message)
        self.branch = branch
        self.message = message
        self.bin = bin
        self.test_id = test_id
        self.module = module

    def __str__(self):
        parts = []
        if self.bin is not None:
            parts.append("bin %d" % self.bin)
        if self.module:
            parts.append("(module %s)" % self.module)
        parts.append("%s: %s" % (self.branch, self.message))
        if self.test_id is not None:
            parts.append("[%s]" % self.test_id)
        return " ".join(parts)


# The block between the CanonicalRecorder markers is a verbatim copy of the
# recorder the parity measurement used, which lives outside this tree. A copy
# made both runs emit comparable records; no regenerator owns the block, so
# edit it here. Its aliased imports keep it independent of this module's names.
# `canonical_key` sorts by id, kind, params, outcome, reason: the order a
# reader scans a diff in. CANONICAL_FIELDS lists the same five fields.
# BEGIN CanonicalRecorder
import json as _cr_json
import os as _cr_os
import time as _cr_time
import unittest as _cr_unittest
from unittest.case import _SubTest as _CrSubTest
from unittest.suite import _ErrorHolder as _CrErrorHolder

CANONICAL_FIELDS = ("id", "kind", "outcome", "reason", "params")


def canonical_key(record):
    """The canonical sort key: every canonical field, None read as ""."""
    return tuple("" if record.get(f) is None else str(record.get(f))
                 for f in ("id", "kind", "params", "outcome", "reason"))


class CanonicalRecorder(_cr_unittest.TestResult):
    """A TestResult that also emits one record per test event.

    Record: {id, kind: test|subtest|holder, outcome: ok|fail|error|skip|xfail|
    uxsuccess|none, reason, params} plus the non-canonical duration, bin, pid
    and detail. A test counts as run on a startTest/stopTest pair; `none` marks
    a started test with no outcome of its own (a parent whose subtests failed
    or skipped). An _ErrorHolder event (a class or module fixture failure or
    skip) is kind `holder` under its id, e.g. `setUpClass (mod.Cls)`.
    ModuleSkipped and _FailedTest are ordinary started tests.
    """

    def __init__(self, stream=None, descriptions=None, verbosity=None, bin=None):
        super().__init__(stream, descriptions, verbosity)
        self.bin = bin
        self.pid = _cr_os.getpid()
        self.records = []
        self._open = {}

    def _new(self, test_id, kind, outcome, reason="", params=None, detail=None):
        return {"id": test_id, "kind": kind, "outcome": outcome,
                "reason": "" if reason is None else str(reason), "params": params,
                "duration": None, "bin": self.bin, "pid": self.pid, "detail": detail}

    @staticmethod
    def _detail(err):
        if not err:
            return None
        exc = err[1]
        text = "%s: %s" % (type(exc).__name__, exc)
        return text[:500]

    def _outcome(self, test, outcome, reason="", err=None):
        if isinstance(test, _CrSubTest):
            self.records.append(self._new(test.test_case.id(), "subtest", outcome, reason,
                                          test._subDescription(), self._detail(err)))
            return
        entry = self._open.get(id(test))
        if entry is not None:
            entry[0]["outcome"] = outcome
            entry[0]["reason"] = "" if reason is None else str(reason)
            entry[0]["detail"] = self._detail(err)
            return
        kind = "holder" if isinstance(test, _CrErrorHolder) else "test"
        self.records.append(self._new(test.id(), kind, outcome, reason, None, self._detail(err)))

    def startTest(self, test):
        super().startTest(test)
        self._open[id(test)] = [self._new(test.id(), "test", "none"), _cr_time.perf_counter()]

    def stopTest(self, test):
        super().stopTest(test)
        entry = self._open.pop(id(test), None)
        if entry is not None:
            if entry[0]["duration"] is None:
                entry[0]["duration"] = round(_cr_time.perf_counter() - entry[1], 6)
            self.records.append(entry[0])

    def addDuration(self, test, elapsed):
        parent = getattr(super(), "addDuration", None)
        if parent is not None:
            parent(test, elapsed)
        entry = self._open.get(id(test))
        if entry is not None:
            entry[0]["duration"] = round(elapsed, 6)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._outcome(test, "ok")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._outcome(test, "fail", "", err)

    def addError(self, test, err):
        super().addError(test, err)
        self._outcome(test, "error", "", err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._outcome(test, "skip", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._outcome(test, "xfail", "", err)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._outcome(test, "uxsuccess")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            outcome = "ok"
        elif issubclass(err[0], test.failureException):
            outcome = "fail"
        else:
            outcome = "error"
        self.records.append(self._new(test.id(), "subtest", outcome, "",
                                      subtest._subDescription(), self._detail(err)))

    def sorted_records(self):
        return sorted(self.records, key=canonical_key)

    def write_jsonl(self, path):
        with open(path, "w", encoding="utf-8") as fh:
            for record in self.sorted_records():
                fh.write(_cr_json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
# END CanonicalRecorder


# ---------------------------------------------------------------------------
# Discovery and the manifest
# ---------------------------------------------------------------------------


class _ModuleLoader(unittest.TestLoader):
    """The standard loader; it also tags each module's suite with the module
    name. The tag changes nothing about the discovered tree."""

    def loadTestsFromModule(self, module, *args, **kwargs):
        suite = super().loadTestsFromModule(module, *args, **kwargs)
        try:
            suite._parallel_suite_module = module.__name__
        except AttributeError:
            pass
        return suite


def discover(start, pattern, top, select=()):
    """The `unittest discover` loader call: `discover(start, pattern, top)`.

    `select` names the modules, classes and methods to keep (see `select_tests`). Empty keeps every test.
    """
    suite = _ModuleLoader().discover(start, pattern, top)
    return select_tests(suite, select) if select else suite


def _selected(test_id, wanted):
    """Whether `test_id` is `wanted` or lies under it: a module, class or method id on a segment boundary."""
    return test_id == wanted or test_id.startswith(wanted + ".")


def _prune(suite, wanted):
    kept = unittest.TestSuite()
    tag = getattr(suite, "_parallel_suite_module", None)
    if tag is not None:
        kept._parallel_suite_module = tag
    for child in suite:
        if isinstance(child, unittest.TestSuite):
            pruned = _prune(child, wanted)
            if any(True for _ in _leaves(pruned)):
                kept.addTest(pruned)
        elif any(_selected(child.id(), item) for item in wanted):
            kept.addTest(child)
    return kept


def select_tests(suite, select):
    """The discovered `suite` cut to the tests under the ids in `select`.

    An id matches a test when it equals the test's id or is a dotted prefix of it, so a module, a class
    or a method selects what it contains and `Alpha` never selects `AlphaExtra`. An id that matches no
    discovered test raises `LedgerError`: a stale selection must not pass by running nothing.
    """
    wanted = tuple(dict.fromkeys(select))
    ids = [leaf.id() for leaf in _leaves(suite)]
    missing = [item for item in wanted if not any(_selected(test_id, item) for test_id in ids)]
    if missing:
        error = LedgerError("selection", "selection id not found: " + ", ".join(missing))
        error.missing = missing
        raise error
    return _prune(suite, wanted)


def _leaves(test):
    if isinstance(test, unittest.TestSuite):
        for child in test:
            yield from _leaves(child)
    else:
        yield test


def _module_name(position, child):
    name = getattr(child, "_parallel_suite_module", None)
    if name:
        return name
    for leaf in _leaves(child):
        if type(leaf).__module__ == "unittest.loader":
            # A failed import or a module-level skip: the loader names the
            # test after the module.
            return getattr(leaf, "_testMethodName", None) or leaf.id()
        return type(leaf).__module__
    return "<position %d>" % position


def build_manifest(suite):
    """One (module name, test ids) entry per top-level child, in order."""
    return [(_module_name(position, child), tuple(leaf.id() for leaf in _leaves(child)))
            for position, child in enumerate(suite)]


def _module_hazard(module):
    """Why a module's tests must run together, or None when its classes may be
    scheduled apart. Module fixtures and module cleanups tie every class to one
    process; `load_tests` builds a suite the driver cannot cut safely."""
    for attr in ("setUpModule", "tearDownModule", "load_tests"):
        if hasattr(module, attr):
            return attr
    try:
        with open(module.__file__, encoding="utf-8", errors="replace") as fh:
            if "addModuleCleanup" in fh.read():
                return "addModuleCleanup"
    except (AttributeError, OSError, TypeError):
        # A module with no readable source cannot be shown safe.
        return "no readable source"
    return None


def _class_units(module, child):
    """The per-class units of a module's suite, or None when the module stays
    one unit."""
    if getattr(child, "_parallel_suite_module", None) != module:
        return None
    loaded = sys.modules.get(module)
    if loaded is None or _module_hazard(loaded) is not None:
        return None
    units = []
    for part in child:
        if not isinstance(part, unittest.TestSuite):
            return None
        leaves = list(_leaves(part))
        if not leaves:
            continue
        classes = {type(leaf) for leaf in leaves}
        if len(classes) != 1:
            return None
        (cls,) = classes
        # A class the module imports runs its module fixtures with the module that defines
        # it, so that module needs the same clearance.
        owner = sys.modules.get(cls.__module__)
        if not issubclass(cls, unittest.TestCase) or owner is None or (
                owner is not loaded and _module_hazard(owner) is not None):
            return None
        units.append(Unit(module, "%s.%s" % (module, cls.__name__),
                          tuple(leaf.id() for leaf in leaves), part,
                          "%s.%s" % (cls.__module__.rpartition(".")[2], cls.__name__)))
    return units if len(units) > 1 else None


def build_units(suite, affinity=AFFINITY):
    """The scheduling units of a discovered suite, in discovery order. Call it
    after discovery: it reads the imported module objects. The coordinator and
    every worker call it on their own identical discovery."""
    pinned = {name for group in affinity for name in group}
    units = []
    for position, child in enumerate(suite):
        module = _module_name(position, child)
        split = None if module.rpartition(".")[2] in pinned else _class_units(module, child)
        if split is None:
            units.append(Unit(module, module, tuple(leaf.id() for leaf in _leaves(child)), child,
                              module.rpartition(".")[2]))
        else:
            units.extend(split)
    return units


def unit_manifest(units):
    """One (unit name, test ids) entry per unit, in order."""
    return [(unit.name, unit.ids) for unit in units]


# ---------------------------------------------------------------------------
# Timings
# ---------------------------------------------------------------------------


def record_key(test_id):
    """The timings key of a test id, or None when the id has no module and class."""
    parts = test_id.split(".")
    return ".".join(parts[-3:-1]) if len(parts) >= 3 else None


def _is_seconds(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


def read_timings(path):
    """The timings mapping in `path`. Raise LedgerError("malformed-timings")
    when the file is unreadable, not JSON, or not an object of non-negative
    numbers."""
    def refuse(why):
        raise LedgerError("malformed-timings", "%s: %s" % (path, why))

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        refuse("%s: %s" % (type(exc).__name__, exc))
    if not isinstance(data, dict):
        refuse("the file is not a JSON object")
    for key, value in data.items():
        if not _is_seconds(value):
            refuse("%r maps to %r, not a non-negative number" % (key, value))
    return data


def load_timings(explicit):
    """(timings, note) for a run. An explicit path must exist. The default file
    may be absent, which gives uniform weights."""
    path = explicit or DEFAULT_TIMINGS
    if not explicit and not os.path.exists(path):
        return {}, "none (%s absent): every unit weighs 1" % path
    timings = read_timings(path)
    return timings, "%s (%d entries)" % (path, len(timings))


def unit_weights(units, timings):
    """The weight of each unit, in seconds. A module unit weighs the sum of its
    class entries; a unit with no entry weighs the median of all entries, or 1
    when there are none."""
    median = statistics.median(timings.values()) if timings else 1
    weights = []
    for unit in units:
        key = unit.key
        if unit.name == unit.module:
            parts = [v for k, v in timings.items() if k.startswith(key + ".")]
            weight = math.fsum(parts) if parts else median
        else:
            weight = timings.get(key, median)
        weights.append(max(weight, MIN_WEIGHT))
    return weights


def timings_from_records(path):
    """Seconds per timings key from a `--records` JSONL: the sum of the
    `duration` of each `test` record. Records with no duration are ignored."""
    sums = collections.defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise LedgerError("malformed-records", "%s line %d: %s" % (path, number, exc)) from None
            if not isinstance(record, dict) or record.get("kind") != "test":
                continue
            key = record_key(record["id"]) if isinstance(record.get("id"), str) else None
            if key is not None and _is_seconds(record.get("duration")):
                sums[key].append(record["duration"])
                if _is_seconds(record.get("fixture_duration")):
                    sums[key].append(record["fixture_duration"])
    return {key: round(math.fsum(values), TIMINGS_ROUND) for key, values in sorted(sums.items())}


_FAILING = frozenset({"fail", "error", "uxsuccess"})
_HOLDER_FAILED = re.compile(r"^(?:setUp|tearDown)(?:Class|Module) \((.+)\)$")


def failed_ids_from_records(path):
    """The ids of the tests that failed in a `--records` JSONL, sorted.

    A subtest record already carries its parent's id. A failed class or module fixture selects that
    class or module. Raises `LedgerError` on a missing file, a non-JSON line or a file with no test record.
    """
    failed, tests = set(), 0
    try:
        fh = open(path, encoding="utf-8")
    except OSError as exc:
        raise LedgerError("malformed-records", "cannot read %s: %s" % (path, exc)) from None
    with fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise LedgerError("malformed-records", "%s line %d: %s" % (path, number, exc)) from None
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                continue
            kind, outcome = record.get("kind"), record.get("outcome")
            if kind in ("test", "subtest"):
                tests += 1
                if outcome in _FAILING:
                    failed.add(record["id"])
            elif kind == "holder" and outcome in _FAILING:
                match = _HOLDER_FAILED.match(record["id"])
                if match:
                    failed.add(match.group(1))
    if not tests:
        raise LedgerError("malformed-records", "%s holds no test record" % path)
    return sorted(failed)


def format_timings(timings):
    """The committed bytes of a timings mapping: sorted keys, one per line."""
    return json.dumps(timings, indent=1, sort_keys=True) + "\n"


def write_timings(records_path, out_path):
    """Regenerate the timings file. Return the number of entries."""
    timings = timings_from_records(records_path)
    if not timings:
        raise LedgerError("malformed-records", "%s holds no test record with a duration" % records_path)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(format_timings(timings))
    return len(timings)


# ---------------------------------------------------------------------------
# Running one bin
# ---------------------------------------------------------------------------


class _Announced(unittest.TestSuite):
    """One module's suite, which reports its name as it begins."""

    def __init__(self, child, name, announce):
        super().__init__([child])
        self._name = name
        self._announce = announce

    def run(self, result, debug=False):
        if self._announce is not None:
            self._announce(self._name)
        first = len(result.records)
        started = time.perf_counter()
        try:
            return super().run(result, debug)
        finally:
            elapsed = time.perf_counter() - started
            tests = [r for r in result.records[first:] if r["kind"] == "test"]
            if tests:
                tests[0]["fixture_duration"] = round(max(
                    0.0, elapsed - math.fsum(r.get("duration") or 0.0 for r in tests)), 6)


def run_positions(children, positions, bin_index, names=None, announce=None):
    """Run the children at `positions` as one suite, as TextTestRunner runs a
    suite, and return the CanonicalRecorder that recorded it."""
    result = CanonicalRecorder(sys.stderr, True, 1, bin=bin_index)
    unittest.registerResult(result)
    result.failfast = False
    result.buffer = False
    result.tb_locals = False
    suite = unittest.TestSuite()
    for position in positions:
        name = names[position] if names else "<position %d>" % position
        suite.addTest(_Announced(children[position], name, announce))
    with warnings.catch_warnings():
        if not sys.warnoptions:
            warnings.simplefilter("default")
        result.startTestRun()
        try:
            suite(result)
        finally:
            result.stopTestRun()
    return result


def _description(test):
    """TextTestResult.getDescription with descriptions on."""
    short = getattr(test, "shortDescription", None)
    doc = short() if short is not None else None
    return "\n".join((str(test), doc)) if doc else str(test)


def _position_of(test, positions):
    """The manifest position a failure, error or unexpected success belongs
    to, or None when no test id in `positions` matches. The coordinator
    orders the summary blocks by it, and refuses a row with None.

    Known limit: when one test id sits at two positions, which happens when
    one TestCase class is imported into two test modules, the row takes the
    first of them. The summary blocks then sort by that first position.
    Import fixture modules instead of their TestCase classes to avoid running
    the imported tests twice.
    """
    if isinstance(test, _CrSubTest):
        test = test.test_case
    test_id = test.id()
    if test_id in positions:
        return positions[test_id]
    # A class or module fixture record, e.g. `tearDownModule (mod)`.
    match = _HOLDER_RE.match(test_id)
    if match:
        target = match.group(2) + "."
        for known, position in positions.items():
            if known.startswith(target):
                return position
    return None


def result_payload(result, bin_index, manifest, sys_path, bin_positions):
    """The picklable payload a worker sends for its bin. Each failure, error
    and unexpected success carries its manifest position, looked up among
    the bin's own positions only."""
    positions = {}
    for position in bin_positions:
        for test_id in manifest[position][1]:
            positions.setdefault(test_id, position)

    def where(test):
        return _position_of(test, positions)

    return {
        "bin": bin_index,
        "manifest": [(name, tuple(ids)) for name, ids in manifest],
        "sys_path": list(sys_path),
        "records": list(result.records),
        "tests_run": result.testsRun,
        "failures": [(_description(test), err, where(test)) for test, err in result.failures],
        "errors": [(_description(test), err, where(test)) for test, err in result.errors],
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected": [(_description(test), where(test)) for test in result.unexpectedSuccesses],
    }


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------

_PAYLOAD_KEYS = frozenset({"bin", "manifest", "sys_path", "records", "tests_run", "failures",
                           "errors", "skipped", "expected_failures", "unexpected"})
_KINDS = frozenset({"test", "subtest", "holder"})
_OUTCOMES = frozenset({"ok", "fail", "error", "skip", "xfail", "uxsuccess", "none"})
_HOLDER_RE = re.compile(r"^(\w+) \((.+)\)$")
# A failed setUpClass or setUpModule stops its tests from starting.
_COVERING = frozenset({"setUpClass", "setUpModule"})


class Summary:
    """The merged result of every bin."""

    def __init__(self):
        self.tests_run = 0
        self.failures = []
        self.errors = []
        self.skipped = 0
        self.expected_failures = 0
        self.unexpected = []
        self.records = []

    def was_successful(self):
        return not self.failures and not self.errors and not self.unexpected


def _is_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_strings(value):
    return isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value)


def _is_rows(value, width):
    """A list of rows of `width - 1` strings, each ending in a position or
    None. `_check_row_positions` refuses None and any position outside the
    bin."""
    return isinstance(value, (list, tuple)) and all(
        isinstance(v, (list, tuple)) and len(v) == width
        and all(isinstance(s, str) for s in v[:-1]) and (v[-1] is None or _is_count(v[-1]))
        for v in value)


def _check_row_positions(payload, b):
    """Refuse a failure, error or unexpected-success row whose position is
    None or is not one of the bin's positions."""
    held = frozenset(b.positions)
    for key in ("failures", "errors", "unexpected"):
        for row in payload[key]:
            position = row[-1]
            if position is None:
                raise LedgerError("malformed-payload", "a row in %s has no manifest position: %s"
                                  % (key, row[0].splitlines()[0] if row[0] else "?"), bin=b.index)
            if position not in held:
                raise LedgerError("malformed-payload", "a row in %s names position %d, which this "
                                  "bin does not hold" % (key, position), bin=b.index)


def _is_manifest(value):
    return isinstance(value, (list, tuple)) and all(
        isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], str) and _is_strings(v[1])
        for v in value)


def _check_payload(payload, index):
    def refuse(why):
        raise LedgerError("malformed-payload", why, bin=index)

    if not isinstance(payload, dict):
        refuse("the payload is not a mapping")
    missing = sorted(_PAYLOAD_KEYS - set(payload))
    if missing:
        refuse("the payload lacks %s" % ", ".join(missing))
    if payload["bin"] != index:
        refuse("the payload names bin %r" % (payload["bin"],))
    for key in ("tests_run", "skipped", "expected_failures"):
        if not _is_count(payload[key]):
            refuse("%s is not a count" % key)
    if not _is_manifest(payload["manifest"]):
        refuse("the manifest is not a list of (module, ids)")
    if not _is_strings(payload["sys_path"]):
        refuse("sys_path is not a list of strings")
    if not (_is_rows(payload["failures"], 3) and _is_rows(payload["errors"], 3)):
        refuse("failures or errors is not a list of (description, traceback, position)")
    if not _is_rows(payload["unexpected"], 2):
        refuse("unexpected is not a list of (description, position)")
    if not isinstance(payload["records"], (list, tuple)):
        refuse("records is not a list")
    for record in payload["records"]:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            refuse("a record is not a mapping with a string id")
        if record.get("kind") not in _KINDS:
            refuse("record %s has kind %r" % (record["id"], record.get("kind")))
        if record.get("outcome") not in _OUTCOMES:
            refuse("record %s has outcome %r" % (record["id"], record.get("outcome")))


def _normal(manifest):
    return [(name, tuple(ids)) for name, ids in manifest]


def _manifest_difference(ours, theirs):
    for position in range(max(len(ours), len(theirs))):
        mine = ours[position] if position < len(ours) else None
        other = theirs[position] if position < len(theirs) else None
        if mine == other:
            continue
        describe = (lambda entry: "nothing" if entry is None
                    else "%s with %d tests" % (entry[0], len(entry[1])))
        return ("at position %d the coordinator has %s and the worker has %s"
                % (position, describe(mine), describe(other)))
    return "the manifests differ"


def reconcile(manifest, bins, payloads, sys_path):
    """Check every bin's payload against the coordinator's discovery and
    merge them. Raise LedgerError on the first discrepancy."""
    manifest = _normal(manifest)
    if not any(ids for _, ids in manifest):
        raise LedgerError("zero-tests", "discovery found zero tests")
    _check_coverage(manifest, bins)
    summary = Summary()
    failures, errors, unexpected = [], [], []
    for b in bins:
        payload = payloads.get(b.index)
        if payload is None:
            raise LedgerError("missing-record", "the bin sent no result payload", bin=b.index)
        _check_payload(payload, b.index)
        theirs = _normal(payload["manifest"])
        if theirs != manifest:
            raise LedgerError("manifest-mismatch", _manifest_difference(manifest, theirs), bin=b.index)
        if list(payload["sys_path"]) != list(sys_path):
            raise LedgerError("sys-path-mismatch", "the worker's sys.path after discovery is %r; the "
                              "coordinator's is %r" % (payload["sys_path"], list(sys_path)), bin=b.index)
        _check_row_positions(payload, b)

        expected = collections.Counter()
        order = []
        for position in b.positions:
            for test_id in manifest[position][1]:
                if not expected[test_id]:
                    order.append(test_id)
                expected[test_id] += 1
        started = collections.Counter()
        covering = []
        for record in payload["records"]:
            record_id = record["id"]
            if record["kind"] == "holder":
                match = _HOLDER_RE.match(record_id)
                target = match.group(2) + "." if match else None
                if target is None or not any(t.startswith(target) for t in expected):
                    raise LedgerError("foreign-record", "a fixture record for no test in this bin",
                                      bin=b.index, test_id=record_id)
                if match.group(1) in _COVERING:
                    covering.append(target)
            elif record_id not in expected:
                raise LedgerError("foreign-record", "a record for a test outside this bin",
                                  bin=b.index, test_id=record_id)
            elif record["kind"] == "test":
                started[record_id] += 1
        for test_id in order:
            if started[test_id] > expected[test_id]:
                raise LedgerError("duplicate-record", "%d records for a test discovered %d times"
                                  % (started[test_id], expected[test_id]), bin=b.index, test_id=test_id)
        recorded = sum(started.values())
        if payload["tests_run"] > recorded:
            raise LedgerError("missing-record", "the worker started %d tests and recorded %d"
                              % (payload["tests_run"], recorded), bin=b.index)
        if payload["tests_run"] < recorded:
            raise LedgerError("duplicate-record", "the worker recorded %d tests and started %d"
                              % (recorded, payload["tests_run"]), bin=b.index)
        for test_id in order:
            if started[test_id] < expected[test_id] and not any(test_id.startswith(c) for c in covering):
                raise LedgerError("unaccounted-id", "a test neither started nor covered by a "
                                  "setUpClass or setUpModule record", bin=b.index, test_id=test_id)

        summary.tests_run += payload["tests_run"]
        failures.extend(payload["failures"])
        errors.extend(payload["errors"])
        summary.skipped += payload["skipped"]
        summary.expected_failures += payload["expected_failures"]
        unexpected.extend(payload["unexpected"])
        summary.records.extend(payload["records"])
    # A serial run lists these in discovery order. One bin holds each
    # position, so a stable sort by position keeps each bin's own order.
    summary.failures = [(d, e) for d, e, _ in sorted(failures, key=lambda f: f[2])]
    summary.errors = [(d, e) for d, e, _ in sorted(errors, key=lambda f: f[2])]
    summary.unexpected = [d for d, _ in sorted(unexpected, key=lambda u: u[1])]
    return summary


def _check_coverage(manifest, bins):
    """Refuse unless the bins hold every manifest position exactly once."""
    holders = collections.defaultdict(list)
    for b in bins:
        for position in b.positions:
            holders[position].append(b.index)
    for position in sorted(holders):
        if not 0 <= position < len(manifest):
            raise LedgerError("bin-coverage", "position %d is outside the manifest of %d units"
                              % (position, len(manifest)), bin=holders[position][0])
    for position, (name, _) in enumerate(manifest):
        held = holders.get(position, [])
        if not held:
            raise LedgerError("bin-coverage", "position %d is in no bin" % position, module=name)
        if len(held) > 1:
            raise LedgerError("bin-coverage", "position %d is in bins %s"
                              % (position, ", ".join(str(i) for i in held)), module=name)


def format_summary(summary, elapsed):
    """The text TextTestRunner prints after its progress line."""
    sep1, sep2 = "=" * 70, "-" * 70
    out = ["\n"]
    for flavour, entries in (("ERROR", summary.errors), ("FAIL", summary.failures)):
        for description, err in entries:
            out.append("%s\n%s: %s\n%s\n%s\n" % (sep1, flavour, description, sep2, err))
    if summary.unexpected:
        out.append(sep1 + "\n")
        for description in summary.unexpected:
            out.append("UNEXPECTED SUCCESS: %s\n" % description)
    run = summary.tests_run
    out.append(sep2 + "\n")
    out.append("Ran %d test%s in %.3fs\n\n" % (run, run != 1 and "s" or "", elapsed))
    infos = []
    if not summary.was_successful():
        out.append("FAILED")
        if summary.failures:
            infos.append("failures=%d" % len(summary.failures))
        if summary.errors:
            infos.append("errors=%d" % len(summary.errors))
    elif run == 0 and not summary.skipped:
        out.append("NO TESTS RAN")
    else:
        out.append("OK")
    if summary.skipped:
        infos.append("skipped=%d" % summary.skipped)
    if summary.expected_failures:
        infos.append("expected failures=%d" % summary.expected_failures)
    if summary.unexpected:
        infos.append("unexpected successes=%d" % len(summary.unexpected))
    out.append(" (%s)\n" % ", ".join(infos) if infos else "\n")
    return "".join(out)


def exit_code(summary):
    """0 or 1, by TestResult.wasSuccessful: an unexpected success fails."""
    return 0 if summary.was_successful() else 1


# ---------------------------------------------------------------------------
# Bins
# ---------------------------------------------------------------------------


def assign_bins(units, workers, affinity=AFFINITY, timings=None):
    """Assign unit positions to at most `workers` bins. Deterministic.

    `units` are `Unit`s. AFFINITY and the timings name a module by its last
    dotted part, so a run under a top-level directory, whose modules are named
    `pkg.test_x`, matches the same entries. Two groups that share a name are
    refused: a position would land in two bins. Every unit of a module in a
    group joins the group's one task."""
    group_of = {}
    for number, group in enumerate(affinity):
        for name in sorted(set(group)):
            if name in group_of:
                raise LedgerError("affinity-overlap", "%s sits in affinity groups %d and %d"
                                  % (name, group_of[name], number), module=name)
            group_of[name] = number
    short = [unit.module.rpartition(".")[2] for unit in units]
    grouped = set()
    tasks = []
    for group in affinity:
        members = [position for position, name in enumerate(short) if name in group]
        if members:
            tasks.append(members)
            grouped.update(members)
    tasks.extend([position] for position in range(len(units)) if position not in grouped)
    if not tasks:
        return []
    each = unit_weights(units, timings or {})
    weight = {id(task): math.fsum(each[p] for p in task) for task in tasks}
    tasks.sort(key=lambda task: (-weight[id(task)], task[0]))
    count = max(1, min(workers, len(tasks)))
    loads = [0.0] * count
    members = [[] for _ in range(count)]
    for task in tasks:
        target = min(range(count), key=lambda i: (loads[i], i))
        loads[target] += weight[id(task)]
        members[target].extend(task)
    return [Bin(i, loads[i], tuple(sorted(members[i]))) for i in range(count)]


def effective_workers(requested):
    """The requested count (DEFAULT_WORKERS when None), capped by the CPUs this
    process may use, which an affinity mask can make fewer than the host's."""
    wanted = DEFAULT_WORKERS if requested is None else requested
    return max(1, min(wanted, os.process_cpu_count() or 1))


# ---------------------------------------------------------------------------
# The shared slot pool
# ---------------------------------------------------------------------------
#
# `tools/release.py verify` runs the release preflight and `sync.sh --dry-run` at the same time, and
# each starts suite drivers. Separate processes cannot share a counter, so the host's worker budget
# lives in a directory: `size` holds the slot count, `slot-NNNN` is one slot, `waiters/` holds one
# record per driver that still has bins to start. A process holds a slot by holding an exclusive
# `flock` on its file. The kernel drops the lock when the holder exits, even on SIGKILL, so a dead
# peer frees its slots and no token is ever lost.
#
# A driver that sees `CRUX_GATE_POOL` cuts the suite into many small bins instead of one bin per
# worker and starts each bin when it can take a slot. A slot that a finished peer (or a finished
# gate) returns goes to the next driver to ask, so a running suite widens as peers finish. That is
# the rebalance a fixed `--workers` count cannot make. Waiting drivers publish the weight they still
# have to start; a driver defers to a live waiter with more weight left, which hands a freed slot to
# the longest remaining work. The priority is a speed hint and never a safety property: a record
# that is not refreshed for WAITER_STALE_SECONDS stops counting.
#
# A driver started without the variable behaves exactly as before. A variable that names no usable
# pool stops the driver closed (exit 2): running unbounded would defeat the budget it was given.

POOL_ENV = "CRUX_GATE_POOL"
POOL_POLL_SECONDS = 0.2
# Target weight of one pooled bin, in timings seconds. A bin costs a process start and a repeat of
# discovery (about 2 s for this suite), so bins stay large enough that this is a few percent of the work.
POOL_BIN_SECONDS = 120.0
WAITER_STALE_SECONDS = 30.0
_WAITER_WEIGHT_FORMAT = "%020.3f"
_WAITER_FORMAT = _WAITER_WEIGHT_FORMAT + " %017.3f\n"


class PoolError(Exception):
    """The directory CRUX_GATE_POOL names is not a usable pool."""


class SlotPool:
    """One handle on a pool directory. A handle holds slots; two handles contend, even in one process."""

    def __init__(self, directory, clock=time.time):
        self.directory = os.path.abspath(os.fspath(directory))
        self._clock = clock
        self._held = {}
        try:
            with open(os.path.join(self.directory, "size"), encoding="ascii") as handle:
                size = int(handle.read().strip())
        except (OSError, ValueError) as err:
            raise PoolError("%s is not a slot pool: its size cannot be read (%s)" % (self.directory, err)) from err
        if size < 1:
            raise PoolError("%s is not a slot pool: its size is %d" % (self.directory, size))
        for number in range(size):
            if not os.path.isfile(self._slot_path(number)):
                raise PoolError("%s is not a slot pool: slot %d is missing" % (self.directory, number))
        if not os.path.isdir(os.path.join(self.directory, "waiters")):
            raise PoolError("%s is not a slot pool: its waiters directory is missing" % self.directory)
        self.size = size

    @classmethod
    def create(cls, size, directory=None):
        """Make a pool of `size` slots in `directory` (a new private temporary directory when None)."""
        if size < 1:
            raise PoolError("a pool needs at least one slot")
        if directory is None:
            directory = tempfile.mkdtemp(prefix="crux-gate-pool-")
        directory = os.fspath(directory)
        os.makedirs(os.path.join(directory, "waiters"), mode=0o700, exist_ok=True)
        for number in range(size):
            with open(os.path.join(directory, "slot-%04d" % number), "a", encoding="ascii"):
                pass
        with open(os.path.join(directory, "size"), "w", encoding="ascii") as handle:
            handle.write("%d\n" % size)
        return cls(directory)

    @classmethod
    def from_environ(cls, environ=None):
        """The pool CRUX_GATE_POOL names, None when it is unset. Raises PoolError when it names no usable pool."""
        value = (os.environ if environ is None else environ).get(POOL_ENV, "")
        return cls(value) if value else None

    def _slot_path(self, number):
        return os.path.join(self.directory, "slot-%04d" % number)

    def waiter(self, weight=0.0):
        return PoolWaiter(self, weight)

    def try_acquire(self, waiter=None):
        """Take a free slot and return its number, or None. Never waits.

        With a `waiter`, a live waiter that has more weight left to start goes first (equal weights: the
        lower record name). The waiter's own record is refreshed, so a driver that keeps polling keeps
        its place.
        """
        if waiter is not None:
            waiter.refresh()
            if waiter.deferred():
                return None
        for number in range(self.size):
            if number in self._held:
                continue
            descriptor = os.open(self._slot_path(number), os.O_RDWR)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(descriptor)
                continue
            self._held[number] = descriptor
            return number
        return None

    def release(self, number):
        descriptor = self._held.pop(number, None)
        if descriptor is not None:
            os.close(descriptor)  # closing the descriptor drops the lock

    def release_all(self):
        for number in list(self._held):
            self.release(number)

    @property
    def held(self):
        return sorted(self._held)


class PoolWaiter:
    """A driver's record that it has bins left to start, with the weight of those bins.

    The record is a file under `waiters/` that its owner locks for as long as it exists. Another process
    that can take that lock knows the owner is gone and deletes the record.
    """
    _counter = 0

    def __init__(self, pool, weight):
        PoolWaiter._counter += 1
        self.pool, self.weight = pool, float(weight)
        self.name = "%08d.%04d" % (os.getpid(), PoolWaiter._counter)
        self.path = os.path.join(pool.directory, "waiters", self.name)
        self._descriptor = None

    def refresh(self, weight=None):
        """Create the record on first use, then stamp it with the current weight and time."""
        if weight is not None:
            self.weight = float(weight)
        if self._descriptor is None:
            descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            self._descriptor = descriptor
        os.pwrite(self._descriptor, (_WAITER_FORMAT % (self.weight, self.pool._clock())).encode("ascii"), 0)

    def close(self):
        """Drop the record: this driver has nothing left to start."""
        if self._descriptor is not None:
            try:
                os.unlink(self.path)
            except OSError:
                pass
            os.close(self._descriptor)
            self._descriptor = None

    def deferred(self):
        """Whether a live, fresh waiter of another process or handle outranks this one."""
        mine = (-float(_WAITER_WEIGHT_FORMAT % self.weight), self.name)
        directory = os.path.join(self.pool.directory, "waiters")
        try:
            names = os.listdir(directory)
        except OSError:
            return False
        for name in names:
            if name == self.name:
                continue
            path = os.path.join(directory, name)
            try:
                descriptor = os.open(path, os.O_RDONLY)
            except OSError:
                continue
            try:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    pass  # the owner holds it: alive
                else:
                    try:
                        os.unlink(path)  # nobody holds it: the owner is gone
                    except OSError:
                        pass
                    continue
                try:
                    weight, stamp = (float(x) for x in os.pread(descriptor, 64, 0).decode("ascii").split())
                except (OSError, ValueError):
                    return True  # a record caught mid-write: defer once rather than guess
                if self.pool._clock() - stamp > WAITER_STALE_SECONDS:
                    continue
                if (-weight, name) < mine:
                    return True
            finally:
                os.close(descriptor)
        return False


def pooled_bin_count(units, timings, pool_size, affinity=AFFINITY):
    """How many bins a pooled run cuts the suite into: about POOL_BIN_SECONDS of weight each, at least one
    per slot, and no more than there are tasks to place."""
    tasks = len(assign_bins(units, max(1, len(units)), affinity, timings))
    total = math.fsum(unit_weights(units, timings or {}))
    return max(1, min(tasks, max(pool_size, math.ceil(total / POOL_BIN_SECONDS))))


# ---------------------------------------------------------------------------
# The worker
# ---------------------------------------------------------------------------


def _disable_fixture_git_maintenance():
    """Point every `git init` a test runs at a template whose config turns auto maintenance off.

    Git copies the template's `config` into each new repository, so the setting lands before the
    first commit. Without it, a commit can start background maintenance that packs and deletes
    loose objects while the test clones the repository, and the clone fails on a vanished file.
    The copy keeps git's default template content. A caller's own template is left alone.
    """
    if "GIT_TEMPLATE_DIR" in os.environ:
        return
    template = tempfile.mkdtemp(prefix="crux-git-template-")
    atexit.register(shutil.rmtree, template, True)
    try:
        exec_path = subprocess.run(["git", "--exec-path"], capture_output=True, text=True).stdout.strip()
    except OSError:
        exec_path = ""
    default = os.path.join(exec_path, os.pardir, os.pardir, "share", "git-core", "templates")
    if exec_path and os.path.isdir(default):
        shutil.copytree(default, template, dirs_exist_ok=True)
    with open(os.path.join(template, "config"), "w", encoding="utf-8") as handle:
        handle.write("[maintenance]\n\tauto = false\n")
    os.environ["GIT_TEMPLATE_DIR"] = template


def _worker_main(conn, bin_index, positions, start, pattern, top, snapshot, expected, select=()):
    # Lead a process group, so the coordinator can stop this worker and every
    # process its tests start with one killpg. The terminal's signals reach
    # only the coordinator's group, and the coordinator stops the workers.
    try:
        os.setpgid(0, 0)
    except OSError:
        pass
    # The pool is the coordinator's budget. A test that starts a driver of its own must not draw on it:
    # its parent bin already holds a slot, and a nested driver waiting for another could wait on itself.
    os.environ.pop(POOL_ENV, None)
    _disable_fixture_git_maintenance()
    # A background process group that writes to a terminal set to `tostop` is
    # stopped by SIGTTOU. Ignoring it lets the write through, as in a serial
    # run, which writes from the foreground group.
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    devnull = os.open(os.devnull, os.O_RDONLY)
    if devnull != 0:
        os.dup2(devnull, 0)
        os.close(devnull)
    sys.path[:] = snapshot
    units = build_units(discover(start, pattern, top, select))
    manifest = unit_manifest(units)
    discovered_path = list(sys.path)
    if _normal(manifest) != _normal(expected):
        # The coordinator refuses this payload; running other positions
        # would only cost time.
        positions = ()
    children = [unit.suite for unit in units]
    names = [name for name, _ in manifest]
    result = run_positions(children, positions, bin_index, names,
                           lambda name: conn.send(("begin", name)))
    conn.send(("result", result_payload(result, bin_index, manifest, discovered_path, positions)))
    conn.close()


# ---------------------------------------------------------------------------
# The coordinator
# ---------------------------------------------------------------------------


class _Interrupted(Exception):
    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


def _on_signal(signum, frame):
    raise _Interrupted(signum)


def _deferring(pending):
    """A handler that records the signal, for use while discovery imports."""
    def handler(signum, frame):
        pending.append(signum)
    return handler


def _exit_error(b, proc, current, when):
    proc.join(5)
    return LedgerError("worker-exit", "the worker exited with exit code %s %s"
                       % (proc.exitcode, when), bin=b.index, module=current.get(b.index))


def _drain(conn, b, proc, current, payloads):
    """Read every waiting message. Return True once the payload arrived."""
    while conn.poll():
        # Known limit: recv() waits for a whole message. A worker that dies
        # partway through a send, while a forked child of a test holds the
        # pipe open, leaves recv() waiting with no EOF. No module under
        # crux/scripts/tests calls os.fork outside this driver's self-test,
        # and that test's worker exits between sends.
        try:
            message = conn.recv()
        except EOFError:
            raise _exit_error(b, proc, current, "before its payload") from None
        if isinstance(message, tuple) and len(message) == 2 and message[0] == "begin":
            current[b.index] = message[1]
        elif isinstance(message, tuple) and len(message) == 2 and message[0] == "result":
            payloads[b.index] = message[1]
            return True
        else:
            raise LedgerError("malformed-payload", "an unknown message from the worker",
                              bin=b.index, module=current.get(b.index))
    return False


def _collect(running, current, payloads):
    """Receive every bin's payload into `payloads`, before any join.
    `current` maps each bin to the module its worker last began."""
    pending = {conn: (b, proc) for b, proc, conn in running}
    while pending:
        _wait_ready(list(pending) + [proc.sentinel for b, proc in pending.values()],
                    timeout=_POLL_SECONDS)
        for conn, (b, proc) in list(pending.items()):
            if _drain(conn, b, proc, current, payloads):
                del pending[conn]
                conn.close()
            elif proc.exitcode is not None:
                # The worker has exited. Every write it made is in the pipe
                # now, so read once more before refusing. The exit code is
                # the signal because a forked child of a test can inherit the
                # pipe and the sentinel and keep both open.
                if _drain(conn, b, proc, current, payloads):
                    del pending[conn]
                    conn.close()
                else:
                    raise _exit_error(b, proc, current, "before its payload")
    for b, proc, _ in running:
        proc.join()
        if proc.exitcode != 0:
            raise _exit_error(b, proc, current, "after its payload")
    return payloads


def _collect_pooled(bins, pool, cap, launch, started, conns, current, payloads):
    """Start the bins as the pool grants slots and receive every payload, before any join.

    `_collect` for a run whose bins outnumber its slots. The bins start heaviest first, each holding one
    slot until its payload arrives and its worker exits. `launch(b)` starts a worker and returns
    `(proc, reader)`. A worker that dies, or sends a malformed message, fails the run closed exactly as
    in `_collect`. At most `cap` bins run at once. Returns the `(bin, proc, reader)` of every bin.
    """
    waiting = sorted(bins, key=lambda b: (-b.weight, b.index))
    active = {}
    finished = []
    waiter = pool.waiter(math.fsum(b.weight for b in waiting))
    try:
        while waiting or active:
            while waiting and len(active) < cap:
                slot = pool.try_acquire(waiter)
                if slot is None:
                    break
                b = waiting.pop(0)
                waiter.weight = math.fsum(w.weight for w in waiting)
                try:
                    proc, reader = launch(b)
                except BaseException:
                    pool.release(slot)
                    raise
                active[reader] = (b, proc, slot)
            if not waiting:
                waiter.close()
            if not active:
                time.sleep(POOL_POLL_SECONDS)  # every slot is a peer's: ask again soon
                continue
            _wait_ready(list(active) + [proc.sentinel for _, proc, _ in active.values()],
                        timeout=POOL_POLL_SECONDS if waiting else _POLL_SECONDS)
            for conn, (b, proc, slot) in list(active.items()):
                if _drain(conn, b, proc, current, payloads):
                    pass
                elif proc.exitcode is not None:
                    # The worker has exited. Every write it made is in the pipe now, so read once more
                    # before refusing, as `_collect` does.
                    if not _drain(conn, b, proc, current, payloads):
                        raise _exit_error(b, proc, current, "before its payload")
                else:
                    continue
                conn.close()
                proc.join()
                if proc.exitcode != 0:
                    raise _exit_error(b, proc, current, "after its payload")
                pool.release(slot)
                del active[conn]
                finished.append((b, proc, conn))
    finally:
        waiter.close()
    return finished


def _signal_worker(proc, signum):
    """Send `signum` to the worker's process group. Before the worker leads
    a group, send it to the worker alone."""
    try:
        os.killpg(proc.pid, signum)
        return
    except (ProcessLookupError, PermissionError):
        pass
    if proc.exitcode is None:
        try:
            os.kill(proc.pid, signum)
        except ProcessLookupError:
            pass


def _unfinished(started, payloads):
    """The started workers that have not delivered a payload and exited 0."""
    return [(b, proc) for b, proc in started
            if proc.pid is not None and not (b.index in payloads and proc.exitcode == 0)]


def _stop(started, payloads):
    """Stop every unfinished worker with its process group: SIGTERM, then
    SIGKILL for whatever the group still holds after a grace period."""
    stopping = _unfinished(started, payloads)
    for _, proc in stopping:
        _signal_worker(proc, signal.SIGTERM)
    for _, proc in started:
        if proc.pid is not None:
            proc.join(5)
    for _, proc in stopping:
        _signal_worker(proc, signal.SIGKILL)
        proc.join()


def _report_unfinished(started, conns, current, payloads):
    """Name the module each unfinished worker was running. Read the begin
    messages still waiting in each pipe first, so the name is the latest."""
    for b, proc in _unfinished(started, payloads):
        conn = conns.get(b.index)
        try:
            while conn is not None and not conn.closed and conn.poll():
                message = conn.recv()
                if isinstance(message, tuple) and len(message) == 2 and message[0] == "begin":
                    current[b.index] = message[1]
        except Exception:
            # The report is best effort; the exit code already says the run stopped.
            pass
        module = current.get(b.index)
        sys.stderr.write("%s worker for bin %d was running %s\n"
                         % (_PREFIX, b.index, module if module else "no module yet"))


def _crux_origin():
    try:
        spec = importlib.util.find_spec("crux")
    except (ImportError, ValueError):
        return None
    if spec is None:
        return None
    if spec.origin and spec.origin != "namespace":
        return spec.origin
    locations = list(spec.submodule_search_locations or ())
    return locations[0] if locations else None


def _worker_interpreter_argv():
    """The argv prefix that starts a spawned worker: the interpreter and its flags.

    Read from the spawn context's own command line, so the check runs under the interpreter,
    flags (`-S`, `-I`, `-X`) and, through the inherited environment and cwd, the import path that
    the workers get. Discovery runs in the coordinator, and the coordinator is the same
    interpreter as its spawned workers."""
    command = multiprocessing.spawn.get_command_line()
    return command[:command.index("-c")] if "-c" in command else [sys.executable]


def _missing_modules(modules):
    """The `modules` a worker interpreter cannot import. Raises when the check cannot run."""
    proc = subprocess.run(
        [*_worker_interpreter_argv(), "-c", _PROBE_SOURCE, *modules], capture_output=True,
        text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
        timeout=_PROBE_TIMEOUT_SECONDS)
    if proc.returncode != 0:
        raise RuntimeError("the import check exited %d: %s" % (proc.returncode, proc.stderr.strip()))
    return _parse_probe(proc.stdout)


def _parse_probe(stdout):
    """The missing module names from the probe's marked line. Raises RuntimeError when the
    line is absent, because then the check did not run to its end."""
    for line in reversed(stdout.splitlines()):
        if line.startswith(_PROBE_MARKER):
            return [name for name in line[len(_PROBE_MARKER):].split(",") if name]
    raise RuntimeError("the import check printed no result line")


def _targets_own_tests(start):
    """True when `start` resolves to the directory this driver lives in."""
    return os.path.realpath(start) == os.path.dirname(os.path.realpath(__file__))


# The interpreter-check refusal has its own exit code. The evidence engine records every exit 2 as
# a failed run, because it cannot tell afterwards whether a test had started. This refusal comes
# before discovery, so it is not a failure of any test.
EXIT_INTERPRETER_REFUSED = 3


def _refuse_incapable_interpreter(args):
    """The exit-3 message when START is the plugin suite and its interpreter lacks a dependency,
    else None."""
    if not _targets_own_tests(args.start):
        return None
    try:
        missing = _missing_modules(PLUGIN_SUITE_MODULES)
    except Exception as exc:  # the check could not run: the same environment lane
        return ("the interpreter check could not run under %s: %s: %s. Run `%s`."
                % (sys.executable, type(exc).__name__, exc, WORKING_COMMAND))
    if missing:
        return ("the interpreter %s cannot import: %s. The plugin suite needs them. Run `%s`."
                % (sys.executable, ", ".join(missing), WORKING_COMMAND))
    return None


def _header(args, manifest, bins, workers, timings_note, pool=None):
    requested = args.workers if args.workers is not None else "default %d" % DEFAULT_WORKERS
    origin = _crux_origin()
    lines = [
        "python %s (%s)" % (sys.version.split()[0], sys.implementation.name),
        "executable %s" % sys.executable,
        "prefix %s" % sys.prefix,
        "crux %s" % origin if origin else "crux not importable",
        "discovered %d tests in %d units (start %s, pattern %s, top %s)"
        % (sum(len(ids) for _, ids in manifest), len(manifest), args.start, args.pattern, args.top),
        "timings %s" % timings_note,
        "workers %d (%d bins; requested %s, process_cpu_count %s)"
        % (workers, len(bins), requested, os.process_cpu_count()),
    ]
    if pool is not None:
        lines.append("pool %s (%d slots; each bin starts when it can take one)" % (pool.directory, pool.size))
    for b in bins:
        lines.append("bin %d weight %.1f: %s" % (b.index, b.weight,
                                               " ".join(manifest[p][0] for p in b.positions)))
    sys.stderr.write("".join("%s %s\n" % (_PREFIX, line) for line in lines))
    sys.stderr.flush()


def _positive(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return value


def _parse(argv):
    parser = argparse.ArgumentParser(
        prog="parallel_suite.py",
        description="Run `unittest discover` across worker processes; fail closed on any discrepancy.")
    parser.add_argument("start", nargs="?", default=None,
                        help="the start directory, as for unittest discover -s "
                             "(required unless --write-timings)")
    parser.add_argument("-p", "--pattern", default=DEFAULT_PATTERN,
                        help="the test file pattern (default %s)" % DEFAULT_PATTERN)
    parser.add_argument("-t", "--top-level-directory", dest="top", default=None,
                        help="the top-level directory of the project")
    parser.add_argument("-w", "--workers", type=_positive, default=None,
                        help="the worker count (default %d, capped by the CPUs this process may use)"
                             % DEFAULT_WORKERS)
    parser.add_argument("--select", action="append", default=[], metavar="ID",
                        help="run only the tests under this module, class or method id; repeatable. "
                             "An id that matches no discovered test is an error")
    parser.add_argument("--failed-from", dest="failed_from", default=None, metavar="RECORDS",
                        help="run only the tests that failed or errored in this --records JSONL "
                             "(a failed subtest selects its parent); with --select, only those under a selected id")
    parser.add_argument("--tier", action="append", default=[], choices=("dev", "release", "ephemeral"),
                        metavar="TIER",
                        help="run only the tests START/test-tiers.json labels with this tier (dev, release or "
                             "ephemeral); repeatable. A missing or invalid manifest, a discovered test with "
                             "no label, and a selection that keeps no test fail closed")
    parser.add_argument("--flagged", action="store_true",
                        help="run the tests the flagged list names for this Python minor; an entry whose "
                             "test skips, and an entry that selects no test, fail the run")
    parser.add_argument("--flagged-list", dest="flagged_list", default=None, metavar="PATH",
                        help="the flagged list for --flagged (default: flagged_tests.json beside the driver)")
    parser.add_argument("--staged-check", dest="staged_check", choices=("flagged", "health"), default=None,
                        help="with --shared-evidence --evidence-scope staged: run the registered staged "
                             "check of this name through the evidence engine instead of the full suite")
    parser.add_argument("--records", default=None,
                        help="write the canonical JSONL records to this path")
    parser.add_argument("--timings", default=None,
                        help="read unit weights from this file (default: suite_timings.json "
                             "beside the driver)")
    parser.add_argument("--write-timings", dest="write_timings", default=None, metavar="RECORDS",
                        help="write the timings file from a --records JSONL and exit")
    parser.add_argument("--timings-out", dest="timings_out", default=None,
                        help="the file --write-timings writes (default: the committed file)")
    parser.add_argument("--shared-evidence", action="store_true", help="reuse repository-wide evidence for matching suite inputs")
    parser.add_argument("--evidence-scope", choices=("checkout", "staged"), default="checkout")
    parser.add_argument("--source-root", default=None, help="the dev checkout that holds uv.lock and the durable evidence store (staged scope)")
    parser.add_argument("--python-minor", default=None, help="the Python minor of a staged suite run (default: the running interpreter's)")
    parser.add_argument("--retry-reason", default=os.environ.get("CRUX_TEST_RETRY_REASON"), help="reason to retry an unchanged failing check")
    evidence_mode = parser.add_mutually_exclusive_group()
    evidence_mode.add_argument("--plan-test-evidence", action="store_true", help="report evidence lookup only; never execute tests")
    evidence_mode.add_argument("--reuse-test-evidence-only", action="store_true", help="refuse missing or invalid evidence without executing tests")
    args = parser.parse_args(argv)
    if (args.plan_test_evidence or args.reuse_test_evidence_only) and not args.shared_evidence:
        parser.error("evidence planning/reuse-only requires --shared-evidence")
    if (args.plan_test_evidence or args.reuse_test_evidence_only) and args.write_timings is not None:
        parser.error("evidence planning/reuse-only cannot write timings")
    if args.staged_check and not (args.shared_evidence and args.evidence_scope == "staged"):
        parser.error("--staged-check needs --shared-evidence and --evidence-scope staged")
    if args.staged_check == "flagged" and args.flagged:
        parser.error("--staged-check flagged already runs --flagged; give one of them")
    if args.tier and (args.flagged or args.write_timings is not None):
        parser.error("--tier chooses its own selection; do not combine it with --flagged or --write-timings")
    if args.tier and args.shared_evidence and (args.tier != ["release"] or args.select or args.failed_from
                                               or args.evidence_scope != "checkout" or args.staged_check):
        parser.error("--shared-evidence takes only --tier release, alone, for the registered release-tier "
                     "declaration of a checkout suite")
    if args.flagged and args.select:
        parser.error("--flagged chooses its own selection; do not combine it with --select")
    if args.failed_from and (args.flagged or args.shared_evidence or args.write_timings is not None):
        parser.error("--failed-from chooses its own selection; do not combine it with --flagged, "
                     "--shared-evidence or --write-timings")
    if args.write_timings is None and args.start is None:
        parser.error("the following arguments are required: start")
    return args


def _write_timings_main(args):
    out = args.timings_out or DEFAULT_TIMINGS
    try:
        count = write_timings(args.write_timings, out)
    except (LedgerError, OSError) as err:
        sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
        return 2
    sys.stderr.write("%s wrote %d timings entries to %s\n" % (_PREFIX, count, out))
    return 0


def _scripts_on_path():
    scripts = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)


def tier_selection(start, pattern, top, tiers, select=()):
    """The ids that run under ``--tier``: the discovered tests whose manifest tier is in ``tiers``.

    Reads ``start/test-tiers.json`` through ``test_tiers.load``. Keeps a loader-failure id so an
    import error still runs and fails. Raises ``LedgerError`` when the manifest is missing or invalid,
    when a discovered test's module has no label, when a ``select`` id matches no discovered test, and
    when nothing is left. The result names modules or classes when every discovered test under one is
    kept, and methods otherwise.
    """
    _scripts_on_path()
    import test_tiers
    try:
        data = test_tiers.load(start)
    except test_tiers.ManifestError as err:
        raise LedgerError("tier", str(err))
    ids = _discovered_ids(start, pattern, top)
    missing = [item for item in dict.fromkeys(select) if not any(_selected(i, item) for i in ids)]
    if missing:
        error = LedgerError("selection", "selection id not found: " + ", ".join(missing))
        error.missing = missing
        raise error
    wanted = set(tiers)
    kept, unlabelled = [], []
    for test_id in ids:
        if test_id.startswith(test_tiers.FAILED_TEST_PREFIX):
            kept.append(test_id)
            continue
        tier = test_tiers.tier_of_id(data, test_id)
        if tier is None:
            unlabelled.append(test_id)
        elif tier in wanted and (not select or any(_selected(test_id, item) for item in select)):
            kept.append(test_id)
    if unlabelled:
        raise LedgerError("tier", "discovered test has no tier label in %s: %s"
                          % (os.path.join(start, test_tiers.MANIFEST_NAME), ", ".join(unlabelled[:5])))
    if not any(not i.startswith(test_tiers.FAILED_TEST_PREFIX) for i in kept):
        raise LedgerError("tier", "the tier selection (%s) keeps no test" % ", ".join(sorted(wanted)))
    return _compress(ids, kept)


_DISCOVER_SOURCE = (
    "import json, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import parallel_suite as p\n"
    "top = sys.argv[4] or None\n"
    "ids = [leaf.id() for leaf in p._leaves(p._ModuleLoader().discover(sys.argv[2], sys.argv[3], top))]\n"
    "with open(sys.argv[5], 'w', encoding='utf-8') as out:\n"
    "    json.dump(ids, out)\n"
)


def _discovered_ids(start, pattern, top):
    """The discovered test ids, from a child interpreter.

    Discovery runs test-module code, and that code can change ``sys.path`` and module state. The
    coordinator discovers once more for its own manifest, and each worker compares its ``sys.path``
    and manifest with that discovery. A second discovery in the coordinator's process would add its
    own changes and fail that comparison, so the tier selection discovers in a child of the same
    interpreter, flags and working directory as the workers.
    """
    with tempfile.TemporaryDirectory() as scratch:
        out = os.path.join(scratch, "ids.json")
        proc = subprocess.run(
            [*_worker_interpreter_argv(), "-c", _DISCOVER_SOURCE, os.path.dirname(os.path.abspath(__file__)),
             start, pattern, top or "", out],
            capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
        if proc.returncode != 0 or not os.path.isfile(out):
            raise LedgerError("tier", "tier discovery exited %d: %s" % (proc.returncode, proc.stderr.strip()[-2000:]))
        with open(out, encoding="utf-8") as handle:
            return json.load(handle)


def _compress(all_ids, kept):
    """``kept`` as the fewest module, class and method ids that select exactly ``kept`` among ``all_ids``."""
    keep = set(kept)
    out = []
    for test_id in kept:
        if test_id.startswith("unittest.loader."):
            out.append(test_id)
    ordinary = [i for i in all_ids if not i.startswith("unittest.loader.")]
    done = set()
    for test_id in ordinary:
        if test_id not in keep or test_id in done:
            continue
        parts = test_id.split(".")
        for size in (1, 2):
            prefix = ".".join(parts[:size])
            under = [i for i in ordinary if i == prefix or i.startswith(prefix + ".")]
            if size < len(parts) and all(i in keep for i in under):
                out.append(prefix)
                done.update(under)
                break
        else:
            out.append(test_id)
            done.add(test_id)
    return out


def _flagged_plan(args):
    """``(entries, ids)`` for the running minor, or raises `FlaggedError` with the list's problems."""
    _scripts_on_path()
    import flagged_tests
    path = args.flagged_list or os.path.join(os.path.dirname(os.path.abspath(__file__)), "flagged_tests.json")
    entries = flagged_tests.load(path)
    problems = flagged_tests.validate(entries)
    if problems:
        raise flagged_tests.FlaggedError("the flagged list is invalid: " + "; ".join(problems))
    minor = args.python_minor or "%d.%d" % sys.version_info[:2]
    return minor, flagged_tests.applicable(entries, minor), flagged_tests.selection(entries, minor)


def _flagged_skips(summary):
    """The `flagged test skipped` lines for every skipped record of a flagged run."""
    seen, lines = set(), []
    for record in summary.records:
        if record["outcome"] == "skip" and (record["id"], record["reason"]) not in seen:
            seen.add((record["id"], record["reason"]))
            lines.append("flagged test skipped: %s (%s)" % (record["id"], record["reason"] or "no reason given"))
    return lines


# The full-suite lock. `tools/test-suite.py` holds `<git-common-dir>/crux/full-suite.lock` for a full run and
# records its holder as one JSON line (`pid`, `head`, `started_at`, `output_dir`); the cycle writer defers its
# record commit while the lock is held. An executing registered checkout-suite run holds the same lock, so a
# writer commit cannot move HEAD under it. The path and the holder format must stay what test-suite.py writes.
# test-suite.py hands a child run its descriptor and names it in FULL_SUITE_LOCK_FD_ENV; the child then
# holds nothing of its own.
FULL_SUITE_LOCK_NAME = "full-suite.lock"
FULL_SUITE_LOCK_FD_ENV = "CRUX_FULL_SUITE_LOCK_FD"


class _LockHeld(Exception):
    """Another run holds the full-suite lock; the message names the holder."""


def _lock_directory():
    """`<git-common-dir>/crux`, or None when this is not a git work tree."""
    try:
        done = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                              capture_output=True, text=True)
    except OSError:
        return None
    return os.path.join(done.stdout.strip(), "crux") if done.returncode == 0 and done.stdout.strip() else None


def _inherits_the_lock(path):
    """True when FULL_SUITE_LOCK_FD_ENV names an open descriptor of the lock file at `path`."""
    value = os.environ.get(FULL_SUITE_LOCK_FD_ENV)
    if not value or not value.isdigit():
        return False
    try:
        held, lock = os.fstat(int(value)), os.stat(path)
    except OSError:
        return False
    return (held.st_dev, held.st_ino) == (lock.st_dev, lock.st_ino)


def _head():
    done = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


@contextlib.contextmanager
def _full_suite_lock():
    """Hold the full-suite lock for the block, or raise `_LockHeld` naming the holder.

    Holds nothing when this run inherited the lock from `tools/test-suite.py` or when the directory is not a
    git work tree (the evidence engine fails closed there itself).
    """
    directory = _lock_directory()
    if directory is None:
        yield
        return
    path = os.path.join(directory, FULL_SUITE_LOCK_NAME)
    if _inherits_the_lock(path):
        yield
        return
    for candidate in (directory, path):
        if os.path.islink(candidate):
            raise _LockHeld("%s is a symlink; remove it so the run never writes through it" % candidate)
    with contextlib.suppress(FileExistsError):
        os.mkdir(directory, 0o700)
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError as err:
        raise _LockHeld("cannot open %s: %s" % (path, err))
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            holder = os.pread(fd, 4096, 0).decode(errors="replace").strip()
            try:
                info = json.loads(holder)
                detail = " ".join("%s=%s" % (key, info.get(key)) for key in ("pid", "head", "started_at", "output_dir"))
            except (ValueError, AttributeError):
                detail = "holder unrecorded"
            raise _LockHeld("lock held: %s; %s" % (path, detail))
        os.ftruncate(fd, 0)
        started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        os.pwrite(fd, (json.dumps({"pid": os.getpid(), "head": _head(), "started_at": started,
                                   "output_dir": None}) + "\n").encode(), 0)
        yield
    finally:
        os.close(fd)


def _registered_checkout_run(args):
    """True when `args` name an executing run of a registered checkout suite (not a plan or a reuse-only check)."""
    if args.evidence_scope != "checkout" or args.staged_check:
        return False
    if args.plan_test_evidence or args.reuse_test_evidence_only:
        return False
    try:
        from suite_evidence import declaration_for
        _, registered = declaration_for(args.evidence_scope, args.start, args.pattern, args.top, os.getcwd())
    except Exception:  # a declaration that cannot be built fails closed in run_shared, with its own message
        return False
    return registered


def _run(argv=None):
    args = _parse(argv)
    if args.write_timings is not None:
        return _write_timings_main(args)
    if args.failed_from:
        try:
            failed = failed_ids_from_records(args.failed_from)
        except LedgerError as err:
            sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
            return 2
        if args.select:
            failed = [i for i in failed if any(_selected(i, item) for item in args.select)]
        if not failed:
            sys.stderr.write("%s no failed or errored test to rerun in %s; nothing to run\n"
                             % (_PREFIX, args.failed_from))
            return 0
        args.select = failed
    if args.tier and not args.shared_evidence:
        try:
            args.select = tier_selection(args.start, args.pattern, args.top, args.tier, tuple(args.select))
        except LedgerError as err:
            sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
            return 2
    if args.shared_evidence:
        _scripts_on_path()
        from suite_evidence import run_shared
        from test_evidence import EvidenceError
        try:
            if _registered_checkout_run(args):
                with _full_suite_lock():
                    return run_shared(args)
            return run_shared(args)
        except _LockHeld as err:
            sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
            return 2
        except (EvidenceError, OSError) as err:
            sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
            return 2
    if args.flagged:
        try:
            minor, flagged_entries, flagged_ids = _flagged_plan(args)
        except Exception as err:  # FlaggedError and a missing `flagged_tests` module alike fail closed
            sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
            return 2
        if not flagged_ids:
            sys.stderr.write("%s no flagged entry applies to Python %s; nothing to run\n" % (_PREFIX, minor))
            return 0
        args.select = list(flagged_ids)
    try:
        timings, timings_note = load_timings(args.timings)
    except LedgerError as err:
        sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
        return 2
    refusal = _refuse_incapable_interpreter(args)
    if refusal:
        sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, refusal))
        return EXIT_INTERPRETER_REFUSED
    try:
        pool = SlotPool.from_environ()
    except PoolError as err:
        sys.stderr.write("%s FAILED CLOSED: %s names no usable pool: %s\n" % (_PREFIX, POOL_ENV, err))
        return 2
    records_path = os.path.abspath(args.records) if args.records else None
    if not sys.flags.safe_path:
        # The `python -m unittest` shape: the working directory first, in
        # place of this script's directory. Under -P neither is on the path.
        sys.path[0] = os.getcwd()
    snapshot = list(sys.path)
    started, conns, current, payloads = [], {}, {}, {}
    saved = {}
    try:
        pending = []
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            if signal.getsignal(signum) is not signal.SIG_IGN:
                saved[signum] = signal.signal(signum, _deferring(pending))
        units = build_units(discover(args.start, args.pattern, args.top, tuple(args.select)))
        manifest = unit_manifest(units)
        # Install the raising handler before reading `pending`, so a signal
        # between the two either is already recorded or raises.
        for signum in saved:
            signal.signal(signum, _on_signal)
        if pending:
            raise _Interrupted(pending[0])
        discovered_path = list(sys.path)
        if pool is None:
            workers = effective_workers(args.workers)
            bins = assign_bins(units, workers, AFFINITY, timings)
        else:
            # The pool, not the CPU count, bounds the run. `--workers` still caps the bins that run at once.
            workers = min(args.workers, pool.size) if args.workers else pool.size
            bins = assign_bins(units, pooled_bin_count(units, timings, pool.size), AFFINITY, timings)
        _header(args, manifest, bins, workers, timings_note, pool)
        if not any(ids for _, ids in manifest):
            reconcile(manifest, bins, {}, discovered_path)
        began = time.perf_counter()
        # spawn, not fork: each worker starts from an interpreter that has
        # imported no test module, as a serial run does, and repeats discovery
        # itself. fork would copy the coordinator's discovery imports, and fork
        # is the Linux default before 3.14.
        context = multiprocessing.get_context("spawn")

        def launch(b):
            reader, writer = context.Pipe(duplex=False)
            proc = context.Process(
                target=_worker_main, name="parallel_suite-bin-%d" % b.index, daemon=False,
                args=(writer, b.index, b.positions, args.start, args.pattern, args.top,
                      snapshot, manifest, tuple(args.select)))
            started.append((b, proc))
            conns[b.index] = reader
            proc.start()
            writer.close()
            return proc, reader

        if pool is None:
            running = []
            for b in sorted(bins, key=lambda b: (-b.weight, b.index)):
                proc, reader = launch(b)
                running.append((b, proc, reader))
            _collect(running, current, payloads)
        else:
            _collect_pooled(bins, pool, workers, launch, started, conns, current, payloads)
        summary = reconcile(manifest, bins, payloads, discovered_path)
        elapsed = time.perf_counter() - began
    except LedgerError as err:
        if args.flagged and err.branch == "selection":
            # A flagged entry that names no discovered test is stale; say which entries, and fail the check.
            for missing in err.missing:
                sys.stderr.write("%s flagged entry selects no test: %s\n" % (_PREFIX, missing))
            return 1
        sys.stderr.write("%s FAILED CLOSED: %s\n" % (_PREFIX, err))
        _report_unfinished(started, conns, current, payloads)
        return 2
    except _Interrupted as interrupted:
        sys.stderr.write("%s interrupted by signal %d; stopping every unfinished worker\n"
                         % (_PREFIX, interrupted.signum))
        _report_unfinished(started, conns, current, payloads)
        return 128 + interrupted.signum
    except Exception:
        traceback.print_exc()
        sys.stderr.write("%s FAILED CLOSED: the driver raised\n" % _PREFIX)
        return 2
    finally:
        for signum in saved:
            signal.signal(signum, signal.SIG_IGN)
        _stop(started, payloads)
        if pool is not None:
            pool.release_all()
        for signum, handler in saved.items():
            signal.signal(signum, handler)
    if records_path:
        merged = CanonicalRecorder()
        merged.records = summary.records
        merged.write_jsonl(records_path)
    sys.stderr.write(format_summary(summary, elapsed))
    sys.stderr.flush()
    code = exit_code(summary)
    if args.flagged:
        skips = _flagged_skips(summary)
        for line in skips:
            sys.stderr.write("%s %s\n" % (_PREFIX, line))
        if skips:
            sys.stderr.flush()
            return code or 1
    return code


# The variables a test process must not inherit: each one routes a call to a live model or search
# service. `CRUX_HOME` is replaced, not removed, because the env reader falls back to `~/.crux`.
LIVE_ENVIRONMENT_NAMES = ("OPENROUTER_API_KEY", "PERPLEXITY_API_KEY", "CRUX_ALLOW_LIVE")


@contextlib.contextmanager
def isolated_live_environment(own_uv_cache=False):
    """Give the processes started inside the block an empty `CRUX_HOME` and no live-model variable.

    `own_uv_cache` also gives them a fresh `UV_CACHE_DIR`, unless the caller already set one.
    """
    names = (*LIVE_ENVIRONMENT_NAMES, "CRUX_HOME", "UV_CACHE_DIR")
    saved = {name: os.environ.get(name) for name in names}
    home = tempfile.mkdtemp(prefix="crux-suite-home-")
    cache = tempfile.mkdtemp(prefix="crux-suite-uv-cache-") if own_uv_cache and saved["UV_CACHE_DIR"] is None else None
    try:
        for name in LIVE_ENVIRONMENT_NAMES:
            os.environ.pop(name, None)
        os.environ["CRUX_HOME"] = home
        if cache:
            os.environ["UV_CACHE_DIR"] = cache
        yield home
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(home, ignore_errors=True)
        if cache:
            shutil.rmtree(cache, ignore_errors=True)


def main(argv=None):
    # A run that names its Python minor is one of several suites that may run at once, one per minor.
    # Each owns its uv cache: a shared one lets a minor rebuild a script environment while another runs it.
    minor_run = bool(_parse(argv).python_minor)
    with isolated_live_environment(own_uv_cache=minor_run):
        return _run(argv)


if __name__ == "__main__":
    sys.exit(main())
