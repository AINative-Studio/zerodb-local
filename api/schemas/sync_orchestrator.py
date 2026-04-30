"""
Sync Orchestrator Schemas
Pydantic models for sync orchestration operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class SyncDirection(str, Enum):
    """Sync direction enumeration"""
    PUSH = "push"  # Local → Cloud
    PULL = "pull"  # Cloud → Local
    BIDIRECTIONAL = "bidirectional"  # Both directions


class SyncStepType(str, Enum):
    """Sync step type enumeration"""
    SCHEMA_VALIDATION = "schema_validation"
    EXPORT_CREATION = "export_creation"
    DATA_UPLOAD = "data_upload"
    DATA_DOWNLOAD = "data_download"
    IMPORT_DATA = "import_data"
    UPDATE_WATERMARKS = "update_watermarks"
    MARK_SYNCED = "mark_synced"


class EntityType(str, Enum):
    """Entity type enumeration"""
    TABLES = "tables"
    VECTORS = "vectors"
    MEMORY = "memory"
    EVENTS = "events"
    FILES = "files"
    SCHEMA = "schema"


class OperationType(str, Enum):
    """Operation type enumeration"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SCHEMA_CHANGE = "schema_change"


class SyncStatus(str, Enum):
    """Sync status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ConflictResolutionStrategy(str, Enum):
    """Conflict resolution strategy"""
    LOCAL_WINS = "local_wins"
    CLOUD_WINS = "cloud_wins"
    MANUAL = "manual"
    NEWEST_WINS = "newest_wins"


class SyncStep(BaseModel):
    """Individual step in sync plan"""
    step_number: int = Field(..., description="Step sequence number")
    step_type: SyncStepType = Field(..., description="Type of sync step")
    entity_type: Optional[EntityType] = Field(None, description="Entity type affected")
    operation: Optional[OperationType] = Field(None, description="Operation to perform")
    data_count: int = Field(default=0, description="Number of records/entities affected")
    estimated_duration_seconds: Optional[float] = Field(
        None,
        description="Estimated time to complete step"
    )
    description: str = Field(..., description="Human-readable step description")


class EntityCount(BaseModel):
    """Count of entities to sync"""
    tables: int = Field(default=0, description="Number of tables")
    table_rows: int = Field(default=0, description="Total table rows")
    vectors: int = Field(default=0, description="Number of vectors")
    memory: int = Field(default=0, description="Number of memory records")
    events: int = Field(default=0, description="Number of events")
    files: int = Field(default=0, description="Number of file metadata records")


class SchemaChangeInfo(BaseModel):
    """Information about schema changes"""
    has_changes: bool = Field(..., description="Whether schema changes exist")
    is_breaking: bool = Field(..., description="Whether changes are breaking")
    changes: List[str] = Field(
        default_factory=list,
        description="List of schema changes detected"
    )
    migration_required: bool = Field(
        default=False,
        description="Whether migration is required"
    )


class ConflictInfo(BaseModel):
    """Information about sync conflicts"""
    has_conflicts: bool = Field(..., description="Whether conflicts exist")
    conflict_count: int = Field(default=0, description="Number of conflicts")
    conflicts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed conflict information"
    )
    resolution_strategy: Optional[ConflictResolutionStrategy] = Field(
        None,
        description="Recommended resolution strategy"
    )


class SyncWarning(BaseModel):
    """Warning in sync plan"""
    severity: str = Field(..., description="Warning severity (low/medium/high)")
    message: str = Field(..., description="Warning message")
    category: str = Field(..., description="Warning category")


class SyncPlan(BaseModel):
    """Complete sync plan"""
    plan_id: UUID = Field(..., description="Unique plan identifier")
    project_id: UUID = Field(..., description="Project UUID")
    direction: SyncDirection = Field(..., description="Sync direction")
    created_at: datetime = Field(..., description="Plan creation timestamp")

    # Plan details
    steps: List[SyncStep] = Field(..., description="Ordered list of sync steps")
    entity_counts: EntityCount = Field(..., description="Entity counts to sync")
    estimated_duration_seconds: float = Field(
        ...,
        description="Total estimated duration"
    )
    estimated_data_size_bytes: int = Field(
        ...,
        description="Estimated data size to transfer"
    )

    # Schema and conflicts
    schema_changes: SchemaChangeInfo = Field(
        ...,
        description="Schema change information"
    )
    conflicts: ConflictInfo = Field(
        ...,
        description="Conflict information"
    )

    # Warnings and risks
    warnings: List[SyncWarning] = Field(
        default_factory=list,
        description="Warnings about sync operation"
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether manual approval required"
    )
    can_rollback: bool = Field(
        default=True,
        description="Whether sync can be rolled back"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "project_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "direction": "push",
                "created_at": "2025-12-29T10:00:00Z",
                "steps": [
                    {
                        "step_number": 1,
                        "step_type": "schema_validation",
                        "description": "Validate schema compatibility",
                        "estimated_duration_seconds": 2.0
                    },
                    {
                        "step_number": 2,
                        "step_type": "export_creation",
                        "entity_type": "tables",
                        "operation": "create",
                        "data_count": 500,
                        "description": "Export table data to bundle",
                        "estimated_duration_seconds": 5.0
                    }
                ],
                "entity_counts": {
                    "tables": 5,
                    "table_rows": 500,
                    "vectors": 100,
                    "memory": 50,
                    "events": 20,
                    "files": 10
                },
                "estimated_duration_seconds": 15.0,
                "estimated_data_size_bytes": 5242880,
                "schema_changes": {
                    "has_changes": False,
                    "is_breaking": False,
                    "changes": [],
                    "migration_required": False
                },
                "conflicts": {
                    "has_conflicts": False,
                    "conflict_count": 0,
                    "conflicts": []
                },
                "warnings": [],
                "requires_approval": False,
                "can_rollback": True
            }
        }


class SyncStepResult(BaseModel):
    """Result of individual sync step"""
    step_number: int
    step_type: SyncStepType
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    records_processed: int = Field(default=0, description="Number of records processed")


class SyncResult(BaseModel):
    """Result of sync execution"""
    sync_id: UUID = Field(..., description="Unique sync execution identifier")
    project_id: UUID = Field(..., description="Project UUID")
    plan_id: UUID = Field(..., description="Plan that was executed")
    direction: SyncDirection = Field(..., description="Sync direction")
    status: SyncStatus = Field(..., description="Overall sync status")

    # Execution details
    started_at: datetime = Field(..., description="Sync start time")
    completed_at: Optional[datetime] = Field(None, description="Sync completion time")
    duration_seconds: Optional[float] = Field(None, description="Total duration")

    # Step results
    steps_completed: List[SyncStepResult] = Field(
        default_factory=list,
        description="Results of completed steps"
    )
    total_steps: int = Field(..., description="Total number of steps")
    successful_steps: int = Field(default=0, description="Number of successful steps")
    failed_steps: int = Field(default=0, description="Number of failed steps")

    # Data processing
    records_synced: int = Field(default=0, description="Total records synced")
    bytes_transferred: int = Field(default=0, description="Total bytes transferred")

    # Error handling
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages from failed steps"
    )
    rollback_available: bool = Field(
        default=True,
        description="Whether rollback is available"
    )
    snapshot_id: Optional[UUID] = Field(
        None,
        description="Snapshot ID for rollback"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sync_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "project_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "plan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "direction": "push",
                "status": "completed",
                "started_at": "2025-12-29T10:05:00Z",
                "completed_at": "2025-12-29T10:05:15Z",
                "duration_seconds": 15.3,
                "steps_completed": [
                    {
                        "step_number": 1,
                        "step_type": "schema_validation",
                        "status": "completed",
                        "started_at": "2025-12-29T10:05:00Z",
                        "completed_at": "2025-12-29T10:05:02Z",
                        "duration_seconds": 2.1,
                        "records_processed": 0
                    }
                ],
                "total_steps": 5,
                "successful_steps": 5,
                "failed_steps": 0,
                "records_synced": 500,
                "bytes_transferred": 5242880,
                "errors": [],
                "rollback_available": True,
                "snapshot_id": "d4e5f6a7-b8c9-0123-def0-1234567890ab"
            }
        }


class ValidationResult(BaseModel):
    """Result of sync plan validation"""
    is_valid: bool = Field(..., description="Whether plan is valid")
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors"
    )
    warnings: List[SyncWarning] = Field(
        default_factory=list,
        description="Validation warnings"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for improvement"
    )


class RollbackResult(BaseModel):
    """Result of sync rollback"""
    success: bool = Field(..., description="Whether rollback succeeded")
    sync_id: UUID = Field(..., description="Sync that was rolled back")
    snapshot_id: UUID = Field(..., description="Snapshot restored")
    restored_at: datetime = Field(..., description="Rollback completion time")
    restored_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="State that was restored"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Errors during rollback"
    )


class SyncStatusResponse(BaseModel):
    """Current sync status for a project"""
    project_id: UUID
    last_sync_at: Optional[datetime] = Field(
        None,
        description="Last successful sync timestamp"
    )
    last_sync_direction: Optional[SyncDirection] = Field(
        None,
        description="Direction of last sync"
    )
    sync_in_progress: bool = Field(
        default=False,
        description="Whether sync currently running"
    )
    current_sync_id: Optional[UUID] = Field(
        None,
        description="ID of running sync"
    )
    pending_changes_count: int = Field(
        default=0,
        description="Number of pending changes"
    )
    entity_sync_states: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Sync state per entity type"
    )


class SyncPlanRequest(BaseModel):
    """Request to create sync plan"""
    direction: SyncDirection = Field(..., description="Sync direction")
    entity_types: Optional[List[EntityType]] = Field(
        None,
        description="Specific entity types to sync (None = all)"
    )
    conflict_strategy: ConflictResolutionStrategy = Field(
        default=ConflictResolutionStrategy.NEWEST_WINS,
        description="Strategy for resolving conflicts"
    )
    include_schema: bool = Field(
        default=True,
        description="Whether to include schema sync"
    )


class SyncExecuteRequest(BaseModel):
    """Request to execute sync"""
    plan_id: UUID = Field(..., description="Plan to execute")
    approved: bool = Field(
        default=False,
        description="Manual approval if required"
    )
    conflict_resolutions: Optional[Dict[str, str]] = Field(
        None,
        description="Manual conflict resolutions"
    )
