"""Role x skill x harness pairing gate over the real tree, plus its controls.

Real-tree checks assert the denominator and the exact lane-carried set
(rule:pairing-gate-has-a-denominator-and-controls). Each control builds a
variant of the green fixture, asserts the exact named triple and its reason,
and pairs every red with a green baseline so the fixture is shown to trigger.
Reads only crux/, so it runs in the staged artifact.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _role_skill_pairing as gate  # noqa: E402

GREEN = Path(__file__).resolve().parent / "fixtures" / "role_skill_pairing" / "green"
ALL = ("claude-code", "codex", "opencode")
CS, RC = "caller-supplies", "returns-to-caller"
# Pairs sum the declared skills; triples count each pair across three harnesses.
EXPECTED_PAIRS, EXPECTED_TRIPLES = 56, 168
SCRIPT = Path(gate.__file__).resolve()
# Residual facts over the passing real-tree triples; each name is a fact about a host the static gate cannot see.
EXPECTED_RESIDUALS = {"opencode-external-read": 53, "codex-skill-binding": 52, "codex-egress": 47,
                      "codex-uv-cache": 47, "codex-git-writable": 43, "codex-shell-permit": 2}
GREEN_CARRIED = {(r, s, h, k) for r, s, k in (("reader", "supplied-skill", CS), ("reader", "report-skill", RC),
                                              ("conductor", "tree-skill", "delegates:writer")) for h in ALL}


def _expected_lane_carried() -> set:
    def each(role, skill, kind, harnesses=ALL):
        return {(role, skill, h, kind) for h in harnesses}

    out = each("brainstormer", "query-docs", CS) | each("brainstormer", "whiteboarding", CS)
    out |= each("librarian", "query-docs", CS, ("codex",))
    for role in ("brainstormer", "librarian", "reviewer"):
        out |= each(role, "forge-skill", RC)
    out |= each("reviewer", "council", RC, ("codex",))
    out |= each("commander", "cycle", "delegates:historian")
    out |= each("commander", "run-promptbook", "delegates:historian")
    out |= each("commander", "log-work", "delegates:historian")
    # The access ladder alone covers council in Claude Code and Codex; OpenCode
    # needs the lane. Commander prose still requires architect to run councils.
    out |= each("commander", "council", "delegates:architect", ("opencode",))
    return out


def assert_lane_set(test: unittest.TestCase, report, expected: set) -> None:
    got = report.lane_carried
    test.assertEqual(got, expected, msg=f"lane-carried drift: unexpected={sorted(got - expected)} "
                                        f"missing={sorted(expected - got)}")


class RealTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = gate.evaluate(gate.PLUGIN_DIR)

    def test_every_triple_passes(self):
        lines = [t.line() for t in self.report.failures] + self.report.errors
        self.assertEqual(lines, [], msg="failing triples:\n" + "\n".join(lines))

    def test_denominator(self):
        self.assertEqual((len(self.report.pairs), len(self.report.triples)), (EXPECTED_PAIRS, EXPECTED_TRIPLES))

    def test_lane_carried_set_is_exact(self):
        expected = _expected_lane_carried()
        self.assertEqual(len(expected), 27)
        assert_lane_set(self, self.report, expected)

    def test_every_lane_carries_a_triple(self):
        self.assertEqual(self.report.unused_lanes, [])

    def test_residual_counter_is_pinned(self):
        got = {}
        for t in self.report.triples:
            if t.ok:
                for r in t.residuals:
                    got[r] = got.get(r, 0) + 1
        self.assertEqual(got, EXPECTED_RESIDUALS)

    def test_every_line_has_its_route_and_residuals(self):
        for t in self.report.triples:
            line = t.line()
            self.assertIn(f"route={t.route}", line)
            if t.ok and t.harness != "claude-code" and t.route != f"lane:{RC}":
                self.assertIn("pass (residual: ", line, msg=line)


def agent_text(name, tools, skills, disallowed=None, scope=None, lanes=None) -> str:
    meta = (f'  shell_scope: "{scope}"\n' if scope else "") + (f'  skill_lanes: "{lanes}"\n' if lanes else "")
    deny = f"disallowedTools: {disallowed}\n" if disallowed else ""
    return (f"---\nname: {name}\ndescription: Fixture role {name}.\ntools: {tools}\nmodel: sonnet\n{deny}"
            f"skills: [{skills}]\nmetadata:\n  tags: \"fixture\"\n  bundles: \"fixture\"\n"
            f"  risk_level: \"low\"\n{meta}---\n\n# {name}\n\nFixture body.\n")


class VariantCase(unittest.TestCase):
    """Builds variants of the green fixture; holds no tests of its own."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.n = 0

    def variant(self, *args, **kwargs):
        return gate.evaluate(self.variant_root(*args, **kwargs))

    def variant_root(self, agents=(), skills=(), new_agents=None, new_skills=None):
        """Copy the green fixture, apply (name, old, new) edits, add roles and skills; return the plugin dir."""
        self.n += 1
        root = Path(self._tmp.name) / f"v{self.n}"
        shutil.copytree(GREEN, root)
        for kind, edits in (("agents", agents), ("skills", skills)):
            for name, old, new in edits:
                path = root / kind / (f"{name}.md" if kind == "agents" else f"{name}/SKILL.md")
                text = path.read_text()
                self.assertIn(old, text, msg=f"edit target missing in {name}")
                path.write_text(text.replace(old, new))
        for name, kwargs in (new_agents or {}).items():
            (root / "agents" / f"{name}.md").write_text(agent_text(name, **kwargs))
        for name, need in (new_skills or {}).items():
            (root / "skills" / name).mkdir()
            (root / "skills" / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Fixture skill {name}.\nmetadata:\n  tags: \"fixture\"\n"
                f"  bundles: \"fixture\"\n  risk_level: \"low\"\n  requires_access: \"{need}\"\n---\n\n# {name}\n")
        return root

    def triple(self, report, role, skill, harness):
        found = [t for t in report.triples if (t.role, t.skill, t.harness) == (role, skill, harness)]
        self.assertEqual(len(found), 1, msg=f"{role} x {skill} x {harness}")
        return found[0]

    def red(self, report, role, skill, harness, *reasons):
        t = self.triple(report, role, skill, harness)
        self.assertFalse(t.ok, msg=t.line())
        for reason in reasons:
            self.assertIn(reason, "; ".join(t.why), msg=t.line())

    def green(self, report, role, skill, harness):
        t = self.triple(report, role, skill, harness)
        self.assertTrue(t.ok, msg=t.line())


class ControlTests(VariantCase):
    def test_green_fixture_passes(self):
        report = self.variant()
        self.assertTrue(report.ok, msg=gate.format_report(report))
        self.assertEqual((len(report.pairs), len(report.triples), len(report.lane_carried)), (7, 21, 9))
        self.assertEqual(report.lane_carried, GREEN_CARRIED)

    def test_a_write_tree_skill_on_a_read_only_role(self):
        report = self.variant(agents=[("reader", "supplied-skill, report-skill]", "supplied-skill, report-skill, tree-skill]")])
        self.red(report, "reader", "tree-skill", "claude-code", "Bash", "Edit", "Write")
        self.red(report, "reader", "tree-skill", "codex", "workspace-write")
        self.red(report, "reader", "tree-skill", "opencode", "shell", "edit")
        report = self.variant()  # declaration removed: green again
        self.assertEqual([t for t in report.triples if (t.role, t.skill) == ("reader", "tree-skill")], [])
        self.assertTrue(report.ok)

    def test_b_bash_in_tools_and_disallowed_tools(self):
        base = dict(tools="Read, Grep, Glob, Bash, Skill", skills="run-skill", scope="run-plugin-script")
        denied = self.variant(new_agents={"shellrole": dict(base, disallowed="Bash")})
        self.red(denied, "shellrole", "run-skill", "claude-code", "Bash")
        self.red(denied, "shellrole", "run-skill", "opencode", "shell")
        free = self.variant(new_agents={"shellrole": base})
        self.green(free, "shellrole", "run-skill", "claude-code")
        self.green(free, "shellrole", "run-skill", "opencode")

    def test_c_skill_denied(self):
        denied = self.variant(agents=[("reader", "model: sonnet", "model: sonnet\ndisallowedTools: Skill")])
        self.red(denied, "reader", "read-skill", "claude-code", "skill grant")
        self.red(denied, "reader", "read-skill", "opencode", "skill grant")
        self.green(denied, "reader", "read-skill", "codex")  # Codex binds every declared skill
        self.green(self.variant(), "reader", "read-skill", "claude-code")

    def test_d_edit_write_bash_without_read(self):
        role = dict(tools="Grep, Glob, Edit, Write, Bash, Skill", skills="read-skill")
        report = self.variant(new_agents={"noread": role})
        self.red(report, "noread", "read-skill", "claude-code", "Read")
        self.red(report, "noread", "read-skill", "opencode", "read")
        self.green(report, "noread", "read-skill", "codex")  # a shell is Codex's read path

    def test_e_and_f_edit_or_write_in_disallowed_tools(self):
        for withheld in ("Edit", "Write"):
            role = dict(tools="Read, Grep, Glob, Edit, Write, Bash, Skill", skills="read-skill", disallowed=withheld)
            report = self.variant(new_agents={"split": role})
            for h in ALL:
                self.red(report, "split", "read-skill", h, f"disallowedTools withholds {withheld}")

    def test_g_edit_without_bash(self):
        role = dict(tools="Read, Grep, Glob, Edit, Write, Skill", skills="read-skill")
        report = self.variant(new_agents={"nobash": role})
        for h in ALL:
            self.red(report, "nobash", "read-skill", h, "Edit without Bash")

    def test_h_shell_scope_below_the_need(self):
        def role(scope):
            return {"scoped": dict(tools="Read, Grep, Glob, Bash, Skill", skills="record-skill", scope=scope)}

        low = self.variant(new_agents=role("read-local"), new_skills={"record-skill": "write-run"})
        for h in ALL:
            self.red(low, "scoped", "record-skill", h, "shell_scope=read-local below write-run")
        ok = self.variant(new_agents=role("write-run"), new_skills={"record-skill": "write-run"})
        self.green(ok, "scoped", "record-skill", "claude-code")
        self.green(ok, "scoped", "record-skill", "opencode")

    def test_i_delegate_target_cannot_cover_or_is_not_dispatchable(self):
        weak = self.variant(agents=[("writer", "Edit, Write, ", "")])
        self.red(weak, "conductor", "tree-skill", "claude-code", "target writer envelope lacks")
        self.red(weak, "conductor", "tree-skill", "opencode", "target writer envelope lacks")
        self.red(weak, "conductor", "tree-skill", "codex", "target writer envelope lacks")
        # `Agent(reader)` only: OpenCode renders `deny *` then `allow reader`; writer matches only the deny.
        other = self.variant(agents=[("conductor", "Agent(writer)", "Agent(reader)")])
        self.red(other, "conductor", "tree-skill", "claude-code", "no dispatch grant for writer")
        self.red(other, "conductor", "tree-skill", "opencode", "no dispatch grant for writer")
        collapsed = self.variant(agents=[("conductor", "model: sonnet", "model: sonnet\ndisallowedTools: Agent")])
        self.red(collapsed, "conductor", "tree-skill", "claude-code", "no dispatch grant for writer")
        self.red(collapsed, "conductor", "tree-skill", "opencode", "no dispatch grant for writer")
        self.green(self.variant(), "conductor", "tree-skill", "opencode")  # allow after deny: last match wins

    def test_j_skill_without_a_valid_token(self):
        gone = self.variant(skills=[("run-skill", '  requires_access: "run-plugin-script"\n', "")])
        bogus = self.variant(skills=[("run-skill", '"run-plugin-script"', '"bogus"')])
        for report in (gone, bogus):
            for h in ALL:
                self.red(report, "writer", "run-skill", h, "skill run-skill has no valid requires_access")
            self.assertFalse(report.ok)

    def test_n_unknown_shell_scope_names_its_triples(self):
        def role(scope):
            return {"scoped": dict(tools="Read, Grep, Glob, Bash, Skill", skills="read-skill", scope=scope)}

        bogus = self.variant(new_agents=role("bogus"))
        for h in ALL:
            self.red(bogus, "scoped", "read-skill", h, "unknown shell_scope 'bogus'")
        self.assertFalse(bogus.ok)
        self.green(self.variant(new_agents=role("read-local")), "scoped", "read-skill", "claude-code")

    def test_m_caller_supplies_needs_a_covered_supplied_access(self):
        undeclared = self.variant(skills=[("supplied-skill", '\n  supplied_access: "read-local"', "")])
        uncovered = self.variant(skills=[("supplied-skill", '"read-local"', '"run-plugin-script"')])
        for h in ALL:
            self.red(undeclared, "reader", "supplied-skill", h, "skill declares no supplied_access")
            self.red(uncovered, "reader", "supplied-skill", h, "supplied run-plugin-script not covered")
        self.green(self.variant(), "reader", "supplied-skill", "codex")

    def test_k_lane_that_carries_no_triple(self):
        lane = 'risk_level: "low"\n  skill_lanes: "read-skill=returns-to-caller"'
        report = self.variant(agents=[("writer", 'risk_level: "low"', lane)])
        self.assertEqual(report.failures, [])
        self.assertEqual(report.unused_lanes, [("writer", "read-skill")])
        self.assertFalse(report.ok)

    def test_l_envelope_regression_moves_a_triple_onto_a_lane(self):
        def variant_with(scope):
            role = dict(tools="Grep, Glob, Skill", skills="read-skill", scope=scope, lanes=f"read-skill={RC}")
            return self.variant(new_agents={"scoped": role})

        # Read is withheld, so Claude Code and OpenCode ride the lane; the Codex shell permit covers it.
        expected = GREEN_CARRIED | {("scoped", "read-skill", h, RC) for h in ("claude-code", "opencode")}
        assert_lane_set(self, variant_with("read-local"), expected)
        with self.assertRaises(AssertionError) as caught:  # permit lost: the Codex triple moves onto the lane
            assert_lane_set(self, variant_with(None), expected)
        self.assertIn("('scoped', 'read-skill', 'codex', 'returns-to-caller')", str(caught.exception))

    def test_i_target_must_declare_the_skill_and_hold_no_lane_for_it(self):
        undeclared = self.variant(agents=[("writer", "[tree-skill, run-skill, read-skill]", "[run-skill, read-skill]")])
        laned = self.variant(agents=[("writer", 'risk_level: "low"', 'risk_level: "low"\n  skill_lanes: "tree-skill=returns-to-caller"')])
        for h in ALL:
            self.red(undeclared, "conductor", "tree-skill", h, "target does not declare the skill")
            self.red(laned, "conductor", "tree-skill", h, "target holds a lane for the skill")
            self.green(self.variant(), "conductor", "tree-skill", h)

    def test_a_broken_role_rides_no_lane(self):
        role = dict(tools="Read, Grep, Glob, Edit, Write, Skill", skills="read-skill", lanes=f"read-skill={RC}")
        report = self.variant(new_agents={"nobash": role})
        for h in ALL:
            self.red(report, "nobash", "read-skill", h, "Edit without Bash")
            self.assertEqual(self.triple(report, "nobash", "read-skill", h).route, "envelope")

    def test_caller_supplies_cannot_carry_a_write(self):
        report = self.variant(agents=[("reader", "report-skill=returns-to-caller", "report-skill=caller-supplies")],
                              skills=[("report-skill", '"write-tree"', '"write-tree"\n  supplied_access: "read-local"')])
        for h in ALL:
            self.red(report, "reader", "report-skill", h, "caller-supplies cannot carry a need above run-plugin-script")
            self.green(self.variant(), "reader", "report-skill", h)

    def test_write_host_is_never_met_in_codex(self):
        report = self.variant(agents=[("writer", "[tree-skill,", "[host-skill, tree-skill,")],
                              new_skills={"host-skill": "write-host"})
        self.red(report, "writer", "host-skill", "codex", "never")
        for h, residual in (("claude-code", "claude-host-write"), ("opencode", "opencode-host-write")):
            t = self.triple(report, "writer", "host-skill", h)
            self.assertTrue(t.ok, msg=t.line())
            self.assertIn(residual, t.residuals)

    def test_residuals_follow_the_envelope_that_runs_the_skill(self):
        # The conductor holds a shell_scope without Bash, so its own Codex residuals would add codex-shell-permit;
        # the delegate (writer) holds Bash, so the delegated triple must not.
        report = self.variant(agents=[("conductor", 'risk_level: "low"', 'risk_level: "low"\n  shell_scope: "read-local"')])
        codex = ("codex-egress", "codex-git-writable", "codex-skill-binding", "codex-uv-cache")
        self.assertEqual(self.triple(report, "conductor", "tree-skill", "codex").residuals, codex)
        self.assertEqual(self.triple(report, "conductor", "tree-skill", "claude-code").residuals, ())
        self.assertEqual(self.triple(report, "conductor", "tree-skill", "opencode").residuals, ("opencode-external-read",))
        for h in ALL:  # returns-to-caller runs nothing here, so it carries no residual
            t = self.triple(report, "reader", "report-skill", h)
            self.assertEqual((t.ok, t.route, t.residuals), (True, f"lane:{RC}", ()), msg=t.line())

    def test_malformed_skill_lanes_is_an_error_that_fails_the_report(self):
        report = self.variant(agents=[("reader", "report-skill=returns-to-caller", "report-skill=returns-to-caller, bogus")])
        self.assertEqual(report.failures, [])
        self.assertEqual(len(report.errors), 1)
        self.assertIn("reader", report.errors[0])
        self.assertIn("bogus", report.errors[0])
        self.assertFalse(report.ok)

    def test_summary_line_reports_resolved_counts(self):
        text = gate.format_report(self.variant())
        self.assertIn("pairs=7 triples=21 passing=21 failing=0", text.splitlines())

    def test_ladder_must_match_the_coverage_table(self):
        vc = gate._modules()[0]
        with mock.patch.object(vc, "ACCESS_LADDER", tuple(reversed(vc.ACCESS_LADDER))):
            with self.assertRaises(RuntimeError) as caught:
                self.variant()
        self.assertIn("ladder", str(caught.exception))
        self.assertTrue(self.variant().ok)


class CommandLineTests(VariantCase):
    """Exit codes and the summary line, through the real entry point in a subprocess."""

    def run_cli(self, plugin_dir):
        return subprocess.run([sys.executable, str(SCRIPT), "--plugin-dir", str(plugin_dir)],
                              capture_output=True, text=True, timeout=120)

    def test_green_exits_0_with_the_summary_line(self):
        done = self.run_cli(self.variant_root())
        self.assertEqual(done.returncode, 0, msg=done.stdout + done.stderr)
        self.assertIn("pairs=7 triples=21 passing=21 failing=0", done.stdout.splitlines())

    def test_failing_triple_exits_1(self):
        root = self.variant_root(agents=[("reader", "supplied-skill, report-skill]", "supplied-skill, report-skill, tree-skill]")])
        done = self.run_cli(root)
        self.assertEqual(done.returncode, 1, msg=done.stdout + done.stderr)
        named = [line for line in done.stdout.splitlines() if line.startswith("reader x tree-skill x codex ")]
        self.assertEqual(len(named), 1, msg=done.stdout)
        self.assertTrue(named[0].startswith("reader x tree-skill x codex need=write-tree route=envelope FAIL ("), msg=named[0])
        self.assertTrue(named[0].endswith(")"), msg=named[0])

    def test_lane_error_exits_1(self):
        root = self.variant_root(agents=[("reader", "report-skill=returns-to-caller", "report-skill=returns-to-caller, bogus")])
        done = self.run_cli(root)
        self.assertEqual(done.returncode, 1, msg=done.stdout + done.stderr)
        self.assertIn("ERROR reader:", done.stdout)

    def test_unused_lane_exits_1(self):
        lane = 'risk_level: "low"\n  skill_lanes: "read-skill=returns-to-caller"'
        done = self.run_cli(self.variant_root(agents=[("writer", 'risk_level: "low"', lane)]))
        self.assertEqual(done.returncode, 1, msg=done.stdout + done.stderr)
        self.assertIn("FAIL lane writer x read-skill", done.stdout)

    def test_environment_errors_exit_2_with_one_stderr_line(self):
        empty = Path(self._tmp.name) / "empty"
        empty.mkdir()
        no_skills = self.variant_root()
        shutil.rmtree(no_skills / "skills")
        for root, message in ((empty, "no role found under"), (Path(self._tmp.name) / "missing", "no role found under"),
                              (no_skills, "no skill found under")):
            done = self.run_cli(root)
            self.assertEqual(done.returncode, 2, msg=done.stdout + done.stderr)
            self.assertEqual(len(done.stderr.strip().splitlines()), 1, msg=done.stderr)
            self.assertIn(message, done.stderr)
            self.assertNotIn("pairs=", done.stdout)

    def test_no_role_declaring_a_skill_exits_2(self):
        # A zero denominator is not a pass: every role present, none declaring a skill.
        root = self.variant_root()
        for path in sorted((root / "agents").glob("*.md")):
            text = path.read_text()
            stripped = re.sub(r"(?m)^skills:.*$", "skills: []", text)
            stripped = re.sub(r"(?m)^[ \t]+skill_lanes:.*\n", "", stripped)
            path.write_text(stripped)
        done = self.run_cli(root)
        self.assertEqual(done.returncode, 2, msg=done.stdout + done.stderr)
        self.assertEqual(done.stderr.strip().splitlines(), [f"error: no role declares a skill under {root / 'agents'}"])
        self.assertNotIn("pairs=", done.stdout)

    def test_uncaught_exception_exits_2(self):
        root = self.variant_root()
        (root / "agents" / "reader.md").write_text("no frontmatter at all\n")
        done = self.run_cli(root)
        self.assertEqual(done.returncode, 2, msg=done.stdout + done.stderr)
        self.assertEqual(done.stderr.strip().splitlines(),
                         [f"error: {root / 'agents' / 'reader.md'} has no frontmatter"], msg=done.stderr)
        self.assertNotIn("Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main()
