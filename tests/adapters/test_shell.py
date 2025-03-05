import unittest
from unittest.mock import patch
from smart_terminal.adapters.shell import (
    BashAdapter,
    ZshAdapter,
    PowerShellAdapter,
    ShellAdapterFactory,
)


class TestBashAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = BashAdapter()

    @patch("subprocess.run")
    def test_execute_command(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "output"
        success, output = self.adapter.execute_command("echo 'Hello World'")
        self.assertTrue(success)
        self.assertEqual(output, "output")

    @patch("subprocess.run")
    def test_execute_command_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "error"
        success, output = self.adapter.execute_command("invalid_command")
        self.assertFalse(success)
        self.assertEqual(output, "error")

    def test_write_environment_command(self):
        commands = ["export TEST_VAR='test'"]
        path = self.adapter.write_environment_command(commands, "Test command")
        self.assertTrue(path.endswith("last_commands.sh"))

    def test_get_integration_script(self):
        script = self.adapter.get_integration_script()
        self.assertIn("function smart_terminal_integration", script)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists", return_value=False)
    def test_is_integration_active(self, mock_exists, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(self.adapter.is_integration_active())


class TestZshAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = ZshAdapter()

    @patch("subprocess.run")
    def test_execute_command(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "output"
        success, output = self.adapter.execute_command("echo 'Hello World'")
        self.assertTrue(success)
        self.assertEqual(output, "output")

    @patch("subprocess.run")
    def test_execute_command_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "error"
        success, output = self.adapter.execute_command("invalid_command")
        self.assertFalse(success)
        self.assertEqual(output, "error")

    def test_write_environment_command(self):
        commands = ["export TEST_VAR='test'"]
        path = self.adapter.write_environment_command(commands, "Test command")
        self.assertTrue(path.endswith("last_commands.sh"))

    def test_get_integration_script(self):
        script = self.adapter.get_integration_script()
        self.assertIn("function smart_terminal_integration", script)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists", return_value=False)
    def test_is_integration_active(self, mock_exists, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(self.adapter.is_integration_active())


class TestPowerShellAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = PowerShellAdapter()

    @patch("subprocess.run")
    def test_execute_command(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "output"
        success, output = self.adapter.execute_command("Write-Output 'Hello World'")
        self.assertTrue(success)
        self.assertEqual(output, "output")

    @patch("subprocess.run")
    def test_execute_command_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "error"
        success, output = self.adapter.execute_command("invalid_command")
        self.assertFalse(success)
        self.assertEqual(output, "error")

    def test_write_environment_command(self):
        commands = ["$env:TEST_VAR='test'"]
        path = self.adapter.write_environment_command(commands, "Test command")
        self.assertTrue(path.endswith("last_commands.ps1"))

    def test_get_integration_script(self):
        script = self.adapter.get_integration_script()
        self.assertIn("function Invoke-SmartTerminalIntegration", script)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists", return_value=False)
    def test_is_integration_active(self, mock_exists, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(self.adapter.is_integration_active())


class TestShellAdapterFactory(unittest.TestCase):
    @patch("smart_terminal.adapters.shell.ZshAdapter.is_supported", return_value=True)
    @patch("os.environ.get", return_value="/bin/zsh")
    def test_create_adapter_zsh(self, mock_env, mock_supported):
        adapter = ShellAdapterFactory.create_adapter()
        self.assertIsInstance(adapter, ZshAdapter)

    @patch("smart_terminal.adapters.shell.BashAdapter.is_supported", return_value=True)
    @patch("os.environ.get", return_value="/bin/bash")
    def test_create_adapter_bash(self, mock_env, mock_supported):
        adapter = ShellAdapterFactory.create_adapter()
        self.assertIsInstance(adapter, BashAdapter)


if __name__ == "__main__":
    unittest.main()
