"""Static contracts for task-local workflow instructions.

These tests prove that each route and its critical procedure text ships together.
They do not prove what a host loads; fresh-session checks remain necessary.

Run: uv run python3 -m unittest discover -s crux/scripts/tests -p test_log_work_prose.py
"""

from __future__ import annotations

import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2] / "skills"


def source(skill: str, reference: str | None = None) -> str:
    root = SKILLS / skill
    path = root / "SKILL.md" if reference is None else root / "references" / f"{reference}.md"
    return path.read_text(encoding="utf-8")


class TaskLocalProcedureTests(unittest.TestCase):
    def test_log_work_routes_to_available_selected_references(self):
        entry = source("log-work")
        for operation in ("journal", "log-only"):
            with self.subTest(operation=operation):
                self.assertIn(f"references/{operation}.md", entry)
                self.assertTrue(source("log-work", operation).startswith("# "))
        self.assertIn("before the first side effect", entry)
        self.assertIn("missing or unreadable", entry)
        self.assertNotIn("## The pipeline", entry)

    def test_run_promptbook_routes_to_available_selected_references(self):
        entry = source("run-promptbook")
        for operation in ("start", "advance", "abandon", "status"):
            with self.subTest(operation=operation):
                self.assertIn(f"references/{operation}.md", entry)
                self.assertTrue(source("run-promptbook", operation).startswith("# "))
        self.assertIn("before the first side effect", entry)
        self.assertIn("missing or unreadable", entry)
        self.assertNotIn("## The pipeline", entry)


if __name__ == "__main__":
    unittest.main()
