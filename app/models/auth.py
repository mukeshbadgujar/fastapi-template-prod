"""
Authentication models for JWT users and API key management
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

from app.db.base import Base


class User(Base):
    """
    User model for JWT-based authentication
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # User status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Profile information
    profile_data = Column(JSON, nullable=True)  # Flexible profile storage
    preferences = Column(JSON, nullable=True)   # User preferences


class RefreshToken(Base):
    """
    Refresh token model for JWT token rotation
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # Foreign key to users
    token_hash = Column(String(255), nullable=False, index=True)  # Hashed refresh token

    # Token metadata
    device_info = Column(String(500), nullable=True)  # User agent, device info
    ip_address = Column(String(45), nullable=True)    # IPv6 support

    # Token lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Security tracking
    last_used = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0, nullable=False)


class APIKey(Base):
    """
    API Key model for service-to-service authentication
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_id = Column(String(50), unique=True, index=True, nullable=False)  # Public identifier
    key_hash = Column(String(255), nullable=False, index=True)             # Hashed secret key

    # Key metadata
    name = Column(String(255), nullable=False)                # Human-readable name
    description = Column(Text, nullable=True)                 # Key description/purpose

    # Owner information
    created_by_user_id = Column(Integer, nullable=True, index=True)  # User who created it
    organization = Column(String(255), nullable=True)               # Organization/team

    # Key configuration
    scopes = Column(JSON, nullable=True)                      # API scopes/permissions
    rate_limit = Column(Integer, nullable=True)              # Requests per minute
    allowed_ips = Column(JSON, nullable=True)                # IP whitelist

    # Key lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)             # Null = never expires
    revoked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Usage tracking
    last_used = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)
    last_request_ip = Column(String(45), nullable=True)


class APIKeyUsage(Base):
    """
    API Key usage tracking for analytics and monitoring
    """
    __tablename__ = "api_key_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key_id = Column(Integer, nullable=False, index=True)  # Foreign key to api_keys

    # Request details
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)

    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    correlation_id = Column(String(255), nullable=True, index=True)

    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    request_size = Column(Integer, nullable=True)
    response_size = Column(Integer, nullable=True)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)
