import unittest
from unittest.mock import patch, mock_open
from smart_terminal.config.manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    @patch("smart_terminal.config.manager.Path.mkdir")
    @patch("smart_terminal.config.manager.open", new_callable=mock_open)
    @patch("smart_terminal.config.manager.get_default_config")
    def test_init_config(self, mock_get_default_config, mock_open, mock_mkdir):
        mock_get_default_config.return_value = {"key": "value"}

        # Ensure CONFIG_FILE and HISTORY_FILE do not exist
        ConfigManager.CONFIG_FILE.unlink(missing_ok=True)
        ConfigManager.HISTORY_FILE.unlink(missing_ok=True)

        ConfigManager.init_config()
        mock_mkdir.assert_called()
        mock_open.assert_called()
        mock_get_default_config.assert_called()

    @patch("smart_terminal.config.manager.Path.mkdir")
    @patch("smart_terminal.config.manager.open", new_callable=mock_open)
    @patch("smart_terminal.config.manager.json.load")
    @patch("smart_terminal.config.manager.merge_with_defaults")
    def test_load_config(
        self, mock_merge_with_defaults, mock_json_load, mock_open, mock_mkdir
    ):
        mock_json_load.return_value = {"key": "value"}
        mock_merge_with_defaults.return_value = {"key": "value"}
        
        # Ensure CONFIG_FILE exists
        ConfigManager.CONFIG_FILE.touch()

        config = ConfigManager.load_config()
        mock_mkdir.assert_called()
        mock_open.assert_called_with(ConfigManager.CONFIG_FILE, "r")
        mock_json_load.assert_called()
        mock_merge_with_defaults.assert_called()
        self.assertEqual(config, {"key": "value"})

    @patch("smart_terminal.config.manager.Path.mkdir")
    @patch("smart_terminal.config.manager.open", new_callable=mock_open)
    @patch("smart_terminal.config.manager.json.load")
    def test_load_history(self, mock_json_load, mock_open, mock_mkdir):
        mock_json_load.return_value = [{"message": "test"}]
        
        # Ensure HISTORY_FILE exists
        ConfigManager.HISTORY_FILE.touch()

        history = ConfigManager.load_history()
        mock_mkdir.assert_called()
        mock_open.assert_called_with(ConfigManager.HISTORY_FILE, "r")
        mock_json_load.assert_called()
        self.assertEqual(history, [{"message": "test"}])

    @patch("smart_terminal.config.manager.Path.mkdir")
    @patch("smart_terminal.config.manager.open", new_callable=mock_open)
    @patch("smart_terminal.config.manager.json.dump")
    def test_save_config(self, mock_json_dump, mock_open, mock_mkdir):
        config = {"key": "value"}
        ConfigManager.save_config(config)
        mock_mkdir.assert_called()
        mock_open.assert_called()
        mock_json_dump.assert_called_with(config, mock_open(), indent=2)

    @patch("smart_terminal.config.manager.Path.mkdir")
    @patch("smart_terminal.config.manager.open", new_callable=mock_open)
    @patch("smart_terminal.config.manager.json.dump")
    def test_save_history(self, mock_json_dump, mock_open, mock_mkdir):
        history = [{"message": "test"}]
        ConfigManager.save_history(history)
        mock_mkdir.assert_called()
        mock_open.assert_called()
        mock_json_dump.assert_called_with(history, mock_open(), indent=2)

    @patch("smart_terminal.config.manager.Path.mkdir")
    @patch("smart_terminal.config.manager.open", new_callable=mock_open)
    @patch("smart_terminal.config.manager.json.dump")
    def test_reset_history(self, mock_json_dump, mock_open, mock_mkdir):
        ConfigManager.reset_history()
        mock_open.assert_called()
        mock_json_dump.assert_called_with([], mock_open())

    @patch("smart_terminal.config.manager.ConfigManager.load_config")
    @patch("smart_terminal.config.manager.ConfigManager.save_config")
    def test_update_config_value(self, mock_save_config, mock_load_config):
        mock_load_config.return_value = {"key": "value"}
        ConfigManager.update_config_value("key", "new_value")
        mock_load_config.assert_called()
        mock_save_config.assert_called_with({"key": "new_value"})

    @patch("smart_terminal.config.manager.ConfigManager.load_config")
    def test_get_config_value(self, mock_load_config):
        mock_load_config.return_value = {"key": "value"}
        value = ConfigManager.get_config_value("key")
        mock_load_config.assert_called()
        self.assertEqual(value, "value")


if __name__ == "__main__":
    unittest.main()
