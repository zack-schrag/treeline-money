"""Unit tests for logging functionality."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from treeline.utils import (
    get_log_dir,
    get_log_file_path,
    get_logger,
    get_treeline_dir,
    setup_logging,
)


@pytest.fixture
def temp_treeline_dir():
    """Create a temporary treeline directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, {"TREELINE_DIR": tmpdir}):
            yield Path(tmpdir)


class TestGetLogDir:
    """Tests for get_log_dir function."""

    def test_returns_logs_subdirectory(self, temp_treeline_dir: Path):
        """Should return logs subdirectory under treeline dir."""
        log_dir = get_log_dir()
        assert log_dir == temp_treeline_dir / "logs"

    def test_respects_treeline_dir_override(self, temp_treeline_dir: Path):
        """Should use TREELINE_DIR environment variable."""
        log_dir = get_log_dir()
        assert str(temp_treeline_dir) in str(log_dir)


class TestGetLogFilePath:
    """Tests for get_log_file_path function."""

    def test_creates_log_directory(self, temp_treeline_dir: Path):
        """Should create log directory if it doesn't exist."""
        log_file = get_log_file_path()
        assert log_file.parent.exists()

    def test_returns_dated_log_file(self, temp_treeline_dir: Path):
        """Should return a log file with date in the name."""
        log_file = get_log_file_path()
        assert log_file.name.startswith("treeline-")
        assert log_file.suffix == ".log"

    def test_log_file_format(self, temp_treeline_dir: Path):
        """Should use YYYY-MM-DD format in filename."""
        import re

        log_file = get_log_file_path()
        pattern = r"treeline-\d{4}-\d{2}-\d{2}\.log"
        assert re.match(pattern, log_file.name)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_returns_logger(self, temp_treeline_dir: Path):
        """Should return a logger instance."""
        # Clear any existing handlers
        logger = logging.getLogger("treeline")
        logger.handlers.clear()

        result = setup_logging()
        assert isinstance(result, logging.Logger)
        assert result.name == "treeline"

    def test_creates_file_handler(self, temp_treeline_dir: Path):
        """Should create a file handler."""
        # Clear any existing handlers
        logger = logging.getLogger("treeline")
        logger.handlers.clear()

        setup_logging()

        # Check that a file handler was added
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) == 1

    def test_idempotent_setup(self, temp_treeline_dir: Path):
        """Should not add duplicate handlers on multiple calls."""
        # Clear any existing handlers
        logger = logging.getLogger("treeline")
        logger.handlers.clear()

        setup_logging()
        initial_handlers = len(logger.handlers)

        setup_logging()
        assert len(logger.handlers) == initial_handlers

    def test_writes_to_log_file(self, temp_treeline_dir: Path):
        """Should write log messages to file."""
        # Clear any existing handlers
        logger = logging.getLogger("treeline")
        logger.handlers.clear()

        setup_logging()
        log_file = get_log_file_path()

        # Log a test message
        logger.info("Test log message")

        # Force flush
        for handler in logger.handlers:
            handler.flush()

        # Verify message was written
        content = log_file.read_text()
        assert "Test log message" in content


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_base_logger(self, temp_treeline_dir: Path):
        """Should return base treeline logger when no name provided."""
        # Clear any existing handlers
        logging.getLogger("treeline").handlers.clear()

        logger = get_logger()
        assert logger.name == "treeline"

    def test_returns_base_logger_for_treeline_name(self, temp_treeline_dir: Path):
        """Should return base logger when name is 'treeline'."""
        # Clear any existing handlers
        logging.getLogger("treeline").handlers.clear()

        logger = get_logger("treeline")
        assert logger.name == "treeline"

    def test_returns_namespaced_logger(self, temp_treeline_dir: Path):
        """Should return namespaced logger for other names."""
        # Clear any existing handlers
        logging.getLogger("treeline").handlers.clear()

        logger = get_logger("cli.sync")
        assert logger.name == "treeline.cli.sync"

    def test_auto_configures_logging(self, temp_treeline_dir: Path):
        """Should auto-configure logging if not already done."""
        # Clear any existing handlers
        logging.getLogger("treeline").handlers.clear()

        get_logger("test")

        # Check that base logger has handlers
        base_logger = logging.getLogger("treeline")
        assert len(base_logger.handlers) > 0
