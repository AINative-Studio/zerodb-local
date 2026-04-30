"""
Schema Migrator Service
Handles schema migrations from cloud to local database
"""
from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class SchemaMigrator:
    """
    Service for applying schema changes from cloud to local database

    Handles:
    - Adding new fields to tables
    - Removing deprecated fields
    - Changing field types
    - Safe migrations with rollback support
    """

    async def migrate_schema(
        self,
        db: Session,
        project_id: UUID,
        cloud_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply schema migrations from cloud to local

        Args:
            db: Database session
            project_id: Project UUID
            cloud_schema: Schema from cloud to apply

        Returns:
            Migration result with changes applied
        """
        try:
            # Get current local schema
            local_schema = await self._get_local_schema(db, project_id)

            # Calculate schema differences
            changes = self._calculate_schema_diff(local_schema, cloud_schema)

            if not changes:
                logger.info(f"No schema changes needed for project {project_id}")
                return {
                    'success': True,
                    'migrations_applied': 0,
                    'changes': []
                }

            # Apply migrations
            applied_changes = []
            for change in changes:
                try:
                    await self._apply_migration(db, project_id, change)
                    applied_changes.append(change)
                    logger.info(f"Applied migration: {change}")
                except Exception as e:
                    logger.error(f"Failed to apply migration {change}: {e}")
                    raise

            db.commit()

            return {
                'success': True,
                'migrations_applied': len(applied_changes),
                'changes': applied_changes
            }

        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            db.rollback()
            return {
                'success': False,
                'error': str(e),
                'migrations_applied': 0,
                'changes': []
            }

    async def _get_local_schema(
        self,
        db: Session,
        project_id: UUID
    ) -> Dict[str, Any]:
        """
        Get current local schema for project

        Args:
            db: Database session
            project_id: Project UUID

        Returns:
            Local schema dictionary
        """
        query = text("""
            SELECT name, schema
            FROM tables
            WHERE project_id = :project_id
            AND deleted_at IS NULL
        """)

        result = db.execute(query, {"project_id": str(project_id)})
        rows = result.fetchall()

        schema = {'tables': {}}
        for row in rows:
            schema['tables'][row.name] = row.schema

        return schema

    def _calculate_schema_diff(
        self,
        local_schema: Dict[str, Any],
        cloud_schema: Dict[str, Any]
    ) -> List[str]:
        """
        Calculate differences between local and cloud schemas

        Args:
            local_schema: Current local schema
            cloud_schema: Cloud schema to apply

        Returns:
            List of change descriptions
        """
        changes = []

        # Get table lists
        local_tables = set(local_schema.get('tables', {}).keys())
        cloud_tables = set(cloud_schema.get('tables', {}).keys())

        # New tables in cloud
        for table_name in cloud_tables - local_tables:
            changes.append(f"add_table:{table_name}")

        # Removed tables (present in local but not cloud)
        for table_name in local_tables - cloud_tables:
            changes.append(f"remove_table:{table_name}")

        # Modified tables
        for table_name in local_tables & cloud_tables:
            local_table = local_schema['tables'][table_name]
            cloud_table = cloud_schema['tables'][table_name]

            # Compare fields
            local_fields = set(local_table.get('fields', {}).keys())
            cloud_fields = set(cloud_table.get('fields', {}).keys())

            # New fields
            for field_name in cloud_fields - local_fields:
                changes.append(f"add_field:{table_name}.{field_name}")

            # Removed fields
            for field_name in local_fields - cloud_fields:
                changes.append(f"remove_field:{table_name}.{field_name}")

            # Changed field types
            for field_name in local_fields & cloud_fields:
                local_type = local_table.get('fields', {}).get(field_name, {}).get('type')
                cloud_type = cloud_table.get('fields', {}).get(field_name, {}).get('type')

                if local_type != cloud_type:
                    changes.append(
                        f"change_type:{table_name}.{field_name}:{local_type}->{cloud_type}"
                    )

        return changes

    async def _apply_migration(
        self,
        db: Session,
        project_id: UUID,
        change: str
    ) -> None:
        """
        Apply a single schema migration

        Args:
            db: Database session
            project_id: Project UUID
            change: Change description (e.g., "add_field:users.email")
        """
        parts = change.split(':')
        operation = parts[0]

        if operation == 'add_table':
            table_name = parts[1]
            await self._add_table(db, project_id, table_name)

        elif operation == 'remove_table':
            table_name = parts[1]
            await self._remove_table(db, project_id, table_name)

        elif operation == 'add_field':
            table_field = parts[1]
            table_name, field_name = table_field.split('.')
            await self._add_field(db, project_id, table_name, field_name)

        elif operation == 'remove_field':
            table_field = parts[1]
            table_name, field_name = table_field.split('.')
            await self._remove_field(db, project_id, table_name, field_name)

        elif operation == 'change_type':
            table_field = parts[1]
            table_name, field_name = table_field.split('.')
            type_change = parts[2]
            old_type, new_type = type_change.split('->')
            await self._change_field_type(
                db, project_id, table_name, field_name, old_type, new_type
            )

    async def _add_table(
        self,
        db: Session,
        project_id: UUID,
        table_name: str
    ) -> None:
        """Add a new table to local schema"""
        query = text("""
            INSERT INTO tables (project_id, name, schema, description)
            VALUES (:project_id, :name, '{}'::jsonb, 'Synced from cloud')
            ON CONFLICT (project_id, name) WHERE deleted_at IS NULL
            DO NOTHING
        """)

        db.execute(query, {
            "project_id": str(project_id),
            "name": table_name
        })

    async def _remove_table(
        self,
        db: Session,
        project_id: UUID,
        table_name: str
    ) -> None:
        """Remove a table from local schema (soft delete)"""
        query = text("""
            UPDATE tables
            SET deleted_at = NOW()
            WHERE project_id = :project_id
            AND name = :name
            AND deleted_at IS NULL
        """)

        db.execute(query, {
            "project_id": str(project_id),
            "name": table_name
        })

    async def _add_field(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        field_name: str
    ) -> None:
        """Add a new field to table schema"""
        query = text("""
            UPDATE tables
            SET schema = jsonb_set(
                schema,
                '{fields,' || :field_name || '}',
                '{"type": "string"}'::jsonb,
                true
            ),
            updated_at = NOW()
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
        """)

        db.execute(query, {
            "project_id": str(project_id),
            "table_name": table_name,
            "field_name": field_name
        })

    async def _remove_field(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        field_name: str
    ) -> None:
        """Remove a field from table schema"""
        query = text("""
            UPDATE tables
            SET schema = schema #- '{fields,' || :field_name || '}',
            updated_at = NOW()
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
        """)

        db.execute(query, {
            "project_id": str(project_id),
            "table_name": table_name,
            "field_name": field_name
        })

    async def _change_field_type(
        self,
        db: Session,
        project_id: UUID,
        table_name: str,
        field_name: str,
        old_type: str,
        new_type: str
    ) -> None:
        """Change field type in table schema"""
        query = text("""
            UPDATE tables
            SET schema = jsonb_set(
                schema,
                '{fields,' || :field_name || ',type}',
                to_jsonb(:new_type::text),
                true
            ),
            updated_at = NOW()
            WHERE project_id = :project_id
            AND name = :table_name
            AND deleted_at IS NULL
        """)

        db.execute(query, {
            "project_id": str(project_id),
            "table_name": table_name,
            "field_name": field_name,
            "new_type": new_type
        })
