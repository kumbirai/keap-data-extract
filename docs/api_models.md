# Keap REST API Models

## Core Models

### Contact
- Primary entity for storing contact information
- Fields:
  - `id` (integer)
  - `given_name` (string)
  - `family_name` (string)
  - `email_addresses` (array of EmailAddress)
  - `phone_numbers` (array of PhoneNumber)
  - `company_name` (string)
  - `job_title` (string)
  - `addresses` (array of Address)
  - `created_at` (datetime)
  - `modified_at` (datetime)
  - `custom_fields` (array of CustomFieldValue)

### EmailAddress
- Contact's email address
- Fields:
  - `email` (string)
  - `field` (string, e.g., "EMAIL1", "EMAIL2")
  - `type` (string)

### PhoneNumber
- Contact's phone number
- Fields:
  - `number` (string)
  - `field` (string, e.g., "PHONE1", "PHONE2")
  - `type` (string)

### Address
- Contact's address
- Fields:
  - `street_address` (string)
  - `city` (string)
  - `state` (string)
  - `postal_code` (string)
  - `country` (string)
  - `field` (string, e.g., "BILLING", "SHIPPING")
  - `type` (string)

### Tag
- Contact tags/categories
- Fields:
  - `id` (integer)
  - `name` (string)
  - `description` (string)
  - `category` (string)
  - `created_at` (datetime)

### CustomField
- Custom field definitions
- Fields:
  - `id` (integer)
  - `name` (string)
  - `type` (string)
  - `options` (array of string)
  - `created_at` (datetime)

### CustomFieldValue
- Values for custom fields
- Fields:
  - `id` (integer)
  - `custom_field_id` (integer)
  - `value` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Sales Models

### Opportunity
- Sales opportunities
- Fields:
  - `id` (integer)
  - `contact_id` (integer)
  - `title` (string)
  - `stage` (string)
  - `value` (decimal)
  - `probability` (decimal)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### Product
- Products that can be sold
- Fields:
  - `id` (integer)
  - `product_name` (string)
  - `product_sku` (string)
  - `subscription_plan_id` (integer)
  - `subscription_only` (boolean)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### Order
- Sales orders
- Fields:
  - `id` (integer)
  - `contact_id` (integer)
  - `order_date` (datetime)
  - `order_status` (string)
  - `order_total` (decimal)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### OrderItem
- Items in an order
- Fields:
  - `id` (integer)
  - `order_id` (integer)
  - `product_id` (integer)
  - `quantity` (integer)
  - `price` (decimal)
  - `created_at` (datetime)

## Task Management Models

### Task
- Tasks and appointments
- Fields:
  - `id` (integer)
  - `contact_id` (integer)
  - `title` (string)
  - `description` (string)
  - `due_date` (datetime)
  - `completed` (boolean)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### Note
- Notes associated with contacts
- Fields:
  - `id` (integer)
  - `contact_id` (integer)
  - `title` (string)
  - `body` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Campaign Models

### Campaign
- Marketing campaigns
- Fields:
  - `id` (integer)
  - `name` (string)
  - `status` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### CampaignSequence
- Campaign sequences
- Fields:
  - `id` (integer)
  - `campaign_id` (integer)
  - `name` (string)
  - `status` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Subscription Models

### Subscription
- Subscription information
- Fields:
  - `id` (integer)
  - `contact_id` (integer)
  - `subscription_plan_id` (integer)
  - `status` (string)
  - `next_bill_date` (datetime)
  - `created_at` (datetime)
  - `modified_at` (datetime)

### SubscriptionPlan
- Subscription plan definitions
- Fields:
  - `id` (integer)
  - `plan_name` (string)
  - `plan_description` (string)
  - `frequency` (string)
  - `price` (decimal)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Webhook Models

### Webhook
- Webhook configurations
- Fields:
  - `id` (integer)
  - `event_key` (string)
  - `hook_url` (string)
  - `status` (string)
  - `created_at` (datetime)
  - `modified_at` (datetime)

## Common Fields
All models include these common fields where applicable:
- `id` (integer): Unique identifier
- `created_at` (datetime): Creation timestamp
- `modified_at` (datetime): Last modification timestamp

## Relationships
- Contacts can have multiple:
  - Email addresses
  - Phone numbers
  - Addresses
  - Tags
  - Custom field values
  - Opportunities
  - Tasks
  - Notes
  - Orders
  - Subscriptions

- Orders can have multiple:
  - Order items
  - Products

- Campaigns can have multiple:
  - Campaign sequences

- Subscriptions are linked to:
  - Contacts
  - Subscription plans 