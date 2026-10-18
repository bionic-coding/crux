"""New work cannot silently allocate another legacy promptbook run."""
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('legacy_start', SCRIPTS / 'start-run.py')
start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start)


class LegacyCutoverTests(unittest.TestCase):
    def test_default_refuses_before_any_write(self):
        with patch.object(start, 'create_run') as writer, redirect_stdout(io.StringIO()) as output:
            result = start.main(['old.yaml', '--run-id', 'RUN-002', '--output', 'new.yaml'])
        self.assertEqual(1, result)
        writer.assert_not_called()
        self.assertIn('new-work-uses-cycle', output.getvalue())

    def test_explicit_replay_preserves_historical_writer(self):
        with patch.object(start, 'create_run', return_value={'run': 'fixture'}) as writer, redirect_stdout(io.StringIO()):
            result = start.main(['--historical-replay', 'old.yaml', '--run-id', 'RUN-001', '--output', 'new.yaml'])
        self.assertEqual(0, result)
        writer.assert_called_once()
