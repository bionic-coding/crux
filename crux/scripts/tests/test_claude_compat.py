"""Tests for check-claude-compat.py — the measured compatibility verdict.

The defect this exists to prevent: a check that reports a version number and calls
it compatibility. A host can be on a new enough version and still load none of the
repository's instructions, because the fallback is suppressed by a Claude-named
file, disabled by the mode, or absent on the distribution.

The verdict must therefore name the effective instruction files and the inputs it
derived that from. These tests pin the four ways it can be wrong.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "crux" / "scripts" / "check-claude-compat.py"

_spec = importlib.util.spec_from_file_location("check_claude_compat", SCRIPT)
cc = importlib.util.module_from_spec(_spec)
sys.modules["check_claude_compat"] = cc
_spec.loader.exec_module(cc)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class CompatFixture(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "_home"
        self.home.mkdir()
        _write(self.root / "AGENTS.md", "canonical\n")

    def verdict(self, **kw):
        kw.setdefault("version", "2.1.278 (Claude Code)")
        kw.setdefault("distribution", "anthropic")
        kw.setdefault("home", self.home)
        wd = kw.pop("working_dir", self.root)
        return cc.evaluate(self.root, wd, **kw)

    def settings(self, payload: dict):
        _write(self.home / "settings.json", json.dumps(payload))


class SupportedTests(CompatFixture):
    def test_a_clean_host_on_the_default_mode_is_supported(self):
        v = self.verdict()
        self.assertTrue(v["supported"], v["reasons"])
        self.assertTrue(v["effective_instruction_files"])

    def test_the_verdict_names_the_inputs_it_was_derived_from(self):
        v = self.verdict()
        d = v["derived_from"]
        for key in ("version", "version_floor", "distribution", "builtin_disabled",
                    "mode", "mode_source", "mode_setting_exposed", "working_dir"):
            self.assertIn(key, d)
        self.assertEqual(d["version_authority"], "the v2.1.277 release changelog")

    def test_an_unexposed_setting_is_reported_as_the_default_not_as_observed(self):
        v = self.verdict()
        self.assertFalse(v["derived_from"]["mode_setting_exposed"])
        self.assertIn("default", v["derived_from"]["mode_source"])

    def test_an_exposed_setting_is_reported_with_its_source_file(self):
        self.settings({"pluginConfigs": {"agents-md@builtin": {
            "options": {"instructionFiles": "claude-md-and-agents-md"}}}})
        v = self.verdict()
        self.assertTrue(v["derived_from"]["mode_setting_exposed"])
        self.assertIn("settings.json", v["derived_from"]["mode_source"])


class VersionAndDistributionTests(CompatFixture):
    def test_a_version_below_the_floor_is_unsupported(self):
        v = self.verdict(version="2.1.276")
        self.assertFalse(v["supported"])
        self.assertTrue(any("2.1.277" in r for r in v["reasons"]))

    def test_the_floor_itself_is_supported(self):
        self.assertTrue(self.verdict(version="2.1.277")["supported"])

    def test_an_undetectable_version_is_unsupported_rather_than_assumed(self):
        v = self.verdict(version="no version here")
        self.assertFalse(v["supported"])
        self.assertTrue(any("unverified" in r for r in v["reasons"]))

    def test_each_excluded_distribution_is_unsupported(self):
        for dist in ("bedrock", "vertex", "foundry"):
            with self.subTest(dist=dist):
                v = self.verdict(distribution=dist)
                self.assertFalse(v["supported"])
                self.assertTrue(any(dist in r for r in v["reasons"]))

    def test_the_changelog_is_named_as_the_authority_for_the_exclusion(self):
        v = self.verdict(distribution="bedrock")
        self.assertTrue(any("changelog is the authority" in r for r in v["reasons"]))


class ModeTests(CompatFixture):
    def test_claude_md_mode_never_loads_agents_md(self):
        self.settings({"pluginConfigs": {"agents-md@builtin": {
            "options": {"instructionFiles": "claude-md"}}}})
        v = self.verdict()
        self.assertFalse(v["supported"])
        self.assertTrue(v["adapter_applies"])

    def test_managed_only_is_unsupported_and_the_adapter_does_not_repair_it(self):
        self.settings({"pluginConfigs": {"agents-md@builtin": {
            "options": {"instructionFiles": "managed-only"}}}})
        v = self.verdict()
        self.assertFalse(v["supported"])
        self.assertFalse(v["adapter_applies"],
                         "managed-only drops private files too; only config repairs it")
        self.assertTrue(any("configuration change" in r for r in v["reasons"]))

    def test_the_legacy_project_instructions_key_maps_onto_the_four_modes(self):
        for legacy, mode in cc.LEGACY_MODE_MAP.items():
            with self.subTest(legacy=legacy):
                self.settings({"pluginConfigs": {"agents-md@builtin": {
                    "options": {"projectInstructions": legacy}}}})
                self.assertEqual(self.verdict()["derived_from"]["mode"], mode)

    def test_a_disabled_builtin_is_unsupported(self):
        self.settings({"disabledPlugins": ["agents-md@builtin"]})
        v = self.verdict()
        self.assertFalse(v["supported"])
        self.assertTrue(any("disabled" in r for r in v["reasons"]))

    def test_an_unrecognised_mode_is_refused_rather_than_defaulted(self):
        self.settings({"pluginConfigs": {"agents-md@builtin": {
            "options": {"instructionFiles": "something-new"}}}})
        v = self.verdict()
        self.assertFalse(v["supported"])
        self.assertTrue(any("unrecognised" in r for r in v["reasons"]))


class SuppressorTests(CompatFixture):
    def test_an_on_chain_suppressor_fails_the_default_mode(self):
        _write(self.root / "CLAUDE.md", "legacy\n")
        v = self.verdict()
        self.assertFalse(v["supported"])
        self.assertTrue(any("suppressed" in r for r in v["reasons"]))
        self.assertTrue(v["suppressors"]["on_chain"])

    def test_the_same_suppressor_does_not_fail_the_and_mode(self):
        """Both names load under claude-md-and-agents-md, so nothing is suppressed."""
        _write(self.root / "CLAUDE.md", "legacy\n")
        self.settings({"pluginConfigs": {"agents-md@builtin": {
            "options": {"instructionFiles": "claude-md-and-agents-md"}}}})
        v = self.verdict()
        self.assertTrue(v["supported"], v["reasons"])
        self.assertTrue(v["suppressors"]["on_chain"],
                        "it is still REPORTED; reporting and failing are two acts")

    def test_an_off_chain_suppressor_is_reported_and_fails_nothing(self):
        _write(self.root / "sub" / "CLAUDE.local.md", "private\n")
        v = self.verdict(working_dir=self.root)
        self.assertTrue(v["supported"], v["reasons"])
        self.assertTrue(v["suppressors"]["off_chain"])
        self.assertFalse(v["suppressors"]["on_chain"])

    def test_the_same_file_fails_once_the_working_directory_moves_onto_its_chain(self):
        """A private override silences the tree for anyone working inside it."""
        _write(self.root / "sub" / "CLAUDE.local.md", "private\n")
        v = self.verdict(working_dir=self.root / "sub")
        self.assertFalse(v["supported"])
        self.assertTrue(v["suppressors"]["on_chain"])

    def test_crux_never_claims_it_will_touch_a_private_override(self):
        """The remedy may say the file is the user's to delete. It may not say
        crux deletes it, and nothing may propose that crux does."""
        _write(self.root / "CLAUDE.local.md", "private\n")
        v = self.verdict()
        sup = [s for s in v["suppressors"]["on_chain"] + v["suppressors"]["off_chain"]
               if s["path"].endswith("CLAUDE.local.md")]
        self.assertEqual(len(sup), 1, "positive control: the override was reported")
        remedy = sup[0]["remedy"]
        self.assertIn("yours", remedy, "the action is attributed to the user")
        for claim in ("crux will", "we delete", "will be deleted", "automatically"):
            self.assertNotIn(claim, json.dumps(v).lower())
        self.assertTrue((self.root / "CLAUDE.local.md").is_file(),
                        "reporting must not have touched it")


class EntryPointTests(CompatFixture):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(self.root),
             "--claude-home", str(self.home), *args],
            capture_output=True, text=True)

    def test_supported_exits_zero_with_json(self):
        r = self._run("--claude-version", "2.1.278", "--distribution", "anthropic")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout)["supported"])

    def test_unsupported_exits_one_with_json(self):
        r = self._run("--claude-version", "2.1.100", "--distribution", "anthropic")
        self.assertEqual(r.returncode, 1)
        payload = json.loads(r.stdout)
        self.assertFalse(payload["supported"])
        self.assertTrue(payload["reasons"])

    def test_a_missing_repo_root_is_a_capability_error(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(self.root / "nope")],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout.strip(), "")
        self.assertTrue(r.stderr.strip())

    def test_the_script_declares_no_third_party_dependencies(self):
        head = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("# /// script", head)
        self.assertIn("dependencies = []", head)



# --------------------------------------------- settings precedence (review S3)


class SettingsPrecedenceTests(CompatFixture):
    """Claude Code resolves local > project > user.

    Review found this inverted and untested: every existing test wrote to `home`
    only, so a user-first read that returned on the first hit passed them all while
    reporting a mode the host does not use.
    """

    def _project(self, payload, local=False):
        name = "settings.local.json" if local else "settings.json"
        _write(self.root / ".claude" / name, json.dumps(payload))

    @staticmethod
    def _mode(value):
        return {"pluginConfigs": {"agents-md@builtin":
                                  {"options": {"instructionFiles": value}}}}

    def test_a_project_setting_beats_the_user_setting(self):
        self.settings(self._mode("claude-md-and-agents-md"))
        self._project(self._mode("claude-md"))
        v = self.verdict()
        self.assertEqual(v["derived_from"]["mode"], "claude-md")
        self.assertIn(".claude/settings.json", v["derived_from"]["mode_source"])

    def test_a_local_setting_beats_the_project_setting(self):
        self._project(self._mode("claude-md"))
        self._project(self._mode("claude-md-and-agents-md"), local=True)
        v = self.verdict()
        self.assertEqual(v["derived_from"]["mode"], "claude-md-and-agents-md")
        self.assertIn("settings.local.json", v["derived_from"]["mode_source"])

    def test_the_user_setting_still_applies_when_no_project_setting_exists(self):
        """Positive control: precedence did not simply disable the user source."""
        self.settings(self._mode("claude-md"))
        v = self.verdict()
        self.assertEqual(v["derived_from"]["mode"], "claude-md")

    def test_precedence_holds_for_the_builtin_disabled_flag_too(self):
        self.settings({"disabledPlugins": ["agents-md@builtin"]})
        self._project({"enabledPlugins": ["agents-md@builtin"]}, local=True)
        self.assertFalse(self.verdict()["derived_from"]["builtin_disabled"])


class EffectiveFileTests(CompatFixture):
    """Clause 10 names the effective files. Naming one it never stats is inference."""

    def test_only_files_that_exist_are_named(self):
        v = self.verdict()
        for rel in v["effective_instruction_files"]:
            self.assertTrue((self.root / rel).is_file(), rel)

    def test_the_canonical_file_is_named_when_it_exists(self):
        """Positive control for the assertion above."""
        self.assertIn("AGENTS.md", self.verdict()["effective_instruction_files"])


# ----------------------------------------------------- the adapter (review M4)


class AdapterAuditTests(CompatFixture):
    """Clause 11's three reports, which review found asserted in prose and
    implemented nowhere."""

    def setUp(self):
        super().setUp()
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(
            "claude_adapter", REPO_ROOT / "crux" / "scripts" / "claude_adapter.py")
        self.ad = ilu.module_from_spec(spec)
        # Register BEFORE exec: @dataclass resolves cls.__module__ through
        # sys.modules, and an unregistered module makes that lookup return None.
        sys.modules["claude_adapter"] = self.ad
        spec.loader.exec_module(self.ad)
        _write(self.root / "bionic" / "AGENTS.md", "tree schema\n")
        self.tracked = ["AGENTS.md", "bionic/AGENTS.md"]

    def test_a_generated_adapter_carries_its_source_and_digest(self):
        path = self.ad.generate(self.root, ".")
        text = path.read_text(encoding="utf-8")
        self.assertTrue(self.ad.is_adapter(text))
        self.assertEqual(len(self.ad.recorded_digest(text)), 64)
        self.assertIn("canonical", text, "the source content is carried through")

    def test_a_current_adapter_is_reported_current_on_an_unsupported_host(self):
        self.ad.generate(self.root, ".")
        self.ad.generate(self.root, "bionic")
        a = self.ad.audit(self.root, self.tracked, host_supported=False)
        self.assertEqual({r.status for r in a.adapters}, {"current"})
        self.assertTrue(a.clean(), a.findings)

    def test_an_adapter_whose_source_moved_is_reported_stale(self):
        self.ad.generate(self.root, ".")
        self.ad.generate(self.root, "bionic")
        _write(self.root / "AGENTS.md", "canonical, edited\n")
        a = self.ad.audit(self.root, self.tracked, host_supported=False)
        stale = [r for r in a.adapters if r.status == "stale"]
        self.assertEqual([r.scope for r in stale], ["."])
        self.assertTrue(any("STALE" in f for f in a.findings))

    def test_an_adapter_on_a_supported_host_is_reported_removable(self):
        self.ad.generate(self.root, ".")
        self.ad.generate(self.root, "bionic")
        a = self.ad.audit(self.root, self.tracked, host_supported=True)
        self.assertEqual({r.status for r in a.adapters}, {"removable"})
        self.assertTrue(any("REMOVABLE" in f for f in a.findings))

    def test_a_root_only_adapter_is_reported_incomplete(self):
        """The hazard: a root adapter suppresses every AGENTS.md beneath it."""
        self.ad.generate(self.root, ".")
        a = self.ad.audit(self.root, self.tracked, host_supported=False)
        self.assertEqual(a.incomplete, ["bionic"])
        self.assertTrue(any("INCOMPLETE" in f for f in a.findings))

    def test_adapters_at_every_scope_are_not_incomplete(self):
        """Positive control for the finding above."""
        self.ad.generate(self.root, ".")
        self.ad.generate(self.root, "bionic")
        a = self.ad.audit(self.root, self.tracked, host_supported=False)
        self.assertEqual(a.incomplete, [])

    def test_a_legacy_claude_md_is_not_mistaken_for_an_adapter(self):
        """A hand-written CLAUDE.md carries no generated header; it belongs to the
        migration, not to this audit."""
        _write(self.root / "CLAUDE.md", "# CLAUDE.md\n\nhand written\n")
        a = self.ad.audit(self.root, self.tracked, host_supported=True)
        self.assertEqual(a.adapters, [])
        self.assertEqual(a.findings, [])

    def test_an_adapter_whose_source_vanished_is_reported_orphan(self):
        self.ad.generate(self.root, "bionic")
        (self.root / "bionic" / "AGENTS.md").unlink()
        a = self.ad.audit(self.root, self.tracked, host_supported=False)
        self.assertEqual([r.status for r in a.adapters], ["orphan"])

    def test_the_audit_never_writes_or_deletes(self):
        self.ad.generate(self.root, ".")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.ad.audit(self.root, self.tracked, host_supported=True)
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_the_verdict_carries_the_adapter_report(self):
        self.ad.generate(self.root, ".")
        v = self.verdict()
        self.assertIn("adapters", v)
        self.assertTrue(v["adapters"]["findings"],
                        "a root-only adapter on a supported host owes findings")


if __name__ == "__main__":
    unittest.main()
