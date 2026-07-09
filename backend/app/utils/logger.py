"""Centralized logging configuration for the application."""

import logging
import sys

from app.config.settings import settings


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance for the given module name."""

    logger = logging.getLogger(name)

    if logger.handlers:
        # Logger already configured (avoid duplicate handlers on reload).
        return logger

    logger.setLevel(settings.LOG_LEVEL.upper())

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
