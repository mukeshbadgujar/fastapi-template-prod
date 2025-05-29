import time
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.common.exceptions import NotFoundException
from app.common.response import PaginationMeta, ResponseUtil
from app.db.base import get_db
from app.utils.logger import logger

# Create a router for this API module
router = APIRouter(
    prefix="/template",  # Change this to your resource name
    tags=["Template"],   # Change this to your resource tag name
)


# GET - Retrieve a list of items
@router.get("/")
async def get_items(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of items to return"),
    search: Optional[str] = Query(None, description="Search term"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of items.

    This endpoint allows pagination and optional search.
    """
    # Get request_id and start_time from request state
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)

    logger.info(
        f"Getting items with skip={skip}, limit={limit}, search={search}",
        extra={"skip": skip, "limit": limit, "search": search}
    )

    # In real implementation, call your service layer here
    # Example: items, total = await item_service.get_items(db=db, skip=skip, limit=limit, search=search)

    # Return mock data for template
    items = [{"id": i, "name": f"Item {i}"} for i in range(skip, skip + limit)]
    total = 1000  # Mock total

    # Calculate pages
    pages = (total + limit - 1) // limit

    # Calculate elapsed time
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000

    # Create pagination metadata
    pagination = PaginationMeta(
        page=(skip // limit) + 1,
        size=limit,
        total=total,
        pages=pages
    )

    # Return standardized response
    return ResponseUtil.success_response(
        data=items,
        message="Items retrieved successfully",
        pagination=pagination,
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


# GET - Retrieve a single item by ID
@router.get("/{item_id}")
async def get_item(
    request: Request,
    item_id: int = Path(..., description="The ID of the item to retrieve"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a single item by its ID.
    """
    # Get request_id and start_time from request state
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)

    logger.info(f"Getting item with id={item_id}", extra={"item_id": item_id})

    # In real implementation, call your service layer here
    # Example: item = await item_service.get_item(db=db, item_id=item_id)
    # if not item:
    #     raise NotFoundException(detail=f"Item with id {item_id} not found")

    # Return mock data for template
    if item_id < 0:
        # Calculate elapsed time
        elapsed_ms = None
        if start_time:
            elapsed_ms = (time.time() - start_time) * 1000

        # Return not found response
        return ResponseUtil.not_found(
            entity="Item",
            message=f"Item with id {item_id} not found",
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )

    # Mock item data
    item = {"id": item_id, "name": f"Item {item_id}"}

    # Calculate elapsed time
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000

    # Return standardized response
    return ResponseUtil.success_response(
        data=item,
        message="Item retrieved successfully",
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


# POST - Create a new item
@router.post("/")
async def create_item(
    request: Request,
    # item_in: ItemCreate,  # Change to your schema
    db: Session = Depends(get_db),
):
    """
    Create a new item.
    """
    # Get request_id and start_time from request state
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)

    # For template purposes, we're not using real schemas
    item_in = {"name": "New Item"}

    logger.info(f"Creating new item: {item_in}", extra={"item_data": item_in})

    # In real implementation, call your service layer here
    # Example: item = await item_service.create_item(db=db, item_in=item_in)

    # Return mock data for template
    new_item = {"id": 123, "name": item_in["name"]}

    # Calculate elapsed time
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000

    # Return standardized response
    return ResponseUtil.success_response(
        data=new_item,
        message="Item created successfully",
        status_code=status.HTTP_201_CREATED,
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


# PUT - Update an existing item
@router.put("/{item_id}")
async def update_item(
    request: Request,
    item_id: int = Path(..., description="The ID of the item to update"),
    # item_in: ItemUpdate,  # Change to your schema
    db: Session = Depends(get_db),
):
    """
    Update an existing item.
    """
    # Get request_id and start_time from request state
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)

    # For template purposes, we're not using real schemas
    item_in = {"name": "Updated Item"}

    logger.info(
        f"Updating item with id={item_id}: {item_in}",
        extra={"item_id": item_id, "item_data": item_in}
    )

    # In real implementation, call your service layer here
    # Example:
    # existing_item = await item_service.get_item(db=db, item_id=item_id)
    # if not existing_item:
    #     raise NotFoundException(detail=f"Item with id {item_id} not found")
    # item = await item_service.update_item(db=db, item_id=item_id, item_in=item_in)

    # Return mock data for template
    if item_id < 0:
        # Calculate elapsed time
        elapsed_ms = None
        if start_time:
            elapsed_ms = (time.time() - start_time) * 1000

        # Return not found response
        return ResponseUtil.not_found(
            entity="Item",
            message=f"Item with id {item_id} not found",
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )

    # Mock updated item
    updated_item = {"id": item_id, "name": item_in["name"]}

    # Calculate elapsed time
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000

    # Return standardized response
    return ResponseUtil.success_response(
        data=updated_item,
        message="Item updated successfully",
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


# DELETE - Delete an item
@router.delete("/{item_id}")
async def delete_item(
    request: Request,
    item_id: int = Path(..., description="The ID of the item to delete"),
    db: Session = Depends(get_db),
):
    """
    Delete an item.
    """
    # Get request_id and start_time from request state
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)

    logger.info(f"Deleting item with id={item_id}", extra={"item_id": item_id})

    # In real implementation, call your service layer here
    # Example:
    # existing_item = await item_service.get_item(db=db, item_id=item_id)
    # if not existing_item:
    #     raise NotFoundException(detail=f"Item with id {item_id} not found")
    # await item_service.delete_item(db=db, item_id=item_id)

    # For template, just check if ID is valid
    if item_id < 0:
        # Calculate elapsed time
        elapsed_ms = None
        if start_time:
            elapsed_ms = (time.time() - start_time) * 1000

        # Return not found response
        return ResponseUtil.not_found(
            entity="Item",
            message=f"Item with id {item_id} not found",
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )

    # Calculate elapsed time
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000

    # Return standardized response for deletion
    return ResponseUtil.success_response(
        message="Item deleted successfully",
        status_code=status.HTTP_200_OK,  # Using 200 instead of 204 to allow message content
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )
