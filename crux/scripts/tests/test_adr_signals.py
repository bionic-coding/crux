"""Regression tests for `adr-signals.py`, the decision review's five signals.

Every case reads the miniature repo roots under
`crux/scripts/tests/fixtures/adr-signals-corpus/` and nothing else: `trips/`
carries a fixture that trips each signal, `quiet/` one that does not. No case
reads the live tree, the README, or any other dev-only surface, so the suite
passes unchanged against the crux-only staged artifact.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
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
    def test_positive_a_journal_with_reflective_sections_is_computed(self):
        # Positive control for the fourth leg: the materializer placed a forge
        # log carrying a `fallback` entry, so the count below includes it.
        forge = TRIPS / ".claude" / "skills" / "forge-log.md"
        self.assertTrue(forge.is_file())
        self.assertIn("] fallback |", forge.read_text(encoding="utf-8"))
        rec = record(TRIPS, "friction_citations")
        self.assertEqual(rec["verdict"], "computed")
        # 2 journal `### ` headings + 1 non-empty snapshot note + 1 dismissal
        # naming an ADR + 1 fallback forge-log entry.
        self.assertEqual(rec["value"], 5)
        self.assertIsNone(rec["filter"])

    def test_negative_a_journal_with_no_reflective_section_is_unmeasurable(self):
        rec = record(QUIET, "friction_citations")
        self.assertEqual(rec["verdict"], "unmeasurable")
        self.assertIsNone(rec["value"])
        self.assertIn("no grammar at all", rec["filter"])
        # Positive control: the journal FILE exists and carries a real entry —
        # only the `### ` grammar is missing. An unmeasurable verdict driven by
        # a missing directory would be a different (and wrong) finding.
        journal = QUIET / "bionic" / "journal" / "2026-02.md"
        self.assertTrue(journal.is_file())
        self.assertIn("## [2026-02-11 09:00]", journal.read_text(encoding="utf-8"))
        # Second positive control: the other three legs report present, so the
        # verdict turns on the journal leg alone.
        for leg in ("run-snapshot notes", "whats_next.md dismissals", "forge-log.md"):
            self.assertIn(leg, rec["basis"])
        self.assertEqual(rec["basis"].count("— present"), 3)
        self.assertEqual(rec["basis"].count("— absent"), 1)

    def test_index_md_headings_are_not_counted_as_reflective_sections(self):
        index = TRIPS / "bionic" / "journal" / "index.md"
        # Positive control: index.md DOES carry a `### ` heading, so excluding
        # it is a real subtraction rather than a no-op over an empty file.
        self.assertIn("### This heading is in index.md", index.read_text(encoding="utf-8"))
        self.assertEqual(record(TRIPS, "friction_citations")["value"], 5)


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


class EnvelopeContractTests(unittest.TestCase):
    def test_every_record_carries_exactly_the_five_members(self):
        for root in (TRIPS, QUIET):
            with self.subTest(root=root.name):
                env = envelope(root)
                self.assertEqual(set(env), {"active_adrs", "signals"})
                self.assertEqual(len(env["signals"]), 5)
                assert_envelope_contract(self, env)

    def test_each_adr_keyed_mapping_has_exactly_active_adrs_keys(self):
        for root in (TRIPS, QUIET):
            with self.subTest(root=root.name):
                env = envelope(root)
                keyed = {r["signal"]: r["value"] for r in env["signals"]
                         if isinstance(r["value"], dict)}
                self.assertEqual(set(keyed),
                                 {"amendment_fan_in", "paper_only", "dormancy_days"})
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

    def test_table_mode_renders_all_five_members_of_every_signal(self):
        proc = _run("--repo-root", str(TRIPS), "--today", TODAY.isoformat())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("active_adrs: 3", proc.stdout)
        for name in ("amendment_fan_in", "carve_out_count", "paper_only",
                     "dormancy_days", "friction_citations"):
            self.assertIn(name, proc.stdout)
        for label in ("verdict:", "value:", "basis:", "filter:"):
            self.assertEqual(proc.stdout.count(label), 5, label)
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
            self.assertEqual(len(payload["signals"]), 5)
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


if __name__ == "__main__":
    unittest.main()
