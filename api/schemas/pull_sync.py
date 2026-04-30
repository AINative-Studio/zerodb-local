"""
Pull Sync Schemas
Pydantic models for pull sync operations (cloud → local)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class PullEntityType(str, Enum):
    """Entity types that can be pulled from cloud"""
    TABLES = "tables"
    VECTORS = "vectors"
    MEMORY = "memory"
    EVENTS = "events"
    FILES = "files"
    ALL = "all"


class ImportStatus(str, Enum):
    """Import operation status"""
    PENDING = "pending"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ConflictAction(str, Enum):
    """Action to take on conflict during import"""
    SKIP = "skip"  # Skip conflicting record
    OVERWRITE = "overwrite"  # Overwrite local with cloud
    MERGE = "merge"  # Merge metadata/data
    FAIL = "fail"  # Fail import on conflict


class SchemaCompatibility(str, Enum):
    """Schema compatibility level"""
    COMPATIBLE = "compatible"  # Fully compatible
    COMPATIBLE_WITH_MIGRATION = "compatible_with_migration"  # Requires migration
    BREAKING = "breaking"  # Breaking changes detected
    UNKNOWN = "unknown"  # Cannot determine


class PullRequest(BaseModel):
    """Request to pull data from cloud"""
    project_id: UUID = Field(..., description="Project UUID")
    entity_types: Optional[List[PullEntityType]] = Field(
        None,
        description="Specific entity types to pull (None = all)"
    )
    since_timestamp: Optional[datetime] = Field(
        None,
        description="Only pull changes after this timestamp (incremental)"
    )
    conflict_action: ConflictAction = Field(
        default=ConflictAction.OVERWRITE,
        description="How to handle conflicts"
    )
    validate_schema: bool = Field(
        default=True,
        description="Validate schema compatibility before import"
    )
    dry_run: bool = Field(
        default=False,
        description="Preview changes without applying"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "entity_types": ["vectors", "tables"],
                "since_timestamp": "2025-12-29T00:00:00Z",
                "conflict_action": "overwrite",
                "validate_schema": True,
                "dry_run": False
            }
        }


class ImportedCounts(BaseModel):
    """Counts of entities imported"""
    tables_created: int = Field(default=0, description="New tables created")
    tables_updated: int = Field(default=0, description="Existing tables updated")
    table_rows_inserted: int = Field(default=0, description="Table rows inserted")
    table_rows_updated: int = Field(default=0, description="Table rows updated")
    vectors_upserted: int = Field(default=0, description="Vectors upserted")
    memory_inserted: int = Field(default=0, description="Memory records inserted")
    events_published: int = Field(default=0, description="Events published")
    files_uploaded: int = Field(default=0, description="Files uploaded")
    total_imported: int = Field(default=0, description="Total records imported")


class ConflictDetail(BaseModel):
    """Details of a single conflict"""
    entity_type: str = Field(..., description="Type of entity")
    entity_id: str = Field(..., description="Entity identifier")
    conflict_type: str = Field(..., description="Type of conflict (timestamp, schema, data)")
    local_value: Optional[Any] = Field(None, description="Local value")
    cloud_value: Optional[Any] = Field(None, description="Cloud value")
    resolution: Optional[str] = Field(None, description="How conflict was resolved")
    timestamp: datetime = Field(..., description="When conflict detected")


class SchemaBreakingChange(BaseModel):
    """Details of a breaking schema change"""
    table_name: str
    change_type: str  # "column_removed", "type_changed", "constraint_changed"
    description: str
    affected_columns: List[str] = []
    migration_sql: Optional[str] = None


class ImportValidation(BaseModel):
    """Validation result for import bundle"""
    is_valid: bool = Field(..., description="Whether bundle is valid for import")
    schema_compatible: bool = Field(
        ...,
        description="Whether schema is compatible"
    )
    compatibility_level: SchemaCompatibility = Field(
        ...,
        description="Level of schema compatibility"
    )
    breaking_changes: List[SchemaBreakingChange] = Field(
        default_factory=list,
        description="Breaking schema changes detected"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-blocking warnings"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Validation errors"
    )
    estimated_conflicts: int = Field(
        default=0,
        description="Estimated number of conflicts"
    )
    can_auto_migrate: bool = Field(
        default=False,
        description="Whether migration can be automated"
    )


class PullResult(BaseModel):
    """Result of pull sync operation"""
    pull_id: UUID = Field(..., description="Unique pull operation ID")
    project_id: UUID = Field(..., description="Project UUID")
    status: ImportStatus = Field(..., description="Pull operation status")

    # Execution details
    started_at: datetime = Field(..., description="Pull start time")
    completed_at: Optional[datetime] = Field(None, description="Pull completion time")
    duration_seconds: Optional[float] = Field(None, description="Total duration")

    # Import details
    bundle_id: Optional[UUID] = Field(None, description="Cloud bundle ID pulled")
    bundle_size_bytes: int = Field(default=0, description="Bundle size downloaded")
    imported_counts: ImportedCounts = Field(
        default_factory=ImportedCounts,
        description="Counts of imported entities"
    )

    # Conflicts
    conflicts: List[ConflictDetail] = Field(
        default_factory=list,
        description="Conflicts encountered during import"
    )
    conflicts_resolved: int = Field(
        default=0,
        description="Number of conflicts resolved"
    )
    conflicts_skipped: int = Field(
        default=0,
        description="Number of conflicts skipped"
    )

    # Errors and rollback
    errors: List[str] = Field(
        default_factory=list,
        description="Errors encountered"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical warnings"
    )
    rolled_back: bool = Field(
        default=False,
        description="Whether changes were rolled back"
    )
    snapshot_id: Optional[UUID] = Field(
        None,
        description="Snapshot ID for rollback"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "pull_id": "f1e2d3c4-b5a6-7890-cdef-123456789abc",
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "completed",
                "started_at": "2025-12-29T10:00:00Z",
                "completed_at": "2025-12-29T10:05:00Z",
                "duration_seconds": 300.5,
                "bundle_id": "b1c2d3e4-f5a6-7890-bcde-f12345678901",
                "bundle_size_bytes": 5242880,
                "imported_counts": {
                    "tables_created": 2,
                    "tables_updated": 3,
                    "table_rows_inserted": 500,
                    "table_rows_updated": 100,
                    "vectors_upserted": 250,
                    "memory_inserted": 50,
                    "events_published": 25,
                    "files_uploaded": 10,
                    "total_imported": 940
                },
                "conflicts": [],
                "conflicts_resolved": 5,
                "conflicts_skipped": 0,
                "errors": [],
                "warnings": ["Table 'users' schema mismatch - auto-migrated"],
                "rolled_back": False,
                "snapshot_id": "c2d3e4f5-a6b7-8901-cdef-234567890abc"
            }
        }


class PullPreview(BaseModel):
    """Preview of what would be pulled from cloud"""
    project_id: UUID
    cloud_bundle_id: Optional[UUID] = None
    cloud_last_modified: Optional[datetime] = None
    estimated_counts: ImportedCounts
    estimated_size_bytes: int
    validation: ImportValidation
    estimated_conflicts: int
    estimated_duration_seconds: float
    requires_migration: bool
    safe_to_pull: bool

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "cloud_bundle_id": "b1c2d3e4-f5a6-7890-bcde-f12345678901",
                "cloud_last_modified": "2025-12-29T09:00:00Z",
                "estimated_counts": {
                    "tables_created": 2,
                    "table_rows_inserted": 500,
                    "vectors_upserted": 250,
                    "total_imported": 752
                },
                "estimated_size_bytes": 5242880,
                "validation": {
                    "is_valid": True,
                    "schema_compatible": True,
                    "compatibility_level": "compatible",
                    "breaking_changes": [],
                    "warnings": [],
                    "errors": [],
                    "estimated_conflicts": 5,
                    "can_auto_migrate": True
                },
                "estimated_conflicts": 5,
                "estimated_duration_seconds": 300.0,
                "requires_migration": False,
                "safe_to_pull": True
            }
        }


class BundleImportRequest(BaseModel):
    """Request to import a downloaded bundle"""
    project_id: UUID
    bundle_data: Dict[str, Any]
    conflict_action: ConflictAction = ConflictAction.OVERWRITE
    validate_first: bool = True
    create_snapshot: bool = True


class BundleImportResult(BaseModel):
    """Result of bundle import"""
    import_id: UUID
    project_id: UUID
    status: ImportStatus
    validation: Optional[ImportValidation] = None
    imported_counts: ImportedCounts
    conflicts: List[ConflictDetail]
    errors: List[str]
    snapshot_id: Optional[UUID] = None
    duration_seconds: float
