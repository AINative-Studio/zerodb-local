"""
Local Embeddings Service
In-process embedding generation using sentence-transformers.
Eliminates the need for a separate embeddings HTTP service.
"""
import os
from pathlib import Path
from typing import List, Dict, Any

# Module-level singleton for model caching
_model = None
_model_name = "BAAI/bge-small-en-v1.5"
_embedding_dim = 384

# Configure model cache directory
_cache_dir = str(Path.home() / ".zerodb" / "models")
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", _cache_dir)


def _get_model():
    """
    Load and cache the SentenceTransformer model as a module-level singleton.
    The model is loaded once on first call and reused for all subsequent calls.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        Path(_cache_dir).mkdir(parents=True, exist_ok=True)
        _model = SentenceTransformer(_model_name, cache_folder=_cache_dir)
    return _model


class EmbeddingsServiceLocal:
    """
    Service for generating vector embeddings locally using sentence-transformers.
    Uses BAAI/bge-small-en-v1.5 (384 dimensions) loaded in-process.
    No external service dependency required.
    """

    def __init__(self):
        self.model_name = _model_name
        self.embedding_dim = _embedding_dim

    async def generate_embeddings(
        self,
        texts: List[str],
        normalize: bool = True,
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            normalize: Whether to normalize embeddings to unit length

        Returns:
            List of embedding vectors (384 dimensions)

        Raises:
            ValueError: If texts is not a list or contains non-string elements
        """
        if not isinstance(texts, list):
            raise ValueError("texts must be a list of strings")

        if len(texts) == 0:
            return []

        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise ValueError(f"Element at index {i} is not a string: {type(text)}")

        model = _get_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the local embeddings model is loaded and operational.

        Returns:
            Health status dict with model info
        """
        try:
            model = _get_model()
            return {
                "status": "healthy",
                "model": self.model_name,
                "dimensions": self.embedding_dim,
                "backend": "local",
                "cache_dir": _cache_dir,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Global instance (mirrors the pattern in embeddings_service.py)
embeddings_service_local = EmbeddingsServiceLocal()
