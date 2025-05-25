import logging
from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.models.models import Contact, EmailAddress, PhoneNumber, Address, Tag, CustomFieldValue
from src.utils.logging_config import setup_logging
from src.scripts.load_data import load_contacts, CheckpointManager

# Setup logging
setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    app_name="keap_data_extract_test"
)

logger = logging.getLogger(__name__)

def verify_contact_relationships(contact_id: int, db: Session) -> bool:
    """Verify that a contact's relationships were properly loaded."""
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            logger.error(f"Contact {contact_id} not found in database")
            return False
            
        # Get the contact from the API to compare
        client = KeapClient()
        api_contact = client.get_contact(contact_id)
        
        # Verify email addresses
        email_count = db.query(EmailAddress).filter(EmailAddress.contact_id == contact_id).count()
        if email_count != len(api_contact.email_addresses):
            logger.error(f"Email address count mismatch for contact {contact_id}. Expected {len(api_contact.email_addresses)}, got {email_count}")
            return False
            
        # Verify phone numbers
        phone_count = db.query(PhoneNumber).filter(PhoneNumber.contact_id == contact_id).count()
        if phone_count != len(api_contact.phone_numbers):
            logger.error(f"Phone number count mismatch for contact {contact_id}. Expected {len(api_contact.phone_numbers)}, got {phone_count}")
            return False
            
        # Verify addresses
        address_count = db.query(Address).filter(Address.contact_id == contact_id).count()
        if address_count != len(api_contact.addresses):
            logger.error(f"Address count mismatch for contact {contact_id}. Expected {len(api_contact.addresses)}, got {address_count}")
            return False
            
        # Verify tags
        tag_count = len(contact.tags)
        if tag_count != len(api_contact.tags):
            logger.error(f"Tag count mismatch for contact {contact_id}. Expected {len(api_contact.tags)}, got {tag_count}")
            return False
            
        # Verify custom field values
        cfv_count = db.query(CustomFieldValue).filter(CustomFieldValue.contact_id == contact_id).count()
        if cfv_count != len(api_contact.custom_field_values):
            logger.error(f"Custom field value count mismatch for contact {contact_id}. Expected {len(api_contact.custom_field_values)}, got {cfv_count}")
            return False
            
        logger.info(f"All relationships verified for contact {contact_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying relationships for contact {contact_id}: {str(e)}")
        return False

def test_data_load():
    """Test the full data loading process with relationship verification."""
    # Initialize database tables
    from src.database.init_db import init_db
    init_db()

    client = KeapClient()
    db = SessionLocal()
    checkpoint_manager = CheckpointManager()
    
    try:
        # Clear any existing checkpoints
        checkpoint_manager.clear_checkpoints()
        
        # Load a small batch of contacts
        logger.info("Loading contacts...")
        load_contacts(client, db, checkpoint_manager, batch_size=5)
        
        # Get the first few contacts from the database
        contacts = db.query(Contact).limit(5).all()
        
        # Verify relationships for each contact
        success_count = 0
        for contact in contacts:
            if verify_contact_relationships(contact.id, db):
                success_count += 1
                
        logger.info(f"Relationship verification completed. {success_count} out of {len(contacts)} contacts passed.")
        return success_count == len(contacts)
        
    except Exception as e:
        logger.error(f"Error during data load testing: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_data_load() 