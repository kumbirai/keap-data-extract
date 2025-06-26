"""
Specialized loader for opportunities.

Opportunities have relationships with contacts and custom field values
that need special handling during the loading process.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.models import Contact
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class OpportunityLoader(BaseEntityLoader):
    """Specialized loader for opportunities with relationship handling.
    
    Opportunities are unique because:
    1. They have relationships with contacts that need to be properly linked
    2. They have custom field values that need to be processed
    3. They have stage information stored as JSON
    4. They may have owner references that need validation
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "opportunities", "get_opportunities", "get_opportunity")

    def _process_entity(self, opportunity: Any) -> None:
        """Process opportunity-specific relationships.
        
        This method handles the complex relationships that opportunities have:
        - Contact relationships
        - Custom field values
        - Stage information validation
        """
        # Handle contact relationships
        if hasattr(opportunity, 'contacts'):
            # Ensure all referenced contacts exist in the database
            self._ensure_contacts_exist(opportunity.contacts)
            opportunity.contacts = opportunity.contacts

        # Handle custom field values
        if hasattr(opportunity, 'custom_field_values'):
            opportunity.custom_field_values = opportunity.custom_field_values

        # Validate and process stage information
        self._process_stage_information(opportunity)

        # Handle owner references
        self._handle_owner_references(opportunity)

    def _ensure_contacts_exist(self, contacts: list) -> None:
        """Ensure all referenced contacts exist in the database.
        
        This method checks if the contacts associated with an opportunity
        exist in the database and logs warnings for any missing contacts.
        """
        if not contacts:
            return

        for contact in contacts:
            try:
                # Check if contact exists in database
                existing_contact = self.db.query(Contact).filter(Contact.id == contact.id).first()

                if existing_contact is None:
                    logger.warning(f"Contact ID {contact.id} referenced by opportunity not found in database")
                else:
                    logger.debug(f"Contact ID {contact.id} exists in database")

            except Exception as e:
                logger.error(f"Error checking contact ID {contact.id}: {str(e)}")

    def _process_stage_information(self, opportunity: Any) -> None:
        """Process and validate stage information.
        
        Opportunities store stage information as JSON, which may include
        stage details, pipeline information, and other metadata.
        """
        if hasattr(opportunity, 'stage') and opportunity.stage:
            try:
                # Log stage information for debugging
                if isinstance(opportunity.stage, dict):
                    stage_name = opportunity.stage.get('name', 'Unknown')
                    logger.debug(f"Processing opportunity {opportunity.id} with stage: {stage_name}")
                else:
                    logger.debug(f"Processing opportunity {opportunity.id} with stage: {opportunity.stage}")

            except Exception as e:
                logger.warning(f"Error processing stage information for opportunity {opportunity.id}: {str(e)}")

    def _handle_owner_references(self, opportunity: Any) -> None:
        """Handle owner references in opportunities.
        
        Opportunities may have owner_id references that need to be validated
        or processed appropriately.
        """
        if hasattr(opportunity, 'owner_id') and opportunity.owner_id:
            try:
                # For now, just log owner references
                # In the future, this could validate against a users table
                logger.debug(f"Opportunity {opportunity.id} has owner_id: {opportunity.owner_id}")

            except Exception as e:
                logger.warning(f"Error processing owner reference for opportunity {opportunity.id}: {str(e)}")

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to opportunities."""
        return {'id': item.id, 'title': getattr(item, 'title', None), 'stage': getattr(item, 'stage', None), 'value': getattr(item, 'value', None), 'probability': getattr(item, 'probability', None),
                'created_at': getattr(item, 'created_at', None), 'modified_at': getattr(item, 'modified_at', None)}
