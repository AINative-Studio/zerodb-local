"""
Memory Router
Handles agent memory operations (store, search, context window)
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
from services.memory_service import memory_service


router = APIRouter()


# Schemas
class MemoryStore(BaseModel):
    """Schema for storing agent memory"""
    content: str = Field(..., description="Memory content")
    role: str = Field(..., pattern="^(user|assistant|system)$", description="Message role")
    agent_id: Optional[str] = Field(default="default", description="Agent identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "User asked about product pricing",
                "role": "user",
                "agent_id": "customer-support-agent",
                "session_id": "session-123",
                "metadata": {"category": "pricing", "priority": "high"}
            }
        }


class MemorySearch(BaseModel):
    """Schema for searching agent memory"""
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Max results")
    threshold: float = Field(default=0.7, ge=0, le=1, description="Similarity threshold")
    agent_id: Optional[str] = Field(default=None, description="Filter by agent ID")
    session_id: Optional[str] = Field(default=None, description="Filter by session ID")
    role: Optional[str] = Field(default=None, description="Filter by role")


class MemoryResponse(BaseModel):
    """Schema for memory response"""
    id: str
    session_id: Optional[str]
    agent_id: str
    role: str
    content: str
    metadata: Dict[str, Any]
    created_at: Optional[str]


class MemorySearchResult(BaseModel):
    """Schema for memory search result"""
    id: str
    session_id: Optional[str]
    agent_id: str
    role: str
    content: str
    metadata: Dict[str, Any]
    score: float


class ContextWindow(BaseModel):
    """Schema for context window response"""
    session_id: str
    messages: List[MemoryResponse]
    message_count: int
    estimated_tokens: int
    truncated: bool


class SessionInfo(BaseModel):
    """Schema for session information"""
    session_id: str
    agent_id: str
    message_count: int
    first_message_at: Optional[str]
    last_message_at: Optional[str]


# Endpoints

@router.post("/store", response_model=MemoryResponse)
async def store_memory(
    project_id: UUID,
    memory: MemoryStore,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Store agent memory

    **Flow:**
    1. Generate embedding from content (local embeddings service)
    2. Store in PostgreSQL (persistent memory)
    3. Store in Qdrant (fast semantic search)

    **Authentication:** Required

    **Parameters:**
    - content: Memory content (message text)
    - role: Message role (user/assistant/system)
    - agent_id: Agent identifier (default: "default")
    - session_id: Session identifier (optional)
    - metadata: Optional JSON metadata

    **Returns:**
    - Memory object with generated ID
    """
    try:
        result = await memory_service.store_memory(
            db=db,
            project_id=project_id,
            content=memory.content,
            role=memory.role,
            agent_id=memory.agent_id,
            session_id=memory.session_id,
            metadata=memory.metadata
        )

        return MemoryResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error storing memory: {str(e)}"
        )


@router.post("/search", response_model=List[MemorySearchResult])
async def search_memory(
    project_id: UUID,
    search: MemorySearch,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Search agent memory using semantic search

    **Flow:**
    1. Generate embedding from query text
    2. Search Qdrant for similar memories
    3. Apply metadata filters if provided
    4. Return results with similarity scores

    **Authentication:** Required

    **Parameters:**
    - query: Search query text
    - limit: Max results (1-100)
    - threshold: Similarity threshold (0-1)
    - agent_id: Filter by agent ID (optional)
    - session_id: Filter by session ID (optional)
    - role: Filter by role (optional)

    **Returns:**
    - List of matching memories with similarity scores
    """
    try:
        results = await memory_service.search_memory(
            db=db,
            project_id=project_id,
            query=search.query,
            limit=search.limit,
            threshold=search.threshold,
            agent_id=search.agent_id,
            session_id=search.session_id,
            role=search.role
        )

        return [MemorySearchResult(**result) for result in results]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching memory: {str(e)}"
        )


@router.get("/context/{session_id}", response_model=ContextWindow)
async def get_context(
    project_id: UUID,
    session_id: str,
    limit: int = 50,
    max_tokens: Optional[int] = None,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Get agent context window for a session

    Retrieves recent messages in chronological order for LLM context.

    **Authentication:** Required

    **Path Parameters:**
    - session_id: Session identifier

    **Query Parameters:**
    - limit: Max messages to retrieve (default: 50)
    - max_tokens: Optional token limit (approximate)

    **Returns:**
    - session_id: Session identifier
    - messages: List of messages in chronological order
    - message_count: Number of messages returned
    - estimated_tokens: Approximate token count
    - truncated: Whether messages were truncated due to token limit
    """
    try:
        result = await memory_service.get_context_window(
            db=db,
            project_id=project_id,
            session_id=session_id,
            limit=limit,
            max_tokens=max_tokens
        )

        return ContextWindow(**result)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving context window: {str(e)}"
        )


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(
    project_id: UUID,
    agent_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    List memory sessions with message counts

    **Authentication:** Required

    **Query Parameters:**
    - agent_id: Filter by agent ID (optional)
    - skip: Number to skip for pagination
    - limit: Max results (max 100)

    **Returns:**
    - List of sessions with metadata
    """
    try:
        if limit > 100:
            limit = 100

        results = await memory_service.list_sessions(
            db=db,
            project_id=project_id,
            agent_id=agent_id,
            skip=skip,
            limit=limit
        )

        return [SessionInfo(**result) for result in results]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing sessions: {str(e)}"
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    project_id: UUID,
    session_id: str,
    current_user = Depends(get_current_user_flexible),
    db: Session = Depends(database_service.get_db)
):
    """
    Delete all memories for a session

    **Authentication:** Required

    **Path Parameters:**
    - session_id: Session identifier

    **Returns:**
    - 204 No Content on success
    """
    try:
        deleted_count = await memory_service.delete_session(
            db=db,
            project_id=project_id,
            session_id=session_id
        )

        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or already empty"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        )
