"""
Events Router
Handles event streaming operations (create, list, subscribe)
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import authentication
try:
    from app.api.deps import get_current_user_flexible
    from app.models.user import User
except ImportError:
    class MockUser:
        def __init__(self):
            self.id = "00000000-0000-0000-0000-000000000001"

    User = MockUser

    def get_current_user_flexible():
        return lambda: MockUser()

# Import services
from services.database_service import database_service
from services.events_service import events_service


router = APIRouter()


# Schemas
class EventCreate(BaseModel):
    """Schema for creating an event"""
    event_type: str = Field(..., description="Event type/category")
    event_data: Dict[str, Any] = Field(..., description="Event payload")
    source: Optional[str] = Field(default=None, description="Event source identifier")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracing")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "user.signup",
                "event_data": {"user_id": "123", "email": "user@example.com"},
                "source": "auth-service",
                "correlation_id": "trace-456"
            }
        }


class EventResponse(BaseModel):
    """Schema for event response"""
    id: str
    event_type: str
    source: Optional[str]
    correlation_id: Optional[str]
    event_data: Dict[str, Any]
    timestamp: Optional[str]


class EventStats(BaseModel):
    """Schema for event statistics"""
    time_range: str
    total_events: int
    event_type_count: int
    source_count: int
    top_event_types: List[Dict[str, Any]]
    event_type: Optional[str]


class SubscriptionResponse(BaseModel):
    """Schema for subscription response"""
    subscription_id: str
    topic: str
    event_types: Optional[List[str]]


# Endpoints

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    project_id: UUID,
    event: EventCreate,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Create an event

    **Flow:**
    1. Store in PostgreSQL (persistent history)
    2. Publish to RedPanda (real-time streaming)

    **Authentication:** Required

    **Parameters:**
    - event_type: Event type/category
    - event_data: Event payload (JSON)
    - source: Event source identifier (optional)
    - correlation_id: Correlation ID for tracing (optional)

    **Returns:**
    - Event object with generated ID and timestamp
    """
    try:
        result = await events_service.create_event(
            db=db,
            project_id=project_id,
            event_type=event.event_type,
            event_data=event.event_data,
            source=event.source,
            correlation_id=event.correlation_id
        )

        return EventResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating event: {str(e)}"
        )


@router.get("", response_model=List[EventResponse])
async def list_events(
    project_id: UUID,
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    List events with filtering

    **Authentication:** Required

    **Query Parameters:**
    - event_type: Filter by event type (optional)
    - source: Filter by source (optional)
    - start_time: Filter by start timestamp (optional)
    - end_time: Filter by end timestamp (optional)
    - skip: Number to skip for pagination
    - limit: Max results (max 100)

    **Returns:**
    - List of events
    """
    try:
        if limit > 100:
            limit = 100

        results = await events_service.list_events(
            db=db,
            project_id=project_id,
            event_type=event_type,
            source=source,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=limit
        )

        return [EventResponse(**result) for result in results]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing events: {str(e)}"
        )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    project_id: UUID,
    event_id: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get a specific event by ID

    **Authentication:** Required

    **Path Parameters:**
    - event_id: Event ID

    **Returns:**
    - Event object
    """
    try:
        result = await events_service.get_event(
            db=db,
            project_id=project_id,
            event_id=event_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        return EventResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving event: {str(e)}"
        )


@router.get("/stats/summary", response_model=EventStats)
async def get_event_stats(
    project_id: UUID,
    time_range: str = "day",
    event_type: Optional[str] = None,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get event statistics

    **Authentication:** Required

    **Query Parameters:**
    - time_range: Time range (hour, day, week, month)
    - event_type: Filter by event type (optional)

    **Returns:**
    - total_events: Total count
    - event_type_count: Number of unique event types
    - source_count: Number of unique sources
    - top_event_types: Top 10 event types with counts
    """
    try:
        if time_range not in ["hour", "day", "week", "month"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="time_range must be: hour, day, week, or month"
            )

        stats = await events_service.get_event_stats(
            db=db,
            project_id=project_id,
            time_range=time_range,
            event_type=event_type
        )

        return EventStats(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving event stats: {str(e)}"
        )


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_events(
    project_id: UUID,
    event_types: Optional[List[str]] = None,
    current_user = Depends(get_current_user_flexible)
):
    """
    Subscribe to event stream

    **Authentication:** Required

    **Parameters:**
    - event_types: Optional filter by event types

    **Returns:**
    - subscription_id: Subscription identifier
    - topic: RedPanda topic name
    - event_types: Filtered event types
    """
    try:
        result = await events_service.subscribe_to_events(
            project_id=project_id,
            event_types=event_types
        )

        return SubscriptionResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error subscribing to events: {str(e)}"
        )
