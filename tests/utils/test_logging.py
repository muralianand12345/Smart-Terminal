import logging

from smart_terminal.utils.logging import (
    setup_logging,
    get_logger,
    disable_all_logging,
    enable_debug_logging,
    check_log_file,
    clear_logs,
    NullHandler,
)


def test_get_logger():
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)


def test_setup_logging(tmp_path, monkeypatch):
    log_file = tmp_path / "smartterminal.log"
    monkeypatch.setattr("smart_terminal.utils.logging.LOG_DIR", tmp_path)
    setup_logging(level_name="DEBUG", log_file=True, log_to_console=False)
    logger = get_logger("test_logger")
    logger.debug("This is a debug message")
    assert log_file.exists()


def test_disable_all_logging():
    disable_all_logging()
    logger = get_logger("test_logger")
    assert logger.level == logging.CRITICAL + 1
    assert not any(
        isinstance(handler, logging.StreamHandler) for handler in logger.handlers
    )


def test_enable_debug_logging(tmp_path, monkeypatch):
    log_file = tmp_path / "smartterminal.log"
    monkeypatch.setattr("smart_terminal.utils.logging.LOG_DIR", tmp_path)
    setup_logging(level_name="INFO", log_file=True, log_to_console=False)
    enable_debug_logging()
    logger = get_logger("test_logger")
    assert logger.level == logging.DEBUG
    assert any(
        isinstance(handler, logging.StreamHandler) for handler in logger.handlers
    )


def test_check_log_file(tmp_path, monkeypatch):
    log_file = tmp_path / "smartterminal.log"
    log_file.touch()
    monkeypatch.setattr("smart_terminal.utils.logging.LOG_DIR", tmp_path)
    info = check_log_file()
    assert info["exists"]
    assert info["path"] == str(log_file)


def test_clear_logs(tmp_path, monkeypatch):
    log_file = tmp_path / "smartterminal.log"
    log_file.touch()
    monkeypatch.setattr("smart_terminal.utils.logging.LOG_DIR", tmp_path)
    assert clear_logs()
    assert not log_file.exists()


def test_null_handler():
    handler = NullHandler()
    logger = get_logger("test_logger")
    logger.addHandler(handler)
    logger.info("This should not raise an error")
