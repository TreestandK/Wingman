# Building Wingman Docker Image

Quick guide to building and testing the Wingman Docker image locally.

## Quick Build

```bash
# Simple build (single architecture)
docker build -t wingman:latest .

# View the image
docker images wingman
```

## Test Locally

```bash
# Run the container
docker run -d \
  -p 5000:5000 \
  -e DOMAIN=test.com \
  -e CF_API_TOKEN=test \
  -e CF_ZONE_ID=test \
  --name wingman-test \
  wingman:latest

# Check if it's running
docker ps | grep wingman

# View logs
docker logs -f wingman-test

# Test the health endpoint
curl http://localhost:5000/health

# Access the web interface
# Open browser: http://localhost:5000
```

## Clean Up Test

```bash
# Stop and remove container
docker stop wingman-test
docker rm wingman-test
```

## Build for Multiple Architectures (Advanced)

For production deployments supporting both Intel and ARM:

```bash
# Create buildx builder
docker buildx create --name multiarch --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-registry/wingman:latest \
  --push .
```

## Common Build Issues

### Issue: "COPY static/ /app/static/ 2>/dev/null || true" fails

**Error:**
```
ERROR: failed to calculate checksum of ref: "/||": not found
```

**Solution:**
The Dockerfile has been fixed. The `2>/dev/null || true` syntax doesn't work in Docker COPY commands. Simply use:
```dockerfile
COPY static/ /app/static/
```

### Issue: Build cache causing problems

**Solution:**
```bash
# Build without cache
docker build --no-cache -t wingman:latest .

# Clear build cache
docker builder prune -a
```

### Issue: Image too large

**Solution:**
The current image is ~167MB which is reasonable. To reduce further:

1. Use multi-stage build
2. Remove unnecessary dependencies
3. Use alpine base (requires compilation of some packages)

## Testing with Docker Compose

The easiest way to test:

```bash
# Copy environment template
cp .env.example .env

# Edit with your test credentials
nano .env

# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Access
# http://localhost:5000

# Stop
docker-compose down
```

## Build Verification

After building, verify the image:

```bash
# Check image size
docker images wingman:latest

# Inspect image
docker inspect wingman:latest

# Test container can start
docker run --rm wingman:latest python -c "import app; print('OK')"

# Check installed packages
docker run --rm wingman:latest pip list
```

## Next Steps

After successful local build:

1. **Tag for registry:**
   ```bash
   docker tag wingman:latest ghcr.io/your-username/wingman:latest
   ```

2. **Push to registry:**
   ```bash
   docker push ghcr.io/your-username/wingman:latest
   ```

3. **Deploy to TrueNAS:**
   - Update `truenas/install.yaml` with your image name
   - Follow [TRUENAS-INSTALL.md](TRUENAS-INSTALL.md)

## Troubleshooting

### Container won't start

```bash
# Check logs immediately
docker logs wingman-test

# Run interactively to see errors
docker run -it --rm wingman:latest /bin/bash
```

### Health check failing

```bash
# Check if Flask is running
docker exec wingman-test ps aux | grep python

# Check if port is listening
docker exec wingman-test netstat -tlnp | grep 5000

# Manual health check
docker exec wingman-test curl localhost:5000/health
```

### Permission issues

The container runs as root by default. If you need non-root:

```dockerfile
# Add to Dockerfile
RUN useradd -m -u 1000 wingman && \
    chown -R wingman:wingman /app
USER wingman
```

## Build Time Optimizations

### Layer Caching

The Dockerfile is optimized for layer caching:

1. System dependencies first (changes rarely)
2. requirements.txt (changes occasionally)
3. Application code (changes frequently)

### Parallel Builds

If building locally for multiple architectures:

```bash
# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -t wingman:latest .

# Or with buildx
docker buildx build --load -t wingman:latest .
```

## Production Build

For production, use the GitHub Actions workflow:

1. Push code to GitHub
2. Workflow automatically builds on every push
3. Tags with version numbers
4. Builds for amd64 + arm64
5. Pushes to GitHub Container Registry

See [.github/workflows/build-and-push.yml](.github/workflows/build-and-push.yml)

---

## Quick Reference

```bash
# Build
docker build -t wingman:latest .

# Test run
docker run -d -p 5000:5000 --name wingman-test wingman:latest

# Check logs
docker logs -f wingman-test

# Test endpoint
curl http://localhost:5000/health

# Stop
docker stop wingman-test && docker rm wingman-test

# Push to registry
docker tag wingman:latest ghcr.io/USERNAME/wingman:latest
docker push ghcr.io/USERNAME/wingman:latest
```
