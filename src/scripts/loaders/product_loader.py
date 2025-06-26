"""
Specialized loader for products.

Products have subscription plans embedded in their API response and
require special handling for product options and relationships.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.models import SubscriptionPlan
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class ProductLoader(BaseEntityLoader):
    """Specialized loader for products with subscription plan handling.
    
    Products are unique because:
    1. They have subscription plans embedded in the API response
    2. They need special handling for product options
    3. They require careful relationship management to avoid conflicts
    4. They don't support the 'since' parameter for updates
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "products", "get_products", "get_product")

    @property
    def supports_since_parameter(self) -> bool:
        return False  # Products API doesn't support 'since' parameter

    def _check_existing_subscription_plan(self, plan_id: int) -> SubscriptionPlan:
        """Check if a subscription plan already exists in the database.
        
        Args:
            plan_id: The subscription plan ID to check
            
        Returns:
            The existing subscription plan if found, None otherwise
        """
        try:
            return self.db.get(SubscriptionPlan, plan_id)
        except Exception as e:
            logger.debug(f"Error checking existing subscription plan {plan_id}: {str(e)}")
            return None

    def _process_subscription_plan(self, subscription_plan: SubscriptionPlan, product_id: int) -> SubscriptionPlan:
        """Process a single subscription plan with proper error handling.
        
        Args:
            subscription_plan: The subscription plan to process
            product_id: The product ID this plan belongs to
            
        Returns:
            The merged subscription plan
            
        Raises:
            Exception: If processing fails
        """
        # Check if the plan already exists
        existing_plan = self._check_existing_subscription_plan(subscription_plan.id)

        if existing_plan:
            logger.debug(f"Subscription plan {subscription_plan.id} already exists, updating...")
            # Update existing plan with new data
            for attr, value in subscription_plan.__dict__.items():
                if not attr.startswith('_') and hasattr(existing_plan, attr):
                    setattr(existing_plan, attr, value)
            existing_plan.product_id = product_id
            return existing_plan
        else:
            logger.debug(f"Creating new subscription plan {subscription_plan.id}")
            # Ensure the subscription plan has the correct product_id
            subscription_plan.product_id = product_id

            # Process the new subscription plan
            self.db.flush()  # Flush any pending changes
            merged_plan = self.db.merge(subscription_plan)
            self.db.flush()  # Flush the merge operation

            return merged_plan

    def _process_entity(self, product: Any) -> None:
        """Process product-specific relationships.
        
        This method handles the subscription plans that were duplicated
        in the original load_product_by_id function.
        """
        # Store subscription plans for later handling
        product_subscription_plans = product.subscription_plans if hasattr(product, 'subscription_plans') else []

        # Clear subscription plans from the product to avoid relationship conflicts
        if hasattr(product, 'subscription_plans'):
            product.subscription_plans = []

        # Handle other relationships if needed
        if hasattr(product, 'options'):
            product.options = product.options

        if hasattr(product, 'order_items'):
            product.order_items = product.order_items

        if hasattr(product, 'direct_orders'):
            product.direct_orders = product.direct_orders

        if hasattr(product, 'subscriptions'):
            product.subscriptions = product.subscriptions

        # Handle subscription plans in separate transactions to avoid duplicate key violations
        if product_subscription_plans:
            # Deduplicate subscription plans by ID to prevent processing duplicates
            seen_ids = set()
            unique_plans = []
            for plan in product_subscription_plans:
                if plan.id not in seen_ids:
                    seen_ids.add(plan.id)
                    unique_plans.append(plan)

            logger.info(f"Processing {len(unique_plans)} unique subscription plans for product {product.id} (from {len(product_subscription_plans)} total)")

            successful_plans = 0
            for subscription_plan in unique_plans:
                try:
                    # Process the subscription plan using the helper method
                    merged_plan = self._process_subscription_plan(subscription_plan, product.id)

                    # Add the merged plan to the product's subscription_plans list
                    product.subscription_plans.append(merged_plan)
                    successful_plans += 1

                    logger.debug(f"Successfully processed subscription plan {subscription_plan.id} for product {product.id}")

                except Exception as e:
                    logger.warning(f"Error processing subscription plan {subscription_plan.id} for product {product.id}: {str(e)}")
                    # Rollback this specific subscription plan operation
                    try:
                        self.db.rollback()
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback for subscription plan {subscription_plan.id}: {str(rollback_error)}")
                    continue

            logger.info(f"Successfully processed {successful_plans}/{len(unique_plans)} subscription plans for product {product.id}")

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to products."""
        return {'product_name': getattr(item, 'product_name', None), 'sku': getattr(item, 'sku', None), 'active': getattr(item, 'active', None),
                'subscription_only': getattr(item, 'subscription_only', None)}
