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

One exemption, read from the script's own contract: an operand
`${CRUX_PLUGIN_ROOT}/scripts/<name>.py` may run in project mode only when that script's module
docstring holds a paragraph that begins with "Runs in the subject project's environment" and has
at least one further sentence after the sentence that holds the phrase. The further sentence is the
stated reason. A paragraph with the phrase alone exempts nothing. The test-evidence engine states
its reason this way; this file lists no script. The companion guard
`test_shipped_instructions_teach_only_the_python3_evidence_form` in
`test_cycle_instruction_contracts.py` rejects a `-p` or `--no-project` variant of the
engine line.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent.parent / "skills"
SCRIPTS = Path(__file__).resolve().parent.parent

# `uv run` followed by flags, then a bare python/python3 command word.
_INVOCATION = re.compile(r"\buv run\b(?P<flags>[^|&;`\n]*?)\s(?P<py>python3?)(?=\s|$)")

# The exact phrase a script contract opens its project-mode paragraph with.
_CONTRACT_PHRASE = "Runs in the subject project's environment"
_OPERAND = re.compile(r'^"?\$\{CRUX_PLUGIN_ROOT\}/scripts/(?P<name>[A-Za-z0-9_-]+\.py)"?(?=\s|$)')


def contract_states_project_mode(script: Path) -> bool:
    """True when the script's module docstring carries the phrase paragraph with a reason sentence."""
    try:
        doc = ast.get_docstring(ast.parse(script.read_text(encoding="utf-8")), clean=True)
    except (OSError, SyntaxError, ValueError):
        return False
    for paragraph in re.split(r"\n\s*\n", doc or ""):
        flat = " ".join(paragraph.split())
        if not flat.startswith(_CONTRACT_PHRASE):
            continue
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", flat) if s.strip()]
        if len(sentences) >= 2:
            return True
    return False


def _runs_exempt_script(line: str, end: int, scripts_dir: Path) -> bool:
    """True when the first argument after python/python3 is a plugin script whose contract exempts it."""
    match = _OPERAND.match(line[end:].lstrip())
    if match is None:
        return False
    return contract_states_project_mode(scripts_dir / match.group("name"))


def unpinned_invocations(text: str, scripts_dir: Path = SCRIPTS) -> list[tuple[int, str]]:
    """Return (line number, line) for each direct-python `uv run` lacking a pin."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = _INVOCATION.search(line)
        if match is None or "crux/scripts/" in line:
            continue
        if _runs_exempt_script(line, match.end(), scripts_dir):
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

    def test_accepts_the_engine_form(self):
        line = 'uv run python3 "${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py" lookup --repo-root .'
        self.assertEqual(unpinned_invocations(line), [])

    def test_flags_another_plugin_script_in_project_mode(self):
        line = 'uv run python3 "${CRUX_PLUGIN_ROOT}/scripts/derive-arch.py"'
        self.assertEqual(len(unpinned_invocations(line)), 1)

    def test_flags_the_engine_named_other_than_as_the_python_operand(self):
        line = "uv run python3 -c 'x' \"${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py\""
        self.assertEqual(len(unpinned_invocations(line)), 1)

    def test_engine_exception_rejects_similar_or_suffixed_paths(self):
        for operand in (
            '"${CRUX_PLUGIN_ROOT}/scripts/test-evidence.py.backup"',
            '"${CRUX_PLUGIN_ROOT}/scripts/not-test-evidence.py"',
        ):
            with self.subTest(operand=operand):
                self.assertEqual(len(unpinned_invocations(f"uv run python3 {operand}")), 1)

    def test_derive_arch_in_project_mode_stays_flagged(self):
        line = 'uv run python3 "${CRUX_PLUGIN_ROOT}/scripts/derive-arch.py" --dry-run'
        self.assertEqual(len(unpinned_invocations(line)), 1)

    def test_engine_exemption_is_read_from_its_contract(self):
        self.assertTrue(contract_states_project_mode(SCRIPTS / "test-evidence.py"))
        self.assertFalse(contract_states_project_mode(SCRIPTS / "derive-arch.py"))

    def _fixture_line(self, docstring: str) -> list[tuple[int, str]]:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "probe-tool.py").write_text(f'"""{docstring}"""\nimport sys\n', encoding="utf-8")
            line = 'uv run python3 "${CRUX_PLUGIN_ROOT}/scripts/probe-tool.py" --x'
            return unpinned_invocations(line, scripts_dir=Path(tmp))

    def test_fixture_with_phrase_and_reason_is_exempt(self):
        doc = "Probe.\n\nRuns in the subject project's environment. The check reads the subject's lock.\n"
        self.assertEqual(self._fixture_line(doc), [])

    def test_fixture_without_the_paragraph_is_flagged(self):
        self.assertEqual(len(self._fixture_line("Probe tool.\n\nIt does things. It does more.\n")), 1)

    def test_fixture_with_phrase_and_no_reason_sentence_is_flagged(self):
        doc = "Probe.\n\nRuns in the subject project's environment.\n"
        self.assertEqual(len(self._fixture_line(doc)), 1)

    def test_fixture_with_phrase_not_opening_its_paragraph_is_flagged(self):
        doc = "Probe.\n\nThis tool Runs in the subject project's environment. Because reasons.\n"
        self.assertEqual(len(self._fixture_line(doc)), 1)

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
