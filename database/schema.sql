-- Schema for Keap Data Extract
-- This schema defines all tables, relationships, and indexes for the Keap data extraction system

-- =============================================
-- Create ENUM Types
-- =============================================

CREATE TYPE address_type AS ENUM (
    'BILLING',
    'SHIPPING',
    'OTHER',
    'HOME',
    'WORK'
);

CREATE TYPE custom_field_type AS ENUM (
    'text',
    'number',
    'date',
    'dropdown',
    'multiselect',
    'radio',
    'checkbox',
    'url',
    'email',
    'phone',
    'currency',
    'percent',
    'social',
    'address',
    'image',
    'file',
    'list',
    'multiline',
    'password',
    'time',
    'datetime',
    'boolean',
    'hidden',
    -- Additional field types from the API
    'TextArea',
    'WholeNumber',
    'Website',
    -- API field type mappings
    'Dropdown',
    'Text',
    'DateTime',
    'Date',
    'Currency'
);

CREATE TYPE note_type AS ENUM (
    'Call',
    'Email',
    'Fax',
    'Letter',
    'Meeting',
    'Other',
    'Task',
    'SMS',
    'Social',
    'Chat',
    'Voicemail',
    'Website',
    'Form',
    'Appointment',
    'Campaign',
    'Contact',
    'Deal',
    'Document',
    'File',
    'Follow Up',
    'Invoice',
    'Order',
    'Product',
    'Purchase',
    'Recurring Order',
    'Referral',
    'Refund',
    'Subscription',
    'Survey',
    'Tag',
    'Template',
    'Transaction',
    'User',
    'Webform',
    'Workflow'
);

CREATE TYPE contact_email_status AS ENUM (
    'UnengagedMarketable',
    'SingleOptIn',
    'DoubleOptIn',
    'Confirmed',
    'UnengagedNonMarketable',
    'NonMarketable',
    'Lockdown',
    'Bounce',
    'HardBounce',
    'Manual',
    'Admin',
    'System',
    'ListUnsubscribe',
    'Feedback',
    'Spam',
    'Invalid',
    'Deactivated'
);

CREATE TYPE order_status AS ENUM (
    'DRAFT',
    'PENDING',
    'PAID',
    'REFUNDED',
    'CANCELLED',
    'FAILED',
    'PARTIALLY_PAID',
    'PARTIALLY_REFUNDED',
    'VOID',
    'PROCESSING',
    'ON_HOLD'
);

CREATE TYPE task_status AS ENUM (
    'PENDING',
    'COMPLETED',
    'CANCELLED',
    'DEFERRED',
    'WAITING',
    'IN_PROGRESS'
);

CREATE TYPE task_priority AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'URGENT'
);

CREATE TYPE subscription_status AS ENUM (
    'Active',
    'Cancelled',
    'Expired',
    'Paused',
    'Trial',
    'Past Due',
    'Pending',
    'Failed',
    'On Hold'
);

CREATE TYPE campaign_status AS ENUM (
    'Draft',
    'Active',
    'Paused',
    'Completed',
    'Archived',
    'Scheduled',
    'Stopped'
);

CREATE TYPE affiliate_status AS ENUM (
    'Active',
    'Inactive',
    'Pending',
    'Suspended',
    'Terminated'
);

CREATE TYPE order_source_type AS ENUM (
    'API',
    'CALL',
    'EMAIL',
    'FORM',
    'IMPORT',
    'INVOICE',
    'ONLINE',
    'PHONE',
    'SMS',
    'SYSTEM',
    'WEBSITE',
    'MANUAL',
    'SOCIAL',
    'REFERRAL',
    'PARTNER',
    'AFFILIATE'
);

CREATE TYPE contact_source_type AS ENUM (
    'API',
    'CALL',
    'EMAIL',
    'FORM',
    'IMPORT',
    'INVOICE',
    'ONLINE',
    'PHONE',
    'SMS',
    'SYSTEM',
    'WEBSITE',
    'MANUAL',
    'SOCIAL',
    'REFERRAL',
    'PARTNER',
    'AFFILIATE'
);

CREATE TYPE opportunity_stage AS ENUM (
    'Qualified',
    'Proposal',
    'Negotiation',
    'Closed Won',
    'Closed Lost',
    'Discovery',
    'Presentation',
    'Decision',
    'Contract',
    'Implementation'
);

-- =============================================
-- Create Functions
-- =============================================

CREATE OR REPLACE FUNCTION update_modified_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =============================================
-- Create Tables
-- =============================================

CREATE TABLE contacts (
    id INTEGER PRIMARY KEY,
    given_name VARCHAR(100),
    family_name VARCHAR(100),
    middle_name VARCHAR(100),
    company_name VARCHAR(200),
    job_title VARCHAR(200),
    email_opted_in BOOLEAN DEFAULT FALSE,
    email_status contact_email_status,
    score_value VARCHAR(50),
    owner_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated_utc_millis BIGINT,
    anniversary TIMESTAMP WITH TIME ZONE,
    birthday TIMESTAMP WITH TIME ZONE,
    contact_type VARCHAR(50),
    duplicate_option VARCHAR(50),
    lead_source_id INTEGER,
    preferred_locale VARCHAR(50),
    preferred_name VARCHAR(100),
    source_type contact_source_type,
    spouse_name VARCHAR(100),
    time_zone VARCHAR(50),
    website VARCHAR(255),
    year_created INTEGER
);

CREATE TABLE email_addresses (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE phone_numbers (
    id INTEGER PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contact_addresses (
    id INTEGER PRIMARY KEY,
    country_code VARCHAR(10),
    field address_type NOT NULL,
    line1 VARCHAR(255),
    line2 VARCHAR(255),
    locality VARCHAR(100),
    postal_code VARCHAR(20),
    region VARCHAR(100),
    zip_code VARCHAR(20),
    zip_four VARCHAR(10),
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fax_numbers (
    id INTEGER PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tag_categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES tag_categories(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE custom_fields (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    type custom_field_type,
    options JSONB,
    -- Additional fields from API response
    label VARCHAR(255),
    field_name VARCHAR(100),
    record_type VARCHAR(50),
    default_value VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE custom_field_metadata (
    id INTEGER PRIMARY KEY,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    label VARCHAR(255),
    description TEXT,
    data_type VARCHAR(50),
    is_required BOOLEAN DEFAULT FALSE,
    is_read_only BOOLEAN DEFAULT FALSE,
    is_visible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE contact_custom_field_values (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contact_id, custom_field_id)
);

CREATE TABLE opportunities (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    stage JSONB,
    value FLOAT,
    probability FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_action_date TIMESTAMP,
    next_action_notes TEXT,
    source_type VARCHAR(50),
    source_id INTEGER,
    pipeline_id INTEGER,
    pipeline_stage_id INTEGER,
    owner_id INTEGER,
    last_updated_utc_millis BIGINT
);

CREATE TABLE opportunity_custom_field_values (
    id INTEGER PRIMARY KEY,
    opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(opportunity_id, custom_field_id)
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    title VARCHAR(200),
    notes TEXT,
    priority task_priority,
    status task_status,
    type VARCHAR(50),
    due_date TIMESTAMP WITH TIME ZONE,
    completed_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200),
    status order_status,
    recurring BOOLEAN,
    total NUMERIC(10,2),
    notes TEXT,
    terms TEXT,
    order_type VARCHAR(50),
    source_type order_source_type,
    creation_date TIMESTAMP WITH TIME ZONE,
    modification_date TIMESTAMP WITH TIME ZONE,
    order_date TIMESTAMP WITH TIME ZONE,
    lead_affiliate_id INTEGER,
    sales_affiliate_id INTEGER,
    total_paid NUMERIC(10,2),
    total_due NUMERIC(10,2),
    refund_total NUMERIC(10,2),
    allow_payment BOOLEAN,
    allow_paypal BOOLEAN,
    invoice_number INTEGER,
    contact_id INTEGER REFERENCES contacts(id),
    product_id INTEGER,
    payment_gateway_id INTEGER REFERENCES payment_gateways(id),
    subscription_plan_id INTEGER REFERENCES subscription_plans(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    job_recurring_id INTEGER,
    name VARCHAR(200),
    description TEXT,
    type VARCHAR(50),
    notes TEXT,
    quantity INTEGER,
    cost NUMERIC(10,2),
    price NUMERIC(10,2),
    discount NUMERIC(10,2),
    special_id INTEGER,
    special_amount NUMERIC(10,2),
    special_pct_or_amt INTEGER,
    product_id INTEGER REFERENCES products(id),
    subscription_plan_id INTEGER REFERENCES subscription_plans(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_payments (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    amount NUMERIC(10,2) NOT NULL,
    note TEXT,
    invoice_id INTEGER,
    payment_id INTEGER,
    pay_date TIMESTAMP NOT NULL,
    pay_status VARCHAR(50),
    last_updated TIMESTAMP,
    skip_commission BOOLEAN DEFAULT FALSE,
    refund_invoice_payment_id INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_transactions (
    id INTEGER PRIMARY KEY,
    test BOOLEAN DEFAULT FALSE,
    amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10),
    gateway VARCHAR(50),
    payment_date TIMESTAMP,
    type VARCHAR(50),
    status VARCHAR(100),
    errors TEXT,
    contact_id INTEGER REFERENCES contacts(id),
    transaction_date TIMESTAMP,
    gateway_account_name VARCHAR(100),
    order_ids VARCHAR(100),
    collection_method VARCHAR(50),
    payment_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_transaction (
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES order_transactions(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, transaction_id)
);

CREATE TABLE order_custom_field_values (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(order_id, custom_field_id)
);

CREATE TABLE payment_plans (
    order_id INTEGER PRIMARY KEY REFERENCES orders(id),
    auto_charge BOOLEAN,
    credit_card_id INTEGER,
    days_between_payments INTEGER,
    initial_payment_amount NUMERIC(10,2),
    initial_payment_percent NUMERIC(5,2),
    initial_payment_date DATE,
    number_of_payments INTEGER,
    merchant_account_id INTEGER REFERENCES payment_gateways(id),
    merchant_account_name VARCHAR(200),
    plan_start_date DATE,
    payment_method_id VARCHAR(50),
    max_charge_attempts INTEGER,
    days_between_retries INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shipping_information (
    id INTEGER PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(200),
    phone VARCHAR(50),
    street1 VARCHAR(255),
    street2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    zip VARCHAR(20),
    country VARCHAR(100),
    tracking_number VARCHAR(100),
    carrier VARCHAR(100),
    shipping_status VARCHAR(50),
    shipping_date TIMESTAMP WITH TIME ZONE,
    estimated_delivery_date TIMESTAMP WITH TIME ZONE,
    invoice_to_company BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    sku VARCHAR(100),
    active BOOLEAN DEFAULT TRUE,
    url VARCHAR(255),
    product_name VARCHAR(200),
    sub_category_id INTEGER DEFAULT 0,
    product_desc TEXT,
    product_price NUMERIC(10,2),
    product_short_desc TEXT,
    subscription_only BOOLEAN DEFAULT FALSE,
    status INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_options (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10,2),
    sku VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subscription_plans (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    name VARCHAR(200),
    description TEXT,
    frequency VARCHAR(50),
    subscription_plan_price DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    subscription_plan_id INTEGER REFERENCES subscription_plans(id),
    status subscription_status,
    next_bill_date TIMESTAMP WITH TIME ZONE,
    contact_id INTEGER REFERENCES contacts(id),
    payment_gateway_id INTEGER REFERENCES payment_gateways(id),
    credit_card_id INTEGER REFERENCES credit_cards(id),
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    billing_cycle VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subscription_custom_field_values (
    id INTEGER PRIMARY KEY,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subscription_id, custom_field_id)
);

CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    title VARCHAR(200),
    body TEXT,
    type note_type,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE note_custom_field_values (
    id INTEGER PRIMARY KEY,
    note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(note_id, custom_field_id)
);

CREATE TABLE campaign_sequences (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(50),
    sequence_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status campaign_status,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE affiliates (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    parent_id INTEGER,
    status affiliate_status,
    code VARCHAR(50),
    name VARCHAR(200),
    email VARCHAR(255),
    company VARCHAR(200),
    website VARCHAR(255),
    phone VARCHAR(50),
    address1 VARCHAR(255),
    address2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    tax_id VARCHAR(50),
    payment_email VARCHAR(255),
    notify_on_lead BOOLEAN,
    notify_on_sale BOOLEAN,
    track_leads_for INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE affiliate_commissions (
    id INTEGER PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount_earned DECIMAL(10,2),
    contact_id INTEGER REFERENCES contacts(id),
    contact_first_name VARCHAR(100),
    contact_last_name VARCHAR(100),
    date_earned TIMESTAMP WITH TIME ZONE,
    description TEXT,
    invoice_id INTEGER,
    product_name VARCHAR(200),
    sales_affiliate_id INTEGER,
    sold_by_first_name VARCHAR(100),
    sold_by_last_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE affiliate_programs (
    id INTEGER PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    name VARCHAR(200),
    notes TEXT,
    priority INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE affiliate_redirects (
    id INTEGER PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    local_url_code VARCHAR(100),
    name VARCHAR(200),
    redirect_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE affiliate_summaries (
    id INTEGER PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount_earned DECIMAL(10,2),
    balance DECIMAL(10,2),
    clawbacks DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE affiliate_clawbacks (
    id INTEGER PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount DECIMAL(10,2),
    contact_id INTEGER REFERENCES contacts(id),
    date_earned TIMESTAMP WITH TIME ZONE,
    description TEXT,
    family_name VARCHAR(100),
    given_name VARCHAR(100),
    invoice_id INTEGER,
    product_name VARCHAR(200),
    sale_affiliate_id INTEGER,
    sold_by_family_name VARCHAR(100),
    sold_by_given_name VARCHAR(100),
    subscription_plan_name VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE affiliate_payments (
    id INTEGER PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount DECIMAL(10,2),
    date TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE account_profiles (
    id INTEGER PRIMARY KEY,
    address_id INTEGER REFERENCES contact_addresses(id),
    business_primary_color VARCHAR(50),
    business_secondary_color VARCHAR(50),
    business_type VARCHAR(100),
    currency_code VARCHAR(10),
    email VARCHAR(255),
    language_tag VARCHAR(50),
    logo_url VARCHAR(255),
    name VARCHAR(200),
    phone VARCHAR(50),
    phone_ext VARCHAR(20),
    time_zone VARCHAR(50),
    website VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE business_goals (
    id INTEGER PRIMARY KEY,
    account_profile_id INTEGER REFERENCES account_profiles(id),
    goal VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE credit_cards (
    id INTEGER PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id),
    card_type VARCHAR(50),
    card_number VARCHAR(20),
    expiration_month INTEGER,
    expiration_year INTEGER,
    card_holder_name VARCHAR(100),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payment_gateways (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    credentials JSONB,
    settings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- Create Join Tables
-- =============================================

CREATE TABLE contact_tag (
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, tag_id)
);

CREATE TABLE contact_opportunity (
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, opportunity_id)
);

CREATE TABLE contact_task (
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, task_id)
);

CREATE TABLE contact_note (
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, note_id)
);

CREATE TABLE contact_order (
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, order_id)
);

CREATE TABLE contact_subscription (
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, subscription_id)
);

CREATE TABLE product_subscription (
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, subscription_id)
);

CREATE TABLE product_order_item (
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    order_item_id INTEGER REFERENCES order_items(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, order_item_id)
);

CREATE TABLE campaign_sequence (
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    sequence_id INTEGER REFERENCES campaign_sequences(id) ON DELETE CASCADE,
    PRIMARY KEY (campaign_id, sequence_id)
);

CREATE TABLE affiliate_redirect_programs (
    id INTEGER PRIMARY KEY,
    affiliate_redirect_id INTEGER REFERENCES affiliate_redirects(id),
    program_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- Create Indexes
-- =============================================

CREATE INDEX idx_contacts_company_name ON contacts(company_name);
CREATE INDEX idx_contacts_created_at ON contacts(created_at);
CREATE INDEX idx_contacts_email_status ON contacts(email_status);
CREATE INDEX idx_contacts_contact_type ON contacts(contact_type);
CREATE INDEX idx_contacts_owner_id ON contacts(owner_id);
CREATE INDEX idx_contacts_lead_source_id ON contacts(lead_source_id);

CREATE INDEX idx_email_addresses_email ON email_addresses(email);
CREATE INDEX idx_email_addresses_field ON email_addresses(field);
CREATE INDEX idx_email_addresses_contact_id ON email_addresses(contact_id);

CREATE INDEX idx_phone_numbers_number ON phone_numbers(number);
CREATE INDEX idx_phone_numbers_field ON phone_numbers(field);
CREATE INDEX idx_phone_numbers_contact_id ON phone_numbers(contact_id);

CREATE INDEX idx_addresses_country_code ON addresses(country_code);
CREATE INDEX idx_addresses_field ON addresses(field);
CREATE INDEX idx_addresses_postal_code ON addresses(postal_code);

CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_order_status ON orders(status);
CREATE INDEX idx_orders_order_type ON orders(order_type);
CREATE INDEX idx_orders_payment_gateway_id ON orders(payment_gateway_id);
CREATE INDEX idx_orders_lead_affiliate_id ON orders(lead_affiliate_id);
CREATE INDEX idx_orders_sales_affiliate_id ON orders(sales_affiliate_id);
CREATE INDEX idx_orders_subscription_plan_id ON orders(subscription_plan_id);

CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);

CREATE INDEX idx_opportunities_stage ON opportunities(stage);
CREATE INDEX idx_opportunities_value ON opportunities(value);
CREATE INDEX idx_opportunities_probability ON opportunities(probability);
CREATE INDEX idx_opportunities_owner_id ON opportunities(owner_id);
CREATE INDEX idx_opportunities_pipeline_id ON opportunities(pipeline_id);
CREATE INDEX idx_opportunities_pipeline_stage_id ON opportunities(pipeline_stage_id);

CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_completed_date ON tasks(completed_date);
CREATE INDEX idx_tasks_type ON tasks(type);

CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_next_bill_date ON subscriptions(next_bill_date);
CREATE INDEX idx_subscriptions_contact_id ON subscriptions(contact_id);
CREATE INDEX idx_subscriptions_payment_gateway_id ON subscriptions(payment_gateway_id);
CREATE INDEX idx_subscriptions_credit_card_id ON subscriptions(credit_card_id);
CREATE INDEX idx_subscriptions_start_date ON subscriptions(start_date);
CREATE INDEX idx_subscriptions_end_date ON subscriptions(end_date);
CREATE INDEX idx_subscriptions_billing_cycle ON subscriptions(billing_cycle);

CREATE INDEX idx_affiliates_code ON affiliates(code);
CREATE INDEX idx_affiliates_status ON affiliates(status);
CREATE INDEX idx_affiliates_parent_id ON affiliates(parent_id);

CREATE INDEX idx_affiliate_commissions_date_earned ON affiliate_commissions(date_earned);
CREATE INDEX idx_affiliate_commissions_affiliate_id ON affiliate_commissions(affiliate_id);
CREATE INDEX idx_affiliate_commissions_contact_id ON affiliate_commissions(contact_id);

CREATE INDEX idx_affiliate_clawbacks_date_earned ON affiliate_clawbacks(date_earned);
CREATE INDEX idx_affiliate_clawbacks_affiliate_id ON affiliate_clawbacks(affiliate_id);
CREATE INDEX idx_affiliate_clawbacks_contact_id ON affiliate_clawbacks(contact_id);

CREATE INDEX idx_affiliate_payments_date ON affiliate_payments(date);
CREATE INDEX idx_affiliate_payments_affiliate_id ON affiliate_payments(affiliate_id);
CREATE INDEX idx_affiliate_payments_type ON affiliate_payments(type);

CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaign_sequences_status ON campaign_sequences(status);

CREATE INDEX idx_custom_fields_type ON custom_fields(type);
CREATE INDEX idx_custom_fields_name ON custom_fields(name);
CREATE INDEX idx_custom_fields_label ON custom_fields(label);
CREATE INDEX idx_custom_fields_field_name ON custom_fields(field_name);
CREATE INDEX idx_custom_fields_record_type ON custom_fields(record_type);

CREATE INDEX idx_custom_field_metadata_label ON custom_field_metadata(label);
CREATE INDEX idx_custom_field_metadata_data_type ON custom_field_metadata(data_type);

CREATE INDEX idx_contact_custom_field_values_contact_id ON contact_custom_field_values(contact_id);
CREATE INDEX idx_contact_custom_field_values_custom_field_id ON contact_custom_field_values(custom_field_id);

CREATE INDEX idx_opportunity_custom_field_values_opportunity_id ON opportunity_custom_field_values(opportunity_id);
CREATE INDEX idx_opportunity_custom_field_values_custom_field_id ON opportunity_custom_field_values(custom_field_id);

CREATE INDEX idx_order_custom_field_values_order_id ON order_custom_field_values(order_id);
CREATE INDEX idx_order_custom_field_values_custom_field_id ON order_custom_field_values(custom_field_id);

CREATE INDEX idx_subscription_custom_field_values_subscription_id ON subscription_custom_field_values(subscription_id);
CREATE INDEX idx_subscription_custom_field_values_custom_field_id ON subscription_custom_field_values(subscription_id);

CREATE INDEX idx_note_custom_field_values_note_id ON note_custom_field_values(note_id);
CREATE INDEX idx_note_custom_field_values_custom_field_id ON note_custom_field_values(custom_field_id);

CREATE INDEX idx_contact_opportunity_contact_id ON contact_opportunity(contact_id);
CREATE INDEX idx_contact_opportunity_opportunity_id ON contact_opportunity(opportunity_id);

CREATE INDEX idx_contact_task_contact_id ON contact_task(contact_id);
CREATE INDEX idx_contact_task_task_id ON contact_task(task_id);

CREATE INDEX idx_contact_note_contact_id ON contact_note(contact_id);
CREATE INDEX idx_contact_note_note_id ON contact_note(note_id);

CREATE INDEX idx_contact_order_contact_id ON contact_order(contact_id);
CREATE INDEX idx_contact_order_order_id ON contact_order(order_id);

CREATE INDEX idx_contact_subscription_contact_id ON contact_subscription(contact_id);
CREATE INDEX idx_contact_subscription_subscription_id ON contact_subscription(subscription_id);

CREATE INDEX idx_product_subscription_product_id ON product_subscription(product_id);
CREATE INDEX idx_product_subscription_subscription_id ON product_subscription(subscription_id);

CREATE INDEX idx_product_order_item_product_id ON product_order_item(product_id);
CREATE INDEX idx_product_order_item_order_item_id ON product_order_item(order_item_id);

CREATE INDEX idx_campaign_sequence_campaign_id ON campaign_sequence(campaign_id);
CREATE INDEX idx_campaign_sequence_sequence_id ON campaign_sequence(sequence_id);

CREATE INDEX idx_fax_numbers_number ON fax_numbers(number);
CREATE INDEX idx_fax_numbers_field ON fax_numbers(field);

CREATE INDEX idx_fax_numbers_contact_id ON fax_numbers(contact_id);

CREATE INDEX idx_payment_plans_name ON payment_plans(name);
CREATE INDEX idx_payment_plans_frequency ON payment_plans(frequency);

CREATE INDEX idx_subscription_plans_name ON subscription_plans(name);
CREATE INDEX idx_subscription_plans_frequency ON subscription_plans(frequency);

CREATE INDEX idx_business_goals_account_profile_id ON business_goals(account_profile_id);

CREATE INDEX idx_affiliate_redirect_programs_affiliate_redirect_id ON affiliate_redirect_programs(affiliate_redirect_id);
CREATE INDEX idx_affiliate_redirect_programs_program_id ON affiliate_redirect_programs(program_id);

CREATE INDEX idx_payment_gateways_name ON payment_gateways(name);
CREATE INDEX idx_payment_gateways_type ON payment_gateways(type);
CREATE INDEX idx_payment_gateways_is_active ON payment_gateways(is_active);

CREATE INDEX idx_shipping_information_order_id ON shipping_information(order_id);
CREATE INDEX idx_shipping_information_tracking_number ON shipping_information(tracking_number);
CREATE INDEX idx_shipping_information_carrier ON shipping_information(carrier);
CREATE INDEX idx_shipping_information_shipping_status ON shipping_information(shipping_status);
CREATE INDEX idx_shipping_information_shipping_date ON shipping_information(shipping_date);
CREATE INDEX idx_shipping_information_estimated_delivery_date ON shipping_information(estimated_delivery_date);

CREATE INDEX idx_tags_category_id ON tags(category_id);
CREATE INDEX idx_tag_categories_name ON tag_categories(name);

CREATE INDEX idx_credit_cards_contact_id ON credit_cards(contact_id);
CREATE INDEX idx_credit_cards_card_type ON credit_cards(card_type);
CREATE INDEX idx_credit_cards_is_default ON credit_cards(is_default);

CREATE INDEX idx_products_product_name ON products(product_name);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_product_price ON products(product_price);
CREATE INDEX idx_products_active ON products(active);
CREATE INDEX idx_products_subscription_only ON products(subscription_only);
CREATE INDEX idx_products_status ON products(status);

CREATE INDEX idx_contact_addresses_contact_id ON contact_addresses(contact_id);

CREATE INDEX idx_order_transaction_order_id ON order_transaction(order_id);
CREATE INDEX idx_order_transaction_transaction_id ON order_transaction(transaction_id);

-- =============================================
-- Create Triggers
-- =============================================

CREATE TRIGGER update_contacts_modtime
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_products_modtime
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_orders_modtime
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_opportunities_modtime
    BEFORE UPDATE ON opportunities
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_tasks_modtime
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_campaigns_modtime
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_campaign_sequences_modtime
    BEFORE UPDATE ON campaign_sequences
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_subscriptions_modtime
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_contact_custom_field_values_modtime
    BEFORE UPDATE ON contact_custom_field_values
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_custom_fields_modtime
    BEFORE UPDATE ON custom_fields
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_account_profiles_modtime
    BEFORE UPDATE ON account_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_affiliates_modtime
    BEFORE UPDATE ON affiliates
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_affiliate_programs_modtime
    BEFORE UPDATE ON affiliate_programs
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_affiliate_redirects_modtime
    BEFORE UPDATE ON affiliate_redirects
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_affiliate_summaries_modtime
    BEFORE UPDATE ON affiliate_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_payment_plans_modtime
    BEFORE UPDATE ON payment_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_subscription_plans_modtime
    BEFORE UPDATE ON subscription_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_note_custom_field_values_modtime
    BEFORE UPDATE ON note_custom_field_values
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_subscription_custom_field_values_modtime
    BEFORE UPDATE ON subscription_custom_field_values
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_payment_gateways_modtime
    BEFORE UPDATE ON payment_gateways
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_shipping_information_modtime
    BEFORE UPDATE ON shipping_information
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_credit_cards_modtime
    BEFORE UPDATE ON credit_cards
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_order_items_modtime
    BEFORE UPDATE ON order_items
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_order_payments_modtime
    BEFORE UPDATE ON order_payments
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_order_transactions_modtime
    BEFORE UPDATE ON order_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_product_options_modtime
    BEFORE UPDATE ON product_options
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column();

CREATE TRIGGER update_notes_modtime
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_at_column(); 