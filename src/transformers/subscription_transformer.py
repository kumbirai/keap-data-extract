from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Contact, Product, Subscription


class SubscriptionTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Subscription:
        """Transform subscription data from Keap API to database model."""
        # Create or update subscription
        subscription = db.query(Subscription).filter_by(id=data['id']).first()
        if not subscription:
            subscription = Subscription(id=data['id'])
            db.add(subscription)

        # Update basic fields
        subscription.status = data.get('status')
        subscription.next_bill_date = data.get('next_bill_date')
        subscription.last_updated = datetime.utcnow()

        # Handle contact relationship
        if 'contact' in data:
            contact = db.query(Contact).filter_by(id=data['contact']['id']).first()
            if contact:
                # Clear existing contact relationships
                subscription.contacts = []
                subscription.contacts.append(contact)

        # Handle product relationship
        if 'product' in data:
            product = db.query(Product).filter_by(id=data['product']['id']).first()
            if product:
                # Clear existing product relationships
                subscription.products = []
                subscription.products.append(product)

        return subscription
