"""Regression tests for Crux's OMP (Oh My Pi) generated role agents.

Covers the shared projection in `omp_agents.py`, the standalone
`generate-omp-agents.py` CLI, and the `install-omp-agents` installer. Mirrors
the Codex/OpenCode lanes: rendering, tool translation, symlink refusal, and
install scope/no-clobber contracts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import models_catalog  # noqa: E402
import omp_agent_health as health  # noqa: E402
import omp_agents as agents  # noqa: E402

CATALOG = models_catalog.load()
SOURCE_DIR = REPO_ROOT / "crux" / "agents"
INSTALLER = REPO_ROOT / "crux" / "skills" / "install-omp-agents" / "scripts" / "install.py"
GENERATOR = SCRIPTS_DIR / "generate-omp-agents.py"

EXPECTED_SOURCE_NAMES = {
    "architect", "brainstormer", "commander", "dev-lead", "developer",
    "historian", "librarian", "night-gardener", "reviewer", "wayfinder",
}
EXPECTED_FILES = {f"{name}.md" for name in EXPECTED_SOURCE_NAMES}

# Independently stated OpenRouter resolutions. A catalog edit that changes one
# fails here rather than passing through the projection untested.
EXPECTED_MODEL_IDS = {
    "architect": "openrouter/anthropic/claude-opus-5.5",
    "brainstormer": "openrouter/openai/gpt-6.1-sol",
    "commander": "openrouter/moonshotai/kimi-k3.1-pro",
    "dev-lead": "openrouter/openai/gpt-6.1-sol",
    "developer": "openrouter/deepseek/deepseek-v4.1-flash-1017",
    "historian": "openrouter/z-ai/glm-5.3",
    "librarian": "openrouter/z-ai/glm-5.3",
    "night-gardener": "openrouter/anthropic/claude-opus-5.5",
    "reviewer": "openrouter/openai/gpt-6.1-sol",
    "wayfinder": "openrouter/z-ai/glm-5.3",
}

EXPECTED_THINKING_LEVEL = {
    "architect": "high",
    "developer": "medium",
    "historian": "medium",
    "librarian": "medium",
    "reviewer": "high",
    "wayfinder": "medium",
}

# Ordered OMP tool emission for each role, plus the `spawns` value (None when
# the role may not spawn subagents at all).
EXPECTED_TOOLS = {
    "architect": ["read", "grep", "glob", "find", "edit", "write", "bash", "web_search"],
    "brainstormer": ["read", "grep", "glob", "find", "web_search"],
    "commander": ["read", "grep", "glob", "find", "bash", "task", "todo"],
    "dev-lead": ["read", "grep", "glob", "find", "edit", "write", "bash", "task", "todo"],
    "developer": ["read", "grep", "glob", "find", "edit", "write", "bash", "todo"],
    "historian": ["read", "grep", "glob", "find", "edit", "write", "bash", "todo"],
    "librarian": ["read", "grep", "glob", "find", "bash"],
    "night-gardener": ["read", "grep", "glob", "find", "edit", "write", "bash", "task", "todo", "web_search"],
    "reviewer": ["read", "grep", "glob", "find", "bash"],
    "wayfinder": ["read", "grep", "glob", "find", "web_search"],
}
EXPECTED_SPAWNS = {
    "commander": [
        "architect", "brainstormer", "dev-lead", "historian", "librarian",
        "night-gardener", "reviewer", "scout", "wayfinder",
    ],
    "dev-lead": ["developer", "historian", "reviewer", "scout", "wayfinder"],
    "night-gardener": ["historian", "librarian", "scout", "wayfinder"],
}


def _bracket_list(raw: str) -> list[str]:
    assert raw.startswith("[") and raw.endswith("]"), raw
    inner = raw[1:-1].strip()
    if not inner:
        return []
    return [token.strip().strip('"').strip("'") for token in inner.split(",")]


class RenderTests(unittest.TestCase):
    def _parse(self, text: str) -> tuple[dict[str, str], str]:
        match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)\Z", text, re.DOTALL)
        self.assertIsNotNone(match, "rendered agent lacks a Markdown frontmatter block")
        frontmatter = match.group("frontmatter")
        fields: dict[str, str] = {}
        for line in frontmatter.splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            self.assertNotIn(line[:1], (" ", "\t"), f"unexpected indented frontmatter line: {line!r}")
            key, separator, raw = line.partition(":")
            self.assertEqual(separator, ":", f"malformed frontmatter line: {line!r}")
            self.assertNotIn(key, fields, f"duplicate frontmatter key: {key}")
            fields[key] = raw.strip()
        return fields, match.group("body")

    def test_catalog_roster_matches_source_agents(self):
        self.assertEqual(set(CATALOG.agents), EXPECTED_SOURCE_NAMES)
        self.assertEqual({path.stem for path in SOURCE_DIR.glob("*.md")}, EXPECTED_SOURCE_NAMES)

    def test_all_ten_roles_render_valid_omp_markdown(self):
        generated = agents.generate()
        self.assertEqual(set(generated), EXPECTED_FILES)
        for role in sorted(EXPECTED_SOURCE_NAMES):
            with self.subTest(role=role):
                fields, body = self._parse(generated[f"{role}.md"])
                self.assertEqual(fields["name"], role)
                self.assertTrue(fields["description"])
                self.assertIn("model", fields)
                self.assertIn("<!-- BEGIN GENERATED: omp-compat -->", body)
                self.assertIn("<!-- END GENERATED: omp-compat -->", body)
                source = agents.parse_source(SOURCE_DIR / f"{role}.md")
                self.assertIn(source.body, body)
                self.assertTrue(
                    body.rstrip("\n").endswith(source.body),
                    "the source role body must be preserved verbatim after the compatibility header",
                )
                self.assertNotIn("autoloadSkills", fields)

    def test_model_is_role_alias_plus_resolved_openrouter_model(self):
        generated = agents.generate()
        for role in sorted(EXPECTED_SOURCE_NAMES):
            with self.subTest(role=role):
                fields, _ = self._parse(generated[f"{role}.md"])
                resolved = CATALOG.resolve(role).opencode
                alias = f"@crux_{role.replace('-', '_')}"
                self.assertEqual(_bracket_list(fields["model"]), [alias, resolved])
                self.assertEqual(resolved, EXPECTED_MODEL_IDS[role])

    def test_thinking_level_tracks_source_effort(self):
        generated = agents.generate()
        for role in sorted(EXPECTED_SOURCE_NAMES):
            with self.subTest(role=role):
                fields, _ = self._parse(generated[f"{role}.md"])
                if role in EXPECTED_THINKING_LEVEL:
                    self.assertEqual(fields.get("thinking-level"), EXPECTED_THINKING_LEVEL[role])
                else:
                    self.assertNotIn("thinking-level", fields)
                source = agents.parse_source(SOURCE_DIR / f"{role}.md")
                self.assertEqual(source.effort, EXPECTED_THINKING_LEVEL.get(role))

    def test_read_summarize_is_disabled_only_for_reconnaissance_and_retrieval(self):
        generated = agents.generate()
        disabled = {"librarian", "wayfinder"}
        for role in sorted(EXPECTED_SOURCE_NAMES):
            with self.subTest(role=role):
                fields, _ = self._parse(generated[f"{role}.md"])
                if role in disabled:
                    self.assertEqual(fields.get("read-summarize"), "false")
                else:
                    self.assertNotIn("read-summarize", fields)

    def test_rendered_tools_and_spawns_match_the_role_contract(self):
        generated = agents.generate()
        for role in sorted(EXPECTED_SOURCE_NAMES):
            with self.subTest(role=role):
                fields, _ = self._parse(generated[f"{role}.md"])
                self.assertEqual(_bracket_list(fields["tools"]), EXPECTED_TOOLS[role])
                if role in EXPECTED_SPAWNS:
                    self.assertEqual(_bracket_list(fields["spawns"]), EXPECTED_SPAWNS[role])
                    self.assertIn("task", EXPECTED_TOOLS[role])
                else:
                    self.assertNotIn("spawns", fields)
                    self.assertNotIn("task", EXPECTED_TOOLS[role])



class DevCheckoutShadowTests(unittest.TestCase):
    # Personal OMP agents (~/.omp/agent/agents/) are the default configuration.
    # A project-local copy in this checkout shadows them.
    @unittest.skipUnless(
        (REPO_ROOT / "tools" / "sync_stage.py").is_file(),
        "project-shadow guard applies only to the private development checkout",
    )
    def test_dev_checkout_has_no_project_omp_agents(self):
        output_dir = REPO_ROOT / ".omp" / "agents"
        shadows = sorted(path.name for path in output_dir.glob("*.md"))
        self.assertEqual(shadows, [], "project-local Crux OMP agents shadow personal agents")

class ToolResolutionTests(unittest.TestCase):
    def _source(self, tools: tuple[str, ...], disallowed: tuple[str, ...] = ()) -> agents.SourceAgent:
        return agents.SourceAgent(
            name="architect",
            description="Synthetic.",
            tools=tools,
            disallowed_tools=disallowed,
            effort=None,
            skills=(),
            body="Body.",
        )

    def test_each_mapped_tool_translates_to_its_omp_name(self):
        mapping = {
            "Read": ["read"],
            "Grep": ["grep", "find"],
            "Glob": ["glob"],
            "Edit": ["edit"],
            "Write": ["write"],
            "Bash": ["bash"],
            "TodoWrite": ["todo"],
            "WebSearch": ["web_search"],
        }
        for claude_tool, expected in mapping.items():
            with self.subTest(tool=claude_tool):
                tools, spawns = agents.resolve_tools_and_spawns(self._source((claude_tool,)))
                self.assertEqual(tools, expected)
                self.assertIsNone(spawns)

    def test_host_only_tools_add_no_redundant_entries(self):
        tools, spawns = agents.resolve_tools_and_spawns(
            self._source(("Read", "Skill", "WebFetch", "SendMessage", "Monitor"))
        )
        self.assertEqual(tools, ["read"])
        self.assertIsNone(spawns)

        only_host_tools, _ = agents.resolve_tools_and_spawns(
            self._source(("Skill", "WebFetch", "SendMessage", "Monitor"))
        )
        self.assertEqual(only_host_tools, [])

    def test_agent_grants_become_spawns_and_task(self):
        tools, spawns = agents.resolve_tools_and_spawns(
            self._source(("Agent(developer)",))
        )
        self.assertEqual(tools, ["task"])
        self.assertEqual(spawns, ["developer"])

    def test_wayfinder_grant_also_offers_native_scout(self):
        tools, spawns = agents.resolve_tools_and_spawns(self._source(("Agent(wayfinder)",)))
        self.assertEqual(tools, ["task"])
        self.assertEqual(spawns, ["scout", "wayfinder"])

    def test_spawning_roles_map_wayfinder_and_scout_together(self):
        for role in ("commander", "dev-lead", "night-gardener"):
            with self.subTest(role=role):
                tools, spawns = agents.resolve_tools_and_spawns(
                    agents.parse_source(SOURCE_DIR / f"{role}.md")
                )
                self.assertIn("task", tools)
                self.assertIsInstance(spawns, list)
                self.assertIn("scout", spawns)
                self.assertIn("wayfinder", spawns)

    def test_roles_without_agent_grants_have_no_task_and_no_spawns(self):
        for role in (
            "architect", "brainstormer", "developer", "historian",
            "librarian", "reviewer", "wayfinder",
        ):
            with self.subTest(role=role):
                tools, spawns = agents.resolve_tools_and_spawns(
                    agents.parse_source(SOURCE_DIR / f"{role}.md")
                )
                self.assertNotIn("task", tools)
                self.assertIsNone(spawns)

    def test_disallowed_tools_revoke_mapped_grants(self):
        tools, spawns = agents.resolve_tools_and_spawns(
            self._source(("Read", "Bash", "Edit", "Write"), ("Bash", "Edit"))
        )
        self.assertEqual(tools, ["read", "write"])
        self.assertIsNone(spawns)

    def test_disallowed_webfetch_and_skill_revoke_read(self):
        for denied in ("WebFetch", "Skill"):
            with self.subTest(denied=denied):
                tools, _ = agents.resolve_tools_and_spawns(
                    self._source(("Read", "Grep"), (denied,))
                )
                self.assertEqual(tools, ["grep", "find"])

    def test_disallowed_agent_revokes_task_and_spawns(self):
        for denied in ("Agent", "Agent(developer)"):
            with self.subTest(denied=denied):
                tools, spawns = agents.resolve_tools_and_spawns(
                    self._source(("Read", "Agent(developer)"), (denied,))
                )
                self.assertEqual(tools, ["read"])
                self.assertIsNone(spawns)

    def test_unmapped_allowed_tool_is_a_spec_violation(self):
        with self.assertRaises(agents.SpecViolation):
            agents.resolve_tools_and_spawns(self._source(("Read", "NotATool")))

    def test_unmapped_disallowed_tool_is_a_spec_violation(self):
        with self.assertRaises(agents.SpecViolation):
            agents.resolve_tools_and_spawns(self._source(("Read",), ("NotATool",)))


class WriteSymlinkRefusalTests(unittest.TestCase):
    """The shared write()/diff() never follow or clobber managed leaves.

    Managed leaves for this lane are the ten `<role>.md` names. Every refusal
    is fail-closed: a SpecViolation, the victim untouched, and no partial
    write.
    """

    def _victim(self, path: Path, content: str = "SENTINEL — must not be clobbered\n") -> Path:
        path.write_text(content, encoding="utf-8")
        return path

    def test_write_refuses_leaf_symlink_with_escaping_target(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as outside:
            output_dir = Path(repo) / ".omp" / "agents"
            output_dir.mkdir(parents=True)
            victim = self._victim(Path(outside) / "victim.md")
            (output_dir / "architect.md").symlink_to(victim)

            with self.assertRaises(agents.SpecViolation):
                agents.write(output_dir, agents.generate())
            self.assertEqual(victim.read_text(encoding="utf-8"), "SENTINEL — must not be clobbered\n")
            self.assertFalse((output_dir / "developer.md").exists())

    def test_write_refuses_leaf_symlink_with_contained_target(self):
        with tempfile.TemporaryDirectory() as repo:
            output_dir = Path(repo) / ".omp" / "agents"
            output_dir.mkdir(parents=True)
            victim = self._victim(Path(repo) / "in_repo_victim.md")
            (output_dir / "developer.md").symlink_to(victim)

            with self.assertRaises(agents.SpecViolation):
                agents.write(output_dir, agents.generate())
            self.assertEqual(victim.read_text(encoding="utf-8"), "SENTINEL — must not be clobbered\n")

    def test_write_refuses_stale_leaf_symlink_before_unlink(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as outside:
            output_dir = Path(repo) / ".omp" / "agents"
            output_dir.mkdir(parents=True)
            victim = self._victim(Path(outside) / "stale_victim.md")
            stale = output_dir / "architect.md"
            stale.symlink_to(victim)

            with self.assertRaises(agents.SpecViolation):
                agents.write(output_dir, {}, remove_stale=True)
            self.assertTrue(stale.is_symlink())
            self.assertTrue(victim.exists())

    def test_diff_refuses_dangling_leaf_symlink_with_clean_error(self):
        with tempfile.TemporaryDirectory() as repo:
            output_dir = Path(repo) / ".omp" / "agents"
            output_dir.mkdir(parents=True)
            (output_dir / "architect.md").symlink_to(Path(repo) / "nonexistent.md")
            with self.assertRaises(agents.SpecViolation):
                agents.diff(output_dir, agents.generate())

    def test_write_remove_stale_false_keeps_stale_managed_file(self):
        with tempfile.TemporaryDirectory() as repo:
            output_dir = Path(repo) / ".omp" / "agents"
            generated = agents.generate()
            agents.write(output_dir, generated)
            subset = {name: text for name, text in generated.items() if name != "developer.md"}

            written, removed = agents.write(output_dir, subset, remove_stale=False)
            self.assertEqual(written, [])
            self.assertEqual(removed, [])
            self.assertTrue((output_dir / "developer.md").exists())

            written, removed = agents.write(output_dir, subset)
            self.assertEqual(written, [])
            self.assertEqual(removed, ["developer.md"])
            self.assertFalse((output_dir / "developer.md").exists())

    def test_write_replaces_a_managed_hardlink_without_mutating_its_victim(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            generated = agents.generate()
            agents.write(output_dir, generated)
            leaf = output_dir / "architect.md"
            victim = Path(temporary) / "victim.md"
            victim.hardlink_to(leaf)
            original = victim.read_text(encoding="utf-8")
            replacement = dict(generated)
            replacement[leaf.name] = replacement[leaf.name] + "# refreshed\n"

            agents.write(output_dir, replacement)

            self.assertEqual(victim.read_text(encoding="utf-8"), original)
            self.assertEqual(leaf.read_text(encoding="utf-8"), replacement[leaf.name])

    def test_write_refuses_nonregular_leaf_before_any_partial_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            output_dir.mkdir()
            (output_dir / "developer.md").mkdir()
            with self.assertRaises(agents.SpecViolation):
                agents.write(output_dir, agents.generate())
            self.assertFalse((output_dir / "architect.md").exists())

    def test_write_preserves_unrelated_custom_agent(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            output_dir.mkdir()
            custom = output_dir / "my-custom-agent.md"
            custom.write_text("mine\n", encoding="utf-8")
            agents.write(output_dir, agents.generate())
            self.assertEqual(custom.read_text(encoding="utf-8"), "mine\n")

    def test_atomic_replace_does_not_follow_leaf_substituted_after_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            generated = agents.generate()
            agents.write(output_dir, generated)
            leaf = output_dir / "architect.md"
            victim = Path(temporary) / "victim.md"
            victim.write_text("SENTINEL\n", encoding="utf-8")
            replacement = dict(generated)
            replacement[leaf.name] = replacement[leaf.name] + "# refreshed\n"
            actual_replace = agents.os.replace

            def substitute_then_replace(src, dst, *args, **kwargs):
                leaf.unlink()
                leaf.symlink_to(victim)
                return actual_replace(src, dst, *args, **kwargs)

            with mock.patch.object(agents.os, "replace", side_effect=substitute_then_replace):
                agents.write(output_dir, replacement)

            self.assertEqual(victim.read_text(encoding="utf-8"), "SENTINEL\n")
            self.assertFalse(leaf.is_symlink())
            self.assertEqual(leaf.read_text(encoding="utf-8"), replacement[leaf.name])

    def test_pin_directory_refuses_output_outside_containment_root(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary) / "root"
            root.mkdir()
            output_dir = root / ".omp" / "agents"
            output_dir.parent.mkdir(parents=True)
            output_dir.symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaises(agents.SpecViolation):
                agents.pin_directory(output_dir, containment_root=root)

    def test_pinned_directory_survives_output_directory_substitution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            output_dir = root / ".omp" / "agents"
            output_dir.parent.mkdir(parents=True)
            target = root / "managed-agents"
            target.mkdir()
            output_dir.symlink_to(target, target_is_directory=True)
            outside = Path(temporary) / "outside"
            outside.mkdir()
            generated = agents.generate()

            with agents.pin_directory(output_dir, containment_root=root) as pinned:
                output_dir.unlink()
                output_dir.symlink_to(outside, target_is_directory=True)
                agents.write(pinned, generated)

            self.assertEqual({path.name for path in target.glob("*.md")}, EXPECTED_FILES)
            self.assertEqual({path.name for path in outside.glob("*.md")}, set())

    def test_pinned_directory_survives_parent_directory_substitution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            output_dir = root / ".omp" / "agents"
            output_dir.mkdir(parents=True)
            outside = Path(temporary) / "outside"
            outside.mkdir()
            generated = agents.generate()

            with agents.pin_directory(output_dir, containment_root=root) as pinned:
                original_parent = root / ".omp-original"
                (root / ".omp").rename(original_parent)
                (root / ".omp").symlink_to(outside, target_is_directory=True)
                agents.write(pinned, generated)

            self.assertEqual(
                {path.name for path in (original_parent / "agents").glob("*.md")},
                EXPECTED_FILES,
            )
            self.assertEqual({path.name for path in outside.glob("*.md")}, set())


class InstallerTests(unittest.TestCase):
    def _run_project(self, repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALLER), "--repo-root", str(repo_root), *args],
            check=False, capture_output=True, text=True,
        )

    def _run_personal(self, omp_home: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALLER), "--omp-home", str(omp_home), *args],
            check=False, capture_output=True, text=True,
        )

    def _run_isolated(self, installer: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a scratch-tree installer with the dev tree's `crux/scripts` off sys.path.

        A scratch tree that omits a module only models a broken install if the
        module is genuinely unimportable. The development venv's `.pth` puts
        `<repo>/crux/scripts` on every interpreter's path, so the omission is
        invisible without this driver. Under the staged artifact the same entry
        is the one `sync.sh` exports as PYTHONPATH; removing it measures the
        same thing in both worlds. The comparison is on resolved paths because
        macOS temp paths differ between `/var/...` and `/private/var/...`.
        """
        driver = (
            "import runpy, sys\n"
            "from pathlib import Path as _Path\n"
            f"_target = _Path({str(SCRIPTS_DIR)!r}).resolve()\n"
            "def _leaks(p):\n"
            "    if p == '':\n"
            "        return True\n"
            "    try:\n"
            "        return _Path(p).resolve() == _target\n"
            "    except OSError:\n"
            "        return False\n"
            "sys.path[:] = [p for p in sys.path if not _leaks(p)]\n"
            f"sys.argv = ['install.py', {', '.join(repr(arg) for arg in args)}]\n"
            f"runpy.run_path({str(installer)!r}, run_name='__main__')\n"
        )
        return subprocess.run(
            [sys.executable, "-c", driver], check=False, capture_output=True, text=True
        )

    def _scratch_installer_without_source_agents(self, scratch: Path) -> Path:
        plugin_root = scratch / "crux"
        (plugin_root / "agents").mkdir(parents=True)
        (plugin_root / "scripts").mkdir()
        scratch_scripts = plugin_root / "skills" / "install-omp-agents" / "scripts"
        scratch_scripts.mkdir(parents=True)
        for module in ("omp_agents.py", "omp_agent_health.py", "models_catalog.py", "_yaml_min.py"):
            shutil.copy2(SCRIPTS_DIR / module, plugin_root / "scripts")
        shutil.copy2(INSTALLER, scratch_scripts)
        return scratch_scripts / "install.py"

    def _scratch_installer_without_models_catalog(self, scratch: Path) -> Path:
        """A scratch plugin tree with a real source agent but NO models_catalog.py.

        The sibling fixture fails on an empty roster, which never reaches the
        catalog. This one enters the other lane: `omp_agents` imports cleanly
        and installs its `_DeferredCatalogFault` stand-in, so the fault
        surfaces at first use as the `SpecViolation` the stand-in serves.
        """
        plugin_root = scratch / "crux"
        (plugin_root / "agents").mkdir(parents=True)
        (plugin_root / "scripts").mkdir()
        scratch_scripts = plugin_root / "skills" / "install-omp-agents" / "scripts"
        scratch_scripts.mkdir(parents=True)
        shutil.copy2(SOURCE_DIR / "architect.md", plugin_root / "agents" / "architect.md")
        # `models_catalog.py` deliberately omitted.
        for module in ("omp_agents.py", "_yaml_min.py"):
            shutil.copy2(SCRIPTS_DIR / module, plugin_root / "scripts")
        shutil.copy2(INSTALLER, scratch_scripts)
        return scratch_scripts / "install.py"

    def test_personal_install_writes_into_the_omp_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            agent_home = Path(temporary) / "home" / "agent"
            result = self._run_personal(agent_home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            target = (agent_home / "agents").resolve()
            self.assertEqual(payload["scope"], "personal")
            self.assertEqual(payload["target"], str(target))
            self.assertEqual(set(payload["written"]), EXPECTED_FILES)
            self.assertEqual({path.name for path in target.glob("*.md")}, EXPECTED_FILES)

    def test_project_install_writes_under_the_repo_omp_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary)
            result = self._run_project(repo_root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            target = (repo_root / ".omp" / "agents").resolve()
            self.assertEqual(payload["scope"], "project")
            self.assertEqual(payload["target"], str(target))
            self.assertEqual(set(payload["written"]), EXPECTED_FILES)
            self.assertEqual({path.name for path in target.glob("*.md")}, EXPECTED_FILES)

    def test_installer_preserves_unrelated_custom_agent_even_with_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary)
            custom = repo_root / ".omp" / "agents" / "my-custom-agent.md"
            custom.parent.mkdir(parents=True)
            custom.write_text("mine\n", encoding="utf-8")

            result = self._run_project(repo_root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(custom.read_text(encoding="utf-8"), "mine\n")

            forced = self._run_project(repo_root, "--force")
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertEqual(json.loads(forced.stdout)["written"], [])
            self.assertEqual(custom.read_text(encoding="utf-8"), "mine\n")

    def test_installer_refuses_changed_managed_agent_without_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary)
            self.assertEqual(self._run_project(repo_root).returncode, 0)
            changed = repo_root / ".omp" / "agents" / "developer.md"
            changed.write_text("---\nname: developer\ndescription: local\n---\nLocal.\n", encoding="utf-8")

            result = self._run_project(repo_root)
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertIn("developer.md", payload["changed"])
            self.assertIn("error", payload)
            self.assertIn("--force", payload["error"])

            forced = self._run_project(repo_root, "--force")
            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertIn("developer.md", json.loads(forced.stdout)["written"])
            self.assertIn("name: developer", changed.read_text(encoding="utf-8"))

    def test_check_mode_delegates_to_the_health_inspector(self):
        with tempfile.TemporaryDirectory() as temporary:
            agent_home = Path(temporary) / "home" / "agent"
            self.assertEqual(self._run_personal(agent_home).returncode, 0)
            target = (agent_home / "agents").resolve()
            expected = health.inspect_install(
                target=target, plugin_root=REPO_ROOT / "crux", scope="personal"
            )

            result = self._run_personal(agent_home, "--check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report, expected)
            self.assertEqual(report["drift"]["status"], "clean")
            self.assertEqual(report["installed"]["status"], "clean")

    def test_installer_missing_models_catalog_is_exit_two_json_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            scratch = Path(temporary)
            installer = self._scratch_installer_without_models_catalog(scratch)
            repo_root = scratch / "repo"
            repo_root.mkdir()

            result = self._run_isolated(installer, ["--repo-root", str(repo_root)])
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("models_catalog.py", payload["error"])
            self.assertIn("ships beside", payload["error"])
            self.assertFalse((repo_root / ".omp").exists())

    def test_installer_translates_generate_spec_violation_to_exit_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            scratch = Path(temporary)
            installer = self._scratch_installer_without_source_agents(scratch)
            repo_root = scratch / "repo"
            repo_root.mkdir()

            result = self._run_isolated(installer, ["--repo-root", str(repo_root)])
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("no source agents", payload["error"])
            self.assertFalse((repo_root / ".omp").exists())


class GeneratorCliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(GENERATOR), *args],
            check=False, capture_output=True, text=True,
        )

    def _assert_refused(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("generate-omp-agents:", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_output_dir_is_required(self):
        result = self._run("--dry-run")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("--output-dir", result.stderr)
        self.assertIn("required", result.stderr)

    def test_clean_write_and_dry_run_report_normally(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            written = self._run("--output-dir", str(output_dir))
            self.assertEqual(written.returncode, 0, written.stderr)
            payload = json.loads(written.stdout)
            self.assertEqual(set(payload["written"]), EXPECTED_FILES)
            self.assertEqual(payload["removed"], [])
            self.assertEqual({path.name for path in output_dir.glob("*.md")}, EXPECTED_FILES)

            clean = self._run("--output-dir", str(output_dir), "--dry-run")
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertEqual(json.loads(clean.stdout), {"added": [], "changed": [], "removed": []})

    def test_dry_run_reports_added_and_changed_drift_with_exit_one(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            added = self._run("--output-dir", str(output_dir), "--dry-run")
            self.assertEqual(added.returncode, 1)
            self.assertEqual(set(json.loads(added.stdout)["added"]), EXPECTED_FILES)

            self.assertEqual(self._run("--output-dir", str(output_dir)).returncode, 0)
            (output_dir / "reviewer.md").write_text("local\n", encoding="utf-8")
            changed = self._run("--output-dir", str(output_dir), "--dry-run")
            self.assertEqual(changed.returncode, 1)
            payload = json.loads(changed.stdout)
            self.assertEqual(payload["changed"], ["reviewer.md"])
            self.assertEqual(payload["added"], [])

    def test_output_dir_that_is_a_regular_file_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            blocker = Path(temporary) / "agents"
            blocker.write_text("NOT A DIRECTORY\n", encoding="utf-8")
            self._assert_refused(self._run("--output-dir", str(blocker)))
            self.assertEqual(blocker.read_text(encoding="utf-8"), "NOT A DIRECTORY\n")

    def test_symlinked_leaf_is_refused_on_the_write_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            output_dir.mkdir()
            victim = Path(temporary) / "victim.md"
            victim.write_text("SENTINEL\n", encoding="utf-8")
            (output_dir / "architect.md").symlink_to(victim)

            self._assert_refused(self._run("--output-dir", str(output_dir)))
            self.assertEqual(victim.read_text(encoding="utf-8"), "SENTINEL\n")
            self.assertFalse((output_dir / "developer.md").exists())

    def test_symlinked_leaf_is_refused_on_the_dry_run_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "agents"
            output_dir.mkdir()
            (output_dir / "architect.md").symlink_to(Path(temporary) / "gone.md")
            self._assert_refused(self._run("--output-dir", str(output_dir), "--dry-run"))


if __name__ == "__main__":
    unittest.main()
