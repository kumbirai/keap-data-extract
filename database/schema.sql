-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE address_type AS ENUM ('BILLING', 'SHIPPING', 'OTHER');
CREATE TYPE custom_field_type AS ENUM (
    'text', 'number', 'date', 'dropdown', 'multiselect', 'radio', 'checkbox',
    'url', 'email', 'phone', 'currency', 'percent', 'social', 'address',
    'image', 'file'
);

-- Create tables in order of dependencies

-- Tags table
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Account profiles table
CREATE TABLE account_profiles (
    id SERIAL PRIMARY KEY,
    address_id INTEGER REFERENCES addresses(id),
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

-- Contacts table
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    given_name VARCHAR(100),
    family_name VARCHAR(100),
    middle_name VARCHAR(100),
    company_name VARCHAR(200),
    job_title VARCHAR(200),
    email_opted_in BOOLEAN DEFAULT FALSE,
    email_status VARCHAR(50),
    score_value VARCHAR(50),
    owner_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    anniversary TIMESTAMP WITH TIME ZONE,
    birthday TIMESTAMP WITH TIME ZONE,
    contact_type VARCHAR(50),
    duplicate_option VARCHAR(50),
    lead_source_id INTEGER,
    preferred_locale VARCHAR(50),
    preferred_name VARCHAR(100),
    source_type VARCHAR(50),
    spouse_name VARCHAR(100),
    time_zone VARCHAR(50),
    website VARCHAR(255),
    year_created INTEGER
);

-- Contact-Tag association table
CREATE TABLE contact_tag (
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, tag_id)
);

-- Email addresses table
CREATE TABLE email_addresses (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Phone numbers table
CREATE TABLE phone_numbers (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Custom fields table
CREATE TABLE custom_fields (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    type VARCHAR(50),
    options JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Custom field metadata table
CREATE TABLE custom_field_metadata (
    id SERIAL PRIMARY KEY,
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

-- Create index for custom field metadata
CREATE INDEX idx_custom_field_metadata_custom_field_id ON custom_field_metadata(custom_field_id);

-- Custom field values tables
CREATE TABLE contact_custom_field_values (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(contact_id, custom_field_id)
);

CREATE TABLE opportunity_custom_field_values (
    id SERIAL PRIMARY KEY,
    opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(opportunity_id, custom_field_id)
);

CREATE TABLE order_custom_field_values (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (order_id, custom_field_id)
);

CREATE TABLE subscription_custom_field_values (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES subscriptions(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (subscription_id, custom_field_id)
);

-- Create indexes for custom field values
CREATE INDEX idx_contact_custom_field_values_contact_id ON contact_custom_field_values(contact_id);
CREATE INDEX idx_contact_custom_field_values_custom_field_id ON contact_custom_field_values(custom_field_id);
CREATE INDEX idx_opportunity_custom_field_values_opportunity_id ON opportunity_custom_field_values(opportunity_id);
CREATE INDEX idx_opportunity_custom_field_values_custom_field_id ON opportunity_custom_field_values(custom_field_id);
CREATE INDEX idx_order_custom_field_values_order_id ON order_custom_field_values(order_id);
CREATE INDEX idx_order_custom_field_values_custom_field_id ON order_custom_field_values(custom_field_id);
CREATE INDEX idx_subscription_custom_field_values_subscription_id ON subscription_custom_field_values(subscription_id);
CREATE INDEX idx_subscription_custom_field_values_custom_field_id ON subscription_custom_field_values(custom_field_id);

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    product_sku VARCHAR(100) UNIQUE,
    subscription_only BOOLEAN DEFAULT FALSE,
    plan_description TEXT,
    frequency VARCHAR(50),
    price FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50),
    order_date TIMESTAMP WITH TIME ZONE NOT NULL,
    order_status VARCHAR(50),
    order_total FLOAT,
    order_type VARCHAR(50),
    payment_plan_id INTEGER,
    payment_type VARCHAR(50),
    subscription_plan_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Order items table
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    quantity INTEGER NOT NULL,
    price FLOAT NOT NULL,
    description TEXT,
    subscription_plan_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Opportunities table
CREATE TABLE opportunities (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200),
    stage VARCHAR(100),
    value DECIMAL(15,2),
    probability DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    due_date TIMESTAMP WITH TIME ZONE,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notes table
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200),
    body TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Campaigns table
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Campaign sequences table
CREATE TABLE campaign_sequences (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    status VARCHAR(50),
    next_bill_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Affiliates table
CREATE TABLE affiliates (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    notify_on_lead BOOLEAN DEFAULT FALSE,
    notify_on_sale BOOLEAN DEFAULT FALSE,
    parent_id INTEGER REFERENCES affiliates(id),
    status VARCHAR(50),
    track_leads_for INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Affiliate commissions table
CREATE TABLE affiliate_commissions (
    id SERIAL PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount_earned FLOAT,
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

-- Affiliate programs table
CREATE TABLE affiliate_programs (
    id SERIAL PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    name VARCHAR(200),
    notes TEXT,
    priority INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Affiliate redirects table
CREATE TABLE affiliate_redirects (
    id SERIAL PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    local_url_code VARCHAR(100),
    name VARCHAR(200),
    redirect_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Affiliate summaries table
CREATE TABLE affiliate_summaries (
    id SERIAL PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount_earned FLOAT,
    balance FLOAT,
    clawbacks FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create fax numbers table
CREATE TABLE fax_numbers (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fax numbers
CREATE INDEX idx_fax_numbers_contact_id ON fax_numbers(contact_id);

-- Create indexes for better query performance
CREATE INDEX idx_contacts_company_name ON contacts(company_name);
CREATE INDEX idx_contacts_created_at ON contacts(created_at);
CREATE INDEX idx_email_addresses_email ON email_addresses(email);
CREATE INDEX idx_phone_numbers_number ON phone_numbers(number);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_opportunities_stage ON opportunities(stage);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_affiliates_code ON affiliates(code);
CREATE INDEX idx_affiliate_commissions_date_earned ON affiliate_commissions(date_earned);

-- Create function to update modified_at timestamp
CREATE OR REPLACE FUNCTION update_modified_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for modified_at
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

CREATE TRIGGER update_notes_modtime
    BEFORE UPDATE ON notes
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

-- Join tables for relationships
CREATE TABLE contact_address (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    address_id INTEGER NOT NULL REFERENCES addresses(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, address_id)
);

CREATE TABLE contact_email (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    email_id INTEGER NOT NULL REFERENCES email_addresses(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, email_id)
);

CREATE TABLE contact_phone (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    phone_id INTEGER NOT NULL REFERENCES phone_numbers(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, phone_id)
);

CREATE TABLE contact_fax (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    fax_id INTEGER NOT NULL REFERENCES fax_numbers(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, fax_id)
);

CREATE TABLE contact_opportunity (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, opportunity_id)
);

CREATE TABLE contact_task (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, task_id)
);

CREATE TABLE contact_note (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, note_id)
);

CREATE TABLE contact_order (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, order_id)
);

CREATE TABLE contact_subscription (
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, subscription_id)
);

CREATE TABLE order_item (
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, item_id)
);

CREATE TABLE product_order_item (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    order_item_id INTEGER NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, order_item_id)
);

CREATE TABLE product_subscription (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, subscription_id)
);

CREATE TABLE campaign_sequence (
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    sequence_id INTEGER NOT NULL REFERENCES campaign_sequences(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (campaign_id, sequence_id)
);

-- Add indexes for join tables
CREATE INDEX idx_contact_address_contact_id ON contact_address(contact_id);
CREATE INDEX idx_contact_address_address_id ON contact_address(address_id);
CREATE INDEX idx_contact_email_contact_id ON contact_email(contact_id);
CREATE INDEX idx_contact_email_email_id ON contact_email(email_id);
CREATE INDEX idx_contact_phone_contact_id ON contact_phone(contact_id);
CREATE INDEX idx_contact_phone_phone_id ON contact_phone(phone_id);
CREATE INDEX idx_contact_fax_contact_id ON contact_fax(contact_id);
CREATE INDEX idx_contact_fax_fax_id ON contact_fax(fax_id);
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
CREATE INDEX idx_order_item_order_id ON order_item(order_id);
CREATE INDEX idx_order_item_item_id ON order_item(item_id);
CREATE INDEX idx_product_order_item_product_id ON product_order_item(product_id);
CREATE INDEX idx_product_order_item_order_item_id ON product_order_item(order_item_id);
CREATE INDEX idx_product_subscription_product_id ON product_subscription(product_id);
CREATE INDEX idx_product_subscription_subscription_id ON product_subscription(subscription_id);
CREATE INDEX idx_campaign_sequence_campaign_id ON campaign_sequence(campaign_id);
CREATE INDEX idx_campaign_sequence_sequence_id ON campaign_sequence(sequence_id); 