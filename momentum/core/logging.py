"""Momentum logging utilities."""

from typing import Optional
import logging


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger for momentum modules."""
    logger = logging.getLogger(name or "momentum")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
