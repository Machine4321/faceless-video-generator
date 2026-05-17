"""Tests for shadowvault.logging_config."""

import logging
import os

from shadowvault.logging_config import setup_logging, _ColorFormatter


class TestSetupLogging:
    def test_creates_log_directory(self, tmp_path):
        log_dir = str(tmp_path / "test_logs")
        setup_logging(log_dir=log_dir)
        assert os.path.isdir(log_dir)

    def test_creates_log_file(self, tmp_path):
        log_dir = str(tmp_path / "test_logs")
        setup_logging(log_dir=log_dir)
        log_file = os.path.join(log_dir, "shadowvault.log")
        # Write a log message to trigger file creation
        logging.getLogger("test").info("test message")
        assert os.path.isfile(log_file)

    def test_sets_root_level(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir, level=logging.DEBUG)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_has_two_handlers(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir)
        root = logging.getLogger()
        assert len(root.handlers) == 2

    def test_no_duplicate_handlers_on_reinit(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir)
        setup_logging(log_dir=log_dir)
        root = logging.getLogger()
        assert len(root.handlers) == 2

    def test_moviepy_logger_suppressed(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir)
        moviepy_logger = logging.getLogger("moviepy")
        assert moviepy_logger.level == logging.WARNING

    def test_pil_logger_suppressed(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir)
        pil_logger = logging.getLogger("PIL")
        assert pil_logger.level == logging.WARNING

    def test_log_message_written_to_file(self, tmp_path):
        log_dir = str(tmp_path / "logs")
        setup_logging(log_dir=log_dir)
        test_logger = logging.getLogger("test_write")
        test_logger.info("hello from test")
        log_file = os.path.join(log_dir, "shadowvault.log")
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "hello from test" in content


class TestColorFormatter:
    def test_format_adds_color_to_info(self):
        fmt = "%(levelname)s %(message)s"
        formatter = _ColorFormatter(fmt)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test msg", args=(), exc_info=None,
        )
        result = formatter.format(record)
        assert "test msg" in result
        # Should contain ANSI escape codes
        assert "\033[" in result

    def test_format_adds_color_to_error(self):
        fmt = "%(levelname)s %(message)s"
        formatter = _ColorFormatter(fmt)
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="", lineno=0,
            msg="error msg", args=(), exc_info=None,
        )
        result = formatter.format(record)
        assert "error msg" in result
        assert "\033[31m" in result  # red

    def test_format_adds_color_to_warning(self):
        fmt = "%(levelname)s %(message)s"
        formatter = _ColorFormatter(fmt)
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="warn msg", args=(), exc_info=None,
        )
        result = formatter.format(record)
        assert "\033[33m" in result  # yellow
