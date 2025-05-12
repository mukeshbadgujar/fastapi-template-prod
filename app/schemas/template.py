from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, validator


# Base model shared between create/update/read operations
class ItemBase(BaseModel):
    """
    Base model for item shared attributes
    """
    name: str = Field(..., min_length=1, max_length=100, description="The name of the item")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the item")
    is_active: bool = Field(True, description="Whether the item is active")


# Model for creating items (used in POST requests)
class ItemCreate(ItemBase):
    """
    Model for creating a new item
    """
    # Additional fields required for creation only
    category_id: int = Field(..., ge=1, description="Category ID the item belongs to")
    
    @validator("name")
    def name_must_not_contain_special_chars(cls, v):
        """
        Custom validation for the name field
        """
        if any(char in v for char in "!@#$%^&*()"):
            raise ValueError("name must not contain special characters")
        return v


# Model for updating items (used in PUT/PATCH requests)
class ItemUpdate(BaseModel):
    """
    Model for updating an existing item
    
    All fields are optional since this is for updates
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="The name of the item")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the item")
    is_active: Optional[bool] = Field(None, description="Whether the item is active")
    category_id: Optional[int] = Field(None, ge=1, description="Category ID the item belongs to")
    
    @validator("name")
    def name_must_not_contain_special_chars(cls, v):
        """
        Custom validation for the name field
        """
        if v is not None and any(char in v for char in "!@#$%^&*()"):
            raise ValueError("name must not contain special characters")
        return v


# Model for reads (used in GET responses)
class ItemRead(ItemBase):
    """
    Model for returning item data
    
    Includes all fields from the database
    """
    id: int = Field(..., description="The unique identifier of the item")
    category_id: int = Field(..., description="Category ID the item belongs to")
    created_at: datetime = Field(..., description="When the item was created")
    updated_at: Optional[datetime] = Field(None, description="When the item was last updated")
    
    class Config:
        """
        Pydantic config for this model
        """
        # Allow reading data from ORM objects
        from_attributes = True
        
        # Schema examples for documentation
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Sample Item",
                "description": "This is a sample item",
                "is_active": True,
                "category_id": 42,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-02T12:30:45Z"
            }
        }


# Model for list reads (used in list GET responses)
class ItemList(BaseModel):
    """
    Model for returning a list of items with pagination info
    """
    items: List[ItemRead] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


# Example of a more complex model with relationships
class UserBase(BaseModel):
    """Base model for user attributes"""
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    is_active: bool = Field(True, description="Whether the user is active")


class UserCreate(UserBase):
    """Model for creating a user"""
    password: str = Field(..., min_length=8, description="User's password")


class UserUpdate(BaseModel):
    """Model for updating a user"""
    email: Optional[EmailStr] = Field(None, description="User's email address")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")
    password: Optional[str] = Field(None, min_length=8, description="User's password")


class UserRead(UserBase):
    """Model for returning user data"""
    id: UUID = Field(..., description="The unique identifier of the user")
    created_at: datetime = Field(..., description="When the user was created")
    updated_at: Optional[datetime] = Field(None, description="When the user was last updated")
    
    class Config:
        """Pydantic config"""
        from_attributes = True


# Token models
class Token(BaseModel):
    """Model for token response"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenPayload(BaseModel):
    """Model for JWT token payload"""
    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration time (UNIX timestamp)")
    iat: int = Field(..., description="Issued at time (UNIX timestamp)")
    scope: str = Field("access_token", description="Token scope") 