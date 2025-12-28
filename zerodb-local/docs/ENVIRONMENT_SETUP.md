# Environment Setup Guide

This guide explains how to configure ZeroDB Local for different environments: local development, staging, and production.

## Quick Start

For local development, the default `.env.local.example` is sufficient:

```bash
cp .env.local.example .env.local
docker-compose up -d
```

## Environment Files

ZeroDB Local supports three environment configurations:

| File | Purpose | Security Level |
|------|---------|---------------|
| `.env.local` | Local development | Low (default passwords OK) |
| `.env.staging` | Staging deployment | Medium (change passwords) |
| `.env.production` | Production deployment | High (strong secrets required) |

## Switching Environments

Set the `ZERODB_ENV` variable to control which environment is active:

```bash
# Local development (default)
export ZERODB_ENV=local
docker-compose --env-file .env.local up -d

# Staging
export ZERODB_ENV=staging
docker-compose --env-file .env.staging up -d

# Production
export ZERODB_ENV=production
docker-compose --env-file .env.production up -d
```

## Local Development Environment

**Purpose:** Fast iteration, debugging, no security concerns

**Setup:**
```bash
cp .env.local.example .env.local
# No changes needed for local dev
docker-compose up -d
```

**Default Credentials:**
- PostgreSQL: `zerodb` / `localpass`
- MinIO: `minioadmin` / `minioadmin`

**Features:**
- ✅ Debug mode enabled
- ✅ API docs at `/docs`
- ✅ SQL query logging
- ✅ Hot reload
- ❌ No SSL/TLS
- ❌ Weak passwords (OK for local)

## Staging Environment

**Purpose:** Pre-production testing, integration testing

**Setup:**
```bash
cp .env.staging.example .env.staging
nano .env.staging  # Update passwords and API keys
docker-compose --env-file .env.staging up -d
```

**Required Changes:**
```bash
# Generate strong passwords
openssl rand -hex 32

# Update these variables:
POSTGRES_PASSWORD=<generated-password>
MINIO_ACCESS_KEY=<generated-key>
MINIO_SECRET_KEY=<generated-secret>
SECRET_KEY=<generated-secret>
CLOUD_API_KEY=<get-from-dashboard>
```

**Features:**
- ✅ Production-like configuration
- ✅ API docs enabled (for testing)
- ✅ Prometheus metrics
- ✅ Auto-sync every 5 minutes
- ✅ Cloud-wins conflict resolution
- ❌ Debug mode disabled

## Production Environment

**Purpose:** Live production deployment

**Setup:**
```bash
cp .env.production.example .env.production
nano .env.production  # MUST update all secrets
docker-compose --env-file .env.production up -d
```

**⚠️ CRITICAL: Required Changes Before Deployment**

1. **Generate Strong Secrets:**
   ```bash
   # PostgreSQL password (min 32 characters)
   openssl rand -base64 32

   # MinIO credentials (min 32 characters)
   openssl rand -base64 32

   # JWT secret (min 64 characters for production)
   openssl rand -hex 32

   # Copy these values to .env.production
   ```

2. **Update API Keys:**
   ```bash
   # Get production API key from:
   # https://www.ainative.studio/dashboard/api-keys
   CLOUD_API_KEY=<your-production-key>
   ```

3. **Set CORS Origins:**
   ```bash
   # Only allow your production domains
   CORS_ORIGINS=https://www.yourcompany.com,https://dashboard.yourcompany.com
   ```

4. **Configure Backup:**
   ```bash
   BACKUP_ENABLED=true
   BACKUP_SCHEDULE=0 2 * * *  # Daily at 2 AM
   BACKUP_RETENTION_DAYS=30
   ```

**Features:**
- ✅ Maximum security
- ✅ Manual sync only (no auto-sync)
- ✅ Manual conflict resolution
- ✅ Prometheus metrics
- ✅ Automated backups
- ❌ API docs disabled
- ❌ Debug mode disabled
- ❌ SQL logging disabled

## Environment Variables Reference

### Critical Security Variables

| Variable | Local | Staging | Production | Notes |
|----------|-------|---------|------------|-------|
| `POSTGRES_PASSWORD` | `localpass` | Strong (32+) | Strong (32+) | Database password |
| `MINIO_SECRET_KEY` | `minioadmin` | Strong (32+) | Strong (32+) | Object storage secret |
| `SECRET_KEY` | Any | Strong (32+) | Strong (64+) | JWT signing key |
| `CLOUD_API_KEY` | Optional | Required | Required | Cloud sync API key |
| `CORS_ORIGINS` | `*` | Specific | Specific | Allowed domains |

### Performance Variables

| Variable | Local | Staging | Production | Notes |
|----------|-------|---------|------------|-------|
| `API_WORKERS` | 4 | 8 | 16 | Uvicorn workers |
| `DB_POOL_SIZE` | 20 | 50 | 100 | Connection pool |
| `EMBEDDINGS_MODEL` | small | small | base | BGE model size |

### Sync Variables

| Variable | Local | Staging | Production | Notes |
|----------|-------|---------|------------|-------|
| `SYNC_MODE` | incremental | incremental | incremental | Sync strategy |
| `CONFLICT_RESOLUTION` | newest-wins | cloud-wins | manual | Conflict handling |
| `AUTO_SYNC_INTERVAL` | 0 (disabled) | 300 (5 min) | 0 (disabled) | Auto-sync frequency |

## Validation

After setting up an environment, validate the configuration:

```bash
# Check services are running
docker-compose ps

# Verify health checks
curl http://localhost:8000/health
curl http://localhost:6333/healthz
curl http://localhost:9000/minio/health/live
curl http://localhost:8001/health

# Check logs for errors
docker-compose logs -f zerodb-api
```

## Security Checklist

Before deploying to production:

- [ ] All passwords are strong (min 32 characters)
- [ ] JWT secret is strong (min 64 characters)
- [ ] Cloud API key is production key (not development)
- [ ] CORS origins are restricted to production domains
- [ ] Debug mode is disabled (`DEBUG=false`)
- [ ] API docs are disabled (`ENABLE_DOCS=false`)
- [ ] SQL logging is disabled (`SQL_ECHO=false`)
- [ ] Auto-sync is disabled or set to manual
- [ ] Backup is configured and tested
- [ ] Prometheus metrics are enabled
- [ ] Alert webhooks are configured
- [ ] SSL/TLS is enabled (if using reverse proxy)

## Troubleshooting

### Environment variables not loaded

```bash
# Check which env file is being used
docker-compose config

# Explicitly specify env file
docker-compose --env-file .env.production config
```

### Services can't connect

```bash
# Verify network configuration
docker network ls
docker network inspect zerodb_zerodb-network

# Check service DNS resolution
docker-compose exec zerodb-api ping postgres
```

### Permission errors

```bash
# Fix data directory permissions
sudo chown -R $(id -u):$(id -g) data/

# Reset and reinitialize
docker-compose down -v
docker-compose up -d
```

## Best Practices

1. **Never commit `.env.*` files** (except `.example` templates)
2. **Use secrets manager** for production (e.g., AWS Secrets Manager, HashiCorp Vault)
3. **Rotate secrets regularly** (every 90 days minimum)
4. **Test staging environment** before production deployment
5. **Monitor logs** for unauthorized access attempts
6. **Enable automated backups** in staging and production
7. **Use strong, unique passwords** for each environment
8. **Restrict network access** using firewalls in production

## References

- Environment templates: `.env.*.example`
- Docker Compose: `docker-compose.yml`
- Security guide: `docs/SECURITY.md`
- Backup guide: `docs/DATA_MANAGEMENT.md`
