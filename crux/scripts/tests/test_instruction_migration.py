"""Tests for instruction_migration.py — the AGENTS.md discovery and migration contract.

Written before the implementation, per PB-0115 prompt 2.

The properties under test are the ones five council rounds rejected earlier designs
for. Each names the failure it exists to prevent:

- discovery's MUTATION set is the tracked files of ONE checkout, so a vendored
  dependency cache and a linked worktree are outside it by construction
- discovery's SUPPRESSION set is wider than the mutation set and includes untracked
  files, because a file crux must not touch can still silence the canonical one.
  No `governs` entry projects this clause; it is the safety property most likely to
  be missed by an implementer reading only the rule table
- deduplication matches on (heading path, bytes), never bytes alone, so a block is
  never silently REPARENTED while the accounting still balances
- the accounting balances as retained + synthesized + resolved, and refuses otherwise
- a `#` inside a fenced code block opens no block
- staging is per file and a rerun converges
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "crux" / "scripts" / "instruction_migration.py"
ENTRY = REPO_ROOT / "crux" / "scripts" / "migrate-instructions.py"

_spec = importlib.util.spec_from_file_location("instruction_migration", MODULE)
im = importlib.util.module_from_spec(_spec)
sys.modules["instruction_migration"] = im
_spec.loader.exec_module(im)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TempRepo(unittest.TestCase):
    """A repo root whose tracked set is injected, so most tests need no git."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def discover(self, tracked=None, denylist=(), cwd=None):
        """Discovery with an injected tracked set (the git call is the one seam)."""
        if tracked is None:
            tracked = [
                p.relative_to(self.root).as_posix()
                for p in self.root.rglob("*")
                if p.is_file() and ".git" not in p.parts
            ]
        return im.discover(
            self.root,
            tracked_files=tracked,
            denylist=list(denylist),
            working_dir=cwd or self.root,
        )


# ---------------------------------------------------------------- block parsing


class BlockParsingTests(unittest.TestCase):
    def test_preamble_carries_the_empty_heading_path(self):
        blocks = im.split_blocks("intro text\n\n# One\nbody\n")
        self.assertEqual(blocks[0].path, ())
        self.assertIn("intro text", blocks[0].text)
        self.assertEqual(blocks[1].path, ("One",))

    def test_heading_path_is_the_full_ancestry(self):
        blocks = im.split_blocks("# A\n## B\n### C\nbody\n")
        self.assertEqual([b.path for b in blocks], [("A",), ("A", "B"), ("A", "B", "C")])

    def test_a_hash_inside_a_fenced_code_block_opens_no_block(self):
        text = "# Real\n```\n# Not a heading\n```\nafter\n"
        blocks = im.split_blocks(text)
        self.assertEqual([b.path for b in blocks], [("Real",)])
        self.assertIn("# Not a heading", blocks[0].text)

    def test_a_tilde_fence_also_suppresses_headings(self):
        blocks = im.split_blocks("# Real\n~~~\n# Nope\n~~~\n")
        self.assertEqual([b.path for b in blocks], [("Real",)])

    def test_a_hash_inside_an_html_comment_opens_no_block(self):
        blocks = im.split_blocks("# Real\n<!--\n# Nope\n-->\nafter\n")
        self.assertEqual([b.path for b in blocks], [("Real",)])

    def test_a_hash_in_an_indented_code_block_opens_no_block(self):
        blocks = im.split_blocks("# Real\n\n    # indented not a heading\n\nafter\n")
        self.assertEqual([b.path for b in blocks], [("Real",)])

    def test_a_setext_heading_opens_a_block(self):
        blocks = im.split_blocks("Title\n=====\nbody\n\nSub\n---\nmore\n")
        self.assertEqual([b.path for b in blocks], [("Title",), ("Title", "Sub")])

    def test_a_setext_underline_inside_a_fence_opens_no_block(self):
        blocks = im.split_blocks("# Real\n```\nTitle\n=====\n```\n")
        self.assertEqual([b.path for b in blocks], [("Real",)])


# ------------------------------------------------------------------- discovery


class DiscoveryTests(TempRepo):
    def test_matching_is_case_insensitive_over_the_three_names(self):
        for name in ("AGENTS.md", "CLAUDE.md", "Claude.MD", "claude.local.md"):
            self.assertTrue(im.is_instruction_name(name), name)
        for name in ("AGENT.md", "CLAUDE.markdown", "README.md", "CLAUDE.md.tmpl"):
            self.assertFalse(im.is_instruction_name(name), name)

    def test_an_untracked_file_is_never_in_the_mutation_set(self):
        _write(self.root / "CLAUDE.md", "tracked\n")
        _write(self.root / "vendor" / "CLAUDE.md", "untracked\n")
        d = self.discover(tracked=["CLAUDE.md"])
        self.assertEqual([p.as_posix() for p in d.managed_paths()], ["CLAUDE.md"])

    def test_a_vendored_cache_and_a_worktree_are_outside_the_tracked_set(self):
        _write(self.root / "CLAUDE.md", "real\n")
        _write(self.root / ".cache" / "dep" / "CLAUDE.md", "vendored\n")
        _write(self.root / ".cache" / "dep" / "AGENTS.md", "vendored\n")
        _write(self.root / "wt" / "copy" / "CLAUDE.md", "worktree\n")
        d = self.discover(tracked=["CLAUDE.md"])
        self.assertEqual([p.as_posix() for p in d.managed_paths()], ["CLAUDE.md"])

    def test_a_template_is_excluded_by_path_and_keeps_its_bytes(self):
        t = _write(self.root / "crux" / "templates" / "CLAUDE.md", "tmpl\n")
        before = t.read_bytes()
        d = self.discover(tracked=["crux/templates/CLAUDE.md"])
        self.assertEqual(d.managed_paths(), [])
        self.assertEqual(d.disposition("crux/templates/CLAUDE.md"), "excluded:template")
        self.assertEqual(t.read_bytes(), before)

    def test_a_denylisted_fixture_is_excluded_and_named(self):
        rel = "crux/scripts/tests/fixtures/trips/CLAUDE.md"
        _write(self.root / rel, "fixture\n")
        d = self.discover(tracked=[rel], denylist=[rel])
        self.assertEqual(d.managed_paths(), [])
        self.assertEqual(d.disposition(rel), "excluded:denylist")

    def test_an_absent_denylist_is_empty_rather_than_an_error(self):
        _write(self.root / "CLAUDE.md", "x\n")
        d = im.discover(self.root, tracked_files=["CLAUDE.md"], denylist=None,
                        working_dir=self.root)
        self.assertEqual([p.as_posix() for p in d.managed_paths()], ["CLAUDE.md"])

    def test_claude_local_md_is_excluded_by_name_even_when_tracked(self):
        _write(self.root / "CLAUDE.local.md", "private\n")
        d = self.discover(tracked=["CLAUDE.local.md"])
        self.assertEqual(d.managed_paths(), [])
        self.assertEqual(d.disposition("CLAUDE.local.md"), "excluded:local-override")

    def test_a_dot_claude_claude_md_is_excluded_by_path_even_when_tracked(self):
        """Renaming it would silence it: no host is known to load .claude/AGENTS.md."""
        _write(self.root / ".claude" / "CLAUDE.md", "dot claude\n")
        d = self.discover(tracked=[".claude/CLAUDE.md"])
        self.assertEqual(d.managed_paths(), [])
        self.assertEqual(d.disposition(".claude/CLAUDE.md"), "excluded:dot-claude")

    def test_a_symlink_is_never_followed_and_keeps_its_bytes(self):
        _write(self.root / "real.md", "target\n")
        link = self.root / "CLAUDE.md"
        os.symlink(self.root / "real.md", link)
        d = self.discover(tracked=["CLAUDE.md", "real.md"])
        self.assertEqual(d.managed_paths(), [])
        self.assertEqual(d.disposition("CLAUDE.md"), "excluded:symlink")
        self.assertTrue(link.is_symlink())


class SuppressionScanTests(TempRepo):
    """Clause 5. No governs entry projects this; it is the clause most likely missed.

    The mutation set is tracked files. The suppression set is wider and includes
    untracked ones, because a file crux must not touch can still silence the
    canonical file.
    """

    def test_an_untracked_suppressor_is_reported_though_it_is_not_mutable(self):
        _write(self.root / "AGENTS.md", "canonical\n")
        _write(self.root / "CLAUDE.local.md", "private\n")
        d = self.discover(tracked=["AGENTS.md"])
        self.assertIn("CLAUDE.local.md", [s.path.as_posix() for s in d.suppressors])
        self.assertEqual(d.disposition("CLAUDE.local.md"), "excluded:untracked")
        self.assertNotIn("CLAUDE.local.md",
                         [p.as_posix() for p in d.managed_paths()])
        self.assertEqual(im.build_plan(d).actions, [],
                         "a canonical-only scope needs no action")

    def test_the_scan_covers_the_whole_checkout_not_one_ancestor_chain(self):
        """A private bionic/CLAUDE.local.md silences the tree for anyone inside it."""
        _write(self.root / "AGENTS.md", "canonical\n")
        _write(self.root / "bionic" / "CLAUDE.local.md", "private\n")
        d = self.discover(tracked=["AGENTS.md"], cwd=self.root)
        found = [s.path.as_posix() for s in d.suppressors]
        self.assertIn("bionic/CLAUDE.local.md", found)

    def test_a_tracked_legacy_claude_md_is_also_a_suppressor_until_migrated(self):
        _write(self.root / "AGENTS.md", "canonical\n")
        _write(self.root / "CLAUDE.md", "legacy\n")
        d = self.discover(tracked=["AGENTS.md", "CLAUDE.md"])
        self.assertIn("CLAUDE.md", [s.path.as_posix() for s in d.suppressors])

    def test_on_chain_and_off_chain_suppressors_are_distinguished(self):
        _write(self.root / "AGENTS.md", "canonical\n")
        _write(self.root / "bionic" / "CLAUDE.local.md", "off chain from root\n")
        _write(self.root / "CLAUDE.local.md", "on chain\n")
        d = self.discover(tracked=["AGENTS.md"], cwd=self.root)
        by_path = {s.path.as_posix(): s for s in d.suppressors}
        self.assertTrue(by_path["CLAUDE.local.md"].on_chain)
        self.assertFalse(by_path["bionic/CLAUDE.local.md"].on_chain)

    def test_a_deeper_working_directory_puts_the_tree_file_on_the_chain(self):
        _write(self.root / "AGENTS.md", "canonical\n")
        _write(self.root / "bionic" / "CLAUDE.local.md", "private\n")
        d = self.discover(tracked=["AGENTS.md"], cwd=self.root / "bionic")
        by_path = {s.path.as_posix(): s for s in d.suppressors}
        self.assertTrue(by_path["bionic/CLAUDE.local.md"].on_chain)

    def test_the_scan_skips_a_nested_checkout_below_the_root_but_not_the_root(self):
        _write(self.root / "CLAUDE.local.md", "mine\n")
        nested = self.root / "wt" / "copy"
        _write(nested / "CLAUDE.local.md", "theirs\n")
        (nested / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        (self.root / ".git").mkdir(exist_ok=True)
        d = self.discover(tracked=[])
        found = [s.path.as_posix() for s in d.suppressors]
        self.assertIn("CLAUDE.local.md", found)
        self.assertNotIn("wt/copy/CLAUDE.local.md", found)


# ----------------------------------------------------------------------- merge


class MergeTests(unittest.TestCase):
    def test_identical_blocks_at_the_same_path_are_emitted_once(self):
        r = im.merge_documents("# A\nbody\n", "# A\nbody\n")
        self.assertEqual(r.text.count("# A"), 1)
        self.assertFalse(r.flags)

    def test_unique_content_from_both_sources_survives(self):
        r = im.merge_documents("# Only A\naaa\n", "# Only C\nccc\n")
        self.assertIn("Only A", r.text)
        self.assertIn("Only C", r.text)
        self.assertIn("aaa", r.text)
        self.assertIn("ccc", r.text)

    def test_a_repeated_paragraph_block_appears_once(self):
        shared = "# Shared\npara one\n\npara two\n"
        r = im.merge_documents(shared + "# A\naaa\n", shared + "# C\nccc\n")
        self.assertEqual(r.text.count("para one"), 1)
        self.assertEqual(r.text.count("para two"), 1)

    def test_semantic_similarity_is_never_treated_as_duplication(self):
        r = im.merge_documents("# A\nRun the tests.\n", "# C\nRun the test suite.\n")
        self.assertIn("Run the tests.", r.text)
        self.assertIn("Run the test suite.", r.text)

    def test_identical_bytes_under_different_parents_are_two_blocks(self):
        """Dedupe matches on (path, bytes). Bytes alone would conflate these."""
        a = "# Alpha\n## Note\nsame body\n"
        c = "# Beta\n## Note\nsame body\n"
        r = im.merge_documents(a, c)
        self.assertEqual(r.text.count("same body"), 2)

    def test_a_colliding_heading_path_with_differing_bodies_is_flagged(self):
        r = im.merge_documents("# Setup\nuse make\n", "# Setup\nuse just\n")
        kinds = {f.kind for f in r.flags}
        self.assertIn("overlap", kinds)

    def test_an_overlap_is_flagged_and_never_resolved(self):
        r = im.merge_documents("# Setup\nuse make\n", "# Setup\nuse just\n")
        self.assertTrue(r.flags)
        self.assertFalse(r.applied, "an overlap must not auto-apply")

    def test_the_council_reparenting_example_is_escalated_not_taken(self):
        """AGENTS: General, JavaScript. CLAUDE: General, General/Security.

        The naive ordering rule appends Security after JavaScript, moving it from
        General/Security to JavaScript/Security while every block still records as
        retained or deduplicated. That is the defect this test pins.
        """
        a = "# General\nG\n# JavaScript\nJ\n"
        c = "# General\nG\n## Security\nS\n"
        r = im.merge_documents(a, c)
        self.assertIn("reparent", {f.kind for f in r.flags})
        self.assertFalse(r.applied)

    def test_a_child_from_the_other_source_is_placed_under_its_own_ancestry(self):
        a = "# Alpha\nA\n"
        c = "# Gamma\n## Child\nC\n"
        r = im.merge_documents(a, c)
        self.assertTrue(r.applied, r.flags)
        placed = {row.result_path for row in r.receipt_rows if row.result_path}
        self.assertIn(("Gamma", "Child"), placed)

    def test_a_placed_block_keeps_its_source_heading_path(self):
        a = "# Alpha\nA\n"
        c = "# Gamma\n## Child\nC\n"
        r = im.merge_documents(a, c)
        for row in r.receipt_rows:
            if row.disposition == "retained":
                self.assertEqual(row.source_path, row.result_path, row)

    def test_the_accounting_balances_retained_plus_synthesized_plus_resolved(self):
        a = "# Alpha\nA\n# Shared\nS\n"
        c = "# Shared\nS\n# Gamma\n## Child\nC\n"
        r = im.merge_documents(a, c)
        self.assertTrue(r.applied, r.flags)
        self.assertTrue(r.accounting_balances(), r.accounting())

    def test_a_reviewed_resolution_replaces_divergent_siblings_without_data_loss(self):
        a = "# Setup\nuse make\n"
        c = "# Setup\nuse just\n"
        resolution = {("Setup",): "# Setup\nuse make, or just where make is absent\n"}
        r = im.merge_documents(a, c, resolutions=resolution)
        self.assertTrue(r.applied, r.flags)
        self.assertIn("use make, or just where make is absent", r.text)
        self.assertIn("resolved", {row.disposition for row in r.receipt_rows})
        self.assertTrue(r.accounting_balances(), r.accounting())

    def test_every_source_block_gets_a_disposition(self):
        a = "# Alpha\nA\n# Shared\nS\n"
        c = "# Shared\nS\n# Gamma\nG\n"
        r = im.merge_documents(a, c)
        n_source = len(im.split_blocks(a)) + len(im.split_blocks(c))
        rows = [row for row in r.receipt_rows if row.disposition != "synthesized"]
        self.assertEqual(len(rows), n_source)
        self.assertTrue(all(row.disposition for row in rows))

    def test_source_order_is_preserved_within_each_source(self):
        a = "# A1\nx\n# A2\ny\n"
        c = "# C1\nz\n# C2\nw\n"
        r = im.merge_documents(a, c)
        order = [r.text.index(h) for h in ("# A1", "# A2", "# C1", "# C2")]
        self.assertEqual(order, sorted(order))


# ------------------------------------------------------------------- planning


class PlanValidationTests(TempRepo):
    def test_a_lone_managed_claude_md_plans_a_byte_preserving_rename(self):
        _write(self.root / "CLAUDE.md", "exact bytes\n")
        plan = im.build_plan(self.discover(tracked=["CLAUDE.md"]))
        self.assertEqual([a.kind for a in plan.actions], ["rename"])
        self.assertTrue(plan.valid, plan.errors)

    def test_a_case_variant_plans_a_normalizing_rename(self):
        _write(self.root / "Claude.md", "v\n")
        plan = im.build_plan(self.discover(tracked=["Claude.md"]))
        self.assertEqual(plan.actions[0].kind, "rename")
        self.assertEqual(plan.actions[0].dest.name, "AGENTS.md")

    def test_an_agents_case_variant_normalizes_to_the_exact_spelling(self):
        _write(self.root / "Agents.md", "v\n")
        plan = im.build_plan(self.discover(tracked=["Agents.md"]))
        self.assertEqual(plan.actions[0].dest.name, "AGENTS.md")

    def test_two_names_in_one_case_folded_family_are_an_ambiguity(self):
        _write(self.root / "CLAUDE.md", "one\n")
        _write(self.root / "Claude.md", "two\n")
        d = self.discover(tracked=["CLAUDE.md", "Claude.md"])
        plan = im.build_plan(d)
        self.assertFalse(plan.valid)
        self.assertTrue(any("ambiguous" in e.lower() for e in plan.errors), plan.errors)

    def test_identical_siblings_plan_a_collapse(self):
        _write(self.root / "AGENTS.md", "same\n")
        _write(self.root / "CLAUDE.md", "same\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        self.assertEqual([a.kind for a in plan.actions], ["collapse"])
        self.assertTrue(plan.valid)

    def test_differing_siblings_plan_a_merge(self):
        _write(self.root / "AGENTS.md", "# A\naaa\n")
        _write(self.root / "CLAUDE.md", "# C\nccc\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        self.assertEqual([a.kind for a in plan.actions], ["merge"])
        self.assertTrue(plan.valid)

    def test_an_unresolved_conflict_blocks_its_own_scope_and_no_other(self):
        _write(self.root / "AGENTS.md", "# Setup\nmake\n")
        _write(self.root / "CLAUDE.md", "# Setup\njust\n")
        _write(self.root / "sub" / "CLAUDE.md", "elsewhere\n")
        d = self.discover(tracked=["AGENTS.md", "CLAUDE.md", "sub/CLAUDE.md"])
        plan = im.build_plan(d)
        blocked = [a for a in plan.actions if a.blocked]
        runnable = [a for a in plan.actions if not a.blocked]
        self.assertTrue(blocked)
        self.assertTrue(runnable, "a conflict in one scope must not block another")
        self.assertEqual(runnable[0].scope.as_posix(), "sub")

    def test_the_whole_plan_validates_before_any_mutation(self):
        _write(self.root / "CLAUDE.md", "one\n")
        _write(self.root / "Claude.md", "two\n")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        plan = im.build_plan(self.discover(tracked=["CLAUDE.md", "Claude.md"]))
        with self.assertRaises(im.PlanInvalid):
            im.apply_plan(plan, self.root)
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after, "an invalid plan must mutate nothing")


# -------------------------------------------------------------------- applying


class ApplyTests(TempRepo):
    def test_a_lone_claude_md_migrates_byte_for_byte(self):
        body = "line one\nline two\n\ntrailing\n"
        _write(self.root / "CLAUDE.md", body)
        plan = im.build_plan(self.discover(tracked=["CLAUDE.md"]))
        im.apply_plan(plan, self.root)
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), body)

    def test_a_case_only_rename_lands_on_the_exact_spelling(self):
        _write(self.root / "Claude.md", "v\n")
        plan = im.build_plan(self.discover(tracked=["Claude.md"]))
        im.apply_plan(plan, self.root)
        names = [p.name for p in self.root.iterdir() if p.is_file()]
        self.assertIn("AGENTS.md", names)
        self.assertNotIn("Claude.md", names)

    def test_a_case_only_rename_is_staged_through_a_temporary_name(self):
        """On a case-insensitive filesystem a direct rename is a no-op or an error."""
        _write(self.root / "Agents.md", "v\n")
        plan = im.build_plan(self.discover(tracked=["Agents.md"]))
        action = plan.actions[0]
        self.assertTrue(action.needs_case_staging)

    def test_identical_siblings_collapse_to_agents_md(self):
        _write(self.root / "AGENTS.md", "same\n")
        _write(self.root / "CLAUDE.md", "same\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        im.apply_plan(plan, self.root)
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), "same\n")

    def test_a_merge_keeps_both_sources_unique_content(self):
        _write(self.root / "AGENTS.md", "# A\naaa\n")
        _write(self.root / "CLAUDE.md", "# C\nccc\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        im.apply_plan(plan, self.root)
        out = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("aaa", out)
        self.assertIn("ccc", out)
        self.assertFalse((self.root / "CLAUDE.md").exists())

    def test_neither_source_is_removed_while_a_conflict_is_unresolved(self):
        _write(self.root / "AGENTS.md", "# Setup\nmake\n")
        _write(self.root / "CLAUDE.md", "# Setup\njust\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        im.apply_plan(plan, self.root)
        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertTrue((self.root / "CLAUDE.md").exists())

    def test_a_conflict_writes_a_reviewable_preview(self):
        _write(self.root / "AGENTS.md", "# Setup\nmake\n")
        _write(self.root / "CLAUDE.md", "# Setup\njust\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        receipt = im.apply_plan(plan, self.root)
        preview = im.preview_path(self.root)
        self.assertTrue(preview.exists(), "an unresolved conflict owes a preview")
        text = preview.read_text(encoding="utf-8")
        self.assertIn("make", text)
        self.assertIn("just", text)
        self.assertTrue(receipt.has_unresolved())

    def test_excluded_files_keep_their_bytes_and_report_a_named_disposition(self):
        cases = {
            "crux/templates/CLAUDE.md": "excluded:template",
            "CLAUDE.local.md": "excluded:local-override",
            ".claude/CLAUDE.md": "excluded:dot-claude",
            "vendor/dep/CLAUDE.md": "excluded:untracked",
        }
        for rel in cases:
            _write(self.root / rel, f"bytes of {rel}\n")
        _write(self.root / "CLAUDE.md", "migrate me\n")
        tracked = ["CLAUDE.md", "crux/templates/CLAUDE.md", "CLAUDE.local.md",
                   ".claude/CLAUDE.md"]
        before = {rel: (self.root / rel).read_bytes() for rel in cases}
        d = self.discover(tracked=tracked)
        receipt = im.apply_plan(im.build_plan(d), self.root)
        # Positive control. Without it this test passes when apply_plan is a
        # no-op, which is the reading it exists to rule out: "untouched" is only
        # meaningful if the same run touched something.
        self.assertTrue((self.root / "AGENTS.md").exists(),
                        "the managed file must have migrated in this same run")
        self.assertFalse((self.root / "CLAUDE.md").exists())
        for rel, expected in cases.items():
            self.assertEqual((self.root / rel).read_bytes(), before[rel], rel)
            self.assertEqual(d.disposition(rel), expected, rel)
            self.assertIn(rel, receipt.dispositions, rel)


# -------------------------------------------------------- receipt and recovery


class ReceiptTests(TempRepo):
    def test_the_receipt_records_source_hashes_and_dispositions(self):
        body = "exact\n"
        _write(self.root / "CLAUDE.md", body)
        receipt = im.apply_plan(im.build_plan(self.discover(tracked=["CLAUDE.md"])),
                                self.root)
        self.assertEqual(receipt.source_hashes["CLAUDE.md"], _sha(body))
        self.assertEqual(receipt.dispositions["CLAUDE.md"], "renamed")

    def test_the_receipt_is_written_to_disk_and_reread(self):
        _write(self.root / "CLAUDE.md", "x\n")
        im.apply_plan(im.build_plan(self.discover(tracked=["CLAUDE.md"])), self.root)
        path = im.receipt_path(self.root)
        self.assertTrue(path.exists())
        again = im.read_receipt(path)
        self.assertIn("CLAUDE.md", again.source_hashes)

    def test_the_receipt_does_not_claim_multi_file_atomicity(self):
        _write(self.root / "CLAUDE.md", "x\n")
        receipt = im.apply_plan(im.build_plan(self.discover(tracked=["CLAUDE.md"])),
                                self.root)
        self.assertFalse(getattr(receipt, "atomic", False))
        self.assertIn("per-file", receipt.staging_note.lower())


class RecoveryTests(TempRepo):
    def test_per_file_staging_recovers_after_an_injected_interruption(self):
        _write(self.root / "a" / "CLAUDE.md", "aaa\n")
        _write(self.root / "b" / "CLAUDE.md", "bbb\n")
        tracked = ["a/CLAUDE.md", "b/CLAUDE.md"]
        plan = im.build_plan(self.discover(tracked=tracked))

        boom = RuntimeError("injected interruption")
        calls = {"n": 0}
        real = im._commit_action

        def flaky(action, root, receipt):
            calls["n"] += 1
            if calls["n"] == 2:
                raise boom
            return real(action, root, receipt)

        im._commit_action = flaky
        try:
            with self.assertRaises(RuntimeError):
                im.apply_plan(plan, self.root)
        finally:
            im._commit_action = real

        done = [(self.root / "a" / "AGENTS.md").exists(),
                (self.root / "b" / "AGENTS.md").exists()]
        self.assertEqual(sum(done), 1, "exactly one file should have committed")

        receipt = im.apply_plan(im.build_plan(self.discover(tracked=tracked)), self.root)
        self.assertTrue((self.root / "a" / "AGENTS.md").exists())
        self.assertTrue((self.root / "b" / "AGENTS.md").exists())
        self.assertEqual((self.root / "a" / "AGENTS.md").read_text(encoding="utf-8"), "aaa\n")
        self.assertEqual((self.root / "b" / "AGENTS.md").read_text(encoding="utf-8"), "bbb\n")

    def test_no_temporary_file_survives_a_completed_run(self):
        _write(self.root / "CLAUDE.md", "x\n")
        im.apply_plan(im.build_plan(self.discover(tracked=["CLAUDE.md"])), self.root)
        leftovers = [p for p in self.root.rglob("*") if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_a_rerun_converges_to_a_reported_no_op(self):
        _write(self.root / "CLAUDE.md", "x\n")
        im.apply_plan(im.build_plan(self.discover(tracked=["CLAUDE.md"])), self.root)
        d2 = self.discover(tracked=["AGENTS.md"])
        plan2 = im.build_plan(d2)
        self.assertEqual(plan2.actions, [])
        receipt2 = im.apply_plan(plan2, self.root)
        self.assertTrue(receipt2.is_noop())
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), "x\n")

    def test_a_resolution_is_bound_to_the_bytes_it_was_reviewed_against(self):
        _write(self.root / "AGENTS.md", "# Setup\nmake\n")
        _write(self.root / "CLAUDE.md", "# Setup\njust\n")
        d = self.discover(tracked=["AGENTS.md", "CLAUDE.md"])
        plan = im.build_plan(d)
        im.apply_plan(plan, self.root)
        stale = im.read_receipt(im.receipt_path(self.root))
        _write(self.root / "CLAUDE.md", "# Setup\nninja\n")
        d2 = self.discover(tracked=["AGENTS.md", "CLAUDE.md"])
        self.assertFalse(im.resolution_still_binds(stale, d2),
                         "a source that moved must invalidate the plan")


# ------------------------------------------------------------------- log + CLI


class LogTests(TempRepo):
    def test_the_log_records_one_migration_operation_not_one_entry_per_file(self):
        for rel in ("a/CLAUDE.md", "b/CLAUDE.md", "c/CLAUDE.md"):
            _write(self.root / rel, "x\n")
        tracked = ["a/CLAUDE.md", "b/CLAUDE.md", "c/CLAUDE.md"]
        log = _write(self.root / "bionic" / "log.md",
                     "# Operations log\n\n_Append-only. Newest first._\n\n")
        receipt = im.apply_plan(im.build_plan(self.discover(tracked=tracked)), self.root)
        im.append_log(log, receipt, date="2026-09-21")
        text = log.read_text(encoding="utf-8")
        self.assertEqual(text.count("] schema | "), 1)
        self.assertIn("3", text, "the single entry should carry the file count")

    def test_the_log_op_matches_the_current_writer_enum(self):
        import re
        _write(self.root / "CLAUDE.md", "x\n")
        log = _write(self.root / "bionic" / "log.md",
                     "# Operations log\n\n_Append-only. Newest first._\n\n")
        receipt = im.apply_plan(im.build_plan(self.discover(tracked=["CLAUDE.md"])),
                                self.root)
        im.append_log(log, receipt, date="2026-09-21")
        pattern = (r"^## \[\d{4}-\d{2}-\d{2}\] (init|extract|arch|ingest|refresh|audit"
                   r"|cleanup-campsite|lint|adr|brief|journal|promptbook|invariant"
                   r"|observation|recover|query|schema|skill|origin|garden|adr-review"
                   r"|backfill|release) \| ")
        heads = [l for l in log.read_text(encoding="utf-8").splitlines()
                 if l.startswith("## [")]
        self.assertEqual(len(heads), 1)
        self.assertRegex(heads[0], pattern)


class EntryPointTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        if shutil.which("git") is None:
            self.skipTest("git is not available on PATH")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"],
                       cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.root, check=True)

    def _commit(self, rel, body):
        _write(self.root / rel, body)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "x"], cwd=self.root, check=True)

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(ENTRY), "--repo-root", str(self.root), *args],
            capture_output=True, text=True)

    def test_dry_run_reports_and_writes_nothing(self):
        self._commit("CLAUDE.md", "body\n")
        r = self._run("--dry-run")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertTrue((self.root / "CLAUDE.md").exists())
        self.assertFalse((self.root / "AGENTS.md").exists())
        import json
        json.loads(r.stdout)

    def test_a_clean_tree_exits_zero(self):
        self._commit("AGENTS.md", "body\n")
        r = self._run("--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_migrate_applies_and_the_real_git_tracked_set_is_the_boundary(self):
        self._commit("CLAUDE.md", "body\n")
        _write(self.root / "untracked" / "CLAUDE.md", "not mine\n")
        r = self._run("--migrate")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertEqual((self.root / "untracked" / "CLAUDE.md").read_text(encoding="utf-8"),
                         "not mine\n")

    def test_a_reviewed_resolution_unblocks_a_previewed_conflict(self):
        self._commit("AGENTS.md", "# Setup\nmake\n")
        self._commit("CLAUDE.md", "# Setup\njust\n")

        blocked = self._run("--migrate")
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        receipt = json.loads((self.root / ".instruction-migration-receipt.json").read_text())
        resolution = {
            "source_hashes": receipt["source_hashes"],
            "resolutions": [{
                "scope": ".",
                "path": ["Setup"],
                "text": "# Setup\nmake, or just where make is absent\n",
            }],
        }
        resolution_path = _write(
            self.root / "reviewed-resolution.json", json.dumps(resolution))

        applied = self._run("--migrate", "--resolution", str(resolution_path))

        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertEqual(
            (self.root / "AGENTS.md").read_text(encoding="utf-8"),
            "# Setup\nmake, or just where make is absent\n")
        final = json.loads(applied.stdout)
        self.assertTrue(any(row["disposition"] == "resolved"
                            for row in final["merge_rows"]))

    def test_a_resolution_refuses_when_a_previewed_source_changed(self):
        self._commit("AGENTS.md", "# Setup\nmake\n")
        self._commit("CLAUDE.md", "# Setup\njust\n")

        blocked = self._run("--migrate")
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        receipt = json.loads((self.root / ".instruction-migration-receipt.json").read_text())
        resolution = {
            "source_hashes": receipt["source_hashes"],
            "resolutions": [{
                "scope": ".",
                "path": ["Setup"],
                "text": "# Setup\nmake, or just where make is absent\n",
            }],
        }
        resolution_path = _write(
            self.root / "reviewed-resolution.json", json.dumps(resolution))
        _write(self.root / "CLAUDE.md", "# Setup\nninja\n")

        refused = self._run("--migrate", "--resolution", str(resolution_path))

        self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
        self.assertTrue((self.root / "CLAUDE.md").exists())
        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8"),
                         "# Setup\nninja\n")
        payload = json.loads(refused.stdout)
        self.assertTrue(payload["validation_errors"])

    def test_a_reparent_resolution_renders_under_its_receipted_ancestry(self):
        self._commit("AGENTS.md", "# General\nG\n# JavaScript\nJ\n")
        self._commit("CLAUDE.md", "# General\nG\n## Security\nS\n")

        blocked = self._run("--migrate")
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        receipt = json.loads((self.root / ".instruction-migration-receipt.json").read_text())
        resolution = {
            "source_hashes": receipt["source_hashes"],
            "resolutions": [{
                "scope": ".",
                "path": ["General", "Security"],
                "text": "## Security\nreviewed\n",
            }],
        }
        resolution_path = _write(
            self.root / "reviewed-resolution.json", json.dumps(resolution))

        applied = self._run("--migrate", "--resolution", str(resolution_path))

        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        blocks = im.split_blocks((self.root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(
            [block.path for block in blocks],
            [("General",), ("General", "Security"), ("JavaScript",)])
        final = json.loads(applied.stdout)
        self.assertTrue(any(row["result_path"] == ["General", "Security"]
                            and row["disposition"] == "resolved"
                            for row in final["merge_rows"]))

    def test_the_entry_point_declares_no_third_party_dependencies(self):
        head = ENTRY.read_text(encoding="utf-8")
        self.assertIn("# /// script", head)
        self.assertIn("dependencies = []", head)



# --------------------------------------------- the accounting refusal (review M1)


class AccountingRefusalTests(TempRepo):
    """The refusal clause 8 states, exercised against an UNBALANCED merge.

    An independent review found `accounting_balances()` defined, asserted on two
    happy paths, and called by nothing in production — so the refusal did not
    exist and no negative test was constructible. These are that negative test.
    """

    def _unbalance(self):
        """Make the merge under-account: drop a retained row from the receipt."""
        real = im.merge_documents

        def lying(a, c, resolutions=None):
            r = real(a, c, resolutions=resolutions)
            if r.applied:
                for i, row in enumerate(r.receipt_rows):
                    if row.disposition == "retained":
                        del r.receipt_rows[i]
                        break
            return r
        return real, lying

    def test_an_unbalanced_merge_is_refused_at_planning(self):
        _write(self.root / "AGENTS.md", "# A\naaa\n")
        _write(self.root / "CLAUDE.md", "# C\nccc\n")
        real, lying = self._unbalance()
        im.merge_documents = lying
        try:
            plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        finally:
            im.merge_documents = real
        self.assertTrue(plan.actions[0].blocked,
                        "an unbalanced merge must not be planned as runnable")
        self.assertIn("accounting does not balance", plan.actions[0].reason)

    def test_an_unbalanced_merge_writes_nothing(self):
        _write(self.root / "AGENTS.md", "# A\naaa\n")
        _write(self.root / "CLAUDE.md", "# C\nccc\n")
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        real, lying = self._unbalance()
        im.merge_documents = lying
        try:
            plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
            im.apply_plan(plan, self.root)
        finally:
            im.merge_documents = real
        after = {p: p.read_bytes() for p in self.root.rglob("*")
                 if p.is_file() and not p.name.startswith(".instruction-migration")}
        self.assertEqual(before, after, "a refused merge must leave both sources")

    def test_the_commit_guard_refuses_even_if_planning_is_bypassed(self):
        """Defence in depth: the guard is not an `assert`, so `python -O` keeps it."""
        _write(self.root / "AGENTS.md", "# A\naaa\n")
        _write(self.root / "CLAUDE.md", "# C\nccc\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        action = plan.actions[0]
        self.assertFalse(action.blocked, "positive control: this merge is runnable")
        for i, row in enumerate(action.merge.receipt_rows):
            if row.disposition == "retained":
                del action.merge.receipt_rows[i]
                break
        with self.assertRaises(im.PlanInvalid):
            im._commit_action(action, self.root, im.Receipt(self.root))

    def test_a_balanced_merge_still_applies(self):
        """Positive control: the refusal does not block a correct merge."""
        _write(self.root / "AGENTS.md", "# A\naaa\n")
        _write(self.root / "CLAUDE.md", "# C\nccc\n")
        plan = im.build_plan(self.discover(tracked=["AGENTS.md", "CLAUDE.md"]))
        self.assertFalse(plan.actions[0].blocked)
        im.apply_plan(plan, self.root)
        out = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("aaa", out)
        self.assertIn("ccc", out)


class SuppressorRemedyTests(TempRepo):
    """Clause 5 reports a suppressor WITH ITS REMEDY. A classification is not one."""

    def test_every_suppressor_carries_an_actionable_remedy(self):
        _write(self.root / "CLAUDE.md", "legacy\n")
        _write(self.root / "CLAUDE.local.md", "private\n")
        _write(self.root / ".claude" / "CLAUDE.md", "dot\n")
        d = self.discover(tracked=["CLAUDE.md"])
        self.assertTrue(d.suppressors, "positive control: suppressors were found")
        for s in d.suppressors:
            self.assertTrue(s.remedy.strip(), f"{s.path} carries no remedy")

    def test_a_private_override_is_never_told_to_be_deleted_by_crux(self):
        _write(self.root / "CLAUDE.local.md", "private\n")
        d = self.discover(tracked=[])
        s = next(x for x in d.suppressors if x.path.name == "CLAUDE.local.md")
        self.assertIn("yours", s.remedy)

    def test_a_denylisted_path_is_not_described_as_awaiting_migration(self):
        """It will never be migrated, so `suppresses until migrated` is false."""
        rel = "fixtures/trips/CLAUDE.md"
        _write(self.root / rel, "fixture\n")
        d = self.discover(tracked=[rel], denylist=[rel])
        s = next(x for x in d.suppressors if x.path.as_posix() == rel)
        self.assertIn("denylist", s.reason)
        self.assertNotIn("until migrated", s.reason)

    def test_a_genuinely_legacy_file_still_names_the_migrate_command(self):
        """Positive control for the branch above."""
        _write(self.root / "CLAUDE.md", "legacy\n")
        d = self.discover(tracked=["CLAUDE.md"])
        s = next(x for x in d.suppressors if x.path.as_posix() == "CLAUDE.md")
        self.assertIn("until migrated", s.reason)
        self.assertIn("--migrate", s.remedy)


class ContainmentTests(TempRepo):
    """Clause 2: no path resolves outside the root. Checked over the whole path."""

    def test_a_path_through_a_symlinked_directory_is_excluded(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        _write(outside / "CLAUDE.md", "elsewhere\n")
        os.symlink(outside, self.root / "linked")
        d = self.discover(tracked=["linked/CLAUDE.md"])
        self.assertEqual(d.managed_paths(), [])
        self.assertEqual(d.disposition("linked/CLAUDE.md"), "excluded:escapes-root")
        self.assertEqual((outside / "CLAUDE.md").read_text(encoding="utf-8"),
                         "elsewhere\n")

    def test_an_ordinary_nested_path_is_still_managed(self):
        """Positive control: containment does not exclude everything."""
        _write(self.root / "sub" / "CLAUDE.md", "mine\n")
        d = self.discover(tracked=["sub/CLAUDE.md"])
        self.assertEqual([p.as_posix() for p in d.managed_paths()], ["sub/CLAUDE.md"])


if __name__ == "__main__":
    unittest.main()
