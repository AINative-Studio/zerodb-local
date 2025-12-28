"""
Sync Plan Generator - Creates detailed sync plans showing differences between local and cloud
"""
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class SyncOperation:
    """Represents a single sync operation"""
    entity_type: str  # 'table', 'vector', 'file', 'event', 'memory'
    operation: Literal['create', 'update', 'delete', 'upsert']
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    description: str = ""
    data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncPlan:
    """Complete sync plan with all operations"""
    direction: Literal['push', 'pull', 'bidirectional']
    mode: Literal['full', 'incremental', 'selective']
    operations: List[SyncOperation] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def total_operations(self) -> int:
        """Total number of operations"""
        return len(self.operations)

    @property
    def has_conflicts(self) -> bool:
        """Check if plan has conflicts"""
        return len(self.conflicts) > 0

    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics"""
        summary = {
            'total': len(self.operations),
            'create': 0,
            'update': 0,
            'delete': 0,
            'upsert': 0
        }

        for op in self.operations:
            summary[op.operation] = summary.get(op.operation, 0) + 1

        return summary

    def get_by_entity_type(self, entity_type: str) -> List[SyncOperation]:
        """Get operations for specific entity type"""
        return [op for op in self.operations if op.entity_type == entity_type]


class SyncPlanner:
    """Generates sync plans by comparing local and cloud state"""

    def __init__(self, local_api_url: str = "http://localhost:8000", cloud_api_url: str = "https://api.ainative.studio"):
        self.local_api_url = local_api_url
        self.cloud_api_url = cloud_api_url

    def generate_plan(
        self,
        project_id: str,
        direction: Literal['push', 'pull', 'bidirectional'] = 'push',
        mode: Literal['full', 'incremental', 'selective'] = 'incremental',
        filters: Optional[Dict[str, Any]] = None
    ) -> SyncPlan:
        """
        Generate sync plan by comparing local and cloud state

        Args:
            project_id: Project ID to sync
            direction: Sync direction (push, pull, bidirectional)
            mode: Sync mode (full, incremental, selective)
            filters: Optional filters for selective sync

        Returns:
            SyncPlan with all operations
        """
        plan = SyncPlan(direction=direction, mode=mode)

        # In a real implementation, this would:
        # 1. Fetch local state
        # 2. Fetch cloud state
        # 3. Compare and generate operations
        # 4. Detect conflicts

        # For now, create a placeholder plan
        if mode == 'full':
            plan.operations = self._generate_full_sync_operations(project_id, direction, filters)
        else:
            plan.operations = self._generate_incremental_sync_operations(project_id, direction, filters)

        return plan

    def _generate_full_sync_operations(
        self,
        project_id: str,
        direction: Literal['push', 'pull', 'bidirectional'],
        filters: Optional[Dict[str, Any]]
    ) -> List[SyncOperation]:
        """Generate operations for full sync"""
        operations = []

        # TODO: Implement full sync logic
        # This would export all local data and compare with cloud

        return operations

    def _generate_incremental_sync_operations(
        self,
        project_id: str,
        direction: Literal['push', 'pull', 'bidirectional'],
        filters: Optional[Dict[str, Any]]
    ) -> List[SyncOperation]:
        """Generate operations for incremental sync"""
        operations = []

        # TODO: Implement incremental sync using change log
        # This would only sync changes since last sync timestamp

        return operations

    def detect_conflicts(self, local_changes: List[Dict], cloud_changes: List[Dict]) -> List[Dict[str, Any]]:
        """
        Detect conflicts between local and cloud changes

        Args:
            local_changes: List of local changes
            cloud_changes: List of cloud changes

        Returns:
            List of conflicts
        """
        conflicts = []

        for local_change in local_changes:
            for cloud_change in cloud_changes:
                if (local_change['entity_type'] == cloud_change['entity_type'] and
                    local_change['entity_id'] == cloud_change['entity_id']):

                    conflicts.append({
                        'entity_type': local_change['entity_type'],
                        'entity_id': local_change['entity_id'],
                        'local_value': local_change.get('data'),
                        'cloud_value': cloud_change.get('data'),
                        'local_timestamp': local_change.get('timestamp'),
                        'cloud_timestamp': cloud_change.get('timestamp')
                    })

        return conflicts

    def plan_to_json(self, plan: SyncPlan) -> str:
        """Convert plan to JSON string"""
        return json.dumps({
            'direction': plan.direction,
            'mode': plan.mode,
            'created_at': plan.created_at,
            'total_operations': plan.total_operations,
            'has_conflicts': plan.has_conflicts,
            'summary': plan.get_summary(),
            'operations': [
                {
                    'entity_type': op.entity_type,
                    'operation': op.operation,
                    'entity_id': op.entity_id,
                    'entity_name': op.entity_name,
                    'description': op.description,
                    'metadata': op.metadata
                }
                for op in plan.operations
            ],
            'conflicts': plan.conflicts
        }, indent=2)
