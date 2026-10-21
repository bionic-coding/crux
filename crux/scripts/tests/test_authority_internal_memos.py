"""The repeated work CYC-0030 removed from the authority readers changes no verdict.

Each memo here stores only a success, keyed to inputs it re-checks, and never a refusal:

* `binding_memo` answers a repeated historical migration binding proof inside a git-read scope.
* `signed_baseline_memo` and `implementation_migration._signed_baseline_at` read one publication
  commit's signed baseline once per process.
* `retained_evidence.holding_root_for_path` is a function of two spellings.
* `observation_admission.context_reuse` shares one admission context across a read-only phase.
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import _council_gate_support as sup
import binding_memo
import git_read_cache
import implementation_approval as ap
import implementation_migration as migration
import observation_admission as admission
import retained_evidence
import signed_baseline_memo

SCRIPTS = Path(__file__).resolve().parent.parent


def age(root: Path) -> None:
    """Make every working-tree path older than the memo's racy window."""
    old = time.time() - 3600
    for current, dirs, files in os.walk(root):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in dirs + files:
            os.utime(os.path.join(current, name), (old, old), follow_symlinks=False)
        os.utime(current, (old, old))
    # The memo also covers the git directory's ignore file, which `git init` writes just before the test.
    exclude = root / ".git" / "info" / "exclude"
    if exclude.exists():
        os.utime(exclude, (old, old))


class BindingFixture(unittest.TestCase):
    """A git repository with a run file, a council record and a stand-in proof function."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = sup.init_repo(Path(temp.name) / "repo")
        self.run_dir = self.root / "bionic/promptbooks/runs/PB-1-example"
        (self.run_dir / "council").mkdir(parents=True)
        (self.root / "bionic/promptbooks/active").mkdir(parents=True)
        self.run = self.run_dir / "run-RUN-001.yaml"
        self.run.write_text("state: closed\n")
        self.record = self.run_dir / "council/record.json"
        self.record.write_text('{"outcome": "ran"}\n')
        sup.commit_all(self.root, "fixture")
        age(self.root)
        self.calls = 0
        self.behaviour = "prove"
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(ap, "validate_historical_migration_binding", self.prove).start()

    def prove(self, repo_root, run_path, *, slot, batch_path, batch_sha256):
        self.calls += 1
        text = Path(run_path).read_text()
        names = sorted(p.name for p in (Path(run_path).parent / "council").iterdir())
        if self.behaviour == "refuse":
            raise ap.Refused("approval-evidence-invalid")
        if self.behaviour == "child":
            subprocess.run([sys.executable, "-c", "pass"], check=True)
        return ap.ValidatedBinding({"book_id": "PB-1-example", "run_id": "RUN-001", "text": text},
                                   {"slot": slot}, {"names": names}, {}, "0" * 40)

    def ask(self, *, run=None):
        return binding_memo.validate_historical_migration_binding(
            self.root, run or self.run, slot="implementation-1", batch_path="b.yaml", batch_sha256="a" * 64)


class BindingMemoTests(BindingFixture):
    def test_outside_a_scope_every_call_proves(self):
        self.ask(); self.ask()
        self.assertEqual(self.calls, 2)

    def test_a_repeat_inside_a_scope_is_answered_from_memory_as_a_copy(self):
        with git_read_cache.scope():
            first = self.ask(); second = self.ask()
        self.assertEqual(self.calls, 1)
        self.assertEqual(first, second)
        self.assertIsNot(first.binding, second.binding)

    def test_an_entry_keeps_alive_the_proof_function_whose_identity_keys_it(self):
        with git_read_cache.scope():
            self.ask()
            entries = list(git_read_cache.scope_memo("historical-migration-binding").values())
        self.assertEqual(len(entries), 1)
        self.assertIs(entries[0]["prove"], ap.validate_historical_migration_binding)

    def test_the_memo_ends_with_the_outermost_scope(self):
        with git_read_cache.scope():
            self.ask()
        with git_read_cache.scope():
            self.ask()
        self.assertEqual(self.calls, 2)

    def test_a_refusal_is_never_remembered(self):
        self.behaviour = "refuse"
        with git_read_cache.scope():
            for _ in range(2):
                with self.assertRaises(ap.Refused) as caught:
                    self.ask()
                self.assertEqual(caught.exception.code, "approval-evidence-invalid")
            self.assertEqual(self.calls, 2)
            self.behaviour = "prove"
            self.ask(); self.ask()
            self.assertEqual(self.calls, 3)

    def test_a_new_commit_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            (self.root / "other.txt").write_text("x\n")
            sup.commit_all(self.root, "next")
            self.ask()
        self.assertEqual(self.calls, 2)

    def test_an_edited_run_file_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            self.run.write_text("state: reopened\n")
            self.assertEqual(self.ask().binding["text"], "state: reopened\n")
        self.assertEqual(self.calls, 2)

    def test_a_same_size_rewrite_that_restores_the_mtime_of_a_young_file_is_a_miss(self):
        young = time.time() - 1.0
        self.run.write_text("state: closed\n"); os.utime(self.run, (young, young))
        with git_read_cache.scope():
            self.ask()
            self.run.write_text("state: CLOSED\n"); os.utime(self.run, (young, young))
            self.assertEqual(self.ask().binding["text"], "state: CLOSED\n")
        self.assertEqual(self.calls, 2)

    def test_a_new_record_in_the_run_directory_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            (self.run_dir / "council/second.json").write_text("{}\n")
            self.assertEqual(self.ask().run["names"], ["record.json", "second.json"])
        self.assertEqual(self.calls, 2)

    def test_a_record_replaced_by_a_link_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            council = self.run_dir / "council"
            moved = self.run_dir / "moved"
            council.rename(moved); council.symlink_to(moved)
            self.ask()
        self.assertEqual(self.calls, 2)

    def test_the_other_book_tier_appearing_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            archive = self.root / "bionic/promptbooks/archive"
            archive.mkdir(); (archive / "PB-1-example.yaml").write_text("id: x\n")
            self.ask()
        self.assertEqual(self.calls, 2)

    def test_a_pending_council_copy_appearing_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            pending = self.root / ".git/crux/council-pending/PB-1-example/RUN-001"
            pending.mkdir(parents=True); (pending / "copy.json").write_text("{}\n")
            self.ask()
        self.assertEqual(self.calls, 2)

    def test_a_proof_that_started_another_program_is_not_stored(self):
        self.behaviour = "child"
        with git_read_cache.scope():
            self.ask(); self.ask()
        self.assertEqual(self.calls, 2)

    def test_an_input_modified_just_before_the_proof_is_not_stored(self):
        self.record.write_text('{"outcome": "ran", "n": 2}\n')
        with git_read_cache.scope():
            self.ask(); self.ask()
            self.assertEqual(self.calls, 2)
            age(self.root)
            self.ask(); self.ask()
        self.assertEqual(self.calls, 3)

    def test_a_replaced_proof_function_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            replacement = mock.Mock(side_effect=ap.Refused("approval-evidence-invalid"))
            with mock.patch.object(ap, "validate_historical_migration_binding", replacement):
                with self.assertRaises(ap.Refused):
                    self.ask()
        self.assertEqual(self.calls, 1)
        self.assertEqual(replacement.call_count, 1)

    def test_a_changed_environment_is_a_miss(self):
        with git_read_cache.scope():
            self.ask()
            with mock.patch.dict(os.environ, {"CRUX_B4_MEMO_PROBE": "1"}):
                self.ask()
        self.assertEqual(self.calls, 2)

    def test_a_tree_without_readable_git_state_is_never_remembered(self):
        (self.root / ".git/commondir").write_text("..\n")
        with git_read_cache.scope():
            self.ask(); self.ask()
        self.assertEqual(self.calls, 2)


class SignedBaselineTests(unittest.TestCase):
    def setUp(self):
        signed_baseline_memo.forget(); self.addCleanup(signed_baseline_memo.forget)
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = sup.init_repo(Path(temp.name) / "repo")
        (self.root / "a.txt").write_text("one\n"); sup.commit_all(self.root, "first")
        self.first = sup.git(self.root, "rev-parse", "HEAD").strip()
        (self.root / "a.txt").write_text("two\n"); sup.commit_all(self.root, "second")
        self.second = sup.git(self.root, "rev-parse", "HEAD").strip()
        self.clones = 0
        self.behaviour = "read"
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(migration, "_revision_repository", self.clone).start()
        mock.patch.object(migration, "_signed_inventory", self.inventory).start()
        mock.patch.object(migration, "_configuration", lambda repo: SimpleNamespace(docs_root=Path("bionic"))).start()

    @contextlib.contextmanager
    def clone(self, repo, revision):
        self.clones += 1
        yield repo

    def inventory(self, repo, tree):
        if self.behaviour == "refuse":
            raise ap.Refused("migration-signed-ledger-refused")
        return [{"path": "ledger", "sha256": "0" * 64}], []

    def test_a_commit_is_read_from_a_clone_once(self):
        first = migration._signed_baseline_at(self.root, self.first)
        second = migration._signed_baseline_at(self.root, self.first)
        self.assertEqual(self.clones, 1)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        first[0]["sha256"] = "changed"
        self.assertEqual(migration._signed_baseline_at(self.root, self.first)[0]["sha256"], "0" * 64)

    def test_a_branch_name_and_the_full_id_share_one_entry(self):
        migration._signed_baseline_at(self.root, "main")
        migration._signed_baseline_at(self.root, self.second)
        self.assertEqual(self.clones, 1)

    def test_another_commit_is_a_miss(self):
        migration._signed_baseline_at(self.root, self.first)
        migration._signed_baseline_at(self.root, self.second)
        self.assertEqual(self.clones, 2)

    def test_a_refused_read_is_never_remembered(self):
        self.behaviour = "refuse"
        for _ in range(2):
            with self.assertRaises(ap.Refused) as caught:
                migration._signed_baseline_at(self.root, self.first)
            self.assertEqual(caught.exception.code, "migration-signed-ledger-refused")
        self.assertEqual(self.clones, 2)
        self.behaviour = "read"
        migration._signed_baseline_at(self.root, self.first)
        migration._signed_baseline_at(self.root, self.first)
        self.assertEqual(self.clones, 3)

    def test_an_unknown_revision_still_refuses_beside_a_stored_commit(self):
        migration._signed_baseline_at(self.root, self.first)
        with self.assertRaises(ap.Refused) as caught:
            migration._signed_baseline_at(self.root, "f" * 40)
        self.assertEqual(caught.exception.code, "migration-query-revision-refused")

    def test_a_shallow_repository_still_refuses_beside_a_stored_commit(self):
        migration._signed_baseline_at(self.root, self.second)
        shallow = self.root.parent / "shallow"
        sup.git(self.root.parent, "clone", "-q", "--depth", "1", "file://" + str(self.root), str(shallow))
        with self.assertRaises(ap.Refused) as caught:
            migration._signed_baseline_at(shallow, self.second)
        self.assertEqual(caught.exception.code, "history-unavailable")

    def test_only_a_full_commit_id_is_stored(self):
        signed_baseline_memo.remember("main", [{"path": "x"}])
        self.assertIsNone(signed_baseline_memo.recall("main"))

    def test_the_memo_is_bounded(self):
        for index in range(signed_baseline_memo._LIMIT + 5):
            signed_baseline_memo.remember("%040x" % index, [])
        self.assertIsNone(signed_baseline_memo.recall("%040x" % 0))
        self.assertIsNotNone(signed_baseline_memo.recall("%040x" % (signed_baseline_memo._LIMIT + 4)))


class HoldingRootTests(unittest.TestCase):
    ROOT = Path("/project/bionic")
    TAIL = "evidence/implementation-cycles/retained-repositories"
    HOLDING = ROOT / "promptbooks/runs/PB-0001-example" / TAIL / "file.txt"

    def setUp(self):
        retained_evidence.holding_root_for_path.cache_clear()

    def test_it_answers_the_same_as_the_uncached_function(self):
        uncached = retained_evidence.holding_root_for_path.__wrapped__
        samples = [(self.ROOT, self.HOLDING), (self.ROOT, self.ROOT / "adrs/ADR-0001.md"),
                   (self.ROOT, Path("/elsewhere/x")), (Path("/project/bionic/"), self.HOLDING)]
        for docs_root, path in samples:
            with self.subTest(path=str(path)):
                self.assertEqual(retained_evidence.holding_root_for_path(docs_root, path),
                                 uncached(docs_root, path))
        self.assertEqual(retained_evidence.holding_root_for_path(self.ROOT, self.HOLDING),
                         self.ROOT / "promptbooks/runs/PB-0001-example" / self.TAIL)

    def test_a_repeat_is_answered_from_memory(self):
        retained_evidence.holding_root_for_path(self.ROOT, self.HOLDING)
        retained_evidence.holding_root_for_path(self.ROOT, self.HOLDING)
        info = retained_evidence.holding_root_for_path.cache_info()
        self.assertEqual((info.hits, info.misses), (1, 1))

    def test_it_reads_no_file_and_lists_no_directory(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("filesystem access")
        fresh = self.ROOT / "promptbooks/runs/PB-0002-other" / self.TAIL / "x"
        with mock.patch("os.stat", forbidden), mock.patch("os.lstat", forbidden), \
                mock.patch("os.scandir", forbidden), mock.patch("builtins.open", forbidden):
            self.assertEqual(retained_evidence.holding_root_for_path(self.ROOT, fresh),
                             self.ROOT / "promptbooks/runs/PB-0002-other" / self.TAIL)

    def test_a_refusal_is_raised_on_every_call_and_never_stored(self):
        refusals = [(self.ROOT, self.ROOT / "promptbooks/runs/not-a-book" / self.TAIL / "x"),
                    (Path("/project/../bionic"), self.HOLDING), (Path("relative"), self.HOLDING),
                    (self.ROOT, Path("/project/bionic/a\x00b"))]
        for docs_root, path in refusals:
            for _ in range(2):
                with self.subTest(path=repr(str(path))), self.assertRaises(retained_evidence.RetainedEvidenceRefusal):
                    retained_evidence.holding_root_for_path(docs_root, path)
        self.assertEqual(retained_evidence.holding_root_for_path.cache_info().currsize, 0)


class _ContextReuseCase(unittest.TestCase):
    MANIFEST = 'schema_version: "5"\nconcerns_enabled: [adrs, observations]\n'

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / "repo"
        (self.root / "bionic/observations").mkdir(parents=True)
        (self.root / ".bionic.yml").write_text("docs_dir: bionic\n")
        (self.root / "bionic/manifest.yml").write_text(self.MANIFEST)
        self.builds = 0
        self.fail_next = False
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(admission, "_complete_context_inputs", self.build).start()

    def build(self, layout, sp, migration_module):
        self.builds += 1
        if self.fail_next:
            self.fail_next = False
            raise admission.AdmissionRefusal("admission-input-changed")
        return {"built": self.builds, "source_io": layout["source_io"]}

    def layout(self):
        layout = admission._load_layout(self.root)
        self.addCleanup(layout["source_io"].close)
        return layout


class ContextReuseTests(_ContextReuseCase):
    def test_without_a_reuse_phase_every_call_builds(self):
        layout = self.layout()
        admission._complete_context(layout); admission._complete_context(layout)
        self.assertEqual(self.builds, 2)

    def test_inside_a_phase_one_operation_builds_once(self):
        layout = self.layout()
        with admission.context_reuse():
            first = admission._complete_context(layout)
            second = admission._complete_context(layout)
        self.assertEqual(self.builds, 1)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)

    def test_a_nested_phase_shares_the_outer_one(self):
        layout = self.layout()
        with admission.context_reuse():
            admission._complete_context(layout)
            with admission.context_reuse():
                admission._complete_context(layout)
        self.assertEqual(self.builds, 1)

    def test_another_operation_builds_its_own_context(self):
        with admission.context_reuse():
            admission._complete_context(self.layout()); admission._complete_context(self.layout())
        self.assertEqual(self.builds, 2)

    def test_a_refused_build_is_never_remembered(self):
        layout = self.layout()
        with admission.context_reuse():
            self.fail_next = True
            for _ in range(1):
                with self.assertRaises(admission.AdmissionRefusal):
                    admission._complete_context(layout)
            admission._complete_context(layout)
            admission._complete_context(layout)
        self.assertEqual(self.builds, 2)

    def test_an_input_changed_after_the_context_refuses_instead_of_serving_it(self):
        layout = self.layout()
        with admission.context_reuse():
            admission._complete_context(layout)
            (self.root / "bionic/manifest.yml").write_text(self.MANIFEST + "# edited\n")
            with self.assertRaises(admission.SourceIORefusal):
                admission._complete_context(layout)
        self.assertEqual(self.builds, 1)

    def test_a_new_commit_builds_again(self):
        sup.init_repo(self.root)
        sup.commit_all(self.root, "one")
        layout = self.layout()
        with admission.context_reuse():
            admission._complete_context(layout)
            (self.root / "later.txt").write_text("x\n"); sup.commit_all(self.root, "two")
            admission._complete_context(layout)
        self.assertEqual(self.builds, 2)

    def test_a_repository_whose_state_cannot_be_read_exactly_is_never_reused(self):
        sup.init_repo(self.root)
        sup.commit_all(self.root, "one")
        (self.root / ".git/commondir").write_text("..\n")
        layout = self.layout()
        with admission.context_reuse():
            admission._complete_context(layout); admission._complete_context(layout)
        self.assertEqual(self.builds, 2)


class SourceIOContextReuseTests(_ContextReuseCase):
    """The path every recorded-source check takes: a fresh layout on the shared operation."""

    def context_for(self, source_io):
        return admission._context_for_source_io(self.root, _source_io=source_io)

    def test_a_recorded_source_check_reuses_the_phase_context(self):
        source_io = admission._AdmissionIO(self.root); self.addCleanup(source_io.close)
        with admission.context_reuse():
            for _ in range(3):
                self.context_for(source_io)
        self.assertEqual(self.builds, 1)

    def test_a_recorded_source_check_refuses_when_an_input_changed(self):
        source_io = admission._AdmissionIO(self.root); self.addCleanup(source_io.close)
        with admission.context_reuse():
            self.context_for(source_io)
            (self.root / "bionic/manifest.yml").write_text(self.MANIFEST + "# edited\n")
            with self.assertRaises(admission.SourceIORefusal):
                self.context_for(source_io)
        self.assertEqual(self.builds, 1)


class ContractBytesMemoTests(unittest.TestCase):
    PINNED = {"2": ap.SUPPORTED_PROFILES["2"].contract_sha256, "3": ap.SUPPORTED_PROFILES["3"].contract_sha256,
              "4": ap.SUPPORTED_PROFILES["4"].contract_sha256}

    def setUp(self):
        import contract_bytes_memo
        self.memo = contract_bytes_memo
        self.memo.forget(); self.addCleanup(self.memo.forget)
        self.addCleanup(mock.patch.stopall)

    def counted(self):
        real = ap._gate_contract_bytes
        calls = []

        def walk(version=ap.CONTRACT_VERSION):
            calls.append(version)
            return real(version)
        mock.patch.object(ap, "_gate_contract_bytes", walk).start()
        return calls

    def test_the_walk_runs_once_per_unchanged_policy_and_the_bytes_stay_pinned(self):
        calls = self.counted()
        import hashlib
        for version in ("2", "3", "4"):
            first = ap.gate_contract_bytes(version); second = ap.gate_contract_bytes(version)
            self.assertIs(first, second)
            self.assertEqual(hashlib.sha256(first).hexdigest(), self.PINNED[version])
            self.assertEqual(ap.production_contract_bytes(version), first)
        self.assertEqual(calls, ["2", "3", "4"])

    def test_a_replaced_policy_module_is_a_miss_and_its_bytes_differ(self):
        import council_history_v3 as v3
        original = ap.gate_contract_bytes("3")
        self.assertEqual(ap.gate_contract_bytes("3"), original)
        calls = self.counted()
        with mock.patch.object(v3, "start_snapshot_yaml", types_module("owned_yaml_stand_in")):
            changed = None
            try:
                changed = ap.gate_contract_bytes("3")
            except ap.Refused:
                pass
        self.assertEqual(calls, ["3"])
        self.assertNotEqual(changed, original)
        self.assertEqual(ap.gate_contract_bytes("3"), original)
        self.assertEqual(calls, ["3"])

    def test_a_replaced_global_is_a_miss(self):
        import council_history_v4 as v4
        ap.gate_contract_bytes("4")
        calls = self.counted()
        with mock.patch.object(v4, "VERSION", "4-probe"):
            try:
                ap.gate_contract_bytes("4")
            except ap.Refused:
                pass
        self.assertEqual(calls, ["4"])

    def test_an_edited_source_file_changes_the_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "policy_stand_in.py"
            path.write_text("VALUE = 1\n")
            spec = importlib.util.spec_from_file_location("policy_stand_in", path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            before = self.memo.key("4", [module])
            self.assertEqual(self.memo.key("4", [module]), before)
            path.write_text("VALUE = 2\n")
            self.assertNotEqual(self.memo.key("4", [module]), before)

    def test_a_named_file_that_changes_changes_the_key(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / "schema.json"
            data.write_text("{}\n")
            module = types_module("holder"); module.SCHEMA = data
            before = self.memo.key("4", [module])
            data.write_text('{"a": 1}\n')
            self.assertNotEqual(self.memo.key("4", [module]), before)

    def test_a_replaced_reader_function_is_a_miss(self):
        ap.gate_contract_bytes("2")
        calls = self.counted()
        read = Path.read_bytes
        with mock.patch.object(Path, "read_bytes", lambda path: read(path)):
            ap.gate_contract_bytes("2")
        self.assertEqual(calls, ["2"])

    def test_a_key_keeps_alive_every_object_whose_identity_it_holds(self):
        import gc
        import weakref

        def reader(path):
            return b""
        probe = weakref.ref(reader)
        module = types_module("holder")
        with mock.patch.object(Path, "read_bytes", reader):
            memo_key = self.memo.key("4", [module])
        del reader
        gc.collect()
        self.assertIsNotNone(probe(), "the key let an identity it holds be reused by a later object")
        self.assertTrue(any(item is probe() for item in memo_key.refs[0]))

    def test_a_refused_walk_is_never_remembered(self):
        real = ap._gate_contract_bytes
        outcomes = []

        def walk(version=ap.CONTRACT_VERSION):
            outcomes.append(version)
            if len(outcomes) == 1:
                raise ap.Refused("context-policy-unavailable")
            return real(version)
        with mock.patch.object(ap, "_gate_contract_bytes", walk):
            with self.assertRaises(ap.Refused) as caught:
                ap.gate_contract_bytes("4")
            self.assertEqual(caught.exception.code, "context-policy-unavailable")
            content = ap.gate_contract_bytes("4")
            self.assertEqual(ap.gate_contract_bytes("4"), content)
        self.assertEqual(outcomes, ["4", "4"])

    def test_an_unsupported_version_refuses_on_every_call(self):
        for _ in range(2):
            with self.assertRaises(ap.Refused) as caught:
                ap.gate_contract_bytes("5")
            self.assertEqual(caught.exception.code, "context-version-unsupported")


def types_module(name):
    import types
    return types.ModuleType(name)


class SignoffBuildPlanScopeTests(unittest.TestCase):
    def test_build_plan_runs_its_phase_inside_a_context_reuse_scope(self):
        spec = importlib.util.spec_from_file_location("signoff_survey_under_test", SCRIPTS / "signoff-survey.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        seen = []

        def phase(ctx):
            seen.append(admission._CONTEXT_REUSE.get() is not None)
            return "sheet", []
        with mock.patch.object(module, "_build_plan", phase):
            self.assertEqual(module.build_plan({}), ("sheet", []))
        self.assertEqual(seen, [True])
        self.assertIsNone(admission._CONTEXT_REUSE.get())


if __name__ == "__main__":
    unittest.main()
