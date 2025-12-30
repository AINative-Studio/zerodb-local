"""
Conflict Resolution Schemas
Pydantic models for conflict detection and resolution
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class ConflictType(str, Enum):
    """Type of conflict detected"""
    CONCURRENT_UPDATE = "concurrent_update"  # Both local and cloud modified same entity
    DELETE_CONFLICT = "delete_conflict"  # One deleted, other modified
    SCHEMA_CONFLICT = "schema_conflict"  # Schema changed in one environment
    VERSION_CONFLICT = "version_conflict"  # Different versions of same data


class ConflictResolutionStrategy(str, Enum):
    """Strategy for resolving conflicts"""
    LOCAL_WINS = "local_wins"  # Local changes override cloud
    CLOUD_WINS = "cloud_wins"  # Cloud changes override local
    NEWEST_WINS = "newest_wins"  # Most recent timestamp wins
    MANUAL = "manual"  # Interactive user resolution


class EntityVersion(BaseModel):
    """Represents a version of an entity (local or cloud)"""
    data: Dict[str, Any] = Field(..., description="Entity data")
    timestamp: datetime = Field(..., description="Last modified timestamp")
    hash: str = Field(..., description="Data hash for change detection")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class Conflict(BaseModel):
    """Represents a detected conflict"""
    conflict_id: UUID = Field(..., description="Unique conflict ID")
    project_id: UUID = Field(..., description="Project ID")
    entity_type: str = Field(..., description="Type of entity (vector, table_row, memory, event, file)")
    entity_id: str = Field(..., description="Entity identifier")
    conflict_type: ConflictType = Field(..., description="Type of conflict")

    local_version: EntityVersion = Field(..., description="Local version of entity")
    cloud_version: EntityVersion = Field(..., description="Cloud version of entity")

    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When conflict was detected")
    is_breaking: bool = Field(default=False, description="Whether conflict is breaking (data loss risk)")

    suggested_strategy: Optional[ConflictResolutionStrategy] = Field(
        None,
        description="AI-suggested resolution strategy"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conflict_id": "123e4567-e89b-12d3-a456-426614174000",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_type": "vector",
                "entity_id": "vec_12345",
                "conflict_type": "concurrent_update",
                "local_version": {
                    "data": {"embedding": [0.1, 0.2], "metadata": {"user": "alice"}},
                    "timestamp": "2025-12-29T10:00:00Z",
                    "hash": "abc123"
                },
                "cloud_version": {
                    "data": {"embedding": [0.1, 0.2], "metadata": {"user": "bob"}},
                    "timestamp": "2025-12-29T10:05:00Z",
                    "hash": "def456"
                },
                "detected_at": "2025-12-29T10:10:00Z",
                "is_breaking": False,
                "suggested_strategy": "newest_wins"
            }
        }


class ConflictResolutionRequest(BaseModel):
    """Request to resolve a conflict"""
    conflict_id: UUID = Field(..., description="Conflict to resolve")
    strategy: ConflictResolutionStrategy = Field(..., description="Resolution strategy to use")
    manual_choice: Optional[str] = Field(
        None,
        description="For manual strategy: 'local' or 'cloud'"
    )
    notes: Optional[str] = Field(None, description="Optional resolution notes")

    class Config:
        json_schema_extra = {
            "example": {
                "conflict_id": "123e4567-e89b-12d3-a456-426614174000",
                "strategy": "newest_wins",
                "notes": "Auto-resolved using timestamp"
            }
        }


class ConflictResolutionResponse(BaseModel):
    """Response from conflict resolution"""
    conflict_id: UUID = Field(..., description="Resolved conflict ID")
    resolved_data: Dict[str, Any] = Field(..., description="Final resolved data")
    strategy_used: ConflictResolutionStrategy = Field(..., description="Strategy that was used")
    chosen_version: str = Field(..., description="Which version was chosen: 'local', 'cloud', or 'merged'")
    resolved_at: datetime = Field(default_factory=datetime.utcnow, description="When resolved")

    class Config:
        json_schema_extra = {
            "example": {
                "conflict_id": "123e4567-e89b-12d3-a456-426614174000",
                "resolved_data": {"embedding": [0.1, 0.2], "metadata": {"user": "bob"}},
                "strategy_used": "newest_wins",
                "chosen_version": "cloud",
                "resolved_at": "2025-12-29T10:15:00Z"
            }
        }


class ConflictSummary(BaseModel):
    """Summary of conflicts for a project"""
    project_id: UUID = Field(..., description="Project ID")
    total_conflicts: int = Field(..., description="Total number of conflicts")
    unresolved_conflicts: int = Field(..., description="Number of unresolved conflicts")
    resolved_conflicts: int = Field(..., description="Number of resolved conflicts")

    by_entity_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Conflict count by entity type"
    )
    by_conflict_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Conflict count by conflict type"
    )
    by_strategy: Dict[str, int] = Field(
        default_factory=dict,
        description="Resolution count by strategy used"
    )

    breaking_conflicts: int = Field(default=0, description="Number of breaking conflicts")
    requires_manual_resolution: int = Field(default=0, description="Conflicts requiring manual resolution")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_conflicts": 15,
                "unresolved_conflicts": 3,
                "resolved_conflicts": 12,
                "by_entity_type": {
                    "vector": 8,
                    "table_row": 5,
                    "memory": 2
                },
                "by_conflict_type": {
                    "concurrent_update": 12,
                    "delete_conflict": 3
                },
                "by_strategy": {
                    "newest_wins": 8,
                    "local_wins": 3,
                    "cloud_wins": 1
                },
                "breaking_conflicts": 2,
                "requires_manual_resolution": 3
            }
        }


class AutoResolveRequest(BaseModel):
    """Request to auto-resolve all conflicts with a strategy"""
    project_id: UUID = Field(..., description="Project ID")
    strategy: ConflictResolutionStrategy = Field(..., description="Strategy to apply to all conflicts")
    exclude_breaking: bool = Field(
        default=True,
        description="Exclude breaking conflicts from auto-resolution"
    )
    dry_run: bool = Field(
        default=False,
        description="Preview resolutions without applying"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "strategy": "newest_wins",
                "exclude_breaking": True,
                "dry_run": False
            }
        }


class AutoResolveResponse(BaseModel):
    """Response from auto-resolve operation"""
    project_id: UUID = Field(..., description="Project ID")
    strategy_used: ConflictResolutionStrategy = Field(..., description="Strategy applied")
    total_conflicts: int = Field(..., description="Total conflicts found")
    resolved_count: int = Field(..., description="Number of conflicts resolved")
    skipped_count: int = Field(..., description="Number of conflicts skipped")
    failed_count: int = Field(..., description="Number of resolution failures")

    resolutions: List[ConflictResolutionResponse] = Field(
        default_factory=list,
        description="Individual resolution results"
    )
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "strategy_used": "newest_wins",
                "total_conflicts": 15,
                "resolved_count": 12,
                "skipped_count": 3,
                "failed_count": 0,
                "resolutions": [],
                "errors": []
            }
        }


class ManualResolutionPrompt(BaseModel):
    """Prompt for manual conflict resolution"""
    conflict: Conflict = Field(..., description="Conflict requiring manual resolution")
    options: List[str] = Field(..., description="Available resolution options: ['local', 'cloud', 'custom']")
    recommendation: Optional[str] = Field(None, description="AI recommendation")
    impact_analysis: Optional[str] = Field(None, description="Analysis of choosing each option")

    class Config:
        json_schema_extra = {
            "example": {
                "conflict": {
                    "conflict_id": "123e4567-e89b-12d3-a456-426614174000",
                    "entity_type": "vector",
                    "entity_id": "vec_12345",
                    "conflict_type": "concurrent_update"
                },
                "options": ["local", "cloud", "custom"],
                "recommendation": "cloud",
                "impact_analysis": "Choosing cloud version preserves recent metadata update by Bob"
            }
        }
