from typing import Dict, List, Any, Optional
from datetime import datetime
from ..models.models import (
    Contact, EmailAddress, PhoneNumber, Address, Tag, CustomField,
    CustomFieldValue, Opportunity, Product, Order, OrderItem,
    Task, Note, Campaign, CampaignSequence, Subscription, ContactAddress,
    AccountProfile, Affiliate, AffiliateCommission, AffiliateProgram,
    AffiliateRedirect, AffiliateSummary, AffiliateClawback, AffiliatePayment
)

def transform_contact(api_data: Dict[str, Any]) -> Contact:
    """Transform API contact data to Contact model instance."""
    return Contact(
        id=api_data.get('id'),
        given_name=api_data.get('given_name'),
        family_name=api_data.get('family_name'),
        middle_name=api_data.get('middle_name'),
        company_name=api_data.get('company'),  # API uses 'company' instead of 'company_name'
        job_title=api_data.get('job_title'),
        email_opted_in=api_data.get('email_opted_in', False),
        email_status=api_data.get('email_status'),
        score_value=api_data.get('ScoreValue'),  # API uses 'ScoreValue' instead of 'score_value'
        owner_id=api_data.get('owner_id'),
        created_at=datetime.fromisoformat(api_data.get('date_created')) if api_data.get('date_created') else None,  # API uses 'date_created'
        modified_at=datetime.fromisoformat(api_data.get('last_updated')) if api_data.get('last_updated') else None,  # API uses 'last_updated'
        last_updated_utc_millis=api_data.get('last_updated_utc_millis')
    )

def transform_email_address(api_data: Dict[str, Any], contact_id: int) -> EmailAddress:
    """Transform API email address data to EmailAddress model instance."""
    return EmailAddress(
        contact_id=contact_id,
        email=api_data.get('email'),
        field=api_data.get('field'),
        type=api_data.get('type'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_phone_number(api_data: Dict[str, Any], contact_id: int) -> PhoneNumber:
    """Transform API phone number data to PhoneNumber model instance."""
    return PhoneNumber(
        contact_id=contact_id,
        number=api_data.get('number'),
        field=api_data.get('field'),
        type=api_data.get('type'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_address(api_data: Dict[str, Any], contact_id: int) -> Address:
    """Transform API address data to Address model instance."""
    return Address(
        contact_id=contact_id,
        country_code=api_data.get('country_code'),
        field=api_data.get('field'),
        line1=api_data.get('line1'),
        line2=api_data.get('line2'),
        locality=api_data.get('locality'),
        postal_code=api_data.get('postal_code'),
        region=api_data.get('region'),
        zip_code=api_data.get('zip_code'),
        zip_four=api_data.get('zip_four'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_contact_address(api_data: Dict[str, Any]) -> ContactAddress:
    """Transform API contact address data to ContactAddress model instance."""
    return ContactAddress(
        id=api_data.get('id'),
        country_code=api_data.get('country_code'),
        field=api_data.get('field'),
        line1=api_data.get('line1'),
        line2=api_data.get('line2'),
        locality=api_data.get('locality'),
        postal_code=api_data.get('postal_code'),
        region=api_data.get('region'),
        zip_code=api_data.get('zip_code'),
        zip_four=api_data.get('zip_four')
    )

def transform_tag(api_data: Dict[str, Any]) -> Tag:
    """Transform API tag data to Tag model instance."""
    category = api_data.get('category')
    if isinstance(category, dict):
        category = category.get('name')
    return Tag(
        id=api_data.get('id'),
        name=api_data.get('name'),
        description=api_data.get('description'),
        category=category,
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_custom_field(api_data: Dict[str, Any]) -> CustomField:
    """Transform API custom field data to CustomField model instance."""
    return CustomField(
        id=api_data.get('id'),
        name=api_data.get('name'),
        type=api_data.get('type'),
        options=api_data.get('options'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_custom_field_value(api_data: Dict[str, Any], contact_id: int, custom_field_id: int) -> CustomFieldValue:
    """Transform API custom field value data to CustomFieldValue model instance."""
    return CustomFieldValue(
        contact_id=contact_id,
        custom_field_id=custom_field_id,
        value=api_data.get('value'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

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
    
    return Opportunity(
        id=api_data.get('id'),
        contact_id=api_data.get('contact_id'),
        title=title,
        stage=stage,
        value=value,
        probability=probability,
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_product(api_data: Dict[str, Any]) -> Product:
    """Transform API product data to Product model instance."""
    return Product(
        id=api_data.get('id'),
        product_name=api_data.get('product_name'),
        product_sku=api_data.get('product_sku'),
        subscription_only=api_data.get('subscription_only', False),
        plan_description=api_data.get('plan_description'),
        frequency=api_data.get('frequency'),
        price=api_data.get('price'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_order(api_data: Dict[str, Any]) -> Order:
    """Transform API order data to Order model instance."""
    return Order(
        id=api_data.get('id'),
        contact_id=api_data.get('contact_id'),
        order_date=datetime.fromisoformat(api_data.get('order_date')) if api_data.get('order_date') else None,
        order_status=api_data.get('order_status'),
        order_total=api_data.get('order_total'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_order_item(api_data: Dict[str, Any]) -> OrderItem:
    """Transform API order item data to OrderItem model instance."""
    return OrderItem(
        id=api_data.get('id'),
        order_id=api_data.get('order_id'),
        product_id=api_data.get('product_id'),
        quantity=api_data.get('quantity'),
        price=api_data.get('price'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_task(api_data: Dict[str, Any]) -> Task:
    """Transform API task data to Task model instance."""
    return Task(
        id=api_data.get('id'),
        contact_id=api_data.get('contact_id'),
        title=api_data.get('title'),
        description=api_data.get('description'),
        due_date=datetime.fromisoformat(api_data.get('due_date')) if api_data.get('due_date') else None,
        completed=api_data.get('completed', False),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_note(api_data: Dict[str, Any]) -> Note:
    """Transform API note data to Note model instance."""
    return Note(
        id=api_data.get('id'),
        contact_id=api_data.get('contact_id'),
        title=api_data.get('title'),
        body=api_data.get('body'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_campaign(api_data: Dict[str, Any]) -> Campaign:
    """Transform API campaign data to Campaign model instance."""
    return Campaign(
        id=api_data.get('id'),
        name=api_data.get('name'),
        status=api_data.get('status'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_campaign_sequence(api_data: Dict[str, Any]) -> CampaignSequence:
    """Transform API campaign sequence data to CampaignSequence model instance."""
    return CampaignSequence(
        id=api_data.get('id'),
        campaign_id=api_data.get('campaign_id'),
        name=api_data.get('name'),
        status=api_data.get('status'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_subscription(api_data: Dict[str, Any]) -> Subscription:
    """Transform API subscription data to Subscription model instance."""
    return Subscription(
        id=api_data.get('id'),
        contact_id=api_data.get('contact_id'),
        product_id=api_data.get('product_id'),
        status=api_data.get('status'),
        next_bill_date=datetime.fromisoformat(api_data.get('next_bill_date')) if api_data.get('next_bill_date') else None,
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_list_response(api_data: Dict[str, Any], transform_func: callable) -> List[Any]:
    """Transform a list response from the API using the specified transformation function."""
    # Try to find the first key whose value is a list
    items = None
    for key, value in api_data.items():
        if isinstance(value, list):
            items = value
            break
    # Fallback to 'items' key if present
    if items is None:
        items = api_data.get('items', [])
    return [transform_func(item) for item in items]

def transform_contact_with_related(api_data: Dict[str, Any]) -> Contact:
    """Transform a contact with all its related data from the API."""
    contact = transform_contact(api_data)
    
    # Transform email addresses
    if 'email_addresses' in api_data:
        contact.email_addresses = [
            transform_email_address(email, contact.id)
            for email in api_data['email_addresses']
        ]
    
    # Transform phone numbers
    if 'phone_numbers' in api_data:
        contact.phone_numbers = [
            transform_phone_number(phone, contact.id)
            for phone in api_data['phone_numbers']
        ]
    
    # Transform addresses
    if 'addresses' in api_data:
        contact.addresses = [
            transform_address(address, contact.id)
            for address in api_data['addresses']
        ]
    
    # Transform tags
    if 'tag_ids' in api_data:
        # Create Tag objects with just the IDs
        contact.tags = [
            Tag(id=tag_id)
            for tag_id in api_data['tag_ids']
        ]
    
    # Transform custom field values
    if 'custom_fields' in api_data:
        contact.custom_field_values = [
            transform_custom_field_value({
                'value': cf.get('value'),
                'created_at': cf.get('created_at'),
                'modified_at': cf.get('modified_at')
            }, contact.id, cf.get('id'))
            for cf in api_data['custom_fields']
        ]
    
    return contact

def transform_order_with_items(api_data: Dict[str, Any]) -> Order:
    """Transform API order data to Order model instance with its items."""
    order = transform_order(api_data)
    
    # Transform order items
    if 'items' in api_data:
        order.items = [
            transform_order_item(item)
            for item in api_data['items']
        ]
    
    return order

def transform_account_profile(api_data: Dict[str, Any]) -> AccountProfile:
    """Transform API account profile data to AccountProfile model instance."""
    return AccountProfile(
        id=api_data.get('id'),
        address_id=api_data.get('address_id'),
        business_goals=api_data.get('business_goals'),
        business_primary_color=api_data.get('business_primary_color'),
        business_secondary_color=api_data.get('business_secondary_color'),
        business_type=api_data.get('business_type'),
        currency_code=api_data.get('currency_code'),
        email=api_data.get('email'),
        language_tag=api_data.get('language_tag'),
        logo_url=api_data.get('logo_url'),
        name=api_data.get('name'),
        phone=api_data.get('phone'),
        phone_ext=api_data.get('phone_ext'),
        time_zone=api_data.get('time_zone'),
        website=api_data.get('website'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_affiliate(api_data: Dict[str, Any]) -> Affiliate:
    """Transform API affiliate data to Affiliate model instance."""
    return Affiliate(
        id=api_data.get('id'),
        code=api_data.get('code'),
        contact_id=api_data.get('contact_id'),
        name=api_data.get('name'),
        notify_on_lead=api_data.get('notify_on_lead', False),
        notify_on_sale=api_data.get('notify_on_sale', False),
        parent_id=api_data.get('parent_id'),
        status=api_data.get('status'),
        track_leads_for=api_data.get('track_leads_for'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_affiliate_commission(api_data: Dict[str, Any]) -> AffiliateCommission:
    """Transform API affiliate commission data to AffiliateCommission model instance."""
    return AffiliateCommission(
        id=api_data.get('id'),
        affiliate_id=api_data.get('affiliate_id'),
        amount_earned=api_data.get('amount_earned'),
        contact_id=api_data.get('contact_id'),
        contact_first_name=api_data.get('contact_first_name'),
        contact_last_name=api_data.get('contact_last_name'),
        date_earned=datetime.fromisoformat(api_data.get('date_earned')) if api_data.get('date_earned') else None,
        description=api_data.get('description'),
        invoice_id=api_data.get('invoice_id'),
        product_name=api_data.get('product_name'),
        sales_affiliate_id=api_data.get('sales_affiliate_id'),
        sold_by_first_name=api_data.get('sold_by_first_name'),
        sold_by_last_name=api_data.get('sold_by_last_name'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_affiliate_program(api_data: Dict[str, Any]) -> AffiliateProgram:
    """Transform API affiliate program data to AffiliateProgram model instance."""
    return AffiliateProgram(
        id=api_data.get('id'),
        affiliate_id=api_data.get('affiliate_id'),
        name=api_data.get('name'),
        notes=api_data.get('notes'),
        priority=api_data.get('priority'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_affiliate_redirect(api_data: Dict[str, Any]) -> AffiliateRedirect:
    """Transform API affiliate redirect data to AffiliateRedirect model instance."""
    return AffiliateRedirect(
        id=api_data.get('id'),
        affiliate_id=api_data.get('affiliate_id'),
        local_url_code=api_data.get('local_url_code'),
        name=api_data.get('name'),
        program_ids=api_data.get('program_ids'),
        redirect_url=api_data.get('redirect_url'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_affiliate_summary(api_data: Dict[str, Any]) -> AffiliateSummary:
    """Transform API affiliate summary data to AffiliateSummary model instance."""
    return AffiliateSummary(
        id=api_data.get('id'),
        affiliate_id=api_data.get('affiliate_id'),
        amount_earned=api_data.get('amount_earned'),
        balance=api_data.get('balance'),
        clawbacks=api_data.get('clawbacks'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None,
        modified_at=datetime.fromisoformat(api_data.get('modified_at')) if api_data.get('modified_at') else None
    )

def transform_affiliate_clawback(api_data: Dict[str, Any]) -> AffiliateClawback:
    """Transform API affiliate clawback data to AffiliateClawback model instance."""
    return AffiliateClawback(
        id=api_data.get('id'),
        affiliate_id=api_data.get('affiliate_id'),
        amount=api_data.get('amount'),
        contact_id=api_data.get('contact_id'),
        date_earned=datetime.fromisoformat(api_data.get('date_earned')) if api_data.get('date_earned') else None,
        description=api_data.get('description'),
        family_name=api_data.get('family_name'),
        given_name=api_data.get('given_name'),
        invoice_id=api_data.get('invoice_id'),
        product_name=api_data.get('product_name'),
        sale_affiliate_id=api_data.get('sale_affiliate_id'),
        sold_by_family_name=api_data.get('sold_by_family_name'),
        sold_by_given_name=api_data.get('sold_by_given_name'),
        subscription_plan_name=api_data.get('subscription_plan_name'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    )

def transform_affiliate_payment(api_data: Dict[str, Any]) -> AffiliatePayment:
    """Transform API affiliate payment data to AffiliatePayment model instance."""
    return AffiliatePayment(
        id=api_data.get('id'),
        affiliate_id=api_data.get('affiliate_id'),
        amount=api_data.get('amount'),
        date=datetime.fromisoformat(api_data.get('date')) if api_data.get('date') else None,
        notes=api_data.get('notes'),
        type=api_data.get('type'),
        created_at=datetime.fromisoformat(api_data.get('created_at')) if api_data.get('created_at') else None
    ) 