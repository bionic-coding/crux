"""Retired skill routes keep their shipped operator interfaces."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


PLUGIN = Path(__file__).resolve().parents[2]


class RetainedOperatorInterfaceTests(unittest.TestCase):

    def test_runtime_driver_runs_outside_project(self):
        runtime = (PLUGIN / "box" / "runtime-apis.md").read_text()
        driver = runtime.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime_apis.py"
            path.write_text(driver + "\n")
            env = dict(os.environ, CRUX_PLUGIN_ROOT=str(PLUGIN))
            result = subprocess.run(
                ["uv", "run", "--no-project", str(path)],
                cwd=tmp,
                env=env,
                text=True,
                capture_output=True,
                timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("runtime APIs importable", result.stdout)


if __name__ == "__main__":
    unittest.main()
