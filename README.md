# Keap Data Extract

A Python-based data extraction and management tool for Keap (formerly Infusionsoft) data.

## Description

This project provides tools for extracting and managing data from Keap's API, storing it in a PostgreSQL database, and maintaining data synchronization.

## Features

- Data extraction from Keap API
- PostgreSQL database integration
- Automated data synchronization
- Logging and checkpoint management
- Database migration support

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Keap API credentials

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
DB_HOST=localhost        # Database host address
DB_PORT=5432            # PostgreSQL default port
DB_NAME=keap_data       # Name of your database
DB_USER=postgres        # Database username
DB_PASSWORD=password    # Database password
```

## Project Structure

```
keap-data-extract/
├── src/               # Source code
├── database/          # Database related files
├── docs/             # Documentation
├── logs/             # Log files
├── checkpoints/      # Data synchronization checkpoints
├── requirements.txt  # Project dependencies
└── .env             # Environment variables (create this file)
```

## Usage

[Add specific usage instructions here]

## Database Migrations

This project uses Alembic for database migrations. To run migrations:

```bash
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
