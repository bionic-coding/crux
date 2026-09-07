"""Tests for extract-code-docs.py.

Covers the regressions fixed in this pass:

  1. `_atomic_write_text` writes the requested bytes and uses os.replace
     (so the target either has the new content or the old, never partial).
  2. `build_manifest` no longer stamps a per-row `extracted_at` field.
  3. `write_pages` prune does NOT touch files outside `output_dir` (even
     when a symlink under output_dir points at an outside file).
  4. `write_pages` prune handles `.md` files reachable only through a
     symlink: the symlink itself can be unlinked, the real target outside
     the tree is preserved.

Stdlib only (unittest, tempfile, os, importlib, pathlib, json, sys).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # crux repo
SCRIPT_PATH = REPO_ROOT / "crux" / "scripts" / "extract-code-docs.py"


def _load_dispatcher():
    """Import extract-code-docs.py as a module (the hyphen breaks regular import)."""
    spec = importlib.util.spec_from_file_location("extract_code_docs_dispatcher", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["extract_code_docs_dispatcher"] = mod
    spec.loader.exec_module(mod)
    return mod


dispatcher = _load_dispatcher()


class AtomicWriteTextTests(unittest.TestCase):
    def test_writes_utf8_bytes_without_newline_translation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            body = "alpha\nbeta\n— omega\n"  # includes a non-ASCII char
            dispatcher._atomic_write_text(target, body)
            # Read back as bytes to verify no '\r\n' got injected.
            self.assertEqual(target.read_bytes(), body.encode("utf-8"))

    def test_tmp_file_is_cleaned_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            dispatcher._atomic_write_text(target, "hello")
            # No leftover .tmp sibling.
            sibs = sorted(p.name for p in Path(tmp).iterdir())
            self.assertEqual(sibs, ["out.txt"])

    def test_replaces_existing_file_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.txt"
            target.write_text("OLD", encoding="utf-8")
            dispatcher._atomic_write_text(target, "NEW")
            self.assertEqual(target.read_text(encoding="utf-8"), "NEW")

    def test_a_pre_created_tmp_symlink_is_refused(self):
        # [SECURITY:S5] The third of three byte-identical siblings, found by a
        # fail-closed sweep rather than by diff review — this file was not in
        # the diff that fixed the first one.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "victim.txt"
            victim.write_text("VICTIM\n", encoding="utf-8")
            target = root / "out.txt"
            (root / "out.txt.tmp").symlink_to(victim)
            with self.assertRaises(OSError):
                dispatcher._atomic_write_text(target, "GENERATED")
            self.assertEqual(victim.read_text(encoding="utf-8"), "VICTIM\n")
            self.assertFalse(target.exists())

    def test_a_target_that_is_already_a_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "victim.txt"
            victim.write_text("VICTIM\n", encoding="utf-8")
            target = root / "out.txt"
            target.symlink_to(victim)
            with self.assertRaises(OSError):
                dispatcher._atomic_write_text(target, "GENERATED")
            self.assertEqual(victim.read_text(encoding="utf-8"), "VICTIM\n")
            self.assertTrue(target.is_symlink())


class BuildManifestTests(unittest.TestCase):
    def test_no_extracted_at_in_rows(self):
        page = dispatcher.DocPage(
            title="Foo",
            path="elixir/Foo.md",
            body="# Foo\n",
            source_path="lib/foo.ex",
        )
        manifest = dispatcher.build_manifest([page])
        self.assertEqual(len(manifest["pages"]), 1)
        row = manifest["pages"][0]
        self.assertNotIn("extracted_at", row)
        # Sanity: the content-stable fields still exist.
        self.assertEqual(row["source_path"], "lib/foo.ex")
        self.assertEqual(row["doc_path"], "elixir/Foo.md")
        self.assertIn("sha256", row)
        self.assertIn("extractor_version", row)

    def test_manifest_is_byte_stable_across_calls(self):
        page = dispatcher.DocPage(
            title="Foo", path="elixir/Foo.md", body="# Foo\n", source_path="lib/foo.ex"
        )
        a = json.dumps(dispatcher.build_manifest([page]), sort_keys=True)
        b = json.dumps(dispatcher.build_manifest([page]), sort_keys=True)
        self.assertEqual(a, b)


class WritePagesPruneTests(unittest.TestCase):
    def test_prune_removes_stale_md_files_inside_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "code"
            out.mkdir()
            stale = out / "elixir" / "Old.md"
            stale.parent.mkdir(parents=True)
            stale.write_text("# stale\n", encoding="utf-8")

            page = dispatcher.DocPage(
                title="New", path="elixir/New.md", body="# new\n", source_path="lib/new.ex"
            )
            dispatcher.write_pages([page], out, verbose=False)

            self.assertFalse(stale.exists(), "stale .md inside output_dir should be pruned")
            self.assertTrue((out / "elixir" / "New.md").is_file())

    def test_prune_does_not_touch_files_outside_output_dir(self):
        """A symlink under output_dir pointing OUTSIDE must not cause unlink
        of the outside target. We unlink the symlink itself (it's inside),
        but never reach through to delete the real outside file."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "code"
            out.mkdir()
            outside_dir = Path(tmp) / "outside"
            outside_dir.mkdir()
            outside_file = outside_dir / "DoNotDelete.md"
            outside_file.write_text("# precious\n", encoding="utf-8")

            # Place a symlink inside out/ that points at outside_file.
            link = out / "Linked.md"
            try:
                link.symlink_to(outside_file)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not supported on this platform")

            page = dispatcher.DocPage(
                title="Keep", path="elixir/Keep.md", body="# keep\n", source_path="lib/keep.ex"
            )
            dispatcher.write_pages([page], out, verbose=False)

            # The outside target MUST still exist regardless of what we did
            # to the symlink.
            self.assertTrue(
                outside_file.exists(),
                "file outside output_dir must never be unlinked by the pruner",
            )
            self.assertEqual(
                outside_file.read_text(encoding="utf-8"),
                "# precious\n",
                "outside target contents must be untouched",
            )

    def test_prune_respects_resolved_kept_set_for_index_and_meta(self):
        """index.md and _meta/manifest.json under the output dir must not
        be pruned even though they aren't in the input page list."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "code"
            out.mkdir()
            meta_dir = out / "_meta"
            meta_dir.mkdir()
            (meta_dir / "manifest.json").write_text("{}", encoding="utf-8")
            (out / "index.md").write_text("# old index\n", encoding="utf-8")

            page = dispatcher.DocPage(
                title="X", path="elixir/X.md", body="# x\n", source_path="lib/x.ex"
            )
            dispatcher.write_pages([page], out, verbose=False)

            # write_pages regenerates index.md but does NOT touch manifest.json
            # (that's write_meta's job). Both must still exist post-prune.
            self.assertTrue((out / "index.md").is_file())
            self.assertTrue((meta_dir / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
