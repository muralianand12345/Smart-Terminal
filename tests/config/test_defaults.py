import unittest
from smart_terminal.config.defaults import (
    get_default_config,
    reset_to_defaults,
    merge_with_defaults,
)


class TestDefaults(unittest.TestCase):
    def test_get_default_config(self):
        config = get_default_config()
        self.assertIn("default_os", config)
        self.assertIn("log_level", config)

    def test_reset_to_defaults(self):
        config = {"key": "value"}
        reset_config = reset_to_defaults(config)
        self.assertIn("default_os", reset_config)
        self.assertNotIn("key", reset_config)

    def test_merge_with_defaults(self):
        config = {"key": "value"}
        merged_config = merge_with_defaults(config)
        self.assertIn("default_os", merged_config)
        self.assertIn("key", merged_config)


if __name__ == "__main__":
    unittest.main()
