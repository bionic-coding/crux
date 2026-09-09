"""init-docs defaults new repos to schema 5 + invariants.

Attribution split: the seven-concern / no-"six concerns" framing bar is
ADR-0053 criterion 4; the schema_version "5" + bionic/ tree unification is
ADR-0059 (ADR-0053 specified "4"; it predates the unification).
`TestInitDocsSkillProse` asserts the `init-docs` SKILL.md prose matches the
shipped templates rather than a hardcoded version literal, and carries no
obsolete v4 current-layout wording. No third-party deps beyond PyYAML
(for the manifest + bionic-yml templates).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES = REPO_ROOT / "crux" / "templates"

try:
    from ._dev_surface import TREE, TREE_CLAUDE_MD, require_dev_surface
except ImportError:  # unittest discover imports test modules top-level
    from _dev_surface import TREE, TREE_CLAUDE_MD, require_dev_surface

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

SEVEN = {"code", "research", "adrs", "briefs", "journal", "promptbooks", "invariants"}


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class ManifestTemplateTests(unittest.TestCase):
    def test_manifest_tmpl_is_v5_seven_concerns_plus_arch_and_observations(self):
        m = yaml.safe_load((TEMPLATES / "manifest.yml.tmpl").read_text())
        self.assertEqual(m["schema_version"], "5")
        self.assertEqual(set(m["concerns_enabled"]), SEVEN | {"arch", "observations"})

    def test_manifest_tmpl_carries_observation_counter_without_schema_bump(self):
        # Additive enablement on the arch precedent: the counters arrive with
        # NO schema_version bump (docs/CLAUDE.md §17, §17.5). init-docs step 6
        # copies this template VERBATIM, so this block IS a fresh tree's
        # `observation` block — the survey keys are absent from a new repo
        # unless they are seeded here.
        m = yaml.safe_load((TEMPLATES / "manifest.yml.tmpl").read_text())
        self.assertEqual(m["observation"], {"next_number": 1, "stale_days": 90,
                                            "next_survey_number": 1,
                                            "survey_stub_days": 1})
        self.assertEqual(m["schema_version"], "5")
        self.assertEqual(m["adr"], {"next_number": 1})
        self.assertEqual(m["promptbook"], {"next_number": 1})

    def test_manifest_tmpl_agrees_with_claude_md_tmpl(self):
        # Twin lock-step: the CLAUDE.md.tmpl §7 example manifest must show the
        # same schema + include invariants, so a fresh seed is self-consistent.
        c = (TEMPLATES / "CLAUDE.md.tmpl").read_text()
        self.assertIn('schema_version: "5"', c)
        self.assertRegex(c, r"concerns_enabled:[\s\S]{0,400}- invariants")
        self.assertRegex(c, r"concerns_enabled:[\s\S]{0,400}- arch")

    def test_manifest_tmpl_observation_block_matches_claude_md_tmpl_section_7(self):
        # The gap that shipped the survey keys to the dogfood tree but not to a
        # fresh one: §7 of the CLAUDE.md written INTO a new tree documents the
        # `observation` keys, and nothing compared that list against the
        # manifest init-docs actually writes. Every key §7 documents must exist
        # in the template, or a fresh repo reads a schema doc describing a
        # manifest it does not have.
        m = yaml.safe_load((TEMPLATES / "manifest.yml.tmpl").read_text())
        c = (TEMPLATES / "CLAUDE.md.tmpl").read_text()
        block = re.search(r"\nobservation:.*?\n\n", c, re.DOTALL)
        self.assertIsNotNone(block, "no `observation:` block in CLAUDE.md.tmpl §7")
        documented = set(re.findall(r"^  ([a-z_]+):", block.group(0), re.MULTILINE))
        # Positive control: §7 must actually document keys, so an empty match
        # cannot make the subset assertion below vacuously true.
        self.assertIn("next_number", documented)
        self.assertEqual(documented - set(m["observation"]), set())


class StrictFramingSurfaceTests(unittest.TestCase):
    """ADR-0053 criterion 4 strict bar: no residual 'six concern(s)' framing."""

    STRICT = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "USER_GUIDE.md",
        REPO_ROOT / "crux" / "templates" / "USER_GUIDE.md",
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "crux" / "templates" / "manifest.yml.tmpl",
    ]

    def test_no_six_concern_framing_in_strict_surfaces(self):
        require_dev_surface(self, REPO_ROOT / "CLAUDE.md", "CLAUDE.md")
        pat = re.compile(r"six[- ]concern", re.IGNORECASE)
        for f in self.STRICT:
            self.assertIsNone(
                pat.search(f.read_text()),
                f"residual six-concern framing in {f.relative_to(REPO_ROOT)}",
            )

    def test_strict_surfaces_name_seven_concerns_or_invariants(self):
        require_dev_surface(self, REPO_ROOT / "CLAUDE.md", "CLAUDE.md")
        # Positive check: the framing actually moved to seven / names invariants.
        for f in (REPO_ROOT / "README.md", REPO_ROOT / "USER_GUIDE.md", REPO_ROOT / "CLAUDE.md"):
            t = f.read_text()
            self.assertTrue(
                "seven concern" in t or "invariants" in t,
                f"{f.relative_to(REPO_ROOT)} does not name seven concerns / invariants",
            )


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class TestInitDocsSkillProse(unittest.TestCase):
    """ADR-0059 acceptance: init-docs SKILL.md prose matches the shipped
    templates (bionic/ tree unification) and carries no obsolete v4
    current-layout wording. Expectations are derived FROM the templates
    where practical rather than hardcoded, so a future schema bump that
    updates the templates doesn't silently desync this test from them.
    """

    SKILL_MD = REPO_ROOT / "crux" / "skills" / "init-docs" / "SKILL.md"

    def _skill_text(self) -> str:
        return self.SKILL_MD.read_text()

    def test_step6_schema_version_parenthetical_matches_manifest_template(self):
        manifest = yaml.safe_load((TEMPLATES / "manifest.yml.tmpl").read_text())
        current_schema = manifest["schema_version"]
        text = self._skill_text()
        m = re.search(r'currently `"([^"]+)"`', text)
        self.assertIsNotNone(
            m, "expected a step-6 `currently \"X\"` parenthetical in init-docs SKILL.md"
        )
        self.assertEqual(
            m.group(1),
            current_schema,
            "SKILL.md step-6 'currently' literal is out of sync with "
            "manifest.yml.tmpl's schema_version",
        )

    def test_no_obsolete_v4_current_layout_literals(self):
        text = self._skill_text()
        # Amendment A1: ban only obsolete CURRENT-LAYOUT literals; history /
        # migration references to older schema versions stay legitimate.
        banned = [
            'currently `"4"`',
            "tree at schema_version 4",
        ]
        for literal in banned:
            self.assertNotIn(
                literal,
                text,
                f"obsolete v4 current-layout literal {literal!r} found in init-docs SKILL.md",
            )

    def test_invariants_concern_is_one_folder_inside_the_tree(self):
        text = self._skill_text()
        # Positive: the suite + reconciliation are named INSIDE the tree.
        self.assertIn("${DOCS_DIR}/invariants/checks/", text)
        self.assertIn("${DOCS_DIR}/invariants/reconciliation.yml", text)
        # Negative: no peer-root instruction survives (the v4 split layout).
        self.assertNotIn("OUTSIDE docs/", text)
        self.assertNotIn("at the repo root under `bionic/`", text)
        self.assertNotIn("peer invariants check suite", text)

    def test_arch_concern_scaffolded_and_spine_deferred(self):
        # WU1 (arch enrollment): init eagerly creates the arch/ directory + a
        # placeholder index.md but DEFERS the derived spine (no derive-arch at
        # init), and the master index stays exempt (no ## Arch section).
        text = self._skill_text()
        # Instruction to create the arch dir + a placeholder index.md.
        self.assertIn("arch/", text)
        self.assertIn("${DOCS_DIR}/arch/index.md", text)
        # DEFER appears in the arch scaffolding block, and it states init must
        # not run the derive at bootstrap (deferred to first derive/audit).
        i = text.index("Arch concern")
        arch_block = text[i : i + 900]
        self.assertRegex(arch_block, r"(?i)defer")
        self.assertIn("MUST NOT invoke", arch_block)
        # It must NOT instruct adding an `## Arch` master-index section; the
        # only permitted mention is the exemption (no `## Arch` section).
        self.assertIn("NO `## Arch` section", text)

    def test_directory_tree_step_creates_under_docs_dir_not_literal_docs(self):
        text = self._skill_text()
        self.assertIn(
            "${REPO_ROOT}/${DOCS_DIR}/",
            text,
            "step-4 directory-tree instructions should create the tree under "
            "${REPO_ROOT}/${DOCS_DIR}/",
        )
        self.assertNotIn(
            "under `${REPO_ROOT}/docs/`",
            text,
            "step-4 must not instruct creation under the retired literal docs/ layout",
        )

    def test_checklist_guards_against_greenfield_docs_directory(self):
        text = self._skill_text()
        self.assertIn(
            "No directory literally named `docs` was created on a greenfield default init",
            text,
        )

    def test_directory_tree_diagram_root_matches_bionic_yml_template(self):
        bionic_cfg = yaml.safe_load((TEMPLATES / "bionic-yml.tmpl").read_text())
        docs_dir = bionic_cfg["docs_dir"]
        text = self._skill_text()
        # The step-4 fenced diagram's first line is the tree root name.
        m = re.search(r"```\n(\S+)/\n", text)
        self.assertIsNotNone(
            m, "expected the step-4 fenced directory-tree diagram in init-docs SKILL.md"
        )
        self.assertEqual(
            m.group(1),
            docs_dir,
            "step-4 diagram root does not match bionic-yml.tmpl's docs_dir",
        )

    def _section(self, heading: str) -> str:
        """Extract one pipeline step's body (### heading to the next ###)."""
        t = self._skill_text()
        i = t.index(heading)
        j = t.find("\n### ", i + len(heading))
        return t[i : j if j != -1 else len(t)]

    def test_step2_guard_keys_on_resolved_docs_dir(self):
        s = self._section("### 2. Resolve the tree location")
        self.assertIn("${REPO_ROOT}/${DOCS_DIR}/", s)
        self.assertIn("bionic-config.py", s)
        self.assertNotRegex(s, r"\$\{REPO_ROOT\}/(docs|bionic)/")
        self.assertIn("never guess `bionic`", s)

    def test_step6a_substitutes_resolved_docs_dir(self):
        s = self._section("### 6.A.")
        self.assertIn("substituting `docs_dir: ${DOCS_DIR}`", s)
        self.assertNotIn("Copy it verbatim", s)

    def test_log_seed_literal_matches_manifest_template(self):
        manifest = yaml.safe_load((TEMPLATES / "manifest.yml.tmpl").read_text())
        current_schema = manifest["schema_version"]
        # Positive derivation (amendment A1/SC-1): the seeded init entry must
        # record the CURRENT schema, whatever obsolete value history holds.
        self.assertIn(
            f"tree at schema_version {current_schema}",
            self._skill_text(),
            "step-8 log.md seed literal does not record the current schema_version",
        )

    def test_rollback_contract_restores_modifications_and_archive(self):
        s = self._section("**Rollback contract.**")
        self.assertIn("record the PRIOR content", s)
        self.assertIn("Restore the recorded prior content", s)
        self.assertIn("move `${ARCHIVE}` back to `${DOCS_DIR}`", s)
        self.assertIn("do NOT move and instead report both paths", s)
        self.assertIn("state the archive path in the failure report", s)
        self.assertIn("Never `rm -rf`", s)

    def test_user_guide_overwrite_requires_force_and_confirmation(self):
        t = self._skill_text()
        self.assertIn("overwrite ONLY when `--force` was passed AND the user has confirmed", t)

    def test_step2_refuses_non_directory_at_resolved_location(self):
        s = self._section("### 2. Resolve the tree location")
        self.assertIn("is not a directory, **STOP**", s)

    def test_checklist_bionic_yml_names_the_created_tree(self):
        self.assertIn(
            "`.bionic.yml` exists at the repo root and carries `docs_dir` naming "
            "the tree just created",
            self._skill_text(),
        )


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class TemplateCommentAgreementTests(unittest.TestCase):
    """A template's COMMENTS must agree with its own parsed VALUES — the
    drift class that shipped this bug (a "currently == \"4\"" comment
    beside schema_version: "5") is invisible to yaml.safe_load alone.
    """

    def test_manifest_tmpl_comments_agree_with_its_own_value(self):
        raw = (TEMPLATES / "manifest.yml.tmpl").read_text()
        v = yaml.safe_load(raw)["schema_version"]
        for m in re.finditer(r'currently == "(\d+)"', raw):
            self.assertEqual(
                m.group(1), v,
                "manifest.yml.tmpl comment contradicts its own schema_version",
            )

    def test_dot_crux_tmpl_comments_do_not_claim_docs_default(self):
        raw = (TEMPLATES / "dot-crux.tmpl").read_text()
        self.assertNotIn('Default: "docs"', raw)
        self.assertNotIn("docs tree at ./docs/", raw)
        self.assertIn("defaults to `bionic`", raw)

    def test_bionic_yml_tmpl_comments_agree_with_its_own_docs_dir(self):
        raw = (TEMPLATES / "bionic-yml.tmpl").read_text()
        self.assertNotIn("ledger at ./docs/", raw)
        docs_dir = yaml.safe_load(raw)["docs_dir"]
        self.assertIn(docs_dir, raw.split("docs_dir:", 1)[1])


def _frontmatter_keys(text: str) -> list[str]:
    """Top-level keys of a `---`-fenced frontmatter block, in file order."""
    parts = text.split("---\n")
    assert len(parts) >= 3, "missing a --- delimited frontmatter block"
    return re.findall(r"^([A-Za-z_][A-Za-z0-9_]*):", parts[1], re.MULTILINE)


def _section_17_1_keyset(claude_md: str) -> list[str]:
    """The backticked first-column tokens of the §17.1 table, in table order."""
    i = claude_md.index("### 17.1 ")
    j = claude_md.index("### 17.2 ", i)
    rows = re.findall(r"^\| `([a-z_]+)` \|", claude_md[i:j], re.MULTILINE)
    assert rows, "§17.1 table rows not found"
    return rows


class ObservationsConcernTests(unittest.TestCase):
    """The observations concern is enabled additively (docs/CLAUDE.md §17):
    the template carries the §17.1 keyset one-for-one, the dogfood + template
    manifests carry the concern and its counter with NO schema_version bump,
    and init-docs eagerly creates the concern's surfaces.
    """

    OBS_TEMPLATE = TEMPLATES / "OBS-template.md"
    SKILL_MD = REPO_ROOT / "crux" / "skills" / "init-docs" / "SKILL.md"

    def test_obs_template_keyset_matches_section_17_1_in_order(self):
        require_dev_surface(self, TREE_CLAUDE_MD, f"{TREE}/CLAUDE.md")
        canonical = _section_17_1_keyset(TREE_CLAUDE_MD.read_text())
        self.assertTrue(self.OBS_TEMPLATE.exists(), "crux/templates/OBS-template.md missing")
        self.assertEqual(_frontmatter_keys(self.OBS_TEMPLATE.read_text()), canonical)

    def test_obs_template_points_at_the_schema_and_restates_nothing(self):
        # §11.D rule 4: the template names §17.1 as the source of truth and
        # carries no copy of the field semantics (no `required`, no enum list).
        t = self.OBS_TEMPLATE.read_text()
        self.assertIn("§17.1", t)
        self.assertNotRegex(t, r"(?i)\brequired\b")
        self.assertNotIn("observed | ratified", t)

    def test_obs_template_body_skeleton_and_no_code_excerpt(self):
        t = self.OBS_TEMPLATE.read_text()
        for heading in (
            "# OBS-NNNN — <title>",
            "## What the code does",
            "## Evidence",
            "## Why this is observed, not decided",
        ):
            self.assertIn(heading, t)
        self.assertIn("path:line-range", t)
        self.assertNotIn("```", t, "no code excerpt anywhere in the template")

    def test_obs_template_is_a_clean_distributed_surface(self):
        t = self.OBS_TEMPLATE.read_text()
        self.assertNotRegex(t, r"ADR-\d{4}")
        self.assertNotIn("[[adrs/", t)

    @unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
    def test_dogfood_manifest_enables_observations_without_schema_bump(self):
        path = REPO_ROOT / TREE / "manifest.yml"
        require_dev_surface(self, path, f"{TREE}/manifest.yml")
        m = yaml.safe_load(path.read_text())
        self.assertIn("observations", m["concerns_enabled"])
        # The two counters are monotonic and move the first time the concern is
        # used — the dogfood tree scaffolded SVY-0001 on 2026-08-31 — so the
        # block is pinned by key set and thresholds, never by a counter's value.
        obs = m["observation"]
        self.assertEqual(set(obs), {"next_number", "stale_days", "next_survey_number", "survey_stub_days"})
        self.assertEqual((obs["stale_days"], obs["survey_stub_days"]), (90, 1))
        for key in ("next_number", "next_survey_number"):
            self.assertIsInstance(obs[key], int)
            self.assertGreaterEqual(obs[key], 1, key)
        self.assertEqual(m["schema_version"], "5")

    def test_dogfood_observations_index_count_matches_disk(self):
        path = REPO_ROOT / TREE / "observations" / "index.md"
        require_dev_surface(self, path, f"{TREE}/observations/index.md")
        t = path.read_text()
        # The count is read from disk, never pinned: the dogfood tree published
        # its first batch (SVY-0001, three records) on 2026-08-31.
        n = len(list((REPO_ROOT / TREE / "observations").glob("OBS-*.md")))
        self.assertIn(f"## Records ({n})", t)
        self.assertIn("§17", t)
        self.assertIn("visibly marked", t)

    def test_dogfood_master_index_carries_observations_between_invariants_and_arch(self):
        path = REPO_ROOT / TREE / "index.md"
        require_dev_surface(self, path, f"{TREE}/index.md")
        t = path.read_text()
        i = t.index("## Invariants (")
        # The count is DERIVED, never frozen: this test asserts the section's
        # POSITION, and freezing `(0)` made it fail the moment the tree
        # ratified its first observation — a true tree reported as a defect.
        m = re.search(r"^## Observations \(\d+\)$", t, re.M)
        self.assertIsNotNone(m, "master index carries no ## Observations section")
        o = m.start()
        a = t.index("## Arch")
        self.assertTrue(i < o < a, "## Observations must sit after Invariants and before Arch")

    def test_init_docs_skill_creates_observations_surfaces_eagerly(self):
        t = self.SKILL_MD.read_text()
        self.assertIn("${DOCS_DIR}/observations/index.md", t)
        self.assertIn("Records (0)", t)
        self.assertIn("## Observations (0)", t)
        self.assertIn("observation.next_number: 1", t)
        self.assertRegex(t, r"concerns_enabled: \[[^\]]*observations[^\]]*\]")
        self.assertIn("`concerns_enabled` includes `invariants`, `arch`, and `observations`", t)

    def test_init_docs_skill_adds_no_migration_rung_and_no_schema_bump(self):
        t = self.SKILL_MD.read_text()
        # The only `currently "X"` literal is the step-6 one, still "5".
        self.assertEqual(re.findall(r'currently `"([^"]+)"`', t), ["5"])
        i = t.index("Observations concern")
        block = t[i : i + 900]
        self.assertNotRegex(block, r"(?i)migrat")


class InstallDocsSkillsProseTests(unittest.TestCase):
    """The sibling detection surface: fresh-vs-upgrade detection must not
    key on the retired literal `docs/` absence (a bionic/-only repo is an
    existing installation)."""

    SKILL_MD = REPO_ROOT / "crux" / "skills" / "install-docs-skills" / "SKILL.md"

    def test_detection_never_keys_on_literal_docs_absence(self):
        t = self.SKILL_MD.read_text()
        self.assertNotIn(
            "If `docs/` does NOT exist in the target repo (fresh install)", t)
        for marker in ("`.bionic.yml`", "`bionic/` tree", "legacy `docs/` tree"):
            self.assertIn(marker, t, f"detection marker {marker} missing")


class UserGuideSchemaLiteralTests(unittest.TestCase):
    """USER_GUIDE 'this project uses schema_version N' claims must match the
    shipped manifest template's value (the class that recurred across two
    bumps — a guide saying "3" into the v5 era)."""

    @unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
    def test_user_guides_name_the_current_schema_version(self):
        v = yaml.safe_load((TEMPLATES / "manifest.yml.tmpl").read_text())["schema_version"]
        for f in (REPO_ROOT / "USER_GUIDE.md", TEMPLATES / "USER_GUIDE.md"):
            self.assertIn(f"schema_version {v}", f.read_text(),
                          f"{f.name} does not name schema_version {v}")


class ReviewsSurfaceAtInitTests(unittest.TestCase):
    """`init-docs` creates the decision-review surface before the first review.

    Without it a fresh tree reaches the CLN-ADR-5 cadence nudge with nowhere
    to write (review finding `adr-review-init-docs-omits-reviews`).
    """

    def setUp(self) -> None:
        self.text = (REPO_ROOT / "crux" / "skills" / "init-docs" / "SKILL.md").read_text(encoding="utf-8")

    def test_the_directory_tree_names_adrs_reviews(self):
        self.assertIn("adrs/reviews/", self.text)

    def test_the_gitkeep_list_and_the_checklist_carry_it(self):
        keep = self.text[self.text.index("Add a `.gitkeep` file to each leaf directory"):]
        self.assertIn("`adrs/reviews/`", keep.split("\n", 1)[0])
        self.assertIn("`${DOCS_DIR}/adrs/reviews/`", self.text[self.text.index("## Verification checklist"):])


if __name__ == "__main__":
    unittest.main()
