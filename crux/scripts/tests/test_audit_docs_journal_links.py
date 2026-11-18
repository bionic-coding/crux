"""CHK-JR-4 resolves the bare ADR citation form by id.

`docs/AGENTS.md` §9 prescribes `[[adrs/ADR-NNNN]]` for citing an ADR, while
ADR files carry a slug (`ADR-NNNN-<slug>.md`) and may sit in `adrs/archive/`.
CHK-JR-4 is prose an auditing agent executes; no script implements it. These
tests pin the resolution rule in both places the skill states it, then apply
that rule over this repository's live journal and ADR tree.

What this proves: the skill text states the id-keyed rule, and under that rule
the 31 bare-id links in the historical journal months each resolve to exactly
one ADR file while a made-up id resolves to none. What it does not prove: that
an auditing agent reading the skill applies the rule.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from _dev_surface import REPO_ROOT, TREE, require_dev_surface

SKILL = REPO_ROOT / "crux" / "skills" / "audit-docs" / "SKILL.md"
JOURNAL = REPO_ROOT / TREE / "journal"
ADRS = REPO_ROOT / TREE / "adrs"

# §14.3 dual-form id: an optional artifact prefix before `ADR-NNNN`.
ID = r"(?:[A-Z][A-Z0-9]{1,9}-)?ADR-\d{4}"
BARE = re.compile(rf"\[\[adrs/({ID})\]\]")
ADR_LINK = re.compile(r"\[\[adrs/([^\[\]|#`\s]+)(?:[|#][^\]]*)?\]\]")

# The journal months whose bare-id links the docs audit reported as dangling.
REPORTED_MONTHS = ("2026-06.md", "2026-07.md", "2026-08.md", "2026-09.md")
REPORTED_COUNT = 31


def chk_jr_4_text() -> str:
    """The inline CHK-JR-4 rule: its bullet, up to the next CHK bullet."""
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("- **CHK-JR-4**")
    end = text.index("- **CHK-JR-5**", start)
    return text[start:end]


def explore_item_44() -> str:
    """The Explore-agent journal item that restates CHK-JR-4."""
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("> 44. ")
    end = text.index("\n", start)
    return text[start:end]


def adr_files(adrs: Path) -> list[Path]:
    """ADR files in the two tiers CHK-JR-4 searches: `adrs/` and `adrs/archive/`."""
    return sorted(
        p
        for tier in (adrs, adrs / "archive")
        if tier.is_dir()
        for p in tier.glob("*ADR-[0-9][0-9][0-9][0-9]*.md")
    )


def resolve(target: str, adrs: Path) -> list[Path]:
    """Resolve an `adrs/` wiki-link target under the rule CHK-JR-4 states.

    A bare id matches by id across both tiers; the id is the whole key. Any
    other target keeps exact-path resolution: a slugged ADR link must name an
    existing file in either tier, and a non-ADR path (`reviews/...`) must exist
    as written.
    """
    if re.fullmatch(ID, target):
        pattern = re.compile(rf"{re.escape(target)}(?:-.*)?\.md")
        return [p for p in adr_files(adrs) if pattern.fullmatch(p.name)]
    if re.fullmatch(rf"{ID}-.+", target):
        hits = [adrs / f"{target}.md", adrs / "archive" / f"{target}.md"]
        return [p for p in hits if p.is_file()]
    exact = adrs / f"{target}.md"
    return [exact] if exact.is_file() else []


class SkillStatesTheRuleTests(unittest.TestCase):
    """Both statements of CHK-JR-4 name the bare form and the two tiers."""

    def test_inline_rule_resolves_the_bare_id_across_both_tiers(self) -> None:
        rule = chk_jr_4_text()
        self.assertIn("bare citation form", rule)
        self.assertIn("`adrs/ADR-NNNN`", rule)
        # The release-content gate refuses the wiki-link literal on a shipped skill.
        self.assertNotIn("[[adrs/", rule)
        self.assertIn("`docs/adrs/archive/`", rule)
        self.assertIn("ADR links resolve by id", rule)
        self.assertIn("slugged", rule)

    def test_inline_rule_keeps_the_promptbook_and_run_forms(self) -> None:
        rule = chk_jr_4_text()
        self.assertIn("`[[promptbooks/PB-NNNN]]`", rule)
        self.assertIn("keep exact-path resolution", rule)
        self.assertIn("Dangling → WARNING", rule)

    def test_explore_item_resolves_the_bare_id_across_both_tiers(self) -> None:
        item = explore_item_44()
        self.assertIn("A bare `adrs/ADR-NNNN` target", item)
        self.assertNotIn("[[adrs/", item)
        self.assertIn("`archive/`", item)
        self.assertIn("by id", item)


class LiveTreeTests(unittest.TestCase):
    """The stated rule applied to this repository's journal and ADRs."""

    def setUp(self) -> None:
        require_dev_surface(self, JOURNAL, f"{TREE}/journal")
        require_dev_surface(self, ADRS, f"{TREE}/adrs")

    def reported_links(self) -> list[tuple[str, str]]:
        links = []
        for name in REPORTED_MONTHS:
            path = JOURNAL / name
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                links += [(name, m) for m in BARE.findall(text)]
        return links

    def test_each_reported_bare_id_resolves_to_exactly_one_adr(self) -> None:
        links = self.reported_links()
        self.assertEqual(len(links), REPORTED_COUNT, links)
        for month, target in links:
            with self.subTest(month=month, target=target):
                hits = resolve(target, ADRS)
                self.assertEqual(len(hits), 1, hits)
                self.assertTrue(hits[0].name.startswith(f"{target}-"), hits)

    def test_the_reported_links_dangle_under_exact_path_resolution(self) -> None:
        # Positive control: the bare form names no file as written, which is
        # why an exact-path reading reported every one of them.
        for _, target in self.reported_links():
            with self.subTest(target=target):
                self.assertFalse((ADRS / f"{target}.md").exists())
                self.assertFalse((ADRS / "archive" / f"{target}.md").exists())

    def test_bare_ids_reach_the_archive_tier(self) -> None:
        tiers = {resolve(t, ADRS)[0].parent.name for _, t in self.reported_links()}
        self.assertIn("archive", tiers)

    def test_a_missing_id_still_dangles(self) -> None:
        used = {re.search(r"ADR-(\d{4})", p.name).group(1) for p in adr_files(ADRS)}
        missing = next(f"{n:04d}" for n in range(9999, 0, -1) if f"{n:04d}" not in used)
        self.assertEqual(resolve(f"ADR-{missing}", ADRS), [])
        self.assertEqual(resolve(f"ADR-{missing}-made-up-slug", ADRS), [])

    def test_every_journal_adr_link_resolves_under_the_rule(self) -> None:
        for path in sorted(JOURNAL.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].md")):
            for target in ADR_LINK.findall(path.read_text(encoding="utf-8")):
                with self.subTest(month=path.name, target=target):
                    self.assertTrue(resolve(target, ADRS), target)

    def test_a_stale_slug_still_dangles(self) -> None:
        # The slugged form keeps exact-filename resolution; only the bare id
        # resolves by id.
        self.assertEqual(resolve("ADR-0050-a-slug-that-drifted", ADRS), [])


if __name__ == "__main__":
    unittest.main()
