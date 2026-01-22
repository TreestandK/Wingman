# Pterodactyl Integration Guide

## Overview

Wingman now supports automatic game server creation in Pterodactyl during deployment. This allows you to:
- Select a Pterodactyl nest and egg from the deploy form
- Choose which node to deploy to
- Automatically allocate ports
- Create the server with custom resource limits
- Link the deployment with the Pterodactyl server

## Prerequisites

1. **Pterodactyl Panel** running and accessible
2. **Application API Key** with full permissions
3. **At least one node** configured with available allocations
4. **Nests and eggs** set up for your desired games

## Configuration

### 1. Get Your Pterodactyl API Key

1. Log into your Pterodactyl panel as admin
2. Go to **Account** → **API Credentials**
3. Click **Create New**
4. Give it a descriptive name (e.g., "Wingman Integration")
5. **Important**: Use an **Application API Key**, not a Client API Key
6. Copy the key (you won't see it again!)

### 2. Configure Wingman

Add your Pterodactyl configuration via the Settings tab or environment variables:

**Via Environment Variables:**
```bash
docker run -d -p 5000:5000 \
  -e PTERO_URL=https://panel.yourdomain.com \
  -e PTERO_API_KEY=ptla_your_application_api_key \
  --name wingman \
  wingman:local
```

**Via Settings Tab:**
1. Open Wingman web interface
2. Go to **Settings** tab
3. Scroll to **Pterodactyl Configuration**
4. Enter:
   - **URL**: `https://panel.yourdomain.com` (no trailing slash)
   - **API Key**: Your application API key
5. Click **Save Configuration**
6. Click **Test Connectivity** to verify

## Usage

### Deploy a Server with Pterodactyl

1. Go to the **Deploy Server** tab
2. Fill in basic configuration (subdomain, IP, game type, port)
3. Set resource allocation (memory, disk, CPU)
4. Expand **Pterodactyl Game Server** section
5. Check ☑ **Create Pterodactyl Server**
6. Configure Pterodactyl:
   - **Nest**: Select the nest (e.g., "Minecraft", "Source Engine")
   - **Egg**: Select the specific egg (e.g., "Minecraft Java", "Paper")
   - **Node**: Choose which node to deploy on
   - **Port Allocation**: Select an available port
7. Click **Deploy Server**

### What Happens

When you deploy with Pterodactyl enabled:

1. **Cloudflare DNS** is created (if configured)
2. **UniFi port forwarding** is set up (if configured)
3. **Nginx Proxy Manager** creates the reverse proxy (if configured)
4. **Pterodactyl server** is created with:
   - Selected egg and configuration
   - Your specified resource limits (memory, disk, CPU)
   - Allocated port
   - Server name: `{subdomain}-{game_type}`

The deployment log will show:
```
Creating Pterodactyl game server...
✓ Server created: minecraft-minecraft_java (ID: 42)
```

## Troubleshooting

### "Pterodactyl not configured or not enabled"

**Problem**: Wingman can't connect to Pterodactyl

**Solutions:**
1. Check your PTERO_URL doesn't have a trailing slash
2. Verify your API key is an **Application** key (starts with `ptla_`)
3. Test connectivity in Settings tab
4. Check Pterodactyl logs for API errors

### "No eggs available in this nest"

**Problem**: The selected nest has no eggs

**Solutions:**
1. Verify eggs exist in Pterodactyl admin panel
2. Navigate to **Nests** → Select your nest → **Eggs**
3. Import eggs if needed
4. Refresh the Wingman page

### "No available ports on this node"

**Problem**: Node has no unassigned allocations

**Solutions:**
1. In Pterodactyl panel, go to **Nodes** → Select node → **Allocation**
2. Click **Create Allocation**
3. Add IP and port range (e.g., 25565-25600)
4. Refresh Wingman and try again

### "Error creating Pterodactyl server"

**Problem**: Server creation failed

**Solutions:**
1. Check Pterodactyl panel logs
2. Verify your API key has sufficient permissions
3. Ensure the selected node has available resources
4. Check the deployment logs for specific error details

### API Key Permissions

Your Application API key needs these permissions:
- ✅ **Read & Write** - Servers
- ✅ **Read** - Nodes
- ✅ **Read** - Allocations
- ✅ **Read** - Nests
- ✅ **Read** - Eggs

## Advanced Configuration

### Default User ID

By default, Pterodactyl servers are created for user ID 1 (usually admin). To change this, add to your config:

```json
{
  "pterodactyl": {
    "url": "https://panel.yourdomain.com",
    "api_key": "ptla_...",
    "enabled": true,
    "default_user_id": 2
  }
}
```

### Database & Backup Limits

Configure default limits for databases and backups:

```json
{
  "pterodactyl": {
    "url": "https://panel.yourdomain.com",
    "api_key": "ptla_...",
    "enabled": true,
    "default_databases": 2,
    "default_backups": 5
  }
}
```

## API Endpoints

### Get Nests
```bash
GET /api/pterodactyl/nests
```

Returns list of nests with their eggs.

### Get Nodes
```bash
GET /api/pterodactyl/nodes
```

Returns list of nodes with resource information.

### Get Allocations
```bash
GET /api/pterodactyl/nodes/{node_id}/allocations
```

Returns available (unassigned) port allocations for a node.

### Get Eggs
```bash
GET /api/pterodactyl/eggs
```

Returns all eggs from all nests.

## Examples

### Minecraft Java Server

1. **Nest**: Minecraft
2. **Egg**: Paper
3. **Resources**: 4GB RAM, 10GB disk, 100% CPU
4. **Node**: Your Minecraft node
5. **Port**: Any available allocation

### Valheim Server

1. **Nest**: Steamcmd Servers
2. **Egg**: Valheim
3. **Resources**: 4GB RAM, 15GB disk, 200% CPU
4. **Node**: Your game node
5. **Port**: Default 2456-2458

### ARK: Survival Evolved

1. **Nest**: Steamcmd Servers
2. **Egg**: ARK: Survival Evolved
3. **Resources**: 8GB RAM, 50GB disk, 200% CPU
4. **Node**: High-performance node
5. **Port**: 7777-7778

## Integration with Existing Deployments

If you have existing Wingman deployments, you can manually link them to Pterodactyl servers by editing the deployment JSON in `/app/data/deployments.json`:

```json
{
  "deployment-id-123": {
    "subdomain": "minecraft",
    "pterodactyl_server_id": 42,
    "pterodactyl_server_uuid": "abcd1234-...",
    ...
  }
}
```

## Best Practices

1. **Use descriptive nest names** matching your game categories
2. **Assign sufficient allocations** to each node (at least 20-50 ports)
3. **Monitor node resources** to avoid over-allocation
4. **Use separate nodes** for different game types if possible
5. **Test connectivity** after configuring Pterodactyl credentials
6. **Keep API keys secure** - never commit them to git

## Limitations

- Pterodactyl integration is optional - deployments work without it
- Server creation is one-directional (Wingman → Pterodactyl only)
- Deleting a deployment does not delete the Pterodactyl server
- Rollback removes DNS/proxy but not the Pterodactyl server

## Future Enhancements

Planned features:
- Server start/stop/restart from Wingman UI
- Real-time server status from Pterodactyl
- Console access through Wingman
- Automatic server deletion on rollback
- Server modification (change resources, reinstall)
- Backup management integration

---

**Status**: ✅ Fully Implemented

Pterodactyl egg selection is now available in Wingman!
