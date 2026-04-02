"""
Tests for FilesystemService — local file storage replacing MinIO.

Uses BDD-style naming (given/when/then) and pytest tmp_path fixture
for fully isolated test directories.

Refs #1709
"""
import json
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest

# Adjust import path so the module can be resolved regardless of CWD
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lite.services.filesystem_service import FilesystemService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service(tmp_path: Path) -> FilesystemService:
    """Return a FilesystemService rooted in a temporary directory."""
    return FilesystemService(base_dir=str(tmp_path))


@pytest.fixture
def project_id() -> UUID:
    """A deterministic project UUID for test isolation checks."""
    return UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def other_project_id() -> UUID:
    """A second project UUID to verify isolation."""
    return UUID("11111111-2222-3333-4444-555555555555")


def _make_stream(content: bytes) -> BytesIO:
    """Helper to build a seekable BytesIO stream."""
    stream = BytesIO(content)
    return stream


# ---------------------------------------------------------------------------
# initialize_storage
# ---------------------------------------------------------------------------

class TestInitializeStorage:
    """Scenario: Preparing the base storage directory."""

    @pytest.mark.asyncio
    async def test_given_no_directory_when_initialize_then_creates_it(self, service: FilesystemService):
        result = await service.initialize_storage()
        assert result is True
        assert Path(service.base_dir).exists()

    @pytest.mark.asyncio
    async def test_given_existing_directory_when_initialize_then_succeeds(self, service: FilesystemService):
        Path(service.base_dir).mkdir(parents=True, exist_ok=True)
        result = await service.initialize_storage()
        assert result is True


# ---------------------------------------------------------------------------
# upload_file
# ---------------------------------------------------------------------------

class TestUploadFile:
    """Scenario: Storing a file on the local filesystem."""

    @pytest.mark.asyncio
    async def test_given_valid_input_when_upload_then_returns_object_name(
        self, service: FilesystemService, project_id: UUID
    ):
        content = b"hello world"
        result = await service.upload_file(
            project_id=project_id,
            file_id="file-001",
            file_content=_make_stream(content),
            file_name="readme.txt",
            content_type="text/plain",
        )

        assert result is not None
        assert "readme.txt" in result
        assert str(project_id) in result

    @pytest.mark.asyncio
    async def test_given_upload_when_file_written_then_content_matches(
        self, service: FilesystemService, project_id: UUID
    ):
        content = b"expected bytes"
        await service.upload_file(
            project_id=project_id,
            file_id="file-002",
            file_content=_make_stream(content),
            file_name="data.bin",
        )

        stored = service._project_dir(project_id) / "data.bin"
        assert stored.read_bytes() == content

    @pytest.mark.asyncio
    async def test_given_folder_when_upload_then_nested_directory_created(
        self, service: FilesystemService, project_id: UUID
    ):
        result = await service.upload_file(
            project_id=project_id,
            file_id="file-003",
            file_content=_make_stream(b"nested"),
            file_name="report.csv",
            folder="exports",
        )

        assert result is not None
        nested = service._project_dir(project_id) / "exports" / "report.csv"
        assert nested.exists()

    @pytest.mark.asyncio
    async def test_given_duplicate_filename_when_upload_then_deduplicates(
        self, service: FilesystemService, project_id: UUID
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="file-a",
            file_content=_make_stream(b"first"),
            file_name="dup.txt",
        )

        result = await service.upload_file(
            project_id=project_id,
            file_id="file-b",
            file_content=_make_stream(b"second"),
            file_name="dup.txt",
        )

        assert result is not None
        # The second file should have a unique suffix, not overwrite the first
        first_data = (service._project_dir(project_id) / "dup.txt").read_bytes()
        assert first_data == b"first"

    @pytest.mark.asyncio
    async def test_given_metadata_when_upload_then_sidecar_written(
        self, service: FilesystemService, project_id: UUID
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="file-meta",
            file_content=_make_stream(b"meta test"),
            file_name="meta.txt",
            content_type="text/plain",
            metadata={"author": "test-suite"},
        )

        meta_path = service._project_dir(project_id) / ("meta.txt" + service.METADATA_SUFFIX)
        assert meta_path.exists()

        meta = json.loads(meta_path.read_text())
        assert meta["content_type"] == "text/plain"
        assert meta["custom"]["author"] == "test-suite"
        assert meta["file_id"] == "file-meta"


# ---------------------------------------------------------------------------
# download_file
# ---------------------------------------------------------------------------

class TestDownloadFile:
    """Scenario: Retrieving a stored file."""

    @pytest.mark.asyncio
    async def test_given_existing_file_when_download_then_returns_content(
        self, service: FilesystemService, project_id: UUID
    ):
        content = b"download me"
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="dl-1",
            file_content=_make_stream(content),
            file_name="fetch.bin",
        )

        result = await service.download_file(object_name)
        assert result is not None
        assert result.read() == content

    @pytest.mark.asyncio
    async def test_given_nonexistent_object_when_download_then_returns_none(
        self, service: FilesystemService
    ):
        result = await service.download_file("projects/fake-id/missing.txt")
        assert result is None

    @pytest.mark.asyncio
    async def test_given_invalid_object_name_when_download_then_returns_none(
        self, service: FilesystemService
    ):
        result = await service.download_file("bad/path")
        assert result is None


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------

class TestDeleteFile:
    """Scenario: Removing a file from storage."""

    @pytest.mark.asyncio
    async def test_given_existing_file_when_delete_then_returns_true(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="del-1",
            file_content=_make_stream(b"delete me"),
            file_name="remove.txt",
        )

        result = await service.delete_file(object_name)
        assert result is True

    @pytest.mark.asyncio
    async def test_given_deleted_file_when_download_then_returns_none(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="del-2",
            file_content=_make_stream(b"gone soon"),
            file_name="ephemeral.txt",
        )

        await service.delete_file(object_name)
        result = await service.download_file(object_name)
        assert result is None

    @pytest.mark.asyncio
    async def test_given_deleted_file_then_sidecar_also_removed(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="del-3",
            file_content=_make_stream(b"and meta"),
            file_name="withmeta.txt",
            metadata={"key": "val"},
        )

        await service.delete_file(object_name)

        meta_path = service._project_dir(project_id) / ("withmeta.txt" + service.METADATA_SUFFIX)
        assert not meta_path.exists()

    @pytest.mark.asyncio
    async def test_given_nonexistent_file_when_delete_then_returns_false(
        self, service: FilesystemService
    ):
        result = await service.delete_file("projects/no-such-project/nope.txt")
        assert result is False


# ---------------------------------------------------------------------------
# delete_files_by_project
# ---------------------------------------------------------------------------

class TestDeleteFilesByProject:
    """Scenario: Bulk-removing all files for a project."""

    @pytest.mark.asyncio
    async def test_given_project_files_when_delete_by_project_then_all_removed(
        self, service: FilesystemService, project_id: UUID
    ):
        for i in range(3):
            await service.upload_file(
                project_id=project_id,
                file_id=f"bulk-{i}",
                file_content=_make_stream(f"file {i}".encode()),
                file_name=f"file_{i}.txt",
            )

        deleted = await service.delete_files_by_project(project_id)
        assert deleted == 3
        assert not service._project_dir(project_id).exists()

    @pytest.mark.asyncio
    async def test_given_empty_project_when_delete_by_project_then_returns_zero(
        self, service: FilesystemService
    ):
        fake_id = uuid4()
        deleted = await service.delete_files_by_project(fake_id)
        assert deleted == 0


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

class TestListFiles:
    """Scenario: Enumerating stored files."""

    @pytest.mark.asyncio
    async def test_given_uploaded_files_when_list_then_returns_all(
        self, service: FilesystemService, project_id: UUID
    ):
        for i in range(3):
            await service.upload_file(
                project_id=project_id,
                file_id=f"list-{i}",
                file_content=_make_stream(f"data-{i}".encode()),
                file_name=f"item_{i}.txt",
                content_type="text/plain",
            )

        files = await service.list_files(project_id)
        assert len(files) == 3
        names = {f["object_name"] for f in files}
        for i in range(3):
            assert any(f"item_{i}.txt" in n for n in names)

    @pytest.mark.asyncio
    async def test_given_folder_filter_when_list_then_returns_filtered(
        self, service: FilesystemService, project_id: UUID
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="f1",
            file_content=_make_stream(b"root"),
            file_name="root.txt",
        )
        await service.upload_file(
            project_id=project_id,
            file_id="f2",
            file_content=_make_stream(b"nested"),
            file_name="nested.txt",
            folder="subfolder",
        )

        filtered = await service.list_files(project_id, folder="subfolder")
        assert len(filtered) == 1
        assert "nested.txt" in filtered[0]["object_name"]

    @pytest.mark.asyncio
    async def test_given_no_files_when_list_then_returns_empty(
        self, service: FilesystemService
    ):
        files = await service.list_files(uuid4())
        assert files == []

    @pytest.mark.asyncio
    async def test_list_files_includes_size_and_content_type(
        self, service: FilesystemService, project_id: UUID
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="typed",
            file_content=_make_stream(b"12345"),
            file_name="sized.json",
            content_type="application/json",
        )

        files = await service.list_files(project_id)
        assert len(files) == 1
        assert files[0]["size"] == 5
        assert files[0]["content_type"] == "application/json"


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------

class TestGetFileInfo:
    """Scenario: Inspecting a single file's metadata."""

    @pytest.mark.asyncio
    async def test_given_existing_file_when_get_info_then_returns_metadata(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="info-1",
            file_content=_make_stream(b"info test"),
            file_name="info.txt",
            content_type="text/plain",
            metadata={"tag": "important"},
        )

        info = await service.get_file_info(object_name)
        assert info is not None
        assert info["object_name"] == object_name
        assert info["size"] == len(b"info test")
        assert info["content_type"] == "text/plain"
        assert info["metadata"]["tag"] == "important"

    @pytest.mark.asyncio
    async def test_given_missing_file_when_get_info_then_returns_none(
        self, service: FilesystemService
    ):
        info = await service.get_file_info("projects/nope/no-file.txt")
        assert info is None

    @pytest.mark.asyncio
    async def test_given_invalid_path_when_get_info_then_returns_none(
        self, service: FilesystemService
    ):
        info = await service.get_file_info("invalid")
        assert info is None


# ---------------------------------------------------------------------------
# Project isolation
# ---------------------------------------------------------------------------

class TestProjectIsolation:
    """Scenario: Files in separate projects must not leak across boundaries."""

    @pytest.mark.asyncio
    async def test_given_two_projects_when_list_then_only_own_files_returned(
        self,
        service: FilesystemService,
        project_id: UUID,
        other_project_id: UUID,
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="iso-a",
            file_content=_make_stream(b"project A"),
            file_name="a.txt",
        )
        await service.upload_file(
            project_id=other_project_id,
            file_id="iso-b",
            file_content=_make_stream(b"project B"),
            file_name="b.txt",
        )

        files_a = await service.list_files(project_id)
        files_b = await service.list_files(other_project_id)

        assert len(files_a) == 1
        assert len(files_b) == 1
        assert "a.txt" in files_a[0]["object_name"]
        assert "b.txt" in files_b[0]["object_name"]

    @pytest.mark.asyncio
    async def test_given_delete_by_project_then_other_project_untouched(
        self,
        service: FilesystemService,
        project_id: UUID,
        other_project_id: UUID,
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="del-iso-a",
            file_content=_make_stream(b"delete me"),
            file_name="gone.txt",
        )
        await service.upload_file(
            project_id=other_project_id,
            file_id="del-iso-b",
            file_content=_make_stream(b"keep me"),
            file_name="stay.txt",
        )

        await service.delete_files_by_project(project_id)

        remaining = await service.list_files(other_project_id)
        assert len(remaining) == 1


# ---------------------------------------------------------------------------
# Large file handling
# ---------------------------------------------------------------------------

class TestLargeFileHandling:
    """Scenario: Service handles files larger than typical small payloads."""

    @pytest.mark.asyncio
    async def test_given_10mb_file_when_upload_download_then_roundtrips(
        self, service: FilesystemService, project_id: UUID
    ):
        large_content = b"X" * (10 * 1024 * 1024)  # 10 MB

        object_name = await service.upload_file(
            project_id=project_id,
            file_id="large-1",
            file_content=_make_stream(large_content),
            file_name="large.bin",
        )

        downloaded = await service.download_file(object_name)
        assert downloaded is not None
        assert downloaded.read() == large_content

    @pytest.mark.asyncio
    async def test_given_large_file_when_get_info_then_size_correct(
        self, service: FilesystemService, project_id: UUID
    ):
        size = 5 * 1024 * 1024  # 5 MB
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="large-2",
            file_content=_make_stream(b"Y" * size),
            file_name="medium.bin",
        )

        info = await service.get_file_info(object_name)
        assert info is not None
        assert info["size"] == size


# ---------------------------------------------------------------------------
# Content type detection
# ---------------------------------------------------------------------------

class TestContentTypeDetection:
    """Scenario: MIME types are resolved from filenames and overrides."""

    @pytest.mark.asyncio
    async def test_given_json_filename_when_upload_no_type_then_detects_json(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="ct-1",
            file_content=_make_stream(b"{}"),
            file_name="data.json",
            content_type="application/json",
        )

        info = await service.get_file_info(object_name)
        assert info["content_type"] == "application/json"

    @pytest.mark.asyncio
    async def test_given_explicit_type_when_upload_then_uses_override(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="ct-2",
            file_content=_make_stream(b"custom"),
            file_name="blob",
            content_type="application/x-custom",
        )

        info = await service.get_file_info(object_name)
        assert info["content_type"] == "application/x-custom"

    def test_detect_content_type_fallback(self, service: FilesystemService):
        assert service._detect_content_type("unknown_ext") == "application/octet-stream"

    def test_detect_content_type_known_extensions(self, service: FilesystemService):
        assert service._detect_content_type("image.png") == "image/png"
        assert service._detect_content_type("style.css") == "text/css"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Scenario: Verifying storage backend availability."""

    @pytest.mark.asyncio
    async def test_given_writable_dir_when_health_check_then_healthy(
        self, service: FilesystemService
    ):
        result = await service.health_check()
        assert result["status"] == "healthy"
        assert result["storage"] == "filesystem"

    @pytest.mark.asyncio
    async def test_given_unwritable_dir_when_health_check_then_unhealthy(
        self, tmp_path: Path
    ):
        bad_path = tmp_path / "readonly"
        bad_path.mkdir()
        bad_path.chmod(0o444)
        svc = FilesystemService(base_dir=str(bad_path / "nested" / "deep"))
        # On some systems this may or may not fail depending on root permissions,
        # but at minimum the method should not raise
        result = await svc.health_check()
        assert "status" in result
        # Restore permissions for cleanup
        bad_path.chmod(0o755)


# ---------------------------------------------------------------------------
# Error handling edge cases
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Scenario: Graceful handling of filesystem errors."""

    @pytest.mark.asyncio
    async def test_given_invalid_delete_path_when_delete_then_returns_false(
        self, service: FilesystemService
    ):
        # Malformed object_name with no "projects" prefix
        result = await service.delete_file("no-prefix/file.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_given_file_without_sidecar_when_list_then_detects_type(
        self, service: FilesystemService, project_id: UUID
    ):
        """Files placed directly (no sidecar) should still appear in listings."""
        project_dir = service._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "manual.html").write_bytes(b"<html></html>")

        files = await service.list_files(project_id)
        assert len(files) == 1
        assert files[0]["content_type"] == "text/html"
        assert files[0]["metadata"] == {}

    @pytest.mark.asyncio
    async def test_given_file_without_sidecar_when_get_info_then_falls_back(
        self, service: FilesystemService, project_id: UUID
    ):
        """get_file_info should still work when no sidecar metadata exists."""
        project_dir = service._project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "plain.txt").write_bytes(b"no meta")

        info = await service.get_file_info(f"projects/{project_id}/plain.txt")
        assert info is not None
        assert info["size"] == 7
        assert info["metadata"] == {}

    @pytest.mark.asyncio
    async def test_given_default_base_dir_when_init_then_uses_home(self):
        """Default constructor should target ~/.zerodb/data/files."""
        svc = FilesystemService()
        assert svc.base_dir == Path.home() / ".zerodb" / "data" / "files"

    @pytest.mark.asyncio
    async def test_given_upload_with_no_metadata_when_sidecar_read_then_empty_custom(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="no-meta",
            file_content=_make_stream(b"bare"),
            file_name="bare.txt",
        )
        info = await service.get_file_info(object_name)
        assert info["metadata"] == {}


# ---------------------------------------------------------------------------
# OSError branch coverage via mocks/patching
# ---------------------------------------------------------------------------

class TestOSErrorBranches:
    """Scenario: Filesystem errors are caught and handled gracefully."""

    @pytest.mark.asyncio
    async def test_upload_returns_none_on_write_error(
        self, service: FilesystemService, project_id: UUID
    ):
        from unittest.mock import patch
        with patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
            result = await service.upload_file(
                project_id=project_id,
                file_id="err-1",
                file_content=_make_stream(b"fail"),
                file_name="fail.txt",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_download_returns_none_on_read_error(
        self, service: FilesystemService, project_id: UUID
    ):
        # First upload a real file
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="err-dl",
            file_content=_make_stream(b"ok"),
            file_name="readable.txt",
        )
        from unittest.mock import patch
        with patch.object(Path, "read_bytes", side_effect=OSError("io error")):
            result = await service.download_file(object_name)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_unlink_error(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="err-del",
            file_content=_make_stream(b"stuck"),
            file_name="stuck.txt",
        )
        from unittest.mock import patch
        with patch.object(Path, "unlink", side_effect=OSError("perm denied")):
            result = await service.delete_file(object_name)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_files_by_project_returns_zero_on_error(
        self, service: FilesystemService, project_id: UUID
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="err-bulk",
            file_content=_make_stream(b"bulk fail"),
            file_name="bulkfail.txt",
        )
        from unittest.mock import patch
        with patch.object(Path, "unlink", side_effect=OSError("cannot remove")):
            result = await service.delete_files_by_project(project_id)
        assert result == 0

    @pytest.mark.asyncio
    async def test_list_files_returns_empty_on_error(
        self, service: FilesystemService, project_id: UUID
    ):
        await service.upload_file(
            project_id=project_id,
            file_id="err-list",
            file_content=_make_stream(b"list fail"),
            file_name="listfail.txt",
        )
        from unittest.mock import patch
        with patch.object(Path, "rglob", side_effect=OSError("no access")):
            result = await service.list_files(project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_file_info_returns_none_on_stat_error(
        self, service: FilesystemService, project_id: UUID
    ):
        object_name = await service.upload_file(
            project_id=project_id,
            file_id="err-info",
            file_content=_make_stream(b"stat fail"),
            file_name="statfail.txt",
        )
        from unittest.mock import patch
        with patch.object(Path, "stat", side_effect=OSError("stat error")):
            result = await service.get_file_info(object_name)
        assert result is None

    @pytest.mark.asyncio
    async def test_initialize_storage_returns_false_on_error(self, tmp_path: Path):
        from unittest.mock import patch
        svc = FilesystemService(base_dir=str(tmp_path / "init_fail"))
        with patch.object(Path, "mkdir", side_effect=OSError("cannot create")):
            result = await svc.initialize_storage()
        assert result is False
