from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Contact, \
    Opportunity


class OpportunityTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Opportunity:
        """Transform opportunity data from Keap API to database model."""
        # Create or update opportunity
        opportunity = db.query(Opportunity).filter_by(id=data['id']).first()
        if not opportunity:
            opportunity = Opportunity(id=data['id'])
            db.add(opportunity)

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

        return opportunity
