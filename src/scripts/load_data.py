import argparse
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.models.models import (Affiliate, Campaign, Contact, CustomField, Note, Opportunity, Order, PaymentGateway, PaymentPlan, Product, Subscription, SubscriptionPlan, Task, TagCategory)
from src.utils.error_logger import ErrorLogger
from src.utils.logging_config import setup_logging
from src.utils.transformers import (transform_credit_card, transform_shipping_information, transform_tag)

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
        self.checkpoints = self._load_checkpoints()
        self.audit_logger = AuditLogger()

    def _load_checkpoints(self) -> Dict:
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
        return self.checkpoints.get(entity_type, {}).get('offset', 0)

    def get_last_loaded_timestamp(self, entity_type: str) -> Optional[str]:
        return self.checkpoints.get(entity_type, {}).get('last_loaded')

    def clear_checkpoints(self) -> None:
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
def load_contacts(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load contacts from Keap API into database."""
    entity_type = 'contacts'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    try:
        # Get initial offset from checkpoint
        offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Starting contact load from offset {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_contacts(limit=batch_size, offset=offset, db_session=db)
            logger.debug(f"Retrieved {len(items)} contacts from API")

            if not items:
                logger.info("No more contacts to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing contact ID: {item.id}, Name: {item.given_name} {item.family_name}")

                    # First, check if contact exists
                    existing_contact = db.query(Contact).filter(Contact.id == item.id).first()

                    if existing_contact:
                        # Update existing contact's attributes
                        for key, value in item.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_contact, key, value)
                        db.add(existing_contact)
                    else:
                        # Add new contact
                        db.add(item)

                    # Fetch and process credit cards for this contact
                    try:
                        credit_cards, _ = client.get_contact_credit_cards(item.id)
                        for card_data in credit_cards:
                            try:
                                card = transform_credit_card(card_data)
                                if existing_contact:
                                    existing_contact.credit_cards.append(card)
                                else:
                                    item.credit_cards.append(card)
                            except Exception as e:
                                logger.error(f"Error transforming credit card for contact {item.id}: {e}")
                                continue
                    except Exception as e:
                        logger.error(f"Error fetching credit cards for contact {item.id}: {e}")
                        # Continue with next contact even if credit card fetch fails
                        continue

                    db.commit()
                    success_count += 1
                    logger.debug(f"Successfully processed contact ID: {item.id}")

                except Exception as e:
                    db.rollback()
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e)
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


@audit_load_operation
def load_tags(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load tags from the API into the database."""
    entity_type = 'tags'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    try:
        # Get initial offset from checkpoint
        offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Starting tag load from offset {offset}")

        while True:
            # Get batch of tags
            items, pagination = client.get_tags(limit=batch_size, offset=offset)
            if not items:
                logger.info("No more tags to load")
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
                                logger.warning(f"Error handling tag category for tag {tag_id}: {str(e)}")
                                # Continue processing the tag even if category handling fails

                        # Use merge instead of add to handle both inserts and updates
                        db_session.merge(tag)
                        success_count += 1
                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, tag_id, e, {'name': tag_name})
                    logger.error(f"Error processing tag {tag_id}: {str(e)}")
                    # Roll back the session for this item
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

    try:
        logger.info("Fetching custom fields from all entity models")
        all_custom_fields = client.get_all_custom_fields()

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
                        db.add(existing_field)
                    else:
                        # Add new field
                        db.add(field)

                    # Commit after each field to maintain atomicity
                    db.commit()
                    success_count += 1

                    # Log metadata if present
                    if field.field_metadata:
                        logger.debug(f"Field {field.name} has metadata: {field.field_metadata}")

                except SQLAlchemyError as e:
                    failed_count += 1
                    logger.error(f"Database error processing custom field {field.id} from {model_entity_type}: {str(e)}")
                    db.rollback()
                    continue
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing custom field {field.id} from {model_entity_type}: {str(e)}")
                    db.rollback()
                    continue

        # Mark as completed since we load all fields at once
        checkpoint_manager.save_checkpoint(checkpoint_entity_type, total_records, completed=True)

        if failed_count > 0:
            logger.warning(f"Failed to process {failed_count} custom fields")

        logger.info(f"Successfully loaded {success_count} out of {total_records} custom fields")

    except Exception as e:
        logger.error(f"Error loading custom fields: {str(e)}")
        raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_opportunities(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load opportunities from Keap API into database."""
    entity_type = 'opportunities'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        try:
            # Make API call with limit and offset
            items, pagination = client.get_opportunities(limit=batch_size, offset=current_offset)

            if not items:
                # Mark as completed when no more items
                checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing opportunity ID: {item.id}, Title: {item.title}")

                    # Get full opportunity details
                    full_opportunity = client.get_opportunity(item.id)
                    logger.info(f"Retrieved full opportunity details for ID: {item.id}")

                    # First, check if opportunity exists
                    existing_opportunity = db_session.query(Opportunity).filter(Opportunity.id == item.id).first()

                    if existing_opportunity:
                        # Update existing opportunity's attributes
                        for key, value in full_opportunity.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_opportunity, key, value)

                        # Clear existing relationships
                        existing_opportunity.custom_field_values = []
                        existing_opportunity.contacts = []

                        # Add new relationships using SQLAlchemy's native relationship handling
                        existing_opportunity.custom_field_values = full_opportunity.custom_field_values
                        existing_opportunity.contacts = full_opportunity.contacts

                        # After adding existing opportunity
                        db_session.add(existing_opportunity)
                    else:
                        # Add new opportunity with relationships
                        db_session.add(full_opportunity)

                        # Commit after each opportunity
                        db_session.commit()
                        success_count += 1

                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'offset': current_offset})
                    db_session.rollback()
                    continue

            # Update offset based on next URL if available
            if pagination.get('next'):
                next_offset = client._parse_next_url(pagination['next'])
                if next_offset is not None:
                    checkpoint_manager.save_checkpoint(entity_type, next_offset)
                else:
                    # If we can't parse the next URL, increment by batch size
                    checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items))
            else:
                # No more pages
                checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items), completed=True)
                break

        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'offset': current_offset})
            db_session.rollback()
            # Don't raise the exception, continue with next batch
            continue

    return total_records, success_count, failed_count


@audit_load_operation
def load_products(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load products from Keap API into database."""
    entity_type = 'products'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    try:
        # Get initial offset from checkpoint
        offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Starting product load from offset {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_products(limit=batch_size, offset=offset, db_session=db_session)
            logger.debug(f"Retrieved {len(items)} products from API")

            if not items:
                logger.info("No more products to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing product ID: {item.id}, Name: {item.product_name}")

                    # First, check if product exists
                    existing_product = db_session.query(Product).filter(Product.id == item.id).first()

                    if existing_product:
                        # Update existing product's attributes
                        for key, value in item.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_product, key, value)
                        db_session.add(existing_product)
                    else:
                        # Add new product
                        db_session.add(item)

                    db_session.commit()
                    success_count += 1
                    logger.debug(f"Successfully processed product ID: {item.id}")

                except Exception as e:
                    db_session.rollback()
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e)
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


@audit_load_operation
def load_orders(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load orders from Keap API into database."""
    entity_type = 'orders'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    try:
        # Get initial offset from checkpoint
        offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Starting order load from offset {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_orders(limit=batch_size, offset=offset, db_session=db_session)
            logger.debug(f"Retrieved {len(items)} orders from API")

            if not items:
                logger.info("No more orders to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing order ID: {item.id}, Title: {item.title}")

                    # First, check if order exists
                    existing_order = db_session.query(Order).filter(Order.id == item.id).first()

                    if existing_order:
                        # Update existing order's attributes
                        for key, value in item.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_order, key, value)
                        db_session.add(existing_order)
                    else:
                        # Add new order
                        db_session.add(item)

                    db_session.commit()
                    success_count += 1
                    logger.debug(f"Successfully processed order ID: {item.id}")

                except Exception as e:
                    db_session.rollback()
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e)
                    logger.error(f"Error processing order ID {item.id}: {e}")
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of orders")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading orders. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_orders: {str(e)}")
        raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_tasks(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load tasks from Keap API into database."""
    entity_type = 'tasks'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    try:
        # Get initial offset from checkpoint
        offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Starting task load from offset {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_tasks(limit=batch_size, offset=offset, db_session=db_session)
            logger.debug(f"Retrieved {len(items)} tasks from API")

            if not items:
                logger.info("No more tasks to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing task ID: {item.id}, Title: {item.title}")

                    # First, check if task exists
                    existing_task = db_session.query(Task).filter(Task.id == item.id).first()

                    if existing_task:
                        # Update existing task's attributes
                        for key, value in item.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_task, key, value)
                        db_session.add(existing_task)
                    else:
                        # Add new task
                        db_session.add(item)

                    db_session.commit()
                    success_count += 1
                    logger.debug(f"Successfully processed task ID: {item.id}")

                except Exception as e:
                    db_session.rollback()
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e)
                    logger.error(f"Error processing task ID {item.id}: {e}")
                    continue

            # Update checkpoint with new offset
            new_offset = offset + len(items)
            checkpoint_manager.save_checkpoint(entity_type, new_offset)

            # Check if we've reached the end
            if not pagination.get('next'):
                logger.info("Reached end of tasks")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            # Parse next URL to get the offset for the next batch
            next_offset = client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                checkpoint_manager.save_checkpoint(entity_type, new_offset, completed=True)
                break

            offset = next_offset

        logger.info(f"Completed loading tasks. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Error in load_tasks: {str(e)}")
        raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_notes(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load notes from Keap API into database."""
    entity_type = 'notes'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        try:
            # Make API call with limit and offset
            items, pagination = client.get_notes(limit=batch_size, offset=current_offset)

            if not items:
                # Mark as completed when no more items
                checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing note ID: {item.id}, Title: {item.title}")

                    # Get full note details including custom fields
                    full_note = client.get_note(item.id)
                    logger.info(f"Retrieved full note details for ID: {item.id}")

                    # First, check if note exists
                    existing_note = db_session.query(Note).filter(Note.id == item.id).first()

                    if existing_note:
                        # Update existing note's attributes
                        for key, value in full_note.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_note, key, value)

                        # Clear existing relationships
                        existing_note.contacts = []
                        existing_note.custom_field_values = []

                        # Add new relationships using SQLAlchemy's native relationship handling
                        existing_note.contacts = full_note.contacts
                        existing_note.custom_field_values = full_note.custom_field_values

                        # After adding existing note
                        db_session.add(existing_note)
                    else:
                        # Add new note with relationships
                        db_session.add(full_note)

                        # Commit after each note
                        db_session.commit()
                        success_count += 1

                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'offset': current_offset})
                    db_session.rollback()
                    continue

            # Update offset based on next URL if available
            if pagination.get('next'):
                next_offset = client._parse_next_url(pagination['next'])
                if next_offset is not None:
                    checkpoint_manager.save_checkpoint(entity_type, next_offset)
                else:
                    # If we can't parse the next URL, increment by batch size
                    checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items))
            else:
                # No more pages
                checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items), completed=True)
                break

        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'offset': current_offset})
            db_session.rollback()
            # Don't raise the exception, continue with next batch
            continue

    return total_records, success_count, failed_count


@audit_load_operation
def load_campaigns(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load campaigns from Keap API into database."""
    entity_type = 'campaigns'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    try:
        # Get initial offset from checkpoint
        offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Starting campaign load from offset {offset}")

        while True:
            # Make API call with limit and offset
            items, pagination = client.get_campaigns(limit=batch_size, offset=offset, db_session=db_session)
            logger.debug(f"Retrieved {len(items)} campaigns from API")

            if not items:
                logger.info("No more campaigns to load")
                checkpoint_manager.save_checkpoint(entity_type, offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing campaign ID: {item.id}, Name: {item.name}")

                    # First, check if campaign exists
                    existing_campaign = db_session.query(Campaign).filter(Campaign.id == item.id).first()

                    if existing_campaign:
                        # Update existing campaign's attributes
                        for key, value in item.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_campaign, key, value)
                        db_session.add(existing_campaign)
                    else:
                        # Add new campaign
                        db_session.add(item)

                    db_session.commit()
                    success_count += 1
                    logger.debug(f"Successfully processed campaign ID: {item.id}")

                except Exception as e:
                    db_session.rollback()
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e)
                    logger.error(f"Error processing campaign ID {item.id}: {e}")
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


@audit_load_operation
def load_subscriptions(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load subscriptions from Keap API into database."""
    entity_type = 'subscriptions'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        try:
            # Make API call with limit and offset
            items, pagination = client.get_subscriptions(limit=batch_size, offset=current_offset)

            if not items:
                # Mark as completed when no more items
                checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
                break

            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing subscription ID: {item.id}")

                    # Get full subscription details
                    full_subscription = client.get_subscription(item.id)
                    logger.info(f"Retrieved full subscription details for ID: {item.id}")

                    # First, check if subscription exists
                    existing_subscription = db_session.query(Subscription).filter(Subscription.id == item.id).first()

                    if existing_subscription:
                        # Update existing subscription's attributes
                        for key, value in full_subscription.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_subscription, key, value)

                        # Clear existing relationships
                        existing_subscription.contacts = []
                        existing_subscription.products = []
                        existing_subscription.custom_field_values = []

                        # Add new relationships using SQLAlchemy's native relationship handling
                        existing_subscription.contacts = full_subscription.contacts
                        existing_subscription.products = full_subscription.products
                        existing_subscription.custom_field_values = full_subscription.custom_field_values

                        # After adding existing subscription
                        db_session.add(existing_subscription)
                    else:
                        # Add new subscription with relationships
                        db_session.add(full_subscription)

                        # Commit after each subscription
                        db_session.commit()
                        success_count += 1

                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'offset': current_offset})
                    db_session.rollback()
                    continue

            # Update offset based on next URL if available
            if pagination.get('next'):
                next_offset = client._parse_next_url(pagination['next'])
                if next_offset is not None:
                    checkpoint_manager.save_checkpoint(entity_type, next_offset)
                else:
                    # If we can't parse the next URL, increment by batch size
                    checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items))
            else:
                # No more pages
                checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items), completed=True)
                break

        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'offset': current_offset})
            db_session.rollback()
            # Don't raise the exception, continue with next batch
            continue

    return total_records, success_count, failed_count


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

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_affiliates(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing affiliate ID: {item.id}")

                    # Get full affiliate details
                    full_affiliate = client.get_affiliate(item.id)
                    logger.info(f"Retrieved full affiliate details for ID: {item.id}")

                    # Get affiliate commissions
                    commissions = client.get_affiliate_commissions(item.id)
                    logger.info(f"Retrieved {len(commissions)} commissions for affiliate ID: {item.id}")

                    # Get affiliate payments
                    payments = client.get_affiliate_payments(item.id)
                    logger.info(f"Retrieved {len(payments)} payments for affiliate ID: {item.id}")

                    # Get affiliate clawbacks
                    clawbacks = client.get_affiliate_clawbacks(item.id)
                    logger.info(f"Retrieved {len(clawbacks)} clawbacks for affiliate ID: {item.id}")

                    # First, check if affiliate exists
                    existing_affiliate = db.query(Affiliate).filter(Affiliate.id == item.id).first()

                    if existing_affiliate:
                        # Update existing affiliate's attributes
                        for key, value in full_affiliate.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_affiliate, key, value)

                        # Clear existing relationships
                        existing_affiliate.commissions = []
                        existing_affiliate.payments = []
                        existing_affiliate.clawbacks = []

                        # Add new relationships
                        existing_affiliate.commissions = commissions
                        existing_affiliate.payments = payments
                        existing_affiliate.clawbacks = clawbacks

                        # After adding existing affiliate
                        db.add(existing_affiliate)
                        db.flush()  # Ensure affiliate is persisted
                        db.commit()
                        success_count += 1

                    else:
                        # Add new affiliate with relationships
                        full_affiliate.commissions = commissions
                        full_affiliate.payments = payments
                        full_affiliate.clawbacks = clawbacks

                        db.add(full_affiliate)
                        db.flush()  # Ensure affiliate is persisted
                        db.commit()
                        success_count += 1

                except Exception as e:
                    failed_count += 1
                    log_error(error_logger, entity_type, item.id, e, {'offset': current_offset})
                    db.rollback()
                    continue

            # Update offset based on next URL if available
            if pagination.get('next'):
                next_offset = client._parse_next_url(pagination['next'])
                if next_offset is not None:
                    checkpoint_manager.save_checkpoint(entity_type, next_offset)
                else:
                    # If we can't parse the next URL, increment by batch size
                    checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items))
            else:
                # No more pages
                checkpoint_manager.save_checkpoint(entity_type, current_offset + len(items), completed=True)
                break

        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'offset': current_offset})
            db.rollback()
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_commissions(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load all affiliate commissions."""
    entity_type = 'affiliate_commissions'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing commissions for affiliate ID: {affiliate_id}")
        current_offset = 0  # Reset offset for each affiliate

        while True:
            try:
                # Get query parameters including since timestamp if applicable
                query_params = checkpoint_manager.get_query_params(entity_type, update)
                query_params.update({'limit': batch_size, 'offset': current_offset})

                commissions, pagination = client.get_affiliate_commissions(affiliate_id, **query_params)
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
    """Load all affiliate programs."""
    entity_type = 'affiliate_programs'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing programs for affiliate ID: {affiliate_id}")
        current_offset = 0  # Reset offset for each affiliate

        while True:
            try:
                # Get query parameters including since timestamp if applicable
                query_params = checkpoint_manager.get_query_params(entity_type, update)
                query_params.update({'limit': batch_size, 'offset': current_offset})

                programs, pagination = client.get_affiliate_programs(affiliate_id, **query_params)
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
    logger.info(f"Loaded {total_records} programs in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_redirects(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load all affiliate redirects."""
    entity_type = 'affiliate_redirects'
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing redirects for affiliate ID: {affiliate_id}")
        try:
            # Get query parameters including since timestamp if applicable
            query_params = checkpoint_manager.get_query_params(entity_type, update)
            query_params.update({'limit': batch_size, 'offset': 0  # Reset offset for each affiliate
                                 })

            redirects = client.get_affiliate_redirects(affiliate_id, **query_params)
            logger.info(f"Received {len(redirects) if redirects else 0} redirects for affiliate {affiliate_id}")

            if not redirects:
                continue

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

            if failed_count > 0:
                logger.warning(f"Failed to process {failed_count} redirects")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    # Mark as completed since we process all affiliates
    checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
    logger.info(f"Loaded {total_records} redirects in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_summaries(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager) -> tuple:
    """Load all affiliate summaries."""
    entity_type = 'affiliate_summaries'
    total_records = 0
    success_count = 0
    failed_count = 0
    error_logger = ErrorLogger()

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing summary for affiliate ID: {affiliate_id}")
        try:
            summary = client.get_affiliate_summary(affiliate_id)
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
                log_error(error_logger, entity_type, summary.id if summary else affiliate_id, e, 
                         {'summary_data': summary.__dict__ if summary else None})
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
    """Load all affiliate clawbacks."""
    entity_type = 'affiliate_clawbacks'
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing clawbacks for affiliate ID: {affiliate_id}")
        try:
            # Get query parameters including since timestamp if applicable
            query_params = checkpoint_manager.get_query_params(entity_type, update)
            query_params.update({'limit': batch_size, 'offset': 0  # Reset offset for each affiliate
                                 })

            clawbacks = client.get_affiliate_clawbacks(affiliate_id, **query_params)
            logger.info(f"Received {len(clawbacks) if clawbacks else 0} clawbacks for affiliate {affiliate_id}")

            if not clawbacks:
                continue

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

            if failed_count > 0:
                logger.warning(f"Failed to process {failed_count} clawbacks")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    # Mark as completed since we process all affiliates
    checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
    logger.info(f"Loaded {total_records} clawbacks in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_payments(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, update: bool = False) -> tuple:
    """Load all affiliate payments."""
    entity_type = 'affiliate_payments'
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing payments for affiliate ID: {affiliate_id}")
        try:
            # Get query parameters including since timestamp if applicable
            query_params = checkpoint_manager.get_query_params(entity_type, update)
            query_params.update({'limit': batch_size, 'offset': 0  # Reset offset for each affiliate
                                 })

            payments = client.get_affiliate_payments(affiliate_id, **query_params)
            logger.info(f"Received {len(payments) if payments else 0} payments for affiliate {affiliate_id}")

            if not payments:
                continue

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

            if failed_count > 0:
                logger.warning(f"Failed to process {failed_count} payments")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    # Mark as completed since we process all affiliates
    checkpoint_manager.save_checkpoint(entity_type, total_records, completed=True)
    logger.info(f"Loaded {total_records} payments in total")
    return total_records, success_count, failed_count


def main(update: bool = False):
    """Main function to perform the data load.
    
    Args:
        update: Whether to perform an update operation using last_loaded timestamps
    """
    start_time = datetime.now(timezone.utc)
    total_records = 0
    success_count = 0
    failed_count = 0

    client = KeapClient()
    db = SessionLocal()
    checkpoint_manager = CheckpointManager()

    # Initialize database tables
    from src.database.init_db import init_db
    init_db()

    if not update:
        checkpoint_manager.clear_checkpoints()
        logger.info("Starting fresh data load...")
    else:
        logger.info("Performing update operation...")

    try:
        # Load data in a specific order to maintain referential integrity
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

        # Load products before orders and subscriptions
        products_total, products_success, products_failed = load_products(client, db, checkpoint_manager, update=update)
        total_records += products_total
        success_count += products_success
        failed_count += products_failed

        # Then load contacts and their related data
        contacts_total, contacts_success, contacts_failed = load_contacts(client, db, checkpoint_manager, update=update)
        total_records += contacts_total
        success_count += contacts_success
        failed_count += contacts_failed

        # Load remaining data
        opportunities_total, opportunities_success, opportunities_failed = load_opportunities(client, db, checkpoint_manager, update=update)
        total_records += opportunities_total
        success_count += opportunities_success
        failed_count += opportunities_failed

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

        # Load affiliate data after contacts are loaded
        affiliates_total, affiliates_success, affiliates_failed = load_affiliates(client, db, checkpoint_manager, update=update)
        total_records += affiliates_total
        success_count += affiliates_success
        failed_count += affiliates_failed

        commissions_total, commissions_success, commissions_failed = load_affiliate_commissions(client, db, checkpoint_manager, update=update)
        total_records += commissions_total
        success_count += commissions_success
        failed_count += commissions_failed

        programs_total, programs_success, programs_failed = load_affiliate_programs(client, db, checkpoint_manager, update=update)
        total_records += programs_total
        success_count += programs_success
        failed_count += programs_failed

        redirects_total, redirects_success, redirects_failed = load_affiliate_redirects(client, db, checkpoint_manager, update=update)
        total_records += redirects_total
        success_count += redirects_success
        failed_count += redirects_failed

        summaries_total, summaries_success, summaries_failed = load_affiliate_summaries(client, db, checkpoint_manager)
        total_records += summaries_total
        success_count += summaries_success
        failed_count += summaries_failed

        clawbacks_total, clawbacks_success, clawbacks_failed = load_affiliate_clawbacks(client, db, checkpoint_manager, update=update)
        total_records += clawbacks_total
        success_count += clawbacks_success
        failed_count += clawbacks_failed

        payments_total, payments_success, payments_failed = load_affiliate_payments(client, db, checkpoint_manager, update=update)
        total_records += payments_total
        success_count += payments_success
        failed_count += payments_failed

        logger.info("Data load completed successfully!")

    except Exception as e:
        logger.error(f"Error during data load: {str(e)}")
        db.rollback()
        raise
    finally:
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Format as HH:MM:SS

        # Log final audit summary
        logger.info(f"Final Audit Summary:")
        logger.info(f"Total Records: {total_records}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Duration: {duration_str}")

        # Save final audit log
        checkpoint_manager.audit_logger.log_audit(entity_type='complete_load', start_time=start_time, end_time=end_time, total_records=total_records, success=success_count, failed=failed_count)

        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load data from Keap API')
    parser.add_argument('--update', action='store_true', help='Resume from existing checkpoints')
    args = parser.parse_args()

    main(update=args.update)
