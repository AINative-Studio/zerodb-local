"""
Files Service
Handles file storage using PostgreSQL (metadata) + MinIO (object storage)
"""
import os
import base64
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.minio_service import minio_service


class FilesService:
    """
    Service for file operations

    Architecture:
    - PostgreSQL: Stores file metadata (name, size, path)
    - MinIO: Stores actual file content (S3-compatible)
    """

    def __init__(self):
        self.default_bucket = os.getenv("MINIO_BUCKET_NAME", "zerodb-local")

    async def upload_file(
        self,
        db: Session,
        project_id: UUID,
        file_name: str,
        file_content: bytes,
        content_type: str = "application/octet-stream",
        folder: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file

        Steps:
        1. Upload to MinIO (object storage)
        2. Store metadata in PostgreSQL

        Args:
            db: Database session
            project_id: Project UUID
            file_name: File name
            file_content: File content (bytes)
            content_type: MIME type
            folder: Optional folder path
            metadata: Optional metadata dict

        Returns:
            Created file info
        """
        # Step 1: Upload to MinIO
        file_path = f"{project_id}/{folder}/{file_name}" if folder else f"{project_id}/{file_name}"
        file_size = len(file_content)

        await minio_service.upload_object(
            bucket_name=self.default_bucket,
            object_name=file_path,
            data=file_content,
            content_type=content_type
        )

        # Step 2: Store metadata in PostgreSQL
        insert_query = text("""
            INSERT INTO files (project_id, file_name, file_path, content_type, file_size, folder, metadata)
            VALUES (:project_id, :file_name, :file_path, :content_type, :file_size, :folder, CAST(:metadata AS jsonb))
            RETURNING id, file_name, file_path, content_type, file_size, folder, metadata, created_at, updated_at
        """)

        result = db.execute(
            insert_query,
            {
                "project_id": str(project_id),
                "file_name": file_name,
                "file_path": file_path,
                "content_type": content_type,
                "file_size": file_size,
                "folder": folder,
                "metadata": str(metadata or {})
            }
        ).first()

        db.commit()

        return {
            "id": str(result.id),
            "file_name": result.file_name,
            "file_path": result.file_path,
            "content_type": result.content_type,
            "file_size": result.file_size,
            "folder": result.folder,
            "metadata": result.metadata or {},
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None
        }

    async def download_file(
        self,
        db: Session,
        project_id: UUID,
        file_id: str,
        return_base64: bool = True
    ) -> Dict[str, Any]:
        """
        Download a file

        Steps:
        1. Get metadata from PostgreSQL
        2. Download from MinIO

        Args:
            db: Database session
            project_id: Project UUID
            file_id: File ID
            return_base64: Return content as base64 string

        Returns:
            File info with content
        """
        # Step 1: Get metadata from PostgreSQL
        query = text("""
            SELECT id, file_name, file_path, content_type, file_size, folder, metadata
            FROM files
            WHERE project_id = :project_id
            AND id = :file_id
            AND deleted_at IS NULL
        """)

        result = db.execute(
            query,
            {"project_id": str(project_id), "file_id": file_id}
        ).first()

        if not result:
            return None

        # Step 2: Download from MinIO
        file_content = await minio_service.download_object(
            bucket_name=self.default_bucket,
            object_name=result.file_path
        )

        # Encode to base64 if requested
        if return_base64:
            file_content = base64.b64encode(file_content).decode('utf-8')

        return {
            "id": str(result.id),
            "file_name": result.file_name,
            "file_path": result.file_path,
            "content_type": result.content_type,
            "file_size": result.file_size,
            "folder": result.folder,
            "metadata": result.metadata or {},
            "content": file_content
        }

    async def list_files(
        self,
        db: Session,
        project_id: UUID,
        folder: Optional[str] = None,
        content_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files with pagination

        Args:
            db: Database session
            project_id: Project UUID
            folder: Filter by folder
            content_type: Filter by MIME type
            skip: Number to skip (pagination)
            limit: Max results

        Returns:
            List of files
        """
        # Build dynamic query
        filters = ["project_id = :project_id", "deleted_at IS NULL"]
        params = {
            "project_id": str(project_id),
            "limit": limit,
            "offset": skip
        }

        if folder is not None:
            filters.append("folder = :folder")
            params["folder"] = folder

        if content_type:
            filters.append("content_type = :content_type")
            params["content_type"] = content_type

        where_clause = " AND ".join(filters)

        query = text(f"""
            SELECT id, file_name, file_path, content_type, file_size, folder, metadata, created_at, updated_at
            FROM files
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        results = db.execute(query, params).fetchall()

        return [
            {
                "id": str(row.id),
                "file_name": row.file_name,
                "file_path": row.file_path,
                "content_type": row.content_type,
                "file_size": row.file_size,
                "folder": row.folder,
                "metadata": row.metadata or {},
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            }
            for row in results
        ]

    async def get_file_metadata(
        self,
        db: Session,
        project_id: UUID,
        file_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get file metadata without downloading content

        Args:
            db: Database session
            project_id: Project UUID
            file_id: File ID

        Returns:
            File metadata or None
        """
        query = text("""
            SELECT id, file_name, file_path, content_type, file_size, folder, metadata, created_at, updated_at
            FROM files
            WHERE project_id = :project_id
            AND id = :file_id
            AND deleted_at IS NULL
        """)

        result = db.execute(
            query,
            {"project_id": str(project_id), "file_id": file_id}
        ).first()

        if not result:
            return None

        return {
            "id": str(result.id),
            "file_name": result.file_name,
            "file_path": result.file_path,
            "content_type": result.content_type,
            "file_size": result.file_size,
            "folder": result.folder,
            "metadata": result.metadata or {},
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None
        }

    async def delete_file(
        self,
        db: Session,
        project_id: UUID,
        file_id: str
    ) -> bool:
        """
        Delete a file (soft delete in PostgreSQL, hard delete in MinIO)

        Args:
            db: Database session
            project_id: Project UUID
            file_id: File ID

        Returns:
            True if deleted, False if not found
        """
        # Get file path before deleting
        select_query = text("""
            SELECT file_path FROM files
            WHERE project_id = :project_id
            AND id = :file_id
            AND deleted_at IS NULL
        """)

        result = db.execute(
            select_query,
            {"project_id": str(project_id), "file_id": file_id}
        ).first()

        if not result:
            return False

        file_path = result.file_path

        # Soft delete from PostgreSQL
        delete_query = text("""
            UPDATE files
            SET deleted_at = NOW()
            WHERE project_id = :project_id
            AND id = :file_id
            RETURNING id
        """)

        db.execute(
            delete_query,
            {"project_id": str(project_id), "file_id": file_id}
        )

        db.commit()

        # Hard delete from MinIO
        try:
            await minio_service.delete_object(
                bucket_name=self.default_bucket,
                object_name=file_path
            )
        except Exception:
            pass  # Continue even if MinIO delete fails

        return True

    async def generate_presigned_url(
        self,
        db: Session,
        project_id: UUID,
        file_id: str,
        expiry_hours: int = 24
    ) -> Optional[str]:
        """
        Generate presigned URL for file access

        Args:
            db: Database session
            project_id: Project UUID
            file_id: File ID
            expiry_hours: URL expiration time in hours

        Returns:
            Presigned URL or None
        """
        # Get file path from PostgreSQL
        query = text("""
            SELECT file_path FROM files
            WHERE project_id = :project_id
            AND id = :file_id
            AND deleted_at IS NULL
        """)

        result = db.execute(
            query,
            {"project_id": str(project_id), "file_id": file_id}
        ).first()

        if not result:
            return None

        # Generate presigned URL from MinIO
        url = await minio_service.generate_presigned_url(
            bucket_name=self.default_bucket,
            object_name=result.file_path,
            expiry_seconds=expiry_hours * 3600
        )

        return url


# Global instance
files_service = FilesService()
