"""
MinIO Object Storage Service
Handles file upload/download using MinIO (S3-compatible)
"""
import os
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import timedelta
from uuid import UUID

from minio import Minio
from minio.error import S3Error
from urllib3.response import HTTPResponse


class MinIOService:
    """Service for interacting with MinIO object storage"""

    def __init__(self):
        """Initialize MinIO client"""
        # Parse MinIO URL (remove http:// or https://)
        minio_url = os.getenv("MINIO_URL", "localhost:9000").replace("http://", "").replace("https://", "")

        self.endpoint = minio_url
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.default_bucket = os.getenv("MINIO_BUCKET", "zerodb-local-files")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.testing = os.getenv("TESTING", "false").lower() == "true"

        if not self.testing:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
        else:
            # Mock MinIO client for testing
            from unittest.mock import MagicMock
            self.client = MagicMock()

    async def initialize_bucket(self, bucket_name: str = None) -> bool:
        """
        Create bucket if it doesn't exist

        Args:
            bucket_name: Bucket name (default: zerodb-local-files)

        Returns:
            bool: True if created/exists, False on error
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            # Check if bucket exists
            if self.client.bucket_exists(bucket_name):
                print(f"✅ Bucket '{bucket_name}' already exists")
                return True

            # Create bucket
            self.client.make_bucket(bucket_name)
            print(f"✅ Created bucket '{bucket_name}'")
            return True

        except S3Error as e:
            print(f"❌ Error creating bucket: {e}")
            return False

    async def upload_file(
        self,
        project_id: UUID,
        file_id: str,
        file_content: BinaryIO,
        file_name: str,
        content_type: str = "application/octet-stream",
        folder: str = None,
        metadata: Dict[str, str] = None,
        bucket_name: str = None
    ) -> Optional[str]:
        """
        Upload file to MinIO

        Args:
            project_id: Project UUID
            file_id: File UUID
            file_content: File binary content
            file_name: Original file name
            content_type: MIME type
            folder: Optional folder path
            metadata: Optional file metadata
            bucket_name: Bucket name

        Returns:
            str: Object name in MinIO, or None on error
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            # Construct object path: projects/{project_id}/{folder}/{file_id}
            path_parts = ["projects", str(project_id)]
            if folder:
                path_parts.append(folder)
            path_parts.append(file_id)

            object_name = "/".join(path_parts)

            # Prepare metadata
            file_metadata = {
                "project_id": str(project_id),
                "file_name": file_name,
                "file_id": file_id
            }
            if metadata:
                file_metadata.update(metadata)

            # Get file size
            file_content.seek(0, 2)  # Seek to end
            file_size = file_content.tell()
            file_content.seek(0)  # Reset to beginning

            # Upload to MinIO
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_content,
                length=file_size,
                content_type=content_type,
                metadata=file_metadata
            )

            print(f"✅ Uploaded file '{file_name}' to {object_name}")
            return object_name

        except S3Error as e:
            print(f"❌ Error uploading file: {e}")
            return None

    async def download_file(
        self,
        object_name: str,
        bucket_name: str = None
    ) -> Optional[HTTPResponse]:
        """
        Download file from MinIO

        Args:
            object_name: Object path in MinIO
            bucket_name: Bucket name

        Returns:
            HTTPResponse with file data, or None on error
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            response = self.client.get_object(bucket_name, object_name)
            return response

        except S3Error as e:
            print(f"❌ Error downloading file: {e}")
            return None

    async def delete_file(
        self,
        object_name: str,
        bucket_name: str = None
    ) -> bool:
        """
        Delete file from MinIO

        Args:
            object_name: Object path in MinIO
            bucket_name: Bucket name

        Returns:
            bool: Success status
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            self.client.remove_object(bucket_name, object_name)
            print(f"✅ Deleted file '{object_name}'")
            return True

        except S3Error as e:
            print(f"❌ Error deleting file: {e}")
            return False

    async def delete_files_by_project(
        self,
        project_id: UUID,
        bucket_name: str = None
    ) -> int:
        """
        Delete all files for a project

        Args:
            project_id: Project UUID
            bucket_name: Bucket name

        Returns:
            int: Number of files deleted
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            # List all objects with project prefix
            prefix = f"projects/{str(project_id)}/"
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)

            deleted_count = 0
            for obj in objects:
                self.client.remove_object(bucket_name, obj.object_name)
                deleted_count += 1

            print(f"✅ Deleted {deleted_count} files for project {project_id}")
            return deleted_count

        except S3Error as e:
            print(f"❌ Error deleting files: {e}")
            return 0

    async def generate_presigned_url(
        self,
        object_name: str,
        expiry_hours: int = 24,
        bucket_name: str = None
    ) -> Optional[str]:
        """
        Generate presigned URL for file download

        Args:
            object_name: Object path in MinIO
            expiry_hours: URL expiration in hours
            bucket_name: Bucket name

        Returns:
            str: Presigned URL, or None on error
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(hours=expiry_hours)
            )
            return url

        except S3Error as e:
            print(f"❌ Error generating presigned URL: {e}")
            return None

    async def list_files(
        self,
        project_id: UUID,
        folder: str = None,
        bucket_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        List files for a project

        Args:
            project_id: Project UUID
            folder: Optional folder filter
            bucket_name: Bucket name

        Returns:
            List of file info dicts
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            # Build prefix
            prefix = f"projects/{str(project_id)}/"
            if folder:
                prefix += f"{folder}/"

            # List objects
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)

            files = []
            for obj in objects:
                # Get object metadata
                stat = self.client.stat_object(bucket_name, obj.object_name)

                files.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "content_type": stat.content_type,
                    "metadata": stat.metadata
                })

            return files

        except S3Error as e:
            print(f"❌ Error listing files: {e}")
            return []

    async def get_file_info(
        self,
        object_name: str,
        bucket_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get file metadata

        Args:
            object_name: Object path in MinIO
            bucket_name: Bucket name

        Returns:
            File info dict or None
        """
        if bucket_name is None:
            bucket_name = self.default_bucket

        try:
            stat = self.client.stat_object(bucket_name, object_name)

            return {
                "object_name": object_name,
                "size": stat.size,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "etag": stat.etag,
                "metadata": stat.metadata
            }

        except S3Error as e:
            print(f"❌ Error getting file info: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check MinIO health

        Returns:
            Health status dict
        """
        try:
            # Try to list buckets
            buckets = self.client.list_buckets()

            return {
                "status": "healthy",
                "endpoint": self.endpoint,
                "secure": self.secure,
                "buckets": [bucket.name for bucket in buckets]
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "endpoint": self.endpoint,
                "error": str(e)
            }


# Global instance
minio_service = MinIOService()
