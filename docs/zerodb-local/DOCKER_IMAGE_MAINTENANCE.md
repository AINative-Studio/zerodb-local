# ZeroDB Local - Docker Image Maintenance Guide

This guide documents the Docker images used in ZeroDB Local and how to maintain them.

## Current Docker Images

### Production Images

| Service | Image | Registry | Version |
|---------|-------|----------|---------|
| PostgreSQL | `pgvector/pgvector:pg16` | Docker Hub | Latest PG16 |
| Qdrant | `qdrant/qdrant:latest` | Docker Hub | Latest |
| RedPanda | `docker.redpanda.com/redpandadata/redpanda:latest` | RedPanda Official | Latest |

### Custom Images (Built from Dockerfiles)

| Service | Build Context | Dockerfile | Base Image |
|---------|---------------|------------|------------|
| Embeddings | `./embeddings` | `./embeddings/Dockerfile` | `python:3.11-slim` |
| API Server | `./api` | `./api/Dockerfile` | `python:3.11-slim` |
| Dashboard | `./dashboard` | `./dashboard/Dockerfile` | `node:20-alpine` |
| MinIO | `./vendor/minio` (git submodule) | `./vendor/minio/Dockerfile.ainative` | fork's own base |

## Image Update History

### MinIO: switched to AINative's own maintained fork, built locally (2026-11-23)

**Issue**: #83

**Change**:
- From: `image: ainative-studio/minio:local` -- a tag that was never actually publishable anywhere (no registry, no CI that built it); `docker compose up` always failed trying to pull it.
- To: `build: {context: ./vendor/minio, dockerfile: Dockerfile.ainative}`, where `vendor/minio` is a git submodule pointing at `AINative-Studio/minio` (a maintained fork of upstream MinIO), and `Dockerfile.ainative` is a new, from-source multi-stage Dockerfile added to that fork -- the fork's own existing `Dockerfile` and `Dockerfile.release` both turned out to be unusable too: `Dockerfile` does `FROM minio/minio:latest` (the same dead Docker Hub image), and `Dockerfile.release`'s build stage `curl`s pre-built binaries from `dl.min.io`, which now returns HTTP 410 Gone with an explicit "archived and no longer maintained" notice for every release. `Dockerfile.ainative` instead compiles the vendored Go source directly (`golang:1.24-alpine` → `go build` → `alpine:3.20` runtime), with no dependency on either dead service.

**Reason**: MinIO Inc. stopped distributing free Community Edition Docker images -- `minio/minio` and `minio/mc` were removed from Docker Hub on 2026-09-11 (CE itself was archived upstream on 2026-02-13, source-only since). AINative is maintaining its own fork going forward rather than depending on a now-dead upstream distribution channel.

**Impact**: `docker compose up` now builds MinIO from source on first run (slower than a pull, same as the `embeddings`/`zerodb-api`/`dashboard` services already do) instead of failing outright. Anyone cloning this repo needs `git submodule update --init` (or `git clone --recurse-submodules`) to populate `vendor/minio` before building.

**Verification**:
```bash
git submodule update --init vendor/minio
docker compose build minio
docker compose up -d minio
docker compose logs minio
curl -f http://localhost:9000/minio/health/live
```

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
- **AINative fork (what we actually build)**: https://github.com/AINative-Studio/minio -- vendored here as a git submodule at `vendor/minio`, built locally via `./vendor/minio/Dockerfile.ainative`. AINative maintains this fork going forward.
- **Upstream (reference only, no longer usable as an image source)**: https://github.com/minio/minio -- MinIO Inc. stopped shipping free Community Edition images; `minio/minio` and `minio/mc` were removed from Docker Hub 2026-09-11 (CE archived 2026-02-13). Upstream's own docs (https://min.io/docs/) are still a useful reference for MinIO's features/config, but its Docker Hub page/images are dead.

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
