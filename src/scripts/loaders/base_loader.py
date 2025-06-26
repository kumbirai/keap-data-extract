"""
Base loader classes for entity loading operations.

This module provides the foundation for all entity loaders, eliminating
code duplication through abstraction and common patterns.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.exceptions import KeapQuotaExhaustedError, KeapRateLimitError, KeapServerError
from src.api.keap_client import KeapClient
from src.utils.global_logger import get_error_logger
from src.utils.retry import exponential_backoff

logger = logging.getLogger(__name__)


@dataclass
class LoadResult:
    """Data class to hold load operation results."""
    total_records: int
    success_count: int
    failed_count: int


class EntityLoader(ABC):
    """Abstract base class for entity loaders.
    
    This class provides the common interface and shared functionality
    for all entity loaders, eliminating code duplication.
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        self.client = client
        self.db = db
        self.checkpoint_manager = checkpoint_manager
        self.error_logger = get_error_logger()

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Return the entity type this loader handles."""
        pass

    @property
    @abstractmethod
    def supports_pagination(self) -> bool:
        """Whether this entity type supports pagination."""
        pass

    @property
    @abstractmethod
    def supports_since_parameter(self) -> bool:
        """Whether this entity type supports the 'since' parameter for updates."""
        pass

    @abstractmethod
    def get_entities(self, limit: int = None, offset: int = None, **kwargs) -> Tuple[List, Dict]:
        """Get entities from the API."""
        pass

    @abstractmethod
    def load_entity_by_id(self, entity_id: int) -> bool:
        """Load a single entity by ID."""
        pass

    def get_query_params(self, update: bool = False) -> Dict[str, Any]:
        """Get query parameters for this entity type."""
        if update and self.supports_since_parameter:
            return self.checkpoint_manager.get_query_params(self.entity_type, update)
        return {}

    def get_initial_offset(self, update: bool = False) -> int:
        """Get the initial API offset for loading.
        
        Since checkpoints now store both total records processed and API offset,
        we can directly use the stored API offset for resuming.
        """
        if update and self.supports_since_parameter:
            return 0

        # Use the stored API offset for resuming
        return self.checkpoint_manager.get_api_offset(self.entity_type)

    def load_all(self, batch_size: int = 50, update: bool = False) -> LoadResult:
        """Load all entities of this type.
        
        This method provides the common pagination and processing logic
        that was duplicated across all load functions.
        """
        try:
            query_params = self.get_query_params(update)
            offset = self.get_initial_offset(update)

            logger.info(f"Starting {self.entity_type} load with params: {query_params}")

            if self.supports_pagination:
                return self._load_with_pagination(batch_size, offset, query_params)
            else:
                return self._load_all_at_once(query_params)

        except Exception as e:
            logger.error(f"Error in load_{self.entity_type}: {str(e)}")
            self._log_operation_error(e)
            raise

    def _load_with_pagination(self, batch_size: int, offset: int, query_params: Dict) -> LoadResult:
        """Load entities using pagination.
        
        This method contains the pagination logic that was duplicated
        across all load functions.
        """
        total_records = 0
        success_count = 0
        failed_count = 0
        api_offset = offset  # Track API pagination offset separately

        while True:
            items, pagination = self.get_entities(limit=batch_size, offset=api_offset, **query_params)

            if not items:
                logger.info(f"No more {self.entity_type} to load")
                self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing {self.entity_type} ID: {item.id}")
                    success = self.load_entity_by_id(item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    self._log_item_error(item, e)
                    continue

            # Update checkpoint with total records processed and current API offset
            self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset)

            # Check for next page
            if not pagination.get('next'):
                logger.info(f"Reached end of {self.entity_type}")
                self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset, completed=True)
                break

            next_offset = self.client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset, completed=True)
                break

            api_offset = next_offset

        logger.info(f"Completed loading {self.entity_type}. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")
        return LoadResult(total_records, success_count, failed_count)

    def _load_all_at_once(self, query_params: Dict) -> LoadResult:
        """Load all entities at once (for entities that don't support pagination)."""
        total_records = 0
        success_count = 0
        failed_count = 0

        items, _ = self.get_entities(**query_params)

        if not items:
            self.checkpoint_manager.save_checkpoint(self.entity_type, 0, 0, completed=True)
            return LoadResult(0, 0, 0)

        for item in items:
            total_records += 1
            try:
                logger.info(f"Processing {self.entity_type} ID: {item.id}")
                success = self.load_entity_by_id(item.id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                self._log_item_error(item, e)
                continue

        self.checkpoint_manager.save_checkpoint(self.entity_type, len(items), 0, completed=True)
        logger.info(f"Completed loading {self.entity_type}. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")
        return LoadResult(total_records, success_count, failed_count)

    def _log_item_error(self, item: Any, error: Exception) -> None:
        """Log error for a specific item."""
        additional_data = self._get_item_error_data(item)
        self._log_error(self.entity_type, item.id, error, additional_data)

    def _log_operation_error(self, error: Exception) -> None:
        """Log error for the entire operation."""
        self._log_error(self.entity_type, 0, error, {'operation': f'load_{self.entity_type}'})

    def _log_error(self, entity_type: str, entity_id: int, error: Exception, additional_data: Dict = None) -> None:
        """Centralized error logging."""
        error_type = type(error).__name__
        error_message = str(error)

        if isinstance(error, SQLAlchemyError):
            error_message = error_message.split('\n')[0]

        logger.error(f"Error processing {entity_type} {entity_id}: {error_message}")
        self.error_logger.log_error(entity_type=entity_type, entity_id=entity_id, error_type=error_type, error_message=error_message, additional_data=additional_data)

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging. Override in subclasses."""
        return {}


class BaseEntityLoader(EntityLoader):
    """Base implementation for simple entity loaders.
    
    This class provides a standard implementation for entities that follow
    the common pattern, eliminating the need to duplicate the same logic
    across multiple loaders.
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any, entity_type: str, get_method: str, get_by_id_method: str):
        super().__init__(client, db, checkpoint_manager)
        self._entity_type = entity_type
        self._get_method = get_method
        self._get_by_id_method = get_by_id_method

    @property
    def entity_type(self) -> str:
        return self._entity_type

    @property
    def supports_pagination(self) -> bool:
        return True

    @property
    def supports_since_parameter(self) -> bool:
        # Most entities support since parameter, override in subclasses if needed
        return True

    def get_entities(self, limit: int = None, offset: int = None, **kwargs) -> Tuple[List, Dict]:
        """Get entities using the specified get method."""
        method = getattr(self.client, self._get_method)

        # For entities that don't support pagination, don't pass limit/offset
        if not self.supports_pagination:
            return method(**kwargs)

        # For entities that support pagination, ensure limit and offset are provided
        if limit is None:
            limit = 50  # Default limit
        if offset is None:
            offset = 0  # Default offset

        return method(limit=limit, offset=offset, **kwargs)

    @exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
    def load_entity_by_id(self, entity_id: int) -> bool:
        """Load a single entity by ID using the specified method.
        
        This method provides the common error handling and database operations
        that were duplicated across all individual load functions.
        """
        try:
            logger.info(f"Loading {self.entity_type} ID: {entity_id}")

            method = getattr(self.client, self._get_by_id_method)
            full_entity = method(entity_id)
            logger.info(f"Retrieved full {self.entity_type} details for ID: {entity_id}")

            # Handle entity-specific processing
            self._process_entity(full_entity)

            # Use merge instead of add to handle both inserts and updates
            self.db.merge(full_entity)
            self.db.commit()

            logger.info(f"Successfully processed {self.entity_type} ID: {entity_id}")
            return True

        except (KeapRateLimitError, KeapServerError) as e:
            # These are retryable errors, let the decorator handle them
            logger.warning(f"Retryable error processing {self.entity_type} ID {entity_id}: {e}")
            raise
        except KeapQuotaExhaustedError as e:
            # Quota exhaustion is not retryable, log and return False
            logger.error(f"Quota exhausted while processing {self.entity_type} ID {entity_id}: {e}")
            self._log_error(self.entity_type, entity_id, e, {f'{self.entity_type}_id': entity_id})
            return False
        except Exception as e:
            # Other errors are not retryable
            self.db.rollback()
            logger.error(f"Error processing {self.entity_type} ID {entity_id}: {e}")
            self._log_error(self.entity_type, entity_id, e, {f'{self.entity_type}_id': entity_id})
            return False

    def _process_entity(self, entity: Any) -> None:
        """Process entity-specific logic. Override in subclasses for customization."""
        pass
