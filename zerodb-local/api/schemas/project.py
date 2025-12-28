"""
Project Schemas
Pydantic models for project operations
"""
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Project name"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Project description"
    )
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Project settings (JSON)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-ai-project",
                "description": "My first AI project with ZeroDB Local",
                "settings": {
                    "embeddings_model": "bge-small-en-v1.5",
                    "vector_dimensions": 384
                }
            }
        }


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="New project name"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="New project description"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated settings"
    )


class ProjectResponse(BaseModel):
    """Schema for project response"""
    id: UUID
    name: str
    description: Optional[str]
    user_id: UUID
    organization_id: Optional[UUID]
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "my-ai-project",
                "description": "My first AI project",
                "user_id": "user-123",
                "organization_id": None,
                "settings": {},
                "created_at": "2025-12-28T12:00:00Z",
                "updated_at": "2025-12-28T12:00:00Z"
            }
        }


class ProjectStats(BaseModel):
    """Schema for project statistics"""
    project_id: UUID
    vector_count: int
    memory_count: int
    table_count: int
    file_count: int
    event_count: int
    storage_bytes: int

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "vector_count": 1523,
                "memory_count": 342,
                "table_count": 5,
                "file_count": 12,
                "event_count": 89,
                "storage_bytes": 524288000
            }
        }
