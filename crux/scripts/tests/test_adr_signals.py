"""Regression tests for `adr-signals.py`, the decision review's eight signals.

Every case reads the miniature repo roots under
`crux/scripts/tests/fixtures/adr-signals-corpus/` and nothing else: `trips/`
carries a fixture that trips each signal, `quiet/` one that does not. No case
reads the live tree, the README, or any other dev-only surface, so the suite
passes unchanged against the crux-only staged artifact.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "crux" / "scripts" / "adr-signals.py"
CORPUS = Path(__file__).resolve().parent / "fixtures" / "adr-signals-corpus"
TODAY = dt.date(2026, 2, 20)

# The materialized roots, filled in by setUpModule.
_WORKSPACE: tempfile.TemporaryDirectory | None = None
TRIPS: Path
QUIET: Path


def setUpModule() -> None:
    """Materialize both fixture roots into a temp directory.

    `adr-signals.py` reads the forge log at `<root>/.claude/skills/forge-log.md`,
    and `tools/sync_stage.py` strips every `.claude` directory from the staged
    public artifact. A committed `.claude/` under the corpus would exist in the
    dev checkout and vanish at release, so the corpus ships each root's forge
    log as `forge-log.src.md` and this hook writes it into place.
    """
    global _WORKSPACE, TRIPS, QUIET
    _WORKSPACE = tempfile.TemporaryDirectory(prefix="adr-signals-corpus-")
    base = Path(_WORKSPACE.name)
    for name in ("trips", "quiet"):
        root = base / name
        shutil.copytree(CORPUS / name, root)
        skills = root / ".claude" / "skills"
        skills.mkdir(parents=True)
        (skills / "forge-log.md").write_text(
            (root / "forge-log.src.md").read_text(encoding="utf-8"), encoding="utf-8")
        (root / "forge-log.src.md").unlink()
    TRIPS = base / "trips"
    QUIET = base / "quiet"


def tearDownModule() -> None:
    if _WORKSPACE is not None:
        _WORKSPACE.cleanup()

RECORD_MEMBERS = {"signal", "verdict", "value", "basis", "filter"}
BANNED_MEMBERS = ("severity", "recommendation")


def _load_module():
    spec = importlib.util.spec_from_file_location("adr_signals", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sig = _load_module()


def envelope(root: Path) -> dict:
    env, errors = sig.build(root, TODAY)
    assert errors == [], f"fixture root {root.name} produced errors: {errors}"
    return env


def record(root: Path, name: str) -> dict:
    for rec in envelope(root)["signals"]:
        if rec["signal"] == name:
            return rec
    raise AssertionError(f"no {name!r} record in the {root.name} envelope")


def assert_envelope_contract(tc: unittest.TestCase, env: dict) -> None:
    """Every record carries exactly the five members and neither banned key.

    Its teeth are proved by `EnvelopeContractControlTests` below, which feeds
    the same helper a hand-built record carrying `severity`.
    """
    for rec in env["signals"]:
        tc.assertEqual(set(rec), RECORD_MEMBERS, f"{rec.get('signal')} member set")
        for banned in BANNED_MEMBERS:
            tc.assertNotIn(banned, rec, f"{rec.get('signal')} must carry no {banned}")
        tc.assertIn(rec["verdict"], {"computed", "unmeasurable"})
        if rec["verdict"] == "unmeasurable":
            tc.assertIsNone(rec["value"])
            tc.assertIsNotNone(rec["filter"], "an unmeasurable record names the missing grammar")


class AmendmentFanInTests(unittest.TestCase):
    def test_positive_active_amender_and_superseder_both_count(self):
        value = record(TRIPS, "amendment_fan_in")["value"]
        # ADR-0002 amends ADR-0001; ADR-0003 supersedes it.
        self.assertEqual(value["ADR-0001"], 2)

    def test_negative_a_tree_with_no_amendments_reads_zero_throughout(self):
        rec = record(QUIET, "amendment_fan_in")
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], {"ADR-0001": 0, "ADR-0002": 0})
        # Positive control for the zeros: the same signal over `trips` is
        # non-zero, so a zero here is the fixture and not a dead code path.
        self.assertEqual(record(TRIPS, "amendment_fan_in")["value"]["ADR-0001"], 2)

    def test_archived_adr_is_excluded_from_the_keyset_and_from_the_counts(self):
        archived = TRIPS / "bionic" / "adrs" / "archive" / "ADR-0009-archived-thing.md"
        # Positive control 1: the archived file exists and DOES name ADR-0001,
        # so the absence below is the archive filter and not a missing fixture.
        self.assertTrue(archived.is_file())
        self.assertIn("amends: [ADR-0001]", archived.read_text(encoding="utf-8"))
        env = envelope(TRIPS)
        value = env["signals"][0]["value"]
        self.assertNotIn("ADR-0009", value)
        # Positive control 2: the two ACTIVE amenders are counted, so the count
        # is 2 rather than the 3 an unfiltered walk would produce.
        self.assertEqual(value["ADR-0001"], 2)
        self.assertEqual(env["active_adrs"], 3)


class CarveOutCountTests(unittest.TestCase):
    def test_positive_deduped_manifest_roster_plus_literal_names(self):
        rec = record(TRIPS, "carve_out_count")
        # `adr.governs_exempt: [ADR-0003]` and the doctrine `## Exempt ADRs`
        # roster both name ADR-0003 and are ONE surface, so they contribute 1,
        # not 2; `EXEMPT_THINGS` contributes its two names.
        self.assertEqual(rec["value"], 3)
        self.assertIn("EXEMPT_THINGS", rec["basis"])
        self.assertIn("counted ONCE", rec["filter"])

    def test_negative_a_tree_with_no_carve_outs_reads_zero(self):
        rec = record(QUIET, "carve_out_count")
        self.assertEqual(rec["value"], 0)
        # Positive control: `quiet/crux/scripts/plain.py` DOES carry a
        # module-level frozenset literal — it is merely not named `EXEMPT*`.
        # A name filter that stopped filtering would read 2 here, not 0.
        plain = QUIET / "crux" / "scripts" / "plain.py"
        self.assertIn("frozenset({\"alpha\", \"beta\"})", plain.read_text(encoding="utf-8"))
        self.assertEqual(record(TRIPS, "carve_out_count")["value"], 3)


class DownstreamInstallShapeTests(unittest.TestCase):
    """The whole envelope over a root that is NOT a crux development checkout.

    Both corpus roots carry a `crux/scripts/` marker, so every other
    full-envelope case in this file is a DEV-repo run. The shape a downstream
    install actually has — a `bionic/` tree and no `crux/` directory at all —
    was never exercised end to end, so nothing pinned that the signals degrade
    by NAMING what is absent instead of inventing a value or crashing.
    """

    def _downstream(self) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-downstream-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        (docs / "adrs").mkdir(parents=True)
        (docs / "journal").mkdir(parents=True)
        (root / ".bionic.yml").write_text(
            'config_version: "1"\ndocs_dir: bionic\n', encoding="utf-8")
        (docs / "manifest.yml").write_text(
            'schema_version: "5"\nadr:\n  next_number: 2\n'
            'journal:\n  friction_line_from: "2026-02-01"\n', encoding="utf-8")
        (docs / "adrs" / "ADR-0001-a-downstream-decision.md").write_text(
            "---\nid: ADR-0001\nstatus: Accepted\ntitle: A downstream decision\n"
            "date: 2026-02-02\namends: []\nsupersedes: []\n---\n\n# A downstream decision\n",
            encoding="utf-8")
        (docs / "log.md").write_text("# log\n", encoding="utf-8")
        return root

    def test_no_crux_directory_exists_in_the_fixture(self):
        """Positive control: the fixture really is the downstream shape."""
        root = self._downstream()
        self.assertFalse((root / "crux").exists())
        self.assertFalse((root / "CLAUDE.md").exists())

    def test_the_envelope_still_carries_every_signal(self):
        env, _ = sig.build(self._downstream(), TODAY)
        names = [r["signal"] for r in env["signals"]]
        self.assertEqual(len(names), len(set(names)))
        for expected in ("amendment_fan_in", "carve_out_count", "paper_only",
                         "dormancy_days", "friction_citations", "release_cadence",
                         "schema_growth", "gate_count"):
            self.assertIn(expected, names)

    def test_every_record_keeps_the_envelope_contract(self):
        env, _ = sig.build(self._downstream(), TODAY)
        assert_envelope_contract(self, env)

    def test_absent_dev_surfaces_are_named_never_invented(self):
        """`unmeasurable` with a filter, never a fabricated zero."""
        env, _ = sig.build(self._downstream(), TODAY)
        by = {r["signal"]: r for r in env["signals"]}
        for name in ("release_cadence", "gate_count"):
            self.assertEqual(by[name]["verdict"], "unmeasurable", name)
            self.assertIsNone(by[name]["value"], name)
            self.assertIsNotNone(by[name]["filter"], name)

    def test_a_missing_doctrine_index_is_an_error_not_a_silent_zero(self):
        """The absence is REPORTED. A downstream tree without doctrine says so."""
        _, errors = sig.build(self._downstream(), TODAY)
        self.assertTrue(errors, "a downstream root with no doctrine index must report it")
        self.assertTrue(any("doctrine" in e.get("input", "") or "doctrine" in e.get("problem", "")
                            for e in errors), errors)


class FrictionMeasuredZeroTests(unittest.TestCase):
    """A recorded adoption date plus a post-adoption entry with NO friction.

    This is the lane that separates "nobody recorded friction" from "nobody has
    measured". `signal_friction_citations` returns `unmeasurable` when no entry
    is dated at or after the boundary, so the corpus roots exercise
    `unmeasurable` (quiet) and a positive count (trips) but never a MEASURED
    ZERO. A zero that cannot be distinguished from an unmeasured window is the
    exact ambiguity the adoption boundary exists to remove.
    """

    def _tree(self, journal_body: str) -> tuple[Path, Path]:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-zero-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        (docs / "manifest.yml").write_text(
            'schema_version: "5"\njournal:\n  friction_line_from: "2026-02-01"\n',
            encoding="utf-8")
        (docs / "journal" / "2026-02.md").write_text(journal_body, encoding="utf-8")
        (docs / "log.md").write_text("# log\n", encoding="utf-8")
        return root, docs

    NO_FRICTION = ("# 2026-02\n\n## [2026-02-10 09:00] implementation | a unit of work\n\n"
                   "Did the thing; nothing got in the way.\n")
    WITH_FRICTION = ("# 2026-02\n\n## [2026-02-10 09:00] implementation | a unit of work\n\n"
                     "Did the thing.\n\nFriction: the manifest key had to be hand-edited.\n")

    def _friction(self, body: str) -> dict:
        root, docs = self._tree(body)
        ff = sig.read_journal_friction_from((docs / "manifest.yml").read_text(encoding="utf-8"))
        self.assertEqual(ff, "2026-02-01", "fixture must record an adoption date")
        return sig.signal_friction_citations(root, docs, "bionic", ff)

    def test_a_post_adoption_entry_with_no_friction_is_a_measured_zero(self):
        rec = self._friction(self.NO_FRICTION)
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 0)

    def test_positive_control_the_same_tree_with_a_friction_line_counts_one(self):
        """Proves the zero above is a MEASUREMENT, not a fixture that counts nothing."""
        rec = self._friction(self.WITH_FRICTION)
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 1)

    def test_a_window_wholly_before_adoption_stays_unmeasurable(self):
        """The contrast that gives the zero its meaning: no entry at or after."""
        body = ("# 2026-01\n\n## [2026-01-10 09:00] implementation | before adoption\n\n"
                "Friction: this predates the boundary.\n")
        root, docs = self._tree("# 2026-02\n")
        (docs / "journal" / "2026-01.md").write_text(body, encoding="utf-8")
        rec = sig.signal_friction_citations(root, docs, "bionic", "2026-02-01")
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])


class GovernsExemptCommentedBlockKeyTests(unittest.TestCase):
    """`read_governs_exempt` opens the `adr:` block through a comment.

    The sibling of the `journal:` block-key defect, and the same cause: the
    shipped `manifest.yml.tmpl` comments every column-0 block key, and this
    reader matched `^adr\\s*:\\s*$`. A commented `adr:` therefore never opened
    the block, every recorded exemption read as absent, and the carve-out count
    fell silently to zero on a manifest that records exemptions.
    """

    EXEMPT = ["ADR-0093", "ADR-0094"]

    def _ids(self, adr_block_key: str, body: str = "  governs_exempt: [ADR-0093, ADR-0094]\n"):
        return sig.read_governs_exempt(
            'schema_version: "5"\n' + adr_block_key + body + "promptbook:\n  next_number: 1\n")

    def test_uncommented_and_commented_keys_agree(self):
        """The paired comparison: same non-empty exemptions, both spellings."""
        uncommented = self._ids("adr:\n")
        commented = self._ids("adr:  # ADR allocation\n")
        self.assertEqual(uncommented, self.EXEMPT)   # positive control
        self.assertEqual(commented, uncommented)

    def test_a_comment_abutting_the_colon_reads_the_exemptions(self):
        self.assertEqual(self._ids("adr:# ADR allocation\n"), self.EXEMPT)

    def test_the_mapping_member_shape_survives_a_commented_key(self):
        """The comment tolerance widens the block key, never the member grammar."""
        self.assertEqual(
            self._ids("adr:  # c\n",
                      '  governs_exempt: [{adr: ADR-0093, reason: "amends only"}]\n'),
            ["ADR-0093"])

    def test_an_absent_key_under_a_commented_block_is_empty(self):
        """The absent-key control: empty because the key is absent, not hidden."""
        self.assertEqual(self._ids("adr:  # c\n", "  next_number: 1\n"), [])

    def test_an_empty_value_under_a_commented_key_is_empty(self):
        self.assertEqual(self._ids("adr:  # c\n", "  governs_exempt: []\n"), [])

    def test_a_malformed_member_carrying_no_adr_id_is_dropped(self):
        """Malformed input still yields no fragment, commented key or not."""
        self.assertEqual(self._ids("adr:  # c\n", '  governs_exempt: [{reason: "no id"}]\n'), [])

    def test_a_different_column_0_key_prefixed_adr_does_not_open_the_block(self):
        self.assertIsNotNone(self._ids("adrx:  # not the block\n"))
        self.assertEqual(self._ids("adrx:  # not the block\n"), [])

    def test_the_block_still_ends_at_the_next_column_0_key(self):
        """A commented key opens the block; it does not stop it from closing."""
        self.assertEqual(
            sig.read_governs_exempt("adr:  # c\npromptbook:\n  governs_exempt: [ADR-0093]\n"), [])


class JournalFrictionAdoptionReaderTests(unittest.TestCase):
    """`read_journal_friction_from` opens the `journal:` block through a comment.

    The shipped `manifest.yml.tmpl` comments every column-0 block key. A
    `journal:` key carrying a trailing `#` comment never opened the block, so
    the adoption date read as absent and every friction reader reported
    `unmeasurable` against a manifest that records one. The value leg already
    stripped its own comment; only the block key did not.
    """

    DATE = "2026-09-07"

    def _read(self, manifest: str) -> str | None:
        return sig.read_journal_friction_from(manifest)

    def test_plain_block_key_reads_the_date(self):
        """The positive control: without a comment the reader always worked."""
        self.assertEqual(self._read(f"journal:\n  friction_line_from: {self.DATE}\n"), self.DATE)

    def test_a_commented_block_key_reads_the_date(self):
        self.assertEqual(
            self._read(f"journal:  # the friction-line cohort boundary\n"
                       f"  friction_line_from: {self.DATE}\n"), self.DATE)

    def test_a_comment_abutting_the_colon_reads_the_date(self):
        self.assertEqual(
            self._read(f"journal:# boundary\n  friction_line_from: {self.DATE}\n"), self.DATE)

    def test_the_shipped_template_block_reads_its_date(self):
        """The exact spelling `manifest.yml.tmpl` ships, date substituted."""
        self.assertEqual(self._read(
            "# Journal concern.\n"
            "journal:                           # The friction-line cohort boundary.\n"
            f"  friction_line_from: {self.DATE}  # ISO date; set by init-docs.\n"), self.DATE)

    def test_a_commented_key_with_a_null_value_is_still_null(self):
        """The comment tolerance widens the block key, never the value grammar."""
        self.assertIsNone(self._read("journal:  # boundary\n  friction_line_from: null\n"))

    def test_a_commented_key_with_a_non_iso_value_is_still_none(self):
        self.assertIsNone(self._read("journal:  # boundary\n  friction_line_from: soon\n"))

    def test_a_different_column_0_key_prefixed_journal_does_not_open_the_block(self):
        """`journalx:` is a different key; the comment tolerance must not match it."""
        self.assertIsNone(
            self._read(f"journalx:  # not the block\n  friction_line_from: {self.DATE}\n"))

    def test_the_block_still_ends_at_the_next_column_0_key(self):
        """A commented key opens the block; it does not stop it from closing."""
        self.assertIsNone(
            self._read(f"journal:  # boundary\nadr:\n  friction_line_from: {self.DATE}\n"))


class GovernsExemptShapesTests(unittest.TestCase):
    """`read_governs_exempt` returns ids for both member shapes of the key.

    `docs/CLAUDE.md` §7 admits a bare `ADR-NNNN` and a `{adr, reason}` mapping,
    in flow or block form. A reader pinned to the bare form returned
    `reason: ...` fragments as exemptions and miscounted the carve-outs.
    """

    def _ids(self, adr_block: str) -> list[str]:
        text = ('schema_version: "5"\nadr:\n' + adr_block
                + 'promptbook:\n  next_number: 1\n')
        return sig.read_governs_exempt(text)

    def test_bare_flow_form(self):
        self.assertEqual(self._ids("  governs_exempt: [ADR-0093, ADR-0094]\n"), ["ADR-0093", "ADR-0094"])

    def test_mapping_flow_form_yields_ids_and_no_reason_fragment(self):
        self.assertEqual(
            self._ids('  governs_exempt: [{adr: ADR-0093, reason: "amends only"}]\n'), ["ADR-0093"])

    def test_a_reason_citing_an_adr_is_not_a_second_exemption(self):
        """A `reason` may cite an ADR; that citation is prose, not an exemption.

        The flow branch split the bracket body on EVERY comma, so a mapping
        member became two fragments and the reason's own ADR id read as a
        second exemption — `carve_out_count` then reported 2 where the tree
        declares 1.
        """
        self.assertEqual(
            self._ids('  governs_exempt: [{adr: ADR-0093, reason: "amends ADR-0092 only"}]\n'),
            ["ADR-0093"])

    def test_a_reason_preceding_the_adr_key_does_not_win_the_id(self):
        # `ADR_ID.search` takes the FIRST id in the member. When the reason is
        # written first, that id is the reason's. The `adr:` key decides.
        self.assertEqual(
            self._ids('  governs_exempt: [{reason: "supersedes ADR-0092", adr: ADR-0093}]\n'),
            ["ADR-0093"])

    def test_mapping_block_form_reads_past_a_reason_continuation_line(self):
        block = ('  governs_exempt:\n'
                 '    - adr: ADR-0093\n'
                 '      reason: "amends ADR-0092 item 4 and authors no new rule"\n'
                 '    - adr: ADR-0094\n'
                 '      reason: "second"\n'
                 '  next_number: 102\n')
        self.assertEqual(self._ids(block), ["ADR-0093", "ADR-0094"])

    def test_bare_block_form_still_reads(self):
        self.assertEqual(self._ids("  governs_exempt:\n    - ADR-0093\n"), ["ADR-0093"])

    def test_absent_and_null_read_empty(self):
        self.assertEqual(self._ids("  next_number: 1\n"), [])
        self.assertEqual(self._ids("  governs_exempt: []\n"), [])
        self.assertEqual(self._ids("  governs_exempt: ~\n"), [])


class PaperOnlyTests(unittest.TestCase):
    def test_positive_an_adr_whose_every_row_is_not_run_bound_is_true(self):
        self.assertIs(record(TRIPS, "paper_only")["value"]["ADR-0001"], True)

    def test_negative_one_run_bound_row_is_enough_to_read_false(self):
        # ADR-0002 carries one run-bound row and one not-run-bound row.
        self.assertIs(record(TRIPS, "paper_only")["value"]["ADR-0002"], False)
        self.assertIs(record(QUIET, "paper_only")["value"]["ADR-0001"], False)

    def test_a_rowless_adr_maps_to_null_and_the_filter_says_why(self):
        rec = record(TRIPS, "paper_only")
        # Positive control: the doctrine index the signal reads exists and
        # names ADR-0001 and ADR-0002, so ADR-0003's null is a rowless ADR
        # rather than an unread or missing file.
        doctrine = (TRIPS / "bionic" / "adrs" / "doctrine" / "index.md").read_text(encoding="utf-8")
        self.assertIn("ADR-0001/alpha-one", doctrine)
        self.assertNotIn("ADR-0003/", doctrine)
        self.assertIsNone(rec["value"]["ADR-0003"])
        self.assertIn("null", rec["filter"])


class DormancyDaysTests(unittest.TestCase):
    def test_positive_the_newest_surviving_mention_sets_the_day_count(self):
        value = record(TRIPS, "dormancy_days")["value"]
        # log.md 2026-02-10 names ADR-0001 and ADR-0002 — two ids, under the
        # bulk threshold — and TODAY is 2026-02-20.
        self.assertEqual(value["ADR-0001"], 10)
        # The 2026-02-11 journal entry is newer than the 2026-02-09 snapshot.
        self.assertEqual(value["ADR-0002"], 9)

    def test_negative_an_adr_named_only_by_a_bulk_entry_reads_null(self):
        log = (QUIET / "bionic" / "log.md").read_text(encoding="utf-8")
        # Positive control: the only entry in `quiet/log.md` DOES name
        # ADR-0001, and it names four distinct ids. So the null below is the
        # bulk-entry filter firing, not an ADR nothing ever mentioned.
        self.assertIn("ADR-0001", log)
        self.assertEqual(len({m for m in ("ADR-0001", "ADR-0002", "ADR-0003", "ADR-0004")
                              if m in log}), sig.BULK_ENTRY_THRESHOLD)
        self.assertIsNone(record(QUIET, "dormancy_days")["value"]["ADR-0001"])
        # Second positive control: the same signal DOES produce a day count in
        # `trips`, whose log entry names two ids.
        self.assertEqual(record(TRIPS, "dormancy_days")["value"]["ADR-0001"], 10)

    def test_the_filter_declares_the_threshold_verbatim(self):
        rec = record(TRIPS, "dormancy_days")
        self.assertIn(
            "an entry naming 4 or more distinct ADR ids is a roster, not a mention, "
            "and is excluded", rec["filter"])
        self.assertIn(str(TODAY), rec["basis"])


class FrictionCitationsTests(unittest.TestCase):
    """`signal_friction_citations` reader per ADR-0102 requirements 4 and 5.

    `friction_line_from: 2026-02-14` is the adoption date recorded in
    `trips/bionic/manifest.yml`. The journal leg counts `Friction:` lines only
    over entries dated at or after that boundary.
    """

    def test_trips_reads_computed_with_the_adoption_date_named_in_basis(self):
        # Positive control for the fourth leg: the materializer placed a forge
        # log carrying a `fallback` entry, so the count below includes it.
        forge = TRIPS / ".claude" / "skills" / "forge-log.md"
        self.assertTrue(forge.is_file())
        self.assertIn("] fallback |", forge.read_text(encoding="utf-8"))
        rec = record(TRIPS, "friction_citations")
        self.assertEqual(rec["verdict"], "computed")
        # 3 counted journal `Friction:` lines (2026-02-14, 2026-02-16 and
        # 2026-02-19) + 1 non-empty run-snapshot note + 1 whats_next dismissal
        # naming an ADR + 1 fallback forge-log entry.
        self.assertEqual(rec["value"], 6)
        self.assertIsNone(rec["filter"])
        self.assertIn("2026-02-14", rec["basis"])

    def test_a_pre_boundary_friction_line_is_present_but_excluded_and_truncated(self):
        journal = TRIPS / "bionic" / "journal" / "2026-02.md"
        text = journal.read_text(encoding="utf-8")
        # Positive control: the pre-boundary entry and its `Friction:` line ARE
        # in the file, so excluding it from the count is the boundary filter
        # firing rather than the line never having existed.
        self.assertIn("## [2026-02-11 09:00] review | fixture reflection", text)
        self.assertIn("Friction: The review took two passes before the wording held.", text)
        rec = record(TRIPS, "friction_citations")
        self.assertEqual(rec["value"], 6)
        self.assertIn("truncated", rec["basis"])

    def test_an_entry_dated_exactly_on_the_adoption_date_is_counted(self):
        """The boundary is `>=`, so the adoption day itself is inside the window.

        Without an entry dated on the boundary, mutating `date >= friction_from`
        to `date > friction_from` left the whole module green: every counted
        fixture entry sat strictly after 2026-02-14.
        """
        journal = TRIPS / "bionic" / "journal" / "2026-02.md"
        text = journal.read_text(encoding="utf-8")
        # Positive control: the boundary-day entry and its `Friction:` line are
        # in the fixture, dated on the recorded adoption date itself.
        self.assertIn("## [2026-02-14 07:45] chore | fixture boundary-day friction control",
                      text)
        self.assertIn("Friction: The boundary day itself needed an entry before it "
                      "could be tested.", text)
        manifest = (TRIPS / "bionic" / "manifest.yml").read_text(encoding="utf-8")
        self.assertIn("friction_line_from: 2026-02-14", manifest)
        rec = record(TRIPS, "friction_citations")
        self.assertEqual(rec["verdict"], "computed")
        # 6 with the boundary day counted; a `>` boundary reads 5.
        self.assertEqual(rec["value"], 6)

    def test_a_contentless_friction_line_is_skipped_with_a_same_day_positive_control(self):
        journal = TRIPS / "bionic" / "journal" / "2026-02.md"
        text = journal.read_text(encoding="utf-8")
        # Both lines exist in the fixture: the contentless one (skipped) and a
        # non-empty one on the same day, at or after the boundary (counted).
        self.assertIn("## [2026-02-19 14:00] bug | fixture contentless friction control", text)
        self.assertIn("Friction:\n", text)
        self.assertIn(
            "## [2026-02-19 09:30] implementation | fixture counted friction control", text)
        self.assertIn("Friction: A dependency version pin caused an unexpected rebuild loop.",
                       text)
        self.assertEqual(record(TRIPS, "friction_citations")["value"], 6)

    def test_a_markdown_heading_inside_an_entry_contributes_nothing(self):
        journal = TRIPS / "bionic" / "journal" / "2026-02.md"
        text = journal.read_text(encoding="utf-8")
        # Positive control: the heading exists in the fixture, so its
        # exclusion from the count is a real subtraction.
        self.assertIn("### What was hard", text)
        self.assertEqual(record(TRIPS, "friction_citations")["value"], 6)

    def test_index_md_is_excluded_on_both_its_heading_and_its_friction_line(self):
        index = TRIPS / "bionic" / "journal" / "index.md"
        text = index.read_text(encoding="utf-8")
        # POSITIVE CONTROLS. The `### ` heading and the `Friction:` line were
        # not enough on their own: a `Friction:` line belongs to no entry
        # unless a dated `## [YYYY-MM-DD]` entry heading precedes it, and the
        # fixture carried none — so the line was dropped whether `index.md`
        # was excluded by name or not, and deleting the exclusion left the
        # suite green. The dated heading is what makes the exclusion a real
        # subtraction: with it, the count is 6 excluded and 7 included.
        self.assertIn("### This heading is in index.md", text)
        self.assertIn("Friction: This line is in index.md", text)
        self.assertIn("## [2026-02-19 12:00] work |", text)
        # The heading is dated at or after the tree's recorded adoption date,
        # which is the other half of countability.
        manifest = (TRIPS / "bionic" / "manifest.yml").read_text(encoding="utf-8")
        self.assertIn("friction_line_from: 2026-02-14", manifest)
        self.assertEqual(record(TRIPS, "friction_citations")["value"], 6)

    def test_the_same_friction_line_in_a_dated_monthly_file_is_counted(self):
        """The discriminator, driven rather than asserted about.

        `index.md`'s entry and friction line, copied verbatim into a monthly
        file under the same journal, raise the count to 7. So the 6 above is
        the name-based exclusion firing on a countable line, not a line that
        was never countable.
        """
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-index-md-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "trips"
        shutil.copytree(TRIPS, root)
        journal = root / "bionic" / "journal"
        shutil.copyfile(journal / "index.md", journal / "2026-03.md")
        self.assertEqual(record(root, "friction_citations")["value"], 7)

    def test_quiet_reads_unmeasurable_naming_the_missing_adoption_date(self):
        rec = record(QUIET, "friction_citations")
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        self.assertIn("records no adoption date", rec["filter"])
        # Positive control: `quiet/bionic/manifest.yml` carries no `journal`
        # key at all, so the missing-date verdict is the fixture and not a
        # reader bug.
        manifest = QUIET / "bionic" / "manifest.yml"
        self.assertNotIn("journal:", manifest.read_text(encoding="utf-8"))
        # Second positive control: the other three legs report present, so
        # the verdict turns on the missing adoption date alone.
        for leg in ("run-snapshot notes", "whats_next.md dismissals", "forge-log.md"):
            self.assertIn(leg, rec["basis"])
        self.assertEqual(rec["basis"].count("— present"), 3)
        self.assertEqual(rec["basis"].count("— absent"), 1)

    def test_a_window_wholly_before_the_boundary_reads_unmeasurable(self):
        """`shutil.copytree`s TRIPS, per `DoctrineEscapedPipeTests` — no third corpus root."""
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-window-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "trips"
        shutil.copytree(TRIPS, root)
        manifest = root / "bionic" / "manifest.yml"
        text = manifest.read_text(encoding="utf-8")
        self.assertIn("friction_line_from: 2026-02-14", text)
        # Every trips entry is dated in February 2026, so a March boundary
        # leaves the window wholly before it.
        manifest.write_text(
            text.replace("friction_line_from: 2026-02-14", "friction_line_from: 2026-03-01"),
            encoding="utf-8")
        env, errors = sig.build(root, TODAY)
        self.assertEqual(errors, [])
        rec = next(r for r in env["signals"] if r["signal"] == "friction_citations")
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        self.assertIn("wholly before", rec["filter"])
        self.assertIn("2026-03-01", rec["filter"])
        # Positive control: the SAME root before the rewrite reads `computed`,
        # so the unmeasurable verdict above is the truncated window and not
        # some other property of the copied fixture.
        self.assertEqual(record(TRIPS, "friction_citations")["verdict"], "computed")


class DoctrineEscapedPipeTests(unittest.TestCase):
    """A doctrine row whose rule text carries an escaped `\\|` is still a row.

    The doctrine renderer escapes a literal pipe inside a cell as `\\|`. A
    parser that splits on every pipe sees nine cells instead of eight and
    drops the row without an error, so a run-bound rule reads as rowless and
    its ADR as paper-only. The fixture appends such a row for ADR-0003, which
    the corpus otherwise leaves rowless (`test_a_rowless_adr_maps_to_null`).
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="adr-signals-pipe-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "trips"
        shutil.copytree(TRIPS, self.root)
        self.doctrine = self.root / "bionic" / "adrs" / "doctrine" / "index.md"

    def _append_row(self, basis: str) -> None:
        row = ("| ADR-0003/pipe-rule | rule:pipe-rule | a rule whose text says "
               "`a \\| b` on purpose | ADR-0003 | decided | " + basis + " |\n")
        text = self.doctrine.read_text(encoding="utf-8")
        marker = "## Exempt ADRs"
        if marker in text:
            text = text.replace(marker, row + "\n" + marker, 1)
        else:
            text = text.rstrip("\n") + "\n" + row
        self.doctrine.write_text(text, encoding="utf-8")

    def test_a_run_bound_row_with_an_escaped_pipe_reads_false_not_null(self):
        self._append_row("run-bound")
        env, errors = sig.build(self.root, TODAY)
        self.assertEqual(errors, [])
        value = next(r for r in env["signals"] if r["signal"] == "paper_only")["value"]
        self.assertIs(value["ADR-0003"], False)

    def test_a_not_run_bound_row_with_an_escaped_pipe_reads_true_not_null(self):
        self._append_row("not-run-bound")
        env, errors = sig.build(self.root, TODAY)
        self.assertEqual(errors, [])
        value = next(r for r in env["signals"] if r["signal"] == "paper_only")["value"]
        self.assertIs(value["ADR-0003"], True)

    def test_the_control_without_the_row_still_reads_null(self):
        # Positive control for the two tests above: the appended row is the
        # only thing that moves ADR-0003 off null.
        env, _ = sig.build(self.root, TODAY)
        value = next(r for r in env["signals"] if r["signal"] == "paper_only")["value"]
        self.assertIsNone(value["ADR-0003"])


class ForgeLogRuntimeDirTests(unittest.TestCase):
    """The forge log lives under the runtime's local skills directory.

    Claude Code writes it under `.claude/skills`, Codex under `.agents/skills`,
    OpenCode under `.opencode/skills` (or the singular `.opencode/skill`). A
    reader pinned to Claude's path misses every Codex and OpenCode entry.
    """

    RUNTIME_DIRS = (".agents/skills", ".opencode/skills", ".opencode/skill")

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="adr-signals-forge-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "trips"
        shutil.copytree(TRIPS, self.root)

    def _friction(self) -> dict:
        env, errors = sig.build(self.root, TODAY)
        self.assertEqual(errors, [])
        return next(r for r in env["signals"] if r["signal"] == "friction_citations")

    def test_a_codex_or_opencode_forge_log_entry_is_counted(self):
        base = self._friction()["value"]
        for i, rel in enumerate(self.RUNTIME_DIRS, start=1):
            log = self.root / rel / "forge-log.md"
            log.parent.mkdir(parents=True)
            log.write_text(
                f"# Forge log\n\n## [2026-02-0{i} 10:00] fallback | some-skill\n"
                f"A gate row fired.\n", encoding="utf-8")
            with self.subTest(runtime_dir=rel):
                self.assertEqual(self._friction()["value"], base + i)

    def test_a_used_entry_in_a_codex_log_is_not_counted(self):
        # Negative control: only `fallback` and `escalated` count, on every path.
        base = self._friction()["value"]
        log = self.root / ".agents" / "skills" / "forge-log.md"
        log.parent.mkdir(parents=True)
        log.write_text("# Forge log\n\n## [2026-02-01 10:00] used | some-skill\nok\n",
                       encoding="utf-8")
        self.assertEqual(self._friction()["value"], base)

    def test_the_basis_names_every_runtime_directory(self):
        basis = self._friction()["basis"]
        for rel in (".claude/skills",) + self.RUNTIME_DIRS:
            self.assertIn(rel, basis)


#: The three signals whose `value` is a mapping keyed by ADR id. Selected BY
#: NAME rather than by `isinstance(value, dict)`: `release_cadence` and
#: `schema_growth` also carry dict values, and a shape-based selector would
#: quietly widen to them and then assert the wrong cardinality.
ADR_KEYED = {"amendment_fan_in", "paper_only", "dormancy_days"}
DELIVERY_SIGNALS = {"release_cadence", "schema_growth", "gate_count"}


class EnvelopeContractTests(unittest.TestCase):
    def test_every_record_carries_exactly_the_envelope_members(self):
        for root in (TRIPS, QUIET):
            with self.subTest(root=root.name):
                env = envelope(root)
                self.assertEqual(set(env), {"active_adrs", "signals"})
                self.assertEqual(len(env["signals"]), 8)
                assert_envelope_contract(self, env)

    def test_each_adr_keyed_mapping_has_exactly_active_adrs_keys(self):
        for root in (TRIPS, QUIET):
            with self.subTest(root=root.name):
                env = envelope(root)
                names = {r["signal"] for r in env["signals"]}
                # The positive control for the by-name selector: the three
                # delivery signals ARE in the envelope and are NOT ADR-keyed,
                # so the narrowing below is doing work rather than describing
                # an empty difference.
                self.assertTrue(DELIVERY_SIGNALS <= names)
                self.assertEqual(DELIVERY_SIGNALS & ADR_KEYED, set())
                keyed = {r["signal"]: r["value"] for r in env["signals"]
                         if r["signal"] in ADR_KEYED}
                self.assertEqual(set(keyed), ADR_KEYED)
                for name, value in keyed.items():
                    self.assertEqual(len(value), env["active_adrs"], name)


class EnvelopeContractControlTests(unittest.TestCase):
    """The positive control proving `assert_envelope_contract` has teeth."""

    def test_the_contract_helper_rejects_a_record_carrying_severity(self):
        forged = {"signals": [{"signal": "forged", "verdict": "computed", "value": 1,
                               "basis": "hand-built", "filter": None, "severity": "P1"}]}
        with self.assertRaises(AssertionError):
            assert_envelope_contract(self, forged)

    def test_the_contract_helper_rejects_a_record_carrying_recommendation(self):
        forged = {"signals": [{"signal": "forged", "verdict": "computed", "value": 1,
                               "basis": "hand-built", "filter": None,
                               "recommendation": "escalate"}]}
        with self.assertRaises(AssertionError):
            assert_envelope_contract(self, forged)

    def test_the_contract_helper_rejects_a_record_missing_a_member(self):
        forged = {"signals": [{"signal": "forged", "verdict": "computed", "value": 1,
                               "basis": "hand-built"}]}
        with self.assertRaises(AssertionError):
            assert_envelope_contract(self, forged)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


class CliTests(unittest.TestCase):
    def test_json_mode_exits_zero_with_a_parseable_envelope(self):
        proc = _run("--repo-root", str(TRIPS), "--today", TODAY.isoformat(), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["active_adrs"], 3)
        assert_envelope_contract(self, payload)

    def test_an_unmeasurable_verdict_does_not_change_the_exit_code(self):
        proc = _run("--repo-root", str(QUIET), "--today", TODAY.isoformat(), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        verdicts = {r["signal"]: r["verdict"] for r in payload["signals"]}
        # Positive control for the exit code: an unmeasurable verdict IS
        # present, so exit 0 is the documented lane rather than a clean run.
        self.assertEqual(verdicts["friction_citations"], "unmeasurable")

    def test_table_mode_renders_every_member_of_every_signal(self):
        proc = _run("--repo-root", str(TRIPS), "--today", TODAY.isoformat())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("active_adrs: 3", proc.stdout)
        for name in ("amendment_fan_in", "carve_out_count", "paper_only",
                     "dormancy_days", "friction_citations",
                     "release_cadence", "schema_growth", "gate_count"):
            self.assertIn(name, proc.stdout)
        for label in ("verdict:", "value:", "basis:", "filter:"):
            self.assertEqual(proc.stdout.count(label), 8, label)
        # A mapping renders as a count plus a bounded sample, never whole.
        self.assertIn("3 entries", proc.stdout)

    def test_missing_repo_root_flag_exits_two_naming_the_flag(self):
        proc = _run("--json")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        # The content discriminator: "exit 2 either way" cannot pass this.
        self.assertIn("--repo-root", proc.stderr)

    def test_a_root_that_is_not_a_crux_repo_exits_two_naming_the_adrs_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = _run("--repo-root", tmp, "--json")
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(proc.stdout, "")
            # A different content discriminator from the case above, so the two
            # exit-2 lanes cannot satisfy each other's assertion.
            self.assertIn("adrs", proc.stderr)
            self.assertIn("not a crux repo root", proc.stderr)
            self.assertNotIn("--repo-root", proc.stderr)

    def test_a_malformed_today_exits_two_naming_the_flag(self):
        proc = _run("--repo-root", str(TRIPS), "--today", "not-a-date", "--json")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        # The content discriminator: argparse's usage line for the
        # missing-flag lane also contains "--today", so the flag name alone
        # cannot tell the two exit-2 lanes apart. Pin the message.
        self.assertIn("must be an ISO calendar date", proc.stderr)
        self.assertNotIn("the following arguments are required", proc.stderr)


class RedactionRoutingTests(unittest.TestCase):
    """The CALL sites, not the function — `rule:mined-values-fenced-and-bounded`.

    `test_untrusted.py` proves `redact` bounds and replaces. Nothing proved
    that `adr-signals.py` CALLS it. Two mutations run against the pre-fix
    module made the point: neutering `redact` to an identity render left the
    26 cases here at `OK`, and deleting every document-path `redact(...)` call
    outright left them at `OK` too. A gate nothing asserts is a gate that is
    not there, and that class of hole is invisible to `false-green-test-guard`,
    which reads the tests that EXIST.

    Every case below therefore asserts the bound or the replacement FIRED on a
    hostile value AND, in the same test, that it did NOT fire on a legitimate
    one. The paired control is what makes the assertion mean "redaction ran"
    rather than "some string was produced": a `redact` stubbed to always
    truncate would pass the first leg and fail the second.

    Payloads are BUILT — `chr(27)`, `"a" * 200` — never pasted. A pasted
    control byte in a source file is a hazard to every tool that later reads
    it, and 200 keeps each path component inside the 255-byte POSIX limit.
    """

    #: Long enough to cross `untrusted.LIMIT` (120), short enough that the
    #: whole filename stays under the 255-byte POSIX path-component ceiling.
    FILLER = 200

    def _root(self) -> Path:
        """A writable copy of the `trips` fixture root, torn down after."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "root"
        shutil.copytree(TRIPS, root)
        return root

    def _errors(self, root: Path) -> list[dict]:
        proc = _run("--repo-root", str(root), "--today", TODAY.isoformat(), "--json")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        return json.loads(proc.stdout)["errors"]

    def test_an_over_long_adr_filename_is_bounded_in_the_errors_array(self):
        # An ADR file with no frontmatter is the shortest route from a
        # filename to `errors[]["input"]`. The name is the payload.
        hostile = f"ADR-9999-{'a' * self.FILLER}.md"
        root = self._root()
        (root / "bionic" / "adrs" / hostile).write_text("no frontmatter here\n",
                                                        encoding="utf-8")
        entry = next(e for e in self._errors(root) if e["input"].startswith("ADR-9999-"))
        self.assertEqual(entry["problem"],
                         "ADR file carries no YAML frontmatter block")
        # The bound fired: the rendered value is the 120-character head plus
        # the note naming the true length, and never the whole 212 characters.
        self.assertIn(f"truncated from {len(hostile)} characters", entry["input"])
        self.assertNotIn("a" * (self.FILLER - 1), entry["input"])
        self.assertLess(len(entry["input"]), len(hostile))

        # PAIRED POSITIVE CONTROL, same lane, same assertion surface: a
        # legitimate filename round-trips to EXACTLY itself with no note. A
        # `redact` that always truncated would pass the leg above and fail
        # this one, so the pair cannot be satisfied by a constant.
        benign = "ADR-9998-short.md"
        root2 = self._root()
        (root2 / "bionic" / "adrs" / benign).write_text("no frontmatter here\n",
                                                        encoding="utf-8")
        control = next(e for e in self._errors(root2) if e["input"].startswith("ADR-9998-"))
        self.assertEqual(control["input"], benign)

    def test_an_unprintable_doctrine_basis_is_replaced_not_echoed(self):
        # ESC is the sharp one: `\x1b[2J` clears the reader's terminal, so a
        # basis cell that reached stdout verbatim would erase the finding that
        # reported it.
        esc = chr(27)
        hostile = f"not-run{esc}[2Jbound"
        root = self._root()
        doctrine = root / "bionic" / "adrs" / "doctrine" / "index.md"
        text = doctrine.read_text(encoding="utf-8")
        doctrine.write_text(
            text.replace("| ADR-0001/alpha-one | rule:alpha-one | The first fixture rule. "
                         "| ADR-0001 | decided | not-run-bound |",
                         f"| ADR-0001/alpha-one | rule:alpha-one | The first fixture rule. "
                         f"| ADR-0001 | decided | {hostile} |"),
            encoding="utf-8")
        entry = next(e for e in self._errors(root) if "unknown basis" in e["problem"])
        self.assertNotIn(esc, entry["problem"])
        self.assertIn("\ufffd", entry["problem"])
        self.assertIn("1 unprintable character redacted", entry["problem"])

        # PAIRED POSITIVE CONTROL: an unknown but wholly PRINTABLE basis is
        # reported verbatim and carries no redaction note, so the assertion
        # above measures the unprintable character and not merely "the
        # message mentioned the cell".
        root2 = self._root()
        doctrine2 = root2 / "bionic" / "adrs" / "doctrine" / "index.md"
        doctrine2.write_text(
            doctrine2.read_text(encoding="utf-8").replace(
                "| ADR-0001 | decided | not-run-bound |",
                "| ADR-0001 | decided | not-run-bounded |", 1),
            encoding="utf-8")
        control = next(e for e in self._errors(root2) if "unknown basis" in e["problem"])
        self.assertIn("not-run-bounded", control["problem"])
        self.assertNotIn("redacted", control["problem"])
        self.assertNotIn("\ufffd", control["problem"])

    def test_a_hostile_today_cannot_forge_or_flood_a_stderr_line(self):
        # `--today` is the one untrusted value that reaches stderr on the
        # exit-2 lane. A newline in it would forge a second line where the
        # contract is one; the length would flood the reader either way.
        payload = "2026-01-01" + chr(27) + "[2J" + "\n" + "b" * self.FILLER
        proc = _run("--repo-root", str(TRIPS), "--today", payload, "--json")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        # Content discriminator: this is the --today lane, not argparse's.
        self.assertIn("must be an ISO calendar date", proc.stderr)
        # Structure: exactly one line, whatever the payload contained.
        self.assertEqual(proc.stderr.count("\n"), 1, proc.stderr)
        self.assertNotIn(chr(27), proc.stderr)
        self.assertIn(f"truncated from {len(payload)} characters", proc.stderr)

        # PAIRED POSITIVE CONTROL: a short, printable, still-invalid date is
        # echoed verbatim on the same lane with neither note, so the bound and
        # the replacement are shown NOT firing on a legitimate refusal.
        ok = _run("--repo-root", str(TRIPS), "--today", "not-a-date", "--json")
        self.assertEqual(ok.returncode, 2)
        self.assertIn("got not-a-date\n", ok.stderr)
        self.assertNotIn("redacted", ok.stderr)
        self.assertNotIn("truncated from", ok.stderr)

    def test_the_carve_out_basis_redacts_the_exempt_literal_it_names(self):
        # `carve_out_count`'s basis names a variable read out of a source file
        # by `ast` and the filename it came from. Both are values this script
        # did not author, and both land in an envelope member the report
        # renders.
        root = self._root()
        carve = root / "crux" / "scripts" / "carve.py"
        hostile_name = "EXEMPT_" + "C" * self.FILLER
        carve.write_text(
            carve.read_text(encoding="utf-8").replace("EXEMPT_THINGS", hostile_name),
            encoding="utf-8")
        proc = _run("--repo-root", str(root), "--today", TODAY.isoformat(), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = next(r for r in json.loads(proc.stdout)["signals"]
                   if r["signal"] == "carve_out_count")
        self.assertIn("truncated from", rec["basis"])
        self.assertNotIn(hostile_name, rec["basis"])

        # PAIRED POSITIVE CONTROL: the unmodified fixture names its literal
        # in full, so the truncation above is the bound firing and not the
        # basis having stopped naming the literal at all.
        self.assertIn("EXEMPT_THINGS", record(TRIPS, "carve_out_count")["basis"])
        self.assertNotIn("truncated from", record(TRIPS, "carve_out_count")["basis"])


class MalformedInputTests(unittest.TestCase):
    def test_a_missing_doctrine_index_exits_one_with_an_errors_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            (root / ".bionic.yml").write_text("config_version: \"1\"\ndocs_dir: bionic\n",
                                              encoding="utf-8")
            src = TRIPS / "bionic"
            dst = root / "bionic"
            (dst / "adrs").mkdir(parents=True)
            (dst / "manifest.yml").write_text((src / "manifest.yml").read_text(encoding="utf-8"),
                                              encoding="utf-8")
            for adr in sorted((src / "adrs").glob("ADR-*.md")):
                (dst / "adrs" / adr.name).write_text(adr.read_text(encoding="utf-8"),
                                                     encoding="utf-8")
            proc = _run("--repo-root", str(root), "--today", TODAY.isoformat(), "--json")
            self.assertEqual(proc.returncode, 1, proc.stderr)
            payload = json.loads(proc.stdout)
            # Partial JSON: the envelope is still there beside the errors.
            self.assertEqual(payload["active_adrs"], 3)
            self.assertEqual(len(payload["signals"]), 8)
            self.assertTrue(any("doctrine" in e["input"] for e in payload["errors"]))
            # Positive control: the SAME three ADRs under the complete `trips`
            # root exit 0, so exit 1 is the missing doctrine index and not the
            # copied ADR set.
            ok = _run("--repo-root", str(TRIPS), "--today", TODAY.isoformat(), "--json")
            self.assertEqual(ok.returncode, 0, ok.stderr)


class BionicConfigLaneTests(unittest.TestCase):
    """`.bionic.yml` resolution is an ENVIRONMENT problem, never a traceback.

    `_tree_name` reads `.bionic.yml` and raises `BionicConfigError` on a
    malformed one or on a `docs_dir` that resolves outside the repo root. It
    is called twice on the entry path — once in `main` for the `adrs`
    existence check and once inside `build` — and outside a handler either
    escaped as an uncaught traceback: exit 1 with EMPTY stdout, which is
    neither documented lane (exit 1 carries partial JSON, exit 2 carries a
    message). The traceback also printed absolute filesystem paths and the
    raw `docs_dir` through an unrouted `{value!r}`. Same structure as
    generate-reviews-index.py's handler.
    """

    @staticmethod
    def _root(tmp: str, docs_dir: str) -> Path:
        root = Path(tmp) / "root"
        (root / "bionic" / "adrs").mkdir(parents=True)
        (root / ".bionic.yml").write_text(
            f'config_version: "1"\ndocs_dir: {docs_dir}\n', encoding="utf-8")
        return root

    def test_a_docs_dir_escaping_the_root_exits_two_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, "../outside")
            proc = _run("--repo-root", str(root), "--today", TODAY.isoformat(),
                        "--json")
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertEqual(proc.stdout, "")
            # Content discriminators, so "exit 2 either way" cannot pass:
            # the message names this script and the config's own error type.
            self.assertIn("adr-signals:", proc.stderr)
            self.assertIn("BionicConfigError", proc.stderr)
            # The defect this pins: a raw traceback rather than a message.
            self.assertNotIn("Traceback", proc.stderr)
            self.assertNotIn('File "', proc.stderr)
            self.assertEqual(len(proc.stderr.strip().splitlines()), 1)

            # PAIRED POSITIVE CONTROL. The same synthetic root, differing in
            # `docs_dir` alone, reaches the documented document lane instead:
            # not exit 2, JSON on stdout, no config error on stderr. Without
            # this, the assertion above would also hold for a script that
            # exits 2 on every root.
            ok_root = self._root(str(Path(tmp) / "ok"), "bionic")
            ok = _run("--repo-root", str(ok_root), "--today", TODAY.isoformat(),
                      "--json")
            self.assertNotEqual(ok.returncode, 2, ok.stderr)
            self.assertTrue(json.loads(ok.stdout))
            self.assertNotIn("BionicConfigError", ok.stderr)

    def test_the_config_error_is_routed_through_redact_and_bounded(self):
        """The message is REDACTED, not merely caught.

        `bionic_config` renders the offending `docs_dir` with `{value!r}`, so
        an 8000-character value reaches stderr whole unless the handler bounds
        it. The truncation note is `redact`'s own, which no bare `str(exc)`
        can produce.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, "../" + "z" * 8000)
            proc = _run("--repo-root", str(root), "--today", TODAY.isoformat(),
                        "--json")
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertEqual(proc.stdout, "")
            self.assertIn("truncated from", proc.stderr)
            self.assertLess(len(proc.stderr), 8000)

            # PAIRED POSITIVE CONTROL for the bound: a SHORT malformed value
            # travels the same lane and is NOT truncated, so the note above
            # tracks the value's length rather than appearing unconditionally.
            short = self._root(str(Path(tmp) / "short"), "../outside")
            proc2 = _run("--repo-root", str(short), "--today", TODAY.isoformat(),
                         "--json")
            self.assertEqual(proc2.returncode, 2, proc2.stderr)
            self.assertNotIn("truncated from", proc2.stderr)


# --------------------------------------------------------------------------
# the three delivery signals
# --------------------------------------------------------------------------

GIT = shutil.which("git")

#: The variables that relocate a repository, its object store, or its
#: configuration. `_git_env` drops every one of them, and `SubstrateGuardTests`
#: plants every one of them to prove `_git_environment` inherits none.
#:
#: The last three were missing. `GIT_CONFIG_PARAMETERS` outranks every
#: configuration FILE, so `GIT_CONFIG_GLOBAL=/dev/null` does not close it;
#: `GIT_COMMON_DIR` relocates the object store and was measured sending 36
#: loose objects into a canary repository; `GIT_ALTERNATE_OBJECT_DIRECTORIES`
#: adds one. The tuple is still ILLUSTRATIVE rather than exhaustive — what
#: makes the environment safe is that `_git_environment` builds an ALLOWLIST
#: from nothing and inherits no `GIT_`-prefixed name at all.
REPO_REDIRECT_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                      "GIT_CEILING_DIRECTORIES", "GIT_OBJECT_DIRECTORY",
                      "GIT_COMMON_DIR", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                      "GIT_CONFIG_PARAMETERS")


def _git_env() -> dict[str, str]:
    """The ambient git configuration, neutralized — the pattern already used by
    `_git` in `test_check_blast_radius.py`.

    `-c user.name`/`-c user.email` covers the identity half alone. A machine
    carrying `commit.gpgsign = true`, `tag.gpgSign`, or a global
    `core.hooksPath` failed these fixtures under `check=True` for an
    environment reason rather than a code one.

    An ambient repository redirect is the second half. A shell that exports
    the repository-location variables puts a fixture commit into the
    surrounding checkout's history rather than into the temporary directory
    the test built, so those names are dropped before the identity ones are
    set.
    """
    env = dict(os.environ)
    for redirect in REPO_REDIRECT_VARS:
        env.pop(redirect, None)
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    })
    return env


def _run_git(path: Path | None, *args: str) -> None:
    prefix = ["git"] + (["-C", str(path)] if path is not None else [])
    subprocess.run([*prefix, *args], check=True, capture_output=True, env=_git_env())


def _init_repo(path: Path) -> None:
    _run_git(None, "init", "-q", str(path))


def _commit(path: Path, subject: str) -> None:
    _run_git(path, "add", "-A")
    _run_git(path, "commit", "-q", "--allow-empty", "-m", subject)


def _tag(path: Path, name: str) -> None:
    _run_git(path, "tag", name)


def _branch(path: Path, name: str) -> None:
    """A BRANCH of the given name, under the heads namespace alone."""
    _run_git(path, "branch", name)


def _ref_resolves(path: Path, ref: str) -> bool:
    """True when the fully qualified `ref` exists in this fixture repository."""
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--verify", "--quiet", ref],
        capture_output=True, env=_git_env()).returncode == 0


def _annotated_tag(path: Path, name: str) -> None:
    """An ANNOTATED tag, whose ref resolves to a tag object and not a commit."""
    _run_git(path, "tag", "-a", name, "-m", name)


THREE_RELEASE_CHANGELOG = """# Changelog

## [Unreleased]

### Added

## [1.2.0] — 2026-01-26

### Added
- The third fictitious release.

## [1.1.0] — 2026-01-11

### Added
- The second fictitious release.

## [1.0.0] — 2026-01-01

### Added
- The first fictitious release.
"""

TWO_RELEASE_CHANGELOG = (
    "# Changelog\n\n## [1.1.0] — 2026-01-11\n\n- b\n\n"
    "## [1.0.0] — 2026-01-01\n\n- a\n"
)


#: Progressive CHANGELOG.md snapshots — each stage introduces exactly one
#: dated heading over the last, without ever touching an already-dated one.
#: Committed in sequence, each stage's commit becomes that version's release
#: mark: the predicate (present in this blob, absent from the first-parent
#: parent's) fires exactly once per version.
CHANGELOG_SEED = "# Changelog\n\n## [Unreleased]\n\n### Added\n"

CHANGELOG_WITH_1_0_0 = (
    "# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
    "## [1.0.0] — 2026-01-01\n\n### Added\n- The first fictitious release.\n"
)

CHANGELOG_WITH_1_0_0_AND_1_1_0 = (
    "# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
    "## [1.1.0] — 2026-01-11\n\n### Added\n- The second fictitious release.\n\n"
    "## [1.0.0] — 2026-01-01\n\n### Added\n- The first fictitious release.\n"
)
# `CHANGELOG_WITH_1_0_0_AND_1_1_0` plus a 1.2.0 section is
# `THREE_RELEASE_CHANGELOG`, defined above.


class ReleaseCadenceTests(unittest.TestCase):
    def _cadence(self, root: Path) -> dict:
        return sig.signal_release_cadence(root, "bionic")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_computed_over_a_repo_with_three_release_markers(self):
        """Each dated heading is introduced by ITS OWN commit, so each
        version resolves to a distinct release mark, and it is that
        mark-bounded interval — never a subject scan — that `span_commits`
        and `prep_commits` are computed over.

        Independently hand-calculated: walking first-parent history
        newest-first gives [v1.2.0-prep, work-d, v1.1.0-prep, work-c, work-b,
        v1.0.0-prep, work-a, seed]. 1.1.0's interval EXCLUDES 1.0.0's mark and
        INCLUDES its own: {v1.1.0-prep, work-c, work-b} — 3 commits, 1 of
        them a declared preparation commit. 1.2.0's interval is
        {v1.2.0-prep, work-d} — 2 commits, 1 preparation. 1.0.0 is the oldest
        release: it has no previous release at all, so its interval is
        unbounded — null on both members, never a guess at "runs to the end
        of history".
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            _commit(root, "work a")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            _commit(root, "work b")
            _commit(root, "work c")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0_AND_1_1_0,
                                               encoding="utf-8")
            _commit(root, "Release prep v1.1.0")
            _commit(root, "work d")
            (root / "CHANGELOG.md").write_text(THREE_RELEASE_CHANGELOG, encoding="utf-8")
            _commit(root, "Release prep v1.2.0")
            _tag(root, "v1.2.0")

            rec = self._cadence(root)
            self.assertEqual(rec["verdict"], "computed")
            # The four changelog-only members: 2026-01-01 -> 01-11 -> 01-26.
            self.assertEqual(rec["value"]["releases"], 3)
            self.assertEqual(rec["value"]["intervals_days"], [10, 15])
            self.assertEqual(rec["value"]["mean_interval_days"], 12.5)
            self.assertEqual(rec["value"]["median_interval_days"], 12.5)
            # The two git-dependent, mark-bounded members. Keys are
            # `repr()`-delimited, so a reader can see where each version
            # starts and ends.
            self.assertEqual(rec["value"]["span_commits"],
                             {"'1.0.0'": None, "'1.1.0'": 3, "'1.2.0'": 2})
            self.assertEqual(rec["value"]["prep_commits"],
                             {"'1.0.0'": None, "'1.1.0'": 1, "'1.2.0'": 1})
            # Both rejected markers, with the coverage measured on this run,
            # plus the release-mark resolution stats.
            self.assertIn("1 of 3", rec["filter"])   # tags
            self.assertIn("3 of 3 dated headings resolve", rec["filter"])
            self.assertIn("2 of 3 releases have a bounded interval", rec["filter"])

    def test_unmeasurable_in_a_directory_carrying_no_changelog(self):
        # `quiet/` carries no CHANGELOG.md and is not a work tree. This
        # signal's measurability rests on the changelog, so the reason it
        # reports is the absent changelog and never the absent repository.
        rec = self._cadence(QUIET)
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        self.assertIn("CHANGELOG.md", rec["filter"])
        self.assertIn("absent", rec["filter"])

    def test_a_heading_shaped_like_a_date_but_not_one_is_not_a_dated_heading(self):
        """`2026-13-45` matches the heading SHAPE and is no calendar date.

        `dt.date.fromisoformat` raised on it, the ValueError escaped into
        `main`'s blanket handler, and ALL EIGHT signals collapsed into the
        exit-2 environment lane. One typo in a repo-content file is not an
        environment failure: the heading is not a dated heading, so this
        signal reports the condition requirement 1 names and every other
        signal keeps its verdict.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [1.0.0] — 2026-13-45\n\n## [0.9.0] — 2026-01-01\n",
                encoding="utf-8")
            rec = self._cadence(root)
            self.assertEqual(rec["verdict"], "unmeasurable")
            self.assertIn("fewer than two", rec["filter"])
            # Positive control: the SAME file with a real date computes, so the
            # refusal is the malformed date and not the two-heading count.
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [1.0.0] — 2026-01-11\n\n## [0.9.0] — 2026-01-01\n",
                encoding="utf-8")
            self.assertEqual(self._cadence(root)["verdict"], "computed")

    def test_unmeasurable_with_fewer_than_two_dated_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] — 2026-01-01\n\n- one\n",
                encoding="utf-8")
            rec = self._cadence(root)
            self.assertEqual(rec["verdict"], "unmeasurable")
            self.assertIsNone(rec["value"])
            self.assertIn("fewer than two", rec["filter"])
            # Positive control: the SAME reader over a three-heading changelog
            # computes, so the refusal is the count and not a dead parser.
            (root / "CHANGELOG.md").write_text(THREE_RELEASE_CHANGELOG, encoding="utf-8")
            self.assertEqual(self._cadence(root)["verdict"], "computed")

    def test_a_failed_leg_leaves_span_and_prep_commits_null_and_keeps_computed(self):
        # A changelog with no repository around it: the contained git session
        # cannot be established, so `span_commits` and `prep_commits` are
        # null for every release and the verdict stays `computed` — the
        # four changelog-only members are unaffected.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text(THREE_RELEASE_CHANGELOG, encoding="utf-8")
            rec = self._cadence(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(rec["value"]["span_commits"],
                             {"'1.0.0'": None, "'1.1.0'": None, "'1.2.0'": None})
            self.assertEqual(rec["value"]["prep_commits"],
                             {"'1.0.0'": None, "'1.1.0'": None, "'1.2.0'": None})
            # The computed verdict is real: the changelog legs measured.
            self.assertEqual(rec["value"]["intervals_days"], [10, 15])
            # The filter says the coverage was not measured rather than
            # printing a hardcoded number.
            self.assertIn("not measured", rec["filter"])

    def test_the_fixture_changelog_computes_with_null_span_and_prep_commits(self):
        # `trips/` is a plain directory copy with no `.git` at all, so the
        # contained git session cannot be established there either.
        rec = self._cadence(TRIPS)
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"]["intervals_days"], [5, 15])
        self.assertTrue(all(v is None for v in rec["value"]["span_commits"].values()))
        self.assertTrue(all(v is None for v in rec["value"]["prep_commits"].values()))


# --------------------------------------------------------------------------
# ADR-0109 — the release mark: `resolve_release_marks` and the interval it
# bounds. Each case below is independently hand-calculated in its own
# comment, never asserted by calling the function under test a second time.
# --------------------------------------------------------------------------

class ReleaseMarkTests(unittest.TestCase):
    def _marks(self, root: Path):
        legs = sig._GitLegs(root)
        self.assertTrue(legs.usable, legs.reason)
        marks, conditions, _capped = sig.resolve_release_marks(legs)
        return marks, conditions

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_an_unmatched_heading_resolves_no_mark_and_never_widens_a_span(self):
        """SCENARIO 2 — a missing release boundary reads null, never a
        widened span. `1.1.0`'s heading is written to the WORKING TREE only
        and never committed, so no commit satisfies the mark predicate for
        it: it is a key of neither `marks` nor `conditions` at all — the
        "no commit ever introduces this heading" case.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            _commit(root, "work a")
            # 1.1.0 lands on disk but is never committed.
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0_AND_1_1_0,
                                               encoding="utf-8")

            marks, conditions = self._marks(root)
            self.assertIn("1.0.0", marks)
            self.assertNotIn("1.1.0", marks)
            self.assertNotIn("1.1.0", conditions)

            # Through the real signal, taken WHILE 1.1.0 is still
            # uncommitted: its interval is unbounded — null, never a guess
            # that widens the span to "the rest of history".
            rec = sig.signal_release_cadence(root, "bionic")
            self.assertIsNone(rec["value"]["span_commits"]["'1.1.0'"])
            self.assertIsNone(rec["value"]["prep_commits"]["'1.1.0'"])

            # PAIRED POSITIVE CONTROL: committing that same content DOES
            # resolve a mark for 1.1.0, so the null above is the missing
            # commit and not a reader that never resolves a second version.
            _commit(root, "Release prep v1.1.0")
            marks2, conditions2 = self._marks(root)
            self.assertIn("1.1.0", marks2)
            self.assertEqual(conditions2, {})
            control = sig.signal_release_cadence(root, "bionic")
            self.assertIsNotNone(control["value"]["span_commits"]["'1.1.0'"])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_two_prep_declarations_for_one_version_are_one_key_not_two(self):
        """SCENARIO 4 — a version published to two targets (beta and
        official) is ONE version and ONE key. Modelled here as two
        "Release prep" commits inside the SAME release's interval — one
        that only declares the release, and the one that actually
        introduces its heading (and so becomes its mark) — so
        `prep_commits` counts both under the single `'1.1.0'` key rather
        than splitting into two.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            # A "beta" prep declaration, no changelog change yet — it sits
            # INSIDE 1.1.0's future interval, before the commit that
            # actually introduces the heading.
            _commit(root, "Release prep v1.1.0 beta")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0_AND_1_1_0,
                                               encoding="utf-8")
            _commit(root, "Release prep v1.1.0 official")

            rec = sig.signal_release_cadence(root, "bionic")
            self.assertEqual(rec["verdict"], "computed")
            # ONE key for 1.1.0 — never two, and never a publication-event
            # key this repository holds no evidence for.
            self.assertEqual(sorted(rec["value"]["prep_commits"]),
                             ["'1.0.0'", "'1.1.0'"])
            self.assertEqual(rec["value"]["prep_commits"]["'1.1.0'"], 2)
            self.assertEqual(rec["value"]["span_commits"]["'1.1.0'"], 2)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_failed_beta_followed_by_a_new_version_is_two_versions_two_keys(self):
        """SCENARIO 5 — a failed beta (1.1.0, never actually shipped as such
        in the changelog) followed by a genuinely new version (1.1.1) is TWO
        distinct versions and TWO distinct keys, each with its own mark.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0_AND_1_1_0,
                                               encoding="utf-8")
            _commit(root, "Release prep v1.1.0")
            # The 1.1.0 beta failed; 1.1.1 is the actual next release.
            failed_and_real = (
                "# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
                "## [1.1.1] — 2026-01-15\n\n### Added\n- The real release.\n\n"
                "## [1.1.0] — 2026-01-11\n\n### Added\n- The second fictitious release.\n\n"
                "## [1.0.0] — 2026-01-01\n\n### Added\n- The first fictitious release.\n"
            )
            (root / "CHANGELOG.md").write_text(failed_and_real, encoding="utf-8")
            _commit(root, "Release prep v1.1.1")

            marks, conditions = self._marks(root)
            self.assertIn("1.1.0", marks)
            self.assertIn("1.1.1", marks)
            self.assertNotEqual(marks["1.1.0"], marks["1.1.1"])
            self.assertEqual(conditions, {})

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_shared_mark_reads_null_for_both_sharing_versions(self):
        """SCENARIO 6 — two versions introduced by the SAME commit share a
        mark that separates neither of them: both read
        `"baseline-ref-ambiguous"`, never an arbitrary tie-break.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            # One commit introduces BOTH 1.1.0 and 1.2.0 at once.
            both_at_once = (
                "# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
                "## [1.2.0] — 2026-01-26\n\n### Added\n- c.\n\n"
                "## [1.1.0] — 2026-01-11\n\n### Added\n- b.\n\n"
                "## [1.0.0] — 2026-01-01\n\n### Added\n- a.\n"
            )
            (root / "CHANGELOG.md").write_text(both_at_once, encoding="utf-8")
            _commit(root, "Release prep v1.1.0 and v1.2.0 together")

            marks, conditions = self._marks(root)
            self.assertNotIn("1.1.0", marks)
            self.assertNotIn("1.2.0", marks)
            self.assertEqual(conditions["1.1.0"], "baseline-ref-ambiguous")
            self.assertEqual(conditions["1.2.0"], "baseline-ref-ambiguous")
            # PAIRED POSITIVE CONTROL: 1.0.0, introduced alone, resolves.
            self.assertIn("1.0.0", marks)

            rec = sig.signal_release_cadence(root, "bionic")
            self.assertIsNone(rec["value"]["span_commits"]["'1.1.0'"])
            self.assertIsNone(rec["value"]["span_commits"]["'1.2.0'"])
            self.assertIsNone(rec["value"]["prep_commits"]["'1.1.0'"])
            self.assertIsNone(rec["value"]["prep_commits"]["'1.2.0'"])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_duplicate_mark_candidates_from_removal_and_restoration_read_null(self):
        """SCENARIO 7 — a heading removed and later restored satisfies the
        mark predicate at MORE THAN ONE commit, so the version has no single
        mark: `"baseline-ref-ambiguous"`, on the same footing as a shared
        mark rather than resolving to whichever commit a walk reached first.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")   # candidate #1
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "accidentally drop the 1.0.0 heading")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "restore the 1.0.0 heading")   # candidate #2

            marks, conditions = self._marks(root)
            self.assertNotIn("1.0.0", marks)
            self.assertEqual(conditions["1.0.0"], "baseline-ref-ambiguous")

            # PAIRED POSITIVE CONTROL: the same heading, introduced exactly
            # once and never removed, resolves cleanly.
            with tempfile.TemporaryDirectory() as tmp2:
                control_root = Path(tmp2)
                _init_repo(control_root)
                (control_root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
                _commit(control_root, "seed")
                (control_root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0,
                                                           encoding="utf-8")
                _commit(control_root, "Release prep v1.0.0")
                control_marks, control_conditions = self._marks(control_root)
                self.assertIn("1.0.0", control_marks)
                self.assertEqual(control_conditions, {})

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_root_commit_carrying_several_headings_reads_null_for_all(self):
        """SCENARIO 8 — a ROOT COMMIT SATISFIES THE PREDICATE'S SECOND HALF
        VACUOUSLY, because nothing precedes it: a heading present there was
        introduced there. Where the root commit already carries several
        dated headings — this repository's own 0.1.0 through 0.7.0 at
        `1f00a91fde` — every one of them shares that single mark and reads
        null, on the shared-mark footing rather than the unresolved one.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            root_changelog = (
                "# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
                "## [0.2.0] — 2026-01-05\n\n### Added\n- b.\n\n"
                "## [0.1.0] — 2026-01-01\n\n### Added\n- a.\n"
            )
            (root / "CHANGELOG.md").write_text(root_changelog, encoding="utf-8")
            _commit(root, "the root commit, already carrying two dated headings")
            (root / "CHANGELOG.md").write_text(
                root_changelog.replace(
                    "## [Unreleased]\n\n### Added\n\n",
                    "## [Unreleased]\n\n### Added\n\n"
                    "## [0.3.0] — 2026-01-20\n\n### Added\n- c.\n\n"),
                encoding="utf-8")
            _commit(root, "Release prep v0.3.0")

            marks, conditions = self._marks(root)
            self.assertNotIn("0.1.0", marks)
            self.assertNotIn("0.2.0", marks)
            self.assertEqual(conditions["0.1.0"], "baseline-ref-ambiguous")
            self.assertEqual(conditions["0.2.0"], "baseline-ref-ambiguous")
            # PAIRED POSITIVE CONTROL: 0.3.0, introduced by its own later
            # commit, resolves normally — the null above is the shared root
            # mark and not a reader that resolves nothing.
            self.assertIn("0.3.0", marks)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_determinism_the_same_repository_state_yields_the_same_json_twice(self):
        """SCENARIO 10 — the signal is deterministic: the same repository
        state, read twice, produces byte-identical JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            _commit(root, "work a")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0_AND_1_1_0,
                                               encoding="utf-8")
            _commit(root, "Release prep v1.1.0")

            first = json.dumps(sig.signal_release_cadence(root, "bionic"), sort_keys=True)
            second = json.dumps(sig.signal_release_cadence(root, "bionic"), sort_keys=True)
            self.assertEqual(first, second)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_no_network_and_no_writes(self):
        """SCENARIO 11 — the release-mark walk opens no socket and writes no
        file. The fixture repository's tree, mtimes aside, is byte-identical
        before and after, and a patched `socket.socket` that raises on
        construction is never triggered.
        """
        import socket as socket_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            _commit(root, "work a")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0_AND_1_1_0,
                                               encoding="utf-8")
            _commit(root, "Release prep v1.1.0")

            def _refuse_socket(*_args, **_kwargs):
                raise AssertionError("signal_release_cadence opened a socket")

            before = {
                p: p.stat().st_size
                for p in sorted(root.rglob("*")) if p.is_file()
            }
            with unittest.mock.patch.object(socket_module, "socket", _refuse_socket):
                rec = sig.signal_release_cadence(root, "bionic")
            after = {
                p: p.stat().st_size
                for p in sorted(root.rglob("*")) if p.is_file()
            }
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(before, after)


def _schema_growth_release_commit(root: Path, version: str, date: str,
                                  note: str = "release") -> None:
    """Commit a NEW dated changelog heading for `version`, prepended above
    whatever headings already exist — so each release lands in its OWN
    commit and gets its own, unshared release mark, unlike `TWO_RELEASE_CHANGELOG`
    / `THREE_RELEASE_CHANGELOG` above (whole file written once, before any
    commit, which is exactly the SHARED-mark shape ADR-0109 also covers).
    """
    path = root / "CHANGELOG.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Changelog\n\n"
    header, sep, rest = existing.partition("\n\n")
    heading = f"## [{version}] — {date}\n\n- {note}\n\n"
    path.write_text(header + sep + heading + rest, encoding="utf-8")
    _commit(root, f"release {version}")



class BoundarySelectionTests(unittest.TestCase):
    """WHICH marks bound an interval or a baseline — the half of the mark
    machinery a mutation pass found unconstrained. The interval arithmetic
    itself is pinned elsewhere; every test here changes the SELECTION and
    states the value a mutant of the named branch would produce instead.
    """

    def _cadence(self, root: Path) -> dict:
        return sig.signal_release_cadence(root, "bionic")

    def _growth(self, root: Path) -> dict:
        return sig.signal_schema_growth(root, root / "bionic", "bionic")

    @staticmethod
    def _seed(root: Path, n: int) -> None:
        """A crux-shaped dev repo whose two schema surfaces both measure `n`."""
        (root / "bionic").mkdir(exist_ok=True)
        (root / "bionic" / "CLAUDE.md").write_text("x\n" * n, encoding="utf-8")
        catalog = root / "crux" / "catalog"
        catalog.mkdir(parents=True, exist_ok=True)
        (catalog / "skills.json").write_text(
            json.dumps([{"id": str(k)} for k in range(n)]), encoding="utf-8")
        (root / "crux" / "scripts").mkdir(parents=True, exist_ok=True)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_the_baseline_is_the_second_newest_release_never_the_oldest(self):
        """Three releases with distinct marks separate the two positions.
        Every other schema-growth fixture has exactly two, where the oldest
        IS the second-newest and a mutant reading either passes.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            for n, (version, date) in enumerate(
                    [("1.0.0", "2026-01-01"), ("1.1.0", "2026-01-11"),
                     ("1.2.0", "2026-01-21")], start=1):
                self._seed(root, n)
                _schema_growth_release_commit(root, version, date)

            value = self._growth(root)["value"]
            self.assertEqual(value["baseline"]["release"], "'1.1.0'")
            self.assertEqual(value["baseline"]["claude_md_lines"], 2)
            self.assertEqual(value["current"]["claude_md_lines"], 3)
            self.assertEqual(value["conditions"], [])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_ambiguity_at_the_NEWEST_position_refuses_the_baseline(self):
        """The walk reads two positions and either may fail. Here the
        SECOND-NEWEST resolves cleanly and only the newest is ambiguous —
        the existing ambiguity fixtures make both fail at once, so a mutant
        that checks only the second-newest survives them.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._seed(root, 2)
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            self._seed(root, 3)
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")
            changelog = root / "CHANGELOG.md"
            whole = changelog.read_text(encoding="utf-8")
            # Removing the newest heading and restoring it gives 1.1.0 two
            # commits satisfying the predicate; 1.0.0 keeps its single mark.
            changelog.write_text(
                whole.replace("## [1.1.0] — 2026-01-11\n\n- release\n\n", ""),
                encoding="utf-8")
            _commit(root, "drop the newest heading")
            changelog.write_text(whole, encoding="utf-8")
            _commit(root, "restore it")

            value = self._growth(root)["value"]
            self.assertIn({"condition": "baseline-ref-ambiguous"},
                          value["conditions"])
            self.assertIsNone(value["baseline"]["ref"])
            # PAIRED POSITIVE CONTROL: 1.0.0, the second-newest, DID resolve
            # to a single mark — the refusal is the newest position's.
            legs = sig._GitLegs(root)
            marks, conditions, _capped = sig.resolve_release_marks(legs)
            self.assertIn("1.0.0", marks)
            self.assertEqual(conditions.get("1.1.0"), "baseline-ref-ambiguous")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_version_past_the_walk_cap_names_unresolved(self):
        """`baseline-ref-unresolved` from the walk itself. Any heading at
        HEAD is introduced somewhere on first-parent — vacuously at the root
        — so the cap is the only way this branch is reached in a committed
        repository, and no test referenced the cap.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._seed(root, 2)
            for version, date in [("1.0.0", "2026-01-01"),
                                  ("1.1.0", "2026-01-11"),
                                  ("1.2.0", "2026-01-21")]:
                _schema_growth_release_commit(root, version, date)

            with unittest.mock.patch.object(sig, "RELEASE_MARK_WALK_CAP", 1):
                legs = sig._GitLegs(root)
                marks, conditions, _capped = sig.resolve_release_marks(legs)
                self.assertEqual(sorted(marks), ["1.2.0"])
                self.assertEqual(conditions["1.0.0"], "baseline-ref-unresolved")
                self.assertEqual(conditions["1.1.0"], "baseline-ref-unresolved")
                capped = self._growth(root)["value"]
            self.assertIn({"condition": "baseline-ref-unresolved"},
                          capped["conditions"])

            # PAIRED POSITIVE CONTROL: the same repository at the real cap
            # resolves every version and names no condition at all.
            uncapped = self._growth(root)["value"]
            self.assertEqual(uncapped["conditions"], [])
            self.assertEqual(uncapped["baseline"]["release"], "'1.1.0'")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_the_filter_says_whether_the_walk_stopped_at_the_cap(self):
        """A version past the cap reads `baseline-ref-unresolved`, and
        glossing that as "no commit satisfies the predicate" would assert an
        absence the walk did not establish. The note says which case it is.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._seed(root, 2)
            for version, date in [("1.0.0", "2026-01-01"),
                                  ("1.1.0", "2026-01-11"),
                                  ("1.2.0", "2026-01-21")]:
                _schema_growth_release_commit(root, version, date)

            with unittest.mock.patch.object(sig, "RELEASE_MARK_WALK_CAP", 1):
                capped = self._cadence(root)["filter"]
            whole = self._cadence(root)["filter"]

            # Asserted as a DISJUNCTION over the two cases rather than as a
            # set of literal phrases: what the rule requires is that the note
            # tell the two apart, and pinning the wording would fail on any
            # rewrite that still did.
            truncated = "stopped at the cap"
            complete = "read every touching commit"
            self.assertIn(truncated, capped)
            self.assertNotIn(complete, capped)
            self.assertIn(complete, whole)
            self.assertNotIn(truncated, whole)
            # And the gloss on `unresolved` is qualified only in the capped
            # case, because only there is the unqualified claim false.
            self.assertIn("no commit the walk read satisfies", capped)
            self.assertIn("no commit satisfies the mark predicate", whole)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_backdated_heading_never_wraps_to_the_newest_release(self):
        """`2.0.0` is committed BEFORE `1.0.0` but dated after it, so date
        order and commit order disagree. The oldest release by date has no
        predecessor and reads null; the newer one's own mark is OLDER in
        commit order than its predecessor's, which is also null. A mutant
        wrapping the oldest to the newest gives it a bounded interval
        against a release that is not its predecessor.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text("# Changelog\n\n", encoding="utf-8")
            _commit(root, "seed")
            _schema_growth_release_commit(root, "2.0.0", "2026-02-01")
            _commit(root, "work a")
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            _commit(root, "work b")

            value = self._cadence(root)["value"]
            self.assertEqual(value["span_commits"],
                             {"'1.0.0'": None, "'2.0.0'": None})
            self.assertEqual(value["prep_commits"],
                             {"'1.0.0'": None, "'2.0.0'": None})
            # PAIRED POSITIVE CONTROL: both marks DID resolve — the nulls are
            # the boundary guard's, not a failure to find the marks.
            marks, conditions, _capped = sig.resolve_release_marks(sig._GitLegs(root))
            self.assertEqual(sorted(marks), ["1.0.0", "2.0.0"])
            self.assertEqual(conditions, {})

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_two_releases_dated_the_same_day_order_by_file_position(self):
        """A shared DATE is not a shared mark. The two headings have
        distinct marks, so they are ordered — by their position in the file,
        newest at the top — rather than collapsed into one interval.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text("# Changelog\n\n", encoding="utf-8")
            _commit(root, "seed")
            _commit(root, "work a")
            _schema_growth_release_commit(root, "1.0.1", "2026-01-05")
            _commit(root, "work b")
            _commit(root, "work c")
            _schema_growth_release_commit(root, "1.0.2", "2026-01-05")

            value = self._cadence(root)["value"]
            # 1.0.2 sits above 1.0.1 in the file, so it is the newer of the
            # two: its interval is {its own mark, work c, work b} = 3.
            self.assertEqual(value["span_commits"]["'1.0.2'"], 3)
            # 1.0.1 is then the oldest release and has no predecessor.
            self.assertIsNone(value["span_commits"]["'1.0.1'"])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_malformed_surface_at_the_baseline_is_null_never_zero(self):
        """Zero is a measurement. A catalog that does not parse at the
        baseline leaves that member null with `surface-malformed` named at
        the endpoint it failed at — a mutant returning 0 reports a
        measurement nobody made and the condition disappears with it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._seed(root, 2)
            (root / "crux" / "catalog" / "skills.json").write_text(
                "{not json", encoding="utf-8")
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            self._seed(root, 3)
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")

            value = self._growth(root)["value"]
            self.assertIn({"condition": "surface-malformed",
                           "endpoint": "baseline", "surface": "skills"},
                          value["conditions"])
            self.assertIsNone(value["baseline"]["skills"])
            # PAIRED POSITIVE CONTROL: the OTHER surface read cleanly at both
            # ends, so the null is this surface's and not a dead reader.
            self.assertEqual(value["baseline"]["claude_md_lines"], 2)
            self.assertEqual(value["current"]["skills"], 3)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_first_parent_leg_that_did_not_run_leaves_both_members_null(self):
        """The per-release members rest on the first-parent walk. A leg that
        did not run supplies no commits — which is not a count of zero.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._seed(root, 2)
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")

            with unittest.mock.patch.object(sig, "_first_parent_commits",
                                            return_value=None):
                value = self._cadence(root)["value"]
            self.assertTrue(all(v is None for v in value["span_commits"].values()),
                            value["span_commits"])
            self.assertTrue(all(v is None for v in value["prep_commits"].values()),
                            value["prep_commits"])
            # PAIRED POSITIVE CONTROL: the changelog-only members still
            # computed, so the nulls are the walk's and not the signal's.
            self.assertEqual(value["releases"], 2)

class LegFailureConditionTests(unittest.TestCase):
    """The conditions a FAILED GIT LEG produces, as distinct from the ones an
    absent or malformed surface produces. Every one below survived mutation
    before these tests existed — `surface-unreadable` had no test at all, and
    renaming both its emissions to `surface-absent` left the suite green.
    """

    def _growth(self, root: Path) -> dict:
        return sig.signal_schema_growth(root, root / "bionic", "bionic")

    def _cadence(self, root: Path) -> dict:
        return sig.signal_release_cadence(root, "bionic")

    @staticmethod
    def _seed(root: Path, n: int) -> None:
        (root / "bionic").mkdir(exist_ok=True)
        (root / "bionic" / "CLAUDE.md").write_text("x\n" * n, encoding="utf-8")
        catalog = root / "crux" / "catalog"
        catalog.mkdir(parents=True, exist_ok=True)
        (catalog / "skills.json").write_text(
            json.dumps([{"id": str(k)} for k in range(n)]), encoding="utf-8")
        (root / "crux" / "scripts").mkdir(parents=True, exist_ok=True)

    def _two_releases(self, root: Path) -> None:
        _init_repo(root)
        self._seed(root, 2)
        _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
        self._seed(root, 3)
        _schema_growth_release_commit(root, "1.1.0", "2026-01-11")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_failed_listing_leg_names_unreadable_never_absent(self):
        """`surface-absent` means the ref resolved and the path is not there.
        A leg that DID NOT RUN establishes neither, so it is `unreadable` —
        the two are different situations and the closed set names each once.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_releases(root)
            real = sig._GitLegs.lines

            def fail_ls_tree(self, *args):
                if args and args[0] == "ls-tree":
                    return None
                return real(self, *args)

            with unittest.mock.patch.object(sig._GitLegs, "lines", fail_ls_tree):
                conditions = self._growth(root)["value"]["conditions"]
            named = {c["condition"] for c in conditions}
            self.assertIn("surface-unreadable", named)
            self.assertNotIn("surface-absent", named)

            # PAIRED POSITIVE CONTROL: the same repository with the leg
            # running names no surface condition at all.
            self.assertEqual(self._growth(root)["value"]["conditions"], [])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_failed_blob_leg_names_unreadable_at_its_own_endpoint(self):
        """The path IS present and the read failed — the second of the two
        sites emitting this condition, and it names the endpoint it hit."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_releases(root)

            with unittest.mock.patch.object(sig._GitLegs, "blob",
                                            return_value=None):
                conditions = self._growth(root)["value"]["conditions"]
            unreadable = [c for c in conditions
                          if c["condition"] == "surface-unreadable"]
            self.assertTrue(unreadable, conditions)
            for entry in unreadable:
                self.assertIn(entry["endpoint"], ("baseline", "current"))
                self.assertIn(entry["surface"], ("claude_md_lines", "skills"))

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_failed_mark_walk_leg_is_named_at_both_signals(self):
        """`resolve_release_marks` returning None — the walk itself could not
        run, which is not the same as a version it ran and could not
        resolve. Both consumers name it rather than reporting a bare null.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_releases(root)
            real = sig._GitLegs.lines

            def fail_touch_walk(self, *args):
                if args[:2] == ("log", "--first-parent"):
                    return None
                return real(self, *args)

            with unittest.mock.patch.object(sig._GitLegs, "lines",
                                            fail_touch_walk):
                cadence = self._cadence(root)
                growth = self._growth(root)

            self.assertIn("the release-mark walk over CHANGELOG.md's touching "
                          "commits did not run", cadence["filter"])
            self.assertIn({"condition": "baseline-ref-unresolved"},
                          growth["value"]["conditions"])
            # PAIRED POSITIVE CONTROL: the changelog-only members still
            # computed, so the signal reports what it could still measure.
            self.assertEqual(cadence["value"]["releases"], 2)
            self.assertEqual(cadence["verdict"], "computed")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_one_dated_heading_is_no_release_record_for_schema_growth(self):
        """The threshold is TWO headings, because the baseline is the
        second-newest. Pinned at its boundary for this signal, as it already
        was for release_cadence.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._seed(root, 2)
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")

            conditions = self._growth(root)["value"]["conditions"]
            self.assertIn({"condition": "no-release-record"}, conditions)

            # PAIRED POSITIVE CONTROL: adding the SECOND heading — one more
            # than the threshold — clears the condition entirely.
            self._seed(root, 3)
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")
            self.assertEqual(self._growth(root)["value"]["conditions"], [])

class SchemaGrowthTests(unittest.TestCase):
    """`schema_growth`'s baseline is a RELEASE MARK (a commit), never a tag —
    rule:baseline-is-a-release-mark-and-unavailable-is-named.
    """

    def _growth(self, root: Path) -> dict:
        return sig.signal_schema_growth(root, root / "bionic", "bionic")

    @staticmethod
    def _seed(root: Path, claude_lines: int, skills: int) -> None:
        (root / "bionic").mkdir(exist_ok=True)
        (root / "bionic" / "CLAUDE.md").write_text(
            "".join(f"line {i}\n" for i in range(claude_lines)), encoding="utf-8")
        catalog = root / "crux" / "catalog"
        catalog.mkdir(parents=True, exist_ok=True)
        (catalog / "skills.json").write_text(
            json.dumps([{"id": f"skill-{i}"} for i in range(skills)]), encoding="utf-8")

    @staticmethod
    def _dev_repo(root: Path) -> None:
        """The structural marker `_schema_growth_is_dev_repo` reads."""
        (root / "crux" / "scripts").mkdir(parents=True, exist_ok=True)

    def _two_release_dev_repo(self, root: Path, *, baseline_claude=4, baseline_skills=2,
                              current_claude=9, current_skills=5):
        # The seed for a release's own snapshot is written and staged BEFORE
        # `_schema_growth_release_commit` commits — so the RELEASE MARK
        # commit (the one introducing that version's heading) is also the
        # commit that carries that release's schema state, exactly as a real
        # release does. Seeding AFTER the release commit would put the
        # baseline's own content one commit later than its mark.
        _init_repo(root)
        self._dev_repo(root)
        self._seed(root, claude_lines=baseline_claude, skills=baseline_skills)
        _schema_growth_release_commit(root, "1.0.0", "2026-01-01", note="the baseline release")
        self._seed(root, claude_lines=current_claude, skills=current_skills)
        _schema_growth_release_commit(root, "1.1.0", "2026-01-11",
                                      note="growth since the baseline")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_computed_with_a_baseline_at_the_second_newest_release_mark_positive(self):
        """POSITIVE change: current counts exceed the baseline's."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_release_dev_repo(root, baseline_claude=4, baseline_skills=2,
                                       current_claude=9, current_skills=5)

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(rec["value"]["conditions"], [])
            self.assertEqual(rec["value"]["current"]["claude_md_lines"], 9)
            self.assertEqual(rec["value"]["current"]["skills"], 5)
            self.assertEqual(rec["value"]["baseline"]["release"], "'1.0.0'")
            self.assertEqual(rec["value"]["baseline"]["claude_md_lines"], 4)
            self.assertEqual(rec["value"]["baseline"]["skills"], 2)
            ref = rec["value"]["baseline"]["ref"]
            self.assertRegex(ref, r"^[0-9a-f]{40}$")
            # The locator is a COMMIT, never a tag: no tag was ever created.
            self.assertFalse(_ref_resolves(root, f"refs/tags/{ref}"))

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_computed_with_no_change_between_baseline_and_current(self):
        """ZERO change: current counts equal the baseline's exactly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_release_dev_repo(root, baseline_claude=4, baseline_skills=2,
                                       current_claude=4, current_skills=2)

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(rec["value"]["current"]["claude_md_lines"], 4)
            self.assertEqual(rec["value"]["baseline"]["claude_md_lines"], 4)
            self.assertEqual(rec["value"]["current"]["skills"], 2)
            self.assertEqual(rec["value"]["baseline"]["skills"], 2)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_computed_with_a_negative_change_since_the_baseline(self):
        """NEGATIVE change: current counts are BELOW the baseline's."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_release_dev_repo(root, baseline_claude=9, baseline_skills=5,
                                       current_claude=4, current_skills=2)

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(rec["value"]["current"]["claude_md_lines"], 4)
            self.assertEqual(rec["value"]["baseline"]["claude_md_lines"], 9)
            self.assertLess(rec["value"]["current"]["claude_md_lines"],
                            rec["value"]["baseline"]["claude_md_lines"])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_an_absent_changelog_leaves_the_baseline_unavailable_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._dev_repo(root)
            self._seed(root, claude_lines=9, skills=5)
            _commit(root, "no changelog at all")

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertIsNone(rec["value"]["baseline"]["ref"])
            conditions = rec["value"]["conditions"]
            self.assertIn({"condition": "no-release-record"}, conditions)
            self.assertIn({"condition": "no-baseline", "surface": "claude_md_lines"},
                          conditions)
            self.assertIn({"condition": "no-baseline", "surface": "skills"}, conditions)
            # PAIRED POSITIVE CONTROL: the HEAD leg DID measure — the
            # unavailability is the baseline's, not a dead reader.
            self.assertEqual(rec["value"]["current"]["claude_md_lines"], 9)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_heading_only_in_the_work_tree_names_unresolved_not_a_bare_null(self):
        """The mark predicate reads HEAD's blob; this signal reads the work
        tree. A version declared in the work tree and committed nowhere
        satisfies the predicate at no commit, so it is `baseline-ref-unresolved`
        — never a bare `no-baseline`, which names no reason.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_release_dev_repo(root)
            changelog = root / "CHANGELOG.md"
            changelog.write_text(
                "## [2.0.0] \u2014 2026-02-02\n\n## [1.9.0] \u2014 2026-02-01\n\n"
                + changelog.read_text(encoding="utf-8"), encoding="utf-8")

            rec = self._growth(root)
            conditions = rec["value"]["conditions"]
            named = {c["condition"] for c in conditions}
            self.assertIn("baseline-ref-unresolved", named)
            self.assertIsNone(rec["value"]["baseline"]["ref"])
            # PAIRED POSITIVE CONTROL: the same repo WITHOUT the uncommitted
            # headings resolves a baseline, so the refusal is the work-tree
            # heading's and not this fixture's.
            changelog.write_text(
                changelog.read_text(encoding="utf-8").split(
                    "## [1.9.0] \u2014 2026-02-01\n\n", 1)[1], encoding="utf-8")
            control = self._growth(root)
            self.assertEqual(control["value"]["conditions"], [])
            self.assertRegex(control["value"]["baseline"]["ref"], r"^[0-9a-f]{40}$")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_an_incompatible_baseline_names_not_comparable_never_absent(self):
        """A downstream (non-crux) repo can never carry the skills catalog —
        `surface-not-comparable`, not `surface-absent`, at ANY ref including
        one where the baseline resolves cleanly for `claude_md_lines`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            # Deliberately NOT a crux dev repo: no crux/scripts/ marker.
            (root / "bionic").mkdir()
            (root / "bionic" / "CLAUDE.md").write_text("line 0\n" * 4, encoding="utf-8")
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            (root / "bionic" / "CLAUDE.md").write_text("line 0\n" * 9, encoding="utf-8")
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertIsNotNone(rec["value"]["baseline"]["ref"])
            self.assertIsNone(rec["value"]["current"]["skills"])
            self.assertIsNone(rec["value"]["baseline"]["skills"])
            conditions = rec["value"]["conditions"]
            self.assertIn({"condition": "surface-not-comparable", "surface": "skills"},
                          conditions)
            for entry in conditions:
                self.assertFalse(
                    entry["condition"] == "surface-absent" and entry.get("surface") == "skills",
                    conditions)
            self.assertIn("surface-not-comparable", rec["filter"])
            # claude_md_lines, on the SAME repo and the SAME resolved baseline,
            # compares cleanly — the not-comparable verdict is about the
            # skills SURFACE'S provenance, not about this baseline generally.
            self.assertEqual(rec["value"]["baseline"]["claude_md_lines"], 4)
            self.assertEqual(rec["value"]["current"]["claude_md_lines"], 9)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_shared_mark_names_baseline_ref_ambiguous(self):
        """Two versions introduced in ONE commit share a mark — the real case
        eight early crux versions share at the repository's own root commit.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._dev_repo(root)
            # Both headings land in the SAME commit: TWO_RELEASE_CHANGELOG is
            # written whole, before the first (and only) commit.
            (root / "CHANGELOG.md").write_text(TWO_RELEASE_CHANGELOG, encoding="utf-8")
            self._seed(root, claude_lines=9, skills=5)
            _commit(root, "both releases introduced together")

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertIsNone(rec["value"]["baseline"]["ref"])
            conditions = rec["value"]["conditions"]
            self.assertIn({"condition": "baseline-ref-ambiguous"}, conditions)
        # PAIRED POSITIVE CONTROL: the two-commit, one-heading-per-commit
        # fixture over the SAME two versions resolves cleanly. A SEPARATE
        # temp directory — a nested repo under the ambiguous one above would
        # not be a second, independent repository.
        with tempfile.TemporaryDirectory() as control_tmp:
            control_root = Path(control_tmp)
            self._two_release_dev_repo(control_root)
            control = self._growth(control_root)
            self.assertIsNotNone(control["value"]["baseline"]["ref"])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_removed_and_restored_heading_names_baseline_ref_ambiguous(self):
        """A version satisfying the predicate at MORE THAN ONE commit — the
        duplicate-candidate shape a removed-then-restored heading produces.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._dev_repo(root)
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            self._seed(root, claude_lines=4, skills=2)
            _commit(root, "the baseline release")
            # Remove the 1.0.0 heading, then restore it verbatim: two distinct
            # commits now satisfy the mark predicate for "1.0.0".
            (root / "CHANGELOG.md").write_text("# Changelog\n\n", encoding="utf-8")
            _commit(root, "drop the 1.0.0 heading by mistake")
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01", note="restored")
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")
            self._seed(root, claude_lines=9, skills=5)
            _commit(root, "growth since the baseline")

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertIsNone(rec["value"]["baseline"]["ref"])
            self.assertIn({"condition": "baseline-ref-ambiguous"}, rec["value"]["conditions"])

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_unmeasurable_forces_history_unavailable_with_no_endpoint(self):
        # `quiet/` is not a work tree, so the git session cannot be
        # established. This is the ONE condition that forces `unmeasurable`.
        rec = self._growth(QUIET)
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        self.assertIn("history-unavailable", rec["filter"])
        self.assertIn("history-unavailable", rec["basis"])
        # No endpoint is ever named alongside it — it is a resolution
        # condition, emitted without one.
        self.assertNotIn("endpoint=", rec["filter"])
        # PAIRED POSITIVE CONTROL: a real work tree computes.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_release_dev_repo(root)
            control = self._growth(root)
            self.assertEqual(control["verdict"], "computed")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_surface_failing_at_both_endpoints_names_baseline_only(self):
        """`claude_md_lines` absent at BOTH ends — ONE entry, naming `baseline`
        and never `current` alongside it (the member carries one condition).
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._dev_repo(root)
            # The docs tree never exists at either commit read.
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            _commit(root, "the baseline release, tree never named")
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")
            _commit(root, "growth, tree still never named")

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertIsNone(rec["value"]["current"]["claude_md_lines"])
            self.assertIsNone(rec["value"]["baseline"]["claude_md_lines"])
            matches = [c for c in rec["value"]["conditions"]
                      if c.get("surface") == "claude_md_lines"
                      and c["condition"] == "surface-absent"]
            self.assertEqual(len(matches), 1, rec["value"]["conditions"])
            self.assertEqual(matches[0]["endpoint"], "baseline")

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_determinism_across_two_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._two_release_dev_repo(root)
            first = self._growth(root)
            second = self._growth(root)
            self.assertEqual(first, second)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_zero_is_a_measurement_distinct_from_null(self):
        """An empty skills catalog reports 0; a repo where the catalog never
        existed at that ref reports null. The two are never confused.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            self._dev_repo(root)
            (root / "bionic").mkdir()
            (root / "bionic" / "CLAUDE.md").write_text("line 0\n" * 4, encoding="utf-8")
            catalog = root / "crux" / "catalog"
            catalog.mkdir(parents=True)
            (catalog / "skills.json").write_text("[]", encoding="utf-8")
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01",
                                          note="the baseline release, an EMPTY catalog")
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11",
                                          note="growth, catalog still empty at HEAD")

            rec = self._growth(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(rec["value"]["baseline"]["skills"], 0)
            self.assertEqual(rec["value"]["current"]["skills"], 0)
            self.assertNotIn(
                {"condition": "surface-absent", "endpoint": "baseline", "surface": "skills"},
                rec["value"]["conditions"])


ROSTER_HEADER = "| Output | Source of truth | Regenerator | Drift check |"


class GateCountTests(unittest.TestCase):
    def _gates(self, root: Path) -> dict:
        return sig.signal_gate_count(root, "bionic")

    def test_computed_over_a_root_whose_claude_md_carries_a_roster(self):
        rec = self._gates(TRIPS)
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 2)
        # Positive control that the header row is the input: the fixture's
        # heading above the table spells its count as an English word.
        text = (TRIPS / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(ROSTER_HEADER, text)
        self.assertIn("## Two regenerative outputs", text)

    def test_unmeasurable_over_a_root_with_no_claude_md(self):
        self.assertFalse((QUIET / "CLAUDE.md").exists())
        rec = self._gates(QUIET)
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        # This signal has two unmeasurable branches and BOTH filters name
        # `CLAUDE.md` and `header row`, so neither token tells them apart.
        # Assert the phrase this branch alone carries, and refuse the other's.
        self.assertIn("is absent from the repository root", rec["filter"])
        self.assertNotIn("carries no roster header row", rec["filter"])

    def test_unmeasurable_over_a_claude_md_carrying_no_roster_header_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text(
                "# CLAUDE.md\n\n## Sixteen regenerative outputs\n\n"
                "| a | b |\n|---|---|\n| one | two |\n", encoding="utf-8")
            rec = self._gates(root)
            self.assertEqual(rec["verdict"], "unmeasurable")
            self.assertIsNone(rec["value"])
            # The other branch's filter also carries `header row`; this phrase
            # is this branch's alone. The refusal below rules that branch out.
            self.assertIn("carries no roster header row", rec["filter"])
            self.assertNotIn("is absent from the repository root", rec["filter"])
            # Positive control: adding the header row makes the same reader
            # compute, so the refusal is the missing row and not a dead parser.
            (root / "CLAUDE.md").write_text(
                f"# CLAUDE.md\n\n{ROSTER_HEADER}\n|---|---|---|---|\n"
                "| a | b | c | d |\n", encoding="utf-8")
            self.assertEqual(self._gates(root)["value"], 1)

    def test_a_roster_with_no_enrolled_row_reports_zero_and_stays_computed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text(
                f"# CLAUDE.md\n\n{ROSTER_HEADER}\n|---|---|---|---|\n\n"
                "The roster is empty today.\n", encoding="utf-8")
            rec = self._gates(root)
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(rec["value"], 0)



# --------------------------------------------------------------------------
# fence awareness, mined-value redaction, and the version-control guards
# --------------------------------------------------------------------------

FENCE = "`" * 3

FENCED_BACKDATED_JOURNAL = f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

Friction: the first real one, dated after the adoption date.

The entry-heading grammar is written like this:

{FENCE}text
## [2026-01-01 09:00] work | a fenced example, dated before adoption
{FENCE}

Friction: the second real one, still inside the 2026-02-20 entry.
"""

FENCED_QUOTATION_JOURNAL = f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

The friction grammar is written like this:

{FENCE}text
Friction: a quotation of the grammar, which cites no friction of its own.
{FENCE}

Friction: the only real citation in this entry.
"""

FENCED_BACKDATED_LOG = f"""# log

## [2026-02-10] adr | the only entry in this file

This entry names ADR-0001 in its opening line.

{FENCE}text
## [2026-01-01] adr | a fenced example heading
{FENCE}

It also names ADR-0002 after the fence, still inside the same entry.
"""


def _unfenced(text: str) -> str:
    """The same document with the fence markers deleted, and nothing else."""
    return text.replace(FENCE + "text\n", "").replace(FENCE + "\n", "")


class FenceAwareEntryScanTests(unittest.TestCase):
    """A fenced example is content — never an entry heading, never a citation.

    Both scanners split on the dated entry heading and read `Friction:` lines
    with no fence tracking, so the count moved in both directions. A fenced
    back-dated heading opened a pre-adoption entry and reattributed the
    friction lines after it out of the count; a journal entry that merely
    quotes the grammar inside a fence added a citation nobody made. The second
    needs no attacker: the cycle that introduces the grammar is exactly the
    work whose journal entry quotes it.
    """

    def _friction(self, text: str) -> dict:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-fence-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        (docs / "journal" / "2026-02.md").write_text(text, encoding="utf-8")
        return sig.signal_friction_citations(root, docs, "bionic", "2026-02-14")

    def test_a_fenced_back_dated_heading_does_not_reattribute_later_lines(self):
        rec = self._friction(FENCED_BACKDATED_JOURNAL)
        self.assertEqual(rec["verdict"], "computed")
        # Both `Friction:` lines belong to the 2026-02-20 entry. Read as a
        # heading, the fenced 2026-01-01 line opens a pre-adoption entry and
        # the second line drops out, reading 1 — and the loss disguises itself
        # as the legitimate boundary truncation.
        self.assertEqual(rec["value"], 2)
        self.assertNotIn("truncated", rec["basis"])
        # Positive control: the same text with the fence markers deleted DOES
        # lose the line, so the fixture really exercises the hazard.
        self.assertEqual(self._friction(_unfenced(FENCED_BACKDATED_JOURNAL))["value"], 1)

    def test_a_fenced_quotation_of_the_grammar_is_not_counted_as_a_citation(self):
        rec = self._friction(FENCED_QUOTATION_JOURNAL)
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 1)
        # Positive control: unfenced, the same quotation IS counted, so the
        # exclusion above is the fence and not an unreachable line.
        self.assertEqual(self._friction(_unfenced(FENCED_QUOTATION_JOURNAL))["value"], 2)

    def test_the_dated_entry_split_is_fence_aware_too(self):
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-fence-log-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        docs.mkdir(parents=True)
        (docs / "log.md").write_text(FENCED_BACKDATED_LOG, encoding="utf-8")
        entries, refused = sig._dated_entries(root, docs)
        # Nothing was refused, so the entry list below is the whole surface.
        self.assertEqual(refused, [])
        # One entry, not two: the fenced heading is content.
        self.assertEqual([date for _label, date, _ids in entries], ["2026-02-10"])
        # Both ids belong to that one entry, so `dormancy_days` measures both
        # against 2026-02-10 rather than dating ADR-0002 to the fenced example.
        self.assertEqual(entries[0][2], {"ADR-0001", "ADR-0002"})


ESC = "\x1b"
#: A version string that is neither printable nor short, mined out of a
#: CHANGELOG heading this script does not author.
HOSTILE_VERSION = "1.0.0" + ESC + "[2J" + "9" * 300


def _hostile_changelog() -> str:
    return (f"# Changelog\n\n## [1.1.0] — 2026-01-11\n\n- b\n\n"
            f"## [{HOSTILE_VERSION}] — 2026-01-01\n\n- a\n")


class MinedVersionRedactionTests(unittest.TestCase):
    """The mined CHANGELOG version is routed through `redact` — MF-1.

    The heading grammar captures the version as an unbounded run of non-bracket
    characters. Unredacted it became a JSON object key in
    `release_cadence.value.prep_commits` and was interpolated into
    `schema_growth`'s `filter` and `baseline.ref`: a 20,000-character heading
    produced a 40,738-character `filter`, and a heading carrying ESC put that
    byte raw on the human table lane.
    """

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_a_hostile_version_reaches_the_prep_commits_key_bounded_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(_hostile_changelog(), encoding="utf-8")
            _commit(root, "seed")

            rec = sig.signal_release_cadence(root, "bionic")
            self.assertEqual(rec["verdict"], "computed")
            keys = list(rec["value"]["prep_commits"])
            self.assertEqual(len(keys), 2)
            self.assertNotIn(ESC, "".join(keys))
            self.assertTrue(any("unprintable" in k for k in keys), keys)
            self.assertTrue(any("truncated from 309 characters" in k for k in keys), keys)
            # The key is BOUNDED, and its bound is independent of the raw
            # value's length. The ceiling is DERIVED from the module's own
            # `untrusted.LIMIT` and `_PREP_KEY_DIGEST_CHARS` rather than
            # written down: it was written down as 240, which was both a
            # magic number and the wrong one, and it pinned the digest width
            # so that widening the digest failed here for the wrong reason.
            self.assertLessEqual(max(len(k) for k in keys),
                                 _prep_key_ceiling(309))
            # Positive control: a benign version round-trips to exactly its
            # `repr()` — the delimiting a human reader needs to see where the
            # key starts and ends — so the bound/redaction above is what
            # widened the key, not a general re-quoting of every key.
            (root / "CHANGELOG.md").write_text(TWO_RELEASE_CHANGELOG, encoding="utf-8")
            benign = sig.signal_release_cadence(root, "bionic")
            self.assertEqual(set(benign["value"]["prep_commits"]), {"'1.0.0'", "'1.1.0'"})

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_a_hostile_version_reaches_the_schema_growth_filter_bounded_and_redacted(self):
        # The hostile version is its OWN release, in its OWN commit — so its
        # mark resolves cleanly and its (redacted) name reaches
        # `baseline["release"]` and the `filter` sentence, rather than
        # tripping `baseline-ref-ambiguous` by sharing a mark with 1.1.0.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            SchemaGrowthTests._dev_repo(root)
            _schema_growth_release_commit(root, HOSTILE_VERSION, "2026-01-01")
            SchemaGrowthTests._seed(root, claude_lines=4, skills=2)
            _commit(root, "the baseline release, hostile version")
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")
            SchemaGrowthTests._seed(root, claude_lines=9, skills=5)
            _commit(root, "growth since the baseline")

            rec = sig.signal_schema_growth(root, root / "bionic", "bionic")
            self.assertEqual(rec["verdict"], "computed")
            self.assertNotIn(ESC, rec["filter"])
            self.assertIn("unprintable", rec["filter"])
            self.assertIn("truncated from 309 characters", rec["filter"])
            self.assertLess(len(rec["filter"]), 2000)
            # Positive control: a benign second-newest version is named in the
            # filter verbatim, so the bound above is the redaction firing and
            # not the version having been dropped from the sentence.
            with tempfile.TemporaryDirectory() as tmp2:
                benign_root = Path(tmp2)
                _init_repo(benign_root)
                SchemaGrowthTests._dev_repo(benign_root)
                _schema_growth_release_commit(benign_root, "1.0.0", "2026-01-01")
                SchemaGrowthTests._seed(benign_root, claude_lines=4, skills=2)
                _commit(benign_root, "the baseline release")
                _schema_growth_release_commit(benign_root, "1.1.0", "2026-01-11")
                SchemaGrowthTests._seed(benign_root, claude_lines=9, skills=5)
                _commit(benign_root, "growth since the baseline")
                benign = sig.signal_schema_growth(benign_root, benign_root / "bionic", "bionic")
                self.assertIn("'1.0.0'", benign["filter"])

    def test_the_release_cadence_filter_states_what_a_heading_yields(self):
        rec = sig.signal_release_cadence(TRIPS, "bionic")
        self.assertEqual(rec["verdict"], "computed")
        # The claim the filter makes must be the TRUE one: the heading grammar
        # captures ANY run of non-bracket characters without checking that it
        # looks like a version, so a prose-shaped bracketed run is mined
        # exactly as a real version would be. A discriminating clause, not a
        # word ("mined") that recurs elsewhere in the same sentence.
        self.assertIn(
            "the heading grammar does not check that the captured text looks "
            "like a version, so a prose-shaped bracketed run is mined exactly "
            "as a real version would be, and nothing else in the heading or "
            "file is mined",
            rec["filter"])
        self.assertIn("redaction bound", rec["filter"])
        # NEGATIVE — the actual regression pin for A5: the OLD, FALSE claim
        # ("no prose is mined") must be absent. `CHANGELOG_HEADING` captures
        # `[^\]]+`, so it mines any bracketed run — prose included — and the
        # filter must never again claim otherwise.
        self.assertNotIn("no prose is mined", rec["filter"])


class BlobDecodeTests(unittest.TestCase):
    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_an_invalid_utf8_byte_in_a_read_blob_does_not_collapse_the_envelope(self):
        """`text=True` decodes strictly, and `UnicodeDecodeError` is a ValueError.

        The subprocess reader caught `OSError` alone, so the decode error
        escaped to `main`'s blanket handler and all eight signals collapsed
        into exit 2. The file lane already read with `errors="replace"`, so the
        asymmetry was unintended.
        """
        with tempfile.TemporaryDirectory() as tmp:
            # `quiet/` copied, so the envelope is the whole eight-record one
            # rather than a bare root that would report input errors of its own.
            root = Path(tmp) / "root"
            shutil.copytree(QUIET, root)
            _init_repo(root)
            (root / "bionic" / "CLAUDE.md").write_bytes(b"schema\n\xff\nmore\n")
            _commit(root, "a tree whose CLAUDE.md carries one invalid byte")

            proc = _run("--repo-root", str(root), "--today", TODAY.isoformat(), "--json")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(len(payload["signals"]), 8)
            assert_envelope_contract(self, payload)
            growth = next(r for r in payload["signals"] if r["signal"] == "schema_growth")
            # The content discriminator: the blob was read, with the byte
            # replaced rather than raised on.
            self.assertEqual(growth["verdict"], "computed")
            self.assertEqual(growth["value"]["current"]["claude_md_lines"], 3)


class SubstrateGuardTests(unittest.TestCase):
    """Direct cover for the four guards on repo-supplied input.

    Each was independently deletable with the module green: the argument
    grammar forced to admit everything, the environment allowlist replaced
    with the inherited environment, the containment check forced false, and
    the end-of-options separator removed from the session probe.
    """

    def test_the_argument_grammar_admits_a_qualified_ref_and_refuses_nine_shapes(self):
        for admitted in ("refs/tags/1.0.0", "HEAD", "bionic/CLAUDE.md",
                         "crux/catalog/skills.json"):
            with self.subTest(admitted=admitted):
                self.assertTrue(sig._valid_git_arg(admitted))
        # THE LEADING-HYPHEN REFUSAL IS ITS OWN CLASS, and the refused list
        # did not cover it. `--upload-pack=x` was the only hyphen-leading
        # shape here, and it also carries an `=`, which the character class
        # refuses on its own — so widening the grammar to admit a leading
        # hyphen left the suite green. `--all`, `-n` and `-` are drawn
        # entirely from the admitted character set and fail on the OPENING
        # character alone, which is the guard the docstring claims: no
        # repo-supplied value can be read by git as an option.
        for refused in ("--upload-pack=x", "--all", "-n", "-",
                        "a..b", "a b", "", "x" * 257):
            with self.subTest(refused=refused):
                self.assertFalse(sig._valid_git_arg(refused))
        # PAIRED POSITIVE CONTROL: a hyphen is admitted everywhere EXCEPT
        # first, so the three rows above turn on their opening character and
        # not on the hyphen being refused outright.
        for admitted in ("a-b", "refs/tags/v1.0.0-rc1", "n-"):
            with self.subTest(admitted=admitted):
                self.assertTrue(sig._valid_git_arg(admitted))

    def test_the_environment_is_the_named_allowlist_and_inherits_no_redirect(self):
        expected = {"LC_ALL", "GIT_CONFIG_NOSYSTEM", "PATH"}
        if sys.platform == "win32":
            expected.add("SYSTEMROOT")
        # POSITIVE CONTROL: every name the binary honours that this suite
        # enumerates is planted in the ambient environment for the duration of
        # the call, so an inherited environment cannot pass this on an
        # already-clean machine. The roster includes the three the docstring's
        # enumeration had omitted — `GIT_CONFIG_PARAMETERS`, which outranks
        # every configuration file, `GIT_COMMON_DIR` and
        # `GIT_ALTERNATE_OBJECT_DIRECTORIES`, which relocate the object store.
        planted = {"HOME": "/tmp/adr-signals-planted-home",
                   "GIT_CONFIG_GLOBAL": "/tmp/adr-signals-planted-config"}
        for name in REPO_REDIRECT_VARS:
            planted[name] = "/tmp/adr-signals-planted.git"
        saved = {name: os.environ.get(name) for name in planted}
        os.environ.update(planted)
        try:
            env = sig._git_environment()
        finally:
            for name, old in saved.items():
                if old is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = old
        self.assertEqual(set(env), expected)
        for name in planted:
            self.assertNotIn(name, env)
        self.assertEqual(env["LC_ALL"], "C")
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        # The allowlist's real property, stronger than any enumeration: the
        # one `GIT_`-named member is SUPPLIED, and no other `GIT_`-prefixed
        # name is present whether this suite thought to name it or not.
        self.assertEqual([n for n in env if n.startswith("GIT_")],
                         ["GIT_CONFIG_NOSYSTEM"])

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_a_plain_subdirectory_of_a_work_tree_is_refused_as_uncontained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            SchemaGrowthTests._seed(root, claude_lines=9, skills=5)
            _commit(root, "the enclosing repository")
            inner = root / "inner"
            inner.mkdir()
            SchemaGrowthTests._seed(inner, claude_lines=3, skills=1)

            rec = sig.signal_schema_growth(inner, inner / "bionic", "bionic")
            self.assertEqual(rec["verdict"], "unmeasurable")
            self.assertIsNone(rec["value"])
            self.assertIn("the work tree git resolves is not the given repository root",
                          rec["basis"])
            # PAIRED POSITIVE CONTROL: the same reader over the repository root
            # itself computes, so the refusal is containment and not the fixture.
            control = sig.signal_schema_growth(root, root / "bionic", "bionic")
            self.assertEqual(control["verdict"], "computed")
            self.assertEqual(control["value"]["current"]["claude_md_lines"], 9)

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_every_repo_supplied_value_is_passed_after_end_of_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            SchemaGrowthTests._seed(root, claude_lines=4, skills=2)
            _commit(root, "one commit")
            _tag(root, "1.0.0")

            calls: list[tuple[str, ...]] = []
            real = sig._git

            def recorder(where, *args):
                calls.append(args)
                return real(where, *args)

            sig._git = recorder
            try:
                legs = sig._GitLegs(root)
                self.assertTrue(legs.usable, legs.reason)
                self.assertIsNotNone(legs.blob("HEAD", "bionic/CLAUDE.md"))
                self.assertIsNotNone(legs.tag_commit("1.0.0"))
            finally:
                sig._git = real

            probe = [a for a in calls if a[0] == "rev-list" and a[-1] == "HEAD"]
            self.assertEqual(len(probe), 1, calls)
            self.assertIn("--end-of-options", probe[0])
            for args in calls:
                if args[0] in {"show", "rev-list"}:
                    with self.subTest(args=args):
                        self.assertIn("--end-of-options", args)
                        # The pathspec separator is never substituted for it: a
                        # ref placed after that separator reads as a path.
                        self.assertNotIn("--", args)

class RootFileContainmentTests(unittest.TestCase):
    """A root-level read follows no symlink out of the declared read surface.

    `release_cadence` reads the repository root's CHANGELOG.md and
    `gate_count` its CLAUDE.md; both computed from files outside that root
    when the root-level name was a symlink. The refusal is `unmeasurable` with
    the reason in `filter` — never an `errors` entry, and never exit 2.
    """

    def _pair(self, name: str, content: str) -> tuple[Path, Path]:
        outer = tempfile.TemporaryDirectory(prefix="adr-signals-outside-")
        self.addCleanup(outer.cleanup)
        inner = tempfile.TemporaryDirectory(prefix="adr-signals-root-")
        self.addCleanup(inner.cleanup)
        outside = Path(outer.name) / name
        outside.write_text(content, encoding="utf-8")
        root = Path(inner.name)
        (root / name).symlink_to(outside)
        return root, outside

    def test_a_symlinked_changelog_is_refused_rather_than_read(self):
        root, outside = self._pair("CHANGELOG.md", THREE_RELEASE_CHANGELOG)
        rec = sig.signal_release_cadence(root, "bionic")
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        self.assertIn("resolves outside", rec["filter"])
        # PAIRED POSITIVE CONTROL: the same content in place IS read, so the
        # refusal is containment and not the corpus.
        (root / "CHANGELOG.md").unlink()
        shutil.copyfile(outside, root / "CHANGELOG.md")
        control = sig.signal_release_cadence(root, "bionic")
        self.assertEqual(control["verdict"], "computed")
        self.assertEqual(control["value"]["intervals_days"], [10, 15])

    def test_a_symlinked_repo_root_claude_md_is_refused_rather_than_read(self):
        roster = (f"# CLAUDE.md\n\n{ROSTER_HEADER}\n|---|---|---|---|\n"
                  "| a | b | c | d |\n")
        root, outside = self._pair("CLAUDE.md", roster)
        rec = sig.signal_gate_count(root, "bionic")
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        self.assertIn("resolves outside", rec["filter"])
        # PAIRED POSITIVE CONTROL: the same roster in place counts its one row.
        (root / "CLAUDE.md").unlink()
        shutil.copyfile(outside, root / "CLAUDE.md")
        self.assertEqual(sig.signal_gate_count(root, "bionic")["value"], 1)

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_the_schema_growth_baseline_read_is_contained_too(self):
        """`schema_growth`'s OWN read of CHANGELOG.md — for baseline discovery
        — is contained too, a SECOND call site over the same root-level file
        `release_cadence` reads for its interval calculation.

        Drives the real signal, matching the idiom of the two sibling tests
        above: `test_the_schema_growth_baseline_read_is_contained_too`
        formerly drove a private boolean containment helper directly (since
        deleted — `_read_contained` took over all thirteen call sites and the
        predicate had no caller left), so deleting
        the containment branch FROM THE SIGNAL left the suite `OK` while the
        signal itself read a baseline from outside the root.
        """
        with tempfile.TemporaryDirectory() as outer, tempfile.TemporaryDirectory() as inner:
            outside = Path(outer) / "CHANGELOG.md"
            outside.write_text(THREE_RELEASE_CHANGELOG, encoding="utf-8")
            root = Path(inner)
            _init_repo(root)
            SchemaGrowthTests._dev_repo(root)
            (root / "CHANGELOG.md").symlink_to(outside)
            SchemaGrowthTests._seed(root, claude_lines=9, skills=5)
            _commit(root, "one commit, CHANGELOG.md symlinked outside the root")

            rec = sig.signal_schema_growth(root, root / "bionic", "bionic")
            self.assertEqual(rec["verdict"], "computed")
            self.assertIsNone(rec["value"]["baseline"]["ref"])
            self.assertIn({"condition": "no-release-record"}, rec["value"]["conditions"])
            self.assertIn("resolves outside that root", rec["filter"])
            # The HEAD leg itself is unaffected: it reads bionic/CLAUDE.md and
            # the skills catalog at HEAD, never the symlinked CHANGELOG.
            self.assertEqual(rec["value"]["current"]["claude_md_lines"], 9)

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_the_same_changelog_content_in_place_does_resolve_a_baseline(self):
        # PAIRED POSITIVE CONTROL for the refusal above, built independently:
        # in-place CHANGELOG.md content, one release per commit, DOES report a
        # baseline mark, so the null above is the symlink refusal and not a
        # fixture that never carries two dated headings or a resolvable mark.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            SchemaGrowthTests._dev_repo(root)
            _schema_growth_release_commit(root, "1.0.0", "2026-01-01")
            SchemaGrowthTests._seed(root, claude_lines=4, skills=2)
            _commit(root, "the baseline release")
            _schema_growth_release_commit(root, "1.1.0", "2026-01-11")
            SchemaGrowthTests._seed(root, claude_lines=9, skills=5)
            _commit(root, "growth since the baseline")

            control = sig.signal_schema_growth(root, root / "bionic", "bionic")
            self.assertEqual(control["verdict"], "computed")
            self.assertIsNotNone(control["value"]["baseline"]["ref"])
            self.assertEqual(control["value"]["baseline"]["release"], "'1.0.0'")


# --------------------------------------------------------------------------
# A1 — the single-descriptor O_NOFOLLOW read closes a check-then-read race
# --------------------------------------------------------------------------

class ContainedReadRaceTests(unittest.TestCase):
    """`_read_contained` resolves the whole name once, then opens the
    RESOLVED name once with `O_NOFOLLOW` through that one descriptor.

    A naive check-then-read pair resolves a name, confirms containment, and
    then re-opens the ORIGINAL name — reading whatever it points to by the
    time of that SECOND lookup. This deterministically simulates that window
    by swapping the leaf to an outside symlink as a side effect of the first
    `Path.resolve()` call `_read_contained` itself makes, standing in for the
    race finding A1 describes probabilistically (4,000 raced pairs, 411
    attacker reads).
    """

    def test_a_leaf_swapped_to_an_outside_symlink_after_resolve_is_refused(self):
        with tempfile.TemporaryDirectory() as root_dir, \
                tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            target = root / "ADR-9000-race.md"
            target.write_text("safe content", encoding="utf-8")
            outside = Path(outside_dir) / "secret.md"
            outside.write_text("attacker content", encoding="utf-8")

            real_resolve = Path.resolve
            swapped = {"done": False}

            def resolve_and_swap(self_path, strict=False):
                result = real_resolve(self_path, strict=strict)
                if not swapped["done"] and self_path == target:
                    swapped["done"] = True
                    target.unlink()
                    target.symlink_to(outside)
                return result

            with unittest.mock.patch.object(Path, "resolve", resolve_and_swap):
                text = sig._read_contained(root, target)
            self.assertIsNone(text)
            self.assertTrue(swapped["done"], "the fixture never triggered the swap")

            # PAIRED POSITIVE CONTROL: the identical target, restored to a
            # plain in-root file with no swap in flight, reads its own
            # content — so the None above is the race refusal firing and not
            # `_read_contained` refusing every read it is given.
            target.unlink()
            target.write_text("safe content", encoding="utf-8")
            self.assertEqual(sig._read_contained(root, target), "safe content")


# --------------------------------------------------------------------------
# A3 — `_fence_marker` tracks the fence CHARACTER and RUN LENGTH, not just ```
# --------------------------------------------------------------------------

TILDE = "~" * 3
FOUR_BACKTICK = "`" * 4

TILDE_BACKDATED_JOURNAL = f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

Friction: the first real one, dated after the adoption date.

The entry-heading grammar is written like this:

{TILDE}text
## [2026-01-01 09:00] work | a fenced example, dated before adoption
{TILDE}

Friction: the second real one, still inside the 2026-02-20 entry.
"""

TILDE_QUOTATION_JOURNAL = f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

The friction grammar is written like this:

{TILDE}text
Friction: a quotation of the grammar, which cites no friction of its own.
{TILDE}

Friction: the only real citation in this entry.
"""

FOUR_BACKTICK_WRAPPING_THREE_JOURNAL = f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

Friction: the first real one, dated after the adoption date.

A fence inside a fence, escaped the CommonMark way:

{FOUR_BACKTICK}text
{FENCE}text
## [2026-01-01 09:00] work | a fenced example wrapped twice
{FENCE}
{FOUR_BACKTICK}

Friction: the second real one, still inside the 2026-02-20 entry.
"""


class FenceCharacterAndRunLengthTests(unittest.TestCase):
    """Fence tracking by CHARACTER and RUN LENGTH, not a bare ``` prefix test.

    `_fence_marker` recognizes a `~~~` fence and requires a closing run at
    LEAST as long as the opener's, so four backticks wrapping three-backtick
    content stays fenced through the inner run. A scanner blind to either
    property misreads a back-dated heading inside such a block as real, and a
    `Friction:` line inside one as a genuine citation.
    """

    def _friction(self, text: str) -> dict:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-fence-char-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        (docs / "journal" / "2026-02.md").write_text(text, encoding="utf-8")
        return sig.signal_friction_citations(root, docs, "bionic", "2026-02-14")

    def test_a_tilde_fenced_back_dated_heading_does_not_reattribute_later_lines(self):
        rec = self._friction(TILDE_BACKDATED_JOURNAL)
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 2)
        # Positive control: the same text with the tilde fence markers
        # deleted DOES lose the second line, so the fixture really exercises
        # the hazard and the 2 above is the fence tracking, not a no-op.
        unfenced = TILDE_BACKDATED_JOURNAL.replace(TILDE + "text\n", "").replace(TILDE + "\n", "")
        self.assertEqual(self._friction(unfenced)["value"], 1)

    def test_a_tilde_fenced_quotation_is_not_counted_as_a_citation(self):
        rec = self._friction(TILDE_QUOTATION_JOURNAL)
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 1)
        # Positive control: unfenced, the same quotation IS counted, so the
        # exclusion above is the fence and not an unreachable line.
        unfenced = TILDE_QUOTATION_JOURNAL.replace(TILDE + "text\n", "").replace(TILDE + "\n", "")
        self.assertEqual(self._friction(unfenced)["value"], 2)

    def test_four_backticks_wrapping_three_backtick_content_stays_fenced(self):
        rec = self._friction(FOUR_BACKTICK_WRAPPING_THREE_JOURNAL)
        self.assertEqual(rec["verdict"], "computed")
        # Both `Friction:` lines belong to the 2026-02-20 entry; the doubly
        # fenced back-dated heading never opens a pre-adoption entry.
        self.assertEqual(rec["value"], 2)
        # Positive control: with every fence marker deleted, the inner
        # back-dated heading DOES reattribute the second line, dropping it.
        unfenced = (FOUR_BACKTICK_WRAPPING_THREE_JOURNAL
                    .replace(FOUR_BACKTICK + "text\n", "")
                    .replace(FOUR_BACKTICK + "\n", "")
                    .replace(FENCE + "text\n", "")
                    .replace(FENCE + "\n", ""))
        self.assertEqual(self._friction(unfenced)["value"], 1)


# --------------------------------------------------------------------------
# A4 — `_git` splits stdout on `"\n"` alone, never `str.splitlines()`
# --------------------------------------------------------------------------

class GitOutputSplittingTests(unittest.TestCase):
    """A commit subject carrying U+2028 is one line of git's `\\n`-joined
    output, never two — `str.splitlines()` also breaks on it."""

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_u2028_commit_subject_yields_one_subject_not_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            subject = "notes more notes"
            _commit(root, subject)
            lines = sig._git(root, "log", "--format=%s", "HEAD")
            self.assertEqual(lines, [subject])
            # Positive control: a second, ordinary commit really does add a
            # second element, so the one line above is the U+2028 subject and
            # not a reader that always returns a single line.
            _commit(root, "a second, unrelated commit")
            self.assertEqual(len(sig._git(root, "log", "--format=%s", "HEAD")), 2)

    @unittest.skipUnless(GIT, "git is not on PATH")
    def test_a_u2028_break_inside_a_non_prep_subject_forges_no_prep_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            _commit(root, "work a")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0, encoding="utf-8")
            _commit(root, "Release prep v1.0.0")
            _commit(root, "work b")
            _commit(root, "work c")
            (root / "CHANGELOG.md").write_text(CHANGELOG_WITH_1_0_0_AND_1_1_0,
                                               encoding="utf-8")
            _commit(root, "Release prep v1.1.0")
            # A forged subject: one commit whose subject carries a U+2028
            # break, so `str.splitlines()` would misread it as TWO lines —
            # "notes" and "Release prep v1.2.0" — with the second matching
            # the declared prefix. `_git` splits on `"\n"` alone, so this is
            # ONE subject, "notes Release prep v1.2.0", which does not
            # itself start with the prefix. It sits inside 1.2.0's own
            # interval below.
            _commit(root, "notes Release prep v1.2.0")
            (root / "CHANGELOG.md").write_text(THREE_RELEASE_CHANGELOG, encoding="utf-8")
            _commit(root, "work e")

            rec = sig.signal_release_cadence(root, "bionic")
            self.assertEqual(rec["verdict"], "computed")
            # 1.2.0's mark is "work e" (the commit that introduces its
            # heading), and its interval is {"work e", the forged commit}.
            # Neither subject genuinely starts with the declared prefix, so
            # the forged fragment counts nothing — 0, never a guess.
            self.assertEqual(rec["value"]["prep_commits"]["'1.2.0'"], 0)
            # Positive control: 1.1.0's interval genuinely contains a
            # "Release prep v1.1.0" commit, so the 0 above is the forged-line
            # refusal and not a reader that matches nothing.
            self.assertEqual(rec["value"]["prep_commits"]["'1.1.0'"], 1)
            # 1.0.0 is the oldest release and has no previous release, so its
            # interval is unbounded regardless of any subject text.
            self.assertIsNone(rec["value"]["prep_commits"]["'1.0.0'"])
            self.assertIn("3 of 3 dated headings resolve", rec["filter"])


# --------------------------------------------------------------------------
# A7 — `gate_count` refuses an ambiguous roster rather than guessing at one
# --------------------------------------------------------------------------

class GateCountDecoyHeaderTests(unittest.TestCase):
    def test_a_decoy_header_row_placed_first_does_not_win(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text(
                f"# CLAUDE.md\n\n{ROSTER_HEADER}\n|---|---|---|---|\n"
                "| decoy | decoy | decoy | decoy |\n\n"
                "## Two regenerative outputs\n\n"
                f"{ROSTER_HEADER}\n|---|---|---|---|\n"
                "| a | b | c | d |\n| e | f | g | h |\n",
                encoding="utf-8")
            rec = sig.signal_gate_count(root, "bionic")
            self.assertEqual(rec["verdict"], "unmeasurable")
            self.assertIsNone(rec["value"])
            self.assertIn("2 lines matching the roster header row", rec["filter"])

    def test_a_single_genuine_header_row_still_computes_the_right_row_count(self):
        # PAIRED POSITIVE CONTROL: the SAME fixture with the decoy row deleted
        # computes over the one remaining header row, so the refusal above is
        # the ambiguity and not a reader that never counts a roster.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text(
                "# CLAUDE.md\n\n## Two regenerative outputs\n\n"
                f"{ROSTER_HEADER}\n|---|---|---|---|\n"
                "| a | b | c | d |\n| e | f | g | h |\n",
                encoding="utf-8")
            rec = sig.signal_gate_count(root, "bionic")
            self.assertEqual(rec["verdict"], "computed")
            self.assertEqual(rec["value"], 2)


# --------------------------------------------------------------------------
# B1 — `env=_git_environment()` rides every real `subprocess.run` call `_git`
# makes; deletable with the whole suite green otherwise
# --------------------------------------------------------------------------

class GitEnvironmentIsAlwaysPassedTests(unittest.TestCase):
    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_every_git_invocation_passes_the_named_allowlist_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(TWO_RELEASE_CHANGELOG, encoding="utf-8")
            SchemaGrowthTests._seed(root, claude_lines=4, skills=2)
            _commit(root, "one commit")
            _tag(root, "1.0.0")

            expected = sig._git_environment()
            calls: list[dict | None] = []
            real_run = sig.subprocess.run

            def spy(*args, **kwargs):
                calls.append(kwargs.get("env"))
                return real_run(*args, **kwargs)

            with unittest.mock.patch.object(sig.subprocess, "run", spy):
                legs = sig._GitLegs(root)
                self.assertTrue(legs.usable, legs.reason)
                legs.lines("log", "--first-parent", "--format=%s", "HEAD")
                legs.tag_commit("1.0.0")

            # Positive control built into the assertion itself: at least the
            # `--show-toplevel` probe, the `--end-of-options` probe, the log
            # leg and the tag leg all ran, so this is not an empty loop.
            self.assertGreaterEqual(len(calls), 4, calls)
            for env in calls:
                self.assertEqual(env, expected)
                self.assertNotIn("GIT_DIR", env)




# --------------------------------------------------------------------------
# A1 — `_fence_marker` bounds the indent at 0-3 columns, opener AND closer
# --------------------------------------------------------------------------

def _indented_early_close(indent: str) -> str:
    """A genuine fence carrying a fence-shaped run at `indent`.

    At four spaces CommonMark reads that run as indented code, so the fence
    stays open across both quoted `Friction:` lines. At column 0 the same run
    really is the closer and both quoted lines become citations.
    """
    return f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

Friction: the real one, outside every fence.

A sample that carries a fence-shaped run of its own:

{FENCE}text
{indent}{FENCE}
Friction: quoted A, inside the fence.
Friction: quoted B, inside the fence.
{FENCE}

Friction: the real second one, after the fence closes.
"""


def _indented_phantom_open(indent: str) -> str:
    """A lone fence-shaped run at `indent`, ahead of a genuine fenced block.

    At four spaces it opens nothing. At column 0 it opens a fence that the
    later ```text run cannot close — its info string is non-empty — so the
    remainder of the file is fenced and both citations vanish.
    """
    return f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

An indented sample line:

{indent}{FENCE}

Friction: the first real one.

{FENCE}text
a quoted line inside a genuine fence
{FENCE}

Friction: the second real one.
"""


class FenceIndentBoundTests(unittest.TestCase):
    """CommonMark bounds a fence marker at 0-3 leading columns; 4+ is code.

    `_fence_marker` stripped unlimited leading whitespace, which was
    exploitable in two directions. A four-space-indented run CLOSED a fence
    the reader still sees as open (early close). At top level the same run
    OPENED a phantom fence, and the next real run then closed the phantom
    while opening the reader's — inverting every fence state for the rest of
    the file, which moved `friction_citations` on a real journal.
    """

    def _friction(self, text: str) -> dict:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-fence-indent-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        (docs / "journal" / "2026-02.md").write_text(text, encoding="utf-8")
        return sig.signal_friction_citations(root, docs, "bionic", "2026-02-14")

    def test_a_four_space_indented_run_does_not_close_an_open_fence(self):
        rec = self._friction(_indented_early_close("    "))
        self.assertEqual(rec["verdict"], "computed")
        # The two real citations only. Quoted A and quoted B stay inside the
        # fence, because the four-space run is indented code and not a closer.
        self.assertEqual(rec["value"], 2)
        # PAIRED POSITIVE CONTROL: the SAME run at column 0 really is the
        # closer, and both quoted lines are then counted — so the 2 above is
        # the indent bound firing and not two unreachable lines.
        self.assertEqual(self._friction(_indented_early_close(""))["value"], 3)

    def test_a_four_space_indented_run_does_not_open_a_phantom_fence(self):
        rec = self._friction(_indented_phantom_open("    "))
        self.assertEqual(rec["verdict"], "computed")
        # Both citations are unfenced: nothing opens before the ```text run,
        # which the run two lines below closes.
        self.assertEqual(rec["value"], 2)
        # PAIRED POSITIVE CONTROL: the SAME run at column 0 DOES open a fence.
        # The later ```text run cannot close it — its info string is non-empty
        # — so the FIRST citation goes fenced and only the second survives. So
        # the 2 above is the indent bound and not a fixture whose citations
        # were never countable.
        self.assertEqual(self._friction(_indented_phantom_open(""))["value"], 1)

    def test_the_indent_bound_is_three_columns_and_a_tab_counts_as_four(self):
        # Admitted: 0 to 3 leading spaces.
        for indent in ("", " ", "  ", "   "):
            with self.subTest(indent=len(indent)):
                self.assertIsNotNone(sig._fence_marker(indent + FENCE))
        # Refused: 4 or more columns, and a tab is four columns on its own.
        for indent in ("    ", "     ", "\t", " \t", "\t\t"):
            with self.subTest(indent=repr(indent)):
                self.assertIsNone(sig._fence_marker(indent + FENCE))


# --------------------------------------------------------------------------
# A2 — `_fenced_entries` splits on "\n" alone, never `str.splitlines()`
# --------------------------------------------------------------------------

U2028 = "\u2028"


def _line_separator_journal(sep: str) -> str:
    return f"""# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

Friction: the only real citation in this entry.

A sentence about the grammar.{sep}Friction: a citation nobody wrote.
"""


class FencedEntrySplittingTests(unittest.TestCase):
    """The file lane splits on `"\\n"` alone, as `_git` does on git's stdout.

    `str.splitlines()` also breaks on U+2028, U+2029, U+0085, U+000B, U+000C
    and U+001C-U+001E, so a journal sentence carrying U+2028 forged a
    `Friction:` line that CommonMark renders as mid-sentence prose. The file
    lane differs from the git lane in one respect — a CRLF document is in
    scope — so one trailing `\\r` per line is stripped in `splitlines()`'
    place.
    """

    def _friction(self, text: str) -> dict:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-split-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        (docs / "journal" / "2026-02.md").write_text(text, encoding="utf-8")
        return sig.signal_friction_citations(root, docs, "bionic", "2026-02-14")

    def test_a_u2028_break_in_a_journal_sentence_forges_no_friction_line(self):
        rec = self._friction(_line_separator_journal(U2028))
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 1)
        # PAIRED POSITIVE CONTROL: the same text with a REAL newline in that
        # one position IS counted, so the forged line really is `Friction:`-
        # shaped and the 1 above is the split discipline, not a dead branch.
        self.assertEqual(self._friction(_line_separator_journal("\n"))["value"], 2)

    def test_a_crlf_document_yields_lines_carrying_no_carriage_return(self):
        entries = sig._fenced_entries(
            "## [2026-02-20 10:00] work | e\r\nbody line\r\n")
        self.assertEqual(entries[0][0], "## [2026-02-20 10:00] work | e")
        # The body is one line. It used to be `["body line", ""]`: the split
        # was written out inside `_fenced_entries` and kept the empty element
        # a bare `split` leaves after a final newline. `_lines` drops it, which
        # is what `str.splitlines()` does and what makes the helper a drop-in.
        # The empty element matched no grammar, so nothing counted changed.
        self.assertEqual([line for line, _fenced in entries[0][1]], ["body line"])
        # The property this test is NAMED for, asserted rather than implied:
        # no line carries a carriage return.
        for line, _fenced in entries[0][1]:
            self.assertNotIn("\r", line)
        self.assertNotIn("\r", entries[0][0])

    def test_exactly_one_trailing_carriage_return_is_stripped_per_line(self):
        """The paired control for the strip: it removes ONE, not all.

        Without it, `_lines` could strip every trailing `\r` — or none, if the
        document happened to carry no CRLF — and the test above would not
        tell the difference.
        """
        entries = sig._fenced_entries(
            "## [2026-02-20 10:00] work | e\nkept\r\r\nbare\r\n")
        self.assertEqual([line for line, _fenced in entries[0][1]],
                         ["kept\r", "bare"])


# --------------------------------------------------------------------------
# A3 — the mined version is rendered at each CONSUMER, so two headings that
# `redact(quoted=False)` collapsed onto one string key two different slots
# --------------------------------------------------------------------------

#: A heading carrying one control character.
HOSTILE_ESC_VERSION = "esc\x1b[31m"
#: A heading that SPELLS the note `redact` appends to the value above. Under a
#: `redact(..., quoted=False)` at entry the two became byte-identical, and
#: `repr()` at the key site could not separate them, so one release's
#: `prep_commits` count silently overwrote the other's.
FORGER_VERSION = "esc\ufffd[31m [1 unprintable character redacted]"


class ReleasePrepKeyCollisionTests(unittest.TestCase):
    """Two versions `redact(..., quoted=False)` collapsed onto one string key
    two different `prep_commits` slots.

    The collision is created at the ENTRY point, not at the key: both values
    left `_dated_release_headings` as the SAME string, and no key-site
    transform can separate two equal strings — a second redaction is a no-op,
    because U+FFFD is printable. Moving the render to the consumer is what
    fixes it, and `redact(version, quoted=True)` is the primitive, because it
    applies `repr` to the redacted HEAD and appends the note OUTSIDE the
    quotes.

    The pair is driven through `_prep_key` directly rather than through a
    CHANGELOG: `FORGER_VERSION` ends in `]` and `CHANGELOG_HEADING` captures
    `[^\\]]+`, so this exact forger cannot be spelled as a heading.
    `signal_release_cadence` keys both `span_commits` and `prep_commits` by
    exactly `_prep_key(version)` for every version the changelog carries, so
    building that same mapping here is composed from the real stages rather
    than a stand-in. The end-to-end case below pins the KEY SHAPE — the note
    outside the quotes — on the real signal.
    """

    def test_the_heading_reader_returns_the_raw_capture(self):
        text = f"# Changelog\n\n## [{HOSTILE_ESC_VERSION}] — 2026-01-11\n\n- b\n"
        self.assertEqual(sig._dated_release_headings(text),
                         [(HOSTILE_ESC_VERSION, "2026-01-11")])
        # NEGATIVE: the redaction note is no longer pulled into the value at
        # entry. It is appended by whichever consumer renders it, outside the
        # quotes, which is what keeps two values distinct.
        self.assertNotIn("redacted", sig._dated_release_headings(text)[0][0])

    def test_a_forger_version_and_the_hostile_one_key_two_distinct_slots(self):
        # COMPOSED FROM THE REAL STAGES: the entry reader, then the key render.
        # Rendering at entry made this composition collapse — the hostile
        # heading left the reader spelling FORGER_VERSION exactly.
        captured = [v for v, _d in sig._dated_release_headings(
            f"# Changelog\n\n## [{HOSTILE_ESC_VERSION}] — 2026-01-11\n\n- b\n")]
        self.assertEqual(captured, [HOSTILE_ESC_VERSION])
        counts = {sig._prep_key(v): None for v in captured + [FORGER_VERSION]}
        # The discriminator: TWO versions, TWO keys. Under the render-at-entry
        # shape this mapping carried ONE, and one release's count silently
        # overwrote the other's.
        self.assertEqual(len(counts), 2, counts)
        hostile_key = next(k for k in counts if "redacted" in k)
        self.assertTrue(
            hostile_key.startswith("'esc\ufffd[31m' [1 unprintable character redacted]"),
            hostile_key)
        # The forger renders identically up to the note — that is what made
        # it a forger — and is separated by the digest the hostile key
        # carries and it does not.
        self.assertIn(repr(FORGER_VERSION), counts)
        self.assertNotEqual(hostile_key, repr(FORGER_VERSION))
        # PAIRED POSITIVE CONTROL: ordinary versions still key the mapping as
        # their own `repr()`, so the render above did not change what a
        # benign changelog produces.
        benign = {sig._prep_key(v) for v in ("1.0.0", "1.1.0")}
        self.assertEqual(benign, {"'1.0.0'", "'1.1.0'"})

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_the_note_lands_outside_the_quotes_on_the_real_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(_hostile_changelog(), encoding="utf-8")
            _commit(root, "seed")

            rec = sig.signal_release_cadence(root, "bionic")
            self.assertEqual(rec["verdict"], "computed")
            hostile_keys = [k for k in rec["value"]["prep_commits"] if "redacted" in k]
            self.assertEqual(len(hostile_keys), 1, rec["value"]["prep_commits"])
            key = hostile_keys[0]
            # The note sits OUTSIDE the closing quote. Rendered at entry it sat
            # INSIDE, which is what let a heading spelling the note key the
            # same slot.
            self.assertRegex(
                key,
                r"^'.*' \[[^\]]*redacted[^\]]*\] \[sha256:[0-9a-f]{%d}\]$"
                % sig._PREP_KEY_DIGEST_CHARS)
            self.assertFalse(key.endswith("redacted]'"), key)
            # PAIRED POSITIVE CONTROL: the benign key in the same mapping is a
            # bare `repr()` with no note at all, so the shape above is the
            # redaction firing rather than a suffix added to every key.
            benign = [k for k in rec["value"]["prep_commits"] if "redacted" not in k]
            self.assertEqual(benign, ["'1.1.0'"])


# --------------------------------------------------------------------------
# `re.escape`-around-a-mined-subject and the re.error containment lane —
# RETIRED under ADR-0109. `prep_commits` no longer matches a mined version
# string against a commit subject at all: the boundary comes from a
# CHANGELOG.md blob diff, and the interval count matches only the fixed,
# unescaped declared prefix. There is no mined content left to compile into
# a regex, so the hazard `SubjectMatchEscapeTests` and
# `SubjectMatchFailureIsAFindingTests` guarded against has no call site left
# to guard.
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# the `prep_commits` key is INJECTIVE, not merely bounded and rendered
# --------------------------------------------------------------------------

#: Two distinct versions of EQUAL total length sharing a 120-character prefix.
#: `redact` shows the first 120 characters and names the total, so both the
#: shown head and the `truncated from N characters` discriminator matched, and
#: the two keyed one slot.
_SHARED_PREFIX = "1.0.0" + "9" * 115
COLLIDING_A = _SHARED_PREFIX + "a" * 40
COLLIDING_B = _SHARED_PREFIX + "b" * 40


# The prep key's CEILING, derived rather than guessed. Every term comes from a
# constant the module under test owns, so widening the digest or moving
# `untrusted.LIMIT` moves this with them instead of turning a hand-written
# number into a lie.
#
#   2 * LIMIT + 2   the `repr` of the shown head. `repr` DOUBLES a backslash,
#                   and the version grammar admits backslashes, so a head of
#                   LIMIT backslashes renders at twice its length plus the two
#                   quotes. This is the term the old `< 240` assertion missed:
#                   120 backslashes alone key at 242.
#   + len(note)     ` [` + the redaction and truncation notes + `]`. The
#                   truncation note names the RAW length, so its digit count
#                   is a function of the input and is passed in.
#   + len(digest)   ` [sha256:` + the digest + `]`, and only on the lossy
#                   shape. Reads `_PREP_KEY_DIGEST_CHARS` rather than spelling
#                   a width, which is what made four tests fail closed when
#                   the width moved from 16 to 64 instead of silently passing.
def _prep_key_ceiling(raw_length: int, *, lossy: bool = True) -> int:
    limit = sig.LIMIT
    body = 2 * limit + 2
    note = (f" [{limit} unprintable characters redacted"
            f"; truncated from {raw_length} characters]")
    digest = f" [sha256:{'0' * sig._PREP_KEY_DIGEST_CHARS}]" if lossy else ""
    return body + len(note) + len(digest)


class PrepKeyInjectivityTests(unittest.TestCase):
    """Distinct versions never share a `prep_commits` slot.

    The key names a slot whose value is a COUNT, so a collision is not a
    rendering nuisance: one release's number silently overwrites another's.
    Keying on the full raw value would carry injectivity and would also put an
    unbounded, unredacted mined string into a JSON mapping key — the exact
    channel hazard the redaction exists to close. The key stays bounded and
    rendered, and gains a digest of the full raw value on the shapes where the
    rendering loses information.
    """

    def test_the_prefix_pair_renders_identically_before_the_digest(self):
        """The positive control on the FIXTURE: the two versions really do
        collapse under `redact` alone, so the test below measures a collision
        the pair can produce rather than one it never could."""
        self.assertNotEqual(COLLIDING_A, COLLIDING_B)
        self.assertEqual(len(COLLIDING_A), len(COLLIDING_B))
        self.assertEqual(sig.redact(COLLIDING_A, quoted=True),
                         sig.redact(COLLIDING_B, quoted=True))

    def test_two_colliding_versions_key_two_distinct_slots(self):
        # A dict comprehension keyed by `_prep_key`, exactly the shape
        # `signal_release_cadence` builds `span_commits`/`prep_commits`
        # with, over the two colliding-rendering versions.
        counts = {sig._prep_key(v): None for v in (COLLIDING_A, COLLIDING_B)}
        self.assertEqual(len(counts), 2, counts)
        self.assertEqual(sig._prep_key(COLLIDING_A), sig._prep_key(COLLIDING_A))
        self.assertNotEqual(sig._prep_key(COLLIDING_A), sig._prep_key(COLLIDING_B))

    @unittest.skipUnless(GIT, "the version-control binary is not on PATH")
    def test_each_slot_keeps_its_own_release_mark_interval(self):
        """The end-to-end sibling: two colliding-rendering versions as REAL
        consecutive releases, each with its own release mark and its own
        interval, driven through the real signal — the counting mechanism
        this file's collision property actually has to hold against now.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "CHANGELOG.md").write_text(CHANGELOG_SEED, encoding="utf-8")
            _commit(root, "seed")
            _commit(root, "work a")
            (root / "CHANGELOG.md").write_text(
                f"# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
                f"## [{COLLIDING_A}] — 2026-01-01\n\n- a\n",
                encoding="utf-8")
            _commit(root, "Release prep A")
            _commit(root, "work b")
            (root / "CHANGELOG.md").write_text(
                f"# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
                f"## [{COLLIDING_B}] — 2026-01-11\n\n### Added\n- b\n\n"
                f"## [{COLLIDING_A}] — 2026-01-01\n\n- a\n",
                encoding="utf-8")
            _commit(root, "work c")

            rec = sig.signal_release_cadence(root, "bionic")
            self.assertEqual(rec["verdict"], "computed")
            key_a, key_b = sig._prep_key(COLLIDING_A), sig._prep_key(COLLIDING_B)
            self.assertEqual(set(rec["value"]["prep_commits"]), {key_a, key_b})
            # A (oldest) has no previous release: null. B's interval is
            # {"work c", "work b"} — bounded, zero preparation declared.
            self.assertIsNone(rec["value"]["prep_commits"][key_a])
            self.assertEqual(rec["value"]["prep_commits"][key_b], 0)
            self.assertEqual(rec["value"]["span_commits"][key_b], 2)

    def test_the_key_stays_bounded_and_carries_no_unprintable_character(self):
        """The property the naive repair would have destroyed. The key is
        rendered and bounded whatever the raw value's length or bytes.

        THE BOUND IS DERIVED, NOT GUESSED. This asserted `< 240` while
        claiming the key is bounded "whatever the raw value's length or
        bytes", and 240 was simply the wrong number: `repr` doubles a
        backslash and the heading grammar admits backslashes, so 120
        backslashes alone key at 242 and the claim was false for an input the
        grammar accepts. The key IS bounded — `_prep_key_ceiling` says by how
        much — and the assertion now reads the same constants the key is
        built from.
        """
        hostile = "1.0.0\x1b[2J\r" + "9" * 5000
        key = sig._prep_key(hostile)
        self.assertLessEqual(len(key), _prep_key_ceiling(len(hostile)))
        self.assertNotIn("\x1b", key)
        self.assertNotIn("\r", key)
        self.assertIn("redacted", key)
        self.assertIn("truncated from 5010 characters", key)

    def test_a_backslash_run_keys_past_the_old_hand_written_bound(self):
        """The case that showed `< 240` was wrong.

        A version of exactly `untrusted.LIMIT` backslashes is short enough and
        printable enough to take the LOSSLESS shape, so it carries no note and
        no digest — and `repr` still doubles every character, which puts the
        key at `2 * LIMIT + 2`. Nothing here is hostile beyond being legal.
        """
        limit = sig.LIMIT
        version = "\\" * limit
        key = sig._prep_key(version)
        self.assertEqual(len(key), 2 * limit + 2)
        self.assertGreater(len(key), 240)          # the old assertion's number
        self.assertLessEqual(len(key), _prep_key_ceiling(len(version), lossy=False))
        # It is the LOSSLESS shape: `repr` exactly, so injectivity is `repr`'s.
        self.assertEqual(key, repr(version))

    def test_a_backslash_run_past_the_limit_takes_the_digest_and_stays_bounded(self):
        """The lossy sibling of the row above: the same character, long enough
        to truncate, so the key takes the digest and the widest term of the
        ceiling and the digest term are both live at once."""
        version = "\\" * (sig.LIMIT + 50)
        key = sig._prep_key(version)
        self.assertLessEqual(len(key), _prep_key_ceiling(len(version)))
        self.assertIn("truncated from", key)
        self.assertTrue(key.endswith("]"), key)

    def test_a_benign_version_keys_as_its_own_repr_with_no_digest(self):
        """PAIRED POSITIVE CONTROL: a version the rendering loses nothing
        from keys exactly as before — `repr` is injective on its own, so
        nothing is added and the common key stays the `'1.2.3'` a human
        reads."""
        for version in ("1.0.0", "v2", "", "0.9.2-rc1", "x" * 120):
            with self.subTest(version=version):
                self.assertEqual(sig._prep_key(version), repr(version))

    def test_the_lossless_and_lossy_key_shapes_cannot_collide(self):
        """The two shapes are disjoint by construction: `repr` always closes
        with its quote, and a digest-bearing key always closes with `]`."""
        self.assertTrue(sig._prep_key("1.0.0").endswith("'"))
        self.assertTrue(sig._prep_key("x" * 121).endswith("]"))
        # The width is READ from the module, never spelled here. Spelled, this
        # row and three others pinned 16 hexadecimal characters by hand, so
        # widening the digest against an offline collision search failed four
        # tests that were asserting the old width rather than the property.
        self.assertRegex(
            sig._prep_key("x" * 121),
            r"\[sha256:[0-9a-f]{%d}\]$" % sig._PREP_KEY_DIGEST_CHARS)

    def test_the_digest_is_the_whole_sha256_of_the_raw_value(self):
        """The digest is UNTRUNCATED, and that is the injectivity claim.

        At 16 hexadecimal characters the comment justified the width with the
        ACCIDENTAL bound — the odds of two honestly-written versions
        colliding. The versions are mined from a file this reader does not
        own, so the bound that matters is the work an attacker does offline:
        ~2**32 evaluations at 64 bits, about 22 minutes on one core in pure
        Python. Untruncated, the claim is exactly SHA-256's.
        """
        self.assertEqual(sig._PREP_KEY_DIGEST_CHARS,
                         len(hashlib.sha256(b"").hexdigest()))
        version = "x" * 121
        expected = hashlib.sha256(version.encode("utf-8")).hexdigest()
        self.assertTrue(sig._prep_key(version).endswith(f"[sha256:{expected}]"))

    def test_two_versions_that_render_alike_key_two_slots(self):
        """The property, driven through the counting half rather than asserted
        of the digest.

        The pair shares a `untrusted.LIMIT`-character head AND a total length,
        so `redact` renders them identically and the `truncated from N
        characters` discriminator matches too — the digest is the only thing
        left that can separate them. Measured at a reduced width with only the
        width changed, this pair keyed ONE slot and one release's count
        overwrote the other's.
        """
        head = ("1.0.0-" + "x" * 200)[: sig.LIMIT]
        a, b = head + "000000000001", head + "000000000002"
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), len(b))
        # POSITIVE CONTROL ON THE FIXTURE: they really do collapse under the
        # rendering alone, so the row below measures a collision this pair can
        # produce rather than one it never could.
        self.assertEqual(sig.redact(a, quoted=True), sig.redact(b, quoted=True))
        self.assertNotEqual(sig._prep_key(a), sig._prep_key(b))
        # Driven through the same dict-comprehension shape
        # `signal_release_cadence` builds `span_commits`/`prep_commits` with.
        counts = {sig._prep_key(v): None for v in (a, b)}
        self.assertEqual(len(counts), 2, counts)


# --------------------------------------------------------------------------
# A4 — `_dated_entries` excludes a FENCED ADR mention from the entry's id set
# --------------------------------------------------------------------------

FENCED_ADR_ID_LOG = f"""# log

## [2026-02-10] adr | the only entry in this file

This entry names ADR-0001 in its opening line, outside every fence.

{FENCE}text
A quoted example naming ADR-0777, which nobody decided anything about.
{FENCE}
"""


class DatedEntryFencedMentionTests(unittest.TestCase):
    """A fenced ADR id is a quoted example, never a dated mention.

    `_dated_entries` joins only the UNFENCED body lines before searching for
    ids. Deleting that filter fed `signal_dormancy_days` a mention nobody
    made, so a quoted example reset the dormancy clock — the exact harm the
    function's own docstring says it prevents. The pre-existing fence test
    over this scanner put BOTH ids outside the fence, so the filter was
    deletable with the module green.
    """

    def _entries(self, text: str):
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-fenced-id-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs = root / "bionic"
        docs.mkdir(parents=True)
        (docs / "log.md").write_text(text, encoding="utf-8")
        return sig._dated_entries(root, docs)

    def test_a_fenced_adr_id_is_absent_from_the_entry_id_set(self):
        entries, refused = self._entries(FENCED_ADR_ID_LOG)
        self.assertEqual(refused, [])
        self.assertEqual(len(entries), 1)
        ids = entries[0][2]
        # POSITIVE CONTROL, in the same fixture: the UNFENCED id IS present,
        # so the absence below is the fence filter and not an empty id set.
        self.assertIn("ADR-0001", ids)
        self.assertNotIn("ADR-0777", ids)
        # SECOND CONTROL: the same document with the fence markers deleted DOES
        # carry the second id, so the fixture really exercises the hazard.
        unfenced, _ = self._entries(_unfenced(FENCED_ADR_ID_LOG))
        self.assertEqual(unfenced[0][2], {"ADR-0001", "ADR-0777"})


# --------------------------------------------------------------------------
# A5 — `signal_gate_count`'s fence tracking is what a fenced decoy row hits
# --------------------------------------------------------------------------

def _decoy_roster_claude_md(fenced: bool) -> str:
    open_marker = f"{FENCE}text\n" if fenced else ""
    close_marker = f"{FENCE}\n" if fenced else ""
    return ("# CLAUDE.md\n\n"
            "An example of the roster shape, quoted:\n\n"
            f"{open_marker}"
            f"{ROSTER_HEADER}\n|---|---|---|---|\n"
            "| decoy | decoy | decoy | decoy |\n"
            f"{close_marker}"
            "\n## Two regenerative outputs\n\n"
            f"{ROSTER_HEADER}\n|---|---|---|---|\n"
            "| a | b | c | d |\n| e | f | g | h |\n")


def _decoy_roster_with_separator(sep: str) -> str:
    """The fenced-decoy fixture with `sep` inside the fenced block's FIRST
    content line, immediately before a fence-shaped run.

    With `sep` a real newline the run really is a closer: the decoy escapes
    the fence and the block's true closer opens a phantom one that swallows
    the real roster. With `sep` a U+2028 the whole thing is one content line
    that closes nothing — unless the reader split it with `str.splitlines()`.
    """
    return ("# CLAUDE.md\n\n"
            "An example of the roster shape, quoted:\n\n"
            f"{FENCE}text\n"
            f"a sample line{sep}{FENCE}\n"
            f"{ROSTER_HEADER}\n|---|---|---|---|\n"
            "| decoy | decoy | decoy | decoy |\n"
            f"{FENCE}\n"
            "\n## Two regenerative outputs\n\n"
            f"{ROSTER_HEADER}\n|---|---|---|---|\n"
            "| a | b | c | d |\n| e | f | g | h |\n")


class GateCountFencedDecoyTests(unittest.TestCase):
    """A decoy header row inside a fence is content, never a candidate match.

    The live repo-root CLAUDE.md carries a fenced block above its real roster,
    which is why the loop tracks fences at all — yet every one of those lines
    was uncovered: the pre-existing decoy test plants two UNFENCED rows, so it
    reaches the ambiguity refusal and never the fence tracking.
    """

    def test_a_fenced_decoy_row_leaves_one_candidate_and_the_roster_computes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text(_decoy_roster_claude_md(True),
                                            encoding="utf-8")
            rec = sig.signal_gate_count(root, "bionic")
            self.assertEqual(rec["verdict"], "computed")
            # The REAL roster's row count, not the decoy's one row.
            self.assertEqual(rec["value"], 2)

    def test_the_same_fixture_unfenced_is_refused_as_ambiguous(self):
        # PAIRED POSITIVE CONTROL for the test above: the SAME two header rows
        # with the fence markers deleted are two candidates and the signal
        # refuses — so the `computed` above is the fence tracking and not a
        # fixture that only ever carried one header row.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text(_decoy_roster_claude_md(False),
                                            encoding="utf-8")
            rec = sig.signal_gate_count(root, "bionic")
            self.assertEqual(rec["verdict"], "unmeasurable")
            self.assertIsNone(rec["value"])
            self.assertIn("2 lines matching the roster header row", rec["filter"])

    def _gate_count(self, text: str) -> dict:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-gate-split-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "CLAUDE.md").write_text(text, encoding="utf-8")
        return sig.signal_gate_count(root, "bionic")

    def test_a_u2028_in_the_fence_forges_no_closer_and_inverts_no_roster(self):
        """The measured `gate_count` decoy-roster inversion.

        `signal_gate_count` split its input with `str.splitlines()`, which
        breaks on U+2028. One such character inside the fenced block's first
        content line therefore produced a fence-shaped "line" that closed the
        fence early — freeing the DECOY roster — while the block's real closer
        then opened a phantom fence that swallowed the REAL roster. The signal
        read `computed 1` off the decoy instead of `computed 2` off the
        roster, and reported no ambiguity, because it only ever saw one
        candidate.
        """
        rec = self._gate_count(_decoy_roster_with_separator(U2028))
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 2)

    def test_a_real_newline_in_that_position_does_invert_the_roster(self):
        # PAIRED POSITIVE CONTROL for the test above. The SAME fixture with a
        # real newline where the U+2028 sat DOES close the fence early, and
        # the signal then reads the decoy's single row. So the 2 above is the
        # split discipline firing, not a fixture that could only ever read 2.
        rec = self._gate_count(_decoy_roster_with_separator("\n"))
        self.assertEqual(rec["verdict"], "computed")
        self.assertEqual(rec["value"], 1)


# --------------------------------------------------------------------------
# A7 — a refused named surface narrows a signal, and the basis says so
# --------------------------------------------------------------------------

DATED_LOG = """# log

## [2026-02-10] adr | the only entry in this file

This entry names ADR-0001.
"""

FRICTION_JOURNAL = """# 2026-02

## [2026-02-20 10:00] work | the only entry in this file

Friction: the only real citation in this entry.
"""

FORGE_LOG = """# forge log

## [2026-02-15] fallback | a capability gap that fell back
"""


class RefusedSurfaceIsNamedTests(unittest.TestCase):
    """A refused read narrows a count; the envelope must not read as a zero.

    Two named inputs narrowed silently. Symlinking `log.md` out of the root
    moved `dormancy_days` to `null` for the ADRs mentioned only there, with
    the basis unchanged — and `null` there means "no dated mention", which is
    then false. And `friction_citations` dropped its forge-log entries while
    that leg's basis still read "present", because the presence predicate was
    `is_file()`, which FOLLOWS the symlink `_read_contained` refuses.
    """

    def _root(self) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-refused-")
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def _outside(self) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-refused-outside-")
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_a_readable_dated_log_produces_its_entries(self):
        """POSITIVE CONTROL for every symlink case in this class.

        The three symlink tests below assert `entries == []` over `DATED_LOG`.
        That empty list is evidence of refusal ONLY if the same fixture, read
        normally, is known to produce entries — otherwise a fixture that parses
        to nothing would satisfy all three and the guard could be absent.
        Nothing in this file pinned that, so the greens rested on an unpinned
        assumption. This is the assumption, pinned.

        Verifies the existing implementation. It reproduces no new defect and
        changes no behaviour authored in cff92d0.
        """
        root = self._root()
        docs = root / "bionic"
        docs.mkdir(parents=True)
        (docs / "log.md").write_text(DATED_LOG, encoding="utf-8")
        entries, refused = sig._dated_entries(root, docs)
        self.assertEqual(refused, [])
        self.assertEqual(entries, [("log.md", "2026-02-10", {"ADR-0001"})])
        # And the signal built from those entries is a real measurement, so the
        # refused cases' `null` is a narrowing rather than the fixture's own shape.
        rec = sig.signal_dormancy_days({"ADR-0001": {}}, entries, TODAY, "bionic", refused)
        self.assertIsNotNone(rec["value"]["ADR-0001"])

    def test_a_dangling_symlink_at_a_surface_is_refused_and_named(self):
        # `is_file()`/`is_dir()` follow the link, so a dangling one read as
        # "absent" and the surface vanished from the narrowing with no name —
        # the exact false null `_dated_entries` promises never to produce.
        # A dangling link survives commit and clone, so this is reachable
        # from repository content alone.
        root, outside = self._root(), self._outside()
        docs = root / "bionic"
        docs.mkdir(parents=True)
        (docs / "log.md").symlink_to(outside / "nowhere-log.md")
        (docs / "journal").symlink_to(outside / "nowhere-journal")
        (docs / "promptbooks").mkdir()
        (docs / "promptbooks" / "runs").symlink_to(outside / "nowhere-runs")
        entries, refused = sig._dated_entries(root, docs)
        self.assertEqual(entries, [])
        self.assertEqual(sorted(refused),
                         ["bionic/journal", "bionic/log.md", "bionic/promptbooks/runs"])
        rec = sig.signal_dormancy_days({"ADR-0001": {}}, entries, TODAY, "bionic", refused)
        self.assertIn("3 named surface(s) were refused", rec["filter"])

    def test_a_symlinked_run_snapshot_is_refused_and_named(self):
        root, outside = self._root(), self._outside()
        runs = root / "bionic" / "promptbooks" / "runs" / "PB-0001-x"
        runs.mkdir(parents=True)
        planted = outside / "run-RUN-001.yaml"
        planted.write_text("started_at: '2026-02-01T00:00:00Z'\nnotes: ADR-0001\n", encoding="utf-8")
        (runs / "run-RUN-001.yaml").symlink_to(planted)
        entries, refused = sig._dated_entries(root, root / "bionic")
        self.assertEqual(entries, [])
        self.assertEqual(refused, ["bionic/promptbooks/runs/PB-0001-x/run-RUN-001.yaml"])

    def test_a_symlinked_log_md_is_named_in_the_dormancy_filter(self):
        root, outside = self._root(), self._outside()
        docs = root / "bionic"
        docs.mkdir(parents=True)
        planted = outside / "log.md"
        planted.write_text(DATED_LOG, encoding="utf-8")
        (docs / "log.md").symlink_to(planted)

        entries, refused = sig._dated_entries(root, docs)
        self.assertEqual(entries, [])
        self.assertEqual(refused, ["bionic/log.md"])
        rec = sig.signal_dormancy_days({"ADR-0001": {}}, entries, TODAY, "bionic", refused)
        self.assertIsNone(rec["value"]["ADR-0001"])
        # The narrowing is NAMED, so the null above cannot be read as "no
        # dated mention exists".
        self.assertIn("1 named surface(s) were refused", rec["filter"])
        self.assertIn("bionic/log.md", rec["filter"])

        # PAIRED POSITIVE CONTROL: the identical content in place is read, the
        # refusal list is empty, the day count is real, and the filter names
        # no refusal — so the sentence above tracks the refusal rather than
        # appearing unconditionally.
        (docs / "log.md").unlink()
        shutil.copyfile(planted, docs / "log.md")
        entries2, refused2 = sig._dated_entries(root, docs)
        self.assertEqual(refused2, [])
        control = sig.signal_dormancy_days({"ADR-0001": {}}, entries2, TODAY, "bionic",
                                           refused2)
        self.assertEqual(control["value"]["ADR-0001"], 10)
        self.assertNotIn("were refused", control["filter"])

    #: A refused journal filename carrying ESC and CR. A filename is chosen
    #: by whoever writes the file, so it is untrusted content exactly as a
    #: table cell is — and this one reaches a `filter` a human reads.
    HOSTILE_JOURNAL_NAME = "2026-02\x1b[31m\rhidden.md"

    def test_a_hostile_refused_filename_is_redacted_in_the_table_lane(self):
        """`redact` on the refused paths was deletable with the suite green.

        The existing case refuses `bionic/log.md`, and `redact` returns that
        name unchanged, so both of its assertions held whether the call was
        there or not. Driven with a filename carrying ESC and CR, the
        unguarded lane put both characters raw into the `filter` — a sentence
        `render_table` writes straight to a terminal, where ESC is a control
        sequence and CR returns the carriage over the text before it.
        """
        root, outside = self._root(), self._outside()
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        planted = outside / "planted.md"
        planted.write_text(DATED_LOG, encoding="utf-8")
        (docs / "journal" / self.HOSTILE_JOURNAL_NAME).symlink_to(planted)

        entries, refused = sig._dated_entries(root, docs)
        # POSITIVE CONTROL ON THE FIXTURE: the refusal really did happen, and
        # the name really does carry both characters raw at this point — so
        # the assertions below measure the render and not an empty list.
        self.assertEqual(refused, [f"bionic/journal/{self.HOSTILE_JOURNAL_NAME}"])
        self.assertIn("\x1b", refused[0])
        self.assertIn("\r", refused[0])

        rec = sig.signal_dormancy_days({"ADR-0001": {}}, entries, TODAY, "bionic",
                                       refused)
        filt = rec["filter"]
        self.assertIn("1 named surface(s) were refused", filt)
        # Neither control character survives into the lane.
        self.assertNotIn("\x1b", filt)
        self.assertNotIn("\r", filt)
        # Each is REPLACED rather than dropped, and the replacement is
        # counted, so a truncated or altered name cannot read as a whole one.
        self.assertIn("\ufffd", filt)
        self.assertIn("2 unprintable characters redacted", filt)

    def test_a_benign_refused_filename_carries_no_redaction_note(self):
        """PAIRED POSITIVE CONTROL for the case above: a refused name with
        nothing to redact round-trips byte-for-byte and gains no note, so the
        note is the guard firing rather than a suffix on every named surface.
        """
        root, outside = self._root(), self._outside()
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        planted = outside / "planted.md"
        planted.write_text(DATED_LOG, encoding="utf-8")
        (docs / "journal" / "2026-02.md").symlink_to(planted)

        entries, refused = sig._dated_entries(root, docs)
        self.assertEqual(refused, ["bionic/journal/2026-02.md"])
        filt = sig.signal_dormancy_days({"ADR-0001": {}}, entries, TODAY, "bionic",
                                        refused)["filter"]
        self.assertIn("bionic/journal/2026-02.md", filt)
        self.assertNotIn("redacted", filt)

    def test_a_symlinked_forge_log_reads_absent_rather_than_present(self):
        root, outside = self._root(), self._outside()
        docs = root / "bionic"
        (docs / "journal").mkdir(parents=True)
        (docs / "journal" / "2026-02.md").write_text(FRICTION_JOURNAL, encoding="utf-8")
        planted = outside / "forge-log.md"
        planted.write_text(FORGE_LOG, encoding="utf-8")
        local = root / ".claude" / "skills"
        local.mkdir(parents=True)
        (local / "forge-log.md").symlink_to(planted)

        rec = sig.signal_friction_citations(root, docs, "bionic", "2026-02-14")
        self.assertEqual(rec["verdict"], "computed")
        # The read was refused, so the leg reports ABSENT and contributes
        # nothing. The basis and the count agree.
        self.assertIn(".opencode/skill) — absent", rec["basis"])
        self.assertEqual(rec["value"], 1)

        # PAIRED POSITIVE CONTROL: the identical log in place is read, the leg
        # reports PRESENT, and its one fallback entry joins the count — so the
        # "absent" above is the refused read and not a log that never had an
        # entry to contribute.
        (local / "forge-log.md").unlink()
        shutil.copyfile(planted, local / "forge-log.md")
        control = sig.signal_friction_citations(root, docs, "bionic", "2026-02-14")
        self.assertIn(".opencode/skill) — present", control["basis"])
        self.assertEqual(control["value"], 2)


#: A run snapshot whose `notes` key is non-empty, so the notes leg has
#: something to count when it is allowed to read the file.
PLANTED_RUN_SNAPSHOT = """book: PB-0001
started_at: 2026-02-18
notes: |
  A note the notes leg counts when it reads this file.
"""

#: A `whats_next.md` whose frontmatter carries a dismissal naming an ADR.
PLANTED_WHATS_NEXT = """---
dismissed:
  - id: CLN-PJ-2
    reason: superseded by ADR-0001
---

# What's next
"""


class ContainedReadOnEveryFrictionLegTests(unittest.TestCase):
    """The friction signal's four legs each read through `_read_contained`,
    and TWO of those calls were deletable with the suite green.

    Both reverted to a plain `_read` — which FOLLOWS a symlink — and nothing
    noticed, because every existing case for those legs plants a real file
    inside the root, where `_read` and `_read_contained` agree. A file
    symlinked out of the root is where they part: `_read` serves its content
    into a count, and `_read_contained` refuses it.
    """

    def _root(self) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-friction-contained-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "bionic" / "journal").mkdir(parents=True)
        (root / "bionic" / "journal" / "2026-02.md").write_text(
            FRICTION_JOURNAL, encoding="utf-8")
        return root

    def _outside(self) -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="adr-signals-friction-outside-")
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def _friction(self, root: Path) -> dict:
        return sig.signal_friction_citations(root, root / "bionic", "bionic",
                                             "2026-02-14")

    def test_a_symlinked_run_snapshot_contributes_no_note(self):
        root, outside = self._root(), self._outside()
        runs = root / "bionic" / "promptbooks" / "runs" / "PB-0001"
        runs.mkdir(parents=True)
        planted = outside / "RUN-001.yaml"
        planted.write_text(PLANTED_RUN_SNAPSHOT, encoding="utf-8")
        (runs / "RUN-001.yaml").symlink_to(planted)

        rec = self._friction(root)
        self.assertEqual(rec["verdict"], "computed")
        # The snapshot is GLOBBED — the leg reports present, because a file of
        # that name is there — and read as nothing, so neither the `notes` key
        # nor its body reaches the count. The journal's one citation is all
        # that is left.
        self.assertIn("0 snapshot(s) carry a `notes` key, 0 of them non-empty",
                      rec["basis"])
        self.assertEqual(rec["value"], 1)

        # PAIRED POSITIVE CONTROL: the identical snapshot IN PLACE is read,
        # its non-empty `notes` joins the count, and the basis says so — so
        # the zero above is the containment refusing and not a snapshot that
        # never had a note to contribute.
        (runs / "RUN-001.yaml").unlink()
        shutil.copyfile(planted, runs / "RUN-001.yaml")
        control = self._friction(root)
        self.assertIn("1 snapshot(s) carry a `notes` key, 1 of them non-empty",
                      control["basis"])
        self.assertEqual(control["value"], 2)

    def test_a_symlinked_whats_next_contributes_no_dismissal(self):
        root, outside = self._root(), self._outside()
        planted = outside / "whats_next.md"
        planted.write_text(PLANTED_WHATS_NEXT, encoding="utf-8")
        (root / "bionic" / "whats_next.md").symlink_to(planted)

        rec = self._friction(root)
        self.assertEqual(rec["verdict"], "computed")
        # `is_file()` FOLLOWS the symlink, so the file looks present; the read
        # refuses it, so the dismissed block is never seen and the leg reports
        # absent. The predicate and the count agree.
        self.assertIn("whats_next.md dismissals — absent", rec["basis"])
        self.assertEqual(rec["value"], 1)

        # PAIRED POSITIVE CONTROL: the identical file in place is read, its
        # one ADR-naming dismissal joins the count, and the leg reports
        # present.
        (root / "bionic" / "whats_next.md").unlink()
        shutil.copyfile(planted, root / "bionic" / "whats_next.md")
        control = self._friction(root)
        self.assertIn("whats_next.md dismissals — present", control["basis"])
        self.assertEqual(control["value"], 2)


# --------------------------------------------------------------------------
# A8 — `_read_contained` refuses for four reasons, and the prose names them
# --------------------------------------------------------------------------

class RefusalReasonIsTrueTests(unittest.TestCase):
    """A contained, mode-000 file is refused for reason 4, not reason 2.

    Every caller sentence asserted the containment leg alone, so a
    CHANGELOG.md that sits inside the root and merely will not open reported
    "resolves outside that root" — a false statement about a true refusal.
    """

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "a root process reads a mode-000 file, so the refusal never fires")
    def test_a_contained_mode_000_changelog_reports_a_true_refusal_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            changelog = root / "CHANGELOG.md"
            changelog.write_text(THREE_RELEASE_CHANGELOG, encoding="utf-8")

            # PAIRED POSITIVE CONTROL, taken FIRST on the identical file: while
            # it is readable the same reader computes, so the refusal below is
            # the mode and not the fixture.
            control = sig.signal_release_cadence(root, "bionic")
            self.assertEqual(control["verdict"], "computed")
            self.assertEqual(control["value"]["intervals_days"], [10, 15])

            os.chmod(changelog, 0o000)
            try:
                rec = sig.signal_release_cadence(root, "bionic")
            finally:
                # Restored INSIDE the temporary directory's lifetime; an
                # `addCleanup` here runs after the directory is gone.
                os.chmod(changelog, 0o644)
            self.assertEqual(rec["verdict"], "unmeasurable")
            self.assertIsNone(rec["value"])
            # The reported reason must be TRUE of this refusal. The file is
            # contained, so the disjunct that fired is the open failing.
            self.assertIn("was not read as a contained artifact", rec["filter"])
            self.assertIn("the open failed for another reason", rec["filter"])
            # NEGATIVE: the old sentence asserted containment as the SOLE
            # reason and must never return.
            self.assertNotIn("resolves outside that root, so the read is not contained",
                             rec["filter"])


# --------------------------------------------------------------------------
# A9 — the open takes the RESOLVED name, which is the ancestor half of the
# containment claim; `O_NOFOLLOW` guards the leaf alone
# --------------------------------------------------------------------------

class ContainedReadAncestorTests(unittest.TestCase):
    """An ANCESTOR swapped to a symlink after the resolve is never traversed.

    `os.open(str(resolved), flags)` was replaceable with
    `os.open(str(path), flags)` with the whole module green, yet an
    ancestor-swap probe then served attacker content in place of the safe
    file. `O_NOFOLLOW` cannot cover this: it refuses a symlinked LEAF, and the
    swapped component here is a directory.
    """

    def test_an_ancestor_swapped_to_a_symlink_after_resolve_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as root_dir, \
                tempfile.TemporaryDirectory() as outside_dir:
            root = Path(root_dir)
            outside = Path(outside_dir)
            real_dir = root / "dir_real"
            real_dir.mkdir()
            (real_dir / "ADR-9002-ancestor.md").write_text("safe content",
                                                           encoding="utf-8")
            (outside / "ADR-9002-ancestor.md").write_text("attacker content",
                                                          encoding="utf-8")
            link_dir = root / "dir"
            link_dir.symlink_to(real_dir)
            target = link_dir / "ADR-9002-ancestor.md"

            real_resolve = Path.resolve
            swapped = {"done": False}

            def resolve_and_swap(self_path, strict=False):
                result = real_resolve(self_path, strict=strict)
                if not swapped["done"] and self_path == target:
                    swapped["done"] = True
                    link_dir.unlink()
                    link_dir.symlink_to(outside)
                return result

            with unittest.mock.patch.object(Path, "resolve", resolve_and_swap):
                text = sig._read_contained(root, target)
            self.assertTrue(swapped["done"], "the fixture never triggered the swap")
            self.assertEqual(text, "safe content")
            # PAIRED POSITIVE CONTROL: the path AS GIVEN now really does reach
            # the attacker's file, so the read above took the resolved name
            # rather than the fixture being harmless.
            self.assertEqual(target.read_text(encoding="utf-8"), "attacker content")


# --------------------------------------------------------------------------
# the DICT KEY on the table lane
# --------------------------------------------------------------------------

#: An ADR `id:` scalar carrying ESC. `read_active_adrs` lifts `id` with `re`
#: and never checks it against the `ADR-\d{4}` grammar the rest of the file
#: uses, so this is what an ADR file's author can put in a key. `\x1b[2J`
#: clears the reader's screen and `\x1b[31m...\x1b[0m` colours forged text.
HOSTILE_ADR_ID = "ADR-0001\x1b[2J\x1b[31mALL CLEAR\x1b[0m"

#: The other half of the class: a key spelling the SAMPLE'S OWN SEPARATOR.
#: Nothing here is unprintable, so the redaction alone does not touch it —
#: what keeps it from forging a fourth pair is the delimiting `repr`.
SEPARATOR_ADR_ID = "ADR-0001=999, ADR-9999"


def _one_signal_envelope(value) -> dict:
    """The smallest envelope `render_table` accepts, carrying one record."""
    return {"active_adrs": 1,
            "signals": [{"signal": "paper_only", "verdict": "computed",
                         "value": value, "basis": "b", "filter": None}]}


class RenderedDictKeyTests(unittest.TestCase):
    """A dict KEY reaches the table lane bounded, redacted and delimited.

    `_render_value` routed the VALUE through `json.dumps` and the KEY through
    a bare f-string. The three ADR-keyed signals — `amendment_fan_in`,
    `paper_only`, `dormancy_days` — key on the verbatim `id:` scalar of an
    ADR's frontmatter, so an ADR file's author chose every byte of that key
    and `render_table` wrote it straight to a terminal.

    The render is `redact(k, quoted=True)`, matching `_prep_key` — the
    sibling in the same module that renders a mined string as a key-like
    token. `quoted=False` was measured wrong for the same reason it was wrong
    there: it puts the redaction note INSIDE the `k=v` pair with nothing
    marking where the key ends, so a key and the note describing it become
    one run of text. Quoted, the note sits outside the quotes.
    """

    def test_a_hostile_adr_id_key_is_redacted_on_the_table_lane(self):
        # POSITIVE CONTROL ON THE FIXTURE: the key really does carry ESC at
        # the point the renderer receives it, so the assertions below measure
        # the render rather than a benign input.
        value = {HOSTILE_ADR_ID: True, "ADR-0002": False, "ADR-0003": None}
        self.assertIn("\x1b", next(iter(value)))

        table = sig.render_table(_one_signal_envelope(value))

        self.assertNotIn("\x1b", table)
        # REPLACED rather than dropped, and counted, so a mangled id cannot
        # read as a whole one.
        self.assertIn("\ufffd", table)
        self.assertIn("unprintable characters redacted", table)
        # The record still renders: the guard bounds the key, it does not
        # swallow the row.
        self.assertIn("3 entries", table)
        self.assertIn("=false", table)

    def test_the_raw_lane_really_did_carry_the_escape(self):
        """ANTI-VACUITY. The assertion above is an ABSENCE, so it would hold
        just as well against a renderer that dropped the sample entirely.
        This drives the same key through the unrouted expression the fix
        replaced and shows ESC arriving on the lane, so the absence above is
        the guard firing rather than an empty string.
        """
        unrouted = ", ".join(
            f"{k}={json.dumps(v)}"
            for k, v in {HOSTILE_ADR_ID: True}.items())
        self.assertIn("\x1b[2J", unrouted)
        self.assertIn("ALL CLEAR", unrouted)

    def test_a_separator_spelling_key_cannot_forge_a_fourth_pair(self):
        """The printable half of the class, which the redaction alone does
        not close: `=` and `, ` are the sample's own structure, and a key
        spelling them added a pair the mapping never held. The delimiting
        `repr` is what contains it — the forged text renders inside the
        quotes that mark the key.
        """
        value = {SEPARATOR_ADR_ID: 0, "ADR-0002": 0, "ADR-0003": 0}
        table = sig.render_table(_one_signal_envelope(value))

        sample = table.split("value:   ", 1)[1].split("\n", 1)[0]
        # Every key is `repr`-quoted, so `'=` is the pair delimiter and
        # counting it counts PAIRS. Three entries in, three pairs out;
        # unrouted this sample read four, the fourth a forged `ADR-9999=0`.
        self.assertEqual(sample.count("'="), 3, sample)
        # The forged text is still SHOWN — nothing is dropped — but it is
        # shown inside the quotes that mark it as one key's content.
        self.assertIn("'ADR-0001=999, ADR-9999'=0", sample)
        self.assertNotIn(", ADR-9999=0,", sample)

    def test_a_benign_key_renders_as_its_own_repr_with_no_note(self):
        """PAIRED POSITIVE CONTROL: an id the redaction loses nothing from
        gains no note, so the note is the guard firing rather than a suffix
        on every key. The quotes are `repr`'s and are the delimiter the case
        above relies on.
        """
        table = sig.render_table(_one_signal_envelope({"ADR-0001": 3}))
        self.assertIn("'ADR-0001'=3", table)
        self.assertNotIn("redacted", table)
        self.assertNotIn("truncated", table)

    def test_an_overlong_key_is_bounded_and_names_its_true_length(self):
        """LENGTH, the third channel hazard. The `id:` scalar is read with
        `re` and carries no length bound of its own, so a 5000-character id
        put 5000 characters on one terminal line.
        """
        long_id = "ADR-0001" + "9" * 5000
        table = sig.render_table(_one_signal_envelope({long_id: 1}))
        self.assertIn("truncated from 5008 characters", table)
        # Bounded by the shown head, its `repr` quotes and the note — never
        # by the raw length.
        self.assertLess(len(table), 5000)

    def test_the_three_adr_keyed_signals_all_route_through_the_render(self):
        """The SIBLING SWEEP, asserted rather than argued. All three
        ADR-keyed signals build their map from the same `active` keys, so a
        guard on one of them and not the others would leave the class open on
        two inputs — which is how the last three rounds of this cycle each
        left a sibling behind.
        """
        active = {HOSTILE_ADR_ID: {"amends": [], "supersedes": []}}
        records = [
            sig.signal_amendment_fan_in(active, "bionic"),
            sig.signal_paper_only(active, {}, "bionic"),
            sig.signal_dormancy_days(active, [], TODAY, "bionic"),
        ]
        for rec in records:
            with self.subTest(signal=rec["signal"]):
                # The ENVELOPE keeps the raw id — that residue is named in the
                # module docstring and is `json.dumps`-escaped on the JSON
                # lane. It is the TABLE lane the render bounds.
                self.assertIn(HOSTILE_ADR_ID, rec["value"])
                table = sig.render_table({"active_adrs": 1, "signals": [rec]})
                self.assertNotIn("\x1b", table)
                self.assertIn("unprintable characters redacted", table)


if __name__ == "__main__":
    unittest.main()
