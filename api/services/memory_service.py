"""
Memory Service
Handles agent memory storage and retrieval using PostgreSQL + Qdrant + Local Embeddings
"""
import json
import os
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.embeddings_service import embeddings_service
from services.qdrant_service import qdrant_service
from lite.config import is_lite_mode
from lite.sql_compat import jsonb_cast_sql, log_cdc_change, new_id, parse_json_column, to_isoformat


def _embedding_cast_sql(expr: str) -> str:
    """
    SQL fragment to store an embedding bind parameter.

    PostgreSQL (pgvector) needs CAST(:x AS vector) to coerce the text
    representation into its native vector type. SQLite has no vector type
    at all -- the `memory` table stores embeddings in a BLOB column (see
    lite/db/schema_lite.sql), and this service's own Qdrant/FAISS call is
    the actual similarity-search path, so the SQLite column is write-only
    backup storage: pass the bind parameter through unchanged.
    """
    return expr if is_lite_mode() else f"CAST({expr} AS vector)"


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

        # Step 2: Store in PostgreSQL. In lite mode `id` has no SQL-level
        # default (Postgres's schema declares DEFAULT gen_random_uuid(),
        # SQLite's does not), so generate it explicitly.
        lite = is_lite_mode()
        columns = "project_id, session_id, agent_id, role, content, embedding, metadata"
        values = (
            f":project_id, :session_id, :agent_id, :role, :content, "
            f"{_embedding_cast_sql(':embedding')}, {jsonb_cast_sql(':metadata', lite)}"
        )
        params = {
            "project_id": str(project_id),
            "session_id": session_id,
            "agent_id": agent_id,
            "role": role,
            "content": content,
            "embedding": str(embedding),
            "metadata": json.dumps(metadata or {})
        }
        if lite:
            columns = "id, " + columns
            values = ":id, " + values
            params["id"] = new_id()

        insert_query = text(f"""
            INSERT INTO memory ({columns})
            VALUES ({values})
            RETURNING id, session_id, agent_id, role, content, metadata, created_at
        """)

        result = db.execute(insert_query, params).first()

        # Application-level CDC (Refs #63): full mode logs this via the
        # memory table's INSERT trigger; lite mode has no trigger support,
        # so log the same change_log row explicitly before committing, so
        # it lands atomically with the memory row it describes.
        if lite:
            log_cdc_change(
                db, project_id, "memory", result.id, "INSERT",
                {
                    "session_id": result.session_id,
                    "agent_id": result.agent_id,
                    "role": result.role,
                    "content": result.content,
                    "metadata": parse_json_column(result.metadata),
                },
            )

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
            "metadata": parse_json_column(result.metadata) or {},
            "created_at": to_isoformat(result.created_at)
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

        # Search Qdrant — filter by type=memory at the Qdrant level
        results = await qdrant_service.search_vectors(
            project_id=project_id,
            query_vector=query_embedding,
            limit=limit * 2,  # Get more results for filtering
            threshold=threshold,
            filter_metadata={"type": "memory"}
        )

        # Filter by metadata
        # Note: qdrant_service returns {"id", "score", "payload"} — key is "payload" not "metadata"
        filtered_results = []
        for result in results:
            payload = result.get("payload", {})

            # Skip non-memory entries
            if payload.get("type") != "memory":
                continue

            if agent_id and payload.get("agent_id") != agent_id:
                continue
            if session_id and payload.get("session_id") != session_id:
                continue
            if role and payload.get("role") != role:
                continue

            filtered_results.append({
                "id": payload.get("pg_id"),
                "session_id": payload.get("session_id"),
                "agent_id": payload.get("agent_id"),
                "role": payload.get("role"),
                "content": payload.get("content"),
                "metadata": {k: v for k, v in payload.items()
                           if k not in ["content", "role", "agent_id", "session_id", "pg_id", "type", "project_id", "namespace", "vector_id"]},
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
                "metadata": parse_json_column(row.metadata) or {},
                "created_at": to_isoformat(row.created_at)
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
                "first_message_at": to_isoformat(row.first_message_at),
                "last_message_at": to_isoformat(row.last_message_at)
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

        # Application-level CDC (Refs #63): full mode logs each deleted row
        # via the memory table's DELETE trigger; lite mode has no trigger
        # support, so log the same change_log rows explicitly.
        if is_lite_mode():
            for memory_id in memory_ids:
                log_cdc_change(
                    db, project_id, "memory", memory_id, "DELETE",
                    {"session_id": session_id},
                )

        db.commit()

        # Delete from Qdrant. NOTE: this previously passed a project_id=
        # kwarg that neither QdrantService.delete_vector nor
        # FAISSService.delete_vector accept (both take only vector_id/
        # collection_name) -- a pre-existing bug independent of lite vs.
        # full mode, fixed here for the same reason as vector_service.py's
        # delete_vector.
        for memory_id in memory_ids:
            qdrant_id = f"{project_id}_memory_{memory_id}"
            try:
                await qdrant_service.delete_vector(vector_id=qdrant_id)
            except Exception:
                pass  # Continue even if Qdrant delete fails

        return len(memory_ids)


# Global instance
memory_service = MemoryService()
