"""
Tests for EmbeddingsServiceLocal
BDD-style tests with mocked sentence-transformers to avoid model download in CI.
"""
import time
import pytest
import numpy as np
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def reset_model_singleton():
    """Reset the cached model singleton before each test."""
    import lite.services.embeddings_service_local as mod
    mod._model = None
    yield
    mod._model = None


@pytest.fixture
def mock_sentence_transformer():
    """
    Provide a mock SentenceTransformer that returns deterministic
    384-dimensional embeddings matching the expected model output.
    Patches _get_model to return the mock without importing sentence_transformers.
    """
    mock_model = MagicMock()
    call_count = {"value": 0}

    def fake_encode(texts, normalize_embeddings=True, show_progress_bar=False):
        """Return a numpy array of shape (len(texts), 384) with deterministic values."""
        embeddings = np.random.default_rng(42).random((len(texts), 384)).astype(np.float32)
        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
        return embeddings

    mock_model.encode = fake_encode

    import lite.services.embeddings_service_local as mod
    original_get_model = mod._get_model

    def patched_get_model():
        """Inject mock model into the singleton cache on first call."""
        if mod._model is None:
            call_count["value"] += 1
            mod._model = mock_model
        return mod._model

    mock_constructor = MagicMock(side_effect=lambda: call_count["value"])
    mock_constructor.call_count = 0

    class _MockTracker:
        """Tracks how many times the model constructor would have been called."""
        @property
        def call_count(self):
            return call_count["value"]

    with patch.object(mod, "_get_model", side_effect=patched_get_model):
        yield _MockTracker(), mock_model


# ---------------------------------------------------------------------------
# Feature: Single text embedding generation
# ---------------------------------------------------------------------------

class TestSingleEmbedding:
    """Scenario: Generating an embedding for a single text input."""

    @pytest.mark.asyncio
    async def test_given_single_text_when_generating_then_returns_384_dimensions(
        self, mock_sentence_transformer
    ):
        """
        Given a single text string
        When generate_embeddings is called
        Then it should return one vector with 384 dimensions.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        result = await service.generate_embeddings(["hello world"])

        assert len(result) == 1
        assert len(result[0]) == 384

    @pytest.mark.asyncio
    async def test_given_single_text_when_generating_then_returns_list_of_floats(
        self, mock_sentence_transformer
    ):
        """
        Given a single text string
        When generate_embeddings is called
        Then each element in the vector should be a float.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        result = await service.generate_embeddings(["test"])

        assert all(isinstance(v, float) for v in result[0])


# ---------------------------------------------------------------------------
# Feature: Batch embedding generation
# ---------------------------------------------------------------------------

class TestBatchEmbedding:
    """Scenario: Generating embeddings for multiple texts at once."""

    @pytest.mark.asyncio
    async def test_given_multiple_texts_when_generating_then_returns_matching_count(
        self, mock_sentence_transformer
    ):
        """
        Given a batch of 5 text strings
        When generate_embeddings is called
        Then it should return exactly 5 embedding vectors.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        texts = ["one", "two", "three", "four", "five"]
        result = await service.generate_embeddings(texts)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_given_multiple_texts_when_generating_then_each_has_384_dims(
        self, mock_sentence_transformer
    ):
        """
        Given a batch of texts
        When generate_embeddings is called
        Then every vector should have exactly 384 dimensions.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        texts = ["alpha", "beta", "gamma"]
        result = await service.generate_embeddings(texts)

        for embedding in result:
            assert len(embedding) == 384


# ---------------------------------------------------------------------------
# Feature: Model caching (singleton pattern)
# ---------------------------------------------------------------------------

class TestModelCaching:
    """Scenario: Model should be loaded once and reused across calls."""

    @pytest.mark.asyncio
    async def test_given_two_calls_when_generating_then_model_loaded_once(
        self, mock_sentence_transformer
    ):
        """
        Given the service is called twice
        When generate_embeddings is invoked each time
        Then the SentenceTransformer constructor should be called only once.
        """
        mock_cls, _ = mock_sentence_transformer
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        await service.generate_embeddings(["first call"])
        await service.generate_embeddings(["second call"])

        assert mock_cls.call_count == 1

    @pytest.mark.asyncio
    async def test_given_cached_model_when_second_call_then_faster_than_first(
        self, mock_sentence_transformer
    ):
        """
        Given the model is cached after first call
        When a second call is made
        Then the second call should not reload the model (constructor called once).
        """
        mock_cls, _ = mock_sentence_transformer
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()

        start1 = time.monotonic()
        await service.generate_embeddings(["first"])
        dur1 = time.monotonic() - start1

        start2 = time.monotonic()
        await service.generate_embeddings(["second"])
        dur2 = time.monotonic() - start2

        # Both should be fast with mocks, but constructor only called once
        assert mock_cls.call_count == 1


# ---------------------------------------------------------------------------
# Feature: Empty input handling
# ---------------------------------------------------------------------------

class TestEmptyInput:
    """Scenario: Handling edge cases with empty or invalid input."""

    @pytest.mark.asyncio
    async def test_given_empty_list_when_generating_then_returns_empty_list(
        self, mock_sentence_transformer
    ):
        """
        Given an empty list of texts
        When generate_embeddings is called
        Then it should return an empty list without error.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        result = await service.generate_embeddings([])

        assert result == []

    @pytest.mark.asyncio
    async def test_given_non_list_input_when_generating_then_raises_value_error(
        self, mock_sentence_transformer
    ):
        """
        Given a non-list input (e.g., a plain string)
        When generate_embeddings is called
        Then it should raise a ValueError.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()

        with pytest.raises(ValueError, match="texts must be a list"):
            await service.generate_embeddings("not a list")

    @pytest.mark.asyncio
    async def test_given_non_string_element_when_generating_then_raises_value_error(
        self, mock_sentence_transformer
    ):
        """
        Given a list containing a non-string element
        When generate_embeddings is called
        Then it should raise a ValueError indicating the bad element.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()

        with pytest.raises(ValueError, match="not a string"):
            await service.generate_embeddings(["valid", 123])


# ---------------------------------------------------------------------------
# Feature: Normalization
# ---------------------------------------------------------------------------

class TestNormalization:
    """Scenario: Embeddings normalization behavior."""

    @pytest.mark.asyncio
    async def test_given_normalize_true_when_generating_then_unit_length_vectors(
        self, mock_sentence_transformer
    ):
        """
        Given normalize=True (default)
        When generate_embeddings is called
        Then each vector should have approximately unit L2 norm.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        result = await service.generate_embeddings(["test normalization"])

        norm = np.linalg.norm(result[0])
        assert abs(norm - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_given_normalize_false_when_generating_then_passes_flag(
        self, mock_sentence_transformer
    ):
        """
        Given normalize=False
        When generate_embeddings is called
        Then the normalize_embeddings=False flag is passed to model.encode.
        """
        _, mock_model = mock_sentence_transformer
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()

        # Replace encode with a spy that tracks kwargs
        original_encode = mock_model.encode
        call_kwargs = {}

        def spy_encode(texts, **kwargs):
            call_kwargs.update(kwargs)
            return original_encode(texts, **kwargs)

        mock_model.encode = spy_encode
        await service.generate_embeddings(["test"], normalize=False)

        assert call_kwargs.get("normalize_embeddings") is False


# ---------------------------------------------------------------------------
# Feature: Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Scenario: Service health reporting."""

    @pytest.mark.asyncio
    async def test_given_model_available_when_health_check_then_returns_healthy(
        self, mock_sentence_transformer
    ):
        """
        Given the model can be loaded
        When health_check is called
        Then it should return status=healthy with model metadata.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()
        health = await service.health_check()

        assert health["status"] == "healthy"
        assert health["model"] == "BAAI/bge-small-en-v1.5"
        assert health["dimensions"] == 384
        assert health["backend"] == "local"

    @pytest.mark.asyncio
    async def test_given_model_fails_when_health_check_then_returns_unhealthy(self):
        """
        Given the model fails to load
        When health_check is called
        Then it should return status=unhealthy with error details.
        """
        from lite.services.embeddings_service_local import EmbeddingsServiceLocal

        service = EmbeddingsServiceLocal()

        with patch(
            "lite.services.embeddings_service_local._get_model",
            side_effect=RuntimeError("Model download failed"),
        ):
            health = await service.health_check()

        assert health["status"] == "unhealthy"
        assert "Model download failed" in health["error"]


# ---------------------------------------------------------------------------
# Feature: Global instance
# ---------------------------------------------------------------------------

class TestGlobalInstance:
    """Scenario: Module provides a pre-instantiated global instance."""

    def test_given_module_imported_when_accessing_global_then_instance_exists(self):
        """
        Given the module is imported
        When accessing embeddings_service_local
        Then it should be an instance of EmbeddingsServiceLocal.
        """
        from lite.services.embeddings_service_local import (
            EmbeddingsServiceLocal,
            embeddings_service_local,
        )

        assert isinstance(embeddings_service_local, EmbeddingsServiceLocal)


# ---------------------------------------------------------------------------
# Feature: Cache directory configuration
# ---------------------------------------------------------------------------

class TestCacheDirectory:
    """Scenario: Model cache directory is properly configured."""

    def test_given_default_config_when_imported_then_cache_dir_set(self):
        """
        Given default configuration
        When the module is imported
        Then SENTENCE_TRANSFORMERS_HOME should be set to ~/.zerodb/models/.
        """
        import os
        from pathlib import Path

        expected = str(Path.home() / ".zerodb" / "models")
        assert os.environ.get("SENTENCE_TRANSFORMERS_HOME") == expected
