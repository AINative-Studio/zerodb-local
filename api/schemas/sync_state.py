"""
Sync State Schemas
Pydantic models for sync state tracking operations
"""
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# Enums for sync state
SyncStrategy = Literal["full", "incremental", "selective"]
SyncDirection = Literal["push", "pull", "bidirectional"]
EntityType = Literal["vectors", "tables", "memory", "files", "events"]


class WatermarkSchema(BaseModel):
    """
    Watermark schema for incremental sync tracking

    Structure varies by entity_type:
    - vectors: {"last_vector_id": "uuid", "last_timestamp": "iso8601"}
    - tables: {"table_id": {"last_row_id": "uuid", "last_timestamp": "iso8601"}}
    - events: {"last_event_id": "uuid", "last_timestamp": "iso8601", "offset": 123}
    """
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Watermark data specific to entity type"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "last_vector_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "last_timestamp": "2025-12-28T12:00:00Z"
                }
            }
        }


class SyncStateCreate(BaseModel):
    """Schema for creating sync state"""
    project_id: UUID = Field(..., description="Project ID")
    entity_type: EntityType = Field(..., description="Entity type to track")
    sync_strategy: SyncStrategy = Field(
        default="full",
        description="Sync strategy: full, incremental, or selective"
    )
    sync_direction: SyncDirection = Field(
        default="bidirectional",
        description="Sync direction: push, pull, or bidirectional"
    )
    watermark: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Initial watermark data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "entity_type": "vectors",
                "sync_strategy": "incremental",
                "sync_direction": "bidirectional",
                "watermark": {}
            }
        }


class SyncStateUpdate(BaseModel):
    """Schema for updating sync state"""
    last_sync_at: Optional[datetime] = Field(
        default=None,
        description="Last successful sync timestamp"
    )
    last_cloud_export_id: Optional[UUID] = Field(
        default=None,
        description="Last cloud export operation ID"
    )
    last_cloud_import_id: Optional[UUID] = Field(
        default=None,
        description="Last cloud import operation ID"
    )
    watermark: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated watermark data"
    )
    sync_strategy: Optional[SyncStrategy] = Field(
        default=None,
        description="Updated sync strategy"
    )
    sync_direction: Optional[SyncDirection] = Field(
        default=None,
        description="Updated sync direction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "last_sync_at": "2025-12-28T12:00:00Z",
                "watermark": {
                    "last_vector_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "last_timestamp": "2025-12-28T12:00:00Z"
                }
            }
        }


class SyncStateResponse(BaseModel):
    """Schema for sync state response"""
    id: UUID
    project_id: UUID
    entity_type: str
    last_sync_at: Optional[datetime]
    last_cloud_export_id: Optional[UUID]
    last_cloud_import_id: Optional[UUID]
    watermark: Dict[str, Any]
    sync_strategy: str
    sync_direction: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "entity_type": "vectors",
                "last_sync_at": "2025-12-28T12:00:00Z",
                "last_cloud_export_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "last_cloud_import_id": None,
                "watermark": {
                    "last_vector_id": "d4e5f6a7-b8c9-0123-def1-234567890123",
                    "last_timestamp": "2025-12-28T12:00:00Z"
                },
                "sync_strategy": "incremental",
                "sync_direction": "bidirectional",
                "created_at": "2025-12-28T10:00:00Z",
                "updated_at": "2025-12-28T12:00:00Z"
            }
        }


class SyncStateListResponse(BaseModel):
    """Schema for listing sync states"""
    items: list[SyncStateResponse]
    total: int
    project_id: UUID

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 5,
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        }
