from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Contact, Order, OrderItem, Product


class OrderTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Order:
        """Transform order data from Keap API to database model."""
        # Create or update order
        order = db.query(Order).filter_by(id=data['id']).first()
        if not order:
            order = Order(id=data['id'])
            db.add(order)

        # Update basic fields
        order.order_number = data.get('order_number')
        order.order_date = data.get('order_date')
        order.total = data.get('total')
        order.status = data.get('status')
        order.last_updated = datetime.utcnow()

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
                order_item = OrderItem(id=item_data['id'], quantity=item_data.get('quantity'), price=item_data.get('price'))
                db.add(order_item)
                order.items.append(order_item)

                # Handle product relationship
                if 'product' in item_data:
                    product = db.query(Product).filter_by(id=item_data['product']['id']).first()
                    if product:
                        # Clear existing product relationships
                        order_item.products = []
                        order_item.products.append(product)

        return order
