"""The ADR provenance reader CLI (`crux/scripts/adr-provenance.py`).

Pins, one named test per claim (rule:provenance-is-recorded-at-acceptance,
rule:in-run-adr-text-is-guidance, rule:owner-promotes-guidance):

  - a rule added in-run is guidance; an edited pre-existing rule is binding at its base entry,
    and an edit to any governs field but `handle` and `provenance` is in-run text; an unchanged
    one is binding at its own entry; a rule removed in-run is listed, stays promotable, and is
    numbered after the rules;
  - an ADR first proposed in the run has every rule guidance and base_path null;
  - `record` without `--run` refuses and writes nothing (the same fixture with `--run` writes);
  - an unresolvable base_commit refuses; a record is written once; a symlinked provenance
    directory refuses; the writer never writes through a planted link;
  - `promote` by numbers and by `all`, with `--dry-run` writing nothing, and each refusal;
  - `open` lists unpromoted in-run changes and drops them after promotion;
  - ADR-0150 at the run commit it was accepted against classifies six guidance rules and
    twelve binding rules, by dry-run (dev checkout only).

Fixtures are throwaway git repositories in temp dirs. Needs PyYAML (the uv lane) and git.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from ._dev_surface import REPO_ROOT, TREE, require_dev_surface
except ImportError:
    from _dev_surface import REPO_ROOT, TREE, require_dev_surface

CLI = SCRIPTS_DIR / "adr-provenance.py"
ACCEPTING_RUN_BASE = "21ef406e225969f97c21b4a6be98bf61ca21d2d3"
UNKNOWN_COMMIT = "1234567890abcdef1234567890abcdef12345678"


def _load():
    spec = importlib.util.spec_from_file_location("adr_provenance_cli", CLI)
    module = importlib.util.module_from_spec(spec)
    sys.modules["adr_provenance_cli"] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return proc.stdout.strip()


ACCEPTED_ON = "2026-10-12"


def adr_text(num: int, rules: dict[str, str], status: str = "Accepted") -> str:
    lines = ["---", f"id: ADR-{num:04d}", f'title: "Decision {num}"', f"status: {status}"]
    if status == "Accepted":
        lines.append(f"accepted_date: {ACCEPTED_ON}")
    lines.append("governs:")
    for slug, wording in rules.items():
        lines += ["  - domain: tests", f'    rule: "{wording}"', "    scope: crux/",
                  f"    handle: ADR-{num:04d}/{slug}", "    provenance: authored"]
    lines += ["---", "", "Body.", ""]
    return "\n".join(lines)


def adr_entries_text(num: int, entries: list[dict], status: str = "Accepted",
                     amends: list[str] | None = None) -> str:
    """An ADR whose governs entries carry every field the caller gives (handle added here)."""
    import yaml
    governs = [{**{k: v for k, v in e.items() if k != "slug"},
                "handle": f"ADR-{num:04d}/{e['slug']}"} for e in entries]
    head = {"id": f"ADR-{num:04d}", "title": f"Decision {num}", "status": status}
    if amends is not None:
        head["amends"] = amends
    if status == "Accepted":
        head["accepted_date"] = ACCEPTED_ON
    front = yaml.safe_dump({**head, "governs": governs}, sort_keys=False, width=1_000_000)
    return f"---\n{front}---\n\nBody.\n"


def run_yaml(base: str, *, status: str = "in_progress", started: str = "2026-10-12T09:00:00Z",
             artifacts: tuple[str, ...] = ("docs/adrs/ADR-0007-decision.md",), book: str = "PB-0001") -> str:
    """A run snapshot: in progress, started the day ADR-0007 is accepted, naming ADR-0007."""
    names = ", ".join(f'"{a}"' for a in artifacts)
    return (f"format_version: '2'\nbook_id: {book}\nrun_id: RUN-001\nbase_commit: {base}\n"
            f"started_at: '{started}'\nstatus: {status}\nprompts:\n- n: 1\n  artifacts: [{names}]\n")


class Repo:
    """A throwaway repository: `docs/adrs/`, a `.bionic.yml`, and a committed run snapshot."""

    def __init__(self, tc: unittest.TestCase):
        self._tmp = tempfile.TemporaryDirectory()
        tc.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.name", "T")
        _git(self.root, "config", "user.email", "t@example.com")
        _git(self.root, "config", "commit.gpgsign", "false")
        (self.root / ".bionic.yml").write_text('config_version: "1"\ndocs_dir: docs\n')
        self.adrs = self.root / "docs" / "adrs"
        self.adrs.mkdir(parents=True)

    def commit(self, message: str) -> str:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", message)
        return _git(self.root, "rev-parse", "HEAD")

    def write_adr(self, num: int, rules: dict[str, str], status: str = "Accepted") -> Path:
        path = self.adrs / f"ADR-{num:04d}-decision.md"
        path.write_text(adr_text(num, rules, status))
        return path

    def snapshot(self, base: str, *, book: str = "PB-0001", **fields) -> str:
        rel = f"docs/promptbooks/runs/{book}-x/run-RUN-001.yaml"
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(run_yaml(base, book=book, **fields))
        self.commit("snapshot")
        return rel

    def witness(self, paths: list[str], *, book: str = "PB-0001") -> None:
        """Commit a run-work witness beside the snapshot, one prompt-1 entry per path."""
        path = self.root / f"docs/promptbooks/runs/{book}-x/run-work-witness.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = [{"path": p, "prompt": 1, "sha256": "0" * 64, "written_at": "2026-10-12T09:00:00Z"}
                   for p in paths]
        path.write_text(json.dumps({"record_type": "run-work-witness", "format_version": "1",
                                    "book": book, "run_id": "RUN-001", "entries": entries}))
        self.commit("witness")

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(CLI), *args, "--repo-root", str(self.root)],
                              capture_output=True, text=True, check=False)

    def record_path(self, num: int) -> Path:
        return self.adrs / "provenance" / f"ADR-{num:04d}.yaml"


def in_run_repo(tc: unittest.TestCase, base_rules: dict[str, str], run_rules: dict[str, str]):
    """ADR-0007 holds `base_rules` at base_commit and `run_rules` after the run's edits."""
    repo = Repo(tc)
    repo.write_adr(7, base_rules, status="Proposed")
    base = repo.commit("base")
    repo.write_adr(7, run_rules)
    repo.commit("in-run edit")
    return repo, repo.snapshot(base), base


def rules_by_handle(record: dict) -> dict[str, dict]:
    return {r["handle"]: r for r in record["rules"]}


def _base_of(repo: "Repo", run: str) -> str:
    import yaml
    return yaml.safe_load((repo.root / run).read_text())["base_commit"]


def _read_record(repo: "Repo", num: int) -> dict:
    import adr_provenance
    return adr_provenance.parse_record(repo.record_path(num).read_text(), name=repo.record_path(num).name)


class ClassifyTests(unittest.TestCase):
    def test_added_edited_unchanged_and_removed_rules(self):
        repo, run, base = in_run_repo(
            self,
            {"keep": "Keep this.", "edit": "Old wording.", "drop": "Dropped wording."},
            {"keep": "Keep this.", "edit": "New wording.", "add": "Added in the run."})
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)
        record = json.loads(done.stdout)
        rules = rules_by_handle(record)
        entry = lambda wording: {"domain": "tests", "rule": wording, "scope": "crux/", "provenance": "authored"}
        # a. added in-run -> guidance, no binding version
        self.assertEqual(rules["ADR-0007/add"]["standing"], "guidance")
        self.assertIsNone(rules["ADR-0007/add"]["base"])
        # b. edited -> binding at its base entry; unchanged -> binding at its own entry
        edit = rules["ADR-0007/edit"]
        self.assertEqual(edit["standing"], "binding")
        self.assertEqual(edit["base"], entry("Old wording."))
        self.assertEqual(edit["entry"], entry("New wording."))
        keep = rules["ADR-0007/keep"]
        self.assertEqual((keep["standing"], keep["base"], keep["entry"]),
                         ("binding", entry("Keep this."), entry("Keep this.")))
        # f. removed in-run, with its whole base entry
        self.assertEqual(record["removed_in_run"],
                         [{"handle": "ADR-0007/drop", "base": entry("Dropped wording.")}])
        self.assertEqual([r["handle"] for r in record["rules"]],
                         ["ADR-0007/keep", "ADR-0007/edit", "ADR-0007/add"])
        self.assertEqual(record["base_commit"], base)

    def test_classify_is_pure_and_matches_by_handle_only(self):
        cli = _load()
        a2, b, g = {"rule": "A2"}, {"rule": "B"}, {"rule": "G"}
        current = [{"handle": "ADR-0007/a", "entry": a2}, {"handle": "ADR-0007/b", "entry": b}]
        base = [{"handle": "ADR-0007/b", "entry": b}, {"handle": "ADR-0007/gone", "entry": g}]
        rules, removed = cli.classify(current, base)
        self.assertEqual(rules[0], {"handle": "ADR-0007/a", "standing": "guidance", "entry": a2, "base": None})
        self.assertEqual(rules[1]["base"], b)
        self.assertEqual(removed, [{"handle": "ADR-0007/gone", "base": g}])
        # with no base at all every rule is guidance and nothing is removed
        rules, removed = cli.classify(current, None)
        self.assertEqual([r["standing"] for r in rules], ["guidance", "guidance"])
        self.assertEqual(removed, [])

    def test_adr_first_proposed_in_the_run_is_all_guidance(self):
        repo = Repo(self)
        repo.write_adr(1, {"other": "Other ADR."})
        base = repo.commit("base")
        repo.write_adr(7, {"one": "First.", "two": "Second."})
        repo.commit("new adr")
        run = repo.snapshot(base)
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)
        record = json.loads(done.stdout)
        self.assertIsNone(record["base_path"])
        self.assertIsNone(record["base_sha256"])
        self.assertEqual([r["standing"] for r in record["rules"]], ["guidance", "guidance"])
        self.assertEqual(record["removed_in_run"], [])

    def test_base_path_and_digest_are_the_base_bytes(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One."})
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        record = json.loads(done.stdout)
        self.assertEqual(record["base_path"], "docs/adrs/ADR-0007-decision.md")
        base_bytes = adr_text(7, {"a": "One."}, status="Proposed").encode()
        self.assertEqual(record["base_sha256"], hashlib.sha256(base_bytes).hexdigest())
        self.assertEqual(record["run"], {"book_id": "PB-0001", "run_id": "RUN-001", "snapshot": run})

    def test_dry_run_writes_nothing_and_a_real_run_writes_a_parseable_record(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertFalse((repo.adrs / "provenance").exists())
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run).returncode, 0)
        record = _read_record(repo, 7)
        self.assertEqual([r["standing"] for r in record["rules"]], ["binding", "guidance"])

    def test_a_governs_field_outside_the_governs_set_is_a_validation_error(self):
        repo, run = entries_repo(self, [_entry("a")], [_entry("a", weight="high")])
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 1, done.stderr)
        problems = json.loads(done.stdout)["validation_errors"]
        self.assertTrue(any("fields outside" in p["problem"] for p in problems), problems)


class NoRunTests(unittest.TestCase):
    def test_record_without_run_refuses_and_with_run_writes(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        refused = repo.cli("record", "--adr", "ADR-0007")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("accepted outside a run has no in-run text", refused.stderr)
        self.assertFalse((repo.adrs / "provenance").exists())
        # positive control: the same fixture with --run writes the record
        written = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(repo.record_path(7).is_file())


class RecordRefusalTests(unittest.TestCase):
    def test_unresolvable_base_commit_refuses_and_writes_nothing(self):
        repo = Repo(self)
        repo.write_adr(7, {"a": "One."})
        repo.commit("base")
        run = repo.snapshot(UNKNOWN_COMMIT)
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("does not resolve", refused.stderr)
        self.assertIn("refuses rather than guessing", refused.stderr)
        self.assertFalse((repo.adrs / "provenance").exists())
        # positive control: a base_commit that resolves writes
        head = _git(repo.root, "rev-parse", "HEAD")
        run = repo.snapshot(head)
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run).returncode, 0)

    def test_malformed_base_commit_refuses(self):
        repo = Repo(self)
        repo.write_adr(7, {"a": "One."})
        repo.commit("base")
        run = repo.snapshot("HEAD")
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("full lowercase commit id", refused.stderr)

    def test_diverged_snapshot_refuses(self):
        repo, run, base = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        head = _git(repo.root, "rev-parse", "HEAD")
        (repo.root / run).write_text(run_yaml(head))                 # uncommitted forward move
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("diverges", refused.stderr)
        (repo.root / run).write_text(run_yaml(base))                 # control: restored
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run").returncode, 0)

    def test_second_record_refuses_and_leaves_the_first_unchanged(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run).returncode, 0)
        first = repo.record_path(7).read_bytes()
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("already exists", refused.stderr)
        self.assertEqual(repo.record_path(7).read_bytes(), first)

    def test_adr_must_be_accepted_and_unique(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One."})
        repo.write_adr(7, {"a": "One."}, status="Proposed")
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("Accepted", refused.stderr)
        repo.write_adr(7, {"a": "One."})
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run").returncode, 0)
        (repo.adrs / "ADR-0007-twin.md").write_text(adr_text(7, {"a": "One."}))
        twin = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(twin.returncode, 2)
        self.assertIn("exactly one", twin.stderr)
        missing = repo.cli("record", "--adr", "ADR-0099", "--run", run, "--dry-run")
        self.assertEqual(missing.returncode, 2)

    def test_symlinked_provenance_directory_refuses(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, True)
        (repo.adrs / "provenance").symlink_to(outside)
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("symlink", refused.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_duplicate_handle_in_governs_is_a_validation_error(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One."})
        path = repo.adrs / "ADR-0007-decision.md"
        dup = ('  - domain: tests\n    rule: "Dup."\n    scope: crux/\n'
               "    handle: ADR-0007/a\n    provenance: authored\n")
        path.write_text(path.read_text().replace("---\n\nBody", dup + "---\n\nBody"))
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 1)
        self.assertTrue(json.loads(done.stdout)["validation_errors"])

    def test_unparseable_working_frontmatter_is_a_validation_error_not_a_traceback(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One."})
        path = repo.adrs / "ADR-0007-decision.md"
        path.write_text("---\nid: ADR-0007\nstatus: Accepted\ngoverns: [\n---\n\nBody.\n")
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        problems = json.loads(done.stdout)["validation_errors"]
        self.assertTrue(any("not valid YAML" in p["problem"] for p in problems), problems)
        self.assertFalse(repo.record_path(7).exists())

    def test_non_mapping_working_frontmatter_is_a_validation_error_not_a_traceback(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One."})
        path = repo.adrs / "ADR-0007-decision.md"
        path.write_text("---\n- one\n- two\n---\n\nBody.\n")
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        problems = json.loads(done.stdout)["validation_errors"]
        self.assertTrue(any("mapping" in p["problem"] for p in problems), problems)


class ArgumentAnchorTests(unittest.TestCase):
    def test_adr_argument_with_a_trailing_newline_refuses(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One."})
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")  # positive control
        self.assertEqual(done.returncode, 0, done.stderr)
        refused = repo.cli("record", "--adr", "ADR-0007\n", "--run", run, "--dry-run")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("--adr must be ADR-NNNN", refused.stderr)


class BaseBytesRefusalTests(unittest.TestCase):
    """An ADR that existed at base_commit whose bytes do not read must refuse, never demote."""

    def _repo(self, base_bytes: bytes):
        repo = Repo(self)
        (repo.adrs / "ADR-0007-decision.md").write_bytes(base_bytes)
        base = repo.commit("base")
        repo.write_adr(7, {"a": "One."})
        repo.commit("in-run edit")
        return repo, repo.snapshot(base)

    def test_crlf_base_refuses_and_writes_nothing(self):
        crlf = adr_text(7, {"a": "One."}, status="Proposed").replace("\n", "\r\n").encode()
        repo, run = self._repo(crlf)
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("ADR-0007 at", refused.stderr)
        self.assertIn("frontmatter", refused.stderr)
        self.assertFalse(repo.record_path(7).exists())

    def test_non_utf8_base_refuses_and_writes_nothing(self):
        raw = adr_text(7, {"a": "One."}, status="Proposed").encode() + b"\xff\xfe\n"
        repo, run = self._repo(raw)
        refused = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("UTF-8", refused.stderr)
        self.assertFalse(repo.record_path(7).exists())

    def test_base_with_frontmatter_but_no_governs_is_all_guidance(self):
        # positive control: legitimate, not a refusal
        base = b"---\nid: ADR-0007\ntitle: x\nstatus: Proposed\n---\n\nBody.\n"
        repo, run = self._repo(base)
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)
        record = json.loads(done.stdout)
        self.assertIsNotNone(record["base_path"])
        self.assertEqual({r["standing"] for r in record["rules"]}, {"guidance"})


class PromoteTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.run, _ = in_run_repo(
            self, {"keep": "Keep.", "edit": "Old."},
            {"keep": "Keep.", "edit": "New.", "add": "Added.", "add2": "Added two."})
        done = self.repo.cli("record", "--adr", "ADR-0007", "--run", self.run)
        self.assertEqual(done.returncode, 0, done.stderr)
        # rules, in order: 1 keep (no in-run text), 2 edit, 3 add, 4 add2

    def promote(self, *extra: str):
        return self.repo.cli("promote", "--adr", "ADR-0007", "--instruction",
                             "promote ADR-0007: rules 2", "--date", "2026-10-12", *extra)

    def record(self) -> dict:
        return _read_record(self.repo, 7)

    def test_promote_by_numbers_appends_and_dry_run_writes_nothing(self):
        before = self.repo.record_path(7).read_bytes()
        dry = self.promote("--rules", "2,4", "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["promotions"][0]["handles"],
                         ["ADR-0007/edit", "ADR-0007/add2"])
        self.assertEqual(self.repo.record_path(7).read_bytes(), before)      # nothing written
        done = self.promote("--rules", "2,4")
        self.assertEqual(done.returncode, 0, done.stderr)
        promos = self.record()["promotions"]
        self.assertEqual(len(promos), 1)
        self.assertEqual(promos[0]["handles"], ["ADR-0007/edit", "ADR-0007/add2"])
        self.assertEqual(promos[0]["instruction"], "promote ADR-0007: rules 2")
        self.assertEqual(promos[0]["date"], "2026-10-12")
        self.assertFalse(promos[0]["body"])

    def test_promote_all_selects_every_unpromoted_in_run_rule(self):
        self.assertEqual(self.promote("--rules", "2").returncode, 0)
        done = self.promote("--rules", "all")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.record()["promotions"][1]["handles"],
                         ["ADR-0007/add", "ADR-0007/add2"])      # rule 1 has no in-run text

    def test_promote_refusals_each_name_their_cause(self):
        before = self.repo.record_path(7).read_bytes()
        cases = [
            (("--rules", "9"), "out of range"),
            (("--rules", "0"), "out of range"),
            (("--rules", "1"), "no in-run text"),
            (("--rules", "2,2"), "twice"),
            (("--rules", "x"), "rule numbers"),
        ]
        for args, needle in cases:
            with self.subTest(args=args):
                done = self.promote(*args)
                self.assertEqual(done.returncode, 2, done.stdout)
                self.assertIn(needle, done.stderr)
        self.assertEqual(self.repo.record_path(7).read_bytes(), before)
        # positive control: a valid selection on the same record succeeds
        self.assertEqual(self.promote("--rules", "3").returncode, 0)
        again = self.promote("--rules", "3")
        self.assertEqual(again.returncode, 2)
        self.assertIn("already promoted", again.stderr)

    def test_empty_selection_refuses_without_body_and_succeeds_with_it(self):
        self.assertEqual(self.promote("--rules", "all").returncode, 0)
        empty = self.promote("--rules", "all")
        self.assertEqual(empty.returncode, 2)
        self.assertIn("nothing to promote", empty.stderr)
        body = self.promote("--rules", "all", "--body")
        self.assertEqual(body.returncode, 0, body.stderr)
        last = self.record()["promotions"][-1]
        self.assertEqual((last["handles"], last["body"]), ([], True))

    def test_promote_refuses_a_missing_record_and_a_bad_date_or_instruction(self):
        absent = self.repo.cli("promote", "--adr", "ADR-0042", "--rules", "all", "--instruction", "x",
                               "--date", "2026-10-12")
        self.assertEqual(absent.returncode, 2)
        self.assertIn("no provenance record", absent.stderr)
        bad_date = self.repo.cli("promote", "--adr", "ADR-0007", "--rules", "2", "--instruction", "x",
                                 "--date", "12-10-2026")
        self.assertEqual(bad_date.returncode, 2)
        self.assertIn("YYYY-MM-DD", bad_date.stderr)
        blank = self.repo.cli("promote", "--adr", "ADR-0007", "--rules", "2", "--instruction", "  ",
                              "--date", "2026-10-12")
        self.assertEqual(blank.returncode, 2)
        self.assertIn("instruction", blank.stderr)

    def test_open_lists_unpromoted_text_and_drops_it_after_promotion(self):
        listed = self.repo.cli("open")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        entries = json.loads(listed.stdout)["open"]
        self.assertEqual([e["adr"] for e in entries], ["ADR-0007"])
        self.assertEqual([r["number"] for r in entries[0]["guidance"]], [3, 4])
        self.assertEqual([r["number"] for r in entries[0]["edited"]], [2])
        self.assertEqual(self.promote("--rules", "all").returncode, 0)
        after = self.repo.cli("open")
        self.assertEqual(after.returncode, 0)
        self.assertEqual(json.loads(after.stdout), {"open": []})

    def test_open_with_a_malformed_record_exits_one(self):
        self.repo.record_path(7).write_text("schema: '1'\n")
        done = self.repo.cli("open")
        self.assertEqual(done.returncode, 1)
        self.assertTrue(json.loads(done.stdout)["validation_errors"])

    def test_open_with_no_records_is_clean(self):
        empty = Repo(self)
        done = empty.cli("open")
        self.assertEqual((done.returncode, json.loads(done.stdout)), (0, {"open": []}))


def _entry(slug: str, **fields) -> dict:
    return {"slug": slug, "domain": "tests", "rule": f"Rule {slug}.", "scope": "crux/",
            "provenance": "authored", **fields}


def entries_repo(tc: unittest.TestCase, base: list[dict], run: list[dict]):
    """ADR-0007 holds the `base` governs entries at base_commit and the `run` entries after."""
    repo = Repo(tc)
    path = repo.adrs / "ADR-0007-decision.md"
    path.write_text(adr_entries_text(7, base, status="Proposed"))
    base_commit = repo.commit("base")
    path.write_text(adr_entries_text(7, run))
    repo.commit("in-run edit")
    return repo, repo.snapshot(base_commit)


def _open_handles(repo: Repo, kind: str) -> list[str]:
    done = repo.cli("open")
    assert done.returncode == 0, done.stderr
    return [row["handle"] for entry in json.loads(done.stdout)["open"] for row in entry.get(kind, [])]


class WholeEntryClassificationTests(unittest.TestCase):
    """An in-run edit to any governs field but `handle` and `provenance` is in-run text: the
    rule is listed as edited and the owner can promote it (ADR-0151 decision 1, text level)."""

    def _promotable_edit(self, **run_fields):
        repo, run = entries_repo(self, [_entry("a"), _entry("b")],
                                 [_entry("a", **run_fields), _entry("b")])
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(_open_handles(repo, "edited"), ["ADR-0007/a"])
        promoted = repo.cli("promote", "--adr", "ADR-0007", "--rules", "1", "--instruction",
                            "promote ADR-0007: rules 1", "--date", "2026-10-12")
        self.assertEqual(promoted.returncode, 0, promoted.stderr)
        self.assertEqual(_open_handles(repo, "edited"), [])
        return repo

    def test_a_scope_only_edit_is_in_run_text(self):
        self._promotable_edit(scope="crux/, tools/")

    def test_a_domain_only_edit_is_in_run_text(self):
        self._promotable_edit(domain="other-domain")

    def test_an_anchor_only_edit_is_in_run_text(self):
        self._promotable_edit(anchor="Body.")

    def test_control_an_unchanged_entry_and_a_provenance_only_edit_carry_no_in_run_text(self):
        repo, run = entries_repo(self, [_entry("a"), _entry("b")],
                                 [_entry("a"), _entry("b", provenance="reconstructed")])
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run).returncode, 0)
        self.assertEqual(_open_handles(repo, "edited"), [])
        for number in ("1", "2"):
            refused = repo.cli("promote", "--adr", "ADR-0007", "--rules", number, "--instruction",
                               "x", "--date", "2026-10-12")
            self.assertEqual(refused.returncode, 2)
            self.assertIn("no in-run text", refused.stderr)


class RemovedInRunTests(unittest.TestCase):
    """A rule that stood at base_commit and was deleted in the run stays binding at its base
    wording until the owner promotes the deletion: `open` lists it, numbered after the rules,
    and `promote` addresses it by that number (ADR-0151 decisions 1, 2 and 4)."""

    def setUp(self):
        self.repo, run = entries_repo(self, [_entry("a"), _entry("drop", rule="Dropped wording.")],
                                      [_entry("a"), _entry("add")])
        done = self.repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(done.returncode, 0, done.stderr)
        # numbering: 1 a (no in-run text), 2 add (guidance), 3 drop (removed in-run)

    def promote(self, rules: str):
        return self.repo.cli("promote", "--adr", "ADR-0007", "--rules", rules, "--instruction",
                             f"promote ADR-0007: rules {rules}", "--date", "2026-10-12")

    def test_open_lists_the_deletion_numbered_after_the_rules(self):
        entry = json.loads(self.repo.cli("open").stdout)["open"][0]
        removed = entry["removed"]
        self.assertEqual([(r["number"], r["handle"]) for r in removed], [(3, "ADR-0007/drop")])
        self.assertEqual(removed[0]["base"]["rule"], "Dropped wording.")

    def test_promote_addresses_the_deletion_by_its_number(self):
        done = self.promote("3")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(_open_handles(self.repo, "removed"), [])
        self.assertEqual(_open_handles(self.repo, "guidance"), ["ADR-0007/add"])
        again = self.promote("3")
        self.assertEqual(again.returncode, 2)
        self.assertIn("already promoted", again.stderr)

    def test_promote_all_covers_the_deletion(self):
        self.assertEqual(self.promote("all").returncode, 0)
        import yaml
        record = yaml.safe_load(self.repo.record_path(7).read_text())
        self.assertEqual(record["promotions"][-1]["handles"], ["ADR-0007/add", "ADR-0007/drop"])
        self.assertEqual(json.loads(self.repo.cli("open").stdout), {"open": []})

    def test_control_a_number_past_the_deletions_is_out_of_range(self):
        refused = self.promote("4")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("out of range", refused.stderr)


class RecordScopeTests(unittest.TestCase):
    """[SECURITY:S3] `record` writes a record only inside the scope decided for provenance
    records (ADR-0151 rule 4, decision 5): for an ADR accepted inside the run that names it,
    while that run is in progress. Each refusal writes nothing and is paired with the passing
    fixture. A dry-run writes nothing, so it inspects any Accepted ADR and checks no scope."""

    def _repo(self, **snapshot):
        repo = Repo(self)
        repo.write_adr(7, {"a": "One."}, status="Proposed")
        base = repo.commit("base")
        repo.write_adr(7, {"a": "One.", "b": "Two."})
        repo.commit("in-run edit")
        return repo, repo.snapshot(base, **snapshot)

    def _refused(self, repo: Repo, run: str, needle: str, *extra: str):
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run, *extra)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn(needle, done.stderr)
        self.assertFalse(repo.record_path(7).exists(), "nothing written")
        dry = repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run", *extra)
        self.assertEqual(dry.returncode, 0, dry.stderr)

    def test_control_an_in_progress_run_that_names_the_adr_writes(self):
        repo, run = self._repo()
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(repo.record_path(7).is_file())

    def test_a_run_that_is_no_longer_in_progress_refuses(self):
        repo, run = self._repo(status="completed")
        self._refused(repo, run, "is 'completed', not in_progress")

    def test_an_adr_accepted_before_its_run_started_refuses(self):
        repo, run = self._repo(started="2026-10-14T09:00:00Z")
        self._refused(repo, run, "before its run started")

    def test_same_day_and_one_day_of_timezone_slack_are_inside_the_run(self):
        for started in ("2026-10-12T23:59:00Z", "2026-10-13T01:00:00Z"):
            with self.subTest(started=started):
                repo, run = self._repo(started=started)
                done = repo.cli("record", "--adr", "ADR-0007", "--run", run)
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_run_that_names_no_file_of_the_adr_refuses(self):
        repo, run = self._repo(artifacts=("docs/adrs/ADR-0001-other.md",))
        self._refused(repo, run, "names no ADR-0007 file")

    def test_an_adr_with_no_accepted_date_refuses(self):
        repo, run = self._repo()
        path = repo.adrs / "ADR-0007-decision.md"
        path.write_text(path.read_text().replace(f"accepted_date: {ACCEPTED_ON}\n", ""))
        self._refused(repo, run, "carries no readable accepted_date")

    # The run names the ADR by the module-close gate's own predicate: a prompt artifact or a
    # run-work witness entry whose path, resolved as the council gate resolves an artifact, is a
    # file of the ADR under the tree's adrs/ or adrs/archive/.

    def _writes(self, repo: Repo, run: str):
        done = repo.cli("record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(repo.record_path(7).is_file())

    def test_an_artifact_under_the_archive_names_the_adr(self):
        self._writes(*self._repo(artifacts=("docs/adrs/archive/ADR-0007-decision.md",)))

    def test_an_artifact_spelled_with_a_leading_dot_slash_names_the_adr(self):
        self._writes(*self._repo(artifacts=("./docs/adrs/ADR-0007-decision.md",)))

    def test_an_artifact_in_another_directory_names_nothing(self):
        for artifact in ("other/ADR-0007-decision.md", "vendor/adrs/ADR-0007-decision.md"):
            with self.subTest(artifact=artifact):
                repo, run = self._repo(artifacts=(artifact,))
                self._refused(repo, run, "names no ADR-0007 file")

    def test_a_run_work_witness_entry_names_the_adr(self):
        repo, run = self._repo(artifacts=())
        self._refused(repo, run, "names no ADR-0007 file")       # control: no artifact, no witness
        repo.witness(["docs/adrs/ADR-0007-decision.md"])
        self._writes(repo, run)

    def test_a_witness_entry_outside_the_adrs_directory_names_nothing(self):
        repo, run = self._repo(artifacts=())
        repo.witness(["other/ADR-0007-decision.md", "docs/adrs/index.md"])
        self._refused(repo, run, "names no ADR-0007 file")

    # [SECURITY:S3] The scope reads the snapshot as committed, so editing the working-tree
    # snapshot cannot widen it.

    def _tampered(self, committed: dict, working: dict, needle: str):
        repo, run = self._repo(**committed)
        (repo.root / run).write_text(run_yaml(_base_of(repo, run), **working))
        self.assertNotEqual(_git(repo.root, "status", "--porcelain", "--", run), "", "working tree differs")
        self._refused(repo, run, needle)

    def test_a_working_tree_status_edit_does_not_reopen_an_ended_run(self):
        self._tampered({"status": "completed"}, {}, "is 'completed', not in_progress")

    def test_a_working_tree_artifact_edit_does_not_name_the_adr(self):
        self._tampered({"artifacts": ("docs/adrs/ADR-0001-other.md",)}, {}, "names no ADR-0007 file")

    def test_a_working_tree_start_date_edit_does_not_move_the_run(self):
        self._tampered({"started": "2026-10-14T09:00:00Z"}, {}, "before its run started")

    def test_an_uncommitted_snapshot_refuses_a_write(self):
        repo = Repo(self)
        repo.write_adr(7, {"a": "One."}, status="Proposed")
        base = repo.commit("base")
        repo.write_adr(7, {"a": "One.", "b": "Two."})
        repo.commit("in-run edit")
        run = "docs/promptbooks/runs/PB-0001-x/run-RUN-001.yaml"
        (repo.root / run).parent.mkdir(parents=True)
        (repo.root / run).write_text(run_yaml(base))
        self._refused(repo, run, "has no committed version")
        repo.commit("snapshot")
        self._writes(repo, run)                                   # control: once committed it writes


class RetroactiveRecordTests(unittest.TestCase):
    """[SECURITY:S3] A record for an ADR whose accepting run has ended is written only on an
    owner-promoted rule whose wording names that ADR (`--authorized-by`): the shape of ADR-0150's
    record, which waits for the owner's promotion of the decision that grants it."""

    def setUp(self):
        self.repo = Repo(self)
        self.repo.write_adr(7, {"a": "One."}, status="Proposed")
        base = self.repo.commit("base")
        self.repo.write_adr(7, {"a": "One.", "b": "Two."})
        self.write_9(amends=["ADR-0007"])
        self.repo.commit("both accepted")
        self.done_run = self.repo.snapshot(base, status="completed")
        self.live_run = self.repo.snapshot(base, book="PB-0002",
                                           artifacts=("docs/adrs/ADR-0009-decision.md",))
        recorded = self.repo.cli("record", "--adr", "ADR-0009", "--run", self.live_run)
        self.assertEqual(recorded.returncode, 0, recorded.stderr)

    def write_9(self, amends: list[str] | None):
        (self.repo.adrs / "ADR-0009-decision.md").write_text(adr_entries_text(9, [
            _entry("grants", rule="ADR-0007 is the one earlier ADR that receives a provenance record."),
            _entry("other", rule="Names no earlier decision.")], amends=amends))

    def record_7(self, *extra: str, run: str | None = None):
        return self.repo.cli("record", "--adr", "ADR-0007", "--run", run or self.done_run, *extra)

    def promote_9(self, rules: str):
        done = self.repo.cli("promote", "--adr", "ADR-0009", "--rules", rules, "--instruction",
                             f"promote ADR-0009: rules {rules}", "--date", "2026-10-13")
        self.assertEqual(done.returncode, 0, done.stderr)

    def assert_refused(self, done, needle: str):
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn(needle, done.stderr)
        self.assertFalse(self.repo.record_path(7).exists(), "nothing written")

    def test_without_authorization_an_ended_run_refuses(self):
        self.assert_refused(self.record_7(), "not in_progress")

    def test_an_unpromoted_authorizing_rule_refuses_and_its_promotion_admits(self):
        self.assert_refused(self.record_7("--authorized-by", "ADR-0009/grants"), "has not promoted")
        self.promote_9("1")
        done = self.record_7("--authorized-by", "ADR-0009/grants")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(self.repo.record_path(7).is_file())

    def test_a_promoted_rule_that_does_not_name_the_adr_refuses(self):
        self.promote_9("2")
        self.assert_refused(self.record_7("--authorized-by", "ADR-0009/other"), "does not name ADR-0007")

    def test_an_authorizing_adr_that_does_not_amend_the_target_refuses(self):
        self.promote_9("1")
        for amends in (None, ["ADR-0008"]):
            with self.subTest(amends=amends):
                self.write_9(amends=amends)
                self.assert_refused(self.record_7("--authorized-by", "ADR-0009/grants"),
                                    "does not list ADR-0007 in amends")
        self.write_9(amends=["ADR-0008", "ADR-0007"])
        done = self.record_7("--authorized-by", "ADR-0009/grants")     # control
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_authorization_lifts_only_the_in_progress_requirement(self):
        self.promote_9("1")
        base = _base_of(self.repo, self.done_run)
        no_file = self.repo.snapshot(base, book="PB-0003", status="completed",
                                     artifacts=("docs/adrs/ADR-0001-other.md",))
        self.assert_refused(self.record_7("--authorized-by", "ADR-0009/grants", run=no_file),
                            "names no ADR-0007 file")
        too_late = self.repo.snapshot(base, book="PB-0004", status="completed",
                                      started="2026-10-14T09:00:00Z")
        self.assert_refused(self.record_7("--authorized-by", "ADR-0009/grants", run=too_late),
                            "before its run started")
        done = self.record_7("--authorized-by", "ADR-0009/grants")     # control: the ended run that names it
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_an_authorizing_handle_with_no_record_or_rule_refuses(self):
        self.assert_refused(self.record_7("--authorized-by", "ADR-0042/grants"), "has no provenance record")
        self.assert_refused(self.record_7("--authorized-by", "ADR-0009/never"), "is not a rule")
        self.assert_refused(self.record_7("--authorized-by", "not-a-handle"), "--authorized-by must be")


class SecretAndInputPathTests(unittest.TestCase):
    """[SECURITY:S2] `promote` never writes or prints a credential-shaped value, and `record
    --run` refuses a secret location and echoes no snapshot text on a parse failure."""

    KEY = "AK" + "IA" + "Q" * 16                 # a synthetic aws-access-key-id shape

    def setUp(self):
        self.repo, self.run, _ = in_run_repo(self, {"a": "Old."}, {"a": "New."})
        self.assertEqual(self.repo.cli("record", "--adr", "ADR-0007", "--run", self.run).returncode, 0)

    def promote(self, instruction: str, *extra: str):
        return self.repo.cli("promote", "--adr", "ADR-0007", "--rules", "1", "--instruction",
                             instruction, "--date", "2026-10-12", *extra)

    def test_a_key_shaped_instruction_refuses_naming_the_field_never_the_value(self):
        before = self.repo.record_path(7).read_bytes()
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                done = self.promote(f"promote ADR-0007: rules 1 {self.KEY}", *extra)
                self.assertEqual(done.returncode, 2, done.stdout)
                self.assertIn("promotions[0].instruction", done.stderr)
                self.assertNotIn(self.KEY, done.stderr + done.stdout)
        self.assertEqual(self.repo.record_path(7).read_bytes(), before)
        # positive control: the same words without the key shape are written
        self.assertEqual(self.promote("promote ADR-0007: rules 1").returncode, 0)

    def test_record_refuses_a_run_snapshot_in_a_secret_location(self):
        env = self.repo.root / "docs" / ".env"
        env.write_text((self.repo.root / self.run).read_text())
        refused = self.repo.cli("record", "--adr", "ADR-0007", "--run", "docs/.env", "--dry-run")
        self.assertEqual(refused.returncode, 2, refused.stdout)
        self.assertIn("env-file", refused.stderr)
        done = self.repo.cli("record", "--adr", "ADR-0007", "--run", self.run, "--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)            # positive control

    def test_record_refuses_a_key_shaped_governs_value_naming_the_field_never_the_value(self):
        repo, run, _ = in_run_repo(self, {"keep": "Keep.", "gone": f"Rotate {self.KEY} now."},
                                   {"keep": "Keep."})
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                done = repo.cli("record", "--adr", "ADR-0007", "--run", run, *extra)
                self.assertEqual(done.returncode, 2, done.stdout)
                self.assertIn("removed_in_run[0].base.rule", done.stderr)
                self.assertNotIn(self.KEY, done.stderr + done.stdout)
                self.assertFalse(repo.record_path(7).exists(), "nothing written")
        # positive control: the same shape without the key is written
        clean, clean_run, _ = in_run_repo(self, {"keep": "Keep.", "gone": "Rotate it now."}, {"keep": "Keep."})
        self.assertEqual(clean.cli("record", "--adr", "ADR-0007", "--run", clean_run).returncode, 0)

    def test_a_snapshot_that_does_not_parse_is_reported_by_type_and_line_only(self):
        bad = self.repo.root / "docs" / "promptbooks" / "runs" / "PB-0001-x" / "broken.yaml"
        bad.write_text(f"base_commit: [unclosed {self.KEY}\n")
        refused = self.repo.cli("record", "--adr", "ADR-0007", "--run", str(bad.relative_to(self.repo.root)),
                                "--dry-run")
        self.assertEqual(refused.returncode, 2)
        self.assertIn("line", refused.stderr)
        self.assertNotIn(self.KEY, refused.stderr)
        self.assertNotIn("unclosed", refused.stderr)


class SnapshotReadRefusalTests(unittest.TestCase):
    """`record --run` refuses a snapshot outside the repository, one that is not a file, one
    that is not UTF-8 and one that is not a mapping; each exits 2 and the control reads."""

    def setUp(self):
        self.repo, self.run, _ = in_run_repo(self, {"a": "Old."}, {"a": "New."})

    def refused(self, run: str, needle: str):
        done = self.repo.cli("record", "--adr", "ADR-0007", "--run", run, "--dry-run")
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertIn(needle, done.stderr)

    def test_each_refusal_names_its_cause(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / "run.yaml").write_text((self.repo.root / self.run).read_text())
        self.refused(str(outside / "run.yaml"), "outside-repo")
        self.refused("docs", "missing")                                  # a directory is not a file
        runs = self.repo.root / "docs" / "promptbooks" / "runs" / "PB-0001-x"
        (runs / "latin1.yaml").write_bytes(b"status: \xe9t\xe9\n")
        self.refused(f"{runs.relative_to(self.repo.root)}/latin1.yaml", "is not UTF-8")
        (runs / "list.yaml").write_text("- one\n- two\n")
        self.refused(f"{runs.relative_to(self.repo.root)}/list.yaml", "is not a mapping")
        done = self.repo.cli("record", "--adr", "ADR-0007", "--run", self.run, "--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)               # control


class RecordFileModeTests(unittest.TestCase):
    """A record lands 0644, like the sibling projection writers, on its first write and on a
    promotion's replacement."""

    def test_record_and_promote_write_mode_0644(self):
        import stat
        repo, run, _ = in_run_repo(self, {"a": "Old."}, {"a": "New."})
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run).returncode, 0)
        self.assertEqual(stat.S_IMODE(repo.record_path(7).stat().st_mode), 0o644)
        done = repo.cli("promote", "--adr", "ADR-0007", "--rules", "1", "--instruction",
                        "promote ADR-0007: rules 1", "--date", "2026-10-12")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(stat.S_IMODE(repo.record_path(7).stat().st_mode), 0o644)


class RulesArgumentTests(unittest.TestCase):
    """`--rules` takes ASCII digits joined by commas, or `all`; `int()` alone would also admit
    other decimal digits, a sign and surrounding space."""

    def test_only_ascii_digit_lists_select(self):
        repo, run, _ = in_run_repo(self, {"a": "Old.", "b": "Old b."}, {"a": "New.", "b": "New b."})
        self.assertEqual(repo.cli("record", "--adr", "ADR-0007", "--run", run).returncode, 0)
        for spec in ("\u0661", "+1", " 1", "1, 2", "1,", ""):
            with self.subTest(spec=spec):
                done = repo.cli("promote", "--adr", "ADR-0007", "--rules", spec, "--instruction",
                                "x", "--date", "2026-10-12", "--dry-run")
                self.assertEqual(done.returncode, 2, done.stdout)
                self.assertIn("--rules takes rule numbers", done.stderr)
        done = repo.cli("promote", "--adr", "ADR-0007", "--rules", "1,2", "--instruction",
                        "promote ADR-0007: rules 1, 2", "--date", "2026-10-12", "--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)                # control


class WriterFileGuardTests(unittest.TestCase):
    """[SECURITY:S5] The record writer never writes through a planted link, at its temporary
    name or at the record path. The writer runs in-process so `os.getpid()` is its pid, which is
    the name a predictable temporary file would have used."""

    def _outside(self) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        victim = directory / "victim.txt"
        victim.write_text("victim\n")
        return victim

    def _plant_temporary_link(self, repo: Repo, name: str) -> tuple[Path, Path]:
        victim = self._outside()
        provenance = repo.adrs / "provenance"
        provenance.mkdir(exist_ok=True)
        link = provenance / f".{name}.tmp-{os.getpid()}"
        link.symlink_to(victim)
        return victim, link

    def _main(self, repo: Repo, *args: str) -> tuple[int, str, str]:
        cli = _load()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main([*args, "--repo-root", str(repo.root)])
        return code, out.getvalue(), err.getvalue()

    def test_positive_control_a_plain_write_through_the_planted_link_reaches_outside(self):
        repo, _run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        victim, link = self._plant_temporary_link(repo, "ADR-0007.yaml")
        link.write_text("redirected\n")          # what `Path.write_text` on that name does
        self.assertEqual(victim.read_text(), "redirected\n")

    def test_record_never_writes_through_a_link_planted_at_a_temporary_name(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        victim, link = self._plant_temporary_link(repo, "ADR-0007.yaml")
        code, _out, err = self._main(repo, "record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(victim.read_text(), "victim\n")
        record = repo.record_path(7)
        self.assertFalse(record.is_symlink())
        self.assertTrue(record.is_file())
        self.assertNotEqual(os.stat(record).st_ino, os.stat(victim).st_ino)
        self.assertEqual(code, 0, err)
        self.assertTrue(link.is_symlink())          # someone else's file is left alone

    def test_promote_never_writes_through_a_link_planted_at_a_temporary_name(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        self.assertEqual(self._main(repo, "record", "--adr", "ADR-0007", "--run", run)[0], 0)
        victim, link = self._plant_temporary_link(repo, "ADR-0007.yaml")
        code, _out, err = self._main(repo, "promote", "--adr", "ADR-0007", "--rules", "2",
                                     "--instruction", "promote ADR-0007: rules 2",
                                     "--date", "2026-10-12")
        self.assertEqual(victim.read_text(), "victim\n")
        record = repo.record_path(7)
        self.assertFalse(record.is_symlink())
        self.assertEqual(code, 0, err)
        self.assertIn("promote ADR-0007: rules 2", record.read_text())
        self.assertTrue(link.is_symlink())

    def test_record_refuses_a_link_at_the_record_path_and_writes_nothing_outside(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        victim = self._outside()
        victim.unlink()                            # a dangling link: the write would create it
        (repo.adrs / "provenance").mkdir()
        repo.record_path(7).symlink_to(victim)
        code, _out, err = self._main(repo, "record", "--adr", "ADR-0007", "--run", run)
        self.assertEqual(code, 2)
        self.assertIn("symlink", err)
        self.assertFalse(victim.exists())
        repo.record_path(7).unlink()               # positive control: no link, the write lands
        self.assertEqual(self._main(repo, "record", "--adr", "ADR-0007", "--run", run)[0], 0)

    def test_promote_refuses_a_link_at_the_record_path_and_leaves_its_target_unchanged(self):
        repo, run, _ = in_run_repo(self, {"a": "One."}, {"a": "One.", "b": "Two."})
        self.assertEqual(self._main(repo, "record", "--adr", "ADR-0007", "--run", run)[0], 0)
        victim = self._outside()
        victim.write_text(repo.record_path(7).read_text())
        before = victim.read_bytes()
        repo.record_path(7).unlink()
        repo.record_path(7).symlink_to(victim)
        code, _out, err = self._main(repo, "promote", "--adr", "ADR-0007", "--rules", "2",
                                     "--instruction", "promote ADR-0007: rules 2",
                                     "--date", "2026-10-12")
        self.assertEqual(code, 2)
        self.assertIn("no provenance record", err)
        self.assertEqual(victim.read_bytes(), before)
        self.assertTrue(repo.record_path(7).is_symlink())


class LiveAdr0150Tests(unittest.TestCase):
    SNAPSHOT = (f"{TREE}/promptbooks/runs/PB-0149-ship-the-crux-mods-plugin-with-a-run-dashboard/"
                "run-RUN-001.yaml")
    SIX = ["mods-gate-refuses-what-it-cannot-check", "mods-start-only-the-fixed-launcher",
           "launch-values-have-fixed-sources", "reader-json-mode-is-contained",
           "enforcing-entries-name-their-counterpart", "mods-add-no-harness-specific-stop"]

    def test_adr_0150_dry_run_yields_six_guidance_and_twelve_binding_rules(self):
        require_dev_surface(self, REPO_ROOT / self.SNAPSHOT, "PB-0149 run snapshot")
        probe = subprocess.run(["git", "-C", str(REPO_ROOT), "cat-file", "-e",
                                f"{ACCEPTING_RUN_BASE}^{{commit}}"], capture_output=True)
        if probe.returncode != 0:
            self.skipTest("the run's base_commit is not in this clone")
        provenance = REPO_ROOT / TREE / "adrs" / "provenance"
        existed = (provenance / "ADR-0150.yaml").exists()
        done = subprocess.run([sys.executable, str(CLI), "record", "--adr", "ADR-0150", "--run",
                               self.SNAPSHOT, "--dry-run", "--repo-root", str(REPO_ROOT)],
                              capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        record = json.loads(done.stdout)
        guidance = [r["handle"].split("/")[1] for r in record["rules"] if r["standing"] == "guidance"]
        binding = [r for r in record["rules"] if r["standing"] == "binding"]
        self.assertEqual(sorted(guidance), sorted(self.SIX))     # governs order, not listing order
        self.assertEqual(len(binding), 12)
        self.assertEqual(record["base_commit"], ACCEPTING_RUN_BASE)
        self.assertEqual((provenance / "ADR-0150.yaml").exists(), existed)   # nothing written


if __name__ == "__main__":
    unittest.main()
