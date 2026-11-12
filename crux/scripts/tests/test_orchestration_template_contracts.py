"""The cycle module templates and their hand twins still parse as YAML.

The module partials are hand-mirrored into the cycle, iterate and patch
templates with no regenerator, so a hand edit can break any one of them.
"""

import unittest
from pathlib import Path

import yaml

CRUX = Path(__file__).resolve().parent.parent.parent
TEMPLATES = CRUX / 'templates'

MODULE_DEV = 'cycle-module-dev.yaml'
MODULE_REVIEW = 'cycle-module-review.yaml'
MODULE_ADR = 'cycle-module-adr.yaml'
CYCLE = 'cycle-promptbook-template.yaml'
ITERATE = 'iterate-promptbook-template.yaml'
PATCH = 'patch-promptbook-template.yaml'

TEMPLATE_NAMES = (MODULE_DEV, CYCLE, ITERATE, PATCH, MODULE_REVIEW, MODULE_ADR)


class TemplateContractPins(unittest.TestCase):
    def test_templates_still_parse_as_yaml(self):
        for name in TEMPLATE_NAMES:
            with self.subTest(template=name):
                yaml.safe_load((TEMPLATES / name).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
