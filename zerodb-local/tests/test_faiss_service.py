"""
Tests for FAISS Vector Search Service

BDD-style test suite covering upsert, search, delete, namespace filtering,
metadata filtering, persistence, and health check.

Target coverage: >= 90%
"""
import json
import os
import shutil
import tempfile
import uuid
from uuid import UUID

import faiss
import numpy as np
import pytest
import pytest_asyncio

# Ensure imports resolve from the zerodb-local root
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lite.services.faiss_service import FAISSService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a clean temporary directory for FAISS persistence."""
    return str(tmp_path / "faiss_test_data")


@pytest.fixture
def service(tmp_data_dir):
    """Create a fresh FAISSService instance backed by a temp directory."""
    return FAISSService(data_dir=tmp_data_dir)


@pytest.fixture
def project_id():
    """Return a deterministic project UUID for tests."""
    return UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def other_project_id():
    """Return a second project UUID for cross-project isolation tests."""
    return UUID("11111111-2222-3333-4444-555555555555")


def _random_vector(dim: int = 384) -> list:
    """Generate a random unit-normalised vector."""
    v = np.random.randn(dim).astype(np.float32)
    v /= np.linalg.norm(v)
    return v.tolist()


def _similar_vector(base: list, noise: float = 0.05) -> list:
    """Generate a vector similar to *base* by adding small noise."""
    arr = np.array(base, dtype=np.float32)
    arr += np.random.randn(len(base)).astype(np.float32) * noise
    arr /= np.linalg.norm(arr)
    return arr.tolist()


# ---------------------------------------------------------------------------
# Scenario: Upserting vectors
# ---------------------------------------------------------------------------

class TestUpsertVector:
    """Given a fresh FAISS index, upsert operations should succeed."""

    @pytest.mark.asyncio
    async def test_upsert_single_vector(self, service, project_id):
        """When I upsert one vector, it should be stored in the index."""
        vec = _random_vector()
        result = await service.upsert_vector(
            project_id=project_id,
            vector_id="vec-001",
            embedding=vec,
            payload={"label": "test"},
            namespace="default",
        )
        assert result is True

        info = await service.get_collection_info()
        assert info["vectors_count"] == 1

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, service, project_id):
        """When I upsert the same vector_id twice, the index should not grow."""
        vec1 = _random_vector()
        vec2 = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="vec-dup", embedding=vec1
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="vec-dup", embedding=vec2,
            payload={"updated": True},
        )

        info = await service.get_collection_info()
        assert info["vectors_count"] == 1

    @pytest.mark.asyncio
    async def test_upsert_accepts_metadata_kwarg(self, service, project_id):
        """The upsert method should accept 'metadata' as an alias for 'payload'."""
        vec = _random_vector()
        result = await service.upsert_vector(
            project_id=project_id,
            vector_id="vec-meta",
            embedding=vec,
            metadata={"source": "kwarg"},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_upsert_auto_detects_dimension(self, service, project_id):
        """Upserting a 128-dim vector should create an index with matching dimension."""
        vec = _random_vector(dim=128)
        await service.upsert_vector(
            project_id=project_id, vector_id="vec-128", embedding=vec
        )
        info = await service.get_collection_info()
        assert info["dimension"] == 128


# ---------------------------------------------------------------------------
# Scenario: Searching vectors
# ---------------------------------------------------------------------------

class TestSearchVectors:
    """Given vectors in the index, search should return scored results."""

    @pytest.mark.asyncio
    async def test_search_returns_similar_vectors(self, service, project_id):
        """When I search with a similar vector, it should appear in results."""
        base = _random_vector()
        similar = _similar_vector(base, noise=0.01)
        dissimilar = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="close", embedding=base,
            payload={"type": "close"},
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="far", embedding=dissimilar,
            payload={"type": "far"},
        )

        results = await service.search_vectors(
            project_id=project_id,
            query_vector=similar,
            limit=5,
            threshold=0.8,
        )

        assert len(results) >= 1
        assert results[0]["payload"]["type"] == "close"
        assert results[0]["score"] >= 0.8

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, service, project_id):
        """Search should never return more results than the limit."""
        base = _random_vector()
        for i in range(20):
            vec = _similar_vector(base, noise=0.02)
            await service.upsert_vector(
                project_id=project_id, vector_id=f"batch-{i}", embedding=vec,
            )

        results = await service.search_vectors(
            project_id=project_id,
            query_vector=base,
            limit=5,
            threshold=0.0,
        )
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_search_respects_threshold(self, service, project_id):
        """Results below the similarity threshold should be excluded."""
        base = _random_vector()
        await service.upsert_vector(
            project_id=project_id, vector_id="only-one", embedding=base,
        )

        results = await service.search_vectors(
            project_id=project_id,
            query_vector=base,
            limit=10,
            threshold=0.99999,
        )
        # The vector is identical so score should be ~1.0
        assert all(r["score"] >= 0.99 for r in results)

    @pytest.mark.asyncio
    async def test_search_empty_index_returns_empty(self, service, project_id):
        """Searching an empty index should return an empty list."""
        results = await service.search_vectors(
            project_id=project_id,
            query_vector=_random_vector(),
            limit=5,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_search_scores_are_floats(self, service, project_id):
        """Each result score should be a Python float."""
        vec = _random_vector()
        await service.upsert_vector(
            project_id=project_id, vector_id="score-check", embedding=vec,
        )
        results = await service.search_vectors(
            project_id=project_id, query_vector=vec, limit=1, threshold=0.0,
        )
        assert len(results) == 1
        assert isinstance(results[0]["score"], float)


# ---------------------------------------------------------------------------
# Scenario: Namespace filtering
# ---------------------------------------------------------------------------

class TestNamespaceFiltering:
    """Vectors in different namespaces should be independently searchable."""

    @pytest.mark.asyncio
    async def test_search_filters_by_namespace(self, service, project_id):
        """Only vectors matching the requested namespace should be returned."""
        vec = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="ns-a", embedding=vec,
            namespace="alpha",
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="ns-b", embedding=vec,
            namespace="beta",
        )

        results_alpha = await service.search_vectors(
            project_id=project_id, query_vector=vec,
            namespace="alpha", limit=10, threshold=0.0,
        )
        results_beta = await service.search_vectors(
            project_id=project_id, query_vector=vec,
            namespace="beta", limit=10, threshold=0.0,
        )

        assert len(results_alpha) == 1
        assert results_alpha[0]["payload"]["namespace"] == "alpha"
        assert len(results_beta) == 1
        assert results_beta[0]["payload"]["namespace"] == "beta"

    @pytest.mark.asyncio
    async def test_search_without_namespace_returns_all(self, service, project_id):
        """Omitting namespace should return vectors from all namespaces."""
        vec = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="all-a", embedding=vec,
            namespace="one",
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="all-b",
            embedding=_similar_vector(vec, noise=0.01), namespace="two",
        )

        results = await service.search_vectors(
            project_id=project_id, query_vector=vec,
            namespace=None, limit=10, threshold=0.0,
        )
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Scenario: Metadata filtering
# ---------------------------------------------------------------------------

class TestMetadataFiltering:
    """Post-filter should match only vectors whose payload contains the filter keys."""

    @pytest.mark.asyncio
    async def test_filter_by_single_metadata_key(self, service, project_id):
        """Filter with one key should narrow results correctly."""
        vec = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="m1", embedding=vec,
            payload={"category": "docs"},
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="m2",
            embedding=_similar_vector(vec, noise=0.01),
            payload={"category": "code"},
        )

        results = await service.search_vectors(
            project_id=project_id, query_vector=vec,
            filter_metadata={"category": "docs"},
            limit=10, threshold=0.0,
        )
        assert len(results) == 1
        assert results[0]["payload"]["category"] == "docs"

    @pytest.mark.asyncio
    async def test_filter_by_multiple_metadata_keys(self, service, project_id):
        """Filter with multiple keys should require all to match."""
        vec = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="mm1", embedding=vec,
            payload={"category": "docs", "lang": "en"},
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="mm2",
            embedding=_similar_vector(vec, noise=0.01),
            payload={"category": "docs", "lang": "fr"},
        )

        results = await service.search_vectors(
            project_id=project_id, query_vector=vec,
            filter_metadata={"category": "docs", "lang": "en"},
            limit=10, threshold=0.0,
        )
        assert len(results) == 1
        assert results[0]["payload"]["lang"] == "en"


# ---------------------------------------------------------------------------
# Scenario: Deleting vectors
# ---------------------------------------------------------------------------

class TestDeleteVector:
    """Deletion should remove vectors from both index and metadata."""

    @pytest.mark.asyncio
    async def test_delete_existing_vector(self, service, project_id):
        """Deleting an existing vector should return True and reduce count."""
        vec = _random_vector()
        await service.upsert_vector(
            project_id=project_id, vector_id="del-me", embedding=vec,
        )

        result = await service.delete_vector(vector_id="del-me")
        assert result is True

        info = await service.get_collection_info()
        assert info["vectors_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_vector(self, service, project_id):
        """Deleting a missing vector should return False."""
        result = await service.delete_vector(vector_id="ghost")
        assert result is False

    @pytest.mark.asyncio
    async def test_deleted_vector_excluded_from_search(self, service, project_id):
        """After deletion, the vector should no longer appear in search."""
        vec = _random_vector()
        await service.upsert_vector(
            project_id=project_id, vector_id="gone", embedding=vec,
        )
        await service.delete_vector(vector_id="gone")

        results = await service.search_vectors(
            project_id=project_id, query_vector=vec, limit=10, threshold=0.0,
        )
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Scenario: Bulk delete by project
# ---------------------------------------------------------------------------

class TestDeleteVectorsByProject:
    """Bulk deletion should remove all matching vectors for a project."""

    @pytest.mark.asyncio
    async def test_delete_all_project_vectors(self, service, project_id, other_project_id):
        """Only vectors belonging to the target project should be removed."""
        vec = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="p1-v1", embedding=vec,
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="p1-v2", embedding=vec,
        )
        await service.upsert_vector(
            project_id=other_project_id, vector_id="p2-v1", embedding=vec,
        )

        deleted = await service.delete_vectors_by_project(project_id=project_id)
        assert deleted == 2

        info = await service.get_collection_info()
        assert info["vectors_count"] == 1

    @pytest.mark.asyncio
    async def test_delete_by_project_and_namespace(self, service, project_id):
        """Namespace scoping should limit which project vectors are deleted."""
        vec = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="ns-del-a", embedding=vec,
            namespace="keep",
        )
        await service.upsert_vector(
            project_id=project_id, vector_id="ns-del-b", embedding=vec,
            namespace="remove",
        )

        deleted = await service.delete_vectors_by_project(
            project_id=project_id, namespace="remove",
        )
        assert deleted == 1

        info = await service.get_collection_info()
        assert info["vectors_count"] == 1


# ---------------------------------------------------------------------------
# Scenario: Persistence (save / load)
# ---------------------------------------------------------------------------

class TestPersistence:
    """Index and metadata should survive service restarts."""

    @pytest.mark.asyncio
    async def test_index_survives_reload(self, tmp_data_dir, project_id):
        """After saving and creating a new service instance, data should persist."""
        svc1 = FAISSService(data_dir=tmp_data_dir)
        vec = _random_vector()

        await svc1.upsert_vector(
            project_id=project_id, vector_id="persist-1", embedding=vec,
            payload={"persistent": True},
        )

        # Create a fresh instance pointing at the same directory
        svc2 = FAISSService(data_dir=tmp_data_dir)

        info = await svc2.get_collection_info()
        assert info["vectors_count"] == 1

        results = await svc2.search_vectors(
            project_id=project_id, query_vector=vec, limit=5, threshold=0.0,
        )
        assert len(results) == 1
        assert results[0]["payload"]["persistent"] is True

    @pytest.mark.asyncio
    async def test_empty_index_loads_cleanly(self, tmp_data_dir):
        """A fresh directory should produce a working empty service."""
        svc = FAISSService(data_dir=tmp_data_dir)
        info = await svc.get_collection_info()
        assert info["vectors_count"] == 0

    @pytest.mark.asyncio
    async def test_corrupted_files_fallback(self, tmp_data_dir):
        """If persisted files are corrupt, the service should start with an empty index."""
        os.makedirs(tmp_data_dir, exist_ok=True)
        # Write garbage
        with open(os.path.join(tmp_data_dir, "vectors.faiss"), "w") as f:
            f.write("not a faiss index")
        with open(os.path.join(tmp_data_dir, "vectors_meta.json"), "w") as f:
            f.write("not json{{{")

        svc = FAISSService(data_dir=tmp_data_dir)
        info = await svc.get_collection_info()
        assert info["vectors_count"] == 0


# ---------------------------------------------------------------------------
# Scenario: Project isolation
# ---------------------------------------------------------------------------

class TestProjectIsolation:
    """Vectors from different projects should not leak into each other's searches."""

    @pytest.mark.asyncio
    async def test_search_scoped_to_project(self, service, project_id, other_project_id):
        """Search for project A should not return project B's vectors."""
        vec = _random_vector()

        await service.upsert_vector(
            project_id=project_id, vector_id="iso-a", embedding=vec,
        )
        await service.upsert_vector(
            project_id=other_project_id, vector_id="iso-b", embedding=vec,
        )

        results = await service.search_vectors(
            project_id=project_id, query_vector=vec,
            limit=10, threshold=0.0,
        )
        assert len(results) == 1
        assert results[0]["payload"]["project_id"] == str(project_id)


# ---------------------------------------------------------------------------
# Scenario: Collection info and health
# ---------------------------------------------------------------------------

class TestCollectionInfoAndHealth:
    """Info and health endpoints should return correct metadata."""

    @pytest.mark.asyncio
    async def test_collection_info_structure(self, service):
        """get_collection_info should return expected keys."""
        info = await service.get_collection_info()
        assert "name" in info
        assert "vectors_count" in info
        assert "backend" in info
        assert info["backend"] == "faiss-cpu"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, service):
        """Health check should report healthy status."""
        health = await service.health_check()
        assert health["status"] == "healthy"
        assert health["backend"] == "faiss-cpu"

    @pytest.mark.asyncio
    async def test_initialize_collection(self, service):
        """initialize_collection should succeed and set correct dimension."""
        result = await service.initialize_collection(vector_size=512)
        assert result is True

        info = await service.get_collection_info()
        assert info["dimension"] == 512


# ---------------------------------------------------------------------------
# Scenario: ID conversion
# ---------------------------------------------------------------------------

class TestIDConversion:
    """_to_point_id should handle both valid UUIDs and arbitrary strings."""

    def test_valid_uuid_passthrough(self):
        uid = str(uuid.uuid4())
        assert FAISSService._to_point_id(uid) == uid

    def test_arbitrary_string_to_uuid5(self):
        result = FAISSService._to_point_id("my-custom-id")
        # Should be a valid UUID
        parsed = uuid.UUID(result)
        assert str(parsed) == result

    def test_deterministic(self):
        a = FAISSService._to_point_id("same-key")
        b = FAISSService._to_point_id("same-key")
        assert a == b


# ---------------------------------------------------------------------------
# Scenario: Vector service lite wrapper
# ---------------------------------------------------------------------------

class TestVectorServiceLite:
    """VectorServiceLite should delegate all calls to the FAISS backend."""

    @pytest.mark.asyncio
    async def test_wrapper_delegates_upsert_and_search(self, tmp_data_dir, project_id):
        """Wrapper should proxy upsert and search to FAISSService."""
        from lite.services.vector_service_lite import VectorServiceLite

        backend = FAISSService(data_dir=tmp_data_dir)
        wrapper = VectorServiceLite(backend=backend)

        vec = _random_vector()
        result = await wrapper.upsert_vector(
            project_id=project_id, vector_id="wrap-1", embedding=vec,
        )
        assert result is True

        results = await wrapper.search_vectors(
            project_id=project_id, query_vector=vec, limit=5, threshold=0.0,
        )
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_wrapper_health_check(self, tmp_data_dir):
        """Wrapper health_check should return healthy."""
        from lite.services.vector_service_lite import VectorServiceLite

        backend = FAISSService(data_dir=tmp_data_dir)
        wrapper = VectorServiceLite(backend=backend)

        health = await wrapper.health_check()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_wrapper_delete(self, tmp_data_dir, project_id):
        """Wrapper delete should proxy to FAISS backend."""
        from lite.services.vector_service_lite import VectorServiceLite

        backend = FAISSService(data_dir=tmp_data_dir)
        wrapper = VectorServiceLite(backend=backend)

        vec = _random_vector()
        await wrapper.upsert_vector(
            project_id=project_id, vector_id="wrap-del", embedding=vec,
        )

        deleted = await wrapper.delete_vector(vector_id="wrap-del")
        assert deleted is True

        info = await wrapper.get_collection_info()
        assert info["vectors_count"] == 0

    @pytest.mark.asyncio
    async def test_wrapper_initialize_collection(self, tmp_data_dir):
        """Wrapper initialize_collection should delegate to backend."""
        from lite.services.vector_service_lite import VectorServiceLite

        backend = FAISSService(data_dir=tmp_data_dir)
        wrapper = VectorServiceLite(backend=backend)

        result = await wrapper.initialize_collection(vector_size=256)
        assert result is True

    @pytest.mark.asyncio
    async def test_wrapper_delete_vectors_by_project(self, tmp_data_dir, project_id):
        """Wrapper delete_vectors_by_project should delegate to backend."""
        from lite.services.vector_service_lite import VectorServiceLite

        backend = FAISSService(data_dir=tmp_data_dir)
        wrapper = VectorServiceLite(backend=backend)

        vec = _random_vector()
        await wrapper.upsert_vector(
            project_id=project_id, vector_id="bulk-1", embedding=vec,
        )
        await wrapper.upsert_vector(
            project_id=project_id, vector_id="bulk-2", embedding=vec,
        )

        deleted = await wrapper.delete_vectors_by_project(project_id=project_id)
        assert deleted == 2

    @pytest.mark.asyncio
    async def test_wrapper_get_collection_info(self, tmp_data_dir):
        """Wrapper get_collection_info should return backend info."""
        from lite.services.vector_service_lite import VectorServiceLite

        backend = FAISSService(data_dir=tmp_data_dir)
        wrapper = VectorServiceLite(backend=backend)

        info = await wrapper.get_collection_info()
        assert info is not None
        assert info["backend"] == "faiss-cpu"

    def test_get_vector_service_lite(self, monkeypatch):
        """get_vector_service should return VectorServiceLite when ZERODB_BACKEND=lite."""
        monkeypatch.setenv("ZERODB_BACKEND", "lite")
        from lite.services.vector_service_lite import get_vector_service, VectorServiceLite

        svc = get_vector_service()
        assert isinstance(svc, VectorServiceLite)
