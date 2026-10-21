"""Prepared writer fixtures retain history without sharing mutable test state."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import _council_gate_support as support
import _implementation_templates as templates
import test_implementation_authority as authority
import test_implementation_cycles as fixtures


class FixtureCopyTests(unittest.TestCase):
    def test_copies_preserve_history_and_isolate_files_paths_and_python_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            original = fixtures.WriterFixture(root / "original", migration=True)
            first = original.copy_to(root / "first")
            second = original.copy_to(root / "second")
            commit = support.git(original.root, "rev-parse", "HEAD")
            content = original.path.read_bytes()
            for fixture in (first, second):
                self.assertEqual(support.git(fixture.root, "rev-parse", "HEAD"), commit)
                self.assertEqual(fixture.path.read_bytes(), content)
                self.assertEqual(fixture.env.root, fixture.root)
                for value in vars(fixture).values():
                    if isinstance(value, Path):
                        self.assertTrue(value.is_relative_to(fixture.root), value)
            first.path.write_text("synthetic mutation\n")
            first.book["title"] = "Changed only in the first copy"
            first.env.hash = "changed"
            support.commit_all(first.root, "synthetic private copy mutation")
            self.assertNotEqual(support.git(first.root, "rev-parse", "HEAD"), commit)
            for fixture in (original, second):
                self.assertEqual(fixture.path.read_bytes(), content)
                self.assertEqual(support.git(fixture.root, "rev-parse", "HEAD"), commit)
                self.assertNotEqual(fixture.book["title"], first.book["title"])
                self.assertNotEqual(fixture.env.hash, first.env.hash)


class SharedTemplateTests(unittest.TestCase):
    """The shared-template helpers never hand one test's state to another."""

    def test_clone_state_moves_paths_and_refuses_text_paths_and_callables(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp).resolve() / "old", Path(temp).resolve() / "new"
            holder = type("Holder", (), {})(); holder.path = old / "a"; holder.items = [old / "b", "text"]
            moved = templates.clone_state({"holder": holder, "root": old}, old, new)
            self.assertEqual(moved["root"], new)
            self.assertEqual(moved["holder"].path, new / "a")
            self.assertEqual(moved["holder"].items, [new / "b", "text"])
            self.assertIsNot(moved["holder"], holder)
            self.assertEqual(holder.path, old / "a")  # The source is untouched.
            with self.assertRaises(AssertionError):  # A path kept as text would point at the template.
                templates.clone_state({"text": str(old / "a")}, old, new)
            with self.assertRaises(AssertionError):  # A closure would call back into the template.
                templates.clone_state({"call": lambda: old}, old, new)

    def test_merge_into_keeps_the_identity_of_unchanged_containers(self):
        state = {"entries": [{"k": 1}], "batch": {"signed": []}}
        entry, batch = state["entries"][0], state["batch"]
        templates.merge_into(state, {"entries": [{"k": 1}], "batch": {"signed": ["ref"]}, "proof": 1})
        self.assertIs(state["entries"][0], entry)
        self.assertIs(state["batch"], batch)
        self.assertEqual(state, {"entries": [{"k": 1}], "batch": {"signed": ["ref"]}, "proof": 1})

    def test_a_fixture_takes_a_registered_step_only_while_repository_and_state_equal(self):
        fixture = authority.AuthorityView("runTest"); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.assertIsNotNone(fixture._equal_template())  # Positive control: a fresh clone equals its template.
        untracked = fixture.root / "stray.txt"; untracked.write_text("not in the template\n")
        self.assertIsNone(fixture._equal_template()); untracked.unlink()
        (fixture.root / "empty-dir").mkdir()  # Git cannot see it; a restored close would drop it.
        self.assertIsNone(fixture._equal_template()); (fixture.root / "empty-dir").rmdir()
        fixture.f.book["marker"] = "changed in memory only"
        self.assertIsNone(fixture._equal_template()); del fixture.f.book["marker"]
        self.assertIsNotNone(fixture._equal_template())
        (fixture.root / "diverged.txt").write_text("committed after the build\n")
        support.commit_all(fixture.root, "synthetic divergence from the template")
        self.assertIsNone(fixture._equal_template())

    def test_untracked_content_added_before_close_makes_the_fixture_run_the_real_producer(self):
        real = authority.PublicationProof.close_for_real
        def closes(prepare):
            fixture = authority.PublicationProof(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
            prepare(fixture.root / "alternate")
            ran = []
            def counting(instance):
                ran.append(1); return real(instance)
            with mock.patch.object(authority.PublicationProof, "close_for_real", counting):
                fixture.close()
            return fixture, ran
        warm = authority.PublicationProof(); warm.setUp(); self.addCleanup(warm.doCleanups)
        warm.close()  # Builds the registered result, so the counts below see only this fixture's own close.
        fixture, ran = closes(lambda path: None)  # Positive control: nothing added, the registered result is taken.
        self.assertEqual(ran, [])
        for shape, prepare in (("file", lambda path: path.write_text("x\n")), ("empty-directory", lambda path: path.mkdir())):
            with self.subTest(shape=shape):
                fixture, ran = closes(prepare)
                self.assertEqual(ran, [1], "the cached result replaced the real producer")
                self.assertTrue((fixture.root / "alternate").exists(), "the closed repository lost the content")

    def test_two_clones_and_the_template_do_not_share_files_or_state(self):
        first = authority.AuthorityView("runTest"); first.setUp(); self.addCleanup(first.doCleanups)
        second = authority.AuthorityView("runTest"); second.setUp(); self.addCleanup(second.doCleanups)
        template = authority._prototype(authority.AuthorityView, *authority._ambient())
        before = template.snapshot()
        self.assertEqual(support.git(first.root, "rev-parse", "HEAD"), support.git(second.root, "rev-parse", "HEAD"))
        first.f.path.write_text("synthetic mutation\n"); first.f.book["marker"] = "first only"
        support.commit_all(first.root, "synthetic clone mutation")
        self.assertNotEqual(first.f.path.read_bytes(), second.f.path.read_bytes())
        self.assertNotIn("marker", second.f.book)
        self.assertEqual(template.snapshot(), before)
        self.assertNotEqual(support.git(first.root, "rev-parse", "HEAD"), support.git(template.root, "rev-parse", "HEAD"))
        self.assertTrue(first.root.is_relative_to(Path(first.temp.name).resolve()))
