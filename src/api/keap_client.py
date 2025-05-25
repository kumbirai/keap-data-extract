import logging
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urlparse, parse_qs

from .base_client import KeapBaseClient
from .exceptions import KeapNotFoundError
from ..models.models import (
    Contact,
    Tag,
    CustomField,
    Opportunity,
    Product,
    Order,
    OrderItem,
    Task,
    Note,
    Campaign,
    CampaignSequence,
    Subscription,
    AccountProfile,
    Affiliate,
    AffiliateCommission,
    AffiliateProgram,
    AffiliateRedirect,
    AffiliateSummary,
    AffiliateClawback,
    AffiliatePayment
)
from ..utils.transformers import (
    transform_contact_with_related,
    transform_tag,
    transform_custom_field,
    transform_opportunity,
    transform_product,
    transform_order_item,
    transform_task,
    transform_note,
    transform_campaign,
    transform_campaign_sequence,
    transform_subscription,
    transform_list_response,
    transform_order_with_items,
    transform_account_profile,
    transform_affiliate,
    transform_affiliate_commission,
    transform_affiliate_program,
    transform_affiliate_redirect,
    transform_affiliate_summary,
    transform_affiliate_clawback,
    transform_affiliate_payment,
    transform_applied_tag
)

logger = logging.getLogger(__name__)


class KeapClient(KeapBaseClient):
    def _parse_next_url(self, next_url: Optional[str]) -> Optional[int]:
        """Parse the offset from a next URL.
        
        Args:
            next_url: The next URL from the API response
            
        Returns:
            The offset value from the URL, or None if not found
        """
        if not next_url:
            return None

        try:
            parsed_url = urlparse(next_url)
            query_params = parse_qs(parsed_url.query)
            offset = query_params.get('offset', [None])[0]
            return int(offset) if offset is not None else None
        except (ValueError, KeyError, IndexError) as e:
            logger.warning(f"Failed to parse next URL: {next_url}. Error: {str(e)}")
            return None

    def get_contacts(self, limit: int = 50, offset: int = 0, db_session=None) -> Tuple[List[Contact], Dict[str, Any]]:
        """Get a list of contacts.
        
        Args:
            limit: Maximum number of contacts to return
            offset: Offset for pagination
            db_session: Optional database session for processing related data
            
        Returns:
            Tuple containing:
            - List of Contact objects
            - Dictionary containing pagination metadata
        """
        try:
            params = {'limit': limit, 'offset': offset, 'order': 'id'}
            response = self.get('contacts', params)
            logger.debug(f"Raw contacts API response: {response}")

            if not response or 'contacts' not in response:
                logger.warning(f"Invalid response format from contacts API: {response}")
                return [], {'next': None, 'count': 0, 'total': 0}

            # Transform each contact with its related data
            items = []
            for item in response.get('contacts', []):
                try:
                    transformed_contact = transform_contact_with_related(item, db_session)
                    items.append(transformed_contact)
                except Exception as e:
                    logger.error(f"Error transforming contact: {str(e)}")
                    logger.debug(f"Problematic contact data: {item}")
                    continue

            # Extract pagination metadata
            pagination = {
                'next': response.get('next'),
                'count': response.get('count'),
                'total': response.get('total')
            }

            logger.info(f"Successfully retrieved {len(items)} contacts")
            return items, pagination

        except Exception as e:
            logger.error(f"Error fetching contacts: {str(e)}")
            raise

    def get_contact(self, contact_id: int) -> Contact:
        """Get a single contact by ID with all related data."""
        response = self.get(f'contacts/{contact_id}')
        logger.debug(f"Raw contact API response: {response}")
        return transform_contact_with_related(response)

    def get_tags(self, limit: int = 50, offset: int = 0) -> Tuple[List[Tag], Dict[str, Any]]:
        """Get a list of tags.
        
        Args:
            limit: Maximum number of tags to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of Tag objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        response = self.get('tags', params)
        logger.debug(f"Raw tags API response: {response}")
        return transform_list_response(response, transform_tag)

    def get_custom_fields(self, limit: int = 50, offset: int = 0) -> Tuple[List[CustomField], Dict[str, Any]]:
        """Get a list of custom fields.
        
        Args:
            limit: Maximum number of custom fields to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of CustomField objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        response = self.get('customFields', params)
        return transform_list_response(response, transform_custom_field)

    def get_opportunities(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> Tuple[
        List[Opportunity], Dict[str, Any]]:
        """Get a list of opportunities.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of opportunities to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of Opportunity objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('opportunities', params)
        return transform_list_response(response, transform_opportunity)

    def get_products(self, limit: int = 50, offset: int = 0, subscription_only: Optional[bool] = None) -> Tuple[
        List[Product], Dict[str, Any]]:
        """Get a list of products.
        
        Args:
            limit: Maximum number of products to return
            offset: Offset for pagination
            subscription_only: Optional flag to filter subscription products
            
        Returns:
            Tuple containing:
            - List of Product objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        if subscription_only is not None:
            params['subscription_only'] = subscription_only
        response = self.get('products', params)
        return transform_list_response(response, transform_product)

    def get_product(self, product_id: int) -> Product:
        """Get a single product by ID."""
        response = self.get(f'products/{product_id}')
        return transform_product(response)

    def get_orders(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> Tuple[
        List[Order], Dict[str, Any]]:
        """Get a list of orders.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of orders to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of Order objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('orders', params)
        return transform_list_response(response, transform_order_with_items)

    def get_order(self, order_id: int) -> Order:
        """Get a single order by ID with its items."""
        response = self.get(f'orders/{order_id}')
        return transform_order_with_items(response)

    def get_order_items(self, order_id: int) -> List[OrderItem]:
        """Get items for an order."""
        try:
            response = self.get(f'orders/{order_id}/items')
            return transform_list_response(response, transform_order_item)
        except KeapNotFoundError:
            logger.warning(f"No items found for order {order_id}")
            return []

    def get_tasks(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> Tuple[
        List[Task], Dict[str, Any]]:
        """Get a list of tasks.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of Task objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('tasks', params)
        return transform_list_response(response, transform_task)

    def get_task(self, task_id: int) -> Task:
        """Get a single task by ID."""
        response = self.get(f'tasks/{task_id}')
        return transform_task(response)

    def get_notes(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> Tuple[
        List[Note], Dict[str, Any]]:
        """Get a list of notes.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of notes to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of Note objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('notes', params)
        return transform_list_response(response, transform_note)

    def get_note(self, note_id: int) -> Note:
        """Get a single note by ID."""
        response = self.get(f'notes/{note_id}')
        return transform_note(response)

    def get_campaigns(self, limit: int = 50, offset: int = 0) -> Tuple[List[Campaign], Dict[str, Any]]:
        """Get a list of campaigns.
        
        Args:
            limit: Maximum number of campaigns to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of Campaign objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        response = self.get('campaigns', params)
        return transform_list_response(response, transform_campaign)

    def get_campaign(self, campaign_id: int) -> Campaign:
        """Get a single campaign by ID."""
        response = self.get(f'campaigns/{campaign_id}')
        return transform_campaign(response)

    def get_campaign_sequences(self, campaign_id: int) -> List[CampaignSequence]:
        """Get sequences for a campaign."""
        try:
            response = self.get(f'campaigns/{campaign_id}/sequences')
            return transform_list_response(response, transform_campaign_sequence)
        except KeapNotFoundError:
            logger.warning(f"No sequences found for campaign {campaign_id}")
            return []

    def get_subscriptions(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> Tuple[
        List[Subscription], Dict[str, Any]]:
        """Get a list of subscriptions.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of subscriptions to return
            offset: Offset for pagination
            
        Returns:
            Tuple containing:
            - List of Subscription objects
            - Dictionary containing pagination metadata
        """
        params = {'limit': limit, 'offset': offset, 'order': 'id'}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('subscriptions', params)
        return transform_list_response(response, transform_subscription)

    def get_subscription(self, subscription_id: int) -> Subscription:
        """Get a single subscription by ID."""
        response = self.get(f'subscriptions/{subscription_id}')
        return transform_subscription(response)

    def get_account_profile(self) -> AccountProfile:
        """Get the account profile."""
        response = self.get('account/profile')
        return transform_account_profile(response)

    def get_affiliates(self, limit: int = 50, offset: int = 0) -> List[Affiliate]:
        """Get a list of affiliates."""
        params = {'limit': limit, 'offset': offset}
        response = self.get('affiliates', params)
        return transform_list_response(response, transform_affiliate)

    def get_affiliate(self, affiliate_id: int) -> Affiliate:
        """Get a single affiliate by ID."""
        response = self.get(f'affiliates/{affiliate_id}')
        return transform_affiliate(response)

    def get_affiliate_commissions(self, affiliate_id: int, limit: int = 50, offset: int = 0) -> List[
        AffiliateCommission]:
        """Get commissions for an affiliate."""
        params = {'limit': limit, 'offset': offset}
        response = self.get(f'affiliates/{affiliate_id}/commissions', params)
        return transform_list_response(response, transform_affiliate_commission)

    def get_affiliate_programs(self, affiliate_id: int, limit: int = 50, offset: int = 0) -> List[AffiliateProgram]:
        """Get programs for an affiliate."""
        params = {'limit': limit, 'offset': offset}
        response = self.get(f'affiliates/{affiliate_id}/programs', params)
        return transform_list_response(response, transform_affiliate_program)

    def get_affiliate_redirects(self, affiliate_id: int, limit: int = 50, offset: int = 0) -> List[AffiliateRedirect]:
        """Get redirects for an affiliate."""
        params = {'limit': limit, 'offset': offset}
        response = self.get(f'affiliates/{affiliate_id}/redirects', params)
        return transform_list_response(response, transform_affiliate_redirect)

    def get_affiliate_summary(self, affiliate_id: int) -> AffiliateSummary:
        """Get summary for an affiliate."""
        response = self.get(f'affiliates/{affiliate_id}/summary')
        return transform_affiliate_summary(response)

    def get_affiliate_clawbacks(self, affiliate_id: int, limit: int = 50, offset: int = 0) -> List[AffiliateClawback]:
        """Get clawbacks for an affiliate."""
        params = {'limit': limit, 'offset': offset}
        response = self.get(f'affiliates/{affiliate_id}/clawbacks', params)
        return transform_list_response(response, transform_affiliate_clawback)

    def get_affiliate_payments(self, affiliate_id: int, limit: int = 50, offset: int = 0) -> List[AffiliatePayment]:
        """Get payments for an affiliate."""
        params = {'limit': limit, 'offset': offset}
        response = self.get(f'affiliates/{affiliate_id}/payments', params)
        return transform_list_response(response, transform_affiliate_payment)

    def get_contact_tags(self, contact_id: int) -> List[Tag]:
        """Get a list of tags applied to a specific contact.
        
        Args:
            contact_id: The ID of the contact to get tags for
            
        Returns:
            List of Tag objects
        """
        response = self.get(f'contacts/{contact_id}/tags')
        # Use a different transformer for the applied tags response
        return [transform_applied_tag(tag_data) for tag_data in response.get('tags', [])]
