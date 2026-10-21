"""Executable contracts for the standalone guide and its source projection."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from _dev_surface import TREE_AGENTS_MD, require_dev_surface

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))


def generator():
    spec = importlib.util.spec_from_file_location("micro_crux_generator", SCRIPTS / "generate-micro-crux.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def example(guide, name):
    match = re.search(r"<!-- BEGIN EXAMPLE: " + re.escape(name) + r" -->\n```[^\n]*\n(.*?)\n```\n<!-- END EXAMPLE: " + re.escape(name) + r" -->", guide, re.S)
    if not match:
        raise AssertionError(f"missing complete example {name}")
    return match.group(1)


class MicroCruxContractTests(unittest.TestCase):
    def setUp(self):
        self.gen = generator()
        self.plugin = ROOT / "crux"
        self.guide = self.gen.render(self.plugin)

    def test_render_is_deterministic_and_shipped_target_matches(self):
        self.assertEqual(self.guide, self.gen.render(self.plugin))
        self.assertEqual(self.guide, (self.plugin / "box/micro-crux.md").read_text())
        self.assertNotIn(str(ROOT), self.guide)

    def test_root_preview_matches_when_authoring_surface_exists(self):
        preview = ROOT / "micro-crux.md"
        require_dev_surface(self, preview, "root micro-crux.md preview")
        self.assertEqual(self.guide, preview.read_text())

    def test_embedded_schemas_match_and_resolve_offline(self):
        from council_records import _validator
        validator = _validator()
        for name in self.gen.SCHEMAS:
            with self.subTest(schema=name):
                schema = json.loads(example(self.guide, name))
                self.assertEqual(schema, json.loads((self.plugin / "schemas" / name).read_text()))
                self.gen.validate_refs(schema)
                if name == "adr-provenance.schema.json":
                    # Historical provenance owns a parser, not the promptbook engine's subset.
                    import adr_provenance as ap
                    self.assertEqual(set(schema["required"]), set(ap._TOP_KEYS))
                    self.assertEqual(set(schema["$defs"]["entry"]["properties"]), set(ap.ENTRY_FIELDS))
                    record = {
                        "schema": "1", "adr": "ADR-0001",
                        "run": {"book_id": "PB-0001", "run_id": "RUN-001",
                                "snapshot": "knowledge/promptbooks/runs/PB-0001-example/run-RUN-001.yaml"},
                        "base_commit": "a" * 40, "base_path": None, "base_sha256": None,
                        "rules": [{"handle": "ADR-0001/example-rule", "standing": "guidance",
                                   "entry": {"rule": "Illustrative historical rule."}, "base": None}],
                        "removed_in_run": [], "promotions": [],
                    }
                    self.assertEqual(record, ap.parse_record(ap.render_record(record), name="ADR-0001.yaml"))
                else:
                    # Current cycle/council writers use this bounded offline schema reader.
                    self.assertEqual(schema, validator.load_schema(self.plugin / "schemas" / name))

    def test_external_or_broken_schema_reference_is_refused(self):
        for reference in ("other.json", "https://invalid.example/schema", "#/$defs/missing"):
            with self.subTest(reference=reference), self.assertRaises(self.gen.GuideError):
                self.gen.validate_refs({"$ref": reference})

    def test_all_manifest_fields_in_canonical_local_schema_are_preserved(self):
        import yaml
        require_dev_surface(self, TREE_AGENTS_MD, "operational tree AGENTS.md")
        local = self.gen.section(TREE_AGENTS_MD.read_text(), "## 7.")
        expected = yaml.safe_load(re.search(r"```yaml\n(.*?)\n```", local, re.S).group(1))
        actual = yaml.safe_load(example(self.guide, "manifest-contract"))
        def keypaths(value, prefix=()):
            return {prefix + (key,) for key in value} | set().union(*(keypaths(child, prefix + (key,)) for key, child in value.items() if isinstance(child, dict)))
        self.assertEqual(keypaths(expected), keypaths(actual))

    def test_operational_fields_match_local_canonical_tables(self):
        require_dev_surface(self, TREE_AGENTS_MD, "operational tree AGENTS.md")
        local = TREE_AGENTS_MD.read_text()
        for heading in ("## 11.A.", "### 15.2", "### 17.1"):
            expected = self.gen.section(local, heading)
            rendered = self.gen.section(self.guide, self.gen.CONTRACTS[heading][0])
            fields = lambda text: re.findall(r"^\| `([^`]+)` \|", text, re.M)
            self.assertEqual(fields(expected), fields(rendered), heading)

    def test_initial_cycle_and_permitted_updates_use_canonical_semantics(self):
        from cycle_workflow import validate, replan, check_plan_file, updated_task, event
        from types import SimpleNamespace
        doc = json.loads(example(self.guide, "initial-cycle"))
        validate(doc)
        previous = deepcopy(doc["plan"])
        revised = deepcopy(previous)
        revised["tasks"][0]["description"] += " Preserve sorting."
        check_plan_file(revised)
        cfg = SimpleNamespace(repo_root=ROOT, docs_root=ROOT / "bionic")
        replan(cfg, previous, revised)
        revised["revision"] = previous["revision"] + 1
        event(doc, "plan-revised", previous=previous, reason="Clarify the expected behavior.")
        doc["plan"] = revised
        task = doc["plan"]["tasks"][0]
        task.update(updated_task(cfg, doc, task, {"state": "active", "assignee": "implementer"}))
        event(doc, "task-updated", task=task["id"], state="active", assignee="implementer")
        validate(doc)
        self.assertEqual(previous, doc["history"][-2]["previous"])
        with self.assertRaises(ValueError):
            updated_task(cfg, doc, doc["plan"]["tasks"][1], {"state": "done"})
        malformed = deepcopy(doc)
        malformed["plan"]["tasks"][0]["depends_on"] = ["missing"]
        with self.assertRaises(ValueError):
            validate(malformed)

    def test_proposed_adr_and_sidecar_match_canonical_writer(self):
        import yaml
        from decision_policy import propose, frontmatter
        body = example(self.guide, "proposed-adr") + "\n"
        fm = yaml.safe_load(body.split("---", 2)[1])
        sidecar = json.loads(example(self.guide, "adr-proposal-metadata"))
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: knowledge\n')
            docs = repo / "knowledge"
            docs.mkdir()
            (docs / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 1\n')
            outcome = propose(repo, {**fm, "body": body.split("---", 2)[2]}, origin="direct")
            actual = json.loads((docs / "adrs/proposals/ADR-0001.json").read_text())
            self.assertEqual(sidecar, actual)
            rendered_fm, _ = frontmatter((docs / outcome["path"]).read_text())
            # The proposal date belongs to the real invocation; the example is illustrative.
            for key in fm.keys() - {"date", "proposed_date"}:
                self.assertEqual(fm[key], rendered_fm[key], key)
            self.assertEqual(2, yaml.safe_load((docs / "manifest.yml").read_text())["adr"]["next_number"])


class MicroCruxGenerationTests(unittest.TestCase):
    def setUp(self):
        self.gen = generator()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        for path in self.gen.input_paths(ROOT / "crux"):
            target = self.repo / "crux" / path.relative_to(ROOT / "crux")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        shutil.copyfile(SCRIPTS / "authoring_scope.py", self.repo / "crux/scripts/authoring_scope.py")

    def command(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPTS / "generate-micro-crux.py"), "--repo-root", str(self.repo), *args], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_staged_generation_dry_run_and_independent_drifts(self):
        code, payload = self.command()
        self.assertEqual(0, code, payload)
        self.assertFalse((self.repo / "micro-crux.md").exists())
        code, payload = self.command("--dry-run")
        self.assertEqual((0, False), (code, payload["drift"]))
        output = self.repo / "crux/box/micro-crux.md"
        output.write_text(output.read_text() + "local edit\n")
        code, payload = self.command("--dry-run")
        self.assertEqual(1, code, payload)
        self.assertTrue(payload["drift"])
        self.command()
        schema = self.repo / "crux/schemas/cycle.schema.json"
        data = json.loads(schema.read_text())
        data["description"] = "A changed upstream contract."
        schema.write_text(json.dumps(data))
        code, payload = self.command("--dry-run")
        self.assertEqual(1, code, payload)
        self.assertTrue(payload["drift"])

    def test_a_plugin_version_bump_does_not_drift_the_guide(self):
        """The guide carries no plugin version, so a release's version bump leaves it unchanged."""
        code, payload = self.command()
        self.assertEqual(0, code, payload)
        guide = (self.repo / "crux/box/micro-crux.md").read_text()
        self.assertNotIn("plugin_version", guide)
        manifest = self.repo / "crux/plugin.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads((ROOT / "crux/plugin.json").read_text())
        data["version"] = "99.0.0"
        manifest.write_text(json.dumps(data))
        code, payload = self.command("--dry-run")
        self.assertEqual((0, False), (code, payload["drift"]), payload)

    def test_consumer_reports_surface_absent_without_writes(self):
        consumer = self.repo / "consumer"
        consumer.mkdir()
        result = subprocess.run([sys.executable, str(SCRIPTS / "generate-micro-crux.py"), "--repo-root", str(consumer), "--dry-run"], capture_output=True, text=True)
        self.assertEqual(0, result.returncode)
        self.assertTrue(json.loads(result.stdout)["surface_absent"])
        self.assertEqual([], list(consumer.iterdir()))

    def test_missing_input_does_not_replace_existing_output(self):
        self.command()
        target = self.repo / "crux/box/micro-crux.md"
        before = target.read_bytes()
        (self.repo / "crux/schemas/cycle.schema.json").unlink()
        code, payload = self.command()
        self.assertEqual(1, code, payload)
        self.assertEqual(before, target.read_bytes())


if __name__ == "__main__":
    unittest.main()
