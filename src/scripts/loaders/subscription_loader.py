"""
Specialized loader for subscriptions.

Subscriptions are unique because they don't follow the standard pattern
of having both get_subscriptions and get_subscription methods. According
to the Keap API documentation, subscriptions should be modeled from the
get_subscriptions call only.
"""

import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.models import Subscription
from .base_loader import EntityLoader

logger = logging.getLogger(__name__)


class SubscriptionLoader(EntityLoader):
    """Specialized loader for subscriptions.
    
    Subscriptions are unique because:
    1. They don't have a get_subscription method for individual retrieval
    2. They should be modeled from the get_subscriptions call only
    3. They support pagination and the 'since' parameter
    4. They have relationships with contacts, products, and subscription plans
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager)

    @property
    def entity_type(self) -> str:
        return "subscriptions"

    @property
    def supports_pagination(self) -> bool:
        return True

    @property
    def supports_since_parameter(self) -> bool:
        return False

    def get_entities(self, limit: int = None, offset: int = None, **kwargs) -> Tuple[List, Dict]:
        """Get subscriptions from the API.
        
        Since subscriptions don't have a get_subscription method, we only
        use get_subscriptions and process all subscriptions from that call.
        """
        if limit is None:
            limit = 50
        if offset is None:
            offset = 0

        return self.client.get_subscriptions(limit=limit, offset=offset, **kwargs)

    def load_entity_by_id(self, entity_id: int) -> bool:
        """Load a single subscription by ID.
        
        Since there's no get_subscription method, this method is not used
        for subscriptions. All subscription data comes from get_subscriptions.
        """
        logger.warning(f"load_entity_by_id called for subscription {entity_id}, but subscriptions don't support individual retrieval")
        return False

    def load_all(self, batch_size: int = 50, update: bool = False) -> Any:
        """Load all subscriptions.
        
        This method overrides the base implementation to handle the fact that
        subscriptions don't have individual retrieval methods.
        """
        try:
            query_params = self.get_query_params(update)
            offset = self.get_initial_offset(update)

            logger.info(f"Starting {self.entity_type} load with params: {query_params}")

            return self._load_with_pagination(batch_size, offset, query_params)

        except Exception as e:
            logger.error(f"Error in load_{self.entity_type}: {str(e)}")
            self._log_operation_error(e)
            raise

    def _load_with_pagination(self, batch_size: int, offset: int, query_params: Dict) -> Any:
        """Load subscriptions using pagination.
        
        This method processes all subscriptions from each get_subscriptions call
        since there's no individual subscription retrieval method.
        """
        from .base_loader import LoadResult

        total_records = 0
        success_count = 0
        failed_count = 0
        api_offset = offset  # Track API pagination offset separately

        while True:
            subscriptions, pagination = self.get_entities(limit=batch_size, offset=api_offset, **query_params)

            if not subscriptions:
                logger.info(f"No more {self.entity_type} to load")
                self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset, completed=True)
                break

            # Process all subscriptions from this batch
            for subscription in subscriptions:
                total_records += 1
                try:
                    logger.info(f"Processing {self.entity_type} ID: {subscription.id}")

                    # Since we already have the full subscription data from get_subscriptions,
                    # we can directly merge it into the database
                    self._process_subscription(subscription)

                    success_count += 1
                    logger.info(f"Successfully processed {self.entity_type} ID: {subscription.id}")

                except Exception as e:
                    failed_count += 1
                    self._log_item_error(subscription, e)
                    continue

            # Update checkpoint with total records processed and current API offset
            self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset)

            # Check for next page
            if not pagination.get('next'):
                logger.info(f"Reached end of {self.entity_type}")
                self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset, completed=True)
                break

            next_offset = self.client._parse_next_url(pagination.get('next'))
            if next_offset is None:
                logger.info("No more pages to load")
                self.checkpoint_manager.save_checkpoint(self.entity_type, total_records, api_offset, completed=True)
                break

            api_offset = next_offset

        logger.info(f"Completed loading {self.entity_type}. Total: {total_records}, Success: {success_count}, Failed: {failed_count}")
        return LoadResult(total_records, success_count, failed_count)

    def _process_subscription(self, subscription: Subscription) -> None:
        """Process a single subscription.
        
        Since we get full subscription data from get_subscriptions, we can
        directly merge it into the database without additional API calls.
        """
        try:
            # Use merge instead of add to handle both inserts and updates
            self.db.merge(subscription)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing subscription {subscription.id}: {e}")
            raise

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to subscriptions."""
        return {'subscription_id': getattr(item, 'id', None), 'contact_id': getattr(item, 'contact_id', None), 'product_id': getattr(item, 'product_id', None), 'status': getattr(item, 'status', None)}
