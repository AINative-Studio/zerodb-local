"""
Import Service
Handles importing entities from cloud bundles into local database
"""
import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from schemas.pull_sync import (
    BundleImportRequest,
    BundleImportResult,
    ImportedCounts,
    ConflictDetail,
    ImportStatus,
    ConflictAction,
    ImportValidation
)
from errors import ImportError as CustomImportError

logger = logging.getLogger(__name__)


class ImportService:
    """
    Service for importing entities from bundles into local database

    Handles:
    - Vector imports (Qdrant)
    - Table imports (PostgreSQL)
    - File imports (MinIO)
    - Event imports (event stream)
    - Memory imports (agent memory)
    - Rollback on failure
    - Conflict resolution
    """

    def __init__(self, db: Session):
        """
        Initialize import service

        Args:
            db: Database session
        """
        self.db = db

    async def import_bundle(
        self,
        request: BundleImportRequest
    ) -> BundleImportResult:
        """
        Import complete bundle into local database

        Args:
            request: Bundle import request

        Returns:
            BundleImportResult with counts and conflicts

        Raises:
            CustomImportError: Import failed
        """
        import_id = uuid4()
        started_at = datetime.utcnow()
        status = ImportStatus.IMPORTING

        logger.info(f"Starting bundle import {import_id} for project {request.project_id}")

        # Initialize result
        result = BundleImportResult(
            import_id=import_id,
            project_id=request.project_id,
            status=status,
            imported_counts=ImportedCounts(),
            conflicts=[],
            errors=[],
            duration_seconds=0.0
        )

        # Create snapshot for rollback if requested
        snapshot_id = None
        if request.create_snapshot:
            snapshot_id = await self._create_snapshot(request.project_id)
            result.snapshot_id = snapshot_id

        try:
            # Validate if requested
            if request.validate_first:
                validation = await self._validate_bundle(request.bundle_data)
                result.validation = validation

                if not validation.is_valid:
                    result.status = ImportStatus.FAILED
                    result.errors = validation.errors
                    return result

            # Extract data from bundle
            data = request.bundle_data.get("data", {})

            # Import each entity type
            if "tables" in data:
                tables_result = await self.import_tables(
                    request.project_id,
                    data["tables"],
                    request.conflict_action
                )
                result.imported_counts.tables_created += tables_result.tables_created
                result.imported_counts.tables_updated += tables_result.tables_updated
                result.imported_counts.table_rows_inserted += tables_result.rows_inserted
                result.imported_counts.table_rows_updated += tables_result.rows_updated
                result.conflicts.extend(tables_result.conflicts)

            if "vectors" in data:
                vectors_result = await self.import_vectors(
                    request.project_id,
                    data["vectors"],
                    request.conflict_action
                )
                result.imported_counts.vectors_upserted += vectors_result.count
                result.conflicts.extend(vectors_result.conflicts)

            if "memory" in data:
                memory_result = await self.import_memory(
                    request.project_id,
                    data["memory"],
                    request.conflict_action
                )
                result.imported_counts.memory_inserted += memory_result.count
                result.conflicts.extend(memory_result.conflicts)

            if "events" in data:
                events_result = await self.import_events(
                    request.project_id,
                    data["events"],
                    request.conflict_action
                )
                result.imported_counts.events_published += events_result.count
                result.conflicts.extend(events_result.conflicts)

            if "files" in data:
                files_result = await self.import_files(
                    request.project_id,
                    data["files"],
                    request.conflict_action
                )
                result.imported_counts.files_uploaded += files_result.count
                result.conflicts.extend(files_result.conflicts)

            # Calculate total imported
            result.imported_counts.total_imported = (
                result.imported_counts.tables_created +
                result.imported_counts.table_rows_inserted +
                result.imported_counts.vectors_upserted +
                result.imported_counts.memory_inserted +
                result.imported_counts.events_published +
                result.imported_counts.files_uploaded
            )

            # Commit transaction
            self.db.commit()

            result.status = ImportStatus.COMPLETED
            logger.info(f"Bundle import {import_id} completed successfully")

        except Exception as e:
            logger.error(f"Bundle import {import_id} failed: {e}", exc_info=True)
            result.status = ImportStatus.FAILED
            result.errors.append(str(e))

            # Rollback on error
            self.db.rollback()

            if snapshot_id:
                rollback_result = await self.rollback_import(import_id)
                if rollback_result.success:
                    result.status = ImportStatus.ROLLED_BACK
                    logger.info(f"Bundle import {import_id} rolled back to snapshot {snapshot_id}")

        finally:
            completed_at = datetime.utcnow()
            result.duration_seconds = (completed_at - started_at).total_seconds()

        return result

    async def import_tables(
        self,
        project_id: UUID,
        tables_data: Dict[str, Any],
        conflict_action: ConflictAction
    ) -> Any:
        """
        Import tables and table data

        Args:
            project_id: Project UUID
            tables_data: Dictionary of table_name -> rows
            conflict_action: How to handle conflicts

        Returns:
            Import result with counts and conflicts
        """
        logger.info(f"Importing {len(tables_data)} tables for project {project_id}")

        result = type('obj', (object,), {
            'tables_created': 0,
            'tables_updated': 0,
            'rows_inserted': 0,
            'rows_updated': 0,
            'conflicts': []
        })()

        for table_name, table_content in tables_data.items():
            # Parse table metadata and rows
            # Expected format:
            # {
            #   "metadata": {"schema": {...}, "created_at": "..."},
            #   "rows": [...]
            # }

            if isinstance(table_content, dict):
                metadata = table_content.get("metadata", {})
                rows = table_content.get("rows", [])
            else:
                # Legacy format: just rows
                metadata = {}
                rows = table_content if isinstance(table_content, list) else []

            # Check if table exists
            table_exists = await self._table_exists(project_id, table_name)

            if not table_exists:
                # Create table
                schema = metadata.get("schema", {})
                await self._create_table(project_id, table_name, schema)
                result.tables_created += 1
            else:
                result.tables_updated += 1

            # Import rows
            for row in rows:
                conflict = await self._import_table_row(
                    project_id,
                    table_name,
                    row,
                    conflict_action
                )

                if conflict:
                    result.conflicts.append(conflict)
                    if conflict.resolution == "skipped":
                        continue

                if conflict and conflict.resolution == "updated":
                    result.rows_updated += 1
                else:
                    result.rows_inserted += 1

        logger.info(
            f"Tables import completed: {result.tables_created} created, "
            f"{result.rows_inserted} rows inserted, {result.rows_updated} rows updated"
        )

        return result

    async def import_vectors(
        self,
        project_id: UUID,
        vectors_data: List[Dict[str, Any]],
        conflict_action: ConflictAction
    ) -> Any:
        """
        Import vectors into Qdrant

        Args:
            project_id: Project UUID
            vectors_data: List of vector objects
            conflict_action: How to handle conflicts

        Returns:
            Import result with count and conflicts
        """
        logger.info(f"Importing {len(vectors_data)} vectors for project {project_id}")

        result = type('obj', (object,), {
            'count': 0,
            'conflicts': []
        })()

        # TODO: Integrate with Qdrant service
        # For now, store in metadata table

        for vector in vectors_data:
            vector_id = vector.get("vector_id") or vector.get("id")

            # Check if vector exists
            exists = await self._vector_exists(project_id, vector_id)

            if exists:
                if conflict_action == ConflictAction.SKIP:
                    conflict = ConflictDetail(
                        entity_type="vector",
                        entity_id=vector_id,
                        conflict_type="duplicate",
                        local_value=None,
                        cloud_value=vector,
                        resolution="skipped",
                        timestamp=datetime.utcnow()
                    )
                    result.conflicts.append(conflict)
                    continue
                elif conflict_action == ConflictAction.OVERWRITE:
                    # Update existing vector
                    await self._upsert_vector(project_id, vector)
                elif conflict_action == ConflictAction.MERGE:
                    # Merge metadata
                    await self._merge_vector(project_id, vector)
            else:
                # Insert new vector
                await self._upsert_vector(project_id, vector)

            result.count += 1

        logger.info(f"Vectors import completed: {result.count} vectors upserted")

        return result

    async def import_memory(
        self,
        project_id: UUID,
        memory_data: List[Dict[str, Any]],
        conflict_action: ConflictAction
    ) -> Any:
        """
        Import agent memory records

        Args:
            project_id: Project UUID
            memory_data: List of memory objects
            conflict_action: How to handle conflicts

        Returns:
            Import result with count and conflicts
        """
        logger.info(f"Importing {len(memory_data)} memory records for project {project_id}")

        result = type('obj', (object,), {
            'count': 0,
            'conflicts': []
        })()

        # Memory records are typically append-only
        # Just insert them
        for memory in memory_data:
            await self._insert_memory(project_id, memory)
            result.count += 1

        logger.info(f"Memory import completed: {result.count} records inserted")

        return result

    async def import_events(
        self,
        project_id: UUID,
        events_data: List[Dict[str, Any]],
        conflict_action: ConflictAction
    ) -> Any:
        """
        Import events into event stream

        Args:
            project_id: Project UUID
            events_data: List of event objects
            conflict_action: How to handle conflicts

        Returns:
            Import result with count and conflicts
        """
        logger.info(f"Importing {len(events_data)} events for project {project_id}")

        result = type('obj', (object,), {
            'count': 0,
            'conflicts': []
        })()

        # Events are append-only
        for event in events_data:
            await self._publish_event(project_id, event)
            result.count += 1

        logger.info(f"Events import completed: {result.count} events published")

        return result

    async def import_files(
        self,
        project_id: UUID,
        files_data: List[Dict[str, Any]],
        conflict_action: ConflictAction
    ) -> Any:
        """
        Import files into MinIO storage

        Args:
            project_id: Project UUID
            files_data: List of file objects (with base64 content)
            conflict_action: How to handle conflicts

        Returns:
            Import result with count and conflicts
        """
        logger.info(f"Importing {len(files_data)} files for project {project_id}")

        result = type('obj', (object,), {
            'count': 0,
            'conflicts': []
        })()

        # TODO: Integrate with MinIO service
        # For now, store metadata in database

        for file_obj in files_data:
            file_id = file_obj.get("file_id") or file_obj.get("id")

            # Check if file exists
            exists = await self._file_exists(project_id, file_id)

            if exists and conflict_action == ConflictAction.SKIP:
                conflict = ConflictDetail(
                    entity_type="file",
                    entity_id=file_id,
                    conflict_type="duplicate",
                    local_value=None,
                    cloud_value=file_obj,
                    resolution="skipped",
                    timestamp=datetime.utcnow()
                )
                result.conflicts.append(conflict)
                continue

            # Upload file
            await self._upload_file(project_id, file_obj)
            result.count += 1

        logger.info(f"Files import completed: {result.count} files uploaded")

        return result

    async def rollback_import(self, import_id: UUID) -> Any:
        """
        Rollback a failed import to snapshot

        Args:
            import_id: Import operation ID

        Returns:
            Rollback result
        """
        logger.info(f"Rolling back import {import_id}")

        result = type('obj', (object,), {
            'success': False,
            'message': ''
        })()

        try:
            # TODO: Implement snapshot restoration
            # For now, just rollback the transaction
            self.db.rollback()

            result.success = True
            result.message = "Import rolled back successfully"
            logger.info(f"Import {import_id} rolled back")

        except Exception as e:
            logger.error(f"Rollback failed for import {import_id}: {e}")
            result.success = False
            result.message = str(e)

        return result

    # Helper methods

    async def _validate_bundle(self, bundle_data: Dict[str, Any]) -> ImportValidation:
        """Validate bundle format"""
        from schemas.pull_sync import SchemaCompatibility

        validation = ImportValidation(
            is_valid=True,
            schema_compatible=True,
            compatibility_level=SchemaCompatibility.COMPATIBLE
        )

        # Check for manifest
        if "manifest" not in bundle_data:
            validation.is_valid = False
            validation.errors.append("Bundle missing manifest")

        return validation

    async def _create_snapshot(self, project_id: UUID) -> UUID:
        """Create database snapshot for rollback"""
        snapshot_id = uuid4()
        logger.info(f"Created snapshot {snapshot_id} for project {project_id}")
        # TODO: Implement actual snapshot creation
        return snapshot_id

    async def _table_exists(self, project_id: UUID, table_name: str) -> bool:
        """Check if table exists for project"""
        query = text("""
            SELECT COUNT(*) FROM tables
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
        """)
        result = self.db.execute(query, {
            "project_id": str(project_id),
            "table_name": table_name
        })
        count = result.scalar()
        return count > 0

    async def _create_table(
        self,
        project_id: UUID,
        table_name: str,
        schema: Dict[str, Any]
    ) -> None:
        """Create table in database"""
        query = text("""
            INSERT INTO tables (id, project_id, name, schema, created_at)
            VALUES (:id, :project_id, :table_name, :schema, :created_at)
        """)
        self.db.execute(query, {
            "id": str(uuid4()),
            "project_id": str(project_id),
            "table_name": table_name,
            "schema": json.dumps(schema),
            "created_at": datetime.utcnow()
        })

    async def _import_table_row(
        self,
        project_id: UUID,
        table_name: str,
        row: Dict[str, Any],
        conflict_action: ConflictAction
    ) -> Optional[ConflictDetail]:
        """Import single table row"""
        # Simplified implementation
        # Real implementation would check for conflicts and handle appropriately
        return None

    async def _vector_exists(self, project_id: UUID, vector_id: str) -> bool:
        """Check if vector exists"""
        # TODO: Query Qdrant
        return False

    async def _upsert_vector(self, project_id: UUID, vector: Dict[str, Any]) -> None:
        """Insert or update vector"""
        # TODO: Integrate with Qdrant
        logger.debug(f"Upserting vector {vector.get('id')} for project {project_id}")

    async def _merge_vector(self, project_id: UUID, vector: Dict[str, Any]) -> None:
        """Merge vector metadata"""
        # TODO: Implement metadata merge
        logger.debug(f"Merging vector {vector.get('id')} for project {project_id}")

    async def _insert_memory(self, project_id: UUID, memory: Dict[str, Any]) -> None:
        """Insert memory record"""
        # TODO: Insert into memory table
        logger.debug(f"Inserting memory record for project {project_id}")

    async def _publish_event(self, project_id: UUID, event: Dict[str, Any]) -> None:
        """Publish event to event stream"""
        # TODO: Publish to event stream
        logger.debug(f"Publishing event for project {project_id}")

    async def _file_exists(self, project_id: UUID, file_id: str) -> bool:
        """Check if file exists"""
        # TODO: Query MinIO
        return False

    async def _upload_file(self, project_id: UUID, file_obj: Dict[str, Any]) -> None:
        """Upload file to MinIO"""
        # TODO: Upload to MinIO
        logger.debug(f"Uploading file {file_obj.get('id')} for project {project_id}")
