"""`_timing.assert_grows_linearly` tells linear from quadratic growth without reading a clock.

The cases feed it synthetic durations, so the verdict is the same on a loaded host and an idle one.
"""
import unittest

import _timing


def grows(factor_of_n):
    """A `seconds(size)` whose cost is `cost(size)` in synthetic units (no clock read)."""
    return lambda cost: (lambda size: cost(size) / 1e5)


class GrowthBoundTests(unittest.TestCase):
    N = 30_000

    def check(self, cost):
        _timing.assert_grows_linearly(self, grows(8)(cost), self.N, "synthetic work", attempts=1)

    def test_exact_linear_and_quadratic_work(self):
        self.check(lambda size: size)
        with self.assertRaises(AssertionError):
            self.check(lambda size: size * size / 4000)

    def test_linear_work_that_ran_three_and_a_half_times_slower_at_the_large_size_passes(self):
        # The loaded-host observation that failed the old bound: 29 times for work that should grow 8 times.
        self.check(lambda size: size * 3.6 if size == self.N else size)

    def test_quadratic_work_with_a_noisy_small_run_still_fails(self):
        with self.assertRaises(AssertionError):
            self.check(lambda size: size * size / 4000 * (0.9 if size == self.N else 1.0))


if __name__ == "__main__":
    unittest.main()
