# Server Deployment Guide

Learn how to deploy game servers using Wingman's web interface.

## Prerequisites

Before deploying servers, configure these services in the Settings tab:

- **Cloudflare** (optional) - Automatic DNS record creation
- **Nginx Proxy Manager** (optional) - Automatic reverse proxy setup
- **UniFi Controller** (optional) - Automatic port forwarding
- **Pterodactyl Panel** (optional) - Automatic game server creation

At minimum, you need:
- A subdomain
- Server IP address
- Game type and port

## Basic Deployment

### Step 1: Navigate to Deploy Tab

Click the **"Deploy Server"** tab in the navigation menu.

### Step 2: Fill Basic Configuration

**Subdomain:**
- Enter a subdomain (e.g., `minecraft`, `valheim`)
- Alphanumeric and hyphens only
- Will create `subdomain.yourdomain.com`

**Server IP:**
- Enter the game server's IP address
- Format: `192.168.1.100` or public IP

**Game Type:**
- Select from dropdown:
  - Minecraft (Java)
  - Minecraft (Bedrock)
  - Valheim
  - Terraria
  - Palworld
  - Rust
  - ARK: Survival Evolved
  - Custom

**Primary Port:**
- Enter the main game port
- Examples: 25565 (Minecraft), 2456 (Valheim)

### Step 3: Resource Allocation

**Memory (MB):**
- RAM allocation for server
- Example: 4096 = 4GB
- Minimum: 512MB

**Disk Space (MB):**
- Storage allocation
- Example: 10240 = 10GB
- Minimum: 1024MB (1GB)

**CPU Limit (%):**
- CPU allocation
- 100% = 1 core, 200% = 2 cores
- Default: 100%

**Additional Ports (optional):**
- Comma-separated list: `25575, 25576`
- Used for RCON, query, etc.

### Step 4: Advanced Options (Optional)

Click to expand **"Advanced Options"**:

**Enable SSL/TLS:**
- ✅ Checked by default
- Creates HTTPS proxy

**Enable Monitoring:**
- ☑ Optional
- Enables metrics collection

**Protocol:**
- TCP + UDP (Both) - Most common
- TCP Only
- UDP Only

### Step 5: Pterodactyl Game Server (Optional)

If Pterodactyl is configured, expand **"Pterodactyl Game Server"**:

1. ✅ Check "Create Pterodactyl Server"
2. **Select Nest** (e.g., Minecraft, Source Engine)
3. **Select Egg** (specific game type)
4. **Select Node** (which server to deploy on)
5. **Select Port Allocation** (available port)

See [PTERODACTYL.md](PTERODACTYL.md) for details.

### Step 6: Deploy

Click **"Deploy Server"** button.

## Real-Time Console

After clicking deploy, a real-time console appears showing:

- Connection status
- Each deployment step
- Success/error messages
- Progress percentage

**Console Controls:**
- 🗑 **Clear** - Clear console logs
- 💾 **Export** - Download logs as .txt file

**Log Colors:**
- 🔵 Blue - System messages
- ⚪ White - Regular logs
- 🟢 Green - Success
- 🔴 Red - Errors
- 🟡 Yellow - Warnings

## Deployment Steps

A typical deployment performs these steps:

1. **Validation** - Check configuration
2. **Cloudflare DNS** - Create DNS record
3. **UniFi Port Forwarding** - Configure firewall rules
4. **Nginx Proxy Manager** - Create reverse proxy
5. **Pterodactyl Server** - Create game server (if enabled)

Each step shows:
- ⏳ Pending - Not started
- ▶️ Active - In progress
- ✅ Completed - Success
- ❌ Failed - Error occurred

## View Deployments

### Active Deployments Tab

Shows all deployments with:
- Subdomain and server IP
- Game type and status
- Progress percentage
- Deployment ID
- Created timestamp

**Actions:**
- 🔄 **Rollback** - Remove deployment (DNS, proxy, etc.)
- 📋 **View Logs** - See deployment logs

### Deployment Status

**Status Types:**
- **Pending** - Queued, not started
- **Running** - Currently deploying
- **Completed** - Successfully deployed
- **Failed** - Error occurred

## Templates

### Save as Template

When deploying, check **"Save as Template"**:
1. ✅ Check "Save as Template"
2. Enter template name
3. Click Deploy

Template saves your configuration for reuse.

### Use Template

1. Go to **Templates** tab
2. Click template name
3. Modify if needed
4. Click Deploy

## Rollback Deployment

To remove a deployment:

1. Go to **Deployments** tab
2. Find the deployment
3. Click **"Rollback"** button
4. Confirm action

**What gets removed:**
- ✅ Cloudflare DNS record
- ✅ Nginx Proxy Manager proxy
- ✅ UniFi port forwarding rules
- ⚠️ **Note:** Pterodactyl server is NOT automatically deleted

## Error Handling

If deployment fails, you'll see:
- Detailed error message
- Troubleshooting steps
- Documentation links

**Common Issues:**

**"Service Not Configured"**
- Configure the service in Settings tab
- Click "Test Connectivity" to verify

**"Connection Refused"**
- Check service URL is correct
- Verify API credentials
- Check network connectivity

**"Permission Denied"**
- Verify API key has sufficient permissions
- Check firewall rules

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more help.

## API Deployment

Deploy via API:

```bash
curl -X POST http://localhost:5000/api/deploy \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "subdomain": "minecraft",
    "server_ip": "192.168.1.100",
    "game_type": "minecraft_java",
    "game_port": 25565,
    "memory_mb": 4096,
    "disk_mb": 10240,
    "cpu_limit": 100,
    "enable_ssl": true,
    "enable_monitoring": false,
    "protocol": "tcp_udp"
  }'
```

**Response:**
```json
{
  "success": true,
  "deployment_id": "dep_abc123",
  "message": "Deployment started"
}
```

**Check Status:**
```bash
curl http://localhost:5000/api/deploy/dep_abc123/status -b cookies.txt
```

## Best Practices

1. **Test connectivity** before deploying
2. **Use meaningful subdomains** (e.g., `mc-survival`, `valheim-pve`)
3. **Allocate sufficient resources** for the game type
4. **Enable SSL** for secure connections
5. **Save successful configs** as templates
6. **Review logs** if deployment fails
7. **Rollback failed deployments** to clean up resources
8. **Monitor resource usage** on game servers

## Game-Specific Examples

### Minecraft Java Server
```
Subdomain: minecraft
Server IP: 192.168.1.100
Game Type: Minecraft (Java)
Port: 25565
Memory: 4096 MB
Disk: 10240 MB
CPU: 100%
Additional Ports: 25575 (RCON)
```

### Valheim Server
```
Subdomain: valheim
Server IP: 192.168.1.101
Game Type: Valheim
Port: 2456
Memory: 4096 MB
Disk: 15360 MB
CPU: 200%
Additional Ports: 2457, 2458
```

### ARK: Survival Evolved
```
Subdomain: ark
Server IP: 192.168.1.102
Game Type: ARK: Survival Evolved
Port: 7777
Memory: 8192 MB
Disk: 51200 MB (50GB)
CPU: 200%
Additional Ports: 7778, 27015
```

## Monitoring Deployments

After deployment:

1. Check service is accessible at `subdomain.yourdomain.com`
2. Verify port forwarding works
3. Test SSL certificate (if enabled)
4. Connect to game server
5. Check logs for any warnings

Use **Monitoring** tab to view:
- Active connections
- Resource usage
- Uptime statistics
- Performance metrics
