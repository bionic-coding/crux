"""The mechanical tier check: every refusal code of ``test-tiers.py``, each driven through the CLI.

Every refusal test starts from a valid fixture (the positive control: it passes with exit 0 and no
finding), applies one mutation, and asserts the exit status and the finding code. Fixtures are built
in temporary directories. No committed file besides a real root manifest is named ``test-tiers.json``:
the fixture root keeps its manifest as ``test-tiers.example.json`` and each test renames a copy.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE.parent / "test-tiers.py"
FIXTURE = HERE / "fixtures" / "test_tiers"

TEST_SOURCE = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_one(self):\n        pass\n"
TWO_SOURCE = TEST_SOURCE + "\n    def test_two(self):\n        pass\n"


def run(*argv, cwd=None):
    done = subprocess.run([sys.executable, str(CLI), *argv], capture_output=True, text=True, cwd=cwd, timeout=120)
    return done.returncode, done.stdout, done.stderr


def codes(report):
    return sorted(f["code"] for f in report["findings"])


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def json_of(self, out):
        return json.loads(out)


class RootCase(Base):
    """A copy of the valid fixture root, checked with ``check --root``."""

    def setUp(self):
        super().setUp()
        self.root = self.base / "root"
        shutil.copytree(FIXTURE, self.root)
        (self.root / "test-tiers.example.json").rename(self.root / "test-tiers.json")

    def manifest(self):
        return json.loads((self.root / "test-tiers.json").read_text())

    def write(self, data):
        (self.root / "test-tiers.json").write_text(json.dumps(data))

    def check(self, *extra):
        code, out, err = run("check", "--root", str(self.root), *extra)
        return code, (json.loads(out) if out.strip() else None), err

    def assert_valid(self):
        code, report, err = self.check()
        self.assertEqual((code, report["findings"]), (0, []), err)

    def assert_refused(self, expected_codes):
        code, report, err = self.check()
        self.assertEqual((code, codes(report)), (1, sorted(expected_codes)), err)
        return report


class LabelRuleTests(RootCase):
    def test_unlabelled_file(self):
        self.assert_valid()
        (self.root / "test_new.py").write_text(TEST_SOURCE)
        report = self.assert_refused(["unlabelled"])
        self.assertIn("test_new.py", report["findings"][0]["detail"])

    def test_unlabelled_nested(self):
        sub = self.root / "sub"
        sub.mkdir()
        (sub / "test_deep.py").write_text(TEST_SOURCE)
        self.assert_valid()  # no __init__.py: the runner does not reach it
        (sub / "__init__.py").write_text("")
        self.assert_refused(["unlabelled-nested"])

    def test_duplicate_key_is_a_doubly_labelled_file(self):
        self.assert_valid()
        text = (self.root / "test-tiers.json").read_text()
        text = text.replace('"test_old.py": {', '"test_old.py": {"tier": "dev"}, "test_old.py": {', 1)
        (self.root / "test-tiers.json").write_text(text)
        report = self.assert_refused(["duplicate-key"])
        self.assertIn("test_old.py", report["findings"][0]["detail"])

    def test_redundant_override(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_gate.py"]["overrides"]["Gate.test_x"] = {"tier": "release", "area": "core"}
        self.write(data)
        self.assert_refused(["redundant-override"])

    def test_stale_file(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_gone.py"] = {"tier": "dev"}
        self.write(data)
        self.assert_refused(["stale-file"])

    def test_stale_class_override(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_basic.py"]["overrides"]["Missing"] = {"tier": "release", "area": "core"}
        self.write(data)
        self.assert_refused(["stale-override"])

    def test_stale_method_override(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_basic.py"]["overrides"]["Plain.test_zzz"] = {"tier": "release", "area": "core"}
        self.write(data)
        self.assert_refused(["stale-override"])

    def test_undeclared_area(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_gate.py"]["area"] = "nowhere"
        self.write(data)
        self.assert_refused(["undeclared-area"])

    def test_release_without_area(self):
        self.assert_valid()
        data = self.manifest()
        del data["files"]["test_gate.py"]["area"]
        self.write(data)
        self.assert_refused(["missing-area"])


class EphemeralAndFieldTests(RootCase):
    def test_ephemeral_without_reason(self):
        self.assert_valid()
        data = self.manifest()
        del data["files"]["test_old.py"]["reason"]
        self.write(data)
        self.assert_refused(["ephemeral-no-reason"])

    def test_ephemeral_without_expires_or_retire_when(self):
        self.assert_valid()
        data = self.manifest()
        del data["files"]["test_old.py"]["expires"]
        self.write(data)
        self.assert_refused(["ephemeral-no-expiry"])

    def test_disallowed_field(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_gate.py"]["overrides"]["Gate.test_y"]["area"] = "core"  # a dev entry carries no area
        self.write(data)
        self.assert_refused(["bad-field"])

    def test_unknown_key(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_gate.py"]["owner"] = "someone"
        self.write(data)
        self.assert_refused(["bad-field"])

    def test_invalid_date(self):
        self.assert_valid()
        data = self.manifest()
        data["files"]["test_old.py"]["expires"] = "2099-13-45"
        self.write(data)
        self.assert_refused(["bad-date"])

    def test_expired_ephemeral_is_reported_once_per_file_and_does_not_fail(self):
        code, report, err = self.check()
        self.assertEqual((code, report["expired"]), (0, []), err)  # positive control: future expiry
        data = self.manifest()
        data["files"]["test_basic.py"]["tier"] = "ephemeral"
        data["files"]["test_basic.py"].update(reason="Old record", expires="2000-01-01")
        data["files"]["test_basic.py"]["overrides"] = {"Critical": {"tier": "release", "area": "core"}}
        self.write(data)
        code, out, err = run("check", "--repo-root", str(self.base), "--discover", "filesystem")
        report = json.loads(out)
        self.assertEqual((code, report["findings"]), (0, []), err)
        self.assertEqual([(row["file"], row["expires"]) for row in report["expired"]],
                         [("test_basic.py", "2000-01-01")])
        self.assertTrue(report["expired"][0]["path"].endswith("test-tiers.json"))


class FileGlobTests(Base):
    def test_the_manifest_is_not_an_unlabelled_file_when_the_pattern_matches_it(self):
        root = self.base / "globroot"
        root.mkdir()
        (root / "case_a.json").write_text("{}")
        manifest = {"format": "crux.test-tiers", "version": 1, "kind": "file-glob", "pattern": "*.json",
                    "areas": {}, "files": {"case_a.json": {"tier": "dev"}}}
        (root / "test-tiers.json").write_text(json.dumps(manifest))
        code, out, err = run("check", "--root", str(root))
        self.assertEqual((code, self.json_of(out)["findings"]), (0, []), err)
        (root / "case_b.json").write_text("{}")  # the same root with a real unlabelled file
        code, out, _ = run("check", "--root", str(root))
        report = self.json_of(out)
        self.assertEqual((code, codes(report)), (1, ["unlabelled"]))
        self.assertIn("case_b.json", report["findings"][0]["detail"])


class ProjectCase(Base):
    """A project with roots under it, checked with ``check --repo-root`` and filesystem discovery."""

    def make_root(self, name, sources, files, areas=None):
        root = self.base / name
        root.mkdir(parents=True, exist_ok=True)
        for fname, source in sources.items():
            (root / fname).write_text(source)
        manifest = {"format": "crux.test-tiers", "version": 1, "kind": "python-unittest", "pattern": "test*.py",
                    "areas": {"core": "The core path"} if areas is None else areas, "files": files}
        (root / "test-tiers.json").write_text(json.dumps(manifest))
        return root

    def good(self):
        return self.make_root("tests", {"test_a.py": TEST_SOURCE, "test_b.py": TEST_SOURCE},
                              {"test_a.py": {"tier": "release", "area": "core"}, "test_b.py": {"tier": "dev"}})

    def project(self, *extra):
        code, out, err = run("check", "--repo-root", str(self.base), "--discover", "filesystem", *extra)
        return code, (json.loads(out) if out.strip() else None), err

    def assert_valid(self, *extra):
        code, report, err = self.project(*extra)
        self.assertEqual((code, report["findings"]), (0, []), err)
        return report

    def assert_refused(self, expected_codes, *extra):
        code, report, err = self.project(*extra)
        self.assertEqual((code, codes(report)), (1, sorted(expected_codes)), err)
        return report

    def edit(self, root, fn):
        path = root / "test-tiers.json"
        data = json.loads(path.read_text())
        fn(data)
        path.write_text(json.dumps(data))


class ProperSubsetTests(ProjectCase):
    def test_zero_release_units(self):
        root = self.good()
        self.assert_valid()
        self.edit(root, lambda d: d["files"].update({"test_a.py": {"tier": "dev"}}))
        report = self.assert_refused(["no-release-units", "uncovered-area"])
        self.assertEqual(report["counts"]["release"], 0)

    def test_zero_non_release_units(self):
        root = self.good()
        self.assert_valid()
        self.edit(root, lambda d: d["files"].update({"test_b.py": {"tier": "release", "area": "core"}}))
        self.assert_refused(["no-non-release-units"])

    def test_too_small_for_adoption(self):
        root = self.make_root("tests", {"test_a.py": TEST_SOURCE}, {"test_a.py": {"tier": "release", "area": "core"}})
        code, report, err = self.project()
        self.assertEqual((code, codes(report)), (1, ["no-non-release-units", "too-small"]), err)
        (root / "test_b.py").write_text(TEST_SOURCE)
        self.edit(root, lambda d: d["files"].update({"test_b.py": {"tier": "dev"}}))
        self.assert_valid()

    def test_uncovered_area(self):
        root = self.good()
        self.assert_valid()
        self.edit(root, lambda d: d["areas"].update({"extra": "An area no release test covers"}))
        report = self.assert_refused(["uncovered-area"])
        self.assertIn("extra", report["findings"][0]["detail"])

    def test_undeclared_area_in_a_project_check(self):
        root = self.good()
        self.assert_valid()
        self.edit(root, lambda d: d["files"]["test_a.py"].update(area="nowhere"))
        self.assert_refused(["undeclared-area", "uncovered-area"])

    def test_area_conflict_across_roots(self):
        self.good()
        other = self.make_root("tools", {"test_c.py": TEST_SOURCE, "test_d.py": TEST_SOURCE},
                               {"test_c.py": {"tier": "release", "area": "core"}, "test_d.py": {"tier": "dev"}})
        self.assert_valid()
        self.edit(other, lambda d: d["areas"].update(core="A different description"))
        self.assert_refused(["area-conflict"])


class RootExpectationTests(ProjectCase):
    def test_no_manifest_is_unconfigured_without_expect_root_and_missing_with_it(self):
        (self.base / "tests").mkdir()
        code, report, err = self.project()
        self.assertEqual((code, report["configured"], report["findings"]), (0, False, []), err)
        code, report, err = self.project("--expect-root", "tests")
        self.assertEqual((code, codes(report)), (1, ["missing-root"]), err)
        self.good()  # positive control: the expected root holds a manifest
        self.assert_valid("--expect-root", "tests")

    def test_require_release_units_names_a_root_with_none(self):
        root = self.good()
        self.assert_valid("--require-release-units", "tests")
        self.edit(root, lambda d: d["files"].update({"test_a.py": {"tier": "dev"}}))
        report = self.assert_refused(["no-release-units", "root-no-release-units", "uncovered-area"],
                                     "--require-release-units", "tests")
        self.assertEqual([f["path"] for f in report["findings"] if f["code"] == "root-no-release-units"], ["tests"])

    def test_require_release_units_names_a_root_with_no_manifest(self):
        self.good()
        (self.base / "tools").mkdir()
        self.assert_valid("--require-release-units", "tests")
        report = self.assert_refused(["root-no-release-units"], "--require-release-units", "tools", "--require-release-units", "tests")
        self.assertIn("no checked manifest", report["findings"][0]["detail"])


class DoublyLabelledTests(ProjectCase):
    def test_a_file_under_two_manifests(self):
        outer = self.good()
        inner = outer / "sub"
        inner.mkdir()
        (inner / "test_s.py").write_text(TEST_SOURCE)
        manifest = {"format": "crux.test-tiers", "version": 1, "kind": "python-unittest", "pattern": "test*.py",
                    "areas": {"core": "The core path"}, "files": {"test_s.py": {"tier": "dev"}}}
        (inner / "test-tiers.json").write_text(json.dumps(manifest))
        self.assert_valid()  # no __init__.py: the outer runner never reaches sub/test_s.py
        (inner / "__init__.py").write_text("")
        report = self.assert_refused(["doubly-labelled", "unlabelled-nested"])
        doubly = [f for f in report["findings"] if f["code"] == "doubly-labelled"][0]
        self.assertTrue(doubly["path"].endswith("test_s.py"))


class ShardAndMergeTests(RootCase):
    def shard(self, name, files, **top):
        data = self.manifest()
        data.update(top)
        data["files"] = {f: data["files"][f] for f in files}
        path = self.base / f"{name}.shard.json"
        path.write_text(json.dumps(data))
        return path

    def test_shard_check_skips_unlabelled_rules_and_refuses_a_disallowed_field(self):
        path = self.shard("a", ["test_gate.py"])
        code, out, err = run("check", "--root", str(self.root), "--shard", str(path))
        self.assertEqual((code, self.json_of(out)["findings"]), (0, []), err)
        data = json.loads(path.read_text())
        data["files"]["test_gate.py"]["overrides"]["Gate.test_y"]["reason"] = "dev carries no reason"
        path.write_text(json.dumps(data))
        code, out, _ = run("check", "--root", str(self.root), "--shard", str(path))
        self.assertEqual((code, codes(self.json_of(out))), (1, ["bad-field"]))

    def test_shard_without_root_is_a_usage_error(self):
        path = self.shard("a", ["test_gate.py"])
        code, _, err = run("check", "--shard", str(path))
        self.assertEqual(code, 2)
        self.assertIn("--shard needs --root", err)

    def test_merge_refuses_a_file_in_two_shards_and_conflicting_area_descriptions(self):
        a = self.shard("a", ["test_basic.py"])
        b = self.shard("b", ["test_gate.py", "test_old.py"])
        c = self.shard("c", ["test_gate.py"])
        d = self.shard("d", ["test_gate.py", "test_old.py"], areas={"core": "Another description"})
        (self.root / "test-tiers.json").unlink()
        code, out, err = run("merge", "--root", str(self.root), "--shard", str(a), "--shard", str(b))
        self.assertEqual((code, self.json_of(out)["merged"]), (0, True), err)  # positive control
        (self.root / "test-tiers.json").unlink()
        code, out, _ = run("merge", "--root", str(self.root), "--shard", str(c), "--shard", str(b))
        self.assertEqual((code, codes(self.json_of(out))), (1, ["doubly-labelled"]))
        self.assertFalse((self.root / "test-tiers.json").exists())
        code, out, _ = run("merge", "--root", str(self.root), "--shard", str(a), "--shard", str(d))
        self.assertEqual((code, codes(self.json_of(out))), (1, ["area-conflict"]))
        self.assertFalse((self.root / "test-tiers.json").exists())


class ListTests(RootCase):
    def test_list_and_list_ids_select_by_tier(self):
        code, out, err = run("list", "--root", str(self.root), "--tier", "release")
        self.assertEqual((code, out.split()), (0, ["test_basic.py", "test_gate.py"]), err)
        code, out, err = run("list", "--root", str(self.root), "--tier", "release", "--ids")
        self.assertEqual((code, out.split()), (0, ["test_basic.Critical", "test_gate.Gate.test_x"]), err)

    def test_list_refuses_with_exit_two_when_a_per_root_rule_fails(self):
        code, _, err = run("list", "--root", str(self.root), "--tier", "dev", "--ids")
        self.assertEqual(code, 0, err)  # positive control
        (self.root / "test_new.py").write_text(TEST_SOURCE)
        code, out, err = run("list", "--root", str(self.root), "--tier", "dev", "--ids")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("unlabelled", err)


if __name__ == "__main__":
    unittest.main()
