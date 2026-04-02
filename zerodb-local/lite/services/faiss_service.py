"""
FAISS Vector Search Service
Lightweight vector similarity search using FAISS (faiss-cpu).
Replaces Qdrant dependency for the lite/local backend.

Persistence:
  - Index: ~/.zerodb/data/vectors.faiss
  - Metadata: ~/.zerodb/data/vectors_meta.json

Index strategy: IndexFlatIP on L2-normalized vectors gives cosine similarity.
Default dimension: 384 (BAAI/bge-small-en-v1.5).
"""
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import faiss
import numpy as np


class FAISSService:
    """Service for vector similarity search backed by FAISS (faiss-cpu)."""

    DEFAULT_DIM = 384
    DEFAULT_COLLECTION = "zerodb_local"

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialise the FAISS service.

        Args:
            data_dir: Directory for persisted index and metadata files.
                      Defaults to ~/.zerodb/data
        """
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".zerodb" / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._index_path = self.data_dir / "vectors.faiss"
        self._meta_path = self.data_dir / "vectors_meta.json"

        # Lock protects _index and _metadata across async callers
        self._lock = threading.Lock()

        # id_map: ordered list of vector_id strings matching FAISS row order
        # metadata: dict[vector_id] -> payload dict
        self._index: Optional[faiss.IndexFlatIP] = None
        self._id_map: List[str] = []
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._dimension: int = self.DEFAULT_DIM

        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load index and metadata from disk if they exist."""
        if self._index_path.exists() and self._meta_path.exists():
            try:
                self._index = faiss.read_index(str(self._index_path))
                self._dimension = self._index.d
                with open(self._meta_path, "r") as fh:
                    blob = json.load(fh)
                self._id_map = blob.get("id_map", [])
                self._metadata = blob.get("metadata", {})
            except Exception as exc:
                print(f"Warning: failed to load FAISS index from disk, starting fresh: {exc}")
                self._init_empty_index(self._dimension)
        else:
            self._init_empty_index(self._dimension)

    def _save(self) -> None:
        """Persist index and metadata to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self._index is not None:
            faiss.write_index(self._index, str(self._index_path))
        blob = {
            "id_map": self._id_map,
            "metadata": self._metadata,
        }
        with open(self._meta_path, "w") as fh:
            json.dump(blob, fh)

    def _init_empty_index(self, dim: int) -> None:
        """Create a fresh, empty IndexFlatIP."""
        self._dimension = dim
        self._index = faiss.IndexFlatIP(dim)
        self._id_map = []
        self._metadata = {}

    # ------------------------------------------------------------------
    # ID helpers (mirrors QdrantService._to_point_id)
    # ------------------------------------------------------------------

    @staticmethod
    def _to_point_id(vector_id: str) -> str:
        """Deterministic UUID from an arbitrary string key."""
        try:
            return str(UUID(vector_id))
        except (ValueError, AttributeError):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, vector_id))

    @staticmethod
    def _normalize(vec: List[float]) -> np.ndarray:
        """L2-normalise a vector so inner-product == cosine similarity."""
        arr = np.array(vec, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr /= norm
        return arr

    # ------------------------------------------------------------------
    # Public interface (matches QdrantService)
    # ------------------------------------------------------------------

    async def initialize_collection(
        self,
        collection_name: str = None,
        vector_size: int = DEFAULT_DIM,
        distance: str = "cosine",
    ) -> bool:
        """
        Ensure the FAISS index is ready.

        In lite mode there is a single flat index, so collection_name is
        recorded as metadata but does not create separate storage.

        Args:
            collection_name: Logical collection name (stored in metadata only).
            vector_size: Embedding dimension.
            distance: Distance metric (only 'cosine' is supported via IndexFlatIP).

        Returns:
            True on success.
        """
        with self._lock:
            if self._index is None or self._index.d != vector_size:
                self._init_empty_index(vector_size)
                self._save()
        return True

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
        """
        Upsert a vector into the FAISS index.

        Args:
            project_id: Project UUID.
            vector_id: Unique vector identifier.
            embedding: Raw embedding floats.
            payload: Metadata dict (also accepts 'metadata' kwarg).
            namespace: Logical namespace stored in payload.
            collection_name: Ignored (single index), kept for interface compat.

        Returns:
            True on success, False on error.
        """
        if payload is None:
            payload = kwargs.get("metadata", {})

        point_id = self._to_point_id(vector_id)
        full_payload = {
            **payload,
            "project_id": str(project_id),
            "namespace": namespace,
            "vector_id": vector_id,
        }

        vec = self._normalize(embedding)

        with self._lock:
            # Auto-create index on first upsert if dimensions differ
            if self._index is None or self._index.d != len(embedding):
                self._init_empty_index(len(embedding))

            if point_id in self._metadata:
                # Remove existing row then re-add (FAISS has no native update)
                idx = self._id_map.index(point_id)
                self._remove_row(idx)

            self._index.add(vec)
            self._id_map.append(point_id)
            self._metadata[point_id] = full_payload
            self._save()

        return True

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
        """
        Search for similar vectors.

        FAISS does not support payload filters natively, so we over-fetch and
        apply Python post-filters for project_id, namespace, and metadata.

        Args:
            project_id: Scope search to this project.
            query_vector: Query embedding.
            limit: Maximum results to return.
            threshold: Minimum cosine similarity (0-1).
            namespace: Optional namespace filter.
            filter_metadata: Optional key/value metadata filters.
            collection_name: Ignored (single index).

        Returns:
            List of dicts with keys: id, score, payload.
        """
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return []

            vec = self._normalize(query_vector)

            # Over-fetch to compensate for post-filtering
            k = min(self._index.ntotal, limit * 10)
            scores, indices = self._index.search(vec, k)

        results: List[Dict[str, Any]] = []
        project_str = str(project_id)

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if float(score) < threshold:
                continue

            point_id = self._id_map[idx]
            meta = self._metadata.get(point_id, {})

            # Project filter
            if meta.get("project_id") != project_str:
                continue

            # Namespace filter
            if namespace and meta.get("namespace") != namespace:
                continue

            # Metadata filter
            if filter_metadata:
                if not all(meta.get(k_) == v_ for k_, v_ in filter_metadata.items()):
                    continue

            results.append({
                "id": point_id,
                "score": float(score),
                "payload": meta,
            })

            if len(results) >= limit:
                break

        return results

    async def delete_vector(
        self,
        vector_id: str,
        collection_name: Optional[str] = None,
    ) -> bool:
        """
        Delete a single vector by ID.

        Args:
            vector_id: The vector ID to remove.
            collection_name: Ignored (single index).

        Returns:
            True if found and deleted, False otherwise.
        """
        point_id = self._to_point_id(vector_id)

        with self._lock:
            if point_id not in self._metadata:
                return False

            idx = self._id_map.index(point_id)
            self._remove_row(idx)
            self._save()

        return True

    async def delete_vectors_by_project(
        self,
        project_id: UUID,
        namespace: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> int:
        """
        Delete all vectors belonging to a project (optionally filtered by namespace).

        Args:
            project_id: Project UUID.
            namespace: Optional namespace scope.
            collection_name: Ignored.

        Returns:
            Number of vectors deleted.
        """
        project_str = str(project_id)

        with self._lock:
            to_remove: List[int] = []
            for i, pid in enumerate(self._id_map):
                meta = self._metadata.get(pid, {})
                if meta.get("project_id") != project_str:
                    continue
                if namespace and meta.get("namespace") != namespace:
                    continue
                to_remove.append(i)

            # Remove in reverse order to preserve earlier indices
            for idx in reversed(to_remove):
                self._remove_row(idx)

            if to_remove:
                self._save()

        return len(to_remove)

    async def get_collection_info(
        self,
        collection_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Return information about the current index.

        Args:
            collection_name: Logical name (defaults to zerodb_local).

        Returns:
            Dict with index statistics or None on error.
        """
        name = collection_name or self.DEFAULT_COLLECTION
        with self._lock:
            if self._index is None:
                return None
            return {
                "name": name,
                "vectors_count": self._index.ntotal,
                "indexed_vectors_count": self._index.ntotal,
                "segments_count": 1,
                "status": "green",
                "optimizer_status": "ok",
                "dimension": self._dimension,
                "backend": "faiss-cpu",
            }

    async def health_check(self) -> Dict[str, Any]:
        """
        Return FAISS service health status.

        Returns:
            Dict with status, backend info, and vector count.
        """
        with self._lock:
            total = self._index.ntotal if self._index else 0
        return {
            "status": "healthy",
            "url": f"file://{self.data_dir}",
            "collections": [self.DEFAULT_COLLECTION],
            "backend": "faiss-cpu",
            "total_vectors": total,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_row(self, idx: int) -> None:
        """
        Remove a single row from the FAISS index by rebuilding without it.

        Must be called while holding self._lock.
        """
        point_id = self._id_map[idx]

        # Rebuild index without the target row
        n = self._index.ntotal
        if n <= 1:
            self._init_empty_index(self._dimension)
            self._metadata.pop(point_id, None)
            return

        # Extract all vectors, drop target, rebuild
        all_vecs = faiss.rev_swig_ptr(self._index.get_xb(), n * self._dimension)
        all_vecs = np.array(all_vecs, dtype=np.float32).reshape(n, self._dimension)
        keep_mask = np.ones(n, dtype=bool)
        keep_mask[idx] = False
        remaining = all_vecs[keep_mask]

        new_index = faiss.IndexFlatIP(self._dimension)
        new_index.add(remaining)
        self._index = new_index

        self._id_map.pop(idx)
        self._metadata.pop(point_id, None)


# Global instance
faiss_service = FAISSService()
