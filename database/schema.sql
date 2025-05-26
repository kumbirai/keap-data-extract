-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE address_type AS ENUM ('BILLING', 'SHIPPING', 'OTHER');

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
    business_goals JSONB,
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
    last_updated_utc_millis BIGINT
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
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Phone numbers table
CREATE TABLE phone_numbers (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    number VARCHAR(50) NOT NULL,
    field VARCHAR(50),
    type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Custom fields table
CREATE TABLE custom_fields (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    options JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Custom field values table
CREATE TABLE custom_field_values (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    custom_field_id INTEGER REFERENCES custom_fields(id) ON DELETE CASCADE,
    value TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (contact_id, custom_field_id)
);

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
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
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
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
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
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
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
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
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
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
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
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    status VARCHAR(50),
    next_bill_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Affiliates table
CREATE TABLE affiliates (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL,
    contact_id INTEGER REFERENCES contacts(id),
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
    program_ids JSONB,
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

-- Affiliate clawbacks table
CREATE TABLE affiliate_clawbacks (
    id SERIAL PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount FLOAT,
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

-- Affiliate payments table
CREATE TABLE affiliate_payments (
    id SERIAL PRIMARY KEY,
    affiliate_id INTEGER REFERENCES affiliates(id),
    amount FLOAT,
    date TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_contacts_company_name ON contacts(company_name);
CREATE INDEX idx_contacts_created_at ON contacts(created_at);
CREATE INDEX idx_email_addresses_email ON email_addresses(email);
CREATE INDEX idx_phone_numbers_number ON phone_numbers(number);
CREATE INDEX idx_orders_contact_id ON orders(contact_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_opportunities_contact_id ON opportunities(contact_id);
CREATE INDEX idx_opportunities_stage ON opportunities(stage);
CREATE INDEX idx_tasks_contact_id ON tasks(contact_id);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_notes_contact_id ON notes(contact_id);
CREATE INDEX idx_subscriptions_contact_id ON subscriptions(contact_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_product_id ON subscriptions(product_id);
CREATE INDEX idx_affiliates_contact_id ON affiliates(contact_id);
CREATE INDEX idx_affiliates_code ON affiliates(code);
CREATE INDEX idx_affiliate_commissions_affiliate_id ON affiliate_commissions(affiliate_id);
CREATE INDEX idx_affiliate_commissions_contact_id ON affiliate_commissions(contact_id);
CREATE INDEX idx_affiliate_commissions_date_earned ON affiliate_commissions(date_earned);
CREATE INDEX idx_affiliate_clawbacks_affiliate_id ON affiliate_clawbacks(affiliate_id);
CREATE INDEX idx_affiliate_clawbacks_contact_id ON affiliate_clawbacks(contact_id);
CREATE INDEX idx_affiliate_clawbacks_date_earned ON affiliate_clawbacks(date_earned);

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

CREATE TRIGGER update_custom_field_values_modtime
    BEFORE UPDATE ON custom_field_values
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