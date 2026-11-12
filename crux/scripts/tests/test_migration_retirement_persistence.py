"""The migration readers take retirement targets from the shared predicate
(rule:retirement-persists-after-its-host-leaves-accepted).

Three readers of `implementation_migration` (the architectural-reference reader, the raw
architecture reader behind the retired and denied sets, and the displacement reader) and the
raw record reader of `migration_disposition` each answer the same question for one host.
Each test that asserts a retirement persists pairs it with the Accepted positive control and
the never-accepted control on the same fixture.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _council_gate_support as sup  # noqa: E402
import implementation_migration as migration  # noqa: E402
import migration_disposition as dispositions  # noqa: E402

OLD = "ADR-0001/old-rule"
NEW = "ADR-0002/new-rule"
HOST_FILE = "ADR-0002-retire-old.md"
RECORD_CODE = "migration-source-record-refused"
DISPOSITION_CODE = "migration-disposition-source-refused"


def governs(handle, retires=None):
    entry = {"domain": "d", "rule": "Rule text.", "scope": "s", "handle": handle,
             "provenance": "authored"}
    if retires is not None:
        entry["retires"] = retires
    return entry


class ReaderMixin:
    """Run the three non-displacement readers over `self.root` and report each answer."""

    def retired_by_refs(self):
        try:
            migration._architectural_refs(self.root, [OLD])
        except migration.Refused as refused:
            if refused.code != "migration-constraint-not-live-accepted":
                raise
            return True
        return False

    def architecture(self):
        records, fingerprints = migration._raw_architecture(self.root)
        return {r["handle"]: r for r in records}, fingerprints

    def retired_by_architecture(self):
        records, _ = self.architecture()
        return any(OLD in r["retired_targets"] for r in records.values() if r["retires_in_force"])

    def retired_by_disposition(self):
        config = migration._configuration(self.root)
        records, _ = dispositions._raw_records(self.root, config)
        return OLD in dispositions.retired_handles(records)

    def answers(self):
        return (self.retired_by_refs(), self.retired_by_architecture(), self.retired_by_disposition())

    def refusal_codes(self):
        codes = []
        for reader in (self.retired_by_refs, self.retired_by_architecture, self.retired_by_disposition):
            with self.assertRaises(migration.Refused) as caught:
                reader()
            codes.append(caught.exception.code)
        return codes


class PlainHostTests(ReaderMixin, unittest.TestCase):
    """A pre-policy host, with no acceptance record, in every lifecycle state."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = sup.init_repo(Path(self.temp.name) / "repo")
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: knowledge\n')
        self.adrs = self.root / "knowledge/adrs"
        (self.adrs / "archive").mkdir(parents=True)
        (self.root / "knowledge/manifest.yml").write_text(
            'schema_version: "5"\nconcerns_enabled: [adrs]\n')
        self.put(self.adrs / "ADR-0001-old.md", {
            "id": "ADR-0001", "status": "Accepted", "accepted_date": "2026-01-01",
            "governs": [governs(OLD)]})

    def put(self, path, fm):
        path.write_text("---\n" + yaml.safe_dump(fm) + "---\n# Body\n")

    def state(self, status, tier="active", *, accepted_date="2026-01-02", entries=None):
        for stale in (self.adrs / HOST_FILE, self.adrs / "archive" / HOST_FILE):
            stale.unlink(missing_ok=True)
        fm = {"id": "ADR-0002", "status": status,
              "governs": entries if entries is not None else [governs(NEW, [OLD])]}
        if accepted_date is not None:
            fm["accepted_date"] = accepted_date
        self.put((self.adrs if tier == "active" else self.adrs / "archive") / HOST_FILE, fm)

    def test_accepted_positive_control_retires_in_every_reader(self):
        self.state("Accepted")
        self.assertEqual(self.answers(), (True, True, True))
        records, _ = self.architecture()
        self.assertTrue(records[NEW]["retires_in_force"])
        self.assertEqual(records[NEW]["retired_targets"], [OLD])
        self.assertFalse(records[OLD]["retires_in_force"])

    def test_deprecated_archived_host_keeps_the_retirement(self):
        self.state("Accepted")
        self.assertEqual(self.answers(), (True, True, True))
        self.state("Deprecated", "archive")
        self.assertEqual(self.answers(), (True, True, True))
        records, _ = self.architecture()
        self.assertTrue(records[NEW]["retires_in_force"])
        self.assertFalse(records[NEW]["live_host"])
        self.state("Deprecated", "archive", accepted_date=None)
        self.assertEqual(self.answers(), (False, False, False))

    def test_superseded_archived_host_keeps_the_retirement(self):
        self.state("Accepted")
        self.assertEqual(self.answers(), (True, True, True))
        self.state("Superseded", "archive")
        self.assertEqual(self.answers(), (True, True, True))
        self.state("Superseded", "archive", accepted_date=None)
        self.assertEqual(self.answers(), (False, False, False))

    def test_deprecated_host_in_the_active_tier_keeps_the_retirement(self):
        self.state("Accepted")
        self.assertEqual(self.answers(), (True, True, True))
        self.state("Deprecated", "active")
        self.assertEqual(self.answers(), (True, True, True))
        records, _ = self.architecture()
        self.assertFalse(records[NEW]["live_host"])
        self.state("Deprecated", "active", accepted_date=None)
        self.assertEqual(self.answers(), (False, False, False))

    def test_proposed_host_retires_nothing(self):
        self.state("Accepted")
        self.assertEqual(self.answers(), (True, True, True))
        self.state("Proposed", accepted_date=None)
        self.assertEqual(self.answers(), (False, False, False))

    def test_archived_accepted_file_refuses_with_each_readers_code(self):
        self.state("Accepted")
        self.assertEqual(self.answers(), (True, True, True))
        self.state("Accepted", "archive")
        self.assertEqual(self.refusal_codes(), [RECORD_CODE, RECORD_CODE, DISPOSITION_CODE])

    def test_malformed_archived_retires_refuses_with_each_readers_code(self):
        self.state("Accepted")
        self.assertEqual(self.answers(), (True, True, True))
        malformed = {
            "a scalar": [governs(NEW, OLD)],
            "a list of mappings": [governs(NEW, [{"handle": OLD}])],
            "a repeated retiring entry": [governs(NEW, [OLD]), governs(NEW, [OLD])],
        }
        for name, entries in malformed.items():
            with self.subTest(name):
                self.state("Deprecated", "archive", entries=entries)
                self.assertEqual(self.refusal_codes(), [RECORD_CODE, RECORD_CODE, DISPOSITION_CODE])
        with self.subTest("a repeated handle is idempotent, not malformed"):
            self.state("Deprecated", "archive", entries=[governs(NEW, [OLD, OLD])])
            self.assertEqual(self.answers(), (True, True, True))

    def every_lane(self):
        """Each lane's answer for OLD: the three migration readers, the summaries
        `retired_by`, and whether `implementation_approval.live_constraints` refuses OLD
        as retired. The approval lane reads committed files, so the fixture is committed."""
        import implementation_approval as approval
        import summaries_projection as sp
        sup.commit_all(self.root, "fixture")
        retired_by = {r["handle"]: r["retired_by"] for r in sp.collect_records(self.adrs)}[OLD]
        try:
            approval.live_constraints(self.root, [OLD])
            approval_retired = False
        except approval.Refused as refused:
            self.assertEqual(refused.code, "constraint-not-live-accepted")
            approval_retired = True
        return self.answers() + (retired_by, approval_retired)

    def test_a_repeated_retires_member_is_idempotent_in_every_lane(self):
        # One ADR naming a handle twice is idempotent (ADR-0097 part 6): every lane gives
        # the answer the single-member positive control gives, for an Accepted host and
        # for a Deprecated archived host; none refuses.
        retired = (True, True, True, ["ADR-0002"], True)
        cases = (("Accepted", "active"), ("Deprecated", "archive"))
        for status, tier in cases:
            with self.subTest(f"{status} {tier}: positive control [X]"):
                self.state(status, tier, entries=[governs(NEW, [OLD])])
                self.assertEqual(self.every_lane(), retired)
            with self.subTest(f"{status} {tier}: repeated [X, X]"):
                self.state(status, tier, entries=[governs(NEW, [OLD, OLD])])
                self.assertEqual(self.every_lane(), retired)
        with self.subTest("never-accepted control: [X, X] with no accepted_date"):
            self.state("Deprecated", "archive", accepted_date=None,
                       entries=[governs(NEW, [OLD, OLD])])
            self.assertEqual(self.every_lane(), (False, False, False, [], False))


class PolicyHostTests(ReaderMixin, unittest.TestCase):
    """A Lite-accepted policy host, built with the real policy writer."""

    def setUp(self):
        from test_retirement_edges_in_force import RealPolicyHostTests
        self.fixture = RealPolicyHostTests("test_accepted_control_then_archived_record_persists")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.docs = self.fixture.docs

    def test_resolving_record_persists_in_every_reader(self):
        path = self.fixture.accept()
        self.assertEqual(self.answers(), (True, True, True))
        archived = self.fixture.archive(path, "Deprecated")
        self.assertEqual(self.answers(), (True, True, True))
        archived.write_text(archived.read_text().replace("status: Deprecated", "status: Superseded", 1))
        self.assertEqual(self.answers(), (True, True, True))

    def test_no_record_with_a_null_date_has_no_effect(self):
        import decision_policy as dp
        self.fixture.accept()
        self.assertEqual(self.answers(), (True, True, True))
        shutil.rmtree(self.docs / "adrs/acceptances")
        accepted = next(self.docs.glob("adrs/ADR-0002-*.md"))
        accepted.unlink()
        subject = dp.propose(self.root, {
            "title": "Retire old", "body": "# Decision\nRetire.\n",
            "governs": [{"domain": "d", "scope": "s", "rule": "New.", "handle": "new-rule",
                         "retires": [OLD]}]}, origin="direct")["path"]
        path = self.docs / subject
        path.write_text(path.read_text().replace("status: Proposed", "status: Deprecated", 1))
        self.assertEqual(self.answers(), (False, False, False))
        (self.docs / "adrs/archive").mkdir(exist_ok=True)
        target = self.docs / "adrs/archive" / path.name
        target.write_text(path.read_text())
        path.unlink()
        self.assertEqual(self.answers(), (False, False, False))

    def test_lost_record_with_a_date_refuses_with_each_readers_code(self):
        path = self.fixture.accept()
        self.fixture.archive(path)
        self.assertEqual(self.answers(), (True, True, True))
        shutil.move(str(self.docs / "adrs/acceptances"), str(self.root / "lost"))
        self.assertEqual(self.refusal_codes(), [RECORD_CODE, RECORD_CODE, DISPOSITION_CODE])
        shutil.move(str(self.root / "lost"), str(self.docs / "adrs/acceptances"))
        self.assertEqual(self.answers(), (True, True, True))

    def test_a_file_that_disagrees_with_its_record_refuses(self):
        path = self.fixture.accept()
        archived = self.fixture.archive(path)
        good = archived.read_text()
        self.assertEqual(self.answers(), (True, True, True))
        archived.write_text(good.replace(OLD, "ADR-0001/other-rule"))
        self.assertEqual(self.refusal_codes(), [RECORD_CODE, RECORD_CODE, DISPOSITION_CODE])

    def test_the_architecture_fingerprints_bind_the_acceptance_record(self):
        path = self.fixture.accept()
        self.fixture.archive(path)
        _, fingerprints = self.architecture()
        record = next(item for item in fingerprints if item["path"].endswith("acceptances/ADR-0002.json"))
        self.assertEqual(record["sha256"], migration._digest(
            (self.docs / "adrs/acceptances/ADR-0002.json").read_bytes()))
        self.assertTrue(any(item["path"].endswith("archive/" + path.name) for item in fingerprints))
        paths = [item["path"] for item in fingerprints]
        self.assertEqual(len(paths), len(set(paths)))


class DisplacementReaderTests(unittest.TestCase):
    """`_validated_inputs`: the displacement reader of a selected source host."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import test_implementation_authority as fixtures
        self.fixture = fixtures.PublicationProof()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.close()
        self.root = self.fixture.root
        self.source = self.root / "docs/adrs/ADR-0110-source.md"
        self.archived = self.root / "docs/adrs/archive/ADR-0110-source.md"
        self.original = self.source.read_text()

    def facts(self, status, tier="active", *, accepted_date="2026-01-02"):
        text = re.sub(r"^accepted_date:.*\n", "", self.original, flags=re.MULTILINE)
        text = text.replace("status: Accepted", f"status: {status}")
        if accepted_date is not None:
            text = text.replace(f"status: {status}", f"status: {status}\naccepted_date: '{accepted_date}'", 1)
        self.source.unlink(missing_ok=True)
        self.archived.unlink(missing_ok=True)
        if tier == "archive":
            self.archived.parent.mkdir(exist_ok=True)
            self.archived.write_text(text)
        else:
            self.source.write_text(text)
        sup.commit_all(self.root, f"synthetic {status} source host in the {tier} tier")
        return migration._validated_inputs(self.root, self.fixture.proof)

    def assertRetires(self, facts, retired):
        targets = ["ADR-0109/old-rotation"] if retired else []
        self.assertEqual(facts["retired_handles"], targets)
        self.assertEqual([f["target_handle"] for f in facts["historical_displacements"]], targets)

    def test_deprecated_archived_host_keeps_its_displacement_edges(self):
        self.assertRetires(self.facts("Accepted"), True)
        self.assertRetires(self.facts("Deprecated", "archive"), True)
        self.assertRetires(self.facts("Deprecated", "archive", accepted_date=None), False)

    def test_superseded_archived_host_keeps_its_displacement_edges(self):
        self.assertRetires(self.facts("Accepted"), True)
        self.assertRetires(self.facts("Superseded", "archive"), True)
        self.assertRetires(self.facts("Superseded", "archive", accepted_date=None), False)

    def test_deprecated_host_in_the_active_tier_keeps_its_displacement_edges(self):
        self.assertRetires(self.facts("Accepted"), True)
        self.assertRetires(self.facts("Deprecated", "active"), True)
        self.assertRetires(self.facts("Deprecated", "active", accepted_date=None), False)

    def test_host_deprecated_from_proposed_keeps_no_displacement_edges(self):
        self.assertRetires(self.facts("Accepted"), True)
        self.assertRetires(self.facts("Proposed", accepted_date=None), False)
        self.assertRetires(self.facts("Deprecated", "active", accepted_date=None), False)
        self.assertRetires(self.facts("Deprecated", "archive", accepted_date=None), False)

    def test_no_publication_fact_names_the_reader_fields(self):
        facts = self.facts("Deprecated", "archive")
        self.assertRetires(facts, True)
        text = json.dumps(facts, sort_keys=True, default=str)
        for name in ("retires_in_force", "retired_targets", "persisted_edges", "persisted_retirement_edges"):
            self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
