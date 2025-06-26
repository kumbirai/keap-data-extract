"""
Specialized loader for affiliates.

Affiliates have complex relationships including payments, clawbacks,
commissions, and programs that need special handling.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class AffiliateLoader(BaseEntityLoader):
    """Specialized loader for affiliates with complex relationship handling.
    
    Affiliates are unique because:
    1. They don't support pagination (loaded all at once)
    2. They have payments and clawbacks that need to be fetched separately
    3. They have complex relationships with contacts and other affiliates
    4. They need special handling for commissions, programs, and redirects
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "affiliates", "get_affiliates", "get_affiliate")

    @property
    def supports_pagination(self) -> bool:
        return True

    def _process_entity(self, affiliate: Any) -> None:
        """Process affiliate-specific relationships.
        
        This method handles the complex relationships that were duplicated
        in the original load_affiliate_by_id function.
        """
        # Get affiliate payments
        try:
            payments, _ = self.client.get_affiliate_payments(affiliate.id)
            logger.info(f"Retrieved {len(payments)} payments for affiliate ID: {affiliate.id}")
        except Exception as e:
            logger.warning(f"Error getting payments for affiliate {affiliate.id}: {str(e)}")
            payments = []

        # Get affiliate clawbacks
        try:
            clawbacks, _ = self.client.get_affiliate_clawbacks(affiliate.id)
            logger.info(f"Retrieved {len(clawbacks)} clawbacks for affiliate ID: {affiliate.id}")
        except Exception as e:
            logger.warning(f"Error getting clawbacks for affiliate {affiliate.id}: {str(e)}")
            clawbacks = []

        # Clear and set relationships
        if hasattr(affiliate, 'payments'):
            affiliate.payments = []
            for payment in payments:
                affiliate.payments.append(payment)

        if hasattr(affiliate, 'clawbacks'):
            affiliate.clawbacks = []
            for clawback in clawbacks:
                affiliate.clawbacks.append(clawback)

        # Handle other relationships
        if hasattr(affiliate, 'contact'):
            affiliate.contact = affiliate.contact

        if hasattr(affiliate, 'parent'):
            affiliate.parent = affiliate.parent

        if hasattr(affiliate, 'children'):
            affiliate.children = affiliate.children

        if hasattr(affiliate, 'commissions'):
            affiliate.commissions = affiliate.commissions

        if hasattr(affiliate, 'programs'):
            affiliate.programs = affiliate.programs

        if hasattr(affiliate, 'redirects'):
            affiliate.redirects = affiliate.redirects

        if hasattr(affiliate, 'summary'):
            affiliate.summary = affiliate.summary

        # Handle order relationships
        if hasattr(affiliate, 'lead_orders'):
            affiliate.lead_orders = affiliate.lead_orders

        if hasattr(affiliate, 'sales_orders'):
            affiliate.sales_orders = affiliate.sales_orders

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to affiliates."""
        return {'name': getattr(item, 'name', None), 'email': getattr(item, 'email', None), 'company': getattr(item, 'company', None), 'status': getattr(item, 'status', None),
                'contact_id': getattr(item, 'contact_id', None)}
