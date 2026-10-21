"""Self-tests for the shared slot pool in `parallel_suite.py`.

`tools/release.py verify` runs a preflight and `sync.sh --dry-run` side by side, and each starts
suite drivers of its own. One directory of slot files, named by `CRUX_GATE_POOL`, holds the host's
worker budget for all of them. This module covers the pool (slot files held with `flock`, so a dead
holder frees its slot), the waiter records that hand a freed slot to the longest remaining weight, and a
pooled driver run: bins start as slots free up, so a slot a finished peer returns goes to a driver that
is still running.

Every tree and every pool is synthetic and lives under a temporary directory. The tests run drivers as
subprocesses over tiny trees and wait on files, never on elapsed time: a deadline only bounds a hung run.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRIVER = HERE / "parallel_suite.py"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import parallel_suite as ps  # noqa: E402

DEADLINE = 120


def _until(predicate, what, limit=DEADLINE):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting for " + what)


class _PoolCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.children = []
        self.addCleanup(self._reap)

    def _reap(self):
        for child in self.children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    child.kill()
            child.wait()
            if child.stdout is not None:
                child.stdout.close()

    def pool(self, size, **kw):
        directory = self.root / f"pool{len(list(self.root.glob('pool*')))}"
        ps.SlotPool.create(size, directory)
        return ps.SlotPool(directory, **kw)

    def holder(self, pool_dir, count, hold="slots"):
        """A process that holds `count` slots (or a waiter record) of the pool until it is killed."""
        code = textwrap.dedent(f"""
            import sys, time
            sys.path.insert(0, {str(HERE)!r})
            import parallel_suite as ps
            pool = ps.SlotPool({str(pool_dir)!r})
            waiter = pool.waiter(500.0) if {hold!r} == "waiter" else None
            if waiter is not None:
                waiter.refresh()
            got = [pool.try_acquire(waiter) for _ in range({count})]
            print(got, flush=True)
            time.sleep(600)
        """)
        child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, start_new_session=True)
        self.children.append(child)
        child.stdout.readline()
        return child


class SlotPoolTests(_PoolCase):
    def test_slots_are_distinct_until_the_pool_is_empty_and_return_on_release(self):
        pool = self.pool(3)
        taken = [pool.try_acquire() for _ in range(3)]
        self.assertEqual(sorted(taken), [0, 1, 2])
        self.assertIsNone(pool.try_acquire(), "a fourth acquire on a pool of three")
        pool.release(taken[1])
        self.assertEqual(pool.try_acquire(), taken[1])

    def test_two_handles_on_one_directory_contend(self):
        first = self.pool(1)
        second = ps.SlotPool(first.directory)
        self.assertEqual(first.try_acquire(), 0)
        self.assertIsNone(second.try_acquire(), "a second handle took the first handle's slot")
        first.release(0)
        self.assertEqual(second.try_acquire(), 0)

    def test_a_killed_holder_frees_its_slots(self):
        pool = self.pool(2)
        holder = self.holder(pool.directory, 2)
        self.assertIsNone(pool.try_acquire(), "the control: both slots are held while the holder lives")
        os.killpg(holder.pid, signal.SIGKILL)
        holder.wait()
        self.assertIsNotNone(_until(pool.try_acquire, "a freed slot"), "a dead holder kept its slot")

    def test_release_all_returns_every_held_slot(self):
        pool = self.pool(2)
        pool.try_acquire(), pool.try_acquire()
        pool.release_all()
        self.assertEqual(sorted([pool.try_acquire(), pool.try_acquire()]), [0, 1])


class PoolEnvironmentTests(_PoolCase):
    def test_no_variable_means_no_pool(self):
        self.assertIsNone(ps.SlotPool.from_environ({}))

    def test_the_variable_opens_the_pool_it_names(self):
        pool = self.pool(4)
        opened = ps.SlotPool.from_environ({ps.POOL_ENV: str(pool.directory)})
        self.assertEqual((opened.size, opened.directory), (4, pool.directory))

    def test_a_variable_naming_nothing_usable_is_refused_not_ignored(self):
        good = self.pool(2)
        ps.SlotPool.from_environ({ps.POOL_ENV: str(good.directory)})  # the control: this one opens
        missing_slot = self.pool(2)
        (Path(missing_slot.directory) / "slot-0001").unlink()
        zero = self.pool(2)
        (Path(zero.directory) / "size").write_text("0\n")
        garbled = self.pool(2)
        (Path(garbled.directory) / "size").write_text("two\n")
        for what, path in (("a missing directory", self.root / "absent"), ("a missing slot file", missing_slot.directory),
                           ("a size of zero", zero.directory), ("an unreadable size", garbled.directory)):
            with self.subTest(what):
                with self.assertRaises(ps.PoolError):
                    ps.SlotPool.from_environ({ps.POOL_ENV: str(path)})


class WaiterPriorityTests(_PoolCase):
    def setUp(self):
        super().setUp()
        self.now = [1000.0]
        self.pool_ = self.pool(2, clock=lambda: self.now[0])

    def test_a_heavier_waiter_gets_the_slot_before_a_lighter_one(self):
        heavy, light = self.pool_.waiter(900.0), self.pool_.waiter(30.0)
        heavy.refresh()
        self.assertIsNone(self.pool_.try_acquire(light), "a light waiter took a slot while a heavier one waited")
        self.assertIsNotNone(self.pool_.try_acquire(heavy))

    def test_a_lighter_waiter_proceeds_once_the_heavier_one_has_nothing_left_to_start(self):
        heavy, light = self.pool_.waiter(900.0), self.pool_.waiter(30.0)
        heavy.refresh()
        self.assertIsNone(self.pool_.try_acquire(light))
        heavy.close()
        self.assertIsNotNone(self.pool_.try_acquire(light))

    def test_a_waiter_that_stopped_refreshing_is_ignored(self):
        heavy, light = self.pool_.waiter(900.0), self.pool_.waiter(30.0)
        heavy.refresh()
        self.assertIsNone(self.pool_.try_acquire(light), "the control: a fresh heavy waiter blocks")
        self.now[0] += ps.WAITER_STALE_SECONDS + 1
        self.assertIsNotNone(self.pool_.try_acquire(light), "a waiter that stopped polling still blocked a slot")

    def test_a_dead_waiters_record_is_removed_and_does_not_block(self):
        light = self.pool_.waiter(30.0)
        dead = self.holder(self.pool_.directory, 0, hold="waiter")
        self.assertIsNone(self.pool_.try_acquire(light), "the control: a live heavy waiter in another process blocks")
        os.killpg(dead.pid, signal.SIGKILL)
        dead.wait()
        self.assertIsNotNone(_until(lambda: self.pool_.try_acquire(light), "the dead waiter's record to stop blocking"))
        self.assertEqual(sorted(p.name for p in (Path(self.pool_.directory) / "waiters").glob("*")), [os.path.basename(light.path)])

    def test_equal_weights_pick_one_winner(self):
        first, second = self.pool_.waiter(50.0), self.pool_.waiter(50.0)
        first.refresh(), second.refresh()
        winners = [w for w in (first, second) if self.pool_.try_acquire(w) is not None]
        self.assertEqual(len(winners), 1, "two equal waiters both took a slot, or neither did")


def _tree(root: Path, modules: dict[str, str]) -> Path:
    tree = root / "tree"
    tree.mkdir(exist_ok=True)
    for name, body in modules.items():
        (tree / f"{name}.py").write_text(textwrap.dedent(body))
    return tree


def _timings(path: Path, weights: dict[str, float]) -> Path:
    path.write_text(json.dumps(weights))
    return path


class PooledDriverTests(_PoolCase):
    def _launch(self, tree, timings, pool, *extra, name="driver"):
        env = {**os.environ, ps.POOL_ENV: str(pool.directory)}
        child = subprocess.Popen([sys.executable, str(DRIVER), ".", "--timings", str(timings), *extra], cwd=tree, env=env,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 start_new_session=True)
        self.children.append(child)
        return child

    def _finish(self, child):
        out, err = child.communicate(timeout=DEADLINE)
        return child.returncode, out, err

    def test_a_pooled_run_reports_what_the_serial_run_reports_and_frees_every_slot(self):
        modules = {
            "test_a": """
                import unittest
                class A(unittest.TestCase):
                    def test_ok(self): pass
                    def test_skip(self): self.skipTest("why")
            """,
            "test_b": """
                import unittest
                class B(unittest.TestCase):
                    def test_bad(self): self.assertEqual(1, 2)
            """,
            "test_c": """
                import unittest
                class C(unittest.TestCase):
                    def test_ok(self): pass
            """,
        }
        tree = _tree(self.root, modules)
        timings = _timings(self.root / "t.json", {"test_a.A": 100, "test_b.B": 100, "test_c.C": 100})
        pool = self.pool(2)
        serial = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "."], cwd=tree, capture_output=True,
                                text=True, timeout=DEADLINE)
        code, _, err = self._finish(self._launch(tree, timings, pool))
        self.assertEqual(code, 1)
        self.assertEqual(code, serial.returncode)
        for line in ("Ran 4 tests", "FAILED (failures=1, skipped=1)"):
            self.assertIn(line, err)
            self.assertIn(line, serial.stderr)
        self.assertIn("pool %s" % pool.directory, err, "the header must name the pool, or this was an unpooled run")
        self.assertEqual(sorted(n for n in (pool.try_acquire() for _ in range(3)) if n is not None), [0, 1],
                         "a finished pooled run kept a slot")

    def test_the_run_never_holds_more_slots_than_the_pool_has_and_does_use_them(self):
        modules = {f"test_m{i}": f"""
            import os, time, unittest
            LOG = os.path.join(os.path.dirname(__file__), "events.log")
            class M{i}(unittest.TestCase):
                def test_it(self):
                    with open(LOG, "a") as f: f.write("start\\n")
                    time.sleep(0.6)
                    with open(LOG, "a") as f: f.write("end\\n")
        """ for i in range(5)}
        tree = _tree(self.root, modules)
        timings = _timings(self.root / "t.json", {f"test_m{i}.M{i}": 200 for i in range(5)})
        pool = self.pool(2)
        code, _, err = self._finish(self._launch(tree, timings, pool))
        self.assertEqual(code, 0, err)
        peak = running = 0
        for line in (tree / "events.log").read_text().split():
            running += 1 if line == "start" else -1
            peak = max(peak, running)
        self.assertEqual(peak, 2, "five bins on a pool of two should overlap by exactly two")
        self.assertIn("5 bins", err)

    def test_a_slot_a_finished_peer_returns_goes_to_the_driver_still_running(self):
        gate_a = self.root / "gate-a"
        a_tree = self.root / "a"
        a_tree.mkdir()
        a = _tree(a_tree, {"test_a": f"""
            import os, time, unittest
            class A(unittest.TestCase):
                def test_it(self):
                    open({str(self.root / "a-started")!r}, "w").close()
                    end = time.monotonic() + 100
                    while not os.path.exists({str(gate_a)!r}) and time.monotonic() < end: time.sleep(0.05)
        """})
        b_tree = self.root / "b"
        b_tree.mkdir()
        b = _tree(b_tree, {f"test_b{i}": f"""
            import os, time, unittest
            class B{i}(unittest.TestCase):
                def test_it(self):
                    open({str(self.root / f"b{i}-started")!r}, "w").close()
                    end = time.monotonic() + 100
                    while not os.path.exists({str(self.root / "gate-b")!r}) and time.monotonic() < end: time.sleep(0.05)
        """ for i in (0, 1)})
        ta = _timings(self.root / "ta.json", {"test_a.A": 100})
        tb = _timings(self.root / "tb.json", {"test_b0.B0": 100, "test_b1.B1": 100})
        pool = self.pool(2)
        da = self._launch(a, ta, pool)
        _until((self.root / "a-started").exists, "driver A to hold a slot")
        db = self._launch(b, tb, pool)
        _until(lambda: (self.root / "b0-started").exists() or (self.root / "b1-started").exists(),
               "driver B to start a bin on the one free slot")
        time.sleep(2.0)
        started = [(self.root / f"b{i}-started").exists() for i in (0, 1)]
        self.assertEqual(sum(started), 1, "driver B ran both bins while A held a slot of two")
        gate_a.touch()  # A finishes and returns its slot
        _until(lambda: all((self.root / f"b{i}-started").exists() for i in (0, 1)),
               "the slot A returned to reach driver B's second bin")
        (self.root / "gate-b").touch()
        self.assertEqual(self._finish(da)[0], 0)
        self.assertEqual(self._finish(db)[0], 0)

    def test_workers_caps_the_pooled_bins_that_run_at_once(self):
        modules = {f"test_m{i}": f"""
            import os, time, unittest
            LOG = os.path.join(os.path.dirname(__file__), "events.log")
            class M{i}(unittest.TestCase):
                def test_it(self):
                    with open(LOG, "a") as f: f.write("start\\n")
                    time.sleep(0.4)
                    with open(LOG, "a") as f: f.write("end\\n")
        """ for i in range(4)}
        tree = _tree(self.root, modules)
        timings = _timings(self.root / "t.json", {f"test_m{i}.M{i}": 200 for i in range(4)})
        pool = self.pool(4)
        code, _, err = self._finish(self._launch(tree, timings, pool, "--workers", "1"))
        self.assertEqual(code, 0, err)
        peak = running = 0
        for line in (tree / "events.log").read_text().split():
            running += 1 if line == "start" else -1
            peak = max(peak, running)
        self.assertEqual(peak, 1, "--workers 1 must hold a pooled driver to one bin at a time")

    def test_a_test_under_the_pooled_driver_does_not_see_the_pool(self):
        tree = _tree(self.root, {"test_env": f"""
            import os, unittest
            class E(unittest.TestCase):
                def test_it(self):
                    open({str(self.root / "seen")!r}, "w").write(repr(os.environ.get("CRUX_GATE_POOL")))
        """})
        timings = _timings(self.root / "t.json", {"test_env.E": 1})
        pool = self.pool(1)
        code, _, err = self._finish(self._launch(tree, timings, pool))
        self.assertEqual(code, 0, err)
        self.assertIn("pool %s" % pool.directory, err, "the control: the driver itself ran pooled")
        self.assertEqual((self.root / "seen").read_text(), "None",
                         "a test inherited the pool, so a nested driver would draw on the parent's budget")

    def test_a_variable_that_names_no_pool_stops_the_driver_closed(self):
        tree = _tree(self.root, {"test_ok": """
            import unittest
            class T(unittest.TestCase):
                def test_it(self): pass
        """})
        timings = _timings(self.root / "t.json", {"test_ok.T": 1})
        good = self.pool(1)
        self.assertEqual(self._finish(self._launch(tree, timings, good))[0], 0, "the control: a real pool runs")
        env = {**os.environ, ps.POOL_ENV: str(self.root / "no-such-pool")}
        run = subprocess.run([sys.executable, str(DRIVER), ".", "--timings", str(timings)], cwd=tree, env=env,
                             capture_output=True, text=True, timeout=DEADLINE)
        self.assertEqual(run.returncode, 2)
        self.assertIn("FAILED CLOSED", run.stderr)
        self.assertIn("no-such-pool", run.stderr)
        self.assertNotIn("Ran 1 test", run.stderr, "the driver ran tests without the budget it was told to use")

    def test_a_signalled_pooled_driver_returns_its_slots(self):
        gate = self.root / "never"
        tree = _tree(self.root, {f"test_h{i}": f"""
            import os, time, unittest
            class H{i}(unittest.TestCase):
                def test_it(self):
                    open({str(self.root / f"h{i}-started")!r}, "w").close()
                    end = time.monotonic() + 100
                    while not os.path.exists({str(gate)!r}) and time.monotonic() < end: time.sleep(0.05)
        """ for i in (0, 1)})
        timings = _timings(self.root / "t.json", {"test_h0.H0": 100, "test_h1.H1": 100})
        pool = self.pool(2)
        driver = self._launch(tree, timings, pool)
        _until(lambda: (self.root / "h0-started").exists() and (self.root / "h1-started").exists(), "both bins to run")
        self.assertIsNone(pool.try_acquire(), "the control: the running driver holds both slots")
        os.killpg(driver.pid, signal.SIGTERM)
        code, _, err = self._finish(driver)
        self.assertEqual(code, 128 + signal.SIGTERM, err)
        got = _until(lambda: pool.try_acquire() is not None and pool.try_acquire() is not None,
                     "both slots back after the signal")
        self.assertTrue(got)


class BinCountTests(unittest.TestCase):
    def _units(self, count):
        return [ps.Unit("m%d" % i, "m%d.C" % i, ("t",), None, "m%d.C" % i) for i in range(count)]

    def test_a_pool_cuts_a_heavy_suite_into_bins_of_about_the_target_weight(self):
        units = self._units(100)
        timings = {"m%d.C" % i: 100.0 for i in range(100)}
        count = ps.pooled_bin_count(units, timings, pool_size=10)
        self.assertEqual(count, 84)  # ceil(10000 / POOL_BIN_SECONDS)

    def test_a_light_suite_gets_at_least_one_bin_per_slot_but_never_more_than_it_has_tasks(self):
        self.assertEqual(ps.pooled_bin_count(self._units(100), {}, pool_size=10), 10)
        self.assertEqual(ps.pooled_bin_count(self._units(3), {"m0.C": 1000.0}, pool_size=10), 3)


if __name__ == "__main__":
    unittest.main()
