# ZeroDB Local - Environment Setup

Complete guide to configuring ZeroDB Local for different environments: local development, staging, and production.

## Table of Contents

- [Environment Files Overview](#environment-files-overview)
- [Local Development Setup](#local-development-setup)
- [Staging Environment Setup](#staging-environment-setup)
- [Production Environment Setup](#production-environment-setup)
- [Environment Variables Reference](#environment-variables-reference)
- [Service-Specific Configuration](#service-specific-configuration)
- [Port Configuration](#port-configuration)
- [Performance Tuning](#performance-tuning)
- [Security Best Practices](#security-best-practices)
- [Multi-Environment Workflows](#multi-environment-workflows)

## Environment Files Overview

ZeroDB Local uses environment files to manage configuration across different deployment scenarios:

| File | Purpose | Committed to Git |
|------|---------|-----------------|
| `.env.local.example` | Template for local development | Yes |
| `.env.staging.example` | Template for staging environment | Yes |
| `.env.production.example` | Template for production environment | Yes |
| `.env.local` | Your local development config | No (gitignored) |
| `.env.staging` | Your staging config | No (gitignored) |
| `.env.production` | Your production config | No (gitignored) |

**Important:** Never commit actual `.env.*` files (without `.example` suffix) to version control. They contain sensitive credentials.

## Local Development Setup

Local development prioritizes ease of use, fast iteration, and verbose logging.

### Quick Setup

```bash
# Copy the template
cp .env.local.example .env.local

# Start services
docker-compose up -d
```

### Recommended `.env.local` Configuration

```env
# ======================
# ENVIRONMENT
# ======================
ENVIRONMENT=local
DEBUG=true
LOG_LEVEL=debug

# ======================
# DATABASE
# ======================
POSTGRES_USER=zerodb
POSTGRES_PASSWORD=localpass
POSTGRES_DB=zerodb_local
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Connection pool (relaxed for local)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# ======================
# VECTOR SEARCH
# ======================
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

# ======================
# OBJECT STORAGE
# ======================
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_HOST=minio
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_BUCKET=zerodb-local

# ======================
# EVENT STREAMING
# ======================
REDPANDA_ADVERTISED_HOST=redpanda
REDPANDA_ADVERTISED_PORT=9092
REDPANDA_SCHEMA_REGISTRY_PORT=8081

# ======================
# EMBEDDINGS SERVICE
# ======================
EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5
EMBEDDINGS_DEVICE=cpu
EMBEDDINGS_BATCH_SIZE=32
EMBEDDINGS_MAX_LENGTH=512

# For Apple Silicon (optional)
# EMBEDDINGS_DEVICE=mps

# For NVIDIA GPU (optional)
# EMBEDDINGS_DEVICE=cuda

# ======================
# API SERVER
# ======================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
API_RELOAD=true

# CORS (allow all for local development)
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*

# JWT (use simple secret for local)
JWT_SECRET=local-development-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# ======================
# DASHBOARD
# ======================
DASHBOARD_PORT=3000
VITE_API_URL=http://localhost:8000

# ======================
# CLOUD SYNC (Optional)
# ======================
CLOUD_API_URL=https://api.ainative.studio
CLOUD_API_KEY=
SYNC_ENABLED=false
SYNC_INTERVAL_SECONDS=300

# ======================
# FEATURE FLAGS
# ======================
ENABLE_TELEMETRY=false
ENABLE_ANALYTICS=false
ENABLE_CACHE=true
CACHE_TTL_SECONDS=60
```

### Local Development Tips

**Hot Reload for API:**
```bash
cd api
pip install -e .
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Hot Reload for Dashboard:**
```bash
cd dashboard
npm install
npm run dev
```

**Verbose Logging:**
```env
LOG_LEVEL=debug
DEBUG=true
```

**Disable Services You Don't Need:**
```bash
# Only start specific services
docker-compose up -d postgres qdrant api
```

## Staging Environment Setup

Staging mirrors production configuration but with relaxed security for testing.

### Setup Steps

```bash
# Copy the template
cp .env.staging.example .env.staging

# Edit configuration
nano .env.staging

# Start with staging config
docker-compose --env-file .env.staging up -d
```

### Recommended `.env.staging` Configuration

```env
# ======================
# ENVIRONMENT
# ======================
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=info

# ======================
# DATABASE
# ======================
POSTGRES_USER=zerodb
POSTGRES_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
POSTGRES_DB=zerodb_staging
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Connection pool (moderate limits)
DB_POOL_SIZE=15
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=20
DB_POOL_RECYCLE=1800

# ======================
# VECTOR SEARCH
# ======================
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

# ======================
# OBJECT STORAGE
# ======================
MINIO_ROOT_USER=zerodb-staging
MINIO_ROOT_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
MINIO_HOST=minio
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_BUCKET=zerodb-staging

# ======================
# EVENT STREAMING
# ======================
REDPANDA_ADVERTISED_HOST=redpanda
REDPANDA_ADVERTISED_PORT=9092
REDPANDA_SCHEMA_REGISTRY_PORT=8081

# ======================
# EMBEDDINGS SERVICE
# ======================
EMBEDDINGS_MODEL=BAAI/bge-base-en-v1.5
EMBEDDINGS_DEVICE=cpu
EMBEDDINGS_BATCH_SIZE=64
EMBEDDINGS_MAX_LENGTH=512

# ======================
# API SERVER
# ======================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=2
API_RELOAD=false

# CORS (restrict to staging domains)
CORS_ORIGINS=https://staging.ainative.studio,https://staging-dashboard.ainative.studio
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,PATCH
CORS_ALLOW_HEADERS=*

# JWT (use strong secret)
JWT_SECRET=GENERATE_RANDOM_SECRET_HERE
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=12

# ======================
# DASHBOARD
# ======================
DASHBOARD_PORT=3000
VITE_API_URL=https://staging-api.ainative.studio

# ======================
# CLOUD SYNC
# ======================
CLOUD_API_URL=https://api.ainative.studio
CLOUD_API_KEY=your_staging_api_key_here
SYNC_ENABLED=true
SYNC_INTERVAL_SECONDS=600

# ======================
# MONITORING
# ======================
ENABLE_TELEMETRY=true
ENABLE_ANALYTICS=true
ENABLE_CACHE=true
CACHE_TTL_SECONDS=300

# ======================
# RATE LIMITING
# ======================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

### Staging-Specific Considerations

**Generate Strong Secrets:**
```bash
# Generate random JWT secret
openssl rand -base64 32

# Generate random passwords
openssl rand -base64 24
```

**SSL/TLS Configuration:**
For HTTPS in staging, use a reverse proxy like Nginx or Caddy in front of the API:

```yaml
# docker-compose.staging.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/staging.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - api
```

## Production Environment Setup

Production prioritizes security, performance, and reliability.

### Setup Steps

```bash
# Copy the template
cp .env.production.example .env.production

# Edit configuration with secure values
nano .env.production

# Start with production config
docker-compose --env-file .env.production up -d
```

### Recommended `.env.production` Configuration

```env
# ======================
# ENVIRONMENT
# ======================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=warning

# ======================
# DATABASE
# ======================
POSTGRES_USER=zerodb
POSTGRES_PASSWORD=USE_VERY_STRONG_PASSWORD_HERE
POSTGRES_DB=zerodb_production
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Connection pool (strict limits)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=900

# ======================
# VECTOR SEARCH
# ======================
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

# ======================
# OBJECT STORAGE
# ======================
MINIO_ROOT_USER=zerodb-production
MINIO_ROOT_PASSWORD=USE_VERY_STRONG_PASSWORD_HERE
MINIO_HOST=minio
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_BUCKET=zerodb-production

# ======================
# EVENT STREAMING
# ======================
REDPANDA_ADVERTISED_HOST=redpanda
REDPANDA_ADVERTISED_PORT=9092
REDPANDA_SCHEMA_REGISTRY_PORT=8081

# ======================
# EMBEDDINGS SERVICE
# ======================
EMBEDDINGS_MODEL=BAAI/bge-large-en-v1.5
EMBEDDINGS_DEVICE=cuda
EMBEDDINGS_BATCH_SIZE=128
EMBEDDINGS_MAX_LENGTH=512

# ======================
# API SERVER
# ======================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false

# CORS (restrict to production domains only)
CORS_ORIGINS=https://ainative.studio,https://dashboard.ainative.studio
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,PATCH
CORS_ALLOW_HEADERS=Authorization,Content-Type

# JWT (use cryptographically random secret)
JWT_SECRET=USE_CRYPTOGRAPHICALLY_RANDOM_SECRET_HERE
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=6

# ======================
# DASHBOARD
# ======================
DASHBOARD_PORT=3000
VITE_API_URL=https://api.ainative.studio

# ======================
# CLOUD SYNC
# ======================
CLOUD_API_URL=https://api.ainative.studio
CLOUD_API_KEY=your_production_api_key_here
SYNC_ENABLED=true
SYNC_INTERVAL_SECONDS=300

# ======================
# MONITORING
# ======================
ENABLE_TELEMETRY=true
ENABLE_ANALYTICS=true
ENABLE_CACHE=true
CACHE_TTL_SECONDS=600

# ======================
# RATE LIMITING
# ======================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# ======================
# SECURITY
# ======================
ALLOWED_HOSTS=api.ainative.studio,dashboard.ainative.studio
SECURE_COOKIES=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true

# ======================
# BACKUP
# ======================
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=zerodb-backups
BACKUP_S3_REGION=us-west-2
```

### Production Security Checklist

- [ ] Change all default passwords
- [ ] Use cryptographically random secrets (32+ chars)
- [ ] Restrict CORS to production domains only
- [ ] Enable HTTPS/TLS with valid certificates
- [ ] Configure rate limiting
- [ ] Enable security headers
- [ ] Set up database backups
- [ ] Configure monitoring and alerts
- [ ] Restrict network access (firewall rules)
- [ ] Use secrets management (AWS Secrets Manager, Vault, etc.)
- [ ] Enable audit logging
- [ ] Set up log aggregation (ELK, Datadog, etc.)

### Production Deployment Patterns

**Docker Swarm:**
```bash
docker stack deploy -c docker-compose.yml -c docker-compose.production.yml zerodb
```

**Kubernetes:**
```bash
# Convert docker-compose to Kubernetes manifests
kompose convert -f docker-compose.yml

# Apply with production config
kubectl apply -f k8s/
kubectl create secret generic zerodb-secrets --from-env-file=.env.production
```

**Cloud Deployment (AWS/GCP/Azure):**
- Use managed PostgreSQL (RDS, Cloud SQL, Azure Database)
- Use managed object storage (S3, GCS, Azure Blob)
- Deploy containers to ECS, GKE, or AKS
- Use managed load balancers
- Configure auto-scaling

## Environment Variables Reference

### Complete Variable List

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENVIRONMENT` | string | local | Environment name (local/staging/production) |
| `DEBUG` | boolean | false | Enable debug mode |
| `LOG_LEVEL` | string | info | Logging level (debug/info/warning/error) |
| `POSTGRES_USER` | string | zerodb | PostgreSQL username |
| `POSTGRES_PASSWORD` | string | localpass | PostgreSQL password |
| `POSTGRES_DB` | string | zerodb_local | PostgreSQL database name |
| `POSTGRES_HOST` | string | postgres | PostgreSQL host |
| `POSTGRES_PORT` | integer | 5432 | PostgreSQL port |
| `DB_POOL_SIZE` | integer | 10 | Database connection pool size |
| `DB_MAX_OVERFLOW` | integer | 10 | Max overflow connections |
| `DB_POOL_TIMEOUT` | integer | 30 | Connection timeout (seconds) |
| `DB_POOL_RECYCLE` | integer | 3600 | Recycle connections after (seconds) |
| `QDRANT_HOST` | string | qdrant | Qdrant host |
| `QDRANT_PORT` | integer | 6333 | Qdrant HTTP port |
| `QDRANT_GRPC_PORT` | integer | 6334 | Qdrant gRPC port |
| `MINIO_ROOT_USER` | string | minioadmin | MinIO root username |
| `MINIO_ROOT_PASSWORD` | string | minioadmin | MinIO root password |
| `MINIO_HOST` | string | minio | MinIO host |
| `MINIO_PORT` | integer | 9000 | MinIO API port |
| `MINIO_CONSOLE_PORT` | integer | 9001 | MinIO console port |
| `MINIO_BUCKET` | string | zerodb-local | Default bucket name |
| `REDPANDA_ADVERTISED_HOST` | string | redpanda | RedPanda host |
| `REDPANDA_ADVERTISED_PORT` | integer | 9092 | RedPanda Kafka port |
| `EMBEDDINGS_MODEL` | string | BAAI/bge-small-en-v1.5 | Embedding model name |
| `EMBEDDINGS_DEVICE` | string | cpu | Device (cpu/cuda/mps) |
| `EMBEDDINGS_BATCH_SIZE` | integer | 32 | Embedding batch size |
| `EMBEDDINGS_MAX_LENGTH` | integer | 512 | Max token length |
| `API_HOST` | string | 0.0.0.0 | API bind host |
| `API_PORT` | integer | 8000 | API port |
| `API_WORKERS` | integer | 1 | Number of worker processes |
| `API_RELOAD` | boolean | false | Enable auto-reload |
| `CORS_ORIGINS` | string | * | Allowed CORS origins |
| `JWT_SECRET` | string | - | JWT signing secret |
| `JWT_ALGORITHM` | string | HS256 | JWT algorithm |
| `JWT_EXPIRATION_HOURS` | integer | 24 | JWT expiration time |
| `CLOUD_API_KEY` | string | - | ZeroDB Cloud API key |
| `SYNC_ENABLED` | boolean | false | Enable cloud sync |
| `SYNC_INTERVAL_SECONDS` | integer | 300 | Sync interval |
| `RATE_LIMIT_PER_MINUTE` | integer | 60 | Requests per minute |

## Service-Specific Configuration

### PostgreSQL Tuning

For better performance, adjust PostgreSQL settings:

```yaml
# docker-compose.yml
services:
  postgres:
    command:
      - "postgres"
      - "-c"
      - "max_connections=200"
      - "-c"
      - "shared_buffers=256MB"
      - "-c"
      - "effective_cache_size=1GB"
      - "-c"
      - "maintenance_work_mem=128MB"
      - "-c"
      - "checkpoint_completion_target=0.9"
      - "-c"
      - "wal_buffers=16MB"
      - "-c"
      - "default_statistics_target=100"
      - "-c"
      - "random_page_cost=1.1"
      - "-c"
      - "effective_io_concurrency=200"
```

### Qdrant Configuration

```env
# For large vector collections
QDRANT_COLLECTION_MAX_SIZE=10000000
QDRANT_HNSW_EF_CONSTRUCT=200
QDRANT_HNSW_M=16
```

### MinIO Configuration

```env
# Enable versioning
MINIO_VERSIONING=on

# Set retention policy
MINIO_RETENTION_DAYS=90
```

## Port Configuration

### Changing Default Ports

Edit `docker-compose.yml` to change exposed ports:

```yaml
services:
  api:
    ports:
      - "8080:8000"  # Expose on 8080 instead of 8000

  dashboard:
    ports:
      - "3001:3000"  # Expose on 3001 instead of 3000
```

### Port Conflicts Resolution

**Check for conflicts:**
```bash
lsof -i :8000  # Check if port 8000 is in use
```

**Kill conflicting process:**
```bash
kill -9 $(lsof -t -i :8000)
```

## Performance Tuning

### Hardware Recommendations by Workload

**Small Workload (<10K vectors, <1GB data):**
- 4GB RAM
- 2 CPU cores
- Standard HDD

**Medium Workload (10K-100K vectors, 1-10GB data):**
- 8GB RAM
- 4 CPU cores
- SSD storage

**Large Workload (100K+ vectors, 10GB+ data):**
- 16GB+ RAM
- 8+ CPU cores
- NVMe SSD
- GPU for embeddings (optional)

### Docker Resource Limits

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### Embeddings Performance

**CPU (default):**
- ~100ms per embedding
- Good for development

**Apple Silicon (MPS):**
```env
EMBEDDINGS_DEVICE=mps
```
- ~20-30ms per embedding

**NVIDIA GPU (CUDA):**
```env
EMBEDDINGS_DEVICE=cuda
```
- ~5-10ms per embedding
- Requires NVIDIA GPU and CUDA drivers

## Security Best Practices

### Secrets Management

**Never hardcode secrets in .env files for production.**

Use environment-specific secrets management:

**AWS Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name zerodb/production/postgres-password \
  --secret-string "your-secret-password"
```

**Docker Secrets:**
```yaml
# docker-compose.production.yml
services:
  postgres:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password

secrets:
  postgres_password:
    external: true
```

### Network Isolation

```yaml
# docker-compose.yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No internet access

services:
  api:
    networks:
      - frontend
      - backend

  postgres:
    networks:
      - backend  # Only accessible from backend network
```

### Read-Only Containers

```yaml
services:
  api:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

## Multi-Environment Workflows

### Switch Between Environments

```bash
# Start local
docker-compose --env-file .env.local up -d

# Stop and switch to staging
docker-compose --env-file .env.local down
docker-compose --env-file .env.staging up -d

# Stop and switch to production
docker-compose --env-file .env.staging down
docker-compose --env-file .env.production up -d
```

### Environment-Specific Docker Compose Files

```bash
# Use override files
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

### Configuration Validation

```bash
# Validate environment file
docker-compose --env-file .env.production config

# Check for missing variables
docker-compose --env-file .env.production config | grep -i "warning"
```

## Summary

You now have complete control over ZeroDB Local configuration across all environments:

- **Local**: Fast iteration, verbose logging, relaxed security
- **Staging**: Production-like, testing-friendly, moderate security
- **Production**: Secure, performant, reliable

Key takeaways:
- Never commit `.env.*` files (without `.example`) to git
- Use strong, random secrets in staging and production
- Tune resource limits based on workload
- Follow security best practices for production deployments
- Use environment-specific compose files for complex setups

For more information:
- [Quick Start](./QUICK_START.md) - Get started quickly
- [Data Management](./DATA_MANAGEMENT.md) - Backups and data lifecycle
- [Troubleshooting](./TROUBLESHOOTING.md) - Common configuration issues
