# ZeroDB Local - Docker Image Maintenance Guide

This guide documents the Docker images used in ZeroDB Local and how to maintain them.

## Current Docker Images

### Production Images

| Service | Image | Registry | Version |
|---------|-------|----------|---------|
| PostgreSQL | `pgvector/pgvector:pg16` | Docker Hub | Latest PG16 |
| Qdrant | `qdrant/qdrant:latest` | Docker Hub | Latest |
| MinIO | `minio/minio:latest` | Docker Hub | Latest |
| RedPanda | `docker.redpanda.com/redpandadata/redpanda:latest` | RedPanda Official | Latest |

### Custom Images (Built from Dockerfiles)

| Service | Build Context | Dockerfile | Base Image |
|---------|---------------|------------|------------|
| Embeddings | `./embeddings` | `./embeddings/Dockerfile` | `python:3.11-slim` |
| API Server | `./api` | `./api/Dockerfile` | `python:3.11-slim` |
| Dashboard | `./dashboard` | `./dashboard/Dockerfile` | `node:20-alpine` |

## Image Update History

### RedPanda Migration (2026-02-10)

**Issue**: #1125

**Change**:
- From: `vectorized/redpanda:latest`
- To: `docker.redpanda.com/redpandadata/redpanda:latest`

**Reason**: RedPanda moved their official Docker images from the `vectorized` namespace to their own registry at `docker.redpanda.com`.

**Impact**: All deployments needed to update the image name. The old registry no longer serves images.

**Verification**:
```bash
python3 scripts/test_redpanda_image.py
```

## Image Update Procedure

### For Official Images (e.g., PostgreSQL, Qdrant, MinIO, RedPanda)

1. **Check for updates**:
   ```bash
   docker pull <image-name>:latest
   ```

2. **Test locally**:
   ```bash
   cd zerodb-local
   docker-compose down
   docker-compose up -d <service-name>
   docker-compose logs <service-name>
   ```

3. **Verify health**:
   ```bash
   docker ps | grep zerodb-<service-name>
   docker inspect zerodb-<service-name> --format='{{.State.Health.Status}}'
   ```

4. **Run integration tests**:
   ```bash
   cd api
   pytest tests/ -v
   ```

5. **Update documentation** if image source or registry changes

### For Custom Images (Embeddings, API, Dashboard)

1. **Update Dockerfile** as needed

2. **Rebuild image**:
   ```bash
   cd zerodb-local
   docker-compose build <service-name>
   ```

3. **Test locally**:
   ```bash
   docker-compose up -d <service-name>
   docker-compose logs <service-name>
   ```

4. **Run service-specific tests**

## Monitoring Image Deprecations

### RedPanda
- **Official Docs**: https://docs.redpanda.com/
- **Docker Registry**: https://hub.docker.com/r/redpandadata/redpanda
- **New Registry**: https://docker.redpanda.com/

### PostgreSQL + pgvector
- **pgvector Repo**: https://github.com/pgvector/pgvector
- **Docker Hub**: https://hub.docker.com/r/pgvector/pgvector

### Qdrant
- **Official Docs**: https://qdrant.tech/
- **Docker Hub**: https://hub.docker.com/r/qdrant/qdrant

### MinIO
- **Official Docs**: https://min.io/docs/
- **Docker Hub**: https://hub.docker.com/r/minio/minio

## Automated Testing

### Test Script for RedPanda

Run the automated test to verify RedPanda configuration:
```bash
python3 scripts/test_redpanda_image.py
```

This script verifies:
- Correct image name in docker-compose.yml
- Image pulls successfully
- Container starts and becomes healthy
- No obsolete image references

### Adding Tests for Other Services

To create similar tests for other services, use the RedPanda test as a template:
```python
# Example structure
class ServiceImageTester:
    CORRECT_IMAGE = "registry/image:tag"

    def test_compose_file_image(self):
        # Verify docker-compose.yml
        pass

    def test_image_pull(self):
        # Test docker pull
        pass

    def test_container_start(self):
        # Test startup and health
        pass
```

## Troubleshooting

### Image Pull Errors

If you see "repository does not exist" errors:

1. **Verify the registry**:
   ```bash
   grep "image:" docker-compose.yml | grep <service-name>
   ```

2. **Check Docker Hub or official docs** for the correct registry

3. **Update docker-compose.yml** if registry has changed

4. **Pull manually to test**:
   ```bash
   docker pull <correct-image-name>
   ```

### Old Images Taking Up Space

Clean up old images:
```bash
# Remove unused images
docker image prune -a

# Remove specific old image
docker rmi vectorized/redpanda:latest
```

### Container Won't Start After Image Update

1. **Check logs**:
   ```bash
   docker-compose logs <service-name>
   ```

2. **Verify configuration compatibility** with new image version

3. **Check volume mounts** - some images change data directory locations

4. **Rollback if needed**:
   ```bash
   # Update docker-compose.yml back to old image
   docker-compose up -d <service-name>
   ```

## Best Practices

1. **Pin versions in production**:
   - Use specific tags instead of `:latest`
   - Example: `postgres:16.1` instead of `postgres:latest`

2. **Test updates locally first**:
   - Never update production images without local testing
   - Run full test suite after updates

3. **Document registry changes**:
   - If an image moves registries, document it here
   - Create verification tests
   - Update all references

4. **Monitor deprecation notices**:
   - Subscribe to official project announcements
   - Check Docker Hub for deprecation warnings
   - Review release notes regularly

5. **Maintain compatibility**:
   - Test data migration when updating database images
   - Verify API compatibility when updating service images
   - Check for breaking changes in release notes

## Version Pinning Strategy

### Development (Current)
Uses `:latest` tags for easier updates and testing

### Staging (Recommended)
Pin to specific minor versions:
```yaml
postgres: pgvector/pgvector:pg16.1
qdrant: qdrant/qdrant:v1.7.4
redpanda: docker.redpanda.com/redpandadata/redpanda:v23.3.5
```

### Production (Recommended)
Pin to specific patch versions:
```yaml
postgres: pgvector/pgvector:pg16.1.0
qdrant: qdrant/qdrant:v1.7.4
redpanda: docker.redpanda.com/redpandadata/redpanda:v23.3.5
```

## Related Documentation

- [ZeroDB Local README](/Users/aideveloper/core/zerodb-local/README.md)
- [RedPanda Image Fix Verification](/Users/aideveloper/core/docs/infrastructure/REDPANDA_IMAGE_FIX_VERIFICATION.md)
- [Docker Compose Validation](/Users/aideveloper/core/docs/deployment/DOCKER_COMPOSE_VALIDATION.md)

## Maintenance Schedule

- **Weekly**: Check for security updates
- **Monthly**: Review release notes for all images
- **Quarterly**: Test minor version updates
- **Annually**: Review and update this guide

Refs #1125
