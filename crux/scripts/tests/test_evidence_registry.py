"""The registry of the four reused suites, the exclusion mechanism, and the bookkeeping rule."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence_fixtures import write_lock_project
import _dev_surface
from _dev_surface import REPO_ROOT, require_dev_surface
import suite_evidence
import test_evidence as te
from test_evidence import execute, lookup

CORE = "checkout:unittest:crux/scripts/tests:test*.py"
TOOLS = "checkout:unittest:tools/tests:test*.py"
STAGED = "staged:py{}:unittest:crux/scripts/tests:test*.py"


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")

    def test_the_four_suites_and_their_check_ids(self):
        declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
        self.assertEqual(sorted(declared), sorted([CORE, TOOLS, STAGED.format("3.13"), STAGED.format("3.14")]))

    def test_the_supported_minors_come_from_the_project_matrix(self):
        (self.root / "pyproject.toml").write_text((self.root / "pyproject.toml").read_text() + '\n[tool.crux]\npython-versions = ["3.13", "3.15"]\n')
        declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
        self.assertIn(STAGED.format("3.15"), declared)
        self.assertNotIn(STAGED.format("3.14"), declared)

    def test_requirements_by_suite(self):
        declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
        core, tools, staged = (te.normalize(declared[k])["requirement"] for k in (CORE, TOOLS, STAGED.format("3.14")))
        self.assertTrue(core["isolated"])
        self.assertEqual(core["packages"]["lock"]["project"], False)
        self.assertEqual(core["interpreter"]["minors"], ["3.13"])
        self.assertFalse(tools["isolated"])
        self.assertTrue(tools["packages"]["lock"]["project"])
        self.assertEqual(staged["interpreter"]["minors"], ["3.14"])
        self.assertEqual(staged["packages"]["lock"]["source"], "dev-root")
        self.assertTrue(staged["isolated"])
        self.assertEqual(staged["variables"]["PYTHONPATH"], "${REPOSITORY}/crux/scripts")
        self.assertIn("PYTHONDONTWRITEBYTECODE", staged["variables"])
        self.assertEqual(staged["flags"], {"dont_write_bytecode": 1})
        self.assertIn("git", core["tools"])
        self.assertIn("uv", core["tools"])

    def test_the_commands_omit_the_interpreter_path_and_scheduling_arguments(self):
        for declaration in suite_evidence.registered_declarations(self.root, dev_root=self.root).values():
            self.assertEqual(declaration["command"][0], "python")
            self.assertNotIn("--workers", declaration["command"])
        shared = te.canonical_command(["/some/venv/bin/python3.13", "crux/scripts/tests/parallel_suite.py", "crux/scripts/tests",
                                       "--pattern", "test*.py", "--workers", "8", "--records", "r.jsonl", "--timings", "t.json"])
        self.assertEqual(shared, ["python", "crux/scripts/tests/parallel_suite.py", "crux/scripts/tests", "--pattern", "test*.py"])
        other = te.canonical_command(["/elsewhere/python3", "crux/scripts/tests/parallel_suite.py", "crux/scripts/tests", "--pattern", "test*.py"])
        self.assertEqual(shared, other)

    def test_the_tester_and_the_release_ask_for_the_same_declaration(self):
        for scope, start, minor in (("checkout", "crux/scripts/tests", None), ("checkout", "tools/tests", None), ("staged", "crux/scripts/tests", "3.14")):
            declaration, registered = suite_evidence.declaration_for(scope, start, "test*.py", None, self.root, minor=minor, dev_root=self.root)
            self.assertTrue(registered)
            by_id = suite_evidence.registered_declaration(self.root, declaration["check_id"], dev_root=self.root)
            self.assertEqual(te.normalize(declaration), te.normalize(by_id))

    def test_a_focused_pattern_or_start_is_not_registered(self):
        declaration, registered = suite_evidence.declaration_for("checkout", "crux/scripts/tests", "test_one.py", None, self.root)
        self.assertFalse(registered)
        self.assertNotIn("requirement", declaration)
        self.assertEqual(declaration["environment"], [])
        _, registered = suite_evidence.declaration_for("checkout", "other/tests", "test*.py", None, self.root)
        self.assertFalse(registered)
        self.assertIsNone(suite_evidence.registered_declaration(self.root, "unit"))

    def test_the_registered_exclusions_are_the_cycle_records_and_the_bookkeeping_documents(self):
        # Every path here has no reader in either checkout suite: the live-read audit
        # (bionic/cycles/CYC-0016/evidence/build/b1-live-read-audit.md; for `queue`,
        # bionic/cycles/CYC-0036/evidence/build/live-read-audit.md) shows each test that opened
        # one now reads a fixture or a committed copy that omits them. Schemas, templates,
        # instruction files, decisions, observations, invariants, arch, research and briefs stay inputs.
        expected = ("cycles", "journal", "log.md", "inbox", "garden", "whats_next.md", "queue")
        self.assertEqual(suite_evidence.DOCS_EXCLUSIONS, expected)
        self.assertEqual(suite_evidence.runtime_exclusions(self.root), ["docs/" + name for name in expected])
        declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
        for check in (CORE, TOOLS):
            # The release exclusion follows the shared bookkeeping names; CHANGELOG.md is never listed here (P9).
            self.assertEqual(declared[check]["exclude_inputs"], ["docs/" + name for name in expected] + ["public"])
        for minor in ("3.13", "3.14"):
            self.assertEqual(declared[STAGED.format(minor)]["exclude_inputs"], ["CHANGELOG.md"])
        for kept in ("adrs", "observations", "invariants", "arch", "research", "briefs", "AGENTS.md", "manifest.yml"):
            self.assertNotIn(kept, suite_evidence.DOCS_EXCLUSIONS)

    def test_a_registration_can_add_more(self):
        with patch.object(suite_evidence, "DOCS_EXCLUSIONS", ("cycles", "journal", "log.md", "inbox")):
            declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)
            self.assertEqual(declared[CORE]["exclude_inputs"], ["docs/cycles", "docs/journal", "docs/log.md", "docs/inbox", "public"])
            self.assertEqual(declared[STAGED.format("3.13")]["exclude_inputs"], ["CHANGELOG.md"])


# Every registered exclusion and projection entry and the verdict of the release read audit that
# cleared it (bionic/cycles/CYC-0038/evidence/build/release-read-audit.md, section 1). A path joins the
# registry only with a cleared verdict, so the registry must equal this table exactly.
AUDIT_PROJECTIONS = {
    "checkout": {
        "crux/plugin.json": (["json-string:version"], "P1"),
        "crux/.claude-plugin/plugin.json": (["json-string:version"], "P1"),
        "crux/.codex-plugin/plugin.json": (["json-string:version"], "P1"),
        "crux-mods/.claude-plugin/plugin.json": (["json-string:version"], "P1"),
        "pyproject.toml": (["toml-project-version"], "P2"),
        "uv.lock": (["uv-lock-package-version:crux"], "P3"),
        "tools/bionic-catalog/crux-learning-catalog-guide.json": (["json-string:reviewed_plugin_version"], "P4"),
        "README.md": (["readme-footer-version"], "P5"),
    },
    "staged": {
        "crux/plugin.json": (["json-string:version"], "P1"),
        "crux/.claude-plugin/plugin.json": (["json-string:version"], "P1"),
        "crux/.codex-plugin/plugin.json": (["json-string:version"], "P1"),
        "crux-mods/.claude-plugin/plugin.json": (["json-string:version"], "P1"),
        ".generated": (["json-string:version"], "P6"),
        "README.md": (["generated-fingerprint-line", "readme-footer-version"], "P7, P8"),
    },
}
AUDIT_EXCLUSIONS = {"checkout": {"public": "P10"}, "staged": {"CHANGELOG.md": "P11"}}


class ReleaseNeutralRegistrationTests(unittest.TestCase):
    """The registered declarations carry the audited exclusions, projections and lock mode; nothing else does."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")
        self.declared = suite_evidence.registered_declarations(self.root, dev_root=self.root)

    def test_the_projections_are_exactly_the_audited_entries(self):
        for scope, checks in (("checkout", (CORE, TOOLS)), ("staged", (STAGED.format("3.13"), STAGED.format("3.14")))):
            expected = {path: kinds for path, (kinds, _verdict) in AUDIT_PROJECTIONS[scope].items()}
            for check in checks:
                self.assertEqual(self.declared[check]["input_projections"], expected, check)
                self.assertEqual(te.normalize(self.declared[check])["input_projections"],
                                 {path: sorted(kinds) for path, kinds in expected.items()}, check)

    def test_the_release_exclusions_are_exactly_the_audited_entries(self):
        for check in (CORE, TOOLS):
            added = [e for e in self.declared[check]["exclude_inputs"] if not e.startswith("docs/")]
            self.assertEqual(added, list(AUDIT_EXCLUSIONS["checkout"]), check)
            self.assertNotIn("CHANGELOG.md", self.declared[check]["exclude_inputs"])  # P9: stays an input
        for minor in ("3.13", "3.14"):
            self.assertEqual(self.declared[STAGED.format(minor)]["exclude_inputs"], list(AUDIT_EXCLUSIONS["staged"]))

    def test_a_projected_path_is_never_excluded(self):
        for check, declaration in self.declared.items():
            for path in declaration["input_projections"]:
                self.assertNotIn(path, declaration["exclude_inputs"], check)

    def test_only_the_readme_projects_a_footer_version(self):
        # Nit 3: the footer locator belongs to the README alone, in the checkout and in the stage.
        for scope in ("checkout", "staged"):
            holders = [p for p, (kinds, _v) in AUDIT_PROJECTIONS[scope].items() if "readme-footer-version" in kinds]
            self.assertEqual(holders, ["README.md"], scope)
        for check, declaration in self.declared.items():
            holders = [p for p, kinds in declaration["input_projections"].items() if "readme-footer-version" in kinds]
            self.assertEqual(holders, ["README.md"], check)

    def test_only_the_tools_suite_is_release_neutral(self):
        lock = {check: te.normalize(d)["requirement"]["packages"]["lock"] for check, d in self.declared.items()}
        self.assertEqual(lock[TOOLS]["project_version"], "release-neutral")
        self.assertTrue(lock[TOOLS]["project"])
        for check, found in lock.items():
            if check != TOOLS:
                self.assertNotIn("project_version", found, check)
                self.assertFalse(found["project"], check)

    def test_a_focused_run_carries_neither_field(self):
        declaration, registered = suite_evidence.declaration_for("checkout", "crux/scripts/tests", "test_one.py", None, self.root)
        self.assertFalse(registered)
        self.assertNotIn("input_projections", declaration)
        self.assertEqual(declaration["exclude_inputs"], suite_evidence.runtime_exclusions(self.root))
        declaration, registered = suite_evidence.declaration_for("staged", "crux/scripts/tests", "test_one.py", None, self.root, minor="3.13")
        self.assertFalse(registered)
        self.assertNotIn("input_projections", declaration)
        self.assertEqual(declaration["exclude_inputs"], [])

    def test_the_registered_declaration_matches_what_the_tester_asks_for(self):
        declaration, registered = suite_evidence.declaration_for("checkout", "tools/tests", "test*.py", None, self.root, dev_root=self.root)
        self.assertTrue(registered)
        self.assertEqual(te.normalize(declaration), te.normalize(self.declared[TOOLS]))
        self.assertIn("input_projections", declaration)

    def test_a_release_only_change_keeps_a_checkout_fingerprint_and_a_changelog_change_does_not(self):
        # Registry-side demonstration on a throwaway project: the projected version spans and `public/`
        # leave the fingerprint alone; CHANGELOG.md, which stays an input of the checkout suites, moves it.
        def vcs(*args):
            subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],
                           cwd=self.root, capture_output=True, check=True)
        footer = "body\n\nMIT licensed (see [LICENSE](./LICENSE)). v{}\n"
        for rel, text in (("crux/plugin.json", '{"version": "1.2.3", "name": "x"}\n'), ("CHANGELOG.md", "# Changelog\n"),
                          ("public/README.md", "public\n"), ("README.md", footer.format("1.2.3"))):
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text)
        vcs("init", "-q")
        vcs("add", "-A")
        vcs("commit", "-qm", "base")

        def fingerprint():
            declaration = suite_evidence.registered_declaration(self.root, CORE, dev_root=self.root)
            return te.snapshot(self.root, declaration, source_root=self.root)["fingerprint"]
        before = fingerprint()
        (self.root / "crux/plugin.json").write_text('{"version": "9.9.9", "name": "x"}\n')
        (self.root / "README.md").write_text(footer.format("9.9.9"))
        (self.root / "public/README.md").write_text("regenerated\n")
        self.assertEqual(fingerprint(), before)
        (self.root / "crux/plugin.json").write_text('{"version": "9.9.9", "name": "renamed"}\n')
        self.assertNotEqual(fingerprint(), before)
        (self.root / "crux/plugin.json").write_text('{"version": "9.9.9", "name": "x"}\n')
        self.assertEqual(fingerprint(), before)
        (self.root / "CHANGELOG.md").write_text("# Changelog\n\n## 9.9.9\n")
        self.assertNotEqual(fingerprint(), before)


class ReleaseMetadataPresetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "tools").mkdir()
        (self.root / "tools/release-preflight.py").write_text("")

    def test_the_preset_runs_the_metadata_check_over_the_broad_inputs(self):
        declaration = suite_evidence.preset_declaration(self.root, "release-metadata", "metadata-check")
        self.assertEqual(declaration["command"], ["python", "tools/release-preflight.py", "--metadata"])
        self.assertEqual(declaration["inputs"], suite_evidence.INPUTS)
        self.assertEqual(declaration["exclude_inputs"], suite_evidence.runtime_exclusions(self.root))
        self.assertNotIn("input_projections", declaration)
        self.assertEqual(declaration["requirement"], {"tools": ["uv"]})
        self.assertTrue(declaration["git_tracked"])

    def test_the_preset_refuses_where_the_script_is_absent(self):
        (self.root / "tools/release-preflight.py").unlink()
        with self.assertRaises(te.EvidenceError) as raised:
            suite_evidence.preset_declaration(self.root, "release-metadata", "metadata-check")
        self.assertIn("not applicable", str(raised.exception))

    def test_no_preset_carries_a_release_exclusion_or_projection(self):
        for spec in suite_evidence.PRESETS.values():
            if spec["script"]:
                (self.root / spec["script"]).parent.mkdir(parents=True, exist_ok=True)
                (self.root / spec["script"]).write_text("")
        for preset, spec in suite_evidence.PRESETS.items():
            with self.subTest(preset=preset):
                declaration = suite_evidence.preset_declaration(
                    self.root, preset, "c", command=["python", "x.py"] if spec["command"] is None else None)
                self.assertNotIn("input_projections", declaration)
                for release in (*suite_evidence.RELEASE_EXCLUSIONS["checkout"], *suite_evidence.RELEASE_EXCLUSIONS["staged"]):
                    self.assertNotIn(release, declaration["exclude_inputs"])
                lock = (declaration.get("requirement") or {}).get("packages", {}).get("lock", {})
                self.assertNotIn("project_version", lock)


def _stage(testcase):
    """A staged tree: this run's own stage when the suite runs inside one, else a fresh one from the checkout."""
    if _dev_surface.IS_STAGED_ARTIFACT:
        return REPO_ROOT
    require_dev_surface(testcase, REPO_ROOT / "tools/sync_stage.py", "tools/sync_stage.py")
    holder = tempfile.TemporaryDirectory()
    testcase.addCleanup(holder.cleanup)
    version = json.loads((REPO_ROOT / "crux/plugin.json").read_text())["version"]
    stage = Path(holder.name) / "stage"
    subprocess.run([sys.executable, str(REPO_ROOT / "tools/sync_stage.py"), "stage", "--dev-root", str(REPO_ROOT),
                    "--stage-dir", str(stage), "--version", version], check=True, capture_output=True)
    return stage


class LiveProjectionShapeTests(unittest.TestCase):
    """Each registered projection locates exactly one span in the file as it stands (Nit 4).

    These assert the shape the audit classed as invariant: exactly one span located with its strict
    format held, so a projection never falls back to the raw digest on a real file. They assert no
    version value.
    """

    def assert_projects(self, root, scope, path):
        kinds, _verdict = AUDIT_PROJECTIONS[scope][path]
        data = (root / path).read_bytes()
        text = data.decode("utf-8")
        for kind in kinds:
            self.assertIsNotNone(te._locate(text, kind), f"{kind} locates no single span in {path}")
        projected = te.projected_digest(data, kinds)
        self.assertIsNotNone(projected, f"{path} falls back to the raw digest")
        self.assertNotEqual(projected, te.input_digest(data))

    def test_each_checkout_entry_locates_one_span_in_the_live_file(self):
        for path in AUDIT_PROJECTIONS["checkout"]:
            with self.subTest(path=path):
                if path == "README.md" and _dev_surface.IS_STAGED_ARTIFACT:
                    self.skipTest("the staged README.md is the public rendition; the staged-scope test covers it")
                require_dev_surface(self, REPO_ROOT / path, path)
                self.assert_projects(REPO_ROOT, "checkout", path)

    def test_reviewed_plugin_version_is_a_top_level_key(self):
        path = REPO_ROOT / "tools/bionic-catalog/crux-learning-catalog-guide.json"
        require_dev_surface(self, path, "tools/bionic-catalog/crux-learning-catalog-guide.json")
        text = path.read_text(encoding="utf-8")
        self.assertIsInstance(json.loads(text).get("reviewed_plugin_version"), str)
        self.assertEqual(len(re.findall(r'"reviewed_plugin_version"', text)), 1)

    def test_each_staged_entry_locates_one_span_in_a_real_stage(self):
        stage = _stage(self)
        for path in AUDIT_PROJECTIONS["staged"]:
            with self.subTest(path=path):
                self.assertTrue((stage / path).is_file(), f"{path} is absent from the stage")
                self.assert_projects(stage, "staged", path)

    def test_the_staged_readme_holds_both_spans_disjointly(self):
        stage = _stage(self)
        text = (stage / "README.md").read_text(encoding="utf-8")
        line, footer = te._locate(text, "generated-fingerprint-line"), te._locate(text, "readme-footer-version")
        self.assertEqual(line[0], 0)
        self.assertLessEqual(line[1], footer[0])


class BookkeepingTests(unittest.TestCase):
    """With an exclusion registered, edits under the excluded paths leave receipts valid."""

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args], cwd=self.root, capture_output=True, check=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        patcher = patch.dict(os.environ, {"CRUX_TEST_EVIDENCE_STORE": str(self.root / ".evidence-store")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.git("init", "-q")
        (self.root / ".gitignore").write_text(".evidence-store/\n")
        (self.root / "bionic/journal").mkdir(parents=True)
        (self.root / "bionic/inbox").mkdir()
        (self.root / "bionic/cycles/CYC-0001").mkdir(parents=True)
        (self.root / "bionic/manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
        (self.root / "bionic/journal/2026-10.md").write_text("entry\n")
        (self.root / "bionic/log.md").write_text("log\n")
        (self.root / "bionic/inbox/note.md").write_text("note\n")
        (self.root / "bionic/cycles/CYC-0001/cycle.json").write_text("{}\n")
        (self.root / "src").mkdir()
        (self.root / "src/a.txt").write_text("source\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def declaration(self):
        return {"check_id": "bookkeeping", "command": [sys.executable, "-c", "print('ok')"], "inputs": ["src", "bionic"],
                "environment": [], "git_tracked": True,
                "exclude_inputs": suite_evidence.runtime_exclusions(self.root)}

    def test_edits_under_excluded_paths_leave_receipts_valid_and_a_source_edit_invalidates_them(self):
        with patch.object(suite_evidence, "DOCS_EXCLUSIONS", ("cycles", "journal", "log.md", "inbox")):
            declaration = self.declaration()
            first = execute(self.root, declaration)["evidence"]
            # Uncommitted additions and modifications.
            (self.root / "bionic/journal/2026-10.md").write_text("entry\nmore\n")
            (self.root / "bionic/journal/2026-11.md").write_text("new month\n")
            (self.root / "bionic/log.md").write_text("log\nline\n")
            (self.root / "bionic/inbox/second.md").write_text("another\n")
            (self.root / "bionic/cycles/CYC-0001/cycle.json").write_text('{"changed": true}\n')
            (self.root / "bionic/cycles/CYC-0002").mkdir()
            (self.root / "bionic/cycles/CYC-0002/cycle.json").write_text("{}\n")
            self.assertEqual(lookup(self.root, declaration)["record"]["id"], first["id"])
            # The same edits, committed.
            self.git("add", "-A")
            self.git("commit", "-qm", "journal and cycle records")
            again = execute(self.root, declaration)
            self.assertEqual((again["action"], again["evidence"]["id"]), ("reused", first["id"]))
            # A source edit invalidates, committed or not.
            (self.root / "src/a.txt").write_text("source changed\n")
            self.assertEqual(lookup(self.root, declaration)["state"], "inputs-changed")
            self.git("add", "-A")
            self.git("commit", "-qm", "source")
            self.assertEqual(lookup(self.root, declaration)["state"], "inputs-changed")

    def test_without_the_exclusion_the_same_journal_edit_invalidates(self):
        with patch.object(suite_evidence, "DOCS_EXCLUSIONS", ("cycles",)):
            declaration = self.declaration()
        self.assertEqual(declaration["exclude_inputs"], ["bionic/cycles"])
        first = execute(self.root, declaration)["evidence"]
        (self.root / "bionic/journal/2026-10.md").write_text("entry\nmore\n")
        self.assertEqual(lookup(self.root, declaration)["state"], "inputs-changed")
        self.assertEqual(first["status"], "passed")


class RegisteredBookkeepingTests(unittest.TestCase):
    """The registered checkout declarations, as registered: a bookkeeping commit leaves the
    suite's input fingerprint unchanged, and any other tracked file moves it."""

    BOOKKEEPING = ("bionic/journal/2026-10.md", "bionic/log.md", "bionic/inbox/note.md",
                   "bionic/garden/2026-10-01.md", "bionic/whats_next.md", "bionic/queue/cycles.yaml",
                   "bionic/cycles/CYC-0001/cycle.json")
    INPUTS = ("bionic/adrs/ADR-0001-x.md", "bionic/AGENTS.md", "bionic/manifest.yml",
              "bionic/observations/OBS-0001-x.md", "bionic/invariants/INV-0001.md",
              "bionic/arch/overview.md", "bionic/research/note.md", "bionic/briefs/BRIEF-x.md",
              "crux/scripts/tool.py", "tools/helper.py")

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@example.invalid", *args],
                              cwd=self.root, capture_output=True, check=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        write_lock_project(self.root)
        (self.root / ".python-version").write_text("3.13\n")
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
        self.git("init", "-q")
        for rel in (*self.BOOKKEEPING, *self.INPUTS):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")

    def fingerprint(self, check):
        declaration = suite_evidence.registered_declaration(self.root, check, dev_root=self.root)
        return te.snapshot(self.root, declaration, source_root=self.root)["fingerprint"]

    def test_a_bookkeeping_edit_leaves_both_checkout_suites_fingerprints_unchanged(self):
        before = {check: self.fingerprint(check) for check in (CORE, TOOLS)}
        for rel in self.BOOKKEEPING:
            (self.root / rel).write_text("original\nappended\n")
        (self.root / "bionic/journal/2026-11.md").write_text("a new month\n")
        (self.root / "bionic/inbox/second.md").write_text("another\n")
        (self.root / "bionic/cycles/CYC-0002").mkdir()
        (self.root / "bionic/cycles/CYC-0002/cycle.json").write_text("{}\n")
        for check in (CORE, TOOLS):
            self.assertEqual(self.fingerprint(check), before[check], check)
        # The same edits, committed.
        self.git("add", "-A")
        self.git("commit", "-qm", "bookkeeping")
        for check in (CORE, TOOLS):
            self.assertEqual(self.fingerprint(check), before[check], check)

    def test_an_edit_to_any_other_tracked_file_changes_the_fingerprint(self):
        # POSITIVE DISCRIMINATOR: the equality above is a measurement, because each of these
        # moves the same fingerprint.
        for rel in self.INPUTS:
            with self.subTest(path=rel):
                before = self.fingerprint(CORE)
                (self.root / rel).write_text("changed\n")
                self.assertNotEqual(self.fingerprint(CORE), before)
                self.assertNotEqual(self.fingerprint(TOOLS), before)
                (self.root / rel).write_text("original\n")
                self.assertEqual(self.fingerprint(CORE), before)


if __name__ == "__main__":
    unittest.main()
