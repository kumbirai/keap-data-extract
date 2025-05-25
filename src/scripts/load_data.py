import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Any

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


class CheckpointManager:
    def __init__(self, checkpoint_file: str = 'checkpoints/load_progress.json'):
        self.checkpoint_file = checkpoint_file
        self.checkpoints = self._load_checkpoints()

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


def load_contacts(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                  update: bool = False) -> None:
    """Load all contacts and their related data."""
    entity_type = 'contacts'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_contacts(limit=batch_size, offset=current_offset, db_session=db)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
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

                    else:
                        # Add new contact with relationships
                        db.add(item)
                        db.flush()  # Ensure contact is persisted

                        # Insert tags into contact_tag for new contacts
                        api_tags = client.get_contact_tags(item.id)
                        insert_contact_tags(db, item.id, api_tags)

                    # Commit after inserting tags
                    db.commit()

                except Exception as e:
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


def load_tags(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
              update: bool = False) -> None:
    """Load tags from Keap API into database."""
    entity_type = 'tags'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_tags(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                try:
                    logger.info(f"Processing tag ID: {item.id}, Name: {item.name}")
                    # Use merge operation to handle both inserts and updates
                    merged_tag = db_session.merge(item)
                    db_session.commit()
                except Exception as e:
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


def load_custom_fields(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                       update: bool = False) -> None:
    """Load all custom fields."""
    entity_type = 'custom_fields'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_fields = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    while True:
        logger.info(f"Fetching custom fields with params: {query_params}")
        custom_fields = client.get_custom_fields(**query_params)
        logger.info(f"Received {len(custom_fields) if custom_fields else 0} custom fields from API")

        if not custom_fields:
            break

        processed_in_batch = 0
        failed_fields = []

        for field in custom_fields:
            logger.info(f"Processing custom field ID: {field.id}, Name: {field.name}, Type: {field.type}")
            try:
                merged_field = db.merge(field)
                total_fields += 1
                processed_in_batch += 1
                db.commit()
            except Exception as e:
                logger.error(f"Error processing custom field {field.id}: {str(e)}")
                failed_fields.append(field.id)
                db.rollback()
                continue

        # Update offset by the total number of custom fields received
        offset += len(custom_fields)
        checkpoint_manager.save_checkpoint(entity_type, offset)
        logger.debug(f"Successfully processed batch of {processed_in_batch} custom fields")

        if failed_fields:
            logger.warning(f"Failed to process custom fields: {failed_fields}")

        logger.info(f"Loaded {total_fields} custom fields so far")


def load_opportunities(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager,
                       batch_size: int = 50, update: bool = False) -> None:
    """Load opportunities from Keap API into database."""
    entity_type = 'opportunities'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_opportunities(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                try:
                    logger.info(f"Processing opportunity ID: {item.id}, Title: {item.title}")
                    # Use merge operation to handle both inserts and updates
                    merged_opportunity = db_session.merge(item)
                    db_session.commit()
                except Exception as e:
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


def load_products(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                  update: bool = False) -> None:
    """Load products from Keap API into database."""
    entity_type = 'products'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_products(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                try:
                    logger.info(f"Processing product ID: {item.id}, Name: {item.product_name}")
                    # Use merge operation to handle both inserts and updates
                    merged_product = db_session.merge(item)
                    db_session.commit()
                except Exception as e:
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


def load_orders(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                update: bool = False) -> None:
    """Load orders from Keap API into database."""
    entity_type = 'orders'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_orders(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                try:
                    logger.info(f"Processing order ID: {item.id}, Order Number: {item.order_number}")
                    # Use merge operation to handle both inserts and updates
                    merged_order = db_session.merge(item)
                    db_session.commit()
                except Exception as e:
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


def load_tasks(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
               update: bool = False) -> None:
    """Load tasks from Keap API into database."""
    entity_type = 'tasks'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_tasks(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                try:
                    logger.info(f"Processing task ID: {item.id}, Title: {item.title}")
                    # Use merge operation to handle both inserts and updates
                    merged_task = db_session.merge(item)
                    db_session.commit()
                except Exception as e:
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


def load_notes(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
               update: bool = False) -> None:
    """Load notes from Keap API into database."""
    entity_type = 'notes'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_notes(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                try:
                    logger.info(f"Processing note ID: {item.id}, Contact ID: {item.contact_id}")
                    # Use merge operation to handle both inserts and updates
                    merged_note = db_session.merge(item)
                    db_session.commit()
                except Exception as e:
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


def load_campaigns(client: KeapClient, db_session: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                   update: bool = False) -> None:
    """Load campaigns from Keap API into database."""
    entity_type = 'campaigns'

    while True:
        # Get current offset from checkpoint
        current_offset = checkpoint_manager.get_checkpoint(entity_type)

        # Make API call with limit and offset
        items, pagination = client.get_campaigns(limit=batch_size, offset=current_offset)

        if not items:
            # Mark as completed when no more items
            checkpoint_manager.save_checkpoint(entity_type, current_offset, completed=True)
            break

        try:
            # Process items
            for item in items:
                try:
                    logger.info(f"Processing campaign ID: {item.id}, Name: {item.name}")
                    # Use merge operation to handle both inserts and updates
                    merged_campaign = db_session.merge(item)
                    db_session.commit()
                except Exception as e:
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


def load_subscriptions(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                       update: bool = False) -> None:
    """Load all active subscriptions."""
    entity_type = 'subscriptions'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_subscriptions = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    while True:
        logger.info(f"Fetching subscriptions with params: {query_params}")
        try:
            subscriptions = client.get_subscriptions(**query_params)
            logger.info(f"Received {len(subscriptions) if subscriptions else 0} subscriptions from API")
        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'query_params': query_params})
            break

        if not subscriptions:
            break

        processed_in_batch = 0
        failed_subscriptions = []

        for subscription in subscriptions:
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
                total_subscriptions += 1
                processed_in_batch += 1
                db.commit()
            except Exception as e:
                log_error(error_logger, entity_type, subscription.id, e, {'subscription_data': subscription.__dict__})
                failed_subscriptions.append(subscription.id)
                db.rollback()
                continue

        # Update offset by the total number of subscriptions received
        offset += len(subscriptions)
        checkpoint_manager.save_checkpoint(entity_type, offset)
        logger.debug(f"Successfully processed batch of {processed_in_batch} subscriptions")

        if failed_subscriptions:
            logger.warning(f"Failed to process subscriptions: {failed_subscriptions}")

        logger.info(f"Loaded {total_subscriptions} subscriptions so far")


def load_affiliates(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50,
                    update: bool = False) -> None:
    """Load all affiliates."""
    entity_type = 'affiliates'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_affiliates = 0

    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params(entity_type, update)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })

    while True:
        logger.info(f"Fetching affiliates with params: {query_params}")
        try:
            affiliates = client.get_affiliates(**query_params)
            logger.info(f"Received {len(affiliates) if affiliates else 0} affiliates from API")
        except Exception as e:
            log_error(error_logger, entity_type, 0, e, {'query_params': query_params})
            break

        if not affiliates:
            break

        processed_in_batch = 0
        failed_affiliates = []

        for affiliate in affiliates:
            logger.info(f"Processing affiliate ID: {affiliate.id}, Name: {affiliate.name}")
            try:
                # Validate affiliate data
                if not affiliate.code:
                    raise ValueError("Code is required for affiliate")

                # Use merge operation to handle both inserts and updates
                merged_affiliate = db.merge(affiliate)
                total_affiliates += 1
                processed_in_batch += 1
                db.commit()
            except Exception as e:
                log_error(error_logger, entity_type, affiliate.id, e, {'affiliate_data': affiliate.__dict__})
                failed_affiliates.append(affiliate.id)
                db.rollback()
                continue

        # Update offset by the total number of affiliates received
        offset += len(affiliates)
        checkpoint_manager.save_checkpoint(entity_type, offset)
        logger.debug(f"Successfully processed batch of {processed_in_batch} affiliates")

        if failed_affiliates:
            logger.warning(f"Failed to process affiliates: {failed_affiliates}")

        logger.info(f"Loaded {total_affiliates} affiliates so far")


def load_affiliate_commissions(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                               batch_size: int = 50,
                               update: bool = False) -> None:
    """Load all affiliate commissions."""
    entity_type = 'affiliate_commissions'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_commissions = 0

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

            processed_in_batch = 0
            failed_commissions = []

            for commission in commissions:
                try:
                    # Validate commission data
                    if not commission.affiliate_id:
                        raise ValueError("Affiliate ID is required for commission")

                    # Use merge operation to handle both inserts and updates
                    merged_commission = db.merge(commission)
                    total_commissions += 1
                    processed_in_batch += 1
                    db.commit()
                except Exception as e:
                    log_error(error_logger, entity_type, commission.id, e, {'commission_data': commission.__dict__})
                    failed_commissions.append(commission.id)
                    db.rollback()
                    continue

            logger.debug(
                f"Successfully processed batch of {processed_in_batch} commissions for affiliate {affiliate_id}")

            if failed_commissions:
                logger.warning(f"Failed to process commissions: {failed_commissions}")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_commissions} commissions in total")


def load_affiliate_programs(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                            batch_size: int = 50,
                            update: bool = False) -> None:
    """Load all affiliate programs."""
    entity_type = 'affiliate_programs'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_programs = 0

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

            processed_in_batch = 0
            failed_programs = []

            for program in programs:
                try:
                    # Validate program data
                    if not program.affiliate_id:
                        raise ValueError("Affiliate ID is required for program")

                    # Use merge operation to handle both inserts and updates
                    merged_program = db.merge(program)
                    total_programs += 1
                    processed_in_batch += 1
                    db.commit()
                except Exception as e:
                    log_error(error_logger, entity_type, program.id, e, {'program_data': program.__dict__})
                    failed_programs.append(program.id)
                    db.rollback()
                    continue

            logger.debug(f"Successfully processed batch of {processed_in_batch} programs for affiliate {affiliate_id}")

            if failed_programs:
                logger.warning(f"Failed to process programs: {failed_programs}")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_programs} programs in total")


def load_affiliate_redirects(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                             batch_size: int = 50,
                             update: bool = False) -> None:
    """Load all affiliate redirects."""
    entity_type = 'affiliate_redirects'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_redirects = 0

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

            processed_in_batch = 0
            failed_redirects = []

            for redirect in redirects:
                try:
                    # Validate redirect data
                    if not redirect.affiliate_id:
                        raise ValueError("Affiliate ID is required for redirect")

                    # Use merge operation to handle both inserts and updates
                    merged_redirect = db.merge(redirect)
                    total_redirects += 1
                    processed_in_batch += 1
                    db.commit()
                except Exception as e:
                    log_error(error_logger, entity_type, redirect.id, e, {'redirect_data': redirect.__dict__})
                    failed_redirects.append(redirect.id)
                    db.rollback()
                    continue

            logger.debug(f"Successfully processed batch of {processed_in_batch} redirects for affiliate {affiliate_id}")

            if failed_redirects:
                logger.warning(f"Failed to process redirects: {failed_redirects}")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_redirects} redirects in total")


def load_affiliate_summaries(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager) -> None:
    """Load all affiliate summaries."""
    entity_type = 'affiliate_summaries'
    total_summaries = 0

    # Get all affiliate IDs
    affiliate_ids = [a.id for a in db.query(Affiliate).all()]

    for affiliate_id in affiliate_ids:
        logger.info(f"Processing summary for affiliate ID: {affiliate_id}")
        try:
            summary = client.get_affiliate_summary(affiliate_id)
            logger.info(f"Received summary for affiliate {affiliate_id}")

            try:
                # Validate summary data
                if not summary.affiliate_id:
                    raise ValueError("Affiliate ID is required for summary")

                # Use merge operation to handle both inserts and updates
                merged_summary = db.merge(summary)
                total_summaries += 1
                db.commit()
            except Exception as e:
                log_error(error_logger, entity_type, summary.id, e, {'summary_data': summary.__dict__})
                db.rollback()
                continue

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_summaries} summaries in total")


def load_affiliate_clawbacks(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                             batch_size: int = 50,
                             update: bool = False) -> None:
    """Load all affiliate clawbacks."""
    entity_type = 'affiliate_clawbacks'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_clawbacks = 0

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

            processed_in_batch = 0
            failed_clawbacks = []

            for clawback in clawbacks:
                try:
                    # Validate clawback data
                    if not clawback.affiliate_id:
                        raise ValueError("Affiliate ID is required for clawback")

                    # Use merge operation to handle both inserts and updates
                    merged_clawback = db.merge(clawback)
                    total_clawbacks += 1
                    processed_in_batch += 1
                    db.commit()
                except Exception as e:
                    log_error(error_logger, entity_type, clawback.id, e, {'clawback_data': clawback.__dict__})
                    failed_clawbacks.append(clawback.id)
                    db.rollback()
                    continue

            logger.debug(f"Successfully processed batch of {processed_in_batch} clawbacks for affiliate {affiliate_id}")

            if failed_clawbacks:
                logger.warning(f"Failed to process clawbacks: {failed_clawbacks}")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_clawbacks} clawbacks in total")


def load_affiliate_payments(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager,
                            batch_size: int = 50,
                            update: bool = False) -> None:
    """Load all affiliate payments."""
    entity_type = 'affiliate_payments'
    offset = checkpoint_manager.get_checkpoint(entity_type)
    total_payments = 0

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

            processed_in_batch = 0
            failed_payments = []

            for payment in payments:
                try:
                    # Validate payment data
                    if not payment.affiliate_id:
                        raise ValueError("Affiliate ID is required for payment")

                    # Use merge operation to handle both inserts and updates
                    merged_payment = db.merge(payment)
                    total_payments += 1
                    processed_in_batch += 1
                    db.commit()
                except Exception as e:
                    log_error(error_logger, entity_type, payment.id, e, {'payment_data': payment.__dict__})
                    failed_payments.append(payment.id)
                    db.rollback()
                    continue

            logger.debug(f"Successfully processed batch of {processed_in_batch} payments for affiliate {affiliate_id}")

            if failed_payments:
                logger.warning(f"Failed to process payments: {failed_payments}")

        except Exception as e:
            log_error(error_logger, entity_type, affiliate_id, e, {'affiliate_id': affiliate_id})
            continue

    logger.info(f"Loaded {total_payments} payments in total")


def main(update: bool = False):
    """Main function to perform the data load.
    
    Args:
        update: Whether to perform an update operation using last_loaded timestamps
    """
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
        load_tags(client, db, checkpoint_manager, update=update)

        # Then load contacts and their related data
        load_contacts(client, db, checkpoint_manager, update=update)

        # Load remaining data
        load_products(client, db, checkpoint_manager, update=update)
        load_opportunities(client, db, checkpoint_manager, update=update)
        load_orders(client, db, checkpoint_manager, update=update)
        load_tasks(client, db, checkpoint_manager, update=update)
        load_notes(client, db, checkpoint_manager, update=update)
        load_campaigns(client, db, checkpoint_manager, update=update)
        load_subscriptions(client, db, checkpoint_manager, update=update)

        # Load affiliate data after contacts are loaded
        load_affiliates(client, db, checkpoint_manager, update=update)
        load_affiliate_commissions(client, db, checkpoint_manager, update=update)
        load_affiliate_programs(client, db, checkpoint_manager, update=update)
        load_affiliate_redirects(client, db, checkpoint_manager, update=update)
        load_affiliate_summaries(client, db, checkpoint_manager)
        load_affiliate_clawbacks(client, db, checkpoint_manager, update=update)
        load_affiliate_payments(client, db, checkpoint_manager, update=update)

        logger.info("Data load completed successfully!")

    except Exception as e:
        logger.error(f"Error during data load: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Load data from Keap API')
    parser.add_argument('--update', action='store_true', help='Perform update operation using last_loaded timestamps')
    args = parser.parse_args()
    main(update=args.update)
