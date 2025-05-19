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
- **Code quality tools** with pre-commit hooks for linting, formatting and type checking

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
├── .flake8                    # Flake8 linting configuration
├── .pylintrc                  # Pylint configuration
├── mypy.ini                   # MyPy type checking configuration
├── .isort.cfg                 # Import sorting configuration
├── .pre-commit-config.yaml    # Pre-commit hooks configuration
├── .github/workflows/         # GitHub Actions workflows
├── .gitlab-ci.yml             # GitLab CI pipeline configuration
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

5. Set up linting tools for code quality (recommended):
   ```bash
   # Run the linting setup script
   chmod +x setup_linting.sh
   ./setup_linting.sh

   # This installs and configures:
   # - flake8 (style guide enforcement)
   # - pylint (code analysis)
   # - mypy (static type checking)
   # - isort (import sorting)
   # - black (code formatting)
   # - pre-commit (git hooks)
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

### Code Quality and Linting

The project includes several tools to ensure code quality:

1. **flake8** - For style guide enforcement
   ```bash
   flake8 .
   ```

2. **pylint** - For code analysis (finds unused imports, undefined variables, etc.)
   ```bash
   pylint app
   ```

3. **mypy** - For static type checking
   ```bash
   mypy app
   ```

4. **isort** - For import sorting
   ```bash
   isort .
   ```

5. **black** - For code formatting
   ```bash
   black .
   ```

**Pre-commit hooks** automatically run these checks before each commit. To manually trigger them:
```bash
pre-commit run --all-files
```

**CI/CD Integration:**
- GitHub Actions and GitLab CI are preconfigured to run these checks on every push and pull/merge request
- Check `.github/workflows/lint.yml` and `.gitlab-ci.yml` for the configuration

## Testing

Run tests with pytest:

```bash
pytest
```

## API Examples

The following curl examples demonstrate how to interact with the API endpoints. You can also find a complete Postman collection at [https://www.postman.com/protuple/workspace/fastapi-template-prod](https://www.postman.com/protuple/workspace/fastapi-template-prod).

### Health Check

```bash
curl --location 'http://localhost:8000/health' \
--header 'Accept: application/json'
```

### Weather API

```bash
curl --location 'http://localhost:8000/api/weather?city=London' \
--header 'Accept: application/json'
```

### Template Endpoint

```bash
curl --location 'http://localhost:8000/api/template' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--data '{
    "name": "Example",
    "description": "This is a test request",
    "priority": "high"
}'
```

## Contributing

We are actively accepting contributions to this project! Here's how you can contribute:

### Contribution Guidelines

1. **Fork the Repository**
   - Fork the project on GitHub to your own account

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/mukeshbadgujar/fastapi-template-prod.git
   cd fastapi-template-prod
   ```

3. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Your Changes**
   - Implement your feature or bug fix
   - Add or update tests as necessary
   - Follow the existing code style and project structure

5. **Run Tests**
   ```bash
   pytest
   ```

6. **Commit Your Changes**
   ```bash
   git commit -m "Add feature: your feature description"
   ```

7. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**
   - Go to the original repository on GitHub
   - Click "New pull request"
   - Select your fork and branch
   - Provide a clear description of your changes
   - Reference any related issues using #issue-number

### Pull Request Guidelines

- Keep your changes focused and related to a single issue/feature
- Include tests for any new functionality
- Ensure all tests pass before submitting
- Make sure all linting checks pass (`pre-commit run --all-files`)
- Update documentation if needed
- Follow the project's coding style
- Be responsive to feedback and questions on your PR

We aim to review all pull requests promptly. Thank you for your contributions!

## Deployment

### Production Deployment

1. Set appropriate environment variables in your `.env` file
2. Build and start the Docker containers:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
