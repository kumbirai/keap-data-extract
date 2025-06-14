from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Contact, Product, Subscription
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Subscription:
        """Transform subscription data from Keap API to database model."""
        try:
            # Create or update subscription
            subscription = db.query(Subscription).filter_by(id=data['id']).first()
            if not subscription:
                subscription = Subscription(id=data['id'])

            # Update basic fields
            subscription.status = data.get('status')
            subscription.next_bill_date = data.get('next_bill_date')
            subscription.last_updated = datetime.utcnow()

            # Handle contact relationship
            if 'contacts' in data:
                subscription.contacts = []
                for contact_data in data['contacts']:
                    contact = db.query(Contact).filter_by(id=contact_data['id']).first()
                    if contact:
                        subscription.contacts.append(contact)

            # Handle product relationship
            if 'products' in data:
                subscription.products = []
                for product_data in data['products']:
                    product = db.query(Product).filter_by(id=product_data['id']).first()
                    if product:
                        subscription.products.append(product)

            # Merge the subscription itself
            db.merge(subscription)
            return subscription

        except Exception as e:
            logger.error(f"Error transforming subscription data: {str(e)}")
            raise
