"""The shared retirement predicate, `retirement_edges_in_force`
(rule:retirement-persists-after-its-host-leaves-accepted).

Each test that asserts a retirement persists pairs it with the Accepted
positive control and the never-accepted control on the same fixture.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import summaries_projection as sp  # noqa: E402
from cycle_workflow import digest  # noqa: E402

FILE = "ADR-0002-retire-old.md"
HOST = "ADR-0002"


def host_fm(status, *, accepted_date="2026-01-02", retires=("ADR-0001/old-rule",), **extra):
    fm = {"id": HOST, "status": status,
          "governs": [{"domain": "d", "rule": "New.", "scope": "s",
                       "handle": f"{HOST}/new-rule", "provenance": "authored",
                       "retires": list(retires)}]}
    if accepted_date is not None:
        fm["accepted_date"] = accepted_date
    fm.update(extra)
    return fm


def no_records():
    return (lambda path: (_ for _ in ()).throw(FileNotFoundError(path)),
            lambda path: False)


def edges(fm, tier="active", filename=FILE, reader=None):
    proof_reader, exists = reader or no_records()
    return sp.retirement_edges_in_force(fm, filename, tier,
                                        proof_reader=proof_reader, exists=exists)


EDGE = sp.RetirementEdge(HOST, f"{HOST}/new-rule", "ADR-0001/old-rule")


class PrePolicyHostTests(unittest.TestCase):
    def test_accepted_positive_control_retires(self):
        self.assertEqual(edges(host_fm("Accepted")), (EDGE,))

    def test_deprecated_once_accepted_persists_in_archive(self):
        self.assertEqual(edges(host_fm("Deprecated"), "archive"), (EDGE,))
        self.assertEqual(edges(host_fm("Accepted")), (EDGE,))
        self.assertEqual(edges(host_fm("Deprecated", accepted_date=None), "archive"), ())

    def test_superseded_once_accepted_persists(self):
        self.assertEqual(edges(host_fm("Superseded"), "archive"), (EDGE,))
        self.assertEqual(edges(host_fm("Accepted")), (EDGE,))
        self.assertEqual(edges(host_fm("Superseded", accepted_date=None), "archive"), ())

    def test_deprecated_still_in_active_tier_persists(self):
        self.assertEqual(edges(host_fm("Deprecated"), "active"), (EDGE,))
        self.assertEqual(edges(host_fm("Deprecated", accepted_date=""), "active"), ())

    def test_proposed_and_absent_status_give_none(self):
        self.assertEqual(edges(host_fm("Proposed")), ())
        fm = host_fm("Accepted")
        del fm["status"]
        self.assertEqual(edges(fm), ())

    def test_archived_non_terminal_status_refuses(self):
        for status in ("Accepted", "Proposed", None):
            with self.subTest(status=status), self.assertRaises(sp.RetirementPersistenceRefusal):
                edges(host_fm(status), "archive")

    def test_malformed_retires_refuses(self):
        for bad in ("ADR-0001/old-rule", [{"h": 1}], []):
            fm = host_fm("Deprecated")
            fm["governs"][0]["retires"] = bad
            with self.subTest(bad=bad), self.assertRaises(sp.RetirementPersistenceRefusal):
                edges(fm, "archive")
        # A repeated member is idempotent (ADR-0097 part 6), not malformed.
        fm = host_fm("Deprecated")
        fm["governs"][0]["retires"] = fm["governs"][0]["retires"] * 2
        self.assertEqual(edges(fm, "archive"), edges(host_fm("Deprecated"), "archive"))

    def test_duplicate_retiring_handle_and_foreign_anchor_refuse(self):
        fm = host_fm("Deprecated")
        fm["governs"].append(dict(fm["governs"][0]))
        with self.assertRaises(sp.RetirementPersistenceRefusal):
            edges(fm, "archive")
        fm = host_fm("Deprecated")
        fm["governs"][0]["handle"] = "ADR-0009/new-rule"
        with self.assertRaises(sp.RetirementPersistenceRefusal):
            edges(fm, "archive")

    def test_non_list_governs_refuses_and_absent_governs_gives_none(self):
        fm = host_fm("Deprecated")
        fm["governs"] = {"handle": "x"}
        with self.assertRaises(sp.RetirementPersistenceRefusal):
            edges(fm, "archive")
        fm = host_fm("Deprecated")
        del fm["governs"]
        self.assertEqual(edges(fm, "archive"), ())

    def test_entries_without_retires_are_untouched(self):
        fm = host_fm("Deprecated")
        fm["governs"].append("an older shape")
        fm["governs"].append({"rule": "no handle"})
        self.assertEqual(edges(fm, "archive"), (EDGE,))

    def test_bad_filename_refuses(self):
        with self.assertRaises(sp.RetirementPersistenceRefusal):
            edges(host_fm("Accepted"), filename="../x.md")

    def test_edges_are_frozen_sorted_and_deduplicated(self):
        fm = host_fm("Accepted", retires=("ADR-0001/b", "ADR-0001/a"))
        result = edges(fm)
        self.assertIsInstance(result, tuple)
        self.assertEqual([e.target for e in result], ["ADR-0001/a", "ADR-0001/b"])
        with self.assertRaises(AttributeError):
            result[0].target = "x"


class PolicyHostCrafted(unittest.TestCase):
    """Policy-host outcomes with a stubbed resolver; the real resolver runs in
    `RealPolicyHostTests`."""

    def receipt(self, *, adr=HOST, subject=f"adrs/{FILE}", retires=("ADR-0001/old-rule",),
                text=None):
        fm = host_fm("Accepted", retires=retires)
        import yaml
        accepted = text if text is not None else "---\n" + yaml.safe_dump(fm) + "---\nBody\n"
        return {"adr": adr, "subject": subject, "accepted_text": accepted}

    def run_with(self, fm, receipt=None, *, record=True, error=None):
        def exists(path):
            return record and path == f"adrs/acceptances/{HOST}.json"

        def resolve(adr, *, proof_reader, exists):
            if error:
                raise error
            if not record:
                raise FileNotFoundError(adr)
            return f"adrs/acceptances/{adr}.json", receipt
        with patch("decision_policy.resolve_acceptance", resolve):
            return edges(fm, "archive", reader=(lambda p: b"", exists))

    def policy_fm(self, **kw):
        return host_fm("Deprecated", acceptance_format="crux.adr-acceptance.v1", **kw)

    def test_resolving_record_persists_with_controls(self):
        self.assertEqual(self.run_with(self.policy_fm(), self.receipt()), (EDGE,))
        self.assertEqual(edges(host_fm("Accepted", acceptance_format="crux.adr-acceptance.v1")), (EDGE,))
        self.assertEqual(self.run_with(self.policy_fm(accepted_date=None), record=False), ())

    def test_no_retires_and_no_record_gives_false(self):
        self.assertEqual(self.run_with(self.policy_fm(retires=()) | {"governs": []}, record=False), ())

    def test_refusals(self):
        cases = {
            "record missing with date": dict(fm=self.policy_fm(), record=False),
            "record unresolvable": dict(fm=self.policy_fm(), error=ValueError("bad")),
            "record names another ADR": dict(fm=self.policy_fm(), receipt=self.receipt(adr="ADR-0003")),
            "record names another file": dict(fm=self.policy_fm(), receipt=self.receipt(subject="adrs/ADR-0002-x.md")),
            "accepted_text does not parse": dict(fm=self.policy_fm(), receipt=self.receipt(text="no frontmatter")),
            "map differs": dict(fm=self.policy_fm(), receipt=self.receipt(retires=("ADR-0001/other",))),
            "reordered": dict(fm=self.policy_fm(retires=("ADR-0001/a", "ADR-0001/b")),
                              receipt=self.receipt(retires=("ADR-0001/b", "ADR-0001/a"))),
            "file lost retires": dict(fm=self.policy_fm() | {"governs": []}, receipt=self.receipt()),
            "record with null date": dict(fm=self.policy_fm(accepted_date=None), receipt=self.receipt()),
        }
        for name, case in cases.items():
            with self.subTest(name), self.assertRaises(sp.RetirementPersistenceRefusal):
                self.run_with(case["fm"], case.get("receipt"), record=case.get("record", True),
                              error=case.get("error"))

    def test_malformed_accepted_text_governs_refuses(self):
        import yaml
        for governs in ("x", ["not a mapping"], [{"rule": "no handle"}],
                        [{"handle": f"{HOST}/a"}, {"handle": f"{HOST}/a"}]):
            text = "---\n" + yaml.safe_dump({"id": HOST, "governs": governs}) + "---\n"
            with self.subTest(governs=governs), self.assertRaises(sp.RetirementPersistenceRefusal):
                self.run_with(self.policy_fm(), self.receipt(text=text))

    def test_proposal_record_alone_never_refuses(self):
        def exists(path):
            return path == f"adrs/proposals/{HOST}.json"
        fm = host_fm("Deprecated", accepted_date=None)
        self.assertEqual(edges(fm, "archive", reader=(lambda p: b"", exists)), ())


class RealPolicyHostTests(unittest.TestCase):
    """A real Lite-accepted policy host, deprecated and archived: the receipt
    binds neither the subject's current path nor its bytes (IDR nit
    anthropic_top:F11), so the resolving record persists the retirement."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.docs = self.root / "bionic"
        (self.docs / "adrs").mkdir(parents=True)
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: bionic\n')
        (self.docs / "manifest.yml").write_text(
            'schema_version: "5"\nconcerns_enabled: [adrs]\nadr:\n  next_number: 2\n')
        (self.docs / "objectives.md").write_text("Use proportional review with durable history.")
        (self.docs / "adrs/ADR-0001-old.md").write_text(
            "---\nid: ADR-0001\ntitle: Old\nstatus: Accepted\naccepted_date: 2026-01-01\n"
            "governs:\n- domain: d\n  rule: Old.\n  scope: s\n  handle: ADR-0001/old-rule\n"
            "  provenance: authored\n---\n\n# Old\n")
        for args in (("init", "-q"), ("config", "user.email", "t@example.invalid"),
                     ("config", "user.name", "T")):
            self.git(*args)
        from council_policy import initialize
        initialize(self.root, "lite", selection="Explicit test setup selects Lite")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, check=True).stdout.decode()

    def vote(self, request, context, decision):
        body = {"decision": decision, "reasoning": "Check completed.", "findings": []}
        return {"tool": "collaboration.spawn_agent", "input": request["dispatch"],
                "result": {"task_name": context},
                "final": f"Message Type: FINAL_ANSWER\nTask name: /root\nSender: {context}\n"
                         "Payload:\n" + json.dumps(body)}

    def accept(self):
        import decision_policy as dp
        from council_native import ingest, prepare
        from council_policy import disposition
        subject = dp.propose(self.root, {
            "title": "Retire old", "body": "# Decision\nRetire the old rule.\n",
            "governs": [{"domain": "d", "scope": "s", "rule": "New.", "handle": "new-rule",
                         "retires": ["ADR-0001/old-rule"]}]}, origin="direct")["path"]
        args = {"harness": "codex", "author_context": "/root/author"}
        first = prepare(self.root, "adr", subject, "Review", **args)
        ingest(self.root, first["request"], self.vote(first, "/root/challenger", "REQUEST_CHANGES"))
        final = prepare(self.root, "adr", subject, "Review", phase="final",
                        attempt_path=first["attempt"], response="Architect response", **args)
        reviewed = ingest(self.root, final["request"], self.vote(final, "/root/final", "APPROVE"))
        disposition(self.root, reviewed["record"], {
            "agrees": True, "subject_sha256": digest((self.docs / subject).read_bytes()),
            "rationale": "Proceed", "dissent": []})
        dp.accept(self.root, subject, reviewed["record"], human_approval="Owner accepts this")
        return self.docs / subject

    def archive(self, path, status="Deprecated"):
        text = path.read_text().replace("status: Accepted", f"status: {status}", 1)
        (self.docs / "adrs/archive").mkdir(exist_ok=True)
        target = self.docs / "adrs/archive" / path.name
        target.write_text(text)
        path.unlink()
        return target

    def test_accepted_control_then_archived_record_persists(self):
        path = self.accept()
        fm = sp.read_frontmatter(path.read_text())
        reader = sp._docs_reader(self.docs / "adrs", None)
        accepted = sp.retirement_edges_in_force(fm, path.name, "active",
                                                proof_reader=reader[0], exists=reader[1])
        self.assertEqual([e.target for e in accepted], ["ADR-0001/old-rule"])
        self.assertEqual(sp.persisted_retirement_edges(self.docs / "adrs"), ())
        archived = self.archive(path)
        persisted = sp.persisted_retirement_edges(self.docs / "adrs")
        self.assertEqual(persisted, accepted)
        self.assertEqual(persisted[0].source_adr, fm["id"])

    def test_archived_superseded_record_persists(self):
        path = self.accept()
        self.archive(path, "Superseded")
        self.assertEqual([e.target for e in sp.persisted_retirement_edges(self.docs / "adrs")],
                         ["ADR-0001/old-rule"])

    def test_archived_edit_or_lost_record_refuses(self):
        path = self.accept()
        archived = self.archive(path)
        good = archived.read_text()
        archived.write_text(good.replace("ADR-0001/old-rule", "ADR-0001/other-rule"))
        with self.assertRaises(sp.RetirementPersistenceRefusal):
            sp.persisted_retirement_edges(self.docs / "adrs")
        archived.write_text(good)
        acceptances = self.docs / "adrs/acceptances"
        shutil.move(str(acceptances), str(self.root / "lost"))
        with self.assertRaises(sp.RetirementPersistenceRefusal) as caught:
            sp.persisted_retirement_edges(self.docs / "adrs")
        self.assertIn("restore the acceptance record", str(caught.exception))

    def test_never_accepted_policy_host_gives_no_effect(self):
        import decision_policy as dp
        subject = dp.propose(self.root, {
            "title": "Retire old", "body": "# Decision\nRetire.\n",
            "governs": [{"domain": "d", "scope": "s", "rule": "New.", "handle": "new-rule",
                         "retires": ["ADR-0001/old-rule"]}]}, origin="direct")["path"]
        path = self.docs / subject
        text = path.read_text().replace("status: Proposed", "status: Deprecated", 1)
        (self.docs / "adrs/archive").mkdir(exist_ok=True)
        (self.docs / "adrs/archive" / path.name).write_text(text)
        path.unlink()
        self.assertEqual(sp.persisted_retirement_edges(self.docs / "adrs"), ())


if __name__ == "__main__":
    unittest.main()
