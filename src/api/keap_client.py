import logging
from typing import List, Optional

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
    transform_contact,
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
    transform_affiliate_payment
)

logger = logging.getLogger(__name__)


class KeapClient(KeapBaseClient):
    def get_contacts(self, limit: int = 50, offset: int = 0) -> List[Contact]:
        """Get a list of contacts."""
        params = {'limit': limit, 'offset': offset}
        response = self.get('contacts', params)
        logger.info(f"Raw contacts API response: {response}")
        return transform_list_response(response, transform_contact)

    def get_contact(self, contact_id: int) -> Contact:
        """Get a single contact by ID with all related data."""
        response = self.get(f'contacts/{contact_id}')
        return transform_contact_with_related(response)

    def get_tags(self, limit: int = 50, offset: int = 0) -> List[Tag]:
        """Get a list of tags."""
        params = {'limit': limit, 'offset': offset}
        response = self.get('tags', params)
        return transform_list_response(response, transform_tag)

    def get_custom_fields(self, limit: int = 50, offset: int = 0) -> List[CustomField]:
        """Get a list of custom fields."""
        params = {'limit': limit, 'offset': offset}
        response = self.get('customFields', params)
        return transform_list_response(response, transform_custom_field)

    def get_opportunities(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[
        Opportunity]:
        """Get a list of opportunities."""
        params = {'limit': limit, 'offset': offset}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('opportunities', params)
        return transform_list_response(response, transform_opportunity)

    def get_products(self, limit: int = 50, offset: int = 0, subscription_only: Optional[bool] = None) -> List[Product]:
        """Get a list of products, optionally filtered by subscription_only flag."""
        params = {'limit': limit, 'offset': offset}
        if subscription_only is not None:
            params['subscription_only'] = subscription_only
        response = self.get('products', params)
        return transform_list_response(response, transform_product)

    def get_product(self, product_id: int) -> Product:
        """Get a single product by ID."""
        response = self.get(f'products/{product_id}')
        return transform_product(response)

    def get_orders(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[Order]:
        """Get a list of orders with their items."""
        params = {'limit': limit, 'offset': offset}
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

    def get_tasks(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[Task]:
        """Get a list of tasks."""
        params = {'limit': limit, 'offset': offset}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('tasks', params)
        return transform_list_response(response, transform_task)

    def get_task(self, task_id: int) -> Task:
        """Get a single task by ID."""
        response = self.get(f'tasks/{task_id}')
        return transform_task(response)

    def get_notes(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[Note]:
        """Get a list of notes."""
        params = {'limit': limit, 'offset': offset}
        if contact_id:
            params['contact_id'] = contact_id
        response = self.get('notes', params)
        return transform_list_response(response, transform_note)

    def get_note(self, note_id: int) -> Note:
        """Get a single note by ID."""
        response = self.get(f'notes/{note_id}')
        return transform_note(response)

    def get_campaigns(self, limit: int = 50, offset: int = 0) -> List[Campaign]:
        """Get a list of campaigns."""
        params = {'limit': limit, 'offset': offset}
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

    def get_subscriptions(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0) -> List[
        Subscription]:
        """Get a list of subscriptions."""
        params = {'limit': limit, 'offset': offset}
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
