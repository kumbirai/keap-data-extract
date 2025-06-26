"""
Specialized loader for tags.

Tags have special handling for tag categories and require transformation
from API response to model instances.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.exceptions import KeapQuotaExhaustedError, KeapRateLimitError, KeapServerError
from src.api.keap_client import KeapClient
from src.models.models import TagCategory
from src.transformers.transformers import transform_tag
from src.utils.retry import exponential_backoff
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class TagsLoader(BaseEntityLoader):
    """Specialized loader for tags with category handling.
    
    Tags are unique because:
    1. They may have associated tag categories
    2. They require transformation from API response
    3. They need special handling for category relationships
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "tags", "get_tags", "get_tag")

    def _process_entity(self, tag: Any) -> None:
        """Process tag-specific relationships.
        
        This method handles the tag category relationships that were
        duplicated in the original load_tags function.
        """
        # Handle tag category if present
        if hasattr(tag, 'category_id') and tag.category_id:
            try:
                # Check if category exists
                existing_category = self.db.query(TagCategory).filter_by(id=tag.category_id).first()
                if not existing_category:
                    # Create new category
                    category = TagCategory(id=tag.category_id, name=tag.category.name if hasattr(tag, 'category') else '')
                    self.db.merge(category)
                    self.db.flush()
            except Exception as e:
                logger.warning(f"Error handling tag category for tag {tag.id}: {str(e)}")  # Continue processing the tag even if category handling fails

    @exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
    def load_entity_by_id(self, entity_id: int) -> bool:
        """Load a single tag by ID with transformation."""
        try:
            logger.info(f"Loading tag ID: {entity_id}")

            # Get tag from API
            tag_data = self.client.get_tag(entity_id)
            logger.info(f"Retrieved tag details for ID: {entity_id}")

            # Transform tag data if it's a dictionary
            if isinstance(tag_data, dict):
                tag = transform_tag(tag_data)
            else:
                tag = tag_data

            if not tag:
                logger.warning(f"Failed to transform tag ID {entity_id}")
                return False

            # Handle entity-specific processing
            self._process_entity(tag)

            # Use merge instead of add to handle both inserts and updates
            self.db.merge(tag)
            self.db.commit()

            logger.info(f"Successfully processed tag ID: {entity_id}")
            return True

        except (KeapRateLimitError, KeapServerError) as e:
            # These are retryable errors, let the decorator handle them
            logger.warning(f"Retryable error processing tag ID {entity_id}: {e}")
            raise
        except KeapQuotaExhaustedError as e:
            # Quota exhaustion is not retryable, log and return False
            logger.error(f"Quota exhausted while processing tag ID {entity_id}: {e}")
            self._log_error(self.entity_type, entity_id, e, {'tag_id': entity_id})
            return False
        except Exception as e:
            # Other errors are not retryable
            self.db.rollback()
            logger.error(f"Error processing tag ID {entity_id}: {e}")
            self._log_error(self.entity_type, entity_id, e, {'tag_id': entity_id})
            return False

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to tags."""
        return {'name': getattr(item, 'name', None), 'category_id': getattr(item, 'category_id', None)}
