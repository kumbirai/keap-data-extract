import logging
import logging.handlers
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: int = logging.INFO, log_dir: str = "logs", app_name: str = "keap_data_extract") -> None:
    """
    Configure application-wide logging
    
    Args:
        log_level: The logging level (default: INFO)
        log_dir: Directory to store log files (default: logs)
        app_name: Application name for log file naming
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_path / f"{app_name}_{timestamp}.log"

    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Create and configure file handler
    file_handler = logging.handlers.RotatingFileHandler(filename=log_file, maxBytes=20 * 1024 * 1024,  # 20MB
                                                        backupCount=10, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)

    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)

    # Get the root logger
    root_logger = logging.getLogger()

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Reset the root logger's level
    root_logger.setLevel(log_level)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Set logging level for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    # Create logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")
