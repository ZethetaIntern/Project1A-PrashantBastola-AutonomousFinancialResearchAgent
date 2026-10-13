
"""Centralized logging configuration for the financial research agent."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import LOG_LEVEL, PROJECT_ROOT


LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "agent.log"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(message)s"
)


def setup_logging() -> None:
    """Configure console and rotating file logging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()

    # Avoid duplicate handlers if setup_logging() is called more than once.
    if getattr(root_logger, "_financial_agent_logging_configured", False):
        return

    level = getattr(logging, LOG_LEVEL, logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    root_logger._financial_agent_logging_configured = True

    logging.getLogger(__name__).info("Logging initialized")

