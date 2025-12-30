"""
Cloud Sync Schemas
Defines Pydantic models for cloud API integration and sync operations
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class CloudSyncDirection(str, Enum):
    """Cloud sync direction"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    BIDIRECTIONAL = "bidirectional"


class BundleStatus(str, Enum):
    """Bundle status in cloud"""
    PENDING = "pending"
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


# Authentication Schemas
class CloudAuthRequest(BaseModel):
    """Request to authenticate with ZeroDB Cloud API"""
    api_key: str = Field(
        ...,
        description="ZeroDB Cloud API key",
        min_length=32
    )

    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "zdb_sk_1234567890abcdef1234567890abcdef"
            }
        }


class CloudAuthResponse(BaseModel):
    """Response from cloud authentication"""
    auth_token: str = Field(..., description="Bearer token for API requests")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user_id: Optional[str] = Field(None, description="Authenticated user ID")
    organization_id: Optional[str] = Field(None, description="Organization ID")

    class Config:
        json_schema_extra = {
            "example": {
                "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "user_id": "usr_abc123",
                "organization_id": "org_xyz789"
            }
        }


# Bundle Upload Schemas
class BundleUploadRequest(BaseModel):
    """Request to upload a sync bundle to cloud"""
    project_id: str = Field(..., description="Project ID in cloud")
    bundle_data: Dict[str, Any] = Field(
        ...,
        description="Bundle data (vectors, tables, memory, files, events)"
    )
    bundle_name: Optional[str] = Field(
        None,
        description="Optional bundle name for identification"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata about the bundle"
    )
    compression: bool = Field(
        default=True,
        description="Enable compression for bundle data"
    )

    @validator("bundle_data")
    def validate_bundle_data(cls, v):
        """Ensure bundle_data has valid structure"""
        if not isinstance(v, dict):
            raise ValueError("bundle_data must be a dictionary")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj_abc123",
                "bundle_data": {
                    "vectors": [],
                    "tables": [],
                    "metadata": {}
                },
                "bundle_name": "local_sync_2025-12-29",
                "compression": True
            }
        }


class BundleUploadResponse(BaseModel):
    """Response from bundle upload"""
    upload_id: str = Field(..., description="Unique upload operation ID")
    bundle_id: str = Field(..., description="Bundle ID in cloud storage")
    status: BundleStatus = Field(..., description="Upload status")
    upload_url: Optional[str] = Field(
        None,
        description="Presigned URL for direct upload (if applicable)"
    )
    estimated_size_bytes: Optional[int] = Field(
        None,
        description="Estimated bundle size in bytes"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Upload creation timestamp"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "upload_id": "upl_xyz789",
                "bundle_id": "bnd_abc123",
                "status": "ready",
                "estimated_size_bytes": 1048576,
                "created_at": "2025-12-29T12:00:00Z"
            }
        }


# Bundle Download Schemas
class BundleDownloadRequest(BaseModel):
    """Request to download a bundle from cloud"""
    project_id: str = Field(..., description="Project ID in cloud")
    bundle_id: str = Field(..., description="Bundle ID to download")
    include_metadata: bool = Field(
        default=True,
        description="Include bundle metadata in response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj_abc123",
                "bundle_id": "bnd_xyz789",
                "include_metadata": True
            }
        }


class BundleDownloadResponse(BaseModel):
    """Response from bundle download"""
    bundle_id: str = Field(..., description="Bundle ID")
    bundle_data: Dict[str, Any] = Field(
        ...,
        description="Bundle data (vectors, tables, memory, files, events)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Bundle metadata"
    )
    created_at: datetime = Field(..., description="Bundle creation timestamp")
    size_bytes: Optional[int] = Field(None, description="Bundle size in bytes")
    checksum: Optional[str] = Field(None, description="Bundle checksum (SHA256)")

    class Config:
        json_schema_extra = {
            "example": {
                "bundle_id": "bnd_xyz789",
                "bundle_data": {
                    "vectors": [],
                    "tables": [],
                    "metadata": {}
                },
                "metadata": {
                    "source": "cloud",
                    "version": "1.0"
                },
                "created_at": "2025-12-29T12:00:00Z",
                "size_bytes": 1048576,
                "checksum": "sha256:abc123..."
            }
        }


# Cloud Sync Status Schemas
class BundleInfo(BaseModel):
    """Information about a cloud bundle"""
    bundle_id: str = Field(..., description="Bundle ID")
    bundle_name: Optional[str] = Field(None, description="Bundle name")
    status: BundleStatus = Field(..., description="Bundle status")
    created_at: datetime = Field(..., description="Creation timestamp")
    size_bytes: Optional[int] = Field(None, description="Bundle size")
    entity_counts: Optional[Dict[str, int]] = Field(
        default_factory=dict,
        description="Count of entities per type (vectors, tables, etc.)"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "bundle_id": "bnd_abc123",
                "bundle_name": "cloud_export_2025-12-29",
                "status": "ready",
                "created_at": "2025-12-29T12:00:00Z",
                "size_bytes": 2097152,
                "entity_counts": {
                    "vectors": 100,
                    "tables": 5,
                    "memory": 50
                }
            }
        }


class ConflictInfo(BaseModel):
    """Information about sync conflicts"""
    entity_type: str = Field(..., description="Type of entity with conflict")
    entity_id: str = Field(..., description="ID of conflicting entity")
    local_modified_at: datetime = Field(
        ...,
        description="Local modification timestamp"
    )
    cloud_modified_at: datetime = Field(
        ...,
        description="Cloud modification timestamp"
    )
    conflict_type: str = Field(
        ...,
        description="Type of conflict (update_conflict, delete_conflict, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "entity_type": "vectors",
                "entity_id": "vec_123",
                "local_modified_at": "2025-12-29T11:00:00Z",
                "cloud_modified_at": "2025-12-29T12:00:00Z",
                "conflict_type": "update_conflict"
            }
        }


class CloudSyncStatus(BaseModel):
    """Cloud sync status for a project"""
    project_id: str = Field(..., description="Project ID")
    is_authenticated: bool = Field(
        default=False,
        description="Whether authenticated with cloud"
    )
    last_sync_at: Optional[datetime] = Field(
        None,
        description="Last successful sync timestamp"
    )
    last_upload_at: Optional[datetime] = Field(
        None,
        description="Last upload timestamp"
    )
    last_download_at: Optional[datetime] = Field(
        None,
        description="Last download timestamp"
    )
    available_bundles: List[BundleInfo] = Field(
        default_factory=list,
        description="List of available bundles in cloud"
    )
    pending_conflicts: List[ConflictInfo] = Field(
        default_factory=list,
        description="List of pending sync conflicts"
    )
    sync_direction: CloudSyncDirection = Field(
        default=CloudSyncDirection.BIDIRECTIONAL,
        description="Configured sync direction"
    )
    auto_sync_enabled: bool = Field(
        default=False,
        description="Whether auto-sync is enabled"
    )
    total_bundles: int = Field(default=0, description="Total bundle count")
    storage_used_bytes: Optional[int] = Field(
        None,
        description="Cloud storage used in bytes"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "project_id": "proj_abc123",
                "is_authenticated": True,
                "last_sync_at": "2025-12-29T10:00:00Z",
                "last_upload_at": "2025-12-29T09:00:00Z",
                "last_download_at": "2025-12-29T08:00:00Z",
                "available_bundles": [],
                "pending_conflicts": [],
                "sync_direction": "bidirectional",
                "auto_sync_enabled": False,
                "total_bundles": 5,
                "storage_used_bytes": 10485760
            }
        }


# List Bundles Schemas
class ListBundlesRequest(BaseModel):
    """Request to list available bundles"""
    project_id: str = Field(..., description="Project ID")
    status_filter: Optional[BundleStatus] = Field(
        None,
        description="Filter by bundle status"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of bundles to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )

    class Config:
        use_enum_values = True


class ListBundlesResponse(BaseModel):
    """Response with list of bundles"""
    bundles: List[BundleInfo] = Field(..., description="List of bundles")
    total: int = Field(..., description="Total bundle count")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")

    class Config:
        json_schema_extra = {
            "example": {
                "bundles": [],
                "total": 5,
                "limit": 50,
                "offset": 0
            }
        }


# Error Response Schema
class CloudAPIError(BaseModel):
    """Error response from cloud API"""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    status_code: int = Field(..., description="HTTP status code")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "authentication_failed",
                "message": "Invalid API key provided",
                "status_code": 401
            }
        }
