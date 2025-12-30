"""
Change Log Schemas
Pydantic models for CDC (Change Data Capture) operations
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class OperationType(str, Enum):
    """Database operation types"""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class EntityType(str, Enum):
    """Entity types that are tracked"""
    VECTOR = "vector"
    TABLE_ROW = "table_row"
    FILE = "file"
    EVENT = "event"
    MEMORY = "memory"


class ChangeLogEntry(BaseModel):
    """Single change log entry"""
    id: str = Field(..., description="Change log entry ID")
    project_id: str = Field(..., description="Project ID")
    entity_type: EntityType = Field(..., description="Type of entity changed")
    entity_id: str = Field(..., description="ID of the changed entity")
    operation: OperationType = Field(..., description="Database operation performed")
    data: Optional[Dict[str, Any]] = Field(None, description="Full row data as JSON")
    timestamp: datetime = Field(..., description="When the change occurred")
    synced_at: Optional[datetime] = Field(None, description="When the change was synced to cloud")
    synced: bool = Field(False, description="Whether change has been synced")

    class Config:
        use_enum_values = True


class ChangeLogQuery(BaseModel):
    """Query parameters for fetching change logs"""
    project_id: str = Field(..., description="Project ID to query")
    entity_type: Optional[EntityType] = Field(None, description="Filter by entity type")
    since: Optional[datetime] = Field(None, description="Get changes after this timestamp")
    until: Optional[datetime] = Field(None, description="Get changes before this timestamp")
    synced_only: bool = Field(False, description="Only return synced changes")
    unsynced_only: bool = Field(False, description="Only return unsynced changes")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Pagination offset")

    class Config:
        use_enum_values = True


class ChangeLogResponse(BaseModel):
    """Response containing multiple change log entries"""
    changes: List[ChangeLogEntry] = Field(..., description="List of change log entries")
    total: int = Field(..., description="Total number of changes matching query")
    has_more: bool = Field(..., description="Whether there are more changes beyond limit")


class ChangeCountResponse(BaseModel):
    """Response for change count query"""
    project_id: str = Field(..., description="Project ID")
    total_changes: int = Field(..., description="Total number of changes")
    unsynced_changes: int = Field(..., description="Number of unsynced changes")
    by_entity_type: Dict[str, int] = Field(..., description="Change count by entity type")
    by_operation: Dict[str, int] = Field(..., description="Change count by operation type")
    oldest_change: Optional[datetime] = Field(None, description="Timestamp of oldest change")
    newest_change: Optional[datetime] = Field(None, description="Timestamp of newest change")


class MarkSyncedRequest(BaseModel):
    """Request to mark changes as synced"""
    change_ids: List[str] = Field(..., description="List of change log IDs to mark as synced")


class MarkSyncedResponse(BaseModel):
    """Response from marking changes as synced"""
    synced_count: int = Field(..., description="Number of changes marked as synced")
    timestamp: datetime = Field(..., description="Timestamp when changes were marked")


class CleanupRequest(BaseModel):
    """Request to cleanup old synced changes"""
    project_id: str = Field(..., description="Project ID to cleanup")
    older_than_days: int = Field(30, ge=1, le=365, description="Delete synced changes older than this many days")
    dry_run: bool = Field(False, description="Preview deletion without actually deleting")


class CleanupResponse(BaseModel):
    """Response from cleanup operation"""
    project_id: str = Field(..., description="Project ID")
    deleted_count: int = Field(..., description="Number of changes deleted")
    oldest_deleted: Optional[datetime] = Field(None, description="Oldest timestamp deleted")
    dry_run: bool = Field(..., description="Whether this was a dry run")
