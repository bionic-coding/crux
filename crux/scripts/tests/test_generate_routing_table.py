"""Tests for generate-routing-table.py — the fourteenth regenerative output (ADR-0092).

Modelled on test_generate_writing_rules.py: the marker-region generator's core is
the fail-closed `find_region`, so every refusal path is pinned, plus the
`build_region` user-invocable/Claude-only split and an end-to-end `run()` that
proves the region body is replaced while everything outside the markers survives
byte-for-byte.

The F1 phrase-extraction grammar (triggers placed after the first period are
dropped) is DEFERRED, not fixed here: `extract_phrases` is tested at its current,
documented behavior — the post-period drop is asserted as the status quo.

Stdlib only (unittest, importlib, tempfile, pathlib, json, subprocess, sys).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "crux" / "scripts" / "generate-routing-table.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_routing_table", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


grt = _load_module()
B, E = grt.BEGIN, grt.END


class FindRegionTestCase(unittest.TestCase):
    """find_region is the fail-closed core; every refusal path is tested (lines 104-123)."""

    def test_valid_single_pair_returns_span_and_preserves_outside(self):
        text = f"HEAD\n{B}\nold body\n{E}\nTAIL\n"
        i, j = grt.find_region(text, "t")
        # The span is the BODY strictly between the marker lines.
        self.assertEqual(text[i:j], "\nold body\n")
        # Replacing the body leaves the bytes outside the markers verbatim.
        rebuilt = text[:i] + "\nNEW\n" + text[j:]
        self.assertEqual(rebuilt, f"HEAD\n{B}\nNEW\n{E}\nTAIL\n")
        self.assertTrue(text[:i].endswith(B))
        self.assertTrue(text[j:].startswith(E))

    def test_missing_begin_marker_is_refused(self):
        with self.assertRaises(grt.RegenError) as cm:
            grt.find_region(f"only\n{E}\n", "t")
        self.assertIn("missing marker", str(cm.exception))

    def test_missing_end_marker_is_refused(self):
        with self.assertRaises(grt.RegenError) as cm:
            grt.find_region(f"only\n{B}\n", "t")
        self.assertIn("missing marker", str(cm.exception))

    def test_duplicate_begin_marker_is_refused_rather_than_guessed(self):
        text = f"{B}\na\n{E}\n{B}\nb\n{E}\n"
        with self.assertRaises(grt.RegenError) as cm:
            grt.find_region(text, "t")
        self.assertIn("duplicate marker", str(cm.exception))

    def test_end_before_begin_is_refused(self):
        with self.assertRaises(grt.RegenError) as cm:
            grt.find_region(f"{E}\nbody\n{B}\n", "t")
        self.assertIn("precedes", str(cm.exception))

    def test_marker_as_midline_substring_is_not_a_delimiter(self):
        # A marker mentioned inside a sentence must not delimit anything.
        text = f"Prose mentioning {B} and {E} inline.\n"
        with self.assertRaises(grt.RegenError) as cm:
            grt.find_region(text, "t")
        self.assertIn("missing marker", str(cm.exception))


class BuildRegionTestCase(unittest.TestCase):
    """build_region splits user-invocable skills from Claude-only ones and
    reports the skills whose description yields no trigger phrase."""

    SKILLS = [
        {"id": "beta", "description": 'Use when "do this" / "do that". "ignored" after.'},
        {"id": "alpha", "description": "No quotes here at all.", "routing_note": "note-a"},
        {"id": "zed", "description": "whatever", "user-invocable": False,
         "routing_note": "claude-note"},
    ]

    def test_user_invocable_and_claude_only_are_split(self):
        region, no_triggers = grt.build_region(self.SKILLS)
        # Main table header present; the Claude-only sub-table present.
        self.assertIn("| User phrase | Skill | Notes |", region)
        self.assertIn("### Claude-only (no user phrase)", region)
        # `zed` (user-invocable: false) is in the Claude-only table, NOT the main
        # one, and carries its routing note.
        self.assertIn("| `zed` | claude-note |", region)
        # A user-invocable skill lands in the main table with its phrase cell.
        self.assertIn('| "do this" / "do that" | `beta` |', region)

    def test_no_trigger_skill_is_reported_and_gets_an_empty_phrase_cell(self):
        region, no_triggers = grt.build_region(self.SKILLS)
        # `alpha` is user-invocable but has no quoted phrase → reported, and its
        # main-table row has an empty phrase cell.
        self.assertEqual(no_triggers, ["alpha"])
        self.assertIn("|  | `alpha` | note-a |", region)

    def test_rows_are_sorted_by_skill_id(self):
        region, _ = grt.build_region(self.SKILLS)
        # alpha before beta in the main table.
        self.assertLess(region.index("`alpha`"), region.index("`beta`"))


class ExtractPhrasesCurrentBehaviorTestCase(unittest.TestCase):
    """Current, documented behavior — the F1 post-period drop is DEFERRED, not fixed."""

    def test_only_phrases_before_the_first_period_are_taken(self):
        # This IS the F1 defect, asserted as the status quo: a trigger placed
        # after the first period is dropped. Do not "fix" this here.
        phrases = grt.extract_phrases('Use "keep me". Then "drop me" later.')
        self.assertEqual(phrases, ["keep me"])

    def test_duplicates_are_collapsed_in_order(self):
        phrases = grt.extract_phrases('"a" / "b" / "a"')
        self.assertEqual(phrases, ["a", "b"])

    def test_single_quoted_triggers_are_recognized(self):
        phrases = grt.extract_phrases("Use when 'start a cycle' happens")
        self.assertEqual(phrases, ["start a cycle"])


class RunEndToEndTestCase(unittest.TestCase):
    """run() against a minimal temp tree: region replaced, outside preserved."""

    def _make_tree(self, tmp: Path, body: str, skills: list[dict]) -> Path:
        (tmp / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n', encoding="utf-8")
        (tmp / "crux" / "catalog").mkdir(parents=True)
        (tmp / "crux" / "catalog" / "skills.json").write_text(
            json.dumps(skills), encoding="utf-8"
        )
        (tmp / "bionic").mkdir()
        claude = tmp / "bionic" / "CLAUDE.md"
        claude.write_text(f"HEAD LINE\n{B}\n{body}\n{E}\nTAIL LINE\n", encoding="utf-8")
        return claude

    SKILLS = [{"id": "alpha", "description": 'Use when "do this".', "routing_note": "n"}]

    def test_dry_run_reports_drift_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            claude = self._make_tree(tmp, "STALE", self.SKILLS)
            before = claude.read_text(encoding="utf-8")
            code, payload = grt.run(tmp, dry_run=True)
            self.assertEqual(code, 1)
            self.assertTrue(payload["drift"])
            self.assertEqual(claude.read_text(encoding="utf-8"), before, "--dry-run must not write")

    def test_regeneration_replaces_region_and_preserves_outside_verbatim(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            claude = self._make_tree(tmp, "STALE", self.SKILLS)
            code, payload = grt.run(tmp, dry_run=False)
            self.assertEqual(code, 0)
            self.assertEqual(payload["written"], ["bionic/CLAUDE.md"])
            after = claude.read_text(encoding="utf-8")
            # Bytes outside the markers are untouched.
            self.assertTrue(after.startswith("HEAD LINE\n"))
            self.assertTrue(after.endswith("\nTAIL LINE\n"))
            # The regenerated region carries the skill's row; STALE is gone.
            self.assertNotIn("STALE", after)
            self.assertIn("`alpha`", after)

    def test_regeneration_is_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            claude = self._make_tree(tmp, "STALE", self.SKILLS)
            grt.run(tmp, dry_run=False)
            first = claude.read_text(encoding="utf-8")
            code, payload = grt.run(tmp, dry_run=True)
            self.assertEqual(code, 0)
            self.assertFalse(payload["drift"])
            self.assertEqual(claude.read_text(encoding="utf-8"), first)


class ExitAndEnrollmentTestCase(unittest.TestCase):
    def test_missing_skills_json_exits_one_with_json(self):
        with tempfile.TemporaryDirectory() as t:
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--dry-run", "--repo-root", t],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn('"error"', proc.stdout)

    def test_enrolled_in_the_regenerative_outputs_table(self):
        claude = REPO_ROOT / "CLAUDE.md"
        if not claude.is_file():
            self.skipTest(
                "repo-root CLAUDE.md absent (staged public artifact) — the "
                "regenerative-outputs roster is dev-repo only"
            )
        self.assertIn("generate-routing-table.py", claude.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
