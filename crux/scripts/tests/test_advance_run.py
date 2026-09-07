"""Issue 3: advance-run.py advances a .yaml run snapshot and preserves the
run-level trailing fields (notes / pr_draft / summary) across every advance.

Imports the vendored `advance-run.py` by path (it's a hyphenated script, so
importlib rather than a normal import). Runs under the uv lane (PyYAML).
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ADVANCE = REPO_ROOT / "crux" / "scripts" / "advance-run.py"
VALIDATE = REPO_ROOT / "crux" / "scripts" / "validate-promptbook.py"

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

if HAVE_YAML and ADVANCE.is_file():
    _spec = importlib.util.spec_from_file_location("advance_run", ADVANCE)
    _ar = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_ar)
    _vspec = importlib.util.spec_from_file_location("_vp_for_advance", VALIDATE)
    _vp = importlib.util.module_from_spec(_vspec)
    _vspec.loader.exec_module(_vp)
    HAVE = True
else:
    HAVE = False


def _cli(args):
    """Invoke advance-run.py as a subprocess (the real CLI surface)."""
    return subprocess.run([sys.executable, str(ADVANCE), *args],
                          capture_output=True, text=True)


def _git(cwd: Path, *args: str) -> None:
    """Run git with the ambient config neutralized, so a result never depends on
    the developer's ~/.gitconfig."""
    env = dict(os.environ)
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    })
    subprocess.run(["git", "-C", str(cwd), *args], check=True,
                   capture_output=True, text=True, env=env)


def _run_doc(n_prompts=3):
    return {
        "format_version": "1",
        "run_id": "RUN-001",
        "book_id": "PB-9001",
        "book_content_hash": "sha256:" + "0" * 64,
        "started_at": "2026-07-22T00:00:00Z",
        "completed_at": None,
        "status": "in_progress",
        "current_prompt": 1,
        "prompts": [
            {"n": i, "title": f"P{i}", "state": ("running" if i == 1 else "pending"),
             "started": None, "completed": None, "result": "", "artifacts": []}
            for i in range(1, n_prompts + 1)
        ],
        "notes": "IMPORTANT NOTES", "pr_draft": "PR DRAFT BODY", "summary": "",
    }


@unittest.skipUnless(HAVE, "advance-run.py or PyYAML unavailable")
class AdvanceRunTests(unittest.TestCase):
    def test_advance_moves_pointer_and_records(self):
        r = _ar.advance(_run_doc(), "done", "did the thing", ["docs/x.md"])
        p1 = r["prompts"][0]
        self.assertEqual(p1["state"], "done")
        self.assertEqual(p1["result"], "did the thing")
        self.assertEqual(p1["artifacts"], ["docs/x.md"])
        self.assertIsNotNone(p1["completed"])
        self.assertEqual(r["current_prompt"], 2)
        self.assertEqual(r["prompts"][1]["state"], "running")

    def test_trailing_fields_preserved(self):
        # THE Issue-3 hazard: notes / pr_draft / summary must survive.
        r = _ar.advance(_run_doc(), "done", "", [])
        self.assertEqual(r["notes"], "IMPORTANT NOTES")
        self.assertEqual(r["pr_draft"], "PR DRAFT BODY")
        self.assertIn("summary", r)

    def test_dump_reload_preserves_trailing_fields(self):
        # The REAL Issue-3 hazard is the re-emit dropping keys — exercise
        # _dump() -> reparse, not just the in-memory mutation.
        import yaml
        r = _ar.advance(_run_doc(), "done", "x", [])
        reloaded = yaml.safe_load(_ar._dump(r))
        self.assertEqual(reloaded["notes"], "IMPORTANT NOTES")
        self.assertEqual(reloaded["pr_draft"], "PR DRAFT BODY")
        self.assertIn("summary", reloaded)

    def test_dump_reload_defaults_absent_trailing_fields(self):
        import yaml
        bare = _run_doc()
        for k in ("notes", "pr_draft", "summary"):
            bare.pop(k, None)
        r = _ar.advance(bare, "done", "", [])
        reloaded = yaml.safe_load(_ar._dump(r))
        self.assertEqual(reloaded["notes"], "")
        self.assertEqual(reloaded["pr_draft"], "")
        self.assertEqual(reloaded["summary"], "")

    def test_last_prompt_completes_run(self):
        doc = _run_doc(1)
        r = _ar.advance(doc, "done", "", [])
        self.assertEqual(r["status"], "completed")
        self.assertIsNone(r["current_prompt"])
        self.assertIsNotNone(r["completed_at"])

    def test_blocked_writes_no_per_prompt_flag(self):
        # ADR-0077 clause 5(b) deleted `blocked_confirmed`. `blocked` now means
        # blocked, full stop; nothing extra is written on the element, and
        # run.schema.json (additionalProperties: false) would reject it if it were.
        r = _ar.advance(_run_doc(), "blocked", "stuck", [])
        self.assertEqual(r["prompts"][0]["state"], "blocked")
        self.assertNotIn("blocked_confirmed", r["prompts"][0])

    def test_blocked_confirmed_flag_is_gone_from_the_cli(self):
        proc = _cli(["--help"])
        self.assertNotIn("--blocked-confirmed", proc.stdout)

    def test_malformed_snapshot_fails_cleanly(self):
        # A .yaml with format_version but no prompts list -> clean _fail (SystemExit 1),
        # not an uncaught KeyError.
        with self.assertRaises(SystemExit) as cm:
            _ar.advance({"format_version": "1", "current_prompt": 1}, "done", "", [])
        self.assertEqual(cm.exception.code, 1)

    def test_prior_elements_untouched(self):
        doc = _run_doc(3)
        _ar.advance(doc, "done", "one", [])          # p1 -> done, p2 running
        r = _ar.advance(doc, "skipped", "two", [])   # p2 -> skipped, p3 running
        self.assertEqual(r["prompts"][0]["state"], "done")     # p1 unchanged
        self.assertEqual(r["prompts"][0]["result"], "one")
        self.assertEqual(r["prompts"][1]["state"], "skipped")
        self.assertEqual(r["current_prompt"], 3)


@unittest.skipUnless(HAVE, "advance-run.py or PyYAML unavailable")
class AbandonRunTests(unittest.TestCase):
    """ADR-0077 clause 5(b): abandonment is a RUN-level act. `abandonment.kind:
    deliberate` is the archive-eligibility signal that replaced the per-prompt
    `blocked_confirmed` flag."""

    def test_abandon_sets_run_level_record(self):
        r = _ar.abandon(_run_doc(), "the approach was wrong")
        self.assertEqual(r["status"], "abandoned")
        self.assertIsNone(r["current_prompt"])
        self.assertIsNotNone(r["completed_at"])
        self.assertEqual(r["abandonment"]["kind"], "deliberate")
        self.assertEqual(r["abandonment"]["reason"], "the approach was wrong")
        self.assertTrue(r["abandonment"]["at"])

    def test_abandon_leaves_prompt_states_untouched(self):
        # The non-terminal prompt left behind IS the evidence the run was
        # abandoned mid-flight; rewriting it would erase that.
        doc = _run_doc(3)
        r = _ar.abandon(doc, "stopping here")
        self.assertEqual(r["prompts"][0]["state"], "running")
        self.assertEqual(r["prompts"][1]["state"], "pending")
        self.assertEqual(r["prompts"][2]["state"], "pending")

    def test_abandon_preserves_trailing_fields_through_a_dump_reload(self):
        import yaml
        r = _ar.abandon(_run_doc(), "stopping")
        reloaded = yaml.safe_load(_ar._dump(r))
        self.assertEqual(reloaded["notes"], "IMPORTANT NOTES")
        self.assertEqual(reloaded["pr_draft"], "PR DRAFT BODY")
        self.assertEqual(reloaded["abandonment"]["kind"], "deliberate")

    def test_abandon_requires_a_reason(self):
        for reason in ("", "   "):
            with self.assertRaises(SystemExit) as cm:
                _ar.abandon(_run_doc(), reason)
            self.assertEqual(cm.exception.code, 1)

    def test_abandon_refuses_to_retrofit_onto_a_terminal_run(self):
        for status in ("completed", "abandoned"):
            doc = _run_doc()
            doc["status"] = status
            with self.assertRaises(SystemExit) as cm:
                _ar.abandon(doc, "too late")
            self.assertEqual(cm.exception.code, 1)

    def test_abandon_refuses_when_a_record_already_exists(self):
        doc = _run_doc()
        doc["abandonment"] = {"kind": "superseded", "at": "2026-01-01T00:00:00Z", "reason": "x"}
        with self.assertRaises(SystemExit) as cm:
            _ar.abandon(doc, "again")
        self.assertEqual(cm.exception.code, 1)

    def test_abandoned_run_validates_against_the_run_schema(self):
        import yaml
        r = _ar.abandon(_run_doc(), "stopping")
        doc = yaml.safe_load(_ar._dump(r))
        errors: list[dict] = []
        _vp.validate(doc, _vp.load_schema(_vp.RUN_SCHEMA), "#", "#", errors, "<t>")
        self.assertEqual(errors, [])


@unittest.skipUnless(HAVE, "advance-run.py or PyYAML unavailable")
class AbandonCliTests(unittest.TestCase):
    """The CLI's mode gate, and the book-pointer rule that keeps a terminal run
    reachable: only a book's CURRENT run can authorize its archive (ADR-0077 clause
    5(b)), so `current_run` survives BOTH a completion and an abandonment — only
    `current_prompt` is nulled. `current_run` is nulled by exactly one writer,
    `archive-promptbook`, at archival."""

    def _write_run(self, tmp: Path) -> Path:
        import yaml
        path = tmp / "run-RUN-001.yaml"
        path.write_text(_ar._dump(_run_doc(3)))
        return path

    def test_abandon_and_outcome_are_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            run = self._write_run(Path(td))
            proc = _cli([str(run), "--abandon", "--reason", "x", "--outcome", "done"])
            self.assertEqual(proc.returncode, 1)
            self.assertIn("mutually exclusive", proc.stdout)

    def test_neither_mode_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            run = self._write_run(Path(td))
            proc = _cli([str(run)])
            self.assertEqual(proc.returncode, 1)
            self.assertIn("required", proc.stdout)

    def test_abandon_keeps_the_books_current_run_pointer(self):
        import yaml
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = self._write_run(tmp)
            book = tmp / "PB-9001-x.yaml"
            book.write_text("id: PB-9001\ncurrent_run: RUN-001\ncurrent_prompt: 1\n")
            proc = _cli([str(run), "--abandon", "--reason", "stopping", "--book", str(book)])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            text = book.read_text()
            self.assertIn("current_run: RUN-001", text)
            self.assertIn("current_prompt: null", text)
            self.assertEqual(yaml.safe_load(run.read_text())["abandonment"]["kind"], "deliberate")

    def test_completed_run_keeps_the_books_current_run_pointer(self):
        # Contract (a): a completing advance nulls ONLY current_prompt. current_run
        # stays pointed at the run — the same rule that already holds for abandon —
        # and is nulled by exactly one writer, archive-promptbook, at archival.
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            path = tmp / "run-RUN-001.yaml"
            path.write_text(_ar._dump(_run_doc(1)))
            book = tmp / "PB-9001-x.yaml"
            book.write_text("id: PB-9001\ncurrent_run: RUN-001\ncurrent_prompt: 1\n")
            proc = _cli([str(path), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            text = book.read_text()
            self.assertIn("current_run: RUN-001", text)
            self.assertIn("current_prompt: null", text)


@unittest.skipUnless(HAVE, "advance-run.py or PyYAML unavailable")
class BookRewriteValidationBackstopTests(unittest.TestCase):
    """F2: the --book pointer writer mutates raw text via re.sub, so it needs its own
    validation backstop — an exactly-one-match assertion before writing, and a
    post-write re-parse. A duplicate `current_prompt:` key must fail LOUDLY rather
    than be rewritten twice or silently not at all; a lookalike key must not be
    matched by the anchored pattern; and a book that is not parseable YAML must get
    the documented `{"error": ...}` exit-1 contract rather than a traceback.

    Ordering is part of the contract: every check that CAN run before the run
    snapshot is written does, so a refusal never advances the run. Two checks are
    inherently post-write — they re-read what the rewrite produced — and each has
    its own refusal test below, because a guard no test enters is a guard that can
    regress unnoticed."""

    def _write_run(self, tmp: Path) -> Path:
        path = tmp / "run-RUN-001.yaml"
        path.write_text(_ar._dump(_run_doc(1)))
        return path

    def test_duplicate_current_prompt_key_refuses_the_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = self._write_run(tmp)
            before = run.read_text()
            book = tmp / "PB-9001-x.yaml"
            book_text = (
                "id: PB-9001\n"
                "current_run: RUN-001\n"
                "current_prompt: 1\n"
                "current_prompt: 1\n"
            )
            book.write_text(book_text)
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("2 lines matching", proc.stdout)
            self.assertIn("expected exactly 1", proc.stdout)
            # The book is untouched — no double-rewrite, no silent no-op.
            self.assertEqual(book.read_text(), book_text)
            # And NEITHER is the run. The --book validation runs BEFORE the run
            # snapshot is written, so a refusal leaves the run exactly as it was.
            # Were it the other way round, this refusal would strand the run one
            # prompt ahead of the book, and re-running the same command would mark
            # `done` a prompt that was never executed.
            self.assertEqual(run.read_text(), before)

    def test_lookalike_key_is_not_matched_by_the_anchored_pattern(self):
        # `current_prompt_backup:` is not `current_prompt:` — the anchored pattern
        # `^current_prompt: .*$` requires the literal key, so a lookalike key must
        # survive the rewrite untouched, and the real key is still the sole match.
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = self._write_run(tmp)
            book = tmp / "PB-9001-x.yaml"
            book.write_text(
                "id: PB-9001\n"
                "current_run: RUN-001\n"
                "current_prompt_backup: 99\n"
                "current_prompt: 1\n"
            )
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            text = book.read_text()
            self.assertIn("current_prompt_backup: 99", text)
            self.assertIn("current_prompt: null", text)
            self.assertIn("current_run: RUN-001", text)

    def test_a_well_formed_book_satisfies_every_rewrite_guard(self):
        # POSITIVE CONTROL for the refusal tests below: a well-formed book clears
        # every guard — the pre-write current_prompt type check, the pre-write
        # ^RUN-\d{3}$ pointer precondition, and both post-write re-parse checks.
        # It enters NONE of the refusal branches; each of those has its own test.
        # (The former name claimed a branch this test never reaches.)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = self._write_run(tmp)
            book = tmp / "PB-9001-x.yaml"
            book.write_text("id: PB-9001\ncurrent_run: RUN-001\ncurrent_prompt: 1\n")
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            import yaml
            doc = yaml.safe_load(book.read_text())
            self.assertEqual(doc["current_run"], "RUN-001")
            self.assertIsNone(doc["current_prompt"])

    def test_unparseable_book_fails_the_json_contract_and_leaves_the_run(self):
        # A book that is not YAML must produce the documented {"error": ...} exit-1
        # payload, NOT an uncaught traceback — and, being a pre-write check, must
        # leave the run snapshot untouched.
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = self._write_run(tmp)
            before = run.read_text()
            book = tmp / "PB-9001-x.yaml"
            book.write_text("id: PB-9001\ncurrent_run: RUN-001\ncurrent_prompt: 1\n"
                            "bad: [unclosed\n")
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertIn("does not parse as YAML", payload["error"])
            self.assertEqual(run.read_text(), before)

    def test_a_non_int_current_prompt_is_refused_before_either_write(self):
        # The run snapshot is attacker-controlled input, and `current_prompt` is
        # taken from it and interpolated into the book rewrite. A `n:` carrying a
        # newline injects a top-level key into the book, which PyYAML's
        # last-duplicate-wins then makes authoritative. Refused on TYPE, before
        # either file is written.
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            doc = _run_doc(2)
            doc["prompts"][1]["n"] = "2\ngoal: PWNED-INJECTED-KEY"
            run = tmp / "run-RUN-001.yaml"
            run.write_text(_ar._dump(doc))
            run_before = run.read_text()
            book = tmp / "PB-9001-x.yaml"
            book_text = ("id: PB-9001\ngoal: the real goal\n"
                         "current_run: RUN-001\ncurrent_prompt: 1\n")
            book.write_text(book_text)
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertIn("not an int or null", payload["error"])
            # Neither file moved, and the injected key never reached the book.
            self.assertEqual(book.read_text(), book_text)
            self.assertNotIn("PWNED-INJECTED-KEY", book.read_text())
            self.assertEqual(run.read_text(), run_before)

    def test_a_null_current_run_is_refused_before_either_write(self):
        # A book whose `current_run` is null cannot authorize the archive that a
        # completing advance hands it. This precondition is on PRE-EXISTING book
        # state, so it must fire before the writes: below them it would leave the
        # run `completed` and the book's `current_prompt` rewritten, then refuse.
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = tmp / "run-RUN-001.yaml"
            run.write_text(_ar._dump(_run_doc(1)))
            run_before = run.read_text()
            book = tmp / "PB-9001-x.yaml"
            book_text = "id: PB-9001\ncurrent_run: null\ncurrent_prompt: 1\n"
            book.write_text(book_text)
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertIn("does not match ^RUN-", payload["error"])
            self.assertEqual(book.read_text(), book_text)
            self.assertEqual(run.read_text(), run_before)

    def test_post_write_parse_failure_gets_the_json_contract_not_a_traceback(self):
        # POST-WRITE branch 1, driven through the real CLI. The anchor `&p` lives
        # ON the line the rewrite replaces, so the alias `*p` below it dangles once
        # the line is gone and the rewritten book no longer parses. An unguarded
        # re-parse raises here — exit 1 with EMPTY stdout, which this repo's
        # exit-code convention reads as a crash rather than a finding.
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = tmp / "run-RUN-001.yaml"
            run.write_text(_ar._dump(_run_doc(1)))
            book = tmp / "PB-9001-x.yaml"
            book.write_text("id: PB-9001\ncurrent_run: RUN-001\n"
                            "current_prompt: &p 1\nnote: *p\n")
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertTrue(proc.stdout.strip(), "exit 1 with empty stdout reads as a crash")
            payload = json.loads(proc.stdout)
            self.assertIn("no longer parses as YAML after write", payload["error"])

    def test_post_write_pointer_change_is_refused(self):
        # POST-WRITE branch 2, driven through the real CLI. `current_prompt`'s value
        # opens a multi-line FLOW sequence, so the second `current_run:` is nested
        # inside it and invisible to the pre-write parse. Replacing the opening line
        # closes the flow early and promotes that key to top level, where
        # last-duplicate-wins makes it the pointer — the exact silent-repoint this
        # guard exists to catch.
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = tmp / "run-RUN-001.yaml"
            run.write_text(_ar._dump(_run_doc(1)))
            book = tmp / "PB-9001-x.yaml"
            book.write_text("id: PB-9001\ncurrent_run: RUN-042\n"
                            "current_prompt: [1,\ncurrent_run: RUN-999]\n")
            proc = _cli([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertIn("pointer changed during a write", payload["error"])
            self.assertIn("RUN-042", payload["error"])
            self.assertIn("RUN-999", payload["error"])

    def test_post_write_non_mapping_is_refused(self):
        # POST-WRITE branch 3. Stated honestly: this branch has NO CLI-reachable
        # vector. The pre-write check already proved the book is a mapping, and the
        # rewrite substitutes one column-0 line with `current_prompt: <int|null>`,
        # which yields either a mapping or a parse error (branch 1) — never a
        # sequence or a scalar. It is a backstop against a future rewrite that is
        # not line-local, so it is driven at `main()` with the substitution itself
        # replaced. The sibling branches above are driven through the real CLI.
        import io
        import contextlib
        from unittest import mock
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            run = tmp / "run-RUN-001.yaml"
            run.write_text(_ar._dump(_run_doc(1)))
            book = tmp / "PB-9001-x.yaml"
            book.write_text("id: PB-9001\ncurrent_run: RUN-001\ncurrent_prompt: 1\n")
            buf = io.StringIO()
            with mock.patch.object(_ar.re, "sub", lambda *a, **k: "- not\n- a mapping\n"):
                with contextlib.redirect_stdout(buf):
                    with self.assertRaises(SystemExit) as ctx:
                        _ar.main([str(run), "--outcome", "done", "--book", str(book)])
            self.assertEqual(ctx.exception.code, 1)
            payload = __import__("json").loads(buf.getvalue())
            self.assertIn("no longer parses as a YAML mapping after write",
                          payload["error"])


@unittest.skipUnless(HAVE, "advance-run.py or PyYAML unavailable")
class AbandonValidatesBeforeWritingTests(unittest.TestCase):
    """Abandonment validates the document BEFORE it mutates it.

    An abandonment is recorded once and never retrofitted, so a half-applied one is
    unrecoverable: if `status: abandoned` reaches disk and the invocation then dies,
    the retrofit guard refuses every later attempt and the run can never archive by
    either path. Ordering is therefore the whole fix — the same order `advance()`
    already used."""

    def _malformed(self, tmp: Path) -> Path:
        """A snapshot with every key the CLI's own preamble checks, and no `prompts`.
        This is the shape that crashed AFTER the write."""
        path = tmp / "run-RUN-001.yaml"
        path.write_text(
            "format_version: '1'\n"
            "run_id: RUN-001\n"
            "book_id: PB-9001\n"
            "status: in_progress\n"
            "current_prompt: 1\n"
        )
        return path

    def test_abandon_on_a_run_missing_prompts_refuses_before_writing(self):
        import yaml
        with tempfile.TemporaryDirectory() as td:
            run = self._malformed(Path(td))
            before = run.read_text()
            proc = _cli([str(run), "--abandon", "--reason", "stopping"])
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            # A document verdict on stdout, not a traceback on stderr.
            self.assertIn("prompts", proc.stdout)
            self.assertNotIn("Traceback", proc.stderr)
            # And — the point of the test — the file is untouched, so the run is
            # still abandonable once the snapshot is repaired.
            self.assertEqual(run.read_text(), before)
            doc = yaml.safe_load(run.read_text())
            self.assertEqual(doc["status"], "in_progress")
            self.assertNotIn("abandonment", doc)

    def test_abandon_in_memory_refuses_a_run_missing_prompts(self):
        with self.assertRaises(SystemExit) as ctx:
            _ar.abandon({"status": "in_progress"}, "stopping")
        self.assertEqual(ctx.exception.code, 1)


@unittest.skipUnless(HAVE and shutil.which("git") is not None,
                     "advance-run.py, PyYAML or git unavailable")
class BaseCommitPinTests(unittest.TestCase):
    """`base_commit` is written once at run start and never rewritten.

    It is the one value the `patch` tier's archive check reads out of the run, so
    advancing it forward shrinks the diff that check proves — the exact move an
    overshooting run is motivated to make. Nothing pinned it, so this pins it against
    the snapshot's own committed record, mirroring abandonment's never-retrofit guard.

    The pin's honest limit is also asserted below: between run start and the
    snapshot's first commit there is no committed record, so there is nothing to
    compare against and the guard is inert."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name).resolve()
        self.addCleanup(self._td.cleanup)
        _git(self.root, "init", "-q", "-b", "main")
        self.run_path = self.root / "run-RUN-001.yaml"
        doc = _run_doc(3)
        doc["base_commit"] = "a" * 40
        self.run_path.write_text(_ar._dump(doc))

    def _commit(self):
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "snapshot")

    def _rewrite_base(self, value: str):
        import yaml
        doc = yaml.safe_load(self.run_path.read_text())
        doc["base_commit"] = value
        self.run_path.write_text(_ar._dump(doc))

    def test_a_base_commit_advanced_past_its_committed_record_is_refused(self):
        import yaml
        self._commit()
        self._rewrite_base("b" * 40)
        proc = _cli([str(self.run_path), "--outcome", "done"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("base_commit", proc.stdout)
        # Refused before the write: the advance did not land.
        doc = yaml.safe_load(self.run_path.read_text())
        self.assertEqual(doc["prompts"][0]["state"], "running")

    def test_the_abandon_path_is_pinned_too(self):
        self._commit()
        self._rewrite_base("b" * 40)
        proc = _cli([str(self.run_path), "--abandon", "--reason", "stopping"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("base_commit", proc.stdout)

    def test_an_unchanged_base_commit_advances_normally(self):
        self._commit()
        proc = _cli([str(self.run_path), "--outcome", "done"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_removing_the_base_commit_entirely_is_also_refused(self):
        import yaml
        self._commit()
        doc = yaml.safe_load(self.run_path.read_text())
        del doc["base_commit"]
        self.run_path.write_text(_ar._dump(doc))
        proc = _cli([str(self.run_path), "--outcome", "done"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("base_commit", proc.stdout)

    def test_adding_a_base_commit_where_the_record_had_none_is_refused(self):
        # The retrofit direction: a run that started outside a git work tree wrote
        # `base_commit: null`, and a later hand-edit supplies one to manufacture an
        # evidence source. "No committed record" and "a committed null" are
        # different states and must not be conflated.
        import yaml
        doc = yaml.safe_load(self.run_path.read_text())
        doc["base_commit"] = None
        self.run_path.write_text(_ar._dump(doc))
        self._commit()
        self._rewrite_base("c" * 40)
        proc = _cli([str(self.run_path), "--outcome", "done"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("base_commit", proc.stdout)

    def test_the_pin_is_inert_on_an_uncommitted_snapshot(self):
        # Stated as a test so the limit is recorded, not implied: a snapshot with no
        # committed version has nothing to compare against, and the guard must not
        # invent a verdict from the absence of evidence.
        self._rewrite_base("b" * 40)
        proc = _cli([str(self.run_path), "--outcome", "done"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_the_pin_is_inert_outside_a_git_work_tree(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "run-RUN-001.yaml"
            doc = _run_doc(3)
            doc["base_commit"] = "a" * 40
            path.write_text(_ar._dump(doc))
            proc = _cli([str(path), "--outcome", "done"])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
