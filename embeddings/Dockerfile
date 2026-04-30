# ZeroDB Local Embeddings Service
# Uses BAAI BGE models for local embedding generation (no API costs)

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create directory for model cache
RUN mkdir -p /app/models

# Set environment variables
ENV MODEL_NAME=BAAI/bge-small-en-v1.5
ENV DEVICE=cpu
ENV MODEL_CACHE_DIR=/app/models

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
