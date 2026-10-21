"""Cycle timing is a pure function of the history and an explicit now."""
import copy
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cycle_timing import cycle_timing

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
PHASES = {
    'dev': ['plan', 'build', 'test', 'review', 'reflect'],
    'iterate': ['plan', 'build', 'test', 'review', 'reflect'],
    'refactor': ['plan', 'build', 'test', 'review', 'reflect'],
    'quick-fix': ['build', 'test', 'review', 'reflect'],
    'release': ['plan', 'release', 'reflect'],
}


def at(seconds):
    return (T0 + timedelta(seconds=seconds)).isoformat()


def doc(kind, rows, status='active'):
    """rows: (seconds, action, pass, phase[, recorded status])."""
    history = []
    for row in rows:
        entry = {'at': at(row[0]), 'action': row[1], 'pass': row[2], 'phase': row[3]}
        if len(row) > 4:
            entry['status'] = row[4]
        history.append(entry)
    first = PHASES[kind][0]
    return {'id': 'CYC-0001', 'type': kind, 'status': status, 'created_at': at(0), 'pass': 1, 'phase': first, 'history': history}


def seg(result):
    return [(s['pass'], s['phase'], s['active_seconds'], s['paused_seconds']) for s in result['segments']]


class TimingTests(unittest.TestCase):
    def test_every_type_elapsed_advances_with_now(self):
        for kind, phases in PHASES.items():
            with self.subTest(kind=kind):
                d = doc(kind, [(0, 'created', 1, phases[0], 'active'), (100, 'advance', 1, phases[1], 'active')])
                a = cycle_timing(d, T0 + timedelta(seconds=160))
                b = cycle_timing(d, T0 + timedelta(seconds=400))
                self.assertEqual((a['elapsed_seconds'], b['elapsed_seconds']), (160, 400))
                self.assertEqual(a['paused_seconds'], 0)
                self.assertEqual(a['basis'], 'recorded')
                self.assertEqual(a['started_at'], at(0))
                self.assertIsNone(a['ended_at'])
                self.assertEqual(seg(b), [(1, phases[0], 100, 0), (1, phases[1], 300, 0)])
                self.assertIsNone(b['segments'][-1]['ended_at'])
                self.assertEqual(b['segments'][0]['ended_at'], at(100))

    def test_explicit_pause_and_resume(self):
        for kind, phases in PHASES.items():
            with self.subTest(kind=kind):
                d = doc(kind, [(0, 'created', 1, phases[0], 'active'), (50, 'pause', 1, phases[0], 'paused'), (80, 'resume', 1, phases[0], 'active')])
                r = cycle_timing(d, T0 + timedelta(seconds=200))
                self.assertEqual((r['elapsed_seconds'], r['paused_seconds']), (200, 30))
                self.assertEqual(seg(r), [(1, phases[0], 170, 30)])

    def test_open_pause_keeps_counting_to_now(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active'), (50, 'pause', 1, 'plan', 'paused')], 'paused')
        for now, paused in ((60, 10), (500, 450)):
            r = cycle_timing(d, T0 + timedelta(seconds=now))
            self.assertEqual((r['elapsed_seconds'], r['paused_seconds']), (now, paused))

    def test_recorded_return_induced_pause(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active'), (10, 'advance', 1, 'review', 'active'),
                        (20, 'return-requested', 1, 'review', 'active'), (20, 'return', 1, 'review', 'paused'),
                        (90, 'extend', 1, 'review', 'paused'), (100, 'resume', 2, 'plan', 'active')])
        r = cycle_timing(d, T0 + timedelta(seconds=130))
        self.assertEqual(r['basis'], 'recorded')
        self.assertEqual(r['paused_seconds'], 80)
        self.assertEqual(seg(r), [(1, 'plan', 10, 0), (1, 'review', 10, 80), (2, 'plan', 30, 0)])

    def test_historical_return_followed_by_resume_is_derived_pause(self):
        d = doc('quick-fix', [(0, 'created', 1, 'build'), (10, 'advance', 1, 'review'), (20, 'return-requested', 1, 'review'),
                              (20, 'return', 1, 'review'), (90, 'extend', 1, 'review'), (100, 'resume', 2, 'build')])
        r = cycle_timing(d, T0 + timedelta(seconds=130))
        self.assertEqual(r['basis'], 'derived')
        self.assertEqual(r['paused_seconds'], 80)

    def test_historical_return_with_new_pass_is_not_a_pause(self):
        d = doc('refactor', [(0, 'created', 1, 'plan'), (10, 'advance', 1, 'review'), (20, 'return-requested', 1, 'review'),
                             (20, 'return', 2, 'plan'), (60, 'advance', 2, 'build')])
        r = cycle_timing(d, T0 + timedelta(seconds=100))
        self.assertEqual((r['paused_seconds'], r['basis']), (0, 'derived'))

    def test_historical_return_that_ends_the_record_paused(self):
        d = doc('iterate', [(0, 'created', 1, 'plan'), (20, 'return', 1, 'review')], 'paused')
        r = cycle_timing(d, T0 + timedelta(seconds=50))
        self.assertEqual((r['paused_seconds'], r['basis']), (30, 'derived'))

    def test_historical_record_without_returns_is_recorded_basis(self):
        d = doc('release', [(0, 'created', 1, 'plan'), (40, 'pause', 1, 'plan'), (70, 'resume', 1, 'plan')])
        r = cycle_timing(d, T0 + timedelta(seconds=100))
        self.assertEqual((r['paused_seconds'], r['basis']), (30, 'recorded'))

    def test_completed_values_do_not_change_with_now(self):
        for kind, phases in PHASES.items():
            with self.subTest(kind=kind):
                d = doc(kind, [(0, 'created', 1, phases[0], 'active'), (60, 'pause', 1, phases[0], 'paused'), (90, 'resume', 1, phases[0], 'active'),
                               (150, 'advance', 1, phases[-1], 'completed')], 'completed')
                results = [cycle_timing(d, T0 + timedelta(seconds=n)) for n in (150, 400, 10_000)]
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])
                r = results[0]
                self.assertEqual((r['elapsed_seconds'], r['paused_seconds'], r['ended_at']), (150, 30, at(150)))
                self.assertIsNotNone(r['segments'][-1]['ended_at'])

    def test_historical_completion_infers_from_document_status(self):
        d = doc('dev', [(0, 'created', 1, 'plan'), (80, 'advance', 1, 'reflect')], 'completed')
        r = cycle_timing(d, T0 + timedelta(seconds=999))
        self.assertEqual((r['elapsed_seconds'], r['ended_at'], r['basis']), (80, at(80), 'derived'))

    def test_owner_complete_closes_a_paused_cycle(self):
        d = doc('release', [(0, 'created', 1, 'plan'), (10, 'pause', 1, 'plan'), (60, 'owner-complete', 1, 'plan')], 'completed')
        r = cycle_timing(d, T0 + timedelta(seconds=9999))
        self.assertEqual((r['elapsed_seconds'], r['paused_seconds'], r['ended_at']), (60, 50, at(60)))

    def test_paused_then_abandoned_is_stable_at_later_now(self):
        for kind, phases in PHASES.items():
            with self.subTest(kind=kind):
                d = doc(kind, [(0, 'created', 1, phases[0], 'active'), (30, 'pause', 1, phases[0], 'paused'), (100, 'abandon', 1, phases[0], 'abandoned')], 'abandoned')
                results = [cycle_timing(d, T0 + timedelta(seconds=n)) for n in (100, 101, 5000, 10**7)]
                for r in results[1:]:
                    self.assertEqual(r, results[0])
                self.assertEqual((results[0]['elapsed_seconds'], results[0]['paused_seconds'], results[0]['ended_at']), (100, 70, at(100)))

    def test_extension_does_not_alter_time(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active'), (30, 'extend', 1, 'plan', 'active')])
        r = cycle_timing(d, T0 + timedelta(seconds=50))
        self.assertEqual((r['elapsed_seconds'], r['paused_seconds']), (50, 0))

    def test_decreasing_timestamps_use_effective_timeline_and_reconcile(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active'), (10, 'advance', 1, 'build', 'active'),
                        (5, 'pause', 1, 'build', 'paused'), (15, 'resume', 1, 'build', 'active')])
        r = cycle_timing(d, T0 + timedelta(seconds=15))
        self.assertEqual(r['elapsed_seconds'], 15)
        # The pause is effective at 10 and the resume at 15.
        self.assertEqual(r['paused_seconds'], 5)
        self.assertEqual(sum(s['active_seconds'] + s['paused_seconds'] for s in r['segments']), 15)

    def test_now_before_last_entry_is_clamped(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active'), (100, 'advance', 1, 'build', 'active')])
        r = cycle_timing(d, T0 + timedelta(seconds=40))
        self.assertEqual(r['elapsed_seconds'], 100)

    def test_epoch_seconds_now_matches_datetime_now(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active')])
        moment = T0 + timedelta(seconds=77)
        self.assertEqual(cycle_timing(d, moment), cycle_timing(d, moment.timestamp()))

    def test_totals_reconcile_for_every_type_and_input_is_unchanged(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active'), (20, 'pause', 1, 'plan', 'paused'), (45, 'resume', 1, 'plan', 'active'),
                        (60, 'advance', 1, 'build', 'active')])
        before = copy.deepcopy(d)
        r = cycle_timing(d, T0 + timedelta(seconds=100))
        self.assertEqual(d, before)
        self.assertAlmostEqual(sum(s['active_seconds'] + s['paused_seconds'] for s in r['segments']), r['elapsed_seconds'])
        json.dumps(r)

    def test_segments_change_with_each_pass_and_phase(self):
        d = doc('dev', [(0, 'created', 1, 'plan', 'active'), (10, 'advance', 1, 'build', 'active'), (30, 'return', 2, 'plan', 'active'),
                        (40, 'advance', 2, 'build', 'active')])
        r = cycle_timing(d, T0 + timedelta(seconds=50))
        self.assertEqual([(s['pass'], s['phase']) for s in r['segments']], [(1, 'plan'), (1, 'build'), (2, 'plan'), (2, 'build')])

    def test_real_historical_records_are_derived_and_reconcile(self):
        root = Path(__file__).resolve().parents[3] / 'bionic/cycles'
        path = root / 'CYC-0009/cycle.json'
        if not path.exists():
            self.skipTest('dogfood record absent')
        record = json.loads(path.read_text())
        r = cycle_timing(record, datetime(2027, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(r['basis'], 'derived')
        self.assertEqual(r['ended_at'], record['history'][-1]['at'])
        self.assertGreater(r['paused_seconds'], 0)
        self.assertAlmostEqual(sum(s['active_seconds'] + s['paused_seconds'] for s in r['segments']), r['elapsed_seconds'])


if __name__ == '__main__':
    unittest.main()
