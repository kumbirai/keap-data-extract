from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Campaign, CampaignSequence
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CampaignTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Campaign:
        """Transform campaign data from Keap API to database model."""
        try:
            # Create or update campaign
            campaign = db.query(Campaign).filter_by(id=data['id']).first()
            if not campaign:
                campaign = Campaign(id=data['id'])

            # Update basic fields
            campaign.name = data.get('name')
            campaign.description = data.get('description')
            campaign.status = data.get('status')
            campaign.last_updated = datetime.utcnow()

            # Handle sequences
            if 'sequences' in data:
                # Clear existing sequence relationships
                campaign.sequences = []
                for seq_data in data['sequences']:
                    sequence = CampaignSequence(id=seq_data['id'], name=seq_data.get('name'), status=seq_data.get('status'))
                    sequence.campaign = campaign
                    db.merge(sequence)
                    campaign.sequences.append(sequence)

            # Merge the campaign itself
            db.merge(campaign)
            return campaign

        except Exception as e:
            logger.error(f"Error transforming campaign data: {str(e)}")
            raise
