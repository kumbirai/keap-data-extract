"""
Specialized loader for contacts with complex relationships.

This loader demonstrates how to handle entities with multiple related
data types like credit cards, tags, email addresses, etc.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.models import Tag
from src.transformers.transformers import transform_credit_card
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class ContactLoader(BaseEntityLoader):
    """Specialized loader for contacts with complex relationships.
    
    This loader handles the complex relationships that contacts have:
    - Credit cards
    - Tags
    - Email addresses
    - Phone numbers
    - Addresses
    - Custom field values
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "contacts", "get_contacts", "get_contact")

    def _process_entity(self, contact: Any) -> None:
        """Process contact-specific relationships.
        
        This method handles all the complex relationship processing that
        was duplicated in the original load_contact_by_id function.
        """
        # Get credit cards for this contact
        try:
            credit_cards_data, _ = self.client.get_contact_credit_cards(contact.id)
            logger.info(f"Retrieved {len(credit_cards_data)} credit cards for contact {contact.id}")
            # Transform credit card dictionaries into model instances
            credit_cards = [transform_credit_card(card_data) for card_data in credit_cards_data]
        except Exception as e:
            logger.info(f"Error fetching credit cards for contact {contact.id}: {e}")
            credit_cards = []

        # Get tag IDs and existing tags
        tags = contact.tags if hasattr(contact, 'tags') else []
        tag_ids = [tag.id for tag in tags]
        existing_tags = self.db.query(Tag).filter(Tag.id.in_(tag_ids)).all()

        # Clear existing credit cards and set new ones
        contact.credit_cards = []
        for credit_card in credit_cards:
            contact.credit_cards.append(credit_card)

        # Set other relationships before merging
        if hasattr(contact, 'email_addresses'):
            contact.email_addresses = contact.email_addresses
        if hasattr(contact, 'phone_numbers'):
            contact.phone_numbers = contact.phone_numbers
        if hasattr(contact, 'addresses'):
            contact.addresses = contact.addresses
        if hasattr(contact, 'tags'):
            # Clear existing tags and set new ones
            contact.tags = []
            for tag in existing_tags:
                contact.tags.append(tag)
        if hasattr(contact, 'custom_field_values'):
            contact.custom_field_values = contact.custom_field_values

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to contacts."""
        return {'id': item.id, 'given_name': getattr(item, 'given_name', None), 'family_name': getattr(item, 'family_name', None), 'date_created': getattr(item, 'date_created', None),
                'last_updated': getattr(item, 'last_updated', None)}
