import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import time
import argparse

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.models.models import (
    Contact, contact_tag, Affiliate
)
from src.utils.error_logger import ErrorLogger
from src.utils.logging_config import setup_logging

# Create logs and checkpoints directories if they don't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('checkpoints', exist_ok=True)

# Setup logging
setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    app_name="keap_data_extract"
)

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

    def log_audit(self, entity_type: str, start_time: datetime, end_time: datetime,
                  total_records: int, success: int, failed: int) -> None:
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

        audit_entry = {
            'entity_type': entity_type,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'total_records': total_records,
            'success': success,
            'failed': failed,
            'duration': duration_str
        }

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
                audit_logger.log_audit(
                    entity_type=entity_type,
                    start_time=start_time,
                    end_time=end_time,
                    total_records=total_records,
                    success=success_count,
                    failed=failed_count
                )

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
            self.checkpoints[entity_type] = {
                'offset': 0,
                'last_loaded': None
            }

        self.checkpoints[entity_type]['offset'] = offset
        if completed:
            self.checkpoints[entity_type]['last_loaded'] = datetime.now(timezone.utc).isoformat()

        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoints, f)
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


def log_error(error_logger: ErrorLogger, entity_type: str, entity_id: int, error: Exception,
              additional_data: Dict = None) -> None:
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

    error_logger.log_error(
        entity_type=entity_type,
        entity_id=entity_id,
        error_type=error_type,
        error_message=error_message,
        additional_data=additional_data
    )


def insert_contact_tags(db, contact_id, tags):
    """Helper function to insert tags into the contact_tag table."""
    for tag in tags:
        db.execute(
            contact_tag.insert().values(
                contact_id=contact_id,
                tag_id=tag.id,
                created_at=datetime.now(timezone.utc)
            )
        )


@audit_load_operation
def load_contacts(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                  update: bool = False) -> tuple:
    """Load all contacts and their related data."""
    entity_type = 'contacts'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_contacts(limit=batch_size, offset=current_offset, db_session=db)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(
                        f"Processing contact ID: {item.id}, Name: {item.given_name} {item.family_name} - {item.tags}")
                    # Handle company_name if it's a dictionary
                    if isinstance(item.company_name, dict):
                        item.company_name = item.company_name.get('company_name')

                    # First, check if contact exists
                    existing_contact = db.query(Contact).filter(Contact.id == item.id).first()

                    if existing_contact:
                        # Update existing contact's attributes
                        for key, value in item.__dict__.items():
                            if not key.startswith('_'):
                                setattr(existing_contact, key, value)

                        # Clear existing relationships
                        existing_contact.email_addresses = []
                        existing_contact.phone_numbers = []
                        existing_contact.addresses = []
                        existing_contact.tags = []
                        existing_contact.custom_field_values = []

                        # Add new relationships
                        existing_contact.email_addresses = item.email_addresses
                        existing_contact.phone_numbers = item.phone_numbers
                        existing_contact.addresses = item.addresses
                        existing_contact.tags = item.tags
                        existing_contact.custom_field_values = item.custom_field_values

                        # After adding existing contact
                        db.add(existing_contact)
                        db.flush()  # Ensure contact is persisted

                        # Insert tags into contact_tag
                        api_tags = client.get_contact_tags(item.id)
                        insert_contact_tags(db, item.id, api_tags)

                        # Commit after inserting tags
                        db.commit()
                        success_count += 1

                    else:
                        # Add new contact with relationships
                        db.add(item)
                        db.flush()  # Ensure contact is persisted

                        # Insert tags into contact_tag for new contacts
                        api_tags = client.get_contact_tags(item.id)
                        insert_contact_tags(db, item.id, api_tags)

                        # Commit after inserting tags
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
def load_tags(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
              update: bool = False) -> tuple:
    """Load tags from Keap API into database."""
    entity_type = 'tags'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_tags(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing tag ID: {item.id}, Name: {item.name}")
                    # Use merge operation to handle both inserts and updates
                    merged_tag = db_session.merge(item)
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
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_custom_fields(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                       update: bool = False) -> tuple:
    """Load all custom fields."""
    entity_type = 'custom_fields'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    while True:
        logger.info(f"Loading {entity_type} - Current offset: {offset}")
        logger.info(f"Fetching custom fields with params: {query_params}")
        custom_fields = client.get_custom_fields(**query_params)
        logger.info(f"Received {len(custom_fields) if custom_fields else 0} custom fields from API")

        if not custom_fields:
            break

        for field in custom_fields:
            total_records += 1
            logger.info(f"Processing custom field ID: {field.id}, Name: {field.name}, Type: {field.type}")
            try:
                merged_field = db.merge(field)
                success_count += 1
                db.commit()
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing custom field {field.id}: {str(e)}")
                db.rollback()
                continue

        # Update offset by the total number of custom fields received
        offset += len(custom_fields)
        checkpoint_manager.save_checkpoint(entity_type, offset)
        logger.debug(f"Successfully processed batch of {success_count} custom fields")

        if failed_count > 0:
            logger.warning(f"Failed to process {failed_count} custom fields")

        logger.info(f"Loaded {total_records} custom fields so far")

    return total_records, success_count, failed_count


@audit_load_operation
def load_opportunities(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager,
                       batch_size: int = 50, update: bool = False) -> tuple:
    """Load opportunities from Keap API into database."""
    entity_type = 'opportunities'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_opportunities(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing opportunity ID: {item.id}, Title: {item.title}")
                    # Use merge operation to handle both inserts and updates
                    merged_opportunity = db_session.merge(item)
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
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_products(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                  update: bool = False) -> tuple:
    """Load products from Keap API into database."""
    entity_type = 'products'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_products(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing product ID: {item.id}, Name: {item.product_name}")
                    # Use merge operation to handle both inserts and updates
                    merged_product = db_session.merge(item)
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
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_orders(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                update: bool = False) -> tuple:
    """Load orders from Keap API into database."""
    entity_type = 'orders'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_orders(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing order ID: {item.id}, Order Number: {item.order_number}")
                    # Use merge operation to handle both inserts and updates
                    merged_order = db_session.merge(item)
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
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_tasks(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
               update: bool = False) -> tuple:
    """Load tasks from Keap API into database."""
    entity_type = 'tasks'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_tasks(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing task ID: {item.id}, Title: {item.title}")
                    # Use merge operation to handle both inserts and updates
                    merged_task = db_session.merge(item)
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
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_notes(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
               update: bool = False) -> tuple:
    """Load notes from Keap API into database."""
    entity_type = 'notes'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_notes(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing note ID: {item.id}, Contact ID: {item.contact_id}")
                    # Use merge operation to handle both inserts and updates
                    merged_note = db_session.merge(item)
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
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_campaigns(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                   update: bool = False) -> tuple:
    """Load campaigns from Keap API into database."""
    entity_type = 'campaigns'
    total_records = 0
    success_count = 0
    failed_count = 0

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)
        logger.info(f"Loading {entity_type} - Current offset: {current_offset}")

        # Make API call with limit and offset
        items, pagination = client.get_campaigns(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                total_records += 1
                try:
                    logger.info(f"Processing campaign ID: {item.id}, Name: {item.name}")
                    # Use merge operation to handle both inserts and updates
                    merged_campaign = db_session.merge(item)
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
            raise

    return total_records, success_count, failed_count


@audit_load_operation
def load_subscriptions(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                       update: bool = False) -> tuple:
    """Load all active subscriptions."""
    entity_type = 'subscriptions'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    while True:
        logger.info(f"Loading {entity_type} - Current offset: {offset}")
        logger.info(f"Fetching subscriptions with params: {query_params}")
        try:
            subscriptions = client.get_subscriptions(**query_params)
            logger.info(f"Received {len(subscriptions) if subscriptions else 0} subscriptions from API")
        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'query_params': query_params})
            break

        if not subscriptions:
            break

        for subscription in subscriptions:
            total_records += 1
            logger.info(
                f"Processing subscription ID: {subscription.id}, Contact ID: {subscription.contact_id}, Product ID: {subscription.product_id}")
            try:
                # Validate subscription data
                if not subscription.contact_id:
                    raise ValueError("Contact ID is required for subscription")
                if not subscription.product_id:
                    raise ValueError("Product ID is required for subscription")
                if not subscription.status:
                    raise ValueError("Status is required for subscription")

                # Use merge operation to handle both inserts and updates
                merged_subscription = db.merge(subscription)
                success_count += 1
                db.commit()
            except Exception as e:
                failed_count += 1
                log_error(error_logger, entity_type, subscription.id, e, {'subscription_data': subscription.__dict__})
                db.rollback()
                continue

        # Update offset by the total number of subscriptions received
        offset += len(subscriptions)
        checkpoint_manager.save_checkpoint(entity_type, offset)
        logger.debug(f"Successfully processed batch of {success_count} subscriptions")

        if failed_count > 0:
            logger.warning(f"Failed to process {failed_count} subscriptions")

        logger.info(f"Loaded {total_records} subscriptions so far")

    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliates(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                    update: bool = False) -> tuple:
    """Load all affiliates."""
    entity_type = 'affiliates'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    while True:
        logger.info(f"Loading {entity_type} - Current offset: {offset}")
        logger.info(f"Fetching affiliates with params: {query_params}")
        try:
            affiliates = client.get_affiliates(**query_params)
            logger.info(f"Received {len(affiliates) if affiliates else 0} affiliates from API")
        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'query_params': query_params})
            break

        if not affiliates:
            break

        for affiliate in affiliates:
            total_records += 1
            logger.info(f"Processing affiliate ID: {affiliate.id}, Name: {affiliate.name}")
            try:
                # Validate affiliate data
                if not affiliate.code:
                    raise ValueError("Code is required for affiliate")

                # Use merge operation to handle both inserts and updates
                merged_affiliate = db.merge(affiliate)
                success_count += 1
                db.commit()
            except Exception as e:
                failed_count += 1
                log_error(error_logger, entity_type, affiliate.id, e, {'affiliate_data': affiliate.__dict__})
                db.rollback()
                continue

        # Update offset by the total number of affiliates received
        offset += len(affiliates)
        checkpoint_manager.save_checkpoint(entity_type, offset)
        logger.debug(f"Successfully processed batch of {success_count} affiliates")

        if failed_count > 0:
            logger.warning(f"Failed to process {failed_count} affiliates")

        logger.info(f"Loaded {total_records} affiliates so far")

    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_commissions(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                               batch_size: int = 50,
                               update: bool = False) -> tuple:
    """Load all affiliate commissions."""
    entity_type = 'affiliate_commissions'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing commissions for affiliate ID: {affiliate_id}")
        try:
            commissions = client.get_affiliate_commissions(affiliate_id, **query_params)
            logger.info(f"Received {len(commissions) if commissions else 0} commissions for affiliate {affiliate_id}")

            if not commissions:
                continue

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

            if failed_count > 0:
                logger.warning(f"Failed to process {failed_count} commissions")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_records} commissions in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_programs(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                            batch_size: int = 50,
                            update: bool = False) -> tuple:
    """Load all affiliate programs."""
    entity_type = 'affiliate_programs'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing programs for affiliate ID: {affiliate_id}")
        try:
            programs = client.get_affiliate_programs(affiliate_id, **query_params)
            logger.info(f"Received {len(programs) if programs else 0} programs for affiliate {affiliate_id}")

            if not programs:
                continue

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

            if failed_count > 0:
                logger.warning(f"Failed to process {failed_count} programs")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_records} programs in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_redirects(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                             batch_size: int = 50,
                             update: bool = False) -> tuple:
    """Load all affiliate redirects."""
    entity_type = 'affiliate_redirects'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing redirects for affiliate ID: {affiliate_id}")
        try:
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

    logger.info(f"Loaded {total_records} redirects in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_summaries(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager) -> tuple:
    """Load all affiliate summaries."""
    entity_type = 'affiliate_summaries'
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing summary for affiliate ID: {affiliate_id}")
        try:
            summary = client.get_affiliate_summary(affiliate_id)
            logger.info(f"Received summary for affiliate {affiliate_id}")

            total_records += 1
            try:
                # Validate summary data
                if not summary.affiliate_id:
                    raise ValueError("Affiliate ID is required for summary")

                # Use merge operation to handle both inserts and updates
                merged_summary = db.merge(summary)
                success_count += 1
                db.commit()
            except Exception as e:
                failed_count += 1
                log_error(error_logger, entity_type, summary.id, e, {'summary_data': summary.__dict__})
                db.rollback()
                continue

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_records} summaries in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_clawbacks(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                             batch_size: int = 50,
                             update: bool = False) -> tuple:
    """Load all affiliate clawbacks."""
    entity_type = 'affiliate_clawbacks'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing clawbacks for affiliate ID: {affiliate_id}")
        try:
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

    logger.info(f"Loaded {total_records} clawbacks in total")
    return total_records, success_count, failed_count


@audit_load_operation
def load_affiliate_payments(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                            batch_size: int = 50,
                            update: bool = False) -> tuple:
    """Load all affiliate payments."""
    entity_type = 'affiliate_payments'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_records = 0
    success_count = 0
    failed_count = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing payments for affiliate ID: {affiliate_id}")
        try:
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
        # First load tags since they are referenced by contacts
        tags_total, tags_success, tags_failed = load_tags(client, db, checkpoint_manager, update=update)
        total_records += tags_total
        success_count += tags_success
        failed_count += tags_failed

        # Then load contacts and their related data
        contacts_total, contacts_success, contacts_failed = load_contacts(client, db, checkpoint_manager, update=update)
        total_records += contacts_total
        success_count += contacts_success
        failed_count += contacts_failed

        # Load remaining data
        products_total, products_success, products_failed = load_products(client, db, checkpoint_manager, update=update)
        total_records += products_total
        success_count += products_success
        failed_count += products_failed

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
        checkpoint_manager.audit_logger.log_audit(
            entity_type='complete_load',
            start_time=start_time,
            end_time=end_time,
            total_records=total_records,
            success=success_count,
            failed=failed_count
        )

        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load data from Keap API')
    parser.add_argument('--update', action='store_true', help='Resume from existing checkpoints')
    args = parser.parse_args()
    
    main(update=args.update)
