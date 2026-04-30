"""
Pull Sync Service
Handles cloud → local sync operations (pull direction)
"""
import os
import json
import zipfile
import tempfile
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from schemas.pull_sync import (
    PullRequest,
    PullResult,
    PullPreview,
    ImportValidation,
    ImportedCounts,
    ConflictDetail,
    SchemaBreakingChange,
    ImportStatus,
    ConflictAction,
    SchemaCompatibility,
    BundleImportRequest
)
from schemas.cloud_sync import BundleDownloadResponse
from services.cloud_client import CloudAPIClient
from services.schema_diff_service import SchemaDiffService
from services.sync_state_service import SyncStateService
from services.import_service import ImportService
from errors import (
    CloudAPINotFoundError,
    ValidationError,
    ImportError as CustomImportError
)

logger = logging.getLogger(__name__)


class PullSyncService:
    """
    Service for pulling data from cloud to local (cloud → local sync)

    Handles:
    - Bundle download from cloud
    - Bundle validation (format, schema compatibility)
    - Conflict detection with local data
    - Import orchestration via ImportService
    - Rollback on failure
    - Watermark updates
    """

    def __init__(
        self,
        db: Session,
        cloud_client: Optional[CloudAPIClient] = None,
        schema_diff_service: Optional[SchemaDiffService] = None,
        sync_state_service: Optional[SyncStateService] = None,
        import_service: Optional[ImportService] = None
    ):
        """
        Initialize pull sync service

        Args:
            db: Database session
            cloud_client: Cloud API client (optional, creates if not provided)
            schema_diff_service: Schema diff service
            sync_state_service: Sync state service
            import_service: Import service for entity imports
        """
        self.db = db
        self.cloud_client = cloud_client
        self.schema_diff_service = schema_diff_service or SchemaDiffService()
        self.sync_state_service = sync_state_service or SyncStateService(db)
        self.import_service = import_service or ImportService(db)

    async def pull_from_cloud(
        self,
        request: PullRequest,
        api_key: str
    ) -> PullResult:
        """
        Pull data from cloud to local database

        Full workflow:
        1. Authenticate with cloud
        2. Get latest bundle metadata
        3. Download bundle
        4. Extract and parse
        5. Validate schema compatibility
        6. Detect conflicts
        7. Create snapshot for rollback
        8. Import data
        9. Update watermarks
        10. Return result

        Args:
            request: Pull request with options
            api_key: Cloud API key for authentication

        Returns:
            PullResult with import details

        Raises:
            CloudAPINotFoundError: Bundle not found
            ValidationError: Invalid bundle format
            CustomImportError: Import failed
        """
        pull_id = uuid4()
        started_at = datetime.utcnow()
        status = ImportStatus.PENDING

        logger.info(f"Starting pull sync {pull_id} for project {request.project_id}")

        result = PullResult(
            pull_id=pull_id,
            project_id=request.project_id,
            status=status,
            started_at=started_at
        )

        try:
            # Initialize cloud client if needed
            if not self.cloud_client:
                self.cloud_client = CloudAPIClient()

            # Authenticate
            async with self.cloud_client as client:
                await client.authenticate(api_key)

                # Get latest bundle for project
                bundles = await client.list_available_bundles(
                    str(request.project_id),
                    limit=1
                )

                if not bundles:
                    raise CloudAPINotFoundError(
                        f"No bundles found for project {request.project_id}"
                    )

                latest_bundle = bundles[0]
                result.bundle_id = latest_bundle.bundle_id

                # Download bundle
                logger.info(f"Downloading bundle {latest_bundle.bundle_id}")
                download_response = await client.download_bundle(
                    str(request.project_id),
                    str(latest_bundle.bundle_id)
                )

                result.bundle_size_bytes = download_response.size_bytes

                # Validate bundle
                if request.validate_schema:
                    result.status = ImportStatus.VALIDATING
                    validation = await self.validate_bundle(
                        request.project_id,
                        download_response
                    )

                    if not validation.is_valid:
                        result.status = ImportStatus.FAILED
                        result.errors = validation.errors
                        result.warnings = validation.warnings
                        result.completed_at = datetime.utcnow()
                        result.duration_seconds = (
                            result.completed_at - started_at
                        ).total_seconds()
                        return result

                    # Check for breaking changes
                    if validation.breaking_changes:
                        result.warnings.extend([
                            f"Breaking change: {bc.description}"
                            for bc in validation.breaking_changes
                        ])

                        # If breaking changes and not dry run, require explicit approval
                        if not request.dry_run and validation.compatibility_level == SchemaCompatibility.BREAKING:
                            result.status = ImportStatus.FAILED
                            result.errors.append(
                                "Breaking schema changes detected. Manual approval required."
                            )
                            result.completed_at = datetime.utcnow()
                            result.duration_seconds = (
                                result.completed_at - started_at
                            ).total_seconds()
                            return result

                # Dry run - preview only
                if request.dry_run:
                    result.status = ImportStatus.COMPLETED
                    result.warnings.append("Dry run - no changes applied")
                    result.completed_at = datetime.utcnow()
                    result.duration_seconds = (
                        result.completed_at - started_at
                    ).total_seconds()
                    return result

                # Apply bundle (import data)
                result.status = ImportStatus.IMPORTING
                import_result = await self.apply_bundle(
                    request.project_id,
                    download_response,
                    request.conflict_action
                )

                # Update result
                result.imported_counts = import_result.imported_counts
                result.conflicts = import_result.conflicts
                result.conflicts_resolved = len([
                    c for c in import_result.conflicts if c.resolution
                ])
                result.conflicts_skipped = len([
                    c for c in import_result.conflicts if not c.resolution
                ])
                result.snapshot_id = import_result.snapshot_id
                result.errors = import_result.errors

                # Check if import succeeded
                if import_result.errors:
                    result.status = ImportStatus.FAILED
                else:
                    result.status = ImportStatus.COMPLETED

                    # Update watermarks on success
                    await self._update_watermarks(
                        request.project_id,
                        download_response,
                        result.bundle_id
                    )

        except Exception as e:
            logger.error(f"Pull sync {pull_id} failed: {e}", exc_info=True)
            result.status = ImportStatus.FAILED
            result.errors.append(str(e))

        finally:
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (
                result.completed_at - started_at
            ).total_seconds()

        logger.info(
            f"Pull sync {pull_id} completed with status {result.status} "
            f"in {result.duration_seconds:.2f}s"
        )

        return result

    async def download_bundle(
        self,
        project_id: UUID,
        bundle_id: UUID,
        api_key: str
    ) -> BundleDownloadResponse:
        """
        Download bundle from cloud

        Args:
            project_id: Project UUID
            bundle_id: Bundle ID to download
            api_key: Cloud API key

        Returns:
            BundleDownloadResponse with bundle data

        Raises:
            CloudAPINotFoundError: Bundle not found
        """
        logger.info(f"Downloading bundle {bundle_id} for project {project_id}")

        if not self.cloud_client:
            self.cloud_client = CloudAPIClient()

        async with self.cloud_client as client:
            await client.authenticate(api_key)
            return await client.download_bundle(
                str(project_id),
                str(bundle_id)
            )

    async def validate_bundle(
        self,
        project_id: UUID,
        bundle: BundleDownloadResponse
    ) -> ImportValidation:
        """
        Validate bundle for import

        Checks:
        - Bundle format validity
        - Schema compatibility
        - Breaking changes
        - Estimated conflicts

        Args:
            project_id: Project UUID
            bundle: Downloaded bundle

        Returns:
            ImportValidation with validation results
        """
        logger.info(f"Validating bundle {bundle.bundle_id} for project {project_id}")

        validation = ImportValidation(
            is_valid=True,
            schema_compatible=True,
            compatibility_level=SchemaCompatibility.COMPATIBLE
        )

        try:
            # Parse manifest
            manifest = bundle.bundle_data.get("manifest", {})

            if not manifest:
                validation.is_valid = False
                validation.errors.append("Bundle missing manifest")
                return validation

            # Validate required fields
            required_fields = ["format_version", "project_id", "created_at"]
            for field in required_fields:
                if field not in manifest:
                    validation.is_valid = False
                    validation.errors.append(f"Manifest missing required field: {field}")

            if not validation.is_valid:
                return validation

            # Check schema compatibility
            if "schema" in bundle.bundle_data:
                from schemas.schema_diff import SchemaDefinition

                # Parse cloud schema
                cloud_schema = SchemaDefinition(**bundle.bundle_data["schema"])

                # Get local schema
                local_schema = await self.schema_diff_service.get_local_schema(
                    self.db,
                    project_id
                )

                # Compare schemas
                diff = self.schema_diff_service.compare_schemas(
                    local_schema,
                    cloud_schema
                )

                # Check for breaking changes
                if diff.breaking_changes:
                    validation.breaking_changes = [
                        SchemaBreakingChange(
                            table_name=bc.entity_name,
                            change_type=bc.change_type.value,
                            description=bc.description,
                            affected_columns=[bc.field_name] if bc.field_name else []
                        )
                        for bc in diff.breaking_changes
                    ]
                    validation.compatibility_level = SchemaCompatibility.BREAKING
                    validation.schema_compatible = False

                # Check if auto-migration possible
                if diff.total_changes > 0:
                    # Can auto-migrate if no breaking changes
                    validation.can_auto_migrate = len(diff.breaking_changes) == 0

                    if validation.can_auto_migrate:
                        validation.compatibility_level = SchemaCompatibility.COMPATIBLE_WITH_MIGRATION
                        validation.warnings.append(
                            f"{diff.total_changes} schema changes detected - auto-migration available"
                        )

            # Estimate conflicts
            validation.estimated_conflicts = 0

            # Check for potential data conflicts
            # This is a rough estimate based on entity counts
            if "data" in bundle.bundle_data:
                for entity_type, entity_data in bundle.bundle_data["data"].items():
                    if isinstance(entity_data, list):
                        # Assume 5% conflict rate as estimate
                        validation.estimated_conflicts += int(len(entity_data) * 0.05)

        except Exception as e:
            logger.error(f"Bundle validation failed: {e}", exc_info=True)
            validation.is_valid = False
            validation.schema_compatible = False
            validation.errors.append(f"Validation error: {str(e)}")

        return validation

    async def apply_bundle(
        self,
        project_id: UUID,
        bundle: BundleDownloadResponse,
        conflict_action: ConflictAction = ConflictAction.OVERWRITE
    ) -> Any:
        """
        Apply bundle to local database

        Orchestrates the import process:
        1. Create snapshot for rollback
        2. Import each entity type
        3. Handle conflicts based on strategy
        4. Rollback on error

        Args:
            project_id: Project UUID
            bundle: Bundle to import
            conflict_action: How to handle conflicts

        Returns:
            Import result with counts and conflicts
        """
        logger.info(f"Applying bundle {bundle.bundle_id} to project {project_id}")

        # Create import request
        import_request = BundleImportRequest(
            project_id=project_id,
            bundle_data=bundle.bundle_data,
            conflict_action=conflict_action,
            validate_first=False,  # Already validated
            create_snapshot=True
        )

        # Delegate to import service
        return await self.import_service.import_bundle(import_request)

    async def detect_conflicts(
        self,
        project_id: UUID,
        bundle: BundleDownloadResponse
    ) -> List[ConflictDetail]:
        """
        Detect conflicts between bundle and local data

        Args:
            project_id: Project UUID
            bundle: Bundle to check

        Returns:
            List of detected conflicts
        """
        conflicts: List[ConflictDetail] = []

        # Extract data from bundle
        data = bundle.bundle_data.get("data", {})

        # Check each entity type for conflicts
        for entity_type, entities in data.items():
            if entity_type == "tables":
                # Check table conflicts
                table_conflicts = await self._detect_table_conflicts(
                    project_id,
                    entities
                )
                conflicts.extend(table_conflicts)

            elif entity_type == "vectors":
                # Check vector conflicts
                vector_conflicts = await self._detect_vector_conflicts(
                    project_id,
                    entities
                )
                conflicts.extend(vector_conflicts)

        return conflicts

    async def _detect_table_conflicts(
        self,
        project_id: UUID,
        tables_data: Dict[str, Any]
    ) -> List[ConflictDetail]:
        """Detect conflicts in table data"""
        conflicts = []

        for table_name, rows in tables_data.items():
            # Check if table exists locally
            # If it does, check for row ID conflicts
            # This is a simplified implementation
            # Real implementation would query local database
            pass

        return conflicts

    async def _detect_vector_conflicts(
        self,
        project_id: UUID,
        vectors_data: List[Dict[str, Any]]
    ) -> List[ConflictDetail]:
        """Detect conflicts in vector data"""
        conflicts = []

        # Check for vector ID conflicts
        # This would query local Qdrant to check for existing vectors
        pass

        return conflicts

    async def _update_watermarks(
        self,
        project_id: UUID,
        bundle: BundleDownloadResponse,
        bundle_id: Optional[UUID]
    ) -> None:
        """
        Update sync state watermarks after successful import

        Args:
            project_id: Project UUID
            bundle: Imported bundle
            bundle_id: Bundle ID
        """
        logger.info(f"Updating watermarks for project {project_id}")

        # Extract entity counts from bundle
        data = bundle.bundle_data.get("data", {})

        for entity_type in data.keys():
            # Update watermark for each entity type
            watermark = {
                "last_pull_at": datetime.utcnow().isoformat(),
                "last_bundle_id": str(bundle_id) if bundle_id else None,
                "last_bundle_timestamp": bundle.created_at.isoformat() if bundle.created_at else None
            }

            self.sync_state_service.update_watermark(
                project_id=project_id,
                entity_type=entity_type,
                watermark_data=watermark
            )

        logger.info(f"Watermarks updated for project {project_id}")

    async def preview_pull(
        self,
        project_id: UUID,
        api_key: str
    ) -> PullPreview:
        """
        Preview what would be pulled from cloud without applying changes

        Args:
            project_id: Project UUID
            api_key: Cloud API key

        Returns:
            PullPreview with estimated changes
        """
        logger.info(f"Previewing pull for project {project_id}")

        if not self.cloud_client:
            self.cloud_client = CloudAPIClient()

        async with self.cloud_client as client:
            await client.authenticate(api_key)

            # Get latest bundle
            bundles = await client.list_available_bundles(
                str(project_id),
                limit=1
            )

            if not bundles:
                raise CloudAPINotFoundError(
                    f"No bundles found for project {project_id}"
                )

            latest_bundle = bundles[0]

            # Download bundle for preview
            bundle = await client.download_bundle(
                str(project_id),
                str(latest_bundle.bundle_id)
            )

            # Validate
            validation = await self.validate_bundle(project_id, bundle)

            # Estimate counts
            data = bundle.bundle_data.get("data", {})
            estimated_counts = ImportedCounts()

            if "tables" in data:
                estimated_counts.tables_created = len(data["tables"])
                for table_rows in data["tables"].values():
                    if isinstance(table_rows, list):
                        estimated_counts.table_rows_inserted += len(table_rows)

            if "vectors" in data:
                estimated_counts.vectors_upserted = len(data.get("vectors", []))

            if "memory" in data:
                estimated_counts.memory_inserted = len(data.get("memory", []))

            if "events" in data:
                estimated_counts.events_published = len(data.get("events", []))

            if "files" in data:
                estimated_counts.files_uploaded = len(data.get("files", []))

            estimated_counts.total_imported = (
                estimated_counts.tables_created +
                estimated_counts.table_rows_inserted +
                estimated_counts.vectors_upserted +
                estimated_counts.memory_inserted +
                estimated_counts.events_published +
                estimated_counts.files_uploaded
            )

            # Detect conflicts
            conflicts = await self.detect_conflicts(project_id, bundle)

            # Estimate duration (rough estimate: 100 records per second)
            estimated_duration = max(
                estimated_counts.total_imported / 100.0,
                1.0
            )

            preview = PullPreview(
                project_id=project_id,
                cloud_bundle_id=latest_bundle.bundle_id,
                cloud_last_modified=latest_bundle.created_at,
                estimated_counts=estimated_counts,
                estimated_size_bytes=bundle.size_bytes,
                validation=validation,
                estimated_conflicts=len(conflicts),
                estimated_duration_seconds=estimated_duration,
                requires_migration=validation.compatibility_level == SchemaCompatibility.COMPATIBLE_WITH_MIGRATION,
                safe_to_pull=validation.is_valid and not validation.breaking_changes
            )

            return preview
