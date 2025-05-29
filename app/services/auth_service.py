"""
Authentication service for JWT and API key management
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import bcrypt
import jwt
from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.auth import APIKey, APIKeyUsage, RefreshToken, User
from app.schemas.auth import (
    APIKeyCreate,
    AuthContext,
    AuthValidation,
    TokenPayload,
    UserCreate,
    UserLogin,
)
from app.utils.logger import logger


class AuthenticationService:
    """
    Service for handling JWT and API key authentication
    """

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = 30  # 30 days for refresh tokens

    # ========================================================================
    # Password Utilities
    # ========================================================================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    # ========================================================================
    # JWT Token Management
    # ========================================================================

    def create_access_token(self, user_id: int, username: str, scopes: List[str] = None) -> str:
        """Create a JWT access token"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": str(user_id),
            "username": username,
            "exp": expire,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "type": "access",
            "scopes": scopes or []
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: int, device_info: str = None, ip_address: str = None) -> Tuple[str, str]:
        """Create a refresh token and return (token, token_hash)"""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        logger.info(
            "Refresh token created",
            extra={
                "event_type": "refresh_token_created",
                "user_id": user_id,
                "device_info": device_info,
                "ip_address": ip_address
            }
        )

        return token, token_hash

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired", extra={"event_type": "token_expired"})
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(
                "Invalid token",
                extra={
                    "event_type": "token_invalid",
                    "error": str(e)
                }
            )
            return None

    # ========================================================================
    # User Management
    # ========================================================================

    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = await self.get_user_by_email_or_username(
            db, user_data.email, user_data.username
        )
        if existing_user:
            raise ValueError("User with this email or username already exists")

        # Create new user
        hashed_password = self.hash_password(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            is_verified=user_data.is_verified
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(
            "User created",
            extra={
                "event_type": "user_created",
                "user_id": user.id,
                "username": user.username,
                "email": user.email
            }
        )

        return user

    async def authenticate_user(self, db: AsyncSession, login_data: UserLogin) -> Optional[User]:
        """Authenticate a user with username/email and password"""
        user = await self.get_user_by_email_or_username(db, login_data.username, login_data.username)

        if not user:
            logger.warning(
                "Login attempt with non-existent user",
                extra={
                    "event_type": "login_failed",
                    "username": login_data.username,
                    "reason": "user_not_found"
                }
            )
            return None

        if not self.verify_password(login_data.password, user.hashed_password):
            logger.warning(
                "Login attempt with wrong password",
                extra={
                    "event_type": "login_failed",
                    "user_id": user.id,
                    "username": user.username,
                    "reason": "wrong_password"
                }
            )
            return None

        if not user.is_active:
            logger.warning(
                "Login attempt by inactive user",
                extra={
                    "event_type": "login_failed",
                    "user_id": user.id,
                    "username": user.username,
                    "reason": "user_inactive"
                }
            )
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()

        logger.info(
            "User authenticated successfully",
            extra={
                "event_type": "login_success",
                "user_id": user.id,
                "username": user.username
            }
        )

        return user

    async def get_user_by_email_or_username(self, db: AsyncSession, email: str, username: str) -> Optional[User]:
        """Get user by email or username"""
        result = await db.execute(
            User.__table__.select().where(
                or_(User.email == email, User.username == username)
            )
        )
        user_row = result.fetchone()
        return User(**user_row._asdict()) if user_row else None

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(
            User.__table__.select().where(User.id == user_id)
        )
        user_row = result.fetchone()
        return User(**user_row._asdict()) if user_row else None

    # ========================================================================
    # API Key Management
    # ========================================================================

    async def create_api_key(self, db: AsyncSession, key_data: APIKeyCreate, created_by_user_id: int = None) -> Tuple[APIKey, str]:
        """Create a new API key and return (api_key, secret_key)"""
        # Generate key ID and secret
        key_id = f"ak_{secrets.token_hex(8)}"
        secret_key = f"sk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(secret_key.encode()).hexdigest()

        # Create API key
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=key_data.name,
            description=key_data.description,
            created_by_user_id=created_by_user_id,
            organization=key_data.organization,
            scopes=key_data.scopes,
            rate_limit=key_data.rate_limit,
            allowed_ips=key_data.allowed_ips,
            expires_at=key_data.expires_at
        )

        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        logger.info(
            "API key created",
            extra={
                "event_type": "api_key_created",
                "api_key_id": api_key.id,
                "key_id": key_id,
                "name": key_data.name,
                "created_by_user_id": created_by_user_id
            }
        )

        return api_key, secret_key

    async def validate_api_key(self, db: AsyncSession, api_key: str, ip_address: str = None) -> AuthValidation:
        """Validate an API key"""
        try:
            # Extract key_id and secret from the API key
            if not api_key.startswith(("ak_", "sk_")):
                return AuthValidation(valid=False, error="Invalid API key format")

            # For keys starting with ak_, we expect the full key in the format: ak_xxxxx.sk_yyyyy
            if "." in api_key:
                key_id, secret = api_key.split(".", 1)
            else:
                return AuthValidation(valid=False, error="Invalid API key format")

            # Get API key from database
            result = await db.execute(
                APIKey.__table__.select().where(APIKey.key_id == key_id)
            )
            key_row = result.fetchone()

            if not key_row:
                logger.warning(
                    "API key validation failed - key not found",
                    extra={
                        "event_type": "api_key_validation_failed",
                        "key_id": key_id,
                        "reason": "key_not_found"
                    }
                )
                return AuthValidation(valid=False, error="Invalid API key")

            api_key_obj = APIKey(**key_row._asdict())

            # Verify secret
            secret_hash = hashlib.sha256(secret.encode()).hexdigest()
            if secret_hash != api_key_obj.key_hash:
                logger.warning(
                    "API key validation failed - wrong secret",
                    extra={
                        "event_type": "api_key_validation_failed",
                        "key_id": key_id,
                        "api_key_id": api_key_obj.id,
                        "reason": "wrong_secret"
                    }
                )
                return AuthValidation(valid=False, error="Invalid API key")

            # Check if key is active
            if not api_key_obj.is_active or api_key_obj.is_revoked:
                logger.warning(
                    "API key validation failed - key inactive/revoked",
                    extra={
                        "event_type": "api_key_validation_failed",
                        "key_id": key_id,
                        "api_key_id": api_key_obj.id,
                        "reason": "key_inactive"
                    }
                )
                return AuthValidation(valid=False, error="API key is inactive or revoked")

            # Check expiration
            if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
                logger.warning(
                    "API key validation failed - key expired",
                    extra={
                        "event_type": "api_key_validation_failed",
                        "key_id": key_id,
                        "api_key_id": api_key_obj.id,
                        "reason": "key_expired"
                    }
                )
                return AuthValidation(valid=False, error="API key has expired")

            # Check IP restrictions
            if api_key_obj.allowed_ips and ip_address:
                if ip_address not in api_key_obj.allowed_ips:
                    logger.warning(
                        "API key validation failed - IP not allowed",
                        extra={
                            "event_type": "api_key_validation_failed",
                            "key_id": key_id,
                            "api_key_id": api_key_obj.id,
                            "ip_address": ip_address,
                            "reason": "ip_not_allowed"
                        }
                    )
                    return AuthValidation(valid=False, error="IP address not allowed for this API key")

            # Update usage statistics
            api_key_obj.last_used = datetime.utcnow()
            api_key_obj.total_requests += 1
            api_key_obj.last_request_ip = ip_address
            await db.commit()

            # Create auth context
            auth_context = AuthContext(
                auth_type="api_key",
                api_key_id=api_key_obj.id,
                api_key_name=api_key_obj.name,
                scopes=api_key_obj.scopes or [],
                rate_limit=api_key_obj.rate_limit,
                ip_address=ip_address
            )

            logger.info(
                "API key validated successfully",
                extra={
                    "event_type": "api_key_validated",
                    "key_id": key_id,
                    "api_key_id": api_key_obj.id,
                    "name": api_key_obj.name
                }
            )

            return AuthValidation(valid=True, auth_context=auth_context)

        except Exception as e:
            logger.error(
                "API key validation error",
                extra={
                    "event_type": "api_key_validation_error",
                    "error": str(e)
                }
            )
            return AuthValidation(valid=False, error="Internal validation error")

    # ========================================================================
    # Token Validation
    # ========================================================================

    async def validate_jwt_token(self, db: AsyncSession, token: str) -> AuthValidation:
        """Validate a JWT token"""
        token_payload = self.decode_token(token)

        if not token_payload:
            return AuthValidation(valid=False, error="Invalid or expired token")

        if token_payload.type != "access":
            return AuthValidation(valid=False, error="Invalid token type")

        # Get user from database
        user = await self.get_user_by_id(db, int(token_payload.sub))

        if not user:
            logger.warning(
                "JWT validation failed - user not found",
                extra={
                    "event_type": "jwt_validation_failed",
                    "user_id": token_payload.sub,
                    "reason": "user_not_found"
                }
            )
            return AuthValidation(valid=False, error="User not found")

        if not user.is_active:
            logger.warning(
                "JWT validation failed - user inactive",
                extra={
                    "event_type": "jwt_validation_failed",
                    "user_id": user.id,
                    "reason": "user_inactive"
                }
            )
            return AuthValidation(valid=False, error="User is inactive")

        # Create auth context
        auth_context = AuthContext(
            auth_type="jwt",
            user_id=user.id,
            username=user.username,
            scopes=token_payload.scopes,
            is_superuser=user.is_superuser
        )

        logger.debug(
            "JWT token validated successfully",
            extra={
                "event_type": "jwt_validated",
                "user_id": user.id,
                "username": user.username
            }
        )

        return AuthValidation(valid=True, auth_context=auth_context)


# Global authentication service instance
auth_service = AuthenticationService()
