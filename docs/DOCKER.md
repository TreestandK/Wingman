# Docker Deployment Guide

Wingman runs as a Docker container for easy deployment and portability.

## Quick Start

### Pull from GitHub Container Registry

```bash
docker pull ghcr.io/treestandk/wingman:latest
```

### Run Container

```bash
docker run -d \
  -p 5000:5000 \
  -e ADMIN_PASSWORD=YourSecurePassword \
  -e FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
  -e DOMAIN=yourdomain.com \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name wingman \
  --restart unless-stopped \
  ghcr.io/treestandk/wingman:latest
```

Access at: http://localhost:5000

## Environment Variables

### Required

```bash
# Session security (minimum 32 characters)
FLASK_SECRET_KEY=your-random-secret-key

# Default admin password
ADMIN_PASSWORD=YourSecurePassword
```

### Optional

```bash
# Domain for DNS/SSL (no protocol, no trailing slash)
DOMAIN=yourdomain.com

# Authentication (default: true)
ENABLE_AUTH=true

# Session cookie security (set true when using HTTPS)
SESSION_COOKIE_SECURE=false

# SAML authentication (default: false)
ENABLE_SAML=false
```

## Volumes

Mount these volumes to persist data:

```bash
-v /path/to/data:/app/data      # User data, deployments, config
-v /path/to/logs:/app/logs      # Application logs
-v /path/to/templates:/app/templates/saved  # Deployment templates
```

**Important:** Without volumes, all data is lost when container is removed!

## Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  wingman:
    image: ghcr.io/treestandk/wingman:latest
    container_name: wingman
    ports:
      - "5000:5000"
    environment:
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - DOMAIN=${DOMAIN}
      - ENABLE_AUTH=true
      - SESSION_COOKIE_SECURE=false
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./templates:/app/templates/saved
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Create `.env` file:

```bash
FLASK_SECRET_KEY=your-random-32-character-secret-key
ADMIN_PASSWORD=YourSecurePassword
DOMAIN=yourdomain.com
```

Start:
```bash
docker-compose up -d
```

Stop:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f wingman
```

## Building from Source

### Clone Repository

```bash
git clone https://github.com/treestandk/wingman.git
cd wingman
```

### Build Image

```bash
docker build -t wingman:local .
```

### Build Without Cache (if issues)

```bash
docker build --no-cache -t wingman:local .
```

### Run Local Build

```bash
docker run -d -p 5000:5000 \
  -e ADMIN_PASSWORD=YourPassword \
  -e FLASK_SECRET_KEY=your-secret-key \
  --name wingman \
  wingman:local
```

## Container Management

### View Logs

```bash
# All logs
docker logs wingman

# Follow logs (real-time)
docker logs -f wingman

# Last 50 lines
docker logs --tail 50 wingman

# Search logs
docker logs wingman 2>&1 | grep "ERROR"
```

### Restart Container

```bash
docker restart wingman
```

### Stop Container

```bash
docker stop wingman
```

### Remove Container

```bash
docker stop wingman
docker rm wingman
```

### Execute Commands

```bash
# Access shell
docker exec -it wingman /bin/bash

# Create admin user
docker exec -it wingman python create_admin.py

# Check Python version
docker exec wingman python --version

# View config
docker exec wingman cat /app/data/config.json
```

## Networking

### Port Mapping

Default port: 5000

Change to different port:
```bash
-p 8080:5000  # Access via localhost:8080
```

### Docker Network

Create custom network:
```bash
docker network create wingman-net

docker run -d \
  --network wingman-net \
  --name wingman \
  ghcr.io/treestandk/wingman:latest
```

### Connecting to Other Containers

If NPM or other services are in containers:

```yaml
services:
  wingman:
    networks:
      - shared-network
  nginx-proxy-manager:
    networks:
      - shared-network

networks:
  shared-network:
    external: true
```

## Security

### Production Setup

1. **Generate Strong Secret Key:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

2. **Use Environment File:**
Don't expose secrets in docker run command. Use `.env` file or Docker secrets.

3. **Enable HTTPS:**
```bash
-e SESSION_COOKIE_SECURE=true
```

4. **Limit Port Exposure:**
```bash
-p 127.0.0.1:5000:5000  # Only localhost
```

5. **Use Reverse Proxy:**
Don't expose Flask directly. Use Nginx/Caddy/Traefik.

### Docker Secrets (Swarm)

```bash
echo "your-secret-key" | docker secret create flask_secret_key -

docker service create \
  --name wingman \
  --secret flask_secret_key \
  --publish 5000:5000 \
  ghcr.io/treestandk/wingman:latest
```

## Health Check

Wingman includes a health check endpoint:

```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-22T12:34:56.789012"
}
```

Docker health status:
```bash
docker inspect --format='{{.State.Health.Status}}' wingman
```

## Updates

### Pull Latest Image

```bash
docker pull ghcr.io/treestandk/wingman:latest
```

### Update Running Container

```bash
# Stop old container
docker stop wingman
docker rm wingman

# Pull latest
docker pull ghcr.io/treestandk/wingman:latest

# Start new container (use same volumes!)
docker run -d -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name wingman \
  ghcr.io/treestandk/wingman:latest
```

### Update with Docker Compose

```bash
docker-compose pull
docker-compose up -d
```

## Backup

### Backup Data

```bash
# Backup volumes
docker run --rm \
  -v wingman_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/wingman-backup.tar.gz /data

# Or simply copy
cp -r ./data ./data-backup-$(date +%Y%m%d)
```

### Restore Data

```bash
# Extract backup
tar xzf wingman-backup.tar.gz -C ./data

# Or copy
cp -r ./data-backup-20260122 ./data
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs wingman

# Check if port is in use
sudo netstat -tlnp | grep 5000

# Try different port
docker run -p 5001:5000 ...
```

### Connection Refused

```bash
# Verify container is running
docker ps | grep wingman

# Check port mapping
docker port wingman

# Test from inside container
docker exec wingman curl -f http://localhost:5000/health
```

### Permission Denied on Volumes

```bash
# Fix permissions
sudo chown -R 1000:1000 ./data ./logs

# Or use named volumes instead of bind mounts
docker volume create wingman_data
docker volume create wingman_logs

docker run -d \
  -v wingman_data:/app/data \
  -v wingman_logs:/app/logs \
  ...
```

### ModuleNotFoundError

Image wasn't built with latest code:
```bash
docker pull ghcr.io/treestandk/wingman:latest
# Or rebuild from source
docker build --no-cache -t wingman:local .
```

### Auth Not Working

Check environment variables:
```bash
docker exec wingman env | grep ENABLE_AUTH
```

Rebuild and restart:
```bash
docker stop wingman
docker rm wingman
docker run ...
```

## Performance

### Resource Limits

Limit CPU and memory:
```bash
docker run -d \
  --cpus="2" \
  --memory="2g" \
  --name wingman \
  ghcr.io/treestandk/wingman:latest
```

### Docker Compose Limits

```yaml
services:
  wingman:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Monitor Resources

```bash
docker stats wingman
```

## Multi-Platform

Wingman supports multiple architectures:

```bash
# Specific platform
docker pull --platform linux/amd64 ghcr.io/treestandk/wingman:latest
docker pull --platform linux/arm64 ghcr.io/treestandk/wingman:latest
```

## Development

### Run in Development Mode

```bash
docker run -d \
  -p 5000:5000 \
  -e ENABLE_AUTH=false \
  -v $(pwd):/app \
  --name wingman-dev \
  wingman:local
```

### Hot Reload (not recommended in container)

Better to develop locally with Python virtual environment.
