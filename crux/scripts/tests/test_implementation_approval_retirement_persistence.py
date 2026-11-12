"""The implementation-approval readers keep a retirement whose host left Accepted
(rule:retirement-persists-after-its-host-leaves-accepted).

One fixture: ADR-0001 is Accepted and carries `alpha`; ADR-0002 retires it. Each
test that asserts a retirement persists first checks the Accepted positive control
and the never-accepted control on the same fixture. A refusal maps to
`constraint-record-refused`.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _council_gate_support as sup  # noqa: E402
import implementation_approval as approval  # noqa: E402

TARGET = "ADR-0001/alpha"
HOST = "ADR-0002"
FILE = "ADR-0002-retire-alpha.md"
VIEW = {"historical_handles": {}, "retired_handles": [], "amendments": {}}


def governs(handle, extra=None):
    return {"handle": handle, "domain": "d", "rule": f"the {handle} rule",
            "scope": "crux/scripts", "provenance": "authored", **(extra or {})}


class RetirementPersistenceFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = sup.init_repo(Path(self.temp.name) / "repo")
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: docs\n')
        self.adrs = self.root / "docs/adrs"
        self.adrs.mkdir(parents=True)
        self.write(self.adrs / "ADR-0001-base.md",
                   {"id": "ADR-0001", "status": "Accepted", "accepted_date": "2026-01-01",
                    "governs": [governs(TARGET)]})
        sup.commit_all(self.root, "base")

    @staticmethod
    def write(path, fm):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump(fm) + "---\n")

    def host(self, status, *, tier="active", accepted_date="2026-01-02", retires=None,
             governs_value=None, **extra):
        """Replace the host with one fixture state and commit it."""
        for old in (self.adrs / FILE, self.adrs / "archive" / FILE):
            old.unlink(missing_ok=True)
        entry = governs(f"{HOST}/new-rule", {"retires": [TARGET] if retires is None else retires})
        fm = {"id": HOST, "status": status,
              "governs": [entry] if governs_value is None else governs_value, **extra}
        if accepted_date is not None:
            fm["accepted_date"] = accepted_date
        path = self.adrs / FILE if tier == "active" else self.adrs / "archive" / FILE
        self.write(path, fm)
        sup.commit_all(self.root, f"host {status} {tier}")

    def raw_retired(self):
        try:
            approval._raw_live_constraints(self.root, [TARGET])
        except approval.Refused as exc:
            self.assertEqual(exc.code, "constraint-not-live-accepted")
            return True
        return False

    def undeclared_retired(self):
        found = approval.undeclared_governing_constraints(self.root, ["crux/scripts"], [], VIEW)
        return TARGET not in found["overlapping"]

    def assertRetired(self, expected, label):
        with self.subTest(label):
            self.assertIs(self.raw_retired(), expected)
            self.assertIs(self.undeclared_retired(), expected)

    def assertRefused(self, label):
        for call in (lambda: approval._raw_live_constraints(self.root, [TARGET]),
                     lambda: approval.undeclared_governing_constraints(
                         self.root, ["crux/scripts"], [], VIEW)):
            with self.subTest(label), self.assertRaises(approval.Refused) as caught:
                call()
            self.assertEqual(caught.exception.code, "constraint-record-refused")

    def controls(self):
        """The Accepted positive control and the never-accepted control, then the
        caller's variant on the same fixture."""
        self.host("Accepted")
        self.assertRetired(True, "positive control: Accepted host retires")
        self.host("Deprecated", accepted_date=None, tier="archive")
        self.assertRetired(False, "never-accepted control: no accepted_date")


class PreRecordHostTests(RetirementPersistenceFixture):
    def test_deprecated_and_archived_keeps_the_target_retired(self):
        self.controls()
        self.host("Deprecated", tier="archive")
        self.assertRetired(True, "deprecated archived")

    def test_superseded_and_archived_keeps_the_target_retired(self):
        self.controls()
        self.host("Superseded", tier="archive")
        self.assertRetired(True, "superseded archived")

    def test_deprecated_still_in_the_active_tier_keeps_the_target_retired(self):
        self.controls()
        self.host("Deprecated", tier="active")
        self.assertRetired(True, "deprecated active")

    def test_proposed_to_deprecated_never_retires(self):
        self.host("Proposed", accepted_date=None)
        self.assertRetired(False, "proposed")
        self.host("Deprecated", accepted_date=None, tier="active")
        self.assertRetired(False, "deprecated active, never accepted")
        self.host("Accepted")
        self.assertRetired(True, "positive control")

    def test_archived_accepted_file_refuses(self):
        self.host("Accepted", tier="archive")
        self.assertRefused("archived Accepted")

    def test_malformed_archived_retires_refuses(self):
        self.controls()
        bad_entry = governs(f"{HOST}/new-rule")
        cases = {
            "scalar retires": dict(retires=TARGET),
            "list of mappings": dict(retires=[{"handle": TARGET}]),
            "duplicate handle": dict(governs_value=[
                governs(f"{HOST}/new-rule", {"retires": [TARGET]}),
                governs(f"{HOST}/new-rule", {"retires": [TARGET]})]),
            "governs not a list": dict(governs_value={"handle": bad_entry["handle"]}),
        }
        for label, kwargs in cases.items():
            self.host("Deprecated", tier="archive", **kwargs)
            self.assertRefused(label)


class PolicyHostTests(RetirementPersistenceFixture):
    """A policy host carries `acceptance_format`; the resolver is stubbed here
    and runs for real in test_retirement_edges_in_force.py."""

    POLICY = {"acceptance_format": "crux.adr-acceptance.v1"}

    def receipt(self):
        entry = governs(f"{HOST}/new-rule", {"retires": [TARGET]})
        fm = {"id": HOST, "status": "Accepted", "governs": [entry]}
        return {"adr": HOST, "subject": f"adrs/{FILE}",
                "accepted_text": "---\n" + yaml.safe_dump(fm) + "---\nBody\n"}

    def add_record(self):
        record = self.root / f"docs/adrs/acceptances/{HOST}.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text("{}\n")
        sup.commit_all(self.root, "record")

    def resolver(self):
        def resolve(adr, *, proof_reader, exists):
            proof_reader(f"adrs/acceptances/{adr}.json")
            return f"adrs/acceptances/{adr}.json", self.receipt()
        return patch("decision_policy.resolve_acceptance", resolve)

    def test_resolving_record_keeps_the_target_retired(self):
        self.host("Accepted", **self.POLICY)
        self.assertRetired(True, "positive control: Accepted policy host")
        self.host("Deprecated", tier="archive", accepted_date=None, **self.POLICY)
        self.assertRetired(False, "never-accepted control: no record, no date")
        self.host("Deprecated", tier="archive", **self.POLICY)
        self.add_record()
        with self.resolver():
            self.assertRetired(True, "deprecated archived policy host with a record")

    def test_no_record_and_no_accepted_date_has_no_effect(self):
        self.host("Accepted", **self.POLICY)
        self.assertRetired(True, "positive control")
        self.host("Deprecated", tier="archive", accepted_date=None, **self.POLICY)
        self.assertRetired(False, "no record, accepted_date null")

    def test_lost_record_with_accepted_date_refuses(self):
        self.host("Accepted", **self.POLICY)
        self.assertRetired(True, "positive control")
        self.host("Deprecated", tier="archive", accepted_date=None, **self.POLICY)
        self.assertRetired(False, "never-accepted control")
        self.host("Deprecated", tier="archive", **self.POLICY)
        self.assertRefused("record lost, accepted_date set")


if __name__ == "__main__":
    unittest.main()
