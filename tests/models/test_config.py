import unittest
from smart_terminal.models.config import (
    Config,
    HistorySettings,
    AISettings,
    ShellSettings,
    LogLevel,
    OsType,
)


class TestConfigModels(unittest.TestCase):
    def test_history_settings(self):
        history_settings = HistorySettings(history_limit=10, save_history=False)
        self.assertEqual(history_settings.history_limit, 10)
        self.assertFalse(history_settings.save_history)

    def test_ai_settings(self):
        ai_settings = AISettings(
            api_key="test_key",
            base_url="https://api.example.com",
            model_name="test_model",
            temperature=0.5,
        )
        self.assertEqual(ai_settings.api_key, "test_key")
        self.assertEqual(ai_settings.base_url, "https://api.example.com")
        self.assertEqual(ai_settings.model_name, "test_model")
        self.assertEqual(ai_settings.temperature, 0.5)

    def test_shell_settings(self):
        shell_settings = ShellSettings(
            shell_integration_enabled=True, auto_source_commands=True
        )
        self.assertTrue(shell_settings.shell_integration_enabled)
        self.assertTrue(shell_settings.auto_source_commands)

    def test_config(self):
        config = Config(
            default_os=OsType.LINUX,
            log_level=LogLevel.DEBUG,
            ai=AISettings(api_key="test_key"),
            history=HistorySettings(history_limit=10),
            shell=ShellSettings(shell_integration_enabled=True),
        )
        self.assertEqual(config.default_os, OsType.LINUX)
        self.assertEqual(config.log_level, LogLevel.DEBUG)
        self.assertEqual(config.ai.api_key, "test_key")
        self.assertEqual(config.history.history_limit, 10)
        self.assertTrue(config.shell.shell_integration_enabled)


if __name__ == "__main__":
    unittest.main()
