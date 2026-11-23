"""
Vector Service
Handles vector storage and search using PostgreSQL + Qdrant + Local Embeddings
"""
import json
import os
from typing import List, Dict, Any, Optional
from uuid import UUID
from dbos import DBOS
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.embeddings_service import embeddings_service
from services.qdrant_service import qdrant_service
from lite.config import is_lite_mode
from lite.sql_compat import (
    jsonb_cast_sql,
    log_cdc_change,
    new_id,
    now_iso,
    now_sql,
    parse_json_column,
    to_isoformat,
)


def _embedding_cast_sql(expr: str) -> str:
    """
    SQL fragment to store an embedding bind parameter.

    PostgreSQL (pgvector) needs CAST(:x AS vector); SQLite has no vector
    type at all -- the `vectors` table stores embeddings in a BLOB column
    (see lite/db/schema_lite.sql), and qdrant_service (FAISS in lite mode)
    is the actual similarity-search path, so the SQLite column is
    write-only backup storage: pass the bind parameter through unchanged.
    """
    return expr if is_lite_mode() else f"CAST({expr} AS vector)"


def _id_match_clause(column: str, lite: Optional[bool] = None) -> str:
    """
    SQL fragment matching a row by either its primary-key id or its
    user-supplied vector_id column.

    PostgreSQL needs `id::text = :x` to compare a uuid column against a
    text bind parameter; SQLite has no `::text` cast operator, and its
    `id` column is already stored as TEXT (see lite/db/schema_lite.sql),
    so a direct equality comparison works without casting.
    """
    if lite is None:
        lite = is_lite_mode()
    id_expr = "id" if lite else "id::text"
    return f"({id_expr} = :{column} OR vector_id = :{column})"


# Refs #107: upsert_vector/delete_vector write to two independent systems
# -- the SQL `vectors` table (committed first, already atomic on its own)
# and Qdrant/FAISS (via qdrant_service, which dispatches to whichever
# backend is active) -- with nothing making the pair atomic as a whole. A
# crash between the SQL commit and the Qdrant/FAISS call previously left
# the row permanently marked as written while the vector silently never
# reached (or never left) the search index, with no error and no way to
# detect the drift short of a manual reconcile.
#
# These are plain module-level functions, not VectorService methods: DBOS
# resumes a workflow by replaying a reference to the function it was
# registered under, which must be stable across a process restart --
# resuming the SQL step is not attempted here, only the Qdrant/FAISS step,
# since the SQL write already has its own transaction. Both the SQL write
# (done by the caller, already committed by the time this workflow is
# invoked) and the Qdrant/FAISS write are individually idempotent by
# vector_id/point_id, so DBOS's at-least-once step retry on resume is
# safe: replaying this workflow after a crash just re-applies the same
# upsert/delete again, never duplicates anything.
@DBOS.step()
async def _qdrant_upsert_step(
    project_id: str,
    qdrant_id: str,
    embedding: List[float],
    payload: Dict[str, Any],
    namespace: str,
) -> bool:
    return await qdrant_service.upsert_vector(
        project_id=project_id,
        vector_id=qdrant_id,
        embedding=embedding,
        payload=payload,
        namespace=namespace,
    )


@DBOS.workflow()
async def _qdrant_upsert_workflow(
    project_id: str,
    qdrant_id: str,
    embedding: List[float],
    payload: Dict[str, Any],
    namespace: str,
) -> bool:
    return await _qdrant_upsert_step(project_id, qdrant_id, embedding, payload, namespace)


@DBOS.step()
async def _qdrant_delete_step(qdrant_id: str) -> bool:
    return await qdrant_service.delete_vector(vector_id=qdrant_id)


@DBOS.workflow()
async def _qdrant_delete_workflow(qdrant_id: str) -> bool:
    return await _qdrant_delete_step(qdrant_id)


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

        lite = is_lite_mode()
        metadata_param = json.dumps(metadata) if isinstance(metadata, dict) else str(metadata)

        # Step 2: Upsert in PostgreSQL (or SQLite in lite mode)
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
                update_query = text(f"""
                    UPDATE vectors
                    SET embedding = {_embedding_cast_sql(':embedding')},
                        document = :document,
                        metadata = {jsonb_cast_sql(':metadata', lite)},
                        updated_at = {now_sql(lite)}
                    WHERE id = :id
                    RETURNING id, vector_id, document, metadata, created_at, updated_at
                """)
                params = {
                    "id": str(existing.id),
                    "embedding": str(embedding),
                    "document": document,
                    "metadata": metadata_param
                }
                if lite:
                    params["now"] = now_iso()
                result = db.execute(update_query, params).first()
                pg_vector_id = str(existing.id)

                # Application-level CDC (Refs #63): full mode logs this via
                # the vectors table's UPDATE trigger; lite mode has no
                # trigger support, so log the same change_log row explicitly.
                if lite:
                    log_cdc_change(
                        db, project_id, "vector", pg_vector_id, "UPDATE",
                        {
                            "document": document,
                            "metadata": metadata,
                            "namespace": namespace,
                            "vector_id": result.vector_id,
                        },
                    )
            else:
                # Insert new vector with custom ID. In lite mode `id` has no
                # SQL-level default (Postgres's schema declares DEFAULT
                # gen_random_uuid(), SQLite's does not), so generate it
                # explicitly.
                columns = "project_id, namespace, vector_id, embedding, document, metadata"
                values = (
                    f":project_id, :namespace, :vector_id, "
                    f"{_embedding_cast_sql(':embedding')}, :document, {jsonb_cast_sql(':metadata', lite)}"
                )
                params = {
                    "project_id": str(project_id),
                    "namespace": namespace,
                    "vector_id": vector_id,
                    "embedding": str(embedding),
                    "document": document,
                    "metadata": metadata_param
                }
                if lite:
                    columns = "id, " + columns
                    values = ":id, " + values
                    params["id"] = new_id()

                insert_query = text(f"""
                    INSERT INTO vectors ({columns})
                    VALUES ({values})
                    RETURNING id, vector_id, document, metadata, created_at, updated_at
                """)
                result = db.execute(insert_query, params).first()
                pg_vector_id = str(result.id)

                if lite:
                    log_cdc_change(
                        db, project_id, "vector", pg_vector_id, "INSERT",
                        {
                            "document": document,
                            "metadata": metadata,
                            "namespace": namespace,
                            "vector_id": result.vector_id,
                        },
                    )
        else:
            # Insert new vector (auto-generate ID)
            columns = "project_id, namespace, embedding, document, metadata"
            values = f":project_id, :namespace, {_embedding_cast_sql(':embedding')}, :document, {jsonb_cast_sql(':metadata', lite)}"
            params = {
                "project_id": str(project_id),
                "namespace": namespace,
                "embedding": str(embedding),
                "document": document,
                "metadata": metadata_param
            }
            if lite:
                columns = "id, " + columns
                values = ":id, " + values
                params["id"] = new_id()

            insert_query = text(f"""
                INSERT INTO vectors ({columns})
                VALUES ({values})
                RETURNING id, vector_id, document, metadata, created_at, updated_at
            """)
            result = db.execute(insert_query, params).first()
            pg_vector_id = str(result.id)
            vector_id = str(result.id)  # Use the row's UUID as vector_id

            if lite:
                log_cdc_change(
                    db, project_id, "vector", pg_vector_id, "INSERT",
                    {
                        "document": document,
                        "metadata": metadata,
                        "namespace": namespace,
                        "vector_id": vector_id,
                    },
                )

        db.commit()

        # Step 3: Upsert in Qdrant/FAISS, as a DBOS workflow (Refs #107) so
        # a crash here resumes on next launch instead of leaving the SQL
        # row above permanently out of sync with the search index.
        qdrant_id = f"{project_id}_{namespace}_{vector_id}"
        await _qdrant_upsert_workflow(
            project_id=str(project_id),
            qdrant_id=qdrant_id,
            embedding=embedding,
            payload={
                **metadata,
                "document": document,
                "namespace": namespace,
                "pg_id": pg_vector_id
            },
            namespace=namespace
        )

        return {
            "id": pg_vector_id,
            "vector_id": vector_id,
            "document": document,
            "metadata": metadata,
            "namespace": namespace,
            "dimensions": len(embedding),
            "created_at": to_isoformat(result.created_at),
            "updated_at": to_isoformat(result.updated_at)
        }

    async def search_vectors(
        self,
        db: Session,
        project_id: UUID,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        # Refs #111: None, not "default" -- matches the request schema's
        # default in api/routers/vectors.py, so a caller that omits
        # namespace entirely gets "search every namespace" (the same thing
        # an explicit None already does below), not "search only the
        # literal 'default' namespace".
        namespace: Optional[str] = None,
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
            threshold=threshold,
            namespace=namespace
        )

        # Filter by namespace and metadata if needed
        # Note: qdrant_service returns {"id", "score", "payload"} — key is "payload" not "metadata"
        filtered_results = []
        for result in results:
            payload = result.get("payload", {})

            # Lite mode shares one FAISS index/metadata store across features
            # (Refs #87/#88) -- e.g. Memory writes payload["content"], not
            # payload["document"]. Skip any candidate that isn't vector-shaped
            # rather than crashing the whole search on a non-vector hit.
            if payload.get("document") is None:
                continue

            # Check namespace (already filtered at Qdrant level, but double-check)
            if namespace and payload.get("namespace") != namespace:
                continue

            # Check metadata filters
            if filter_metadata:
                if not all(payload.get(k) == v for k, v in filter_metadata.items()):
                    continue

            filtered_results.append({
                "id": payload.get("pg_id"),
                "vector_id": result.get("id", ""),
                "document": payload.get("document"),
                "metadata": {k: v for k, v in payload.items()
                           if k not in ["document", "namespace", "pg_id", "project_id", "vector_id"]},
                "score": result.get("score"),
                "namespace": payload.get("namespace")
            })

        return filtered_results[:limit]

    async def list_vectors(
        self,
        db: Session,
        project_id: UUID,
        namespace: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List vectors with pagination, optionally filtered to one namespace

        Args:
            db: Database session
            project_id: Project UUID
            namespace: Vector namespace to filter by. None lists across all namespaces.
            skip: Number to skip (pagination)
            limit: Max results

        Returns:
            List of vectors
        """
        namespace_clause = "AND namespace = :namespace" if namespace is not None else ""
        query = text(f"""
            SELECT id, vector_id, document, metadata, namespace, created_at, updated_at
            FROM vectors
            WHERE project_id = :project_id
            {namespace_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        params = {
            "project_id": str(project_id),
            "limit": limit,
            "offset": skip
        }
        if namespace is not None:
            params["namespace"] = namespace

        results = db.execute(query, params).fetchall()

        return [
            {
                "id": str(row.id),
                "vector_id": row.vector_id or str(row.id),
                "document": row.document,
                "metadata": parse_json_column(row.metadata) or {},
                "namespace": row.namespace,
                "created_at": to_isoformat(row.created_at),
                "updated_at": to_isoformat(row.updated_at)
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
        # id::text casts a uuid column to text for comparison in Postgres;
        # SQLite has no ::text cast operator and its id column is already
        # TEXT (see lite/db/schema_lite.sql), so the cast must be omitted.
        id_clause = _id_match_clause("vector_id")
        query = text(f"""
            SELECT id, vector_id, document, metadata, namespace, created_at, updated_at
            FROM vectors
            WHERE project_id = :project_id
            AND {id_clause}
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
            "metadata": parse_json_column(result.metadata) or {},
            "namespace": result.namespace,
            "created_at": to_isoformat(result.created_at),
            "updated_at": to_isoformat(result.updated_at)
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
        # Delete from PostgreSQL (or SQLite in lite mode)
        id_clause = _id_match_clause("vector_id")
        delete_query = text(f"""
            DELETE FROM vectors
            WHERE project_id = :project_id
            AND {id_clause}
            RETURNING id, namespace
        """)

        result = db.execute(
            delete_query,
            {"project_id": str(project_id), "vector_id": vector_id}
        ).first()

        if not result:
            return False

        # Application-level CDC (Refs #63): full mode logs this via the
        # vectors table's DELETE trigger; lite mode has no trigger support.
        if is_lite_mode():
            log_cdc_change(
                db, project_id, "vector", result.id, "DELETE",
                {"namespace": result.namespace, "vector_id": vector_id},
            )

        db.commit()

        # Delete from Qdrant/FAISS, as a DBOS workflow (Refs #107) for the
        # same crash-recovery reason as the upsert path above. NOTE: this
        # previously passed a project_id= kwarg that neither
        # QdrantService.delete_vector nor FAISSService.delete_vector
        # accept (both take only vector_id/collection_name) -- a
        # pre-existing bug independent of lite vs. full mode, fixed here
        # because it blocks vector deletion end-to-end in both backends.
        qdrant_id = f"{project_id}_{result.namespace}_{vector_id}"
        await _qdrant_delete_workflow(qdrant_id=qdrant_id)

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


# Global instance.
#
# Refs #47: this used to dispatch to lite.services.vector_service_lite's
# VectorServiceLite in lite mode, but that class has a completely different
# method signature (upsert_vector(project_id, vector_id, embedding, payload,
# namespace, ...), no db/document/metadata params) than every router call
# site in api/routers/vectors.py expects (upsert_vector(db=, project_id=,
# document=, metadata=, namespace=, vector_id=)) -- the dispatch meant every
# vector endpoint crashed with a TypeError in lite mode. VectorService
# itself is now dialect-aware (see jsonb_cast_sql/_embedding_cast_sql/
# _id_match_clause above) and already delegates the actual similarity
# search to qdrant_service, which correctly resolves to FAISS in lite mode
# -- so there is no longer a separate lite implementation to dispatch to.
vector_service = VectorService()
