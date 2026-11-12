"""The `rule:` spellings on the planning surfaces parse as the citation lint reads them.

Grammar: a citation is `rule:` followed by a lowercase letter then lowercase
letters, digits and hyphens; the token ends at the first character outside
that set. The placeholder form `rule:<new-thing>` is a NON-token because `<`
is not a lowercase letter, which is how a brief may name a rule that does not
exist yet without tripping the citation lint. The lint resolves every token;
a malformed spelling (an uppercase letter, a digit, an unclosed `<`) is no
token at all, so the lint skips it, and `CitationGrammarTests` catches it here.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# Frozen historical orchestration contract; live-cycle coverage is separate.
from _legacy_workflow_prose import legacy_path

REPO_ROOT = Path(__file__).resolve().parents[3]
CRUX = REPO_ROOT / "crux"
TEMPLATES = CRUX / "templates"
SKILLS = CRUX / "skills"

DEV_MODULE = TEMPLATES / "cycle-module-dev.yaml"
VERIFY_MODULE = TEMPLATES / "cycle-module-verify.yaml"
ADR_MODULE = TEMPLATES / "cycle-module-adr.yaml"
REVIEW_MODULE = TEMPLATES / "cycle-module-review.yaml"
ITERATE_TEMPLATE = TEMPLATES / "iterate-promptbook-template.yaml"
BRIEF_TEMPLATE = TEMPLATES / "BRIEF-template.md"
ITERATE_SKILL = SKILLS / "iterate" / "SKILL.md"
DEV_CYCLE_SKILL = SKILLS / "dev-cycle" / "SKILL.md"
LOG_WORK_SKILL = SKILLS / "log-work" / "SKILL.md"
WHITEBOARDING_SKILL = SKILLS / "whiteboarding" / "SKILL.md"

#: The surfaces this unit owns. Every citation-grammar assertion below runs
#: over exactly these files.
PLANNING_SURFACES: tuple[Path, ...] = (
    DEV_MODULE,
    VERIFY_MODULE,
    ADR_MODULE,
    REVIEW_MODULE,
    ITERATE_TEMPLATE,
    BRIEF_TEMPLATE,
    ITERATE_SKILL,
    DEV_CYCLE_SKILL,
    LOG_WORK_SKILL,
    WHITEBOARDING_SKILL,
)

# Clause-1 grammar. A token is the citation; a placeholder is the authoring
# convention. Everything else after `rule:` is classified by `_classify`.
RULE_TOKEN_RE = re.compile(r"rule:([a-z][a-z0-9-]*)")
PLACEHOLDER_RE = re.compile(r"rule:<([a-z][a-z0-9-]*)>")
RULE_PREFIX_RE = re.compile(r"rule:(.?)")


def _read(p: Path) -> str:
    return legacy_path(p).read_text(encoding="utf-8")


def _classify(text: str) -> dict[str, list[str]]:
    """Bucket every `rule:` occurrence in `text`.

    `token`       — `rule:<slug>` per the clause-1 grammar (must resolve).
    `placeholder` — `rule:<name>` in angle brackets (the authoring rule).
    `mention`     — the bare prefix in prose (`rule:` before a backtick, a
                    space, or end of text), which cites nothing.
    `malformed`   — anything else: an uppercase letter, a digit, an
                    underscore, or a `<` not closed as a placeholder.
    """
    out: dict[str, list[str]] = {
        "token": [], "placeholder": [], "mention": [], "malformed": [],
    }
    for m in RULE_PREFIX_RE.finditer(text):
        nxt = m.group(1)
        at = m.start()
        if nxt and nxt.islower() and nxt.isalpha():
            out["token"].append(RULE_TOKEN_RE.match(text, at).group(1))
        elif nxt == "<":
            pm = PLACEHOLDER_RE.match(text, at)
            if pm:
                out["placeholder"].append(pm.group(1))
            else:
                out["malformed"].append(text[at:at + 40])
        elif nxt in ("", "`", " ", "\n", ")", ","):
            out["mention"].append(text[at:at + 40])
        else:
            out["malformed"].append(text[at:at + 40])
    return out


class CitationGrammarTests(unittest.TestCase):
    """Every placeholder on the planning surfaces is a non-token, and no spelling is malformed."""

    def test_classifier_separates_the_four_shapes(self):
        # Positive control for every bucket the assertions below rely on.
        b = _classify("`rule:live-slug` and `rule:<new-thing>` and a `rule:` prefix and rule:Bad and rule:<x y>")
        self.assertEqual(b["token"], ["live-slug"])
        self.assertEqual(b["placeholder"], ["new-thing"])
        self.assertEqual(len(b["mention"]), 1)
        self.assertEqual(len(b["malformed"]), 2)

    def test_every_placeholder_is_angle_bracketed_and_nothing_is_malformed(self):
        placeholders: list[str] = []
        for p in PLANNING_SURFACES:
            with self.subTest(surface=p.name):
                b = _classify(_read(p))
                self.assertEqual(b["malformed"], [], f"malformed rule: spelling in {p.name}")
                placeholders += b["placeholder"]
        self.assertTrue(placeholders, "the authoring rule is stated somewhere (positive control)")


if __name__ == "__main__":
    unittest.main()
