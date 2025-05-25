import logging
import sys

from src.api.exceptions import KeapAPIError, KeapValidationError
from src.scripts.load_data import main as load_data_main
from src.utils.logging_config import setup_logging


def main():
    # Setup logging
    setup_logging(
        log_level=logging.INFO,
        log_dir="logs",
        app_name="keap_data_extract"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Keap Data Extraction application")

    try:
        # Execute the load_data script
        load_data_main(update=False)
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
