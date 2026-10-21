"""`cycle.py status` renders the cycle visualization read-only, once or on a timer."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import cycle  # noqa: E402
import cycle_progress  # noqa: E402
from cycle_workflow import create  # noqa: E402

spec = importlib.util.spec_from_file_location('visualize_cycle_progress', HERE / 'visualize-cycle-progress.py')
visualizer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visualizer)


def run(main, *argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(list(argv))
    return code, out.getvalue()


class StatusTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'bionic').mkdir(); (self.root / 'src').mkdir()
        (self.root / 'bionic/manifest.yml').write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.first = create(self.root, 'quick-fix', 'First fix', 'Goal', ['src'], ['passes'], 'b', 't')['id']
        self.second = create(self.root, 'iterate', 'Second change', 'Goal', ['src'], ['passes'], 'b', 't')['id']
        # One clock for both readers, so their documents compare byte for byte.
        clock = mock.patch.object(cycle_progress.time, 'time', return_value=2_000_000_000)
        clock.start(); self.addCleanup(clock.stop)

    def status(self, *argv):
        return run(cycle.main, '--repo-root', str(self.root), 'status', *argv)

    def test_single_cycle_matches_the_visualizer_text(self):
        code, text = self.status(self.first)
        self.assertEqual(code, 0)
        self.assertEqual(text, run(visualizer.main, '--project-root', str(self.root), '--cycle', self.first)[1])
        self.assertIn('First fix', text); self.assertNotIn('Second change', text)

    def test_all_cycles_without_an_identity(self):
        code, text = self.status()
        self.assertEqual(code, 0)
        self.assertEqual(text, run(visualizer.main, '--project-root', str(self.root))[1])
        self.assertLess(text.index('Second change'), text.index('First fix'))

    def test_json_is_the_visualizer_document(self):
        for argv in ((), (self.first,)):
            with self.subTest(argv=argv):
                code, text = self.status(*argv, '--json')
                extra = ('--cycle', *argv) if argv else ()
                self.assertEqual(code, 0)
                self.assertEqual(text, run(visualizer.main, '--project-root', str(self.root), *extra, '--json')[1])
                self.assertEqual(json.loads(text)['format'], 'crux.cycle-progress')

    def test_unknown_or_invalid_cycle_exits_1(self):
        for identity in ('CYC-9999', 'not-a-cycle'):
            with self.subTest(identity=identity):
                self.assertEqual(self.status(identity)[0], 1)

    def test_missing_tree_exits_2(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(run(cycle.main, '--repo-root', empty, 'status')[0], 2)

    def test_watch_redraws_until_interrupted_and_writes_nothing(self):
        record = self.root / 'bionic/cycles' / self.first / 'cycle.json'
        before = record.read_bytes()
        with mock.patch.object(cycle.time, 'sleep', side_effect=[None, KeyboardInterrupt]) as sleep:
            code, text = self.status(self.first, '--watch', '5')
        self.assertEqual(code, 0)
        self.assertEqual(text.count('\x1b[H\x1b[2J'), 2)
        self.assertEqual(text.count('First fix'), 2)
        self.assertEqual([c.args for c in sleep.call_args_list], [(5.0,), (5.0,)])
        self.assertEqual(record.read_bytes(), before)

    def test_watch_rejects_a_non_positive_interval(self):
        with redirect_stdout(io.StringIO()), mock.patch('sys.stderr', io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                cycle.main(['--repo-root', str(self.root), 'status', '--watch', '0'])
        self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
