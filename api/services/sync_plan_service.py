"""
Sync Plan Service
Manages persistence and retrieval of sync plans
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from models.sync_plan import SyncPlan as SyncPlanModel
from schemas.sync_orchestrator import SyncPlan as SyncPlanSchema

logger = logging.getLogger(__name__)


class SyncPlanService:
    """
    Service for managing sync plans

    Responsibilities:
    - Store generated sync plans
    - Retrieve plans for execution
    - Track plan approval and execution
    - Invalidate expired plans
    """

    def __init__(self, plan_ttl_hours: int = 24):
        """
        Initialize sync plan service

        Args:
            plan_ttl_hours: Time-to-live for plans in hours (default 24)
        """
        self.plan_ttl_hours = plan_ttl_hours

    def save_plan(
        self,
        db: Session,
        sync_plan: SyncPlanSchema
    ) -> SyncPlanModel:
        """
        Save sync plan to database

        Args:
            db: Database session
            sync_plan: SyncPlan schema object to save

        Returns:
            SyncPlanModel database record
        """
        logger.info(f"Saving sync plan {sync_plan.plan_id} for project {sync_plan.project_id}")

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=self.plan_ttl_hours)

        # Convert schema to dict for JSON storage
        plan_dict = sync_plan.model_dump(mode='json')

        # Create database record
        plan_model = SyncPlanModel(
            plan_id=sync_plan.plan_id,
            project_id=sync_plan.project_id,
            direction=sync_plan.direction.value,
            status='pending',
            steps=plan_dict['steps'],
            total_steps=len(sync_plan.steps),
            entity_counts=plan_dict['entity_counts'],
            estimated_duration_seconds=sync_plan.estimated_duration_seconds,
            estimated_data_size_bytes=sync_plan.estimated_data_size_bytes,
            schema_changes=plan_dict['schema_changes'],
            conflicts=plan_dict['conflicts'],
            warnings=sync_plan.warnings,
            requires_approval=sync_plan.requires_approval,
            can_rollback=sync_plan.can_rollback,
            expires_at=expires_at
        )

        db.add(plan_model)
        db.commit()
        db.refresh(plan_model)

        logger.info(
            f"Sync plan saved: plan_id={plan_model.plan_id}, "
            f"steps={plan_model.total_steps}, "
            f"requires_approval={plan_model.requires_approval}"
        )

        return plan_model

    def get_plan_by_id(
        self,
        db: Session,
        plan_id: UUID,
        project_id: Optional[UUID] = None
    ) -> Optional[SyncPlanModel]:
        """
        Get sync plan by plan_id

        Args:
            db: Database session
            plan_id: Plan UUID
            project_id: Optional project UUID for additional validation

        Returns:
            SyncPlanModel or None
        """
        query = db.query(SyncPlanModel).filter(
            SyncPlanModel.plan_id == plan_id
        )

        if project_id:
            query = query.filter(SyncPlanModel.project_id == project_id)

        plan = query.first()

        if plan and plan.is_expired():
            # Mark as expired
            plan.status = 'expired'
            db.commit()
            logger.warning(f"Plan {plan_id} has expired")

        return plan

    def get_plans_for_project(
        self,
        db: Session,
        project_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[SyncPlanModel]:
        """
        Get sync plans for a project

        Args:
            db: Database session
            project_id: Project UUID
            status_filter: Optional status filter
            limit: Maximum plans to return

        Returns:
            List of SyncPlanModel records
        """
        query = db.query(SyncPlanModel).filter(
            SyncPlanModel.project_id == project_id
        )

        if status_filter:
            query = query.filter(SyncPlanModel.status == status_filter)

        query = query.order_by(SyncPlanModel.created_at.desc()).limit(limit)

        return query.all()

    def approve_plan(
        self,
        db: Session,
        plan_id: UUID,
        approved_by: str
    ) -> Optional[SyncPlanModel]:
        """
        Approve a sync plan for execution

        Args:
            db: Database session
            plan_id: Plan UUID
            approved_by: User or system that approved the plan

        Returns:
            Updated SyncPlanModel or None if not found
        """
        plan = self.get_plan_by_id(db, plan_id)

        if not plan:
            logger.warning(f"Cannot approve plan {plan_id}: not found")
            return None

        if plan.is_expired():
            logger.warning(f"Cannot approve plan {plan_id}: expired")
            return None

        plan.status = 'approved'
        plan.approved_by = approved_by
        plan.approved_at = datetime.utcnow()

        db.commit()
        db.refresh(plan)

        logger.info(f"Plan {plan_id} approved by {approved_by}")

        return plan

    def mark_executing(
        self,
        db: Session,
        plan_id: UUID
    ) -> Optional[SyncPlanModel]:
        """
        Mark plan as currently executing

        Args:
            db: Database session
            plan_id: Plan UUID

        Returns:
            Updated SyncPlanModel or None
        """
        plan = self.get_plan_by_id(db, plan_id)

        if not plan:
            return None

        if not plan.is_executable():
            logger.warning(
                f"Cannot execute plan {plan_id}: "
                f"status={plan.status}, expired={plan.is_expired()}"
            )
            return None

        plan.status = 'executing'
        plan.executed_at = datetime.utcnow()

        db.commit()
        db.refresh(plan)

        logger.info(f"Plan {plan_id} marked as executing")

        return plan

    def mark_completed(
        self,
        db: Session,
        plan_id: UUID,
        sync_result_id: UUID
    ) -> Optional[SyncPlanModel]:
        """
        Mark plan as completed

        Args:
            db: Database session
            plan_id: Plan UUID
            sync_result_id: UUID of SyncResult record

        Returns:
            Updated SyncPlanModel or None
        """
        plan = self.get_plan_by_id(db, plan_id)

        if not plan:
            return None

        plan.status = 'completed'
        plan.completed_at = datetime.utcnow()
        plan.sync_result_id = sync_result_id

        db.commit()
        db.refresh(plan)

        logger.info(
            f"Plan {plan_id} marked as completed: "
            f"sync_result_id={sync_result_id}"
        )

        return plan

    def mark_failed(
        self,
        db: Session,
        plan_id: UUID
    ) -> Optional[SyncPlanModel]:
        """
        Mark plan as failed

        Args:
            db: Database session
            plan_id: Plan UUID

        Returns:
            Updated SyncPlanModel or None
        """
        plan = self.get_plan_by_id(db, plan_id)

        if not plan:
            return None

        plan.status = 'failed'
        plan.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(plan)

        logger.info(f"Plan {plan_id} marked as failed")

        return plan

    def delete_plan(
        self,
        db: Session,
        plan_id: UUID
    ) -> bool:
        """
        Delete a sync plan

        Args:
            db: Database session
            plan_id: Plan UUID

        Returns:
            True if deleted, False if not found
        """
        plan = self.get_plan_by_id(db, plan_id)

        if not plan:
            return False

        db.delete(plan)
        db.commit()

        logger.info(f"Plan {plan_id} deleted")

        return True

    def invalidate_expired(self, db: Session) -> int:
        """
        Mark expired plans as expired

        Args:
            db: Database session

        Returns:
            Number of plans marked as expired
        """
        query = text("""
            UPDATE sync_plans
            SET status = 'expired'
            WHERE status IN ('pending', 'approved')
            AND expires_at IS NOT NULL
            AND expires_at < NOW()
        """)

        result = db.execute(query)
        db.commit()

        expired_count = result.rowcount
        logger.info(f"Marked {expired_count} sync plans as expired")

        return expired_count

    def cleanup_old_plans(
        self,
        db: Session,
        days_old: int = 30
    ) -> int:
        """
        Delete old completed/failed plans

        Args:
            db: Database session
            days_old: Delete plans older than this many days

        Returns:
            Number of plans deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        query = text("""
            DELETE FROM sync_plans
            WHERE status IN ('completed', 'failed', 'expired')
            AND created_at < :cutoff_date
        """)

        result = db.execute(query, {"cutoff_date": cutoff_date})
        db.commit()

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} old sync plans (>{days_old} days)")

        return deleted_count
