"""Logging setup shared by every stage."""

from __future__ import annotations

import logging


ROOT_LOGGER_NAME = "bsi_pipeline"
_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
_DATEFMT = "%H:%M:%S"


def configure(verbosity: int = 1) -> None:
    """Configure the root pipeline logger.

    verbosity: 0 = WARNING, 1 = INFO (default), 2+ = DEBUG.
    """
    level = logging.WARNING if verbosity <= 0 else logging.INFO if verbosity == 1 else logging.DEBUG

    root = logging.getLogger(ROOT_LOGGER_NAME)
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setLevel(level)

    root.propagate = False


def get_logger(stage: str) -> logging.Logger:
    """Return a logger for a named stage (e.g. ``extract``)."""
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{stage}")
