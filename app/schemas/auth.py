"""
Authentication schemas for JWT users and API key management
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# ============================================================================
# User Authentication Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: bool = True
    is_verified: bool = False


class UserCreate(UserBase):
    """Schema for user creation"""
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v


class UserUpdate(BaseModel):
    """Schema for user updates"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    profile_data: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """Schema for user responses"""
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    profile_data: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('New passwords do not match')
        return v


# ============================================================================
# JWT Token Schemas
# ============================================================================

class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefresh(BaseModel):
    """Schema for token refresh request"""
    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for JWT token payload"""
    sub: str  # subject (user_id)
    exp: int  # expiration time
    iat: int  # issued at
    jti: str  # JWT ID
    type: str  # "access" or "refresh"
    user_id: Optional[int] = None
    username: Optional[str] = None
    scopes: List[str] = []


# ============================================================================
# API Key Schemas
# ============================================================================

class APIKeyBase(BaseModel):
    """Base API key schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    organization: Optional[str] = Field(None, max_length=255)
    scopes: Optional[List[str]] = Field(default_factory=list)
    rate_limit: Optional[int] = Field(None, ge=1, le=10000, description="Requests per minute")
    allowed_ips: Optional[List[str]] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    """Schema for API key creation"""
    pass


class APIKeyUpdate(BaseModel):
    """Schema for API key updates"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    scopes: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    allowed_ips: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class APIKeyResponse(APIKeyBase):
    """Schema for API key responses (without secret)"""
    id: int
    key_id: str
    created_by_user_id: Optional[int]
    created_at: datetime
    is_active: bool
    is_revoked: bool
    last_used: Optional[datetime] = None
    total_requests: int
    last_request_ip: Optional[str] = None

    model_config = {"from_attributes": True}


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes secret)"""
    secret_key: str = Field(..., description="This will only be shown once!")


class APIKeyUsageResponse(BaseModel):
    """Schema for API key usage statistics"""
    api_key_id: int
    key_name: str
    total_requests: int
    requests_today: int
    requests_this_week: int
    requests_this_month: int
    average_response_time_ms: Optional[float] = None
    error_rate_percent: Optional[float] = None
    last_used: Optional[datetime] = None
    top_endpoints: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# Authentication Context Schemas
# ============================================================================

class AuthContext(BaseModel):
    """Schema for authentication context in request state"""
    auth_type: str  # "jwt" or "api_key"
    user_id: Optional[int] = None
    username: Optional[str] = None
    api_key_id: Optional[int] = None
    api_key_name: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    is_superuser: bool = False

    # Rate limiting context
    rate_limit: Optional[int] = None
    request_count: int = 0

    # Request metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuthValidation(BaseModel):
    """Schema for authentication validation response"""
    valid: bool
    auth_context: Optional[AuthContext] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


# ============================================================================
# Admin Schemas
# ============================================================================

class UserListResponse(BaseModel):
    """Schema for paginated user list"""
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class APIKeyListResponse(BaseModel):
    """Schema for paginated API key list"""
    api_keys: List[APIKeyResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class AuthStatsResponse(BaseModel):
    """Schema for authentication statistics"""
    total_users: int
    active_users: int
    verified_users: int
    total_api_keys: int
    active_api_keys: int
    total_requests_today: int
    total_requests_this_week: int
    average_response_time_ms: Optional[float] = None
