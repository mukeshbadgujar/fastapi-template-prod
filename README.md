# FastAPI Production Template

A feature-rich, production-grade FastAPI template for building scalable web services, especially suited for LOS-based applications. This template enforces best practices, encourages test-driven development, and provides a solid foundation for your FastAPI projects.

## Features

- **Well-structured project** with a modular architecture following best practices
- **Environment-specific configurations** via environment variables (DEV, UAT, PROD, PREPROD)
- **Database integration** with SQLAlchemy + Alembic for migrations
- **Robust API call handling** with logging, circuit breaker, and fallback mechanisms
- **Structured JSON logging** for easy viewing in CloudWatch
- **Docker** and **Docker Compose** for containerization
- **Middleware** support for easy integration of custom middleware
- **Request/Response validation** using Pydantic schemas
- **Health check endpoint** for monitoring

## Project Structure

```
fastapi-template-prod/
├── alembic/                   # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── api/                   # API routes
│   │   └── health.py
│   ├── auth/                  # Authentication
│   ├── common/                # Shared components
│   │   ├── api_call.py        # Reusable API client
│   │   └── exceptions.py      # Common exceptions
│   ├── config/                # Configuration
│   │   └── settings.py
│   ├── core/                  # Core functionality
│   ├── db/                    # Database
│   │   └── base.py
│   ├── external/              # External services
│   ├── middleware/            # Middleware
│   │   ├── base.py
│   │   └── logging.py
│   ├── models/                # Database models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   ├── utils/                 # Utilities
│   │   └── logger.py
│   ├── __init__.py
│   └── main.py                # Application entry point
├── tests/                     # Tests
├── .env.example               # Example environment variables
├── alembic.ini                # Alembic configuration
├── docker-compose.yml         # Docker Compose configuration
├── Dockerfile                 # Docker configuration
├── README.md                  # This file
└── requirements.txt           # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (optional, for containerized deployment)
- PostgreSQL (can be run via Docker)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fastapi-template-prod.git
   cd fastapi-template-prod
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Running the Application

#### Without Docker:

```bash
uvicorn app.main:app --reload
```

#### With Docker:

```bash
docker-compose up -d
```

### Database Migrations

Initialize the database:
```bash
alembic upgrade head
```

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply pending migrations:
```bash
alembic upgrade head
```

## Development Guide

### Adding a New API Endpoint

1. Create a new route file in the `app/api` directory
2. Define appropriate Pydantic schemas in `app/schemas`
3. Implement the business logic in `app/services`
4. Register the router in `app/main.py`

### Adding a New Model

1. Define the SQLAlchemy model in `app/models`
2. Create corresponding Pydantic schemas in `app/schemas`
3. Generate migrations using Alembic

### Making External API Calls

Use the `ApiClient` class from `app/common/api_call.py` to make API calls:

```python
from app.common.api_call import create_api_client, create_fallback_config

# Create a fallback config (optional)
fallback_config = create_fallback_config(
    base_url="https://fallback-api.example.com",
    vendor="fallback-service",
    api_key="your-fallback-api-key",
    api_key_header="X-API-Key"
)

# Create an API client with fallback
client = create_api_client(
    base_url="https://api.example.com",
    vendor="example-service",
    api_key="your-api-key",
    api_key_header="X-API-Key",
    fallback_config=fallback_config
)

# Make API call
response_data, headers, status_code = await client.request(
    method="GET",
    endpoint="/users",
    params={"limit": 10},
    account_id="user123"  # For logging
)
```

### Logging

Use the centralized logger for consistent logging:

```python
from app.utils.logger import logger

# Simple logging
logger.info("Processing request")

# Structured logging
logger.info(
    "User data processed",
    extra={
        "user_id": "123",
        "action": "profile_update",
        "status": "success"
    }
)

# Set context for all subsequent logs
logger.set_context(
    request_id="req-123",
    account_id="user-456",
    partner_journey_id="journey-789"
)
```

## Testing

Run tests with pytest:

```bash
pytest
```

## Deployment

### Production Deployment

1. Set appropriate environment variables in your `.env` file
2. Build and start the Docker containers:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 