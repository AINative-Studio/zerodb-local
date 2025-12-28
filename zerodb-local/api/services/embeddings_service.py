"""
Embeddings Service
Wrapper for local embeddings generation via HTTP API
"""
import os
import httpx
from typing import List, Dict, Any


class EmbeddingsService:
    """
    Service for generating vector embeddings using local BAAI BGE models
    No API costs - embeddings are generated locally
    """

    def __init__(self):
        self.embeddings_url = os.getenv("EMBEDDINGS_URL", "http://embeddings:8001")
        self.timeout = 30.0  # Embeddings can take a few seconds

    async def generate_embeddings(
        self,
        texts: List[str],
        normalize: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts

        Args:
            texts: List of text strings to embed
            normalize: Whether to normalize embeddings to unit length

        Returns:
            List of embedding vectors (384/768/1024 dimensions depending on model)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.embeddings_url}/embeddings",
                json={
                    "texts": texts,
                    "normalize": normalize
                },
                timeout=self.timeout
            )

            if response.status_code != 200:
                raise Exception(f"Embeddings service error: {response.text}")

            data = response.json()
            return data["embeddings"]

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if embeddings service is healthy

        Returns:
            Health status dict with model info
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.embeddings_url}/health",
                    timeout=5.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}"
                    }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
embeddings_service = EmbeddingsService()
