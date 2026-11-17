"""ADR-0181 in the Ruby pack — absent, unreadable, unparseable and unlistable inputs.

`RubyPackLaneTests` holds the cases the core's shared reader and walk give
every pack. The classes below hold the Ruby pack's own sites: its fixed
schema, routes and routes-dump reads, its OpenAPI candidate probe, the
autoload directories a config file names, its listings (`config/environments`,
`app/` and the gemspec markers), its decode and parse sites, its oversize
residuals. The broad-handler rule covers every pack module from
`test_arch_input_failures_core.py`.

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

RB = __import__("crux.arch.packs.ruby", fromlist=["extract_ruby_data_model"])


class RubyPackLaneTests(PackLaneCases, unittest.TestCase):
    SOURCE = "lib/app/widget.rb"
    SUBDIR = "lib/app"

    def build(self, root: Path) -> None:
        write(root, "Gemfile", 'source "https://rubygems.org"\n')
        write(root, "lib/app.rb", 'require_relative "app/widget"\n')
        write(root, "lib/app/widget.rb", "module App\n  class Widget\n  end\nend\n")


_APPLICATION = (
    'require_relative "boot"\n\n'
    "module Shop\n"
    "  class Application < Rails::Application\n"
    '    config.autoload_paths << "extras"\n'
    "  end\n"
    "end\n"
)

_SCHEMA = (
    'ActiveRecord::Schema[7.1].define(version: 2026_01_01_000000) do\n'
    '  create_table "users", force: :cascade do |t|\n'
    '    t.string "name", null: false\n'
    "  end\n"
    "end\n"
)

_ROUTES_DUMP = (
    "--[ Route 1 ]-----------------\n"
    "Prefix            | items\n"
    "Verb              | GET\n"
    "URI Pattern       | /items(.:format)\n"
    "Controller#Action | items#index\n"
)


#: A Rails repository the Ruby pack populates in all three descriptive
#: concerns: `db/schema.rb` (data-model), `config/routes.rb` (api-surface) and
#: the Zeitwerk roots `app/models`, `lib` and the named `extras` (module-graph).
def ruby_repo(root: Path) -> None:
    bionic(root)
    write(root, "Gemfile", 'source "https://rubygems.org"\n')
    write(root, "config/application.rb", _APPLICATION)
    write(root, "config/environments/production.rb",
          "Rails.application.configure do\n  config.eager_load = true\nend\n")
    write(root, "config/routes.rb",
          "Rails.application.routes.draw do\n  resources :users, only: [:index]\nend\n")
    write(root, "db/schema.rb", _SCHEMA)
    write(root, "app/models/user.rb", "class User < ApplicationRecord\n  Helper\nend\n")
    write(root, "lib/helper.rb", "module Helper\nend\n")
    write(root, "extras/gadget.rb", "class Gadget\n  User\nend\n")


class _Repo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        ruby_repo(self.root)
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
        self.assertIn("`/users`", self.spine("api-surface"))
        graph = self.spine("module-graph")
        for const in ("User", "Helper", "Gadget"):
            self.assertIn(const, graph)


class AbsentTests(_Repo):

    def test_an_absent_schema_is_no_input(self):
        (self.root / "db" / "schema.rb").unlink()
        self.assert_no_omission()
        self.assertNotEqual(coverage(self.root)["data-model"]["verdict"], "populated")

    def test_an_absent_openapi_document_and_routes_dump_are_no_input(self):
        self.assert_no_omission()
        self.assertIn("config/routes.rb", self.spine("api-surface"))

    def test_an_absent_environments_directory_is_no_input(self):
        for p in (self.root / "config" / "environments").iterdir():
            p.unlink()
        (self.root / "config" / "environments").rmdir()
        self.assert_no_omission()

    def test_an_absent_autoload_directory_a_config_names_is_named_absent(self):
        for p in (self.root / "extras").iterdir():
            p.unlink()
        (self.root / "extras").rmdir()
        self.assert_omitted("extras", "absent", "absent", "module-graph")
        self.assertEqual(coverage(self.root)["module-graph"]["verdict"], "populated")

    def test_a_regular_file_at_a_named_autoload_directory_is_named_absent(self):
        for p in (self.root / "extras").iterdir():
            p.unlink()
        (self.root / "extras").rmdir()
        write(self.root, "extras", "not a directory\n")
        self.assert_omitted("extras", "absent", "absent", "module-graph")

    def test_an_interpolated_autoload_string_names_no_input(self):
        write(self.root, "config/application.rb",
              _APPLICATION.replace('"extras"', '"#{root}/extras"'))
        self.assert_no_omission()
        self.assertNotIn("Gadget", self.spine("module-graph"))

    def test_a_regular_file_at_the_app_directory_is_no_input(self):
        for p in (self.root / "app" / "models").iterdir():
            p.unlink()
        (self.root / "app" / "models").rmdir()
        (self.root / "app").rmdir()
        write(self.root, "app", "not a directory\n")
        self.assert_no_omission()
        self.assertIn("Helper", self.spine("module-graph"))


class OpenApiCandidateTests(_Repo):
    """`_ruby_openapi_path` tries `openapi.json`, then `swagger.json`, … (nits F1)."""

    SWAGGER = '{"paths": {"/pets": {"get": {"summary": "list", "tags": ["pets"]}}}}'

    def test_positive_control_an_absent_first_candidate_reads_the_second(self):
        write(self.root, "swagger.json", self.SWAGGER)
        self.assert_no_omission()
        self.assertIn("_Derived from `swagger.json`._", self.spine("api-surface"))

    def test_a_dangling_link_at_the_first_candidate_is_named_and_ends_the_probe(self):
        write(self.root, "swagger.json", self.SWAGGER)
        os.symlink("nowhere.json", self.root / "openapi.json")
        self.assert_omitted("openapi.json", "not-a-file", "symbolic-link", "api-surface")
        # The second candidate is not read in its place; the routes rung answers.
        self.assertNotIn("swagger.json", self.spine("api-surface"))
        self.assertIn("`/users`", self.spine("api-surface"))

    def test_a_directory_at_the_first_candidate_is_named_and_ends_the_probe(self):
        write(self.root, "swagger.json", self.SWAGGER)
        (self.root / "openapi.json").mkdir()
        self.assert_omitted("openapi.json", "not-a-file", "directory", "api-surface")
        self.assertNotIn("swagger.json", self.spine("api-surface"))

    def test_no_candidate_present_records_nothing(self):
        with active_ledger(self.root, "api-surface") as ledger:
            self.assertIsNone(RB._ruby_openapi_path(self.root))
        self.assertEqual(ledger.omissions("api-surface"), [])
        self.assertEqual(ledger.findings, [])


class UnreadableTests(_Repo):

    def test_an_undecodable_source_is_named_and_still_hashed(self):
        write(self.root, "lib/bad.rb", b"BAD = '\xff'\n")
        self.assert_omitted("lib/bad.rb", "undecodable", "undecodable", "module-graph")
        self.assertNotIn("`Bad`", self.spine("module-graph"))
        self.assertIn("lib/bad.rb", coverage(self.root)["module-graph"]["inputs_found"])

    def test_a_symbolic_link_source_is_named_not_a_file(self):
        os.symlink("helper.rb", self.root / "lib" / "alias.rb")
        self.assert_omitted("lib/alias.rb", "not-a-file", "symbolic-link", "module-graph")

    def test_an_oversize_source_is_named_and_not_as_a_residual(self):
        write(self.root, "lib/huge.rb", "# " + "x" * (2 * 1024 * 1024) + "\n")
        self.assert_omitted("lib/huge.rb", "over-cap", "oversize", "module-graph")
        self.assertNotIn("2 MB bound", self.spine("module-graph"))

    def test_an_undecodable_application_rb_is_named(self):
        write(self.root, "config/application.rb", _APPLICATION.encode() + b"# \xff\n")
        self.assert_omitted("config/application.rb", "undecodable", "undecodable",
                            "module-graph")

    def test_a_dangling_link_environment_file_is_named(self):
        os.symlink("nowhere.rb", self.root / "config" / "environments" / "staging.rb")
        self.assert_omitted("config/environments/staging.rb", "not-a-file",
                            "symbolic-link", "module-graph")

    def test_a_link_under_app_is_named_not_followed(self):
        os.symlink("../lib", self.root / "app" / "linked")
        self.assert_omitted("app/linked", "not-a-file", "symbolic-link", "module-graph")

    def test_an_undecodable_schema_is_named(self):
        write(self.root, "db/schema.rb", _SCHEMA.encode() + b"# \xff\n")
        self.assert_omitted("db/schema.rb", "undecodable", "undecodable", "data-model")
        self.assertNotIn("| users |", self.spine("data-model"))

    def test_a_directory_at_the_schema_is_not_a_file(self):
        (self.root / "db" / "schema.rb").unlink()
        (self.root / "db" / "schema.rb").mkdir()
        self.assert_omitted("db/schema.rb", "not-a-file", "directory", "data-model")

    def test_a_dangling_link_at_the_schema_is_not_a_file(self):
        (self.root / "db" / "schema.rb").unlink()
        os.symlink("nowhere.rb", self.root / "db" / "schema.rb")
        self.assert_omitted("db/schema.rb", "not-a-file", "symbolic-link", "data-model")

    def test_an_oversize_schema_is_named(self):
        write(self.root, "db/schema.rb", _SCHEMA + "# " + "x" * (2 * 1024 * 1024) + "\n")
        self.assert_omitted("db/schema.rb", "over-cap", "oversize", "data-model")

    def test_an_undecodable_routes_rb_is_named(self):
        write(self.root, "config/routes.rb",
              b"Rails.application.routes.draw do\n  # \xff\n  resources :users\nend\n")
        self.assert_omitted("config/routes.rb", "undecodable", "undecodable", "api-surface")
        self.assertNotIn("`/users`", self.spine("api-surface"))

    def test_a_directory_at_the_routes_dump_is_not_a_file(self):
        (self.root / "arch-inputs" / "routes.txt").mkdir(parents=True)
        self.assert_omitted("arch-inputs/routes.txt", "not-a-file", "directory",
                            "api-surface")
        self.assertIn("`/users`", self.spine("api-surface"))

    def test_an_undecodable_routes_dump_is_named(self):
        write(self.root, "arch-inputs/routes.txt", _ROUTES_DUMP.encode() + b"\xff\n")
        self.assert_omitted("arch-inputs/routes.txt", "undecodable", "undecodable",
                            "api-surface")

    def test_positive_control_a_regular_routes_dump_is_read(self):
        write(self.root, "arch-inputs/routes.txt", _ROUTES_DUMP)
        self.assert_no_omission()
        self.assertIn("`/items`", self.spine("api-surface"))

    def test_a_mode_000_schema_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / "db" / "schema.rb", 0)
        self.assert_refused(1, "db/schema.rb")

    def test_a_mode_000_routes_rb_is_a_document_finding(self):
        skip_if_root(self)
        os.chmod(self.root / "config" / "routes.rb", 0)
        self.assert_refused(1, "config/routes.rb")

    def test_a_fifo_at_the_schema_is_an_environment_failure(self):
        (self.root / "db" / "schema.rb").unlink()
        os.mkfifo(self.root / "db" / "schema.rb")
        self.assert_refused(2, "db/schema.rb")


class UnparseableTests(_Repo):

    def test_an_unparseable_openapi_json_is_named(self):
        write(self.root, "openapi.json", "{not json")
        self.assert_omitted("openapi.json", "unparseable", "unparseable", "api-surface")

    def test_a_routes_dump_with_no_record_is_named_and_the_next_rung_answers(self):
        write(self.root, "arch-inputs/routes.txt", "not a routes dump\n")
        self.assert_omitted("arch-inputs/routes.txt", "unparseable", "unparseable",
                            "api-surface")
        self.assertIn("`/users`", self.spine("api-surface"))

    def test_a_memory_error_while_parsing_routes_exits_2(self):
        with mock.patch.object(RB, "_ruby_ts_parse", side_effect=MemoryError()):
            code, out, _payload, err = run_cli(self.root)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("config/routes.rb", err)
        self.assertIn("MemoryError", err)
        self.assertEqual(arch_snapshot(self.root), self.before)

    def test_a_content_failure_while_parsing_routes_is_named(self):
        with mock.patch.object(RB, "_ruby_ts_parse", side_effect=RecursionError()):
            self.assert_omitted("config/routes.rb", "unparseable", "unparseable",
                                "api-surface")


class UnlistableTests(_Repo):

    def test_an_unlistable_environments_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / "config" / "environments", 0o300)   # searchable, not listable
        self.assert_refused(2, "config/environments")

    def test_an_unlistable_app_directory_is_an_environment_failure(self):
        skip_if_root(self)
        os.chmod(self.root / "app", 0o300)
        self.assert_refused(2, "app")

    # The shared walk or an earlier listing reaches an unlistable directory
    # first in a derive, so the pack's own listing sites are driven directly
    # under an active ledger.

    def test_the_environments_listing_raises_the_environment_lane(self):
        skip_if_root(self)
        env = self.root / "config" / "environments"
        os.chmod(env, 0o300)
        with active_ledger(self.root, "module-graph"):
            with self.assertRaises(CORE.ArchEnvironmentFailure) as caught:
                RB._autoload_roots(self.root, self.root)
        self.assertTrue(any(line.startswith("config/environments:")
                            for line in caught.exception.failures),
                        caught.exception.failures)
        os.chmod(env, 0o755)
        with active_ledger(self.root, "module-graph"):        # positive control
            roots, _residuals = RB._autoload_roots(self.root, self.root)
        self.assertIn(self.root / "lib", roots)

    def test_the_gemspec_listing_raises_the_environment_lane(self):
        skip_if_root(self)
        write(self.root, "shop.gemspec", "Gem::Specification.new\n")
        self.assertEqual(RB.detect(self.root).markers, ("Gemfile", "shop.gemspec"))
        os.chmod(self.root, 0o300)
        try:
            with active_ledger(self.root, None):
                with self.assertRaises(CORE.ArchEnvironmentFailure):
                    RB.detect(self.root)
            # Outside a derive the listing answers as the glob did: no gemspec.
            self.assertEqual(RB.detect(self.root).markers, ("Gemfile",))
        finally:
            os.chmod(self.root, 0o755)


class LedgerParityTests(unittest.TestCase):
    """The direct-extractor fixture with no omission, run once more under an
    active ledger and concern: the same content and an empty ledger."""

    EXTRACTORS = (("data-model", "extract_ruby_data_model"),
                  ("api-surface", "extract_ruby_api_surface_routes"),
                  ("module-graph", "extract_ruby_module_graph"))

    def test_each_extractor_matches_under_an_active_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            ruby_repo(root)
            for concern, name in self.EXTRACTORS:
                with self.subTest(concern=concern):
                    fn = getattr(RB, name)
                    direct = fn(root, "bionic")
                    with active_ledger(root, concern) as ledger:
                        under = fn(root, "bionic")
                    self.assertEqual(under, direct)
                    self.assertEqual(ledger.omissions(concern), [])
                    self.assertEqual(ledger.findings, [])

    def test_positive_control_the_wrapper_records_a_content_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            ruby_repo(root)
            write(root, "lib/bad.rb", b"\xff\n")
            with active_ledger(root, "module-graph") as ledger:
                RB.extract_ruby_module_graph(root, "bionic")
            self.assertEqual([r["path"] for r in ledger.omissions("module-graph")],
                             ["lib/bad.rb"])


class DirectCallTests(unittest.TestCase):
    """With no active ledger the pack answers as before."""

    def test_an_oversize_source_keeps_its_residual_line_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            ruby_repo(root)
            write(root, "lib/huge.rb", "# " + "x" * (2 * 1024 * 1024) + "\n")
            content, _sources = RB.extract_ruby_module_graph(root, "bionic")
            self.assertIn("Skipped for exceeding the 2 MB bound: `lib/huge.rb`", content)
            self.assertNotIn("Omissions", content)
            self.assertIsNone(CORE._ACTIVE_LEDGER.get())

    def test_an_undecodable_source_is_replacement_decoded_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            ruby_repo(root)
            write(root, "lib/legacy.rb", b"# \xff\nmodule Legacy\n  Helper\nend\n")
            content, sources = RB.extract_ruby_module_graph(root, "bionic")
            self.assertIn("Legacy", content)
            self.assertIn("lib/legacy.rb", sources)

    def test_an_unparseable_routes_dump_falls_through_in_silence_without_a_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            ruby_repo(root)
            write(root, "arch-inputs/routes.txt", "not a routes dump\n")
            self.assertFalse(RB._detect_ruby_routes_artifact(root))



if __name__ == "__main__":
    unittest.main()
