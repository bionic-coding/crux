"""inspect carries the cycle's last activity and each open attempt's, with age and source (F26, F28).

The friction: inspect said only `liveness unknown`, so a commander could not tell an idle cycle
from one whose developer had committed two minutes earlier, and one session was lost with no trace.
The activity is derived by cycle_activity from the record and git; liveness stays `unknown`.
"""
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cycle_activity
from test_cycle_slice import SliceBase


def later(seconds):
    return patch.object(cycle_activity, 'time', SimpleNamespace(time=lambda: time.time() + seconds))


class InspectActivityTests(SliceBase):
    def test_no_open_attempt_and_a_three_hour_old_write_reads_idle_with_the_age(self):
        with later(3 * 3600):
            full = self.ok({'op': 'inspect'})
            short = self.ok({'op': 'inspect', 'summary': True})
        for found in (full, short):
            self.assertEqual(found['activity']['state'], 'idle')
            self.assertEqual(found['activity']['last']['source'], 'record-write')
            self.assertGreaterEqual(found['activity']['last']['age_s'], 3 * 3600)
            self.assertTrue(found['activity']['text'].startswith('idle for 3h0'), found['activity']['text'])

    def test_an_open_attempt_shows_its_trailer_commit_age_and_source_and_liveness_stays_unknown(self):
        prepared = self.prepare()
        (self.repo / 'src/a.py').write_text('answer = 2\n')
        self.git('add', 'src/a.py')
        # The commit is dated 5 s after the reservation, so it is the attempt's newest event.
        with patch.dict('os.environ', {'GIT_COMMITTER_DATE': f'@{int(time.time()) + 5} +0000'}):
            self.git('commit', '-q', '-m', 'set the answer\n\nCycle-Task: build-it')
        sha = self.git('rev-parse', 'HEAD')
        with later(125):
            full = self.ok({'op': 'inspect', 'host': 'claude-code'})
            short = self.ok({'op': 'inspect', 'summary': True, 'host': 'claude-code'})
        rows = [a for a in full['assignments'] if a['id'] == prepared['assignment']]
        self.assertEqual(len(rows), 1)
        for row in (rows[0], short['open_attempts'][0]):
            self.assertEqual(row['liveness'], 'unknown')
            last = row['last_activity']
            self.assertEqual((last['source'], last['detail']), ('commit', sha[:12]))
            self.assertGreaterEqual(last['age_s'], 120)
        for found in (full, short):
            self.assertEqual(found['activity']['state'], 'attempts-open')
            self.assertTrue(found['activity']['text'].startswith('last activity 2m ago (commit '), found['activity']['text'])

    def test_a_delivered_attempt_carries_no_activity(self):
        prepared = self.prepare()
        sha = self.work(prepared)
        self.ok({'op': 'deliver', 'op_id': 'deliver-01', 'assignment': prepared['assignment'], 'attempt': 1, 'outcome': 'done', 'commits': [sha]})
        found = self.ok({'op': 'inspect'})
        self.assertEqual(found['activity']['state'], 'idle')
        self.assertTrue(all('last_activity' not in a for a in found['assignments']))


if __name__ == '__main__':
    unittest.main()
