"""PB-0150 postcondition: the rule citations this cycle touches resolve, the promotion path builds.

rule:guidance-rules-keep-resolving, rule:provenance-is-recorded-at-acceptance,
rule:accepting-cycle-requests-promotion.

  - LiveCitationTests: the twelve rule slugs of ADR-0150's in-run rules and ADR-0151's rules resolve in
    the live resolver and appear in the live doctrine index; each row's standing matches the live
    provenance record (branching on the record, so the test holds after the owner promotes).
  - PromotionPathTests: ADR-0150's record, from the CLI dry-run, is added IN PROCESS to the loaded
    projection inputs (nothing is written to the live tree) and both plans build with the expected
    standing. Controls: the same plan without the record carries no ADR-0150 standing; a record whose
    handle no live row carries is refused.
  - AcceptHookTests: the ADR module's accept step passes `--run` to `transition-adr` in both templates
    (shipped surface, so no dev-surface guard).
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
try:
    from ._dev_surface import REPO_ROOT, TREE, require_dev_surface
except ImportError:
    from _dev_surface import REPO_ROOT, TREE, require_dev_surface

sys.path.insert(0, str(SCRIPTS_DIR))
import adr_provenance as ap  # noqa: E402
import summaries_projection as sp  # noqa: E402

ADRS = REPO_ROOT / TREE / "adrs"
RESOLVER = ADRS / "summaries" / "resolver.json"
DOCTRINE = ADRS / "doctrine" / "index.md"
SNAPSHOT = (f"{TREE}/promptbooks/runs/PB-0149-ship-the-crux-mods-plugin-with-a-run-dashboard/"
            "run-RUN-001.yaml")
ACCEPTING_RUN_BASE = "21ef406e225969f97c21b4a6be98bf61ca21d2d3"
SIX_0150 = ["mods-gate-refuses-what-it-cannot-check", "mods-start-only-the-fixed-launcher",
            "launch-values-have-fixed-sources", "reader-json-mode-is-contained",
            "enforcing-entries-name-their-counterpart", "mods-add-no-harness-specific-stop"]
SIX_0151 = ["in-run-adr-text-is-guidance", "guidance-rules-keep-resolving",
            "guidance-changes-without-a-decision", "provenance-is-recorded-at-acceptance",
            "owner-promotes-guidance", "accepting-cycle-requests-promotion"]
SLUGS = SIX_0150 + SIX_0151


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _slug_rows(resolver: dict, slugs: list[str]) -> dict[str, dict]:
    """slug -> resolver row, resolving each slug through `slugs`; raises KeyError on a miss."""
    return {s: resolver[resolver["slugs"][s]] for s in slugs}


def _live_record(adr: str):
    path = ADRS / ap.DIRNAME / f"{adr}.yaml"
    return ap.parse_record(path.read_text(encoding="utf-8"), name=path.name) if path.is_file() else None


def _promoted(record) -> set[str]:
    return {h for p in record["promotions"] for h in p["handles"]}


def _check_standing(tc: unittest.TestCase, rows: dict[str, dict], adr: str, slugs: list[str],
                    record) -> None:
    promoted = _promoted(record) if record else set()
    for slug in slugs:
        row = rows[slug]
        if record is None:
            tc.assertNotIn("standing", row, slug)
        elif f"{adr}/{slug}" in promoted:
            tc.assertEqual(row["standing"], "binding", slug)
            tc.assertEqual(row["binding_rule"], row["rule"], slug)
        else:
            tc.assertEqual(row["standing"], "guidance", slug)
            tc.assertIsNone(row["binding_rule"], slug)
            tc.assertEqual(row["in_run_edit"], ["added"], slug)


class LiveCitationTests(unittest.TestCase):
    def setUp(self):
        require_dev_surface(self, RESOLVER, "summaries resolver")
        require_dev_surface(self, DOCTRINE, "doctrine index")
        self.resolver = json.loads(RESOLVER.read_text(encoding="utf-8"))
        self.doctrine = DOCTRINE.read_text(encoding="utf-8")

    def test_twelve_slugs_resolve_and_appear_in_the_doctrine(self):
        rows = _slug_rows(self.resolver, SLUGS)
        self.assertEqual(len(rows), 12)
        for slug in SLUGS:
            handle = self.resolver["slugs"][slug]
            self.assertTrue(handle.endswith("/" + slug), handle)
            self.assertIn(f"| {handle} |", self.doctrine, handle)

    def test_the_resolution_check_fails_when_a_slug_is_missing(self):
        broken = copy.deepcopy(self.resolver)
        del broken["slugs"][SLUGS[0]]
        with self.assertRaises(KeyError):
            _slug_rows(broken, SLUGS)                       # the observed failure of the check
        dangling = copy.deepcopy(self.resolver)
        del dangling[dangling["slugs"][SLUGS[1]]]
        with self.assertRaises(KeyError):
            _slug_rows(dangling, SLUGS)

    def test_adr_0151_rows_follow_its_live_record(self):
        record = _live_record("ADR-0151")
        self.assertIsNotNone(record, "ADR-0151 must carry a provenance record")
        _check_standing(self, _slug_rows(self.resolver, SIX_0151), "ADR-0151", SIX_0151, record)

    def test_adr_0150_rows_follow_its_live_record_or_carry_no_standing(self):
        _check_standing(self, _slug_rows(self.resolver, SIX_0150), "ADR-0150", SIX_0150,
                        _live_record("ADR-0150"))

    def test_standing_check_rejects_a_wrong_row(self):
        rows = _slug_rows(self.resolver, SIX_0151)
        record = _live_record("ADR-0151")
        wrong = copy.deepcopy(rows)
        wrong[SIX_0151[0]]["standing"] = "binding"
        if f"ADR-0151/{SIX_0151[0]}" not in _promoted(record):
            with self.assertRaises(AssertionError):
                _check_standing(self, wrong, "ADR-0151", SIX_0151, record)
        # control: a record-less reading of rows that carry standing must fail too
        with self.assertRaises(AssertionError):
            _check_standing(self, rows, "ADR-0151", SIX_0151, None)


    def test_standing_check_runs_its_promoted_branch(self):
        record = _live_record("ADR-0151")
        if record is None:
            self.skipTest("no ADR-0151 provenance record on this surface")
        handle = f"ADR-0151/{SIX_0151[0]}"
        promoted = copy.deepcopy(record)
        promoted["promotions"].append({"date": "2026-09-01", "instruction": "Promote it.",
                                       "handles": [handle], "body": False})
        self.assertIn(handle, _promoted(promoted))
        rows = copy.deepcopy(_slug_rows(self.resolver, SIX_0151))
        rows[SIX_0151[0]].update({"standing": "binding", "binding_rule": rows[SIX_0151[0]]["rule"]})
        _check_standing(self, rows, "ADR-0151", SIX_0151, promoted)     # passes through the branch
        # control: the record says promoted while the row still reads guidance (built here, because
        # the live row reads binding once the owner has promoted the rule)
        unpromoted = copy.deepcopy(rows)
        unpromoted[SIX_0151[0]].update({"standing": "guidance", "binding_rule": None})
        with self.assertRaises(AssertionError):
            _check_standing(self, unpromoted, "ADR-0151", SIX_0151, promoted)


class PromotionPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (REPO_ROOT / SNAPSHOT).is_file():
            raise unittest.SkipTest("PB-0149 run snapshot absent (dev-only surface)")
        if not (REPO_ROOT / ".git").is_dir():
            # Run snapshots name artifacts under `.git/crux/results/`; in a linked worktree `.git`
            # is a file, so the live-tree projection refuses (retained-evidence-layout-refused).
            raise unittest.SkipTest("the live-tree projection needs a primary checkout (.git directory)")
        probe = subprocess.run(["git", "-C", str(REPO_ROOT), "cat-file", "-e",
                                f"{ACCEPTING_RUN_BASE}^{{commit}}"], capture_output=True)
        if probe.returncode != 0:
            raise unittest.SkipTest("the run's base_commit is not in this clone")
        cli = subprocess.run([sys.executable, str(SCRIPTS_DIR / "adr-provenance.py"), "record",
                              "--adr", "ADR-0150", "--run", SNAPSHOT, "--dry-run",
                              "--repo-root", str(REPO_ROOT)], capture_output=True, text=True, check=False)
        if cli.returncode != 0:
            raise AssertionError(cli.stderr)
        cls.record = json.loads(cli.stdout)
        cls.record_text = ap.render_record(cls.record)
        cls.sa = _load("sa_pb0150", "summarize-adrs.py")
        cls.dp = _load("dp_pb0150", "doctrine_projection.py")
        manifest = sp.read_manifest(REPO_ROOT)
        import implementation_migration as migration
        with migration.read_scope():
            cls.summ = cls.sa._load_summary_inputs(REPO_ROOT, manifest)
            cls.doct = cls.dp._load_doctrine_inputs(REPO_ROOT, manifest)

    @staticmethod
    def _with_record(inputs, record_text: str, digest_key: str = "metadata"):
        loaded, view, pending, actual = copy.deepcopy(inputs)
        entries = [e for e in sp.provenance_entries(ADRS) if e[0] != "ADR-0150.yaml"]
        entries.append(("ADR-0150.yaml", record_text.encode("utf-8")))
        loaded["provenance"] = ap.parse_records(entries)
        target = loaded[digest_key]
        target["provenance_sha256"] = ap.records_sha256(entries)
        if "provenance" not in target["input_domain"]:
            target["input_domain"] = list(target["input_domain"]) + ["provenance"]
        return loaded, view, pending, actual

    def _summary_resolver(self, inputs) -> dict:
        loaded, view, pending, actual = inputs
        plan = sp._plan_summary_outputs(loaded, view, pending)
        proven = sp._committed_publication_ref(pending, actual) if pending is not None else None
        out = sp._materialize_summary_outputs(plan, proven)
        return json.loads(out[loaded["paths"]["resolver.json"]].decode("utf-8"))

    def _doctrine_index(self, inputs) -> str:
        loaded, view, pending, actual = inputs
        plan = self.dp._plan_doctrine_outputs(loaded, view, pending)
        proven = sp._committed_publication_ref(pending, actual) if pending is not None else None
        out = self.dp._materialize_doctrine_outputs(plan, proven)
        return out[loaded["paths"]["index.md"]].decode("utf-8")

    def test_the_record_makes_six_guidance_and_twelve_binding_rows(self):
        resolver = self._summary_resolver(self._with_record(self.summ, self.record_text))
        rows = _slug_rows(resolver, SIX_0150)
        for slug, row in rows.items():
            self.assertEqual(row["standing"], "guidance", slug)
            self.assertIsNone(row["binding_rule"], slug)
            self.assertEqual(row["in_run_edit"], ["added"], slug)
        binding = [r for h, r in resolver.items()
                   if h.startswith("ADR-0150/") and r.get("standing") == "binding"]
        self.assertEqual(len(binding), 12)
        self.assertTrue(all(r["binding_rule"] for r in binding))
        edited = [h for h, r in resolver.items() if h.startswith("ADR-0150/")
                  and r.get("standing") == "binding" and r["in_run_edit"]]
        self.assertEqual(len(edited), 10)
        self.assertEqual(resolver["ADR-0150/mods-plugin-is-versioned-and-released-with-crux"]["in_run_edit"],
                         ["scope"])

    def test_control_without_the_record_adr_0150_rows_carry_no_standing(self):
        if _live_record("ADR-0150") is not None:
            self.skipTest("ADR-0150's record is promoted into the live tree")
        resolver = self._summary_resolver(self.summ)
        rows = [r for h, r in resolver.items() if h.startswith("ADR-0150/")]
        self.assertGreaterEqual(len(rows), 18)
        self.assertTrue(all("standing" not in r for r in rows))

    def test_a_record_naming_a_handle_with_no_live_row_is_refused(self):
        bad = copy.deepcopy(self.record)
        bad["rules"][0]["handle"] = "ADR-0150/no-such-rule-exists"
        with self.assertRaises(sp.GovernsValidationError):
            self._summary_resolver(self._with_record(self.summ, ap.render_record(bad)))

    def test_doctrine_index_holds_a_standing_row_for_each_guidance_handle(self):
        index = self._doctrine_index(self._with_record(self.doct, self.record_text, digest_key="digests"))
        self.assertIn("_Standing (from provenance records):_", index)
        for slug in SIX_0150:
            self.assertRegex(index, rf"\| ADR-0150/{re.escape(slug)} \| guidance \| — \| added \|")
        self.assertRegex(index, r"\| ADR-0150/mods-plugin-is-versioned-and-released-with-crux "
                                r"\| binding \|[^\n]*\| scope \|")

    def test_control_doctrine_without_the_record_has_no_adr_0150_standing_row(self):
        if _live_record("ADR-0150") is not None:
            self.skipTest("ADR-0150's record is promoted into the live tree")
        index = self._doctrine_index(self.doct)
        self.assertGreater(index.count("| ADR-0150/"), 0)
        self.assertNotRegex(index, r"\| ADR-0150/[a-z-]+ \| (guidance|binding) \|")


class AcceptHookTests(unittest.TestCase):
    """The accept step passes `--run`, so acceptance inside a run writes the provenance record."""
    TEMPLATES = SCRIPTS_DIR.parent / "templates"
    PIN = re.compile(r"accept ADR-NNNN --run <run-RUN-NNN\.yaml>")

    @staticmethod
    def _prompts(path: Path) -> list[dict]:
        import yaml
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        return doc["prompts"] if isinstance(doc, dict) else doc

    def _accept_text(self, path: Path) -> str:
        found = [re.sub(r"\s+", " ", p["prompt"]) for p in self._prompts(path)
                 if "invoke `transition-adr`" in re.sub(r"\s+", " ", p["prompt"])]
        self.assertEqual(len(found), 1, f"{path.name}: expected one accept step")
        return found[0]

    def test_both_templates_pass_run_to_transition_adr(self):
        for name in ("cycle-promptbook-template.yaml", "cycle-module-adr.yaml"):
            self.assertRegex(self._accept_text(self.TEMPLATES / name), self.PIN, name)

    def test_pin_fails_when_run_is_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = (self.TEMPLATES / "cycle-module-adr.yaml").read_text(encoding="utf-8")
            self.assertIn("--run <run-RUN-NNN.yaml>", src)      # positive control: the text is there
            copy_path = Path(tmp) / "cycle-module-adr.yaml"
            copy_path.write_text(src.replace(" --run <run-RUN-NNN.yaml>", ""), encoding="utf-8")
            self.assertNotRegex(self._accept_text(copy_path), self.PIN)


if __name__ == "__main__":
    unittest.main()
