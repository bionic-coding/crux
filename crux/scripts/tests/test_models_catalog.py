"""Tests for models_catalog.py — the shared agent-model catalog reader.

The loader is the fail-closed gate: it runs the schema check (V0), the roster
bijection (V1) and the reference-graph check (V2) BEFORE returning, so a
regenerator invoked directly rather than through CI fails before it writes.
These tests pin that behavior, and pin the resolution against the intended
ten-agent lineup.

Self-contained fixtures throughout. `sync.sh` runs this suite against a
crux-only staged tree, so a test that copies the repo and reads an
out-of-allowlist path would false-fail at release time.

Stdlib only. Run: uv run python3 -m unittest crux.scripts.tests.test_models_catalog
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import models_catalog as MC  # noqa: E402

EXPECTED_AGENTS = {
    "architect", "brainstormer", "commander", "dev-lead", "developer",
    "historian", "librarian", "night-gardener", "reviewer", "wayfinder",
}

# Historical schema-1 body. The schema-version-3 reader refuses it without
# migration or inference.
V1_BODY = textwrap.dedent(
    """\
    schema_version: "1"

    agents:
      architect: planning
      brainstormer: planning
      commander: planning
      dev-lead: planning
      developer: coding
      historian: retrieval
      librarian: retrieval
      night-gardener: planning
      reviewer: review
      wayfinder: retrieval

    categories:
      planning: flagship
      coding: standard
      review: flagship
      retrieval: standard

    levels:
      flagship:
        claude: opus
        opencode: anthropic/claude-opus-5
        codex:
          model: gpt-5.6-sol
          reasoning_effort: high
          verified: "2026-08-21"
          source: "carried forward at adoption"
      standard:
        claude: sonnet
        opencode: anthropic/claude-sonnet-5
        codex:
          model: gpt-5.6-terra
          reasoning_effort: medium
          verified: "2026-08-21"
          source: "carried forward at adoption"

    claude_aliases:
      - fable
      - opus
      - sonnet
      - haiku
      - inherit
    """
)


def _agents_fixture(tmp: Path, *, drop: str | None = None, extra: str | None = None) -> Path:
    """The ten real agent files copied into `tmp`, minus `drop`, plus `extra`."""
    out = tmp / "agents"
    out.mkdir()
    for src in sorted(MC.AGENTS_DIR.glob("*.md")):
        if src.stem == drop:
            continue
        shutil.copy2(src, out / src.name)
    if extra is not None:
        (out / f"{extra}.md").write_text(
            f"---\nname: {extra}\ndescription: Synthetic.\ntools: Read\nmodel: sonnet\n---\nBody.\n",
            encoding="utf-8",
        )
    return out


def _catalog_copy(tmp: Path, transform=None) -> Path:
    """The shipped catalog copied into `tmp`, optionally text-transformed."""
    text = MC.CATALOG_PATH.read_text(encoding="utf-8")
    if transform is not None:
        text = transform(text)
    path = tmp / "models.yml"
    path.write_text(text, encoding="utf-8")
    return path


class ShippedCatalogTests(unittest.TestCase):
    def test_shipped_catalog_passes_every_loader_rule(self):
        raw = MC.load_raw()
        self.assertEqual(MC.check_shape(raw), [])
        self.assertEqual(MC.check_roster(raw, MC.AGENTS_DIR), [])
        self.assertEqual(MC.check_reference_graph(raw), [])

    def test_load_returns_the_ten_agent_roster(self):
        catalog = MC.load()
        self.assertEqual(set(catalog.agents), EXPECTED_AGENTS)
        self.assertEqual(catalog.schema_version, MC.SCHEMA_VERSION)

    def test_managed_filenames_are_the_roster_as_filenames(self):
        catalog = MC.load()
        self.assertEqual(catalog.managed_filenames, frozenset(f"{n}.md" for n in EXPECTED_AGENTS))

    def test_resolution_reproduces_the_intended_lineup(self):
        """The resolved triple per agent, with OpenCode bound by alias NAME.

        Binding the OpenCode column to `aliases[<alias>]` rather than a literal
        id is what lets the owner bump a model in a one-line alias edit without
        touching this test — which is the whole reason the alias table exists.
        """
        expected = {
            "architect":      ("opus",   "kimi-latest",   "gpt-5.6-sol",   "high"),
            "brainstormer":   ("opus",   "kimi-latest",   "gpt-5.6-sol",   "high"),
            "commander":      ("fable",   "qwen-max",      "gpt-6-astra",   "high"),
            "dev-lead":       ("opus",   "glm-latest",    "gpt-5.6-sol",   "high"),
            "developer":      ("sonnet", "glm-flash",     "gpt-5.6-terra", "high"),
            "historian":      ("sonnet", "qwen-max",      "gpt-5.6-terra", "high"),
            "librarian":      ("sonnet", "qwen-max",      "gpt-5.6-terra", "high"),
            "night-gardener": ("fable",  "kimi-latest",   "gpt-6-astra",   "high"),
            "reviewer":       ("fable",   "kimi-latest",   "gpt-5.6-sol",   "xhigh"),
            "wayfinder":      ("sonnet", "qwen-max",      "gpt-5.6-terra", "high"),
        }
        catalog = MC.load()
        self.assertEqual(set(expected), EXPECTED_AGENTS)
        for name, (claude, alias, model, effort) in sorted(expected.items()):
            with self.subTest(agent=name):
                resolved = catalog.resolve(name)
                self.assertEqual(resolved.claude, claude)
                self.assertEqual(catalog.opencode_alias(name), alias)
                self.assertEqual(resolved.opencode, catalog.aliases[alias])
                self.assertEqual(resolved.codex.model, model)
                self.assertEqual(resolved.codex.reasoning_effort, effort)

    def test_apex_uses_astra_while_flagship_keeps_sol_at_high_effort(self):
        catalog = MC.load()
        apex, flagship = catalog.levels["apex"], catalog.levels["flagship"]
        # Apex runs Fable on Claude; flagship keeps Opus. The two tiers differ
        # on every provider now, which is the point of having two.
        self.assertEqual(apex.claude, "fable")
        self.assertEqual(flagship.claude, "opus")
        self.assertEqual(apex.codex.model, "gpt-6-astra")
        self.assertEqual(flagship.codex.model, "gpt-5.6-sol")
        self.assertEqual(apex.codex.reasoning_effort, "high")
        self.assertEqual(flagship.codex.reasoning_effort, "high")
        self.assertIsNone(apex.opencode)
        self.assertIsNotNone(flagship.opencode)

    def test_reviewer_is_the_only_codex_override(self):
        """The reviewer override keeps the other nine level-derived Codex assignments unchanged."""
        catalog = MC.load()
        overrides = {name for name, row in catalog.agents.items() if row.codex is not None}
        self.assertEqual(overrides, {"reviewer"})
        expected = MC.CodexRuntime(
            model="gpt-5.6-sol",
            reasoning_effort="xhigh",
            verified="2026-09-11",
            source="OpenAI GPT-5.6 Sol model documentation checked 2026-09-11",
        )
        self.assertEqual(catalog.agents["reviewer"].codex, expected)
        self.assertEqual(catalog.resolve("reviewer").codex, expected)

    def test_agent_without_a_codex_override_falls_back_to_its_level(self):
        catalog = MC.load()
        self.assertIsNone(catalog.agents["commander"].codex)
        self.assertEqual(catalog.resolve("commander").codex, catalog.levels["apex"].codex)


class FailClosedTests(unittest.TestCase):
    def test_historical_v1_schema_is_refused_without_migration(self):
        """AC-7: an older schema is refused, not migrated."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "models.yml"
            path.write_text(V1_BODY, encoding="utf-8")
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=MC.AGENTS_DIR)
        self.assertIn("schema_version", str(ctx.exception))

    def test_v2_schema_is_refused_without_migration_or_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(
                tmp, lambda text: text.replace('schema_version: "3"', 'schema_version: "2"', 1)
            )
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertIn("schema_version must be '3'", str(ctx.exception))

    def test_load_rejects_a_non_mapping_reviewer_codex_override(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(
                tmp,
                lambda text: text.replace(
                    "    codex:\n"
                    "      model: gpt-5.6-sol\n"
                    "      reasoning_effort: xhigh\n"
                    '      verified: "2026-09-11"\n'
                    '      source: "OpenAI GPT-5.6 Sol model documentation checked 2026-09-11"',
                    "    codex: gpt-5.6-sol",
                    1,
                ),
            )
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertIn("agents.'reviewer'.codex must be a mapping", str(ctx.exception))

    def test_load_rejects_a_non_string_member_of_reviewer_codex_override(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(
                tmp,
                lambda text: text.replace("      reasoning_effort: xhigh", "      reasoning_effort: 4", 1),
            )
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertIn(
            "agents.'reviewer'.codex.'reasoning_effort' must be a string",
            str(ctx.exception),
        )

    def test_missing_file_raises_spec_violation(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(MC.SpecViolation):
                MC.load_raw(Path(td) / "absent.yml")

    def test_roster_mismatch_extra_key_raises(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            agents = _agents_fixture(tmp, drop="wayfinder")
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=MC.CATALOG_PATH, agents_dir=agents)
        self.assertIn("wayfinder", str(ctx.exception))

    def test_roster_mismatch_unlisted_agent_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            agents = _agents_fixture(tmp, extra="interloper")
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=MC.CATALOG_PATH, agents_dir=agents)
        self.assertIn("interloper", str(ctx.exception))

    def test_resolve_refuses_an_agent_outside_the_roster(self):
        with self.assertRaises(MC.SpecViolation):
            MC.load().resolve("no-such-agent")

    def test_empty_agents_dir_is_refused_rather_than_passing_vacuously(self):
        # An empty glob would make the bijection trivially "hold" in one
        # direction and report a roster of ten stale keys in the other.
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td) / "agents"
            empty.mkdir()
            findings = MC.check_roster(MC.load_raw(), empty)
        self.assertTrue(findings)


class RuleFindingTests(unittest.TestCase):
    """Each check function reports the defect it owns, and only that one."""

    def test_shape_rejects_a_fourth_level(self):
        raw = MC.load_raw()
        raw["levels"]["fast"] = dict(raw["levels"]["standard"])
        self.assertTrue(any("levels" in f for f in MC.check_shape(raw)))

    def test_shape_rejects_an_appended_claude_alias(self):
        raw = MC.load_raw()
        raw["claude_aliases"] = raw["claude_aliases"] + ["invented"]
        self.assertTrue(any("claude_aliases" in f for f in MC.check_shape(raw)))

    def test_shape_rejects_an_added_claude_disabled_table(self):
        # The `claude_disabled` deny-list table is GONE from the shipped
        # catalog: the top-level key set is six keys. Reintroducing it at all —
        # even with the original `fable` entry — is the defect V0's key-set
        # check refuses, so a deleted entry can never quietly unlock anything.
        # (The absent-key-is-fine side of this contract is pinned by
        # test_shipped_catalog_passes_every_loader_rule above.)
        raw = MC.load_raw()
        raw["claude_disabled"] = ["fable"]
        self.assertTrue(any(
            "unknown top-level key" in f and "claude_disabled" in f
            for f in MC.check_shape(raw)
        ))

    def test_shape_rejects_an_agent_row_carrying_a_claude_key(self):
        raw = MC.load_raw()
        raw["agents"]["architect"] = {"level": "flagship", "claude": "opus"}
        # The row name is interpolated with `!r` — a whitespace-only or empty
        # roster key is otherwise invisible in the finding.
        self.assertTrue(any("agents.'architect'" in f for f in MC.check_shape(raw)))

    def test_shape_rejects_a_partial_agent_codex_override(self):
        raw = MC.load_raw()
        raw["agents"]["reviewer"]["codex"] = {"model": "gpt-5.6-sol"}
        findings = MC.check_shape(raw)
        self.assertTrue(any(
            "agents.'reviewer'.codex key set must be exactly" in finding
            for finding in findings
        ))

    def test_shape_rejects_an_agent_codex_override_with_an_extra_field(self):
        raw = MC.load_raw()
        raw["agents"]["reviewer"]["codex"] = {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "xhigh",
            "verified": "2026-09-11",
            "source": "OpenAI GPT-5.6 Sol model documentation checked 2026-09-11",
            "unexpected": "value",
        }
        findings = MC.check_shape(raw)
        self.assertTrue(any(
            "agents.'reviewer'.codex key set must be exactly" in finding
            for finding in findings
        ))

    def test_reference_graph_rejects_an_undeclared_alias(self):
        raw = MC.load_raw()
        raw["agents"]["commander"] = {"level": "apex", "opencode": "not-declared"}
        self.assertTrue(any("not-declared" in f for f in MC.check_reference_graph(raw)))

    def test_reference_graph_rejects_an_unreached_level(self):
        raw = MC.load_raw()
        raw["agents"]["commander"] = {"level": "flagship", "opencode": "kimi-latest"}
        raw["agents"]["reviewer"] = "flagship"
        raw["agents"]["night-gardener"] = "flagship"
        self.assertTrue(any("apex" in f for f in MC.check_reference_graph(raw)))

    def test_reference_graph_rejects_an_apex_agent_with_no_override(self):
        raw = MC.load_raw()
        raw["agents"]["commander"] = "apex"
        self.assertTrue(any("commander" in f for f in MC.check_reference_graph(raw)))

    def test_reference_graph_rejects_an_uninherited_level_default(self):
        raw = MC.load_raw()
        for name, row in list(raw["agents"].items()):
            level = row if isinstance(row, str) else row["level"]
            if level == "standard":
                raw["agents"][name] = {"level": "standard", "opencode": "glm-latest"}
        self.assertTrue(any("standard" in f for f in MC.check_reference_graph(raw)))

    def test_reference_graph_rejects_an_uninherited_codex_level_default(self):
        raw = MC.load_raw()
        for name, row in list(raw["agents"].items()):
            level = row if isinstance(row, str) else row["level"]
            if level == "standard":
                override = dict(row) if isinstance(row, dict) else {"level": level}
                override["codex"] = dict(raw["levels"]["standard"]["codex"])
                raw["agents"][name] = override
        findings = MC.check_reference_graph(raw)
        self.assertTrue(any(
            "levels.standard.codex: every agent at this level overrides it" in finding
            for finding in findings
        ))


class NonStringKeyTests(unittest.TestCase):
    """A YAML mapping key need not be a string, and the rules must not crash on one.

    `123: standard` under `agents:` is legal YAML; the PyYAML path constructs
    the key as `int`. Every rule that sorted a document-derived key set then
    raised `TypeError: '<' not supported between instances of 'str' and 'int'`.
    That is not a cosmetic crash: `validate-catalog.py` and
    `generate-opencode-agents.py` each promise exit 2 with a message on stderr
    for a bad catalog, and an unhandled `TypeError` gives exit 1, a traceback,
    and empty stdout — where exit-1 stdout is contractually the JSON report.
    So these tests assert a FINDING, not merely "no crash".
    """

    def _raw_with_key(self, key):
        raw = MC.load_raw()
        raw["agents"] = {key: "standard", **raw["agents"]}
        return raw

    def test_v0_reports_a_non_string_roster_key_rather_than_raising(self):
        findings = MC.check_shape(self._raw_with_key(123))
        self.assertTrue(any("must be a string" in f and "123" in f for f in findings))

    def test_v0_handles_a_boolean_roster_key(self):
        # `true:` and `yes:` are the other unquoted keys PyYAML does not
        # deliver as strings, and `bool` sorts against `str` no better.
        findings = MC.check_shape(self._raw_with_key(True))
        self.assertTrue(any("must be a string" in f for f in findings))

    def test_v1_roster_check_does_not_raise_on_a_non_string_key(self):
        # V1 is only reached after V0 is clean, so this is defense in depth —
        # but `check_roster` is a public function and a caller may run it
        # alone, which is exactly how the sort was reached in the report.
        #
        # `drop=` is load-bearing in this fixture. The stale set must contain
        # BOTH the int key and a string key: sorting a one-element set never
        # compares anything, so without a second stale key of the other type
        # the mutant "remove `key=repr`" survives and the test proves nothing.
        with tempfile.TemporaryDirectory() as td:
            agents = _agents_fixture(Path(td), drop="wayfinder")
            findings = MC.check_roster(self._raw_with_key(123), agents)
        blob = " ".join(findings)
        self.assertIn("123", blob)
        self.assertIn("wayfinder", blob)

    def test_v0_does_not_raise_on_a_non_string_level_key(self):
        # `levels` is sorted twice inside V0's key-set comparison; a non-string
        # key beside the three real ones is the mixed sort.
        raw = MC.load_raw()
        raw["levels"] = {7: {}, **raw["levels"]}
        findings = MC.check_shape(raw)
        self.assertTrue(any("`levels` key set must be exactly" in f for f in findings))

    def test_v2_reference_graph_does_not_raise_on_a_non_string_key(self):
        # `_coerce_row` accepts the VALUE, so the row survives into the sort.
        self.assertIsInstance(MC.check_reference_graph(self._raw_with_key(123)), list)

    def test_non_string_top_level_key_is_reported_not_raised(self):
        # Two extra keys of different types is the minimum that makes the
        # top-level `sorted()` compare an int with a str.
        raw = MC.load_raw()
        raw[42] = "x"
        raw["zzz-unknown"] = "y"
        findings = MC.check_shape(raw)
        self.assertTrue(any("unknown top-level key" in f for f in findings))

    def test_load_translates_a_non_string_roster_key_into_a_spec_violation(self):
        """End to end: the exit-code contract's exception type, not a TypeError."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            body = MC.CATALOG_PATH.read_text(encoding="utf-8").replace(
                "agents:\n  architect:", "agents:\n  123: standard\n  architect:", 1
            )
            path = tmp / "models.yml"
            path.write_text(body, encoding="utf-8")
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertIn("123", str(ctx.exception))
        self.assertIn("must be a string", str(ctx.exception))


class SourceLeafSymlinkTests(unittest.TestCase):
    """[SECURITY:S5] A symlinked `crux/agents/*.md` is refused at the READ.

    `check_roster` deliberately still counts a symlinked leaf as present — see
    the note in that function: a V1 finding closes `validate-catalog.py`'s
    [SECURITY:S3] gate, which would silence rule V6 and make
    `_agent_md_path`'s containment layer dead code for the one case it exists
    to catch. The refusal therefore lives on the two `parse_source` reads,
    which are what project a leaf's bytes into a generated agent file.
    """

    def test_check_roster_still_counts_a_symlinked_leaf_as_present(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            agents = _agents_fixture(tmp, drop="wayfinder")
            victim = tmp / "outside.md"
            victim.write_text("---\nname: wayfinder\n---\nPLANTED\n", encoding="utf-8")
            (agents / "wayfinder.md").symlink_to(victim)
            # No finding: the bijection holds, and refusing here would close
            # the gate that keeps V6's containment layer live.
            self.assertEqual(MC.check_roster(MC.load_raw(), agents), [])


if __name__ == "__main__":
    unittest.main()
