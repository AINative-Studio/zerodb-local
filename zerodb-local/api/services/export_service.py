"""
Export Service
Business logic for creating export bundles for sync operations
"""
import os
import json
import zipfile
import io
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from schemas.export import (
    VectorExport,
    TableExport,
    FileExport,
    EventExport,
    MemoryExport,
    ExportBundle,
    BundleManifest,
    RecordCounts,
    ExportMetadata,
    ExportPreview
)
from services.sync_state_service import SyncStateService
from services.cdc_service import CDCService
from services.schema_diff_service import SchemaDiffService


class ExportService:
    """
    Service for creating export bundles

    Supports three export modes:
    - FULL: Export all entities in project
    - INCREMENTAL: Export only changes since last sync
    - SELECTIVE: Export specific entity types

    Bundle structure:
        bundle.zip:
          manifest.json (metadata, counts, file list)
          schema.json (schema from schema_diff_service)
          vectors.jsonl (one JSON per line)
          tables/{table_name}.jsonl
          files/{file_id}.dat + metadata.json
          events.jsonl
          memory.jsonl
    """

    def __init__(
        self,
        sync_state_service: Optional[SyncStateService] = None,
        cdc_service: Optional[CDCService] = None,
        schema_diff_service: Optional[SchemaDiffService] = None
    ):
        """
        Initialize export service

        Args:
            sync_state_service: Service for sync state tracking
            cdc_service: Service for change data capture
            schema_diff_service: Service for schema diffing
        """
        self.sync_state_service = sync_state_service
        self.cdc_service = cdc_service or CDCService()
        self.schema_diff_service = schema_diff_service
        self.export_dir = os.getenv("EXPORT_DIR", "/tmp/zerodb_exports")

        # Ensure export directory exists
        os.makedirs(self.export_dir, exist_ok=True)

    async def create_export_bundle(
        self,
        db: Session,
        project_id: UUID,
        mode: str = 'full',
        entity_types: Optional[List[str]] = None,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create complete export bundle

        Args:
            db: Database session
            project_id: Project UUID
            mode: Export mode ('full', 'incremental', 'selective')
            entity_types: Entity types for selective mode
            since_timestamp: Timestamp for incremental mode

        Returns:
            Export bundle metadata and path
        """
        export_id = uuid4()

        # Determine since_timestamp for incremental mode
        if mode == 'incremental' and not since_timestamp:
            if self.sync_state_service:
                # Get last sync timestamp from sync state
                sync_states = self.sync_state_service.list_sync_states(project_id)
                if sync_states:
                    # Use the earliest last_sync_at across all entity types
                    timestamps = [
                        s.last_sync_at for s in sync_states
                        if s.last_sync_at
                    ]
                    if timestamps:
                        since_timestamp = min(timestamps)

        # Export entities based on mode
        bundle = ExportBundle(
            manifest=BundleManifest(
                bundle_id=export_id,
                project_id=project_id,
                export_type=mode,
                created_at=datetime.utcnow(),
                entity_counts=RecordCounts(),
                files=[],
                since_timestamp=since_timestamp
            )
        )

        # Determine which entities to export
        entities_to_export = entity_types or ['vectors', 'tables', 'files', 'events', 'memory']

        # Export each entity type
        if 'vectors' in entities_to_export:
            bundle.vectors = await self.export_vectors(db, project_id, since_timestamp)
            bundle.manifest.entity_counts.vectors = len(bundle.vectors)

        if 'tables' in entities_to_export:
            bundle.tables = await self.export_tables(db, project_id, since_timestamp)
            bundle.manifest.entity_counts.tables = len(bundle.tables)
            bundle.manifest.entity_counts.table_rows = sum(
                len(t.rows) for t in bundle.tables
            )

        if 'files' in entities_to_export:
            bundle.files = await self.export_files(db, project_id, since_timestamp)
            bundle.manifest.entity_counts.files = len(bundle.files)

        if 'events' in entities_to_export:
            bundle.events = await self.export_events(db, project_id, since_timestamp)
            bundle.manifest.entity_counts.events = len(bundle.events)

        if 'memory' in entities_to_export:
            bundle.memory = await self.export_memory(db, project_id, since_timestamp)
            bundle.manifest.entity_counts.memory = len(bundle.memory)

        # Get schema definition if schema_diff_service available
        if self.schema_diff_service:
            schema_def = await self.schema_diff_service.get_local_schema(db, project_id)
            bundle.schema = schema_def.dict()

        # Package bundle as ZIP
        bundle_bytes = await self.package_bundle(bundle)

        # Save bundle to disk
        bundle_path = os.path.join(self.export_dir, f"export_{export_id}.zip")
        with open(bundle_path, 'wb') as f:
            f.write(bundle_bytes)

        # Create metadata
        metadata = ExportMetadata(
            export_id=export_id,
            project_id=project_id,
            export_type=mode,
            timestamp=datetime.utcnow(),
            record_counts=bundle.manifest.entity_counts,
            file_size_bytes=len(bundle_bytes),
            compressed=True,
            entity_types=entity_types,
            since_timestamp=since_timestamp
        )

        return {
            "export_id": export_id,
            "bundle_path": bundle_path,
            "metadata": metadata,
            "bundle_size_bytes": len(bundle_bytes)
        }

    async def export_vectors(
        self,
        db: Session,
        project_id: UUID,
        since_timestamp: Optional[datetime] = None
    ) -> List[VectorExport]:
        """
        Export vectors from project

        Args:
            db: Database session
            project_id: Project UUID
            since_timestamp: Only export vectors modified after this time

        Returns:
            List of vector export records
        """
        query = """
            SELECT
                id, vector_id, namespace, document, metadata,
                embedding, created_at, updated_at
            FROM vectors
            WHERE project_id = :project_id
            AND deleted_at IS NULL
        """
        params = {"project_id": str(project_id)}

        if since_timestamp:
            query += " AND updated_at > :since"
            params["since"] = since_timestamp

        query += " ORDER BY created_at"

        result = db.execute(text(query), params)

        vectors = []
        for row in result:
            vectors.append(VectorExport(
                vector_id=row.vector_id,
                namespace=row.namespace,
                document=row.document,
                metadata=row.metadata or {},
                embedding=row.embedding or [],
                created_at=row.created_at,
                updated_at=row.updated_at
            ))

        return vectors

    async def export_tables(
        self,
        db: Session,
        project_id: UUID,
        since_timestamp: Optional[datetime] = None
    ) -> List[TableExport]:
        """
        Export tables and their rows from project

        Args:
            db: Database session
            project_id: Project UUID
            since_timestamp: Only export tables/rows modified after this time

        Returns:
            List of table export records with rows
        """
        # Get tables
        table_query = """
            SELECT
                id, name, schema, description, created_at, updated_at
            FROM tables
            WHERE project_id = :project_id
            AND deleted_at IS NULL
        """
        table_params = {"project_id": str(project_id)}

        if since_timestamp:
            table_query += " AND updated_at > :since"
            table_params["since"] = since_timestamp

        table_query += " ORDER BY created_at"

        table_result = db.execute(text(table_query), table_params)

        tables = []
        for table_row in table_result:
            table_id = str(table_row.id)

            # Get rows for this table
            row_query = """
                SELECT id, data, created_at, updated_at
                FROM table_rows
                WHERE table_id = :table_id
                AND deleted_at IS NULL
            """
            row_params = {"table_id": table_id}

            if since_timestamp:
                row_query += " AND updated_at > :since"
                row_params["since"] = since_timestamp

            row_query += " ORDER BY created_at"

            row_result = db.execute(text(row_query), row_params)

            rows = []
            for row in row_result:
                row_data = row.data or {}
                row_data['_id'] = str(row.id)
                row_data['_created_at'] = row.created_at.isoformat()
                row_data['_updated_at'] = row.updated_at.isoformat()
                rows.append(row_data)

            tables.append(TableExport(
                table_id=table_id,
                table_name=table_row.name,
                schema=table_row.schema or {},
                description=table_row.description,
                rows=rows,
                created_at=table_row.created_at,
                updated_at=table_row.updated_at
            ))

        return tables

    async def export_files(
        self,
        db: Session,
        project_id: UUID,
        since_timestamp: Optional[datetime] = None
    ) -> List[FileExport]:
        """
        Export file metadata from project

        Note: Actual file data is stored in MinIO and exported separately

        Args:
            db: Database session
            project_id: Project UUID
            since_timestamp: Only export files modified after this time

        Returns:
            List of file export records
        """
        query = """
            SELECT
                id, file_name, content_type, folder, metadata,
                size_bytes, created_at, updated_at
            FROM files
            WHERE project_id = :project_id
            AND deleted_at IS NULL
        """
        params = {"project_id": str(project_id)}

        if since_timestamp:
            query += " AND updated_at > :since"
            params["since"] = since_timestamp

        query += " ORDER BY created_at"

        result = db.execute(text(query), params)

        files = []
        for row in result:
            files.append(FileExport(
                file_id=str(row.id),
                file_name=row.file_name,
                content_type=row.content_type,
                folder=row.folder,
                metadata=row.metadata or {},
                size_bytes=row.size_bytes or 0,
                created_at=row.created_at,
                updated_at=row.updated_at
            ))

        return files

    async def export_events(
        self,
        db: Session,
        project_id: UUID,
        since_timestamp: Optional[datetime] = None
    ) -> List[EventExport]:
        """
        Export events from project

        Args:
            db: Database session
            project_id: Project UUID
            since_timestamp: Only export events created after this time

        Returns:
            List of event export records
        """
        query = """
            SELECT
                id, event_type, event_data, source,
                correlation_id, created_at
            FROM events
            WHERE project_id = :project_id
        """
        params = {"project_id": str(project_id)}

        if since_timestamp:
            query += " AND created_at > :since"
            params["since"] = since_timestamp

        query += " ORDER BY created_at"

        result = db.execute(text(query), params)

        events = []
        for row in result:
            events.append(EventExport(
                event_id=str(row.id),
                event_type=row.event_type,
                event_data=row.event_data or {},
                source=row.source,
                correlation_id=row.correlation_id,
                created_at=row.created_at
            ))

        return events

    async def export_memory(
        self,
        db: Session,
        project_id: UUID,
        since_timestamp: Optional[datetime] = None
    ) -> List[MemoryExport]:
        """
        Export memory records from project

        Args:
            db: Database session
            project_id: Project UUID
            since_timestamp: Only export memory created after this time

        Returns:
            List of memory export records
        """
        query = """
            SELECT
                id, agent_id, session_id, role, content,
                metadata, embedding, created_at
            FROM memory
            WHERE project_id = :project_id
        """
        params = {"project_id": str(project_id)}

        if since_timestamp:
            query += " AND created_at > :since"
            params["since"] = since_timestamp

        query += " ORDER BY created_at"

        result = db.execute(text(query), params)

        memories = []
        for row in result:
            memories.append(MemoryExport(
                memory_id=str(row.id),
                agent_id=row.agent_id,
                session_id=row.session_id,
                role=row.role,
                content=row.content,
                metadata=row.metadata or {},
                embedding=row.embedding,
                created_at=row.created_at
            ))

        return memories

    async def package_bundle(
        self,
        bundle: ExportBundle
    ) -> bytes:
        """
        Package export bundle as ZIP file

        Creates a ZIP with the following structure:
        - manifest.json
        - schema.json (if available)
        - vectors.jsonl
        - tables/{table_name}.jsonl
        - events.jsonl
        - memory.jsonl
        - files/metadata.json

        Args:
            bundle: Export bundle to package

        Returns:
            ZIP file as bytes
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            bundle.manifest.files = []

            # Add schema if available
            if bundle.schema:
                schema_json = json.dumps(bundle.schema, indent=2, default=str)
                zf.writestr('schema.json', schema_json)
                bundle.manifest.files.append('schema.json')

            # Add vectors as JSONL
            if bundle.vectors:
                vectors_lines = []
                for vector in bundle.vectors:
                    vectors_lines.append(
                        json.dumps(vector.dict(), default=str)
                    )
                zf.writestr('vectors.jsonl', '\n'.join(vectors_lines))
                bundle.manifest.files.append('vectors.jsonl')

            # Add tables as separate JSONL files
            if bundle.tables:
                os.makedirs('tables', exist_ok=True)
                for table in bundle.tables:
                    table_file = f"tables/{table.table_name}.jsonl"

                    # Write table metadata and rows
                    table_lines = []

                    # First line: table metadata
                    table_meta = {
                        "table_id": table.table_id,
                        "table_name": table.table_name,
                        "schema": table.schema,
                        "description": table.description,
                        "created_at": table.created_at.isoformat(),
                        "updated_at": table.updated_at.isoformat(),
                        "row_count": len(table.rows)
                    }
                    table_lines.append(json.dumps(table_meta, default=str))

                    # Subsequent lines: rows
                    for row in table.rows:
                        table_lines.append(json.dumps(row, default=str))

                    zf.writestr(table_file, '\n'.join(table_lines))
                    bundle.manifest.files.append(table_file)

            # Add events as JSONL
            if bundle.events:
                events_lines = []
                for event in bundle.events:
                    events_lines.append(
                        json.dumps(event.dict(), default=str)
                    )
                zf.writestr('events.jsonl', '\n'.join(events_lines))
                bundle.manifest.files.append('events.jsonl')

            # Add memory as JSONL
            if bundle.memory:
                memory_lines = []
                for mem in bundle.memory:
                    memory_lines.append(
                        json.dumps(mem.dict(), default=str)
                    )
                zf.writestr('memory.jsonl', '\n'.join(memory_lines))
                bundle.manifest.files.append('memory.jsonl')

            # Add file metadata
            if bundle.files:
                files_metadata = []
                for file in bundle.files:
                    files_metadata.append(file.dict())

                zf.writestr(
                    'files/metadata.json',
                    json.dumps(files_metadata, indent=2, default=str)
                )
                bundle.manifest.files.append('files/metadata.json')

            # Write manifest last (includes file list)
            manifest_json = json.dumps(
                bundle.manifest.dict(),
                indent=2,
                default=str
            )
            zf.writestr('manifest.json', manifest_json)

        zip_buffer.seek(0)
        return zip_buffer.read()

    async def preview_export(
        self,
        db: Session,
        project_id: UUID,
        mode: str = 'full',
        entity_types: Optional[List[str]] = None,
        since_timestamp: Optional[datetime] = None
    ) -> ExportPreview:
        """
        Preview what would be exported without creating the bundle

        Args:
            db: Database session
            project_id: Project UUID
            mode: Export mode
            entity_types: Entity types to include
            since_timestamp: Timestamp for incremental

        Returns:
            Export preview with estimated counts and size
        """
        counts = RecordCounts()
        estimated_size = 0

        entities_to_check = entity_types or ['vectors', 'tables', 'files', 'events', 'memory']

        # Count vectors
        if 'vectors' in entities_to_check:
            vector_count_query = """
                SELECT COUNT(*) as count
                FROM vectors
                WHERE project_id = :project_id
                AND deleted_at IS NULL
            """
            params = {"project_id": str(project_id)}
            if since_timestamp:
                vector_count_query += " AND updated_at > :since"
                params["since"] = since_timestamp

            result = db.execute(text(vector_count_query), params)
            counts.vectors = result.scalar() or 0
            estimated_size += counts.vectors * 2048  # ~2KB per vector

        # Count tables and rows
        if 'tables' in entities_to_check:
            table_count_query = """
                SELECT COUNT(*) as count
                FROM tables
                WHERE project_id = :project_id
                AND deleted_at IS NULL
            """
            params = {"project_id": str(project_id)}
            if since_timestamp:
                table_count_query += " AND updated_at > :since"
                params["since"] = since_timestamp

            result = db.execute(text(table_count_query), params)
            counts.tables = result.scalar() or 0

            # Count total rows across all tables
            row_count_query = """
                SELECT COUNT(*) as count
                FROM table_rows tr
                JOIN tables t ON tr.table_id = t.id
                WHERE t.project_id = :project_id
                AND tr.deleted_at IS NULL
            """
            result = db.execute(text(row_count_query), {"project_id": str(project_id)})
            counts.table_rows = result.scalar() or 0
            estimated_size += counts.table_rows * 512  # ~512B per row

        # Count files
        if 'files' in entities_to_check:
            file_count_query = """
                SELECT COUNT(*) as count
                FROM files
                WHERE project_id = :project_id
                AND deleted_at IS NULL
            """
            params = {"project_id": str(project_id)}
            if since_timestamp:
                file_count_query += " AND updated_at > :since"
                params["since"] = since_timestamp

            result = db.execute(text(file_count_query), params)
            counts.files = result.scalar() or 0
            estimated_size += counts.files * 1024  # ~1KB per file metadata

        # Count events
        if 'events' in entities_to_check:
            event_count_query = """
                SELECT COUNT(*) as count
                FROM events
                WHERE project_id = :project_id
            """
            params = {"project_id": str(project_id)}
            if since_timestamp:
                event_count_query += " AND created_at > :since"
                params["since"] = since_timestamp

            result = db.execute(text(event_count_query), params)
            counts.events = result.scalar() or 0
            estimated_size += counts.events * 256  # ~256B per event

        # Count memory
        if 'memory' in entities_to_check:
            memory_count_query = """
                SELECT COUNT(*) as count
                FROM memory
                WHERE project_id = :project_id
            """
            params = {"project_id": str(project_id)}
            if since_timestamp:
                memory_count_query += " AND created_at > :since"
                params["since"] = since_timestamp

            result = db.execute(text(memory_count_query), params)
            counts.memory = result.scalar() or 0
            estimated_size += counts.memory * 1024  # ~1KB per memory

        return ExportPreview(
            project_id=project_id,
            export_type=mode,
            estimated_counts=counts,
            estimated_size_bytes=estimated_size,
            since_timestamp=since_timestamp,
            entity_types=entity_types
        )


# Singleton instance
export_service = ExportService()
