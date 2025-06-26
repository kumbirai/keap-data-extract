"""
Specialized loader for campaigns.

Campaigns have relationships with sequences and specific attributes like status,
description, and creation/modification dates that need special handling.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class CampaignLoader(BaseEntityLoader):
    """Specialized loader for campaigns with relationship handling.
    
    Campaigns are unique because:
    1. They have relationships with campaign sequences that need to be properly linked
    2. They have various statuses (Draft, Active, Paused, Completed, etc.) that need validation
    3. They have descriptions that may need processing or validation
    4. They may have complex sequence relationships that need special handling
    5. They are foundational for marketing automation workflows
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "campaigns", "get_campaigns", "get_campaign")

    def _process_entity(self, campaign: Any) -> None:
        """Process campaign-specific relationships and attributes.
        
        This method handles the complex relationships and attributes that campaigns have:
        - Sequence relationships
        - Campaign status validation
        - Description processing
        - Creation and modification dates
        """
        # Handle sequence relationships
        if hasattr(campaign, 'sequences'):
            # Process campaign sequences
            self._process_campaign_sequences(campaign.sequences)
            campaign.sequences = campaign.sequences

        # Validate and process campaign attributes
        self._process_campaign_attributes(campaign)

        # Handle campaign content and description
        self._process_campaign_content(campaign)

    def _process_campaign_sequences(self, sequences: list) -> None:
        """Process campaign sequences.
        
        This method handles the sequences associated with a campaign,
        including validation and logging of sequence information.
        """
        if not sequences:
            logger.debug("Campaign has no sequences")
            return

        logger.debug(f"Processing {len(sequences)} sequences for campaign")

        for sequence in sequences:
            try:
                # Log sequence information
                sequence_id = getattr(sequence, 'id', 'Unknown')
                sequence_name = getattr(sequence, 'name', 'Unknown')
                sequence_number = getattr(sequence, 'sequence_number', 'Unknown')
                sequence_status = getattr(sequence, 'status', 'Unknown')

                logger.debug(f"Sequence {sequence_id}: {sequence_name} (Number: {sequence_number}, Status: {sequence_status})")

                # Could add sequence validation here
                self._validate_sequence_attributes(sequence)

            except Exception as e:
                logger.warning(f"Error processing sequence: {str(e)}")

    def _validate_sequence_attributes(self, sequence: Any) -> None:
        """Validate sequence attributes."""
        try:
            # Validate sequence number
            if hasattr(sequence, 'sequence_number') and sequence.sequence_number is not None:
                if not isinstance(sequence.sequence_number, int) or sequence.sequence_number < 0:
                    logger.warning(f"Invalid sequence number: {sequence.sequence_number}")

            # Validate sequence name
            if hasattr(sequence, 'name') and sequence.name:
                if len(sequence.name.strip()) == 0:
                    logger.warning("Sequence has empty name")

            # Validate sequence status
            if hasattr(sequence, 'status') and sequence.status:
                valid_statuses = ['Active', 'Inactive', 'Draft', 'Completed', 'Paused']
                if sequence.status not in valid_statuses:
                    logger.warning(f"Unknown sequence status: {sequence.status}")

        except Exception as e:
            logger.warning(f"Error validating sequence attributes: {str(e)}")

    def _process_campaign_attributes(self, campaign: Any) -> None:
        """Process and validate campaign-specific attributes.
        
        This method handles campaign status, name, and other attributes
        with appropriate validation and logging.
        """
        # Log campaign name
        if hasattr(campaign, 'name') and campaign.name:
            logger.debug(f"Processing campaign: {campaign.name}")
        elif hasattr(campaign, 'name') and not campaign.name:
            logger.warning(f"Campaign {campaign.id} has no name")

        # Log and validate campaign status
        if hasattr(campaign, 'status') and campaign.status:
            logger.debug(f"Campaign {campaign.id} has status: {campaign.status}")
            self._validate_campaign_status(campaign.status)
        elif hasattr(campaign, 'status') and not campaign.status:
            logger.debug(f"Campaign {campaign.id} has no status")

        # Process creation and modification dates
        if hasattr(campaign, 'created_at') and campaign.created_at:
            logger.debug(f"Campaign {campaign.id} was created on: {campaign.created_at}")

        if hasattr(campaign, 'modified_at') and campaign.modified_at:
            logger.debug(f"Campaign {campaign.id} was modified on: {campaign.modified_at}")

    def _validate_campaign_status(self, status: str) -> None:
        """Validate campaign status against known statuses."""
        valid_statuses = ['Draft', 'Active', 'Paused', 'Completed', 'Archived', 'Scheduled', 'Stopped']

        if status not in valid_statuses:
            logger.warning(f"Unknown campaign status: {status}")

    def _process_campaign_content(self, campaign: Any) -> None:
        """Process campaign content like description."""
        # Process campaign description
        if hasattr(campaign, 'description') and campaign.description:
            try:
                # Log description length for debugging
                desc_length = len(campaign.description) if campaign.description else 0
                logger.debug(f"Campaign {campaign.id} has description with {desc_length} characters")

                # Could add content validation here (e.g., check for required fields)
                # Could add content processing here (e.g., HTML sanitization, link extraction)
                self._process_description_content(campaign.description)

            except Exception as e:
                logger.warning(f"Error processing description for campaign {campaign.id}: {str(e)}")
        elif hasattr(campaign, 'description') and not campaign.description:
            logger.debug(f"Campaign {campaign.id} has no description")

    def _process_description_content(self, description: str) -> None:
        """Process the description content of a campaign.
        
        This method can be extended to handle various content processing needs:
        - HTML sanitization
        - Link extraction
        - Content validation
        - Text analysis
        """
        try:
            # Basic content analysis
            if description:
                # Check for common patterns
                if '<' in description and '>' in description:
                    logger.debug("Campaign description contains HTML-like content")

                if 'http' in description:
                    logger.debug("Campaign description contains URLs")

                # Could add more sophisticated content processing here  # For example: keyword extraction, sentiment analysis, etc.

        except Exception as e:
            logger.warning(f"Error in description content processing: {str(e)}")

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to campaigns."""
        return {'id': item.id, 'name': getattr(item, 'name', None), 'status': getattr(item, 'status', None),
                'description_length': len(getattr(item, 'description', '')) if getattr(item, 'description', None) else 0,
                'sequence_count': len(getattr(item, 'sequences', [])) if hasattr(item, 'sequences') else 0, 'created_at': getattr(item, 'created_at', None),
                'modified_at': getattr(item, 'modified_at', None)}
