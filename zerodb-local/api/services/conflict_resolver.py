"""
Conflict Resolution Service

Detects and resolves conflicts between local and cloud data during sync operations.
Implements multiple resolution strategies and provides manual intervention capabilities.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from sqlalchemy.orm import Session
import logging

from models.conflict_log import ConflictLog
from schemas.conflict_resolution import (
    Conflict,
    ConflictType,
    ConflictResolutionStrategy,
    EntityVersion,
    ConflictResolutionRequest,
    ConflictResolutionResponse,
    ConflictSummary,
    AutoResolveRequest,
    AutoResolveResponse,
    ManualResolutionPrompt
)

logger = logging.getLogger(__name__)


class ConflictResolutionStrategy(str, Enum):
    """Strategy for resolving conflicts - matches schema enum"""
    LOCAL_WINS = "local_wins"
    CLOUD_WINS = "cloud_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"


class ConflictResolver:
    """
    Service for detecting and resolving conflicts between local and cloud data.

    Supports multiple resolution strategies:
    - LOCAL_WINS: Local changes override cloud
    - CLOUD_WINS: Cloud changes override local
    - NEWEST_WINS: Most recent timestamp wins
    - MANUAL: Interactive user resolution
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize conflict resolver.

        Args:
            db: Optional database session for persistence
        """
        self.db = db

    def detect_conflicts(
        self,
        local_entities: List[Dict[str, Any]],
        cloud_entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between local and cloud entities.

        A conflict occurs when:
        - Same entity_id exists in both local and cloud
        - The data hashes are different (concurrent modifications)

        Args:
            local_entities: List of local entity dictionaries
            cloud_entities: List of cloud entity dictionaries

        Returns:
            List of detected conflicts with local and cloud versions
        """
        conflicts = []

        # Build lookup maps by entity_id
        local_map = {e["entity_id"]: e for e in local_entities}
        cloud_map = {e["entity_id"]: e for e in cloud_entities}

        # Find entities that exist in both with different hashes
        for entity_id, local_entity in local_map.items():
            if entity_id in cloud_map:
                cloud_entity = cloud_map[entity_id]

                # Check if hashes differ (concurrent modification)
                if local_entity.get("hash") != cloud_entity.get("hash"):
                    conflicts.append({
                        "entity_id": entity_id,
                        "entity_type": local_entity.get("entity_type"),
                        "local_version": local_entity,
                        "cloud_version": cloud_entity,
                        "detected_at": datetime.utcnow()
                    })

        return conflicts

    def resolve_conflict(
        self,
        conflict: Dict[str, Any],
        strategy: ConflictResolutionStrategy
    ) -> Dict[str, Any]:
        """
        Resolve a conflict using the specified strategy.

        Args:
            conflict: Conflict dictionary with local_version and cloud_version
            strategy: Resolution strategy to apply

        Returns:
            Resolution result with chosen_version and resolution metadata

        Raises:
            ValueError: If strategy is invalid
        """
        if not isinstance(strategy, (ConflictResolutionStrategy, str)):
            raise ValueError(f"Invalid resolution strategy: {strategy}")

        # Normalize string to enum
        if isinstance(strategy, str):
            try:
                strategy = ConflictResolutionStrategy(strategy)
            except ValueError:
                raise ValueError(f"Invalid resolution strategy: {strategy}")

        local_version = conflict["local_version"]
        cloud_version = conflict["cloud_version"]

        if strategy == ConflictResolutionStrategy.LOCAL_WINS:
            return {
                "resolution": "local_wins",
                "chosen_version": local_version,
                "discarded_version": cloud_version
            }

        elif strategy == ConflictResolutionStrategy.CLOUD_WINS:
            return {
                "resolution": "cloud_wins",
                "chosen_version": cloud_version,
                "discarded_version": local_version
            }

        elif strategy == ConflictResolutionStrategy.NEWEST_WINS:
            # Compare timestamps if available
            local_ts = local_version.get("updated_at")
            cloud_ts = cloud_version.get("updated_at")

            if local_ts and cloud_ts:
                if local_ts >= cloud_ts:
                    chosen = local_version
                    discarded = cloud_version
                else:
                    chosen = cloud_version
                    discarded = local_version
            else:
                # Fall back to local-wins if timestamps unavailable
                chosen = local_version
                discarded = cloud_version

            return {
                "resolution": "newest_wins",
                "chosen_version": chosen,
                "discarded_version": discarded
            }

        elif strategy == ConflictResolutionStrategy.MANUAL:
            # For manual resolution, prompt user
            chosen = self.prompt_user_for_resolution(conflict)
            discarded = cloud_version if chosen == local_version else local_version

            return {
                "resolution": "manual",
                "chosen_version": chosen,
                "discarded_version": discarded
            }

        raise ValueError(f"Invalid resolution strategy: {strategy}")

    def prompt_user_for_resolution(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prompt user to manually resolve a conflict.

        Args:
            conflict: Conflict data with local and cloud versions

        Returns:
            Chosen version (local or cloud)
        """
        local_version = conflict["local_version"]
        cloud_version = conflict["cloud_version"]

        print("\n" + "="*80)
        print(f"CONFLICT DETECTED: {conflict['entity_type']} - {conflict['entity_id']}")
        print("="*80)
        print("\n1. LOCAL VERSION:")
        print(f"   Data: {local_version.get('data')}")
        print(f"   Updated: {local_version.get('updated_at')}")
        print("\n2. CLOUD VERSION:")
        print(f"   Data: {cloud_version.get('data')}")
        print(f"   Updated: {cloud_version.get('updated_at')}")
        print("\n" + "="*80)

        while True:
            try:
                choice = input("\nChoose version (1=local, 2=cloud): ").strip()
                if choice == "1":
                    return local_version
                elif choice == "2":
                    return cloud_version
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            except (KeyboardInterrupt, EOFError):
                print("\nDefaulting to local version")
                return local_version

    def log_conflict(
        self,
        project_id: UUID,
        conflict: Dict[str, Any],
        resolution: Dict[str, Any]
    ) -> None:
        """
        Log a resolved conflict to the database.

        Args:
            project_id: Project ID
            conflict: Conflict data
            resolution: Resolution result
        """
        if not self.db:
            logger.warning("No database session provided, skipping conflict logging")
            return

        conflict_log = ConflictLog(
            project_id=project_id,
            entity_type=conflict["entity_type"],
            entity_id=conflict["entity_id"],
            local_version=conflict["local_version"],
            cloud_version=conflict["cloud_version"],
            resolution_strategy=resolution["resolution"],
            chosen_version=resolution["chosen_version"],
            detected_at=conflict.get("detected_at", datetime.utcnow()),
            resolved_at=datetime.utcnow()
        )

        self.db.add(conflict_log)
        self.db.commit()

    def resolve_all(
        self,
        project_id: UUID,
        conflicts: List[Dict[str, Any]],
        strategy: ConflictResolutionStrategy
    ) -> List[Dict[str, Any]]:
        """
        Resolve all conflicts using the specified strategy.

        Args:
            project_id: Project ID
            conflicts: List of conflicts to resolve
            strategy: Resolution strategy to apply to all

        Returns:
            List of resolution results
        """
        results = []

        for conflict in conflicts:
            try:
                resolution = self.resolve_conflict(conflict, strategy)

                # Log to database if session available
                if self.db:
                    self.log_conflict(project_id, conflict, resolution)

                results.append({
                    "conflict": conflict,
                    "resolution": resolution,
                    "success": True
                })
            except Exception as e:
                logger.error(f"Failed to resolve conflict {conflict.get('entity_id')}: {str(e)}")
                results.append({
                    "conflict": conflict,
                    "error": str(e),
                    "success": False
                })

        return results

    def get_conflicts(
        self,
        project_id: UUID,
        status: str = "all",
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ConflictLog]:
        """
        Retrieve conflicts from the database.

        Args:
            project_id: Project ID
            status: Filter by status (all, resolved, unresolved) - not used in current model
            entity_type: Optional filter by entity type
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of conflict log entries
        """
        if not self.db:
            return []

        query = self.db.query(ConflictLog).filter(
            ConflictLog.project_id == project_id
        )

        if entity_type:
            query = query.filter(ConflictLog.entity_type == entity_type)

        # Note: Current model doesn't have status field
        # All logged conflicts are resolved by definition

        return query.offset(offset).limit(limit).all()

    def get_conflict_by_id(
        self,
        conflict_id: str,
        db: Session
    ) -> Optional[ConflictLog]:
        """
        Get a specific conflict by ID.

        Args:
            conflict_id: Conflict ID
            db: Database session

        Returns:
            ConflictLog or None if not found
        """
        try:
            conflict_uuid = UUID(conflict_id)
            return db.query(ConflictLog).filter(
                ConflictLog.id == conflict_uuid
            ).first()
        except (ValueError, AttributeError):
            return None

    def get_conflict_summary(
        self,
        project_id: UUID
    ) -> Dict[str, Any]:
        """
        Get summary statistics of conflicts for a project.

        Args:
            project_id: Project ID

        Returns:
            Summary statistics
        """
        if not self.db:
            return {
                "total_conflicts": 0,
                "by_entity_type": {},
                "by_strategy": {}
            }

        conflicts = self.db.query(ConflictLog).filter(
            ConflictLog.project_id == project_id
        ).all()

        # Calculate statistics
        by_entity_type = {}
        by_strategy = {}

        for conflict in conflicts:
            # Count by entity type
            entity_type = conflict.entity_type
            by_entity_type[entity_type] = by_entity_type.get(entity_type, 0) + 1

            # Count by strategy
            strategy = conflict.resolution_strategy
            by_strategy[strategy] = by_strategy.get(strategy, 0) + 1

        return {
            "total_conflicts": len(conflicts),
            "by_entity_type": by_entity_type,
            "by_strategy": by_strategy
        }


# Standalone helper functions for use without class instantiation

def detect_conflicts_in_entities(
    local_entities: List[Dict[str, Any]],
    cloud_entities: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Standalone function to detect conflicts without class instance.

    Args:
        local_entities: Local entity list
        cloud_entities: Cloud entity list

    Returns:
        List of conflicts
    """
    resolver = ConflictResolver()
    return resolver.detect_conflicts(local_entities, cloud_entities)


def resolve_conflict_auto(
    conflict: Dict[str, Any],
    strategy: ConflictResolutionStrategy
) -> Dict[str, Any]:
    """
    Standalone function to resolve a conflict without class instance.

    Args:
        conflict: Conflict data
        strategy: Resolution strategy

    Returns:
        Resolution result
    """
    resolver = ConflictResolver()
    return resolver.resolve_conflict(conflict, strategy)
