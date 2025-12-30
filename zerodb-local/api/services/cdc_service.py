"""
Change Data Capture (CDC) Service
Service for tracking and querying database changes
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session


class CDCService:
    """
    Service for Change Data Capture operations

    Provides methods to:
    - Query change log entries
    - Filter changes by timestamp, entity type
    - Mark changes as synced
    - Clean up old synced changes
    - Get change statistics
    """

    def get_changes(
        self,
        db: Session,
        project_id: UUID,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all changes for a project with optional filters

        Args:
            db: Database session
            project_id: Project UUID
            entity_type: Optional filter by entity type
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of change log entries as dictionaries
        """
        query = """
            SELECT
                id, project_id, entity_type, entity_id, operation,
                data, timestamp, synced_at, synced
            FROM change_log
            WHERE project_id = :project_id
        """
        params = {"project_id": str(project_id), "limit": limit, "offset": offset}

        if entity_type:
            query += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type

        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"

        result = db.execute(text(query), params)
        changes = []

        for row in result:
            changes.append({
                "id": str(row.id),
                "project_id": str(row.project_id),
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id),
                "operation": row.operation,
                "data": row.data,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "synced_at": row.synced_at.isoformat() if row.synced_at else None,
                "synced": row.synced
            })

        return changes

    def get_changes_since(
        self,
        db: Session,
        project_id: UUID,
        since: datetime,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get changes that occurred after a specific timestamp

        Args:
            db: Database session
            project_id: Project UUID
            since: Get changes after this timestamp
            entity_type: Optional filter by entity type
            limit: Maximum results to return

        Returns:
            List of change log entries as dictionaries
        """
        query = """
            SELECT
                id, project_id, entity_type, entity_id, operation,
                data, timestamp, synced_at, synced
            FROM change_log
            WHERE project_id = :project_id AND timestamp > :since
        """
        params = {
            "project_id": str(project_id),
            "since": since,
            "limit": limit
        }

        if entity_type:
            query += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type

        query += " ORDER BY timestamp ASC LIMIT :limit"

        result = db.execute(text(query), params)
        changes = []

        for row in result:
            changes.append({
                "id": str(row.id),
                "project_id": str(row.project_id),
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id),
                "operation": row.operation,
                "data": row.data,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "synced_at": row.synced_at.isoformat() if row.synced_at else None,
                "synced": row.synced
            })

        return changes

    def get_unsynced_changes(
        self,
        db: Session,
        project_id: UUID,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all unsynced changes for a project

        Args:
            db: Database session
            project_id: Project UUID
            entity_type: Optional filter by entity type
            limit: Maximum results to return

        Returns:
            List of unsynced change log entries
        """
        query = """
            SELECT
                id, project_id, entity_type, entity_id, operation,
                data, timestamp, synced_at, synced
            FROM change_log
            WHERE project_id = :project_id AND synced = FALSE
        """
        params = {"project_id": str(project_id), "limit": limit}

        if entity_type:
            query += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type

        query += " ORDER BY timestamp ASC LIMIT :limit"

        result = db.execute(text(query), params)
        changes = []

        for row in result:
            changes.append({
                "id": str(row.id),
                "project_id": str(row.project_id),
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id),
                "operation": row.operation,
                "data": row.data,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "synced_at": row.synced_at.isoformat() if row.synced_at else None,
                "synced": row.synced
            })

        return changes

    def get_change_count(
        self,
        db: Session,
        project_id: UUID,
        entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about changes for a project

        Args:
            db: Database session
            project_id: Project UUID
            entity_type: Optional filter by entity type

        Returns:
            Dictionary with change statistics
        """
        base_filter = "WHERE project_id = :project_id"
        params = {"project_id": str(project_id)}

        if entity_type:
            base_filter += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type

        # Total and unsynced counts
        count_query = f"""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE synced = FALSE) as unsynced
            FROM change_log
            {base_filter}
        """
        count_result = db.execute(text(count_query), params).first()

        # By entity type
        entity_query = f"""
            SELECT entity_type, COUNT(*) as count
            FROM change_log
            {base_filter}
            GROUP BY entity_type
        """
        entity_result = db.execute(text(entity_query), params)
        by_entity_type = {row.entity_type: row.count for row in entity_result}

        # By operation
        operation_query = f"""
            SELECT operation, COUNT(*) as count
            FROM change_log
            {base_filter}
            GROUP BY operation
        """
        operation_result = db.execute(text(operation_query), params)
        by_operation = {row.operation: row.count for row in operation_result}

        # Timestamps
        timestamp_query = f"""
            SELECT
                MIN(timestamp) as oldest,
                MAX(timestamp) as newest
            FROM change_log
            {base_filter}
        """
        timestamp_result = db.execute(text(timestamp_query), params).first()

        return {
            "project_id": str(project_id),
            "total_changes": count_result.total,
            "unsynced_changes": count_result.unsynced,
            "by_entity_type": by_entity_type,
            "by_operation": by_operation,
            "oldest_change": timestamp_result.oldest.isoformat() if timestamp_result.oldest else None,
            "newest_change": timestamp_result.newest.isoformat() if timestamp_result.newest else None
        }

    def mark_synced(
        self,
        db: Session,
        change_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Mark specific changes as synced

        Args:
            db: Database session
            change_ids: List of change log IDs to mark

        Returns:
            Dictionary with count of synced changes
        """
        if not change_ids:
            return {"synced_count": 0, "timestamp": datetime.utcnow().isoformat()}

        now = datetime.utcnow()

        # Convert string IDs to proper format for SQL
        id_list = ", ".join(f"'{id}'" for id in change_ids)

        query = f"""
            UPDATE change_log
            SET synced = TRUE, synced_at = :synced_at
            WHERE id IN ({id_list})
        """

        result = db.execute(text(query), {"synced_at": now})
        db.commit()

        return {
            "synced_count": result.rowcount,
            "timestamp": now.isoformat()
        }

    def cleanup_old_changes(
        self,
        db: Session,
        project_id: Optional[UUID] = None,
        days: int = 30,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up old synced changes

        Args:
            db: Database session
            project_id: Optional project UUID (if None, cleans all projects)
            days: Delete changes older than this many days
            dry_run: If True, only count what would be deleted

        Returns:
            Dictionary with deletion statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = """
            SELECT COUNT(*) as count, MIN(timestamp) as oldest
            FROM change_log
            WHERE synced = TRUE AND timestamp < :cutoff_date
        """
        params = {"cutoff_date": cutoff_date}

        if project_id:
            query += " AND project_id = :project_id"
            params["project_id"] = str(project_id)

        result = db.execute(text(query), params).first()

        if dry_run:
            return {
                "deleted_count": result.count,
                "oldest_deleted": result.oldest.isoformat() if result.oldest else None,
                "dry_run": True
            }

        # Actually delete
        delete_query = """
            DELETE FROM change_log
            WHERE synced = TRUE AND timestamp < :cutoff_date
        """

        if project_id:
            delete_query += " AND project_id = :project_id"

        delete_result = db.execute(text(delete_query), params)
        db.commit()

        return {
            "deleted_count": delete_result.rowcount,
            "oldest_deleted": result.oldest.isoformat() if result.oldest else None,
            "dry_run": False
        }

    def get_changes_between(
        self,
        db: Session,
        project_id: UUID,
        start: datetime,
        end: datetime,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get changes that occurred between two timestamps

        Args:
            db: Database session
            project_id: Project UUID
            start: Start timestamp (inclusive)
            end: End timestamp (inclusive)
            entity_type: Optional filter by entity type
            limit: Maximum results to return

        Returns:
            List of change log entries
        """
        query = """
            SELECT
                id, project_id, entity_type, entity_id, operation,
                data, timestamp, synced_at, synced
            FROM change_log
            WHERE project_id = :project_id
              AND timestamp >= :start
              AND timestamp <= :end
        """
        params = {
            "project_id": str(project_id),
            "start": start,
            "end": end,
            "limit": limit
        }

        if entity_type:
            query += " AND entity_type = :entity_type"
            params["entity_type"] = entity_type

        query += " ORDER BY timestamp ASC LIMIT :limit"

        result = db.execute(text(query), params)
        changes = []

        for row in result:
            changes.append({
                "id": str(row.id),
                "project_id": str(row.project_id),
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id),
                "operation": row.operation,
                "data": row.data,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "synced_at": row.synced_at.isoformat() if row.synced_at else None,
                "synced": row.synced
            })

        return changes
