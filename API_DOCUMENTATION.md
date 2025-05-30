# FastAPI Template - Complete API Documentation

This document contains all available API endpoints with their corresponding curl commands for testing.

**Base URL:** `http://localhost:8001`
**API Prefix:** `/api`

## Table of Contents

1. [Home](#home)
2. [Health Check](#health-check)
3. [Authentication](#authentication)
4. [Weather](#weather)
5. [Templates (CRUD Example)](#templates-crud-example)
6. [Payments (Razorpay Integration)](#payments-razorpay-integration)
7. [Admin](#admin)

---

## Home

### Get API Information
Get basic information about the API.

```bash
curl -X GET "http://localhost:8001/" \
  -H "Accept: application/json"
```

---

## Health Check

### Health Check
Check if the API is running and healthy.

```bash
curl -X GET "http://localhost:8001/api/health" \
  -H "Accept: application/json"
```

---

## Authentication

### Register User
Create a new user account.

```bash
curl -X POST "http://localhost:8001/api/auth/register" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123",
    "full_name": "Test User"
  }'
```

### Login
Authenticate and get access token.

```bash
curl -X POST "http://localhost:8001/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword123"
  }'
```

### OAuth Login
Alternative login method (OAuth style).

```bash
curl -X POST "http://localhost:8001/api/auth/login/oauth" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -d "grant_type=password&username=testuser&password=securepassword123"
```

### Get Current User Profile
Get the current authenticated user's profile.

```bash
curl -X GET "http://localhost:8001/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### Update User Profile
Update the current user's profile information.

```bash
curl -X PUT "http://localhost:8001/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "full_name": "Updated Name",
    "email": "updated@example.com"
  }'
```

### Change Password
Change the current user's password.

```bash
curl -X POST "http://localhost:8001/api/auth/change-password" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "current_password": "oldpassword123",
    "new_password": "newpassword123"
  }'
```

### Request Password Reset
Request a password reset token.

```bash
curl -X POST "http://localhost:8001/api/auth/reset-password" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "email": "test@example.com"
  }'
```

### Confirm Password Reset
Confirm password reset with token.

```bash
curl -X POST "http://localhost:8001/api/auth/reset-password/confirm" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "token": "reset_token_here",
    "new_password": "newpassword123"
  }'
```

### Logout
Logout and invalidate the current token.

```bash
curl -X POST "http://localhost:8001/api/auth/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

---

## Weather

### Get Weather (GET)
Get current weather information for a city.

```bash
curl -X GET "http://localhost:8001/api/weather?city=London&country_code=uk&units=metric" \
  -H "Accept: application/json"
```

### Get Weather (POST)
Get weather information using POST with JSON body.

```bash
curl -X POST "http://localhost:8001/api/weather" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "city": "Mumbai",
    "country_code": "in",
    "units": "metric"
  }'
```

---

## Templates (CRUD Example)

### List All Templates
Get all template items with pagination.

```bash
curl -X GET "http://localhost:8001/api/template?skip=0&limit=10" \
  -H "Accept: application/json"
```

### Get Template by ID
Get a specific template item by ID.

```bash
curl -X GET "http://localhost:8001/api/template/1" \
  -H "Accept: application/json"
```

### Create Template
Create a new template item.

```bash
curl -X POST "http://localhost:8001/api/template" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "Sample Template",
    "description": "This is a sample template for testing"
  }'
```

### Update Template
Update an existing template item.

```bash
curl -X PUT "http://localhost:8001/api/template/1" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "Updated Template",
    "description": "This template has been updated"
  }'
```

### Delete Template
Delete a template item.

```bash
curl -X DELETE "http://localhost:8001/api/template/1" \
  -H "Accept: application/json"
```

---

## Payments (Razorpay Integration)

### Create Customer
Create or get a Razorpay customer for the current user.

```bash
curl -X POST "http://localhost:8001/api/payments/customers" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "contact": "9999999999",
    "fail_existing": false,
    "gstin": "GST123456789",
    "notes": {
      "description": "Premium customer"
    }
  }'
```

### Get My Customer Profile
Get customer details for the current user.

```bash
curl -X GET "http://localhost:8001/api/payments/customers/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### Create Mandate
Create a new eMandate for recurring payments.

```bash
curl -X POST "http://localhost:8001/api/payments/mandates" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "amount": 100000,
    "currency": "INR",
    "max_amount": 500000,
    "description": "Monthly subscription",
    "frequency": "monthly",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "bank_account": {
      "account_number": "1234567890",
      "ifsc": "HDFC0000123",
      "name": "HDFC Bank"
    },
    "notes": {
      "subscription_type": "premium"
    }
  }'
```

### Get Mandate by ID
Get specific mandate details.

```bash
curl -X GET "http://localhost:8001/api/payments/mandates/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### List My Mandates
Get all mandates for the current user.

```bash
curl -X GET "http://localhost:8001/api/payments/mandates?status=active&skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### Create Recurring Payment
Create a recurring payment using an existing mandate.

```bash
curl -X POST "http://localhost:8001/api/payments/mandates/1/charge" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "amount": 100000,
    "description": "Monthly subscription payment",
    "receipt": "receipt_2025_01",
    "notes": {
      "billing_cycle": "january_2025"
    }
  }'
```

### Get Payment Transaction
Get specific payment transaction details.

```bash
curl -X GET "http://localhost:8001/api/payments/transactions/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### List My Transactions
Get all payment transactions for the current user.

```bash
curl -X GET "http://localhost:8001/api/payments/transactions?status=captured&skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### Get Payment Statistics
Get payment statistics for the current user.

```bash
curl -X GET "http://localhost:8001/api/payments/stats" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### Razorpay Webhook
Webhook endpoint for Razorpay events (used by Razorpay, not for manual testing).

```bash
curl -X POST "http://localhost:8001/api/payments/webhooks" \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: webhook_signature_here" \
  -d '{
    "entity": "event",
    "account_id": "acc_xxx",
    "event": "payment.captured",
    "payload": {
      "payment": {
        "entity": {
          "id": "pay_xxx",
          "amount": 100000,
          "status": "captured"
        }
      }
    }
  }'
```

---

## Admin

### Get Request Logs
Get API request logs for monitoring.

```bash
curl -X GET "http://localhost:8001/api/admin/logs/requests?limit=10&refresh=true" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### Get Request Log Details
Get detailed information about a specific request.

```bash
curl -X GET "http://localhost:8001/api/admin/logs/requests/request_id_here" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### Get Database Info
Get information about the logging database.

```bash
curl -X GET "http://localhost:8001/api/admin/logs/db-info" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### Get Log Statistics
Get statistics about the logs in the database.

```bash
curl -X GET "http://localhost:8001/api/admin/logs/stats" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### Get Payment Statistics (Admin)
Get comprehensive payment statistics for admin monitoring.

```bash
curl -X GET "http://localhost:8001/api/admin/payments/stats" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### List All Mandates (Admin)
List all mandates for admin monitoring.

```bash
curl -X GET "http://localhost:8001/api/admin/payments/mandates?status=active&skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### Get Failed Payments (Admin)
Get failed payments for admin analysis.

```bash
curl -X GET "http://localhost:8001/api/admin/payments/failed?skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### List Webhook Events (Admin)
List webhook events for admin monitoring.

```bash
curl -X GET "http://localhost:8001/api/admin/webhooks/events?event_type=payment.captured&status=processed&skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### List Payment Customers (Admin)
List payment customers for admin monitoring.

```bash
curl -X GET "http://localhost:8001/api/admin/payments/customers?skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

### Get Payment Analytics (Admin)
Get payment analytics for specified number of days.

```bash
curl -X GET "http://localhost:8001/api/admin/analytics/payments?days=30" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Accept: application/json"
```

---

## Common Response Format

All endpoints return responses in a standardized format:

```json
{
  "status": "success" | "error",
  "timestamp": "2025-05-30T10:00:00.000Z",
  "status_code": 200,
  "message": "Operation completed successfully",
  "data": { /* Response data */ },
  "errors": [
    {
      "code": "ERROR_CODE",
      "message": "Error description"
    }
  ],
  "meta": {
    "elapsed_ms": 150.5,
    "request_id": "req_12345",
    "correlation_id": "corr_67890"
  }
}
```

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Get the access token by calling the `/api/auth/login` endpoint.

## Error Handling

The API uses standard HTTP status codes and returns detailed error information in the response body.

Common status codes:
- `200` - OK
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error
- `502` - Bad Gateway (External API Error)

## Environment Setup

Before testing, ensure you have:

1. Set up your environment variables (copy `env_example.txt` to `.env`)
2. Started the FastAPI server: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`
3. Run database migrations: `alembic upgrade head`

## Note on Razorpay Integration

To test Razorpay payment endpoints, you need to:

1. Set up Razorpay API credentials in your `.env` file
2. Install missing dependency: `pip install setuptools` (to fix the `pkg_resources` error)
3. Configure webhook endpoints in your Razorpay dashboard

Replace `YOUR_ACCESS_TOKEN` and `YOUR_ADMIN_TOKEN` with actual JWT tokens obtained from the login endpoints. 