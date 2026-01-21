# Wingman Game Server Manager - Docker Deployment Guide

Transform your game server deployment automation into a web-based application with monitoring and a beautiful UI!

## What This Is

This is a Docker Compose application that converts the original `gameserver-deploy.sh` bash script into a modern web application with:

- **Web GUI**: Beautiful, responsive web interface
- **Real-time Monitoring**: Track deployment status and server health
- **Template Management**: Save and reuse server configurations
- **API-driven**: RESTful API for all operations
- **Persistent Storage**: All data saved in Docker volumes
- **TrueNAS Compatible**: Can be deployed as a TrueNAS app

## Features

- Deploy game servers with a few clicks
- Automatic Cloudflare DNS configuration
- UniFi port forwarding automation
- Nginx Proxy Manager integration
- Pterodactyl panel integration
- Template system for common configurations
- Deployment history and rollback capability
- Real-time deployment progress tracking
- Monitoring dashboard

## Quick Start

### 1. Configuration

Create a `.env` file in the same directory as `docker-compose.yml`:

```bash
# Domain Configuration
DOMAIN=treestandk.com

# Cloudflare Configuration
CF_API_TOKEN=your_cloudflare_api_token
CF_ZONE_ID=your_cloudflare_zone_id

# Nginx Proxy Manager Configuration
NPM_API_URL=http://192.168.1.100:81/api
NPM_EMAIL=admin@example.com
NPM_PASSWORD=your_npm_password

# UniFi Configuration
UNIFI_URL=https://192.168.1.1
UNIFI_USER=admin
UNIFI_PASS=your_unifi_password
UNIFI_SITE=default
UNIFI_IS_UDM=false

# Pterodactyl Configuration
PTERO_URL=https://panel.yourdomain.com
PTERO_API_KEY=your_pterodactyl_api_key

# Network Configuration
PUBLIC_IP=

# Feature Flags
ENABLE_AUTO_UNIFI=true
ENABLE_SSL_AUTO=true
ENABLE_MONITORING=false

# Application Settings
FLASK_SECRET_KEY=change-this-to-a-random-secret-key
```

### 2. Deploy with Docker Compose

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### 3. Access the Web Interface

Open your browser and navigate to:
```
http://localhost:5000
```

Or if deployed on a server:
```
http://your-server-ip:5000
```

## TrueNAS Deployment

### Quick Installation via YAML (Recommended)

For TrueNAS SCALE, use the automated YAML installation:

1. Copy `truenas/install.yaml` to your TrueNAS system
2. Edit the credentials in the file
3. Run: `kubectl apply -f install.yaml`
4. Access at `http://your-truenas-ip:30500`

**📖 See [TRUENAS-INSTALL.md](TRUENAS-INSTALL.md) for complete TrueNAS installation guide with:**
- Step-by-step YAML installation
- Custom App via GUI setup
- Automatic update configuration
- Monitoring and troubleshooting
- Backup and restore procedures

### Option 1: Using TrueNAS Custom App

1. In TrueNAS SCALE, go to **Apps** > **Discover Apps**
2. Click **Custom App**
3. Configure the following:

**Application Name**: `wingman`

**Image Repository**: Build your image first, then use it, or use:
```
ghcr.io/your-username/wingman:latest
```

**Container Port**: `5000`

**Node Port**: `30500` (or your preferred port)

**Environment Variables**: Add all variables from the `.env` file above

**Storage**:
- Add Host Path Volume: `/mnt/pool/wingman/data` → `/app/data`
- Add Host Path Volume: `/mnt/pool/wingman/logs` → `/app/logs`
- Add Host Path Volume: `/mnt/pool/wingman/templates` → `/app/templates/saved`

4. Click **Install**

### Option 2: Using Kubernetes YAML

For a production-ready deployment on TrueNAS SCALE, use the Kubernetes manifests in the `truenas/` directory. This provides:

- Automatic updates with rolling deployments
- Proper secrets management
- Persistent volume claims
- Health checks and monitoring
- Easy configuration via TrueNAS GUI (questions.yaml)

See [TRUENAS-INSTALL.md](TRUENAS-INSTALL.md) for detailed instructions.

## Usage

### Deploy a New Game Server

1. Navigate to the **Deploy Server** tab
2. Fill in the deployment form:
   - Subdomain (e.g., "minecraft")
   - Server IP address
   - Game type (auto-fills port and resources)
   - Primary port
   - Additional ports (if needed)
   - Memory and disk allocation
3. Optionally save as a template
4. Click **Deploy Server**
5. Watch the real-time deployment progress

### Use Templates

1. Go to the **Templates** tab
2. Click **Use Template** on any saved template
3. Modify settings as needed
4. Deploy

### Monitor Deployments

1. Go to the **Deployments** tab to see all active deployments
2. View logs for any deployment
3. Rollback deployments if needed
4. Check the **Monitoring** tab for statistics

### Settings

The **Settings** tab allows you to:
- Validate your configuration
- Test API connectivity
- View current system status

## Supported Game Types

Pre-configured templates for:
- Minecraft (Java Edition)
- Minecraft (Bedrock Edition)
- Valheim
- Terraria
- Palworld
- Rust
- ARK: Survival Evolved
- Custom games

## Architecture

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│  Flask Web App  │  (Port 5000)
│  (app.py)       │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────┐
│  Deployment Manager         │
│  (deployment_manager.py)    │
└──┬────┬────┬────┬──────────┘
   │    │    │    │
   ↓    ↓    ↓    ↓
 CF   NPM  UniFi Ptero
```

## API Endpoints

The application exposes a RESTful API:

- `GET /health` - Health check
- `POST /api/deploy` - Start a deployment
- `GET /api/deploy/<id>/status` - Get deployment status
- `GET /api/deployments` - List all deployments
- `POST /api/deploy/<id>/rollback` - Rollback a deployment
- `GET /api/templates` - List templates
- `POST /api/templates` - Save a template
- `POST /api/config/validate` - Validate configuration
- `POST /api/config/test` - Test API connectivity
- `GET /api/monitoring/stats` - Get monitoring stats

## Volumes

Three persistent volumes are created:

- `wingman-data`: Deployment state and configuration
- `wingman-logs`: Application and deployment logs
- `wingman-templates`: Saved deployment templates

## Security Considerations

1. **Change the Flask secret key** in your `.env` file
2. **Secure your API credentials** - never commit the `.env` file
3. **Use HTTPS** in production with a reverse proxy
4. **Restrict network access** to the management interface
5. **Regular backups** of the data volumes

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs wingman
```

### Can't connect to APIs

1. Go to the **Settings** tab
2. Click **Test All APIs**
3. Check which services are failing
4. Verify credentials in `.env` file

### Deployment fails

1. Go to **Deployments** tab
2. Click **Logs** on the failed deployment
3. Review error messages
4. Fix configuration issues
5. Try again or rollback

### Port conflicts

If port 5000 is already in use, edit `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Change 5000 to any available port
```

## Upgrading

To upgrade to a new version:

```bash
# Pull latest changes
git pull

# Rebuild the container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

Your data will be preserved in the Docker volumes.

## Backing Up

To backup your deployment data:

```bash
# Backup data volume
docker run --rm -v wingman-data:/data -v $(pwd):/backup alpine tar czf /backup/wingman-data-backup.tar.gz -C /data .

# Backup templates
docker run --rm -v wingman-templates:/data -v $(pwd):/backup alpine tar czf /backup/wingman-templates-backup.tar.gz -C /data .
```

To restore:

```bash
# Restore data
docker run --rm -v wingman-data:/data -v $(pwd):/backup alpine tar xzf /backup/wingman-data-backup.tar.gz -C /data

# Restore templates
docker run --rm -v wingman-templates:/data -v $(pwd):/backup alpine tar xzf /backup/wingman-templates-backup.tar.gz -C /data
```

## Differences from Original Script

| Feature | Original Script | Docker Version |
|---------|----------------|----------------|
| Interface | Command-line | Web GUI |
| Deployment | Interactive prompts | Form-based |
| Monitoring | Log files | Real-time dashboard |
| Templates | File-based | Web-managed |
| Status | Manual checking | API-driven |
| Rollback | Command-line | One-click |
| Multi-user | No | Yes (with auth) |
| Remote Access | SSH required | Web browser |

## Future Enhancements

Planned features for future releases:

- User authentication and authorization
- Multi-tenancy support
- Webhook notifications
- Discord/Slack integration
- Advanced monitoring with metrics
- Scheduled deployments
- Backup/restore functionality
- Game server status checking
- Resource usage graphs

## Contributing

This is based on the original `gameserver-deploy.sh` script. To contribute:

1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

## License

Same license as the original game server deployment script.

## Support

For issues and questions:

1. Check the logs: `docker-compose logs -f`
2. Review the API responses in browser DevTools
3. Verify your configuration in the Settings tab
4. Check that all external services are accessible

## Credits

- Original automation script: treestandk.com infrastructure team
- Web interface: Docker transformation project
- Icons: Font Awesome
- Framework: Flask

---

**Note**: This Docker version provides the same functionality as the original bash script but with a modern web interface and better monitoring capabilities. All the core deployment logic has been preserved and enhanced.
