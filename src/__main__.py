import argparse
import logging
import sys
from pathlib import Path

from src.api.exceptions import KeapAPIError, KeapValidationError
from src.scripts.load_data import main as load_data_main
from src.utils.logging_config import setup_logging


def ensure_directories_exist():
    """Ensure all required directories exist."""
    required_dirs = ["logs", "logs/errors", "checkpoints"]

    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logging.info(f"Ensured directory exists: {dir_path}")


def parse_args():
    """Parse all command line arguments."""
    parser = argparse.ArgumentParser(description='Keap Data Extraction Tool')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--update', action='store_true', help='Perform update operation using last_loaded timestamps')
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_args()

    # Setup logging with the appropriate level
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level=log_level, log_dir="logs", app_name="keap_data_extract")

    logger = logging.getLogger(__name__)
    logger.info("Starting Keap Data Extraction application")

    try:
        # Ensure all required directories exist
        ensure_directories_exist()

        # Execute the load_data script with an update flag
        load_data_main(update=args.update)
        logger.info("Data loading completed successfully")

    except KeapValidationError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except KeapAPIError as e:
        logger.error(f"API error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

    logger.info("Application completed successfully")


if __name__ == "__main__":
    main()
