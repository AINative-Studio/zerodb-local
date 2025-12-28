"""
Files Router
Handles file storage operations (upload, download, delete, list)
"""
import base64
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import authentication
try:
    from app.api.deps import get_current_user_flexible
    from app.models.user import User
except ImportError:
    class MockUser:
        def __init__(self):
            self.id = "00000000-0000-0000-0000-000000000001"
    def get_current_user_flexible():
        return lambda: MockUser()

# Import services
from services.database_service import database_service
from services.files_service import files_service


router = APIRouter()


# Schemas
class FileUpload(BaseModel):
    """Schema for file upload"""
    file_name: str = Field(..., description="File name")
    file_content: str = Field(..., description="Base64-encoded file content")
    content_type: Optional[str] = Field(default="application/octet-stream", description="MIME type")
    folder: Optional[str] = Field(default=None, description="Virtual folder path")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "document.pdf",
                "file_content": "JVBERi0xLjQK...",
                "content_type": "application/pdf",
                "folder": "documents",
                "metadata": {"category": "reports", "year": 2024}
            }
        }


class FileResponse(BaseModel):
    """Schema for file response"""
    id: str
    file_name: str
    file_path: str
    content_type: str
    file_size: int
    folder: Optional[str]
    metadata: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]


class FileDownloadResponse(BaseModel):
    """Schema for file download response"""
    id: str
    file_name: str
    file_path: str
    content_type: str
    file_size: int
    folder: Optional[str]
    metadata: Dict[str, Any]
    content: str  # Base64-encoded


class PresignedUrlResponse(BaseModel):
    """Schema for presigned URL response"""
    file_id: str
    url: str
    expiry_hours: int


# Endpoints

@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    project_id: UUID,
    file: FileUpload,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Upload file to MinIO storage

    **Flow:**
    1. Decode base64 content
    2. Upload to MinIO (S3-compatible object storage)
    3. Store metadata in PostgreSQL

    **Authentication:** Required

    **Parameters:**
    - file_name: File name
    - file_content: Base64-encoded file content
    - content_type: MIME type (default: application/octet-stream)
    - folder: Virtual folder path (optional)
    - metadata: Optional JSON metadata

    **Returns:**
    - File object with generated ID and metadata
    """
    try:
        # Decode base64 content
        try:
            file_content = base64.b64decode(file.file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 content: {str(e)}"
            )

        result = await files_service.upload_file(
            db=db,
            project_id=project_id,
            file_name=file.file_name,
            file_content=file_content,
            content_type=file.content_type,
            folder=file.folder,
            metadata=file.metadata
        )

        return FileResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("", response_model=List[FileResponse])
async def list_files(
    project_id: UUID,
    folder: Optional[str] = None,
    content_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    List files with pagination

    **Authentication:** Required

    **Query Parameters:**
    - folder: Filter by folder (optional)
    - content_type: Filter by MIME type (optional)
    - skip: Number to skip for pagination
    - limit: Max results (max 100)

    **Returns:**
    - List of files with metadata
    """
    try:
        if limit > 100:
            limit = 100

        results = await files_service.list_files(
            db=db,
            project_id=project_id,
            folder=folder,
            content_type=content_type,
            skip=skip,
            limit=limit
        )

        return [FileResponse(**result) for result in results]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )


@router.get("/{file_id}", response_model=FileDownloadResponse)
async def download_file(
    project_id: UUID,
    file_id: str,
    return_base64: bool = True,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Download file from MinIO storage

    **Flow:**
    1. Get metadata from PostgreSQL
    2. Download from MinIO
    3. Return base64-encoded content

    **Authentication:** Required

    **Path Parameters:**
    - file_id: File ID

    **Query Parameters:**
    - return_base64: Return content as base64 string (default: true)

    **Returns:**
    - File object with content (base64-encoded)
    """
    try:
        result = await files_service.download_file(
            db=db,
            project_id=project_id,
            file_id=file_id,
            return_base64=return_base64
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        return FileDownloadResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )


@router.get("/{file_id}/metadata", response_model=FileResponse)
async def get_file_metadata(
    project_id: UUID,
    file_id: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get file metadata without downloading content

    **Authentication:** Required

    **Path Parameters:**
    - file_id: File ID

    **Returns:**
    - File metadata
    """
    try:
        result = await files_service.get_file_metadata(
            db=db,
            project_id=project_id,
            file_id=file_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        return FileResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving file metadata: {str(e)}"
        )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    project_id: UUID,
    file_id: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Delete file from storage

    **Flow:**
    1. Soft delete metadata from PostgreSQL
    2. Hard delete from MinIO

    **Authentication:** Required

    **Path Parameters:**
    - file_id: File ID

    **Returns:**
    - 204 No Content on success
    """
    try:
        deleted = await files_service.delete_file(
            db=db,
            project_id=project_id,
            file_id=file_id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )


@router.get("/{file_id}/url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    project_id: UUID,
    file_id: str,
    expiry_hours: int = 24,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Generate presigned URL for file access

    Presigned URLs allow temporary direct access to files without authentication.

    **Authentication:** Required

    **Path Parameters:**
    - file_id: File ID

    **Query Parameters:**
    - expiry_hours: URL expiration time in hours (default: 24, max: 168)

    **Returns:**
    - Presigned URL with expiration time
    """
    try:
        if expiry_hours < 1 or expiry_hours > 168:  # Max 7 days
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expiry_hours must be between 1 and 168 (7 days)"
            )

        url = await files_service.generate_presigned_url(
            db=db,
            project_id=project_id,
            file_id=file_id,
            expiry_hours=expiry_hours
        )

        if not url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        return PresignedUrlResponse(
            file_id=file_id,
            url=url,
            expiry_hours=expiry_hours
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating presigned URL: {str(e)}"
        )
