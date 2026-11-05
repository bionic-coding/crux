"""The test-tiers skill and the instruction surfaces that state the labelling requirement.

These are text contracts. The skill is the portable statement a target project reads; the
other surfaces state where each tier runs. Each assertion names a clause whose removal would
let an agent narrow a gate by tier, accept a release-tier receipt as all-tests evidence, or
add a test without a label.
"""
from pathlib import Path
import json
import re
import unittest

try:
    from ._dev_surface import TREE_AGENTS_MD, require_dev_surface
except ImportError:
    from _dev_surface import TREE_AGENTS_MD, require_dev_surface

PLUGIN = Path(__file__).resolve().parents[2]
REPO = PLUGIN.parent
SKILL = PLUGIN / "skills" / "test-tiers" / "SKILL.md"


def flat(path):
    return " ".join(path.read_text(encoding="utf-8").split())


def missing(text, clauses):
    return [clause for clause in clauses if clause not in text]


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return match.group(1) if match else ""


# The rule slugs the accepted test-tier decision governs. Instruction surfaces cite them in
# footnotes; a surface that states a tier rule without its citation drifts from the decision.
CORE_SLUGS = (
    "every-test-has-exactly-one-tier",
    "new-tests-are-labelled-in-the-same-change",
    "tiers-never-narrow-a-cycle-gate",
    "completion-requires-every-tier",
)


class TestTiersSkillContracts(unittest.TestCase):
    def test_skill_is_catalogued_with_trigger_phrases(self):
        head = frontmatter(SKILL)
        self.assertIn("name: test-tiers", head)
        triggers = re.search(r'triggers: "([^"]+)"', head)
        self.assertIsNotNone(triggers, "the skill carries no trigger phrases")
        phrases = [p.strip() for p in triggers.group(1).split("|")]
        for phrase in ("label the tests", "check the test tiers", "list the release tier"):
            self.assertIn(phrase, phrases)
        catalog = json.loads((PLUGIN / "catalog" / "skills.json").read_text(encoding="utf-8"))
        entries = catalog["skills"] if isinstance(catalog, dict) else catalog
        names = [entry["name"] for entry in entries]
        self.assertIn("test-tiers", names)

    def test_skill_states_three_tiers_and_what_each_means(self):
        text = flat(SKILL)
        self.assertEqual(missing(text, (
            "**`dev`**", "**`release`**", "**`ephemeral`**",
            "a chosen subset, never every test",
            "The test is labelled, not deleted",
            "labels it in the same change",
            "non-empty proper subset",
            "explicit change that names it")), [])

    def test_skill_states_where_each_tier_runs_and_that_gates_never_narrow(self):
        text = flat(SKILL)
        self.assertEqual(missing(text, (
            "Tiers narrow development loops only",
            "No gate's test selection narrows by tier",
            "Completing a cycle of any type except release needs current passing evidence for every test of every tier",
            "A tier-filtered receipt never counts as an all-tests pass",
            "A release cycle completes on its fixed step list",
            "Merging needs every test to pass on the head",
            "Pull-request CI runs every test its environment can run",
            "needs recorded passing evidence for the head before the merge")), [])

    def test_skill_documents_every_manifest_key_and_the_override_order(self):
        text = flat(SKILL)
        for key in ("`format`", "`version`", "`kind`", "`pattern`", "`areas`", "`files`",
                    "`overrides`", "`area`", "`reason`", "`expires`", "`retire_when`",
                    "`python-unittest`", "`file-glob`", "crux.test-tiers"):
            self.assertIn(key, text)
        self.assertIn("A method override wins over a class override, which wins over the file entry", text)
        self.assertIn("`test-tiers.example.json`", text)

    def test_skill_example_manifest_is_valid_json_in_manifest_shape(self):
        body = SKILL.read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)\n```", body, re.S)
        self.assertEqual(len(blocks), 1, "the skill should carry exactly one example manifest")
        example = json.loads(blocks[0])
        self.assertEqual(sorted(example), sorted(("format", "version", "kind", "pattern", "areas", "files")))
        self.assertEqual((example["format"], example["version"]), ("crux.test-tiers", 1))
        tiers = {entry["tier"] for entry in example["files"].values()}
        tiers |= {o["tier"] for entry in example["files"].values() for o in entry.get("overrides", {}).values()}
        self.assertEqual(tiers, {"dev", "release", "ephemeral"})

    def test_skill_states_the_check_rules_and_the_warning_only_expiry(self):
        text = flat(SKILL)
        self.assertEqual(missing(text, (
            "**unlabelled**", "`unlabelled-nested`", "**doubly-labelled**", "**stale**",
            "**subset**", "**areas**", "**ephemeral**", "**fields**",
            "`missing-root`", "`untracked-root`", "`--expect-root ROOT`",
            "`--require-release-units ROOT`", "`check --root ROOT`", "`check --shard PATH --root ROOT`",
            "never fails the check")), [])

    def test_skill_states_the_language_agnostic_runner_contract(self):
        text = flat(SKILL)
        self.assertEqual(missing(text, (
            "## The runner contract", "`list`", "`--ids`",
            "exits 2 on a finding or on a missing or invalid manifest",
            "fails closed", "a test that failed to load",
            "--preset test-tiers")), [])

    def test_skill_cites_rules_by_slug_and_no_decision_number(self):
        body = SKILL.read_text(encoding="utf-8")
        for slug in CORE_SLUGS:
            self.assertIn(f"rule:{slug}", body)
        self.assertIsNone(re.search(r"\bADR-\d{4}\b", body))

    def test_skill_is_in_a_bundle(self):
        bundles = (PLUGIN / "catalog" / "bundles.yml").read_text(encoding="utf-8")
        self.assertIn('- "test-tiers"', bundles)


class TierInstructionSurfaceContracts(unittest.TestCase):
    """Every surface that tells an agent how to test states the labelling requirement."""

    def test_testing_reference_states_tiers_and_the_registered_ids(self):
        text = flat(PLUGIN / "skills" / "cycle" / "references" / "testing.md")
        self.assertEqual(missing(text, (
            "## Test tiers", "labels it in the same change",
            "No gate narrows by tier", "A release-tier receipt never satisfies it",
            "`checkout:test-tiers`", "`checkout:unittest-release:...`",
            "A current failing full receipt fails the step, with no fallback",
            "`--tier release`", "`related-tests.py --tier dev --tier release`",
            "| `test-tiers` |")), [])
        for slug in CORE_SLUGS:
            self.assertIn(f"rule:{slug}", text)

    def test_commands_reference_names_the_tier_check_as_a_build_check(self):
        text = flat(PLUGIN / "skills" / "cycle" / "references" / "commands.md")
        self.assertEqual(missing(text, (
            "the tier check `checkout:test-tiers`",
            "A release-tier receipt never satisfies Build, Verify, Review, Reflect or `finish`")), [])

    def test_each_role_states_the_labelling_requirement(self):
        for role in ("developer", "dev-lead", "reviewer", "commander"):
            text = flat(PLUGIN / "agents" / f"{role}.md")
            self.assertIn("test-tiers", text, role)
            self.assertIn("rule:new-tests-are-labelled-in-the-same-change", text, role)
        self.assertIn("Each developer dispatch says so", flat(PLUGIN / "agents" / "dev-lead.md"))
        self.assertIn("It never narrows a gate", flat(PLUGIN / "agents" / "developer.md"))

    TWIN = ("Test tiers label every test with exactly one tier.",
            "never every test",
            "labels it in the same change",
            "No gate narrows by tier.",
            "A tier-filtered receipt never counts as that evidence.",
            "A release cycle completes on its fixed step list.",
            "Merging a pull request requires every test to pass on its head.",
            "rule:tiers-never-narrow-a-cycle-gate")

    def test_shipped_operational_schema_template_states_tiers(self):
        self.assertEqual(missing(flat(PLUGIN / "templates" / "AGENTS.md.tmpl"), self.TWIN), [])

    def test_live_operational_schema_twin_states_tiers(self):
        require_dev_surface(self, TREE_AGENTS_MD, "docs-tree AGENTS.md")
        self.assertEqual(missing(flat(TREE_AGENTS_MD), self.TWIN), [])

    def test_root_instructions_runbook_and_guide_state_tiers(self):
        expectations = {
            "AGENTS.md": ("### Test tiers", "No gate narrows by tier", "`checkout:test-tiers`",
                          "A release-tier receipt never satisfies it"),
            "DEPLOY.md": ("`checkout:unittest-release:<root>:test*.py`", "`checkout:test-tiers`",
                          "A current failing full receipt fails `verify`, with no fallback",
                          "release tier, on the floor minor, and not every test"),
            "USER_GUIDE.md": ("label the tests", "Merging a pull request requires every test",
                              "Completing a cycle still requires every test to pass"),
        }
        for relative, clauses in expectations.items():
            path = REPO / relative
            require_dev_surface(self, path, relative)
            self.assertEqual(missing(flat(path), clauses), [], relative)


if __name__ == "__main__":
    unittest.main()
