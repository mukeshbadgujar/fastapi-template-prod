"""
Template Models

This module contains SQLAlchemy models for template-related entities.
These models serve as examples and should be modified according to your specific use case.
"""

import uuid
from datetime import datetime
from typing import Any, List, Optional, Union

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.user import Base


class TimestampMixin:
    """
    Mixin to add created_at and updated_at timestamps to models
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=None, onupdate=datetime.utcnow)


class Item(Base, TimestampMixin):
    """
    Example Item model

    Demonstrates a basic database model with relationships
    """
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Foreign keys
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships - use string references to avoid circular imports
    category = relationship("Category", back_populates="items")
    # Note: User relationship removed to avoid circular import

    # Additional constraints
    __table_args__ = (
        UniqueConstraint("name", "category_id", name="uq_item_name_category"),
    )

    def __repr__(self) -> str:
        """String representation of the model"""
        return f"<Item(id={self.id}, name='{self.name}')>"


class Category(Base, TimestampMixin):
    """
    Example Category model

    Demonstrates a model with child relationships
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Relationships - One-to-Many with Item
    items = relationship("Item", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of the model"""
        return f"<Category(id={self.id}, name='{self.name}')>"


class Transaction(Base, TimestampMixin):
    """
    Example Transaction model

    Demonstrates a model with monetary values and computed columns
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships - use string reference to avoid circular import
    # Note: User relationship removed to avoid circular import

    def __repr__(self) -> str:
        """String representation of the model"""
        return f"<Transaction(id={self.id}, amount={self.amount})>"
