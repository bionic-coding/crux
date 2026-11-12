"""Tests for generate-runtime-compat.py — the runtime-compatibility block regenerator.

Two lanes, deliberately separated:

* **Synthetic-tree lanes** build a miniature repo root (canonical file, skill
  catalog, a handful of `SKILL.md` targets) and drive the failure modes there.
  Mutating the real tree to prove a refusal would leave the checkout dirty on
  a failed assertion, and the refusals are properties of the CODE, not of this
  repo's content.
* **Real-tree lanes** assert the facts that are properties of THIS checkout:
  the projection is in sync, every region is byte-equivalent to the canonical,
  the four exempt skills carry no block, and nothing under the distributed
  roots cites an ADR by number.

Stdlib only. Run:
  uv run python3 -m unittest discover -s crux/scripts/tests -p 'test_generate_runtime_compat.py'
"""

from __future__ import annotations

import contextlib
import errno
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent.parent
SCRIPT = SCRIPTS_DIR / "generate-runtime-compat.py"
from _authoring_fixture import seed_authoring_probe

sys.path.insert(0, str(SCRIPTS_DIR))
import input_lanes  # noqa: E402


def _load_module():
    """Import the hyphenated script by location; it is not an importable name."""
    spec = importlib.util.spec_from_file_location("generate_runtime_compat", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_module()

BEGIN = gen.PROJECTION_BEGIN
END = gen.PROJECTION_END
CANONICAL_BODY = "## Runtime compatibility\n\nIntro sentence.\n\n- One bullet.\n"


def _files(exc: "gen.RegenError") -> list[str]:
    """The `file` of every entry a document-lane refusal carries, in order."""
    return [entry["file"] for entry in exc.errors]


def _skill_md(body: str = CANONICAL_BODY, *, marked: bool = True) -> str:
    head = "---\nname: x\ndescription: \"y\"\n---\n\n# Title\n\n"
    if not marked:
        return head + "Some prose.\n"
    return head + f"{BEGIN}\n{body}{END}\n\nMore prose.\n"


class SyntheticTreeCase(unittest.TestCase):
    """Builds a miniature repo root so refusals never touch the real checkout."""

    def _tree(
        self,
        tmp: Path,
        *,
        skills: dict[str, str] | None = None,
        canonical: str = CANONICAL_BODY,
        exempt: set[str] | None = None,
    ) -> Path:
        root = tmp
        seed_authoring_probe(root, SCRIPT)
        (root / "crux" / "templates").mkdir(parents=True)
        (root / "crux" / "catalog").mkdir(parents=True)
        (root / "crux" / "templates" / "runtime-compatibility.md").write_text(
            canonical, encoding="utf-8"
        )
        skills = skills if skills is not None else {"alpha": _skill_md(), "beta": _skill_md()}
        for name, text in skills.items():
            d = root / "crux" / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(text, encoding="utf-8")
        (root / "crux" / "catalog" / "skills.json").write_text(
            json.dumps([{"id": n, "name": n} for n in sorted(skills)]), encoding="utf-8"
        )
        self._patch_exempt(exempt if exempt is not None else set())
        return root

    def _patch_exempt(self, names: set[str]) -> None:
        original = gen.EXEMPT_SKILLS
        gen.EXEMPT_SKILLS = frozenset(names)
        self.addCleanup(lambda: setattr(gen, "EXEMPT_SKILLS", original))

    @staticmethod
    def _read(root: Path, name: str) -> str:
        return (root / "crux" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


class HappyPathTests(SyntheticTreeCase):
    def test_writes_the_canonical_body_into_every_marked_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(
                Path(tmp),
                skills={"alpha": _skill_md("stale\n"), "beta": _skill_md("stale\n")},
            )
            code, payload = gen.run(root, dry_run=False)
            self.assertEqual(code, 0)
            self.assertEqual(len(payload["written"]), 2)
            for name in ("alpha", "beta"):
                self.assertIn(CANONICAL_BODY, self._read(root, name))

    def test_is_idempotent_and_dry_run_then_reports_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), skills={"alpha": _skill_md("stale\n")})
            gen.run(root, dry_run=False)
            code, payload = gen.run(root, dry_run=False)
            self.assertEqual(code, 0)
            self.assertEqual(payload["written"], [])
            code, payload = gen.run(root, dry_run=True)
            self.assertEqual(code, 0)
            self.assertEqual(payload["drifted"], [])

    def test_dry_run_reports_drift_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), skills={"alpha": _skill_md("stale\n")})
            before = self._read(root, "alpha")
            code, payload = gen.run(root, dry_run=True)
            self.assertEqual(code, 1)
            self.assertEqual(payload["drifted"], ["crux/skills/alpha/SKILL.md"])
            self.assertEqual(self._read(root, "alpha"), before)

    def test_only_the_region_is_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), skills={"alpha": _skill_md("stale\n")})
            gen.run(root, dry_run=False)
            text = self._read(root, "alpha")
            self.assertTrue(text.startswith("---\nname: x\n"))
            self.assertTrue(text.endswith("More prose.\n"))

    def test_crlf_line_endings_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), skills={"alpha": _skill_md("stale\n")})
            path = root / "crux" / "skills" / "alpha" / "SKILL.md"
            with path.open("r", encoding="utf-8", newline="") as fh:
                crlf = fh.read().replace("\n", "\r\n")
            with path.open("w", encoding="utf-8", newline="") as fh:
                fh.write(crlf)
            code, _ = gen.run(root, dry_run=False)
            self.assertEqual(code, 0)
            with path.open("r", encoding="utf-8", newline="") as fh:
                after = fh.read()
            # The markers were still found (a bare `$` would miss them), and
            # the bytes outside the region kept their CRLF endings.
            self.assertIn("---\r\nname: x\r\n", after)
            self.assertIn("More prose.\r\n", after)

    def test_file_mode_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), skills={"alpha": _skill_md("stale\n")})
            path = root / "crux" / "skills" / "alpha" / "SKILL.md"
            os.chmod(path, 0o644)
            gen.run(root, dry_run=False)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o644)


class MarkerContractTests(SyntheticTreeCase):
    def test_missing_end_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = _skill_md().replace(END + "\n", "")
            root = self._tree(Path(tmp), skills={"alpha": broken})
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("missing marker", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), ["crux/skills/alpha/SKILL.md"])

    def test_duplicate_marker_fails_closed_rather_than_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            dup = _skill_md() + f"\n{BEGIN}\nsecond\n{END}\n"
            root = self._tree(Path(tmp), skills={"alpha": dup})
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("duplicate marker", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), ["crux/skills/alpha/SKILL.md"])

    def test_misordered_markers_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            head = "---\nname: x\n---\n\n"
            swapped = head + f"{END}\nbody\n{BEGIN}\n"
            root = self._tree(Path(tmp), skills={"alpha": swapped})
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("precedes BEGIN", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), ["crux/skills/alpha/SKILL.md"])

    def test_a_marker_mid_sentence_is_not_a_delimiter(self):
        """Whole-line matching: prose naming the marker must not delimit."""
        with tempfile.TemporaryDirectory() as tmp:
            prose = _skill_md().replace(
                "More prose.", f"The marker is written {BEGIN} inline here."
            )
            root = self._tree(Path(tmp), skills={"alpha": prose})
            code, _ = gen.run(root, dry_run=False)
            self.assertEqual(code, 0)
            self.assertIn(f"written {BEGIN} inline", self._read(root, "alpha"))

    def test_no_target_is_written_when_a_later_target_is_malformed(self):
        """Pass 1 validates everything before pass 2 writes anything."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(
                Path(tmp),
                skills={
                    "alpha": _skill_md("stale\n"),
                    "zeta": _skill_md("stale\n") + f"\n{BEGIN}\ndup\n{END}\n",
                },
            )
            before = self._read(root, "alpha")
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertEqual(_files(ctx.exception), ["crux/skills/zeta/SKILL.md"])
            self.assertEqual(self._read(root, "alpha"), before)


class CanonicalContractTests(SyntheticTreeCase):
    def test_empty_canonical_refuses_to_project_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), canonical="   \n\n")
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("refusing to project nothing", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), [gen.CANONICAL_FILE])

    def test_missing_canonical_file_is_a_findings_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp))
            (root / gen.CANONICAL_FILE).unlink()
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertEqual(ctx.exception.errors, [
                {"file": gen.CANONICAL_FILE, "error": input_lanes.absent_reason("file")}])

    def test_canonical_containing_a_projection_marker_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), canonical=f"## Runtime compatibility\n{BEGIN}\n")
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("wedge every later run", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), [gen.CANONICAL_FILE])

    def test_trailing_blank_lines_in_the_canonical_do_not_cause_drift(self):
        """Idempotence must not depend on how the canonical file happens to end."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), skills={"alpha": _skill_md("stale\n")})
            gen.run(root, dry_run=False)
            (root / gen.CANONICAL_FILE).write_text(CANONICAL_BODY + "\n\n\n", encoding="utf-8")
            code, _ = gen.run(root, dry_run=True)
            self.assertEqual(code, 0)


class FailClosedTargetDerivationTests(SyntheticTreeCase):
    """A skill that silently loses its markers must FAIL, not drop out."""

    def test_a_catalogued_skill_without_markers_or_an_exemption_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(
                Path(tmp),
                skills={"alpha": _skill_md("stale\n"), "beta": _skill_md(marked=False)},
            )
            before = self._read(root, "alpha")
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("beta", str(ctx.exception))
            self.assertIn("neither the runtime-compat markers nor an exemption", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), ["crux/skills/beta/SKILL.md"])
            # And it fails BEFORE writing, so the drift gate and the writer agree.
            self.assertEqual(self._read(root, "alpha"), before)

    def test_positive_control_the_same_tree_with_an_exemption_passes(self):
        """Without this, the refusal above would pass on a regenerator that always failed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(
                Path(tmp),
                skills={"alpha": _skill_md("stale\n"), "beta": _skill_md(marked=False)},
                exempt={"beta"},
            )
            code, payload = gen.run(root, dry_run=False)
            self.assertEqual(code, 0)
            self.assertEqual(payload["written"], ["crux/skills/alpha/SKILL.md"])
            self.assertEqual(payload["targets"], 1)

    def test_an_exempt_skill_that_carries_markers_fails(self):
        """The exemption list cannot rot in the other direction either."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(
                Path(tmp),
                skills={"alpha": _skill_md(), "beta": _skill_md()},
                exempt={"beta"},
            )
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("DO carry the runtime-compat markers", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), [gen.SCRIPT_FILE])

    def test_an_exemption_for_a_deleted_skill_fails(self):
        """The third direction the list can rot in, and the only silent one.

        The other two legs only look at skills that still exist, so an
        exemption left behind by a deleted skill was invisible to both: the
        entry named nothing, matched nothing, and the regenerator reported
        clean. The docstring claimed the list "cannot rot in either direction"
        while this hole was open, which is what this pins shut.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(
                Path(tmp),
                skills={"alpha": _skill_md(), "beta": _skill_md(marked=False)},
                exempt={"beta", "deleted-skill"},
            )
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("deleted-skill", str(ctx.exception))
            self.assertIn("the catalog does not carry", str(ctx.exception))
            # The still-live exemption is not reported as stale.
            self.assertNotIn("beta", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), [gen.SCRIPT_FILE])

    def test_positive_control_the_same_tree_without_the_dead_exemption_passes(self):
        """Without this, the refusal above passes on a regenerator that always failed.

        One exemption removed, nothing else changed.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(
                Path(tmp),
                skills={"alpha": _skill_md(), "beta": _skill_md(marked=False)},
                exempt={"beta"},
            )
            code, payload = gen.run(root, dry_run=False)
            self.assertEqual(code, 0)
            self.assertEqual(payload["targets"], 1)

    def test_a_marked_skill_absent_from_the_catalog_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp), skills={"alpha": _skill_md()})
            extra = root / "crux" / "skills" / "ghost"
            extra.mkdir()
            (extra / "SKILL.md").write_text(_skill_md(), encoding="utf-8")
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("absent from the catalog", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), ["crux/skills/ghost/SKILL.md"])

    def test_a_malformed_catalog_is_a_findings_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._tree(Path(tmp))
            (root / gen.CATALOG_FILE).write_text("{not json", encoding="utf-8")
            with self.assertRaises(gen.RegenError) as ctx:
                gen.run(root, dry_run=False)
            self.assertIn("not valid JSON", str(ctx.exception))
            self.assertEqual(_files(ctx.exception), [gen.CATALOG_FILE])


def _seed_exempt_members(root: Path) -> None:
    """Give each real EXEMPT_SKILLS name an unmarked SKILL.md.

    Every catalogued skill's SKILL.md is a catalogue member, exempt or not, so a
    CLI fixture that catalogues the real exemptions must carry their files.
    """
    for name in sorted(gen.EXEMPT_SKILLS):
        d = root / "crux" / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(_skill_md(marked=False), encoding="utf-8")


class CliContractTests(unittest.TestCase):
    """Exit-code semantics, driven through the script's own CLI."""

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False, capture_output=True, text=True,
        )

    def test_dry_run_on_the_real_tree_exits_zero_with_json(self):
        # --repo-root is explicit: the CLI takes its target from the invocation, so
        # without it this case declines whenever the suite runs from a directory that
        # is not this checkout, and the 53-target assertion below measures nothing.
        result = self._run("--dry-run", "--repo-root", str(SCRIPT.parents[2]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["drifted"], [])
        # A gate that measured nothing would also print an empty drift list.
        self.assertEqual(payload["targets"], 53)

    def test_seeded_drift_makes_the_cli_exit_one_with_json_on_stdout(self):
        """Positive control for the row above, through the same CLI."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_authoring_probe(root, SCRIPT)
            for sub in ("templates", "catalog", "skills"):
                (root / "crux" / sub).mkdir()
            (root / "crux" / "templates" / "runtime-compatibility.md").write_text(
                CANONICAL_BODY, encoding="utf-8"
            )
            # The exempt names are catalogued too. The CLI runs in a
            # subprocess, so it carries the REAL `EXEMPT_SKILLS`, and an
            # exemption naming a skill this catalog does not list is itself a
            # findings error — a fixture fault that would mask the drift this
            # test is the positive control for.
            (root / "crux" / "catalog" / "skills.json").write_text(
                json.dumps([{"name": n} for n in sorted({"alpha", *gen.EXEMPT_SKILLS})]),
                encoding="utf-8",
            )
            d = root / "crux" / "skills" / "alpha"
            d.mkdir()
            (d / "SKILL.md").write_text(_skill_md("drifted body\n"), encoding="utf-8")
            _seed_exempt_members(root)

            result = self._run("--dry-run", "--repo-root", str(root))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["drifted"], ["crux/skills/alpha/SKILL.md"])
            self.assertIn("generate-runtime-compat.py", payload["remediation"])

    def test_a_validation_error_exits_one_with_json_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed_authoring_probe(tmp, SCRIPT)
            result = self._run("--dry-run", "--repo-root", tmp)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            # The retired {"error": ...} shape is gone; every refusal is an entry.
            self.assertNotIn("error", payload)
            self.assertEqual(
                [e["file"] for e in payload["validation_errors"]],
                [gen.CANONICAL_FILE, gen.CATALOG_FILE, gen.SKILLS_DIR])
            self.assertNotIn("Traceback", result.stderr)

    def test_a_non_utf8_target_is_a_document_finding_on_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_authoring_probe(root, SCRIPT)
            (root / "crux" / "templates").mkdir(parents=True)
            (root / "crux" / "catalog").mkdir(parents=True)
            (root / "crux" / "templates" / "runtime-compatibility.md").write_text(
                CANONICAL_BODY, encoding="utf-8"
            )
            (root / "crux" / "catalog" / "skills.json").write_text(
                json.dumps([{"name": n} for n in sorted({"alpha", *gen.EXEMPT_SKILLS})]),
                encoding="utf-8",
            )
            d = root / "crux" / "skills" / "alpha"
            d.mkdir(parents=True)
            _seed_exempt_members(root)
            # Positive control: the same fixture with a UTF-8 target is clean.
            (d / "SKILL.md").write_text(_skill_md(), encoding="utf-8")
            control = self._run("--dry-run", "--repo-root", str(root))
            self.assertEqual(control.returncode, 0, control.stdout + control.stderr)

            (d / "SKILL.md").write_bytes(b"\xff\xfe not utf-8 at all\n")
            for args in (("--dry-run",), ()):
                with self.subTest(args=args):
                    result = self._run(*args, "--repo-root", str(root))
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    entries = json.loads(result.stdout)["validation_errors"]
                    self.assertEqual([e["file"] for e in entries],
                                     ["crux/skills/alpha/SKILL.md"])
                    self.assertIn("is not valid UTF-8", entries[0]["error"])
                    self.assertNotIn(str(root), entries[0]["error"])
                    self.assertNotIn("Traceback", result.stderr)
            self.assertEqual((d / "SKILL.md").read_bytes(), b"\xff\xfe not utf-8 at all\n")


def _skip_if_root(case: unittest.TestCase) -> None:
    if os.geteuid() == 0:
        case.skipTest("running as root: a mode-000 path is still readable")


def _snapshot(root: Path) -> dict[str, object]:
    """Every path under `root` with its bytes, so a changed or created file shows.

    A path the process cannot read records its mode instead; a directory it
    cannot list is skipped by `os.walk` the same way before and after a run.
    """
    snap: dict[str, object] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            st = os.lstat(path)
            if os.path.islink(path) or not os.path.isfile(path):
                snap[rel] = ("node", st.st_mode)
                continue
            try:
                snap[rel] = path.read_bytes()
            except OSError:
                snap[rel] = ("unreadable", st.st_mode)
    return snap


MODES = (("write", ()), ("dry-run", ("--dry-run",)))


class InputLaneCase(SyntheticTreeCase):
    """One fixture per test: `alpha` drifted and `beta` clean, both catalogued and marked.

    `control()` is the positive control on the fixture each refusal then breaks:
    the dry-run reads every input and reports alpha drifted.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(self._remove_tmp)
        self.root = self._tree(
            self.tmp, skills={"alpha": _skill_md("stale\n"), "beta": _skill_md()})
        self.skills = self.root / gen.SKILLS_DIR

    def _remove_tmp(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self.tmp):
            for name in dirnames:
                os.chmod(Path(dirpath) / name, 0o755)
        for dirpath, _dirnames, filenames in os.walk(self.tmp):
            for name in filenames:
                p = Path(dirpath) / name
                if not p.is_symlink():
                    os.chmod(p, 0o644)
        shutil.rmtree(self.tmp)

    def main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = gen.main([*args, "--repo-root", str(self.root)])
        return rc, out.getvalue(), err.getvalue()

    def control(self) -> None:
        rc, out, err = self.main("--dry-run")
        self.assertEqual(rc, 1, out + err)
        self.assertEqual(json.loads(out)["drifted"], ["crux/skills/alpha/SKILL.md"])

    def assert_document_lane(self, expected: list[tuple[str, str]]) -> list[dict]:
        """Exit 1 in every mode with exactly `expected` (file, reason fragment) entries."""
        before = _snapshot(self.root)
        entries: list[dict] = []
        for mode, args in MODES:
            with self.subTest(mode=mode):
                rc, out, err = self.main(*args)
                self.assertEqual(rc, 1, out + err)
                entries = json.loads(out)["validation_errors"]
                self.assertEqual([e["file"] for e in entries], [f for f, _ in expected])
                for entry, (_f, fragment) in zip(entries, expected):
                    self.assertIn(fragment, entry["error"])
                    for form in (str(self.tmp), str(self.tmp.resolve())):
                        self.assertNotIn(form, entry["error"], "absolute path in a reason")
                self.assertEqual(err, "")
                self.assertEqual(_snapshot(self.root), before, "an output changed or appeared")
        return entries

    def assert_environment_lane(self, *fragments: str, patch=None) -> None:
        """Exit 2 in every mode, nothing on stdout, every fragment on stderr."""
        before = _snapshot(self.root)
        for mode, args in MODES:
            with self.subTest(mode=mode):
                with patch() if patch else contextlib.nullcontext():
                    rc, out, err = self.main(*args)
                self.assertEqual(rc, 2, out + err)
                self.assertEqual(out, "")
                self.assertIn("generate-runtime-compat.py: environment failure: ", err)
                for fragment in fragments:
                    self.assertIn(fragment, err)
                self.assertNotIn("Traceback", err)
                self.assertEqual(_snapshot(self.root), before, "an output changed or appeared")

    def eio_on(self, rel: str):
        """Patch the one reader so `rel` fails with EIO; every other read is real."""
        real = gen.read_text_verbatim
        # The CLI resolves --repo-root, so compare resolved forms.
        target = (self.root / rel).resolve()

        def read(path):
            if Path(path).resolve() == target:
                raise OSError(errno.EIO, "Input/output error", str(path))
            return real(path)

        return lambda: mock.patch.object(gen, "read_text_verbatim", read)


class RequiredFileLaneTests(InputLaneCase):
    """The canonical file and the catalog: absent, unreadable, and process-level."""

    REQUIRED = (gen.CANONICAL_FILE, gen.CATALOG_FILE)

    def test_positive_control_present_required_files_reach_the_drift_report(self):
        """Positive control: the absence fixture, with each required file present, runs to drift."""
        for rel in self.REQUIRED:
            with self.subTest(file=rel):
                self.assertTrue((self.root / rel).is_file(), f"{rel} missing from the fixture")
                self.control()

    def test_a_confirmed_absent_required_file_is_a_finding(self):
        for rel in self.REQUIRED:
            with self.subTest(file=rel):
                self.control()
                path = self.root / rel
                saved = path.read_bytes()
                path.unlink()
                self.assert_document_lane([(rel, "is a required input and is absent")])
                self.assertFalse(path.exists(), "a refusal created the absent input")
                path.write_bytes(saved)

    def test_a_mode_000_required_file_is_a_finding(self):
        _skip_if_root(self)
        for rel in self.REQUIRED:
            with self.subTest(file=rel):
                self.control()
                path = self.root / rel
                path.chmod(0o000)
                self.assert_document_lane([(rel, "could not be read (EACCES")])
                path.chmod(0o644)

    def test_an_invalid_utf8_required_file_is_a_finding(self):
        for rel in self.REQUIRED:
            with self.subTest(file=rel):
                self.control()
                path = self.root / rel
                saved = path.read_bytes()
                path.write_bytes(b"\xff\xfe not utf-8\n")
                self.assert_document_lane([(rel, "is not valid UTF-8")])
                path.write_bytes(saved)

    def test_a_directory_in_place_of_a_required_file_is_a_finding(self):
        for rel in self.REQUIRED:
            with self.subTest(file=rel):
                self.control()
                path = self.root / rel
                saved = path.read_bytes()
                path.unlink()
                path.mkdir()
                self.assert_document_lane([(rel, "could not be read (EISDIR")])
                path.rmdir()
                path.write_bytes(saved)

    def test_eio_on_a_required_file_takes_the_environment_lane(self):
        for rel in self.REQUIRED:
            with self.subTest(file=rel):
                self.control()
                self.assert_environment_lane(f"{rel}: OSError: ", patch=self.eio_on(rel))


class SkillsDirectoryLaneTests(InputLaneCase):
    """The listed skills directory: unlistable, a regular file, confirmed absent."""

    def test_positive_control_a_present_skills_directory_reaches_the_drift_report(self):
        """Positive control: the absence fixture, with the skills directory present, runs to drift."""
        self.assertTrue(self.skills.is_dir(), "the fixture has no skills directory")
        self.control()

    def test_a_mode_000_skills_directory_takes_the_environment_lane(self):
        _skip_if_root(self)
        self.control()
        self.skills.chmod(0o000)
        self.addCleanup(self.skills.chmod, 0o755)
        self.assert_environment_lane(f"{gen.SKILLS_DIR}: PermissionError: ")

    def test_a_regular_file_at_the_skills_path_takes_the_environment_lane(self):
        self.control()
        shutil.rmtree(self.skills)
        self.skills.write_text("not a directory\n", encoding="utf-8")
        self.assert_environment_lane(
            f"{gen.SKILLS_DIR}: NotADirectoryError: ", "exists and is not a directory")

    def test_a_confirmed_absent_skills_directory_names_it_and_every_member(self):
        self.control()
        shutil.rmtree(self.skills)
        self.assert_document_lane([
            (gen.SKILLS_DIR, "is the required skills directory and is absent"),
            ("crux/skills/alpha/SKILL.md", "is a catalogue member and is absent"),
            ("crux/skills/beta/SKILL.md", "is a catalogue member and is absent"),
        ])
        self.assertFalse(self.skills.exists(), "a refusal created the skills directory")

    def test_a_regular_file_in_the_skills_directory_is_no_candidate(self):
        # Positive control for the probe: `.gitkeep` fails it with ENOTDIR.
        (self.skills / ".gitkeep").write_text("", encoding="utf-8")
        self.control()


class SkillMemberLaneTests(InputLaneCase):
    """Each listed SKILL.md and each catalogue member."""

    def test_a_catalogued_skill_with_no_skill_md_is_an_absent_member(self):
        self.control()
        (self.skills / "beta" / "SKILL.md").unlink()
        self.assert_document_lane(
            [("crux/skills/beta/SKILL.md", "is a catalogue member and is absent")])

    def test_a_catalogued_skill_with_no_directory_is_an_absent_member(self):
        self.control()
        shutil.rmtree(self.skills / "beta")
        self.assert_document_lane(
            [("crux/skills/beta/SKILL.md", "is a catalogue member and is absent")])

    def test_an_absent_exempt_member_is_still_an_absent_member(self):
        (self.skills / "gamma").mkdir()
        (self.skills / "gamma" / "SKILL.md").write_text(_skill_md(marked=False), "utf-8")
        catalog = self.root / gen.CATALOG_FILE
        catalog.write_text(json.dumps([{"name": n} for n in ("alpha", "beta", "gamma")]),
                           encoding="utf-8")
        self._patch_exempt({"gamma"})
        self.control()
        (self.skills / "gamma" / "SKILL.md").unlink()
        self.assert_document_lane(
            [("crux/skills/gamma/SKILL.md", "is a catalogue member and is absent")])

    def test_a_mode_000_member_is_one_finding_never_also_unmarked(self):
        _skip_if_root(self)
        self.control()
        path = self.skills / "beta" / "SKILL.md"
        path.chmod(0o000)
        self.assert_document_lane(
            [("crux/skills/beta/SKILL.md", "could not be read (EACCES")])

    def test_an_invalid_utf8_member_is_a_finding(self):
        self.control()
        (self.skills / "beta" / "SKILL.md").write_bytes(b"\xff\xfe not utf-8\n")
        self.assert_document_lane([("crux/skills/beta/SKILL.md", "is not valid UTF-8")])

    def test_a_mode_000_skill_directory_is_a_finding_at_its_skill_md(self):
        _skip_if_root(self)
        self.control()
        (self.skills / "beta").chmod(0o000)
        self.addCleanup((self.skills / "beta").chmod, 0o755)
        self.assert_document_lane(
            [("crux/skills/beta/SKILL.md", "could not be read (EACCES")])

    def test_a_dangling_skill_md_link_in_an_uncatalogued_directory_is_a_finding(self):
        self.control()
        (self.skills / "ghost").mkdir()
        (self.skills / "ghost" / "SKILL.md").symlink_to(self.tmp / "nowhere.md")
        self.assert_document_lane(
            [("crux/skills/ghost/SKILL.md", "was listed but could not be opened (ENOENT")])

    def test_a_hidden_marked_uncatalogued_skill_is_refused(self):
        self.control()
        (self.skills / ".hid").mkdir()
        (self.skills / ".hid" / "SKILL.md").write_text(_skill_md(), encoding="utf-8")
        self.assert_document_lane(
            [("crux/skills/.hid/SKILL.md", "is a marked skill absent from the catalog")])

    def test_eio_on_a_member_takes_the_environment_lane(self):
        self.control()
        rel = "crux/skills/beta/SKILL.md"
        self.assert_environment_lane(f"{rel}: OSError: ", patch=self.eio_on(rel))

    def test_two_simultaneous_findings_are_named_in_one_payload(self):
        self.control()
        (self.skills / "beta" / "SKILL.md").write_bytes(b"\xff not utf-8\n")
        (self.root / gen.CANONICAL_FILE).unlink()
        self.assert_document_lane([
            (gen.CANONICAL_FILE, "is a required input and is absent"),
            ("crux/skills/beta/SKILL.md", "is not valid UTF-8"),
        ])


class DependentCheckTests(InputLaneCase):
    """A check that depends on a refused input is skipped: one finding, not a flood."""

    def test_a_malformed_catalog_yields_exactly_its_own_finding(self):
        (self.skills / "gamma").mkdir()
        (self.skills / "gamma" / "SKILL.md").write_text(_skill_md(marked=False), "utf-8")
        catalog = self.root / gen.CATALOG_FILE
        catalog.write_text(json.dumps([{"name": n} for n in ("alpha", "beta", "gamma")]),
                           encoding="utf-8")
        self._patch_exempt({"gamma"})
        self.control()
        catalog.write_text("{not json", encoding="utf-8")
        self.assert_document_lane([(gen.CATALOG_FILE, "not valid JSON")])

    def test_an_absent_template_beside_a_drifted_target_writes_nothing(self):
        self.control()
        (self.root / gen.CANONICAL_FILE).unlink()
        self.assert_document_lane([(gen.CANONICAL_FILE, "is a required input and is absent")])
        self.assertIn("stale\n", self._read(self.root, "alpha"))

    def test_a_refused_catalog_still_reports_a_malformed_region(self):
        self.control()
        (self.root / gen.CATALOG_FILE).write_text("{not json", encoding="utf-8")
        alpha = self.skills / "alpha" / "SKILL.md"
        alpha.write_text(_skill_md().replace(END + "\n", ""), encoding="utf-8")
        self.assert_document_lane([
            (gen.CATALOG_FILE, "not valid JSON"),
            ("crux/skills/alpha/SKILL.md", "missing marker"),
        ])


class PrecedenceTests(InputLaneCase):
    """An environment-lane failure wins, and names the document finding beside it."""

    def test_an_absent_member_plus_eio_takes_the_environment_lane(self):
        self.control()
        (self.skills / "beta" / "SKILL.md").unlink()
        self.assert_environment_lane(
            f"{gen.CANONICAL_FILE}: OSError: ",
            "document finding met in the same run: crux/skills/beta/SKILL.md: is a "
            "catalogue member and is absent",
            patch=self.eio_on(gen.CANONICAL_FILE))

    def test_a_pass_two_write_failure_keeps_exit_two(self):
        self.control()

        def fail(path, text):
            raise OSError(errno.EIO, "Input/output error", str(path))

        with mock.patch.object(gen, "write_text_atomically", fail):
            rc, out, err = self.main()
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("generate-runtime-compat.py: ", err)
        self.assertIn("Input/output error", err)


class RealTreeTests(unittest.TestCase):
    """Facts about THIS checkout, which the synthetic lanes cannot assert."""

    def test_the_projection_covers_53_of_the_57_catalogued_skills(self):
        targets = gen.resolve_targets(REPO_ROOT)
        catalogued = gen._catalogued_skills(REPO_ROOT)
        self.assertEqual(len(catalogued), 57)
        self.assertEqual(len(targets), 53)
        self.assertEqual(len(gen.EXEMPT_SKILLS), 4)
        self.assertEqual(len(targets) + len(gen.EXEMPT_SKILLS), len(catalogued))

    def test_every_region_is_byte_equivalent_to_the_canonical(self):
        canonical = gen._load_canonical(REPO_ROOT)
        for rel in gen.resolve_targets(REPO_ROOT):
            with self.subTest(target=rel):
                text = gen.read_text_verbatim(REPO_ROOT / rel)
                region = gen.extract_region(text, BEGIN, END, rel)
                self.assertEqual(region, canonical)

    def test_the_four_exempt_skills_carry_no_block_and_no_markers(self):
        for name in sorted(gen.EXEMPT_SKILLS):
            with self.subTest(skill=name):
                path = REPO_ROOT / "crux" / "skills" / name / "SKILL.md"
                self.assertTrue(path.is_file(), f"{name} is exempt but has no SKILL.md")
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(BEGIN, text)
                self.assertNotIn("## Runtime compatibility", text)


if __name__ == "__main__":
    unittest.main()
