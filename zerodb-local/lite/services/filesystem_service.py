"""
Filesystem Storage Service for ZeroDB Lite
Replaces MinIO dependency with local filesystem storage.
Files stored at ~/.zerodb/data/files/{project_id}/{filename}
"""
import json
import mimetypes
import os
import shutil
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional
from uuid import UUID


class FilesystemService:
    """
    Local filesystem storage service that mirrors the MinIO service interface.

    Stores files under a configurable base directory (default ~/.zerodb/data/files)
    with per-project isolation. Metadata is tracked via JSON sidecar files.
    """

    METADATA_SUFFIX = ".__meta__.json"

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize filesystem service.

        Args:
            base_dir: Root directory for file storage.
                      Defaults to ~/.zerodb/data/files
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / ".zerodb" / "data" / "files"

    def _project_dir(self, project_id: UUID) -> Path:
        """Get the storage directory for a given project."""
        return self.base_dir / str(project_id)

    def _resolve_path(self, project_id: UUID, folder: Optional[str], filename: str) -> Path:
        """Build the full file path within a project directory."""
        parts = [self._project_dir(project_id)]
        if folder:
            parts.append(Path(folder))
        parts.append(Path(filename))
        # Join all parts
        result = parts[0]
        for p in parts[1:]:
            result = result / p
        return result

    def _meta_path(self, file_path: Path) -> Path:
        """Return the sidecar metadata path for a given file."""
        return file_path.parent / (file_path.name + self.METADATA_SUFFIX)

    def _write_metadata(self, file_path: Path, metadata: Dict[str, Any]) -> None:
        """Write metadata to a JSON sidecar file."""
        meta_path = self._meta_path(file_path)
        meta_path.write_text(json.dumps(metadata, default=str), encoding="utf-8")

    def _read_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Read metadata from a JSON sidecar file."""
        meta_path = self._meta_path(file_path)
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return {}

    def _deduplicate_filename(self, target_path: Path) -> Path:
        """
        If the target path already exists, append a UUID suffix to avoid
        overwriting existing files.

        Returns:
            A path that does not collide with existing files.
        """
        if not target_path.exists():
            return target_path

        stem = target_path.stem
        suffix = target_path.suffix
        unique = uuid.uuid4().hex[:8]
        new_name = f"{stem}_{unique}{suffix}"
        return target_path.parent / new_name

    def _detect_content_type(self, filename: str) -> str:
        """Guess MIME type from filename, falling back to octet-stream."""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    def _object_name(self, project_id: UUID, folder: Optional[str], filename: str) -> str:
        """Build a virtual object name matching the MinIO path convention."""
        parts = ["projects", str(project_id)]
        if folder:
            parts.append(folder)
        parts.append(filename)
        return "/".join(parts)

    # ------------------------------------------------------------------
    # Public API — mirrors MinIO service interface
    # ------------------------------------------------------------------

    async def initialize_storage(self) -> bool:
        """
        Ensure the base storage directory exists.

        Returns:
            True if directory exists or was created successfully.
        """
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as exc:
            print(f"Error creating storage directory: {exc}")
            return False

    async def upload_file(
        self,
        project_id: UUID,
        file_id: str,
        file_content: BinaryIO,
        file_name: str,
        content_type: str = "application/octet-stream",
        folder: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Upload a file to local filesystem storage.

        Args:
            project_id: Project UUID for isolation.
            file_id: Unique file identifier.
            file_content: Readable binary stream with the file data.
            file_name: Original filename (used for content-type detection).
            content_type: MIME type override.
            folder: Optional sub-folder within the project directory.
            metadata: Optional key-value metadata stored in sidecar JSON.

        Returns:
            The virtual object name (string path) on success, None on error.
        """
        try:
            target_path = self._resolve_path(project_id, folder, file_name)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle duplicate filenames
            target_path = self._deduplicate_filename(target_path)

            # Read content
            file_content.seek(0, 2)
            file_size = file_content.tell()
            file_content.seek(0)
            data = file_content.read()

            # Write file
            target_path.write_bytes(data)

            # Write sidecar metadata
            meta = {
                "project_id": str(project_id),
                "file_id": file_id,
                "file_name": file_name,
                "stored_name": target_path.name,
                "content_type": content_type,
                "size": file_size,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "folder": folder,
            }
            if metadata:
                meta["custom"] = metadata
            self._write_metadata(target_path, meta)

            object_name = self._object_name(project_id, folder, target_path.name)
            return object_name

        except OSError as exc:
            print(f"Error uploading file: {exc}")
            return None

    async def download_file(
        self,
        object_name: str,
    ) -> Optional[BytesIO]:
        """
        Download a file from local storage.

        Args:
            object_name: Virtual object path (projects/{project_id}/...).

        Returns:
            BytesIO stream with file contents, or None if not found.
        """
        try:
            # Convert object_name back to filesystem path
            # Format: projects/{project_id}/[folder/]{filename}
            parts = object_name.split("/")
            if len(parts) < 3 or parts[0] != "projects":
                return None

            project_id = parts[1]
            remaining = parts[2:]
            file_path = self.base_dir / project_id / Path(*remaining)

            if not file_path.exists() or not file_path.is_file():
                return None

            return BytesIO(file_path.read_bytes())

        except (OSError, TypeError) as exc:
            print(f"Error downloading file: {exc}")
            return None

    async def delete_file(
        self,
        object_name: str,
    ) -> bool:
        """
        Delete a file and its metadata sidecar from local storage.

        Args:
            object_name: Virtual object path.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            parts = object_name.split("/")
            if len(parts) < 3 or parts[0] != "projects":
                return False

            project_id = parts[1]
            remaining = parts[2:]
            file_path = self.base_dir / project_id / Path(*remaining)

            if not file_path.exists():
                return False

            # Remove sidecar metadata first
            meta_path = self._meta_path(file_path)
            if meta_path.exists():
                meta_path.unlink()

            # Remove the file
            file_path.unlink()
            return True

        except OSError as exc:
            print(f"Error deleting file: {exc}")
            return False

    async def delete_files_by_project(
        self,
        project_id: UUID,
    ) -> int:
        """
        Delete all files for a given project.

        Args:
            project_id: Project UUID.

        Returns:
            Number of files deleted (excluding metadata sidecars).
        """
        project_dir = self._project_dir(project_id)
        if not project_dir.exists():
            return 0

        try:
            deleted = 0
            for path in project_dir.rglob("*"):
                if path.is_file() and not path.name.endswith(self.METADATA_SUFFIX):
                    # Remove sidecar
                    meta = self._meta_path(path)
                    if meta.exists():
                        meta.unlink()
                    path.unlink()
                    deleted += 1

            # Clean up empty directories
            shutil.rmtree(project_dir, ignore_errors=True)
            return deleted

        except OSError as exc:
            print(f"Error deleting project files: {exc}")
            return 0

    async def list_files(
        self,
        project_id: UUID,
        folder: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all files for a project, optionally filtered by folder.

        Args:
            project_id: Project UUID.
            folder: Optional sub-folder filter.

        Returns:
            List of file info dicts.
        """
        search_dir = self._project_dir(project_id)
        if folder:
            search_dir = search_dir / folder

        if not search_dir.exists():
            return []

        files = []
        try:
            for path in search_dir.rglob("*"):
                if not path.is_file():
                    continue
                if path.name.endswith(self.METADATA_SUFFIX):
                    continue

                meta = self._read_metadata(path)
                stat = path.stat()

                files.append({
                    "object_name": self._object_name(
                        project_id,
                        folder,
                        path.name,
                    ),
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "content_type": meta.get(
                        "content_type",
                        self._detect_content_type(path.name),
                    ),
                    "metadata": meta.get("custom", {}),
                })

            return files

        except OSError as exc:
            print(f"Error listing files: {exc}")
            return []

    async def get_file_info(
        self,
        object_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a single file.

        Args:
            object_name: Virtual object path.

        Returns:
            File info dict, or None if not found.
        """
        try:
            parts = object_name.split("/")
            if len(parts) < 3 or parts[0] != "projects":
                return None

            project_id = parts[1]
            remaining = parts[2:]
            file_path = self.base_dir / project_id / Path(*remaining)

            if not file_path.exists() or not file_path.is_file():
                return None

            stat = file_path.stat()
            meta = self._read_metadata(file_path)

            return {
                "object_name": object_name,
                "size": stat.st_size,
                "last_modified": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "content_type": meta.get(
                    "content_type",
                    self._detect_content_type(file_path.name),
                ),
                "etag": None,
                "metadata": meta.get("custom", {}),
            }

        except OSError as exc:
            print(f"Error getting file info: {exc}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check filesystem storage health.

        Returns:
            Health status dict.
        """
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            # Verify we can write
            test_file = self.base_dir / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()

            return {
                "status": "healthy",
                "storage": "filesystem",
                "base_dir": str(self.base_dir),
            }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "storage": "filesystem",
                "error": str(exc),
            }


# Global instance
filesystem_service = FilesystemService()
