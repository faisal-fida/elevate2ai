import logging
from typing import Optional, Union
from pathlib import Path


def setup_logger(
    name: str,
    level: Optional[Union[int, str]] = None,
    log_format: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
) -> logging.Logger:
    logger = logging.getLogger(name)

    # Set logging level
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    if level is not None:
        logger.setLevel(level)
    elif not logger.level:
        logger.setLevel(logging.INFO)

    # Use default format if none specified
    if log_format is None:
        log_format = "%(levelname)s:     %(message)s"

    formatter = logging.Formatter(log_format)

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Add file handler if log_file specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
