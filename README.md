# Keap Data Extract

A Python-based data extraction and management tool for Keap (formerly Infusionsoft) data.

## Description

This project provides tools for extracting and managing data from Keap's API, storing it in a PostgreSQL database, and maintaining data synchronization. It's designed to help businesses efficiently manage their Keap data and keep it synchronized with their local database.

## Features

- Data extraction from Keap API
- PostgreSQL database integration
- Automated data synchronization
- Logging and checkpoint management
- Database migration support
- Error handling and retry mechanisms
- Data validation and integrity checks

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

## Project Structure

```
keap-data-extract/
├── src/               # Source code
│   ├── api/          # Keap API integration
│   ├── models/       # Database models
│   ├── sync/         # Data synchronization logic
│   └── utils/        # Utility functions
├── database/         # Database related files
│   ├── migrations/   # Alembic migration files
│   └── schemas/      # Database schemas
├── docs/            # Documentation
├── logs/            # Log files
├── checkpoints/     # Data synchronization checkpoints
├── tests/           # Test files
├── requirements.txt # Project dependencies
└── .env            # Environment variables (create this file)
```

## Usage

[Add specific usage instructions here]

## Database Migrations

This project uses Alembic for database migrations. To run migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
