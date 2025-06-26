"""
Specialized loader for orders.

Orders have complex relationships including payments, transactions,
contacts, and affiliate references that need special handling.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.models import Affiliate, PaymentGateway
from .affiliate_loader import AffiliateLoader
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class OrderLoader(BaseEntityLoader):
    """Specialized loader for orders with complex relationship handling.
    
    Orders are unique because:
    1. They have payments and transactions that need to be fetched separately
    2. They reference affiliates that may be 0 (need to be set to None)
    3. They have complex relationships with contacts and custom fields
    4. They need special handling for order items and shipping information
    5. They can have associated payment plans with complex payment schedules
    6. Payment plans reference payment gateways through merchant_account_id
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "orders", "get_orders", "get_order")
        self.affiliate_loader = AffiliateLoader(client, db, checkpoint_manager)

    def _process_entity(self, order: Any) -> None:
        """Process order-specific relationships.
        
        This method handles the complex relationships that were duplicated
        in the original load_order_by_id function.
        """
        # Handle payment plan FIRST, before any other operations
        # This ensures payment gateways are created before the order is saved
        payment_plan = None
        if hasattr(order, 'payment_plan') and order.payment_plan:
            try:
                payment_plan = self._handle_payment_plan(order.payment_plan, order.id)
                logger.info(f"Processed payment plan for order ID: {order.id}")
            except Exception as e:
                logger.warning(f"Error processing payment plan for order {order.id}: {str(e)}")

        # Get order payments
        try:
            payments = self.client.get_order_payments(order.id)
            logger.info(f"Retrieved {len(payments)} payments for order ID: {order.id}")
        except Exception as e:
            logger.warning(f"Error getting payments for order {order.id}: {str(e)}")
            payments = []

        # Get order transactions
        try:
            transactions = self.client.get_order_transactions(order.id)
            logger.info(f"Retrieved {len(transactions)} transactions for order ID: {order.id}")
        except Exception as e:
            logger.warning(f"Error getting transactions for order {order.id}: {str(e)}")
            transactions = []

        # Clear and set relationships
        if hasattr(order, 'payments'):
            order.payments = []
            for payment in payments:
                order.payments.append(payment)

        if hasattr(order, 'transactions'):
            order.transactions = []
            for transaction in transactions:
                order.transactions.append(transaction)

        if hasattr(order, 'payment_plan') and payment_plan:
            order.payment_plan = payment_plan

        # Handle other relationships
        if hasattr(order, 'contacts'):
            order.contacts = order.contacts

        if hasattr(order, 'custom_field_values'):
            order.custom_field_values = order.custom_field_values

        if hasattr(order, 'items'):
            order.items = order.items

        if hasattr(order, 'shipping_information'):
            order.shipping_information = order.shipping_information

        # Handle affiliate references
        self._handle_affiliate_references(order)

        # Handle credit card references (for payment plans)
        if payment_plan and hasattr(payment_plan, 'credit_card_id'):
            self._handle_credit_card_references(payment_plan)

    def _handle_payment_plan(self, payment_plan_data: Any, order_id: int) -> Any:
        """Handle payment plan data from order API response.
        
        Args:
            payment_plan_data: The payment plan data from the order API response (could be dict or PaymentPlan object)
            order_id: The ID of the order this payment plan belongs to
            
        Returns:
            PaymentPlan object or None if not found
        """
        try:
            from src.models.models import PaymentPlan
            from src.transformers.transformers import transform_payment_plan

            # Check if payment plan exists in database first
            existing_plan = self.db.query(PaymentPlan).filter(PaymentPlan.order_id == order_id).first()

            if existing_plan:
                logger.debug(f"Payment plan for order {order_id} already exists in database")
                return existing_plan

            # Handle the case where payment_plan_data is already a PaymentPlan object
            if isinstance(payment_plan_data, PaymentPlan):
                payment_plan = payment_plan_data
                # Extract payment gateway data from the payment plan object
                gateway_data = {
                    'merchant_account_name': payment_plan.merchant_account_name
                }
            else:
                # Transform the payment plan data (it's a dictionary)
                payment_plan = transform_payment_plan(payment_plan_data, order_id)
                # Extract payment gateway data from the original data
                gateway_data = payment_plan_data.get('payment_gateway', {})
            
            # Handle payment gateway relationship
            if payment_plan.merchant_account_id:
                try:
                    self._ensure_payment_gateway_exists(payment_plan.merchant_account_id, gateway_data)
                except Exception as gateway_error:
                    logger.error(f"Failed to ensure payment gateway exists for order {order_id}: {str(gateway_error)}")
                    logger.warning(f"Skipping payment plan for order {order_id} due to payment gateway issue")
                    return None

            # Save to database
            try:
                merged_plan = self.db.merge(payment_plan)
                self.db.commit()
                logger.info(f"Successfully saved payment plan for order {order_id} to database")
                return merged_plan
            except Exception as db_error:
                logger.error(f"Error saving payment plan for order {order_id} to database: {str(db_error)}")
                self.db.rollback()
                return None  # Return None if save failed

        except Exception as e:
            logger.error(f"Error handling payment plan for order {order_id}: {str(e)}")
            return None

    def _handle_credit_card_references(self, payment_plan: Any) -> None:
        """Handle credit card references in payment plans - check if they exist and load if needed."""
        if hasattr(payment_plan, 'credit_card_id') and payment_plan.credit_card_id:
            self._ensure_credit_card_exists(payment_plan.credit_card_id)

    def _ensure_payment_gateway_exists(self, gateway_id: int, gateway_data: Dict[str, Any]) -> None:
        """Check if payment gateway exists in database, create if it doesn't.
        
        Args:
            gateway_id: The ID of the payment gateway
            gateway_data: The payment gateway data from the API response
        """
        try:
            from src.models.models import PaymentGateway
            
            existing_gateway = self.db.query(PaymentGateway).filter(PaymentGateway.id == gateway_id).first()

            if existing_gateway is None:
                logger.info(f"Payment gateway ID {gateway_id} not found in database, creating from order data")
                
                # Create payment gateway from the data in the order response
                payment_gateway = PaymentGateway(
                    id=gateway_id,
                    name=gateway_data.get('merchant_account_name', f'Gateway {gateway_id}'),
                    type='Unknown',  # Default type since not provided in order data
                    is_active=True,
                    credentials={},
                    settings={}
                )
                
                try:
                    merged_gateway = self.db.merge(payment_gateway)
                    self.db.commit()
                    logger.info(f"Successfully created payment gateway ID {gateway_id} from order data")
                except Exception as db_error:
                    logger.error(f"Error creating payment gateway ID {gateway_id}: {str(db_error)}")
                    self.db.rollback()
                    # If we can't create the payment gateway, we should skip this payment plan
                    # to avoid foreign key constraint violations
                    raise
            else:
                logger.debug(f"Payment gateway ID {gateway_id} already exists in database")

        except Exception as e:
            logger.error(f"Error checking/creating payment gateway ID {gateway_id}: {str(e)}")
            raise

    def _ensure_credit_card_exists(self, credit_card_id: int) -> None:
        """Check if credit card exists in database, skip if it doesn't.
        
        Note: Credit cards are loaded through the contact loader, so we just log
        if they don't exist rather than trying to load them here.
        """
        try:
            from src.models.models import CreditCard
            existing_card = self.db.query(CreditCard).filter(CreditCard.id == credit_card_id).first()

            if existing_card is None:
                logger.warning(f"Credit card ID {credit_card_id} not found in database. Credit cards should be loaded through the contact loader.")
            else:
                logger.debug(f"Credit card ID {credit_card_id} already exists in database")

        except Exception as e:
            logger.error(f"Error checking credit card ID {credit_card_id}: {str(e)}")

    def _handle_affiliate_references(self, order: Any) -> None:
        """Handle affiliate references - check if they exist and load if needed."""
        # Handle lead affiliate
        if hasattr(order, 'lead_affiliate_id'):
            if order.lead_affiliate_id == 0:
                order.lead_affiliate_id = None
            elif order.lead_affiliate_id and order.lead_affiliate_id > 0:
                self._ensure_affiliate_exists(order.lead_affiliate_id)

        # Handle sales affiliate
        if hasattr(order, 'sales_affiliate_id'):
            if order.sales_affiliate_id == 0:
                order.sales_affiliate_id = None
            elif order.sales_affiliate_id and order.sales_affiliate_id > 0:
                self._ensure_affiliate_exists(order.sales_affiliate_id)

    def _ensure_affiliate_exists(self, affiliate_id: int) -> None:
        """Check if affiliate exists in database, load if it doesn't."""
        try:
            # Check if affiliate exists in database
            existing_affiliate = self.db.query(Affiliate).filter(Affiliate.id == affiliate_id).first()

            if existing_affiliate is None:
                logger.info(f"Affiliate ID {affiliate_id} not found in database, loading from API")
                # Load the affiliate using the affiliate loader
                success = self.affiliate_loader.load_entity_by_id(affiliate_id)
                if success:
                    logger.info(f"Successfully loaded affiliate ID {affiliate_id}")
                else:
                    logger.warning(f"Failed to load affiliate ID {affiliate_id}")
            else:
                logger.debug(f"Affiliate ID {affiliate_id} already exists in database")

        except Exception as e:
            logger.error(f"Error checking/loading affiliate ID {affiliate_id}: {str(e)}")

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to orders."""
        return {'title': getattr(item, 'title', None), 'status': getattr(item, 'status', None), 'order_date': getattr(item, 'order_date', None), 'total': getattr(item, 'total', None),
                'contact_id': getattr(item, 'contact_id', None)}
