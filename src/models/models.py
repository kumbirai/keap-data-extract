import enum
from datetime import datetime, timezone

from sqlalchemy import (BigInteger, Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer, JSON, Numeric, String, Table, Text, UniqueConstraint, func)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


# Define all enums first
class AddressType(enum.Enum):
    BILLING = "BILLING"
    SHIPPING = "SHIPPING"
    OTHER = "OTHER"
    HOME = "HOME"
    WORK = "WORK"


class ContactSourceType(enum.Enum):
    API = "API"
    CALL = "CALL"
    EMAIL = "EMAIL"
    FORM = "FORM"
    IMPORT = "IMPORT"
    INVOICE = "INVOICE"
    ONLINE = "ONLINE"
    PHONE = "PHONE"
    SMS = "SMS"
    SYSTEM = "SYSTEM"
    WEBSITE = "WEBSITE"
    MANUAL = "MANUAL"
    SOCIAL = "SOCIAL"
    REFERRAL = "REFERRAL"
    PARTNER = "PARTNER"
    AFFILIATE = "AFFILIATE"


class ContactEmailStatus(enum.Enum):
    UNENGAGED_MARKETABLE = "UnengagedMarketable"
    SINGLE_OPT_IN = "SingleOptIn"
    DOUBLE_OPT_IN = "DoubleOptIn"
    CONFIRMED = "Confirmed"
    UNENGAGED_NON_MARKETABLE = "UnengagedNonMarketable"
    NON_MARKETABLE = "NonMarketable"
    LOCKDOWN = "Lockdown"
    BOUNCE = "Bounce"
    HARD_BOUNCE = "HardBounce"
    MANUAL = "Manual"
    ADMIN = "Admin"
    SYSTEM = "System"
    LIST_UNSUBSCRIBE = "ListUnsubscribe"
    FEEDBACK = "Feedback"
    SPAM = "Spam"
    INVALID = "Invalid"
    DEACTIVATED = "Deactivated"


class OrderSourceType(enum.Enum):
    API = "API"
    CALL = "CALL"
    EMAIL = "EMAIL"
    FORM = "FORM"
    IMPORT = "IMPORT"
    INVOICE = "INVOICE"
    ONLINE = "ONLINE"
    PHONE = "PHONE"
    SMS = "SMS"
    SYSTEM = "SYSTEM"
    WEBSITE = "WEBSITE"
    MANUAL = "MANUAL"
    SOCIAL = "SOCIAL"
    REFERRAL = "REFERRAL"
    PARTNER = "PARTNER"
    AFFILIATE = "AFFILIATE"


class OrderStatus(enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    VOID = "VOID"
    PROCESSING = "PROCESSING"
    ON_HOLD = "ON_HOLD"


class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    DEFERRED = "DEFERRED"
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"


class TaskPriority(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class OpportunityStage(enum.Enum):
    QUALIFIED = "Qualified"
    PROPOSAL = "Proposal"
    NEGOTIATION = "Negotiation"
    CLOSED_WON = "Closed Won"
    CLOSED_LOST = "Closed Lost"
    DISCOVERY = "Discovery"
    PRESENTATION = "Presentation"
    DECISION = "Decision"
    CONTRACT = "Contract"
    IMPLEMENTATION = "Implementation"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "Active"
    CANCELLED = "Cancelled"
    EXPIRED = "Expired"
    PAUSED = "Paused"
    TRIAL = "Trial"
    PAST_DUE = "Past Due"
    PENDING = "Pending"
    FAILED = "Failed"
    ON_HOLD = "On Hold"


class CampaignStatus(enum.Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"
    SCHEDULED = "Scheduled"
    STOPPED = "Stopped"


class AffiliateStatus(enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    SUSPENDED = "Suspended"
    TERMINATED = "Terminated"


class CustomFieldType(enum.Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    DROPDOWN = "DROPDOWN"
    MULTISELECT = "MULTISELECT"
    RADIO = "RADIO"
    CHECKBOX = "CHECKBOX"
    URL = "URL"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    CURRENCY = "CURRENCY"
    PERCENT = "PERCENT"
    SOCIAL = "SOCIAL"
    ADDRESS = "ADDRESS"
    IMAGE = "IMAGE"
    FILE = "FILE"
    LIST = "LIST"
    MULTILINE = "MULTILINE"
    PASSWORD = "PASSWORD"
    TIME = "TIME"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"
    HIDDEN = "HIDDEN"


class NoteType(enum.Enum):
    CALL = "Call"
    EMAIL = "Email"
    FAX = "Fax"
    LETTER = "Letter"
    MEETING = "Meeting"
    OTHER = "Other"
    TASK = "Task"
    SMS = "SMS"
    SOCIAL = "Social"
    CHAT = "Chat"
    VOICEMAIL = "Voicemail"
    WEBSITE = "Website"
    FORM = "Form"
    APPOINTMENT = "Appointment"
    CAMPAIGN = "Campaign"
    CONTACT = "Contact"
    DEAL = "Deal"
    DOCUMENT = "Document"
    FILE = "File"
    FOLLOW_UP = "Follow Up"
    INVOICE = "Invoice"
    ORDER = "Order"
    PRODUCT = "Product"
    PURCHASE = "Purchase"
    RECURRING_ORDER = "Recurring Order"
    REFERRAL = "Referral"
    REFUND = "Refund"
    SUBSCRIPTION = "Subscription"
    SURVEY = "Survey"
    TAG = "Tag"
    TEMPLATE = "Template"
    TRANSACTION = "Transaction"
    USER = "User"
    WEBFORM = "Webform"
    WORKFLOW = "Workflow"


# Join tables
contact_tag = Table('contact_tag', Base.metadata, Column('contact_id', Integer, ForeignKey('contacts.id'), primary_key=True), Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True), Column('created_at', DateTime, default=utc_now))

contact_opportunity = Table('contact_opportunity', Base.metadata, Column('contact_id', Integer, ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True), Column('opportunity_id', Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

contact_task = Table('contact_task', Base.metadata, Column('contact_id', Integer, ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True), Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

contact_note = Table('contact_note', Base.metadata, Column('contact_id', Integer, ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True), Column('note_id', Integer, ForeignKey('notes.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

contact_order = Table('contact_order', Base.metadata, Column('contact_id', Integer, ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True), Column('order_id', Integer, ForeignKey('orders.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

contact_subscription = Table('contact_subscription', Base.metadata, Column('contact_id', Integer, ForeignKey('contacts.id', ondelete='CASCADE'), primary_key=True), Column('subscription_id', Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

order_item = Table('order_item', Base.metadata, Column('order_id', Integer, ForeignKey('orders.id', ondelete='CASCADE'), primary_key=True), Column('item_id', Integer, ForeignKey('order_items.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

product_order_item = Table('product_order_item', Base.metadata, Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True), Column('order_item_id', Integer, ForeignKey('order_items.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

product_subscription = Table('product_subscription', Base.metadata, Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True), Column('subscription_id', Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

campaign_sequence = Table('campaign_sequence', Base.metadata, Column('campaign_id', Integer, ForeignKey('campaigns.id', ondelete='CASCADE'), primary_key=True), Column('sequence_id', Integer, ForeignKey('campaign_sequences.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))

order_transaction = Table('order_transaction', Base.metadata, Column('order_id', Integer, ForeignKey('orders.id', ondelete='CASCADE'), primary_key=True), Column('transaction_id', Integer, ForeignKey('order_transactions.id', ondelete='CASCADE'), primary_key=True), Column('created_at', DateTime, default=utc_now))


class AccountProfile(Base):
    __tablename__ = 'account_profiles'

    id = Column(Integer, primary_key=True)
    address_id = Column(Integer, ForeignKey('contact_addresses.id'))
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
    address = relationship("ContactAddress", foreign_keys=[address_id])
    business_goals = relationship("BusinessGoal", back_populates="account_profile", cascade="all, delete-orphan", foreign_keys="BusinessGoal.account_profile_id")

    def __repr__(self):
        return f"<AccountProfile(id={self.id}, name='{self.name}', business_type='{self.business_type}')>"


class Affiliate(Base):
    __tablename__ = 'affiliates'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    parent_id = Column(Integer)
    status = Column(Enum(AffiliateStatus))
    code = Column(String(50))
    name = Column(String(200))
    email = Column(String(255))
    company = Column(String(200))
    website = Column(String(255))
    phone = Column(String(50))
    address1 = Column(String(255))
    address2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    tax_id = Column(String(50))
    payment_email = Column(String(255))
    notify_on_lead = Column(Boolean, nullable=True)
    notify_on_sale = Column(Boolean, nullable=True)
    track_leads_for = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    contact = relationship("Contact", back_populates="affiliate")
    parent = relationship("Affiliate", remote_side=[id], primaryjoin="foreign(Affiliate.parent_id)==Affiliate.id", back_populates="children")
    children = relationship("Affiliate", back_populates="parent", primaryjoin="Affiliate.id==foreign(Affiliate.parent_id)")
    commissions = relationship("AffiliateCommission", back_populates="affiliate", cascade="all, delete-orphan")
    programs = relationship("AffiliateProgram", back_populates="affiliate", cascade="all, delete-orphan")
    redirects = relationship("AffiliateRedirect", back_populates="affiliate", cascade="all, delete-orphan")
    clawbacks = relationship("AffiliateClawback", back_populates="affiliate", cascade="all, delete-orphan")
    payments = relationship("AffiliatePayment", back_populates="affiliate", cascade="all, delete-orphan")
    summary = relationship("AffiliateSummary", back_populates="affiliate", uselist=False, cascade="all, delete-orphan")
    lead_orders = relationship("Order", back_populates="lead_affiliate", foreign_keys="Order.lead_affiliate_id", primaryjoin="Affiliate.id==Order.lead_affiliate_id", post_update=True)
    sales_orders = relationship("Order", back_populates="sales_affiliate", foreign_keys="Order.sales_affiliate_id", primaryjoin="Affiliate.id==Order.sales_affiliate_id", post_update=True)

    def __repr__(self):
        return f"<Affiliate(id={self.id}, code='{self.code}', name='{self.name}', status='{self.status}')>"


class AffiliateCommission(Base):
    __tablename__ = 'affiliate_commissions'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount_earned = Column(Numeric(10, 2))
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
    affiliate = relationship("Affiliate", back_populates="commissions", foreign_keys=[affiliate_id])
    contact = relationship("Contact", foreign_keys=[contact_id])

    def __repr__(self):
        return f"<AffiliateCommission(id={self.id}, affiliate_id={self.affiliate_id}, amount_earned={self.amount_earned})>"


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
    affiliate = relationship("Affiliate", back_populates="programs", foreign_keys=[affiliate_id])

    def __repr__(self):
        return f"<AffiliateProgram(id={self.id}, affiliate_id={self.affiliate_id}, name='{self.name}', priority={self.priority})>"


class AffiliateRedirect(Base):
    __tablename__ = 'affiliate_redirects'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    local_url_code = Column(String(100))
    name = Column(String(200))
    redirect_url = Column(String(255))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="redirects", foreign_keys=[affiliate_id])
    program_ids = relationship("AffiliateRedirectProgram", back_populates="affiliate_redirect", cascade="all, delete-orphan", foreign_keys="AffiliateRedirectProgram.affiliate_redirect_id")

    def __repr__(self):
        return f"<AffiliateRedirect(id={self.id}, affiliate_id={self.affiliate_id}, name='{self.name}', local_url_code='{self.local_url_code}')>"


class AffiliateSummary(Base):
    __tablename__ = 'affiliate_summaries'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount_earned = Column(Numeric(10, 2))
    balance = Column(Numeric(10, 2))
    clawbacks = Column(Numeric(10, 2))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="summary", foreign_keys=[affiliate_id])

    def __repr__(self):
        return f"<AffiliateSummary(id={self.id}, affiliate_id={self.affiliate_id}, amount_earned={self.amount_earned}, balance={self.balance})>"


class AffiliateClawback(Base):
    __tablename__ = 'affiliate_clawbacks'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount = Column(Numeric(10, 2))
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    date_earned = Column(DateTime)
    description = Column(Text)
    family_name = Column(String(100))
    given_name = Column(String(100))
    invoice_id = Column(Integer)
    product_name = Column(String(200))
    sale_affiliate_id = Column(Integer)
    sold_by_family_name = Column(String(100))
    sold_by_given_name = Column(String(100))
    subscription_plan_name = Column(String(200))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="clawbacks", foreign_keys=[affiliate_id])
    contact = relationship("Contact", foreign_keys=[contact_id])

    def __repr__(self):
        return f"<AffiliateClawback(id={self.id}, affiliate_id={self.affiliate_id}, amount={self.amount})>"


class AffiliatePayment(Base):
    __tablename__ = 'affiliate_payments'

    id = Column(Integer, primary_key=True)
    affiliate_id = Column(Integer, ForeignKey('affiliates.id'))
    amount = Column(Numeric(10, 2))
    date = Column(DateTime)
    notes = Column(Text)
    type = Column(String(50))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate", back_populates="payments", foreign_keys=[affiliate_id])

    def __repr__(self):
        return f"<AffiliatePayment(id={self.id}, affiliate_id={self.affiliate_id}, amount={self.amount})>"


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True)
    given_name = Column(String(100))
    family_name = Column(String(100))
    middle_name = Column(String(100))
    company_name = Column(String(200))
    job_title = Column(String(200))
    email_opted_in = Column(Boolean, default=False)
    email_status = Column(Enum(ContactEmailStatus))
    score_value = Column(String(50))
    owner_id = Column(Integer)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    last_updated_utc_millis = Column(BigInteger)
    anniversary = Column(DateTime)
    birthday = Column(DateTime)
    contact_type = Column(String(50))
    duplicate_option = Column(String(50))
    lead_source_id = Column(Integer)
    preferred_locale = Column(String(50))
    preferred_name = Column(String(100))
    source_type = Column(Enum(ContactSourceType))
    spouse_name = Column(String(100))
    time_zone = Column(String(50))
    website = Column(String(255))
    year_created = Column(Integer)

    # Relationships with cascade options
    email_addresses = relationship("EmailAddress", back_populates="contact", cascade="all, delete-orphan")
    phone_numbers = relationship("PhoneNumber", back_populates="contact", cascade="all, delete-orphan")
    addresses = relationship("ContactAddress", back_populates="contact", cascade="all, delete-orphan")
    fax_numbers = relationship("FaxNumber", back_populates="contact", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=contact_tag, back_populates="contacts", cascade="save-update, merge")
    custom_field_values = relationship("ContactCustomFieldValue", back_populates="contact", cascade="all, delete-orphan", foreign_keys="ContactCustomFieldValue.contact_id")
    opportunities = relationship("Opportunity", secondary="contact_opportunity", back_populates="contacts", cascade="none")
    tasks = relationship("Task", secondary="contact_task", back_populates="contacts", cascade="none")
    notes = relationship("Note", secondary="contact_note", back_populates="contacts", cascade="none")
    orders = relationship("Order", secondary="contact_order", back_populates="contacts", cascade="none")
    subscriptions = relationship("Subscription", secondary="contact_subscription", back_populates="contacts", cascade="none")
    credit_cards = relationship("CreditCard", back_populates="contact", cascade="save-update, merge, delete, delete-orphan")
    affiliate = relationship("Affiliate", back_populates="contact", uselist=False, cascade="all, delete-orphan")
    direct_orders = relationship("Order", back_populates="contact", foreign_keys="Order.contact_id")

    def __repr__(self):
        return f"<Contact(id={self.id}, given_name='{self.given_name}', family_name='{self.family_name}', company_name='{self.company_name}')>"


class EmailAddress(Base):
    __tablename__ = 'email_addresses'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    field = Column(String(50))  # e.g., "EMAIL1", "EMAIL2"
    type = Column(String(50))
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="email_addresses")

    def __repr__(self):
        return f"<EmailAddress(id={self.id}, email='{self.email}', field='{self.field}')>"


class PhoneNumber(Base):
    __tablename__ = 'phone_numbers'

    id = Column(Integer, primary_key=True)
    number = Column(String(50), nullable=False)
    field = Column(String(50))  # e.g., "PHONE1", "PHONE2"
    type = Column(String(50))
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="phone_numbers")

    def __repr__(self):
        return f"<PhoneNumber(id={self.id}, number='{self.number}', field='{self.field}')>"


class ContactAddress(Base):
    __tablename__ = 'contact_addresses'

    id = Column(Integer, primary_key=True)
    country_code = Column(String(10))  # Changed from country
    field = Column(Enum(AddressType), nullable=False)  # Changed to use enum
    line1 = Column(String(255))  # Changed from street_address
    line2 = Column(String(255))  # Added
    locality = Column(String(100))  # Changed from city
    postal_code = Column(String(20))
    region = Column(String(100))  # Changed from state
    zip_code = Column(String(20))  # Added
    zip_four = Column(String(10))  # Added
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="addresses")

    def __repr__(self):
        return f"<ContactAddress(id={self.id}, field='{self.field}', locality='{self.locality}')>"


class TagCategory(Base):
    __tablename__ = 'tag_categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    tags = relationship("Tag", back_populates="category")

    def __repr__(self):
        return f"<TagCategory(id={self.id}, name='{self.name}')>"


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey('tag_categories.id'))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    category = relationship("TagCategory", back_populates="tags")
    contacts = relationship("Contact", secondary=contact_tag, back_populates="tags")

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}', category_id={self.category_id})>"


class CustomFieldMetaData(Base):
    __tablename__ = 'custom_field_metadata'

    id = Column(Integer, primary_key=True)
    custom_field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    label = Column(String(255))
    description = Column(Text)
    data_type = Column(String(50))  # string, number, date, etc.
    is_required = Column(Boolean, default=False)
    is_read_only = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    custom_field = relationship("CustomField", back_populates="field_metadata", foreign_keys=[custom_field_id])

    def __repr__(self):
        return f"<CustomFieldMetaData(id={self.id}, label='{self.label}', data_type='{self.data_type}')>"


class CustomField(Base):
    __tablename__ = 'custom_fields'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=True)
    type = Column(Enum(CustomFieldType, values_callable=lambda obj: [e.value for e in obj]), nullable=True)
    options = Column(JSON, nullable=True)  # Array of string options for dropdown/multiselect/radio fields
    # Additional fields from API response
    label = Column(String(255), nullable=True)  # Human-readable label
    field_name = Column(String(100), nullable=True)  # Internal field name from API
    record_type = Column(String(50), nullable=True)  # e.g., "CONTACT", "OPPORTUNITY", etc.
    default_value = Column(String(255), nullable=True)  # Default value for the field
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    values = relationship("ContactCustomFieldValue", back_populates="custom_field", cascade="all, delete-orphan", foreign_keys="ContactCustomFieldValue.custom_field_id")
    field_metadata = relationship("CustomFieldMetaData", back_populates="custom_field", uselist=False, cascade="all, delete-orphan", foreign_keys="CustomFieldMetaData.custom_field_id")
    opportunity_values = relationship("OpportunityCustomFieldValue", back_populates="custom_field", cascade="all, delete-orphan", foreign_keys="OpportunityCustomFieldValue.custom_field_id")
    order_values = relationship("OrderCustomFieldValue", back_populates="custom_field", cascade="all, delete-orphan", foreign_keys="OrderCustomFieldValue.custom_field_id")
    subscription_values = relationship("SubscriptionCustomFieldValue", back_populates="custom_field", cascade="all, delete-orphan", foreign_keys="SubscriptionCustomFieldValue.custom_field_id")
    note_values = relationship("NoteCustomFieldValue", back_populates="custom_field", cascade="all, delete-orphan", foreign_keys="NoteCustomFieldValue.custom_field_id")

    def __repr__(self):
        return f"<CustomField(id={self.id}, name='{self.name}', type='{self.type}')>"


class ContactCustomFieldValue(Base):
    __tablename__ = 'contact_custom_field_values'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'))
    custom_field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="custom_field_values", foreign_keys=[contact_id])
    custom_field = relationship("CustomField", back_populates="values", foreign_keys=[custom_field_id])

    __table_args__ = (UniqueConstraint('contact_id', 'custom_field_id', name='uix_contact_custom_field'),)

    def __repr__(self):
        return f"<ContactCustomFieldValue(id={self.id}, contact_id={self.contact_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class OpportunityCustomFieldValue(Base):
    __tablename__ = 'opportunity_custom_field_values'

    id = Column(Integer, primary_key=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id', ondelete='CASCADE'))
    custom_field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="custom_field_values", foreign_keys=[opportunity_id])
    custom_field = relationship("CustomField", back_populates="opportunity_values", foreign_keys=[custom_field_id])

    __table_args__ = (UniqueConstraint('opportunity_id', 'custom_field_id', name='uix_opportunity_custom_field'),)

    def __repr__(self):
        return f"<OpportunityCustomFieldValue(id={self.id}, opportunity_id={self.opportunity_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class OrderCustomFieldValue(Base):
    __tablename__ = 'order_custom_field_values'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'))
    custom_field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    order = relationship("Order", back_populates="custom_field_values", foreign_keys=[order_id])
    custom_field = relationship("CustomField", back_populates="order_values", foreign_keys=[custom_field_id])

    __table_args__ = (UniqueConstraint('order_id', 'custom_field_id', name='uix_order_custom_field'),)

    def __repr__(self):
        return f"<OrderCustomFieldValue(id={self.id}, order_id={self.order_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class SubscriptionCustomFieldValue(Base):
    __tablename__ = 'subscription_custom_field_values'

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='CASCADE'))
    custom_field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    subscription = relationship("Subscription", back_populates="custom_field_values", foreign_keys=[subscription_id])
    custom_field = relationship("CustomField", back_populates="subscription_values", foreign_keys=[custom_field_id])

    __table_args__ = (UniqueConstraint('subscription_id', 'custom_field_id', name='uix_subscription_custom_field'),)

    def __repr__(self):
        return f"<SubscriptionCustomFieldValue(id={self.id}, subscription_id={self.subscription_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    job_recurring_id = Column(Integer)
    name = Column(String(200))
    description = Column(Text)
    type = Column(String(50))
    notes = Column(Text)
    quantity = Column(Integer)
    cost = Column(Numeric(10, 2))
    price = Column(Numeric(10, 2))
    discount = Column(Numeric(10, 2))
    special_id = Column(Integer)
    special_amount = Column(Numeric(10, 2))
    special_pct_or_amt = Column(Integer)
    product_id = Column(Integer, ForeignKey('products.id'))
    subscription_plan_id = Column(Integer, ForeignKey('subscription_plans.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="items", foreign_keys=[order_id])
    product = relationship("Product", back_populates="order_items", foreign_keys=[product_id])
    subscription_plan = relationship("SubscriptionPlan", back_populates="order_items", foreign_keys=[subscription_plan_id])

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, name='{self.name}', price={self.price})>"


class OrderPayment(Base):
    __tablename__ = 'order_payments'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'))
    amount = Column(Numeric(10, 2), nullable=False)
    note = Column(Text)
    invoice_id = Column(Integer)
    payment_id = Column(Integer)
    pay_date = Column(DateTime, nullable=False)
    pay_status = Column(String(50))
    last_updated = Column(DateTime)
    skip_commission = Column(Boolean, default=False)
    refund_invoice_payment_id = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    order = relationship("Order", back_populates="payments", foreign_keys=[order_id])

    def __repr__(self):
        return f"<OrderPayment(id={self.id}, order_id={self.order_id}, amount={self.amount}, pay_date='{self.pay_date}')>"


class OrderTransaction(Base):
    __tablename__ = 'order_transactions'

    id = Column(Integer, primary_key=True)
    test = Column(Boolean, default=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10))
    gateway = Column(String(50))
    payment_date = Column(DateTime)
    type = Column(String(50))
    status = Column(String(100))
    errors = Column(Text)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    transaction_date = Column(DateTime)
    gateway_account_name = Column(String(100))
    order_ids = Column(String(100))
    collection_method = Column(String(50))
    payment_id = Column(Integer)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    orders = relationship("Order", secondary=order_transaction, back_populates="transactions")
    contact = relationship("Contact", foreign_keys=[contact_id])

    def __repr__(self):
        return f"<OrderTransaction(id={self.id}, amount={self.amount}, type='{self.type}', status='{self.status}')>"


class Opportunity(Base):
    __tablename__ = 'opportunities'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    stage = Column(JSON)
    value = Column(Float)
    probability = Column(Float)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    next_action_date = Column(DateTime)
    next_action_notes = Column(Text)
    source_type = Column(String(50))
    source_id = Column(Integer)
    pipeline_id = Column(Integer)
    pipeline_stage_id = Column(Integer)
    owner_id = Column(Integer)
    last_updated_utc_millis = Column(BigInteger)

    # Relationships
    contacts = relationship("Contact", secondary="contact_opportunity", back_populates="opportunities")
    custom_field_values = relationship("OpportunityCustomFieldValue", back_populates="opportunity", cascade="all, delete-orphan", foreign_keys="OpportunityCustomFieldValue.opportunity_id")

    def __repr__(self):
        return f"<Opportunity(id={self.id}, title='{self.title}', stage='{self.stage}', value={self.value})>"


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    sku = Column(String(100))
    active = Column(Boolean, default=True)
    url = Column(String(255))
    product_name = Column(String(200))
    sub_category_id = Column(Integer, default=0)
    product_desc = Column(Text)
    product_price = Column(Numeric(10, 2))
    product_short_desc = Column(Text)
    subscription_only = Column(Boolean, default=False)
    status = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    options = relationship("ProductOption", back_populates="product", cascade="all, delete-orphan")
    subscription_plans = relationship("SubscriptionPlan", back_populates="product", foreign_keys="SubscriptionPlan.product_id", primaryjoin="Product.id==SubscriptionPlan.product_id")
    direct_orders = relationship("Order", back_populates="product", foreign_keys="Order.product_id", primaryjoin="Product.id==Order.product_id", post_update=True)
    order_items = relationship("OrderItem", back_populates="product", foreign_keys="OrderItem.product_id")
    subscriptions = relationship("Subscription", secondary="product_subscription", back_populates="products", lazy="dynamic")

    def __repr__(self):
        return f"<Product(id={self.id}, product_name='{self.product_name}', sku='{self.sku}')>"


class ProductOption(Base):
    __tablename__ = 'product_options'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2))
    sku = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    product = relationship("Product", back_populates="options", foreign_keys=[product_id])

    def __repr__(self):
        return f"<ProductOption(id={self.id}, product_id={self.product_id}, name='{self.name}', price={self.price})>"


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    subscription_plan_id = Column(Integer, ForeignKey('subscription_plans.id'))
    status = Column(Enum(SubscriptionStatus))
    next_bill_date = Column(DateTime)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    payment_gateway_id = Column(Integer, ForeignKey('payment_gateways.id'))
    credit_card_id = Column(Integer, ForeignKey('credit_cards.id'))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    billing_cycle = Column(String(50))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contacts = relationship("Contact", secondary="contact_subscription", back_populates="subscriptions")
    products = relationship("Product", secondary="product_subscription", back_populates="subscriptions", lazy="dynamic")
    subscription_plan = relationship("SubscriptionPlan", back_populates="subscriptions", foreign_keys=[subscription_plan_id])
    custom_field_values = relationship("SubscriptionCustomFieldValue", back_populates="subscription", cascade="all, delete-orphan", foreign_keys="SubscriptionCustomFieldValue.subscription_id")
    contact = relationship("Contact", foreign_keys=[contact_id])
    payment_gateway = relationship("PaymentGateway", foreign_keys=[payment_gateway_id])
    credit_card = relationship("CreditCard", foreign_keys=[credit_card_id])

    def __repr__(self):
        return f"<Subscription(id={self.id}, product_id={self.product_id}, status='{self.status}', next_bill_date='{self.next_bill_date}')>"


class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    name = Column(String(200))
    description = Column(Text)
    frequency = Column(String(50))
    subscription_plan_price = Column(Numeric(10, 2))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    product = relationship("Product", back_populates="subscription_plans", foreign_keys=[product_id], primaryjoin="SubscriptionPlan.product_id==Product.id")
    orders = relationship("Order", back_populates="subscription_plan", foreign_keys="Order.subscription_plan_id")
    subscriptions = relationship("Subscription", back_populates="subscription_plan", foreign_keys="Subscription.subscription_plan_id")
    order_items = relationship("OrderItem", back_populates="subscription_plan", foreign_keys="OrderItem.subscription_plan_id")

    def __repr__(self):
        return f"<SubscriptionPlan(id={self.id}, name='{self.name}', price={self.subscription_plan_price})>"


class PaymentGateway(Base):
    __tablename__ = 'payment_gateways'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    type = Column(String(50))
    is_active = Column(Boolean, default=True)
    credentials = Column(JSON)
    settings = Column(JSON)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="payment_gateway", foreign_keys="Subscription.payment_gateway_id")
    payment_plans = relationship("PaymentPlan", foreign_keys="PaymentPlan.merchant_account_id")

    def __repr__(self):
        return f"<PaymentGateway(id={self.id}, name='{self.name}', type='{self.type}')>"


class ShippingInformation(Base):
    __tablename__ = 'shipping_information'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    first_name = Column(String(100))
    middle_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(200))
    phone = Column(String(50))
    street1 = Column(String(255))
    street2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    zip = Column(String(20))
    country = Column(String(100))
    tracking_number = Column(String(100))
    carrier = Column(String(100))
    shipping_status = Column(String(50))
    shipping_date = Column(DateTime(timezone=True))
    estimated_delivery_date = Column(DateTime(timezone=True))
    invoice_to_company = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="shipping_information", foreign_keys=[order_id])

    def __repr__(self):
        return f"<ShippingInformation(id={self.id}, order_id={self.order_id}, name='{self.first_name} {self.last_name}')>"


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    status = Column(Enum(OrderStatus))
    recurring = Column(Boolean)
    total = Column(Numeric(10, 2))
    notes = Column(Text)
    terms = Column(Text)
    order_type = Column(String(50))
    source_type = Column(Enum(OrderSourceType))
    creation_date = Column(DateTime(timezone=True))
    modification_date = Column(DateTime(timezone=True))
    order_date = Column(DateTime(timezone=True))
    lead_affiliate_id = Column(Integer)
    sales_affiliate_id = Column(Integer)
    total_paid = Column(Numeric(10, 2))
    total_due = Column(Numeric(10, 2))
    refund_total = Column(Numeric(10, 2))
    allow_payment = Column(Boolean)
    allow_paypal = Column(Boolean)
    invoice_number = Column(Integer)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    product_id = Column(Integer)
    payment_gateway_id = Column(Integer, ForeignKey('payment_gateways.id'))
    subscription_plan_id = Column(Integer, ForeignKey('subscription_plans.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", foreign_keys="OrderItem.order_id")
    shipping_information = relationship("ShippingInformation", back_populates="order", uselist=False, cascade="all, delete-orphan")
    payment_plan = relationship("PaymentPlan", back_populates="order", uselist=False, cascade="all, delete-orphan")
    contacts = relationship("Contact", secondary="contact_order", back_populates="orders")
    custom_field_values = relationship("OrderCustomFieldValue", back_populates="order", cascade="all, delete-orphan", foreign_keys="OrderCustomFieldValue.order_id")
    payments = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan", foreign_keys="OrderPayment.order_id")
    transactions = relationship("OrderTransaction", secondary=order_transaction, back_populates="orders")
    subscription_plan = relationship("SubscriptionPlan", back_populates="orders", foreign_keys=[subscription_plan_id])
    contact = relationship("Contact", foreign_keys=[contact_id], back_populates="direct_orders")
    product = relationship("Product", foreign_keys=[product_id], back_populates="direct_orders", primaryjoin="Order.product_id==Product.id", post_update=True)
    lead_affiliate = relationship("Affiliate", foreign_keys=[lead_affiliate_id], back_populates="lead_orders", primaryjoin="Order.lead_affiliate_id==Affiliate.id", post_update=True)
    sales_affiliate = relationship("Affiliate", foreign_keys=[sales_affiliate_id], back_populates="sales_orders", primaryjoin="Order.sales_affiliate_id==Affiliate.id", post_update=True)

    def __repr__(self):
        return f"<Order(id={self.id}, title='{self.title}', total={self.total}, status='{self.status}')>"


class PaymentPlan(Base):
    __tablename__ = 'payment_plans'

    order_id = Column(Integer, ForeignKey('orders.id'), primary_key=True)
    auto_charge = Column(Boolean)
    credit_card_id = Column(Integer)
    days_between_payments = Column(Integer)
    initial_payment_amount = Column(Numeric(10, 2))
    initial_payment_percent = Column(Numeric(5, 2))
    initial_payment_date = Column(Date)
    number_of_payments = Column(Integer)
    merchant_account_id = Column(Integer, ForeignKey('payment_gateways.id'))
    merchant_account_name = Column(String(200))
    plan_start_date = Column(Date)
    payment_method_id = Column(String(50))
    max_charge_attempts = Column(Integer)
    days_between_retries = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="payment_plan", foreign_keys=[order_id])
    payment_gateway = relationship("PaymentGateway", foreign_keys=[merchant_account_id])

    def __repr__(self):
        return f"<PaymentPlan(order_id={self.order_id}, initial_payment_amount={self.initial_payment_amount})>"


class FaxNumber(Base):
    __tablename__ = 'fax_numbers'

    id = Column(Integer, primary_key=True)
    number = Column(String(50), nullable=False)
    field = Column(String(50))
    type = Column(String(50))
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'))
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="fax_numbers")

    def __repr__(self):
        return f"<FaxNumber(id={self.id}, number='{self.number}', field='{self.field}')>"


class BusinessGoal(Base):
    __tablename__ = 'business_goals'

    id = Column(Integer, primary_key=True)
    account_profile_id = Column(Integer, ForeignKey('account_profiles.id'))
    goal = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    account_profile = relationship("AccountProfile", back_populates="business_goals", foreign_keys=[account_profile_id])

    def __repr__(self):
        return f"<BusinessGoal(id={self.id}, goal='{self.goal}')>"


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(Enum(CampaignStatus))
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    sequences = relationship("CampaignSequence", back_populates="campaign", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class CampaignSequence(Base):
    __tablename__ = 'campaign_sequences'

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id', ondelete='CASCADE'))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50))
    sequence_number = Column(Integer)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    campaign = relationship("Campaign", back_populates="sequences")

    def __repr__(self):
        return f"<CampaignSequence(id={self.id}, campaign_id={self.campaign_id}, name='{self.name}', sequence_number={self.sequence_number})>"


class AffiliateRedirectProgram(Base):
    __tablename__ = 'affiliate_redirect_programs'

    id = Column(Integer, primary_key=True)
    affiliate_redirect_id = Column(Integer, ForeignKey('affiliate_redirects.id'))
    program_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    affiliate_redirect = relationship("AffiliateRedirect", back_populates="program_ids", foreign_keys=[affiliate_redirect_id])

    def __repr__(self):
        return f"<AffiliateRedirectProgram(id={self.id}, affiliate_redirect_id={self.affiliate_redirect_id}, program_id={self.program_id})>"


class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    title = Column(String(200))
    body = Column(Text)
    type = Column(Enum(NoteType))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    contact = relationship("Contact", back_populates="notes")
    contacts = relationship("Contact", secondary="contact_note", back_populates="notes")
    custom_field_values = relationship("NoteCustomFieldValue", back_populates="note", cascade="all, delete-orphan", foreign_keys="NoteCustomFieldValue.note_id")

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}', type='{self.type}')>"


class NoteCustomFieldValue(Base):
    __tablename__ = 'note_custom_field_values'

    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey('notes.id', ondelete='CASCADE'))
    custom_field_id = Column(Integer, ForeignKey('custom_fields.id', ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    note = relationship("Note", back_populates="custom_field_values", foreign_keys=[note_id])
    custom_field = relationship("CustomField", back_populates="note_values", foreign_keys=[custom_field_id])

    __table_args__ = (UniqueConstraint('note_id', 'custom_field_id', name='uix_note_custom_field'),)

    def __repr__(self):
        return f"<NoteCustomFieldValue(id={self.id}, note_id={self.note_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    title = Column(String(200))
    notes = Column(Text)
    priority = Column(Enum(TaskPriority))
    status = Column(Enum(TaskStatus))
    type = Column(String(50))
    due_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    contact = relationship("Contact", foreign_keys=[contact_id], back_populates="tasks")
    contacts = relationship("Contact", secondary="contact_task", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}', priority='{self.priority}')>"


class CreditCard(Base):
    __tablename__ = 'credit_cards'

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    card_type = Column(String(50))
    card_number = Column(String(20))  # Changed from String(4) to handle masked numbers
    expiration_month = Column(Integer)
    expiration_year = Column(Integer)
    card_holder_name = Column(String(100))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    modified_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    contact = relationship("Contact", back_populates="credit_cards")

    def __repr__(self):
        return f"<CreditCard(id={self.id}, contact_id={self.contact_id}, card_type='{self.card_type}', card_number='{self.card_number}')>"
