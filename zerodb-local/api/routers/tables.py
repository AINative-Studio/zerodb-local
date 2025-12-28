"""
Tables Router
Handles NoSQL table operations (CRUD, query, insert, update, delete)
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import authentication
try:
    from app.api.deps import get_current_user_flexible
    from app.models.user import User
except ImportError:
    class MockUser:
        def __init__(self):
            self.id = "00000000-0000-0000-0000-000000000001"
    def get_current_user_flexible():
        return lambda: MockUser()

# Import services
from services.database_service import database_service
from services.tables_service import tables_service


router = APIRouter()


# Schemas
class TableCreate(BaseModel):
    """Schema for creating a table"""
    table_name: str = Field(..., description="Table name (unique per project)")
    schema: Dict[str, Any] = Field(..., description="JSON schema definition")
    description: Optional[str] = Field(default=None, description="Optional description")

    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "users",
                "schema": {
                    "fields": {
                        "name": {"type": "string", "required": True},
                        "email": {"type": "string", "required": True},
                        "age": {"type": "integer", "required": False}
                    }
                },
                "description": "User data table"
            }
        }


class TableResponse(BaseModel):
    """Schema for table response"""
    id: str
    name: str
    schema: Dict[str, Any]
    description: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class TableQuery(BaseModel):
    """Schema for querying table rows"""
    filter: Optional[Dict[str, Any]] = Field(default=None, description="JSONB filter")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class TableRowInsert(BaseModel):
    """Schema for inserting rows"""
    rows: List[Dict[str, Any]] = Field(..., description="Rows to insert")


class TableRowUpdate(BaseModel):
    """Schema for updating rows"""
    filter: Dict[str, Any] = Field(..., description="JSONB filter to match rows")
    update: Dict[str, Any] = Field(..., description="Data to update")


class TableRowDelete(BaseModel):
    """Schema for deleting rows"""
    filter: Dict[str, Any] = Field(..., description="JSONB filter to match rows")


class TableRowResponse(BaseModel):
    """Schema for table row response"""
    id: str
    data: Dict[str, Any]
    created_at: Optional[str]
    updated_at: Optional[str]


class InsertResponse(BaseModel):
    """Schema for insert operation response"""
    table_name: str
    inserted_count: int
    inserted_ids: List[str]


class UpdateResponse(BaseModel):
    """Schema for update operation response"""
    table_name: str
    updated_count: int


class DeleteResponse(BaseModel):
    """Schema for delete operation response"""
    table_name: str
    deleted_count: int


# Endpoints

@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    project_id: UUID,
    table: TableCreate,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Create a new NoSQL table

    **Authentication:** Required

    **Parameters:**
    - table_name: Table name (unique per project)
    - schema: JSON schema definition
    - description: Optional description

    **Returns:**
    - Table object with generated ID
    """
    try:
        result = await tables_service.create_table(
            db=db,
            project_id=project_id,
            table_name=table.table_name,
            schema=table.schema,
            description=table.description
        )

        return TableResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating table: {str(e)}"
        )


@router.get("", response_model=List[TableResponse])
async def list_tables(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    List all tables

    **Authentication:** Required

    **Query Parameters:**
    - skip: Number to skip for pagination
    - limit: Max results (max 100)

    **Returns:**
    - List of tables
    """
    try:
        if limit > 100:
            limit = 100

        results = await tables_service.list_tables(
            db=db,
            project_id=project_id,
            skip=skip,
            limit=limit
        )

        return [TableResponse(**result) for result in results]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing tables: {str(e)}"
        )


@router.get("/{table_name}", response_model=TableResponse)
async def get_table(
    project_id: UUID,
    table_name: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get table by name

    **Authentication:** Required

    **Path Parameters:**
    - table_name: Table name

    **Returns:**
    - Table object
    """
    try:
        result = await tables_service.get_table(
            db=db,
            project_id=project_id,
            table_name=table_name
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found"
            )

        return TableResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving table: {str(e)}"
        )


@router.delete("/{table_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    project_id: UUID,
    table_name: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Delete table (soft delete, cascade deletes rows)

    **Authentication:** Required

    **Path Parameters:**
    - table_name: Table name

    **Returns:**
    - 204 No Content on success
    """
    try:
        deleted = await tables_service.delete_table(
            db=db,
            project_id=project_id,
            table_name=table_name
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting table: {str(e)}"
        )


@router.post("/{table_name}/insert", response_model=InsertResponse)
async def insert_rows(
    project_id: UUID,
    table_name: str,
    insert_data: TableRowInsert,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Insert rows into table

    **Authentication:** Required

    **Path Parameters:**
    - table_name: Table name

    **Body:**
    - rows: List of row data dicts

    **Returns:**
    - Insert results with IDs
    """
    try:
        result = await tables_service.insert_rows(
            db=db,
            project_id=project_id,
            table_name=table_name,
            rows=insert_data.rows
        )

        return InsertResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inserting rows: {str(e)}"
        )


@router.post("/{table_name}/query", response_model=List[TableRowResponse])
async def query_rows(
    project_id: UUID,
    table_name: str,
    query: TableQuery,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Query rows from table

    **Authentication:** Required

    **Path Parameters:**
    - table_name: Table name

    **Body:**
    - filter: Optional JSONB filter (PostgreSQL @> operator)
    - limit: Max results (1-1000)
    - offset: Pagination offset

    **Returns:**
    - List of matching rows
    """
    try:
        results = await tables_service.query_rows(
            db=db,
            project_id=project_id,
            table_name=table_name,
            filter_data=query.filter,
            skip=query.offset,
            limit=query.limit
        )

        return [TableRowResponse(**result) for result in results]

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying rows: {str(e)}"
        )


@router.put("/{table_name}/update", response_model=UpdateResponse)
async def update_rows(
    project_id: UUID,
    table_name: str,
    update_data: TableRowUpdate,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Update rows in table

    **Authentication:** Required

    **Path Parameters:**
    - table_name: Table name

    **Body:**
    - filter: JSONB filter to match rows (PostgreSQL @> operator)
    - update: Data to update (merged with existing data using || operator)

    **Returns:**
    - Number of rows updated
    """
    try:
        updated_count = await tables_service.update_rows(
            db=db,
            project_id=project_id,
            table_name=table_name,
            filter_data=update_data.filter,
            update_data=update_data.update
        )

        return UpdateResponse(
            table_name=table_name,
            updated_count=updated_count
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating rows: {str(e)}"
        )


@router.delete("/{table_name}/rows", response_model=DeleteResponse)
async def delete_rows(
    project_id: UUID,
    table_name: str,
    delete_data: TableRowDelete,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Delete rows from table (soft delete)

    **Authentication:** Required

    **Path Parameters:**
    - table_name: Table name

    **Body:**
    - filter: JSONB filter to match rows (PostgreSQL @> operator)

    **Returns:**
    - Number of rows deleted
    """
    try:
        deleted_count = await tables_service.delete_rows(
            db=db,
            project_id=project_id,
            table_name=table_name,
            filter_data=delete_data.filter
        )

        return DeleteResponse(
            table_name=table_name,
            deleted_count=deleted_count
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting rows: {str(e)}"
        )
