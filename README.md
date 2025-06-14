# Keap Data Extract

A Python-based data extraction tool for Keap (formerly Infusionsoft) data.

## Description

This project provides tools for extracting data from Keap's API and storing it in a PostgreSQL database. It's designed to help businesses efficiently extract and store their Keap data for analysis and reporting purposes.

## Features

- **Data Extraction**
  - Extraction of contacts, companies, opportunities, tasks, and more
  - Support for custom fields and tags
  - Incremental data loading with checkpoint tracking
  - Batch processing with configurable batch sizes

- **Database Integration**
  - PostgreSQL database storage
  - SQLAlchemy ORM integration
  - Database migration support via Alembic

- **Monitoring & Logging**
  - Comprehensive logging system
  - Audit logging of data operations
  - Error tracking and reporting
  - Checkpoint management for resumable operations

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
# For Windows
pyinstaller keap_data_extract.spec

# For macOS/Linux
pyinstaller keap_data_extract.spec
```

The executable will be created in the `dist` directory. The spec file is configured to:
- Include all necessary dependencies
- Package all source files
- Create a single-file executable
- Handle all required Python modules

Note: Make sure to copy your `.env` file to the same directory as the executable when deploying.

## Project Structure

```
keap-data-extract/
├── src/               # Source code
│   ├── api/          # Keap API integration
│   ├── models/       # Database models
│   ├── scripts/      # Data loading scripts
│   ├── transformers/ # Data transformation logic
│   └── utils/        # Utility functions
├── database/         # Database related files
│   ├── migrations/   # Alembic migration files
│   └── schemas/      # Database schemas
├── docs/            # Documentation
├── logs/            # Log files
├── checkpoints/     # Data loading checkpoints
├── tests/           # Test files
├── requirements.txt # Project dependencies
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
```

### Command Line Options

The tool provides several command-line options:

```bash
# Basic usage
python -m src

# Enable debug logging
python -m src --debug

# Perform incremental update
python -m src --update

# Load specific entity type
python -m src --entity-type contacts
python -m src --entity-type products
python -m src --entity-type affiliates
python -m src --entity-type orders

# Load specific entity by ID
python -m src --entity-type contacts --entity-id 123
python -m src --entity-type products --entity-id 456
python -m src --entity-type affiliates --entity-id 789
python -m src --entity-type orders --entity-id 101
```

### Command Line Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--update` | Perform an update operation using last_loaded timestamps | No | False |
| `--entity-type` | Type of entity to load | No | None |
| `--entity-id` | ID of specific entity to load | No | None |

The `--entity-type` argument accepts the following values:
- `products`: Load product data
- `contacts`: Load contact data
- `affiliates`: Load affiliate data
- `orders`: Load order data

When using `--entity-id`, you must also specify `--entity-type`.

### Supported Data Types

The tool can extract the following data types from Keap:

Core Data:
- Contacts
- Products
- Orders
- Opportunities
- Tasks
- Notes
- Campaigns
- Subscriptions

Custom Data:
- Custom Fields
- Tags

Affiliate Data:
- Affiliates
- Affiliate Commissions
- Affiliate Programs
- Affiliate Redirects
- Affiliate Summaries
- Affiliate Clawbacks
- Affiliate Payments

Each data type is loaded with its related data and maintains its own checkpoint for tracking progress.

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

### Logging

Logs are stored in the `logs/` directory with the following format:
- `audit_log.json`: Audit information for data loading operations
- `error.log`: Error tracking
- `keap_data_extract.log`: Main application log

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
