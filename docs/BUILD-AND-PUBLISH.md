# Building and Publishing Wingman Docker Image

This guide covers building and publishing the Wingman Docker image for use with TrueNAS SCALE.

## Prerequisites

- Docker installed
- GitHub account (for GitHub Container Registry)
- Docker Hub account (optional alternative)

## Quick Start

Before pushing to a registry, test your build locally:

```bash
# Build the image
docker build -t wingman:latest .

# Test it works
docker run -d -p 5000:5000 --name wingman-test wingman:latest
curl http://localhost:5000/health

# Clean up
docker stop wingman-test && docker rm wingman-test
```

**📖 See [BUILDING.md](BUILDING.md) for detailed local build and testing guide**

---

## Method 1: GitHub Container Registry (Recommended)

### Setup

1. **Create a GitHub repository** for Wingman
2. **Enable GitHub Actions** in repository settings
3. **Configure secrets** (if needed for private registries)

### Automatic Build

The included GitHub Actions workflow will automatically build and push images:

```yaml
# .github/workflows/build-and-push.yml is already configured
```

**Triggers:**
- Push to `main` branch → builds `latest` tag
- Push version tags (`v*`) → builds version-specific tags
- Manual workflow dispatch → build on demand

**What it does:**
- Builds for `linux/amd64` and `linux/arm64`
- Pushes to `ghcr.io/YOUR-USERNAME/wingman:latest`
- Creates version tags automatically
- Caches builds for faster rebuilds

### Manual Build and Push

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR-USERNAME --password-stdin

# Build the image
docker build -t ghcr.io/YOUR-USERNAME/wingman:latest .

# Build for multiple architectures (optional)
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/YOUR-USERNAME/wingman:latest \
  --push .

# Push to registry
docker push ghcr.io/YOUR-USERNAME/wingman:latest
```

### Make Image Public

1. Go to `https://github.com/YOUR-USERNAME?tab=packages`
2. Find the `wingman` package
3. Click **Package settings**
4. Scroll to **Danger Zone**
5. Click **Change visibility** → **Public**

## Method 2: Docker Hub

### Build and Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Build the image
docker build -t YOUR-DOCKERHUB-USERNAME/wingman:latest .

# Tag with version
docker tag YOUR-DOCKERHUB-USERNAME/wingman:latest YOUR-DOCKERHUB-USERNAME/wingman:2.0.0

# Push to Docker Hub
docker push YOUR-DOCKERHUB-USERNAME/wingman:latest
docker push YOUR-DOCKERHUB-USERNAME/wingman:2.0.0
```

### Update TrueNAS Configuration

Edit your TrueNAS deployment files to use Docker Hub:

```yaml
# In truenas/install.yaml
image: YOUR-DOCKERHUB-USERNAME/wingman:latest

# In truenas/charts/values.yaml
image:
  repository: YOUR-DOCKERHUB-USERNAME/wingman
  tag: latest
```

## Method 3: Local Build for TrueNAS

### Build Locally

```bash
# Build the image
docker build -t wingman:latest .

# Save to file
docker save wingman:latest | gzip > wingman-latest.tar.gz

# Copy to TrueNAS
scp wingman-latest.tar.gz root@truenas-ip:/tmp/

# SSH to TrueNAS and load
ssh root@truenas-ip
k3s ctr images import /tmp/wingman-latest.tar.gz
```

### Deploy with Local Image

```yaml
# In truenas/install.yaml, change:
image: wingman:latest
imagePullPolicy: Never  # Don't try to pull from registry
```

## Automated Updates

### GitHub Actions Setup (Recommended)

1. **Push code to GitHub:**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Create a release tag:**
```bash
git tag v2.0.0
git push origin v2.0.0
```

3. **GitHub Actions will automatically:**
   - Build the Docker image
   - Push to `ghcr.io/YOUR-USERNAME/wingman:latest`
   - Push to `ghcr.io/YOUR-USERNAME/wingman:2.0.0`
   - Build for multiple architectures

4. **TrueNAS will auto-update** (if configured with `imagePullPolicy: Always`)

### Webhook-based Updates

Add a webhook to trigger TrueNAS updates:

```bash
# Create a simple update webhook on TrueNAS
cat > /root/update-wingman-webhook.sh << 'EOF'
#!/bin/bash
kubectl rollout restart deployment/wingman -n wingman
EOF

chmod +x /root/update-wingman-webhook.sh

# Call this webhook after GitHub Actions completes
# Add to GitHub Actions workflow:
# - name: Trigger TrueNAS Update
#   run: |
#     curl -X POST https://your-truenas-ip/webhook/update-wingman
```

## Version Management

### Semantic Versioning

Use semantic versioning for releases:

```bash
# Major version (breaking changes)
git tag v3.0.0

# Minor version (new features)
git tag v2.1.0

# Patch version (bug fixes)
git tag v2.0.1

# Push all tags
git push origin --tags
```

### Tag Strategy

The GitHub Actions workflow automatically creates:

- `latest` - Always points to the latest build from main
- `v2.0.0` - Specific version tag
- `v2.0` - Minor version tag
- `v2` - Major version tag
- `main` - Latest main branch build

### Using Specific Versions in TrueNAS

```yaml
# In truenas/install.yaml or values.yaml

# Use latest (auto-updates)
image: ghcr.io/YOUR-USERNAME/wingman:latest

# Pin to specific version (no auto-updates)
image: ghcr.io/YOUR-USERNAME/wingman:v2.0.0

# Use major version (gets minor updates)
image: ghcr.io/YOUR-USERNAME/wingman:v2
```

## Customization

### Custom Build with Environment Variables

```dockerfile
# Create custom Dockerfile
FROM ghcr.io/YOUR-USERNAME/wingman:latest

# Add custom configurations
ENV CUSTOM_SETTING=value
COPY custom-config.json /app/config/

# Build custom image
docker build -f Dockerfile.custom -t wingman:custom .
```

### Multi-stage Build for Smaller Images

The Dockerfile is already optimized, but you can further reduce size:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
WORKDIR /app
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app.py"]
```

## Testing Before Deployment

### Test Locally

```bash
# Build the image
docker build -t wingman:test .

# Run locally
docker run -d \
  -p 5000:5000 \
  -e DOMAIN=test.com \
  -e CF_API_TOKEN=test \
  --name wingman-test \
  wingman:test

# Test the interface
curl http://localhost:5000/health

# View logs
docker logs -f wingman-test

# Clean up
docker stop wingman-test
docker rm wingman-test
```

### Test with Docker Compose

```bash
# Use the docker-compose.yml
cp .env.example .env
# Edit .env with test credentials

docker-compose up -d
docker-compose logs -f

# Test
curl http://localhost:5000/health

# Clean up
docker-compose down
```

## Registry Authentication

### GitHub Container Registry

```bash
# Create a Personal Access Token (PAT) with read:packages scope
# At: https://github.com/settings/tokens

# Login
echo YOUR_PAT | docker login ghcr.io -u YOUR-USERNAME --password-stdin
```

### Configure TrueNAS to Pull Private Images

```yaml
# Add image pull secret
apiVersion: v1
kind: Secret
metadata:
  name: ghcr-secret
  namespace: wingman
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: BASE64_ENCODED_DOCKER_CONFIG

---
# In deployment.yaml, add:
spec:
  template:
    spec:
      imagePullSecrets:
      - name: ghcr-secret
```

## Troubleshooting

### Build Fails

```bash
# Clear Docker cache
docker builder prune -a

# Build with no cache
docker build --no-cache -t wingman:latest .

# Check build context size
docker build --progress=plain -t wingman:latest . 2>&1 | grep "context"
```

### Image Too Large

```bash
# Check image size
docker images wingman

# Analyze layers
docker history wingman:latest

# Use dive to inspect
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive:latest wingman:latest
```

### Pull Fails on TrueNAS

```bash
# Check if image is accessible
docker pull ghcr.io/YOUR-USERNAME/wingman:latest

# Check TrueNAS can reach registry
kubectl run test --image=ghcr.io/YOUR-USERNAME/wingman:latest --dry-run=client -o yaml

# Verify image pull policy
kubectl get deployment wingman -n wingman -o yaml | grep -A5 imagePullPolicy
```

## Best Practices

1. **Always tag images** with version numbers
2. **Use multi-arch builds** for compatibility
3. **Keep images small** by using slim base images
4. **Scan for vulnerabilities** before pushing
5. **Test locally** before deploying to TrueNAS
6. **Use semantic versioning** for releases
7. **Keep secrets out** of Docker images
8. **Document changes** in commit messages

## Next Steps

After building and pushing your image:

1. Update `truenas/install.yaml` with your image name
2. Update `truenas/charts/values.yaml` with your image repository
3. Deploy to TrueNAS using [TRUENAS-INSTALL.md](TRUENAS-INSTALL.md)
4. Set up automatic updates with the cron script
5. Configure GitHub Actions for continuous deployment

---

**Quick Commands Reference:**

```bash
# Build
docker build -t ghcr.io/YOUR-USERNAME/wingman:latest .

# Push
docker push ghcr.io/YOUR-USERNAME/wingman:latest

# Deploy to TrueNAS
kubectl set image deployment/wingman wingman=ghcr.io/YOUR-USERNAME/wingman:latest -n wingman

# Rollback
kubectl rollout undo deployment/wingman -n wingman

# Check status
kubectl rollout status deployment/wingman -n wingman
```
