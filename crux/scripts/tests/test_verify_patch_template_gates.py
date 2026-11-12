"""The verify-path and patch templates keep their YAML shape and their embedded copy.

Covers `cycle-module-verify.yaml`, `iterate-promptbook-template.yaml` and
`patch-promptbook-template.yaml`. A template changes only new books, so every
assertion here reads the template text; none of them touches an existing book.

The line-start scan has a seeded control in `DetectorControlTests`.
"""

import re
import unittest
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent
TEMPLATES = SCRIPTS.parent / "templates"
VERIFY = TEMPLATES / "cycle-module-verify.yaml"
ITERATE = TEMPLATES / "iterate-promptbook-template.yaml"
PATCH = TEMPLATES / "patch-promptbook-template.yaml"

FORBIDDEN_STARTS = ("rule:", "[", "{", "--")


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def verify_module():
    return load(VERIFY)


def iterate_prompts():
    return load(ITERATE)["prompts"]


def substitute(text):
    """Resolve the verify module's tokens as `iterate` does for a single verify module."""
    return text.replace(" {M}", "").replace("{M}", "")


def forbidden_line_starts(strings):
    return [ln for s in strings for ln in s.splitlines()
            if ln.lstrip().startswith(FORBIDDEN_STARTS)]


def all_strings(node):
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for v in node.values() for s in all_strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in all_strings(v)]
    return []


class VerifyModuleTests(unittest.TestCase):

    def test_no_block_scalar_line_opens_with_a_forbidden_token(self):
        self.assertEqual(forbidden_line_starts(all_strings(verify_module())), [])


class IterateTemplateTests(unittest.TestCase):

    def test_embedded_council_prompt_equals_the_module_after_parse(self):
        mod = verify_module()[1]
        emb = iterate_prompts()[1]
        for field in ("title", "purpose", "prompt", "expected_output"):
            self.assertEqual(norm(substitute(mod[field])), norm(emb[field]), field)
        self.assertEqual(mod["side_effects"], emb["side_effects"])

    def test_no_block_scalar_line_opens_with_a_forbidden_token(self):
        self.assertEqual(forbidden_line_starts(all_strings(load(ITERATE))), [])


class PatchTemplateTests(unittest.TestCase):

    def test_no_block_scalar_line_opens_with_a_forbidden_token(self):
        self.assertEqual(forbidden_line_starts(all_strings(load(PATCH))), [])


class DetectorControlTests(unittest.TestCase):

    def test_forbidden_line_start_detector_reports_each_shape(self):
        for opener in ("rule:x", "[a]", "{b}", "--c"):
            self.assertEqual(forbidden_line_starts([f"ok\n  {opener}\nok"]), [f"  {opener}"])


if __name__ == "__main__":
    unittest.main()
