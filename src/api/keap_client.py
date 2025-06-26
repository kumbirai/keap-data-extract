import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from src.transformers.transformers import (transform_account_profile, transform_affiliate, transform_affiliate_clawback, transform_affiliate_commission, transform_affiliate_payment,
                                           transform_affiliate_program, transform_affiliate_redirect, transform_affiliate_summary, transform_applied_tag, transform_campaign,
                                           transform_contact_with_related, transform_credit_card, transform_custom_field, transform_list_response, transform_note, transform_opportunity,
                                           transform_order_item, transform_order_payment, transform_order_transaction, transform_order_with_items, transform_payment_gateway, transform_payment_plan,
                                           transform_product, transform_subscription, transform_tag, transform_task)
from .base_client import KeapBaseClient
from .exceptions import KeapNotFoundError
from ..models.models import (AccountProfile, Affiliate, AffiliateClawback, AffiliateCommission, AffiliatePayment, AffiliateProgram, AffiliateRedirect, AffiliateSummary, Campaign, Contact, CustomField,
                             Note, Opportunity, Order, OrderItem, OrderPayment, OrderTransaction, Product, Subscription, Tag, Task)

logger = logging.getLogger(__name__)


class KeapClient(KeapBaseClient):
    # Core/Utility Methods
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

    def _prepare_params(self, limit: int = 50, offset: int = 0, order: str = None, **additional_params) -> Dict[str, Any]:
        """Prepare parameters for API requests.
        
        Args:
            limit: Maximum number of items to return
            offset: Offset for pagination
            order: Field to order by (default varies by endpoint)
            additional_params: Additional parameters to include
            
        Returns:
            Dictionary of parameters for the API request
        """
        # Start with additional_params as base
        params = additional_params.copy()

        # Override with explicit parameters if they are not None
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset

        # Only include order parameter if it's explicitly provided
        # This is because some endpoints don't support ordering
        # and others have specific default ordering
        if order is not None:
            params['order'] = order

        # Filter out None values
        params = {k: v for k, v in params.items() if v is not None}

        return params

    # Contact Related Methods
    def get_contacts(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List[Contact], Dict[str, Any]]:
        """Get a list of contacts.
        
        Args:
            limit: Maximum number of contacts to return
            offset: Offset for pagination
            since: Optional timestamp to get contacts modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Contact objects
            - Dictionary containing pagination metadata
        """
        try:
            # Set default order to 'id' for contacts
            if 'order' not in additional_params:
                additional_params['order'] = 'id'

            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
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
            pagination = {'next': response.get('next'), 'count': response.get('count'), 'total': response.get('total')}

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

    def get_contact_model(self) -> Dict[str, Any]:
        """Get the contact model definition from the API.
        
        Returns:
            Dictionary containing the contact model definition
        """
        response = self.get('contacts/model')
        return response

    def get_contact_tags(self, contact_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[Tag], Dict[str, Any]]:
        """Get a list of tags applied to a specific contact.
        
        Args:
            contact_id: The ID of the contact to get tags for
            limit: Maximum number of tags to return
            offset: Offset for pagination
            since: Optional timestamp to get tags modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Tag objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'contacts/{contact_id}/tags', params)
        # Use a different transformer for the applied tags response
        items = [transform_applied_tag(tag_data) for tag_data in response.get('tags', [])]
        pagination = {'next': None, 'count': len(items), 'total': len(items)}
        return items, pagination

    def get_contact_credit_cards(self, contact_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Get credit cards for a specific contact.
        
        Args:
            contact_id: The ID of the contact
            limit: Maximum number of credit cards to return
            offset: Offset for pagination
            since: Optional timestamp to get credit cards modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of credit card dictionaries
            - Dictionary containing pagination metadata
        """
        try:
            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
            endpoint = f"contacts/{contact_id}/creditCards"
            response = self._make_request('GET', endpoint, params=params)

            # The API returns a list directly, not wrapped in an object
            if isinstance(response, list):
                items = response
            # If it's wrapped in an object, try to get the creditCards field
            elif isinstance(response, dict):
                items = response.get('creditCards', [])
            else:
                logger.warning(f"Unexpected response format for credit cards: {response}")
                items = []

            # Transform each credit card item
            transformed_items = []
            for item in items:
                try:
                    # Add contact_id to each credit card item
                    if isinstance(item, dict):
                        item['contact_id'] = contact_id
                        transformed_items.append(item)
                except Exception as e:
                    logger.error(f"Error transforming credit card item: {str(e)}")
                    continue

            pagination = {'next': None, 'count': len(transformed_items), 'total': len(transformed_items)}
            return transformed_items, pagination

        except Exception as e:
            logger.error(f"Error fetching credit cards for contact {contact_id}: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    # Custom Fields Methods
    def get_custom_fields(self, entity_type: str = 'contacts', **additional_params) -> Tuple[List[CustomField], Dict[str, Any]]:
        """Get all custom fields from the specified entity model.
        
        This method retrieves all custom fields defined in the specified entity model.
        Custom fields are not paginated as they are all returned at once from the model endpoint.
        
        Args:
            entity_type: The type of entity to get custom fields for. Must be one of:
                - 'contacts' (default)
                - 'companies'
                - 'opportunities'
                - 'orders'
                - 'subscriptions'
            additional_params: Additional parameters to pass to the API calls
        
        Returns:
            Tuple containing:
            - List of CustomField objects
            - Dictionary containing empty pagination metadata (for consistency with other methods)
            
        Raises:
            ValueError: If an invalid entity_type is provided
        """
        valid_entity_types = ['contacts', 'companies', 'opportunities', 'orders', 'subscriptions']
        if entity_type not in valid_entity_types:
            raise ValueError(f"Invalid entity_type. Must be one of: {', '.join(valid_entity_types)}")

        # Get the model for the specified entity type
        model = self.get(f'{entity_type}/model')

        # Extract custom fields from the model
        custom_fields = []
        custom_fields_data = model.get('custom_fields', [])

        # Handle the new API structure where custom_fields is a list
        if isinstance(custom_fields_data, list):
            # New API structure - custom_fields is a list of field objects
            for field_def in custom_fields_data:
                try:
                    # Use field_name as the field name, fallback to label if not available
                    field_name = field_def.get('field_name') or field_def.get('label', f"Field_{field_def.get('id')}")
                    custom_field = transform_custom_field(field_name, field_def)
                    custom_fields.append(custom_field)
                except Exception as e:
                    logger.error(f"Error transforming custom field for {entity_type}: {str(e)}")
                    continue
        elif isinstance(custom_fields_data, dict):
            # Legacy structure - custom_fields is a dictionary
            for field_name, field_def in custom_fields_data.items():
                try:
                    custom_field = transform_custom_field(field_name, field_def)
                    custom_fields.append(custom_field)
                except Exception as e:
                    logger.error(f"Error transforming custom field {field_name} for {entity_type}: {str(e)}")
                    continue
        else:
            logger.warning(f"Unexpected custom_fields format for {entity_type}: {type(custom_fields_data)}")

        # Create empty pagination metadata for consistency
        pagination = {'next': None, 'count': len(custom_fields), 'total': len(custom_fields)}

        logger.info(f"Retrieved {len(custom_fields)} custom fields from {entity_type} model")
        return custom_fields, pagination

    def get_all_custom_fields(self, **additional_params) -> Dict[str, List[CustomField]]:
        """Get all custom fields from all entity models.
        
        This method retrieves custom fields from all supported entity types:
        - contacts
        - companies
        - opportunities
        - orders
        - subscriptions
        
        Args:
            additional_params: Additional parameters to pass to the API calls
        
        Returns:
            Dictionary mapping entity types to their list of CustomField objects
        """
        all_custom_fields = {}
        entity_types = ['contacts', 'companies', 'opportunities', 'orders', 'subscriptions']

        for entity_type in entity_types:
            try:
                custom_fields, _ = self.get_custom_fields(entity_type, **additional_params)
                all_custom_fields[entity_type] = custom_fields
            except Exception as e:
                logger.error(f"Error retrieving custom fields for {entity_type}: {str(e)}")
                all_custom_fields[entity_type] = []
                continue

        return all_custom_fields

    # Opportunity Related Methods
    def get_opportunities(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[
        List[Opportunity], Dict[str, Any]]:
        """Get a list of opportunities.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of opportunities to return
            offset: Offset for pagination
            since: Optional timestamp to get opportunities modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Opportunity objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
        response = self.get('opportunities', params)
        return transform_list_response(response, transform_opportunity)

    def get_opportunity(self, opportunity_id: int) -> Opportunity:
        """Get a single opportunity by ID.
        
        Args:
            opportunity_id: The ID of the opportunity to retrieve
            
        Returns:
            Opportunity object
        """
        try:
            response = self.get(f'opportunities/{opportunity_id}')
            return transform_opportunity(response)
        except Exception as e:
            logger.error(f"Error fetching opportunity {opportunity_id}: {str(e)}")
            raise

    # Product Related Methods
    def get_products(self, limit: int = 50, offset: int = 0, subscription_only: Optional[bool] = None, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[
        List[Product], Dict[str, Any]]:
        """Get a list of products.
        
        Args:
            limit: Maximum number of products to return
            offset: Offset for pagination
            subscription_only: Optional flag to filter subscription products
            since: Optional timestamp to get products modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Product objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, subscription_only=subscription_only, **additional_params)
        response = self.get('products', params)
        return transform_list_response(response, transform_product)

    def get_product(self, product_id: int) -> Product:
        """Get a single product by ID."""
        response = self.get(f'products/{product_id}')
        return transform_product(response)

    # Order Related Methods
    def get_orders(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List[Order], Dict[str, Any]]:
        """Get a list of orders.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of orders to return
            offset: Offset for pagination
            since: Optional timestamp to get orders modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Order objects
            - Dictionary containing pagination metadata
        """
        # Set default order to 'date_created' for orders
        if 'order' not in additional_params:
            additional_params['order'] = 'date_created'

        params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
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

    def get_order_payments(self, order_id: int) -> List[OrderPayment]:
        """Get payments for a specific order.
        
        Args:
            order_id: The ID of the order to get payments for
            
        Returns:
            List of OrderPayment objects
        """
        try:
            response = self._make_request('GET', f'orders/{order_id}/payments')
            if not response:
                logger.warning(f"No payments found for order {order_id}")
                return []
            
            # Handle different response formats
            if isinstance(response, list):
                # Direct list of payments
                payments = response
            elif isinstance(response, dict):
                # Dictionary with payments in a key
                payments = response.get('payments', [])
                if not payments:
                    # Try other possible keys
                    payments = response.get('data', [])
                    if not payments:
                        # If no payments found, return empty list
                        logger.debug(f"No payments found in response for order {order_id}: {response}")
                        return []
            else:
                logger.warning(f"Unexpected response format for order payments {order_id}: {type(response)}")
                return []
            
            return [transform_order_payment(payment) for payment in payments]
        except Exception as e:
            logger.error(f"Error getting payments for order {order_id}: {str(e)}")
            return []

    def get_order_transactions(self, order_id: int) -> List[OrderTransaction]:
        """Get transactions for a specific order.
        
        Args:
            order_id: The ID of the order to get transactions for
            
        Returns:
            List of OrderTransaction objects
        """
        try:
            response = self._make_request('GET', f'orders/{order_id}/transactions')
            if not response:
                logger.warning(f"No transactions found for order {order_id}")
                return []
            
            # Handle different response formats
            if isinstance(response, list):
                # Direct list of transactions
                transactions = response
            elif isinstance(response, dict):
                # Dictionary with transactions in a key
                transactions = response.get('transactions', [])
                if not transactions:
                    # Try other possible keys
                    transactions = response.get('data', [])
                    if not transactions:
                        # If no transactions found, return empty list
                        logger.debug(f"No transactions found in response for order {order_id}: {response}")
                        return []
            else:
                logger.warning(f"Unexpected response format for order transactions {order_id}: {type(response)}")
                return []
            
            return [transform_order_transaction(transaction) for transaction in transactions]
        except Exception as e:
            logger.error(f"Error getting transactions for order {order_id}: {str(e)}")
            return []

    def get_order_payment_plan(self, order_id: int) -> Any:
        """Get payment plan for a specific order.
        
        Args:
            order_id: The ID of the order to get payment plan for
            
        Returns:
            PaymentPlan object or None if not found
        """
        try:
            response = self._make_request('GET', f'orders/{order_id}/paymentPlan')
            if not response:
                logger.debug(f"No payment plan found for order {order_id}")
                return None
            return transform_payment_plan(response, order_id)
        except Exception as e:
            logger.warning(f"Error getting payment plan for order {order_id}: {str(e)}")
            return None

    def get_payment_gateways(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[Any], Dict[str, Any]]:
        """Get a list of payment gateways.
        
        Args:
            limit: Maximum number of payment gateways to return
            offset: Offset for pagination
            since: Optional timestamp to get payment gateways modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of PaymentGateway objects
            - Dictionary containing pagination metadata
        """
        try:
            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
            response = self.get('paymentGateways', params)
            items = [transform_payment_gateway(gateway) for gateway in response.get('paymentGateways', [])] if isinstance(response, dict) else [transform_payment_gateway(gateway) for gateway in
                                                                                                                                                response]
            pagination = {'next': response.get('next') if isinstance(response, dict) else None, 'count': len(items), 'total': len(items)}
            return items, pagination
        except Exception as e:
            logger.error(f"Error fetching payment gateways: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    # Task Related Methods
    def get_tasks(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List[Task], Dict[str, Any]]:
        """Get a list of tasks.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of tasks to return
            offset: Offset for pagination
            since: Optional timestamp to get tasks modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Task objects
            - Dictionary containing pagination metadata
        """
        try:
            # Set default order to 'due_date' for tasks
            if 'order' not in additional_params:
                additional_params['order'] = 'due_date'

            params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
            response = self.get('tasks', params)
            return transform_list_response(response, transform_task)
        except Exception as e:
            logger.error(f"Error fetching tasks: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    def get_task(self, task_id: int) -> Task:
        """Get a single task by ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            Task object
        """
        try:
            response = self.get(f'tasks/{task_id}')
            return transform_task(response)
        except Exception as e:
            logger.error(f"Error fetching task {task_id}: {str(e)}")
            raise

    # Note Related Methods
    def get_notes(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List[Note], Dict[str, Any]]:
        """Get a list of notes.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of notes to return
            offset: Offset for pagination
            since: Optional timestamp to get notes modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Note objects
            - Dictionary containing pagination metadata
        """
        try:
            # Set default order to 'date_created' for notes
            if 'order' not in additional_params:
                additional_params['order'] = 'date_created'

            params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
            response = self.get('notes', params)
            return transform_list_response(response, transform_note)
        except Exception as e:
            logger.error(f"Error fetching notes: {str(e)}")
            return [], {'next': None, 'count': 0, 'total': 0}

    def get_note(self, note_id: int) -> Note:
        """Get a single note by ID.
        
        Args:
            note_id: The ID of the note to retrieve
            
        Returns:
            Note object
        """
        try:
            response = self.get(f'notes/{note_id}')
            return transform_note(response)
        except Exception as e:
            logger.error(f"Error fetching note {note_id}: {str(e)}")
            raise

    # Campaign Related Methods
    def get_campaigns(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List[Campaign], Dict[str, Any]]:
        """Get a list of campaigns.
        
        Args:
            limit: Maximum number of campaigns to return
            offset: Offset for pagination
            since: Optional timestamp to get campaigns modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Campaign objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get('campaigns', params)
        return transform_list_response(response, transform_campaign)

    def get_campaign(self, campaign_id: int) -> Campaign:
        """Get a single campaign by ID."""
        response = self.get(f'campaigns/{campaign_id}')
        return transform_campaign(response)

    # Subscription Related Methods
    def get_subscriptions(self, contact_id: Optional[int] = None, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[
        List[Subscription], Dict[str, Any]]:
        """Get a list of subscriptions.
        
        Args:
            contact_id: Optional contact ID to filter by
            limit: Maximum number of subscriptions to return
            offset: Offset for pagination
            since: Optional timestamp to get subscriptions modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Subscription objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, contact_id=contact_id, **additional_params)
        response = self.get('subscriptions', params)
        return transform_list_response(response, transform_subscription)

    # Account Related Methods
    def get_account_profile(self) -> AccountProfile:
        """Get the account profile."""
        response = self.get('account/profile')
        return transform_account_profile(response)

    # Affiliate Related Methods
    def get_affiliates(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, db_session=None, **additional_params) -> Tuple[List[Affiliate], Dict[str, Any]]:
        """Get a list of affiliates.
        
        Args:
            limit: Maximum number of affiliates to return
            offset: Offset for pagination
            since: Optional timestamp to get affiliates modified since
            db_session: Optional database session for processing related data
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Affiliate objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get('affiliates', params)
        return transform_list_response(response, transform_affiliate)

    def get_affiliate(self, affiliate_id: int) -> Affiliate:
        """Get a single affiliate by ID."""
        response = self.get(f'affiliates/{affiliate_id}')
        return transform_affiliate(response)

    def get_affiliate_commissions(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[AffiliateCommission], Dict[str, Any]]:
        """Get commissions for an affiliate.
        
        Args:
            affiliate_id: The ID of the affiliate
            limit: Maximum number of commissions to return
            offset: Offset for pagination
            since: Optional timestamp to get commissions modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of AffiliateCommission objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/commissions', params)
        return transform_list_response(response, transform_affiliate_commission)

    def get_affiliate_programs(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[AffiliateProgram], Dict[str, Any]]:
        """Get programs for an affiliate.
        
        Args:
            affiliate_id: The ID of the affiliate
            limit: Maximum number of programs to return
            offset: Offset for pagination
            since: Optional timestamp to get programs modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of AffiliateProgram objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/programs', params)
        return transform_list_response(response, transform_affiliate_program)

    def get_affiliate_redirects(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[AffiliateRedirect], Dict[str, Any]]:
        """Get redirects for an affiliate.
        
        Args:
            affiliate_id: The ID of the affiliate
            limit: Maximum number of redirects to return
            offset: Offset for pagination
            since: Optional timestamp to get redirects modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of AffiliateRedirect objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/redirects', params)
        return transform_list_response(response, transform_affiliate_redirect)

    def get_affiliate_summary(self, affiliate_id: int) -> AffiliateSummary:
        """Get summary for an affiliate."""
        response = self.get(f'affiliates/{affiliate_id}/summary')
        return transform_affiliate_summary(response)

    def get_affiliate_clawbacks(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[AffiliateClawback], Dict[str, Any]]:
        """Get clawbacks for an affiliate.
        
        Args:
            affiliate_id: The ID of the affiliate
            limit: Maximum number of clawbacks to return
            offset: Offset for pagination
            since: Optional timestamp to get clawbacks modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of AffiliateClawback objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/clawbacks', params)
        return transform_list_response(response, transform_affiliate_clawback)

    def get_affiliate_payments(self, affiliate_id: int, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[AffiliatePayment], Dict[str, Any]]:
        """Get payments for an affiliate.
        
        Args:
            affiliate_id: The ID of the affiliate
            limit: Maximum number of payments to return
            offset: Offset for pagination
            since: Optional timestamp to get payments modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of AffiliatePayment objects
            - Dictionary containing pagination metadata
        """
        params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
        response = self.get(f'affiliates/{affiliate_id}/payments', params)
        return transform_list_response(response, transform_affiliate_payment)

    # Tag Related Methods
    def get_tags(self, limit: int = 50, offset: int = 0, since: Optional[str] = None, **additional_params) -> Tuple[List[Tag], Dict[str, Any]]:
        """Get a list of tags.
        
        Args:
            limit: Maximum number of tags to return
            offset: Offset for pagination
            since: Optional timestamp to get tags modified since
            additional_params: Additional parameters to pass to the API
            
        Returns:
            Tuple containing:
            - List of Tag objects
            - Dictionary containing pagination metadata
        """
        try:
            params = self._prepare_params(limit=limit, offset=offset, since=since, **additional_params)
            response = self.get('tags', params)
            logger.debug(f"Raw tags API response: {response}")

            if not response:
                logger.warning("Empty response received from tags API")
                return [], {'next': None, 'previous': None, 'count': 0, 'limit': limit, 'offset': offset}

            return transform_list_response(response, transform_tag)

        except Exception as e:
            logger.error(f"Error fetching tags: {str(e)}")
            return [], {'next': None, 'previous': None, 'count': 0, 'limit': limit, 'offset': offset}

    def get_tag(self, tag_id: int) -> Tag:
        """Get a single tag by ID.
        
        Args:
            tag_id: The ID of the tag to retrieve
            
        Returns:
            Tag object
        """
        try:
            response = self.get(f'tags/{tag_id}')
            logger.debug(f"Raw tag API response: {response}")
            return transform_tag(response)
        except Exception as e:
            logger.error(f"Error fetching tag {tag_id}: {str(e)}")
            raise
