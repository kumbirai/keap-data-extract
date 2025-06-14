from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Contact, Order, OrderItem, Product
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OrderTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Order:
        """Transform order data from Keap API to database model."""
        try:
            # Create or update order
            order = db.query(Order).filter_by(id=data['id']).first()
            if not order:
                order = Order(id=data['id'])

            # Update basic fields
            order.order_number = data.get('order_number')
            order.order_date = data.get('order_date')
            order.order_total = data.get('total')
            order.order_status = data.get('status')
            order.order_type = data.get('order_type')
            order.shipping_information = data.get('shipping_information')
            order.payment_gateway = data.get('payment_gateway')
            order.modified_at = datetime.utcnow()

            # Handle contact relationship
            if 'contact' in data:
                contact = db.query(Contact).filter_by(id=data['contact']['id']).first()
                if contact:
                    # Clear existing contact relationships
                    order.contacts = []
                    order.contacts.append(contact)

            # Handle order items
            if 'items' in data:
                # Clear existing item relationships
                order.items = []
                for item_data in data['items']:
                    # Create or update order item
                    order_item = OrderItem(id=item_data['id'], order_id=order.id, quantity=item_data.get('quantity'), price=item_data.get('price'), description=item_data.get('description'),
                                           subscription_plan_id=item_data.get('subscription_plan_id'))
                    order_item.order = order
                    db.merge(order_item)

                    # Handle product relationship
                    if 'product' in item_data:
                        product = db.query(Product).filter_by(id=item_data['product']['id']).first()
                        if product:
                            order_item.product_id = product.id

                    order.items.append(order_item)

            # Merge the order itself
            db.merge(order)
            return order

        except Exception as e:
            logger.error(f"Error transforming order data: {str(e)}")
            raise
