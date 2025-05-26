import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey,
    JSON, Text, Table, UniqueConstraint, Enum, BigInteger
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def utc_now():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


# Association Tables
contact_tag = Table(
    'contact_tag',
    Base.metadata,
    Column('contact_id', Integer, ForeignKey('contacts.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True),
    Column('created_at', DateTime, default=utc_now)
)


class AddressType(enum.Enum):
    BILLING = "BILLING"
    SHIPPING = "SHIPPING"
    OTHER = "OTHER"


class ContactAddress(Base):
    __tablename__ = 'contact_addresses'

    id = Column(Integer, primary_key=True)
    country_code = Column(String(10))
    field = Column(Enum(AddressType), nullable=False)
    line1 = Column(String(255))
    line2 = Column(String(255))
    locality = Column(String(100))
    postal_code = Column(String(20))
    region = Column(String(100))
    zip_code = Column(String(20))
    zip_four = Column(String(10))


class AccountProfile(Base):
    __tablename__ = 'account_profiles'

    id = Column(Integer, primary_key=True)
    address_id = Column(Integer, ForeignKey('addresses.id'))
    business_goals = Column(JSON)  # Array of strings
    business_primary_color = Column(String(50))
    business_secondary_color = Column(String(50))
    business_type = Column(String(100))
    currency_code = Column(String(10))
    email = Column(String(255))
    language_tag = Column(String(50))
    logo_url = Column(String(255))
    name = Column(String(200))
    phone = Column(String(50))
    phone_ext = Column(String(20))
    time_zone = Column(String(50))
    website = Column(String(255))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    address = relationship("Address")


class Affiliate(Base):
    __tablename__ = 'affiliates'

    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    name = Column(String(200))
    notify_on_lead = Column(Boolean, default=False)
    notify_on_sale = Column(Boolean, default=False)
    parent_id = Column(Integer, ForeignKey('affiliates.id'))
    status = Column(String(50))
    track_leads_for = Column(Integer)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact")
    parent = relationship("Affiliate", remote_side=[id])
    commissions = relationship("AffiliateCommission", back_populates="affiliate")
    programs = relationship("AffiliateProgram", back_populates="affiliate")
    redirects = relationship("AffiliateRedirect", back_populates="affiliate")
    clawbacks = relationship("AffiliateClawback", back_populates="affiliate")
    payments = relationship("AffiliatePayment", back_populates="affiliate")


class AffiliateCommission(Base):
    __tablename__ = 'affiliate_commissions'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount_earned = Column(Float)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    contact_first_name = Column(String(100))
    contact_last_name = Column(String(100))
    date_earned = Column(DateTime)
    description = Column(Text)
    invoice_id = Column(Integer)
    product_name = Column(String(200))
    sales_affiliate_id = Column(Integer)
    sold_by_first_name = Column(String(100))
    sold_by_last_name = Column(String(100))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="commissions")
    contact = relationship("Contact")


class AffiliateProgram(Base):
    __tablename__ = 'affiliate_programs'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    name = Column(String(200))
    notes = Column(Text)
    priority = Column(Integer)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="programs")


class AffiliateRedirect(Base):
    __tablename__ = 'affiliate_redirects'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    local_url_code = Column(String(100))
    name = Column(String(200))
    program_ids = Column(JSON)  # Array of integers
    redirect_url = Column(String(255))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="redirects")


class AffiliateSummary(Base):
    __tablename__ = 'affiliate_summaries'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount_earned = Column(Float)
    balance = Column(Float)
    clawbacks = Column(Float)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate")


class AffiliateClawback(Base):
    __tablename__ = 'affiliate_clawbacks'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount = Column(Float)  # API uses double format
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    date_earned = Column(DateTime)  # API returns string, we store as DateTime
    description = Column(Text)
    family_name = Column(String(100))  # API uses family_name instead of contact_last_name
    given_name = Column(String(100))  # API uses given_name instead of contact_first_name
    invoice_id = Column(Integer)
    product_name = Column(String(200))
    sale_affiliate_id = Column(Integer)  # API uses sale_affiliate_id
    sold_by_family_name = Column(String(100))  # API uses sold_by_family_name
    sold_by_given_name = Column(String(100))  # API uses sold_by_given_name
    subscription_plan_name = Column(String(200))  # Added from API spec
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="clawbacks")
    contact = relationship("Contact")


class AffiliatePayment(Base):
    __tablename__ = 'affiliate_payments'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount = Column(Float)
    date = Column(DateTime)
    notes = Column(Text)
    type = Column(String(50))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="payments")


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True)
    given_name = Column(String(100))
    family_name = Column(String(100))
    middle_name = Column(String(100))
    company_name = Column(String(200))
    job_title = Column(String(200))
    email_opted_in = Column(Boolean, default=False)
    email_status = Column(String(50))
    score_value = Column(String(50))
    owner_id = Column(Integer)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    last_updated_utc_millis = Column(BigInteger)

    # Relationships with cascade options
    email_addresses = relationship("EmailAddress", back_populates="contact", cascade="all, delete-orphan")
    phone_numbers = relationship("PhoneNumber", back_populates="contact", cascade="all, delete-orphan")
    addresses = relationship("Address", back_populates="contact", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=contact_tag, back_populates="contacts")
    custom_field_values = relationship("CustomFieldValue", back_populates="contact", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="contact", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="contact", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="contact", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="contact", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="contact", cascade="all, delete-orphan")


class EmailAddress(Base):
    __tablename__ = 'email_addresses'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    email = Column(String(255), nullable=False)
    field = Column(String(50))  # e.g., "EMAIL1", "EMAIL2"
    type = Column(String(50))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="email_addresses")


class PhoneNumber(Base):
    __tablename__ = 'phone_numbers'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    number = Column(String(50), nullable=False)
    field = Column(String(50))  # e.g., "PHONE1", "PHONE2"
    type = Column(String(50))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="phone_numbers")


class Address(Base):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    country_code = Column(String(10))  # Changed from country
    field = Column(Enum(AddressType), nullable=False)  # Changed to use enum
    line1 = Column(String(255))  # Changed from street_address
    line2 = Column(String(255))  # Added
    locality = Column(String(100))  # Changed from city
    postal_code = Column(String(20))
    region = Column(String(100))  # Changed from state
    zip_code = Column(String(20))  # Added
    zip_four = Column(String(10))  # Added
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="addresses")


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contacts = relationship("Contact", secondary=contact_tag, back_populates="tags")


class CustomField(Base):
    __tablename__ = 'custom_fields'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)
    options = Column(JSON)  # Array of string options
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    values = relationship("CustomFieldValue", back_populates="custom_field")


class CustomFieldValue(Base):
    __tablename__ = 'custom_field_values'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    custom_field_id = Column(Integer, ForeignKey('custom_fields.id'))
    value = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="custom_field_values")
    custom_field = relationship("CustomField", back_populates="values")

    __table_args__ = (
        UniqueConstraint('contact_id', 'custom_field_id', name='uix_contact_custom_field'),
    )


class Opportunity(Base):
    __tablename__ = 'opportunities'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    title = Column(String(200), nullable=False)
    stage = Column(String(100))
    value = Column(Float)
    probability = Column(Float)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="opportunities")


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    product_name = Column(String(200), nullable=False)
    product_sku = Column(String(100), unique=True)
    subscription_only = Column(Boolean, default=False)
    plan_description = Column(Text)
    frequency = Column(String(50))
    price = Column(Float)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    subscriptions = relationship("Subscription", back_populates="product")


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    order_number = Column(String(50))  # Added from API spec
    order_date = Column(DateTime, nullable=False)
    order_status = Column(String(50))
    order_total = Column(Float)
    order_type = Column(String(50))  # Added from API spec
    payment_plan_id = Column(Integer)  # Added from API spec
    payment_type = Column(String(50))  # Added from API spec
    subscription_plan_id = Column(Integer)  # Added from API spec
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text)  # Added from API spec
    subscription_plan_id = Column(Integer)  # Added from API spec
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)  # Added from API spec

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="tasks")


class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    title = Column(String(200))
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="notes")


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    status = Column(String(50))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    sequences = relationship("CampaignSequence", back_populates="campaign")


class CampaignSequence(Base):
    __tablename__ = 'campaign_sequences'

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    name = Column(String(200), nullable=False)
    status = Column(String(50))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    campaign = relationship("Campaign", back_populates="sequences")


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    status = Column(String(50))
    next_bill_date = Column(DateTime)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="subscriptions")
    product = relationship("Product", back_populates="subscriptions")
