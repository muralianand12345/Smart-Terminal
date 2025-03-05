import unittest
from smart_terminal.cli.arguments import parse_arguments, validate_args


class TestArguments(unittest.TestCase):
    def test_parse_arguments(self):
        args = parse_arguments(["--version"])
        self.assertTrue(args.version)
        self.assertFalse(args.config_info)

    def test_validate_args(self):
        args = parse_arguments(["--version"])
        self.assertTrue(validate_args(args))

        args = parse_arguments(["--setup", "some command"])
        self.assertFalse(validate_args(args))


if __name__ == "__main__":
    unittest.main()
