"""Clean-environment `--help` check for every script entry point.

A script run as `uv run <path>.py` gets only the packages its PEP 723 block
declares. The plugin suite runs in the project environment, which has more
packages, so an undeclared third-party import passes there and fails for a
user. This test runs each entry point's `--help` in an isolated uv
environment and fails on an ImportError or ModuleNotFoundError.

Entry point: a file under crux/scripts, or under a skill's `scripts/`
directory (the three installers), that carries a PEP 723 `script` block and a
`__main__` guard. A block without a guard marks a library, which is imported
and never run.

Safety: each run starts in an empty scratch directory with CRUX_HOME set to
another empty directory, so `--help` cannot write the repository or reach a
live model route. EXCLUDED lists scripts that must not run; it is empty
because every entry point answers `--help` without side effects.

Offline: uv resolves from its cache when it can. When resolution needs the
network and fails, the test skips and says so; it never passes silently.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SCRIPTS_DIR.parent
SKILLS_DIR = PLUGIN_ROOT / "skills"

# relative path -> reason the script cannot run `--help` safely.
EXCLUDED: dict[str, str] = {}

BLOCK_RE = re.compile(r"(?m)^# /// script$")
IMPORT_ERR_RE = re.compile(r"ModuleNotFoundError|ImportError")
OFFLINE_RE = re.compile(
    r"Failed to fetch|dns error|error sending request|"
    r"Failed to download|Temporary failure in name resolution|network was disabled|offline"
)
TIMEOUT_S = 180
WORKERS = 8


def rel_key(path: Path) -> str:
    """Name a script relative to crux/scripts, or to the plugin root for a skill script."""
    if path.is_relative_to(SCRIPTS_DIR):
        return path.relative_to(SCRIPTS_DIR).as_posix()
    return path.relative_to(PLUGIN_ROOT).as_posix()


def entry_points() -> list[Path]:
    found = []
    candidates = sorted(SCRIPTS_DIR.rglob("*.py")) + sorted(SKILLS_DIR.glob("*/scripts/**/*.py"))
    for path in candidates:
        rel = Path(rel_key(path))
        if "tests" in rel.parts or "__pycache__" in rel.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if BLOCK_RE.search(text) and "__main__" in text:
            found.append(path)
    return found


def run_help(script: Path) -> tuple[int, str]:
    """Run `script --help` isolated; return (exit code, stderr)."""
    with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as home:
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("VIRTUAL_ENV", "UV_PROJECT"))
               and k not in ("PYTHONPATH", "PYTHONHOME")}
        env["CRUX_HOME"] = home
        try:
            proc = subprocess.run(
                ["uv", "run", "--isolated", "--no-project", str(script), "--help"],
                cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return 124, f"timeout after {TIMEOUT_S}s"
        return proc.returncode, proc.stderr


def classify(code: int, err: str) -> str | None:
    """Return "import", "offline", "other" or None (a clean run)."""
    if IMPORT_ERR_RE.search(err):
        return "import"
    if code == 0:
        return None
    return "offline" if OFFLINE_RE.search(err) else "other"


def check_all(scripts: list[Path]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return (import, offline, other failures), each keyed by relative path."""
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(run_help, scripts))
    found: dict[str, dict[str, str]] = {"import": {}, "offline": {}, "other": {}}
    for script, (code, err) in zip(scripts, results):
        kind = classify(code, err)
        if kind:
            last = err.strip().splitlines()[-1] if err.strip() else ""
            found[kind][rel_key(script)] = last
    return found["import"], found["offline"], found["other"]


@unittest.skipUnless(shutil.which("uv"), "uv is not installed; the clean-environment check needs it")
class EntrypointCleanEnvTests(unittest.TestCase):
    def test_discovery_finds_entry_points(self):
        names = {rel_key(p) for p in entry_points()}
        self.assertIn("cycle.py", names)
        for agent in ("codex", "opencode", "omp"):
            self.assertIn(f"skills/install-{agent}-agents/scripts/install.py", names)
        self.assertGreater(len(names), 50)
        self.assertNotIn("summaries_projection.py", names)  # block, no guard: a library

    def test_positive_control_detects_undeclared_import(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.py"
            bad.write_text(textwrap.dedent('''\
                # /// script
                # requires-python = ">=3.13"
                # dependencies = []
                # ///
                import httpx  # installed in the dev environment, undeclared here

                if __name__ == "__main__":
                    pass
                '''))
            code, err = run_help(bad)
        self.assertNotEqual(code, 0)
        self.assertRegex(err, IMPORT_ERR_RE)

    def test_positive_control_reports_a_non_import_failure(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "boom.py"
            bad.write_text(textwrap.dedent('''\
                # /// script
                # requires-python = ">=3.13"
                # dependencies = []
                # ///
                undefined_name_xyz

                if __name__ == "__main__":
                    pass
                '''))
            code, err = run_help(bad)
        self.assertEqual(classify(code, err), "other")
        self.assertIn("NameError", err)

    def test_every_entry_point_starts_in_a_clean_environment(self):
        scripts = [p for p in entry_points() if rel_key(p) not in EXCLUDED]
        imports, offline, other = check_all(scripts)
        if offline and not imports and not other:
            self.skipTest(f"uv could not resolve dependencies (offline?): {sorted(offline)[:3]}")
        self.assertEqual(imports, {}, "entry points that fail to import in a clean uv environment")
        self.assertEqual(other, {}, "entry points whose --help exits non-zero for a reason other than import or network")


if __name__ == "__main__":
    unittest.main()
