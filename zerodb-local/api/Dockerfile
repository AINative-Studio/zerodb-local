# ZeroDB Local API - Production Dockerfile
# Multi-stage build for optimized image size

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY api/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (before copying files)
RUN useradd -m -u 1000 zerodb

# Copy Python dependencies from builder stage to zerodb user home
COPY --from=builder /root/.local /home/zerodb/.local

# Make sure scripts in .local are usable
ENV PATH=/home/zerodb/.local/bin:$PATH

# Copy application code and lite module (build context is repo root)
COPY api/ .
COPY lite/ ./lite/

# Change ownership of app directory
RUN chown -R zerodb:zerodb /app /home/zerodb/.local

# Switch to non-root user
USER zerodb

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start API server
# Single worker for local dev — ensures cloud auth state persists across requests.
# For production, use multiple workers with shared state (Redis/file).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
