# Wingman Authentication Setup Guide

## Quick Start

Authentication in Wingman is **optional** and disabled by default. Follow these steps to enable it.

### Step 1: Create the First Admin User

Before enabling authentication, you need to create an admin account.

**Option A: Using the CLI tool (Recommended)**

```bash
# If using Docker
docker exec -it wingman-gameserver-manager python create_admin.py

# If running locally
python create_admin.py
```

Follow the prompts to create your admin user:
```
Wingman Admin User Creation Tool
==========================================================

Creating new admin user...

Enter username: admin
Enter email (optional): admin@example.com
Enter password: ********
Confirm password: ********

✅ Admin user created successfully!
Username: admin
Role: admin
Email: admin@example.com

To enable authentication, set environment variable:
  ENABLE_AUTH=true
```

**Option B: Using Python directly**

```bash
docker exec -it wingman-gameserver-manager python3 << 'EOF'
from auth import AuthManager
auth_manager = AuthManager()
result = auth_manager.create_user('admin', 'your-secure-password', 'admin', 'admin@example.com')
print(result)
EOF
```

### Step 2: Enable Authentication

Add the environment variable to your deployment:

**Docker Compose:**
```yaml
environment:
  - ENABLE_AUTH=true
```

**Docker Run:**
```bash
docker run -e ENABLE_AUTH=true ...
```

**TrueNAS SCALE:**
Add environment variable in the Custom App configuration:
- Variable: `ENABLE_AUTH`
- Value: `true`

### Step 3: Restart the Application

```bash
# Docker Compose
docker-compose restart

# Docker (by container name)
docker restart wingman-gameserver-manager

# TrueNAS
kubectl rollout restart deployment/wingman -n wingman
```

### Step 4: Log In

1. Navigate to `http://your-server:5000`
2. You'll be redirected to the login page
3. Enter your admin credentials
4. You're now logged in!

---

## User Roles

Wingman supports three user roles with different permission levels:

### Admin
- **Full system access**
- Manage configurations
- Create, view, edit, and delete deployments
- Manage templates
- **Manage users** (create, delete, change roles)
- View monitoring statistics
- Access system settings

### Operator
- Create and manage deployments
- View configurations (cannot edit)
- Create and edit own templates
- Rollback deployments
- View logs and monitoring
- **Cannot** manage users or system settings

### Viewer
- **Read-only access**
- View deployment status and history
- View deployment logs
- View monitoring statistics
- **Cannot** create or modify anything

---

## Managing Users

### Create Additional Users (Admin Only)

**Via Web UI:**
1. Log in as admin
2. Go to Settings → User Management (coming soon)
3. Click "Add User"
4. Enter username, password, role, and optional email
5. Click "Create User"

**Via API:**
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{
    "username": "operator1",
    "password": "secure-password",
    "role": "operator",
    "email": "operator@example.com"
  }'
```

**Via CLI:**
```bash
docker exec -it wingman-gameserver-manager python create_admin.py
```
(Works for creating any role, not just admin)

### Change User Role

```bash
curl -X PUT http://localhost:5000/api/users/operator1/role \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"role": "admin"}'
```

### Delete User

```bash
curl -X DELETE http://localhost:5000/api/users/operator1 \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

Note: You cannot delete the last admin user.

### Change Your Own Password

```bash
curl -X POST http://localhost:5000/api/users/change-password \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{
    "old_password": "current-password",
    "new_password": "new-secure-password"
  }'
```

---

## SAML Integration (Optional)

Wingman supports SAML authentication via Keycloak or other SAML providers.

### Prerequisites
- A running SAML Identity Provider (Keycloak, Okta, Azure AD, etc.)
- SAML metadata from your IdP

### Enable SAML

1. Set environment variables:
```bash
ENABLE_SAML=true
SAML_IDP_METADATA_URL=https://your-idp.com/auth/realms/your-realm/protocol/saml/descriptor
# OR provide metadata file path
SAML_IDP_METADATA_FILE=/app/data/saml_metadata.xml
```

2. Configure SAML settings:
```bash
SAML_SP_ENTITY_ID=http://your-server:5000
SAML_SP_ACS_URL=http://your-server:5000/api/auth/saml/acs
SAML_SP_SLS_URL=http://your-server:5000/api/auth/saml/sls
```

3. Restart the application

4. Access via `/api/auth/saml/login` for SAML login

Note: SAML users still need to be created in Wingman first. SAML only handles authentication, not user provisioning.

---

## Security Best Practices

### 1. Strong Passwords
- Minimum 8 characters required
- Use a mix of uppercase, lowercase, numbers, and symbols
- Use a password manager

### 2. Change Default Admin Password
If you used the default password during initial setup, **change it immediately**:
```bash
curl -X POST http://localhost:5000/api/users/change-password \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "admin123",
    "new_password": "your-new-secure-password"
  }'
```

### 3. Secure Flask Secret Key
Generate a secure random secret key:
```bash
# Generate a random 32-character key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Then set it in your environment:
```bash
FLASK_SECRET_KEY=your-generated-secret-key-here
```

**Important:** Changing the secret key will log out all users!

### 4. Use HTTPS in Production
Never use authentication over plain HTTP in production. Put Wingman behind a reverse proxy with SSL/TLS:
- Nginx Proxy Manager
- Traefik
- Caddy
- nginx with Let's Encrypt

### 5. Limit Access
Use firewall rules to restrict access to the Wingman port (5000) to trusted networks only.

### 6. Regular Audits
Check the audit log regularly:
```bash
# View audit log
docker exec wingman-gameserver-manager cat /app/data/audit.log

# Or tail it in real-time
docker exec wingman-gameserver-manager tail -f /app/data/audit.log
```

---

## Audit Logging

All authentication events are logged to `/app/data/audit.log`:

```
2024-01-22T10:15:23.456789 | login_success | admin | 192.168.1.100 | Successful login
2024-01-22T10:20:15.123456 | user_created | operator1 | 192.168.1.100 | User operator1 created with role operator
2024-01-22T10:25:45.789012 | password_changed | admin | 192.168.1.100 | Password changed successfully
2024-01-22T11:00:00.000000 | login_failed | hacker | 192.168.1.200 | Invalid password
```

---

## Troubleshooting

### I forgot my admin password

Reset it via Docker:
```bash
docker exec -it wingman-gameserver-manager python3 << 'EOF'
from auth import AuthManager
import bcrypt
auth_manager = AuthManager()
# Set new password
new_password = "new-admin-password"
password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
auth_manager.users['admin'].password_hash = password_hash
auth_manager._save_users()
print("Admin password reset to:", new_password)
EOF
```

### Authentication isn't working

1. Check `ENABLE_AUTH=true` is set
2. Verify you created at least one user
3. Check logs: `docker logs wingman-gameserver-manager`
4. Ensure `FLASK_SECRET_KEY` is set and hasn't changed

### Can't create first admin user

Make sure the `/app/data` directory is writable:
```bash
docker exec wingman-gameserver-manager ls -la /app/data
```

### Session expires too quickly

Sessions expire when the container restarts or if `FLASK_SECRET_KEY` changes. Set a permanent secret key.

---

## Disabling Authentication

To disable authentication:

1. Set environment variable:
```bash
ENABLE_AUTH=false
```

2. Restart the application

All endpoints will be accessible without login. Users and audit logs are preserved.

---

## File Locations

- **User database:** `/app/data/users.json`
- **Audit log:** `/app/data/audit.log`
- **Session data:** In-memory (lost on restart unless using Redis)

**Backup these files** as part of your regular backup strategy!

---

## API Reference

### Authentication Endpoints

- `POST /api/auth/login` - Login with username/password
- `POST /api/auth/logout` - Logout current session
- `GET /api/auth/status` - Check authentication status

### User Management (Admin Only)

- `GET /api/users` - List all users
- `POST /api/users` - Create new user
- `DELETE /api/users/<username>` - Delete user
- `PUT /api/users/<username>/role` - Update user role
- `POST /api/users/change-password` - Change own password

---

## Next Steps

- Set up user accounts for your team
- Configure SAML for enterprise authentication (optional)
- Review audit logs regularly
- Set up HTTPS with reverse proxy
- Enable monitoring and alerts

For more information, see:
- [Wingman Documentation](docs/README.md)
- [RBAC Permissions](rbac.py)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
