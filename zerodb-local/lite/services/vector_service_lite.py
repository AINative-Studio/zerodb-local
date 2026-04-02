"""
Vector Service Lite
Wrapper that delegates to FAISSService when ZERODB_BACKEND=lite.
Drop-in replacement for the Qdrant-backed VectorService in local/lite mode.
"""
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from lite.services.faiss_service import FAISSService, faiss_service


class VectorServiceLite:
    """
    Lightweight vector service that uses FAISS instead of Qdrant.

    Activated when the environment variable ZERODB_BACKEND is set to 'lite'.
    Falls back to the standard Qdrant-backed VectorService otherwise.
    """

    def __init__(self, backend: Optional[FAISSService] = None):
        self.backend = backend or faiss_service
        self.vector_dimensions = int(os.getenv("QDRANT_VECTOR_SIZE", "384"))
        self.default_collection = os.getenv("QDRANT_COLLECTION_NAME", "zerodb_local")

    # ------------------------------------------------------------------
    # Core operations (match QdrantService interface)
    # ------------------------------------------------------------------

    async def initialize_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: int = 384,
        distance: str = "cosine",
    ) -> bool:
        """Initialise the underlying FAISS index."""
        return await self.backend.initialize_collection(
            collection_name=collection_name or self.default_collection,
            vector_size=vector_size,
            distance=distance,
        )

    async def upsert_vector(
        self,
        project_id: UUID,
        vector_id: str,
        embedding: List[float],
        payload: Optional[Dict[str, Any]] = None,
        namespace: str = "default",
        collection_name: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Upsert a vector via the FAISS backend."""
        return await self.backend.upsert_vector(
            project_id=project_id,
            vector_id=vector_id,
            embedding=embedding,
            payload=payload,
            namespace=namespace,
            collection_name=collection_name,
            **kwargs,
        )

    async def search_vectors(
        self,
        project_id: UUID,
        query_vector: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors via FAISS."""
        return await self.backend.search_vectors(
            project_id=project_id,
            query_vector=query_vector,
            limit=limit,
            threshold=threshold,
            namespace=namespace,
            filter_metadata=filter_metadata,
            collection_name=collection_name,
        )

    async def delete_vector(
        self,
        vector_id: str,
        collection_name: Optional[str] = None,
    ) -> bool:
        """Delete a vector by ID."""
        return await self.backend.delete_vector(
            vector_id=vector_id,
            collection_name=collection_name,
        )

    async def delete_vectors_by_project(
        self,
        project_id: UUID,
        namespace: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> int:
        """Delete all vectors for a project."""
        return await self.backend.delete_vectors_by_project(
            project_id=project_id,
            namespace=namespace,
            collection_name=collection_name,
        )

    async def get_collection_info(
        self,
        collection_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get FAISS index information."""
        return await self.backend.get_collection_info(
            collection_name=collection_name,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check FAISS service health."""
        return await self.backend.health_check()


def get_vector_service():
    """
    Factory that returns the appropriate vector service based on ZERODB_BACKEND.

    Returns:
        VectorServiceLite when ZERODB_BACKEND=lite, otherwise the standard
        Qdrant-backed service.
    """
    backend = os.getenv("ZERODB_BACKEND", "qdrant").lower()
    if backend == "lite":
        return VectorServiceLite()

    # Fall back to standard Qdrant service
    from services.qdrant_service import qdrant_service  # noqa: delayed import
    return qdrant_service


# Global instance resolved at import time
vector_service_lite = VectorServiceLite()
