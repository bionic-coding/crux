"""The `.bionic.yml` `decisions: {classifier: off}` opt-out (CYC-0090, decision-transport-and-routing)."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bionic_config
from bionic_config import BionicConfigError, load_decisions_policy, validate_decisions_policy


def write_config(root, extra):
    (Path(root) / '.bionic.yml').write_text('config_version: "1"\ndocs_dir: bionic\n' + extra)


class DecisionsPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_absent_section_leaves_the_classifier_on(self):
        self.assertEqual(validate_decisions_policy({}), {'classifier': 'default'})
        write_config(self.root, '')
        self.assertEqual(load_decisions_policy(self.root), {'classifier': 'default'})

    def test_unquoted_off_loaded_from_yaml_text_validates(self):
        write_config(self.root, 'decisions:\n  classifier: off\n')
        self.assertEqual(load_decisions_policy(self.root), {'classifier': 'off'})

    def test_quoted_string_off_validates(self):
        write_config(self.root, 'decisions:\n  classifier: "off"\n')
        self.assertEqual(load_decisions_policy(self.root), {'classifier': 'off'})

    def test_boolean_false_validates(self):
        self.assertEqual(validate_decisions_policy({'decisions': {'classifier': False}}), {'classifier': 'off'})

    def test_any_other_value_is_a_configuration_error(self):
        for value in (True, 'on', 'OFF', 'no', 0, None, ['off']):
            with self.subTest(value=value), self.assertRaises(BionicConfigError):
                validate_decisions_policy({'decisions': {'classifier': value}})

    def test_an_invalid_value_in_the_file_is_a_configuration_error_for_every_reader(self):
        write_config(self.root, 'decisions:\n  classifier: on\n')
        with self.assertRaises(BionicConfigError):
            load_decisions_policy(self.root)
        with self.assertRaises(BionicConfigError):
            bionic_config.load_workflow_policy(self.root)

    def test_another_key_or_a_non_mapping_is_a_configuration_error(self):
        for raw in ({'decisions': {'other': 1}}, {'decisions': 'off'}, {'decisions': ['off']}):
            with self.subTest(raw=raw), self.assertRaises(BionicConfigError):
                validate_decisions_policy(raw)


if __name__ == '__main__':
    unittest.main()
