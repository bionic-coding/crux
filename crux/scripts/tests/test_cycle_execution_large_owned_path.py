"""An execution checkpoint identifies an owned file larger than the context-read bound."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_context_read as reader
import cycle_execution


class LargeOwnedPathCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self.tmp.name))
        self.env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, env=self.env)
        self.name = 'log.md'
        self.path = self.root / self.name
        self.path.write_bytes(b'## [2026-11-07] op | entry\n' * 50000)  # about 1.3 MiB

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_context_reader_still_refuses_the_file(self):
        # Positive control: the fixture really exceeds the context bound.
        self.assertGreater(self.path.stat().st_size, reader.MAX_OBJECT_BYTES)
        with self.assertRaises(reader.ReadRefused):
            reader._bounded_bytes(reader.Reference(self.path, self.root))

    def test_the_checkpoint_records_the_git_blob_identity(self):
        pending = cycle_execution._pending(self.root, [self.name])
        # The raw blob identity: no clean filter or attribute of the developer's configuration applies (CYC-0118 C3).
        expected = subprocess.run(['git', '-C', str(self.root), 'hash-object', '--no-filters', self.name],
                                  check=True, capture_output=True, text=True, env=self.env).stdout.strip()
        self.assertEqual(pending[self.name]['working'], {'mode': '100644', 'oid': expected})
        self.assertIsNone(pending[self.name]['index'])


if __name__ == '__main__':
    unittest.main()
