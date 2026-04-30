"""
Pydantic schemas for sync history and audit logging
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class SyncDirection(str, Enum):
    """Sync direction options"""
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class SyncMode(str, Enum):
    """Sync mode options"""
    FULL = "full"
    INCREMENTAL = "incremental"
    SELECTIVE = "selective"


class SyncStatus(str, Enum):
    """Sync status options"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SyncHistoryCreate(BaseModel):
    """Schema for creating sync history entry"""
    project_id: UUID
    sync_id: UUID
    direction: SyncDirection
    mode: SyncMode = SyncMode.INCREMENTAL
    snapshot_id: Optional[UUID] = None

    class Config:
        use_enum_values = True


class SyncHistoryUpdate(BaseModel):
    """Schema for updating sync history entry"""
    status: Optional[SyncStatus] = None
    completed_at: Optional[datetime] = None
    records_synced: Optional[Dict[str, int]] = None
    bytes_transferred: Optional[int] = None
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    snapshot_id: Optional[UUID] = None

    @field_validator('bytes_transferred')
    @classmethod
    def validate_bytes(cls, v):
        """Validate bytes_transferred is non-negative"""
        if v is not None and v < 0:
            raise ValueError("bytes_transferred must be non-negative")
        return v

    class Config:
        use_enum_values = True


class SyncHistoryResponse(BaseModel):
    """Schema for sync history response"""
    id: UUID
    project_id: UUID
    sync_id: UUID
    direction: SyncDirection
    mode: SyncMode
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_synced: Dict[str, int] = Field(default_factory=dict)
    bytes_transferred: int = 0
    error_message: Optional[str] = None
    snapshot_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class SyncHistoryFilter(BaseModel):
    """Schema for filtering sync history"""
    direction: Optional[SyncDirection] = None
    mode: Optional[SyncMode] = None
    status: Optional[SyncStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    class Config:
        use_enum_values = True


class SyncHistoryListResponse(BaseModel):
    """Schema for paginated sync history list"""
    items: List[SyncHistoryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class SyncHistoryStats(BaseModel):
    """Schema for aggregated sync statistics"""
    project_id: UUID
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    rolled_back_syncs: int
    last_sync_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    total_records_synced: int
    total_bytes_transferred: int
    avg_sync_duration_seconds: Optional[float] = None
    avg_bytes_per_sync: Optional[float] = None

    # Per-direction breakdown
    push_syncs: int = 0
    pull_syncs: int = 0
    bidirectional_syncs: int = 0

    # Per-entity-type totals
    entity_type_totals: Dict[str, int] = Field(default_factory=dict)


class CleanupResult(BaseModel):
    """Schema for cleanup operation result"""
    deleted_count: int
    oldest_deleted: Optional[datetime] = None
    newest_deleted: Optional[datetime] = None
    bytes_freed: int = 0


class SyncHistoryDetailResponse(SyncHistoryResponse):
    """Extended schema with additional details for single record retrieval"""
    total_records_synced: int = 0

    @field_validator('total_records_synced', mode='before')
    @classmethod
    def calculate_total_records(cls, v, info):
        """Calculate total from records_synced dict"""
        records_synced = info.data.get('records_synced', {})
        if isinstance(records_synced, dict):
            return sum(records_synced.values())
        return 0


class SyncHistoryExportRequest(BaseModel):
    """Schema for exporting sync history"""
    project_id: UUID
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: str = Field(default="json", pattern="^(json|csv)$")
    include_errors: bool = True
