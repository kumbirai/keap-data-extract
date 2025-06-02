from datetime import datetime

from sqlalchemy.orm import Session
from src.utils.logger import get_logger

from src.models.models import Contact, Opportunity

logger = get_logger(__name__)


class OpportunityTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Opportunity:
        """Transform opportunity data from Keap API to database model."""
        try:
            # Create or update opportunity
            opportunity = db.query(Opportunity).filter_by(id=data['id']).first()
            if not opportunity:
                opportunity = Opportunity(id=data['id'])

            # Update basic fields
            opportunity.title = data.get('title')
            opportunity.value = data.get('value')
            opportunity.status = data.get('status')
            opportunity.last_updated = datetime.utcnow()

            # Handle contact relationship
            if 'contact' in data:
                contact = db.query(Contact).filter_by(id=data['contact']['id']).first()
                if contact:
                    # Clear existing contact relationships
                    opportunity.contacts = []
                    opportunity.contacts.append(contact)

            # Merge the opportunity itself
            db.merge(opportunity)
            return opportunity

        except Exception as e:
            logger.error(f"Error transforming opportunity data: {str(e)}")
            raise
