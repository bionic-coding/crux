"""No guide, skill, agent or template tells the conductor to commit the council record.

The council runner commits its own attempt record and its council record, so a
sentence such as "Commit each council record before you advance." is stale. The scan
collapses every run of whitespace, newlines and markdown line wraps included, to one
space, so a wrapped sentence cannot hide. It covers:

* `crux/skills/**/references/*.md` and `crux/skills/**/SKILL.md`
* every text file under `crux/templates/`
* `crux/agents/*.md`
* every repo-root `*.md` guide except `CHANGELOG.md`, whose dated entries record what
  earlier releases told the conductor.

The repo-root files are dev-only surfaces; their cases skip in the staged artifact
(`require_dev_surface`) and the `crux/` cases keep running there.
"""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

from _dev_surface import REPO_ROOT, require_dev_surface

# live-changelog-read: released-sections-only
# This file reads CHANGELOG.md only through release_section(), which selects a released version heading.

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import suite_evidence  # noqa: E402

# Copied from test_adr_path_templates.py (class CouncilRunnerRoundRuleTests,
# CONDUCTOR_COMMIT_COUNCIL), which owns the pattern; keep the two in step.
CONDUCTOR_COMMIT_COUNCIL = re.compile(
    r"\b[Cc]ommit (?:the|each|every|this|both) (?:new )?(?:council|attempt) records?\b")

CRUX = REPO_ROOT / "crux"
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".tmpl", ".txt", ".json"}


def norm(text: str) -> str:
    """Collapse every run of whitespace, line wraps included, to one space."""
    return re.sub(r"\s+", " ", text)


def hits(text: str) -> list[str]:
    return [m.group(0) for m in CONDUCTOR_COMMIT_COUNCIL.finditer(norm(text))]


def crux_files() -> list[Path]:
    found = set(CRUX.glob("skills/**/references/*.md"))
    found |= set(CRUX.glob("skills/**/SKILL.md"))
    found |= {p for p in (CRUX / "templates").rglob("*")
              if p.is_file() and p.suffix in TEXT_SUFFIXES}
    found |= set(CRUX.glob("agents/*.md"))
    return sorted(found)


def root_guides(root: Path = REPO_ROOT) -> list[Path]:
    """The repo-root guides. A file `.bionic.yml` configures as bookkeeping is a note, not a guide."""
    notes = {Path(entry) for entry in suite_evidence.bookkeeping_paths(root)}
    return sorted(p for p in root.glob("*.md")
                  if p.name != "CHANGELOG.md" and p.relative_to(root) not in notes)


class RootGuideSelectionTests(unittest.TestCase):
    """Configured bookkeeping files are notes, so the guide scan skips them (CYC-0036)."""

    def make(self, tmp, config):
        root = Path(tmp)
        for name in ("CODEX.md", "crux-authority-reset.md", "crux-implementation-evidence.md", "CHANGELOG.md", "notes.txt"):
            (root / name).write_text("text\n", encoding="utf-8")
        (root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n' + config, encoding="utf-8")
        return root

    def test_a_configured_bookkeeping_file_is_not_a_guide_and_an_unconfigured_one_is(self):
        config = ("evidence:\n  bookkeeping_paths:\n    - crux-authority-reset.md\n"
                  "    - crux-implementation-evidence.md\n")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([p.name for p in root_guides(self.make(tmp, config))], ["CODEX.md"])
        # POSITIVE DISCRIMINATOR: with nothing configured the same files are guides, so the
        # skip above is the setting's doing.
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([p.name for p in root_guides(self.make(tmp, ""))],
                             ["CODEX.md", "crux-authority-reset.md", "crux-implementation-evidence.md"])

    def test_this_checkouts_guides_skip_the_configured_notes_and_keep_the_rest(self):
        require_dev_surface(self, REPO_ROOT / "CODEX.md", "CODEX.md")
        require_dev_surface(self, REPO_ROOT / "AGENTS.md", "AGENTS.md")
        names = {p.name for p in root_guides()}
        self.assertTrue({"CODEX.md", "AGENTS.md"} <= names)
        self.assertFalse(names & set(suite_evidence.bookkeeping_paths(REPO_ROOT)))


class ScanControlTests(unittest.TestCase):

    def test_a_sentence_wrapped_across_lines_is_caught(self):
        self.assertEqual(hits("Commit each council\nrecord before you advance."),
                         ["Commit each council record"])
        self.assertEqual(hits("and then commit the\n  attempt records first"),
                         ["commit the attempt records"])

    def test_the_three_original_sentences_are_caught(self):
        for sentence in ("Commit each council record before you advance.",
                         "Commit each council record before you advance. The gate check refuses",
                         "Before a run's next gate prompt, store the key. Commit each council record before you advance."):
            with self.subTest(sentence=sentence):
                self.assertEqual(len(hits(sentence)), 1)

    def test_benign_sentences_are_not_caught(self):
        for fine in ("Commit the refutation record before the advance.",
                     "Commit both records before the advance.",
                     "The council runner commits its council record itself.",
                     "Do not commit either record by hand."):
            with self.subTest(fine=fine):
                self.assertEqual(hits(fine), [])


class ConductorCommitRuleTests(unittest.TestCase):

    def test_the_scan_reads_files(self):
        self.assertGreater(len(crux_files()), 50)

    def test_no_shipped_surface_tells_the_conductor_to_commit_the_council_record(self):
        stale = {str(p.relative_to(REPO_ROOT)): hits(p.read_text(encoding="utf-8"))
                 for p in crux_files()}
        self.assertEqual({k: v for k, v in stale.items() if v}, {})

    def test_no_repo_root_guide_tells_the_conductor_to_commit_the_council_record(self):
        require_dev_surface(self, REPO_ROOT / "CODEX.md", "CODEX.md")
        guides = root_guides()
        self.assertIn("CODEX.md", {p.name for p in guides})
        stale = {p.name: hits(p.read_text(encoding="utf-8")) for p in guides}
        self.assertEqual({k: v for k, v in stale.items() if v}, {})

    def test_neither_the_trees_instruction_file_nor_the_opencode_agents_tell_the_conductor_to(self):
        """`bionic/AGENTS.md` mirrors the AGENTS template for this repository's own runs, and
        `opencode/agents/` projects the agent definitions; a conductor reads both. Positive
        control: each file names the council runner, so the scan read real text."""
        tree_file = REPO_ROOT / "bionic" / "AGENTS.md"
        require_dev_surface(self, tree_file, "bionic/AGENTS.md")
        files = [tree_file, *sorted((REPO_ROOT / "opencode" / "agents").glob("*.md"))]
        self.assertGreater(len(files), 5)
        self.assertIn("council runner", tree_file.read_text(encoding="utf-8"))
        stale = {str(p.relative_to(REPO_ROOT)): hits(p.read_text(encoding="utf-8")) for p in files}
        self.assertEqual({k: v for k, v in stale.items() if v}, {})


# A sentence that sends a council runner exit 2 to recovery. Each must name the owner's remedy
# (a `timeout` or moved work: restore the set-aside work, then a stale `index.lock`) before its
# first recovery step, so the conductor's one next step after such an exit 2 is the owner stop.
EXIT2_TRIGGER = re.compile(r"\b(?:When the council runner exits 2|When it exits 2|[Oo]n exit 2)\b")
RECOVERY_STEP = re.compile(r"process check|--recover|\bruns? recovery\b")
#: How far after a trigger its recovery step may sit and still belong to it.
EXIT2_WINDOW = 700
#: The surfaces that route a council runner exit 2 in their own words. The scan must check at
#: least one trigger in each, so a reworded trigger cannot make the check vacuous.
EXIT2_SURFACES = ("CODEX.md", "OPENCODE.md", "OPENCODE_GUIDE.md", "USER_GUIDE.md", "bionic/AGENTS.md",
                  "crux/templates/AGENTS.md.tmpl", "crux/templates/USER_GUIDE.md",
                  "crux/skills/install-docs-skills/references/install-and-upgrade.md")


def exit2_sites(text: str) -> list[tuple[str, bool]]:
    """Each trigger with a recovery step in its window, and whether the owner's remedy comes first."""
    t = norm(text)
    out = []
    for m in EXIT2_TRIGGER.finditer(t):
        r = RECOVERY_STEP.search(t, m.end(), m.end() + EXIT2_WINDOW)
        if r is None:
            continue
        between = t[m.start():r.start()]
        out.append((t[m.start():m.start() + 100], "`timeout`" in between and "index.lock" in between))
    return out


class Exit2RemedyOrderTests(unittest.TestCase):
    """After a council runner exit 2 whose stderr names `timeout` or moved work, every harness's
    guidance gives one next step: the owner's remedy, then recovery. The root guides (`CODEX.md`,
    `OPENCODE.md`, `OPENCODE_GUIDE.md`) and the user guides are pinned with the shipped surfaces."""

    def surfaces(self) -> dict[str, str]:
        require_dev_surface(self, REPO_ROOT / "CODEX.md", "CODEX.md")
        require_dev_surface(self, REPO_ROOT / "bionic" / "AGENTS.md", "bionic/AGENTS.md")
        files = set(crux_files()) | set(root_guides()) | {REPO_ROOT / "bionic" / "AGENTS.md"}
        files |= set((REPO_ROOT / "opencode" / "agents").glob("*.md"))
        return {str(p.relative_to(REPO_ROOT)): p.read_text(encoding="utf-8") for p in sorted(files)}

    def test_every_exit_2_route_names_the_owners_remedy_before_recovery(self):
        texts = self.surfaces()
        late = {name: [s for s, ok in exit2_sites(text) if not ok] for name, text in texts.items()}
        self.assertEqual({k: v for k, v in late.items() if v}, {})
        for name in EXIT2_SURFACES:
            with self.subTest(surface=name):
                self.assertTrue(exit2_sites(texts[name]), "no exit-2 route checked, so nothing was")

    def test_control_the_order_check_reports_recovery_before_the_remedy(self):
        old = ("When the council runner exits 2 or leaves an open attempt, run the process check. "
               "A slow hook times out; restore the stash, then remove a stale `.git/index.lock`.")
        self.assertEqual([ok for _s, ok in exit2_sites(old)], [False])
        good = ("On exit 2 whose stderr names `timeout`, the owner restores the set-aside work and removes "
                "a stale `index.lock`. Then, and on every other exit 2, run the process check.")
        self.assertEqual([ok for _s, ok in exit2_sites(good)], [True])
        self.assertEqual(exit2_sites("On exit 2 (absent key), stop."), [])


def cycle_section(text: str) -> str:
    """The cycle workflow section: from its heading to the line that closes it."""
    start = text.index("## 11.E. Current cycle workflow")
    end_marker = "Historical records remain readable, with their original authority and evidence."
    return text[start:text.index(end_marker, start) + len(end_marker)]


class CycleWorkflowDocsTests(unittest.TestCase):
    """The user and operator documents describe the typed-operation cycle model.

    Code owns the cycle procedure, so the instructions state outcomes, the typed
    operations and the stated limits, and no longer carry the manual bookkeeping sequence.
    """

    def read(self, name: str) -> str:
        path = REPO_ROOT / name
        require_dev_surface(self, path, name)
        return norm(path.read_text(encoding="utf-8"))

    def twins(self) -> dict[str, str]:
        tree = REPO_ROOT / "bionic" / "AGENTS.md"
        template = CRUX / "templates" / "AGENTS.md.tmpl"
        require_dev_surface(self, tree, "bionic/AGENTS.md")
        return {"bionic/AGENTS.md": cycle_section(tree.read_text(encoding="utf-8")),
                "AGENTS.md.tmpl": cycle_section(template.read_text(encoding="utf-8"))}

    def test_the_instruction_file_and_its_template_carry_the_same_cycle_section(self):
        texts = self.twins()
        self.assertEqual(texts["bionic/AGENTS.md"], texts["AGENTS.md.tmpl"])

    def test_the_cycle_section_states_the_typed_operation_model(self):
        for name, text in self.twins().items():
            flat = norm(text)
            for needle in ("run `inspect`, then the action it returns", "cycle.py op",
                           "prepare-dispatch", "attach-execution", "deliver", "mark-lost",
                           "owner-exception", "needs-upgrade", "version-3",
                           "unverified", "three attempts", "uncapped"):
                with self.subTest(surface=name, needle=needle):
                    self.assertIn(needle, flat)

    def test_the_cycle_section_drops_the_manual_bookkeeping_sequence(self):
        for name, text in self.twins().items():
            flat = norm(text)
            for stale in ("Each dispatcher runs `handoff`", "Do not bypass these leads",
                          "records an `assignment` running before each dispatch"):
                with self.subTest(surface=name, stale=stale):
                    self.assertNotIn(stale, flat)

    def test_the_cycle_section_keeps_the_rules_the_decisions_retain(self):
        for name, text in self.twins().items():
            flat = norm(text)
            for kept in ("Maximum passes", "**Fix step.**", "independent review", "owner's own words",
                         "Historical records remain readable", "contradicted premise"):
                with self.subTest(surface=name, kept=kept):
                    self.assertIn(kept, flat)

    def test_the_root_instruction_file_points_at_inspect_and_keeps_the_temporary_authorization(self):
        flat = self.read("AGENTS.md")
        self.assertIn("## Temporary authorization: cycle workflow replacement", flat)
        autonomy = flat[flat.index("### Cycle execution autonomy"):]
        autonomy = autonomy[:autonomy.index("## Historical authority preservation")]
        self.assertIn("run `inspect`", autonomy)

    def test_the_user_guide_states_hosts_limits_recovery_and_rollback(self):
        flat = self.read("USER_GUIDE.md")
        for needle in ("typed operations", "Claude Code", "Codex", "OpenCode", "OMP", "unverified",
                       "three attempts", "uncapped", "mark-lost", "v2-cycle.json",
                       "refuses version-3 records", "not authoritative"):
            with self.subTest(needle=needle):
                self.assertIn(needle, flat)

    def test_the_host_guides_and_deploy_runbook_state_their_part(self):
        for name, needles in {
            "OPENCODE_GUIDE.md": ("Result-End", "background"),
            "OMP_GUIDE.md": ("Result-End", "task"),
            "DEPLOY.md": ("v2-cycle.json", "version-3"),
        }.items():
            flat = self.read(name)
            for needle in needles:
                with self.subTest(guide=name, needle=needle):
                    self.assertIn(needle, flat)

    def raw_changelog(self) -> str:
        path = REPO_ROOT / "CHANGELOG.md"
        require_dev_surface(self, path, "CHANGELOG.md")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def release_section(changelog: str, version: str) -> str:
        """The `## [<version>]` section of a released version, never the live Unreleased section."""
        for section in re.split(r"(?m)^(?=## \[)", changelog):
            if section.startswith(f"## [{version}]"):
                return section
        raise AssertionError(f"no changelog section for {version}")

    def assert_names_the_cycle_workflow_change(self, changelog: str) -> None:
        section = self.release_section(changelog, "5.0.0").lower()
        for needle in ("typed cycle operations", "version-3", "v2-cycle.json"):
            with self.subTest(needle=needle):
                self.assertIn(needle, section)

    def test_the_5_0_0_changelog_states_the_classifier_release_facts(self):
        section = self.release_section(self.raw_changelog(), "5.0.0").lower()
        for label, needle in (
                ("the opt-out", "decisions: {classifier: off}"),
                ("councils still send under the opt-out", "councils still send"),
                ("no zero-data-retention preference", "does not send the zero-data-retention preference"),
                ("the Codex sandbox note", "codex's default workspace-write sandbox"),
                ("no spend cap", "no spend cap")):
            with self.subTest(fact=label):
                self.assertIn(needle, section)

    def test_the_5_0_0_changelog_names_the_cycle_workflow_change(self):
        self.assert_names_the_cycle_workflow_change(self.raw_changelog())

    def test_the_check_ignores_whatever_the_live_unreleased_section_holds(self):
        released = self.release_section(self.raw_changelog(), "5.0.0")
        for label, unreleased in (("empty", ""), ("populated", "### Changed\n\n- Unrelated entry.\n\n")):
            with self.subTest(unreleased=label):
                fixture = f"# Changelog\n\n## [Unreleased]\n\n{unreleased}{released}"
                self.assert_names_the_cycle_workflow_change(fixture)


if __name__ == "__main__":
    unittest.main()
