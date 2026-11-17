"""ADR-0181 in the Elixir pack — absent, unreadable, unparseable and unlistable inputs.

`ElixirPackLaneTests` holds the cases the core's shared reader and walk give
every pack. The classes below hold the Elixir pack's own sites: its OpenAPI
candidate probe, its `router.ex` candidates, the walked `.ex` sources, the
fixed `priv/repo/migrations/` directory and its listing, its decode,
tree-sitter parse and comment-scrub sites, its three aggregate scan caps, its
oversize, scan-cap and scrub-bail residuals. The broad-handler rule covers
every pack module from `test_arch_input_failures_core.py`.

Each case derives a fixture through `derive-arch.py` and asserts the lane: an
omission named in the map and in `coverage.json` with exit 0, a document
finding with exit 1, or an environment failure with exit 2. Every refusing
case asserts the byte-unchanged arch tree, and the clean derive of the same
fixture in `setUp` is the positive control.
"""

from __future__ import annotations

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

ELIXIR = __import__("crux.arch.packs.elixir", fromlist=["extract_elixir_module_graph"])


class ElixirPackLaneTests(PackLaneCases, unittest.TestCase):
    SOURCE = "lib/app/widget.ex"
    SUBDIR = "lib/app"

    def build(self, root: Path) -> None:
        write(root, "mix.exs", "defmodule App.MixProject do\n  use Mix.Project\nend\n")
        write(root, "lib/app.ex", "defmodule App do\n  alias App.Widget\nend\n")
        write(root, "lib/app/widget.ex", "defmodule App.Widget do\n  def f, do: 1\nend\n")


_MIX = "defmodule App.MixProject do\n  use Mix.Project\nend\n"

_APP = (
    "defmodule App do\n"
    "  alias App.Accounts.User\n"
    "  def u, do: User.new()\n"
    "end\n"
)

_USER = (
    "defmodule App.Accounts.User do\n"
    "  use Ecto.Schema\n"
    '  schema "users" do\n'
    "    field :email, :string\n"
    "  end\n"
    "  def new, do: 1\n"
    "end\n"
)

_ROUTER = (
    "defmodule AppWeb.Router do\n"
    "  use Phoenix.Router\n"
    '  scope "/", AppWeb do\n'
    '    get "/items", ItemController, :index\n'
    "  end\n"
    "end\n"
)

_MIGRATION = (
    "defmodule App.Repo.Migrations.CreateUsers do\n"
    "  use Ecto.Migration\n"
    "  def change do\n"
    "    create table(:users) do\n"
    "      add :email, :string\n"
    "    end\n"
    "  end\n"
    "end\n"
)

#: A source whose comment scrub cannot close its string (`_ElixirScrubBail`).
_BAIL = 'defmodule App.Bad do\n  @x "unterminated\nend\n'

_BIG = 2 * 1024 * 1024

_MIGS = "priv/repo/migrations"
_MIG = f"{_MIGS}/20200101000000_create_users.exs"


#: A Phoenix repository the pack populates in all three descriptive concerns:
#: an Ecto schema (data-model), a router with one route (api-surface) and an
#: alias with a remote reference between two of its modules (module-graph).
def elixir_repo(root: Path) -> None:
    bionic(root)
    write(root, "mix.exs", _MIX)
    write(root, "lib/app.ex", _APP)
    write(root, "lib/app/accounts/user.ex", _USER)
    write(root, "lib/app_web/router.ex", _ROUTER)


#: An Elixir repository whose only data-model input is its migrations, so the
#: schema probe does not fire and the migration replay answers.
def migrations_repo(root: Path) -> None:
    bionic(root)
    write(root, "mix.exs", _MIX)
    write(root, "lib/app.ex", "defmodule App do\n  def f, do: 1\nend\n")
    write(root, _MIG, _MIGRATION)


class _Repo(unittest.TestCase):
    FIXTURE = staticmethod(elixir_repo)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.FIXTURE(self.root)
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

    def described(self, concern: str) -> str:
        """The spine file without its Omissions section."""
        return self.spine(concern).split("## Omissions")[0]

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
        self.assertIn("| users |", self.spine("data-model"))
        self.assertIn("`/items`", self.spine("api-surface"))
        graph = self.spine("module-graph")
        self.assertIn("-->", graph)
        self.assertIn("App.Accounts.User", graph)


class AbsentTests(_Repo):

    def test_an_absent_openapi_document_is_no_input(self):
        self.assert_no_omission()
        self.assertIn("`/items`", self.spine("api-surface"))

    def test_no_openapi_candidate_present_records_nothing(self):
        with active_ledger(self.root, "api-surface") as ledger:
            self.assertIsNone(ELIXIR._elixir_openapi_path(self.root))
        self.assertEqual(ledger.omissions("api-surface"), [])
        self.assertEqual(ledger.findings, [])

    def test_an_absent_router_is_no_input(self):
        (self.root / "lib" / "app_web" / "router.ex").unlink()
        self.assert_no_omission()
        self.assertNotEqual(coverage(self.root)["api-surface"]["verdict"], "populated")

    def test_an_absent_migrations_directory_is_no_input(self):
        self.assert_no_omission()
        with active_ledger(self.root, "data-model") as ledger:
            self.assertIsNone(ELIXIR._elixir_migrations_dir(self.root))
        self.assertEqual(ledger.omissions("data-model"), [])


class OpenApiCandidateTests(_Repo):
    """`_elixir_openapi_path` tries `openapi.json`, then `swagger.json`, … (nits F1)."""

    SWAGGER = '{"paths": {"/pets": {"get": {"summary": "list", "tags": ["pets"]}}}}'

    def test_positive_control_an_absent_first_candidate_reads_the_second(self):
        write(self.root, "swagger.json", self.SWAGGER)
        self.assert_no_omission()
        self.assertIn("_Derived from `swagger.json`._", self.spine("api-surface"))

    def test_a_dangling_link_at_the_first_candidate_is_named_and_ends_the_probe(self):
        write(self.root, "swagger.json", self.SWAGGER)
        os.symlink("nowhere.json", self.root / "openapi.json")
        self.assert_omitted("openapi.json", "not-a-file", "symbolic-link", "api-surface")
        # The second candidate is not read in its place; the router answers.
        self.assertNotIn("swagger.json", self.spine("api-surface"))
        self.assertIn("`/items`", self.spine("api-surface"))

    def test_a_directory_at_the_first_candidate_is_named_and_ends_the_probe(self):
        write(self.root, "swagger.json", self.SWAGGER)
        (self.root / "openapi.json").mkdir()
        self.assert_omitted("openapi.json", "not-a-file", "directory", "api-surface")
        self.assertNotIn("swagger.json", self.spine("api-surface"))

    def test_a_mode_000_openapi_document_is_a_document_finding(self):
        skip_if_root(self)
        write(self.root, "openapi.json", self.SWAGGER)
        self.derive_ok()
        self.before = arch_snapshot(self.root)
        os.chmod(self.root / "openapi.json", 0)
        self.assert_refused(1, "openapi.json")

    def test_an_undecodable_openapi_document_is_named(self):
        write(self.root, "openapi.json", self.SWAGGER.encode() + b" \xff")
        self.assert_omitted("openapi.json", "undecodable", "undecodable", "api-surface")
        self.assertNotIn("`/pets`", self.spine("api-surface"))


class UnreadableTests(_Repo):

    def test_an_undecodable_source_is_named_and_still_hashed(self):
        write(self.root, "lib/bad.ex", b"defmodule App.Bad do\n  @x '\xff'\nend\n")
        self.assert_omitted("lib/bad.ex", "undecodable", "undecodable",
                            "module-graph", "data-model")
        self.assertNotIn("App.Bad", self.described("module-graph"))
        self.assertIn("lib/bad.ex", coverage(self.root)["module-graph"]["inputs_found"])
        # The router scan's byte prefilter rules the file out before any
        # decode: it cannot be a router, so api-surface omits nothing.
        self.assertEqual(self.omissions("api-surface"), [])

    def test_a_symbolic_link_source_is_named_not_a_file(self):
        os.symlink("accounts/user.ex", self.root / "lib" / "app" / "alias.ex")
        self.assert_omitted("lib/app/alias.ex", "not-a-file", "symbolic-link",
                            "module-graph", "data-model")

    def test_an_oversize_source_is_named_and_not_as_a_residual(self):
        write(self.root, "lib/huge.ex", "# " + "x" * _BIG + "\n")
        self.assert_omitted("lib/huge.ex", "over-cap", "oversize",
                            "module-graph", "data-model")
        self.assertNotIn("2 MB bound", self.spine("module-graph"))
        self.assertNotIn("2 MB bound", self.spine("data-model"))

    def test_an_undecodable_router_is_named_and_the_concern_stubs(self):
        write(self.root, "lib/app_web/router.ex", _ROUTER.encode() + b"# \xff\n")
        self.assert_omitted("lib/app_web/router.ex", "undecodable", "undecodable",
                            "api-surface")
        self.assertNotIn("`/items`", self.spine("api-surface"))
        self.assertIn("lib/app_web/router.ex",
                      coverage(self.root)["api-surface"]["inputs_found"])

    def test_a_linked_router_is_named_and_is_no_candidate(self):
        real = self.root / "lib" / "app_web" / "router.ex"
        real.rename(self.root / "lib" / "app_web" / "real_router.ex")
        os.symlink("real_router.ex", real)
        self.assert_omitted("lib/app_web/router.ex", "not-a-file", "symbolic-link",
                            "api-surface")
        # The real file still declares the router, and the parse finds it.
        self.assertIn("`lib/app_web/real_router.ex`", self.described("api-surface"))


class UnparseableTests(_Repo):

    def test_an_unparseable_openapi_json_is_named(self):
        write(self.root, "openapi.json", "{not json")
        self.assert_omitted("openapi.json", "unparseable", "unparseable", "api-surface")

    def test_a_scrub_bail_is_named_and_not_as_a_residual(self):
        write(self.root, "lib/bad.ex", _BAIL)
        self.assert_omitted("lib/bad.ex", "unparseable", "scrub-bail",
                            "module-graph", "data-model")
        self.assertNotIn("scrub bailed", self.spine("module-graph"))
        self.assertNotIn("scrub bailed", self.spine("data-model"))
        self.assertIn("lib/bad.ex", coverage(self.root)["module-graph"]["inputs_found"])

    def test_a_memory_error_while_parsing_the_router_exits_2(self):
        with mock.patch.object(ELIXIR, "_elixir_parse", side_effect=MemoryError()):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("lib/app_web/router.ex", err)
        self.assertIn("MemoryError", err)
        self.assertEqual(arch_snapshot(self.root), self.before)

    def test_a_content_failure_while_parsing_the_router_is_named(self):
        with mock.patch.object(ELIXIR, "_elixir_parse", side_effect=RecursionError()):
            self.assert_omitted("lib/app_web/router.ex", "unparseable", "unparseable",
                                "api-surface")
        self.assertNotIn("`/items`", self.spine("api-surface"))


class MigrationTests(_Repo):
    """The fixed `priv/repo/migrations/` directory and its `*.exs` listing."""

    FIXTURE = staticmethod(migrations_repo)

    def test_positive_control_the_migrations_populate_the_data_model(self):
        self.assert_no_omission()
        self.assertIn("| users |", self.spine("data-model"))

    def test_an_undecodable_migration_is_named_and_still_hashed(self):
        write(self.root, _MIG, _MIGRATION.encode() + b"# \xff\n")
        self.assert_omitted(_MIG, "undecodable", "undecodable", "data-model")
        self.assertNotIn("| users |", self.spine("data-model"))
        self.assertIn(_MIG, coverage(self.root)["data-model"]["inputs_found"])

    def test_a_linked_migration_is_named_not_a_file(self):
        os.symlink(Path(_MIG).name, self.root / _MIGS / "20200102000000_alias.exs")
        self.assert_omitted(f"{_MIGS}/20200102000000_alias.exs", "not-a-file",
                            "symbolic-link", "data-model")
        self.assertIn("| users |", self.described("data-model"))

    def test_a_directory_named_like_a_migration_is_not_a_file(self):
        (self.root / _MIGS / "20200102000000_odd.exs").mkdir()
        self.assert_omitted(f"{_MIGS}/20200102000000_odd.exs", "not-a-file",
                            "directory", "data-model")

    def test_a_content_failure_while_parsing_a_migration_is_named(self):
        with mock.patch.object(ELIXIR, "_parse_elixir_migration",
                               side_effect=RecursionError()):
            self.assert_omitted(_MIG, "unparseable", "unparseable", "data-model")
        self.assertNotIn("syntax error", self.spine("data-model"))

    def test_a_mode_000_migration_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / _MIG, 0)
        self.assert_refused(1, _MIG)

    def test_a_fifo_migration_is_an_environment_failure(self):
        os.mkfifo(self.root / _MIGS / "20200102000000_trap.exs")
        self.assert_refused(2, f"{_MIGS}/20200102000000_trap.exs")

    def test_an_unlistable_migrations_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / _MIGS, 0o300)      # searchable, not listable
        self.assert_refused(2, _MIGS)

    def test_outside_a_derive_an_unlistable_migrations_directory_has_no_files(self):
        skip_if_root(self)
        os.chmod(self.root / _MIGS, 0o300)
        self.assertEqual(ELIXIR._elixir_migration_files(self.root / _MIGS), [])

    def test_a_dangling_link_at_the_migrations_directory_is_not_a_file(self):
        migs = self.root / _MIGS
        migs.rename(self.root / "priv" / "repo" / "elsewhere")
        os.symlink("nowhere", migs)
        self.assert_omitted(_MIGS, "not-a-file", "symbolic-link", "data-model")

    def test_a_regular_file_at_the_migrations_directory_is_no_input(self):
        migs = self.root / _MIGS
        (migs / Path(_MIG).name).unlink()
        migs.rmdir()
        write(self.root, _MIGS, "not a directory\n")
        self.assert_no_omission()
        self.assertNotEqual(coverage(self.root)["data-model"]["verdict"], "populated")

    def test_an_absent_migrations_directory_is_no_input(self):
        (self.root / _MIG).unlink()
        (self.root / _MIGS).rmdir()
        self.assert_no_omission()


class ScanCapTests(_Repo):
    """The three aggregate scan caps (`_scan_ex_files`, `_elixir_scan_contains`,
    `_elixir_router_files`) are counted over-cap omissions over the sorted walk
    (ADR-0181 approach 8), one record per loop (nit F5)."""

    def test_the_source_scan_cap_names_the_skipped_count_and_drops_the_residual_line(self):
        with mock.patch.object(ELIXIR, "_MAX_SCAN_FILES", 1):
            self.derive_ok()
        caps = [r for r in self.omissions("module-graph") if "cap" in r]
        self.assertEqual(caps, [{"cap": "_MAX_SCAN_FILES", "dir": ".", "skipped": 2,
                                 "reason": "over-cap", "kind": "scan-cap"}])
        text = self.spine("module-graph")
        self.assertIn("- scan cap `_MAX_SCAN_FILES` under `.` skipped 2 input(s)", text)
        self.assertNotIn("Aggregate scan cap reached", text)

    def test_positive_control_without_a_ledger_the_residual_line_renders(self):
        with mock.patch.object(ELIXIR, "_MAX_SCAN_FILES", 1):
            _entries, _sources, residuals = ELIXIR._scan_ex_files(self.root)
        self.assertTrue(any("Aggregate scan cap reached" in r for r in residuals))

    def test_the_detector_scan_caps_are_counted_per_loop(self):
        with mock.patch.object(ELIXIR, "_MAX_SCAN_FILES", 1):
            with active_ledger(self.root, "api-surface") as ledger:
                self.assertFalse(ELIXIR._elixir_scan_contains(
                    self.root, ELIXIR._ELIXIR_HAS_SCHEMA_RE))
                # `router.ex` is still found by name; only the `.ex` scan caps.
                ELIXIR._elixir_router_files(self.root)
        caps = [(r["cap"], r["skipped"]) for r in ledger.omissions("api-surface")]
        # Sorted walk: `lib/app.ex` is read, the other two `.ex` are skipped.
        self.assertEqual(caps, [("_MAX_SCAN_FILES", 2), ("_MAX_SCAN_FILES", 2)])

    def test_positive_control_a_detector_under_its_cap_records_nothing(self):
        with active_ledger(self.root, "api-surface") as ledger:
            self.assertTrue(ELIXIR._elixir_scan_contains(
                self.root, ELIXIR._ELIXIR_HAS_SCHEMA_RE))
            self.assertEqual(len(ELIXIR._elixir_router_files(self.root)), 1)
        self.assertEqual(ledger.omissions("api-surface"), [])


class LedgerParityTests(unittest.TestCase):
    """The direct-extractor fixture with no omission, run once more under an
    active ledger and concern: the same content and an empty ledger."""

    EXTRACTORS = ((elixir_repo, "data-model", "extract_elixir_data_model"),
                  (elixir_repo, "api-surface", "extract_elixir_api_surface_router"),
                  (elixir_repo, "module-graph", "extract_elixir_module_graph"),
                  (migrations_repo, "data-model", "extract_elixir_migrations"))

    def test_each_extractor_matches_under_an_active_ledger(self):
        for fixture, concern, name in self.EXTRACTORS:
            with self.subTest(extractor=name), tempfile.TemporaryDirectory() as d:
                root = Path(d).resolve()
                fixture(root)
                fn = getattr(ELIXIR, name)
                direct = fn(root, "bionic")
                with active_ledger(root, concern) as ledger:
                    under = fn(root, "bionic")
                self.assertEqual(under, direct)
                self.assertEqual(ledger.omissions(concern), [])
                self.assertEqual(ledger.findings, [])

    def test_positive_control_the_wrapper_records_a_content_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            elixir_repo(root)
            write(root, "lib/bad.ex", b"\xff\n")
            with active_ledger(root, "module-graph") as ledger:
                ELIXIR.extract_elixir_module_graph(root, "bionic")
            self.assertEqual([r["path"] for r in ledger.omissions("module-graph")],
                             ["lib/bad.ex"])


class DirectCallTests(unittest.TestCase):
    """With no active ledger the pack answers as before."""

    def _root(self, d: str) -> Path:
        root = Path(d).resolve()
        elixir_repo(root)
        return root

    def test_an_oversize_source_keeps_its_residual_line_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            write(root, "lib/huge.ex", "# " + "x" * _BIG + "\n")
            content, _sources = ELIXIR.extract_elixir_module_graph(root, "bionic")
            self.assertIn("Skipped for exceeding the 2 MB bound: `lib/huge.ex`", content)
            self.assertNotIn("Omissions", content)
            self.assertIsNone(CORE._ACTIVE_LEDGER.get())

    def test_an_undecodable_source_is_replacement_decoded_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            write(root, "lib/legacy.ex",
                  b"# \xff\ndefmodule App.Legacy do\n  def f, do: App.Accounts.User.new()\nend\n")
            content, sources = ELIXIR.extract_elixir_module_graph(root, "bionic")
            self.assertIn("App.Legacy", content)
            self.assertIn("lib/legacy.ex", sources)

    def test_a_scrub_bail_keeps_its_residual_line_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            write(root, "lib/bad.ex", _BAIL)
            graph, _ = ELIXIR.extract_elixir_module_graph(root, "bionic")
            model, _ = ELIXIR.extract_elixir_data_model(root, "bionic")
            for content in (graph, model):
                self.assertIn("scrub bailed (hashed, not parsed): `lib/bad.ex`", content)

    def test_the_marker_is_the_exists_predicate_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            self.assertFalse(ELIXIR.detect(root).matched)
            (root / "mix.exs").mkdir()
            self.assertEqual(ELIXIR.detect(root).markers, ("mix.exs",))



if __name__ == "__main__":
    unittest.main()
