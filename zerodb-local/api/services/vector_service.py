"""
Vector Service
Handles vector storage and search using PostgreSQL + Qdrant + Local Embeddings
"""
import os
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.embeddings_service import embeddings_service
from services.qdrant_service import qdrant_service


class VectorService:
    """
    Service for vector operations

    Architecture:
    - PostgreSQL: Stores vector metadata and embeddings (backup)
    - Qdrant: Provides fast similarity search
    - Embeddings Service: Generates vectors locally (no API costs)
    """

    def __init__(self):
        self.default_collection = os.getenv("QDRANT_COLLECTION_NAME", "zerodb_local")
        self.vector_dimensions = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))

    async def upsert_vector(
        self,
        db: Session,
        project_id: UUID,
        document: str,
        metadata: Dict[str, Any],
        namespace: str = "default",
        vector_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert a single vector

        Steps:
        1. Generate embedding from document text
        2. Store in PostgreSQL (metadata + backup)
        3. Store in Qdrant (fast search)

        Args:
            db: Database session
            project_id: Project UUID
            document: Text to embed
            metadata: Optional metadata dict
            namespace: Vector namespace
            vector_id: Optional custom vector ID

        Returns:
            Created/updated vector info
        """
        # Step 1: Generate embedding
        embeddings = await embeddings_service.generate_embeddings([document])
        embedding = embeddings[0]

        # Step 2: Upsert in PostgreSQL
        if vector_id:
            # Check if vector exists (for update)
            check_query = text("""
                SELECT id FROM vectors
                WHERE project_id = :project_id
                AND namespace = :namespace
                AND vector_id = :vector_id
            """)
            existing = db.execute(
                check_query,
                {
                    "project_id": str(project_id),
                    "namespace": namespace,
                    "vector_id": vector_id
                }
            ).first()

            if existing:
                # Update existing vector
                update_query = text("""
                    UPDATE vectors
                    SET embedding = :embedding::vector,
                        document = :document,
                        metadata = :metadata::jsonb,
                        updated_at = NOW()
                    WHERE id = :id
                    RETURNING id, vector_id, document, metadata, created_at, updated_at
                """)
                result = db.execute(
                    update_query,
                    {
                        "id": str(existing.id),
                        "embedding": str(embedding),
                        "document": document,
                        "metadata": str(metadata)
                    }
                ).first()
                pg_vector_id = str(existing.id)
            else:
                # Insert new vector with custom ID
                insert_query = text("""
                    INSERT INTO vectors (project_id, namespace, vector_id, embedding, document, metadata)
                    VALUES (:project_id, :namespace, :vector_id, :embedding::vector, :document, :metadata::jsonb)
                    RETURNING id, vector_id, document, metadata, created_at, updated_at
                """)
                result = db.execute(
                    insert_query,
                    {
                        "project_id": str(project_id),
                        "namespace": namespace,
                        "vector_id": vector_id,
                        "embedding": str(embedding),
                        "document": document,
                        "metadata": str(metadata)
                    }
                ).first()
                pg_vector_id = str(result.id)
        else:
            # Insert new vector (auto-generate ID)
            insert_query = text("""
                INSERT INTO vectors (project_id, namespace, embedding, document, metadata)
                VALUES (:project_id, :namespace, :embedding::vector, :document, :metadata::jsonb)
                RETURNING id, vector_id, document, metadata, created_at, updated_at
            """)
            result = db.execute(
                insert_query,
                {
                    "project_id": str(project_id),
                    "namespace": namespace,
                    "embedding": str(embedding),
                    "document": document,
                    "metadata": str(metadata)
                }
            ).first()
            pg_vector_id = str(result.id)
            vector_id = str(result.id)  # Use PostgreSQL UUID as vector_id

        db.commit()

        # Step 3: Upsert in Qdrant
        qdrant_id = f"{project_id}_{namespace}_{vector_id}"
        await qdrant_service.upsert_vector(
            project_id=project_id,
            vector_id=qdrant_id,
            embedding=embedding,
            metadata={
                **metadata,
                "document": document,
                "namespace": namespace,
                "pg_id": pg_vector_id
            }
        )

        return {
            "id": pg_vector_id,
            "vector_id": vector_id,
            "document": document,
            "metadata": metadata,
            "namespace": namespace,
            "dimensions": len(embedding),
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None
        }

    async def search_vectors(
        self,
        db: Session,
        project_id: UUID,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        namespace: Optional[str] = "default",
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using semantic search

        Steps:
        1. Generate embedding from query text
        2. Search Qdrant for similar vectors
        3. Apply metadata filters if provided

        Args:
            db: Database session
            project_id: Project UUID
            query: Search query text
            limit: Max results to return
            threshold: Similarity threshold (0-1)
            namespace: Search in specific namespace
            filter_metadata: Optional metadata filters

        Returns:
            List of matching vectors with scores
        """
        # Generate query embedding
        embeddings = await embeddings_service.generate_embeddings([query])
        query_embedding = embeddings[0]

        # Search Qdrant
        results = await qdrant_service.search_vectors(
            project_id=project_id,
            query_vector=query_embedding,
            limit=limit,
            threshold=threshold
        )

        # Filter by namespace and metadata if needed
        filtered_results = []
        for result in results:
            # Check namespace
            if namespace and result.get("metadata", {}).get("namespace") != namespace:
                continue

            # Check metadata filters
            if filter_metadata:
                matches = all(
                    result.get("metadata", {}).get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not matches:
                    continue

            filtered_results.append({
                "id": result.get("metadata", {}).get("pg_id"),
                "vector_id": result.get("id", "").split("_")[-1],
                "document": result.get("metadata", {}).get("document"),
                "metadata": {k: v for k, v in result.get("metadata", {}).items()
                           if k not in ["document", "namespace", "pg_id"]},
                "score": result.get("score"),
                "namespace": result.get("metadata", {}).get("namespace")
            })

        return filtered_results[:limit]

    async def list_vectors(
        self,
        db: Session,
        project_id: UUID,
        namespace: str = "default",
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List vectors with pagination

        Args:
            db: Database session
            project_id: Project UUID
            namespace: Vector namespace
            skip: Number to skip (pagination)
            limit: Max results

        Returns:
            List of vectors
        """
        query = text("""
            SELECT id, vector_id, document, metadata, namespace, created_at, updated_at
            FROM vectors
            WHERE project_id = :project_id
            AND namespace = :namespace
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        results = db.execute(
            query,
            {
                "project_id": str(project_id),
                "namespace": namespace,
                "limit": limit,
                "offset": skip
            }
        ).fetchall()

        return [
            {
                "id": str(row.id),
                "vector_id": row.vector_id or str(row.id),
                "document": row.document,
                "metadata": row.metadata or {},
                "namespace": row.namespace,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None
            }
            for row in results
        ]

    async def get_vector(
        self,
        db: Session,
        project_id: UUID,
        vector_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific vector by ID

        Args:
            db: Database session
            project_id: Project UUID
            vector_id: Vector ID

        Returns:
            Vector info or None
        """
        query = text("""
            SELECT id, vector_id, document, metadata, namespace, created_at, updated_at
            FROM vectors
            WHERE project_id = :project_id
            AND (id::text = :vector_id OR vector_id = :vector_id)
        """)

        result = db.execute(
            query,
            {"project_id": str(project_id), "vector_id": vector_id}
        ).first()

        if not result:
            return None

        return {
            "id": str(result.id),
            "vector_id": result.vector_id or str(result.id),
            "document": result.document,
            "metadata": result.metadata or {},
            "namespace": result.namespace,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "updated_at": result.updated_at.isoformat() if result.updated_at else None
        }

    async def delete_vector(
        self,
        db: Session,
        project_id: UUID,
        vector_id: str
    ) -> bool:
        """
        Delete a vector

        Args:
            db: Database session
            project_id: Project UUID
            vector_id: Vector ID

        Returns:
            True if deleted, False if not found
        """
        # Delete from PostgreSQL
        delete_query = text("""
            DELETE FROM vectors
            WHERE project_id = :project_id
            AND (id::text = :vector_id OR vector_id = :vector_id)
            RETURNING id, namespace
        """)

        result = db.execute(
            delete_query,
            {"project_id": str(project_id), "vector_id": vector_id}
        ).first()

        if not result:
            return False

        db.commit()

        # Delete from Qdrant
        qdrant_id = f"{project_id}_{result.namespace}_{vector_id}"
        await qdrant_service.delete_vector(
            project_id=project_id,
            vector_id=qdrant_id
        )

        return True

    async def get_stats(
        self,
        db: Session,
        project_id: UUID,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get vector statistics

        Args:
            db: Database session
            project_id: Project UUID
            namespace: Optional namespace filter

        Returns:
            Statistics dict
        """
        if namespace:
            stats_query = text("""
                SELECT
                    COUNT(*) as total_vectors,
                    COUNT(DISTINCT namespace) as namespace_count,
                    :namespace as namespace
                FROM vectors
                WHERE project_id = :project_id
                AND namespace = :namespace
            """)
            params = {"project_id": str(project_id), "namespace": namespace}
        else:
            stats_query = text("""
                SELECT
                    COUNT(*) as total_vectors,
                    COUNT(DISTINCT namespace) as namespace_count
                FROM vectors
                WHERE project_id = :project_id
            """)
            params = {"project_id": str(project_id)}

        result = db.execute(stats_query, params).first()

        return {
            "total_vectors": result.total_vectors or 0,
            "namespace_count": result.namespace_count or 0,
            "dimensions": self.vector_dimensions,
            "namespace": namespace
        }


# Global instance
vector_service = VectorService()
