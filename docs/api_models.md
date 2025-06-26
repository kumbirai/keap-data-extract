# Keap REST API Models

## Core Models

### Contact
- Primary entity for storing contact information
- Fields:
  - `id` (integer, Primary Key)
  - `given_name` (string)
  - `family_name` (string)
  - `middle_name` (string)
  - `company_name` (string)
  - `job_title` (string)
  - `email_opted_in` (boolean)
  - `email_status` (enum: UnengagedMarketable, SingleOptIn, DoubleOptIn, Confirmed, UnengagedNonMarketable, NonMarketable, Lockdown, Bounce, HardBounce, Manual, Admin, System, ListUnsubscribe, Feedback, Spam, Invalid, Deactivated)
  - `score_value` (string)
  - `owner_id` (integer)
  - `anniversary` (datetime)
  - `birthday` (datetime)
  - `contact_type` (string)
  - `duplicate_option` (string)
  - `lead_source_id` (integer)
  - `preferred_locale` (string)
  - `preferred_name` (string)
  - `source_type` (enum: API, CALL, EMAIL, FORM, IMPORT, INVOICE, ONLINE, PHONE, SMS, SYSTEM, WEBSITE, MANUAL, SOCIAL, REFERRAL, PARTNER, AFFILIATE)
  - `spouse_name` (string)
  - `time_zone` (string)
  - `website` (string)
  - `year_created` (integer)
  - `last_updated_utc_millis` (bigint)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### EmailAddress
- Contact's email address
- Fields:
  - `id` (integer, Primary Key)
  - `email` (string, Indexed)
  - `field` (string, e.g., "EMAIL1", "EMAIL2")
  - `type` (string)
  - `contact_id` (integer, Foreign Key)
  - `created_at` (datetime)

### PhoneNumber
- Contact's phone number
- Fields:
  - `id` (integer, Primary Key)
  - `number` (string, Indexed)
  - `field` (string, e.g., "PHONE1", "PHONE2")
  - `type` (string)
  - `contact_id` (integer, Foreign Key)
  - `created_at` (datetime)

### ContactAddress
- Contact's address
- Fields:
  - `id` (integer, Primary Key)
  - `country_code` (string)
  - `field` (enum: BILLING, SHIPPING, OTHER, HOME, WORK)
  - `line1` (string)
  - `line2` (string)
  - `locality` (string)
  - `postal_code` (string)
  - `region` (string)
  - `zip_code` (string)
  - `zip_four` (string)
  - `contact_id` (integer, Foreign Key)
  - `created_at` (datetime)

### FaxNumber
- Contact's fax number
- Fields:
  - `id` (integer, Primary Key)
  - `number` (string, Indexed)
  - `field` (string)
  - `type` (string)
  - `contact_id` (integer, Foreign Key)
  - `created_at` (datetime)

### TagCategory
- Tag category definitions
- Fields:
  - `id` (integer, Primary Key)
  - `name` (string, Indexed)
  - `created_at` (datetime)

### Tag
- Contact tags/categories
- Fields:
  - `id` (integer, Primary Key)
  - `name` (string, Indexed)
  - `description` (text)
  - `category_id` (integer, Foreign Key)
  - `created_at` (datetime)

### CustomField
- Custom field definitions
- Fields:
  - `id` (integer, Primary Key)
  - `name` (string)
  - `type` (enum with 30+ field types including: text, number, date, dropdown, multiselect, radio, checkbox, url, email, phone, currency, percent, social, address, image, file, list, multiline, password, time, datetime, boolean, hidden, TextArea, WholeNumber, Website, Dropdown, Text, DateTime, Date, Currency)
  - `options` (JSON)
  - `label` (string)
  - `field_name` (string)
  - `record_type` (string)
  - `default_value` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### CustomFieldValue
- Values for custom fields (multiple tables for different entity types)
- Fields:
  - `id` (integer, Primary Key)
  - `entity_id` (integer, Foreign Key - varies by table)
  - `custom_field_id` (integer, Foreign Key)
  - `value` (text)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Sales Models

### Opportunity
- Sales opportunities
- Fields:
  - `id` (integer, Primary Key)
  - `title` (string)
  - `stage` (JSON)
  - `value` (float)
  - `probability` (float)
  - `next_action_date` (datetime)
  - `next_action_notes` (text)
  - `source_type` (string)
  - `source_id` (integer)
  - `pipeline_id` (integer)
  - `pipeline_stage_id` (integer)
  - `owner_id` (integer)
  - `last_updated_utc_millis` (bigint)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### Product
- Products that can be sold
- Fields:
  - `id` (integer, Primary Key)
  - `sku` (string)
  - `active` (boolean)
  - `url` (string)
  - `product_name` (string)
  - `sub_category_id` (integer)
  - `product_desc` (text)
  - `product_price` (numeric)
  - `product_short_desc` (text)
  - `subscription_only` (boolean)
  - `status` (integer)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### ProductOption
- Product options/variants
- Fields:
  - `id` (integer, Primary Key)
  - `product_id` (integer, Foreign Key)
  - `name` (string)
  - `price` (numeric)
  - `sku` (string)
  - `description` (text)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### Order
- Sales orders
- Fields:
  - `id` (integer, Primary Key)
  - `title` (string)
  - `status` (enum: DRAFT, PENDING, PAID, REFUNDED, CANCELLED, FAILED, PARTIALLY_PAID, PARTIALLY_REFUNDED, VOID, PROCESSING, ON_HOLD)
  - `recurring` (boolean)
  - `total` (numeric)
  - `notes` (text)
  - `terms` (text)
  - `order_type` (string)
  - `source_type` (enum: API, CALL, EMAIL, FORM, IMPORT, INVOICE, ONLINE, PHONE, SMS, SYSTEM, WEBSITE, MANUAL, SOCIAL, REFERRAL, PARTNER, AFFILIATE)
  - `creation_date` (datetime)
  - `modification_date` (datetime)
  - `order_date` (datetime)
  - `lead_affiliate_id` (integer)
  - `sales_affiliate_id` (integer)
  - `total_paid` (numeric)
  - `total_due` (numeric)
  - `refund_total` (numeric)
  - `allow_payment` (boolean)
  - `allow_paypal` (boolean)
  - `invoice_number` (integer)
  - `contact_id` (integer, Foreign Key)
  - `product_id` (integer)
  - `payment_gateway_id` (integer, Foreign Key)
  - `subscription_plan_id` (integer, Foreign Key)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### OrderItem
- Items in an order
- Fields:
  - `id` (integer, Primary Key)
  - `order_id` (integer, Foreign Key)
  - `job_recurring_id` (integer)
  - `name` (string)
  - `description` (text)
  - `type` (string)
  - `notes` (text)
  - `quantity` (integer)
  - `cost` (numeric)
  - `price` (numeric)
  - `discount` (numeric)
  - `special_id` (integer)
  - `special_amount` (numeric)
  - `special_pct_or_amt` (integer)
  - `product_id` (integer, Foreign Key)
  - `subscription_plan_id` (integer, Foreign Key)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### OrderPayment
- Payment information for orders
- Fields:
  - `id` (integer, Primary Key)
  - `order_id` (integer, Foreign Key)
  - `amount` (numeric)
  - `note` (text)
  - `invoice_id` (integer)
  - `payment_id` (integer)
  - `pay_date` (datetime)
  - `pay_status` (string)
  - `last_updated` (datetime)
  - `skip_commission` (boolean)
  - `refund_invoice_payment_id` (integer)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### OrderTransaction
- Transaction information
- Fields:
  - `id` (integer, Primary Key)
  - `test` (boolean)
  - `amount` (numeric)
  - `currency` (string)
  - `gateway` (string)
  - `payment_date` (datetime)
  - `type` (string)
  - `status` (string)
  - `errors` (text)
  - `contact_id` (integer, Foreign Key)
  - `transaction_date` (datetime)
  - `gateway_account_name` (string)
  - `order_ids` (string)
  - `collection_method` (string)
  - `payment_id` (integer)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### PaymentPlan
- Payment plan information
- Fields:
  - `id` (integer, Primary Key)
  - `order_id` (integer, Foreign Key)
  - `auto_charge` (boolean)
  - `credit_card_id` (integer)
  - `days_between_payments` (integer)
  - `initial_payment_amount` (numeric)
  - `initial_payment_percent` (numeric)
  - `initial_payment_date` (date)
  - `number_of_payments` (integer)
  - `merchant_account_id` (integer)
  - `merchant_account_name` (string)
  - `plan_start_date` (date)
  - `payment_method_id` (string)
  - `max_charge_attempts` (integer)
  - `days_between_retries` (integer)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### ShippingInformation
- Shipping information for orders
- Fields:
  - `id` (integer, Primary Key)
  - `order_id` (integer, Foreign Key)
  - `first_name` (string)
  - `middle_name` (string)
  - `last_name` (string)
  - `company` (string)
  - `phone` (string)
  - `street1` (string)
  - `street2` (string)
  - `city` (string)
  - `state` (string)
  - `zip` (string)
  - `country` (string)
  - `tracking_number` (string)
  - `carrier` (string)
  - `shipping_status` (string)
  - `shipping_date` (datetime)
  - `estimated_delivery_date` (datetime)
  - `invoice_to_company` (boolean)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Task Management Models

### Task
- Tasks and appointments
- Fields:
  - `id` (integer, Primary Key)
  - `contact_id` (integer, Foreign Key)
  - `title` (string)
  - `notes` (text)
  - `priority` (enum: LOW, MEDIUM, HIGH, URGENT)
  - `status` (enum: PENDING, COMPLETED, CANCELLED, DEFERRED, WAITING, IN_PROGRESS)
  - `type` (string)
  - `due_date` (datetime)
  - `completed_date` (datetime)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### Note
- Notes associated with contacts
- Fields:
  - `id` (integer, Primary Key)
  - `contact_id` (integer, Foreign Key)
  - `title` (string)
  - `body` (text)
  - `type` (enum with 35+ types including: Call, Email, Fax, Letter, Meeting, Other, Task, SMS, Social, Chat, Voicemail, Website, Form, Appointment, Campaign, Contact, Deal, Document, File, Follow Up, Invoice, Order, Product, Purchase, Recurring Order, Referral, Refund, Subscription, Survey, Tag, Template, Transaction, User, Webform, Workflow)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Campaign Models

### Campaign
- Marketing campaigns
- Fields:
  - `id` (integer, Primary Key)
  - `name` (string)
  - `description` (text)
  - `status` (enum: Draft, Active, Paused, Completed, Archived, Scheduled, Stopped)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### CampaignSequence
- Campaign sequences
- Fields:
  - `id` (integer, Primary Key)
  - `campaign_id` (integer, Foreign Key)
  - `name` (string)
  - `description` (text)
  - `status` (string)
  - `sequence_number` (integer)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Subscription Models

### Subscription
- Subscription information
- Fields:
  - `id` (integer, Primary Key)
  - `product_id` (integer, Foreign Key)
  - `subscription_plan_id` (integer, Foreign Key)
  - `status` (enum: Active, Cancelled, Expired, Paused, Trial, Past Due, Pending, Failed, On Hold)
  - `next_bill_date` (datetime)
  - `contact_id` (integer, Foreign Key)
  - `payment_gateway_id` (integer, Foreign Key)
  - `credit_card_id` (integer, Foreign Key)
  - `start_date` (datetime)
  - `end_date` (datetime)
  - `billing_cycle` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### SubscriptionPlan
- Subscription plan definitions
- Fields:
  - `id` (integer, Primary Key)
  - `product_id` (integer, Foreign Key)
  - `name` (string)
  - `description` (text)
  - `frequency` (string)
  - `subscription_plan_price` (numeric)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Affiliate Models

### Affiliate
- Affiliate information
- Fields:
  - `id` (integer, Primary Key)
  - `contact_id` (integer, Foreign Key)
  - `parent_id` (integer)
  - `status` (enum: Active, Inactive, Pending, Suspended, Terminated)
  - `code` (string)
  - `name` (string)
  - `email` (string)
  - `company` (string)
  - `website` (string)
  - `phone` (string)
  - `address1` (string)
  - `address2` (string)
  - `city` (string)
  - `state` (string)
  - `postal_code` (string)
  - `country` (string)
  - `tax_id` (string)
  - `payment_email` (string)
  - `notify_on_lead` (boolean)
  - `notify_on_sale` (boolean)
  - `track_leads_for` (integer)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### AffiliateCommission
- Affiliate commission information
- Fields:
  - `id` (integer, Primary Key)
  - `affiliate_id` (integer, Foreign Key)
  - `amount_earned` (numeric)
  - `contact_id` (integer, Foreign Key)
  - `contact_first_name` (string)
  - `contact_last_name` (string)
  - `date_earned` (datetime)
  - `description` (text)
  - `invoice_id` (integer)
  - `product_name` (string)
  - `sales_affiliate_id` (integer)
  - `sold_by_first_name` (string)
  - `sold_by_last_name` (string)
  - `created_at` (datetime)

### AffiliateProgram
- Affiliate program information
- Fields:
  - `id` (integer, Primary Key)
  - `affiliate_id` (integer, Foreign Key)
  - `name` (string)
  - `notes` (text)
  - `priority` (integer)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### AffiliateRedirect
- Affiliate redirect information
- Fields:
  - `id` (integer, Primary Key)
  - `affiliate_id` (integer, Foreign Key)
  - `local_url_code` (string)
  - `name` (string)
  - `redirect_url` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### AffiliateSummary
- Affiliate summary information
- Fields:
  - `id` (integer, Primary Key)
  - `affiliate_id` (integer, Foreign Key)
  - `amount_earned` (numeric)
  - `balance` (numeric)
  - `clawbacks` (numeric)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### AffiliateClawback
- Affiliate clawback information
- Fields:
  - `id` (integer, Primary Key)
  - `affiliate_id` (integer, Foreign Key)
  - `amount` (numeric)
  - `contact_id` (integer, Foreign Key)
  - `date_earned` (datetime)
  - `description` (text)
  - `family_name` (string)
  - `given_name` (string)
  - `invoice_id` (integer)
  - `product_name` (string)
  - `sale_affiliate_id` (integer)
  - `sold_by_family_name` (string)
  - `sold_by_given_name` (string)
  - `subscription_plan_name` (string)
  - `created_at` (datetime)

### AffiliatePayment
- Affiliate payment information
- Fields:
  - `id` (integer, Primary Key)
  - `affiliate_id` (integer, Foreign Key)
  - `amount` (numeric)
  - `date` (datetime)
  - `notes` (text)
  - `type` (string)
  - `created_at` (datetime)

### AffiliateRedirectProgram
- Junction table for affiliate redirects and programs
- Fields:
  - `id` (integer, Primary Key)
  - `affiliate_redirect_id` (integer, Foreign Key)
  - `program_id` (integer)
  - `created_at` (datetime)

## Account Models

### AccountProfile
- Account profile information
- Fields:
  - `id` (integer, Primary Key)
  - `address_id` (integer, Foreign Key)
  - `business_primary_color` (string)
  - `business_secondary_color` (string)
  - `business_type` (string)
  - `currency_code` (string)
  - `email` (string)
  - `language_tag` (string)
  - `logo_url` (string)
  - `name` (string)
  - `phone` (string)
  - `phone_ext` (string)
  - `time_zone` (string)
  - `website` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### BusinessGoal
- Business goal information
- Fields:
  - `id` (integer, Primary Key)
  - `account_profile_id` (integer, Foreign Key)
  - `goal` (string)
  - `created_at` (datetime)

## Payment Models

### CreditCard
- Credit card information
- Fields:
  - `id` (integer, Primary Key)
  - `contact_id` (integer, Foreign Key)
  - `card_type` (string)
  - `card_number` (string)
  - `expiration_month` (integer)
  - `expiration_year` (integer)
  - `card_holder_name` (string)
  - `is_default` (boolean)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### PaymentGateway
- Payment gateway information
- Fields:
  - `id` (integer, Primary Key)
  - `name` (string)
  - `type` (string)
  - `is_active` (boolean)
  - `credentials` (JSON)
  - `settings` (JSON)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Junction Tables

### Contact Relationships
- `contact_tag` - Many-to-many relationship between contacts and tags
- `contact_opportunity` - Many-to-many relationship between contacts and opportunities
- `contact_task` - Many-to-many relationship between contacts and tasks
- `contact_note` - Many-to-many relationship between contacts and notes
- `contact_order` - Many-to-many relationship between contacts and orders
- `contact_subscription` - Many-to-many relationship between contacts and subscriptions

### Product Relationships
- `product_subscription` - Many-to-many relationship between products and subscriptions
- `product_order_item` - Many-to-many relationship between products and order items

### Campaign Relationships
- `campaign_sequence` - Many-to-many relationship between campaigns and sequences

### Order Relationships
- `order_transaction` - Many-to-many relationship between orders and transactions

## Common Fields
All models include these common fields where applicable:
- `id` (integer): Unique identifier
- `created_at` (datetime): Creation timestamp
- `modified_at` (datetime): Last modification timestamp (with automatic triggers)

## Relationships
- Contacts can have multiple:
  - Email addresses
  - Phone numbers
  - Addresses
  - Fax numbers
  - Tags (many-to-many)
  - Custom field values
  - Opportunities (many-to-many)
  - Tasks (many-to-many)
  - Notes (many-to-many)
  - Orders (many-to-many)
  - Subscriptions (many-to-many)
  - Credit cards
  - Affiliate record

- Orders can have multiple:
  - Order items
  - Order payments
  - Order transactions
  - Custom field values
  - Shipping information
  - Payment plan

- Products can have multiple:
  - Product options
  - Subscription plans
  - Order items
  - Subscriptions (many-to-many)

- Campaigns can have multiple:
  - Campaign sequences (many-to-many)

- Affiliates can have multiple:
  - Commissions
  - Programs
  - Redirects
  - Clawbacks
  - Payments
  - Summary record

- Subscriptions are linked to:
  - Contacts (many-to-many)
  - Products (many-to-many)
  - Subscription plans
  - Payment gateways
  - Credit cards
  - Custom field values

## Database Features

### Indexing Strategy
- Comprehensive indexing on frequently queried fields
- Composite indexes for common query patterns
- Foreign key indexes for relationship performance
- Text search indexes for name and description fields

### Constraints
- Primary key constraints on all tables
- Foreign key constraints with proper cascade options
- Unique constraints where appropriate
- Check constraints for data validation

### Triggers
- Automatic `modified_at` timestamp updates
- Data validation triggers
- Audit trail triggers

### Performance Optimizations
- Efficient query patterns
- Proper indexing strategy
- Connection pooling
- Batch processing capabilities 