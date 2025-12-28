"""
Projects Router
Handles project management operations (CRUD)
"""
from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

# Import schemas
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStats

# Import authentication from core backend (when available)
try:
    from app.api.deps import get_current_user_flexible
    from app.models.user import User
except ImportError:
    # Fallback for isolated testing
    print("Warning: Core authentication not available. Using mock auth for development.")
    class MockUser:
        def __init__(self):
            self.id = "00000000-0000-0000-0000-000000000001"
            self.email = "dev@localhost"
            self.organization_id = None

    def get_current_user_flexible():
        return lambda: MockUser()

# Import database service
from services.database_service import database_service


router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Create a new project

    **Authentication:** Required

    **Parameters:**
    - name: Project name (1-255 characters)
    - description: Optional project description
    - settings: Optional JSON settings

    **Returns:**
    - Project object with generated UUID
    """
    # Check if project name already exists for this user
    check_query = text("""
        SELECT id FROM projects
        WHERE user_id = :user_id
        AND name = :name
        AND deleted_at IS NULL
    """)

    existing = db.execute(
        check_query,
        {"user_id": str(current_user.id), "name": project.name}
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{project.name}' already exists"
        )

    # Create project
    insert_query = text("""
        INSERT INTO projects (name, description, user_id, organization_id, settings)
        VALUES (:name, :description, :user_id, :organization_id, :settings::jsonb)
        RETURNING id, name, description, user_id, organization_id, settings, created_at, updated_at
    """)

    result = db.execute(
        insert_query,
        {
            "name": project.name,
            "description": project.description,
            "user_id": str(current_user.id),
            "organization_id": str(current_user.organization_id) if hasattr(current_user, 'organization_id') and current_user.organization_id else None,
            "settings": str(project.settings) if project.settings else "{}"
        }
    ).first()

    db.commit()

    return ProjectResponse(
        id=result.id,
        name=result.name,
        description=result.description,
        user_id=result.user_id,
        organization_id=result.organization_id,
        settings=result.settings if result.settings else {},
        created_at=result.created_at,
        updated_at=result.updated_at
    )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    List all projects for the current user

    **Authentication:** Required

    **Query Parameters:**
    - skip: Number of projects to skip (pagination)
    - limit: Maximum number of projects to return (max 100)

    **Returns:**
    - List of project objects
    """
    if limit > 100:
        limit = 100

    query = text("""
        SELECT id, name, description, user_id, organization_id, settings, created_at, updated_at
        FROM projects
        WHERE user_id = :user_id
        AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    results = db.execute(
        query,
        {"user_id": str(current_user.id), "limit": limit, "offset": skip}
    ).fetchall()

    return [
        ProjectResponse(
            id=row.id,
            name=row.name,
            description=row.description,
            user_id=row.user_id,
            organization_id=row.organization_id,
            settings=row.settings if row.settings else {},
            created_at=row.created_at,
            updated_at=row.updated_at
        )
        for row in results
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get a specific project by ID

    **Authentication:** Required

    **Path Parameters:**
    - project_id: UUID of the project

    **Returns:**
    - Project object
    """
    query = text("""
        SELECT id, name, description, user_id, organization_id, settings, created_at, updated_at
        FROM projects
        WHERE id = :project_id
        AND user_id = :user_id
        AND deleted_at IS NULL
    """)

    result = db.execute(
        query,
        {"project_id": str(project_id), "user_id": str(current_user.id)}
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return ProjectResponse(
        id=result.id,
        name=result.name,
        description=result.description,
        user_id=result.user_id,
        organization_id=result.organization_id,
        settings=result.settings if result.settings else {},
        created_at=result.created_at,
        updated_at=result.updated_at
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project: ProjectUpdate,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Update a project

    **Authentication:** Required

    **Path Parameters:**
    - project_id: UUID of the project

    **Body:**
    - name: New project name (optional)
    - description: New description (optional)
    - settings: Updated settings (optional)

    **Returns:**
    - Updated project object
    """
    # Check project exists and user owns it
    check_query = text("""
        SELECT id FROM projects
        WHERE id = :project_id
        AND user_id = :user_id
        AND deleted_at IS NULL
    """)

    exists = db.execute(
        check_query,
        {"project_id": str(project_id), "user_id": str(current_user.id)}
    ).first()

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Build dynamic update query
    update_fields = []
    params = {"project_id": str(project_id), "user_id": str(current_user.id)}

    if project.name is not None:
        update_fields.append("name = :name")
        params["name"] = project.name

    if project.description is not None:
        update_fields.append("description = :description")
        params["description"] = project.description

    if project.settings is not None:
        update_fields.append("settings = :settings::jsonb")
        params["settings"] = str(project.settings)

    if not update_fields:
        # No fields to update, just return current project
        return await get_project(project_id, current_user, db)

    update_fields.append("updated_at = NOW()")

    update_query = text(f"""
        UPDATE projects
        SET {', '.join(update_fields)}
        WHERE id = :project_id
        AND user_id = :user_id
        RETURNING id, name, description, user_id, organization_id, settings, created_at, updated_at
    """)

    result = db.execute(update_query, params).first()
    db.commit()

    return ProjectResponse(
        id=result.id,
        name=result.name,
        description=result.description,
        user_id=result.user_id,
        organization_id=result.organization_id,
        settings=result.settings if result.settings else {},
        created_at=result.created_at,
        updated_at=result.updated_at
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Delete a project (soft delete)

    **Authentication:** Required
    **⚠️ WARNING:** This will soft-delete the project.
    Cascade deletion of vectors, tables, files, and events is handled by the database.

    **Path Parameters:**
    - project_id: UUID of the project

    **Returns:**
    - 204 No Content on success
    """
    # Soft delete the project
    delete_query = text("""
        UPDATE projects
        SET deleted_at = NOW()
        WHERE id = :project_id
        AND user_id = :user_id
        AND deleted_at IS NULL
        RETURNING id
    """)

    result = db.execute(
        delete_query,
        {"project_id": str(project_id), "user_id": str(current_user.id)}
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    db.commit()
    return None


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get project statistics

    **Authentication:** Required

    **Path Parameters:**
    - project_id: UUID of the project

    **Returns:**
    - vector_count: Number of vectors
    - memory_count: Number of memory entries
    - table_count: Number of tables
    - file_count: Number of files
    - event_count: Number of events
    - storage_bytes: Total storage used (bytes)
    """
    # Verify project exists and user owns it
    check_query = text("""
        SELECT id FROM projects
        WHERE id = :project_id
        AND user_id = :user_id
        AND deleted_at IS NULL
    """)

    exists = db.execute(
        check_query,
        {"project_id": str(project_id), "user_id": str(current_user.id)}
    ).first()

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get counts from各 tables
    stats_query = text("""
        SELECT
            (SELECT COUNT(*) FROM vectors WHERE project_id = :project_id) as vector_count,
            (SELECT COUNT(*) FROM memory WHERE project_id = :project_id) as memory_count,
            (SELECT COUNT(*) FROM tables WHERE project_id = :project_id AND deleted_at IS NULL) as table_count,
            (SELECT COUNT(*) FROM files WHERE project_id = :project_id AND deleted_at IS NULL) as file_count,
            (SELECT COUNT(*) FROM events WHERE project_id = :project_id) as event_count,
            (SELECT COALESCE(SUM(file_size), 0) FROM files WHERE project_id = :project_id AND deleted_at IS NULL) as storage_bytes
    """)

    result = db.execute(stats_query, {"project_id": str(project_id)}).first()

    return ProjectStats(
        project_id=project_id,
        vector_count=result.vector_count or 0,
        memory_count=result.memory_count or 0,
        table_count=result.table_count or 0,
        file_count=result.file_count or 0,
        event_count=result.event_count or 0,
        storage_bytes=result.storage_bytes or 0
    )
