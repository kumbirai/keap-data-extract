import enum
from datetime import datetime, \
    timezone

from sqlalchemy import (BigInteger,
                        Boolean,
                        Column,
                        DateTime,
                        Enum,
                        Float,
                        ForeignKey,
                        Integer,
                        JSON,
                        String,
                        Table,
                        Text,
                        UniqueConstraint)
from sqlalchemy.orm import declarative_base, \
    relationship

Base = declarative_base()


def utc_now():
    """Return current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


# Association Tables
contact_tag = Table('contact_tag',
                    Base.metadata,
                    Column('contact_id',
                           Integer,
                           ForeignKey('contacts.id'),
                           primary_key=True),
                    Column('tag_id',
                           Integer,
                           ForeignKey('tags.id'),
                           primary_key=True),
                    Column('created_at',
                           DateTime,
                           default=utc_now))


class AddressType(enum.Enum):
    BILLING = "BILLING"
    SHIPPING = "SHIPPING"
    OTHER = "OTHER"


class AccountProfile(Base):
    __tablename__ = 'account_profiles'

    id = Column(Integer,
                primary_key=True)
    address_id = Column(Integer,
                        ForeignKey('addresses.id'))
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
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    address = relationship("Address")
    business_goals = relationship("BusinessGoal",
                                  back_populates="account_profile",
                                  cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AccountProfile(id={self.id}, name='{self.name}', business_type='{self.business_type}')>"


class Affiliate(Base):
    __tablename__ = 'affiliates'

    id = Column(Integer,
                primary_key=True)
    code = Column(String(100),
                  nullable=False)
    contact_id = Column(Integer,
                        ForeignKey('contacts.id'))
    name = Column(String(200))
    notify_on_lead = Column(Boolean,
                            default=False)
    notify_on_sale = Column(Boolean,
                            default=False)
    parent_id = Column(Integer,
                       ForeignKey('affiliates.id'))
    status = Column(String(50))
    track_leads_for = Column(Integer)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    contact = relationship("Contact")
    parent = relationship("Affiliate",
                          remote_side=[id])
    commissions = relationship("AffiliateCommission",
                               back_populates="affiliate")
    programs = relationship("AffiliateProgram",
                            back_populates="affiliate")
    redirects = relationship("AffiliateRedirect",
                             back_populates="affiliate")
    clawbacks = relationship("AffiliateClawback",
                             back_populates="affiliate")
    payments = relationship("AffiliatePayment",
                            back_populates="affiliate")

    def __repr__(self):
        return f"<Affiliate(id={self.id}, code='{self.code}', name='{self.name}', status='{self.status}')>"


class AffiliateCommission(Base):
    __tablename__ = 'affiliate_commissions'

    id = Column(Integer,
                primary_key=True)
    affiliate_id = Column(Integer,
                          ForeignKey('affiliates.id'))
    amount_earned = Column(Float)
    contact_id = Column(Integer,
                        ForeignKey('contacts.id'))
    contact_first_name = Column(String(100))
    contact_last_name = Column(String(100))
    date_earned = Column(DateTime)
    description = Column(Text)
    invoice_id = Column(Integer)
    product_name = Column(String(200))
    sales_affiliate_id = Column(Integer)
    sold_by_first_name = Column(String(100))
    sold_by_last_name = Column(String(100))
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate",
                             back_populates="commissions")
    contact = relationship("Contact")

    def __repr__(self):
        return f"<AffiliateCommission(id={self.id}, affiliate_id={self.affiliate_id}, amount_earned={self.amount_earned}, date_earned='{self.date_earned}')>"


class AffiliateProgram(Base):
    __tablename__ = 'affiliate_programs'

    id = Column(Integer,
                primary_key=True)
    affiliate_id = Column(Integer,
                          ForeignKey('affiliates.id'))
    name = Column(String(200))
    notes = Column(Text)
    priority = Column(Integer)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate",
                             back_populates="programs")

    def __repr__(self):
        return f"<AffiliateProgram(id={self.id}, affiliate_id={self.affiliate_id}, name='{self.name}', priority={self.priority})>"


class AffiliateRedirect(Base):
    __tablename__ = 'affiliate_redirects'

    id = Column(Integer,
                primary_key=True)
    affiliate_id = Column(Integer,
                          ForeignKey('affiliates.id'))
    local_url_code = Column(String(100))
    name = Column(String(200))
    redirect_url = Column(String(255))
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate",
                             back_populates="redirects")
    program_ids = relationship("AffiliateRedirectProgram",
                               back_populates="affiliate_redirect",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AffiliateRedirect(id={self.id}, affiliate_id={self.affiliate_id}, name='{self.name}', local_url_code='{self.local_url_code}')>"


class AffiliateSummary(Base):
    __tablename__ = 'affiliate_summaries'

    id = Column(Integer,
                primary_key=True)
    affiliate_id = Column(Integer,
                          ForeignKey('affiliates.id'))
    amount_earned = Column(Float)
    balance = Column(Float)
    clawbacks = Column(Float)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    affiliate = relationship("Affiliate")

    def __repr__(self):
        return f"<AffiliateSummary(id={self.id}, affiliate_id={self.affiliate_id}, amount_earned={self.amount_earned}, balance={self.balance})>"


class AffiliateClawback(Base):
    __tablename__ = 'affiliate_clawbacks'

    id = Column(Integer,
                primary_key=True)
    affiliate_id = Column(Integer,
                          ForeignKey('affiliates.id'))
    amount = Column(Float)  # API uses double format
    contact_id = Column(Integer,
                        ForeignKey('contacts.id'))
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
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate",
                             back_populates="clawbacks")
    contact = relationship("Contact")

    def __repr__(self):
        return f"<AffiliateClawback(id={self.id}, affiliate_id={self.affiliate_id}, amount={self.amount}, date_earned='{self.date_earned}')>"


class AffiliatePayment(Base):
    __tablename__ = 'affiliate_payments'

    id = Column(Integer,
                primary_key=True)
    affiliate_id = Column(Integer,
                          ForeignKey('affiliates.id'))
    amount = Column(Float)
    date = Column(DateTime)
    notes = Column(Text)
    type = Column(String(50))
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    affiliate = relationship("Affiliate",
                             back_populates="payments")

    def __repr__(self):
        return f"<AffiliatePayment(id={self.id}, affiliate_id={self.affiliate_id}, amount={self.amount}, date='{self.date}', type='{self.type}')>"


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer,
                primary_key=True)
    given_name = Column(String(100))
    family_name = Column(String(100))
    middle_name = Column(String(100))
    company_name = Column(String(200))
    job_title = Column(String(200))
    email_opted_in = Column(Boolean,
                            default=False)
    email_status = Column(String(50))
    score_value = Column(String(50))
    owner_id = Column(Integer)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)
    last_updated_utc_millis = Column(BigInteger)
    anniversary = Column(DateTime)
    birthday = Column(DateTime)
    contact_type = Column(String(50))
    duplicate_option = Column(String(50))
    lead_source_id = Column(Integer)
    preferred_locale = Column(String(50))
    preferred_name = Column(String(100))
    source_type = Column(String(50))
    spouse_name = Column(String(100))
    time_zone = Column(String(50))
    website = Column(String(255))
    year_created = Column(Integer)

    # Relationships with cascade options
    email_addresses = relationship("EmailAddress",
                                   secondary="contact_email",
                                   back_populates="contacts")
    phone_numbers = relationship("PhoneNumber",
                                 secondary="contact_phone",
                                 back_populates="contacts")
    addresses = relationship("Address",
                             secondary="contact_address",
                             back_populates="contacts")
    fax_numbers = relationship("FaxNumber",
                               secondary="contact_fax",
                               back_populates="contacts")
    tags = relationship("Tag",
                        secondary=contact_tag,
                        back_populates="contacts",
                        cascade="none")
    custom_field_values = relationship("ContactCustomFieldValue",
                                       back_populates="contact",
                                       cascade="all, delete-orphan")
    opportunities = relationship("Opportunity",
                                 secondary="contact_opportunity",
                                 back_populates="contacts")
    tasks = relationship("Task",
                         secondary="contact_task",
                         back_populates="contacts")
    notes = relationship("Note",
                         secondary="contact_note",
                         back_populates="contacts")
    orders = relationship("Order",
                          secondary="contact_order",
                          back_populates="contacts")
    subscriptions = relationship("Subscription",
                                 secondary="contact_subscription",
                                 back_populates="contacts")

    def __repr__(self):
        return f"<Contact(id={self.id}, given_name='{self.given_name}', family_name='{self.family_name}', company_name='{self.company_name}')>"


class EmailAddress(Base):
    __tablename__ = 'email_addresses'

    id = Column(Integer,
                primary_key=True)
    email = Column(String(255),
                   nullable=False)
    field = Column(String(50))  # e.g., "EMAIL1", "EMAIL2"
    type = Column(String(50))
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_email",
                            back_populates="email_addresses")

    def __repr__(self):
        return f"<EmailAddress(id={self.id}, email='{self.email}', field='{self.field}')>"


class PhoneNumber(Base):
    __tablename__ = 'phone_numbers'

    id = Column(Integer,
                primary_key=True)
    number = Column(String(50),
                    nullable=False)
    field = Column(String(50))  # e.g., "PHONE1", "PHONE2"
    type = Column(String(50))
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_phone",
                            back_populates="phone_numbers")

    def __repr__(self):
        return f"<PhoneNumber(id={self.id}, number='{self.number}', field='{self.field}')>"


class Address(Base):
    __tablename__ = 'addresses'

    id = Column(Integer,
                primary_key=True)
    country_code = Column(String(10))  # Changed from country
    field = Column(Enum(AddressType),
                   nullable=False)  # Changed to use enum
    line1 = Column(String(255))  # Changed from street_address
    line2 = Column(String(255))  # Added
    locality = Column(String(100))  # Changed from city
    postal_code = Column(String(20))
    region = Column(String(100))  # Changed from state
    zip_code = Column(String(20))  # Added
    zip_four = Column(String(10))  # Added
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_address",
                            back_populates="addresses")

    def __repr__(self):
        return f"<Address(id={self.id}, field='{self.field}', locality='{self.locality}')>"


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer,
                primary_key=True)
    name = Column(String(255),
                  nullable=False)
    description = Column(Text)
    category = Column(String(100))
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary=contact_tag,
                            back_populates="tags")

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}', category='{self.category}')>"


class CustomFieldType(enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    DROPDOWN = "dropdown"
    MULTISELECT = "multiselect"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    CURRENCY = "currency"
    PERCENT = "percent"
    SOCIAL = "social"
    ADDRESS = "address"
    IMAGE = "image"
    FILE = "file"


class CustomFieldMetaData(Base):
    __tablename__ = 'custom_field_metadata'

    id = Column(Integer,
                primary_key=True)
    custom_field_id = Column(Integer,
                             ForeignKey('custom_fields.id',
                                        ondelete='CASCADE'))
    label = Column(String(255))
    description = Column(Text)
    data_type = Column(String(50))  # string, number, date, etc.
    is_required = Column(Boolean,
                         default=False)
    is_read_only = Column(Boolean,
                          default=False)
    is_visible = Column(Boolean,
                        default=True)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    custom_field = relationship("CustomField",
                                back_populates="field_metadata")

    def __repr__(self):
        return f"<CustomFieldMetaData(id={self.id}, label='{self.label}', data_type='{self.data_type}')>"


class CustomField(Base):
    __tablename__ = 'custom_fields'

    id = Column(Integer,
                primary_key=True)
    name = Column(String(100),
                  nullable=True)
    type = Column(Enum(CustomFieldType),
                  nullable=True)
    options = Column(JSON,
                     nullable=True)  # Array of string options for dropdown/multiselect/radio fields
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    values = relationship("ContactCustomFieldValue",
                          back_populates="custom_field",
                          cascade="all, delete-orphan")
    field_metadata = relationship("CustomFieldMetaData",
                                  back_populates="custom_field",
                                  uselist=False,
                                  cascade="all, delete-orphan")
    opportunity_values = relationship("OpportunityCustomFieldValue",
                                      back_populates="custom_field",
                                      cascade="all, delete-orphan")
    order_values = relationship("OrderCustomFieldValue",
                                back_populates="custom_field",
                                cascade="all, delete-orphan")
    subscription_values = relationship("SubscriptionCustomFieldValue",
                                       back_populates="custom_field",
                                       cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CustomField(id={self.id}, name='{self.name}', type='{self.type}')>"


class ContactCustomFieldValue(Base):
    __tablename__ = 'contact_custom_field_values'

    id = Column(Integer,
                primary_key=True)
    contact_id = Column(Integer,
                        ForeignKey('contacts.id',
                                   ondelete='CASCADE'))
    custom_field_id = Column(Integer,
                             ForeignKey('custom_fields.id',
                                        ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    contact = relationship("Contact",
                           back_populates="custom_field_values")
    custom_field = relationship("CustomField",
                                back_populates="values")

    __table_args__ = (UniqueConstraint('contact_id',
                                       'custom_field_id',
                                       name='uix_contact_custom_field'),)

    def __repr__(self):
        return f"<ContactCustomFieldValue(id={self.id}, contact_id={self.contact_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class OpportunityCustomFieldValue(Base):
    __tablename__ = 'opportunity_custom_field_values'

    id = Column(Integer,
                primary_key=True)
    opportunity_id = Column(Integer,
                            ForeignKey('opportunities.id',
                                       ondelete='CASCADE'))
    custom_field_id = Column(Integer,
                             ForeignKey('custom_fields.id',
                                        ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    opportunity = relationship("Opportunity",
                               back_populates="custom_field_values")
    custom_field = relationship("CustomField",
                                back_populates="opportunity_values")

    __table_args__ = (UniqueConstraint('opportunity_id',
                                       'custom_field_id',
                                       name='uix_opportunity_custom_field'),)

    def __repr__(self):
        return f"<OpportunityCustomFieldValue(id={self.id}, opportunity_id={self.opportunity_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class OrderCustomFieldValue(Base):
    __tablename__ = 'order_custom_field_values'

    id = Column(Integer,
                primary_key=True)
    order_id = Column(Integer,
                      ForeignKey('orders.id',
                                 ondelete='CASCADE'))
    custom_field_id = Column(Integer,
                             ForeignKey('custom_fields.id',
                                        ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    order = relationship("Order",
                         back_populates="custom_field_values")
    custom_field = relationship("CustomField",
                                back_populates="order_values")

    __table_args__ = (UniqueConstraint('order_id',
                                       'custom_field_id',
                                       name='uix_order_custom_field'),)

    def __repr__(self):
        return f"<OrderCustomFieldValue(id={self.id}, order_id={self.order_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class SubscriptionCustomFieldValue(Base):
    __tablename__ = 'subscription_custom_field_values'

    id = Column(Integer,
                primary_key=True)
    subscription_id = Column(Integer,
                             ForeignKey('subscriptions.id',
                                        ondelete='CASCADE'))
    custom_field_id = Column(Integer,
                             ForeignKey('custom_fields.id',
                                        ondelete='CASCADE'))
    value = Column(Text)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    subscription = relationship("Subscription",
                                back_populates="custom_field_values")
    custom_field = relationship("CustomField",
                                back_populates="subscription_values")

    __table_args__ = (UniqueConstraint('subscription_id',
                                       'custom_field_id',
                                       name='uix_subscription_custom_field'),)

    def __repr__(self):
        return f"<SubscriptionCustomFieldValue(id={self.id}, subscription_id={self.subscription_id}, custom_field_id={self.custom_field_id}, value='{self.value}')>"


class Opportunity(Base):
    __tablename__ = 'opportunities'

    id = Column(Integer,
                primary_key=True)
    title = Column(String(200),
                   nullable=False)
    stage = Column(String(100))
    value = Column(Float)
    probability = Column(Float)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_opportunity",
                            back_populates="opportunities")
    custom_field_values = relationship("OpportunityCustomFieldValue",
                                       back_populates="opportunity",
                                       cascade="all, delete-orphan",
                                       lazy="dynamic")

    def __repr__(self):
        return f"<Opportunity(id={self.id}, title='{self.title}', stage='{self.stage}', value={self.value})>"


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer,
                primary_key=True)
    product_name = Column(String(200),
                          nullable=False)
    product_sku = Column(String(100),
                         unique=True)
    subscription_only = Column(Boolean,
                               default=False)
    plan_description = Column(Text)
    frequency = Column(String(50))
    price = Column(Float)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    order_items = relationship("OrderItem",
                               secondary="product_order_item",
                               back_populates="products")
    subscriptions = relationship("Subscription",
                                 secondary="product_subscription",
                                 back_populates="products")

    def __repr__(self):
        return f"<Product(id={self.id}, product_name='{self.product_name}', product_sku='{self.product_sku}', price={self.price})>"


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer,
                primary_key=True)
    order_number = Column(String(50))  # Added from API spec
    order_date = Column(DateTime,
                        nullable=False)
    order_status = Column(String(50))
    order_total = Column(Float)
    order_type = Column(String(50))  # Added from API spec
    payment_plan_id = Column(Integer)  # Added from API spec
    payment_type = Column(String(50))  # Added from API spec
    subscription_plan_id = Column(Integer)  # Added from API spec
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_order",
                            back_populates="orders")
    items = relationship("OrderItem",
                         secondary="order_item",
                         back_populates="orders")
    custom_field_values = relationship("OrderCustomFieldValue",
                                       back_populates="order",
                                       cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', order_status='{self.order_status}', order_total={self.order_total})>"


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer,
                primary_key=True)
    order_id = Column(Integer,
                      ForeignKey('orders.id',
                                 ondelete='CASCADE'))
    product_id = Column(Integer,
                        ForeignKey('products.id',
                                   ondelete='CASCADE'))
    quantity = Column(Integer,
                      nullable=False)
    price = Column(Float,
                   nullable=False)
    description = Column(Text)  # Added from API spec
    subscription_plan_id = Column(Integer)  # Added from API spec
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)  # Added from API spec

    # Relationships
    orders = relationship("Order",
                          secondary="order_item",
                          back_populates="items")
    products = relationship("Product",
                            secondary="product_order_item",
                            back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity}, price={self.price})>"


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer,
                primary_key=True)
    title = Column(String(200),
                   nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    completed = Column(Boolean,
                       default=False)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_task",
                            back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', due_date='{self.due_date}', completed={self.completed})>"


class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer,
                primary_key=True)
    title = Column(String(200))
    body = Column(Text,
                  nullable=False)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_note",
                            back_populates="notes")

    def __repr__(self):
        return f"<Note(id={self.id}, title='{self.title}')>"


class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(Integer,
                primary_key=True)
    name = Column(String(200),
                  nullable=False)
    status = Column(String(50))
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    sequences = relationship("CampaignSequence",
                             secondary="campaign_sequence",
                             back_populates="campaigns")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class CampaignSequence(Base):
    __tablename__ = 'campaign_sequences'

    id = Column(Integer,
                primary_key=True)
    name = Column(String(200),
                  nullable=False)
    status = Column(String(50))
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    campaigns = relationship("Campaign",
                             secondary="campaign_sequence",
                             back_populates="sequences")

    def __repr__(self):
        return f"<CampaignSequence(id={self.id}, name='{self.name}', status='{self.status}')>"


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer,
                primary_key=True)
    product_id = Column(Integer,
                        ForeignKey('products.id',
                                   ondelete='CASCADE'))
    status = Column(String(50))
    next_bill_date = Column(DateTime)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_subscription",
                            back_populates="subscriptions")
    products = relationship("Product",
                            secondary="product_subscription",
                            back_populates="subscriptions")
    custom_field_values = relationship("SubscriptionCustomFieldValue",
                                       back_populates="subscription",
                                       cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subscription(id={self.id}, product_id={self.product_id}, status='{self.status}', next_bill_date='{self.next_bill_date}')>"


class FaxNumber(Base):
    __tablename__ = 'fax_numbers'

    id = Column(Integer,
                primary_key=True)
    number = Column(String(50),
                    nullable=False)
    field = Column(String(50))
    type = Column(String(50))
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    contacts = relationship("Contact",
                            secondary="contact_fax",
                            back_populates="fax_numbers")

    def __repr__(self):
        return f"<FaxNumber(id={self.id}, number='{self.number}', field='{self.field}')>"


class BusinessGoal(Base):
    __tablename__ = 'business_goals'

    id = Column(Integer,
                primary_key=True)
    account_profile_id = Column(Integer,
                                ForeignKey('account_profiles.id'))
    goal = Column(String(255),
                  nullable=False)
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    account_profile = relationship("AccountProfile",
                                   back_populates="business_goals")

    def __repr__(self):
        return f"<BusinessGoal(id={self.id}, account_profile_id={self.account_profile_id}, goal='{self.goal}')>"


class AffiliateRedirectProgram(Base):
    __tablename__ = 'affiliate_redirect_programs'

    id = Column(Integer,
                primary_key=True)
    affiliate_redirect_id = Column(Integer,
                                   ForeignKey('affiliate_redirects.id'))
    program_id = Column(Integer,
                        nullable=False)
    created_at = Column(DateTime,
                        default=utc_now)

    # Relationships
    affiliate_redirect = relationship("AffiliateRedirect",
                                      back_populates="program_ids")

    def __repr__(self):
        return f"<AffiliateRedirectProgram(id={self.id}, affiliate_redirect_id={self.affiliate_redirect_id}, program_id={self.program_id})>"


# Join tables
contact_address = Table('contact_address',
                        Base.metadata,
                        Column('contact_id',
                               Integer,
                               ForeignKey('contacts.id',
                                          ondelete='CASCADE'),
                               primary_key=True),
                        Column('address_id',
                               Integer,
                               ForeignKey('addresses.id',
                                          ondelete='CASCADE'),
                               primary_key=True),
                        Column('created_at',
                               DateTime,
                               default=utc_now))

contact_email = Table('contact_email',
                      Base.metadata,
                      Column('contact_id',
                             Integer,
                             ForeignKey('contacts.id',
                                        ondelete='CASCADE'),
                             primary_key=True),
                      Column('email_id',
                             Integer,
                             ForeignKey('email_addresses.id',
                                        ondelete='CASCADE'),
                             primary_key=True),
                      Column('created_at',
                             DateTime,
                             default=utc_now))

contact_phone = Table('contact_phone',
                      Base.metadata,
                      Column('contact_id',
                             Integer,
                             ForeignKey('contacts.id',
                                        ondelete='CASCADE'),
                             primary_key=True),
                      Column('phone_id',
                             Integer,
                             ForeignKey('phone_numbers.id',
                                        ondelete='CASCADE'),
                             primary_key=True),
                      Column('created_at',
                             DateTime,
                             default=utc_now))

contact_fax = Table('contact_fax',
                    Base.metadata,
                    Column('contact_id',
                           Integer,
                           ForeignKey('contacts.id',
                                      ondelete='CASCADE'),
                           primary_key=True),
                    Column('fax_id',
                           Integer,
                           ForeignKey('fax_numbers.id',
                                      ondelete='CASCADE'),
                           primary_key=True),
                    Column('created_at',
                           DateTime,
                           default=utc_now))

contact_opportunity = Table('contact_opportunity',
                            Base.metadata,
                            Column('contact_id',
                                   Integer,
                                   ForeignKey('contacts.id',
                                              ondelete='CASCADE'),
                                   primary_key=True),
                            Column('opportunity_id',
                                   Integer,
                                   ForeignKey('opportunities.id',
                                              ondelete='CASCADE'),
                                   primary_key=True),
                            Column('created_at',
                                   DateTime,
                                   default=utc_now))

contact_task = Table('contact_task',
                     Base.metadata,
                     Column('contact_id',
                            Integer,
                            ForeignKey('contacts.id',
                                       ondelete='CASCADE'),
                            primary_key=True),
                     Column('task_id',
                            Integer,
                            ForeignKey('tasks.id',
                                       ondelete='CASCADE'),
                            primary_key=True),
                     Column('created_at',
                            DateTime,
                            default=utc_now))

contact_note = Table('contact_note',
                     Base.metadata,
                     Column('contact_id',
                            Integer,
                            ForeignKey('contacts.id',
                                       ondelete='CASCADE'),
                            primary_key=True),
                     Column('note_id',
                            Integer,
                            ForeignKey('notes.id',
                                       ondelete='CASCADE'),
                            primary_key=True),
                     Column('created_at',
                            DateTime,
                            default=utc_now))

contact_order = Table('contact_order',
                      Base.metadata,
                      Column('contact_id',
                             Integer,
                             ForeignKey('contacts.id',
                                        ondelete='CASCADE'),
                             primary_key=True),
                      Column('order_id',
                             Integer,
                             ForeignKey('orders.id',
                                        ondelete='CASCADE'),
                             primary_key=True),
                      Column('created_at',
                             DateTime,
                             default=utc_now))

contact_subscription = Table('contact_subscription',
                             Base.metadata,
                             Column('contact_id',
                                    Integer,
                                    ForeignKey('contacts.id',
                                               ondelete='CASCADE'),
                                    primary_key=True),
                             Column('subscription_id',
                                    Integer,
                                    ForeignKey('subscriptions.id',
                                               ondelete='CASCADE'),
                                    primary_key=True),
                             Column('created_at',
                                    DateTime,
                                    default=utc_now))

order_item = Table('order_item',
                   Base.metadata,
                   Column('order_id',
                          Integer,
                          ForeignKey('orders.id',
                                     ondelete='CASCADE'),
                          primary_key=True),
                   Column('item_id',
                          Integer,
                          ForeignKey('order_items.id',
                                     ondelete='CASCADE'),
                          primary_key=True),
                   Column('created_at',
                          DateTime,
                          default=utc_now))

product_order_item = Table('product_order_item',
                           Base.metadata,
                           Column('product_id',
                                  Integer,
                                  ForeignKey('products.id',
                                             ondelete='CASCADE'),
                                  primary_key=True),
                           Column('order_item_id',
                                  Integer,
                                  ForeignKey('order_items.id',
                                             ondelete='CASCADE'),
                                  primary_key=True),
                           Column('created_at',
                                  DateTime,
                                  default=utc_now))

product_subscription = Table('product_subscription',
                             Base.metadata,
                             Column('product_id',
                                    Integer,
                                    ForeignKey('products.id',
                                               ondelete='CASCADE'),
                                    primary_key=True),
                             Column('subscription_id',
                                    Integer,
                                    ForeignKey('subscriptions.id',
                                               ondelete='CASCADE'),
                                    primary_key=True),
                             Column('created_at',
                                    DateTime,
                                    default=utc_now))

campaign_sequence = Table('campaign_sequence',
                          Base.metadata,
                          Column('campaign_id',
                                 Integer,
                                 ForeignKey('campaigns.id',
                                            ondelete='CASCADE'),
                                 primary_key=True),
                          Column('sequence_id',
                                 Integer,
                                 ForeignKey('campaign_sequences.id',
                                            ondelete='CASCADE'),
                                 primary_key=True),
                          Column('created_at',
                                 DateTime,
                                 default=utc_now))
