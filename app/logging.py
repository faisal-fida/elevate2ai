import logging
import sys
import traceback
from datetime import datetime
from typing import Optional, Union
from pathlib import Path

# Ensure logs directory exists
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Configure log formats
LOG_FORMAT = "%(levelname)s:     %(message)s (%(filename)s:%(lineno)d)"
DETAILED_FORMAT = (
    "%(levelname)s:     %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)

# Terminal color codes for different log levels
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
    Custom formatter that adds colors to log level names in terminal output.

    This makes logs more readable in the console by color-coding
    different log levels (e.g., errors in red, warnings in yellow).
    """

    def format(self, record):
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
        result = super().format(record)
        record.levelname = levelname  # Restore original levelname
        return result


class DetailedErrorHandler(logging.Handler):
    """
    Custom handler that adds traceback information to error logs.

    This ensures that all error logs include detailed stack traces
    for better debugging.
    """

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            if record.exc_info:
                # Use existing exception info if available
                record.msg = f"{record.msg}\nTraceback:\n{''.join(traceback.format_exception(*record.exc_info))}"
            elif hasattr(record, "stack_info") and record.stack_info:
                # Use stack info if provided
                record.msg = f"{record.msg}\nStack:\n{record.stack_info}"
            else:
                # Capture current stack
                stack = traceback.format_stack()[:-1]  # Exclude this frame
                record.msg = f"{record.msg}\nStack:\n{''.join(stack)}"

        self.formatter.format(record)


def setup_logger(
    name: str,
    level: Optional[Union[int, str]] = None,
    log_format: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
) -> logging.Logger:
    """
    Configure and return a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, etc.)
        log_format: Custom log format string
        log_file: Optional path to additional log file

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set log level
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    if level is not None:
        logger.setLevel(level)
    elif not logger.level:
        logger.setLevel(logging.INFO)

    # Use default format if none specified
    if log_format is None:
        log_format = LOG_FORMAT

    # Create formatters
    standard_formatter = logging.Formatter(log_format)
    colored_formatter = ColoredFormatter(log_format)

    # Only add handlers if none exist already
    if not logger.handlers:
        # Console output with colors
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)

        # Optional specific log file
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(standard_formatter)
            logger.addHandler(file_handler)

        # Enhanced error handler
        error_handler = DetailedErrorHandler()
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(standard_formatter)
        logger.addHandler(error_handler)

        # Daily error log file
        today = datetime.now().strftime("%Y-%m-%d")
        error_file_handler = logging.FileHandler(LOGS_DIR / f"{today}-errors.log")
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(standard_formatter)
        logger.addHandler(error_file_handler)

    return logger


def log_exception(logger: logging.Logger, message: str, exc: Exception = None) -> None:
    """
    Log an exception with full traceback information.

    Args:
        logger: Logger instance
        message: Error message to include
        exc: Exception object (if None, uses current exception context)
    """
    if exc is None:
        # Get current exception info
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if not any((exc_type, exc_value, exc_traceback)):
            logger.error(f"{message} (no exception info available)")
            return
    else:
        # Use provided exception
        exc_type = type(exc)
        exc_value = exc
        exc_traceback = exc.__traceback__

    # Format traceback and log error
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)
    logger.error(f"{message}\n{tb_text}")
