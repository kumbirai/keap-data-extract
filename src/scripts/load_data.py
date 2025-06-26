import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.utils.global_logger import initialize_loggers
from src.utils.logging_config import setup_logging

# Create logs and checkpoints directories if they don't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('checkpoints', exist_ok=True)

# Setup logging
setup_logging(log_level=logging.INFO, log_dir="logs", app_name="keap_data_extract")

# Get logger for this module
logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Enumeration of supported entity types."""
    CUSTOM_FIELDS = "custom_fields"
    TAGS = "tags"
    PRODUCTS = "products"
    CONTACTS = "contacts"
    OPPORTUNITIES = "opportunities"
    AFFILIATES = "affiliates"
    ORDERS = "orders"
    TASKS = "tasks"
    NOTES = "notes"
    CAMPAIGNS = "campaigns"
    SUBSCRIPTIONS = "subscriptions"


@dataclass
class LoadResult:
    """Data class to hold load operation results."""
    total_records: int
    success_count: int
    failed_count: int


class AuditLogger:
    def __init__(self, audit_file: str = 'logs/audit_log.json'):
        self.audit_file = audit_file
        self.audits = self._load_audits()

    def _load_audits(self) -> Dict:
        if os.path.exists(self.audit_file):
            try:
                with open(self.audit_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid audit file, starting fresh")
                return {}
        return {}

    def log_audit(self, entity_type: str, start_time: datetime, end_time: datetime, total_records: int, success: int, failed: int) -> None:
        """Log audit information for a data load operation."""
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]

        audit_entry = {'entity_type': entity_type, 'start_time': start_time.isoformat(), 'end_time': end_time.isoformat(), 'total_records': total_records, 'success': success, 'failed': failed,
                       'duration': duration_str}

        if entity_type not in self.audits:
            self.audits[entity_type] = []

        self.audits[entity_type].append(audit_entry)

        with open(self.audit_file, 'w') as f:
            json.dump(self.audits, f, indent=2)

        logger.info(f"Audit log for {entity_type}: Total={total_records}, Success={success}, "
                    f"Failed={failed}, Duration={duration_str}")


class CheckpointManager:
    def __init__(self, checkpoint_file: str = 'checkpoints/load_progress.json'):
        self.checkpoint_file = checkpoint_file
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        self.checkpoints = self._load_checkpoints()
        self.audit_logger = AuditLogger()

    def _load_checkpoints(self) -> Dict:
        """Load checkpoints from file if it exists, otherwise return empty dict."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid checkpoint file, starting fresh")
                return {}
        return {}

    def save_checkpoint(self, entity_type: str, total_records_processed: int, api_offset: int = None, completed: bool = False) -> None:
        """Save checkpoint with total records processed and API offset.
        
        Args:
            entity_type: The type of entity being processed
            total_records_processed: Total number of records processed so far
            api_offset: Current API pagination offset (optional, will be calculated if not provided)
            completed: Whether this entity type is fully loaded
        """
        if entity_type not in self.checkpoints:
            self.checkpoints[entity_type] = {'total_records_processed': 0, 'api_offset': 0, 'last_loaded': None}

        self.checkpoints[entity_type]['total_records_processed'] = total_records_processed

        # If api_offset is provided, use it; otherwise calculate from total_records_processed
        if api_offset is not None:
            self.checkpoints[entity_type]['api_offset'] = api_offset
        else:
            # Calculate API offset based on total records processed (assuming batch size of 50)
            self.checkpoints[entity_type]['api_offset'] = (total_records_processed // 50) * 50

        if completed:
            self.checkpoints[entity_type]['last_loaded'] = datetime.now(timezone.utc).isoformat()

        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoints, f, indent=2)
        logger.debug(f"Saved checkpoint for {entity_type}: {total_records_processed} records processed, API offset: {self.checkpoints[entity_type]['api_offset']}")

    def get_checkpoint(self, entity_type: str) -> int:
        """Get the total records processed for an entity type."""
        return self.checkpoints.get(entity_type, {}).get('total_records_processed', 0)

    def get_api_offset(self, entity_type: str) -> int:
        """Get the API offset for an entity type."""
        return self.checkpoints.get(entity_type, {}).get('api_offset', 0)

    def get_last_loaded_timestamp(self, entity_type: str) -> Optional[str]:
        """Get the last loaded timestamp for an entity type."""
        return self.checkpoints.get(entity_type, {}).get('last_loaded')

    def clear_checkpoints(self) -> None:
        """Clear all checkpoints."""
        self.checkpoints = {}
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        logger.debug("Cleared all checkpoints")

    def get_query_params(self, entity_type: str, update: bool = False) -> Dict[str, Any]:
        """Get query parameters based on entity type and update flag."""
        params = {}
        if update:
            last_loaded = self.get_last_loaded_timestamp(entity_type)
            if last_loaded:
                params['since'] = last_loaded
        return params


class DataLoadManager:
    """Main class to manage data loading operations."""

    def __init__(self):
        self.client = KeapClient()
        self.db = SessionLocal()
        self.checkpoint_manager = CheckpointManager()

        # Initialize logging
        initialize_loggers()

        # Initialize database tables
        from src.database.init_db import init_db
        init_db()

    def load_entity(self, entity_type: str, entity_id: Optional[int] = None, update: bool = False) -> LoadResult:
        """Load a specific entity type or individual entity."""
        if entity_id:
            return self._load_single_entity(entity_type, entity_id)
        else:
            return self._load_entity_type(entity_type, update)

    def _load_single_entity(self, entity_type: str, entity_id: int) -> LoadResult:
        """Load a single entity by ID."""
        start_time = datetime.now(timezone.utc)
        try:
            from src.scripts.loaders import LoaderFactory
            loader = LoaderFactory.create_loader(entity_type, self.client, self.db, self.checkpoint_manager)
            success = loader.load_entity_by_id(entity_id)
            result = LoadResult(1, 1 if success else 0, 0 if success else 1)

            # Log audit information
            end_time = datetime.now(timezone.utc)
            self.checkpoint_manager.audit_logger.log_audit(entity_type=f"{entity_type}_single", start_time=start_time, end_time=end_time, total_records=result.total_records, success=result.success_count, failed=result.failed_count)

            return result
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            # Log audit information even for failed operations
            self.checkpoint_manager.audit_logger.log_audit(entity_type=f"{entity_type}_single", start_time=start_time, end_time=end_time, total_records=1, success=0, failed=1)
            logger.error(f"Error loading {entity_type} {entity_id}: {e}")
            return LoadResult(1, 0, 1)

    def _load_entity_type(self, entity_type: str, update: bool) -> LoadResult:
        """Load all entities of a specific type."""
        start_time = datetime.now(timezone.utc)
        try:
            from src.scripts.loaders import LoaderFactory
            loader = LoaderFactory.create_loader(entity_type, self.client, self.db, self.checkpoint_manager)
            result = loader.load_all(update=update)

            # Log audit information
            end_time = datetime.now(timezone.utc)
            self.checkpoint_manager.audit_logger.log_audit(entity_type=entity_type, start_time=start_time, end_time=end_time, total_records=result.total_records, success=result.success_count, failed=result.failed_count)

            return result
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            # Log audit information even for failed operations
            self.checkpoint_manager.audit_logger.log_audit(entity_type=entity_type, start_time=start_time, end_time=end_time, total_records=0, success=0, failed=1)
            logger.error(f"Error loading {entity_type}: {e}")
            raise

    def load_all_data(self, update: bool = False) -> LoadResult:
        """Load all data in the correct order to maintain referential integrity."""
        start_time = datetime.now(timezone.utc)
        total_result = LoadResult(0, 0, 0)

        # Define load order for referential integrity
        load_order = [EntityType.CUSTOM_FIELDS.value, EntityType.TAGS.value, EntityType.PRODUCTS.value, EntityType.CONTACTS.value, EntityType.OPPORTUNITIES.value, EntityType.AFFILIATES.value,
                      EntityType.ORDERS.value, EntityType.TASKS.value, EntityType.NOTES.value, EntityType.CAMPAIGNS.value, EntityType.SUBSCRIPTIONS.value, ]

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

        # Log audit information for the overall operation
        end_time = datetime.now(timezone.utc)
        self.checkpoint_manager.audit_logger.log_audit(entity_type="all_entities", start_time=start_time, end_time=end_time, total_records=total_result.total_records, success=total_result.success_count, failed=total_result.failed_count)

        return total_result

    def get_supported_entity_types(self) -> list:
        """Get list of all supported entity types."""
        from src.scripts.loaders import LoaderFactory
        return LoaderFactory.get_supported_entity_types()

    def close(self):
        """Close database connection."""
        self.db.close()


def main(update: bool = False, entity_type: str = None, entity_id: int = None):
    """Main function to perform the data load."""
    start_time = datetime.now(timezone.utc)

    manager = DataLoadManager()

    try:
        if update:
            logger.info("Performing update operation...")
        else:
            logger.info("Starting full data load...")

        if entity_type and entity_id:
            result = manager.load_entity(entity_type, entity_id, update)
        elif entity_type:
            result = manager.load_entity(entity_type, update=update)
        else:
            result = manager.load_all_data(update)

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
    parser.add_argument('--entity-type', choices=[e.value for e in EntityType], help='Type of entity to load')
    parser.add_argument('--entity-id', type=int, help='ID of specific entity to load')

    args = parser.parse_args()

    main(update=args.update, entity_type=args.entity_type, entity_id=args.entity_id)
