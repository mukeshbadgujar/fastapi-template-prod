from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import TokenData
from app.auth.security import verify_token
from app.db.session import get_db
from app.models.user import User

# Security scheme
security = HTTPBearer()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract and validate the JWT token from the Authorization header
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Validated token
        
    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    username = verify_token(token)
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


async def get_current_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user
    
    Args:
        token: Validated JWT token
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If user not found or inactive
    """
    username = verify_token(token)
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    from app.services.user_service import get_user_by_username
    user = await get_user_by_username(db, username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active user (alias for get_current_user)
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current active user
    """
    return current_user


def get_optional_current_user():
    """
    Dependency that returns the current user if authenticated, None otherwise
    Useful for endpoints that work with or without authentication
    """
    async def _get_optional_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
        db: AsyncSession = Depends(get_db)
    ) -> Optional[User]:
        if credentials is None:
            return None
        
        try:
            token = credentials.credentials
            username = verify_token(token)
            
            if username is None:
                return None
            
            # Get user from database
            from app.services.user_service import get_user_by_username
            user = await get_user_by_username(db, username)
            
            if user is None or not user.is_active:
                return None
            
            return user
        except Exception:
            return None
    
    return _get_optional_current_user 