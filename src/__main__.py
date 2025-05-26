import argparse
import logging
import sys

from src.api.exceptions import KeapAPIError, KeapValidationError
from src.scripts.load_data import main as load_data_main
from src.utils.logging_config import setup_logging


def parse_args():
    """Parse all command line arguments."""
    parser = argparse.ArgumentParser(description='Keap Data Extraction Tool')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--update', action='store_true', help='Perform update operation using last_loaded timestamps')
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_args()

    # Setup logging with appropriate level
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(
        log_level=log_level,
        log_dir="logs",
        app_name="keap_data_extract"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Keap Data Extraction application")

    try:
        # Execute the load_data script with update flag
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
