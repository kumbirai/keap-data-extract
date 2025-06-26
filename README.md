# Keap Data Extract

A Python-based data extraction tool for Keap (formerly Infusionsoft) data.

## Description

This project provides tools for extracting data from Keap's API and storing it in a PostgreSQL database. It's designed to help businesses efficiently extract and store their Keap data for analysis and reporting purposes.

## Features

- **Data Extraction**
  - Extraction of contacts, companies, opportunities, tasks, notes, campaigns, subscriptions, products, orders, affiliates, tags, and custom fields
  - Support for custom fields and tags across multiple entity types
  - Incremental data loading with checkpoint tracking
  - Batch processing with configurable batch sizes
  - Automatic error reprocessing for failed entities

- **Database Integration**
  - PostgreSQL database storage
  - SQLAlchemy ORM integration with comprehensive model relationships
  - Database migration support via Alembic
  - Automatic table creation and schema management

- **Monitoring & Logging**
  - Comprehensive logging system with rotating log files
  - Audit logging of data operations with detailed statistics
  - Error tracking and reporting with structured error logs
  - Checkpoint management for resumable operations
  - Error reprocessing system for handling failed entities

- **Advanced Features**
  - Factory pattern for entity loaders
  - Data transformation layer for API to database mapping
  - Support for complex relationships and foreign keys
  - Automatic dependency resolution for data loading order
  - Retry mechanisms with exponential backoff

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database (version 12 or higher)
- Keap API credentials
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kumbirai/keap-data-extract.git
cd keap-data-extract
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
# Your Keap API key for authentication
KEAP_API_KEY=your_api_key

# Database connection settings
DB_HOST=localhost       # Database host address
DB_PORT=5432            # PostgreSQL default port
DB_NAME=keap_db         # Name of your database
DB_USER=postgres        # Database username
DB_PASSWORD=password    # Database password
```

## Building Executables

To create standalone executables for your platform:

1. Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

2. Build the executable using PyInstaller:
```bash
# Using the build script (recommended)
python build.py

# Or using PyInstaller directly
pyinstaller keap_data_extract.spec
```

The executable will be created in the `dist` directory. The spec file is configured to:
- Include all necessary dependencies and source files
- Create a single-file executable
- Handle all required Python modules
- Include configuration files and directories

Note: Make sure to copy your `.env` file to the same directory as the executable when deploying.

## Project Structure

```
keap-data-extract/
├── src/               # Source code
│   ├── api/          # Keap API integration
│   │   ├── base_client.py      # Base API client
│   │   ├── keap_client.py      # Main API client with all endpoints
│   │   ├── exceptions.py       # API exceptions
│   │   └── validators.py       # Data validation
│   ├── models/       # Database models (SQLAlchemy ORM)
│   ├── scripts/      # Data loading scripts
│   │   ├── load_data.py        # Main data loading logic
│   │   ├── load_data_manager.py # Data loading manager
│   │   ├── reprocess_errors.py # Error reprocessing system
│   │   └── loaders/            # Entity-specific loaders
│   │       ├── loader_factory.py    # Factory for creating loaders
│   │       ├── base_loader.py       # Base loader class
│   │       ├── contact_loader.py    # Contact-specific loader
│   │       ├── product_loader.py    # Product-specific loader
│   │       ├── order_loader.py      # Order-specific loader
│   │       ├── affiliate_loader.py  # Affiliate-specific loader
│   │       ├── custom_fields_loader.py # Custom fields loader
│   │       └── tags_loader.py       # Tags loader
│   ├── transformers/ # Data transformation logic
│   │   └── transformers.py     # API to database model transformers
│   ├── database/     # Database configuration
│   │   ├── config.py           # Database connection setup
│   │   └── init_db.py          # Database initialization
│   └── utils/        # Utility functions
│       ├── logging_config.py   # Logging configuration
│       ├── error_logger.py     # Error logging system
│       ├── global_logger.py    # Global logger management
│       └── retry.py            # Retry mechanisms
├── database/         # Database related files
│   ├── migrations/   # Alembic migration files
│   │   └── versions/ # Migration version files
│   └── schema.sql    # Database schema
├── docs/            # Documentation
│   ├── api_models.md # API model documentation
│   └── V1.json      # API specification
├── logs/            # Log files (created automatically)
│   └── errors/      # Error log files
├── checkpoints/     # Data loading checkpoints (created automatically)
├── assets/          # Application assets (icons, etc.)
├── requirements.txt # Project dependencies
├── build.py         # Build script for executables
├── keap_data_extract.spec # PyInstaller specification
└── .env            # Environment variables (create this file)
```

## Usage

### Initial Setup

1. Configure your database:
```bash
# Create the database
createdb keap_db

# Run migrations
alembic upgrade head
```

2. Run the data extraction:
```bash
# Full data load
python -m src

# Incremental update (load only new/changed data)
python -m src --update

# Enable debug logging
python -m src --debug
```

### Advanced Usage (Direct Script Execution)

For more granular control, you can run the data loading script directly:

```bash
# Load specific entity type
python src/scripts/load_data.py --entity-type contacts
python src/scripts/load_data.py --entity-type products
python src/scripts/load_data.py --entity-type affiliates
python src/scripts/load_data.py --entity-type orders
python src/scripts/load_data.py --entity-type opportunities
python src/scripts/load_data.py --entity-type tasks
python src/scripts/load_data.py --entity-type notes
python src/scripts/load_data.py --entity-type campaigns
python src/scripts/load_data.py --entity-type subscriptions
python src/scripts/load_data.py --entity-type tags
python src/scripts/load_data.py --entity-type custom_fields

# Load specific entity by ID
python src/scripts/load_data.py --entity-type contacts --entity-id 123
python src/scripts/load_data.py --entity-type products --entity-id 456
python src/scripts/load_data.py --entity-type affiliates --entity-id 789
python src/scripts/load_data.py --entity-type orders --entity-id 101

# Perform incremental update
python src/scripts/load_data.py --update
```

### Command Line Arguments

#### Main Module (`python -m src`)
| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--update` | Perform an update operation using last_loaded timestamps | No | False |
| `--debug` | Enable debug logging | No | False |

#### Direct Script (`python src/scripts/load_data.py`)
| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--update` | Perform an update operation using last_loaded timestamps | No | False |
| `--entity-type` | Type of entity to load | No | None |
| `--entity-id` | ID of specific entity to load | No | None |

The `--entity-type` argument accepts the following values:
- `contacts`: Load contact data with all related information
- `products`: Load product data with subscription plans
- `affiliates`: Load affiliate data with commissions, programs, redirects, etc.
- `orders`: Load order data with items, payments, and transactions
- `opportunities`: Load opportunity data
- `tasks`: Load task data
- `notes`: Load note data
- `campaigns`: Load campaign data with sequences
- `subscriptions`: Load subscription data
- `tags`: Load tag data with categories
- `custom_fields`: Load custom field definitions and values

When using `--entity-id`, you must also specify `--entity-type`.

### Supported Data Types

The tool can extract the following data types from Keap:

**Core Data:**
- **Contacts** - Complete contact information including email addresses, phone numbers, addresses, fax numbers, credit cards, and relationships
- **Products** - Product information with embedded subscription plans
- **Orders** - Order data with items, payments, transactions, and shipping information
- **Opportunities** - Sales opportunities with stages and values
- **Tasks** - Task and appointment data
- **Notes** - Contact notes with various types
- **Campaigns** - Marketing campaigns with sequences
- **Subscriptions** - Subscription data with plans and billing information

**Custom Data:**
- **Custom Fields** - Custom field definitions and values for contacts, opportunities, orders, subscriptions, and notes
- **Tags** - Tag system with categories and contact associations

**Affiliate Data:**
- **Affiliates** - Affiliate information with contact relationships
- **Affiliate Commissions** - Commission tracking
- **Affiliate Programs** - Program definitions
- **Affiliate Redirects** - Redirect URLs and program associations
- **Affiliate Summaries** - Summary statistics
- **Affiliate Clawbacks** - Clawback tracking
- **Affiliate Payments** - Payment history

**Account Data:**
- **Account Profile** - Account information with business goals

**Note:** Subscription plans are automatically loaded as part of the product loading process since they are embedded in the product API response, not as a separate endpoint.

Each data type is loaded with its related data and maintains its own checkpoint for tracking progress. The system automatically handles referential integrity by loading entities in the correct dependency order.

### Error Handling and Reprocessing

The application includes a sophisticated error handling and reprocessing system:

1. **Error Logging** - All errors are logged to structured JSON files in `logs/errors/`
2. **Error Analysis** - The system analyzes errors to identify missing dependencies
3. **Automatic Reprocessing** - Failed entities are automatically reprocessed after dependencies are loaded
4. **Manual Reprocessing** - You can manually run error reprocessing:
   ```bash
   python src/scripts/reprocess_errors.py
   ```

## Database Migrations

This project uses Alembic for database migrations. To run migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1  # Roll back one migration
alembic downgrade base  # Roll back all migrations
```

## Database Schema

The application creates a comprehensive database schema with the following main tables:

- `contacts` - Contact information
- `email_addresses`, `phone_numbers`, `contact_addresses`, `fax_numbers` - Contact details
- `tags`, `tag_categories` - Tagging system
- `custom_fields`, `*_custom_field_values` - Custom field system
- `products`, `subscription_plans`, `product_options` - Product catalog
- `orders`, `order_items`, `order_payments`, `order_transactions` - Order management
- `opportunities` - Sales opportunities
- `tasks` - Task management
- `notes` - Contact notes
- `campaigns`, `campaign_sequences` - Marketing campaigns
- `subscriptions` - Subscription management
- `affiliates` and related affiliate tables - Affiliate system
- `account_profiles`, `business_goals` - Account information

All tables include proper foreign key relationships, indexes, and audit fields (created_at, modified_at).

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify your API key is correct
   - Check your internet connection
   - Ensure you haven't exceeded API rate limits

2. **Database Connection Issues**
   - Verify database credentials in .env file
   - Ensure PostgreSQL is running
   - Check database port accessibility

3. **Data Loading Issues**
   - Check logs in the `logs/` directory
   - Verify checkpoint files in `checkpoints/`
   - Ensure sufficient disk space
   - Review error logs in `logs/errors/`

4. **Foreign Key Violations**
   - The system automatically handles these through error reprocessing
   - Check the error reprocessing logs for details

### Logging

Logs are stored in the `logs/` directory with the following format:
- `keap_data_extract_YYYYMMDD.log`: Main application log with rotating files
- `audit_log.json`: Audit information for data loading operations
- `logs/errors/data_load_errors_YYYYMMDD.json`: Structured error logs

### Performance Optimization

- The application uses connection pooling for database operations
- Batch processing is configurable through the API client
- Checkpoint system allows for resumable operations
- Error reprocessing runs automatically after main data loads

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please:
1. Check the [documentation](docs/)
2. Review the [troubleshooting guide](#troubleshooting)
3. Open an issue on GitHub
4. Contact the maintainers
