# Debugging Authentication Issues

## Quick Debug Steps

### Step 1: Use the New Debug Endpoint

**NEW!** We added a comprehensive debug endpoint:

```bash
curl http://localhost:5000/api/auth/debug | python -m json.tool
```

This shows:
- Current `auth_enabled` value and its type
- Number of users
- Environment variables (ENABLE_AUTH, ENABLE_SAML)
- Session information
- AuthManager instance ID

**Expected output when auth is enabled:**
```json
{
  "auth_manager": {
    "auth_enabled": true,
    "auth_enabled_type": "bool",
    "saml_enabled": false,
    "users_count": 1,
    "users": ["admin"]
  },
  "environment": {
    "ENABLE_AUTH": "NOT SET",
    "ENABLE_SAML": "NOT SET",
    "FLASK_SECRET_KEY_LENGTH": 32
  },
  "session": {
    "authenticated": false,
    "username": null,
    "role": null
  }
}
```

### Step 2: Check Container Status

```bash
docker ps -a | grep wingman
```

If the container is:
- **Exited/Crashed**: There's a startup error
- **Running**: Network/port issue

### Step 3: Check Container Logs for Auth Initialization

**NEW!** Look for the initialization message:

```bash
# Look for the AuthManager initialization log
docker logs wingman 2>&1 | grep "AuthManager initialized"

# Expected output:
# INFO - AuthManager initialized: ENABLE_AUTH=true, auth_enabled=True
```

If you see `auth_enabled=False`, that's the problem!

**Full container logs:**
```bash
# View all logs
docker logs wingman

# Follow logs in real-time
docker logs -f wingman

# Last 50 lines
docker logs --tail 50 wingman
```

Look for errors mentioning:
- `ModuleNotFoundError`
- `Permission denied`
- `OSError`
- `Failed to initialize`
- `AuthManager initialized` (this is the key line!)

### Step 3: Run Auth Test Script

```bash
docker exec -it wingman-gameserver-manager python test_auth.py
```

This will check:
- Environment variables
- Directory permissions
- Auth module imports
- User database status

### Step 4: Check if Directories Exist

```bash
docker exec wingman-gameserver-manager ls -la /app/data
docker exec wingman-gameserver-manager ls -la /app/logs
```

### Step 5: Manually Test App Startup

```bash
# Try to run the app manually
docker exec -it wingman-gameserver-manager python app.py
```

Watch for errors during startup.

---

## Common Issues & Solutions

### Issue 1: Container Won't Start (Connection Refused)

**Cause**: App crashed during startup

**Solution**:
```bash
# Check logs
docker logs wingman-gameserver-manager

# Common fixes:
# 1. Rebuild without cache
docker-compose build --no-cache
docker-compose up -d

# 2. Check if port 5000 is already in use
sudo netstat -tlnp | grep 5000
# or on Mac/Windows:
netstat -an | grep 5000

# 3. Try different port
# Edit docker-compose.yml: "5001:5000"
```

### Issue 2: "ModuleNotFoundError: No module named 'auth'"

**Cause**: Docker image wasn't rebuilt with new files

**Solution**:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue 3: "Permission denied" on /app/data

**Cause**: Volume mount permissions issue

**Solution**:
```bash
# Check volume permissions
docker exec wingman-gameserver-manager ls -la /app/data

# Fix permissions (if using host path volumes)
sudo chown -R 1000:1000 /path/to/host/volume/data

# Or in docker-compose.yml, remove volume mounts temporarily to test:
# volumes:
#   - ./data:/app/data  # Comment out
```

### Issue 4: Auth Enabled but No Users Created

**Cause**: /app/data not writable or initialization failed

**Solution**:
```bash
# Create admin user manually
docker exec -it wingman-gameserver-manager python create_admin.py

# Or disable auth temporarily
# In docker-compose.yml:
# - ENABLE_AUTH=false

# Restart
docker-compose restart
```

### Issue 5: Can't Access Login Page (404)

**Cause**: Template not copied to container

**Solution**:
```bash
# Check if login.html exists
docker exec wingman-gameserver-manager ls -la /app/templates/login.html

# If missing, rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Issue 6: Login Page Loads but Can't Log In

**Cause**: No users exist or credentials wrong

**Solution**:
```bash
# Check users
docker exec wingman-gameserver-manager cat /app/data/users.json

# If empty, create admin
docker exec -it wingman-gameserver-manager python create_admin.py

# Check audit log for failed attempts
docker exec wingman-gameserver-manager cat /app/data/audit.log
```

---

## Manual Fixes

### Reset Everything (Nuclear Option)

```bash
# Stop and remove container
docker-compose down

# Remove volumes (WARNING: Deletes all data!)
docker volume rm wingman-data wingman-logs wingman-templates

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d

# Create admin user
docker exec -it wingman-gameserver-manager python create_admin.py

# Enable auth
# Add to docker-compose.yml: ENABLE_AUTH=true
docker-compose restart
```

### Create Admin Without Container Running

If container keeps crashing:

```bash
# 1. Disable auth
# In docker-compose.yml: ENABLE_AUTH=false

# 2. Start container
docker-compose up -d

# 3. Create admin
docker exec -it wingman-gameserver-manager python create_admin.py

# 4. Enable auth
# In docker-compose.yml: ENABLE_AUTH=true

# 5. Restart
docker-compose restart
```

---

## Diagnostic Commands

### Check All Environment Variables
```bash
docker exec wingman-gameserver-manager env | grep -E '(ENABLE_AUTH|FLASK_SECRET)'
```

### Check Python Modules
```bash
docker exec wingman-gameserver-manager python -c "import auth; print('✓ auth works')"
docker exec wingman-gameserver-manager python -c "import bcrypt; print('✓ bcrypt works')"
```

### Check File Permissions
```bash
docker exec wingman-gameserver-manager ls -la /app/*.py
docker exec wingman-gameserver-manager ls -la /app/templates/
```

### Test HTTP Connection
```bash
# From host
curl -v http://localhost:5000/health

# From inside container
docker exec wingman-gameserver-manager curl -v http://localhost:5000/health
```

### Interactive Shell
```bash
docker exec -it wingman-gameserver-manager /bin/bash
# Then test manually:
cd /app
python app.py
```

---

## Still Not Working?

### Collect Debug Info

Run these commands and share the output:

```bash
# 1. Container status
docker ps -a | grep wingman

# 2. Recent logs
docker logs --tail 100 wingman-gameserver-manager 2>&1 | tee wingman-debug.log

# 3. Auth test
docker exec wingman-gameserver-manager python test_auth.py 2>&1 | tee auth-test.log

# 4. Environment
docker exec wingman-gameserver-manager env | grep -E '(ENABLE|FLASK)' 2>&1 | tee env.log

# 5. File structure
docker exec wingman-gameserver-manager find /app -type f -name "*.py" 2>&1 | tee files.log
```

Then share:
- `wingman-debug.log`
- `auth-test.log`
- `env.log`
- Your docker-compose.yml (with secrets redacted)

---

## Contact

If none of these work, open an issue with the debug logs at:
https://github.com/treestandk/wingman/issues
