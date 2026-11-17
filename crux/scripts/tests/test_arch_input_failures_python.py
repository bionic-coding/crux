"""ADR-0181 in the Python pack — absent, unreadable, unparseable and unlistable inputs.

`PythonPackLaneTests` holds the cases the core's shared reader and walk give
every pack. The classes below hold the Python pack's own sites: its fixed
manifest and OpenAPI reads, its candidate probes (`_resolve_pkg_dir` and the
Alembic `versions/` locations), its listings, its decode and parse sites, its
route-scan cap. The broad-handler rule covers every pack module from
`test_arch_input_failures_core.py`.

Each case derives a fixture through `derive-arch.py` and asserts the lane: an
omission named in the map and in `coverage.json` with exit 0, a document
finding with exit 1, or an environment failure with exit 2. Every refusing
case asserts the byte-unchanged arch tree, and the clean derive of the same
fixture in `setUp` is the positive control.
"""

from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arch_input_failures_support import (
    CORE,
    PackLaneCases,
    active_ledger,
    arch_snapshot,
    bionic,
    coverage,
    run_cli,
    skip_if_root,
    write,
)

PY = __import__("crux.arch.packs.python", fromlist=["extract_python_data_model"])


class PythonPackLaneTests(PackLaneCases, unittest.TestCase):
    SOURCE = "app/models.py"
    SUBDIR = "app/sub"

    def build(self, root: Path) -> None:
        write(root, "pyproject.toml", '[project]\nname = "app"\nversion = "0.1"\n')
        write(root, "app/__init__.py", "")
        write(root, "app/models.py", "from dataclasses import dataclass\n\n\n"
                                     "@dataclass\nclass User:\n    name: str\n")
        write(root, "app/sub/__init__.py", "")
        write(root, "app/sub/util.py", "def f():\n    return 1\n")


#: A repository the Python pack populates in all three descriptive concerns:
#: a SQLAlchemy model (data-model), a FastAPI route (api-surface) and the
#: declared package `app` (module-graph). `requirements.txt` is a second stack
#: marker, so a fault at `pyproject.toml` leaves the stack Python.
def python_repo(root: Path) -> None:
    bionic(root)
    write(root, "pyproject.toml", '[project]\nname = "app"\nversion = "0.1"\n')
    write(root, "requirements.txt", "fastapi\n")
    write(root, "app/__init__.py", "")
    write(root, "app/models.py",
          "from sqlalchemy import Column, Integer\n\n\n"
          "class User(Base):\n    __tablename__ = 'users'\n"
          "    id = Column(Integer, primary_key=True)\n")
    write(root, "app/api.py",
          "from fastapi import APIRouter\n\n"
          "from . import models\n\n"
          "router = APIRouter()\n\n\n"
          "@router.get('/items')\ndef items():\n    return []\n")
    write(root, "app/sub/__init__.py", "")
    write(root, "app/sub/util.py", "from .. import models\n")


class _Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        python_repo(self.root)
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))
        self.before = arch_snapshot(self.root)

    def tearDown(self):
        for path in [self.root, *self.root.rglob("*")]:
            try:
                if not path.is_symlink():
                    os.chmod(path, 0o755 if path.is_dir() else 0o644)
            except OSError:
                pass
        self._tmp.cleanup()

    def omissions(self, concern: str) -> list[dict]:
        return coverage(self.root)[concern]["omissions"]

    def spine(self, concern: str) -> str:
        return (self.root / "bionic" / "arch" / f"{concern}.md").read_text()

    def derive_ok(self) -> None:
        code, _out, payload, err = run_cli(self.root)
        self.assertEqual(code, 0, (payload, err))

    def assert_omitted(self, rel: str, reason: str, kind: str, *concerns: str) -> None:
        self.derive_ok()
        for concern in concerns:
            with self.subTest(concern=concern):
                self.assertIn({"path": rel, "reason": reason, "kind": kind},
                              self.omissions(concern))
                self.assertIn(f"- `{rel}` — {reason} ({kind})", self.spine(concern))

    def assert_no_omission(self) -> None:
        self.derive_ok()
        for concern, rec in coverage(self.root).items():
            self.assertEqual(rec["omissions"], [], concern)

    def assert_refused(self, code_want: int, name: str) -> None:
        for argv in ((), ("--dry-run",)):
            with self.subTest(argv=argv):
                code, out, payload, err = run_cli(self.root, *argv)
                self.assertEqual(code, code_want, (payload, err))
                if code_want == 1:
                    self.assertIn(name, [f["file"] for f in payload["validation_errors"]])
                else:
                    self.assertEqual(out, "")
                    self.assertIn(name, err)
                self.assertEqual(arch_snapshot(self.root), self.before)


class PositiveControlTests(_Repo):

    def test_every_concern_populates_with_no_omission(self):
        cov = coverage(self.root)
        for concern in ("data-model", "api-surface", "module-graph"):
            self.assertEqual(cov[concern]["verdict"], "populated", concern)
            self.assertEqual(cov[concern]["omissions"], [], concern)
        self.assertIn("users", self.spine("data-model"))
        self.assertIn("`/items`", self.spine("api-surface"))


class AbsentTests(_Repo):

    def test_an_absent_pyproject_is_no_input(self):
        (self.root / "pyproject.toml").unlink()
        self.assert_no_omission()
        self.assertEqual(coverage(self.root)["module-graph"]["verdict"], "populated")

    def test_an_absent_openapi_document_is_no_input(self):
        self.assert_no_omission()
        self.assertNotIn("openapi.json", self.spine("api-surface"))

    def test_a_regular_file_at_the_src_directory_gate_is_no_input(self):
        write(self.root, "src", "not a directory\n")
        self.assert_no_omission()
        self.assertEqual(coverage(self.root)["module-graph"]["verdict"], "populated")

    def test_a_regular_file_at_an_alembic_versions_location_is_no_input(self):
        write(self.root, "alembic/versions", "not a directory\n")
        self.assert_no_omission()


class CandidateProbeTests(_Repo):
    """`_resolve_pkg_dir` tries `src/<name>` then `<name>` (nits F1)."""

    def test_positive_control_an_absent_first_candidate_reads_the_second(self):
        self.assertFalse((self.root / "src").exists())
        self.assert_no_omission()
        self.assertIn("app", self.spine("module-graph"))

    def test_a_regular_file_at_the_first_candidate_is_not_this_candidate(self):
        write(self.root, "src/app", "a file, not a package\n")
        self.assert_no_omission()
        self.assertEqual(coverage(self.root)["module-graph"]["verdict"], "populated")

    def test_a_dangling_link_at_the_first_candidate_is_named_and_ends_the_probe(self):
        (self.root / "src").mkdir()
        os.symlink("nowhere", self.root / "src" / "app")
        with active_ledger(self.root, "module-graph") as ledger:
            found = PY._resolve_pkg_dir(self.root, "app")
        self.assertIsNone(found)        # the second candidate is not read in its place
        self.assertEqual(ledger.omissions("module-graph"),
                         [{"path": "src/app", "reason": "not-a-file",
                           "kind": "symbolic-link"}])
        self.assert_omitted("src/app", "not-a-file", "symbolic-link", "module-graph")

    def test_no_candidate_present_records_nothing(self):
        (self.root / "app").rename(self.root / "application")
        with active_ledger(self.root, "module-graph") as ledger:
            self.assertIsNone(PY._resolve_pkg_dir(self.root, "app"))
        self.assertEqual(ledger.omissions("module-graph"), [])
        self.assertEqual(ledger.findings, [])

    def test_a_name_that_is_no_path_component_names_no_candidate(self):
        for name in ("a/b", "x" * 300, "bad\x00name"):
            with self.subTest(name=name[:12]):
                with active_ledger(self.root, "module-graph") as ledger:
                    self.assertIsNone(PY._resolve_pkg_dir(self.root, name))
                self.assertEqual(ledger.omissions("module-graph"), [])


class UnreadableTests(_Repo):

    def test_an_undecodable_source_is_named_where_it_is_walked(self):
        write(self.root, "app/bad.py", b"NAME = '\xff'\n")
        self.assert_omitted("app/bad.py", "undecodable", "undecodable",
                            "data-model", "api-surface")

    def test_a_symbolic_link_source_is_named_not_a_file(self):
        os.symlink("models.py", self.root / "app" / "alias.py")
        self.assert_omitted("app/alias.py", "not-a-file", "symbolic-link",
                            "data-model", "api-surface")

    def test_a_directory_at_openapi_json_is_not_a_file(self):
        (self.root / "openapi.json").mkdir()
        self.assert_omitted("openapi.json", "not-a-file", "directory", "api-surface")
        # The route probe answers in its place.
        self.assertIn("`/items`", self.spine("api-surface"))

    def test_a_dangling_link_at_openapi_json_is_not_a_file(self):
        os.symlink("nowhere.json", self.root / "openapi.json")
        self.assert_omitted("openapi.json", "not-a-file", "symbolic-link", "api-surface")

    def test_positive_control_a_regular_openapi_json_is_read(self):
        write(self.root, "openapi.json",
              '{"paths": {"/pets": {"get": {"summary": "list", "tags": ["pets"]}}}}')
        self.assert_no_omission()
        self.assertIn("_Derived from `openapi.json`._", self.spine("api-surface"))

    def test_a_directory_at_pyproject_toml_is_not_a_file(self):
        (self.root / "pyproject.toml").unlink()
        (self.root / "pyproject.toml").mkdir()
        self.assert_omitted("pyproject.toml", "not-a-file", "directory", "module-graph")

    def test_a_dangling_link_at_pyproject_toml_is_not_a_file(self):
        (self.root / "pyproject.toml").unlink()
        os.symlink("nowhere.toml", self.root / "pyproject.toml")
        self.assert_omitted("pyproject.toml", "not-a-file", "symbolic-link", "module-graph")

    def test_an_undecodable_pyproject_is_named(self):
        write(self.root, "pyproject.toml", b'[project]\nname = "\xff"\n')
        self.assert_omitted("pyproject.toml", "undecodable", "undecodable", "module-graph")

    def test_a_mode_000_pyproject_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / "pyproject.toml", 0)
        self.assert_refused(1, "pyproject.toml")

    def test_a_mode_000_openapi_json_is_a_document_finding(self):
        skip_if_root(self)
        write(self.root, "openapi.json", '{"paths": {}}')
        os.chmod(self.root / "openapi.json", 0)
        self.before = arch_snapshot(self.root)
        self.assert_refused(1, "openapi.json")

    def test_a_fifo_at_openapi_json_is_an_environment_failure(self):
        os.mkfifo(self.root / "openapi.json")
        self.assert_refused(2, "openapi.json")


class UnparseableTests(_Repo):

    def test_an_unparseable_source_is_named_and_not_as_a_residual(self):
        write(self.root, "app/broken.py", "def (\n")
        self.assert_omitted("app/broken.py", "unparseable", "unparseable",
                            "data-model", "api-surface")
        for concern in ("data-model", "api-surface"):
            self.assertNotIn("Python's parser refused", self.spine(concern))
        # Read and omitted for its content, so still hashed (ADR-0181 point 5).
        self.assertIn("app/broken.py",
                      coverage(self.root)["data-model"]["inputs_found"])

    def test_an_unparseable_pyproject_is_named(self):
        write(self.root, "pyproject.toml", "[project\n")
        self.assert_omitted("pyproject.toml", "unparseable", "unparseable", "module-graph")
        self.assertEqual(coverage(self.root)["module-graph"]["verdict"], "populated")

    def test_an_unparseable_setup_py_is_named(self):
        # The root hint names no package, so the nested manifests are read.
        write(self.root, "pyproject.toml", '[project]\nname = "absent-pkg"\n')
        write(self.root, "svc/setup.py", "setup(name=\n")
        self.assert_omitted("svc/setup.py", "unparseable", "unparseable", "module-graph")

    def test_an_unparseable_openapi_json_is_named(self):
        write(self.root, "openapi.json", "{not json")
        self.assert_omitted("openapi.json", "unparseable", "unparseable", "api-surface")

    def test_an_unparseable_migration_is_named(self):
        write(self.root, "alembic/versions/0001_init.py",
              "revision = 'a1'\ndown_revision = None\n")
        write(self.root, "alembic/versions/0002_bad.py", "revision = (\n")
        self.assert_omitted("alembic/versions/0002_bad.py", "unparseable", "unparseable",
                            "data-model")
        self.assertIn("`a1`", self.spine("data-model"))

    def test_a_memory_error_while_parsing_a_source_exits_2(self):
        real = ast.parse

        def boom(source, *a, **k):
            if isinstance(source, str) and "__tablename__ = 'users'" in source:
                raise MemoryError()
            return real(source, *a, **k)
        with mock.patch.object(PY.ast, "parse", side_effect=boom):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("app/models.py", err)
        self.assertIn("MemoryError", err)
        self.assertEqual(arch_snapshot(self.root), self.before)


class UnlistableTests(_Repo):

    def test_an_unlistable_src_directory_is_an_environment_failure(self):
        skip_if_root(self)
        write(self.root, "src/other/__init__.py", "")
        self.assertEqual(run_cli(self.root)[0], 0)
        self.before = arch_snapshot(self.root)
        os.chmod(self.root / "src", 0o300)      # searchable, not listable
        self.assert_refused(2, "src")

    def test_an_unlistable_versions_directory_is_an_environment_failure(self):
        skip_if_root(self)
        write(self.root, "alembic/versions/0001_init.py",
              "revision = 'a1'\ndown_revision = None\n")
        self.assertEqual(run_cli(self.root)[0], 0)
        self.before = arch_snapshot(self.root)
        os.chmod(self.root / "alembic" / "versions", 0o300)
        self.assert_refused(2, "alembic/versions")

    # The shared walk reaches an unlistable directory first in a derive, so the
    # pack's own listing sites are driven directly under an active ledger.

    def test_the_package_listing_raises_the_environment_lane(self):
        skip_if_root(self)
        write(self.root, "pyproject.toml", '[project]\nname = "absent-pkg"\n')
        write(self.root, "src/other/__init__.py", "")
        os.chmod(self.root / "src", 0o300)
        with active_ledger(self.root, "module-graph"):
            with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                PY.detect_packages(self.root)
        self.assertTrue(any(line.startswith("src:") for line in caught.exception.failures),
                        caught.exception.failures)

    def test_the_migration_listing_raises_the_environment_lane(self):
        skip_if_root(self)
        write(self.root, "alembic/versions/0001_init.py",
              "revision = 'a1'\ndown_revision = None\n")
        versions = self.root / "alembic" / "versions"
        os.chmod(versions, 0o300)
        with active_ledger(self.root, "data-model"):
            with self.assertRaises(CORE.ArchEnvironmentFailure):
                PY._has_migration(self.root, versions)
        os.chmod(versions, 0o755)
        with active_ledger(self.root, "data-model"):        # positive control
            self.assertTrue(PY._has_migration(self.root, versions))


class ScanCapTests(_Repo):
    """The route scan's file cap (packs/python.py `_RouteScan._scan`) is a
    counted over-cap omission over the sorted walk (ADR-0181 approach 8)."""

    def test_the_cap_names_the_skipped_count_and_drops_the_residual_line(self):
        total = len(list(self.root.rglob("*.py")))
        with mock.patch.object(PY, "_MAX_SCAN_FILES", 2):
            self.derive_ok()
        caps = [r for r in self.omissions("api-surface") if "cap" in r]
        self.assertEqual(caps, [{"cap": "_MAX_SCAN_FILES", "dir": ".",
                                 "skipped": total - 2, "reason": "over-cap",
                                 "kind": "scan-cap"}])
        text = self.spine("api-surface")
        self.assertIn(f"- scan cap `_MAX_SCAN_FILES` under `.` skipped {total - 2} input(s)",
                      text)
        self.assertNotIn("file bound", text)

    def test_positive_control_without_a_ledger_the_residual_line_renders(self):
        with mock.patch.object(PY, "_MAX_SCAN_FILES", 2):
            scan = PY._RouteScan(self.root)
        self.assertTrue(scan.truncated)
        self.assertTrue(any("file bound" in line for line in scan.residual_lines()))


class LedgerParityTests(unittest.TestCase):
    """The direct-extractor fixture with no omission, run once more under an
    active ledger and concern: the same content and an empty ledger."""

    EXTRACTORS = (("data-model", "extract_python_data_model"),
                  ("api-surface", "extract_python_api_surface_routes"),
                  ("module-graph", "extract_python_module_graph"))

    def test_each_extractor_matches_under_an_active_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            python_repo(root)
            for concern, name in self.EXTRACTORS:
                with self.subTest(concern=concern):
                    fn = getattr(PY, name)
                    direct = fn(root, "bionic")
                    with active_ledger(root, concern) as ledger:
                        under = fn(root, "bionic")
                    self.assertEqual(under, direct)
                    self.assertEqual(ledger.omissions(concern), [])
                    self.assertEqual(ledger.findings, [])

    def test_positive_control_the_wrapper_records_a_content_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            python_repo(root)
            write(root, "app/bad.py", b"\xff\n")
            with active_ledger(root, "data-model") as ledger:
                PY.extract_python_data_model(root, "bionic")
            self.assertEqual([r["path"] for r in ledger.omissions("data-model")],
                             ["app/bad.py"])


class DirectCallTests(unittest.TestCase):
    """With no active ledger the pack answers as before."""

    def test_an_unparseable_source_keeps_its_residual_line_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            python_repo(root)
            write(root, "app/broken.py", "def (\n")
            content, sources = PY.extract_python_data_model(root, "bionic")
            self.assertIn("Python's parser refused", content)
            self.assertNotIn("Omissions", content)
            self.assertIn("app/broken.py", sources)
            self.assertIsNone(CORE._ACTIVE_LEDGER.get())

    def test_an_undecodable_source_is_replacement_decoded_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            python_repo(root)
            write(root, "app/legacy.py", b"# \xff\nclass Old(Base):\n"
                                         b"    __tablename__ = 'old'\n"
                                         b"    id = Column(Integer)\n")
            content, _sources = PY.extract_python_data_model(root, "bionic")
            self.assertIn("old", content)



if __name__ == "__main__":
    unittest.main()
