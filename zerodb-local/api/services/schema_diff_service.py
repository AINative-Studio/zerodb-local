"""
Schema Diff Service
Handles schema comparison between local and cloud databases
"""
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
import logging

from schemas.schema_diff import (
    SchemaDefinition,
    TableDefinition,
    ColumnDefinition,
    IndexDefinition,
    ConstraintDefinition,
    VectorCollectionDefinition,
    BucketDefinition,
    SchemaDiff,
    SchemaChange,
    BreakingChange,
    MigrationPlan,
    MigrationStep,
    ChangeType,
    ChangeSeverity
)

logger = logging.getLogger(__name__)


class SchemaDiffService:
    """
    Service for comparing and diffing database schemas

    Handles:
    - PostgreSQL table schema comparison
    - Qdrant vector collection comparison
    - MinIO bucket policy comparison
    - Breaking change detection
    - Migration plan generation
    """

    def __init__(self, qdrant_service=None, minio_service=None):
        """
        Initialize schema diff service

        Args:
            qdrant_service: Optional Qdrant service for vector collection introspection
            minio_service: Optional MinIO service for bucket introspection
        """
        self.qdrant_service = qdrant_service
        self.minio_service = minio_service

    async def get_local_schema(
        self,
        db: Session,
        project_id: UUID
    ) -> SchemaDefinition:
        """
        Get current local schema for a project

        Introspects:
        - PostgreSQL tables, columns, indexes, constraints
        - Qdrant vector collections
        - MinIO buckets

        Args:
            db: Database session
            project_id: Project UUID

        Returns:
            Complete schema definition
        """
        schema = SchemaDefinition(
            project_id=str(project_id),
            snapshot_timestamp=datetime.utcnow()
        )

        # Get PostgreSQL table schemas
        schema.tables = await self._get_postgres_tables(db, project_id)

        # Get Qdrant vector collections (if service available)
        if self.qdrant_service:
            schema.vector_collections = await self._get_qdrant_collections(project_id)

        # Get MinIO buckets (if service available)
        if self.minio_service:
            schema.buckets = await self._get_minio_buckets(project_id)

        return schema

    async def _get_postgres_tables(
        self,
        db: Session,
        project_id: UUID
    ) -> Dict[str, TableDefinition]:
        """
        Get PostgreSQL table definitions for project

        Args:
            db: Database session
            project_id: Project UUID

        Returns:
            Dictionary of table name -> TableDefinition
        """
        tables: Dict[str, TableDefinition] = {}

        # Get all tables for this project from our metadata
        query = text("""
            SELECT name, schema
            FROM tables
            WHERE project_id = :project_id
            AND deleted_at IS NULL
            ORDER BY name
        """)

        result = db.execute(query, {"project_id": str(project_id)})
        rows = result.fetchall()

        for row in rows:
            table_name = row.name
            table_schema = row.schema or {}

            # Build column definitions
            columns = {}
            fields = table_schema.get('fields', {})

            for field_name, field_def in fields.items():
                columns[field_name] = ColumnDefinition(
                    name=field_name,
                    data_type=field_def.get('type', 'text'),
                    nullable=field_def.get('nullable', True),
                    default=field_def.get('default'),
                    is_primary_key=field_def.get('is_primary_key', False),
                    is_foreign_key=field_def.get('is_foreign_key', False),
                    foreign_key_table=field_def.get('foreign_key_table'),
                    foreign_key_column=field_def.get('foreign_key_column')
                )

            # Build index definitions
            indexes = []
            for idx in table_schema.get('indexes', []):
                indexes.append(IndexDefinition(
                    name=idx.get('name', f"idx_{table_name}"),
                    columns=idx.get('columns', []),
                    unique=idx.get('unique', False),
                    index_type=idx.get('type', 'btree')
                ))

            # Build constraint definitions
            constraints = []
            for constraint in table_schema.get('constraints', []):
                constraints.append(ConstraintDefinition(
                    name=constraint.get('name', ''),
                    constraint_type=constraint.get('type', 'check'),
                    columns=constraint.get('columns', []),
                    referenced_table=constraint.get('referenced_table'),
                    referenced_columns=constraint.get('referenced_columns'),
                    check_expression=constraint.get('check_expression')
                ))

            # Get row count
            count_query = text(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE project_id = :project_id
                AND deleted_at IS NULL
            """)
            count_result = db.execute(count_query, {"project_id": str(project_id)})
            row_count = count_result.scalar()

            tables[table_name] = TableDefinition(
                name=table_name,
                columns=columns,
                indexes=indexes,
                constraints=constraints,
                row_count=row_count
            )

        return tables

    async def _get_qdrant_collections(
        self,
        project_id: UUID
    ) -> Dict[str, VectorCollectionDefinition]:
        """
        Get Qdrant vector collection definitions

        Args:
            project_id: Project UUID

        Returns:
            Dictionary of collection name -> VectorCollectionDefinition
        """
        collections: Dict[str, VectorCollectionDefinition] = {}

        if not self.qdrant_service:
            return collections

        try:
            # List all collections for this project
            project_collections = await self.qdrant_service.list_collections(project_id)

            for collection_name in project_collections:
                # Get collection info
                info = await self.qdrant_service.get_collection_info(collection_name)

                collections[collection_name] = VectorCollectionDefinition(
                    name=collection_name,
                    vector_dimension=info.get('vector_dimension', 1536),
                    distance_metric=info.get('distance_metric', 'cosine'),
                    vector_count=info.get('vector_count', 0),
                    index_type=info.get('index_type'),
                    hnsw_config=info.get('hnsw_config')
                )
        except Exception as e:
            logger.warning(f"Failed to get Qdrant collections: {e}")

        return collections

    async def _get_minio_buckets(
        self,
        project_id: UUID
    ) -> Dict[str, BucketDefinition]:
        """
        Get MinIO bucket definitions

        Args:
            project_id: Project UUID

        Returns:
            Dictionary of bucket name -> BucketDefinition
        """
        buckets: Dict[str, BucketDefinition] = {}

        if not self.minio_service:
            return buckets

        try:
            # List buckets for this project
            project_buckets = await self.minio_service.list_buckets(project_id)

            for bucket_name in project_buckets:
                # Get bucket info
                info = await self.minio_service.get_bucket_info(bucket_name)

                buckets[bucket_name] = BucketDefinition(
                    name=bucket_name,
                    policy=info.get('policy'),
                    versioning_enabled=info.get('versioning_enabled', False),
                    object_count=info.get('object_count', 0),
                    total_size_bytes=info.get('total_size_bytes', 0)
                )
        except Exception as e:
            logger.warning(f"Failed to get MinIO buckets: {e}")

        return buckets

    def parse_cloud_schema(self, cloud_export: Dict[str, Any]) -> SchemaDefinition:
        """
        Parse cloud schema from export format

        Args:
            cloud_export: Cloud schema export dictionary

        Returns:
            SchemaDefinition parsed from export
        """
        return SchemaDefinition(**cloud_export)

    def compare_schemas(
        self,
        local_schema: SchemaDefinition,
        cloud_schema: SchemaDefinition
    ) -> SchemaDiff:
        """
        Compare local and cloud schemas to detect differences

        Args:
            local_schema: Local database schema
            cloud_schema: Cloud database schema

        Returns:
            SchemaDiff with all detected changes
        """
        diff = SchemaDiff(
            local_schema=local_schema,
            cloud_schema=cloud_schema,
            compared_at=datetime.utcnow()
        )

        # Compare PostgreSQL tables
        self._compare_tables(diff, local_schema, cloud_schema)

        # Compare vector collections
        self._compare_vector_collections(diff, local_schema, cloud_schema)

        # Compare buckets
        self._compare_buckets(diff, local_schema, cloud_schema)

        # Detect breaking changes
        diff.breaking_changes = self.detect_breaking_changes(diff)
        diff.has_breaking_changes = len(diff.breaking_changes) > 0

        # Calculate total changes
        diff.total_changes = (
            len(diff.added_changes) +
            len(diff.removed_changes) +
            len(diff.modified_changes)
        )

        return diff

    def _compare_tables(
        self,
        diff: SchemaDiff,
        local_schema: SchemaDefinition,
        cloud_schema: SchemaDefinition
    ) -> None:
        """
        Compare PostgreSQL tables between schemas

        Args:
            diff: SchemaDiff to populate
            local_schema: Local schema
            cloud_schema: Cloud schema
        """
        local_tables = set(local_schema.tables.keys())
        cloud_tables = set(cloud_schema.tables.keys())

        # New tables in cloud (not in local)
        for table_name in cloud_tables - local_tables:
            diff.added_changes.append(SchemaChange(
                change_type=ChangeType.TABLE_ADDED,
                severity=ChangeSeverity.INFO,
                entity_type="table",
                entity_name=table_name,
                new_value=cloud_schema.tables[table_name].dict(),
                description=f"Table '{table_name}' exists in cloud but not in local"
            ))

        # Removed tables (in local but not cloud)
        for table_name in local_tables - cloud_tables:
            diff.removed_changes.append(SchemaChange(
                change_type=ChangeType.TABLE_REMOVED,
                severity=ChangeSeverity.CRITICAL,
                entity_type="table",
                entity_name=table_name,
                old_value=local_schema.tables[table_name].dict(),
                description=f"Table '{table_name}' exists in local but not in cloud"
            ))

        # Compare common tables
        for table_name in local_tables & cloud_tables:
            local_table = local_schema.tables[table_name]
            cloud_table = cloud_schema.tables[table_name]

            self._compare_columns(diff, table_name, local_table, cloud_table)
            self._compare_indexes(diff, table_name, local_table, cloud_table)

    def _compare_columns(
        self,
        diff: SchemaDiff,
        table_name: str,
        local_table: TableDefinition,
        cloud_table: TableDefinition
    ) -> None:
        """
        Compare columns between local and cloud table

        Args:
            diff: SchemaDiff to populate
            table_name: Name of table being compared
            local_table: Local table definition
            cloud_table: Cloud table definition
        """
        local_cols = set(local_table.columns.keys())
        cloud_cols = set(cloud_table.columns.keys())

        # New columns in cloud
        for col_name in cloud_cols - local_cols:
            diff.added_changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                severity=ChangeSeverity.INFO,
                entity_type="table",
                entity_name=table_name,
                field_name=col_name,
                new_value=cloud_table.columns[col_name].dict(),
                description=f"Column '{col_name}' added to table '{table_name}'"
            ))

        # Removed columns (in local but not cloud)
        for col_name in local_cols - cloud_cols:
            diff.removed_changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                severity=ChangeSeverity.CRITICAL,
                entity_type="table",
                entity_name=table_name,
                field_name=col_name,
                old_value=local_table.columns[col_name].dict(),
                description=f"Column '{col_name}' removed from table '{table_name}'"
            ))

        # Compare common columns
        for col_name in local_cols & cloud_cols:
            local_col = local_table.columns[col_name]
            cloud_col = cloud_table.columns[col_name]

            # Type changed
            if local_col.data_type != cloud_col.data_type:
                diff.modified_changes.append(SchemaChange(
                    change_type=ChangeType.COLUMN_TYPE_CHANGED,
                    severity=ChangeSeverity.CRITICAL,
                    entity_type="table",
                    entity_name=table_name,
                    field_name=col_name,
                    old_value=local_col.data_type,
                    new_value=cloud_col.data_type,
                    description=f"Column '{col_name}' type changed from {local_col.data_type} to {cloud_col.data_type}"
                ))

            # Nullable changed
            if local_col.nullable != cloud_col.nullable:
                severity = ChangeSeverity.CRITICAL if not cloud_col.nullable else ChangeSeverity.WARNING
                diff.modified_changes.append(SchemaChange(
                    change_type=ChangeType.COLUMN_NULLABLE_CHANGED,
                    severity=severity,
                    entity_type="table",
                    entity_name=table_name,
                    field_name=col_name,
                    old_value=local_col.nullable,
                    new_value=cloud_col.nullable,
                    description=f"Column '{col_name}' nullable changed from {local_col.nullable} to {cloud_col.nullable}"
                ))

    def _compare_indexes(
        self,
        diff: SchemaDiff,
        table_name: str,
        local_table: TableDefinition,
        cloud_table: TableDefinition
    ) -> None:
        """
        Compare indexes between local and cloud table

        Args:
            diff: SchemaDiff to populate
            table_name: Name of table being compared
            local_table: Local table definition
            cloud_table: Cloud table definition
        """
        local_idx_names = {idx.name for idx in local_table.indexes}
        cloud_idx_names = {idx.name for idx in cloud_table.indexes}

        # New indexes
        for idx_name in cloud_idx_names - local_idx_names:
            cloud_idx = next(idx for idx in cloud_table.indexes if idx.name == idx_name)
            diff.added_changes.append(SchemaChange(
                change_type=ChangeType.INDEX_ADDED,
                severity=ChangeSeverity.INFO,
                entity_type="table",
                entity_name=table_name,
                field_name=idx_name,
                new_value=cloud_idx.dict(),
                description=f"Index '{idx_name}' added to table '{table_name}'"
            ))

        # Removed indexes
        for idx_name in local_idx_names - cloud_idx_names:
            local_idx = next(idx for idx in local_table.indexes if idx.name == idx_name)
            diff.removed_changes.append(SchemaChange(
                change_type=ChangeType.INDEX_REMOVED,
                severity=ChangeSeverity.WARNING,
                entity_type="table",
                entity_name=table_name,
                field_name=idx_name,
                old_value=local_idx.dict(),
                description=f"Index '{idx_name}' removed from table '{table_name}'"
            ))

    def _compare_vector_collections(
        self,
        diff: SchemaDiff,
        local_schema: SchemaDefinition,
        cloud_schema: SchemaDefinition
    ) -> None:
        """
        Compare Qdrant vector collections

        Args:
            diff: SchemaDiff to populate
            local_schema: Local schema
            cloud_schema: Cloud schema
        """
        local_collections = set(local_schema.vector_collections.keys())
        cloud_collections = set(cloud_schema.vector_collections.keys())

        # New collections
        for coll_name in cloud_collections - local_collections:
            diff.added_changes.append(SchemaChange(
                change_type=ChangeType.VECTOR_INDEX_ADDED,
                severity=ChangeSeverity.INFO,
                entity_type="vector_collection",
                entity_name=coll_name,
                new_value=cloud_schema.vector_collections[coll_name].dict(),
                description=f"Vector collection '{coll_name}' added"
            ))

        # Removed collections
        for coll_name in local_collections - cloud_collections:
            diff.removed_changes.append(SchemaChange(
                change_type=ChangeType.VECTOR_INDEX_REMOVED,
                severity=ChangeSeverity.CRITICAL,
                entity_type="vector_collection",
                entity_name=coll_name,
                old_value=local_schema.vector_collections[coll_name].dict(),
                description=f"Vector collection '{coll_name}' removed"
            ))

        # Compare common collections
        for coll_name in local_collections & cloud_collections:
            local_coll = local_schema.vector_collections[coll_name]
            cloud_coll = cloud_schema.vector_collections[coll_name]

            # Dimension changed (CRITICAL - incompatible)
            if local_coll.vector_dimension != cloud_coll.vector_dimension:
                diff.modified_changes.append(SchemaChange(
                    change_type=ChangeType.VECTOR_DIMENSION_CHANGED,
                    severity=ChangeSeverity.CRITICAL,
                    entity_type="vector_collection",
                    entity_name=coll_name,
                    field_name="vector_dimension",
                    old_value=local_coll.vector_dimension,
                    new_value=cloud_coll.vector_dimension,
                    description=f"Vector dimension changed from {local_coll.vector_dimension} to {cloud_coll.vector_dimension}"
                ))

    def _compare_buckets(
        self,
        diff: SchemaDiff,
        local_schema: SchemaDefinition,
        cloud_schema: SchemaDefinition
    ) -> None:
        """
        Compare MinIO buckets

        Args:
            diff: SchemaDiff to populate
            local_schema: Local schema
            cloud_schema: Cloud schema
        """
        local_buckets = set(local_schema.buckets.keys())
        cloud_buckets = set(cloud_schema.buckets.keys())

        # New buckets
        for bucket_name in cloud_buckets - local_buckets:
            diff.added_changes.append(SchemaChange(
                change_type=ChangeType.BUCKET_POLICY_CHANGED,
                severity=ChangeSeverity.INFO,
                entity_type="bucket",
                entity_name=bucket_name,
                new_value=cloud_schema.buckets[bucket_name].dict(),
                description=f"Bucket '{bucket_name}' added"
            ))

        # Removed buckets
        for bucket_name in local_buckets - cloud_buckets:
            diff.removed_changes.append(SchemaChange(
                change_type=ChangeType.BUCKET_POLICY_CHANGED,
                severity=ChangeSeverity.WARNING,
                entity_type="bucket",
                entity_name=bucket_name,
                old_value=local_schema.buckets[bucket_name].dict(),
                description=f"Bucket '{bucket_name}' removed"
            ))

    def detect_breaking_changes(self, diff: SchemaDiff) -> List[BreakingChange]:
        """
        Detect breaking changes from schema diff

        Args:
            diff: Schema diff to analyze

        Returns:
            List of breaking changes with impact and mitigation
        """
        breaking_changes = []

        # Analyze all changes
        all_changes = (
            diff.added_changes +
            diff.removed_changes +
            diff.modified_changes
        )

        for change in all_changes:
            if change.severity == ChangeSeverity.CRITICAL:
                breaking_change = self._create_breaking_change(change)
                if breaking_change:
                    breaking_changes.append(breaking_change)

        return breaking_changes

    def _create_breaking_change(self, change: SchemaChange) -> Optional[BreakingChange]:
        """
        Create breaking change with impact and mitigation

        Args:
            change: Schema change to analyze

        Returns:
            BreakingChange or None if not actually breaking
        """
        impact = ""
        mitigation = ""
        requires_manual = False

        if change.change_type == ChangeType.TABLE_REMOVED:
            impact = "All data in this table will be lost. Queries will fail."
            mitigation = "Export table data before migration. Update application code to remove references."
            requires_manual = True

        elif change.change_type == ChangeType.COLUMN_REMOVED:
            impact = f"Data in column '{change.field_name}' will be lost. Queries referencing it will fail."
            mitigation = f"Export column data before migration. Update queries to remove '{change.field_name}' references."
            requires_manual = True

        elif change.change_type == ChangeType.COLUMN_TYPE_CHANGED:
            impact = f"Data type conversion from {change.old_value} to {change.new_value} may lose precision or fail."
            mitigation = "Verify data compatibility. Consider backing up data before type conversion."
            requires_manual = True

        elif change.change_type == ChangeType.COLUMN_NULLABLE_CHANGED:
            if change.new_value is False:  # Becoming NOT NULL
                impact = "Existing NULL values will cause migration to fail."
                mitigation = "Set default values for existing NULL rows before migration."
                requires_manual = True

        elif change.change_type == ChangeType.VECTOR_DIMENSION_CHANGED:
            impact = "Vector dimensions incompatible. All vectors must be re-embedded."
            mitigation = "Re-generate all embeddings with new dimension. This cannot be automated."
            requires_manual = True

        elif change.change_type == ChangeType.VECTOR_INDEX_REMOVED:
            impact = "All vectors in this collection will be lost."
            mitigation = "Export vectors before migration."
            requires_manual = True

        if not impact:
            return None

        return BreakingChange(
            change_type=change.change_type,
            severity=change.severity,
            entity_type=change.entity_type,
            entity_name=change.entity_name,
            field_name=change.field_name,
            description=change.description,
            impact=impact,
            mitigation=mitigation,
            requires_manual_intervention=requires_manual
        )

    def generate_migration_plan(
        self,
        diff: SchemaDiff,
        project_id: UUID
    ) -> MigrationPlan:
        """
        Generate migration plan from schema diff

        Args:
            diff: Schema diff to generate plan from
            project_id: Project UUID

        Returns:
            MigrationPlan with ordered steps
        """
        plan_id = f"migration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        steps: List[MigrationStep] = []
        warnings: List[str] = []
        total_duration = 0.0

        step_number = 1

        # Step 1: Add new tables
        for change in diff.added_changes:
            if change.change_type == ChangeType.TABLE_ADDED:
                step = self._create_add_table_step(step_number, change)
                steps.append(step)
                total_duration += step.estimated_duration_seconds or 0
                step_number += 1

        # Step 2: Add new columns (non-breaking)
        for change in diff.added_changes:
            if change.change_type == ChangeType.COLUMN_ADDED:
                step = self._create_add_column_step(step_number, change)
                steps.append(step)
                total_duration += step.estimated_duration_seconds or 0
                step_number += 1

        # Step 3: Modify columns (potentially breaking)
        for change in diff.modified_changes:
            if change.change_type in [ChangeType.COLUMN_TYPE_CHANGED, ChangeType.COLUMN_NULLABLE_CHANGED]:
                step = self._create_modify_column_step(step_number, change)
                steps.append(step)
                total_duration += step.estimated_duration_seconds or 0
                warnings.append(f"Step {step_number}: {change.description} - Verify data compatibility")
                step_number += 1

        # Step 4: Add indexes
        for change in diff.added_changes:
            if change.change_type == ChangeType.INDEX_ADDED:
                step = self._create_add_index_step(step_number, change)
                steps.append(step)
                total_duration += step.estimated_duration_seconds or 0
                step_number += 1

        # Step 5: Remove indexes (safe)
        for change in diff.removed_changes:
            if change.change_type == ChangeType.INDEX_REMOVED:
                step = self._create_remove_index_step(step_number, change)
                steps.append(step)
                total_duration += step.estimated_duration_seconds or 0
                step_number += 1

        # Breaking changes generate warnings
        for breaking_change in diff.breaking_changes:
            warnings.append(
                f"BREAKING: {breaking_change.description} - {breaking_change.mitigation}"
            )

        is_safe = len(diff.breaking_changes) == 0
        requires_downtime = len(diff.breaking_changes) > 0

        return MigrationPlan(
            plan_id=plan_id,
            project_id=str(project_id),
            steps=steps,
            total_steps=len(steps),
            estimated_total_duration_seconds=total_duration,
            warnings=warnings,
            is_safe=is_safe,
            requires_downtime=requires_downtime,
            breaking_changes_count=len(diff.breaking_changes),
            created_at=datetime.utcnow()
        )

    def _create_add_table_step(self, step_number: int, change: SchemaChange) -> MigrationStep:
        """Create migration step for adding a table"""
        return MigrationStep(
            step_number=step_number,
            operation=f"CREATE TABLE {change.entity_name} (id UUID PRIMARY KEY)",
            description=f"Create table '{change.entity_name}'",
            is_reversible=True,
            rollback_operation=f"DROP TABLE {change.entity_name}",
            estimated_duration_seconds=0.1,
            affected_entities=[change.entity_name]
        )

    def _create_add_column_step(self, step_number: int, change: SchemaChange) -> MigrationStep:
        """Create migration step for adding a column"""
        col_def = change.new_value or {}
        data_type = col_def.get('data_type', 'TEXT')
        nullable = "NULL" if col_def.get('nullable', True) else "NOT NULL"

        return MigrationStep(
            step_number=step_number,
            operation=f"ALTER TABLE {change.entity_name} ADD COLUMN {change.field_name} {data_type} {nullable}",
            description=f"Add column '{change.field_name}' to table '{change.entity_name}'",
            is_reversible=True,
            rollback_operation=f"ALTER TABLE {change.entity_name} DROP COLUMN {change.field_name}",
            estimated_duration_seconds=0.5,
            affected_entities=[change.entity_name]
        )

    def _create_modify_column_step(self, step_number: int, change: SchemaChange) -> MigrationStep:
        """Create migration step for modifying a column"""
        if change.change_type == ChangeType.COLUMN_TYPE_CHANGED:
            operation = f"ALTER TABLE {change.entity_name} ALTER COLUMN {change.field_name} TYPE {change.new_value}"
            description = f"Change column '{change.field_name}' type to {change.new_value}"
            rollback_operation = f"ALTER TABLE {change.entity_name} ALTER COLUMN {change.field_name} TYPE {change.old_value}"
        else:  # COLUMN_NULLABLE_CHANGED
            if change.new_value is False:
                operation = f"ALTER TABLE {change.entity_name} ALTER COLUMN {change.field_name} SET NOT NULL"
                rollback_operation = f"ALTER TABLE {change.entity_name} ALTER COLUMN {change.field_name} DROP NOT NULL"
            else:
                operation = f"ALTER TABLE {change.entity_name} ALTER COLUMN {change.field_name} DROP NOT NULL"
                rollback_operation = f"ALTER TABLE {change.entity_name} ALTER COLUMN {change.field_name} SET NOT NULL"
            description = f"Change column '{change.field_name}' nullable to {change.new_value}"

        return MigrationStep(
            step_number=step_number,
            operation=operation,
            description=description,
            is_reversible=True,
            rollback_operation=rollback_operation,
            estimated_duration_seconds=1.0,
            affected_entities=[change.entity_name]
        )

    def _create_add_index_step(self, step_number: int, change: SchemaChange) -> MigrationStep:
        """Create migration step for adding an index"""
        idx_def = change.new_value or {}
        columns = ", ".join(idx_def.get('columns', []))
        unique = "UNIQUE " if idx_def.get('unique', False) else ""

        return MigrationStep(
            step_number=step_number,
            operation=f"CREATE {unique}INDEX {change.field_name} ON {change.entity_name} ({columns})",
            description=f"Create index '{change.field_name}' on table '{change.entity_name}'",
            is_reversible=True,
            rollback_operation=f"DROP INDEX {change.field_name}",
            estimated_duration_seconds=2.0,
            affected_entities=[change.entity_name]
        )

    def _create_remove_index_step(self, step_number: int, change: SchemaChange) -> MigrationStep:
        """Create migration step for removing an index"""
        return MigrationStep(
            step_number=step_number,
            operation=f"DROP INDEX {change.field_name}",
            description=f"Remove index '{change.field_name}' from table '{change.entity_name}'",
            is_reversible=False,  # Cannot recreate without knowing exact definition
            estimated_duration_seconds=0.5,
            affected_entities=[change.entity_name]
        )
