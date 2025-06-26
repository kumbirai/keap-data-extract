"""
Specialized loader for custom fields.

Custom fields have a unique loading pattern - they are loaded from all
entity models at once and don't support pagination.
"""

import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.models import CustomField
from .base_loader import EntityLoader, LoadResult

logger = logging.getLogger(__name__)


class CustomFieldsLoader(EntityLoader):
    """Specialized loader for custom fields.
    
    Custom fields are unique because:
    1. They are loaded from all entity models at once
    2. They don't support pagination
    3. They don't support the 'since' parameter
    4. They require special handling for field metadata
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager)

    @property
    def entity_type(self) -> str:
        return "custom_fields"

    @property
    def supports_pagination(self) -> bool:
        return False  # Custom fields are loaded all at once

    @property
    def supports_since_parameter(self) -> bool:
        return False  # Custom fields don't support 'since' parameter

    def get_entities(self, limit: int = None, offset: int = None, **kwargs) -> Tuple[List, Dict]:
        """Get all custom fields from all entity models."""
        # Custom fields are loaded from all entity models
        all_custom_fields = self.client.get_all_custom_fields(**kwargs)
        return all_custom_fields, {}

    def load_entity_by_id(self, entity_id: int) -> bool:
        """Load a single custom field by ID.
        
        Note: This is not typically used for custom fields as they are
        loaded in bulk, but it's required by the interface.
        """
        try:
            logger.info(f"Loading custom field ID: {entity_id}")

            # Get the custom field from the database
            custom_field = self.db.query(CustomField).filter(CustomField.id == entity_id).first()
            if custom_field:
                logger.info(f"Successfully processed custom field ID: {entity_id}")
                return True
            else:
                logger.warning(f"Custom field ID {entity_id} not found")
                return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing custom field ID {entity_id}: {e}")
            self._log_error(self.entity_type, entity_id, e, {'custom_field_id': entity_id})
            return False

    def load_all(self, batch_size: int = 50, update: bool = False) -> LoadResult:
        """Load all custom fields from all entity models.
        
        This overrides the base implementation because custom fields have
        a unique loading pattern.
        """
        total_records = 0
        success_count = 0
        failed_count = 0

        try:
            logger.info("Fetching custom fields from all entity models")
            all_custom_fields = self.client.get_all_custom_fields()

            for model_entity_type, custom_fields in all_custom_fields.items():
                logger.info(f"Processing {len(custom_fields)} custom fields from {model_entity_type} model")

                if not custom_fields:
                    logger.warning(f"No custom fields found in {model_entity_type} model")
                    continue

                for field in custom_fields:
                    total_records += 1
                    try:
                        logger.info(f"Processing custom field ID: {field.id}, Name: {field.name}, Type: {field.type}")

                        # Check if field already exists
                        existing_field = self.db.query(CustomField).filter(CustomField.id == field.id).first()

                        if existing_field:
                            # Update existing field
                            for key, value in field.__dict__.items():
                                if not key.startswith('_'):
                                    setattr(existing_field, key, value)
                            self.db.merge(existing_field)
                        else:
                            # Add new field
                            self.db.merge(field)

                        # Commit after each field to maintain atomicity
                        self.db.commit()
                        success_count += 1

                        # Log metadata if present
                        if field.field_metadata:
                            logger.debug(f"Field {field.name} has metadata: {field.field_metadata}")

                    except SQLAlchemyError as e:
                        failed_count += 1
                        logger.error(f"Database error processing custom field {field.id} from {model_entity_type}: {str(e)}")
                        self._log_error(self.entity_type, field.id, e, {'model_entity_type': model_entity_type, 'field_name': getattr(field, 'name', None)})
                        self.db.rollback()
                        continue
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error processing custom field {field.id} from {model_entity_type}: {str(e)}")
                        self._log_error(self.entity_type, field.id, e, {'model_entity_type': model_entity_type, 'field_name': getattr(field, 'name', None)})
                        self.db.rollback()
                        continue

            # Mark as completed since we load all fields at once
            self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, 0, completed=True)

            if failed_count > 0:
                logger.warning(f"Failed to process {failed_count} custom fields")

            logger.info(f"Successfully loaded {success_count} out of {total_records} custom fields")

        except Exception as e:
            logger.error(f"Error loading custom fields: {str(e)}")
            self._log_operation_error(e)
            raise

        return LoadResult(total_records, success_count, failed_count)

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to custom fields."""
        return {'field_name': getattr(item, 'name', None), 'field_type': getattr(item, 'type', None), 'model_entity_type': getattr(item, 'model_entity_type', None)}
