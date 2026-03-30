"""
Memory Service
Handles agent memory storage and retrieval using PostgreSQL + Qdrant + Local Embeddings
"""
import os
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.embeddings_service import embeddings_service
from services.qdrant_service import qdrant_service


class MemoryService:
    """
    Service for agent memory operations

    Architecture:
    - PostgreSQL: Stores memory content and embeddings (persistent storage)
    - Qdrant: Provides fast semantic search
    - Embeddings Service: Generates vectors locally (no API costs)
    """

    def __init__(self):
        self.default_collection = os.getenv("QDRANT_COLLECTION_NAME", "zerodb_local")
        self.vector_dimensions = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))

    async def store_memory(
        self,
        db: Session,
        project_id: UUID,
        content: str,
        role: str,
        agent_id: Optional[str] = "default",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store agent memory

        Steps:
        1. Generate embedding from content
        2. Store in PostgreSQL (persistent memory)
        3. Store in Qdrant (fast search)

        Args:
            db: Database session
            project_id: Project UUID
            content: Memory content
            role: Message role (user/assistant/system)
            agent_id: Agent identifier
            session_id: Session identifier
            metadata: Optional metadata dict

        Returns:
            Created memory info
        """
        # Step 1: Generate embedding
        embeddings = await embeddings_service.generate_embeddings([content])
        embedding = embeddings[0]

        # Step 2: Store in PostgreSQL
        insert_query = text("""
            INSERT INTO memory (project_id, session_id, agent_id, role, content, embedding, metadata)
            VALUES (:project_id, :session_id, :agent_id, :role, :content, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
            RETURNING id, session_id, agent_id, role, content, metadata, created_at
        """)

        result = db.execute(
            insert_query,
            {
                "project_id": str(project_id),
                "session_id": session_id,
                "agent_id": agent_id,
                "role": role,
                "content": content,
                "embedding": str(embedding),
                "metadata": str(metadata or {})
            }
        ).first()

        db.commit()

        memory_id = str(result.id)

        # Step 3: Store in Qdrant
        qdrant_id = f"{project_id}_memory_{memory_id}"
        await qdrant_service.upsert_vector(
            project_id=project_id,
            vector_id=qdrant_id,
            embedding=embedding,
            payload={
                **(metadata or {}),
                "content": content,
                "role": role,
                "agent_id": agent_id,
                "session_id": session_id,
                "pg_id": memory_id,
                "type": "memory"
            }
        )

        return {
            "id": memory_id,
            "session_id": result.session_id,
            "agent_id": result.agent_id,
            "role": result.role,
            "content": result.content,
            "metadata": result.metadata or {},
            "created_at": result.created_at.isoformat() if result.created_at else None
        }

    async def search_memory(
        self,
        db: Session,
        project_id: UUID,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search agent memory using semantic search

        Steps:
        1. Generate embedding from query text
        2. Search Qdrant for similar memories
        3. Apply filters (agent_id, session_id, role)

        Args:
            db: Database session
            project_id: Project UUID
            query: Search query text
            limit: Max results to return
            threshold: Similarity threshold (0-1)
            agent_id: Filter by agent ID
            session_id: Filter by session ID
            role: Filter by role

        Returns:
            List of matching memories with scores
        """
        # Generate query embedding
        embeddings = await embeddings_service.generate_embeddings([query])
        query_embedding = embeddings[0]

        # Search Qdrant
        results = await qdrant_service.search_vectors(
            project_id=project_id,
            query_vector=query_embedding,
            limit=limit * 2,  # Get more results for filtering
            threshold=threshold
        )

        # Filter by metadata
        filtered_results = []
        for result in results:
            metadata = result.get("metadata", {})

            # Skip non-memory entries
            if metadata.get("type") != "memory":
                continue

            # Check agent_id filter
            if agent_id and metadata.get("agent_id") != agent_id:
                continue

            # Check session_id filter
            if session_id and metadata.get("session_id") != session_id:
                continue

            # Check role filter
            if role and metadata.get("role") != role:
                continue

            filtered_results.append({
                "id": metadata.get("pg_id"),
                "session_id": metadata.get("session_id"),
                "agent_id": metadata.get("agent_id"),
                "role": metadata.get("role"),
                "content": metadata.get("content"),
                "metadata": {k: v for k, v in metadata.items()
                           if k not in ["content", "role", "agent_id", "session_id", "pg_id", "type"]},
                "score": result.get("score")
            })

            if len(filtered_results) >= limit:
                break

        return filtered_results

    async def get_context_window(
        self,
        db: Session,
        project_id: UUID,
        session_id: str,
        limit: int = 50,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get agent context window for a session

        Retrieves recent messages in chronological order for LLM context.

        Args:
            db: Database session
            project_id: Project UUID
            session_id: Session identifier
            limit: Max messages to retrieve
            max_tokens: Optional token limit (approximate)

        Returns:
            Context window with messages and metadata
        """
        query = text("""
            SELECT id, session_id, agent_id, role, content, metadata, created_at
            FROM memory
            WHERE project_id = :project_id
            AND session_id = :session_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        results = db.execute(
            query,
            {
                "project_id": str(project_id),
                "session_id": session_id,
                "limit": limit
            }
        ).fetchall()

        # Reverse to get chronological order (oldest first)
        messages = [
            {
                "id": str(row.id),
                "session_id": row.session_id,
                "agent_id": row.agent_id,
                "role": row.role,
                "content": row.content,
                "metadata": row.metadata or {},
                "created_at": row.created_at.isoformat() if row.created_at else None
            }
            for row in reversed(results)
        ]

        # Calculate approximate token count (rough estimate: 1 token ≈ 4 chars)
        total_chars = sum(len(msg["content"]) for msg in messages)
        estimated_tokens = total_chars // 4

        # Truncate if max_tokens specified
        if max_tokens and estimated_tokens > max_tokens:
            truncated_messages = []
            current_tokens = 0
            for msg in messages:
                msg_tokens = len(msg["content"]) // 4
                if current_tokens + msg_tokens > max_tokens:
                    break
                truncated_messages.append(msg)
                current_tokens += msg_tokens
            messages = truncated_messages
            estimated_tokens = current_tokens

        return {
            "session_id": session_id,
            "messages": messages,
            "message_count": len(messages),
            "estimated_tokens": estimated_tokens,
            "truncated": max_tokens is not None and len(results) > len(messages)
        }

    async def list_sessions(
        self,
        db: Session,
        project_id: UUID,
        agent_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List memory sessions with message counts

        Args:
            db: Database session
            project_id: Project UUID
            agent_id: Optional filter by agent ID
            skip: Number to skip (pagination)
            limit: Max results

        Returns:
            List of sessions with metadata
        """
        if agent_id:
            query = text("""
                SELECT
                    session_id,
                    agent_id,
                    COUNT(*) as message_count,
                    MIN(created_at) as first_message_at,
                    MAX(created_at) as last_message_at
                FROM memory
                WHERE project_id = :project_id
                AND agent_id = :agent_id
                AND session_id IS NOT NULL
                GROUP BY session_id, agent_id
                ORDER BY MAX(created_at) DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {
                "project_id": str(project_id),
                "agent_id": agent_id,
                "limit": limit,
                "offset": skip
            }
        else:
            query = text("""
                SELECT
                    session_id,
                    agent_id,
                    COUNT(*) as message_count,
                    MIN(created_at) as first_message_at,
                    MAX(created_at) as last_message_at
                FROM memory
                WHERE project_id = :project_id
                AND session_id IS NOT NULL
                GROUP BY session_id, agent_id
                ORDER BY MAX(created_at) DESC
                LIMIT :limit OFFSET :offset
            """)
            params = {
                "project_id": str(project_id),
                "limit": limit,
                "offset": skip
            }

        results = db.execute(query, params).fetchall()

        return [
            {
                "session_id": row.session_id,
                "agent_id": row.agent_id,
                "message_count": row.message_count,
                "first_message_at": row.first_message_at.isoformat() if row.first_message_at else None,
                "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None
            }
            for row in results
        ]

    async def delete_session(
        self,
        db: Session,
        project_id: UUID,
        session_id: str
    ) -> int:
        """
        Delete all memories for a session

        Args:
            db: Database session
            project_id: Project UUID
            session_id: Session identifier

        Returns:
            Number of memories deleted
        """
        # Get memory IDs before deleting
        select_query = text("""
            SELECT id FROM memory
            WHERE project_id = :project_id
            AND session_id = :session_id
        """)

        results = db.execute(
            select_query,
            {"project_id": str(project_id), "session_id": session_id}
        ).fetchall()

        memory_ids = [str(row.id) for row in results]

        # Delete from PostgreSQL
        delete_query = text("""
            DELETE FROM memory
            WHERE project_id = :project_id
            AND session_id = :session_id
        """)

        db.execute(
            delete_query,
            {"project_id": str(project_id), "session_id": session_id}
        )

        db.commit()

        # Delete from Qdrant
        for memory_id in memory_ids:
            qdrant_id = f"{project_id}_memory_{memory_id}"
            try:
                await qdrant_service.delete_vector(
                    project_id=project_id,
                    vector_id=qdrant_id
                )
            except Exception:
                pass  # Continue even if Qdrant delete fails

        return len(memory_ids)


# Global instance
memory_service = MemoryService()
