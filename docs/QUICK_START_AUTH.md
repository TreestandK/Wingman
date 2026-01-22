# Quick Start: Setting Up Authentication in Wingman

## Step 1: Rebuild Your Docker Image

Since you're running the container, you need to rebuild with the new authentication code:

```bash
# Stop the current container
docker-compose down
# or
docker stop wingman-gameserver-manager

# Rebuild the image
docker-compose build --no-cache

# Start it back up
docker-compose up -d
```

## Step 2: Create Your First Admin User

Before enabling authentication, create an admin account:

```bash
docker exec -it wingman-gameserver-manager python create_admin.py
```

Follow the prompts:
```
Enter username: admin
Enter email (optional): admin@yourdomain.com
Enter password: [type a secure password]
Confirm password: [type it again]
```

You'll see:
```
✅ Admin user created successfully!
Username: admin
Role: admin

To enable authentication, set environment variable:
  ENABLE_AUTH=true
```

## Step 3: Enable Authentication (Optional)

If you want to require login, update your `docker-compose.yml`:

```yaml
services:
  wingman:
    environment:
      - ENABLE_AUTH=true  # Add this line
      - DOMAIN=treestandk.com
      # ... rest of your config
```

Then restart:
```bash
docker-compose restart
```

## Step 4: Test It!

**Without ENABLE_AUTH=true:**
- Go to http://your-server:5000
- Works exactly as before - no login needed

**With ENABLE_AUTH=true:**
- Go to http://your-server:5000
- You'll be redirected to `/login`
- Enter your admin credentials
- You're in!

## Alternative: Use Environment Variable Only

If you don't want to edit docker-compose.yml, you can set it temporarily:

```bash
docker run -e ENABLE_AUTH=true \
  -e DOMAIN=treestandk.com \
  # ... rest of your config
```

## Creating Additional Users

Once logged in as admin, you can create more users via API:

```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username": "operator",
    "password": "secure-password",
    "role": "operator",
    "email": "operator@example.com"
  }'
```

Or use the CLI tool:
```bash
docker exec -it wingman-gameserver-manager python create_admin.py
```

## Roles Available

- **admin**: Full access (manage users, config, deployments)
- **operator**: Deploy servers, view logs, manage templates
- **viewer**: Read-only access

## If Something Goes Wrong

**Can't log in?**
```bash
# Check if auth is enabled
docker exec wingman-gameserver-manager env | grep ENABLE_AUTH

# Check logs
docker logs wingman-gameserver-manager

# View users
docker exec wingman-gameserver-manager cat /app/data/users.json
```

**Forgot password?**
```bash
docker exec -it wingman-gameserver-manager python3 << 'EOF'
from auth import AuthManager
import bcrypt
auth = AuthManager()
new_password = "new-password-here"
password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
auth.users['admin'].password_hash = password_hash
auth._save_users()
print("Password reset!")
EOF
```

## Disabling Authentication

Just remove or set `ENABLE_AUTH=false` and restart. All user data is preserved.

---

**For full documentation, see:** [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md)
