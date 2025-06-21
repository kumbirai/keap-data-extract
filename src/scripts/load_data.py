import json
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.api.exceptions import KeapRateLimitError, KeapServerError, KeapQuotaExhaustedError
from src.database.config import SessionLocal
from src.models.models import (Affiliate, CustomField, Product, Tag, TagCategory, SubscriptionPlan)
from src.transformers.transformers import (transform_credit_card, transform_tag)
from src.utils.error_logger import ErrorLogger
from src.utils.global_logger import get_error_logger, initialize_loggers
from src.utils.logging_config import setup_logging
from src.utils.retry import exponential_backoff

# Create logs and checkpoints directories if they don't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('checkpoints', exist_ok=True)

# Setup logging
setup_logging(log_level=logging.INFO, log_dir="logs", app_name="keap_data_extract")

# Get logger for this module
logger = logging.getLogger(__name__)

# Initialize error logger
error_logger = ErrorLogger()


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
        """Log audit information for a data load operation.
        
        Args:
            entity_type: The type of entity being loaded
            start_time: Start time of the operation
            end_time: End time of the operation
            total_records: Total number of records processed
            success: Number of successful records
            failed: Number of failed records
        """
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Format as HH:MM:SS

        audit_entry = {'entity_type': entity_type, 'start_time': start_time.isoformat(), 'end_time': end_time.isoformat(), 'total_records': total_records, 'success': success, 'failed': failed,
                       'duration': duration_str}

        if entity_type not in self.audits:
            self.audits[entity_type] = []

        self.audits[entity_type].append(audit_entry)

        with open(self.audit_file, 'w') as f:
            json.dump(self.audits, f, indent=2)

        logger.info(f"Audit log for {entity_type}: Total={total_records}, Success={success}, "
                    f"Failed={failed}, Duration={duration_str}")


def audit_load_operation(func):
    """Decorator to add audit logging to load functions."""

    def wrapper(*args, **kwargs):
        start_time = datetime.now(timezone.utc)
        total_records = 0
        success_count = 0
        failed_count = 0

        try:
            # Extract entity_type from function name
            entity_type = func.__name__.replace('load_', '')

            # Call the original function
            result = func(*args, **kwargs)

            # If the function returns a tuple of (total, success, failed), use those values
            if isinstance(result, tuple) and len(result) == 3:
                total_records, success_count, failed_count = result
            else:
                # Otherwise, try to get counts from the function's local variables
                frame = func.__globals__
                if 'total_records' in frame:
                    total_records = frame['total_records']
                if 'success_count' in frame:
                    success_count = frame['success_count']
                if 'failed_count' in frame:
                    failed_count = frame['failed_count']

        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
        finally:
            end_time = datetime.now(timezone.utc)
            # Get the audit logger from the first argument (self)
            audit_logger = args[0].audit_logger if hasattr(args[0], 'audit_logger') else None
            if audit_logger:
                audit_logger.log_audit(entity_type=entity_type, start_time=start_time, end_time=end_time, total_records=total_records, success=success_count, failed=failed_count)

        return result

    return wrapper


class CheckpointManager:
    def __init__(self, checkpoint_file: str = 'checkpoints/load_progress.json'):
        self.checkpoint_file = checkpoint_file
        # Create directory if it doesn't exist
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

    def save_checkpoint(self, entity_type: str, offset: int, completed: bool = False) -> None:
        """Save checkpoint with optional completion timestamp.
        
        Args:
            entity_type: The type of entity being loaded
            offset: The current offset value
            completed: Whether this is a completion checkpoint
        """
        if entity_type not in self.checkpoints:
            self.checkpoints[entity_type] = {'offset': 0, 'last_loaded': None}

        self.checkpoints[entity_type]['offset'] = offset
        if completed:
            self.checkpoints[entity_type]['last_loaded'] = datetime.now(timezone.utc).isoformat()

        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoints, f, indent=2)
        logger.debug(f"Saved checkpoint for {entity_type} at offset {offset}")

    def get_checkpoint(self, entity_type: str) -> int:
        """Get the current offset for an entity type."""
        return self.checkpoints.get(entity_type, {}).get('offset', 0)

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
        """Get query parameters based on entity type and update flag.
        
        Args:
            entity_type: The type of entity being loaded
            update: Whether this is an update operation
            
        Returns:
            Dict containing the query parameters to use
        """
        params = {}

        if update:
            last_loaded = self.get_last_loaded_timestamp(entity_type)
            if last_loaded:
                # If we have a last_loaded timestamp, use it for the since parameter
                params['since'] = last_loaded

        return params


def log_error(error_logger: ErrorLogger, entity_type: str, entity_id: int, error: Exception, additional_data: Dict = None) -> None:
    """Helper function to log errors in a concise format.
    
    Args:
        error_logger: The error logger instance
        entity_type: Type of entity being processed
        entity_id: ID of the entity
        error: The exception that occurred
        additional_data: Additional data to include in the error log
    """
    error_type = type(error).__name__
    error_message = str(error)

    # For database errors, extract just the error message without the SQL details
    if isinstance(error, SQLAlchemyError):
        error_message = error_message.split('\n')[0]

    logger.error(f"Error processing {entity_type} {entity_id}: {error_message}")

    error_logger.log_error(entity_type=entity_type, entity_id=entity_id, error_type=error_type, error_message=error_message, additional_data=additional_data)


@audit_load_operation
def load_custom_fields(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> Tuple[int, int, int]:
    """Load all custom fields from all entity models.
    
    This function loads custom fields from all supported entity models:
    - contacts
    - companies
    - opportunities
    - orders
    - subscriptions
    
    Since custom fields are defined in the model endpoints and don't support pagination,
    we load them all at once for each entity type.
    
    Args:
        client: KeapClient instance for API calls
        db: Database session for database operations
        checkpoint_manager: CheckpointManager instance for tracking progress
        batch_size: Not used for custom fields as they are loaded all at once
        update: Whether this is an update operation
        
    Returns:
        Tuple containing:
        - total_records: Total number of records processed
        - success_count: Number of successfully processed records
        - failed_count: Number of failed records
    """
    checkpoint_entity_type = 'custom_fields'  # Used for checkpoint tracking
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()  # Initialize error logger

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(checkpoint_entity_type, update)

        logger.info("Fetching custom fields from all entity models")
        all_custom_fields = client.get_all_custom_fields(**query_params)

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
                    existing_field = db.query(CustomField).filter(CustomField.id == field.id).first()

                    if existing_field:
                        # Update existing field
                        for key, value in field.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_field, key, value)
                        db.merge(existing_field)
                    else:
                        # Add new field
                        db.merge(field)

                    # Commit after each field to maintain atomicity
                    db.commit()
                    success_count += 1

                    # Log metadata if present
                    if field.field_metadata:
                        logger.debug(f"Field {field.name} has metadata: {field.field_metadata}")

                except SQLAlchemyError as e:
                    failed_count += 1
                    logger.error(f"Database error processing custom field {field.id} from {model_entity_type}: {str(e)}")
                    log_error(error_logger, 'custom_fields', field.id, e, {'model_entity_type': model_entity_type, 'field_name': getattr(field, 'name', None)})
                    db.rollback()
                    continue
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing custom field {field.id} from {model_entity_type}: {str(e)}")
                    log_error(error_logger, 'custom_fields', field.id, e, {'model_entity_type': model_entity_type, 'field_name': getattr(field, 'name', None)})
                    db.rollback()
                    continue

        # Mark as completed since we load all fields at once
        checkpoint_manager.save_checkpoint(checkpoint_entity_type, total_records, completed=True)

        if failed_count > 0:
            logger.warning(f"Failed to process {failed_count} custom fields")

        logger.info(f"Successfully loaded {success_count} out of {total_records} custom fields")

    except Exception as e:
        logger.error(f"Error loading custom fields: {str(e)}")
        log_error(error_logger, 'custom_fields', 0, e, {'operation': 'load_custom_fields'})
        raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_tags(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load tags from the API into the database."""
    entity_type = 'tags'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        # If update is True and we have a last_loaded timestamp, we don't need to use offset
        if update and 'since' in query_params:
            offset = 0
        else:
            offset = checkpoint_manager.get_checkpoint(entity_type)

        logger.info(f"Starting tag load with params: {query_params}")

        while True:
            # Get batch of tags
            items, pagination = client.get_tags(limit=batch_size, offset=offset, **query_params)
            if not items:
                logger.info("No more tags to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            total_records += len(items)
            logger.info(f"Retrieved {len(items)} tags (offset: {offset})")

            # Process items
            for item in items:
                # Log tag being processed
                tag_id = item.id if hasattr(item, 'id') else (item.get('id', 0) if isinstance(item, dict) else 0)
                tag_name = item.name if hasattr(item, 'name') else (item.get('name', '') if isinstance(item, dict) else '')
                logger.info(f"Processing tag ID: {tag_id}, Name: {tag_name}")

                try:
                    # Transform and save tag
                    tag = transform_tag(item) if isinstance(item, dict) else item
                    if tag:
                        # Handle tag category if present
                        if hasattr(tag, 'category_id') and tag.category_id:
                            try:
                                # Check if category exists
                                existing_category = db_session.query(TagCategory).filter_by(id=tag.category_id).first()
                                if not existing_category:
                                    # Create new category
                                    category = TagCategory(id=tag.category_id, name=tag.category.name if hasattr(tag, 'category') else '')
                                    db_session.merge(category)
                                    db_session.flush()
                            except Exception as e:
                                logger.warning(f"Error handling tag category for tag {tag_id}: {str(e)}")  # Continue processing the tag even if category handling fails

                        # Use merge instead of add to handle both inserts and updates
                        db_session.merge(tag)
                        success_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, tag_id, e, {'name': tag_name})
                    db_session.rollback()
                    continue

            # Commit the batch
            try:
                db_session.commit()
                logger.info(f"Committed batch of {len(items)} tags")
            except Exception as e:
                logger.error(f"Error committing batch: {str(e)}")
                db_session.rollback()
                failed_count += len(items)
                success_count -= len(items)
                continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of tags")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading tags. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_tags: {str(e)}")
        raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_products(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load products from Keap API into database."""
    entity_type = 'products'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Note: Products API doesn't support 'since' parameter
        query_params = {}  # No special query parameters for products

        # Always start from offset 0 to ensure we get all products
        offset = 0

        logger.info(f"Starting products load with offset: {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_products(limit=batch_size, offset=offset, **query_params)
            logger.debug(f"Retrieved {len(items)} products from API")

            if not items:
                logger.info("No more products to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing product ID: {item.id}")
                    success = load_product_by_id(client, db_session, item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'product_name': getattr(item, 'product_name', None), 'sku': getattr(item, 'sku', None)})
                    logger.error(f"Error processing product ID {item.id}: {e}")
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of products")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading products. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_products: {str(e)}")
        raise

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_product_by_id(client: KeapClient, db_session: Session, product_id: int) -> bool:
    """Load a single product by ID from Keap API into database.
    
    This function also handles subscription plans that are embedded in the product API response.
    """
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading product ID: {product_id}")

        # Get full product details (includes subscription plans)
        full_product = client.get_product(product_id)
        logger.info(f"Retrieved full product details for ID: {product_id}")

        # Store subscription plans for later handling
        product_subscription_plans = full_product.subscription_plans if hasattr(full_product, 'subscription_plans') else []

        # Clear subscription plans from the product to avoid relationship conflicts
        if hasattr(full_product, 'subscription_plans'):
            full_product.subscription_plans = []

        # Use merge to handle both new and existing products
        # This will insert if the product doesn't exist, or update if it does
        merged_product = db_session.merge(full_product)
        
        # Handle relationships if needed
        if hasattr(full_product, 'options'):
            merged_product.options = full_product.options

        # Handle subscription plans after the product is merged
        if product_subscription_plans:
            for subscription_plan in product_subscription_plans:
                try:
                    # Ensure the subscription plan has the correct product_id
                    subscription_plan.product_id = product_id
                    # Merge the subscription plan
                    merged_plan = db_session.merge(subscription_plan)
                    # Add to the product's subscription plans relationship
                    merged_product.subscription_plans.append(merged_plan)
                except Exception as e:
                    logger.warning(f"Error processing subscription plan {subscription_plan.id} for product {product_id}: {str(e)}")
                    continue

        db_session.commit()
        logger.info(f"Successfully processed product ID: {product_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing product ID {product_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing product ID {product_id}: {e}")
        log_error(error_logger, 'products', product_id, e, {'product_id': product_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing product ID {product_id}: {e}")
        # Log to error file
        log_error(error_logger, 'products', product_id, e, {'product_id': product_id})
        return False


@audit_load_operation
def load_contacts(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load contacts from Keap API into database."""
    entity_type = 'contacts'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        # If update is True and we have a last_loaded timestamp, we don't need to use offset
        if update and 'since' in query_params:
            offset = 0
        else:
            offset = checkpoint_manager.get_checkpoint(entity_type)

        logger.info(f"Starting contact load with params: {query_params}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_contacts(limit=batch_size, offset=offset, **query_params)
            logger.debug(f"Retrieved {len(items)} contacts from API")

            if not items:
                logger.info("No more contacts to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing contact ID: {item.id}")
                    success = load_contact_by_id(client, db, item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e,
                              {'id': item.id, 'given_name': getattr(item, 'given_name', None), 'family_name': getattr(item, 'family_name', None), 'date_created': getattr(item, 'date_created', None),
                               'last_updated': getattr(item, 'last_updated', None)})
                    logger.error(f"Error processing contact ID {item.id}: {e}")
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of contacts")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading contacts. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_contacts: {str(e)}")
        raise

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_contact_by_id(client: KeapClient, db_session: Session, contact_id: int) -> bool:
    """Load a single contact by ID from Keap API into database."""
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading contact ID: {contact_id}")

        # Get full contact details
        full_contact = client.get_contact(contact_id)
        logger.info(f"Retrieved full contact details for ID: {contact_id}")

        # Get credit cards for this contact
        try:
            credit_cards_data, _ = client.get_contact_credit_cards(contact_id)
            logger.info(f"Retrieved {len(credit_cards_data)} credit cards for contact {contact_id}")
            # Transform credit card dictionaries into model instances
            credit_cards = [transform_credit_card(card_data) for card_data in credit_cards_data]
        except Exception as e:
            logger.info(f"Error fetching credit cards for contact {contact_id}: {e}")
            credit_cards = []

        # Get tag IDs and existing tags
        tags = full_contact.tags if hasattr(full_contact, 'tags') else []
        tag_ids = [tag.id for tag in tags]
        existing_tags = db_session.query(Tag).filter(Tag.id.in_(tag_ids)).all()

        # Clear existing credit cards and set new ones
        full_contact.credit_cards = []
        for credit_card in credit_cards:
            full_contact.credit_cards.append(credit_card)

        # Set other relationships before merging
        if hasattr(full_contact, 'email_addresses'):
            full_contact.email_addresses = full_contact.email_addresses
        if hasattr(full_contact, 'phone_numbers'):
            full_contact.phone_numbers = full_contact.phone_numbers
        if hasattr(full_contact, 'addresses'):
            full_contact.addresses = full_contact.addresses
        if hasattr(full_contact, 'tags'):
            # Clear existing tags and set new ones
            full_contact.tags = []
            for tag in existing_tags:
                full_contact.tags.append(tag)
        if hasattr(full_contact, 'custom_field_values'):
            full_contact.custom_field_values = full_contact.custom_field_values

        # Use merge instead of add to handle both inserts and updates
        db_session.merge(full_contact)
        db_session.commit()

        logger.info(f"Successfully processed contact ID: {contact_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing contact ID {contact_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing contact ID {contact_id}: {e}")
        log_error(error_logger, 'contacts', contact_id, e, {'contact_id': contact_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing contact ID {contact_id}: {e}")
        # Log to error file
        log_error(error_logger, 'contacts', contact_id, e, {'contact_id': contact_id})
        return False


@audit_load_operation
def load_opportunities(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load opportunities from Keap API into database."""
    entity_type = 'opportunities'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Note: Opportunities API doesn't support 'since' parameter
        query_params = {}  # No special query parameters for opportunities

        # Always start from offset 0 to ensure we get all opportunities
        offset = 0

        logger.info(f"Starting opportunities load with offset: {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_opportunities(limit=batch_size, offset=offset, **query_params)
            logger.debug(f"Retrieved {len(items)} opportunities from API")

            if not items:
                logger.info("No more opportunities to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing opportunity ID: {item.id}")
                    success = load_opportunity_by_id(client, db_session, item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'title': getattr(item, 'title', None)})
                    logger.error(f"Error processing opportunity ID {item.id}: {e}")
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of opportunities")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading opportunities. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_opportunities: {str(e)}")
        raise

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_opportunity_by_id(client: KeapClient, db_session: Session, opportunity_id: int) -> bool:
    """Load a single opportunity by ID from Keap API into database."""
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading opportunity ID: {opportunity_id}")

        # Get full opportunity details
        full_opportunity = client.get_opportunity(opportunity_id)
        logger.info(f"Retrieved full opportunity details for ID: {opportunity_id}")

        # Ensure title is never None
        if full_opportunity.title is None:
            full_opportunity.title = ""

        # Clear and set relationships
        if hasattr(full_opportunity, 'contacts'):
            full_opportunity.contacts = full_opportunity.contacts

        if hasattr(full_opportunity, 'custom_field_values'):
            full_opportunity.custom_field_values = full_opportunity.custom_field_values

        # Use merge instead of add to handle both inserts and updates
        db_session.merge(full_opportunity)
        db_session.commit()

        logger.info(f"Successfully processed opportunity ID: {opportunity_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing opportunity ID {opportunity_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing opportunity ID {opportunity_id}: {e}")
        log_error(error_logger, 'opportunities', opportunity_id, e, {'opportunity_id': opportunity_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing opportunity ID {opportunity_id}: {e}")
        # Log to error file
        log_error(error_logger, 'opportunities', opportunity_id, e, {'opportunity_id': opportunity_id})
        return False


@audit_load_operation
def load_affiliates(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load all affiliates with their related data.
    
    This function loads affiliates and all their related data including:
    - Commissions
    - Payments
    - Clawbacks
    
    Args:
        client: KeapClient instance
        db: Database session
        checkpoint_manager: CheckpointManager instance
        batch_size: Number of affiliates to load per batch
        update: Whether this is an update operation
        
    Returns:
        Tuple of (total_records, success_count, failed_count)
    """
    entity_type = 'affiliates'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()  # Initialize error logger

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        logger.info(f"Starting affiliates load with params: {query_params}")

        # Get all affiliates in a single call
        items, _ = client.get_affiliates(**query_params)

        if not items:
            # Mark as completed when no items
            checkpoint_manager.save_checkpoint(entity_type, 0, completed=True)
            return total_records, success_count, failed_count

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    success = load_affiliate_by_id(client, db, item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'first_name': getattr(item, 'first_name', None), 'last_name': getattr(item, 'last_name', None)})
                    db.rollback()
                    continue

            # Mark as completed since we processed all items
            checkpoint_manager.save_checkpoint(entity_type, len(items), completed=True)
            logger.info(f"Completed loading affiliates. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

        except Exception as e:
            log_error(error_logger, entity_type, 0, e)
            db.rollback()
            raise

    except Exception as e:
        logger.error(f"Error in load_affiliates: {str(e)}")
        raise

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_affiliate_by_id(client: KeapClient, db_session: Session, affiliate_id: int) -> bool:
    """Load a single affiliate by ID from Keap API into database."""
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading affiliate ID: {affiliate_id}")

        # Get full affiliate details
        full_affiliate = client.get_affiliate(affiliate_id)
        logger.info(f"Retrieved full affiliate details for ID: {affiliate_id}")

        # Get affiliate payments
        try:
            payments, _ = client.get_affiliate_payments(affiliate_id)
            logger.info(f"Retrieved {len(payments)} payments for affiliate ID: {affiliate_id}")
        except Exception as e:
            logger.warning(f"Error getting payments for affiliate {affiliate_id}: {str(e)}")
            payments = []

        # Get affiliate clawbacks
        try:
            clawbacks, _ = client.get_affiliate_clawbacks(affiliate_id)
            logger.info(f"Retrieved {len(clawbacks)} clawbacks for affiliate ID: {affiliate_id}")
        except Exception as e:
            logger.warning(f"Error getting clawbacks for affiliate {affiliate_id}: {str(e)}")
            clawbacks = []

        # Clear and set relationships
        if hasattr(full_affiliate, 'payments'):
            full_affiliate.payments = []
            for payment in payments:
                full_affiliate.payments.append(payment)

        if hasattr(full_affiliate, 'clawbacks'):
            full_affiliate.clawbacks = []
            for clawback in clawbacks:
                full_affiliate.clawbacks.append(clawback)

        # Use merge instead of add to handle both inserts and updates
        db_session.merge(full_affiliate)
        db_session.commit()

        logger.info(f"Successfully processed affiliate ID: {affiliate_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing affiliate ID {affiliate_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing affiliate ID {affiliate_id}: {e}")
        log_error(error_logger, 'affiliates', affiliate_id, e, {'affiliate_id': affiliate_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing affiliate ID {affiliate_id}: {e}")
        # Log to error file
        log_error(error_logger, 'affiliates', affiliate_id, e, {'affiliate_id': affiliate_id})
        return False


@audit_load_operation
def load_affiliate_commissions(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load all affiliate commissions."""
    entity_type = 'affiliate_commissions'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    # Get query parameters based on update flag
    query_params = checkpoint_manager.get_query_params(entity_type, update)

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing commissions for affiliate ID: {affiliate_id}")
        current_offset = 0  # Reset offset for each affiliate

        while True:
            try:
                # Add affiliate_id to query params
                current_params = {**query_params, 'limit': batch_size, 'offset': current_offset}

                commissions, pagination = client.get_affiliate_commissions(affiliate_id, **current_params)
                logger.info(f"Received {len(commissions) if commissions else 0} commissions for affiliate {affiliate_id}")

                if not commissions:
                    break

                for commission in commissions:
                    total_records += 1
                    try:
                        # Validate commission data
                        if not commission.affiliate_id:
                            raise ValueError("Affiliate ID is required for commission")

                        # Use merge operation to handle both inserts and updates
                        merged_commission = db.merge(commission)
                        success_count += 1
                        db.commit()
                    except Exception as e:
                        failed_count += 1
                        log_error(error_logger, entity_type, commission.id, e, {'commission_data': commission.__dict__})
                        db.rollback()
                        continue

                logger.debug(f"Successfully processed batch of {success_count} commissions for affiliate {affiliate_id}")

                # Update offset based on next URL if available
                if pagination.get('next'):
                    next_offset = client._parse_next_url(pagination['next'])
                    if next_offset is not None:
                        current_offset = next_offset
                    else:
                        # If we can't parse the next URL, increment by batch size
                        current_offset += len(commissions)
                else:
                    # No more pages for this affiliate
                    break

            except Exception as e:
                log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id, 'offset': current_offset})
                db.rollback()
                # Continue with next batch
                current_offset += batch_size
                continue

    # Mark as completed since we process all affiliates
    checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
    logger.info(f"Loaded {total_records} commissions in total (Success: {success_count}, Failed: {failed_count})")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_programs(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load affiliate programs from Keap API into database."""
    entity_type = 'affiliate_programs'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        # Get all affiliate IDs
        affiliate_ids = [a.id for a in db.query(Affiliate).all()]

        for affiliate_id in affiliate_ids:
            logger.info(f"Processing programs for affiliate ID: {affiliate_id}")
            current_offset = 0  # Reset offset for each affiliate

            while True:
                try:
                    # Add affiliate_id to query params
                    current_params = {**query_params, 'limit': batch_size, 'offset': current_offset}

                    programs, pagination = client.get_affiliate_programs(affiliate_id, **current_params)
                    logger.info(f"Received {len(programs) if programs else 0} programs for affiliate {affiliate_id}")

                    if not programs:
                        break

                    for program in programs:
                        total_records += 1
                        try:
                            # Validate program data
                            if not program.affiliate_id:
                                raise ValueError("Affiliate ID is required for program")

                            # Use merge operation to handle both inserts and updates
                            merged_program = db.merge(program)
                            success_count += 1
                            db.commit()
                        except Exception as e:
                            failed_count += 1
                            log_error(error_logger, entity_type, program.id, e, {'program_data': program.__dict__})
                            db.rollback()
                            continue

                    logger.debug(f"Successfully processed batch of {success_count} programs for affiliate {affiliate_id}")

                    # Update offset based on next URL if available
                    if pagination.get('next'):
                        next_offset = client._parse_next_url(pagination['next'])
                        if next_offset is not None:
                            current_offset = next_offset
                        else:
                            # If we can't parse the next URL, increment by batch size
                            current_offset += len(programs)
                    else:
                        # No more pages for this affiliate
                        break

                except Exception as e:
                    log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id, 'offset': current_offset})
                    db.rollback()
                    # Continue with next batch
                    current_offset += batch_size
                    continue

        # Mark as completed since we process all affiliates
        checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
        logger.info(f"Loaded {total_records} programs in total (Success: {success_count}, Failed: {failed_count})")
        return total_records, success_count, failed_count

    except Exception as e:
        logger.error(f"Error in load_affiliate_programs: {str(e)}")
        log_error(error_logger, 'affiliate_programs', 0, e, {'operation': 'load_affiliate_programs'})
        raise


@audit_load_operation
def load_affiliate_redirects(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load all affiliate redirects."""
    entity_type = 'affiliate_redirects'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        # Get all affiliate IDs
        affiliate_ids = [a.id for a in db.query(Affiliate).all()]

        for affiliate_id in affiliate_ids:
            logger.info(f"Processing redirects for affiliate ID: {affiliate_id}")
            current_offset = 0  # Reset offset for each affiliate

            while True:
                try:
                    # Add affiliate_id to query params
                    current_params = {**query_params, 'limit': batch_size, 'offset': current_offset}

                    redirects, pagination = client.get_affiliate_redirects(affiliate_id, **current_params)
                    logger.info(f"Received {len(redirects) if redirects else 0} redirects for affiliate {affiliate_id}")

                    if not redirects:
                        break

                    for redirect in redirects:
                        total_records += 1
                        try:
                            # Validate redirect data
                            if not redirect.affiliate_id:
                                raise ValueError("Affiliate ID is required for redirect")

                            # Use merge operation to handle both inserts and updates
                            merged_redirect = db.merge(redirect)
                            success_count += 1
                            db.commit()
                        except Exception as e:
                            failed_count += 1
                            log_error(error_logger, entity_type, redirect.id, e, {'redirect_data': redirect.__dict__})
                            db.rollback()
                            continue

                    logger.debug(f"Successfully processed batch of {success_count} redirects for affiliate {affiliate_id}")

                    # Update offset based on next URL if available
                    if pagination.get('next'):
                        next_offset = client._parse_next_url(pagination['next'])
                        if next_offset is not None:
                            current_offset = next_offset
                        else:
                            # If we can't parse the next URL, increment by batch size
                            current_offset += len(redirects)
                    else:
                        # No more pages for this affiliate
                        break

                except Exception as e:
                    log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id, 'offset': current_offset})
                    db.rollback()
                    # Continue with next batch
                    current_offset += batch_size
                    continue

        # Mark as completed since we process all affiliates
        checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
        logger.info(f"Loaded {total_records} redirects in total (Success: {success_count}, Failed: {failed_count})")
        return total_records, success_count, failed_count

    except Exception as e:
        logger.error(f"Error in load_affiliate_redirects: {str(e)}")
        log_error(error_logger, 'affiliate_redirects', 0, e, {'operation': 'load_affiliate_redirects'})
        raise


@audit_load_operation
def load_affiliate_summaries(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load all affiliate summaries."""
    entity_type = 'affiliate_summaries'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    # Get query parameters based on update flag
    query_params = checkpoint_manager.get_query_params(entity_type, update)

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing summary for affiliate ID: {affiliate_id}")
        try:
            # Add affiliate_id to query params
            current_params = {**query_params, 'affiliate_id': affiliate_id}
            summary = client.get_affiliate_summary(**current_params)
            logger.info(f"Received summary for affiliate {affiliate_id}")

            if not summary:
                logger.warning(f"No summary found for affiliate {affiliate_id}")
                continue

            total_records += 1
            try:
                # Validate summary data
                if not summary.affiliate_id:
                    raise ValueError("Affiliate ID is required for summary")

                # Use merge operation to handle both inserts and updates
                merged_summary = db.merge(summary)
                success_count += 1
                db.commit()
                logger.debug(f"Successfully processed summary for affiliate {affiliate_id}")
            except Exception as e:
                failed_count += 1
                log_error(error_logger, entity_type, summary.id if summary else affiliate_id, e, {'summary_data': summary.__dict__ if summary else None})
                db.rollback()
                continue

        except Exception as e:
            failed_count += 1
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            db.rollback()
            continue

    # Mark as completed since we process all affiliates
    checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
    logger.info(f"Loaded {total_records} summaries in total (Success: {success_count}, Failed: {failed_count})")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_clawbacks(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load affiliate clawbacks from Keap API into database."""
    entity_type = 'affiliate_clawbacks'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        # Get all affiliate IDs
        affiliate_ids = [a.id for a in db.query(Affiliate).all()]

        for affiliate_id in affiliate_ids:
            logger.info(f"Processing clawbacks for affiliate ID: {affiliate_id}")
            current_offset = 0  # Reset offset for each affiliate

            while True:
                try:
                    # Add affiliate_id to query params
                    current_params = {**query_params, 'limit': batch_size, 'offset': current_offset}

                    clawbacks, pagination = client.get_affiliate_clawbacks(affiliate_id, **current_params)
                    logger.info(f"Received {len(clawbacks) if clawbacks else 0} clawbacks for affiliate {affiliate_id}")

                    if not clawbacks:
                        break

                    for clawback in clawbacks:
                        total_records += 1
                        try:
                            # Validate clawback data
                            if not clawback.affiliate_id:
                                raise ValueError("Affiliate ID is required for clawback")

                            # Use merge operation to handle both inserts and updates
                            merged_clawback = db.merge(clawback)
                            success_count += 1
                            db.commit()
                        except Exception as e:
                            failed_count += 1
                            log_error(error_logger, entity_type, clawback.id, e, {'clawback_data': clawback.__dict__})
                            db.rollback()
                            continue

                    logger.debug(f"Successfully processed batch of {success_count} clawbacks for affiliate {affiliate_id}")

                    # Update offset based on next URL if available
                    if pagination.get('next'):
                        next_offset = client._parse_next_url(pagination['next'])
                        if next_offset is not None:
                            current_offset = next_offset
                        else:
                            # If we can't parse the next URL, increment by batch size
                            current_offset += len(clawbacks)
                    else:
                        # No more pages for this affiliate
                        break

                except Exception as e:
                    log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id, 'offset': current_offset})
                    db.rollback()
                    # Continue with next batch
                    current_offset += batch_size
                    continue

        # Mark as completed since we process all affiliates
        checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
        logger.info(f"Loaded {total_records} clawbacks in total (Success: {success_count}, Failed: {failed_count})")
        return total_records, success_count, failed_count

    except Exception as e:
        logger.error(f"Error in load_affiliate_clawbacks: {str(e)}")
        raise


@audit_load_operation
def load_affiliate_payments(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load affiliate payments from Keap API into database."""
    entity_type = 'affiliate_payments'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        # Get all affiliate IDs
        affiliate_ids = [a.id for a in db.query(Affiliate).all()]

        for affiliate_id in affiliate_ids:
            logger.info(f"Processing payments for affiliate ID: {affiliate_id}")
            current_offset = 0  # Reset offset for each affiliate

            while True:
                try:
                    # Add affiliate_id to query params
                    current_params = {**query_params, 'limit': batch_size, 'offset': current_offset}

                    payments, pagination = client.get_affiliate_payments(affiliate_id, **current_params)
                    logger.info(f"Received {len(payments) if payments else 0} payments for affiliate {affiliate_id}")

                    if not payments:
                        break

                    for payment in payments:
                        total_records += 1
                        try:
                            # Validate payment data
                            if not payment.affiliate_id:
                                raise ValueError("Affiliate ID is required for payment")

                            # Use merge operation to handle both inserts and updates
                            merged_payment = db.merge(payment)
                            success_count += 1
                            db.commit()
                        except Exception as e:
                            failed_count += 1
                            log_error(error_logger, entity_type, payment.id, e, {'payment_data': payment.__dict__})
                            db.rollback()
                            continue

                    logger.debug(f"Successfully processed batch of {success_count} payments for affiliate {affiliate_id}")

                    # Update offset based on next URL if available
                    if pagination.get('next'):
                        next_offset = client._parse_next_url(pagination['next'])
                        if next_offset is not None:
                            current_offset = next_offset
                        else:
                            # If we can't parse the next URL, increment by batch size
                            current_offset += len(payments)
                    else:
                        # No more pages for this affiliate
                        break

                except Exception as e:
                    log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id, 'offset': current_offset})
                    db.rollback()
                    # Continue with next batch
                    current_offset += batch_size
                    continue

        # Mark as completed since we process all affiliates
        checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
        logger.info(f"Loaded {total_records} payments in total (Success: {success_count}, Failed: {failed_count})")
        return total_records, success_count, failed_count

    except Exception as e:
        logger.error(f"Error in load_affiliate_payments: {str(e)}")
        raise


@audit_load_operation
def load_orders(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load orders from Keap API into database."""
    entity_type = 'orders'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    # Get query parameters
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    offset = checkpoint_manager.get_checkpoint(entity_type)

    logger.info(f"Starting to load orders with offset {offset}")

    while True:
        # Make API call with limit and offset
        items, pagination = client.get_orders(limit=batch_size, offset=offset, **query_params)
        logger.debug(f"Retrieved {len(items)} orders from API")

        if not items:
            logger.info("No more orders to load")
            checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
            break

        # Process items
        for item in items:
            total_records += 1
            try:
                logger.info(f"Processing order ID: {item.id}")
                success = load_order_by_id(client, db_session, item.id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                log_error(error_logger, entity_type, item.id, e,
                          {'id': item.id, 'title': getattr(item, 'title', None), 'status': getattr(item, 'status', None), 'order_date': getattr(item, 'order_date', None)})
                logger.error(f"Error processing order ID {item.id}: {e}")
                continue

        # Update checkpoint with new offset
        new_offset = offset + len(items)
        checkpoint_manager.save_checkpoint(entity_type, new_offset)

        # Parse next URL to get the offset for the next batch
        next_offset = client._parse_next_url(pagination.get('next'))
        if next_offset is None:
            logger.info("No more pages to load")
            checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
            break

        offset = next_offset

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_order_by_id(client: KeapClient, db_session: Session, order_id: int) -> bool:
    """Load a single order by ID from Keap API into database."""
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading order ID: {order_id}")

        # Get full order details
        full_order = client.get_order(order_id)
        logger.info(f"Retrieved full order details for ID: {order_id}")

        # Get order payments
        try:
            payments = client.get_order_payments(order_id)
            logger.info(f"Retrieved {len(payments)} payments for order ID: {order_id}")
        except Exception as e:
            logger.warning(f"Error getting payments for order {order_id}: {str(e)}")
            payments = []

        # Get order transactions
        try:
            transactions = client.get_order_transactions(order_id)
            logger.info(f"Retrieved {len(transactions)} transactions for order ID: {order_id}")
        except Exception as e:
            logger.warning(f"Error getting transactions for order {order_id}: {str(e)}")
            transactions = []

        # Clear and set relationships
        if hasattr(full_order, 'payments'):
            full_order.payments = []
            for payment in payments:
                full_order.payments.append(payment)

        if hasattr(full_order, 'transactions'):
            full_order.transactions = []
            for transaction in transactions:
                full_order.transactions.append(transaction)

        if hasattr(full_order, 'contacts'):
            full_order.contacts = full_order.contacts

        if hasattr(full_order, 'custom_field_values'):
            full_order.custom_field_values = full_order.custom_field_values

        # Set affiliate IDs to None if they are 0
        if full_order.lead_affiliate_id == 0:
            full_order.lead_affiliate_id = None
        if full_order.sales_affiliate_id == 0:
            full_order.sales_affiliate_id = None

        # Use merge instead of add to handle both inserts and updates
        db_session.merge(full_order)
        db_session.commit()

        logger.info(f"Successfully processed order ID: {order_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing order ID {order_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing order ID {order_id}: {e}")
        log_error(error_logger, 'orders', order_id, e, {'order_id': order_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing order ID {order_id}: {e}")
        # Log to error file
        log_error(error_logger, 'orders', order_id, e, {'order_id': order_id})
        return False


@audit_load_operation
def load_tasks(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load tasks from Keap API into database."""
    entity_type = 'tasks'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        # If update is True and we have a last_loaded timestamp, we don't need to use offset
        if update and 'since' in query_params:
            offset = 0
        else:
            offset = checkpoint_manager.get_checkpoint(entity_type)

        logger.info(f"Starting tasks load with params: {query_params}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_tasks(limit=batch_size, offset=offset, **query_params)
            logger.debug(f"Retrieved {len(items)} tasks from API")

            if not items:
                logger.info("No more tasks to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing task ID: {item.id}")
                    success = load_task_by_id(client, db_session, item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e,
                              {'id': item.id, 'title': getattr(item, 'title', None), 'status': getattr(item, 'status', None), 'due_date': getattr(item, 'due_date', None)})
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

        logger.info(f"Completed loading tasks. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_tasks: {str(e)}")
        raise

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_task_by_id(client: KeapClient, db_session: Session, task_id: int) -> bool:
    """Load a single task by ID from Keap API into database."""
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading task ID: {task_id}")

        # Get full task details
        full_task = client.get_task(task_id)
        logger.info(f"Retrieved full task details for ID: {task_id}")

        # Get task contacts
        try:
            contacts = client.get_task_contacts(task_id)
            logger.info(f"Retrieved {len(contacts)} contacts for task ID: {task_id}")
        except Exception as e:
            logger.error(f"Error getting contacts for task {task_id}: {str(e)}")
            contacts = []

        # Set relationships before merging
        full_task.contacts = contacts

        # Use merge instead of add to handle both inserts and updates
        db_session.merge(full_task)
        db_session.commit()

        logger.info(f"Successfully processed task ID: {task_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing task ID {task_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing task ID {task_id}: {e}")
        log_error(error_logger, 'tasks', task_id, e, {'task_id': task_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing task ID {task_id}: {e}")
        # Log to error file
        log_error(error_logger, 'tasks', task_id, e, {'task_id': task_id})
        return False


@audit_load_operation
def load_notes(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load notes from Keap API into database."""
    entity_type = 'notes'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Note: Notes API doesn't support 'since' parameter
        query_params = {}  # No special query parameters for notes

        # Always start from offset 0 to ensure we get all notes
        offset = 0

        logger.info(f"Starting notes load with offset: {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_notes(limit=batch_size, offset=offset, **query_params)
            logger.debug(f"Retrieved {len(items)} notes from API")

            if not items:
                logger.info("No more notes to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing note ID: {item.id}")
                    success = load_note_by_id(client, db_session, item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'content': getattr(item, 'content', None)})
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of notes")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading notes. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_notes: {str(e)}")
        raise

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_note_by_id(client: KeapClient, db_session: Session, note_id: int) -> bool:
    """Load a single note by ID from Keap API into database."""
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading note ID: {note_id}")

        # Get full note details
        full_note = client.get_note(note_id)
        logger.info(f"Retrieved full note details for ID: {note_id}")

        # Use merge instead of add to handle both inserts and updates
        db_session.merge(full_note)
        db_session.commit()

        logger.info(f"Successfully processed note ID: {note_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing note ID {note_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing note ID {note_id}: {e}")
        log_error(error_logger, 'notes', note_id, e, {'note_id': note_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing note ID {note_id}: {e}")
        # Log to error file
        log_error(error_logger, 'notes', note_id, e, {'note_id': note_id})
        return False


@audit_load_operation
def load_campaigns(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load campaigns from Keap API into database."""
    entity_type = 'campaigns'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Note: Campaigns API doesn't support 'since' parameter
        query_params = {}  # No special query parameters for campaigns

        # Always start from offset 0 to ensure we get all campaigns
        offset = 0

        logger.info(f"Starting campaigns load with offset: {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_campaigns(limit=batch_size, offset=offset, **query_params)
            logger.debug(f"Retrieved {len(items)} campaigns from API")

            if not items:
                logger.info("No more campaigns to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing campaign ID: {item.id}")
                    success = load_campaign_by_id(client, db_session, item.id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'name': getattr(item, 'name', None)})
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of campaigns")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading campaigns. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_campaigns: {str(e)}")
        raise

    return total_records, success_count, failed_count


@exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
def load_campaign_by_id(client: KeapClient, db_session: Session, campaign_id: int) -> bool:
    """Load a single campaign by ID from Keap API into database."""
    error_logger = get_error_logger()  # Get error logger for file logging
    
    try:
        logger.info(f"Loading campaign ID: {campaign_id}")

        # Get full campaign details (includes sequences)
        full_campaign = client.get_campaign(campaign_id)
        logger.info(f"Retrieved full campaign details for ID: {campaign_id}")

        # Use merge instead of add to handle both inserts and updates
        db_session.merge(full_campaign)
        db_session.commit()

        logger.info(f"Successfully processed campaign ID: {campaign_id}")
        return True

    except (KeapRateLimitError, KeapServerError) as e:
        # These are retryable errors, let the decorator handle them
        logger.warning(f"Retryable error processing campaign ID {campaign_id}: {e}")
        raise
    except KeapQuotaExhaustedError as e:
        # Quota exhaustion is not retryable, log and return False
        logger.error(f"Quota exhausted while processing campaign ID {campaign_id}: {e}")
        log_error(error_logger, 'campaigns', campaign_id, e, {'campaign_id': campaign_id})
        return False
    except Exception as e:
        # Other errors are not retryable
        db_session.rollback()
        logger.error(f"Error processing campaign ID {campaign_id}: {e}")
        # Log to error file
        log_error(error_logger, 'campaigns', campaign_id, e, {'campaign_id': campaign_id})
        return False


@audit_load_operation
def load_subscriptions(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load subscriptions from Keap API into database."""
    entity_type = 'subscriptions'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = get_error_logger()

    try:
        # Get query parameters based on update flag
        query_params = checkpoint_manager.get_query_params(entity_type, update)

        logger.info(f"Starting subscriptions load with params: {query_params}")

        # Get all subscriptions in a single call
        items, _ = client.get_subscriptions(**query_params)

        if not items:
            # Mark as completed when no items
            checkpoint_manager.save_checkpoint(entity_type, 0, completed=True)
            return total_records, success_count, failed_count

        try:
            # Process items directly from the list response
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing subscription ID: {item.id}")
                    # Use merge instead of add to handle both inserts and updates
                    db_session.merge(item)
                    db_session.commit()
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'id': getattr(item, 'id', None)})
                    db_session.rollback()
                    continue

            # Mark as completed since we processed all items
            checkpoint_manager.save_checkpoint(entity_type, len(items), completed=True)
            logger.info(f"Completed loading subscriptions. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

        except Exception as e:
            log_error(error_logger, entity_type, 0, e)
            raise

    except Exception as e:
        logger.error(f"Error in load_subscriptions: {str(e)}")
        raise

    return total_records, success_count, failed_count


def main(update: bool = False, entity_type: str = None, entity_id: int = None):
    """Main function to perform the data load.
    
    Args:
        update: Whether to perform an update operation using last_loaded timestamps
        entity_type: Type of entity to load (products, contacts, affiliates, orders, opportunities, tasks, notes, campaigns, subscriptions)
        entity_id: ID of specific entity to load
    """
    start_time = datetime.now(timezone.utc)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Initialize logging and error logger
    initialize_loggers()

    client = KeapClient()
    db = SessionLocal()
    checkpoint_manager = CheckpointManager()

    # Initialize database tables
    from src.database.init_db import init_db
    init_db()

    if update:
        logger.info("Performing update operation...")
    else:
        logger.info("Starting full data load...")

    try:
        if entity_type and entity_id:
            # Load specific entity by ID
            success = False
            if entity_type == 'products':
                success = load_product_by_id(client, db, entity_id)
            elif entity_type == 'contacts':
                success = load_contact_by_id(client, db, entity_id)
            elif entity_type == 'affiliates':
                success = load_affiliate_by_id(client, db, entity_id)
            elif entity_type == 'orders':
                success = load_order_by_id(client, db, entity_id)
            elif entity_type == 'opportunities':
                success = load_opportunity_by_id(client, db, entity_id)
            elif entity_type == 'tasks':
                success = load_task_by_id(client, db, entity_id)
            elif entity_type == 'notes':
                success = load_note_by_id(client, db, entity_id)
            elif entity_type == 'campaigns':
                success = load_campaign_by_id(client, db, entity_id)
            else:
                logger.error(f"Unknown entity type: {entity_type}")
                return

            if success:
                success_count += 1
            else:
                failed_count += 1
        elif entity_type:
            # Load specific entity type (all records)
            if entity_type == 'custom_fields':
                custom_fields_total, custom_fields_success, custom_fields_failed = load_custom_fields(client, db, checkpoint_manager, update=update)
                total_records += custom_fields_total
                success_count += custom_fields_success
                failed_count += custom_fields_failed
            elif entity_type == 'tags':
                tags_total, tags_success, tags_failed = load_tags(client, db, checkpoint_manager, update=update)
                total_records += tags_total
                success_count += tags_success
                failed_count += tags_failed
            elif entity_type == 'products':
                products_total, products_success, products_failed = load_products(client, db, checkpoint_manager, update=update)
                total_records += products_total
                success_count += products_success
                failed_count += products_failed
            elif entity_type == 'contacts':
                contacts_total, contacts_success, contacts_failed = load_contacts(client, db, checkpoint_manager, update=update)
                total_records += contacts_total
                success_count += contacts_success
                failed_count += contacts_failed
            elif entity_type == 'opportunities':
                opportunities_total, opportunities_success, opportunities_failed = load_opportunities(client, db, checkpoint_manager, update=update)
                total_records += opportunities_total
                success_count += opportunities_success
                failed_count += opportunities_failed
            elif entity_type == 'affiliates':
                affiliates_total, affiliates_success, affiliates_failed = load_affiliates(client, db, checkpoint_manager, update=update)
                total_records += affiliates_total
                success_count += affiliates_success
                failed_count += affiliates_failed
            elif entity_type == 'orders':
                orders_total, orders_success, orders_failed = load_orders(client, db, checkpoint_manager, update=update)
                total_records += orders_total
                success_count += orders_success
                failed_count += orders_failed
            elif entity_type == 'tasks':
                tasks_total, tasks_success, tasks_failed = load_tasks(client, db, checkpoint_manager, update=update)
                total_records += tasks_total
                success_count += tasks_success
                failed_count += tasks_failed
            elif entity_type == 'notes':
                notes_total, notes_success, notes_failed = load_notes(client, db, checkpoint_manager, update=update)
                total_records += notes_total
                success_count += notes_success
                failed_count += notes_failed
            elif entity_type == 'campaigns':
                campaigns_total, campaigns_success, campaigns_failed = load_campaigns(client, db, checkpoint_manager, update=update)
                total_records += campaigns_total
                success_count += campaigns_success
                failed_count += campaigns_failed
            elif entity_type == 'subscriptions':
                subscriptions_total, subscriptions_success, subscriptions_failed = load_subscriptions(client, db, checkpoint_manager, update=update)
                total_records += subscriptions_total
                success_count += subscriptions_success
                failed_count += subscriptions_failed
            else:
                logger.error(f"Unknown entity type: {entity_type}")
                return
        else:
            # Load all data in a specific order to maintain referential integrity
            # First load custom fields since they are referenced by contacts
            custom_fields_total, custom_fields_success, custom_fields_failed = load_custom_fields(client, db, checkpoint_manager, update=update)
            total_records += custom_fields_total
            success_count += custom_fields_success
            failed_count += custom_fields_failed

            # Then load tags since they are referenced by contacts
            tags_total, tags_success, tags_failed = load_tags(client, db, checkpoint_manager, update=update)
            total_records += tags_total
            success_count += tags_success
            failed_count += tags_failed

            # Load products before orders and subscriptions (subscription plans are now handled as part of product loading)
            products_total, products_success, products_failed = load_products(client, db, checkpoint_manager, update=update)
            total_records += products_total
            success_count += products_success
            failed_count += products_failed

            # Then load contacts and their related data
            contacts_total, contacts_success, contacts_failed = load_contacts(client, db, checkpoint_manager, update=update)
            total_records += contacts_total
            success_count += contacts_success
            failed_count += contacts_failed

            # Load opportunities
            opportunities_total, opportunities_success, opportunities_failed = load_opportunities(client, db, checkpoint_manager, update=update)
            total_records += opportunities_total
            success_count += opportunities_success
            failed_count += opportunities_failed

            # Load affiliate data before orders since orders reference affiliates
            affiliates_total, affiliates_success, affiliates_failed = load_affiliates(client, db, checkpoint_manager, update=update)
            total_records += affiliates_total
            success_count += affiliates_success
            failed_count += affiliates_failed

            # Now load orders which depend on affiliates
            orders_total, orders_success, orders_failed = load_orders(client, db, checkpoint_manager, update=update)
            total_records += orders_total
            success_count += orders_success
            failed_count += orders_failed

            tasks_total, tasks_success, tasks_failed = load_tasks(client, db, checkpoint_manager, update=update)
            total_records += tasks_total
            success_count += tasks_success
            failed_count += tasks_failed

            notes_total, notes_success, notes_failed = load_notes(client, db, checkpoint_manager, update=update)
            total_records += notes_total
            success_count += notes_success
            failed_count += notes_failed

            campaigns_total, campaigns_success, campaigns_failed = load_campaigns(client, db, checkpoint_manager, update=update)
            total_records += campaigns_total
            success_count += campaigns_success
            failed_count += campaigns_failed

            subscriptions_total, subscriptions_success, subscriptions_failed = load_subscriptions(client, db, checkpoint_manager, update=update)
            total_records += subscriptions_total
            success_count += subscriptions_success
            failed_count += subscriptions_failed

        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time

        logger.info(f"Data load completed in {duration}")
        logger.info(f"Total records processed: {total_records}")
        logger.info(f"Successfully processed: {success_count}")
        logger.info(f"Failed to process: {failed_count}")
        # Run error reprocessing after main data load
        if not entity_type and not entity_id:  # Only run for full loads, not individual entity loads
            try:
                from src.scripts.reprocess_errors import ErrorReprocessor
                reprocessor = ErrorReprocessor()
                reprocessor.run()
                logger.info("Error reprocessing completed")
            except Exception as e:
                logger.error(f"Error during error reprocessing: {str(e)}")
                # Don't raise here - we don't want to fail the main load if reprocessing fails

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        db.close()

    


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Load data from Keap API into database')
    parser.add_argument('--update', action='store_true', help='Perform update operation using last_loaded timestamps')
    parser.add_argument('--entity-type', choices=['custom_fields', 'tags', 'products', 'contacts', 'affiliates', 'orders', 'opportunities', 'tasks', 'notes', 'campaigns', 'subscriptions'], help='Type of entity to load')
    parser.add_argument('--entity-id', type=int, help='ID of specific entity to load')

    args = parser.parse_args()

    main(update=args.update, entity_type=args.entity_type, entity_id=args.entity_id)
