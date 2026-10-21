"""Static health reports for installed Crux OMP agents.

Covers `omp_agent_health.inspect_install`, its CLI exit contract, managed-leaf
safety findings, project shadow detection, and plugin-manifest refusal.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "crux" / "scripts"
HEALTH_CLI = SCRIPTS_DIR / "omp_agent_health.py"
sys.path.insert(0, str(SCRIPTS_DIR))

import omp_agent_health as health  # noqa: E402
import omp_agents as agents  # noqa: E402

EXPECTED_SOURCE_NAMES = {
    "architect", "brainstormer", "commander", "dev-lead", "developer",
    "historian", "librarian", "night-gardener", "reviewer", "wayfinder",
}
EXPECTED_FILES = {f"{name}.md" for name in EXPECTED_SOURCE_NAMES}


class HealthTests(unittest.TestCase):
    def _health_cli(
        self,
        target: Path,
        *,
        plugin: Path = REPO_ROOT / "crux",
        scope: str = "personal",
        project_context: Path | None = None,
        timeout: float = 10,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable, str(HEALTH_CLI),
            "--target", str(target),
            "--plugin-root", str(plugin),
            "--scope", scope,
        ]
        if project_context is not None:
            command.extend(["--project-context", str(project_context)])
        try:
            return subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            self.fail(f"health CLI blocked on target inspection: {exc}")

    def _write_clean_install(self, target: Path) -> None:
        agents.write(target, agents.generate())

    def test_clean_install_is_exit_zero_and_reports_every_role_installed(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "agents"
            self._write_clean_install(target)
            direct = health.inspect_install(
                target=target, plugin_root=REPO_ROOT / "crux", scope="personal"
            )
            result = self._health_cli(target)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report, direct)
        self.assertEqual(report["drift"]["status"], "clean")
        self.assertEqual(report["installed"]["status"], "clean")
        self.assertEqual({role["role"] for role in report["installed"]["roles"]}, EXPECTED_SOURCE_NAMES)
        self.assertTrue(all(role["status"] == "installed" for role in report["installed"]["roles"]))
        self.assertEqual(report["shadows"]["status"], "unverified")
        self.assertEqual(report["runtime"]["status"], "unverified")
        self.assertIsNone(report["runtime"]["client_version"])

    def test_missing_install_is_exit_one_with_every_role_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "absent" / "agents"
            result = self._health_cli(target)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["drift"]["status"], "drift")
        self.assertEqual(set(report["drift"]["added"]), EXPECTED_FILES)
        self.assertEqual(report["installed"]["status"], "findings")
        self.assertEqual({role["status"] for role in report["installed"]["roles"]}, {"missing"})

    def test_drifted_install_is_exit_one_and_names_the_changed_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "agents"
            self._write_clean_install(target)
            (target / "reviewer.md").write_text("locally changed\n", encoding="utf-8")
            result = self._health_cli(target)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["drift"]["status"], "drift")
        self.assertEqual(report["drift"]["changed"], ["reviewer.md"])
        self.assertEqual(report["drift"]["added"], [])
        installed = {role["role"]: role for role in report["installed"]["roles"]}
        self.assertEqual(installed["reviewer"]["status"], "malformed")
        self.assertEqual(installed["architect"]["status"], "installed")

    def test_health_reports_symlink_fifo_directory_and_invalid_utf8_without_blocking(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "agents"
            target.mkdir()
            victim = Path(temporary) / "victim.md"
            victim.write_text("sentinel", encoding="utf-8")
            (target / "architect.md").symlink_to(victim)
            (target / "developer.md").write_bytes(b"\xff\xfe")
            os.mkfifo(target / "historian.md")
            (target / "librarian.md").mkdir()
            result = self._health_cli(target)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        installed = {role["role"]: role for role in report["installed"]["roles"]}
        self.assertEqual(installed["architect"]["status"], "unsafe")
        self.assertEqual(installed["developer"]["status"], "malformed")
        self.assertEqual(installed["historian"]["status"], "unsafe")
        self.assertEqual(installed["librarian"]["status"], "unsafe")
        self.assertEqual(report["installed"]["status"], "findings")
        self.assertIn("architect.md", report["drift"]["changed"])

    def test_project_shadows_use_effective_names_and_report_unsafe_and_malformed_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            agents_dir = project / ".omp" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "custom-name.md").write_text(
                "---\nname: reviewer\ndescription: project shadow\n---\nBody.\n",
                encoding="utf-8",
            )
            (agents_dir / "bad.md").write_text("not frontmatter\n", encoding="utf-8")
            victim = root / "victim.md"
            victim.write_text("sentinel", encoding="utf-8")
            (agents_dir / "unsafe.md").symlink_to(victim)
            os.mkfifo(agents_dir / "special.md")

            result = self._health_cli(
                root / "target", scope="personal", project_context=project
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        shadows = json.loads(result.stdout)["shadows"]
        self.assertEqual(shadows["status"], "findings")
        self.assertEqual(
            shadows["roles"],
            [{"role": "reviewer", "file": "custom-name.md", "name": "reviewer"}],
        )
        self.assertEqual([item["file"] for item in shadows["malformed"]], ["bad.md"])
        self.assertEqual({item["file"] for item in shadows["unsafe"]}, {"unsafe.md", "special.md"})


    def test_project_shadows_discover_nearest_ancestor_omp_root_from_nested_subdirectory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            nested = project / "src" / "pkg"
            nested.mkdir(parents=True)
            agents_dir = project / ".omp" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "reviewer.md").write_text(
                "---\nname: reviewer\ndescription: ancestor shadow\n---\nBody.\n",
                encoding="utf-8",
            )

            result = self._health_cli(
                root / "target", scope="personal", project_context=nested
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        shadows = json.loads(result.stdout)["shadows"]
        self.assertEqual(shadows["status"], "findings")
        self.assertEqual(
            shadows["roles"],
            [{"role": "reviewer", "file": "reviewer.md", "name": "reviewer"}],
        )
    def test_project_shadow_scan_does_not_follow_an_escaping_omp_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            project.mkdir()
            outside = root / "outside"
            outside_agents = outside / "agents"
            outside_agents.mkdir(parents=True)
            (outside_agents / "external.md").write_text(
                "---\nname: architect\ndescription: external\n---\nBody.\n",
                encoding="utf-8",
            )
            (project / ".omp").symlink_to(outside, target_is_directory=True)

            result = self._health_cli(
                root / "target", scope="personal", project_context=project
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        shadows = json.loads(result.stdout)["shadows"]
        self.assertEqual(shadows["status"], "findings")
        self.assertEqual([item["file"] for item in shadows["unsafe"]], [".omp"])
        self.assertEqual(shadows["roles"], [])
        self.assertEqual(shadows["malformed"], [])

    def test_plugin_manifest_invalid_utf8_or_nonobject_is_a_spec_violation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "plugin.json"
            manifest.write_bytes(b"\xff")
            with self.assertRaises(health.omp_agents.SpecViolation):
                health._plugin(root)
            manifest.write_text("[]", encoding="utf-8")
            with self.assertRaises(health.omp_agents.SpecViolation):
                health._plugin(root)

    def test_health_cli_returns_structured_exit_two_for_invalid_manifest_before_target_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "plugin"
            root.mkdir()
            manifest = root / "plugin.json"
            target = Path(temporary) / "agents"
            for payload in (b"\xff", b"not json", b"[]", b'{"version": null}', b'{"version": " "}'):
                with self.subTest(payload=payload):
                    manifest.write_bytes(payload)
                    result = self._health_cli(target, plugin=root)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    error = json.loads(result.stdout)["error"]
                    self.assertIn("plugin manifest", error)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
