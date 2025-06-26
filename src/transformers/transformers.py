import enum
import logging
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from dateutil.parser import parse as parse_datetime

from src.models.models import (AccountProfile, Affiliate, AffiliateClawback, AffiliateCommission, AffiliatePayment, AffiliateProgram, AffiliateRedirect, AffiliateRedirectProgram, AffiliateStatus,
                               AffiliateSummary, BusinessGoal, Campaign, CampaignSequence, CampaignStatus, Contact, ContactAddress, ContactCustomFieldValue, ContactEmailStatus, ContactSourceType,
                               CreditCard, CustomField, CustomFieldType, EmailAddress, FaxNumber, Note, NoteType, Opportunity, Order, OrderItem, OrderPayment, OrderSourceType, OrderStatus,
                               OrderTransaction, PaymentGateway, PaymentPlan, PhoneNumber, Product, Subscription, SubscriptionPlan, SubscriptionStatus, Tag, TagCategory, Task, TaskPriority,
                               TaskStatus)

logger = logging.getLogger(__name__)


def safe_parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Safely parse a datetime string into a timezone-aware datetime object.
    
    Args:
        dt_str: The datetime string to parse
        
    Returns:
        Timezone-aware datetime object or None if parsing fails
    """
    if not dt_str:
        return None

    try:
        # Try parsing with dateutil first
        dt = parse_datetime(dt_str)
        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError) as e:
        try:
            # Try ISO format as fallback
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing datetime {dt_str}: {e}")
            return None


def safe_enum_convert(value: Any, enum_class: Type[enum.Enum], default: Optional[enum.Enum] = None) -> Optional[enum.Enum]:
    """Safely convert a value to an enum value.
    
    Args:
        value: The value to convert
        enum_class: The enum class to convert to
        default: Optional default value to use if conversion fails
        
    Returns:
        The converted enum value or default if conversion fails
    """
    if value is None:
        return default

    # Special mappings for CustomFieldType to handle API values that don't match database enum
    if enum_class == CustomFieldType:
        api_to_db_mapping = {'TextArea': 'MULTILINE', 'WholeNumber': 'NUMBER', 'Website': 'URL', 'Email': 'EMAIL'}

        # Check if we have a direct mapping
        if str(value) in api_to_db_mapping:
            try:
                return enum_class(api_to_db_mapping[str(value)])
            except ValueError:
                pass

    try:
        # First try direct conversion
        return enum_class(value)
    except ValueError:
        # If that fails, try case-insensitive matching
        try:
            # Convert both the input and enum values to uppercase for comparison
            value_upper = str(value).upper()

            # Try to find a matching enum by comparing uppercase values
            for enum_member in enum_class:
                if str(enum_member.value).upper() == value_upper:
                    return enum_member

            # If no match found, try to find by enum name
            for enum_member in enum_class:
                if enum_member.name.upper() == value_upper:
                    return enum_member

        except Exception:
            pass

        # If all else fails, return default
        return default


def transform_list_response(api_data: Dict[str, Any], transformer_func: Callable) -> Tuple[List[Any], Dict[str, Any]]:
    """Transform a list response from the API into a list of model instances.
    
    Args:
        api_data: The API response data
        transformer_func: Function to transform individual items
        
    Returns:
        Tuple of (list of transformed items, pagination info)
        
    The pagination info dictionary contains:
        - next: URL for the next page (if available)
        - previous: URL for the previous page (if available)
        - count: Number of items in the current page
        - total: Total number of items available
    """
    items = []
    pagination = {}

    try:
        # Handle different response formats
        if isinstance(api_data, dict):
            # Extract items based on response format
            if 'items' in api_data:
                items_data = api_data['items']
                # For entity-specific lists, extract pagination info if available
                pagination = {'next': api_data.get('next'), 'previous': api_data.get('previous'), 'count': api_data.get('count', len(items_data)), 'total': api_data.get('total', len(items_data))}
            else:
                # Try to find entity-specific list
                for key in api_data:
                    if isinstance(api_data[key], list):
                        items_data = api_data[key]
                        # For entity-specific lists, extract pagination info if available
                        pagination = {'next': api_data.get('next'), 'previous': api_data.get('previous'), 'count': api_data.get('count', len(items_data)),
                                      'total': api_data.get('total', len(items_data))}
                        break
                else:
                    # If no list found, treat the entire response as a single item
                    items_data = [api_data]
                    pagination = {'next': None, 'previous': None, 'count': 1, 'total': 1}
        elif isinstance(api_data, list):
            # Direct list response
            items_data = api_data
            pagination = {'next': None, 'previous': None, 'count': len(items_data), 'total': len(items_data)}
        else:
            logger.error(f"Unexpected API response type: {type(api_data)}")
            return [], {}

        # Transform items
        for item_data in items_data:
            try:
                if not isinstance(item_data, dict):
                    logger.warning(f"Skipping non-dict item: {type(item_data)}")
                    continue

                transformed_item = transformer_func(item_data)
                if transformed_item:
                    items.append(transformed_item)
            except Exception as e:
                logger.error(f"Error transforming item: {str(e)}")
                logger.debug(f"Problematic item data: {item_data}")
                continue

        return items, pagination

    except Exception as e:
        logger.error(f"Error in transform_list_response: {str(e)}")
        logger.debug(f"Problematic API data: {api_data}")
        return [], {}


def transform_contact(contact_data: Dict[str, Any]) -> Contact:
    """Transform contact data from API to database model."""
    email_status = contact_data.get('email_status')
    if email_status:
        email_status = safe_enum_convert(email_status, ContactEmailStatus)

    source_type = contact_data.get('source_type')
    if source_type:
        source_type = safe_enum_convert(source_type, ContactSourceType)

    # Helper function to safely parse datetime
    def safe_parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return parse_datetime(dt_str)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing datetime {dt_str}: {e}")
            return None

    return Contact(id=contact_data.get('id'), given_name=contact_data.get('given_name'), family_name=contact_data.get('family_name'), middle_name=contact_data.get('middle_name'), company_name=contact_data.get('company_name'), job_title=contact_data.get('job_title'), email_opted_in=contact_data.get('email_opted_in'), email_status=email_status, score_value=contact_data.get('score_value'), owner_id=contact_data.get('owner_id'), created_at=safe_parse_datetime(contact_data.get('created_at')), modified_at=safe_parse_datetime(contact_data.get('modified_at')), last_updated_utc_millis=contact_data.get('last_updated_utc_millis'), anniversary=safe_parse_datetime(contact_data.get('anniversary')), birthday=safe_parse_datetime(contact_data.get('birthday')), contact_type=contact_data.get('contact_type'), duplicate_option=contact_data.get('duplicate_option'), lead_source_id=contact_data.get('lead_source_id'), preferred_locale=contact_data.get('preferred_locale'), preferred_name=contact_data.get('preferred_name'), source_type=source_type, spouse_name=contact_data.get('spouse_name'), time_zone=contact_data.get('time_zone'), website=contact_data.get('website'), year_created=contact_data.get('year_created'))


def transform_contact_with_related(api_data: Dict[str, Any], db_session=None) -> Contact:
    """Transform API contact data with all related data to Contact model instance.
    
    This function handles the transformation of a contact and all its related data,
    including email addresses, phone numbers, addresses, fax numbers, tags,
    custom fields, opportunities, tasks, notes, orders, and subscriptions.
    
    Args:
        api_data: The contact data from the API
        db_session: Optional database session for querying related data
        
    Returns:
        Contact instance with all related data
    """
    # First transform the basic contact data
    contact = transform_contact(api_data)

    # Handle email addresses
    if 'email_addresses' in api_data:
        for email in api_data['email_addresses']:
            try:
                if isinstance(email, dict):
                    email_address = transform_email_address(email, contact.id)
                else:
                    email_address = transform_email_address(email.__dict__, contact.id)
                contact.email_addresses.append(email_address)
            except Exception as e:
                logger.error(f"Error transforming email address for contact {contact.id}: {str(e)}")

    # Handle phone numbers
    if 'phone_numbers' in api_data:
        for phone in api_data['phone_numbers']:
            try:
                if isinstance(phone, dict):
                    phone_number = transform_phone_number(phone, contact.id)
                else:
                    phone_number = transform_phone_number(phone.__dict__, contact.id)
                contact.phone_numbers.append(phone_number)
            except Exception as e:
                logger.error(f"Error transforming phone number for contact {contact.id}: {str(e)}")

    # Handle addresses
    if 'addresses' in api_data:
        for address in api_data['addresses']:
            try:
                if isinstance(address, dict):
                    address_obj = transform_contact_address(address, contact.id)
                else:
                    address_obj = transform_contact_address(address.__dict__, contact.id)
                contact.addresses.append(address_obj)
            except Exception as e:
                logger.error(f"Error transforming address for contact {contact.id}: {str(e)}")

    # Handle fax numbers
    if 'fax_numbers' in api_data:
        for fax in api_data['fax_numbers']:
            try:
                if isinstance(fax, dict):
                    fax_number = transform_fax_number(fax, contact.id)
                else:
                    fax_number = transform_fax_number(fax.__dict__, contact.id)
                contact.fax_numbers.append(fax_number)
            except Exception as e:
                logger.error(f"Error transforming fax number for contact {contact.id}: {str(e)}")

    # Handle tags
    if 'tag_ids' in api_data:
        for tag_id in api_data['tag_ids']:
            try:
                # Create a minimal Tag object with just the ID
                tag_obj = Tag(id=tag_id, name=f"Tag {tag_id}",  # Generic name for new tags
                              created_at=datetime.now(timezone.utc))
                contact.tags.append(tag_obj)
            except Exception as e:
                logger.error(f"Error transforming tag for contact {contact.id}: {str(e)}")

    # Handle custom fields
    if 'custom_fields' in api_data:
        for field_name, field_def in api_data['custom_fields'].items():
            try:
                custom_field = transform_custom_field(field_name, field_def)
                if 'value' in field_def:
                    custom_field_value = transform_custom_field_value({'value': field_def['value']}, contact.id, custom_field.id)
                    contact.custom_field_values.append(custom_field_value)
            except Exception as e:
                logger.error(f"Error transforming custom field {field_name} for contact {contact.id}: {str(e)}")

    # Handle opportunities
    if 'opportunities' in api_data:
        for opportunity in api_data['opportunities']:
            try:
                if isinstance(opportunity, dict):
                    opportunity_obj = transform_opportunity(opportunity)
                else:
                    opportunity_obj = transform_opportunity(opportunity.__dict__)
                contact.opportunities.append(opportunity_obj)
            except Exception as e:
                logger.error(f"Error transforming opportunity for contact {contact.id}: {str(e)}")

    # Handle tasks
    if 'tasks' in api_data:
        for task in api_data['tasks']:
            try:
                if isinstance(task, dict):
                    task_obj = transform_task(task)
                else:
                    task_obj = transform_task(task.__dict__)
                contact.tasks.append(task_obj)
            except Exception as e:
                logger.error(f"Error transforming task for contact {contact.id}: {str(e)}")

    # Handle notes
    if 'notes' in api_data:
        for note in api_data['notes']:
            try:
                if isinstance(note, dict):
                    note_obj = transform_note(note)
                else:
                    note_obj = transform_note(note.__dict__)
                contact.notes.append(note_obj)
            except Exception as e:
                logger.error(f"Error transforming note for contact {contact.id}: {str(e)}")

    # Handle orders
    if 'orders' in api_data:
        for order in api_data['orders']:
            try:
                if isinstance(order, dict):
                    order_obj = transform_order_with_items(order)
                else:
                    order_obj = transform_order_with_items(order.__dict__)
                contact.orders.append(order_obj)
            except Exception as e:
                logger.error(f"Error transforming order for contact {contact.id}: {str(e)}")

    # Handle subscriptions
    if 'subscriptions' in api_data:
        for subscription in api_data['subscriptions']:
            try:
                if isinstance(subscription, dict):
                    subscription_obj = transform_subscription(subscription)
                else:
                    subscription_obj = transform_subscription(subscription.__dict__)
                contact.subscriptions.append(subscription_obj)
            except Exception as e:
                logger.error(f"Error transforming subscription for contact {contact.id}: {str(e)}")

    return contact


def transform_order_with_items(api_data: Dict[str, Any]) -> Order:
    """Transform API order data to Order model instance with its items."""
    if not isinstance(api_data, dict):
        api_data = api_data.__dict__

    order = transform_order(api_data)

    # Transform order items
    if 'order_items' in api_data:
        order.items = []
        for item in api_data['order_items']:
            try:
                if not isinstance(item, dict):
                    item = item.__dict__
                order.items.append(transform_order_item(item))
            except Exception as e:
                logger.error(f"Error transforming order item: {str(e)}")

    # Handle payment plan data if it exists in the order response
    if 'payment_plan' in api_data and api_data['payment_plan']:
        try:
            from src.transformers.transformers import transform_payment_plan
            order.payment_plan = transform_payment_plan(api_data['payment_plan'], order.id)
        except Exception as e:
            logger.error(f"Error transforming payment plan for order {order.id}: {str(e)}")

    return order


def transform_email_address(api_data: Dict[str, Any], contact_id: int) -> EmailAddress:
    """Transform API email address data into an EmailAddress model instance."""
    return EmailAddress(id=api_data.get('id'), email=api_data.get('email'), field=api_data.get('field'), type=api_data.get('type'), contact_id=contact_id)


def transform_phone_number(api_data: Dict[str, Any], contact_id: int) -> PhoneNumber:
    """Transform API phone number data into a PhoneNumber model instance."""
    return PhoneNumber(id=api_data.get('id'), number=api_data.get('number'), field=api_data.get('field'), type=api_data.get('type'), contact_id=contact_id)


def transform_contact_address(api_data: Dict[str, Any], contact_id: int) -> ContactAddress:
    """Transform API address data into a ContactAddress model instance."""
    return ContactAddress(id=api_data.get('id'), country_code=api_data.get('country_code'), field=api_data.get('field'), line1=api_data.get('line1'), line2=api_data.get('line2'), locality=api_data.get('locality'), postal_code=api_data.get('postal_code'), region=api_data.get('region'), zip_code=api_data.get('zip_code'), zip_four=api_data.get('zip_four'), contact_id=contact_id)


def transform_fax_number(api_data: Dict[str, Any], contact_id: int) -> FaxNumber:
    """Transform API fax number data into a FaxNumber model instance."""
    return FaxNumber(id=api_data.get('id'), number=api_data.get('number'), field=api_data.get('field'), type=api_data.get('type'), contact_id=contact_id)


def transform_credit_card(api_data: Dict[str, Any]) -> CreditCard:
    """Transform API credit card data into a CreditCard model instance."""
    try:
        return CreditCard(id=api_data.get('id'), contact_id=api_data.get('contact_id'), card_type=api_data.get('card_type'), card_number=api_data.get('card_number'), expiration_month=api_data.get('expiration_month'), expiration_year=api_data.get('expiration_year'), card_holder_name=api_data.get('card_holder_name'), is_default=api_data.get('is_default', False), created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))
    except Exception as e:
        logger.error(f"Error transforming credit card: {str(e)}")
        logger.debug(f"Problematic credit card data: {api_data}")
        raise


def transform_custom_field(field_name: str, field_def: Dict[str, Any]) -> CustomField:
    """Transform API custom field definition into a CustomField model instance.
    
    Args:
        field_name: The name/key of the custom field (for backward compatibility)
        field_def: The custom field definition from the API
        
    Returns:
        CustomField model instance
    """
    # Handle the new API structure where field_def is a complete object
    if isinstance(field_def, dict) and 'id' in field_def:
        # New API structure - field_def is the complete field object
        field_id = field_def.get('id')
        field_type_str = field_def.get('field_type')
        label = field_def.get('label')
        field_name_internal = field_def.get('field_name')
        record_type = field_def.get('record_type')
        default_value = field_def.get('default_value')
        options = field_def.get('options', [])

        # Convert API field type to our enum and always use uppercase value
        field_type_enum = safe_enum_convert(field_type_str, CustomFieldType)
        field_type = field_type_enum.value.upper() if field_type_enum else None

        return CustomField(id=field_id, name=field_name_internal or field_name,  # Use field_name from API if available
                           type=field_type, options=options, label=label, field_name=field_name_internal, record_type=record_type, default_value=default_value)
    else:
        # Legacy structure - field_def is just the field definition
        field_type_enum = safe_enum_convert(field_def.get('type'), CustomFieldType)
        field_type = field_type_enum.value.upper() if field_type_enum else None

        return CustomField(id=field_def.get('id'), name=field_name, type=field_type, options=field_def.get('options'))


def transform_custom_field_value(api_data: Dict[str, Any], entity_id: int, custom_field_id: int) -> ContactCustomFieldValue:
    """Transform API custom field value data into a CustomFieldValue model instance."""
    return ContactCustomFieldValue(id=api_data.get('id'), contact_id=entity_id, custom_field_id=custom_field_id, value=api_data.get('value'))


def transform_tag(api_data: Dict[str, Any]) -> Optional[Tag]:
    """Transform API tag data into a Tag model instance.
    
    Args:
        api_data: Dictionary containing tag data from the API
        
    Returns:
        Tag instance or None if api_data is empty
    """
    if not api_data:
        return None

    try:
        # Create tag instance with required fields
        tag = Tag(id=api_data.get('id'), name=api_data.get('name', ''),  # Ensure name is never None
                  description=api_data.get('description'))

        # Handle category data
        category_data = api_data.get('category', {})
        if category_data:
            category = TagCategory()
            category.id = category_data.get('id')
            category.name = category_data.get('name')
            tag.category = category
            tag.category_id = category.id

        # Handle created_at timestamp
        created_at = api_data.get('created_at')
        if created_at:
            tag.created_at = safe_parse_datetime(created_at)
        else:
            tag.created_at = datetime.now(timezone.utc)

        return tag

    except Exception as e:
        logger.error(f"Error transforming tag data: {str(e)}")
        logger.debug(f"Problematic tag data: {api_data}")
        return None


def transform_applied_tag(api_data: Dict[str, Any]) -> Optional[Tag]:
    """Transform API applied tag data to Tag model instance."""
    try:
        if not isinstance(api_data, dict):
            logger.error(f"Invalid applied tag data format: {type(api_data)}")
            return None

        # Handle both nested and direct tag data formats
        tag_data = api_data.get('tag', api_data)
        if not isinstance(tag_data, dict):
            logger.error(f"Invalid tag data in applied tag: {type(tag_data)}")
            return None

        # Create tag instance
        tag = Tag(id=tag_data.get('id'), name=tag_data.get('name'), description=tag_data.get('description'), category=tag_data.get('category'))

        # Handle created_at timestamp
        created_at = api_data.get('created_at')
        if created_at:
            tag.created_at = safe_parse_datetime(created_at)
        else:
            tag.created_at = datetime.now(timezone.utc)

        return tag

    except Exception as e:
        logger.error(f"Error transforming applied tag data: {e}")
        return None


def transform_opportunity(api_data: Dict[str, Any]) -> Opportunity:
    """Transform opportunity data from API to Opportunity model."""
    opportunity = Opportunity(id=api_data.get('id'), title=api_data.get('opportunity_title'),  # API returns 'opportunity_title', model expects 'title'
                              stage=api_data.get('stage'),  # Now storing the entire stage object as JSON
                              value=api_data.get('value'), probability=api_data.get('probability'), next_action_date=safe_parse_datetime(api_data.get('next_action_date')), next_action_notes=api_data.get('opportunity_notes'),
                              # API returns 'opportunity_notes', model expects 'next_action_notes'
                              source_type=api_data.get('source_type'), source_id=api_data.get('source_id'), pipeline_id=api_data.get('pipeline_id'), pipeline_stage_id=api_data.get('pipeline_stage_id'), owner_id=api_data.get('owner_id'), last_updated_utc_millis=api_data.get('last_updated_utc_millis'))
    return opportunity


def transform_product(api_data: Dict[str, Any]) -> Product:
    """Transform API product data into a Product model instance.
    
    This function also handles subscription plans that are embedded in the product API response.
    The subscription plans are stored in the product.subscription_plans relationship.
    """
    try:
        product = Product(id=api_data.get('id'), sku=api_data.get('sku', ''), active=api_data.get('active', True), url=api_data.get('url'), product_name=api_data.get('product_name'), sub_category_id=api_data.get('sub_category_id', 0), product_desc=api_data.get('product_desc'), product_price=api_data.get('product_price'), product_short_desc=api_data.get('product_short_desc'), subscription_only=api_data.get('subscription_only', False), status=api_data.get('status', 1))

        # Handle subscription plans if they exist in the API response
        subscription_plans_data = api_data.get('subscription_plans', [])
        if subscription_plans_data and isinstance(subscription_plans_data, list):
            product.subscription_plans = []
            for plan_data in subscription_plans_data:
                try:
                    subscription_plan = transform_subscription_plan(plan_data, product.id)
                    product.subscription_plans.append(subscription_plan)
                except Exception as e:
                    logger.error(f"Error transforming subscription plan for product {product.id}: {str(e)}")
                    continue

        return product
    except Exception as e:
        logger.error(f"Error transforming product: {str(e)}")
        logger.debug(f"Problematic product data: {api_data}")
        raise


def transform_subscription_plan(api_data: Dict[str, Any], product_id: int) -> SubscriptionPlan:
    """Transform API subscription plan data into a SubscriptionPlan model instance.
    
    Args:
        api_data: The subscription plan data from the API
        product_id: The ID of the product this subscription plan belongs to
        
    Returns:
        SubscriptionPlan instance
    """
    try:
        return SubscriptionPlan(id=api_data.get('id'), product_id=product_id, name=api_data.get('name'), description=api_data.get('description'), frequency=api_data.get('frequency'), subscription_plan_price=api_data.get('subscription_plan_price'), created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))
    except Exception as e:
        logger.error(f"Error transforming subscription plan: {str(e)}")
        logger.debug(f"Problematic subscription plan data: {api_data}")
        raise


def transform_order(api_data: Dict[str, Any]) -> Order:
    """Transform order data from API to database model."""
    status = safe_enum_convert(api_data.get('status'), OrderStatus)
    source_type = safe_enum_convert(api_data.get('source_type'), OrderSourceType)

    # Handle product_id being '0' or 0
    product_id = api_data.get('product_id')
    if product_id in ('0', 0):
        product_id = None

    return Order(id=api_data.get('id'), title=api_data.get('title'), status=status, recurring=api_data.get('recurring'), total=api_data.get('total'), notes=api_data.get('notes'), terms=api_data.get('terms'), order_type=api_data.get('order_type'), source_type=source_type, creation_date=safe_parse_datetime(api_data.get('creation_date')), modification_date=safe_parse_datetime(api_data.get('modification_date')), order_date=safe_parse_datetime(api_data.get('order_date')), lead_affiliate_id=api_data.get('lead_affiliate_id'), sales_affiliate_id=api_data.get('sales_affiliate_id'), total_paid=api_data.get('total_paid'), total_due=api_data.get('total_due'), refund_total=api_data.get('refund_total'), allow_payment=api_data.get('allow_payment'), allow_paypal=api_data.get('allow_paypal'), invoice_number=api_data.get('invoice_number'), contact_id=api_data.get('contact_id'), product_id=product_id, payment_gateway_id=api_data.get('payment_gateway_id'), subscription_plan_id=api_data.get('subscription_plan_id'))


def transform_order_item(api_data: Dict[str, Any]) -> OrderItem:
    """Transform order item data from API to database model."""
    return OrderItem(id=api_data[
        'id'], job_recurring_id=api_data.get('jobRecurringId'), name=api_data.get('name'), description=api_data.get('description'), type=api_data.get('type'), notes=api_data.get('notes'), quantity=api_data.get('quantity'), cost=api_data.get('cost'), price=api_data.get('price'), discount=api_data.get('discount'), special_id=api_data.get('specialId'), special_amount=api_data.get('specialAmount'), special_pct_or_amt=api_data.get('specialPctOrAmt'), product_id=api_data.get('product', {}).get('id') if api_data.get('product') else None, subscription_plan_id=api_data.get('subscriptionPlan', {}).get('id') if api_data.get('subscriptionPlan') else None)


def transform_order_payment(api_data: Dict[str, Any]) -> OrderPayment:
    """Transform API order payment data into an OrderPayment model instance."""
    if not isinstance(api_data, dict):
        api_data = api_data.__dict__

    return OrderPayment(id=api_data.get('id'), order_id=api_data.get('order_id'), amount=api_data.get('amount'), note=api_data.get('note'), invoice_id=api_data.get('invoice_id'), payment_id=api_data.get('payment_id'), pay_date=safe_parse_datetime(api_data.get('pay_date')), pay_status=api_data.get('pay_status'), last_updated=safe_parse_datetime(api_data.get('last_updated')), skip_commission=api_data.get('skip_commission', False), refund_invoice_payment_id=api_data.get('refund_invoice_payment_id', 0), created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))


def transform_order_transaction(api_data: Dict[str, Any]) -> OrderTransaction:
    """Transform API order transaction data into OrderTransaction model instance."""
    return OrderTransaction(id=api_data.get('id'), test=api_data.get('test', False), amount=api_data.get('amount'), currency=api_data.get('currency'), gateway=api_data.get('gateway'), payment_date=safe_parse_datetime(api_data.get('paymentDate')), type=api_data.get('type'), status=api_data.get('status'), errors=api_data.get('errors'), contact_id=api_data.get('contact_id'), transaction_date=safe_parse_datetime(api_data.get('transaction_date')), gateway_account_name=api_data.get('gateway_account_name'), order_ids=api_data.get('order_ids'), collection_method=api_data.get('collection_method'), payment_id=api_data.get('payment_id'), created_at=datetime.now(timezone.utc), modified_at=datetime.now(timezone.utc))


def transform_note(api_data: Dict[str, Any]) -> Note:
    """Transform API data to Note model."""
    note_type = safe_enum_convert(api_data.get('type'), NoteType)
    # Convert enum to string value if it exists
    type_value = note_type.value if note_type else None

    return Note(id=api_data.get('id'), contact_id=api_data.get('contact_id'), title=api_data.get('title'), body=api_data.get('body'), type=type_value,  # Use the string value instead of enum
                created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))


def transform_task(api_data: Dict[str, Any]) -> Task:
    """Transform task data from API to database model."""
    status = safe_enum_convert(api_data.get('status'), TaskStatus)
    priority = safe_enum_convert(api_data.get('priority'), TaskPriority)

    return Task(id=api_data.get('id'), contact_id=api_data.get('contact_id'), title=api_data.get('title'), notes=api_data.get('notes'), priority=priority, status=status, type=api_data.get('type'), due_date=safe_parse_datetime(api_data.get('due_date')))


def transform_campaign(api_data: Dict[str, Any]) -> Campaign:
    """Transform campaign data from API to database model."""
    status = safe_enum_convert(api_data.get('status'), CampaignStatus)

    return Campaign(id=api_data.get('id'), name=api_data.get('name'), description=api_data.get('description'), status=status, created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))


def transform_campaign_sequence(api_data: Dict[str, Any]) -> CampaignSequence:
    """Transform API campaign sequence data into a CampaignSequence model instance."""
    return CampaignSequence(id=api_data.get('id'), campaign_id=api_data.get('campaign_id'), name=api_data.get('name'), description=api_data.get('description'), status=api_data.get('status'), sequence_number=api_data.get('sequence_number'))


def transform_subscription(api_data: Dict[str, Any]) -> Subscription:
    """Transform subscription data from API to database model."""
    status = safe_enum_convert(api_data.get('status'), SubscriptionStatus)

    return Subscription(id=api_data.get('id'), product_id=api_data.get('product_id'), subscription_plan_id=api_data.get('subscription_plan_id'), status=status, next_bill_date=safe_parse_datetime(api_data.get('next_bill_date')), contact_id=api_data.get('contact_id'), payment_gateway_id=api_data.get('payment_gateway_id'), credit_card_id=api_data.get('credit_card_id'), start_date=safe_parse_datetime(api_data.get('start_date')), end_date=safe_parse_datetime(api_data.get('end_date')), billing_cycle=api_data.get('billing_cycle'), created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))


def transform_account_profile(api_data: Dict[str, Any]) -> AccountProfile:
    """Transform API account profile data to AccountProfile model instance."""
    profile = AccountProfile(id=api_data.get('id'), address_id=api_data.get('address_id'), business_primary_color=api_data.get('business_primary_color'), business_secondary_color=api_data.get('business_secondary_color'), business_type=api_data.get('business_type'), currency_code=api_data.get('currency_code'), email=api_data.get('email'), language_tag=api_data.get('language_tag'), logo_url=api_data.get('logo_url'), name=api_data.get('name'), phone=api_data.get('phone'), phone_ext=api_data.get('phone_ext'), time_zone=api_data.get('time_zone'), website=api_data.get('website'), created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))

    # Transform business goals
    if 'business_goals' in api_data:
        profile.business_goals = []
        for goal in api_data['business_goals']:
            try:
                profile.business_goals.append(transform_business_goal(goal, profile.id))
            except Exception as e:
                logger.error(f"Error transforming business goal for profile {profile.id}: {str(e)}")
                continue

    return profile


def transform_business_goal(api_data: Dict[str, Any], account_profile_id: int) -> BusinessGoal:
    """Transform API business goal data into a BusinessGoal model instance."""
    return BusinessGoal(id=api_data.get('id'), account_profile_id=account_profile_id, goal=api_data.get('goal'))


def transform_affiliate(api_data: Dict[str, Any]) -> Affiliate:
    """Transform API affiliate data into an Affiliate model instance."""
    status = safe_enum_convert(api_data.get('status'), AffiliateStatus)

    return Affiliate(id=api_data.get('id'), code=api_data.get('code'), contact_id=api_data.get('contact_id'), name=api_data.get('name'), parent_id=api_data.get('parent_id'), status=status, notify_on_lead=api_data.get('notify_on_lead'), notify_on_sale=api_data.get('notify_on_sale'), track_leads_for=api_data.get('track_leads_for'))


def transform_affiliate_commission(api_data: Dict[str, Any]) -> AffiliateCommission:
    """Transform API affiliate commission data into an AffiliateCommission model instance."""
    return AffiliateCommission(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount_earned=api_data.get('amount_earned'), contact_id=api_data.get('contact_id'), contact_first_name=api_data.get('contact_first_name'), contact_last_name=api_data.get('contact_last_name'), date_earned=safe_parse_datetime(api_data.get('date_earned')), description=api_data.get('description'), invoice_id=api_data.get('invoice_id'), product_name=api_data.get('product_name'), sales_affiliate_id=api_data.get('sales_affiliate_id'), sold_by_first_name=api_data.get('sold_by_first_name'), sold_by_last_name=api_data.get('sold_by_last_name'))


def transform_affiliate_program(api_data: Dict[str, Any]) -> AffiliateProgram:
    """Transform API affiliate program data into an AffiliateProgram model instance."""
    return AffiliateProgram(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), name=api_data.get('name'), notes=api_data.get('notes'), priority=api_data.get('priority'))


def transform_affiliate_redirect(api_data: Dict[str, Any]) -> AffiliateRedirect:
    """Transform API affiliate redirect data into an AffiliateRedirect model instance."""
    return AffiliateRedirect(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), local_url_code=api_data.get('local_url_code'), name=api_data.get('name'), redirect_url=api_data.get('redirect_url'))


def transform_affiliate_summary(api_data: Dict[str, Any]) -> AffiliateSummary:
    """Transform API affiliate summary data into an AffiliateSummary model instance."""
    return AffiliateSummary(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount_earned=api_data.get('amount_earned'), balance=api_data.get('balance'), clawbacks=api_data.get('clawbacks'))


def transform_affiliate_clawback(api_data: Dict[str, Any]) -> AffiliateClawback:
    """Transform API affiliate clawback data into an AffiliateClawback model instance."""
    return AffiliateClawback(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount=api_data.get('amount'), contact_id=api_data.get('contact_id'), date_earned=safe_parse_datetime(api_data.get('date_earned')), description=api_data.get('description'), family_name=api_data.get('family_name'), given_name=api_data.get('given_name'), invoice_id=api_data.get('invoice_id'), product_name=api_data.get('product_name'), sale_affiliate_id=api_data.get('sale_affiliate_id'), sold_by_family_name=api_data.get('sold_by_family_name'), sold_by_given_name=api_data.get('sold_by_given_name'), subscription_plan_name=api_data.get('subscription_plan_name'))


def transform_affiliate_payment(api_data: Dict[str, Any]) -> AffiliatePayment:
    """Transform API affiliate payment data into an AffiliatePayment model instance."""
    return AffiliatePayment(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount=api_data.get('amount'), date=safe_parse_datetime(api_data.get('date')), notes=api_data.get('notes'), type=api_data.get('type'))


def transform_affiliate_redirect_program(api_data: Dict[str, Any], affiliate_redirect_id: int) -> AffiliateRedirectProgram:
    """Transform API affiliate redirect program data into an AffiliateRedirectProgram model instance."""
    return AffiliateRedirectProgram(id=api_data.get('id'), affiliate_redirect_id=affiliate_redirect_id, program_id=api_data.get('program_id'))


def transform_payment_plan(api_data: Dict[str, Any], order_id: int) -> PaymentPlan:
    """Transform API payment plan data into a PaymentPlan model instance.
    
    Args:
        api_data: The payment plan data from the API
        order_id: The ID of the order this payment plan belongs to
        
    Returns:
        PaymentPlan instance
    """
    try:
        # Extract payment gateway information from the nested structure
        payment_gateway_data = api_data.get('payment_gateway', {})
        merchant_account_id = payment_gateway_data.get('merchant_account_id')
        merchant_account_name = payment_gateway_data.get('merchant_account_name')
        
        return PaymentPlan(
            order_id=order_id,
            auto_charge=api_data.get('auto_charge'),
            credit_card_id=api_data.get('credit_card_id'),
            days_between_payments=api_data.get('days_between_payments'),
            initial_payment_amount=api_data.get('initial_payment_amount'),
            initial_payment_percent=api_data.get('initial_payment_percent'),
            initial_payment_date=safe_parse_date(api_data.get('initial_payment_date')),
            number_of_payments=api_data.get('number_of_payments'),
            merchant_account_id=merchant_account_id,
            merchant_account_name=merchant_account_name,
            plan_start_date=safe_parse_date(api_data.get('plan_start_date')),
            payment_method_id=api_data.get('payment_method_id'),
            max_charge_attempts=api_data.get('max_charge_attempts'),
            days_between_retries=api_data.get('days_between_retries'),
            created_at=safe_parse_datetime(api_data.get('created_at')),
            modified_at=safe_parse_datetime(api_data.get('modified_at'))
        )
    except Exception as e:
        logger.error(f"Error transforming payment plan: {str(e)}")
        logger.debug(f"Problematic payment plan data: {api_data}")
        raise


def transform_payment_gateway(api_data: Dict[str, Any]) -> PaymentGateway:
    """Transform API payment gateway data into a PaymentGateway model instance."""
    try:
        return PaymentGateway(id=api_data.get('id'), name=api_data.get('name'), type=api_data.get('type'), is_active=api_data.get('is_active', True), credentials=api_data.get('credentials'), settings=api_data.get('settings'), created_at=safe_parse_datetime(api_data.get('created_at')), modified_at=safe_parse_datetime(api_data.get('modified_at')))
    except Exception as e:
        logger.error(f"Error transforming payment gateway: {str(e)}")
        logger.debug(f"Problematic payment gateway data: {api_data}")
        raise


def safe_parse_date(date_string: Optional[str]) -> Optional[date]:
    """Safely parse a date string.
    
    Args:
        date_string: The date string to parse
        
    Returns:
        Parsed date object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        if isinstance(date_string, str):
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                try:
                    return datetime.strptime(date_string, fmt).date()
                except ValueError:
                    continue

            # If none of the formats work, try parsing as datetime first
            parsed_datetime = safe_parse_datetime(date_string)
            if parsed_datetime:
                return parsed_datetime.date()

        return None
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_string}': {str(e)}")
        return None
