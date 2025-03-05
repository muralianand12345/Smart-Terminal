import sys
import json
import unittest
from io import StringIO
from unittest.mock import patch

from smart_terminal.cli.main import show_version_info, show_config_info
from smart_terminal import __version__


class TestInfoFunctions(unittest.TestCase):
    def setUp(self):
        # Capture stdout for checking output
        self.stdout_capture = StringIO()
        self.stdout_backup = sys.stdout
        sys.stdout = self.stdout_capture

    def tearDown(self):
        # Restore stdout
        sys.stdout = self.stdout_backup

    def get_stdout(self):
        """Get captured stdout and reset the buffer."""
        output = self.stdout_capture.getvalue()
        self.stdout_capture = StringIO()
        sys.stdout = self.stdout_capture
        return output

    @patch("platform.python_version")
    @patch("platform.platform")
    @patch("platform.system")
    @patch("platform.release")
    @patch("platform.processor")
    def test_show_version_info_standard_output(
        self, mock_processor, mock_release, mock_system, mock_platform, mock_py_version
    ):
        # Set up mocks
        mock_py_version.return_value = "3.10.5"
        mock_platform.return_value = "macOS-13.4-x86_64"
        mock_system.return_value = "Darwin"
        mock_release.return_value = "22.5.0"
        mock_processor.return_value = "i386"

        # Call function
        show_version_info(json_output=False)

        # Get output
        output = self.get_stdout()

        # Check output
        self.assertIn(f"SmartTerminal version {__version__}", output)
        self.assertIn("Python 3.10.5 on macOS-13.4-x86_64", output)

    @patch("platform.python_version")
    @patch("platform.platform")
    @patch("platform.system")
    @patch("platform.release")
    @patch("platform.processor")
    def test_show_version_info_json_output(
        self, mock_processor, mock_release, mock_system, mock_platform, mock_py_version
    ):
        # Set up mocks
        mock_py_version.return_value = "3.10.5"
        mock_platform.return_value = "macOS-13.4-x86_64"
        mock_system.return_value = "Darwin"
        mock_release.return_value = "22.5.0"
        mock_processor.return_value = "i386"

        # Call function
        show_version_info(json_output=True)

        # Get output
        output = self.get_stdout()

        # Parse JSON and check structure
        try:
            version_info = json.loads(output)
            self.assertEqual(version_info["version"], __version__)
            self.assertEqual(version_info["python_version"], "3.10.5")
            self.assertEqual(version_info["platform"], "macOS-13.4-x86_64")
            self.assertEqual(version_info["system"], "Darwin")
            self.assertEqual(version_info["release"], "22.5.0")
            self.assertEqual(version_info["processor"], "i386")
        except json.JSONDecodeError:
            self.fail("Output is not valid JSON")

    @patch("smart_terminal.config.ConfigManager.load_config")
    def test_show_config_info_standard_output(self, mock_load_config):
        # Set up mock config
        mock_load_config.return_value = {
            "api_key": "sk-abcd1234efgh5678ijkl",
            "base_url": "https://api.groq.com/openai/v1",
            "model_name": "llama-3.3-70b-versatile",
            "default_os": "macos",
            "history_limit": 20,
            "log_level": "INFO",
            "shell_integration_enabled": True,
            "custom_setting": "test_value",
        }

        # Call function
        show_config_info(json_output=False)

        # Get output
        output = self.get_stdout()

        # Check output contains expected sections and values (redacted api_key)
        self.assertIn("Configuration Information", output)
        self.assertIn("AI Service", output)
        self.assertIn("api_key: sk-a...ijkl", output)
        self.assertIn("base_url: https://api.groq.com/openai/v1", output)
        self.assertIn("model_name: llama-3.3-70b-versatile", output)
        self.assertIn("default_os: macos", output)
        self.assertIn("history_limit: 20", output)
        self.assertIn("shell_integration_enabled: True", output)
        self.assertIn("custom_setting: test_value", output)

    @patch("smart_terminal.config.ConfigManager.load_config")
    def test_show_config_info_json_output(self, mock_load_config):
        # Set up mock config
        mock_load_config.return_value = {
            "api_key": "sk-abcd1234efgh5678ijkl",
            "base_url": "https://api.groq.com/openai/v1",
            "model_name": "llama-3.3-70b-versatile",
            "default_os": "macos",
            "history_limit": 20,
            "log_level": "INFO",
            "shell_integration_enabled": True,
            "custom_setting": "test_value",
        }

        # Call function
        show_config_info(json_output=True)

        # Get output
        output = self.get_stdout()

        # Parse JSON and check structure
        try:
            config_info = json.loads(output)
            self.assertEqual(config_info["api_key"], "sk-a...ijkl")
            self.assertEqual(config_info["base_url"], "https://api.groq.com/openai/v1")
            self.assertEqual(config_info["model_name"], "llama-3.3-70b-versatile")
            self.assertEqual(config_info["default_os"], "macos")
            self.assertEqual(config_info["history_limit"], 20)
            self.assertEqual(config_info["log_level"], "INFO")
            self.assertEqual(config_info["shell_integration_enabled"], True)
            self.assertEqual(config_info["custom_setting"], "test_value")
        except json.JSONDecodeError:
            self.fail("Output is not valid JSON")

    @patch("smart_terminal.config.ConfigManager.load_config")
    def test_show_config_info_with_short_api_key(self, mock_load_config):
        # Set up mock config with short API key
        mock_load_config.return_value = {
            "api_key": "short-key",
            "model_name": "llama-3.3-70b-versatile",
        }

        # Test JSON output
        show_config_info(json_output=True)
        json_output = self.get_stdout()
        config_info = json.loads(json_output)
        self.assertEqual(config_info["api_key"], "********")

        # Test standard output
        show_config_info(json_output=False)
        standard_output = self.get_stdout()
        self.assertIn("api_key: ********", standard_output)

    @patch("smart_terminal.config.ConfigManager.load_config")
    def test_show_config_info_with_error(self, mock_load_config):
        # Make the load_config raise an exception
        mock_load_config.side_effect = Exception("Test error")

        # Call function and check it handles the error
        show_config_info()
        output = self.get_stdout()
        self.assertIn("Error loading configuration: Test error", output)
