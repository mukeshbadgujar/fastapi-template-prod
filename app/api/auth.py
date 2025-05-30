from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.models import (
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.auth.security import (
    create_access_token,
    create_reset_token,
    get_password_hash,
    verify_password,
    verify_reset_token,
)
from app.config.settings import settings
from app.db.session import get_db
from app.models.user import User
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_username,
    update_user,
)
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = await get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    existing_email = await get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = await create_user(db, user_data)
    
    logger.info(
        f"New user registered: {user.username}",
        extra={
            "event_type": "user_registered",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )
    
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Login and get access token
    """
    user = await authenticate_user(db, login_data.username, login_data.password)
    if not user:
        logger.warning(
            f"Failed login attempt for username: {login_data.username}",
            extra={
                "event_type": "login_failed",
                "username": login_data.username,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    
    logger.info(
        f"User logged in: {user.username}",
        extra={
            "event_type": "user_login",
            "user_id": user.id,
            "username": user.username,
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/login/oauth", response_model=TokenResponse)
async def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible login endpoint
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(
            f"Failed OAuth login attempt for username: {form_data.username}",
            extra={
                "event_type": "oauth_login_failed",
                "username": form_data.username,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    
    logger.info(
        f"User logged in via OAuth: {user.username}",
        extra={
            "event_type": "oauth_user_login",
            "user_id": user.id,
            "username": user.username,
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user information
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user information
    """
    # Check if username is being changed and if it's already taken
    if user_update.username and user_update.username != current_user.username:
        existing_user = await get_user_by_username(db, user_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Check if email is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_email = await get_user_by_email(db, user_update.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
    
    updated_user = await update_user(db, current_user.id, user_update)
    
    logger.info(
        f"User updated profile: {current_user.username}",
        extra={
            "event_type": "user_profile_updated",
            "user_id": current_user.id,
            "username": current_user.username,
        }
    )
    
    return updated_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change user password
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    hashed_password = get_password_hash(password_data.new_password)
    user_update = UserUpdate(password=password_data.new_password)
    await update_user(db, current_user.id, user_update)
    
    logger.info(
        f"User changed password: {current_user.username}",
        extra={
            "event_type": "password_changed",
            "user_id": current_user.id,
            "username": current_user.username,
        }
    )
    
    return {"message": "Password updated successfully"}


@router.post("/reset-password")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Request password reset
    """
    user = await get_user_by_email(db, reset_data.email)
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Create reset token
    reset_token = create_reset_token(user.email)
    
    # In a real application, you would send this token via email
    # For now, we'll just log it
    logger.info(
        f"Password reset requested for user: {user.username}",
        extra={
            "event_type": "password_reset_requested",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "reset_token": reset_token,  # In production, don't log the token
        }
    )
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Confirm password reset with token
    """
    email = verify_reset_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user_update = UserUpdate(password=reset_data.new_password)
    await update_user(db, user.id, user_update)
    
    logger.info(
        f"Password reset completed for user: {user.username}",
        extra={
            "event_type": "password_reset_completed",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        }
    )
    
    return {"message": "Password reset successfully"}


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Logout user (client should discard the token)
    """
    logger.info(
        f"User logged out: {current_user.username}",
        extra={
            "event_type": "user_logout",
            "user_id": current_user.id,
            "username": current_user.username,
        }
    )
    
    return {"message": "Successfully logged out"} 