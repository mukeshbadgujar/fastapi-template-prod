# FastAPI Production Template

A feature-rich, production-grade FastAPI template for building scalable web services with enterprise-grade authentication, configuration management, and observability. This template enforces best practices, encourages test-driven development, and provides a solid foundation for your FastAPI projects.

## 🚀 Features

- **🏗️ Well-structured project** with modular architecture following best practices
- **🔐 Enterprise Authentication** with JWT + API key dual authentication system
- **⚙️ Redis Configuration Management** with JSON-based environment-specific configs
- **📊 Enhanced Logging & Observability** with correlation tracking and pluggable backends
- **🗄️ Multi-Database Support** with SQLAlchemy + Alembic for migrations
- **🌐 Advanced HTTP Client** with correlation ID propagation and circuit breaker
- **🐳 Docker & Docker Compose** for containerization
- **🛡️ Security Best Practices** with bcrypt, JWT tokens, and API key management
- **🔍 Code Quality Tools** with pre-commit hooks, linting, and type checking
- **📈 Production Ready** with health checks, metrics, and monitoring

## 🔐 Authentication System

### Dual Authentication Support

This template provides comprehensive authentication with both JWT-based user authentication and API key management:

#### JWT Authentication
- **User registration and login** with bcrypt password hashing
- **Access/Refresh token rotation** with secure token management
- **User profile management** with extensible profile data
- **Account verification and security** with activation flows
- **Session management** with device tracking and IP logging

#### API Key Management
- **Programmatic API access** for service-to-service communication
- **Scoped permissions** with fine-grained access control
- **Rate limiting** per API key with customizable limits
- **IP restrictions** for enhanced security
- **Usage analytics** with detailed request tracking and monitoring
- **Expiration and revocation** with lifecycle management

### Authentication Models

```python
# User Management
from app.models.auth import User, RefreshToken
from app.schemas.auth import UserCreate, UserLogin, UserResponse

# API Key Management
from app.models.auth import APIKey, APIKeyUsage
from app.schemas.auth import APIKeyCreate, APIKeyResponse

# Authentication Service
from app.services.auth_service import auth_service

# Create user
user = await auth_service.create_user(db, UserCreate(
    email="user@example.com",
    username="testuser",
    password="securepassword123",
    confirm_password="securepassword123"
))

# Authenticate user
user = await auth_service.authenticate_user(db, UserLogin(
    username="testuser",
    password="securepassword123"
))

# Create API key
api_key, secret = await auth_service.create_api_key(db, APIKeyCreate(
    name="My Service API Key",
    description="API key for external service integration",
    scopes=["read:users", "write:data"],
    rate_limit=1000,  # requests per minute
    allowed_ips=["192.168.1.100", "10.0.0.0/8"]
))
```

## ⚙️ Redis Configuration Management

### Environment-Specific JSON Configurations

The template includes a sophisticated Redis-based configuration system:

```python
from app.services.redis_service import redis_config

# Initialize Redis configuration service
await redis_config.initialize()

# Get configuration values
api_rate_limit = await redis_config.get_rate_limit("api_requests_per_minute", 1000)
feature_enabled = await redis_config.get_feature_flag("user_registration", True)
app_config = await redis_config.get("app", {})

# Dynamic configuration updates
await redis_config.set("features.new_feature", True)
await redis_config.reload_from_file()  # Reload from config files
```

### Configuration Structure

Environment-specific configuration files in `config/redis/`:
- `dev_redis_config.json` - Development settings
- `uat_redis_config.json` - UAT environment
- `prod_redis_config.json` - Production settings

Example configuration:
```json
{
  "app": {
    "name": "FastAPI Production Template",
    "version": "1.0.0",
    "debug": false
  },
  "features": {
    "user_registration": true,
    "api_key_creation": true,
    "email_verification": true,
    "rate_limiting": true
  },
  "rate_limits": {
    "api_requests_per_minute": 1000,
    "login_attempts_per_hour": 5,
    "api_key_requests_per_minute": 100
  },
  "security": {
    "password_min_length": 8,
    "session_timeout_minutes": 30,
    "max_login_attempts": 5
  }
}
```

## 📊 Logging & Observability

### Enhanced Logging System

This template includes a sophisticated logging system with the following features:

#### Correlation ID Tracking
- **Automatic correlation ID generation** for each incoming request
- **Propagation** of correlation IDs through all external API calls
- **Chain tracking** linking all related operations within a request flow
- **Configurable header names** and enable/disable options

#### Pluggable Database Backends
Configure logging destination with a single environment variable:

```bash
# SQLite (default for development)
LOG_DB_URL="sqlite:///./api_logs.db"

# PostgreSQL (recommended for production)
LOG_DB_URL="postgresql://logs_user:password@db.example.com:5432/logs"

# MySQL
LOG_DB_URL="mysql://logs_user:password@db.example.com:3306/logs"
```

#### JSON & Console Logging
- **Structured JSON logs** with embedded correlation IDs and context
- **Console colorization** by log level (DEBUG=cyan, INFO=green, WARNING=yellow, ERROR=red)
- **Pretty print mode** for human-readable development logs
- **Configurable formatting** via environment variables

#### Logging Configuration

```bash
# Basic logging format
LOG_FORMAT=json              # Options: "json", "pretty"
LOG_PRETTY=false             # Enable pretty/human-readable format
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_COLOR=true               # Enable colored console output

# Correlation tracking
ENABLE_CORRELATION_ID=true     # Enable correlation ID generation
CORRELATION_ID_HEADER=X-Correlation-ID  # Header name

# Database logging
LOG_DB_URL=sqlite:///./api_logs.db      # Pluggable backend
API_LOG_TABLE=api_request_logs          # Table for incoming requests
INT_API_LOG_TABLE=internal_api_logs     # Table for outgoing API calls
```

### Using the Enhanced Logger

```python
from app.utils.logger import logger, get_logger
from app.common.api_call import create_correlation_client, with_correlation_context

# Basic logging with automatic correlation context
logger.info("Processing user request", extra={
    "user_id": "12345",
    "action": "update_profile"
})

# Create correlation-aware HTTP client
client = create_correlation_client(
    base_url="https://api.example.com",
    vendor="example-service",
    api_key="your-api-key"
)

# Make API call - correlation ID automatically propagated
response_data, headers, status_code = await client.request(
    method="GET",
    endpoint="/users/12345",
    account_id="account_123",
    partner_journey_id="journey_456"
)

# Decorate internal service calls for correlation tracking
@with_correlation_context
async def internal_service_call(data: dict, correlation_id: str = None):
    # correlation_id automatically injected if not provided
    logger.info("Internal service processing", extra={"data_keys": list(data.keys())})
    return {"status": "processed"}
```

## 🏗️ Project Structure

```
fastapi-template-prod/
├── alembic/                   # Database migrations
├── app/
│   ├── api/                   # API routes
│   ├── auth/                  # Authentication (deprecated - moved to models/services)
│   ├── common/                # Shared components
│   │   ├── api_call.py        # Enhanced API client with correlation
│   │   └── exceptions.py      # Common exceptions
│   ├── config/                # Configuration
│   │   └── settings.py        # Enhanced settings with auth config
│   ├── core/                  # Core functionality
│   │   └── logging_backend.py # Pluggable database logging backend
│   ├── db/                    # Database
│   │   └── base.py
│   ├── middleware/            # Middleware
│   │   ├── logging.py         # Request/response logging
│   │   └── request_logger.py  # Enhanced request logger with correlation
│   ├── models/                # Database models
│   │   └── auth.py            # 🔐 Authentication models (User, APIKey, etc.)
│   ├── schemas/               # Pydantic schemas
│   │   └── auth.py            # 🔐 Authentication schemas
│   ├── services/              # Business logic
│   │   ├── auth_service.py    # 🔐 Authentication service
│   │   └── redis_service.py   # ⚙️ Redis configuration service
│   ├── utils/                 # Utilities
│   │   └── logger.py          # Enhanced logger with correlation support
│   └── main.py                # Application entry point
├── config/                    # ⚙️ Environment configurations
│   └── redis/                 # Redis configuration files
│       ├── dev_redis_config.json
│       ├── uat_redis_config.json
│       └── prod_redis_config.json
├── tests/                     # Tests
├── .env                       # Environment variables
├── env_example.txt            # Example environment variables
├── docker-compose.yml         # Docker Compose configuration
└── requirements.txt           # Enhanced dependencies with auth & Redis
```

### 🔐 New Authentication Components

- **`app/models/auth.py`** - Database models for User, RefreshToken, APIKey, APIKeyUsage
- **`app/schemas/auth.py`** - Pydantic schemas for all authentication operations
- **`app/services/auth_service.py`** - Authentication service with JWT + API key support

### ⚙️ New Configuration Components

- **`app/services/redis_service.py`** - Redis-based configuration management
- **`config/redis/`** - Environment-specific JSON configuration files

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Redis Server (for configuration management)
- Docker and Docker Compose (optional, for containerized deployment)
- PostgreSQL (optional, can be run via Docker)

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

4. Create a `.env` file based on `env_example.txt`:
   ```bash
   cp env_example.txt .env
   # Edit .env with your configuration
   ```

5. **Set up Redis** (required for configuration management):
   ```bash
   # Option 1: Install Redis locally
   # Ubuntu/Debian: sudo apt install redis-server
   # macOS: brew install redis

   # Option 2: Run Redis via Docker
   docker run -d -p 6379:6379 redis:latest

   # Option 3: Use Docker Compose (includes Redis)
   docker-compose up -d redis
   ```

6. Set up linting tools for code quality (recommended):
   ```bash
   chmod +x setup_linting.sh
   ./setup_linting.sh
   ```

### Environment Configuration

#### Development Configuration (.env)
```bash
ENV=dev
DEBUG=true
SECRET_KEY=CHANGE_ME_IN_PRODUCTION_USE_STRONG_SECRET
DATABASE_URL=sqlite:///./sql_app.db
LOG_DB_URL=sqlite:///./api_logs.db
LOG_FORMAT=pretty
LOG_LEVEL=DEBUG
REDIS_URL=redis://localhost:6379/0
```

#### Production Configuration (.env)
```bash
ENV=prod
DEBUG=false
SECRET_KEY=your-super-secure-secret-key
DATABASE_URL=postgresql://user:password@db.example.com:5432/production
LOG_DB_URL=postgresql://logs_user:password@db.example.com:5432/production_logs
LOG_FORMAT=json
LOG_LEVEL=INFO
REDIS_URL=redis://redis.example.com:6379/0
```

### Running the Application

#### Without Docker:

```bash
# Start Redis (if not already running)
redis-server

# Run database migrations
alembic upgrade head

# Start the FastAPI application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### With Docker:

```bash
docker-compose up -d
```

The application will be available at `http://localhost:8000`

- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

## 🔧 Development Guide

### Adding Authentication to Your Endpoints

```python
from fastapi import Depends
from app.services.auth_service import auth_service
from app.schemas.auth import AuthContext

# JWT authentication dependency
async def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthContext:
    validation = await auth_service.validate_jwt_token(db, token)
    if not validation.valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    return validation.auth_context

# API key authentication dependency
async def get_api_key_auth(api_key: str = Header(None)) -> AuthContext:
    validation = await auth_service.validate_api_key(db, api_key)
    if not validation.valid:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return validation.auth_context

# Use in your endpoints
@app.get("/protected")
async def protected_endpoint(auth: AuthContext = Depends(get_current_user)):
    return {"user_id": auth.user_id, "scopes": auth.scopes}
```

### Working with Redis Configuration

```python
from app.services.redis_service import redis_config

# Check feature flags
if await redis_config.get_feature_flag("new_feature_enabled", False):
    # Feature is enabled
    pass

# Get rate limits
rate_limit = await redis_config.get_rate_limit("api_requests_per_minute", 1000)

# Update configuration dynamically
await redis_config.set("features.maintenance_mode", True)

# Reload configuration from files (useful for deployment)
await redis_config.reload_from_file()
```

### Making External API Calls

Use the enhanced `CorrelationHTTPClient` for automatic correlation tracking:

```python
from app.common.api_call import create_correlation_client

# Create correlation-aware API client
client = create_correlation_client(
    base_url="https://api.example.com",
    vendor="example-service",
    api_key="your-api-key",
    api_key_header="X-API-Key"
)

# Make API call with automatic correlation propagation
response_data, headers, status_code = await client.request(
    method="GET",
    endpoint="/users",
    params={"limit": 10},
    account_id="user123",              # For logging context
    partner_journey_id="journey456"    # For logging context
)

# Client automatically:
# - Propagates correlation ID in headers
# - Logs request/response to database
# - Handles circuit breaker logic
# - Sanitizes sensitive data in logs
```

### Enhanced Logging Best Practices

```python
from app.utils.logger import logger
from app.common.api_call import with_correlation_context

# Use structured logging with context
logger.info("User profile updated", extra={
    "user_id": "12345",
    "fields_updated": ["email", "phone"],
    "action": "profile_update"
})

# Decorate internal service functions for correlation tracking
@with_correlation_context
async def process_user_data(user_id: str, data: dict):
    logger.info("Processing user data", extra={
        "user_id": user_id,
        "data_size": len(data)
    })

    # Any external API calls here will automatically include correlation ID
    return {"status": "processed"}

# Set custom context for a block of operations
logger.set_context(
    account_id="account_123",
    partner_journey_id="journey_456"
)

# All subsequent logs in this request will include the context
logger.info("Starting complex operation")
# ... multiple operations ...
logger.info("Complex operation completed")

# Clear context when done (optional - middleware does this automatically)
logger.clear_context()
```

## 📊 Querying Logs

### API Request Logs Table Structure
```sql
-- api_request_logs table
SELECT
    correlation_id,
    request_id,
    timestamp,
    method,
    path,
    status_code,
    execution_time_ms,
    client_ip,
    account_id,
    partner_journey_id,
    error_message
FROM api_request_logs
WHERE correlation_id = 'your-correlation-id';
```

### Authentication Usage Analytics
```sql
-- API key usage analytics
SELECT
    ak.name,
    ak.key_id,
    COUNT(aku.id) as total_requests,
    AVG(aku.response_time_ms) as avg_response_time,
    COUNT(CASE WHEN aku.status_code >= 400 THEN 1 END) as error_count
FROM api_keys ak
LEFT JOIN api_key_usage aku ON ak.id = aku.api_key_id
WHERE ak.is_active = true
GROUP BY ak.id, ak.name, ak.key_id
ORDER BY total_requests DESC;

-- User login patterns
SELECT
    u.username,
    u.email,
    COUNT(rt.id) as active_sessions,
    u.last_login,
    u.created_at
FROM users u
LEFT JOIN refresh_tokens rt ON u.id = rt.user_id AND rt.is_revoked = false
WHERE u.is_active = true
GROUP BY u.id, u.username, u.email, u.last_login, u.created_at
ORDER BY u.last_login DESC;
```

## 🧪 Testing

Run tests with pytest:

```bash
pytest
```

## 🔌 API Examples

### Authentication Endpoints

#### User Registration
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword123",
    "confirm_password": "securepassword123",
    "full_name": "Test User"
  }'
```

#### User Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword123"
  }'
```

#### Create API Key
```bash
curl -X POST "http://localhost:8000/api/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Service API Key",
    "description": "API key for external service integration",
    "scopes": ["read:users", "write:data"],
    "rate_limit": 1000,
    "allowed_ips": ["192.168.1.100"]
  }'
```

### Configuration Management
```bash
# Get configuration value
curl -X GET "http://localhost:8000/api/config/features.user_registration" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Update configuration (admin only)
curl -X PUT "http://localhost:8000/api/config/features.new_feature" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": true}'

# Reload configuration from files
curl -X POST "http://localhost:8000/api/config/reload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Legacy Endpoints

#### Health Check
```bash
curl --location 'http://localhost:8000/health' \
--header 'Accept: application/json'
```

#### Weather API
```bash
curl --location 'http://localhost:8000/api/weather?city=London' \
--header 'Accept: application/json'
```

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**:
   ```bash
   # Set production environment variables
   ENV=prod
   DEBUG=false
   SECRET_KEY=your-super-secure-secret-key
   DATABASE_URL=postgresql://user:password@db.example.com:5432/production
   REDIS_URL=redis://redis.example.com:6379/0
   ```

2. **Security Configuration**:
   ```bash
   # Update Redis configuration for production
   # config/redis/prod_redis_config.json
   {
     "rate_limits": {
       "api_requests_per_minute": 500,
       "login_attempts_per_hour": 3
     },
     "security": {
       "max_login_attempts": 3,
       "account_lockout_minutes": 30
     }
   }
   ```

3. **Deploy with Docker**:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

## 🤝 Contributing

We are actively accepting contributions to this project! Please see our contributing guidelines in the original repository.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🔄 Migration Notes

### From Previous Versions

If you're upgrading from a previous version of this template:

1. **Authentication Migration**: The new authentication system is fully backward compatible. Existing API endpoints will continue to work.

2. **Redis Configuration**: The Redis configuration system is optional. If Redis is not available, the system will use local configuration caching.

3. **Environment Variables**: Review and update your `.env` file based on the new `env_example.txt` template.

4. **Database Schema**: Run migrations to add the new authentication tables:
   ```bash
   alembic upgrade head
   ```

### New Dependencies

The enhanced template includes these new dependencies:
- `bcrypt` - Password hashing
- `PyJWT` - JWT token handling
- `aioredis` - Redis async client
- `python-multipart` - Form data handling

Install them with:
```bash
pip install -r requirements.txt
```
