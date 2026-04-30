"""
ZeroDB Local Embeddings Service
Generates vector embeddings using BAAI BGE models (no API costs)
"""
import os
import time
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer


# Global model instance
model = None
model_info = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for model loading"""
    global model, model_info

    # Startup: Load model
    model_name = os.getenv("MODEL_NAME", "BAAI/bge-small-en-v1.5")
    device = os.getenv("DEVICE", "cpu")
    cache_dir = os.getenv("MODEL_CACHE_DIR", "/app/models")

    print(f"Loading model: {model_name}")
    print(f"Device: {device}")
    print(f"Cache directory: {cache_dir}")

    start_time = time.time()

    try:
        model = SentenceTransformer(
            model_name,
            device=device,
            cache_folder=cache_dir
        )

        load_time = time.time() - start_time

        # Get model info
        model_info = {
            "model_name": model_name,
            "dimensions": model.get_sentence_embedding_dimension(),
            "max_seq_length": model.max_seq_length,
            "device": device,
            "load_time_seconds": round(load_time, 2)
        }

        print(f"✅ Model loaded successfully in {load_time:.2f}s")
        print(f"   Dimensions: {model_info['dimensions']}")
        print(f"   Max sequence length: {model_info['max_seq_length']}")

    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise

    yield

    # Shutdown: Cleanup
    print("Shutting down embeddings service")
    model = None


# Create FastAPI app
app = FastAPI(
    title="ZeroDB Local Embeddings Service",
    description="Generate vector embeddings using BAAI BGE models (free, no API costs)",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models
class EmbeddingRequest(BaseModel):
    """Request for generating embeddings"""
    texts: List[str] = Field(
        ...,
        description="List of texts to embed (max 100)",
        min_items=1,
        max_items=100
    )
    normalize: bool = Field(
        default=True,
        description="Normalize embeddings to unit length"
    )


class EmbeddingResponse(BaseModel):
    """Response with generated embeddings"""
    embeddings: List[List[float]] = Field(
        ...,
        description="List of embedding vectors"
    )
    model: str = Field(
        ...,
        description="Model used for embeddings"
    )
    dimensions: int = Field(
        ...,
        description="Embedding dimensions"
    )
    count: int = Field(
        ...,
        description="Number of embeddings generated"
    )


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    model_info: Dict[str, Any]


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "ZeroDB Local Embeddings",
        "version": "1.0.0",
        "model": model_info.get("model_name"),
        "dimensions": model_info.get("dimensions"),
        "status": "ready" if model else "loading"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint

    Returns model status and info
    """
    return {
        "status": "healthy" if model else "unhealthy",
        "model_loaded": model is not None,
        "model_info": model_info
    }


@app.post("/embeddings", response_model=EmbeddingResponse, tags=["Embeddings"])
async def create_embeddings(request: EmbeddingRequest):
    """
    Generate embeddings for texts

    This endpoint uses BAAI BGE models to generate high-quality embeddings locally.
    No API costs, no rate limits, no external dependencies.

    **Supported models:**
    - `BAAI/bge-small-en-v1.5` (384 dimensions) - Default, fastest
    - `BAAI/bge-base-en-v1.5` (768 dimensions) - Balanced
    - `BAAI/bge-large-en-v1.5` (1024 dimensions) - Most accurate

    **Performance:**
    - Single text: <100ms
    - Batch (10 texts): ~200ms
    - Batch (100 texts): ~2s

    **Args:**
    - texts: List of strings to embed (max 100)
    - normalize: Normalize embeddings to unit length (recommended for cosine similarity)

    **Returns:**
    - embeddings: List of embedding vectors
    - model: Model name used
    - dimensions: Number of dimensions per embedding
    - count: Number of embeddings generated
    """
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please wait for initialization."
        )

    try:
        # Generate embeddings
        embeddings = model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            show_progress_bar=False
        )

        # Convert to list of lists
        embeddings_list = embeddings.tolist()

        return {
            "embeddings": embeddings_list,
            "model": model_info["model_name"],
            "dimensions": model_info["dimensions"],
            "count": len(embeddings_list)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embeddings: {str(e)}"
        )


@app.get("/models", tags=["Models"])
async def list_models():
    """
    List available models

    Returns information about available BAAI BGE models
    """
    return {
        "current_model": model_info.get("model_name"),
        "available_models": [
            {
                "name": "BAAI/bge-small-en-v1.5",
                "dimensions": 384,
                "description": "Small, fast model (recommended for most use cases)",
                "performance": "~50ms per text"
            },
            {
                "name": "BAAI/bge-base-en-v1.5",
                "dimensions": 768,
                "description": "Balanced model with good accuracy",
                "performance": "~100ms per text"
            },
            {
                "name": "BAAI/bge-large-en-v1.5",
                "dimensions": 1024,
                "description": "Large, most accurate model",
                "performance": "~200ms per text"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
