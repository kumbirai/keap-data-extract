"""
Data load manager for orchestrating entity loading operations.

This module provides a clean interface for loading data, eliminating the
complex main function and massive if/elif chains from the original script.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.scripts.loaders import LoadResult, LoaderFactory
from src.utils.global_logger import initialize_loggers

logger = logging.getLogger(__name__)


class DataLoadManager:
    """Main class to manage data loading operations.
    
    This class provides a clean interface for loading data, replacing the
    complex main function with a simple, extensible design.
    """

    def __init__(self):
        """Initialize the data load manager."""
        self.client = KeapClient()
        self.db = SessionLocal()

        # Initialize logging
        initialize_loggers()

        # Initialize database tables
        from src.database.init_db import init_db
        init_db()

        # Import checkpoint manager here to avoid circular imports
        from src.scripts.load_data import CheckpointManager
        self.checkpoint_manager = CheckpointManager()

    def load_entity(self, entity_type: str, entity_id: Optional[int] = None, update: bool = False) -> LoadResult:
        """Load a specific entity type or individual entity.
        
        Args:
            entity_type: The type of entity to load
            entity_id: Optional ID of specific entity to load
            update: Whether to perform an update operation
            
        Returns:
            LoadResult containing the operation statistics
        """
        if entity_id:
            return self._load_single_entity(entity_type, entity_id)
        else:
            return self._load_entity_type(entity_type, update)

    def _load_single_entity(self, entity_type: str, entity_id: int) -> LoadResult:
        """Load a single entity by ID."""
        try:
            loader = LoaderFactory.create_loader(entity_type, self.client, self.db, self.checkpoint_manager)
            success = loader.load_entity_by_id(entity_id)
            return LoadResult(1, 1 if success else 0, 0 if success else 1)
        except Exception as e:
            logger.error(f"Error loading {entity_type} {entity_id}: {e}")
            return LoadResult(1, 0, 1)

    def _load_entity_type(self, entity_type: str, update: bool) -> LoadResult:
        """Load all entities of a specific type."""
        try:
            loader = LoaderFactory.create_loader(entity_type, self.client, self.db, self.checkpoint_manager)
            return loader.load_all(update=update)
        except Exception as e:
            logger.error(f"Error loading {entity_type}: {e}")
            raise

    def load_all_data(self, update: bool = False) -> LoadResult:
        """Load all data in the correct order to maintain referential integrity.
        
        This method replaces the massive if/elif chains and repetitive
        result aggregation from the original main function.
        """
        total_result = LoadResult(0, 0, 0)

        # Define load order for referential integrity
        # This could be moved to configuration for even more flexibility
        load_order = ['custom_fields',  # Referenced by contacts
                      'tags',  # Referenced by contacts
                      'products',  # Referenced by orders and subscriptions
                      'contacts',  # Referenced by orders, tasks, notes
                      'opportunities',  # Independent
                      'affiliates',  # Referenced by orders
                      'orders',  # Referenced by subscriptions
                      'tasks',  # Independent
                      'notes',  # Independent
                      'campaigns',  # Independent
                      'subscriptions',  # Referenced by products
                      ]

        for entity_type in load_order:
            try:
                logger.info(f"Loading {entity_type}...")
                result = self._load_entity_type(entity_type, update)
                total_result.total_records += result.total_records
                total_result.success_count += result.success_count
                total_result.failed_count += result.failed_count
                logger.info(f"Completed {entity_type}: {result.success_count}/{result.total_records} successful")
            except Exception as e:
                logger.error(f"Error loading {entity_type}: {e}")
                # Continue with other entities instead of failing completely
                total_result.failed_count += 1

        return total_result

    def get_supported_entity_types(self) -> list:
        """Get list of all supported entity types."""
        return LoaderFactory.get_supported_entity_types()

    def close(self):
        """Close database connection."""
        self.db.close()


def main(update: bool = False, entity_type: str = None, entity_id: int = None):
    """Main function to perform the data load.
    
    This simplified main function replaces the original 100+ line function
    with a clean, readable implementation.
    """
    start_time = datetime.now(timezone.utc)

    manager = DataLoadManager()

    try:
        if update:
            logger.info("Performing update operation...")
        else:
            logger.info("Starting full data load...")

        # Load data based on parameters
        if entity_type and entity_id:
            result = manager.load_entity(entity_type, entity_id, update)
        elif entity_type:
            result = manager.load_entity(entity_type, update=update)
        else:
            result = manager.load_all_data(update)

        # Log results
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time

        logger.info(f"Data load completed in {duration}")
        logger.info(f"Total records processed: {result.total_records}")
        logger.info(f"Successfully processed: {result.success_count}")
        logger.info(f"Failed to process: {result.failed_count}")

        # Run error reprocessing after main data load
        if not entity_id:
            try:
                from src.scripts.reprocess_errors import ErrorReprocessor
                reprocessor = ErrorReprocessor()
                reprocessor.run()
                logger.info("Error reprocessing completed")
            except Exception as e:
                logger.error(f"Error during error reprocessing: {str(e)}")

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        manager.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Load data from Keap API into database')
    parser.add_argument('--update', action='store_true', help='Perform update operation using last_loaded timestamps')
    parser.add_argument('--entity-type', choices=LoaderFactory.get_supported_entity_types(), help='Type of entity to load')
    parser.add_argument('--entity-id', type=int, help='ID of specific entity to load')

    args = parser.parse_args()

    main(update=args.update, entity_type=args.entity_type, entity_id=args.entity_id)
