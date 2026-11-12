"""A published historical replacement resolves through the retirements in force.

Synthetic pure facts, read by the real projection readers; they supply no council,
publication or owner approval. Every fixture is built in memory or in a temporary
tree and reads no dev-only surface.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import summaries_projection as sp  # noqa: E402


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = _load("_hrr_lint", "lint-governs-references.py")
catalog = _load("_hrr_catalog", "generate-rules-catalog.py")


def record(handle, *, retires=(), status="Accepted"):
    return dict(handle=handle, source_adr=handle.split("/")[0], domain="testing",
                rule="Frozen implementation text.", scope="reader", provenance="authored",
                source_status=status, source_kind="adr", adr_num=sp.adr_num(handle.split("/")[0]),
                retires=list(retires), retired_by=[])


OLD = "ADR-0001/predecessor"
DEMOTED = "ADR-0110/implementation"
SURVIVING = "ADR-0110/surviving"
H = "ADR-0146/constraint"            # the recorded replacement
H2 = "ADR-0179/restated-rule"         # restates H, distinct slug
H3 = "ADR-0180/third-rule"            # restates H2, distinct slug
ARCHIVED = "ADR-0170/archived-rule"   # an archived displacer nothing displaced
PREPARED = dict(origin="prospective-prepared", publication_ref=dict(
    path="docs/adrs/migrations/one.publication.json", sha256="5" * 64))
CANDIDATE = dict(origin="prospective-candidate", package_sha256="6" * 64)
PUBLISHED = dict(origin="prospective-publication", publication_ref=dict(
    path="docs/adrs/migrations/one.publication.json", sha256="5" * 64, publication_commit="7" * 40))
SECOND = dict(path="docs/adrs/archive/second.md", source_adr="ADR-0111", tier="archive",
              status="Superseded", source_identity="c" * 64, clause_sha256="d" * 64)


def facts(replacements=(H,), origin=None):
    view = dict(historical_handles={DEMOTED: dict(source_identity="a" * 64,
        destination=dict(source_adr="ADR-0110", clause_sha256="b" * 64), replacements=list(replacements))},
        historical_displacements=[dict(target_handle=OLD, source_displacer=DEMOTED,
            source_identity="a" * 64, source_ref=dict(path="docs/adrs/archive/source.md",
                source_adr="ADR-0110", clause_sha256="b" * 64))],
        retired_handles=[OLD], reserved_slugs=["implementation"], retained_handles=[],
        source_refs=[dict(path="docs/adrs/archive/source.md", source_adr="ADR-0110", tier="archive",
            status="Superseded", source_identity="a" * 64, clause_sha256="b" * 64)],
        dependency_fingerprints=[dict(path="docs/adrs/migrations/pilot.yaml", sha256="3" * 64)])
    if origin is not None:
        view["origins"] = {DEMOTED: origin}
    return view


def corpus(variant):
    """(a) proposed: the retiring ADR is Proposed, so H is live. (b) accepted: an
    Accepted ADR retires H with H2. (c) chain: a second Accepted ADR retires H2 with
    H3. (d) persisted: the first retiring ADR is Superseded and its retirement
    persists. (e) archived: H is retired by a persisted edge whose archived displacer
    nothing displaced."""
    rows = [record(OLD), record(DEMOTED, retires=[OLD]), record(H), record(SURVIVING)]
    persisted = ()
    if variant == "proposed":
        rows.append(record(H2, retires=[H], status="Proposed"))
    elif variant == "accepted":
        rows.append(record(H2, retires=[H]))
    elif variant == "chain":
        rows += [record(H2, retires=[H]), record(H3, retires=[H2])]
    elif variant == "persisted":
        rows += [record(H2, retires=[H], status="Superseded"), record(H3, retires=[H2])]
        persisted = (sp.RetirementEdge("ADR-0179", H2, H),)
    elif variant == "archived":
        persisted = (sp.RetirementEdge("ADR-0170", ARCHIVED, H),)
    sp._stamp_retirements(rows, persisted_edges=persisted)
    return rows, persisted


def overlay(variant, view=None, **kwargs):
    rows, persisted = corpus(variant)
    return sp._summary_authority_records(rows, view or facts(), {}, {}, persisted_edges=persisted, **kwargs)


def loaded(variant, clauses=()):
    rows, persisted = corpus(variant)
    tree = Path("/synthetic/docs")
    return dict(tree=tree, paths={name: tree / "adrs/summaries" / name for name in
        ("rule-table.md", "resolver.json", "implementation-map.md", "_meta.json")},
        records=rows, reviews=dict(batches={}, receipts=[], no_rule=[]), aliases={}, governs_from=None,
        archived_handles=[ARCHIVED] if variant == "archived" else [], signed_handles=[],
        historical_clauses=list(clauses), publication_history=[], persisted_edges=persisted,
        implementation_map="# Synthetic implementation map\n", metadata=dict(
            adr_frontmatter_sha256="1" * 64, backfill_reviews_sha256=None,
            observations_sha256=None, survey_receipts_sha256=None,
            input_domain=["adrs", "backfill-reviews"], schema="6", tool="summarize-adrs.py"))


def pending():
    return dict(path="docs/adrs/migrations/pilot.application.json", sha256="2" * 64,
        close_identity=dict(batch=dict(path="docs/adrs/migrations/pilot.yaml", sha256="3" * 64),
            book_id="PB-9998", run_id="RUN-999", book_content_hash="sha256:" + "4" * 64,
            slot="implementation-1", gate_prompt=3))


def clause(source, replacements):
    return dict(source_identity=source["source_identity"],
                source_ref={k: source[k] for k in ("path", "source_adr", "clause_sha256")},
                destination={k: source[k] for k in ("source_adr", "clause_sha256")},
                replacements=list(replacements))


def rule_table(data, view):
    plan = sp._plan_summary_outputs(data, view, pending())
    outputs = sp._materialize_summary_outputs(plan, sp._committed_publication_ref(pending(), dict(
        path=pending()["path"], sha256=pending()["sha256"], publication_commit="5" * 40)))
    return outputs[Path("/synthetic/docs/adrs/summaries/rule-table.md")].decode()


def problems(exc):
    return str(exc.exception)


class ResolveThrough(unittest.TestCase):
    def test_two_handle_cycle_terminates_empty(self):
        self.assertEqual(sp.resolve_through(["A/x"], {"A/x": {"B/y"}, "B/y": {"A/x"}}, set()), {"A/x": ()})

    def test_diamond_is_deduplicated(self):
        successors = {"A/x": {"B/y", "C/z"}, "B/y": {"D/w"}, "C/z": {"D/w"}}
        self.assertEqual(sp.resolve_through(["A/x"], successors, {"D/w"}), {"A/x": ("D/w",)})

    def test_live_handle_is_not_followed_further(self):
        self.assertEqual(sp.resolve_through(["A/x"], {"A/x": {"B/y"}}, {"A/x", "B/y"}), {"A/x": ("A/x",)})

    def test_retired_displacer_is_followed_never_dropped(self):
        successors = {"A/x": {"B/y"}, "B/y": {"C/z"}}
        self.assertEqual(sp.resolve_through(["A/x"], successors, {"C/z"}), {"A/x": ("C/z",)})

    def test_successors_agree_with_retired_by(self):
        rows, persisted = corpus("persisted")
        successors = sp.replacement_successors(rows, persisted_edges=persisted)
        for row in rows:
            self.assertEqual(sorted({h.split("/")[0] for h in successors.get(row["handle"], ())},
                                    key=sp.adr_num), row["retired_by"], row["handle"])

    def test_resolved_text_never_renders_a_displacer_alone(self):
        self.assertEqual(sp.resolved_replacement_text([H], {H: (H2,)}), f"{H} (now {H2})")
        self.assertEqual(sp.resolved_replacement_text([H], {H: (H,)}), H)
        self.assertEqual(sp.resolved_replacement_text([H], {H: ()}), H)


class HistoricalHandleFacts(unittest.TestCase):
    """R1: the historical-handle facts of `_summary_authority_records`."""

    def test_proposed_retirement_keeps_h_live(self):
        result = overlay("proposed")
        self.assertEqual(result["historical_slugs"]["implementation"]["replacements"], [H])

    def test_accepted_retirement_resolves_and_keeps_the_recorded_row(self):
        for origin in (None, PUBLISHED):
            with self.subTest(origin=origin):
                result = overlay("accepted", facts(origin=origin))
                self.assertEqual(result["historical_slugs"]["implementation"]["replacements"], [H])
                self.assertEqual(sp.resolve_replacements([H], result["records"], persisted_edges=()), {H: (H2,)})

    def test_two_step_chain_resolves_to_the_last_displacer(self):
        result = overlay("chain")
        self.assertEqual(sp.resolve_replacements([H], result["records"], persisted_edges=()), {H: (H3,)})

    def test_persisted_retirement_of_a_superseded_host_is_followed(self):
        rows, persisted = corpus("persisted")
        result = sp._summary_authority_records(rows, facts(), {}, {}, persisted_edges=persisted)
        self.assertEqual(sp.resolve_replacements([H], result["records"], persisted_edges=persisted), {H: (H3,)})

    def test_no_live_displacer_refuses(self):
        with self.assertRaises(sp.GovernsValidationError) as exc:
            overlay("archived")
        self.assertIn("summaries replacement is not live architecture", problems(exc))

    def test_prepared_and_candidate_origins_stay_strict(self):
        for origin, prepared in ((PREPARED, True), (CANDIDATE, False),
                                 (dict(PUBLISHED, publication_ref={"path": "x"}), False)):
            with self.subTest(origin=origin["origin"]), self.assertRaises(sp.GovernsValidationError) as exc:
                overlay("accepted", facts(origin=origin), _prepared=prepared)
            self.assertIn("summaries replacement is not live architecture", problems(exc))

    def test_prepared_origin_with_a_live_replacement_is_accepted(self):
        result = overlay("proposed", facts(origin=PREPARED), _prepared=True)
        self.assertEqual(result["historical_slugs"]["implementation"]["replacements"], [H])

    def test_package_retire_lane_is_not_an_edge(self):
        view = facts(replacements=[H])
        view["retired_handles"] = [OLD, H]
        view["historical_displacements"].append(dict(target_handle=H, source_displacer=SURVIVING,
            source_identity="a" * 64, source_ref=dict(path="docs/adrs/archive/source.md",
                source_adr="ADR-0110", clause_sha256="b" * 64)))
        with self.assertRaises(sp.GovernsValidationError) as exc:
            overlay("proposed", view)
        self.assertIn("summaries replacement is not live architecture", problems(exc))

    def test_package_historical_lane_is_not_an_edge(self):
        view = facts(replacements=[H])
        view["historical_handles"][H] = dict(source_identity="e" * 64,
            destination=dict(source_adr="ADR-0146", clause_sha256="f" * 64), replacements=[SURVIVING])
        view["reserved_slugs"] = ["constraint", "implementation"]
        with self.assertRaises(sp.GovernsValidationError) as exc:
            overlay("plain", view)
        self.assertIn("summaries replacement is not live architecture", problems(exc))


class HistoricalClausesAndRuleTable(unittest.TestCase):
    """R2: the historical clauses of `_plan_summary_outputs`; R4: the rule table."""

    def test_positive_control_renders_h_alone(self):
        table = rule_table(loaded("proposed"), facts())
        self.assertIn(f"| {H} |", table)
        self.assertNotIn("(now ", table)

    def test_rule_table_shows_the_resolution_beside_the_recorded_replacement(self):
        self.assertIn(f"| {H} (now {H2}) |", rule_table(loaded("accepted"), facts()))
        self.assertIn(f"| {H} (now {H3}) |", rule_table(loaded("chain"), facts()))

    def test_published_clause_resolves(self):
        source = facts()["source_refs"][0]
        for variant in ("accepted", "chain"):
            with self.subTest(variant=variant):
                self.assertIn("## Historical implementation clauses",
                              rule_table(loaded(variant, [clause(source, [H])]), facts()))

    def test_application_batch_clause_with_no_handle_fact_resolves(self):
        view = facts(); view["source_refs"].append(copy.deepcopy(SECOND))
        self.assertIn("## Historical implementation clauses",
                      rule_table(loaded("accepted", [clause(SECOND, [H])]), view))

    def test_prepared_clause_stays_strict(self):
        view = facts(replacements=[SURVIVING], origin=PREPARED)
        source = view["source_refs"][0]
        with self.assertRaises(sp.GovernsValidationError) as exc:
            rule_table(loaded("accepted", [clause(source, [H])]), view)
        self.assertIn("summaries historical clause is not a selected source", problems(exc))

    def test_application_clause_without_live_displacer_refuses(self):
        # Binding note anthropic_top:F2: a clause matching no handle fact, whose
        # replacement H is displaced only by a package retire lane, or by an
        # archived displacer, refuses.
        retire_lane = facts(replacements=[SURVIVING])
        retire_lane["source_refs"].append(copy.deepcopy(SECOND))
        retire_lane["retired_handles"] = [OLD, H]
        retire_lane["retained_handles"] = [SURVIVING]
        retire_lane["historical_displacements"].append(dict(target_handle=H, source_displacer=SURVIVING,
            source_identity="a" * 64, source_ref=dict(path="docs/adrs/archive/source.md",
                source_adr="ADR-0110", clause_sha256="b" * 64)))
        archived = facts(replacements=[SURVIVING])
        archived["source_refs"].append(copy.deepcopy(SECOND))
        for name, variant, view in (("retire-lane", "proposed", retire_lane), ("archived", "archived", archived)):
            with self.subTest(name), self.assertRaises(sp.GovernsValidationError) as exc:
                rule_table(loaded(variant, [clause(SECOND, [H])]), view)
            self.assertIn("summaries historical clause is not a selected source", problems(exc))


class Suggestions(unittest.TestCase):
    """R5: the governs-reference lint; R6: the rules catalog."""

    def lint_rows(self, variant):
        rows, persisted = corpus(variant)
        result = sp._summary_authority_records(rows, facts(), {}, {}, persisted_edges=persisted)
        return lint._resolved_overlay(result, persisted_edges=persisted)["historical_slugs"]["implementation"]

    def test_lint_suggests_the_live_displacer(self):
        expectations = {"proposed": [H], "accepted": [H2], "chain": [H3], "persisted": [H3]}
        for variant, expected in expectations.items():
            with self.subTest(variant=variant):
                row = self.lint_rows(variant)
                self.assertEqual(row["replacements"], expected)
                message = lint._historical_message("rule:implementation", row)
                self.assertIn(", ".join("rule:" + sp.slug_of(h) for h in expected), message)

    def test_lint_finding_reads_the_resolved_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "notes.md"; path.write_text("See rule:implementation.\n")
            _, findings, _, _ = lint.find_unresolved([path], {}, {}, {},
                historical_slugs={"implementation": self.lint_rows("chain")}, authoring=True)
        self.assertTrue(findings)
        self.assertIn("rule:third-rule", json.dumps(findings))
        self.assertNotIn("rule:constraint", json.dumps(findings))

    def catalog_reason(self, variant):
        rows, persisted = corpus(variant)
        payload = catalog._catalog_payload(dict(records=rows, reviews=dict(batches={}, receipts=[], no_rule=[]),
            aliases={}, cited={"implementation": ["crux/skills/x/SKILL.md"]}, refusals=[],
            persisted_edges=persisted), facts())
        return [row["reason"] for row in payload["ineligible"] if row["slug"] == "implementation"]

    def test_catalog_suggests_the_live_displacer(self):
        expectations = {"proposed": "rule:constraint", "accepted": "rule:restated-rule",
                        "chain": "rule:third-rule", "persisted": "rule:third-rule"}
        for variant, expected in expectations.items():
            with self.subTest(variant=variant):
                self.assertEqual(self.catalog_reason(variant),
                                 ["historical implementation citation; replace with " + expected])


class ArchitecturalFootnotes(unittest.TestCase):
    """R7: the arch spine's historical-clause footnotes."""

    def setUp(self):
        from crux.arch import core
        import implementation_migration as migration
        self.core, self.migration = core, migration
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "docs/adrs").mkdir(parents=True)

    def index(self, clauses, resolution):
        with mock.patch.object(self.migration, "_decision_index_applicability", return_value="PRESENT"), \
                mock.patch.object(self.core, "_decision_history",
                                  return_value=(clauses, {}, dict(state="original"))), \
                mock.patch.object(self.core, "_replacement_resolutions", return_value=resolution) as resolve:
            text, _ = self.core.extract_decision_index(self.root, "docs")
        return text, resolve

    def test_footnote_shows_the_resolution_beside_the_recorded_replacement(self):
        source = facts()["source_refs"][0]
        text, _ = self.index([clause(source, [H])], {H: (H,)})
        self.assertIn(f"architectural replacements: {H}\n", text)
        text, resolve = self.index([clause(source, [H])], {H: (H3,)})
        self.assertIn(f"architectural replacements: {H} (now {H3})", text)
        resolve.assert_called_once()

    def test_tree_without_published_migration_reads_no_overlay(self):
        text, resolve = self.index([], {})
        resolve.assert_not_called()
        self.assertNotIn("Historical implementation clauses", text)

    def test_resolutions_read_the_lint_overlay(self):
        rows, persisted = corpus("chain")
        with mock.patch.object(sp, "collect_records", return_value=rows), \
                mock.patch.object(sp, "persisted_retirement_edges", return_value=persisted), \
                mock.patch.object(sp, "read_reviews", return_value=dict(batches={}, receipts=[], no_rule=[])), \
                mock.patch.object(sp, "read_manifest", return_value={}), \
                mock.patch.object(sp, "observations_source", return_value=None), \
                mock.patch.object(sp, "collect_observation_alias_rows", return_value={}), \
                mock.patch.object(sp, "adrs_dir", return_value=self.root / "docs/adrs"):
            resolution = self.core._replacement_resolutions(self.root, facts(), [clause(facts()["source_refs"][0], [H])])
        self.assertEqual(resolution, {H: (H3,)})


import test_implementation_authority as authority  # noqa: E402
import yaml  # noqa: E402

AUTH = "ADR-0146/authority-migration-is-reviewed-and-source-bound"
REPL = "ADR-0146/rotation-preserves-assessment-outcomes"


class PublishedBatchReplacements(authority._PublicationFixture):
    """R3: `_architectural_refs` re-validating an already-published batch."""

    def adr(self, number, slug, governs, status="Accepted"):
        rules = [dict(domain="testing", rule="A restated rule.", scope="reader", provenance="authored", **entry)
                 for entry in governs]
        (self.root / f"docs/adrs/ADR-{number}-{slug}.md").write_text("---\n" + yaml.safe_dump({
            "id": f"ADR-{number}", "status": status, "accepted_date": "2026-11-10", "governs": rules}) +
            "---\nA synthetic restatement.\n")

    def commit(self):
        authority.sup.commit_all(self.root, "synthetic restatement")

    def view(self):
        return authority.migration.authority_view(self.root)

    def test_positive_control_published_batch_with_live_replacement(self):
        self.close(); self.publish()
        self.adr("0179", "restate", [dict(handle="ADR-0179/restated-rotation", retires=[REPL])], status="Proposed")
        self.commit()
        self.assertEqual(self.view()["state"], "published")

    def test_retired_and_restated_replacement_resolves_on_revalidation(self):
        self.close(); self.publish()
        self.adr("0179", "restate", [dict(handle="ADR-0179/restated-rotation", retires=[REPL])])
        self.commit()
        self.assertEqual(self.view()["state"], "published")

    def test_two_step_chain_resolves_on_revalidation(self):
        self.close(); self.publish()
        self.adr("0179", "restate", [dict(handle="ADR-0179/restated-rotation", retires=[REPL])])
        self.adr("0180", "again", [dict(handle="ADR-0180/third-rotation", retires=["ADR-0179/restated-rotation"])])
        self.commit()
        self.assertEqual(self.view()["state"], "published")
        records, successors, live = authority.migration._architecture_index(self.root)
        self.assertEqual(sp.resolve_through([REPL], successors, live), {REPL: ("ADR-0180/third-rotation",)})

    def test_replacement_with_no_live_displacer_refuses(self):
        self.close(); self.publish()
        self.adr("0179", "restate", [dict(handle="ADR-0179/a-rotation", retires=[REPL, "ADR-0180/b-rotation"])])
        self.adr("0180", "again", [dict(handle="ADR-0180/b-rotation", retires=["ADR-0179/a-rotation"])])
        self.commit()
        with self.assertRaisesRegex(authority.migration.Refused, "migration-constraint-not-live-accepted"):
            self.view()

    def test_retired_authorizing_ref_stays_strict(self):
        self.close(); self.publish()
        self.adr("0179", "restate", [dict(handle="ADR-0179/restated-authority", retires=[AUTH])])
        self.commit()
        with self.assertRaisesRegex(authority.migration.Refused, "migration-constraint-not-live-accepted"):
            self.view()

    def test_pairing_bearing_replacement_stays_strict(self):
        # openai_top:F2: the strict refusal comes from call (c), after the real
        # receipts validated; the entry is classed pairing-bearing there.
        self.close(); self.publish()
        self.adr("0179", "restate", [dict(handle="ADR-0179/restated-rotation", retires=[REPL])])
        self.commit()
        original = authority.migration._disposition_inputs
        batch = yaml.safe_load(self.f.path.read_bytes())

        def pairing(*args, pairings=None, **kwargs):
            result = original(*args, pairings=pairings, **kwargs)
            pairings.update(entry["source_identity"] for entry in batch["entries"])
            return result
        calls = []
        refs = authority.migration._architectural_refs

        def recorded(*args, **kwargs):
            calls.append((list(args[1]), list(kwargs.get("published_replacements", ()))))
            return refs(*args, **kwargs)
        with mock.patch.object(authority.migration, "_disposition_inputs", side_effect=pairing), \
                mock.patch.object(authority.migration, "_architectural_refs", side_effect=recorded):
            with self.assertRaisesRegex(authority.migration.Refused, "migration-constraint-not-live-accepted"):
                self.view()
        self.assertEqual(calls[-1], ([REPL], []))

    def test_published_call_shape_checks_each_replacement_once_after_receipts(self):
        self.close(); self.publish()
        calls = []
        refs = authority.migration._architectural_refs

        def recorded(*args, **kwargs):
            calls.append((list(args[1]), list(kwargs.get("published_replacements", ()))))
            return refs(*args, **kwargs)
        with mock.patch.object(authority.migration, "_architectural_refs", side_effect=recorded):
            self.assertEqual(self.view()["state"], "published")
        self.assertEqual(calls, [([AUTH], []), ([], [REPL])])

    def test_unpublished_batch_naming_a_retired_replacement_refuses(self):
        self.close()
        self.adr("0179", "restate", [dict(handle="ADR-0179/restated-rotation", retires=[REPL])])
        self.commit()
        with self.assertRaisesRegex(authority.migration.Refused, "migration-constraint-not-live-accepted"):
            authority.migration.inventory(self.root, self.f.rel)

    def test_successor_maps_agree(self):
        # anthropic_top:F9: R3's successor map equals the projection readers' map.
        self.adr("0179", "restate", [dict(handle="ADR-0179/restated-rotation", retires=[REPL])])
        self.adr("0180", "again", [dict(handle="ADR-0180/third-rotation", retires=["ADR-0179/restated-rotation"])])
        _, successors, _ = authority.migration._architecture_index(self.root)
        adrs = self.root / "docs/adrs"
        # The fixture's own retires names a handle collect_records would refuse as a
        # typo, so the records carry exactly the fields the edge map reads.
        records = [dict(handle=rule["handle"], source_status=fm.get("status"), retires=rule.get("retires", []))
                   for path in adrs.glob("ADR-*.md") for fm in [sp.read_frontmatter(path.read_text())]
                   for rule in fm.get("governs") or []]
        projected = sp.replacement_successors(records, persisted_edges=sp.persisted_retirement_edges(adrs))
        self.assertIn(REPL, projected)
        self.assertEqual(successors, projected)


import test_adr_migration as migration_fixtures  # noqa: E402
import test_adr_migration_publication as publication_tests  # noqa: E402


class PublicationTimeRevalidation(migration_fixtures.MigrationFixture):
    """Creation nit anthropic_top:F3: a later ADR retires a successor of a published
    package. The package re-validates unchanged under its publication-time
    standing, and the published replacement resolves to the restatement."""

    def test_retired_successor_of_published_package(self):
        import decision_policy as dp
        from cycle_workflow import digest, encoded
        import implementation_migration as historical
        subject = dp.propose(self.root, {"title": "Successor", "body": "# Successor\nKeep lasting context.",
            "governs": [{"handle": "lasting-context", "domain": "migration", "rule": "Keep lasting context.",
                         "scope": "context"}]}, origin="direct")["path"]
        self.write("bionic/adrs/councils/successor.json",
                   self.council(subject, digest((self.docs / subject).read_bytes()), purpose="adr"))
        dp.accept(self.root, subject, "adrs/councils/successor.json", human_approval="Accept successor")
        rule = dp.frontmatter((self.docs / subject).read_text())[0]["governs"][0]
        self.package["items"][0].update(disposition="replace", successors=[{"handle": rule["handle"],
            "source": self.bind("bionic/" + subject), "clause_sha256": digest(encoded(rule))}])
        self.write(self.package_path, self.package)
        self.owner["presented"] = self.bind(self.package_path)
        self.council_path = "bionic/adrs/councils/replace-disposition.json"
        vote = self.council(self.package_path.removeprefix("bionic/"), self.bind(self.package_path)["sha256"])
        vote["readiness"] = self.readiness
        vote["review_bundle_sha256"] = digest(encoded(migration_fixtures.m.review_bundle(self.root, self.package_path)))
        self.write(self.council_path, self.seal(vote)); self.commit("Exact replacement council")
        publication_tests.PublicationTests.approve(self)
        self.write("bionic/adrs/migrations/publication-one.publication.json",
                   json.loads((self.root / self.candidate).read_bytes()))
        self.commit("Publish replacement")
        before = historical.authority_view(self.root)
        handle = self.package["items"][0]["handle"]
        self.assertEqual(before["historical_handles"][handle]["replacements"], [rule["handle"]])
        restated = dp.propose(self.root, {"title": "Restatement", "body": "# Restatement\nKeep context.",
            "governs": [{"handle": "restated-context", "domain": "migration", "rule": "Keep context.",
                         "scope": "context", "retires": [rule["handle"]]}]}, origin="direct")["path"]
        self.write("bionic/adrs/councils/restated.json",
                   self.council(restated, digest((self.docs / restated).read_bytes()), purpose="adr"))
        dp.accept(self.root, restated, "adrs/councils/restated.json", human_approval="Accept restatement")
        self.commit("Retire the published successor")
        after = historical.authority_view(self.root)
        self.assertEqual(after["historical_handles"], before["historical_handles"])
        new = dp.frontmatter((self.docs / restated).read_text())[0]["governs"][0]["handle"]
        records = sp.collect_records(self.docs / "adrs")
        overlay = sp._summary_authority_records(records, after, {}, {})
        self.assertEqual(overlay["historical_slugs"][handle.split("/", 1)[1]]["replacements"], [rule["handle"]])
        self.assertEqual(sp.resolve_replacements([rule["handle"]], overlay["records"], persisted_edges=None),
                         {rule["handle"]: (new,)})


if __name__ == "__main__":
    unittest.main()
