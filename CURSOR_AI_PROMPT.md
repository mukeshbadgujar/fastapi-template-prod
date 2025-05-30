# Cursor AI Code Generation Prompt - Razorpay eMandate Integration

## **Project Context**
```
You are extending a production-ready FastAPI application with the following existing architecture:
- Async FastAPI with SQLAlchemy (sqlite+aiosqlite)
- JWT authentication system (Bearer tokens)
- Unified logging with correlation IDs
- Database request/response logging
- Admin endpoints for monitoring
- Structured error handling with standardized responses
- Middleware-based request tracking
- 12-Factor app compliance
```

## **Existing Project Structure**
```
app/
├── api/                    # API endpoints
│   ├── auth.py            # JWT authentication endpoints
│   ├── admin.py           # Admin/monitoring endpoints
│   └── template.py        # CRUD template endpoints
├── auth/                  # Authentication logic
│   ├── dependencies.py   # Auth dependencies
│   ├── security.py       # JWT & password handling
│   └── models.py         # Auth Pydantic models
├── services/              # Business logic
│   └── user_service.py   # User CRUD operations
├── models/                # SQLAlchemy models
│   └── user.py           # User database model
├── middleware/            # Request middleware
│   └── request_logger.py # Correlation & logging
├── common/                # Shared utilities
│   ├── api_call.py       # External API client
│   ├── response.py       # Standardized responses
│   └── exceptions.py     # Custom exceptions
└── core/                  # Core functionality
    └── logging_backend.py # Database logging
```

## **Integration Requirements: Razorpay eMandate**

### **Target Implementation**
```markdown
Create a complete Razorpay eMandate integration with:

1. **Payment Gateway Setup**
   - Razorpay API client configuration
   - Webhook handling for payment events
   - Secure credential management

2. **eMandate Functionality**
   - Customer registration & authentication
   - Mandate creation & approval workflow
   - Recurring payment processing
   - Payment status tracking & notifications

3. **Database Schema**
   - Customer payment profiles
   - Mandate records with status tracking
   - Payment transaction history
   - Webhook event logging

4. **API Endpoints**
   - Customer onboarding flow
   - Mandate creation & management
   - Payment initiation & tracking
   - Admin reporting & analytics
```

## **Code Generation Guidelines**

### **1. Follow Existing Patterns**
```python
# Use existing APIRouter structure
router = APIRouter(prefix="/payments", tags=["Payments"])

# Follow existing async patterns
async def create_mandate(
    mandate_data: MandateCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    pass

# Use existing error handling
from app.common.exceptions import ExternalAPIException
from app.common.response import ResponseUtil

# Follow existing logging patterns with correlation IDs
from app.utils.logger import logger
```

### **2. Database Integration**
```python
# Follow existing model patterns
class RazorpayCustomer(Base):
    __tablename__ = "razorpay_customers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    razorpay_customer_id = Column(String(255), unique=True, nullable=False)
    # ... additional fields
    
    # Timestamps (follow existing pattern)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### **3. External API Integration**
```python
# Use existing UnifiedAPIClient pattern
from app.common.api_call import UnifiedAPIClient

class RazorpayClient:
    def __init__(self):
        self.api_client = UnifiedAPIClient(
            base_url="https://api.razorpay.com/v1",
            default_headers={"Authorization": f"Basic {encoded_auth}"},
            vendor_name="razorpay"
        )
```

### **4. Security & Configuration**
```python
# Follow existing settings pattern
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Razorpay Configuration
    RAZORPAY_KEY_ID: str = Field("", env="RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: str = Field("", env="RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: str = Field("", env="RAZORPAY_WEBHOOK_SECRET")
    RAZORPAY_ENVIRONMENT: str = Field("test", env="RAZORPAY_ENVIRONMENT")  # test/live
```

## **Specific Implementation Tasks**

### **Task 1: Razorpay Client Setup**
```python
# FILE: app/integrations/razorpay_client.py
"""
Create a Razorpay client that:
- Uses existing UnifiedAPIClient for HTTP requests
- Implements all eMandate operations
- Handles webhook signature verification
- Logs all API calls with correlation IDs
- Implements proper error handling
"""
```

### **Task 2: Database Models**
```python
# FILE: app/models/payment.py
"""
Create SQLAlchemy models for:
- RazorpayCustomer (customer profile storage)
- Mandate (mandate details & status)
- PaymentTransaction (individual payment records)
- WebhookEvent (webhook event logging)
"""
```

### **Task 3: Pydantic Schemas**
```python
# FILE: app/schemas/payment.py
"""
Create Pydantic models for:
- Customer creation/update requests
- Mandate creation/management
- Payment initiation requests
- Webhook event handling
- Admin reporting responses
"""
```

### **Task 4: API Endpoints**
```python
# FILE: app/api/payments.py
"""
Create API endpoints:
- POST /api/payments/customers - Create Razorpay customer
- POST /api/payments/mandates - Create eMandate
- GET /api/payments/mandates/{id} - Get mandate details
- POST /api/payments/mandates/{id}/charge - Initiate payment
- POST /api/payments/webhooks - Handle Razorpay webhooks
- GET /api/payments/transactions - List user transactions
"""
```

### **Task 5: Admin Integration**
```python
# FILE: Update app/api/admin.py
"""
Add admin endpoints:
- GET /api/admin/payments/stats - Payment statistics
- GET /api/admin/payments/mandates - All mandates with filters
- GET /api/admin/payments/failed - Failed payments analysis
- GET /api/admin/webhooks/events - Webhook event logs
"""
```

### **Task 6: Webhook Handler**
```python
# FILE: app/services/payment_webhook_service.py
"""
Create webhook service that:
- Verifies Razorpay webhook signatures
- Processes different event types
- Updates database records
- Sends notifications if needed
- Logs all webhook events
"""
```

### **Task 7: Environment Configuration**
```python
# FILE: Update env_example.txt
"""
Add Razorpay configuration:
RAZORPAY_KEY_ID=your_key_id_here
RAZORPAY_KEY_SECRET=your_key_secret_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
RAZORPAY_ENVIRONMENT=test
"""
```

## **Expected Code Structure**

### **Endpoint Example**
```python
@router.post("/mandates", response_model=MandateResponse)
async def create_mandate(
    mandate_request: MandateCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new eMandate for recurring payments"""
    
    try:
        # Log the operation
        logger.info(
            f"Creating mandate for user {current_user.id}",
            extra={
                "event_type": "mandate_creation_start",
                "user_id": current_user.id,
                "amount": mandate_request.amount
            }
        )
        
        # Create mandate via Razorpay
        mandate = await payment_service.create_mandate(
            db=db,
            user=current_user,
            mandate_data=mandate_request
        )
        
        return ResponseUtil.success_response(
            data=mandate,
            message="Mandate created successfully"
        )
        
    except ExternalAPIException as e:
        logger.error(f"Razorpay API error: {e}")
        return ResponseUtil.error_response(
            message="Failed to create mandate",
            errors=[str(e)]
        )
```

### **Database Migration**
```python
# Create Alembic migration for payment tables
alembic revision --autogenerate -m "Add Razorpay payment tables"
```

## **Dependencies to Add**
```bash
# Update requirements.txt
razorpay==1.3.0
cryptography>=3.4.8  # For webhook signature verification
```

## **Testing Requirements**
```python
# Create test files:
# tests/test_payments.py - API endpoint tests
# tests/test_razorpay_client.py - Client integration tests
# tests/test_webhook_handler.py - Webhook processing tests
```

## **Documentation Requirements**
```markdown
1. Update API documentation with payment endpoints
2. Create payment flow diagrams
3. Add Razorpay setup instructions
4. Document webhook URL configuration
5. Add troubleshooting guide
```

---

**Implementation Priority Order:**
1. Razorpay client setup with basic authentication
2. Database models and migrations
3. Customer management endpoints
4. eMandate creation and management
5. Webhook handling system
6. Payment processing endpoints
7. Admin monitoring integration
8. Testing and documentation

**Maintain Consistency With:**
- Existing async patterns
- JWT authentication requirements
- Standardized response formats
- Correlation ID logging
- Error handling patterns
- Database naming conventions
- API versioning strategy 