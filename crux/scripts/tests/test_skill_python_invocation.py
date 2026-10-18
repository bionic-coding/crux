"""Shipped skills must not run plugin Python on the project's `.venv`.

A skill runs with the user's project as its working directory. A bare
`uv run python3 ...` there selects the project's `.venv` interpreter, which may
be older than the Python 3.13 floor crux supports (a 3.9 `.venv` rejects `-P`).
PEP 723 script invocations (`uv run "${CRUX_PLUGIN_ROOT}/scripts/x.py"`) get an
isolated environment and are unaffected, so this guard reads only invocations
that run `python`/`python3` directly.

The rule: such an invocation carries `--no-project` and an explicit
`-p`/`--python` request. An invocation whose own line names a repo-relative
`crux/scripts/` path runs this checkout's dev commands, not a downstream
project's, and is out of scope.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent.parent / "skills"

# `uv run` followed by flags, then a bare python/python3 command word.
_INVOCATION = re.compile(r"\buv run\b(?P<flags>[^|&;`\n]*?)\s(?P<py>python3?)(?=\s|$)")


def unpinned_invocations(text: str) -> list[tuple[int, str]]:
    """Return (line number, line) for each direct-python `uv run` lacking a pin."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = _INVOCATION.search(line)
        if match is None or "crux/scripts/" in line:
            continue
        flags = match.group("flags")
        has_no_project = "--no-project" in flags
        has_python = re.search(r"(?:^|\s)(?:-p|--python)(?:[\s=]|$)", flags) is not None
        if not (has_no_project and has_python):
            found.append((number, line.strip()))
    return found


class UnpinnedInvocationDetectorTests(unittest.TestCase):
    def test_flags_the_project_venv_form(self):
        line = "  printf x | uv run python3 -P -c 'print(1)'"
        self.assertEqual(len(unpinned_invocations(line)), 1)

    def test_flags_no_project_without_a_python_request(self):
        self.assertEqual(len(unpinned_invocations("uv run --no-project python3 -c 'x'")), 1)

    def test_accepts_the_pinned_form(self):
        line = "uv run --no-project -p '>=3.13' -- python3 -P -c 'print(1)'"
        self.assertEqual(unpinned_invocations(line), [])

    def test_ignores_pep723_script_invocations(self):
        line = 'uv run "${CRUX_PLUGIN_ROOT}/scripts/derive-arch.py" --dry-run'
        self.assertEqual(unpinned_invocations(line), [])

    def test_ignores_repo_relative_dev_commands(self):
        line = "`uv run python3 crux/scripts/validate-catalog.py --dry-run`"
        self.assertEqual(unpinned_invocations(line), [])


class ShippedSkillsPinPythonTests(unittest.TestCase):
    def test_every_direct_python_invocation_is_pinned(self):
        files = sorted(SKILLS.glob("**/*.md"))
        self.assertGreater(len(files), 0)
        offenders = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            for number, line in unpinned_invocations(text):
                offenders.append(f"{path.relative_to(SKILLS)}:{number}: {line}")
        self.assertEqual(offenders, [], "unpinned `uv run python` in shipped skills")

    def test_migration_uses_the_canonical_script_entrypoint(self):
        text = (SKILLS / "migrate-adrs" / "SKILL.md").read_text(encoding="utf-8")
        reference=(SKILLS / "migrate-adrs" / "references" / "publication.md").read_text(encoding="utf-8")
        self.assertIn('uv run "${CRUX_PLUGIN_ROOT}/scripts/adr-migration.py"',reference)
        self.assertEqual(unpinned_invocations(text+reference),[])


@unittest.skipUnless(shutil.which("uv"), "uv is not installed")
class PinnedFormIgnoresProjectVenvTests(unittest.TestCase):
    def test_pinned_form_selects_a_supported_interpreter_in_a_venv_project(self):
        host = Path("/usr/bin/python3")
        if not host.exists():
            host = Path(sys.executable)
        with tempfile.TemporaryDirectory() as tmp:
            made = subprocess.run(
                [str(host), "-m", "venv", ".venv"], cwd=tmp, capture_output=True, text=True
            )
            if made.returncode != 0:
                self.skipTest("cannot create a scratch .venv")
            cmd = [
                "uv", "run", "--offline", "--no-project", "-p", ">=3.13", "--",
                "python3", "-P", "-c", "import sys; print(sys.version_info[:2] >= (3, 13))",
            ]
            result = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
            if result.returncode != 0 and "No interpreter found" in result.stderr:
                self.skipTest("no Python 3.13 available offline")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "True")


if __name__ == "__main__":
    unittest.main()
