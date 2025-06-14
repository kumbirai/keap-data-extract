import logging
from typing import Optional

from .error_logger import ErrorLogger

# Global logger instances
_error_logger: Optional[ErrorLogger] = None


def get_error_logger() -> ErrorLogger:
    """Get the global error logger instance.
    
    Returns:
        ErrorLogger: The global error logger instance
    """
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger


def initialize_loggers() -> None:
    """Initialize all global loggers."""
    global _error_logger
    _error_logger = ErrorLogger()
    logging.info("Global loggers initialized")
