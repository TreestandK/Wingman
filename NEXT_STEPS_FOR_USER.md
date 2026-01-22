# Next Steps: Debug Auth Issue

## What We Added

I've added comprehensive debugging to help us figure out why `auth_enabled` is showing as `false`.

### New Features:
1. **Debug logging** in AuthManager initialization (shows exact value read from environment)
2. **New `/api/auth/debug` endpoint** that shows everything about auth state
3. **Enhanced logging** in `/api/auth/status` endpoint
4. **Updated DEBUG_AUTH.md** with troubleshooting steps

---

## What You Need to Do Now

### On Your Windows Machine:

#### 1. Pull Latest Code
```powershell
cd D:\Wingman
git pull origin main
```

#### 2. Stop and Remove Old Container
```powershell
docker stop wingman
docker rm wingman
```

#### 3. Rebuild Image (with --no-cache)
```powershell
docker build --no-cache -t wingman:local .
```

#### 4. Run New Container
```powershell
docker run -d -p 5000:5000 `
  -e ADMIN_PASSWORD=YourSecurePassword `
  -e FLASK_SECRET_KEY=change-this-to-a-random-32-char-key `
  -e DOMAIN=treestandk.com `
  --name wingman `
  wingman:local
```

**IMPORTANT:** 
- Use `wingman:local` (your local build), NOT `ghcr.io/treestandk/wingman:latest`
- Do NOT set `ENABLE_AUTH` environment variable (let it use the default)

#### 5. Check the NEW Debug Log
```powershell
docker logs wingman 2>&1 | Select-String "AuthManager initialized"
```

**You should see something like:**
```
INFO - AuthManager initialized: ENABLE_AUTH=true, auth_enabled=True
```

If you see `auth_enabled=False`, then we know the problem is happening during initialization!

#### 6. Call the NEW Debug Endpoint
```powershell
curl http://localhost:5000/api/auth/debug
```

**Expected output:**
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
  },
  "auth_manager_id": 140234567890,
  "timestamp": "2026-01-22T12:34:56.789012"
}
```

**Key things to check:**
- `auth_enabled` should be `true`
- `auth_enabled_type` should be `"bool"`
- `ENABLE_AUTH` in environment should be `"NOT SET"` (we want it to use the default)
- `users` should include `["admin"]`

#### 7. Call the Status Endpoint (Again)
```powershell
curl http://localhost:5000/api/auth/status
```

This should now show `"auth_enabled": true`.

---

## What the Debug Output Will Tell Us

### Scenario 1: `AuthManager initialized` shows `auth_enabled=False`
**Problem:** Something is setting ENABLE_AUTH=false in the environment
**Solution:** Check docker-compose.yml, .env file, or docker run command for `ENABLE_AUTH=false`

### Scenario 2: `AuthManager initialized` shows `auth_enabled=True` but `/api/auth/status` shows `false`
**Problem:** Multiple AuthManager instances or the instance is being modified
**Solution:** Check `auth_manager_id` in debug output to see if it's the same instance

### Scenario 3: Debug endpoint shows `auth_enabled: true` but still redirects to home page
**Problem:** Frontend issue, not backend
**Solution:** Need to debug the index.html auth checking logic

### Scenario 4: Can't access debug endpoint (404 or connection refused)
**Problem:** Container using old image
**Solution:** Make sure you're using `wingman:local` not the GitHub image

---

## Quick Reference: Container Names

Throughout debugging, use:
- `wingman` (what you're using now)

NOT:
- `wingman-gameserver-manager` (old container name in some docs)

---

## If You Get Stuck

Share with me:
1. Output of: `docker logs wingman | Select-String "AuthManager"`
2. Output of: `curl http://localhost:5000/api/auth/debug`
3. Output of: `curl http://localhost:5000/api/auth/status`
4. Your `docker run` command or `docker-compose.yml` file

This will give us everything we need to solve the mystery!
