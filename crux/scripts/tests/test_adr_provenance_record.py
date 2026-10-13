"""The ADR provenance record library (`crux/scripts/adr_provenance.py`).

Pins, one named test per claim:

  - the record round-trips through `render_record` / `parse_record`, and its keys match the
    published schema `crux/schemas/adr-provenance.schema.json` at every level, the recorded
    entry's fields included;
  - every refusal names its problem, each paired with a positive control that the same
    fixture minus the defect parses;
  - a recorded entry carries the governs sub-fields minus `handle`, and compares field by field
    the way the summaries projection normalizes a live row;
  - `effective_rules`: a guidance rule, a binding rule, a binding rule edited in-run, a rule
    deleted in-run, and promotions of each;
  - `open_request` lists every unpromoted in-run change in record order, deletions after the
    rules, and closes when all of it is promoted;
  - `join_standing` returns standing only for an ADR with a record, refuses a live handle the
    record does not name or whose entry moved in any field, and ignores an archived ADR's
    record;
  - `records_sha256` is order-free and moves when a record's bytes move;
  - the one directory reader refuses a stray file and a symlink, and reads an absent directory
    as empty.

Stdlib plus PyYAML (the uv lane). Fixtures live in temp dirs; nothing reads the live tree.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import adr_provenance as ap  # noqa: E402
import summaries_projection as sp  # noqa: E402

SCHEMA_PATH = SCRIPTS_DIR.parent / "schemas" / "adr-provenance.schema.json"
BASE = "0123456789abcdef0123456789abcdef01234567"


def _entry(rule: str, **fields) -> dict:
    return {"domain": "tests", "rule": rule, "scope": "crux/scripts", "provenance": "authored", **fields}


def _record() -> dict:
    return {
        "schema": "1",
        "adr": "ADR-0900",
        "run": {"book_id": "PB-0900", "run_id": "RUN-001",
                "snapshot": "docs/promptbooks/runs/PB-0900-x/run-RUN-001.yaml"},
        "base_commit": BASE,
        "base_path": "docs/adrs/ADR-0900-x.md",
        "base_sha256": "a" * 64,
        "rules": [
            {"handle": "ADR-0900/added-in-run", "standing": "guidance",
             "entry": _entry("Added during the run."), "base": None},
            {"handle": "ADR-0900/stood-unchanged", "standing": "binding",
             "entry": _entry("Stood at base."), "base": _entry("Stood at base.")},
            {"handle": "ADR-0900/stood-edited", "standing": "binding",
             "entry": _entry("Edited in the run."), "base": _entry("As it stood at base.")},
            {"handle": "ADR-0900/scope-widened", "standing": "binding",
             "entry": _entry("Scope widened.", scope="crux/scripts, tools/"),
             "base": _entry("Scope widened.")},
        ],
        "removed_in_run": [{"handle": "ADR-0900/dropped", "base": _entry("Dropped in-run.")}],
        "promotions": [],
    }


def _problems(record: dict) -> list[str]:
    """The problems `parse_record` reports for a record dumped without `render_record`'s check."""
    import yaml
    text = yaml.safe_dump(record, sort_keys=False)
    try:
        ap.parse_record(text)
    except ap.ProvenanceError as exc:
        return [p["problem"] for p in exc.problems]
    return []


class RecordGrammarTests(unittest.TestCase):
    def test_round_trip(self):
        record = _record()
        text = ap.render_record(record)
        self.assertEqual(ap.parse_record(text, name="ADR-0900.yaml"), record)
        self.assertEqual(ap.render_record(ap.parse_record(text)), text)

    def test_schema_keys_match_parser_keys(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(schema["required"]), set(ap._TOP_KEYS))
        self.assertEqual(set(schema["properties"]), set(ap._TOP_KEYS))
        props = schema["properties"]
        self.assertEqual(set(props["run"]["required"]), set(ap._RUN_KEYS))
        self.assertEqual(set(props["rules"]["items"]["required"]), set(ap._RULE_KEYS))
        self.assertEqual(set(props["removed_in_run"]["items"]["required"]), set(ap._REMOVED_KEYS))
        self.assertEqual(set(props["promotions"]["items"]["required"]), set(ap._PROMOTION_KEYS))
        self.assertEqual(props["rules"]["items"]["properties"]["standing"]["enum"], list(ap.STANDINGS))
        self.assertEqual(props["schema"]["const"], ap.SCHEMA)
        entry = schema["$defs"]["entry"]
        self.assertEqual(list(entry["properties"]), list(ap.ENTRY_FIELDS))
        self.assertEqual(entry["required"], ["rule"])
        self.assertIs(entry["additionalProperties"], False)

    def test_entry_fields_are_the_governs_sub_fields_minus_the_handle(self):
        self.assertEqual(set(ap.ENTRY_FIELDS), set(sp.GOVERNS_SUBFIELDS) - {"handle"})
        self.assertEqual(set(ap.COMPARED_FIELDS), set(ap.ENTRY_FIELDS) - {"provenance"})

    def test_comparable_normalizes_as_the_summaries_record_does(self):
        cases = [_entry("R."), {"rule": "R."}, _entry("R.", anchor="Body."),
                 _entry("R.", anchor=["one", "two"], retires=["ADR-0001/old"])]
        for raw in cases:
            with self.subTest(raw=raw):
                row = sp._record_from_entry({**raw, "handle": "ADR-0900/x"}, "ADR-0900", 900)
                self.assertEqual(ap.comparable(raw), {k: row[k] for k in ap.ENTRY_FIELDS})

    def test_positive_control_fixture_parses(self):
        self.assertEqual(_problems(_record()), [])

    def test_guidance_rule_with_a_base_refuses(self):
        record = _record()
        record["rules"][0]["base"] = _entry("x")
        self.assertTrue(any("guidance rule has no binding version" in p for p in _problems(record)))

    def test_binding_rule_without_a_base_refuses(self):
        record = _record()
        record["rules"][1]["base"] = None
        self.assertTrue(any("binding rule carries its base_commit entry" in p for p in _problems(record)))

    def test_entry_shape_refusals(self):
        cases = {
            "fields outside": ("entry", {**_entry("R."), "weight": "high"}),
            "non-empty text": ("entry", {"domain": "tests"}),
            "`retires` has the wrong type": ("entry", _entry("R.", retires="ADR-0001/old")),
            "`scope` has the wrong type": ("base", _entry("R.", scope=["crux/"])),
            "must be a mapping": ("entry", "Just a sentence."),
        }
        for needle, (field, value) in cases.items():
            with self.subTest(needle=needle):
                record = _record()
                record["rules"][2][field] = value
                self.assertTrue(any(needle in p for p in _problems(record)), _problems(record))
        removed = _record()
        removed["removed_in_run"][0]["base"] = {"scope": "x"}
        self.assertTrue(any("non-empty text" in p for p in _problems(removed)))

    def test_a_handle_that_is_both_a_rule_and_removed_refuses(self):
        self.assertEqual(_problems(_record()), [])                       # control
        record = _record()
        record["removed_in_run"].append({"handle": "ADR-0900/stood-edited", "base": _entry("Also gone.")})
        self.assertIn("a handle is either a rule or removed in-run, never both", _problems(record))

    def test_a_handle_named_twice_in_one_promotion_refuses(self):
        record = _record()
        record["promotions"] = [{"date": "2026-10-12", "instruction": "promote ADR-0900: rules 1",
                                 "handles": ["ADR-0900/added-in-run"], "body": False}]
        self.assertEqual(_problems(record), [])                          # control
        record["promotions"][0]["handles"] = ["ADR-0900/added-in-run", "ADR-0900/added-in-run"]
        self.assertEqual(_problems(record), ["promotion 1 names a handle twice"])

    def test_first_proposed_in_run_binds_nothing(self):
        record = _record()
        record["base_path"] = None
        record["base_sha256"] = None
        record["removed_in_run"] = []
        problems = _problems(record)
        self.assertTrue(any("binds nothing" in p for p in problems))
        # Positive control: the same record with every rule guidance parses.
        for rule in record["rules"]:
            rule["standing"], rule["base"] = "guidance", None
        self.assertEqual(_problems(record), [])

    def test_handle_of_another_adr_refuses(self):
        record = _record()
        record["rules"][0]["handle"] = "ADR-0901/added-in-run"
        self.assertTrue(any("must be ADR-0900/<slug>" in p for p in _problems(record)))

    def test_unknown_key_refuses(self):
        record = _record()
        record["standing_note"] = "x"
        self.assertTrue(any("record keys must be exactly" in p for p in _problems(record)))

    def test_misnamed_file_refuses(self):
        text = ap.render_record(_record())
        with self.assertRaises(ap.ProvenanceError) as caught:
            ap.parse_record(text, name="ADR-0901.yaml")
        self.assertIn("must be named ADR-0900.yaml", str(caught.exception))
        ap.parse_record(text, name="ADR-0900.yaml")  # positive control

    def test_duplicate_yaml_key_refuses(self):
        text = ap.render_record(_record()).replace("schema: '1'\n", "schema: '1'\nschema: '1'\n", 1)
        with self.assertRaises(ap.ProvenanceError):
            ap.parse_record(text)

    def test_unresolvable_commit_shape_refuses(self):
        record = _record()
        record["base_commit"] = "HEAD~1"
        self.assertTrue(any("base_commit must be a full lowercase commit id" in p for p in _problems(record)))

    def test_trailing_newline_refuses_in_every_anchored_field(self):
        # `$` also matches before a trailing newline; the published schema's ECMA `$` does not.
        self.assertEqual(_problems(_record()), [])  # positive control: the clean record parses

        def edit(path, value):
            record = _record()
            target = record
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            return record

        cases = {
            "handle": edit(("rules", 0, "handle"), "ADR-0900/added-in-run\n"),
            "base_commit": edit(("base_commit",), BASE + "\n"),
            "adr": edit(("adr",), "ADR-0900\n"),
            "book_id": edit(("run", "book_id"), "PB-0900\n"),
            "run_id": edit(("run", "run_id"), "RUN-001\n"),
            "base_sha256": edit(("base_sha256",), "a" * 64 + "\n"),
        }
        for field, record in cases.items():
            with self.subTest(field=field):
                self.assertTrue(_problems(record), f"{field} with a trailing newline parsed")

    def test_record_name_with_trailing_newline_is_not_a_record(self):
        self.assertEqual(ap.check_record_name("ADR-0900.yaml"), "ADR-0900")  # positive control
        self.assertIsNone(ap.check_record_name("ADR-0900.yaml\n"))

    def test_ids_take_ascii_digits_only(self):
        arabic_indic = "\u0660\u0669\u0660\u0660"     # four non-ASCII decimal digits
        self.assertIsNone(ap.check_record_name(f"ADR-{arabic_indic}.yaml"))
        record = _record()
        record["adr"] = f"ADR-{arabic_indic}"
        self.assertTrue(any("adr must be ADR-NNNN" in p for p in _problems(record)))

    def test_invalid_yaml_reports_its_type_and_line_and_quotes_no_text(self):
        with self.assertRaises(ap.ProvenanceError) as caught:
            ap.parse_record("schema: '1'\nadr: [unclosed SECRET-ISH-TEXT\n")
        message = str(caught.exception)
        self.assertIn("not valid YAML", message)
        self.assertIn("line", message)
        self.assertNotIn("SECRET-ISH-TEXT", message)


class PromotionTests(unittest.TestCase):
    def _promote(self, record, handles, body=False):
        record["promotions"].append({"date": "2026-10-13", "instruction": "promote ADR-0900: rules 1, 3",
                                     "handles": handles, "body": body})
        return record

    def test_effective_before_promotion(self):
        eff = ap.effective_rules(_record())
        self.assertEqual(eff["ADR-0900/added-in-run"],
                         {"standing": "guidance", "binding": None, "in_run_edit": ["added"],
                          "promoted": False, "removed": False})
        self.assertEqual(eff["ADR-0900/stood-unchanged"],
                         {"standing": "binding", "binding": _entry("Stood at base."), "in_run_edit": [],
                          "promoted": False, "removed": False})
        self.assertEqual(eff["ADR-0900/stood-edited"]["binding"], _entry("As it stood at base."))
        self.assertEqual(eff["ADR-0900/stood-edited"]["in_run_edit"], ["rule"])
        self.assertEqual(eff["ADR-0900/scope-widened"]["in_run_edit"], ["scope"])
        self.assertEqual(eff["ADR-0900/scope-widened"]["binding"]["scope"], "crux/scripts")
        self.assertEqual(eff["ADR-0900/dropped"],
                         {"standing": "binding", "binding": _entry("Dropped in-run."), "in_run_edit": ["deleted-in-run"],
                          "promoted": False, "removed": True})
        self.assertEqual(ap.removed_entries(_record()), [("ADR-0900/dropped", _entry("Dropped in-run."))])

    def test_effective_after_promotion(self):
        record = self._promote(_record(), ["ADR-0900/added-in-run", "ADR-0900/stood-edited",
                                           "ADR-0900/scope-widened", "ADR-0900/dropped"])
        record = ap.parse_record(ap.render_record(record))
        eff = ap.effective_rules(record)
        self.assertEqual(eff["ADR-0900/added-in-run"],
                         {"standing": "binding", "binding": _entry("Added during the run."), "in_run_edit": [],
                          "promoted": True, "removed": False})
        self.assertEqual(eff["ADR-0900/stood-edited"]["binding"]["rule"], "Edited in the run.")
        self.assertEqual(eff["ADR-0900/scope-widened"]["binding"]["scope"], "crux/scripts, tools/")
        self.assertEqual(eff["ADR-0900/dropped"]["standing"], None, "a promoted deletion has taken effect")
        self.assertEqual(ap.removed_entries(record), [])
        self.assertIsNone(ap.open_request(record))

    def test_a_provenance_only_change_is_no_in_run_edit(self):
        record = _record()
        record["rules"][1]["entry"]["provenance"] = "reconstructed"
        self.assertEqual(ap.effective_rules(record)["ADR-0900/stood-unchanged"]["in_run_edit"], [])
        record = self._promote(record, ["ADR-0900/stood-unchanged"])
        self.assertTrue(any("carries no in-run text" in p for p in _problems(record)))

    def test_promoting_a_rule_without_in_run_text_refuses(self):
        record = self._promote(_record(), ["ADR-0900/stood-unchanged"])
        self.assertTrue(any("carries no in-run text" in p for p in _problems(record)))

    def test_promoting_an_unknown_handle_refuses(self):
        record = self._promote(_record(), ["ADR-0900/never-was"])
        self.assertTrue(any("not a rule of this record" in p for p in _problems(record)))
        self.assertEqual(_problems(self._promote(_record(), ["ADR-0900/dropped"])), [])  # control

    def test_promoting_twice_refuses(self):
        record = self._promote(_record(), ["ADR-0900/added-in-run"])
        record = self._promote(record, ["ADR-0900/added-in-run"])
        self.assertTrue(any("already promoted" in p for p in _problems(record)))

    def test_promotion_needs_the_owners_words_and_a_date(self):
        record = self._promote(_record(), ["ADR-0900/added-in-run"])
        record["promotions"][0]["instruction"] = " "
        record["promotions"][0]["date"] = "13 October"
        problems = _problems(record)
        self.assertTrue(any("quote the owner's own words" in p for p in problems))
        self.assertTrue(any("date must be YYYY-MM-DD" in p for p in problems))

    def test_open_request_lists_in_run_changes_in_record_order(self):
        request = ap.open_request(_record())
        self.assertEqual([r["number"] for r in request["guidance"]], [1])
        self.assertEqual([(r["number"], r["edited"]) for r in request["edited"]], [(3, ["rule"]), (4, ["scope"])])
        self.assertEqual(request["edited"][0]["base"]["rule"], "As it stood at base.")
        self.assertEqual(request["edited"][0]["entry"]["rule"], "Edited in the run.")
        self.assertEqual(set(request["edited"][0]), {"number", "handle", "edited", "entry", "base"})
        self.assertEqual(request["edited"][1]["base"]["scope"], "crux/scripts")
        self.assertEqual([(r["number"], r["handle"], r["base"]["rule"]) for r in request["removed"]],
                         [(5, "ADR-0900/dropped", "Dropped in-run.")])
        partial = ap.parse_record(ap.render_record(self._promote(_record(), ["ADR-0900/added-in-run"])))
        self.assertEqual(ap.open_request(partial)["guidance"], [])
        self.assertEqual(len(ap.open_request(partial)["edited"]), 2)


class JoinTests(unittest.TestCase):
    def _rows(self, record):
        rows = [sp._record_from_entry({**r["entry"], "handle": r["handle"]}, "ADR-0900", 900)
                for r in record["rules"]]
        rows += [sp._record_from_entry({**base, "handle": h}, "ADR-0900", 900)
                 for h, base in ap.removed_entries(record)]
        return rows + [sp._record_from_entry(_entry("x", handle="ADR-0002/other"), "ADR-0002", 2)]

    def test_join_returns_standing_only_for_recorded_adrs(self):
        record = _record()
        joined = ap.join_standing({"ADR-0900": record}, self._rows(record))
        self.assertEqual(set(joined), {r["handle"] for r in record["rules"]} | {"ADR-0900/dropped"})
        self.assertNotIn("ADR-0002/other", joined)
        self.assertEqual(joined["ADR-0900/dropped"],
                         {"standing": "binding", "binding_rule": "Dropped in-run.", "in_run_edit": ["deleted-in-run"]})
        self.assertEqual(joined["ADR-0900/added-in-run"],
                         {"standing": "guidance", "binding_rule": None, "in_run_edit": ["added"]})

    def test_join_refuses_a_handle_the_record_does_not_name(self):
        record = _record()
        rows = self._rows(record) + [sp._record_from_entry(_entry("x", handle="ADR-0900/later"), "ADR-0900", 900)]
        with self.assertRaises(ap.ProvenanceError) as caught:
            ap.join_standing({"ADR-0900": record}, rows)
        self.assertIn("has no rule in its ADR's provenance record", str(caught.exception))

    def test_join_refuses_an_entry_that_moved_in_any_field(self):
        for field, value in (("rule", "Reworded after acceptance."), ("scope", "everything/"),
                             ("domain", "elsewhere"), ("provenance", "reconstructed")):
            with self.subTest(field=field):
                record = _record()
                rows = self._rows(record)
                rows[0] = dict(rows[0], **{field: value})
                with self.assertRaises(ap.ProvenanceError) as caught:
                    ap.join_standing({"ADR-0900": record}, rows)
                self.assertIn(f"differs from the entry its provenance record captured at acceptance (fields: {field})",
                              str(caught.exception))

    def test_join_ignores_a_record_with_no_live_rows(self):
        self.assertEqual(ap.join_standing({"ADR-0900": _record()}, []), {})


class DirectoryTests(unittest.TestCase):
    """`summaries_projection.provenance_entries` is the one reader of `adrs/provenance/`."""

    def test_absent_directory_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(sp.provenance_entries(Path(tmp)), [])

    def test_reads_records_and_digest_moves(self):
        with tempfile.TemporaryDirectory() as tmp:
            adrs = Path(tmp)
            (adrs / "provenance").mkdir()
            path = adrs / "provenance" / "ADR-0900.yaml"
            path.write_text(ap.render_record(_record()), encoding="utf-8")
            entries = sp.provenance_entries(adrs)
            self.assertEqual(list(ap.parse_records(entries)), ["ADR-0900"])
            before = ap.records_sha256(entries)
            self.assertEqual(before, ap.records_sha256(list(reversed(entries))))
            promoted = _record()
            promoted["promotions"].append({"date": "2026-10-13", "instruction": "promote ADR-0900: rule 1",
                                           "handles": ["ADR-0900/added-in-run"], "body": False})
            path.write_text(ap.render_record(promoted), encoding="utf-8")
            self.assertNotEqual(before, ap.records_sha256(sp.provenance_entries(adrs)))

    def test_stray_file_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            adrs = Path(tmp)
            (adrs / "provenance").mkdir()
            (adrs / "provenance" / "ADR-0900.yaml").write_text(ap.render_record(_record()), encoding="utf-8")
            self.assertEqual(list(ap.parse_records(sp.provenance_entries(adrs))), ["ADR-0900"])  # control
            (adrs / "provenance" / "notes.md").write_text("x", encoding="utf-8")
            with self.assertRaises(ap.ProvenanceError) as caught:
                ap.parse_records(sp.provenance_entries(adrs))
            self.assertIn("holds only ADR-NNNN.yaml records", str(caught.exception))

    @unittest.skipIf(os.name == "nt", "symlinks")
    def test_symlinked_record_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            adrs = Path(tmp)
            (adrs / "provenance").mkdir()
            target = adrs / "elsewhere.yaml"
            target.write_text(ap.render_record(_record()), encoding="utf-8")
            (adrs / "provenance" / "ADR-0900.yaml").symlink_to(target)
            with self.assertRaises(OSError) as caught:
                sp.provenance_entries(adrs)
            self.assertIn("not a regular record file", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
