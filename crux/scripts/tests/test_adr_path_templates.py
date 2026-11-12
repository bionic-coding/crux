"""The ADR-path cycle templates keep their embedded module copy and a parseable shape.

Three templates carry the ADR module or the review module's first prompt:
`cycle-module-adr.yaml`, `cycle-promptbook-template.yaml` (which embeds a copy of
the ADR module and of the review module) and `cycle-module-review.yaml`. This suite
parses each as YAML and checks:

1. the ADR module copy in the canonical book equals the module file's prompts for
   ordinals 2 to 4 byte for byte after the `{M}` substitution;
2. no block-scalar line opens with `rule:`, `[`, `{` or `--`, which YAML or the
   templates' own grammar would misread.

Stdlib plus PyYAML; reads only the shipped templates, so it is safe against the
staged artifact.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

# Frozen historical orchestration contract; live-cycle coverage is separate.
from _legacy_workflow_prose import legacy_path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent

TEMPLATES = SCRIPTS.parent / "templates"
ADR_MODULE = TEMPLATES / "cycle-module-adr.yaml"
REVIEW_MODULE = TEMPLATES / "cycle-module-review.yaml"
BOOK = TEMPLATES / "cycle-promptbook-template.yaml"

FORBIDDEN_LINE_START = re.compile(r"^\s*(?:rule:|\[|\{|--)")


def load(path: Path):
    return yaml.safe_load(legacy_path(path).read_text(encoding="utf-8"))



def book_module(book: dict, tag: str) -> list[dict]:
    return [p for p in book["prompts"] if p.get("module_tag") == tag]


def line_start_problems(raw: str) -> list[str]:
    """Lines of a block scalar that open with a shape the templates forbid."""
    problems = []
    in_block = False
    block_indent = 0
    for number, line in enumerate(raw.splitlines(), 1):
        if not in_block:
            if re.search(r":\s*[|>][+-]?\s*$", line):
                in_block = True
                block_indent = len(line) - len(line.lstrip()) + 1
            continue
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip())
        if indent < block_indent:
            in_block = bool(re.search(r":\s*[|>][+-]?\s*$", line))
            if in_block:
                block_indent = indent + 1
            continue
        if FORBIDDEN_LINE_START.match(line):
            problems.append(f"line {number}: {line.strip()[:40]!r}")
    return problems


class CouncilPromptTests(unittest.TestCase):

    def test_book_copy_equals_module_for_ordinals_two_to_four(self):
        module = load(ADR_MODULE)
        embedded = book_module(load(BOOK), "adr-1")
        self.assertEqual(len(module), len(embedded))
        for i in (1, 2, 3):
            for key in ("purpose", "prompt", "expected_output", "side_effects"):
                with self.subTest(ordinal=i + 1, field=key):
                    a, b = module[i][key], embedded[i][key]
                    if isinstance(a, str):
                        a = a.replace("{M}", "1")
                    self.assertEqual(a, b)


class LineStartTests(unittest.TestCase):

    def test_no_block_scalar_line_opens_with_a_forbidden_shape(self):
        for path in (ADR_MODULE, REVIEW_MODULE, BOOK):
            with self.subTest(template=path.name):
                self.assertEqual(line_start_problems(legacy_path(path).read_text(encoding="utf-8")), [])

    def test_control_the_scan_sees_each_forbidden_shape(self):
        for bad in ("rule:some-slug", "[link]", "{token}", "--flag"):
            raw = f"- prompt: |\n    ok line\n    {bad} opens a line\n"
            with self.subTest(bad=bad):
                self.assertEqual(len(line_start_problems(raw)), 1)
        self.assertEqual(line_start_problems("- prompt: |\n    fine (rule:a-slug)\n"), [])


if __name__ == "__main__":
    unittest.main()
