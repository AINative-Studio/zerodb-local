"""
Qdrant Vector Search Service
Handles vector similarity search using Qdrant

Compatible with qdrant-client >= 1.12 (uses query_points API)
"""
import os
import uuid
from typing import List, Dict, Any, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from qdrant_client.http.exceptions import UnexpectedResponse


class QdrantService:
    """Service for interacting with Qdrant vector database"""

    def __init__(self):
        """Initialize Qdrant client"""
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.testing = os.getenv("TESTING", "false").lower() == "true"
        self.default_collection = "zerodb_local"
        self._initialized_collections: set = set()

        if not self.testing:
            self.client = QdrantClient(url=self.url)
        else:
            from unittest.mock import MagicMock
            self.client = MagicMock()

    async def _ensure_collection(
        self,
        collection_name: str,
        vector_size: int = 1536
    ) -> None:
        """Auto-create collection if it doesn't exist (cached per session)"""
        if collection_name in self._initialized_collections:
            return

        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Auto-created collection '{collection_name}' ({vector_size} dims)")
            self._initialized_collections.add(collection_name)
        except Exception as e:
            print(f"⚠️ Collection check failed (will retry): {e}")

    @staticmethod
    def _to_point_id(vector_id: str) -> str:
        """Convert a vector ID string to a valid Qdrant point UUID"""
        try:
            return str(UUID(vector_id))
        except (ValueError, AttributeError):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, vector_id))

    async def initialize_collection(
        self,
        collection_name: str = None,
        vector_size: int = 1536,
        distance: str = "cosine"
    ) -> bool:
        """
        Initialize Qdrant collection with HNSW index

        Args:
            collection_name: Name of the collection (default: zerodb_local)
            vector_size: Vector dimensions (default: 1536 for OpenAI ada-002)
            distance: Distance metric (cosine, euclid, dot)

        Returns:
            bool: True if created/exists, False on error
        """
        if collection_name is None:
            collection_name = self.default_collection

        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if exists:
                self._initialized_collections.add(collection_name)
                print(f"✅ Collection '{collection_name}' already exists")
                return True

            distance_map = {
                "cosine": Distance.COSINE,
                "euclid": Distance.EUCLID,
                "dot": Distance.DOT
            }

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_map.get(distance.lower(), Distance.COSINE)
                )
            )

            self._initialized_collections.add(collection_name)
            print(f"✅ Created collection '{collection_name}' with {vector_size} dimensions ({distance} distance)")
            return True

        except UnexpectedResponse as e:
            print(f"❌ Error creating collection: {e}")
            return False

    async def upsert_vector(
        self,
        project_id: UUID,
        vector_id: str,
        embedding: List[float],
        payload: Dict[str, Any] = None,
        namespace: str = "default",
        collection_name: str = None,
        **kwargs
    ) -> bool:
        """
        Upsert a vector into Qdrant

        Args:
            project_id: Project UUID
            vector_id: Vector ID (will be converted to UUID)
            embedding: Vector embedding
            payload: Metadata payload (also accepts 'metadata' kwarg)
            namespace: Vector namespace
            collection_name: Collection name

        Returns:
            bool: Success status
        """
        if collection_name is None:
            collection_name = self.default_collection

        # Accept both 'payload' and 'metadata' kwargs
        if payload is None:
            payload = kwargs.get("metadata", {})

        try:
            # Auto-create collection if needed
            await self._ensure_collection(collection_name, len(embedding))

            full_payload = {
                **payload,
                "project_id": str(project_id),
                "namespace": namespace,
                "vector_id": vector_id
            }

            point_id = self._to_point_id(vector_id)

            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=full_payload
                    )
                ]
            )

            return True

        except UnexpectedResponse as e:
            print(f"❌ Error upserting vector: {e}")
            return False

    async def search_vectors(
        self,
        project_id: UUID,
        query_vector: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        namespace: str = None,
        filter_metadata: Dict[str, Any] = None,
        collection_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using query_points API (qdrant-client >= 1.12)

        Args:
            project_id: Project UUID
            query_vector: Query embedding
            limit: Max results
            threshold: Similarity threshold (0-1)
            namespace: Optional namespace filter
            filter_metadata: Optional metadata filters
            collection_name: Collection name

        Returns:
            List of search results with scores
        """
        if collection_name is None:
            collection_name = self.default_collection

        try:
            # Build filter
            filter_conditions = [
                FieldCondition(
                    key="project_id",
                    match=MatchValue(value=str(project_id))
                )
            ]

            if namespace:
                filter_conditions.append(
                    FieldCondition(
                        key="namespace",
                        match=MatchValue(value=namespace)
                    )
                )

            if filter_metadata:
                for key, value in filter_metadata.items():
                    filter_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )

            query_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Use query_points (replaces deprecated client.search in qdrant-client >= 1.12)
            response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=threshold,
                query_filter=query_filter,
                with_payload=True,
            )

            # query_points returns response.points (not a direct list)
            return [
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload
                }
                for point in response.points
            ]

        except UnexpectedResponse as e:
            print(f"❌ Error searching vectors: {e}")
            return []

    async def delete_vector(
        self,
        vector_id: str,
        collection_name: str = None
    ) -> bool:
        """
        Delete a vector from Qdrant

        Args:
            vector_id: Vector ID to delete
            collection_name: Collection name

        Returns:
            bool: Success status
        """
        if collection_name is None:
            collection_name = self.default_collection

        try:
            point_id = self._to_point_id(vector_id)
            self.client.delete(
                collection_name=collection_name,
                points_selector=[point_id]
            )
            return True

        except UnexpectedResponse as e:
            print(f"❌ Error deleting vector: {e}")
            return False

    async def delete_vectors_by_project(
        self,
        project_id: UUID,
        namespace: str = None,
        collection_name: str = None
    ) -> int:
        """
        Delete all vectors for a project

        Args:
            project_id: Project UUID
            namespace: Optional namespace filter
            collection_name: Collection name

        Returns:
            int: Number of vectors deleted
        """
        if collection_name is None:
            collection_name = self.default_collection

        try:
            filter_conditions = [
                FieldCondition(
                    key="project_id",
                    match=MatchValue(value=str(project_id))
                )
            ]

            if namespace:
                filter_conditions.append(
                    FieldCondition(
                        key="namespace",
                        match=MatchValue(value=namespace)
                    )
                )

            result = self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(must=filter_conditions)
            )

            return getattr(result, 'points_deleted', 0)

        except UnexpectedResponse as e:
            print(f"❌ Error deleting vectors: {e}")
            return 0

    async def get_collection_info(
        self,
        collection_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get collection information"""
        if collection_name is None:
            collection_name = self.default_collection

        try:
            info = self.client.get_collection(collection_name)

            return {
                "name": collection_name,
                "vectors_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status
            }

        except UnexpectedResponse as e:
            print(f"❌ Error getting collection info: {e}")
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Check Qdrant health"""
        try:
            collections = self.client.get_collections()

            return {
                "status": "healthy",
                "url": self.url,
                "collections": [c.name for c in collections.collections]
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "url": self.url,
                "error": str(e)
            }


# Global instance
qdrant_service = QdrantService()
