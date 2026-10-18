"""The summaries and doctrine projections read each rule's standing from provenance records.

rule:provenance-is-recorded-at-acceptance, rule:guidance-rules-keep-resolving.

Pins, one named test per claim:

  - A  no record: both projections are byte-identical to the tree with no provenance directory,
       and `provenance` is absent from both `_meta.json` files. Control: with a record the bytes
       differ and the member and its digest are present.
  - B  a record with a guidance rule, a binding rule and a binding rule edited in-run adds the
       rule-table section, the resolver keys and the doctrine sub-table, and moves no
       disposition, authority, review state, basis, domain state or row.
  - C  a promotion appended to the record drifts both regenerators (exit 1) before regeneration,
       and the standing flips to binding at the accepted wording after it.
  - D  a handle the record does not name, and wording that moved since acceptance, are
       validation errors (exit 1, nothing written), each paired with the passing fixture.
  - E  a malformed record and a stray file in the directory are validation errors.
  - F  a declared `provenance` member with a symlinked directory refuses (exit 2, nothing
       written); an undeclared symlink refuses too; the real directory passes.
  - G  the rules catalog publishes a guidance rule with the keys a binding rule gets and no
       `standing` key, and a `rule:<slug>` citation of a guidance rule resolves in
       lint-governs-references as a binding rule's does.

Every fixture is a throwaway tree built here; no test reads the live documentation tree, so the
file runs unchanged in the staged crux-only artifact. Needs PyYAML (the uv lane).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:  # pragma: no cover
    HAVE_YAML = False


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if HAVE_YAML:
    import adr_provenance as ap  # noqa: E402
    import summaries_projection as sp  # noqa: E402
    SA = _load("summarize_adrs_provenance", "summarize-adrs.py")
    CD = _load("compile_doctrine_provenance", "compile-doctrine.py")
    LINT = _load("lint_governs_provenance", "lint-governs-references.py")

BASE = "0123456789abcdef0123456789abcdef01234567"
GUIDANCE, BINDING, EDITED = "ADR-0901/added-in-run", "ADR-0901/stood-unchanged", "ADR-0901/stood-edited"
OTHER = "ADR-0902/no-record"
RULES = {
    GUIDANCE: "Added during the run.",
    BINDING: "Stood at base.",
    EDITED: "Edited in the run.",
}
REGENERATOR = SCRIPTS_DIR / "generate-rules-catalog.py"


def _adr(num: int, rules: dict[str, str], domain: str) -> str:
    lines = ["---", f"id: ADR-{num:04d}", f'title: "Decision {num}"', "status: Accepted",
             "date: 2026-08-01", "proposed_date: 2026-08-01", "accepted_date: 2026-08-01",
             "supersedes: []", "superseded_by: null", "tags: [test]", "governs:"]
    for handle, rule in rules.items():
        lines += [f"  - handle: {handle}", f"    domain: {domain}", f'    rule: "{rule}"',
                  "    scope: crux/scripts", "    provenance: authored"]
    lines += ["---", "", f"# ADR-{num:04d}", "", "Body.", ""]
    return "\n".join(lines)


def _entry(rule: str, domain: str = "alpha", **fields) -> dict:
    """A recorded governs entry as `_adr` writes it, without its handle."""
    return {"domain": domain, "rule": rule, "scope": "crux/scripts", "provenance": "authored", **fields}


def _record(promotions: list[dict] | None = None, rules: dict[str, str] | None = None) -> dict:
    rules = RULES if rules is None else rules
    stood = {GUIDANCE: ("guidance", None), BINDING: ("binding", "Stood at base."),
             EDITED: ("binding", "As it stood at base.")}
    return {
        "schema": "1", "adr": "ADR-0901",
        "run": {"book_id": "PB-0900", "run_id": "RUN-001",
                "snapshot": "bionic/promptbooks/runs/PB-0900-x/run-RUN-001.yaml"},
        "base_commit": BASE, "base_path": "bionic/adrs/ADR-0901-x.md", "base_sha256": "a" * 64,
        "rules": [{"handle": h, "standing": stood[h][0], "entry": _entry(w),
                   "base": _entry(stood[h][1]) if stood[h][1] is not None else None}
                  for h, w in rules.items()],
        "removed_in_run": [], "promotions": promotions or [],
    }


PROMOTION = {"date": "2026-09-01", "instruction": "Promote the added rule and the edit.",
             "handles": [GUIDANCE, EDITED], "body": False}


class Tree:
    """A throwaway repository: one tree, two ADRs (ADR-0901 may carry a record; ADR-0902 never does)."""

    def __init__(self, root: Path):
        self.root = root
        (root / ".bionic.yml").write_text("docs_dir: bionic\n", encoding="utf-8")
        tree = root / "bionic"
        self.adrs = tree / "adrs"
        self.adrs.mkdir(parents=True)
        (tree / "invariants").mkdir()
        (tree / "promptbooks" / "runs").mkdir(parents=True)
        (tree / "manifest.yml").write_text(
            'schema_version: "5"\nconcerns_enabled:\n  - adrs\n  - invariants\n'
            "adr:\n  next_number: 1000\n  governs_from: 1\n", encoding="utf-8")
        self.provenance = self.adrs / "provenance"
        self.summaries = self.adrs / "summaries"
        self.doctrine = self.adrs / "doctrine"
        self.write_adrs(RULES)
        # The authoring-checkout probe `generate-rules-catalog.py` asks for, and a shipped surface.
        probe = root / "crux" / "scripts" / REGENERATOR.name
        probe.parent.mkdir(parents=True)
        probe.write_text("# authoring-checkout probe (test fixture)\n", encoding="utf-8")
        (root / "crux" / "skills" / "fixture").mkdir(parents=True)
        (root / "pages").mkdir()

    def write_adrs(self, rules: dict[str, str]):
        (self.adrs / "ADR-0901-x.md").write_text(_adr(901, rules, "alpha"), encoding="utf-8")
        (self.adrs / "ADR-0902-x.md").write_text(_adr(902, {OTHER: "Holds no record."}, "beta"),
                                                  encoding="utf-8")

    def write_record(self, record: dict | None = None) -> Path:
        self.provenance.mkdir(exist_ok=True)
        path = self.provenance / "ADR-0901.yaml"
        path.write_text(ap.render_record(record or _record()), encoding="utf-8")
        return path

    def run(self, module, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = module.main(["--repo-root", str(self.root), *args])
        return rc, out.getvalue(), err.getvalue()

    def regenerate(self):
        for module in (SA, CD):
            rc, out, err = self.run(module)
            assert rc == 0, (module.__name__, rc, out, err)

    def summaries_files(self) -> dict[str, str]:
        return {p.name: p.read_text(encoding="utf-8") for p in sorted(self.summaries.glob("*"))}

    def doctrine_files(self) -> dict[str, str]:
        return {p.name: p.read_text(encoding="utf-8") for p in sorted(self.doctrine.glob("*"))}

    def built(self) -> tuple[dict[str, str], dict[str, str]]:
        """Both projections as the regenerators would write them, without writing."""
        return ({p.name: b for p, b in SA.build(self.root).items()},
                {p.name: b for p, b in CD.build(self.root).items()})


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.t = Tree(Path(self._tmp.name))


def _standing_rows(table: str) -> list[list[str]]:
    section = table.split("## Rule standing", 1)[1]
    return [[c.strip() for c in line.strip("|").split("|")]
            for line in section.splitlines() if line.startswith("| ADR-")]


def _doctrine_rule_rows(index: str) -> list[str]:
    """The rules-table rows (7 columns); the standing sub-table rows have 4."""
    return [line for line in index.splitlines() if line.startswith("| ADR-") and line.count("|") == 8]


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class NoRecordIsByteIdenticalTests(_Base):
    def test_no_record_changes_no_byte_and_names_no_member(self):
        base_summaries, base_doctrine = self.t.built()
        self.t.provenance.mkdir()           # an empty directory is still no record
        empty_summaries, empty_doctrine = self.t.built()
        self.assertEqual(empty_summaries, base_summaries)
        self.assertEqual(empty_doctrine, base_doctrine)
        for meta in (json.loads(base_summaries["_meta.json"]), json.loads(base_doctrine["_meta.json"])):
            self.assertNotIn("provenance", meta["input_domain"])
            self.assertNotIn("provenance_sha256", meta)
        self.assertNotIn("Rule standing", base_summaries["rule-table.md"])
        self.assertNotIn("Standing (from provenance", base_doctrine["index.md"])
        # the schema numbers do not move
        self.assertEqual(json.loads(base_summaries["_meta.json"])["schema"], "7")
        self.assertEqual(json.loads(base_doctrine["_meta.json"])["schema"], "6")

    def test_control_a_record_moves_bytes_and_declares_the_member(self):
        base_summaries, base_doctrine = self.t.built()
        self.t.write_record()
        with_summaries, with_doctrine = self.t.built()
        self.assertNotEqual(with_summaries["rule-table.md"], base_summaries["rule-table.md"])
        self.assertNotEqual(with_doctrine["index.md"], base_doctrine["index.md"])
        for files in (with_summaries, with_doctrine):
            meta = json.loads(files["_meta.json"])
            self.assertIn("provenance", meta["input_domain"])
            self.assertRegex(meta["provenance_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(meta["schema"], "7" if files is with_summaries else "6")


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class StandingRenderingTests(_Base):
    def test_summaries_section_resolver_and_doctrine_sub_table(self):
        base_summaries, base_doctrine = self.t.built()
        self.t.write_record()
        summaries, doctrine = self.t.built()

        table = summaries["rule-table.md"]
        self.assertTrue(table.startswith(base_summaries["rule-table.md"].rstrip("\n")),
                        "every row the no-record table had stays, in order")
        self.assertEqual(table.count("## Rule standing"), 1)
        self.assertEqual(_standing_rows(table), [
            [GUIDANCE, "guidance", "—", "added"],
            [EDITED, "binding", "As it stood at base.", "rule"],
            [BINDING, "binding", "Stood at base.", "—"],
        ])
        self.assertNotIn(OTHER, table.split("## Rule standing", 1)[1])

        resolver, base_resolver = json.loads(summaries["resolver.json"]), json.loads(base_summaries["resolver.json"])
        self.assertEqual(set(resolver), set(base_resolver), "a guidance rule stays in the resolver")
        self.assertEqual((resolver[GUIDANCE]["standing"], resolver[GUIDANCE]["binding_rule"]), ("guidance", None))
        self.assertEqual((resolver[EDITED]["standing"], resolver[EDITED]["binding_rule"]),
                         ("binding", "As it stood at base."))
        self.assertEqual((resolver[BINDING]["standing"], resolver[BINDING]["binding_rule"]),
                         ("binding", "Stood at base."))
        self.assertNotIn("standing", resolver[OTHER])
        self.assertNotIn("binding_rule", resolver[OTHER])
        for handle, row in resolver.items():
            if handle in RULES:
                row = {k: v for k, v in row.items() if k not in ("standing", "binding_rule", "in_run_edit")}
            self.assertEqual(row, base_resolver[handle], handle)    # disposition, authority, review_state, rule

        index = doctrine["index.md"]
        self.assertEqual(index.count("_Standing (from provenance records):_"), 1)
        sub = index.split("_Standing (from provenance records):_", 1)[1]
        self.assertIn(f"| {GUIDANCE} | guidance | — | added |", sub)
        self.assertIn(f"| {EDITED} | binding | As it stood at base. | rule |", sub)
        self.assertIn(f"| {BINDING} | binding | Stood at base. | — |", sub)
        self.assertEqual(_doctrine_rule_rows(index), _doctrine_rule_rows(base_doctrine["index.md"]),
                         "the rules table keeps its rows and columns")
        headings = lambda text: [l for l in text.splitlines() if l.startswith("## ")]
        self.assertEqual(headings(index), headings(base_doctrine["index.md"]), "domain states do not move")
        self.assertIn(f"| {GUIDANCE} |", index.split("## beta")[0], "the guidance rule stays live in doctrine")

    def test_doctrine_sub_table_sits_in_its_domain_before_the_evidence_slot(self):
        self.t.write_record()
        _, doctrine = self.t.built()
        alpha = doctrine["index.md"].split("## alpha", 1)[1].split("## beta", 1)[0]
        beta = doctrine["index.md"].split("## beta", 1)[1].split("## Exempt", 1)[0]
        self.assertIn("_Standing (from provenance records):_", alpha)
        self.assertNotIn("_Standing (from provenance records):_", beta)   # control: beta has no record
        self.assertLess(alpha.index("| handle | citation |"), alpha.index("_Standing (from provenance"))


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class PromotionDriftTests(_Base):
    def test_a_promotion_drifts_both_projections_and_flips_the_standing(self):
        self.t.write_record()
        self.t.regenerate()
        for module in (SA, CD):
            self.assertEqual(self.t.run(module, "--dry-run")[0], 0, "clean after regeneration")

        self.t.write_record(_record([PROMOTION]))
        rc, out, _ = self.t.run(SA, "--dry-run")
        self.assertEqual((rc, json.loads(out)["drift"]), (1, True))
        rc, out, _ = self.t.run(CD, "--dry-run")
        self.assertEqual((rc, json.loads(out)["drift"]), (1, True))

        self.t.regenerate()
        rows = {r[0]: r for r in _standing_rows(self.t.summaries_files()["rule-table.md"])}
        self.assertEqual(rows[GUIDANCE][1:], ["binding", "Added during the run.", "—"])
        self.assertEqual(rows[EDITED][1:], ["binding", "Edited in the run.", "—"])
        resolver = json.loads(self.t.summaries_files()["resolver.json"])
        self.assertEqual(resolver[GUIDANCE]["binding_rule"], RULES[GUIDANCE])
        self.assertIn(f"| {GUIDANCE} | binding | Added during the run. | — |", self.t.doctrine_files()["index.md"])
        for module in (SA, CD):
            self.assertEqual(self.t.run(module, "--dry-run")[0], 0)


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class JoinRefusalTests(_Base):
    def _assert_validation_error(self, needle: str):
        for module in (SA, CD):
            for args in (("--dry-run",), ()):
                rc, out, err = self.t.run(module, *args)
                self.assertEqual(rc, 1, (module.__name__, args, err))
                problems = json.loads(out)["validation_errors"]
                self.assertTrue(any(needle in p["problem"] for p in problems), problems)
        self.assertFalse(self.t.summaries.exists(), "nothing written")
        self.assertFalse(self.t.doctrine.exists(), "nothing written")

    def test_a_live_handle_the_record_does_not_name_refuses(self):
        self.t.write_record(_record(rules={k: v for k, v in RULES.items() if k != BINDING}))
        self._assert_validation_error("governs handle has no rule in its ADR's provenance record")

    def test_wording_that_moved_since_acceptance_refuses(self):
        self.t.write_record()
        self.t.write_adrs({**RULES, BINDING: "Stood at base, then edited."})
        self._assert_validation_error("differs from the entry its provenance record captured at acceptance (fields: rule)")

    def test_a_scope_that_moved_since_acceptance_refuses(self):
        record = _record()
        record["rules"][1]["entry"]["scope"] = "crux/scripts, tools/"
        record["rules"][1]["base"]["scope"] = "crux/scripts, tools/"
        self.t.write_record(record)
        self._assert_validation_error("(fields: scope)")

    def test_control_the_matching_fixture_builds(self):
        self.t.write_record()
        self.t.regenerate()
        self.assertTrue(self.t.summaries.exists() and self.t.doctrine.exists())


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class MalformedRecordTests(_Base):
    def _assert_refused(self):
        for module in (SA, CD):
            rc, out, err = self.t.run(module, "--dry-run")
            self.assertEqual(rc, 1, (module.__name__, err))
            self.assertTrue(json.loads(out)["validation_errors"])
        self.assertFalse(self.t.summaries.exists())

    def test_a_record_missing_its_keys_is_a_validation_error(self):
        self.t.provenance.mkdir()
        (self.t.provenance / "ADR-0901.yaml").write_text("schema: '1'\nadr: ADR-0901\n", encoding="utf-8")
        self._assert_refused()

    def test_a_stray_file_in_the_directory_is_a_validation_error(self):
        self.t.write_record()
        (self.t.provenance / "notes.txt").write_text("stray\n", encoding="utf-8")
        self._assert_refused()

    def test_control_dotfiles_are_skipped(self):
        self.t.write_record()
        (self.t.provenance / ".keep").write_text("", encoding="utf-8")
        self.assertEqual(self.t.run(SA, "--dry-run")[0], 1, "drift only: nothing written yet")
        self.t.regenerate()


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class UnreadableDirectoryTests(_Base):
    def _swap_for_symlink(self):
        real = self.t.adrs / "provenance-real"
        self.t.provenance.rename(real)
        self.t.provenance.symlink_to(real, target_is_directory=True)

    def _snapshot(self):
        return self.t.summaries_files(), self.t.doctrine_files()

    def test_a_declared_member_with_a_symlinked_directory_refuses_and_writes_nothing(self):
        self.t.write_record()
        self.t.regenerate()
        self.assertIn("provenance", json.loads(self.t.summaries_files()["_meta.json"])["input_domain"])
        before = self._snapshot()
        self._swap_for_symlink()
        for args in (("--dry-run",), ()):
            rc, out, err = self.t.run(SA, *args)
            self.assertEqual(rc, 2, (args, out))
            self.assertIn("declares `provenance` in its input_domain", err)
            rc, out, err = self.t.run(CD, *args)
            self.assertEqual(rc, 2, (args, out))
            self.assertIn("provenance", err)
        self.assertEqual(self._snapshot(), before, "nothing written")

    def test_an_undeclared_symlinked_directory_refuses_too(self):
        self.t.write_record()
        self._swap_for_symlink()
        for module in (SA, CD):
            rc, _, err = self.t.run(module, "--dry-run")
            self.assertEqual(rc, 2, err)
            self.assertIn("symlink", err)
        self.assertFalse(self.t.summaries.exists())

    def test_control_the_real_directory_passes_the_declared_member(self):
        self.t.write_record()
        self.t.regenerate()
        for module in (SA, CD):
            self.assertEqual(self.t.run(module, "--dry-run")[0], 0)

    def test_zero_records_drops_a_declared_member_on_rebuild(self):
        self.t.write_record()
        self.t.regenerate()
        (self.t.provenance / "ADR-0901.yaml").unlink()
        for module in (SA, CD):
            rc, out, _ = self.t.run(module, "--dry-run")
            self.assertEqual((rc, json.loads(out)["drift"]), (1, True))
        self.t.regenerate()
        self.assertNotIn("provenance", json.loads(self.t.summaries_files()["_meta.json"])["input_domain"])
        self.assertNotIn("provenance", json.loads(self.t.doctrine_files()["_meta.json"])["input_domain"])


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class GuidanceRulesKeepResolvingTests(_Base):
    def _catalog_run(self) -> tuple[subprocess.CompletedProcess, dict]:
        (self.t.root / "crux" / "skills" / "fixture" / "SKILL.md").write_text(
            "This surface cites rule:added-in-run and rule:stood-unchanged.\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(REGENERATOR), "--repo-root", str(self.t.root)],
                              capture_output=True, text=True)
        catalog = self.t.root / "crux" / "catalog" / "rules.json"
        return proc, (json.loads(catalog.read_text(encoding="utf-8")) if catalog.exists() else {})

    def test_the_rules_catalog_ships_a_guidance_rule_with_no_standing_field(self):
        proc, without = self._catalog_run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.t.write_record()
        self.assertEqual(json.loads(
            self.t.built()[0]["resolver.json"])[GUIDANCE]["standing"], "guidance",
            "control: the record is live in this tree")
        proc, with_record = self._catalog_run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rules = with_record["rules"]
        self.assertEqual(set(rules), {"added-in-run", "stood-unchanged"})
        self.assertEqual(set(rules["added-in-run"]), set(rules["stood-unchanged"]))
        self.assertNotIn("standing", json.dumps(with_record))
        self.assertEqual(with_record, without, "a record moves no catalog byte")

    def _lint(self, *slugs: str) -> tuple[int, dict]:
        (self.t.root / "pages" / "p.md").write_text("".join(f"rule:{s}\n" for s in slugs), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = LINT.main(["--repo-root", str(self.t.root), "--path", str(self.t.root / "pages")])
        return rc, json.loads(out.getvalue().strip().splitlines()[-1])

    def test_a_guidance_citation_resolves_as_a_binding_one_does(self):
        slugs = ("added-in-run", "stood-unchanged", "stood-edited")
        rc_without, report_without = self._lint(*slugs)
        self.t.write_record()
        rc_with, report_with = self._lint(*slugs)
        self.assertEqual((rc_without, rc_with), (0, 0), (report_without, report_with))
        self.assertEqual(report_with["rule_findings"], [])
        self.assertEqual(report_with["rule_tokens"], 3, "all three citations were scanned")
        self.assertEqual(report_with, report_without)
        # control: the lint does fail an unknown slug in the same tree
        rc, report = self._lint("added-in-run", "no-such-rule-anywhere")
        self.assertEqual(rc, 1)
        self.assertEqual([f["reason"] for f in report["rule_findings"]], ["unknown"])


REMOVED = "ADR-0901/dropped-in-run"
REMOVED_WORDING = "Dropped in the run."


def _removed_entry() -> dict:
    """The record's entry for a rule that stood at base_commit and the run deleted."""
    return {"handle": REMOVED, "base": _entry(REMOVED_WORDING)}


def _record_with_removal(promotions: list[dict] | None = None) -> dict:
    record = _record(promotions)
    record["removed_in_run"] = [_removed_entry()]
    return record


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class RemovedInRunProjectionTests(_Base):
    """A rule deleted in-run binds at its base_commit wording until the owner promotes the
    deletion, so every projection keeps it live at that wording (ADR-0151 decisions 1, 2, 4)."""

    def test_an_unpromoted_deletion_projects_binding_at_its_base_wording(self):
        self.t.write_record(_record_with_removal())
        summaries, doctrine = self.t.built()
        resolver = json.loads(summaries["resolver.json"])
        self.assertEqual(resolver[REMOVED]["rule"], REMOVED_WORDING)
        self.assertEqual((resolver[REMOVED]["standing"], resolver[REMOVED]["binding_rule"]),
                         ("binding", REMOVED_WORDING))
        self.assertEqual(resolver[REMOVED]["in_run_edit"], ["deleted-in-run"])
        self.assertEqual(resolver["slugs"]["dropped-in-run"], REMOVED)
        rows = {r[0]: r for r in _standing_rows(summaries["rule-table.md"])}
        self.assertEqual(rows[REMOVED][1:], ["binding", REMOVED_WORDING, "deleted-in-run"])
        alpha = doctrine["index.md"].split("## alpha", 1)[1].split("## beta", 1)[0]
        self.assertIn(f"| {REMOVED} |", alpha.split("_Standing (from provenance")[0])
        self.assertIn(f"| {REMOVED} | binding | {REMOVED_WORDING} | deleted-in-run |", alpha)

    def test_a_citation_of_the_deleted_rule_resolves(self):
        rc, report = GuidanceRulesKeepResolvingTests._lint(self, "dropped-in-run")
        self.assertEqual(rc, 1, "control: with no record the deleted rule is unknown")
        self.t.write_record(_record_with_removal())
        rc, report = GuidanceRulesKeepResolvingTests._lint(self, "dropped-in-run")
        self.assertEqual((rc, report["rule_findings"]), (0, []))

    def test_a_promoted_deletion_leaves_every_projection(self):
        promotion = {"date": "2026-09-01", "instruction": "Promote the deletion.",
                     "handles": [REMOVED], "body": False}
        self.t.write_record(_record_with_removal([promotion]))
        summaries, doctrine = self.t.built()
        self.assertNotIn(REMOVED, json.loads(summaries["resolver.json"]))
        self.assertNotIn(REMOVED, summaries["rule-table.md"])
        self.assertNotIn(REMOVED, doctrine["index.md"])
        rc, report = GuidanceRulesKeepResolvingTests._lint(self, "dropped-in-run")
        self.assertEqual(rc, 1)

    def test_the_resolver_names_the_fields_edited_in_run(self):
        self.t.write_record()
        resolver = json.loads(self.t.built()[0]["resolver.json"])
        self.assertEqual(resolver[EDITED]["in_run_edit"], ["rule"])
        self.assertEqual(resolver[BINDING]["in_run_edit"], [])
        self.assertEqual(resolver[GUIDANCE]["in_run_edit"], ["added"])
        self.assertNotIn("in_run_edit", resolver[OTHER])

    def test_a_scope_only_in_run_edit_projects_as_an_edit_of_a_binding_rule(self):
        record = _record()
        record["rules"][1]["base"]["scope"] = "crux/"           # BINDING: the run widened its scope
        self.t.write_record(record)
        summaries, doctrine = self.t.built()
        row = json.loads(summaries["resolver.json"])[BINDING]
        self.assertEqual((row["standing"], row["binding_rule"], row["in_run_edit"]),
                         ("binding", "Stood at base.", ["scope"]))
        rows = {r[0]: r for r in _standing_rows(summaries["rule-table.md"])}
        self.assertEqual(rows[BINDING][1:], ["binding", "Stood at base.", "scope"])
        self.assertIn(f"| {BINDING} | binding | Stood at base. | scope |", doctrine["index.md"])

    def test_a_deleted_handle_back_in_the_governs_block_refuses(self):
        record = _record_with_removal()
        self.t.write_record(record)
        self.t.write_adrs({**RULES, REMOVED: REMOVED_WORDING})
        for module in (SA, CD):
            rc, out, err = self.t.run(module, "--dry-run")
            self.assertEqual(rc, 1, (module.__name__, err))
            problems = json.loads(out)["validation_errors"]
            self.assertTrue(any("is back in the governs block" in p["problem"] for p in problems), problems)

    def _record_removing(self, **fields) -> dict:
        record = _record()
        record["removed_in_run"] = [{"handle": REMOVED, "base": _entry(REMOVED_WORDING, **fields)}]
        return record

    def _assert_refused(self, record: dict, fragment: str):
        self.t.write_record(record)
        for module in (SA, CD):
            rc, out, err = self.t.run(module, "--dry-run")
            self.assertEqual(rc, 1, (module.__name__, out, err))
            problems = json.loads(out)["validation_errors"]
            self.assertTrue(any(p["source_adr"] == "ADR-0901" and p["handle"] == REMOVED
                                and fragment in p["problem"] for p in problems), problems)

    def test_a_removed_entry_whose_domain_has_a_newline_refuses(self):
        self.t.write_record(self._record_removing())
        self.assertIn(REMOVED, self.t.built()[0]["resolver.json"])      # positive control
        self._assert_refused(self._record_removing(domain="alpha\n## EVIL \u2014 clean"),
                             "spans more than one line")

    def test_a_removed_entry_whose_domain_has_a_carriage_return_refuses(self):
        self._assert_refused(self._record_removing(domain="alpha\r## EVIL"),
                             "spans more than one line")

    def test_a_removed_entry_with_an_empty_retires_refuses(self):
        self._assert_refused(self._record_removing(retires=[]), "`retires` must not be empty")

    def test_a_deletion_whose_adr_left_the_active_set_projects_nothing(self):
        self.t.write_record(_record_with_removal())
        self.assertIn(REMOVED, self.t.built()[0]["resolver.json"])      # positive control
        archive = self.t.adrs / "archive"
        archive.mkdir()
        (self.t.adrs / "ADR-0901-x.md").rename(archive / "ADR-0901-x.md")
        summaries, doctrine = self.t.built()
        self.assertNotIn(REMOVED, summaries["resolver.json"])
        self.assertNotIn(REMOVED, summaries["rule-table.md"])
        self.assertNotIn(REMOVED, doctrine["index.md"])


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class AdrsDirectoryContainmentTests(_Base):
    """[SECURITY:S5] The provenance reader refuses an `adrs` directory that resolves outside the
    tree (the ancestor leg), as well as a symlinked provenance directory or record."""

    def test_an_adrs_directory_linked_outside_the_tree_refuses(self):
        self.t.write_record()
        self.assertEqual(len(sp.provenance_entries(self.t.adrs)), 1)       # positive control
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, True)
        moved = outside / "adrs"
        self.t.adrs.rename(moved)
        self.t.adrs.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError) as caught:
            sp.provenance_entries(self.t.adrs)
        self.assertIn("does not resolve inside the tree", str(caught.exception))

    def test_an_adrs_directory_linked_inside_the_tree_reads(self):
        self.t.write_record()
        moved = self.t.root / "bionic" / "adrs-stored"
        self.t.adrs.rename(moved)
        self.t.adrs.symlink_to(moved.name, target_is_directory=True)
        self.assertEqual(len(sp.provenance_entries(self.t.adrs)), 1)


@unittest.skipUnless(HAVE_YAML, "PyYAML required (run under uv)")
class PlanContractOrderTests(_Base):
    """A loaded frame whose input_domain is not a list fails the plan's own contract check.

    The provenance membership test reads `input_domain` with `in`; it must run after the
    list check, or a None frame escapes as a TypeError instead of the contract refusal."""

    def _summary_loaded(self):
        return SA._load_summary_inputs(self.t.root, sp.read_manifest(self.t.root))

    def _doctrine_loaded(self):
        return CD.dp._load_doctrine_inputs(self.t.root, sp.read_manifest(self.t.root))

    def test_control_the_unmodified_frames_plan(self):
        for record in (False, True):
            if record:
                self.t.write_record()
            loaded, view, pending, _ = self._summary_loaded()
            sp._plan_summary_outputs(loaded, view, pending)
            loaded, view, pending, _ = self._doctrine_loaded()
            CD.dp._plan_doctrine_outputs(loaded, view, pending)

    def test_summaries_plan_refuses_a_non_list_input_domain(self):
        for record in (False, True):
            if record:
                self.t.write_record()
            loaded, view, pending, _ = self._summary_loaded()
            loaded["metadata"]["input_domain"] = None
            with self.assertRaises(sp.GovernsValidationError) as caught:
                sp._plan_summary_outputs(loaded, view, pending)
            self.assertIn("summaries metadata contract invalid", str(caught.exception))

    def test_doctrine_plan_refuses_a_non_list_input_domain(self):
        for record in (False, True):
            if record:
                self.t.write_record()
            loaded, view, pending, _ = self._doctrine_loaded()
            loaded["digests"]["input_domain"] = None
            with self.assertRaises(sp.GovernsValidationError) as caught:
                CD.dp._plan_doctrine_outputs(loaded, view, pending)
            self.assertIn("doctrine digest model invalid", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
