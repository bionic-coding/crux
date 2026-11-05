"""The test-tier reader and the ``test-tiers.py`` CLI, proved end to end on the fixture root.

The fixture root ``fixtures/test_tiers`` holds one file per tier with a class override and a method
override. Its manifest is named ``test-tiers.example.json`` in the repository, so no committed file
besides a real root manifest carries the reader's name; each test copies the root to a temporary
directory and renames the manifest. Every case drives the CLI in a subprocess. The refusal cases pair
with the valid root they were mutated from, which passes (the positive control).
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
CLI = SCRIPTS / "test-tiers.py"
FIXTURE = HERE / "fixtures" / "test_tiers"
SCHEMA = SCRIPTS.parent / "schemas" / "test-tiers.schema.json"

sys.path.insert(0, str(SCRIPTS))
import test_tiers  # noqa: E402


def run(*argv, cwd=None):
    done = subprocess.run([sys.executable, str(CLI), *argv], capture_output=True, text=True, cwd=cwd, timeout=120)
    return done.returncode, done.stdout, done.stderr


class FixtureCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / "root"
        shutil.copytree(FIXTURE, self.root)
        (self.root / "test-tiers.example.json").rename(self.root / "test-tiers.json")

    def manifest(self):
        return json.loads((self.root / "test-tiers.json").read_text())

    def write(self, data):
        (self.root / "test-tiers.json").write_text(json.dumps(data))

    def check(self, *extra):
        code, out, err = run("check", "--root", str(self.root), *extra)
        return code, json.loads(out) if out.strip() else None, err


class CheckTests(FixtureCase):
    def test_check_exits_zero_on_the_fixture_root_with_one_tier_per_unit(self):
        code, report, err = self.check()
        self.assertEqual(code, 0, err)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["counts"], {"dev": 2, "ephemeral": 2, "release": 3})

    def test_an_unlabelled_file_fails_with_its_code_while_the_valid_root_passes(self):
        self.assertEqual(self.check()[0], 0)  # positive control
        (self.root / "test_new.py").write_text("import unittest\nclass N(unittest.TestCase):\n    def test_n(self):\n        pass\n")
        code, report, _ = self.check()
        self.assertEqual(code, 1)
        self.assertEqual([(f["code"], "test_new.py" in f["detail"]) for f in report["findings"]], [("unlabelled", True)])

    def test_a_stale_class_override_fails_with_its_code(self):
        data = self.manifest()
        data["files"]["test_basic.py"]["overrides"]["Missing"] = {"tier": "release", "area": "core"}
        self.write(data)
        code, report, _ = self.check()
        self.assertEqual(code, 1)
        self.assertEqual([f["code"] for f in report["findings"]], ["stale-override"])

    def test_a_missing_manifest_exits_two(self):
        (self.root / "test-tiers.json").unlink()
        code, out, err = run("check", "--root", str(self.root))
        self.assertEqual(code, 2)
        self.assertIn("cannot read the tier manifest", err)


class ShardTests(FixtureCase):
    """check --shard on a partial manifest, as a classifier validates its work."""

    def shard(self, *files):
        data = self.manifest()
        data["files"] = {name: data["files"][name] for name in files}
        path = self.base / "alpha.shard.json"
        path.write_text(json.dumps(data))
        return path

    def test_a_partial_shard_passes_without_the_unlabelled_rules(self):
        path = self.shard("test_gate.py")
        code, out, err = run("check", "--root", str(self.root), "--shard", str(path))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["findings"], [])
        # the same partial manifest as the root's manifest leaves two files unlabelled
        (self.root / "test-tiers.json").write_text(path.read_text())
        code, report, _ = self.check()
        self.assertEqual((code, sorted(f["code"] for f in report["findings"])), (1, ["unlabelled", "unlabelled"]))

    def test_a_shard_with_an_undeclared_area_fails(self):
        path = self.shard("test_gate.py")
        data = json.loads(path.read_text())
        data["files"]["test_gate.py"]["area"] = "nowhere"
        path.write_text(json.dumps(data))
        code, out, _ = run("check", "--root", str(self.root), "--shard", str(path))
        self.assertEqual(code, 1)
        self.assertEqual([f["code"] for f in json.loads(out)["findings"]], ["undeclared-area"])

    def test_a_shard_that_names_an_absent_file_fails(self):
        path = self.shard("test_gate.py")
        data = json.loads(path.read_text())
        data["files"]["test_gone.py"] = {"tier": "dev"}
        path.write_text(json.dumps(data))
        code, out, _ = run("check", "--root", str(self.root), "--shard", str(path))
        self.assertEqual(code, 1)
        self.assertEqual([f["code"] for f in json.loads(out)["findings"]], ["stale-file"])


class ListTests(FixtureCase):
    def test_list_prints_the_files_holding_a_unit_of_the_tier(self):
        code, out, err = run("list", "--root", str(self.root), "--tier", "release")
        self.assertEqual((code, out.split()), (0, ["test_basic.py", "test_gate.py"]), err)

    def test_list_ids_resolves_file_class_and_method_overrides(self):
        code, out, err = run("list", "--root", str(self.root), "--tier", "release", "--ids")
        self.assertEqual((code, out.split()), (0, ["test_basic.Critical", "test_gate.Gate.test_x"]), err)
        code, out, err = run("list", "--root", str(self.root), "--tier", "ephemeral", "--ids")
        self.assertEqual((code, out.split()), (0, ["test_basic.Plain.test_b", "test_old"]), err)
        code, out, err = run("list", "--root", str(self.root), "--tier", "dev", "--ids")
        self.assertEqual((code, out.split()), (0, ["test_basic.Plain.test_a", "test_gate.Gate.test_y"]), err)

    def test_list_exits_two_on_a_manifest_finding(self):
        (self.root / "test_new.py").write_text("import unittest\n")
        code, out, err = run("list", "--root", str(self.root), "--tier", "release")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("unlabelled", err)

    def test_list_exits_two_on_a_missing_manifest(self):
        (self.root / "test-tiers.json").unlink()
        code, _, err = run("list", "--root", str(self.root), "--tier", "release")
        self.assertEqual(code, 2)
        self.assertIn("no tier manifest", err)


class MergeTests(FixtureCase):
    def shards(self):
        data = self.manifest()
        paths = []
        for name, files in (("a", ["test_basic.py"]), ("b", ["test_gate.py", "test_old.py"])):
            part = dict(data, files={f: data["files"][f] for f in files})
            path = self.base / f"{name}.shard.json"
            path.write_text(json.dumps(part))
            paths.append(path)
        return data, paths

    def test_merge_writes_the_union_that_check_accepts(self):
        original, (a, b) = self.shards()
        (self.root / "test-tiers.json").unlink()
        code, out, err = run("merge", "--root", str(self.root), "--shard", str(a), "--shard", str(b))
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.manifest(), original)
        self.assertEqual(self.check()[0], 0)

    def test_merge_refuses_a_file_named_by_two_shards_and_writes_nothing(self):
        _, (a, b) = self.shards()
        (self.root / "test-tiers.json").unlink()
        run("merge", "--root", str(self.root), "--shard", str(a), "--shard", str(b))  # positive control wrote it
        (self.root / "test-tiers.json").unlink()
        c = self.base / "c.shard.json"
        data = json.loads(a.read_text())
        data["files"]["test_gate.py"] = json.loads(b.read_text())["files"]["test_gate.py"]
        c.write_text(json.dumps(data))
        code, out, _ = run("merge", "--root", str(self.root), "--shard", str(c), "--shard", str(b))
        self.assertEqual(code, 1)
        self.assertEqual([f["code"] for f in json.loads(out)["findings"]], ["doubly-labelled"])
        self.assertFalse((self.root / "test-tiers.json").exists())


class SchemaParityTests(unittest.TestCase):
    """The schema documents the reader: its keys, enums and required fields equal the reader's."""

    def setUp(self):
        self.schema = json.loads(SCHEMA.read_text())

    def test_top_level_keys_and_required_fields(self):
        self.assertEqual(tuple(self.schema["properties"]), test_tiers.TOP_KEYS)
        self.assertEqual(tuple(self.schema["required"]), test_tiers.TOP_KEYS)
        self.assertEqual(self.schema["properties"]["format"]["const"], test_tiers.FORMAT)
        self.assertEqual(self.schema["properties"]["version"]["const"], test_tiers.VERSION)
        self.assertEqual(tuple(self.schema["properties"]["kind"]["enum"]), test_tiers.KINDS)

    def test_entry_and_override_keys_and_tier_enum(self):
        defs = self.schema["$defs"]
        self.assertEqual(tuple(defs["fileEntry"]["properties"]), test_tiers.ENTRY_KEYS)
        self.assertEqual(tuple(defs["override"]["properties"]), test_tiers.OVERRIDE_KEYS)
        self.assertEqual(defs["fileEntry"]["required"], ["tier"])
        self.assertEqual(defs["override"]["required"], ["tier"])
        self.assertEqual(tuple(defs["tier"]["enum"]), test_tiers.TIERS)

    def test_the_fixture_manifest_has_exactly_the_documented_top_level_keys(self):
        data = json.loads((FIXTURE / "test-tiers.example.json").read_text())
        self.assertEqual(tuple(data), test_tiers.TOP_KEYS)


if __name__ == "__main__":
    unittest.main()
