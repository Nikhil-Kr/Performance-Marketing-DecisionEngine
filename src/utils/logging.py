"""Structured logging for Project Expedition."""
import logging

def get_logger(name: str) -> logging.Logger:
    """Get a named logger with consistent formatting."""
    logger = logging.getLogger(f"expedition.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
