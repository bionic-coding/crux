"""Optional token-overlap candidates never replace literal related-test selection."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("related_test_candidates_tool", SCRIPTS / "related-tests.py")
RELATED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELATED)


class ExtraCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.write("crux/scripts/tests/test_unrelated.py", "import json\n")

    def write(self, relative, text=""):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def gates(self, *names):
        rows = ["| Gate (output) | Scope | Dry-run command | Regenerator that fixes it |", "|---|---|---|---|"]
        for name in names:
            self.write("crux/scripts/" + name)
            rows.append(f"| output | plugin-authoring | `{name} --dry-run` | `{name}` |")
        self.write("crux/skills/check-drift/SKILL.md", "\n".join(rows) + "\n")

    def test_extras_are_additive_and_exclude_every_literal_test_match(self):
        self.write("crux/scripts/tests/test_cycle_required.py", "import cycle_workflow\n")
        self.write("crux/scripts/tests/test_cycle_recovery.py")
        paths = ["crux/scripts/cycle_workflow.py"]
        before = RELATED.related(self.root, paths)
        extra = RELATED.extra_candidates(self.root, paths)
        self.assertEqual([row["path"] for row in extra], ["crux/scripts/tests/test_cycle_recovery.py"])
        self.assertEqual(RELATED.related(self.root, paths), before)
        self.assertEqual(list(before["tests"]), ["crux/scripts/tests/test_cycle_required.py"])
        self.assertNotIn("extra_candidates", before)

    def test_order_ids_reasons_and_deduplication_do_not_depend_on_input_order(self):
        self.write("tools/tests/test_cycle_zebra.py")
        self.write("crux/scripts/tests/test_cycle_alpha.py")
        self.gates("generate-cycle-guide.py")
        changed = ["crux/scripts/cycle_workflow.py", "tools/cycle_helper.py"]
        first = RELATED.extra_candidates(self.root, changed)
        second = RELATED.extra_candidates(self.root, [changed[1], changed[0], changed[1]])
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first, key=lambda row: (row["path"], row["id"])))
        self.assertEqual(len(first), 3)
        self.assertEqual(len({row["id"] for row in first}), 3)
        self.assertEqual(len({row["path"] for row in first}), 3)
        for row in first:
            self.assertEqual(set(row), {"id", "path", "reason"})
            self.assertTrue(row["id"].endswith(row["path"]))
            self.assertIn("cycle", row["reason"])

    def test_module_reader_adds_its_drift_gate_without_changing_literal_hop_rule(self):
        self.gates("generate-micro-crux.py")
        self.write("crux/scripts/generate-micro-crux.py", "SOURCES = ('scripts/cycle_workflow.py',)\n")
        self.write("crux/scripts/tests/test_micro_crux_contracts.py")
        paths = ["crux/scripts/cycle_workflow.py"]
        self.assertEqual(RELATED.related(self.root, paths)["readers"], {})
        extras = RELATED.extra_candidates(self.root, paths)
        gate = next(row for row in extras if row["id"] == "drift:crux/scripts/generate-micro-crux.py")
        self.assertIn("micro", gate["reason"])
        self.assertIn("generate-micro-crux.py", gate["reason"])
        self.assertIn("crux/scripts/tests/test_micro_crux_contracts.py", [row["path"] for row in extras])

    def test_nonmodule_reader_literal_matches_remain_excluded(self):
        self.write("crux/scripts/generate-micro-crux.py", "TEMPLATE = 'micro-crux.md.tmpl'\n")
        self.write("crux/scripts/tests/test_required.py", "run('generate-micro-crux.py')\n")
        self.write("crux/scripts/tests/test_micro_sections.py")
        extra = RELATED.extra_candidates(self.root, ["crux/templates/micro-crux.md.tmpl"])
        self.assertEqual([row["path"] for row in extra], ["crux/scripts/tests/test_micro_sections.py"])

    def test_only_identifier_tokens_match_not_body_or_generic_test_words(self):
        self.write("crux/scripts/tests/test_unrelated.py", "# cycle workflow micro\n")
        self.write("crux/scripts/tests/test_cycler.py")
        self.gates("generate-unrelated.py")
        self.assertEqual(RELATED.extra_candidates(self.root, ["crux/scripts/cycle_workflow.py"]), [])

    def test_only_declared_existing_gates_and_direct_test_files_are_candidates(self):
        self.gates("generate-cycle-guide.py")
        self.write("crux/scripts/generate-cycle-undeclared.py")
        self.write("crux/scripts/tests/fixtures/test_cycle_fixture.py")
        self.write("tools/tests/test_cycle_case.py")
        extra = RELATED.extra_candidates(self.root, ["crux/scripts/cycle_workflow.py"])
        self.assertEqual({row["path"] for row in extra}, {
            "crux/scripts/generate-cycle-guide.py", "tools/tests/test_cycle_case.py"})
        for row in extra:
            self.assertFalse(Path(row["path"]).is_absolute())
            self.assertTrue((self.root / row["path"]).is_file())
            self.assertTrue((self.root / row["path"]).resolve().is_relative_to(self.root))

    def test_guard_table_is_read_but_prose_missing_scripts_and_traversal_are_ignored(self):
        self.write("crux/scripts/check-cycle-records.py")
        self.write("crux/scripts/check-cycle-prose.py")
        self.write("crux/skills/check-drift/SKILL.md", """Run `check-cycle-prose.py` someday.
| Guard | Scope | Command | What it answers |
|---|---|---|---|
| records | project | `check-cycle-records.py` | validity |
| missing | project | `check-cycle-missing.py` | absent |
| outside | project | `../check-cycle-outside.py` | unsafe |
""")
        self.assertEqual([row["path"] for row in RELATED.extra_candidates(self.root, ["cycle_data.py"])],
                         ["crux/scripts/check-cycle-records.py"])

    def test_absolute_changed_path_normalizes_and_outside_root_refuses(self):
        self.write("crux/scripts/tests/test_cycle_case.py")
        relative = "crux/scripts/cycle_workflow.py"
        self.assertEqual(RELATED.extra_candidates(self.root, [relative]),
                         RELATED.extra_candidates(self.root, [str(self.root / relative)]))
        with self.assertRaises(RELATED.EnvironmentProblem):
            RELATED.extra_candidates(self.root, ["../cycle_escape.py"])

    def test_empty_changes_return_nothing_and_candidate_files_are_never_executed(self):
        self.write("crux/scripts/tests/test_cycle_case.py", "raise RuntimeError('must not execute')\n")
        self.gates("generate-cycle-guide.py")
        self.write("crux/scripts/generate-cycle-guide.py", "raise RuntimeError('must not execute')\n")
        self.assertEqual(RELATED.extra_candidates(self.root, []), [])
        with mock.patch("subprocess.run", side_effect=AssertionError("no subprocess")):
            self.assertEqual(len(RELATED.extra_candidates(self.root, ["cycle_data.py"])), 2)

    def test_comment_only_reader_does_not_expand_optional_tokens(self):
        self.gates("generate-micro-crux.py")
        self.write("crux/scripts/generate-micro-crux.py", "# cycle_workflow.py is discussed here\n")
        self.write("crux/scripts/tests/test_micro_sections.py")
        self.assertEqual(RELATED.extra_candidates(self.root, ["cycle_workflow.py"]), [])

    def test_symlink_candidates_never_escape_the_repository(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "test_cycle_external.py"
            external.write_text("# no execution\n")
            (self.root / "crux/scripts/tests/test_cycle_external.py").symlink_to(external)
            self.assertEqual(RELATED.extra_candidates(self.root, ["cycle_workflow.py"]), [])

    def test_camel_case_identifiers_match_without_substring_matches(self):
        self.write("crux/scripts/tests/test_MicroSections.py")
        self.write("crux/scripts/tests/test_microscope.py")
        self.assertEqual([row["path"] for row in RELATED.extra_candidates(self.root, ["MicroReader.py"])],
                         ["crux/scripts/tests/test_MicroSections.py"])


if __name__ == "__main__":
    unittest.main()
