import logging
from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.models.models import Contact, EmailAddress, PhoneNumber, Address, Tag, CustomFieldValue
from src.utils.logging_config import setup_logging

# Setup logging
setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    app_name="keap_data_extract_test"
)

logger = logging.getLogger(__name__)

def test_contact_relationships():
    """Test if contact relationships are being properly persisted."""
    # Initialize database tables
    from src.database.init_db import init_db
    init_db()

    client = KeapClient()
    db = SessionLocal()
    
    try:
        # Get a single contact with all its relationships
        contact_id = 92637  # Replace with an actual contact ID from your system
        contact = client.get_contact(contact_id)
        
        # Save the contact to the database
        db.add(contact)
        db.commit()
        
        # Verify the contact was saved
        saved_contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not saved_contact:
            logger.error(f"Contact {contact_id} was not saved")
            return False
            
        # Test email addresses
        email_count = db.query(EmailAddress).filter(EmailAddress.contact_id == contact_id).count()
        logger.info(f"Contact has {email_count} email addresses")
        if email_count != len(contact.email_addresses):
            logger.error(f"Email address count mismatch. Expected {len(contact.email_addresses)}, got {email_count}")
            return False
            
        # Test phone numbers
        phone_count = db.query(PhoneNumber).filter(PhoneNumber.contact_id == contact_id).count()
        logger.info(f"Contact has {phone_count} phone numbers")
        if phone_count != len(contact.phone_numbers):
            logger.error(f"Phone number count mismatch. Expected {len(contact.phone_numbers)}, got {phone_count}")
            return False
            
        # Test addresses
        address_count = db.query(Address).filter(Address.contact_id == contact_id).count()
        logger.info(f"Contact has {address_count} addresses")
        if address_count != len(contact.addresses):
            logger.error(f"Address count mismatch. Expected {len(contact.addresses)}, got {address_count}")
            return False
            
        # Test tags
        tag_count = len(saved_contact.tags)
        logger.info(f"Contact has {tag_count} tags")
        if tag_count != len(contact.tags):
            logger.error(f"Tag count mismatch. Expected {len(contact.tags)}, got {tag_count}")
            return False
            
        # Test custom field values
        cfv_count = db.query(CustomFieldValue).filter(CustomFieldValue.contact_id == contact_id).count()
        logger.info(f"Contact has {cfv_count} custom field values")
        if cfv_count != len(contact.custom_field_values):
            logger.error(f"Custom field value count mismatch. Expected {len(contact.custom_field_values)}, got {cfv_count}")
            return False
            
        # Test relationship content
        logger.info("Testing relationship content...")
        
        # Test email addresses content
        for email in contact.email_addresses:
            saved_email = db.query(EmailAddress).filter(
                EmailAddress.contact_id == contact_id,
                EmailAddress.email == email.email
            ).first()
            if not saved_email:
                logger.error(f"Email address {email.email} was not saved")
                return False
                
        # Test phone numbers content
        for phone in contact.phone_numbers:
            saved_phone = db.query(PhoneNumber).filter(
                PhoneNumber.contact_id == contact_id,
                PhoneNumber.number == phone.number
            ).first()
            if not saved_phone:
                logger.error(f"Phone number {phone.number} was not saved")
                return False
                
        # Test addresses content
        for address in contact.addresses:
            saved_address = db.query(Address).filter(
                Address.contact_id == contact_id,
                Address.line1 == address.line1
            ).first()
            if not saved_address:
                logger.error(f"Address {address.line1} was not saved")
                return False
                
        # Test tags content
        for tag in contact.tags:
            if tag not in saved_contact.tags:
                logger.error(f"Tag {tag.name} was not saved")
                return False
                
        # Test custom field values content
        for cfv in contact.custom_field_values:
            saved_cfv = db.query(CustomFieldValue).filter(
                CustomFieldValue.contact_id == contact_id,
                CustomFieldValue.custom_field_id == cfv.custom_field_id,
                CustomFieldValue.value == cfv.value
            ).first()
            if not saved_cfv:
                logger.error(f"Custom field value for field {cfv.custom_field_id} was not saved")
                return False
                
        logger.info("All relationship tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Error during relationship testing: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_contact_relationships() 