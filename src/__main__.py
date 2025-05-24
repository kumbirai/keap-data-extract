import os
import sys
import logging
from pathlib import Path
from utils.logging_config import setup_logging
from api import KeapClient
from api.exceptions import KeapAPIError, KeapValidationError

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
        # Initialize the API client
        client = KeapClient()
        logger.info("API client initialized successfully")
        
        # Example usage
        contacts = client.get_contacts(limit=10)
        logger.info(f"Retrieved {len(contacts.get('contacts', []))} contacts")
        
    except KeapValidationError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except KeapAPIError as e:
        logger.error(f"API error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("Application completed successfully")

if __name__ == "__main__":
    main() 