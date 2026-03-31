"""
Vectors Router
Handles vector storage and semantic search operations
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import authentication
from auth import get_current_user_flexible, User
# Import services
from services.database_service import database_service
from services.vector_service import vector_service


router = APIRouter()


# Schemas
class VectorUpsert(BaseModel):
    """Schema for upserting a single vector"""
    document: str = Field(..., description="Text document to embed and store")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")
    namespace: str = Field(default="default", description="Vector namespace")
    vector_id: Optional[str] = Field(None, description="Optional custom vector ID")

    class Config:
        json_schema_extra = {
            "example": {
                "document": "The quick brown fox jumps over the lazy dog",
                "metadata": {"source": "example", "category": "animals"},
                "namespace": "default"
            }
        }


class VectorBatchUpsert(BaseModel):
    """Schema for batch upserting vectors"""
    vectors: List[VectorUpsert] = Field(..., description="List of vectors to upsert")


class VectorSearch(BaseModel):
    """Schema for vector search"""
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Max results to return")
    threshold: float = Field(default=0.7, ge=0, le=1, description="Similarity threshold")
    namespace: Optional[str] = Field(default="default", description="Search namespace")
    filter_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class VectorResponse(BaseModel):
    """Schema for vector response"""
    id: str
    vector_id: str
    document: str
    metadata: Dict[str, Any]
    namespace: str
    dimensions: int
    created_at: Optional[str]
    updated_at: Optional[str]


class VectorSearchResult(BaseModel):
    """Schema for search result"""
    id: str
    vector_id: str
    document: str
    metadata: Dict[str, Any]
    score: float
    namespace: str


class VectorStats(BaseModel):
    """Schema for vector statistics"""
    total_vectors: int
    namespace_count: int
    dimensions: int
    namespace: Optional[str]


# Endpoints

@router.post("/upsert", response_model=VectorResponse)
async def upsert_vector(
    project_id: UUID,
    vector: VectorUpsert,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Upsert a vector (create or update)

    **Flow:**
    1. Generate embedding from document text (local embeddings service)
    2. Store vector in Qdrant (fast search)
    3. Store metadata in PostgreSQL (backup + filtering)
    4. Emit CDC event to RedPanda

    **Authentication:** Required

    **Parameters:**
    - document: Text to embed and store
    - metadata: Optional JSON metadata
    - namespace: Vector namespace (default: "default")
    - vector_id: Optional custom vector ID

    **Returns:**
    - Vector object with generated/updated ID
    """
    try:
        result = await vector_service.upsert_vector(
            db=db,
            project_id=project_id,
            document=vector.document,
            metadata=vector.metadata or {},
            namespace=vector.namespace,
            vector_id=vector.vector_id
        )

        return VectorResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error upserting vector: {str(e)}"
        )


@router.post("/upsert-batch")
async def upsert_batch_vectors(
    project_id: UUID,
    batch: VectorBatchUpsert,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Batch upsert multiple vectors

    **Flow:**
    1. Process each vector in parallel
    2. Store all in PostgreSQL and Qdrant
    3. Return results with counts

    **Authentication:** Required

    **Parameters:**
    - vectors: List of vector objects to upsert

    **Returns:**
    - List of created/updated vectors
    - Success/failure counts
    """
    try:
        results = []
        errors = []

        for idx, vec in enumerate(batch.vectors):
            try:
                result = await vector_service.upsert_vector(
                    db=db,
                    project_id=project_id,
                    document=vec.document,
                    metadata=vec.metadata or {},
                    namespace=vec.namespace,
                    vector_id=vec.vector_id
                )
                results.append(result)
            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": str(e)
                })

        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error batch upserting vectors: {str(e)}"
        )


@router.post("/search", response_model=List[VectorSearchResult])
async def search_vectors(
    project_id: UUID,
    search: VectorSearch,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Search for similar vectors using semantic search

    **Flow:**
    1. Generate embedding from query text
    2. Search Qdrant for similar vectors
    3. Apply metadata filters if provided
    4. Return results with similarity scores

    **Authentication:** Required

    **Parameters:**
    - query: Search query text
    - limit: Max results (1-100)
    - threshold: Similarity threshold (0-1)
    - namespace: Search in specific namespace
    - filter_metadata: Optional metadata filters

    **Returns:**
    - List of matching vectors with similarity scores
    """
    try:
        results = await vector_service.search_vectors(
            db=db,
            project_id=project_id,
            query=search.query,
            limit=search.limit,
            threshold=search.threshold,
            namespace=search.namespace,
            filter_metadata=search.filter_metadata
        )

        return [VectorSearchResult(**result) for result in results]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching vectors: {str(e)}"
        )


@router.get("", response_model=List[VectorResponse])
async def list_vectors(
    project_id: UUID,
    namespace: str = "default",
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    List vectors in a namespace with pagination

    **Authentication:** Required

    **Query Parameters:**
    - namespace: Vector namespace (default: "default")
    - skip: Number to skip for pagination
    - limit: Max results (max 100)

    **Returns:**
    - List of vectors
    """
    try:
        if limit > 100:
            limit = 100

        results = await vector_service.list_vectors(
            db=db,
            project_id=project_id,
            namespace=namespace,
            skip=skip,
            limit=limit
        )

        return [
            VectorResponse(
                **result,
                dimensions=384  # Default dimensions (from embeddings model)
            )
            for result in results
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing vectors: {str(e)}"
        )


@router.get("/stats", response_model=VectorStats)
async def get_vector_stats(
    project_id: UUID,
    namespace: Optional[str] = None,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """Get vector statistics for a project"""
    try:
        stats = await vector_service.get_stats(db=db, project_id=project_id, namespace=namespace)
        return VectorStats(**stats)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error retrieving vector stats: {str(e)}")


@router.get("/{vector_id}", response_model=VectorResponse)
async def get_vector(
    project_id: UUID,
    vector_id: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get a specific vector by ID

    **Authentication:** Required

    **Path Parameters:**
    - vector_id: Vector ID

    **Returns:**
    - Vector object
    """
    try:
        result = await vector_service.get_vector(
            db=db,
            project_id=project_id,
            vector_id=vector_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vector not found"
            )

        return VectorResponse(
            **result,
            dimensions=384  # Default dimensions
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving vector: {str(e)}"
        )


@router.delete("/{vector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vector(
    project_id: UUID,
    vector_id: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Delete a specific vector by ID

    **Authentication:** Required

    **Path Parameters:**
    - vector_id: Vector ID

    **Returns:**
    - 204 No Content on success
    """
    try:
        deleted = await vector_service.delete_vector(
            db=db,
            project_id=project_id,
            vector_id=vector_id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vector not found"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting vector: {str(e)}"
        )


    # /stats route defined above /{vector_id} to prevent path collision
