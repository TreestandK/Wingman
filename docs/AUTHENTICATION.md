# Authentication & User Management

Wingman includes a complete authentication system with role-based access control (RBAC).

## Overview

**Features:**
- Session-based authentication with bcrypt password hashing
- Three user roles: Admin, Operator, Viewer
- Audit logging for all authentication events
- SAML integration framework
- Secure session cookies with CSRF protection
- Rate limiting to prevent brute force attacks

## Quick Start

### Default Admin User

On first run, Wingman automatically creates a default admin user:

- **Username:** `admin`
- **Password:** Value of `ADMIN_PASSWORD` environment variable

**⚠️ Change this password immediately after first login!**

### Environment Variables

```bash
# Required for secure sessions
FLASK_SECRET_KEY=your-random-32-character-secret-key

# Optional: Set default admin password (recommended)
ADMIN_PASSWORD=YourSecurePassword

# Optional: Disable auth (not recommended)
ENABLE_AUTH=true
```

Generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## User Roles

### Admin
- **Full system access**
- Create/delete users
- Modify any configuration
- Deploy and rollback servers
- Access all logs and audit trails

### Operator
- Deploy servers
- View deployments and logs
- Rollback deployments
- **Cannot** create users or modify system configuration

### Viewer
- **Read-only access**
- View deployments
- View logs
- **Cannot** deploy or modify anything

## User Management

### Create User (Web UI)

1. Login as admin
2. Go to Settings tab → User Management
3. Click "Add User"
4. Enter username, password, and role
5. Click "Create"

### Create User (CLI)

```bash
docker exec -it wingman python create_admin.py
```

Follow the prompts to create a new user.

### Change Password

**Via API:**
```bash
curl -X POST http://localhost:5000/api/users/username/password \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"new_password": "NewSecurePassword"}'
```

**Via CLI:**
```bash
docker exec -it wingman python3 << 'EOF'
from auth import AuthManager
import bcrypt

auth = AuthManager()
username = "admin"
new_password = "NewPassword123"

auth.users[username].password_hash = bcrypt.hashpw(
    new_password.encode('utf-8'),
    bcrypt.gensalt()
).decode('utf-8')
auth._save_users()
print(f"Password updated for {username}")
EOF
```

### Delete User

```bash
curl -X DELETE http://localhost:5000/api/users/username \
  -b cookies.txt
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with username/password
- `POST /api/auth/logout` - Logout current session
- `GET /api/auth/status` - Check authentication status

### User Management (Admin only)
- `GET /api/users` - List all users
- `POST /api/users` - Create new user
- `PUT /api/users/<username>` - Update user role
- `DELETE /api/users/<username>` - Delete user
- `POST /api/users/<username>/password` - Change password

## Security Features

### Session Security
- HttpOnly cookies (prevents XSS)
- SameSite=Strict (prevents CSRF)
- Secure flag (HTTPS only in production)
- Configurable session timeout

### Password Security
- bcrypt hashing with automatic salt
- Minimum password complexity enforced
- Password change on first login (recommended)

### Audit Logging
All authentication events are logged to `/app/data/audit.log`:
- Login attempts (success/failure)
- User creation/deletion
- Password changes
- Role modifications

View audit log:
```bash
docker exec wingman cat /app/data/audit.log
```

## Disabling Authentication

**Not recommended for production!**

To disable authentication (for testing only):

```bash
docker run -d -p 5000:5000 \
  -e ENABLE_AUTH=false \
  --name wingman \
  wingman:latest
```

## Troubleshooting

### Can't Log In

**Check credentials:**
```bash
docker exec wingman cat /app/data/users.json
```

**Reset admin password:**
```bash
docker exec -it wingman python create_admin.py
```

**Check audit log:**
```bash
docker exec wingman tail -20 /app/data/audit.log
```

### Login Page Not Showing (Firefox)

Firefox may cache the old non-auth version:
1. Clear browser cache (Ctrl+Shift+Delete)
2. Try incognito/private window
3. Use Chrome/Edge which respect cache headers better

### "Auth Disabled" Despite Setting ENABLE_AUTH=true

Check environment variables:
```bash
docker exec wingman env | grep ENABLE_AUTH
```

Rebuild without cache:
```bash
docker build --no-cache -t wingman:local .
```

### Permission Denied Errors

Check that user has correct role:
```bash
curl http://localhost:5000/api/auth/status -b cookies.txt
```

Operators cannot create users or modify config.
Viewers cannot deploy or modify anything.

## SAML Integration (Future)

Framework is in place for SAML integration. To enable:

1. Set `ENABLE_SAML=true`
2. Configure SAML provider details in config
3. Metadata URL or XML file required

(Full SAML documentation coming soon)

## Best Practices

1. **Always change default password** immediately
2. **Use strong secret key** (32+ random characters)
3. **Enable HTTPS** in production
4. **Review audit logs** regularly
5. **Use operator/viewer roles** for limited access users
6. **Don't disable auth** in production
7. **Rotate passwords** periodically
8. **Backup** `/app/data/users.json` and `/app/data/audit.log`
