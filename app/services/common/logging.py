import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Union
from pathlib import Path

if not os.path.exists("logs"):
    os.makedirs("logs")

LOG_FORMAT = "%(levelname)s | %(name)s | (%(filename)s:%(lineno)d) | %(message)s"
DETAILED_FORMAT = (
    "%(levelname)s | %(name)s | (%(filename)s:%(lineno)d) | %(funcName)s | %(message)s"
)

COLORS = {
    "DEBUG": "\033[94m",  # Blue
    "INFO": "\033[92m",  # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",  # Red
    "CRITICAL": "\033[1;91m",  # Bold Red
    "RESET": "\033[0m",  # Reset to default
}


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log level names in terminal output
    """

    def format(self, record):
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
        result = super().format(record)
        record.levelname = levelname
        return result


class ErrorHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            if record.exc_info:
                record.msg = f"{record.msg}\nTraceback:\n{traceback.format_exception(*record.exc_info)}"
            elif hasattr(record, "stack_info") and record.stack_info:
                record.msg = f"{record.msg}\nStack:\n{record.stack_info}"
            else:
                stack = traceback.format_stack()[:-1]  # Exclude this frame
                record.msg = f"{record.msg}\nStack:\n{''.join(stack)}"
        self.formatter.format(record)


def setup_logger(
    name: str,
    level: Optional[Union[int, str]] = None,
    log_format: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
) -> logging.Logger:
    logger = logging.getLogger(name)

    if isinstance(level, str):
        level = getattr(logging, level.upper())
    if level is not None:
        logger.setLevel(level)
    elif not logger.level:
        logger.setLevel(logging.INFO)

    if log_format is None:
        log_format = LOG_FORMAT

    standard_formatter = logging.Formatter(log_format)
    colored_formatter = ColoredFormatter(log_format)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)

        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(standard_formatter)
            logger.addHandler(file_handler)

        error_handler = ErrorHandler()
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(standard_formatter)
        logger.addHandler(error_handler)

        today = datetime.now().strftime("%Y-%m-%d")
        error_file_handler = logging.FileHandler(f"logs/{today}-errors.log")
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(standard_formatter)
        logger.addHandler(error_file_handler)

    return logger


def log_exception(logger, message, exc=None):
    """
    Log an exception with full traceback information

    Args:
        logger: Logger instance
        message: Error message
        exc: Exception object (optional - if not provided, will use current exception)
    """
    if exc is None:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if not any((exc_type, exc_value, exc_traceback)):
            logger.error(f"{message} (no exception info available)")
            return
    else:
        exc_type = type(exc)
        exc_value = exc
        exc_traceback = exc.__traceback__

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)

    logger.error(f"{message}\n{tb_text}")
