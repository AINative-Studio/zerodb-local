"""
Sync Schemas
Defines Pydantic models for sync operations
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SyncMode(str, Enum):
    """Sync mode types"""
    FULL = "full"
    INCREMENTAL = "incremental"
    SELECTIVE = "selective"


class SyncOperationType(str, Enum):
    """Sync operation types"""
    EXPORT = "export"
    UPLOAD = "upload"
    VERIFY = "verify"
    CLEANUP = "cleanup"


class SyncOperationAction(str, Enum):
    """Sync operation actions"""
    FULL_EXPORT = "full_export"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class SyncEntityType(str, Enum):
    """Sync entity types"""
    VECTORS = "vectors"
    TABLES = "tables"
    MEMORY = "memory"
    FILES = "files"
    EVENTS = "events"
    ALL = "all"


class SyncOperation(BaseModel):
    """Single sync operation in a plan"""
    type: SyncOperationType
    entity: SyncEntityType
    action: SyncOperationAction
    entity_id: Optional[str] = None
    estimated_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class SyncFilters(BaseModel):
    """Filters for selective sync"""
    entities: Optional[List[SyncEntityType]] = None
    entity_ids: Optional[List[str]] = None
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None

    class Config:
        use_enum_values = True


class SyncPlanRequest(BaseModel):
    """Request to generate a sync plan"""
    project_id: str = Field(..., description="Project ID to sync")
    mode: SyncMode = Field(
        default=SyncMode.FULL,
        description="Sync mode: full, incremental, or selective"
    )
    filters: Optional[SyncFilters] = Field(
        default=None,
        description="Optional filters for selective sync"
    )
    dry_run: bool = Field(
        default=False,
        description="If true, only preview the plan without executing"
    )

    class Config:
        use_enum_values = True


class SyncPlan(BaseModel):
    """Generated sync plan"""
    plan_id: str
    project_id: str
    mode: SyncMode
    operations: List[SyncOperation]
    estimated_duration_seconds: Optional[int] = None
    estimated_total_size: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class SyncExecuteRequest(BaseModel):
    """Request to execute a sync plan"""
    plan_id: Optional[str] = Field(
        default=None,
        description="Plan ID to execute (if not provided, generates new plan)"
    )
    project_id: str = Field(..., description="Project ID to sync")
    mode: SyncMode = Field(
        default=SyncMode.FULL,
        description="Sync mode (required if plan_id not provided)"
    )
    filters: Optional[SyncFilters] = None

    class Config:
        use_enum_values = True


class SyncProgressStatus(str, Enum):
    """Sync progress status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SyncProgress(BaseModel):
    """Sync progress tracking"""
    sync_id: str
    plan_id: str
    project_id: str
    status: SyncProgressStatus
    operations_total: int
    operations_completed: int
    current_operation: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    class Config:
        use_enum_values = True


class SyncRollbackRequest(BaseModel):
    """Request to rollback a sync"""
    sync_id: str = Field(..., description="Sync ID to rollback")
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for rollback"
    )


class SyncRollbackResponse(BaseModel):
    """Response from rollback operation"""
    sync_id: str
    status: str
    operations_rolled_back: int
    message: str


class SyncState(BaseModel):
    """Sync state for a project"""
    project_id: str
    last_sync_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    total_syncs: int = 0
    failed_syncs: int = 0
    last_sync_status: Optional[SyncProgressStatus] = None
    last_error: Optional[str] = None

    class Config:
        use_enum_values = True
