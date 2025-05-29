from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.exceptions import NotFoundException, ValidationException
from app.models.template import Item
from app.schemas.template import ItemCreate, ItemUpdate
from app.utils.logger import logger


class ItemService:
    """
    Service for handling business logic related to items

    This class centralizes all item-related operations to keep
    API routes focused on HTTP handling rather than business logic.
    """

    async def get_items(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        owner_id: Optional[Union[int, UUID]] = None,
    ) -> Tuple[List[Item], int]:
        """
        Get a list of items with optional filtering and pagination

        Args:
            db: Database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            search: Optional search string to filter by name
            category_id: Optional category ID to filter by
            owner_id: Optional owner ID to filter by

        Returns:
            Tuple of (list of items, total count)
        """
        logger.info(
            f"Getting items with skip={skip}, limit={limit}, search={search}, "
            f"category_id={category_id}, owner_id={owner_id}"
        )

        # Start building query
        query = select(Item)

        # Add filters
        if search:
            query = query.filter(Item.name.ilike(f"%{search}%"))

        if category_id:
            query = query.filter(Item.category_id == category_id)

        if owner_id:
            query = query.filter(Item.owner_id == owner_id)

        # Get total count for pagination
        count_query = select(func.count()).select_from(query.alias())
        total = await db.execute(count_query)
        total = total.scalar()

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()

        return items, total

    async def get_item(
        self,
        db: Session,
        item_id: int
    ) -> Optional[Item]:
        """
        Get a single item by ID

        Args:
            db: Database session
            item_id: Item ID to retrieve

        Returns:
            Item object or None if not found
        """
        logger.info(f"Getting item with id={item_id}")

        query = select(Item).filter(Item.id == item_id)
        result = await db.execute(query)
        item = result.scalar_one_or_none()

        return item

    async def create_item(
        self,
        db: Session,
        item_in: ItemCreate,
        owner_id: Union[int, UUID]
    ) -> Item:
        """
        Create a new item

        Args:
            db: Database session
            item_in: Item data for creation
            owner_id: ID of the owner

        Returns:
            Newly created Item
        """
        logger.info(f"Creating new item: {item_in.dict()}")

        # Create the item with data from item_in and the provided owner_id
        item_data = item_in.dict()
        item_data["owner_id"] = owner_id

        # Create new item instance
        item = Item(**item_data)

        # Add to database
        db.add(item)
        await db.commit()
        await db.refresh(item)

        logger.info(f"Successfully created item with id={item.id}")

        return item

    async def update_item(
        self,
        db: Session,
        item_id: int,
        item_in: ItemUpdate,
        owner_id: Optional[Union[int, UUID]] = None
    ) -> Item:
        """
        Update an existing item

        Args:
            db: Database session
            item_id: Item ID to update
            item_in: Item data for update
            owner_id: Optional owner ID to validate ownership

        Returns:
            Updated Item

        Raises:
            NotFoundException: If item doesn't exist
            ValidationException: If owner_id is provided and doesn't match item's owner
        """
        logger.info(f"Updating item with id={item_id}: {item_in.dict(exclude_unset=True)}")

        # Get the existing item
        item = await self.get_item(db, item_id)
        if not item:
            logger.warning(f"Item with id={item_id} not found for update")
            raise NotFoundException(detail=f"Item with id {item_id} not found")

        # If owner_id is provided, validate ownership
        if owner_id and str(item.owner_id) != str(owner_id):
            logger.warning(f"Update attempt for item id={item_id} by non-owner (owner_id={owner_id})")
            raise ValidationException(detail="You can only update your own items")

        # Get item data as dict
        item_data = jsonable_encoder(item)

        # Update fields with new values
        update_data = item_in.dict(exclude_unset=True)
        for field in item_data:
            if field in update_data:
                setattr(item, field, update_data[field])

        # Save to database
        db.add(item)
        await db.commit()
        await db.refresh(item)

        logger.info(f"Successfully updated item with id={item.id}")

        return item

    async def delete_item(
        self,
        db: Session,
        item_id: int,
        owner_id: Optional[Union[int, UUID]] = None
    ) -> bool:
        """
        Delete an item

        Args:
            db: Database session
            item_id: Item ID to delete
            owner_id: Optional owner ID to validate ownership

        Returns:
            True if successful

        Raises:
            NotFoundException: If item doesn't exist
            ValidationException: If owner_id is provided and doesn't match item's owner
        """
        logger.info(f"Deleting item with id={item_id}")

        # Get the existing item
        item = await self.get_item(db, item_id)
        if not item:
            logger.warning(f"Item with id={item_id} not found for deletion")
            raise NotFoundException(detail=f"Item with id {item_id} not found")

        # If owner_id is provided, validate ownership
        if owner_id and str(item.owner_id) != str(owner_id):
            logger.warning(f"Delete attempt for item id={item_id} by non-owner (owner_id={owner_id})")
            raise ValidationException(detail="You can only delete your own items")

        # Delete the item
        await db.delete(item)
        await db.commit()

        logger.info(f"Successfully deleted item with id={item_id}")

        return True


# Create a singleton instance
item_service = ItemService()
