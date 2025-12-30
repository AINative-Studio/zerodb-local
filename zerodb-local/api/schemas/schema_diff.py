"""
Schema Diff Schemas
Pydantic models for schema comparison and migration planning
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ChangeType(str, Enum):
    """Types of schema changes"""
    TABLE_ADDED = "table_added"
    TABLE_REMOVED = "table_removed"
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_TYPE_CHANGED = "column_type_changed"
    COLUMN_NULLABLE_CHANGED = "column_nullable_changed"
    INDEX_ADDED = "index_added"
    INDEX_REMOVED = "index_removed"
    CONSTRAINT_ADDED = "constraint_added"
    CONSTRAINT_REMOVED = "constraint_removed"
    VECTOR_DIMENSION_CHANGED = "vector_dimension_changed"
    VECTOR_INDEX_ADDED = "vector_index_added"
    VECTOR_INDEX_REMOVED = "vector_index_removed"
    BUCKET_POLICY_CHANGED = "bucket_policy_changed"


class ChangeSeverity(str, Enum):
    """Severity levels for schema changes"""
    INFO = "info"           # Non-breaking, safe to apply
    WARNING = "warning"     # May require attention but safe
    CRITICAL = "critical"   # Breaking change, requires careful handling


class ColumnDefinition(BaseModel):
    """PostgreSQL column definition"""
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_table: Optional[str] = None
    foreign_key_column: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "user_id",
                "data_type": "uuid",
                "nullable": False,
                "is_foreign_key": True,
                "foreign_key_table": "users",
                "foreign_key_column": "id"
            }
        }


class IndexDefinition(BaseModel):
    """Database index definition"""
    name: str
    columns: List[str]
    unique: bool = False
    index_type: str = "btree"  # btree, hash, gin, gist

    class Config:
        json_schema_extra = {
            "example": {
                "name": "idx_users_email",
                "columns": ["email"],
                "unique": True,
                "index_type": "btree"
            }
        }


class ConstraintDefinition(BaseModel):
    """Database constraint definition"""
    name: str
    constraint_type: str  # primary_key, foreign_key, unique, check
    columns: List[str]
    referenced_table: Optional[str] = None
    referenced_columns: Optional[List[str]] = None
    check_expression: Optional[str] = None


class TableDefinition(BaseModel):
    """PostgreSQL table definition"""
    name: str
    columns: Dict[str, ColumnDefinition]
    indexes: List[IndexDefinition] = []
    constraints: List[ConstraintDefinition] = []
    row_count: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "users",
                "columns": {
                    "id": {
                        "name": "id",
                        "data_type": "uuid",
                        "nullable": False,
                        "is_primary_key": True
                    },
                    "email": {
                        "name": "email",
                        "data_type": "varchar(255)",
                        "nullable": False
                    }
                },
                "indexes": [
                    {
                        "name": "idx_users_email",
                        "columns": ["email"],
                        "unique": True
                    }
                ],
                "row_count": 1500
            }
        }


class VectorCollectionDefinition(BaseModel):
    """Qdrant vector collection definition"""
    name: str
    vector_dimension: int
    distance_metric: str = "cosine"  # cosine, euclidean, dot
    vector_count: Optional[int] = None
    index_type: Optional[str] = None  # hnsw, flat
    hnsw_config: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "embeddings",
                "vector_dimension": 1536,
                "distance_metric": "cosine",
                "vector_count": 5000,
                "index_type": "hnsw"
            }
        }


class BucketDefinition(BaseModel):
    """MinIO bucket definition"""
    name: str
    policy: Optional[str] = None  # public-read, private, custom
    versioning_enabled: bool = False
    object_count: Optional[int] = None
    total_size_bytes: Optional[int] = None


class SchemaDefinition(BaseModel):
    """Complete schema definition for local or cloud"""
    tables: Dict[str, TableDefinition] = {}
    vector_collections: Dict[str, VectorCollectionDefinition] = {}
    buckets: Dict[str, BucketDefinition] = {}
    snapshot_timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "tables": {
                    "users": {
                        "name": "users",
                        "columns": {
                            "id": {"name": "id", "data_type": "uuid", "nullable": False, "is_primary_key": True}
                        },
                        "row_count": 1500
                    }
                },
                "vector_collections": {
                    "embeddings": {
                        "name": "embeddings",
                        "vector_dimension": 1536,
                        "vector_count": 5000
                    }
                },
                "buckets": {
                    "uploads": {
                        "name": "uploads",
                        "policy": "private",
                        "object_count": 250
                    }
                },
                "snapshot_timestamp": "2025-12-29T12:00:00Z",
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            }
        }


class SchemaChange(BaseModel):
    """Single schema change detected"""
    change_type: ChangeType
    severity: ChangeSeverity
    entity_type: str  # "table", "vector_collection", "bucket"
    entity_name: str
    field_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "change_type": "column_added",
                "severity": "info",
                "entity_type": "table",
                "entity_name": "users",
                "field_name": "phone_number",
                "old_value": None,
                "new_value": {"data_type": "varchar(20)", "nullable": True},
                "description": "Added new column 'phone_number' to table 'users'"
            }
        }


class BreakingChange(BaseModel):
    """Breaking change that requires attention"""
    change_type: ChangeType
    severity: ChangeSeverity
    entity_type: str
    entity_name: str
    field_name: Optional[str] = None
    description: str
    impact: str  # Description of what will break
    mitigation: str  # Suggested mitigation strategy
    requires_manual_intervention: bool = False

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "change_type": "column_removed",
                "severity": "critical",
                "entity_type": "table",
                "entity_name": "users",
                "field_name": "legacy_id",
                "description": "Column 'legacy_id' removed from table 'users'",
                "impact": "Queries referencing 'legacy_id' will fail. Data will be lost.",
                "mitigation": "Export data before migration. Update all queries to remove references to 'legacy_id'.",
                "requires_manual_intervention": True
            }
        }


class SchemaDiff(BaseModel):
    """Complete schema difference analysis"""
    local_schema: SchemaDefinition
    cloud_schema: SchemaDefinition
    added_changes: List[SchemaChange] = []
    removed_changes: List[SchemaChange] = []
    modified_changes: List[SchemaChange] = []
    breaking_changes: List[BreakingChange] = []
    total_changes: int = 0
    has_breaking_changes: bool = False
    compared_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "local_schema": {"tables": {}, "vector_collections": {}, "buckets": {}},
                "cloud_schema": {"tables": {}, "vector_collections": {}, "buckets": {}},
                "added_changes": [
                    {
                        "change_type": "column_added",
                        "severity": "info",
                        "entity_type": "table",
                        "entity_name": "users",
                        "field_name": "phone_number",
                        "description": "Added new column 'phone_number'"
                    }
                ],
                "removed_changes": [],
                "modified_changes": [],
                "breaking_changes": [],
                "total_changes": 1,
                "has_breaking_changes": False,
                "compared_at": "2025-12-29T12:00:00Z"
            }
        }


class MigrationStep(BaseModel):
    """Single step in migration plan"""
    step_number: int
    operation: str  # SQL statement or API call
    description: str
    is_reversible: bool
    rollback_operation: Optional[str] = None
    estimated_duration_seconds: Optional[float] = None
    affected_entities: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "step_number": 1,
                "operation": "ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)",
                "description": "Add phone_number column to users table",
                "is_reversible": True,
                "rollback_operation": "ALTER TABLE users DROP COLUMN phone_number",
                "estimated_duration_seconds": 0.5,
                "affected_entities": ["users"]
            }
        }


class MigrationPlan(BaseModel):
    """Complete migration plan for applying schema changes"""
    plan_id: str
    project_id: str
    steps: List[MigrationStep]
    total_steps: int
    estimated_total_duration_seconds: float
    warnings: List[str] = []
    is_safe: bool  # True if no breaking changes
    requires_downtime: bool = False
    breaking_changes_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "migration_20251229_120000",
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "steps": [
                    {
                        "step_number": 1,
                        "operation": "ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)",
                        "description": "Add phone_number column",
                        "is_reversible": True,
                        "estimated_duration_seconds": 0.5
                    }
                ],
                "total_steps": 1,
                "estimated_total_duration_seconds": 0.5,
                "warnings": [],
                "is_safe": True,
                "requires_downtime": False,
                "breaking_changes_count": 0,
                "created_at": "2025-12-29T12:00:00Z"
            }
        }


class SchemaCompareRequest(BaseModel):
    """Request to compare schemas"""
    project_id: str = Field(..., description="Project ID to compare schemas for")
    cloud_schema: Optional[SchemaDefinition] = Field(
        None,
        description="Cloud schema (if not provided, will be fetched from cloud API)"
    )
    include_migration_plan: bool = Field(
        default=True,
        description="Whether to generate migration plan"
    )


class SchemaCompareResponse(BaseModel):
    """Response from schema comparison"""
    project_id: str
    diff: SchemaDiff
    migration_plan: Optional[MigrationPlan] = None
    comparison_summary: str

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "diff": {
                    "total_changes": 5,
                    "has_breaking_changes": False
                },
                "migration_plan": {
                    "plan_id": "migration_20251229_120000",
                    "total_steps": 3,
                    "is_safe": True
                },
                "comparison_summary": "Found 5 non-breaking changes. Migration is safe to apply."
            }
        }
