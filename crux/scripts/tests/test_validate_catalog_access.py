"""Grammar tests for the access-need keys in validate-catalog.py.

Skill keys: `metadata.requires_access` (required) and `metadata.supplied_access`
(optional, strictly below requires_access). Agent keys: `metadata.shell_scope`
and `metadata.skill_lanes` (optional, double-quoted flat strings).

Every fixture is parsed both ways, with the minimal line parser and with
PyYAML, and the two must agree: the catalog runs on either. Fixtures only;
nothing here reads the live crux/ tree.

Stdlib plus PyYAML when present (the PyYAML half skips without it).
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import yaml  # type: ignore

    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "crux" / "scripts" / "validate-catalog.py"
ALLOWED_MODELS = {"fable", "opus", "sonnet", "haiku", "inherit"}


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_catalog_access_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validator = _load_validator()


def _block(text: str) -> str:
    lines = text.splitlines()
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    return "\n".join(lines[1:end])


def _parsers():
    parsers = [("minimal", validator._parse_minimal_yaml)]
    if HAVE_YAML:
        parsers.append(("pyyaml", yaml.safe_load))
    return parsers


def _note_missing_pyyaml(case: unittest.TestCase) -> None:
    """Report the dropped PyYAML half as a skipped subTest, never silently."""
    if not HAVE_YAML:
        with case.subTest(parser="pyyaml"):
            case.skipTest("PyYAML is not installed; only the minimal parser half ran")


# ───────────────────────────── skill keys ─────────────────────────────────

SKILL = """\
---
name: demo
description: Use when the user wants a demo.
metadata:
  tags: "demo"
  bundles: "crux-core"
  risk_level: "low"
{extra}---

# Demo
"""


def _validate_skill(tmp: Path, extra: str, toplevel: str = "", description: str = ""):
    """Return {parser: (entry, messages)} for one fixture, parsed both ways."""
    text = SKILL.format(extra=extra)
    if description:
        text = text.replace("description: Use when the user wants a demo.\n", description, 1)
    if toplevel:
        text = text.replace("metadata:\n", toplevel + "metadata:\n", 1)
    path = tmp / "skills" / "demo" / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    out = {}
    for label, parse in _parsers():
        lifted, shape = validator._lift_metadata(parse(_block(text)))
        entry, errs = validator.validate_skill_frontmatter(lifted, path, tmp)
        out[label] = (entry, shape + [e["error"] for e in errs])
    return out


class SkillAccessGrammarTests(unittest.TestCase):
    def assertBoth(self, results, check):
        self.assertTrue(results, "no parser ran")
        _note_missing_pyyaml(self)
        for label, (entry, messages) in results.items():
            with self.subTest(parser=label):
                check(entry, messages)

    def _skill(self, extra: str, toplevel: str = "", description: str = ""):
        with tempfile.TemporaryDirectory() as t:
            return _validate_skill(Path(t), extra, toplevel, description)

    def test_the_ladder_is_the_five_ordered_tokens(self):
        self.assertEqual(
            validator.ACCESS_LADDER,
            ("read-local", "run-plugin-script", "write-run", "write-tree", "write-host"),
        )

    def test_every_ladder_token_is_accepted_and_projected(self):
        for token in validator.ACCESS_LADDER:
            results = self._skill(f'  requires_access: "{token}"\n')

            def check(entry, messages, token=token):
                self.assertEqual(messages, [])
                self.assertEqual(entry["requires_access"], token)
                self.assertNotIn("supplied_access", entry)

            self.assertBoth(results, check)

    def test_missing_requires_access_is_fatal_and_defaults_nothing(self):
        def check(entry, messages):
            self.assertIsNone(entry)
            self.assertTrue(any("requires_access" in m and "missing" in m for m in messages), messages)

        self.assertBoth(self._skill(""), check)

    def test_empty_requires_access_is_refused(self):
        def check(entry, messages):
            self.assertIsNone(entry)
            self.assertTrue(any("requires_access" in m for m in messages), messages)

        self.assertBoth(self._skill('  requires_access: ""\n'), check)

    def test_unknown_requires_access_is_refused_by_name(self):
        def check(entry, messages):
            self.assertTrue(any("'sudo'" in m and "requires_access" in m for m in messages), messages)

        self.assertBoth(self._skill('  requires_access: "sudo"\n'), check)

    def test_list_requires_access_is_refused_as_a_non_string(self):
        def check(entry, messages):
            self.assertTrue(
                any("requires_access" in m and "string" in m for m in messages), messages
            )

        self.assertBoth(self._skill("  requires_access: [read-local]\n"), check)

    def test_top_level_requires_access_is_refused(self):
        def check(entry, messages):
            self.assertTrue(
                any("'requires_access'" in m and "under `metadata:`" in m for m in messages), messages
            )

        self.assertBoth(self._skill('  requires_access: "read-local"\n', toplevel='requires_access: "read-local"\n'), check)

    def test_supplied_access_strictly_below_is_accepted_and_projected(self):
        extra = '  requires_access: "run-plugin-script"\n  supplied_access: "read-local"\n'

        def check(entry, messages):
            self.assertEqual(messages, [])
            self.assertEqual(entry["supplied_access"], "read-local")

        self.assertBoth(self._skill(extra), check)

    def test_supplied_access_equal_to_requires_access_fails(self):
        extra = '  requires_access: "write-run"\n  supplied_access: "write-run"\n'

        def check(entry, messages):
            self.assertTrue(any("supplied_access" in m and "below" in m for m in messages), messages)

        self.assertBoth(self._skill(extra), check)

    def test_supplied_access_above_requires_access_fails(self):
        extra = '  requires_access: "read-local"\n  supplied_access: "write-tree"\n'

        def check(entry, messages):
            self.assertTrue(any("supplied_access" in m and "below" in m for m in messages), messages)

        self.assertBoth(self._skill(extra), check)

    def test_supplied_access_unknown_empty_or_list_fails(self):
        for value in ('"sudo"', '""', "[read-local]"):
            extra = f'  requires_access: "write-tree"\n  supplied_access: {value}\n'

            def check(entry, messages, value=value):
                self.assertTrue(any("supplied_access" in m for m in messages), (value, messages))

            self.assertBoth(self._skill(extra), check)

    def test_supplied_access_without_requires_access_does_not_hide_the_missing_key(self):
        def check(entry, messages):
            self.assertIsNone(entry)
            self.assertTrue(any("requires_access" in m and "missing" in m for m in messages), messages)

        self.assertBoth(self._skill('  supplied_access: "read-local"\n'), check)

    def test_duplicate_requires_access_is_fatal_whichever_value_comes_last(self):
        # A second line lowering the need must not win silently.
        for first, last in (("write-tree", "read-local"), ("read-local", "write-tree")):
            extra = f'  requires_access: "{first}"\n  requires_access: "{last}"\n'

            def check(entry, messages):
                self.assertIsNone(entry)
                self.assertIn("requires_access appears 2 times under metadata:; declare it once", messages)

            self.assertBoth(self._skill(extra), check)
        # Single-line baseline: the same text with one line is clean.
        def clean(entry, messages):
            self.assertEqual(messages, [])
            self.assertEqual(entry["requires_access"], "read-local")

        self.assertBoth(self._skill('  requires_access: "read-local"\n'), clean)

    def test_duplicate_supplied_access_is_refused(self):
        extra = (
            '  requires_access: "write-tree"\n'
            '  supplied_access: "read-local"\n'
            '  supplied_access: "write-run"\n'
        )

        def check(entry, messages):
            self.assertIn("supplied_access appears 2 times under metadata:; declare it once", messages)

        self.assertBoth(self._skill(extra), check)

        def clean(entry, messages):
            self.assertEqual(messages, [])

        self.assertBoth(
            self._skill('  requires_access: "write-tree"\n  supplied_access: "read-local"\n'), clean
        )

    # Spellings of one key that a raw `^key:` line count misses. Each puts a
    # second `requires_access` / `supplied_access` after the first, in a form
    # PyYAML (and, after the fix, the minimal parser) reads as the same key.
    SKILL_REPEAT_SPELLINGS = (
        ("space-before-colon", '  {key} : "{val}"\n'),
        ("double-quoted-key", '  "{key}": "{val}"\n'),
        ("single-quoted-key", "  '{key}': \"{val}\"\n"),
    )

    def test_repeat_spellings_of_an_access_key_are_refused(self):
        for key, base in (
            ("requires_access", '  requires_access: "write-tree"\n'),
            ("supplied_access", '  requires_access: "write-tree"\n  supplied_access: "read-local"\n'),
        ):
            for name, template in self.SKILL_REPEAT_SPELLINGS:
                extra = base + template.format(key=key, val="read-local")

                def check(entry, messages, key=key):
                    self.assertIn(f"{key} appears 2 times under metadata:; declare it once", messages)

                with self.subTest(key=key, spelling=name):
                    self.assertBoth(self._skill(extra), check)

    def test_explicit_question_mark_key_under_metadata_is_refused(self):
        extra = '  ? requires_access\n  : "read-local"\n'

        def check(entry, messages):
            self.assertTrue(
                any("explicit `?` keys are not allowed under metadata:" in m for m in messages),
                messages,
            )

        self.assertBoth(self._skill(extra), check)

    def test_duplicate_risk_level_is_refused(self):
        # SKILL already declares risk_level once; any metadata key repeats are refused.
        extra = '  risk_level: "high"\n  requires_access: "read-local"\n'

        def check(entry, messages):
            self.assertIn("risk_level appears 2 times under metadata:; declare it once", messages)

        self.assertBoth(self._skill(extra), check)

    def test_indented_key_text_inside_a_block_scalar_is_not_a_repeat(self):
        description = (
            "description: |\n"
            "  Use when the user wants a demo.\n"
            '  requires_access: "read-local"\n'
        )

        def check(entry, messages):
            self.assertEqual(messages, [])
            self.assertEqual(entry["requires_access"], "write-tree")

        self.assertBoth(self._skill('  requires_access: "write-tree"\n', description=description), check)

    def test_scan_and_pyyaml_key_readers_agree_on_every_spelling(self):
        if not HAVE_YAML:
            self.skipTest("PyYAML is not installed; the agreement check needs both readers")
        bodies = [
            'metadata:\n  a: "1"\n  a : "2"\n',
            'metadata:\n  a: "1"\n  "a": "2"\n',
            "metadata:\n  a: \"1\"\n  'a': \"2\"\n",
            'metadata:\n  a: "1"\n  b: "2"\n',
            'description: |\n  a: "x"\nmetadata:\n  a: "1"\n',
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.assertEqual(
                    validator._metadata_keys_by_scan(body),
                    validator._metadata_keys_by_yaml(body),
                )

    def test_projection_puts_requires_access_after_risk_level_then_supplied_access(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _validate_skill(tmp, '  requires_access: "write-run"\n  supplied_access: "read-local"\n  requires_env: "FOO"\n')
            entries, errors = validator.regenerate_skills_json(tmp, verbose=False)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 1)
        keys = list(entries[0])
        at = keys.index("risk_level")
        self.assertEqual(keys[at + 1 : at + 3], ["requires_access", "supplied_access"])
        self.assertEqual(keys[at + 3], "requires_env")
        text = validator.serialize_skills_json(entries)
        self.assertIn('"requires_access": "write-run"', text)

    def test_projection_omits_an_undeclared_supplied_access(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            _validate_skill(tmp, '  requires_access: "read-local"\n')
            entries, errors = validator.regenerate_skills_json(tmp, verbose=False)
        self.assertEqual(errors, [])
        self.assertNotIn("supplied_access", entries[0])
        self.assertEqual(entries[0]["requires_access"], "read-local")


# ───────────────────────────── agent keys ─────────────────────────────────

AGENT = """\
---
name: {name}
description: Use when the user wants X.
tools: {tools}
model: sonnet
skills: {skills}
{disallowed}metadata:
  tags: "agents"
  bundles: "crux-agents"
  risk_level: "low"
{extra}---

# {name}
"""


def _agent_text(name="solo", tools="Read, Grep, Glob, Skill", skills="[]", extra="", disallowed=""):
    return AGENT.format(name=name, tools=tools, skills=skills, extra=extra, disallowed=disallowed)


def _validate_agent(text: str, name="solo", skill_ids=("alpha", "beta", "gamma"), siblings=("architect", "historian")):
    """Return {parser: (entry, messages)}; asserts both parsers saw no parse error."""
    out = {}
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for s in skill_ids:
            d = tmp / "skills" / s
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        agents = tmp / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        for sib in siblings:
            (agents / f"{sib}.md").write_text(_agent_text(name=sib), encoding="utf-8")
        path = agents / f"{name}.md"
        path.write_text(text, encoding="utf-8")
        fm_min, err = validator.extract_agent_frontmatter(path)
        assert err is None, err
        for label, fm in [("minimal", fm_min)] + ([("pyyaml", yaml.safe_load(_block(text)))] if HAVE_YAML else []):
            entry, errs = validator.validate_agent_frontmatter(
                fm, path, tmp, ALLOWED_MODELS, set(skill_ids)
            )
            out[label] = (entry, [(e["field"], e["error"]) for e in errs if e.get("severity") != "warning"])
    return out


def _json_of(text: str, name="solo", skill_ids=("alpha", "beta", "gamma"), siblings=("architect", "historian")):
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for s in skill_ids:
            d = tmp / "skills" / s
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        agents = tmp / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        (tmp / "catalog").mkdir()
        for sib in siblings:
            (agents / f"{sib}.md").write_text(_agent_text(name=sib), encoding="utf-8")
        (agents / f"{name}.md").write_text(text, encoding="utf-8")
        models_yml = REPO_ROOT / "crux" / "catalog" / "models.yml"
        (tmp / "catalog" / "models.yml").write_text(models_yml.read_text(encoding="utf-8"), encoding="utf-8")
        entries, errors = validator.regenerate_agents_json(tmp, False, set(skill_ids))
    return entries, errors


class AgentAccessGrammarTests(unittest.TestCase):
    def results(self, **kw):
        res = _validate_agent(_agent_text(**kw))
        self.assertTrue(res)
        return res

    def assertErr(self, res, field, fragment):
        _note_missing_pyyaml(self)
        for label, (entry, errs) in res.items():
            with self.subTest(parser=label):
                self.assertTrue(
                    any(f == field and fragment in m for f, m in errs),
                    f"no {field!r} error containing {fragment!r}: {errs}",
                )

    def assertClean(self, res):
        _note_missing_pyyaml(self)
        for label, (entry, errs) in res.items():
            with self.subTest(parser=label):
                self.assertEqual(errs, [])
                self.assertIsNotNone(entry)

    # ── shell_scope ──
    def test_bash_without_edit_and_no_scope_fails(self):
        res = self.results(tools="Read, Grep, Glob, Bash, Skill")
        self.assertErr(res, "metadata.shell_scope", "must declare")

    def test_bash_with_edit_and_write_needs_no_scope(self):
        self.assertClean(self.results(tools="Read, Grep, Glob, Edit, Write, Bash, Skill"))

    def test_bash_with_only_edit_cannot_be_satisfied(self):
        # Edit without Write holds Bash without the pair (must declare) and
        # holds Edit (must not): both rules fire, so the role has to change.
        res = self.results(tools="Read, Edit, Bash, Skill")
        self.assertErr(res, "metadata.shell_scope", "must declare")

    def test_edit_with_a_scope_fails(self):
        res = self.results(
            tools="Read, Edit, Write, Bash, Skill", extra='  shell_scope: "write-run"\n'
        )
        self.assertErr(res, "metadata.shell_scope", "Edit")

    def test_bash_without_edit_and_scope_up_to_write_run_passes(self):
        for token in ("read-local", "run-plugin-script", "write-run"):
            with self.subTest(token=token):
                self.assertClean(
                    self.results(
                        tools="Read, Bash, Skill", extra=f'  shell_scope: "{token}"\n'
                    )
                )

    def test_scope_above_write_run_fails(self):
        for token in ("write-tree", "write-host"):
            res = self.results(tools="Read, Bash, Skill", extra=f'  shell_scope: "{token}"\n')
            self.assertErr(res, "metadata.shell_scope", "write-run")

    def test_unknown_or_empty_scope_fails(self):
        for token in ("root", ""):
            res = self.results(tools="Read, Bash, Skill", extra=f'  shell_scope: "{token}"\n')
            self.assertErr(res, "metadata.shell_scope", "ladder")

    def test_no_bash_may_declare_only_read_local(self):
        self.assertClean(self.results(extra='  shell_scope: "read-local"\n'))
        res = self.results(extra='  shell_scope: "run-plugin-script"\n')
        self.assertErr(res, "metadata.shell_scope", "read-local")

    def test_a_denied_bash_is_not_effective(self):
        # tools lists Bash but disallowedTools removes it: effective no-Bash.
        res = self.results(
            tools="Read, Bash, Skill",
            disallowed="disallowedTools: Bash\n",
            extra='  shell_scope: "run-plugin-script"\n',
        )
        self.assertErr(res, "metadata.shell_scope", "read-local")
        self.assertClean(
            self.results(tools="Read, Bash, Skill", disallowed="disallowedTools: Bash\n")
        )

    def test_unquoted_scope_is_refused_on_the_raw_line(self):
        res = self.results(tools="Read, Bash, Skill", extra="  shell_scope: write-run\n")
        self.assertErr(res, "metadata.shell_scope", "double-quoted")

    def test_scope_projects_as_a_string_after_risk_level(self):
        entries, errors = _json_of(
            _agent_text(tools="Read, Bash, Skill", extra='  shell_scope: "run-plugin-script"\n')
        )
        self.assertEqual([e for e in errors if e.get("severity") != "warning"], [])
        solo = next(e for e in entries if e["id"] == "solo")
        keys = list(solo)
        self.assertEqual(solo["shell_scope"], "run-plugin-script")
        self.assertEqual(keys[keys.index("risk_level") + 1], "shell_scope")

    def test_undeclared_scope_is_absent_from_the_projection(self):
        entries, _ = _json_of(_agent_text())
        solo = next(e for e in entries if e["id"] == "solo")
        self.assertNotIn("shell_scope", solo)
        self.assertNotIn("skill_lanes", solo)

    def test_duplicate_shell_scope_is_refused(self):
        extra = '  shell_scope: "read-local"\n  shell_scope: "write-run"\n'
        res = self.results(tools="Read, Bash, Skill", extra=extra)
        self.assertErr(res, "metadata.shell_scope", "shell_scope appears 2 times under metadata:; declare it once")
        self.assertClean(self.results(tools="Read, Bash, Skill", extra='  shell_scope: "write-run"\n'))

    def test_duplicate_skill_lanes_is_refused(self):
        extra = '  skill_lanes: "alpha=returns-to-caller"\n  skill_lanes: "beta=returns-to-caller"\n'
        res = self.results(skills="[alpha, beta]", extra=extra)
        self.assertErr(res, "metadata.skill_lanes", "skill_lanes appears 2 times under metadata:; declare it once")
        self.assertClean(
            self.results(skills="[alpha, beta]", extra='  skill_lanes: "alpha=returns-to-caller"\n')
        )

    AGENT_REPEAT_SPELLINGS = (
        ("space-before-colon", '  {key} : "{val}"\n'),
        ("double-quoted-key", '  "{key}": "{val}"\n'),
        ("single-quoted-key", "  '{key}': \"{val}\"\n"),
    )

    def test_repeat_spellings_of_shell_scope_are_refused(self):
        for name, template in self.AGENT_REPEAT_SPELLINGS:
            extra = '  shell_scope: "read-local"\n' + template.format(key="shell_scope", val="write-run")
            with self.subTest(spelling=name):
                res = self.results(tools="Read, Bash, Skill", extra=extra)
                self.assertErr(
                    res, "metadata.shell_scope", "shell_scope appears 2 times under metadata:; declare it once"
                )

    def test_repeat_spellings_of_skill_lanes_are_refused(self):
        for name, template in self.AGENT_REPEAT_SPELLINGS:
            extra = '  skill_lanes: "alpha=returns-to-caller"\n' + template.format(
                key="skill_lanes", val="beta=returns-to-caller"
            )
            with self.subTest(spelling=name):
                res = self.results(skills="[alpha, beta]", extra=extra)
                self.assertErr(
                    res, "metadata.skill_lanes", "skill_lanes appears 2 times under metadata:; declare it once"
                )

    def test_explicit_question_mark_key_on_an_agent_is_refused(self):
        for key, kw in (
            ("shell_scope", {"tools": "Read, Bash, Skill"}),
            ("skill_lanes", {"skills": "[alpha]"}),
        ):
            value = "write-run" if key == "shell_scope" else "alpha=returns-to-caller"
            extra = f'  ? {key}\n  : "{value}"\n'
            with self.subTest(key=key):
                res = self.results(extra=extra, **kw)
                self.assertErr(
                    res, f"metadata.{key}", "explicit `?` keys are not allowed under metadata:"
                )

    def test_duplicate_agent_risk_level_is_refused(self):
        res = self.results(extra='  risk_level: "high"\n')
        self.assertErr(res, "metadata.risk_level", "risk_level appears 2 times under metadata:; declare it once")

    def test_space_before_colon_line_still_gets_the_quoted_value_check(self):
        # `shell_scope : write-run` is a raw line the old regex could not see.
        res = self.results(tools="Read, Bash, Skill", extra="  shell_scope : write-run\n")
        self.assertErr(res, "metadata.shell_scope", "extended metadata values are flat strings")

    def test_quoted_key_with_a_quoted_value_passes_the_value_check(self):
        res = self.results(tools="Read, Bash, Skill", extra='  "shell_scope": "write-run"\n')
        self.assertClean(res)

    def test_unquoted_scope_error_names_the_rule_without_an_adr_number(self):
        res = self.results(tools="Read, Bash, Skill", extra="  shell_scope: write-run\n")
        self.assertErr(res, "metadata.shell_scope", "extended metadata values are flat strings")
        for _label, (_entry, errs) in res.items():
            self.assertFalse(any("ADR-" in m for _f, m in errs), errs)

    # ── skill_lanes ──
    def lanes(self, value, skills="[alpha, beta]"):
        return self.results(skills=skills, extra=f'  skill_lanes: "{value}"\n')

    def test_valid_lanes_pass_and_trim_whitespace(self):
        self.assertClean(
            self.lanes("alpha=delegates:architect,  beta = returns-to-caller ")
        )

    def test_lanes_project_as_a_sorted_object_after_risk_level(self):
        entries, errors = _json_of(
            _agent_text(
                skills="[beta, alpha]",
                extra='  skill_lanes: "beta=returns-to-caller, alpha=delegates:architect"\n',
            )
        )
        self.assertEqual([e for e in errors if e.get("severity") != "warning"], [])
        solo = next(e for e in entries if e["id"] == "solo")
        keys = list(solo)
        self.assertEqual(
            solo["skill_lanes"], {"alpha": "delegates:architect", "beta": "returns-to-caller"}
        )
        self.assertEqual(list(solo["skill_lanes"]), ["alpha", "beta"])
        self.assertEqual(keys[keys.index("risk_level") + 1], "skill_lanes")
        self.assertIn('"skill_lanes": {', validator.serialize_agents_json(entries))

    def test_empty_lane_string_fails(self):
        self.assertErr(self.lanes(""), "metadata.skill_lanes", "empty")

    def test_empty_entry_fails(self):
        self.assertErr(
            self.lanes("alpha=returns-to-caller,,beta=returns-to-caller"),
            "metadata.skill_lanes",
            "empty entry",
        )

    def test_leading_and_trailing_commas_fail(self):
        self.assertErr(self.lanes(",alpha=returns-to-caller"), "metadata.skill_lanes", "leading comma")
        self.assertErr(self.lanes("alpha=returns-to-caller,"), "metadata.skill_lanes", "trailing comma")

    def test_undeclared_skill_fails(self):
        self.assertErr(
            self.lanes("gamma=returns-to-caller"), "metadata.skill_lanes", "does not declare"
        )

    def test_skill_named_twice_fails(self):
        self.assertErr(
            self.lanes("alpha=returns-to-caller, alpha=caller-supplies"),
            "metadata.skill_lanes",
            "twice",
        )

    def test_unknown_kind_fails(self):
        self.assertErr(self.lanes("alpha=relay"), "metadata.skill_lanes", "kind")

    def test_delegate_target_that_is_not_a_role_fails(self):
        self.assertErr(
            self.lanes("alpha=delegates:nobody"), "metadata.skill_lanes", "not a role"
        )

    def test_role_naming_itself_fails(self):
        self.assertErr(self.lanes("alpha=delegates:solo"), "metadata.skill_lanes", "itself")

    def test_unquoted_lanes_are_refused_on_the_raw_line(self):
        res = self.results(skills="[alpha]", extra="  skill_lanes: alpha=returns-to-caller\n")
        self.assertErr(res, "metadata.skill_lanes", "double-quoted")


class ParseSkillLanesTests(unittest.TestCase):
    def test_returns_mapping_and_no_errors_for_a_valid_string(self):
        lanes, errors = validator.parse_skill_lanes(
            "council=delegates:architect, log-work=delegates:historian, forge-skill=returns-to-caller"
        )
        self.assertEqual(errors, [])
        self.assertEqual(
            lanes,
            {
                "council": "delegates:architect",
                "log-work": "delegates:historian",
                "forge-skill": "returns-to-caller",
            },
        )

    def test_caller_supplies_is_a_kind(self):
        lanes, errors = validator.parse_skill_lanes("query-docs=caller-supplies")
        self.assertEqual((lanes, errors), ({"query-docs": "caller-supplies"}, []))

    def test_each_syntax_defect_yields_an_error_string(self):
        cases = {
            "": "empty",
            "   ": "empty",
            "a=returns-to-caller,,b=returns-to-caller": "empty entry",
            ",a=returns-to-caller": "leading comma",
            "a=returns-to-caller,": "trailing comma",
            "a": "'='",
            "Bad_Name=returns-to-caller": "skill name",
            "a=returns-to-caller, a=caller-supplies": "twice",
            "a=relay": "kind",
            "a=delegates:": "target",
            "a=delegates:Bad Role": "target",
        }
        for raw, fragment in cases.items():
            with self.subTest(raw=raw):
                _, errors = validator.parse_skill_lanes(raw)
                self.assertTrue(errors, "expected an error")
                self.assertTrue(
                    any(fragment in e for e in errors), f"{fragment!r} not in {errors}"
                )
                self.assertTrue(all(isinstance(e, str) for e in errors))

    def test_it_checks_syntax_only_not_context(self):
        # An undeclared skill and a self target are context checks, left to the
        # agent validator; the parser accepts them.
        lanes, errors = validator.parse_skill_lanes("whoever=delegates:anyone")
        self.assertEqual((lanes, errors), ({"whoever": "delegates:anyone"}, []))


# ───────────────────────── repeated top-level keys ─────────────────────────


def _lanes():
    """(label, context) per parser lane: PyYAML when present, and PyYAML hidden."""
    lanes = [("minimal", lambda: mock.patch.dict(sys.modules, {"yaml": None}))]
    if HAVE_YAML:
        lanes.append(("pyyaml", lambda: mock.patch.dict(sys.modules, {})))
    return lanes


SECOND_SKILL_BLOCK = (
    '{key}:\n  tags: "demo"\n  bundles: "crux-core"\n  risk_level: "low"\n'
    '  requires_access: "read-local"\n'
)
SECOND_AGENT_BLOCK = (
    '{key}:\n  tags: "agents"\n  bundles: "crux-agents"\n  risk_level: "low"\n'
    '  shell_scope: "write-run"\n'
)
TOP_LEVEL_SPELLINGS = (("plain", "metadata"), ("double-quoted", '"metadata"'))
REPEAT_MESSAGE = "metadata appears 2 times at the top level of the frontmatter; declare it once"


class RepeatedTopLevelKeyTests(unittest.TestCase):
    """A second top-level `metadata:` block must not replace the first.

    Both parsers keep the last of two equal top-level keys, so a second block
    could lower a skill's requires_access or raise an agent's shell_scope with
    no error. Each case runs through the regenerator, in both parser lanes.
    """

    def _skills(self, second: str):
        out = {}
        for label, lane in _lanes():
            with tempfile.TemporaryDirectory() as t, lane():
                tmp = Path(t)
                path = tmp / "skills" / "demo" / "SKILL.md"
                path.parent.mkdir(parents=True)
                text = SKILL.format(extra='  requires_access: "write-tree"\n')
                path.write_text(text.replace("---\n\n# Demo", second + "---\n\n# Demo", 1), encoding="utf-8")
                out[label] = validator.regenerate_skills_json(tmp, verbose=False)
        return out

    def _agents(self, second: str):
        out = {}
        text = _agent_text(tools="Read, Bash, Skill", extra='  shell_scope: "read-local"\n')
        text = text.replace("---\n\n# solo", second + "---\n\n# solo", 1)
        for label, lane in _lanes():
            with lane():
                out[label] = _json_of(text)
        return out

    def test_control_one_block_projects_its_values(self):
        _note_missing_pyyaml(self)
        for label, (entries, errors) in self._skills("").items():
            with self.subTest(parser=label, kind="skill"):
                self.assertEqual(errors, [])
                self.assertEqual(entries[0]["requires_access"], "write-tree")
        for label, (entries, errors) in self._agents("").items():
            with self.subTest(parser=label, kind="agent"):
                self.assertEqual([e for e in errors if e.get("severity") != "warning"], [])
                solo = next(e for e in entries if e["id"] == "solo")
                self.assertEqual(solo["shell_scope"], "read-local")

    def test_a_second_metadata_block_on_a_skill_is_refused(self):
        _note_missing_pyyaml(self)
        for spelling, key in TOP_LEVEL_SPELLINGS:
            for label, (entries, errors) in self._skills(SECOND_SKILL_BLOCK.format(key=key)).items():
                with self.subTest(parser=label, spelling=spelling):
                    self.assertEqual(entries, [])
                    self.assertTrue(any(REPEAT_MESSAGE in e["error"] for e in errors), errors)

    def test_a_second_metadata_block_on_an_agent_is_refused(self):
        _note_missing_pyyaml(self)
        for spelling, key in TOP_LEVEL_SPELLINGS:
            for label, (entries, errors) in self._agents(SECOND_AGENT_BLOCK.format(key=key)).items():
                with self.subTest(parser=label, spelling=spelling):
                    self.assertNotIn("solo", [e["id"] for e in entries])
                    self.assertTrue(
                        any(e["file"] == "agents/solo.md" and REPEAT_MESSAGE in e["error"] for e in errors),
                        errors,
                    )


if __name__ == "__main__":
    unittest.main()
