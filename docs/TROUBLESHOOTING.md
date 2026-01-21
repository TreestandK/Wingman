# Wingman Troubleshooting Guide

Common issues and solutions for Wingman Game Server Manager.

---

## Configuration Issues

### "undefined" Error When Validating Configuration

**Symptom:** When clicking "Validate Configuration" or "Test All APIs", you see "undefined" in the status display.

**Cause:** The frontend JavaScript was sending an empty configuration object instead of the actual configuration.

**Solution:** This has been fixed in the latest version. The validation functions now:
1. Load the current configuration from `/api/config`
2. Send the actual configuration to the validation endpoint
3. Display detailed error messages with proper error handling

**How to verify the fix:**
1. Open browser Developer Tools (F12)
2. Go to the Console tab
3. Click "Validate Configuration"
4. You should see logs like:
   ```
   Loaded config: {success: true, config: {...}}
   Validation result: {success: false, errors: [...], warnings: [...]}
   ```

### Configuration Not Saving

**Symptom:** Changes to configuration in the UI don't persist after page reload.

**Possible Causes:**
1. Directory permissions issue
2. Container volume not mounted correctly
3. Backend error during save

**Solution:**

**For Docker Compose:**
```bash
# Check if volumes are mounted
docker-compose ps
docker inspect wingman-gameserver-manager | grep Mounts -A 20

# Check container logs
docker-compose logs wingman

# Ensure data directory exists and is writable
docker-compose exec wingman ls -la /app/data
```

**For TrueNAS:**
```bash
# Check PVC status
kubectl get pvc -n wingman

# Check pod logs
kubectl logs -n wingman deployment/wingman

# Exec into pod and check permissions
kubectl exec -it -n wingman deployment/wingman -- ls -la /app/data
```

**Manual Fix:**
```bash
# Create config directory with correct permissions
mkdir -p /app/data
chmod 777 /app/data  # For testing; use more restrictive in production
```

### "Failed to load configuration" Error

**Symptom:** Error message when accessing Settings tab or validating config.

**Debugging Steps:**

1. **Check browser console (F12 → Console tab):**
   ```javascript
   // Look for errors like:
   Failed to load config: HTTP 500
   ```

2. **Check backend logs:**
   ```bash
   # Docker Compose
   docker-compose logs wingman | grep -i error

   # TrueNAS
   kubectl logs -n wingman deployment/wingman | grep -i error
   ```

3. **Test the API directly:**
   ```bash
   # From inside container
   curl http://localhost:5000/api/config

   # From host (Docker Compose)
   curl http://localhost:5000/api/config

   # From host (TrueNAS)
   curl http://<truenas-ip>:30500/api/config
   ```

**Common Solutions:**
- Restart the container/pod
- Check file permissions on `/app/data`
- Verify environment variables are set correctly

---

## API Connectivity Issues

### Cloudflare Test Failing

**Symptoms:**
- Cloudflare shows "Failed" in API tests
- DNS records not being created

**Debugging:**

1. **Verify API token:**
   ```bash
   # Test token directly
   curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
     -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json"
   ```

2. **Check token permissions:**
   - Token needs `Zone.DNS` edit permissions
   - Verify Zone ID matches your domain

3. **Common issues:**
   - Token expired
   - Wrong Zone ID
   - Insufficient permissions
   - Network firewall blocking api.cloudflare.com

### Nginx Proxy Manager Test Failing

**Symptoms:**
- NPM shows "Failed" in API tests
- Proxy hosts not being created

**Debugging:**

1. **Verify NPM is accessible:**
   ```bash
   # Test from Wingman container
   docker-compose exec wingman curl http://nginx-proxy-manager:81/api

   # Should return 401 or 404, not connection refused
   ```

2. **Check NPM configuration:**
   - API URL should be internal Docker network address
   - Example: `http://nginx-proxy-manager:81/api`
   - NOT: `http://192.168.1.100:81/api` (unless external)

3. **Verify credentials:**
   - Default NPM admin: `admin@example.com` / `changeme`
   - Change after first login!

4. **Common issues:**
   - NPM not on same Docker network
   - Incorrect API URL format
   - Wrong credentials

### UniFi Controller Test Failing

**Symptoms:**
- UniFi shows "Failed" in API tests
- Port forwards not being created

**Debugging:**

1. **Verify controller accessibility:**
   ```bash
   # Test connection (expects SSL error or login page)
   curl -k https://unifi-controller:8443
   ```

2. **Check UniFi configuration:**
   - UDM users: Set `is_udm` to `true`
   - Non-UDM: Set `is_udm` to `false`
   - Site name usually `default`

3. **Common issues:**
   - Self-signed certificate (use `-k` flag or set verify=False)
   - Wrong site name
   - Account doesn't have admin permissions
   - UDM vs non-UDM setting incorrect

### Pterodactyl Test Failing

**Symptoms:**
- Pterodactyl shows "Failed" in API tests
- Cannot list nests/eggs

**Debugging:**

1. **Verify panel is accessible:**
   ```bash
   curl https://panel.yourdomain.com/api/application/nodes \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Accept: Application/vnd.pterodactyl.v1+json"
   ```

2. **Check API key:**
   - Must be an **Application API** key, not Client API
   - Created in panel: Admin → Application API → Create New

3. **Common issues:**
   - Using Client API key instead of Application API key
   - API key doesn't have required permissions
   - URL doesn't include `https://`
   - Panel has IP whitelist enabled

---

## Browser Console Debugging

### Enable Detailed Logging

1. **Open Browser Developer Tools:**
   - Chrome/Edge: F12 or Ctrl+Shift+I
   - Firefox: F12 or Ctrl+Shift+I
   - Safari: Cmd+Option+I (enable Developer menu first)

2. **Check Console tab for errors:**
   - Red messages indicate errors
   - Look for failed network requests
   - Check JavaScript errors

3. **Check Network tab:**
   - See all API requests and responses
   - Look for red (failed) requests
   - Click request to see details
   - Check Response tab for error messages

### Common Console Errors

**Error: `Failed to fetch`**
- Backend not running
- CORS issue
- Network connectivity problem

**Error: `JSON.parse: unexpected character`**
- Backend returning HTML instead of JSON
- Usually means backend error/crash
- Check backend logs

**Error: `Cannot read property 'config' of undefined`**
- API response missing expected data
- Backend returned error but frontend expected success
- Check Network tab for actual response

---

## Backend Logging

### View Logs

**Docker Compose:**
```bash
# View all logs
docker-compose logs wingman

# Follow logs in real-time
docker-compose logs -f wingman

# Last 100 lines
docker-compose logs --tail=100 wingman

# Search for errors
docker-compose logs wingman | grep -i error
```

**TrueNAS SCALE:**
```bash
# View logs
kubectl logs -n wingman deployment/wingman

# Follow logs
kubectl logs -f -n wingman deployment/wingman

# Previous crashed container
kubectl logs -n wingman deployment/wingman --previous
```

### Enable Debug Logging

Add to environment variables:

**Docker Compose** (`docker-compose.yml`):
```yaml
environment:
  - FLASK_DEBUG=true
  - LOG_LEVEL=DEBUG
```

**TrueNAS** (via GUI or `install.yaml`):
```yaml
env:
  - name: FLASK_DEBUG
    value: "true"
  - name: LOG_LEVEL
    value: "DEBUG"
```

### Log File Locations

- Application logs: `/app/logs/wingman.log`
- Deployment logs: `/app/logs/<deployment_id>.log`

**Access logs:**
```bash
# Docker Compose
docker-compose exec wingman cat /app/logs/wingman.log

# TrueNAS
kubectl exec -n wingman deployment/wingman -- cat /app/logs/wingman.log
```

---

## Common Error Messages

### "Domain is not configured"

**Fix:** Set `DOMAIN` environment variable or configure in UI Settings tab.

### "Cloudflare is enabled but API token is not configured"

**Fix:** Either:
1. Disable Cloudflare in Settings (uncheck "Enable Cloudflare")
2. Add API token in Settings

### "Validation failed: undefined"

**Fix:** Update to latest version. This has been fixed with improved error handling.

### "Missing nest_id or egg_data"

**Occurs when:** Uploading Pterodactyl egg

**Fix:**
1. Ensure you selected a JSON file
2. Verify Nest ID is entered (numeric)
3. Check browser console for JSON parse errors

---

## Performance Issues

### Web UI Loading Slowly

**Possible causes:**
1. Container CPU/memory limits too low
2. Large number of deployments
3. Network latency to external APIs

**Solutions:**
```yaml
# Increase container resources (docker-compose.yml)
services:
  wingman:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2'
        requests:
          memory: 512M
          cpus: '1'
```

### API Timeout Errors

**Symptoms:** Requests taking 30+ seconds or timing out

**Solutions:**
1. Check external API connectivity
2. Increase timeout values in code
3. Check network between container and external services

---

## Container Won't Start

### Check Status

**Docker Compose:**
```bash
docker-compose ps
docker-compose logs wingman
```

**TrueNAS:**
```bash
kubectl get pods -n wingman
kubectl describe pod -n wingman <pod-name>
```

### Common Issues

**Port already in use:**
```bash
# Find what's using port 5000
sudo netstat -tulpn | grep 5000

# Change port in docker-compose.yml
ports:
  - "5001:5000"  # Use 5001 instead
```

**Volume mount issues:**
```bash
# Check volume status
docker volume ls
docker volume inspect wingman_wingman-data

# Remove and recreate volumes (WARNING: loses data)
docker-compose down -v
docker-compose up -d
```

**Image not found:**
```bash
# Build image locally
docker-compose build

# Or pull from registry
docker pull ghcr.io/your-repo/wingman:latest
```

---

## Database/Storage Issues

### Configuration Not Persisting

**Check volume mounts:**
```bash
# Docker
docker inspect wingman-gameserver-manager | grep -A 10 Mounts

# Should show:
# "Destination": "/app/data"
# "Destination": "/app/logs"
# "Destination": "/app/templates/saved"
```

**Verify files exist:**
```bash
docker-compose exec wingman ls -la /app/data/
# Should show config.json, deployments.json
```

---

## Network Issues

### Container Can't Reach External APIs

**Symptoms:**
- All API tests fail
- Deployments timeout
- "Connection refused" errors

**Debugging:**
```bash
# Test from inside container
docker-compose exec wingman ping google.com
docker-compose exec wingman curl https://api.cloudflare.com
docker-compose exec wingman curl http://nginx-proxy-manager:81
```

**Solutions:**
1. Check Docker network configuration
2. Verify firewall rules
3. Check DNS resolution
4. Ensure services are on correct network

---

## Getting Help

If you're still experiencing issues:

1. **Gather information:**
   - Wingman version
   - Docker/TrueNAS version
   - Full error message
   - Browser console output
   - Backend logs
   - Steps to reproduce

2. **Check existing issues:**
   - [GitHub Issues](https://github.com/your-repo/wingman/issues)

3. **Create new issue:**
   - Include all gathered information
   - Use issue template if available
   - Be specific about what you expected vs what happened

---

## Useful Commands Reference

### Docker Compose
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart wingman

# Rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f wingman

# Execute command in container
docker-compose exec wingman <command>

# Shell access
docker-compose exec wingman /bin/bash
```

### TrueNAS SCALE / Kubernetes
```bash
# Get pods
kubectl get pods -n wingman

# Describe pod
kubectl describe pod -n wingman <pod-name>

# View logs
kubectl logs -n wingman deployment/wingman

# Execute command
kubectl exec -n wingman deployment/wingman -- <command>

# Shell access
kubectl exec -it -n wingman deployment/wingman -- /bin/bash

# Restart deployment
kubectl rollout restart -n wingman deployment/wingman
```

---

**Last Updated:** 2026-01-21
