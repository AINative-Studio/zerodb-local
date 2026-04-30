"""
Project Schemas
Pydantic models for project operations
"""
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project — matches cloud API"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    tier: str = Field(default="free", description="Project tier")
    database_enabled: bool = Field(default=True, description="Enable database features")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Project settings (JSON)")


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
    """Schema for project response — matches cloud API schema"""
    id: UUID
    name: str
    description: Optional[str] = None
    user_id: UUID
    organization_id: Optional[UUID] = None
    tier: str = "free"
    status: str = "ACTIVE"
    database_enabled: bool = True
    database_config: Dict[str, Any] = Field(default_factory=dict)
    vector_dimensions: int = 1536
    quantum_enabled: bool = False
    mcp_enabled: bool = False
    railway_project_id: Optional[str] = None
    usage: Dict[str, Any] = Field(default_factory=lambda: {
        "vectors": 0, "tables": 0, "events": 0, "memory": 0, "files": 0
    })
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
