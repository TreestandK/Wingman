# Wingman Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Run Wingman Container

**Windows (PowerShell):**
```powershell
docker run -d -p 5000:5000 `
  -e ADMIN_PASSWORD=REPLACEME `
  -e FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") `
  -e DOMAIN=yourdomain.com `
  -v ${PWD}/data:/app/data `
  -v ${PWD}/logs:/app/logs `
  --name wingman `
  ghcr.io/treestandk/wingman:latest
```

**Linux/Mac:**
```bash
docker run -d -p 5000:5000 \
  -e ADMIN_PASSWORD=REPLACEME \
  -e FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
  -e DOMAIN=yourdomain.com \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name wingman \
  ghcr.io/treestandk/wingman:latest
```

**Docker Compose (Recommended):**
```yaml
version: '3.8'

services:
  wingman:
    image: ghcr.io/treestandk/wingman:latest
    container_name: wingman-gameserver-manager
    ports:
      - "5000:5000"
    environment:
      # Auth (enabled by default)
      - ADMIN_PASSWORD=REPLACEME
      - FLASK_SECRET_KEY=generate-a-random-32-char-key

      # Your configuration
      - DOMAIN=yourdomain.com
      - CF_API_TOKEN=
      - CF_ZONE_ID=
      - NPM_API_URL=
      - NPM_EMAIL=
      - NPM_PASSWORD=
      - UNIFI_URL=
      - UNIFI_USER=
      - UNIFI_PASS=
      - PTERO_URL=
      - PTERO_API_KEY=
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./templates:/app/templates/saved
    restart: unless-stopped

networks:
  wingman-network:
    driver: bridge
```

Then: `docker-compose up -d`

---

### Step 2: Check Container Status

```bash
# Check if running
docker ps | grep wingman

# View logs
docker logs wingman

# Should see:
# ============================================================
# CREATED DEFAULT ADMIN USER - CHANGE PASSWORD IMMEDIATELY!
# Username: admin
# Password: YourSecurePassword123
# ============================================================
```

---

### Step 3: Access & Login

Open your browser:
```
http://localhost:5000
```

**Login with:**
- Username: `admin`
- Password: (whatever you set in `ADMIN_PASSWORD`)

---

## 🔐 Authentication (Enabled by Default)

- **Default admin user** is auto-created on first run
- **Username**: `admin`
- **Password**: Set via `ADMIN_PASSWORD` env var (default: `admin123`)

### Create Additional Users

**Via CLI:**
```bash
docker exec -it wingman python create_admin.py
```

**Via API (after logging in):**
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username": "operator",
    "password": "secure-password",
    "role": "operator"
  }'
```

### Disable Authentication (Not Recommended)

```bash
docker run ... -e ENABLE_AUTH=false ...
```

---

## 📝 Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ADMIN_PASSWORD` | Admin user password | `SecurePass123!` |
| `FLASK_SECRET_KEY` | Session encryption key (32+ chars) | `your-random-key` |
| `DOMAIN` | Your domain name | `yourdomain.com` |

### Optional - Cloudflare

| Variable | Description |
|----------|-------------|
| `CF_API_TOKEN` | Cloudflare API token |
| `CF_ZONE_ID` | Cloudflare Zone ID |

### Optional - Nginx Proxy Manager

| Variable | Description |
|----------|-------------|
| `NPM_API_URL` | NPM API URL |
| `NPM_EMAIL` | NPM admin email |
| `NPM_PASSWORD` | NPM password |

### Optional - UniFi Controller

| Variable | Description |
|----------|-------------|
| `UNIFI_URL` | UniFi controller URL |
| `UNIFI_USER` | UniFi username |
| `UNIFI_PASS` | UniFi password |
| `UNIFI_SITE` | Site name (default: `default`) |
| `UNIFI_IS_UDM` | Set to `true` for UDM |

### Optional - Pterodactyl

| Variable | Description |
|----------|-------------|
| `PTERO_URL` | Pterodactyl panel URL |
| `PTERO_API_KEY` | Application API key |

---

## 🎮 Using Wingman

### 1. Configure Services

Go to **Settings** tab and configure your services:
- Cloudflare (DNS)
- Nginx Proxy Manager (reverse proxy)
- UniFi Controller (port forwarding)
- Pterodactyl (game server panel)

Click **Test Connectivity** to verify.

### 2. Deploy a Server

Go to **Deploy** tab:
1. Enter subdomain (e.g., `minecraft`)
2. Enter server IP
3. Select game type
4. Set resources (memory, disk)
5. Click **Deploy Server**

### 3. Monitor Deployments

Go to **Deployments** tab to:
- View active deployments
- Check deployment status
- View logs
- Rollback if needed

### 4. Save Templates

Frequently deploy the same configuration? Save it as a template!

---

## 🔧 Troubleshooting

### Can't access http://localhost:5000

```bash
# Check container is running
docker ps | grep wingman

# Check logs for errors
docker logs wingman

# Verify port mapping
docker port wingman
# Should show: 5000/tcp -> 0.0.0.0:5000

# Test from inside container
docker exec wingman curl http://localhost:5000/health
```

### Forgot admin password

```bash
docker exec -it wingman python3 << 'EOF'
from auth import AuthManager
import bcrypt
auth = AuthManager()
new_password = "NewPassword123"
password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
auth.users['admin'].password_hash = password_hash
auth._save_users()
print(f"Password reset to: {new_password}")
EOF
```

### Container keeps restarting

```bash
# Check logs
docker logs wingman --tail 100

# Common issues:
# 1. Port 5000 already in use - change to 5001:5000
# 2. Volume permissions - check /app/data is writable
# 3. Missing required env vars
```

---

## 📚 Next Steps

- [Authentication Guide](AUTHENTICATION_SETUP.md) - User management, RBAC, SAML
- [TrueNAS Installation](docs/TRUENAS-INSTALL.md) - Deploy on TrueNAS SCALE
- [Troubleshooting](DEBUG_AUTH.md) - Detailed debugging guide
- [API Documentation](docs/API.md) - REST API reference

---

## 🛡️ Security Notes

1. **Change the default password immediately**
2. **Set a strong FLASK_SECRET_KEY** (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
3. **Use HTTPS in production** (put behind reverse proxy)
4. **Restrict network access** to port 5000
5. **Review audit logs** regularly at `/app/data/audit.log`

---

## 🆘 Need Help?

- Check logs: `docker logs wingman`
- Run diagnostics: `docker exec wingman python test_auth.py`
- See [DEBUG_AUTH.md](DEBUG_AUTH.md) for detailed troubleshooting
- Open issue: https://github.com/treestandk/wingman/issues

---

**Enjoy automated game server management with Wingman!** 🎮✈️
