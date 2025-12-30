"""
Qdrant Vector Search Service
Handles vector similarity search using Qdrant
"""
import os
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
    SearchRequest,
    CollectionInfo
)
from qdrant_client.http.exceptions import UnexpectedResponse


class QdrantService:
    """Service for interacting with Qdrant vector database"""

    def __init__(self):
        """Initialize Qdrant client"""
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.testing = os.getenv("TESTING", "false").lower() == "true"
        self.default_collection = "zerodb_local"

        if not self.testing:
            self.client = QdrantClient(url=self.url)
        else:
            # Mock Qdrant client for testing
            from unittest.mock import MagicMock
            self.client = MagicMock()

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
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if exists:
                print(f"✅ Collection '{collection_name}' already exists")
                return True

            # Map distance metric
            distance_map = {
                "cosine": Distance.COSINE,
                "euclid": Distance.EUCLID,
                "dot": Distance.DOT
            }

            # Create collection with HNSW index
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_map.get(distance.lower(), Distance.COSINE)
                )
            )

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
        payload: Dict[str, Any],
        namespace: str = "default",
        collection_name: str = None
    ) -> bool:
        """
        Upsert a vector into Qdrant

        Args:
            project_id: Project UUID
            vector_id: Vector ID
            embedding: Vector embedding
            payload: Metadata payload
            namespace: Vector namespace
            collection_name: Collection name

        Returns:
            bool: Success status
        """
        if collection_name is None:
            collection_name = self.default_collection

        try:
            # Add project_id and namespace to payload
            full_payload = {
                **payload,
                "project_id": str(project_id),
                "namespace": namespace,
                "vector_id": vector_id
            }

            # Upsert to Qdrant
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=vector_id,
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
        Search for similar vectors

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

            # Search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=threshold,
                query_filter=Filter(must=filter_conditions) if filter_conditions else None
            )

            # Format results
            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                }
                for result in results
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
            self.client.delete(
                collection_name=collection_name,
                points_selector=[vector_id]
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

            # Delete with filter
            result = self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(must=filter_conditions)
            )

            return result.points_deleted if hasattr(result, 'points_deleted') else 0

        except UnexpectedResponse as e:
            print(f"❌ Error deleting vectors: {e}")
            return 0

    async def get_collection_info(
        self,
        collection_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get collection information

        Args:
            collection_name: Collection name

        Returns:
            Collection info dict or None
        """
        if collection_name is None:
            collection_name = self.default_collection

        try:
            info: CollectionInfo = self.client.get_collection(collection_name)

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
        """
        Check Qdrant health

        Returns:
            Health status dict
        """
        try:
            # Try to get collections
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
