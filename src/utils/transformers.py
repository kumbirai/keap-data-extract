import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from ..models.models import (AccountProfile, Address, AddressType, Affiliate, AffiliateClawback, AffiliateCommission, AffiliatePayment, AffiliateProgram, AffiliateRedirect, AffiliateRedirectProgram,
                             AffiliateSummary, BusinessGoal, Campaign, CampaignSequence, Contact, ContactCustomFieldValue, CustomField, CustomFieldMetaData, EmailAddress, FaxNumber, Note, Opportunity,
                             Order, OrderItem, OrderPayment, PhoneNumber, Product, Subscription, Tag, Task, OrderTransaction)

logger = logging.getLogger(__name__)


def transform_contact(api_data: Dict[str, Any]) -> Contact:
    """Transform API contact data to Contact model instance."""
    return Contact(id=api_data.get('id'), given_name=api_data.get('given_name'), family_name=api_data.get('family_name'), middle_name=api_data.get('middle_name'), company_name=api_data.get('company'),
                   # API uses 'company' instead of 'company_name'
                   job_title=api_data.get('job_title'), email_opted_in=api_data.get('email_opted_in', False), email_status=api_data.get('email_status'), score_value=api_data.get('ScoreValue'),
                   # API uses 'ScoreValue' instead of 'score_value'
                   owner_id=api_data.get('owner_id'), created_at=datetime.fromisoformat(api_data.get('date_created')) if api_data.get('date_created') else None, modified_at=datetime.fromisoformat(api_data.get('last_updated')) if api_data.get('last_updated') else None, last_updated_utc_millis=api_data.get('last_updated_utc_millis'),
                   # New fields from API reference
                   anniversary=datetime.fromisoformat(api_data.get('anniversary')) if api_data.get('anniversary') else None, birthday=datetime.fromisoformat(api_data.get('birthday')) if api_data.get('birthday') else None, contact_type=api_data.get('contact_type'), duplicate_option=api_data.get('duplicate_option'), lead_source_id=api_data.get('lead_source_id'), preferred_locale=api_data.get('preferred_locale'), preferred_name=api_data.get('preferred_name'), source_type=api_data.get('source_type'), spouse_name=api_data.get('spouse_name'), time_zone=api_data.get('time_zone'), website=api_data.get('website'), year_created=api_data.get('year_created'))


def transform_email_address(api_data: Dict[str, Any]) -> EmailAddress:
    """Transform API email address data to EmailAddress model instance."""
    return EmailAddress(email=api_data.get('email'), field=api_data.get('field'), type=api_data.get('type'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_phone_number(api_data: Dict[str, Any]) -> PhoneNumber:
    """Transform API phone number data to PhoneNumber model instance."""
    return PhoneNumber(number=api_data.get('number'), field=api_data.get('field'), type=api_data.get('type'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_address(api_data: Dict[str, Any]) -> Address:
    """Transform API address data to Address model instance."""
    field = api_data.get('field', 'OTHER')
    if isinstance(field, str):
        field = AddressType[field.upper()]

    return Address(country_code=api_data.get('country_code'), field=field, line1=api_data.get('line1'), line2=api_data.get('line2'), locality=api_data.get('locality'), postal_code=api_data.get('postal_code'), region=api_data.get('region'), zip_code=api_data.get('zip_code'), zip_four=api_data.get('zip_four'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_tag(api_data: Dict[str, Any]) -> Tag:
    """Transform API tag data to Tag model instance."""
    category = api_data.get('category')
    if isinstance(category, dict):
        category = category.get('name')

    # Validate that name exists
    name = api_data.get('name')
    if not name:
        raise ValueError(f"Tag name is required. Tag ID: {api_data.get('id')}")

    return Tag(id=api_data.get('id'), name=name, description=api_data.get('description'), category=category, created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_custom_field(field_name: str, field_def: Dict[str, Any]) -> CustomField:
    """Transform API custom field data to CustomField model instance.
    
    Args:
        field_name: The name of the custom field
        field_def: The field definition from the contact model
        
    Returns:
        CustomField instance
    """
    custom_field = CustomField(id=field_def.get('id'), name=field_name, type=field_def.get('type'), options=field_def.get('options'), created_at=datetime.now(timezone.utc))

    # Add metadata if available
    if 'metadata' in field_def:
        metadata = field_def['metadata']
        custom_field.field_metadata = CustomFieldMetaData(label=metadata.get('label'), description=metadata.get('description'), data_type=metadata.get('data_type'), is_required=metadata.get('is_required', False), is_read_only=metadata.get('is_read_only', False), is_visible=metadata.get('is_visible', True), created_at=datetime.now(timezone.utc))

    return custom_field


def transform_custom_field_value(api_data: Dict[str, Any], contact_id: int, custom_field_id: int) -> ContactCustomFieldValue:
    """Transform API custom field value data to ContactCustomFieldValue model instance."""
    return ContactCustomFieldValue(contact_id=contact_id, custom_field_id=custom_field_id, value=api_data.get('value'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_opportunity(api_data: Dict[str, Any]) -> Opportunity:
    """Transform API opportunity data to Opportunity model instance."""
    # Handle complex stage object
    stage = api_data.get('stage')
    if isinstance(stage, dict):
        stage = stage.get('name')

    # Handle complex value object if present
    value = api_data.get('value')
    if isinstance(value, dict):
        value = value.get('amount')

    # Handle complex probability object if present
    probability = api_data.get('probability')
    if isinstance(probability, dict):
        probability = probability.get('value')

    # Generate a default title if none is provided
    title = api_data.get('title')
    if not title:
        stage_name = stage if stage else 'Unknown Stage'
        contact_id = api_data.get('contact_id', 'Unknown Contact')
        title = f"Opportunity for Contact {contact_id} - {stage_name}"

    return Opportunity(id=api_data.get('id'), title=title, stage=stage, value=value, probability=probability, created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_product(api_data: Dict[str, Any]) -> Product:
    """Transform API product data to Product model instance."""
    return Product(id=api_data.get('id'), product_name=api_data.get('product_name'), product_sku=api_data.get('product_sku'), subscription_only=api_data.get('subscription_only', False), plan_description=api_data.get('plan_description'), frequency=api_data.get('frequency'), price=api_data.get('price'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_order(api_data: Dict[str, Any]) -> Order:
    """Transform API order data to Order model instance."""
    return Order(id=api_data.get('id'), order_number=api_data.get('order_number'), order_date=datetime.fromisoformat(api_data.get('order_date')) if api_data.get('order_date') else None, order_status=api_data.get('order_status'), order_total=api_data.get('order_total'), order_type=api_data.get('order_type'), payment_plan_id=api_data.get('payment_plan_id'), payment_type=api_data.get('payment_type'), subscription_plan_id=api_data.get('subscription_plan_id'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_order_item(api_data: Dict[str, Any]) -> OrderItem:
    """Transform API order item data to OrderItem model instance."""
    return OrderItem(id=api_data.get('id'), quantity=api_data.get('quantity'), price=api_data.get('price'), description=api_data.get('description'), subscription_plan_id=api_data.get('subscription_plan_id'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_order_payment(api_data: Dict[str, Any]) -> OrderPayment:
    """Transform API order payment data into OrderPayment model instance."""
    return OrderPayment(id=api_data.get('id'), order_id=api_data.get('order_id'), amount=api_data.get('amount'), payment_date=datetime.fromisoformat(api_data.get('payment_date')) if api_data.get('payment_date') else None, payment_type=api_data.get('payment_type'), payment_status=api_data.get('payment_status'), payment_gateway=api_data.get('payment_gateway'), transaction_id=api_data.get('transaction_id'), notes=api_data.get('notes'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_order_transaction(api_data: Dict[str, Any]) -> OrderTransaction:
    """Transform API order transaction data into OrderTransaction model instance."""
    return OrderTransaction(id=api_data.get('id'), order_id=api_data.get('order_id'), transaction_date=datetime.fromisoformat(api_data.get('transaction_date')) if api_data.get('transaction_date') else None, transaction_type=api_data.get('transaction_type'), transaction_status=api_data.get('transaction_status'), amount=api_data.get('amount'), payment_gateway=api_data.get('payment_gateway'), gateway_transaction_id=api_data.get('gateway_transaction_id'), gateway_response_code=api_data.get('gateway_response_code'), gateway_response_message=api_data.get('gateway_response_message'), payment_type=api_data.get('payment_type'), card_type=api_data.get('card_type'), card_last_four=api_data.get('card_last_four'), card_expiration_month=api_data.get('card_expiration_month'), card_expiration_year=api_data.get('card_expiration_year'), notes=api_data.get('notes'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_task(api_data: Dict[str, Any]) -> Task:
    """Transform API task data to Task model instance."""
    return Task(id=api_data.get('id'), title=api_data.get('title'), description=api_data.get('description'), due_date=datetime.fromisoformat(api_data.get('due_date')) if api_data.get('due_date') else None, completed=api_data.get('completed', False), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_note(api_data: Dict[str, Any]) -> Note:
    """Transform API note data to Note model instance."""
    return Note(id=api_data.get('id'), title=api_data.get('title'), body=api_data.get('body'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_campaign(api_data: Dict[str, Any]) -> Campaign:
    """Transform API campaign data to Campaign model instance."""
    return Campaign(id=api_data.get('id'), name=api_data.get('name'), status=api_data.get('status'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_campaign_sequence(api_data: Dict[str, Any]) -> CampaignSequence:
    """Transform API campaign sequence data to CampaignSequence model instance."""
    return CampaignSequence(id=api_data.get('id'), campaign_id=api_data.get('campaign_id'), name=api_data.get('name'), status=api_data.get('status'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_subscription(api_data: Dict[str, Any]) -> Subscription:
    """Transform API subscription data to Subscription model instance."""
    return Subscription(id=api_data.get('id'), status=api_data.get('status'), next_bill_date=datetime.fromisoformat(api_data.get('next_bill_date')) if api_data.get('next_bill_date') else None, created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_list_response(api_data: Dict[str, Any], transform_func: callable) -> Tuple[List[Any], Dict[str, Any]]:
    """Transform a list response from the API using the specified transformation function.
    
    Args:
        api_data: The API response data
        transform_func: Function to transform individual items
        
    Returns:
        Tuple containing:
        - List of transformed items
        - Dictionary containing pagination metadata (next URL, count, total)
    """
    # Handle special case for contacts
    if 'contacts' in api_data:
        items = api_data['contacts']
    else:
        # Try to find the first key whose value is a list
        items = None
        for key, value in api_data.items():
            if isinstance(value, list):
                items = value
                break
        # Fallback to 'items' key if present
        if items is None:
            items = api_data.get('items', [])

    # Transform items with error handling
    transformed_items = []
    for item in items:
        try:
            transformed_item = transform_func(item)
            transformed_items.append(transformed_item)
        except Exception as e:
            logger.error(f"Error transforming item: {str(e)}")
            logger.debug(f"Problematic item data: {item}")
            continue

    # Extract pagination metadata
    pagination = {'next': api_data.get('next'), 'count': api_data.get('count'), 'total': api_data.get('total')}

    return transformed_items, pagination


def transform_fax_number(api_data: Dict[str, Any]) -> FaxNumber:
    """Transform API fax number data to FaxNumber model instance."""
    return FaxNumber(number=api_data.get('number'), field=api_data.get('field'), type=api_data.get('type'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_business_goal(api_data: Dict[str, Any], account_profile_id: int) -> BusinessGoal:
    """Transform API business goal data to BusinessGoal model instance."""
    return BusinessGoal(account_profile_id=account_profile_id, goal=api_data, created_at=datetime.now(timezone.utc))


def transform_affiliate_redirect_program(api_data: Dict[str, Any], affiliate_redirect_id: int) -> AffiliateRedirectProgram:
    """Transform API affiliate redirect program data to AffiliateRedirectProgram model instance."""
    return AffiliateRedirectProgram(affiliate_redirect_id=affiliate_redirect_id, program_id=api_data, created_at=datetime.now(timezone.utc))


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
                    email_address = transform_email_address(email)
                else:
                    email_address = transform_email_address(email.__dict__)
                contact.email_addresses.append(email_address)
            except Exception as e:
                logger.error(f"Error transforming email address for contact {contact.id}: {str(e)}")

    # Handle phone numbers
    if 'phone_numbers' in api_data:
        for phone in api_data['phone_numbers']:
            try:
                if isinstance(phone, dict):
                    phone_number = transform_phone_number(phone)
                else:
                    phone_number = transform_phone_number(phone.__dict__)
                contact.phone_numbers.append(phone_number)
            except Exception as e:
                logger.error(f"Error transforming phone number for contact {contact.id}: {str(e)}")

    # Handle addresses
    if 'addresses' in api_data:
        for address in api_data['addresses']:
            try:
                if isinstance(address, dict):
                    address_obj = transform_address(address)
                else:
                    address_obj = transform_address(address.__dict__)
                contact.addresses.append(address_obj)
            except Exception as e:
                logger.error(f"Error transforming address for contact {contact.id}: {str(e)}")

    # Handle fax numbers
    if 'fax_numbers' in api_data:
        for fax in api_data['fax_numbers']:
            try:
                if isinstance(fax, dict):
                    fax_number = transform_fax_number(fax)
                else:
                    fax_number = transform_fax_number(fax.__dict__)
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
    order = transform_order(api_data)

    # Transform order items
    if 'items' in api_data:
        order.items = [transform_order_item(item) for item in api_data['items']]

    return order


def transform_account_profile(api_data: Dict[str, Any]) -> AccountProfile:
    """Transform API account profile data to AccountProfile model instance."""
    profile = AccountProfile(id=api_data.get('id'), address_id=api_data.get('address_id'), business_primary_color=api_data.get('business_primary_color'), business_secondary_color=api_data.get('business_secondary_color'), business_type=api_data.get('business_type'), currency_code=api_data.get('currency_code'), email=api_data.get('email'), language_tag=api_data.get('language_tag'), logo_url=api_data.get('logo_url'), name=api_data.get('name'), phone=api_data.get('phone'), phone_ext=api_data.get('phone_ext'), time_zone=api_data.get('time_zone'), website=api_data.get('website'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)

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


def transform_affiliate(api_data: Dict[str, Any]) -> Affiliate:
    """Transform API affiliate data to Affiliate model instance."""
    return Affiliate(id=api_data.get('id'), code=api_data.get('code'), contact_id=api_data.get('contact_id'), name=api_data.get('name'), notify_on_lead=api_data.get('notify_on_lead', False), notify_on_sale=api_data.get('notify_on_sale', False), parent_id=api_data.get('parent_id'), status=api_data.get('status'), track_leads_for=api_data.get('track_leads_for'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_affiliate_commission(api_data: Dict[str, Any]) -> AffiliateCommission:
    """Transform API affiliate commission data to AffiliateCommission model instance."""
    return AffiliateCommission(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount_earned=api_data.get('amount_earned'), contact_id=api_data.get('contact_id'), contact_first_name=api_data.get('contact_first_name'), contact_last_name=api_data.get('contact_last_name'), date_earned=datetime.fromisoformat(api_data.get('date_earned')) if api_data.get('date_earned') else None, description=api_data.get('description'), invoice_id=api_data.get('invoice_id'), product_name=api_data.get('product_name'), sales_affiliate_id=api_data.get('sales_affiliate_id'), sold_by_first_name=api_data.get('sold_by_first_name'), sold_by_last_name=api_data.get('sold_by_last_name'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_affiliate_program(api_data: Dict[str, Any]) -> AffiliateProgram:
    """Transform API affiliate program data to AffiliateProgram model instance."""
    return AffiliateProgram(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), name=api_data.get('name'), notes=api_data.get('notes'), priority=api_data.get('priority'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_affiliate_redirect(api_data: Dict[str, Any]) -> AffiliateRedirect:
    """Transform API affiliate redirect data to AffiliateRedirect model instance."""
    redirect = AffiliateRedirect(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), local_url_code=api_data.get('local_url_code'), name=api_data.get('name'), redirect_url=api_data.get('redirect_url'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)

    # Transform program IDs
    if 'program_ids' in api_data:
        redirect.program_ids = []
        for program_id in api_data['program_ids']:
            try:
                redirect.program_ids.append(transform_affiliate_redirect_program(program_id, redirect.id))
            except Exception as e:
                logger.error(f"Error transforming program ID for redirect {redirect.id}: {str(e)}")
                continue

    return redirect


def transform_affiliate_summary(api_data: Dict[str, Any]) -> AffiliateSummary:
    """Transform API affiliate summary data to AffiliateSummary model instance."""
    return AffiliateSummary(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount_earned=api_data.get('amount_earned'), balance=api_data.get('balance'), clawbacks=api_data.get('clawbacks'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None, modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None)


def transform_affiliate_clawback(api_data: Dict[str, Any]) -> AffiliateClawback:
    """Transform API affiliate clawback data to AffiliateClawback model instance."""
    return AffiliateClawback(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount=api_data.get('amount'), contact_id=api_data.get('contact_id'), date_earned=datetime.fromisoformat(api_data.get('date_earned')) if api_data.get('date_earned') else None, description=api_data.get('description'), family_name=api_data.get('family_name'), given_name=api_data.get('given_name'), invoice_id=api_data.get('invoice_id'), product_name=api_data.get('product_name'), sale_affiliate_id=api_data.get('sale_affiliate_id'), sold_by_family_name=api_data.get('sold_by_family_name'), sold_by_given_name=api_data.get('sold_by_given_name'), subscription_plan_name=api_data.get('subscription_plan_name'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_affiliate_payment(api_data: Dict[str, Any]) -> AffiliatePayment:
    """Transform API affiliate payment data to AffiliatePayment model instance."""
    return AffiliatePayment(id=api_data.get('id'), affiliate_id=api_data.get('affiliate_id'), amount=api_data.get('amount'), date=datetime.fromisoformat(api_data.get('date')) if api_data.get('date') else None, notes=api_data.get('notes'), type=api_data.get('type'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)


def transform_applied_tag(api_data: Dict[str, Any]) -> Tag:
    """Transform API applied tag data to Tag model instance."""
    tag = api_data.get('tag')
    return Tag(id=tag.get('id'), name=tag.get('name'), description=tag.get('description'), category=tag.get('category'), created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None)
