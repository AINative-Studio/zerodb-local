"""
Export Schemas
Pydantic models for export operations
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class ExportType(str, Enum):
    """Export type enumeration"""
    FULL = "full"
    INCREMENTAL = "incremental"
    SELECTIVE = "selective"


class ExportStatus(str, Enum):
    """Export status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportCreate(BaseModel):
    """Schema for creating an export"""
    export_type: ExportType = Field(
        ...,
        description="Type of export to create"
    )
    entity_types: Optional[List[str]] = Field(
        None,
        description="Entity types for selective export (e.g., ['tables', 'vectors'])"
    )
    since_timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp for incremental export (only export changes after this)"
    )
    compress: bool = Field(
        default=True,
        description="Whether to compress the export bundle with gzip"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "export_type": "full",
                "compress": True
            }
        }


class RecordCounts(BaseModel):
    """Record counts for exported entities"""
    tables: int = Field(default=0, description="Number of tables exported")
    table_rows: int = Field(default=0, description="Total rows across all tables")
    vectors: int = Field(default=0, description="Number of vectors exported")
    memory: int = Field(default=0, description="Number of memory records exported")
    events: int = Field(default=0, description="Number of events exported")
    files: int = Field(default=0, description="Number of file metadata records exported")


class ExportMetadata(BaseModel):
    """Metadata about an export bundle"""
    export_id: UUID
    project_id: UUID
    export_type: ExportType
    timestamp: datetime
    record_counts: RecordCounts
    file_size_bytes: int
    compressed: bool
    entity_types: Optional[List[str]] = None
    since_timestamp: Optional[datetime] = None
    schema_version: str = "1.0.0"


# Individual entity export schemas
class VectorExport(BaseModel):
    """Single vector export record"""
    vector_id: str
    namespace: str
    document: str
    metadata: Dict[str, Any]
    embedding: List[float]
    created_at: datetime
    updated_at: datetime


class TableExport(BaseModel):
    """Single table export record"""
    table_id: str
    table_name: str
    schema: Dict[str, Any]
    description: Optional[str] = None
    rows: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class FileExport(BaseModel):
    """Single file export record"""
    file_id: str
    file_name: str
    content_type: str
    folder: Optional[str] = None
    metadata: Dict[str, Any]
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    # Note: actual file data stored separately in bundle


class EventExport(BaseModel):
    """Single event export record"""
    event_id: str
    event_type: str
    event_data: Dict[str, Any]
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime


class MemoryExport(BaseModel):
    """Single memory export record"""
    memory_id: str
    agent_id: str
    session_id: str
    role: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: datetime


class BundleManifest(BaseModel):
    """Manifest file for export bundle"""
    bundle_id: UUID
    project_id: UUID
    export_type: ExportType
    created_at: datetime
    schema_version: str = "1.0.0"
    entity_counts: RecordCounts
    files: List[str] = Field(
        description="List of files in bundle (relative paths)"
    )
    since_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class ExportBundle(BaseModel):
    """Complete export bundle structure"""
    manifest: BundleManifest
    schema: Optional[Dict[str, Any]] = None
    vectors: List[VectorExport] = []
    tables: List[TableExport] = []
    files: List[FileExport] = []
    events: List[EventExport] = []
    memory: List[MemoryExport] = []


class ExportPreview(BaseModel):
    """Preview of what would be exported"""
    project_id: UUID
    export_type: ExportType
    estimated_counts: RecordCounts
    estimated_size_bytes: int
    since_timestamp: Optional[datetime] = None
    entity_types: Optional[List[str]] = None


class ExportResponse(BaseModel):
    """Schema for export creation response"""
    export_id: UUID
    project_id: UUID
    status: ExportStatus
    export_type: ExportType
    bundle_path: str
    metadata: ExportMetadata
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "export_id": "e1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "completed",
                "export_type": "full",
                "bundle_path": "/exports/export_e1b2c3d4.json.gz",
                "metadata": {
                    "export_id": "e1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "export_type": "full",
                    "timestamp": "2025-12-28T12:00:00Z",
                    "record_counts": {
                        "tables": 5,
                        "table_rows": 1200,
                        "vectors": 500,
                        "memory": 100,
                        "events": 50,
                        "files": 10
                    },
                    "file_size_bytes": 5242880,
                    "compressed": True,
                    "schema_version": "1.0.0"
                },
                "created_at": "2025-12-28T12:00:00Z",
                "updated_at": "2025-12-28T12:00:00Z"
            }
        }


class ExportStatusResponse(BaseModel):
    """Schema for export status check"""
    export_id: UUID
    status: ExportStatus
    progress_percentage: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Progress percentage (0-100)"
    )
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ExportListResponse(BaseModel):
    """Schema for listing exports"""
    exports: List[ExportStatusResponse]
    total: int
