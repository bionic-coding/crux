"""The forge-log preamble the cycle engine writes, held against forge-skill's locked block.

  (f) The live forge-log read reads only the log's preamble: the bytes before the
      first line that begins `## [`. Entries the cycle engine inserts never change
      what it asserts.

  (g) The cycle engine's forge-log preamble constant equals forge-skill's locked
      preamble block.

Uses only stdlib (unittest, pathlib, ast, re).  No mocks needed — everything resolves
from repo-relative paths so the test is cwd-independent.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

try:
    from ._dev_surface import require_dev_surface
except ImportError:  # unittest discover imports test modules top-level
    from _dev_surface import require_dev_surface

# ─── repo paths ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FORGE_SKILL = REPO_ROOT / "crux" / "skills" / "forge-skill" / "SKILL.md"
FORGE_LOG_MD = REPO_ROOT / ".claude" / "skills" / "forge-log.md"
ENGINE_LOCAL_SKILLS = REPO_ROOT / "crux" / "scripts" / "cycle_local_skills.py"

# ─── live forge-log preamble ─────────────────────────────────────────────────

_ENTRY_LINE = re.compile(r"^## \[", re.MULTILINE)


def forge_log_preamble(text: str) -> str:
    """The live forge log's preamble: the text before the first line that begins `## [`.

    The cycle engine inserts `used` entries before that line, so a read of the
    preamble alone stays independent of the entries."""
    match = _ENTRY_LINE.search(text)
    return text if match is None else text[: match.start()]


# ─────────────────────────────────────────────────────────────────────────────
# (g) Engine preamble constant
# ─────────────────────────────────────────────────────────────────────────────


def _locked_preamble_block(text: str) -> str:
    """forge-skill's locked preamble: the fenced block under `**Preamble (written once on first write):**`."""
    anchor = text.index("**Preamble (written once on first write):**")
    match = re.compile(r"```markdown\n(.*?)```", re.DOTALL).search(text, anchor)
    if match is None:
        raise AssertionError("forge-skill/SKILL.md has no fenced preamble block after its anchor")
    return match.group(1)


def _engine_constant(name: str, path: Path = ENGINE_LOCAL_SKILLS):
    """The literal value of one module-level assignment in an engine module, read without importing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{path.name} assigns no {name}")


class TestEnginePreambleEqualsLockedPreamble(unittest.TestCase):
    """(g) The bytes the engine writes as a new forge log's preamble are forge-skill's locked block."""

    def test_engine_preamble_equals_forge_skill_locked_preamble(self) -> None:
        locked = _locked_preamble_block(FORGE_SKILL.read_text(encoding="utf-8"))
        engine = _engine_constant("PREAMBLE")
        self.assertIsInstance(engine, bytes)
        self.assertEqual(engine.decode("utf-8"), locked)

    def test_live_forge_log_preamble_carries_the_locked_body_line(self) -> None:
        require_dev_surface(self, FORGE_LOG_MD, ".claude/skills/forge-log.md")
        locked_body = _locked_preamble_block(FORGE_SKILL.read_text(encoding="utf-8")).splitlines()[2]
        preamble = forge_log_preamble(FORGE_LOG_MD.read_text(encoding="utf-8"))
        self.assertIn(locked_body, preamble)

    def test_preamble_reader_stops_at_the_first_entry(self) -> None:
        text = "# Forge log\n\n_pre_\n\n## [2026-11-07 10:00] used | a-b\nbody\n## [x] y\n"
        self.assertEqual(forge_log_preamble(text), "# Forge log\n\n_pre_\n\n")
        self.assertEqual(forge_log_preamble("no entries\n"), "no entries\n")
        self.assertEqual(forge_log_preamble("text ## [not a line start]\n"), "text ## [not a line start]\n")
