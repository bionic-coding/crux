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

import re
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


# The two agents the Claude Code override exception covers, and the model it
# selects. Named once so a re-point of the override moves one line here.
CLAUDE_OVERRIDES = {"commander": "claude-opus-5-5", "night-gardener": "claude-opus-5-5"}


def _agent_row_re(agent: str) -> re.Pattern[str]:
    """An agent row's head, anchored on STRUCTURE: its name and its `level:` line.

    Never on a model value. The owner picks those, and a fixture that spells
    one out goes inert the next time it changes. An optional `claude:` line
    directly under `level:` is captured so a fixture can replace or drop it.
    """
    return re.compile(
        rf"^(  {re.escape(agent)}:\n    level: \S+\n)(    claude: \S+\n)?", re.M
    )


def _set_agent_claude(text: str, agent: str, value: str | None) -> str:
    """Set (or, with None, remove) one agent row's Claude Code override.

    Refuses a fixture whose anchor no longer occurs: a silent zero-match
    substitution would validate the pristine catalog and pass for nothing.
    """
    line = "" if value is None else f"    claude: {value}\n"
    out, count = _agent_row_re(agent).subn(lambda m: m.group(1) + line, text)
    if count != 1:
        raise AssertionError(f"fixture inert: agent row {agent!r} not found as a mapping row")
    return out


def _strip_claude_overrides(text: str) -> str:
    """The shipped catalog with every agent's Claude Code override removed."""
    for agent in sorted(CLAUDE_OVERRIDES):
        text = _set_agent_claude(text, agent, None)
    return text


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
            "architect":      ("opus",   "opus-latest",   "gpt-6-sol",     "high"),
            "brainstormer":   ("opus",   "opus-latest",   "gpt-6-sol",     "high"),
            "commander":      ("claude-opus-5-5", "glm-latest", "gpt-6-astra", "high"),
            "dev-lead":       ("opus",   "sol-latest",    "gpt-6-sol",     "high"),
            "developer":      ("sonnet", "deepseek-flash", "gpt-6-sol",     "high"),
            "historian":      ("sonnet", "glm-latest",    "gpt-6-sol",     "high"),
            "librarian":      ("sonnet", "glm-latest",    "gpt-6-sol",     "high"),
            "night-gardener": ("claude-opus-5-5", "opus-latest", "gpt-6-astra", "high"),
            "reviewer":       ("claude-opus-5-5", "sol-latest", "gpt-6-sol", "xhigh"),
            "wayfinder":      ("sonnet", "glm-latest",    "gpt-6-sol",     "high"),
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

    def test_opencode_assignments_follow_the_owner_lineup(self):
        """The OpenCode column: flagship defaults to Opus, three agents override.

        architect and brainstormer carry no override, so they inherit the
        flagship default. kimi-latest stays declared as a parked alternate that
        no agent resolves through.
        """
        catalog = MC.load()
        self.assertEqual(catalog.aliases["opus-latest"], "openrouter/anthropic/claude-opus-5.5")
        self.assertEqual(catalog.aliases["sol-latest"], "openrouter/openai/gpt-6-sol")
        self.assertEqual(catalog.aliases["kimi-latest"], "openrouter/moonshotai/kimi-k3")
        self.assertEqual(catalog.levels["flagship"].opencode, "opus-latest")
        for name in ("architect", "brainstormer"):
            with self.subTest(agent=name):
                self.assertEqual(catalog.agents[name].level, "flagship")
                self.assertIsNone(catalog.agents[name].opencode)
        self.assertEqual(catalog.agents["dev-lead"].opencode, "sol-latest")
        self.assertEqual(catalog.agents["night-gardener"].opencode, "opus-latest")
        self.assertEqual(catalog.agents["reviewer"].opencode, "sol-latest")
        self.assertNotIn("kimi-latest", {catalog.opencode_alias(n) for n in catalog.agents})

    def test_apex_uses_astra_while_flagship_keeps_sol_at_high_effort(self):
        catalog = MC.load()
        apex, flagship = catalog.levels["apex"], catalog.levels["flagship"]
        # Apex pins Opus 5.5 on Claude; flagship retains its family alias.
        self.assertEqual(apex.claude, "claude-opus-5-5")
        self.assertEqual(flagship.claude, "opus")
        self.assertEqual(apex.codex.model, "gpt-6-astra")
        self.assertEqual(flagship.codex.model, "gpt-6-sol")
        # GPT-6 has no Terra, so standard selects Sol too; the two rungs stay
        # distinct on their Claude and OpenCode cells (rule V8).
        standard = catalog.levels["standard"]
        self.assertEqual(standard.codex.model, "gpt-6-sol")
        self.assertEqual(standard.codex.reasoning_effort, "high")
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
            model="gpt-6-sol",
            reasoning_effort="xhigh",
            verified="2026-09-22",
            source="OpenAI GPT-6 Sol model documentation and Codex 0.155.1 models_cache.json checked 2026-09-22",
        )
        self.assertEqual(catalog.agents["reviewer"].codex, expected)
        self.assertEqual(catalog.resolve("reviewer").codex, expected)

    def test_agent_without_a_codex_override_falls_back_to_its_level(self):
        catalog = MC.load()
        self.assertIsNone(catalog.agents["commander"].codex)
        self.assertEqual(catalog.resolve("commander").codex, catalog.levels["apex"].codex)


class ClaudeOverrideResolutionTests(unittest.TestCase):
    """A per-agent `claude` key wins over the level's Claude cell, and moves nothing else."""

    def test_the_overrides_are_exactly_the_authorized_agents(self):
        catalog = MC.load()
        overrides = {name: row.claude for name, row in catalog.agents.items() if row.claude is not None}
        self.assertEqual(overrides, CLAUDE_OVERRIDES)

    def test_an_override_wins_over_the_level_cell(self):
        catalog = MC.load()
        self.assertEqual(catalog.levels["apex"].claude, "claude-opus-5-5")
        for agent, value in sorted(CLAUDE_OVERRIDES.items()):
            with self.subTest(agent=agent):
                self.assertEqual(catalog.agents[agent].level, "apex")
                self.assertEqual(catalog.resolve(agent).claude, value)

    def test_reviewer_inherits_the_apex_opus_assignment(self):
        catalog = MC.load()
        self.assertIsNone(catalog.agents["reviewer"].claude)
        self.assertEqual(catalog.levels["apex"].claude, "claude-opus-5-5")
        self.assertEqual(catalog.resolve("reviewer").claude, "claude-opus-5-5")
        self.assertEqual(catalog.resolve("reviewer").opencode, catalog.aliases["sol-latest"])
        self.assertEqual(catalog.resolve("reviewer").codex.model, "gpt-6-sol")

    def test_removing_an_override_returns_the_agent_to_its_level_cell(self):
        # The same agent, with and without the key: the discriminating pair.
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(tmp, lambda t: _set_agent_claude(t, "commander", None))
            catalog = MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertIsNone(catalog.agents["commander"].claude)
        self.assertEqual(catalog.resolve("commander").claude, "claude-opus-5-5")
        self.assertEqual(catalog.resolve("night-gardener").claude, "claude-opus-5-5")

    def test_an_inherit_override_resolves_to_inherit(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(tmp, lambda t: _set_agent_claude(t, "night-gardener", "inherit"))
            catalog = MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertEqual(catalog.resolve("night-gardener").claude, "inherit")

    def test_apex_repoint_moves_only_reviewers_claude_assignment(self):
        """Compare the prior apex cell with the new cell across all ten roles."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            before = MC.load(
                catalog_path=_catalog_copy(
                    tmp,
                    lambda text: text.replace(
                        "  apex:\n    claude: claude-opus-5-5\n",
                        "  apex:\n    claude: fable\n",
                        1,
                    ),
                ),
                agents_dir=_agents_fixture(tmp),
            )
        after = MC.load()
        self.assertEqual(set(after.agents), EXPECTED_AGENTS)
        changed_claude = set()
        for agent in sorted(EXPECTED_AGENTS):
            with self.subTest(agent=agent):
                old, new = before.resolve(agent), after.resolve(agent)
                self.assertEqual(new.codex, old.codex)
                self.assertEqual(new.opencode, old.opencode)
                self.assertEqual(after.opencode_alias(agent), before.opencode_alias(agent))
                if new.claude != old.claude:
                    changed_claude.add(agent)
        self.assertEqual(changed_claude, {"reviewer"})


class FailClosedTests(unittest.TestCase):
    def test_historical_v1_schema_is_refused_without_migration(self):
        """AC-7: an older schema is refused, not migrated."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "models.yml"
            path.write_text(V1_BODY, encoding="utf-8")
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=MC.AGENTS_DIR)
        self.assertIn("schema_version", str(ctx.exception))

    def _refuse_version(self, version: str) -> str:
        current = f'schema_version: "{MC.SCHEMA_VERSION}"'
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            text = MC.CATALOG_PATH.read_text(encoding="utf-8")
            self.assertIn(current, text, "fixture inert: the version line moved")
            path = _catalog_copy(
                tmp, lambda t: t.replace(current, f'schema_version: "{version}"', 1)
            )
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        return str(ctx.exception)

    def test_the_reader_is_at_schema_version_4(self):
        self.assertEqual(MC.SCHEMA_VERSION, "4")

    def test_v2_schema_is_refused_without_migration_or_defaults(self):
        self.assertIn("schema_version must be '4'", self._refuse_version("2"))

    def test_v3_schema_is_refused_without_migration(self):
        # A version-3 reader refused anything but "3"; a version-4 reader
        # refuses "3" in turn. The body is otherwise the shipped catalog, so
        # the version is the only defect.
        self.assertIn("schema_version must be '4', got '3'", self._refuse_version("3"))

    def test_load_rejects_a_non_string_claude_override(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(tmp, lambda t: _set_agent_claude(t, "commander", "5"))
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertIn("agents.'commander'.claude must be a string", str(ctx.exception))

    def test_load_rejects_a_level_claude_cell_every_agent_overrides(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(tmp, lambda t: _set_agent_claude(t, "reviewer", "fable"))
            with self.assertRaises(MC.SpecViolation) as ctx:
                MC.load(catalog_path=path, agents_dir=_agents_fixture(tmp))
        self.assertIn("levels.apex.claude: every agent at this level overrides it", str(ctx.exception))

    def test_load_rejects_a_non_mapping_reviewer_codex_override(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = _catalog_copy(
                tmp,
                lambda text: text.replace(
                    "    codex:\n"
                    "      model: gpt-6-sol\n"
                    "      reasoning_effort: xhigh\n"
                    '      verified: "2026-09-22"\n'
                    '      source: "OpenAI GPT-6 Sol model documentation and Codex 0.155.1 models_cache.json checked 2026-09-22"',
                    "    codex: gpt-6-sol",
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

    def test_shape_accepts_an_agent_row_carrying_a_string_claude_key(self):
        raw = MC.load_raw()
        raw["agents"]["architect"] = {"level": "flagship", "claude": "opus"}
        self.assertEqual(MC.check_shape(raw), [])

    def test_shape_rejects_a_non_string_claude_override(self):
        for value in (5, ["opus"], {"model": "opus"}, None, True):
            with self.subTest(value=value):
                raw = MC.load_raw()
                raw["agents"]["architect"] = {"level": "flagship", "claude": value}
                # The row name is interpolated with `!r` — a whitespace-only or
                # empty roster key is otherwise invisible in the finding.
                self.assertIn(
                    "agents.'architect'.claude must be a string", MC.check_shape(raw)
                )

    def test_shape_rejects_an_unknown_agent_row_key_and_names_the_override_set(self):
        raw = MC.load_raw()
        raw["agents"]["architect"] = {"level": "flagship", "claude_model": "opus"}
        findings = MC.check_shape(raw)
        self.assertTrue(any(
            "agents.'architect': unknown key(s) ['claude_model']" in f
            and "'claude', 'codex', 'opencode'" in f
            for f in findings
        ), findings)
        self.assertFalse(any("silently ignored" in f for f in findings), findings)

    def test_shape_rejects_a_partial_agent_codex_override(self):
        raw = MC.load_raw()
        raw["agents"]["reviewer"]["codex"] = {"model": "gpt-6-sol"}
        findings = MC.check_shape(raw)
        self.assertTrue(any(
            "agents.'reviewer'.codex key set must be exactly" in finding
            for finding in findings
        ))

    def test_shape_rejects_an_agent_codex_override_with_an_extra_field(self):
        raw = MC.load_raw()
        raw["agents"]["reviewer"]["codex"] = {
            "model": "gpt-6-sol",
            "reasoning_effort": "xhigh",
            "verified": "2026-09-22",
            "source": "OpenAI GPT-6 Sol model documentation and Codex 0.155.1 models_cache.json checked 2026-09-22",
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

    def test_reference_graph_rejects_an_uninherited_claude_level_default(self):
        raw = MC.load_raw()
        raw["agents"]["reviewer"]["claude"] = "fable"
        findings = MC.check_reference_graph(raw)
        self.assertIn(
            "levels.apex.claude: every agent at this level overrides it — "
            "a default within a rung that nothing inherits",
            findings,
        )

    def test_reference_graph_accepts_a_claude_cell_one_agent_still_inherits(self):
        # The positive control for the clause above: the shipped apex level has
        # two overridden agents and one inheritor, and that is legal.
        raw = MC.load_raw()
        self.assertEqual(
            [f for f in MC.check_reference_graph(raw) if ".claude" in f], []
        )
        self.assertNotIn("claude", raw["agents"]["reviewer"])


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
