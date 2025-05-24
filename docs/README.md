# Keap Data Extraction Project Documentation

## Project Overview
This project is designed to extract data from the Keap (formerly Infusionsoft) CRM system using their REST API and store it in a PostgreSQL database. The project implements a robust API client and database models to handle various Keap entities.

## Project Structure
```
keap-data-extract/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── base_client.py
│   │   └── keap_client.py
│   ├── database/
│   │   └── config.py
│   └── models/
│       └── models.py
├── docs/
│   └── README.md
├── requirements.txt
└── .env
```

## Database Design

### Core Tables

#### Contacts (`contacts`)
- Primary entity storing contact information
- Fields:
  - `id` (Primary Key)
  - `email` (Unique, Indexed)
  - `first_name`
  - `last_name`
  - `phone`
  - `company`
  - `job_title`
  - `address` (JSON)
  - `created_at`
  - `updated_at`

#### Tags (`tags`)
- Stores tag definitions
- Fields:
  - `id` (Primary Key)
  - `name` (Unique)
  - `description`
  - `category`
  - `created_at`

#### Contact Tags (`contact_tags`)
- Junction table for many-to-many relationship between contacts and tags
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `tag_id` (Foreign Key)
  - `created_at`

#### Custom Fields (`custom_fields`)
- Stores custom field definitions
- Fields:
  - `id` (Primary Key)
  - `name`
  - `type`
  - `options` (JSON)
  - `created_at`

#### Contact Custom Fields (`contact_custom_fields`)
- Stores values of custom fields for contacts
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `custom_field_id` (Foreign Key)
  - `value`
  - `created_at`
  - `updated_at`

#### Opportunities (`opportunities`)
- Stores sales opportunities
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `title`
  - `stage`
  - `value`
  - `probability`
  - `created_at`
  - `updated_at`

#### Tasks (`tasks`)
- Stores tasks associated with contacts
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `title`
  - `description`
  - `due_date`
  - `completed`
  - `created_at`
  - `updated_at`

#### Notes (`notes`)
- Stores notes associated with contacts
- Fields:
  - `id` (Primary Key)
  - `contact_id` (Foreign Key)
  - `title`
  - `body`
  - `created_at`
  - `updated_at`

## API Client Implementation

### Base Client (`KeapBaseClient`)
Located in `src/api/base_client.py`, this class provides:
- Authentication handling using API key
- Base URL management
- Common request functionality
- Error handling for API requests

### Main Client (`KeapClient`)
Located in `src/api/keap_client.py`, implements all GET operations:

#### Contact Operations
- `get_contacts(limit=50, offset=0, email=None)`: Get all contacts with pagination
- `get_contact(contact_id)`: Get a specific contact
- `get_contact_tags(contact_id)`: Get tags for a contact
- `get_contact_custom_fields(contact_id)`: Get custom fields for a contact

#### Tag Operations
- `get_tags(limit=50, offset=0)`: Get all tags with pagination

#### Custom Field Operations
- `get_custom_fields(limit=50, offset=0)`: Get all custom fields with pagination

#### Opportunity Operations
- `get_opportunities(contact_id=None, limit=50, offset=0)`: Get opportunities with optional contact filtering
- `get_opportunity(opportunity_id)`: Get a specific opportunity

#### Task Operations
- `get_tasks(contact_id=None, limit=50, offset=0)`: Get tasks with optional contact filtering
- `get_task(task_id)`: Get a specific task

#### Note Operations
- `get_notes(contact_id=None, limit=50, offset=0)`: Get notes with optional contact filtering
- `get_note(note_id)`: Get a specific note

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
- `psycopg2-binary>=2.9.0`: PostgreSQL adapter
- `requests>=2.31.0`: HTTP client
- `python-dotenv>=1.0.0`: Environment variable management
- `alembic>=1.13.0`: Database migrations

## Error Handling and Validation

### Custom Exceptions
The API client implements a hierarchy of custom exceptions:
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

### Logging
The client implements structured logging:
- Request/response logging
- Error logging
- Debug information for troubleshooting
- Performance metrics

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

### Rate Limiting
- Built-in rate limit detection
- Proper error handling for rate limit responses
- Automatic retry logic for rate-limited requests

### Data Validation
- Input validation before making API calls
- Response validation
- Type checking
- Range validation

### Error Recovery
- Graceful error handling
- Detailed error messages
- Proper exception hierarchy
- Logging for debugging

### Security
- API key validation
- Secure header management
- No sensitive data logging

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
    contacts = client.get_contacts(
        limit=100,
        offset=0,
        email="user@example.com"
    )
    
    # Get a specific contact
    contact = client.get_contact(contact_id=123)
    
    # Get contact's tags
    contact_tags = client.get_contact_tags(contact_id=123)
    
except KeapValidationError as e:
    logging.error(f"Validation error: {e}")
except KeapAPIError as e:
    logging.error(f"API error: {e}")
except Exception as e:
    logging.error(f"Unexpected error: {e}")
```

## Usage Example

```python
from src.api import KeapClient

# Initialize the client
client = KeapClient()

# Get contacts with pagination
contacts = client.get_contacts(limit=100, offset=0)

# Get a specific contact
contact = client.get_contact(contact_id=123)

# Get contact's tags
contact_tags = client.get_contact_tags(contact_id=123)
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
contacts = client.get_contacts(limit=100)
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

### Transformation Module (`src/utils/transformers.py`)

The transformation module provides functions to convert API responses to database models:

#### Contact Transformations
```python
# Transform single contact
contact = transform_contact(api_data)

# Transform list of contacts
contacts = transform_list_response(api_data, transform_contact)
```

#### Tag Transformations
```python
# Transform single tag
tag = transform_tag(api_data)

# Transform list of tags
tags = transform_list_response(api_data, transform_tag)

# Create contact-tag relationship
contact_tag = transform_contact_tag(contact_id, tag_id)
```

#### Custom Field Transformations
```python
# Transform single custom field
custom_field = transform_custom_field(api_data)

# Transform list of custom fields
custom_fields = transform_list_response(api_data, transform_custom_field)

# Create contact custom field value
contact_custom_field = transform_contact_custom_field(
    contact_id=contact_id,
    custom_field_id=custom_field_id,
    value=value
)
```

#### Opportunity Transformations
```python
# Transform single opportunity
opportunity = transform_opportunity(api_data)

# Transform list of opportunities
opportunities = transform_list_response(api_data, transform_opportunity)
```

#### Task Transformations
```python
# Transform single task
task = transform_task(api_data)

# Transform list of tasks
tasks = transform_list_response(api_data, transform_task)
```

#### Note Transformations
```python
# Transform single note
note = transform_note(api_data)

# Transform list of notes
notes = transform_list_response(api_data, transform_note)
```

### Data Handling Features

1. **Type Conversion**
   - Automatic conversion of API data types to Python types
   - Handling of nullable fields
   - Date/time string parsing to Python datetime objects

2. **Nested Data Handling**
   - Extraction of nested objects (e.g., addresses, email addresses)
   - Default values for missing nested data
   - JSON field handling

3. **Relationship Management**
   - Creation of relationship objects (e.g., contact-tag associations)
   - Proper foreign key handling
   - Timestamp management for relationship records

4. **List Response Handling**
   - Generic list transformation function
   - Pagination support
   - Batch processing capabilities

### Usage Example

```python
from src.api import KeapClient
from src.utils.transformers import transform_contact, transform_list_response

client = KeapClient()

# Get and transform a single contact
contact_data = client.get_contact(123)
contact = transform_contact(contact_data)

# Get and transform a list of contacts
contacts_data = client.get_contacts(limit=100)
contacts = transform_list_response(contacts_data, transform_contact)

# Access transformed data
print(f"Contact: {contact.first_name} {contact.last_name}")
print(f"Email: {contact.email}")
print(f"Company: {contact.company}")
```

### Error Handling

The transformation functions include error handling for:
- Missing required fields
- Invalid data types
- Malformed date strings
- Invalid JSON data
- Missing nested objects

Example error handling:
```python
try:
    contact = transform_contact(api_data)
except KeyError as e:
    print(f"Missing required field: {e}")
except ValueError as e:
    print(f"Invalid data format: {e}")
```