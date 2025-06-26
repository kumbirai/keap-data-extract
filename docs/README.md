# Keap Data Extraction Project Documentation

## Project Overview
This project is designed to extract data from the Keap (formerly Infusionsoft) CRM system using their REST API and store it in a PostgreSQL database. The project implements a robust API client and database models to handle various Keap entities with comprehensive error handling, logging, and data transformation capabilities.

## Project Structure
```
keap-data-extract/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── base_client.py
│   │   ├── keap_client.py
│   │   ├── exceptions.py
│   │   └── validators.py
│   ├── database/
│   │   ├── config.py
│   │   └── init_db.py
│   ├── models/
│   │   └── models.py
│   ├── transformers/
│   │   └── transformers.py
│   ├── utils/
│   │   ├── error_logger.py
│   │   ├── global_logger.py
│   │   ├── logger.py
│   │   ├── logging_config.py
│   │   └── retry.py
│   └── scripts/
│       ├── load_data_manager.py
│       ├── load_data.py
│       ├── reprocess_errors.py
│       └── loaders/
│           ├── __init__.py
│           ├── affiliate_loader.py
│           ├── base_loader.py
│           ├── contact_loader.py
│           ├── custom_fields_loader.py
│           ├── loader_factory.py
│           ├── order_loader.py
│           ├── product_loader.py
│           └── tags_loader.py
├── docs/
│   ├── README.md
│   ├── api_models.md
│   └── V1.json
├── database/
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   └── schema.sql
├── requirements.txt
└── .env
```

## Database Design

### Core Tables

#### Contacts (`contacts`)
- Primary entity storing contact information
- Fields:
  - `id` (Primary Key)
  - `given_name`, `family_name`, `middle_name`
  - `company_name`, `job_title`
  - `email_opted_in`, `email_status` (enum)
  - `score_value`, `owner_id`
  - `anniversary`, `birthday`
  - `contact_type`, `duplicate_option`
  - `lead_source_id`, `preferred_locale`
  - `preferred_name`, `source_type` (enum)
  - `spouse_name`, `time_zone`, `website`
  - `year_created`, `last_updated_utc_millis`
  - `created_at`, `modified_at`

#### Email Addresses (`email_addresses`)
- Stores contact email addresses
- Fields:
  - `id` (Primary Key)
  - `email` (Indexed)
  - `field` (e.g., "EMAIL1", "EMAIL2")
  - `type`
  - `contact_id` (Foreign Key)
  - `created_at`

#### Phone Numbers (`phone_numbers`)
- Stores contact phone numbers
- Fields:
  - `id` (Primary Key)
  - `number` (Indexed)
  - `field` (e.g., "PHONE1", "PHONE2")
  - `type`
  - `contact_id` (Foreign Key)
  - `created_at`

#### Contact Addresses (`contact_addresses`)
- Stores contact addresses
- Fields:
  - `id` (Primary Key)
  - `country_code`, `field` (enum: BILLING, SHIPPING, OTHER, HOME, WORK)
  - `line1`, `line2`, `locality`, `region`
  - `postal_code`, `zip_code`, `zip_four`
  - `contact_id` (Foreign Key)
  - `created_at`

#### Fax Numbers (`fax_numbers`)
- Stores contact fax numbers
- Fields:
  - `id` (Primary Key)
  - `number` (Indexed)
  - `field`, `type`
  - `contact_id` (Foreign Key)
  - `created_at`

#### Tags (`tags`)
- Stores tag definitions
- Fields:
  - `id` (Primary Key)
  - `name` (Indexed)
  - `description`
  - `category_id` (Foreign Key to tag_categories)
  - `created_at`

#### Tag Categories (`tag_categories`)
- Stores tag category definitions
- Fields:
  - `id` (Primary Key)
  - `name` (Indexed)
  - `created_at`

#### Custom Fields (`custom_fields`)
- Stores custom field definitions
- Fields:
  - `id` (Primary Key)
  - `name`, `type` (enum with 30+ field types)
  - `options` (JSON)
  - `label`, `field_name`, `record_type`
  - `default_value`
  - `created_at`, `modified_at`

#### Custom Field Values
Multiple tables for different entity types:
- `contact_custom_field_values`
- `opportunity_custom_field_values`
- `order_custom_field_values`
- `subscription_custom_field_values`
- `note_custom_field_values`

#### Opportunities (`opportunities`)
- Stores sales opportunities
- Fields:
  - `id` (Primary Key)
  - `title`, `stage` (JSON)
  - `value`, `probability`
  - `next_action_date`, `next_action_notes`
  - `source_type`, `source_id`
  - `pipeline_id`, `pipeline_stage_id`
  - `owner_id`, `last_updated_utc_millis`
  - `created_at`, `modified_at`

#### Orders (`orders`)
- Stores sales orders
- Fields:
  - `id` (Primary Key)
  - `title`, `status` (enum)
  - `recurring`, `total`, `notes`, `terms`
  - `order_type`, `source_type` (enum)
  - `creation_date`, `modification_date`, `order_date`
  - `lead_affiliate_id`, `sales_affiliate_id`
  - `total_paid`, `total_due`, `refund_total`
  - `allow_payment`, `allow_paypal`
  - `invoice_number`, `contact_id`
  - `product_id`, `payment_gateway_id`, `subscription_plan_id`
  - `created_at`, `modified_at`

#### Order Items (`order_items`)
- Stores items in orders
- Fields:
  - `id` (Primary Key)
  - `order_id` (Foreign Key)
  - `job_recurring_id`, `name`, `description`
  - `type`, `notes`, `quantity`
  - `cost`, `price`, `discount`
  - `special_id`, `special_amount`, `special_pct_or_amt`
  - `product_id`, `subscription_plan_id`
  - `created_at`, `modified_at`

#### Order Payments (`order_payments`)
- Stores payment information for orders
- Fields:
  - `id` (Primary Key)
  - `order_id` (Foreign Key)
  - `amount`, `note`, `invoice_id`, `payment_id`
  - `pay_date`, `pay_status`, `last_updated`
  - `skip_commission`, `refund_invoice_payment_id`
  - `created_at`, `modified_at`

#### Order Transactions (`order_transactions`)
- Stores transaction information
- Fields:
  - `id` (Primary Key)
  - `test`, `amount`, `currency`, `gateway`
  - `payment_date`, `type`, `status`, `errors`
  - `contact_id`, `transaction_date`
  - `gateway_account_name`, `order_ids`
  - `collection_method`, `payment_id`
  - `created_at`, `modified_at`

#### Tasks (`tasks`)
- Stores tasks associated with contacts
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `title`, `notes`
  - `priority` (enum: LOW, MEDIUM, HIGH, URGENT)
  - `status` (enum: PENDING, COMPLETED, CANCELLED, DEFERRED, WAITING, IN_PROGRESS)
  - `type`, `due_date`, `completed_date`
  - `created_at`, `modified_at`

#### Notes (`notes`)
- Stores notes associated with contacts
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `title`, `body`
  - `type` (enum with 35+ note types)
  - `created_at`, `modified_at`

#### Products (`products`)
- Stores product information
- Fields:
  - `id` (Primary Key)
  - `sku`, `active`, `url`
  - `product_name`, `sub_category_id`
  - `product_desc`, `product_price`
  - `product_short_desc`
  - `subscription_only`, `status`
  - `created_at`, `modified_at`

#### Product Options (`product_options`)
- Stores product option information
- Fields:
  - `id` (Primary Key)
  - `product_id` (Foreign Key)
  - `name`, `price`, `sku`, `description`
  - `created_at`, `modified_at`

#### Subscriptions (`subscriptions`)
- Stores subscription information
- Fields:
  - `id` (Primary Key)
  - `product_id`, `subscription_plan_id`
  - `status` (enum: Active, Cancelled, Expired, Paused, Trial, Past Due, Pending, Failed, On Hold)
  - `next_bill_date`, `contact_id`
  - `payment_gateway_id`, `credit_card_id`
  - `start_date`, `end_date`, `billing_cycle`
  - `created_at`, `modified_at`

#### Subscription Plans (`subscription_plans`)
- Stores subscription plan definitions
- Fields:
  - `id` (Primary Key)
  - `product_id` (Foreign Key)
  - `name`, `description`, `frequency`
  - `subscription_plan_price`
  - `created_at`, `modified_at`

#### Campaigns (`campaigns`)
- Stores marketing campaigns
- Fields:
  - `id` (Primary Key)
  - `name`, `description`
  - `status` (enum: Draft, Active, Paused, Completed, Archived, Scheduled, Stopped)
  - `created_at`, `modified_at`

#### Campaign Sequences (`campaign_sequences`)
- Stores campaign sequences
- Fields:
  - `id` (Primary Key)
  - `campaign_id` (Foreign Key)
  - `name`, `description`, `status`
  - `sequence_number`
  - `created_at`, `modified_at`

#### Affiliates (`affiliates`)
- Stores affiliate information
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `parent_id`, `status` (enum)
  - `code`, `name`, `email`, `company`
  - `website`, `phone`, `address1`, `address2`
  - `city`, `state`, `postal_code`, `country`
  - `tax_id`, `payment_email`
  - `notify_on_lead`, `notify_on_sale`
  - `track_leads_for`
  - `created_at`, `modified_at`

#### Affiliate Commissions (`affiliate_commissions`)
- Stores affiliate commission information
- Fields:
  - `id` (Primary Key)
  - `affiliate_id` (Foreign Key)
  - `amount_earned`, `contact_id`
  - `contact_first_name`, `contact_last_name`
  - `date_earned`, `description`
  - `invoice_id`, `product_name`
  - `sales_affiliate_id`
  - `sold_by_first_name`, `sold_by_last_name`
  - `created_at`

#### Affiliate Programs (`affiliate_programs`)
- Stores affiliate program information
- Fields:
  - `id` (Primary Key)
  - `affiliate_id` (Foreign Key)
  - `name`, `notes`, `priority`
  - `created_at`, `modified_at`

#### Affiliate Redirects (`affiliate_redirects`)
- Stores affiliate redirect information
- Fields:
  - `id` (Primary Key)
  - `affiliate_id` (Foreign Key)
  - `local_url_code`, `name`, `redirect_url`
  - `created_at`, `modified_at`

#### Affiliate Summaries (`affiliate_summaries`)
- Stores affiliate summary information
- Fields:
  - `id` (Primary Key)
  - `affiliate_id` (Foreign Key)
  - `amount_earned`, `balance`, `clawbacks`
  - `created_at`, `modified_at`

#### Affiliate Clawbacks (`affiliate_clawbacks`)
- Stores affiliate clawback information
- Fields:
  - `id` (Primary Key)
  - `affiliate_id` (Foreign Key)
  - `amount`, `contact_id`
  - `date_earned`, `description`
  - `family_name`, `given_name`
  - `invoice_id`, `product_name`
  - `sale_affiliate_id`
  - `sold_by_family_name`, `sold_by_given_name`
  - `subscription_plan_name`
  - `created_at`

#### Affiliate Payments (`affiliate_payments`)
- Stores affiliate payment information
- Fields:
  - `id` (Primary Key)
  - `affiliate_id` (Foreign Key)
  - `amount`, `date`, `notes`, `type`
  - `created_at`

#### Account Profiles (`account_profiles`)
- Stores account profile information
- Fields:
  - `id` (Primary Key)
  - `address_id` (Foreign Key)
  - `business_primary_color`, `business_secondary_color`
  - `business_type`, `currency_code`, `email`
  - `language_tag`, `logo_url`, `name`
  - `phone`, `phone_ext`, `time_zone`, `website`
  - `created_at`, `modified_at`

#### Business Goals (`business_goals`)
- Stores business goal information
- Fields:
  - `id` (Primary Key)
  - `account_profile_id` (Foreign Key)
  - `goal`
  - `created_at`

#### Credit Cards (`credit_cards`)
- Stores credit card information
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `card_type`, `card_number`
  - `expiration_month`, `expiration_year`
  - `card_holder_name`, `is_default`
  - `created_at`, `modified_at`

#### Payment Gateways (`payment_gateways`)
- Stores payment gateway information
- Fields:
  - `id` (Primary Key)
  - `name`, `type`, `is_active`
  - `credentials` (JSON), `settings` (JSON)
  - `created_at`, `modified_at`

#### Shipping Information (`shipping_information`)
- Stores shipping information for orders
- Fields:
  - `id` (Primary Key)
  - `order_id` (Foreign Key)
  - `first_name`, `middle_name`, `last_name`
  - `company`, `phone`, `street1`, `street2`
  - `city`, `state`, `zip`, `country`
  - `tracking_number`, `carrier`, `shipping_status`
  - `shipping_date`, `estimated_delivery_date`
  - `invoice_to_company`
  - `created_at`, `modified_at`

#### Payment Plans (`payment_plans`)
- Stores payment plan information
- Fields:
  - `id` (Primary Key)
  - `order_id` (Foreign Key)
  - `auto_charge`, `credit_card_id`
  - `days_between_payments`
  - `initial_payment_amount`, `initial_payment_percent`
  - `initial_payment_date`, `number_of_payments`
  - `merchant_account_id`, `merchant_account_name`
  - `plan_start_date`, `payment_method_id`
  - `max_charge_attempts`, `days_between_retries`
  - `created_at`, `modified_at`

### Junction Tables
- `contact_tag` - Many-to-many relationship between contacts and tags
- `contact_opportunity` - Many-to-many relationship between contacts and opportunities
- `contact_task` - Many-to-many relationship between contacts and tasks
- `contact_note` - Many-to-many relationship between contacts and notes
- `contact_order` - Many-to-many relationship between contacts and orders
- `contact_subscription` - Many-to-many relationship between contacts and subscriptions
- `product_subscription` - Many-to-many relationship between products and subscriptions
- `product_order_item` - Many-to-many relationship between products and order items
- `campaign_sequence` - Many-to-many relationship between campaigns and sequences
- `affiliate_redirect_programs` - Many-to-many relationship between affiliate redirects and programs
- `order_transaction` - Many-to-many relationship between orders and transactions

## API Client Implementation

### Base Client (`KeapBaseClient`)
Located in `src/api/base_client.py`, this class provides:
- Authentication handling using API key
- Base URL management (`https://api.infusionsoft.com/crm/rest`)
- Common request functionality with retry mechanism
- Error handling for API requests
- Session management with connection pooling

### Main Client (`KeapClient`)
Located in `src/api/keap_client.py`, implements comprehensive GET operations:

#### Contact Operations
- `get_contacts(limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get all contacts with pagination and optional filtering
- `get_contact(contact_id)`: Get a specific contact with all related data
- `get_contact_model()`: Get the contact model definition from the API
- `get_contact_tags(contact_id, limit=50, offset=0, since=None, **additional_params)`: Get tags for a contact
- `get_contact_credit_cards(contact_id, limit=50, offset=0, since=None, **additional_params)`: Get credit cards for a contact

#### Tag Operations
- `get_tags(limit=50, offset=0, since=None, **additional_params)`: Get all tags with pagination
- `get_tag(tag_id)`: Get a specific tag

#### Custom Field Operations
- `get_custom_fields(entity_type='contacts', **additional_params)`: Get custom fields for specific entity types
- `get_all_custom_fields(**additional_params)`: Get all custom fields across all entity types

#### Opportunity Operations
- `get_opportunities(contact_id=None, limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get opportunities with optional contact filtering
- `get_opportunity(opportunity_id)`: Get a specific opportunity

#### Product Operations
- `get_products(limit=50, offset=0, subscription_only=None, since=None, db_session=None, **additional_params)`: Get products with optional filtering
- `get_product(product_id)`: Get a specific product

#### Order Operations
- `get_orders(contact_id=None, limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get orders with optional contact filtering
- `get_order(order_id)`: Get a specific order
- `get_order_items(order_id)`: Get items for a specific order
- `get_order_payments(order_id)`: Get payments for a specific order
- `get_order_transactions(order_id)`: Get transactions for a specific order

#### Task Operations
- `get_tasks(contact_id=None, limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get tasks with optional contact filtering
- `get_task(task_id)`: Get a specific task

#### Note Operations
- `get_notes(contact_id=None, limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get notes with optional contact filtering
- `get_note(note_id)`: Get a specific note

#### Campaign Operations
- `get_campaigns(limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get campaigns with pagination
- `get_campaign(campaign_id)`: Get a specific campaign

#### Subscription Operations
- `get_subscriptions(contact_id=None, limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get subscriptions with optional contact filtering

#### Account Operations
- `get_account_profile()`: Get account profile information

#### Affiliate Operations
- `get_affiliates(limit=50, offset=0, since=None, db_session=None, **additional_params)`: Get affiliates with pagination
- `get_affiliate(affiliate_id)`: Get a specific affiliate
- `get_affiliate_commissions(affiliate_id, limit=50, offset=0, since=None, **additional_params)`: Get commissions for an affiliate
- `get_affiliate_programs(affiliate_id, limit=50, offset=0, since=None, **additional_params)`: Get programs for an affiliate
- `get_affiliate_redirects(affiliate_id, limit=50, offset=0, since=None, **additional_params)`: Get redirects for an affiliate
- `get_affiliate_summary(affiliate_id)`: Get summary for an affiliate
- `get_affiliate_clawbacks(affiliate_id, limit=50, offset=0, since=None, **additional_params)`: Get clawbacks for an affiliate
- `get_affiliate_payments(affiliate_id, limit=50, offset=0, since=None, **additional_params)`: Get payments for an affiliate

## Configuration

### Environment Variables
Required environment variables in `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=keap_db
DB_USER=postgres
DB_PASSWORD=secret
KEAP_API_KEY=your_api_key_here
```

### Dependencies
Key dependencies in `requirements.txt`:
- `sqlalchemy>=2.0.0`: Database ORM
- `psycopg2-binary>=2.9.9`: PostgreSQL adapter
- `requests>=2.31.0`: HTTP client
- `python-dotenv>=1.0.0`: Environment variable management
- `alembic>=1.13.1`: Database migrations
- `pyinstaller>=6.3.0`: Application packaging
- `python-dateutil~=2.9.0.post0`: Date parsing utilities

## Error Handling and Validation

### Custom Exceptions
The API client implements a comprehensive hierarchy of custom exceptions:
- `KeapAPIError`: Base exception for all API-related errors
- `KeapAuthenticationError`: Authentication and authorization issues
- `KeapValidationError`: Input validation failures
- `KeapRateLimitError`: Rate limit exceeded
- `KeapNotFoundError`: Resource not found
- `KeapServerError`: Server-side errors

### Input Validation
The client includes comprehensive input validation:
- Email format validation
- Pagination parameter validation (limit/offset)
- ID validation for all entities
- Required field validation for data objects
- Data type validation
- Range validation for numeric values
- Enum value validation

### Logging
The client implements structured logging with multiple loggers:
- `src.utils.logging_config`: Centralized logging configuration
- `src.utils.global_logger`: Global logger instance
- `src.utils.error_logger`: Error-specific logging
- `src.utils.logger`: General logging utilities

Example of error handling:
```python
from src.api import KeapClient
from src.api.exceptions import KeapValidationError, KeapAPIError

client = KeapClient()

try:
    # This will raise KeapValidationError if email is invalid
    contacts = client.get_contacts(email="invalid-email")
except KeapValidationError as e:
    print(f"Validation error: {e}")
except KeapAPIError as e:
    print(f"API error: {e}")
```

## Best Practices

### Connection Management
- Uses connection pooling via `requests.Session`
- Proper cleanup of resources
- Automatic session management
- Retry mechanism with exponential backoff

### Rate Limiting
- Built-in rate limit detection
- Proper error handling for rate limit responses
- Automatic retry logic for rate-limited requests
- Configurable retry parameters

### Data Validation
- Input validation before making API calls
- Response validation
- Type checking
- Range validation
- Enum value validation

### Error Recovery
- Graceful error handling
- Detailed error messages
- Proper exception hierarchy
- Comprehensive logging for debugging

### Security
- API key validation
- Secure header management
- No sensitive data logging
- Environment variable usage for secrets

## Usage Example with Error Handling

```python
from src.api import KeapClient
from src.api.exceptions import KeapValidationError, KeapAPIError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

try:
    client = KeapClient()
    
    # Get contacts with validation
    contacts, pagination = client.get_contacts(
        limit=100,
        offset=0,
        since="2024-01-01T00:00:00Z"
    )
    
    # Get a specific contact
    contact = client.get_contact(contact_id=123)
    
    # Get contact's tags
    contact_tags, tag_pagination = client.get_contact_tags(contact_id=123)
    
    # Get custom fields
    custom_fields, cf_pagination = client.get_custom_fields(entity_type='contacts')
    
    # Get opportunities
    opportunities, opp_pagination = client.get_opportunities(contact_id=123)
    
    # Get orders
    orders, order_pagination = client.get_orders(contact_id=123)
    
    # Get tasks
    tasks, task_pagination = client.get_tasks(contact_id=123)
    
    # Get notes
    notes, note_pagination = client.get_notes(contact_id=123)
    
    # Get affiliate data
    affiliates, affiliate_pagination = client.get_affiliates()
    
except KeapValidationError as e:
    logging.error(f"Validation error: {e}")
except KeapAPIError as e:
    logging.error(f"API error: {e}")
except Exception as e:
    logging.error(f"Unexpected error: {e}")
```

## Logging Configuration

The application implements a centralized logging system that writes logs to both console and file:

### Log File Configuration
- Log files are stored in the `logs` directory
- Files are named with pattern: `keap_data_extract_YYYYMMDD.log`
- Log rotation is enabled:
  - Maximum file size: 10MB
  - Maximum backup files: 5
  - Automatic rotation when size limit is reached

### Log Format
- File logs include:
  - Timestamp
  - Logger name
  - Log level
  - Message
- Console logs include:
  - Timestamp
  - Log level
  - Message

### Log Levels
- Default level: INFO
- Third-party library logging is set to WARNING
- Configurable through `setup_logging` function

### Usage Example
```python
from src.utils.logging_config import setup_logging
import logging

# Configure logging
setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    app_name="keap_data_extract"
)

# Get logger for your module
logger = logging.getLogger(__name__)

# Use logger
logger.info("Application started")
logger.error("An error occurred", exc_info=True)
```

### Log File Structure
```
logs/
├── keap_data_extract_20240315.log
├── keap_data_extract_20240315.log.1
├── keap_data_extract_20240315.log.2
└── ... 
```

## Retry Mechanism

The application implements an exponential backoff retry mechanism for handling rate-limited requests and server errors:

### Retry Configuration
- Maximum retries: 5
- Base delay: 1 second
- Maximum delay: 60 seconds
- Exponential base: 2
- Jitter: Enabled (random delay variation)

### Retry Behavior
- Automatically retries on:
  - Rate limit exceeded (429)
  - Server errors (5xx)
- Implements exponential backoff:
  - Delay increases exponentially with each retry
  - Maximum delay caps the exponential growth
  - Random jitter prevents thundering herd problem

### Example Retry Sequence
```
Attempt 1: Immediate
Attempt 2: ~1 second delay
Attempt 3: ~2 seconds delay
Attempt 4: ~4 seconds delay
Attempt 5: ~8 seconds delay
Attempt 6: ~16 seconds delay
```

### Usage
The retry mechanism is automatically applied to all API requests. No additional configuration is needed.

Example of retry in action:
```python
from src.api import KeapClient

client = KeapClient()

# This request will automatically retry if rate limited
contacts, pagination = client.get_contacts(limit=100)
```

### Logging
Retry attempts are logged with:
- Warning level for retry attempts
- Error level for max retries exceeded
- Includes delay information and error details

Example log output:
```
WARNING - Attempt 1/5 failed. Retrying in 1.23 seconds. Error: Rate limit exceeded
WARNING - Attempt 2/5 failed. Retrying in 2.45 seconds. Error: Rate limit exceeded
ERROR - Max retries (5) exceeded. Last error: Rate limit exceeded
```

## Data Transformation

The application includes a comprehensive data transformation layer that converts API responses to SQLAlchemy model instances:

### Transformation Module (`src/transformers/transformers.py`)

The transformation module provides functions to convert API responses to database models:

#### Contact Transformations
```python
# Transform single contact
contact = transform_contact(api_data)

# Transform contact with all related data
contact = transform_contact_with_related(api_data, db_session)

# Transform list of contacts
contacts, pagination = transform_list_response(api_data, transform_contact)
```

#### Tag Transformations
```python
# Transform single tag
tag = transform_tag(api_data)

# Transform applied tag (from contact-tag relationship)
tag = transform_applied_tag(api_data)

# Transform list of tags
tags, pagination = transform_list_response(api_data, transform_tag)
```

#### Custom Field Transformations
```python
# Transform single custom field
custom_field = transform_custom_field(field_name, field_def)

# Transform list of custom fields
custom_fields, pagination = transform_list_response(api_data, transform_custom_field)

# Create custom field value
custom_field_value = transform_custom_field_value(api_data, entity_id, custom_field_id)
```

#### Opportunity Transformations
```python
# Transform single opportunity
opportunity = transform_opportunity(api_data)

# Transform list of opportunities
opportunities, pagination = transform_list_response(api_data, transform_opportunity)
```

#### Order Transformations
```python
# Transform single order with items
order = transform_order_with_items(api_data)

# Transform order item
order_item = transform_order_item(api_data)

# Transform order payment
order_payment = transform_order_payment(api_data)

# Transform order transaction
order_transaction = transform_order_transaction(api_data)
```

#### Task Transformations
```python
# Transform single task
task = transform_task(api_data)

# Transform list of tasks
tasks, pagination = transform_list_response(api_data, transform_task)
```

#### Note Transformations
```python
# Transform single note
note = transform_note(api_data)

# Transform list of notes
notes, pagination = transform_list_response(api_data, transform_note)
```

#### Product Transformations
```python
# Transform single product
product = transform_product(api_data)

# Transform list of products
products, pagination = transform_list_response(api_data, transform_product)
```

#### Subscription Transformations
```python
# Transform single subscription
subscription = transform_subscription(api_data)

# Transform list of subscriptions
subscriptions, pagination = transform_list_response(api_data, transform_subscription)
```

#### Campaign Transformations
```python
# Transform single campaign
campaign = transform_campaign(api_data)

# Transform list of campaigns
campaigns, pagination = transform_list_response(api_data, transform_campaign)
```

#### Affiliate Transformations
```python
# Transform single affiliate
affiliate = transform_affiliate(api_data)

# Transform affiliate commission
commission = transform_affiliate_commission(api_data)

# Transform affiliate program
program = transform_affiliate_program(api_data)

# Transform affiliate redirect
redirect = transform_affiliate_redirect(api_data)

# Transform affiliate summary
summary = transform_affiliate_summary(api_data)

# Transform affiliate clawback
clawback = transform_affiliate_clawback(api_data)

# Transform affiliate payment
payment = transform_affiliate_payment(api_data)
```

#### Account Transformations
```python
# Transform account profile
account_profile = transform_account_profile(api_data)

# Transform business goal
business_goal = transform_business_goal(api_data, account_profile_id)
```

### Data Handling Features

1. **Type Conversion**
   - Automatic conversion of API data types to Python types
   - Handling of nullable fields
   - Date/time string parsing to Python datetime objects
   - Enum value conversion with fallback handling

2. **Nested Data Handling**
   - Extraction of nested objects (e.g., addresses, email addresses)
   - Default values for missing nested data
   - JSON field handling
   - Complex object transformation

3. **Relationship Management**
   - Creation of relationship objects (e.g., contact-tag associations)
   - Proper foreign key handling
   - Timestamp management for relationship records
   - Many-to-many relationship handling

4. **List Response Handling**
   - Generic list transformation function
   - Pagination support
   - Batch processing capabilities
   - Error handling for individual items

5. **Error Handling**
   - Graceful handling of missing fields
   - Type conversion error recovery
   - Logging of transformation errors
   - Fallback values for invalid data

### Usage Example

```python
from src.api import KeapClient
from src.transformers.transformers import transform_contact_with_related, transform_list_response

client = KeapClient()

# Get and transform a single contact with all related data
contact_data = client.get_contact(123)
contact = transform_contact_with_related(contact_data)

# Get and transform a list of contacts
contacts_data, pagination = client.get_contacts(limit=100)
contacts, _ = transform_list_response(contacts_data, transform_contact_with_related)

# Access transformed data
print(f"Contact: {contact.given_name} {contact.family_name}")
print(f"Email: {contact.email_addresses[0].email if contact.email_addresses else 'No email'}")
print(f"Company: {contact.company_name}")
print(f"Tags: {[tag.name for tag in contact.tags]}")
```

### Error Handling

The transformation functions include comprehensive error handling for:
- Missing required fields
- Invalid data types
- Malformed date strings
- Invalid JSON data
- Missing nested objects
- Enum conversion failures

Example error handling:
```python
try:
    contact = transform_contact_with_related(api_data)
except KeyError as e:
    print(f"Missing required field: {e}")
except ValueError as e:
    print(f"Invalid data format: {e}")
except Exception as e:
    print(f"Transformation error: {e}")
```

## Data Loading System

The project includes a comprehensive data loading system with specialized loaders for different entity types:

### Loader Architecture
- `BaseLoader`: Abstract base class for all loaders
- `ContactLoader`: Handles contact data loading
- `TagLoader`: Handles tag data loading
- `CustomFieldsLoader`: Handles custom field data loading
- `OrderLoader`: Handles order data loading
- `ProductLoader`: Handles product data loading
- `AffiliateLoader`: Handles affiliate data loading
- `LoaderFactory`: Factory pattern for creating appropriate loaders

### Loader Features
- Batch processing capabilities
- Error handling and recovery
- Progress tracking
- Data validation
- Duplicate handling
- Relationship management

### Usage Example
```python
from src.scripts.load_data_manager import LoadDataManager

# Initialize the data manager
manager = LoadDataManager()

# Load all data types
manager.load_all_data()

# Load specific data types
manager.load_contacts()
manager.load_tags()
manager.load_custom_fields()
manager.load_orders()
manager.load_products()
manager.load_affiliates()
```

## Database Migrations

The project uses Alembic for database migrations:

### Migration Structure
- `database/migrations/versions/`: Contains migration files
- `database/migrations/env.py`: Migration environment configuration
- `database/migrations/script.py.mako`: Migration template

### Migration Commands
```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1

# Check current migration status
alembic current
```

## API Version Information

The project is based on the Keap REST API version 1.70.0.820452-hf-202506171311, which includes:

### Available Endpoints
- Account Info: Profile management
- Affiliate: Complete affiliate management system
- Campaign: Marketing campaign management
- Company: Company information
- Contact: Comprehensive contact management
- E-Commerce: Order and product management
- Email: Email management
- Email Address: Email address management
- File: File management
- Locale: Localization settings
- Merchant: Merchant account management
- Note: Note management
- Opportunity: Sales opportunity management
- Product: Product catalog management
- REST Hooks: Webhook management
- Setting: System settings
- Tags: Tag management
- Task: Task management
- User Info: User information
- Users: User management

### API Features
- OAuth2 authentication
- Comprehensive pagination support
- Rate limiting with proper error responses
- Webhook support for real-time updates
- Extensive custom field support
- Multi-entity relationship management

## Performance Considerations

### Database Optimization
- Comprehensive indexing strategy
- Proper foreign key constraints
- Efficient query patterns
- Connection pooling

### API Optimization
- Request batching where possible
- Efficient pagination handling
- Caching strategies
- Rate limit compliance

### Memory Management
- Streaming data processing for large datasets
- Efficient data transformation
- Proper resource cleanup
- Memory-efficient data structures

## Security Considerations

### API Security
- Secure API key management
- HTTPS-only communication
- Input validation and sanitization
- Error message sanitization

### Database Security
- Parameterized queries
- SQL injection prevention
- Proper access controls
- Secure connection handling

### Data Protection
- Sensitive data encryption
- Audit logging
- Access control
- Data retention policies

## Troubleshooting

### Common Issues
1. **Authentication Errors**: Verify API key and permissions
2. **Rate Limiting**: Implement proper retry logic
3. **Data Transformation Errors**: Check API response format
4. **Database Connection Issues**: Verify connection parameters
5. **Memory Issues**: Implement streaming for large datasets

### Debugging
- Enable debug logging
- Check API response formats
- Verify database schema
- Monitor performance metrics

### Support
- Check API documentation for endpoint changes
- Review error logs for specific issues
- Verify environment configuration
- Test with minimal data sets first