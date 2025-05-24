import logging
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.models.models import (
    Contact, EmailAddress, PhoneNumber, Address, Tag, CustomFieldValue,
    Opportunity, Product, Order, OrderItem, Task, Note, Campaign,
    CampaignSequence, Subscription
)
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

    def save_checkpoint(self, entity_type: str, offset: int, timestamp: Optional[str] = None) -> None:
        if entity_type not in self.checkpoints:
            self.checkpoints[entity_type] = {}
        
        self.checkpoints[entity_type]['offset'] = offset
        if timestamp:
            self.checkpoints[entity_type]['last_loaded'] = timestamp
            
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

    def get_query_params(self, entity_type: str, resume: bool) -> Dict[str, Any]:
        """
        Get the appropriate query parameters based on the entity type and resume flag.
        
        Args:
            entity_type: The type of entity being loaded
            resume: Whether this is a resume operation
            
        Returns:
            Dict containing the query parameters to use
        """
        params = {}
        
        if not resume:
            last_loaded = self.get_last_loaded_timestamp(entity_type)
            if last_loaded:
                params['since'] = last_loaded
                
        return params

def load_contacts(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all contacts and their related data."""
    offset = checkpoint_manager.get_checkpoint('contacts')
    total_contacts = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('contacts', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching contacts with params: {query_params}")
        contacts = client.get_contacts(**query_params)
        logger.info(f"Received {len(contacts) if contacts else 0} contacts from API")
        
        if not contacts:
            logger.info("No more contacts to load")
            break
            
        processed_in_batch = 0
        failed_contacts = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for contact in contacts:
            logger.info(f"Processing contact ID: {contact.id}")
            try:
                full_contact = client.get_contact(contact.id)
                
                logger.info(f"Contact {contact.id} related data: "
                           f"{len(full_contact.email_addresses)} emails, "
                           f"{len(full_contact.phone_numbers)} phones, "
                           f"{len(full_contact.addresses)} addresses, "
                           f"{len(full_contact.tags)} tags, "
                           f"{len(full_contact.custom_field_values)} custom fields")
                
                merged_contact = db.merge(full_contact)
                total_contacts += 1
                processed_in_batch += 1
                
            except Exception as e:
                logger.error(f"Error processing contact {contact.id}: {str(e)}")
                failed_contacts.append(contact.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                # Update checkpoint with both offset and timestamp
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('contacts', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} contacts")
                
                if failed_contacts:
                    logger.warning(f"Failed to process contacts: {failed_contacts}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            # Don't update checkpoint on commit failure
            continue
            
        logger.info(f"Processed {total_contacts} contacts so far")

def load_tags(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all tags."""
    offset = checkpoint_manager.get_checkpoint('tags')
    total_tags = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('tags', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching tags with params: {query_params}")
        tags = client.get_tags(**query_params)
        logger.info(f"Received {len(tags) if tags else 0} tags from API")
        
        if not tags:
            break
            
        processed_in_batch = 0
        failed_tags = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for tag in tags:
            logger.info(f"Processing tag: {tag.name} (ID: {tag.id})")
            try:
                merged_tag = db.merge(tag)
                total_tags += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing tag {tag.id}: {str(e)}")
                failed_tags.append(tag.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('tags', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} tags")
                
                if failed_tags:
                    logger.warning(f"Failed to process tags: {failed_tags}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_tags} tags so far")

def load_custom_fields(client: KeapClient, db: Session, batch_size: int = 50, resume: bool = False) -> None:
    """Load all custom fields."""
    offset = 0
    total_fields = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('custom_fields', resume)
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
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for field in custom_fields:
            logger.info(f"Processing custom field: {field.name} (ID: {field.id}, Type: {field.type})")
            try:
                db.add(field)
                total_fields += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing custom field {field.id}: {str(e)}")
                failed_fields.append(field.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('custom_fields', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} custom fields")
                
                if failed_fields:
                    logger.warning(f"Failed to process custom fields: {failed_fields}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_fields} custom fields so far")

def load_opportunities(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all opportunities."""
    offset = checkpoint_manager.get_checkpoint('opportunities')
    total_opportunities = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('opportunities', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching opportunities with params: {query_params}")
        opportunities = client.get_opportunities(**query_params)
        logger.info(f"Received {len(opportunities) if opportunities else 0} opportunities from API")
        
        if not opportunities:
            break
            
        processed_in_batch = 0
        failed_opportunities = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for opportunity in opportunities:
            try:
                merged_opportunity = db.merge(opportunity)
                total_opportunities += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing opportunity {opportunity.id}: {str(e)}")
                failed_opportunities.append(opportunity.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('opportunities', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} opportunities")
                
                if failed_opportunities:
                    logger.warning(f"Failed to process opportunities: {failed_opportunities}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_opportunities} opportunities so far")

def load_products(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all products, including subscription plans."""
    offset = checkpoint_manager.get_checkpoint('products')
    total_products = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('products', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching products with params: {query_params}")
        products = client.get_products(**query_params)
        logger.info(f"Received {len(products) if products else 0} products from API")
        
        if not products:
            break
            
        processed_in_batch = 0
        failed_products = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for product in products:
            try:
                merged_product = db.merge(product)
                total_products += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing product {product.id}: {str(e)}")
                failed_products.append(product.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('products', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} products")
                
                if failed_products:
                    logger.warning(f"Failed to process products: {failed_products}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_products} products so far")

def load_orders(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all orders with their items."""
    offset = checkpoint_manager.get_checkpoint('orders')
    total_orders = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('orders', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching orders with params: {query_params}")
        orders = client.get_orders(**query_params)
        logger.info(f"Received {len(orders) if orders else 0} orders from API")
        
        if not orders:
            break
            
        processed_in_batch = 0
        failed_orders = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for order in orders:
            try:
                merged_order = db.merge(order)
                total_orders += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
                failed_orders.append(order.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('orders', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} orders")
                
                if failed_orders:
                    logger.warning(f"Failed to process orders: {failed_orders}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_orders} orders so far")

def load_tasks(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all tasks."""
    offset = checkpoint_manager.get_checkpoint('tasks')
    total_tasks = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('tasks', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching tasks with params: {query_params}")
        tasks = client.get_tasks(**query_params)
        logger.info(f"Received {len(tasks) if tasks else 0} tasks from API")
        
        if not tasks:
            break
            
        processed_in_batch = 0
        failed_tasks = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for task in tasks:
            try:
                merged_task = db.merge(task)
                total_tasks += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing task {task.id}: {str(e)}")
                failed_tasks.append(task.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('tasks', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} tasks")
                
                if failed_tasks:
                    logger.warning(f"Failed to process tasks: {failed_tasks}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_tasks} tasks so far")

def load_notes(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all notes."""
    offset = checkpoint_manager.get_checkpoint('notes')
    total_notes = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('notes', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching notes with params: {query_params}")
        notes = client.get_notes(**query_params)
        logger.info(f"Received {len(notes) if notes else 0} notes from API")
        
        if not notes:
            break
            
        processed_in_batch = 0
        failed_notes = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for note in notes:
            try:
                merged_note = db.merge(note)
                total_notes += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing note {note.id}: {str(e)}")
                failed_notes.append(note.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('notes', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} notes")
                
                if failed_notes:
                    logger.warning(f"Failed to process notes: {failed_notes}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_notes} notes so far")

def load_campaigns(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all campaigns and their sequences."""
    offset = checkpoint_manager.get_checkpoint('campaigns')
    total_campaigns = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('campaigns', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching campaigns with params: {query_params}")
        campaigns = client.get_campaigns(**query_params)
        logger.info(f"Received {len(campaigns) if campaigns else 0} campaigns from API")
        
        if not campaigns:
            break
            
        processed_in_batch = 0
        failed_campaigns = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for campaign in campaigns:
            try:
                sequences = client.get_campaign_sequences(campaign.id)
                campaign.sequences = sequences
                merged_campaign = db.merge(campaign)
                total_campaigns += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing campaign {campaign.id}: {str(e)}")
                failed_campaigns.append(campaign.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('campaigns', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} campaigns")
                
                if failed_campaigns:
                    logger.warning(f"Failed to process campaigns: {failed_campaigns}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_campaigns} campaigns so far")

def load_subscriptions(client: KeapClient, db: Session, checkpoint_manager: CheckpointManager, batch_size: int = 50, resume: bool = False) -> None:
    """Load all active subscriptions."""
    offset = checkpoint_manager.get_checkpoint('subscriptions')
    total_subscriptions = 0
    
    # Get query parameters including since timestamp if applicable
    query_params = checkpoint_manager.get_query_params('subscriptions', resume)
    query_params.update({
        'limit': batch_size,
        'offset': offset
    })
    
    while True:
        logger.info(f"Fetching subscriptions with params: {query_params}")
        subscriptions = client.get_subscriptions(**query_params)
        logger.info(f"Received {len(subscriptions) if subscriptions else 0} subscriptions from API")
        
        if not subscriptions:
            break
            
        processed_in_batch = 0
        failed_subscriptions = []
        current_timestamp = datetime.now(timezone.utc).isoformat()
        
        for subscription in subscriptions:
            try:
                merged_subscription = db.merge(subscription)
                total_subscriptions += 1
                processed_in_batch += 1
            except Exception as e:
                logger.error(f"Error processing subscription {subscription.id}: {str(e)}")
                failed_subscriptions.append(subscription.id)
                continue
        
        try:
            if processed_in_batch > 0:
                db.commit()
                offset += processed_in_batch
                checkpoint_manager.save_checkpoint('subscriptions', offset, current_timestamp)
                logger.debug(f"Successfully committed batch of {processed_in_batch} subscriptions")
                
                if failed_subscriptions:
                    logger.warning(f"Failed to process subscriptions: {failed_subscriptions}")
        except Exception as e:
            logger.error(f"Error committing batch: {str(e)}")
            db.rollback()
            continue
            
        logger.info(f"Loaded {total_subscriptions} subscriptions so far")

def main(resume: bool = False):
    """Main function to perform the initial data load."""
    client = KeapClient()
    db = SessionLocal()
    checkpoint_manager = CheckpointManager()
    
    # Initialize database tables
    from src.database.init_db import init_db
    init_db()
    
    if not resume:
        checkpoint_manager.clear_checkpoints()
        logger.info("Starting fresh data load...")
    else:
        logger.info("Resuming previous data load...")
    
    try:
        # Load data in a specific order to maintain referential integrity
        load_tags(client, db, checkpoint_manager, resume=resume)
        load_contacts(client, db, checkpoint_manager, resume=resume)
        load_products(client, db, checkpoint_manager, resume=resume)
        load_opportunities(client, db, checkpoint_manager, resume=resume)
        load_orders(client, db, checkpoint_manager, resume=resume)
        load_tasks(client, db, checkpoint_manager, resume=resume)
        load_notes(client, db, checkpoint_manager, resume=resume)
        load_campaigns(client, db, checkpoint_manager, resume=resume)
        load_subscriptions(client, db, checkpoint_manager, resume=resume)
        
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
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    args = parser.parse_args()
    main(resume=args.resume) 