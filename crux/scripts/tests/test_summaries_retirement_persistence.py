"""The summaries projection, doctrine, rules catalog and citation lint keep a
retirement after its host leaves Accepted
(rule:retirement-persists-after-its-host-leaves-accepted).

Each test that asserts a retirement persists pairs it with the Accepted
positive control and the never-accepted control on the same fixture.
"""
import copy
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import doctrine_projection as dp  # noqa: E402
import summaries_projection as sp  # noqa: E402
import test_doctrine_migration_projection as doctrine_fixtures  # noqa: E402
import test_summaries_migration_projection as summary_fixtures  # noqa: E402
import yaml  # noqa: E402

LINT = importlib.import_module("lint-governs-references")
CATALOG = importlib.import_module("generate-rules-catalog")

TARGET = "ADR-0001/alpha"
HOST_HANDLE = "ADR-0002/beta"


def facts():
    return dict(historical_handles={}, historical_displacements=[], retired_handles=[],
                reserved_slugs=[], retained_handles=[], source_refs=[], dependency_fingerprints=[])


def entry(num, slug, retires=None):
    out = {"handle": f"ADR-{num:04d}/{slug}", "domain": "d", "rule": f"the {slug} rule",
           "scope": "s", "provenance": "authored"}
    if retires:
        out["retires"] = list(retires)
    return out


class Tree:
    """A throwaway docs tree with an active and an archive tier."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n")
        self.tree = self.root / "bionic"
        self.adrs = self.tree / "adrs"
        (self.adrs / "archive").mkdir(parents=True)
        (self.adrs / "summaries").mkdir()
        (self.adrs / "doctrine").mkdir()
        (self.tree / "manifest.yml").write_text('schema_version: "5"\nconcerns_enabled: [adrs]\n')

    def adr(self, num, status, entries, *, tier="active", accepted_date="2026-01-02", **extra):
        fm = {"id": f"ADR-{num:04d}", "title": f"Decision {num}", "status": status,
              "date": "2026-01-01", "governs": entries}
        if accepted_date is not None:
            fm["accepted_date"] = accepted_date
        fm.update(extra)
        folder = self.adrs if tier == "active" else self.adrs / "archive"
        path = folder / f"ADR-{num:04d}-decision.md"
        path.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n# Body\n")
        return path

    def records(self):
        return sp.collect_records(self.adrs)

    def tombstone(self, handle):
        path = self.adrs / "summaries" / "backfill-reviews.yml"
        digest = hashlib.sha256(handle.encode()).hexdigest()
        path.write_text('config_version: "1"\nbatches:\n  - id: batch-1\n    signed: 2026-08-01\n'
                        f'    handles: [{handle}]\n    no_rule: []\nreceipts:\n'
                        f'  - handle: {handle}\n    digest: {digest}\n    verdict: removed\n'
                        '    batch: batch-1\n')

    def reconciliation(self, handle):
        path = self.adrs / "doctrine" / "reconciliations.yml"
        digest = hashlib.sha256(handle.encode()).hexdigest()
        path.write_text('config_version: "1"\nreconciliations:\n  - invariant: INV-0001\n'
                        f'    handle: {handle}\n    verdict: compatible\n    content_digest: {digest}\n'
                        '    rationale: null\n    signed: 2026-08-01\n')


# status, tier, accepted_date, does the retirement take effect
VARIANTS = {
    "accepted (positive control)": ("Accepted", "active", "2026-01-02", True),
    "deprecated, archived": ("Deprecated", "archive", "2026-01-02", True),
    "superseded, archived": ("Superseded", "archive", "2026-01-02", True),
    "deprecated, still in the active tier": ("Deprecated", "active", "2026-01-02", True),
    "never accepted, archived": ("Deprecated", "archive", None, False),
    "never accepted, active tier": ("Deprecated", "active", None, False),
}


def retiring_tree(tmp, variant):
    status, tier, accepted, _ = VARIANTS[variant]
    tree = Tree(tmp)
    tree.adr(1, "Accepted", [entry(1, "alpha")])
    tree.adr(2, status, [entry(2, "beta", [TARGET])], tier=tier, accepted_date=accepted)
    return tree


def each_variant(test):
    def run(self):
        for name, (_, _, _, effective) in VARIANTS.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                test(self, retiring_tree(tmp, name), effective)
    return run


class CollectedRecordTests(unittest.TestCase):
    @each_variant
    def test_retired_by_names_the_host_once_it_has_left_accepted(self, tree, effective):
        by_handle = {r["handle"]: r for r in tree.records()}
        self.assertEqual(by_handle[TARGET]["retired_by"], ["ADR-0002"] if effective else [])

    def test_every_record_carries_one_internal_edge_tuple_that_no_digest_reads(self):
        for name, (status, _, _, effective) in VARIANTS.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                tree = retiring_tree(tmp, name)
                records = tree.records()
                expected = sp.persisted_retirement_edges(tree.adrs)
                # An Accepted host's edges stay on its records, not in the tuple.
                self.assertEqual(bool(expected), effective and status != "Accepted")
                for record in records:
                    self.assertIs(type(record["persisted_edges"]), tuple)
                    self.assertEqual(record["persisted_edges"], expected)
                    plain = {k: v for k, v in record.items() if k != "persisted_edges"}
                    self.assertEqual(sp.canonical_string(record), sp.canonical_string(plain))
                    self.assertEqual(sp.content_digest(record), sp.content_digest(plain))

    def test_a_reader_without_the_keyword_unions_the_edges_over_its_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = retiring_tree(tmp, "deprecated, archived")
            records = tree.records()
            edges = sp.persisted_retirement_edges(tree.adrs)
            self.assertEqual(sp.live_and_retired_slugs(records),
                             sp.live_and_retired_slugs(records, persisted_edges=edges))
            self.assertEqual(sp._summary_authority_records(records, facts(), {}, {})["retired_slugs"],
                             sp._summary_authority_records(records, facts(), {}, {},
                                                           persisted_edges=edges)["retired_slugs"])
            # An explicit empty tuple replaces the records' own field: the target stays
            # retired (its record is stamped) but nothing names a displacer.
            self.assertEqual(sp.live_and_retired_slugs(records, persisted_edges=())[1], {"alpha": []})


class ProjectionReaderTests(unittest.TestCase):
    @each_variant
    def test_rule_table_resolver_and_slug_map_follow_the_persisted_retirement(self, tree, effective):
        records = tree.records()
        table = sp.build_rule_table(records)
        resolver = sp.build_resolver(records)
        slugs, retired_slugs = sp.live_and_retired_slugs(records)
        if effective:
            roster = table.split("## Retired handles")[1]
            self.assertIn(f"| {TARGET} | the alpha rule | ADR-0001 | ADR-0002 |", roster)
            self.assertNotIn(TARGET, resolver)
            self.assertEqual(retired_slugs, {"alpha": [HOST_HANDLE]})
        else:
            self.assertNotIn("## Retired handles", table)
            self.assertIn(TARGET, resolver)
            self.assertEqual(retired_slugs, {})
        self.assertEqual("alpha" in slugs, not effective)

    @each_variant
    def test_doctrine_entries_drop_the_persistently_retired_rule(self, tree, effective):
        entries = dp.build_domain_entries(tree.records(), [], [], {}, None, repo_root=tree.root)
        handles = {r["handle"] for e in entries for r in e["rules"]}
        self.assertEqual(TARGET in handles, not effective)

    @each_variant
    def test_rules_catalog_withholds_the_persistently_retired_rule(self, tree, effective):
        loaded = dict(root=tree.root, target=tree.root / "crux/catalog/rules.json",
                      records=tree.records(), reviews=sp.read_reviews(tree.adrs), aliases={},
                      cited={"alpha": ["crux/x.md:1"]}, refusals=[],
                      persisted_edges=sp.persisted_retirement_edges(tree.adrs))
        payload = CATALOG._catalog_payload(loaded, facts())
        self.assertEqual("alpha" in payload["rules"], not effective)
        self.assertEqual(payload["unresolved"], ["alpha"] if effective else [])

    def test_summary_plan_accepts_the_persisted_edges_key_and_renders_the_retirement(self):
        for name in ("accepted (positive control)", "deprecated, archived", "never accepted, archived"):
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                tree = retiring_tree(tmp, name)
                effective = VARIANTS[name][3]
                loaded = summary_fixtures.loaded_inputs()
                loaded.update(records=tree.records(), persisted_edges=sp.persisted_retirement_edges(tree.adrs))
                plan = sp._plan_summary_outputs(loaded, facts(), None)
                outputs = {path.name: text for path, text
                           in sp._materialize_summary_outputs(plan, None).items()}
                resolver = json.loads(outputs["resolver.json"])
                self.assertEqual(resolver["retired_slugs"], {"alpha": [HOST_HANDLE]} if effective else {})
                self.assertEqual(TARGET in resolver, not effective)

    def test_summary_plan_refuses_a_malformed_persisted_edges_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = retiring_tree(tmp, "deprecated, archived")
            for bad in (["ADR-0002/beta"], (("ADR-0002", HOST_HANDLE, "not a handle"),),
                        (sp.RetirementEdge("ADR-0002", HOST_HANDLE, "no-slash"),), 7):
                loaded = summary_fixtures.loaded_inputs()
                loaded.update(records=tree.records(), persisted_edges=bad)
                with self.subTest(bad=bad), self.assertRaises(sp.GovernsValidationError):
                    sp._plan_summary_outputs(loaded, facts(), None)

    def test_doctrine_plan_validates_and_passes_the_persisted_edges(self):
        typo = sp.RetirementEdge("ADR-0090", "ADR-0090/a", "ADR-0001/never-existed")
        data = doctrine_fixtures.loaded()
        data["persisted_edges"] = ()
        dp._plan_doctrine_outputs(data, summary_fixtures.facts(), doctrine_fixtures.pending())
        data["persisted_edges"] = (typo,)
        with self.assertRaises(sp.GovernsValidationError) as caught:
            dp._plan_doctrine_outputs(data, summary_fixtures.facts(), doctrine_fixtures.pending())
        self.assertIn("never been a live handle", str(caught.exception.problems))
        data["persisted_edges"] = ["not an edge tuple"]
        with self.assertRaises(sp.GovernsValidationError):
            dp._plan_doctrine_outputs(data, summary_fixtures.facts(), doctrine_fixtures.pending())


class DisplacerTests(unittest.TestCase):
    def chain(self, tmp, b_status, *, b_accepted="2026-01-03", b_tier="archive"):
        """X retired by A/d (A archived, Superseded); A/d retired by B (B archived)."""
        tree = Tree(tmp)
        tree.adr(1, "Accepted", [entry(1, "x")])
        tree.adr(2, "Superseded", [entry(2, "d", ["ADR-0001/x"])], tier="archive")
        if b_status is not None:
            tree.adr(3, b_status, [entry(3, "y", ["ADR-0002/d"])], tier=b_tier,
                     accepted_date=b_accepted, supersedes=["ADR-0002"])
        return tree

    def test_an_archived_displacer_is_named_until_a_once_accepted_edge_retires_it(self):
        cases = {
            "no later retirement (control)": (None, {"x": ["ADR-0002/d"]}),
            "B Accepted": ("Accepted", {"x": []}),
            "B deprecated, once accepted": ("Deprecated", {"x": []}),
            "B superseded, once accepted": ("Superseded", {"x": []}),
        }
        for name, (b_status, expected) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                tree = self.chain(tmp, b_status, b_tier="active" if b_status == "Accepted" else "archive")
                records = tree.records()
                self.assertEqual(sp.live_and_retired_slugs(records)[1], expected)
                self.assertEqual(sp._summary_authority_records(records, facts(), {}, {})["retired_slugs"],
                                 expected)

    def test_a_displacer_retired_only_by_a_never_accepted_edge_is_still_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.chain(tmp, "Deprecated", b_accepted=None)
            self.assertEqual(sp.live_and_retired_slugs(tree.records())[1], {"x": ["ADR-0002/d"]})

    def test_a_persisted_and_an_active_edge_to_one_target_give_one_roster_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.adr(1, "Accepted", [entry(1, "alpha")])
            tree.adr(2, "Deprecated", [entry(2, "beta", [TARGET])], tier="archive")
            tree.adr(3, "Accepted", [entry(3, "gamma", [TARGET])])
            records = tree.records()
            self.assertEqual({r["handle"]: r["retired_by"] for r in records}[TARGET],
                             ["ADR-0002", "ADR-0003"])
            roster = sp.build_rule_table(records).split("## Retired handles")[1]
            self.assertEqual(roster.count(f"| {TARGET} |"), 1)
            self.assertIn("| ADR-0002, ADR-0003 |", roster)
            self.assertEqual(sp.live_and_retired_slugs(records)[1],
                             {"alpha": ["ADR-0002/beta", "ADR-0003/gamma"]})

    def test_an_all_archived_tree_keeps_its_overlay_checks_through_route_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.adr(1, "Deprecated", [entry(1, "alpha")], tier="archive")
            tree.adr(2, "Deprecated", [entry(2, "beta", [TARGET])], tier="archive")
            self.assertEqual(tree.records(), [])
            edges = sp.persisted_retirement_edges(tree.adrs)
            self.assertEqual([(e.handle, e.target) for e in edges], [(HOST_HANDLE, TARGET)])
            view = dict(facts(), historical_handles={TARGET: {}})
            with self.assertRaises(sp.GovernsValidationError) as caught:
                sp._summary_authority_records([], view, {}, {}, persisted_edges=edges)
            self.assertIn("cannot be retired again", str(caught.exception.problems))
            # Route two sees no record, so this reader omits the overlay check.
            with self.assertRaises(sp.GovernsValidationError) as other:
                sp._summary_authority_records([], view, {}, {})
            self.assertNotIn("cannot be retired again", str(other.exception.problems))


class PersistedEdgeRefusalTests(unittest.TestCase):
    """Part 6's four refusals fire on a persisted edge as on an active one."""

    def refused(self, tree, needle):
        with self.assertRaises(sp.GovernsValidationError) as caught:
            tree.records()
        self.assertTrue(any(needle in p["problem"] for p in caught.exception.problems),
                        caught.exception.problems)

    def host_tree(self, tmp, retires, extra_entries=()):
        tree = Tree(tmp)
        tree.adr(1, "Accepted", [entry(1, "alpha")])
        tree.adr(2, "Deprecated", [entry(2, "beta", retires), *extra_entries], tier="archive")
        return tree

    def test_each_of_the_four_refusals_fires_on_a_persisted_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.host_tree(tmp, [TARGET])
            self.assertEqual(len(tree.records()), 1, "control: the clean fixture collects")
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.host_tree(tmp, ["ADR-0002/gamma"], [entry(2, "gamma")])
            self.refused(tree, "retires a handle of its own governs block")
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.host_tree(tmp, [TARGET])
            tree.reconciliation(TARGET)
            self.refused(tree, "a signed reconciliation record names")
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.host_tree(tmp, ["ADR-0001/typo"])
            self.refused(tree, "has never been a live handle")
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.host_tree(tmp, [TARGET])
            tree.tombstone(TARGET)
            self.refused(tree, "both the removed and the retired lane")

    def test_a_never_accepted_host_raises_none_of_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.adr(1, "Accepted", [entry(1, "alpha")])
            tree.adr(2, "Deprecated", [entry(2, "beta", ["ADR-0001/typo"])], tier="archive",
                     accepted_date=None)
            self.assertEqual(len(tree.records()), 1)

    def test_an_active_deprecated_host_reports_one_problem_not_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.adr(1, "Accepted", [entry(1, "alpha")])
            tree.adr(2, "Deprecated", [entry(2, "beta", ["ADR-0001/typo"])])
            with self.assertRaises(sp.GovernsValidationError) as caught:
                tree.records()
            self.assertEqual(len(caught.exception.problems), 1, caught.exception.problems)

    def test_an_archived_file_with_a_non_terminal_status_refuses_and_a_terminal_one_collects(self):
        for status in ("Accepted", "Proposed"):
            with self.subTest(status), tempfile.TemporaryDirectory() as tmp:
                tree = Tree(tmp)
                tree.adr(1, "Accepted", [entry(1, "alpha")])
                tree.adr(2, status, [entry(2, "beta")], tier="archive")
                with self.assertRaises(sp.RetirementPersistenceRefusal):
                    tree.records()
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.adr(1, "Accepted", [entry(1, "alpha")])
            tree.adr(2, "Superseded", [entry(2, "beta")], tier="archive")
            self.assertEqual(len(tree.records()), 1)


class FingerprintTests(unittest.TestCase):
    def tree(self, tmp):
        tree = Tree(tmp)
        tree.adr(1, "Accepted", [entry(1, "alpha")])
        return tree

    def test_the_fingerprint_moves_only_for_archived_retires_or_policy_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.tree(tmp)
            base = sp.adr_frontmatter_sha256(tree.adrs)
            tree.adr(5, "Deprecated", [entry(5, "plain")], tier="archive")
            self.assertEqual(sp.adr_frontmatter_sha256(tree.adrs), base,
                             "an archived ADR with no retires and no policy proof changes nothing")
            tree.adr(5, "Deprecated", [entry(5, "plain")], tier="archive", title="Edited title")
            self.assertEqual(sp.adr_frontmatter_sha256(tree.adrs), base)

            tree.adr(6, "Deprecated", [entry(6, "retiring", [TARGET])], tier="archive")
            with_retires = sp.adr_frontmatter_sha256(tree.adrs)
            self.assertNotEqual(with_retires, base)
            tree.adr(6, "Deprecated", [entry(6, "retiring", ["ADR-0001/other"])], tier="archive")
            self.assertNotEqual(sp.adr_frontmatter_sha256(tree.adrs), with_retires)

    def test_an_archived_policy_host_joins_the_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.tree(tmp)
            base = sp.adr_frontmatter_sha256(tree.adrs)
            tree.adr(7, "Deprecated", [entry(7, "policy")], tier="archive",
                     acceptance_format="crux.adr-acceptance.v1", accepted_date=None)
            hosted = sp.adr_frontmatter_sha256(tree.adrs)
            self.assertNotEqual(hosted, base)
            tree.adr(7, "Deprecated", [entry(7, "policy")], tier="archive", title="Edited",
                     acceptance_format="crux.adr-acceptance.v1", accepted_date=None)
            self.assertNotEqual(sp.adr_frontmatter_sha256(tree.adrs), hosted)

    def test_an_archived_proposal_record_makes_a_host_a_policy_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.tree(tmp)
            tree.adr(8, "Deprecated", [entry(8, "p")], tier="archive", accepted_date=None)
            before = sp.adr_frontmatter_sha256(tree.adrs)
            (tree.adrs / "proposals").mkdir()
            (tree.adrs / "proposals/ADR-0008.json").write_text("{}")
            hashed_with_record = sp.adr_frontmatter_sha256(tree.adrs)
            tree.adr(8, "Deprecated", [entry(8, "p")], tier="archive", accepted_date=None,
                     title="Edited")
            self.assertNotEqual(sp.adr_frontmatter_sha256(tree.adrs), hashed_with_record)
            self.assertNotEqual(hashed_with_record, before)


class LintTests(unittest.TestCase):
    def lint_tree(self, tmp, variant):
        tree = retiring_tree(tmp, variant)
        subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
        return tree

    def test_the_lint_classes_a_citation_of_a_slug_retired_by_an_archived_host_and_names_it(self):
        for name, (_, _, _, effective) in VARIANTS.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                tree = self.lint_tree(tmp, name)
                resolver, overlay = LINT._lint_projection(tree.root)
                doc = Path(tmp) / "note.md"
                doc.write_text("The code follows rule:alpha here.\n")
                findings = LINT.find_unresolved([doc], resolver, overlay["slugs"],
                                                overlay["retired_slugs"])[1]
                if effective:
                    self.assertEqual(overlay["retired_slugs"], {"alpha": [HOST_HANDLE]})
                    self.assertEqual([f["reason"] for f in findings], ["retired"], findings)
                    self.assertIn("rule:beta", findings[0]["message"])
                else:
                    self.assertEqual(findings, [])

    def test_the_lint_source_passes_the_edges_explicitly_at_both_projection_calls(self):
        text = (Path(__file__).resolve().parents[1] / "lint-governs-references.py").read_text()
        self.assertIn("persisted_edges=sp.persisted_retirement_edges(adrs)", text)
        self.assertNotIn("live_and_retired_slugs(", text.replace("`live_and_retired_slugs(records)`", ""),
                         "a direct slug-map call would need the explicit keyword too")


class NoLeakTests(unittest.TestCase):
    NAMES = ("persisted_edges", "persisted_retirement_edges", "retires_in_force", "RetirementEdge")

    def test_no_projection_names_the_internal_edge_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = retiring_tree(tmp, "deprecated, archived")
            records = tree.records()
            overlay = sp._summary_authority_records(records, facts(), {}, {})
            rendered = [sp.build_rule_table(overlay["records"]),
                        json.dumps(sp.build_resolver(overlay["records"]), sort_keys=True),
                        json.dumps(dp.build_domain_entries(records, [], [], {}, None, repo_root=tree.root),
                                   sort_keys=True, default=str)]
            loaded = summary_fixtures.loaded_inputs()
            loaded.update(records=records, persisted_edges=sp.persisted_retirement_edges(tree.adrs))
            plan = sp._plan_summary_outputs(loaded, facts(), None)
            rendered.extend(text.decode() for text in sp._materialize_summary_outputs(plan, None).values())
            self.assertTrue(rendered[0].count("ADR-0002") >= 1, "control: the retirement renders")
            for text in rendered:
                for name in self.NAMES:
                    self.assertNotIn(name, text)

    def test_the_committed_projections_name_none_of_them(self):
        from _dev_surface import require_dev_surface
        repo = Path(__file__).resolve().parents[3]
        summaries, doctrine = repo / "bionic/adrs/summaries", repo / "bionic/adrs/doctrine"
        require_dev_surface(self, summaries, "bionic/adrs/summaries")
        require_dev_surface(self, doctrine, "bionic/adrs/doctrine")
        committed = [repo / "crux/catalog/rules.json",
                     *sorted(summaries.glob("*")), *sorted(doctrine.glob("*"))]
        committed = [p for p in committed if p.is_file()]
        self.assertTrue(committed, "control: the committed projections are read")
        for path in committed:
            text = path.read_text(encoding="utf-8")
            for name in self.NAMES:
                self.assertNotIn(name, text, path.name)


if __name__ == "__main__":
    unittest.main()
